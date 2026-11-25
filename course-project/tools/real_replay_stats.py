#!/usr/bin/env python3
"""Exploratory paired differences on the real-log replay (M3.T19 / M4.T13), and what the per-step traces show.

    python3 course-project/tools/real_replay_stats.py --obslogs <set>/obslogs --result <analyze result.json> \
        --run <arm>=<run folder> [--run <arm>=<another folder of that arm>] ... --out <file stem>

`--result` is the output of `tools/real_replay.py analyze` (its per-episode errors against the three truths and the
truths themselves); `--run` gives the same run folders (trimmed copies are enough: tools' names, estimate_pose,
report.pose_source, checks, fallback, error, seconds, cost_usd per row), for the per-step traces and the run behaviour.

**Nothing here is a pre-registered test.** The pre-registration (evidence/M4/M4.T1/prereg.md section 6) reports the
real logs descriptively, as the sim-to-real gap; the report's Metrics section says they test no hypothesis; the
value used here (the final-position error against the end circle) was chosen after the data; and
evidence/M5/requirements.md records "no significance claim from a handful of trials". So this tool reports paired
differences only: per comparison the study's estimator (`metrics/stats.py`: the Hodges-Lehmann estimate with its exact
95 % interval, or the sample median with its exact order-statistic interval when the adjusted skewness exceeds 1, the
pre-registered switch) and the number of episodes below and above zero. No p-value, no multiplicity correction, no
rejection, no practical-significance verdict. Every model - B0 difference is shown beside B2 - B0, because a model
that follows the procedure inherits the procedure's gain over dead reckoning. H2 (against B1) is not run: B1 needs
oracle association, which the real logs do not have (their detections carry no true tag, and the room repeats tag
IDs).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this tool.
"""
import argparse
import collections
import importlib.util
import json
import math
import os
import pathlib
import statistics
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "beaconmind" / "src"))
from beaconmind import real_replay as rr  # noqa: E402
from beaconmind.metrics import pilot as pm  # noqa: E402
from beaconmind.metrics import stats as st  # noqa: E402
from scipy import stats as sps  # noqa: E402

_spec = importlib.util.spec_from_file_location("study_analyze", ROOT / "tools" / "study_analyze.py")
sa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sa)

LLM_ARMS = ("claude-opus-5-5", "qwen38-flash-xhigh", "gemma4-26b")     # the study's three model arms
DIVERGE_M = 0.05                                                       # an arm "parts from B2" beyond this


def _rows(folders, seed):
    return rr._arm_rows(folders, seed)


def _cm(v):
    return "" if v is None else "%.1f" % (100 * v)


def _ci(ci):
    return "%s to %s" % (_cm(ci[0]), _cm(ci[1])) if ci and ci[0] is not None else ""


def _p(p):
    return "" if p is None else ("%.4f" % p if p >= 0.0001 else "%.1e" % p)


# ---------------------------------------------------------------- values per seed and arm

def values(result, key, seeds, arms):
    """{seed: {arm: {"ate_m": value}}} for the seeds where every arm has the value (the study's functions read
    "ate_m"; here it holds whichever value is tested)."""
    per = {}
    for s in seeds:
        row = {}
        for a in arms:
            r = result["errors"].get(a, {}).get(str(s))
            if not r or not r.get("complete") or r.get(key) is None:
                break
            row[a] = {"ate_m": r[key]}
        else:
            per[s] = row
    return per


def ate_all_steps(docs, runs, seeds):
    """{seed: {arm: {"ate_m", "per_step_m"}}}: ATE-RMSE over all steps against the batch's logged (tracked) truth,
    unaligned, in the episode's map frame; B0 at report precision (the study's chain), B2 the car's own estimates."""
    out = {}
    for s in seeds:
        recs = docs[s]["records"]
        truth = [r["truth"] for r in recs]
        poses = {"B0": sa.dead_reckoning_chain(recs), "B2": [r["b2_estimate"] for r in recs]}
        for arm, folders in runs.items():
            rows = _rows(folders, s)
            if len(rows) == len(recs):
                poses[arm] = [r["estimate_pose"] for r in rows]
        out[s] = {}
        for arm, p in poses.items():
            e = pm.trajectory_errors(p, truth)
            out[s][arm] = {"ate_m": e["ate_m"], "per_step_m": e["per_step_m"], "poses": p}
    return out


# ---------------------------------------------------------------- paired differences (exploratory)

def paired(d):
    """The study's estimator on paired differences d (no test): Hodges-Lehmann with its exact 95 % interval, or the
    median with its exact interval when |adjusted skewness| > 1 (the pre-registered switch); counts below/above 0."""
    d = np.asarray(d, dtype=float)
    skew = st.adjusted_skewness(d) if len(d) > 2 else 0.0
    est, estimand = (st.median_ci(d), "median") if abs(skew) > sa.SKEW_LIMIT else (st.hodges_lehmann(d), "Hodges-Lehmann")
    return {"n": int(len(d)), "estimand": estimand, "estimate": est["estimate"], "ci95": est["ci"],
            "n_below": int((d < 0).sum()), "n_above": int((d > 0).sum()), "n_zero": int((d == 0).sum()),
            "mean": float(d.mean()), "skewness_G1": float(skew), "d": d.tolist()}


def differences(per, arms, label):
    """Exploratory: every arm - B0 (B2's first: the procedure's own gain), every LLM arm - B2 (with the
    pre-registration's descriptive "within 1 cm of B2 on every episode" check), the LLM pairs and their mean ranks."""
    seeds = sorted(per)
    llm = [a for a in LLM_ARMS if a in arms]
    out = {"label": label, "n": len(seeds), "seeds": seeds, "exploratory": True,
           "h2": "not run: B1 needs oracle association, which the real logs do not have",
           "vs_B0": {}, "vs_B2": {}, "llm_pairs": {}, "mean_rank": None}
    for a in ["B2"] + llm:
        out["vs_B0"][a] = paired([per[s][a]["ate_m"] - per[s]["B0"]["ate_m"] for s in seeds])
    for a in llm:
        d = [per[s][a]["ate_m"] - per[s]["B2"]["ate_m"] for s in seeds]
        out["vs_B2"][a] = dict(paired(d), within_1cm_every_episode=bool(all(abs(x) <= 0.01 for x in d)))
    for i in range(len(llm)):
        for j in range(i + 1, len(llm)):
            out["llm_pairs"]["%s minus %s" % (llm[i], llm[j])] = paired(
                [per[s][llm[i]]["ate_m"] - per[s][llm[j]]["ate_m"] for s in seeds])
    if len(llm) >= 2:
        mat = np.array([[per[s][a]["ate_m"] for a in llm] for s in seeds])
        ranks = np.apply_along_axis(sps.rankdata, 1, mat)
        out["mean_rank"] = {a: float(ranks[:, j].mean()) for j, a in enumerate(llm)}
    return out


# ---------------------------------------------------------------- run behaviour and traces

def behaviour(docs, runs, seeds, procedure="procedure"):
    out = {}
    proc = runs.get(procedure)
    for arm, folders in runs.items():
        rows = [r for s in seeds for r in _rows(folders, s)]
        if not rows:
            continue
        secs = sorted(float(r.get("seconds") or 0.0) for r in rows)
        tools = collections.Counter(c.get("tool") for r in rows for c in r.get("calls") or [])
        agree = tot = 0
        src_same = src_n = 0
        src_diff = collections.Counter()
        if proc and arm != procedure:
            for s in seeds:
                for r, q in zip(_rows(folders, s), _rows(proc, s)):
                    ra, qa = (r.get("report") or {}).get("pose_source"), (q.get("report") or {}).get("pose_source")
                    if ra is not None and qa is not None:
                        src_n += 1
                        src_same += ra == qa
                        if ra != qa:
                            src_diff["%s instead of %s" % (ra, qa)] += 1
                    a = collections.Counter(c["tool"] for c in r.get("calls") or [] if c.get("tool") != "move")
                    b = collections.Counter(c["tool"] for c in q.get("calls") or [] if c.get("tool") != "move")
                    agree += sum((a & b).values())
                    tot += max(sum(a.values()), sum(b.values()))
        out[arm] = {"steps": len(rows), "expected": sum(len(docs[s]["records"]) for s in seeds),
                    "valid": sum(1 for r in rows if (r.get("checks") or {}).get("valid")),
                    "fallbacks": sum(1 for r in rows if r.get("fallback")),
                    "repaired": sum(1 for r in rows if (r.get("checks") or {}).get("repaired_chars")),
                    "errors": sum(1 for r in rows if r.get("error")),
                    "calls_per_step": sum(tools.values()) / len(rows), "tools": dict(tools.most_common()),
                    "tool_name_agreement_with_procedure": (agree / tot) if tot else None,
                    "pose_source_agreement_with_procedure": (src_same / src_n) if src_n else None,
                    "pose_source_steps_compared": src_n, "pose_source_differences": dict(src_diff.most_common()),
                    "mean_s": statistics.fmean(secs), "median_s": statistics.median(secs),
                    "p95_s": secs[max(0, math.ceil(0.95 * len(secs)) - 1)],
                    "cost_usd": sum(float(r.get("cost_usd") or 0.0) for r in rows)}
    return out


def traces(docs, ate, seeds, arms):
    """Per seed and LLM arm: how far the arm's estimate is from B2's at each step (truth-free), where it first parts
    by more than DIVERGE_M, its largest gap; and every arm's error against the logged truth at 25/50/75/100 % of the
    episode."""
    out = {}
    for s in seeds:
        n = len(docs[s]["records"])
        b2 = ate[s]["B2"]["poses"]
        row = {"steps": n, "arms": {}}
        for a in arms:
            if a not in ate[s]:
                continue
            e = ate[s][a]["per_step_m"]
            q = {str(f): e[max(0, math.ceil(f * n / 100) - 1)] for f in (25, 50, 75, 100)}
            d = None
            if a not in ("B0", "B2"):
                gap = [math.hypot(p["x_m"] - b["x_m"], p["y_m"] - b["y_m"]) for p, b in zip(ate[s][a]["poses"], b2)]
                first = next((i for i, x in enumerate(gap) if x > DIVERGE_M), None)
                d = {"first_step_beyond": first, "max_gap_m": max(gap), "max_gap_step": int(np.argmax(gap)),
                     "final_gap_m": gap[-1], "steps_beyond": sum(1 for x in gap if x > DIVERGE_M)}
            row["arms"][a] = {"error_at_pct_m": q, "vs_B2": d}
        out[s] = row
    return out


# ---------------------------------------------------------------- markdown

def _diff_md(rows, display, what):
    lines = ["| %s | n | estimate (cm) | 95 %% interval (cm) | estimator | episodes below / above zero |" % what,
             "| --- | --- | --- | --- | --- | --- |"]
    for name, v in rows:
        lines.append("| %s | %d | %s | %s | %s | %d / %d |" % (name, v["n"], _cm(v["estimate"]), _ci(v["ci95"]),
                                                             v["estimand"], v["n_below"], v["n_above"]))
    return lines


def markdown(res):
    display = lambda a: sa.DISPLAY.get(a, a)  # noqa: E731
    L = ["# Real-log replay: exploratory paired differences and per-step traces (not pre-registered)", "",
         "Set `%s`: %d episodes in the main analysis, %d flagged and kept apart; cm." % (
             res["set"], len(res["main_seeds"]), len(res["flagged_seeds"])), "",
         "**Exploratory, not pre-registered.** The pre-registration reports the real logs descriptively (prereg.md "
         "section 6), the value compared here was chosen after the data, and there is no significance claim from a "
         "handful of episodes (evidence/M5/requirements.md). Each line is a paired difference: the study's estimator "
         "(Hodges-Lehmann with its exact 95 % interval, or the median with its exact interval when the skewness switch "
         "applies) and the episodes below and above zero. No p-values, no multiplicity correction, no verdicts. "
         "H2 (against B1) is not run: B1 needs oracle association, which the real logs do not have.", ""]
    for t in res["tests"]:
        L += ["## %s (n = %d; exploratory, not pre-registered)" % (t["label"], t["n"]), "",
              "Arm - B0. B2 - B0 is the procedure's own gain over dead reckoning; a model that follows the procedure "
              "inherits it, so a model's gain over B0 is the procedure's, not the model's:", ""]
        L += _diff_md([(display(a) + " - B0", v) for a, v in t["vs_B0"].items()], display, "Difference")
        if t["vs_B2"]:
            L += ["", "Model - B2 (what the model adds to or loses against the procedure it was given):", ""]
            L += _diff_md([(display(a) + " - B2", v) for a, v in t["vs_B2"].items()], display, "Difference")
            L += [""] + ["- %s within 1 cm of B2 on every episode: %s" % (
                display(a), "yes" if v["within_1cm_every_episode"] else "no") for a, v in t["vs_B2"].items()]
        if t["llm_pairs"]:
            L += ["", "Between the models (mean rank, 1 = smallest error: %s):" % ", ".join(
                "%s %.2f" % (display(a), r) for a, r in t["mean_rank"].items()), ""]
            L += _diff_md([(" - ".join(display(x) for x in k.split(" minus ")), v) for k, v in t["llm_pairs"].items()],
                          display, "Difference")
        L.append("")
    L += ["## Run behaviour (the main episodes)", "",
          "| Arm | steps | valid | fallbacks | repaired | step errors | calls per step | tool names as the procedure's | mean / median / p95 s per step | cost (US$) |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for a, b in res["behaviour"].items():
        L.append("| %s | %d of %d | %d | %d | %d | %d | %.2f | %s | %.1f / %.1f / %.1f | %.2f |" % (
            display(a), b["steps"], b["expected"], b["valid"], b["fallbacks"], b["repaired"], b["errors"],
            b["calls_per_step"], "" if b["tool_name_agreement_with_procedure"] is None else
            "%.0f %%" % (100 * b["tool_name_agreement_with_procedure"]), b["mean_s"], b["median_s"], b["p95_s"],
            b["cost_usd"]))
    L += ["", "`tool names as the procedure's`: per step, the share of tool calls (by name, `move` left out) the arm "
          "has in common with the coded procedure on the same input; the study's call precision and recall also "
          "match the arguments, which the trimmed rows here do not keep.", "",
          "Pose source as the procedure's (the steps where both reported one; the study's pose-source agreement), and "
          "the arm's differences from the procedure:", ""]
    for a, b in res["behaviour"].items():
        if b.get("pose_source_agreement_with_procedure") is not None:
            L.append("- %s: %.1f %% of %d steps; %s" % (
                display(a), 100 * b["pose_source_agreement_with_procedure"], b["pose_source_steps_compared"],
                "; ".join("%s: %d" % kv for kv in b["pose_source_differences"].items()) or "no difference"))
    L += ["",
          "## Per-step traces", "",
          "Error against the batch's logged (tracked) truth at 25/50/75/100 %% of each episode (tracker-dependent), "
          "and where each LLM arm's estimate first parts from B2's by more than %.0f cm (truth-free):" % (100 * DIVERGE_M),
          ""]
    arms = res["trace_arms"]
    L += ["| Seed | steps | " + " | ".join("%s 25/50/75/100 %%" % display(a) for a in arms) + " | " +
          " | ".join("%s parts from B2 (first step; steps beyond; largest gap)" % display(a) for a in arms
                     if a not in ("B0", "B2")) + " |",
          "| --- | --- | " + " | ".join("---" for _ in arms) + " | " +
          " | ".join("---" for a in arms if a not in ("B0", "B2")) + " |"]
    for s, row in sorted(res["traces"].items(), key=lambda kv: int(kv[0])):
        cells = []
        for a in arms:
            x = row["arms"].get(a)
            cells.append("/".join(_cm(x["error_at_pct_m"][f]) for f in ("25", "50", "75", "100")) if x else "")
        gaps = []
        for a in arms:
            if a in ("B0", "B2"):
                continue
            x = (row["arms"].get(a) or {}).get("vs_B2")
            gaps.append("never" if x and x["first_step_beyond"] is None else
                        ("%d; %d; %s cm at %d" % (x["first_step_beyond"], x["steps_beyond"], _cm(x["max_gap_m"]),
                                                  x["max_gap_step"]) if x else ""))
        L.append("| %s%s | %d | %s | %s |" % (s, " (flagged)" if int(s) in res["flagged_seeds"] else "", row["steps"],
                                             " | ".join(cells), " | ".join(gaps)))
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--obslogs", required=True)
    ap.add_argument("--result", required=True, help="tools/real_replay.py analyze's .json")
    ap.add_argument("--run", action="append", default=[], help="<arm>=<run folder>, repeatable (as for analyze)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    index, docs = rr.load_obslogs(a.obslogs)
    result = json.loads(pathlib.Path(a.result).read_text(encoding="utf-8"))
    runs = {}
    for spec in a.run:
        label, _, folder = spec.partition("=")
        runs.setdefault(label, []).append(folder)
    truths = {int(k): v for k, v in result["truths"].items()}
    seeds = sorted(docs)
    flagged = [s for s in seeds if (truths.get(s) or {}).get("flag")]
    main_seeds = [s for s in seeds if s not in flagged]
    arms = ["B0", "B2"] + [x for x in LLM_ARMS if x in runs]
    complete = [x for x in arms if all((result["errors"].get(x, {}).get(str(s)) or {}).get("complete") for s in main_seeds)]
    ate = ate_all_steps(docs, {k: v for k, v in runs.items() if k in complete}, seeds)
    per_ate = {s: {x: {"ate_m": ate[s][x]["ate_m"]} for x in complete} for s in main_seeds}
    tests = [differences(values(result, "vs_end_circle_m", main_seeds, complete), complete,
                         "Final-position error against the end circle"),
             differences(values(result, "final_m", main_seeds, complete), complete,
                         "Final-position error against the last step's logged truth (tracker-dependent)"),
             differences(values(result, "vs_recomputed_m", main_seeds, complete), complete,
                         "Final-position error against the recomputed truth (tracker-dependent)"),
             differences(per_ate, complete, "ATE over all steps against the logged truth (tracker-dependent)")]
    res = {"schema": "bm.real_replay_stats/2", "exploratory": True, "set": index.get("batch"), "main_seeds": main_seeds,
           "flagged_seeds": flagged, "arms_complete": complete, "tests": tests,
           "behaviour": behaviour(docs, runs, main_seeds),
           "behaviour_flagged": behaviour(docs, runs, flagged) if flagged else None,
           "trace_arms": complete, "traces": {str(s): v for s, v in traces(docs, ate, seeds, complete).items()},
           "ate_per_seed_m": {str(s): {x: ate[s][x]["ate_m"] for x in ate[s]} for s in seeds}}
    md = markdown(res)
    pathlib.Path(a.out + ".json").write_text(json.dumps(res, indent=1, default=float))
    pathlib.Path(a.out + ".md").write_text(md)
    sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
