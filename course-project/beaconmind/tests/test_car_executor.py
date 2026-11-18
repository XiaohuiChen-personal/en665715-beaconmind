"""The bounded-move executor on the simulated car: targets reached, every way a move ends early, and the proof
that the car stops without any message from the host (work list 2.6; plan M3.T6).

Tolerances. The simulated car coasts and its telemetry is 20 ms apart, as on the real one, so a straight move is
asked to end within 1 cm of its distance and a turn within 3 degrees of its angle; what the executor REPORTS
(counts, heading) is asked to match what the simulated car really did within 2 mm and 0.2 degrees.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote these tests.
"""
import math

import pytest

from beaconmind.car import config as C
from beaconmind.car.latch import Latch
from beaconmind.car.link import SimLink
from beaconmind.car.moves import ACTIONS, make_move
from beaconmind.car.simcar import SimCar, SimCarParams
from beaconmind.schemas import validate

CFG = C.load_config()
STRAIGHT = {"FORWARD_25": 0.25, "FORWARD_10": 0.10, "BACKWARD_10": -0.10}
TURN = {"TURN_LEFT_30": 30.0, "TURN_RIGHT_30": -30.0}


def make_link(cfg=None, latch=None, **sim):
    return SimLink(cfg or CFG, SimCar(SimCarParams(**sim)), latch=latch)


def run(action, cfg=None, latch=None, on_step=None, **sim):
    link = make_link(cfg, latch, **sim)
    link.on_step = on_step
    result = link.execute(make_move(action, 7, "test"))
    assert validate("move_result", result) == [], result
    assert not link.executor.busy
    return link, result


def assert_car_at_rest(link, seconds=1.0):
    """The car is stopped now, stays stopped, and the host sends nothing more."""
    sent = len(link.published)
    before = link.sim.truth()
    link.wait(seconds)
    assert not link.sim.moving
    after = link.sim.truth()                # the simulated motors run down exponentially: allow that tail
    assert after["x_m"] == pytest.approx(before["x_m"], abs=0.0005) and after["y_m"] == pytest.approx(before["y_m"], abs=0.0005)
    assert after["theta_deg"] == pytest.approx(before["theta_deg"], abs=0.05)
    assert len(link.published) == sent, "the executor published while idle"


# ---------------------------------------------------------------- targets reached

@pytest.mark.parametrize("action", sorted(STRAIGHT))
@pytest.mark.parametrize("sim", [{}, {"left_gain": 0.7}, {"speed_per_duty_mps": 0.2, "left_gain": 0.7},
                                 {"telemetry_delay_s": 0.03, "command_delay_s": 0.03}, {"right_gain": 0.85}],
                         ids=["matched", "carpet-left-70pct", "slow-carpet", "30ms-delays", "right-85pct"])
def test_straight_moves_reach_their_distance(action, sim):
    link, result = run(action, **sim)
    truth, target = link.sim.truth(), STRAIGHT[action]
    assert result["result"] == "done" and result["reason"] is None
    assert truth["x_m"] == pytest.approx(target, abs=0.010)
    assert result["achieved_forward_m"] == pytest.approx(target, abs=0.010)
    assert abs(truth["theta_deg"]) < 5.0                      # the heading hold: under 5 degrees even on "carpet"
    assert (result["enc_left_ticks"] > 0) == (target > 0) and (result["enc_right_ticks"] > 0) == (target > 0)
    assert result["duration_s"] < CFG.move_timeout_s
    assert result["stall"] is False and result["bump"] is False
    assert_car_at_rest(link)


@pytest.mark.parametrize("action", sorted(TURN))
@pytest.mark.parametrize("sim", [{}, {"left_gain": 0.7}, {"speed_per_duty_mps": 0.2},
                                 {"telemetry_delay_s": 0.02, "command_delay_s": 0.02}],
                         ids=["matched", "carpet-left-70pct", "slow", "20ms-delays"])
def test_turns_reach_their_angle_with_the_right_sign(action, sim):
    link, result = run(action, **sim)
    truth, target = link.sim.truth(), TURN[action]
    assert result["result"] == "done"
    assert truth["theta_deg"] == pytest.approx(target, abs=3.0)
    assert result["gyro_dyaw_deg"] == pytest.approx(truth["theta_deg"], abs=0.2)
    # left turn = counter-clockwise = positive: the left wheel goes backward and the right forward
    assert (result["enc_right_ticks"] > 0) == (target > 0) and (result["enc_left_ticks"] < 0) == (target > 0)
    assert math.hypot(truth["x_m"], truth["y_m"]) < 0.02      # in place
    assert_car_at_rest(link)


def test_the_report_matches_what_the_car_did():
    link, result = run("FORWARD_25", left_gain=0.7)
    truth, odo = link.sim.truth(), link.last_diag["odometry"]
    assert odo["forward_m"] == pytest.approx(truth["x_m"], abs=0.002)
    assert odo["left_m"] == pytest.approx(truth["y_m"], abs=0.002)
    assert odo["dtheta_deg"] == pytest.approx(truth["theta_deg"], abs=0.2)
    assert result["gyro_dyaw_deg"] == pytest.approx(truth["theta_deg"], abs=0.2)
    ticks = link.sim.p.ticks_per_m
    assert result["enc_left_ticks"] == pytest.approx(link.sim.travel[0] * ticks, abs=2)
    assert result["enc_right_ticks"] == pytest.approx(link.sim.travel[1] * ticks, abs=2)


def test_counts_and_heading_that_wrap_change_nothing():
    plain = run("FORWARD_25", left_gain=0.7)[1]
    wrapped = run("FORWARD_25", left_gain=0.7, left0=2 ** 31 - 800, right0=-2 ** 31 + 500, yaw0_deg=179.2)[1]
    assert wrapped == plain
    assert run("TURN_LEFT_30", yaw0_deg=170.0)[1] == run("TURN_LEFT_30")[1]      # the heading crosses +-180
    assert run("BACKWARD_10", left0=-2 ** 31 + 100, right0=-2 ** 31 + 100)[1] == run("BACKWARD_10")[1]


def test_commands_stay_inside_the_limits():
    link, _ = run("FORWARD_25", left_gain=0.7)
    assert max(abs(v) for _t, v, _w in link.published) <= CFG.v_max_mps + 1e-9
    assert max(abs(w) for _t, _v, w in link.published) <= CFG.hold_limit_rps + 1e-9
    link, _ = run("TURN_LEFT_30")
    assert all(v == 0.0 for _t, v, _w in link.published)
    assert max(abs(w) for _t, _v, w in link.published) <= math.radians(CFG.turn_rate_dps) + 1e-9
    gaps = [b[0] - a[0] for a, b in zip(link.published, link.published[1:])]
    assert max(gaps) <= CFG.command_period_s + 0.002           # well inside the car's 0.5 s command timeout


def test_slip_shows_as_wheel_and_gyro_disagreeing():
    link, result = run("FORWARD_25", slip_left=0.6)            # the left wheel spins without moving the car as far
    assert link.last_diag["yaw_disagree_deg"] > 10.0           # configs/dv.json slip_yaw_disagree_deg
    assert run("FORWARD_25")[0].last_diag["yaw_disagree_deg"] < 1.0


# ---------------------------------------------------------------- ways a move ends early

def test_timeout_when_the_car_is_too_slow():
    link, result = run("FORWARD_25", speed_per_duty_mps=0.04)  # moving, far above the stall floor, but too slow
    assert result["result"] == "timeout" and result["reason"] == "timeout"
    assert CFG.move_timeout_s <= result["duration_s"] <= CFG.move_timeout_s + CFG.settle_max_s + 0.1
    assert 0.02 < result["achieved_forward_m"] < 0.25
    assert_car_at_rest(link)


def test_turn_on_the_stand_times_out():
    """Wheels up, the car cannot rotate and the IMU sees no yaw: the plan's expected stand result for a turn."""
    link, result = run("TURN_LEFT_30", slip_left=1.0, slip_right=1.0)
    assert result["result"] == "timeout"
    assert abs(result["gyro_dyaw_deg"]) < 0.5 and result["enc_right_ticks"] > 1000 and result["enc_left_ticks"] < -1000
    assert_car_at_rest(link)


@pytest.mark.parametrize("wheel, reason", [("blocked_left", "stall_left"), ("blocked_right", "stall_right")])
def test_a_blocked_wheel_is_a_stall(wheel, reason):
    link, result = run("FORWARD_25", **{wheel: True})
    assert result["result"] == "stalled" and result["reason"] == reason and result["stall"] is True
    assert result["duration_s"] <= CFG.stall_grace_s + 2 * CFG.stall_window_s + CFG.settle_max_s
    stop_t = next(t for t, v, w in link.published if v == 0.0 and w == 0.0)
    assert stop_t - 0.2 <= CFG.stall_grace_s + 2 * CFG.stall_window_s + 0.1     # 0.2 s: the link's warm-up
    assert_car_at_rest(link)


def test_both_wheels_blocked_in_a_turn_is_a_stall():
    link, result = run("TURN_RIGHT_30", blocked_left=True, blocked_right=True)
    assert result["result"] == "stalled" and result["stall"] is True
    assert_car_at_rest(link)


def test_free_running_wheels_never_look_stalled():
    for sim in ({}, {"left_gain": 0.7}, {"speed_per_duty_mps": 0.2, "left_gain": 0.7}, {"speed_per_duty_mps": 0.08}):
        for action in ACTIONS:
            assert run(action, **sim)[1]["result"] in ("done", "timeout"), (sim, action)


def test_telemetry_gap_is_link_lost_and_latches(tmp_path):
    latch = Latch(tmp_path / "LATCH")
    link, result = run("FORWARD_25", latch=latch, telemetry_drop=[(0.9, 30.0)])
    assert result["result"] == "link_lost" and result["reason"] == "telemetry_gap"
    pause_t = next(t for t, v, w in link.published if v == 0.0 and w == 0.0)
    assert pause_t == pytest.approx(0.9 + CFG.blind_pause_s, abs=0.08)         # blind: zeros first (the car pauses)
    assert all((v, w) == (0.0, 0.0) for t, v, w in link.published if t >= pause_t)   # and never motion again
    assert 0.9 + CFG.link_gap_s - 0.2 <= result["duration_s"] <= 0.9 + CFG.link_gap_s + CFG.settle_max_s
    assert link.sim.truth()["x_m"] < 0.20                                      # stopped well short, not driven blind
    assert latch.is_set() and latch.read()["by"] == "executor"                 # plan C5 item 2
    assert not link.sim.moving
    refused = link.execute(make_move("FORWARD_10", 8, "test"))
    assert refused["result"] == "refused" and refused["reason"] == "latched"


def test_short_telemetry_gap_is_ridden_through():
    link, result = run("FORWARD_25", telemetry_drop=[(0.9, 1.2)])              # 0.3 s: under the 0.5 s rule
    assert result["result"] == "done"
    assert link.last_diag["lost_samples"] >= 14 and link.last_diag["blind_pauses"] >= 1
    assert link.sim.truth()["x_m"] == pytest.approx(0.25, abs=0.010)           # paused while blind, then finished


def test_commands_not_reaching_the_car_is_link_lost(tmp_path):
    latch = Latch(tmp_path / "LATCH")
    link, result = run("FORWARD_25", latch=latch, command_drop=[(0.8, 30.0)], agent_alive=False)
    assert result["result"] == "link_lost"
    assert result["reason"] in ("car_not_hearing", "car_command_timeout")
    assert latch.is_set()
    assert not link.sim.moving and link.sim.truth()["x_m"] < 0.25


def test_car_disarming_itself_is_link_lost(tmp_path):
    def disarm(link):
        if link.t >= 1.0:
            link.sim.armed = False
    link, result = run("FORWARD_25", latch=Latch(tmp_path / "LATCH"), on_step=disarm)
    assert (result["result"], result["reason"]) == ("link_lost", "car_disarmed")


def test_car_restart_during_a_move(tmp_path):
    latch = Latch(tmp_path / "LATCH")
    done = []

    def reboot(link):
        if link.t >= 1.0 and not done:
            done.append(link.sim.reboot())
    link, result = run("FORWARD_25", latch=latch, on_step=reboot)
    assert (result["result"], result["reason"]) == ("link_lost", "car_rebooted")
    assert result["boot_id"] == 1                              # restarts seen by this executor
    assert latch.is_set() and "restarted" in latch.read()["reason"]
    assert link.car_state()["boots"] == 1
    # after the operator clears the latch and re-arms, the boot drive map is caught before any motion
    latch.clear("tester")
    link.arm()
    again = link.execute(make_move("FORWARD_10", 9, "test"))
    assert again["result"] == "refused" and again["reason"].startswith("drive_map")
    assert link.set_drive_map(*C.DRIVE_MAP_EXPECTED) == list(C.DRIVE_MAP_EXPECTED)
    assert link.execute(make_move("FORWARD_10", 10, "test"))["result"] == "done"


def test_car_restart_while_idle_latches(tmp_path):
    latch = Latch(tmp_path / "LATCH")
    link = make_link(latch=latch)
    link.sim.reboot()
    link.wait(0.2)
    assert latch.is_set() and link.car_state()["boots"] == 1
    assert link.published == []


def test_stale_commands_end_the_move_before_the_car_moves(tmp_path):
    """The host's clock is 1 s behind the car's: the car drops every stamped motion command as too old."""
    link, result = run("FORWARD_25", latch=Latch(tmp_path / "LATCH"), clock_skew_s=1.0)
    assert (result["result"], result["reason"]) == ("link_lost", "stale_commands")
    assert link.sim.truth()["x_m"] == 0.0 and link.sim.stale >= CFG.stale_commands_limit
    assert result["duration_s"] < 1.0 + CFG.settle_max_s


def test_imu_dropout(tmp_path):
    link, result = run("FORWARD_25", imu_fail=[(0.9, 1.0)])                    # 0.1 s: the wheels fill the gap
    assert result["result"] == "done" and link.last_diag["imu_substitutions"] >= 5
    assert link.sim.truth()["theta_deg"] == pytest.approx(result["gyro_dyaw_deg"], abs=0.3)
    link, result = run("TURN_LEFT_30", latch=Latch(tmp_path / "LATCH"), imu_fail=[(0.3, 30.0)])
    assert (result["result"], result["reason"]) == ("link_lost", "imu")
    assert_car_at_rest(link)


def test_an_internal_error_still_stops_the_car(tmp_path):
    latch = Latch(tmp_path / "LATCH")
    link = make_link(latch=latch)
    real_control, calls = link.executor._control, []

    def broken(dt):
        calls.append(dt)
        if len(calls) > 8:
            raise ZeroDivisionError("injected")
        return real_control(dt)
    link.executor._control = broken
    result = link.execute(make_move("FORWARD_25", 3, "test"))
    assert validate("move_result", result) == []
    assert result["result"] == "link_lost" and result["reason"].startswith("executor_error: ZeroDivisionError")
    assert link.published[-1][1:] == (0.0, 0.0) and latch.is_set()
    assert_car_at_rest(link)


def test_telemetry_lost_after_the_stop_is_not_called_done(tmp_path):
    latch = Latch(tmp_path / "LATCH")
    link = make_link(latch=latch)

    def cut(l):
        if l.executor.phase == "stopping" and not l.sim.p.telemetry_drop:
            l.sim.p.telemetry_drop.append((l.t, l.t + 30.0))
    link.on_step = cut
    result = link.execute(make_move("FORWARD_10", 1, "test"))
    assert (result["result"], result["reason"]) == ("link_lost", "telemetry_gap_after_stop")


# ---------------------------------------------------------------- refusals (nothing is sent)

def refused(reason_start, cfg=None, latch=None, cmd=None, prepare=None, **sim):
    link = make_link(cfg, latch, **sim)
    if prepare:
        prepare(link)
    result = link.execute(cmd or make_move("FORWARD_25", 5, "test"))
    assert validate("move_result", result) == []
    assert result["result"] == "refused" and result["reason"].startswith(reason_start), result
    assert link.published == [] and not link.executor.busy
    link.wait(1.0)
    assert link.published == [] and link.sim.truth() == {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
    return link


def test_refusals():
    refused("car_disarmed", armed=False)
    refused("imu_not_ready", imu_ready=False)
    refused("no_clock_sync", clock_ok=False)
    refused("drive_map", map_min_duty=C.FW_MAP_BOOT[0], map_max_speed_mps=C.FW_MAP_BOOT[1])
    refused("no_telemetry", telemetry_drop=[(0.25, 30.0)], prepare=lambda link: link.wait(0.8))
    refused("bad_command", cmd=dict(make_move("FORWARD_25", 5, "t"), distance_m=0.5))
    refused("bad_command", cmd={"action": "FORWARD_25"})
    refused("zero_distance", cmd=make_move("BACKWARD_10", 5, "t", prev_forward_m=0.0))


def test_unstamped_commands_do_not_need_the_car_clock():
    assert run("FORWARD_10", cfg=CFG.replace(stamp_commands=False), clock_ok=False)[1]["result"] == "done"


def test_drive_map_check_can_be_turned_off():
    cfg = CFG.replace(expected_drive_map=None)
    link, result = run("FORWARD_10", cfg=cfg, map_min_duty=0.46, map_max_speed_mps=0.215)
    assert result["result"] == "done"


def test_busy_executor_refuses_a_second_move():
    link = make_link()
    assert link.executor.start(make_move("FORWARD_25", 1, "t"), link.t) is None
    second = link.executor.start(make_move("FORWARD_10", 2, "t"), link.t)
    assert second["result"] == "refused" and second["reason"] == "busy" and second["cmd_seq"] == 2


def test_a_moving_car_is_not_given_a_new_move():
    link = make_link()
    link.sim.send(0.15, 0.0)
    link.wait(0.4)
    result = link.execute(make_move("FORWARD_10", 1, "t"))
    assert result["result"] == "refused" and result["reason"] == "car_moving"


# ---------------------------------------------------------------- the deadman: no message from the host is needed

@pytest.mark.parametrize("action", ["FORWARD_25", "TURN_LEFT_30"])
def test_the_car_stops_by_itself_when_the_host_dies_mid_move(action):
    link = make_link()
    assert link.executor.start(make_move(action, 1, "t"), link.t) is None
    link._next_tick = link.t
    link.wait(0.45 if action == "FORWARD_25" else 0.2)         # mid-move, at speed
    assert link.sim.moving and link.executor.busy
    link.host_alive = False                                    # the host process, or the link, is gone: no zeros sent
    sent, died_at = len(link.published), link.t
    last_cmd_t = link.published[-1][0]
    assert link.published[-1][1:] != (0.0, 0.0)                # the last message the car got was a motion command
    stopped_at = None
    while link.t < died_at + 2.0:
        link.wait(0.001)
        if not link.sim.moving and stopped_at is None:
            stopped_at = link.t
    assert len(link.published) == sent                         # nothing more was sent
    assert stopped_at is not None, "the car kept moving"
    # the car's own command timeout (0.5 s after the last command) plus the motor's run-down
    assert stopped_at - last_cmd_t <= C.FW_COMMAND_TIMEOUT_S + 0.5
    assert link.sim.status == 2                                # the firmware's "timeout stop"
    # what the car covered after the last command it received: at most its speed x the timeout, plus the run-down
    assert link.sim.distance_after_last_cmd <= 0.20 * C.FW_COMMAND_TIMEOUT_S + 0.03
    if action == "FORWARD_25":
        assert link.sim.truth()["x_m"] < 0.25                  # it did not even reach the commanded distance


def test_every_motion_command_is_refreshed_inside_the_car_timeout():
    """The design leans on the car's 0.5 s timeout, so the executor must never leave a longer gap while moving,
    and must never send a motion command it would not repeat (no 'run for N seconds' message exists)."""
    link, _ = run("FORWARD_25")
    moving = [t for t, v, w in link.published if (v, w) != (0.0, 0.0)]
    assert max(b - a for a, b in zip(moving, moving[1:])) < C.FW_COMMAND_TIMEOUT_S / 5
    assert link.published[-1][1:] == (0.0, 0.0)


# ---------------------------------------------------------------- coast lead and steering details

def test_steering_never_reverses_the_inner_wheel():
    """The firmware answers the smallest reverse command with its smallest duty, backward: a steering term larger
    than v / (track / 2) would flip the inner wheel from forward to backward."""
    half = CFG.track_width_m / 2.0
    for action in ("FORWARD_25", "BACKWARD_10"):
        link, _ = run(action, left_gain=0.5, telemetry_delay_s=0.05, command_delay_s=0.05)
        for _t, v, w in link.published:
            assert abs(w) * half <= abs(v) + 1e-9
            assert (v - w * half) * v >= -1e-12 and (v + w * half) * v >= -1e-12   # both wheels the move's way
    allowed, _ = run("FORWARD_25", cfg=CFG.replace(hold_allow_reverse=True), left_gain=0.5, telemetry_delay_s=0.05,
                     command_delay_s=0.05)
    assert any(abs(w) * half > abs(v) + 1e-9 for _t, v, w in allowed.published)    # the old behaviour is still there


# ================================================================ added after the independent review (2026-11-18)

from beaconmind.car import telemetry as T                      # noqa: E402
from beaconmind.car.executor import MoveExecutor               # noqa: E402


def test_heading_hold_is_what_keeps_the_carpet_car_straight():
    """Left wheel at 70 %: with no steering the heading leaves by 15 degrees and the move is ended, not finished;
    the Module 8 guide's gain 2 / limit 0.5 rad/s saturates; the carpet gains (8 / 1.2) hold it."""
    link, result = run("FORWARD_25", cfg=CFG.replace(hold_gain_per_s=0.0), left_gain=0.7)
    assert (result["result"], result["reason"]) == ("link_lost", "heading_diverged")
    assert abs(link.sim.truth()["theta_deg"]) < 15.0 + 8.0 and link.sim.truth()["x_m"] < 0.25
    weak = run("FORWARD_25", cfg=CFG.replace(hold_gain_per_s=2.0, hold_limit_rps=0.5), left_gain=0.7)[0].sim.truth()["theta_deg"]
    held = run("FORWARD_25", left_gain=0.7)[0].sim.truth()["theta_deg"]
    assert abs(held) < abs(weak) and abs(held) < 5.0
    integral = run("FORWARD_25", cfg=CFG.replace(hold_integral_per_s2=20.0), left_gain=0.7)[0].sim.truth()["theta_deg"]
    assert abs(integral) < abs(held)


def test_an_oscillating_heading_hold_is_ended_not_called_done(tmp_path):
    """Review finding 6: a 50 % left wheel with 60 ms each way makes the hold swing. The move must not come back
    `done` with the car pointing somewhere else."""
    latch = Latch(tmp_path / "LATCH")
    link = make_link(latch=latch, left_gain=0.5, telemetry_delay_s=0.06, command_delay_s=0.06)
    seen = []
    for i in range(4):
        result = link.execute(make_move("FORWARD_25", i, "t"))
        seen.append((result["result"], result["reason"], abs(result["gyro_dyaw_deg"])))
        if result["result"] != "done":
            break
        link.wait(0.4)
    assert all(dyaw <= CFG.heading_abort_deg + 8.0 for _r, _why, dyaw in seen)
    assert all(dyaw <= CFG.heading_abort_deg for r, _why, dyaw in seen if r == "done")
    assert seen[-1][:2] == ("link_lost", "heading_diverged") and latch.is_set()


def test_the_speed_limit_holds_from_the_first_move():
    """Review finding 5. The governor starts under 1, so the first move of a fresh process is inside the limit
    (10 % allowed, measured on the simulated car's TRUE speed), and what it learns can be saved and restored."""
    link = make_link()
    for i in range(3):
        assert link.execute(make_move("FORWARD_25" if i != 1 else "FORWARD_10", i, "t"))["result"] == "done"
        assert link.last_diag["peak_speed_mps"] <= CFG.v_max_mps * 1.1 and link.last_diag["over_speed_limit"] is False
        link.wait(0.5)
    assert link.sim.max_abs_speed <= CFG.v_max_mps * 1.1                       # the car's true speed, not a command
    learned = link.executor.export_state()
    assert learned["governor"]["straight"] < 1.0
    fresh = make_link()
    fresh.executor.import_state(json_round_trip(learned))
    assert fresh.executor.export_state() == learned
    fresh.executor.import_state({"governor": {"straight": 7.0, "turn": "x"}, "coast": {}})      # nonsense is ignored
    assert fresh.executor.export_state() == learned
    ungoverned = make_link(CFG.replace(govern_linear=False, governor_start=1.0))
    ungoverned.execute(make_move("FORWARD_25", 1, "t"))
    assert ungoverned.sim.max_abs_speed > CFG.v_max_mps * 1.1


def json_round_trip(obj):
    import json
    return json.loads(json.dumps(obj))


def test_a_car_faster_than_its_smallest_duty_allows_is_reported():
    """A plant twice as fast as the real car cannot be brought under 0.15 m/s by any command above the dead band.
    The executor cannot fix that; it must say so."""
    link = make_link(speed_per_duty_mps=0.6)
    for i in range(3):
        link.execute(make_move("FORWARD_25", i, "t"))
        link.wait(0.5)
    assert link.last_diag["governor"] == pytest.approx(CFG.governor_min, abs=0.05)
    assert link.last_diag["over_speed_limit"] is True


def test_turn_rate_is_over_the_design_limit_and_says_so():
    """The known deviation: at its smallest duty this car pivots at about twice turn_rate_dps."""
    link, result = run("TURN_LEFT_30")
    assert link.sim.max_abs_rate_dps > CFG.turn_rate_dps * 1.5
    assert link.last_diag["over_rate_limit"] is True


def test_the_firmware_cut_off_is_reported_as_a_stall():
    cfg = CFG.replace(stall_speed_mps=0.0)                     # host rule off: only the firmware's cut-off remains
    link, result = run("FORWARD_25", cfg=cfg, blocked_left=True, blocked_right=True)
    assert result["result"] == "stalled" and result["reason"] == "firmware_cutoff"
    assert_car_at_rest(link)


def test_a_cut_off_flag_left_from_before_does_not_end_a_new_move():
    """Review finding 18. The firmware clears a cut-off on a fresh start; a flag still set in the samples before
    this move's first command reached the car is not this move's stall."""
    link = make_link()
    link.sim.cut = [True, False]
    link.wait(0.1)
    assert link.executor.tel.cut_off == (True, False)
    assert link.execute(make_move("FORWARD_10", 1, "t"))["result"] == "done"


DELAYS = [0.0, 0.03, 0.06, 0.10]


@pytest.mark.parametrize("delay", DELAYS)
@pytest.mark.parametrize("tau", [0.08, 0.12])
@pytest.mark.parametrize("action, target", [("TURN_LEFT_30", 30.0), ("TURN_RIGHT_30", -30.0)])
def test_turns_with_link_latency(delay, tau, action, target):
    """Review finding 4: 0 to 100 ms each way. The round trip is measured in each move and added to the coast lead,
    so the FIRST turn is already close, and no turn is called `done` past the overshoot bound."""
    link = make_link(telemetry_delay_s=delay, command_delay_s=delay, tau_s=tau)
    first_tol = 5.0 if delay <= 0.06 else 9.0
    for i in range(4):
        result = link.execute(make_move(action, i, "t"))
        assert result["result"] == "done", (i, result)
        error = result["gyro_dyaw_deg"] - target
        assert abs(error) <= first_tol, (i, error)
        assert (result["gyro_dyaw_deg"] > 0) == (target > 0)
        link.wait(0.4)
    assert abs(result["gyro_dyaw_deg"] - target) <= (5.0 if delay <= 0.06 else 6.0)        # the fourth turn
    assert link.last_diag["round_trip_s"] == pytest.approx(2 * delay + 0.02, abs=0.035)    # the measured round trip
    assert link.sim.truth()["theta_deg"] == pytest.approx(4 * target, abs=4 * first_tol)   # the car itself, not the report


@pytest.mark.parametrize("delay", DELAYS)
@pytest.mark.parametrize("action, target", [("FORWARD_25", 0.25), ("FORWARD_10", 0.10), ("BACKWARD_10", -0.10)])
def test_straight_moves_with_link_latency(delay, action, target):
    link = make_link(telemetry_delay_s=delay, command_delay_s=delay, left_gain=0.7)
    for i in range(4):
        result = link.execute(make_move(action, i, "t"))
        assert result["result"] == "done", (i, result)
        assert result["achieved_forward_m"] == pytest.approx(target, abs=0.020 if i == 0 else 0.015), i
        assert abs(result["gyro_dyaw_deg"]) < 10.0
        link.wait(0.4)
    assert result["achieved_forward_m"] == pytest.approx(target, abs=0.012)


def test_coast_time_is_learned_only_from_finished_first_approaches():
    link = make_link(telemetry_delay_s=0.05, command_delay_s=0.05, tau_s=0.15)
    start = link.executor.export_state()["coast"]["turn"]
    assert start == CFG.coast_start_turn_s
    link.execute(make_move("TURN_LEFT_30", 1, "t"))
    d = link.last_diag
    assert d["coast_time_used_s"] == start and d["coast_time_measured_s"] > start
    assert CFG.coast_time_min_s <= d["coast_time_next_s"] <= CFG.coast_time_max_s and d["coast_time_next_s"] > start
    stalled = make_link(blocked_left=True, blocked_right=True)
    assert stalled.execute(make_move("FORWARD_25", 1, "t"))["result"] == "stalled"
    assert stalled.last_diag["coast_time_measured_s"] is None
    assert stalled.last_diag["coast_time_next_s"] == CFG.coast_start_straight_s


def test_a_move_that_stops_short_is_finished_by_a_second_approach():
    """The trim: with a coast time far too long the first approach ends well short; the move goes on and ends close."""
    cfg = CFG.replace(coast_start_turn_s=0.30, adapt_coast=False)
    link, result = run("TURN_LEFT_30", cfg=cfg)
    assert result["result"] == "done" and link.last_diag["trims"] >= 1
    assert result["gyro_dyaw_deg"] == pytest.approx(30.0, abs=CFG.trim_angle_deg + 1.0)
    no_trim, short = run("TURN_LEFT_30", cfg=cfg.replace(max_trims=0))
    assert short["gyro_dyaw_deg"] < result["gyro_dyaw_deg"] - 4.0


@pytest.mark.parametrize("action", ["FORWARD_25", "FORWARD_10", "TURN_LEFT_30"])
def test_stop_commands_that_do_not_arrive_are_not_done(tmp_path, action):
    """Review finding 3: the zeros of the stop are lost for 0.45 s (the car runs on until its own timeout). The
    move must not come back `done`."""
    latch = Latch(tmp_path / "LATCH")
    link = make_link(latch=latch)

    real_send, first_zero = link.sim.send, []

    def send(v, w, stamp_unix=0.0, arm_marker=False):
        if (v, w) == (0.0, 0.0):
            first_zero.append(link.t)
            if link.t - first_zero[0] < 0.45:
                return                                         # lost on the way, from the very first zero
        real_send(v, w, stamp_unix, arm_marker)
    link.sim.send = send
    result = link.execute(make_move(action, 1, "t"))
    assert validate("move_result", result) == []
    assert result["result"] == "link_lost" and result["reason"] in ("stop_not_confirmed", "overshoot"), result
    assert latch.is_set()
    assert not link.sim.moving


def test_an_overshoot_past_the_bound_is_not_done(tmp_path):
    """A plant twice as fast as the car with 100 ms each way: the turn lands far past 30 degrees."""
    latch = Latch(tmp_path / "LATCH")
    link, result = run("TURN_LEFT_30", latch=latch, speed_per_duty_mps=0.6, telemetry_delay_s=0.1, command_delay_s=0.1)
    assert result["gyro_dyaw_deg"] > 30.0 + CFG.overshoot_deg
    assert (result["result"], result["reason"]) == ("link_lost", "overshoot") and latch.is_set()


class WrongWayCar(SimCar):
    """A car whose turning is wired backward (or an IMU mounted upside down)."""

    def send(self, v, w, stamp_unix=0.0, arm_marker=False):
        super().send(v, -w, stamp_unix, arm_marker)


def test_a_turn_that_goes_the_wrong_way_is_ended(tmp_path):
    """Review finding 20."""
    latch = Latch(tmp_path / "LATCH")
    link = SimLink(CFG, WrongWayCar(SimCarParams()), latch=latch)
    result = link.execute(make_move("TURN_LEFT_30", 1, "t"))
    assert (result["result"], result["reason"]) == ("link_lost", "wrong_way")
    assert result["duration_s"] < 2.5 and -30.0 < result["gyro_dyaw_deg"] < -8.0
    assert latch.is_set()


def sample_like(tel, **changes):
    data = T.encode_wheel_ticks(left=tel.left, right=tel.right, uptime_ms=tel.uptime_ms, seq=tel.seq, flags=tel.flags,
                                yaw_cdeg=int(round(tel.yaw_deg * 100)), agent_rx_age_ms=tel.agent_rx_age_ms,
                                drive_map=T.pack_drive_map(tel.map_min_duty, tel.map_max_speed_mps))
    for key, value in changes.items():
        data[getattr(T, "TK_" + key.upper())] = value
    return data


def test_late_repeated_and_reordered_telemetry(tmp_path):
    """Review finding 8. A repeat, a sample 2 s old, and two samples swapped must change nothing: no restart, no
    latch, no odometry. A real restart (three samples in a row with a lower clock and sequence) is still seen."""
    latch = Latch(tmp_path / "LATCH")
    link = make_link(latch=latch)
    ex = link.executor
    state, tel = ex.odom.state, ex.tel
    assert ex.on_telemetry(tel) is None                                        # the same sample again
    old = T.decode_wheel_ticks(sample_like(tel, uptime_ms=tel.uptime_ms - 2000, seq=tel.seq - 100, left=tel.left - 5000,
                                           right=tel.right - 5000), link.t)
    assert ex.on_telemetry(old) is None                                        # 2 s late, 0.24 m of counts behind
    assert ex.odom.state == state and ex.boots == 0 and not latch.is_set() and ex.out_of_order == 2
    newer = T.decode_wheel_ticks(sample_like(tel, uptime_ms=tel.uptime_ms + 40, seq=tel.seq + 2), link.t)
    older = T.decode_wheel_ticks(sample_like(tel, uptime_ms=tel.uptime_ms + 20, seq=tel.seq + 1), link.t)
    ex.on_telemetry(newer)
    ex.on_telemetry(older)                                                     # swapped on the way
    assert ex.tel is newer and ex.boots == 0 and not latch.is_set()
    link.wait(0.1)
    assert link.execute(make_move("FORWARD_10", 1, "t"))["result"] == "done"   # and the car still drives


def test_a_restart_soon_after_boot_is_still_seen(tmp_path):
    latch = Latch(tmp_path / "LATCH")
    link = make_link(latch=latch, uptime0_ms=300)              # the car booted 0.3 s before the link came up
    link.wait(0.3)
    link.sim.reboot()                                          # uptime falls by less than a second
    link.wait(0.2)
    assert link.executor.boots == 1 and latch.is_set()


def test_stale_telemetry_refuses_instead_of_starting_and_latching(tmp_path):
    """Review finding 17: telemetry 0.2 s old (under the 0.5 s link rule, over the 0.12 s blind pause)."""
    latch = Latch(tmp_path / "LATCH")
    link = make_link(latch=latch, telemetry_drop=[(0.25, 30.0)])
    link.wait(0.25)
    result = link.execute(make_move("FORWARD_25", 1, "t"))
    assert (result["result"], result["reason"]) == ("refused", "no_telemetry")
    assert link.published == [] and not latch.is_set()


def test_a_latch_that_cannot_be_written_refuses_every_later_move():
    """Review finding 21: the car restarts while idle and the latch write fails. Nothing may move afterwards."""
    class BrokenLatch:
        def is_set(self):
            return False

        def set(self, reason, by):
            raise PermissionError("read-only file system")
    link = make_link(latch=BrokenLatch())
    link.sim.reboot()
    link.wait(0.3)
    assert link.executor.boots == 1 and "PermissionError" in link.executor.latch_failed
    link.arm()
    link.set_drive_map(*C.DRIVE_MAP_EXPECTED)
    result = link.execute(make_move("FORWARD_10", 1, "t"))
    assert result["result"] == "refused" and result["reason"].startswith("latch_write_failed")
    assert all((v, w) == (0.0, 0.0) for _t, v, w in link.published)


def test_an_error_while_handling_telemetry_still_stops_the_car(tmp_path):
    """The other exception path (the review noted only the tick path was tested)."""
    latch = Latch(tmp_path / "LATCH")
    link = make_link(latch=latch)
    real_update, calls = link.executor.odom.update, []

    def broken(*args, **kwargs):
        calls.append(1)
        if len(calls) > 30:
            raise RuntimeError("injected")
        return real_update(*args, **kwargs)
    link.executor.odom.update = broken
    result = link.execute(make_move("FORWARD_25", 3, "t"))
    link.executor.odom.update = real_update
    assert validate("move_result", result) == []
    assert result["result"] == "link_lost" and "executor_error: RuntimeError" in result["reason"]
    assert link.published[-1][1:] == (0.0, 0.0) and latch.is_set()
    link.wait(1.0)
    assert not link.sim.moving


def test_noisy_heading_at_rest_does_not_refuse_a_move():
    """Review finding 19: 0.2 degrees of yaw noise on a parked car."""
    import random
    rng = random.Random(7)
    refused = 0
    for trial in range(20):
        link = make_link()
        ex = link.executor
        for k in range(12):
            tel = ex.tel
            noisy = T.decode_wheel_ticks(sample_like(tel, uptime_ms=tel.uptime_ms + 20, seq=tel.seq + 1,
                                                     yaw_cdeg=int(round(rng.gauss(0.0, 0.2) * 100))), link.t)
            ex.on_telemetry(noisy)
        refused += ex._why_not(make_move("FORWARD_10", 1, "t"), link.t) == "car_moving"
    assert refused == 0

