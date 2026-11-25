"""tools/real_replay_stats.py: the pre-registered tests on the real-log replay's values, and the per-step traces.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote these tests.
"""
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("real_replay_stats", ROOT / "tools" / "real_replay_stats.py")
rs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rs)


def _result(per_arm):
    """An analyze result with the end-circle errors given per arm and seed (all complete)."""
    return {"errors": {arm: {str(s): {"complete": True, "vs_end_circle_m": v, "final_m": v + 0.01}
                             for s, v in by.items()} for arm, by in per_arm.items()}}


def test_family_one_with_one_arm_run_holds_the_others_at_p_one():
    seeds = list(range(1, 9))
    res = _result({"B0": {s: 0.30 + 0.01 * s for s in seeds}, "B2": {s: 0.05 for s in seeds},
                   "claude-opus-5-5": {s: 0.05 + 0.001 * s for s in seeds}})
    arms = ["B0", "B2", "claude-opus-5-5"]
    per = rs.values(res, "vs_end_circle_m", seeds, arms)
    t = rs.tests_on(per, arms, "end circle", True)
    h1 = t["family1"]["H1:claude-opus-5-5"]
    # 8 of 8 below B0: the exact one-sided signed-rank p is 1/256; Holm over three pre-registered arms triples it
    assert h1["test"] == "signed-rank" and h1["p"] == pytest.approx(1 / 256) and h1["p_adj"] == pytest.approx(3 / 256)
    assert h1["reject_h0"] and h1["practical"] and h1["n_negative"] == 8
    assert t["family1"]["H1:gemma4-26b"]["not_run"] and t["family1"]["H1:gemma4-26b"]["p_adj"] == 1.0
    assert not t["family1"]["H2:claude-opus-5-5"]["tested"]                 # no B1 on real logs: family 2 not run
    assert t["models"] is None                                             # fewer than three LLM arms
    v = t["vs_B2"]["claude-opus-5-5"]
    assert v["alternative"] == "two-sided" and v["within_1cm_every_seed"] and v["n_positive"] == 8


def test_three_llm_arms_get_the_friedman_test_and_a_seed_missing_an_arm_is_left_out():
    seeds = list(range(1, 10))
    base = {s: 0.4 for s in seeds}
    res = _result({"B0": base, "B2": {s: 0.05 for s in seeds}, "claude-opus-5-5": {s: 0.04 + 0.001 * s for s in seeds},
                   "qwen38-flash-xhigh": {s: 0.06 + 0.002 * s for s in seeds},
                   "gemma4-26b": {s: 0.10 + 0.003 * s for s in seeds}})
    res["errors"]["gemma4-26b"]["9"]["complete"] = False
    arms = ["B0", "B2", "claude-opus-5-5", "qwen38-flash-xhigh", "gemma4-26b"]
    per = rs.values(res, "vs_end_circle_m", seeds, arms)
    assert sorted(per) == list(range(1, 9))
    t = rs.tests_on(per, arms, "end circle", False)
    m = t["models"]
    assert m["interpret_pairs"] and m["mean_rank"]["claude-opus-5-5"] == 1.0 and m["mean_rank"]["gemma4-26b"] == 3.0
    assert set(t["vs_B0"]) == {"claude-opus-5-5", "qwen38-flash-xhigh", "gemma4-26b"}


def test_ate_and_traces_on_a_small_set(tmp_path):
    truth = [{"x_m": 0.1 * k, "y_m": 0.0, "theta_deg": 0.0} for k in range(4)]
    recs = [{"step": k, "truth": truth[k], "b2_estimate": dict(truth[k], y_m=0.01),
             "raw": {"odometry": None if k == 0 else {"forward_m": 0.1, "left_m": 0.0, "dtheta_deg": 0.0}}}
            for k in range(4)]
    docs = {7: {"records": recs}}
    run = tmp_path / "arm"
    run.mkdir()
    poses = [dict(truth[0]), dict(truth[1]), dict(truth[2], y_m=0.08), dict(truth[3], y_m=0.02)]
    (run / "seed_7.jsonl").write_text("".join(json.dumps({"step": k, "estimate_pose": p}) + "\n"
                                              for k, p in enumerate(poses)))
    ate = rs.ate_all_steps(docs, {"claude-opus-5-5": str(run)}, [7])
    assert ate[7]["B0"]["ate_m"] == pytest.approx(0.0)
    assert ate[7]["B2"]["ate_m"] == pytest.approx(0.01)
    tr = rs.traces(docs, ate, [7], ["B0", "B2", "claude-opus-5-5"])[7]["arms"]["claude-opus-5-5"]
    assert tr["vs_B2"]["first_step_beyond"] == 2 and tr["vs_B2"]["steps_beyond"] == 1      # 7 cm from B2 at step 2
    assert tr["vs_B2"]["max_gap_m"] == pytest.approx(0.07) and tr["error_at_pct_m"]["100"] == pytest.approx(0.02)
