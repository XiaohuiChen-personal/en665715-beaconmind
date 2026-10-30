#!/usr/bin/env python3
"""Analyse the pilot: metrics per condition, seed and arm (B0, B2, L2), the H1 pilot test, the
judge calibration and selection, the baseline sensitivity sweep, and the report's table, figure and
number macros (generated here, never typed by hand: plan/M5-report.md M5.T4).

Run on the Spark host venv (numpy, scipy, matplotlib):
  ~/.venvs/beaconmind/bin/python tools/pilot_analyze.py --data data/pilot-20261029 \
      --evidence evidence/M4/M4.T11 --report report

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: wrote this analysis.
"""
import argparse
import csv
import json
import math
import pathlib
import statistics
import sys

import numpy as np
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "beaconmind" / "src"))
sys.path.insert(0, str(ROOT / "tools"))
from beaconmind.envs import kinsim_lite as ks  # noqa: E402
from beaconmind.metrics import judge as J  # noqa: E402
from beaconmind.metrics import pilot as pm  # noqa: E402
from pilot_judge import load_rows  # noqa: E402

CONDITIONS = [("nominal", "obslogs", "opus", 0.0), ("drift2", "obslogs-drift02", "opus-drift02", 0.02)]
TAU_POSE_M, TAU_MAP_M = 0.25, 0.30
ALPHA_PLAN = 0.05 / 3
SWEEP = [0.0, 0.005, 0.01, 0.015, 0.02, 0.03, 0.05]


def nearest_rank(v, q):
    s = sorted(v)
    return s[max(0, math.ceil(q / 100 * len(s)) - 1)]


def seed_metrics(doc, rows):
    rows = sorted(rows, key=lambda r: r["step"])
    n = len(rows)
    assert [r["step"] for r in rows] == list(range(n)), "non-contiguous run log"
    recs = doc["records"][:n]
    world = doc["world"]
    ids = [t["id"] for t in world]
    dup = {i for i in ids if ids.count(i) == 2}
    truth = [r["truth"] for r in recs]
    est = {"B0": ks.dead_reckoning(recs), "B2": [r["report"]["pose"] for r in recs],
           "L2": [r["estimate_pose"] for r in rows]}
    out = {"n_steps": n, "episode_steps": len(doc["records"]), "n_tags": len(world)}
    for arm, poses in est.items():
        e = pm.trajectory_errors(poses, truth)
        out[arm] = {k: e[k] for k in ("ate_m", "heading_rmse_deg", "final_pos_m", "final_heading_deg", "max_pos_m")}
        out[arm]["pose_score"] = pm.linear_score(e["ate_m"], TAU_POSE_M)
        out[arm]["per_step_m"] = e["per_step_m"]
    b2_reports = [r["report"] for r in recs]
    for arm, reports, prevs in (("B2", b2_reports, [None] + b2_reports[:-1]),
                                ("L2", [r["next_prev"] for r in rows], [r["prev_report"] for r in rows])):
        tr = pm.LabelTracker()
        res = []
        for rep, prev, rec in zip(reports, prevs, recs):
            res += tr.score_step(rep, prev, rec["raw"]["detections"], dup)
        a_all, a_dup = pm.association_scores(res), pm.association_scores([x for x in res if x[0]])
        final = next((rep for rep in reversed(reports) if rep), {"map": []})
        ms = pm.map_scores_c10(final.get("map"), world)
        out[arm].update(ms)
        out[arm].update(assoc_precision=a_all["precision"], assoc_recall=a_all["recall"],
                        assoc_precision_dup=a_dup["precision"], assoc_recall_dup=a_dup["recall"],
                        assoc_counts=a_all, assoc_counts_dup=a_dup)
        out[arm]["map_score"] = pm.linear_score(ms["map_rmse_m"], TAU_MAP_M) if ms["map_rmse_m"] is not None else None
    tp = fp = fn = 0
    skipped = agree_src = agree_assoc = compared = 0
    for r in rows:
        gold = pm.gold_calls(r["observation"], r["prev_report"])
        if gold is None:
            skipped += 1
            continue
        a, b, c = pm.match_calls(r["calls"], gold)
        tp, fp, fn = tp + a, fp + b, fn + c
        if r["checks"]["valid"]:
            g = ks.estimate_step(r["observation"], r["prev_report"])
            compared += 1
            agree_src += r["report"].get("pose_source") == g["pose_source"]
            # a rejected detection's label is not part of the decision (the procedure leaves it empty
            # under prior_kept; the agent tends to name the nearest candidate)
            key = lambda d_, res, lab: (d_, res, lab if res != "rejected" else None)
            want = sorted(key(a_["det"], a_["result"], a_["beacon"]) for a_, _ in g["assoc"])
            got = sorted(key(x.get("det"), x.get("result"), x.get("beacon")) for x in r["report"].get("associations") or [] if isinstance(x, dict))
            agree_assoc += want == got
    l2 = out["L2"]
    l2.update(pm.prf(tp, fp, fn))
    l2["gold_skipped"] = skipped
    l2["non_int_det_calls"] = sum(1 for r in rows for c in r["calls"]
                                  if "det" in (c.get("args") or {}) and not isinstance(c["args"]["det"], int))
    l2["budget_aborts"] = sum(1 for r in rows if r["error"] == "budget cap reached")
    l2["pose_source_agree"] = agree_src / compared if compared else None
    l2["assoc_agree"] = agree_assoc / compared if compared else None
    l2["valid_rate"] = sum(r["checks"]["valid"] for r in rows) / n
    l2["fallbacks"] = sum(r["fallback"] for r in rows)
    l2["decision_none_rate"] = sum(r["checks"]["decision_none"] for r in rows) / n
    l2["estops"] = sum(1 for r in rows for c in r["calls"] if c["tool"] == "emergency_stop")
    l2["move_calls"] = sum(1 for r in rows for c in r["calls"] if c["tool"] == "move")
    secs = [r["seconds"] for r in rows]
    l2["latency_p50_s"], l2["latency_p95_s"], l2["latency_max_s"] = nearest_rank(secs, 50), nearest_rank(secs, 95), max(secs)
    l2["tool_calls_per_step"] = sum(len(r["calls"]) for r in rows) / n
    l2["turns_per_step"] = sum(len(r["turns"]) for r in rows) / n
    l2["input_tokens_per_step"] = sum(t["usage"]["input_tokens"] + t["usage"]["cache_creation_input_tokens"]
                                      + t["usage"]["cache_read_input_tokens"] for r in rows for t in r["turns"]) / n
    l2["cache_read_share"] = (sum(t["usage"]["cache_read_input_tokens"] for r in rows for t in r["turns"])
                              / max(1, sum(t["usage"]["input_tokens"] + t["usage"]["cache_creation_input_tokens"]
                                           + t["usage"]["cache_read_input_tokens"] for r in rows for t in r["turns"])))
    l2["output_tokens_per_step"] = sum(t["usage"]["output_tokens"] for r in rows for t in r["turns"]) / n
    l2["cost_usd"] = sum(r["cost_usd"] for r in rows)
    l2["cost_per_step_usd"] = l2["cost_usd"] / n
    l2["errors"] = sum(1 for r in rows if r["error"])
    return out


def unmatched_calls(rows):
    """The agent's calls that match no gold call, by tool and reason."""
    out, total = {}, 0
    for r in rows:
        gold = pm.gold_calls(r["observation"], r["prev_report"]) or []
        used = [False] * len(gold)
        for c in r["calls"]:
            total += 1
            hit = next((i for i, g in enumerate(gold) if not used[i] and pm.call_matches(c, g)), None)
            if hit is not None:
                used[hit] = True
                continue
            err = isinstance(c["result"], dict) and c["result"].get("status") == "error"
            why = ("refused" if err or c["tool"] == "move" else
                   "empty_candidates" if c["tool"] == "gate_detection" and not (c.get("args") or {}).get("candidates") else "other")
            key = "%s:%s" % (c["tool"], why)
            out[key] = out.get(key, 0) + 1
    return {"total_calls": total, "unmatched": dict(sorted(out.items(), key=lambda kv: -kv[1]))}


def rank_biserial(d):
    d = [x for x in d if x != 0]
    if not d:
        return None
    ranks = stats.rankdata([abs(x) for x in d])
    wp = sum(r for r, x in zip(ranks, d) if x > 0)
    wm = sum(r for r, x in zip(ranks, d) if x < 0)
    return (wp - wm) / (len(d) * (len(d) + 1) / 2)


def h1_stats(a, b, alternative):
    """Paired per-seed differences a - b: exact Wilcoxon signed-rank, rank-biserial r, mean with a
    10,000-resample percentile bootstrap 95 % CI (seed 12345), Cohen's d_z."""
    d = np.array(a) - np.array(b)
    rng = np.random.default_rng(12345)
    boot = rng.choice(d, size=(10000, len(d)), replace=True).mean(axis=1)
    w = stats.wilcoxon(d, alternative=alternative, method="exact") if np.any(d != 0) else None
    sd = d.std(ddof=1) if len(d) > 1 else float("nan")
    return {"d": d.tolist(), "mean": float(d.mean()), "median": float(np.median(d)),
            "ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
            "wilcoxon_stat": float(w.statistic) if w else None, "p": float(w.pvalue) if w else None,
            "alternative": alternative, "rank_biserial": rank_biserial(d.tolist()),
            "dz": float(d.mean() / sd) if sd and sd > 0 else None, "n_negative": int((d < 0).sum())}


def power_curve(d, ns=(5, 10, 15, 20, 30, 40), sims=4000, alpha=ALPHA_PLAN):
    rng = np.random.default_rng(4242)
    out = {}
    for n in ns:
        hits = 0
        for _ in range(sims):
            s = rng.choice(d, size=n, replace=True)
            if np.all(s == 0):
                continue
            hits += stats.wilcoxon(s, alternative="less", method="auto").pvalue < alpha
        out[n] = hits / sims
    return out


def power_normal(mean, sd, ns=(5, 10, 15, 20, 30, 40), sims=4000, alpha=ALPHA_PLAN):
    """Power of the one-sided Wilcoxon test when per-seed differences are Normal(mean, sd)."""
    rng = np.random.default_rng(4243)
    return {n: float(np.mean([stats.wilcoxon(rng.normal(mean, sd, n), alternative="less", method="auto").pvalue < alpha
                              for _ in range(sims)])) for n in ns}


# ---------------------------------------------------------------- judge calibration

def judge_analysis(jdir):
    items = {json.loads(l)["id"]: json.loads(l) for l in (jdir / "items.jsonl").read_text().splitlines() if l.strip()}
    res = {}
    for j in ("gemma", "sol"):
        p = jdir / ("%s.jsonl" % j)
        if not p.exists():
            continue
        recs = {}
        for l in p.read_text().splitlines():
            if l.strip():
                r = json.loads(l)
                if r.get("levels"):
                    recs[r["id"]] = r
        res[j] = recs
    out = {"n_items": {s: sum(1 for it in items.values() if it["set"] == s) for s in ("real", "kl", "fab", "rep", "rev", "pad")}}
    for j, recs in res.items():
        a = {"errors": sum(1 for l in (jdir / ("%s.jsonl" % j)).read_text().splitlines() if l.strip() and json.loads(l).get("error"))}
        kl = [it for it in items.values() if it["set"] == "kl" and it.get("split") == "test" and it["id"] in recs]
        a["kl_n"] = len(kl)
        for k in J.JUDGED:
            exp = [it["expected"][k] for it in kl]
            got = [recs[it["id"]]["levels"][k] for it in kl]
            a["kl_acc_" + k] = sum(x == y for x, y in zip(exp, got)) / len(kl) if kl else None
            a["kl_kappa_" + k] = J.weighted_kappa(exp, got)
        es = [J.score(it["expected"], J.concise_level(it["note"])) for it in kl]
        gs = [J.score(recs[it["id"]]["levels"], J.concise_level(it["note"])) for it in kl]
        a["kl_spearman"] = float(stats.spearmanr(es, gs).statistic) if len(kl) > 2 else None
        a["kl_bias"] = sum(g - e for g, e in zip(gs, es)) / len(kl) if kl else None
        a["kl_mad"] = sum(abs(g - e) for g, e in zip(gs, es)) / len(kl) if kl else None
        by_kind = {}
        for it in kl:
            by_kind.setdefault(it["kind"], []).append(recs[it["id"]]["levels"] == {k: it["expected"][k] for k in J.JUDGED})
        a["kl_exact_by_kind"] = {k: sum(v) / len(v) for k, v in sorted(by_kind.items())}
        fab = [it for it in items.values() if it["set"] == "fab" and it["id"] in recs]
        a["fab_n"] = len(fab)
        a["fab_detect"] = sum(recs[it["id"]]["levels"]["faithful"] == 0 for it in fab) / len(fab) if fab else None
        for s in ("rep", "rev", "pad"):
            pairs = [(recs[it["id"]]["levels"], recs[it["base"]]["levels"]) for it in items.values()
                     if it["set"] == s and it["id"] in recs and it["base"] in recs]
            a["inv_" + s] = (sum(x[k] == y[k] for x, y in pairs for k in J.JUDGED) / (3 * len(pairs))) if pairs else None
            a["inv_%s_n" % s] = len(pairs)
        crit_ok = all((a["kl_kappa_" + k] or 0) >= J.THRESHOLDS["kappa"] and (a["kl_acc_" + k] or 0) >= J.THRESHOLDS["accuracy"]
                      for k in J.JUDGED)
        a["eligible"] = bool(crit_ok and (a["fab_detect"] or 0) >= J.THRESHOLDS["fabrication_detect"]
                             and all((a["inv_" + s] or 0) >= J.THRESHOLDS["invariance"] for s in ("rep", "rev", "pad")))
        a["kl_mean_acc"] = sum(a["kl_acc_" + k] for k in J.JUDGED) / 3 if kl else 0
        real = [it for it in items.values() if it["set"] == "real" and it["id"] in recs]
        a["real_n"] = len(real)
        # Module 9's cheapest check: a beacon label in the note that the report never mentions is a
        # code-detectable faithfulness fault; compare with the judge's faithful level.
        flagged = [it for it in real if set(it.get("note_labels", [])) - set(it.get("known_labels", []))]
        a["code_flagged_n"] = len(flagged)
        a["code_flagged_judged_below_2"] = (sum(recs[it["id"]]["levels"]["faithful"] < 2 for it in flagged) / len(flagged)
                                            if flagged else None)
        a["real_faithful_mean"] = sum(recs[it["id"]]["levels"]["faithful"] for it in real) / len(real) if real else None
        out[j] = a
    # inter-judge agreement on real notes
    common = [i for i, it in items.items() if it["set"] == "real" and i in res.get("gemma", {}) and i in res.get("sol", {})]
    if len(common) >= 3:
        out["inter_judge_n"] = len(common)
        for k in J.JUDGED:
            out["inter_kappa_" + k] = J.weighted_kappa([res["gemma"][i]["levels"][k] for i in common],
                                                       [res["sol"][i]["levels"][k] for i in common])
            out["inter_exact_" + k] = sum(res["gemma"][i]["levels"][k] == res["sol"][i]["levels"][k] for i in common) / len(common)
        sg = [J.score(res["gemma"][i]["levels"], J.concise_level(items[i]["note"])) for i in common]
        ss = [J.score(res["sol"][i]["levels"], J.concise_level(items[i]["note"])) for i in common]
        out["inter_spearman"] = float(stats.spearmanr(sg, ss).statistic)
    elig = [j for j in res if out[j]["eligible"]]
    if elig:
        best = max(out[j]["kl_mean_acc"] for j in elig)
        top = [j for j in elig if abs(out[j]["kl_mean_acc"] - best) < 1e-12]
        out["selected"] = "gemma" if "gemma" in top else top[0]
    else:
        out["selected"] = None
    return out, items, res


def rubric_by_seed(items, recs, cond):
    rows = {}
    for i, it in items.items():
        if it["set"] != "real" or it.get("cond") != cond or i not in recs:
            continue
        lv = recs[i]["levels"]
        c = J.concise_level(it["note"])
        rows.setdefault(it["seed"], []).append((J.score(lv, c), lv, c))
    return {s: {"rubric": sum(x[0] for x in v) / len(v), "gate_fail": sum(1 for x in v if x[1]["faithful"] == 0),
                "n": len(v), **{"mean_" + k: sum(x[1][k] for x in v) / len(v) for k in J.JUDGED},
                "mean_concise": sum(x[2] for x in v) / len(v)} for s, v in rows.items()}


# ---------------------------------------------------------------- sweep, figure, tables

def sweep():
    out = []
    for bias in SWEEP:
        b0, b2, fails, why = [], [], 0, {}
        for seed in range(1000, 1100):
            try:
                ep = ks.run_episode(seed, odo_bias=bias)
            except NotImplementedError as exc:
                fails += 1
                why[str(exc)] = why.get(str(exc), 0) + 1
                continue
            recs = ep["records"]
            truth = [r["truth"] for r in recs]
            b0.append(pm.trajectory_errors(ks.dead_reckoning(recs), truth)["ate_m"])
            b2.append(pm.trajectory_errors([r["report"]["pose"] for r in recs], truth)["ate_m"])
        q = lambda v, p: float(np.percentile(v, p))
        out.append({"bias": bias, "n": len(b0), "failures": fails, "failure_kinds": why,
                    "b0_med": q(b0, 50), "b0_q1": q(b0, 25), "b0_q3": q(b0, 75),
                    "b2_med": q(b2, 50), "b2_q1": q(b2, 25), "b2_q3": q(b2, 75),
                    "b2_better": sum(1 for x, y in zip(b0, b2) if y < x)})
    return out


def figure(per, sw, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 8, "font.family": "serif", "axes.linewidth": 0.6})
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 2.5), gridspec_kw={"width_ratios": [1.15, 1]})
    arms = ["B0", "B2", "L2"]
    colors = {"B0": "#7f7f7f", "B2": "#1f77b4", "L2": "#d62728"}
    for ci, (cond, label) in enumerate((("nominal", "No drift"), ("drift2", "2 % drift"))):
        seeds = sorted(per[cond])
        for s in seeds:
            ys = [per[cond][s][a]["ate_m"] * 100 for a in arms]
            xs = [ci * 4 + k for k in range(3)]
            ax1.plot(xs, ys, color="#bbbbbb", lw=0.6, zorder=1)
            for x, y, a in zip(xs, ys, arms):
                ax1.scatter(x, y, s=12, color=colors[a], zorder=2)
        ax1.text(ci * 4 + 1, -0.12, label, ha="center", va="top", transform=ax1.get_xaxis_transform())
    ax1.set_xticks([0, 1, 2, 4, 5, 6])
    ax1.set_xticklabels(arms * 2)
    ax1.set_ylabel("ATE-RMSE (cm)")
    ax1.set_title("(a) Pilot: per-seed trajectory error", fontsize=8)
    ax1.grid(axis="y", lw=0.3, alpha=0.6)
    sw = [r for r in sw if r["bias"] <= 0.03]          # the 5 % level is in the JSON and the text
    b = [r["bias"] * 100 for r in sw]
    for arm, key in (("B0", "b0"), ("B2", "b2")):
        ax2.plot(b, [r[key + "_med"] * 100 for r in sw], marker="o", ms=3, color=colors[arm],
                 label=arm + " (median of 100 seeds per level)")
        ax2.fill_between(b, [r[key + "_q1"] * 100 for r in sw], [r[key + "_q3"] * 100 for r in sw], color=colors[arm], alpha=0.15, lw=0)
    for cond, x in (("nominal", 0.0), ("drift2", 2.0)):
        med = statistics.median(per[cond][s]["L2"]["ate_m"] * 100 for s in per[cond])
        ax2.scatter([x], [med], marker="*", s=60, color=colors["L2"], zorder=3, label="L2 pilot (5 seeds, median)" if cond == "nominal" else None)
    ax2.set_xlabel("Systematic odometry over-read (%)")
    ax2.set_ylabel("ATE-RMSE (cm)")
    ax2.set_title("(b) Baseline sensitivity to odometry drift", fontsize=8)
    ax2.legend(frameon=False, fontsize=7, loc="upper left")
    ax2.grid(lw=0.3, alpha=0.6)
    fig.tight_layout()
    fig.savefig(path.with_suffix(".pdf"))
    fig.savefig(path.with_suffix(".png"), dpi=200)


def fmt(v, scale=1.0, nd=1):
    """Fixed decimals; a value that rounds to zero prints as 0, and a negative one with a real minus sign."""
    if v is None:
        return "--"
    s = "%.*f" % (nd, v * scale)
    if float(s) == 0:
        return "%.*f" % (nd, 0.0)
    return "$-$" + s[1:] if s.startswith("-") else s


def median_range(vals, scale=1.0, nd=1):
    vals = [v for v in vals if v is not None]
    if not vals:
        return "--"
    return "%s (%s--%s)" % (fmt(statistics.median(vals), scale, nd), fmt(min(vals), scale, nd), fmt(max(vals), scale, nd))


def table_pilot(per, rub, path):
    rows = [("ATE-RMSE (cm)", "ate_m", 100, 1, ("B0", "B2", "L2")),
            ("Final position error (cm)", "final_pos_m", 100, 1, ("B0", "B2", "L2")),
            ("Heading RMSE (deg)", "heading_rmse_deg", 1, 1, ("B0", "B2", "L2")),
            ("Pose score, $\\tau=0.25$ m (0--1)", "pose_score", 1, 2, ("B0", "B2", "L2")),
            ("Map RMSE, correct entries (cm)", "map_rmse_m", 100, 1, ("B2", "L2")),
            ("Map ID precision / phantoms (0--1)", "map_precision", 1, 2, ("B2", "L2")),
            ("Map recall, tags mapped (0--1)", "map_recall", 1, 2, ("B2", "L2")),
            ("Association precision (0--1)", "assoc_precision", 1, 2, ("B2", "L2")),
            ("\\quad duplicated IDs only (0--1)", "assoc_precision_dup", 1, 2, ("B2", "L2")),
            ("Association recall (0--1)", "assoc_recall", 1, 2, ("B2", "L2")),
            ("Tool-call F1 (0--1)", "f1", 1, 2, ("L2",)),
            ("Pose source as procedure (0--1)", "pose_source_agree", 1, 2, ("L2",)),
            ("Valid reports (0--1)", "valid_rate", 1, 2, ("L2",)),
            ("Latency per step, p95 (s)", "latency_p95_s", 1, 1, ("L2",)),
            ("Cost per step (US\\$)", "cost_per_step_usd", 1, 3, ("L2",))]
    lines = ["% Generated by course-project/tools/pilot_analyze.py; do not edit by hand.",
             "\\begin{table*}[t]", "\\caption{Pilot Results per Arm (median and range over 5 seeds; 0--1 rows are scores, higher is better)}",
             "\\label{tab:pilot}", "\\centering", "\\scriptsize", "\\renewcommand{\\arraystretch}{1.1}",
             "\\setlength{\\tabcolsep}{3pt}", "\\begin{tabular}{l ccc ccc}", "\\hline",
             " & \\multicolumn{3}{c}{No odometry drift} & \\multicolumn{3}{c}{2\\,\\% odometry over-read} \\\\",
             "Metric & B0 & B2 & L2 & B0 & B2 & L2 \\\\", "\\hline"]
    for label, key, sc, nd, arms in rows:
        cells = []
        for cond in ("nominal", "drift2"):
            for a in ("B0", "B2", "L2"):
                cells.append(median_range([per[cond][s][a].get(key) for s in per[cond]], sc, nd) if a in arms else "")
        lines.append("%s & %s \\\\" % (label, " & ".join(cells)))
    cells = []
    for cond in ("nominal", "drift2"):
        cells += ["", "", median_range([rub[cond][s]["rubric"] for s in rub[cond]], 1, 2) if rub.get(cond) else "--"]
    lines.append("Note rubric score (0--1) & %s \\\\" % " & ".join(cells))
    lines += ["\\hline", "\\end{tabular}", "\\end{table*}"]
    path.write_text("\n".join(lines) + "\n")


def table_judge(cal, path):
    names = {"gemma": "Gemma 4", "sol": "GPT-6.1 Sol"}
    js = [j for j in ("gemma", "sol") if j in cal]
    lines = ["% Generated by course-project/tools/pilot_analyze.py; do not edit by hand.",
             "\\begin{table}[t]", "\\caption{Automated Calibration of the Two Note Judges (Pilot)}", "\\label{tab:judge}", "\\centering",
             "\\scriptsize", "\\renewcommand{\\arraystretch}{1.1}", "\\setlength{\\tabcolsep}{4pt}",
             "\\begin{tabular}{l %s}" % ("c" * len(js)), "\\hline",
             "Check (threshold) & %s \\\\" % " & ".join(names[j] for j in js), "\\hline"]
    def row(label, key, nd=2):
        lines.append("%s & %s \\\\" % (label, " & ".join(fmt(cal[j].get(key), 1, nd) for j in js)))
    lines.append("\\multicolumn{%d}{l}{\\textit{Known-label notes, calibration seeds 1001--1004 (n = %s)}} \\\\" % (len(js) + 1, cal[js[0]]["kl_n"]))
    for k, lab in (("faithful", "Faithful"), ("coverage", "Coverage"), ("uncertainty", "Uncertainty")):
        row("\\quad %s: accuracy ($\\geq$0.7)" % lab, "kl_acc_" + k)
        row("\\quad %s: weighted $\\kappa$ ($\\geq$0.6)" % lab, "kl_kappa_" + k)
    row("\\quad Score: Spearman $\\rho$ with the key", "kl_spearman")
    row("\\quad Score: bias, judge $-$ key", "kl_bias")
    lines.append("\\multicolumn{%d}{l}{\\textit{Real notes (n = %s per check)}} \\\\" % (len(js) + 1, cal[js[0]]["fab_n"]))
    row("\\quad False claim caught ($\\geq$0.8)", "fab_detect")
    row("\\quad Unchanged: repeat run ($\\geq$0.9)", "inv_rep")
    row("\\quad Unchanged: anchors reversed ($\\geq$0.9)", "inv_rev")
    row("\\quad Unchanged: padding added ($\\geq$0.9)", "inv_pad")
    lines.append("Eligible under the fixed rule & %s \\\\" % " & ".join("yes" if cal[j]["eligible"] else "no" for j in js))
    lines += ["\\hline", "\\end{tabular}", "\\end{table}"]
    path.write_text("\n".join(lines) + "\n")


def macros(summary, path):
    out = ["% Generated by course-project/tools/pilot_analyze.py; do not edit by hand."]
    def m(name, val):
        out.append("\\newcommand{\\%s}{%s}" % (name, val))
    for cond, tag in (("nominal", "Nom"), ("drift2", "Drift")):
        per = summary["per_seed"][cond]
        for arm in ("B0", "B2", "L2"):
            m("ate%s%s" % (arm.replace("0", "Zero").replace("2", "Two"), tag),
              fmt(statistics.median(per[s][arm]["ate_m"] for s in per), 100, 1))
        h = summary["h1"][cond]
        m("hOneMean%s" % tag, fmt(h["mean"], 100, 1))
        m("hOneLo%s" % tag, fmt(h["ci95"][0], 100, 1))
        m("hOneHi%s" % tag, fmt(h["ci95"][1], 100, 1))
        m("hOneP%s" % tag, fmt(h["p"], 1, 3))
        m("hOneR%s" % tag, fmt(h["rank_biserial"], 1, 2))
        m("hOneNeg%s" % tag, str(h["n_negative"]))
        m("fOne%s" % tag, fmt(statistics.median(per[s]["L2"]["f1"] for s in per), 1, 2))
        m("steps%s" % tag, str(sum(per[s]["n_steps"] for s in per)))
        m("cost%s" % tag, fmt(sum(per[s]["L2"]["cost_usd"] for s in per), 1, 2))
        m("lat%s" % tag, fmt(max(per[s]["L2"]["latency_p95_s"] for s in per), 1, 1))
        m("sd%s" % tag, fmt(statistics.stdev(h["d"]), 100, 1))
        m("moves%s" % tag, str(sum(per[s]["L2"]["move_calls"] for s in per)))
        m("srcAgree%s" % tag, fmt(min(per[s]["L2"]["pose_source_agree"] for s in per), 1, 2))
        m("assocAgree%s" % tag, fmt(min(per[s]["L2"]["assoc_agree"] for s in per), 1, 2))
        m("recall%s" % tag, fmt(min(per[s]["L2"]["recall"] for s in per), 1, 2))
        m("prec%s" % tag, fmt(statistics.median(per[s]["L2"]["precision"] for s in per), 1, 2))
        m("lTwoBTwo%s" % tag, fmt(max(abs(x) for x in summary["l2_vs_b2"][cond]["d"]), 100, 1))
        pw = summary["power_h1"][cond]
        for key, nm in (("normal_pilot_mean", "PowObs"), ("normal_sesoi", "PowSesoi")):
            for n in (10, 30):
                m("%s%s%s" % (nm, {10: "Ten", 30: "Thirty"}[n], tag), fmt(pw[key][n], 1, 2))
        m("sdLo%s" % tag, fmt(pw["sd_ci95"][0], 100, 1))
        m("sdHi%s" % tag, fmt(pw["sd_ci95"][1], 100, 1))
        m("PowSesoiSdHi%s" % tag, fmt(pw["normal_sesoi_sd_hi"][30], 1, 2))
    uc = summary["unmatched_calls"]
    tot = {k: sum(uc[c]["unmatched"].get(k, 0) for c in uc) for k in
           ("fix_pose:refused", "gate_detection:empty_candidates", "exploration_summary:other", "move:refused")}
    m("callsTotal", "{:,}".format(sum(uc[c]["total_calls"] for c in uc)))
    m("callsUnmatched", str(sum(sum(uc[c]["unmatched"].values()) for c in uc)))
    m("fpFixRefused", str(tot["fix_pose:refused"]))
    m("fpGateEmpty", str(tot["gate_detection:empty_candidates"]))
    m("fpExplore", str(tot["exploration_summary:other"]))
    m("fpMove", str(tot["move:refused"]))
    m("fpOther", str(sum(sum(uc[c]["unmatched"].values()) for c in uc) - sum(tot.values())))
    per_n = summary["per_seed"]["nominal"]
    m("inTokNom", "{:,}".format(round(statistics.mean(per_n[s]["L2"]["input_tokens_per_step"] for s in per_n))))
    sel = summary["judge"].get("selected") if summary.get("judge") else None
    if sel:
        cal = summary["judge"]
        m("judgeSelected", {"gemma": "Gemma~4 26B", "sol": "GPT-6.1 Sol"}[sel])
        for j, nm in (("gemma", "Gemma"), ("sol", "Sol")):
            if j in cal:
                m("fab%s" % nm, fmt(cal[j]["fab_detect"], 1, 2))
                m("klMean%s" % nm, fmt(cal[j]["kl_mean_acc"], 1, 2))
                m("klN%s" % nm, str(cal[j]["kl_n"]))
                m("codeFlag%s" % nm, str(cal[j]["code_flagged_n"]))
        for k, nm in (("faithful", "Faith"), ("coverage", "Cover"), ("uncertainty", "Unc")):
            if "inter_kappa_" + k in cal:
                m("inter%s" % nm, fmt(cal["inter_kappa_" + k], 1, 2))
                m("interExact%s" % nm, fmt(cal["inter_exact_" + k], 1, 2))
            for j, jn in (("gemma", "Gemma"), ("sol", "Sol")):
                if j in cal:
                    m("klKappa%s%s" % (nm, jn), fmt(cal[j]["kl_kappa_" + k], 1, 2))
        if "inter_spearman" in cal:
            m("interRho", fmt(cal["inter_spearman"], 1, 2))
            m("interN", str(cal["inter_judge_n"]))
        rub = summary.get("rubric", {})
        for cond, tag in (("nominal", "Nom"), ("drift2", "Drift")):
            if rub.get(cond):
                v = list(rub[cond].values())
                m("rubric%s" % tag, fmt(statistics.median(x["rubric"] for x in v), 1, 2))
                m("gate%s" % tag, str(sum(x["gate_fail"] for x in v)))
                m("notes%s" % tag, str(sum(x["n"] for x in v)))
                for k, nm in (("faithful", "Faith"), ("coverage", "Cover"), ("uncertainty", "Unc"), ("concise", "Conc")):
                    m("mean%s%s" % (nm, tag), fmt(sum(x["mean_" + k] * x["n"] for x in v) / sum(x["n"] for x in v), 1, 2))
    ev = summary.get("judge_evidence_versions") or {}
    for k, nm in (("sol_faithful0", "vOneFaithZero"), ("sol_real_n", "vOneN"), ("sol_v2_faithful0", "vTwoFaithZero"),
                  ("sol_v2_faithful1", "vTwoFaithOne"), ("sol_faithful1", "vOneFaithOne")):
        if k in ev:
            m(nm, str(ev[k]))
    if ev.get("gemma_kl_kappa_coverage") is not None:
        m("vOneGemmaCoverKappa", fmt(ev["gemma_kl_kappa_coverage"], 1, 2))
    for k, nm in (("judge_cost_v1", "judgeCostVOne"), ("judge_cost_v2", "judgeCostVTwo")):
        if k in ev:
            m(nm, fmt(ev[k], 1, 2))
    for k, nm in (("gemma_real_n", "gemmaRealN"), ("gemma_real_drift_n", "gemmaRealDriftN")):
        if k in ev:
            m(nm, str(ev[k]))
    phantoms = {c: sum(summary["per_seed"][c][s]["L2"]["phantoms"] for s in summary["per_seed"][c]) for c in summary["per_seed"]}
    m("phantomsDrift", str(phantoms["drift2"]))
    m("phantomsNom", str(phantoms["nominal"]))
    sw = {round(r["bias"], 3): r for r in summary.get("sweep", [])}
    for b, nm in ((0.01, "One"), (0.02, "Two"), (0.03, "Three"), (0.05, "Five")):
        if b in sw:
            m("sweepFail%s" % nm, str(sw[b]["failures"]))
            m("sweepWin%s" % nm, str(sw[b]["b2_better"]))
            m("sweepN%s" % nm, str(sw[b]["n"]))
    path.write_text("\n".join(out) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--no-sweep", action="store_true")
    ap.add_argument("--judge-dir", default="judge-v2")
    ap.add_argument("--judge-v1", default="judge", help="earlier judge run with evidence v1, summarized for comparison")
    args = ap.parse_args()
    data, ev, rep = pathlib.Path(args.data), pathlib.Path(args.evidence), pathlib.Path(args.report)
    ev.mkdir(parents=True, exist_ok=True)
    (rep / "figures").mkdir(parents=True, exist_ok=True)
    per, h1, h1_b2, power, extra_calls = {}, {}, {}, {}, {}
    for cond, obs_dir, run_dir, bias in CONDITIONS:
        per[cond] = {}
        rows = load_rows(data / run_dir)
        extra_calls[cond] = unmatched_calls(rows)
        for seed in sorted({r["seed"] for r in rows}):
            doc = json.loads((data / obs_dir / ("seed_%d.json" % seed)).read_text())
            per[cond][seed] = seed_metrics(doc, [r for r in rows if r["seed"] == seed])
        seeds = sorted(per[cond])
        l2 = [per[cond][s]["L2"]["ate_m"] for s in seeds]
        h1[cond] = h1_stats(l2, [per[cond][s]["B0"]["ate_m"] for s in seeds], "less")
        h1_b2[cond] = h1_stats(l2, [per[cond][s]["B2"]["ate_m"] for s in seeds], "two-sided")
        d = np.array(h1[cond]["d"])
        sd = float(d.std(ddof=1))
        sd_hi = sd * math.sqrt((len(d) - 1) / stats.chi2.ppf(0.025, len(d) - 1))   # upper end of the 95 % CI of the SD
        sd_lo = sd * math.sqrt((len(d) - 1) / stats.chi2.ppf(0.975, len(d) - 1))
        power[cond] = {"resample": power_curve(d),
                       "normal_pilot_mean": power_normal(float(d.mean()), sd),
                       "normal_sesoi": power_normal(-0.03, sd),
                       "sd_ci95": [sd_lo, sd_hi],
                       "normal_sesoi_sd_hi": power_normal(-0.03, sd_hi, ns=(30,))}
    jdir = data / args.judge_dir
    cal, items, recs = judge_analysis(jdir) if (jdir / "items.jsonl").exists() else ({}, {}, {})
    sel = cal.get("selected")
    rub = {c: rubric_by_seed(items, recs[sel], c) for c, *_ in CONDITIONS} if sel else {}
    v1 = {}
    if args.judge_v1 and (data / args.judge_v1 / "items.jsonl").exists():
        cal1, items1, recs1 = judge_analysis(data / args.judge_v1)
        if "sol" in recs1:
            real1 = [i for i, it in items1.items() if it["set"] == "real" and i in recs1["sol"]]
            v1 = {"sol_real_n": len(real1),
                  "sol_faithful0": sum(recs1["sol"][i]["levels"]["faithful"] == 0 for i in real1),
                  "sol_faithful1": sum(recs1["sol"][i]["levels"]["faithful"] == 1 for i in real1),
                  "sol_kl_mean_acc": cal1.get("sol", {}).get("kl_mean_acc"),
                  "gemma_kl_kappa_coverage": cal1.get("gemma", {}).get("kl_kappa_coverage")}
    for name, d_ in (("judge_cost_v1", args.judge_v1), ("judge_cost_v2", args.judge_dir)):
        p = data / d_ / "sol.jsonl" if d_ else None
        if p and p.exists():
            v1[name] = sum((json.loads(l).get("cost_usd") or 0.0) for l in p.read_text().splitlines() if l.strip())
    if "gemma" in recs:
        v1["gemma_real_n"] = sum(1 for i, it in items.items() if it["set"] == "real" and i in recs["gemma"])
        v1["gemma_real_drift_n"] = sum(1 for i, it in items.items() if it["set"] == "real" and it.get("cond") == "drift2"
                                       and i in recs["gemma"])
    if sel and "sol" in recs:
        real2 = [i for i, it in items.items() if it["set"] == "real" and i in recs["sol"]]
        v1.update(sol_v2_real_n=len(real2), sol_v2_faithful0=sum(recs["sol"][i]["levels"]["faithful"] == 0 for i in real2),
                  sol_v2_faithful1=sum(recs["sol"][i]["levels"]["faithful"] == 1 for i in real2))
    sw = [] if args.no_sweep else sweep()
    summary = {"per_seed": {c: {s: {k: (v if k not in ("B0", "B2", "L2") else {kk: vv for kk, vv in v.items() if kk != "per_step_m"})
                                    for k, v in m_.items()} for s, m_ in per[c].items()} for c in per},
               "h1": h1, "l2_vs_b2": h1_b2, "power_h1": power, "judge": cal, "rubric": rub, "sweep": sw,
               "unmatched_calls": extra_calls, "judge_evidence_versions": v1, "judge_dir": args.judge_dir,
               "tau_pose_m": TAU_POSE_M, "tau_map_m": TAU_MAP_M}
    (ev / "pilot_summary.json").write_text(json.dumps(summary, indent=1, default=float))
    with open(ev / "pilot_per_seed.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["condition", "seed", "arm", "steps", "ate_m", "final_pos_m", "heading_rmse_deg", "map_rmse_m",
                    "map_precision", "map_recall", "assoc_precision", "assoc_precision_dup", "assoc_recall", "f1",
                    "valid_rate", "latency_p95_s", "cost_usd"])
        for c in per:
            for s in sorted(per[c]):
                for a in ("B0", "B2", "L2"):
                    x = per[c][s][a]
                    w.writerow([c, s, a, per[c][s]["n_steps"], x["ate_m"], x["final_pos_m"], x["heading_rmse_deg"],
                                x.get("map_rmse_m"), x.get("map_precision"), x.get("map_recall"), x.get("assoc_precision"),
                                x.get("assoc_precision_dup"), x.get("assoc_recall"), x.get("f1"),
                                x.get("valid_rate"), x.get("latency_p95_s"), x.get("cost_usd")])
    if sw:
        figure(per, sw, rep / "figures" / "fig_pilot")
    table_pilot(per, rub, rep / "tab_pilot.tex")
    if cal:
        table_judge(cal, rep / "tab_judge.tex")
    macros(summary, rep / "pilot_macros.tex")
    print(json.dumps({"h1": {c: {k: h1[c][k] for k in ("mean", "ci95", "p", "rank_biserial", "dz", "n_negative")} for c in h1},
                      "power": power, "selected_judge": sel,
                      "judge": {j: {k: v for k, v in cal[j].items() if not isinstance(v, dict)} for j in ("gemma", "sol") if j in cal},
                      "sweep": sw}, indent=1, default=float))


if __name__ == "__main__":
    main()
