"""A deterministic simulated car that behaves like the firmware on the real one, for tests.

It models what the executor depends on, each item as the Build K2 sources state it (see config.py):

- a velocity command becomes two wheel duties through the two-number drive map, with its dead band;
- a rising duty ramps (1.0 per 0.3 s), a falling one applies at once;
- no command for 0.5 s stops the wheels (the command timeout): the property the whole design leans on;
- stamped motion older than 0.3 s is dropped and counted; zeros always stop;
- a disarmed car ignores motion until a zero command (with the arm marker when it asks for one);
- a wheel that stays blocked is cut off by the firmware after about 2 s;
- telemetry is the 84-field layout-9 array every 20 ms, with 32-bit counts and the yaw in hundredths of a degree.

The plant is first order per wheel: speed -> speed_per_duty x duty x that wheel's gain, time constant tau. The
default speed_per_duty (0.33 m/s per unit duty) is the hard-floor figure of this car's motors in pivots:
about 0.17 m/s per wheel at duty 0.53 (research/2026-10-24-car-firmware-lessons-and-pid.md F6/F8) and 87 to
89 degrees/s at duty about 0.30 (private repo, assignment8 evidence/turn-cal-rates.txt). So, as on the real car,
the simulated car moves about twice as fast as the command says at low speeds. left_gain 0.7 gives the carpet's
imbalance (CONTEXT.md 2026-11-02). The numbers are stand-ins for tests, not a calibrated model of the car.

No wall clock and no randomness: step(dt) advances the car's own time.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this simulated car.
AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: counts per metre per wheel, by default the scales the
executor reads (configs/car.json since the floor check of 2026-11-25), so the simulated car is the car as car.json
says, as it was while both were nominal.
"""
import math
from dataclasses import dataclass, field

from . import config as C
from . import telemetry as T

EPOCH_S = 1.8e9     # the simulated Unix time at t = 0 (any value above the firmware's CMD_STAMP_MIN_S)


_SCALES = {}


def _configured_scales():
    """(left, right) counts per metre the executor reads (configs/car.json, or nominal), read once per process."""
    if "lr" not in _SCALES:
        cfg = C.load_config()
        _SCALES["lr"] = (float(cfg.ticks_per_m_left), float(cfg.ticks_per_m_right))
    return _SCALES["lr"]


@dataclass
class SimCarParams:
    # the drive map the car has now (DRIVE_MAP_EXPECTED is what the Module 9 runs set; after a restart it is
    # C.FW_MAP_BOOT)
    map_min_duty: float = C.DRIVE_MAP_EXPECTED[0]
    map_max_speed_mps: float = C.DRIVE_MAP_EXPECTED[1]
    # plant
    speed_per_duty_mps: float = 0.33
    duty_stick: float = 0.12            # below this duty a wheel does not turn
    tau_s: float = 0.08
    left_gain: float = 1.0              # 0.7 = the left wheel makes 70 % of the right wheel's speed
    right_gain: float = 1.0
    slip_left: float = 0.0              # share of the wheel's travel that does not move the car
    slip_right: float = 0.0
    blocked_left: bool = False          # the wheel cannot turn (a stall)
    blocked_right: bool = False
    track_width_m: float = 0.1335       # configs/car.json track_width_m
    ticks_per_m: float = C.FW_COUNTS_PER_WHEEL_REV / (math.pi * 0.067)   # 4320 per turn, 67 mm tyre (nominal)
    # the encoders' true counts per metre of wheel travel; None: the scales the executor reads from configs/car.json
    # (config.load_config: the floor check's measured values, or the nominal one above). A test that wants the
    # executor to be wrong about the scale changes the executor's config, not these.
    ticks_per_m_left: float = None
    ticks_per_m_right: float = None
    # initial state
    left0: int = 0
    right0: int = 0
    yaw0_deg: float = 0.0
    uptime0_ms: int = 600000
    armed: bool = True
    need_marker: bool = False
    imu_ready: bool = True
    clock_ok: bool = True
    clock_skew_s: float = 0.0           # the car's idea of Unix time minus the host's
    agent_alive: bool = True            # the agent's once-a-second time sync reaches the car
    # link
    telemetry_delay_s: float = 0.0
    command_delay_s: float = 0.0
    telemetry_drop: list = field(default_factory=list)   # [(t0, t1)]: samples sent in these windows are lost
    command_drop: list = field(default_factory=list)     # [(t0, t1)]: commands sent in these windows are lost
    imu_fail: list = field(default_factory=list)         # [(t0, t1)]: IMU reads fail (yaw reported as 0)
    vsys_mv: int = 4680                 # the Pico's supply on its power bank (the recorded parked car read 4684)
    cutoff_after_s: float = 2.0         # a blocked, commanded wheel is cut off after this long


def _in(windows, t):
    return any(t0 <= t < t1 for t0, t1 in windows)


def _to_int32(n):
    return ((int(n) + (1 << 31)) % (1 << 32)) - (1 << 31)


class SimCar:
    def __init__(self, params=None):
        self.p = params or SimCarParams()
        p = self.p
        if p.ticks_per_m_left is None or p.ticks_per_m_right is None:
            cfg = _configured_scales()
        self.ticks_per_m = (p.ticks_per_m_left if p.ticks_per_m_left is not None else cfg[0],
                            p.ticks_per_m_right if p.ticks_per_m_right is not None else cfg[1])
        self.t = 0.0
        self.x = self.y = self.theta = 0.0          # true pose, m and rad, in the frame of the start
        self.speed = [0.0, 0.0]                     # wheel speeds, m/s
        self.travel = [0.0, 0.0]                    # wheel travel, m (what the encoders count)
        self.target = [0.0, 0.0]                    # duties asked for
        self.duty = [0.0, 0.0]                      # duties applied (after the ramp)
        self.status = T.DRIVE_STOPPED
        self.armed = p.armed
        self.need_marker = p.need_marker
        self.last_cmd_t = None                      # last command that reached the drive
        self.last_rx_t = None                       # last datagram of any kind
        self.commands = 0
        self.stale = 0
        self.cutoffs = 0
        self.cut = [False, False]
        self.blocked_since = [None, None]
        self.imu_fails = 0
        self.sessions = 1
        self.seq = 0
        self.boot_t = -p.uptime0_ms / 1000.0        # the car's time when it booted
        self.left0, self.right0 = p.left0, p.right0
        self._next_tel = 0.0
        self._tel_out = []                          # (deliver at, array)
        self._cmd_in = []                           # (deliver at, v, w, stamp, marker)
        self.unix_time = None                       # a callable giving Unix time; None = EPOCH_S + the car's time
        self.max_abs_speed = 0.0
        self.max_abs_rate_dps = 0.0
        self.distance_after_last_cmd = 0.0          # travel of the car since the last command arrived

    # ------------------------------------------------------------ host -> car

    def send(self, v, w, stamp_unix=0.0, arm_marker=False):
        """A /pico/cmd_vel message leaves the host now."""
        if _in(self.p.command_drop, self.t):
            return
        self._cmd_in.append((self.t + self.p.command_delay_s, float(v), float(w), float(stamp_unix), arm_marker))

    def set_map(self, min_duty, max_speed_mps):
        """What a /pico/imu/std message with a 4th and 5th value does (the accepted ranges are the firmware's)."""
        if 0.15 <= min_duty <= 0.60:
            self.p.map_min_duty = min_duty
        if 0.15 <= max_speed_mps <= 0.60:
            self.p.map_max_speed_mps = max_speed_mps

    def reboot(self):
        """The Pico restarts: counters and uptime start again, the motors are off, the map is the boot map."""
        self.boot_t = self.t
        self.left0 = self.right0 = 0
        self.travel = [0.0, 0.0]
        self.speed = [0.0, 0.0]
        self.target = [0.0, 0.0]
        self.duty = [0.0, 0.0]
        self.status = T.DRIVE_STOPPED
        self.seq = 0
        self.commands = self.stale = self.cutoffs = 0
        self.cut = [False, False]
        self.last_cmd_t = None
        self.p.map_min_duty, self.p.map_max_speed_mps = C.FW_MAP_BOOT
        self.armed, self.need_marker = False, True     # an abnormal boot waits for the arm marker

    def _receive(self, v, w, stamp, marker):
        t = self.t
        self.last_rx_t = t
        zero = v == 0.0 and w == 0.0
        if stamp > C.FW_STAMP_MIN_S:
            if not self.p.clock_ok:
                if not zero:
                    self.stale += 1
                    return
            else:
                unix_now = self.unix_time() if self.unix_time is not None else EPOCH_S + t
                age = (unix_now + self.p.clock_skew_s) - stamp
                if age > C.FW_STAMP_MAX_AGE_S:
                    self.stale += 1
                    if zero:
                        self._stop_drive(T.DRIVE_STOPPED)
                    return
        if not self.armed:
            if zero and (not self.need_marker or marker):
                self.armed, self.need_marker = True, False
            return
        if self.status == T.DRIVE_DRIVING and t - self.last_cmd_t > C.FW_COMMAND_TIMEOUT_S:
            self._stop_drive(T.DRIVE_TIMEOUT_STOP)
        self.last_cmd_t = t
        self.commands += 1
        self.distance_after_last_cmd = 0.0
        v = max(-C.FW_MAX_LINEAR_MPS, min(C.FW_MAX_LINEAR_MPS, v))
        w = max(-C.FW_MAX_ANGULAR_RPS, min(C.FW_MAX_ANGULAR_RPS, w))
        half = self.p.track_width_m / 2.0          # the firmware's WHEEL_SEPARATION_M is the same 0.1335 m
        for i, wheel in enumerate((v - w * half, v + w * half)):
            duty = self._wheel_duty(wheel)
            old = self.target[i]
            if old == 0.0 and duty != 0.0:
                self.cut[i] = False                 # the firmware clears a cut-off on any fresh start
                self.blocked_since[i] = None
            if duty == 0.0 or (old != 0.0 and (duty > 0) != (old > 0)):
                self.duty[i] = 0.0                  # a stop or a reversal applies at once, then ramps from 0
                self.cut[i] = False                 # a fresh start clears a cut-off
                self.blocked_since[i] = None
            self.target[i] = duty
        self.status = T.DRIVE_STOPPED if self.target == [0.0, 0.0] else T.DRIVE_DRIVING

    def _wheel_duty(self, wheel_speed):
        fraction = max(-1.0, min(1.0, wheel_speed / self.p.map_max_speed_mps))
        if abs(fraction) < C.FW_DUTY_DEADBAND_FRACTION:
            return 0.0
        duty = self.p.map_min_duty + (1.0 - self.p.map_min_duty) * abs(fraction)
        return math.copysign(duty, fraction)

    def _stop_drive(self, status):
        self.target = [0.0, 0.0]
        self.duty = [0.0, 0.0]
        self.status = status

    # ------------------------------------------------------------ time

    def step(self, dt):
        p = self.p
        self.t += dt
        t = self.t
        due = [c for c in self._cmd_in if c[0] <= t]
        if due:
            self._cmd_in = [c for c in self._cmd_in if c[0] > t]
            for _at, v, w, stamp, marker in due:
                self._receive(v, w, stamp, marker)
        if p.agent_alive and int(t) != int(t - dt):
            self.last_rx_t = t                      # the agent's time sync, once a second
        # the command timeout (drive_control_update) and, behind it, the deadman timer
        if self.status == T.DRIVE_DRIVING and t - self.last_cmd_t > C.FW_COMMAND_TIMEOUT_S:
            self._stop_drive(T.DRIVE_TIMEOUT_STOP)
        blocked = (p.blocked_left, p.blocked_right)
        gains = (p.left_gain, p.right_gain)
        for i in (0, 1):
            target = 0.0 if self.cut[i] else self.target[i]
            if abs(target) <= abs(self.duty[i]) or target == 0.0:
                self.duty[i] = target
            else:
                step = dt / C.FW_RAMP_FULL_S
                self.duty[i] = math.copysign(min(abs(target), abs(self.duty[i]) + step), target)
            duty = self.duty[i]
            steady = 0.0
            if abs(duty) >= p.duty_stick and not blocked[i]:
                steady = math.copysign(p.speed_per_duty_mps * abs(duty) * gains[i], duty)
            if blocked[i]:
                self.speed[i] = 0.0
                if self.target[i] != 0.0 and not self.cut[i]:
                    if self.blocked_since[i] is None:
                        self.blocked_since[i] = t
                    elif t - self.blocked_since[i] >= p.cutoff_after_s:
                        self.cut[i] = True
                        self.cutoffs += 1
            else:
                self.blocked_since[i] = None
                self.speed[i] += (steady - self.speed[i]) * min(1.0, dt / p.tau_s)
                if steady == 0.0 and abs(self.speed[i]) < 0.005:    # friction ends the run-down
                    self.speed[i] = 0.0
            self.travel[i] += self.speed[i] * dt
        body_l = self.speed[0] * (1.0 - p.slip_left)
        body_r = self.speed[1] * (1.0 - p.slip_right)
        v = (body_l + body_r) / 2.0
        omega = (body_r - body_l) / p.track_width_m
        self.x += v * math.cos(self.theta + omega * dt / 2.0) * dt
        self.y += v * math.sin(self.theta + omega * dt / 2.0) * dt
        self.theta += omega * dt
        self.distance_after_last_cmd += abs(v) * dt
        self.max_abs_speed = max(self.max_abs_speed, abs(v))
        self.max_abs_rate_dps = max(self.max_abs_rate_dps, abs(math.degrees(omega)))
        while self._next_tel <= t + 1e-9:
            self._emit_telemetry(self._next_tel)
            self._next_tel += C.FW_TELEMETRY_PERIOD_S

    def _emit_telemetry(self, t):
        p = self.p
        self.seq += 1
        imu_fail = _in(p.imu_fail, t)
        if imu_fail:
            self.imu_fails += 1
        yaw = (p.yaw0_deg + math.degrees(self.theta) + 180.0) % 360.0 - 180.0
        flags = ((T.FLAG_STBY if self.status == T.DRIVE_DRIVING else 0) | (T.FLAG_ARMED if self.armed else 0)
                 | (T.FLAG_IMU_READY if p.imu_ready else 0) | (self.status << T.FLAG_STATUS_SHIFT)
                 | (T.FLAG_CLOCK_OK if p.clock_ok else 0) | (T.FLAG_NEED_MARKER if self.need_marker else 0)
                 | (T.FLAG_CUT_LEFT if self.cut[0] else 0) | (T.FLAG_CUT_RIGHT if self.cut[1] else 0))
        age = -1 if self.last_rx_t is None else int(round((t - self.last_rx_t) * 1000))
        data = T.encode_wheel_ticks(
            left=_to_int32(self.left0 + int(math.floor(self.travel[0] * self.ticks_per_m[0] + 0.5))),
            right=_to_int32(self.right0 + int(math.floor(self.travel[1] * self.ticks_per_m[1] + 0.5))),
            uptime_ms=int(round((t - self.boot_t) * 1000)), seq=self.seq, flags=flags,
            vsys_min_mv=p.vsys_mv, vsys_max_mv=p.vsys_mv,
            yaw_cdeg=0 if imu_fail else int(round(yaw * 100)), imu_fails=self.imu_fails, commands=self.commands,
            boot_report=1100, sessions=self.sessions, stale_cmds=self.stale, cutoffs=self.cutoffs,
            agent_rx_age_ms=age, duty_left=int(round(self.duty[0] * 1000)), duty_right=int(round(self.duty[1] * 1000)),
            drive_map=T.pack_drive_map(p.map_min_duty, p.map_max_speed_mps))
        if not _in(p.telemetry_drop, t):
            self._tel_out.append((t + p.telemetry_delay_s, data))

    def pop_telemetry(self):
        """The telemetry arrays that have reached the host by now, oldest first."""
        due = [d for at, d in self._tel_out if at <= self.t + 1e-9]
        if due:
            self._tel_out = [(at, d) for at, d in self._tel_out if at > self.t + 1e-9]
        return due

    # ------------------------------------------------------------ truth, for tests

    @property
    def moving(self):
        return abs(self.speed[0]) > 1e-6 or abs(self.speed[1]) > 1e-6

    def truth(self):
        return {"x_m": self.x, "y_m": self.y, "theta_deg": math.degrees(self.theta)}
