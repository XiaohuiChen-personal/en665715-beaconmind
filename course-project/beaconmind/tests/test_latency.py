"""Nearest-rank latency percentile tests.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the M1.T4 percentile cases.
"""
import pytest

from beaconmind.metrics.latency import percentile_nearest_rank, summarize_latencies


def test_p95_of_1_to_20_is_19():
    assert percentile_nearest_rank(range(1, 21), 95) == 19


def test_p50_of_four():
    assert percentile_nearest_rank([4, 1, 3, 2], 50) == 2


def test_p100_is_max():
    assert percentile_nearest_rank([5, 9, 1], 100) == 9


def test_empty_raises():
    with pytest.raises(ValueError):
        percentile_nearest_rank([], 50)


def test_q_out_of_range_raises():
    with pytest.raises(ValueError):
        percentile_nearest_rank([1, 2, 3], 0)
    with pytest.raises(ValueError):
        percentile_nearest_rank([1, 2, 3], 101)


def test_summarize_keys():
    summary = summarize_latencies([1, 2, 3])
    assert set(summary) == {"n", "p50", "p95", "max", "mean"}
    assert summary["n"] == 3
