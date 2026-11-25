"""The early blind limit's cost with a correct odometer: the tests' 20-tag room (its first forward moves can see no
tag) and the real room, four-episode B2 batches, seeds 1 to 3, the early limit 0.30 m against 0.75 m (none). Per run:
status, episodes done, moves sent, refusals by the early limit, looks around on the way, transit attempts, the
smallest true footprint depth.
usage (course-project/beaconmind): python3 blind_cap_cost.py

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this measurement."""
import json, sys, tempfile, pathlib, shutil
sys.path.insert(0, "src"); sys.path.insert(0, "tests")
from beaconmind.car import batch as B
from beaconmind.car.latch import Latch
from beaconmind.harness import closed_loop as cl, replay as rp
import test_car_batch as T
root = pathlib.Path("..")
real_world = json.load(open(root / "configs/arenas/real-room.json"))
real_starts = [dict(sc["start_pose"], id=sc["id"]) for sc in json.load(open(root / "configs/arenas/real-room-scenarios.json"))["scenarios"]]
rooms = {"20-tag room": (T.WORLD20, dict(T.PLACE20), [dict(T.S1), {"id": "S5", "x_m": 2.25, "y_m": 2.6, "theta_deg": 180.0}], 0.0),
         "real room": (real_world, {"x_m": 2.369, "y_m": 2.206, "theta_deg": -90.0}, real_starts, 0.3)}
for name, (world, place, starts, slip) in rooms.items():
    for early in (0.30, 0.75):
        for seed in (1, 2, 3):
            out = pathlib.Path(tempfile.mkdtemp())
            params = B.BatchParams(world_path="x", start_poses=starts, initial_pose=dict(place), episodes=4, max_steps=80,
                                   max_range_m=3.0, odometry_slip_sigma_per_m=slip, early_blind_travel_m=early)
            rig = B.dry_rig(world, place, latch=Latch(out / "LATCH"), seed=seed, max_range_m=3.0)
            logs = []
            runner = B.BatchRunner(params, rig, world, out / "batch", driver=cl.B2Driver(), budget=rp.Budget(float("inf")),
                                   log=lambda *a: logs.append(" ".join(str(x) for x in a)), run_episode=cl.run_episode)
            depth = {"min": 9.0}
            walls = rig.link.on_step

            def watch(link, walls=walls, depth=depth, runner=runner, rig=rig):
                walls(link)
                depth["min"] = min(depth["min"], runner.guard.footprint_depth(rig.sim_truth_fn()))
            rig.link.on_step = watch
            res = runner.run()
            m = json.load(open(out / "batch/manifest.json"))
            text = "\n".join(logs)
            refusals = 0
            for f in (out / "batch" / "episodes").rglob("*.jsonl"):
                refusals += f.read_text().count("forward moves are ranged")
            att = [e["start_fix"].get("attempts") for e in m["episodes"] if e.get("start_fix")]
            print("%-11s early %.2f seed %d | %-8s %-12s done %d | moves %4d | early-limit refusal mentions %3d | looks on the way %d | transit attempts %s | depth %.2f" % (
                name, early, seed, res["status"], (res.get("halt") or {}).get("code") or "-",
                sum(e["status"] == "done" for e in m["episodes"]), m["moves_sent"], refusals, text.count("a look around on the way"),
                att, depth["min"]), flush=True)
            shutil.rmtree(out, ignore_errors=True)
