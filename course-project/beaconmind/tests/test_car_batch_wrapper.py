"""tools/car_batch.sh, the Spark wrapper of the batch runner, run by bash against stand-ins for docker, tmux and the
recorder (plan/README.md section 3.6 "Unattended batches"). What it must do: start the recorder for a real run and stop
it whatever happens (also when the recorder's start reports an error after it began a session), refuse a real run
whose recorder found no car, camera or agent or that would share the camera with a polling session, keep the batch's
exit status after Ctrl+C, and give the container one name per batch.

The real execution on the Spark (2026-11-24, simulated car) is recorded in evidence/M3/M3.T12/batch-runner/README.md;
these tests pin its findings down without docker. Nothing here can reach a car.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote these tests.
"""
import os
import shutil
import signal
import subprocess
import time

import pytest

import beaconmind

ROOT = beaconmind.course_root()
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="needs bash")

FAKE_RECORDER = r"""#!/usr/bin/env bash
# stand-in for tools/record_session.sh: logs its calls; start makes a session as the real one does
CP="$(cd "$(dirname "$0")/.." && pwd)"
echo "record_session $*" >> "$FAKE_LOG"
case "$1" in
  start)
    id="20261124-000000-$2"
    mkdir -p "$CP/data/real/$id/meta"
    printf '%b' "${FAKE_CHECKS:-access point: wlP9s9 holds 10.42.0.1\nmicro-ROS agent: bm-micro-ros-agent running\ncamera relay: tmux bm-cam-relay up\ncamera: 10.42.0.89\ncar: 10.42.0.138 answers\n}" > "$CP/data/real/$id/meta/checks.txt"
    echo '{"camera_mode": "off"}' > "$CP/data/real/$id/meta/session.json"
    echo "$id" > "$CP/data/real/.active"
    exit "${FAKE_START_RC:-0}" ;;
  stop) rm -f "$CP/data/real/.active" ;;
esac
"""

FAKE_DOCKER = r"""#!/usr/bin/env bash
# stand-in for docker: logs its arguments, then behaves as the batch would
echo "docker $*" >> "$FAKE_LOG"
trap 'echo "docker got INT" >> "$FAKE_LOG"; exit "${FAKE_DOCKER_RC_ON_SIGNAL:-3}"' INT
if [ -n "${FAKE_DOCKER_SLEEP:-}" ]; then sleep "$FAKE_DOCKER_SLEEP" & wait $!; fi
exit "${FAKE_DOCKER_RC:-0}"
"""

FAKE_TMUX = r"""#!/usr/bin/env bash
# stand-in for tmux: only `has-session -t bm-rec` is asked
[ "$1 $2 $3" = "has-session -t bm-rec" ] && [ -n "${FAKE_BM_REC:-}" ] && exit 0
exit 1
"""


@pytest.fixture
def rig(tmp_path):
    """A repository layout with the real car_batch.sh and the stand-ins; returns (run, paths)."""
    repo = tmp_path / "repo"
    tools = repo / "course-project" / "tools"
    tools.mkdir(parents=True)
    shutil.copy(ROOT / "tools" / "car_batch.sh", tools / "car_batch.sh")
    (tools / "record_session.sh").write_text(FAKE_RECORDER)
    (repo / "course-project" / "data" / "real").mkdir(parents=True)
    (repo / "course-project" / "configs").mkdir()
    (repo / "course-project" / "configs" / "w.json").write_text("{}")
    binp = tmp_path / "bin"
    binp.mkdir()
    for name, text in (("docker", FAKE_DOCKER), ("tmux", FAKE_TMUX)):
        (binp / name).write_text(text)
        (binp / name).chmod(0o755)
    log = tmp_path / "calls.log"
    log.write_text("")
    env = dict(os.environ, PATH="%s:%s" % (binp, os.environ["PATH"]), FAKE_LOG=str(log), HOME=str(tmp_path))
    env.pop("BM_ROS_DOMAIN_ID", None)

    def run(*args, extra_env=None, timeout=30):
        e = dict(env, **(extra_env or {}))
        p = subprocess.run([BASH, str(tools / "car_batch.sh"), *args], cwd=str(repo), env=e, capture_output=True,
                           text=True, timeout=timeout)
        return p.returncode, p.stdout + p.stderr, log.read_text()

    return run, {"repo": repo, "log": log, "env": env, "tools": tools}


REAL = ["run", "--world", "course-project/configs/w.json", "--initial-pose", "2.4,1.6,70", "--episodes", "1",
        "--policy", "b2"]


def docker_calls(log):
    return [line for line in log.splitlines() if line.startswith("docker run")]


def test_a_dry_run_starts_no_recorder_names_its_container_and_keeps_the_batch_status(rig):
    run, p = rig
    code, out, log = run("dry-1", *REAL, "--dry-run", "--out", "course-project/data/batches/dry-1",
                         extra_env={"FAKE_DOCKER_RC": "3"})
    assert code == 3, out                                       # the batch's own status: halted
    (call,) = docker_calls(log)
    assert "--name bm-batch-dry-1" in call and "--dry-run" in call
    assert "/workspace/course-project/configs/w.json" in call and "/workspace/course-project/data/batches/dry-1" in call
    assert "record_session" not in log


def test_a_recorder_start_that_reports_an_error_is_still_stopped_and_nothing_runs(rig):
    """The Spark, 2026-11-24: with the car off, record_session.sh start began a session but exited 1 (its status
    line under pipefail); the wrapper said "did not start" and left the session recording with nobody to stop it."""
    run, p = rig
    code, out, log = run("b1", *REAL, extra_env={"FAKE_START_RC": "1"})
    assert code == 2 and "the recorder's start failed (exit 1)" in out and "is stopped" in out
    assert "record_session start batch-b1" in log and "record_session stop" in log
    assert not (p["repo"] / "course-project" / "data" / "real" / ".active").exists()
    assert docker_calls(log) == []


@pytest.mark.parametrize("missing", ["car: NOT FOUND on the access point", "camera: NOT FOUND",
                                     "micro-ROS agent: NOT RUNNING (bash course-project/tools/car_net.sh agent-start)"])
def test_a_real_run_without_the_car_camera_or_agent_in_the_recorders_checks_is_refused(rig, missing):
    run, p = rig
    checks = "access point: wlP9s9 holds 10.42.0.1\\ncamera: 10.42.0.89\\ncar: 10.42.0.138 answers\\n" \
             "micro-ROS agent: bm-micro-ros-agent running\\n"
    key = missing.split(":")[0]
    checks = "\\n".join(line for line in checks.split("\\n") if not line.startswith(key)) + missing + "\\n"
    code, out, log = run("b2", *REAL, extra_env={"FAKE_CHECKS": checks})
    assert code == 2 and missing in out and "nothing was sent" in out
    assert "record_session stop" in log and docker_calls(log) == []
    assert not (p["repo"] / "course-project" / "data" / "real" / ".active").exists()


def test_a_real_run_with_the_recorder_up_runs_and_the_recorder_is_stopped_after(rig):
    run, p = rig
    code, out, log = run("b3", *REAL, extra_env={"FAKE_DOCKER_RC": "0"})
    assert code == 0, out
    lines = log.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("record_session start batch-b3"))
    dock = next(i for i, l in enumerate(lines) if l.startswith("docker run"))
    stop = next(i for i, l in enumerate(lines) if l.startswith("record_session stop"))
    assert start < dock < stop                                  # recorder first, batch, recorder stopped last
    assert "--name bm-batch-b3" in lines[dock] and "--label b3" in lines[dock] and "ROS_DOMAIN_ID=0" in lines[dock]


def test_an_active_session_is_used_not_stopped_unless_it_polls_the_camera(rig):
    run, p = rig
    real = p["repo"] / "course-project" / "data" / "real"
    (real / "s1" / "meta").mkdir(parents=True)
    (real / "s1" / "meta" / "checks.txt").write_text("camera: 10.42.0.89\ncar: 10.42.0.138 answers\n")
    (real / "s1" / "meta" / "session.json").write_text('{\n "camera_mode": "poll"\n}')
    (real / ".active").write_text("s1\n")
    code, out, log = run("b4", *REAL, extra_env={"FAKE_BM_REC": "1"})
    assert code == 2 and "polls the camera" in out and docker_calls(log) == [] and "record_session" not in log
    (real / "s1" / "meta" / "session.json").write_text('{\n "camera_mode": "off"\n}')
    code, out, log = run("b4", *REAL, extra_env={"FAKE_BM_REC": "1"})
    assert code == 0 and len(docker_calls(log)) == 1 and "record_session" not in log     # not ours: left running
    assert (real / ".active").exists()
    code, out, log = run("b4", *REAL)                           # marked active, but its tmux session is gone
    assert code == 2 and "is not running" in out and len(docker_calls(log)) == 1


def test_refusals_before_anything_starts(rig):
    run, p = rig
    code, out, log = run("b5", "run", "--world", "/etc/passwd", "--initial-pose", "1,1,0")
    assert code == 2 and "outside the repository" in out
    code, out, log = run("b5", *REAL, "--detector-noise", "/tmp/noise.json")
    assert code == 2 and "outside the repository" in out
    code, out, log = run("-", *REAL)
    assert code == 2 and "needs a label" in out
    assert log == ""


def test_a_simulated_car_domain_starts_no_recorder(rig):
    run, p = rig
    code, out, log = run("b6", *REAL, extra_env={"BM_ROS_DOMAIN_ID": "42"})
    assert code == 0 and "record_session" not in log
    (call,) = docker_calls(log)
    assert "ROS_DOMAIN_ID=42" in call


def test_ctrl_c_keeps_the_batch_status_and_a_kill_of_the_wrapper_alone_does_not_end_the_batch(rig, tmp_path):
    """Ctrl+C reaches the whole process group: docker passes it to the batch, which halts (status 3); the wrapper
    waits for it and returns that status (it returned 130 before). A TERM to the wrapper's process alone does not
    reach the container: the wrapper waits for the batch to end (documented in the wrapper)."""
    run, p = rig
    env = dict(p["env"], FAKE_DOCKER_SLEEP="3", FAKE_DOCKER_RC_ON_SIGNAL="3")
    args = [BASH, str(p["tools"] / "car_batch.sh"), "sig", *REAL, "--dry-run", "--out", "course-project/data/b"]
    proc = subprocess.Popen(args, cwd=str(p["repo"]), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            start_new_session=True)
    deadline = time.time() + 10
    while time.time() < deadline and "docker run" not in p["log"].read_text():
        time.sleep(0.05)
    time.sleep(0.2)
    os.killpg(proc.pid, signal.SIGINT)                          # what Ctrl+C in the tmux window does
    out = proc.communicate(timeout=20)[0].decode()
    assert proc.returncode == 3, out
    assert "docker got INT" in p["log"].read_text() and "the batch was interrupted; its exit status is 3" in out
    p["log"].write_text("")
    env = dict(p["env"], FAKE_DOCKER_SLEEP="1.5", FAKE_DOCKER_RC="0")
    proc = subprocess.Popen(args, cwd=str(p["repo"]), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            start_new_session=True)
    deadline = time.time() + 10
    while time.time() < deadline and "docker run" not in p["log"].read_text():
        time.sleep(0.05)
    t0 = time.time()
    proc.send_signal(signal.SIGTERM)                            # the wrapper's own process only
    proc.communicate(timeout=20)
    assert time.time() - t0 >= 1.0 and proc.returncode == 0     # it waited for the batch, which ended by itself
    assert "docker got INT" not in p["log"].read_text()


def test_the_recorders_status_does_not_fail_without_a_ping_log(tmp_path):
    """The root of the Spark finding: record_session.sh status ended with `tail ping_car.txt | sed` under pipefail,
    so with no car found (no ping log) status, and therefore start, exited 1."""
    tools = tmp_path / "course-project" / "tools"
    tools.mkdir(parents=True)
    shutil.copy(ROOT / "tools" / "record_session.sh", tools / "record_session.sh")
    real = tmp_path / "course-project" / "data" / "real"
    (real / "s1" / "meta" / "run").mkdir(parents=True)
    (real / ".active").write_text("s1\n")
    binp = tmp_path / "bin"
    binp.mkdir()
    (binp / "docker").write_text("#!/usr/bin/env bash\nexit 0\n")
    (binp / "docker").chmod(0o755)
    env = dict(os.environ, PATH="%s:%s" % (binp, os.environ["PATH"]))
    p = subprocess.run([BASH, str(tools / "record_session.sh"), "status"], env=env, capture_output=True, text=True,
                       timeout=30)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "active: s1" in p.stdout and "car ping: none" in p.stdout
