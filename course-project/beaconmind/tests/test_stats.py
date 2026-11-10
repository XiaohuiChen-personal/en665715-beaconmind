"""Tests of metrics/stats.py against independent references: SciPy's exact signed-rank test where it is valid
(no zeros, no ties), brute-force enumeration of every sign assignment where it is not, textbook critical values,
and coverage by simulation.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote these tests.
"""
import itertools

import numpy as np
import pytest

sps = pytest.importorskip("scipy.stats")       # the statistics run on the Spark host venv; beaconmind-ros has no SciPy

from beaconmind.metrics import stats as st  # noqa: E402


def _brute(d, alternative):
    nz = np.asarray([x for x in d if x != 0], dtype=float)
    ranks = sps.rankdata(np.abs(nz))
    s_obs = ranks[nz > 0].sum()
    sums = [sum(r for r, s in zip(ranks, signs) if s) for signs in itertools.product((0, 1), repeat=len(nz))]
    le = np.mean([s <= s_obs + 1e-9 for s in sums])
    ge = np.mean([s >= s_obs - 1e-9 for s in sums])
    return {"less": le, "greater": ge, "two-sided": min(1.0, 2 * min(le, ge))}[alternative]


@pytest.mark.parametrize("alt", ["less", "greater", "two-sided"])
def test_signed_rank_matches_scipy_exact_without_ties_or_zeros(alt):
    rng = np.random.default_rng(1)
    for _ in range(40):
        d = rng.normal(-0.5, 1.0, 30)
        assert st.signed_rank_test(d, alt)["p"] == pytest.approx(sps.wilcoxon(d, alternative=alt, method="exact").pvalue,
                                                                 rel=1e-10)


@pytest.mark.parametrize("alt", ["less", "greater", "two-sided"])
def test_signed_rank_with_zeros_and_ties_matches_enumeration(alt):
    rng = np.random.default_rng(2)
    for _ in range(25):
        d = np.round(rng.normal(-0.3, 1.0, 12), 1)        # rounding makes ties
        d[rng.integers(0, 12, 2)] = 0.0                     # and zeros
        assert st.signed_rank_test(d, alt)["p"] == pytest.approx(_brute(d, alt), abs=1e-12)


def test_reviewer_hand_case_with_zeros():
    """n = 30 with 3 zeros: the exact p on the 27 non-zero pairs, not SciPy's normal approximation."""
    rng = np.random.default_rng(3)
    d = rng.normal(-0.03, 0.02, 30)
    d[:3] = 0.0
    want = sps.wilcoxon(d[3:], alternative="less", method="exact").pvalue
    got = st.signed_rank_test(d, "less")
    assert got["p"] == pytest.approx(want, rel=1e-10) and got["n_zero"] == 3 and got["n_used"] == 27


def test_hodges_lehmann_interval_order_statistic_and_coverage():
    assert st.hodges_lehmann(np.arange(30.0))["k"] == 138          # n = 30: P(T+ <= 137) <= 0.025 < P(T+ <= 138)
    rng = np.random.default_rng(4)
    hits = 0
    for _ in range(1500):
        x = rng.normal(2.0, 1.0, 30)
        lo, hi = st.hodges_lehmann(x)["ci"]
        hits += lo <= 2.0 <= hi
    assert 0.935 < hits / 1500 < 0.97
    d = rng.normal(0, 1, 11)
    i, j = np.triu_indices(11)
    assert st.hodges_lehmann(d)["estimate"] == pytest.approx(np.median((d[i] + d[j]) / 2))


def test_median_interval_and_sign_test():
    x = np.arange(1.0, 31.0)
    m = st.median_ci(x)
    assert m["ci"] == [10.0, 21.0] and m["estimate"] == 15.5      # n = 30: x(10), x(21)
    d = [-1, -2, -3, -4, -5, 1, -6, 0]
    assert st.sign_test(d, "less")["p"] == pytest.approx(sps.binomtest(6, 7, 0.5, alternative="greater").pvalue)


def test_holm_and_gatekeeping():
    adj = st.holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adj == pytest.approx({"a": 0.03, "c": 0.06, "b": 0.06})
    assert st.holm({"a": 0.01, "b": None})["b"] == 1.0
    g = st.serial_gatekeeping({"H1a": 0.001, "H1b": 0.002}, {"H2a": 0.001}, 0.05)
    assert g["H1a"]["reject"] and g["H1b"]["reject"] and g["H2a"]["tested"] and g["H2a"]["reject"]
    g = st.serial_gatekeeping({"H1a": 0.001, "H1b": 0.2}, {"H2a": 0.001}, 0.05)
    assert g["H1a"]["reject"] and not g["H1b"]["reject"] and not g["H2a"]["tested"] and not g["H2a"]["reject"]
    g = st.serial_gatekeeping({"H1a": 0.001, "H1b": None}, {}, 0.05)          # a test not run counts as p = 1
    assert not g["H1b"]["reject"] and g["H1a"]["p_adj"] == pytest.approx(0.002)
    assert st.serial_gatekeeping({"a": 0.025, "b": 0.05}, {}, 0.05)["a"]["reject"]   # reject at p_adj <= alpha


def test_skewness_and_rank_biserial():
    assert st.adjusted_skewness([1, 2, 3]) == 0.0
    assert st.adjusted_skewness([0, 0, 0, 0, 10]) == pytest.approx(sps.skew([0, 0, 0, 0, 10], bias=False))
    assert st.rank_biserial([-1, -2, 3]) == pytest.approx((3 - 3) / 6)
