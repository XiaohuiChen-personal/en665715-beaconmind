"""The room simulator (envs/kinsim_room.py), the room's world file (tools/room_world.py) and the rehearsal metrics.

The equivalence tests are the guard on the frozen study: configured as the 2.25 m square with the study preset, the
simulator must reproduce kinsim_lite.run_episode's records exactly.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote these tests.
"""
import copy
import importlib.util
import json
import math
import random
from pathlib import Path

import pytest

from beaconmind import course_root
from beaconmind import camera_model as cm
from beaconmind import geometry as g
from beaconmind.envs import kinsim_lite as ks
from beaconmind.envs import kinsim_room as kr
from beaconmind.schemas import validate

ROOT = course_root()
WORLD = ROOT / "configs" / "arenas" / "real-room-nominal.json"
SCENARIOS = ROOT / "configs" / "arenas" / "real-room-scenarios.json"
LAYOUT = ROOT / "evidence" / "M3" / "M3.T10" / "layout" / "layout.json"


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def world():
    return json.loads(WORLD.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def scenarios():
    return {s["id"]: s["start_pose"] for s in json.loads(SCENARIOS.read_text(encoding="utf-8"))["scenarios"]}


def room_frame_scene(world, **noise):
    """A scene whose map frame is the room frame shifted to (2, 2): poses are then easy to write by hand."""
    return kr.room_scene(world, {"x_m": 2.0, "y_m": 2.0, "theta_deg": 0.0})


def at(x, y, th):
    """A map-frame pose for the scene above from room-frame coordinates."""
    return {"x_m": x - 2.0, "y_m": y - 2.0, "theta_deg": th}


# ---------------------------------------------------------------- the frozen study is reproduced

@pytest.mark.parametrize("seed", list(range(2000, 2030)) + [1000, 1001, 1002])
def test_study_square_reproduces_kinsim_lite(seed):
    try:
        want = ks.run_episode(seed)
    except NotImplementedError as exc:
        got = kr.run_episode(kr.KinSimEnv.study(seed), seed)
        assert got["ended_by"] == "not_implemented: %s" % exc
        return
    got = kr.run_episode(kr.KinSimEnv.study(seed), seed)
    assert got["seed"] == want["seed"] and got["world"] == want["world"]
    assert len(got["records"]) == len(want["records"]) >= 20
    for a, b in zip(got["records"], want["records"]):
        assert a == b                                   # truth, raw observation, B2's report and its tool calls
    assert json.dumps(got["records"], sort_keys=True) == json.dumps(want["records"], sort_keys=True)
    assert got["ended_by"] == ("DONE" if want["records"][-1]["report"]["decision"] == "DONE" else "budget")


def test_study_square_reproduces_the_drift_condition_and_short_budgets():
    want = ks.run_episode(2003, odo_bias=0.02)
    got = kr.run_episode(kr.KinSimEnv.study(2003, odo_bias=0.02), 2003)
    assert got["records"] == want["records"]
    assert got["records"] != ks.run_episode(2003)["records"]            # the comparison can fail
    short = kr.run_episode(kr.KinSimEnv.study(2004), 2004, max_steps=17)
    assert short["records"] == ks.run_episode(2004, max_steps=17)["records"] and short["ended_by"] == "budget"
    two_dups = kr.run_episode(kr.KinSimEnv.study(2005, n_dup=1), 2005)
    assert two_dups["records"] == ks.run_episode(2005, n_dup=1)["records"]


def test_the_equivalence_is_sensitive_to_every_part_of_the_model():
    want = ks.run_episode(2001)["records"]
    for change in ({"max_range_m": 1.4}, {"hfov_deg": 58.0}, {"range_sigma_b": 0.031}, {"p_detect": 0.9},
                   {"gyro_sigma_deg": 0.31}, {"max_incidence_deg": 55.0}):
        env = kr.KinSimEnv(kr.study_scene(2001), kr.preset("study", **change))
        assert kr.run_episode(env, 2001)["records"] != want, change
    assert kr.run_episode(kr.KinSimEnv.study(2001, wall_limit_m=0.45), 2001)["records"] != want


def test_square_wall_distance_is_kinsim_lites_to_the_last_bit():
    scene = kr.study_scene(2000)
    rng = random.Random(7)
    for _ in range(2000):
        pose = {"x_m": rng.uniform(-0.99, 1.24), "y_m": rng.uniform(-0.99, 1.24),
                "theta_deg": rng.choice([rng.uniform(-180, 180), 30.0 * rng.randrange(12)])}
        assert kr.wall_distance_ahead(scene, pose) == ks.wall_distance_ahead(pose)
        assert kr.forward_allowed(scene, pose) == ks.forward_allowed(pose)


def test_default_policy_is_b2_where_b2_runs():
    for seed in (2000, 2007, 2019):
        want = ks.run_episode(seed)["records"]
        assert kr.run_episode(kr.KinSimEnv.study(seed), seed, policy=kr.make_b2_policy())["records"] == want
        assert kr.run_episode(kr.KinSimEnv.study(seed), seed, policy=kr.make_b2_policy("raise", 2))["records"] == want


# ---------------------------------------------------------------- polygon geometry

def line_hit(p, th, a, b):
    """Independent check: solve p + t d = a + s (b - a) by Cramer's rule; returns t."""
    dx, dy = math.cos(math.radians(th)), math.sin(math.radians(th))
    ex, ey = b[0] - a[0], b[1] - a[1]
    det = dx * (-ey) - dy * (-ex)
    return ((a[0] - p[0]) * (-ey) - (a[1] - p[1]) * (-ex)) / det


def test_wall_distance_at_the_desk_front_line_and_the_cut_corner(world):
    drive = [tuple(p) for p in world["arena"]["drive_polygon_m"]]
    assert kr.is_convex_ccw(drive) and len(drive) == 5
    # the desk-front line x = 0.66, not the desk wall at x = 0
    assert kr.ray_exit_distance(drive, 1.66, 3.0, 180.0) == pytest.approx(1.0, abs=1e-9)
    # the 45 degree cut between corner 4 and corner 3
    c4, c3 = tuple(world["arena"]["polygon_m"][1]), tuple(world["arena"]["polygon_m"][2])
    for th in (-45.0, -30.0, -60.0, 0.0, -90.0):
        want = line_hit((3.0, 1.2), th, c4, c3)
        got = kr.ray_exit_distance(drive, 3.0, 1.2, th)
        if th in (-45.0, -30.0, -60.0):
            assert got == pytest.approx(want, abs=1e-9)
            assert got < min((3.824 - 3.0) / math.cos(math.radians(th)), (1.2 - 0.088) / -math.sin(math.radians(th)))
    # heading -45 deg is square to the cut within 0.3 deg: the distance is the point's distance to that wall's line
    ex, ey = c3[0] - c4[0], c3[1] - c4[1]
    perp = abs((3.0 - c4[0]) * ey - (1.2 - c4[1]) * ex) / math.hypot(ex, ey)
    assert perp == pytest.approx(0.7547, abs=0.0005)
    assert kr.ray_exit_distance(drive, 3.0, 1.2, -45.0) == pytest.approx(perp, abs=1e-4)
    # heading east the ray leaves through the window wall, heading south-west through the 295 cm wall
    assert kr.ray_exit_distance(drive, 3.0, 3.0, 0.0) == pytest.approx(line_hit((3.0, 3.0), 0.0, drive[2], drive[3]), abs=1e-9)
    assert kr.ray_exit_distance(drive, 2.0, 1.0, -90.0) == pytest.approx(line_hit((2.0, 1.0), -90.0, drive[0], drive[1]), abs=1e-9)


def test_forward_allowed_follows_the_wall_limit_in_the_room(world):
    scene = room_frame_scene(world)
    # facing the desk-front line: 0.66 + 0.35 + 0.25 = 1.26 for the long step, 0.66 + 0.35 + 0.10 = 1.11 for the short
    assert kr.forward_allowed(scene, at(1.30, 3.0, 180.0)) == ["FORWARD_25", "FORWARD_10"]
    assert kr.forward_allowed(scene, at(1.20, 3.0, 180.0)) == ["FORWARD_10"]
    assert kr.forward_allowed(scene, at(1.05, 3.0, 180.0)) == []
    assert kr.forward_allowed(scene, at(1.05, 3.0, 0.0)) == ["FORWARD_25", "FORWARD_10"]
    # facing the cut corner squarely: 0.755 m away both steps fit, 0.543 m only the short one, 0.330 m none
    assert kr.forward_allowed(scene, at(3.0, 1.2, -45.0)) == ["FORWARD_25", "FORWARD_10"]
    assert kr.wall_distance_ahead(scene, at(3.15, 1.05, -45.0)) == pytest.approx(0.5426, abs=0.001)
    assert kr.forward_allowed(scene, at(3.15, 1.05, -45.0)) == ["FORWARD_10"]
    assert kr.wall_distance_ahead(scene, at(3.3, 0.9, -45.0)) == pytest.approx(0.3305, abs=0.001)
    assert kr.forward_allowed(scene, at(3.3, 0.9, -45.0)) == []
    assert kr.forward_allowed(scene, at(3.15, 1.05, -45.0), wall_limit_m=0.20) == ["FORWARD_25", "FORWARD_10"]
    # without the cut the same pose would have 0.67 m to the window wall and 0.96 m to the 295 cm wall
    assert kr.forward_allowed(scene, at(3.15, 1.05, 0.0)) == ["FORWARD_25", "FORWARD_10"]


def test_wall_distance_does_not_depend_on_the_start_pose(world, scenarios):
    drive = [tuple(p) for p in world["arena"]["drive_polygon_m"]]
    for start in scenarios.values():
        scene = kr.room_scene(world, start)
        want = kr.ray_exit_distance(drive, start["x_m"], start["y_m"], start["theta_deg"])
        assert kr.wall_distance_ahead(scene, {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}) == pytest.approx(want, abs=1e-9)
        for t, wt in zip(scene["tags"], world["tags"]):       # ranges and normals survive the change of frame
            assert math.hypot(t["x_m"], t["y_m"]) == pytest.approx(
                math.hypot(wt["x_m"] - start["x_m"], wt["y_m"] - start["y_m"]), abs=1e-3)
            back = kr.to_world(start, {"x_m": t["x_m"], "y_m": t["y_m"], "theta_deg": t["normal_deg"]})
            assert (back["x_m"], back["y_m"]) == pytest.approx((wt["x_m"], wt["y_m"]), abs=1e-3)
            assert abs(g.wrap_deg(back["theta_deg"] - wt["normal_deg"])) < 0.02


def test_a_pose_outside_the_driving_area_may_only_drive_back_in(world):
    drive = [tuple(p) for p in world["arena"]["drive_polygon_m"]]
    assert kr.inside_depth(drive, (0.5, 3.0)) == pytest.approx(-0.16, abs=1e-9)
    assert kr.ray_exit_distance(drive, 0.5, 3.0, 180.0) == 0.0
    assert kr.ray_exit_distance(drive, 0.5, 3.0, 90.0) == 0.0
    assert kr.ray_exit_distance(drive, 0.5, 3.0, 0.0) == pytest.approx(3.816 - 0.5, abs=0.01)


def test_inset_polygon_and_start_pose_checks(world):
    sq = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]
    assert kr.inset_polygon(sq, 0.5) == pytest.approx([(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5)])
    drive = [tuple(p) for p in world["arena"]["drive_polygon_m"]]
    inner = kr.inset_polygon(drive, 0.4)
    assert all(kr.inside_depth(drive, p) == pytest.approx(0.4, abs=1e-9) for p in inner)
    with pytest.raises(ValueError):
        kr.inset_polygon(sq, 1.2)
    with pytest.raises(ValueError, match="outside the driving area"):
        kr.room_scene(world, {"x_m": 0.3, "y_m": 3.0, "theta_deg": 0.0})           # on the desk
    with pytest.raises(ValueError, match="outside the driving area"):
        kr.room_scene(world, {"x_m": 0.9, "y_m": 3.0, "theta_deg": 0.0}, drive_inset_m=0.4)


def test_segment_and_polygon_helpers():
    box = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    assert kr.segment_hits_polygon((-1.0, 0.5), (2.0, 0.5), box)
    assert kr.segment_hits_polygon((0.5, 0.5), (0.6, 0.6), box)
    assert not kr.segment_hits_polygon((-1.0, 1.5), (2.0, 1.5), box)
    assert not kr.segment_hits_polygon((-1.0, 0.5), (-0.1, 0.5), box)
    assert kr.polygon_distance(box, (0.5, 0.5)) == 0.0
    assert kr.polygon_distance(box, (2.0, 2.0)) == pytest.approx(math.sqrt(2))
    assert not kr.is_convex_ccw(list(reversed(box)))


# ---------------------------------------------------------------- visibility

def one_tag(x, y, normal_deg, z=0.23):
    n = (math.cos(math.radians(normal_deg)), math.sin(math.radians(normal_deg)))
    return {"tag": 0, "id": 1, "x_m": x, "y_m": y, "wall": "w", "normal_deg": normal_deg, "n": n, "z_m": z,
            "half_m": 0.08}


def open_scene(tag, obstacles=()):
    return {"tags": [tag], "obstacles": list(obstacles)}


ORIGIN = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}


def polar_tag(r, bearing_deg, turn_deg=0.0):
    """A tag at range and bearing from the origin, facing the origin, turned by turn_deg about the vertical."""
    x, y = r * math.cos(math.radians(bearing_deg)), r * math.sin(math.radians(bearing_deg))
    return one_tag(x, y, bearing_deg + 180.0 + turn_deg)


def test_field_of_view_range_and_incidence_with_the_study_preset():
    n = kr.preset("study", max_range_m=2.0)
    assert n["hfov_deg"] == 60.0 and n["camera"] is None
    seen = lambda tag: kr.visible(open_scene(tag), ORIGIN, tag, n) is not None
    assert seen(polar_tag(1.0, 29.0)) and seen(polar_tag(1.0, -29.0))
    assert not seen(polar_tag(1.0, 31.0)) and not seen(polar_tag(1.0, -31.0))
    assert seen(polar_tag(1.99, 0.0)) and not seen(polar_tag(2.01, 0.0))
    assert seen(polar_tag(0.26, 0.0)) and not seen(polar_tag(0.24, 0.0))
    assert seen(polar_tag(1.0, 0.0, 59.0)) and seen(polar_tag(1.0, 0.0, -59.0))
    assert not seen(polar_tag(1.0, 0.0, 61.0)) and not seen(polar_tag(1.0, 0.0, -61.0))
    assert not seen(polar_tag(1.0, 0.0, 180.0))                                        # seen from behind
    r, b = kr.visible(open_scene(polar_tag(1.5, 20.0)), ORIGIN, polar_tag(1.5, 20.0), n)
    assert (r, b) == pytest.approx((1.5, 20.0))


def test_the_measured_camera_sees_less_to_the_side_and_nothing_close():
    """The camera preset's in-view test is beaconmind.camera_model's (distortion and mount angles included)."""
    n = kr.preset("camera", max_range_m=3.0)
    camera = kr.camera_of(n["camera"])
    assert n["hfov_deg"] == pytest.approx(46.86, abs=0.01) and camera.z_m == 0.075 and camera.x_m == 0.12

    def seen(r, bearing, z=0.23, half=0.08, turn=0.0, noise=n):
        tag = dict(polar_tag(r, bearing, turn), z_m=z, half_m=half)
        return kr.visible(open_scene(tag), ORIGIN, tag, noise) is not None

    # near limit: the whole black square, from the axle midpoint (sim-estimate.md finding 1: 0.74 m straight ahead,
    # 0.70 m at 10 deg left, 0.80 m at 10 deg right, 0.81 / 1.09 m at 15 deg left / right)
    for bearing, quoted in ((0.0, 0.74), (10.0, 0.70), (-10.0, 0.80), (15.0, 0.81), (-15.0, 1.09), (5.0, 0.72)):
        limit = cm.min_full_view_range(camera, 0.23, 0.08, bearing)
        assert limit == pytest.approx(quoted, abs=0.006)
        assert seen(limit + 0.01, bearing) and not seen(limit - 0.01, bearing)
    assert not seen(0.60, 0.0) and not seen(0.30, 0.0)
    # a 100 mm tag centred 0.1825 m up is whole from 0.53 m, below done_range_m (0.55 m)
    small = cm.min_full_view_range(camera, 0.1825, 0.05, 0.0)
    assert small == pytest.approx(0.53, abs=0.006) and small < ks.DONE_RANGE_M
    assert seen(small + 0.01, 0.0, z=0.1825, half=0.05) and not seen(small - 0.01, 0.0, z=0.1825, half=0.05)
    # to the side: the true view is 22.4 deg left and 23.9 deg right of an axis that points 2.5 deg left, so a tag
    # at 2 m is whole at 20 deg left and 17 deg right, not at 24 deg either side; the study's 60 deg view has both
    assert seen(2.0, 20.0) and seen(2.0, -17.0) and not seen(2.0, 24.0) and not seen(2.0, -24.0)
    study = kr.preset("study", max_range_m=3.0)
    assert seen(2.0, 24.0, noise=study) and seen(2.0, -24.0, noise=study) and seen(0.30, 0.0, noise=study)
    # range window and incidence still apply
    assert seen(2.99, 0.0) and not seen(3.01, 0.0)
    assert seen(1.5, 0.0, turn=55.0) and not seen(1.5, 0.0, turn=65.0)


def test_in_view_matches_camera_model_in_any_map_frame():
    camera = kr.camera_of(kr.camera_doc())
    rng = random.Random(5)
    agree = inside = 0
    for _ in range(1500):
        r, bearing, turn = rng.uniform(0.4, 3.5), rng.uniform(-30, 30), rng.uniform(-50, 50)
        z, half = rng.choice([(0.23, 0.08), (0.1825, 0.05)])
        want = cm.square_in_view(camera, r, bearing, z, half, margin_px=2.0, incidence_deg=turn)
        # the same view from a car standing anywhere, at any heading
        pose = {"x_m": rng.uniform(-3, 3), "y_m": rng.uniform(-3, 3), "theta_deg": rng.uniform(-180, 180)}
        a = math.radians(pose["theta_deg"] + bearing)
        tag = one_tag(pose["x_m"] + r * math.cos(a), pose["y_m"] + r * math.sin(a),
                      pose["theta_deg"] + bearing + 180.0 + turn, z=z)
        tag["half_m"] = half
        agree += kr.tag_in_picture(pose, camera, tag) == want
        inside += want
    assert agree == 1500 and 300 < inside < 1200
    # the lens is 0.12 m ahead of the axle, on the heading
    assert kr.camera_position({"x_m": 1.0, "y_m": 2.0, "theta_deg": 90.0}, camera) == pytest.approx((1.0, 2.12))
    assert kr.to_base({"x_m": 1.0, "y_m": 2.0, "theta_deg": 90.0}, 1.0, 3.0) == pytest.approx((1.0, 0.0))
    assert kr.to_base({"x_m": 1.0, "y_m": 2.0, "theta_deg": 90.0}, 0.0, 2.0) == pytest.approx((0.0, 1.0))


def test_the_desk_hides_tags_behind_it(world):
    scene = room_frame_scene(world)
    n = kr.preset("study", max_range_m=4.0)
    t09 = next(t for t in scene["tags"] if t["uid"] == "T09")       # doors wall, near corner 1
    t00 = next(t for t in scene["tags"] if t["uid"] == "T00")       # desk wall, entrance side of the desk
    bare = dict(scene, obstacles=[])

    def look(pose_xy, tag, sc):
        th = math.degrees(math.atan2(tag["y_m"] - (pose_xy[1] - 2.0), tag["x_m"] - (pose_xy[0] - 2.0)))
        return kr.visible(sc, at(pose_xy[0], pose_xy[1], th), tag, n)

    assert look((1.0, 2.0), t09, bare) is not None and look((1.0, 2.0), t09, scene) is None     # across the desk
    assert look((1.0, 4.2), t09, scene) is not None                                               # past the desk
    assert look((1.2, 3.0), t00, bare) is not None and look((1.2, 3.0), t00, scene) is None     # across its corner
    assert look((1.2, 1.2), t00, scene) is not None
    assert [o["name"] for o in scene["obstacles"]] == ["desk"]


def test_detect_reports_from_the_axle_and_applies_biases(world, scenarios):
    scene = kr.room_scene(world, scenarios["S1"])
    quiet = dict(range_sigma_a_m=0.0, range_sigma_b=0.0, range_sigma_c=0.0, bearing_sigma_deg=0.0, p_detect=1.0,
                 range_scale_sigma=0.0, range_offset_sigma_m=0.0)
    n = kr.preset("camera", max_range_m=2.5, **quiet)
    pose = {"x_m": 0.0, "y_m": 0.0, "theta_deg": -90.0}                 # S1 turned to face the window wall
    dets = kr.detect(scene, pose, random.Random(1), n)
    assert dets and [d["det"] for d in dets] == list(range(len(dets)))
    for d in dets:
        t = scene["tags"][d["_tag"]]
        o = g.predict_observation(pose, t)
        assert d["range_m"] == round(o["range_m"], 2) and d["bearing_deg"] == round(o["bearing_deg"], 1)
        assert d["id"] == t["id"] and d["quality"] == 0.9
    biased = kr.detect(scene, pose, random.Random(1), dict(n, bearing_bias_deg=2.0, range_bias_frac=-0.01))
    for a, b in zip(dets, biased):
        assert b["bearing_deg"] == pytest.approx(a["bearing_deg"] + 2.0, abs=0.11)
        assert b["range_m"] == pytest.approx(a["range_m"] * 0.99, abs=0.011)
    with pytest.raises(ValueError):
        kr.preset("camera", bogus=1)
    with pytest.raises(ValueError):
        kr.preset("lidar")


def test_camera_noise_preset_carries_the_simulated_estimate(world, scenarios):
    n = kr.preset("camera")
    # per-frame sd from sim-estimate.md finding 2 (160 mm tag): 0.2 mm at 1 m, 1.2 mm at 2 m, 3.3 mm at 3 m (+1 mm floor)
    sigma = lambda r, nn=n: nn["range_sigma_a_m"] + nn["range_sigma_b"] * r + nn["range_sigma_c"] * r * r
    assert sigma(2.0) == pytest.approx(0.0024, abs=0.0005) and sigma(3.0) == pytest.approx(0.0042, abs=0.0005)
    assert n["range_scale_sigma"] == 0.011 and n["range_offset_sigma_m"] == 0.007 and n["bearing_sigma_deg"] == 0.3
    small = kr.preset("camera", tag_black_m=0.10)
    assert small["range_sigma_c"] == pytest.approx(1.6 * n["range_sigma_c"])
    study = kr.preset("study")
    assert {k: study[k] for k in ks.NOISE} == ks.NOISE and study["camera"] is None
    assert study["range_sigma_c"] == study["range_scale_sigma"] == study["range_offset_sigma_m"] == 0.0
    assert n["p_detect"] == ks.NOISE["p_detect"] and n["max_incidence_deg"] == ks.NOISE["max_incidence_deg"]
    assert kr.session_errors(study, 1) == {"scale": 0.0, "offset_m": 0.0}
    # one scale and one offset per episode, the same for every detection of it, different between seeds
    assert kr.session_errors(n, 7) == kr.session_errors(n, 7) != kr.session_errors(n, 8)
    scales = [kr.session_errors(n, s)["scale"] for s in range(400)]
    assert abs(sum(scales) / 400) < 0.002 and math.sqrt(sum(v * v for v in scales) / 400) == pytest.approx(0.011, rel=0.15)
    quiet = dict(range_sigma_a_m=0.0, range_sigma_c=0.0, bearing_sigma_deg=0.0, p_detect=1.0)
    env = kr.KinSimEnv.room(world, scenarios["S1"], preset_name="camera", max_range_m=3.0, noise_overrides=quiet)
    raw = env.reset(4)
    errs = []
    for _ in range(12):
        for d in raw["detections"]:
            true = g.predict_observation(env.truth_pose(), env.scene["tags"][d["_tag"]])["range_m"]
            errs.append((true, d["range_m"] - true))
            assert d["range_m"] == round(true * (1 + env.session["scale"]) + env.session["offset_m"], 2)
        raw = env.step("TURN_LEFT_30")
    assert len(errs) >= 4 and env.session == kr.session_errors(env.noise, 4)
    assert kr.run_episode(env, 4, max_steps=3)["noise"]["session"] == env.session


# ---------------------------------------------------------------- the environment class

def test_environment_interface_on_the_square_and_the_room(world, scenarios):
    for env in (kr.KinSimEnv.study(2000), kr.KinSimEnv.room(world, scenarios["S2"], preset_name="camera")):
        with pytest.raises(RuntimeError):
            env.step("TURN_LEFT_30")
        raw = env.reset(5)
        assert set(raw) == {"step", "odometry", "last_move", "counters", "safety", "detections"}
        assert raw["step"] == 0 and raw["odometry"] is None and raw["last_move"] is None
        assert raw["counters"] == {"odometer_m": 0.0, "travel_since_fix_m": 0.0, "turns_since_fix": 0, "steps_left": 150}
        assert env.truth_pose() == {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
        assert env.MOVES == kr.MOVES and len(env.world) >= 12 and "tag" in env.world[0]
        raw = env.step("TURN_LEFT_30")
        assert raw["step"] == 1 and raw["last_move"] == {"action": "TURN_LEFT_30", "result": "done"}
        assert raw["odometry"]["dtheta_deg"] == pytest.approx(30.0, abs=1.5) and raw["counters"]["turns_since_fix"] == 1
        assert env.truth_pose()["theta_deg"] == pytest.approx(30.0)
        assert not raw["safety"]["backward_allowed"]
        raw = env.step("FORWARD_25")
        assert raw["safety"]["backward_allowed"] and raw["counters"]["odometer_m"] == pytest.approx(0.25, abs=0.03)
        assert math.hypot(env.truth_pose()["x_m"], env.truth_pose()["y_m"]) == pytest.approx(0.25)
        raw = env.step("BACKWARD_10", pose_source="beacon_fix")            # a full fix resets the since-fix counters
        assert raw["odometry"]["forward_m"] == pytest.approx(-0.10, abs=0.02)
        assert raw["counters"]["travel_since_fix_m"] == pytest.approx(0.10, abs=0.02)
        assert raw["counters"]["turns_since_fix"] == 0 and raw["counters"]["steps_left"] == 147
        assert math.hypot(env.truth_pose()["x_m"], env.truth_pose()["y_m"]) == pytest.approx(0.15)
        raw = env.step("BACKWARD_10")                                      # only straight after a forward move
        assert raw["last_move"] == {"action": "BACKWARD_10", "result": "refused"}
        assert raw["odometry"] == {"forward_m": 0.0, "left_m": 0.0, "dtheta_deg": 0.0} and raw["step"] == 4
        with pytest.raises(ValueError):
            env.step("DONE")
        assert set(env.info) == {"wall_m", "obstacle_m", "drive_m"}
        before, counters = env.truth_pose(), dict(raw["counters"])
        raw = env.observe()                                                # a step with no move
        assert raw["step"] == 5 and raw["last_move"] is None and env.truth_pose() == before
        assert raw["odometry"] == {"forward_m": 0.0, "left_m": 0.0, "dtheta_deg": 0.0}
        assert raw["counters"] == dict(counters, steps_left=145) and not raw["safety"]["backward_allowed"]
        assert env.step("TURN_RIGHT_30")["step"] == 6


def test_a_forward_move_into_the_wall_is_refused_and_truth_stays(world):
    env = kr.KinSimEnv.room(world, {"x_m": 1.05, "y_m": 3.0, "theta_deg": 180.0}, preset_name="study")
    raw = env.reset(1)
    assert raw["safety"]["forward_allowed"] == []
    raw = env.step("FORWARD_10")
    assert raw["last_move"]["result"] == "refused" and env.truth_pose() == {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
    assert env.truth_pose_world() == pytest.approx({"x_m": 1.05, "y_m": 3.0, "theta_deg": 180.0})
    assert env.info["drive_m"] == pytest.approx(0.39, abs=1e-6) and env.info["obstacle_m"] > 0.2


def test_truth_in_the_room_frame(world, scenarios):
    env = kr.KinSimEnv.room(world, scenarios["S1"], preset_name="study")           # (2.5, 1.5) facing +y
    env.reset(3)
    env.step("FORWARD_25")
    env.step("TURN_LEFT_30")
    w = env.truth_pose_world()
    assert (w["x_m"], w["y_m"], w["theta_deg"]) == pytest.approx((2.5, 1.75, 120.0))
    assert env.truth_pose() == pytest.approx({"x_m": 0.25, "y_m": 0.0, "theta_deg": 30.0})


def test_carpet_odometry_bends_the_truth_and_reports_it(world, scenarios):
    env = kr.KinSimEnv.room(world, scenarios["S5"], preset_name="study", odometry="carpet")
    raw = env.reset(11)
    dr = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
    for move in ["FORWARD_25"] * 3 + ["TURN_LEFT_30"] * 3 + ["FORWARD_25"] * 2:
        raw = env.step(move)
        o = raw["odometry"]
        dr = g.compose_odometry(dr, o["forward_m"], o["left_m"], o["dtheta_deg"])
    t = env.truth_pose()
    # five forward moves veer about 15 deg/m * 1.25 m = 19 deg to the left; three turns give 3 * 30 * 0.98
    assert t["theta_deg"] == pytest.approx(0.98 * 90 + 15.0 * 1.25, abs=8.0) and t["theta_deg"] > 90.0
    assert abs(g.wrap_deg(dr["theta_deg"] - t["theta_deg"])) < 2.5          # the gyro saw it
    assert math.hypot(dr["x_m"] - t["x_m"], dr["y_m"] - t["y_m"]) < 0.08
    straight = kr.KinSimEnv.room(world, scenarios["S5"], preset_name="study")
    straight.reset(11)
    assert straight.step("FORWARD_25")["odometry"]["left_m"] == 0.0 and straight.truth_pose()["y_m"] == 0.0
    with pytest.raises(ValueError):
        kr.KinSimEnv.room(world, scenarios["S5"], odometry="ice")


def test_episodes_are_deterministic_and_seeded(world, scenarios):
    def run(seed, **kw):
        env = kr.KinSimEnv.room(world, scenarios["S3"], preset_name="camera", max_range_m=2.5, **kw)
        return kr.run_episode(env, seed, policy=kr.make_b2_policy())
    a, b = run(3000), run(3000)
    e1, e2 = (kr.KinSimEnv.room(world, scenarios["S3"], preset_name="study", max_range_m=2.5) for _ in range(2))
    seq = lambda e: [e.reset(9), e.step("TURN_LEFT_30"), e.observe(), e.observe(), e.step("FORWARD_25")]
    assert json.dumps(seq(e1), sort_keys=True) == json.dumps(seq(e2), sort_keys=True)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert run(3001)["records"] != a["records"]
    assert run(3000, odometry="carpet")["records"] != a["records"]
    assert a["ended_by"] in ("DONE", "budget") and len(a["info"]) == len(a["records"]) >= 30


# ---------------------------------------------------------------- downstream tools read room logs unchanged

def test_room_logs_feed_the_replay_inputs_b0_and_the_metrics(world, scenarios):
    from beaconmind.metrics import pilot as pm
    env = kr.KinSimEnv.room(world, scenarios["S1"], preset_name="camera", max_range_m=2.5, odometry="carpet")
    ep = kr.run_episode(env, 3000, policy=kr.make_b2_policy())
    recs = ep["records"]
    assert set(recs[0]) == {"step", "truth", "raw", "report", "calls"}
    study = ks.run_episode(2000)["records"]
    assert set(recs[5]["raw"]) == set(study[5]["raw"]) and set(recs[5]["report"]) == set(study[5]["report"])
    tracker, src = ks.CounterTracker(), None
    for r in recs:
        counters = tracker.before_step(r["raw"], src)            # the replay harness's counters equal the env's for B2
        src = r["report"]["pose_source"]
        assert counters == {k: v for k, v in r["raw"]["counters"].items() if k != "steps_left"}
        obs = ks.as_observation(3000, r["raw"], counters)
        assert all("_tag" not in d for d in obs["detections"])
        if r["step"]:                                             # step 0 has last_move null, as in kinsim_lite's logs
            assert validate("observation", obs) == []
    assert validate("observation", ks.as_observation(2000, study[0]["raw"], study[0]["raw"]["counters"])) == \
        validate("observation", ks.as_observation(3000, recs[0]["raw"], recs[0]["raw"]["counters"]))
    # B2's own reports carry note: null, in the room as in the study (the report schema is for the LLM arms)
    assert validate("report", recs[9]["report"]) == validate("report", study[9]["report"])
    assert validate("report", dict(recs[9]["report"], note="x", message="x", requested_mission="EXPLORE")) == \
        validate("report", dict(study[9]["report"], note="x", message="x", requested_mission="EXPLORE"))
    b0 = ks.dead_reckoning(recs)
    err = pm.trajectory_errors(b0, [r["truth"] for r in recs])
    assert len(b0) == len(recs) and err["ate_m"] < 0.25
    scores = pm.map_scores_c10(recs[-1]["report"]["map"], ep["world"])
    assert 0 < scores["map_recall"] <= 1
    assert pm.gold_calls(ks.as_observation(3000, recs[9]["raw"], recs[9]["raw"]["counters"]), recs[8]["report"]) is not None
    for key in ("wheel_scale_sigma", "gyro_sigma_deg", "range_sigma_a_m", "range_sigma_b", "bearing_sigma_deg"):
        assert key in ep["noise"]                                 # B1's noise block (baselines/b1_gtsam.py NOISE_KEYS)
    json.dumps(ep)


# ---------------------------------------------------------------- the coded procedure in the room

def test_dead_end_branch_is_defined_by_the_room_policy(world, scenarios):
    def run(policy):
        env = kr.KinSimEnv.room(world, scenarios["S4"], preset_name="camera", max_range_m=2.0)
        return kr.run_episode(env, 3001, policy=policy)
    frozen = run(kr.b2_step)
    assert frozen["ended_by"] == "not_implemented: " + kr.DEAD_END
    n = len(frozen["records"])
    fixed = run(kr.make_b2_policy())
    assert fixed["ended_by"] == "DONE" and len(fixed["records"]) > n
    assert fixed["records"][:n] == frozen["records"]              # identical until the branch the frozen code lacks
    step = fixed["records"][n]
    assert step["report"]["memory"]["blocked_heading_deg"] == step["report"]["pose"]["theta_deg"]
    assert step["raw"]["safety"]["forward_allowed"] == [] and step["report"]["decision"].startswith("TURN")
    assert set(step["report"]["memory"]) == set(ks.initial_memory())
    # a completed forward move clears the blocked heading (rule 7)
    later = [r for r in fixed["records"][n + 1:] if r["raw"]["last_move"]["action"].startswith("FORWARD")]
    assert later and all(r["report"]["memory"]["blocked_heading_deg"] is None or
                         r["report"]["memory"]["blocked_heading_deg"] == r["report"]["pose"]["theta_deg"] for r in later)
    with pytest.raises(ValueError):
        kr.make_b2_policy(dead_end="ignore")


def test_patience_postpones_e1_only(world, scenarios):
    def run(patience):
        env = kr.KinSimEnv.room(world, scenarios["S3"], preset_name="camera", max_range_m=2.0)
        return kr.run_episode(env, 3000, policy=kr.make_b2_policy(patience=patience))
    two, four = run(2), run(4)
    n = len(two["records"])
    assert two["ended_by"] == "DONE" and two["records"][-1]["report"]["memory"]["scans_without_new"] == 2
    assert len(four["records"]) > n
    assert [r["report"]["decision"] for r in four["records"][:n - 1]] == [r["report"]["decision"] for r in two["records"][:-1]]
    assert four["records"][n - 1]["report"]["memory"]["scans_without_new"] == 2      # the true count is kept
    if four["ended_by"] == "DONE":
        assert four["records"][-1]["report"]["memory"]["scans_without_new"] >= 4


# ---------------------------------------------------------------- world files and their tool

def test_world_files_validate_and_match_the_layout(world):
    assert validate("world", world) == []
    assert validate("world", json.loads((Path(__file__).parent / "fixtures" / "contracts" / "world.json").read_text())) == []
    layout = json.loads(LAYOUT.read_text(encoding="utf-8"))
    assert world["source"] == "real" and world["measured"] is None and world["world_id"] == "real-room-nominal"
    assert [(t["uid"], t["id"], t["x_m"], t["y_m"], t["normal_deg"]) for t in world["tags"]] == \
        [(t["uid"], t["id"], t["x_m"], t["y_m"], t["normal_deg"]) for t in layout["tags"]]
    assert world["duplicates"] == layout["duplicates"]
    assert world["arena"]["drive_polygon_m"] == [[round(v, 4) for v in p] for p in layout["drive_polygon_m"]]
    assert world["arena"]["polygon_m"] == [layout["corners_m"][c] for c in ("corner 5", "corner 4", "corner 3", "corner 2", "corner 1")]
    d = layout["desk_box_m"]
    assert world["arena"]["obstacles"][0]["polygon_m"] == [[d["x0"], d["y0"]], [d["x1"], d["y0"]], [d["x1"], d["y1"]], [d["x0"], d["y1"]]]
    bad = copy.deepcopy(world)
    bad["arena"]["drive_polygon_m"] = [[0.0, 0.0], [1.0]]
    assert validate("world", bad)
    bad = copy.deepcopy(world)
    bad["arena"]["obstacles"][0]["height_m"] = 0.7
    assert validate("world", bad)


def test_room_world_tool_regenerates_the_nominal_file_and_takes_measurements(world, tmp_path):
    rw = load_tool("room_world")
    layout = json.loads(LAYOUT.read_text(encoding="utf-8"))
    assert rw.build_world(layout, start=rw.default_start()) == world            # the tracked file is the tool's output
    assert rw.check_world(world) == []
    sheet = (ROOT / "evidence" / "M3" / "M3.T10" / "layout" / "mounting.md").read_text(encoding="utf-8")
    assert rw.parse_measured_md(sheet) == {}                                    # nothing measured yet
    filled = "\n".join(line.rstrip()[:-1].rstrip() + " %d |" % (float(line.split("|")[5]) + 3)
                       if line.startswith("| T0") or line.startswith("| T1") else line for line in sheet.splitlines())
    measured = rw.parse_measured_md(filled)
    assert len(measured) == 12 and measured["T00"] == 164.0 and measured["T11"] == 346.0
    out = tmp_path / "real-room.json"
    rw.main(["--measured", ",".join("%s=%s" % kv for kv in measured.items()), "--measured-by", "test", "--date",
             "2026-11-19", "--error-cm", "0.5", "--out", str(out)])
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert validate("world", doc) == [] and doc["world_id"] == "real-room" and doc["measured"]["error_estimate_m"] == 0.005
    assert doc["measured"]["nominal_shift_cm"]["T03"] == 3.0
    for t, nominal in zip(doc["tags"], world["tags"]):                          # each tag moved 3 cm along its wall
        assert math.hypot(t["x_m"] - nominal["x_m"], t["y_m"] - nominal["y_m"]) == pytest.approx(0.03, abs=0.002)
        assert t["id"] == nominal["id"] and t["normal_deg"] == nominal["normal_deg"]
    t04 = next(t for t in doc["tags"] if t["uid"] == "T04")                     # the angled wall runs at 45 degrees
    assert (t04["x_m"] - 3.554, t04["y_m"] - 0.686) == pytest.approx((0.0213, 0.0211), abs=0.002)
    with pytest.raises(SystemExit):                                             # a tag missing
        rw.main(["--measured", "T00=160", "--measured-by", "t", "--date", "d", "--error-cm", "1", "--out", str(out)])
    with pytest.raises(SystemExit):                                             # off the wall
        rw.main(["--measured", ",".join("%s=%s" % (k, 900 if k == "T04" else v) for k, v in measured.items()),
                 "--measured-by", "t", "--date", "d", "--error-cm", "1", "--out", str(out)])
    close = copy.deepcopy(world)
    a, b = (next(t for t in close["tags"] if t["uid"] == u) for u in ("T02", "T05"))
    b["x_m"], b["y_m"] = a["x_m"] + 1.0, a["y_m"]
    assert any("share ID" in p for p in rw.check_world(close))
    far = copy.deepcopy(world)
    far["start_pose"] = {"x_m": 0.9, "y_m": 3.0, "theta_deg": 0.0}
    assert any("start pose" in p for p in rw.check_world(far))


def test_scenarios_start_inside_the_driving_area_clear_of_the_walls(world, scenarios):
    drive = [tuple(p) for p in world["arena"]["drive_polygon_m"]]
    assert len(scenarios) == 5
    for sid, s in scenarios.items():
        assert kr.inside_depth(drive, (s["x_m"], s["y_m"])) >= 0.75, sid
        kr.room_scene(world, s, drive_inset_m=0.4)
    assert world["start_pose"] == scenarios["S1"]


def test_rehearsal_metrics_on_one_episode(world, scenarios):
    rr = load_tool("room_rehearsal")
    rows = rr.run_cell(world, [{"id": "S1", "start_pose": scenarios["S1"]}], [3000, 3001], "camera", 2.5, "drift2")
    assert len(rows) == 2
    r = rows[0]
    assert r["scenario"] == "S1" and r["ended_by"] in ("DONE", "budget", "not_implemented")
    shares = sum(r["share_" + k] for k in ("beacon_fix", "relocalised", "position_fix", "prior_kept", "odometry"))
    assert shares == pytest.approx(1.0) and 0 <= r["tags_mapped"] <= r["tags_seen"] <= 12
    assert r["ate_b0_m"] > 0 and r["dup_pairs_mapped_twice"] <= r["dup_pairs_seen"] <= 3
    s = rr.summarise(rows)
    assert s["episodes"] == 2 and s["done"] + s["budget"] + s["not_implemented"] == 2
    assert s["ate_b2_lower"] + s["ate_b2_higher"] <= 2
    more = rr.with_extra_tags(world)
    assert len(more["tags"]) == 18 and validate("world", more) == [] and len(world["tags"]) == 12
    assert "| S1 |" not in rr.table("t", "x", [("row", s)]) and "| row |" in rr.table("t", "x", [("row", s)])


def test_visibility_agrees_with_the_layout_tools_independent_model(world):
    """tools/room_layout.py tests visibility in the room frame with its own code (axis-aligned desk box, bearings from
    atan2); the simulator works in the map frame of each start pose. They must agree but for boundary rounding."""
    rl = load_tool("room_layout")
    drive = [tuple(p) for p in world["arena"]["drive_polygon_m"]]
    rng = random.Random(3)
    pairs = visible = differ = 0
    origin = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
    for _ in range(600):
        x, y, th = rng.uniform(0.7, 3.8), rng.uniform(0.1, 5.2), rng.uniform(-180, 180)
        if kr.inside_depth(drive, (x, y)) < 0.3:
            continue
        scene = kr.room_scene(world, {"x_m": x, "y_m": y, "theta_deg": th})
        for rmax in (2.0, 3.0):
            noise = kr.preset("study", max_range_m=rmax)
            for t, wt in zip(scene["tags"], world["tags"]):
                mine = kr.visible(scene, origin, t, noise) is not None
                r = rl.visible_range((x, y, th), wt, occluders=(rl.DESK,))
                pairs += 1
                visible += mine
                differ += mine != (r is not None and r <= rmax)
    assert pairs > 8000 and visible > 500 and differ <= 2
