#!/usr/bin/env python3
"""Power and practical-support probabilities for the pre-registration (evidence/M4/M4.T1/prereg.md §5), from the
pilot and from development seeds only (1000-1099; never the held-out block).

Run on the Spark host venv (gtsam for B1):
  ~/.venvs/beaconmind/bin/python course-project/tools/prereg_power.py > course-project/evidence/M4/M4.T1/power.txt
Tests are the pre-registered ones (metrics/stats.py: exact signed-rank, Hodges-Lehmann interval), n = 30 per arm.
Family 1 has three H1 tests under Holm, so an arm's H1 is rejected at a level between alpha/3 (when it has the
smallest p-value) and alpha (when the other two are rejected first); both ends are shown.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote this power analysis after the analysis review.
"""
import math
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "beaconmind" / "src"))
sys.path.insert(0, str(ROOT / "tools"))
from beaconmind.envs import kinsim_lite as ks  # noqa: E402
from beaconmind.metrics import pilot as pm  # noqa: E402
from beaconmind.metrics import stats as st  # noqa: E402
from study_analyze import dead_reckoning_chain  # noqa: E402

N, SIMS, ALPHA, SESOI = 30, 4000, 0.05, 0.03
PILOT_MEAN, PILOT_SD = -0.02704, 0.03110          # evidence/M4/M4.T11/pilot_summary.json, h1.drift2 (5 seeds)


def power(draw, sims=SIMS, seed=7):
    rng = np.random.default_rng(seed)
    rej3 = rej1 = prac = 0
    for _ in range(sims):
        d = draw(rng)
        p = st.signed_rank_test(d, "less")["p"]
        rej3 += p <= ALPHA / 3
        rej1 += p <= ALPHA
        prac += p <= ALPHA / 3 and st.hodges_lehmann(d)["ci"][1] < -SESOI
    return rej3 / sims, rej1 / sims, prac / sims


def main():
    print("Power of H1 (exact one-sided signed-rank, n = %d, %d simulations each)" % (N, SIMS))
    print("columns: P(reject at alpha/3), P(reject at alpha), P(reject at alpha/3 and HL interval below -3 cm)")
    sd_hi = PILOT_SD * math.sqrt((5 - 1) / 0.484419)   # chi2(0.025, 4) = 0.484419: upper end of the pilot SD's 95 % CI
    rows = [("pilot effect: Normal(-2.70 cm, 3.11 cm)", lambda r: r.normal(PILOT_MEAN, PILOT_SD, N)),
            ("pilot mean, SD at its 95 %% upper bound (%.2f cm)" % (sd_hi * 100), lambda r: r.normal(PILOT_MEAN, sd_hi, N)),
            ("the 3 cm threshold: Normal(-3.00 cm, 3.11 cm)", lambda r: r.normal(-SESOI, PILOT_SD, N))]
    b2b0, logratio = [], []
    try:
        from beaconmind.baselines import b1_gtsam as b1
    except Exception:
        b1 = None
    for s in range(1000, 1100):
        try:
            ep = ks.run_episode(s, odo_bias=0.02)
        except NotImplementedError:
            continue
        ep["noise"] = dict(ks.NOISE, odo_bias=0.02)
        truth = [r["truth"] for r in ep["records"]]
        a_b0 = pm.trajectory_errors(dead_reckoning_chain(ep["records"]), truth)["ate_m"]
        a_b2 = pm.trajectory_errors([r["report"]["pose"] for r in ep["records"]], truth)["ate_m"]
        b2b0.append(a_b2 - a_b0)
        if b1 is not None and b1.gtsam is not None:
            a_b1 = pm.trajectory_errors([ks.rp(p) for p in b1.build_and_solve(ep)["online"]], truth)["ate_m"]
            logratio.append(math.log(a_b2 / a_b1) - math.log(2.0))
    b2b0 = np.array(b2b0)
    rows.append(("an arm that reproduces the procedure: resampled B2-B0 of %d dev seeds (mean %.2f cm, SD %.2f cm)"
                 % (len(b2b0), b2b0.mean() * 100, b2b0.std(ddof=1) * 100), lambda r: r.choice(b2b0, N, replace=True)))
    for label, draw in rows:
        a, b, c = power(draw)
        print("  %-95s %.3f  %.3f  %.3f" % (label, a, b, c))
    if logratio:
        lr = np.array(logratio)
        print("H2 with B2 as a stand-in for the agent: log(ATE_B2/ATE_B1) - log 2 over %d dev seeds: median %.2f "
              "(range %.2f to %.2f); seeds below 0: %d" % (len(lr), np.median(lr), lr.min(), lr.max(), int((lr < 0).sum())))
        rng = np.random.default_rng(9)
        p_h2 = np.mean([st.signed_rank_test(rng.choice(lr, N, replace=True), "less")["p"] <= ALPHA for _ in range(2000)])
        print("  P(reject H2 at alpha) for such an arm: %.3f" % p_h2)


if __name__ == "__main__":
    main()
