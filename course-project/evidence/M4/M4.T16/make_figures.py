#!/usr/bin/env python3
"""Two presentation figures for the main study, drawn from the frozen analysis's own outputs (no new statistics).

The frozen analysis (tools/study_analyze.py) draws report/figures/fig_study.{pdf,png}: every arm's per-seed ATE on a
linear axis, where Gemma 4's values (up to 227 cm) flatten the differences H1 is about. This script reads
study_per_seed.csv and study_summary.json in this folder and draws:
  fig_study_log   the same per-seed ATE strips on a log axis;
  fig_study_h1    H1's paired differences ATE(arm) - ATE(B0) per seed, with the pre-registered estimate and exact
                  95 % interval (Hodges-Lehmann, or the median under the sign test) and the -3 cm practical line;
                  Gemma 4 in its own panel because its differences are 20 times larger.
Every number drawn is read from those two files. PDF fonts are TrueType (Type 42), not Type 3.

Run from the repository root (python3 with matplotlib):
  python3 course-project/evidence/M4/M4.T16/make_figures.py

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-13: wrote these figures after the analysis.
"""
import csv
import json
import pathlib
import random
import statistics
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parents[2] / "report" / "figures"
ARMS = ["claude-opus-5-5", "qwen38-flash-xhigh", "gemma4-26b"]
ORDER = ["B0", "B1", "B2"] + ARMS
NAME = {"B0": "B0\ndead reckoning", "B1": "B1\nfactor graph", "B2": "B2\ncoded procedure",
        "claude-opus-5-5": "Opus 5.5", "qwen38-flash-xhigh": "Qwen3.8", "gemma4-26b": "Gemma 4"}
INK, MUTED, GRID = "#222222", "#666666", "#dddddd"
XPOS = [0.0, 1.7]                  # strip positions in a panel: room for each arm's annotation
BASE, LLM = "#555555", "#c0392b"   # baselines grey, LLM arms one accent; identity is carried by the axis labels


def style():
    plt.rcParams.update({"font.size": 8, "font.family": "serif", "axes.linewidth": 0.6, "pdf.fonttype": 42,
                         "ps.fonttype": 42, "axes.edgecolor": MUTED, "xtick.color": INK, "ytick.color": INK,
                         "axes.labelcolor": INK})


def load():
    per = {}
    with open(HERE / "study_per_seed.csv", newline="") as fh:
        for r in csv.DictReader(fh):
            per.setdefault(int(r["seed"]), {})[r["arm"]] = float(r["ate_m"]) * 100
    summary = json.loads((HERE / "study_summary.json").read_text())
    return per, summary


def jitter(n, seed, width=0.15):
    """Seeded uniform horizontal offsets, so the x position inside a strip carries no information."""
    rng = random.Random(seed)
    return [rng.uniform(-width, width) for _ in range(n)]


def p_text(p):
    if p >= 0.995:
        return "1.00"
    if p >= 0.001:
        return "%.2g" % p
    m, e = ("%.1e" % p).split("e")
    return "%s x 10^%d" % (m, int(e))


def fig_log(per):
    seeds = sorted(per)
    fig, ax = plt.subplots(figsize=(7.0, 2.8))
    xs = range(len(ORDER))
    for s in seeds:
        ax.plot(xs, [per[s][a] for a in ORDER], color=GRID, lw=0.5, zorder=1)
    for x, a in zip(xs, ORDER):
        v = [per[s][a] for s in seeds]
        ax.scatter([x] * len(v), v, s=9, zorder=2, color=BASE if a in ("B0", "B1", "B2") else LLM, linewidths=0)
        m = statistics.median(v)
        ax.plot([x - 0.25, x + 0.25], [m, m], color=INK, lw=1.2, zorder=3)
        ax.annotate("%.1f" % m, (x + 0.27, m), va="center", fontsize=7, color=INK)
    ax.set_yscale("log")
    ax.set_ylim(0.5, 400)
    ax.set_yticks([1, 3, 10, 30, 100, 300])
    ax.set_yticklabels(["1", "3", "10", "30", "100", "300"])
    ax.set_xticks(list(xs))
    ax.set_xticklabels([NAME[a] for a in ORDER])
    ax.set_ylabel("ATE-RMSE per seed (cm, log scale)")
    ax.grid(axis="y", lw=0.3, color=GRID)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.set_title("30 held-out seeds, 2 % odometry drift; bar and number = median; grey lines join a seed's arms",
                 fontsize=7, color=MUTED, loc="left")
    fig.tight_layout()
    return fig


def fig_h1(per, summary):
    seeds = sorted(per)
    conf = summary["confirmatory"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 2.8), gridspec_kw={"width_ratios": [2, 1]})
    for ax, arms in ((ax1, ARMS[:2]), (ax2, ARMS[2:])):
        for x, arm in zip(XPOS, arms):
            d = [per[s][arm] - per[s]["B0"] for s in seeds]
            ax.scatter([x + j for j in jitter(len(d), arm)], d, s=9, color=LLM, alpha=0.8, linewidths=0, zorder=2)
            t = conf["H1:" + arm]
            est, lo, hi = 100 * t["estimate"], 100 * t["ci95"][0], 100 * t["ci95"][1]
            ax.errorbar([x + 0.32], [est], yerr=[[est - lo], [hi - est]], fmt="o", ms=4, color=INK, capsize=3,
                        lw=1.0, zorder=3)
            what = "HL" if t["test"] == "signed-rank" else "median"
            verdict = ("rejected, not practical" if t["reject_h0"] and not t["practical"] else
                       "supported in practice" if t.get("practical") else "not rejected")
            ax.annotate("%s %+.1f cm\n[%+.1f, %+.1f]\nHolm p = %s\n%s" % (
                what, est, lo, hi, p_text(t["p_adj"]), verdict),
                (x + 0.40, 0.98), xycoords=("data", "axes fraction"), va="top", fontsize=6.5, color=INK)
        ax.axhline(0, color=MUTED, lw=0.7, zorder=1)
        ax.set_xticks(XPOS[:len(arms)])
        ax.set_xticklabels([NAME[a] for a in arms])
        ax.set_xlim(-0.4, XPOS[len(arms) - 1] + 1.15)
        ax.grid(axis="y", lw=0.3, color=GRID)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    ax1.axhline(-3, color=MUTED, lw=0.7, ls="--", zorder=1)
    ax1.annotate("-3 cm", (ax1.get_xlim()[1] - 0.02, -3.3), ha="right", va="top", fontsize=6.5, color=MUTED)
    ax1.set_ylabel("ATE(arm) - ATE(B0) per seed (cm)\nbelow 0 = better than dead reckoning")
    ax2.set_ylabel("same, own scale (cm)")
    ax1.set_title("H1 by seed (n = 30): dots = seeds; black = estimate, exact 95 % interval; dashed = -3 cm threshold",
                  fontsize=7, color=MUTED, loc="left")
    fig.tight_layout()
    return fig


def main():
    style()
    per, summary = load()
    if summary.get("status") != "confirmatory":
        print("warning: the analysis output is labelled %r" % summary.get("status"), file=sys.stderr)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fig in (("fig_study_log", fig_log(per)), ("fig_study_h1", fig_h1(per, summary))):
        fig.savefig(OUT / (name + ".pdf"))
        fig.savefig(OUT / (name + ".png"), dpi=200)
        plt.close(fig)
        print("wrote", OUT / (name + ".pdf"), "and .png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
