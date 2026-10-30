#!/usr/bin/env python3
"""Run the L2 agent (Claude Opus 5.5) in replay over recorded pilot episodes, one thread per seed.

Run inside beaconmind-ros (anthropic 1.11.0), with ANTHROPIC_API_KEY from the secrets env_file:
  docker run --rm --network host --env-file ~/.config/beaconmind/secrets.env \
    -v ~/Projects/EN.665.715:/workspace -e PYTHONPATH=/workspace/course-project/beaconmind/src \
    beaconmind-ros:humble python3 /workspace/course-project/tools/pilot_replay.py \
    --obslogs /workspace/course-project/data/pilot/obslogs --out /workspace/course-project/data/pilot/runs/opus \
    --seeds 1000-1004 --max-steps 60 --cap-usd 80
The key is read from the environment and never printed or logged. Resumable: re-running continues
each seed after its last logged step.

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: wrote this runner.
"""
import argparse
import concurrent.futures as cf
import json
import os
import pathlib
import sys
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "beaconmind" / "src"))
from beaconmind.harness import anthropic_replay as ar  # noqa: E402
from pilot_record import seed_list  # noqa: E402

PRINT = threading.Lock()


def log(msg):
    with PRINT:
        print(time.strftime("%H:%M:%S"), msg, flush=True)


def spent_so_far(out_dir):
    total = 0.0
    for p in out_dir.glob("seed_*.jsonl"):
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                total += json.loads(line).get("cost_usd", 0.0)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--obslogs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--max-steps", type=int, default=60)
    ap.add_argument("--cap-usd", type=float, required=True)
    ap.add_argument("--prompt", default=str(ROOT / "prompts" / "robot_system_prompt_v3.3.txt"))
    args = ap.parse_args()
    import anthropic
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("ANTHROPIC_API_KEY is not set")
    client = anthropic.Anthropic(api_key=key, timeout=900, max_retries=0)
    system_text = pathlib.Path(args.prompt).read_text(encoding="utf-8")
    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    import fcntl
    lock = open(out_dir / ".lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        sys.exit("another pilot_replay.py is already writing %s" % out_dir)
    budget = ar.Budget(args.cap_usd, spent_so_far(out_dir))
    log("start: %s, prompt %s, spent so far $%.2f, cap $%.2f" % (ar.SETTINGS, pathlib.Path(args.prompt).name,
                                                                  budget.spent, budget.cap))
    import hashlib

    def sha12(p):
        return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:12]
    src = ROOT / "beaconmind" / "src" / "beaconmind"
    header = {"settings": ar.SETTINGS, "price_usd_per_mtok": ar.PRICE, "prompt_file": pathlib.Path(args.prompt).name,
              "max_steps": args.max_steps, "seeds": seed_list(args.seeds), "cap_usd": args.cap_usd,
              "anthropic_sdk": anthropic.__version__, "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "sha12": {"prompt": sha12(args.prompt), "dv.json": sha12(ROOT / "configs" / "dv.json"),
                        **{f: sha12(src / f) for f in ("geometry.py", "envs/kinsim_lite.py", "harness/tools_d5.py",
                                                       "harness/anthropic_replay.py")}}}
    name = "run.json" if not (out_dir / "run.json").exists() else "run.resume-%s.json" % time.strftime("%Y%m%dT%H%M%S")
    (out_dir / name).write_text(json.dumps(header, indent=1))

    def one(seed):
        doc = json.loads((pathlib.Path(args.obslogs) / ("seed_%d.json" % seed)).read_text(encoding="utf-8"))
        return seed, ar.replay_seed(client, system_text, doc, out_dir / ("seed_%d.jsonl" % seed), budget,
                                    args.max_steps, log)

    seeds = seed_list(args.seeds)
    with cf.ThreadPoolExecutor(max_workers=len(seeds)) as pool:
        for fut in cf.as_completed([pool.submit(one, s) for s in seeds]):
            try:
                seed, ok = fut.result()
                log("seed %d finished: %s" % (seed, "complete" if ok else "stopped at the cap"))
            except Exception as exc:  # report and keep the other seeds running
                log("a seed failed: %s: %s" % (type(exc).__name__, str(exc)[:300]))
    log("done: total spent $%.2f" % budget.spent)


if __name__ == "__main__":
    main()
