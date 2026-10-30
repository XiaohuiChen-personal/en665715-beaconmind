"""Nearest-rank latency summaries for BeaconMind decision times.

Percentiles use the nearest-rank rule: sort the values, then take the element at
index ceil(q/100 * n) - 1, with q in percent. An empty sample or a q outside
(0, 100] is an error. This module is stdlib only.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote nearest-rank percentiles and summarize_latencies.
"""
import math


def percentile_nearest_rank(values, q: float) -> float:
    """Nearest-rank percentile: sort, take element ceil(q/100 * n) - 1 (q in (0, 100]).

    ValueError on an empty list or q outside (0, 100].
    """
    if isinstance(q, bool) or not isinstance(q, (int, float)):
        raise ValueError("q must be a number in (0, 100]")
    if not (0 < q <= 100):
        raise ValueError("q must be in (0, 100]")
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        raise ValueError("empty list")
    # Integer q uses exact ceil(q * n / 100). A float multiply (0.95 * n) can
    # land just above an integer and select the next rank.
    if isinstance(q, int) or q == int(q):
        rank = (int(q) * n + 99) // 100 - 1
    else:
        rank = math.ceil(q / 100.0 * n) - 1
    if rank < 0 or rank >= n:
        raise ValueError("nearest-rank index out of range")
    return ordered[rank]


def summarize_latencies(values) -> dict:
    """Return n, nearest-rank p50, nearest-rank p95, max and mean for values."""
    sample = list(values)
    n = len(sample)
    if n == 0:
        raise ValueError("empty list")
    return {
        "n": n,
        "p50": percentile_nearest_rank(sample, 50),
        "p95": percentile_nearest_rank(sample, 95),
        "max": max(sample),
        "mean": sum(sample) / n,
    }
