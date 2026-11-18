"""Tests of the closed loop (harness/closed_loop.py): a scripted model plays reports through the real provider
tool loop (no network), the coded procedure B2 drives the same loop, and the logs are checked against the schemas.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote these tests.
"""
import copy
import json
import types

import pytest

import beaconmind
from beaconmind.envs import kinsim_lite as ks
from beaconmind.harness import closed_loop as cl
from beaconmind.harness import replay as rp
from beaconmind.harness import validator as vd
from beaconmind.metrics import closed_loop as mc
from beaconmind.schemas import validate

pytest.importorskip("anthropic")
from beaconmind.harness.providers import anthropic_messages as am  # noqa: E402

OPUS = (dict(am.SETTINGS), dict(am.PRICE))
FABLE_PRICE = {"input": 8.0, "cache_write_5m": 10.0, "cache_read": 0.2, "output": 40.0}
USAGE = {"input_tokens": 1000, "output_tokens": 200, "cache_creation_input_tokens": 300, "cache_read_input_tokens": 5000}
NOLOG = lambda m: None  # noqa: E731


def _resp(blocks, stop):
    return types.SimpleNamespace(content=blocks, stop_reason=stop, usage=dict(USAGE), model="scripted")


class _Block(types.SimpleNamespace):
    """A content block as the SDK returns it: attributes, and model_dump() for sending it back."""

    def model_dump(self, exclude_none=True):
        return dict(self.__dict__)


def _tool(i, name, args):
    return _Block(type="tool_use", id="tu_%d" % i, name=name, input=args)


class ScriptedModel:
    """A fake Anthropic client. Per step it (1) calls the coded procedure's estimation tools and
    exploration_summary, (2) calls the tools the script names for that step (default: move(the procedure's
    decision)), (3) writes the procedure's report with the script's decision. Script entry per step:
    {"calls": [(tool, args), ...], "decision": str, "final": raw text, "raise": Exception}."""

    def __init__(self, script=None):
        self.script, self.requests = script or {}, []
        self.messages = self

    def create(self, **kw):
        self.requests.append(copy.deepcopy({k: v for k, v in kw.items() if k != "messages"}) | {"messages": kw["messages"]})
        msgs = kw["messages"]
        user = json.loads(msgs[0]["content"][0]["text"])
        obs, prev = user["OBSERVATION"], user["PREVIOUS_REPORT"]
        plan = self.script.get(obs["step"], {})
        if "raise" in plan and len(msgs) == 1:
            raise plan["raise"]
        if obs["odometry"] is None and prev is not None:      # a reboot: the procedure has no branch for it
            obs = dict(obs, odometry={"forward_m": 0.0, "left_m": 0.0, "dtheta_deg": 0.0})
        est = ks.estimate_step(obs, prev)
        mem = ks.initial_memory() if prev is None else prev["memory"]
        try:
            decision, m2 = ks.decide_step(copy.deepcopy(est), mem, obs["safety"], obs["counters"]["steps_left"])
        except NotImplementedError:
            decision, m2 = "NONE", mem
        calls = plan.get("calls", [("move", {"action": plan.get("decision", decision)})]
                         if plan.get("decision", decision) in vd.MOVES else [])
        if len(msgs) == 1:
            first = list(est["calls"]) + [("exploration_summary", {"pose": est["pose"]})]
            return _resp([_Block(type="thinking", thinking="", signature="s")]
                         + [_tool(i, n, a) for i, (n, a) in enumerate(first)], "tool_use")
        if len(msgs) == 3 and calls:
            return _resp([_tool(100 + i, n, a) for i, (n, a) in enumerate(calls)], "tool_use")
        if "final" in plan:
            return _resp([_Block(type="text", text=plan["final"])], "end_turn")
        results = [json.loads(b["content"]) for b in msgs[-1]["content"]] if len(msgs) > 3 else []
        moved = [r.get("result") for r in results if isinstance(r, dict) and "result" in r]
        for e in est["new_entries"]:
            e["first_seen_scan"] = m2["scan_index"]
        report = {"step": obs["step"], "mode": "closed_loop", "mission": "EXPLORE", "pose": ks.rp(est["pose"]),
                  "pose_source": est["pose_source"],
                  "associations": [{k: v for k, v in a.items() if k != "conflict"} for a, _ in est["assoc"]],
                  "loop_closure": est["loop_closure"], "map": est["new_map"], "memory": m2,
                  "decision": plan.get("decision", decision), "move_result": moved[-1] if moved else "not_called",
                  "requested_mission": None, "message": None, "note": "scripted"}
        return _resp([_Block(type="text", text=json.dumps(report))], "end_turn")


def _run(tmp_path, script=None, seed=1010, max_steps=6, budget=None, price=None, name="ep", client=None, env=None, **kw):
    client = client or ScriptedModel(script)
    agent = cl.AnthropicDriver(client, "scripted", OPUS[0], price or OPUS[1])
    budget = budget or rp.Budget(float("inf"))
    path = tmp_path / (name + ".jsonl")
    res = cl.run_episode(agent, "SYSTEM", env or cl.KinsimSquareEnv(), seed, path, budget, max_steps, NOLOG, config="t", **kw)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    return res, rows, client, budget


TO_THE_WALL = {0: {"decision": "FORWARD_25"}, 1: {"decision": "FORWARD_25"}, 2: {"decision": "FORWARD_25"},
               3: {"decision": "FORWARD_10"}}


# ---------------------------------------------------------------- the scripted model through the full loop

def test_allowed_move_is_executed_and_shapes_the_next_observation(tmp_path):
    res, rows, client, _ = _run(tmp_path, {0: {"decision": "FORWARD_25"}, 1: {"decision": "TURN_LEFT_30"}}, max_steps=3)
    assert res == {"complete": True, "ended_by": "budget", "detail": "max_steps", "steps": 3}
    r0, r1, r2 = rows
    assert r0["truth"] == {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0} and r0["observation"]["last_move"] is None
    assert r0["executed_move"]["action"] == "FORWARD_25" and r0["executed_move"]["result"] == "done"
    assert r0["move_calls"] == [{"action": "FORWARD_25", "tool_result": "done", "tool_reason": None,
                                 "validator_ok": True, "validator_reason": None, "agree": True}]
    assert r0["report"]["move_result"] == "done" and r0["violations"] == []
    assert r1["truth"]["x_m"] == pytest.approx(0.25) and r1["truth"]["theta_deg"] == 0.0
    assert r1["observation"]["last_move"] == {"action": "FORWARD_25", "result": "done"}
    assert r1["observation"]["odometry"]["forward_m"] == r0["executed_move"]["odometry"]["forward_m"] != 0
    assert r1["observation"]["safety"]["backward_allowed"] is True
    assert r2["truth"]["theta_deg"] == pytest.approx(30.0) and r2["observation"]["safety"]["backward_allowed"] is False
    assert r2["observation"]["counters"]["steps_left"] == cl.STEPS_BUDGET - 2
    assert all(r["mode"] == "closed_loop" and r["observation"]["mode"] == "closed_loop" for r in rows)


def test_refused_forward_at_the_wall_then_a_second_choice(tmp_path):
    script = dict(TO_THE_WALL)
    script[4] = {"calls": [("move", {"action": "FORWARD_25"}), ("move", {"action": "FORWARD_10"}),
                           ("move", {"action": "TURN_LEFT_30"})], "decision": "TURN_LEFT_30"}
    res, rows, _, _ = _run(tmp_path, script, max_steps=6)
    r4, r5 = rows[4], rows[5]
    assert r4["truth"]["x_m"] == pytest.approx(0.85) and r4["observation"]["safety"]["forward_allowed"] == []
    assert [(v["action"], v["tool_result"], v["tool_reason"]) for v in r4["move_calls"]] == [
        ("FORWARD_25", "refused", "not in forward_allowed"), ("FORWARD_10", "refused", "not in forward_allowed"),
        ("TURN_LEFT_30", "done", None)]
    assert all(v["agree"] for v in r4["move_calls"])
    assert r4["executed_move"]["action"] == "TURN_LEFT_30"
    assert [v["code"] for v in r4["violations"]] == ["guardrail", "guardrail"]
    assert r5["truth"]["x_m"] == pytest.approx(0.85) and r5["truth"]["theta_deg"] == pytest.approx(30.0)
    assert r5["observation"]["last_move"] == {"action": "TURN_LEFT_30", "result": "done"}


def test_only_refused_moves_nothing_executes_and_the_next_observation_says_so(tmp_path):
    script = dict(TO_THE_WALL)
    script[4] = {"calls": [("move", {"action": "FORWARD_25"})], "decision": "FORWARD_25"}
    res, rows, _, _ = _run(tmp_path, script, max_steps=6)
    r4, r5 = rows[4], rows[5]
    assert r4["executed_move"] is None and r4["report"]["move_result"] == "refused"
    assert {v["code"] for v in r4["violations"]} == {"guardrail", "decision_mismatch"}
    assert r5["truth"] == r4["truth"]
    assert r5["observation"]["last_move"] == {"action": "FORWARD_25", "result": "refused"}
    assert r5["observation"]["odometry"] == {"forward_m": 0.0, "left_m": 0.0, "dtheta_deg": 0.0, "quality": "ok"}
    assert r5["observation"]["safety"]["backward_allowed"] is False
    assert r5["observation"]["counters"]["odometer_m"] == r4["observation"]["counters"]["odometer_m"]
    assert r5["observation"]["counters"]["turns_since_fix"] == r4["observation"]["counters"]["turns_since_fix"]


def test_move_decision_without_a_move_call_is_not_executed(tmp_path):
    res, rows, _, _ = _run(tmp_path, {1: {"calls": [], "decision": "FORWARD_25"}}, max_steps=3)
    assert rows[1]["executed_move"] is None and rows[1]["move_calls"] == []
    assert [v["code"] for v in rows[1]["violations"]] == ["decision_mismatch"]
    assert rows[2]["truth"] == rows[1]["truth"]
    assert rows[2]["observation"]["last_move"] == {"action": "FORWARD_25", "result": "not_called"}


def test_report_decision_differs_from_the_accepted_move(tmp_path):
    res, rows, _, _ = _run(tmp_path, {0: {"calls": [("move", {"action": "TURN_RIGHT_30"})], "decision": "FORWARD_25"}},
                           max_steps=2)
    assert rows[0]["executed_move"]["action"] == "TURN_RIGHT_30" and rows[0]["decision"] == "FORWARD_25"
    assert [v["code"] for v in rows[0]["violations"]] == ["decision_mismatch"]
    assert rows[1]["truth"]["theta_deg"] == pytest.approx(-30.0) and rows[1]["truth"]["x_m"] == 0.0


def test_move_after_the_latch_is_refused_and_the_episode_ends_latched(tmp_path):
    script = {1: {"calls": [("emergency_stop", {"reason": "test inconsistency"}), ("move", {"action": "TURN_LEFT_30"})],
                  "decision": "STOPPED"}}
    res, rows, _, _ = _run(tmp_path, script, max_steps=6)
    assert res["complete"] and res["ended_by"] == "latch" and res["steps"] == 2
    r1 = rows[1]
    assert r1["move_calls"][0]["tool_reason"] == "latched" and r1["move_calls"][0]["validator_reason"] == "latched"
    assert r1["executed_move"] is None and r1["validator"]["latched"] is True
    assert "test inconsistency" in r1["validator"]["latch_reason"]
    assert r1["episode_end"] == {"ended_by": "latch", "detail": r1["validator"]["latch_reason"]}
    latch = tmp_path / "ep.LATCH"
    assert vd.read_latch_file(latch)["by"] == "agent"
    again = cl.run_episode(cl.B2Driver(), "", cl.KinsimSquareEnv(), 1010, tmp_path / "ep.jsonl", rp.Budget(1e9), 6, NOLOG, config="t")
    assert again == res                                    # a finished episode is not continued


def test_a_latched_episode_without_an_end_row_is_not_resumed(tmp_path):
    _run(tmp_path, max_steps=2)
    vd.write_latch_file(tmp_path / "ep.LATCH", "operator stop", "operator")
    rows = (tmp_path / "ep.jsonl").read_text().splitlines()
    last = json.loads(rows[-1])
    last["episode_end"] = None
    (tmp_path / "ep.jsonl").write_text("\n".join(rows[:-1] + [json.dumps(last)]) + "\n")
    with pytest.raises(RuntimeError, match="latched"):
        _run(tmp_path, max_steps=4)


def test_done_ends_the_episode(tmp_path):
    res, rows, client, _ = _run(tmp_path, {2: {"decision": "DONE"}}, max_steps=10)
    assert res == {"complete": True, "ended_by": "DONE", "detail": "decision", "steps": 3}
    assert rows[2]["executed_move"] is None and rows[2]["report"]["move_result"] == "not_called"
    assert rows[2]["episode_end"] == {"ended_by": "DONE", "detail": "decision"} and rows[1]["episode_end"] is None
    assert max(json.loads(q["messages"][0]["content"][0]["text"])["OBSERVATION"]["step"] for q in client.requests) == 2


def test_stopped_ends_the_episode(tmp_path):
    res, rows, _, _ = _run(tmp_path, {1: {"decision": "STOPPED"}}, max_steps=10)
    assert (res["ended_by"], res["steps"]) == ("STOPPED", 2)


def test_malformed_report_gets_the_replay_fallback(tmp_path):
    script = {0: {"decision": "FORWARD_25"}, 1: {"calls": [], "final": "I think I should turn left."},
              2: {"calls": [("move", {"action": "TURN_LEFT_30"})], "final": '{"step": 2, "pose": "lost"}'}}
    res, rows, _, _ = _run(tmp_path, script, max_steps=4)
    r1, r2, r3 = rows[1], rows[2], rows[3]
    want = rp.fallback_report(r1["prev_report"], r1["raw"]["odometry"], 1)
    assert r1["fallback"] is True and r1["report"] is None and r1["next_prev"] == want
    assert r1["estimate_pose"] == want["pose"] and r1["decision"] == "NONE" and r1["counter_source"] == "odometry"
    assert r1["executed_move"] is None and r1["violations"][0]["code"] == "format"
    assert r2["prev_report"] == want and r2["observation"]["last_move"] is None
    # an invalid report after an accepted move: the move the tool reported `done` is executed all the same
    assert r2["fallback"] is True and r2["checks"]["parses"] is True and r2["checks"]["pose_numeric"] is False
    assert r2["executed_move"]["action"] == "TURN_LEFT_30" and r2["decision"] == "NONE"
    assert {v["code"] for v in r2["violations"]} == {"format", "decision_mismatch"}
    assert r3["truth"]["theta_deg"] == pytest.approx(30.0)
    assert r3["observation"]["last_move"] == {"action": "TURN_LEFT_30", "result": "done"}
    assert r3["prev_report"]["note"].startswith("harness fallback")


def test_repaired_report_counts_as_valid(tmp_path):
    client = ScriptedModel()
    whole = client.create

    def cut(**kw):
        resp = whole(**kw)
        if resp.stop_reason == "end_turn":
            resp.content[0].text = resp.content[0].text[:-1]            # the closing brace is missing
        return resp
    client.create = cut
    res, rows, _, _ = _run(tmp_path, max_steps=2, client=client)
    assert all(r["checks"]["valid"] and r["checks"]["repaired_chars"] == 1 and not r["fallback"] for r in rows)
    assert rows[0]["executed_move"] is not None


def test_three_steps_without_a_move_end_the_episode(tmp_path):
    script = {s: {"calls": [], "decision": "ASK"} for s in range(1, 9)}
    res, rows, _, _ = _run(tmp_path, script, max_steps=10)
    assert res["ended_by"] == "error" and res["detail"].startswith("no_progress: 3 consecutive steps") and res["steps"] == 4
    assert [r["executed_move"] is None for r in rows] == [False, True, True, True]
    assert rows[2]["observation"]["last_move"] is None
    # sensing again without moving gives a new observation of the same pose, with zero odometry
    assert rows[2]["truth"] == rows[1]["truth"] and rows[2]["observation"]["odometry"]["forward_m"] == 0.0


def test_step_budget_ends_a_full_length_episode(tmp_path):
    script = {s: {"decision": "TURN_LEFT_30"} for s in range(cl.STEPS_BUDGET)}
    res, rows, _, _ = _run(tmp_path, script, max_steps=cl.STEPS_BUDGET)
    assert res == {"complete": True, "ended_by": "budget", "detail": "steps", "steps": 150}
    assert rows[-1]["observation"]["counters"]["steps_left"] == 1 and rows[-1]["executed_move"]["action"] == "TURN_LEFT_30"


# ---------------------------------------------------------------- money, failures, resume

def test_usd_cap_stops_before_the_step_and_a_resume_matches_an_uninterrupted_run(tmp_path):
    full, rows_full, _, _ = _run(tmp_path, max_steps=8, name="full")
    step_cost = rows_full[0]["cost_usd"]
    assert step_cost == pytest.approx(3 * am.turn_cost(USAGE), abs=2e-5) and step_cost > 0
    spend = tmp_path / "spend.jsonl"
    res, rows, _, budget = _run(tmp_path, max_steps=8, name="cut", budget=rp.Budget(step_cost * 2.5, path=spend))
    # 2.5 steps of money: the cap is met during step 2 (after its second turn), so step 2 is not written
    assert res == {"complete": False, "ended_by": None, "detail": "usd cap", "steps": 2} and len(rows) == 2
    assert budget.spent == pytest.approx(rp.spent_in(spend)) and budget.spent >= step_cost * 2.5
    res2, rows2, _, _ = _run(tmp_path, max_steps=8, name="cut", budget=rp.Budget(1e9, rp.spent_in(spend), path=spend))
    assert res2 == full

    def strip(rows_):
        return [{k: v for k, v in r.items() if k not in ("seconds", "turns")} for r in rows_]
    assert strip(rows2) == strip(rows_full)


def test_cap_reached_inside_a_step_leaves_it_unwritten_and_unexecuted(tmp_path):
    one_turn = am.turn_cost(USAGE)
    res, rows, _, _ = _run(tmp_path, max_steps=5, budget=rp.Budget(one_turn * 4.5))   # step 0: 3 turns; step 1: 2 turns
    assert res["complete"] is False and res["steps"] == 1 and len(rows) == 1
    res2, rows2, _, _ = _run(tmp_path, max_steps=5)
    _, rows_full, _, _ = _run(tmp_path, max_steps=5, name="full")
    assert [r["truth"] for r in rows2] == [r["truth"] for r in rows_full]


def test_provider_failure_writes_nothing_and_moves_nothing(tmp_path):
    with pytest.raises(RuntimeError, match="server on fire"):
        _run(tmp_path, {2: {"raise": RuntimeError("server on fire")}}, max_steps=5)
    lines = (tmp_path / "ep.jsonl").read_text().splitlines()
    assert len(lines) == 2 and all(json.loads(x)["episode_end"] is None for x in lines)
    res, rows, _, _ = _run(tmp_path, max_steps=5)                       # the rerun resumes at step 2
    _, rows_full, _, _ = _run(tmp_path, max_steps=5, name="full")
    assert res["complete"] and [r["truth"] for r in rows] == [r["truth"] for r in rows_full]
    assert [r["raw"] for r in rows] == [r["raw"] for r in rows_full]


def test_torn_last_line_is_dropped_on_resume(tmp_path):
    _run(tmp_path, max_steps=2)
    path = tmp_path / "ep.jsonl"
    lines = path.read_text().splitlines()
    path.write_text(lines[0] + "\n" + lines[1][:200])
    res, rows, _, _ = _run(tmp_path, max_steps=2)
    assert res["steps"] == 2 and len(rows) == 2 and rows[1]["step"] == 1


def test_resume_refuses_a_log_the_simulator_does_not_reproduce(tmp_path):
    _run(tmp_path, max_steps=3)
    path = tmp_path / "ep.jsonl"
    rows = [json.loads(x) for x in path.read_text().splitlines()]
    rows[-1]["episode_end"] = None
    rows[1]["raw"]["detections"] = []
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    with pytest.raises(cl.ResumeMismatch):
        _run(tmp_path, max_steps=5)
    with pytest.raises(ValueError, match="another configuration"):
        cl.run_episode(cl.B2Driver(), "", cl.KinsimSquareEnv(), 1010, path, rp.Budget(1e9), 5, NOLOG, config="other")


def test_another_models_price_is_what_the_budget_counts(tmp_path):
    spend = tmp_path / "spend.jsonl"
    res, rows, _, budget = _run(tmp_path, max_steps=2, price=FABLE_PRICE, budget=rp.Budget(1e9, path=spend))
    turn = (1000 * 8 + 300 * 10 + 5000 * 0.2 + 200 * 40) / 1e6
    assert cl.price_cost(USAGE, FABLE_PRICE) == pytest.approx(turn) and turn > am.turn_cost(USAGE)
    assert all(t["cost_usd"] == pytest.approx(turn, abs=1e-5) for r in rows for t in r["turns"])
    n_turns = sum(len(r["turns"]) for r in rows)
    assert budget.spent == pytest.approx(n_turns * turn) == pytest.approx(rp.spent_in(spend))
    assert sum(r["cost_usd"] for r in rows) == pytest.approx(n_turns * turn, abs=1e-4)
    assert cl.price_cost(USAGE, am.PRICE) == pytest.approx(am.turn_cost(USAGE))


def test_request_settings_reach_the_api_unchanged_and_carry_no_truth(tmp_path):
    settings = {"model": "claude-fable-5-2", "max_tokens": 64000, "output_config": {"effort": "medium"}}
    client = ScriptedModel()
    agent = cl.AnthropicDriver(client, "claude-fable-5-2", settings, FABLE_PRICE)
    env = cl.KinsimSquareEnv()
    cl.run_episode(agent, "SYSTEM", env, 1010, tmp_path / "e.jsonl", rp.Budget(1e9), 4, NOLOG)
    assert agent.arm == "L2:claude-fable-5-2" and agent.header()["settings"] == settings
    rows = [json.loads(x) for x in (tmp_path / "e.jsonl").read_text().splitlines()]
    for q in client.requests:
        assert set(q) == {"model", "max_tokens", "output_config", "system", "tools", "messages"}
        assert {k: q[k] for k in settings} == settings
        assert q["system"] == [{"type": "text", "text": "SYSTEM", "cache_control": {"type": "ephemeral"}}]
        user = json.loads(q["messages"][0]["content"][0]["text"])
        row = rows[user["OBSERVATION"]["step"]]
        assert q["messages"][0]["content"][0]["text"] == rp.step_message(row["observation"], row["prev_report"])
        sent = json.dumps(q, default=lambda o: getattr(o, "__dict__", str(o)))
        assert "_tag" not in sent and "truth" not in sent and '"wall"' not in sent
    assert any(d.get("_tag") is not None for r in rows for d in r["raw"]["detections"])     # truth stays in the log only
    assert all("_tag" not in d for r in rows for d in r["observation"]["detections"])


# ---------------------------------------------------------------- B2 through the same loop

@pytest.mark.parametrize("seed", [1003, 1010])
def test_b2_closed_loop_reproduces_kinsim_lite_run_episode(tmp_path, seed):
    ref = ks.run_episode(seed)
    env = cl.KinsimSquareEnv()
    path = tmp_path / "b2.jsonl"
    res = cl.run_episode(cl.B2Driver(), "", env, seed, path, rp.Budget(float("inf")), log=NOLOG)
    rows = [json.loads(x) for x in path.read_text().splitlines()]
    assert res == {"complete": True, "ended_by": "DONE", "detail": "decision", "steps": len(ref["records"])}
    assert env.world == ref["world"]
    for row, rec in zip(rows, ref["records"]):
        assert row["truth"] == rec["truth"] and row["raw"] == rec["raw"] and row["report"] == rec["report"]
        assert [[c["tool"], c["args"]] for c in row["calls"] if c["tool"] in mc.ESTIMATION_TOOLS] == \
            json.loads(json.dumps(rec["calls"]))
        assert not row["fallback"] and row["violations"] == []
        assert (row["executed_move"] or {}).get("action") == (rec["report"]["decision"] if rec["report"]["decision"] != "DONE" else None)
    s = mc.summarize(rows, env.world)
    assert s["tools"]["f1"] == 1.0 and s["procedure_agreement"] == {"steps_compared": len(rows), "decision": 1.0, "memory": 1.0}
    assert s["moves_executed"] == len(rows) - 1 and s["refused_move_calls"] == 0 and s["fallbacks"] == 0
    assert s["state_violations"]["pose_bad"] == 0 and s["state_violations"]["map_entries_bad"] == 0
    assert "| ATE (cm) |" in mc.table([s])


def test_scripted_model_following_the_procedure_equals_b2(tmp_path):
    """The model path (provider tool loop, parse, validator) and the B2 driver give the same episode."""
    res, rows, _, _ = _run(tmp_path, seed=1010, max_steps=cl.STEPS_BUDGET)
    ref = ks.run_episode(1010)
    assert res["ended_by"] == "DONE" and len(rows) == len(ref["records"])
    assert [r["truth"] for r in rows] == [r["truth"] for r in ref["records"]]
    assert [r["raw"] for r in rows] == [r["raw"] for r in ref["records"]]


def test_b2_resume_after_a_cut_log(tmp_path):
    env = cl.KinsimSquareEnv()
    path = tmp_path / "b2.jsonl"
    cl.run_episode(cl.B2Driver(), "", env, 1003, path, rp.Budget(1e9), log=NOLOG)
    whole = path.read_text()
    path.write_text("".join(x + "\n" for x in whole.splitlines()[:37]))
    cl.run_episode(cl.B2Driver(), "", cl.KinsimSquareEnv(), 1003, path, rp.Budget(1e9), log=NOLOG)

    def strip(text):
        return [{k: v for k, v in json.loads(x).items() if k != "seconds"} for x in text.splitlines()]
    assert strip(path.read_text()) == strip(whole)


def test_b2_in_the_room_reproduces_the_room_simulators_own_episode(tmp_path):
    kr = pytest.importorskip("beaconmind.envs.kinsim_room")
    world = beaconmind.course_root() / "configs" / "arenas" / "real-room-nominal.json"
    if not world.exists():
        pytest.skip("no room world file")
    ref = kr.run_episode(kr.KinSimEnv.room(str(world)), 1)
    env = cl.room_env(str(world))
    path = tmp_path / "room.jsonl"
    res = cl.run_episode(cl.B2Driver(), "", env, 1, path, rp.Budget(1e9), log=NOLOG)
    rows = [json.loads(x) for x in path.read_text().splitlines()]
    assert len(rows) == len(ref["records"]) and res["complete"]
    for row, rec in zip(rows, ref["records"]):
        assert row["truth"] == rec["truth"] and row["raw"] == rec["raw"] and row["report"] == rec["report"]
    json.dumps(env.describe(), default=list)                              # run.json can hold it


def test_room_env_idle_step_and_executor_refusal(tmp_path):
    pytest.importorskip("beaconmind.envs.kinsim_room")
    world = beaconmind.course_root() / "configs" / "arenas" / "real-room-nominal.json"
    if not world.exists():
        pytest.skip("no room world file")
    env = cl.room_env(str(world))
    env.reset(3)
    before = env.truth()
    idle = env.step(None)
    assert env.truth() == before and idle["move"] is None and idle["odometry"]["forward_m"] == 0.0
    back = env.step("BACKWARD_10")                                        # not allowed: no forward move before it
    assert back["move"]["result"] == "refused" and env.truth() == before
    turn = env.step("TURN_LEFT_30")
    assert turn["move"] == {"action": "TURN_LEFT_30", "result": "done", "reason": None}


# ---------------------------------------------------------------- environment behaviour the validator relies on

def test_square_env_refuses_what_the_validator_would_and_backs_up(tmp_path):
    env = cl.KinsimSquareEnv()
    env.reset(1010)
    for a in ("FORWARD_25", "FORWARD_25", "FORWARD_25", "FORWARD_10"):
        assert env.step(a)["move"]["result"] == "done"
    at_wall = env.truth()
    sense = env.step("FORWARD_10")
    assert sense["move"]["result"] == "refused" and env.truth() == at_wall and sense["odometry"]["forward_m"] == 0.0
    env.step("TURN_LEFT_30")
    assert env.step("BACKWARD_10")["move"]["result"] == "refused"        # the last move was not a forward move
    env2 = cl.KinsimSquareEnv()
    env2.reset(1010)
    env2.step("FORWARD_10")
    back = env2.step("BACKWARD_10")
    assert back["move"]["result"] == "done" and back["odometry"]["forward_m"] < 0
    assert env2.truth()["x_m"] == pytest.approx(0.0, abs=1e-9)
    with pytest.raises(ValueError):
        env2.step("DONE")


class StallingEnv(cl.KinsimSquareEnv):
    """Every forward move stalls (a contact): the car does not move."""

    def step(self, action):
        if action and action.startswith("FORWARD"):
            return self._sense({"forward_m": 0.0, "left_m": 0.0, "dtheta_deg": 0.0},
                               {"action": action, "result": "stalled", "reason": "stall"})
        return super().step(action)


def test_two_contacts_latch_the_episode(tmp_path):
    script = {s: {"decision": "FORWARD_25"} for s in range(5)}
    res, rows, _, _ = _run(tmp_path, script, max_steps=5, env=StallingEnv())
    assert res["ended_by"] == "latch" and res["steps"] == 2 and "2 consecutive contacts" in res["detail"]
    assert rows[1]["observation"]["last_move"] == {"action": "FORWARD_25", "result": "stalled"}
    assert rows[1]["observation"]["counters"]["consecutive_contacts"] == 1
    assert rows[1]["observation"]["counters"]["latched"] is False
    assert rows[1]["observation"]["safety"]["backward_allowed"] is True
    assert rows[1]["truth"] == rows[0]["truth"] and (tmp_path / "ep.LATCH").exists()


# ---------------------------------------------------------------- logs against the contracts

def test_logs_validate_against_the_schemas(tmp_path):
    script = dict(TO_THE_WALL)
    script[4] = {"calls": [("move", {"action": "FORWARD_25"}), ("move", {"action": "TURN_LEFT_30"})], "decision": "TURN_LEFT_30"}
    script[5] = {"calls": [], "final": "garbage"}
    script[6] = {"decision": "DONE"}
    res, rows, _, _ = _run(tmp_path, script, max_steps=10)
    lines = cl.to_runlog(rows, "run-x", "seed_1010")
    assert len(lines) == len(rows) + 1 and lines[-1]["type"] == "episode_footer" and lines[-1]["ended_by"] == "DONE"
    for line in lines:
        assert validate("runlog", line) == []
    for r, line in zip(rows, lines):
        assert validate("observation", r["observation"]) == []
        assert validate("step", line["step_message"]) == []
        assert line["step_message"] == json.loads(rp.step_message(r["observation"], r["prev_report"]))
        if r["executed_move"]:
            assert validate("move", r["executed_move"]["command"]) == []
            assert validate("move_result", line["executed_move"]["result"]) == []
        if r["report"] and not r["fallback"]:
            assert validate("report", r["report"]) == []
        assert sum(len(t["tool_calls"]) for t in line["llm_turns"]) == len(r["calls"])
        assert [len(t["tool_calls"]) for t in line["llm_turns"]] == [t["tool_uses"] for t in r["turns"]]
    assert lines[4]["llm_turns"][1]["tool_calls"][0]["result"] == {"result": "refused", "reason": "not in forward_allowed"}
    assert lines[5]["report"] is None and lines[5]["report_corrected"]["note"].startswith("harness fallback")
    assert lines[-1]["totals"]["cost_usd"] == pytest.approx(sum(r["cost_usd"] for r in rows), abs=1e-4)
    b2 = tmp_path / "b2.jsonl"
    cl.run_episode(cl.B2Driver(), "", cl.KinsimSquareEnv(), 1010, b2, rp.Budget(1e9), log=NOLOG)
    for line in cl.to_runlog([json.loads(x) for x in b2.read_text().splitlines()], "run-b2", "seed_1010"):
        assert validate("runlog", line) == [] and line.get("llm_turns", []) == []


def test_summary_counts_moves_refusals_and_fallbacks(tmp_path):
    script = dict(TO_THE_WALL)
    script[4] = {"calls": [("move", {"action": "FORWARD_25"}), ("move", {"action": "TURN_LEFT_30"})], "decision": "TURN_LEFT_30"}
    script[5] = {"calls": [], "final": "garbage"}
    script[6] = {"decision": "DONE"}
    res, rows, _, _ = _run(tmp_path, script, max_steps=10)
    s = mc.summarize(rows, ks.make_world(1010))
    assert s["steps"] == 7 and s["ended_by"] == "DONE" and s["moves_executed"] == 5
    assert s["moves_by_type"] == {"FORWARD_10": 1, "FORWARD_25": 3, "TURN_LEFT_30": 1}
    assert s["refused_move_calls"] == 1 and s["refused_by_reason"] == {"not in forward_allowed": 1}
    assert s["fallbacks"] == 1 and s["steps_without_move"] == 2 and s["move_calls"] == 6
    assert s["path_length_m"] == pytest.approx(sum(abs((r["raw"]["odometry"] or {}).get("forward_m", 0)) for r in rows))
    assert s["cost_usd"] == pytest.approx(sum(r["cost_usd"] for r in rows)) and s["tokens"]["out"] == 200 * sum(len(r["turns"]) for r in rows)
    assert s["pose"]["ate_m"] >= 0 and s["b0"]["ate_m"] >= 0 and s["tools"]["by_tool"]["move"] == 6
    with pytest.raises(ValueError):
        mc.summarize(rows[1:], ks.make_world(1010))


# ---------------------------------------------------------------- for the real car: no way around the validator, no way past a latch

def test_emergency_stop_after_an_accepted_move_cancels_the_move(tmp_path):
    script = {1: {"calls": [("move", {"action": "FORWARD_25"}), ("emergency_stop", {"reason": "changed my mind"})],
                  "decision": "FORWARD_25"}}
    res, rows, _, _ = _run(tmp_path, script, max_steps=5)
    r1 = rows[1]
    assert res["ended_by"] == "latch" and res["steps"] == 2
    assert r1["move_calls"][0]["tool_result"] == "done" and r1["move_calls"][0]["validator_ok"] is True
    assert r1["executed_move"] is None
    assert [v for v in r1["violations"] if v["code"] == "validator_override"][0]["detail"].endswith("latched")
    assert r1["next_last_move"] == {"action": "FORWARD_25", "result": "refused"}
    journal = (tmp_path / "ep.moves.jsonl").read_text().splitlines()
    assert [json.loads(x)["step"] for x in journal] == [0, 0]                 # only step 0's move reached the executor


def test_latch_file_appearing_while_the_model_thinks_stops_the_move(tmp_path):
    client = ScriptedModel({s: {"decision": "TURN_LEFT_30"} for s in range(5)})
    inner = client.create

    def create(**kw):
        resp = inner(**kw)
        step = json.loads(kw["messages"][0]["content"][0]["text"])["OBSERVATION"]["step"]
        if step == 2 and resp.stop_reason == "end_turn":
            vd.write_latch_file(tmp_path / "ep.LATCH", "out-of-band STOP", "operator")
        return resp
    client.create = create
    res, rows, _, _ = _run(tmp_path, max_steps=5, client=client)
    r2 = rows[2]
    assert res["ended_by"] == "latch" and res["steps"] == 3 and "out-of-band STOP" in res["detail"]
    assert r2["observation"]["counters"]["latched"] is False and r2["move_calls"][0]["tool_result"] == "done"
    assert r2["executed_move"] is None and r2["validator"]["latched"] is True
    assert vd.read_latch_file(tmp_path / "ep.LATCH")["by"] == "operator"      # the operator's file is not overwritten
    with pytest.raises(RuntimeError, match="latched"):
        cl.run_episode(cl.B2Driver(), "", cl.KinsimSquareEnv(), 1010, tmp_path / "other.jsonl", rp.Budget(1e9), 5, NOLOG,
                       watch_latch_paths=[tmp_path / "ep.LATCH"])


def test_watched_latch_file_between_steps_gives_a_latched_observation_and_no_motion(tmp_path):
    project = tmp_path / "LATCH"
    client = ScriptedModel({s: {"decision": "TURN_LEFT_30"} for s in range(6)})
    agent = cl.AnthropicDriver(client, "scripted", OPUS[0], OPUS[1])
    env = cl.KinsimSquareEnv()
    seen = []
    real_step = env.step

    def step(action):
        seen.append(action)
        if len(seen) == 2:
            project.write_text("stop")                      # appears after the second move was executed
        return real_step(action)
    env.step = step
    path = tmp_path / "ep.jsonl"
    res = cl.run_episode(agent, "S", env, 1010, path, rp.Budget(1e9), 6, NOLOG, watch_latch_paths=[project])
    rows = [json.loads(x) for x in path.read_text().splitlines()]
    assert res["ended_by"] == "latch" and res["steps"] == 3 and seen == ["TURN_LEFT_30", "TURN_LEFT_30"]
    r2 = rows[2]
    assert r2["observation"]["counters"]["latched"] is True
    assert r2["move_calls"] == [{"action": "TURN_LEFT_30", "tool_result": "refused", "tool_reason": "latched",
                                 "validator_ok": False, "validator_reason": "latched", "agree": True}]
    assert r2["executed_move"] is None and not (tmp_path / "ep.LATCH").exists()


class RealLikeEnv(cl.KinsimSquareEnv):
    """Stands for a real car: it cannot be re-simulated."""
    deterministic_replay = False


def test_an_environment_that_cannot_be_resimulated_is_never_resumed(tmp_path):
    env = RealLikeEnv()
    calls = []
    real_step = env.step
    env.step = lambda a: (calls.append(a), real_step(a))[1]
    res, rows, _, _ = _run(tmp_path, max_steps=3, env=env)
    assert res["complete"] and len(calls) == 3
    lines = (tmp_path / "ep.jsonl").read_text().splitlines()
    last = json.loads(lines[-1])
    last["episode_end"] = None
    (tmp_path / "ep.jsonl").write_text("\n".join(lines[:-1] + [json.dumps(last)]) + "\n")
    env2 = RealLikeEnv()
    moved = []
    env2.step = lambda a: moved.append(a)
    with pytest.raises(cl.ResumeMismatch, match="cannot be re-simulated"):
        _run(tmp_path, max_steps=6, env=env2)
    assert moved == []                                       # a resume would have driven the three logged moves again


def test_an_executor_that_does_not_confirm_the_move_stops_the_episode(tmp_path):
    class Liar(cl.KinsimSquareEnv):
        def step(self, action):
            sense = super().step(action)
            if action == "FORWARD_25":
                sense["move"] = {"action": "TURN_LEFT_30", "result": "done", "reason": None}
            return sense
    with pytest.raises(RuntimeError, match="did not report the commanded move"):
        _run(tmp_path, {0: {"decision": "TURN_LEFT_30"}, 1: {"decision": "FORWARD_25"}}, max_steps=4, env=Liar())
    assert len((tmp_path / "ep.jsonl").read_text().splitlines()) == 1
    journal = [json.loads(x) for x in (tmp_path / "ep.moves.jsonl").read_text().splitlines()]
    assert [(j["step"], j["phase"], j["action"]) for j in journal] == [
        (0, "commanded", "TURN_LEFT_30"), (0, "result", "TURN_LEFT_30"), (1, "commanded", "FORWARD_25")]


class FlakyEnv(cl.KinsimSquareEnv):
    """Reports error observations at the given steps and a reboot (null odometry) at `reboot_at`."""

    def __init__(self, errors=(), reboot_at=None):
        super().__init__()
        self.errors, self.reboot_at, self.n = set(errors), reboot_at, 0

    def _sense(self, odo, move):
        sense = super()._sense(odo, move)
        if self.n in self.errors:
            sensors = {"camera": "stale", "imu": "ok", "pico": "armed"}
            if self.n % 2:                                   # the backend's form and the flat form, both accepted
                sense["status"] = {"status": "error", "error": "camera stale", "sensors": sensors, "odometry_quality": "ok"}
            else:
                sense.update(status="error", error="camera stale", sensors=sensors)
        if self.n == self.reboot_at:
            sense["odometry"] = None
        self.n += 1
        return sense


def test_error_observation_refuses_the_move_and_two_in_a_row_latch(tmp_path):
    script = {s: {"decision": "TURN_LEFT_30"} for s in range(8)}
    res, rows, _, _ = _run(tmp_path, script, max_steps=8, env=FlakyEnv(errors=(1, 3, 4)))
    r1 = rows[1]
    assert r1["observation"]["status"] == "error" and r1["observation"]["error"] == "camera stale"
    assert r1["observation"]["sensors"]["camera"] == "stale" and validate("observation", r1["observation"]) == []
    # the frozen tool does not look at status and answers done; the validator refuses before execution
    assert r1["move_calls"][0]["tool_result"] == "done" and r1["move_calls"][0]["validator_reason"] == "status error"
    assert r1["executed_move"] is None and rows[2]["truth"] == r1["truth"]
    assert rows[2]["observation"]["last_move"] == {"action": "TURN_LEFT_30", "result": "refused"}
    assert rows[2]["observation"]["counters"]["consecutive_errors"] == 0 and rows[2]["executed_move"] is not None
    assert rows[3]["observation"]["counters"] | {} == rows[3]["observation"]["counters"] and rows[3]["executed_move"] is None
    r4 = rows[4]
    assert res["ended_by"] == "latch" and res["steps"] == 5 and "2 consecutive error observations" in res["detail"]
    assert r4["observation"]["counters"]["latched"] is True and r4["observation"]["counters"]["consecutive_errors"] == 2
    assert r4["move_calls"][0]["tool_reason"] == "latched" and r4["executed_move"] is None


def test_null_odometry_after_step_0_latches_before_the_model_is_asked(tmp_path):
    script = {s: {"decision": "TURN_LEFT_30"} for s in range(6)}
    res, rows, _, _ = _run(tmp_path, script, max_steps=6, env=FlakyEnv(reboot_at=2))
    assert res["ended_by"] == "latch" and res["steps"] == 3 and "Pico reboot" in res["detail"]
    r2 = rows[2]
    assert r2["observation"]["odometry"] is None and r2["observation"]["counters"]["latched"] is True
    assert r2["executed_move"] is None and r2["move_calls"][0]["validator_reason"] == "latched"
    assert (tmp_path / "ep.LATCH").exists()


def test_fuzz_nothing_reaches_the_executor_without_passing_the_validator(tmp_path):
    """A model that calls anything: random sequences of valid, invalid and repeated move calls and emergency stops.
    Every action the environment receives must be one check_move allows for the observation of that step, and
    nothing may be sent once a latch is set."""
    import random
    rng = random.Random(20261118)
    pool = list(vd.MOVES) * 2 + ["DONE", "forward_25", "FORWARD_50", "", None, 7]
    total_sent = total_refused = 0
    for trial in range(12):
        script = {}
        for s in range(40):
            calls = [("move", {"action": rng.choice(pool)}) for _ in range(rng.randint(0, 4))]
            if rng.random() < 0.015:
                calls.insert(rng.randint(0, len(calls)), ("emergency_stop", {"reason": "fuzz"}))
            script[s] = {"calls": calls, "decision": rng.choice(list(vd.DECISIONS[:5]) + ["NONE"])}
            if rng.random() < 0.1:
                script[s]["final"] = rng.choice(["", "{", '{"decision": "FORWARD_25"}', "FORWARD_25"])
        env = cl.KinsimSquareEnv()
        sent = []
        real_step = env.step

        def step(action, _real=real_step, _sent=sent):
            _sent.append(action)
            return _real(action)
        env.step = step
        res, rows, _, _ = _run(tmp_path, script, seed=1000 + trial, max_steps=40, name="fuzz%d" % trial, env=env,
                               max_idle_steps=1000)
        executed = [r["executed_move"]["action"] for r in rows if r["executed_move"]]
        assert [a for a in sent if a is not None] == executed
        latched_at = next((r["step"] for r in rows if r["validator"]["latched"]), None)
        for r in rows:
            ok_calls = [v for v in r["move_calls"] if v["tool_result"] == "done"]
            assert len(ok_calls) <= 1 and all(v["agree"] for v in r["move_calls"])
            total_refused += sum(1 for v in r["move_calls"] if v["tool_result"] != "done")
            if r["executed_move"]:
                a = r["executed_move"]["action"]
                assert vd.check_move(a, r["observation"]) == (True, None)
                assert ok_calls and ok_calls[0]["action"] == a and ok_calls[0]["validator_ok"]
                assert r["executed_move"]["result"] == "done"        # the executor's own wall check never had to refuse
                assert latched_at is None or r["step"] < latched_at
                total_sent += 1
        if latched_at is not None:
            assert rows[-1]["step"] == latched_at and res["ended_by"] == "latch"
        assert all(-1.0 < r["truth"]["x_m"] < 1.25 and -1.0 < r["truth"]["y_m"] < 1.25 for r in rows)
    assert total_sent > 100 and total_refused > 100
