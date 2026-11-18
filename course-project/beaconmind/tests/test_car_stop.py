"""The STOP latch, the out-of-band STOP action, the move tool's refusals and the move log (work list 2.7; plan
M3.T13, contract C5 item 5).

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote these tests.
"""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import beaconmind
from beaconmind.car import config as C
from beaconmind.car import ros_io
from beaconmind.car.executor import ZERO, Command
from beaconmind.car.latch import Latch, default_latch_path
from beaconmind.car.link import SimLink
from beaconmind.car.movelog import MoveLog, active_session_dir, moves_dir
from beaconmind.car.moves import make_move
from beaconmind.car.simcar import SimCar, SimCarParams
from beaconmind.schemas import validate

CFG = C.load_config()
TOOLS = Path(__file__).resolve().parents[2] / "tools"


def load_tool():
    spec = importlib.util.spec_from_file_location("car_move", TOOLS / "car_move.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------- the latch file

def test_default_path_is_course_data_latch():
    assert default_latch_path() == str(beaconmind.course_root() / "data" / "LATCH")       # plan C5 item 5
    assert Latch().path == default_latch_path()


def test_set_read_clear(tmp_path):
    latch = Latch(tmp_path / "data" / "LATCH")                 # the folder does not exist yet
    assert not latch.is_set() and latch.read() is None and latch.clear("xiaohui") is None
    record = latch.set("operator STOP (key)", "bm_stop")
    assert latch.is_set() and latch.read() == record
    assert record["reason"] == "operator STOP (key)" and record["by"] == "bm_stop" and record["time_utc"].endswith("Z")
    assert Latch(latch.path).is_set()                          # another process sees it: it is a file
    cleared = latch.clear("xiaohui")
    assert cleared == record and not latch.is_set()
    events = [json.loads(line) for line in open(latch.path + ".log")]
    assert [e["event"] for e in events] == ["set", "clear"] and events[1]["operator"] == "xiaohui"


def test_clear_needs_an_operator_name(tmp_path):
    latch = Latch(tmp_path / "LATCH")
    latch.set("x", "test")
    for name in ("", "   ", None):
        with pytest.raises(ValueError):
            latch.clear(name)
    assert latch.is_set()


def test_first_cause_is_kept(tmp_path):
    latch = Latch(tmp_path / "LATCH")
    latch.set("operator STOP (key)", "bm_stop")
    latch.set("a move ended link_lost (telemetry_gap)", "executor")
    assert latch.read()["by"] == "bm_stop"


def test_unreadable_latch_still_counts_as_set(tmp_path):
    path = tmp_path / "LATCH"
    path.write_text("not json")
    latch = Latch(path)
    assert latch.is_set() and "unreadable" in latch.read()["reason"]
    path.write_text("")
    assert latch.is_set()


# ---------------------------------------------------------------- STOP and the executor

def test_latched_executor_refuses_and_sends_nothing(tmp_path):
    latch = Latch(tmp_path / "LATCH")
    latch.set("operator STOP (key)", "bm_stop")
    link = SimLink(CFG, SimCar(SimCarParams()), latch=latch)
    for action in ("FORWARD_25", "TURN_LEFT_30", "BACKWARD_10"):
        result = link.execute(make_move(action, 1, "t"))
        assert validate("move_result", result) == []
        assert (result["result"], result["reason"]) == ("refused", "latched")
    link.wait(1.0)
    assert link.published == []                                # never publishes while latched
    assert link.sim.truth() == {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
    latch.clear("xiaohui")                                     # only the operator's action lets it move again
    assert link.execute(make_move("FORWARD_10", 2, "t"))["result"] == "done"


@pytest.mark.parametrize("action", ["FORWARD_25", "TURN_RIGHT_30"])
def test_stop_during_a_move(tmp_path, action):
    latch = Latch(tmp_path / "LATCH")
    link = SimLink(CFG, SimCar(SimCarParams()), latch=latch)
    stop_at = 0.2 + (0.6 if action == "FORWARD_25" else 0.2)   # 0.2 s: the link's warm-up
    pressed = []

    def press(l):
        if l.t >= stop_at and not pressed:
            pressed.append(l.t)
            latch.set("operator STOP (key)", "bm_stop")        # what the STOP program does, from its own process
    link.on_step = press
    result = link.execute(make_move(action, 1, "t"))
    assert validate("move_result", result) == []
    assert (result["result"], result["reason"]) == ("link_lost", "estop")      # OD15 option a (proposed default)
    after = [(t, v, w) for t, v, w in link.published if t >= pressed[0]]
    assert after and all((v, w) == (0.0, 0.0) for _t, v, w in after)           # no motion command after STOP
    assert after[0][0] - pressed[0] <= 0.025                   # the next telemetry sample (20 ms) carries the stop
    link.on_step = None
    link.wait(0.5)
    assert not link.sim.moving
    assert latch.read()["by"] == "bm_stop"                     # the executor did not overwrite the cause
    assert link.execute(make_move("FORWARD_10", 2, "t"))["reason"] == "latched"


def test_stop_now_sends_a_zero_before_the_latch_and_then_floods(tmp_path):
    latch = Latch(tmp_path / "LATCH")
    order, clock = [], [0.0]

    def publish_zero():
        order.append("zero" if latch.is_set() else "zero-before-latch")

    def sleep(dt):
        clock[0] += dt
    record = ros_io.stop_now(publish_zero, latch, "operator STOP (key)", "bm_stop", flood_s=3.0, rate_hz=100.0,
                             sleep=sleep, clock=lambda: clock[0])
    assert order[0] == "zero-before-latch"                     # the motors do not wait for a file write
    assert order.count("zero-before-latch") == 1 and 290 <= order.count("zero") <= 310
    assert latch.is_set() and record["by"] == "bm_stop"


def test_stop_now_still_floods_when_the_latch_cannot_be_written(tmp_path):
    class BrokenLatch:
        path = "x"

        def set(self, reason, by):
            raise PermissionError("disk says no")
    sent, clock = [], [0.0]
    with pytest.raises(OSError, match="STOP was sent"):
        ros_io.stop_now(lambda: sent.append(1), BrokenLatch(), "r", "b", flood_s=1.0, rate_hz=100.0,
                        sleep=lambda dt: clock.__setitem__(0, clock[0] + dt), clock=lambda: clock[0])
    assert len(sent) >= 100


def test_zero_flood_stops_a_car_that_another_program_keeps_commanding():
    """The STOP program cannot silence another publisher. On this firmware a zero drops the duty at once and the
    next motion command has to ramp up again, so a zero every 10 ms leaves the wheels without power."""
    sim = SimCar(SimCarParams())
    for i in range(1000):                                      # 1 s of a rogue 20 Hz forward command: the car runs
        if i % 50 == 0:
            sim.send(0.15, 0.0)
        sim.step(0.001)
    assert sim.moving and sim.truth()["x_m"] > 0.05
    for i in range(400):                                       # STOP: zeros at 100 Hz, the rogue still at 20 Hz
        if i % 50 == 3:
            sim.send(0.15, 0.0)
        if i % 10 == 0:
            sim.send(0.0, 0.0)
        sim.step(0.001)
    x = sim.truth()["x_m"]
    for i in range(2600):
        if i % 50 == 3:
            sim.send(0.15, 0.0)
        if i % 10 == 0:
            sim.send(0.0, 0.0)
        sim.step(0.001)
    assert not sim.moving
    assert sim.truth()["x_m"] - x < 0.002                      # no progress in the last 2.6 s of the flood


def test_key_action():
    assert ros_io.key_action(" ") == "stop" and ros_io.key_action("s") == "stop" and ros_io.key_action("S") == "stop"
    assert ros_io.key_action("q") == "quit"
    for other in ("a", "\n", "x", "\x1b", ""):
        assert ros_io.key_action(other) is None


def test_no_key_is_lost_when_several_arrive_together():
    assert ros_io.keys_to_actions(b"a ") == [None, "stop"]                 # SPACE right after another key still stops
    assert ros_io.keys_to_actions(b"qq") == ["quit", "quit"]
    assert ros_io.keys_to_actions(b"\x1b[A s") == [None, None, None, "stop", "stop"]      # an arrow key, then SPACE, s
    assert ros_io.keys_to_actions(b"\xff") == [None]


def test_stop_heartbeat(tmp_path):
    path = str(tmp_path / "data" / "STOP_ALIVE")
    assert not ros_io.stop_program_alive(path)
    ros_io.write_heartbeat(path, now_unix=1000.0)
    assert ros_io.stop_program_alive(path, now_unix=1001.5)
    assert not ros_io.stop_program_alive(path, now_unix=1002.5)        # older than 2 s: the program died
    Path(path).write_text("garbage")
    assert not ros_io.stop_program_alive(path)


# ---------------------------------------------------------------- what goes on the wire

def test_twist_fields():
    motion = ros_io.twist_fields(Command(0.12, -0.4, True), 1.8e9)
    assert motion == {"linear_x": 0.12, "angular_z": -0.4, "linear_z": 1.8e9, "angular_x": 0.0}
    assert ros_io.twist_fields(Command(0.12, 0.0, False), 1.8e9)["linear_z"] == 0.0
    stop = ros_io.twist_fields(ZERO, 1.8e9)
    assert stop == {"linear_x": 0.0, "angular_z": 0.0, "linear_z": 0.0, "angular_x": 0.0}   # never stamped, never the arm marker
    assert ros_io.twist_fields(Command(0.0, 0.0, True), 1.8e9)["linear_z"] == 0.0


def test_ros_io_imports_without_ros():
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
    code = ("import sys, beaconmind.car.ros_io, beaconmind.car.backend, beaconmind.car.link; "
            "assert 'rclpy' not in sys.modules, 'rclpy was imported at module import time'")
    done = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


def test_the_real_domain_is_zero_and_the_sim_car_refuses_it(monkeypatch):
    assert ros_io.REAL_CAR_DOMAIN == 0
    monkeypatch.setenv("ROS_DOMAIN_ID", "42")
    assert ros_io.ros_domain_id() == 42
    monkeypatch.delenv("ROS_DOMAIN_ID")
    assert ros_io.ros_domain_id() == 0                         # unset means the real car's domain
    for value in ("0", ""):
        monkeypatch.setenv("ROS_DOMAIN_ID", value)
        with pytest.raises(RuntimeError, match="ROS_DOMAIN_ID 0"):
            ros_io.run_sim_car_node(duration_s=0.1)            # refuses before it touches ROS


# ---------------------------------------------------------------- the move tool

def test_tool_refuses_a_real_move_without_the_acknowledgement(tmp_path, capsys):
    tool = load_tool()
    code = tool.main(["--latch", str(tmp_path / "LATCH"), "move", "FORWARD_25"])
    assert code == 2 and "--i-am-at-the-car" in capsys.readouterr().err
    assert tool.main(["--latch", str(tmp_path / "LATCH"), "arm"]) == 2


def test_tool_preflight(tmp_path):
    tool = load_tool()
    data = tmp_path / "data"
    latch = Latch(data / "LATCH")
    problems = tool.preflight_real_move(latch, str(data), domain=0)
    assert len(problems) == 2 and "recorder" in problems[0] and "STOP program" in problems[1]
    (data / "real" / "20261118-120000-floor").mkdir(parents=True)
    (data / "real" / ".active").write_text("20261118-120000-floor\n")
    beat = ros_io.stop_heartbeat_path(str(data))
    ros_io.write_heartbeat(beat, extra={"domain": 42, "subscribers": 1})
    assert "STOP program" in tool.preflight_real_move(latch, str(data), domain=0)[0]       # a STOP on another domain
    ros_io.write_heartbeat(beat, extra={"domain": 0, "subscribers": 0})
    assert "STOP program" in tool.preflight_real_move(latch, str(data), domain=0)[0]       # a STOP that reaches no car
    ros_io.write_heartbeat(beat, extra={"domain": 0, "subscribers": 1})
    assert tool.preflight_real_move(latch, str(data), domain=0) == []
    latch.set("operator STOP (key)", "bm_stop")
    assert "latch" in tool.preflight_real_move(latch, str(data), domain=0)[0]
    assert len(tool.preflight_real_move(latch, str(data), domain=42)) == 1     # another domain: only the latch counts
    latch.clear("xiaohui")
    assert tool.preflight_real_move(latch, str(tmp_path / "empty"), domain=42) == []


def test_tool_simulated_move_and_latch_commands(tmp_path, capsys):
    tool = load_tool()
    latch_path = str(tmp_path / "LATCH")
    assert tool.main(["--latch", latch_path, "move", "FORWARD_25", "--sim", "--left-gain", "0.7"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["sim"] is True and out["result"]["result"] == "done" and validate("move_result", out["result"]) == []
    Latch(latch_path).set("operator STOP (key)", "bm_stop")
    assert tool.main(["--latch", latch_path, "move", "FORWARD_25", "--sim"]) == 1
    assert json.loads(capsys.readouterr().out)["result"]["reason"] == "latched"
    assert tool.main(["--latch", latch_path, "clear-latch", "--operator", " "]) == 2
    assert Latch(latch_path).is_set()
    assert tool.main(["--latch", latch_path, "clear-latch", "--operator", "xiaohui"]) == 0
    assert "cleared by xiaohui" in capsys.readouterr().out and not Latch(latch_path).is_set()


# ---------------------------------------------------------------- the move log

def test_move_log_goes_into_the_active_session(tmp_path):
    root = tmp_path / "data"
    assert active_session_dir(str(root)) is None
    assert moves_dir(str(root)) == (str(root / "moves"), None)
    (root / "real" / "20261118-120000-floor").mkdir(parents=True)
    (root / "real" / ".active").write_text("20261118-120000-floor\n")
    assert moves_dir(str(root)) == (str(root / "real" / "20261118-120000-floor" / "moves"), "20261118-120000-floor")
    (root / "real" / ".active").write_text("../../etc\n")
    assert active_session_dir(str(root)) is None               # a name, never a path


def test_every_command_and_sample_of_a_move_is_logged(tmp_path):
    root = tmp_path / "data"
    (root / "real" / "sess").mkdir(parents=True)
    (root / "real" / ".active").write_text("sess\n")
    log = MoveLog(root=str(root))
    link = SimLink(CFG, SimCar(SimCarParams(left_gain=0.7)), log=log.write)
    cmd = make_move("FORWARD_25", 4, "t")
    path = log.begin(cmd, CFG)
    result = link.execute(cmd)
    log.finish()
    assert path.startswith(str(root / "real" / "sess" / "moves")) and log.error is None
    rows = [json.loads(line) for line in open(path)]
    kinds = [r["ev"] for r in rows]
    assert kinds[0] == "header" and kinds[1] == "start" and kinds[-1] == "result"
    assert rows[0]["cmd"] == cmd and rows[0]["session"] == "sess" and rows[0]["config"]["hold_gain_per_s"] == 8.0
    assert rows[-1]["result"] == result
    logged = [(r["v"], r["w"]) for r in rows if r["ev"] == "cmd"]
    sent = [(round(v, 4), round(w, 4)) for _t, v, w in link.published if (v, w) != (0.0, 0.0)]
    assert logged == sent and len(sent) > 20                   # every motion command, in order
    samples = [r for r in rows if r["ev"] == "tel"]
    assert len(samples) >= result["duration_s"] / 0.02 - 3     # one per 20 ms telemetry sample
    assert {"l", "r", "yaw", "flags", "seq", "up_ms"} <= set(samples[0])


# ================================================================ added after the independent review (2026-11-18)

def test_latch_check_fails_closed(tmp_path, monkeypatch):
    """Review finding 7: when the file system cannot say whether the latch exists, it counts as set."""
    latch = Latch(tmp_path / "LATCH")
    assert not latch.is_set()
    real_lstat = os.lstat

    def broken(path, *args, **kwargs):
        if str(path) == latch.path:
            raise PermissionError(13, "Permission denied")
        return real_lstat(path, *args, **kwargs)
    monkeypatch.setattr(os, "lstat", broken)
    assert latch.is_set() and "unreadable" in latch.read()["reason"]
    link = SimLink(CFG, SimCar(SimCarParams()), latch=latch)
    result = link.execute(make_move("FORWARD_10", 1, "t"))
    assert (result["result"], result["reason"]) == ("refused", "latched") and link.published == []


@pytest.mark.skipif(os.geteuid() == 0, reason="root can search any directory")
def test_latch_in_an_unsearchable_directory_counts_as_set(tmp_path):
    folder = tmp_path / "data"
    folder.mkdir()
    latch = Latch(folder / "LATCH")
    assert not latch.is_set()
    folder.chmod(0o000)
    try:
        assert latch.is_set()
    finally:
        folder.chmod(0o700)


def rogue_and_zeros(sim, seconds, zero_period_ms):
    for i in range(int(seconds * 1000)):
        if i % 50 == 3:
            sim.send(0.15, 0.0)                                # a 20 Hz publisher that ignores the latch
        if i % zero_period_ms == 0:
            sim.send(0.0, 0.0)
        sim.step(0.001)


def test_the_car_stays_stopped_for_as_long_as_the_latch_exists():
    """Review finding 2: after the 3 s flood the STOP program keeps a zero every LATCHED_ZERO_PERIOD_S. One zero
    per 100 ms (the first version) let a publisher that ignores the latch drive the car on."""
    period_ms = int(round(ros_io.LATCHED_ZERO_PERIOD_S * 1000))
    assert period_ms <= 20
    sim = SimCar(SimCarParams())
    rogue_and_zeros(sim, 3.0, 10)                              # the flood
    x = sim.truth()["x_m"]
    rogue_and_zeros(sim, 10.0, period_ms)                      # the ten seconds after it
    assert sim.truth()["x_m"] - x < 0.002 and not sim.moving
    weak = SimCar(SimCarParams())
    rogue_and_zeros(weak, 5.0, 100)
    assert weak.truth()["x_m"] > 0.05                          # why 10 Hz was not enough


def test_heartbeat_names_its_domain_and_its_subscribers(tmp_path):
    path = str(tmp_path / "STOP_ALIVE")
    ros_io.write_heartbeat(path, now_unix=1000.0, extra={"domain": 0, "subscribers": 1})
    assert ros_io.stop_program_alive(path, now_unix=1001.0, domain=0)
    assert not ros_io.stop_program_alive(path, now_unix=1001.0, domain=42)
    ros_io.write_heartbeat(path, now_unix=1000.0, extra={"domain": 0, "subscribers": 0})
    assert not ros_io.stop_program_alive(path, now_unix=1001.0, domain=0)


def test_tool_refuses_backward_without_the_forward_distance(tmp_path, capsys):
    """Review finding 14: BACKWARD_10 is only for directly after a forward move."""
    tool = load_tool()
    code = tool.main(["--latch", str(tmp_path / "LATCH"), "move", "BACKWARD_10", "--i-am-at-the-car"])
    assert code == 2 and "--prev-forward" in capsys.readouterr().err


def test_wrapper_lets_signals_reach_python():
    """Review finding 13: `docker stop` signals PID 1; the wrapper must exec python, not leave bash in front."""
    text = (TOOLS / "car.sh").read_text()
    assert "&& exec python3 /workspace/course-project/tools/car_move.py" in text

