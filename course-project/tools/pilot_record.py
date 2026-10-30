#!/usr/bin/env python3
"""Record the pilot's simulated EXPLORE episodes (arm B2 drives) as JSON observation logs.

Usage: python3 tools/pilot_record.py --seeds 1000-1004 --out data/pilot/obslogs
Each seed gives <out>/seed_<seed>.json with the world, the truth poses, the raw observations
(with each detection's true tag) and B2's reports and tool calls. Pure Python (stdlib only).

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: wrote this recorder.
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "beaconmind" / "src"))
from beaconmind.envs import kinsim_lite as ks  # noqa: E402


def seed_list(text):
    out = []
    for part in text.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b) + 1)) if b else [int(a)]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--odo-bias", type=float, default=0.0, help="systematic odometry over-read (0.02 = 2 %%)")
    args = ap.parse_args()
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for seed in seed_list(args.seeds):
        try:
            ep = ks.run_episode(seed, odo_bias=args.odo_bias)
        except NotImplementedError as exc:
            print("seed %d skipped: %s" % (seed, exc))
            continue
        ep["noise"] = dict(ks.NOISE, odo_bias=args.odo_bias)
        ep["arena"] = ks.ARENA
        (out / ("seed_%d.json" % seed)).write_text(json.dumps(ep), encoding="utf-8")
        recs = ep["records"]
        print("seed %d: %d steps, %d tags (%d duplicated ids), last decision %s" % (
            seed, len(recs), len(ep["world"]), len(ep["world"]) - len({t["id"] for t in ep["world"]}),
            recs[-1]["report"]["decision"]))


if __name__ == "__main__":
    main()
