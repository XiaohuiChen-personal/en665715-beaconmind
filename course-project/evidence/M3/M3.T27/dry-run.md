# M3.T27 — session recorder: parked dry run (2026-11-18)

The recorder for rule R2 (plan/README.md §3.6, widened by Xiaohui on 2026-11-13 to bench sessions and to every frame,
topic and service log): `tools/record_session.sh` (`start`, `run`, `status`, `stop`) with `tools/record_frames.py`
(camera frames), `tools/record_report.py` (README and operator templates) and `tools/session_clock.py` (the clock the
phone films). `tools/car_net.sh` gained `agent-start` / `agent-stop` for the micro-ROS agent (the container of
2026-11-10 was started with `--rm`, so stopping it on 2026-11-13 removed it). Tests: `beaconmind/tests/test_record_session.py`.

Session data stays on the Spark under `course-project/data/real/` (git-ignored). This folder keeps the dry run's README
(`dry-run-README.md`) and the file listing of the three sessions (`listing.txt`).

## Safety

Car parked, Pico on its power bank, motor battery **off** (Xiaohui confirmed: "The motor battery is off, go ahead").
The recorder only subscribes and reads; nothing published to `/pico/cmd_vel`. The agent was started only after that
confirmation (plan §3.6 hardware procedure 2).

## Runs (Spark host, `cd ~/Projects/en665715-beaconmind`)

| Session | What | Result |
| --- | --- | --- |
| `20261118-000642-recorder-smoke` | 30 s, agent **off** (car on Wi-Fi, not on ROS) | every capture started and stopped; bag closed with `metadata.yaml`; 163 frames (4.8/s); pings 0 % loss; no full MAC in any log; no process, container or tmux session left |
| `20261118-000959-recorder-dry-run` | **the acceptance run**: 60 s, car on ROS (`bash course-project/tools/car_net.sh agent-start`; `/pico_fusion` joined in about 10 s) | see below |
| `20261118-001236-recorder-check` | 20 s with the final code (the agent's log at start added) | 1125 IMU messages in 22.7 s; 120 frames; the agent's state at start recorded |

Commands of the acceptance run:

```
bash course-project/tools/record_session.sh start recorder-dry-run --operator "Xiaohui Chen" --note "M3.T27 parked dry run: ..."
bash course-project/tools/record_session.sh run car-net-status -- bash course-project/tools/car_net.sh status
bash course-project/tools/record_session.sh run ros-topics -- docker run ... beaconmind-ros:humble ... "ros2 node list && ros2 topic list -t"
bash course-project/tools/record_session.sh status        # at about 60 s: every window running, bag 2.3 MB, 294 frames
bash course-project/tools/record_session.sh stop
```

Acceptance run, from its README (`dry-run-README.md`):

- **Bag:** 59.35 s, 5945 messages: `/pico/imu/data` 2938 (49.5 Hz), `/pico/wheel_ticks` 2938, `/pico/drive/status` 58,
  plus `/rosout` and `/parameter_events`.
- **Frames:** 300 saved, 0 failed, 4.93 frames/s at 640 × 480 (bm_cam-0.2, VGA quality 12), latency p50 133 ms, p95 199 ms.
- **Link:** car 303/303 pings, p50 5.6 ms, p99 57 ms, longest gap 0.28 s; camera 303/303, longest gap 0.30 s.
- **Terminal:** `terminal/01-car-net-status.log` (974 B), `terminal/02-ros-topics.log` (1030 B), both exit 0.
- **Operator files:** `tape.md` and `notes.md` made; the README's motor-battery line is left for the multimeter reading.

## Acceptance criteria (plan M3.T27)

- [x] One command starts and one stops every capture of rule R2 (bag, frames, pings, Wi-Fi, agent and relay logs,
      terminal through `run`, watchdog).
- [x] The parked dry run's folder holds the bag, frames, terminal capture, README and tape sheet, all non-empty
      (`listing.txt`). Two logs are empty by nature: the camera relay carried no traffic (nothing used it), and the
      agent logged nothing new after the car had joined; the agent's state at the start is now kept in
      `logs/micro_ros_agent_before.log` (check session).
- [x] The README records the firmware build id (`buildK2a_d485d7ab`, documented: K2 does not publish one, and only that
      build joins the access point; camera `bm_cam-0.2` read from `/status`) and the battery-voltage field.

## Findings

- `/pico/imu/std` and `/pico/cmd_vel` are the car's **inputs** (it subscribes; `ros2 topic info -v`: publisher count 0),
  so a parked bag does not hold them; `ros2 bag record -a` picks them up as soon as something publishes. The README says so.
- At VGA the camera answers in about 130–175 ms, so the frame saver reaches its 5 frames/s target. Work list 2.2
  (capture size) measures UXGA too.
- Only one program may be the camera's client: during the capture-size probe, calibration and episodes the probe or
  the backend captures, and the recorder runs with `--camera off` or the consumer reads `frames/latest.jpg`.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-18: wrote the recorder, its tests, ran the three sessions and
wrote this record. Xiaohui Chen confirmed the motor battery was off and is the operator of the acceptance run.
