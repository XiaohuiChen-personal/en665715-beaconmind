# Car firmware lessons from Assignment 7 (Builds G to J2) and the role of the wheel PID (2026-10-24)

**Read this before M3.T14 (build chain), M3.T2 (firmware skeleton), M3.T3 (encoders), M3.T4 (motors and PID),
M3.T6 (move executor), M3.T7 (wheels-down gate) and the tasks added on 2026-10-24 (M3.T21 to M3.T24).** It records what
two weeks of work on the car's Module 7 firmware taught about this car, this Wi-Fi mesh and this Pico, and answers two
questions Xiaohui asked on 2026-10-24: can the Assignment 7 firmware serve as the project firmware, and is a wheel-speed
PID useful for BeaconMind? It also lists the plan changes made from it (section 5).

Owner: Xiaohui Chen. Written by Claude Opus 5.5 via Claude Code from the session's logs, the firmware sources and two
read-only multi-agent checks (a project-fit check with a critic, and the J2 code review); Xiaohui ran the car and made
the decisions recorded here. Line numbers are as of 2026-10-24 and drift as files change.

**Decision recorded (Xiaohui, 2026-10-24): the project may reuse the instructor's code.** This replaces the earlier
plan rule (README L11, "never paste ... the instructor's firmware"; M3.T4/T5/T14 "studied, wrote fresh"). Reused code
keeps a comment naming the instructor file it came from, and every part Claude changed keeps its AI disclosure
(AGENTS.md §5; syllabus "Generative AI Usage Policy"). Upstream, tutorial and internet code is still never pasted.
AGENTS.md §5 records the exception (updated 2026-10-24), together with the rule that every later lab's Pico firmware is
ported onto the car's Wi-Fi-hardened firmware (Build J2) instead of flashing the instructor's main as given.

## 0. Sources (all in this repo unless marked)

| What | Where |
| --- | --- |
| The car's firmware (instructor's Module 7 guide code plus Builds A to J2) | `assignments/assignment7/module-7-kinematics-control/firmware/pico_odometry/` (builds H to J2 uncommitted on 2026-10-24) |
| Which files are the instructor's | `assignments/assignment7/tools/guide-files.sha256` (checksums); pristine copies of five files in `assignments/assignment7/guide-original/firmware/pico_odometry/` |
| Bench log, every run since 2026-10-20 | `assignments/assignment7/evidence/new-motor-bench-2026-10-20.md` |
| Wi-Fi survey of the house mesh (Mac, Spark, Pico; monitor captures) | `assignments/assignment7/evidence/wifi-survey-2026-10-23.md` |
| Wi-Fi roaming design J0 to J4, with as-built notes | `reference/hardware/wifi-roaming-design-2026-10-23.md` (4.2, 4.3, 4.4) |
| Floor-spot A/B runs and the 20-min soak (per-message CSV, ping, summaries) | `assignments/assignment7/evidence/floor_logs/ab_1024/` |
| Motor research after the failures | `reference/hardware/motor-options-2026-10-22.md` |
| Module 7 PID discussion (simulated) | `discussions/module7/README.md`, `discussions/module7/module7-pid.html`; simulator `sim/sim_pico_pid.py` |
| The instructor's PID firmware (`pid.c`, `wheel_control.c`, node) | **not in the repo**: `~/Downloads/pid-source-files.html` on the Mac (53 KB, 2026-10-19). M3.T4 step 0 archives it |
| Earlier drive lessons (Module 6) | `course-project/research/2026-10-11-sim-to-real-drive-lessons.md` |

## 1. Bottom line

1. **The Assignment 7 firmware cannot be dropped in as the project firmware, but much of it can be reused.** It
   speaks a continuous `/pico/cmd_vel` stream, boots armed, and has no `/pico/arm`, `/estop`, latch, move executor,
   move results or boot id: the project's contract C2 (README) is a different interface. Its micro-ROS library
   allows 3 publishers and 2 subscriptions; C2 needs 6 and 4 (M3.T14 builds 6/6).
2. **What to reuse:** the Wi-Fi and safety layer that was written for this car (`wifi_link`, `wifi_events` with
   `cyw43_hook.h`, `safety`, `diag`, later `wifi_roam`), J1's session supervisor (moved into its own file), and,
   now that instructor code may be reused, the instructor's drivers (`tb6612.c`, `encoders.c`, `bno055.c`), UDP
   transport, CMake files and `pid.c` / `wheel_control.c` as starting points.
3. **The Wi-Fi link, not the PID, is the project's largest hardware risk.** At the car's floor spot the house mesh
   delivers multi-second stalls that no firmware removes. The project wants a 500 ms heartbeat watchdog, a 0.2 s
   STOP and an episode latched on any `link_lost`. Measure the link early, with the camera streaming (new task
   M3.T22).
4. **Several plan rules contradict what was measured** (section 2, F3 and F4): a 1000 ms hardware watchdog, "never
   block more than 200 ms", "reboot after 3 failed pings" and S11's "reboot the Pico after any agent restart". They
   were changed on 2026-10-24 (section 5).
5. **The wheel PID is useful, as the inner loop of the move executor** (section 3). It must run off the main loop
   (core 1 or a hardware timer at 100 Hz) and be tuned on the real car; the simulator's gains do not transfer. Its
   tuning is now its own task (M3.T21 on the stand, M3.T24 on the floor).

## 2. Facts established (with evidence)

### F1. The Assignment 7 firmware is the instructor's Module 7 guide code with the car's own layers added.

- Instructor files (checksums in `tools/guide-files.sha256`): `CMakeLists.txt`, `pico_odometry.c`, `encoders.*`,
  `drive_control.*`, `tb6612.*`, `bno055.*`, `picow_udp_transport.*`, `microros_time.c`, `lwipopts.h`. `bno055.*`,
  `microros_time.c` and `lwipopts.h` are unchanged; the others carry "CHANGED/ADDED for Build X" blocks.
- Written for this car by Claude Opus 5.5 via Claude Code (each file has its disclosure header): `safety.c/.h`
  (boot cause, watchdog, crash record), `diag.c/.h` (step timing), `wifi_link.c/.h` (Wi-Fi supervisor),
  `wifi_events.c/.h` and `cyw43_hook.h` (the driver's event dump read without a radio call; it matches
  cyw43-driver v1.1.1 format strings and refuses to build against another version), `wifi_roam.c/.h` (J2's node
  choice). The J1 session supervisor lives inside the instructor's `pico_odometry.c`.
- Interface: node `pico_odometry`; best-effort `/pico/cmd_vel` (`Twist`) in; `/pico/wheel_ticks`
  (`Int32MultiArray`, 75 fields from layout 7), `/pico/imu/heading` (`Float32`), `/pico/drive/status` (`Int32`) out.
- Drive: open loop. One duty map for both wheels, `duty = 0.46 + 0.54 x |v| / 0.215` (`drive_control.c:28,34,357-362`),
  linear cap 0.30 m/s (`:37`, twice the project's 0.15), a 500 ms command timeout, a 600 ms deadman in a 10 ms timer
  interrupt that drops STBY, start-assist and a stall cut-off (Build I). No speed control.

### F2. The Wi-Fi link at the car's floor spot has multi-second stalls that come from the network.

- The house mesh: 6 eero nodes, all on 2.4 GHz channel 6 (about 55 % busy), two of them with a wireless backhaul near
  the car; 802.11k/v, no 802.11r; no Ethernet cable is available for the backhaul (survey; design §1-2).
- Spark-to-Pico ping at the floor spot on 2026-10-23 (5 Hz): median 4-7 ms, **p90 485-1845 ms, p99 2.5-11 s**
  (survey :52).
- 2026-10-24, four 3-min A/B runs at the spot (J1, J0, J1, J0) and a 20-min J1 soak (bench log, `ab_1024/`):

  | Run | Build | Longest telemetry gap | Gaps > 1 s | Ping p99 | Longest ping pause |
  | --- | --- | --- | --- | --- | --- |
  | 1 | J1 | 0.29 s | 0 | 88 ms | 0.37 s |
  | 2 | J0 | 3.85 s | 10 | 2,398 ms | 6.06 s |
  | 3 | J1 | 1.10 s | 1 | 631 ms | 1.22 s |
  | 4 | J0 | 0.96 s | 0 | 187 ms | 1.04 s |
  | soak (20 min) | J1 | 1.28 s | 3 | 228 ms | 1.68 s |

  No telemetry gap was longer than the network's own ping pause: the Pico never held telemetry back. The network
  varied more between runs than the builds did.
- **Not yet measured:** the link with the ESP32-CAM streaming from the car (a second 2.4 GHz radio on a busy
  channel), and the heartbeat gap measured at the Pico, which is what the M3.T7 G0 rule needs
  (`watchdog_ms = max(300, ceil_to_100(p99) + 100)`). By ping p99 alone, run 3 would give 800 ms and run 2 "stop and
  ask" (> 1000).
- A `FORWARD_25` move at 0.15 m/s with 0.3 m/s² ramps takes about 2.2 s (computed), so a watchdog near p99 will trip
  on some moves by construction, and C5 latches the episode on every `link_lost`.

### F3. The main loop blocks on the radio; the Pico is not CPU-bound.

- Each cyw43 send waits up to 1 s for the chip's credits (`safety.h:47-50`; cyw43_ll.c), and a reliable
  `rcl_publish` waits up to 1000 ms. Measured worst main-loop passes: 0.60 s (J1 soak, inside the executor's receive
  call during an agent silence), 0.61 s while driving (a send), 2.2 s (J0, a radio query and a publish in driver
  timeouts).
- The CPU is busy about 12 % of the time: 94 passes per second, 1.4 ms of work in a typical 11.7 ms pass (the rest is
  the executor's planned 10 ms wait); publish 0.48 ms, IMU read 0.8 ms. The second core is unused. Flash 444-453 KB of
  4 MB (about half of it is the Wi-Fi chip's firmware image, bench :878), static RAM 82-83 KB of 520 KB (bench log, "Is the Pico
  CPU-bound?").
- **Consequence:** a control loop run from the main loop (as the instructor's PID node does, and as M3.T2's 10 ms tick
  assumed) can freeze for 0.6 s or more with the wheels on their last duty. Run the PID and the move executor on
  core 1 or from a hardware-timer interrupt, with one owner of the PWM outputs.

### F4. Session and watchdog rules that sound safe made the link worse.

- **A short hardware watchdog reboots a healthy parked car.** Build G.1 raised the parked watchdog to 8 s after
  2-3 s passes (sends waiting for credits) rebooted a parked car twice, each costing 20-34 s offline
  (`safety.h:47-51`). Builds since run 2 s while driving, 8 s parked, 16 s while (re)connecting; the motors never
  depend on it (the 600 ms deadman stops them).
- **A quick session rebuild amplifies stalls.** Build I rebuilt the micro-ROS session after 4 s without an answer
  and on every Wi-Fi rejoin; on 2026-10-23 that turned about 1.4 s of real delivery stall into 9.4 s of silence plus
  a disarm (survey :57-68; `pico_odometry.c:195-200`).
- **J1's session tolerance works on the bench** (bench log, 2026-10-24): agent paused 10 s, the Pico disarmed at
  3.0 s and kept the session; agent restarted, the Pico rebuilt its session 7.7 s after the agent came back, with no
  reboot and no Wi-Fi rejoin. So S11's "reboot the Pico after any agent restart" is no longer needed with J1.
- J1's rules: quiet from 1.5 s of agent silence, motors stopped and disarmed (re-arm needed) from 3 s, the session
  rebuilt only after 20 s, on an IP change, or when two "unknown client" pongs prove the agent restarted; a lost
  Wi-Fi link waits for the wheels to stop before any blocking leave or join.

### F5. Roaming firmware stages and their status (2026-10-24).

| Stage | What it does | Status |
| --- | --- | --- |
| J0 | observe only (event tap, read-backs), Build I behaviour | built, tested |
| J1 | session tolerance, pinned to the office node | bench T1/T2 and floor A/B passed; 20-min soak clean; **now the fallback** (`buildJ1_9849874a`) |
| J2 | the chip's roam engine on for emergencies (below -78 dBm, beacon loss, kicks), host picks the node at each join | **the car's firmware since 2026-10-24** (`buildJ2_b4298742`): five review rounds (16, 11, 4, 4, 2 findings fixed); T1 boot check, a 3-min floor check and a 20-min floor soak passed the adoption rule (no gap longer than the network's own ping pause, 0 rebuilds or reboots, 0 roams, 0.15 % lost); its own recovery tests (tin, node loss, scans while driving) not yet run |
| J3 | parked host roaming "whenever it helps" | design only |
| J4 | accept eero's BSS-transition requests | optional, design only |

Expectation (a judgement, not data): at the floor spot J1, J2 and J3 should look alike, because the stalls hit the
whole mesh; J2/J3 should be much better when a node dies or the car moves between rooms. J2 was kept without a full
A-B-A-B (Xiaohui's choice, once its soak was clean); M3.T22 measures the link **with the car driving and the camera
streaming** and records which build ran. The J2 soak was also the first time J1's 3 s disarm fired at the spot (a 7 s
agent silence): the car disarmed and kept its session, as designed.

### F6. Motors and encoders today.

- History: 3 of the 4 motors of the original model went stiff, weak or jammed within days (right #1, right #2 on
  2026-10-22, and the original left); the left was replaced on 2026-10-22 (same model); right #3 is a different model
  (blue NULLLAB 1:90 TT "Low Noise & Hybrid Gear"), fitted 2026-10-23 (bench log :612-705).
- Lifted test of the current pair (`m30a`, 2026-10-23): both wheels turn as commanded; at the same duty the right is
  1-5 % slower than the left; both lose 7-8 % when driven together (shared AA pack).
- **First floor runs of the current pair** (`m32a`-`m32c`, 2026-10-24, Build J2; bench log, last entry): right #3 runs
  every floor segment, about 4 % slower than the left alone at duty 0.71. Driving straight, the car **veers right 4-5°
  per 34 cm forward** (the right wheel 2.5-3 % slower, encoders agreeing with the compass, so no slip) and goes almost
  straight in reverse. Turning in place, a commanded 45°/s gave **about 160°/s** and 23°/s gave about 145°/s: the old
  duty map underestimates these motors, and the lowest duty this firmware can command moves each wheel about
  0.17 m/s.
- Encoders: **left = GP16/GP17, right = GP18/GP19** (`encoders.h:9-15`), the opposite of the plan's pin table
  (M3 §0.6). 4,320 nominal counts per wheel turn. The left encoder's two channels are not a clean quadrature pair, so
  the firmware counts its edges (edge mode, `encoders.h:20-30`). **On the floor its scale agrees with the compass within
  0.5° in six one-wheel pivots (about 0.3 %, `m32a`).** The right decodes plain x4, losing about 1.6 % at duty 0.96;
  in pivots it reads 0.8-1.7 % more turn than the compass (likely tyre scrub: in in-place turns both encoders agree
  within 0.25-0.9 %).
- **No hand-turning of the wheels since 2026-10-23 (Xiaohui).** Counts per turn and encoder signs come from powered
  stand runs (M3.T3: a filmed tyre flag) and the floor cross-check against the compass (M3.T24), never from turning
  wheels by hand.

### F7. PWM frequency.

The instructor's 1.2 kHz is in use (`tb6612.c:37-48`). A 20 kHz trial on 2026-10-17 cut Wi-Fi losses during pivots,
but one wheel stayed stuck in pivots with the smoother current (old motors, sagging pack), so it was reverted. The
plan's default (20 kHz, M3.T4) needs a re-test on the current motors, and the duty-to-speed curve must be measured
after the frequency is chosen, because the frequency changes it.

### F8. Speeds the project needs against speeds measured.

- A 45°/s pivot (C0 `turn_rate_dps`) needs about 0.05 m/s at each wheel (ω x half the 0.1335 m track).
- Lowest measured so far: about 0.17 m/s per wheel on the floor at duty 0.53 in an in-place turn (`m32c`, 2026-10-24;
  the turn ran at about 145°/s for a commanded 23°/s); about 0.166 m/s lifted at duty 0.48 (`m30a`); 0.136 m/s (old right #2) and 0.159 m/s (new
  left, edge-counted) on the floor at duty 0.56 (`m24_cal`, bench :507-508). Below the old map's minimum duty 0.46 the motors stall. **Whether the current motors can
  hold 0.05 m/s at all is unknown**; M3.T21 measures it.

### F9. The Module 7 PID exists only in the simulator.

- `sim/sim_pico_pid.py` is a Python port of the instructor's `pid.c` and `wheel_control.c`, run against a motor model
  of the OLD pair whose numbers were chosen, not measured (`discussions/module7/README.md:16-24`).
- Final gains Kp 40, Ki 100, Kd 0, feed-forward 0.26/0.45, ramp on. Results in Gazebo: the end heading of a straight
  fell from 3.7° to 0.4°; the square did not improve (6.4 vs 6.2 cm) (`README.md:54-58`).
- The page itself says the gains are only a starting point (`module7-pid.html:183-190`). In the plan's units (duty
  per m/s) Kp 40 is about 22 against M3.T4's starting `KP = 0.5 / k_v` of about 1.3-3.0, so 7-17 times higher
  (computed; an inference that depends on the model's effort scale). Use the tuning **procedure** from Module 7, not
  its numbers.
- The instructor's node runs `wheel_control_update` in the main loop after each `spin_some` (pid-source-files.html,
  the main loop), which F3 rules out on this link.

### F10. micro-ROS entity limits.

The Module 5 library (used by every build so far) allows 1 node, 3 publishers, 2 subscriptions, MTU 1024
(`assignments/assignment5/module-5-imu-tilt-control/micro-ros-builder/colcon.meta:45-47`). J1 uses 3 + 1; the
instructor's PID node needs 3 + 2; C2 plus the diagnostics topics need 6 publishers and 4 subscriptions. A library
rebuild (M3.T14) is required either way.

### F11. Safety gaps in the current firmware (relevant before the project too).

It boots armed after a normal power-up; the arm marker (a zero `Twist` with `angular.x = 1.0`, which any publisher
can send) is required only after an abnormal boot, a reconnect or a 3 s silence. The motor pins are driven low only
after `stdio_init_all()`, a 1.5 s sleep and `diag_init()` (`pico_odometry.c:679-682`), and the watchdog can reboot
it with the battery on. **The STBY pull-down (S5) is not fitted.** M3.T1 fits it; it protects the Assignment 7
firmware as well.

## 3. Is the wheel PID useful for BeaconMind?

**Yes, as the inner loop of the move executor; it is not what makes a move land in the right place.** The agent sends
one of five bounded moves (C2); the Pico runs it with three nested layers:

| Layer | Controls | What it buys | Task |
| --- | --- | --- | --- |
| Distance | stop at an encoder-count target, trapezoidal profile | the 25 cm comes out near 25 cm | M3.T6 |
| Heading | IMU yaw: turns closed to 1°, small corrections on straights | turns come out at 30°, straights stay straight | M3.T6 |
| Wheel speed (the PID) | each wheel follows the profile's speed | equal wheels, the same move time every time, a profile the stall check can compare against | M3.T4, M3.T21 |

Why it helps on this car:
- **The motors are not a matched pair and keep changing**: two different models, one replaced after another (F6).
  Open loop, a single duty map makes the car curve and the curve changes with each motor. In the simulator the PID cut
  the end heading of a straight by about eight times (F9).
- **Battery sag:** open loop, the same duty gives a different speed as the AA pack drains (both wheels lose 7-8 %
  when driven together, F6). The PID holds the planned speed.
- **The stall check** (C0 `stall_*`: below 50 % of the profile for 200 ms after a 200 ms grace) needs a speed profile
  the wheels actually follow, or every slow start looks like a stall.
- **Slow pivots** (about 0.05 m/s per wheel, F8) are far below what open loop has held; feed-forward plus an integral
  term is the usual way to hold a low speed.

Where it will not help:
- The outer loops matter more for position: in the simulator the square did not improve with the PID (F9).
- It cannot make a motor turn slower than its friction allows. If the current motors cannot hold 0.05 m/s, options
  are a faster turn rate (a C0 change, Xiaohui's call), pulsed drive, or accepting the IMU-closed turn's overshoot.

How to build it:
- Start from the instructor's `pid.c` / `wheel_control.c` (reuse allowed) or the plan's `logic/pid.c` (M3.T4 step 8);
  keep conditional integration (anti-windup), per-wheel feed-forward from the measured curve, and a speed filter.
- Run it at 100 Hz on core 1 or from a repeating-timer interrupt, never from the main loop (F3). One owner writes the
  PWM; the main loop only posts setpoints and reads state.
- Tune on the real car: on the stand first (M3.T21), across the battery range, at the speeds the moves use
  (0.05-0.15 m/s); then re-check on the floor after the wheels-down gate (M3.T24).
- **Priority if time runs short:** safety and the move executor first, then the IMU heading loop, then the wheel PID.
  Per-wheel feed-forward plus count stops plus IMU-closed turns gets most of the way without a tuned PID.

## 4. Recommendations

**Reuse** (keep each disclosure; add a line "Copied from `assignments/assignment7/...` on <date>"):
- `safety.c/.h` with its 2 / 8 / 16 s watchdog pattern (not a flat 1000 ms), `diag.c/.h`.
- `wifi_link.c/.h`, `wifi_events.c/.h` with `cyw43_hook.h` (pinned to cyw43-driver v1.1.1; cite the driver's format
  strings), and `wifi_roam.c/.h` once J2 has won its floor A/B.
- J1's session supervisor, moved from `pico_odometry.c` into its own file (`session.c`).
- The instructor's `tb6612.c`, `encoders.c` (plus the car's edge mode), `bno055.c` (add gyro z, linear acceleration
  and calibration status for C2's `/pico/imu`), `picow_udp_transport.c` (plus J1's pong-status parsing),
  `CMakeLists.txt`, `lwipopts.h`, and `pid.c` / `wheel_control.c` as the PID's start. Each keeps a comment naming the
  instructor file.
- The bench tools (`tools/imu_bench.sh`, `wheel_ratio.py`, `diag_run.py`, `wifi_survey/capture/link_listen.py`) as
  instruments: they measure the car now, before the project firmware exists.

**Add new:** everything in C2 (move executor and results, arm, `/estop` with the latch, the heartbeat watchdog, the
boot id, bump detection, the design's stall check, the 0.15 m/s cap), a 6/6 micro-ROS library, host unit tests, the
100 Hz PID on core 1 or a timer, and `/pico/diag` with heartbeat-gap statistics.

**Order:**
1. Finish J2: floor A/B against J1; pick one (Assignment 7 work).
2. M3.T1: fit the STBY pull-down (protects the current firmware too).
3. M3.T22: link baseline with the camera streaming, using the Assignment 7 firmware as the instrument. It tells
   early whether the 0.2 s STOP and a 500 ms watchdog are reachable.
4. M3.T14 (build chain), M3.T23 (the copied link and safety layer), then M3.T2.
5. M3.T3, M3.T4 (curve after choosing the PWM frequency), M3.T21 (PID tuning on the stand), M3.T5, M3.T6, M3.T7,
   then M3.T24 (floor re-tune) before M3.T8 (UMBmark).

## 5. Plan changes made on 2026-10-24 (Xiaohui's request: "modify the task plan accordingly ... add tasks such as tuning PID")

Recorded in `plan/REVIEW.md` Part D, with the files and sections changed. In short:
- README L11: the instructor's code may be reused, with a source comment and the AI disclosure.
- README §7 S11 and M3.T2: the Pico's session supervisor (J1) replaces "reboot the Pico after any agent restart"
  and "reboot after 3 failed pings"; the hardware watchdog follows the 2 / 8 / 16 s pattern; the 200 ms rule is
  replaced by "control loops off the main loop".
- M3 §0.6: encoder sides corrected, current motors and the Assignment 7 firmware recorded.
- M3.T3: counts per turn and signs from powered stand runs (filmed flag), not hand turns; the IMU cross-check is
  M3.T24.
- M3.T4: the PID runs on core 1 or a timer; the PWM frequency is chosen before the curve is measured; the bench
  tuning step moves to M3.T21.
- New tasks: **M3.T21** wheel-speed PID tuning on the real car; **M3.T22** link baseline with the camera streaming;
  **M3.T23** port the Assignment 7 link and safety layer into the project firmware; **M3.T24** floor re-tune of
  the wheel PID and the left encoder's scale (after the wheels-down gate, before UMBmark).
- New open decision: whether a `link_lost` stop that ends inside the move's watchdog margin should still latch the
  episode (C5) on this link.

## 6. Open items

| # | Open item | Test | Owner task |
| --- | --- | --- | --- |
| O1 | Heartbeat-gap p99 at the Pico with the camera streaming, parked and driving | M3.T22 | M3.T22 |
| O2 | Whether J2 (or J3) beats J1 on the floor while driving | floor A/B, Assignment 7 | M3.T22 (uses the winner) |
| O3 | Whether the current motors hold 0.05 m/s per wheel (stand, then floor); open loop the lowest commandable duty gave about 0.17 m/s (`m32c`) | step responses at 0.05 m/s with raw duty below 0.46 | M3.T21, M3.T24 |
| O4 | The left encoder's scale in edge mode: **within 0.3 % of the compass in floor pivots (`m32a`, 2026-10-24)**; re-check with the project firmware | powered floor runs against the IMU | M3.T24 (M3.T3 measures it wheels up) |
| O5 | PWM frequency (1.2 kHz in use, 20 kHz planned) with the current motors | A/B of starts and pivots, Wi-Fi losses logged | M3.T4 |
| O6 | Right #3 under floor load and over time (3 of 4 old-model motors failed); first floor runs clean (`m32a`-`m32c`) | longer floor runs with logged cut-offs | M3.T24 |

## AI disclosure

Written by Claude Opus 5.5 via Claude Code (2026-10-24) from the session's logs and sources listed in section 0;
the facts were cross-checked by two read-only multi-agent checks with a critic. Xiaohui Chen ran the car, made the
decisions recorded here (instructor-code reuse; the plan changes) and is responsible for reviewing this note.
