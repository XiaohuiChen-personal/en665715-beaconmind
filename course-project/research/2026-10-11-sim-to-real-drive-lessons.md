# Sim-to-real drive lessons from the Module 6 discussion (2026-10-11)

**Read this before M3.T3 (encoders), M3.T4 (motor direction mapping, wheel-speed PID, speed cap), M3.T8 (UMBmark)
and before giving the Isaac twin (M2.T4) an actuator model.** It records what happened when the same timed
velocity commands were sent to a Gazebo model of this car and to the car itself: which assumptions were wrong,
the two calibration attempts (one failed, one with an arithmetic slip), and what is still open. It is a starting
point for the project's calibration, not a calibration: every number below is open-loop, from short moves, on one
floor, on one battery charge.

Owner: Xiaohui Chen. Written by Claude Opus 5.5 via Claude Code from the session's logs; Xiaohui ran the car,
judged the wheel tests and took the tape measurements.

## 0. Sources (all in this repo)

| What | Where |
| --- | --- |
| Explainer page with every table, the filmed take and the phone clip | `discussions/module6/module6-sim-to-real.html` (built by `discussions/module6/build_page.py`) |
| Agent event logs (every rehearsal, real run, tape reading) | `assignments/assignment6/module-6-gazebo-sim/sim-to-real/logs/measure.jsonl`, `film.jsonl`, `compare-*.jsonl`, `gate-retest.jsonl` |
| Student observations (tape, drift) | `discussions/module6/evidence/measure-notes.txt`, `discussions/module6/data/tape.json` |
| IMU sign and rest-drift checks | `discussions/module6/evidence/imu-sign-check.txt`, `imu-rest-drift.txt` |
| Wheel-direction tests | `discussions/module6/evidence/wheel-test-after-remap.txt` |
| Firmware as flashed (instructor's sim-to-real drive firmware + my two changes) | `assignments/assignment6/module-6-gazebo-sim/sim-to-real/pico2w_led/drive_control.c` (the comment block holds the calibration arithmetic); UF2s on the Spark in `discussions/module6/firmware/` |
| Phone clip of the filmed route and its frame analysis | `discussions/module6/video/phone-take.mp4`; page section 2 |
| Module 5 full-power run length (estimate) | `discussions/module5/DESIGN.md` (§1 floor notes) |
| Measured car dimensions (track, tyre width) | `assignments/assignment6/measurements.csv`; URDF `course-project/ros2_ws/src/beaconmind_description/` |
| Pack voltage history (last metered 5.7–5.9 V at the driver, 2026-10-01) and the pulse test | `reference/hardware/car-build-notes.md`; `assignments/assignment5/evidence/diagnostics/pintest-pulse-results.txt` |
| Gate thresholds (agent and instructor) | `assignments/assignment6/module-6-gazebo-sim/sim-to-real/sim2real_agent.py` (`DRIVE_SHORTFALL`, `DRIVE_SLIP`, `END_HEADING_TOLERANCE`), `robot_motion.py` (`possibly_blocked`) |
| Gate retest (contact case) and tool-restriction check | `logs/gate-retest.jsonl`, `logs/tools-check.jsonl`; `discussions/module6/evidence/gate-retest-summary.txt`, `tools-restricted-check.txt` |

The firmware is the instructor's Module 6 "sim-to-real" image: `/pico/cmd_vel` (`Twist`) → differential drive →
open-loop PWM on the TB6612FNG, heading from the BNO055 in IMU mode on `/pico/imu/heading`, a 0.5 s command
timeout. **It never reads the encoders.** The Gazebo side is the Module 6 lab world with the step-10 URDF built
from my measurements (`beaconmind_description`), so geometry matched; only actuation and feedback differed.

## 1. Facts established (with evidence)

### F1. Motor channel A drives the RIGHT wheel (camera end = front). This contradicts CONTEXT.md and wiring-plan.md.

- With the instructor's `tb6612.c` (same direction-pin logic as Module 5's: channel A driven inverted relative to B), "forward" rolled the car toward the
  **drive-wheel end**, camera trailing (wheel test, Xiaohui, 2026-10-11; same as the Module 5 floor runs).
- The fix that worked: in `drive_control.c`, `tb6612_set(-right_duty, -left_duty)` (each side's speed goes to the
  other channel, sign flipped). After it, the wheel test gave forward = toward the camera and, on "turn left",
  right wheel forward, left wheel backward.
- Independent check that does not rely on reading wheels: turning the car 90° left by hand raised
  `/pico/imu/heading` from 0.9° to 84.7° (CCW positive confirmed), and with the remap the commanded left turns that
  are unambiguous in the logs raised the heading: +143°, +142° (instructor constants) and +160° (calibration 1)
  (`measure.jsonl`, raw `heading_change_deg`). The calibration-2 and filmed U-turns are **not** usable as proof on
  their own: near 180° the heading wraps (they logged −171°, −173°, −179°) and the agent reports them as the angle
  nearest the command (+189°, +187°, +181°). Their direction is confirmed separately: the duty constants cannot flip
  a turn's sign, and in the phone clip of the filmed U-turn the car's front sweeps from the lane direction through
  the direction away from the camera (the car's left, +y) to facing back, i.e. counterclockwise.
  A swap-and-negate remap can only give correct left turns if channel A is physically the right wheel.
- **Consequence for the project:** `CONTEXT.md` (Hardware state: "Channel A = left wheel, B = right wheel") and
  `reference/hardware/wiring-plan.md` §4 ("channel A = left wheel") describe the intended wiring, not the car.
  The encoder pins (`GP16/17` "right", `GP18/19` "left") are therefore **suspect too**: M3.T3 must map each encoder
  to a wheel by turning one wheel by hand, not from the plan.

### F2. The firmware's speed-to-PWM model was wrong by a factor of two on this car.

`drive_control.c` maps a wheel speed `v` to a duty: `duty = MIN_DUTY + (1 − MIN_DUTY) · v / MAX_WHEEL_SPEED_MPS`.
Instructor values: `MIN_DUTY 0.40`, `MAX_WHEEL_SPEED_MPS 0.60`, `WHEEL_SEPARATION_M 0.127`.

| Setting | Command | Duty sent | Real result | Gazebo | Real average wheel speed |
| --- | --- | --- | --- | --- | --- |
| Instructor constants | straight 0.15 m/s × 2.67 s (40 cm) | 0.550 | **20 cm** (tape); route leg 20 cm → ~10 cm | 40.3 cm | 0.075 m/s |
| Instructor constants | turn 1.0 rad/s × 3.14 s (180°) | 0.464 | **143°** (IMU) | 181.6° | 0.053 m/s (b = 0.134 m) |
| Calibration 1 (MIN 0.25, MAX 0.19, b 0.134) | straight 0.15 m/s × 2.67 s | 0.842 | **26 cm** | 40.2 cm | 0.097 m/s |
| Calibration 1 | turn 1.0 rad/s × 3.14 s | 0.515 | **160°** | 181.5° | 0.059 m/s |
| Calibration 2 (MIN 0.36, MAX 0.20, b 0.134) | straight 0.08 m/s × 5.00 s (40 cm) | 0.616 | **≈40 cm** | 40.3 cm | ≈0.080 m/s |
| Calibration 2 | turn 1.0 rad/s × 3.14 s | 0.574 | **189°** (logged −171°, unwrapped; see F1) | 181.7° | 0.070 m/s |

Gazebo's DiffDrive sets wheel velocity directly (an ideal actuator); in every unobstructed rehearsal it landed within ~0.3 cm (0.32 cm max)
and 2° of the command. The real car has a dead band, load-dependent speed and battery sag.

### F3. Straight driving and turning in place load the motors differently, so one line cannot calibrate both.

Calibration 1 fitted one straight line through a straight point and a turn point and predicted 40 cm and 177°;
the car did 26 cm and 160°. Fitted separately, two points each:
`straight v = 0.075 + 0.077 · (duty − 0.550)`, `turn v = 0.053 + 0.120 · (duty − 0.464)`. At the same duty, a
wheel turns slower when the car pivots in place (tyre and caster scrub).

### F4. Calibration 2 has a documented arithmetic slip; its consistent fit is MIN_DUTY 0.39, MAX 0.215.

Solving both lines for 0.08 m/s straight (duty 0.615) and a 1.0 rad/s turn (0.067 m/s per wheel, duty 0.578)
gives `(1 − MIN)/MAX = 2.85`, `MIN_DUTY = 0.39`, `MAX = 0.215`. The flashed 0.36/0.20 came from a hand
calculation that could not be reproduced afterwards (0.36/0.20 implies a turn duty of ~0.574, i.e. a turn slope of ~0.125
instead of 0.120). They produced duty 0.616 / 0.574 and measured 40 cm / 189°. **Lesson: compute calibration constants with
a script from the logged runs, and log the script's output, never by hand in a session.**

### F5. Short-move averages understate steady-state speed.

The speeds in F2 are averages over 2.7–5 s moves from standstill, so spin-up is inside them. A line through the
two straight points extrapolates to ~0.11 m/s at full power, but the Module 5 floor runs (10 s at full PWM)
covered roughly 1.5–2 m (Xiaohui's estimate, not taped; `discussions/module5/DESIGN.md`), i.e. ~0.15–0.2 m/s once
up to speed. The filmed route's 2.5 s leg also looked short relative to its 5 s leg. **Calibrate on the move
lengths the agent will actually command, or measure speed with the encoders after spin-up.**

### F6. The car veers left on every straight move, by an amount that is not constant.

IMU heading change during straight moves: +12° (taped 20 cm in 2.7 s, duty 0.55), +14° (route leg 1 at instructor
constants, ~20 cm in 2.7 s), +7° (route leg 2 at instructor constants, ~10 cm in 1.33 s), +1° (taped 26 cm in 2.7 s,
duty 0.84), +30° (taped ≈40 cm in 5 s, duty 0.62), +28° and +24° (commanded 40 cm in 5 s), +14° and +16° (commanded
20 cm in 2.5 s). Open loop with two unmatched gearmotors, and the firmware sends both wheels the same duty. Three duty
settings and a handful of moves cannot separate power level, duration and the swivel caster's starting angle. A fixed
per-wheel trim is not expected to cancel it. **Counter-evidence to resolve:** the 2026-10-01 unloaded pulse test found
motor A ~12–17 % slower (mean ~15 %, runs after the driver board was seated) (`assignments/assignment5/evidence/diagnostics/pintest-pulse-results.txt`); with A = the right
wheel (F1) that predicts a RIGHT veer, yet every move veered left. So load, the caster, or a wrong encoder-to-motor
attribution in that test is involved; M3.T3 should measure per-wheel encoder speed at equal duty.

### F7. End position can match while heading does not.

The filmed route (forward 40 cm, U-turn, forward 20 cm) ended ≈21 cm (±3 cm) past the start and on the start line,
close to Gazebo's (20, 0) cm, but facing ~40° off (IMU total +220°, with the U-turn's logged −179° unwrapped to +181°; see F1): the leg-1 veer and the U-turn that started from it
cancelled in position. **Any evaluation of real runs must report heading error next to position error** (relevant
to M4's ATE-based metrics and to the sim-to-real gap: M4.T13 replay → family F7 computed in M4.T16).

### F8. Wheel separation.

Firmware 0.134 m (inner gap 107 mm + tyre width 27 mm); URDF 133.5 mm (mean of outer 160 and inner 107 mm track).
Same within the 1 mm the two measurements agree. The course robot's 0.127 m would make every turn ~5 % short.

### F9. IMU behaviour (BNO055, IMU mode, via this firmware).

Heading is CCW positive after the firmware's sign flip (hand test). It held 34.1° for 20 s at rest (no drift seen).
It does **not** reset to 0 when only the Pico reboots (the BNO055 stays powered), so always use heading changes.

### F10. Infrastructure traps met on the way.

- The instructor's `docker compose -f docker-compose.yml -f sim-to-real/docker-compose.real-robot.yml` silently
  drops `docker-compose.override.yml`; list all three files when the override matters.
- Each Pico reboot under one micro-ROS Agent left a stale `/pico2w_drive` node (six after a few reflashes);
  restart the Agent, then power-cycle the Pico, before anything that counts nodes or films the graph.
- `ros2 topic echo … | awk` buffers its output and loses it on timeout; use a small rclpy script with `flush=True`.
- ROSA with `ros_version=2` silently adds its built-in ROS 2 tools; `ros2_param_set` and `ros2_service_call` put model
  text into a `shell=True` command, so a model could inject `; ros2 topic pub …` and bypass any approval gate. ROSA's
  `blacklist` does not remove tools. Any project agent built on ROSA must replace `_get_tools` (as
  `sim2real_agent.py` does) or otherwise prove the model's tool list.
- The instructor's `possibly_blocked` (true distance ≥ 70 % of the command and wheel-odometry slip ≤ 10 cm) passed
  "drive 100 cm at 0.2 m/s", which hit the box at 0.91 m (slip 9.3 cm). The agent tightens it to 10 % + 2 cm short and
  3 cm slip (`logs/gate-retest.jsonl`); the project's contact detection (M3.T15) should be at least
  that strict.

## 2. Starting point for the project's calibration (M3.T3, M3.T4, M3.T8)

1. **Direction mapping first.** Do not take channel/encoder sides from the wiring plan. At the start of M3.T3 (the
   plan runs it before M3.T4): wheels up, command each channel alone and record which wheel turns and which way, and
   hand-turn each wheel to map its encoder. Then M3.T4 (settles OD10) confirms forward = +x on the floor and, with the
   IMU, that a commanded left turn raises the heading — using turns well away from 180° so the heading cannot wrap. Update `CONTEXT.md` and `wiring-plan.md` §4 with
   the result. The Module 6 remap (`tb6612_set(-right, -left)`) is the expected answer.
2. **Encoders before any speed model (M3.T3).** Per-wheel counts per revolution and sign, then measure each
   wheel's steady speed against duty over the range the agent will command (e.g. duties 0.4–1.0 in steps, wheels
   down, straight and pivoting separately, pack voltage recorded each session).
3. **Closed loop (M3.T4).** The veer (F6) and the load dependence (F3, F5) are what a per-wheel speed PID on
   the encoders removes; use the F2/F3 lines only as the feed-forward term and as a sanity check.
4. **UMBmark (M3.T8)** for the systematic errors that remain (unequal wheel diameters, effective track width).
5. **Twin actuator model.** Gazebo's ideal DiffDrive hid all of this. If the Isaac twin should predict the
   real car, give it the measured speed cap, acceleration and dead band rather than ideal velocity control,
   or report the sim-to-real gap as part of the result.

## 3. Open items

| # | Open item | Suggested test | Owner task |
| --- | --- | --- | --- |
| O1 | Cause and size of the left veer; whether it depends on duty, duration, battery or caster angle | encoder speeds per wheel at equal duty; repeat 40 cm runs with the caster pre-aligned vs sideways | M3.T3/T4 |
| O2 | Channel A = right wheel: update the wiring documents; which encoder pins belong to which wheel | wheels-up single-channel test + hand-turned encoder counts | M3.T3/T4 |
| O3 | Steady-state speed vs duty above 0.84 and at full power; battery dependence | encoder speed after spin-up; pack voltage at the driver before each session (last metered 5.7–5.9 V, before Module 6) | M3.T3/T4 |
| O4 | Whether the in-place turn also translates the car (pivot not at the axle midpoint) | mark the axle midpoint, turn 360°, measure the offset | M3.T8 |
| O5 | The consistent calibration-2 constants (0.39 / 0.215) are untested | reflash only if the open-loop drive firmware is kept for anything | — |
| O6 | Short-move losses (spin-up, latency): the 2.5 s leg looked short | encoder log of a 2.5 s and a 5 s move at the same command | M3.T3 |
