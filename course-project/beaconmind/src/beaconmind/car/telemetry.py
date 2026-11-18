"""The car's /pico/wheel_ticks message (std_msgs/Int32MultiArray, "layout 9") as one Telemetry sample.

Field numbers are the firmware's enum TK_* (private course repo, assignments/assignment8/module-8-sensor-fusion/
firmware/pico_fusion/pico_fusion.c, Build K2 rev b). The Module 8 host tools read fields 2, 3, 14, 38, 50 and 63
the same way (odometry/move_test.py), and Module 9's carpet_tune.sh reads 0, 1, 28, 48 and 81. Checked on
2026-11-18 against a recorded bag of the parked car: every message has 84 fields, field 2 is 9, field 82 is the
yaw of /pico/imu/data in hundredths of a degree, field 81 decodes to the boot drive map 0.46 / 0.215.

Only the fields the executor uses are named here.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this decoder.
"""
import math
from dataclasses import dataclass

LAYOUT_VERSION = 9
N_FIELDS = 84

TK_LEFT = 0             # wheel counts since power-on; both count up when the car drives forward (encoders.h)
TK_RIGHT = 1
TK_LAYOUT = 2
TK_UPTIME_MS = 3        # ms since this boot: falls after a restart
TK_SEQ = 4              # wheel_ticks messages sent since this boot: a gap = messages lost on the way
TK_VSYS_MIN_MV = 5      # the Pico's own supply (VSYS), lowest and highest since the previous message, mV
TK_VSYS_MAX_MV = 6
TK_DUTY_LEFT = 12       # applied duty x 1000, signed
TK_DUTY_RIGHT = 13
TK_FLAGS = 14
TK_IMU_FAILS = 18       # failed IMU reads since boot
TK_COMMANDS = 20        # cmd_vel messages the drive accepted since boot
TK_BOOT_REPORT = 21     # 1000 + 100 x boot kind + last phase before the reset (safety.h)
TK_ASSISTS = 28         # start-assists since boot
TK_SESSIONS = 38        # micro-ROS sessions since boot (a reconnect adds one)
TK_STALE_CMDS = 41      # stamped commands dropped as older than 300 ms
TK_CUTOFFS = 48         # stall cut-offs since boot
TK_AGENT_RX_AGE_MS = 50 # ms since the car last heard any datagram from the agent (-1: none yet)
TK_DISARMS = 63         # bits 0-15: silence disarms since boot
TK_DRIVE_MAP = 81       # smallest duty x 1000 (bits 0-15) | full-PWM wheel speed in mm/s (bits 16-31)
TK_YAW_CDEG = 82        # IMU yaw of the last read, hundredths of a degree, counter-clockwise positive
                        # (0 if that read failed; the zero is wherever the IMU was at power-on)

FLAG_STBY = 1 << 0              # motor driver enabled
FLAG_ARMED = 1 << 1
FLAG_IMU_READY = 1 << 2
FLAG_USB_POWER = 1 << 3
FLAG_STATUS_SHIFT = 4           # bits 4-5: drive status
FLAG_ASSIST = 1 << 6            # a start-assist is running
FLAG_CLOCK_OK = 1 << 7          # the car has a clock offset, so it can judge stamped commands
FLAG_NEED_MARKER = 1 << 8       # re-arming needs the arm marker
FLAG_CUT_LEFT = 1 << 9
FLAG_CUT_RIGHT = 1 << 10
FLAG_LOCK_LEFT = 1 << 11
FLAG_LOCK_RIGHT = 1 << 12
FLAG_SILENCE_DISARMED = 1 << 13

DRIVE_STOPPED = 0               # /pico/drive/status and flags bits 4-5 (drive_control.h)
DRIVE_DRIVING = 1
DRIVE_TIMEOUT_STOP = 2


class LayoutError(ValueError):
    """The array is not Build K2's layout 9, so its fields cannot be trusted."""


@dataclass(frozen=True)
class Telemetry:
    t_rx: float             # host monotonic time when the message arrived, s
    left: int               # counts (int32, may wrap)
    right: int
    uptime_ms: int
    seq: int
    flags: int
    yaw_deg: float          # (-180, 180], counter-clockwise positive
    imu_fails: int
    commands: int
    boot_report: int
    assists: int
    sessions: int
    stale_cmds: int
    cutoffs: int
    agent_rx_age_ms: int
    disarms: int
    duty_left: float
    duty_right: float
    map_min_duty: float
    map_max_speed_mps: float
    vsys_min_mv: int = 0    # the Pico's supply, not the motor battery (the motors run from their own pack)

    @property
    def armed(self):
        return bool(self.flags & FLAG_ARMED)

    @property
    def imu_ready(self):
        return bool(self.flags & FLAG_IMU_READY)

    @property
    def clock_ok(self):
        return bool(self.flags & FLAG_CLOCK_OK)

    @property
    def assisting(self):
        return bool(self.flags & FLAG_ASSIST)

    @property
    def drive_status(self):
        return (self.flags >> FLAG_STATUS_SHIFT) & 3

    @property
    def cut_off(self):
        """(left, right): the firmware holds that wheel at 0 after a stall (cut off or locked)."""
        f = self.flags
        return (bool(f & (FLAG_CUT_LEFT | FLAG_LOCK_LEFT)), bool(f & (FLAG_CUT_RIGHT | FLAG_LOCK_RIGHT)))

    @property
    def locked(self):
        return bool(self.flags & (FLAG_LOCK_LEFT | FLAG_LOCK_RIGHT))

    def brief(self):
        """The fields worth logging with every sample of a move."""
        return {"t_rx": round(self.t_rx, 4), "up_ms": self.uptime_ms, "seq": self.seq, "l": self.left,
                "r": self.right, "yaw": round(self.yaw_deg, 2), "flags": self.flags,
                "duty": [round(self.duty_left, 3), round(self.duty_right, 3)], "age_ms": self.agent_rx_age_ms,
                "stale": self.stale_cmds, "cut": self.cutoffs, "assists": self.assists}


def decode_wheel_ticks(data, t_rx):
    """Telemetry from the message's data array. Raises LayoutError unless it is layout 9 with all its fields."""
    n = len(data)
    if n < N_FIELDS:
        raise LayoutError("wheel_ticks has %d fields; Build K2 layout %d has %d" % (n, LAYOUT_VERSION, N_FIELDS))
    if int(data[TK_LAYOUT]) != LAYOUT_VERSION:
        raise LayoutError("wheel_ticks layout %d; this code reads layout %d" % (int(data[TK_LAYOUT]), LAYOUT_VERSION))
    drive_map = int(data[TK_DRIVE_MAP]) & 0xFFFFFFFF
    return Telemetry(
        t_rx=float(t_rx), left=int(data[TK_LEFT]), right=int(data[TK_RIGHT]), uptime_ms=int(data[TK_UPTIME_MS]),
        seq=int(data[TK_SEQ]), flags=int(data[TK_FLAGS]), yaw_deg=int(data[TK_YAW_CDEG]) / 100.0,
        imu_fails=int(data[TK_IMU_FAILS]), commands=int(data[TK_COMMANDS]), boot_report=int(data[TK_BOOT_REPORT]),
        assists=int(data[TK_ASSISTS]), sessions=int(data[TK_SESSIONS]), stale_cmds=int(data[TK_STALE_CMDS]),
        cutoffs=int(data[TK_CUTOFFS]), agent_rx_age_ms=int(data[TK_AGENT_RX_AGE_MS]),
        disarms=int(data[TK_DISARMS]) & 0xFFFF, duty_left=int(data[TK_DUTY_LEFT]) / 1000.0,
        duty_right=int(data[TK_DUTY_RIGHT]) / 1000.0, map_min_duty=(drive_map & 0xFFFF) / 1000.0,
        map_max_speed_mps=((drive_map >> 16) & 0xFFFF) / 1000.0, vsys_min_mv=int(data[TK_VSYS_MIN_MV]))


def encode_wheel_ticks(**fields):
    """A layout-9 array with the given TK_* fields set and the rest 0 (the simulated car and the tests use it).
    Keyword names are the lower-case field names without the TK_ prefix, e.g. left=, flags=, yaw_cdeg=."""
    index = {name[3:].lower(): value for name, value in globals().items() if name.startswith("TK_")}
    data = [0] * N_FIELDS
    data[TK_LAYOUT] = LAYOUT_VERSION
    data[TK_AGENT_RX_AGE_MS] = -1
    for name, value in fields.items():
        data[index[name]] = int(value)
    return data


def pack_drive_map(min_duty, max_speed_mps):
    """Field 81 for a drive map, as a signed 32-bit integer."""
    raw = (int(round(min_duty * 1000)) & 0xFFFF) | ((int(round(max_speed_mps * 1000)) & 0xFFFF) << 16)
    return raw - (1 << 32) if raw >= (1 << 31) else raw


def yaw_from_quaternion(w, x, y, z):
    """Yaw in degrees of a ROS quaternion (the heading the firmware also sends as field 82)."""
    return math.degrees(math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z)))
