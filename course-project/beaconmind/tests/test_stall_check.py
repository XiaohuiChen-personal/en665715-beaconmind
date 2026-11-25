"""tools/stall_check.py: the stall classifier for a halted batch (read-only).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote these tests.
"""
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def load_tool():
    spec = importlib.util.spec_from_file_location("stall_check", ROOT / "tools" / "stall_check.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    return tool


def move_log(path, right_speeds, left_speed, duties, yaw_rate_dps, cut=0, bump=False):
    """A TURN_LEFT_30 move log: telemetry every 20 ms with the right wheel at the given speeds (m/s) and duties, the
    left wheel backward at left_speed, the yaw turning at yaw_rate_dps; a stall_right stop after the last sample."""
    rows = [{"ev": "header", "cmd": {"action": "TURN_LEFT_30"}, "config": {"ticks_per_m_left": 19385.0, "ticks_per_m_right": 19804.0}},
            {"ev": "start", "t": 0.0}]
    t, l, r, yaw = 0.0, 0.0, 0.0, -50.0
    for v, d in zip(right_speeds, duties):
        t += 0.02
        l -= left_speed * 0.02 * 19385
        r += v * 0.02 * 19804
        yaw += yaw_rate_dps * 0.02
        rows.append({"ev": "tel", "t_rx": t, "l": int(round(l)), "r": int(round(r)), "yaw": yaw, "duty": [-d, d], "cut": cut})
    rows.append({"ev": "stop", "t": t, "result": "stalled", "reason": "stall_right"})
    rows.append({"ev": "result", "t": t + 0.3, "result": {"result": "stalled", "reason": "stall_right", "bump": bump}})
    path.write_text("\n".join(json.dumps(x) for x in rows) + "\n")


def batch(tmp_path, pose):
    b = tmp_path / "batch"
    ep = b / "episodes" / "ep01-a1" / "post"
    ep.mkdir(parents=True)
    (b / "manifest.json").write_text(json.dumps({
        "status": "halted", "halt": {"detail": "TURN_LEFT_30: stall_right"},
        "params": {"world_path": "configs/arenas/real-room.json", "wall_margin_m": 0.15, "sigma_block_m": 0.25}}))
    step = {"step": 7, "t_unix": 1.0, "executed": {"result": {"result": "stalled"}}}
    truth = {"row": 7, "tracked_world": {"pose": pose, "sigma_xy_m": 0.05}}
    (ep / "steps.jsonl").write_text(json.dumps(step) + "\n")
    (ep / "truth.jsonl").write_text(json.dumps(truth) + "\n")
    return b


def test_b2_real_03s_kind_of_stall_is_marginal_duty_and_clear(tmp_path, capsys):
    """The b2-real-03 pattern: the right wheel slows gradually at the turn's minimum duty while the left wheel and the
    gyro keep moving, in open floor (2.415, 1.539): marginal-duty stall, clear of everything."""
    tool = load_tool()
    session = tmp_path / "session"
    (session / "moves").mkdir(parents=True)
    speeds = [0.09] * 10 + [0.074, 0.044, 0.049, 0.019, 0.033, 0.013, 0.006] + [0.0] * 11
    duties = [0.341] * 10 + [0.295] * 18
    move_log(session / "moves" / "move_20261125T133521_6_TURN_LEFT_30.jsonl", speeds, 0.035, duties, 12.0)
    code = tool.main([str(batch(tmp_path, {"x_m": 2.415, "y_m": 1.539, "theta_deg": 30.4})), str(session)])
    out = capsys.readouterr().out
    assert code == 0 and "VERDICT: marginal-duty stall, clear of everything" in out and "gradual" in out, out


def test_an_abrupt_stop_at_full_duty_by_a_wall_is_a_possible_blockage(tmp_path, capsys):
    """A wheel that stops in one sample at full duty, with the other wheel and the gyro stopping too, the car near
    the edge of the driving area: possible blockage, do not restart, with each reason named."""
    tool = load_tool()
    session = tmp_path / "session"
    (session / "moves").mkdir(parents=True)
    speeds = [0.09] * 10 + [0.0] * 12
    duties = [0.341] * 22
    move_log(session / "moves" / "move_20261125T140000_1_TURN_LEFT_30.jsonl", speeds, 0.0, duties, 0.0, bump=True)
    code = tool.main([str(batch(tmp_path, {"x_m": 0.80, "y_m": 1.00, "theta_deg": 180.0})), str(session)])
    out = capsys.readouterr().out
    assert code == 1 and "VERDICT: possible blockage: do not restart" in out, out
    for reason in ("a bump was flagged", "stopped abrupt", "full duty", "the other wheel stood too", "stopped turning",
                   "inside the driving area"):
        assert reason in out, (reason, out)


def test_the_turn_margins_count_only_the_slow_end_not_the_start_ramp(tmp_path, capsys):
    """--turn-margins reads each turn's lowest wheel speed at its slow end: after the highest duty, at 0.75 to 0.9 of
    it. The start ramp, where the duty passes the same values on its way up while the wheel is only starting, does not
    count (a first analysis of b2-real-03 counted it and overstated the near-stalls, 2026-11-25)."""
    tool = load_tool()
    session = tmp_path / "session"
    (session / "moves").mkdir(parents=True)
    # a healthy turn: slow start (0.005 m/s at duty 0.283 on the way up), cruise, a slow end at 0.06 m/s
    move_log(session / "moves" / "move_20261125T130000_1_TURN_LEFT_30.jsonl", [0.0, 0.005, 0.09, 0.09, 0.09, 0.06, 0.06],
             0.05, [0.146, 0.283, 0.341, 0.341, 0.341, 0.295, 0.295], 40.0)
    assert tool.main(["--turn-margins", str(session)]) == 0
    out = capsys.readouterr().out
    right = float(out.split("right ")[1].split(" ")[0])
    assert 0.05 < right < 0.07 and "1 turns; 0 with a wheel below 0.02 m/s" in out, out
