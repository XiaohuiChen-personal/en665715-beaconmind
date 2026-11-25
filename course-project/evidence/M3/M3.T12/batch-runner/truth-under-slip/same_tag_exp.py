"""The same-tag rule, old against new, on the simulated slipping carpet (north 0.67 and 0.60, south 1.04), with the
exact real arguments and --slip-sigma 0.3: ten-episode B2 batches, 3 seeds each.
rule old: a fix on exactly the last fix's tags leaves the position sigma as it was (before 2026-11-25);
rule new: it leaves it no larger than the fix's own sigma (PoseTracker._shrink).
usage (course-project/beaconmind): python3 same_tag_exp.py OUT.jsonl [workers]

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this measurement."""
import json, math, os, shutil, sys, tempfile, pathlib, glob, multiprocessing as mp
sys.path.insert(0, "src")
from beaconmind.car import batch as B, simcar as S
from beaconmind.car.latch import Latch
from beaconmind.harness import closed_loop as cl, replay as rp
root = pathlib.Path("..")
world = json.load(open(root / "configs/arenas/real-room.json"))
scen = json.load(open(root / "configs/arenas/real-room-scenarios.json"))
starts = [dict(sc["start_pose"], id=sc["id"]) for sc in scen["scenarios"]]
place = {"x_m": 2.369, "y_m": 2.206, "theta_deg": -90.0}
TH0 = math.radians(place["theta_deg"])
NEW_SHRINK = B.PoseTracker._shrink


def old_shrink(self, same, a, b, fix_sigma):
    if not same:
        self.sigma_xy_m = max(math.sqrt(a * b / (a + b)), self.floor_m)


ORIG_STEP = S.SimCar.step      # captured once: a worker that runs several jobs must not stack the slip


def one(job):
    rule, north, seed = job
    orig = ORIG_STEP

    def slip_step(self, dt):
        x0, y0 = self.x, self.y; orig(self, dt); dx, dy = self.x - x0, self.y - y0
        if dx or dy:
            k = (north + 1.04) / 2 - (1.04 - north) / 2 * math.sin(TH0 + math.atan2(dy, dx)); self.x, self.y = x0 + k * dx, y0 + k * dy
    S.SimCar.step = slip_step
    B.PoseTracker._shrink = NEW_SHRINK if rule == "new" else old_shrink
    out = pathlib.Path(tempfile.mkdtemp())
    params = B.BatchParams(world_path="x", start_poses=starts, initial_pose=dict(place), episodes=10, max_steps=150, max_range_m=3.0,
                           range_bias_a_m=0.00492, range_bias_b=-0.01658, range_min_m=0.785, odometry_slip_sigma_per_m=0.3)
    rig = B.dry_rig(world, place, latch=Latch(out / "LATCH"), seed=seed, max_range_m=3.0)
    runner = B.BatchRunner(params, rig, world, out / "batch", driver=cl.B2Driver(), budget=rp.Budget(float("inf")), log=lambda *a: None, run_episode=cl.run_episode)
    depth = {"min": 9.0}
    walls = rig.link.on_step

    def watch(link):
        walls(link)
        depth["min"] = min(depth["min"], runner.guard.footprint_depth(rig.sim_truth_fn()))
    rig.link.on_step = watch
    res = runner.run()
    m = json.load(open(out / "batch/manifest.json"))
    errs, ep_errs, beyond, sig, z = [], [], 0, [], []
    for f in glob.glob(str(out / "batch/episodes/*/truth.jsonl")) + glob.glob(str(out / "batch/episodes/*/*/truth.jsonl")):
        is_ep = os.path.basename(os.path.dirname(f)).startswith("ep")
        for l in open(f):
            t = json.loads(l); s_ = t.get("sim_truth_world"); tw = t["tracked_world"]
            sig.append(tw["sigma_xy_m"])
            if not s_:
                continue
            e = math.hypot(s_["x_m"] - tw["pose"]["x_m"], s_["y_m"] - tw["pose"]["y_m"])
            errs.append(e); beyond += e > 2 * tw["sigma_xy_m"]; z.append(e / tw["sigma_xy_m"])
            if is_ep:
                ep_errs.append(e)
    shutil.rmtree(out, ignore_errors=True)        # the batch folder is no longer needed (tens of MB each)
    q = lambda v, p: sorted(v)[min(len(v) - 1, int(p * len(v)))] if v else None
    halt = res.get("halt") or {}
    return {"rule": rule, "north": north, "seed": seed, "status": res["status"], "halt": halt.get("code"),
            "halt_detail": (halt.get("detail") or "")[:140],
            "done": sum(e["status"] == "done" for e in m["episodes"]), "moves": m["moves_sent"],
            "p95": q(errs, 0.95), "max": max(errs), "ep_p95": q(ep_errs, 0.95), "ep_max": max(ep_errs) if ep_errs else None,
            "beyond_2sigma": beyond / len(errs), "z_p99": q(z, 0.99), "sigma_p95": q(sig, 0.95), "sigma_max": max(sig),
            "min_true_depth_m": depth["min"], "contact": bool(rig.link.sim.p.blocked_left or rig.link.sim.p.blocked_right),
            "final_errors": [(e.get("final_pose_error") or {}).get("m") for e in m["episodes"]],
            "tracked_minus_end_circle": [(e.get("tracked_minus_end_scan") or {}).get("m") for e in m["episodes"]]}


if __name__ == "__main__":
    jobs = [(rule, north, seed) for rule in ("old", "new") for north in (0.67, 0.60) for seed in (1, 2, 3)]
    with mp.get_context("fork").Pool(int(sys.argv[2]) if len(sys.argv) > 2 else 6, maxtasksperchild=1) as pool, open(sys.argv[1], "w") as fh:
        for r in pool.imap_unordered(one, jobs):
            fh.write(json.dumps(r) + "\n"); fh.flush()
            print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k not in ("final_errors", "tracked_minus_end_circle", "halt_detail")}), flush=True)
