"""The same-tag rule, old against new, under mis-surveyed tags: the review's tag_probe.py (2026-11-24) with the tag
check on in both modes. The runner's world file has one tag moved by d metres along +x, -x, +y or -y; the simulated
room has it where it really is. Every tag of the 20-tag world, d in 0.1, 0.3, 0.5 m, B2, 3 episodes (S1, S3, S4),
3.0 m range, plus 8 clean seeds. Mode `old`: a fix on the last fix's tags leaves the sigma as it was (before
2026-11-25); `new`: no larger than the fix's own (PoseTracker._shrink).

Per run: outcome, halt code, whether a tag_survey halt named the moved tag, the smallest true footprint depth inside
the driving area (simulated car), the largest error of the tracked pose against the simulated truth while the batch
was not halted; and the step fixes that used the moved tag, the sigma at them, the largest error at them.

usage (course-project/beaconmind): python3 tag_probe_rule.py OUT.jsonl [workers [slip_sigma [d,d,...]]]
(slip_sigma: the tracker's odometry slip sigma, default 0; d: the shifts, default 0.1,0.3,0.5 and the clean seeds)

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote tag_probe.py for the review. 2026-11-25: adapted it
to compare the same-tag rules.
"""
import json
import math
import multiprocessing as mp
import os
import shutil
import sys
import tempfile

ROOT = os.environ.get("BM_ROOT", os.path.abspath(".."))
sys.path.insert(0, ROOT + "/beaconmind/src")

from beaconmind.car import batch as B             # noqa: E402
from beaconmind.car.latch import Latch            # noqa: E402
from beaconmind.harness import closed_loop as cl  # noqa: E402
from beaconmind.harness import replay as rp       # noqa: E402

WORLD = json.load(open(ROOT + "/configs/arenas/real-room-plus8-160mm-nominal.json"))
SCEN = {s["id"]: dict(s["start_pose"], id=s["id"]) for s in json.load(open(ROOT + "/configs/arenas/real-room-scenarios.json"))["scenarios"]}
PLACE = {"x_m": 2.4, "y_m": 1.6, "theta_deg": 70.0}
DIRS = {"+x": (1, 0), "-x": (-1, 0), "+y": (0, 1), "-y": (0, -1)}


NEW_SHRINK = B.PoseTracker._shrink


def old_shrink(self, same, a, b, fix_sigma):
    if not same:
        self.sigma_xy_m = max(math.sqrt(a * b / (a + b)), self.floor_m)


SLIP = {"sigma": float(os.environ.get("PROBE_SLIP_SIGMA", "0"))}   # set by main(); spawned workers read it here


def one(job):
    mode, uid, d, direction, seed = job
    B.PoseTracker._shrink = NEW_SHRINK if mode == "new" else old_shrink
    wrong = json.loads(json.dumps(WORLD))
    if uid:
        for t in wrong["tags"]:
            if t["uid"] == uid:
                t["x_m"] += d * DIRS[direction][0]
                t["y_m"] += d * DIRS[direction][1]
    extra = {"odometry_slip_sigma_per_m": SLIP["sigma"]} if SLIP["sigma"] else {}
    tmp = tempfile.mkdtemp(prefix="probe-")
    params = B.BatchParams(world_path="x", start_poses=[SCEN["S1"], SCEN["S3"], SCEN["S4"]], initial_pose=dict(PLACE),
                           episodes=3, max_steps=60, max_range_m=3.0, seed0=seed, **extra)
    latch = Latch(os.path.join(tmp, "LATCH"))
    rig = B.dry_rig(WORLD, PLACE, latch=latch, seed=seed, max_range_m=3.0)
    runner = B.BatchRunner(params, rig, wrong, os.path.join(tmp, "batch"), driver=cl.B2Driver(),
                           budget=rp.Budget(float("inf")), log=lambda *a: None, run_episode=cl.run_episode)
    stat = {"depth": 9.0, "err": 0.0, "moved_fixes": 0, "moved_sigma": [], "moved_err": 0.0}
    walls = rig.link.on_step
    count = {"n": 0}

    def watch(link):
        walls(link)
        count["n"] += 1
        if count["n"] % 5:
            return
        stat["depth"] = min(stat["depth"], runner.guard.footprint_depth(rig.sim_truth_fn()))
    rig.link.on_step = watch
    result = runner.run()
    import glob
    for path in glob.glob(os.path.join(tmp, "batch", "episodes", "**", "truth.jsonl"), recursive=True):
        for line in open(path):
            row = json.loads(line)
            w, t = row["tracked_world"]["pose"], row["sim_truth_world"]
            if row["halted"] is None and t:
                stat["err"] = max(stat["err"], math.hypot(w["x_m"] - t["x_m"], w["y_m"] - t["y_m"]))
            vf = row.get("view_fix") or {}
            if uid and vf.get("ok") and uid in (vf.get("tags") or []):
                stat["moved_fixes"] += 1
                stat["moved_sigma"].append(row["tracked_world"]["sigma_xy_m"])
                if t:
                    stat["moved_err"] = max(stat["moved_err"], math.hypot(w["x_m"] - t["x_m"], w["y_m"] - t["y_m"]))
    halt = result.get("halt") or {}
    m = json.load(open(os.path.join(tmp, "batch", "manifest.json")))
    shutil.rmtree(tmp, ignore_errors=True)        # each batch folder is ~24 MB: 496 of them filled the disk once
    return {"mode": mode, "tag": uid, "d": d, "dir": direction, "seed": seed, "slip_sigma": SLIP["sigma"],
            "status": result["status"],
            "halt": halt.get("code"), "named": bool(uid) and halt.get("code") == "tag_survey" and ("tag %s " % uid) in halt.get("detail", ""),
            "halt_detail": halt.get("detail", "")[:160], "min_depth_m": round(stat["depth"], 3),
            "max_pose_err_m": round(stat["err"], 3), "episodes_done": sum(e["status"] == "done" for e in m["episodes"]),
            "contact": bool(rig.link.sim.p.blocked_left or rig.link.sim.p.blocked_right),
            "moves": m["moves_sent"], "moved_tag_step_fixes": stat["moved_fixes"],
            "moved_tag_sigma_min_max": [min(stat["moved_sigma"]), max(stat["moved_sigma"])] if stat["moved_sigma"] else None,
            "moved_tag_max_err_m": round(stat["moved_err"], 3)}


def main():
    out = sys.argv[1]
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    SLIP["sigma"] = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
    os.environ["PROBE_SLIP_SIGMA"] = repr(SLIP["sigma"])
    shifts = [float(v) for v in sys.argv[4].split(",")] if len(sys.argv) > 4 else [0.1, 0.3, 0.5]
    jobs = []
    for mode in ("old", "new"):
        if len(sys.argv) <= 4:
            for seed in range(1, 9):
                jobs.append((mode, None, 0.0, "+x", seed))
        for t in WORLD["tags"]:
            for d in shifts:
                for direction in DIRS:
                    jobs.append((mode, t["uid"], d, direction, 1))
    done = set()                                  # resume: jobs already in OUT are kept and not run again
    if os.path.exists(out):
        done = {(r["mode"], r["tag"], r["d"], r["dir"], r["seed"]) for r in map(json.loads, open(out))}
    jobs = [j for j in jobs if j not in done]
    with mp.Pool(workers) as pool, open(out, "a") as fh:
        for i, row in enumerate(pool.imap_unordered(one, jobs)):
            fh.write(json.dumps(row) + "\n")
            fh.flush()
    print("done", len(jobs))


if __name__ == "__main__":
    main()
