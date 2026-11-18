"""Kinematic simulator for a polygon arena (the real room) and for the study square, behind one environment class.

Work list 3.1 (plan M2.T3) and the simulator half of 3.2 (rule R1: every real-car session is rehearsed here first).
kinsim_lite.py is frozen by the pre-registration, so nothing there is edited. This module imports its coded
procedure (estimate_step, decide_step), its record helpers (initial_memory, rp, counters_from, as_observation,
CounterTracker, dead_reckoning) and its constants, and re-implements only what kinsim_lite ties to the 2.25 m
square: the visibility test, the wall distance and the episode loop. Configured as the study square
(KinSimEnv.study(seed)), an episode's records are equal, value for value, to kinsim_lite.run_episode(seed)
(tests/test_kinsim_room.py::test_study_square_reproduces_kinsim_lite).

FRAMES. Everything the simulator hands out is in the MAP frame (plan C1): the car's pose at step 0 is (0, 0, 0),
x forward, y left, angles counter-clockwise in degrees. A world file (bm.world/1) is in its own arena frame;
room_scene() moves the walls, the driving area, the obstacles and the tags (positions and normals) into the map
frame of the chosen start pose. KinSimEnv.truth_pose_world() gives the pose back in the arena frame (for tape checks).

THE ENVIRONMENT CLASS (for the closed-loop harness; the same class serves the square and the room):

    env = KinSimEnv.study(2000)                               # the study's 2.25 m square, world of seed 2000
    env = KinSimEnv.room("configs/arenas/real-room-nominal.json", start_pose={"x_m": 2.2, "y_m": 2.6, "theta_deg": 90},
                         preset_name="camera", max_range_m=2.0, odometry="carpet")
    raw = env.reset(seed)            # first raw step record (step 0); seed selects the noise stream "noise-<seed>"
    raw = env.step(move, pose_source=None)   # executes one move, returns the next raw step record
    raw = env.observe(pose_source=None)      # a step with no move: same pose, zero odometry, last_move None
    env.MOVES                        # ("FORWARD_25", "FORWARD_10", "BACKWARD_10", "TURN_LEFT_30", "TURN_RIGHT_30")
    env.truth_pose()                 # ground truth in the map frame: FOR SCORING ONLY, never shown to the agent
    env.truth_pose_world()           # the same pose in the world file's frame
    env.world                        # the tags in the map frame: [{tag, id, x_m, y_m, wall, (uid, normal_deg)}]
    env.scene                        # polygons, obstacles, start pose (map frame)
    env.info                         # last step's clearance figures (footprint to walls, inside the driving area)
    env.steps_left, env.step_index

  A raw step record is kinsim_lite's: {step, odometry (None at step 0, else {forward_m, left_m, dtheta_deg}),
  last_move (None or {action, result}), counters {odometer_m, travel_since_fix_m, turns_since_fix, steps_left},
  safety {forward_allowed: [...], backward_allowed, turn_allowed, scan_allowed}, detections [{det, id, range_m,
  bearing_deg, quality, _tag}]}. `_tag` is the true tag index (truth, for scoring); kinsim_lite.as_observation(seed,
  raw, counters) strips it and builds the C3 OBSERVATION the agent sees. `pose_source` in step() is the pose source
  of the report the agent just wrote: a full fix ("beacon_fix", "relocalised") resets the env's own
  travel_since_fix_m and turns_since_fix, as kinsim_lite.run_episode does for B2. A harness that keeps its own
  counters (kinsim_lite.CounterTracker, verified fixes only) can ignore the env's and pass nothing.
  A move outside raw["safety"] is refused: the pose does not change and the next record has
  last_move.result == "refused" and zero odometry (it still uses up a step). step() raises ValueError for a string
  that is not in MOVES; DONE and the other non-move decisions are the caller's business (stop calling step()).

  b2_step(raw, prev_report) is the coded procedure B2 on one raw record (the body of kinsim_lite.run_episode's
  loop): it returns (report, calls, est). make_b2_policy() returns the same procedure with the one branch a room
  needs defined (see its docstring); use that one to drive the room. run_episode(env, seed, policy=...) drives a
  whole episode and returns kinsim_lite's episode document plus `ended_by`, `info`, `noise`, `arena`, `scene`, so
  tools/pilot_record-style logs (seed_<n>.json), the replay harness, metrics/pilot.py, dead_reckoning (B0) and B1
  read it unchanged. Any callable (raw, prev_report) -> (report, calls, anything) whose report["decision"] is a
  move or "DONE" can be the policy.

THE RANGE LIMIT is `max_range_m` of the noise block: a tag beyond it is never in the observation. The frozen
estimate_step has no range test of its own (configs/dv.json's reject_range_above_m, 2.0 m, is read by no code; the
study's detector stopped at 1.5 m), so nothing in dv.json needs overriding to rehearse 2.5 m. On the car the same
cut has to be made where the observation is built. The LLM's prompt (v3.3, rule 3) rejects range_m > 2.0 in words.

WHAT DIFFERS FROM kinsim_lite (each is a parameter; the study configuration switches all of them off):
  * driving area: any convex counter-clockwise polygon. Wall distance ahead is the ray's exit distance from that
    polygon; forward_allowed keeps the validator's rule (distance - step >= forward_wall_limit_m, 0.35 m), computed
    from the TRUE pose as in kinsim_lite. `drive_inset_m` moves every edge of the driving area inward.
  * tags anywhere, each with its own normal (normal_deg).
  * obstacles (convex polygons, e.g. the desk) that hide a tag when the sight line crosses them.
  * visibility: `hfov_deg` on the tag centre's bearing from the pose point (kinsim_lite's rule), or, when the noise
    block carries a `camera` (a bm.camera/1 document), beaconmind.camera_model: a tag is in view when the four
    corners of its black square project inside the picture, lens distortion and mount angles included. That gives
    the measured field of view AND the near limit: the lens is 0.075 m up and the tag centres 0.23 m up, so a
    close tag's top edge leaves the top of the picture (camera_model.min_full_view_range: 0.74 m from the axle
    midpoint straight ahead for the 160 mm tags). Each tag's size and height come from the world file.
  * noise: range sigma a + b r + c r^2; per-episode calibration errors (one range scale and one range offset for
    the whole episode); optional constant range and bearing biases (off by default).
  * odometry: kinsim_lite's model, or the `carpet` option (a forward move also turns the car; turns fall short).
  * BACKWARD_10 is executed (kinsim_lite's loop never needs it: B2 does not choose it).
  * B2's unimplemented branches end the episode (`ended_by: "not_implemented: ..."`) with the records so far kept;
    kinsim_lite.run_episode raises and the recorder skips the seed.

NOT SIMULATED (as in kinsim_lite): contacts, slips, null tag IDs, refused turns. Moves always complete. `info`
reports the clearance between the car's footprint and the walls so a rehearsal can count the steps a real car
would have touched something. The coded procedure B2 itself is unchanged: see the rehearsal report
(evidence/M3/M3.T12/rehearsal-b2.md) for how it behaves in a 3.8 x 5.2 m room.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this module (room geometry, camera visibility
model, noise presets, environment class, episode runner) around the imported kinsim_lite procedure.
"""
import contextlib
import json
import math
import os
import random

import beaconmind
from beaconmind import camera_model as cm
from beaconmind import geometry as g
from beaconmind.envs import kinsim_lite as ks

MOVES = ("FORWARD_25", "FORWARD_10", "BACKWARD_10", "TURN_LEFT_30", "TURN_RIGHT_30")
FORWARD_STEP_M = {"FORWARD_25": 0.25, "FORWARD_10": 0.10}
BACKWARD_STEP_M = 0.10
TURN_DEG = {"TURN_LEFT_30": 30.0, "TURN_RIGHT_30": -30.0}
STUDY_NORMALS = {"S": (0.0, 1.0), "N": (0.0, -1.0), "W": (1.0, 0.0), "E": (-1.0, 0.0)}   # kinsim_lite._normal
STUDY_NORMAL_DEG = {"S": 90.0, "N": -90.0, "W": 0.0, "E": 180.0}

# ---------------------------------------------------------------- noise presets
#
# "study": kinsim_lite.NOISE unchanged (the placeholder of plan M2.T3). Only the geometry differs in a room.
#
# "camera": the measured camera (configs/camera.json, 2026-11-18) through beaconmind.camera_model (pinhole, lens
# distortion, mount angles), with the error figures of the SIMULATED tag estimate evidence/M1/M1.T8/sim-estimate.md
# (the perception work of 2026-11-18; the tag pilot M1.T8 replaces them with measurements):
#   * In view: all four corners of the tag's black square inside the picture (2 px margin). This is
#     camera_model.square_in_view for the tag's own normal; it gives the true field of view (22.4 deg left, 23.9
#     right, 17.8 up, 18.1 down) and the near limit (camera_model.min_full_view_range: a 160 mm tag centred 0.23 m up
#     is whole from 0.74 m straight ahead, more to the sides).
#   * Range error is dominated by the calibration, which is the same for a whole session: about 1.1 % of the range
#     (focal length 1 %, tag size, tone curve) plus about 7 mm (lens position 5 mm, pitch 5 mm). So each episode
#     draws ONE scale error N(0, range_scale_sigma = 0.011) and ONE offset N(0, range_offset_sigma_m = 0.007) from
#     its own stream "calib-<seed>" and applies them to every detection. The per-frame part is small: sd 0.2 mm at
#     1 m, 1.2 mm at 2 m, 3.3 mm at 3 m, 4.8 mm at 4 m, i.e. about 0.35 mm r^2 for a 160 mm tag, taken as
#     inversely proportional to the tag's size: range sigma = 0.001 + 0.00035 (0.16 / S) r^2.
#   * Bearing: 0.3 deg per detection (principal point, roll and distortion residuals; the per-frame part is
#     0.002 deg). The camera's yaw is known to +-2 deg until the pilot: that is the separate constant
#     `bearing_bias_deg` (0 here; the rehearsal runs +2 deg as a sensitivity case).
#   * p_detect 0.95, the 60 deg incidence limit and quality 0.9 stay kinsim_lite's placeholders. The simulated
#     estimate found every tag in every frame out to 5 m, turned up to 30 deg; 0.95 leaves room for glare and the
#     corrupt frames seen in recordings (21 of 10,233).
CAMERA_RANGE_C_160 = 0.00035
TAG_BLACK_M = 0.16
_CAMERAS = {}


def camera_doc(path=None):
    """configs/camera.json (bm.camera/1) as a dict: what the noise block carries, so that logs record it."""
    path = path or beaconmind.course_root() / "configs" / "camera.json"
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def camera_of(doc):
    """The beaconmind.camera_model.Camera of a bm.camera/1 document (cached)."""
    key = json.dumps(doc, sort_keys=True)
    if key not in _CAMERAS:
        _CAMERAS[key] = cm.Camera.from_dict(doc)
    return _CAMERAS[key]


def preset(name, max_range_m=None, camera=None, tag_black_m=TAG_BLACK_M, **overrides):
    """A noise block. name: "study" or "camera". max_range_m: the range limit (detections beyond it are never
    reported; kinsim_lite's placeholder is 1.5 m, configs/dv.json's reject_range_above_m is 2.0 m). camera: a
    bm.camera/1 document (default configs/camera.json). tag_black_m scales the camera preset's per-frame noise."""
    n = dict(ks.NOISE, range_sigma_c=0.0, range_scale_sigma=0.0, range_offset_sigma_m=0.0, range_bias_frac=0.0,
             bearing_bias_deg=0.0, camera=None, margin_px=2.0, preset=name)
    if name == "camera":
        doc = camera or camera_doc()
        n.update(camera=doc, hfov_deg=round(camera_of(doc).hfov_deg, 2), range_sigma_a_m=0.001, range_sigma_b=0.0,
                 range_sigma_c=round(CAMERA_RANGE_C_160 * TAG_BLACK_M / tag_black_m, 6), range_scale_sigma=0.011,
                 range_offset_sigma_m=0.007, bearing_sigma_deg=0.3)
    elif name != "study":
        raise ValueError("unknown noise preset %r" % (name,))
    if max_range_m is not None:
        n["max_range_m"] = float(max_range_m)
    unknown = set(overrides) - set(n)
    if unknown:
        raise ValueError("unknown noise keys %s" % sorted(unknown))
    n.update(overrides)
    return n


# Odometry. "study": kinsim_lite's (the truth move is exact; the encoder distance reads (1 + N(0, 0.02)) times it,
# the gyro reads the turn + N(0, 0.3 deg)). "carpet": what the Module 9 sessions measured on this carpet
# (CONTEXT.md 2026-11-02): with the stronger heading hold a 0.30 m straight still turned the car about 4.5 deg to
# the left (15 deg/m), and two 45 deg turns measured 44.4 and 43.7 deg (scale 0.98, spread about 0.5 deg). The
# spread of the veer was not measured: 30 % of it is assumed. The gyro sees the true heading change, so odometry
# reports the veer (as dtheta_deg and left_m on a forward move); the truth path is what bends.
CARPET = {"veer_deg_per_m": 15.0, "veer_sigma_frac": 0.3, "turn_scale": 0.98, "turn_sigma_deg": 0.5}


# ---------------------------------------------------------------- plane geometry (convex, counter-clockwise polygons)

def _edges(poly):
    """[(a, inward unit normal)] for a counter-clockwise polygon (interior on the left)."""
    out = []
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        ex, ey = b[0] - a[0], b[1] - a[1]
        length = math.hypot(ex, ey)
        out.append((a, (-ey / length, ex / length)))
    return out


def is_convex_ccw(poly):
    n = len(poly)
    return n >= 3 and all(
        (poly[(i + 1) % n][0] - poly[i][0]) * (poly[(i + 2) % n][1] - poly[(i + 1) % n][1])
        - (poly[(i + 1) % n][1] - poly[i][1]) * (poly[(i + 2) % n][0] - poly[(i + 1) % n][0]) > 0 for i in range(n))


def inside_depth(poly, p):
    """Smallest signed distance from p to the polygon's edge lines: > 0 inside, < 0 outside."""
    return min((p[0] - a[0]) * n[0] + (p[1] - a[1]) * n[1] for a, n in _edges(poly))


def ray_exit_distance(poly, x, y, theta_deg):
    """Distance along the heading from (x, y) to the boundary of the convex polygon. For a point inside, the
    smallest non-negative crossing with an edge line the ray heads out through (for the axis-aligned square
    this is kinsim_lite.wall_distance_ahead, operation for operation). For a point outside: 0 when the heading
    leads further out through an edge already crossed, else the distance to the next edge."""
    th = math.radians(theta_deg)
    c, s = math.cos(th), math.sin(th)
    ts = []
    for a, n in _edges(poly):
        nd = n[0] * c + n[1] * s
        gap = n[0] * (a[0] - x) + n[1] * (a[1] - y)          # negative inside: the edge line lies ahead along -n
        if gap > 1e-9 and nd <= 1e-9:
            return 0.0                                          # outside this edge and not heading back in
        if nd < -1e-9:
            ts.append(gap / nd)
    return min(t for t in ts if t >= 0)


def segment_hits_polygon(p, q, poly):
    """True when segment p-q meets the convex polygon (Cyrus-Beck clip against its edge half-planes)."""
    t0, t1 = 0.0, 1.0
    dx, dy = q[0] - p[0], q[1] - p[1]
    for a, n in _edges(poly):
        num = (p[0] - a[0]) * n[0] + (p[1] - a[1]) * n[1]     # signed inside distance of p
        den = dx * n[0] + dy * n[1]
        if abs(den) < 1e-12:
            if num < 0:
                return False
            continue
        t = -num / den
        if den > 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return False
    return True


def point_segment_distance(p, a, b):
    ex, ey = b[0] - a[0], b[1] - a[1]
    q = ex * ex + ey * ey
    t = 0.0 if q == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * ex + (p[1] - a[1]) * ey) / q))
    return math.hypot(p[0] - (a[0] + t * ex), p[1] - (a[1] + t * ey))


def polygon_distance(poly, p):
    """0 inside the convex polygon, else the distance to its boundary."""
    if inside_depth(poly, p) >= 0:
        return 0.0
    return min(point_segment_distance(p, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))


def inset_polygon(poly, margin_m):
    """The convex counter-clockwise polygon with every edge moved inward by margin_m (same number of corners)."""
    ed = _edges(poly)
    out = []
    for i in range(len(poly)):
        (a1, n1), (a2, n2) = ed[i - 1], ed[i]
        c1 = n1[0] * a1[0] + n1[1] * a1[1] + margin_m
        c2 = n2[0] * a2[0] + n2[1] * a2[1] + margin_m
        det = n1[0] * n2[1] - n1[1] * n2[0]
        out.append(((c1 * n2[1] - c2 * n1[1]) / det, (n1[0] * c2 - n2[0] * c1) / det))
    if not is_convex_ccw(out) or any(inside_depth(poly, q) < margin_m - 1e-9 for q in out):
        raise ValueError("an inset of %.2f m leaves no valid polygon" % margin_m)
    return out


def to_map(start, x, y):
    """Arena-frame point -> map frame of the start pose (plan C1: T_map<-world = inverse of the start pose)."""
    th = math.radians(start["theta_deg"])
    dx, dy = x - start["x_m"], y - start["y_m"]
    return dx * math.cos(th) + dy * math.sin(th), -dx * math.sin(th) + dy * math.cos(th)


def to_world(start, pose):
    """Map-frame pose -> arena frame."""
    p = g.compose_odometry(start, pose["x_m"], pose["y_m"], pose["theta_deg"])
    return {"x_m": p["x_m"], "y_m": p["y_m"], "theta_deg": p["theta_deg"]}


# ---------------------------------------------------------------- scenes

def study_scene(seed, n_dup=3):
    """The study's 2.25 m square with kinsim_lite.make_world(seed); start pose (0, 0, 0)."""
    a = ks.ARENA
    square = [(a["x0"], a["y0"]), (a["x1"], a["y0"]), (a["x1"], a["y1"]), (a["x0"], a["y1"])]
    world = ks.make_world(seed, n_dup=n_dup)
    tags = [dict(t, n=STUDY_NORMALS[t["wall"]], normal_deg=STUDY_NORMAL_DEG[t["wall"]], z_m=None, half_m=None)
            for t in world]
    return {"name": "study-square-s%s" % seed, "kind": "study", "drive_polygon": square, "walls_polygon": square,
            "obstacles": [], "tags": tags, "world": world, "arena": dict(a),
            "start_pose_world": {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}}


def load_world(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def room_scene(world, start_pose=None, drive_inset_m=0.0):
    """A scene from a bm.world/1 document with arena.drive_polygon_m (and optionally arena.polygon_m and
    arena.obstacles), moved into the map frame of `start_pose` (default: the document's start_pose).
    drive_inset_m shrinks the driving area by that margin on every side (a taped line or a geofence inside it)."""
    if isinstance(world, (str, os.PathLike)):
        world = load_world(world)
    arena = world["arena"]
    start = {k: float((start_pose or world["start_pose"])[k]) for k in ("x_m", "y_m", "theta_deg")}
    drive_w = [tuple(p) for p in arena.get("drive_polygon_m") or arena.get("polygon_m") or []]
    if not drive_w:
        w, h = arena["size_m"]
        drive_w = [(0.0, 0.0), (w, 0.0), (w, h), (0.0, h)]
    walls_w = [tuple(p) for p in arena.get("polygon_m") or drive_w]
    if drive_inset_m:
        drive_w = inset_polygon(drive_w, drive_inset_m)
    for name, poly in (("drive polygon", drive_w), ("walls polygon", walls_w)):
        if not is_convex_ccw(poly):
            raise ValueError("the %s must be convex and counter-clockwise" % name)
    if inside_depth(drive_w, (start["x_m"], start["y_m"])) <= 0:
        raise ValueError("start pose (%.2f, %.2f) is outside the driving area" % (start["x_m"], start["y_m"]))
    mp = lambda poly: [to_map(start, x, y) for x, y in poly]
    tags, out = [], []
    for i, t in enumerate(world["tags"]):
        x, y = to_map(start, t["x_m"], t["y_m"])
        nd = g.wrap_deg(t["normal_deg"] - start["theta_deg"])
        tag = {"tag": i, "id": t["id"], "x_m": round(x, 4), "y_m": round(y, 4), "wall": t["wall"], "uid": t["uid"],
               "normal_deg": round(nd, 2)}
        out.append(dict(tag))
        tags.append(dict(tag, n=(math.cos(math.radians(nd)), math.sin(math.radians(nd))), z_m=t["z_m"],
                         half_m=t["black_size_m"] / 2))
    return {"name": world["world_id"], "kind": "room", "drive_polygon": mp(drive_w), "walls_polygon": mp(walls_w),
            "obstacles": [{"name": o["name"], "polygon": mp(o["polygon_m"]), "occludes": o.get("occludes", True)}
                          for o in arena.get("obstacles") or []],
            "tags": tags, "world": out, "start_pose_world": start,
            "arena": {"world_id": world["world_id"], "frame": "map (start pose at the origin)",
                      "drive_polygon_m": [[round(v, 4) for v in p] for p in mp(drive_w)],
                      "polygon_m": [[round(v, 4) for v in p] for p in mp(walls_w)], "start_pose_world": start}}


# ---------------------------------------------------------------- sensing

def to_base(pose, x, y):
    """A map-frame point in the car's base_link axes (x forward, y left) at `pose`."""
    th = math.radians(pose["theta_deg"])
    dx, dy = x - pose["x_m"], y - pose["y_m"]
    return dx * math.cos(th) + dy * math.sin(th), -dx * math.sin(th) + dy * math.cos(th)


def camera_position(pose, camera):
    """The lens in the map frame."""
    th = math.radians(pose["theta_deg"])
    return (pose["x_m"] + camera.x_m * math.cos(th) - camera.y_m * math.sin(th),
            pose["y_m"] + camera.x_m * math.sin(th) + camera.y_m * math.cos(th))


def tag_in_picture(pose, camera, tag, margin_px=2.0):
    """All four corners of the tag's black square project inside the picture (camera_model, with distortion)."""
    bx, by = to_base(pose, tag["x_m"], tag["y_m"])
    facing = tag["normal_deg"] - pose["theta_deg"]
    for corner in cm.square_corners_base((bx, by, tag["z_m"]), facing, tag["half_m"]):
        try:
            u, v = camera.project_base(corner)
        except ValueError:
            return False
        if not camera.in_image(u, v, margin_px):
            return False
    return True


def visible(scene, pose, tag, noise):
    """Every visibility test but the random drop-out. Returns (range_m, bearing_deg) from the pose point (C1), or None."""
    o = g.predict_observation(pose, tag)
    r, b = o["range_m"], o["bearing_deg"]
    if noise.get("camera") is None:
        if abs(b) > noise["hfov_deg"] / 2 or not noise["min_range_m"] <= r <= noise["max_range_m"]:
            return None
        ex, ey = pose["x_m"], pose["y_m"]
    else:
        camera = camera_of(noise["camera"])
        if not noise["min_range_m"] <= r <= noise["max_range_m"] or not tag_in_picture(pose, camera, tag,
                                                                                       noise["margin_px"]):
            return None
        ex, ey = camera_position(pose, camera)
    dx, dy = ex - tag["x_m"], ey - tag["y_m"]
    dist = math.hypot(dx, dy)
    inc = math.degrees(math.acos(max(-1.0, min(1.0, (dx * tag["n"][0] + dy * tag["n"][1]) / dist))))
    if inc > noise["max_incidence_deg"]:
        return None
    for ob in scene["obstacles"]:
        if ob["occludes"] and segment_hits_polygon((ex, ey), (tag["x_m"], tag["y_m"]), ob["polygon"]):
            return None
    return r, b


def session_errors(noise, seed):
    """The calibration errors that stay the same for one episode: {"scale": s, "offset_m": o}, drawn from the
    stream "calib-<seed>" (not the noise stream, so the study configuration's draws are untouched)."""
    if not (noise["range_scale_sigma"] or noise["range_offset_sigma_m"]):
        return {"scale": 0.0, "offset_m": 0.0}
    rng = random.Random("calib-%s" % seed)
    return {"scale": rng.gauss(0.0, noise["range_scale_sigma"]), "offset_m": rng.gauss(0.0, noise["range_offset_sigma_m"])}


def detect(scene, pose, rng, noise, session=None):
    """kinsim_lite.detect for a scene: the same draws in the same order for each visible tag."""
    out = []
    for t in scene["tags"]:
        rb = visible(scene, pose, t, noise)
        if rb is None:
            continue
        r, b = rb
        if rng.random() > noise["p_detect"]:
            continue
        sigma = noise["range_sigma_a_m"] + noise["range_sigma_b"] * r
        if noise["range_sigma_c"]:
            sigma += noise["range_sigma_c"] * r * r
        rn = r + rng.gauss(0.0, sigma)
        bn = b + rng.gauss(0.0, noise["bearing_sigma_deg"])
        if noise["range_bias_frac"]:
            rn += noise["range_bias_frac"] * r
        if session and (session["scale"] or session["offset_m"]):
            rn += session["scale"] * r + session["offset_m"]
        if noise["bearing_bias_deg"]:
            bn += noise["bearing_bias_deg"]
        out.append({"id": t["id"], "range_m": round(rn, 2), "bearing_deg": round(bn, 1),
                    "quality": noise["quality"], "_tag": t["tag"]})
    for i, d in enumerate(out):
        d["det"] = i
    return out


def wall_distance_ahead(scene, pose):
    return ray_exit_distance(scene["drive_polygon"], pose["x_m"], pose["y_m"], pose["theta_deg"])


def forward_allowed(scene, pose, wall_limit_m=ks.WALL_LIMIT_M):
    """The validator's rule: a forward move is allowed when it leaves >= wall_limit_m to the driving area's edge."""
    d = wall_distance_ahead(scene, pose)
    return [m for m, step in (("FORWARD_25", 0.25), ("FORWARD_10", 0.10)) if d - step >= wall_limit_m]


def default_footprint():
    """The car's plan-view corner points from configs/car.json (axle midpoint frame), or None if unreadable."""
    try:
        with open(beaconmind.course_root() / "configs" / "car.json", encoding="utf-8") as fh:
            return [tuple(p) for p in json.load(fh)["values"]["corners"]["value"]]
    except (OSError, KeyError, ValueError):
        return None


def clearance(scene, pose, footprint):
    """{wall_m: smallest distance from a footprint corner to a wall (negative = through it), obstacle_m: to an
    obstacle (0 = inside one), drive_m: the pose point's depth inside the driving area (negative = outside)}."""
    th = math.radians(pose["theta_deg"])
    pts = [(pose["x_m"] + x * math.cos(th) - y * math.sin(th), pose["y_m"] + x * math.sin(th) + y * math.cos(th))
           for x, y in footprint or [(0.0, 0.0)]]
    obs = [polygon_distance(o["polygon"], p) for o in scene["obstacles"] for p in pts]
    return {"wall_m": round(min(inside_depth(scene["walls_polygon"], p) for p in pts), 3),
            "obstacle_m": round(min(obs), 3) if obs else None,
            "drive_m": round(inside_depth(scene["drive_polygon"], (pose["x_m"], pose["y_m"])), 3)}


# ---------------------------------------------------------------- the environment

class KinSimEnv:
    """One episode's world, truth and noise. See the module docstring for the interface."""

    MOVES = MOVES

    def __init__(self, scene, noise=None, odometry="study", odo_bias=0.0, steps_budget=ks.STEPS_BUDGET,
                 wall_limit_m=ks.WALL_LIMIT_M, footprint="car"):
        self.scene = scene
        self.noise = dict(noise) if noise else preset("study")
        self.carpet = dict(CARPET) if odometry == "carpet" else (dict(odometry) if isinstance(odometry, dict) else None)
        if odometry not in ("study", "carpet") and not isinstance(odometry, dict):
            raise ValueError("odometry must be 'study', 'carpet' or a dict like CARPET")
        self.odo_bias = odo_bias
        self.steps_budget = steps_budget
        self.wall_limit_m = wall_limit_m
        self.footprint = default_footprint() if footprint == "car" else footprint
        self.world = scene["world"]
        self.seed = None

    @classmethod
    def study(cls, world_seed, n_dup=3, odo_bias=0.0, **kw):
        """The study's square arena and placeholder noise: kinsim_lite's episode for this seed."""
        return cls(study_scene(world_seed, n_dup=n_dup), preset("study"), odo_bias=odo_bias, **kw)

    @classmethod
    def room(cls, world, start_pose=None, preset_name="camera", max_range_m=2.0, odometry="study",
             noise_overrides=None, drive_inset_m=0.0, **kw):
        """A world file (path or document) with a polygon arena. preset_name: "study" or "camera". noise_overrides:
        noise keys to change (e.g. {"bearing_bias_deg": 2.0}). drive_inset_m: see room_scene. Other keywords go to
        the constructor (odo_bias, steps_budget, wall_limit_m, footprint)."""
        if isinstance(world, (str, os.PathLike)):
            world = load_world(world)
        black = min(t["black_size_m"] for t in world["tags"])
        return cls(room_scene(world, start_pose, drive_inset_m),
                   preset(preset_name, max_range_m=max_range_m, tag_black_m=black, **(noise_overrides or {})),
                   odometry=odometry, **kw)

    # -- episode

    def reset(self, seed):
        self.seed = seed
        self.rng = random.Random("noise-%s" % seed)
        self.session = session_errors(self.noise, seed)
        self.truth = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
        self.step_index = 0
        self.odometer, self.travel, self.turns = 0.0, 0.0, 0
        self.last_forward_m = 0.0
        self._odo, self._last_move = None, None
        return self._observe()

    @property
    def steps_left(self):
        return self.steps_budget - self.step_index

    def truth_pose(self):
        """Ground truth in the map frame. For scoring only."""
        return dict(self.truth)

    def truth_pose_world(self):
        return to_world(self.scene["start_pose_world"], self.truth)

    def _observe(self):
        dets = detect(self.scene, self.truth, self.rng, self.noise, self.session)
        last = self._last_move
        safety = {"forward_allowed": forward_allowed(self.scene, self.truth, self.wall_limit_m),
                  "backward_allowed": bool(last and last["result"] == "done" and last["action"].startswith("FORWARD")),
                  "turn_allowed": True, "scan_allowed": True}
        self.info = clearance(self.scene, self.truth, self.footprint)
        self.raw = {"step": self.step_index, "odometry": self._odo, "last_move": dict(last) if last else None,
                    "counters": dict(ks.counters_from(self.odometer, self.travel, self.turns),
                                     steps_left=self.steps_left),
                    "safety": safety, "detections": dets}
        return self.raw

    def observe(self, pose_source=None):
        """A step in which the agent makes no move (NONE, ASK, STOPPED...): the next raw record from the unchanged
        true pose, with zero odometry, last_move None, new detection draws and the safety block recomputed. It
        uses up one step (step_index + 1, steps_left - 1), like every other record after the first, and is
        deterministic given the seed and the sequence of step()/observe() calls. pose_source as in step()."""
        if self.seed is None:
            raise RuntimeError("call reset(seed) first")
        if pose_source in ks.FIX_SOURCES:
            self.travel, self.turns = 0.0, 0
        self._odo = {"forward_m": 0.0, "left_m": 0.0, "dtheta_deg": 0.0}
        self._last_move = None
        self.step_index += 1
        return self._observe()

    def step(self, move, pose_source=None):
        if self.seed is None:
            raise RuntimeError("call reset(seed) first")
        if move not in MOVES:
            raise ValueError("not a move: %r (moves: %s)" % (move, ", ".join(MOVES)))
        if pose_source in ks.FIX_SOURCES:
            self.travel, self.turns = 0.0, 0
        safety = self.raw["safety"]
        allowed = (move in safety["forward_allowed"] if move in FORWARD_STEP_M
                   else safety["backward_allowed"] if move == "BACKWARD_10" else safety["turn_allowed"])
        rng, n = self.rng, self.noise
        if not allowed:
            self._odo = {"forward_m": 0.0, "left_m": 0.0, "dtheta_deg": 0.0}
            self._last_move = {"action": move, "result": "refused"}
        elif move in TURN_DEG:
            dth = TURN_DEG[move]
            if self.carpet is None:
                self.truth = g.compose_odometry(self.truth, 0.0, 0.0, dth)
                meas = dth * (1 + self.odo_bias) + rng.gauss(0.0, n["gyro_sigma_deg"])
            else:
                true = dth * self.carpet["turn_scale"] + rng.gauss(0.0, self.carpet["turn_sigma_deg"])
                self.truth = g.compose_odometry(self.truth, 0.0, 0.0, true)
                meas = true * (1 + self.odo_bias) + rng.gauss(0.0, n["gyro_sigma_deg"])
            self.turns += 1
            self._odo = {"forward_m": 0.0, "left_m": 0.0, "dtheta_deg": round(meas, 1)}
            self._last_move = {"action": move, "result": "done"}
        else:
            f = FORWARD_STEP_M[move] if move in FORWARD_STEP_M else -min(BACKWARD_STEP_M, self.last_forward_m)
            if self.carpet is None:
                self.truth = g.compose_odometry(self.truth, f, 0.0, 0.0)
                fm = round(f * (1 + self.odo_bias + rng.gauss(0.0, n["wheel_scale_sigma"])), 2)
                self._odo = {"forward_m": fm, "left_m": 0.0, "dtheta_deg": 0.0}
            else:
                # an arc of length f that turns by the veer; the chord at mid-heading (plan C1)
                veer = self.carpet["veer_deg_per_m"] * abs(f)
                dth = veer + rng.gauss(0.0, self.carpet["veer_sigma_frac"] * veer)
                half = math.radians(dth) / 2
                chord = f * (math.sin(half) / half if half else 1.0)
                self.truth = g.compose_odometry(self.truth, chord * math.cos(half), chord * math.sin(half), dth)
                scale = 1 + self.odo_bias + rng.gauss(0.0, n["wheel_scale_sigma"])
                dm = dth * (1 + self.odo_bias) + rng.gauss(0.0, n["gyro_sigma_deg"])
                hm = math.radians(dm) / 2
                cm = f * scale * (math.sin(hm) / hm if hm else 1.0)
                fm = round(cm * math.cos(hm), 2)
                self._odo = {"forward_m": fm, "left_m": round(cm * math.sin(hm), 2), "dtheta_deg": round(dm, 1)}
            self.odometer += abs(fm)
            self.travel += abs(fm)
            self.last_forward_m = f if f > 0 else 0.0
            self._last_move = {"action": move, "result": "done"}
        self.step_index += 1
        return self._observe()


# ---------------------------------------------------------------- the coded procedure B2 on one record, and an episode

def b2_step(raw, prev_report):
    """kinsim_lite's B2 on one raw step record: (report, calls, est). The body of kinsim_lite.run_episode's loop."""
    est = ks.estimate_step(raw, prev_report)
    mem = ks.initial_memory() if prev_report is None else prev_report["memory"]
    decision, m2 = ks.decide_step(est, mem, raw["safety"], raw["counters"]["steps_left"])
    for e in est["new_entries"]:
        e["first_seen_scan"] = m2["scan_index"]
    report = {"step": raw["step"], "mode": "closed_loop", "mission": "EXPLORE", "pose": ks.rp(est["pose"]),
              "pose_source": est["pose_source"],
              "associations": [{k: v for k, v in a.items() if k != "conflict"} for a, _ in est["assoc"]],
              "loop_closure": est["loop_closure"], "map": est["new_map"], "memory": m2, "decision": decision,
              "move_result": "done" if decision.startswith(("FORWARD", "TURN", "BACKWARD")) else "not_called",
              "requested_mission": None, "message": None, "note": None}
    return report, [[n, a] for n, a in est["calls"]], est


# What a real-run design-value file would hold once the tag pilot has measured the detector: the DV noise model that
# fix_pose's conditioning test uses (configs/dv.json: range 0.05 + 0.05 r m, bearing 2.0 deg, written for the 1.5 m
# arena before any camera existed), set to the simulated estimate of evidence/M1/M1.T8/sim-estimate.md rounded up
# (range about 0.007 + 0.011 r m; bearing 0.3 deg plus what is left of the yaw error after the pilot, about 0.4 deg).
MEASURED_SIGMA_DV = {"sigma_range_a_m": 0.01, "sigma_range_b_per_m": 0.012, "sigma_bearing_deg": 0.5}


@contextlib.contextmanager
def dv_override(**values):
    """Rehearsal only: run the frozen procedure with other design values WITHOUT editing configs/dv.json or any
    frozen file. kinsim_lite and geometry read their thresholds through beaconmind.dv.load_dv(), which caches the
    parsed file per path; inside this block the cached values of the default file are replaced, and restored on
    exit (also after an exception). Unknown keys are refused. Not thread-safe; nothing outside the block sees it."""
    from beaconmind import dv as dvm
    dvm.load_dv()
    key = str(dvm._resolve(None))
    saved = dvm._CACHE[key]
    unknown = set(values) - set(saved)
    if unknown:
        raise KeyError("not design values: %s" % sorted(unknown))
    dvm._CACHE[key] = dict(saved, **values)
    try:
        yield
    finally:
        dvm._CACHE[key] = saved


DEAD_END = "E5 leg with no forward move and no E4"     # the branch kinsim_lite.decide_step leaves unimplemented


def make_b2_policy(dead_end="block", patience=2):
    """The coded procedure with the two things a room needs made explicit. Both wrap the frozen kinsim_lite code;
    make_b2_policy(dead_end="raise", patience=2) is b2_step itself, and with the defaults the result differs from
    b2_step only on steps where b2_step would raise.

    dead_end="block": D7's E5 picks the top-score sector; when the car already faces it and no forward move is
    allowed, E3 ends the leg and, unless a scan is due (E4), E5 picks the same sector again. The written procedure
    loops there and kinsim_lite raises NotImplementedError. In the square that is rare (sectors towards a wall hold a
    mapped tag, so exploration_summary blocks them); in the room the driving area has edges with no tag in view
    (the desk-front line, walls beyond the range limit or inside the camera's near cut-off), so it is common. Here the
    step is decided again with memory.blocked_heading_deg set to the car's heading, which is what rule 7b does after a
    bump: exploration_summary then blocks the sectors within near_blocked_deg of it and E5 takes the next one. Rule
    7's own reset is applied too: a completed forward move clears blocked_heading_deg (kinsim_lite never needed
    it because nothing there ever sets the field).

    patience: E1 ends EXPLORE after 2 scans in a row without a new tag. `patience` > 2 asks for that many instead
    (the memory keeps the true count; the frozen decide_step is shown min(count, 1) until the count reaches
    `patience`). 2 is the procedure as written and as the LLM's prompt states it."""
    if dead_end not in ("block", "raise"):
        raise ValueError("dead_end must be 'block' or 'raise'")

    def policy(raw, prev_report):
        prev = prev_report
        if prev is not None:
            mem = dict(prev["memory"])
            last = raw["last_move"]
            if dead_end == "block" and last and last["result"] == "done" and last["action"].startswith("FORWARD"):
                mem["blocked_heading_deg"] = None
            true_count = mem["scans_without_new"]
            shown = true_count if true_count >= patience or patience <= 2 else min(true_count, 1)
            mem["scans_without_new"] = shown
            prev = dict(prev, memory=mem)
        try:
            report, calls, est = b2_step(raw, prev)
        except NotImplementedError as exc:
            if dead_end != "block" or str(exc) != DEAD_END or prev is None:
                raise
            heading = ks.rp(ks.estimate_step(raw, prev)["pose"])["theta_deg"]      # this step's estimate, as rule 7b's theta
            blocked = dict(prev, memory=dict(prev["memory"], blocked_heading_deg=heading))
            report, calls, est = b2_step(raw, blocked)
        if prev is not None:
            out = report["memory"]["scans_without_new"]
            report["memory"]["scans_without_new"] = (0 if out == 0 else true_count + 1 if out == shown + 1
                                                     else true_count)
        return report, calls, est
    return policy


def run_episode(env, seed, max_steps=None, policy=b2_step):
    """A closed-loop EXPLORE episode driven by `policy` (default: B2). Returns kinsim_lite's episode document
    {"seed", "world", "records"} plus "ended_by" ("DONE", "budget" or "not_implemented: <branch>"), "info" (one
    clearance record per step), "noise", "arena" and "scene". Records: {step, truth, raw, report, calls}."""
    max_steps = env.steps_budget if max_steps is None else max_steps
    raw = env.reset(seed)
    prev_report, records, infos, ended = None, [], [], "budget"
    for step in range(max_steps):
        try:
            report, calls, _ = policy(raw, prev_report)
        except NotImplementedError as exc:
            ended = "not_implemented: %s" % exc
            break
        records.append({"step": step, "truth": env.truth_pose(), "raw": raw, "report": report, "calls": calls})
        infos.append(dict(env.info))
        if report["decision"] == "DONE":
            ended = "DONE"
            break
        if step == max_steps - 1:
            break
        raw = env.step(report["decision"], report["pose_source"])
        prev_report = report
    noise = dict(env.noise, odo_bias=env.odo_bias, carpet=env.carpet, session=env.session)
    return {"seed": seed, "world": env.world, "records": records, "ended_by": ended, "info": infos, "noise": noise,
            "arena": env.scene["arena"],
            "scene": {"name": env.scene["name"], "kind": env.scene["kind"],
                      "start_pose_world": env.scene["start_pose_world"],
                      "obstacles": [{"name": o["name"], "polygon_m": [[round(v, 4) for v in p] for p in o["polygon"]]}
                                    for o in env.scene["obstacles"]]}}
