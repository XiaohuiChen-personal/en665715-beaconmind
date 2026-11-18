"""The real car behind the closed-loop harness's environment protocol (work list 2.9; plan C3, C9, task M3.T9).

The protocol is the one harness/closed_loop.py states, so the same agent, tools, validator and logs run on the
simulators and on the car:

    env.source                 "real"
    env.describe() -> dict     configuration, for run.json
    env.reset(seed) -> sense   the first sensing (no move; `seed` only labels the episode)
    env.step(action) -> sense  execute one C2 move through the executor (None: sense again), then sense
    env.truth() -> pose | None the true pose when one exists (the fake car), else None: on the real car ground
                               truth is tape (plan section 3.6), read by a person, not by this class

A sense is {"odometry": {forward_m, left_m, dtheta_deg} | None, "move": {"action", "result", "reason"} | None,
"safety": {"forward_allowed": [...], "backward_allowed", "turn_allowed", "scan_allowed"},
"detections": [{det, id, range_m, bearing_deg, quality, _tag: None}]}, the same keys as a simulator's, plus
"status" (what contract C3 puts in status / error / sensors / odometry.quality), which the simulators never need
because nothing fails there. Everything else about a step (the command, the bm.move_result/1 record, the
executor's details, the frames used, what each frame showed) is written to steps.jsonl in the log folder.

What one step does: the move runs to its end, the car settles (the executor waits for the counts to stop), the
environment waits obs_settle_s more, takes obs_frames frames, runs the detector on them, and reads the odometer.
The odometry is the motion since the previous sensing, in the robot frame at that sensing (C1), from the wheel
counts and the IMU heading over the whole interval, so the coast after the stop command is in it.

Safety flags. The harness's validator takes forward_allowed from the environment. Here it is the stricter of two
estimates: (1) from the tags in view within 45 degrees of straight ahead, range x cos(bearing) (plan C5 item 3b);
(2) when a world file and the taped start pose are given, the distance to the driving area's edge ahead of the
dead-reckoned pose (the rule the room simulator applies to the true pose). A forward move is offered when it
leaves forward_wall_limit_m. With neither estimate the wall distance is unknown and `unknown_wall` decides:
"allow" (default) or "block". Items 3a, 3c and 3d of C5 (tag-plane estimate, mapped beacons, a tag that dropped
out) are not implemented here; the operator and the stall detection are the backstop.

Fake mode: fake_env() builds the same class on the simulated car and a camera and detector made from a world
file, so the whole path runs in tests and rehearsals without ROS, a camera or OpenCV.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this backend.
"""
import json
import math
import os
import time

from .camera import CameraError, FakeCamera, camera_status, capture_frames, fake_detector
from .moves import ACTIONS, MIN_DISTANCE_M, make_move
from .odometry import delta_between, wrap_deg

FORWARD_STEPS = (("FORWARD_25", 0.25), ("FORWARD_10", 0.10))
ZERO_ODOMETRY = {"forward_m": 0.0, "left_m": 0.0, "dtheta_deg": 0.0}
CONTACT_RESULTS = ("done", "stalled", "bumped")     # C2: BACKWARD_10 only directly after such a forward move


def tag_wall_distance(detections, cone_deg=45.0):
    """Plan C5 item 3b: the smallest range x cos(bearing) over the tags within cone_deg of straight ahead, or None."""
    ahead = [d["range_m"] * math.cos(math.radians(d["bearing_deg"])) for d in detections
             if abs(d["bearing_deg"]) <= cone_deg]
    return min(ahead) if ahead else None


def compose(pose, odo):
    """pose advanced by an odometry step (contract C1), heading wrapped."""
    th = math.radians(pose["theta_deg"])
    return {"x_m": pose["x_m"] + odo["forward_m"] * math.cos(th) - odo["left_m"] * math.sin(th),
            "y_m": pose["y_m"] + odo["forward_m"] * math.sin(th) + odo["left_m"] * math.cos(th),
            "theta_deg": wrap_deg(pose["theta_deg"] + odo["dtheta_deg"])}


class RealCarEnv:
    source = "real"

    def __init__(self, link, camera, detector, dv=None, car=None, scene=None, log_dir=None, truth_fn=None,
                 unknown_wall="allow", episode="real"):
        """link: a car link (ros_io.RosCarLink for the car, link.SimLink for the fake car).
        camera: camera.HttpCamera or FakeCamera. detector: camera.perception_detector(...) or a fake.
        scene: envs.kinsim_room.room_scene(world, start_pose) for the wall check from the dead-reckoned pose, or
        None. log_dir: where steps.jsonl goes (None: nothing is written). truth_fn: () -> pose, fake mode only."""
        if dv is None:
            from beaconmind.dv import load_dv
            dv = load_dv()
        if car is None:
            from .config import load_car
            car = load_car()
        if unknown_wall not in ("allow", "block"):
            raise ValueError("unknown_wall is 'allow' or 'block'")
        self.link, self.camera, self.detector = link, camera, detector
        self.dv, self.scene, self.log_dir, self.truth_fn = dv, scene, log_dir, truth_fn
        self.unknown_wall, self.episode = unknown_wall, episode
        self.obs_frames = int(dv["obs_frames"])
        self.obs_settle_s = float(dv["obs_settle_s"])
        self.wall_limit_m = float(dv["forward_wall_limit_m"])
        self.slip_deg = float(dv["slip_yaw_disagree_deg"])
        self.sweep_m = float(car["sweep_radius_m"])
        self.step_index = 0
        self.cmd_seq = 0
        self.seed = None
        self.pose_dr = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}     # dead reckoning in the map frame
        self._mark = None               # odometer state at the previous sensing
        self._boots = None
        self._last_forward = 0.0
        self.last_step = None           # the full record of the last step (also written to steps.jsonl)

    # ------------------------------------------------------------ protocol

    def describe(self):
        cfg = getattr(self.link, "cfg", None)
        return {"env": "real car (beaconmind.car.backend.RealCarEnv)", "link": type(self.link).__name__,
                "camera": type(self.camera).__name__, "obs_frames": self.obs_frames,
                "obs_settle_s": self.obs_settle_s, "wall_limit_m": self.wall_limit_m,
                "unknown_wall": self.unknown_wall, "wall_check_from_world": self.scene is not None,
                "arena": None if self.scene is None else self.scene.get("arena"),
                "world": None if self.scene is None else self.scene.get("world"),
                "scale_source": getattr(cfg, "scale_source", None),
                "ticks_per_m": None if cfg is None else [cfg.ticks_per_m_left, cfg.ticks_per_m_right],
                "contacts_simulated": False, "ground_truth": "none (tape)" if self.truth_fn is None else "simulated"}

    def reset(self, seed):
        self.seed = seed
        self.step_index = 0
        self.pose_dr = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
        self._last_forward = 0.0
        self._mark = None
        self._boots = None
        if hasattr(self.camera, "configure"):
            try:
                self.camera.configure()
            except CameraError:
                pass                    # the first capture reports the camera's state
        return self._sense(None, None, first=True)

    def step(self, action):
        if action is None:
            self._last_forward = 0.0        # BACKWARD_10 is only for directly after a forward move
            return self._sense(None, None)
        if action not in ACTIONS:
            raise ValueError("not a move: %r" % (action,))
        self.cmd_seq += 1
        obs_id = "%s-s%03d" % (self.episode, self.step_index)
        kind = ACTIONS[action][0]
        if kind == "backward" and self._last_forward < MIN_DISTANCE_M:
            return self._sense({"action": action, "result": "refused", "reason": "executor: no forward move before"},
                               None)
        cmd = make_move(action, self.cmd_seq, obs_id, self.dv,
                        prev_forward_m=self._last_forward if kind == "backward" else None)
        result = self.link.execute(cmd)
        if kind == "forward" and result["result"] in CONTACT_RESULTS:
            self._last_forward = abs(result["achieved_forward_m"])
        else:
            self._last_forward = 0.0
        move = {"action": action, "result": result["result"], "reason": result["reason"]}
        # a refused move never ran: the link's last_diag still belongs to the move before it
        diag = None if result["result"] == "refused" else self.link.last_diag
        return self._sense(move, {"command": cmd, "result": result, "diag": diag})

    def truth(self):
        return None if self.truth_fn is None else self.truth_fn()

    def close(self):
        self.link.close()

    # ------------------------------------------------------------ sensing

    def _sense(self, move, executed, first=False):
        self.link.wait(self.obs_settle_s)
        frames, frame_records = capture_frames(self.camera, self.obs_frames)
        cam = camera_status(self.camera, self.obs_frames, len(frames))
        try:
            found = self.detector(frames, self.obs_frames) if frames else {"detections": [], "internal": [], "per_frame": []}
            detector_error = None
        except Exception as exc:    # noqa: BLE001 - a detector failure is a sensor error of this step, not a crash
            found, detector_error = {"detections": [], "internal": [], "per_frame": []}, "%s: %s" % (type(exc).__name__, exc)
            cam = "down"
        detections = [dict(d, _tag=d.get("_tag")) for d in found["detections"]]
        state = self.link.car_state()
        now = self.link.odom_state()
        rebooted = self._boots is not None and state.get("boots") != self._boots
        self._boots = state.get("boots")
        exact = None
        if first or self._mark is None:
            odometry = None
        elif rebooted:
            odometry = None             # C3: after a restart of the car the counts started again
        else:
            exact = delta_between(self._mark, now)
            odometry = {"forward_m": round(exact["forward_m"], 2), "left_m": round(exact["left_m"], 2),
                        "dtheta_deg": round(exact["dtheta_deg"], 1)}
            self.pose_dr = compose(self.pose_dr, exact)
        self._mark = now
        quality = "ok"
        if exact is not None and executed is not None and executed.get("diag"):
            if executed["diag"].get("yaw_disagree_deg", 0.0) > self.slip_deg:
                quality = "slip_suspected"      # D5: wheel yaw and gyro yaw disagree by more than slip_yaw_disagree_deg
        age = state.get("telemetry_age_s")
        errors = []
        if cam != "ok":
            errors.append("camera %s" % cam + (" (%s)" % detector_error if detector_error else ""))
        if age is None or age > 1.0:
            errors.append("no telemetry from the car")
        if state.get("imu_ready") is False:
            errors.append("imu not ready")
        if state.get("armed") is False and not state.get("latched"):
            errors.append("car disarmed")
        if rebooted:
            errors.append("the car restarted")
        status = {"status": "error" if errors else "ok", "error": "; ".join(errors) or None,
                  "sensors": {"camera": cam,
                              "imu": "ok" if state.get("imu_ready") else "error",
                              "pico": "armed" if state.get("armed") else "disarmed"},
                  "odometry_quality": quality}
        safety = self._safety(detections, move)
        sense = {"odometry": odometry, "move": move, "safety": safety, "detections": detections, "status": status}
        self.last_step = {
            "type": "step", "episode": self.episode, "seed": self.seed, "step": self.step_index,
            "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "t_unix": round(time.time(), 3),
            "sense": sense, "executed": executed, "odometry_exact": exact, "pose_dead_reckoned": dict(self.pose_dr),
            "frames": frame_records, "per_frame": found.get("per_frame"), "detections_internal": found.get("internal"),
            "car_state": state, "truth": self.truth(),
        }
        self._write(self.last_step)
        self.step_index += 1
        return sense

    def _safety(self, detections, move):
        estimates = []
        from_tags = tag_wall_distance(detections)
        if from_tags is not None:
            estimates.append(from_tags)
        if self.scene is not None:
            from beaconmind.envs import kinsim_room as kr
            try:
                estimates.append(kr.wall_distance_ahead(self.scene, self.pose_dr))
            except (ValueError, ZeroDivisionError):
                estimates.append(0.0)       # the dead-reckoned pose left the driving area: nothing forward
        if estimates:
            wall = min(estimates)
            forward = [name for name, step in FORWARD_STEPS if wall - step >= self.wall_limit_m]
        else:
            wall = None
            forward = [name for name, _ in FORWARD_STEPS] if self.unknown_wall == "allow" else []
        near = [d for d in detections if d["range_m"] < self.sweep_m + 0.05]
        # offered exactly when step("BACKWARD_10") would run: after a forward move that covered some distance
        back = self._last_forward >= MIN_DISTANCE_M
        self.last_wall_m = wall
        return {"forward_allowed": forward, "backward_allowed": back, "turn_allowed": not near,
                "scan_allowed": not near}

    last_wall_m = None

    def _write(self, record):
        if not self.log_dir:
            return
        try:
            os.makedirs(self.log_dir, exist_ok=True)
            with open(os.path.join(self.log_dir, "steps.jsonl"), "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, default=str) + "\n")
        except OSError as exc:
            self.log_error = "%s: %s" % (type(exc).__name__, exc)

    log_error = None


def as_observation(env, sense, obs):
    """Put what only a real car reports into a C3 OBSERVATION the harness built from `sense`: source, status,
    error, sensors and odometry.quality. Returns obs (changed in place)."""
    status = sense.get("status") or {}
    obs["source"] = env.source
    obs["status"] = status.get("status", "ok")
    obs["error"] = status.get("error")
    obs["sensors"] = dict(status.get("sensors") or obs.get("sensors") or {})
    if obs.get("odometry") is not None:
        obs["odometry"]["quality"] = status.get("odometry_quality", "ok")
    return obs


# ---------------------------------------------------------------- fake mode

def world_detections_fn(scene_tags, pose_fn, hfov_deg, min_range_m=0.3, max_range_m=2.5, quality=1.0):
    """A stand-in for camera + detector: the tags of a scene (map frame: {id, x_m, y_m}) that the car at pose_fn()
    would see inside the field of view and range window, exact (no noise), as observation detections."""
    def detect(_jpegs):
        pose = pose_fn()
        out = []
        for tag in scene_tags:
            dx, dy = tag["x_m"] - pose["x_m"], tag["y_m"] - pose["y_m"]
            rng = math.hypot(dx, dy)
            bearing = wrap_deg(math.degrees(math.atan2(dy, dx)) - pose["theta_deg"])
            if abs(bearing) <= hfov_deg / 2.0 and min_range_m <= rng <= max_range_m:
                out.append({"id": tag["id"], "range_m": round(rng, 2), "bearing_deg": round(bearing, 1),
                            "quality": quality, "_tag": tag.get("tag")})
        return out
    return detect


def fake_env(scene=None, tags=None, latch=None, log_dir=None, hfov_deg=46.9, sim_params=None, cfg=None, **env_kwargs):
    """RealCarEnv on the simulated car, with a camera and detector that see the given tags from the car's true pose.

    scene: envs.kinsim_room.room_scene(...) (its tags and driving area are used), or None with tags=[{id, x_m, y_m}]
    in the map frame (the car starts at the origin facing +x). hfov_deg 46.9 is configs/camera.json's measured
    field of view."""
    from . import config as C
    from .link import SimLink
    from .simcar import SimCar, SimCarParams

    link = SimLink(cfg or C.load_config(), SimCar(SimCarParams(**(sim_params or {}))), latch=latch)

    def pose():
        t = link.sim.truth()
        return {"x_m": t["x_m"], "y_m": t["y_m"], "theta_deg": wrap_deg(t["theta_deg"])}

    scene_tags = tags if tags is not None else (scene["tags"] if scene is not None else [])
    detector = fake_detector(world_detections_fn(scene_tags, pose, hfov_deg))
    env = RealCarEnv(link, FakeCamera(), detector, scene=scene, log_dir=log_dir, truth_fn=pose, **env_kwargs)
    # the harness may re-simulate logged moves on this environment (a resume). Only the simulated car: on the real
    # car a resume would re-send every logged move, so RealCarEnv itself never has this attribute.
    env.deterministic_replay = True
    return env
