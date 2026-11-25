"""Prototype measurement: the tracker's slip-aware odometry sigma on a simulated slipping carpet.
usage (course-project/beaconmind): python3 slip_sigma_exp.py VARIANT OUT_JSON   VARIANT: base | flat | heading
Ten-episode batches with the exact real arguments on the simulated car, on a carpet where the car covers 0.67 or 0.60
of its counted distance northward (1.04 southward), 3 seeds each; the tracker as the batch runs it (base), with
0.3 x distance of slip sigma on forward moves (flat), or 0.10 + 0.25 x the northward component (heading).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this measurement."""
import json, math, os, sys, tempfile, pathlib, glob, statistics
sys.path.insert(0, "src")
from beaconmind.car import batch as B, simcar as S
from beaconmind.car.latch import Latch
from beaconmind.harness import closed_loop as cl, replay as rp
VARIANTS = {"base": (0.0, 0.0), "flat": (0.3, 0.0), "heading": (0.10, 0.25)}
variant = sys.argv[1]
root = pathlib.Path("..")
world = json.load(open(root / "configs/arenas/real-room.json"))
scen = json.load(open(root / "configs/arenas/real-room-scenarios.json"))
starts = [dict(sc["start_pose"], id=sc["id"]) for sc in scen["scenarios"]]
place = {"x_m": 2.369, "y_m": 2.206, "theta_deg": -90.0}
TH0 = math.radians(place["theta_deg"])
orig = S.SimCar.step
NORTH = {"v": 0.67}
def slip_step(self, dt):
    x0, y0 = self.x, self.y; orig(self, dt); dx, dy = self.x - x0, self.y - y0
    if dx or dy:
        n, s_ = NORTH["v"], 1.04
        k = (n + s_) / 2 - (s_ - n) / 2 * math.sin(TH0 + math.atan2(dy, dx)); self.x, self.y = x0 + k * dx, y0 + k * dy
S.SimCar.step = slip_step
results = []
for north in (0.67, 0.60):
    NORTH["v"] = north
    for seed in (1, 2, 3):
        out = pathlib.Path(tempfile.mkdtemp())
        a, b = VARIANTS[variant]
        params = B.BatchParams(world_path="x", start_poses=starts, initial_pose=dict(place), episodes=10, max_steps=150, max_range_m=3.0,
                               range_bias_a_m=0.00492, range_bias_b=-0.01658, range_min_m=0.785,
                               odometry_slip_sigma_per_m=a, odometry_slip_north_per_m=b)
        rig = B.dry_rig(world, place, latch=Latch(out / "LATCH"), seed=seed, max_range_m=3.0)
        runner = B.BatchRunner(params, rig, world, out / "batch", driver=cl.B2Driver(), budget=rp.Budget(float("inf")), log=lambda *a: None, run_episode=cl.run_episode)
        res = runner.run()
        m = json.load(open(out / "batch/manifest.json"))
        errs, ep_errs, beyond, acc, rej = [], [], 0, 0, 0
        for f in glob.glob(str(out / "batch/episodes/*/truth.jsonl")) + glob.glob(str(out / "batch/episodes/*/*/truth.jsonl")):
            is_ep = os.path.basename(os.path.dirname(f)).startswith("ep")
            for l in open(f):
                t = json.loads(l); s_ = t.get("sim_truth_world"); tw = t["tracked_world"]
                vf = t.get("view_fix") or {}
                if vf.get("ok"): acc += 1
                if vf.get("why") == "far_from_prior" or vf.get("position_fix") == "far_from_prior" or vf.get("rejected"): rej += 1
                if not s_: continue
                e = math.hypot(s_["x_m"] - tw["pose"]["x_m"], s_["y_m"] - tw["pose"]["y_m"])
                errs.append(e); beyond += e > 2 * tw["sigma_xy_m"]
                if is_ep: ep_errs.append(e)
        q = lambda v, p: sorted(v)[min(len(v) - 1, int(p * len(v)))] if v else None
        r = {"variant": variant, "north": north, "seed": seed, "status": res["status"], "halt": (res.get("halt") or {}).get("code"),
             "done": sum(e["status"] == "done" for e in m["episodes"]), "moves": m["moves_sent"],
             "guard_refusals": sum(e.get("guard_blocked_moves", 0) for e in m["episodes"]),
             "p95": q(errs, 0.95), "max": max(errs), "ep_p95": q(ep_errs, 0.95), "ep_max": max(ep_errs) if ep_errs else None,
             "beyond_2sigma": beyond / len(errs), "fixes_accepted": acc, "fixes_refused": rej,
             "final_errors": [(e.get("final_pose_error") or {}).get("m") for e in m["episodes"]],
             "tracked_minus_end_circle": [(e.get("tracked_minus_end_scan") or {}).get("m") for e in m["episodes"]]}
        results.append(r)
        print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k not in ("final_errors", "tracked_minus_end_circle")}), flush=True)
json.dump(results, open(sys.argv[2], "w"))
