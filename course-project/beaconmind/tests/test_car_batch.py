"""The unattended batch runner on the simulated car in the simulated room: resection, the move guard, every health
halt, the manifest and its resume (plan/README.md section 3.6 "Unattended batches").

Nothing here touches ROS or the real car: the rig is batch.dry_rig (SimCar + the room simulator's detections).

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote these tests.
"""
import importlib.util
import json
import math
import random
from pathlib import Path

import pytest

import beaconmind
from beaconmind.car import batch as B
from beaconmind.car import resection as R
from beaconmind.car.camera import CameraError
from beaconmind.car.latch import Latch
from beaconmind.harness import closed_loop as cl
from beaconmind.harness import replay as rp
from beaconmind.harness import validator as vd

ROOT = beaconmind.course_root()
WORLD_PATH = ROOT / "configs" / "arenas" / "real-room-nominal.json"
WORLD = json.loads(WORLD_PATH.read_text())
TAGS = [{"id": t["id"], "uid": t["uid"], "x_m": t["x_m"], "y_m": t["y_m"]} for t in WORLD["tags"]]
S1 = {"id": "S1", "x_m": 2.5, "y_m": 1.5, "theta_deg": 90.0}
S5 = {"id": "S5", "x_m": 2.25, "y_m": 2.6, "theta_deg": 180.0}
PLACE = {"x_m": 2.3, "y_m": 1.7, "theta_deg": 60.0}             # where the simulated car really stands
TAPED = {"x_m": 2.35, "y_m": 1.65, "theta_deg": 55.0}           # what the operator read off the tape


def view_from(pose, max_range=2.5, hfov=360.0, noise=None):
    """Exact (or noisy) detections of the surveyed tags from an arena-frame pose."""
    dets = []
    for t in TAGS:
        dx, dy = t["x_m"] - pose["x_m"], t["y_m"] - pose["y_m"]
        rng = math.hypot(dx, dy)
        bearing = R.wrap_deg(math.degrees(math.atan2(dy, dx)) - pose["theta_deg"])
        if rng <= max_range and abs(bearing) <= hfov / 2:
            if noise:
                rng, bearing = rng * (1 + noise.gauss(0, 0.02)), bearing + noise.gauss(0, 1.0)
            dets.append({"id": t["id"], "range_m": rng, "bearing_deg": bearing})
    return dets


# ---------------------------------------------------------------- resection

@pytest.mark.parametrize("pose", [{"x_m": 2.5, "y_m": 1.5, "theta_deg": 90.0}, {"x_m": 1.4, "y_m": 4.1, "theta_deg": -135.0},
                                  {"x_m": 3.0, "y_m": 2.6, "theta_deg": 10.0}])
def test_resection_recovers_the_pose(pose):
    fix = R.resect([{"pose": None, "detections": view_from(pose)}], TAGS)
    assert fix["ok"] and fix["n_tags"] >= 3 and fix["rms_m"] < 1e-6
    assert fix["pose"]["x_m"] == pytest.approx(pose["x_m"], abs=1e-6) and fix["pose"]["y_m"] == pytest.approx(pose["y_m"], abs=1e-6)
    assert R.wrap_deg(fix["pose"]["theta_deg"] - pose["theta_deg"]) == pytest.approx(0.0, abs=1e-6)
    assert 0.0 < fix["sigma_xy_m"] < 0.2 and 0.0 < fix["sigma_theta_deg"] < 10.0


def test_resection_error_is_inside_its_stated_uncertainty():
    """2 % range noise and 1 degree bearing noise, 200 draws: the error stays within three stated sigmas in at least
    95 % of them (the stated sigma uses the design values' larger noise, so it should be conservative)."""
    rng, pose, inside = random.Random(5), {"x_m": 2.4, "y_m": 2.2, "theta_deg": 30.0}, 0
    for _ in range(200):
        fix = R.resect([{"pose": None, "detections": view_from(pose, noise=rng)}], TAGS, prior=pose)
        assert fix["ok"]
        err = math.hypot(fix["pose"]["x_m"] - pose["x_m"], fix["pose"]["y_m"] - pose["y_m"])
        inside += err <= 3 * fix["sigma_xy_m"] and abs(R.wrap_deg(fix["pose"]["theta_deg"] - 30.0)) <= 3 * fix["sigma_theta_deg"]
    assert inside >= 190


def test_resection_refuses_what_it_cannot_know():
    pose = {"x_m": 2.5, "y_m": 1.5, "theta_deg": 90.0}
    one = [d for d in view_from(pose) if d["id"] == 23]
    assert R.resect([{"pose": None, "detections": one}], TAGS)["ok"] is False             # one tag: no pose
    assert R.resect([{"pose": None, "detections": []}], TAGS) == {"ok": False, "why": "fewer than 2 surveyed tags in view", "n_tags": 0}
    unknown = [{"id": 99, "range_m": 1.0, "bearing_deg": 0.0}, {"id": 98, "range_m": 1.0, "bearing_deg": 20.0}]
    assert R.resect([{"pose": None, "detections": unknown}], TAGS)["ok"] is False         # ids not in the survey
    far = R.resect([{"pose": None, "detections": view_from(pose)}], TAGS, prior={"x_m": 1.0, "y_m": 4.0, "theta_deg": 90.0})
    assert far["ok"] is False and far["why"] == "far_from_prior"
    bent = view_from(pose)
    bent[0]["range_m"] += 0.8                                   # one detection badly wrong: the residual says so
    assert R.resect([{"pose": None, "detections": bent}], TAGS)["ok"] is False


def test_repeated_ids_are_settled_by_fit_or_by_the_prior():
    """Ids 3, 0 and 2 are on two tags each. Two tags of repeated ids alone fit several ways."""
    pose = {"x_m": 2.6, "y_m": 0.9, "theta_deg": -60.0}
    seen = [d for d in view_from(pose) if d["id"] in (3, 0)]    # T04 (id 0) at 1.0 m, T02 and T05 (both id 3) at 1.4 m
    assert sorted(d["id"] for d in seen) == [0, 3, 3]
    two = [seen[1], seen[0]]                                    # one tag of id 0 and one of id 3: four ways to read them
    alone = R.resect([{"pose": None, "detections": two}], TAGS)
    with_prior = R.resect([{"pose": None, "detections": two}], TAGS, prior=pose)
    assert with_prior["ok"] and with_prior["pose"]["x_m"] == pytest.approx(2.6, abs=1e-6)
    if alone["ok"]:                                             # without a prior: refused, or right; never a wrong pose
        assert (alone["pose"]["x_m"], alone["pose"]["y_m"]) == pytest.approx((2.6, 0.9), abs=1e-6)
    else:
        assert "ambiguous" in alone["why"]
    # two tags whose copies are the same distance apart cannot be told apart at all
    twins = [{"id": 1, "x_m": 0.0, "y_m": 0.0}, {"id": 2, "x_m": 1.0, "y_m": 0.0}, {"id": 1, "x_m": 3.0, "y_m": 2.0},
             {"id": 2, "x_m": 4.0, "y_m": 2.0}]
    view = [{"id": 1, "range_m": 1.0, "bearing_deg": 30.0}, {"id": 2, "range_m": 1.0, "bearing_deg": -30.0}]
    assert "ambiguous" in R.resect([{"pose": None, "detections": view}], twins)["why"]
    full = R.resect([{"pose": None, "detections": view_from(pose)}], TAGS)                # all tags: the fit decides
    assert full["ok"] and full["pose"]["y_m"] == pytest.approx(0.9, abs=1e-6)


def test_a_scan_of_narrow_views_gives_one_fix():
    """Twelve views 30 degrees apart, each 47 degrees wide, with the odometry of the turns: one pose for the circle."""
    pose = {"x_m": 2.5, "y_m": 1.5, "theta_deg": 90.0}
    views = [{"pose": {"x_m": 0.0, "y_m": 0.0, "theta_deg": 30.0 * k},
              "detections": view_from(dict(pose, theta_deg=90.0 + 30.0 * k), max_range=2.0, hfov=46.9)} for k in range(12)]
    assert max(len(v["detections"]) for v in views) <= 2        # no single view could do it well
    fix = R.resect(views, TAGS, max_range_m=2.0)
    assert fix["ok"] and fix["n_tags"] >= 4
    assert (fix["pose"]["x_m"], fix["pose"]["y_m"], fix["pose"]["theta_deg"]) == pytest.approx((2.5, 1.5, 90.0), abs=1e-6)


def test_position_fix_from_one_tag_and_the_heading():
    pose = {"x_m": 2.5, "y_m": 1.5, "theta_deg": 90.0}
    one = [d for d in view_from(pose) if d["id"] == 12]
    fix = R.position_fix(one, TAGS, prior={"x_m": 2.45, "y_m": 1.55, "theta_deg": 90.0}, prior_sigma_theta_deg=3.0)
    assert fix["ok"] and fix["kind"] == "position" and fix["n_tags"] == 1
    assert (fix["pose"]["x_m"], fix["pose"]["y_m"]) == pytest.approx((2.5, 1.5), abs=1e-6)
    assert 0.05 < fix["sigma_xy_m"] < 0.25
    away = R.position_fix(one, TAGS, prior={"x_m": 1.0, "y_m": 4.0, "theta_deg": 90.0}, prior_sigma_theta_deg=3.0)
    assert away == {"ok": False, "why": "far_from_prior", "n_tags": 0}
    assert R.position_fix(one, TAGS, prior=pose, prior_sigma_theta_deg=3.0, max_range_m=0.5)["ok"] is False


# ---------------------------------------------------------------- tracker and guard

def make_guard(margin=0.10, block=0.25):
    from beaconmind.car.config import load_car
    c = load_car()
    return B.MoveGuard(WORLD, [tuple(p) for p in c["corners"]], float(c["sweep_radius_m"]), margin, block)


def test_tracker_grows_between_fixes_and_shrinks_on_one():
    t = B.PoseTracker(S1, 0.05, 2.0)
    for _ in range(4):
        t.predict({"forward_m": 0.25, "left_m": 0.0, "dtheta_deg": 0.0})
    assert t.pose["y_m"] == pytest.approx(2.5) and t.steps_since_fix == 4
    grown = t.sigma_xy_m
    assert 0.05 < grown < 0.12
    t.correct({"pose": {"x_m": 2.6, "y_m": 2.5, "theta_deg": 92.0}, "sigma_xy_m": 0.05, "sigma_theta_deg": 2.0})
    assert t.sigma_xy_m == 0.05 < grown and t.steps_since_fix == 0      # never below the floor (fix_floor_m)
    assert 2.5 < t.pose["x_m"] < 2.6 and 90.0 < t.pose["theta_deg"] < 92.0       # between the two, by their weights


def test_guard_blocks_moves_toward_every_edge():
    g = make_guard()
    centre = {"x_m": 2.2, "y_m": 2.6, "theta_deg": 0.0}
    assert g.check("FORWARD_25", centre, 0.05) is None and g.check("TURN_LEFT_30", centre, 0.05) is None
    assert g.forward_allowed(centre, 0.05) == ["FORWARD_25", "FORWARD_10"]
    # the drive-area edge in front of the desk (x = 0.66): facing it from 0.45 m, the camera end would cross the margin
    at_desk = {"x_m": 1.15, "y_m": 2.9, "theta_deg": 180.0}
    assert "edge of the driving area" in g.check("FORWARD_25", at_desk, 0.05)
    assert g.check("FORWARD_10", at_desk, 0.02) is None and g.check("BACKWARD_10", at_desk, 0.05) is None
    # the window wall (x = 3.82), the 295 cm wall (y = 0.09), the far wall (y = 5.2)
    assert g.check("FORWARD_25", {"x_m": 3.3, "y_m": 2.6, "theta_deg": 0.0}, 0.05)
    assert g.check("FORWARD_25", {"x_m": 2.0, "y_m": 0.65, "theta_deg": -90.0}, 0.05)
    assert g.check("FORWARD_25", {"x_m": 2.0, "y_m": 4.6, "theta_deg": 90.0}, 0.05)
    assert g.check("BACKWARD_10", {"x_m": 3.45, "y_m": 2.6, "theta_deg": 180.0}, 0.05)     # the rear toward the wall
    # a turn sweeps the camera end (0.178 m): 0.20 m from the edge is not enough room, 0.25 m is; doubt needs more
    assert "sweep circle" in g.check("TURN_LEFT_30", {"x_m": 0.86, "y_m": 2.9, "theta_deg": 0.0}, 0.02)
    assert g.check("TURN_RIGHT_30", {"x_m": 0.91, "y_m": 2.9, "theta_deg": 0.0}, 0.02) is None
    assert g.check("TURN_RIGHT_30", {"x_m": 0.91, "y_m": 2.9, "theta_deg": 0.0}, 0.10)
    # and no straight move may end where the car could not turn away again
    checked = 0
    for x in (1.0, 1.1, 1.2, 1.3, 1.4, 1.6):                   # facing the drive-area edge from ever closer
        for name in g.forward_allowed({"x_m": x, "y_m": 2.9, "theta_deg": 180.0}, 0.03):
            d = 0.25 if name == "FORWARD_25" else 0.10
            assert g.check("TURN_LEFT_30", {"x_m": x - d - 0.04, "y_m": 2.9, "theta_deg": 180.0}, 0.03) is None
            checked += 1
    assert checked >= 4 and g.forward_allowed({"x_m": 1.0, "y_m": 2.9, "theta_deg": 180.0}, 0.03) == []


def test_guard_blocks_everything_when_the_pose_is_uncertain_or_unknown():
    g = make_guard()
    centre = {"x_m": 2.2, "y_m": 2.6, "theta_deg": 0.0}
    assert "uncertain" in g.check("TURN_LEFT_30", centre, 0.30) and "uncertain" in g.check("FORWARD_10", centre, 0.30)
    assert g.check("FORWARD_10", dict(centre, x_m=float("nan")), 0.05) == "pose unknown"
    assert g.check("FORWARD_10", centre, float("inf")) == "pose unknown"
    assert g.check("JUMP", centre, 0.05) == "not a move"
    near = {"x_m": 3.35, "y_m": 2.6, "theta_deg": 0.0}
    assert g.check("FORWARD_10", near, 0.01) is None and g.check("FORWARD_10", near, 0.08)   # more doubt, more margin


# ---------------------------------------------------------------- the pass marker

def _session(root, name, done, other=0):
    """A recorded session with `done` move logs that ended done and `other` that did not."""
    moves = root / "data" / "real" / name / "moves"
    moves.mkdir(parents=True)
    for i in range(done + other):
        result = "done" if i < done else "timeout"
        (moves / ("move_%03d.jsonl" % i)).write_text(
            json.dumps({"ev": "header"}) + "\n" + json.dumps({"ev": "result", "result": {"result": result}}) + "\n")


def test_pass_marker(tmp_path):
    root = tmp_path / "course"
    for rel in B.MARKER_FILES:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("v1")
    marker = root / "data" / "real" / "ATTENDED_PASS.json"
    assert "no pass marker" in B.check_pass_marker(str(marker), str(root))[0]
    with pytest.raises(ValueError, match="no recorded moves"):
        B.write_pass_marker(str(marker), str(root), "xiaohui", "stand-1", "floor-1")       # sessions must exist
    _session(root, "stand-1", done=6, other=2)                  # the stand test: straights done, turns time out
    _session(root, "floor-1", done=14)
    _session(root, "empty-1", done=1, other=3)
    with pytest.raises(ValueError, match="operator"):
        B.write_pass_marker(str(marker), str(root), " ", "stand-1", "floor-1")
    with pytest.raises(ValueError, match="two recorded sessions"):
        B.write_pass_marker(str(marker), str(root), "xiaohui", "floor-1", "floor-1")       # one session for both
    with pytest.raises(ValueError, match="1 moves that ended `done`"):
        B.write_pass_marker(str(marker), str(root), "xiaohui", "stand-1", "empty-1")       # a session of failed moves
    with pytest.raises(ValueError, match="name|no recorded moves"):
        B.write_pass_marker(str(marker), str(root), "xiaohui", "../stand-1", "floor-1")
    B.write_pass_marker(str(marker), str(root), "xiaohui", "stand-1", "floor-1", now_unix=1000.0)
    assert B.check_pass_marker(str(marker), str(root), now_unix=1000.0 + 86400) == []
    assert "days old" in B.check_pass_marker(str(marker), str(root), now_unix=1000.0 + 8 * 86400)[0]
    assert "days old" in B.check_pass_marker(str(marker), str(root), now_unix=1000.0 - 86400)[0]   # a clock set back
    for rel in ("beaconmind/src/beaconmind/car/executor.py", "beaconmind/src/beaconmind/car/batch.py", "configs/dv.json"):
        old = (root / rel).read_text()
        (root / rel).write_text("v2")                           # changed since the tests
        assert rel.rsplit("/", 1)[1] in B.check_pass_marker(str(marker), str(root), now_unix=1060.0)[0]
        (root / rel).write_text(old)
    record = json.loads(marker.read_text())
    record["fingerprint"] = {"nothing": None}                   # a marker cannot choose what is compared
    marker.write_text(json.dumps(record))
    assert "changed since" in B.check_pass_marker(str(marker), str(root), now_unix=1060.0)[0]
    record["fingerprint"] = "x"
    marker.write_text(json.dumps(record))
    assert B.check_pass_marker(str(marker), str(root), now_unix=1060.0)
    marker.write_text("{}")
    assert "not a bm.attended_pass/1" in B.check_pass_marker(str(marker), str(root))[0]


def test_tool_refuses_a_real_batch_without_the_marker_and_the_recorder(tmp_path, capsys):
    spec = importlib.util.spec_from_file_location("car_batch", ROOT / "tools" / "car_batch.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    code = tool.main(["run", "--world", str(WORLD_PATH), "--start", "S1:2.5,1.5,90", "--initial-pose", "2.5,1.5,90",
                      "--label", "t", "--marker", str(tmp_path / "none.json"), "--latch", str(tmp_path / "LATCH")])
    err = capsys.readouterr().err
    assert code == 2 and "no pass marker" in err and "nothing was sent" in err      # before any ROS import
    Latch(tmp_path / "LATCH").set("x", "t")
    assert tool.main(["run", "--world", str(WORLD_PATH), "--start", "2.5,1.5,90", "--initial-pose", "2.5,1.5,90",
                      "--label", "t", "--marker", str(tmp_path / "none.json"), "--latch", str(tmp_path / "LATCH")]) == 2
    assert "latch is set" in capsys.readouterr().err


def test_tool_dry_run_and_halt_commands(tmp_path, capsys):
    spec = importlib.util.spec_from_file_location("car_batch", ROOT / "tools" / "car_batch.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    out = tmp_path / "batch"
    args = ["run", "--world", str(WORLD_PATH), "--start", "S1:2.5,1.5,90", "--initial-pose", "2.4,1.6,70",
            "--episodes", "1", "--max-steps", "6", "--dry-run", "--out", str(out)]
    assert tool.main(args) == 0
    assert "status: complete" in capsys.readouterr().out
    vd.write_latch_file(out / "HALT.LATCH", "batch halt: test", "car_batch")
    assert tool.main(args) == 2                                 # a halt left behind: nothing runs
    assert tool.main(["clear-halt", "--out", str(out), "--operator", " "]) == 2
    assert tool.main(["clear-halt", "--out", str(out), "--operator", "xiaohui"]) == 0
    assert not (out / "HALT.LATCH").exists()
    assert tool.main(["status", "--out", str(out)]) == 0 and "ep01-a1  done" in capsys.readouterr().out


# ---------------------------------------------------------------- the batch on the simulated car

class Batch:
    """A runner on a dry rig, with a hook called on every simulation step once `at_moves` moves have been sent."""

    def __init__(self, tmp_path, episodes=1, max_steps=10, starts=(S1,), place=PLACE, taped=TAPED, driver=None,
                 budget=None, sim_params=None, **params):
        self.out = tmp_path / "batch"
        self.latch = Latch(tmp_path / "LATCH")
        self.params = B.BatchParams(world_path="configs/arenas/real-room-nominal.json", start_poses=list(starts),
                                    initial_pose=dict(taped), episodes=episodes, max_steps=max_steps, **params)
        self.rig = B.dry_rig(WORLD, place, latch=self.latch, sim_params=sim_params)
        self.budget = budget or rp.Budget(float("inf"))
        self.runner = B.BatchRunner(self.params, self.rig, WORLD, self.out, driver=driver or cl.B2Driver(),
                                    budget=self.budget, log=lambda *a: None, run_episode=cl.run_episode)
        self.fired = False
        self.sent_at_halt = None
        real_halt = self.runner.monitor.halt

        def halt(code, detail, safety=None):
            if self.runner.monitor.halted is None:
                self.sent_at_halt = len(self.rig.link.published)        # what had been sent when the halt was recorded
            return real_halt(code, detail, safety)
        self.runner.monitor.halt = halt

    def at_moves(self, n, action):
        walls = self.rig.link.on_step

        def hook(link):
            if walls:
                walls(link)
            if not self.fired and self.runner.monitor.steps >= n:
                self.fired = True
                action(self)
        self.rig.link.on_step = hook

    def run(self):
        self.result = self.runner.run()
        self.manifest = json.loads((self.out / "manifest.json").read_text())
        return self.result

    def assert_halted(self, code, safety):
        halt = self.result["halt"]
        if safety and halt and halt["safety"] is False and self.latch.is_set():
            safety = False      # the executor had set the project latch already: the batch only names the cause
        assert self.result["status"] == "halted" and halt and halt["code"] == code, self.result
        assert self.manifest["status"] == "halted" and self.manifest["halt"]["code"] == code
        assert vd.read_latch_file(self.out / "HALT.LATCH")["reason"].startswith("batch halt: %s" % code)
        assert halt["safety"] is safety
        if safety or code in B.SAFETY_HALTS:
            assert self.latch.is_set()                          # the project latch too
        assert "HALTED: %s" % code in (self.out / "summary.txt").read_text()
        # from the moment the halt was recorded not one motion command was published
        assert self.sent_at_halt is not None
        assert all((v, w) == (0.0, 0.0) for _t, v, w in self.rig.link.published[self.sent_at_halt:])
        # nothing moves afterwards: the car is at rest, and a rerun refuses until an operator clears the halt
        sent, moves = len(self.rig.link.published), self.runner.monitor.steps
        self.rig.link.on_step = None
        self.rig.link.wait(2.0)
        assert not self.rig.link.sim.moving and len(self.rig.link.published) == sent
        again = B.BatchRunner(self.params, self.rig, WORLD, self.out, driver=cl.B2Driver(), budget=self.budget,
                              log=lambda *a: None, run_episode=cl.run_episode).run()
        assert again["status"] == "refused" and self.runner.monitor.steps == moves
        assert len(self.rig.link.published) == sent


def test_a_batch_of_two_episodes(tmp_path):
    b = Batch(tmp_path, episodes=2, max_steps=30, starts=(S1, S5))
    markers = tmp_path / "markers.jsonl"
    b.runner.marker_path = str(markers)
    assert b.run() == {"status": "complete", "halt": None}
    eps = b.manifest["episodes"]
    assert [e["id"] for e in eps] == ["ep01-a1", "ep02-a1"] and all(e["status"] == "done" for e in eps)
    assert [e["scenario"] for e in eps] == ["S1", "S5"]
    for e, target in zip(eps, (S1, S5)):
        # the start pose was reached within the tolerance, as the start circle measured it, and that measurement is right
        assert e["start_fix"]["ok"] and e["start_fix"]["miss_m"] <= 0.20 and e["start_fix"]["miss_deg"] <= 20.0
        sim, got = e["start_fix"]["sim_truth_world"], e["start_pose_world"]
        assert math.hypot(sim["x_m"] - got["x_m"], sim["y_m"] - got["y_m"]) < 0.05
        assert abs(R.wrap_deg(sim["theta_deg"] - got["theta_deg"])) < 3.0
        assert math.hypot(sim["x_m"] - target["x_m"], sim["y_m"] - target["y_m"]) <= 0.25
        assert e["result"]["ended_by"] == "budget" and e["result"]["steps"] == 30
        assert e["final_pose_error"]["m"] < 0.10 and "tracked_minus_end_scan" in e
        truth = [json.loads(line) for line in open(b.out / "episodes" / e["id"] / "truth.jsonl")]
        assert len(truth) >= 30 and any(r["no_fix"] for r in truth) and any(not r["no_fix"] for r in truth)
        for r in truth:                                         # ground truth per step, with its uncertainty and flag
            assert set(r["truth_map"]) >= {"x_m", "y_m", "theta_deg", "sigma_xy_m", "sigma_theta_deg", "fix", "steps_since_fix"}
            w, s = r["tracked_world"]["pose"], r["sim_truth_world"]
            assert math.hypot(w["x_m"] - s["x_m"], w["y_m"] - s["y_m"]) <= max(3 * r["tracked_world"]["sigma_xy_m"], 0.05)
            assert b.runner.guard.footprint_depth(s) > 0.0      # the simulated car itself never left the driving area
    events = [json.loads(line)["event"] for line in open(markers)]
    assert events == ["episode_start", "episode_end"] * 2
    text = (b.out / "summary.txt").read_text()
    assert "status: complete" in text and "ep02-a1  done" in text and "moves sent" in text
    assert b.manifest["preflight"]["drive_map"] == [0.25, 0.33] and not b.latch.is_set()
    # a rerun of a complete batch drives nothing
    sent = len(b.rig.link.published)
    assert Batch.run(b)["status"] == "complete" and len(b.rig.link.published) == sent


def test_the_taped_start_may_be_off_and_the_scan_corrects_it(tmp_path):
    b = Batch(tmp_path, max_steps=4, taped={"x_m": 2.45, "y_m": 1.55, "theta_deg": 45.0})   # 21 cm and 15 degrees off
    assert b.run()["status"] == "complete"
    first = b.manifest["episodes"][0]["first_fix"]
    assert first["ok"] and math.hypot(first["pose"]["x_m"] - 2.3, first["pose"]["y_m"] - 1.7) < 0.05


def test_halt_latch_appears(tmp_path):
    b = Batch(tmp_path, max_steps=40)
    b.at_moves(30, lambda b: b.latch.set("operator STOP (key)", "bm_stop"))
    b.run()
    b.assert_halted("latch", safety=False)
    assert b.latch.read()["by"] == "bm_stop"                    # the batch did not overwrite the operator's cause
    assert b.runner.monitor.steps <= 31


def test_halt_telemetry_stale(tmp_path):
    b = Batch(tmp_path, max_steps=40)
    real = b.rig.link.car_state
    b.at_moves(28, lambda b: setattr(b.rig.link, "car_state", lambda: dict(real(), telemetry_age_s=3.0)))
    b.run()
    b.assert_halted("telemetry_stale", safety=True)


def test_halt_link_lost_when_telemetry_stops_mid_move(tmp_path):
    b = Batch(tmp_path, max_steps=40)
    b.at_moves(28, lambda b: b.rig.link.sim.p.telemetry_drop.append((b.rig.link.t + 0.3, 1e9)))
    b.run()
    assert b.result["halt"]["code"] in ("link_lost", "telemetry_stale")
    b.assert_halted(b.result["halt"]["code"], safety=True)


def test_halt_command_timeout_seen(tmp_path):
    b = Batch(tmp_path, max_steps=40)
    real = b.rig.link.car_state
    b.at_moves(28, lambda b: setattr(b.rig.link, "car_state", lambda: dict(real(), drive_status=2)))
    b.run()
    b.assert_halted("command_timeout", safety=True)


def test_halt_camera_down(tmp_path):
    b = Batch(tmp_path, max_steps=40)

    def dead(_n):
        raise CameraError("timed out")
    b.at_moves(28, lambda b: setattr(b.rig.camera, "frame_fn", dead))
    b.run()
    b.assert_halted("camera", safety=True)


def test_halt_camera_frames_missing_twice(tmp_path):
    b = Batch(tmp_path, max_steps=40)
    count = {"n": 0}

    def flaky(_n):
        count["n"] += 1
        if count["n"] % 5 in (0, 4, 3):                        # three of every five requests fail: "stale"
            raise CameraError("timed out")
        return b"\xff\xd8x\xff\xd9"
    b.at_moves(28, lambda b: setattr(b.rig.camera, "frame_fn", flaky))
    b.run()
    b.assert_halted("camera", safety=True)


def test_halt_supply_low(tmp_path):
    b = Batch(tmp_path, max_steps=40)
    b.at_moves(28, lambda b: setattr(b.rig.link.sim.p, "vsys_mv", 4100))
    b.run()
    b.assert_halted("supply_low", safety=True)


def test_halt_repeated_no_fix(tmp_path):
    """The tags stop being seen (lights off, a blocked lens that still sends frames): after no_fix_steps steps
    without one fix the batch halts."""
    b = Batch(tmp_path, max_steps=60, no_fix_steps=6)
    blind = {"on": False}
    real_make = b.rig.make_env

    def make_env(*args, **kwargs):
        env = real_make(*args, **kwargs)
        seeing = env.detector
        env.detector = lambda jpegs, n=None: ({"detections": [], "internal": [], "per_frame": []} if blind["on"]
                                              else seeing(jpegs, n))
        return env
    b.rig.make_env = make_env
    b.at_moves(27, lambda b: blind.update(on=True))
    b.run()
    b.assert_halted("no_fix", safety=True)
    assert "6 steps without a tag fix" in b.result["halt"]["detail"]


def test_halt_pose_outside_the_driving_area(tmp_path):
    b = Batch(tmp_path, max_steps=40)
    b.at_moves(28, lambda b: b.runner.tracker.set({"x_m": 0.3, "y_m": 2.9, "theta_deg": 0.0}, 0.05, 2.0))
    b.run()
    b.assert_halted("outside_drive_area", safety=True)


def test_halt_pose_too_uncertain(tmp_path):
    """No tag in view and the tracked position's uncertainty past the limit: the batch halts instead of idling."""
    b = Batch(tmp_path)
    r = b.runner
    r.preflight()
    env = r._service_env("t", str(tmp_path / "t"))
    env.inner.detector = lambda jpegs, n=None: {"detections": [], "internal": [], "per_frame": []}
    env.reset(1)
    assert r.monitor.halted is None
    r.tracker.sigma_xy_m = 0.6
    sense = env.step("TURN_LEFT_30")
    assert sense["move"]["result"] == "refused" and "pose uncertain" in sense["move"]["reason"]
    assert r.monitor.halted["code"] == "pose_uncertain" and b.latch.is_set()
    assert sense["safety"] == {"forward_allowed": [], "backward_allowed": False, "turn_allowed": False, "scan_allowed": False}
    assert b.rig.link.published == []


def test_halt_stall(tmp_path):
    b = Batch(tmp_path, max_steps=60)

    def block(b):
        b.rig.link.sim.p.blocked_left = b.rig.link.sim.p.blocked_right = True
    b.at_moves(28, block)
    b.run()
    b.assert_halted("stall", safety=True)


def test_halt_car_restart(tmp_path):
    b = Batch(tmp_path, max_steps=40)
    b.at_moves(28, lambda b: b.rig.link.sim.reboot())
    b.run()
    assert b.result["halt"]["code"] in ("car_restart", "link_lost")           # whichever the executor names first
    assert "restarted" in b.latch.read()["reason"] or "car_rebooted" in b.latch.read()["reason"]
    b.assert_halted(b.result["halt"]["code"], safety=True)
    assert b.manifest["episodes"][0]["status"] == "halted"


def test_halt_slow_car_times_out(tmp_path):
    """Fading motor batteries show as moves that no longer finish: a timeout halts, it is not retried."""
    b = Batch(tmp_path, max_steps=40)
    b.at_moves(28, lambda b: setattr(b.rig.link.sim.p, "speed_per_duty_mps", 0.03))
    b.run()
    assert b.result["halt"]["code"] in ("move_timeout", "stall")
    b.assert_halted(b.result["halt"]["code"], safety=True)


def test_halt_slow_forward_move(tmp_path):
    b = Batch(tmp_path, max_steps=60, min_forward_speed_mps=0.10)
    b.at_moves(26, lambda b: setattr(b.rig.link.sim.p, "speed_per_duty_mps", 0.16))
    b.run()
    b.assert_halted("slow", safety=True)


def test_halt_episode_wall_clock(tmp_path):
    b = Batch(tmp_path, max_steps=150, episode_wall_s=45.0)     # simulated seconds: the scans alone take about 30
    b.run()
    b.assert_halted("episode_wall_clock", safety=True)


def test_halt_batch_wall_clock_and_step_cap(tmp_path):
    b = Batch(tmp_path, episodes=3, max_steps=10, batch_steps=45)
    b.run()
    b.assert_halted("batch_steps", safety=False)
    assert not b.latch.is_set() and b.runner.monitor.steps <= 46
    c = Batch(tmp_path / "c", episodes=3, max_steps=10, batch_wall_s=50.0)
    c.run()
    c.assert_halted("batch_wall_clock", safety=False)


class PaidB2(cl.B2Driver):
    """The coded procedure, charged like a model: every step costs US$0.20."""

    def step(self, system_text, obs, prev, budget, log, sample_key=None):
        out = super().step(system_text, obs, prev, budget, log, sample_key=sample_key)
        budget.add(0.20)
        out["cost_usd"] = 0.20
        return out


def test_halt_usd_cap(tmp_path):
    spend = tmp_path / "spend.jsonl"
    budget = rp.Budget(1.0, 0.0, path=spend)
    b = Batch(tmp_path, episodes=2, max_steps=20, driver=PaidB2(), budget=budget)
    b.run()
    b.assert_halted("usd_cap", safety=False)
    assert 1.0 <= budget.spent <= 1.2 and rp.spent_in(spend) == pytest.approx(budget.spent)
    assert not b.latch.is_set()
    assert b.manifest["spent_usd"] == pytest.approx(budget.spent)
    rows = [json.loads(line) for line in open(b.out / "episodes" / "ep01-a1" / "seed_1.jsonl")]
    assert len(rows) == 5                                       # five paid steps, then no request was sent


def test_halt_start_pose_not_reached(tmp_path):
    b = Batch(tmp_path, max_steps=10, start_tol_m=0.01, start_tol_deg=1.0, start_attempts=2)
    b.run()
    b.assert_halted("start_pose", safety=True)
    assert "attempts (tolerance 0.01 m, 1 degrees)" in b.result["halt"]["detail"]


def test_halt_drive_map_does_not_take(tmp_path):
    b = Batch(tmp_path, sim_params={"map_min_duty": 0.46, "map_max_speed_mps": 0.215})    # the car's boot map
    b.rig.link.set_drive_map = lambda duty, speed: [0.46, 0.215]                           # and the setting is lost
    b.run()
    b.assert_halted("drive_map", safety=True)
    assert b.runner.monitor.steps == 0 and b.rig.link.published == []                      # nothing moved


def test_drive_map_is_applied_at_the_start(tmp_path):
    b = Batch(tmp_path, max_steps=3, sim_params={"map_min_duty": 0.46, "map_max_speed_mps": 0.215})
    assert b.run()["status"] == "complete"
    assert (b.rig.link.sim.p.map_min_duty, b.rig.link.sim.p.map_max_speed_mps) == (0.25, 0.33)


def test_halt_no_room_for_the_first_scan(tmp_path):
    b = Batch(tmp_path, place={"x_m": 0.95, "y_m": 2.9, "theta_deg": 0.0}, taped={"x_m": 0.95, "y_m": 2.9, "theta_deg": 0.0})
    b.run()
    b.assert_halted("guard_blocked", safety=True)
    assert b.runner.monitor.steps == 0


def test_halt_recorder_stops(tmp_path):
    b = Batch(tmp_path, max_steps=40)
    state = {"ok": True}
    b.runner.monitor.recorder_check = lambda: None if state["ok"] else "the recorder session is no longer active"
    b.at_moves(28, lambda b: state.update(ok=False))
    b.run()
    b.assert_halted("recorder", safety=True)


def test_halt_on_an_unexpected_error(tmp_path):
    b = Batch(tmp_path, max_steps=40)

    def broken(*args, **kwargs):
        raise RuntimeError("harness blew up")
    b.runner.run_episode = broken
    b.run()
    b.assert_halted("error", safety=True)
    assert b.manifest["episodes"][0]["status"] == "failed"


def test_a_guarded_move_is_refused_not_driven(tmp_path):
    """The guard inside an episode: a move toward the edge comes back `refused` and the car does not move."""
    b = Batch(tmp_path)
    r = b.runner
    r.preflight()
    env = r._service_env("t", str(tmp_path / "t"))
    env.reset(1)
    r.tracker.set({"x_m": 3.3, "y_m": 2.6, "theta_deg": 0.0}, 0.03, 1.0)       # believed 0.5 m from the window wall
    before, sent = b.rig.link.sim.truth(), len(b.rig.link.published)
    sense = env.step("FORWARD_25")
    assert sense["move"]["result"] == "refused" and sense["move"]["reason"].startswith("batch guard: FORWARD_25 would end")
    assert b.rig.link.sim.truth() == before and len(b.rig.link.published) == sent and env.blocked == 1
    assert sense["safety"]["forward_allowed"] == [] and r.monitor.halted is None            # refused, not a halt


def test_resume_skips_finished_episodes_and_never_replays_an_unfinished_one(tmp_path):
    b = Batch(tmp_path, episodes=2, max_steps=20, starts=(S1, S5))
    seen = {"n": 0}

    def stop_in_second(b):
        b.latch.set("operator STOP (key)", "bm_stop")
    walls = b.rig.link.on_step

    def hook(link):
        if walls:
            walls(link)
        eps = b.runner.manifest["episodes"] if b.runner.manifest else []
        if len(eps) == 2 and not seen["n"] and (b.out / "episodes" / "ep02-a1" / "seed_2.jsonl").exists():
            seen["n"] = 1
            stop_in_second(b)
    b.rig.link.on_step = hook
    b.run()
    assert b.result["halt"]["code"] == "latch"
    assert [(e["id"], e["status"]) for e in b.manifest["episodes"]] == [("ep01-a1", "done"), ("ep02-a1", "halted")]
    b.rig.link.on_step = walls
    refused = B.BatchRunner(b.params, b.rig, WORLD, b.out, driver=cl.B2Driver(), budget=b.budget, log=lambda *a: None,
                            run_episode=cl.run_episode).run()
    assert refused["status"] == "refused"                       # until the operator clears both
    b.latch.clear("xiaohui")
    assert vd.clear_latch_file(b.out / "HALT.LATCH", "xiaohui")
    moves = b.runner.monitor.steps
    again = B.BatchRunner(b.params, b.rig, WORLD, b.out, driver=cl.B2Driver(), budget=b.budget, log=lambda *a: None,
                          run_episode=cl.run_episode)
    again.tracker = b.runner.tracker                            # the same car, where it stopped
    again.localised = True
    assert again.run() == {"status": "complete", "halt": None}
    m = json.loads((b.out / "manifest.json").read_text())
    assert [(e["id"], e["status"]) for e in m["episodes"]] == [("ep01-a1", "done"), ("ep02-a1", "halted"), ("ep02-a2", "done")]
    assert m["resumes"] == 1 and m["moves_sent"] == moves + again.monitor.steps
    first = [json.loads(line) for line in open(b.out / "episodes" / "ep01-a1" / "seed_1.jsonl")]
    assert len(first) == 20                                     # the finished episode was not run again
    other = Batch(tmp_path, episodes=3, max_steps=20, starts=(S1, S5))                     # another configuration
    assert other.run()["status"] == "refused"


def test_a_resumed_batch_takes_the_cars_new_taped_pose(tmp_path):
    """After a halt the car is somewhere else. The resumed run is given its new pose; that is the same batch, and
    the first circle must confirm the pose before anything else happens."""
    s2 = {"id": "S2", "x_m": 1.75, "y_m": 1.4, "theta_deg": 0.0}
    b = Batch(tmp_path, episodes=2, max_steps=8, starts=(S1, s2))
    b.at_moves(40, lambda b: b.latch.set("operator STOP (key)", "bm_stop"))
    b.run()
    assert b.result["halt"]["code"] == "latch"
    b.rig.link.on_step = None
    b.latch.clear("xiaohui")
    assert vd.clear_latch_file(b.out / "HALT.LATCH", "xiaohui")
    here = b.rig.sim_truth_fn()
    taped = {"x_m": here["x_m"] + 0.05, "y_m": here["y_m"] - 0.05, "theta_deg": here["theta_deg"] + 8.0}
    params = B.BatchParams(**dict(B.asdict(b.params), initial_pose=taped))
    assert params.digest() == b.params.digest()                 # the initial pose alone does not change the batch
    assert B.BatchParams(**dict(B.asdict(b.params), max_steps=9)).digest() != b.params.digest()
    again = B.BatchRunner(params, b.rig, WORLD, b.out, driver=cl.B2Driver(), budget=b.budget, log=lambda *a: None,
                          run_episode=cl.run_episode)
    assert again.tracker.pose == taped and again.localised is False
    assert again.run()["status"] == "complete"
    m = json.loads((b.out / "manifest.json").read_text())
    assert len(m["initial_poses"]) == 2 and m["resumes"] == 1 and "last_tracked_pose_world" in m
    assert [e["status"] for e in m["episodes"]].count("done") == 2
    resumed = [e for e in m["episodes"] if e["status"] == "done"][-1]
    assert resumed["first_fix"]["ok"]                           # the circle confirmed where the car was


def test_the_first_circle_must_give_a_fix_and_a_wrong_taped_pose_halts(tmp_path):
    """Taped pose 1.5 m from where the car stands: the first circle's fix is far from it, so it is refused, and
    because nothing has confirmed the pose yet the batch halts rather than trust the tape."""
    b = Batch(tmp_path, taped={"x_m": 2.6, "y_m": 3.2, "theta_deg": 60.0})
    b.run()
    assert b.result["halt"]["code"] in ("fix_conflict", "no_fix")          # whichever notices first
    b.assert_halted(b.result["halt"]["code"], safety=True)
    assert b.runner.monitor.steps <= 24 and not b.manifest["episodes"][0].get("start_fix")


def load_batch_tool():
    spec = importlib.util.spec_from_file_location("car_batch", ROOT / "tools" / "car_batch.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    return tool


def test_a_run_that_died_without_a_record_needs_an_operator(tmp_path):
    """Killed, power cut, a crash: the manifest still says `running` and nobody knows the car's state. The next run
    refuses and writes the halt; after an operator's clear-halt the dead episode is abandoned, never replayed."""
    b = Batch(tmp_path, episodes=1, max_steps=6)
    b.run()
    m = json.loads((b.out / "manifest.json").read_text())
    m["episodes"][0]["status"], m["status"] = "running", "running"         # as a killed process leaves it
    (b.out / "manifest.json").write_text(json.dumps(m))
    sent = len(b.rig.link.published)

    def rerun():
        r = B.BatchRunner(b.params, b.rig, WORLD, b.out, driver=cl.B2Driver(), budget=b.budget, log=lambda *a: None,
                          run_episode=cl.run_episode)
        r.tracker, r.localised = b.runner.tracker, True
        return r.run()
    assert rerun()["status"] == "refused" and len(b.rig.link.published) == sent
    assert "ended without a record" in vd.read_latch_file(b.out / "HALT.LATCH")["reason"]
    assert rerun()["status"] == "refused"
    assert load_batch_tool().main(["clear-halt", "--out", str(b.out), "--operator", "xiaohui"]) == 0
    assert json.loads((b.out / "manifest.json").read_text())["status"] == "cleared"
    assert rerun()["status"] == "complete"
    m = json.loads((b.out / "manifest.json").read_text())
    assert [(e["id"], e["status"]) for e in m["episodes"]] == [("ep01-a1", "abandoned"), ("ep01-a2", "done")]


# ================================================================ added after the independent review's probes

class Thinker(cl.B2Driver):
    """The coded procedure with a model's habit: before step k it thinks for 20 s, during which a fault appears."""

    def __init__(self, k, fault):
        super().__init__()
        self.k, self.fault, self.n, self.batch = k, fault, 0, None

    def step(self, *args, **kwargs):
        if self.n == self.k:
            b = self.batch
            self.fault(b)
            b.rig.link.wait(20.0)
            self.sent, self.moves = len(b.rig.link.published), b.runner.monitor.steps
        self.n += 1
        return super().step(*args, **kwargs)


def _stale(b):
    real = b.rig.link.car_state
    b.rig.link.car_state = lambda: dict(real(), telemetry_age_s=3.0)


def _timeout_stop(b):
    real = b.rig.link.car_state
    b.rig.link.car_state = lambda: dict(real(), drive_status=2)


def _disarmed(b):
    real = b.rig.link.car_state
    b.rig.link.car_state = lambda: dict(real(), armed=False)


def _camera_dead(b):
    def dead(_n):
        raise CameraError("timed out")
    b.rig.camera.frame_fn = dead


@pytest.mark.parametrize("fault, code", [
    (lambda b: setattr(b.rig.link.sim.p, "vsys_mv", 4100), "supply_low"), (_stale, "telemetry_stale"),
    (_timeout_stop, "command_timeout"), (_disarmed, "car_disarmed"), (_camera_dead, "camera"),
    (lambda b: setattr(b.runner.monitor, "recorder_check", lambda: "the recorder session is no longer active"), "recorder"),
    (lambda b: b.latch.set("operator STOP (key)", "bm_stop"), "latch"),
], ids=["supply", "telemetry", "command-timeout", "disarmed", "camera", "recorder", "latch"])
def test_a_fault_while_the_agent_thinks_stops_the_next_move(tmp_path, fault, code):
    """The review's probe: the fault appears between two steps (a model thinks for 15 s). The car is looked at
    again BEFORE the move the agent then asks for: no move is sent and no motion command is published."""
    driver = Thinker(3, fault)
    b = Batch(tmp_path, max_steps=12, driver=driver)
    driver.batch = b
    b.run()
    assert b.result["halt"]["code"] == code, b.result
    assert b.runner.monitor.steps == driver.moves                              # not one move after the fault
    assert all((v, w) == (0.0, 0.0) for _t, v, w in b.rig.link.published[driver.sent:])
    b.assert_halted(code, safety=code not in ("latch",))


def test_a_fault_after_the_last_move_is_not_a_complete_batch(tmp_path):
    b = Batch(tmp_path, max_steps=5)
    real_run = cl.run_episode
    b.at_moves(10 ** 9, lambda b: None)
    walls = b.rig.link.on_step
    state = {"scans": 0}
    real_scan = b.runner.scan

    def scan(env, what):
        fix = real_scan(env, what)
        state["scans"] += 1
        if "end pose" in what:                                 # the very last moves of the batch are done
            b.rig.link.sim.p.vsys_mv = 4000
            b.rig.link.wait(0.1)
        return fix
    b.runner.scan = scan
    b.run()
    b.assert_halted("supply_low", safety=True)
    assert b.manifest["episodes"][0]["status"] == "done" and b.manifest["status"] == "halted"
    assert real_run is cl.run_episode and walls is not None


def test_a_fix_that_disagrees_with_the_tracked_pose_is_not_blended_in(tmp_path):
    t = B.PoseTracker(S1, 0.06, 2.0)
    good = {"pose": {"x_m": 2.56, "y_m": 1.53, "theta_deg": 90.0}, "sigma_xy_m": 0.08}
    bad = {"pose": {"x_m": 2.95, "y_m": 1.5, "theta_deg": 90.0}, "sigma_xy_m": 0.08}       # 0.45 m away
    assert not t.disagrees(good) and t.disagrees(bad)
    t.sigma_xy_m = 0.25
    assert not t.disagrees(bad)                                 # with that much doubt it is plausible again


def test_a_tag_surveyed_wrongly_halts_before_the_car_reaches_a_wall(tmp_path):
    """The review's probe: one tag is 0.4 m away from where the world file says (the simulator sees it where it
    really is). Before the fix the tracked pose followed that tag and the car drove into the wall. Now the first
    circle that includes the tag refuses to fix (its tags disagree), or the per-step fixes are rejected and the
    batch halts; either way the simulated footprint stays inside the driving area with room to spare."""
    wrong = json.loads(json.dumps(WORLD))
    for tag in wrong["tags"]:
        if tag["uid"] == "T11":
            tag["y_m"] -= 0.4
    for seed in (1, 2, 3):
        out = tmp_path / ("s%d" % seed)
        latch = Latch(out / "LATCH")
        params = B.BatchParams(world_path="x", start_poses=[{"id": "N", "x_m": 2.9, "y_m": 4.2, "theta_deg": 90.0}],
                               initial_pose=dict(TAPED), episodes=1, max_steps=60, max_range_m=2.5)
        rig = B.dry_rig(WORLD, PLACE, latch=latch, seed=seed, max_range_m=2.5)         # the real room
        runner = B.BatchRunner(params, rig, wrong, out / "batch", driver=cl.B2Driver(), budget=rp.Budget(float("inf")),
                               log=lambda *a: None, run_episode=cl.run_episode)     # the runner's (wrong) survey
        depth = {"min": 9.0}
        walls = rig.link.on_step

        def watch(link, walls=walls, depth=depth, runner=runner, rig=rig):
            walls(link)
            depth["min"] = min(depth["min"], runner.guard.footprint_depth(rig.sim_truth_fn()))
        rig.link.on_step = watch
        result = runner.run()
        assert depth["min"] > 0.05, (seed, depth, result)       # never at the wall
        assert result["status"] == "halted" and result["halt"]["code"] in ("no_fix", "fix_conflict", "start_pose",
                                                                             "guard_blocked", "pose_uncertain"), result
        assert not rig.link.sim.p.blocked_left                  # and the simulated wall was never touched


def test_obstacles_count_even_without_a_separate_driving_area():
    """A world file that gives only the walls and the desk box: the desk is still not drivable."""
    from beaconmind.car.config import load_car
    world = json.loads(json.dumps(WORLD))
    del world["arena"]["drive_polygon_m"]
    c = load_car()
    g = B.MoveGuard(world, [tuple(p) for p in c["corners"]], float(c["sweep_radius_m"]), 0.15, 0.25)
    assert g.axle_depth({"x_m": 0.3, "y_m": 2.9, "theta_deg": 0.0}) < 0                    # inside the desk box
    assert g.check("FORWARD_25", {"x_m": 1.15, "y_m": 2.9, "theta_deg": 180.0}, 0.03)       # toward the desk face
    assert g.check("FORWARD_25", {"x_m": 2.4, "y_m": 2.9, "theta_deg": 180.0}, 0.03) is None
    clockwise = json.loads(json.dumps(WORLD))
    clockwise["arena"]["drive_polygon_m"].reverse()
    with pytest.raises(ValueError, match="counter-clockwise"):
        B.MoveGuard(clockwise, [(0.0, 0.0)], 0.178, 0.15, 0.25)


def test_a_halt_that_cannot_be_written_sets_the_project_latch(tmp_path):
    """The review's probe: HALT.LATCH cannot be written (a full or read-only batch folder). A non-safety halt
    then sets the project latch instead, so a rerun still finds something an operator must clear."""
    latch = Latch(tmp_path / "LATCH")
    params = B.BatchParams(world_path="x", start_poses=[S1], initial_pose=dict(TAPED))
    (tmp_path / "blocker").write_text("a file where the batch folder should be")
    m = B.Monitor(params, tmp_path / "blocker" / "HALT.LATCH", latch, log=lambda *a: None)
    halt = m.halt("batch_steps", "40 moves sent, cap 40")       # by itself not a safety halt
    assert not (tmp_path / "blocker" / "HALT.LATCH").exists() and m.latch_error
    assert halt["safety"] is True
    assert latch.is_set() and latch.read()["by"] == "car_batch"


def test_detections_that_are_not_numbers_never_reach_the_pose(tmp_path):
    pose = {"x_m": 2.5, "y_m": 1.5, "theta_deg": 90.0}
    dets = view_from(pose) + [{"id": 23, "range_m": float("nan"), "bearing_deg": 0.0},
                              {"id": 12, "range_m": 1.0, "bearing_deg": float("inf")}, {"id": 10, "range_m": -1.0, "bearing_deg": 0.0},
                              {"id": 10, "range_m": None, "bearing_deg": 0.0}]
    fix = R.resect([{"pose": None, "detections": dets}], TAGS)
    assert fix["ok"] and fix["pose"]["x_m"] == pytest.approx(2.5, abs=1e-6)
    only_bad = [{"id": 23, "range_m": float("nan"), "bearing_deg": 0.0}]
    assert R.position_fix(only_bad, TAGS, pose, 3.0)["ok"] is False
    b = Batch(tmp_path)
    r = b.runner
    r.preflight()
    env = r._service_env("t", str(tmp_path / "t"))
    env.inner.detector = lambda jpegs, n=None: {"detections": [{"det": 0, "id": 23, "range_m": float("nan"), "bearing_deg": 1.0,
                                                               "quality": 1.0}], "internal": [], "per_frame": []}
    env.reset(1)
    assert all(math.isfinite(v) for v in r.tracker.pose.values()) and r.monitor.halted is None


def test_an_interrupted_episode_is_halted_in_the_manifest(tmp_path):
    b = Batch(tmp_path, max_steps=20)

    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt
    b.runner.run_episode = interrupt
    b.run()
    b.assert_halted("interrupted", safety=False)
    assert b.manifest["episodes"][0]["status"] == "halted"


def test_the_move_cap_counts_the_whole_batch_not_one_run(tmp_path):
    b = Batch(tmp_path, episodes=4, max_steps=6, batch_steps=45)
    b.run()
    b.assert_halted("batch_steps", safety=False)
    first = b.runner.monitor.steps
    assert vd.clear_latch_file(b.out / "HALT.LATCH", "xiaohui")
    again = B.BatchRunner(b.params, b.rig, WORLD, b.out, driver=cl.B2Driver(), budget=b.budget, log=lambda *a: None,
                          run_episode=cl.run_episode)
    again.tracker = b.runner.tracker
    result = again.run()
    assert result["halt"]["code"] == "batch_steps" and again.monitor.steps <= 1          # the cap was already used up
    assert json.loads((b.out / "manifest.json").read_text())["moves_sent"] <= first + 1


def test_a_stale_camera_frame_is_an_error():
    from beaconmind.car.camera import HttpCamera
    jpeg = b"\xff\xd8" + b"x" * 50 + b"\xff\xd9"
    seqs = iter([7, 8, 8, 9, 2])

    def grabber(url, timeout):
        return 200, {"X-BM-Seq": str(next(seqs)), "X-BM-Width": "1024", "X-BM-Height": "768"}, jpeg
    cam = HttpCamera("http://cam.invalid", grabber=grabber)
    cam.grab()
    cam.grab()
    with pytest.raises(CameraError, match="stale picture"):
        cam.grab()                                              # frame 8 again: the camera (or a relay) is not live
    cam.grab()
    cam.grab()                                                  # a counter that restarts is a camera reboot: taken
    assert cam.errors == 1 and cam.last_seq == 2



def test_a_wrong_encoder_scale_halts_before_the_car_reaches_a_wall(tmp_path):
    """The review's probe: the odometer reads 25 % short (a wrong car.json). The tracked pose then lags the car, and
    before this check the car drove into the wall with a confident pose. Tag fixes that keep landing ahead of the
    odometry along the way driven now halt the batch."""
    from beaconmind.car import config as C
    cfg = C.load_config()
    wrong = cfg.replace(ticks_per_m_left=cfg.ticks_per_m_left / 0.75, ticks_per_m_right=cfg.ticks_per_m_right / 0.75)
    for seed in (1, 2, 3):
        out = tmp_path / ("s%d" % seed)
        latch = Latch(out / "LATCH")
        params = B.BatchParams(world_path="x", start_poses=[S1], initial_pose=dict(TAPED), episodes=1, max_steps=80,
                               max_range_m=2.5)
        rig = B.dry_rig(WORLD, PLACE, latch=latch, seed=seed, max_range_m=2.5, cfg=wrong)
        runner = B.BatchRunner(params, rig, WORLD, out / "batch", driver=cl.B2Driver(), budget=rp.Budget(float("inf")),
                               log=lambda *a: None, run_episode=cl.run_episode)
        depth = {"min": 9.0}
        walls = rig.link.on_step

        def watch(link, walls=walls, depth=depth, runner=runner, rig=rig):
            walls(link)
            depth["min"] = min(depth["min"], runner.guard.footprint_depth(rig.sim_truth_fn()))
        rig.link.on_step = watch
        result = runner.run()
        assert result["status"] == "halted", (seed, result)
        assert depth["min"] > 0.03 and not rig.link.sim.p.blocked_left, (seed, depth, result)
        assert result["halt"]["code"] in ("odometry_scale", "fix_conflict", "start_pose", "no_fix", "guard_blocked"), result


def test_a_correct_odometer_is_not_called_biased(tmp_path):
    b = Batch(tmp_path, max_steps=60, max_range_m=2.5)
    assert b.run()["status"] == "complete"
    bias = b.runner.tracker.odometry_bias()
    assert bias is not None and abs(bias[0]) < 0.06 and bias[1] > 1.0


def test_telemetry_stopping_between_moves_is_named_and_sends_no_move(tmp_path):
    """The review's sweep: telemetry stops while the car stands between two moves. The executor refuses the next
    move; the batch names the cause (not "executor_refused") and does not count a move that was never sent."""
    b = Batch(tmp_path, max_steps=40)
    b.at_moves(28, lambda b: b.rig.link.sim.p.telemetry_drop.append((b.rig.link.t + 1.5, 1e9)))
    b.run()
    assert b.result["halt"]["code"] in ("telemetry_stale", "link_lost"), b.result
    b.assert_halted(b.result["halt"]["code"], safety=True)


# ================================================================ added for the relayed review (findings 1, 2, 6, 7, 14)

def test_the_first_circle_speaks_without_the_tape_and_a_disagreement_halts(tmp_path):
    """Review finding 2. The taped pose is 0.8 m wrong. The first circle is solved without it, differs from it by
    more than the gate, and the batch halts: no view fix was judged against the wrong pose, no forward move ran."""
    b = Batch(tmp_path, taped={"x_m": 2.3, "y_m": 2.5, "theta_deg": 60.0})
    b.run()
    b.assert_halted("no_fix", safety=True)
    assert "from the taped pose" in b.result["halt"]["detail"]
    assert all(v == 0.0 for _t, v, _w in b.rig.link.published)                 # turns only: not one forward move
    assert b.runner.monitor.steps == 24                                        # two circles, then the halt


def test_no_forward_move_before_a_circle_has_confirmed_the_pose(tmp_path):
    """Whatever the taped pose, the first motion commands of a process are the circle's turns."""
    for taped in (TAPED, {"x_m": 2.45, "y_m": 1.55, "theta_deg": 45.0}, {"x_m": 3.0, "y_m": 2.4, "theta_deg": -100.0}):
        b = Batch(tmp_path / ("t%d" % int(taped["theta_deg"] % 360)), max_steps=3, taped=taped)
        b.run()
        turns = 0
        for _t, v, w in b.rig.link.published:
            if v != 0.0:
                break
            turns += w != 0.0
        assert b.runner.localised or b.result["status"] == "halted"
        if b.result["status"] == "complete":
            assert b.manifest["episodes"][0]["first_fix"]["ok"]
        assert turns > 100 or b.result["status"] == "halted"                   # twelve turns' worth of commands first


def test_the_first_circle_needs_room_for_a_wrong_tape(tmp_path):
    b = Batch(tmp_path, place={"x_m": 1.3, "y_m": 2.9, "theta_deg": 0.0}, taped={"x_m": 1.3, "y_m": 2.9, "theta_deg": 0.0})
    b.run()                                                     # 0.64 m from the desk line: fine once confirmed,
    b.assert_halted("guard_blocked", safety=True)               # not enough for an unconfirmed pose
    assert "nearer the middle" in b.result["halt"]["detail"] and b.runner.monitor.steps == 0


def test_a_rerun_from_the_tracked_pose_with_a_new_process(tmp_path, capsys):
    """Review findings 1 and 2 through the tool: the batch folder is found again by its name, the halt blocks the
    rerun, and after the operator's clear a new process starts from the pose the batch last tracked (`last`)."""
    tool = load_batch_tool()
    out = tmp_path / "batches" / "night1"
    base = ["run", "--world", str(WORLD_PATH), "--start", "S1:2.5,1.5,90", "--start", "S2:1.75,1.4,0", "--episodes", "2",
            "--max-steps", "6", "--dry-run", "--out", str(out)]
    assert tool.main(base + ["--initial-pose", "2.4,1.6,70", "--batch-steps", "45"]) == 3
    assert "HALTED: batch_steps" in capsys.readouterr().out
    assert tool.main(base + ["--initial-pose", "last", "--batch-steps", "45"]) == 2        # the halt is still there
    capsys.readouterr()
    assert tool.main(["clear-halt", "--out", str(out), "--operator", "xiaohui"]) == 0
    # (a dry run's simulated car starts where it is put, so `last` also places the simulated car there)
    assert tool.main(base + ["--initial-pose", "last", "--batch-steps", "45"]) == 3        # the cap counts the whole batch
    text = capsys.readouterr().out
    assert "HALTED: batch_steps" in text and "resumes: 1" in text
    with pytest.raises(SystemExit, match="no tracked pose"):
        tool.main(["run", "--world", str(WORLD_PATH), "--start", "2.5,1.5,90", "--initial-pose", "last", "--dry-run",
                   "--out", str(tmp_path / "nothing")])
    with pytest.raises(SystemExit, match="--label"):
        tool.main(["run", "--world", str(WORLD_PATH), "--start", "2.5,1.5,90", "--initial-pose", "2.5,1.5,90"])
    with pytest.raises(SystemExit, match="name, not a path"):
        tool.main(["run", "--world", str(WORLD_PATH), "--start", "2.5,1.5,90", "--initial-pose", "2.5,1.5,90",
                   "--label", "../x"])


def test_the_wall_clock_cap_counts_the_whole_batch(tmp_path):
    b = Batch(tmp_path, episodes=4, max_steps=6, batch_wall_s=70.0)
    b.run()
    b.assert_halted("batch_wall_clock", safety=False)
    assert vd.clear_latch_file(b.out / "HALT.LATCH", "xiaohui")
    again = B.BatchRunner(b.params, b.rig, WORLD, b.out, driver=cl.B2Driver(), budget=b.budget, log=lambda *a: None,
                          run_episode=cl.run_episode)
    again.tracker, again.localised = b.runner.tracker, True
    again.monitor.t_batch = again.monitor.clock()
    result = again.run()
    assert result["halt"]["code"] == "batch_wall_clock" and again.monitor.steps <= 1


def test_terminate_and_hangup_end_like_an_interrupt():
    """Review finding 6: docker stop, kill and a closed terminal must leave a halt record, as Ctrl+C does."""
    tool = load_batch_tool()
    with pytest.raises(KeyboardInterrupt):
        tool._as_interrupt(15, None)
    source = (ROOT / "tools" / "car_batch.py").read_text()
    assert "for sig in (signal.SIGTERM, signal.SIGHUP):" in source and "signal.signal(sig, _as_interrupt)" in source
    assert "&& exec python3 /workspace/course-project/tools/car_batch.py" in (ROOT / "tools" / "car_batch.sh").read_text()


def test_a_recorder_that_stopped_writing_is_noticed(tmp_path):
    """Review finding 14: a crashed recorder leaves data/real/.active behind."""
    tool = load_batch_tool()
    session = tmp_path / "sess"
    assert "cannot be read" in tool.recorder_silent(str(session))
    (session / "logs").mkdir(parents=True)
    (session / "logs" / "ping_car.log").write_text("x")
    import os as _os
    now = _os.path.getmtime(session / "logs" / "ping_car.log")
    assert tool.recorder_silent(str(session), now=now + 30) is None
    assert "written nothing for 300 s" in tool.recorder_silent(str(session), now=now + 300)


def service_env(tmp_path, **kw):
    b = Batch(tmp_path, **kw)
    r = b.runner
    r.preflight()
    r.localised = True
    env = r._service_env("t", str(tmp_path / "t"))
    env.reset(1)
    return b, r, env


def test_halt_imu_not_ready_before_a_move(tmp_path):
    b, r, env = service_env(tmp_path)
    real = b.rig.link.car_state
    b.rig.link.car_state = lambda: dict(real(), imu_ready=False)
    sense = env.step("TURN_LEFT_30")
    assert sense["move"]["result"] == "refused" and r.monitor.halted["code"] == "imu" and b.latch.is_set()
    assert b.rig.link.published == []


def test_halt_fix_conflict(tmp_path):
    """Three views in a row whose tags put the car far from the tracked pose (here: the tracked pose is moved)."""
    b, r, env = service_env(tmp_path)
    r.tracker.pose = {"x_m": 3.0, "y_m": 2.6, "theta_deg": PLACE["theta_deg"]}     # 1.1 m from where the car is
    r.tracker.sigma_xy_m = 0.06
    for _ in range(12):
        if r.monitor.halted:
            break
        env.step("TURN_LEFT_30")
    assert r.monitor.halted["code"] == "fix_conflict" and r.tracker.conflicts >= 3 and b.latch.is_set()
    assert math.hypot(r.tracker.pose["x_m"] - 3.0, r.tracker.pose["y_m"] - 2.6) < 0.02     # and it was not pulled over


def test_halt_executor_refusal(tmp_path):
    """The car lost its drive map (a restart the telemetry did not show): the executor refuses, the batch halts."""
    b, r, env = service_env(tmp_path)
    b.rig.link.sim.set_map(0.46, 0.215)
    b.rig.link.wait(0.1)
    sense = env.step("TURN_LEFT_30")
    assert sense["move"]["result"] == "refused" and sense["move"]["reason"].startswith("drive_map")
    assert r.monitor.halted["code"] == "executor_refused" and r.monitor.steps == 0


def test_halt_move_timeout(tmp_path):
    """A turn on a car that cannot rotate (both wheels slipping): the move times out, the batch halts on it."""
    b, r, env = service_env(tmp_path)
    b.rig.link.sim.p.slip_left = b.rig.link.sim.p.slip_right = 1.0
    sense = env.step("TURN_LEFT_30")
    assert sense["move"]["result"] == "timeout" and r.monitor.halted["code"] == "move_timeout" and b.latch.is_set()


def test_halt_in_preflight_from_the_latch_and_the_car(tmp_path):
    b = Batch(tmp_path)
    b.latch.set("operator STOP (key)", "bm_stop")
    b.run()
    b.assert_halted("latch", safety=False)
    assert b.runner.monitor.steps == 0 and b.rig.link.published == []
    c = Batch(tmp_path / "c", sim_params={"armed": False})
    c.run()
    c.assert_halted("car_disarmed", safety=True)
    assert c.runner.monitor.steps == 0


def test_halt_harness_latch(tmp_path):
    """The harness latches an episode by its own rules: the batch halts on it and sets the project latch."""
    b = Batch(tmp_path, max_steps=20)
    b.runner.run_episode = lambda *args, **kwargs: {"complete": True, "ended_by": "latch", "detail": "auto: 2 error observations",
                                                    "steps": 3}
    b.run()
    b.assert_halted("harness_latch", safety=True)


def test_halt_file_appearing_mid_run(tmp_path):
    b = Batch(tmp_path, max_steps=40)
    b.at_moves(30, lambda b: vd.write_latch_file(b.out / "HALT.LATCH", "batch halt: by hand", "operator"))
    b.run()
    assert b.result["halt"]["code"] == "latch" and b.runner.monitor.steps <= 31
    assert not b.rig.link.sim.moving



def test_the_transit_checks_the_encoder_scale_before_any_episode(tmp_path):
    """Review finding 8. The first transit is measured by odometry and by the tags. With the odometer reading 25 %
    short the batch halts there: no episode starts, and the simulated car is nowhere near a wall."""
    from beaconmind.car import config as C
    cfg = C.load_config()
    far = {"id": "F", "x_m": 2.4, "y_m": 2.9, "theta_deg": 90.0}             # 1.2 m from where the car stands
    good = Batch(tmp_path / "good", max_steps=3, starts=(far,), max_range_m=2.5)
    assert good.run()["status"] == "complete"
    check = good.manifest["episodes"][0]["odometry_scale_check"]
    assert check["checked"] and check["tags_over_odometry"] == pytest.approx(1.0, abs=0.08) and check["by_tags_m"] > 0.9
    for seed in (1, 2, 3):
        out = tmp_path / ("s%d" % seed)
        latch = Latch(out / "LATCH")
        wrong = cfg.replace(ticks_per_m_left=cfg.ticks_per_m_left / 0.75, ticks_per_m_right=cfg.ticks_per_m_right / 0.75)
        params = B.BatchParams(world_path="x", start_poses=[far], initial_pose=dict(TAPED), max_steps=80, max_range_m=2.5)
        rig = B.dry_rig(WORLD, PLACE, latch=latch, seed=seed, max_range_m=2.5, cfg=wrong)
        runner = B.BatchRunner(params, rig, WORLD, out / "batch", driver=cl.B2Driver(), budget=rp.Budget(float("inf")),
                               log=lambda *a: None, run_episode=cl.run_episode)
        result = runner.run()
        assert result["status"] == "halted" and result["halt"]["code"] in ("odometry_scale", "fix_conflict"), result
        assert not (out / "batch" / "episodes" / "ep01-a1" / "seed_1.jsonl").exists()      # no episode started
        assert runner.guard.footprint_depth(rig.sim_truth_fn()) > 0.5 and latch.is_set()
    near = Batch(tmp_path / "near", max_steps=3)                # S1 is 0.28 m away: too short to judge, and it says so
    near.run()
    assert near.manifest["episodes"][0]["odometry_scale_check"]["checked"] is False


def test_no_straight_move_takes_the_car_far_from_its_last_tag_fix(tmp_path):
    """The limit on distance driven without a tag fix (0.75 m): whatever the odometer's error, it stays inside the
    wall margin. Turns stay allowed: turning is how a tag comes into view."""
    b, r, env = service_env(tmp_path)
    env.inner.detector = lambda jpegs, n=None: {"detections": [], "internal": [], "per_frame": []}     # no tag in view
    r.tracker.set({"x_m": 2.2, "y_m": 1.6, "theta_deg": 90.0}, 0.06, 2.0)      # centre of the room, facing up it
    assert r.tracker.travel_since_fix_m == 0.0
    for i in range(3):
        sense = env.step("FORWARD_25")
        assert sense["move"]["result"] == "done", (i, sense["move"])
    assert 0.70 <= r.tracker.travel_since_fix_m <= 0.80
    assert sense["safety"]["forward_allowed"] == []             # the agent is told, not surprised
    before, sent = b.rig.link.sim.truth(), len(b.rig.link.published)
    refused = env.step("FORWARD_10")
    assert refused["move"]["result"] == "refused" and "since the last tag fix" in refused["move"]["reason"]
    assert b.rig.link.sim.truth() == before and len(b.rig.link.published) == sent
    assert env.step("TURN_LEFT_30")["move"]["result"] == "done" and r.monitor.halted is None
    r.tracker.correct_position({"pose": dict(r.tracker.pose), "sigma_xy_m": 0.08})         # a tag is seen again
    assert r.tracker.travel_since_fix_m == 0.0 and env._blind("FORWARD_25") is None


def test_a_weak_circle_is_blended_with_the_tracked_pose_not_trusted_alone(tmp_path):
    b = Batch(tmp_path, max_steps=3, starts=({"id": "F", "x_m": 2.4, "y_m": 2.9, "theta_deg": 90.0},), max_range_m=2.5)
    assert b.run()["status"] == "complete"
    fix = b.manifest["episodes"][0]["start_fix"]
    assert fix["ok"] and fix["sigma_xy_m"] <= b.params.scan_sigma_max_m
    sim, got = fix["sim_truth_world"], b.manifest["episodes"][0]["start_pose_world"]
    assert math.hypot(sim["x_m"] - got["x_m"], sim["y_m"] - got["y_m"]) < 0.08             # and it is right
    unconfirmed = Batch(tmp_path / "u", max_steps=3, max_range_m=1.3)                       # few tags in reach from the start
    unconfirmed.run()
    assert unconfirmed.result["status"] == "halted" and unconfirmed.result["halt"]["code"] == "no_fix"
    assert unconfirmed.runner.monitor.steps == 24               # a first circle is never blended with a tape reading
