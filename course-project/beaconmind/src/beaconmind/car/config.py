"""Constants and configuration of the host-side move executor. Every number names the file it was read from.

Three kinds of numbers live here:

1. Facts about the firmware on the car (Assignment 8 Build K2, access-point variant buildK2a_d485d7ab). Its
   sources are in the private course repo (assignments/assignment8/module-8-sensor-fusion/firmware/pico_fusion/);
   the public notes that state the same facts are named where they exist. They were checked on 2026-11-18 against
   a recorded bag of the parked car (data/real/20261118-000959-recorder-dry-run on the Spark): 84 fields per
   /pico/wheel_ticks message, field 2 = 9, field 82 equal to the yaw of /pico/imu/data within 0.002 degrees.
2. Design values, read from configs/dv.json (frozen) and configs/car.json at load time, never copied here.
3. Control settings of this executor. Those taken from the Module 8 and Module 9 runs of this car say so; the
   others are this file's own choices and are marked "choice". None has been run on the car by this code yet:
   evidence/M3/M3.T6/README.md lists what the stand test and the floor check must confirm.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this configuration module.
"""
import json
import math
import os
from dataclasses import dataclass, field, replace

# ---------------------------------------------------------------- firmware facts (Build K2)

# drive_control.c: DRIVE_TIMEOUT_MS. The car stops when no command arrived for this long (main loop), and a 10 ms
# timer interrupt drops the driver's standby pin 100 ms later (DEADMAN_TIMEOUT_MS) if the main loop is stuck.
FW_COMMAND_TIMEOUT_S = 0.5
FW_DEADMAN_S = 0.6
# drive_control.c: MAX_LINEAR_MPS, MAX_ANGULAR_RPS. The firmware clamps every command to these.
FW_MAX_LINEAR_MPS = 0.30
FW_MAX_ANGULAR_RPS = 1.50
# drive_control.c: wheel_duty(). A wheel command below 1 % of the map's full speed is sent as duty 0; any larger
# one gets at least the map's smallest duty: duty = min_duty + (1 - min_duty) * |v| / max_wheel_speed.
FW_DUTY_DEADBAND_FRACTION = 0.01
# drive_control.c: MIN_DUTY, MAX_WHEEL_SPEED_MPS: the map after every restart of the car.
FW_MAP_BOOT = (0.46, 0.215)
# drive_control.c: RAMP_MS_FULL. A rising duty climbs by at most 1.0 per 300 ms; a falling one applies at once.
FW_RAMP_FULL_S = 0.300
# drive_control.c: STALL_COUNTS / STALL_MS, ASSIST_REVERSE_MS, ASSIST_FORWARD_MS, ASSIST_MAX_TRIES, CUTOFF_MS,
# LOCKOUT_CUTOFFS. A commanded wheel that makes fewer than 15 counts in 250 ms gets a reverse jog and a forward
# push, three times at most; then it is cut off after 500 ms more, and locked after three cut-offs in a row.
FW_STALL_COUNTS = 15
FW_STALL_S = 0.250
FW_ASSIST_REVERSE_S = 0.060
FW_ASSIST_FORWARD_S = 0.120
FW_ASSIST_MAX_TRIES = 3
FW_CUTOFF_S = 0.500
FW_LOCKOUT_CUTOFFS = 3
# pico_fusion.c: CMD_STAMP_MIN_S, CMD_MAX_AGE_MS. A command may carry its send time (Unix seconds) in linear.z;
# stamped motion older than 300 ms on arrival is dropped. ARM_MARKER: a zero command with angular.x == 1.0 re-arms
# a car that disarmed itself (abnormal boot, session rebuild, 3 s without the agent). Public statement:
# research/2026-10-24-car-firmware-lessons-and-pid.md F11.
FW_STAMP_MIN_S = 1.0e9
FW_STAMP_MAX_AGE_S = 0.300
FW_ARM_MARKER = 1.0
# pico_fusion.c: TICKS_PERIOD_MS, TICKS_PARKED_PERIOD_MS: /pico/wheel_ticks every 20 ms, driving or parked.
FW_TELEMETRY_PERIOD_S = 0.020
# encoders.h: ENCODER_COUNTS_PER_REV (12 pulses x 90 gear ratio x 4 edges); also research note F6 of 2026-10-24.
FW_COUNTS_PER_WHEEL_REV = 4320

# ---------------------------------------------------------------- control settings

# Module 8 odometry/move_test.py (the host-side moves that drove this car): MAX_SPEED is the design value v_max_mps,
# MIN_SPEED 0.05 m/s, the speed falls as 1.5 x the remaining distance, MAX_TURN 0.6 rad/s, MIN_TURN 0.3 rad/s,
# 1.5 x the remaining angle, DIST_TOL 5 mm, ANGLE_TOL 1 degree, one command every 50 ms.
V_MIN_MPS = 0.05
SLOWDOWN_PER_S = 1.5
W_MAX_RPS = 0.6
W_MIN_RPS = 0.3
DIST_TOL_M = 0.005
ANGLE_TOL_DEG = 1.0
COMMAND_PERIOD_S = 0.05
# Module 8 odometry/odom_tools.py: CAR_COAST_TIME 0.09 s, this car's coast lead at drive map 0.25 / 0.33
# (assignment8 evidence/turn-calibration-move_test.txt: 90 degree turns came out 90.0 to 90.7 with it). It was
# measured with the fused estimate as feedback; this executor reads the car's own counts and heading, so the floor
# check re-measures it (each move's log carries the coast it saw).
COAST_TIME_S = 0.09
# choice: the coast time adapts. After every move that ended `done`, the coast the car really made after the stop
# decision, divided by its speed at that decision, is a measured coast time; the next move of that kind uses the
# mean of the old value and the new one, kept inside these bounds. COAST_TIME_S is only the first move's value.
COAST_TIME_MIN_S = 0.03
COAST_TIME_MAX_S = 0.30
COAST_ADAPT_WEIGHT = 0.5
COAST_ADAPT_MIN_SPEED_MPS = 0.03      # a stop decision below these speeds says too little about the coast
COAST_ADAPT_MIN_RATE_DPS = 15.0
# choice: first coast times of a car with no saved state. Larger than the 0.09 s above on purpose: a move that
# stops early is finished by a short second approach (the trim below); a move that stops late has overshot.
COAST_START_STRAIGHT_S = 0.08
COAST_START_TURN_S = 0.08
# choice: the link's round trip is measured in every move (first command sent -> first telemetry sample that shows
# a duty on the wheels) and added to the coast time, so the lead covers what the car does while the stop command
# and the samples are on their way. The adapted coast time is the part that is left after taking it out.
ROUND_TRIP_MAX_S = 0.40
# choice: trim. When the car has settled short of the target by more than this, the move goes on (at most
# MAX_TRIMS times): starting from rest the second approach is a short pulse, which is how the last degrees are
# reached on a firmware whose slowest pivot is fast.
TRIM_DIST_M = 0.02
TRIM_ANGLE_DEG = 5.0
MAX_TRIMS = 2
# choice: a move that ended past its target by more than this is not `done`; it ends link_lost (overshoot) and
# latches, because the stop did not land where the executor decided it.
OVERSHOOT_M = 0.04
OVERSHOOT_DEG = 10.0
# choice: the car must show zero duty this long after the stop decision, else the stop did not arrive in time
STOP_CONFIRM_S = 0.30
# choice: a straight whose heading leaves the start heading by this much ends (heading_diverged); a move that goes
# this far the wrong way ends (wrong_way)
HEADING_ABORT_DEG = 15.0
WRONG_WAY_M = 0.03
WRONG_WAY_DEG = 10.0
# Module 8 odom_tools.py: CAR_HOLD_GAIN 8, CAR_HOLD_LIMIT 1.2 rad/s. On carpet the left wheel made 70 to 74 % of the
# right wheel's counts and gain 2 / limit 0.5 let a 0.30 m straight turn 41 to 46 degrees; 8 / 1.2 gave 4.3 to 4.7
# (CONTEXT.md 2026-11-02; discussions/module9/evidence/carpet/README.md in the private repo).
HOLD_GAIN_PER_S = 8.0
HOLD_LIMIT_RPS = 1.2
# The drive map the Module 9 runs used and these gains belong to (carpet/README.md, tools/carpet_tune.sh). It is
# set live through /pico/imu/std and a restart of the car puts FW_MAP_BOOT back, so a move checks it first.
DRIVE_MAP_EXPECTED = (0.25, 0.33)
# (The link rule's 0.5 s is the design value watchdog_ms; the Module 8 tools used the same figure, move_test.py
# LINK_GAP_S: no wheel_ticks for that long, or the car not hearing the agent for that long, ends the move.)
# choice: a wheel counts as stalled below this speed. The design rule (stall_frac of the profile) needs wheels
# that follow a profile; this firmware drives open loop and its speed is not the commanded one (research note
# 2026-10-11 F2), so an absolute floor is used: 0.01 m/s is about 41 counts in the 200 ms window, three times the
# firmware's own stall test (15 counts in 250 ms) and a tenth of the slowest speed measured in a pivot.
STALL_SPEED_MPS = 0.01
# choice: only a wheel commanded at least this fast is tested (a slower command may sit in the map's dead band).
STALL_MIN_COMMAND_MPS = 0.015
# choice: grace before the stall test. The design value stall_grace_ms (200) suits a driver that applies its duty
# at once; this firmware ramps the duty (up to 0.3 s) and then gives a wheel that does not start one jog of
# 0.25 + 0.06 + 0.12 s. 0.6 s lets the ramp and the first jog happen before the host calls it a stall.
STALL_GRACE_S = 0.6
# choice: the overspeed governor. The command is scaled by a factor between GOVERNOR_MIN and 1 that falls while the
# measured speed is above the limit and creeps back toward 1 while it is below.
GOVERNOR_GAIN_PER_S = 2.5
GOVERNOR_RISE_PER_S = 0.25      # slow on the way up, so the factor a move learned survives the next move's start
GOVERNOR_MIN = 0.15
GOVERNOR_START = 0.7            # the first move of a car nobody has measured yet starts under the limit, not over it
# choice: with no telemetry for this long the executor sends zeros (the car pauses) until samples return; the
# move ends as link_lost only at the 0.5 s link rule. Driving on stale counts would overrun the target.
BLIND_PAUSE_S = 0.12
# choice: after the stop command the executor keeps sending zeros until no count changed for SETTLE_QUIET_S, at
# least STOP_MIN_S and at most SETTLE_MAX_S, and only then reads the move's final counts and heading.
STOP_MIN_S = 0.30
SETTLE_QUIET_S = 0.16
SETTLE_MAX_S = 1.2
# choice: speeds are measured over this much of the car's own clock (five telemetry samples).
RATE_WINDOW_S = 0.10
# choice: a move does not start on a car that is still moving.
REST_SPEED_MPS = 0.02
REST_RATE_DPS = 10.0
# choice: the IMU heading may be missing for this long during a move before the move ends.
IMU_GAP_S = 0.2
# choice: this many stamped commands dropped by the car as too old end the move (the link is delivering late).
STALE_COMMANDS_LIMIT = 3


@dataclass(frozen=True)
class ExecutorConfig:
    """Everything the executor needs. Build it with load_config(); tests replace single fields."""

    # geometry and encoder scale
    ticks_per_m_left: float
    ticks_per_m_right: float
    track_width_m: float
    scale_source: str                 # "car.json" (calibrated keys present) or "nominal"
    # limits (design values)
    v_max_mps: float                  # dv.json v_max_mps
    turn_rate_dps: float              # dv.json turn_rate_dps
    move_timeout_s: float             # dv.json move_timeout_s
    link_gap_s: float                 # dv.json watchdog_ms / 1000
    stall_window_s: float             # dv.json stall_window_ms / 1000
    max_distance_m: float = 0.25      # plan C2: the executor's own caps, whatever the command says
    max_angle_deg: float = 30.0
    # control
    v_min_mps: float = V_MIN_MPS
    slowdown_per_s: float = SLOWDOWN_PER_S
    w_max_rps: float = W_MAX_RPS
    w_min_rps: float = W_MIN_RPS
    dist_tol_m: float = DIST_TOL_M
    angle_tol_deg: float = ANGLE_TOL_DEG
    coast_time_s: float = COAST_TIME_S
    hold_gain_per_s: float = HOLD_GAIN_PER_S
    hold_limit_rps: float = HOLD_LIMIT_RPS
    hold_integral_per_s2: float = 0.0     # optional integral term of the heading hold; 0 = off (not run on the car)
    hold_allow_reverse: bool = False      # False: the steering never asks the inner wheel to turn backward
    adapt_coast: bool = True
    coast_time_min_s: float = COAST_TIME_MIN_S
    coast_time_max_s: float = COAST_TIME_MAX_S
    coast_adapt_weight: float = COAST_ADAPT_WEIGHT
    coast_start_straight_s: float = COAST_START_STRAIGHT_S
    coast_start_turn_s: float = COAST_START_TURN_S
    governor_start: float = GOVERNOR_START
    trim_dist_m: float = TRIM_DIST_M
    trim_angle_deg: float = TRIM_ANGLE_DEG
    max_trims: int = MAX_TRIMS
    overshoot_m: float = OVERSHOOT_M
    overshoot_deg: float = OVERSHOOT_DEG
    stop_confirm_s: float = STOP_CONFIRM_S
    heading_abort_deg: float = HEADING_ABORT_DEG
    hold_rate_gain_s: float = 0.0         # optional damping of the heading hold on the measured yaw rate; 0 = off
    command_period_s: float = COMMAND_PERIOD_S
    govern_linear: bool = True
    govern_turn: bool = False             # see evidence/M3/M3.T6/README.md: this firmware cannot hold 45 deg/s
    governor_gain_per_s: float = GOVERNOR_GAIN_PER_S
    governor_rise_per_s: float = GOVERNOR_RISE_PER_S
    blind_pause_s: float = BLIND_PAUSE_S
    governor_min: float = GOVERNOR_MIN
    # stall
    stall_speed_mps: float = STALL_SPEED_MPS
    stall_min_command_mps: float = STALL_MIN_COMMAND_MPS
    stall_grace_s: float = STALL_GRACE_S
    # stop and settle
    stop_min_s: float = STOP_MIN_S
    settle_quiet_s: float = SETTLE_QUIET_S
    settle_max_s: float = SETTLE_MAX_S
    rate_window_s: float = RATE_WINDOW_S
    rest_speed_mps: float = REST_SPEED_MPS
    rest_rate_dps: float = REST_RATE_DPS
    imu_gap_s: float = IMU_GAP_S
    # link and car state
    stamp_commands: bool = True           # put the send time in linear.z (the car then drops motion older than 0.3 s)
    stale_commands_limit: int = STALE_COMMANDS_LIMIT
    expected_drive_map: "tuple | None" = DRIVE_MAP_EXPECTED   # None = do not check
    latch_on_link_lost: bool = True       # plan C5 item 2: any link_lost and any reboot of the car latch
    sources: dict = field(default_factory=dict, compare=False)

    def replace(self, **changes):
        return replace(self, **changes)


def nominal_ticks_per_m(wheel_diameter_m):
    """Counts per metre of wheel travel from the nominal counts per turn and the tyre diameter."""
    return FW_COUNTS_PER_WHEEL_REV / (math.pi * wheel_diameter_m)


def _course_root():
    import beaconmind
    return beaconmind.course_root()


def load_car(path=None):
    """configs/car.json as {key: value}."""
    path = path or os.path.join(str(_course_root()), "configs", "car.json")
    with open(path, encoding="utf-8") as handle:
        doc = json.load(handle)
    return {key: entry["value"] for key, entry in doc["values"].items()}


def load_config(car_path=None, dv_path=None, **overrides):
    """ExecutorConfig from configs/car.json and configs/dv.json.

    The encoder scale comes from car.json's enc_ticks_per_m_left / enc_ticks_per_m_right when the floor check
    (work list 2.8) has written them (the names plan task M3.T9 uses); until then both wheels use the nominal
    4,320 counts per turn over the measured tyre diameter, and scale_source says "nominal".
    """
    from beaconmind.dv import dv_get, load_dv

    car = load_car(car_path)
    dv = load_dv(dv_path)
    nominal = nominal_ticks_per_m(float(car["wheel_diameter_m"]))
    calibrated = "enc_ticks_per_m_left" in car and "enc_ticks_per_m_right" in car
    sources = {
        "ticks_per_m": "configs/car.json enc_ticks_per_m_left/right" if calibrated else
                       "nominal: 4320 counts per wheel turn (firmware encoders.h; research note 2026-10-24 F6) / "
                       "(pi x configs/car.json wheel_diameter_m)",
        "track_width_m": "configs/car.json track_width_m",
        "v_max_mps, turn_rate_dps, move_timeout_s, watchdog_ms, stall_window_ms": "configs/dv.json",
    }
    values = dict(
        ticks_per_m_left=float(car["enc_ticks_per_m_left"]) if calibrated else nominal,
        ticks_per_m_right=float(car["enc_ticks_per_m_right"]) if calibrated else nominal,
        track_width_m=float(car.get("track_width_eff_m", car["track_width_m"])),
        scale_source="car.json" if calibrated else "nominal",
        v_max_mps=dv_get(dv, "v_max_mps"),
        turn_rate_dps=dv_get(dv, "turn_rate_dps"),
        move_timeout_s=dv_get(dv, "move_timeout_s"),
        link_gap_s=dv_get(dv, "watchdog_ms") / 1000.0,
        stall_window_s=dv_get(dv, "stall_window_ms") / 1000.0,
        sources=sources,
    )
    values.update(overrides)
    return ExecutorConfig(**values)
