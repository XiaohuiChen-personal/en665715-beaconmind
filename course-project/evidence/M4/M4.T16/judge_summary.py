#!/usr/bin/env python3
"""Summarise the main study's note rubric (descriptive; prereg.md §4 "Note rubric").

Reads `study_judge.py`'s output folder (items.jsonl, sol.jsonl, availability.json) and writes, per arm: the number
of notes scored, the rubric score (metrics/judge.py `score`: weighted levels with the faithfulness gate) as the mean
of the per-seed means (the seed is the unit, as in the pilot's `rubric_by_seed`), with a 10,000-resample bootstrap
interval over seeds (seed 12345, the prereg's descriptive convention), the median and range of the per-seed means,
the mean of each judged level (0-2) and of the concision level, the notes that failed the faithfulness gate
(faithful = 0), the judge's errors and spend, and the arm's share of steps with a judgeable note. Stdlib only.

Run from the repository root (Mac or Spark host):
  python3 course-project/evidence/M4/M4.T16/judge_summary.py course-project/data/main/judge/drift2 \
      > course-project/evidence/M4/M4.T16/judge_summary.txt

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-13: wrote this summary of the judge's output.
"""
import json
import pathlib
import random
import statistics
import sys

ARMS = ["claude-opus-5-5", "qwen38-flash-xhigh", "gemma4-26b"]
LEVELS = ("faithful", "coverage", "uncertainty", "concise")


def boot_mean(values, n=10000, seed=12345):
    rng = random.Random(seed)
    means = sorted(statistics.fmean(rng.choices(values, k=len(values))) for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n) - 1]


def main(folder):
    folder = pathlib.Path(folder)
    items = [json.loads(x) for x in (folder / "items.jsonl").read_text().splitlines() if x.strip()]
    recs = {}
    for x in (folder / "sol.jsonl").read_text().splitlines():
        if x.strip():
            r = json.loads(x)
            if r.get("levels") or r["id"] not in recs:      # a later success replaces an earlier error row
                recs[r["id"]] = r
    avail = json.loads((folder / "availability.json").read_text())
    spent = sum((json.loads(x).get("cost_usd") or 0.0) for x in (folder / "sol.jsonl").read_text().splitlines()
                if x.strip())
    out = {"items": len(items), "scored": sum(1 for r in recs.values() if r.get("levels")),
           "errors": sum(1 for r in recs.values() if not r.get("levels")), "spent_usd": round(spent, 2), "arms": {}}
    for arm in ARMS:
        mine = [it for it in items if it["arm"] == arm]
        scored = [recs[it["id"]] for it in mine if recs.get(it["id"], {}).get("levels")]
        by_seed = {}
        for r in scored:
            by_seed.setdefault(r["seed"], []).append(r)
        seed_means = [statistics.fmean(x["score"] for x in v) for _, v in sorted(by_seed.items())]
        lv = {k: statistics.fmean((r["levels"].get(k) if k != "concise" else r["concise"]) for r in scored)
              for k in LEVELS} if scored else {}
        out["arms"][arm] = {
            "notes_sampled": len(mine), "notes_scored": len(scored), "seeds": len(by_seed),
            "rubric_mean_of_seed_means": statistics.fmean(seed_means) if seed_means else None,
            "rubric_mean_ci95": list(boot_mean(seed_means)) if seed_means else None,
            "rubric_seed_median": statistics.median(seed_means) if seed_means else None,
            "rubric_seed_range": [min(seed_means), max(seed_means)] if seed_means else None,
            "mean_levels": lv,
            "faithful_0": sum(1 for r in scored if r["levels"]["faithful"] == 0),
            "faithful_1": sum(1 for r in scored if r["levels"]["faithful"] == 1),
            "judgeable_share": avail.get(arm, {}).get("share"),
            "judgeable_steps": [avail.get(arm, {}).get("with_note"), avail.get(arm, {}).get("steps")],
        }
    print(json.dumps(out, indent=1))
    print()
    print("%-20s %6s %22s %16s %9s %9s %9s %8s %10s %9s" % ("arm", "notes", "rubric mean [95% CI]", "seed range",
                                                          "faithful", "coverage", "uncert.", "concise", "faith.=0", "judgeable"))
    for arm, a in out["arms"].items():
        lo, hi = a["rubric_mean_ci95"]
        print("%-20s %6d %8.3f [%.3f, %.3f] %7.3f-%.3f %9.2f %9.2f %9.2f %8.2f %5d/%-4d %8.1f%%" % (
            arm, a["notes_scored"], a["rubric_mean_of_seed_means"], lo, hi, a["rubric_seed_range"][0],
            a["rubric_seed_range"][1], a["mean_levels"]["faithful"], a["mean_levels"]["coverage"],
            a["mean_levels"]["uncertainty"], a["mean_levels"]["concise"], a["faithful_0"], a["notes_scored"],
            100 * a["judgeable_share"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
