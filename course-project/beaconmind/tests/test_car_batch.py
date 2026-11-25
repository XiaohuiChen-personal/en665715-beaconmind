"""The unattended batch runner on the simulated car in the simulated room: resection, the move guard, every health
halt, the manifest and its resume (plan/README.md section 3.6 "Unattended batches").

Nothing here touches ROS or the real car: the rig is batch.dry_rig (SimCar + the room simulator's detections).

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote these tests.
AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: added the tests at the end (usd_cap between episodes, two
faults in one scan, the tag check, the detector-noise file, quick signals); in older tests: tag_trust off in two that
use the 12-tag layout, `tag_survey` accepted where a wrong tag halts, the signal test after the first-signal change.
AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: the range check's, the drift's, the per-step statistic's and
the slip tests (the real batches' halts); later that day the drift test made record-only, the factor-two test each way
and the same-tag rule's test.
"""
import hashlib
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
    # a turn sweeps the camera end (0.178 m) and needs the turn margin plus one sigma beyond it; doubt needs more.
    # (Changed 2026-11-25 with the turn margin, 0.03 to 0.10 m, after the review's Monte Carlo of fix errors: 0.07 m
    # of room, allowed before, is not enough now; 0.14 m is.)
    assert "sweep circle" in g.check("TURN_LEFT_30", {"x_m": 0.86, "y_m": 2.9, "theta_deg": 0.0}, 0.02)
    assert "sweep circle" in g.check("TURN_RIGHT_30", {"x_m": 0.91, "y_m": 2.9, "theta_deg": 0.0}, 0.02)
    assert g.check("TURN_RIGHT_30", {"x_m": 0.98, "y_m": 2.9, "theta_deg": 0.0}, 0.02) is None
    assert g.check("TURN_RIGHT_30", {"x_m": 0.98, "y_m": 2.9, "theta_deg": 0.0}, 0.10)
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
    near = {"x_m": 3.30, "y_m": 2.6, "theta_deg": 0.0}          # (3.35 before the turn margin went to 0.10 m)
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
        self.min_depth = 9.0            # the simulated car's true footprint depth inside the driving area, at its worst
        walls = self.rig.link.on_step

        def watch(link):
            if walls:
                walls(link)
            if int(link.t * 1000) % 50 == 0:
                self.min_depth = min(self.min_depth, self.runner.guard.footprint_depth(self.rig.sim_truth_fn()))
        self.rig.link.on_step = watch
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
        assert self.min_depth > 0.0, "the simulated car's footprint left the driving area"
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
    b.assert_halted("link_lost", safety=True)                   # the executor ended the move link_lost and latched
    assert "telemetry_gap" in b.result["halt"]["detail"] and b.latch.read()["by"] == "executor"


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
    b.assert_halted("stall", safety=True)                       # under the stall floor: the host's stall rule fires


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
    # (tag_trust off, 2026-11-24: in the 12-tag layout at 2.0 m a circle seldom has four tags in reach, so few tags
    # can be checked and the resumed run, which checks again from scratch, would have none to steer a fix. This test
    # is about the resume bookkeeping; the trust rule has its own tests in the 20-tag room at the end of this file.)
    b = Batch(tmp_path, episodes=2, max_steps=20, starts=(S1, S5), tag_trust=False)
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
                                                                             "guard_blocked", "pose_uncertain",
                                                                             "tag_survey"), result
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
    assert all(math.isfinite(v) for v in r.tracker.pose.values())              # the pose never took it
    assert r.monitor.halted["code"] == "detector" and b.latch.is_set()         # and the batch halts on it
    assert env.step("TURN_LEFT_30")["move"]["result"] == "refused" and b.rig.link.published == []


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


def test_noisy_fixes_after_short_legs_do_not_call_a_correct_odometer_biased():
    """The first real practice batch (2026-11-25) halted `odometry_scale` (-23 %) with a correct odometer: one
    single-tag fix 0.21 m off (sigma 0.12 m), after five turns had moved the axle 5 cm, dominated the sum of
    innovations over the sum of legs. Replayed here with its numbers (legs, innovations along them, fix sigmas): the
    old ratio says -18 %, the weighted estimate says -10 % +- 22 %: not significant, no halt."""
    t = B.PoseTracker(S1, 0.05, 2.0)
    legs = [(0.247, 0.041, 0.178), (0.245, -0.001, 0.204), (0.100, 0.0, 0.182), (0.093, -0.009, 0.276),
            (0.051, -0.209, 0.123), (0.246, -0.017, 0.076), (0.245, -0.032, 0.062)]
    for leg, innovation, sigma in legs:
        t._leg = [0.0, leg]
        t.pose = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 90.0}
        t.sigma_xy_m = 0.05
        t._note_innovation({"pose": {"x_m": 0.0, "y_m": innovation, "theta_deg": 90.0}, "sigma_xy_m": sigma})
    assert t.bias_sum / t.bias_travel == pytest.approx(-0.184, abs=0.01)          # what halted the practice batch
    scale, travel, fixes, se = t.odometry_bias()
    assert scale == pytest.approx(-0.10, abs=0.02) and se == pytest.approx(0.22, abs=0.02)
    assert not (abs(scale) > 0.12 and abs(scale) > 3 * se)                       # no halt
    big = B.PoseTracker(S1, 0.05, 2.0)                                             # a real 25 % error, precise fixes
    for _ in range(8):
        big._leg = [0.0, 0.25]
        big.pose = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 90.0}
        big.sigma_xy_m = 0.05
        big._note_innovation({"pose": {"x_m": 0.0, "y_m": 0.0625, "theta_deg": 90.0}, "sigma_xy_m": 0.03})
    scale, travel, fixes, se = big.odometry_bias()
    assert scale == pytest.approx(0.25, abs=0.01) and scale > 3 * se            # halts


def test_a_correct_odometer_is_not_called_biased(tmp_path):
    # (tag_trust off, 2026-11-24: the 12-tag layout, see test_resume_...; this test is about the bias statistic)
    b = Batch(tmp_path, max_steps=60, max_range_m=2.5, tag_trust=False)
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
    """Review finding 6: docker stop, kill and a closed terminal must leave a halt record, as Ctrl+C does. Since
    2026-11-24 only the first of them counts: the later ones are ignored, so a second Ctrl+C cannot break off the
    move's stop or the halt record half written."""
    import signal
    tool = load_batch_tool()
    saved = {name: signal.getsignal(getattr(signal, name)) for name in tool.INTERRUPTS}
    try:
        with pytest.raises(KeyboardInterrupt):
            tool._as_interrupt(15, None)
        assert all(signal.getsignal(getattr(signal, name)) is tool._later_signal for name in tool.INTERRUPTS)
    finally:
        for name, handler in saved.items():
            signal.signal(getattr(signal, name), handler)
    assert set(tool.INTERRUPTS) == {"SIGINT", "SIGTERM", "SIGHUP"}
    source = (ROOT / "tools" / "car_batch.py").read_text()
    assert "for name in INTERRUPTS:" in source and "signal.signal(getattr(signal, name), _as_interrupt)" in source
    assert "&& exec python3 /workspace/course-project/tools/car_batch.py" in (ROOT / "tools" / "car_batch.sh").read_text()


def test_signals_in_quick_succession_still_leave_one_halt_record(tmp_path):
    """A real dry-run process gets SIGTERM, SIGINT and SIGHUP back to back (docker stop while someone presses
    Ctrl+C): it ends with status 3 and the halt record of the first, the running episode halted, nothing left
    `running`. (The Spark run of 2026-11-24 did the same through docker: README, "First execution".)"""
    import os
    import signal
    import subprocess
    import sys
    import time
    out = tmp_path / "batch"
    cmd = [sys.executable, str(ROOT / "tools" / "car_batch.py"), "run", "--world", str(WORLD_PATH), "--start",
           "S1:2.5,1.5,90", "--initial-pose", "2.4,1.6,70", "--episodes", "20", "--max-range", "2.5",
           "--batch-steps", "100000", "--dry-run", "--out", str(out)]
    env = dict(os.environ, PYTHONPATH=str(ROOT / "beaconmind" / "src"))
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    end = time.time() + 60
    while time.time() < end and not (out / "episodes" / "ep01-a1" / "seed_1.jsonl").exists():
        time.sleep(0.05)
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGINT):
        proc.send_signal(sig)
    text = proc.communicate(timeout=60)[0].decode(errors="replace")
    assert proc.returncode == 3 and "Traceback" not in text, text[-800:]
    m = json.loads((out / "manifest.json").read_text())
    assert m["status"] == "halted" and m["halt"]["code"] == "interrupted"
    assert all(e["status"] != "running" for e in m["episodes"])


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
    short the batch halts before the car comes near a wall. Changed 2026-11-25 (b2-real-01): the transit's comparison
    is a recorded dead-reckoning measurement (it drifted 14 % on the real car with a right encoder scale), so the halt
    now comes from the range check at the first forward move with a tag in view before and after it, in the episode
    (this transit, toward the room's tagless side, has none); the transit records the 1.33."""
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
        transit = json.loads((out / "batch" / "manifest.json").read_text())["episodes"][0]["dead_reckoning_transit"]
        assert transit["tags_over_odometry"] == pytest.approx(1.33, abs=0.03)          # recorded
        assert "ranges to the tags" in result["halt"]["detail"] and len(runner.tracker.range_moves) == 1, result
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


# ================================================================ the lead's list after the review (2026-11-18)

def test_repeated_fixes_from_the_same_tag_do_not_shrink_the_uncertainty():
    """Review finding 3: the same tag seen again repeats its survey error. The pose may follow it; sigma may not
    shrink on it. A different tag is new information. (Since 2026-11-25 the sigma may not stay above that fix's own
    either: test_a_same_tag_fix_leaves_the_sigma_no_larger_than_its_own.)"""
    t = B.PoseTracker(S1, 0.12, 3.0)
    fix = {"pose": {"x_m": 2.55, "y_m": 1.5, "theta_deg": 90.0}, "sigma_xy_m": 0.10, "tags": ["T06"]}
    t.correct_position(dict(fix))
    once = t.sigma_xy_m
    assert once < 0.12
    for _ in range(10):
        t.correct_position(dict(fix))
    assert t.sigma_xy_m == once and t.pose["x_m"] > 2.54        # followed, not sharpened
    t.correct_position(dict(fix, tags=["T05"]))
    assert t.sigma_xy_m < once                                  # another tag: it shrinks, down to the floor at most
    for name in ("T06", "T05", "T06", "T05", "T06", "T05"):
        t.correct_position(dict(fix, tags=[name]))
    assert t.sigma_xy_m == pytest.approx(0.05)


def test_a_same_tag_fix_leaves_the_sigma_no_larger_than_its_own():
    """The lead's decision of 2026-11-25 (the north 0.60 pose_uncertain halt of the slip-sigma dry runs): on a long run
    of one tag's fixes with the slip sigma on, the sigma climbed past sigma_block_m (0.25) between fixes and no fix of
    that tag brought it back, while the pose was within centimetres. Now a fix on exactly the last fix's tags leaves
    the sigma at min(the sigma, the fix's sigma): never larger than one fix of that tag says, never smaller (no
    inverse-variance gain from a repeated survey error). correct() and correct_position() alike."""
    for method in ("correct_position", "correct"):
        t = B.PoseTracker(S1, 0.12, 3.0, slip_sigma_per_m=0.3)
        fix = {"pose": {"x_m": 2.55, "y_m": 1.5, "theta_deg": 90.0}, "sigma_xy_m": 0.10, "sigma_theta_deg": 2.0,
               "tags": ["T06"]}
        getattr(t, method)(dict(fix))
        once = t.sigma_xy_m
        assert once == pytest.approx(math.sqrt(0.12 ** 2 * 0.10 ** 2 / (0.12 ** 2 + 0.10 ** 2)), abs=1e-6)
        for _ in range(4):                                      # a blind stretch on the slipping carpet
            t.predict({"forward_m": 0.25, "left_m": 0.0, "dtheta_deg": 0.0})
        grown = t.sigma_xy_m
        assert grown > 0.15
        getattr(t, method)(dict(fix))                           # the same tag again
        assert t.sigma_xy_m == pytest.approx(0.10)              # no larger than its own; the old rule kept `grown`
        a, b = grown ** 2, 0.10 ** 2
        assert t.sigma_xy_m > math.sqrt(a * b / (a + b))        # and no inverse-variance gain from it
        getattr(t, method)(dict(fix, sigma_xy_m=0.20))          # a worse fix of the same tag cannot raise it
        assert t.sigma_xy_m == pytest.approx(0.10)
        getattr(t, method)(dict(fix, sigma_xy_m=0.01))          # nor take it under the floor
        assert t.sigma_xy_m == pytest.approx(t.floor_m)


def test_guard_margin_has_a_floor_that_no_fix_can_lower():
    g = make_guard(margin=B.BatchParams(world_path="x", start_poses=[S1], initial_pose=TAPED).wall_margin_m)
    assert g.need(0.0) == 0.15 and g.need(0.05) == pytest.approx(0.25) and g.need(1.0) == pytest.approx(0.30)
    t = B.PoseTracker(S1, 0.2, 3.0)
    t.set(S1, 0.001, 0.1)
    assert t.sigma_xy_m == 0.05 and g.need(t.sigma_xy_m) == pytest.approx(0.25)        # never under 0.25 m in a batch


class CountingThinker(Thinker):
    def __init__(self, k, fault):
        super().__init__(k, fault)
        self.calls_after = 0

    def step(self, *args, **kwargs):
        if self.batch.runner.monitor.halted is not None:
            self.calls_after += 1
        return super().step(*args, **kwargs)


@pytest.mark.parametrize("fault, code", [(lambda b: setattr(b.rig.link.sim.p, "vsys_mv", 4100), "supply_low"),
                                         (_camera_dead, "camera")], ids=["supply", "camera"])
def test_no_paid_request_is_sent_after_a_halt(tmp_path, fault, code):
    """Review finding 9. A fault that shows at a sensing halts the batch; the harness would ask the agent once
    more before it ends the episode. The request is not sent: the agent is not called and nothing is spent."""
    class Paid(CountingThinker):
        def step(self, system_text, obs, prev, budget, log, sample_key=None):
            out = super().step(system_text, obs, prev, budget, log, sample_key=sample_key)
            budget.add(0.20)
            return out
    # the fault is planted at move 30, during a move: it is seen at that move's sensing, after which the harness
    # goes round its loop once more
    driver = Paid(10 ** 6, lambda b: None)
    budget = rp.Budget(100.0)
    b = Batch(tmp_path, max_steps=30, driver=driver, budget=budget)
    driver.batch = b
    b.at_moves(36, fault)                                      # inside the episode (the scans and the transit take about 30)
    b.run()
    b.assert_halted(code, safety=True)
    rows = [json.loads(line) for line in open(b.out / "episodes" / "ep01-a1" / "seed_1.jsonl")]
    assert driver.calls_after == 0                              # the agent was never asked after the halt
    paid = sum(1 for r in rows if r.get("cost_usd") or r.get("final_text"))
    assert budget.spent == pytest.approx(0.20 * paid) and paid in (len(rows), len(rows) - 1)   # nothing paid after it
    assert rows[-1]["episode_end"]["ended_by"] == "latch" or b.manifest["episodes"][0]["requests_not_sent_after_halt"] == 1


def test_the_driver_wrapper_sends_no_request_once_halted(tmp_path):
    """The second guard of finding 9, by itself: whatever the harness does, a halted batch's agent is not called."""
    b = Batch(tmp_path)

    class Never:
        arm = "never"

        def step(self, *args, **kwargs):
            raise AssertionError("a request was sent after the halt")
    agent = B.HaltAwareDriver(Never(), b.runner.monitor, b.rig.link)
    assert agent.arm == "never"
    b.rig.link.sim.p.vsys_mv = 4000                             # the fault appears while nobody is looking
    b.rig.link.wait(0.1)
    out = agent.step("", {}, None, rp.Budget(1.0), lambda *a: None)
    assert out["error"] == "budget cap reached" and out["cost_usd"] == 0.0 and agent.requests_refused == 1
    assert b.runner.monitor.halted["code"] == "supply_low" and b.latch.is_set()


def test_a_request_refused_by_the_wrapper_is_recorded_as_the_halt_not_as_the_spend_cap(tmp_path):
    """The fault appears while the agent is about to be asked (after the harness's own latch check): the wrapper
    refuses the request with the harness's cap answer. The manifest must name the real cause, not "usd cap"."""
    b = Batch(tmp_path, max_steps=20)
    real_step = cl.B2Driver.step
    calls = {"n": 0}

    class LateFault(cl.B2Driver):
        def step(self, *args, **kwargs):
            calls["n"] += 1
            return real_step(self, *args, **kwargs)
    b.runner.driver = LateFault()
    real_run = b.runner.run_episode

    def run_episode(agent, *args, **kwargs):
        inner_step = agent.step

        def step(*a, **k):
            if calls["n"] == 3:
                b.rig.link.sim.p.vsys_mv = 4000        # between the harness's latch check and the request
                b.rig.link.wait(0.1)
            return inner_step(*a, **k)
        agent.step = step
        return real_run(agent, *args, **kwargs)
    b.runner.run_episode = run_episode
    b.run()
    b.assert_halted("supply_low", safety=True)
    entry = b.manifest["episodes"][0]
    assert calls["n"] == 3 and entry["requests_not_sent_after_halt"] == 1
    assert entry["result"]["ended_by"] == "halt" and "supply_low" in entry["result"]["detail"]
    assert "usd_cap" not in (b.out / "summary.txt").read_text()


def test_pass_marker_is_for_one_world_file(tmp_path):
    """Review finding 10: the marker names the surveyed world file; a batch on another file is refused."""
    root = tmp_path / "course"
    for rel in B.MARKER_FILES:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("v1")
    _session(root, "stand-1", done=6)
    _session(root, "floor-1", done=12)
    world, other = tmp_path / "room-measured.json", tmp_path / "room-nominal.json"
    world.write_text("{\"measured\": true}")
    other.write_text("{\"measured\": false}")
    marker = root / "data" / "real" / "ATTENDED_PASS.json"
    B.write_pass_marker(str(marker), str(root), "xiaohui", "stand-1", "floor-1", world_path=str(world), now_unix=1000.0)
    assert B.check_pass_marker(str(marker), str(root), now_unix=1060.0, world_path=str(world)) == []
    assert "not the one the pass was recorded for" in B.check_pass_marker(str(marker), str(root), now_unix=1060.0,
                                                                        world_path=str(other))[0]
    world.write_text("{\"measured\": true, \"edited\": 1}")     # the same file, edited after the pass
    assert B.check_pass_marker(str(marker), str(root), now_unix=1060.0, world_path=str(world))
    B.write_pass_marker(str(marker), str(root), "xiaohui", "stand-1", "floor-1", now_unix=1000.0)      # no world named
    assert B.check_pass_marker(str(marker), str(root), now_unix=1060.0, world_path=str(other))
    tool = load_batch_tool()
    with pytest.raises(SystemExit):
        tool.main(["record-pass", "--operator", "x", "--stand-session", "a", "--floor-session", "b"])   # --world is required


def test_sigterm_during_a_batch_leaves_a_halt_record(tmp_path):
    """Review finding 6, for real: a dry-run batch in its own process, SIGTERM in the middle (what `docker stop`
    and `kill` send). The process ends with status 3, the manifest says halted: interrupted, HALT.LATCH exists, the
    running episode is `halted`, and a rerun refuses."""
    import os
    import signal
    import subprocess
    import sys
    import time
    out = tmp_path / "batch"
    cmd = [sys.executable, str(ROOT / "tools" / "car_batch.py"), "run", "--world", str(WORLD_PATH), "--start",
           "S1:2.5,1.5,90", "--start", "S2:1.75,1.4,0", "--initial-pose", "2.4,1.6,70", "--episodes", "40", "--max-range",
           "2.5", "--batch-steps", "100000", "--dry-run", "--out", str(out)]
    env = dict(os.environ, PYTHONPATH=str(ROOT / "beaconmind" / "src"))
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    end = time.time() + 60
    while time.time() < end and not (out / "episodes" / "ep01-a1" / "seed_1.jsonl").exists():
        time.sleep(0.05)
    assert proc.poll() is None, proc.communicate()[0].decode(errors="replace")[-600:]
    proc.send_signal(signal.SIGTERM)
    text = proc.communicate(timeout=60)[0].decode(errors="replace")
    assert proc.returncode == 3, text[-600:]
    m = json.loads((out / "manifest.json").read_text())
    assert m["status"] == "halted" and m["halt"]["code"] == "interrupted"
    assert m["episodes"][-1]["status"] == "halted" and all(e["status"] != "running" for e in m["episodes"])
    assert vd.read_latch_file(out / "HALT.LATCH")["reason"].startswith("batch halt: interrupted")
    again = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=120)
    assert again.returncode == 2 and "HALT.LATCH exists" in again.stdout + again.stderr


def test_usd_cap_between_two_episodes(tmp_path):
    """The cap is reached exactly as an episode ends: the next episode does not start (not even its scan)."""
    budget = rp.Budget(1.0, 0.0, path=tmp_path / "spend.jsonl")
    b = Batch(tmp_path, episodes=3, max_steps=5, driver=PaidB2(), budget=budget)       # five steps = US$1.00
    b.run()
    b.assert_halted("usd_cap", safety=False)
    assert [(e["id"], e["status"]) for e in b.manifest["episodes"]] == [("ep01-a1", "done")]
    assert budget.spent == pytest.approx(1.0) and not b.latch.is_set()


def test_an_exception_from_the_car_link_inside_an_episode_halts(tmp_path):
    b = Batch(tmp_path, max_steps=40)

    def broken(b):
        def execute(cmd):
            raise RuntimeError("link exploded")
        b.rig.link.execute = execute
    b.at_moves(30, broken)
    b.run()
    b.assert_halted("error", safety=True)
    assert "link exploded" in b.result["halt"]["detail"] and b.manifest["episodes"][0]["status"] == "failed"


def test_a_blocked_turn_inside_a_scan_halts(tmp_path):
    """guard_blocked raised from a scan: the tracked pose says the car is against the edge when the end circle
    begins, so its first turn is refused and the batch halts (it does not skip the circle)."""
    b = Batch(tmp_path, max_steps=4)
    real_localise = b.runner.localise

    def localise(env, what, required=True):
        if "end pose" in what:
            b.runner.tracker.set({"x_m": 0.80, "y_m": 2.9, "theta_deg": 0.0}, 0.05, 2.0)
        return real_localise(env, what, required)
    b.runner.localise = localise
    b.run()
    b.assert_halted("guard_blocked", safety=True)
    assert "end pose" in b.result["halt"]["detail"] and "sweep circle" in b.result["halt"]["detail"]


def test_a_car_restart_inside_a_scan_halts(tmp_path):
    b = Batch(tmp_path, max_steps=4)
    b.at_moves(6, lambda b: b.rig.link.sim.reboot())            # the sixth turn of the first circle
    b.run()
    assert b.result["halt"]["code"] in ("car_restart", "link_lost")
    b.assert_halted(b.result["halt"]["code"], safety=True)
    assert b.runner.monitor.steps <= 8 and "first_fix" not in b.manifest["episodes"][0]



# ================================================================ 2026-11-24: the paths CONTEXT.md named untested, the
# check of the surveyed tags against each other (review finding 3, the one left open), the tag pilot's noise file.
# AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote the tests below.

WORLD20_PATH = ROOT / "configs" / "arenas" / "real-room-plus8-160mm-nominal.json"
WORLD20 = json.loads(WORLD20_PATH.read_text())
TAGS20 = [{"id": t["id"], "uid": t["uid"], "x_m": t["x_m"], "y_m": t["y_m"]} for t in WORLD20["tags"]]
PLACE20 = {"x_m": 2.4, "y_m": 1.6, "theta_deg": 70.0}
CHECK = {"k": 4.0, "min_m": 0.15}


def test_usd_cap_between_two_episodes_is_the_check_before_the_next_episode(tmp_path):
    """The cap is reached exactly as episode 1 ends (five paid steps of US$0.20, cap US$1.00). The halt is the check
    between episodes (its own words, not the in-episode "stopped the episode"), episode 2 never begins (no folder, no
    circle, no transit: not one move after episode 1's end circle), and a new process on the same batch, the halt
    cleared, sends no move either: the spend already in spend.jsonl reaches the cap."""
    spend = tmp_path / "spend.jsonl"
    budget = rp.Budget(1.0, 0.0, path=spend)
    b = Batch(tmp_path, episodes=3, max_steps=5, driver=PaidB2(), budget=budget)
    real_episode, after_first = b.runner._episode, {}

    def episode(index):
        real_episode(index)
        after_first.setdefault("moves", b.runner.monitor.steps)
        after_first.setdefault("sent", len(b.rig.link.published))
    b.runner._episode = episode
    b.run()
    b.assert_halted("usd_cap", safety=False)
    assert b.result["halt"]["detail"] == "spent $1.00 of $1.00"
    assert [(e["id"], e["status"]) for e in b.manifest["episodes"]] == [("ep01-a1", "done")]
    assert not (b.out / "episodes" / "ep02-a1").exists()
    assert b.runner.monitor.steps == after_first["moves"]
    assert all((v, w) == (0.0, 0.0) for _t, v, w in b.rig.link.published[after_first["sent"]:])
    # a rerun: cleared by an operator, a new process, the spend counted again from the file
    assert vd.clear_latch_file(b.out / "HALT.LATCH", "xiaohui")
    sent = len(b.rig.link.published)
    again = B.BatchRunner(b.params, b.rig, WORLD, b.out, driver=PaidB2(), budget=rp.Budget(1.0, rp.spent_in(spend), path=spend),
                          log=lambda *a: None, run_episode=cl.run_episode)
    result = again.run()
    assert result["status"] == "halted" and result["halt"]["code"] == "usd_cap" and again.monitor.steps == 0
    assert all((v, w) == (0.0, 0.0) for _t, v, w in b.rig.link.published[sent:])
    assert rp.spent_in(spend) == pytest.approx(1.0)                     # and nothing more was spent


def test_two_faults_inside_one_scan_keep_the_first_cause(tmp_path):
    """Two halts raised inside one scan: at the fifth turn of the first circle the Pico's supply drops and the camera
    dies at once, so one sensing sees both. The first cause found (the car's state is read before the camera) is the
    batch's halt everywhere: result, manifest, summary, HALT.LATCH and the project latch. The second does not write
    over it, the circle is not finished, no move follows, and a rerun refuses."""
    b = Batch(tmp_path, max_steps=4)

    def both(b):
        b.rig.link.sim.p.vsys_mv = 4100
        _camera_dead(b)
    b.at_moves(5, both)
    b.run()
    b.assert_halted("supply_low", safety=True)
    assert vd.read_latch_file(b.out / "HALT.LATCH")["code"] == "supply_low"
    assert b.latch.read()["reason"].startswith("batch halt: supply_low")
    assert "first_fix" not in b.manifest["episodes"][0] and b.runner.monitor.steps <= 6
    assert "camera" not in b.manifest["halt"]["detail"]
    # and the other order: the camera's halt first (a stale frame twice), the supply after it, in the same circle
    c = Batch(tmp_path / "c", max_steps=4)
    c.at_moves(5, _camera_dead)
    real = c.rig.link.car_state
    c.rig.link.car_state = lambda: dict(real(), vsys_min_mv=4100) if c.runner.monitor.halted else real()
    c.run()
    c.assert_halted("camera", safety=True)
    assert vd.read_latch_file(c.out / "HALT.LATCH")["code"] == "camera"


def circle_views(pose, tags, max_range=3.0, hfov=46.9, noise=None):
    """Twelve views 30 degrees apart from an arena pose, each with the exact (or noisy) detections of `tags` (where the
    tags REALLY are), as BatchRunner.scan gives them to resect."""
    views = []
    for k in range(12):
        heading = pose["theta_deg"] + 30.0 * k
        dets = []
        for t in tags:
            dx, dy = t["x_m"] - pose["x_m"], t["y_m"] - pose["y_m"]
            rng = math.hypot(dx, dy)
            bearing = R.wrap_deg(math.degrees(math.atan2(dy, dx)) - heading)
            if rng <= max_range and abs(bearing) <= hfov / 2:
                if noise:
                    rng, bearing = rng * (1 + noise.gauss(0, 0.01)), bearing + noise.gauss(0, 0.5)
                dets.append({"id": t["id"], "range_m": rng, "bearing_deg": bearing})
        views.append({"pose": {"x_m": 0.0, "y_m": 0.0, "theta_deg": 30.0 * k}, "detections": dets})
    return views


def moved(tags, uid, dx, dy):
    return [dict(t, x_m=t["x_m"] + dx, y_m=t["y_m"] + dy) if t["uid"] == uid else dict(t) for t in tags]


PILOT_LIKE = {"sigma_a_m": 0.01, "sigma_b": 0.0148}      # the simulated camera's noise as the tag pilot would give it
ASSUMED = {"sigma_a_m": 0.03, "sigma_b": 0.04}


@pytest.mark.parametrize("uid, d, noise", [("T06", 0.5, ASSUMED), ("T05", 0.5, ASSUMED), ("T06", 0.3, PILOT_LIKE),
                                           ("T05", 0.3, PILOT_LIKE), ("T02", 0.3, PILOT_LIKE), ("T17", 0.3, PILOT_LIKE)],
                         ids=["T06-0.5-assumed", "T05-0.5-assumed", "T06-0.3-pilot", "T05-0.3-pilot", "T02-0.3-pilot",
                              "T17-0.3-pilot"])
def test_the_circle_names_the_tag_surveyed_wrongly(uid, d, noise):
    """A full circle at S1 sees about fifteen tags. One of them is d metres from where the world file says (along x):
    leaving each tag out in turn names it, by its own tag, not its id (T05 and T02 both carry id 3), and puts the
    others within a centimetre of their survey. With the assumed noise (0.03 + 0.04 r) one circle's limit for a tag
    1.3 to 1.8 m away is 0.32 to 0.40 m, so 0.5 m is named at once and 0.3 m only by adding circles up (TagCheck);
    with noise like the simulated camera's a 0.3 m error is named by one circle."""
    pose = {"x_m": 2.5, "y_m": 1.5, "theta_deg": 90.0}
    fix = R.resect(circle_views(pose, TAGS20), moved(TAGS20, uid, -d, 0.0), max_range_m=3.0, rms_max_m=0.08,
                   tag_check=CHECK, **noise)
    check = fix["check"]
    assert check["resolved"] and check["outliers"] == [uid], check
    rows = {r["tag"]: r for r in check["tags"]}
    assert rows[uid]["residual_m"] == pytest.approx(d, abs=0.02)
    assert max(r["residual_m"] for r in check["tags"] if r["tag"] != uid) < 0.01
    assert rows[uid]["dx_m"] == pytest.approx(d, abs=0.02)             # the others see it d further along +x


def test_a_tag_off_by_less_than_the_floor_is_not_named_and_a_clean_circle_names_none():
    pose = {"x_m": 2.5, "y_m": 1.5, "theta_deg": 90.0}
    for noise in (ASSUMED, PILOT_LIKE):                         # 0.1 m is under the 0.15 m floor of the limit
        small = R.resect(circle_views(pose, TAGS20), moved(TAGS20, "T06", -0.1, 0.0), max_range_m=3.0, rms_max_m=0.08,
                         tag_check=CHECK, **noise)
        assert small["ok"] and small["check"]["outliers"] == [] and small["check"]["resolved"]
        assert {r["tag"]: r for r in small["check"]["tags"]}["T06"]["residual_m"] == pytest.approx(0.1, abs=0.01)
    unseen = R.resect(circle_views(pose, TAGS20), moved(TAGS20, "T06", -0.3, 0.0), max_range_m=3.0, rms_max_m=0.08,
                      tag_check=CHECK, **ASSUMED)
    assert unseen["check"]["outliers"] == []                    # 0.3 m at 1.7 m, assumed noise: one circle cannot tell
    t06 = {r["tag"]: r for r in unseen["check"]["tags"]}["T06"]
    assert t06["residual_m"] > 0.25 and t06["limit_m"] > t06["residual_m"]
    rng = random.Random(3)
    for _ in range(20):                                             # the simulated camera's noise: never a tag named
        noisy = R.resect(circle_views(pose, TAGS20, noise=rng), TAGS20, max_range_m=3.0, sigma_a_m=0.03, sigma_b=0.04,
                         rms_max_m=0.08, tag_check=CHECK)
        assert noisy["ok"] and noisy["check"]["outliers"] == []
    three = [t for t in TAGS20 if t["uid"] in ("T03", "T04", "T05")]   # a room where only three tags are in reach
    few = R.resect(circle_views(pose, three), TAGS20, sigma_a_m=0.03, sigma_b=0.04, tag_check=CHECK)
    assert few["ok"] and few["n_tags"] == 3 and few["check"] is None    # nothing to compare a tag with


def test_tagcheck_adds_up_halts_on_a_disagreeing_tag_and_trusts_only_close_checks():
    tc = B.TagCheck(k=4.0, min_m=0.15, trust_max_m=0.30, trust_k=3.0)
    row = lambda tag, dx, sigma: {"tag": tag, "id": 1, "dx_m": dx, "dy_m": 0.0, "residual_m": abs(dx), "sigma_m": sigma,
                                  "limit_m": 0.0, "range_m": 1.0, "outlier": False}
    assert tc.trusted() == set() and tc.add(None) == []                  # nothing compared: nothing trusted
    assert tc.add({"resolved": False, "tags": [row("A", 0.9, 0.05)]}) == []         # no clean reference: not counted
    tc.add({"resolved": True, "tags": [row("A", 0.01, 0.05), row("B", 0.02, 0.12), row("C", 0.25, 0.05)]})
    v = {t: tc.verdict(t) for t in "ABC"}
    assert v["A"]["trusted"] and not v["A"]["flagged"]                  # close and quiet: 3 sigma 0.15 m
    assert not v["B"]["trusted"] and not v["B"]["flagged"]              # compared from too far: 3 sigma 0.36 m
    assert not v["C"]["trusted"] and v["C"]["flagged"]                  # 0.25 m off, limit 0.20 m: halt
    assert tc.flagged() == ["C"] and tc.trusted() == {"A"}
    for _ in range(2):                                                   # B compared twice more: now close enough
        tc.add({"resolved": True, "tags": [row("B", 0.0, 0.12)]})
    assert tc.verdict("B")["trusted"] and tc.verdict("B")["n"] == 3
    d = B.TagCheck(k=4.0, min_m=0.15, trust_max_m=0.30, trust_k=3.0)
    d.add({"resolved": True, "tags": [row("D", 0.17, 0.05)]})            # between the trust and the halt limits
    assert not d.verdict("D")["trusted"] and not d.verdict("D")["flagged"]
    assert "tag D (id 1) is 0.17 m from its surveyed centre" in B.tag_survey_detail(d, "D", [])


def test_an_untrusted_tag_steers_no_fix_and_its_copy_is_never_taken_for_it():
    """Ids 3, 0 and 2 are each on two tags. T05 (id 3, window wall) is seen alone; only T02 (id 3, the 295 cm wall)
    is trusted. The detection is still assigned to T05 (the copy near the tracked pose), which is untrusted: no fix,
    and not "far from the prior" (which would count as a conflict), as it would be if it were forced onto T02."""
    pose = {"x_m": 3.0, "y_m": 1.6, "theta_deg": 0.0}
    seen = [d for d in circle_views(pose, TAGS20, hfov=360.0)[0]["detections"] if d["id"] == 3 and d["range_m"] < 1.0]
    assert len(seen) == 1                                               # T05 at 0.82 m
    one = R.position_fix(seen, TAGS20, pose, 2.0, trusted={"T02"})
    assert one == {"ok": False, "why": "no checked tag in view", "n_tags": 0, "untrusted": ["T05"]}
    assert R.position_fix(seen, TAGS20, pose, 2.0, trusted={"T05"})["ok"]
    two = [d for d in circle_views(pose, TAGS20, hfov=360.0)[0]["detections"] if d["range_m"] < 1.6]
    fix = R.resect([{"pose": None, "detections": two}], TAGS20, prior=pose, trusted={"T06", "T14"})
    assert fix["ok"] and sorted(fix["tags"]) == ["T06", "T14"] and set(fix["untrusted"]) >= {"T05"}
    assert (fix["pose"]["x_m"], fix["pose"]["y_m"]) == pytest.approx((3.0, 1.6), abs=1e-6)
    assert R.resect([{"pose": None, "detections": two}], TAGS20, prior=pose, trusted=set())["why"] == \
        "fewer than 2 checked tags in view"


def tag_batch(tmp_path, wrong_world, seed=1, episodes=2, max_steps=60, starts=("S1", "S3"), place=PLACE20, **params):
    """A dry-run batch in the 20-tag room at 3.0 m whose world file (the runner's) may differ from the room (where
    the simulated camera sees the tags). Returns (runner, rig, result, stats)."""
    scen = {s["id"]: dict(s["start_pose"], id=s["id"])
            for s in json.loads((ROOT / "configs" / "arenas" / "real-room-scenarios.json").read_text())["scenarios"]}
    latch = Latch(tmp_path / "LATCH")
    p = B.BatchParams(world_path="x", start_poses=[scen[s] for s in starts], initial_pose=dict(place),
                      episodes=episodes, max_steps=max_steps, max_range_m=3.0, seed0=seed, **params)
    rig = B.dry_rig(WORLD20, place, latch=latch, seed=seed, max_range_m=3.0)
    runner = B.BatchRunner(p, rig, wrong_world, tmp_path / "batch", driver=cl.B2Driver(), budget=rp.Budget(float("inf")),
                           log=lambda *a: None, run_episode=cl.run_episode)
    stats = {"depth": 9.0, "err": 0.0}
    walls = rig.link.on_step

    def watch(link):
        walls(link)
        stats["depth"] = min(stats["depth"], runner.guard.footprint_depth(rig.sim_truth_fn()))
    rig.link.on_step = watch
    result = runner.run()
    stats["contact"] = bool(rig.link.sim.p.blocked_left or rig.link.sim.p.blocked_right)
    # the tracked pose against the simulator's truth at every sensing (truth.jsonl; not during a move, when the
    # tracker still holds the pose from before it) until the batch halted
    for path in (tmp_path / "batch" / "episodes").glob("**/truth.jsonl"):
        for line in open(path):
            row = json.loads(line)
            w, t = row["tracked_world"]["pose"], row["sim_truth_world"]
            if row["halted"] is None and t:
                stats["err"] = max(stats["err"], math.hypot(w["x_m"] - t["x_m"], w["y_m"] - t["y_m"]))
    return runner, rig, result, stats


def world_with(uid, dx, dy):
    w = json.loads(json.dumps(WORLD20))
    for t in w["tags"]:
        if t["uid"] == uid:
            t["x_m"] += dx
            t["y_m"] += dy
    return w


def test_a_clean_room_raises_no_tag_survey_halt_and_every_tag_ends_trusted(tmp_path):
    runner, rig, result, stats = tag_batch(tmp_path, WORLD20, episodes=2)
    assert result == {"status": "complete", "halt": None}
    m = json.loads((tmp_path / "batch" / "manifest.json").read_text())
    assert m["tag_check"]["flagged"] == [] and len(m["tag_check"]["trusted"]) >= 15
    assert max(v["offset_m"] / v["limit_m"] for v in m["tag_check"]["this_run"].values()) < 0.5
    assert stats["err"] < 0.08 and not stats["contact"]
    assert "tags checked against each other in this run" in (tmp_path / "batch" / "summary.txt").read_text()


def pilot_model(**over):
    """A bm.detector_noise/1 document as tools/tag_pilot.py analyze writes it (numbers like the simulated camera's)."""
    model = {"schema": "bm.detector_noise/1", "range_bias_m": {"a": 0.004, "b": -0.006}, "range_sigma_m": {"a": 0.01, "b": 0.012},
             "bearing_bias_deg": 0.2, "bearing_sigma_deg": {"a": 0.3, "b": 0.1}, "min_range_m": 0.75, "max_range_m": 3.2,
             "max_incidence_deg": 60.0, "p_detect": [{"range_m": 1.0, "incidence_deg": 0.0, "p": 1.0}], "obs_frames": 5,
             "obs_min_frames": 3, "tag_black_size_m": 0.16,
             "source": {"log": "20261125-100000-tag-pilot frames.csv", "date": "2026-11-25", "n_frames": 900, "n_placements": 30}}
    model.update(over)
    return model


def test_fix_sigma_from_the_tag_pilots_detector_noise():
    """Along the line of sight |bias| + sigma = 0.014 + 0.018 r; across it r x (0.2 + 0.3 + 0.1 x 3.0) degrees =
    0.01396 r; together at most 0.014 + hypot(0.018, 0.01396) r = 0.014 + 0.02278 r."""
    a, b, text = B.fix_sigma_from_detector_noise(pilot_model(), 3.0)
    assert a == pytest.approx(0.014) and b == pytest.approx(math.hypot(0.018, math.radians(0.8)))
    assert "tag pilot 20261125-100000-tag-pilot frames.csv (2026-11-25, 900 frames, 30 placements)" in text
    for r in (0.5, 1.0, 2.0, 3.0):          # the bound covers both error directions at every range up to the limit
        along = 0.004 + 0.006 * r + 0.01 + 0.012 * r
        across = r * math.radians(0.2 + 0.3 + 0.1 * 3.0)
        assert a + b * r >= max(along, across) and a + b * r >= math.hypot(along, across) - 1e-12
    for bad in (pilot_model(schema="bm.detector_noise/2"), pilot_model(range_sigma_m={"a": -0.01, "b": 0.01}),
                pilot_model(bearing_sigma_deg={"a": float("nan"), "b": 0.0}), {"schema": "bm.detector_noise/1"}):
        with pytest.raises(ValueError):
            B.fix_sigma_from_detector_noise(bad, 3.0)
    tiny = B.fix_sigma_from_detector_noise(pilot_model(range_bias_m={"a": 0.0, "b": 0.0}, range_sigma_m={"a": 0.0, "b": 0.01}), 3.0)
    assert tiny[0] == 0.005                 # never a zero sigma


def test_the_tool_takes_the_pilots_file_and_the_manifest_says_which_sigma_was_used(tmp_path, capsys):
    """--detector-noise: the fix sigma comes from the pilot's file, the manifest records the file, its hash and the
    numbers; without it the assumed 0.03 + 0.04 r, said so. configs/dv.json is not read for this and not changed."""
    tool = load_batch_tool()
    dv_before = (ROOT / "configs" / "dv.json").read_bytes()
    noise = tmp_path / "detector_noise.json"
    noise.write_text(json.dumps(pilot_model()))
    base = ["run", "--world", str(WORLD20_PATH), "--start", "S1:2.5,1.5,90", "--initial-pose", "2.4,1.6,70",
            "--max-steps", "3", "--max-range", "3.0", "--dry-run"]
    assert tool.main(base + ["--out", str(tmp_path / "a"), "--detector-noise", str(noise)]) == 0
    m = json.loads((tmp_path / "a" / "manifest.json").read_text())
    a, b, _ = B.fix_sigma_from_detector_noise(pilot_model(), 3.0)
    assert m["params"]["fix_sigma_a_m"] == pytest.approx(a) and m["params"]["fix_sigma_b"] == pytest.approx(b)
    source = m["params"]["fix_sigma_source"]
    digest = hashlib.sha256(noise.read_bytes()).hexdigest()[:12]
    assert "sha256:%s" % digest in source and "tag pilot" in source and "WARNING" not in source
    assert "fix sigma: " in (tmp_path / "a" / "summary.txt").read_text()
    assert tool.main(base + ["--out", str(tmp_path / "b")]) == 0
    m = json.loads((tmp_path / "b" / "manifest.json").read_text())
    assert (m["params"]["fix_sigma_a_m"], m["params"]["fix_sigma_b"]) == (0.03, 0.04)
    assert m["params"]["fix_sigma_source"].startswith("assumed: 0.03 m + 0.04 x range")
    assert m["config"] != json.loads((tmp_path / "a" / "manifest.json").read_text())["config"]   # another batch
    short = tmp_path / "short.json"
    short.write_text(json.dumps(pilot_model(max_range_m=2.6)))          # the pilot trusts detections to 2.6 m only
    assert tool.main(base + ["--out", str(tmp_path / "c"), "--detector-noise", str(short)]) == 0
    assert "WARNING: --max-range 3.00 m is beyond the 2.60 m" in capsys.readouterr().out
    assert "WARNING" in json.loads((tmp_path / "c" / "manifest.json").read_text())["params"]["fix_sigma_source"]
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps(pilot_model(range_sigma_m={"a": 0.01})))
    with pytest.raises(SystemExit, match="detector_noise|bm.detector_noise|lacks"):
        tool.main(base + ["--out", str(tmp_path / "d"), "--detector-noise", str(broken)])
    assert not (tmp_path / "d").exists()                                # refused before anything was written
    assert (ROOT / "configs" / "dv.json").read_bytes() == dv_before


def walk_at_one_tag(tmp_path, d, circle=True, **params):
    """The review's hole, made direct: the world file has T06 (window wall, id 12) d metres into the room. After an
    optional full circle at (2.6, 2.58) the camera sees T06 alone, and the car drives FORWARD_10 at the window wall for
    as long as the guard allows. Returns the halt, the smallest true footprint depth, and tracked against true x."""
    place = {"x_m": 2.6, "y_m": 2.58, "theta_deg": 0.0}
    p = B.BatchParams(world_path="x", start_poses=[dict(place, id="P")], initial_pose=dict(place), max_range_m=3.0,
                      **params)
    rig = B.dry_rig(WORLD20, place, latch=Latch(tmp_path / "LATCH"), seed=1, max_range_m=3.0)
    r = B.BatchRunner(p, rig, world_with("T06", -d, 0.0), tmp_path / "b", driver=cl.B2Driver(),
                      budget=rp.Budget(float("inf")), log=lambda *a: None, run_episode=cl.run_episode)
    r.preflight()
    env = r._service_env("t", str(tmp_path / "t"))
    env.reset(1)
    depth = {"min": 9.0}
    walls = rig.link.on_step

    def watch(link):
        walls(link)
        depth["min"] = min(depth["min"], r.guard.footprint_depth(rig.sim_truth_fn()))
    rig.link.on_step = watch
    if circle:
        try:
            r.localise(env, "a circle", required=False)
        except B.BatchStop:
            return {"halt": r.monitor.halted, "depth": depth["min"], "forward": 0}
    r.localised = env.use_views = True
    real = env.inner.detector
    env.inner.detector = lambda jpegs, n=None: dict(real(jpegs, n), detections=[
        x for x in real(jpegs, n)["detections"] if x.get("id") == 12])
    while abs(R.wrap_deg(r.tracker.pose["theta_deg"])) > 15:
        env.step("TURN_RIGHT_30" if r.tracker.pose["theta_deg"] > 0 else "TURN_LEFT_30")
    forward = 0
    for _ in range(25):
        if r.monitor.halted or env.step("FORWARD_10")["move"]["result"] != "done":
            break
        forward += 1
    truth = rig.sim_truth_fn()
    return {"halt": r.monitor.halted, "depth": depth["min"], "forward": forward,
            "lag_m": truth["x_m"] - r.tracker.pose["x_m"], "contact": rig.link.sim.p.blocked_left}


@pytest.mark.parametrize("d", [0.1, 0.3, 0.5])
def test_a_tag_surveyed_wrongly_by_d_cannot_pull_the_car_toward_its_wall(tmp_path, d):
    """Review finding 3 (open since 2026-11-18), with the faults the lead asked for: T06 surveyed 0.1, 0.3, 0.5 m into
    the room. Before 2026-11-24 (no tag check, every tag steers, reproduced here by its parameters) T06 seen alone
    pulls the tracked pose away from the wall, so the guard, keeping its 0.25 m from the pose it believes, lets the
    car closer than that: 0.3 m wrong left 0.18 m, 0.5 m left 0.08 m. Now: the circle names T06 and halts the batch
    (0.3 and 0.5 m) before any forward move; without a circle T06 is not checked, so it steers nothing and the guard
    works on the true pose; 0.1 m (under the 0.15 m floor) is neither named nor dangerous."""
    old = walk_at_one_tag(tmp_path / "old", d, circle=False, tag_check_k=float("inf"), tag_trust=False)
    assert old["halt"] is None and not old["contact"]
    assert old["lag_m"] == pytest.approx(0.67 * d, abs=0.06)            # the pull (most of the survey error)
    if d >= 0.3:
        assert old["depth"] < 0.20                                   # inside the 0.25 m the guard believes it keeps
    new = walk_at_one_tag(tmp_path / "new", d)
    if d >= 0.3:
        assert new["halt"]["code"] == "tag_survey" and "tag T06 (id 12) is" in new["halt"]["detail"]
        assert new["forward"] == 0 and new["depth"] > 0.9
    else:
        assert new["halt"] is None and new["depth"] > 0.25 and new["lag_m"] < 0.10
    unchecked = walk_at_one_tag(tmp_path / "unchecked", d, circle=False)
    assert unchecked["halt"] is None and abs(unchecked["lag_m"]) < 0.03 and unchecked["depth"] > 0.30


@pytest.mark.parametrize("d", [0.1, 0.3, 0.5])
def test_a_batch_with_one_tag_surveyed_wrongly_by_d(tmp_path, d):
    """The whole batch (B2, S1 then S3, 3.0 m, the assumed noise) with T06 surveyed d metres into the room. 0.3 and
    0.5 m: halted `tag_survey` naming T06 (and setting the project latch) with the simulated car well clear of every
    wall; 0.1 m: no tag named, the batch completes, the tracked pose stays within 0.12 m of the truth."""
    runner, rig, result, stats = tag_batch(tmp_path, world_with("T06", -d, 0.0))
    assert not stats["contact"]
    if d >= 0.3:
        assert result["status"] == "halted" and result["halt"]["code"] == "tag_survey", result
        assert "tag T06 (id 12)" in result["halt"]["detail"] and rig.latch.is_set()
        assert stats["depth"] > 0.25 and stats["err"] < 0.10
        assert "DISAGREEING: T06" in (tmp_path / "batch" / "summary.txt").read_text()
    else:
        assert result == {"status": "complete", "halt": None}
        assert stats["depth"] > 0.15 and stats["err"] < 0.12


def test_a_circle_of_tags_not_yet_trusted_does_not_count_toward_no_fix(tmp_path):
    """Found by the stand-in dry run of the first batch's command (2026-11-25): from (2.2, 2.0) every tag is 1.6 m or
    more away, so with the assumed noise the first circle compares them but trusts none; the second circle, at S1,
    then counted its own views (tags in them, none usable yet) toward no_fix and the batch halted inside the circle
    that was about to check them. A circle is the fix: its views with tags do not count. Outside circles they do."""
    runner, rig, result, stats = tag_batch(tmp_path, WORLD20, episodes=1, starts=("S1",), max_steps=40,
                                           place={"x_m": 2.2, "y_m": 2.0, "theta_deg": 90.0})
    assert result == {"status": "complete", "halt": None}
    m = json.loads((tmp_path / "batch" / "manifest.json").read_text())
    first = m["episodes"][0]["first_fix"]
    assert first["ok"] and m["episodes"][0]["start_fix"]["ok"] and len(m["tag_check"]["trusted"]) >= 10
    assert stats["err"] < 0.08 and not stats["contact"]
    b, r, env = service_env(tmp_path / "steps")            # outside a circle, views of untrusted tags still count
    r.tagcheck.stats.clear()
    for _ in range(r.params.no_fix_steps + 1):
        if r.monitor.halted:
            break
        env.step("TURN_LEFT_30")
    assert r.monitor.halted["code"] == "no_fix"


def test_the_recorder_check_compares_the_session_it_was_made_for(tmp_path):
    """The first real batch (2026-11-25) halted before any move with "the recorder session SIGHUP is no longer
    active": the check was a closure over a variable of cmd_run that the signal loop reused. It is a function of its
    own now (make_recorder_check): None while its session is the active one and writing; a reason otherwise. And the
    tool's real path builds it through that function, with nothing in between that could rebind it."""
    tool = load_batch_tool()
    data = tmp_path / "data"
    session = data / "real" / "20261125-034000-batch-b2-real-01"
    (session / "logs").mkdir(parents=True)
    (session / "logs" / "ping_car.txt").write_text("x")
    (data / "real" / ".active").write_text(session.name + "\n")
    check = tool.make_recorder_check(str(session), data_dir=str(data))
    assert check() is None
    (data / "real" / ".active").write_text("20261125-040000-other\n")
    (data / "real" / "20261125-040000-other").mkdir()
    assert check() == "the recorder session 20261125-034000-batch-b2-real-01 is no longer active"
    (data / "real" / ".active").unlink()
    assert "no longer active" in check()
    source = (ROOT / "tools" / "car_batch.py").read_text()
    assert "recorder_check = make_recorder_check(session)" in source


# The first real practice batch's six straight moves (data/batches/practice-01b on the Spark, 2026-11-25): the
# odometry of the move (forward, left) and each tag's position in the car frame before and after it, from the
# detector's own record (detections_internal, base_xyz_m). Its odometry_scale halt (-23 %) came from position fixes.
PRACTICE_01B_STRAIGHTS = [
    ((0.2443, 0.0135), [(1, 1.9585, 0.6948), (9, 2.0952, 0.2693), (23, 2.0885, -0.0464), (8, 2.076, -0.4143)],
     [(1, 1.7548, 0.5845), (9, 1.8658, 0.152), (23, 1.8427, -0.1629), (8, 1.8172, -0.5317)]),
    ((0.2447, 0.0122), [(1, 1.7548, 0.5845), (9, 1.8658, 0.152), (23, 1.8427, -0.1629), (8, 1.8172, -0.5317)],
     [(1, 1.5332, 0.4725), (9, 1.6192, 0.0338), (23, 1.5785, -0.279)]),
    ((0.0994, 0.0053), [(1, 1.5332, 0.4725), (9, 1.6192, 0.0338), (23, 1.5785, -0.279)],
     [(1, 1.4545, 0.3822), (9, 1.523, -0.0591), (23, 1.464, -0.37)]),
    ((0.0930, 0.0047), [(1, 1.4545, 0.3822), (9, 1.523, -0.0591), (23, 1.464, -0.37)],
     [(1, 1.3837, 0.3089), (9, 1.4296, -0.1353)]),
    ((0.2454, 0.0115), [(0, 1.3168, 0.2704), (1, 1.3315, -0.3538)], [(0, 1.0914, 0.2372)]),
    ((0.2453, 0.0094), [(0, 1.0914, 0.2372)], [(0, 0.8798, 0.1665)]),
]


def _sense_and_record(tags_xy):
    """An observation (centimetre ranges, as the agent sees them) and the detector's record (millimetres)."""
    dets = [{"id": i, "range_m": round(math.hypot(x, y), 2), "bearing_deg": round(math.degrees(math.atan2(y, x)), 1)}
            for i, x, y in tags_xy]
    return {"detections": dets}, {"detections_internal": [{"id": i, "base_xyz_m": [x, y, 0.23]} for i, x, y in tags_xy]}


PILOT_RANGE = {"range_bias_a_m": 0.00492, "range_bias_b": -0.01658, "range_min_m": 0.785}    # configs/detector_noise.json


def _range_replay(straights, odometry_factor=1.0, **params):
    """The straights through BatchEnv._range_check as _post runs it: the tracked pose at the origin before each move
    (surveyed tags where the car saw them), advanced by the odometry before the sensing after it."""
    env = B.BatchEnv.__new__(B.BatchEnv)
    env.params = B.BatchParams(world_path="x", start_poses=[S1], initial_pose=dict(S1), max_range_m=3.0, **params)
    env.tracker = B.PoseTracker({"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}, 0.05, 2.0)
    halts = []
    for k, ((fwd, left), before, after) in enumerate(straights):
        env.tags = [{"id": i, "uid": "M%d-%d" % (k, i), "x_m": x, "y_m": y} for i, x, y in before]
        env.tracker.pose = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
        env.range_before = None
        sense, record = _sense_and_record(before)
        env._range_check(None, sense, record, True)
        odo = {"forward_m": fwd * odometry_factor, "left_m": left * odometry_factor, "dtheta_deg": 3.0}
        env.tracker.predict(odo)
        sense, record = _sense_and_record(after)
        env._range_check(odo, sense, record, False)
        halts.append(B.range_scale_halt(env.tracker, env.params))
    return env.tracker, halts


def test_the_practice_batch_ranges_say_its_odometer_was_right():
    """Replayed through the batch's own range check, the six straight moves of the practice batch that halted
    `odometry_scale` (-23 %, from position fixes): with the tag pilot's range bias removed (as a real batch does with
    --detector-noise) tags over odometry 0.94 to 1.05 per move, median 0.98, which agrees with the same batch's
    transit check (1.008): 0.031 apart, 1.2 standard errors of the median (1.25 x 5 % / sqrt(6) = 0.026), before
    the transit's own uncertainty (two circle fixes over 0.69 m) is counted; without the bias removed 0.92 to 1.03,
    median 0.96. No halt at any move either way. The same moves with an odometer
    reading 25 % short halt at the first move (the car going farther than it thinks); with one reading 25 % long they
    read 0.78, under-travel, which passes as slip since the slip test (2026-11-25)."""
    tracker, halts = _range_replay(PRACTICE_01B_STRAIGHTS, **PILOT_RANGE)
    per_move = [m[0] for m in tracker.range_moves]
    assert per_move == pytest.approx([0.989, 1.049, 1.003, 0.965, 0.955, 0.935], abs=0.0015), per_move
    assert [m[1] for m in tracker.range_moves] == [4, 3, 3, 2, 1, 1]
    median = tracker.range_scale()[0]
    assert median == pytest.approx(0.977, abs=0.002)
    assert abs(median - 1.008) < 2.0 * 1.25 * 0.05 / math.sqrt(6)           # within two standard errors
    assert halts == [None] * 6
    tracker, halts = _range_replay(PRACTICE_01B_STRAIGHTS)                     # raw ranges, as cfa3948 read them
    assert [round(m[0], 2) for m in tracker.range_moves] == [0.97, 1.03, 0.99, 0.95, 0.94, 0.92]
    assert tracker.range_scale()[0] == pytest.approx(0.961, abs=0.002) and halts == [None] * 6
    tracker, halts = _range_replay(PRACTICE_01B_STRAIGHTS, odometry_factor=0.75, **PILOT_RANGE)
    assert halts[0] is not None and "configs/car.json is wrong" in halts[0], halts
    assert tracker.range_scale()[0] == pytest.approx(1.30, abs=0.02)
    tracker, halts = _range_replay(PRACTICE_01B_STRAIGHTS, odometry_factor=1.25, **PILOT_RANGE)
    assert halts == [None] * 6 and tracker.range_scale()[0] == pytest.approx(0.78, abs=0.02)


def test_the_range_check_resolves_repeated_ids_by_the_tracked_pose_and_keeps_to_the_window():
    """Two surveyed tags carry id 3, 2.8 m apart (as T02 and T05 of the real room): seen both before and after a
    straight move, each is resolved to its own surveyed tag and paired with itself. Where the tracked pose cannot tell
    two tags of one id apart (under 1 m between their distances), neither is used. Tags nearer than range_min_m or
    farther than max_range_m are not used, and turns (under 5 cm) are not straight moves."""
    env = B.BatchEnv.__new__(B.BatchEnv)
    env.params = B.BatchParams(world_path="x", start_poses=[S1], initial_pose=dict(S1), max_range_m=3.0, range_min_m=0.785)
    env.tracker = B.PoseTracker({"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}, 0.05, 2.0)
    env.tags = [{"id": 3, "uid": "T02", "x_m": 2.0, "y_m": 0.5}, {"id": 3, "uid": "T05", "x_m": 2.2, "y_m": -0.6},
                {"id": 7, "uid": "T07", "x_m": 0.6, "y_m": 0.0}, {"id": 9, "uid": "T09", "x_m": 3.2, "y_m": 0.0}]
    seen = [(3, 2.0, 0.5), (3, 2.2, -0.6), (7, 0.6, 0.0), (9, 3.2, 0.0)]

    def view(odo_x):
        return [(i, x - odo_x, y) for i, x, y in seen]
    env.range_before = None
    env._range_check(None, *_sense_and_record(view(0.0)), True)
    assert sorted(d["key"] for d in env.range_before) == ["T02", "T05"]   # T07 too near, T09 too far
    odo = {"forward_m": 0.25, "left_m": 0.0, "dtheta_deg": 0.0}
    env.tracker.predict(odo)
    env._range_check(odo, *_sense_and_record(view(0.25)), False)
    assert len(env.tracker.range_moves) == 1
    scale, pairs = env.tracker.range_moves[0]
    assert pairs == 2 and scale == pytest.approx(1.0, abs=0.01)
    turn = {"forward_m": 0.013, "left_m": 0.003, "dtheta_deg": 30.0}
    env._range_check(turn, *_sense_and_record(view(0.25)), False)
    assert len(env.tracker.range_moves) == 1                               # a turn adds nothing
    env.tags[1] = {"id": 3, "uid": "T05", "x_m": 2.0, "y_m": 0.0}          # now 0.5 m from T02: not told apart
    env.tracker.pose = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
    env.range_before = None
    env._range_check(None, *_sense_and_record([(3, 2.0, 0.5)]), True)
    assert env.range_before == []


def test_the_range_check_takes_the_pilots_range_bias_and_window(tmp_path):
    """--detector-noise gives the range check the pilot's range bias (removed before comparing) and the near end of
    its reliable window; without it no bias and 0.3 m."""
    tool = load_batch_tool()
    noise = tmp_path / "detector_noise.json"
    noise.write_text(json.dumps(pilot_model()))
    base = ["run", "--world", str(WORLD20_PATH), "--start", "S1:2.5,1.5,90", "--initial-pose", "2.4,1.6,70",
            "--max-steps", "3", "--max-range", "3.0", "--dry-run"]
    assert tool.main(base + ["--out", str(tmp_path / "a"), "--detector-noise", str(noise)]) == 0
    p = json.loads((tmp_path / "a" / "manifest.json").read_text())["params"]
    assert (p["range_bias_a_m"], p["range_bias_b"], p["range_min_m"]) == (0.004, -0.006, 0.75)
    assert tool.main(base + ["--out", str(tmp_path / "b")]) == 0
    p = json.loads((tmp_path / "b" / "manifest.json").read_text())["params"]
    assert (p["range_bias_a_m"], p["range_bias_b"], p["range_min_m"]) == (0.0, 0.0, 0.3)


def test_the_range_of_a_tag_along_a_straight_move_measures_the_scale():
    """Geometry of range_scale_of_move: an exact case, a backward move (the other root), a tag abeam (no
    information, left out), an id seen twice (ambiguous, left out) and a tag far from where it should be (another tag
    of the same id, left out)."""
    def det(i, x, y):
        return {"id": i, "range_m": math.hypot(x, y), "bearing_deg": math.degrees(math.atan2(y, x))}
    tag = (2.0, 0.4)
    for s_true, odo in ((1.0, (0.25, 0.01)), (4.0 / 3.0, (0.25, 0.01)), (0.8, (0.25, -0.02)), (1.0, (-0.10, 0.0)),
                        (1.25, (-0.10, 0.0))):
        moved = (tag[0] - s_true * odo[0], tag[1] - s_true * odo[1])
        est = B.range_scale_of_move([det(5, *tag)], [det(5, *moved)], {"forward_m": odo[0], "left_m": odo[1]})
        assert est is not None and est[0] == pytest.approx(s_true, abs=1e-9) and est[1] == 1, (s_true, odo, est)
    abeam = B.range_scale_of_move([det(5, 0.0, 1.5)], [det(5, -0.25, 1.5)], {"forward_m": 0.25, "left_m": 0.0})
    assert abeam is None
    twice = B.range_scale_of_move([det(5, 2.0, 0.4), det(5, 2.0, -1.0)], [det(5, 1.75, 0.4), det(5, 1.75, -1.0)],
                                  {"forward_m": 0.25, "left_m": 0.0})
    assert twice is None
    other = B.range_scale_of_move([det(5, 2.0, 0.4)], [det(5, 2.6, 0.4)], {"forward_m": 0.25, "left_m": 0.0})
    assert other is None
    wide = B.range_scale_of_move([det(5, 1.5, 1.0)], [det(5, 1.25, 1.0)], {"forward_m": 0.25, "left_m": 0.0})
    assert wide is None                                     # 33.7 degrees off the line of motion: beyond 30
    keyed = B.range_scale_of_move([dict(det(5, 2.0, 0.4), key="T02"), dict(det(5, 2.0, -1.0), key="T05")],
                                  [dict(det(5, 1.75, 0.4), key="T02"), dict(det(5, 1.75, -1.0), key="T05")],
                                  {"forward_m": 0.25, "left_m": 0.0})
    assert keyed is not None and keyed[1] == 2              # one id, two surveyed tags told apart: both count
    assert keyed[0] == pytest.approx(1.0, abs=1e-9)


def test_the_ranges_catch_a_wrong_encoder_scale_either_way_in_both_rooms(tmp_path):
    """The range check against fault injection, in the 8-tag room at 2.5 m and the 20-tag room at 3.0 m. An odometer
    reading 25 % short (the car goes farther than it thinks: the dangerous direction) halts `odometry_scale` on the
    ranges in every run, the simulated car far from any wall. Changed 2026-11-25 (the slip test): an odometer reading
    25 % long (the car covers 0.80 of what it counts, the safe direction) now passes as carpet slip, as the real car's
    0.78 northward does; the range log records the 0.80 and the car stays well inside the driving area. A correct
    odometer completes."""
    from beaconmind.car import config as C
    cfg = C.load_config()
    rooms = [(WORLD, PLACE, S1, TAPED, 2.5),
             (WORLD20, {"x_m": 2.4, "y_m": 1.6, "theta_deg": 70.0}, {"id": "S1", "x_m": 2.5, "y_m": 1.5, "theta_deg": 90.0},
              {"x_m": 2.4, "y_m": 1.6, "theta_deg": 70.0}, 3.0)]
    for factor in (0.75, 1.25, 1.0):
        wrong = cfg.replace(ticks_per_m_left=cfg.ticks_per_m_left / factor, ticks_per_m_right=cfg.ticks_per_m_right / factor)
        for r, (world, place, start, initial, max_range) in enumerate(rooms):
            for seed in (1, 2, 3):
                out = tmp_path / ("f%s-r%d-s%d" % (factor, r, seed))
                params = B.BatchParams(world_path="x", start_poses=[start], initial_pose=dict(initial), episodes=1,
                                       max_steps=80, max_range_m=max_range)
                rig = B.dry_rig(world, place, latch=Latch(out / "LATCH"), seed=seed, max_range_m=max_range, cfg=wrong)
                runner = B.BatchRunner(params, rig, world, out / "batch", driver=cl.B2Driver(),
                                       budget=rp.Budget(float("inf")), log=lambda *a: None, run_episode=cl.run_episode)
                depth = {"min": 9.0}
                walls = rig.link.on_step

                def watch(link, walls=walls, depth=depth, runner=runner, rig=rig):
                    walls(link)
                    depth["min"] = min(depth["min"], runner.guard.footprint_depth(rig.sim_truth_fn()))
                rig.link.on_step = watch
                result = runner.run()
                if factor == 1.0:
                    assert result["status"] == "complete", (r, seed, result)
                    continue
                assert depth["min"] > 0.3 and not rig.link.sim.p.blocked_left, (factor, r, seed, depth)
                if factor == 1.25:                      # under-travel: slip, recorded, no scale halt
                    assert result["halt"] is None or "ranges to the tags" not in result["halt"]["detail"], result
                    assert runner.tracker.range_scale()[0] == pytest.approx(0.80, abs=0.03)
                    continue
                assert result["status"] == "halted" and result["halt"]["code"] == "odometry_scale", (factor, r, seed, result)
                assert "ranges to the tags" in result["halt"]["detail"], result


def test_the_range_check_skips_backward_moves_and_watches_the_recent_moves_too():
    """The review of the range check (2026-11-25): a BACKWARD_10 slips when the wheels reverse (floor check F2) and
    would read 0.75 to 0.87, so backward moves are not measured; and a change in the middle of a batch must not be
    hidden by the moves before it, so the rule also runs over the last range_scale_window moves alone."""
    env = B.BatchEnv.__new__(B.BatchEnv)
    env.params = B.BatchParams(world_path="x", start_poses=[S1], initial_pose=dict(S1), max_range_m=3.0)
    env.tracker = B.PoseTracker({"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}, 0.05, 2.0)
    env.tags = [{"id": 4, "uid": "T04", "x_m": 2.0, "y_m": 0.2}]
    env.range_before = None
    env._range_check(None, *_sense_and_record([(4, 2.0, 0.2)]), True)
    back = {"forward_m": -0.10, "left_m": 0.0, "dtheta_deg": -3.0}
    env.tracker.predict(back)
    env._range_check(back, *_sense_and_record([(4, 2.08, 0.2)]), False)     # slipped: 8 cm back, odometry 10
    assert env.tracker.range_moves == []
    tracker = B.PoseTracker(S1, 0.05, 2.0)
    params = env.params
    tracker.range_moves = [(1.0, 3)] * 40                                     # a long good start
    assert B.range_scale_halt(tracker, params) is None
    tracker.range_moves += [(1.3, 2)] * 6                                     # then a wheel starts to slip
    assert tracker.range_scale()[0] == pytest.approx(1.0)                     # the whole batch hides it
    why = B.range_scale_halt(tracker, params)
    assert why is not None and "over the 10 most recent straight moves" in why and "1.30" in why
    tracker.range_moves = [(1.0, 3)] * 5 + [(1.3, 2)] * 2                     # under 10 moves: the whole-batch rule
    assert B.range_scale_halt(tracker, params) is None


class _Halts:
    def __init__(self):
        self.calls = []

    def halt(self, code, detail, safety=None):
        self.calls.append((code, detail))


def _drift(origin, dead_reckoned, circle, path_m, sigmas=(0.026, 0.024), what="episode (start circle to end circle)"):
    runner = B.BatchRunner.__new__(B.BatchRunner)
    runner.params = B.BatchParams(world_path="x", start_poses=[S1], initial_pose=dict(S1))
    runner.tracker = B.PoseTracker(circle, 0.024, 1.0)
    runner.tracker.dead_reckoned = dict(dead_reckoned)
    runner.tracker.dead_reckoned_path_m = path_m
    runner.monitor = _Halts()
    return runner._dead_reckoning(origin, sigmas, what), runner.monitor.calls


def test_the_dead_reckoning_drift_is_recorded_and_never_halts():
    """b2-real-01 (2026-11-25), episode 1: start circle (2.540, 1.466, 105.9), odometry alone ends at (3.099, 1.019,
    -1.5), the end circle at (3.098, 0.747, 11.9), after about 3.5 m of path (2.64 m of straights, 70 turns' axle
    shifts). Recorded (0.27 m miss, 13.4 deg; the net length ratio 1.27 kept). Since the lead's decision of 2026-11-25
    the drift is record-only in both directions: with slip that depends on direction the net displacement between two
    circles is no scale measure (the reviewer's out-and-back case at north 0.60: net 0.79 m by odometry against 1.29 m
    by the circles, ratio 1.63). would_have_halted records where the old bounds were crossed (the net ratio outside 0.5
    to 1.6; the miss beyond the circles' 2 sigma over 0.6 of the path): a factor-two error on a straight path is flagged
    and does not halt; what halts it is test_a_factor_two_scale_error_each_way_halts_in_the_real_room's."""
    start = {"x_m": 2.5402, "y_m": 1.4662, "theta_deg": 105.88}
    circle = {"x_m": 3.0976, "y_m": 0.7473, "theta_deg": 11.89}
    m, halts = _drift(start, {"x_m": 3.0986, "y_m": 1.0189, "theta_deg": -1.51}, circle, 3.5)
    assert halts == [] and m["measurement"] == "dead-reckoning drift" and m["checked"] and m["would_have_halted"] is False
    assert m["tags_over_odometry"] == pytest.approx(1.272, abs=0.002) and m["miss_m"] == pytest.approx(0.272, abs=0.002)
    assert m["heading_miss_deg"] == pytest.approx(13.4, abs=0.1) and m["circle_sigmas_xy_m"] == [0.026, 0.024]
    assert m["miss_world_m"] == pytest.approx([-0.001, -0.272], abs=0.002) and m["gross_share"] == 0.6
    assert m["miss_over_path"] == pytest.approx((0.272 - 2 * math.hypot(0.026, 0.024)) / 3.5, abs=0.002)
    # the reviewer's out-and-back case: odometry's net 0.79 m, the circles' 1.29 m, after 3.2 m of path
    origin = {"x_m": 2.0, "y_m": 2.0, "theta_deg": 0.0}
    m, halts = _drift(origin, {"x_m": 2.79, "y_m": 2.0, "theta_deg": 0.0}, {"x_m": 3.29, "y_m": 2.0, "theta_deg": 0.0}, 3.2)
    assert m["tags_over_odometry"] == pytest.approx(1.633, abs=0.01) and halts == [], m
    assert len(m["would_have_halted"]) == 1 and "net ratio 1.63" in m["would_have_halted"][0]
    # a factor-two error on a straight path: odometry says 0.455 m, the circle 0.91 m: both old bounds crossed, no halt
    half = {"x_m": start["x_m"] + 0.5 * (circle["x_m"] - start["x_m"]), "y_m": start["y_m"] + 0.5 * (circle["y_m"] - start["y_m"]),
            "theta_deg": 11.89}
    m, halts = _drift(start, half, circle, 0.455)
    assert m["miss_over_path"] > 0.6 and halts == [] and len(m["would_have_halted"]) == 2, m
    # odometry reading 2.2 times (the car covering under half its count): 1.0 m by odometry, 0.455 m on the floor
    double = {"x_m": start["x_m"] + 2.2 * (half["x_m"] - start["x_m"]), "y_m": start["y_m"] + 2.2 * (half["y_m"] - start["y_m"]),
              "theta_deg": 11.89}
    m, halts = _drift(start, double, half, 1.0)
    assert m["tags_over_odometry"] < 0.5 and m["miss_over_path"] < 0.6 and halts == []
    assert len(m["would_have_halted"]) == 1 and "net ratio 0.45" in m["would_have_halted"][0], m
    m, halts = _drift(start, start, start, 0.1)                 # too short a path to measure
    assert halts == [] and m["checked"] is False and "of path" in m["why"] and m["would_have_halted"] is False


def test_a_completed_episode_keeps_its_end_pose_when_a_later_check_halts(tmp_path, monkeypatch):
    """b2-real-01 (2026-11-25): the end-of-episode check halted the batch after episode 1 had ended by DONE, and the
    manifest was left without end_pose_map and final_pose_error, with the episode marked halted. Now the end pose and
    the agent's final error are written before any end-of-episode check, and the episode stays done (its log is
    complete); the halt is the batch's."""
    real = B.BatchRunner._dead_reckoning

    def gross_at_the_end(self, origin, sigmas, what):
        out = real(self, origin, sigmas, what)
        if what.startswith("episode"):
            self.monitor.halt("odometry_scale", "dead reckoning over the %s is grossly off (test)" % what)
        return out
    monkeypatch.setattr(B.BatchRunner, "_dead_reckoning", gross_at_the_end)
    b = Batch(tmp_path, episodes=2, max_steps=30, starts=(S1, S5))
    b.run()
    assert b.result["status"] == "halted" and b.result["halt"]["code"] == "odometry_scale", b.result
    e = b.manifest["episodes"][0]
    assert e["status"] == "done" and e["result"]["complete"] and e["halt"]["code"] == "odometry_scale"
    assert e["end_pose_map"] is not None and e["end_pose_world"] is not None and e.get("final_pose_error") is not None
    assert e["dead_reckoning_episode"]["measurement"] == "dead-reckoning drift"
    assert len(b.manifest["episodes"]) == 1                                  # the batch stopped there


# b2-real-02 (2026-11-25): the range check's 25 forward moves (tags over odometry, range pairs), in order
B2_REAL_02_RANGES = [(0.991, 2), (1.043, 2), (0.978, 2), (1.020, 1), (0.790, 1), (0.934, 1), (0.964, 1), (0.942, 2),
                     (0.989, 2), (1.007, 1), (0.914, 1), (0.978, 1), (0.937, 1), (0.966, 2), (0.871, 2), (0.912, 2),
                     (0.945, 1), (0.972, 1), (0.938, 3), (0.900, 3), (0.863, 4), (0.820, 1), (0.845, 1), (0.909, 1),
                     (0.827, 1)]


def _per_step(scale, se, travel=10.5, fixes=37, ranges=()):
    t = B.PoseTracker(S1, 0.05, 2.0)
    t.bias_travel, t.bias_fixes = travel, fixes
    t.bias_sxx = 1.0 / se ** 2
    t.bias_sxy = scale * t.bias_sxx
    t.range_moves = list(ranges)
    return t


def test_the_per_step_statistic_halts_only_while_the_range_check_cannot_vouch_for_the_scale():
    """b2-real-02 halted on the per-step fixes, -27 % +- 8 % over 10.5 m and 37 fixes, from real slip on northward
    moves, while the range check over 25 forward moves read 0.94 (0.90 over the last 10). Now: under-travel (fixes
    behind the odometry) is the safe direction and never halts on its own (b2-real-04), recorded beyond -45 %; and
    an over-travel reading the range check contradicts is held back by the gate and recorded. With fewer than 3
    measured forward moves the statistic halts beyond its limits, as with the range check out of tolerance."""
    params = B.BatchParams(world_path="x", start_poses=[S1], initial_pose=dict(S1))
    t = _per_step(-0.273, 0.081, ranges=B2_REAL_02_RANGES)
    assert t.odometry_bias()[0] == pytest.approx(-0.273) and B.range_scale_halt(t, params) is None
    assert B.per_step_scale_halt(t, params) is None and t.bias_gated is None
    t = _per_step(0.273, 0.081, ranges=B2_REAL_02_RANGES)                     # ahead, but the ranges say 0.94
    assert B.per_step_scale_halt(t, params) is None
    g = t.bias_gated
    assert g["per_step_scale"] == pytest.approx(0.273) and g["range_moves"] == 25 and g["range_moves_recent"] == 10
    assert g["range_median"] == pytest.approx(0.938, abs=0.002) and g["range_median_recent"] == pytest.approx(0.905, abs=0.003)
    for few in ([], [(1.0, 2)], [(1.0, 2), (0.99, 1)]):                      # fewer than 3 measured moves
        why = B.per_step_scale_halt(_per_step(0.273, 0.081, ranges=few), params)   # ahead: the car goes farther
        assert why is not None and "tag fixes land +27 %" in why and "%d measured forward moves, fewer than 3" % len(few) in why
        # behind (under-travel, the safe direction) never halts on its own since b2-real-04 (2026-11-25); beyond
        # -45 % it is recorded
        shallow = _per_step(-0.273, 0.081, ranges=few)
        assert B.per_step_scale_halt(shallow, params) is None and shallow.bias_under is None
        deep = _per_step(-0.50, 0.081, ranges=few)
        assert B.per_step_scale_halt(deep, params) is None and deep.bias_under["per_step_scale"] == pytest.approx(-0.50)
    out = _per_step(0.273, 0.081, ranges=[(1.20, 2)] * 3)                     # the range check itself out of tolerance
    assert B.range_scale_halt(out, params) is not None and B.per_step_scale_halt(out, params) is not None
    assert B.per_step_scale_halt(_per_step(-0.10, 0.22, ranges=[]), params) is None      # not significant: as before


def test_with_the_range_check_off_the_per_step_fixes_still_halt_a_wrong_scale(tmp_path, monkeypatch):
    """The review (2026-11-25): with the range check off, the per-step fix statistic is the layer that halts a wrong
    encoder scale. The gate keeps that: with no measured forward move, an odometer reading 25 % short (the car going
    farther than it thinks) halts on the fixes in the 20-tag room, by the second episode, the simulated car's
    footprint 0.10 m or more inside the driving area (0.13 m measured). One reading 25 % long (under-travel, -20 %)
    passes as slip since the slip test; the car stays 0.30 m or more inside (0.45 m measured). (The 8-tag room at
    2.5 m is the thin case of this layer alone: there 25 % short halts only in episode 3, at 0.04 m; with the range
    check on it halts at the first ranged move. Review note, 2026-11-25.)"""
    from beaconmind.car import config as C
    monkeypatch.setattr(B.BatchEnv, "_range_check", lambda self, exact, sense, record, first: None)
    cfg = C.load_config()
    place = {"x_m": 2.4, "y_m": 1.6, "theta_deg": 70.0}
    starts = [{"id": "S1", "x_m": 2.5, "y_m": 1.5, "theta_deg": 90.0}, {"id": "S5", "x_m": 2.25, "y_m": 2.6, "theta_deg": 180.0}]
    for factor in (0.75, 1.25):
        wrong = cfg.replace(ticks_per_m_left=cfg.ticks_per_m_left / factor, ticks_per_m_right=cfg.ticks_per_m_right / factor)
        out = tmp_path / ("f%s" % factor)
        params = B.BatchParams(world_path="x", start_poses=starts, initial_pose=dict(place), episodes=4, max_steps=80,
                               max_range_m=3.0)
        rig = B.dry_rig(WORLD20, place, latch=Latch(out / "LATCH"), seed=1, max_range_m=3.0, cfg=wrong)
        runner = B.BatchRunner(params, rig, WORLD20, out / "batch", driver=cl.B2Driver(), budget=rp.Budget(float("inf")),
                               log=lambda *a: None, run_episode=cl.run_episode)
        depth = {"min": 9.0}
        walls = rig.link.on_step

        def watch(link, walls=walls, depth=depth, runner=runner, rig=rig):
            walls(link)
            depth["min"] = min(depth["min"], runner.guard.footprint_depth(rig.sim_truth_fn()))
        rig.link.on_step = watch
        result = runner.run()
        assert not rig.link.sim.p.blocked_left, factor
        if factor == 1.25:
            assert result["halt"] is None or "tag fixes land" not in result["halt"]["detail"], result
            assert depth["min"] > 0.30, depth
            continue
        assert result["status"] == "halted" and result["halt"]["code"] == "odometry_scale", (factor, result)
        assert "tag fixes land" in result["halt"]["detail"] and "0 measured forward moves" in result["halt"]["detail"]
        episodes = json.loads((out / "batch" / "manifest.json").read_text())["episodes"]
        assert len(episodes) <= 2 and depth["min"] > 0.10, (len(episodes), depth)


# The slip test (2026-11-25, recorder session 20261125-064330-slip-test): 4 x FORWARD_25 each way on the pilot's
# centre line, the lens read on the tape: northward the car covered 0.78 of its counted distance, southward 1.04
SLIP_TEST = {"north": 0.7805, "south": 1.0397}


def test_the_measured_carpet_slip_does_not_halt_and_is_recorded_by_heading(tmp_path):
    """The slip test's ratios as range-check moves (four each way) and b2-real-02's 25 real moves: no halt. A car
    going farther than it counts by as little as the southward 1.04 plus 12 % would halt. And a dry batch records each
    measured move with its world heading, and the slip by heading over the batch, in the manifest."""
    params = B.BatchParams(world_path="x", start_poses=[S1], initial_pose=dict(S1))
    for name, ratio in SLIP_TEST.items():
        t = B.PoseTracker(S1, 0.05, 2.0)
        for k in range(4):
            t.range_moves.append((ratio, 1))
            assert B.range_scale_halt(t, params) is None, (name, k)
    north_then_south = B.PoseTracker(S1, 0.05, 2.0)
    north_then_south.range_moves = [(SLIP_TEST["north"], 1)] * 12 + [(SLIP_TEST["south"], 1)] * 4
    assert B.range_scale_halt(north_then_south, params) is None
    t = B.PoseTracker(S1, 0.05, 2.0)
    t.range_moves = list(B2_REAL_02_RANGES)
    assert B.range_scale_halt(t, params) is None
    t.range_moves = [(1.17, 1)] * 3                                           # 17 % farther: halts
    assert "farther than it thinks" in B.range_scale_halt(t, params)
    t.range_moves = [(0.60, 1)] * 3                                           # 0.60: under-travel, allowed since
    assert B.range_scale_halt(t, params) is None                              # the floor went to 0.55
    t.range_moves = [(0.50, 1)] * 3                                           # a factor-two error: below the floor
    assert "floor 0.55" in B.range_scale_halt(t, params)
    b = Batch(tmp_path, episodes=2, max_steps=30, starts=(S1, S5))
    assert b.run()["status"] == "complete"
    moves = [m for e in b.manifest["episodes"] for m in e["range_moves"]]
    assert moves and all(set(m) >= {"time_utc", "heading_deg", "x_m", "y_m", "forward_m", "scale", "pairs"} for m in moves)
    table = b.manifest["episodes"][-1]["slip_by_heading"]
    assert sum(row["moves"] for row in table) == len(moves) and all(0.9 < row["median"] < 1.1 for row in table)


def test_a_long_northward_transit_on_the_slipping_carpet_reaches_its_start(tmp_path, monkeypatch):
    """The transit to S3 runs about 2.4 m north, where the car covers 0.78 of its counted distance (the slip test).
    With 5 attempts it ran out 0.30 m short in 2 of 4 simulated batches (2026-11-25); go_to now gives one attempt per
    0.41 m of floor (0.75 m blind at the 0.55 floor) besides start_attempts. Here, on a simulated carpet with the
    measured slip, from (2.6, 1.0) facing north to S3 (2.9 m): reached, using all of the old 5 attempts, with 11 now
    allowed. (In ten-episode batches on the same carpet the S3 transit needed 6 in 2 of 6 seeds.)"""
    from beaconmind.car import simcar as S
    world = json.loads((ROOT / "configs" / "arenas" / "real-room.json").read_text())
    place = {"x_m": 2.6, "y_m": 1.0, "theta_deg": 90.0}
    theta0 = math.radians(place["theta_deg"])
    real_step = S.SimCar.step

    def slipping(self, dt):
        x0, y0 = self.x, self.y
        real_step(self, dt)
        dx, dy = self.x - x0, self.y - y0
        if dx or dy:
            k = 0.91 - 0.13 * math.sin(theta0 + math.atan2(dy, dx))         # 0.78 north, 1.04 south
            self.x, self.y = x0 + k * dx, y0 + k * dy
    monkeypatch.setattr(S.SimCar, "step", slipping)
    s3 = {"id": "S3", "x_m": 2.60, "y_m": 3.90, "theta_deg": -90.0}
    params = B.BatchParams(world_path="x", start_poses=[s3], initial_pose=dict(place), episodes=1, max_steps=5,
                           max_range_m=3.0, range_bias_a_m=0.00492, range_bias_b=-0.01658, range_min_m=0.785)
    rig = B.dry_rig(world, place, latch=Latch(tmp_path / "LATCH"), seed=2, max_range_m=3.0)
    runner = B.BatchRunner(params, rig, world, tmp_path / "batch", driver=cl.B2Driver(), budget=rp.Budget(float("inf")),
                           log=lambda *a: None, run_episode=cl.run_episode)
    result = runner.run()
    e = json.loads((tmp_path / "batch" / "manifest.json").read_text())["episodes"][0]
    assert result["status"] == "complete", result
    assert e["start_fix"]["miss_m"] <= 0.20 and not rig.link.sim.p.blocked_left
    pose = {"x_m": place["x_m"], "y_m": place["y_m"]}
    allowed = params.start_attempts + math.ceil(math.hypot(s3["x_m"] - pose["x_m"], s3["y_m"] - pose["y_m"])
                                                / (params.max_blind_travel_m * params.range_scale_floor))
    assert allowed == 11 and 5 <= e["start_fix"]["attempts"] <= allowed, (allowed, e["start_fix"]["attempts"])


def test_a_forward_move_starts_where_a_turn_fits_with_the_end_margin_to_spare():
    """A review note (2026-11-25): on the carpet the car covers 0.78 of its counted distance northward, so after a
    blind stretch it really stands between the stretch's start and the tracked end. Turn room is concave along a
    straight line, so it is at least the smaller of the two; the end already needs the turn margin plus 0.05 m, and
    now the start does too. A turn itself is still allowed with the plain turn margin."""
    from beaconmind.car.config import load_car
    c = load_car()
    plain = B.MoveGuard(WORLD, [tuple(p) for p in c["corners"]], float(c["sweep_radius_m"]), 0.15, 0.25)
    spare = B.MoveGuard(WORLD, [tuple(p) for p in c["corners"]], float(c["sweep_radius_m"]), 0.15, 0.25,
                        start_turn_margin_m=0.05)
    sigma = 0.05
    need = B.MoveGuard.turn_margin_m + sigma
    # a pose facing into the room whose turn room is between the turn's need and that need plus 0.05 m
    found = None
    for i in range(400):
        y = 0.20 + i * 0.005
        pose = {"x_m": 1.5, "y_m": y, "theta_deg": 90.0}
        room = plain.axle_depth(pose) - plain.sweep_radius_m
        if need + 0.01 <= room <= need + 0.04:
            found = (pose, room)
            break
    assert found, "no pose with a tight turn room in WORLD"
    pose, room = found
    assert plain.check("TURN_LEFT_30", pose, sigma) is None and spare.check("TURN_LEFT_30", pose, sigma) is None
    assert plain.check("FORWARD_10", pose, sigma) is None, plain.check("FORWARD_10", pose, sigma)
    why = spare.check("FORWARD_10", pose, sigma)
    assert why is not None and "would start where a turn has only" in why, why
    roomy = {"x_m": 1.5, "y_m": pose["y_m"] + 0.10, "theta_deg": 90.0}
    assert spare.check("FORWARD_10", roomy, sigma) is None
    assert B.BatchParams(world_path="x", start_poses=[S1], initial_pose=dict(S1)).start_turn_margin_m == 0.05


def test_a_halt_inside_the_end_circle_leaves_the_episode_done_with_its_end_pose(tmp_path, monkeypatch):
    """b2-real-03 (2026-11-25): a stall in the end circle of episode 2 left the episode `halted`, without an end
    pose, although it had ended DONE with its final error written. Now the end pose is written from the tracked pose
    and the episode marked done before the end circle; a halt inside the circle stops the batch but not the episode."""
    real = B.BatchRunner.localise

    def stall_in_the_end_circle(self, env, what, required=True):
        if "end pose" in what and self.monitor.halted is None:
            self.monitor.halt("stall", "TURN_LEFT_30: stall_right (test)")
            raise B.BatchStop(what)
        return real(self, env, what, required=required)
    monkeypatch.setattr(B.BatchRunner, "localise", stall_in_the_end_circle)
    b = Batch(tmp_path, episodes=2, max_steps=30, starts=(S1, S5))
    b.run()
    assert b.result["status"] == "halted" and b.result["halt"]["code"] == "stall"
    e = b.manifest["episodes"][0]
    assert e["status"] == "done" and e["result"]["complete"] and e["halt"]["code"] == "stall"
    assert e["end_pose_source"] == "tracked, before the end circle" and e["end_pose_map"] is not None
    assert e.get("final_pose_error") is not None and len(b.manifest["episodes"]) == 1


def test_b2_real_04s_under_travel_reading_is_recorded_not_a_halt():
    """b2-real-04 (2026-11-25) halted at its start on the per-step fixes: -56 % +- 18 % over 2.0 m and 5 fixes, four
    of them single-tag fixes of T00 and T01 (seen across the motion, carrying the tracked heading's error) after
    northward legs, with one ranged forward move (0.99). Under-travel now never halts on its own; it is recorded. The
    same reading AHEAD of the odometry (+56 %) still halts, exactly as before, while fewer than 3 moves are ranged."""
    params = B.BatchParams(world_path="x", start_poses=[S1], initial_pose=dict(S1))
    t = _per_step(-0.565, 0.183, travel=2.0, fixes=5, ranges=[(0.9914, 2)])
    assert B.per_step_scale_halt(t, params) is None
    assert t.bias_under["per_step_scale"] == pytest.approx(-0.565) and t.bias_under["range_moves"] == 1
    ahead = _per_step(0.565, 0.183, travel=2.0, fixes=5, ranges=[(0.9914, 2)])
    why = B.per_step_scale_halt(ahead, params)
    assert why is not None and "+56 %" in why and "1 measured forward moves, fewer than 3" in why
    assert B.per_step_scale_halt(_per_step(0.13, 0.04, ranges=[]), params) is not None        # +13 %, 3.25 SE: halts
    assert B.per_step_scale_halt(_per_step(0.13, 0.05, ranges=[]), params) is None            # 2.6 SE: not yet


def test_the_tool_takes_the_slip_sigma_and_a_real_batch_must_state_it(tmp_path, capsys):
    """--slip-sigma (2026-11-25, the carpet): the tracker's extra sigma per metre of a forward move, recorded in the
    manifest's params. A dry run without it runs as before (0); a real batch without it is refused, like --dv; with it
    stated (0.3, or 0 to state it off) that refusal goes."""
    tool = load_batch_tool()
    base = ["run", "--world", str(WORLD20_PATH), "--start", "S1:2.5,1.5,90", "--initial-pose", "2.4,1.6,70",
            "--max-steps", "3", "--max-range", "3.0", "--dry-run"]
    assert tool.main(base + ["--out", str(tmp_path / "a"), "--slip-sigma", "0.3"]) == 0
    assert json.loads((tmp_path / "a" / "manifest.json").read_text())["params"]["odometry_slip_sigma_per_m"] == 0.3
    assert "odometry slip sigma 0.30 x forward distance" in capsys.readouterr().out
    assert tool.main(base + ["--out", str(tmp_path / "b")]) == 0
    assert json.loads((tmp_path / "b" / "manifest.json").read_text())["params"]["odometry_slip_sigma_per_m"] == 0.0
    real = ["run", "--world", str(WORLD20_PATH), "--start", "S1:2.5,1.5,90", "--initial-pose", "2.4,1.6,70", "--label", "t",
            "--marker", str(tmp_path / "none.json"), "--latch", str(tmp_path / "LATCH")]
    capsys.readouterr()
    assert tool.main(real) == 2
    assert "a real batch needs --slip-sigma stated" in capsys.readouterr().err
    for stated in ("0.3", "0"):
        assert tool.main(real + ["--slip-sigma", stated]) == 2              # still refused: no marker, no recorder
        err = capsys.readouterr().err
        assert "no pass marker" in err and "--slip-sigma" not in err
    with pytest.raises(SystemExit, match="--slip-sigma must be 0 to 1"):
        tool.main(base + ["--out", str(tmp_path / "c"), "--slip-sigma", "1.5"])


def test_an_error_inside_the_end_circle_leaves_the_episode_done_and_resume_skips_it(tmp_path, monkeypatch):
    """The review of 2026-11-25: a halt inside the end circle left the episode done, but an unexpected exception there
    marked it failed, and resume reruns every episode not done. Now both leave it done (its log and end pose are
    recorded), the exception is recorded with it, and the batch still halts on it (code "error")."""
    real = B.BatchRunner.localise

    def broken_end_circle(self, env, what, required=True):
        if "end pose" in what:
            raise RuntimeError("camera thread died (test)")
        return real(self, env, what, required=required)
    monkeypatch.setattr(B.BatchRunner, "localise", broken_end_circle)
    b = Batch(tmp_path, episodes=2, max_steps=30, starts=(S1, S5))
    result = b.runner.run()
    assert result["status"] == "halted" and result["halt"]["code"] == "error" and "camera thread died" in result["halt"]["detail"]
    m = json.loads((b.out / "manifest.json").read_text())
    e = m["episodes"][0]
    assert e["status"] == "done" and e["post_episode_error"] == "RuntimeError: camera thread died (test)"
    assert e["end_pose_source"] == "tracked, before the end circle" and e.get("final_pose_error") is not None
    assert {x["index"] for x in m["episodes"] if x["status"] == "done"} == {0}     # what resume skips


def _factor_two(tmp_path, factor, ranges, monkeypatch, seed=1):
    """A four-episode batch in the real room (its scenarios, --slip-sigma 0.3) with car.json's scale wrong by `factor`
    (0.5: the odometer reads half, the car goes twice as far as it thinks; 2.0: it reads double, the car covers half),
    the range check working or switched off (no ranged move ever). (result, smallest true footprint depth, contact)."""
    from beaconmind.car import config as C
    if not ranges:
        monkeypatch.setattr(B.BatchEnv, "_range_check", lambda self, exact, sense, record, first: None)
    cfg = C.load_config()
    wrong = cfg.replace(ticks_per_m_left=cfg.ticks_per_m_left / factor,
                        ticks_per_m_right=cfg.ticks_per_m_right / factor)
    world = json.loads((ROOT / "configs" / "arenas" / "real-room.json").read_text())
    starts = [dict(sc["start_pose"], id=sc["id"]) for sc in
              json.loads((ROOT / "configs" / "arenas" / "real-room-scenarios.json").read_text())["scenarios"]]
    place = {"x_m": 2.369, "y_m": 2.206, "theta_deg": -90.0}
    params = B.BatchParams(world_path="x", start_poses=starts, initial_pose=dict(place), episodes=4, max_steps=80,
                           max_range_m=3.0, odometry_slip_sigma_per_m=0.3)
    rig = B.dry_rig(world, place, latch=Latch(tmp_path / "LATCH"), seed=seed, max_range_m=3.0, cfg=wrong)
    runner = B.BatchRunner(params, rig, world, tmp_path / "batch", driver=cl.B2Driver(), budget=rp.Budget(float("inf")),
                           log=lambda *a: None, run_episode=cl.run_episode)
    depth = {"min": 9.0}
    walls = rig.link.on_step

    def watch(link):
        walls(link)
        depth["min"] = min(depth["min"], runner.guard.footprint_depth(rig.sim_truth_fn()))
    rig.link.on_step = watch
    result = runner.run()
    return result, depth["min"], bool(rig.link.sim.p.blocked_left or rig.link.sim.p.blocked_right)


def test_a_factor_two_scale_error_each_way_halts_in_the_real_room(tmp_path, monkeypatch):
    """The lead's question of 2026-11-25, with the drift bound record-only: what halts a factor-two scale error in
    each direction. In the real room, with the range check working: the range check, at the first ranged forward move,
    both ways (the car going twice as far: 2.0 above the +12 %; covering half: 0.5 below the 0.55 floor). This needs
    the range check's same-tag gate of 1.5 moves (half a move until 2026-11-25 dropped the over-travel pair as another
    tag). With the range check off: fix_conflict for over-travel, in episode 1 (the fixes land far ahead of where
    odometry puts the car); for under-travel fix_conflict in episode 3 in two seeds of three, while the third (seed 2)
    completes four episodes undetected: the car covers less than it thinks, the safe side, and stayed 0.55 m inside
    the driving area. No contact in any run. The 20-tag test room is the weak case: there the car going twice as far
    drove blind from its first forward moves (no tag in view) and reached a wall in 2 of 3 seeds with the range check
    working, 3 of 3 without; the same on 19f71e6 (the README's factor-two table)."""
    cases = ((0.5, True, ("odometry_scale",), 1.0), (2.0, True, ("odometry_scale",), 1.0),
             (0.5, False, ("fix_conflict",), 0.3), (2.0, False, ("fix_conflict", None), 0.3))
    for factor, ranges, codes, deepest in cases:
        with monkeypatch.context() as mp:
            result, depth, contact = _factor_two(tmp_path / ("f%s-%s" % (factor, ranges)), factor, ranges, mp)
        code = (result.get("halt") or {}).get("code")
        assert code in codes and result["status"] == ("halted" if code else "complete"), (factor, ranges, result)
        if ranges:
            assert "ranges to the tags" in result["halt"]["detail"], result
        assert depth > deepest and not contact, (factor, ranges, depth)
