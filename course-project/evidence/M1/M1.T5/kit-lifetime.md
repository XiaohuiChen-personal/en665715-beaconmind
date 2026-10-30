# Kit lifetime — M1.T5 step 9

Spark host `spark-2a60`, 2026-10-07 CT. Script: `course-project/sim/isaac/kit_lifetime.py --seconds 900`. Each run was `timeout --kill-after=60 1000 ./python.sh` from the Isaac 5.1 release directory. Jazzy was not sourced. Logs stay on the Spark under `course-project/data/renders/`.

The hold is 900 s after `READY`. `ALIVE` is seconds since process start, printed every 10 s. Ninety `ALIVE` lines, first at READY+10 s and last at READY+900 s, means the update loop ran for the full hold.

## Run 1 — base kit

tmux `bm-m1t5-life` (session has finished). Log `lifetime-base.log`, mtime 2026-10-07 00:30:49 -0500. No ROS bridge.

| Item | Value |
| --- | --- |
| Launch to `READY` | 6.7 s |
| First `ALIVE` | 16.7 s |
| Last `ALIVE` | 906.7 s |
| Time in the update loop after `READY` | 900.0 s |
| `ALIVE` lines | 90 |
| End marker | `DONE` |
| Exit code | 0 |

## Run 2 — ROS 2 bridge

Started 2026-10-07T00:31:59-05:00, after run 1 had exited and no kit process was left. tmux `bm-m1t5-ros` (session has finished). Log `lifetime-ros.log`, mtime 2026-10-07 00:47:08 -0500. Wrapper: `data/renders/run-lifetime-ros.sh`.

Environment, set in that wrapper only:

- `ROS_DISTRO=humble`
- `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`
- `ROS_DOMAIN_ID=0`
- `LD_LIBRARY_PATH` includes `IsaacSim/_build/linux-aarch64/release/exts/isaacsim.ros2.bridge/humble/lib`
- `FASTRTPS_DEFAULT_PROFILES_FILE` is `discussions/module2/sim/fastdds_udp.xml`

The log shows `isaacsim.ros2.bridge-4.12.4` startup, then internal `rclpy` for Humble (`rclpy loaded`). System `rclpy` is not on the kit Python path.

| Item | Value |
| --- | --- |
| Launch to `READY` | 7.1 s |
| First `ALIVE` | 17.1 s |
| Last `ALIVE` | 907.1 s |
| Time in the update loop after `READY` | 900.0 s |
| `ALIVE` lines | 90 |
| End marker | `DONE` |
| Exit code | 0 |

## kern.log

`/var/log/kern.log` is readable. The last lines matching `killed process`, `out of memory`, or `oom` are NVIDIA `NV_ERR_NO_MEMORY` at 2026-10-06T20:46:50-05:00 and a repeat summary at 2026-10-06T20:53:27-05:00. Both are earlier than these runs. Neither lifetime run added a matching line.

## Outcome

Self-kill not reproduced in 900 s. Both runs printed `DONE` and exited 0. Launch-to-READY was 6.7 s (base) and 7.1 s (ROS bridge). M2.T5 still restarts the kit per episode batch and checkpoints after each episode.

## Generative-AI disclosure

AI-assisted: Grok 4.7 via Cursor, 2026-10-07: polled the base run, started the ROS-bridge run after it finished, and wrote this note from the Spark logs.
