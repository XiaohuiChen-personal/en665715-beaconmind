"""Copy run folders keeping only what tools/real_replay.py analyze reads: run headers, the spend ledger, and per row
step, seed, estimate_pose, seconds, fallback, error, cost_usd, config, fix_verified, checks.valid/repaired_chars,
report.pose_source and the calls' tool names. Usage: python3 trim_runs.py SRC_RUNS DST_RUNS FOLDER [FOLDER ...]
AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: helper for the M3.T19 real-log replay analysis."""
import json
import os
import shutil
import sys

KEEP = ("step", "seed", "estimate_pose", "seconds", "fallback", "error", "cost_usd", "config", "fix_verified")


def main():
    src_root, dst_root = sys.argv[1], sys.argv[2]
    for name in sys.argv[3:]:
        src, dst = os.path.join(src_root, name), os.path.join(dst_root, name)
        os.makedirs(dst, exist_ok=True)
        for f in sorted(os.listdir(src)):
            p = os.path.join(src, f)
            if f.startswith("seed_") and f.endswith(".jsonl"):
                with open(p, encoding="utf-8") as fi, open(os.path.join(dst, f), "w", encoding="utf-8") as fo:
                    for line in fi:
                        r = json.loads(line)
                        o = {k: r.get(k) for k in KEEP}
                        o["calls"] = [{"tool": c.get("tool")} for c in r.get("calls") or []]
                        o["checks"] = {k: (r.get("checks") or {}).get(k) for k in ("valid", "repaired_chars")}
                        o["report"] = {"pose_source": (r.get("report") or {}).get("pose_source")}
                        fo.write(json.dumps(o) + "\n")
            elif (f.startswith("run") and f.endswith(".json")) or f == "spend.jsonl":
                shutil.copy(p, dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
