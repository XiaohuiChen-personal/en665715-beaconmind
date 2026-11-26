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
    assert w["estimand"] == "Hodges-Lehmann" and "median_note" in w                # no switch outside arm - B0
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


def test_the_skewness_switch_applies_to_arm_minus_b0_only():
    """prereg.md section 5: the switch to the median is pre-registered for families 1 and 2 (against B0 and B1) only;
    model - B2 and the model pairs keep the Hodges-Lehmann estimate, as the study's pairwise comparisons do, with the
    median as a note."""
    d = [-0.01, -0.012, -0.011, -0.013, -0.01, -0.011, -0.012, -0.9]
    v = rs.paired(d, True)
    assert abs(v["skewness_G1"]) > 1 and v["estimand"] == "median" and v["n_below"] == 8 and "median_note" not in v
    w = rs.paired(d, False)
    assert w["estimand"] == "Hodges-Lehmann" and w["median_note"]["estimate"] == pytest.approx(v["estimate"])


def test_the_slip_flagged_steps_are_checked_against_the_next_tag_fix(tmp_path):
    """A forward move flagged slip_suspected: the procedure composes it, the model (rule 2 of the room prompt) does
    not; the next tag fix says which was right."""
    pose = lambda x: {"x_m": x, "y_m": 0.0, "theta_deg": 0.0}  # noqa: E731
    odo = {"forward_m": 0.25, "left_m": 0.0, "dtheta_deg": 0.0}
    recs = []
    for k, (b2x, src) in enumerate(((0.0, "odometry"), (0.25, "odometry"), (0.25, "odometry"), (0.02, "beacon_fix"))):
        recs.append({"step": k, "truth": pose(b2x), "b2_estimate": pose(b2x), "report": {"pose_source": src},
                     "raw": {"odometry": dict(odo, forward_m=0.25 if k == 1 else 0.0)},
                     "calls": [{"tool": "compose_odometry", "args": {"forward_m": 0.25 if k == 1 else 0.0, "left_m": 0.0}}],
                     "observation_real": {"odometry_quality": "slip_suspected" if k == 1 else "ok"}})
    run = tmp_path / "opus"
    run.mkdir()
    mx = (0.0, 0.0, 0.0, 0.02)
    (run / "seed_3.jsonl").write_text("".join(json.dumps({
        "step": k, "estimate_pose": pose(x), "report": {"pose_source": recs[k]["report"]["pose_source"]},
        "calls": [{"tool": "compose_odometry", "args": {"forward_m": 0.0, "left_m": 0.0}}]}) + "\n" for k, x in enumerate(mx)))
    out = rs.slip_steps({3: {"records": recs}}, {"claude-opus-5-5": str(run)}, [3], ["claude-opus-5-5"])
    assert out["count"] == 1
    r = out["steps"][0]
    assert r["step"] == 1 and r["composed"]["B2"]["forward_m"] == 0.25 and r["composed"]["claude-opus-5-5"]["forward_m"] == 0.0
    t = r["tag_fix_check"]
    assert t["first_fix_step"] == 3 and t["b2_fix_step"] == 3 and t["from_step"] == 2
    assert t["distance_to_b2_fix_m"]["B2"] == pytest.approx(0.23) and t["distance_to_b2_fix_m"]["claude-opus-5-5"] == pytest.approx(0.02)


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
