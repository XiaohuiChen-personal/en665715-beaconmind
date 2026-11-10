#!/usr/bin/env python3
"""Score a pre-registered sample of the main study's notes with the pilot's selected judge (descriptive).

The judge, its prompt, the evidence it sees (version 2) and the rubric are the pilot's
(metrics/judge.py; selection in evidence/M4/M4.T11/: GPT-6.1 Sol met every calibration threshold, Gemma 4 did
not). No arm is an OpenAI model, so the judge never scores its own family. The sample: for each arm and seed, 10
steps drawn at random (seed 777, the same draw for a given seed and arm on any machine) from the steps whose
report is valid and carries a non-empty note; fewer if a seed has fewer. Because that pool favours arms with fewer
invalid reports, each arm's share of steps with a judgeable note is written to availability.json and reported with
the rubric. Items are interleaved by seed across arms. Run it only after the runs are final. Resumable; a hard cap.

Run inside beaconmind-ros on the Spark (openai SDK; OPENAI_API_KEY from the secrets env_file, never printed):
  docker run --rm --user $(id -u):$(id -g) -e HOME=/tmp --network host --env-file ~/.config/beaconmind/secrets.env \
    -e PYTHONPATH=/workspace/course-project/beaconmind/src -v ~/Projects/en665715-beaconmind:/workspace beaconmind-ros:humble \
    python3 /workspace/course-project/tools/study_judge.py --runs /workspace/course-project/data/main/runs/drift2 \
      --arms claude-opus-5-5,qwen38-flash-xhigh,gemma4-26b --seeds 2000-2029 \
      --out /workspace/course-project/data/main/judge/drift2 --cap-usd 25

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote this runner (from tools/pilot_judge.py).
"""
import argparse
import concurrent.futures as cf
import json
import os
import pathlib
import random
import sys
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "beaconmind" / "src"))
sys.path.insert(0, str(ROOT / "tools"))
from beaconmind.metrics import judge as J  # noqa: E402
from pilot_judge import load_rows  # noqa: E402

PER_SEED, SAMPLE_SEED, MODEL = 10, 777, "gpt-6.1-sol"
LOCK = threading.Lock()


def seed_list(text):
    out = []
    for part in text.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b) + 1)) if b else [int(a)]
    return out


def sample(rows, arm, seed):
    pool = sorted((r for r in rows if r["seed"] == seed and r["checks"]["valid"]
                   and isinstance((r["report"] or {}).get("note"), str) and r["report"]["note"].strip()),
                  key=lambda r: r["step"])
    rng = random.Random("%d|%s|%d" % (SAMPLE_SEED, arm, seed))
    return sorted(rng.sample(pool, min(PER_SEED, len(pool))), key=lambda r: r["step"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--arms", required=True)
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cap-usd", type=float, required=True)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    items, avail = [], {}
    arms = args.arms.split(",")
    rows_by_arm = {arm: load_rows(pathlib.Path(args.runs) / arm) for arm in arms}
    for arm, rows in rows_by_arm.items():          # share of steps with a judgeable note (reported with the rubric)
        n_ok = sum(1 for r in rows if r["checks"]["valid"] and isinstance((r["report"] or {}).get("note"), str)
                   and r["report"]["note"].strip())
        avail[arm] = {"steps": len(rows), "with_note": n_ok, "share": n_ok / len(rows) if rows else None}
    for seed in seed_list(args.seeds):              # interleaved by seed, so a spend cap cannot cut one arm alone
        for arm in arms:
            for r in sample(rows_by_arm[arm], arm, seed):
                items.append({"id": "%s:%d:%d" % (arm, seed, r["step"]), "arm": arm, "seed": seed, "step": r["step"],
                              "note": r["report"]["note"], "evidence": J.build_evidence(r)})
    (out / "availability.json").write_text(json.dumps(avail, indent=1))
    (out / "items.jsonl").write_text("".join(json.dumps({k: v for k, v in it.items() if k != "evidence"}) + "\n"
                                             for it in items), encoding="utf-8")
    path = out / "sol.jsonl"
    done, spent = set(), {"usd": 0.0}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                if rec.get("levels"):
                    done.add(rec["id"])
                spent["usd"] += rec.get("cost_usd") or 0.0
    todo = [it for it in items if it["id"] not in done]
    print("items %d, done %d, to do %d, spent $%.2f, cap $%.2f" % (len(items), len(done), len(todo), spent["usd"], args.cap_usd),
          flush=True)
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=600, max_retries=4)

    def one(it):
        with LOCK:
            if spent["usd"] >= args.cap_usd:
                return None
        prompt = J.judge_prompt(it["evidence"], it["note"])
        rec = {"id": it["id"], "arm": it["arm"], "seed": it["seed"], "step": it["step"], "judge": "sol", "model": MODEL,
               "concise": J.concise_level(it["note"])}
        t0 = time.time()
        for attempt in range(3):
            try:
                res = J.openai_judge(client, MODEL, prompt, effort="medium")
                rec.update(levels=res["levels"], reason=res["reason"], cost_usd=res.get("cost_usd", 0.0), error=None)
                rec["score"] = J.score(res["levels"], rec["concise"])
                break
            except Exception as exc:  # recorded and retried twice, then kept as an error row
                rec.update(levels=None, reason=None, cost_usd=0.0, error="%s: %s" % (type(exc).__name__, str(exc)[:200]))
                time.sleep(5 * (attempt + 1))
        rec["seconds"] = round(time.time() - t0, 1)
        with LOCK:
            spent["usd"] += rec["cost_usd"]
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec) + "\n")
        return rec

    n = 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for rec in pool.map(one, todo):
            n += 1
            if rec and (n % 50 == 0 or rec["error"]):
                print(time.strftime("%H:%M:%S"), n, "/", len(todo), rec["id"], rec["levels"], "$%.2f" % spent["usd"],
                      rec["error"] or "", flush=True)
    print("finished, spent $%.2f" % spent["usd"], flush=True)


if __name__ == "__main__":
    main()
