"""Tests of tools/study_analyze.py: robustness to malformed model output, the B0 chain, padding, the families.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote these tests after the analysis review.
"""
import copy
import importlib.util
import json
import pathlib

import numpy as np
import pytest

pytest.importorskip("scipy")                   # the analysis runs on the Spark host venv; beaconmind-ros has no SciPy

from beaconmind.envs import kinsim_lite as ks  # noqa: E402
from beaconmind.harness import replay as rp  # noqa: E402
from beaconmind.harness import tools_d5 as t5  # noqa: E402

TOOLS = pathlib.Path(__file__).resolve().parents[2] / "tools"
spec = importlib.util.spec_from_file_location("study_analyze", TOOLS / "study_analyze.py")
sa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sa)


@pytest.fixture(scope="module")
def episode():
    return ks.run_episode(1010, odo_bias=0.02)


def _procedure_rows(episode, n=None):
    """Rows as the harness would write them for a model that runs the coded procedure exactly."""
    rows, tr, prev, src = [], ks.CounterTracker(), None, None
    for rec in episode["records"][:n]:
        obs = ks.as_observation(episode["seed"], rec["raw"], tr.before_step(rec["raw"], src))
        est = ks.estimate_step(obs, prev)
        st_ = {"moved": None, "estop": False}
        calls = [{"tool": a, "args": b, "result": t5.rnd(t5.run_tool(a, b, obs, prev, st_))} for a, b in est["calls"]]
        rep = dict(rec["report"], decision="NONE")
        rows.append({"seed": episode["seed"], "step": rec["step"], "truth": rec["truth"], "raw": rec["raw"],
                     "observation": obs, "prev_report": prev, "harness_prior": rp.harness_prior(obs, prev),
                     "report": rep, "checks": t5.report_checks(rep, obs), "fallback": False,
                     "estimate_pose": rep["pose"], "calls": calls, "turns": [], "error": None, "seconds": 1.0,
                     "cost_usd": 0.0, "next_prev": rep, "fix_verified": None})
        prev, src = rep, rep["pose_source"]
    return rows


def test_procedure_rows_score_like_b2(episode):
    m = sa.seed_metrics(episode, None, {"proc": _procedure_rows(episode)})
    assert m["proc"]["ate_m"] == pytest.approx(m["B2"]["ate_m"])
    assert m["proc"]["f1"] == 1.0 and m["proc"]["pose_source_agree"] == 1.0 and m["proc"]["assoc_agree"] == 1.0
    assert m["proc"]["pose_state_violation_rate"] == 0.0 and m["proc"]["map_state_violation_rate"] == 0.0


def test_malformed_model_output_is_scored_not_fatal(episode):
    rows = _procedure_rows(episode)
    bad = copy.deepcopy(rows)
    bad[3]["report"]["associations"] = [{"det": 0, "result": "matched", "beacon": ["B1"]}, {"det": "1", "result": None},
                                        "not a dict", {"det": 2, "result": "new", "beacon": {"x": 1}}]
    # the reviewer's IndexError case: a beacon the next step updates has a one-element first_seen_from
    for b in bad[0]["report"]["map"]:
        b["first_seen_from"] = [1]
    bad[0]["next_prev"] = bad[0]["report"]
    bad[1]["prev_report"] = bad[0]["report"]
    with pytest.raises(IndexError):
        ks.estimate_step(bad[1]["observation"], bad[1]["prev_report"])
    bad[6]["calls"] = [{"tool": "fix_pose", "args": {"prior": "x", "matches": 5}, "result": {}},
                       {"tool": "gate_detection", "args": {"pose": None, "det": [1], "candidates": "B1"}, "result": {}}]
    bad[7]["report"]["associations"] = {"det": 0}
    for r in bad:
        r["checks"] = t5.report_checks(r["report"], r["observation"])
    m = sa.seed_metrics(episode, None, {"bad": bad})
    assert np.isfinite(m["bad"]["ate_m"]) and m["bad"]["gold_skipped"] >= 1


def test_b0_chain_equals_a_pure_dead_reckoning_arm(episode):
    """An arm that never reports anything (all steps padded) dead-reckons exactly like B0: H1's difference is 0."""
    m = sa.seed_metrics(episode, None, {"none": []})
    assert m["none"]["ate_m"] == m["B0"]["ate_m"] and m["none"]["missing_steps"] == len(episode["records"])
    padded, missing = sa.complete_rows([], episode)
    assert [r["estimate_pose"] for r in padded] == sa.dead_reckoning_chain(episode["records"])


def test_confirmatory_families_and_missing_arm():
    rng = np.random.default_rng(5)
    per = {}
    for s in range(30):
        b0 = 0.15 + rng.normal(0, 0.02)
        per[s] = {"B0": {"ate_m": b0}, "B1": {"ate_m": 0.011 + abs(rng.normal(0, 0.002))},
                  "A": {"ate_m": b0 - 0.04 + rng.normal(0, 0.01), "missing_steps": 0},
                  "B": {"ate_m": b0 - 0.05 + rng.normal(0, 0.01), "missing_steps": 0}}
    t = sa.confirmatory(per, ["A", "B"], ["A", "B", "C"], True)
    assert t["H1:C"]["not_run"] and not t["H1:C"]["reject_h0"]            # a missing arm counts as p = 1
    assert t["H1:A"]["reject_h0"] and t["H1:B"]["reject_h0"]
    assert not t["H2:A"]["tested"] and not t["H2:A"]["reject_h0"]        # gate closed: H1:C was not rejected
    assert t["H1:A"]["test"] == "signed-rank" and t["H1:A"]["practical"] is True
    t2 = sa.confirmatory(per, ["A", "B"], ["A", "B"], True)
    assert t2["H2:A"]["tested"] and not t2["H2:A"]["reject_h0"]          # ATE far above 2x B1: H2 fails
    assert t2["H1:A"]["p_adj"] == pytest.approx(min(1, 2 * min(t2["H1:A"]["p"], t2["H1:B"]["p"]))) or \
        t2["H1:A"]["p_adj"] >= t2["H1:A"]["p"]


def test_describe_keeps_metrics_missing_on_the_first_seed():
    per = {1: {"B0": {"ate_m": 0.1}, "B2": {"ate_m": 0.09}, "A": {"ate_m": 0.08, "f1": None, "_seconds": [1.0]}},
           2: {"B0": {"ate_m": 0.1}, "B2": {"ate_m": 0.09}, "A": {"ate_m": 0.07, "f1": 0.9, "_seconds": [2.0, 3.0]}}}
    d = sa.describe(per, ["A"])
    assert d["A"]["f1"]["n"] == 1 and d["A"]["pooled_latency"]["steps"] == 3 and d["A"]["worst_seed"]["seed"] == 1


def test_torn_last_line_is_ignored(tmp_path):
    p = tmp_path / "seed_1.jsonl"
    p.write_text(json.dumps({"step": 0}) + "\n" + json.dumps({"step": 1}) + "\n" + '{"step": 2, "tr')
    assert [r["step"] for r in sa.load_run(p)] == [0, 1]
