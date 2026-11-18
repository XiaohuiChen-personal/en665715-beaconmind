"""Wheel counts and IMU heading to motion in the robot frame (plan/README.md contract C1).

Heading comes from the IMU (the gyro-based yaw the firmware reports), distance from the two encoders with a scale
per wheel. Each telemetry sample adds one small chord at its mid-heading; summed over a move this is the motion
"since the previous observation, in the robot frame at that observation" of C1 (forward, left, heading change),
and for a move of constant curvature it equals C1's single-chord formula, which chord_c1() also gives.

Counts are 32-bit and wrap; headings wrap at +-180 degrees. Both are handled here and nowhere else.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this odometry module.
"""
import math
from dataclasses import dataclass


def wrap_deg(angle):
    """Wrap to (-180, 180]."""
    a = (angle + 180.0) % 360.0 - 180.0
    return 180.0 if a == -180.0 else a


def tick_delta(new, old):
    """new - old for two 32-bit counters, correct across the wrap from 2^31 - 1 to -2^31."""
    return ((int(new) - int(old) + (1 << 31)) % (1 << 32)) - (1 << 31)


def sinc(x):
    return 1.0 if abs(x) < 1e-9 else math.sin(x) / x


def chord_c1(s_m, dtheta_rad):
    """C1's formula: arc length s and heading change dtheta to (forward_m, left_m) in the starting robot frame."""
    c = s_m * sinc(dtheta_rad / 2.0)
    return c * math.cos(dtheta_rad / 2.0), c * math.sin(dtheta_rad / 2.0)


def encoder_yaw_deg(s_left_m, s_right_m, track_width_m):
    """The heading change the two wheels alone imply (used to compare against the gyro: the D5 slip rule)."""
    return math.degrees((s_right_m - s_left_m) / track_width_m)


@dataclass(frozen=True)
class OdomState:
    """Totals since the Odometer was created. x, y, theta are in its own frame (the pose at its first sample)."""
    x_m: float = 0.0
    y_m: float = 0.0
    theta_deg: float = 0.0      # unwrapped: can exceed +-180
    left_ticks: int = 0
    right_ticks: int = 0
    s_left_m: float = 0.0
    s_right_m: float = 0.0
    car_time_s: float = 0.0     # the car's own uptime at the last sample, s
    samples: int = 0


def delta_between(a, b):
    """Motion from state a to state b in the robot frame at a: the C1 odometry of an observation, plus the
    signed counts and wheel distances a move result needs."""
    dx, dy = b.x_m - a.x_m, b.y_m - a.y_m
    th = math.radians(a.theta_deg)
    return {"forward_m": dx * math.cos(th) + dy * math.sin(th),
            "left_m": -dx * math.sin(th) + dy * math.cos(th),
            "dtheta_deg": b.theta_deg - a.theta_deg,
            "left_ticks": b.left_ticks - a.left_ticks, "right_ticks": b.right_ticks - a.right_ticks,
            "s_left_m": b.s_left_m - a.s_left_m, "s_right_m": b.s_right_m - a.s_right_m}


class Odometer:
    """Integrates telemetry samples. Feed every sample with update(); read state at any time.

    When a sample's heading is not valid (the IMU read failed: the firmware then reports yaw 0), that sample's
    heading change is taken from the wheels instead, and the next valid heading re-anchors the difference, so one
    bad read neither jumps the heading nor loses the turn made meanwhile.
    """

    def __init__(self, ticks_per_m_left, ticks_per_m_right, track_width_m):
        self.kl = float(ticks_per_m_left)
        self.kr = float(ticks_per_m_right)
        self.track = float(track_width_m)
        self.state = OdomState()
        self._last = None           # (left, right, yaw_deg or None)
        self.imu_substitutions = 0  # samples whose heading change came from the wheels

    def reset_reference(self):
        """Forget the last sample (after a restart of the car its counters start again)."""
        self._last = None

    def update(self, left, right, yaw_deg, car_time_s, yaw_valid=True):
        st = self.state
        if self._last is None:
            self._last = (left, right, yaw_deg if yaw_valid else None)
            self.state = OdomState(st.x_m, st.y_m, st.theta_deg, st.left_ticks, st.right_ticks, st.s_left_m,
                                   st.s_right_m, car_time_s, st.samples + 1)
            return self.state
        l0, r0, yaw0 = self._last
        dl, dr = tick_delta(left, l0), tick_delta(right, r0)
        sl, sr = dl / self.kl, dr / self.kr
        if yaw_valid and yaw0 is not None:
            dth = math.radians(wrap_deg(yaw_deg - yaw0))
        else:
            dth = (sr - sl) / self.track
            self.imu_substitutions += 1
        s = (sl + sr) / 2.0
        mid = math.radians(st.theta_deg) + dth / 2.0
        c = s * sinc(dth / 2.0)
        self._last = (left, right, yaw_deg if yaw_valid else None)
        self.state = OdomState(st.x_m + c * math.cos(mid), st.y_m + c * math.sin(mid),
                               st.theta_deg + math.degrees(dth), st.left_ticks + dl, st.right_ticks + dr,
                               st.s_left_m + sl, st.s_right_m + sr, car_time_s, st.samples + 1)
        return self.state
