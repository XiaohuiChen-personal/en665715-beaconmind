"""The session recorder's helpers (tools/record_frames.py, record_report.py, session_clock.py; plan task M3.T27).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-18: wrote these tests.
"""
import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "tools"


def load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_redact_keeps_only_the_last_three_bytes():
    rr = load("record_report")
    out = rr.redact("Station aa:bb:cc:dd:ee:ff (on wlP9s9)\n\tsignal: -63 dBm 12:30:45\n")
    assert out == "Station ..:dd:ee:ff (on wlP9s9)\n\tsignal: -63 dBm 12:30:45\n"  # a time stamp is not a MAC


def test_ping_log_gives_loss_and_the_longest_gap(tmp_path):
    rr = load("record_report")
    lines = ["PING 10.42.0.138 (10.42.0.138) 56(84) bytes of data."]
    t = 1000.0
    for seq in range(1, 6):
        lines.append("[%.6f] 64 bytes from 10.42.0.138: icmp_seq=%d ttl=64 time=%.1f ms" % (t, seq, 5.0 + seq))
        t += 0.2
    lines.append("[%.6f] no answer yet for icmp_seq=6" % t)
    t += 1.0                                                     # one lost reply, then a 1.2 s gap
    lines.append("[%.6f] 64 bytes from 10.42.0.138: icmp_seq=7 ttl=64 time=40.0 ms" % t)
    lines += ["", "--- 10.42.0.138 ping statistics ---", "7 packets transmitted, 6 received, 14.2857% packet loss, time 1400ms"]
    (tmp_path / "ping.txt").write_text("\n".join(lines) + "\n")
    p = rr.parse_ping(str(tmp_path / "ping.txt"))
    assert (p["sent"], p["received"], p["loss_pct"]) == (7, 6, 14.29)
    assert p["longest_gap_s"] == 1.2 and p["gaps_over_0_5_s"] == 1
    assert p["rtt_ms_max"] == 40.0 and p["rtt_ms_p50"] == 8.0


def test_bag_info_topics(tmp_path):
    rr = load("record_report")
    (tmp_path / "info.txt").write_text(
        "Files:             bag_0.db3\nBag size:          1.2 MiB\nStorage id:        sqlite3\nDuration:          60.120s\n"
        "Messages:          3300\nTopic information: Topic: /pico/imu/data | Type: sensor_msgs/msg/Imu | Count: 3000 | "
        "Serialization Format: cdr\n                   Topic: /pico/wheel_ticks | Type: std_msgs/msg/Int32MultiArray | "
        "Count: 300 | Serialization Format: cdr\n")
    info = rr.parse_bag_info(str(tmp_path / "info.txt"))
    assert info["Duration"] == "60.120s" and info["Messages"] == "3300" and info["Storage id"] == "sqlite3"
    assert info["topics"] == [("/pico/imu/data", "sensor_msgs/msg/Imu", 3000),
                              ("/pico/wheel_ticks", "std_msgs/msg/Int32MultiArray", 300)]


def fake_camera(fail_on=()):
    calls = {"n": 0}

    def grabber(url, timeout):
        if url.endswith("/status"):
            return 200, {}, b'{"fw": "bm_cam-0.2", "framesize": "VGA", "quality": 12}'
        calls["n"] += 1
        if calls["n"] in fail_on:
            raise OSError("timed out")
        return 200, {"X-BM-Seq": str(100 + calls["n"]), "X-BM-Width": "640", "X-BM-Height": "480",
                     "Content-Type": "image/jpeg"}, b"\xff\xd8jpeg%d\xff\xd9" % calls["n"]
    return grabber


def test_frames_are_kept_indexed_and_latest_points_at_the_newest(tmp_path):
    rf = load("record_frames")
    t = {"ns": 10**18}

    def clock():
        t["ns"] += 50_000_000  # every call advances 50 ms
        return t["ns"]
    saved, errors = rf.run("http://cam", str(tmp_path), fps=0, status_every=10, timeout=1, max_seconds=0.5,
                           grabber=fake_camera(fail_on={2}), clock=clock, sleep=lambda s: None)
    index = [json.loads(l) for l in (tmp_path / "index.jsonl").read_text().splitlines()]
    assert errors == 1 and saved == len(index) - 1 and saved >= 2
    good = [r for r in index if "file" in r]
    assert good[0]["headers"] == {"x-bm-seq": 101, "x-bm-width": 640, "x-bm-height": 480}
    assert (tmp_path / good[-1]["file"]).read_bytes().startswith(b"\xff\xd8")
    assert os.readlink(tmp_path / "latest.jpg") == good[-1]["file"]
    assert "error" in index[1] and index[1]["n"] == 2
    status = json.loads((tmp_path / "status.jsonl").read_text().splitlines()[0])
    assert status["status"]["fw"] == "bm_cam-0.2"


def test_readme_names_firmware_battery_topics_and_keeps_operator_files(tmp_path):
    rr = load("record_report")
    rf = load("record_frames")
    s = tmp_path / "20261118-0010-dry-run"
    for d in ("frames", "logs", "terminal", "meta"):
        (s / d).mkdir(parents=True)
    (s / "meta" / "session.json").write_text(json.dumps({"id": s.name, "label": "dry-run", "pico_build": "buildK2a_d485d7ab",
                                                         "camera_ip": "10.42.0.89", "car_ip": "10.42.0.138", "ntp_synced": "yes"}))
    (s / "meta" / "camera_status_start.json").write_text('{"fw": "bm_cam-0.2", "framesize": "VGA"}')
    (s / "meta" / "stop.json").write_text('{"end_local": "2026-11-18 00:11:00 CST", "reason": "operator"}')
    (s / "meta" / "bag_info.txt").write_text("Duration:          60.0s\nMessages:          10\nStorage id:        sqlite3\n"
                                             "Topic information: Topic: /pico/imu/data | Type: sensor_msgs/msg/Imu | Count: 10 | "
                                             "Serialization Format: cdr\n")
    (s / "logs" / "micro_ros_agent.log").write_text("2026-11-18T06:10:01Z [x] | create_client | session established\n")
    (s / "logs" / "micro_ros_agent_before.log").write_text(
        "".join("2026-11-18T06:0%d:00Z \x1b[32msession established\x1b[m | client_key: 0x%d\n" % (i, i) for i in range(1, 4))
        + "2026-11-18T06:04:00Z topic created\n")
    (s / "terminal" / "01-probe.log").write_text("# cmd: python3 tools/camera_probe.py --n 100 \n# start: a\n# end: b\n# exit: 0\n")
    t = {"ns": 10**18}

    def clock():
        t["ns"] += 100_000_000
        return t["ns"]
    rf.run("http://cam", str(s / "frames"), fps=0, status_every=10, timeout=1, max_seconds=0.5,
           grabber=fake_camera(), clock=clock, sleep=lambda x: None)
    readme = Path(rr.write_readme(str(s))).read_text()
    for needed in ("buildK2a_d485d7ab", "Motor battery", "`/pico/imu/data`", "1 session(s) established",
                   "tools/camera_probe.py", "frames/index.jsonl", "meta/session.json",
                   "3 session(s) established, the last: `2026-11-18T06:03:00Z session established | client_key: 0x3`"):
        assert needed in readme, needed
    assert "\x1b" not in readme
    (s / "tape.md").write_text("filled in by the operator")
    rr.write_readme(str(s))
    assert (s / "tape.md").read_text() == "filled in by the operator"
    assert (s / "notes.md").exists()


def test_clock_digits_line_up():
    sc = load("session_clock")
    lines = sc.render("12:34:56.7")
    assert len(lines) == 7 and len({len(l) for l in lines}) == 1
    assert "BeaconMind session abc" in sc.frame(1794981694.25, "abc")


@pytest.mark.skipif(shutil.which("bash") is None, reason="no bash")
@pytest.mark.parametrize("script", ["record_session.sh", "car_net.sh"])
def test_shell_scripts_parse(script):
    assert subprocess.run(["bash", "-n", str(TOOLS / script)]).returncode == 0
