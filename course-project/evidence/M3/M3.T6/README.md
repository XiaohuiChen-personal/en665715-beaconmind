# M3.T6 — host-side bounded-move executor on the car's own firmware (work list 2.6), 2026-11-18

Status: **software written and tested against a simulated car (Mac and the project container); not run on the real
car.** During this work nothing was published on the real car's ROS graph (domain 0), no container named `bm-*`
was started or stopped, and the motor battery was off (the owner was asleep). What was read from the real car:
one recorded bag of the parked car and the topic list with its QoS (`ros2 topic info`). The stand test and the
floor check at the end are for Xiaohui; until they pass, every control number below is untested on this car.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote the executor, the simulated car, the ROS node, the
tool, the tests and this note. Xiaohui Chen makes every physical action and every measurement.

## 1. What was built

| File (under `course-project/`) | What |
| --- | --- |
| `beaconmind/src/beaconmind/car/config.py` | every constant with its source; `load_config()` from `configs/car.json` and `configs/dv.json` |
| `.../car/telemetry.py` | the car's `/pico/wheel_ticks` array (84 fields, layout 9) as a `Telemetry` sample |
| `.../car/odometry.py` | counts and IMU yaw to motion in the robot frame (C1); 32-bit count wrap, yaw wrap |
| `.../car/moves.py` | the five C2 moves, `bm.move/1`, the limits, `bm.move_result/1` |
| `.../car/executor.py` | `MoveExecutor`: the state machine (no clock, no I/O of its own) |
| `.../car/simcar.py` | `SimCar`: a deterministic simulated car with the firmware's behaviour |
| `.../car/link.py` | `SimLink` (executor + simulated car in simulated time); the link interface |
| `.../car/ros_io.py` | `RosCarLink` (the rclpy node), the STOP program, a simulated-car node for tests |
| `.../car/movelog.py` | one JSONL file per move in the recorder's session |
| `.../car/latch.py`, `camera.py`, `backend.py` | see `../M3.T13/README.md` and `../M3.T9/README.md` |
| `tools/car_move.py`, `tools/car.sh` | the command-line tool and its container wrapper |
| `beaconmind/tests/test_car_odometry.py` (33), `test_car_executor.py` (100), `test_car_stop.py` (27), `test_car_backend.py` (22), `test_car_ros_smoke.py` (13) | tests |

No existing file was edited. `beaconmind_bringup/setup.py` needs no entry point: the tool is a script.

## 2. Why the task text was adapted

The task text (plan `M3-real-car.md`, "M3.T6") describes a C executor inside a project Pico firmware with a wheel
PID, `/pico/move/cmd`, a heartbeat and a STBY line. The re-scope of 2026-11-09 (plan README §3.6, "Hardware
decision") keeps the firmware the car has, Assignment 8 **Build K2** (access-point variant `buildK2a_d485d7ab`),
and puts the executor on the host. What that firmware gives the host (sources in the private course repo,
`assignments/assignment8/module-8-sensor-fusion/firmware/pico_fusion/`; studied, nothing copied):

- `/pico/cmd_vel` (`geometry_msgs/Twist`): linear.x m/s, angular.z rad/s, left turn positive
  (`drive_control.c`: right wheel = v + w x 0.1335 / 2). **Open loop:** a wheel speed becomes a duty,
  `duty = min_duty + (1 - min_duty) x |v| / max_speed`; under 1 % of `max_speed` the duty is 0; a rising duty
  ramps at 1.0 per 0.3 s, a zero or a falling duty applies at once. So the real speed is not the commanded speed.
- **No command for 0.5 s stops the wheels** (`DRIVE_TIMEOUT_MS`; a timer interrupt drops the driver's standby
  100 ms later if the main loop is stuck). This is the property the whole design leans on.
- A command may carry its send time in linear.z; stamped motion older than 0.3 s is dropped. A disarmed car (after
  an abnormal boot, a session rebuild, or 3 s without the agent) ignores motion until a zero command with
  angular.x = 1.0 (`pico_fusion.c` `cmd_vel_callback`).
- `/pico/wheel_ticks` (`std_msgs/Int32MultiArray`, 84 fields, every 20 ms): counts, uptime, sequence number, flags
  (armed, IMU ready, drive status, stall cut-off), the IMU yaw in hundredths of a degree, the drive map, how long
  since the car heard the agent. Field numbers: `car/telemetry.py`.
- A wheel that does not move gets up to three jogs, then is cut off (about 2 s), and locked after three cut-offs.

Checked on 2026-11-18, read-only: the recorded session `data/real/20261118-000959-recorder-dry-run` (Spark) has 84
fields in every one of its 2,938 `wheel_ticks` messages, field 2 = 9, field 82 equal to the yaw of
`/pico/imu/data` within 0.002 degrees, flags 142 (armed, IMU ready, clock offset valid), drive map 0.46 / 0.215
(the boot map), telemetry gaps median 18 ms, 99th percentile 46 ms, longest 91 ms. `ros2 topic info -v` on the
live graph: one node `/pico_fusion`; all five `/pico/*` endpoints BEST_EFFORT, VOLATILE; no publisher on
`/pico/cmd_vel`.

Kept from the task text: the five moves and their names, the limits, the result enum, the order and meaning of the
checks, a profile that slows near the target, the heading hold on straights, the coast lead for turns measured on
these motors, "never complete a move from a host pose estimate" (this executor reads counts and yaw only), a log
of every move. Not kept, and why: the wheel-speed PID (no firmware of ours; the governor in §3 is the host-side
substitute for the mean speed only); bump detection (the bump key of step 1 was never approved, so `bump` is always
false and `bumped` is never returned); the heartbeat topic (the command stream is the heartbeat; the car's
`agent_rx_age_ms` field is the car-side view of it); STBY (S5 waived; the firmware drops standby itself on its
timeout).

## 3. Control design, with every number and where it came from

One move is a stream of velocity commands every 50 ms. **Telemetry decides, the clock sends:** each telemetry
sample (20 ms) updates the odometry and may end the move at once (a zero goes out with that sample, not at the next
50 ms tick); the 50 ms tick sends the next command and checks the time-based rules.

| Item | Value | Source |
| --- | --- | --- |
| Speed limit, turn-rate limit, timeout | 0.15 m/s, 45 deg/s, 5 s | `configs/dv.json` `v_max_mps`, `turn_rate_dps`, `move_timeout_s` |
| Executor's own caps | 0.25 m, 30 deg, and the three above; anything outside is `refused` | plan C2 |
| Counts per metre | 20,524 both wheels (**nominal**: 4,320 counts per turn / (pi x 0.067 m)) | firmware `encoders.h`, research note 2026-10-24 F6; `configs/car.json` `wheel_diameter_m`. The floor check writes `enc_ticks_per_m_left/right` into `car.json`; `load_config()` then uses them |
| Track width | 0.1335 m | `configs/car.json` `track_width_m` |
| Command period | 0.05 s | Module 8 `odometry/move_test.py` (the host moves that drove this car) |
| Straight: commanded speed | `min(0.15, max(0.05, 1.5 x remaining))` m/s, times the governor | `move_test.py` `MAX_SPEED`, `MIN_SPEED`, gain 1.5 |
| Turn: commanded rate | `min(0.6, max(0.3, 1.5 x remaining))` rad/s | `move_test.py` `MAX_TURN`, `MIN_TURN` |
| Stop tolerances | 5 mm, 1 degree, plus the coast lead | `move_test.py` `DIST_TOL`, `ANGLE_TOL` |
| Coast lead | measured speed x (coast time + the link's measured round trip); Module 8 used 0.09 s in all; here the coast part starts at 0.08 s and adapts (below) | Module 8 `odom_tools.py` `CAR_COAST_TIME`; private repo `assignment8/evidence/turn-calibration-move_test.txt` (90 degree turns came out 90.0 to 90.7 with it at drive map 0.25 / 0.33) |
| Heading hold on straights | w = 8 /s x (start heading - heading), limited to 1.2 rad/s | Module 8 `odom_tools.py` `CAR_HOLD_GAIN`, `CAR_HOLD_LIMIT`; `CONTEXT.md` 2026-11-02 (left wheel 70 to 74 % of the right on carpet; gain 2 / limit 0.5 gave 41 to 46 degrees over 0.30 m, 8 / 1.2 gave 4.3 to 4.7) |
| Expected drive map | 0.25 / 0.33; a move is `refused` when the car reports another | Module 9 carpet runs (private repo `discussions/module9/evidence/carpet/README.md`); the car reports its map in field 81. After any restart the car is back at 0.46 / 0.215, where a pivot ran at 141 to 148 deg/s (bench log m32c) |
| Link rule | 0.5 s without telemetry, or the car not hearing the host for 0.5 s: `link_lost` | `configs/dv.json` `watchdog_ms`; the same figure as `move_test.py` `LINK_GAP_S` |
| Stall window | 0.2 s | `configs/dv.json` `stall_window_ms` |

This file's own choices (`config.py` marks each "choice"); none has run on the car. Those marked (R) were added or
changed after the independent review of 2026-11-18 (section 7):

- **Steering never reverses the inner wheel** (`hold_allow_reverse=False`): the steering term is also limited to
  v / (track / 2). The firmware answers the smallest reverse command with its smallest duty, so a larger term flips
  the inner wheel from forward to backward, a relay in the loop. In the Module 9 runs the term stayed under this
  limit (0.66 rad/s needed at cruise), so the adopted behaviour is unchanged where it was measured.
- **The lead covers the link (R).** Each move measures the round trip (first command sent to the first telemetry
  sample that shows a duty on the wheels) and adds it to the coast time. The coast part adapts: after each move
  whose first approach ended at speed, (coast after the stop decision) / (speed at the decision), less the round
  trip, is averaged into the value the next move of that kind starts with, inside 0.03 to 0.30 s. This is the task
  text's "the lead is its own constant, measured on these motors", measured on every move and logged
  (`round_trip_s`, `coast_time_used_s`, `coast_time_measured_s`, `coast_time_next_s`).
- **Trim (R):** a move that has settled short of its target by more than 5 degrees or 2 cm goes on (at most twice):
  from rest the second approach is a short pulse, which is how the last degrees are reached on a firmware whose
  slowest pivot is fast.
- **`done` is checked, not assumed (R).** After the stop decision the car must show zero duty within 0.3 s and must
  be hearing the host, the counts must go quiet before the settle time runs out, and the car must not have ended
  more than 4 cm or 10 degrees past its target. Otherwise the move ends `link_lost` (`stop_not_confirmed` or
  `overshoot`) and latches.
- **Divergence ends a move (R).** A straight whose heading leaves the start heading by 15 degrees ends: `stalled`
  when one wheel covered under a fifth of the other (a blocked wheel seen through the heading), else `link_lost`
  (`heading_diverged`). A move that goes 3 cm or 10 degrees the wrong way ends `link_lost` (`wrong_way`).
- **Speed governor** (straights only): the commanded speed is scaled by a factor between 0.15 and 1 that falls at
  2.5 /s x the relative overspeed while the measured speed is above 0.15 m/s and creeps back at 0.25 /s below it.
  (R) It starts at 0.7, not 1, and the factor and the coast times are saved in `data/car_executor_state.json`
  after every move and loaded by the next process, so a fresh `car_move.py` does not start over. A car too fast
  for any command above the firmware's dead band cannot be brought under the limit; the log then says
  `over_speed_limit`.
  **Turns are not governed** (`govern_turn=False`): at the smallest duty this car pivoted at 87 to 89 deg/s
  (private repo `assignment8/evidence/turn-cal-rates.txt`, drive map 0.25 / 0.33), so 45 deg/s cannot be held by
  this firmware; the reviewer measured that turning the governor on still peaks at 76 deg/s in simulation. Each
  result's log says `over_rate_limit`. This is a deviation from `turn_rate_dps` for Xiaohui to accept or to answer
  with a lower smallest duty after the floor check.
- **Stall rule:** a wheel commanded at least 0.015 m/s one way for 0.6 s that then covers less than 0.01 m/s x the
  0.2 s window is `stalled` (`stall_left` / `stall_right`); the firmware's own cut-off is `stalled`
  (`firmware_cutoff`: the counter rising, or (R) the flag once this move's commands have reached the car, because
  the firmware clears a cut-off on a fresh start); a start-assist of the firmware restarts the watch. The design
  rule (under 50 % of the profile) needs wheels that follow a profile, which open loop they do not (research note
  2026-10-11 F2); 0.6 s instead of the design's 0.2 s grace lets the firmware's duty ramp and first jog happen.
- **Blind pause:** with no telemetry for 0.12 s the executor sends zeros (the car pauses) and resumes when samples
  return; at 0.5 s the move ends `link_lost`. It never drives on stale counts. (R) A move does not start on
  telemetry older than 0.12 s.
- **Settle:** after the stop decision zeros are sent every 50 ms for at least 0.3 s, until no count changed for
  0.16 s (with samples still arriving), at most 1.2 s. Only then are the final counts and heading read.
- **Stamped commands:** motion commands carry the send time, so the car drops any that arrive more than 0.3 s
  late (a delayed burst cannot restart the wheels after a stop). Zeros are never stamped. Three stamped commands
  dropped by the car end the move (`stale_commands`). `--unstamped` turns it off (the Module 9 runs were
  unstamped).
- **A restart of the car (R)** is believed when three samples in a row carry a lower uptime and a lower sequence
  number; one late sample is ignored.
- **One commander (R):** a commanding `RosCarLink` holds an exclusive lock on `data/CAR_LINK.lock`; a second one
  (another `car_move.py`, or the tool beside a harness) is refused.
- A move does not start unless: no latch (and (R) no latch write that failed earlier); telemetry under 0.12 s old;
  armed; IMU ready; no locked wheel; the car has a clock offset; the expected drive map; the car at rest. The
  executor never arms the car (D6: only an operator arms): `car_move.py arm --i-am-at-the-car`.

Results (`bm.move_result/1`): `done`; `stalled`; `timeout`; `link_lost` with reason `telemetry_gap`,
`car_disarmed`, `car_not_hearing`, `car_command_timeout`, `car_rebooted`, `session_rebuilt`, `stale_commands`,
`imu`, `stop_not_confirmed`, `overshoot`, `heading_diverged`, `wrong_way`, `estop` (a STOP during the move: OD15 option a, the plan's proposed default), `executor_error: ...`;
`refused` with the reason. `link_lost` (other than `estop`) and any restart of the car set the latch (C5 item 2;
plan §3.6 hardware procedure 4). `boot_id` counts the car's restarts seen by this process. `achieved_forward_m` is
the mean of the two wheels' distances; `gyro_dyaw_deg` the IMU heading change; both read after the settle.

**The car always gets a stop.** Every exit path of the executor goes through one function that switches to
"stopping" and returns a zero; an exception inside the executor does the same and ends the move `link_lost`
(`test_an_internal_error_still_stops_the_car`); Ctrl+C, `docker stop` and a move that outlives its budget send
zeros from the calling thread. And none of that is needed for safety: if the process, the container, the Spark or
the Wi-Fi dies, no more commands arrive and the car stops itself after 0.5 s
(`test_the_car_stops_by_itself_when_the_host_dies_mid_move`, and on real rclpy
`test_the_simulated_car_stops_by_itself_after_one_command`).

## 4. Test results

Mac, Python 3.13 (`pytest-mac.txt`): **182 passed, 2 skipped** (the rclpy file and the OpenCV test). Whole suite
once at the end: `498 passed, 10 skipped`.

Container on the Spark, Python 3.10.12, rclpy, **ROS_DOMAIN_ID 42, `--network none`** (`pytest-container.txt`):
**195 passed, 1 skipped** (a file-permission test that root cannot run). The rclpy file asserts the domain is 42
before it creates any node, and the simulated-car node refuses domain 0; the container had no network interface
but loopback.

```
tests/test_car_ros_smoke.py::test_domain_is_42_not_the_real_cars_0 PASSED
tests/test_car_ros_smoke.py::test_telemetry_arrives_and_nothing_is_published_while_idle PASSED
tests/test_car_ros_smoke.py::test_forward_25 PASSED
tests/test_car_ros_smoke.py::test_turn_left_30_is_positive_yaw PASSED
tests/test_car_ros_smoke.py::test_the_simulated_car_stops_by_itself_after_one_command PASSED
tests/test_car_ros_smoke.py::test_stop_during_a_move_and_latch_refusal PASSED
tests/test_car_ros_smoke.py::test_read_only_link_has_no_publisher PASSED
tests/test_car_ros_smoke.py::test_only_one_program_may_hold_the_car_link PASSED
tests/test_car_ros_smoke.py::test_learned_values_are_saved_for_the_next_process PASSED
tests/test_car_ros_smoke.py::test_a_dead_spin_thread_refuses_a_move PASSED
tests/test_car_ros_smoke.py::test_an_interrupt_during_a_move_stops_the_car PASSED
tests/test_car_ros_smoke.py::test_one_shot_stop_writes_the_latch PASSED
tests/test_car_ros_smoke.py::test_stop_key_program_in_a_terminal PASSED
======================= 195 passed, 1 skipped in 31.01s ========================
```

The first and the fourth move of a fresh executor on the simulated car (simulated hard floor: 0.33 m/s per unit
duty, so about twice the commanded speed, as measured on the real car in pivots). All 80 moves ended `done`:

| Move | Simulated car | 1st move | 4th move | Peak speed / rate (4th) | Duration s (4th) |
| --- | --- | --- | --- | --- | --- |
| FORWARD_25 | matched wheels | +0.243 m | +0.246 m | 0.16 m/s | 2.25 |
| FORWARD_10 | matched wheels | +0.092 m | +0.097 m | 0.16 m/s | 1.20 |
| BACKWARD_10 | matched wheels | -0.092 m | -0.097 m | 0.16 m/s | 1.20 |
| TURN_LEFT_30 | matched wheels | +28.0 deg | +29.4 deg | 89 deg/s | 0.80 |
| TURN_RIGHT_30 | matched wheels | -28.0 deg | -29.4 deg | 89 deg/s | 0.80 |
| FORWARD_25 | left wheel 70 % (carpet) | +0.244 m | +0.246 m | 0.16 m/s | 2.25 |
| FORWARD_10 | left wheel 70 % (carpet) | +0.093 m | +0.096 m | 0.14 m/s | 1.30 |
| BACKWARD_10 | left wheel 70 % (carpet) | -0.093 m | -0.096 m | 0.14 m/s | 1.30 |
| TURN_LEFT_30 | left wheel 70 % (carpet) | +28.3 deg | +30.2 deg | 77 deg/s | 0.85 |
| TURN_RIGHT_30 | left wheel 70 % (carpet) | -28.3 deg | -30.2 deg | 77 deg/s | 0.85 |
| FORWARD_25 | 60 ms each way | +0.241 m | +0.246 m | 0.16 m/s | 2.30 |
| FORWARD_10 | 60 ms each way | +0.090 m | +0.097 m | 0.17 m/s | 1.25 |
| BACKWARD_10 | 60 ms each way | -0.090 m | -0.097 m | 0.17 m/s | 1.25 |
| TURN_LEFT_30 | 60 ms each way | +30.7 deg | +30.4 deg | 80 deg/s | 0.90 |
| TURN_RIGHT_30 | 60 ms each way | -30.7 deg | -30.4 deg | 80 deg/s | 0.90 |
| FORWARD_25 | 100 ms each way | +0.238 m | +0.247 m | 0.16 m/s | 2.35 |
| FORWARD_10 | 100 ms each way | +0.089 m | +0.095 m | 0.18 m/s | 1.30 |
| BACKWARD_10 | 100 ms each way | -0.089 m | -0.095 m | 0.18 m/s | 1.30 |
| TURN_LEFT_30 | 100 ms each way | +34.6 deg | +34.3 deg | 70 deg/s | 1.05 |
| TURN_RIGHT_30 | 100 ms each way | -34.6 deg | -34.3 deg | 70 deg/s | 1.05 |

What the tests assert:

- targets: all five moves with matched wheels, the 70 % left wheel, a slow car, an 85 % right wheel; **link latency
  0, 30, 60 and 100 ms each way**, four moves each: turns within 5 degrees from the first move up to 60 ms and
  within 9 (first) and 6 (fourth) at 100 ms; straights within 2 cm (first) and 1.2 cm (fourth); the simulated car's
  true pose is checked, not only the report; left turn = positive yaw = left wheel backward, right forward; counts
  crossing the 32-bit wrap and a heading crossing 180 degrees change nothing;
- limits measured on the simulated car's true speed: forward speed inside 0.15 m/s + 10 % from the first move; a
  plant twice as fast and the turn rate are reported as over the limit, not hidden;
- every early end: timeout (slow car; a turn on the stand), stall (each wheel, both wheels, the firmware's cut-off,
  a leftover cut-off flag that must not count), telemetry gap (pause at 0.12 s, `link_lost` at 0.5 s, latch set,
  next move refused), a short gap ridden through, commands not reaching the car, **stop commands not reaching the
  car** (`stop_not_confirmed` / `overshoot`, never `done`), an overshoot past the bound, a heading hold that swings
  (ended at 15 degrees), a turn the wrong way, the car disarming, the car restarting (during a move, idle, and
  0.3 s after boot), late, repeated and swapped telemetry (no false restart), stale commands, IMU dropout, an
  internal error in the tick and in the telemetry path, telemetry lost after the stop, STOP during a move, latch
  refusal, a latch that cannot be read (counts as set) or written (every later move refused);
- refusals send nothing: disarmed, IMU not ready, no clock, wrong drive map, telemetry older than 0.12 s, bad
  command, zero distance, busy, car moving; yaw noise of 0.2 degrees at rest does not refuse a move;
- the deadman, **on the simulated firmware model only**: the host dies mid-move, nothing more is sent, the
  simulated car stops by its own 0.5 s timeout. These tests prove the executor leaves the car in a state where that
  timeout applies (the last message is an ordinary motion command, refreshed every 50 ms, with no "run for N
  seconds" message anywhere); they do not prove the real firmware's timeout, which stand step S7 checks;
- every result validates against `bm.move_result-1`; nothing is published when idle.

Limits found by sweeping the simulated car (plant speed, wheel imbalance, delay, motor lag): a car twice as fast as
the real one with 60 to 100 ms each way overshoots its first turn past the bound and gets `link_lost` / `overshoot`
(not `done`); a 50 % left wheel with 60 ms each way makes the heading hold swing and ends `heading_diverged`; at
the measured carpet ratio (70 %) it holds up to 100 ms each way. The simulated car is a stand-in, not a calibrated
model.

## 5. Procedures for Xiaohui

Rules for every step (plan §3.6 "Hardware decision"; safety rules S1, S2, S4, S6, S7, S13): the Pico (power bank)
on first, **the motor battery last and off first**; the motor battery on only while a step is under way, a hand on
its switch; the **first switch-on of the session with the car on its stand, wheels up**; the recorder running
whenever the motor battery is on; a restart of the car during a step ends the session (battery off, look, then
continue); lift the car to place it, never roll it. Spark host, `cd ~/Projects/en665715-beaconmind`.

### 5.0 Before the motor battery (parked, battery off)

1. `bash course-project/tools/car_net.sh status` : the access point, the agent and the camera relay are up.
2. `bash course-project/tools/record_session.sh start stand-test --operator "Xiaohui Chen"`; film
   `python3 course-project/tools/session_clock.py` with the phone, then keep the phone on the car.
3. Terminal A: `bash course-project/tools/car.sh stop-key` (leave it open; SPACE = STOP).
4. Terminal B: `bash course-project/tools/car.sh state`.
   **Pass:** `telemetry_age_s` under 0.1; `armed: true`; `imu_ready: true`; `clock_ok: true`; `layout_error: null`;
   `latch: null`; `stop_program_alive: true`; `recorder_session` set. `drive_map` will read `[0.46, 0.215]` after a
   restart of the car.
5. Set the drive map the gains belong to: `bash course-project/tools/car.sh set-map 0.25 0.33 --i-am-at-the-car`
   (this publishes on `/pico/imu/std`; no wheel moves). **Pass:** `the car reports drive map [0.25, 0.33]`.
6. Refusal without the flag: `bash course-project/tools/car.sh move FORWARD_10`. **Pass:** `refused: a real move
   needs --i-am-at-the-car`, nothing sent.

### 5.1 Stand test (wheels up)

Car on the stand, both drive wheels in the air and free. Motor battery **on** (first switch-on: watch the wheels;
a twitch at switch-on is the known risk of the waived pull-down, a wheel that keeps turning is a stop: battery off).

| # | Command (`bash course-project/tools/car.sh ...`) | Pass |
| --- | --- | --- |
| S1 | `move FORWARD_10 --i-am-at-the-car` | both wheels turn **forward** (toward the camera end), then stop; `"result": "done"`; `achieved_forward_m` 0.09 to 0.12; both `enc_*_ticks` positive |
| S2 | `move FORWARD_25 --i-am-at-the-car`, three times | `done` each time; `achieved_forward_m` 0.23 to 0.27; `diag.peak_speed_mps` and `diag.round_trip_s` printed (free wheels run faster than on the floor; `over_speed_limit` on the stand is not a failure) |
| S3 | `move BACKWARD_10 --prev-forward 0.10 --i-am-at-the-car` | both wheels turn backward; `done`; both `enc_*_ticks` negative |
| S4 | `move TURN_LEFT_30 --i-am-at-the-car` | the **left wheel turns backward, the right forward**, at low speed, for 5 s; `"result": "timeout"` (on the stand the car cannot rotate, so the IMU sees no turn: the expected stand result, and the proof of the timeout) |
| S5 | `move TURN_RIGHT_30 --i-am-at-the-car` | the mirror image; `timeout` |
| S6 | STOP: steps 4 to 6 of `../M3.T13/README.md` | as stated there |
| S7 | Deadman: start `move FORWARD_25 --i-am-at-the-car`, press Ctrl+C in terminal B while the wheels turn; then start it again and close terminal B's window | the wheels stop within about half a second both times |
| S8 | Stall (optional, only with Xiaohui's agreement; S8 of the safety rules says never hold a wheel stalled for long): not run on the stand | — |

Any `stalled` on the stand is a false stall: stop and tell Claude. Any `link_lost` sets the latch: read the reason
in the printed result, `bash course-project/tools/car.sh clear-latch --operator xiaohui` after looking at the car.
Motor battery **off** before anything else is touched. `bash course-project/tools/record_session.sh stop`.

Copy the printed results into `evidence/M3/M3.T6/stand-test.md` with the session's name. The move logs are in
`data/real/<session>/moves/`.

### 5.2 Floor check (work list 2.8), after the stand test passed

On the floor of the arena, clear space of at least 1 m ahead and 0.5 m around, a tape line on the floor along the
car's heading, a tape cross under the axle midpoint. New recorder session (`start floor-check`), STOP program
running, drive map set (5.0 step 5), a hand on the switch.

| # | What | Measure | Pass |
| --- | --- | --- | --- |
| F1 | `move FORWARD_25`, four times from the cross (lift the car back each time) | tape: axle midpoint's displacement along the line; sideways offset; heading by eye against the line | `done`; from the third run on, tape distance 0.25 m within 2 cm; printed `achieved_forward_m` within 1 cm of the tape; heading change under 6 degrees |
| F2 | `move FORWARD_10`, three times; after each, `move BACKWARD_10 --prev-forward <achieved>` | tape | forward 0.10 m within 1.5 cm; the car returns within 1.5 cm of the cross |
| F3 | `move TURN_LEFT_30` x 3 from the line, then `TURN_RIGHT_30` x 3 | heading against the line after each set (3 x 30 = 90 degrees: use the room's right angle or a set square); printed `gyro_dyaw_deg` | each `done`; the three turns sum to 90 degrees within 8; `gyro_dyaw_deg` sums to the taped angle within 4 |
| F4 | Scale: one straight of four `FORWARD_25` in a row without lifting | tape total against the sum of `achieved_forward_m` | ratio inside 0.97 to 1.03; the ratio and each wheel's counts go to Claude, who writes `enc_ticks_per_m_left/right` into `configs/car.json` |
| F5 | STOP on the floor: SPACE during a `FORWARD_25` | by eye and the video | the car stops within about 5 cm; `link_lost` / `estop` |

From the logs Claude then reads: the measured coast times (expected to settle; if a turn's first value differs a
lot from 0.09 s, the constant is changed), the peak speed and turn rate (the turn rate will be above 45 deg/s; see
§3), whether the heading hold saturated, telemetry gaps and blind pauses, any `assists` or `cutoffs`.

Stop and tell Claude if: a move drives more than 5 cm past its distance or a turn more than 15 degrees past its
angle; the car curves more than 10 degrees in a straight; a `stalled` on open floor; two `link_lost` in one
session; the car restarts.

## 6. Open items (need the car or a decision)

1. Nothing here has run on the real car. Every control number in §3 is from Module 8/9 runs with a different
   feedback path, or is this file's choice.
2. Encoder scale is nominal. The left encoder counts edges and may read 0.5 to 2 % high (firmware `encoders.h`).
   F4 settles it.
3. The turn rate exceeds `turn_rate_dps` (45 deg/s) on this firmware at drive map 0.25 / 0.33. Options after F3:
   accept it; try a lower smallest duty (`set-map 0.20 0.33`; carpet may then stall a wheel); or turn the governor
   on for turns (`govern_turn`, untested on the car).
4. The drive map is lost at every restart of the car and must be set again (5.0 step 5); a move is refused until
   it is. Whether to keep 0.25 / 0.33 on the arena's floor is open until F1 to F3.
5. Bump detection is off (no approved threshold). A contact shows as `stalled` or `timeout`.
6. `estop_max_s` (0.2 s) and the real link's latency are unmeasured; the logs of S6 and F5 give them.
7. Stamped commands assume the container's clock is the Spark's clock, which the car synchronises to through the
   agent. If S1 ends `link_lost` / `stale_commands`, use `--unstamped` and tell Claude.
8. The firmware arms on a plain zero command in one state (disarmed without needing the marker); the STOP flood
   sends zeros. With the latch set nothing of this project then sends motion.
9. The integral term of the heading hold exists (`hold_integral_per_s2`, default 0) and is untested on the car.

## 7. Independent review of 2026-11-18: finding, outcome, test

A second agent reviewed the package adversarially (its probes: the session scratchpad, `review/probe1.py` to
`probe5.py`, `pty_drive*.py`). No critical finding; 7 major, 14 minor. Tests are in `beaconmind/tests/`;
"smoke" = `test_car_ros_smoke.py` (container), "exec" = `test_car_executor.py`, "stop" = `test_car_stop.py`,
"backend" = `test_car_backend.py`.

| # | Finding | Outcome | Test |
| --- | --- | --- | --- |
| 1 | STOP key could sit unread behind a buffered read | fixed: raw `os.read`, every byte acted on; keys typed during the flood are dropped; end of input ends the program with an error | stop `test_no_key_is_lost_when_several_arrive_together`; smoke `test_stop_key_program_in_a_terminal` |
| 2 | after the 3 s flood only one zero per 100 ms | fixed: 50 zeros per second for as long as the latch exists | stop `test_the_car_stays_stopped_for_as_long_as_the_latch_exists` |
| 3 | `done` without checking the stop arrived or where the car ended | fixed: zero duty within 0.3 s, car hearing the host, quiet counts, overshoot bound; else `link_lost` + latch | exec `test_stop_commands_that_do_not_arrive_are_not_done`, `test_an_overshoot_past_the_bound_is_not_done` |
| 4 | turns overshoot with link latency; rate about twice the limit | fixed for latency: measured round trip added to the lead, coast adapts, trim; 30 deg came out 47.3 at 100 ms, now 34.6. **Declined for the rate:** the firmware's smallest duty sets it (see section 3); reported per move | exec `test_turns_with_link_latency`, `test_straight_moves_with_link_latency`, `test_a_move_that_stops_short_is_finished_by_a_second_approach`, `test_turn_rate_is_over_the_design_limit_and_says_so` |
| 5 | speed limit not held on the first move; nothing kept between processes | fixed: governor starts at 0.7, floor 0.15, state saved and loaded | exec `test_the_speed_limit_holds_from_the_first_move`, `test_a_car_faster_than_its_smallest_duty_allows_is_reported`; smoke `test_learned_values_are_saved_for_the_next_process` |
| 6 | heading hold swings with delay on a strongly asymmetric car | fixed as asked: the move ends at 15 degrees (`heading_diverged`, or `stalled` when one wheel is not turning). A damping term on the yaw rate was tried in simulation and changed nothing, so it stays off (`hold_rate_gain_s`) | exec `test_an_oscillating_heading_hold_is_ended_not_called_done`, `test_heading_hold_is_what_keeps_the_carpet_car_straight` |
| 7 | latch check failed open on a file-system error | fixed: `os.lstat`; anything but "no such file" counts as set | stop `test_latch_check_fails_closed`, `test_latch_in_an_unsearchable_directory_counts_as_set` |
| 8 | a late sample taken as a restart; a restart within 1 s of boot missed | fixed: three consecutive samples with lower uptime and sequence | exec `test_late_repeated_and_reordered_telemetry`, `test_a_restart_soon_after_boot_is_still_seen` |
| 9 | spin-thread death could be missed at the start of a move | fixed: refused when the thread is dead; the wait is in 0.1 s slices | smoke `test_a_dead_spin_thread_refuses_a_move` |
| 10 | start block outside the try | fixed | smoke `test_an_interrupt_during_a_move_stops_the_car` |
| 11 | log closed without the lock | fixed (closed under the lock) | same test (`_movelog is None`, link usable again) |
| 12 | one-shot `stop` wrote the latch last | fixed: latch first, then ROS and the zeros | smoke `test_one_shot_stop_writes_the_latch` |
| 13 | `docker stop` did not reach Python | fixed: `exec python3` in `car.sh` | stop `test_wrapper_lets_signals_reach_python` (text check; not run under docker) |
| 14 | preflight holes | fixed: heartbeat carries its domain and subscriber count and both are checked; end of input ends the STOP program; an exclusive lock makes one commander; `BACKWARD_10` needs `--prev-forward`. **Declined:** re-checking the heartbeat during a move (the latch is checked on every sample; unattended batches have nobody at a keyboard) | stop `test_tool_preflight`, `test_heartbeat_names_its_domain_and_its_subscribers`, `test_tool_refuses_backward_without_the_forward_distance`; smoke `test_only_one_program_may_hold_the_car_link` |
| 15 | `arm()` checked the latch once | fixed: latch and busy checked before every marker | smoke `test_stop_during_a_move_and_latch_refusal` (latched: `arm()` false, nothing published) |
| 16 | BACKWARD_10 bookkeeping in the backend | fixed: offered exactly when it would run; a refused step carries no old details | backend `test_backward_is_offered_exactly_when_it_would_run`, `test_a_move_stalled_part_way_can_be_backed_out`, `test_a_refused_step_does_not_reuse_the_previous_moves_details` |
| 17 | start accepted telemetry up to 0.5 s old | fixed: refused above 0.12 s | exec `test_stale_telemetry_refuses_instead_of_starting_and_latching` |
| 18 | a leftover cut-off flag ended a move at once | fixed: the flag counts once this move's commands reached the car. The firmware source says a fresh start clears a cut-off (`drive_control.c` `assist_reset`); not seen on the car | exec `test_a_cut_off_flag_left_from_before_does_not_end_a_new_move` |
| 19 | rest check sensitive to yaw noise | fixed: 10 deg/s | exec `test_noisy_heading_at_rest_does_not_refuse_a_move` |
| 20 | a wrong-way turn ran to the timeout | fixed: `wrong_way` | exec `test_a_turn_that_goes_the_wrong_way_is_ended` |
| 21 | idle restart with a failed latch write was silent | fixed: every later move refused (`latch_write_failed`) | exec `test_a_latch_that_cannot_be_written_refuses_every_later_move` |

Tests the review called weaker than their names: the host-dies tests are now described as tests of the simulated
firmware model (section 4, and section 8 item 1 for the real check); the zero-flood test has the ten seconds after
the flood; late telemetry has a 2 s old and a swapped sample; limits are checked on the simulated car's true
speed; latency runs to 100 ms each way; the telemetry-path exception, the interrupt, the spin-death and the
read-only link have their own tests. Still untested: the host-wait-timeout branch of `RosCarLink.execute`.

## 8. What stops the car when nobody is there

For unattended batches with the motor battery on. Each row: what stops the car, what it depends on, and what has
not been seen on the real firmware. **The first attended stand test must tick off the last column** before any
unattended run.

| # | Mechanism | Stops the car when | Depends on | Not yet verified on the real car |
| --- | --- | --- | --- | --- |
| 1 | The firmware's command timeout (0.5 s; a timer interrupt drops the driver's standby at 0.6 s) | the host process, the container, the Spark, the agent or the Wi-Fi dies, or the executor stops sending | the firmware itself; nothing on the host. Fact from the firmware source (`DRIVE_TIMEOUT_MS`), used by 40 Module 9 runs | that it is 0.5 s on this image: stand step S7 (Ctrl+C, then closing the window, mid-move) |
| 2 | The firmware's stale-command guard (stamped motion older than 0.3 s is dropped) | a burst of delayed commands arrives after a stop | the car's clock offset (flag bit 7) and the container sharing the Spark's clock | that stamped commands are accepted at all (S1), and that a late one is dropped (not testable without delaying the link) |
| 3 | The firmware's disarm after 3 s without the agent, and after an abnormal boot | the link was down for seconds; the Pico restarted | the firmware; the executor never re-arms (only `car_move.py arm`) | not exercised; do not rely on it |
| 4 | The firmware's stall cut-off (about 2 s) and lock | a wheel is blocked | the firmware | not exercised by this code |
| 5 | The executor's end-of-move zeros and settle | every move, every abort | the host process alive and the link up; if not, row 1 | S1 to S5 |
| 6 | The executor's link rules: no telemetry 0.12 s (pause) / 0.5 s (end), car not hearing, car's own timeout seen, disarmed, session rebuilt, stale commands, IMU | the link or a sensor fails during a move | telemetry fields 3, 4, 14, 18, 38, 41, 50 meaning what the source says (checked on a parked bag only) | field 50 and the status bits while driving: the first move's log |
| 7 | The executor's stall rule, heading bound (15 deg), wrong-way bound, timeout (5 s) | the car is blocked, veers, turns the wrong way, or is too slow | wheel counts and IMU yaw | a real stall (not run on the stand by choice, S8); the heading bound on carpet (F1) |
| 8 | `done` is checked: stop confirmed within 0.3 s, overshoot bound | the stop did not land | telemetry field 12/13 (duty) reading 0 after a stop | that the duty fields read 0 within 0.3 s of a zero on the real car (S1's log: `duty` in the `tel` lines after `stop`). If the real firmware reports a duty longer, every move ends `stop_not_confirmed` and latches: safe, but nothing runs |
| 9 | The latch (`course-project/data/LATCH`) | any `link_lost` except a STOP, any restart of the car, the STOP program, the operator | the file system (a check that cannot read counts as set); every program that commands the car checking it: the executor does on every sample and tick; the closed-loop harness watches it when run with `--watch-latch course-project/data/LATCH` | S6 |
| 10 | The STOP program (zeros 100 per second for 3 s, then 50 per second while latched) | a person presses SPACE | a person, a terminal, the link | S6. **Unattended, nobody presses it**: rows 1 and 5 to 9 are what is left |
| 11 | The backend's forward flags and the harness's validator | the agent asks for a move toward a wall | tags in view, or the room polygon with the dead-reckoned pose, which drifts | the practice run |
| 12 | The motor battery's switch | a person is there | a person | — |

What is **not** covered when nobody is there: a wall the car reaches without a tag in view and with a drifted
dead-reckoned pose (it ends as a stall or a timeout after contact, at up to 0.15 to 0.2 m/s); a motor driver that
ignores the firmware (a wheel that keeps turning at switch-on is the known risk of the waived pull-down); a Pico
that restarts with the battery on (the driver inputs float for about 1.5 s: plan section 3.6); the room itself
(a door opened, something on the floor). Rows 1 to 4 are facts read from the firmware source, not measurements by
this project; this project has measured none of them on the car.

