#!/usr/bin/env python3
"""Analyse the main simulated study (plan/README.md §3.6, work list 1.8; pre-registration evidence/M4/M4.T1/).

Arms per seed: B0 (dead reckoning at report precision), B1 (GTSAM iSAM2 online estimate with odometry-scale
calibration and oracle association), B2 (the coded procedure, which drives the log), and one L2 arm per LLM. Every
arm is scored at report precision (2-dp positions, 1-dp headings): the LLM arms and B2 report so; B1's online poses
are rounded; B0 is the dead-reckoning chain rounded at every step, exactly as an arm that only dead-reckons through
its own reports would be (so such an arm ties B0 and adds nothing to a test). Metrics follow the report's Section
IV-C and metrics/pilot.py.

Confirmatory tests (pre-registered; serial gatekeeping at alpha 0.05, metrics/stats.py):
  family 1  H1[arm]  ATE(arm) - ATE(B0) < 0                 for the three LLM arms, Holm
  family 2  H2[arm]  log(ATE(arm)/ATE(B1)) - log 2 < 0      Holm, tested only if every H1 is rejected
  Each test: the exact one-sided Wilcoxon signed-rank test (zeros dropped, ties exact), or the exact sign test when
  the adjusted skewness G1 of the 30 values exceeds 1 in absolute value. Estimand: the Hodges-Lehmann estimate with
  its exact 95 % interval (the sample median with its order-statistic interval under the sign test). A hypothesis
  not run (an arm or B1 missing) counts as p = 1. H1 is supported in practice only if it is rejected and the
  interval's upper end is below -3 cm.
Secondary family H4 (descriptive unless the Friedman test is significant at 0.05): Friedman over the three LLM arms'
ATE with Kendall's W, and the three pairwise two-sided exact signed-rank tests with Holm.
Sensitivity (descriptive): H1 without the seeds an arm did not finish.
Descriptive: every other metric, per arm: mean and median with bootstrap intervals, n, the worst seed; latency
pooled over all real steps; L2 minus B2.

With --prereg, the run is checked against prereg.json (arms, seeds, B1 present and calibrated, each arm's frozen
config tag in every row and run.json, a clean tree at every launch, the observation-log hashes); any mismatch labels
the output "exploratory" and lists why. Run `prereg_freeze.py --verify` too: it checks the analysis files themselves.

Run on the Spark host venv (numpy, scipy, matplotlib):
  ~/.venvs/beaconmind/bin/python course-project/tools/study_analyze.py --study course-project/data/main \\
      --obs obslogs/test/drift2 --b1 b1/test/drift2 --runs runs/drift2 \\
      --arms claude-opus-5-5,qwen38-flash-xhigh,gemma4-26b --seeds 2000-2029 \\
      --prereg course-project/evidence/M4/M4.T1/prereg.json --evidence course-project/evidence/M4/M4.T16 \\
      --report course-project/report

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote this analysis (generalising pilot_analyze.py to
several LLM arms and B1) and revised it after an adversarial review the same day.
"""
import argparse
import csv
import hashlib
import json
import math
import pathlib
import platform
import statistics
import sys

import numpy as np
import scipy
from scipy import stats as sps

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "beaconmind" / "src"))
from beaconmind import geometry as g  # noqa: E402
from beaconmind.envs import kinsim_lite as ks  # noqa: E402
from beaconmind.harness import replay as rp  # noqa: E402
from beaconmind.metrics import pilot as pm  # noqa: E402
from beaconmind.metrics import stats as st  # noqa: E402

ALPHA = 0.05
SESOI_M = 0.03
TAU_POSE_M, TAU_MAP_M = 0.25, 0.30
SKEW_LIMIT = 1.0
DISPLAY = {"claude-opus-5-5": "Opus 5.5", "qwen38-flash-xhigh": "Qwen3.8", "qwen38-flash-medium": "Qwen3.8-med",
           "gemma4-26b": "Gemma 4"}


def seed_list(text):
    out = []
    for part in text.split(","):
        a, _, b = part.partition("-")
        for s in (range(int(a), int(b) + 1) if b else [int(a)]):
            if s not in out:
                out.append(s)
    return out


def nearest_rank(v, q):
    s = sorted(v)
    return s[max(0, math.ceil(q / 100 * len(s)) - 1)] if s else None


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def load_run(path):
    """Rows of one seed's run log, first record of each step, in step order (a torn last line is ignored)."""
    rows, seen = [], set()
    if not path.exists():
        return rows
    lines = path.read_text(encoding="utf-8").split("\n")
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except ValueError:
            if any(x.strip() for x in lines[i + 1:]):
                raise
            break
        if r["step"] not in seen:
            seen.add(r["step"])
            rows.append(r)
    return sorted(rows, key=lambda r: r["step"])


def dead_reckoning_chain(records):
    """B0 at report precision: the start pose composed with each step's odometry, rounded at every step."""
    pose, out = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}, []
    for r in records:
        odo = r["raw"]["odometry"]
        if odo:
            pose = ks.rp(g.compose_odometry(pose, odo["forward_m"], odo["left_m"], odo["dtheta_deg"]))
        out.append(dict(pose))
    return out


# ---------------------------------------------------------------- per seed

def map_and_assoc(reports, prevs, recs, world):
    ids = [t["id"] for t in world]
    dup = {i for i in ids if ids.count(i) == 2}
    tr = pm.LabelTracker()
    res = []
    for rep, prev, rec in zip(reports, prevs, recs):
        res += tr.score_step(rep, prev, rec["raw"]["detections"], dup)
    a_all, a_dup = pm.association_scores(res), pm.association_scores([x for x in res if x[0]])
    final = next((rep for rep in reversed(reports) if rep), {"map": []})
    ms = pm.map_scores_c10(final.get("map"), world)
    out = dict(ms, assoc_precision=a_all["precision"], assoc_recall=a_all["recall"],
               assoc_precision_dup=a_dup["precision"], assoc_recall_dup=a_dup["recall"],
               assoc_counts=a_all, assoc_counts_dup=a_dup)
    out["map_score"] = pm.linear_score(ms["map_rmse_m"], TAU_MAP_M) if ms["map_rmse_m"] is not None else None
    return out


def traj(poses, truth):
    e = pm.trajectory_errors(poses, truth)
    out = {k: e[k] for k in ("ate_m", "heading_rmse_deg", "final_pos_m", "final_heading_deg", "max_pos_m")}
    out["pose_score"] = pm.linear_score(e["ate_m"], TAU_POSE_M)
    return out


def complete_rows(rows, doc):
    """Pad an unfinished run with invalid-report fallbacks so every arm is scored on the whole episode."""
    recs = doc["records"]
    if len(rows) >= len(recs):
        return rows[:len(recs)], 0
    padded = list(rows)
    prev = rows[-1]["next_prev"] if rows else None
    for rec in recs[len(rows):]:
        est = rp.fallback_report(prev, rec["raw"]["odometry"], rec["step"])
        padded.append({"seed": doc["seed"], "step": rec["step"], "truth": rec["truth"], "raw": rec["raw"],
                       "observation": ks.as_observation(doc["seed"], rec["raw"], rec["raw"]["counters"]),
                       "prev_report": prev, "report": None, "checks": {"valid": False, "decision_none": False},
                       "fallback": True, "estimate_pose": est["pose"], "calls": [], "turns": [], "error": "missing step",
                       "seconds": 0.0, "cost_usd": 0.0, "next_prev": est, "fix_verified": None, "padded": True})
        prev = est
    return padded, len(recs) - len(rows)


def _assoc_key(a):
    """A sortable, hashable key of one association (any field may be malformed in model output)."""
    if not isinstance(a, dict):
        return ("<malformed>", "", "")
    res = a.get("result")
    lab = a.get("beacon") if res != "rejected" else None
    return (repr(a.get("det")), repr(res), repr(lab))


def llm_metrics(rows, doc):
    recs = doc["records"]
    truth = [r["truth"] for r in recs]
    out = traj([r["estimate_pose"] for r in rows], truth)
    out.update(map_and_assoc([r["next_prev"] for r in rows], [r["prev_report"] for r in rows], recs, doc["world"]))
    tp = fp = fn = skipped = 0
    agree_src = agree_assoc = compared = 0
    pose_checked = pose_viol = map_viol = map_checked = 0
    real = [r for r in rows if not r.get("padded")]
    for r in real:
        if r["checks"]["valid"]:
            sv = pm.state_violations(r)
            if sv["pose"] is not None:
                pose_checked += 1
                pose_viol += not sv["pose"]
            map_viol += sv["map_bad"]
            map_checked += sv["map_checked"]
        gold = pm.gold_calls(r["observation"], r["prev_report"])
        if gold is None:
            skipped += 1
            continue
        a, b, c = pm.match_calls(r["calls"], gold)
        tp, fp, fn = tp + a, fp + b, fn + c
        if r["checks"]["valid"]:
            try:
                gest = ks.estimate_step(r["observation"], r["prev_report"])
            except Exception:  # noqa: BLE001  (gold was available above, so this does not happen; kept defensive)
                continue
            compared += 1
            agree_src += r["report"].get("pose_source") == gest["pose_source"]
            want = sorted(_assoc_key(a_) for a_, _ in gest["assoc"])
            assocs = r["report"].get("associations")
            got = sorted(_assoc_key(x) for x in (assocs if isinstance(assocs, list) else []))
            agree_assoc += want == got
    out.update(pm.prf(tp, fp, fn))
    n = len(rows)
    secs = [r["seconds"] for r in real]
    turns = [t for r in real for t in r["turns"]]

    def tok(t, key):
        return (t.get("tokens") or {}).get(key) or 0
    out.update(
        gold_skipped=skipped, pose_source_agree=agree_src / compared if compared else None,
        assoc_agree=agree_assoc / compared if compared else None,
        pose_state_violation_rate=pose_viol / pose_checked if pose_checked else None,
        map_state_violation_rate=map_viol / map_checked if map_checked else None,
        valid_rate=sum(1 for r in rows if r["checks"]["valid"]) / n,
        valid_rate_real=sum(1 for r in real if r["checks"]["valid"]) / len(real) if real else None,
        fallbacks=sum(1 for r in rows if r["fallback"]), padded_steps=sum(1 for r in rows if r.get("padded")),
        repaired_reports=sum(1 for r in real if (r["checks"].get("repaired_chars") or 0) > 0),
        unverified_fix_claims=sum(1 for r in real if r.get("fix_verified") is False),
        verified_fix_claims=sum(1 for r in real if r.get("fix_verified") is True),
        errors={e: sum(1 for r in real if (r["error"] or "").split(":")[0] == e)
                for e in sorted({(r["error"] or "").split(":")[0] for r in real if r["error"]})},
        tool_error_results=sum(1 for r in real for c in r["calls"]
                               if isinstance(c.get("result"), dict) and c["result"].get("status") == "error"),
        move_calls=sum(1 for r in real for c in r["calls"] if c.get("tool") == "move"),
        estops=sum(1 for r in real for c in r["calls"] if c.get("tool") == "emergency_stop"),
        tool_calls_per_step=sum(len(r["calls"]) for r in real) / max(1, len(real)),
        turns_per_step=len(turns) / max(1, len(real)),
        latency_p50_s=nearest_rank(secs, 50), latency_p95_s=nearest_rank(secs, 95),
        latency_max_s=max(secs) if secs else None,
        input_tokens_per_step=sum(tok(t, "in") for t in turns) / max(1, len(real)),
        output_tokens_per_step=sum(tok(t, "out") for t in turns) / max(1, len(real)),
        cost_usd=sum(r["cost_usd"] for r in real), n_steps=n, real_steps=len(real), _seconds=secs)
    out["cost_per_step_usd"] = out["cost_usd"] / max(1, len(real))
    return out


def seed_metrics(doc, b1doc, arm_rows):
    recs = doc["records"]
    truth = [r["truth"] for r in recs]
    out = {"n_steps": len(recs), "n_tags": len(doc["world"])}
    out["B0"] = traj(dead_reckoning_chain(recs), truth)
    b2_reports = [r["report"] for r in recs]
    out["B2"] = dict(traj([r["pose"] for r in b2_reports], truth),
                     **map_and_assoc(b2_reports, [None] + b2_reports[:-1], recs, doc["world"]))
    if b1doc is not None:
        if len(b1doc["online"]) != len(recs):
            raise ValueError("B1 log for seed %s has %d steps, episode has %d" % (doc["seed"], len(b1doc["online"]), len(recs)))
        if b1doc.get("scored", "online") != "online":
            raise ValueError("B1 log for seed %s does not score the online trajectory" % doc["seed"])
        out["B1"] = dict(traj([ks.rp(p) for p in b1doc["online"]], truth), **pm.map_scores_c10(b1doc["map"], doc["world"]))
        out["B1"]["smoothed_ate_m"] = pm.trajectory_errors(b1doc["smoothed"], truth)["ate_m"]
        if b1doc.get("scales"):
            out["B1"]["scale_forward"], out["B1"]["scale_turn"] = b1doc["scales"]["forward"], b1doc["scales"]["turn"]
    for arm, rows in arm_rows.items():
        full, missing = complete_rows(rows, doc)
        out[arm] = llm_metrics(full, doc)
        out[arm]["missing_steps"] = missing
    return out


# ---------------------------------------------------------------- statistics

def one_test(d, alternative, practical=False):
    """The pre-registered test of one hypothesis on its per-seed values d."""
    d = np.asarray(d, dtype=float)
    skew = st.adjusted_skewness(d)
    if abs(skew) > SKEW_LIMIT:
        res = st.sign_test(d, alternative)
        est = st.median_ci(d)
        test, estimand = "sign", "median"
    else:
        res = st.signed_rank_test(d, alternative)
        est = st.hodges_lehmann(d)
        test, estimand = "signed-rank", "Hodges-Lehmann"
    sd = d.std(ddof=1) if len(d) > 1 else float("nan")
    out = {"n": int(len(d)), "test": test, "alternative": alternative, "p": res["p"], "statistic": res["statistic"],
           "n_used": res["n_used"], "n_zero": res["n_zero"], "skewness_G1": skew, "estimand": estimand,
           "estimate": est["estimate"], "ci95": est["ci"], "mean": float(d.mean()), "median": float(np.median(d)),
           "mean_boot_ci95": st.bootstrap_ci(d), "rank_biserial": st.rank_biserial(d.tolist()),
           "dz": float(d.mean() / sd) if sd and sd > 0 else None, "n_negative": int((d < 0).sum()),
           "n_positive": int((d > 0).sum()), "d": d.tolist()}
    out["_practical_ok"] = est["ci"][1] < -SESOI_M if practical else None
    return out


def confirmatory(per, arms, prereg_arms, have_b1):
    seeds = sorted(per)
    tests, fam1, fam2 = {}, {}, {}
    for arm in prereg_arms:
        k1, k2 = "H1:" + arm, "H2:" + arm
        if arm in arms:
            a = np.array([per[s][arm]["ate_m"] for s in seeds])
            b0 = np.array([per[s]["B0"]["ate_m"] for s in seeds])
            tests[k1] = one_test(a - b0, "less", practical=True)
            fam1[k1] = tests[k1]["p"]
            if have_b1:
                b1 = np.array([per[s]["B1"]["ate_m"] for s in seeds])
                tests[k2] = one_test(np.log(a / b1) - math.log(2.0), "less")
                fam2[k2] = tests[k2]["p"]
            else:
                fam2[k2] = None
        else:
            fam1[k1], fam2[k2] = None, None              # not run: p = 1 inside its family
    gate = st.serial_gatekeeping(fam1, fam2, ALPHA)
    for k, v in gate.items():
        t = tests.setdefault(k, {"p": None, "not_run": True})
        t.update(family=v["family"], p_adj=v["p_adj"], reject_h0=v["reject"], tested=v["tested"])
        if k.startswith("H1:") and not t.get("not_run"):
            t["practical"] = bool(v["reject"] and t.pop("_practical_ok"))
        else:
            t.pop("_practical_ok", None)
    return tests


def model_comparison(per, arms):
    seeds = sorted(per)
    if len(arms) < 3:
        return None
    mat = np.array([[per[s][a]["ate_m"] for a in arms] for s in seeds])
    fr = sps.friedmanchisquare(*[mat[:, j] for j in range(len(arms))])
    n, k = mat.shape
    pairs = {}
    for i in range(len(arms)):
        for j in range(i + 1, len(arms)):
            d = mat[:, i] - mat[:, j]
            r = st.signed_rank_test(d, "two-sided")
            hl = st.hodges_lehmann(d)
            pairs["%s-%s" % (arms[i], arms[j])] = {"p": r["p"], "n_used": r["n_used"], "estimate": hl["estimate"],
                                                  "ci95": hl["ci"], "mean": float(d.mean())}
    adj = st.holm({k_: v["p"] for k_, v in pairs.items()})
    for k_, v in pairs.items():
        v["p_holm"] = adj[k_]
    ranks = np.apply_along_axis(sps.rankdata, 1, mat)
    return {"friedman_chi2": float(fr.statistic), "friedman_p": float(fr.pvalue),
            "kendall_w": st.kendall_w(fr.statistic, n, k), "interpret_pairs": bool(fr.pvalue < ALPHA),
            "mean_rank": {a: float(ranks[:, j].mean()) for j, a in enumerate(arms)}, "pairs": pairs}


def sensitivity(per, arms):
    """H1 without the seeds an arm did not finish (descriptive)."""
    out = {}
    for arm in arms:
        seeds = [s for s in sorted(per) if per[s][arm]["missing_steps"] == 0]
        if len(seeds) < len(per):
            d = [per[s][arm]["ate_m"] - per[s]["B0"]["ate_m"] for s in seeds]
            r = st.signed_rank_test(d, "less") if d else {"p": None}
            out[arm] = {"n": len(seeds), "excluded": [s for s in sorted(per) if s not in seeds], "p": r["p"],
                        "hodges_lehmann": st.hodges_lehmann(d)["estimate"] if d else None}
    return out


def describe(per, arms):
    seeds = sorted(per)
    out = {}
    for arm in ["B0", "B1", "B2"] + arms:
        if arm not in per[seeds[0]]:
            continue
        keys = sorted({k for s in seeds for k, v in per[s][arm].items() if st.is_finite(v) and not k.startswith("_")})
        d = {}
        for k in keys:
            vals = [per[s][arm][k] for s in seeds if st.is_finite(per[s][arm].get(k))]
            arr = np.array(vals, dtype=float)
            d[k] = {"n": len(vals), "mean": float(arr.mean()), "median": float(np.median(arr)),
                    "min": float(arr.min()), "max": float(arr.max()),
                    "mean_ci95": st.bootstrap_ci(arr), "median_ci95": st.bootstrap_ci(arr, stat=np.median)}
        worst = max(seeds, key=lambda s: per[s][arm]["ate_m"])
        d["worst_seed"] = {"seed": worst, "ate_m": per[worst][arm]["ate_m"]}
        if arm in arms:
            secs = [x for s in seeds for x in per[s][arm].get("_seconds", [])]
            d["pooled_latency"] = {"steps": len(secs), "p50_s": nearest_rank(secs, 50), "p95_s": nearest_rank(secs, 95),
                                   "max_s": max(secs) if secs else None}
            dd = [per[s][arm]["ate_m"] - per[s]["B2"]["ate_m"] for s in seeds]
            d["minus_B2_ate"] = {"mean": float(np.mean(dd)), "median": float(np.median(dd)),
                                 "max_abs": float(np.max(np.abs(dd))), "within_1cm": int(sum(abs(x) <= 0.01 for x in dd)),
                                 "n": len(dd)}
        out[arm] = d
    return out


# ---------------------------------------------------------------- provenance against the pre-registration

def check_prereg(prereg, study, args, arms, seeds):
    bad = []
    des = prereg["design"]
    if arms != des["arms"]["L2"]:
        bad.append("arms %s != pre-registered %s" % (arms, des["arms"]["L2"]))
    if seeds != prereg["seeds"]:
        bad.append("seeds differ from the pre-registered list")
    if not args.b1:
        bad.append("B1 not given")
    for s in seeds:
        if sha256(study / args.obs / ("seed_%d.json" % s)) != prereg["obslogs"].get(str(s)):
            bad.append("observation log of seed %d changed" % s)
            break
    for arm in arms:
        want = prereg.get("config_tags", {}).get(arm)
        rdir = study / args.runs / arm
        runs = [p for p in sorted(rdir.glob("run*.json")) if not p.name.startswith("run.end")]
        if not runs:
            bad.append("%s: no run.json" % arm)
            continue
        for rj in runs:
            h = json.loads(rj.read_text())
            if h.get("config") != want:
                bad.append("%s: %s config %s != frozen %s" % (arm, rj.name, h.get("config"), want))
            # the config tag covers every file a run depends on, so the run may be launched from a later commit
            # (the one that adds prereg.json); it must be a clean tree
            if str(h.get("git_dirty")).strip() != "0":
                bad.append("%s: %s was launched from a dirty tree (%s files)" % (arm, rj.name, h.get("git_dirty")))
        for s in seeds:
            if any(r.get("config") != want for r in load_run(rdir / ("seed_%d.jsonl" % s))):
                bad.append("%s seed %d: a row has another config tag" % (arm, s))
                break
    if args.b1:
        for s in seeds:
            b = json.loads((study / args.b1 / ("seed_%d.json" % s)).read_text())
            if not (b.get("provenance") or {}).get("calibrate_scale") or b.get("scored") != "online":
                bad.append("B1 seed %d is not the calibrated online estimate" % s)
                break
    return bad


# ---------------------------------------------------------------- outputs

def write_csv(per, arms, path):
    cols = ["ate_m", "final_pos_m", "heading_rmse_deg", "map_rmse_m", "map_precision", "map_recall", "phantoms",
            "assoc_precision", "assoc_precision_dup", "assoc_recall", "f1", "valid_rate", "fallbacks",
            "unverified_fix_claims", "pose_state_violation_rate", "missing_steps", "latency_p50_s", "latency_p95_s",
            "cost_usd"]
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["seed", "arm", "steps"] + cols)
        for s in sorted(per):
            for arm in ["B0", "B1", "B2"] + arms:
                if arm in per[s]:
                    w.writerow([s, arm, per[s]["n_steps"]] + [per[s][arm].get(c) for c in cols])


def figure(per, arms, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 8, "font.family": "serif", "axes.linewidth": 0.6})
    order = [a for a in ["B0", "B1", "B2"] + arms if a in per[sorted(per)[0]]]
    fig, ax = plt.subplots(figsize=(7.0, 2.6))
    xs = list(range(len(order)))
    for s in sorted(per):
        ax.plot(xs, [per[s][a]["ate_m"] * 100 for a in order], color="#bbbbbb", lw=0.5, zorder=1)
    for x, a in zip(xs, order):
        v = [per[s][a]["ate_m"] * 100 for s in sorted(per)]
        ax.scatter([x] * len(v), v, s=8, zorder=2, color="#444444" if a in ("B0", "B1", "B2") else "#d62728")
        ax.plot([x - 0.25, x + 0.25], [statistics.median(v)] * 2, color="black", lw=1.2, zorder=3)
    ax.set_xticks(xs)
    ax.set_xticklabels([DISPLAY.get(a, a) for a in order])
    ax.set_ylabel("ATE-RMSE (cm)")
    ax.grid(axis="y", lw=0.3, alpha=0.6)
    fig.tight_layout()
    fig.savefig(path.with_suffix(".pdf"))
    fig.savefig(path.with_suffix(".png"), dpi=200)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", required=True, help="study data folder, e.g. course-project/data/main")
    ap.add_argument("--cond", default="drift2")
    ap.add_argument("--obs", required=True, help="obslogs folder relative to --study")
    ap.add_argument("--b1", default=None, help="B1 output folder relative to --study")
    ap.add_argument("--runs", required=True, help="runs folder relative to --study (one subfolder per arm)")
    ap.add_argument("--arms", required=True)
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--prereg", default=None, help="prereg.json; without it the output is exploratory")
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--report", default=None, help="report folder for the figure (omit for dev runs)")
    ap.add_argument("--tag", default="study")
    args = ap.parse_args()
    study = pathlib.Path(args.study)
    arms = args.arms.split(",")
    seeds = seed_list(args.seeds)
    prereg = json.loads(pathlib.Path(args.prereg).read_text()) if args.prereg else None
    prereg_arms = prereg["design"]["arms"]["L2"] if prereg else arms
    per, missing_runs = {}, {}
    for seed in seeds:
        doc = json.loads((study / args.obs / ("seed_%d.json" % seed)).read_text(encoding="utf-8"))
        b1doc = json.loads((study / args.b1 / ("seed_%d.json" % seed)).read_text()) if args.b1 else None
        arm_rows = {}
        for arm in arms:
            rows = load_run(study / args.runs / arm / ("seed_%d.jsonl" % seed))
            if [r["step"] for r in rows] != list(range(len(rows))):
                raise ValueError("non-contiguous run log: %s seed %d" % (arm, seed))
            if len(rows) < len(doc["records"]):
                missing_runs.setdefault(arm, {})[seed] = len(doc["records"]) - len(rows)
            arm_rows[arm] = rows
        per[seed] = seed_metrics(doc, b1doc, arm_rows)
    problems = check_prereg(prereg, study, args, arms, seeds) if prereg else ["no pre-registration given"]
    summary = {"status": "confirmatory" if not problems else "exploratory", "status_reasons": problems,
               "cond": args.cond, "arms": arms, "seeds": seeds, "missing_steps": missing_runs,
               "confirmatory": confirmatory(per, arms, prereg_arms, bool(args.b1)),
               "model_comparison": model_comparison(per, arms), "sensitivity_h1_finished_seeds": sensitivity(per, arms),
               "descriptive": describe(per, arms), "alpha": ALPHA, "sesoi_m": SESOI_M, "skew_limit": SKEW_LIMIT,
               "frozen_commit": prereg.get("git_commit") if prereg else None,
               "versions": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__},
               "per_seed": {s: {k: ({kk: vv for kk, vv in v.items() if not kk.startswith("_")} if isinstance(v, dict) else v)
                                for k, v in per[s].items()} for s in sorted(per)}}
    ev = pathlib.Path(args.evidence)
    ev.mkdir(parents=True, exist_ok=True)
    (ev / ("%s_summary.json" % args.tag)).write_text(json.dumps(summary, indent=1, default=float))
    write_csv(per, arms, ev / ("%s_per_seed.csv" % args.tag))
    if args.report:
        (pathlib.Path(args.report) / "figures").mkdir(parents=True, exist_ok=True)
        figure(per, arms, pathlib.Path(args.report) / "figures" / ("fig_%s" % args.tag))
    short = {k: {kk: v.get(kk) for kk in ("test", "n_used", "estimate", "ci95", "p", "p_adj", "tested", "reject_h0",
                                          "practical", "skewness_G1")} for k, v in summary["confirmatory"].items()}
    print(json.dumps({"status": summary["status"], "status_reasons": problems[:8], "confirmatory": short,
                      "model_comparison": {k: v for k, v in (summary["model_comparison"] or {}).items() if k != "pairs"},
                      "missing_steps": missing_runs,
                      "median_ate_cm": {a: round(statistics.median(per[s][a]["ate_m"] for s in per) * 100, 2)
                                        for a in ["B0", "B1", "B2"] + arms if a in per[seeds[0]]}},
                     indent=1, default=float))


if __name__ == "__main__":
    main()
