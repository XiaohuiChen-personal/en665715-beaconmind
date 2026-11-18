"""The real-car environment backend in its fake mode: simulated car, fake camera, fake detector (work list 2.9).

It must hand the closed-loop harness the same per-step data as the simulators, so the last tests drive it with the
harness itself (when that module is present).

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote these tests.
"""
import json

import pytest

import beaconmind
from beaconmind.car import backend as B
from beaconmind.car.camera import CameraError, FakeCamera, HttpCamera, bm_headers, camera_status, capture_frames
from beaconmind.car.latch import Latch
from beaconmind.envs import kinsim_lite as ks
from beaconmind.schemas import validate

# tags in the map frame (the car starts at the origin facing +x): one ahead, one to the left, one behind
TAGS = [{"tag": 0, "id": 4, "x_m": 1.50, "y_m": 0.10}, {"tag": 1, "id": 9, "x_m": 0.30, "y_m": 1.40},
        {"tag": 2, "id": 4, "x_m": -1.60, "y_m": 0.0}]
SENSE_KEYS = {"odometry", "move", "safety", "detections", "status"}


def test_reset_gives_the_first_sensing(tmp_path):
    env = B.fake_env(tags=TAGS, log_dir=str(tmp_path))
    assert env.source == "real"
    sense = env.reset(2000)
    assert set(sense) == SENSE_KEYS
    assert sense["odometry"] is None and sense["move"] is None             # step 0, as in the simulators
    assert sense["detections"] == [{"id": 4, "range_m": 1.5, "bearing_deg": 3.8, "quality": 1.0, "_tag": 0, "det": 0}]
    assert sense["status"] == {"status": "ok", "error": None, "odometry_quality": "ok",
                               "sensors": {"camera": "ok", "imu": "ok", "pico": "armed"}}
    assert sense["safety"] == {"forward_allowed": ["FORWARD_25", "FORWARD_10"], "backward_allowed": False,
                               "turn_allowed": True, "scan_allowed": True}
    assert env.camera.n == 5 and env.camera.configured == ("xga", 12)      # obs_frames frames at the calibrated size
    assert env.truth() == {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
    assert env.describe()["ground_truth"] == "simulated"


def test_moves_return_measured_odometry(tmp_path):
    env = B.fake_env(tags=TAGS, log_dir=str(tmp_path), sim_params={"left_gain": 0.7})
    env.reset(1)
    sense = env.step("FORWARD_25")
    truth = env.truth()
    assert sense["move"] == {"action": "FORWARD_25", "result": "done", "reason": None}
    assert sense["odometry"]["forward_m"] == pytest.approx(truth["x_m"], abs=0.006)        # rounded to 0.01 m
    assert sense["odometry"]["left_m"] == pytest.approx(truth["y_m"], abs=0.006)
    assert sense["odometry"]["dtheta_deg"] == pytest.approx(truth["theta_deg"], abs=0.1)
    assert sense["safety"]["backward_allowed"] is True
    left = env.step("TURN_LEFT_30")
    assert left["odometry"]["dtheta_deg"] == pytest.approx(30.0, abs=3.0) and left["odometry"]["dtheta_deg"] > 0
    assert left["safety"]["backward_allowed"] is False
    right = env.step("TURN_RIGHT_30")
    assert right["odometry"]["dtheta_deg"] == pytest.approx(-30.0, abs=3.0)
    idle = env.step(None)
    assert idle["move"] is None and idle["odometry"] == B.ZERO_ODOMETRY    # sensed again, nothing moved
    # dead reckoning from the handed-out precision stays near the truth over these four steps
    assert env.pose_dr["x_m"] == pytest.approx(env.truth()["x_m"], abs=0.01)
    assert env.pose_dr["theta_deg"] == pytest.approx(env.truth()["theta_deg"], abs=0.3)


def test_odometry_feeds_the_agents_tool_like_the_simulators(tmp_path):
    env = B.fake_env(tags=TAGS)
    env.reset(1)
    pose = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
    for action in ("FORWARD_25", "TURN_LEFT_30", "FORWARD_10", "TURN_RIGHT_30", "FORWARD_25"):
        odo = env.step(action)["odometry"]
        pose = beaconmind.geometry.compose_odometry(pose, odo["forward_m"], odo["left_m"], odo["dtheta_deg"])
    truth = env.truth()
    assert pose["x_m"] == pytest.approx(truth["x_m"], abs=0.02) and pose["y_m"] == pytest.approx(truth["y_m"], abs=0.02)
    assert pose["theta_deg"] == pytest.approx(truth["theta_deg"], abs=0.3)


def test_backward_only_after_a_forward_move():
    env = B.fake_env(tags=TAGS)
    env.reset(1)
    refused = env.step("BACKWARD_10")
    assert refused["move"] == {"action": "BACKWARD_10", "result": "refused", "reason": "executor: no forward move before"}
    assert refused["odometry"] == B.ZERO_ODOMETRY and env.truth()["x_m"] == 0.0
    forward = env.step("FORWARD_10")
    back = env.step("BACKWARD_10")
    assert back["move"]["result"] == "done"
    assert back["odometry"]["forward_m"] == pytest.approx(-forward["odometry"]["forward_m"], abs=0.015)
    assert env.truth()["x_m"] == pytest.approx(0.0, abs=0.015)
    assert env.step("BACKWARD_10")["move"]["result"] == "refused"          # only directly after a forward move
    with pytest.raises(ValueError):
        env.step("FORWARD_50")


@pytest.mark.parametrize("distance, allowed", [(1.50, ["FORWARD_25", "FORWARD_10"]), (0.55, ["FORWARD_10"]),
                                              (0.40, [])])
def test_forward_flags_from_the_tag_ahead(distance, allowed):
    env = B.fake_env(tags=[{"tag": 0, "id": 1, "x_m": distance, "y_m": 0.0}])
    assert env.reset(1)["safety"]["forward_allowed"] == allowed            # forward_wall_limit_m 0.35 (configs/dv.json)
    assert env.last_wall_m == pytest.approx(distance, abs=0.01)


def test_unknown_wall_policy():
    assert B.fake_env(tags=[]).reset(1)["safety"]["forward_allowed"] == ["FORWARD_25", "FORWARD_10"]
    assert B.fake_env(tags=[], unknown_wall="block").reset(1)["safety"]["forward_allowed"] == []
    assert B.tag_wall_distance([{"range_m": 1.0, "bearing_deg": 60.0}]) is None            # outside the 45 degree cone
    assert B.tag_wall_distance([{"range_m": 1.0, "bearing_deg": 60.0}, {"range_m": 2.0, "bearing_deg": -20.0}]) == \
        pytest.approx(1.879, abs=0.001)


def test_wall_check_from_the_room_and_the_dead_reckoned_pose():
    kr = pytest.importorskip("beaconmind.envs.kinsim_room")
    world = beaconmind.course_root() / "configs" / "arenas" / "real-room-nominal.json"
    if not world.exists():
        pytest.skip("no room world file")
    start = {"x_m": 2.2, "y_m": 0.9, "theta_deg": -90.0}       # about 0.83 m from the wall it faces (near y = 0.07)
    scene = kr.room_scene(str(world), start_pose=start)
    env = B.fake_env(scene=scene, tags=[])                     # no tag in view: only the room's edge speaks
    sense = env.reset(1)
    expect = kr.forward_allowed(scene, {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}, 0.35)
    assert sense["safety"]["forward_allowed"] == expect
    assert expect == ["FORWARD_25", "FORWARD_10"]
    steps = 0
    while "FORWARD_10" in sense["safety"]["forward_allowed"] and steps < 12:
        sense = env.step("FORWARD_10")
        steps += 1
    assert 3 <= steps <= 6                                     # it stops offering forward moves before the wall
    assert sense["safety"]["forward_allowed"] == []
    assert 0.35 - 0.02 <= kr.wall_distance_ahead(scene, env.truth()) < 0.35 + 0.10


def test_camera_failures_are_reported_not_hidden():
    def dead(_n):
        raise CameraError("timed out")
    env = B.fake_env(tags=TAGS)
    env.camera = FakeCamera(dead)
    sense = env.reset(1)
    assert sense["detections"] == [] and sense["status"]["status"] == "error"
    assert sense["status"]["sensors"]["camera"] == "down" and "camera down" in sense["status"]["error"]

    def flaky(n):
        if n > 3:
            raise CameraError("timed out")
        return b"\xff\xd8x\xff\xd9"
    frames, records = capture_frames(FakeCamera(flaky), 5)
    assert len(frames) == 3 and sum(1 for r in records if "error" in r) == 3
    assert camera_status(None, 5, 3) == "stale" and camera_status(None, 5, 0) == "down" and camera_status(None, 5, 5) == "ok"


def test_a_car_restart_gives_null_odometry_and_an_error(tmp_path):
    latch = Latch(tmp_path / "LATCH")
    env = B.fake_env(tags=TAGS, latch=latch)
    env.reset(1)
    env.step("FORWARD_10")
    env.link.sim.reboot()
    sense = env.step(None)
    assert sense["odometry"] is None                           # contract C3: the counts started again
    assert sense["status"]["status"] == "error" and "restarted" in sense["status"]["error"]
    assert latch.is_set()
    refused = env.step("FORWARD_10")
    assert refused["move"]["result"] == "refused" and refused["move"]["reason"] == "latched"


def test_backward_is_offered_exactly_when_it_would_run():
    """Review finding 16."""
    env = B.fake_env(tags=TAGS)
    env.reset(1)
    env.link.sim.p.blocked_left = env.link.sim.p.blocked_right = True
    stalled = env.step("FORWARD_25")                           # stalled at about 0 m: nothing to back out of
    assert stalled["move"]["result"] == "stalled" and stalled["safety"]["backward_allowed"] is False
    assert env.step("BACKWARD_10")["move"]["result"] == "refused"
    env.link.sim.p.blocked_left = env.link.sim.p.blocked_right = False
    assert env.step("FORWARD_10")["safety"]["backward_allowed"] is True
    idle = env.step(None)                                      # a step without a move in between
    assert idle["safety"]["backward_allowed"] is False
    assert env.step("BACKWARD_10")["move"]["result"] == "refused" and env.truth()["x_m"] > 0.08


def test_a_move_stalled_part_way_can_be_backed_out():
    env = B.fake_env(tags=TAGS)
    env.reset(1)
    link = env.link

    def block(l):
        if l.sim.truth()["x_m"] > 0.08:
            l.sim.p.blocked_left = l.sim.p.blocked_right = True
    link.on_step = block
    sense = env.step("FORWARD_25")
    link.on_step = None
    link.sim.p.blocked_left = link.sim.p.blocked_right = False
    assert sense["move"]["result"] == "stalled" and sense["safety"]["backward_allowed"] is True
    back = env.step("BACKWARD_10")
    assert back["move"]["result"] == "done" and back["odometry"]["forward_m"] == pytest.approx(-0.085, abs=0.025)


def test_a_refused_step_does_not_reuse_the_previous_moves_details(tmp_path):
    latch = Latch(tmp_path / "LATCH")
    env = B.fake_env(tags=TAGS, latch=latch, sim_params={"slip_left": 0.6})
    env.reset(1)
    assert env.step("FORWARD_25")["status"]["odometry_quality"] == "slip_suspected"
    latch.set("operator STOP (key)", "bm_stop")
    refused = env.step("FORWARD_25")
    assert refused["move"]["result"] == "refused" and refused["status"]["odometry_quality"] == "ok"
    assert env.last_step["executed"]["diag"] is None


def test_only_the_fake_environment_allows_a_resume():
    """The harness re-sends every logged move on a resume, so it asks for deterministic_replay. The simulated car
    may say yes; the class used for the real car must not have the attribute at all."""
    assert B.fake_env(tags=TAGS).deterministic_replay is True
    assert not hasattr(B.RealCarEnv, "deterministic_replay")


def test_slip_sets_the_odometry_quality():
    env = B.fake_env(tags=TAGS, sim_params={"slip_left": 0.6})
    env.reset(1)
    assert env.step("FORWARD_25")["status"]["odometry_quality"] == "slip_suspected"


def test_every_step_is_written(tmp_path):
    env = B.fake_env(tags=TAGS, log_dir=str(tmp_path / "run"))
    env.reset(7)
    env.step("FORWARD_10")
    rows = [json.loads(line) for line in open(tmp_path / "run" / "steps.jsonl")]
    assert [r["step"] for r in rows] == [0, 1] and rows[0]["executed"] is None
    executed = rows[1]["executed"]
    assert validate("move", executed["command"]) == [] and validate("move_result", executed["result"]) == []
    assert executed["command"]["obs_id"] == "real-s001" and executed["diag"]["action"] == "FORWARD_10"
    assert rows[1]["odometry_exact"]["forward_m"] == pytest.approx(rows[1]["truth"]["x_m"], abs=0.002)
    assert len(rows[1]["frames"]) == 5 and rows[1]["car_state"]["armed"] is True


def test_the_observation_validates_as_contract_c3():
    """What the harness builds from a sense (kinsim_lite.as_observation, as harness/closed_loop.py does), with the
    real-car fields put in by backend.as_observation, is a valid bm.observation/1 with source "real"."""
    env = B.fake_env(tags=TAGS)
    env.reset(1)
    sense = env.step("FORWARD_25")
    raw = {"step": 1, "odometry": sense["odometry"], "last_move": {"action": "FORWARD_25", "result": "done"},
           "counters": {"steps_left": 149}, "safety": sense["safety"], "detections": sense["detections"]}
    counters = {"odometer_m": 0.25, "travel_since_fix_m": 0.25, "turns_since_fix": 0}
    obs = B.as_observation(env, sense, ks.as_observation(1, raw, counters, mode="closed_loop"))
    assert validate("observation", obs) == []
    assert obs["source"] == "real" and obs["sensors"] == {"camera": "ok", "imu": "ok", "pico": "armed"}
    assert obs["odometry"]["quality"] == "ok" and all("_tag" not in d for d in obs["detections"])


# ---------------------------------------------------------------- the camera client

def test_http_camera_saves_every_frame_like_the_recorder(tmp_path):
    jpeg = b"\xff\xd8" + b"x" * 100 + b"\xff\xd9"
    calls = []

    def grabber(url, timeout):
        calls.append(url)
        if url.endswith("/capture"):
            return 200, {"X-BM-Seq": str(len(calls)), "X-BM-Width": "1024", "X-BM-Height": "768"}, jpeg
        return 200, {}, b"ok"
    cam = HttpCamera("http://cam.invalid/", save_dir=str(tmp_path / "frames"), grabber=grabber)
    assert cam.configure() == "ok" and calls[0] == "http://cam.invalid/control?framesize=xga&quality=12"
    frames, records = capture_frames(cam, 3)
    assert frames == [jpeg] * 3
    index = [json.loads(line) for line in open(tmp_path / "frames" / "index.jsonl")]
    assert len(index) == 3 and all((tmp_path / "frames" / r["file"]).read_bytes() == jpeg for r in index)
    assert index[0]["headers"] == {"x-bm-seq": 2, "x-bm-width": 1024, "x-bm-height": 768} and index[0]["http"] == 200
    assert bm_headers({"X-BM-Seq": "7", "Content-Type": "image/jpeg"}) == {"x-bm-seq": 7}


def test_http_camera_rejects_a_frame_of_the_wrong_size_or_kind(tmp_path):
    def vga(url, timeout):
        return 200, {"X-BM-Width": "640", "X-BM-Height": "480"}, b"\xff\xd8x\xff\xd9"
    with pytest.raises(CameraError, match="calibration is for 1024x768"):
        HttpCamera("http://cam.invalid", save_dir=str(tmp_path), grabber=vga).grab()
    with pytest.raises(CameraError, match="not a JPEG"):
        HttpCamera("http://cam.invalid", grabber=lambda url, timeout: (200, {}, b"<html>busy</html>")).grab()

    def down(url, timeout):
        raise OSError("connection refused")
    cam = HttpCamera("http://cam.invalid", save_dir=str(tmp_path), grabber=down)
    frames, records = capture_frames(cam, 5)
    assert frames == [] and len(records) == 3 and cam.errors == 3          # gives up after three failed requests
    assert "connection refused" in json.loads(open(tmp_path / "index.jsonl").readlines()[-1])["error"]


# ---------------------------------------------------------------- driven by the closed-loop harness

def test_the_harness_drives_the_backend(tmp_path):
    cl = pytest.importorskip("beaconmind.harness.closed_loop")
    rp = pytest.importorskip("beaconmind.harness.replay")
    world = ks.make_world(2000)                                # a study world: tags on the walls of the 2.25 m square
    env = B.fake_env(tags=world, hfov_deg=60.0, log_dir=str(tmp_path / "steps"))
    out = tmp_path / "ep.jsonl"
    res = cl.run_episode(cl.B2Driver(), "", env, 2000, out, rp.Budget(float("inf")), 8, lambda *_: None, config="t")
    assert res["steps"] == 8 and res["ended_by"] == "budget"
    rows = [json.loads(line) for line in open(out)]
    moves = [r["executed_move"] for r in rows if r.get("executed_move")]
    assert len(moves) >= 6 and all(m["result"] == "done" for m in moves)
    assert rows[0]["raw"]["odometry"] is None and rows[1]["raw"]["odometry"] is not None
    assert all(r["truth"] is not None for r in rows)
    steps = [json.loads(line) for line in open(tmp_path / "steps" / "steps.jsonl")]
    assert len(steps) >= 8 and all(validate("move_result", s["executed"]["result"]) == [] for s in steps if s["executed"])


# ---------------------------------------------------------------- the real detector (needs OpenCV: the container)

def test_real_detector_on_a_rendered_frame():
    """camera.perception_detector on a frame rendered by the perception module's own synthesiser, through the
    backend: the C3 pipeline over five frames gives the two tags at the range and bearing they were drawn at."""
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    synth = pytest.importorskip("beaconmind.perception.synth")
    from beaconmind.camera_model import load_camera
    from beaconmind.car.camera import perception_detector
    from beaconmind.car.link import default_sim_link

    frame = synth.render_scene(load_camera(), [synth.tag_at(7, 1.2, 8.0), synth.tag_at(3, 1.8, -12.0)])
    ok, buf = cv2.imencode(".jpg", np.clip(frame, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 90])
    assert ok
    jpeg = buf.tobytes()
    env = B.RealCarEnv(default_sim_link(), FakeCamera(lambda n: jpeg), perception_detector(tag_center_height_m=0.23))
    sense = env.reset(0)
    assert [(d["det"], d["id"]) for d in sense["detections"]] == [(0, 7), (1, 3)]          # left to right
    assert sense["detections"][0]["range_m"] == pytest.approx(1.2, abs=0.03)
    assert sense["detections"][0]["bearing_deg"] == pytest.approx(8.0, abs=0.5)
    assert sense["detections"][1]["range_m"] == pytest.approx(1.8, abs=0.05)
    assert sense["detections"][1]["bearing_deg"] == pytest.approx(-12.0, abs=0.5)
    assert all(d["quality"] == 1.0 and d["_tag"] is None for d in sense["detections"])
    assert sense["status"]["sensors"]["camera"] == "ok" and len(env.last_step["detections_internal"]) == 2
    broken = env.detector([b"not a jpeg"] * 5, 5)                              # an undecodable frame is no detection
    assert broken["detections"] == [] and broken["per_frame"][0] == {"error": "not decodable"}
