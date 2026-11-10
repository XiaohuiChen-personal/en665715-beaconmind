"""Exact paired tests, estimates and multiplicity rules for the main study (pre-registration evidence/M4/M4.T1/).

- `signed_rank_test`: the Wilcoxon signed-rank test (Wilcoxon 1945) with zero differences dropped (Wilcoxon's own
  rule) and an exact p-value from the permutation distribution of the positive-rank sum, computed by dynamic
  programming over doubled midranks, so tied |d| are handled exactly too. SciPy's `method="exact"` assumes no ties,
  and with any zero SciPy 1.18 falls back to a normal approximation (adversarial review 2026-11-10, finding 2).
- `hodges_lehmann`: the Hodges-Lehmann estimate (the median of the Walsh averages, the estimand of the signed-rank
  test) with its exact distribution-free confidence interval from the order statistics of the Walsh averages
  (Hollander, Wolfe & Chicken, Nonparametric Statistical Methods, 3rd ed., 2014, Sec. 3.3).
- `sign_test` with the sample median and its exact order-statistic interval.
- `holm`: Holm's step-down adjusted p-values (Holm 1979); reject where the adjusted p <= alpha.
- `serial_gatekeeping`: family 1 (the primary hypotheses) under Holm at alpha; family 2 is tested, under Holm at
  alpha, only if every hypothesis of family 1 was rejected. This keeps the family-wise error at alpha over both
  families, because family 2 is reached only when family 1 has spent nothing a later rejection could inflate.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote these functions and their tests.
"""
import math

import numpy as np
from scipy import stats as sps


def _null_counts(doubled):
    """Number of sign assignments giving each value of S = sum of the doubled ranks with a positive sign."""
    total = int(sum(doubled))
    counts = np.zeros(total + 1, dtype=np.float64)       # at most 2^n <= 2^53 for n <= 53, exact in float64
    counts[0] = 1.0
    for r in doubled:
        r = int(r)
        shifted = np.zeros_like(counts)
        shifted[r:] = counts[:total + 1 - r]
        counts = counts + shifted
    return counts


def signed_rank_test(d, alternative):
    """Exact Wilcoxon signed-rank test of the median of d against 0. alternative: 'less', 'greater', 'two-sided'.
    Returns {p, statistic (positive-rank sum on the original rank scale), n_used, n_zero, ties}."""
    d = np.asarray(d, dtype=float)
    nz = d[d != 0]
    n = len(nz)
    if n == 0:
        return {"p": 1.0, "statistic": None, "n_used": 0, "n_zero": int(len(d)), "ties": False}
    if n > 50:
        raise ValueError("exact signed-rank distribution implemented for n <= 50")
    ranks = sps.rankdata(np.abs(nz))                     # midranks for ties
    doubled = np.rint(2 * ranks).astype(int)
    s_obs = int(doubled[nz > 0].sum())
    counts = _null_counts(doubled)
    probs = counts / counts.sum()
    p_le = float(probs[: s_obs + 1].sum())
    p_ge = float(probs[s_obs:].sum())
    p = {"less": p_le, "greater": p_ge, "two-sided": min(1.0, 2 * min(p_le, p_ge))}[alternative]
    return {"p": p, "statistic": s_obs / 2.0, "n_used": n, "n_zero": int(len(d) - n),
            "ties": bool(len(np.unique(np.abs(nz))) < n)}


def hodges_lehmann(d, conf=0.95):
    """Hodges-Lehmann estimate and exact confidence interval (no-ties null distribution, all n values)."""
    d = np.asarray(d, dtype=float)
    n = len(d)
    i, j = np.triu_indices(n)
    walsh = np.sort((d[i] + d[j]) / 2.0)
    m = len(walsh)
    probs = _null_counts(2 * np.arange(1, n + 1)) / 2.0 ** n
    cdf = np.cumsum(probs)[::2]                           # P(T+ <= t) on the original rank scale, t = 0..M
    alpha = 1.0 - conf
    k = 0
    while k + 1 <= m and cdf[k] <= alpha / 2:             # largest k with P(T+ <= k-1) <= alpha/2
        k += 1
    k = max(k, 1)
    return {"estimate": float(np.median(walsh)), "ci": [float(walsh[k - 1]), float(walsh[m - k])], "k": k,
            "conf": conf}


def sign_test(d, alternative):
    """Exact sign test of the median of d against 0 (zeros dropped)."""
    d = np.asarray(d, dtype=float)
    nz = d[d != 0]
    n = len(nz)
    if n == 0:
        return {"p": 1.0, "statistic": None, "n_used": 0, "n_zero": int(len(d))}
    neg, pos = int((nz < 0).sum()), int((nz > 0).sum())
    if alternative == "less":
        p = sps.binomtest(neg, n, 0.5, alternative="greater").pvalue
    elif alternative == "greater":
        p = sps.binomtest(pos, n, 0.5, alternative="greater").pvalue
    else:
        p = sps.binomtest(pos, n, 0.5, alternative="two-sided").pvalue
    return {"p": float(p), "statistic": float(neg if alternative == "less" else pos), "n_used": n,
            "n_zero": int(len(d) - n)}


def median_ci(d, conf=0.95):
    """Sample median and its exact distribution-free order-statistic interval."""
    x = np.sort(np.asarray(d, dtype=float))
    n = len(x)
    cdf = sps.binom.cdf(np.arange(n + 1), n, 0.5)
    alpha = 1.0 - conf
    j = 0
    while j + 1 <= n and cdf[j] <= alpha / 2:             # largest j with P(B <= j-1) <= alpha/2
        j += 1
    j = max(j, 1)
    return {"estimate": float(np.median(x)), "ci": [float(x[j - 1]), float(x[n - j])], "conf": conf}


def holm(pvals):
    """Holm step-down adjusted p-values for a dict name -> p (None counts as p = 1)."""
    items = sorted(((k, 1.0 if p is None else p) for k, p in pvals.items()), key=lambda kv: kv[1])
    m, adj, running = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        adj[k] = running
    return adj


def serial_gatekeeping(family1, family2, alpha=0.05):
    """family1, family2: dicts name -> p (None = not run, counted as p = 1). Returns {name: {p_adj, reject,
    tested}}: family 2 is tested only if every family-1 hypothesis is rejected."""
    out = {}
    a1 = holm(family1)
    for k, p in a1.items():
        out[k] = {"p_adj": p, "reject": p <= alpha, "tested": True, "family": 1}
    gate_open = bool(family1) and all(v["reject"] for v in out.values())
    a2 = holm(family2) if family2 else {}
    for k, p in a2.items():
        out[k] = {"p_adj": p if gate_open else None, "reject": bool(gate_open and p <= alpha), "tested": gate_open,
                  "family": 2}
    return out


def adjusted_skewness(d):
    """Fisher-Pearson adjusted skewness G1 (scipy.stats.skew, bias=False) of all values, zeros included."""
    d = np.asarray(d, dtype=float)
    if len(d) < 3 or d.std() == 0:
        return 0.0
    return float(sps.skew(d, bias=False))


def rank_biserial(d):
    """Matched-pairs rank-biserial correlation (Kerby 2014): (sum of positive ranks - sum of negative) / total."""
    d = [x for x in d if x != 0]
    if not d:
        return None
    ranks = sps.rankdata([abs(x) for x in d])
    wp = sum(r for r, x in zip(ranks, d) if x > 0)
    wm = sum(r for r, x in zip(ranks, d) if x < 0)
    return (wp - wm) / (len(d) * (len(d) + 1) / 2)


def bootstrap_ci(x, stat=np.mean, n=10000, seed=12345, conf=0.95):
    x = np.asarray(x, dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n, len(x)))
    vals = np.apply_along_axis(stat, 1, x[idx])
    a = (1 - conf) / 2
    return [float(np.percentile(vals, 100 * a)), float(np.percentile(vals, 100 * (1 - a)))]


def kendall_w(chi2, n, k):
    return float(chi2 / (n * (k - 1))) if n and k > 1 else None


def is_finite(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
