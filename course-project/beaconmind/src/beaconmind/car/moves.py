"""The five bounded moves of contract C2, the bm.move/1 command, its limits and the bm.move_result/1 record.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote the move table and the command checks.
"""
import math

MOVE_SCHEMA = "bm.move/1"
RESULT_SCHEMA = "bm.move_result/1"

# plan/README.md C2 (AGENT-DESIGN D4): action -> (kind, distance in m, angle in degrees, left positive)
ACTIONS = {
    "FORWARD_25": ("forward", 0.25, 0.0),
    "FORWARD_10": ("forward", 0.10, 0.0),
    "BACKWARD_10": ("backward", 0.10, 0.0),
    "TURN_LEFT_30": ("turn", 0.0, 30.0),
    "TURN_RIGHT_30": ("turn", 0.0, -30.0),
}
# C2: one result enum everywhere
RESULTS = ("done", "stalled", "bumped", "timeout", "link_lost", "refused", "not_called")
MIN_DISTANCE_M = 0.005      # a shorter move is inside the stop tolerance: nothing to do


def make_move(action, cmd_seq, obs_id, dv=None, prev_forward_m=None):
    """A bm.move/1 command for one of the five actions, with the design-value limits.

    BACKWARD_10 covers the lesser of 0.10 m and the distance the previous forward move covered (C2); pass that
    distance as prev_forward_m (None = 0.10 m)."""
    if action not in ACTIONS:
        raise KeyError("not a C2 move: %r" % (action,))
    if dv is None:
        from beaconmind.dv import load_dv
        dv = load_dv()
    kind, distance, angle = ACTIONS[action]
    if kind == "backward" and prev_forward_m is not None:
        distance = max(0.0, min(distance, abs(float(prev_forward_m))))
    return {"schema": MOVE_SCHEMA, "cmd_seq": int(cmd_seq), "obs_id": str(obs_id), "action": action,
            "distance_m": round(distance, 4), "angle_deg": angle, "v_max_mps": float(dv["v_max_mps"]),
            "w_max_dps": float(dv["turn_rate_dps"]), "timeout_s": float(dv["move_timeout_s"])}


def _number(cmd, key):
    value = cmd.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("%s is not a finite number" % key)
    return float(value)


def check_move(cmd, cfg):
    """None if the executor may run this command, else the reason it refuses (C2: "anything outside -> refused")."""
    if not isinstance(cmd, dict):
        return "bad_command: not an object"
    if cmd.get("schema") != MOVE_SCHEMA:
        return "bad_command: schema is not %s" % MOVE_SCHEMA
    action = cmd.get("action")
    if action not in ACTIONS:
        return "bad_command: unknown action %r" % (action,)
    if isinstance(cmd.get("cmd_seq"), bool) or not isinstance(cmd.get("cmd_seq"), int):
        return "bad_command: cmd_seq is not an integer"
    try:
        distance, angle = _number(cmd, "distance_m"), _number(cmd, "angle_deg")
        v_max, w_max, timeout = _number(cmd, "v_max_mps"), _number(cmd, "w_max_dps"), _number(cmd, "timeout_s")
    except ValueError as exc:
        return "bad_command: %s" % exc
    kind, table_distance, table_angle = ACTIONS[action]
    eps = 1e-9
    if kind == "turn":
        if abs(angle - table_angle) > eps or abs(angle) > cfg.max_angle_deg + eps:
            return "bad_command: %s turns %+g degrees, not %+g" % (action, table_angle, angle)
        if abs(distance) > eps:
            return "bad_command: a turn has distance_m 0"
    else:
        if abs(angle) > eps:
            return "bad_command: a straight move has angle_deg 0"
        if distance < 0 or distance > table_distance + eps or distance > cfg.max_distance_m + eps:
            return "bad_command: %s covers at most %g m, not %g" % (action, table_distance, distance)
        if kind == "forward" and abs(distance - table_distance) > eps:
            return "bad_command: %s covers %g m, not %g" % (action, table_distance, distance)
        if distance < MIN_DISTANCE_M:
            return "zero_distance"
    if not 0 < v_max <= cfg.v_max_mps + eps:
        return "bad_command: v_max_mps %g is outside (0, %g]" % (v_max, cfg.v_max_mps)
    if not 0 < w_max <= cfg.turn_rate_dps + eps:
        return "bad_command: w_max_dps %g is outside (0, %g]" % (w_max, cfg.turn_rate_dps)
    if not 0 < timeout <= cfg.move_timeout_s + eps:
        return "bad_command: timeout_s %g is outside (0, %g]" % (timeout, cfg.move_timeout_s)
    return None


def target_of(cmd):
    """("straight", signed distance in m) or ("turn", signed angle in degrees) of a checked command."""
    kind, _distance, _angle = ACTIONS[cmd["action"]]
    if kind == "turn":
        return "turn", float(cmd["angle_deg"])
    return "straight", float(cmd["distance_m"]) * (1.0 if kind == "forward" else -1.0)


def make_result(cmd_seq, result, reason=None, boot_id=0, duration_s=0.0, enc_left_ticks=0, enc_right_ticks=0,
                gyro_dyaw_deg=0.0, achieved_forward_m=0.0, stall=False, bump=False):
    """A bm.move_result/1 record (exactly the schema's keys)."""
    if result not in RESULTS:
        raise ValueError("not a C2 result: %r" % (result,))
    seq = cmd_seq if isinstance(cmd_seq, int) and not isinstance(cmd_seq, bool) else -1
    return {"schema": RESULT_SCHEMA, "cmd_seq": seq, "result": result,
            "reason": None if reason is None else str(reason), "boot_id": int(boot_id),
            "duration_s": round(float(duration_s), 3), "enc_left_ticks": int(enc_left_ticks),
            "enc_right_ticks": int(enc_right_ticks), "gyro_dyaw_deg": round(float(gyro_dyaw_deg), 2),
            "achieved_forward_m": round(float(achieved_forward_m), 4), "stall": bool(stall), "bump": bool(bump)}
