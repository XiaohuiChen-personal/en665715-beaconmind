# M3.T9 — the real-car environment backend (work list 2.9), 2026-11-18

Status: **software written and tested in fake mode (simulated car, fake camera, fake detector) and driven by the
closed-loop harness; not yet run with the real car or the real camera.** Nothing in this task was published on the
real car's ROS graph. The steps for Xiaohui are at the end.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote the backend, the camera client, the tests and this
note. Xiaohui Chen runs the car.

## What was built

| File | What |
| --- | --- |
| `beaconmind/src/beaconmind/car/backend.py` | `RealCarEnv` (the environment), `as_observation`, `fake_env` (fake mode) |
| `beaconmind/src/beaconmind/car/camera.py` | `HttpCamera` (frames over HTTP, every frame saved), `perception_detector` (adapter to `beaconmind.perception.tags`), `FakeCamera`, `fake_detector` |
| `beaconmind/src/beaconmind/car/link.py`, `ros_io.py` | the car link the backend drives: `SimLink` (simulated car) or `RosCarLink` (ROS 2) |
| `beaconmind/tests/test_car_backend.py` | 22 tests (21 on the Mac; the detector test needs OpenCV and runs in the container) |

## Interfaces found (step 1 of the task text) and what was adapted

The task text assumed a `RosEnv` from M2.T6/M2.T17, a `bm_pico_bridge` node, an `apriltag_ros` pipeline and an
overhead ground-truth camera. The re-scope (plan README §3.6) dropped the Isaac twin, the project firmware and the
overhead camera. What exists today, and what the backend therefore implements:

- **The environment protocol** is the one `beaconmind/src/beaconmind/harness/closed_loop.py` states (written today
  for work list 4.1): `env.source`, `env.describe()`, `env.reset(seed) -> sense`, `env.step(action) -> sense`,
  `env.truth()`. A sense is `{"odometry": {forward_m, left_m, dtheta_deg} | None, "move": {"action", "result",
  "reason"} | None, "safety": {...}, "detections": [{det, id, range_m, bearing_deg, quality, _tag}]}`; these are the
  fields of a `kinsim_lite` raw step (`envs/kinsim_lite.py` `run_episode`), which the harness turns into the C3
  OBSERVATION with `kinsim_lite.as_observation`. `RealCarEnv` returns exactly these keys, plus `status`.
- **Odometry**: C1's function lives in `beaconmind/car/odometry.py` (`chord_c1`, `Odometer`); the test
  `test_arc_matches_the_c1_formula_and_compose_odometry` checks it against `geometry.compose_odometry`, the check
  C1 asks for. No `/odom` or `/imu/data` topics are published: nothing in the reduced scope consumes them.
- **Detections** come from `beaconmind.perception.tags` (`detect_tags` per frame, `fuse_frames` for the C3 rule,
  `to_observation_detections`, `to_internal_detections`), written in parallel today, on JPEG frames fetched over
  HTTP. No `apriltag_ros`, no `/camera/*` topics, no launch file.
- **Ground truth** on the car is tape (plan §3.6): `env.truth()` returns `None` on the real car and the simulated
  car's true pose in fake mode. `det_truth` is not assigned on the car (`_tag` is `None`).

## What one step does

1. `step(action)` builds the `bm.move/1` command (`car/moves.py` `make_move`: limits from `configs/dv.json`;
   `BACKWARD_10` covers the lesser of 0.10 m and what the previous forward move achieved, and is refused with
   `executor: no forward move before` when there was none, as the simulators do) and runs it through the executor
   (`link.execute`). The executor returns only after the car has settled (see `../M3.T6/README.md`).
2. It waits `obs_settle_s` (0.3 s), takes `obs_frames` (5) frames, runs the detector; `fuse_frames` keeps tags seen
   in at least `obs_min_frames` (3) frames, with the median position and quality = frames seen / 5 (all three
   numbers from `configs/dv.json`; "proposed default (M1.T8 confirms)").
3. Odometry is the odometer's change since the previous sensing, in the robot frame at that sensing, so the coast
   after the stop command and any motion between moves are inside it. Handed out rounded as C1 says (0.01 m,
   0.1 degree); the unrounded values go to `steps.jsonl`.
4. `status` carries what C3 puts in `status` / `error` / `sensors` / `odometry.quality`: camera `ok` / `stale`
   (fewer than 5 frames) / `down` (none); IMU; Pico `armed` / `disarmed`; a restart of the car gives
   `odometry: null` and `status: error` (C3); `odometry_quality: slip_suspected` when the wheels' heading change and
   the gyro's differ by more than `slip_yaw_disagree_deg` (10 degrees). `backend.as_observation(env, sense, obs)`
   puts these into the OBSERVATION the harness built.
5. Every step is appended to `steps.jsonl` in the log folder: the sense, the command, the `bm.move_result/1`
   record, the executor's details, the frame records, what each frame showed, `detections_internal`, the car's
   state and the dead-reckoned pose.

**Safety flags** (`forward_allowed`; the harness's validator takes them from the environment): the stricter of
(1) the tags in view within 45 degrees of straight ahead, range x cos(bearing) (C5 item 3b), and (2) when the room's
world file and the taped start pose are given, the distance to the driving area's edge ahead of the dead-reckoned
pose (`envs/kinsim_room.py` `wall_distance_ahead`, the rule the room simulator applies to the true pose). A forward
move is offered when it leaves `forward_wall_limit_m` (0.35 m). With neither estimate the wall distance is unknown:
`unknown_wall="allow"` (default) or `"block"`. Turns are not offered when a detected tag is inside the sweep radius
plus 5 cm. **Blind zone:** the perception task reports that a wall tag straight ahead is whole in the picture only from 0.74 m from the axle midpoint, so estimate (1) says nothing exactly when the car is closest to a wall; inside that distance only estimate (2), or `unknown_wall="block"`, keeps a forward move from being offered. **Not implemented:** C5 items 3a (tag-plane estimate), 3c (mapped beacons) and 3d (a tag that dropped
out). The dead-reckoned pose drifts over an episode, so estimate (2) weakens with distance driven; the operator at
the switch and the stall detection are the backstop.

## Tests

Mac (Python 3.13), 2026-11-18: `cd course-project/beaconmind && PYTHONPATH=src python3 -m pytest -q
tests/test_car_backend.py` -> `21 passed, 1 skipped` (`../M3.T6/pytest-mac.txt`). Container on the Spark (Python
3.10, OpenCV): all 22 pass (`../M3.T6/pytest-container.txt`).

- `test_real_detector_on_a_rendered_frame` (container): `camera.perception_detector` on a JPEG of a frame rendered
  by the perception module's synthesiser with the calibrated camera, through `RealCarEnv`: two tags drawn at
  (1.2 m, +8 degrees) and (1.8 m, -12 degrees) come back at those values over five frames.

- `test_the_harness_drives_the_backend`: `harness/closed_loop.py` `run_episode` with the coded procedure B2 drives
  the fake car for 8 steps through this backend (moves executed by the executor on the simulated car, observations
  built by the harness), and every executed move's result validates against `bm.move_result-1`.
- `test_the_observation_validates_as_contract_c3`: the OBSERVATION built from a sense validates against
  `bm.observation-1` with `source: "real"`.
- `test_moves_return_measured_odometry`, `test_odometry_feeds_the_agents_tool_like_the_simulators`: the odometry
  handed out matches the simulated car's true motion within the rounding, and composing it with the agent's tool
  tracks the true pose within 2 cm over five moves.
- camera down, car restart, stall, slip, BACKWARD_10 rule, the wall check from tags and from the room.

## For the harness

Since the harness's change of the same night it reads `sense["status"]` itself, stores a `None` truth as it is,
and refuses a resume unless the environment sets `deterministic_replay`: `fake_env()` sets it (the simulated car
replays exactly); `RealCarEnv` never has it, because a resume would re-send every logged move to the car. Run real
episodes with `--watch-latch course-project/data/LATCH`. The two notes below are kept for the record.

### Earlier notes (two small things it needed for `source: "real"`)

1. `env.truth()` is `None` on the real car. `harness/closed_loop.py` `to_runlog` reads `r["truth"]["x_m"]`; for a
   real episode `gt_pose_map` must be `null` (C9.1 allows it).
2. `kinsim_lite.as_observation` writes `sensors` all `ok` and `status: "ok"`. For the car, call
   `beaconmind.car.backend.as_observation(env, sense, obs)` after it, or read `sense["status"]`.

## How to build the real environment (Spark, inside `beaconmind-ros`)

```python
from beaconmind.car import ros_io, camera, backend, movelog
from beaconmind.envs import kinsim_room as kr

session = movelog.active_session_dir()                     # the recorder's session (rule R2)
link = ros_io.RosCarLink()                                 # /pico/* on ROS_DOMAIN_ID 0
cam = camera.HttpCamera(camera.RELAY_URL, save_dir=session + "/frames_backend")
detect = camera.perception_detector(tag_size_m=0.16, tag_center_height_m=0.23)
scene = kr.room_scene("configs/arenas/<the measured world>.json", start_pose={...taped...})
env = backend.RealCarEnv(link, cam, detect, scene=scene, log_dir=session + "/backend", episode="ep01")
```

The recorder must run with `--camera off` then (the camera serves one client; `HttpCamera` saves every frame with
its request and response times and X-BM headers, as `tools/record_frames.py` does). The STOP program and the latch
work the same as for `car_move.py` (see `../M3.T13/README.md`).

## Procedure for Xiaohui (after the M3.T6 stand test and floor check have passed)

Car on the floor at a taped start, recorder running with `--camera off`, STOP program running, a hand on the motor
battery's switch (plan §3.6 hardware procedures).

1. One observation, no move: build the environment as above, `sense = env.reset(0)`.
   **Pass:** `sense["status"]["status"] == "ok"`, camera `ok`; 5 new files in the session's `frames_backend/`; with a
   wall tag in view, a detection whose range is within 5 cm of a tape reading from the axle midpoint.
2. `env.step("FORWARD_10")`, then tape the car's displacement.
   **Pass:** `move.result == "done"`; `odometry.forward_m` within 1 cm of the tape; `backend/steps.jsonl` has the
   step with its command, result and frames.
3. `env.step("TURN_LEFT_30")`. **Pass:** `odometry.dtheta_deg` positive, within 5 degrees of 30; the car turned
   left (counter-clockwise seen from above).
4. A short B2-driven episode through the harness (work list 3.3, the practice run) is the next task, not this one.

## Open items (need the car, the camera or a decision)

- Nothing above has run on the real car. `perception_detector` has run inside this backend on a rendered frame
  only, not on the camera's frames (the detector's own accuracy is the perception task's and work list 2.4).
- Camera frames per stop: 5 frames at XGA take about 1 s (5.4 frames/s measured, M1.T17).
- The 2.0 m range limit and the detector's settings are the perception task's and the tag pilot's (work list 2.4).
- `unknown_wall`: "allow" or "block" for the real room is Xiaohui's call after the practice run.
