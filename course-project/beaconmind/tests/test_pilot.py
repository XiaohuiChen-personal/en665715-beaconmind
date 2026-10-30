"""Tests for the pilot simulator, the D5 tool dispatcher, the report parser and the pilot metrics.

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: wrote these tests.
"""
import itertools
import json
import math

import pytest

from beaconmind.envs import kinsim_lite as ks
from beaconmind.harness import tools_d5 as t5
from beaconmind.metrics import pilot as pm


@pytest.fixture(scope="module")
def episode():
    return ks.run_episode(1000)


@pytest.mark.parametrize("seed", [1000, 1001, 1002, 1003, 1004, 1050])
def test_world_follows_d3(seed):
    w = ks.make_world(seed)
    assert 12 <= len(w) <= 16
    ids = [t["id"] for t in w]
    assert all(0 <= i <= 29 for i in ids)
    dup = [i for i in set(ids) if ids.count(i) == 2]
    assert len(dup) == 3 and max(ids.count(i) for i in ids) == 2
    for i in dup:
        a, b = [t for t in w if t["id"] == i]
        assert math.hypot(a["x_m"] - b["x_m"], a["y_m"] - b["y_m"]) >= 1.5
    for t in w:
        on_wall = (t["x_m"] in (ks.ARENA["x0"], ks.ARENA["x1"]) or t["y_m"] in (ks.ARENA["y0"], ks.ARENA["y1"]))
        assert on_wall


def test_episode_is_deterministic(episode):
    again = ks.run_episode(1000)
    assert [r["report"] for r in again["records"]] == [r["report"] for r in episode["records"]]
    assert [r["truth"] for r in again["records"]] == [r["truth"] for r in episode["records"]]


def test_counter_tracker_reproduces_b2_counters(episode):
    tr, prev_src = ks.CounterTracker(), None
    for r in episode["records"]:
        c = tr.before_step(r["raw"], prev_src)
        want = r["raw"]["counters"]
        assert (c["odometer_m"], c["travel_since_fix_m"], c["turns_since_fix"]) == (
            want["odometer_m"], want["travel_since_fix_m"], want["turns_since_fix"])
        prev_src = r["report"]["pose_source"]


def test_gold_calls_on_b2_inputs_give_perfect_f1(episode):
    """The procedure scored against itself: every B2 call matches the gold calls of its own input."""
    tr, prev_src, prev = ks.CounterTracker(), None, None
    tp = fp = fn = 0
    for r in episode["records"]:
        obs = ks.as_observation(1000, r["raw"], tr.before_step(r["raw"], prev_src))
        gold = pm.gold_calls(obs, prev)
        pred = [{"tool": n, "args": a} for n, a in r["calls"]]
        a, b, c = pm.match_calls(pred, gold)
        tp, fp, fn = tp + a, fp + b, fn + c
        prev, prev_src = r["report"], r["report"]["pose_source"]
    assert tp > 50 and fp == 0 and fn == 0


def test_observation_hides_truth(episode):
    obs = ks.as_observation(1000, episode["records"][3]["raw"], {"odometer_m": 0, "travel_since_fix_m": 0, "turns_since_fix": 0})
    assert all("_tag" not in d for d in obs["detections"]) and obs["mode"] == "replay"


def test_trajectory_errors_hand_fixture():
    truth = [{"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}, {"x_m": 1.0, "y_m": 0.0, "theta_deg": 90.0}]
    est = [{"x_m": 0.03, "y_m": 0.04, "theta_deg": 2.0}, {"x_m": 1.03, "y_m": 0.04, "theta_deg": 88.0}]
    e = pm.trajectory_errors(est, truth)
    assert e["ate_m"] == pytest.approx(0.05) and e["heading_rmse_deg"] == pytest.approx(2.0)
    assert e["final_pos_m"] == pytest.approx(0.05)


def test_call_matching_rule():
    pose = {"x_m": 0.5, "y_m": -0.2, "theta_deg": 30.0}
    gold = ("gate_detection", {"pose": pose, "det": 1, "candidates": ["B3", "B3b"]})
    ok = {"tool": "gate_detection", "args": {"pose": {"x_m": 0.505, "y_m": -0.2, "theta_deg": 30.05}, "det": 1,
                                              "candidates": ["B3b", "B3"]}}
    assert pm.call_matches(ok, gold)
    assert not pm.call_matches(dict(ok, args=dict(ok["args"], candidates=["B3"])), gold)
    assert not pm.call_matches(dict(ok, args=dict(ok["args"], det=0)), gold)
    assert not pm.call_matches(dict(ok, args=dict(ok["args"], pose={"x_m": 0.53, "y_m": -0.2, "theta_deg": 30})), gold)
    assert not pm.call_matches({"tool": "map_point", "args": {"pose": pose, "det": 1}}, gold)
    assert pm.match_calls([ok, ok], [gold]) == (1, 1, 0)
    assert pm.match_calls([], [gold]) == (0, 0, 1)


def test_prf():
    assert pm.prf(3, 1, 1)["f1"] == pytest.approx(0.75)
    assert pm.prf(0, 0, 0)["f1"] is None
    assert pm.prf(0, 2, 1)["f1"] == 0.0
    assert pm.prf(0, 0, 5)["f1"] == 0.0 and pm.prf(0, 0, 5)["precision"] is None


def _rep(assoc, labels):
    return {"associations": assoc, "map": [{"beacon": lab} for lab in labels]}


def test_label_tracker_scores_duplicates():
    tr = pm.LabelTracker()
    t4, t9 = [{"det": 0, "id": 7, "_tag": 4}], [{"det": 0, "id": 7, "_tag": 9}]
    out = tr.score_step(_rep([{"det": 0, "id": 7, "beacon": "B7", "result": "new"}], ["B7"]), None, t4, {7})
    assert out == [(True, "NEW_OK")]
    # the second physical tag with id 7 (tag 9) matched to B7: a false positive
    out = tr.score_step(_rep([{"det": 0, "id": 7, "beacon": "B7", "result": "matched"}], ["B7"]), _rep([], ["B7"]), t9, {7})
    assert out == [(True, "FP")]
    # tag 9 mapped as B7b; then tag 4 matched to B7 (TP); then tag 4 labelled new B7c (FN); then omitted (FN)
    tr.score_step(_rep([{"det": 0, "id": 7, "beacon": "B7b", "result": "new"}], ["B7", "B7b"]), _rep([], ["B7"]), t9, {7})
    prev = _rep([], ["B7", "B7b"])
    out += tr.score_step(_rep([{"det": 0, "id": 7, "beacon": "B7", "result": "matched"}], ["B7", "B7b"]), prev, t4, {7})
    out += tr.score_step(_rep([{"det": 0, "id": 7, "beacon": "B7c", "result": "new"}], ["B7", "B7b"]), prev, t4, {7})
    out += tr.score_step(_rep([], ["B7", "B7b"]), prev, t4, {7})
    assert [o for _, o in out] == ["FP", "TP", "FN", "FN"]
    s = pm.association_scores(out)
    assert s["precision"] == pytest.approx(0.5) and s["recall"] == pytest.approx(1 / 3)


def test_label_bound_only_when_carried():
    """A `new` that never reaches the carried map does not bind its label (review finding 3)."""
    tr = pm.LabelTracker()
    tr.score_step(_rep([{"det": 0, "id": 7, "beacon": "B7", "result": "new"}], []), None, [{"det": 0, "id": 7, "_tag": 4}], set())
    assert tr.tag_of == {}
    out = tr.score_step(_rep([{"det": 0, "id": 7, "beacon": "B7", "result": "new"}], ["B7"]), _rep([], []),
                        [{"det": 0, "id": 7, "_tag": 9}], set())
    assert out == [(False, "NEW_OK")] and tr.tag_of == {"B7": 9}


def test_string_det_is_not_a_match():
    pose = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
    assert not pm.call_matches({"tool": "map_point", "args": {"pose": pose, "det": "0"}}, ("map_point", {"pose": pose, "det": 0}))


def test_gold_calls_reproduce_b2_through_the_dispatcher(episode):
    """Non-circular check: B2's gold calls, answered by run_tool, give B2's prior and new map points."""
    tr, prev_src, prev = ks.CounterTracker(), None, None
    for r in episode["records"]:
        obs = ks.as_observation(1000, r["raw"], tr.before_step(r["raw"], prev_src))
        est = ks.estimate_step(obs, prev)
        st = {"moved": None, "estop": False}
        for name, args in est["calls"]:
            res = t5.run_tool(name, args, obs, prev, st)
            assert res.get("status") != "error", (name, res)
            if name == "compose_odometry":
                assert res == pytest.approx(est["prior"])
            if name == "map_point":
                entry = next(e for e in est["new_entries"] if e["first_seen_from"] == [round(args["pose"]["x_m"], 2), round(args["pose"]["y_m"], 2)])
                assert (round(res["x_m"], 2), round(res["y_m"], 2)) in {(e["x_m"], e["y_m"]) for e in est["new_entries"]}
                assert entry
        prev, prev_src = r["report"], r["report"]["pose_source"]


class _Blk:
    def __init__(self, text):
        self.type, self.text = "text", text

    def model_dump(self, exclude_none=True):
        return {"type": "text", "text": self.text}


class _Resp:
    def __init__(self, text):
        self.content, self.stop_reason, self.model = [_Blk(text)], "end_turn", "mock"
        self.usage = {"input_tokens": 1000, "output_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}


class _MockClient:
    """Answers every step at once with B2's report for that step; each call costs 1000 input tokens."""

    def __init__(self, reports):
        self.reports, self.messages = reports, self

    def create(self, **kw):
        step = json.loads(kw["messages"][0]["content"][0]["text"])["OBSERVATION"]["step"]
        return _Resp(json.dumps(dict(self.reports[step], decision="NONE")))


def test_budget_cap_leaves_no_fallback_and_resume_completes(tmp_path):
    pytest.importorskip("anthropic")
    from beaconmind.harness import anthropic_replay as ar
    doc = ks.run_episode(1001)
    client = _MockClient([r["report"] for r in doc["records"]])
    out = tmp_path / "seed.jsonl"
    per_call = ar.turn_cost({"input_tokens": 1000})
    ok = ar.replay_seed(client, "sys", doc, out, ar.Budget(per_call * 5.5), 12, log=lambda m: None)
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert not ok and len(rows) == 6 and not any(r["fallback"] for r in rows)
    ok = ar.replay_seed(client, "sys", doc, out, ar.Budget(10.0), 12, log=lambda m: None)
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert ok and [r["step"] for r in rows] == list(range(12)) and not any(r["fallback"] for r in rows)
    assert all(r["checks"]["valid"] for r in rows)


def test_map_scores_c10():
    world = [{"tag": 0, "id": 3, "x_m": 0.0, "y_m": 0.0}, {"tag": 1, "id": 3, "x_m": 2.0, "y_m": 0.0},
             {"tag": 2, "id": 5, "x_m": 1.0, "y_m": 1.0}]
    m = [{"beacon": "B3", "id": 3, "x_m": 0.03, "y_m": 0.04}, {"beacon": "B3b", "id": 3, "x_m": 2.0, "y_m": 0.1},
         {"beacon": "B5", "id": 5, "x_m": 0.0, "y_m": 0.0}]
    s = pm.map_scores_c10(m, world)
    assert s["phantoms"] == 1 and s["map_precision"] == pytest.approx(2 / 3) and s["map_recall"] == pytest.approx(2 / 3)
    assert s["map_rmse_m"] == pytest.approx(math.sqrt((0.05 ** 2 + 0.1 ** 2) / 2))


def test_linear_score():
    assert pm.linear_score(0.0, 0.3) == 1.0 and pm.linear_score(0.15, 0.3) == pytest.approx(0.5)
    assert pm.linear_score(0.5, 0.3) == 0.0


def test_parse_report_variants():
    assert t5.parse_report('{"a": 1}') == {"a": 1}
    assert t5.parse_report('```json\n{"a": 1}\n```') == {"a": 1}
    assert t5.parse_report('Here is my report:\n{"a": {"b": 2}}\nDone.') == {"a": {"b": 2}}
    assert t5.parse_report("no json here") is None and t5.parse_report(None) is None


def test_report_checks_and_replay_move_refusal(episode):
    raw = episode["records"][5]["raw"]
    obs = ks.as_observation(1000, raw, {"odometer_m": 0, "travel_since_fix_m": 0, "turns_since_fix": 0})
    rep = dict(episode["records"][5]["report"], decision="NONE")
    assert t5.report_checks(rep, obs)["valid"]
    assert not t5.report_checks(dict(rep, pose={"x_m": "a"}), obs)["valid"]
    st = {"moved": None, "estop": False}
    assert t5.run_tool("move", {"action": "FORWARD_25"}, obs, rep, st)["result"] == "refused"
    assert t5.run_tool("gate_detection", {"pose": rep["pose"], "det": 0, "candidates": ["B99"]}, obs, rep, st)["status"] == "error"


def test_tool_defs_match_the_smoke_harness_names():
    names = [d["name"] for d in t5.anthropic_tool_defs()]
    assert names == ["compose_odometry", "gate_detection", "fix_pose", "map_point", "update_beacon",
                     "predict_observation", "exploration_summary", "move", "emergency_stop"]
    assert all(set(d["input_schema"]["required"]) == set(d["input_schema"]["properties"]) for d in t5.anthropic_tool_defs())


def test_seeds_complete_without_unimplemented_branches():
    for seed in itertools.islice(range(1000, 1100), 0, 100, 10):
        ks.run_episode(seed)
