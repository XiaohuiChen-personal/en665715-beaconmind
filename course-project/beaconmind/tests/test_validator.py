"""Tests of the closed-loop validator (harness/validator.py): move checks, the dispatcher parity, the latch.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote these tests.
"""
import copy
import itertools

import pytest

from beaconmind.envs import kinsim_lite as ks
from beaconmind.harness import tools_d5 as t5
from beaconmind.harness import validator as vd


def _obs(forward=("FORWARD_25", "FORWARD_10"), backward=False, turn=True, latched=False, status="ok", steps_left=100,
         mode="closed_loop"):
    raw = {"step": 3, "odometry": {"forward_m": 0.25, "left_m": 0.0, "dtheta_deg": 0.0},
           "last_move": {"action": "FORWARD_25", "result": "done"},
           "counters": {"steps_left": steps_left, "odometer_m": 0.25, "travel_since_fix_m": 0.25, "turns_since_fix": 0},
           "safety": {"forward_allowed": list(forward), "backward_allowed": backward, "turn_allowed": turn,
                      "scan_allowed": True}, "detections": []}
    obs = ks.as_observation(7, raw, raw["counters"], mode=mode)
    obs["counters"]["latched"] = latched
    obs["status"] = status
    return obs


def test_allowed_moves_pass():
    obs = _obs(backward=True)
    for a in vd.MOVES:
        assert vd.check_move(a, obs) == (True, None)


@pytest.mark.parametrize("action,kw,reason", [
    ("FORWARD_25", {"forward": ("FORWARD_10",)}, "not in forward_allowed"),
    ("FORWARD_10", {"forward": ()}, "not in forward_allowed"),
    ("BACKWARD_10", {}, "backward not allowed"),
    ("TURN_LEFT_30", {"turn": False}, "turn not allowed"),
    ("TURN_RIGHT_30", {"latched": True}, "latched"),
    ("JUMP", {}, "not a move"),
    (None, {}, "not a move"),
    ("DONE", {}, "not a move"),
    ("TURN_LEFT_30", {"status": "error"}, "status error"),
    ("TURN_LEFT_30", {"steps_left": 0}, "no steps left"),
    ("TURN_LEFT_30", {"mode": "replay"}, "replay mode: the log's move is already executed"),
])
def test_refusals_and_reasons(action, kw, reason):
    assert vd.check_move(action, _obs(**kw)) == (False, reason)


def test_second_move_and_estop_refused():
    obs = _obs()
    assert vd.check_move("TURN_LEFT_30", obs, moved="FORWARD_25") == (False, "one executed move per obs_id")
    assert vd.check_move("TURN_LEFT_30", obs, estop=True) == (False, "latched")


def test_same_answer_as_the_frozen_dispatcher():
    """For every case the frozen `move` tool knows, the validator gives the same verdict and the same reason."""
    n = 0
    for fwd, back, turn, latched, mode in itertools.product(
            [(), ("FORWARD_10",), ("FORWARD_25", "FORWARD_10")], [False, True], [False, True], [False, True],
            ["closed_loop", "replay"]):
        obs = _obs(forward=fwd, backward=back, turn=turn, latched=latched, mode=mode)
        for moved, estop in itertools.product([None, "TURN_LEFT_30"], [False, True]):
            for action in vd.MOVES + ("DONE", "SPIN"):
                state = {"moved": moved, "estop": estop}
                tool = t5.run_tool("move", {"action": action}, obs, None, copy.deepcopy(state))
                ok, reason = vd.check_move(action, obs, moved=moved, estop=estop)
                assert ok == (tool["result"] == "done"), (action, obs["safety"], state)
                assert reason == tool["reason"]
                n += 1
    assert n == 3 * 2 * 2 * 2 * 2 * 4 * 7


def test_audit_follows_call_order():
    obs = _obs(forward=("FORWARD_10",))
    state, calls = {"moved": None, "estop": False}, []
    for name, args in (("move", {"action": "FORWARD_25"}), ("move", {"action": "FORWARD_10"}),
                       ("move", {"action": "TURN_LEFT_30"}), ("emergency_stop", {"reason": "test"}),
                       ("move", {"action": "TURN_LEFT_30"})):
        calls.append({"tool": name, "args": args, "result": t5.run_tool(name, args, obs, None, state)})
    verdicts, accepted = vd.audit_move_calls(calls, obs)
    assert [v["tool_result"] for v in verdicts] == ["refused", "done", "refused", "refused"]
    assert [v["validator_reason"] for v in verdicts] == ["not in forward_allowed", None, "one executed move per obs_id",
                                                         "latched"]
    assert all(v["agree"] for v in verdicts) and accepted["action"] == "FORWARD_10" and state["moved"] == "FORWARD_10"


def test_audit_overrules_what_the_dispatcher_does_not_check():
    """The frozen tool does not look at status or steps_left; the validator refuses before execution."""
    for kw, reason in (({"status": "error"}, "status error"), ({"steps_left": 0}, "no steps left")):
        obs = _obs(**kw)
        state = {"moved": None, "estop": False}
        calls = [{"tool": "move", "args": {"action": "TURN_LEFT_30"},
                  "result": t5.run_tool("move", {"action": "TURN_LEFT_30"}, obs, None, state)}]
        verdicts, accepted = vd.audit_move_calls(calls, obs)
        assert accepted["tool_result"] == "done" and not accepted["validator_ok"] and not accepted["agree"]
        assert accepted["validator_reason"] == reason


def test_audit_survives_malformed_calls():
    obs = _obs()
    calls = [{"tool": "move", "args": None, "result": {"status": "error", "error": "TypeError. Nothing changed."}},
             {"tool": "move", "args": {"action": 5}, "result": {"result": "refused", "reason": "not a move"}}]
    verdicts, accepted = vd.audit_move_calls(calls, obs)
    assert accepted is None and [v["tool_result"] for v in verdicts] == ["error", "refused"]
    assert not any(v["validator_ok"] for v in verdicts)


def test_safety_block_backward_rule_and_env_flags():
    v = vd.Validator()
    env = {"forward_allowed": ["FORWARD_10", "FORWARD_25", "WARP"]}
    assert v.safety(env) == {"forward_allowed": ["FORWARD_25", "FORWARD_10"], "backward_allowed": False,
                             "turn_allowed": True, "scan_allowed": True}
    v.after_step({"action": "FORWARD_25", "result": "done"})
    assert v.safety(env)["backward_allowed"] is True
    assert v.safety(dict(env, backward_allowed=False))["backward_allowed"] is False
    v.after_step({"action": "TURN_LEFT_30", "result": "done"})
    assert v.safety(env)["backward_allowed"] is False
    v.after_step({"action": "FORWARD_10", "result": "stalled"})
    assert v.safety(env)["backward_allowed"] is True
    v.after_step(None)                                     # a step without a move: no longer "directly after"
    assert v.safety(env)["backward_allowed"] is False
    v.after_step({"action": "FORWARD_10", "result": "refused"})
    assert v.safety(env)["backward_allowed"] is False
    assert v.safety({"forward_allowed": [], "turn_allowed": False, "scan_allowed": False}) == {
        "forward_allowed": [], "backward_allowed": False, "turn_allowed": False, "scan_allowed": False}


def test_autolatch_after_two_consecutive_contacts(tmp_path):
    latch = tmp_path / "ep.LATCH"
    v = vd.Validator(autolatch_contacts=2, latch_path=latch)
    v.after_step({"action": "FORWARD_25", "result": "stalled"})
    assert not v.latched and v.counters() == {"consecutive_contacts": 1, "consecutive_errors": 0, "latched": False}
    v.after_step({"action": "BACKWARD_10", "result": "done"})          # a completed move clears the count
    v.after_step({"action": "FORWARD_25", "result": "bumped"})
    v.after_step(None)                                                  # no move: the count stays
    assert not v.latched and v.consecutive_contacts == 1
    v.after_step({"action": "FORWARD_10", "result": "stalled"})
    assert v.latched and "2 consecutive contacts" in v.latch_reason
    assert vd.read_latch_file(latch)["by"] == "validator"


def test_link_lost_latches_at_once():
    v = vd.Validator()
    v.after_step({"action": "TURN_LEFT_30", "result": "link_lost"})
    assert v.latched and v.latch_reason == "auto: link_lost"


def test_latch_file_needs_an_operator_to_clear(tmp_path):
    latch = tmp_path / "ep.LATCH"
    v = vd.Validator(latch_path=latch)
    v.latch("emergency_stop: test", by="agent")
    v.latch("second reason is ignored", by="agent")
    assert vd.read_latch_file(latch)["reason"] == "emergency_stop: test"
    with pytest.raises(ValueError):
        vd.clear_latch_file(latch, " ")
    assert latch.exists()
    assert vd.clear_latch_file(latch, "Xiaohui") is True
    assert not latch.exists() and vd.read_latch_file(latch) is None
    assert vd.clear_latch_file(latch, "Xiaohui") is False
    assert "Xiaohui" in (tmp_path / "ep.LATCH.cleared.jsonl").read_text()


# ---------------------------------------------------------------- fail closed; latch sources beyond contacts

def test_malformed_flags_refuse_instead_of_allowing():
    """A flag that is missing or has the wrong type must never read as permission."""
    base = _obs(backward=True)

    def broken(path, value="__missing__"):
        obs = copy.deepcopy(base)
        d = obs
        for k in path[:-1]:
            d = d[k]
        if value == "__missing__":
            d.pop(path[-1])
        else:
            d[path[-1]] = value
        return obs

    assert vd.check_move("TURN_LEFT_30", broken(("counters", "latched"))) == (False, "latched")
    assert vd.check_move("TURN_LEFT_30", broken(("counters", "latched"), "false")) == (False, "latched")
    assert vd.check_move("TURN_LEFT_30", broken(("counters", "latched"), None)) == (False, "latched")
    assert vd.check_move("TURN_LEFT_30", broken(("counters", "steps_left"))) == (False, "no steps left")
    assert vd.check_move("TURN_LEFT_30", broken(("counters", "steps_left"), "12")) == (False, "no steps left")
    assert vd.check_move("TURN_LEFT_30", broken(("counters", "steps_left"), True)) == (False, "no steps left")
    assert vd.check_move("TURN_LEFT_30", broken(("safety", "turn_allowed"))) == (False, "turn not allowed")
    assert vd.check_move("TURN_LEFT_30", broken(("safety", "turn_allowed"), "yes")) == (False, "turn not allowed")
    assert vd.check_move("BACKWARD_10", broken(("safety", "backward_allowed"), 1)) == (False, "backward not allowed")
    assert vd.check_move("FORWARD_25", broken(("safety", "forward_allowed"))) == (False, "not in forward_allowed")
    assert vd.check_move("FORWARD_25", broken(("safety", "forward_allowed"), "FORWARD_25 FORWARD_10")) == (False, "not in forward_allowed")
    assert vd.check_move("FORWARD_25", broken(("safety", "forward_allowed"), None)) == (False, "not in forward_allowed")
    assert vd.check_move("TURN_LEFT_30", broken(("status",))) == (False, "status error")
    assert vd.check_move("TURN_LEFT_30", broken(("mode",)))[0] is False
    assert vd.check_move("TURN_LEFT_30", broken(("mode",), "CLOSED_LOOP"))[0] is False
    for path in (("counters",), ("safety",)):
        with pytest.raises(KeyError):
            vd.check_move("TURN_LEFT_30", broken(path))
    for action in ("turn_left_30", " TURN_LEFT_30", "TURN_LEFT_30 ", ["TURN_LEFT_30"], {"action": "TURN_LEFT_30"}, 30, True):
        assert vd.check_move(action, base) == (False, "not a move")


def test_poll_obeys_latch_files_written_by_someone_else(tmp_path):
    own, project = tmp_path / "ep.LATCH", tmp_path / "LATCH"
    v = vd.Validator(latch_path=own, watch_paths=[project])
    assert v.poll() is False and not v.latched
    project.write_text("")                                   # an operator's `touch`: unreadable, still a latch
    assert v.poll() is True and v.latched and "LATCH" in v.latch_reason
    assert not own.exists()                                  # obeying a latch does not write another one
    v2 = vd.Validator(latch_path=own)
    vd.write_latch_file(own, "out-of-band STOP", "operator")
    assert v2.poll() is True and "out-of-band STOP" in v2.latch_reason
    assert vd.read_latch_file(tmp_path / "none") is None
    (tmp_path / "list.LATCH").write_text("[1, 2]")
    assert vd.read_latch_file(tmp_path / "list.LATCH")["latched"] is True


def test_reboot_and_repeated_errors_latch():
    v = vd.Validator()
    v.note_observation(0, "ok", True)                        # null odometry at step 0 is the start, not a reboot
    assert not v.latched
    v.note_observation(1, "error", False)
    assert not v.latched and v.counters()["consecutive_errors"] == 1
    v.note_observation(2, "ok", False)
    v.note_observation(3, "error", False)
    assert not v.latched and v.consecutive_errors == 1
    v.note_observation(4, "error", False)
    assert v.latched and v.latch_reason == "auto: 2 consecutive error observations"
    v2 = vd.Validator()
    v2.note_observation(5, "ok", True)
    assert v2.latched and "Pico reboot" in v2.latch_reason
