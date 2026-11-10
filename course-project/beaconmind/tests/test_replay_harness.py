"""Tests of the provider-neutral replay loop (harness/replay.py) and the OpenAI-compatible provider.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote these tests.
"""
import copy
import json
import types

import pytest

from beaconmind.envs import kinsim_lite as ks
from beaconmind.harness import replay as rp
from beaconmind.harness import tools_d5 as t5

openai = pytest.importorskip("openai")
from beaconmind.harness.providers import openai_chat as oc  # noqa: E402


@pytest.fixture(scope="module")
def episode():
    return ks.run_episode(1003)


# ---------------------------------------------------------------- mock OpenAI-compatible server

def _msg(content=None, tool_calls=None, reasoning=None, field="reasoning_content"):
    tcs = None
    if tool_calls:
        tcs = [types.SimpleNamespace(id="call_%d" % i, type="function",
                                     function=types.SimpleNamespace(name=n, arguments=a if isinstance(a, str) else json.dumps(a)))
               for i, (n, a) in enumerate(tool_calls)]
    m = types.SimpleNamespace(content=content, tool_calls=tcs, model_extra={field: reasoning} if reasoning else {})
    return m


class _Usage:
    def __init__(self, p=100, c=10, cached=0):
        self.d = {"prompt_tokens": p, "completion_tokens": c, "prompt_tokens_details": {"cached_tokens": cached}}

    def model_dump(self):
        return self.d


def _resp(message, finish="stop"):
    return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message, finish_reason=finish)],
                                 usage=_Usage(), model="mock-model")


class _Client:
    """chat.completions.create(**kw) -> next scripted response; keeps every request."""

    def __init__(self, script):
        self.script, self.requests = list(script), []
        self.chat = types.SimpleNamespace(completions=self)

    def create(self, **kw):
        self.requests.append(copy.deepcopy(kw))
        nxt = self.script.pop(0)
        return nxt(kw) if callable(nxt) else nxt


class _ProcedureClient:
    """A model that runs the coded procedure: on each step it calls exactly B2's tools (the gold calls on
    the step message it received) and then answers with the procedure's report for that input."""

    def __init__(self):
        self.requests = []
        self.chat = types.SimpleNamespace(completions=self)

    def create(self, **kw):
        self.requests.append(kw)
        msgs = kw["messages"]
        user = json.loads(msgs[1]["content"])
        obs, prev = user["OBSERVATION"], user["PREVIOUS_REPORT"]
        est = ks.estimate_step(obs, prev)
        if len(msgs) == 2:
            return _resp(_msg(tool_calls=list(est["calls"]), reasoning="I follow the procedure."), "tool_calls")
        return _resp(_msg(content=json.dumps(self._report(kw))))

    def _report(self, kw):
        user = json.loads(kw["messages"][1]["content"])
        obs, prev = user["OBSERVATION"], user["PREVIOUS_REPORT"]
        est = ks.estimate_step(obs, prev)
        mem = ks.initial_memory() if prev is None else prev["memory"]
        report = {"step": obs["step"], "mode": "replay", "mission": "EXPLORE", "pose": ks.rp(est["pose"]),
                  "pose_source": est["pose_source"],
                  "associations": [{k: v for k, v in a.items() if k != "conflict"} for a, _ in est["assoc"]],
                  "loop_closure": est["loop_closure"], "map": est["new_map"], "memory": mem, "decision": "NONE",
                  "move_result": "not_called", "requested_mission": None, "message": None, "note": "procedure"}
        return report


CFG = {"provider": "vllm", "model": "mock-model", "base_url": "http://127.0.0.1:1/v1", "thinking": True,
       "sampling": {"temperature": 1.0, "top_p": 0.95, "top_k": 20}, "max_turns_per_step": 30,
       "options": {"max_tokens": 64000, "chat_template_kwargs": {"enable_thinking": True, "reasoning_effort": "xhigh"},
                   "reasoning_replay_field": "reasoning"}}


def _obs(episode, i):
    raw = episode["records"][i]["raw"]
    return ks.as_observation(1003, raw, {"odometer_m": 0.0, "travel_since_fix_m": 0.0, "turns_since_fix": 0})


# ---------------------------------------------------------------- the OpenAI provider

def test_request_carries_sampling_template_kwargs_and_seed():
    agent = oc.OpenAIChatAgent(None, "k", CFG, repeat=2)
    kw = agent.request([{"role": "user", "content": "x"}], 123)
    assert kw["temperature"] == 1.0 and kw["top_p"] == 0.95 and kw["max_tokens"] == 64000 and kw["seed"] == 123
    assert kw["extra_body"] == {"top_k": 20, "chat_template_kwargs": {"enable_thinking": True, "reasoning_effort": "xhigh"}}
    assert [t["function"]["name"] for t in kw["tools"]] == [d["name"] for d in t5.anthropic_tool_defs()]
    # an Ollama-style entry sends no sampling and no template kwargs
    ol = dict(CFG, provider="ollama", sampling={}, options={"max_tokens": 64000, "reasoning_replay_field": "reasoning"})
    kw2 = oc.OpenAIChatAgent(None, "g", ol).request([], 7)
    assert "temperature" not in kw2 and "extra_body" not in kw2


def test_sample_seed_depends_on_key_turn_and_repeat():
    s = oc.sample_seed("2000-5", 0, 0)
    assert s == oc.sample_seed("2000-5", 0, 0) and 0 <= s < 2 ** 31
    assert len({s, oc.sample_seed("2000-5", 1, 0), oc.sample_seed("2000-5", 0, 1), oc.sample_seed("2000-6", 0, 0)}) == 4


def test_tool_loop_sends_reasoning_back_in_the_template_field(episode):
    obs = _obs(episode, 0)
    pose = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
    client = _Client([_resp(_msg(tool_calls=[("map_point", {"pose": pose, "det": 0})] if obs["detections"] else
                                 [("exploration_summary", {"pose": pose})], reasoning="think A"), "tool_calls"),
                      _resp(_msg(content='{"pose": {"x_m": 0, "y_m": 0, "theta_deg": 0}, "map": []}', reasoning="think B"))])
    out = oc.OpenAIChatAgent(client, "k", CFG).step("SYS", obs, None, rp.Budget(1.0), lambda m: None, sample_key="1003-0")
    assert out["error"] is None and out["final_text"].startswith("{") and len(out["calls"]) == 1
    assert out["calls"][0]["result"].get("status") != "error"
    second = client.requests[1]["messages"]
    assert second[0] == {"role": "system", "content": "SYS"}
    assert second[2]["role"] == "assistant" and second[2]["reasoning"] == "think A" and "reasoning_content" not in second[2]
    assert "<think>" not in second[2]["content"]
    assert second[3]["role"] == "tool" and second[3]["tool_call_id"] == "call_0"
    assert [t["reasoning"] for t in out["turns"]] == ["think A", "think B"] and out["cost_usd"] == 0.0
    assert client.requests[0]["seed"] != client.requests[1]["seed"]


def test_length_finish_executes_no_partial_tool_call(episode):
    obs = _obs(episode, 0)
    client = _Client([_resp(_msg(tool_calls=[("emergency_stop", {"reason": "x"})]), "length")])
    out = oc.OpenAIChatAgent(client, "k", CFG).step("SYS", obs, None, rp.Budget(1.0), lambda m: None)
    assert out["error"].startswith("length") and out["calls"] == [] and out["state"]["estop"] is False


def test_bad_arguments_are_an_error_result_not_a_crash(episode):
    obs = _obs(episode, 0)
    client = _Client([_resp(_msg(tool_calls=[("compose_odometry", "{not json")]), "tool_calls"),
                      _resp(_msg(content="done"))])
    out = oc.OpenAIChatAgent(client, "k", CFG).step("SYS", obs, None, rp.Budget(1.0), lambda m: None)
    c = out["calls"][0]
    assert c["result"]["status"] == "error" and c["args_raw"] == "{not json" and c["args"] == {}


def test_turn_cap(episode):
    obs = _obs(episode, 0)
    cfg = dict(CFG, max_turns_per_step=3)
    pose = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
    client = _Client([_resp(_msg(tool_calls=[("exploration_summary", {"pose": pose})]), "tool_calls")] * 3)
    out = oc.OpenAIChatAgent(client, "k", cfg).step("SYS", obs, None, rp.Budget(1.0), lambda m: None)
    assert out["error"] == "turn cap" and len(out["turns"]) == 3 and out["final_text"] is None


def test_retry_then_success(monkeypatch, episode):
    obs = _obs(episode, 0)
    monkeypatch.setattr(oc.time, "sleep", lambda s: None)
    def boom(kw):
        raise openai.APIConnectionError(request=None)   # the SDK's own request type differs across versions
    client = _Client([boom, _resp(_msg(content="{}"))])
    logs = []
    out = oc.OpenAIChatAgent(client, "k", CFG).step("SYS", obs, None, rp.Budget(1.0), logs.append)
    assert out["error"] is None and out["final_text"] == "{}" and any("retry" in m for m in logs)


# ---------------------------------------------------------------- the replay loop

def test_procedure_model_reproduces_b2_counters_and_reports(episode, tmp_path):
    """A model that executes B2's gold calls and reports B2's estimate: every claimed fix is verified, so the
    harness counters equal the counters B2 itself used, and every pose equals B2's pose."""
    agent = oc.OpenAIChatAgent(_ProcedureClient(), "proc", CFG)
    out = tmp_path / "seed.jsonl"
    n = len(episode["records"])                  # seed 1003's first full fix is at step 61
    assert rp.replay_seed(agent, "SYS", episode, out, rp.Budget(1.0), n, log=lambda m: None)
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert [r["step"] for r in rows] == list(range(n))
    fixes = 0
    for r, rec in zip(rows, episode["records"]):
        assert r["checks"]["valid"] and not r["fallback"]
        for k in ("travel_since_fix_m", "turns_since_fix", "odometer_m"):
            assert r["observation"]["counters"][k] == rec["raw"]["counters"][k], (r["step"], k)
        assert r["estimate_pose"] == rec["report"]["pose"]
        if rec["report"]["pose_source"] == "beacon_fix":
            fixes += 1
            assert r["fix_verified"] is True and r["counter_source"] == "beacon_fix"
        else:
            assert r["fix_verified"] is None
    assert fixes >= 3


def _fix_step(episode):
    """The first B2 step with a full fix: its report, observation, previous report and B2's own tool calls."""
    rec = next(r for r in episode["records"] if r["report"]["pose_source"] == "beacon_fix")
    obs = ks.as_observation(1003, rec["raw"], rec["raw"]["counters"])
    prev = episode["records"][rec["step"] - 1]["report"]
    st = {"moved": None, "estop": False}
    calls = [{"tool": n, "args": a, "result": t5.rnd(t5.run_tool(n, a, obs, prev, st))}
             for n, a in ks.estimate_step(obs, prev)["calls"]]
    return rec["report"], obs, prev, calls


def test_verify_fix_rules(episode):
    rep, obs, prev, calls = _fix_step(episode)
    prior = rp.harness_prior(obs, prev)
    assert rp.verify_fix(rep, calls, prior) == ("beacon_fix", True)
    # no fix_pose call, a moved pose, or a fix_pose given another prior: not verified
    assert rp.verify_fix(rep, [c for c in calls if c["tool"] != "fix_pose"], prior) == ("unverified_fix", False)
    moved = dict(rep, pose=dict(rep["pose"], x_m=rep["pose"]["x_m"] + 0.05))
    assert rp.verify_fix(moved, calls, prior) == ("unverified_fix", False)
    fp = next(c for c in calls if c["tool"] == "fix_pose")
    other_prior = dict(fp, args=dict(fp["args"], prior=dict(fp["args"]["prior"], x_m=fp["args"]["prior"]["x_m"] + 0.2)))
    assert rp.verify_fix(rep, [other_prior], prior) == ("unverified_fix", False)
    assert rp.verify_fix(rep, [other_prior], None) == ("beacon_fix", True)          # prior check off
    # an error result and a full = None result are skipped, a later good call still verifies
    err = {"tool": "fix_pose", "args": fp["args"], "result": {"status": "error", "error": "x"}}
    nofull = {"tool": "fix_pose", "args": fp["args"], "result": dict(fp["result"], full=None)}
    assert rp.verify_fix(rep, [err, nofull, fp], prior) == ("beacon_fix", True)
    # relocalised needs relocalisation_ok
    full = fp["result"]["full"]
    reloc = dict(rep, pose_source="relocalised")
    ok = {"tool": "fix_pose", "args": fp["args"], "result": {"full": dict(full, relocalisation_ok=True)}}
    no = {"tool": "fix_pose", "args": fp["args"], "result": {"full": dict(full, relocalisation_ok=False)}}
    assert rp.verify_fix(reloc, [ok], prior) == ("relocalised", True)
    assert rp.verify_fix(reloc, [no], prior) == ("unverified_fix", False)
    assert rp.verify_fix(dict(rep, pose_source="odometry"), calls, prior) == ("odometry", None)
    tr = ks.CounterTracker()
    tr.travel, tr.turns = 0.5, 3
    tr.before_step({"odometry": None, "last_move": None}, "unverified_fix")
    assert (tr.travel, tr.turns) == (0.5, 3)


def test_claim_without_a_fix_keeps_the_counters_growing(episode, tmp_path):
    """A model that reports B2's poses and sources but never calls fix_pose: its claimed fixes are not verified."""
    class Claimer(_ProcedureClient):
        def create(self, **kw):
            r = super().create(**kw)
            m = r.choices[0].message
            if m.tool_calls:
                m.tool_calls = [tc for tc in m.tool_calls if tc.function.name != "fix_pose"] or None
                if m.tool_calls is None:
                    return _resp(_msg(content=json.dumps(self._report(kw))))
            return r
    agent = oc.OpenAIChatAgent(Claimer(), "claim", CFG)
    out = tmp_path / "c.jsonl"
    assert rp.replay_seed(agent, "SYS", episode, out, rp.Budget(1.0), 70, log=lambda m: None)
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    fixes = [r for r in rows if (r["report"] or {}).get("pose_source") == "beacon_fix"]
    assert fixes and all(r["fix_verified"] is False for r in fixes)
    first = fixes[0]["step"]
    assert rows[first + 1]["observation"]["counters"]["travel_since_fix_m"] > 0 or \
        rows[first + 1]["observation"]["counters"]["turns_since_fix"] > 0


def test_invalid_and_non_finite_reports_fall_back(episode, tmp_path):
    bad = [_resp(_msg(content="not json")), _resp(_msg(content='{"pose": {"x_m": NaN, "y_m": 0, "theta_deg": 0}, "map": []}'))]
    agent = oc.OpenAIChatAgent(_Client(bad), "k", CFG)
    out = tmp_path / "s.jsonl"
    assert rp.replay_seed(agent, "SYS", episode, out, rp.Budget(1.0), 2, log=lambda m: None)
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert all(r["fallback"] and not r["checks"]["valid"] for r in rows)
    assert rows[1]["estimate_pose"] == ks.rp(ks.g.compose_odometry({"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0},
                                                                   **{k: episode["records"][1]["raw"]["odometry"][k]
                                                                      for k in ("forward_m", "left_m", "dtheta_deg")}))


def test_resume_across_fixes_equals_an_uninterrupted_run(episode, tmp_path):
    """Cut the run after step 62 (seed 1003's first full fix is step 61) and resume: every row equals the
    uninterrupted run's, so the restored counter source, previous and last valid report are right."""
    full = tmp_path / "full.jsonl"
    cut = tmp_path / "cut.jsonl"
    n = len(episode["records"])
    assert rp.replay_seed(oc.OpenAIChatAgent(_ProcedureClient(), "p", CFG), "SYS", episode, full, rp.Budget(1.0), n,
                          log=lambda m: None)
    assert rp.replay_seed(oc.OpenAIChatAgent(_ProcedureClient(), "p", CFG), "SYS", episode, cut, rp.Budget(1.0), 63,
                          log=lambda m: None)
    assert rp.replay_seed(oc.OpenAIChatAgent(_ProcedureClient(), "p", CFG), "SYS", episode, cut, rp.Budget(1.0), n,
                          log=lambda m: None)
    a = [json.loads(line) for line in full.read_text().splitlines()]
    b = [json.loads(line) for line in cut.read_text().splitlines()]
    keys = ("observation", "prev_report", "next_prev", "last_valid", "counter_source", "fix_verified", "estimate_pose")
    assert len(a) == len(b) == n
    for x, y in zip(a, b):
        assert all(x[k] == y[k] for k in keys), x["step"]


def test_torn_last_line_is_cut_and_the_run_resumes(episode, tmp_path):
    out = tmp_path / "t.jsonl"
    agent = oc.OpenAIChatAgent(_ProcedureClient(), "p", CFG)
    assert rp.replay_seed(agent, "SYS", episode, out, rp.Budget(1.0), 5, log=lambda m: None)
    with open(out, "a") as fh:
        fh.write('{"seed": 1003, "step": 5, "trunc')
    logs = []
    assert rp.replay_seed(agent, "SYS", episode, out, rp.Budget(1.0), 8, log=logs.append)
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert [r["step"] for r in rows] == list(range(8)) and any("torn" in m for m in logs)


def test_config_tag_refuses_mixing(episode, tmp_path):
    out = tmp_path / "m.jsonl"
    agent = oc.OpenAIChatAgent(_ProcedureClient(), "p", CFG)
    assert rp.replay_seed(agent, "SYS", episode, out, rp.Budget(1.0), 3, log=lambda m: None, config="aaa")
    with pytest.raises(ValueError, match="another configuration"):
        rp.replay_seed(agent, "SYS", episode, out, rp.Budget(1.0), 6, log=lambda m: None, config="bbb")


class _BadRequest(openai.BadRequestError):
    def __init__(self, msg):            # the SDK's constructor needs an HTTP response; tests only need the text
        Exception.__init__(self, msg)
        self.status_code = 400


def test_context_overflow_is_a_fallback_but_other_400s_raise(episode, tmp_path):
    obs = _obs(episode, 0)

    def overflow(kw):
        raise _BadRequest("This model's maximum context length is 1000 tokens")
    out = oc.OpenAIChatAgent(_Client([overflow]), "k", CFG).step("SYS", obs, None, rp.Budget(1.0), lambda m: None)
    assert out["error"].startswith("context overflow") and out["final_text"] is None

    def malformed(kw):
        raise _BadRequest("invalid tool schema")
    with pytest.raises(openai.BadRequestError):
        oc.OpenAIChatAgent(_Client([malformed]), "k", CFG).step("SYS", obs, None, rp.Budget(1.0), lambda m: None)
    # in the replay loop a malformed request writes no row (a rerun resumes the step)
    path = tmp_path / "x.jsonl"
    with pytest.raises(openai.BadRequestError):
        rp.replay_seed(oc.OpenAIChatAgent(_Client([malformed]), "k", CFG), "SYS", episode, path, rp.Budget(1.0), 2,
                       log=lambda m: None)
    assert not path.exists() or path.read_text() == ""


def test_timeouts_retry_three_times_then_raise(monkeypatch, episode):
    monkeypatch.setattr(oc.time, "sleep", lambda s: None)
    obs = _obs(episode, 0)

    def slow(kw):
        raise openai.APITimeoutError(request=None)
    client = _Client([slow] * 10)
    with pytest.raises(RuntimeError, match="timed out 3 times"):
        oc.OpenAIChatAgent(client, "k", CFG).step("SYS", obs, None, rp.Budget(1.0), lambda m: None)
    assert len(client.requests) == 3


def test_unknown_finish_reason_ends_the_step_without_tools(episode):
    obs = _obs(episode, 0)
    client = _Client([_resp(_msg(tool_calls=[("emergency_stop", {"reason": "x"})]), "abort")])
    out = oc.OpenAIChatAgent(client, "k", CFG).step("SYS", obs, None, rp.Budget(1.0), lambda m: None)
    assert out["error"] == "finish: abort" and out["calls"] == [] and not out["state"]["estop"]


def test_turn_records_carry_normalised_tokens(episode):
    obs = _obs(episode, 0)
    out = oc.OpenAIChatAgent(_Client([_resp(_msg(content="{}"))]), "k", CFG).step("SYS", obs, None, rp.Budget(1.0),
                                                                                   lambda m: None)
    assert out["turns"][0]["tokens"] == {"in": 100, "cached_in": 0, "out": 10, "reasoning": None}
    assert out["turns"][0]["finish"] == "stop"


def test_budget_spend_file(tmp_path):
    p = tmp_path / "spend.jsonl"
    b = rp.Budget(1.0, path=p)
    b.add(0.25)
    b.add(0.0)
    b.add(0.5)
    with open(p, "a") as fh:
        fh.write('{"t": 1, "us')            # a torn line is ignored
    assert rp.spent_in(p) == pytest.approx(0.75) and rp.spent_in(tmp_path / "none") == 0.0


def test_state_violations(episode):
    from beaconmind.metrics import pilot as pm
    rep, obs, prev, calls = _fix_step(episode)
    row = {"report": rep, "checks": {"valid": True}, "calls": calls, "prev_report": prev,
           "harness_prior": rp.harness_prior(obs, prev)}
    sv = pm.state_violations(row)
    assert sv["pose"] is True and sv["map_bad"] == 0 and sv["map_checked"] == len(rep["map"])
    bad_pose = dict(row, report=dict(rep, pose=dict(rep["pose"], y_m=rep["pose"]["y_m"] + 0.03)))
    assert pm.state_violations(bad_pose)["pose"] is False
    moved_map = [dict(b, x_m=b["x_m"] + 0.1) if i == 0 else b for i, b in enumerate(rep["map"])]
    assert pm.state_violations(dict(row, report=dict(rep, map=moved_map)))["map_bad"] == 1


def test_huge_integer_is_not_a_number():
    assert t5._num(10 ** 400) is False and t5._num(1.5) is True and t5._num(float("nan")) is False
