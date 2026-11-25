#!/usr/bin/env python3
"""Recompute a batch's step truth offline, from its logged detections and odometry, with another tracker setting:
python3 course-project/tools/recompute_truth.py BATCH_DIR [--slip-sigma A] [--slip-north B] [--episode ID] [--out JSON]

Analysis only: nothing is sent to a car and nothing in BATCH_DIR is changed. For every episode with a step log
(episodes/<id>/backend/steps.jsonl), the batch's own per-step code (BatchEnv._post: the view fix, the one-tag fix, the
disagreement test, the blend) is run again over the logged rows. It starts from the tracked pose and sigmas the batch
logged at the episode's first row (the start circle's fix), with the tracker's odometry sigma made slip-aware by A and
B (PoseTracker: extra sigma per metre of a forward move, B more by its northward component; 0 and 0 is the tracker the
batch ran). Every surveyed tag may steer a fix (the batch's tag trust is not replayed; by the episodes of the real
batches every tag seen had been checked and trusted).

It prints, per episode:
- the recomputed truth against the logged one: the largest difference over the steps;
- the truth at the step of the agent's last report, logged and recomputed, and the agent's final error against each;
- the end circle's pose (a full circle of many tags, solved on its own) against the tracked pose after the episode's
  last move, logged and recomputed;
- in a dry run, both truths against the simulated car's own pose (sim_truth_world).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this offline truth recomputation.
"""
import argparse
import json
import math
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "beaconmind" / "src"))


class _Monitor:
    def __init__(self):
        self.halted = None
        self.halts = []

    def check_latch(self):
        pass

    def check_sense(self, *args, **kwargs):
        pass

    def clock(self):
        return 0.0

    def halt(self, code, detail, safety=None):
        self.halts.append((code, detail))         # recorded, never acted on: the replay goes through every row


class _Inner:
    def __init__(self):
        self.last_step = None
        self._last_forward = 0.10


def _rows(path):
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def replay_episode(batch, entry, params, world, slip_sigma=0.0, slip_north=0.0):
    """[(row index, step, recomputed truth in the arena frame with its sigma, the logged truth row)] for one episode."""
    from beaconmind.car import batch as B
    from beaconmind.car.config import load_car
    ep_dir = os.path.join(batch, "episodes", entry["id"])
    steps, truth = _rows(os.path.join(ep_dir, "backend", "steps.jsonl")), _rows(os.path.join(ep_dir, "truth.jsonl"))
    first = truth[0]["tracked_world"]
    tracker = B.PoseTracker(first["pose"], first["sigma_xy_m"], first.get("sigma_theta_deg", 1.0), params.fix_floor_m,
                            slip_sigma, slip_north)
    car = load_car()
    env = B.BatchEnv.__new__(B.BatchEnv)
    env.inner, env.tracker, env.monitor = _Inner(), tracker, _Monitor()
    env.guard = B.MoveGuard(world, [tuple(c) for c in car["corners"]], float(car["sweep_radius_m"]), params.wall_margin_m,
                            params.sigma_block_m, start_turn_margin_m=params.start_turn_margin_m)
    env.tags = [{"id": t["id"], "uid": t.get("uid"), "x_m": t["x_m"], "y_m": t["y_m"]} for t in world["tags"]]
    env.params, env.start, env.tagcheck = params, dict(entry["start_pose_world"]), None
    env.truth_path, env.sim_truth_fn = None, None
    env.use_views, env.in_scan, env.range_before, env.t_frame, env.last_fix, env.blocked, env.rows = True, False, None, 0.0, None, 0, 0
    out = []
    for i, (row, logged) in enumerate(zip(steps, truth)):
        env.inner.last_step = row
        sense = json.loads(json.dumps(row["sense"]))
        action = ((row.get("executed") or {}).get("command") or {}).get("action")
        env._post(sense, action, first=(i == 0))
        out.append((i, row["step"], {"pose": dict(tracker.pose), "sigma_xy_m": tracker.sigma_xy_m}, logged))
    return out, env.monitor.halts


def last_report(path):
    """(the agent's last valid report's pose, the logged truth of that row, the row's index), map frame; as
    batch._last_report, with the index (the seed log's rows line up with the step log's and truth.jsonl's)."""
    pose = truth = index = None
    if not os.path.exists(path):
        return None, None, None
    for i, row in enumerate(_rows(path)):
        report = row.get("report")
        if isinstance(report, dict) and isinstance(report.get("pose"), dict) and isinstance(row.get("truth"), dict):
            try:
                pose = {k: float(report["pose"][k]) for k in ("x_m", "y_m", "theta_deg")}
            except (KeyError, TypeError, ValueError):
                continue
            truth, index = dict(row["truth"]), i
    return pose, truth, index


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("batch")
    ap.add_argument("--slip-sigma", type=float, default=0.0)
    ap.add_argument("--slip-north", type=float, default=0.0)
    ap.add_argument("--episode")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    from beaconmind.car import batch as B
    man = json.loads(open(os.path.join(args.batch, "manifest.json"), encoding="utf-8").read())
    fields = {f for f in B.BatchParams.__dataclass_fields__}
    params = B.BatchParams(**{k: v for k, v in man["params"].items() if k in fields})
    world_path = man["params"]["world_path"]
    world = json.loads(open(world_path if os.path.isabs(world_path) else ROOT / world_path, encoding="utf-8").read())
    print("batch %s; tracker slip sigma %.2f + %.2f x north per metre of forward move" % (
        os.path.basename(os.path.normpath(args.batch)), args.slip_sigma, args.slip_north))
    report = []
    for entry in man["episodes"]:
        if args.episode and entry["id"] != args.episode:
            continue
        if not os.path.exists(os.path.join(args.batch, "episodes", entry["id"], "backend", "steps.jsonl")):
            continue
        rows, halts = replay_episode(args.batch, entry, params, world, args.slip_sigma, args.slip_north)
        start = entry["start_pose_world"]
        diff = max(math.hypot(r["pose"]["x_m"] - lg["tracked_world"]["pose"]["x_m"], r["pose"]["y_m"] - lg["tracked_world"]["pose"]["y_m"])
                   for _, _, r, lg in rows)
        line = {"episode": entry["id"], "scenario": entry.get("scenario"), "steps": len(rows),
                "largest_difference_from_the_logged_truth_m": round(diff, 3), "replay_halts": [h[0] for h in halts]}
        seed_log = os.path.join(args.batch, "episodes", entry["id"], "seed_%d.jsonl" % entry["seed"])
        agent, logged_truth, k = last_report(seed_log)
        if agent and logged_truth and k is not None and k < len(rows):
            new = B.to_map_pose(start, rows[k][2]["pose"])
            line["final_error_logged_m"] = round(math.hypot(agent["x_m"] - logged_truth["x_m"], agent["y_m"] - logged_truth["y_m"]), 3)
            line["final_error_recomputed_m"] = round(math.hypot(agent["x_m"] - new["x_m"], agent["y_m"] - new["y_m"]), 3)
            line["final_truth_sigma_logged_m"] = logged_truth.get("sigma_xy_m")
            line["final_truth_sigma_recomputed_m"] = round(rows[k][2]["sigma_xy_m"], 3)
            line["final_truth_shift_m"] = round(math.hypot(new["x_m"] - logged_truth["x_m"], new["y_m"] - logged_truth["y_m"]), 3)
            sim_k = rows[k][3].get("sim_truth_world")
            if sim_k:
                lg = rows[k][3]["tracked_world"]["pose"]
                line["final_truth_vs_sim_logged_m"] = round(math.hypot(lg["x_m"] - sim_k["x_m"], lg["y_m"] - sim_k["y_m"]), 3)
                line["final_truth_vs_sim_recomputed_m"] = round(math.hypot(rows[k][2]["pose"]["x_m"] - sim_k["x_m"],
                                                                           rows[k][2]["pose"]["y_m"] - sim_k["y_m"]), 3)
        end_fix = entry.get("end_fix") or {}
        if agent and end_fix.get("ok") and end_fix.get("pose") and k == len(rows) - 1:
            # the last report was the last step (an episode that ended by DONE moves no more): the end circle
            # measured the very pose the agent reported, from many tags and not through the tracker
            circle_map = B.to_map_pose(start, end_fix["pose"])
            line["final_error_vs_end_circle_m"] = round(math.hypot(agent["x_m"] - circle_map["x_m"], agent["y_m"] - circle_map["y_m"]), 3)
        if end_fix.get("ok") and end_fix.get("pose"):
            circle, last_r, last_lg = end_fix["pose"], rows[-1][2]["pose"], rows[-1][3]["tracked_world"]["pose"]
            line["end_circle_rms_m"] = round(end_fix.get("rms_m") or 0, 3)
            line["logged_minus_end_circle_m"] = round(math.hypot(last_lg["x_m"] - circle["x_m"], last_lg["y_m"] - circle["y_m"]), 3)
            line["recomputed_minus_end_circle_m"] = round(math.hypot(last_r["x_m"] - circle["x_m"], last_r["y_m"] - circle["y_m"]), 3)
        sim = [(r, lg) for _, _, r, lg in rows if lg.get("sim_truth_world")]
        if sim:
            def err(pose, s):
                return math.hypot(pose["x_m"] - s["x_m"], pose["y_m"] - s["y_m"])
            lo = sorted(err(lg["tracked_world"]["pose"], lg["sim_truth_world"]) for r, lg in sim)
            re = sorted(err(r["pose"], lg["sim_truth_world"]) for r, lg in sim)
            line["sim_logged_p95_max_m"] = [round(lo[int(0.95 * (len(lo) - 1))], 3), round(lo[-1], 3)]
            line["sim_recomputed_p95_max_m"] = [round(re[int(0.95 * (len(re) - 1))], 3), round(re[-1], 3)]
        report.append(line)
        print(json.dumps(line))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
