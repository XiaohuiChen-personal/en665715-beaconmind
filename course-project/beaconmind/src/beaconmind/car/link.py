"""The executor coupled to a car. One interface, two cars:

    SimLink                       the simulated car of simcar.py, in its own simulated time (tests, rehearsals)
    ros_io.RosCarLink             the real car, or the simulated-car node, over ROS 2

Both give the same calls, so the environment backend and the command-line tool do not know which they hold:

    execute(cmd) -> result        run one bm.move/1 command to its end; returns the bm.move_result/1 record
    last_diag                     details of the last move (odometry, coast, peaks), not part of the C2 record
    odom_state()                  the odometer's totals now (see odometry.OdomState)
    car_state()                   {"telemetry_age_s", "armed", "imu_ready", "boots", "drive_map", ...} or None fields
    wait(seconds)                 let time pass (the car settles, telemetry keeps arriving)
    arm() / set_drive_map(d, s)   operator actions, only called from the command-line tool
    close()

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote the link interface and the simulated link.
"""
from . import config as C
from .executor import MoveExecutor
from .simcar import EPOCH_S, SimCar
from .telemetry import decode_wheel_ticks


def car_state_from(executor, now):
    """What a caller may want to know about the car before or after a move, from the last telemetry sample."""
    tel = executor.tel
    if tel is None:
        return {"telemetry_age_s": None, "armed": None, "imu_ready": None, "clock_ok": None, "drive_map": None,
                "boots": executor.boots, "busy": executor.busy, "uptime_ms": None, "boot_report": None,
                "sessions": None, "cutoffs": None, "locked": None, "left_ticks": None, "right_ticks": None,
                "yaw_deg": None, "lost_samples": executor.lost_samples, "drive_status": None, "vsys_min_mv": None,
                "agent_rx_age_ms": None, "imu_fails": None}
    return {"telemetry_age_s": round(now - tel.t_rx, 3), "armed": tel.armed, "imu_ready": tel.imu_ready,
            "clock_ok": tel.clock_ok, "drive_map": [tel.map_min_duty, tel.map_max_speed_mps],
            "boots": executor.boots, "busy": executor.busy, "uptime_ms": tel.uptime_ms,
            "boot_report": tel.boot_report, "sessions": tel.sessions, "cutoffs": tel.cutoffs, "locked": tel.locked,
            "left_ticks": tel.left, "right_ticks": tel.right, "yaw_deg": tel.yaw_deg,
            "lost_samples": executor.lost_samples, "drive_status": tel.drive_status, "vsys_min_mv": tel.vsys_min_mv,
            "agent_rx_age_ms": tel.agent_rx_age_ms, "imu_fails": tel.imu_fails}


class SimLink:
    """The executor and a SimCar stepped together, 1 ms at a time, with no wall clock.

    host_alive = False models a host that died: the executor is no longer called and nothing is published, while
    the car's time goes on. on_step(link) is called every step, for tests that change something at a set time.
    """

    def __init__(self, cfg, sim=None, latch=None, log=None, dt=0.001):
        self.cfg = cfg
        self.sim = sim or SimCar()
        self.executor = MoveExecutor(cfg, latch=latch, log=log)
        self.dt = dt
        self.t = 0.0
        self.host_alive = True
        self.on_step = None
        self.published = []             # (t, v, w) of every command sent, for tests
        self._next_tick = 0.0
        self.wait(0.2)                  # the first telemetry samples

    @property
    def last_diag(self):
        return self.executor.last_diag

    def _publish(self, cmd):
        if cmd is None:
            return
        self.published.append((self.t, cmd.v, cmd.w))
        self.sim.send(cmd.v, cmd.w, stamp_unix=(EPOCH_S + self.t) if cmd.stamp else 0.0)

    def _step(self):
        self.sim.step(self.dt)
        self.t = self.sim.t
        if self.on_step is not None:
            self.on_step(self)
        if not self.host_alive:
            self.sim.pop_telemetry()
            return
        for data in self.sim.pop_telemetry():
            self._publish(self.executor.on_telemetry(decode_wheel_ticks(data, self.t)))
        if self.t + 1e-9 >= self._next_tick:
            self._next_tick = self.t + self.cfg.command_period_s
            self._publish(self.executor.tick(self.t))

    def wait(self, seconds):
        end = self.t + seconds
        while self.t < end - 1e-9:
            self._step()

    def execute(self, cmd, max_s=15.0):
        refused = self.executor.start(cmd, self.t)
        if refused is not None:
            return refused
        self._next_tick = self.t            # the first command goes out at once
        end = self.t + max_s
        while self.t < end:
            self._step()
            result = self.executor.take_result()
            if result is not None:
                return result
        raise RuntimeError("the simulated move did not end within %.1f s" % max_s)

    def odom_state(self):
        return self.executor.odom.state

    def car_state(self):
        return car_state_from(self.executor, self.t)

    def arm(self):
        for _ in range(10):
            self.sim.send(0.0, 0.0, arm_marker=True)
            self.wait(0.05)
        return self.car_state()["armed"]

    def set_drive_map(self, min_duty, max_speed_mps):
        self.sim.set_map(min_duty, max_speed_mps)
        self.wait(0.1)
        return self.car_state()["drive_map"]

    def close(self):
        pass


def default_sim_link(latch=None, log=None, **sim_params):
    """A SimLink on the project's configs (tests and the fake-car mode of the backend)."""
    from .simcar import SimCarParams
    cfg = C.load_config()
    return SimLink(cfg, SimCar(SimCarParams(**sim_params)), latch=latch, log=log)
