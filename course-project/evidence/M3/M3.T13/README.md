# M3.T13 — out-of-band STOP and the latch (work list 2.7), 2026-11-18

Status: **software written and tested against a simulated car; not yet run with the real car.** Nothing in this
task was published on the real car's ROS graph (domain 0). The steps for Xiaohui are at the end.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote the latch, the STOP program, the tests and this
note. Xiaohui Chen runs the car and makes every physical action.

## What was built

| File | What |
| --- | --- |
| `beaconmind/src/beaconmind/car/latch.py` | the latch file: `Latch(path)`, `is_set()`, `set(reason, by)`, `read()`, `clear(operator)` |
| `beaconmind/src/beaconmind/car/ros_io.py` | `stop_main` (the STOP program), `stop_now` (the STOP action), `key_action`, the heartbeat file |
| `tools/car_move.py` | `stop-key`, `stop`, `clear-latch --operator <name>` |
| `tools/car.sh` | runs the tool in a one-off `beaconmind-ros` container with the recorder's ROS environment |
| `beaconmind/tests/test_car_stop.py` | 27 tests (Mac; 26 in the container, where root skips one) |
| `beaconmind/tests/test_car_ros_smoke.py` | on real rclpy, domain 42: STOP during a move, latch refusal, the one-shot `stop`, and the STOP program itself under a pseudo-terminal |

## How it differs from the task text, and why

The task text (plan `M3-real-car.md`, "M3.T13") was written for a project firmware with an `/estop` topic and a
STBY line the Pico drops. The re-scope of 2026-11-09 (plan README §3.6) keeps the car's own firmware (Assignment 8
Build K2), which has neither. What replaces them:

| Task text | Here | Why |
| --- | --- | --- |
| publish `/estop true` three times | publish **zero velocity commands** on `/pico/cmd_vel`: one at once, then 100 per second for 3 s, then 50 per second for as long as the latch exists (it was 10 per second until the independent review showed a second publisher could then move the car) | Build K2 has no `/estop`. A zero command stops both wheels at once (firmware `drive_control.c`: a zero target applies immediately, a rising duty has to ramp again at 1.0 per 0.3 s), so a zero every 10 ms leaves the wheels without power even if another program keeps commanding. Test `test_zero_flood_stops_a_car_that_another_program_keeps_commanding`. |
| the Pico disarms and latches | the **latch file** stops the host side: the executor refuses to start, ends a running move within one telemetry sample (20 ms), and never sends a motion command while the file exists | the firmware has no disarm command; its own protection is the 0.5 s command timeout |
| `Latch` from `beaconmind.validator` (task M2.T1) | `beaconmind.car.latch.Latch`, same interface | M2.T1's module was never built (re-scope). The closed-loop harness written today has a per-episode latch for simulated episodes (`harness/validator.py`, files `<episode>.LATCH`), which is a different thing and matches C5 item 5's last sentence. `data/LATCH` has exactly one implementation. |
| `bm-clear-latch --operator <name>` console script | `car_move.py clear-latch --operator <name>` | one tool for the car; no console-script install is needed in a one-off container |
| result of a STOP during a move: open decision OD15 | `link_lost`, reason `estop` | OD15's option a, the plan's proposed default. The executor does not overwrite the latch record, so the file names the operator's STOP as the cause. |

The latch file is `course-project/data/LATCH` (plan C5 item 5; git-ignored; the container and the host see the same
file because the repository is mounted at `/workspace`). Every set and clear is appended to `data/LATCH.log`. A file
that cannot be parsed still counts as set. Only `clear(operator)` with a non-empty name removes it.

The STOP program writes a heartbeat (`data/STOP_ALIVE`, twice a second). `car_move.py move` on the real car's
domain refuses to move unless that heartbeat is under 2 s old, names the same ROS domain and reports a subscriber
on `/pico/cmd_vel`, so the car cannot be driven by hand with no STOP program in reach of it. The latch check itself
fails closed: if the file system cannot say whether the file exists, the latch counts as set. For the harness, the
file to watch is `course-project/data/LATCH` (`--watch-latch`). `car_move.py stop` is the same STOP without a keyboard (for a second terminal or a script).

Order inside STOP (`stop_now`): the first zero command is published **before** the latch file is written, so the
motors never wait for a disk write; if the file cannot be written the zeros still flow and the error is shown.

**What STOP is not.** It is a software stop over Wi-Fi. If the link is down it cannot reach the car; then the car's
own 0.5 s command timeout stops it. The hard stop is the motor battery's switch (safety rule S7), with a hand on it
during every run (plan §3.6 hardware procedure 2). One firmware behaviour to know: a zero command also arms a car
that is disarmed without needing the arm marker (firmware `cmd_vel_callback`); with the latch set nothing of this
project sends motion, so this does not move the car.

## Tests

Mac (Python 3.13), 2026-11-18:

```
$ cd course-project/beaconmind && PYTHONPATH=src python3 -m pytest -q tests/test_car_stop.py
...........................                                              [100%]
27 passed
```

Container on the Spark (Python 3.10, rclpy, ROS_DOMAIN_ID 42, `--network none`): `../M3.T6/pytest-container.txt`
(195 passed, 1 skipped). The STOP cases there:

```
tests/test_car_ros_smoke.py::test_stop_during_a_move_and_latch_refusal PASSED
tests/test_car_ros_smoke.py::test_one_shot_stop_writes_the_latch PASSED
tests/test_car_ros_smoke.py::test_stop_key_program_in_a_terminal PASSED
```

`test_stop_key_program_in_a_terminal` starts `car_move.py stop-key` under a pseudo-terminal beside a running move of
the simulated car, waits for the status line and the heartbeat, types SPACE (the move ends `link_lost` / `estop`,
the latch file says `bm_stop`, the banner appears), then `q q` (exit status 0, heartbeat removed). It found a bug:
keys were read one at a time through a buffer, so a SPACE typed right after another key waited for a third key.
The program now reads the terminal's raw bytes and acts on every key (`keys_to_actions`).

What the tests show: the latch's default path is `course-project/data/LATCH`; clearing needs a name; the first cause
is kept; an unreadable file counts as set; a latched executor refuses every move and publishes nothing; a STOP
during a forward move or a turn gives `link_lost` / `estop`, the first zero follows the latch within 25 ms, no motion
command follows it, and the next move is refused until the operator clears the latch; the zero flood stops a car
that a second publisher keeps commanding; the keys (SPACE, s, q) map as stated.

## Procedure for Xiaohui (stand first, then floor)

Everything here is done with the car **on its stand, wheels up**, the recorder running, and the motor battery
switched on last (plan §3.6 hardware procedures 1 to 5). Spark host, `cd ~/Projects/en665715-beaconmind`.

1. Recorder: `bash course-project/tools/record_session.sh start stop-check --operator "Xiaohui Chen"`.
2. Terminal A (its own window): `bash course-project/tools/car.sh stop-key`. The status line must say
   `latch clear | telemetry 0.0 s old, armed, ... | subscribers on /pico/cmd_vel: 1`. If it says `no telemetry`, the
   car is not on ROS (`bash course-project/tools/car_net.sh status`).
3. Terminal B: `bash course-project/tools/car.sh state`. Check `armed: true`, `imu_ready: true`,
   `stop_program_alive: true`, `recorder_session` not null, `latch: null`.
4. Wheels up, motor battery on. Terminal B: `bash course-project/tools/car.sh move FORWARD_25 --i-am-at-the-car`
   and, while the wheels turn, press **SPACE** in terminal A.
   - **Pass:** the wheels stop at once (well under half a second by eye; the phone video and the move's log give the
     time: the `stop` line of `data/real/<session>/moves/move_*.jsonl` against the last non-zero `duty` in its `tel`
     lines; the design value is `estop_max_s` 0.2 s); terminal A shows the STOP banner; terminal B prints
     `"result": "link_lost", "reason": "estop"`; `cat course-project/data/LATCH` shows `"by": "bm_stop"`.
5. With the latch set: `bash course-project/tools/car.sh move FORWARD_10 --i-am-at-the-car`.
   - **Pass:** it prints `refused, nothing was sent` naming the latch, and no wheel moves.
6. `bash course-project/tools/car.sh clear-latch --operator xiaohui`, then repeat the move of step 5.
   - **Pass:** `latch cleared by xiaohui`, and the move runs.
7. Kill test: start `move FORWARD_25` again and close terminal B's window (or press Ctrl+C) while the wheels turn.
   - **Pass:** the wheels stop within about half a second (the car's own timeout), without any STOP.
8. Motor battery off. `bash course-project/tools/record_session.sh stop`. Put the session's name and the pass/fail
   of steps 4 to 7 into `evidence/M3/M3.T13/smoke.md`.

Stop and tell Claude if: a wheel keeps turning after SPACE; the latch file does not appear; a move starts while the
latch is set; the status line shows more than one subscriber or `DISARMED`.

## Open items (need the car)

- Steps 4 to 7 above have not been run. The 0.2 s figure (`estop_max_s`) is unmeasured on the real link.
- The STOP program's keyboard loop ran under a pseudo-terminal in the container, not yet in Xiaohui's own terminal
  over ssh (step 2).
