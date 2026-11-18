"""rclpy smoke test of the car node against the SIMULATED car node, on ROS_DOMAIN_ID 42.

The real car's micro-ROS agent is on ROS_DOMAIN_ID 0. This file never creates a ROS node unless the environment
says domain 42, and the simulated-car node itself refuses domain 0, so nothing here can reach the real car. It is
skipped where rclpy is missing (the Mac). Run it in the project container on the Spark:

    docker run --rm --network none -e ROS_DOMAIN_ID=42 -e ROS_LOCALHOST_ONLY=1 -e HOME=/tmp/bmhome \
      -e PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 -e PYTHONDONTWRITEBYTECODE=1 \
      -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp -e FASTRTPS_DEFAULT_PROFILES_FILE=/workspace/course-project/docker/fastdds_udp.xml \
      -v ~/Projects/en665715-beaconmind:/workspace:ro beaconmind-ros:humble bash -lc \
      'mkdir -p /tmp/bmhome && source /opt/ros/humble/setup.bash && cd /workspace/course-project/beaconmind && \
       PYTHONPATH=src:$PYTHONPATH python3 -m pytest -q -p no:cacheprovider tests/test_car_ros_smoke.py'

(PYTHONPATH must keep ROS's entries; PYTEST_DISABLE_PLUGIN_AUTOLOAD because ROS's launch_testing plugin does not load
under the container's pytest 9.)

(`--network none`: the container has no network at all, a second wall between this test and the car.)

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this smoke test.
"""
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

pytest.importorskip("rclpy")

from beaconmind.car import config as C                 # noqa: E402
from beaconmind.car import ros_io                      # noqa: E402
from beaconmind.car.executor import Command            # noqa: E402
from beaconmind.car.latch import Latch                 # noqa: E402
from beaconmind.car.moves import make_move             # noqa: E402
from beaconmind.schemas import validate                # noqa: E402

TEST_DOMAIN = 42
TOOL = Path(__file__).resolve().parents[2] / "tools" / "car_move.py"


def _require_test_domain():
    assert TEST_DOMAIN != ros_io.REAL_CAR_DOMAIN
    assert os.environ.get("ROS_DOMAIN_ID") == str(TEST_DOMAIN), (
        "this test only runs with ROS_DOMAIN_ID=%d; domain 0 is the real car" % TEST_DOMAIN)
    assert ros_io.ros_domain_id() != 0


@pytest.fixture(scope="module")
def sim_car(tmp_path_factory):
    _require_test_domain()
    ready = tmp_path_factory.mktemp("sim") / "ready"
    proc = subprocess.Popen([sys.executable, str(TOOL), "sim-car", "--seconds", "180", "--ready-file", str(ready)],
                            env=dict(os.environ), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    end = time.monotonic() + 20
    while not ready.exists() and time.monotonic() < end and proc.poll() is None:
        time.sleep(0.1)
    if not ready.exists():
        proc.kill()
        pytest.fail("the simulated car node did not start: %s" % proc.communicate()[0].decode(errors="replace"))
    yield proc
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture(scope="module")
def link(sim_car, tmp_path_factory):
    _require_test_domain()
    root = tmp_path_factory.mktemp("data")
    link = ros_io.RosCarLink(latch=Latch(root / "LATCH"), log_root=str(root), wait_telemetry_s=15.0)
    yield link
    link.close()


def test_domain_is_42_not_the_real_cars_0():
    _require_test_domain()


def test_telemetry_arrives_and_nothing_is_published_while_idle(link):
    time.sleep(1.5)
    state = link.car_state()
    assert state["ros_domain_id"] == TEST_DOMAIN
    assert state["telemetry_age_s"] is not None and state["telemetry_age_s"] < 0.2
    assert state["armed"] is True and state["imu_ready"] is True and state["layout_error"] is None
    assert state["drive_map"] == list(C.DRIVE_MAP_EXPECTED)
    assert state["drive_status"] == 0 and state["imu_topic_age_s"] < 0.2      # /pico/drive/status and /pico/imu/data
    assert state["cmd_vel_subscribers"] == 1                                 # QoS matches the car's subscription
    assert link.published == 0


def test_forward_25(link):
    before = link.car_state()
    result = link.execute(make_move("FORWARD_25", 1, "smoke"))
    assert validate("move_result", result) == []
    assert result["result"] == "done", result
    assert result["achieved_forward_m"] == pytest.approx(0.25, abs=0.02)
    ticks = link.car_state()["left_ticks"] - before["left_ticks"]
    assert ticks == pytest.approx(0.25 * link.cfg.ticks_per_m_left, rel=0.1) and result["enc_left_ticks"] == ticks
    rows = [json.loads(line) for line in open(link.last_log_path)]
    kinds = [r["ev"] for r in rows]
    assert kinds[0] == "header" and kinds[-1] == "result" and kinds.count("tel") > 40 and kinds.count("cmd") > 15
    assert rows[0]["ros_domain_id"] == TEST_DOMAIN
    sent = link.published
    time.sleep(1.0)
    assert link.published == sent                                            # idle again: nothing published


def test_turn_left_30_is_positive_yaw(link):
    result = link.execute(make_move("TURN_LEFT_30", 2, "smoke"))
    assert result["result"] == "done", result
    assert result["gyro_dyaw_deg"] == pytest.approx(30.0, abs=5.0)
    assert result["enc_right_ticks"] > 0 > result["enc_left_ticks"]


def test_the_simulated_car_stops_by_itself_after_one_command(link):
    """One motion command and then silence, as if the host had died: the car's 0.5 s timeout stops it."""
    time.sleep(0.5)
    with link._lock:
        link._publish(Command(0.10, 0.0, False))
    time.sleep(0.35)
    moving = link.car_state()["left_ticks"]
    time.sleep(1.2)
    a = link.car_state()["left_ticks"]
    time.sleep(0.5)
    b = link.car_state()["left_ticks"]
    assert a > moving and a == b                                             # it moved, then stopped with no stop sent
    assert link.executor.tel.drive_status == 2                               # the firmware's "timeout stop"


def test_stop_during_a_move_and_latch_refusal(link):
    time.sleep(0.5)
    timer = threading.Timer(0.7, lambda: link.latch.set("operator STOP (key)", "bm_stop"))
    timer.start()
    result = link.execute(make_move("FORWARD_25", 3, "smoke"))
    timer.join()
    assert (result["result"], result["reason"]) == ("link_lost", "estop"), result
    assert 0.0 < result["achieved_forward_m"] < 0.20
    time.sleep(0.5)
    sent = link.published
    refused = link.execute(make_move("FORWARD_10", 4, "smoke"))
    assert (refused["result"], refused["reason"]) == ("refused", "latched")
    assert link.arm() is False                                               # no operator command passes a latch
    time.sleep(0.5)
    assert link.published == sent                                            # latched: nothing at all is published
    link.latch.clear("smoke-test")
    assert link.execute(make_move("FORWARD_10", 5, "smoke"))["result"] == "done"


def test_read_only_link_has_no_publisher(sim_car, tmp_path):
    _require_test_domain()
    listener = ros_io.RosCarLink(latch=Latch(tmp_path / "LATCH"), node_name="bm_car_state", wait_telemetry_s=10.0,
                                 read_only=True)
    try:
        state = listener.car_state()
        assert state["armed"] is True and state["cmd_vel_subscribers"] is None
        refused = listener.execute(make_move("FORWARD_10", 9, "smoke"))
        assert (refused["result"], refused["reason"]) == ("refused", "read_only")
        assert listener.arm() is False and listener.published == 0
        assert listener._pub is None and listener._lock_handle is None        # no publisher, no car-link lock
        names = [n for n, _ns in listener.node.get_node_names_and_namespaces()]
        pubs = listener.node.get_publishers_info_by_topic(ros_io.CMD_TOPIC)
        assert "bm_car_state" not in [p.node_name for p in pubs], (names, pubs)
    finally:
        listener.close()


def test_only_one_program_may_hold_the_car_link(link):
    """Review finding 14: a second commanding link (another car_move.py, or the tool beside a harness) is refused."""
    with pytest.raises(RuntimeError, match="another program holds the car link"):
        ros_io.RosCarLink(latch=link.latch, log_root=link.log_root, node_name="bm_second", wait_telemetry_s=0.1)


def test_learned_values_are_saved_for_the_next_process(link):
    """Review finding 5: the governor's factor and the coast times outlive the process."""
    assert link.execute(make_move("FORWARD_10", 20, "smoke"))["result"] == "done"
    saved = json.load(open(os.path.join(link.log_root, "car_executor_state.json")))
    learned = link.executor.export_state()
    assert saved["governor"] == learned["governor"] and saved["coast"] == learned["coast"]


def test_a_dead_spin_thread_refuses_a_move(link):
    """Review finding 9."""
    time.sleep(0.5)
    sent = link.published
    link.spin_error = "injected for the test"
    try:
        refused = link.execute(make_move("FORWARD_10", 21, "smoke"))
    finally:
        link.spin_error = None
    assert (refused["result"], refused["reason"]) == ("refused", "spin_thread_died") and link.published == sent


def test_an_interrupt_during_a_move_stops_the_car(link):
    """Review finding 10 and the untested interrupt branch: Ctrl+C while execute() waits."""
    time.sleep(0.5)
    real_wait, calls = link._event.wait, []

    def wait(timeout=None):
        calls.append(1)
        if len(calls) == 6:                                    # about 0.5 s into the move
            raise KeyboardInterrupt
        return real_wait(timeout)
    link._event.wait = wait
    try:
        with pytest.raises(KeyboardInterrupt):
            link.execute(make_move("FORWARD_25", 22, "smoke"))
    finally:
        link._event.wait = real_wait
    time.sleep(2.5)
    assert not link.executor.busy and link._waiting is False and link._movelog is None
    a = link.car_state()["left_ticks"]
    time.sleep(0.5)
    assert link.car_state()["left_ticks"] == a                 # stopped
    assert link.latch.is_set() and "interrupted" in link.latch.read()["reason"]
    link.latch.clear("smoke-test")
    assert link.execute(make_move("FORWARD_10", 23, "smoke"))["result"] == "done"      # and usable again


def test_one_shot_stop_writes_the_latch(sim_car, tmp_path):
    _require_test_domain()
    latch = tmp_path / "LATCH"
    done = subprocess.run([sys.executable, str(TOOL), "--latch", str(latch), "stop"], env=dict(os.environ),
                          capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stdout + done.stderr
    assert json.loads(latch.read_text())["reason"].startswith("operator STOP")


def test_stop_key_program_in_a_terminal(sim_car, link, tmp_path):
    """The interactive STOP program under a pseudo-terminal: status line, heartbeat, SPACE = zeros + latch, q q = quit.
    While a move of the module's link is running, SPACE must end it."""
    import pty
    import select
    _require_test_domain()
    latch_path = link.latch.path                              # the STOP program and the executor share one latch file
    heartbeat = ros_io.stop_heartbeat_path(os.path.dirname(latch_path))
    pid, fd = pty.fork()
    if pid == 0:                                               # the child: becomes the STOP program
        os.execve(sys.executable, [sys.executable, str(TOOL), "--latch", latch_path, "stop-key"], dict(os.environ))
    seen = b""

    def read_until(word, timeout):
        nonlocal seen
        end = time.monotonic() + timeout
        while word not in seen and time.monotonic() < end:
            if select.select([fd], [], [], 0.2)[0]:
                try:
                    seen += os.read(fd, 4096)
                except OSError:
                    break
        return word in seen

    try:
        assert read_until(b"armed", 20), seen.decode(errors="replace")        # the status line shows the car
        assert ros_io.stop_program_alive(heartbeat, domain=TEST_DOMAIN)       # right domain, a subscriber in reach
        assert not ros_io.stop_program_alive(heartbeat, domain=0)
        result = {}
        mover = threading.Thread(target=lambda: result.update(link.execute(make_move("FORWARD_25", 11, "smoke"))))
        mover.start()
        time.sleep(0.8)
        os.write(fd, b" ")                                     # SPACE
        mover.join(timeout=15)
        assert (result.get("result"), result.get("reason")) == ("link_lost", "estop"), result
        assert read_until(b"sent", 10), seen.decode(errors="replace")         # the banner
        assert json.loads(open(latch_path).read())["by"] == "bm_stop"
        os.write(fd, b"qq")
        _pid, status = os.waitpid(pid, 0)
        assert os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0
        assert not os.path.exists(heartbeat)                   # removed on exit
    finally:
        try:
            os.kill(pid, 9)
        except OSError:
            pass
        os.close(fd)
        link.latch.clear("smoke-test")
