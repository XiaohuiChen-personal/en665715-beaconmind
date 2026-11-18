"""Odometry, telemetry decoding, the move table and the command checks of the car package (work list 2.6).

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote these tests.
"""
import math

import pytest

from beaconmind import geometry as g
from beaconmind.car import config as C
from beaconmind.car import telemetry as T
from beaconmind.car.moves import ACTIONS, check_move, make_move, make_result, target_of
from beaconmind.car.odometry import (Odometer, chord_c1, delta_between, encoder_yaw_deg, tick_delta, wrap_deg)
from beaconmind.schemas import validate

# One /pico/wheel_ticks message of the parked real car, from the recorded session
# data/real/20261118-000959-recorder-dry-run (Spark), with field 30 (the access point's address bytes) set to 0.
REAL_SAMPLE = [-2, -1, 9, 710142, 1529, 4684, 4685, 16111, 10273, 503, 4316, 0, 0, 0, 142, 3, 0, 3, 0, 0, 0, 1100,
               65536, 0, 0, 0, 0, 53244, 0, -56, 0, 11, 0, 1, 5, 0, 0, 10036, 1, 0, 1, 0, -1, 0, 3, 0, -78, -2, 0,
               1794, 273, 0, 66, 0, 0, 0, 13, 1638400, 1024, 0, 0, 0, 65536, 0, 0, 0, 655370, 0, 0, 589837, 0, 676, 0,
               1666926836, 1537, 1840, 1479, 200, 200, 300, 0, 14090700, -12296, 1288]


@pytest.fixture(scope="module")
def cfg():
    return C.load_config()


def test_config_comes_from_the_project_files(cfg):
    assert cfg.v_max_mps == 0.15 and cfg.turn_rate_dps == 45.0 and cfg.move_timeout_s == 5.0    # configs/dv.json
    assert cfg.link_gap_s == 0.5 and cfg.stall_window_s == 0.2
    assert cfg.track_width_m == 0.1335                                                          # configs/car.json
    assert cfg.scale_source == "nominal"            # until the floor check writes enc_ticks_per_m_left/right
    assert cfg.ticks_per_m_left == pytest.approx(4320 / (math.pi * 0.067))
    assert cfg.command_period_s < C.FW_COMMAND_TIMEOUT_S / 4       # several commands inside the car's timeout


def test_calibrated_scale_is_used_when_car_json_has_it(tmp_path):
    import json
    import beaconmind
    doc = json.loads((beaconmind.course_root() / "configs" / "car.json").read_text())
    doc["values"]["enc_ticks_per_m_left"] = {"value": 20900.0}
    doc["values"]["enc_ticks_per_m_right"] = {"value": 20400.0}
    path = tmp_path / "car.json"
    path.write_text(json.dumps(doc))
    cfg = C.load_config(car_path=str(path))
    assert (cfg.ticks_per_m_left, cfg.ticks_per_m_right, cfg.scale_source) == (20900.0, 20400.0, "car.json")


# ---------------------------------------------------------------- telemetry

def test_decode_a_real_message():
    tel = T.decode_wheel_ticks(REAL_SAMPLE, 12.5)
    assert (tel.left, tel.right, tel.uptime_ms, tel.seq) == (-2, -1, 710142, 1529)
    assert tel.armed and tel.imu_ready and tel.clock_ok and not tel.assisting
    assert tel.drive_status == T.DRIVE_STOPPED and tel.cut_off == (False, False) and not tel.locked
    assert tel.yaw_deg == pytest.approx(-122.96)
    assert (tel.map_min_duty, tel.map_max_speed_mps) == C.FW_MAP_BOOT        # the car had restarted: boot map
    assert tel.boot_report == 1100 and tel.sessions == 1 and tel.agent_rx_age_ms == 273 and tel.cutoffs == 0


def test_wrong_layout_is_refused_not_misread():
    with pytest.raises(T.LayoutError):
        T.decode_wheel_ticks([5, 6], 0.0)                      # the guide's firmware: [left, right] only
    other = list(REAL_SAMPLE)
    other[T.TK_LAYOUT] = 8
    with pytest.raises(T.LayoutError):
        T.decode_wheel_ticks(other, 0.0)


def test_encode_round_trip_and_flag_bits():
    data = T.encode_wheel_ticks(left=-5, right=7, flags=T.FLAG_ARMED | T.FLAG_CUT_RIGHT | (2 << T.FLAG_STATUS_SHIFT),
                                yaw_cdeg=-17999, drive_map=T.pack_drive_map(0.25, 0.33), agent_rx_age_ms=40)
    assert len(data) == T.N_FIELDS
    tel = T.decode_wheel_ticks(data, 1.0)
    assert (tel.left, tel.right, tel.yaw_deg) == (-5, 7, -179.99)
    assert tel.armed and not tel.imu_ready and tel.cut_off == (False, True) and tel.drive_status == T.DRIVE_TIMEOUT_STOP
    assert (tel.map_min_duty, tel.map_max_speed_mps) == (0.25, 0.33)


def test_quaternion_yaw():
    assert T.yaw_from_quaternion(math.cos(math.radians(15)), 0, 0, math.sin(math.radians(15))) == pytest.approx(30.0)
    assert T.yaw_from_quaternion(math.cos(math.radians(-45)), 0, 0, math.sin(math.radians(-45))) == pytest.approx(-90.0)


# ---------------------------------------------------------------- counts and angles that wrap

def test_tick_delta_across_the_int32_wrap():
    top, bottom = 2 ** 31 - 1, -2 ** 31
    assert tick_delta(bottom + 9, top - 10) == 20            # forward across the wrap
    assert tick_delta(top - 10, bottom + 9) == -20           # backward across it
    assert tick_delta(5, -5) == 10 and tick_delta(-5, 5) == -10


def test_wrap_deg():
    assert wrap_deg(190.0) == -170.0 and wrap_deg(-190.0) == 170.0 and wrap_deg(180.0) == 180.0
    assert wrap_deg(-180.0) == 180.0 and wrap_deg(360.0) == 0.0


# ---------------------------------------------------------------- odometry (contract C1)

def drive_arc(odo, radius_m, angle_deg, steps, k=20000.0, track=0.1335, yaw0=0.0, l0=0, r0=0):
    """Feed an Odometer a left arc of the given radius and angle in equal steps; returns the final state."""
    t = 0.0
    odo.update(l0, r0, yaw0, t)
    for i in range(1, steps + 1):
        a = math.radians(angle_deg) * i / steps
        left = l0 + int(round((radius_m - track / 2) * a * k))
        right = r0 + int(round((radius_m + track / 2) * a * k))
        left = ((left + 2 ** 31) % 2 ** 32) - 2 ** 31
        right = ((right + 2 ** 31) % 2 ** 32) - 2 ** 31
        t += 0.02
        odo.update(left, right, wrap_deg(yaw0 + math.degrees(a)), t)
    return odo.state


def test_arc_matches_the_c1_formula_and_compose_odometry():
    odo = Odometer(20000.0, 20000.0, 0.1335)
    start = odo.state
    end = drive_arc(odo, radius_m=0.5, angle_deg=40.0, steps=100)
    d = delta_between(start, end)
    s, dth = 0.5 * math.radians(40.0), math.radians(40.0)
    forward, left = chord_c1(s, dth)
    assert d["forward_m"] == pytest.approx(forward, abs=5e-4)
    assert d["left_m"] == pytest.approx(left, abs=5e-4)
    assert d["dtheta_deg"] == pytest.approx(40.0, abs=1e-6)
    # the true end of that arc from the origin, and what the agent's tool computes from the odometry
    pose = g.compose_odometry({"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}, d["forward_m"], d["left_m"], d["dtheta_deg"])
    assert pose["x_m"] == pytest.approx(0.5 * math.sin(dth), abs=5e-4)
    assert pose["y_m"] == pytest.approx(0.5 * (1 - math.cos(dth)), abs=5e-4)
    assert pose["theta_deg"] == pytest.approx(40.0, abs=1e-6)


def test_straight_and_pure_rotation():
    odo = Odometer(20000.0, 20000.0, 0.1335)
    odo.update(0, 0, 10.0, 0.0)
    a = odo.update(5000, 5000, 10.0, 1.0)
    assert (a.x_m, a.y_m, a.theta_deg) == pytest.approx((0.25, 0.0, 0.0))
    b = odo.update(5000 - 700, 5000 + 700, 40.0, 2.0)          # left turn in place: left wheel back, right forward
    d = delta_between(a, b)
    assert d["forward_m"] == pytest.approx(0.0, abs=1e-9) and d["dtheta_deg"] == pytest.approx(30.0)
    assert (d["left_ticks"], d["right_ticks"]) == (-700, 700)
    assert encoder_yaw_deg(d["s_left_m"], d["s_right_m"], 0.1335) == pytest.approx(math.degrees(0.07 / 0.1335))


def test_backward_move_is_negative_forward():
    odo = Odometer(20000.0, 20000.0, 0.1335)
    odo.update(100, 100, 0.0, 0.0)
    d = delta_between(odo.state, odo.update(100 - 2000, 100 - 2000, 0.0, 1.0))
    assert d["forward_m"] == pytest.approx(-0.10) and d["left_m"] == pytest.approx(0.0)


def test_per_wheel_scale():
    odo = Odometer(4000.0, 5000.0, 0.1335)                     # the example of plan task M3.T9
    odo.update(0, 0, 0.0, 0.0)
    st = odo.update(1000, 1000, 0.0, 1.0)
    assert (st.s_left_m, st.s_right_m) == pytest.approx((0.25, 0.20))


def test_wrap_of_counts_and_heading_changes_nothing():
    plain = Odometer(20000.0, 20000.0, 0.1335)
    a = delta_between(plain.state, drive_arc(plain, 0.4, 50.0, 80))
    wrapped = Odometer(20000.0, 20000.0, 0.1335)
    b = delta_between(wrapped.state, drive_arc(wrapped, 0.4, 50.0, 80, yaw0=160.0, l0=2 ** 31 - 1500, r0=-2 ** 31 + 900))
    for key in ("forward_m", "left_m", "dtheta_deg", "left_ticks", "right_ticks"):
        assert a[key] == pytest.approx(b[key], abs=1e-6)


def test_a_failed_imu_read_does_not_jump_the_heading():
    odo = Odometer(20000.0, 20000.0, 0.1335)
    odo.update(0, 0, 50.0, 0.00)
    odo.update(-100, 100, 50.0 + math.degrees(0.01 / 0.1335), 0.02)
    # the firmware reports yaw 0 when a read fails; the wheels kept turning
    odo.update(-200, 200, 0.0, 0.04, yaw_valid=False)
    st = odo.update(-300, 300, 50.0 + math.degrees(0.03 / 0.1335), 0.06)
    assert st.theta_deg == pytest.approx(math.degrees(0.03 / 0.1335), abs=1e-6)
    assert odo.imu_substitutions == 2          # the failed sample and the one that re-anchors on the heading


# ---------------------------------------------------------------- moves and results

def test_move_table_is_contract_c2():
    assert sorted(ACTIONS) == ["BACKWARD_10", "FORWARD_10", "FORWARD_25", "TURN_LEFT_30", "TURN_RIGHT_30"]
    assert target_of(make_move("FORWARD_25", 1, "o")) == ("straight", 0.25)
    assert target_of(make_move("BACKWARD_10", 1, "o")) == ("straight", -0.10)
    assert target_of(make_move("TURN_LEFT_30", 1, "o")) == ("turn", 30.0)       # left = counter-clockwise = positive
    assert target_of(make_move("TURN_RIGHT_30", 1, "o")) == ("turn", -30.0)
    assert make_move("BACKWARD_10", 1, "o", prev_forward_m=0.062)["distance_m"] == 0.062
    assert make_move("BACKWARD_10", 1, "o", prev_forward_m=0.25)["distance_m"] == 0.10


@pytest.mark.parametrize("action", sorted(ACTIONS))
def test_commands_validate_and_pass_the_executor_check(action, cfg):
    cmd = make_move(action, 17, "ep-s014")
    assert validate("move", cmd) == []
    assert check_move(cmd, cfg) is None


@pytest.mark.parametrize("change, word", [
    ({"distance_m": 0.30}, "covers"), ({"action": "FORWARD_50"}, "unknown action"), ({"v_max_mps": 0.30}, "v_max_mps"),
    ({"timeout_s": 9.0}, "timeout_s"), ({"w_max_dps": 90.0}, "w_max_dps"), ({"schema": "bm.move/2"}, "schema"),
    ({"angle_deg": 5.0}, "angle_deg"), ({"cmd_seq": "7"}, "cmd_seq"), ({"distance_m": float("nan")}, "finite"),
    ({"distance_m": 0.10}, "covers"), ({"timeout_s": 0.0}, "timeout_s"),
])
def test_out_of_limit_commands_are_refused(change, word, cfg):
    cmd = dict(make_move("FORWARD_25", 1, "o"), **change)
    reason = check_move(cmd, cfg)
    assert reason is not None and word in reason


def test_turn_and_backward_limits(cfg):
    assert "turns" in check_move(dict(make_move("TURN_LEFT_30", 1, "o"), angle_deg=-30.0), cfg)
    assert "turns" in check_move(dict(make_move("TURN_LEFT_30", 1, "o"), angle_deg=45.0), cfg)
    assert check_move(dict(make_move("BACKWARD_10", 1, "o"), distance_m=0.0), cfg) == "zero_distance"
    assert "covers" in check_move(dict(make_move("BACKWARD_10", 1, "o"), distance_m=0.20), cfg)
    assert check_move("FORWARD_25", cfg).startswith("bad_command")


def test_results_validate():
    for result in ("done", "stalled", "timeout", "link_lost", "refused"):
        assert validate("move_result", make_result(3, result, None if result == "done" else "why")) == []
    with pytest.raises(ValueError):
        make_result(3, "crashed")
