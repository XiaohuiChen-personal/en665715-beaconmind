"""The ROS 2 side of the car package: the executor's node, the out-of-band STOP program, a simulated-car node.

rclpy and the message packages are imported inside the functions that need them, so this module imports (and its
pure parts are tested) on a machine without ROS.

Topics and QoS are the firmware's (Build K2, pico_fusion.c): the car publishes /pico/wheel_ticks
(std_msgs/Int32MultiArray, 50 Hz), /pico/imu/data (sensor_msgs/Imu) and /pico/drive/status (std_msgs/Int32,
1 Hz), all best effort, and subscribes /pico/cmd_vel (geometry_msgs/Twist) and /pico/imu/std
(std_msgs/Float32MultiArray), both best effort. So every subscription here uses the sensor-data profile (best
effort), and commands are published best effort with a queue of one: a command that could not be delivered is
replaced by the next one, never re-sent late.

RosCarLink publishes on /pico/cmd_vel only while a move runs: the motion commands at the command period, then
zeros until the car has settled. Idle, it publishes nothing; with the STOP latch set it refuses to start and never
sends a motion command.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote the node, the STOP program and the simulated-car
node.
"""
import json
import os
import sys
import threading
import time

from . import config as C
from .executor import ZERO, MoveExecutor
from .latch import Latch
from .link import car_state_from
from .movelog import MoveLog, data_root
from .moves import make_result
from .telemetry import LayoutError, decode_wheel_ticks, yaw_from_quaternion

CMD_TOPIC = "/pico/cmd_vel"
TICKS_TOPIC = "/pico/wheel_ticks"
IMU_TOPIC = "/pico/imu/data"
STATUS_TOPIC = "/pico/drive/status"
IMU_STD_TOPIC = "/pico/imu/std"
LATCHED_ZERO_PERIOD_S = 0.02    # while the latch exists the STOP program sends a zero this often (50 per second)
REAL_CAR_DOMAIN = 0             # the micro-ROS agent of the real car runs on ROS_DOMAIN_ID 0 (tools/record_session.sh)


def ros_domain_id():
    try:
        return int(os.environ.get("ROS_DOMAIN_ID", "0") or 0)
    except ValueError:
        return 0


def twist_fields(cmd, unix_time):
    """The four Twist fields the firmware reads, for one Command: linear.x, angular.z, the send time in linear.z
    for a stamped motion command (zeros go unstamped: a stop must never be judged too old), angular.x 0."""
    stamped = cmd.stamp and not cmd.is_zero
    return {"linear_x": float(cmd.v), "angular_z": float(cmd.w), "linear_z": float(unix_time) if stamped else 0.0,
            "angular_x": 0.0}


# ---------------------------------------------------------------- STOP: pure parts

def stop_heartbeat_path(root=None):
    return os.path.join(root or data_root(), "STOP_ALIVE")


def write_heartbeat(path, now_unix=None, extra=None):
    """The STOP program writes this twice a second, so the move tool can refuse to move without it."""
    record = {"pid": os.getpid(), "t_unix": time.time() if now_unix is None else now_unix}
    if extra:
        record.update(extra)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = "%s.tmp.%d" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(record, handle)
    os.replace(tmp, path)


def stop_program_alive(path=None, max_age_s=2.0, now_unix=None, domain=None):
    """True when the STOP program's heartbeat is fresh and, when `domain` is given, the program runs on that ROS
    domain and sees a subscriber on /pico/cmd_vel (a STOP program on another domain cannot stop this car)."""
    try:
        with open(path or stop_heartbeat_path(), encoding="utf-8") as handle:
            record = json.load(handle)
        now = time.time() if now_unix is None else now_unix
        if domain is not None and (record.get("domain") != domain or not record.get("subscribers")):
            return False
        return 0 <= now - float(record["t_unix"]) <= max_age_s
    except (OSError, ValueError, KeyError, TypeError):
        return False


def key_action(ch):
    """What a key means in the STOP program: SPACE or s stops, q asks to quit, anything else is ignored."""
    if ch in (" ", "s", "S"):
        return "stop"
    if ch in ("q", "Q"):
        return "quit"
    return None


def keys_to_actions(data):
    """The action of every key in a chunk read from the terminal, in order (None for keys that mean nothing)."""
    return [key_action(ch) for ch in data.decode("utf-8", "replace")]


def stop_now(publish_zero, latch, reason, by, flood_s=3.0, rate_hz=100.0, sleep=time.sleep, clock=time.monotonic):
    """The STOP action. The first zero command goes out before anything else; then the latch file is written;
    then zeros keep going at rate_hz for flood_s. The flood is what stops a car that some other program is still
    commanding: on this firmware a zero drops the duty to 0 at once and a following motion command has to ramp up
    again, so with a zero every 10 ms the wheels get no power to speak of. Returns the latch record."""
    publish_zero()
    error = None
    try:
        record = latch.set(reason, by)
    except OSError as exc:      # keep stopping the car even if the disk refuses the file
        record, error = None, "%s: %s" % (type(exc).__name__, exc)
    period = 1.0 / rate_hz
    end = clock() + flood_s
    while clock() < end:
        publish_zero()
        sleep(period)
    if error:
        raise OSError("STOP was sent, but the latch file could not be written: " + error)
    return record


# ---------------------------------------------------------------- the executor's node

class RosCarLink:
    """The executor on ROS 2 (the real car, or the simulated-car node on another domain). See link.py for the
    interface. One instance per process; execute() blocks until the move is over."""

    def __init__(self, cfg=None, latch=None, log_root=None, node_name="bm_car_executor", wait_telemetry_s=5.0,
                 read_only=False):
        """read_only=True creates no publisher at all: the node can only listen (the tool's `state` command)."""
        import rclpy
        from geometry_msgs.msg import Twist
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
        from rclpy.signals import SignalHandlerOptions
        from sensor_msgs.msg import Imu
        from std_msgs.msg import Int32, Int32MultiArray

        self.cfg = cfg or C.load_config()
        self.latch = latch if latch is not None else Latch()
        self.log_root = log_root
        self.domain = ros_domain_id()
        self._Twist = Twist
        self._lock = threading.RLock()
        self._event = threading.Event()
        self._waiting = False
        self._result = None
        self._movelog = None
        self.layout_error = None
        self.drive_status = None
        self.imu_last = None            # (monotonic time, yaw deg, gyro z rad/s) of the last /pico/imu/data
        self.published = 0
        self.executor = MoveExecutor(self.cfg, latch=self.latch, log=self._log)
        self.read_only = read_only
        self._lock_handle = None
        if not read_only:
            # one program at a time may command the car: an exclusive lock on a file beside the latch
            import fcntl
            lock_path = os.path.join(log_root or data_root(), "CAR_LINK.lock")
            os.makedirs(os.path.dirname(lock_path), exist_ok=True)
            self._lock_handle = open(lock_path, "a+", encoding="utf-8")
            try:
                fcntl.flock(self._lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                self._lock_handle.close()
                raise RuntimeError("another program holds the car link (%s): only one may command the car"
                                   % lock_path) from exc
            self._load_state()
        self._own_context = not rclpy.ok()
        if self._own_context:
            # no rclpy signal handlers: Ctrl+C must reach execute(), which stops the car before the context closes
            rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
        self._rclpy = rclpy
        self.node = rclpy.create_node(node_name)
        command_qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT, history=HistoryPolicy.KEEP_LAST, depth=1)
        self._pub = None if read_only else self.node.create_publisher(Twist, CMD_TOPIC, command_qos)
        self._std_pub = None
        self.node.create_subscription(Int32MultiArray, TICKS_TOPIC, self._on_ticks, qos_profile_sensor_data)
        self.node.create_subscription(Imu, IMU_TOPIC, self._on_imu, qos_profile_sensor_data)
        self.node.create_subscription(Int32, STATUS_TOPIC, self._on_status, qos_profile_sensor_data)
        self.node.create_timer(self.cfg.command_period_s, self._on_timer)
        self._spinner = SingleThreadedExecutor()
        self._spinner.add_node(self.node)
        self._thread = threading.Thread(target=self._spin, name="bm_car_executor_spin", daemon=True)
        self._thread.start()
        end = time.monotonic() + wait_telemetry_s
        while self.executor.tel is None and time.monotonic() < end:
            time.sleep(0.02)

    # ------------------------------------------------------------ callbacks (the spin thread)

    def _spin(self):
        try:
            self._spinner.spin()
        except Exception as exc:    # noqa: BLE001 - the spin thread must not die silently with a move running
            self.spin_error = "%s: %s" % (type(exc).__name__, exc)
            self._event.set()

    spin_error = None

    def _log(self, record):
        log = self._movelog
        if log is not None:
            log.write(record)

    def _publish(self, cmd):
        if cmd is None or self._pub is None:
            return
        fields = twist_fields(cmd, time.time())
        msg = self._Twist()
        msg.linear.x, msg.angular.z = fields["linear_x"], fields["angular_z"]
        msg.linear.z, msg.angular.x = fields["linear_z"], fields["angular_x"]
        self._pub.publish(msg)
        self.published += 1

    def _after(self):
        if self._waiting and not self.executor.busy:
            result = self.executor.take_result()
            if result is not None:
                self._result = result
                self._event.set()

    def _on_ticks(self, msg):
        now = time.monotonic()
        try:
            tel = decode_wheel_ticks(msg.data, now)
        except LayoutError as exc:
            self.layout_error = str(exc)
            return
        with self._lock:
            self._publish(self.executor.on_telemetry(tel))
            self._after()

    def _on_timer(self):
        with self._lock:
            self._publish(self.executor.tick(time.monotonic()))
            self._after()

    def _on_imu(self, msg):
        q = msg.orientation
        self.imu_last = (time.monotonic(), yaw_from_quaternion(q.w, q.x, q.y, q.z), msg.angular_velocity.z)

    def _on_status(self, msg):
        self.drive_status = int(msg.data)

    # ------------------------------------------------------------ the link interface

    @property
    def last_diag(self):
        return self.executor.last_diag

    def zero_burst(self, n=6, gap_s=0.03):
        """Zeros straight from the calling thread: used when a move is cut short from outside."""
        for _ in range(n):
            with self._lock:
                self._publish(ZERO)
            time.sleep(gap_s)

    def _spin_alive(self):
        return self.spin_error is None and self._thread.is_alive()

    def execute(self, cmd):
        seq = cmd.get("cmd_seq") if isinstance(cmd, dict) else None
        try:
            with self._lock:
                why = ("read_only" if self.read_only else "busy" if self._waiting else
                       "spin_thread_died" if not self._spin_alive() else
                       "telemetry_layout: " + self.layout_error
                       if self.layout_error is not None and self.executor.tel is None else None)
                if why is not None:
                    return make_result(seq, "refused", why, boot_id=self.executor.boots)
                self._movelog = MoveLog(root=self.log_root)
                if isinstance(cmd, dict):
                    self._movelog.begin(cmd, self.cfg, {"ros_domain_id": self.domain, "node": self.node.get_name(),
                                                        "learned": self.executor.export_state()})
                refused = self.executor.start(cmd, time.monotonic())
                if refused is not None:
                    return refused
                self._event.clear()
                self._result = None
                self._waiting = True
                self._publish(self.executor.tick(time.monotonic()))     # the first command goes out at once
            deadline = time.monotonic() + float(cmd["timeout_s"]) + self.cfg.settle_max_s * (self.cfg.max_trims + 1) + 3.0
            while self._result is None and self._spin_alive() and time.monotonic() < deadline:
                self._event.wait(0.1)           # in slices: a dead spin thread is noticed within 0.1 s
            if self._result is None:
                why = "host_wait_timeout" if self._spin_alive() else "spin_thread_died"
                with self._lock:
                    self._publish(self.executor.abort("link_lost", why, time.monotonic()))
                self.zero_burst()
                end = time.monotonic() + self.cfg.settle_max_s + 1.0
                while self._result is None and self._spin_alive() and time.monotonic() < end:
                    self._event.wait(0.1)
                with self._lock:
                    if self._result is None:        # nobody is ticking the executor: end the move by hand
                        self.executor.tick(time.monotonic() + self.cfg.settle_max_s + 1.0)
                        self._result = self.executor.take_result() or make_result(
                            seq, "link_lost", why, boot_id=self.executor.boots)
            return self._result
        except BaseException:
            with self._lock:
                busy = self.executor.busy
                if busy:
                    self._publish(self.executor.abort("link_lost", "interrupted", time.monotonic()))
            if busy:
                self.zero_burst()
            raise
        finally:
            with self._lock:
                self._waiting = False
                self._finish_log()
                self._save_state()

    def _finish_log(self):
        log, self._movelog = self._movelog, None
        if log is not None:
            self.last_log_path = log.finish()
            self.last_log_error = log.error

    def _state_path(self):
        return os.path.join(self.log_root or data_root(), "car_executor_state.json")

    def _load_state(self):
        try:
            with open(self._state_path(), encoding="utf-8") as handle:
                self.executor.import_state(json.load(handle))
        except (OSError, ValueError):
            pass

    def _save_state(self):
        """Keep what the executor learned about the car (governor factor, coast times) for the next process."""
        if self.read_only:
            return
        try:
            path = self._state_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = "%s.tmp.%d" % (path, os.getpid())
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(dict(self.executor.export_state(), t_unix=round(time.time(), 1)), handle)
            os.replace(tmp, path)
        except OSError:
            pass

    last_log_path = None
    last_log_error = None

    def odom_state(self):
        with self._lock:
            return self.executor.odom.state

    def car_state(self):
        with self._lock:
            state = car_state_from(self.executor, time.monotonic())
        state.update({"ros_domain_id": self.domain, "drive_status": self.drive_status,
                      "layout_error": self.layout_error, "latched": self.latch.is_set(),
                      "imu_topic_age_s": None if self.imu_last is None else round(time.monotonic() - self.imu_last[0], 3),
                      "cmd_vel_subscribers": None if self._pub is None else self._pub.get_subscription_count()})
        return state

    def wait(self, seconds):
        time.sleep(seconds)

    def arm(self, timeout_s=6.0):
        """Operator action: send the firmware's arm marker (a zero command with angular.x = 1.0) until the car
        reports itself armed. Refused while the STOP latch is set. Returns True when armed."""
        end = time.monotonic() + timeout_s
        while time.monotonic() < end:
            # checked before every marker: a STOP during these seconds must not be followed by re-arming
            if self._pub is None or self.latch.is_set() or self.executor.busy:
                return False
            msg = self._Twist()
            msg.angular.x = C.FW_ARM_MARKER
            with self._lock:
                self._pub.publish(msg)
                tel = self.executor.tel
            if tel is not None and tel.armed and time.monotonic() - tel.t_rx < 0.5:
                return True
            time.sleep(0.05)
        return False

    def set_drive_map(self, min_duty, max_speed_mps, timeout_s=4.0):
        """Operator action: set the firmware's open-loop drive map through /pico/imu/std (values 4 and 5; the first
        three 0 = unchanged), twice a second until the car reports it in telemetry. Returns the map the car reports."""
        from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
        from std_msgs.msg import Float32MultiArray
        if self.read_only or self.latch.is_set():
            return None
        if self._std_pub is None:
            qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT, history=HistoryPolicy.KEEP_LAST, depth=1)
            self._std_pub = self.node.create_publisher(Float32MultiArray, IMU_STD_TOPIC, qos)
            time.sleep(0.5)     # discovery
        end = time.monotonic() + timeout_s
        while time.monotonic() < end:
            msg = Float32MultiArray()
            msg.data = [0.0, 0.0, 0.0, float(min_duty), float(max_speed_mps)]
            self._std_pub.publish(msg)
            time.sleep(0.5)
            tel = self.executor.tel
            if tel is not None and abs(tel.map_min_duty - min_duty) < 0.0015 \
                    and abs(tel.map_max_speed_mps - max_speed_mps) < 0.0015:
                break
        tel = self.executor.tel
        return None if tel is None else [tel.map_min_duty, tel.map_max_speed_mps]

    def close(self):
        try:
            with self._lock:
                busy = self.executor.busy
                if busy:
                    self._publish(self.executor.abort("link_lost", "closed", time.monotonic()))
            if busy:
                self.zero_burst()
        finally:
            self._spinner.shutdown()
            self._thread.join(timeout=2.0)
            self.node.destroy_node()
            if self._own_context:
                self._rclpy.try_shutdown()
            if self._lock_handle is not None:
                self._lock_handle.close()       # releases the car-link lock


# ---------------------------------------------------------------- the STOP program

BANNER = """
  #####  #######  #####  ######
 #          #    #     # #     #
  #####     #    #     # ######
       #    #    #     # #
  #####     #     #####  #          sent
"""


def stop_main(argv=None):
    """The out-of-band STOP program (plan task M3.T13). It runs in its own terminal, in its own process, so it
    works when the harness hangs. SPACE (or s): zero commands at once and for 3 s, the latch file, a banner.
    While the latch exists it keeps sending a zero 50 times a second. q then y quits.
    The hard stop remains the motor battery's switch (safety rule S7)."""
    import argparse
    ap = argparse.ArgumentParser(prog="car_move.py stop-key", description=stop_main.__doc__.split("\n")[0])
    ap.add_argument("--latch", help="latch file (default: course-project/data/LATCH)")
    ap.add_argument("--now", action="store_true", help="send STOP once and exit (no keyboard)")
    ap.add_argument("--by", default="bm_stop")
    args = ap.parse_args(argv)

    import rclpy
    from geometry_msgs.msg import Twist
    from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
    from std_msgs.msg import Int32MultiArray

    latch = Latch(args.latch)
    heartbeat = stop_heartbeat_path(os.path.dirname(latch.path))
    if args.now:
        try:                    # the latch first: it stops the host side at once, before ROS is even up
            latch.set("operator STOP (car_move.py stop)", args.by)
        except OSError as exc:
            print("latch file not written (%s); sending zeros anyway" % exc, file=sys.stderr)
    rclpy.init()
    node = rclpy.create_node("bm_stop")
    qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT, history=HistoryPolicy.KEEP_LAST, depth=1)
    pub = node.create_publisher(Twist, CMD_TOPIC, qos)
    seen = {"tel": None, "bad": None}

    def on_ticks(msg):
        try:
            seen["tel"] = decode_wheel_ticks(msg.data, time.monotonic())
        except LayoutError as exc:
            seen["bad"] = str(exc)

    node.create_subscription(Int32MultiArray, TICKS_TOPIC, on_ticks, qos_profile_sensor_data)

    def zero():
        pub.publish(Twist())

    def spin_some():
        rclpy.spin_once(node, timeout_sec=0.0)

    if args.now:
        time.sleep(0.3)         # discovery: the first zeros of the flood may be lost, the rest are not
        stop_now(zero, latch, "operator STOP (car_move.py stop)", args.by)
        print("STOP sent; latch file %s" % latch.path)
        node.destroy_node()
        rclpy.try_shutdown()
        return 0

    import select
    import termios
    import tty
    fd = sys.stdin.fileno()
    if not os.isatty(fd):
        print("stop-key needs a terminal (docker run -it ...). For a one-shot stop: car_move.py stop", file=sys.stderr)
        return 2
    saved = termios.tcgetattr(fd)
    print("STOP program on ROS_DOMAIN_ID %d. SPACE or s = STOP (zero commands + latch %s). q then y = quit.\r"
          % (ros_domain_id(), latch.path))
    quit_armed = False
    exit_code = 0
    next_beat = next_zero = next_line = 0.0
    try:
        tty.setcbreak(fd)
        while True:
            now = time.monotonic()
            spin_some()
            if now >= next_beat:
                next_beat = now + 0.5
                try:
                    write_heartbeat(heartbeat, extra={"domain": ros_domain_id(),
                                                      "subscribers": pub.get_subscription_count()})
                except OSError as exc:
                    print("heartbeat file not written: %s\r" % exc)
            latched = latch.is_set()
            if latched and now >= next_zero:
                next_zero = now + LATCHED_ZERO_PERIOD_S     # for as long as the latch exists, not only 3 s
                zero()
            if now >= next_line:
                next_line = now + 1.0
                tel = seen["tel"]
                if tel is None:
                    car = "no telemetry" + (" (%s)" % seen["bad"] if seen["bad"] else "")
                else:
                    car = "telemetry %.1f s old, %s, drive status %d" % (
                        now - tel.t_rx, "armed" if tel.armed else "DISARMED", tel.drive_status)
                sys.stdout.write("\r%s | %s | subscribers on %s: %d   " % (
                    "LATCHED (zeros flowing)" if latched else "latch clear", car, CMD_TOPIC,
                    pub.get_subscription_count()))
                sys.stdout.flush()
            ready, _, _ = select.select([fd], [], [], 0.01)
            if not ready:
                continue
            # raw bytes from the terminal, all that are waiting: a buffered read would hold back a SPACE typed
            # right after another key until a third key arrived
            data = os.read(fd, 1024)
            if not data:
                print("\r\nthe terminal is gone (end of input): STOP keys cannot be read. Restart stop-key.\r")
                exit_code = 3
                break
            actions = keys_to_actions(data)
            if "stop" in actions:
                quit_armed = False
                try:
                    stop_now(zero, latch, "operator STOP (key)", args.by)
                    print("\r\n" + BANNER.replace("\n", "\r\n") + "\r\nlatch: %s\r" % latch.path)
                except OSError as exc:
                    print("\r\nSTOP SENT, but: %s\r" % exc)
                actions = actions[len(actions) - actions[::-1].index("stop"):]     # what was typed after the last STOP
                termios.tcflush(fd, termios.TCIFLUSH)       # keys hit during the 3 s flood are dropped, not replayed
            leave = False
            for action in actions:
                if action == "quit":
                    if quit_armed:
                        leave = True
                        break
                    quit_armed = True
                    print("\r\nquit? press q again (any other key cancels)\r")
                else:
                    quit_armed = False
            if leave:
                break
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)
        try:
            os.remove(heartbeat)
        except OSError:
            pass
        node.destroy_node()
        rclpy.try_shutdown()
        print("\nSTOP program ended.")
    return exit_code


# ---------------------------------------------------------------- a simulated car as a ROS node (tests only)

def run_sim_car_node(params=None, duration_s=None, ready_file=None):
    """The simulated car of simcar.py on the real topics, for the rclpy smoke test. It refuses ROS_DOMAIN_ID 0:
    that is the real car's domain, and two cars answering on its topics would corrupt a run."""
    if ros_domain_id() == REAL_CAR_DOMAIN:      # checked before anything of ROS is touched
        raise RuntimeError("the simulated car does not run on ROS_DOMAIN_ID 0 (the real car's domain)")
    import math

    import rclpy
    from geometry_msgs.msg import Twist
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Imu
    from std_msgs.msg import Int32, Int32MultiArray

    from .simcar import SimCar
    sim = SimCar(params)
    sim.unix_time = time.time
    rclpy.init()
    node = rclpy.create_node("bm_sim_car")
    ticks_pub = node.create_publisher(Int32MultiArray, TICKS_TOPIC, qos_profile_sensor_data)
    imu_pub = node.create_publisher(Imu, IMU_TOPIC, qos_profile_sensor_data)
    status_pub = node.create_publisher(Int32, STATUS_TOPIC, qos_profile_sensor_data)
    lock = threading.Lock()

    def on_cmd(msg):
        with lock:
            sim.send(msg.linear.x, msg.angular.z, stamp_unix=msg.linear.z, arm_marker=(msg.angular.x == C.FW_ARM_MARKER))

    node.create_subscription(Twist, CMD_TOPIC, on_cmd, qos_profile_sensor_data)
    clock = {"last": time.monotonic(), "status": 0.0}

    def on_timer():
        now = time.monotonic()
        with lock:
            steps = min(200, int((now - clock["last"]) / 0.001))
            clock["last"] += steps * 0.001
            for _ in range(steps):
                sim.step(0.001)
            arrays = sim.pop_telemetry()
            status = sim.status
        for data in arrays:
            msg = Int32MultiArray()
            msg.data = data
            ticks_pub.publish(msg)
            imu = Imu()
            imu.header.frame_id = "imu_link"
            yaw = math.radians(data[82] / 100.0)
            imu.orientation.w, imu.orientation.z = math.cos(yaw / 2.0), math.sin(yaw / 2.0)
            imu_pub.publish(imu)
        if now - clock["status"] >= 1.0:
            clock["status"] = now
            out = Int32()
            out.data = int(status)
            status_pub.publish(out)

    node.create_timer(0.005, on_timer)
    if ready_file:
        with open(ready_file, "w", encoding="utf-8") as handle:
            handle.write("%d\n" % os.getpid())
    end = None if duration_s is None else time.monotonic() + duration_s
    try:
        while rclpy.ok() and (end is None or time.monotonic() < end):
            rclpy.spin_once(node, timeout_sec=0.05)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
    return sim
