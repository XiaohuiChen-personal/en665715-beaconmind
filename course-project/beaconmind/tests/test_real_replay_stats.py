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


def test_the_real_logs_get_paired_differences_only_with_b2_beside_every_model():
    """The real logs test no hypothesis (prereg.md section 6): differences with the study's estimator and interval and
    the counts below/above zero; no p-value, no Holm, no verdict; B2 - B0 shown first; H2 not run."""
    seeds = list(range(1, 9))
    res = _result({"B0": {s: 0.30 + 0.01 * s for s in seeds}, "B2": {s: 0.05 for s in seeds},
                   "claude-opus-5-5": {s: 0.05 + 0.001 * s for s in seeds}})
    arms = ["B0", "B2", "claude-opus-5-5"]
    t = rs.differences(rs.values(res, "vs_end_circle_m", seeds, arms), arms, "end circle")
    assert t["exploratory"] and t["h2"].startswith("not run")
    assert list(t["vs_B0"]) == ["B2", "claude-opus-5-5"]
    v = t["vs_B0"]["claude-opus-5-5"]
    assert v["estimand"] == "Hodges-Lehmann" and v["n_below"] == 8 and v["n_above"] == 0 and v["ci95"][1] < 0
    assert not any(k in v for k in ("p", "p_adj", "reject_h0", "practical"))
    w = t["vs_B2"]["claude-opus-5-5"]
    assert w["within_1cm_every_episode"] and w["n_above"] == 8 and t["llm_pairs"] == {} and t["mean_rank"] is None
    md = rs.markdown({"set": "s", "main_seeds": seeds, "flagged_seeds": [], "tests": [t], "behaviour": {},
                      "trace_arms": [], "traces": {}})
    assert "exploratory, not pre-registered" in md and "B2 - B0" in md
    for word in ("confirmatory", "reject", "Holm", "practical", "p-value ", "| p |"):
        assert word not in md


def test_three_models_give_their_pairs_and_mean_ranks_and_a_seed_missing_an_arm_is_left_out():
    seeds = list(range(1, 10))
    res = _result({"B0": {s: 0.4 for s in seeds}, "B2": {s: 0.05 for s in seeds},
                   "claude-opus-5-5": {s: 0.04 + 0.001 * s for s in seeds},
                   "qwen38-flash-xhigh": {s: 0.06 + 0.002 * s for s in seeds},
                   "gemma4-26b": {s: 0.10 + 0.003 * s for s in seeds}})
    res["errors"]["gemma4-26b"]["9"]["complete"] = False
    arms = ["B0", "B2", "claude-opus-5-5", "qwen38-flash-xhigh", "gemma4-26b"]
    per = rs.values(res, "vs_end_circle_m", seeds, arms)
    assert sorted(per) == list(range(1, 9))
    t = rs.differences(per, arms, "end circle")
    assert t["mean_rank"] == {"claude-opus-5-5": 1.0, "qwen38-flash-xhigh": 2.0, "gemma4-26b": 3.0}
    assert set(t["llm_pairs"]) == {"claude-opus-5-5 minus qwen38-flash-xhigh", "claude-opus-5-5 minus gemma4-26b",
                                   "qwen38-flash-xhigh minus gemma4-26b"}
    assert t["llm_pairs"]["claude-opus-5-5 minus gemma4-26b"]["n_below"] == 8
    assert set(t["vs_B0"]) == {"B2", "claude-opus-5-5", "qwen38-flash-xhigh", "gemma4-26b"}


def test_a_skewed_set_of_differences_switches_to_the_median_as_pre_registered():
    d = [-0.01, -0.012, -0.011, -0.013, -0.01, -0.011, -0.012, -0.9]
    v = rs.paired(d)
    assert abs(v["skewness_G1"]) > 1 and v["estimand"] == "median" and v["n_below"] == 8


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
