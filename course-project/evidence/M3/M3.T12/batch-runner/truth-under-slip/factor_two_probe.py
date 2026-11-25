"""Factor-two scale errors each way (configs/car.json's ticks per metre wrong by 2 in either direction), with the
range check working and with it off (no forward move ever ranged), in the real room with its scenarios (slip sigma
0.3) and in the tests' 20-tag room: four-episode B2 batches, seeds 1 to 3. Per run: the halt (odometry_scale split by
which check: the ranges or the per-step fixes), the episode it came in, the smallest true footprint depth inside the
driving area, and contact.
usage (course-project/beaconmind): python3 factor_two_probe.py
For the committed code before a change: the same with PYTHONPATH and the first sys.path entry at an extracted tree
(git archive <commit> course-project/beaconmind/src) and BM_COURSE_ROOT set.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this probe."""
import json, math, sys, tempfile, pathlib
sys.path.insert(0, "src"); sys.path.insert(0, "tests")
from beaconmind.car import batch as B, config as C
from beaconmind.car.latch import Latch
from beaconmind.harness import closed_loop as cl, replay as rp
import test_car_batch as T
root = pathlib.Path("..")
real_world = json.load(open(root / "configs/arenas/real-room.json"))
scen = json.load(open(root / "configs/arenas/real-room-scenarios.json"))
real_starts = [dict(sc["start_pose"], id=sc["id"]) for sc in scen["scenarios"]]
cfg = C.load_config()
ranges_on = B.BatchEnv._range_check
rooms = {"real room": (real_world, {"x_m": 2.369, "y_m": 2.206, "theta_deg": -90.0}, real_starts, 0.3),
         "20-tag room": (T.WORLD20, {"x_m": 2.4, "y_m": 1.6, "theta_deg": 70.0},
                         [{"id": "S1", "x_m": 2.5, "y_m": 1.5, "theta_deg": 90.0}, {"id": "S5", "x_m": 2.25, "y_m": 2.6, "theta_deg": 180.0}], 0.0)}
for name, (world, place, starts, slip) in rooms.items():
    for label, factor in (("odometry reads half: the car goes 2x (over-travel)", 0.5), ("odometry reads double: the car goes half (under-travel)", 2.0)):
        wrong = cfg.replace(ticks_per_m_left=cfg.ticks_per_m_left / factor, ticks_per_m_right=cfg.ticks_per_m_right / factor)
        for ranges in (True, False):
            B.BatchEnv._range_check = ranges_on if ranges else (lambda self, exact, sense, record, first: None)
            line = []
            for seed in (1, 2, 3):
                out = pathlib.Path(tempfile.mkdtemp())
                params = B.BatchParams(world_path="x", start_poses=starts, initial_pose=dict(place), episodes=4, max_steps=80, max_range_m=3.0,
                                       odometry_slip_sigma_per_m=slip)
                rig = B.dry_rig(world, place, latch=Latch(out / "LATCH"), seed=seed, max_range_m=3.0, cfg=wrong)
                runner = B.BatchRunner(params, rig, world, out / "batch", driver=cl.B2Driver(), budget=rp.Budget(float("inf")), log=lambda *a: None, run_episode=cl.run_episode)
                depth = {"min": 9.0}; walls = rig.link.on_step
                def watch(link, walls=walls, depth=depth, runner=runner, rig=rig):
                    walls(link); depth["min"] = min(depth["min"], runner.guard.footprint_depth(rig.sim_truth_fn()))
                rig.link.on_step = watch
                res = runner.run(); h = res.get("halt") or {}
                m = json.load(open(out / "batch/manifest.json"))
                kind = h.get("code") or "-"
                det = h.get("detail", "")
                if kind == "odometry_scale":
                    kind += ":ranges" if "ranges to the tags" in det else ":fixes" if "tag fixes land" in det else ":other"
                line.append("%s ep%d depth %.2f%s" % (kind, len(m["episodes"]), depth["min"], " CONTACT" if (rig.link.sim.p.blocked_left or rig.link.sim.p.blocked_right) else ""))
            print("%-11s | %-55s | ranges %-3s | %s" % (name, label, "on" if ranges else "off", " | ".join(line)), flush=True)
B.BatchEnv._range_check = ranges_on
