"""The bounded-move executor: one C2 move as a stream of velocity commands, closed on the car's own telemetry.

The car's firmware (Build K2) drives open loop: a velocity command becomes a duty through a two-number map, and
the wheels then turn as fast as the motors, the floor and the battery allow. So this executor never trusts a
commanded speed. A straight move ends on the wheel counts, a turn on the IMU heading, each a little early by the
distance the car coasts (measured speed x coast time); straights hold the starting heading with a proportional
steering term strong enough for the carpet; the forward speed is held under the design limit by a governor.

The executor is a state machine with no clock and no I/O of its own:

    start(cmd, now)        -> a `refused` result, or None when the move started
    on_telemetry(sample)   -> a zero Command to publish at once when this sample ended the move, else None
    tick(now)              -> the Command to publish now, or None (idle: publish nothing)
    take_result()          -> the bm.move_result/1 record once the move is over, else None

`now` and each sample's t_rx are the caller's monotonic clock. The caller publishes what it is given and nothing
else. Safety does not depend on any message of this executor arriving: every motion command is good for 0.5 s on
the car (its command timeout), so if this process, the link or the host dies, the car stops by itself. The zeros
sent at the end only make the stop prompt.

Checks while a move runs (the order of plan task M3.T6's firmware executor, adapted). On every command tick: STOP
latch, telemetry gap (0.5 s: link_lost), timeout; with no sample for 0.12 s the tick sends a zero (the car pauses
until samples return). On every telemetry sample: STOP latch, link (car disarmed, car not hearing, the car's own
timeout stop, restart, session rebuilt, stale commands), IMU, stall, completion.

Result mapping, all `bm.move_result/1`: `done`; `stalled` (reason stall_left / stall_right / firmware_cutoff);
`timeout`; `link_lost` (reason says which link rule, or `imu`, or `estop` for a STOP during the move: the
proposed default of open decision OD15, option a); `refused` (never started; the reason says why). `bumped` is
never produced: no bump threshold was ever approved (plan M3.T6 step 1), so bump detection is off.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this executor.
"""
import math
from collections import deque
from dataclasses import dataclass

from . import config as C
from .moves import check_move, make_result, target_of
from .odometry import Odometer, delta_between, encoder_yaw_deg
from .telemetry import DRIVE_TIMEOUT_STOP

IDLE, RUN, STOPPING = "idle", "run", "stopping"


@dataclass(frozen=True)
class Command:
    """One velocity command for /pico/cmd_vel. stamp: put the send time in linear.z (motion commands only)."""
    v: float            # m/s, forward positive
    w: float            # rad/s, counter-clockwise (left) positive
    stamp: bool = False
    why: str = "run"

    @property
    def is_zero(self):
        return self.v == 0.0 and self.w == 0.0


ZERO = Command(0.0, 0.0, False, "stop")


def _clamp(value, limit):
    return max(-limit, min(limit, value))


class MoveExecutor:
    def __init__(self, cfg, latch=None, log=None):
        """cfg: ExecutorConfig. latch: a Latch or None (no latch: tests of the control law only).
        log: a callable taking one dict, called for every command, sample and event of a move."""
        self.cfg = cfg
        self.latch = latch
        self.log = log
        self.odom = Odometer(cfg.ticks_per_m_left, cfg.ticks_per_m_right, cfg.track_width_m)
        self.phase = IDLE
        self.tel = None                 # the last accepted sample
        self.boots = 0                  # restarts of the car seen since this executor started
        self.lost_samples = 0           # telemetry messages that never arrived (gaps in the car's sequence number)
        self.out_of_order = 0
        self.last_diag = None           # details of the last finished move (not part of the C2 record)
        self._window = deque()          # (car time s, s_left m, s_right m, theta deg) for the speed estimate
        self._rates = (0.0, 0.0, 0.0, 0.0)   # v mean m/s, left m/s, right m/s, yaw rate deg/s
        self._yaw_bad_since = None      # t_rx of the first of the latest run of samples without a valid heading
        self._yaw_ok = False            # the last sample's heading was valid
        self._governor = {"straight": cfg.governor_start, "turn": 1.0}     # kept from move to move
        self._coast = {"straight": cfg.coast_start_straight_s, "turn": cfg.coast_start_turn_s}   # adapted
        self._restart_run = []          # consecutive samples that look like a restarted car
        self.latch_failed = None        # a latch this executor had to set could not be written
        self._result = None
        self._m = None                  # the running move's state
        self.last_error = None          # the last internal error, if any

    # ------------------------------------------------------------ public state

    @property
    def busy(self):
        return self.phase != IDLE

    def take_result(self):
        result, self._result = self._result, None
        return result

    def export_state(self):
        """What the executor learned about this car (the governor's factor, the coast times), to keep between
        processes."""
        return {"governor": dict(self._governor), "coast": dict(self._coast)}

    def import_state(self, state):
        """Take learned values saved by export_state(); anything missing or out of range is ignored."""
        cfg = self.cfg
        try:
            for kind in ("straight", "turn"):
                g = float(state["governor"][kind])
                if cfg.governor_min <= g <= 1.0:
                    self._governor[kind] = g
                c = float(state["coast"][kind])
                if cfg.coast_time_min_s <= c <= cfg.coast_time_max_s:
                    self._coast[kind] = c
        except (KeyError, TypeError, ValueError):
            pass

    def _set_latch(self, reason):
        """Set the latch on the executor's own account; a failed write is remembered and refuses every later move."""
        if self.latch is None or not self.cfg.latch_on_link_lost:
            return
        try:
            self.latch.set(reason, "executor")
        except OSError as exc:
            self.latch_failed = "%s: %s" % (type(exc).__name__, exc)

    def rates(self):
        """(forward speed m/s, yaw rate deg/s) measured over the last rate window."""
        return self._rates[0], self._rates[3]

    # ------------------------------------------------------------ telemetry

    def on_telemetry(self, tel):
        try:
            return self._on_telemetry(tel)
        except Exception as exc:   # noqa: BLE001 - whatever went wrong, the car gets a stop
            return self._fault(exc, tel.t_rx)

    def _on_telemetry(self, tel):
        prev = self.tel
        if prev is not None:
            if tel.uptime_ms < prev.uptime_ms and tel.seq < prev.seq:
                # an older clock AND a lower sequence number: a restarted car, or one late sample. A restart is
                # believed when three such samples follow each other; a late one is followed by newer samples.
                run = self._restart_run
                if run and tel.seq > run[-1].seq and tel.uptime_ms > run[-1].uptime_ms:
                    run.append(tel)
                else:
                    self._restart_run = run = [tel]
                if len(run) >= 3:
                    self._restart_run = []
                    return self._car_restarted(tel)
                self.out_of_order += 1
                return None
            self._restart_run = []
            if tel.uptime_ms <= prev.uptime_ms:
                self.out_of_order += 1          # a late copy: the newer sample already counted
                return None
            if tel.seq > prev.seq + 1:
                self.lost_samples += tel.seq - prev.seq - 1
        yaw_valid = tel.imu_ready and (prev is None or tel.imu_fails == prev.imu_fails)
        self.tel = tel
        self._note_yaw(yaw_valid, tel.t_rx)
        state = self.odom.update(tel.left, tel.right, tel.yaw_deg, tel.uptime_ms / 1000.0, yaw_valid)
        self._update_rates(state)
        if self.log and self.phase != IDLE:
            self.log(dict(tel.brief(), ev="tel", yaw_ok=yaw_valid))
        if prev is not None and tel.sessions != prev.sessions and self.phase == RUN:
            return self._stop("link_lost", "session_rebuilt", tel.t_rx)
        if self.phase == RUN:
            return self._check_run(tel, state)
        if self.phase == STOPPING:
            m = self._m
            if prev is not None and (abs(tel.left - prev.left) + abs(tel.right - prev.right)) >= 2:
                m["last_motion_t"] = tel.t_rx
            powered = tel.duty_left != 0.0 or tel.duty_right != 0.0
            if powered and tel.t_rx - m["t_stop"] > self.cfg.stop_confirm_s:
                m["stop_unconfirmed"] = True        # the wheels were still driven: the stop did not arrive in time
            if tel.agent_rx_age_ms >= self.cfg.link_gap_s * 1000.0 and tel.t_rx - m["t_stop"] > self.cfg.stop_confirm_s:
                m["stop_unconfirmed"] = True        # the car is not hearing the zeros
            m["peak_after_stop"] = max(m["peak_after_stop"], abs(self._rates[0]))
        return None

    def _note_yaw(self, valid, t):
        self._yaw_ok = valid
        if valid:
            self._yaw_bad_since = None
        elif self._yaw_bad_since is None:
            self._yaw_bad_since = t

    def _car_restarted(self, tel):
        """The car's uptime fell: it rebooted. Its counters restarted, so the odometer takes a new reference;
        a running move ends, and the latch is set (plan C5 item 2; section 3.6 hardware procedure 4)."""
        self.boots += 1
        self.tel = tel
        self._window.clear()
        self._rates = (0.0, 0.0, 0.0, 0.0)
        self.odom.reset_reference()
        self.odom.update(tel.left, tel.right, tel.yaw_deg, tel.uptime_ms / 1000.0, tel.imu_ready)
        self._yaw_bad_since = None
        self._note_yaw(tel.imu_ready, tel.t_rx)
        self._set_latch("the car restarted (boot report %d)" % tel.boot_report)
        if self.log:
            self.log({"ev": "car_restarted", "t": tel.t_rx, "boot_report": tel.boot_report, "boots": self.boots})
        if self.phase == RUN:
            return self._stop("link_lost", "car_rebooted", tel.t_rx)
        if self.phase == STOPPING:
            self._m["pending"] = ("link_lost", "car_rebooted")
        return None

    def _update_rates(self, state):
        w = self._window
        w.append((state.car_time_s, state.s_left_m, state.s_right_m, state.theta_deg))
        while len(w) > 2 and w[-1][0] - w[1][0] >= self.cfg.rate_window_s:
            w.popleft()
        dt = w[-1][0] - w[0][0]
        if len(w) >= 2 and dt >= 0.03:
            vl = (w[-1][1] - w[0][1]) / dt
            vr = (w[-1][2] - w[0][2]) / dt
            self._rates = ((vl + vr) / 2.0, vl, vr, (w[-1][3] - w[0][3]) / dt)

    # ------------------------------------------------------------ starting a move

    def start(self, cmd, now):
        """Start a move. Returns a `refused` result, or None when the move is running (then call tick())."""
        refusal = self._why_not(cmd, now)
        seq = cmd.get("cmd_seq") if isinstance(cmd, dict) else None
        if refusal is not None:
            result = make_result(seq, "refused", refusal, boot_id=self.boots)
            if self.log:
                self.log({"ev": "refused", "t": now, "cmd": cmd if isinstance(cmd, dict) else repr(cmd),
                          "reason": refusal})
            return result
        kind, target = target_of(cmd)
        cfg = self.cfg
        self._result = None
        self._m = {
            "cmd": dict(cmd), "kind": kind, "target": target, "t_start": now, "start": self.odom.state,
            "timeout": float(cmd["timeout_s"]),
            "v_cap": min(float(cmd["v_max_mps"]), cfg.v_max_mps),
            "w_cap_rps": min(cfg.w_max_rps, math.radians(min(float(cmd["w_max_dps"]), cfg.turn_rate_dps))),
            "rate_cap_dps": min(float(cmd["w_max_dps"]), cfg.turn_rate_dps),
            "g": self._governor[kind], "coast_time": self._coast[kind], "hold_i": 0.0, "last_tick": None, "t_first_cmd": None, "commands": 0,
            "wheel_cmd": (0.0, 0.0), "stall": [None, None], "stale0": self.tel.stale_cmds,
            "cutoffs0": self.tel.cutoffs, "peak_v": 0.0, "peak_rate": 0.0, "pending": None, "t_stop": None,
            "at_stop": None, "rates_at_stop": None, "last_motion_t": None, "peak_after_stop": 0.0,
            "lost0": self.lost_samples, "subs0": self.odom.imu_substitutions, "last_cmd": ZERO, "pauses": 0,
            "trims": 0, "round_trip": None, "stop_unconfirmed": False, "coast_measured": None, "coast_time0": self._coast[kind],
        }
        self.phase = RUN
        if self.log:
            self.log({"ev": "start", "t": now, "cmd": dict(cmd), "kind": kind, "target": target,
                      "governor": self._m["g"], "scale_source": cfg.scale_source})
        return None

    def _why_not(self, cmd, now):
        cfg = self.cfg
        if self.phase != IDLE:
            return "busy"
        bad = check_move(cmd, cfg)
        if bad:
            return bad
        if self.latch is not None and self.latch.is_set():
            return "latched"
        if self.latch_failed:
            return "latch_write_failed: " + self.latch_failed
        tel = self.tel
        if tel is None or now - tel.t_rx > cfg.blind_pause_s:
            return "no_telemetry"
        if not tel.armed:
            return "car_disarmed"
        if not tel.imu_ready or not self._yaw_ok:
            return "imu_not_ready"
        if tel.locked:
            return "wheel_locked"
        if cfg.stamp_commands and not tel.clock_ok:
            return "no_clock_sync"
        if cfg.expected_drive_map is not None:
            duty, speed = cfg.expected_drive_map
            if abs(tel.map_min_duty - duty) > 0.0015 or abs(tel.map_max_speed_mps - speed) > 0.0015:
                return "drive_map: the car has %.3f / %.3f, the executor's gains are for %.3f / %.3f" % (
                    tel.map_min_duty, tel.map_max_speed_mps, duty, speed)
        if abs(self._rates[0]) > cfg.rest_speed_mps or abs(self._rates[3]) > cfg.rest_rate_dps:
            return "car_moving"
        return None

    # ------------------------------------------------------------ the control tick

    def tick(self, now):
        """The command to publish now; None when idle. Call at the command period (and right after start())."""
        if self.phase == IDLE:
            return None
        try:
            if self.phase == RUN:
                return self._tick_run(now)
            return self._tick_stopping(now)
        except Exception as exc:   # noqa: BLE001
            return self._fault(exc, now)

    def _tick_run(self, now):
        m, cfg, tel = self._m, self.cfg, self.tel
        if self.latch is not None and self.latch.is_set():
            return self._stop("link_lost", "estop", now)
        if now - tel.t_rx > cfg.link_gap_s:
            return self._stop("link_lost", "telemetry_gap", now)
        if now - m["t_start"] > m["timeout"]:
            return self._stop("timeout", "timeout", now)
        if now - tel.t_rx > cfg.blind_pause_s:
            # no fresh counts: pause rather than drive on stale ones (the link rule above ends the move at 0.5 s)
            m["wheel_cmd"] = (0.0, 0.0)
            m["last_tick"] = None
            m["pauses"] += 1
            if self.log:
                self.log({"ev": "cmd", "t": round(now, 4), "v": 0.0, "w": 0.0, "pause": True})
            return Command(0.0, 0.0, False, "pause")
        dt = 0.0 if m["last_tick"] is None else max(0.0, min(now - m["last_tick"], 4 * cfg.command_period_s))
        m["last_tick"] = now
        v, w = self._control(dt)
        v, w = _clamp(v, C.FW_MAX_LINEAR_MPS), _clamp(w, C.FW_MAX_ANGULAR_RPS)
        half = cfg.track_width_m / 2.0
        m["wheel_cmd"] = (v - w * half, v + w * half)
        if m["t_first_cmd"] is None:
            m["t_first_cmd"] = now
        m["commands"] += 1
        cmd = Command(v, w, cfg.stamp_commands, "run")
        m["last_cmd"] = cmd
        if self.log:
            self.log({"ev": "cmd", "t": round(now, 4), "v": round(v, 4), "w": round(w, 4), "g": round(m["g"], 3)})
        return cmd

    def _control(self, dt):
        """(v, w) from the odometry since the move started."""
        m, cfg = self._m, self.cfg
        d = delta_between(m["start"], self.odom.state)
        v_meas, _vl, _vr, rate_dps = self._rates
        if m["kind"] == "straight":
            sign = 1.0 if m["target"] >= 0 else -1.0
            remaining = abs(m["target"]) - sign * (d["s_left_m"] + d["s_right_m"]) / 2.0
            shape = min(m["v_cap"], max(cfg.v_min_mps, cfg.slowdown_per_s * remaining))
            if cfg.govern_linear and dt > 0:
                m["g"] = self._govern(m["g"], abs(v_meas), m["v_cap"], dt)
            err = math.radians(-d["dtheta_deg"])                 # hold the starting heading
            if cfg.hold_integral_per_s2 > 0 and dt > 0:
                limit = cfg.hold_limit_rps / cfg.hold_integral_per_s2
                m["hold_i"] = _clamp(m["hold_i"] + err * dt, limit)
            v = sign * m["g"] * shape
            limit = cfg.hold_limit_rps
            if not cfg.hold_allow_reverse:
                # the firmware answers any reverse command with at least its smallest duty, so a steering term
                # larger than this would throw the inner wheel from forward to full backward: a relay in the loop
                limit = min(limit, abs(v) / (cfg.track_width_m / 2.0))
            w = _clamp(cfg.hold_gain_per_s * err + cfg.hold_integral_per_s2 * m["hold_i"]
                       - cfg.hold_rate_gain_s * math.radians(rate_dps), limit)
            return v, w
        err_deg = m["target"] - d["dtheta_deg"]
        shape = min(m["w_cap_rps"], max(cfg.w_min_rps, cfg.slowdown_per_s * math.radians(abs(err_deg))))
        if cfg.govern_turn and dt > 0:
            m["g"] = self._govern(m["g"], abs(rate_dps), m["rate_cap_dps"], dt)
        return 0.0, math.copysign(m["g"] * shape, err_deg)

    def _govern(self, g, measured, cap, dt):
        error = (cap - measured) / cap
        g += (self.cfg.governor_gain_per_s if error < 0 else self.cfg.governor_rise_per_s) * error * dt
        return max(self.cfg.governor_min, min(1.0, g))

    # ------------------------------------------------------------ checks on each sample of a running move

    def _check_run(self, tel, state):
        m, cfg = self._m, self.cfg
        now = tel.t_rx
        if self.latch is not None and self.latch.is_set():
            return self._stop("link_lost", "estop", now)
        v_meas, _vl, _vr, rate_dps = self._rates
        m["peak_v"] = max(m["peak_v"], abs(v_meas))
        m["peak_rate"] = max(m["peak_rate"], abs(rate_dps))
        # link
        if not tel.armed:
            return self._stop("link_lost", "car_disarmed", now)
        commanding = m["t_first_cmd"] is not None and now - m["t_first_cmd"] > 0.3
        if m["round_trip"] is None and m["t_first_cmd"] is not None and (tel.duty_left != 0.0 or tel.duty_right != 0.0):
            m["round_trip"] = max(0.0, min(C.ROUND_TRIP_MAX_S, now - m["t_first_cmd"]))
        if commanding and tel.agent_rx_age_ms >= cfg.link_gap_s * 1000.0:
            return self._stop("link_lost", "car_not_hearing", now)
        if commanding and tel.drive_status == DRIVE_TIMEOUT_STOP:
            return self._stop("link_lost", "car_command_timeout", now)
        if tel.stale_cmds - m["stale0"] >= cfg.stale_commands_limit:
            return self._stop("link_lost", "stale_commands", now)
        if self._yaw_bad_since is not None and now - self._yaw_bad_since > cfg.imu_gap_s:
            return self._stop("link_lost", "imu", now)
        # stall: the firmware's own cut-off, then the host rule
        # (a flag left from before this move counts only once this move's commands have reached the car: the
        # firmware clears a cut-off on a fresh start; the counter rising is always this move's)
        cut_left, cut_right = tel.cut_off
        if tel.cutoffs > m["cutoffs0"] or (commanding and (cut_left or cut_right)):
            return self._stop("stalled", "firmware_cutoff", now)
        for i, (speed_cmd, s_wheel) in enumerate(zip(m["wheel_cmd"], (state.s_left_m, state.s_right_m))):
            if self._stalled(i, speed_cmd, s_wheel, tel):
                return self._stop("stalled", "stall_left" if i == 0 else "stall_right", now)
        # divergence, then completion
        d = delta_between(m["start"], state)
        if m["kind"] == "straight":
            sign = 1.0 if m["target"] >= 0 else -1.0
            remaining = abs(m["target"]) - sign * (d["s_left_m"] + d["s_right_m"]) / 2.0
            if abs(d["dtheta_deg"]) > cfg.heading_abort_deg:
                # one wheel hardly moving while the other drives is a stall seen through the heading
                left, right = sign * d["s_left_m"], sign * d["s_right_m"]
                if max(left, right) > 0.01 and min(left, right) < 0.2 * max(left, right):
                    return self._stop("stalled", "stall_left" if left < right else "stall_right", now)
                return self._stop("link_lost", "heading_diverged", now)
            if remaining - abs(m["target"]) > C.WRONG_WAY_M:
                return self._stop("link_lost", "wrong_way", now)
            lead = max(0.0, sign * v_meas) * (m["coast_time"] + (m["round_trip"] or 0.0))
            if remaining <= cfg.dist_tol_m + lead:
                return self._stop("done", None, now)
        else:
            err = m["target"] - d["dtheta_deg"]
            toward = 1.0 if m["target"] >= 0 else -1.0
            if toward * d["dtheta_deg"] < -C.WRONG_WAY_DEG:
                return self._stop("link_lost", "wrong_way", now)
            lead = max(0.0, toward * rate_dps) * (m["coast_time"] + (m["round_trip"] or 0.0))
            if toward * err <= cfg.angle_tol_deg + lead:
                return self._stop("done", None, now)
        return None

    def _stalled(self, i, speed_cmd, s_wheel, tel):
        """The host stall rule for wheel i (0 left, 1 right): commanded at least stall_min_command_mps one way
        for the grace time, then less than stall_speed_mps of travel that way over a whole stall window. A
        start-assist of the firmware restarts the watch."""
        cfg, m = self.cfg, self._m
        direction = 0 if abs(speed_cmd) < cfg.stall_min_command_mps else (1 if speed_cmd > 0 else -1)
        watch = m["stall"][i]
        if direction == 0 or tel.assisting or watch is None or watch["dir"] != direction:
            m["stall"][i] = None if direction == 0 else {"dir": direction, "since": tel.t_rx, "t0": None, "s0": 0.0}
            return False
        if tel.t_rx - watch["since"] < cfg.stall_grace_s:
            return False
        if watch["t0"] is None:
            watch["t0"], watch["s0"] = tel.t_rx, s_wheel
            return False
        span = tel.t_rx - watch["t0"]
        if span < cfg.stall_window_s:
            return False
        if (s_wheel - watch["s0"]) * direction < cfg.stall_speed_mps * span:
            return True
        watch["t0"], watch["s0"] = tel.t_rx, s_wheel
        return False

    # ------------------------------------------------------------ stopping and the result

    def abort(self, result, reason, now):
        """End the running move from outside (the node is shutting down, the caller gave up)."""
        if self.phase == RUN:
            return self._stop(result, reason, now)
        return ZERO if self.phase == STOPPING else None

    def _stop(self, result, reason, now):
        m = self._m
        m["pending"] = (result, reason)
        m["t_stop"] = now
        m["at_stop"] = self.odom.state
        m["rates_at_stop"] = self._rates
        m["last_motion_t"] = now
        self.phase = STOPPING
        if self.log:
            self.log({"ev": "stop", "t": round(now, 4), "result": result, "reason": reason})
        return ZERO

    def _measured_coast_time(self, m, coast, rates_at_stop):
        """The coast after the stop decision divided by the speed at that decision, in seconds; None when the car
        was too slow at the decision for the ratio to mean anything."""
        if coast is None:
            return None
        toward = 1.0 if m["target"] >= 0 else -1.0
        if m["kind"] == "turn":
            speed, travelled = toward * rates_at_stop[3], toward * coast["dtheta_deg"]
            floor = C.COAST_ADAPT_MIN_RATE_DPS
        else:
            speed, travelled = toward * rates_at_stop[0], toward * (coast["s_left_m"] + coast["s_right_m"]) / 2.0
            floor = C.COAST_ADAPT_MIN_SPEED_MPS
        if speed < floor:
            return None
        return max(0.0, travelled) / speed

    def _fault(self, exc, now):
        """An internal error: stop, end the move as link_lost (it latches), and say what happened."""
        reason = "executor_error: %s: %s" % (type(exc).__name__, exc)
        self.last_error = reason
        if self.log:
            self.log({"ev": "executor_error", "t": now, "error": reason})
        if self.phase == IDLE:
            return None             # nothing is moving on this executor's account: publish nothing
        if self.phase == RUN and self._m is not None:
            try:
                return self._stop("link_lost", reason, now)
            except Exception:   # noqa: BLE001
                pass
        if self._m is not None:
            self._m["pending"] = ("link_lost", reason)
            if self._m.get("t_stop") is None:
                self._m["t_stop"] = now
        if self.phase != IDLE:
            self._finish(now, degraded=True)
        return ZERO

    def _tick_stopping(self, now):
        m, cfg = self._m, self.cfg
        since = now - m["t_stop"]
        blind = self.tel is None or now - self.tel.t_rx > cfg.link_gap_s
        if blind and m["pending"][0] == "done":
            m["pending"] = ("link_lost", "telemetry_gap_after_stop")   # the stop could not be watched
        # "quiet" needs evidence: samples are still arriving and none of them showed the counts changing
        fresh = self.tel is not None and now - self.tel.t_rx <= 5 * C.FW_TELEMETRY_PERIOD_S
        quiet = fresh and now - m["last_motion_t"] >= cfg.settle_quiet_s
        if since >= cfg.settle_max_s or (since >= cfg.stop_min_s and (quiet or blind)):
            if m["pending"][0] == "done":
                if not quiet:
                    m["stop_unconfirmed"] = True            # still moving, or unseen, when the settle time ran out
                elif not m["stop_unconfirmed"]:
                    self._learn_coast()
                    if self._trim(now):
                        return self._tick_run(now)
            self._finish(now)
        return ZERO

    def _progress(self):
        """(how far short of the target the car is now, in the move's own unit and direction; kind)."""
        m = self._m
        d = delta_between(m["start"], self.odom.state)
        toward = 1.0 if m["target"] >= 0 else -1.0
        if m["kind"] == "turn":
            return abs(m["target"]) - toward * d["dtheta_deg"]
        return abs(m["target"]) - toward * (d["s_left_m"] + d["s_right_m"]) / 2.0

    def _trim(self, now):
        """After a settle: go on with the move when it stopped short by more than the trim threshold."""
        m, cfg = self._m, self.cfg
        short = self._progress()
        limit = cfg.trim_angle_deg if m["kind"] == "turn" else cfg.trim_dist_m
        if short <= limit or m["trims"] >= cfg.max_trims or now - m["t_start"] > m["timeout"] - 0.5:
            return False
        if self.latch is not None and self.latch.is_set():
            return False
        m["trims"] += 1
        m["pending"], m["last_tick"], m["stall"], m["hold_i"] = None, None, [None, None], 0.0
        self.phase = RUN
        if self.log:
            self.log({"ev": "trim", "t": round(now, 4), "short_by": short, "n": m["trims"]})
        return True

    def _learn_coast(self):
        """Measure this stop's coast time and adapt the value the next move of this kind starts with."""
        m, cfg = self._m, self.cfg
        if m["at_stop"] is None or m["rates_at_stop"] is None:
            return
        measured = self._measured_coast_time(m, delta_between(m["at_stop"], self.odom.state), m["rates_at_stop"])
        if measured is None or m["trims"] > 0:      # only the first approach of a move, made at speed, teaches
            return
        m["coast_measured"] = measured
        measured = max(0.0, measured - (m["round_trip"] or 0.0))
        if cfg.adapt_coast:
            w = cfg.coast_adapt_weight
            new = max(cfg.coast_time_min_s, min(cfg.coast_time_max_s, (1.0 - w) * m["coast_time"] + w * measured))
            self._coast[m["kind"]] = m["coast_time"] = new

    def _finish(self, now, degraded=False):
        m, cfg = self._m, self.cfg
        result, reason = m["pending"]
        end = self.odom.state
        try:
            d = delta_between(m["start"], end)
            coast = delta_between(m["at_stop"], end) if m["at_stop"] is not None else None
        except Exception:   # noqa: BLE001
            degraded = True
        if degraded:
            d = {"forward_m": 0.0, "left_m": 0.0, "dtheta_deg": 0.0, "left_ticks": 0, "right_ticks": 0,
                 "s_left_m": 0.0, "s_right_m": 0.0}
            coast = None
        mean = (d["s_left_m"] + d["s_right_m"]) / 2.0
        if result == "done" and not degraded:
            # `done` means the stop arrived and the car ended where the executor decided, not merely that it decided
            toward = 1.0 if m["target"] >= 0 else -1.0
            past = (toward * d["dtheta_deg"] - abs(m["target"]) if m["kind"] == "turn"
                    else toward * mean - abs(m["target"]))
            if m["stop_unconfirmed"]:
                result, reason = "link_lost", "stop_not_confirmed"
            elif past > (cfg.overshoot_deg if m["kind"] == "turn" else cfg.overshoot_m):
                result, reason = "link_lost", "overshoot"
        self._result = make_result(
            m["cmd"].get("cmd_seq"), result, reason, boot_id=self.boots, duration_s=now - m["t_start"],
            enc_left_ticks=d["left_ticks"], enc_right_ticks=d["right_ticks"], gyro_dyaw_deg=d["dtheta_deg"],
            achieved_forward_m=mean, stall=(result == "stalled"), bump=False)
        enc_yaw = encoder_yaw_deg(d["s_left_m"], d["s_right_m"], cfg.track_width_m)
        rates_at_stop = m["rates_at_stop"] or (0.0, 0.0, 0.0, 0.0)
        self.last_diag = {
            "action": m["cmd"].get("action"), "kind": m["kind"], "target": m["target"],
            "odometry": {"forward_m": d["forward_m"], "left_m": d["left_m"], "dtheta_deg": d["dtheta_deg"]},
            "s_left_m": d["s_left_m"], "s_right_m": d["s_right_m"], "encoder_yaw_deg": enc_yaw,
            "yaw_disagree_deg": abs(enc_yaw - d["dtheta_deg"]),
            "coast_m": None if coast is None else (coast["s_left_m"] + coast["s_right_m"]) / 2.0,
            "coast_deg": None if coast is None else coast["dtheta_deg"],
            "speed_at_stop_mps": rates_at_stop[0], "rate_at_stop_dps": rates_at_stop[3],
            "peak_speed_mps": m["peak_v"], "peak_rate_dps": m["peak_rate"],
            "over_speed_limit": m["peak_v"] > m["v_cap"] * 1.1,
            "over_rate_limit": m["peak_rate"] > m["rate_cap_dps"] * 1.1,
            "governor": m["g"], "commands": m["commands"], "settle_s": now - (m["t_stop"] or now),
            "lost_samples": self.lost_samples - m["lost0"], "blind_pauses": m["pauses"],
            "imu_substitutions": self.odom.imu_substitutions - m["subs0"],
            "scale_source": cfg.scale_source, "degraded": degraded,
        }
        if m["kind"] in self._governor and not degraded:
            self._governor[m["kind"]] = m["g"]
        self.last_diag.update({"coast_time_used_s": m["coast_time0"], "coast_time_measured_s": m["coast_measured"],
                               "coast_time_next_s": self._coast[m["kind"]], "trims": m["trims"],
                               "round_trip_s": m["round_trip"],
                               "stop_unconfirmed": m["stop_unconfirmed"]})
        if result == "link_lost" and reason != "estop":
            self._set_latch("a move ended link_lost (%s)" % reason)
            if self.latch_failed:
                self.last_diag["latch_error"] = self.latch_failed
        self.phase = IDLE
        if self.log:
            self.log({"ev": "result", "t": round(now, 4), "result": dict(self._result), "diag": dict(self.last_diag)})
        self._m = None
