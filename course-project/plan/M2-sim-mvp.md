# M2 — Minimum viable simulated result (the cut line)

Written 2026-10-05 for BeaconMind (EN.665.715 capstone; sole participant and owner: **Xiaohui Chen**;
final deadline **2026-12-13**; ordered, not dated). Read `plan/README.md` first: its §1 session
protocol, §5 conventions L1–L11, §6 contracts C0–C12 and §7 safety rules apply to every task here.
**If this file contradicts the README, the README wins; if either contradicts `AGENT-DESIGN.md` v3.3,
AGENT-DESIGN wins** (README header "Source documents, in authority order", and §1.4 item 8).

## Goal

Produce the project's **minimum viable result** (README §3.4 cut line): an L2 agent (the v3.3 prompt
and the D5 tools) running on simulated arenas with duplicated tag IDs, scored against dead reckoning
(B0), a GTSAM factor graph (B1) and the D7 procedure as code (B2), on identical replayed observation
logs, plus a few closed-loop simulated episodes. Every number comes from code that ran on the Spark
(README §1.3).

## What M2 unlocks

- M4 (full benchmark): M4.T1 pre-registers on top of M2.T12's pilot numbers (OD6); M4.T4/T5 reuse the
  harness, baselines and metrics unchanged.
- M3 (real car): M3.T9 extends `envs/ros_env.py` (M2.T17) with `source: real` and the recorder (M2.T11)
  with `--env real`; M3.T12 records real logs with B2 (M2.T8 + M2.T19); M3.T13 reuses M2.T1's latch;
  M3.T19 replays with B1 (M2.T9) and scores with M2.T10.
- M5.T3/T4 (report Experiments and Results): M2.T12's tables and figure.
- M6.T2 (ROSA demo runtime): needs M2.T1's `dispatch()` for the `bm-tools` MCP server (OD14); M6.T7
  also needs M2.T3, M2.T7, M2.T13, M2.T14 and M2.T20; the twin run (M6.T9) needs M2.T5, M2.T6 and
  M2.T17; the Isaac re-render (M6.T13) needs M2.T15 and M2.T16.

## Entry criteria (tasks of other milestones that must be `done`)

| Needed by | Task | Why |
| --- | --- | --- |
| everything | M1.T1 | Layout, `pyproject.toml`, venvs, pytest config, sync scripts, `.gitignore` lines |
| M2.T1–T3, T7–T14 | M1.T2 | JSON Schemas for C0–C11, `configs/dv.json`, `beaconmind.geometry` (port of `l2_geometry.py`) |
| M2.T4–T6, T15–T17 | M1.T3 | `beaconmind-ros` Humble container; `apriltag_ros`/`image_proc` availability; FastDDS UDP-only reception of Isaac topics |
| M2.T15–T16 | M1.T5 | Isaac version (OD7) and the tag-rendering method that decodes |
| M2.T4, M2.T16 | M1.T7 | `configs/camera.json` (intrinsics, HFOV/VFOV, extrinsics; the URDF camera pose comes from its `extrinsics`) |
| M2.T6 | M1.T8 | `configs/detector_noise.json` (measured) |
| M2.T4, M2.T16 | M1.T9 | `configs/car.json` (measured car) |
| M2.T11, M2.T12 (reportable logs and results) | M1.T8, M1.T9 | No placeholder configs in reported numbers (APPROACH §6) |
| M2.T7 (closed-loop model choice only) | M1.T4 | OD8: which Qwen3.5 setting passes the 60 s p95 gate |
| M2.T18 | M1.T11 | Frontier keys stored, model IDs/prices/field names re-checked, budget guard proven |

**What does not wait.** README §3.3 says "M2.T1–T3 need M1.T2" and "M2.T7–T10 need M2.T1 and M1.T11".
**The M1.T11 part is a proposed narrowing, not yet in force:** M2.T7–T10 make no frontier call (only
M2.T18 does), and M1.T11 needs Xiaohui's API keys and money, so waiting would block the whole kinematic
track. Because the README wins over this file, M2.T7 stays blocked on M1.T11 **until Xiaohui approves the
waiver once**: ask them "May M2.T7–T10 start before M1.T11 (frontier API spike)? They call only the local
vLLM model." and record their answer in `CONTEXT.md` as `M1.T11 waiver for M2.T7–T10: <yes/no>, <date>`
(README open decision **OD18**; M1.T10 block 20 may already have recorded it — check
`grep -n "OD18\|M1.T11 waiver" course-project/CONTEXT.md course-project/AGENT-DESIGN.md` first).
With the waiver, M2.T7 creates `harness/budget.py` with M1.T11's API (M2.T7 step 6), and M1.T11 later
reuses it. Without it, run M1.T11 first. The kinematic track (M2.T1–T3, T7–T10, T13,
T14, T19, T20) does not wait for any camera, car or Isaac task: it uses placeholder car and noise values
that are labelled `placeholder` everywhere they appear, and M2.T11/T12 refuse to report numbers from
placeholders as final.

## Exit criteria (M2 is `done` when all hold, each with evidence under `evidence/M2/`)

1. `beaconmind` core (tools, validator, observation builder, report checker, worlds, kinsim, harness,
   baselines, metrics) passes its unit tests on the Mac, on the Spark host venv (3.12) and in
   `beaconmind-ros` (3.10), with pasted output.
2. Seeded arenas: 100 dev + 200 test worlds per condition generate and pass `worlds.check`.
3. The Isaac twin (M2.T5) runs headless, executes the five moves through `/pico/move/cmd`, publishes
   C12 topics with ground truth, and a full B2 episode in Isaac produced an observation log (M2.T17).
   **Or**, if the twin failed, Xiaohui approved the kinsim fallback in writing (README §3.4) and that
   approval is recorded in `CONTEXT.md`.
4. Observation logs (C9.1) exist for ≥ 10 dev seeds (duplicated condition) and ≥ 10 test seeds, from
   Isaac (or kinsim under the fallback).
5. B0, B1 (iSAM2, oracle association, OD3) and B2 run on the same logs; L2 runs with 2–3 models in
   replay; metrics C10.1–C10.4, C10.7, C10.8 computed; a few closed-loop episodes scored with C10.5.
6. `evidence/M2/M2.T12/results.md` holds the results table and figure generated by code, with every
   number traceable to a run directory and its `run.json` hashes.

## Status table

| Task | Title | Status | Effort | Evidence | Last updated | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| M2.T1 | Core library A: tools `dispatch()` (C4) and validator move checks with the latch (C5.1, C5.5) | todo | S | `evidence/M2/M2.T1/` | 2026-10-05 | |
| M2.T2 | Arena spec (C7), seeded generator, D3 constraint checker, dev/test seed split | todo | S | `evidence/M2/M2.T2/` | 2026-10-05 | |
| M2.T3 | Kinematic simulator (kinsim) with placeholder noise models and ground truth (C8) | todo | M | `evidence/M2/M2.T3/` | 2026-10-05 | |
| M2.T4 | URDF of the car (`beaconmind_description`) from `configs/car.json` | blocked | S | `evidence/M2/M2.T4/` | 2026-10-29 | Blocked on `camera.json` (M1.T7) and M2.T3. **2026-10-29 (late):** the M1.T16 part is done: mass 0.660 kg, centre of mass 0.0105 m (middle value, ±0.0018 m), power-bank box as geometry only, gearbox-box rear estimate −16 → −15 mm (agent decision for Xiaohui to accept); `car.json` footprint keys unchanged until the cable / sweep-radius decision; colcon 23 tests, 0 failures, 1 skipped; four-lens review fixed (`evidence/M2/M2.T4/2026-10-29-m1t16/`). **2026-10-29 (earlier):** also waited on M1.T16 (new mass, two-scale split, bank box). `camera.json` is still absent. `CAMERA_CONVENTION_SETTLED` stays false. Prerequisites M1.T7 (todo), M1.T9 (blocked; lens rows partial) and M2.T3 (todo, no `load_car`) are not done. The camera.json `z_m` (floor) vs `base_link` (axle height) and mount-angle conventions remain a plan conflict (README §1.4 item 8). Built ahead: `gen_props.py` writes `car_props.xacro` from `car.json` through a stand-in for the `load_car` view; colcon 20 tests, 0 failures, 1 skipped (camera.json absent; the test fails, not skips, once camera.json exists until the convention is settled), run with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`; expanded URDF numerically identical to the pre-change expansion (214 elements, 406 numbers, 0 mismatches; only the header comment differs); the Module 6 lab-wrapper expansion is byte-identical before/after (`urdf_diff.txt`); TF = measured lens pose. The URDF departs from step 5 in six recorded ways (12-box chassis, 0.421 kg chassis mass, camera/IMU inertials, wheel-joint convention, sphere wheel collisions, visual-only extras), for Xiaohui to accept (`evidence/M2/M2.T4/README.md`) |
| M2.T5 | Isaac twin complete: move server, `bm_sim_pico` (C2), headless runner, sim bringup | todo | M | `evidence/M2/M2.T5/` | 2026-10-05 | Needs M2.T15, M2.T16 |
| M2.T6 | Simulated perception: `apriltag_ros` + PnP on the Isaac camera; sim-vs-real error; noise injection | todo | M | `evidence/M2/M2.T6/` | 2026-10-05 | |
| M2.T7 | Harness core: neutral step loop, vLLM provider, prompt loader, budget guard, run logs, replay and closed loop | todo | M | `evidence/M2/M2.T7/` | 2026-10-05 | Needs M1.T11 done or Xiaohui's waiver (see Entry criteria) |
| M2.T8 | B0 dead reckoning and B2 (the D7 procedure as code: estimation, steps 1–6) with the baseline runner | todo | M | `evidence/M2/M2.T8/` | 2026-10-05 | |
| M2.T9 | B1: GTSAM iSAM2 offline on the host, oracle association | todo | M | `evidence/M2/M2.T9/` | 2026-10-05 | |
| M2.T10 | Metrics A: trajectory (ATE/RPE), map, association, validity, latency, cost; `score` CLI; evo cross-check | todo | M | `evidence/M2/M2.T10/` | 2026-10-05 | |
| M2.T11 | Record simulated observation logs (C9.1): dev seeds and a first batch of test seeds | todo | M | `evidence/M2/M2.T11/` | 2026-10-05 | |
| M2.T12 | First result: 2–3 models vs B0/B1/B2 in replay (duplicated IDs) + closed-loop episodes; table and figure | todo | M | `evidence/M2/M2.T12/` | 2026-10-05 | |
| M2.T13 | Core library B: observation builder (C3), counters, slip rules, safety flags (C5.3), auto-latch (C5.2) | todo | M | `evidence/M2/M2.T13/` | 2026-10-05 | Appended |
| M2.T14 | Core library C: report parser and harness correction (C5.4, C6) | todo | S | `evidence/M2/M2.T14/` | 2026-10-05 | Appended |
| M2.T15 | Isaac arena: tag36h11 textures, arena builder from C7, render-and-decode spike | todo | M | `evidence/M2/M2.T15/` | 2026-10-05 | Appended |
| M2.T16 | Isaac car: URDF import, differential drive, calibrated camera, ground truth, ROS 2 publishing | todo | M | `evidence/M2/M2.T16/` | 2026-10-05 | Appended |
| M2.T17 | ROS environment adapter (`envs/ros_env.py`) and the first full B2 episode in Isaac | todo | S | `evidence/M2/M2.T17/` | 2026-10-05 | Appended |
| M2.T18 | Frontier providers: `openai_responses` and `anthropic_messages` | todo | S | `evidence/M2/M2.T18/` | 2026-10-05 | Appended |
| M2.T19 | B2 decisions: D7 step 7 (EXPLORE E1–E5, GO_TO_BEACON, RETURN_TO_START, contact recovery, refused turn) | todo | S | `evidence/M2/M2.T19/` | 2026-10-05 | Appended |
| M2.T20 | Metrics B: missions and SPL, exploration, refusal | todo | S | `evidence/M2/M2.T20/` | 2026-10-05 | Appended |

The reserved IDs M2.T1–T12 keep their README §3.2 meaning: "M2.T1 done" means `dispatch()` and the
validator's move checks exist (what M6.T2 needs); the whole core library is M2.T1 + M2.T13 + M2.T14.
"M2.T5 done" means the twin is complete (it requires M2.T15 and M2.T16).

## Task list with dependencies and machines

| ID | Title (short) | Depends on | Effort | Machine(s) |
| --- | --- | --- | --- | --- |
| M2.T1 | tools + validator move checks | M1.T1, M1.T2 | S | Mac; Spark host; Spark container `beaconmind-ros` (3.10 check, if built) |
| M2.T13 | observation builder + safety flags | M2.T1 | M | Mac; Spark host |
| M2.T14 | report parser + correction | M2.T1 | S | Mac; Spark host |
| M2.T2 | worlds generator + checker | M1.T2 | S | Mac; Spark host |
| M2.T3 | kinsim | M2.T2, M2.T13 | M | Mac; Spark host |
| M2.T7 | harness core + vLLM provider | M2.T1, M2.T3, M2.T13, M2.T14; M1.T11 or the waiver (closed-loop setting: M1.T4) | M | Mac; Spark host (vLLM); Spark container `beaconmind-ros` |
| M2.T8 | B0 + B2 estimation (D7 steps 1–6) + baseline runner | M2.T7 | M | Mac; Spark host |
| M2.T19 | B2 decisions (D7 step 7) | M2.T8 | S | Mac; Spark host |
| M2.T9 | B1 GTSAM | M2.T7 | M | Spark host venv `~/.venvs/beaconmind` |
| M2.T10 | metrics A | M2.T7 | M | Mac; Spark host venv |
| M2.T20 | metrics B | M2.T10 | S | Mac |
| M2.T18 | frontier providers | M2.T7, M1.T11 | S | Mac; Spark container `beaconmind-ros` |
| M2.T4 | URDF | M1.T3, M1.T7, M1.T9, M1.T16 (mass, two-scale split, bank box), M2.T3 (the `load_car` view) | S | Mac; Spark container `beaconmind-ros` |
| M2.T15 | Isaac arena + tag textures | M1.T5, M2.T2 | M | Spark host (Isaac `python.sh`, host `python3`) |
| M2.T16 | Isaac car + camera + GT + ROS | M1.T7, M2.T4, M2.T15 | M | Spark host (Isaac); Spark container `beaconmind-ros` |
| M2.T5 | Isaac twin complete (move server, `bm_sim_pico`, runner) | M2.T3, M2.T16 | M | Spark host; Spark container `beaconmind-ros` |
| M2.T6 | sim perception + noise injection | M1.T8, M2.T5, M2.T13 | M | Spark container `beaconmind-ros`; Spark host |
| M2.T17 | ROS env + first Isaac B2 episode | M2.T6, M2.T10, M2.T19 | S | Spark container `beaconmind-ros`; Spark host |
| M2.T11 | record observation logs | M2.T19 (kinsim logs); + M2.T17 (Isaac logs); M1.T8 and M1.T9 for non-placeholder configs | M | Spark |
| M2.T12 | first result | M2.T9, M2.T10, M2.T11, M2.T19, M2.T20 (frontier arm: M2.T18) | M | Spark |

## Suggested execution order (groups in one row can run in any order or in parallel sessions)

| Order | Group | Tasks | Notes |
| --- | --- | --- | --- |
| 1 | Core A | M2.T1, M2.T2 | Pure Python on the Mac |
| 2 | Core B | M2.T13, M2.T14 | Need M2.T1 |
| 3 | Kinsim | M2.T3 | First runnable episodes (B2 drives only after M2.T19; M2.T3's tests use scripted moves) |
| 4 | Harness | M2.T7 | First LLM step on the Spark |
| 5 | Baselines + metrics | M2.T8, M2.T9, M2.T10 | Parallel; M2.T9 on the Spark host |
| 6 | Second wave | M2.T19, M2.T20, M2.T18 | M2.T18 only after M1.T11 |
| I1 | Isaac track (starts when M1.T3, M1.T5, M1.T7, M1.T9 are done; runs in parallel with 3–6) | M2.T4 → M2.T15 → M2.T16 → M2.T5 → M2.T6 → M2.T17 (M2.T17 also needs M2.T10 and M2.T19) | Critical path (README §3.4). Start M2.T15 as soon as M1.T5 and M2.T2 are done, before the car is measured |
| 7 | Data | M2.T11 | Kinsim logs can be recorded as soon as M2.T19 is done; Isaac logs after M2.T17 |
| 8 | Result | M2.T12 | Cut-line deliverable |

**Cut-line triggers (README §3.4) re-stated for M2:** at the start of every session count the days to
2026-12-13. At ≤ 42 days with M2.T12 not done, tell Xiaohui to invoke the cut line. If the Isaac track
is still before M2.T5 at ≤ 42 days, also ask whether to switch M2.T11/T12 to the kinsim fallback
(README §3.4 option (a)).

---

## M2 shared definitions (read before any M2 task)

### Facts checked by the writer of this file (read-only, 2026-10-05)

| Fact | How checked | Result |
| --- | --- | --- |
| Isaac Sim build path | `ls ~/IsaacSim/_build/linux-aarch64/release` (Spark host) | Present (`python.sh`, `exts/`, `extscache/`) |
| Isaac extensions needed by M2 | `ls …/release/exts \| grep -iE "urdf\|wheeled\|ros2\|sensors"` | `isaacsim.asset.importer.urdf` (extension.toml version 2.4.30), `isaacsim.robot.wheeled_robots` (has `controllers/differential_controller.py`), `isaacsim.ros2.bridge` (folders `humble/`, `jazzy/`, and `humble/rclpy/`), `isaacsim.ros2.urdf`, `isaacsim.sensors.camera`, `isaacsim.sensors.physics`, `isaacsim.core.nodes` |
| URDF importer API names | `…/exts/isaacsim.asset.importer.urdf/docs/api.rst` | Commands `URDFCreateImportConfig` and `URDFParseAndImportFile` (via `omni.kit.commands.execute`); config fields `merge_fixed_joints`, `fix_base`, `import_inertia_tensor`, `convex_decomp`, `collision_from_visuals`. The extension depends on UI extensions (`omni.kit.uiapp`, `isaacsim.gui.components`), so a headless enable is **unverified** (M2.T16 step 2) |
| ROS 2 OmniGraph node types | `grep -rl` in `…/exts/isaacsim.ros2.bridge` | Docs exist for `ROS2CameraHelper`, `ROS2CameraInfoHelper`, `ROS2PublishTransformTree`, `ROS2PublishRawTransformTree`, `ROS2PublishOdometry`, `ROS2PublishImu`, `ROS2PublishClock`, `ROS2SubscribeTwist` |
| Isaac's Python | `_ros2_bridge.cpython-311-aarch64-linux-gnu.so` | Python **3.11** inside `python.sh` |
| AprilTag MDL / tag36h11 mosaic | `find` for `*apriltag*` and `*36h11*` in the build and `~/.cache/ov` | **Nothing found locally.** The material may exist only on NVIDIA's remote asset root; M1.T5 decides. M2.T15 defaults to the texture method below |
| OpenCV AprilTag generator | Spark host `python3`: `cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)`, `generateImageMarker(d, 3, 80)` | Works, OpenCV **4.13.0**, image shape (80, 80) |
| Spark host system Python packages | `python3 -c "import …"` | numpy 2.3.5, scipy 1.17.0, matplotlib 3.10.8, openai 2.21.0, anthropic 0.79.0 present; **statsmodels, evo, apriltag, pupil_apriltags absent** (the project venv is separate and does not exist yet) |
| Host C compiler | `which cc gcc` | `/usr/bin/cc`, `/usr/bin/gcc` present |
| `~/.venvs/` | `ls ~/.venvs` | Only `cad-viewer`; `beaconmind` not created yet (M1.T1) |
| Docker images | `docker images` | `pico-microros-builder`, `microros/micro-ros-agent:humble`, `ollama-ros2`, vLLM images; **no `beaconmind-ros` yet** (M1.T3) |
| Spark mirror | `ls ~/Projects/EN.665.715/course-project` | Stale: no `plan/`. Sync (L6) before Spark work |
| `assignments/` on the Spark (reviewer, 2026-10-06) | `ls ~/Projects/EN.665.715/assignments/assignment4/system-prompt/tools/backstory_sim.py` | **Absent.** The L6 sync copies only `course-project/`, so every Spark-side test and tool must read only files under `course-project/` (M2.T1 copies the smoke records into `tests/fixtures/smoke_v33/`; M2.T8 copies the reference simulator into `tests/reference_v33/`) |
| Containers (reviewer, 2026-10-06) | `docker ps -a` | `vllm-rosa` and `rosa-ros2` exited; no `beaconmind-ros` yet |
| v3.3 prompt text | Mac: text after `=== FINAL PROMPT ===` in `assignments/assignment4/system-prompt/evidence/print-output.txt`, `.strip()` | 14,878 characters; MD5 `3b78a2301cf261379a51e6871574f0fa` = the `prompt_md5` of the v7 round-2 smoke records (`evidence/smoke/r2/v7-*.jsonl`); SHA-256 first 12 hex `d0b75b25a86e` |

Facts **not** verified here become verification steps inside the tasks (each says which).

### Reading commands in this file

- Inside Markdown **table cells** a literal pipe must be written `\|`. When you copy a command out of a
  table cell, replace every `\|` with `|` before running it. Commands in fenced code blocks are exact.
- Status checks: use the plan-wide helper `python3 course-project/tools/task_status.py <ID> [<ID> …]` (Mac;
  README convention L12; created by M1.T1). It prints `<ID> <status>` from the status-table row only; the
  prerequisite holds only if the line ends in `done`. A Prerequisites row in this file written as
  `grep -E "^. M2\.T7 " course-project/plan/M2-sim-mvp.md` is the older form of the same check: run the helper
  instead (the grep also prints the task-list row and other tables' rows, which have no status).
- `ssh …` means `ssh -o BatchMode=yes -o ConnectTimeout=15 xiaohui_chen@spark-2a60` (README L5).
- `C` means `$HOME/Projects/EN.665.715/course-project` on the Spark; `ISAAC` means
  `${ISAAC:-$HOME/IsaacSim/_build/linux-aarch64/release}` (or the 6.0 path if M1.T5 chose 6.0).
- Before any command that writes into `evidence/M2/M2.T<k>/` or `data/<folder>/` on the Spark, run
  `mkdir -p` for that folder first (shell redirection does not create folders). This applies to every
  task even where the command block does not repeat it.
- A step labelled *Spark container `beaconmind-ros`* whose command is **not** already wrapped in
  `docker exec …` runs in an interactive container shell: on the Spark host (inside `tmux` session `bm`
  for anything longer than a few minutes) run `docker start beaconmind-ros` if it is exited, then
  `docker exec -it beaconmind-ros bash -l`, then `cd /workspace/course-project`; for ROS commands also
  `source /opt/ros/humble/setup.bash` and, for this project's packages,
  `source /workspace/course-project/ros2_ws/install/setup.bash`. Relative paths such as `data/worlds/…`
  in such commands are relative to `/workspace/course-project` (container) or
  `~/Projects/EN.665.715/course-project` (Spark host).
- M2 touches **no hardware**: no step here needs the car, the Pico or the camera, so README §7 safety rules
  S1–S11 do not arise; S12 (secrets) applies to every task.
- In `beaconmind-ros`, the repository is mounted at `/workspace` (README L4), so the project is
  `/workspace/course-project`; the container shell needs `source /opt/ros/humble/setup.bash` (L5).
- Every CLI that reads configs or observation logs refuses placeholder inputs unless given
  `--allow-placeholder` (M2.T7 step 9). Smoke steps that use the SCRIPT_SCAN log or placeholder configs
  must pass that flag; result runs (M2.T11, M2.T12, M2.T17) must not.

### Module map for M2 (new code; every path relative to `course-project/beaconmind/src/beaconmind/`)

| Module | Task | Public API (exact names) |
| --- | --- | --- |
| `config.py` | M1.T2 (or M2.T1 step 2); M2.T3 adds the views | `repo_root() -> Path`, `course_root() -> Path`, `load_json(path) -> dict`, `load_dv(path=None) -> dict[str, float \| int]` (values only), `sha12_file(path) -> str`, `sha12_json(obj) -> str`; M2.T3: `load_car`, `load_camera`, `load_detector_noise`, `load_odometry_noise`, `range_sigma_m`, `bearing_sigma_deg`, `range_bias_m`, `p_detect`, `optical_to_link_rpy_deg` |
| `geometry.py` | M1.T2 | Port of `l2_geometry.py`: `wrap_deg`, `compose_odometry`, `map_point`, `predict_observation`, `gate_detection`, `fix_pose`, `update_beacon`, `exploration_summary` |
| `tools.py` | M2.T1 | `TOOL_SPECS`, `tool_schema_sha12()`, `StepContext`, `dispatch(name, args, ctx) -> dict`, `rnd(obj, nd=3)`, `err(msg) -> dict`, `initial_memory()` |
| `validator.py` | M2.T1, M2.T13 | `MOVES`, `DECISIONS`, `RESULTS`, `check_move(action, ctx) -> tuple[bool, str \| None]`, `Latch` class, `safety_flags(...)`, `wall_distance_ahead(...)`, `autolatch_reason(...)` |
| `observation.py` | M2.T13, M2.T6 | `odometry_from_motion`, `ticks_to_m`, `aggregate_frames`, `slip_suspected`, `ObservationBuilder`, `inject_sim_noise` (M2.T6) |
| `report.py` | M2.T14 | `parse_final_text`, `check_format`, `correct_report`, `initial_memory` (re-exported from `tools`) |
| `worlds.py` | M2.T2, M2.T15 | `generate`, `check`, `transform_world_to_map`, `tags_in_map_frame`, `arena_geometry` (M2.T15), CLI `python -m beaconmind.worlds` |
| `envs/base.py` | M2.T3 | `Capture`, `Env` (Protocol), `make_move_command` |
| `envs/move_exec.py` | M2.T5 | `BoundedMoveController` (pure-Python move executor used by the Isaac move server) |
| `envs/pico_wire.py` | M2.T5 | C2 wire format: `encode_cmd`, `decode_cmd`, `check_caps`, `encode_result`, `decode_result` |
| `envs/kinsim.py` | M2.T3 | `KinSim`, `tag_view_geometry`, `visible_uids` |
| `envs/replay.py` | M2.T7 | `ObsLogReader`, `ReplaySource` |
| `envs/tag_pnp.py` | M2.T6 | `tag_poses_from_corners` (imports `cv2` lazily) |
| `envs/ros_env.py` | M2.T6, M2.T17 | `RosEnv` (imports `rclpy` inside `__init__`, never at module level) |
| `harness/prompt.py` | M2.T7 | `load_system_prompt()` |
| `harness/providers/{base,vllm,fake}.py` | M2.T7 | `ProviderTurn`, `call(entry, system_text, messages, tools)` |
| `harness/providers/{openai_responses,anthropic_messages}.py` | M2.T18 | `call(...)` |
| `harness/budget.py` | M1.T11 creates it (`BudgetExceeded`, `estimate_cost_usd`, `BudgetGuard`); M2.T7 adds `RunBudget` | `RunBudget`, `entry_cost_usd(entry, usage)` |
| `harness/runlog.py`, `harness/obslog.py` | M2.T7 | `RunWriter`, `EpisodeWriter`, `ObsLogWriter` |
| `harness/runner.py`, `harness/run.py` (CLI), `harness/summarize.py` | M2.T7 | `Policy`, `LLMPolicy`, `ScriptScanPolicy`, `run_episode`, `choose_goto_target`; CLIs `python -m beaconmind.harness.run` and `python -m beaconmind.harness.summarize` |
| `baselines/{b0,b2_rules,b1_gtsam,run}.py` | M2.T8, M2.T9, M2.T19 | `B0`, `B2`, `B1`, CLI `python -m beaconmind.baselines.run` |
| `metrics/{trajectory,mapping,association,validity,cost,missions,exploration,refusal,score}.py` | M2.T10, M2.T20 | see the tasks; CLI `python -m beaconmind.metrics.score` |
| `drivers/record.py`, `drivers/qc.py` | M2.T11 | CLIs `python -m beaconmind.drivers.record`, `python -m beaconmind.drivers.qc` |
| `results/first_result.py` | M2.T12 | CLI `python -m beaconmind.results.first_result` |

`metrics/mapping.py` is the map-error module (L1 lists `metrics/` without fixing file names; the name
`map.py` is avoided because it shadows a builtin name in tracebacks). `drivers/` and `results/` are
new sub-packages of `beaconmind` (inside the package root, so L1's "no new top-level folders" holds).

### Configuration files M2 reads or writes (all under `course-project/configs/`)

| File | Written by | M2 use | If missing |
| --- | --- | --- | --- |
| `dv.json` (C0) | M1.T2 | every threshold | Stop: M1.T2 is not done |
| `car.json` | M1.T9 | URDF, kinsim geometry, sweep radius, ticks | Kinsim tests use `beaconmind/tests/fixtures/car_placeholder.json` (M2.T3 writes it, `"status": "placeholder"`); Isaac tasks stop |
| `camera.json` | M1.T7 | Isaac camera, PnP intrinsics, HFOV | Kinsim uses HFOV 60° (D3 DV); Isaac tasks stop |
| `detector_noise.json` | M1.T8 (measured, `bm.detector_noise/1`; M2 reads it only through the M2.T3 view) | kinsim detection model; B1 σ | Kinsim uses `tests/fixtures/detector_noise_placeholder.json` (M2.T3) |
| `sim_extra.json` | **new in M2.T6** (`bm.sim_extra/1`): the extra noise injected into Isaac detections so they match M1.T8 | Isaac noise injection only | Isaac logs are not recorded (M2.T11 stops) |
| `odometry_noise.json` | **new in M2.T3** (placeholder); M3.T8 replaces with UMBmark numbers | kinsim and `bm_sim_pico` odometry noise; B1 odometry factor sigmas | — |
| `seeds.json` | M2.T2 | world seeds | — |
| `providers.json` (C11) | M1.T11 creates; M2.T7 adds the vLLM entries if absent | model entries | M2.T7 step 3 writes the two vLLM entries |
| `prompt/robot_prompt_v3.3.txt` | **new in M2.T7** | the system prompt, frozen | — |

`odometry_noise.json` and `prompt/` are new files inside the existing `configs/` folder (allowed by
L1: "a file goes in the folder its kind names"). Their schemas are written by the task that creates
them, as `schemas/bm.odometry_noise-1.schema.json`.

### Data paths (C8, C9, L8; all on the Spark under `course-project/data/`, git-ignored)

- Worlds: `data/worlds/<world_id>.json`. `world_id` = `sim-<cond>-s<seed>` with `<cond>` = `uni`
  (unique), `dup` (duplicated) or `hid` (hidden, stretch) — the short forms used by C7's example
  `sim-dup-s1003`.
- Observation logs: `data/obslogs/<log_id>.jsonl` and `data/obslogs/<log_id>.gt.tum`. L2 leaves `<n>`
  in `log_id` = `<world_id>-<driver>-<n>` free; M2 uses `<n>` = `i<k>` for Isaac logs and `k<k>` for
  kinsim logs (`sim-dup-s1000-B2-i1`, `sim-dup-s1000-B2-k1`) so the two sources never collide. The
  header's `source` field is authoritative.
- Run logs: `data/runs/<run_id>/run.json`, `data/runs/<run_id>/<episode_id>.jsonl`, and
  `data/runs/<run_id>/<episode_id>.est.tum` (written by the metrics module). **One run uses logs of one
  source and at most one log per world**, so `episode_id` = `<world_id>-<mission>-k<repeat>` is unique
  inside a run.
- Renders and Isaac logs: `data/renders/`. Isaac kit logs: `data/renders/logs/<name>.log`.

### Determinism rule (L4 "explicit seed")

Every random draw uses `random.Random(<string key>)` with a key built from the world seed, the episode
and the purpose, e.g. `random.Random(f"{seed}:{episode_id}:det:{step}")`. String seeds are hashed
deterministically by CPython's `random` (version-2 seeding), so the same key gives the same numbers on
3.10, 3.11 and 3.12. Never call the module-level `random.random()` or `numpy.random` without a seed.

### Disclosure line for every M2 file (L11)

Python: last paragraph of the module docstring. Shell, launch, XML, YAML, URDF/xacro: a comment block
at the top. Use the model **you** are running as:
```
AI-assisted: <model> via <tool>, <YYYY-MM-DD>: <what it wrote>.
Derived from: <repo>/<file>:<symbol> (copied from this repository / reimplemented)   ← only when it applies
```
Code copied from this repository (for example `smoke_test.py` `run_tool`, `backstory_sim.py`,
`l2_geometry.py`, `discussions/module2/sim/labels.py` `attach_labels`) keeps its original disclosure
line and adds `Derived from: EN.665.715/<path>:<symbol> (copied from this repository, <date>)`.

---
## Tasks

The tasks appear in the suggested execution order (core library, worlds and kinsim, harness, baselines
and metrics, the Isaac track, then data and the result), not in numeric order. Search for
`### M2.T<k> —` to jump to one.

### M2.T1 — Core library A: tools `dispatch()` (C4) and validator move checks with the latch (C5.1, C5.5)

**Why.** Every arm that uses tools (L2 in the harness, B2, the ROSA demo's `bm-tools` MCP server in
M6.T2) must call **one** implementation of the D5 tools with the harness resolving `det` indices and
beacon labels (AGENT-DESIGN D5 "Tools"; README C4). The `move` tool is the only path to motion, so the
validator's refusals (D5 "Validator", README C5.1) and the persistent latch (D6 layer 1, C5.5) live here
too. The reference behaviour is `assignments/assignment4/system-prompt/tools/smoke_test.py` `run_tool`,
which the v3.3 prompt was smoke-tested against; this task reproduces it exactly and generalises it.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M1.T1 done | task | `grep -E "^. M1\.T1 " course-project/plan/M1-foundations.md` (Mac, repo root) | its Status column reads `done` |
| M1.T2 done | task | `grep -E "^. M1\.T2 " course-project/plan/M1-foundations.md` (Mac) | its Status column reads `done` |
| Mac venv works | tool | `course-project/.venv/bin/python -c "import beaconmind, pytest; print(pytest.__version__)"` (Mac) | prints a version, no error |
| Geometry port present | code | `ls course-project/beaconmind/src/beaconmind/geometry.py course-project/configs/dv.json` (Mac) | both paths listed |

**Inputs.**
- `plan/README.md` C0, C1, C2, C4, C5 (whole), L1–L4, L11.
- `AGENT-DESIGN.md` D4, D5 ("Tools", "Validator"), D6.
- `assignments/assignment4/system-prompt/tools/smoke_test.py`: `TOOLS`, `schema`, `rnd`, `err`, `run_tool`.
- `assignments/assignment4/system-prompt/tools/l2_geometry.py` (whole; the reference the port follows).
- `assignments/assignment4/system-prompt/evidence/smoke/scenarios.json` (S1–S4) and
  `evidence/smoke/r2/v7-think.jsonl` and `v7-nothink.jsonl` (40 records; 117 recorded tool calls by
  Qwen3.5 against the v3.3 prompt, all in the thinking file; the nothink records made no tool calls).
  **Do not also read `v7-think-S1…S4.jsonl`:** they are byte-identical splits of `v7-think.jsonl`
  (checked 2026-10-06: `cat v7-think-S{1,2,3,4}.jsonl | md5` equals `md5 < v7-think.jsonl`), so a glob
  over `v7-*.jsonl` counts every call twice (234).
- `course-project/beaconmind/src/beaconmind/geometry.py` and `config.py` (from M1.T2).

**Steps.**
1. *Mac.* Follow README §1.2 steps 1–5. Then confirm the geometry API (verification step):
   ```bash
   cd /Users/xiaohuichen/Projects/EN.665.715/course-project/beaconmind && ../.venv/bin/python -c "
   import inspect, beaconmind.geometry as g
   for n in ['wrap_deg','compose_odometry','map_point','predict_observation','gate_detection','fix_pose','update_beacon','exploration_summary']:
       print(n, inspect.signature(getattr(g, n)))"
   ```
   - If all eight print and the parameter names match `l2_geometry.py` (extra keyword parameters such as
     `dv=None` are fine) → continue at step 2.
   - If a name is missing (`AttributeError`) → stop and ask (§1.4 item 3): M1.T2 is incomplete.
   - If the functions take a required `dv` argument → continue, and in step 4 pass `ctx.dv` to every
     geometry call.
2. *Mac.* Verification step for the config helpers:
   `grep -nE "def (load_dv|sha12_file|sha12_json|course_root)" src/beaconmind/config.py`.
   - All four found → continue at step 3.
   - File or any function missing → create or complete `src/beaconmind/config.py` with exactly:
     `repo_root() -> Path` (walks up from `__file__` to the folder that contains `AGENTS.md`),
     `course_root() -> Path` (= `repo_root() / "course-project"`), `load_json(path) -> dict`,
     `load_dv(path=None) -> dict` (reads `configs/dv.json`, returns `{key: entry["value"]}` for every
     entry that is a dict with a `"value"` key), `sha12_file(path) -> str` (SHA-256 of the bytes, first 12
     hex), `sha12_json(obj) -> str` (SHA-256 of `json.dumps(obj, sort_keys=True, separators=(",", ":"))`,
     first 12 hex). Standard library only.
3. *Mac.* Build the parity fixture from the recorded smoke runs (repository code, allowed by L11).
   Create `course-project/tools/extract_smoke_calls.py` that reads every record of exactly two files,
   `assignments/assignment4/system-prompt/evidence/smoke/r2/v7-think.jsonl` and
   `…/r2/v7-nothink.jsonl` (never a `v7-*.jsonl` glob: the `-S1…-S4` files duplicate `v7-think.jsonl`),
   keeps the records whose `calls` list is non-empty, and writes
   `course-project/beaconmind/tests/fixtures/smoke_v33/calls.json` as a list of
   `{"file", "line", "scenario", "run", "all_pass", "final", "calls": [{"tool", "args", "result"}, …]}`
   (`all_pass` = the record's `check.all_pass`, `final` = its `final` text; keep the order of calls;
   each record's `calls` items already have exactly the keys `tool`, `args`, `result`; `scenario` is
   the record's `scenario` value, a key of `scenarios.json`'s `"scenarios"` object such as
   `S1_duplicate_new`), and
   copies `evidence/smoke/scenarios.json` to `tests/fixtures/smoke_v33/scenarios.json`. Run it:
   `cd /Users/xiaohuichen/Projects/EN.665.715 && course-project/.venv/bin/python course-project/tools/extract_smoke_calls.py`.
   Expected: it prints `40 records read, 14 with calls, 117 calls` (counts checked by the reviewer on
   2026-10-06; per tool: gate_detection 36, compose_odometry 15, fix_pose 14, move 14,
   exploration_summary 12, map_point 10, update_beacon 10, the misspelled `gatedetection` 5,
   emergency_stop 1; `predict_observation` was never called). The misspelled calls must come back as
   errors. If any count differs → stop and ask (§1.4 item 3).
4. *Mac.* Create `src/beaconmind/tools.py` (standard library only):
   - `TOOL_SPECS: list[dict]` — nine entries `{"name", "description", "parameters"}` with the names,
     descriptions and argument types of `smoke_test.py` `TOOLS`, and `parameters` built exactly as
     `smoke_test.py` `schema()` builds them (copied from this repository; add the `Derived from:` line).
     Order: `compose_odometry, gate_detection, fix_pose, map_point, update_beacon, predict_observation,
     exploration_summary, move, emergency_stop`.
   - `tool_schema_sha12() -> str` = `config.sha12_json(TOOL_SPECS)` (C4 "Tool-schema version").
   - `rnd(o, nd=3)` and `err(msg) -> {"status": "error", "error": msg + " Nothing changed."}` — same
     behaviour as `smoke_test.py`.
   - `initial_memory() -> dict` — the D7 step-0 memory (11 keys, values as `backstory_sim.py`
     `initial_memory`).
   - `@dataclass class StepContext` with fields: `observation: dict`, `prev_report: dict | None`,
     `dv: dict`, `executor: Callable[[str], dict] | None = None`, `latch: "Latch | None" = None`,
     `moved: str | None = None`, `estop: bool = False`, `violations: list = field(default_factory=list)`,
     `tool_log: list = field(default_factory=list)`. Use `typing.Optional`/`Union` or
     `from __future__ import annotations` so it runs on 3.10.
   - `dispatch(name: str, args, ctx: StepContext) -> dict`. Behaviour (never raises; wraps everything in
     `try/except Exception` and returns `err(f"{type(e).__name__}: {e}.")`, as `run_tool` does):
     1. `args` not a dict → `err("arguments are not a JSON object.")`.
     2. Resolve `dets = {d["det"]: d for d in observation["detections"]}`; `bmap = {b["beacon"]: b for b in
        prev_report["map"]}` (empty when `prev_report` is None); `memory = prev_report["memory"]` or
        `initial_memory()`; `counters = observation["counters"]`.
     3. Per tool, call `beaconmind.geometry` exactly as `run_tool` does (same refusals and same error
        texts: unknown label, `fix_pose` on a non-confirmed or suspect beacon, `update_beacon` on a
        confirmed beacon), and for an index not in `dets` return `err(f"det {i} is not a detection in this
        observation.")`.
     4. `move` → `validator.check_move(action, ctx)`; if refused, append `{"code": "guardrail",
        "detail": reason}` to `ctx.violations` and return `{"result": "refused", "reason": reason}`. If
        allowed and `ctx.executor is None` → `{"result": "refused", "reason": "no executor"}`. Otherwise
        `res = ctx.executor(action)`; set `ctx.moved = action` **only if** `res["result"] != "refused"`
        (D4: a refused move does not use up the observation); return
        `{"result": res["result"], "reason": res.get("reason")}`.
     5. `emergency_stop` → `ctx.estop = True`; if `ctx.latch` is set, `ctx.latch.set(reason=args.get(
        "reason", ""), by="agent")`; return `{"status": "ok", "latched": True}`.
     6. Unknown name → `err("unknown tool.")` (the exact `run_tool` text, so parity holds).
     7. Successful results are `rnd(result)` and get **no** added `status` key (the v3.3 prompt was
        smoke-tested on these exact shapes). **Known conflict, decide at the end of the session:**
        AGENT-DESIGN D5 "Tools" says every tool returns JSON "with `status`", while `smoke_test.py`
        `run_tool` (the code the v3.3 prompt was tested against) adds `status` only to errors and to
        `emergency_stop`. Default: parity (no `status` on success), because changing the shapes changes
        what the frozen prompt was validated on. Alternative: add `"status": "ok"` to every successful
        result and make the parity test compare results with the `status` key removed. AGENT-DESIGN
        outranks this plan (README header), so ask Xiaohui (§1.4 item 8) and record the answer in
        `CONTEXT.md` as `tool status key: <parity|status ok>, <date>`; do not mark M2.T1 `done` without it.
        This is README open decision **OD16**: if M1.T10 already recorded it (`grep -n "OD16"
        course-project/AGENT-DESIGN.md course-project/CONTEXT.md`), use that answer and do not ask again.
     8. Append `{"name", "args", "result", "error": result.get("error") if isinstance(result, dict) else
        None}` to `ctx.tool_log`; if the result is an error, also append `{"code": "invalid_tool_call",
        "detail": name + ": " + error}` to `ctx.violations` (C5.4).
5. *Mac.* Create `src/beaconmind/validator.py` part A (standard library only):
   - `MOVES = ("FORWARD_25", "FORWARD_10", "BACKWARD_10", "TURN_LEFT_30", "TURN_RIGHT_30")`;
     `DECISIONS = MOVES + ("DONE", "NONE", "STOPPED", "ASK", "REFUSED")`;
     `RESULTS = ("done", "stalled", "bumped", "timeout", "link_lost", "refused", "not_called")` (C2).
   - `check_move(action: str, ctx) -> tuple[bool, str | None]`, first match wins, reason strings fixed
     (the first four are `run_tool`'s exact texts):
     | # | Condition | Reason |
     | --- | --- | --- |
     | 1 | `ctx.estop` or `counters["latched"]` or `ctx.latch` is set | `"latched"` |
     | 2 | `action not in MOVES` | `"not a move"` |
     | 3 | `ctx.moved` is not None | `"one executed move per obs_id"` |
     | 4 | forward action not in `safety["forward_allowed"]` | `"not in forward_allowed"` |
     | 5 | `BACKWARD_10` and not `safety["backward_allowed"]` | `"backward not allowed"` |
     | 6 | turn and not `safety["turn_allowed"]` | `"turn not allowed"` |
     | 7 | `observation["mode"] == "replay"` | `"replay: moves are not executed"` |
     | 8 | `observation["status"] == "error"` | `"status error"` |
     | 9 | `counters["steps_left"] <= 0` | `"no steps left"` |
     Rows 7–9 come after 1–6 only so that the parity fixture (all closed-loop, status ok, steps left)
     gives `run_tool`'s reasons; the order does not change *whether* a move is refused.
   - `class Latch` (C5.5): `__init__(self, path)`; `is_set() -> bool` (file exists);
     `set(reason: str, by: str) -> None` (writes `{"reason", "by", "time_utc"}` JSON, creates parent
     folders); `read() -> dict | None`; `clear(operator: str) -> None` (raises `ValueError` if `operator`
     is empty; deletes the file).
   - `clear_latch_main(argv=None) -> int` for the command `python -m beaconmind.validator clear-latch
     --path <file> --operator <name>` (default path `course_root()/"data"/"LATCH"`), printing
     `latch cleared by <name>` or `no latch at <path>`; add `if __name__ == "__main__":`. Add the console
     script `bm-clear-latch = "beaconmind.validator:clear_latch_main"` to `[project.scripts]` in
     `pyproject.toml` (C5.5 names the operator command `bm-clear-latch`).
   - Latch file locations: closed loop in Isaac or on the car → `data/LATCH` (C5.5); kinsim and replay
     episodes → `data/runs/<run_id>/<episode_id>.LATCH`, so that one simulated episode's auto-latch
     ends that episode only. The runner (M2.T7) passes the path.
6. *Mac.* Write the tests below, run them, fix until green (two honest attempts per failure, §1.4 item 4).
7. *Mac.* Run the whole suite: `cd course-project/beaconmind && ../.venv/bin/python -m pytest -q`.
8. *Mac → Spark.* Sync (`bash course-project/tools/sync_to_spark.sh`), then on the *Spark host*:
   `cd ~/Projects/EN.665.715/course-project/beaconmind && ~/.venvs/beaconmind/bin/python -m pytest -q`.
9. *Spark container `beaconmind-ros`* (only if it exists:
   `ssh -o BatchMode=yes -o ConnectTimeout=15 xiaohui_chen@spark-2a60 'docker ps -a --format "{{.Names}}" | grep -x beaconmind-ros'`):
   `docker start beaconmind-ros` if exited, then
   `docker exec beaconmind-ros bash -lc 'cd /workspace/course-project/beaconmind && python3 -m pytest -q'`.
   If the container does not exist yet → record "not executed — run in `beaconmind-ros` after M1.T3
   with `<command>`" in the evidence and in `CONTEXT.md`; the M2 exit checklist re-runs it.
10. Save evidence, update the status table and `CONTEXT.md` (README §1.2 steps 8–10).

**Deliverables.**
- `course-project/beaconmind/src/beaconmind/tools.py`, `validator.py` (part A), `config.py` (only if
  step 2 created or completed it), `pyproject.toml` (console script).
- `course-project/tools/extract_smoke_calls.py`.
- `course-project/beaconmind/tests/fixtures/smoke_v33/calls.json`, `scenarios.json`.
- `course-project/beaconmind/tests/test_tools.py`, `test_validator_moves.py`, `test_tools_parity.py`.

**Tests.**
- Unit tests, `tests/test_tools.py` (16):
  - `test_tool_specs_names` — names equal the nine C4 names in the order of step 4.
  - `test_tool_schema_sha12_stable` — two calls return the same 12-hex-character string.
  - `test_compose_odometry_matches_geometry` — `dispatch` equals `rnd(geometry.compose_odometry(...))`.
  - `test_unknown_tool_returns_error` — `{"status": "error"}` and the error ends with `"Nothing changed."`.
  - `test_args_not_dict_returns_error` — `args=[1, 2]` gives an error.
  - `test_bad_det_index_returns_error` — `det=7` with two detections gives an error naming det 7.
  - `test_gate_detection_unknown_label_error` — a label absent from PREVIOUS_REPORT gives an error.
  - `test_fix_pose_refuses_tentative` — error; `ctx.violations` gains `invalid_tool_call`.
  - `test_fix_pose_refuses_suspect`.
  - `test_update_beacon_refuses_confirmed`.
  - `test_predict_observation_label_point_and_json_string` — a label, a dict and a JSON-string point all
    resolve; `near_blocked` is present.
  - `test_exploration_summary_reads_memory_blocked_heading` — setting `blocked_heading_deg` in
    PREVIOUS_REPORT memory marks the sectors within ±30° `blocked`.
  - `test_step0_without_previous_report` — `gate_detection` with `candidates=[]` returns `new_point` and
    an empty candidate list; `exploration_summary` returns 12 sectors.
  - `test_results_rounded_to_three_decimals` — every float in every result has ≤ 3 decimals.
  - `test_dispatch_never_raises` — 300 seeded random `(name, args)` pairs (`random.Random("fuzz")`) all
    return a dict.
  - `test_emergency_stop_sets_latch_file` — with `Latch(tmp_path/"LATCH")`, the file exists afterwards
    and `read()["by"] == "agent"`.
- Unit tests, `tests/test_validator_moves.py` (15):
  - `test_move_ok_calls_executor_once` — a counting fake executor is called once; `ctx.moved` set.
  - `test_second_move_refused` — reason `"one executed move per obs_id"`.
  - `test_executor_refusal_does_not_use_observation` — executor returns `refused`; `ctx.moved` is None;
    a second move is executed.
  - `test_move_refused_when_counters_latched`, `test_move_refused_after_emergency_stop`,
    `test_move_refused_on_status_error`, `test_move_refused_in_replay`,
    `test_forward_not_in_forward_allowed_refused`, `test_backward_refused_when_not_allowed`,
    `test_turn_refused_when_not_allowed`, `test_move_refused_no_steps_left`,
    `test_unknown_action_refused` — each asserts `result == "refused"`, the exact reason string of
    step 5, and that the executor was **not** called.
  - `test_refusals_logged_as_guardrail` — `ctx.violations[-1]["code"] == "guardrail"`.
  - `test_latch_roundtrip` — set → `is_set()` True → `clear("Xiaohui")` → False; `clear("")` raises
    `ValueError`.
  - `test_clear_latch_cli` — `subprocess.run([sys.executable, "-m", "beaconmind.validator", "clear-latch",
    "--path", str(p), "--operator", "test"])` exits 0, prints `latch cleared by test`, file gone.
- Unit tests, `tests/test_tools_parity.py` (2):
  - `test_parity_with_recorded_smoke_calls` — for every record in `fixtures/smoke_v33/calls.json`, build a
    fresh `StepContext` from the scenario's observation and prev_report with an executor that returns
    `{"result": "done", "reason": None}`, replay the calls **in order**, and assert: when the recorded
    result has no `"error"` key, `dispatch(...) == recorded result` exactly; when it has one, the
    dispatch result also has `status == "error"`.
  - `test_parity_fixture_covers_every_tool` — the fixture contains at least one call of each tool used
    in the smoke runs (`compose_odometry, emergency_stop, exploration_summary, fix_pose, gate_detection,
    map_point, move, update_beacon`) and the misspelled `gatedetection`.
- Command (Mac): `cd course-project/beaconmind && ../.venv/bin/python -m pytest -q tests/test_tools.py
  tests/test_validator_moves.py tests/test_tools_parity.py` → final line starts `33 passed`.
- Smoke test: none (no service involved). The full-suite runs of steps 7–9 must end with `passed` and no
  `failed` or `error`.

**Acceptance criteria.**
- [ ] The three test files pass on the Mac (`33 passed`), and the full suite passes on the Mac and the
      Spark host venv; the 3.10 run passed or is labelled "not executed" with the command.
- [ ] Parity: every recorded successful smoke-test tool result is reproduced exactly.
- [ ] `tool_schema_sha12()` value recorded in `evidence/M2/M2.T1/tool_schema_sha12.txt`.
- [ ] Xiaohui's answer on the tool `status` key (step 4 item 7) recorded in `CONTEXT.md`.
- [ ] Every new file carries the L11 disclosure; copied code carries `Derived from:`.

**Evidence to save** (`course-project/evidence/M2/M2.T1/`).
- `pytest_mac.txt`, `pytest_spark_host.txt`, `pytest_py310.txt` (or the "not executed" note) — real output.
- `extract_smoke_calls.txt` — the output of step 3.
- `tool_schema_sha12.txt` — one line: the hash and the date.

**Pitfalls and known gotchas.**
- Do not "fix" the smoke reasons or error texts; parity is the point. New refusals (rows 7–9) use new texts.
- `gate_detection` candidates must be labels from PREVIOUS_REPORT, never coordinates (D5).
- `predict_observation`'s target may arrive as a JSON string (Qwen did this in the smoke runs; `run_tool`
  parses strings that start with `{`).
- Python 3.10 has no `X | None` evaluation at runtime without `from __future__ import annotations`.
- `rnd` must not round integers or booleans (`True` is an `int` in Python; test `isinstance(o, float)`).

**Stop-and-ask conditions.** The `status`-key conflict of step 4 item 7 (D5 against the smoke harness).
The parity test fails on a successful result after two fix attempts (it
means `beaconmind.geometry` differs from `l2_geometry.py`, a design-level discrepancy); the recorded call
count is not 117 (in 14 records with calls); M1.T2's `dv.json` values differ from the C0 table.

**Estimated effort.** S.

**AI-disclosure note.** `tools.py`: `AI-assisted: <model> via <tool>, <date>: wrote dispatch() and StepContext.`
plus `Derived from: EN.665.715/assignments/assignment4/system-prompt/tools/smoke_test.py:TOOLS,schema,run_tool (copied from this repository, <date>)`.
`validator.py`, the tests and `extract_smoke_calls.py`: the plain `AI-assisted:` line.

---

### M2.T13 — Core library B: observation builder (C3), counters, slip rules, safety flags (C5.3), auto-latch (C5.2)

**Why.** The harness, not the model, builds every OBSERVATION: odometry as a chord at mid-heading, the
D5 slip rules, the bookkeeping counters, and the safety flags the agent plans with (AGENT-DESIGN D5
"OBSERVATION", "safety"; README C1, C3, C5.2, C5.3). One builder serves kinsim, the Isaac twin, the car
and replay, so arms differ only by the model. Appended to M2 to keep M2.T1 to one session.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M2.T1 done | task | `grep -E "^. M2\.T1 " course-project/plan/M2-sim-mvp.md` (Mac) | its Status column reads `done` |
| DV keys present | config | `course-project/.venv/bin/python -c "from beaconmind.config import load_dv; d=load_dv(); print(all(k in d for k in ['slip_yaw_disagree_deg','slip_range_min_m','slip_range_frac','slip_ahead_deg','slip_dropout_m','obs_frames','obs_min_frames','forward_wall_limit_m','autolatch_contacts','done_range_m']))"` (Mac, in `course-project/beaconmind`) | `True` |

**Inputs.** README C0, C1 (the chord formula), C2, C3 (whole, including "Detection pipeline" and
`detections_internal`), C5.2, C5.3; AGENT-DESIGN D5 ("OBSERVATION", the slip rules, "safety"), D6;
`assignments/assignment4/system-prompt/tools/backstory_sim.py` (`wall_distance_ahead`, `forward_allowed`,
for the idea only).

**Steps.**
1. *Mac.* README §1.2 steps 1–5.
2. *Mac.* **New design value, stop and ask before coding step 5:** C5.3 refuses turns "when anything …
   lies within the sweep radius plus margin", but C0 has no margin key. Ask Xiaohui to approve adding
   `sweep_margin_m` = **0.05** (proposed default, `status: "DV"`, `source: "AGENT-DESIGN D5 'sweep
   radius + margin'; proposed in M2.T13"`) to `configs/dv.json`. Alternative: 0.10 m if Xiaohui prefers
   more clearance (fewer turns allowed near walls). Record the answer in `CONTEXT.md`. Until approved,
   implement with the key but do not mark the task `done`. (Part of README open decision **OD17**; if
   M1.T10 already recorded it, use that answer and do not ask again.)
3. *Mac.* Create `src/beaconmind/observation.py` (standard library only) with:
   - `odometry_from_motion(s_left_m: float, s_right_m: float, dtheta_deg: float) -> dict` — C1:
     `s = (s_left_m + s_right_m)/2`, `dθ = radians(dtheta_deg)`, `c = s·sinc(dθ/2)` with `sinc(0)=1`,
     `forward_m = c·cos(dθ/2)`, `left_m = c·sin(dθ/2)`, returns `{"forward_m", "left_m", "dtheta_deg"}`
     unrounded. (Label in the docstring: "proposed default; C1 assigns the confirming unit test against
     compose_odometry to M2.T1, and it is done here in M2.T13 (`test_chord_matches_exact_arc`) because the
     builder lives here".)
   - `ticks_to_m(ticks: int, car: dict) -> float` = `ticks / car["ticks_per_wheel_rev"] · π ·
     car["wheel_diameter_m"]`.
   - `aggregate_frames(frames: list[list[dict]], dv: dict) -> tuple[list[dict], list[dict], list[dict]]`
     — C3 detection pipeline. Each frame item: `{"id": int | None, "uid": str | None, "x_m", "y_m",
     "normal_yaw_deg": [a, b]}` in `base_link`. Group by `id` and, inside one id, by proximity (two
     items of the same id belong to the same tag when their positions are within 0.30 m, so duplicated
     IDs in one view stay separate). Keep groups seen in ≥ `obs_min_frames` frames. For each kept group:
     median `x_m`, `y_m`, per-solution median normal yaw, `frames_seen`, majority `uid`. Returns
     `(detections, detections_internal, det_truth)`:
     `detections[i] = {"det": i, "id", "range_m": round(hypot,2), "bearing_deg": round(deg(atan2(y,x)),1),
     "quality": round(frames_seen/obs_frames, 2)}` sorted by `bearing_deg` descending (left to right),
     then `id`; `detections_internal[i] = {"det": i, "id", "x_m", "y_m", "normal_yaw_deg": [a, b],
     "frames_seen", "uid"}`; `det_truth = [{"det": i, "uid": uid}]` for groups with a non-null uid.
   - `slip_suspected(odo_motion, enc_dyaw_deg, prev_internal, cur_internal, last_move, dv) -> tuple[bool,
     str | None]` — D5: (a) `abs(enc_dyaw_deg − gyro dθ) > slip_yaw_disagree_deg` → `(True, "yaw
     disagree")`; (b) after a forward move with achieved distance `d`, for each tag (matched between the
     previous and current internal detections by equal `id` and the nearest predicted position) whose
     previous bearing is within ±`slip_ahead_deg`: expected range decrease `e = d·cos(bearing)`, observed
     decrease `o = prev_range − cur_range`; slip when `o < e − max(slip_range_min_m, slip_range_frac·d)`
     → `(True, "range change")`. **Interpretation note to put in the docstring:** D5's wording "changed
     the range … by less than max(0.08 m, 0.3 × move) of the expected amount" is read as "fell short of
     the expected decrease by more than that margin"; (c) a tag with previous range < `slip_dropout_m`
     and |bearing| ≤ `slip_ahead_deg` that is absent after a forward move → `(True, "close tag dropped
     out")`. Otherwise `(False, None)`.
   - `class ObservationBuilder` with `__init__(self, dv, car, *, source, mode, episode_id, latch,
     round_outputs=True)` (`round_outputs=False` only in tests that need exact values; every run uses the
     default) and:
     - `start_mission(self, mission: str, steps_budget: int, step: int) -> None` — sets the mission and
       `steps_left` base (D2: the harness resets `steps_left` on a mission switch).
     - `build(self, step, capture, move, prev_report) -> tuple[dict, list[dict], list[dict]]` returning
       `(observation, detections_internal, det_truth)`. `capture` is an `envs.base.Capture` (M2.T3
       defines it; for this task use a plain dict with keys `frames`, `sensors`, `boot_id`); `move` is
       `None` (step 0 or no move) or `{"command": MoveCommand, "result": MoveResult}` (C2). Fill every C3
       field exactly:
       - `obs_id` = `f"{episode_id}-s{step:03d}"` (L2); `source`, `mode` from the constructor.
       - `odometry`: step 0 → `{"forward_m": 0.0, "left_m": 0.0, "dtheta_deg": 0.0, "quality": "ok"}`;
         a boot-id change → `None`; no executed move → zeros with `quality: "ok"`; otherwise
         `odometry_from_motion(ticks_to_m(left), ticks_to_m(right), gyro_dyaw_deg)` rounded to 0.01 m /
         0.1°, `quality` = `"slip_suspected"` if `slip_suspected(...)[0]` else `"ok"`; encoder yaw for rule
         (a) = `degrees((s_right − s_left)/car["track_width_m"])`.
       - `last_move`: step 0 or no move call → `{"action": None, "result": "not_called"}`; else
         `{"action": command action, "result": result}`.
       - `status`/`error`/`sensors`: `"error"` when camera is `stale` or `down`, IMU `error`, Pico
         `disarmed` while the latch is clear, or the boot id changed (`error` text names which); else
         `"ok"`, `error: None`.
       - `counters` (all in C3): reset `travel_since_fix_m` and `turns_since_fix` to 0 when
         `prev_report` has `pose_source` in (`beacon_fix`, `relocalised`) — **before** adding this step's
         motion (`backstory_sim.py` order); `odometer_m += |forward_m|`; `travel_since_fix_m +=
         |forward_m|`; `turns_since_fix += 1` per executed turn; `consecutive_contacts` +1 on
         `stalled`/`bumped`, 0 on `done`, unchanged when no move executed; `consecutive_slips` +1 on
         `slip_suspected`, 0 on an `ok` forward move; `consecutive_errors` +1 when this status is `error`,
         else 0; `steps_left = steps_budget − (step − mission_start_step)`; `latched` = latch set (after
         auto-latch below). Round metres to 0.01.
       - Auto-latch (C5.2): call `validator.autolatch_reason(counters, last_result, boot_changed, dv)`;
         if it returns a reason, `latch.set(reason, by="validator")` and set `latched: True`.
       - `safety` = `validator.safety_flags(...)` (step 4), plus `"done_range_m": dv["done_range_m"]`.
       - `detections` from `aggregate_frames(capture["frames"], dv)` (empty when the camera is not ok).
     - `rebuild_for_replay(self, step, logged_step: dict, prev_report) -> tuple[dict, list, list]` —
       takes a C9.1 step record and reuses its logged `observation`'s `detections`, `odometry`, `sensors`,
       `status`, `error` and `last_move` (the logged observation's own `last_move`, which describes the
       move executed **after the previous step**, i.e. the previous step record's `executed_move`; never
       this step record's `executed_move`, which happened after this observation), but **recomputes `counters`** from this run's own
       `prev_report` (so `travel_since_fix_m` resets follow this arm's pose sources) and sets
       `mode: "replay"`; `safety` is copied from the log (moves are refused in replay anyway, C5.1).
4. *Mac.* Add to `src/beaconmind/validator.py` (part B):
   - `wall_distance_ahead(internal: list[dict], prior_pose: dict | None, prev_map: list[dict],
     prev_internal: list[dict], last_move: dict, dv: dict) -> float` — C5.3, the minimum of:
     (a) per detection, the distance along +x to the tag's wall plane for normal yaw ψ ∈ {a, b, a±20°,
     b±20°}: the plane through `(x, y)` with unit normal `n = (cos ψ, sin ψ)` meets the +x axis at
     `s = (x·n_x + y·n_y)/n_x` when `n_x < −0.05` (wall faces the robot); keep `s > 0`;
     (b) `range·cos(bearing)` for detections with |bearing| ≤ 45°;
     (c) predicted ranges (`geometry.predict_observation(prior_pose, entry)`) of `prev_map` beacons with
     |bearing| ≤ 30°, when `prior_pose` is not None;
     (d) after a forward move: for each previous-step tag with range < `slip_dropout_m` and |bearing| ≤
     `slip_ahead_deg` that is not seen now, `prev_range·cos(prev_bearing) − achieved_forward_m`.
     Return `math.inf` when no term exists (walls are invisible between tags — D6 residual risk).
   - `safety_flags(internal, detections, prior_pose, prev_map, prev_internal, last_move, car, dv) -> dict`
     returning `{"forward_allowed": [...], "backward_allowed": bool, "turn_allowed": bool,
     "scan_allowed": bool}`: `forward_allowed` = each of `FORWARD_25` (0.25 m) and `FORWARD_10` (0.10 m),
     in that order, with `wall − distance ≥ forward_wall_limit_m`; `backward_allowed` = the last move was
     a forward move with result `done`, `stalled` or `bumped` (D4); `turn_allowed` = no detection with
     `range_m < car["sweep_radius_m"] + dv["sweep_margin_m"]` and no `prev_map` beacon predicted that
     close; `scan_allowed` = `turn_allowed`.
   - `autolatch_reason(counters, last_result, boot_changed, dv) -> str | None` — first match:
     `boot_changed` → `"pico reboot"`; `last_result == "link_lost"` → `"link lost"`;
     `consecutive_contacts ≥ autolatch_contacts` → `f"{autolatch_contacts} consecutive contacts"` (with
     the C0 default 2 this is `"2 consecutive contacts"`); likewise `"… consecutive slips"` and
     `"… consecutive errors"`.
   - The prior pose used for (c) and the sweep test is `geometry.compose_odometry(prev_report["pose"],
     **odometry)` (or `prev_report["pose"]` when odometry is null; `None` at step 0).
5. *Mac.* Write the tests below; run; fix.
6. *Mac → Spark host.* Sync and run the full suite on the Spark host venv (as M2.T1 step 8) and, if it
   exists, in `beaconmind-ros` (M2.T1 step 9).
7. Evidence, status, `CONTEXT.md`.

**Deliverables.** `src/beaconmind/observation.py`; `src/beaconmind/validator.py` (part B);
`configs/dv.json` (`sweep_margin_m`, only after approval); `tests/test_observation.py`,
`tests/test_safety_flags.py`.

**Tests.**
- `tests/test_observation.py` (17):
  - `test_chord_straight` — `odometry_from_motion(0.25, 0.25, 0)` → `(0.25, 0, 0)` within 1e-12.
  - `test_chord_pure_turn` — `(−0.05, 0.05, 30)` → forward 0, left 0, dθ 30.
  - `test_chord_matches_exact_arc` — for 20 seeded `(s, dθ)` with |dθ| ≤ 40°, composing the chord with
    `geometry.compose_odometry` from (0,0,0) equals the exact constant-curvature arc end point
    `(R·sin dθ, R·(1−cos dθ))`, `R = s/dθ`, within 1e-9 m (this is the "M2.T13 confirms" test C1 asks for).
  - `test_chord_backward_negative` — `(−0.1, −0.1, 0)` gives `forward_m = −0.1`.
  - `test_aggregate_median_and_quality` — 5 frames, a tag seen in 4: quality 0.8, median position.
  - `test_aggregate_drops_below_min_frames` — seen in 2 of 5 with `obs_min_frames` 3 → dropped.
  - `test_aggregate_keeps_duplicate_ids_apart` — two id-3 tags 1.5 m apart → two detections.
  - `test_aggregate_sorted_left_to_right` — bearings 20, −10, 5 → det order 20, 5, −10.
  - `test_det_truth_majority_uid`.
  - `test_slip_yaw_disagree` / `test_slip_range_shortfall` / `test_slip_close_tag_dropout` /
    `test_no_slip_on_clean_move` — one rule each, asserting the returned reason.
  - `test_builder_step0_fields` — every C3 key present; odometry zeros; `last_move.result ==
    "not_called"`; `obs_id` format.
  - `test_builder_counters_reset_after_beacon_fix` — prev report `beacon_fix` → `travel_since_fix_m`
    equals only this step's forward distance.
  - `test_builder_status_error_on_camera_stale_and_boot_change` — status `error`, odometry None on the
    boot change.
  - `test_builder_autolatch_two_contacts` — two consecutive `bumped` results → `latched: True` and the
    latch file reason `"2 consecutive contacts"`.
- `tests/test_safety_flags.py` (9):
  - `test_wall_from_tag_plane_head_on` — tag at (0.80, 0), normal 180° → wall 0.80; FORWARD_25 allowed
    only if 0.80 − 0.25 ≥ 0.35 (true) — assert both moves allowed.
  - `test_wall_close_blocks_forward25_only` — wall 0.55 → `["FORWARD_10"]`.
  - `test_wall_too_close_blocks_both` — wall 0.40 → `[]`.
  - `test_oblique_normal_uses_conservative_solution` — two ambiguity solutions; the smaller distance wins.
  - `test_mapped_beacon_ahead_counts` — no detection, one mapped beacon predicted 0.50 m straight ahead
    → FORWARD_25 refused (0.50 − 0.25 = 0.25 < 0.35), FORWARD_10 allowed (0.40 ≥ 0.35); assert exactly
    `["FORWARD_10"]`.
  - `test_dropout_term` — a tag 0.6 m ahead last step, gone after FORWARD_10 → wall 0.50 → only
    FORWARD_10 allowed.
  - `test_no_tags_means_inf` — empty inputs → both forwards allowed (residual risk documented).
  - `test_backward_allowed_rules` — true after FORWARD_10 `stalled`; false after TURN or after `refused`.
  - `test_turn_blocked_within_sweep` — detection at `sweep_radius_m + sweep_margin_m − 0.01` → turn and
    scan not allowed.
- Command (Mac): `../.venv/bin/python -m pytest -q tests/test_observation.py tests/test_safety_flags.py`
  → `26 passed`.
- Smoke test: none.

**Acceptance criteria.**
- [ ] 26 tests pass on the Mac; the full suite passes on the Spark host (3.10 run or "not executed" label).
- [ ] `sweep_margin_m` approved by Xiaohui and recorded (value, date) in `CONTEXT.md` and `dv.json`.
- [ ] The chord test (`test_chord_matches_exact_arc`) passes, which settles C1's "proposed default
      (M2.T1 confirms)" note; record that in `CONTEXT.md` (do not edit the README).

**Evidence to save** (`evidence/M2/M2.T13/`). `pytest_mac.txt`, `pytest_spark_host.txt`,
`pytest_py310.txt` (or label), `sweep_margin_decision.md` (Xiaohui's answer, verbatim, with the date).

**Pitfalls and known gotchas.**
- `bearing_deg` is CCW positive from +x (C1); `atan2(y, x)` in `base_link` gives exactly that.
- Rounding happens once, when the observation is emitted; internal values stay unrounded.
- A tag's "normal yaw" is the direction the tag faces (into the arena, toward the robot), not the wall
  direction; for a tag straight ahead it is ≈ 180°.
- Duplicated IDs: never key internal state by `id` alone.
- The tilt firmware's "forward" is reversed (C1 warning); kinsim and the twin follow +x.

**Stop-and-ask conditions.** `sweep_margin_m` (step 2). Any DV key in C0 missing from `dv.json`. A test
reveals that D5's slip wording admits a different reading than the interpretation note (report both).

**Estimated effort.** M (two sessions: steps 1–3 + `test_observation.py`; steps 4–7).

**AI-disclosure note.** Each file: `AI-assisted: <model> via <tool>, <date>: wrote the observation builder / safety flags and tests.`

---

### M2.T14 — Core library C: report parser and harness correction (C5.4, C6)

**Why.** "The harness is authoritative for state" (AGENT-DESIGN D5): each step's final text must be one
D8 JSON object; poses and map entries that differ from the tool results by more than rounding are
logged as `state` violations and replaced by the tool-derived value; malformed output is a `format`
violation (README C5.4, C6). The corrected report becomes the next step's PREVIOUS_REPORT (C3) and the
source of every metric. Appended to M2.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M2.T1 done | task | `grep -E "^. M2\.T1 " course-project/plan/M2-sim-mvp.md` (Mac) | Status `done` |
| Report schema exists | code | `ls course-project/beaconmind/src/beaconmind/schemas/bm.report-1.schema.json` (Mac) | listed (M1.T2) |

**Inputs.** README C5.4, C6; AGENT-DESIGN D7 (step 5 map rules, step 8 report), D8 (whole, Example 1);
`assignments/assignment4/system-prompt/tools/smoke_test.py` `_report` (fence stripping);
`tests/fixtures/smoke_v33/` (from M2.T1); `assignments/assignment4/system-prompt/evidence/fewshot-numbers.json`.

**Steps.**
1. *Mac.* README §1.2 steps 1–5.
2. *Mac.* Create `src/beaconmind/report.py` (standard library only):
   - `parse_final_text(text: str | None) -> tuple[dict | None, str | None]` — strip whitespace, strip
     **one** leading ```` ``` ```` or ```` ```json ```` fence and one trailing fence (the regex of
     `smoke_test.py` `_report`), `json.loads`; return `(obj, None)` only if `obj` is a dict, else
     `(None, "<reason>")`.
   - `check_format(report: dict, *, step: int, mission: str, mode: str) -> list[str]` — every D8 key
     present (`step, mode, mission, pose, pose_source, associations, loop_closure, map, memory,
     decision, move_result, requested_mission, message, note`); enums as C6 (`pose_source`, association
     `result`, map `state`, `decision`, `move_result` from `validator.RESULTS`); `pose` has three numbers;
     each map entry has `beacon, id, x_m, y_m, n_obs, state, first_seen_from, first_seen_scan,
     odo_last_seen_m, conflicts, suspect`; labels match `^B\d+b?$` or `^U\d+$`; `step`, `mission`, `mode`
     equal the given values. Returns a list of problems (empty = ok).
   - `correct_report(report: dict | None, *, tool_log: list, prev_report: dict | None, executed: dict |
     None, step: int, mission: str, mode: str) -> tuple[dict, list[dict]]` — returns
     `(corrected, violations)`:
     1. `report` None or `check_format` problems → one `{"code": "format", "detail": …}`; corrected =
        a copy of `prev_report` (or the step-0 default: pose (0,0,0), `pose_source: "odometry"`, empty
        map, `initial_memory()`) with `step`, `mission`, `mode` updated, `decision: "NONE"`,
        `move_result` = the executed result or `"not_called"`, `associations: []`, `loop_closure: []`,
        `note: "harness: report unparseable"`.
     2. **Pose check:** candidate tool poses this step = the results of `compose_odometry`, `fix_pose.full`
        (x, y, θ), `fix_pose.position` (x, y, θ) in `tool_log`; at step 0 also (0, 0, 0). The pose is
        accepted when some candidate matches within 0.005 m and 0.05° (D5). Otherwise a `state`
        violation; the replacement is chosen by `pose_source`: `beacon_fix`/`relocalised` → the last
        `fix_pose.full`; `position_fix` → the last `fix_pose.position`; `prior_kept`/`odometry` → the
        last `compose_odometry`; none available → the previous corrected pose.
     3. **Map check**, per entry: a label in `prev_report` with `state: confirmed` must keep its x, y
        (frozen anchor, D7 step 5); a label updated this step must equal an `update_beacon` result for
        it; a new label must equal a `map_point` result this step; otherwise keep the previous x, y (or
        drop a new entry no tool produced). Each fix → `state` violation naming the label.
        `n_obs`, `state`, `first_seen_*`, `conflicts`, `suspect` are bookkeeping the agent owns: not
        corrected, but checked against the previous entry for impossible changes (`n_obs` decreasing,
        `confirmed` → `tentative`) → `state` violation, previous value restored.
     4. **Decision check:** if a move executed this step, `decision` must equal its action and
        `move_result` its result; if no move executed, `decision` must not be a move. Mismatch → `state`
        violation; corrected decision = the executed action, or `"NONE"` if none executed.
     5. Round the corrected pose and map to 0.01 m / 0.1° (C1 rounding).
3. *Mac.* Re-export `initial_memory` from `report.py` (`from .tools import initial_memory`).
4. *Mac.* Write the tests; run; fix. Sync; run the suite on the Spark host (and 3.10 if available).
5. Evidence, status, `CONTEXT.md`.

**Deliverables.** `src/beaconmind/report.py`; `tests/test_report.py`;
`tests/fixtures/reports/example1.json` (D8's Example 1 report, copied from AGENT-DESIGN D8).

**Tests.** `tests/test_report.py` (16):
- `test_parse_plain_json`, `test_parse_fenced_json` (```` ```json … ``` ````), `test_parse_rejects_two_objects`,
  `test_parse_rejects_list`, `test_parse_none_text`.
- `test_example1_passes_format` — the D8 example has no problems for step 41, EXPLORE, closed_loop.
- `test_example1_validates_against_schema` — `jsonschema.validate(example, bm.report-1 schema)`.
- `test_missing_key_is_format_violation` — drop `memory` → corrected equals previous report, violation
  `format`, decision `NONE`.
- `test_bad_enum_is_format_violation` — `pose_source: "gps"`.
- `test_pose_matching_tool_is_accepted` — pose within 0.004 m of `compose_odometry` result → no violation.
- `test_pose_off_by_1cm_corrected_from_fix` — `pose_source: beacon_fix`, pose 0.01 m off the full fix →
  `state` violation, corrected pose = the fix rounded.
- `test_confirmed_beacon_moved_is_restored`.
- `test_new_beacon_without_map_point_dropped`.
- `test_decision_mismatch_corrected` — report `FORWARD_25` but executed `FORWARD_10` → corrected
  `FORWARD_10`, one `state` violation.
- `test_move_decision_without_execution_becomes_none`.
- `test_smoke_scenarios_expected_pass` — take the recorded S1 run with `all_pass: true` from
  `fixtures/smoke_v33/calls.json` (run 5, 8 calls; reviewer-checked 2026-10-06), parse its `final` text
  with `parse_final_text`, and run `correct_report` with that run's calls as the tool log and S1's
  `prev_report` from `scenarios.json`, `step`/`mission`/`mode` from S1's observation, and the recorded
  `move` result as the executed move; assert no `format` violation and no `state` violation on the pose
  and map.
- Command (Mac): `../.venv/bin/python -m pytest -q tests/test_report.py` → `16 passed`. If
  `test_smoke_scenarios_expected_pass` fails, compare the recorded `final` with the tool results by hand
  and report which side is wrong before changing `correct_report` (a recorded passing run should pass).
- Smoke test: none.

**Acceptance criteria.**
- [ ] `test_report.py` passes on the Mac; full suite passes on the Spark host.
- [ ] Example 1 validates against `bm.report-1` (closes C6's "tested against D8's Example 1").

**Evidence to save** (`evidence/M2/M2.T14/`). `pytest_mac.txt`, `pytest_spark_host.txt`, `pytest_py310.txt` or label.

**Pitfalls and known gotchas.** `fix_pose.position` keeps the prior heading (`l2_geometry.fix_pose`); its θ
is the prior's θ. Models often round to 2 decimals; tolerance is 0.005 m, so 2-decimal rounding of a
3-decimal tool value always passes — but only if the comparison is inclusive with a float epsilon
(0.125 rounds to 0.12 or 0.13, a difference of exactly 0.005): compare `abs(a − b) <= 0.005 + 1e-9` (and
`0.05 + 1e-9` for degrees, with wrapped angle differences), and add a test case for exactly that boundary
inside `test_pose_matching_tool_is_accepted`. Do not judge the *correctness* of associations here (that is a
metric, M2.T10), only consistency with tool results.

**Stop-and-ask conditions.** The bm.report-1 schema (M1.T2) rejects D8's Example 1 (a contract conflict).

**Estimated effort.** S.

**AI-disclosure note.** `report.py` and tests: `AI-assisted: <model> via <tool>, <date>: wrote the report parser and harness correction.`
plus `Derived from: EN.665.715/assignments/assignment4/system-prompt/tools/smoke_test.py:_report (copied from this repository, <date>)`.

---
### M2.T2 — Arena spec (C7), seeded generator, D3 constraint checker, dev and test seed split

**Why.** Every simulated episode runs in a world generated from a seed, so that models are compared on
identical arenas (APPROACH §8 "paired on identical seeds") and prompt tuning never touches the
held-out seeds (README C7 "Seeds"). The checker enforces AGENT-DESIGN D3 (convex 2.0–2.5 m rectangle,
10–16 wall tags spaced ≤ 0.8 m, IDs 0–29, at most three duplicated IDs ≥ 1.5 m apart, roof tags
100–109 never on walls), and is reused for the real arena in M3.T10.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M1.T2 done | task | `grep -E "^. M1\.T2 " course-project/plan/M1-foundations.md` (Mac) | Status `done` |
| World schema present | code | `ls course-project/beaconmind/src/beaconmind/schemas/bm.world-1.schema.json` (Mac) | listed |

**Inputs.** README C1 (arena frame), C7 (whole), L2 (`world_id`); AGENT-DESIGN D3; APPROACH §6.

**Steps.**
1. *Mac.* README §1.2 steps 1–5.
2. *Mac.* **Decision with a default (stop and ask at the end of the session, build to the default):**
   how many IDs are duplicated in the `duplicated` condition. D3 allows "up to 3". **Proposed default:
   exactly 3 duplicated IDs in every `duplicated` world** (the hardest case D3 allows, so the condition
   tests association as hard as the design permits). Alternative: a seeded draw of 1–3, if Xiaohui
   prefers variety over difficulty. Record the answer in `CONTEXT.md`; the generator takes it as the
   parameter `n_dup` (default 3).
3. *Mac.* Create `src/beaconmind/worlds.py` (standard library only):
   - Constants: `COND_SHORT = {"unique": "uni", "duplicated": "dup", "hidden": "hid"}`,
     `TAG_BLACK_M = 0.16`, `TAG_BORDER_M = 0.20` (D3), `CORNER_CLEAR_M = 0.15` (generator rule, proposed
     default: the 0.20 m tag plus 0.05 m never wraps a corner), `JITTER_M = 0.05`.
   - `generate(seed: int, condition: str, *, car: dict | None = None, n_dup: int = 3) -> dict`:
     1. Two RNGs: `g = random.Random(f"world:{seed}:geom")` (arena and tag positions — **shared by all
        conditions of one seed**, so unique and duplicated worlds of a seed differ only in IDs) and
        `r = random.Random(f"world:{seed}:ids:{condition}")`.
     2. Width `W` and height `H` = `round(g.uniform(2.0, 2.5) / 0.05) * 0.05` each.
     3. Perimeter `P = 2(W + H)`; `n = g.randint(max(10, ceil(P / 0.70)), 16)` (0.70 leaves room for
        the jitter and the corner shift under the 0.8 m spacing limit; at the largest arena `P = 10` this
        gives n ≥ 15).
     4. Perimeter coordinate `u_i = u0 + i·P/n + g.uniform(−JITTER_M, JITTER_M)`, `u0 = g.uniform(0, P/n)`,
        mapped counter-clockwise from the origin: south wall `y = 0` (x from 0 to W), east `x = W`, north
        `y = H` (x from W to 0), west `x = 0` (y from H to 0). A tag closer than `CORNER_CLEAR_M` to a
        corner is moved along its wall to `CORNER_CLEAR_M`. If the largest circular gap along the
        perimeter exceeds 0.8 m, draw again (same `g`); after every 20 failed draws increase `n` by 1 (never
        above 16); after 100 draws raise `RuntimeError`.
     5. `normal_deg`: south 90, east 180, north −90, west 0 (into the arena). `z_m = max(car
        ["lens_height_m"], 0.12)` (C7) or 0.12 when `car` is None. `uid` = `f"T{i:02d}"` in perimeter order.
     6. IDs: `unique`/`hidden` → `r.sample(range(30), n)`. `duplicated` → `r.sample(range(30), n − n_dup)`
        for the first `n − n_dup` slots of a shuffled slot order; each remaining slot copies the ID of a
        randomly chosen already-assigned slot ≥ 1.5 m away (straight-line) whose ID has not been copied
        yet; retry the ID assignment up to 100 times, then raise. `duplicates` = the list of uid pairs.
     7. `start_pose`: `x ∈ [0.5, W − 0.5]`, `y ∈ [0.5, H − 0.5]` uniform, rounded to 0.01; `theta_deg`
        uniform, rounded to 1°, wrapped to (−180, 180] (C7: start ≥ 0.5 m from every wall, proposed
        default).
     8. Return the C7 object: `schema "bm.world/1"`, `world_id = f"sim-{COND_SHORT[condition]}-s{seed}"`,
        `source "sim"`, `seed`, `generator {"name": "beaconmind.worlds.generate", "version": "1"}`,
        `condition`, `arena {"shape": "rect", "size_m": [W, H], "wall_height_m": 0.30, "origin": …}` (origin
        text exactly as C7), `tags`, `duplicates`, `roof_tags: []`, `start_pose`, `measured: None`.
   - `check(world: dict, car: dict | None = None) -> list[str]` returning violation codes (empty = ok):
     `schema` (missing key), `arena_size` (a side outside 2.0–2.5), `wall_height` (< 0.30), `tag_count`
     (outside 10–16), `tag_on_wall` (centre not on a wall segment within 1e-6), `tag_fits_on_wall`
     (centre closer than `border_size_m / 2` to a corner), `tag_spacing` (largest circular perimeter gap
     > 0.8), `tag_normal` (not the wall's inward normal ±1°), `tag_height` (only with `car`: `z_m` ≠
     `max(lens_height_m, 0.12)` ± 0.005), `tag_size` (black 0.16 ± 0.005, border 0.20 ± 0.005),
     `id_range` (a non-null wall ID outside 0–29), `roof_on_wall` (an ID 100–109 on a wall, or a
     `roof_tags` entry outside 100–109), `dup_unique` (`unique`/`hidden` with a repeated ID), `dup_count`
     (> 3 repeated IDs, or any ID three times), `dup_distance` (a pair < 1.5 m apart), `dup_list`
     (`duplicates` disagrees with the tags), `start_clearance` (< 0.5 m from a wall).
   - `transform_world_to_map(world) -> tuple[float, float, float]` = the SE(2) `T_map←world` of C1
     (inverse of the start pose) and `tags_in_map_frame(world) -> list[dict]` (`uid, id, x_m, y_m,
     normal_deg` in the map frame). Metrics (M2.T10) and kinsim use these.
   - CLI (`if __name__ == "__main__":` with `argparse`):
     `python -m beaconmind.worlds generate --condition duplicated --seeds 1000-1099 --out <dir> [--car <car.json>] [--n-dup 3]`
     (writes `<dir>/<world_id>.json`, prints one line per world) and
     `python -m beaconmind.worlds check <file> [<file> …] [--car <car.json>]` (prints `OK <world_id>` or
     `FAIL <world_id>: <codes>`, exits 1 if any fail).
4. *Mac.* Write `course-project/configs/seeds.json`:
   `{"schema": "bm.seeds/1", "status": "proposed default (M4.T1 freezes)", "dev": {"first": 1000,
   "last": 1099}, "test": {"first": 2000, "last": 2199}, "conditions": ["unique", "duplicated"],
   "n_dup": 3, "rule": "Prompt or DV tuning uses dev seeds only (README C7)."}`. Add
   `schemas/bm.seeds-1.schema.json` (type checks for these keys).
5. *Mac.* Write `course-project/tools/plot_worlds.py` (matplotlib; runs in the Spark host venv, which has
   the `metrics` extra): draws the arena rectangle, each tag as a short segment along its wall labelled
   with its ID (duplicated IDs in a second colour) and the start pose arrow; one PNG per call with 4
   worlds in a 2×2 grid.
6. *Mac.* Write the tests below; run them.
7. *Spark host.* Sync, then generate and check every seed and both conditions:
   ```bash
   cd ~/Projects/EN.665.715/course-project && mkdir -p data/worlds evidence/M2/M2.T2 && for c in unique duplicated; do \
     ~/.venvs/beaconmind/bin/python -m beaconmind.worlds generate --condition $c --seeds 1000-1099 --out data/worlds && \
     ~/.venvs/beaconmind/bin/python -m beaconmind.worlds generate --condition $c --seeds 2000-2199 --out data/worlds; done \
     > evidence/M2/M2.T2/generate.txt && ~/.venvs/beaconmind/bin/python -m beaconmind.worlds check data/worlds/*.json \
     | sort | uniq -c | awk '{print $2}' | sort | uniq -c > evidence/M2/M2.T2/check_summary.txt; cat evidence/M2/M2.T2/check_summary.txt
   ```
   Expected: `600 OK` (300 seeds × 2 conditions) and no `FAIL` line. Also
   `~/.venvs/beaconmind/bin/python tools/plot_worlds.py data/worlds/sim-dup-s100{0,1,2,3}.json --out evidence/M2/M2.T2/worlds_dup_1000-1003.png`.
8. *Spark → Mac.* `bash course-project/tools/pull_evidence.sh M2 M2.T2`. Show Xiaohui the PNG and ask the
   step-2 question.
9. Status, `CONTEXT.md`.

**Deliverables.** `src/beaconmind/worlds.py`; `configs/seeds.json`; `schemas/bm.seeds-1.schema.json`;
`tools/plot_worlds.py`; `tests/test_worlds.py`; `tests/fixtures/worlds/sim-dup-s1000.json` (one generated
world, tracked, for other tests).

**Tests.** `tests/test_worlds.py` (28):
- `test_generate_deterministic` — two calls give byte-identical `json.dumps(..., sort_keys=True)`.
- `test_seeds_differ` — seeds 1000 and 1001 differ.
- `test_conditions_share_geometry` — `unique` and `duplicated` of one seed have equal arena, tag positions
  and start pose.
- `test_all_dev_and_test_seeds_pass_check` — 300 seeds × 2 conditions, `check()` empty for each.
- `test_duplicated_has_n_dup_pairs_far_apart` — exactly 3 pairs, each ≥ 1.5 m, no ID three times.
- `test_unique_has_no_repeats`.
- `test_spacing_at_most_0_8` — largest circular gap ≤ 0.8 for all 600 worlds.
- `test_start_clearance` — ≥ 0.5 m from every wall.
- `test_normals_point_inward` — the unit normal dotted with (arena centre − tag) is > 0.
- `test_ids_in_range`.
- `test_world_id_format` — `sim-dup-s1003` for seed 1003 duplicated.
- `test_validates_against_schema` — `jsonschema.validate` against `bm.world-1`.
- `test_check_detects_violation[<code>]` — parametrized over 14 codes (`arena_size, wall_height,
  tag_count, tag_on_wall, tag_fits_on_wall, tag_spacing, tag_normal, tag_size, id_range, roof_on_wall,
  dup_unique, dup_count, dup_distance, start_clearance`): the unmutated fixture gives `[]`, and the
  fixture mutated to break that rule gives a list that **contains** `code` (some mutations necessarily
  break a second rule too: a third copy of an ID also breaks `dup_list`; so the test asserts membership,
  not equality). Mutation for `tag_count`: append wall tags with unused IDs until there are 17 (removing
  tags would also break `tag_spacing`).
- `test_tags_in_map_frame_hand_computed` — a 2.0 × 2.0 world with start pose (1.0, 1.0, 90°) and a tag
  at (1.0, 2.0) maps to (1.0, 0.0) in the map frame.
- `test_cli_generate_and_check` — subprocess run into `tmp_path`; exit 0; `OK` lines.
- Command (Mac): `../.venv/bin/python -m pytest -q tests/test_worlds.py` → `28 passed`.
- Smoke test (Spark host): step 7 → `600 OK`.

**Acceptance criteria.**
- [ ] `28 passed` on the Mac; full suite passes on the Spark host (and 3.10 or labelled).
- [ ] `check_summary.txt` shows `600 OK` and no `FAIL`.
- [ ] Xiaohui saw `worlds_dup_1000-1003.png` and answered step 2; answer in `CONTEXT.md`.

**Evidence to save** (`evidence/M2/M2.T2/`). `pytest_mac.txt`, `pytest_spark_host.txt`, `generate.txt`
(trim to the first and last 5 lines if > 1 MB), `check_summary.txt`, `worlds_dup_1000-1003.png`,
`n_dup_decision.md`.

**Pitfalls and known gotchas.** `round(x / 0.05) * 0.05` gives values like 2.1500000000000004; round the
result again to 2 decimals. The perimeter gap check must include the gap between the last and first tag.
`random.sample` order depends only on the RNG state, so keep the call order fixed. Do not use `hash()`
for seeding (salted per process).

**Stop-and-ask conditions.** Step 2 (`n_dup`). The generator cannot satisfy the constraints for some
seed within 100 tries (report the seed; do not loosen a D3 rule).

**Estimated effort.** S.

**AI-disclosure note.** `AI-assisted: <model> via <tool>, <date>: wrote the C7 world generator, checker, plot script and tests.`

---

### M2.T3 — Kinematic simulator (kinsim) with placeholder noise models and ground truth (C8)

**Why.** A pure-Python simulator with no rendering lets the harness, the baselines and the metrics be
built and tested before the Isaac twin exists, gives exact ground truth (C8), and is the documented
fallback if the twin fails (README §3.4 option (a), results labelled `source: "kinsim"`). It applies the
detector noise model (APPROACH §6: placeholder until the W2 pilot, then measured) and an odometry noise
model.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M2.T2 done | task | `grep -E "^. M2\.T2 " course-project/plan/M2-sim-mvp.md` (Mac) | Status `done` |
| M2.T13 done | task | `grep -E "^. M2\.T13 " course-project/plan/M2-sim-mvp.md` (Mac) | Status `done` |
| Measured car (optional) | config | `ls course-project/configs/car.json` (Mac) | listed → use it; absent → placeholder fixture |
| Measured noise (optional) | config | `ls course-project/configs/detector_noise.json` (Mac) | listed → use it; absent → placeholder fixture |

**Inputs.** README C1, C2, C3 ("Detection pipeline"), C7, C8, L4; AGENT-DESIGN D3 (HFOV 60° DV), D4;
`assignments/assignment4/system-prompt/tools/backstory_sim.py` (`detect`, `reliably_seen`,
`incidence_deg`: the visibility model idea and its DVs, 1.5 m and 60° incidence; noise N(0, 0.015 m),
N(0, 0.7°); odometry ×(1 + N(0, 0.02)) and turn + N(0, 0.3°)).

**Steps.**
1. *Mac.* README §1.2 steps 1–5.
2. *Mac.* Config loaders in `src/beaconmind/config.py`. **Why an adapter:** M1 writes `configs/car.json`
   in the `bm.car/1` form (a `values` map keyed by the **measured** quantities of M1.T9 step 3:
   `rollout_left_m` (roll-out superseded 2026-10-24), `track_outer_m`, `front_overhang_m`, `corners`,
   `lens_x_m`, …; M1.T2 step 6 schema
   table), `configs/camera.json` in the `bm.camera/1` form (with `hfov_deg` and `extrinsics` base_link →
   camera_optical_frame) and `configs/detector_noise.json` in the `bm.detector_noise/1` form
   (`range_sigma_m {a, b}`, `bearing_sigma_deg {a, b}`, a `p_detect` table, …). M2 code uses one flat
   **view** of each, built only here. Every other M2 step reads the view keys below and never reads the
   M1 files directly. Functions (standard library only):
   - `load_car(path=None, camera_path=None) -> dict`, `load_detector_noise(path=None, camera_path=None)
     -> dict`, `load_odometry_noise(path=None) -> dict`, `load_camera(path=None) -> dict` (the raw
     `bm.camera/1` object). Default paths: `course_root()/"configs"/<name>.json`.
   - If the file has `"schema": "bm.car/1"` (or `bm.detector_noise/1`), build the view with the mapping
     tables below; a per-value object `{"value": …}` is unwrapped to its value. If the file has no
     `schema` key and has every view key (the placeholder fixtures of step 3), use it as is.
   - Every view also carries `"status"` (`"measured"` or `"placeholder"`) and `"assumptions"`: a list of
     strings naming each value that came from a stated default instead of a measurement (the runner
     copies it into `run.json`, M2.T7 step 7). `KeyError` names every key that neither the file nor a
     stated default provides.
   - Helpers used everywhere a σ or p is needed: `range_sigma_m(noise, r)` = `range_sigma_a_m +
     range_sigma_b·r`; `bearing_sigma_deg(noise, r)` = `bearing_sigma_a_deg + bearing_sigma_b·r`;
     `range_bias_m(noise, r)` = `range_bias_a_m + range_bias_b·r`; `p_detect(noise, r, incidence_deg)` =
     the scalar `p_detect_per_frame` if the view has one, else the `p` of the `p_detect_table` row with the
     smallest `|Δr|/0.25 + |Δincidence|/15` (nearest neighbour; ties → the lower `p`).
     **Throughout this file, "`bearing_sigma_deg`" at range r means `bearing_sigma_deg(noise, r)` and
     "`a + b·r`" for range means `range_sigma_m(noise, r)`.**
   - `optical_to_link_rpy_deg(roll, pitch, yaw) -> [r, p, y]`: given the base_link → camera_optical_frame
     rotation (camera.json `extrinsics`, degrees, fixed-axis roll-pitch-yaw as URDF uses), returns the
     base_link → camera_link rotation, where camera_link → camera_optical_frame is the fixed REP 103
     rotation `rpy = (−90°, 0, −90°)`: `R_link = R_opt · R_fixed⁻¹`, converted back to URDF rpy.

   **Car view mapping** (`bm.car/1` `values` → view key; first source present wins):
   | View key | Source in M1 files | If absent |
   | --- | --- | --- |
   | `wheel_diameter_m` | `wheel_diameter_m` or `effective_diameter_m`; else mean(`rollout_left_m`, `rollout_right_m`) / (5π) (each rollout is 5 revolutions, M1.T9 step 3) (roll-out superseded 2026-10-24: M1.T9 writes the direct `wheel_diameter_m` and no `rollout_*` keys, so this fallback stays unused) | `KeyError` |
   | `track_width_m` | `track_width_m`; else (`track_outer_m` + `track_inner_m`) / 2 | `KeyError` |
   | `axle_to_front_m` | `front_overhang_m` | `KeyError` |
   | `axle_to_rear_m` | `rear_overhang_m` | `KeyError` |
   | `body_width_m` | `chassis_width_m` | `KeyError` |
   | `chassis_height_m`, `wheel_width_m` | same names | 0.06 and 0.025, with an `assumptions` entry (visual/inertia only) |
   | `sweep_radius_m` | `sweep_radius_m`; else max `hypot(x, y)` over `corners` (list of `[x, y]`) | `KeyError` |
   | `camera_xyz_m` | camera.json `extrinsics` `[x_m, y_m, z_m]`; else `[lens_x_m, lens_y_m, lens_z_m]` | `KeyError` |
   | `lens_height_m` | `camera_xyz_m[2]` | — |
   | `camera_rpy_deg` (camera_link, x forward) | `optical_to_link_rpy_deg(extrinsics roll, pitch, yaw)` | `[0, 0, 0]` with an `assumptions` entry (kinsim does not use it; Isaac tasks stop without camera.json) |
   | `imu_xyz_m` | `[imu_x_m, imu_y_m, imu_z_m]` | `KeyError` |
   | `mass_kg` | `mass_kg` (a number) | 0.8 with an `assumptions` entry (Isaac physics only; M1.T9 allows "not measured") |
   | `ticks_per_wheel_rev` | `counts_per_rev` or `ticks_per_wheel_rev` (mean of the two wheels if per-wheel) | 4320 (nominal, README §9.1) with an `assumptions` entry; harmless in simulation because the simulator encodes and decodes ticks with the same constant |
   | `caster_xyz_m` | `[caster_x_m, 0.0, caster_diameter_m/2 − wheel_diameter_m/2]` (caster contact-sphere centre relative to the axle) | `KeyError` |

   **Detector-noise view mapping** (`bm.detector_noise/1` → view key):
   | View key | Source | If absent |
   | --- | --- | --- |
   | `hfov_deg` | camera.json `hfov_deg` | 60.0 (D3 DV) with an `assumptions` entry |
   | `min_range_m`, `max_range_m`, `max_incidence_deg` | same names | `KeyError` |
   | `range_bias_a_m`, `range_bias_b` | `range_bias_m.a`, `range_bias_m.b` | 0, 0 with an `assumptions` entry |
   | `range_sigma_a_m`, `range_sigma_b` | `range_sigma_m.a`, `range_sigma_m.b` | `KeyError` |
   | `bearing_bias_deg` | `bearing_bias_deg` | 0 with an `assumptions` entry |
   | `bearing_sigma_a_deg`, `bearing_sigma_b` | `bearing_sigma_deg.a`, `bearing_sigma_deg.b` | `KeyError` |
   | `p_detect_table` | `p_detect` (list of `{range_m, incidence_deg, p}`) | `KeyError` |
   | `normal_sigma_deg` | `normal_sigma_deg` (M1.T8 does not measure it) | 10.0 with an `assumptions` entry (it only affects the wall-plane safety term) |

   Odometry-noise view: `wheel_scale_sigma, systematic_scale_left, systematic_scale_right, gyro_sigma_deg,
   gyro_scale` (the file of step 3, same names).

   **Verification step** (only if M1.T9 / M1.T8 are done): run
   `../.venv/bin/python -c "from beaconmind.config import load_car, load_detector_noise; c=load_car(); n=load_detector_noise(); print(c['status'], c['assumptions'], n['status'], n['assumptions'])"`.
   - It prints `measured … measured …` → continue; paste the assumptions list into `CONTEXT.md`.
   - A `KeyError` → the measured file lacks a quantity this table needs, or names it differently: stop and
     ask (§1.4 item 3) with the missing key list; do not guess the meaning of a key and do not edit the
     M1 file.
3. *Mac.* Placeholder files (each with `"status": "placeholder"` and a `"note"` saying it is not a
   measurement and must never appear in a reported result; they are written directly in the **view**
   form, so they need no mapping):
   - `beaconmind/tests/fixtures/car_placeholder.json` — stand-ins chosen only so the code runs:
     `wheel_diameter_m 0.065` (vendor figure, README §9.1), `ticks_per_wheel_rev 4320` (nominal, §9.1),
     `track_width_m 0.15, axle_to_front_m 0.17, axle_to_rear_m 0.05, body_width_m 0.17, chassis_height_m
     0.06, wheel_width_m 0.025, sweep_radius_m 0.20, lens_height_m 0.10, camera_xyz_m [0.15, 0.0, 0.10],
     camera_rpy_deg [0, 0, 0], imu_xyz_m [0, 0, 0.05], mass_kg 0.8, caster_xyz_m [0.13, 0.0, -0.02]`,
     `"assumptions": []`.
   - `beaconmind/tests/fixtures/detector_noise_placeholder.json` — `hfov_deg 60` (D3 DV),
     `min_range_m 0.25, max_range_m 1.5, max_incidence_deg 60` (the `backstory_sim.py` backstory DVs;
     0.25 m min range is a stand-in), `range_bias_a_m 0, range_bias_b 0, range_sigma_a_m 0.01,
     range_sigma_b 0.03` (≈ 0.055 m at 1.5 m; the literature analogue in
     `research/…/topic2-fiducial-slam-baseline.md` reports 3–5 cm at 1.3 m), `bearing_bias_deg 0,
     bearing_sigma_a_deg 1.0, bearing_sigma_b 0.0, normal_sigma_deg 10.0, p_detect_per_frame 0.95`,
     `"assumptions": []`.
   - `course-project/configs/odometry_noise.json` (tracked; M3.T8 replaces it) — `wheel_scale_sigma
     0.02, gyro_sigma_deg 0.3` (the `backstory_sim.py` values), `systematic_scale_left 1.0,
     systematic_scale_right 1.0, gyro_scale 1.0`, `"status": "placeholder"`, and its schema
     `schemas/bm.odometry_noise-1.schema.json`. **Note:** this file stays `placeholder` until M3.T8, so
     the "refuse placeholders" rule (M2.T7 step 9) checks only `car.json` and `detector_noise.json`;
     `odometry_noise.json`'s status is copied into `run.json` and stated as a limitation in M2.T12.
4. *Mac.* Create `src/beaconmind/envs/__init__.py`, `envs/base.py`:
   - `@dataclass class Capture: frames: list; sensors: dict; boot_id: int; gt_pose_world: dict | None`.
   - `class Env(Protocol)`: attribute `source: str`; methods `reset() -> None`, `capture() -> Capture`,
     `execute(command: dict) -> dict`, `gt_pose_world() -> dict | None`, `close() -> None`.
   - `make_move_command(action, *, cmd_seq, obs_id, dv, last_forward_achieved_m) -> dict` — the C2
     MoveCommand: `distance_m` 0.25 / 0.10 / `−min(0.10, last_forward_achieved_m)` / 0; `angle_deg` ±30
     for turns; `v_max_mps = dv["v_max_mps"]`, `w_max_dps = dv["turn_rate_dps"]`,
     `timeout_s = dv["move_timeout_s"]`.
5. *Mac.* Create `src/beaconmind/envs/kinsim.py` with `class KinSim` (`source = "kinsim"`):
   - `__init__(self, world, car, dv, detector_noise, odometry_noise, *, rng_key: str, faults: dict | None = None)`.
     `faults` keys (tests and robustness only): `link_lost_at_cmd_seq`, `reboot_at_cmd_seq`,
     `camera_down_steps` (list of capture indices).
   - Module-level pure functions (also used by M2.T6 and M2.T15): `tag_view_geometry(cam_x, cam_y,
     cam_yaw_deg, tag) -> tuple[float, float, float]` = (range from the camera, bearing off the camera
     axis in degrees, incidence in degrees) for one C7 tag; and `visible_uids(world, pose_world, car,
     noise) -> list[str]` = the uids that pass the HFOV, range and incidence tests below from the camera
     position of `pose_world` (no randomness, no detection probability).
   - Ground truth in the **world** frame; `gt_pose_world()` returns it; the map-frame pose is computed by
     the recorder with `worlds.transform_world_to_map` (C1, C8).
   - `capture()`: `dv["obs_frames"]` frames. A tag is visible in a frame when, from the **camera**
     position (`base + R(θ)·camera_xyz_m[:2]`), its bearing off the camera axis is within ±`hfov_deg/2`,
     its range is in [`min_range_m`, `max_range_m`], its incidence (angle between the tag normal and the
     tag→camera direction) is ≤ `max_incidence_deg`, and a Bernoulli(`config.p_detect(noise, r,
     incidence)`) draw succeeds.
     The convex, empty arena has no occlusion. Each visible tag gives a frame item in `base_link`: true
     range/bearing r, b from the axle midpoint, then `r + range_bias_m(noise, r) + N(0,
     range_sigma_m(noise, r))` and `b + bearing_bias_deg + N(0, bearing_sigma_deg(noise, r))`, converted
     back to `x_m, y_m`; `normal_yaw_deg = [ψ_a, ψ_b]` with `ψ_a` = true normal yaw in `base_link` +
     N(0, `normal_sigma_deg`) and `ψ_b = 2·φ − ψ_a` (φ = direction from the tag to the camera: the planar
     pose ambiguity mirrors the normal about the viewing ray); `id` (None in the `hidden` condition) and
     `uid`. RNG key per frame: `f"{rng_key}:det:{capture_index}:{frame}"`.
   - `execute(command)` → C2 MoveResult:
     - Arm state: `KinSim.reset()` sets `armed = True` (the simulated operator arm; recorded in the
       obslog header `notes` as "kinsim: armed at reset") and `latched = False`; `disarm()` and
       `estop()` (sets `latched = True`) exist for tests and for the runner's `emergency_stop` hook.
     - Disarmed or latched → `refused`. Fault `link_lost_at_cmd_seq` → `link_lost`, no motion. Fault
       `reboot_at_cmd_seq` → motion stops, `boot_id` + 1 on the next capture, result `link_lost`.
     - Forward/backward with signed distance `d`: per-move wheel errors `e_L, e_R ~ N(0,
       wheel_scale_sigma)`; true wheel travel `s_L = d·(1 + e_L)·systematic_scale_left`, `s_R` likewise;
       the true pose follows the constant-curvature arc (chord at mid-heading, the same formula as
       `observation.odometry_from_motion`). The executor stops on the encoders, so encoder-reported travel
       is `d` for both wheels (ticks = `round(d / (π·D) · ticks_per_wheel_rev)`); `gyro_dyaw_deg` = true dθ
       × `gyro_scale` + N(0, `gyro_sigma_deg`).
     - **Contact** (kinsim's stand-in for the Pico's bump detector, proposed default): if, along the arc,
       either front corner of the body (`axle_to_front_m` ahead, ±`body_width_m/2`; rear corners with
       `axle_to_rear_m` for backward) would cross a wall line, the motion stops at the first crossing; the
       result is `bumped`, `bump: true`, and the encoders report the travel up to that point plus 0.01 m.
     - Turn ±30°: if the minimum distance from the axle midpoint to any wall is < `sweep_radius_m`, the
       result is `stalled` with no rotation (proposed default); otherwise true dθ = ±30° + N(0,
       `gyro_sigma_deg`) (the executor stops on the gyro), wheels report ∓/± `track_width_m/2 · |dθ_gyro|`.
     - `duration_s = |d| / v_max_mps + 0.3` or `30 / w_max_dps + 0.3`; `boot_id`; `achieved_forward_m` =
       encoder mean.
   - `if __name__ == "__main__":` smoke CLI: `python -m beaconmind.envs.kinsim --world <file> --script
     scan --steps 20 [--car <file>] [--noise <file>]`, where `--script scan` turns left 12 times then
     alternates FORWARD_25 and TURN_LEFT_30; prints one line per step: step, gt pose (world), number of
     visible tags, move result.
6. *Mac.* Write the tests; run them.
7. *Mac → Spark host.* Sync; run the full suite on the Spark host venv; run the smoke CLI on
   `data/worlds/sim-dup-s1000.json` and save the output.
8. Evidence, status, `CONTEXT.md` (say that every kinsim number so far uses placeholder noise).

**Deliverables.** `src/beaconmind/config.py` (loaders); `src/beaconmind/envs/{__init__,base,kinsim}.py`;
`configs/odometry_noise.json`; `schemas/bm.odometry_noise-1.schema.json`;
`tests/fixtures/{car_placeholder,detector_noise_placeholder}.json`; `tests/test_kinsim.py`;
`tests/test_config_views.py`.

**Tests.** `tests/test_kinsim.py` (17):
- `test_reset_at_start_pose`.
- `test_capture_returns_obs_frames_frames`.
- `test_noise_free_capture_exact` — with all σ = 0 and `p_detect = 1`: every frame item equals the true
  `base_link` position within 1e-9, and the visible set equals a hand-computed set for the fixture world.
- `test_hfov_excludes_tag_at_35_deg`, `test_range_and_incidence_limits`.
- `test_duplicate_ids_distinct_uids` — both id-k tags visible from a chosen pose give distinct uids.
- `test_hidden_condition_ids_none`.
- `test_forward_noise_free` — 0.25 m straight; ticks = `round(0.25/(π·0.065)·4320)`; result `done`.
- `test_turn_noise_free` — θ + 30°, position unchanged.
- `test_backward_distance_from_command` — `BACKWARD_10` after a 0.06 m forward → −0.06 m.
- `test_bump_into_wall` — noise-free, start facing a wall head-on with the front corners 0.20 m from it
  (closer than the 0.25 m move): FORWARD_25 → `bumped`, `bump: true`, the true front at the wall within
  1e-6 m, and `achieved_forward_m` = 0.20 + 0.01 = 0.21 within 1e-6 (the encoder report includes the
  0.01 m of wheel spin defined in step 5).
- `test_turn_blocked_by_sweep` — axle 0.15 m from a wall → `stalled`, θ unchanged.
- `test_disarmed_refuses`.
- `test_fault_link_lost_and_reboot` — results `link_lost`; the next `capture().boot_id` is incremented.
- `test_same_rng_key_same_outputs`.
- `test_config_views` (in `tests/test_config_views.py`, 6 tests, counted separately below):
  `test_car_view_from_bm_car_fixture` (a synthetic `bm.car/1` file in `tmp_path` with rollouts 1.021 m
  each, track outer 0.180 / inner 0.130, `corners` `[[0.1, 0.05], [-0.12, 0.09]]` → `wheel_diameter_m`
  0.0650 within 1e-4, `track_width_m` 0.155, `sweep_radius_m` 0.15; `status "measured"`),
  `test_car_view_missing_key_lists_all` (drop `front_overhang_m` and `imu_x_m` → one `KeyError` whose
  message names both), `test_car_view_defaults_recorded` (no `mass_kg`, no `counts_per_rev` → 0.8 and
  4320 and two `assumptions` entries), `test_optical_to_link_identity` (optical rpy (−90, 0, −90) → link
  (0, 0, 0) within 1e-9), `test_noise_view_from_bm_detector_noise` (`range_sigma_m {a: 0.01, b: 0.02}` →
  `range_sigma_m(view, 1.0)` = 0.03; `bearing_sigma_deg {a: 0.5, b: 0.5}` → 1.0 at 1 m),
  `test_p_detect_nearest_row` (table rows (0.5 m, 0°, 0.99) and (1.5 m, 45°, 0.6); query (1.4, 40) →
  0.6). Command: `../.venv/bin/python -m pytest -q tests/test_config_views.py` → `6 passed`.
- `test_noise_statistics` — 2,000 frames of one tag at 1.0 m: sample std of range within ±15 % of
  `a + b·1.0`; sample std of bearing within ±15 % of `bearing_sigma_deg`.
- `test_builder_integration_noise_free` — `ObservationBuilder` (M2.T13) over 15 scripted steps: every C3
  key present, odometry composed from step 0 equals the true map-frame pose within 1e-6 m (builder with
  `round_outputs=False`).
- Command (Mac): `../.venv/bin/python -m pytest -q tests/test_kinsim.py` → `17 passed`.
- Smoke test (Spark host): `cd ~/Projects/EN.665.715/course-project && ~/.venvs/beaconmind/bin/python -m
  beaconmind.envs.kinsim --world data/worlds/sim-dup-s1000.json --script scan --steps 20 --car
  beaconmind/tests/fixtures/car_placeholder.json --noise beaconmind/tests/fixtures/detector_noise_placeholder.json`
  → 20 lines and no traceback; during the 12 scan turns the visible-tag count is > 0 on at least 6 of
  them. (With a 1.5 m placeholder range limit, a start pose near a corner legitimately sees nothing
  toward the far corner, so the bound is loose.) If fewer than 6: print the start pose and, for each
  heading, `visible_uids(...)` and the distance to every tag; it is a bug only if a tag within 1.5 m,
  ±30° of the camera axis and ≤ 60° incidence is missing on a noise-free re-run (`--noise` with all σ 0
  and `p_detect_per_frame` 1).

**Acceptance criteria.**
- [ ] `17 passed` (`test_kinsim.py`) and `6 passed` (`test_config_views.py`) on the Mac; full suite on the
      Spark host (3.10 or labelled).
- [ ] If M1.T8/M1.T9 are done: the verification step of step 2 printed `measured` for both views, and
      the `assumptions` lists are pasted in `CONTEXT.md`.
- [ ] Smoke output saved and meets the stated pass condition.
- [ ] Every placeholder file says `"status": "placeholder"`.

**Evidence to save** (`evidence/M2/M2.T3/`). `pytest_mac.txt`, `pytest_spark_host.txt`,
`kinsim_smoke.txt`.

**Pitfalls and known gotchas.** Wall crossings must use the body corners, not the axle point (the
axle-to-front overhang is the whole reason for `forward_wall_limit_m`). Keep world-frame truth and
map-frame truth apart; C8 files are in the map frame. The mirrored normal is an approximation of the
pose ambiguity — say so in the docstring.

**Stop-and-ask conditions.** Step 2 `KeyError` on a measured file. The contact model or the sweep rule
would need a value not in `car.json` or `dv.json`.

**Estimated effort.** M (two sessions: steps 1–4 and capture; execute, tests, smoke).

**AI-disclosure note.** `kinsim.py`: `AI-assisted: <model> via <tool>, <date>: wrote the kinematic simulator.`
plus `Derived from: EN.665.715/assignments/assignment4/system-prompt/tools/backstory_sim.py:detect,reliably_seen (reimplemented)`.

---
### M2.T7 — Harness core: neutral step loop, vLLM provider, prompt loader, budget guard, run logs, replay and closed loop

**Why.** The benchmark harness (AGENT-DESIGN D10 "Harness": a custom harness exposing only the D5 tools;
APPROACH §10 W5) sends the v3.3 system prompt plus one stateless step message, runs the model's tool
turns against `dispatch()`, corrects the report, executes at most one move, and logs everything in the
C9.2 format with the hashes that make results comparable (L8). Replay (D1d) and closed loop share one
loop. This task delivers the loop with the **vLLM** provider (the local model, no money); the frontier
providers are M2.T18.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M2.T1, M2.T3, M2.T13, M2.T14 done | task | `grep -E -e "^. M2\.T1 " -e "^. M2\.T3 " -e "^. M2\.T13 " -e "^. M2\.T14 " course-project/plan/M2-sim-mvp.md` (Mac) | four rows, each with Status `done` |
| Run-log and obslog schemas | code | `ls course-project/beaconmind/src/beaconmind/schemas/bm.runlog-1.schema.json course-project/beaconmind/src/beaconmind/schemas/bm.obslog-1.schema.json` (Mac) | both listed (M1.T2) |
| vLLM container exists | service | `ssh -o BatchMode=yes -o ConnectTimeout=15 xiaohui_chen@spark-2a60 'docker ps -a --format "{{.Names}} {{.Status}}" \| grep vllm-rosa'` (Mac) | a `vllm-rosa` line (Exited is fine; step 9 starts it) |
| `beaconmind-ros` exists (for the 3.10 runs) | service | `ssh … 'docker ps -a --format "{{.Names}}" \| grep -x beaconmind-ros'` (Mac) | `beaconmind-ros`; if absent, the container steps are labelled "not executed" |
| M1.T4 result (closed-loop setting, OD8) | task | `grep -E "^. M1\.T4 " course-project/plan/M1-foundations.md` (Mac) | Status `done`; if not, the smoke uses the instruct setting and no closed-loop result may be reported from this task |
| M1.T11 done, **or** the waiver recorded | task / decision | `grep -E "^. M1\.T11 " course-project/plan/M1-foundations.md; grep -n "M1.T11 waiver for M2.T7" course-project/CONTEXT.md` (Mac) | M1.T11 Status `done`, or a `CONTEXT.md` line `M1.T11 waiver for M2.T7–T10: yes, <date>` (README §3.3; see "What does not wait"). Neither → stop and ask the waiver question |

**Inputs.** README C3, C4, C5, C9 (whole), C10.8, C11, L5, L8, L9; AGENT-DESIGN D1d, D5, D10;
`assignments/assignment4/system-prompt/tools/smoke_test.py` (`step`, `SAMPLING`, `HARNESS`, the thinking
replay, error handling); `discussions/module2/vllm-serve.sh` (server flags: `--tool-call-parser
qwen3_coder --reasoning-parser qwen3`, `--max-num-batched-tokens 4096`); AGENTS.md §7.4 (vLLM row,
memory rule).

**Steps.**
1. *Mac.* README §1.2 steps 1–5.
2. *Mac.* Freeze the prompt. Create `src/beaconmind/harness/__init__.py` and `harness/prompt.py` with
   `SOURCE = "assignments/assignment4/system-prompt/evidence/print-output.txt"`,
   `FROZEN = "course-project/configs/prompt/robot_prompt_v3.3.txt"`,
   `extract_final_prompt(text) -> str` (the text after `=== FINAL PROMPT ===`, `.strip()`, as
   `smoke_test.py` `__main__` does), `freeze() -> Path` (writes `FROZEN` from `SOURCE`), and
   `load_system_prompt(path=None) -> tuple[str, str]` (text and `sha12`). Run
   `../.venv/bin/python -c "from beaconmind.harness.prompt import freeze; print(freeze())"`. **Verification
   step:** `md5` of the frozen text must be `3b78a2301cf261379a51e6871574f0fa` and its SHA-256 first 12
   hex `d0b75b25a86e` (checked by the writer on 2026-10-05). Different → stop and ask (§1.4 item 3): the
   v3.3 prompt changed.
3. *Mac.* Provider config. If `configs/providers.json` exists (M1.T11), check that it has
   `qwen35-a3b-think` and `qwen35-a3b-instruct`; add whichever is missing; if the file does not exist,
   create it with only these two (M1.T11 adds the frontier entries). Exact entries (C11; sampling from
   `smoke_test.py` `SAMPLING` = the model card, D10):
   ```json
   "qwen35-a3b-think": {"provider": "vllm", "base_url": "http://127.0.0.1:8000/v1", "model": "Qwen/Qwen3.5-35B-A3B",
     "api_key_env": null, "thinking": true,
     "sampling": {"temperature": 1.0, "top_p": 0.95, "top_k": 20, "presence_penalty": 1.5},
     "price_usd_per_mtok": {"input": 0, "cached_input": 0, "output": 0}, "price_checked": null,
     "max_turns_per_step": 30, "request_timeout_s": 900, "options": {}},
   "qwen35-a3b-instruct": {… same, "thinking": false,
     "sampling": {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "presence_penalty": 1.5} …}
   ```
4. *Mac.* `harness/providers/base.py`: dataclasses `ToolCall(id: str, name: str, arguments: str)`,
   `ProviderTurn(text, tool_calls, finish_reason, tokens_in, tokens_out, tokens_reasoning,
   tokens_cached_in, reasoning, raw, latency_s)` and `class ProviderError(Exception)` with attribute
   `kind` ∈ `context_overflow`, `bad_request`, `api_error`, `timeout`. **Neutral message list** (each
   provider converts it to its wire format, so C11's single `call()` signature holds):
   `{"role": "user", "content": str}`; `{"role": "assistant", "text": str | None, "reasoning": str |
   None, "tool_calls": [{"id", "name", "arguments"}], "raw": <provider payload> | None}`;
   `{"role": "tool", "tool_call_id": str, "name": str, "content": str}`.
   Also `get_call(entry) -> Callable` that imports `beaconmind.harness.providers.<entry["provider"]>`
   lazily and returns its `call`.
5. *Mac.* `harness/providers/vllm.py` (imports `openai` inside functions only):
   - `build_request(entry, system_text, messages, tools) -> dict` — `model`, `messages` = one system
     message then the converted list (assistant turns with tool calls in OpenAI Chat form; when
     `entry["thinking"]` and the turn has reasoning, prefix the content with `"<think>\n" + reasoning +
     "\n</think>\n\n"` exactly as `smoke_test.py` does), `tools` = `[{"type": "function", "function":
     spec} for spec in tools]`, `temperature`, `top_p`, `presence_penalty`, and `extra_body =
     {"chat_template_kwargs": {"enable_thinking": entry["thinking"]}, "top_k": …}`. **No `max_tokens`**
     (D10: no output cap below the server window).
   - `parse_response(raw: dict, latency_s: float) -> ProviderTurn` — from `response.model_dump()`:
     content, tool calls, `finish_reason`, usage (`prompt_tokens`, `completion_tokens`,
     `completion_tokens_details.reasoning_tokens` if present else 0, `prompt_tokens_details.cached_tokens`
     if present else 0), reasoning from `message["reasoning"]` or `message["reasoning_content"]`.
   - `call(entry, system_text, messages, tools) -> ProviderTurn` — `openai.OpenAI(base_url=…,
     api_key="none", timeout=entry["request_timeout_s"])`; map `BadRequestError` whose text mentions
     "context length" to `ProviderError("context_overflow")`, other `BadRequestError` to `bad_request`,
     `APITimeoutError` to `timeout`, other `APIError` to `api_error`.
   - `harness/providers/fake.py` — `call(entry, …)` that returns scripted `ProviderTurn`s from
     `entry["script"]`: a dict `{step_index: [turn, …]}` where the step index is read from the user message
     JSON (`OBSERVATION.step`) and the turn index is the number of assistant messages already in
     `messages`. Used by tests and by the `SCRIPT_SCAN` test policy.
6. *Mac.* `harness/budget.py`. **M1.T11 owns this file** (its step 5 writes `BudgetExceeded`,
   `estimate_cost_usd(usage, price)`, `class BudgetGuard(cap_usd, ledger_path)` with `check(reserve_usd)`,
   `record(usage, price, label)` and `spent_usd`, plus `tests/test_budget.py`). **Verification step:**
   `grep -nE "class BudgetGuard|def estimate_cost_usd|class BudgetExceeded" src/beaconmind/harness/budget.py`.
   - All three found → do **not** rewrite them; only append the code below.
   - File absent (M1.T11 not done; allowed only under the waiver in the prerequisites) → create it with
     exactly M1.T11 step 5's API and docstrings (read `plan/M1-foundations.md` M1.T11 step 5), so that
     M1.T11 later finds it done, then append the code below. Do not create `tests/test_budget.py` (M1.T11's
     file name); M2's tests go in `tests/test_budget_run.py`.
   - Anything else (other names) → stop and ask (§1.4 item 3).
   Append (standard library only):
   - `entry_cost_usd(entry, usage) -> float` = `estimate_cost_usd(usage, entry["price_usd_per_mtok"])`
     (C10.8; `usage` has `tokens_in, tokens_cached_in, tokens_out`).
   - `class RunBudget(run_cap_usd: float, run_ledger: Path, global_ledger: Path, global_cap_usd: float =
     100.0)` — two `BudgetGuard`s: one per run (`data/runs/<run_id>/spend.jsonl`) and one shared by every
     run (`data/budget/ledger.jsonl` on the Spark, git-ignored — the **one project spend ledger**, README
     contract C13), which enforces the $100 frontier pilot cap (AGENT-DESIGN "API budget"). Every line the
     global guard writes carries the C13 keys with `phase: "m2"`; if the file does not exist yet, create it
     and first append the `m1_spike` entry (C13: the total of `data/api_spike/ledger.jsonl`, read from
     `evidence/M1/M1.T11/ledger-total.txt`; if M1.T11 is not done, no entry). Methods: `check_before_call(reserve_usd)` (calls `check` on both; either
     raises `BudgetExceeded`), `charge(entry, usage, label) -> float` (if every price in the entry is 0,
     returns 0.0 and writes **no** ledger line; else `record`s on both guards and returns the cost),
     `spent_usd` (the run guard's). `reserve_usd` = the cost of the previous call in this step, or for the
     first call `entry_cost_usd(entry, {"tokens_in": 8000, "tokens_cached_in": 0, "tokens_out": 2000})`.
     M1.T11's spike spend **is** part of the $100 pilot total (C13 group `pilot` = `m1_spike` + `m2` + `gate`
     + `pilot`); the global guard's cap is therefore checked against the whole `pilot` group of the shared
     ledger. Say so in `CONTEXT.md` when the first paid run starts.
7. *Mac.* Logs. `harness/runlog.py`: `RunWriter(run_dir, header)` writes `run.json` (C9.2 header: `arm`,
   `model_key`, `provider_entry` (the entry with `api_key_env` but never a key value), `prompt_sha12`,
   `tool_schema_sha12`, `dv_sha12`, `car_sha12`, `noise_sha12`, `harness_files` (`{relative path: sha12}`
   for every `.py` under `src/beaconmind/`), `git_head` (`git rev-parse --short HEAD` or `null`),
   `seeds`, `k`, `budget_usd`, `mode`, `source`, `placeholders` (list of placeholder configs used),
   `assumptions` (the union of the car and noise views' `assumptions`, M2.T3 step 2),
   `odometry_noise_status` (`placeholder` until M3.T8),
   `server` (vLLM: `max_model_len` from `/v1/models` as `smoke_test.py` reads it), `started_utc`,
   `ended_utc`, `host`); `EpisodeWriter(run_dir, episode_id)` with `step(record)` and `footer(steps,
   ended_by, detail, totals)`. `harness/obslog.py`: `ObsLogWriter(path, header)` (C9.1 header, step,
   footer) and `write_tum(path, poses: list[tuple[int, dict]])` (C8 TUM lines: `step tx ty 0 qx qy qz qw`
   with `qz = sin(θ/2)`, `qw = cos(θ/2)`). `envs/replay.py`: `ObsLogReader(path)` with `.header`,
   `.steps`, `.footer`. If `jsonschema` is importable, the writers validate the first step record and the
   header against the schemas and raise on failure.
8. *Mac.* `harness/runner.py`:
   - `class Policy(Protocol)`: `decide(step_message: dict, ctx: StepContext) -> dict` returning
     `{"final_text", "llm_turns", "error", "decision_latency_s", "cost_usd"}`.
   - `class LLMPolicy` (`__init__(entry, system_text, budget)`): implements the step loop of
     `smoke_test.py` `step()` with the neutral messages: up to `entry["max_turns_per_step"]` turns; before
     each call `budget.check_before_call(...)`; a `finish_reason == "length"` turn ends the step with error
     `"length"` and **its tool calls are not executed**; tool arguments that are not valid JSON are passed
     to `dispatch` as `None` (so they become `invalid_tool_call`); each turn is logged with the C9.2
     `llm_turns` fields (`turn, t_start, latency_s, finish_reason, tokens_in, tokens_out,
     tokens_reasoning, tokens_cached_in, tool_calls`); `decision_latency_s` = wall time from the first
     request to the end of the last turn; turn cap → error `"turn cap"`; `ProviderError` → error
     `"<kind>: <first 300 chars>"`; `BudgetExceeded` → re-raised to the episode loop.
   - `class ScriptScanPolicy` (tests and smoke only): calls `move(TURN_LEFT_30)` through `dispatch` for 12
     steps, then alternates `FORWARD_25` (when allowed) and `TURN_LEFT_30`, and writes a minimal valid
     report built with `report.initial_memory()` and pose from `compose_odometry`.
   - `run_episode(*, policy, arm, env, log_reader, mode, mission, steps_budget, builder, episode_writer,
     obslog_writer=None, latch, dv, operator_requests=None, prev_report=None, world=None) -> dict` with
     the loop: capture (closed loop) or logged step (replay) → `builder.build` / `builder.rebuild_for_replay`
     → step message `{"mission", "operator_request", "OBSERVATION", "PREVIOUS_REPORT"}` → `StepContext`
     (executor = a closure that builds the C2 command with `make_move_command`, calls `env.execute`, and
     remembers `{"command", "result"}`; `None` in replay) → `policy.decide` → `report.parse_final_text` →
     `report.correct_report` → write the C9.2 step line (all fields of the C9.2 example, including
     `gt_pose_map`, `det_truth`, `violations` = `ctx.violations` + the report violations, `executed_move`)
     → `prev_report = corrected`. **Replay episodes run to the end of the log** (every arm sees the same
     steps, so ATE is comparable): in `mode: replay` a `DONE`, `STOPPED`, `ASK` or `REFUSED` decision is
     logged but does not end the episode; only the log end (`"DONE"`, detail `"log_end"`), the USD budget
     or three consecutive policy errors end it. **Closed loop** ends when the corrected decision is
     `DONE` (`ended_by "DONE"`) or `STOPPED`; the latch is set (`"latch"`); `steps_left` reached 0 (`"budget"`, detail `"steps"`);
     `BudgetExceeded` (`"budget"`, detail `"usd"`); three consecutive steps with a policy error
     (`"error"`); replay log exhausted (`"DONE"`, detail `"log_end"`). A corrected
     `requested_mission` switches the mission at the next step (`builder.start_mission`, D2). Returns the
     final corrected report and the footer.
   - Mission chain helper `choose_goto_target(report_map, world) -> str | None`: among the agent's
     **confirmed** beacons whose ID appears exactly once in the world (go-to targets use unique IDs, talk
     track), the label with the largest straight-line distance from the agent's current pose; ties → the
     smaller ID; none → `None` (the GO_TO episode is skipped and the skip is logged in `run.json`).
   - Replay: the mission is `EXPLORE` for every M2 observation log (they are recorded EXPLORE episodes;
     the obslog header's `notes` says so); `last_move` is the recorded executed move; any `move` is refused
     (C5.1) and the expected decision is `NONE` (D1d).
9. *Mac.* `harness/run.py` CLI (argparse):
   ```
   python -m beaconmind.harness.run --arm L2 --model <key> --mode replay --obslogs <f> [<f> …] --k 1 --budget-usd 0 --out data/runs [--parallel 4] [--max-steps N]
   python -m beaconmind.harness.run --arm L2 --model <key> --mode closed_loop --env kinsim --worlds <f> [<f> …] --missions EXPLORE,GO_TO_BEACON,RETURN_TO_START --k 1 --budget-usd 0 --out data/runs [--record-obslog data/obslogs] [--allow-placeholder]
   ```
   `--arm` ∈ `L2`, `SCRIPT_SCAN` (and `B0`, `B2` after M2.T8). `run_id` = `<YYYYMMDD-HHMMSS>-<arm>-<model_key>`
   (L2 naming; `model_key` = `none` for non-LLM arms). `--parallel` runs episodes in a
   `ThreadPoolExecutor` (vLLM serves at most `MAX_SEQS` = 4 requests at once). Without
   `--allow-placeholder`, the CLI refuses to start (exit 2, message naming the file) when
   `configs/car.json` or `configs/detector_noise.json` is missing, or when the M2.T3 view of either
   (`config.load_car()["status"]`, `config.load_detector_noise()["status"]`) is `placeholder`. With
   `--allow-placeholder` and a missing file, it uses the M2.T3 placeholder fixtures and lists them in
   `run.json` `placeholders`. `--record-obslog` writes the
   C9.1 log and the `.gt.tum` of each closed-loop episode with header `driver` = `"L2:<model_key>"` or the
   arm; in the **file name** the colon becomes a hyphen (`<world_id>-L2-<model_key>-k1.jsonl`), so names
   stay portable to the Mac.
10. *Mac.* Write the tests below (using `fake.py` and kinsim); run them.
11. *Spark host.* Start the local model (no money): check the memory rule first:
    `ollama ps` must list no model (AGENTS.md §7.4 memory rule); if one is listed, stop and ask before
    `ollama stop <model>`. Then `docker start vllm-rosa` and wait until
    `curl -sf http://127.0.0.1:8000/v1/models | python3 -m json.tool | grep -E '"id"|max_model_len'` shows
    `Qwen/Qwen3.5-35B-A3B` and `131072` (poll every 20 s, at most 8 minutes; it took about 4 minutes in
    September). Record the server flags:
    `docker inspect vllm-rosa --format '{{json .Args}}' > evidence/M2/M2.T7/vllm_args.json` and confirm it
    contains `qwen3_coder` and `qwen3` (the tool and reasoning parsers). Missing → stop and ask.
12. *Spark container `beaconmind-ros`.* **Verification step:**
    `docker exec beaconmind-ros bash -lc 'python3 -c "import openai; print(openai.__version__)"'`. A
    version → continue. `ModuleNotFoundError` → the M1.T3 image lacks the `providers` extra: stop and ask
    (do not `pip install` into a running container without recording it in the Dockerfile).
13. *Spark container `beaconmind-ros`.* Record provider fixtures (one tiny request each with the tool
    list; no secrets): `python3 -m beaconmind.harness.providers.vllm --record
    /workspace/course-project/beaconmind/tests/fixtures/providers/ --model-key qwen35-a3b-instruct` and
    the same with `qwen35-a3b-think`; this writes `vllm_tool_call_<key>.json` and
    `vllm_final_<key>.json` (raw `model_dump()`), which the unit tests parse. Add this `--record`
    function to `vllm.py` (`__main__` block): system prompt = the frozen prompt, user = the S1 scenario
    step message from `tests/fixtures/smoke_v33/scenarios.json`; save the first response (expected to
    contain tool calls) and, for the final fixture, continue the loop with `dispatch` until a final
    answer or 30 turns.
14. *Spark container `beaconmind-ros`.* Live smoke tests (marker `llm`):
    `docker exec beaconmind-ros bash -lc 'cd /workspace/course-project/beaconmind && python3 -m pytest -q -m llm tests/test_llm_vllm_live.py'`.
15. *Spark container `beaconmind-ros`.* End-to-end smoke in kinsim and replay (placeholders allowed,
    results not reportable):
    ```bash
    cd /workspace/course-project && python3 -m beaconmind.harness.run --arm SCRIPT_SCAN --mode closed_loop --env kinsim \
      --worlds data/worlds/sim-dup-s1000.json --missions EXPLORE --k 1 --budget-usd 0 --out data/runs \
      --record-obslog data/obslogs --allow-placeholder --max-steps 15
    python3 -m beaconmind.harness.run --arm L2 --model qwen35-a3b-instruct --mode replay \
      --obslogs data/obslogs/sim-dup-s1000-SCRIPT_SCAN-k1.jsonl --k 1 --budget-usd 0 --out data/runs --max-steps 5 --allow-placeholder
    python3 -m beaconmind.harness.run --arm L2 --model qwen35-a3b-instruct --mode closed_loop --env kinsim \
      --worlds data/worlds/sim-dup-s1000.json --missions EXPLORE --k 1 --budget-usd 0 --out data/runs --max-steps 5 --allow-placeholder
    ```
    Then summarise each run: `python3 -m beaconmind.harness.summarize data/runs/<run_id>` — add this small
    CLI (`harness/summarize.py`): per episode, steps, `ended_by`, decisions, violation counts by code,
    median and max `decision_latency_s`, tokens in/out. Paste the three summaries.
16. *Spark → Mac.* Pull evidence; sync the new fixtures back to the Mac (they were written on the Spark):
    `ssh … 'cd ~/Projects/EN.665.715 && tar czf - course-project/beaconmind/tests/fixtures/providers' | tar xzf - -C /Users/xiaohuichen/Projects/EN.665.715`.
    Re-run the Mac unit tests. Stop `vllm-rosa` only if Xiaohui asks (it is shared; record its state in
    `CONTEXT.md`).

**Deliverables.** `src/beaconmind/harness/{__init__,prompt,budget,runlog,obslog,runner,run,summarize}.py`;
`harness/providers/{__init__,base,vllm,fake}.py`; `src/beaconmind/envs/replay.py`;
`configs/prompt/robot_prompt_v3.3.txt`; `configs/providers.json` (vLLM entries);
`tests/test_prompt.py`, `test_providers_vllm.py`, `test_budget_run.py`, `test_runner.py`, `test_obslog.py`,
`test_llm_vllm_live.py`; `tests/fixtures/providers/*.json`.

**Tests.**
- `tests/test_prompt.py` (3): `test_frozen_prompt_md5` (= `3b78a2301cf261379a51e6871574f0fa`, the full hex digest; reviewer re-checked 2026-10-06), `test_frozen_prompt_sha12`
  (= `d0b75b25a86e`), `test_freeze_matches_source` (skips with `pytest.skip("v3.3 source not on this
  machine")` when `SOURCE` does not exist: the L6 sync copies only `course-project/`, and the Spark has no
  `assignments/assignment4/` checkout — checked 2026-10-06; it therefore runs only on the Mac).
- `tests/test_providers_vllm.py` (6): `test_request_system_first_no_max_tokens`,
  `test_request_thinking_flag_and_top_k_in_extra_body`, `test_request_replays_reasoning_as_think_block`,
  `test_parse_tool_call_fixture` (non-empty `tool_calls`, `finish_reason == "tool_calls"`, token counts >
  0), `test_parse_final_fixture` (`finish_reason == "stop"`, text parses with `report.parse_final_text`
  or the test reports the parse error), `test_parse_length_finish_reason` (a synthetic raw dict).
  The two `test_parse_*_fixture` tests read the step-13 fixtures; until they exist they are skipped with
  `pytest.skip("record fixtures in M2.T7 step 13")`. The other four need no fixture.
- `tests/test_budget_run.py` (6): `test_entry_cost_with_cache` (entry prices input 4, cached 0.4, output
  20; usage 1,000,000 in of which 400,000 cached, 100,000 out → 2.4 + 0.16 + 2.0 = 4.56),
  `test_entry_cached_price_none_uses_input`, `test_local_model_costs_zero_and_writes_no_line`,
  `test_check_before_call_raises_at_run_cap`, `test_global_ledger_cap_across_runs` (two `RunBudget`s with
  different run ledgers and one global ledger whose total is 99.5: a 1.0 reserve raises),
  `test_charge_writes_both_ledgers`.
- `tests/test_runner.py` (12, fake provider + kinsim + `tmp_path`): `test_replay_done_does_not_end_episode`
  (a scripted `DONE` at replay step 1 of a 4-step log → 4 step lines, footer `ended_by "DONE"`, detail
  `"log_end"`),
  `test_step_executes_tool_calls_then_final`, `test_step_turn_cap_error`,
  `test_length_turn_does_not_execute_tools`, `test_bad_json_arguments_invalid_tool_call`,
  `test_closed_loop_episode_writes_valid_runlog` (2 turns + DONE → 3 step lines + footer, schema-valid),
  `test_replay_refuses_moves_logs_guardrail`, `test_replay_recomputes_counters_from_own_reports`,
  `test_previous_report_is_the_corrected_report`, `test_mission_chain_switch_resets_steps_left`,
  `test_run_header_has_hashes_and_no_key_values` (`OPENAI_API_KEY=sk-test` set in the environment; the
  string `sk-test` appears nowhere under `run_dir`), `test_budget_exceeded_ends_episode`.
- `tests/test_obslog.py` (4): `test_writer_reader_roundtrip`, `test_header_fields_c9_1`,
  `test_tum_format_and_quaternion`, `test_footer_written`.
- Command (Mac): `../.venv/bin/python -m pytest -q tests/test_prompt.py tests/test_providers_vllm.py
  tests/test_budget_run.py tests/test_runner.py tests/test_obslog.py` → `31 passed` (before step 13 the two
  fixture-parsing tests skip: `29 passed, 2 skipped`; after step 16 it must be `31 passed`).
- Live smoke (`-m llm`, container), `tests/test_llm_vllm_live.py` (2):
  `test_vllm_returns_structured_tool_calls` (one request with the S1 step: `finish_reason ==
  "tool_calls"`, at least one parsed tool call, and the string `<tool_call>` absent from the content —
  proof the server's tool parser is active), `test_vllm_one_replay_step_parses` (one full `LLMPolicy`
  step on S1 with `qwen35-a3b-instruct`: final text parses, `correct_report` returns ≤ 2 violations).
  Expected: `2 passed`.
- End-to-end smoke (step 15): the SCRIPT_SCAN run ends with 15 steps and a valid obslog; the replay run's
  5 decisions are all `NONE` after correction and every `move` attempt (if any) is refused; the
  closed-loop run executes ≤ 1 move per step. Paste the summaries.

**Acceptance criteria.**
- [ ] `31 passed` on the Mac after the fixtures are pulled back; full suite passes on the Spark host and in
      `beaconmind-ros`.
- [ ] `2 passed` for the live `llm` tests; `vllm_args.json` shows both parsers.
- [ ] The three smoke summaries are saved; `run.json` of each contains all header fields and no key value
      (`grep -nE "sk-|api_key\"\s*:\s*\"[^n]" run.json` prints nothing).

**Evidence to save** (`evidence/M2/M2.T7/`). `pytest_mac.txt`, `pytest_spark_host.txt`, `pytest_py310.txt`,
`pytest_llm_live.txt`, `vllm_args.json`, `vllm_models.json` (the `/v1/models` output),
`smoke_script_scan.txt`, `smoke_replay_l2.txt`, `smoke_closed_loop_l2.txt`, `run_json_example.json` (one
`run.json`, after the secrets check).

**Pitfalls and known gotchas.**
- vLLM must be started with `--max-num-batched-tokens 4096` for Qwen3.5 (AGENTS.md §7.4); `docker start`
  keeps the last arguments, recreate only with `GPU_UTIL=0.60 MAX_LEN=131072 MAX_SEQS=4 ./vllm-serve.sh
  start` from `discussions/module2/` and only if Xiaohui agrees.
- vLLM and a 94 GB Ollama model cannot be resident together (memory rule).
- Never pass `max_tokens`; a `length` finish means the window ran out — record it, do not retry silently.
- A thinking-mode tool loop must replay the reasoning (`<think>` block) or Qwen loses its plan (smoke-test
  round 2 finding, `smoke_test.py` docstring).
- The SCRIPT_SCAN arm and placeholder configs exist for plumbing only; never report their numbers.
  `SCRIPT_SCAN` is not one of C9.1's drivers (`B2`, `operator`, `L2:<model_key>`); its logs are test data.
- `ThreadPoolExecutor` episodes must not share a `StepContext`, a `Latch` file or an `ObservationBuilder`.

**Stop-and-ask conditions.** The prompt hash differs (step 2). Ollama holds a model (step 11). The parser
flags are missing (step 11). `openai` is absent in the container (step 12). Any call would go to a
non-local URL (this task never spends money).

**Estimated effort.** M (three sessions: steps 1–8; steps 9–10 and the tests; steps 11–16 on the Spark).

**AI-disclosure note.** `harness/*`: `AI-assisted: <model> via <tool>, <date>: wrote the harness step loop, providers, budget guard and logs.`
`vllm.py` and `runner.py` add `Derived from: EN.665.715/assignments/assignment4/system-prompt/tools/smoke_test.py:step,SAMPLING (copied from this repository, <date>)`.

---

### M2.T18 — Frontier providers: `openai_responses` and `anthropic_messages`

**Why.** The roster compares local and frontier models (APPROACH §7; AGENT-DESIGN D10 "Harness": OpenAI
Responses API, Anthropic Messages). GPT-6 models need the Responses API to call tools while reasoning,
and Claude Opus 5.5 always thinks and rejects a forced `tool_choice` and non-default sampling (README
C11, facts recorded 2026-09-27 and re-checked in M1.T11). Appended to M2 so that M2.T7 needs no money.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M2.T7 done | task | `grep -E "^. M2\.T7 " course-project/plan/M2-sim-mvp.md` (Mac) | Status `done` |
| M1.T11 done | task | `grep -E "^. M1\.T11 " course-project/plan/M1-foundations.md` (Mac) | Status `done` |
| Keys file present (never print it) | secret | `ssh … 'test -s ~/.config/beaconmind/secrets.env && stat -c %a ~/.config/beaconmind/secrets.env'` (Mac) | `600` |
| Keys visible in the container | secret | `ssh … "docker exec beaconmind-ros bash -lc 'test -n \"\$OPENAI_API_KEY\" && test -n \"\$ANTHROPIC_API_KEY\" && echo both-set'"` (Mac) | `both-set` |
| `anthropic` in the container | package | `docker exec beaconmind-ros bash -lc 'python3 -c "import anthropic, openai; print(anthropic.__version__, openai.__version__)"'` (Spark host) | two versions |

**Inputs.** README C10.8, C11, L9; `evidence/M1/M1.T11/` (the re-checked model IDs, prices, option field
names and the one-tool-call transcripts per provider — **the only source for API field names in this
task**); AGENT-DESIGN D10.

**Steps.**
1. *Mac.* README §1.2 steps 1–5. Read `evidence/M1/M1.T11/` in full and list, in your notes, for each
   provider: the model IDs, the request field that sets reasoning effort, how reasoning/thinking items are
   returned and must be sent back inside a tool loop, the usage field names (input, cached input, output,
   reasoning), and the stop/finish values. **If any of these is not in the M1.T11 evidence → stop and
   ask** (do not take field names from memory or from this plan).
2. *Mac.* `harness/providers/openai_responses.py`: `build_request(entry, system_text, messages, tools)`,
   `parse_response(raw, latency_s) -> ProviderTurn`, `call(...)`. The neutral assistant turn keeps the
   provider's output items in `raw` so the next request can send them back unchanged (reasoning items
   included, as M1.T11 established); `entry["options"]` is merged into the request unchanged (C11); tools
   are converted from `TOOL_SPECS`; no `temperature` unless the effort allows it (C11). Stateless per
   step: no conversation id is reused across steps (D10).
3. *Mac.* `harness/providers/anthropic_messages.py`: same three functions. The system prompt goes in the
   system field; the assistant's content blocks (thinking blocks included) are stored in `raw` and sent
   back unchanged within the step; tool results go back as tool-result blocks with the matching id; no
   forced tool choice and no sampling parameters (C11).
4. *Mac.* Record fixtures **without spending**: craft two synthetic raw responses per provider by hand
   from the shapes in the M1.T11 transcripts (one with a tool call, one final), store them in
   `tests/fixtures/providers/{openai_responses,anthropic_messages}_{tool_call,final}.json`, and write the
   unit tests. (The live check in step 6 costs a few cents and needs approval.)
5. *Mac.* Run the unit tests.
6. *Spark container `beaconmind-ros`.* **Spend approval (stop and ask).** README L4 forbids frontier calls
   inside pytest, so the live check is a smoke **script**, not a test: write
   `course-project/tools/frontier_smoke.py --model-key <key> --budget-usd 1.0` that runs one `LLMPolicy`
   step on the S1 scenario (`beaconmind/tests/fixtures/smoke_v33/scenarios.json`) with a `RunBudget`
   (run cap 1.0, the shared ledger `data/budget/ledger.jsonl`, C13), then prints `PASS` or `FAIL <reason>` for
   each check: the final text is accepted by `parse_final_text`; ≥ 1 tool call was executed through
   `dispatch`; `cost_usd` > 0; the shared ledger grew by exactly that cost. **Estimate to give Xiaohui
   (worst case, at the C11 prices to be re-checked by M1.T11):** ≤ 10 turns, input growing from about 6k
   to 16k tokens per turn (the v3.3 prompt alone was 6,069 prompt tokens in the smoke records) and ≤ 4k
   output per turn → about 160k in and 40k out per provider → GPT-6 Sol at $2/$10 per Mtok ≈ $0.72,
   Claude Opus 5.5 at $4/$20 ≈ $1.44; ask for approval of **up to $2.50 in total** (each run is capped at
   $1.00 by the guard; a run stopped by the guard is a `FAIL budget` and is reported, not retried without
   a new yes). Run only after a yes, once per provider:
   `docker exec beaconmind-ros bash -lc 'cd /workspace/course-project && python3 tools/frontier_smoke.py --model-key <openai key> --budget-usd 1.0'`
   and the same with the Anthropic key (keys in `configs/providers.json`, from M1.T11).
7. Evidence, status, `CONTEXT.md` (record the dollars spent from the ledger).

**Deliverables.** `harness/providers/openai_responses.py`, `anthropic_messages.py`;
`tests/test_providers_frontier.py`; `tools/frontier_smoke.py`; the four fixture files.

**Tests.**
- `tests/test_providers_frontier.py` (10): per provider —
  `test_<p>_request_has_system_and_tools`, `test_<p>_request_passes_options_unchanged`,
  `test_<p>_no_forbidden_sampling_fields` (Anthropic: no `temperature`/`top_p`/`tool_choice`; OpenAI:
  no `temperature` when an effort other than `none` is set), `test_<p>_parse_tool_call_fixture`,
  `test_<p>_raw_items_replayed_in_next_request` (the stored `raw` of turn 0 appears verbatim in the
  turn-1 request). Command (Mac): `../.venv/bin/python -m pytest -q tests/test_providers_frontier.py` →
  `10 passed`.
- Live smoke (not pytest, README L4; step 6, after the spend approval): `tools/frontier_smoke.py` once per
  provider; expected four `PASS` lines per provider and a total ledger increase ≤ $2.50.

**Acceptance criteria.**
- [ ] `10 passed` on the Mac; full suite passes in `beaconmind-ros`.
- [ ] Live smoke printed only `PASS` lines for both providers after the approval; spend ≤ the approved
      amount (≤ $2.50); ledger lines saved.
- [ ] No key, header or `Authorization` string in any saved file (`grep -rnE "sk-|x-api-key|Authorization" evidence/M2/M2.T18` prints nothing).

**Evidence to save** (`evidence/M2/M2.T18/`). `pytest_mac.txt`, `pytest_py310.txt`, `frontier_smoke.txt`,
`ledger_excerpt.jsonl`, `spend_approval.md` (Xiaohui's yes, verbatim, with the date).

**Pitfalls and known gotchas.** Provider facts go stale (C11): rely only on M1.T11's evidence. Thinking
or reasoning items that are dropped between tool turns break the loop on these APIs. Never log request
headers. Prices in `providers.json` carry `price_checked`; the run header copies it.

**Stop-and-ask conditions.** Step 1 (a field not in the M1.T11 evidence). Step 6 (money). A provider
rejects a request shape that M1.T11 recorded as working (a fact contradicted, §1.4 item 3).

**Estimated effort.** S.

**AI-disclosure note.** `AI-assisted: <model> via <tool>, <date>: wrote the OpenAI Responses and Anthropic Messages providers and tests.`

---
### M2.T8 — B0 dead reckoning and B2 (the D7 procedure as code: estimation steps 1–6) with the baseline runner

**Why.** B0 is the floor every estimator must beat (talk track target "beats B0 on ATE"); B2 runs the
same D7 per-step procedure as ordinary code with the **same tools**, so comparing L2 with B2 measures
what it costs to have an LLM execute the procedure (OD2; talk track "the same per-step procedure run as
ordinary code"). This task gives B2's estimation (D7 steps 1–6 and the report) — all a replay arm needs;
M2.T19 adds the decisions (step 7) that a closed-loop driver needs. Both baselines write the C9.2 run-log
format with `llm_turns: []` (C9.2 "Baselines … write the same run-log format").

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M2.T7 done | task | `grep -E "^. M2\.T7 " course-project/plan/M2-sim-mvp.md` (Mac) | Status `done` |
| Reference simulator importable | code | `cd assignments/assignment4/system-prompt/tools && python3 -c "import backstory_sim, fewshot_scenario, build_scenarios; print(fewshot_scenario.EX3_SEED, build_scenarios.SEED)"` (Mac, from the repository root) | `27 910` (reviewer ran it 2026-10-06) |

**Inputs.** AGENT-DESIGN D7 (whole), D8; README C4, C9.2, OD2; `tools/backstory_sim.py` (`associate`,
`run`: the reference D7 implementation and its rounding: poses `rp()`, map entries 2 dp);
`tools/fewshot_scenario.py` (`EX3_WORLD`, `EX3_SEED`, `EX3_STEP`); `tools/build_scenarios.py` (`WORLD`,
`SEED`, `STEP`).

**Steps.**
1. *Mac.* README §1.2 steps 1–5.
2. *Mac.* `src/beaconmind/baselines/__init__.py`, `baselines/b0.py`: `class B0Policy` (implements
   `runner.Policy`): step 0 → pose (0, 0, 0); otherwise `dispatch("compose_odometry", {"pose":
   prev.pose, **odometry without quality}, ctx)` (null odometry → keep the previous pose); B0 uses the
   odometry as given, whatever its `quality` (dead reckoning from encoders and IMU yaw, glossary). Report:
   `pose_source "odometry"`, `associations []`, `loop_closure []`, `map []`, `memory` =
   `report.initial_memory()`, `decision "NONE"`, `move_result` from the step, `note "B0"`. B0 is a
   replay-only arm; the CLI refuses `--arm B0 --mode closed_loop`.
3. *Mac.* `baselines/b2_rules.py`: `class B2Policy` and the pure function
   `b2_estimate(step_message: dict, ctx: StepContext) -> dict` that returns the report **before** the
   decision, implementing D7 steps 1–6 using **only** `dispatch(...)` (never `beaconmind.geometry`
   directly), so its numbers are exactly the tools' numbers:
   - Step 0 / step 1 checks in D7 order (latched → `STOPPED`; null odometry after step 0 →
     `emergency_stop` then `STOPPED`; `status: error` → `NONE`; each skips steps 3–7 and keeps memory).
   - Step 2 Predict (slip → `forward_m = left_m = 0`).
   - Step 3 Associate with the D7 table, including `rejected` for quality < `reject_quality_below`, range
     > `reject_range_above_m` or a non-null ID outside 0–29; candidates (same ID; for a decoded ID with no
     in-gate entry also `U<n>` entries; for a null ID every entry); `ambiguous` (several in gate);
     `new` with the D3 label rule (`B<id>`, `B<id>b`, `rejected` if both exist; `U<n>` for null IDs);
     `rejected` conflicts within `conflict_radius_m`.
   - Step 4 pose correction table, **including** `relocalised` and drift recovery (≥ 3 detections whose
     ID has a single confirmed entry not in gate → `fix_pose` on those; `relocalisation_ok` → accept and
     re-gate this step's detections from that pose).
   - Step 5 map updates (new → `map_point`, tentative; `update_beacon` for matched tentative;
     confirmation at `n_obs ≥ confirm_n_obs` and `baseline_m ≥ confirm_baseline_m`; confirmed frozen;
     conflicts and `suspect` at `suspect_conflicts`; `prior_kept` → no map change, all detections
     `rejected`), rounding x/y to 0.01 m as `backstory_sim.py` does; `first_seen_scan` is filled in
     M2.T19 (it needs the decision) — until then set it to the current `scan_index`.
   - Step 6 loop closure (accepted only with `beacon_fix`/`relocalised` and the beacon in the fix).
   - `B2Policy.decide` returns the final JSON text of the report with `decision "NONE"` in replay. In
     closed loop it returns `NONE` until M2.T19 adds `b2_decide` (B2 does not drive before M2.T19).
4. *Mac.* `baselines/run.py` CLI, same flags as `harness.run` for `--arm B0|B2`, writing
   `data/runs/<run_id>/…` with `model_key` `none`, `llm_turns: []`, `cost_usd 0`; register `B0` and `B2`
   in `harness/run.py`'s `--arm` choices by delegating to these policies.
5. *Mac.* **Reference copy for the parity tests.** The Mac → Spark sync (L6) copies only `course-project/`,
   so tests must not import from `assignments/`. Copy, unchanged, `backstory_sim.py`, `fewshot_scenario.py`,
   `build_scenarios.py` and `l2_geometry.py` from `assignments/assignment4/system-prompt/tools/` into
   `course-project/beaconmind/tests/reference_v33/` (plus an empty `__init__.py` and a `SOURCES.sha256`
   written with `shasum -a 256` of the four originals; repository code, L11: keep each file's disclosure).
   Tests put that folder first on `sys.path` (`sys.path.insert(0, str(Path(__file__).parent /
   "reference_v33"))`) and import the modules by their plain names. Add
   `test_reference_copy_unchanged` to `tests/test_b2_estimate.py`: the SHA-256 of each copy equals its line
   in `SOURCES.sha256`.
6. *Mac.* Test helper `tests/helpers/synth.py` (shared with M2.T9/M2.T10):
   `make_obslog(tmp_path, world, actions, *, car, dv, noise=None, odo_noise=None, rng_key="t",
   exact=False) -> Path` that drives `KinSim` with a fixed action list through `ObservationBuilder` and
   `ObsLogWriter` and returns the `.jsonl` path (its `.gt.tum` next to it). `exact=True` builds with
   `round_outputs=False`, so noise-free tests can expect exact answers (observations are otherwise rounded
   to 0.01 m and 0.1°, C1).
7. *Mac.* Write the tests; run them; sync; run the full suite on the Spark host.
8. *Spark host.* Smoke: B0 and B2 in replay on the SCRIPT_SCAN obslog from M2.T7 step 15 (no LLM, so
   the host venv is fine), from `~/Projects/EN.665.715/course-project`:
   ```bash
   L=data/obslogs/sim-dup-s1000-SCRIPT_SCAN-k1.jsonl
   ~/.venvs/beaconmind/bin/python -m beaconmind.baselines.run --arm B0 --mode replay --obslogs $L --out data/runs --allow-placeholder
   ~/.venvs/beaconmind/bin/python -m beaconmind.baselines.run --arm B2 --mode replay --obslogs $L --out data/runs --allow-placeholder
   for r in $(ls -td data/runs/*-B0-none data/runs/*-B2-none | head -2); do ~/.venvs/beaconmind/bin/python -m beaconmind.harness.summarize $r; done
   ```
9. Evidence, status, `CONTEXT.md`.

**Deliverables.** `src/beaconmind/baselines/{__init__,b0,b2_rules,run}.py`; `harness/run.py` (arms);
`tests/helpers/__init__.py`, `tests/helpers/synth.py`; `tests/reference_v33/{__init__,backstory_sim,fewshot_scenario,build_scenarios,l2_geometry}.py`
and `SOURCES.sha256`; `tests/test_b0.py`, `tests/test_b2_estimate.py`.

**Tests.**
- `tests/test_b0.py` (4): `test_b0_step0_origin`, `test_b0_composes_reported_odometry` (equals
  `compose_odometry` chained from step 0), `test_b0_keeps_pose_on_null_odometry`,
  `test_b0_runlog_valid_and_no_llm_turns`.
- `tests/test_b2_estimate.py` (13, including `test_reference_copy_unchanged` of step 5):
  - `test_parity_with_backstory_ex3` — run `backstory_sim.run(EX3_WORLD, seed=EX3_SEED,
    max_steps=EX3_STEP + 1)`; for every record, give `b2_estimate` the record's observation (missing C3
    keys filled with closed-loop defaults: `status "ok"`, `sensors` ok, `mode "closed_loop"`, `latched
    False`) and `prev_report`; assert equal `pose` (rounded), `pose_source`, `associations`, and `map`
    entries ignoring `first_seen_scan`.
  - `test_parity_with_backstory_seed910` — same for `build_scenarios.WORLD`, `SEED`, `STEP`.
  - `test_latched_returns_stopped_memory_unchanged`, `test_null_odometry_estop_then_stopped`,
    `test_status_error_returns_none`.
  - `test_slip_zeroes_translation`.
  - `test_reject_rules_quality_range_id`.
  - `test_ambiguous_when_two_in_gate`.
  - `test_third_copy_rejected` (B1 and B1b exist).
  - `test_prior_kept_rejects_everything_no_map_change`.
  - `test_drift_recovery_relocalises` — a pose prior 0.8 m off with three confirmed single-ID beacons in
    view → `pose_source "relocalised"` and the detections re-gated as `matched`.
  - `test_b2_uses_only_dispatch` — static check: the source of `baselines/b2_rules.py` contains no
    `import` of `beaconmind.geometry` or `l2_geometry` (every number goes through `tools.dispatch`).
- Command (Mac): `../.venv/bin/python -m pytest -q tests/test_b0.py tests/test_b2_estimate.py` →
  `17 passed`.
- Smoke test (Spark host): step 8 — both runs end `DONE` (detail `log_end`) with 15 steps; B2 shows zero
  `format` and zero `state` violations (its reports are tool-derived by construction).

**Acceptance criteria.**
- [ ] `17 passed` on the Mac; full suite on the Spark host (3.10 or labelled).
- [ ] Both backstory parity tests pass (B2 estimation = the reference D7 code on two simulated histories).
- [ ] Smoke summaries saved; B2 has 0 format/state violations.

**Evidence to save** (`evidence/M2/M2.T8/`). `pytest_mac.txt`, `pytest_spark_host.txt`, `smoke_b0.txt`, `smoke_b2.txt`.

**Pitfalls and known gotchas.** `backstory_sim.py` raises `NotImplementedError` for branches it does not
model (ambiguous, relocalised, contacts); the parity seeds are ones that complete. Its observation dicts
lack some C3 keys — fill them only in the test adapter, never in B2. Compose from the **rounded** previous
pose (a stateless agent only has PREVIOUS_REPORT).

**Stop-and-ask conditions.** A parity test fails because the D7 text and `backstory_sim.py` disagree
(report the step and both readings; AGENT-DESIGN wins, §1.4 item 8).

**Estimated effort.** M.

**AI-disclosure note.** `b2_rules.py`: `AI-assisted: <model> via <tool>, <date>: wrote B2 (D7 as code).`
plus `Derived from: EN.665.715/assignments/assignment4/system-prompt/tools/backstory_sim.py:associate,run (copied from this repository and extended, <date>)`.

---

### M2.T19 — B2 decisions: D7 step 7 (EXPLORE E1–E5, GO_TO_BEACON, RETURN_TO_START, contact recovery, refused turn)

**Why.** To record observation logs, something deterministic must drive the robot: the cut line allows
"moves chosen by B2 or by the operator, not an LLM" (README §3.4). B2's decisions also make it a
closed-loop baseline for missions (talk track; OD2). Appended to M2.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M2.T8 done | task | `grep -E "^. M2\.T8 " course-project/plan/M2-sim-mvp.md` (Mac) | Status `done` |

**Inputs.** AGENT-DESIGN D2 (done conditions), D7 step 7 (both tables, the refused-turn and reset rules,
the `scan_added` note), step 8; `tools/backstory_sim.py` (`e2`, `e3`, `e4`, `e4_or_e5`, the termination
test, the `scan_added` bookkeeping).

**Steps.**
1. *Mac.* README §1.2 steps 1–5.
2. *Mac.* In `baselines/b2_rules.py` add `b2_decide(report: dict, step_message: dict, ctx) -> dict` that
   applies the D7 decision table in order — row 0 (STOP/REPORT), 1 (contact recovery), 1b (operator
   request: B2 cannot interpret free text, so it answers `ASK` with `message "B2 cannot interpret
   operator requests"`, and the run header says B2 is not scored on the request suite), 2 (EXPLORE rows
   E1–E5 with every memory write, including the v3.3 shared `scans_without_new` update and the
   `scan_added` timing), 3 (GO_TO_BEACON incl. 3a and 3b and `near_blocked`), 4 (RETURN_TO_START) — plus
   the refused-turn and reset rules. Sector choice ties: higher score, then fewer turns, then left
   (`backstory_sim.py` key). It executes the decided move through `dispatch("move", …)`, sets
   `move_result`, fills `first_seen_scan` (D7 step 5), and returns the final report. `B2Policy.decide`
   now calls it in closed loop.
3. *Mac.* Tests; run; sync; Spark host full suite.
4. *Spark host.* Smoke: B2 closed loop in kinsim with placeholders on three dev worlds and the full mission
   chain (no LLM, so the host venv is fine), from `~/Projects/EN.665.715/course-project`:
   `~/.venvs/beaconmind/bin/python -m beaconmind.harness.run --arm B2 --mode closed_loop --env kinsim --worlds data/worlds/sim-dup-s100{0,1,2}.json --missions EXPLORE,GO_TO_BEACON,RETURN_TO_START --k 1 --budget-usd 0 --out data/runs --allow-placeholder`,
   then `python -m beaconmind.harness.summarize data/runs/<run_id>`.
5. Evidence, status, `CONTEXT.md`.

**Deliverables.** `baselines/b2_rules.py` (decisions); `tests/test_b2_decide.py`.

**Tests.** `tests/test_b2_decide.py` (14):
- `test_parity_decisions_ex3` and `test_parity_decisions_seed910` — with the backstory records, the full
  B2 report (decision and memory included, `first_seen_scan` included) equals `backstory_sim`'s report at
  every step.
- `test_stop_mission_overrides_contact`, `test_report_mission_none`.
- `test_contact_backs_off_and_blocks_heading` — FORWARD stalled → `BACKWARD_10`, `blocked_heading_deg` =
  θ, `recovery backed_off`.
- `test_refused_turn_backward_then_ask` — `turn_allowed` false twice → `BACKWARD_10`, then `NONE` with
  `stuck` 1, then `ASK`.
- `test_e1_termination`, `test_e2_abandon_scan_when_turn_refused`, `test_e4_starts_scan_new_place`,
  `test_e5_no_unblocked_sector_done`.
- `test_goto_done_when_close_and_aligned`, `test_goto_lost_target_ask_3a`, `test_return_done_near_origin`.
- `test_closed_loop_kinsim_explore_terminates` — noise-free kinsim on `fixtures/worlds/sim-dup-s1000.json`
  with the placeholder car: EXPLORE ends with `DONE` within 150 steps, zero `guardrail` violations, and
  ≥ 80 % of the wall tags in the final map within 0.30 m of a same-ID tag.
- Command (Mac): `../.venv/bin/python -m pytest -q tests/test_b2_decide.py` → `14 passed`.
- Smoke (Spark host, step 4): for each of the three worlds, the EXPLORE episode ends `DONE` or `budget`,
  and a GO_TO and a RETURN episode follow (or the GO_TO skip is logged); 0 guardrail violations. Paste
  the summary.

**Acceptance criteria.**
- [ ] `14 passed` on the Mac; full suite on the Spark host.
- [ ] Smoke summary saved with the stated pass conditions.

**Evidence to save** (`evidence/M2/M2.T19/`). `pytest_mac.txt`, `pytest_spark_host.txt`, `smoke_b2_closed_loop.txt`.

**Pitfalls and known gotchas.** The decision table's row order matters (v3.2 fix: STOP/REPORT before
contact recovery and the operator request). "Never drive forward to get around a refused turn" (D7).
E2 counts `scan_added` before reading it when a scan was already in progress (v3.3 fix).

**Stop-and-ask conditions.** The noise-free EXPLORE test does not terminate or maps < 80 % of tags (a
procedure-level finding: report it with the world and step — do not tune DVs, §1.4 item 6).

**Estimated effort.** S.

**AI-disclosure note.** As M2.T8 (`Derived from: …backstory_sim.py:e2,e3,e4,e4_or_e5`).

---

### M2.T9 — B1: GTSAM iSAM2 offline on the host, oracle association

**Why.** B1 is the classical reference (talk track: "stay within 2× B1"; APPROACH §10 W4; AGENT-DESIGN
"B1 (GTSAM)": offline on the host in a Python 3.12 venv). It is a planar factor graph — `Pose2` per step,
`Point2` per physical tag, odometry `BetweenFactorPose2`, `BearingRangeFactor2D` per detection
(`research/2026-09-27-llm-slam-feasibility/topic2-fiducial-slam-baseline.md`, the GTSAM PlanarSLAM
example) — with **oracle association when IDs repeat** (OD3: the true physical tag from `det_truth`, so
B1 is an upper bound).

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M2.T7 done | task | `grep -E "^. M2\.T7 " course-project/plan/M2-sim-mvp.md` (Mac) | Status `done` |
| M2.T8 done (for `tests/helpers/synth.py`, B0) | task | `grep -E "^. M2\.T8 " course-project/plan/M2-sim-mvp.md` (Mac) | Status `done` |
| gtsam in the host venv | package | `ssh … '~/.venvs/beaconmind/bin/python -c "import gtsam; print(gtsam.__version__)"'` (Mac) | a version string (step 2 if not) |

**Inputs.** README C1 (radians at the GTSAM boundary), C9, OD3, L3, L5; AGENT-DESIGN "B1 (GTSAM)";
`topic2-fiducial-slam-baseline.md` (lines on the PlanarSLAM template and the recommended B1);
`configs/odometry_noise.json`, `configs/detector_noise.json` (or the placeholders).

**Steps.**
1. *Mac.* README §1.2 steps 1–5.
2. *Spark host.* **Verification step — the GTSAM API** (README §9.1: the cp312 aarch64 wheel is
   unverified). Write `course-project/tools/gtsam_probe.py` that prints `gtsam.__version__` and, for each
   name in `Pose2, Point2, Rot2, BetweenFactorPose2, PriorFactorPose2, BearingRangeFactor2D,
   NonlinearFactorGraph, Values, ISAM2, ISAM2Params, LevenbergMarquardtOptimizer, noiseModel.Diagonal,
   symbol_shorthand.X, symbol_shorthand.L, Rot2.fromDegrees`, `OK <name>` or `MISSING <name>`. Run
   `~/.venvs/beaconmind/bin/python course-project/tools/gtsam_probe.py`.
   - Version printed and no `MISSING` → continue at step 3.
   - `import gtsam` fails → run `~/.venvs/beaconmind/bin/pip install "gtsam==4.3.0"` once and paste the
     output. A wheel installs → re-run the probe. "No matching distribution" → **stop and ask**, with
     the options: (a) a Miniforge environment from conda-forge (whether conda-forge has a linux-aarch64
     gtsam build is unverified — check `conda search -c conda-forge gtsam` first); (b) building GTSAM
     from source with Python bindings (hours); (c) a different version from PyPI that has a cp312
     aarch64 wheel (`pip index versions gtsam`). Default recommendation: (c) if any 4.2+/4.3.x wheel
     exists, else (a).
   - Some names `MISSING` → find the 4.3 spelling with `python -c "import gtsam; print([n for n in
     dir(gtsam) if 'Bearing' in n])"`, use it, and record the mapping in `CONTEXT.md`.
3. *Mac.* `src/beaconmind/baselines/b1_gtsam.py` (imports `gtsam` inside functions only, so the package
   imports without it):
   - `run_b1(obslog_path, *, dv, det_noise, odo_noise, assoc="oracle", out_writer) -> dict`.
   - Keys `X(k)` per step, `L(j)` per landmark; landmark identity = the detection's `uid` from
     `det_truth` (`assoc="oracle"`), or the integer ID (`assoc="id"`, a diagnostic variant; with
     duplicated IDs it merges two tags).
   - Prior on `X(0)` = `Pose2(0, 0, 0)` with σ (1e-3 m, 1e-3 m, 1e-3 rad).
   - Odometry factor from each observation's `odometry` (C1 chord form = the relative pose):
     `Pose2(forward_m, left_m, radians(dtheta_deg))`, σ_x = max(0.002, `wheel_scale_sigma`·|f|/√2), σ_y =
     max(0.002, 0.5·`wheel_scale_sigma`·|f|), σ_θ = radians(max(0.1, `gyro_sigma_deg`)); null odometry →
     σ (1.0 m, 1.0 m, π rad).
   - Detections used: the D7 filter (quality ≥ `reject_quality_below`, range ≤ `reject_range_above_m`,
     ID in 0–29). Factor `BearingRangeFactor2D(X(k), L(j), Rot2.fromDegrees(bearing), range, σ)` with σ =
     (radians(`config.bearing_sigma_deg(noise, range)`), `config.range_sigma_m(noise, range)`), using the
     noise view (M2.T3 step 2) from `configs/detector_noise.json` for every source (Isaac detections are
     degraded to that measured noise by M2.T6's `sim_extra`, so the same σ applies). A new landmark is
     initialised at the detection's map point from the current estimate.
   - **Online estimate (primary, proposed default):** `ISAM2.update` after each step; the step-k pose in
     the run log is the iSAM2 estimate of `X(k)` at step k — causal, like the agent's own belief.
     **Batch (secondary):** after the last step, Levenberg–Marquardt on the whole graph; written to
     `<episode_id>.batch.tum` in the run directory and reported as row `B1-batch`. Tell Xiaohui this
     choice (stop-and-ask at the end of the session; default stays online) because the talk track's "2× B1"
     target needs one of them.
   - Reports per step: `pose` (rounded), `pose_source "beacon_fix"` when the step had ≥ 1 range-bearing
     factor else `"odometry"`, `map` with labels `B<id>` / `B<id>b` in order of first sighting of each
     physical tag, `state "confirmed"` after ≥ 2 observations, `decision "NONE"`.
   - Run header adds `{"b1": {"assoc": "oracle", "online": "isam2", "noise_model": "<sha12s>",
     "note": "B1 uses the generating noise model and oracle association: an upper bound"}}`.
   - CLI: `python -m beaconmind.baselines.run --arm B1 --obslogs <files…> --out data/runs [--assoc id]`.
4. *Mac.* Write `tests/test_b1_gtsam.py` (all tests marked `@pytest.mark.gtsam`), using
   `tests/helpers/synth.py`.
5. *Spark host.* Sync; run `cd ~/Projects/EN.665.715/course-project/beaconmind && ~/.venvs/beaconmind/bin/python -m pytest -q -m gtsam tests/test_b1_gtsam.py`.
6. *Spark host.* Smoke, from `~/Projects/EN.665.715/course-project`:
   `~/.venvs/beaconmind/bin/python -m beaconmind.baselines.run --arm B1 --obslogs data/obslogs/sim-dup-s1000-SCRIPT_SCAN-k1.jsonl --out data/runs --allow-placeholder`,
   then `~/.venvs/beaconmind/bin/python -m beaconmind.harness.summarize $(ls -td data/runs/*-B1-none | head -1)`.
7. Evidence, status, `CONTEXT.md` (gtsam version, any API name mapping, the online/batch answer).

**Deliverables.** `baselines/b1_gtsam.py`; `baselines/run.py` (`--arm B1`); `tools/gtsam_probe.py`;
`tests/test_b1_gtsam.py`.

**Tests.** `tests/test_b1_gtsam.py` (10, marker `gtsam`, Spark host venv):
- `test_noise_free_square_recovers_truth` — a 1 m square driven as FORWARD_25/TURN_LEFT_30 in a fixture
  world with noise-free detections and odometry (`make_obslog(..., exact=True)`): every online pose and
  every landmark within 1e-6 of truth; batch the same.
- `test_odometry_only_equals_dead_reckoning` — detections removed: B1 poses equal the unrounded chain of
  `compose_odometry` over the logged odometry within 1e-9, and B0's reported poses within 0.01 m (B0
  reports rounded poses).
- `test_biased_odometry_corrected_by_landmarks` — forward odometry scaled ×1.10, noise-free tags in view:
  B1's final position error < 0.2 × B0's.
- `test_duplicate_ids_oracle_two_landmarks` — two id-3 tags → two landmarks, each within 1e-6 (noise-free, `exact=True`).
- `test_id_only_association_worse_with_duplicates` — `assoc="id"` final error > oracle final error.
- `test_full_turn_no_wrap_jump` — 12 × 30° turns (`exact=True`): every heading within 1e-6 of truth after wrapping.
- `test_online_is_causal` — the online pose at step k is identical whether the log ends at k or later.
- `test_noisy_beats_b0` — 20 seeded noisy logs (placeholder noise): median unaligned ATE(B1) < median
  ATE(B0) (ATE computed inline here, before M2.T10 exists, with the C10.1 formula).
- `test_runlog_valid_no_llm_turns`.
- `test_filtered_detection_adds_no_factor` — a quality-0.4 detection adds no factor (graph size check).
- Command (Spark host, step 5) → `10 passed`. On the Mac the file is deselected by the default `addopts`
  (`-m 'not … gtsam'`), so the Mac suite is unaffected.
- Smoke (step 6): B1 run ends with 15 steps; paste the summary.

**Acceptance criteria.**
- [ ] Probe output saved with no `MISSING`; gtsam version recorded.
- [ ] `10 passed` on the Spark host.
- [ ] Online/batch choice stated to Xiaohui and recorded.

**Evidence to save** (`evidence/M2/M2.T9/`). `gtsam_probe.txt`, `pip_install.txt` (if step 2 installed),
`pytest_gtsam.txt`, `smoke_b1.txt`, `b1_mode_decision.md`.

**Pitfalls and known gotchas.** GTSAM angles are radians (C1). `Point2` is a NumPy array in GTSAM 4.2+.
Noise-free test logs still need **non-zero** σ in every noise model (a zero sigma makes GTSAM's
`noiseModel.Diagonal.Sigmas` singular): pass the placeholder detector-noise view and
`configs/odometry_noise.json` to `run_b1` in every test; the data are consistent, so the optimum is still exact.
Add each landmark's initial value only once (`Values.insert` twice raises). iSAM2 needs the new factors
and only the new values per update. Pose-graph headings near ±π: use `Pose2.theta()` and wrap in degrees
only when writing the report.

**Stop-and-ask conditions.** Step 2 (no wheel). The online/batch choice (default online).

**Estimated effort.** M.

**AI-disclosure note.** `AI-assisted: <model> via <tool>, <date>: wrote the B1 GTSAM baseline and tests.`
plus `Derived from: GTSAM PlanarSLAM example (gtbook.github.io/gtsam-examples/PlanarSLAMExample.html) (reimplemented, not copied)`.

---
### M2.T10 — Metrics A: trajectory (ATE, RPE), map, association, validity, latency and cost; `score` CLI; evo cross-check

**Why.** One metrics module scores every arm from the same run-log format (C9.2, C10), so B0, B1, B2 and
each model are compared by identical code. The primary pose metric is unaligned ATE in the start frame
(OD5, talk track); aligned ATE, final error, heading RMSE and RPE per metre are secondary; evo is a
cross-check that must agree within 1 mm (C10.2). Map error, association TP/FP/FN (precision primary)
and the validity, latency and cost measures come from C10.3, C10.4, C10.7 and C10.8.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M2.T7, M2.T8 done | task | `grep -E -e "^. M2\.T7 " -e "^. M2\.T8 " course-project/plan/M2-sim-mvp.md` (Mac) | both with Status `done` |
| evo in the host venv | package | `ssh … '~/.venvs/beaconmind/bin/pip show evo \| head -2'` (Mac) | `Name: evo` and a version (step 7 if absent) |

**Inputs.** README C1, C8, C9.2, C10 (items 1–4, 7, 8); talk track backup slide (metric application);
`research/…/topic5-benchmark-and-sim.md` (ATE/RPE definitions, evo); `src/beaconmind/worlds.py`
(`tags_in_map_frame`).

**Steps.**
1. *Mac.* README §1.2 steps 1–5.
2. *Mac.* **Decision with a default:** the map-correctness radius (C10.3: 0.30 m, "proposed default,
   M2.T10 confirms"). Ask Xiaohui at the end of the session; build with
   `metrics/mapping.py: CORRECT_RADIUS_M = 0.30`. Alternative: 0.20 m if the measured detector error (M1.T8)
   is small enough that 0.30 m would accept a wrong tag. Record the answer in `CONTEXT.md`.
3. *Mac.* `src/beaconmind/metrics/__init__.py` and (standard library only unless noted):
   - `trajectory.py`: `read_tum(path) -> dict[int, tuple[x, y, θ_rad]]`, `write_tum(path, poses)`,
     `poses_from_runlog(episode_path) -> tuple[est, gt]` (est from `report_corrected.pose`, gt from
     `gt_pose_map`, keyed by step), `ate_unaligned(est, gt) -> tuple[float, int]` (C10.1, RMSE over steps
     with both, and the count), `umeyama_se2(est, gt) -> tuple[θ, tx, ty]` (closed form, no scale: with
     centred points, θ = atan2(Σ(e_x·g_y − e_y·g_x), Σ(e_x·g_x + e_y·g_y)), t = ḡ − R(θ)·ē),
     `ate_aligned(est, gt)`, `final_pose_error(est, gt) -> tuple[pos_m, abs_head_deg]` (last step with
     both), `heading_rmse_deg(est, gt)` (wrapped differences), `rpe_per_m(est, gt, delta_m=1.0) -> tuple[
     float, int]` (pairs (i, j): j = the first step after i whose ground-truth path length from i is ≥
     `delta_m`; error = translation norm of `(G_i⁻¹ G_j)⁻¹ (E_i⁻¹ E_j)`; RMSE over pairs; and the pair count).
   - `mapping.py`: `map_metrics(final_map, world, radius=CORRECT_RADIUS_M) -> dict` with
     `entries, correct, phantoms, rmse_m, id_precision, id_recall`: ground-truth wall tags (ID 0–29) in the
     map frame via `worlds.tags_in_map_frame`; greedy one-to-one matching of entries to same-ID tags by
     distance; correct when ≤ radius; phantom = an entry with no same-ID tag within the radius; RMSE over
     correct entries; precision = correct / entries; recall = matched physical tags / wall tags.
   - `association.py`: `association_counts(step_records) -> dict` (C10.4): walk the steps in order; a
     label's identity is the `uid` (from `det_truth`) of the detection that created it (`new`); for each
     later detection whose `uid` already has a label: `matched` to a label with the same identity → TP;
     `matched` to another identity → FP; `new`, `ambiguous` or `rejected` → FN. A `matched` detection
     whose `uid` has no label yet → FP. Returns `tp, fp, fn, precision (None if tp+fp = 0), recall,
     loop_closures_accepted, loop_closures_correct`.
   - `validity.py`: per episode `guardrail_per100, format_per100, state_per100, invalid_tool_per100`
     (violations per 100 decisions), `tool_turns_per_decision`, and `executed_invalid` (an executed move
     that was not in that step's `safety` flags — must be 0; a non-zero value is a validator bug).
   - `cost.py`: `latency_stats(latencies) -> {p50, p95}` using `statistics.median` and
     `statistics.quantiles(data, n=100, method="inclusive")[94]`; `episode_cost(records)`;
     `gpu_hours(records)` (sum of `decision_latency_s` / 3600 for local models; state in the docstring that
     this is wall time while the GPU serves the model, an upper bound when requests overlap).
   - `score.py` CLI: `python -m beaconmind.metrics.score --run <run_dir> [--run …] --worlds data/worlds
     --out <dir>` writes `<dir>/episodes.csv` with one row per episode and the columns: `run_id, arm,
     model_key, episode_id, world_id, source, condition, mode, mission, steps, ended_by, ate_unaligned_m,
     ate_steps, ate_aligned_m, final_pos_err_m, final_head_err_deg, heading_rmse_deg, rpe_per_m,
     rpe_pairs, map_entries, map_correct, map_phantoms, map_rmse_m, id_precision, id_recall, assoc_tp,
     assoc_fp, assoc_fn, assoc_precision, assoc_recall, loop_closures, guardrail_per100, format_per100,
     state_per100, invalid_tool_per100, executed_invalid, tool_turns_per_decision, latency_p50_s,
     latency_p95_s, tokens_in, tokens_out, cost_usd, placeholders`; it also writes
     `<episode_id>.est.tum` and `<episode_id>.gt.tum` into the run directory (C8). For `B1` runs it adds
     a `B1-batch` row from `.batch.tum`.
4. *Mac.* Write the tests below (hand-computed fixtures in `tests/fixtures/metrics/`); run.
5. *Mac → Spark host.* Sync; full suite on the Spark host venv.
6. *Spark host.* Smoke, from `~/Projects/EN.665.715/course-project`. Find the newest run directory of each
   arm with `ls -td data/runs/*-<arm>-* | head -1` (run ids are `<YYYYMMDD-HHMMSS>-<arm>-<model_key>`,
   L2), then
   `~/.venvs/beaconmind/bin/python -m beaconmind.metrics.score --run <SCRIPT_SCAN run> --run <B0 run> --run <B2 run> --run <B1 run> --worlds data/worlds --out evidence/M2/M2.T10/smoke`.
7. *Spark host.* **Verification step — evo** (README §9.1: whether `--project_to_plane xy` is needed). If
   `pip show evo` printed nothing, install the `metrics` extra (`~/.venvs/beaconmind/bin/pip install -e
   "$HOME/Projects/EN.665.715/course-project/beaconmind[metrics]"`) and paste the output. Then, for one
   episode `E` from the smoke run:
   ```bash
   cd <run_dir> && ~/.venvs/beaconmind/bin/evo_ape tum E.gt.tum E.est.tum --align 2>&1 | tee /tmp/evo_a.txt
   ~/.venvs/beaconmind/bin/evo_ape tum E.gt.tum E.est.tum --align --project_to_plane xy 2>&1 | tee /tmp/evo_b.txt
   ~/.venvs/beaconmind/bin/evo_rpe tum E.gt.tum E.est.tum --delta 1 --delta_unit m 2>&1 | tee /tmp/evo_r.txt
   ```
   (on the Spark host `/tmp` is fine for these throwaway copies; save the outputs into the evidence
   folder). Branches: (a) the second command fails with "unrecognized arguments" → this evo has no
   `--project_to_plane`; compare the first with `ate_aligned`. (b) Both run → compare both. If the
   matching command's `rmse` differs from `ate_aligned` by ≤ 0.001 m → record which form agrees in
   `CONTEXT.md` (closing README §9.1's evo item). If neither agrees → check the frame (both files in the
   map frame?) and the step association, then stop and ask (§1.4 item 4). For RPE: a difference > 1 mm
   is reported with both pair counts; the custom value stays the reference (C10.2) unless Xiaohui says
   otherwise.
8. Evidence, status, `CONTEXT.md`.

**Deliverables.** `src/beaconmind/metrics/{__init__,trajectory,mapping,association,validity,cost,score}.py`;
`tests/test_metrics_trajectory.py`, `test_metrics_map.py`, `test_metrics_association.py`,
`test_metrics_validity_cost.py`, `test_metrics_score_cli.py`, `test_evo_crosscheck.py`;
`tests/fixtures/metrics/*`.

**Tests.**
- `tests/test_metrics_trajectory.py` (9): `test_ate_unaligned_hand_computed` (three points, errors 0.1,
  0.2, 0.2 → `sqrt(0.09/3)` = 0.17320…), `test_umeyama_recovers_known_transform` (gt rotated 30° and
  shifted (1, 2): aligned ATE < 1e-12, unaligned > 1), `test_aligned_never_exceeds_unaligned` (50 seeded
  random trajectories), `test_final_pose_error`, `test_heading_rmse_wraps` (179° vs −179° → 2°),
  `test_rpe_straight_line_scale_error` (est = 1.1 × gt along a 3 m line, 0.25 m steps → RPE 0.1),
  `test_rpe_pair_selection_by_path_length`, `test_tum_roundtrip`, `test_missing_steps_skipped_and_counted`.
- `tests/test_metrics_map.py` (6): `test_correct_and_phantom`, `test_duplicate_ids_each_tag_matched_once`,
  `test_rmse_over_correct_only`, `test_precision_recall`, `test_radius_boundary` (0.300 correct, 0.301 not),
  `test_map_frame_transform_applied` (world start pose (1.0, 1.0, 90°)).
- `tests/test_metrics_association.py` (7): `test_tp_same_physical_tag`, `test_fp_other_tag_same_id`,
  `test_fn_resighting_labelled_new`, `test_fn_rejected_and_ambiguous`, `test_first_sighting_not_scored`,
  `test_precision_none_without_matches`, `test_loop_closure_counts_and_correctness`.
- `tests/test_metrics_validity_cost.py` (5): `test_per100_rates`, `test_tool_turns_per_decision`,
  `test_latency_percentiles_hand_computed` (1..20 s → p50 10.5, p95 19.05), `test_episode_cost_sums_steps`,
  `test_executed_invalid_detected`.
- `tests/test_metrics_score_cli.py` (2): `test_score_cli_writes_all_columns` (a synthetic run from
  `tests/helpers/synth.py` plus B0), `test_score_values_match_functions`.
- `tests/test_evo_crosscheck.py` (2, `pytest.importorskip("evo")`, so skipped on the Mac):
  `test_evo_ape_aligned_agrees_1mm`, `test_evo_rpe_reported` (writes both values; asserts both are finite).
- Command (Mac): `../.venv/bin/python -m pytest -q tests/test_metrics_*.py tests/test_evo_crosscheck.py`
  → `29 passed, 2 skipped`. Spark host venv (evo installed): `31 passed`.
- Smoke (step 6): `episodes.csv` has one row per episode for the four runs (plus `B1-batch`), no empty
  `ate_unaligned_m`, and `executed_invalid` = 0 everywhere.

**Acceptance criteria.**
- [ ] Mac `29 passed, 2 skipped`; Spark host `31 passed`.
- [ ] evo cross-check result recorded (which flag form agrees, within 1 mm).
- [ ] Map radius answered by Xiaohui and recorded.

**Evidence to save** (`evidence/M2/M2.T10/`). `pytest_mac.txt`, `pytest_spark_host.txt`, `smoke/episodes.csv`,
`evo_ape_align.txt`, `evo_ape_align_xy.txt`, `evo_rpe.txt`, `evo_crosscheck.md` (the comparison table),
`map_radius_decision.md`.

**Pitfalls and known gotchas.** TUM timestamps here are step indices (C8), so evo associates by equal
timestamps; never mix steps from different episodes in one file. A SE(3) alignment of planar data can pick
a rotation about an in-plane axis that mirrors the trajectory — another reason to compare with the SE(2)
custom fit. Ground truth is in the map frame (C1): never compare a world-frame pose with a map-frame
estimate.

**Stop-and-ask conditions.** Step 2 (radius). Step 7 (no evo form agrees within 1 mm after the checks).

**Estimated effort.** M.

**AI-disclosure note.** `AI-assisted: <model> via <tool>, <date>: wrote the trajectory, map, association, validity and cost metrics and the score CLI.`

---

### M2.T20 — Metrics B: missions and SPL, exploration, refusal

**Why.** Closed-loop results need mission success decided from ground truth at the moment the agent says
DONE, never from its claim (C10.5; talk track), SPL with the empty-convex-arena straight-line ℓ, the
exploration curve (C10.9), and the refusal measures (C10.6) that M4.T3 will apply to the request suite.
Appended to M2.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M2.T10 done | task | `grep -E "^. M2\.T10 " course-project/plan/M2-sim-mvp.md` (Mac) | Status `done` |

**Inputs.** README C10.5, C10.6, C10.9; AGENT-DESIGN D2 ("T4 scoring"); talk track backup slide.

**Steps.**
1. *Mac.* README §1.2 steps 1–5.
2. *Mac.* `metrics/missions.py`:
   - `mission_success(episode_records, world, dv) -> dict` — at the first step whose corrected decision is
     `DONE`, using `gt_pose_map`: `GO_TO_BEACON B<k>` (target physical tag = the identity of label `B<k>`,
     as `association.py` defines it): ground-truth range from the axle midpoint ≤ `done_range_m` +
     `success_margin_beacon_m` and |ground-truth bearing| ≤ `success_bearing_deg`; `RETURN_TO_START`:
     distance to the map origin ≤ `success_start_m`; `EXPLORE`: the episode ended (`DONE` or `budget`)
     with ≥ 90 % of the wall tags mapped correctly and no phantom (`mapping.map_metrics`). No `DONE` →
     failure (except EXPLORE's budget rule). Returns `{success, at_step, gt_range_m, gt_bearing_deg,
     reason}`.
   - `spl(success, path_m, ell_m) -> float` = `S · ℓ / max(p, ℓ)`; `path_length_m(records)` = the sum of
     ground-truth step-to-step distances; `ell_m(start_xy, mission, target_xy, dv)` = `max(0,
     dist(start, target) − (done_range_m + success_margin_beacon_m))` for GO_TO and `max(0, dist(start,
     origin) − success_start_m)` for RETURN (C10.5: the nearest point of the success region; the bearing
     part of the region is ignored because the robot can turn in place — say so in the docstring;
     proposed default "SPL ℓ definition"). ℓ = 0 → SPL = S.
3. *Mac.* `metrics/exploration.py`: `exploration_curve(records, world, radius) -> list[dict]` (per step:
   decisions so far, ground-truth metres so far, seconds so far = Σ `decision_latency_s` + Σ move
   `duration_s`, fraction of wall tags correctly mapped in that step's corrected map) and
   `time_to_fraction(curve, f) -> dict | None` for f = 0.90 and 0.99 (steps, metres, seconds).
4. *Mac.* `metrics/refusal.py`: `score_requests(records, suite) -> dict` with `unsafe_n, refused_n,
   refusal_rate, unsafe_followed_by_move` (an unsafe request whose step or the next step executed a move:
   must be 0), `valid_n, false_refusal_rate, ask_correct` (ASK counts as correct only for requests the
   suite marks `ambiguous_valid`). The suite format is fixed by M4.T3; here use a fixture
   `tests/fixtures/metrics/request_suite_small.json` with `{"requests": [{"id", "text", "class":
   "unsafe" | "valid" | "ambiguous_valid"}]}` and state that M4.T3 may extend it.
5. *Mac.* Extend `score.py` with the columns `mission_success, mission_at_step, spl, path_m, ell_m,
   t90_steps, t90_m, t90_s, t99_steps, t99_m, t99_s` (empty when not applicable).
6. *Mac.* Tests; run; sync; Spark host full suite; re-run the score smoke on the M2.T19 B2 closed-loop run.
7. Evidence, status, `CONTEXT.md`.

**Deliverables.** `metrics/{missions,exploration,refusal}.py`; `metrics/score.py` (columns);
`tests/test_metrics_missions.py`, `test_metrics_exploration.py`, `test_metrics_refusal.py`;
`tests/fixtures/metrics/request_suite_small.json`.

**Tests.**
- `tests/test_metrics_missions.py` (8): `test_goto_success_inside_range_and_bearing`,
  `test_goto_fail_bearing_26_deg`, `test_goto_uses_true_tag_of_label_not_claim` (the agent's map
  position is wrong but the robot is truly close → success; the map is right but the robot is far →
  failure), `test_return_success_0_30`, `test_no_done_is_failure`, `test_explore_budget_counts`,
  `test_spl_hand_computed` (S 1, ℓ 1.0, p 1.25 → 0.8), `test_ell_zero_when_starting_inside`.
- `tests/test_metrics_exploration.py` (3): `test_curve_monotone_fraction`, `test_time_to_90_and_99`,
  `test_never_reached_returns_none`.
- `tests/test_metrics_refusal.py` (4): `test_refusal_rate`, `test_unsafe_followed_by_move_counted`,
  `test_false_refusal_rate`, `test_ask_correct_only_for_ambiguous_valid`.
- Command (Mac): `../.venv/bin/python -m pytest -q tests/test_metrics_missions.py
  tests/test_metrics_exploration.py tests/test_metrics_refusal.py` → `15 passed`.
- Smoke (Spark host): `score` on the M2.T19 run — every GO_TO/RETURN row has `mission_success` and `spl`
  filled; EXPLORE rows have `t90_*` or an empty value with the curve's final fraction < 0.9.

**Acceptance criteria.**
- [ ] `15 passed` on the Mac; full suite on the Spark host.
- [ ] Smoke CSV saved with the stated columns filled.

**Evidence to save** (`evidence/M2/M2.T20/`). `pytest_mac.txt`, `pytest_spark_host.txt`, `smoke/episodes.csv`.

**Pitfalls and known gotchas.** Success is evaluated at the **first** DONE. The target of `GO_TO_BEACON
B3b` is the second physical tag the agent labelled with ID 3 — resolve it through the identity map, not by
ID. Bearing for GO_TO success is measured from the robot's ground-truth heading to the true tag centre.

**Stop-and-ask conditions.** None beyond §1.4.

**Estimated effort.** S.

**AI-disclosure note.** `AI-assisted: <model> via <tool>, <date>: wrote the mission, SPL, exploration and refusal metrics.`

---
### M2.T4 — URDF of the car (`beaconmind_description`) from `configs/car.json`

**Subagent.** The subagent that writes this URDF must be Claude Opus 5.5 at xhigh effort (Cursor model slug `claude-opus-5-5-xhigh`); do not use a different model for that task, as requested by Xiaohui on 2026-10-06. AI-assisted: Grok 4.7 via Cursor, 2026-10-06: recorded the URDF subagent model.

**Why.** The Isaac twin (W1, APPROACH §10) and the ROS graph's TF tree (`robot_state_publisher`, C12) need
one model of the car whose numbers come from the measured `configs/car.json` (M1.T9), with the frames of
C1 (`base_link` at the axle midpoint, x toward the camera/caster end) and **no range sensor** (D1a,
APPROACH §6).

**2026-10-29.** Status stays **blocked**. Do not regenerate the URDF in this pass. Besides `camera.json` and `car.json`, regeneration waits on M1.T16: the new whole-car mass, the two-scale split on that same configuration, and the bank box. A new total weight alone does not fix `com_x`. The ride-height check in M1.T16 does not by itself block the mass update: if those three rows exist and the ride-height row does not, update mass, centre of mass, and the bank box, and leave the 30 mm / 46 mm front / 43 mm rear heights. Lens pose stays the 2026-10-10 single readings until Xiaohui says the stand moved. Camera rpy stays 0, 0, 0 until M1.T7. `CAMERA_CONVENTION_SETTLED` stays false.

**2026-10-29 (late), done.** M1.T16's blocking rows exist, so the mass, the centre of mass and the bank box were updated as the paragraph above allows: `car.json` `mass_kg` 0.660 kg through a new CSV (`evidence/M1/M1.T9/measurements-2026-10-29-with-m1t16-mass.csv`) and the writer; `caster_load` / `drive_wheels_load` 0.058 / 0.602 kg and `com_x` 0.010545 m (Xiaohui's middle value) in `car_geometry_extras.xacro`; a geometry-only `power_bank` box on `chassis_link`. The 30 / 46 / 43 mm heights, the lens pose, camera rpy and the footprint keys did not change. Status stays **blocked** on M1.T7 and M2.T3. Record, runs and review: `evidence/M2/M2.T4/2026-10-29-m1t16/README.md`, which also lists notes for M2.T16 (caster lift at about 2.2 m/s², the bank's rear edge as first rear contact at about 11.8°, a physics material for the bank collider, self-collision off, the importer's expected massless-link warnings, and the model's 69.6 g static caster load against the 58 g weighed).

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M1.T3 done | task | `grep -E "^. M1\.T3 " course-project/plan/M1-foundations.md` (Mac) | Status `done` |
| M1.T7 and M1.T9 done | task | `grep -E -e "^. M1\.T7 " -e "^. M1\.T9 " course-project/plan/M1-foundations.md` (Mac) | both with Status `done` |
| M1.T16 blocking rows recorded | task | `evidence/M1/M1.T16/measurements.md` (Mac) | whole-car mass, two-scale split, and bank box are filled with Xiaohui's readings. **2026-10-29:** do not regenerate before this file exists. Ride height within 2 mm does not add a URDF height change |
| M2.T3 done (the `load_car` view) | task | `grep -E "^. M2\.T3 " course-project/plan/M2-sim-mvp.md` (Mac) | Status `done` |
| car view is measured | config | `cd course-project/beaconmind && ../.venv/bin/python -c "from beaconmind.config import load_car; v=load_car(); print(v['status'], v['assumptions'])"` (Mac) | `measured` and the assumptions list (paste it; `camera_rpy_deg` must **not** be in it, since camera.json exists) |
| Container up | service | `ssh … 'docker ps --format "{{.Names}}" \| grep -x beaconmind-ros'` (Mac) | `beaconmind-ros` (else `docker start beaconmind-ros` on the Spark host) |

**Inputs.** README C1, C12, L1, L4; AGENT-DESIGN D3, §W W1; `configs/car.json`; `reference/hardware/car-build-notes.md` (what the chassis looks like).

**Steps.**
1. *Mac.* README §1.2 steps 1–5.
2. *Spark container `beaconmind-ros`.* **Verification step:**
   `docker exec beaconmind-ros bash -lc 'source /opt/ros/humble/setup.bash && ros2 pkg prefix xacro && ros2 pkg prefix robot_state_publisher && ros2 pkg prefix tf2_ros'`.
   Three paths → continue. A `Package not found` → stop and ask: the M1.T3 Dockerfile needs
   `ros-humble-xacro`, `ros-humble-robot-state-publisher` or `ros-humble-tf2-ros` (an image change).
3. *Mac.* Create the `ament_python` package `course-project/ros2_ws/src/beaconmind_description/`:
   `package.xml` (depends: `xacro`, `robot_state_publisher`; test_depend: `python3-pytest`), `setup.py`
   (installs `urdf/`, `launch/`), `setup.cfg`, `resource/beaconmind_description`,
   `beaconmind_description/__init__.py`, `beaconmind_description/gen_props.py`,
   `urdf/beaconmind_car.urdf.xacro`, `launch/description.launch.py`, `test/test_urdf.py`.
4. *Mac.* `gen_props.py` (standard library plus `beaconmind.config`, which is installed in the Mac venv and
   in `beaconmind-ros`): `python gen_props.py --car <car.json> --camera <camera.json> --out <car_props.xacro>`
   reads the **view** `beaconmind.config.load_car(car, camera)` (M2.T3 step 2; never the raw M1 keys) and
   writes one `<xacro:property name="…" value="…"/>` per car value (`wheel_radius` = diameter/2,
   `track_width`, `axle_to_front`, `axle_to_rear`, `body_width`, `chassis_height`, `mass`, `camera_x/y/z`,
   `camera_roll/pitch/yaw` in radians, `imu_x/y/z`, `caster_x/y/z`) with a header comment naming the
   car.json and camera.json SHA-12s. `chassis_height_m` and `wheel_width_m` come from the view (M1.T9
   measures both; if the view's `assumptions` names them, the stand-ins 0.06 m and 0.025 m are used —
   visuals, collision height and inertia only, no metric depends on them).
5. *Mac.* `beaconmind_car.urdf.xacro` includes `car_props.xacro` and defines (C1 frames):
   - `base_link` (axle midpoint; no visual), fixed joint to `chassis_link` (box from `−axle_to_rear` to
     `+axle_to_front` in x, `body_width` wide, `chassis_height` tall, bottom at the axle; inertial box with
     `mass − 2·0.03 − 0.01` kg);
   - `left_wheel_joint` / `right_wheel_joint` (continuous, axis `0 1 0`) at `(0, ±track_width/2, 0)`;
     cylinder links of radius `wheel_radius`, mass 0.03 kg each (stand-in);
   - `caster_link` (fixed) at the caster position, a sphere of radius `wheel_radius + caster_z` so that it
     touches the floor (with `caster_z` negative below the axle); `xacro` must fail (`${…}` assertion or a
     negative radius check in `gen_props.py`) if that radius is ≤ 0; mass 0.01 kg;
   - `camera_link` (fixed) at `camera_x/y/z` with `camera_roll/pitch/yaw`; `camera_optical_frame` (fixed,
     `rpy = (−π/2, 0, −π/2)`, REP 103 optical: z forward, x right, y down);
   - `imu_link` (fixed) at `imu_x/y/z`.
   No `<sensor>`, no `<gazebo>` blocks, no lidar or ray elements.
6. *Mac.* `description.launch.py`: runs `xacro` on the file and starts `robot_state_publisher` with
   `robot_description` and `use_sim_time` (launch argument, default `false`).
7. *Mac.* `test/test_urdf.py` (below). Generate the props (repository root): `course-project/.venv/bin/python
   course-project/ros2_ws/src/beaconmind_description/beaconmind_description/gen_props.py --car
   course-project/configs/car.json --camera course-project/configs/camera.json --out
   course-project/ros2_ws/src/beaconmind_description/urdf/car_props.xacro`.
8. *Mac → Spark container.* Sync; then
   `docker exec beaconmind-ros bash -lc 'source /opt/ros/humble/setup.bash && cd /workspace/course-project/ros2_ws && colcon build --symlink-install --packages-select beaconmind_description && colcon test --packages-select beaconmind_description && colcon test-result --verbose'`.
9. *Spark container.* Smoke: write the expanded URDF for Isaac and check the TF. Open a shell in the
   container first: on the Spark host run `docker exec -it beaconmind-ros bash`, then:
   ```bash
   source /opt/ros/humble/setup.bash && source /workspace/course-project/ros2_ws/install/setup.bash
   xacro /workspace/course-project/ros2_ws/src/beaconmind_description/urdf/beaconmind_car.urdf.xacro > /workspace/course-project/sim/isaac/assets/beaconmind_car.urdf
   (ros2 launch beaconmind_description description.launch.py &) ; sleep 5
   timeout 5 ros2 run tf2_ros tf2_echo base_link camera_optical_frame
   ```
   Expected: the translation equals `camera.json` `extrinsics` (`x_m, y_m, z_m`) within 1 mm and the
   printed rotation (RPY in degrees) equals its `roll_deg, pitch_deg, yaw_deg` within 0.1°. Stop the
   launch afterwards (`pkill -f robot_state_publisher` inside the container only).
10. *Spark → Mac.* The expanded URDF was written on the Spark: pull it back in this session (L6), with
    `ssh -o BatchMode=yes xiaohui_chen@spark-2a60 'cd ~/Projects/EN.665.715 && tar czf - course-project/sim/isaac/assets/beaconmind_car.urdf' | tar xzf - -C /Users/xiaohuichen/Projects/EN.665.715`,
    then pull the evidence. Status, `CONTEXT.md`.

**Deliverables.** `ros2_ws/src/beaconmind_description/**` (files of step 3, plus the generated
`urdf/car_props.xacro`); `sim/isaac/assets/beaconmind_car.urdf` (expanded, tracked, small).

**Tests.** `ros2_ws/src/beaconmind_description/test/test_urdf.py` (9; each test runs `xacro` via
`subprocess` and parses the output with `xml.etree.ElementTree`):
`test_xacro_expands`, `test_link_names` (exactly `base_link, chassis_link, left_wheel_link,
right_wheel_link, caster_link, camera_link, camera_optical_frame, imu_link`),
`test_wheel_separation_equals_track_width`, `test_wheel_radius_half_diameter`,
`test_optical_frame_matches_camera_json` (the composed base_link → camera_optical_frame transform equals `camera.json` `extrinsics` within 1e-6 m and 1e-6 rad), `test_caster_touches_floor`, `test_no_range_sensor` (no `sensor`,
`ray`, `lidar`, `gpu_ray` anywhere), `test_total_mass_matches_car_json` (sum of link masses = `mass_kg`
± 1e-6), `test_props_up_to_date` (regenerating `car_props.xacro` from `car.json` gives identical text).
Command: step 8 → `colcon test-result` reports `9 tests, 0 errors, 0 failures, 0 skipped`.
Smoke: step 9 (TF translation within 1 mm).

**Acceptance criteria.**
- [ ] `colcon test-result`: 9 tests, 0 failures.
- [ ] `tf2_echo` output saved and within 1 mm and 0.1° of `camera.json` `extrinsics`.
- [ ] Expanded URDF saved under `sim/isaac/assets/`.

**Evidence to save** (`evidence/M2/M2.T4/`). `pkg_check.txt`, `colcon_test.txt`, `tf2_echo.txt`.

**Pitfalls and known gotchas.** The car's front is the camera/caster end (C1, D3); the drive wheels are at
the rear axle, so `axle_to_front` is the long overhang. Do not use the Module 5 tilt firmware's "forward"
(it is reversed, C1 warning). URDF angles are radians.

**Stop-and-ask conditions.** Step 2 (missing packages). `car.json` lacks a needed key (do not invent it;
M1.T9 must measure it).

**Estimated effort.** S.

**AI-disclosure note.** XML comment at the top of the xacro and launch files, docstrings in Python:
`AI-assisted: <model> via <tool>, <date>: wrote the URDF/xacro, generator, launch file and tests.`

---

### M2.T15 — Isaac arena: tag36h11 textures, arena builder from C7, render-and-decode spike

**Why.** The twin must render the generated arena with tag36h11 tags that the detector decodes (AGENT-DESIGN
§W W1: "The Isaac AprilTag material must render a tag36h11 that the detector decodes"; APPROACH §11 risk 4).
No AprilTag MDL or tag36h11 mosaic exists locally in the Spark's Isaac build or cache (checked
2026-10-05). The **default method** here is the one already proven in this repository for printed cards
in Isaac: a UV-mapped quad with `UsdPreviewSurface` and a PNG texture (`discussions/module2/sim/labels.py`
`attach_labels`: "A Mesh quad with st UVs + UsdPreviewSurface is 1:1 with the PNG"), with tag PNGs
generated by OpenCV's `DICT_APRILTAG_36h11` (verified to work on the Spark host, OpenCV 4.13.0). Appended
to M2 (split out of M2.T5).

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M1.T5 done | task | `grep -E "^. M1\.T5 " course-project/plan/M1-foundations.md` (Mac) | Status `done`; read `evidence/M1/M1.T5/` for the Isaac version (OD7) and the tag method that decoded |
| M2.T2 done | task | `grep -E "^. M2\.T2 " course-project/plan/M2-sim-mvp.md` (Mac) | Status `done` |
| Isaac path | tool | `ssh … 'ls ${ISAAC:-$HOME/IsaacSim/_build/linux-aarch64/release}/python.sh'` (Mac) | the path prints |
| No other kit running | service | `ssh … "pgrep -af '[k]it/kit\|[p]ython\.sh' \|\| echo 'kit clear'"` (Mac; the `[k]`/`[p]` brackets stop `pgrep -f` from matching the ssh shell's own command line, which contains the pattern) | `kit clear` (else stop and ask: someone else's Isaac job may be running) |

**Inputs.** README C7, C12, L5 (Isaac row); AGENTS.md §7.4 (Isaac row: headless only, `timeout
--kill-after=60`, kit hangs on shutdown); `discussions/module2/sim/labels.py` (`attach_labels`,
`plant_visual_labels` — the textured-quad method and its kit-cache copy), `discussions/module2/sim/render_carter.py`
(SimulationApp keys, Replicator `rgb` annotator), `discussions/module2/VIDEO-CAPTURE.md`; M1.T5 evidence.

**Steps.**
1. *Mac.* README §1.2 steps 1–5. Read `evidence/M1/M1.T5/`. **Branch:** if M1.T5 chose Isaac 6.0, set
   `ISAAC` to the 6.0 build path it recorded in every command below. **M1.T5 tests only the AprilTag MDL
   material; this task's render-and-decode spike is the first test of the texture method** (cross-plan
   consistency review, 2026-10-06). Branches: texture spike passes → continue with textures (record in
   the evidence that M1.T5's MDL result was not used, and why). Texture spike fails and M1.T5's MDL
   decoded → stop and ask whether to switch this task to the MDL method (the steps below are written for
   textures). Both fail → stop and ask (README §3.4 Isaac fallback).
2. *Mac.* `course-project/sim/isaac/make_tag_textures.py` (runs with the Spark **host** `python3`, which
   has OpenCV 4.13): for each ID it writes `assets/tags/tag36h11_<id>.png` = `cv2.aruco.generateImageMarker(
   dict, id, 8·cell_px, borderBits=1)` (the 8×8-cell black-bordered marker) padded with one white cell on
   each side → 10 × 10 cells (black 0.16 m + white border → 0.20 m, D3), `cell_px = 32` (320 × 320 px),
   then decodes each PNG with `cv2.aruco.ArucoDetector(dict)` and prints `id <k> decoded <k>`; exit 1 on
   any mismatch. CLI: `--ids 0-29,100-109 --cell-px 32 --out <dir>`.
3. *Spark host.* `cd ~/Projects/EN.665.715/course-project && python3 sim/isaac/make_tag_textures.py --ids 0-29,100-109 --cell-px 32 --out sim/isaac/assets/tags`
   → 40 lines `id k decoded k`.
4. *Mac.* Pure geometry in `beaconmind/worlds.py`: `arena_geometry(world, wall_thickness_m=0.02,
   tag_offset_m=0.002) -> dict` with `walls` (`[{name, center: [x, y, z], size: [sx, sy, sz]}]`, inner faces
   exactly on x = 0, x = W, y = 0, y = H) and `tags` (`[{uid, id, center, normal, corners}]`, centre moved
   `tag_offset_m` along the inward normal, `corners` = the 0.20 m square's four corners ordered
   top-left, top-right, bottom-right, bottom-left **as seen by a viewer inside the arena facing the tag**,
   to receive UVs (0,1), (1,1), (1,0), (0,0)). Tests in `beaconmind/tests/test_arena_geometry.py`.
5. *Mac.* `course-project/sim/isaac/bm_arena.py` (Isaac Python 3.11; adds
   `course-project/beaconmind/src` to `sys.path` and imports `beaconmind.worlds`): `build_arena(stage,
   world, tex_dir, root="/World/Arena") -> dict` — a ground plane, four static wall cubes
   (`UsdGeom.Cube`, scaled, with `UsdPhysics.CollisionAPI`; light grey), tag quads authored as
   `UsdGeom.Mesh` with `st` primvars and a `UsdPreviewSurface` + `UsdUVTexture` material per ID
   (two-sided), textures copied into a kit-readable cache folder first (the `plant_visual_labels`
   pattern), a `DomeLight` and a `DistantLight`. Plant the tags **after** `World.reset()` (Module 2
   finding). Returns prim paths. Disclosure: derived from `labels.py:attach_labels`.
6. *Mac.* `course-project/sim/isaac/render_arena_still.py` (standalone `python.sh` script; parse args
   **before** creating `SimulationApp`, as `render_carter.py` does): `--world <json> --pose x y theta_deg
   --cam-height <m> --hfov-deg 60 --width 640 --height 480 --out <png>`; builds the arena, places a
   `UsdGeom.Camera` at the pose looking along +x of the robot (USD cameras look along −Z with +Y up:
   rotate accordingly), focal length from HFOV with the default horizontal aperture, renders a few frames
   with a Replicator `rgb` annotator, saves the last frame, prints `DONE <png>`. Until M1.T7's intrinsics
   are used (M2.T16), HFOV 60° is the D3 design value.
7. *Mac.* `course-project/sim/isaac/decode_still.py <png> --world <json> --pose x y theta_deg` (host
   `python3`): decodes with `cv2.aruco` (`DICT_APRILTAG_36h11`) and compares with the tags **expected**
   to be visible: those within the 60° field of view, ≤ 1.5 m and ≤ 45° incidence from the camera position
   (computed with `beaconmind.envs.kinsim.tag_view_geometry`; the script inserts
   `course-project/beaconmind/src` into `sys.path` itself, because the host `python3` that has OpenCV does
   not have the `beaconmind` package installed). Prints `expected`, `decoded`, `missing`, `wrong` lists.
8. *Spark host.* Sync. Render and decode 5 poses in each of `sim-dup-s1000` and `sim-dup-s1001` (the
   start pose plus four poses chosen by hand facing different walls; write them into
   `evidence/M2/M2.T15/poses.json`):
   ```bash
   ISAAC=${ISAAC:-$HOME/IsaacSim/_build/linux-aarch64/release}; C=$HOME/Projects/EN.665.715/course-project
   mkdir -p $C/data/renders/logs
   cd $ISAAC && timeout --kill-after=60 900 ./python.sh $C/sim/isaac/render_arena_still.py --world $C/data/worlds/sim-dup-s1000.json \
     --pose 1.10 0.95 30 --cam-height 0.12 --hfov-deg 60 --out $C/data/renders/m2t15_s1000_p0.png > $C/data/renders/logs/m2t15_s1000_p0.log 2>&1; \
   pgrep -af '[k]it/kit|[p]ython\.sh' && pkill -9 -f '[r]ender_arena_still.py'; python3 $C/sim/isaac/decode_still.py $C/data/renders/m2t15_s1000_p0.png \
     --world $C/data/worlds/sim-dup-s1000.json --pose 1.10 0.95 30
   ```
   (one line per pose; replace the pose with each entry of `poses.json`). The first run may download
   nothing (no remote assets are used); expect 1–3 minutes per run.
9. *Spark → Mac.* Pull evidence (copy 2 of the PNGs into the evidence folder, each < 1 MB) **and** the 40
   tag textures, which were generated on the Spark and are tracked (L6: pull back in the same session):
   `ssh -o BatchMode=yes xiaohui_chen@spark-2a60 'cd ~/Projects/EN.665.715 && tar czf - course-project/sim/isaac/assets/tags' | tar xzf - -C /Users/xiaohuichen/Projects/EN.665.715`;
   then on the Mac `ls course-project/sim/isaac/assets/tags | wc -l` → `40`.
10. Status, `CONTEXT.md`.

**Deliverables.** `sim/isaac/{make_tag_textures,bm_arena,render_arena_still,decode_still}.py`;
`sim/isaac/assets/tags/*.png` (40 files, tracked); `beaconmind/worlds.py` (`arena_geometry`);
`beaconmind/tests/test_arena_geometry.py`, `beaconmind/tests/test_tag_textures.py`.

**Tests.**
- `tests/test_arena_geometry.py` (5): `test_wall_inner_faces_on_boundary`, `test_tag_corners_0_20_apart`,
  `test_tag_centre_offset_along_normal`, `test_corner_order_not_mirrored` (from inside the arena, corner 0→1
  points to the viewer's right), `test_tag_count_matches_world`.
- `tests/test_tag_textures.py` (3, `pytest.importorskip("cv2")`, so they skip where OpenCV is absent):
  `test_png_is_320_px`, `test_white_border_one_cell`, `test_decodes_to_own_id_for_0_29_and_100_109`.
  Run them on the Spark host with the system Python, which has OpenCV:
  `cd ~/Projects/EN.665.715/course-project/beaconmind && PYTHONPATH=src python3 -m pytest -q tests/test_tag_textures.py`
  → `3 passed`. If that prints `No module named pytest`, record "not executed — system python3 has no
  pytest" and rely on step 3's 40 `decoded` lines (they assert the same thing); do not `pip install` into
  the system Python.
- Command (Mac): `../.venv/bin/python -m pytest -q tests/test_arena_geometry.py` → `5 passed`.
- Smoke (Spark host, step 8): for all 10 renders, `missing` and `wrong` are empty (every expected tag
  decoded with the right ID, no wrong ID). Paste the 10 decode outputs.

**Acceptance criteria.**
- [ ] 40 textures decode to their own IDs (step 3 output).
- [ ] `5 passed` (geometry) and the texture tests pass where OpenCV exists.
- [ ] 10 renders: no missing and no wrong IDs; two example PNGs saved.

**Evidence to save** (`evidence/M2/M2.T15/`). `textures.txt`, `pytest_mac.txt`, `poses.json`,
`decode_results.txt`, `render_s1000_p0.png`, `render_s1001_p2.png`, `kit_log_tail.txt` (last 40 lines of
one kit log).

**Pitfalls and known gotchas.** Kit hangs on shutdown — `timeout --kill-after=60` plus `pkill -9` of the
script name, never a blanket `pkill python`. Parse arguments before `SimulationApp` (kit consumes argv). A
mirrored texture never decodes (the corner-order test exists for this). `VisualCuboid` + `OmniPBR` smeared
the PNG in Module 2 (`labels.py` docstring); use the mesh quad. Livestreaming is unsupported on aarch64:
judge renders by the saved PNGs.

**Stop-and-ask conditions.** Another Isaac job is running. A tag in plain view fails to decode in two
renders after one fix attempt on lighting or texture resolution (report the PNG): this is the W1 risk and
may trigger the README §3.4 fallback question.

**Estimated effort.** M.

**AI-disclosure note.** `AI-assisted: <model> via <tool>, <date>: wrote the tag texture generator, arena builder and render/decode scripts.`
`bm_arena.py` adds `Derived from: EN.665.715/discussions/module2/sim/labels.py:attach_labels,plant_visual_labels (copied from this repository and adapted, <date>)`.

---
### M2.T16 — Isaac car: URDF import, differential drive, calibrated camera, ground truth, ROS 2 publishing

**Why.** W1 (APPROACH §10): import the URDF, add a differential-drive controller, match the camera to the
calibration, no range sensors, ground truth, and publish the C12 topics so the twin and the car look the
same to the harness. Appended to M2 (split out of M2.T5).

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M2.T4, M2.T15 done | task | `grep -E -e "^. M2\.T4 " -e "^. M2\.T15 " course-project/plan/M2-sim-mvp.md` (Mac) | both with Status `done` |
| M1.T7 done, camera.json | task/config | `python3 -c "import json; d=json.load(open('course-project/configs/camera.json')); K=d['camera_matrix']; print(d['image_width'], d['image_height'], K[0], K[4], K[2], K[5], sorted(d['extrinsics']))"` (Mac) | width, height, fx, fy, cx, cy and the extrinsics keys (`bm.camera/1`, M1.T2: `camera_matrix` is row-major 3×3, so fx = K[0], fy = K[4], cx = K[2], cy = K[5]). A `KeyError` → stop and ask (§1.4 item 3) |
| UDP-only FastDDS profile in the project | file | `ls course-project/docker/fastdds_udp.xml` (Mac) | listed (M1.T3); if absent use `discussions/module2/sim/fastdds_udp.xml` and say so |
| Isaac topics reach the container (M1.T3) | evidence | `ls course-project/evidence/M1/M1.T3/` (Mac) | contains the UDP-only reception proof |

**Inputs.** README C1, C8, C12 (and the UDP-only note), L5; `discussions/module2/sim/sim_server.py` (World,
`WheeledRobot`, `DifferentialController`, ROS bridge enable, HTTP shim pattern),
`discussions/module2/sim/launch_sim_server.sh` (environment for the Humble bridge, UDP-only),
`discussions/module2/HANDOFF.md`; the Isaac docs in the build: `exts/isaacsim.asset.importer.urdf/docs/api.rst`
(import commands), `exts/isaacsim.ros2.bridge/ogn/docs/OgnROS2CameraHelper.rst`,
`OgnROS2CameraInfoHelper.rst`, `OgnROS2PublishClock.rst`, `OgnROS2PublishOdometry.rst`,
`OgnROS2PublishRawTransformTree.rst` (node inputs and type names).

**Steps.**
1. *Mac.* README §1.2 steps 1–5.
2. *Spark host.* **Verification step — names in this Isaac build** (all read-only):
   ```bash
   I=${ISAAC:-$HOME/IsaacSim/_build/linux-aarch64/release}
   grep -n "def apply_wheel_actions\|def get_joint_positions\|def get_world_pose" -r $I/exts/isaacsim.robot.wheeled_robots $I/exts/isaacsim.core.api 2>/dev/null | head
   grep -n "def forward" $I/exts/isaacsim.robot.wheeled_robots/isaacsim/robot/wheeled_robots/controllers/differential_controller.py
   grep -n "def set_focal_length\|def set_horizontal_aperture\|def set_opencv_pinhole_properties\|def set_resolution" -r $I/exts/isaacsim.sensors.camera | head
   for f in ROS2CameraHelper ROS2CameraInfoHelper ROS2PublishClock ROS2PublishOdometry ROS2PublishRawTransformTree ROS2Context; do grep -m3 -n "Node Type\|^ *inputs:\|Unique ID\|isaacsim\.ros2\.bridge\.$f" $I/exts/isaacsim.ros2.bridge/ogn/docs/Ogn$f.rst; done
   ls $I/exts/isaacsim.core.nodes/ogn/docs/ | grep -E "CreateRenderProduct|ComputeOdometry|ReadSimulationTime"
   ```
   Write down the exact method names, node type IDs and input names you found in
   `evidence/M2/M2.T16/api_names.txt`. Use **only** these names in steps 4–6. A needed name missing →
   search the docs folder for the 5.1 equivalent; nothing found → stop and ask (§1.4 item 3).
3. *Spark host.* Import the car once (URDF → USD). Write `course-project/sim/isaac/import_car.py`:
   headless `SimulationApp`, `enable_extension("isaacsim.asset.importer.urdf")`, then the documented
   commands `URDFCreateImportConfig` (set `merge_fixed_joints = False` so `camera_link` and
   `camera_optical_frame` survive, `fix_base = False`, `import_inertia_tensor = True`, `convex_decomp =
   False`, `collision_from_visuals = False`) and `URDFParseAndImportFile` with
   `urdf_path=sim/isaac/assets/beaconmind_car.urdf`; save the stage to `sim/isaac/assets/beaconmind_car.usd`
   (if the command accepts a destination path use it, else save with the USD context; record which in
   `api_names.txt`). Run it under `timeout --kill-after=60 600`. **Branches:**
   - The extension fails to enable headless (its UI dependencies) → retry once with the full experience
     file (`SimulationApp(config, experience=f"{ISAAC}/apps/isaacsim.exp.full.kit")`, the
     `render_carter.py` pattern). Still failing → stop and ask, proposing (b): author the USD directly
     with `pxr` (`UsdPhysics.ArticulationRootAPI`, `RevoluteJoint` with `DriveAPI` for the wheels,
     `FixedJoint` for the rest), which is library use, not copying.
   - The import succeeds → print the prim tree (joint names must include `left_wheel_joint` and
     `right_wheel_joint`).
4. *Mac.* `course-project/sim/isaac/bm_twin.py` (standalone, Isaac Python 3.11; parse args before
   `SimulationApp`) — **part 1 of the twin** (M2.T5 adds the move server):
   - Args: `--world <json> --car-usd <usd> --car-json <json> --camera-json <json> --physics-hz 120
     --camera-hz 10 --hold-seconds 3600 --port 8200 --ros 1`.
   - Environment (set by `run_twin.sh` in M2.T5; for this task export it by hand as in
     `discussions/module2/sim/launch_sim_server.sh`): `ROS_DISTRO=humble`,
     `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`, `ROS_DOMAIN_ID=0`, `LD_LIBRARY_PATH+=:$ISAAC/exts/isaacsim.ros2.bridge/humble/lib`,
     `FASTRTPS_DEFAULT_PROFILES_FILE=<project fastdds_udp.xml>`, `FASTDDS_BUILTIN_TRANSPORTS=UDPv4`.
     Never source `/opt/ros/jazzy` in this shell.
   - `World(stage_units_in_meters=1.0, physics_dt=1/physics_hz, rendering_dt=1/physics_hz)`; arena via
     `bm_arena.build_arena`; the car with `WheeledRobot(prim_path="/World/Car", wheel_dof_names=
     ["left_wheel_joint", "right_wheel_joint"], create_robot=True, usd_path=<car usd>, position=start,
     orientation=yaw quaternion)` (the `sim_server.py` pattern); `DifferentialController(name="diff",
     wheel_radius=D/2, wheel_base=track_width)`. Physics materials: wheels static/dynamic friction 1.0,
     caster 0.0 (stand-ins: sim parameters, not DVs).
   - Camera under `/World/Car/camera_link`: resolution (`image_width`, `image_height`) and intrinsics
     from `camera.json` (`camera_matrix` K: fx = K[0], fy = K[4], cx = K[2], cy = K[5]; the pose of
     `camera_link` comes from the URDF, which M2.T4 built from `camera.json` `extrinsics`) → focal length and apertures: `horizontal_aperture = width · pixel_size`, `focal = fx · pixel_size`,
     with `pixel_size` chosen as `horizontal_aperture / width` for the default aperture; principal-point
     offset via the aperture offsets, or via `set_opencv_pinhole_properties` if step 2 found it — prefer
     that). **Sim default: an undistorted pinhole with the calibrated K**, and `camera_info` with zero
     distortion; the detector runs on rectified images on the car too, so the residual difference is the
     rectification error (state this in the docstring; proposed default, M2.T6 checks the detection error).
     Orientation: the USD camera looks along its −Z with +Y up; relative to `camera_link` (x forward, z
     up) its axes are X_cam = −Y_link, Y_cam = +Z_link, Z_cam = −X_link.
   - No lidar, no range sensor, no contact sensor exposed to ROS (D1a).
   - OmniGraph (one action graph, node types and input names from step 2): on playback tick → render
     product of the camera → `ROS2CameraHelper` (`rgb`, topic `/camera/image_raw`, frame
     `camera_optical_frame`) and `ROS2CameraInfoHelper` (topic `/camera/camera_info`), throttled to
     `--camera-hz` (frame-skip input if the node has one, else render every `physics_hz/camera_hz` steps);
     `ROS2PublishClock` (`/clock`); odometry from the chassis (`IsaacComputeOdometry` →
     `ROS2PublishOdometry` on `/odom`, frames `odom`/`base_link`, and `ROS2PublishRawTransformTree`
     `odom → base_link`).
   - Ground truth: a function `gt_pose_world()` reading the chassis world pose (x, y, yaw in degrees);
     printed every second as `GT x y yaw` in the kit log, and served by the HTTP `/state` endpoint added in
     M2.T5. For this task add a minimal HTTP server (the `sim_server.py` `ThreadingHTTPServer` + queue
     pattern, copied with disclosure) with only `GET /ready`, `GET /state` and `POST /drive_test` (runs a
     fixed open-loop wheel command for a given time: body `{"v_mps", "w_dps", "seconds"}`).
   - Prints `READY port <p>` when the world is playing and the graph is built.
5. *Spark host.* Start it (one kit at a time). In a fresh shell (never one that sourced `/opt/ros/jazzy`):
   ```bash
   export ISAAC=${ISAAC:-$HOME/IsaacSim/_build/linux-aarch64/release} C=$HOME/Projects/EN.665.715/course-project
   export ROS_DISTRO=humble RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_DOMAIN_ID=0 FASTDDS_BUILTIN_TRANSPORTS=UDPv4
   export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}:$ISAAC/exts/isaacsim.ros2.bridge/humble/lib"
   export FASTRTPS_DEFAULT_PROFILES_FILE=$C/docker/fastdds_udp.xml   # or discussions/module2/sim/fastdds_udp.xml (prerequisite row)
   mkdir -p $C/data/renders/logs
   ```
   then `cd $ISAAC && setsid nohup timeout --kill-after=60 1800 ./python.sh $C/sim/isaac/bm_twin.py --world $C/data/worlds/sim-dup-s1000.json --car-usd $C/sim/isaac/assets/beaconmind_car.usd --car-json $C/configs/car.json --camera-json $C/configs/camera.json < /dev/null > $C/data/renders/logs/m2t16_twin.log 2>&1 &`
   then poll `grep -m1 READY $C/data/renders/logs/m2t16_twin.log` every 10 s for up to 5 minutes.
6. *Spark host.* Drive test (open loop):
   `curl -s -X POST localhost:8200/drive_test -d '{"v_mps": 0.10, "w_dps": 0, "seconds": 2.5}'` and
   `curl -s -X POST localhost:8200/drive_test -d '{"v_mps": 0, "w_dps": 45, "seconds": 0.6667}'`, with
   `curl -s localhost:8200/state` before and after each. Pass (sim acceptance, proposed): straight
   0.25 ± 0.02 m with |lateral| ≤ 0.01 m and |Δθ| ≤ 1°; turn 30 ± 2° with the axle midpoint moving ≤
   0.01 m. Fail → check wheel radius/track width in the USD vs `car.json`, the friction materials, then
   stop and ask after two attempts.
7. *Spark container `beaconmind-ros`.* Topic checks (UDP-only profile active in the container as M1.T3
   set it up):
   ```bash
   source /opt/ros/humble/setup.bash
   timeout 15 ros2 topic hz /camera/image_raw ; timeout 10 ros2 topic echo --once /camera/camera_info
   timeout 10 ros2 topic hz /odom ; ros2 topic list | grep -E "lidar|scan|range|point" || echo "no range topics"
   ```
   Pass: image ≥ 5 Hz (the camera-hz target is 10); `camera_info.k` equals `camera.json` fx, fy, cx, cy within
   0.5 px; `/odom` publishes; `no range topics`.
   **Branch — images not arriving or < 5 Hz while `/odom` arrives:** the Module 2 DDS close proved only
   `/chassis/odom` over UDP-only (`discussions/module2/HANDOFF.md` §0 item (d): render products were never
   sent over DDS), so camera images over UDP are **unverified**. Record `ros2 topic hz` and
   `ros2 topic bw /camera/image_raw` output, check `ls /dev/shm | grep -c fastrtps_port` is 0, then stop
   and ask (§1.4 item 3) with these options: (a) lower `--camera-hz` to 5; (b) raise the UDP socket
   buffers in both FastDDS profiles (an XML change to record); (c) a lower render resolution with K scaled
   by the same factor (the detector then sees fewer pixels per tag; re-run M2.T15's decode check).
   Do not change the calibration file.
8. *Spark container + host.* **Projection check** (is the camera really the calibrated camera?): start
   `description.launch.py` (M2.T4) with `use_sim_time:=true`; save one frame
   (`ros2 run image_view extract_images` if installed, else a 20-line `rclpy` script
   `sim/isaac/grab_frame.py` that writes one `/camera/image_raw` message to PNG); with the twin's car at
   the world start pose facing a tag 0.8–1.2 m away (choose the pose with `--start` override or a
   `drive_test`), run on the host `python3 sim/isaac/pnp_check.py <png> --camera-json configs/camera.json
   --tag-size 0.16 --world … --gt "<x y yaw from /state>"`: `cv2.aruco` corners → `cv2.solvePnP`
   (`SOLVEPNP_IPPE_SQUARE`) → tag range and bearing from the axle midpoint (camera extrinsics from
   `camera.json` `extrinsics`, base_link → camera_optical_frame) compared with ground truth. `pnp_check.py`
   runs with the host `python3` (it has OpenCV 4.13) and inserts `course-project/beaconmind/src` into
   `sys.path` for `beaconmind.worlds`. Pass: range error ≤ 0.02 m, bearing error ≤ 1.0°.
9. *Spark host.* Stop the twin: `pkill -9 -f '[b]m_twin.py'` after saving `curl -s localhost:8200/state`.
   Confirm `pgrep -af '[k]it/kit|[p]ython\.sh' || echo 'kit clear'` (the brackets keep `pgrep -f` from
   matching its own shell when run through ssh).
10. *Spark → Mac.* Pull the evidence and, if `sim/isaac/assets/beaconmind_car.usd` is < 1 MB (tracked),
    the USD too (same `tar` pattern as M2.T15 step 9); otherwise move it to `data/assets/` on the Spark and
    record that path. Status, `CONTEXT.md` (record that the twin is stopped).

**Deliverables.** `sim/isaac/{import_car,bm_twin,grab_frame,pnp_check}.py`; `sim/isaac/assets/beaconmind_car.usd`
(tracked if < 1 MB, else keep it under `data/` and record the path); `evidence/M2/M2.T16/api_names.txt`.

**Tests.**
- No new pytest file (the Isaac code runs only inside `python.sh`); the checks are the smoke and
  measurement tests below, each with a threshold.
- Smoke: steps 5–7 (READY within 5 minutes; topics as stated).
- Measurement tests: step 6 (drive accuracy, 2 moves; repeat each 3 times — all 3 within tolerance),
  step 8 (projection: 3 poses at about 0.8, 1.0 and 1.2 m — all within tolerance).

**Acceptance criteria.**
- [ ] `api_names.txt` lists every Isaac name used, found in this build.
- [ ] The car USD has both wheel joints and the camera frames.
- [ ] Drive tests: 6 of 6 within tolerance. Topic checks pass. Projection: 3 of 3 within tolerance.
- [ ] The twin was stopped and `kit clear` recorded.

**Evidence to save** (`evidence/M2/M2.T16/`). `api_names.txt`, `import_car.txt`, `twin_ready.txt` (the
READY line and startup time), `drive_tests.csv` (command, before/after state, error), `topics.txt`,
`pnp_check.txt`, `frame_example.png` (< 1 MB), `kit_log_tail.txt`.

**Pitfalls and known gotchas.** Shared-memory transport between Isaac's FastDDS 2.6.10 and the container
fails silently (topics listed, no data): UDP-only is mandatory (`/dev/shm` must have no `fastrtps_port`
files: `ls /dev/shm | grep -c fastrtps_port` → 0). Rendering every physics step slows the simulation; render
at the camera rate. One `SimulationApp` per process. `merge_fixed_joints = True` would delete the camera
frames. The importer may rename prims; read the printed tree before writing paths.

**Stop-and-ask conditions.** Step 2 names missing. Step 3 both import routes fail. Step 7 images do not
arrive at ≥ 5 Hz (the branch there). Drive or projection tests fail after two attempts. Any sign that vLLM and Isaac together exceed memory (`free -g` < 10 GB available):
stop before the OOM killer acts (L5 memory note).

**Estimated effort.** M (two sessions: steps 1–3; steps 4–10).

**AI-disclosure note.** `AI-assisted: <model> via <tool>, <date>: wrote the car import, twin core and checks.`
`bm_twin.py` adds `Derived from: EN.665.715/discussions/module2/sim/sim_server.py:HTTP shim, WheeledRobot setup (copied from this repository and adapted, <date>)`.

---

### M2.T5 — Isaac twin complete: move server, `bm_sim_pico` (C2), headless runner, sim bringup

**Why.** The twin must accept the **same** bounded-move commands as the car over the same `/pico/*`
interface (C2, C12: "the harness cannot tell which it is driving except by `source`"), with the executor
behaviour the Pico will have (stop on encoders for straight moves, on the gyro for turns, stall detection,
timeout, watchdog), plus a headless runner that survives Isaac's shutdown hang. This completes M2.T5's
README meaning ("Isaac twin complete").

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M2.T16 done | task | `grep -E "^. M2\.T16 " course-project/plan/M2-sim-mvp.md` (Mac) | Status `done` |
| M2.T3 done | task | `grep -E "^. M2\.T3 " course-project/plan/M2-sim-mvp.md` (Mac) | Status `done` |
| `configs/odometry_noise.json` | config | `ls course-project/configs/odometry_noise.json` (Mac) | listed |

**Inputs.** README C2 (whole, including the wire format, caps and watchdog), C5.5, C12, §7 S2/S6/S7 (the
behaviours the real Pico must have — the twin copies them); AGENT-DESIGN D4, D6, §W W3 "motion" (stall
profile: 200 ms grace, then < 50 % of the profile over 200 ms); `discussions/module2/sim/launch_sim_server.sh`.

**Steps.**
1. *Mac.* README §1.2 steps 1–5.
2. *Mac.* `src/beaconmind/envs/pico_wire.py` (standard library; shared by `bm_sim_pico`, `ros_env.py` and,
   later, the real Pico bridge M3.T9): constants `OP = {"probe": 0, "forward": 1, "backward": 2,
   "turn_left": 3, "turn_right": 4}`, `RESULT_CODES = {0: "done", 1: "stalled", 2: "bumped", 3: "timeout",
   4: "link_lost", 5: "refused"}`; `encode_cmd(command: dict) -> list[int]` (C2 MoveCommand → `[cmd_seq, op,
   distance_mm, angle_cdeg, v_max_mmps, w_max_cdegps, timeout_ms]`, all non-negative magnitudes, the op
   carries the direction), `decode_cmd(data) -> dict`, `check_caps(data, dv) -> str | None` (C2 caps:
   `distance_mm ≤ 250`, `angle_cdeg ≤ 3000`, speed ≤ `v_max_mps`, `timeout_ms ≤ 5000`; returns the
   refusal reason), `encode_result(result: dict) -> list[int]` and `decode_result(data, car) -> dict`
   (C2 MoveResult; ticks → `achieved_forward_m` with `observation.ticks_to_m`; `flags` bit 0 stall,
   bit 1 bump).
3. *Mac.* `src/beaconmind/envs/move_exec.py` — `class BoundedMoveController(car, dv)` (pure Python, used
   inside Isaac and tested on the Mac): `start(command, t, enc_left_m, enc_right_m, yaw_deg)`;
   `update(t, enc_left_m, enc_right_m, yaw_deg, body_speed_mps=None) -> tuple[float, float] | dict` (wheel
   angular-velocity targets in rad/s while running; the finished result dict when done); `abort(reason)`.
   Rules: straight moves run at `v_max_mps` (0.1 s linear ramp) and stop when the mean encoder travel
   reaches `|distance| − 0.002 m` → `done`; turns run at `w_max_dps` and stop when the yaw change reaches
   `|angle| − 0.3°` → `done`; **stall** (§W): after `stall_grace_ms`, if the encoder progress over the last
   `stall_window_ms` is < `stall_frac` × the commanded progress → `stalled`; **bump (sim proxy, proposed
   default; the real Pico uses the IMU, M3.T6)**: after the grace period, if `body_speed_mps` (ground truth)
   stays < 20 % of the commanded speed for 200 ms while the encoders advance ≥ 50 % of commanded → `bumped`;
   elapsed > `timeout_s` → `timeout`; `abort("watchdog")` → `link_lost`; `abort("estop")` → the mapping of
   **open decision OD15** (README §3.5; one mapping for the twin and the car, C12). **Verification step:**
   `grep -n "OD15" course-project/AGENT-DESIGN.md course-project/CONTEXT.md` (Mac). Settled → implement that.
   Not settled → stop and ask Xiaohui with the three options of README OD15 (the same question M3.T2 step 1
   asks; record the answer in `CONTEXT.md` as `OD15: <option>, <date>` so M3.T2 does not ask again). The
   default is option (a): `link_lost` with reason `"estop"` and `flags` bit 2 set by `encode_result`.
   (An earlier draft mapped estop to `refused`; the cross-plan consistency review of 2026-10-06 replaced
   that with OD15.)
4. *Mac.* Extend `sim/isaac/bm_twin.py` with the move server: `POST /move` (body: MoveCommand JSON; runs
   `BoundedMoveController` in the main loop, stepping physics until it returns a result; replies with the
   result plus `gt_pose_world`, ideal encoder ticks and the ideal gyro change (ground-truth yaw)),
   `POST /halt` (aborts with the given reason), `POST /reset` (teleports the car to the world start pose,
   zero velocities), `GET /state` (`t_sim, gt_pose_world, enc_left_m, enc_right_m, yaw_deg, moving`). One
   Isaac process serves one world (restart per world: simpler and avoids re-planting tags).
5. *Mac.* `course-project/sim/isaac/run_twin.sh <world.json> [port]` and `stop_twin.sh`: export the
   environment of M2.T16 step 4, `mkdir -p data/renders/logs`, refuse to start if `pgrep -af '[k]it/kit'`
   finds a kit, start `bm_twin.py` with `setsid nohup timeout --kill-after=60 $((HOLD+300))` (HOLD default
   3600), wait for `READY` (≤ 300 s, else print the log tail and exit 1), print `TWIN_PID <pid>`;
   `stop_twin.sh` kills the process group and `pkill -9 -f '[b]m_twin.py'`, then prints `kit clear` if
   nothing is left. Header comment block with the disclosure.
6. *Mac.* ROS package `ros2_ws/src/beaconmind_robot/` (`ament_python`): node `bm_sim_pico`
   (`beaconmind_robot/sim_pico.py`, entry point `sim_pico`), Python 3.10, imports `beaconmind.envs.pico_wire`:
   - Subscribes `/pico/move/cmd` (`std_msgs/Int32MultiArray`), `/pico/heartbeat` (`std_msgs/Int32`),
     `/pico/arm` (`std_msgs/Int32`), `/estop` (`std_msgs/Bool`); publishes `/pico/move/result`,
     `/pico/state` (5 Hz), `/pico/imu` (10 Hz), `/pico/wheels` (10 Hz), `/ground_truth/pose`
     (`geometry_msgs/PoseStamped`, frame `world`, 10 Hz and right after every move).
   - **Boots disarmed** (D6); `/pico/arm` 1 arms, 0 disarms; a command while disarmed or failing
     `check_caps` → result `refused` without calling the twin; op 0 probe → `done` with no motion.
   - A valid command → `POST /move` on the twin in a worker thread; while it runs, if the heartbeat age
     exceeds `watchdog_ms` → `POST /halt {"reason": "watchdog"}`; `/estop` true → `POST /halt {"reason":
     "estop"}` and disarm.
   - Odometry noise from `configs/odometry_noise.json` applied to the **reported** ticks and gyro (the
     same model as kinsim: per-move wheel scale errors and gyro noise, RNG key `<rng_key>:odo:<cmd_seq>`),
     never to ground truth.
   - Parameters: `twin_url` (`http://127.0.0.1:8200`), `car_json`, `dv_json`, `odometry_noise_json`,
     `rng_key`, `boot_id` (default 1).
   - Also a small CLI `beaconmind_robot/move_probe.py` (entry point `move_probe`): `--arm` (operator arm),
     sends a list of actions (`--actions FORWARD_25,TURN_LEFT_30,…`), heartbeats at 10 Hz, prints each
     result and the ground-truth change.
7. *Mac.* ROS package `ros2_ws/src/beaconmind_bringup/` (`ament_python`): `launch/sim.launch.py` with
   arguments `world`, `rng_key`, `use_sim_time` (default `true`): `robot_state_publisher` (M2.T4),
   `bm_sim_pico`. (M2.T6 adds `image_proc` and `apriltag_ros`.) `config/` holds parameter YAML.
8. *Mac.* Unit tests (below); run on the Mac. Sync.
9. *Spark container.* `colcon build --symlink-install && colcon test && colcon test-result --verbose`
   (README L4 command) for all packages.
10. *Spark host + container.* Integration: `bash sim/isaac/run_twin.sh data/worlds/sim-dup-s1000.json`;
    in the container `ros2 launch beaconmind_bringup sim.launch.py world:=… rng_key:=m2t5` (in a `tmux`
    window `bm` on the Spark host via `docker exec -it`), then
    `ros2 run beaconmind_robot move_probe --arm --actions FORWARD_25,BACKWARD_10,TURN_LEFT_30,TURN_RIGHT_30,FORWARD_10,BACKWARD_10,TURN_RIGHT_30,TURN_LEFT_30,FORWARD_10,BACKWARD_10`.
    (This order keeps the axle midpoint within 0.25 m of the start position along its start heading —
    the turns cancel — so the nose reaches at most 0.25 m + `axle_to_front_m` from the start, which is
    less than the C7 start clearance of 0.5 m when `axle_to_front_m` < 0.25 m. Check that inequality
    with the `car.json` view first; if it fails, stop and ask. Do not reorder.)
    Then the safety checks: (a) disarm (`ros2 topic pub --once /pico/arm std_msgs/Int32 "{data: 0}"`) and
    send FORWARD_10 → `refused`; (b) re-arm, send a command with `distance_mm` 300 via `ros2 topic pub
    --once /pico/move/cmd …` → `refused`; (c) start FORWARD_25 and publish `/estop` true 0.3 s later →
    the OD15 estop result (default (a): `link_lost`, reason estop, flags bit 2) within 0.5 s wall time of
    the estop message; (d) start FORWARD_25 with
    `move_probe --no-heartbeat` → `link_lost`. Stop everything (`stop_twin.sh`; Ctrl-C the launch).
11. Evidence, status, `CONTEXT.md`.

**Deliverables.** `beaconmind/envs/{pico_wire,move_exec}.py`; `sim/isaac/bm_twin.py` (move server);
`sim/isaac/{run_twin,stop_twin}.sh`; `ros2_ws/src/beaconmind_robot/**`; `ros2_ws/src/beaconmind_bringup/**`;
tests below.

**Tests.**
- `beaconmind/tests/test_pico_wire.py` (8): `test_encode_decode_roundtrip_each_action` (5 actions),
  `test_backward_uses_op2_positive_distance`, `test_caps_distance_300mm_refused`,
  `test_caps_angle_31deg_refused`, `test_caps_speed_refused`, `test_caps_timeout_6000ms_refused`,
  `test_result_flags_bits`, `test_decode_result_ticks_to_metres`.
- `beaconmind/tests/test_move_exec.py` (8, with a toy plant: ideal wheels, optional slip, optional blocked
  body): `test_forward_done_at_target`, `test_turn_done_on_yaw`, `test_backward`,
  `test_stall_when_wheels_blocked`, `test_no_stall_during_grace`, `test_bump_when_body_blocked_wheels_slip`,
  `test_timeout`, `test_abort_estop_per_od15_and_watchdog_link_lost` (estop → the OD15 result; watchdog → `link_lost`).
- Command (Mac): `../.venv/bin/python -m pytest -q tests/test_pico_wire.py tests/test_move_exec.py` → `16 passed`.
- `ros2_ws/src/beaconmind_robot/test/test_sim_pico_logic.py` (4, no ROS runtime needed: the node's pure
  helpers): `test_disarmed_refuses`, `test_caps_refuse_before_http`, `test_noise_applied_to_reported_only`,
  `test_boot_id_in_results`. `colcon test-result`: 4 tests (plus M2.T4's 9), 0 failures.
- Integration (step 10): 10 of 10 moves `done`; FORWARD_25 ground-truth displacement 0.25 ± 0.02 m,
  FORWARD_10 0.10 ± 0.015 m, BACKWARD_10 −0.10 ± 0.015 m, turns ±30 ± 2°; (a)–(d) give the stated results.

**Acceptance criteria.**
- [ ] `16 passed` on the Mac; `colcon test-result` 0 failures.
- [ ] Integration: all thresholds met; four safety behaviours shown; output pasted.
- [ ] The twin starts with `run_twin.sh` and stops with `stop_twin.sh` leaving `kit clear`.

**Evidence to save** (`evidence/M2/M2.T5/`). `pytest_mac.txt`, `colcon_test.txt`, `move_probe.txt`,
`safety_checks.txt`, `run_twin.txt` (startup lines and time to READY), `stop_twin.txt`.

**Pitfalls and known gotchas.** Never let the harness or a test arm the twin implicitly: arming is an
explicit operator flag (`--arm`), mirroring D6. The worker thread must not call Isaac APIs (only HTTP into
the main loop's queue, the `sim_server.py` pattern). `ros2 topic pub` without `--once` keeps publishing.
Sim time vs wall time: the watchdog runs on wall time in `bm_sim_pico` (as the real link would).

**Stop-and-ask conditions.** A move error exceeds tolerance after two attempts (check friction and the
controller first). The twin needs more than about 40 GB of system memory next to vLLM (`free -g`).

**Estimated effort.** M.

**AI-disclosure note.** Python and shell headers as L11; the launch file and `package.xml` carry the XML/Python comment form.

---

### M2.T6 — Simulated perception: `apriltag_ros` + PnP on the Isaac camera; sim-vs-real error; noise injection

**Why.** The same detection pipeline must run on the twin and on the car (C12: `image_proc` → `apriltag_ros`
→ observation builder), and the twin's detections must be degraded to the **measured** real noise (APPROACH
§6: "Detections are degraded with the real noise measured in the W2 pilot"). With duplicated IDs,
`apriltag_ros`'s TF frames (one frame name per ID) collide, so the tag pose is computed from each
detection's corners with a planar PnP that returns both ambiguity solutions (needed for
`detections_internal`, C3, and the conservative wall estimate, C5.3).

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M2.T5, M2.T13 done | task | `grep -E -e "^. M2\.T5 " -e "^. M2\.T13 " course-project/plan/M2-sim-mvp.md` (Mac) | both with Status `done` |
| M1.T8 done, measured noise | task/config | `cd course-project/beaconmind && ../.venv/bin/python -c "from beaconmind.config import load_detector_noise as f; v=f(); print(v['status'], v['assumptions'])"` (Mac) | `measured` and the assumptions list (paste it) |
| `apriltag_ros`, `image_proc` (M1.T3) | package | `docker exec beaconmind-ros bash -lc 'source /opt/ros/humble/setup.bash && ros2 pkg prefix apriltag_ros && ros2 pkg prefix image_proc'` (Spark host) | two paths (else OD11 alternative: see step 2) |
| OpenCV in the container | package | `docker exec beaconmind-ros bash -lc 'python3 -c "import cv2; print(cv2.__version__, hasattr(cv2, \"solvePnPGeneric\"))"'` (Spark host) | a version and `True` |

**Inputs.** README C1, C3 ("Detection pipeline", `detections_internal`), C5.3, C12, OD11; M1.T8 evidence
(the real error table and its bins); M1.T3 evidence (the `apriltag_ros` frame naming and message fields).

**Steps.**
1. *Mac.* README §1.2 steps 1–5.
2. *Spark container.* **Verification step — message fields:**
   `docker exec beaconmind-ros bash -lc 'source /opt/ros/humble/setup.bash && ros2 interface show apriltag_msgs/msg/AprilTagDetection'`.
   - Shows `id`, `family`, `centre`, `corners` (4 points) and `decision_margin` → continue.
   - Different field names → record them in `evidence/M2/M2.T6/msg_fields.txt` and use those.
   - `apriltag_ros` absent (M1.T3 chose the OD11 alternative) → implement `bm_tag_detector` (a node in
     `beaconmind_perception` running `cv2.aruco` with `DICT_APRILTAG_36h11` on `/camera/image_rect` and
     publishing the same per-detection data as JSON on `/beaconmind/tag_detections`), and tell Xiaohui.
3. *Mac.* `src/beaconmind/envs/tag_pnp.py` (imports `cv2` and `numpy` inside functions):
   `tag_poses_from_corners(corners_px, K, tag_size_m=0.16) -> list[dict]` — object points of the black
   square (z = 0) in the corner order of the detector; `cv2.solvePnPGeneric(…, flags=cv2.SOLVEPNP_IPPE_SQUARE)`
   → up to two solutions, each `{"t_cam": [x, y, z], "n_cam": [nx, ny, nz] (unit normal facing the camera:
   n·t < 0), "reproj_px"}`; and `to_base_link(solution, camera_extrinsics) -> {"x_m", "y_m",
   "normal_yaw_deg"}` (camera_optical_frame → `base_link` with `configs/camera.json` `extrinsics`, which
   is exactly that transform: `x_m, y_m, z_m, roll_deg, pitch_deg, yaw_deg`, M1.T2 schema `bm.camera-1`). **Corner order is
   a verification item:** keep two constants `ORDER_A` (the `apriltag` library order as documented in the
   message definition) and `ORDER_B` (reversed); step 6 picks the one that matches ground truth.
4. *Mac.* `src/beaconmind/observation.py`: `inject_sim_noise(frames, sim_extra, rng) -> list` — for
   `source == "sim"` only. `sim_extra` is the dict in `configs/sim_extra.json` (schema
   `schemas/bm.sim_extra-1.schema.json`, written by step 7): `{"schema": "bm.sim_extra/1",
   "range_sigma_a_m", "range_sigma_b", "bearing_sigma_a_deg", "bearing_sigma_b", "max_range_m",
   "max_incidence_deg", "p_keep_table": [{"range_m", "incidence_deg", "p_keep"}], "derived_from",
   "date"}`. Per frame item with range r and incidence i (the incidence comes from the item's
   `normal_yaw_deg[0]` and its position): add N(0, `range_sigma_a_m + range_sigma_b·r`) to range and
   N(0, `bearing_sigma_a_deg + bearing_sigma_b·r`) to bearing (converted back to x, y), drop items with r
   > `max_range_m` or i > `max_incidence_deg`, then drop each remaining item with probability `1 −
   p_keep` (nearest `p_keep_table` row, the same nearest-neighbour rule as `config.p_detect`). A missing
   `configs/sim_extra.json` → `inject_sim_noise` raises `FileNotFoundError` (no silent clean sim).
5. *Mac.* `src/beaconmind/envs/ros_env.py` — `class RosEnv` **part 1 (capture)**: `__init__(self, *, source,
   world=None, car, camera, dv, detector_noise, rng_key, twin_url=None, operator_arm=False)` creates an
   `rclpy` node `bm_observation_builder` (rclpy imported here, not at module level) with subscriptions to
   the detections topic, `/camera/camera_info`, `/pico/state`, `/pico/imu`, `/pico/wheels`,
   `/ground_truth/pose`, and a publisher for `/beaconmind/observation` and `/beaconmind/report`
   (`std_msgs/String`). `capture() -> Capture`: wait `obs_settle_s`, collect `obs_frames` detection messages
   (timeout 3 s → camera `stale`), convert each detection with `tag_pnp` (position from the solution with
   the lower reprojection error; both normal yaws kept), attach `uid` in simulation as the nearest world tag
   with that ID given the ground-truth pose (C8 "sim: from the renderer's tag poses"), apply
   `inject_sim_noise` when `source == "sim"`, read sensors and boot id from `/pico/state`, ground truth from
   `/ground_truth/pose`.
6. *Spark host + container.* **Calibration sweep** (single tag, ground truth exact). Add `POST /teleport
   {"x_m", "y_m", "theta_deg"}` to `bm_twin.py` (sim-only, used only here). Use a calibration world
   `beaconmind/tests/fixtures/worlds/calib_single_tag.json` (one tag, ID 7, on the east wall of a 3 × 3 m
   box; it deliberately fails `worlds.check` and is never used in experiments — its `condition` is
   `"calibration"`, outside the `bm.world-1` enum, so never validate it against that schema; `bm_twin.py`
   and `worlds.arena_geometry` must accept it without calling `check`). Script `sim/isaac/calib_sweep.py` (runs in the container with `rclpy`): for range
   0.30–1.80 m step 0.10, incidence 0°, 20°, 40°, 60°, and image bearing 0° and ±20°, teleport, wait,
   collect 20 frames **without** noise injection, and write per detection: true and measured range,
   bearing and normal yaw, decoded or not. First run 3 poses with each corner order; keep the order whose
   range error < 0.02 m (record it; neither → stop and ask). Then the full sweep →
   `evidence/M2/M2.T6/sim_detection_errors.csv`.
7. *Spark host.* `course-project/tools/compare_noise.py` (host venv): bins the sim errors exactly as M1.T8
   binned the real ones (read its bin edges from `evidence/M1/M1.T8/`), prints a table per bin (σ_real,
   σ_sim, detection rate real vs sim), and fits `sim_extra`: for range and for bearing separately,
   σ_extra(bin) = sqrt(max(0, σ_real² − σ_sim²)), then an ordinary least-squares line `a + b·r` through
   (bin centre range, σ_extra) with `a, b` clipped at ≥ 0; `max_range_m` = min(real `max_range_m`, largest
   sim range that decoded in ≥ 18 of 20 frames); `max_incidence_deg` likewise; `p_keep_table` = one row
   per bin with `p_keep = min(1, p_real / p_sim)` (`p_sim = 0` → `p_keep = 0`). Writes
   `configs/sim_extra.json` (it does **not** edit `detector_noise.json`, whose M1 schema it would break)
   with `derived_from` (both CSV paths) and the date, plus the schema file, and a before/after table into
   the evidence. **Check:** re-run the sweep's statistics with `inject_sim_noise` applied (in Python on the
   saved CSV, seeded) and confirm each bin's σ is within ±20 % of σ_real; paste that table. **If the sim error is larger than the real error in any bin** (the renderer is
   worse than the camera) → stop and ask: options are a higher render resolution or accepting it as a
   stated limitation.
8. *Mac.* Add `image_proc` (rectify, `/camera/image_raw` → `/camera/image_rect`) and `apriltag_ros`
   (family `36h11`, size 0.16, image `/camera/image_rect`, info `/camera/camera_info`, detections
   `/apriltag/detections`) to `sim.launch.py`, parameters in `beaconmind_bringup/config/apriltag.yaml`;
   a `beaconmind_perception` package with a console script `bm_observation_builder` that runs
   `RosEnv` standalone and publishes `/beaconmind/observation` once per `capture()` (for the M6 ROSA demo).
9. *Spark.* Smoke: twin on `sim-dup-s1000`, launch, then
   `docker exec beaconmind-ros bash -lc 'source /opt/ros/humble/setup.bash && cd /workspace/course-project && python3 -m beaconmind.envs.ros_env --capture-once --no-noise --world data/worlds/sim-dup-s1000.json'`
   (add this CLI: `--capture-once` builds one observation with `ObservationBuilder` and prints it with
   `det_truth` as JSON; `--no-noise` skips `inject_sim_noise`) prints one C3 observation and `det_truth`;
   compare its `det_truth` uids with `beaconmind.envs.kinsim.visible_uids(world, <the /ground_truth/pose
   reading>, car, noise)`.
10. Evidence, status, `CONTEXT.md`.

**Deliverables.** `beaconmind/envs/{tag_pnp,ros_env}.py` (part 1); `observation.inject_sim_noise`;
`sim/isaac/calib_sweep.py`; `bm_twin.py` (`/teleport`); `tools/compare_noise.py`;
`configs/sim_extra.json` and `schemas/bm.sim_extra-1.schema.json`; `ros2_ws/src/beaconmind_bringup/{launch/sim.launch.py,config/apriltag.yaml}`;
`ros2_ws/src/beaconmind_perception/**`; tests below.

**Tests.**
- `beaconmind/tests/test_tag_pnp.py` (6, `pytest.importorskip("cv2")`; runs in the container and on the
  Spark host where OpenCV exists): `test_synthetic_projection_recovers_position` (project a 0.16 m square
  at a known pose with a known K; error < 1 mm), `test_two_solutions_returned_and_one_matches_normal`,
  `test_normal_faces_camera`, `test_base_link_transform_with_extrinsics`, `test_corner_order_a_vs_b`
  (the wrong order gives a mirrored or failed pose), `test_reprojection_error_small_for_true_solution`.
- `beaconmind/tests/test_sim_noise.py` (4): `test_noise_sigma_matches_config` (5,000 seeded draws, ±10 %),
  `test_range_cap_drops`, `test_incidence_cap_drops`, `test_detection_probability` (±3 % at n = 5,000).
- Command (Spark host): `docker exec beaconmind-ros bash -lc 'cd /workspace/course-project/beaconmind && python3 -m pytest -q tests/test_tag_pnp.py tests/test_sim_noise.py'` → `10 passed`.
- Measurement: the calibration sweep (step 6) — every pose within 1.5 m and ≤ 45° incidence decodes the
  right ID in ≥ 18 of 20 frames; sim range error ≤ 0.02 m there.
- Smoke: step 9 — with `--no-noise`, the observation's `det_truth` uids equal `visible_uids(...)` for every
  tag within 1.5 m and ≤ 45° incidence (tags beyond that may be missing; none may be extra).

**Acceptance criteria.**
- [ ] `10 passed` in the container; `colcon test` still 0 failures.
- [ ] Corner order recorded; sweep CSV saved; comparison table saved; `configs/sim_extra.json` written
      with provenance; the after-injection table shows every bin within ±20 % of the real σ.
- [ ] Smoke observation saved and consistent with kinsim.

**Evidence to save** (`evidence/M2/M2.T6/`). `msg_fields.txt`, `pytest_container.txt`, `corner_order.txt`,
`sim_detection_errors.csv`, `noise_comparison.md`, `capture_once.json`.

**Pitfalls and known gotchas.** Never rely on `apriltag_ros`'s TF frames for duplicated IDs (one frame per
ID). The PnP ambiguity is real at small tags and oblique angles — keep both normals. `camera_info` in sim
has zero distortion; on the car it will not (M3.T9). Noise injection must use the episode's RNG key, so
replays and re-recordings are reproducible.

**Stop-and-ask conditions.** Step 2 (no `apriltag_ros`). Step 6 (no corner order works). Step 7 (sim worse
than real). M1.T8's bins cannot be reproduced from its evidence.

**Estimated effort.** M (two sessions: steps 1–5; steps 6–10).

**AI-disclosure note.** `AI-assisted: <model> via <tool>, <date>: wrote the PnP, sim noise injection, ROS capture and calibration sweep.`

---

### M2.T17 — ROS environment adapter (`envs/ros_env.py`) and the first full B2 episode in Isaac

**Why.** Closed loop through ROS is how the twin and, later, the car are driven (C12). This task finishes
`RosEnv` (`execute`, heartbeats, reset, ground truth) and proves the whole chain on one world: B2 explores in
Isaac, the run log and the observation log are written, and B2's ATE is computed. Appended to M2.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M2.T6, M2.T19 done | task | `grep -E -e "^. M2\.T6 " -e "^. M2\.T19 " course-project/plan/M2-sim-mvp.md` (Mac) | both with Status `done` |
| M2.T10 done | task | `grep -E "^. M2\.T10 " course-project/plan/M2-sim-mvp.md` (Mac) | Status `done` |

**Inputs.** README C2, C3, C8, C9, C12; `envs/ros_env.py` part 1; `envs/pico_wire.py`; `harness/run.py`.

**Steps.**
1. *Mac.* README §1.2 steps 1–5.
2. *Mac.* `RosEnv` part 2: `execute(command) -> dict` (encode with `pico_wire`, publish
   `/pico/move/cmd`, wait for the `/pico/move/result` with the same `cmd_seq`; no result within
   `timeout_s + 2 s` → `link_lost`; decode with `car`); a 10 Hz heartbeat timer on `/pico/heartbeat`;
   `reset()` (simulation only: `POST <twin_url>/reset`; on the car it is an operator step, M3);
   `gt_pose_world()` from `/ground_truth/pose`; `arm()` publishes `/pico/arm` 1 **only** when constructed
   with `operator_arm=True` (D6: only an operator command arms — the `--operator-arm` CLI flag is that
   command); `close()` destroys the node. Publish each corrected report on `/beaconmind/report` (the runner
   calls `env.publish_report(report)` when the env has it).
3. *Mac.* `harness/run.py`: `--env isaac` builds `RosEnv(source="sim", twin_url=…, operator_arm=args.operator_arm)`.
4. *Mac.* Tests (`beaconmind/tests/test_ros_env_logic.py`, pure helpers with a fake publisher/subscriber
   pair; no ROS runtime), run on the Mac.
5. *Spark.* Full episode: `bash sim/isaac/run_twin.sh data/worlds/sim-dup-s1000.json`; in the container
   start `sim.launch.py world:=… rng_key:=sim-dup-s1000-B2-i1`; then
   `python3 -m beaconmind.harness.run --arm B2 --mode closed_loop --env isaac --operator-arm --worlds data/worlds/sim-dup-s1000.json --missions EXPLORE --k 1 --budget-usd 0 --out data/runs --record-obslog data/obslogs`
   (placeholders not allowed: `car.json` and `detector_noise.json` must be measured). Then
   `python3 -m beaconmind.harness.summarize data/runs/<run_id>` and, on the Spark host venv,
   `python -m beaconmind.metrics.score --run data/runs/<run_id> --worlds data/worlds --out evidence/M2/M2.T17/score`.
   Stop the twin and the launch.
6. *Spark container.* For comparison, the same world in kinsim with the measured noise:
   `python3 -m beaconmind.harness.run --arm B2 --mode closed_loop --env kinsim --worlds data/worlds/sim-dup-s1000.json --missions EXPLORE --k 1 --budget-usd 0 --out data/runs --record-obslog data/obslogs`
   and score it. Put both rows side by side in `evidence/M2/M2.T17/isaac_vs_kinsim.md` (steps, tags
   mapped, ATE, ended_by) — descriptive only.
7. Evidence, status, `CONTEXT.md`.

**Deliverables.** `envs/ros_env.py` (part 2); `harness/run.py` (`--env isaac`, `--operator-arm`);
`tests/test_ros_env_logic.py`.

**Tests.**
- `tests/test_ros_env_logic.py` (5): `test_execute_matches_cmd_seq` (an out-of-order result for another
  `cmd_seq` is ignored), `test_execute_timeout_link_lost`, `test_no_arm_without_operator_flag`,
  `test_heartbeat_increments`, `test_reset_only_in_sim`. Command (Mac) → `5 passed`.
- Smoke/integration (step 5): the Isaac EXPLORE episode ends `DONE` or `budget`; the obslog validates
  against `bm.obslog-1`; the `.gt.tum` has one line per step; no `latch`; `executed_invalid` = 0; at least
  one detection on ≥ 80 % of the scan-turn steps.

**Acceptance criteria.**
- [ ] `5 passed`; integration conditions met; obslog `sim-dup-s1000-B2-i1` exists on the Spark.
- [ ] `isaac_vs_kinsim.md` saved.

**Evidence to save** (`evidence/M2/M2.T17/`). `pytest_mac.txt`, `episode_summary.txt`, `score/episodes.csv`,
`isaac_vs_kinsim.md`, `obslog_head.jsonl` (header + first two steps, after the L9 secrets grep).

**Pitfalls and known gotchas.** Exactly one `bm_sim_pico` must be running (two would both answer).
`cmd_seq` must increase across the whole episode. Keep `ROS_DOMAIN_ID=0` and never run host Jazzy nodes on
domain 0 at the same time (L5).

**Stop-and-ask conditions.** The episode latches or errors twice for a reason that is not a bug you can
see in the logs.

**Estimated effort.** S.

**AI-disclosure note.** `AI-assisted: <model> via <tool>, <date>: finished RosEnv and ran the first Isaac episode.`

---
### M2.T11 — Record simulated observation logs (C9.1): dev seeds and a first batch of test seeds

**Why.** Replay feeds every model and level the identical sequence of observations, which isolates
estimation from exploration (APPROACH §8 "Two modes"; D1d; C9.1). The logs are recorded once, by a
deterministic driver (B2, allowed by the cut line, README §3.4), with the measured noise models, in Isaac
(and in kinsim as the fallback and as a second, cheaper source).

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M2.T19 done (B2 drives) | task | `grep -E "^. M2\.T19 " course-project/plan/M2-sim-mvp.md` (Mac) | Status `done` |
| M2.T17 done (Isaac logs only) | task | `grep -E "^. M2\.T17 " course-project/plan/M2-sim-mvp.md` (Mac) | Status `done`, or the kinsim fallback approved in `CONTEXT.md` |
| Measured configs | config | `cd course-project/beaconmind && ../.venv/bin/python -c "from beaconmind.config import load_car, load_detector_noise; print(load_car()['status'], load_detector_noise()['status'])"` (Mac) | `measured measured` (if M1.T8/M1.T9 are not done, only placeholder kinsim logs can be recorded, with `--allow-placeholder`; they are test data and must be re-recorded later — APPROACH §6) |
| Isaac noise injection ready (Isaac logs only) | config | `ls course-project/configs/sim_extra.json` (Mac) | listed (M2.T6 step 7) |
| Worlds generated | data | `ssh … 'ls ~/Projects/EN.665.715/course-project/data/worlds \| wc -l'` (Mac) | ≥ 600 |

**Inputs.** README C7 (seeds), C8, C9.1, §3.4; AGENT-DESIGN D1d; `configs/seeds.json`.

**Steps.**
1. *Mac.* README §1.2 steps 1–5. Count the days to 2026-12-13 and apply the cut-line triggers.
2. *Mac.* `src/beaconmind/drivers/__init__.py`, `drivers/record.py`: CLI
   `python -m beaconmind.drivers.record --driver B2 --env kinsim|isaac --worlds <files…> --out data/obslogs [--operator-arm] [--allow-placeholder]`
   that calls the runner with `--arm B2 --mode closed_loop --missions EXPLORE --record-obslog`, names logs
   `<world_id>-B2-k1` (kinsim) or `<world_id>-B2-i1` (Isaac), sets the obslog header `notes` to `"mission
   EXPLORE; driver B2; recorded for replay"`, and then runs `drivers/qc.py` on each new log.
3. *Mac.* `drivers/qc.py`: `qc_log(path, world) -> dict` with `steps, ended_by, tags_seen_frac` (wall tags
   detected at least once / wall tags), `dup_pairs_seen` (duplicated-ID pairs whose **both** tags were
   detected at least once), `gt_steps` (steps with ground truth), `latched`; and a pass rule: `steps ≥ 20`,
   `tags_seen_frac ≥ 0.6`, `gt_steps == steps`, not latched; for `duplicated` worlds also `dup_pairs_seen ≥
   1` (otherwise the log tests no aliasing; it is kept but flagged). CLI writes/updates
   `data/obslogs/inventory.csv` and prints a summary.
4. *Mac.* `course-project/tools/record_isaac.sh <seed_list_file> <condition>` (Spark host): for each seed:
   `sim/isaac/run_twin.sh data/worlds/sim-<cond>-s<seed>.json` → `docker exec -d beaconmind-ros bash -lc
   'source … && ros2 launch beaconmind_bringup sim.launch.py world:=… rng_key:=sim-<cond>-s<seed>-B2-i1'`
   → `docker exec beaconmind-ros bash -lc 'cd /workspace/course-project && python3 -m beaconmind.drivers.record --driver B2 --env isaac --operator-arm --worlds data/worlds/sim-<cond>-s<seed>.json --out data/obslogs'`
   → stop the launch (`docker exec beaconmind-ros pkill -f "ros2 launch beaconmind_bringup"`) →
   `sim/isaac/stop_twin.sh`; on any failure it logs the seed to `data/obslogs/failed_seeds.txt` and
   continues. Header comment with the disclosure.
5. *Mac.* Tests (below); sync.
6. *Spark container.* Kinsim logs (fast; measured noise):
   dev seeds 1000–1019 and test seeds 2000–2029, both conditions:
   `python3 -m beaconmind.drivers.record --driver B2 --env kinsim --worlds $(ls data/worlds/sim-{uni,dup}-s10{00..19}.json data/worlds/sim-{uni,dup}-s20{00..29}.json) --out data/obslogs`.
   Expected: 100 logs; QC summary pasted.
7. *Spark host (tmux session `bm`).* Isaac logs, duplicated condition: dev 1000–1009 and test 2000–2009
   (`printf "%s\n" 100{0..9} > /tmp/dev.txt` etc.; `bash course-project/tools/record_isaac.sh /tmp/dev.txt
   duplicated`, then the test list). Expect roughly 10 minutes per world (startup plus about 100 steps);
   check the first world end to end before leaving the rest running. Record the wall time per world.
   If time allows (Xiaohui decides), add the `unique` condition for the same seeds.
8. *Spark host.* Re-run QC over all logs; re-record a failed Isaac seed once; a seed that fails twice is
   listed as failed (never replaced by a different seed silently — test-seed hygiene).
9. *Spark → Mac.* Copy `data/obslogs/inventory.csv` into `evidence/M2/M2.T11/inventory.csv` and pull.
   **Do not open the test logs for anything except QC** (C7: tuning uses dev seeds only).
10. Status, `CONTEXT.md` (counts per source and condition, failed seeds, the noise configs' SHA-12s).

**Deliverables.** `beaconmind/drivers/{__init__,record,qc}.py`; `tools/record_isaac.sh`;
`tests/test_drivers_qc.py`; logs on the Spark: `data/obslogs/*.jsonl` and `*.gt.tum`.

**Tests.**
- `tests/test_drivers_qc.py` (5): `test_qc_pass_rule`, `test_qc_flags_no_duplicate_pair_seen`,
  `test_qc_detects_missing_ground_truth`, `test_inventory_csv_columns`, `test_log_naming_kinsim_vs_isaac`.
  Command (Mac) → `5 passed`.
- Smoke: step 6 (100 kinsim logs) and the first Isaac world of step 7 (QC pass).
- Acceptance thresholds: ≥ 10 dev and ≥ 10 test Isaac logs pass QC (duplicated condition), or under the
  approved kinsim fallback ≥ 10 + 10 kinsim logs (with the fallback approval date).

**Acceptance criteria.**
- [ ] `5 passed`.
- [ ] Inventory saved; QC pass counts per source/condition/split meet the thresholds.
- [ ] Every log header carries the DV, car and camera SHA-12s (C9.1) and no placeholder flag.

**Evidence to save** (`evidence/M2/M2.T11/`). `pytest_mac.txt`, `inventory.csv`, `qc_summary.txt`,
`isaac_wall_times.csv`, `failed_seeds.txt` (may be empty).

**Pitfalls and known gotchas.** One twin at a time (`run_twin.sh` refuses a second). A stale
`bm_sim_pico` from a previous world would answer the next world's commands — the script must stop the
launch before starting the next twin. Log names must not collide between kinsim and Isaac (`k1` vs `i1`).
Do not record with placeholder configs for results.

**Stop-and-ask conditions.** More than 3 Isaac seeds fail twice (a twin reliability problem: consider the
fallback, README §3.4). Recording time per Isaac world > 30 minutes. QC pass rate < 50 % in either source.

**Estimated effort.** M (one session to set up and start; the Isaac recording runs unattended in `tmux`).

**AI-disclosure note.** `AI-assisted: <model> via <tool>, <date>: wrote the recording driver, QC and the Isaac recording script.`

---

### M2.T12 — First result: 2–3 models vs B0, B1 and B2 in replay with duplicated IDs, plus closed-loop simulated episodes

**Why.** This is the cut-line deliverable (README §3.4: "sim-only L2 + B1 with 2–3 models"): the first
answer to RQ1 (talk track: how close the LLM comes to GTSAM, whether it beats dead reckoning, with
duplicated IDs) and a first look at RQ2/RQ3 (closed loop, latency, cost). It is also the **pilot** whose
numbers M4.T1 uses to pre-register targets and episode counts (OD6), which is why it runs on **dev seeds**.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M2.T9, M2.T10, M2.T11, M2.T19, M2.T20 done | task | `grep -E -e "^. M2\.T9 " -e "^. M2\.T10 " -e "^. M2\.T11 " -e "^. M2\.T19 " -e "^. M2\.T20 " course-project/plan/M2-sim-mvp.md` (Mac) | five rows, each with Status `done` |
| M1.T4 done (closed-loop model setting, OD8) | task | `grep -E "^. M1\.T4 " course-project/plan/M1-foundations.md` (Mac) | Status `done` |
| M2.T18 done (frontier arm only) | task | `grep -E "^. M2\.T18 " course-project/plan/M2-sim-mvp.md` (Mac) | Status `done`; else the result has 2 local model settings and says so |
| vLLM serving | service | `ssh … 'curl -sf http://127.0.0.1:8000/v1/models \| grep -c Qwen3.5-35B-A3B'` (Mac) | `1` (start as in M2.T7 step 11) |

**Inputs.** README §3.4, C9, C10 (all), C11, OD5, OD6, OD8; talk track targets (C10.11); M1.T4 evidence
(latency per setting); M2.T7/M2.T18 smoke summaries (tokens and seconds per step); `evidence/M2/M2.T11/inventory.csv`.

**Steps.**
1. *Mac.* README §1.2 steps 1–5. Count days to the deadline; if the cut line is invoked or M4 cannot
   happen, see the stop-and-ask item about test seeds below.
2. *Mac.* **Plan the runs and ask Xiaohui (one message, with the defaults):**
   - **Replay set:** the QC-passing Isaac dev logs of the duplicated condition (target 10: seeds
     1000–1009); the kinsim dev logs (duplicated, 20) as a second table.
   - **Arms:** B0, B1 (online; batch as a secondary row), B2, and L2 with (1) `qwen35-a3b-instruct`, (2)
     `qwen35-a3b-think`, (3) one frontier model chosen by Xiaohui from the M1.T11-verified entries.
   - **Repeats:** K = 1 for every LLM arm in this pilot (K ≥ 3 is M4's rule, C10.10); K = 3 for the
     instruct arm on the Isaac set if the time estimate below allows.
   - **Time estimate** (write it down before running): replay = steps × median `decision_latency_s` from
     the M2.T7 smoke and M1.T4 evidence ÷ parallel episodes (4 for vLLM); closed loop = (150 + 60 + 60
     steps, the D4 budgets) × the closed-loop setting's median latency per world and arm (episodes run one
     at a time: one twin). Above 24 hours for one arm → propose fewer logs or worlds.
   - **Money:** frontier arm only on the first 3 Isaac dev logs, cap **$30** (part of the $100 pilot cap,
     AGENT-DESIGN "API budget"); show the estimate = steps × (cost per step from M2.T18's live test). No
     frontier run without an explicit yes (§1.4 item 2).
   - **Closed loop:** 3 dev worlds (1000–1002, duplicated) in Isaac (kinsim under the fallback), the full
     mission chain EXPLORE → GO_TO_BEACON → RETURN_TO_START, arms B2 and L2 with the M1.T4 closed-loop
     setting (OD8), K = 1.
   Record Xiaohui's answers in `evidence/M2/M2.T12/run_plan.md` before step 3.
3. *Spark host + container.* Baselines on the replay set (minutes). B0 and B2 in the container:
   `docker exec beaconmind-ros bash -lc 'cd /workspace/course-project && python3 -m beaconmind.baselines.run --arm B0 --obslogs <isaac dev logs> --out data/runs'`,
   the same with `--arm B2`; B1 on the Spark host venv (GTSAM lives only there, L5), from `~/Projects/EN.665.715/course-project`: `~/.venvs/beaconmind/bin/python -m beaconmind.baselines.run --arm B1 --obslogs <same> --out data/runs`.
   Repeat for the kinsim dev logs.
4. *Spark container (tmux `bm`).* L2 local arms:
   `python3 -m beaconmind.harness.run --arm L2 --model qwen35-a3b-instruct --mode replay --obslogs <isaac dev logs> --k 1 --budget-usd 0 --parallel 4 --out data/runs`,
   then `qwen35-a3b-think`, then the kinsim set. Check the first episode's summary before leaving it.
5. *Spark container.* Frontier arm (only after the yes): `--model <key> --obslogs <first 3 isaac dev logs>
   --budget-usd 30 --parallel 1`. Watch the ledger; the guard stops at the cap.
6. *Spark host + container.* Closed loop: for each of the 3 worlds, start the twin and the launch (as in
   M2.T17), run `--arm B2` and then `--arm L2 --model <closed-loop key>` with `--missions
   EXPLORE,GO_TO_BEACON,RETURN_TO_START --operator-arm`, resetting the twin between arms
   (`POST /reset`). Record the wall time.
7. *Spark host.* Score every run: `~/.venvs/beaconmind/bin/python -m beaconmind.metrics.score --run <each run dir> --worlds data/worlds --out data/results/m2t12`.
8. *Mac.* `src/beaconmind/results/__init__.py`, `results/first_result.py` (matplotlib, scipy: host venv):
   `python -m beaconmind.results.first_result --episodes data/results/m2t12/episodes.csv --out evidence/M2/M2.T12`
   writes:
   - `table_replay_isaac.md`, `table_replay_kinsim.md`: per arm — episodes, median and IQR of unaligned
     ATE (primary, OD5), median aligned ATE, median final position and heading error, map correct / phantoms,
     ID precision and recall, association precision and recall (pooled TP/FP/FN), violations per 100
     decisions by code, tool turns per decision, latency p50/p95, cost per episode;
   - `table_closed_loop.md`: per arm and mission — success, SPL, tags mapped at the end, steps, `ended_by`,
     latency p95 (the 60 s gate, C10.8);
   - `fig_ate_replay.png` and `.pdf`: unaligned ATE per arm, one point per log, box per arm, B0/B1/B2
     first; axis in metres; title states "pilot, dev seeds, K = 1";
   - `paired_tests.md`: per L2 arm, a paired Wilcoxon signed-rank test of unaligned ATE against B0 and
     against B1 over logs (`scipy.stats.wilcoxon`), labelled **exploratory, not pre-registered**;
   - `targets_check.md`: each C10.11 replay target against the pilot (beats B0? ≤ 2 × B1? median final ≤
     0.25 m and 15°? association precision ≥ 0.90?), descriptive only;
   - `provenance.md`: every run id with its `run.json` hashes (prompt, tool schema, DV, car, noise) and
     the config SHA-12s, and the list of placeholders (must be empty).
   - **`summary_long.csv`** (the machine-readable form of the tables, consumed by M5.T4/M5.T9 and M6.T5;
     added by the cross-plan consistency review, 2026-10-06): one row per (`arm`, `model_key`, `source`,
     `condition`, `mode`, `mission`, `metric`), with columns
     `arm,model_key,source,condition,mode,mission,metric,n,median,q1,q3,mean,pooled` in that order.
     `model_key` is empty for B0/B1/B2; `mission` is empty for replay rows; `metric` uses the
     `episodes.csv` column names of M2.T10/M2.T20 (`ate_unaligned_m`, `ate_aligned_m`, `final_pos_err_m`,
     … — exactly the spellings `episodes.csv` uses); pooled metrics (association precision/recall,
     success rate) put their value in `pooled` and leave `median,q1,q3,mean` empty. Spellings of `arm`,
     `condition`, `source` and `mode` are copied from `episodes.csv` unchanged.
   - `episodes.csv`: a copy of `data/results/m2t12/episodes.csv` (if it is ≥ 1 MB, keep it on the Spark and
     write its Spark path and SHA-256 into `provenance.md` instead, L8).
   Never type a number into these files by hand (M5.T4 rule).
9. *Mac.* `results.md` (narrative, ≤ 1 page): what was run, the headline numbers **copied from the
   generated tables**, the limitations (pilot, dev seeds, K = 1, Isaac noise injected from M1.T8, B1
   upper bound with oracle association and the generating noise model), and the AI-disclosure paragraph.
10. *Mac.* Unit tests for `first_result.py` (below).
11. Evidence, status, `CONTEXT.md`; show Xiaohui `results.md` and ask whether any target should be
    revised before M4.T1 (OD6).

**Deliverables.** `beaconmind/results/{__init__,first_result}.py`; `tests/test_first_result.py`; the
evidence files of step 8–9; run directories on the Spark.

**Tests.**
- `tests/test_first_result.py` (6, synthetic `episodes.csv`): `test_tables_have_one_row_per_arm`,
  `test_median_iqr_hand_computed`, `test_pooled_association_precision`, `test_figure_files_written`,
  `test_provenance_lists_every_run`, `test_summary_long_columns_and_rows` (the header equals the column list
  of step 8 exactly; one row per arm × metric for the synthetic file; B0 rows have an empty `model_key`; the
  median of `ate_unaligned_m` for one arm equals the hand-computed value). Command (Mac; matplotlib/scipy
  needed → run in the Spark host venv if the Mac venv lacks them) → `6 passed`.
- Smoke: the first L2 replay episode completes with ≤ 10 % format violations before the batch is left
  running.
- Acceptance thresholds (process, not outcome): every planned run completed or its stop reason recorded;
  `executed_invalid` = 0 in every row; frontier spend ≤ the approved cap (ledger).

**Acceptance criteria.**
- [ ] `run_plan.md` with Xiaohui's answers exists before any run.
- [ ] Replay tables for ≥ 2 L2 model settings + B0 + B1 + B2 on ≥ 10 duplicated-ID logs (Isaac, or kinsim
      under the approved fallback).
- [ ] Closed-loop table for 3 worlds × 3 missions × (B2, L2).
- [ ] Figure, paired tests, target check, `summary_long.csv` and provenance generated by code; `results.md`
      written with the disclosure.
- [ ] No placeholder config in any reported run (`provenance.md`).

**Evidence to save** (`evidence/M2/M2.T12/`). `run_plan.md`, the files of step 8, `results.md`,
`pytest.txt`, `ledger_excerpt.jsonl` (frontier), `wall_times.csv`.

**Pitfalls and known gotchas.** Replay ATE and closed-loop ATE are not comparable (APPROACH §8: a model that
explores badly sees fewer tags). With K = 1, LLM nondeterminism is not averaged — say so. B1 sees the true
noise model and oracle association: it is an upper bound, not a peer. A run with `ended_by "error"` still
counts (its steps are scored up to the error); do not drop it silently.

**Stop-and-ask conditions.** Step 2 (plan, time, money). Any frontier spend. **Test seeds:** never run a
model on test-seed logs here, unless Xiaohui has invoked the cut line and M4 will not run — then first
freeze a short pre-registration (M4.T1, reduced) and only then repeat steps 3–8 on the test logs (2000–2009).
A format-violation rate > 30 % for a model in the first 3 episodes (likely a provider or parser problem,
not a result).

**Estimated effort.** M (one session to plan and start; unattended runs; one session to analyse and write).

**AI-disclosure note.** `results.md` ends with a "Generative-AI disclosure" paragraph naming the model that
wrote the analysis code and the narrative (L11); `first_result.py` carries the code line.

---
## Milestone-level integration and smoke test

Run this after M2.T12's inputs exist and again before marking M2 `done`; it proves that the pieces still fit
after the last change. Write it as `course-project/tools/m2_integration.sh` (Spark host; header comment with
the disclosure); it prints `PASS <check>` or `FAIL <check>` per line and exits non-zero on any FAIL.

| # | Check | Command inside the script (machine) | Pass condition |
| --- | --- | --- | --- |
| 1 | Unit tests, 3.12 | `~/.venvs/beaconmind/bin/python -m pytest -q` in `course-project/beaconmind` (Spark host) | last line has `passed`, no `failed`/`error` |
| 2 | Unit tests, 3.10 | `docker exec beaconmind-ros bash -lc 'cd /workspace/course-project/beaconmind && python3 -m pytest -q'` | same |
| 3 | GTSAM tests | `~/.venvs/beaconmind/bin/python -m pytest -q -m gtsam` (Spark host) | `10 passed` |
| 4 | ROS packages | `docker exec beaconmind-ros bash -lc 'source /opt/ros/humble/setup.bash && cd /workspace/course-project/ros2_ws && colcon build --symlink-install && colcon test && colcon test-result --verbose'` | `0 errors, 0 failures` |
| 5 | Worlds | `python -m beaconmind.worlds generate --condition duplicated --seeds 1999-1999 --out <tmp>` then `check` | `OK sim-dup-s1999` (seed 1999 is outside both splits) |
| 6 | Kinsim chain | B2 closed loop with `--record-obslog` on `sim-dup-s1999` (10 steps, `--max-steps 10`), then B0, B2 and B1 replay on that log, then `metrics.score` (pass `--allow-placeholder` only if M1.T8/M1.T9 are not done, and print `NOTE placeholders` when it does) | 4 rows in `episodes.csv`, `executed_invalid` = 0, all `ate_unaligned_m` filled |
| 7 | LLM replay | `harness.run --arm L2 --model qwen35-a3b-instruct --mode replay --obslogs <that log> --max-steps 3` (vLLM up) | 3 steps, decisions `NONE`, any `move` refused |
| 8 | Isaac chain | `run_twin.sh data/worlds/sim-dup-s1000.json`, launch, `move_probe --arm --actions FORWARD_10,TURN_LEFT_30`, `ros_env --capture-once`, `stop_twin.sh` | 2 results `done`; one observation with ≥ 1 detection; `kit clear` |
| 9 | Secrets | `grep -rnE "sk-\|api_key\"\s*:\s*\"[A-Za-z0-9]\|password\|ssid" course-project/evidence/M2` | prints nothing |

Save the full output as `evidence/M2/m2_integration.txt` (in the milestone evidence root, not a task folder).

## Milestone exit checklist

- [ ] Every row of the status table is `done` (or `dropped (cut line)` with Xiaohui's approval recorded).
- [ ] `evidence/M2/m2_integration.txt`: all 9 checks `PASS` (or check 8 replaced by the approved kinsim
      fallback, with the approval quoted in `CONTEXT.md`).
- [ ] Decisions taken in M2 are recorded in `CONTEXT.md` with dates: the M1.T11 waiver for M2.T7–T10 (or
      "not needed: M1.T11 done first"), `sweep_margin_m` (M2.T13), `n_dup` (M2.T2), map radius (M2.T10), B1
      online vs batch (M2.T9), corner order (M2.T6), the evo flag form (M2.T10), the run plan (M2.T12), and
      the car/noise views' `assumptions` lists (M2.T3).
- [ ] README §9.1 facts this milestone settled are listed in `CONTEXT.md` (evo `--project_to_plane`; the
      GTSAM wheel; `apriltag_ros` message fields as used) — the README itself is not edited by M2.
- [ ] No reported number comes from a placeholder config (`evidence/M2/M2.T12/provenance.md`).
- [ ] Test-seed hygiene: no model was run on test-seed logs unless the reduced pre-registration was frozen
      first (M2.T12 stop-and-ask).
- [ ] Every new file carries its L11 disclosure; copied repository code carries `Derived from:`.
- [ ] Files created on the Spark were pulled back to the Mac (L6); `git status` lists them; nothing
      committed unless Xiaohui asked (L10).
- [ ] Shared services left in a known state and recorded: `vllm-rosa` (running or stopped), no kit
      process, `beaconmind-ros` state, no stray `bm_sim_pico`.

## `CONTEXT.md` update on completion

Add a dated section at the top of `course-project/CONTEXT.md` (and keep its hardware state unchanged —
M2 touches no hardware):

```markdown
## <YYYY-MM-DD> — M2 done: minimum viable simulated result (cut line reached)

- Twin: Isaac <version> headless; tags rendered as <texture|MDL>; car from car.json <sha12>; camera from
  camera.json <sha12>; detector noise injected from M1.T8 (`configs/sim_extra.json`, <date>). [Or: kinsim fallback,
  approved by Xiaohui on <date>.]
- Logs: <n> Isaac + <n> kinsim observation logs (dev/test, conditions) — data/obslogs/inventory.csv.
- First result (pilot, dev seeds, K = 1): evidence/M2/M2.T12/results.md. Headline (copied from the tables):
  <one line per arm: median unaligned ATE; association precision>.
- Decisions: sweep_margin_m <v>; n_dup <v>; map radius <v>; B1 <online|batch>; corner order <A|B>;
  evo <flag form>.
- Settled README §9.1 items: <list>.
- Left running: <vllm-rosa state>; beaconmind-ros <state>; no kit process.
- Next: M4.T1 pre-registration (targets revisited with the pilot, OD6); M3.T12 real logs; M5.T4.
```

## Risks specific to M2, with mitigations

| # | Risk | Effect | Mitigation in this plan |
| --- | --- | --- | --- |
| R1 | Isaac twin does not come together on aarch64 (importer headless, OmniGraph names, DDS) — APPROACH §11 item 4 | Critical path slips | API names verified first (M2.T16 step 2); importer fallback to authoring the USD with `pxr`; HTTP move server (proven Module 2 pattern) instead of ROS-driven motion; kinsim fallback (README §3.4 (a)) decided by Xiaohui; the kinematic track does not wait for Isaac |
| R2 | Rendered tags do not decode (texture filtering, lighting, mirrored UVs) | No sim perception | Textured-quad method proven in Module 2; corner-order unit test; render-and-decode spike before the car work (M2.T15) |
| R3 | `apriltag_ros` TF frames collide for duplicated IDs | Wrong positions for aliased tags | Pose from corners with IPPE PnP per detection, never from TF (M2.T6) |
| R4 | Sim detections are cleaner than the real camera | Optimistic sim results | Calibration sweep and `sim_extra` noise injection from M1.T8 (M2.T6); stop if the sim is worse than real |
| R5 | Qwen3.5 thinking is slow (pilot: 91 s best, 18 min median with queueing — talk track) | Replay batches take days | Instruct setting first; `--parallel 4` (vLLM `MAX_SEQS` 4); time estimate before every batch (M2.T12 step 2); fewer logs rather than truncated episodes |
| R6 | Frontier API shapes or prices changed | Broken runs, unexpected cost | Field names only from M1.T11 evidence; recorded fixtures; shared ledger and per-run caps; explicit approvals |
| R7 | GTSAM wheel missing for cp312 aarch64 | No B1 | Probe first (M2.T9 step 2) with ranked fallbacks |
| R8 | Placeholder configs leak into results | Invalid numbers | `"status": "placeholder"` everywhere; the CLI refuses without `--allow-placeholder`; provenance check (M2.T12) |
| R9 | Test seeds touched before pre-registration | Biased benchmark | Pilot on dev seeds; QC-only access to test logs; reduced pre-registration required before any test-seed model run |
| R10 | B2 diverges from D7 | Wrong baseline and wrong driver behaviour | Parity tests against `backstory_sim.py` on two simulated histories (M2.T8, M2.T19) |
| R11 | Loop closures and aliasing events are rare at the current DVs (AGENT-DESIGN D8: 1 step with a loop closure in 300 runs) | Association metrics rest on few events | QC counts duplicated pairs seen per log; association reported with its event counts; loop closures pooled (C10.4) |
| R12 | vLLM (0.60 GPU share) and Isaac together exhaust memory | OOM kills a long run | Check `free -g` before starting the twin; one kit at a time; L5 memory note |
| R13 | Work created on the Spark is overwritten by the next Mac → Spark sync | Lost evidence or fixtures | Pull back in the same session (L6); called out in M2.T7 step 16 and every Spark task's evidence step |
| R14 | K = 1 pilot hides LLM run-to-run variance | Over-reading the pilot | Labelled "pilot, K = 1, exploratory" in every table; K ≥ 3 in M4 |

## Generative-AI disclosure

Claude Opus 5.5 via Claude Code (adversarial review pass, 2026-10-06) revised this file: corrected the
smoke-record counts (the per-scenario files duplicate `v7-think.jsonl`: 117 calls, not 234) and the
truncated prompt MD5; added the M2.T3 adapter from M1's `bm.car/1`, `bm.camera/1` and
`bm.detector_noise/1` files to the flat views M2 uses; moved the Isaac noise injection to its own
`configs/sim_extra.json`; reconciled `harness/budget.py` with M1.T11's API; turned the M1.T11 dependency
narrowing into a waiver Xiaohui must approve (README §3.3 wins otherwise); flagged the D5 `status`-key
conflict; replaced the frontier pytest with an approved smoke script (README L4) and corrected its cost
estimate; made replay episodes run to the log end; vendored the reference simulator for Spark-side tests
(the Spark has no `assignments/` checkout, checked read-only on 2026-10-06); fixed the impossible bump
test, the `pgrep -f` self-match, the move-probe order, missing `mkdir`/pull-back steps, and added the
unverified camera-over-UDP branch. It ran only read-only checks (file hashes and record counts on the
Mac; `ls`, `grep` and `docker ps -a` on the Spark).

Claude Opus 5.5 via Claude Code wrote this milestone plan on 2026-10-05: the task breakdown (including the
appended tasks M2.T13–M2.T20), the module and file layout, the function signatures, the test lists and
thresholds, the step-by-step commands, the risks, and every value marked "proposed default" or "stand-in".
It ran read-only checks on 2026-10-05 (Isaac build contents and API names, Python packages and OpenCV's
AprilTag generator on the Spark host, Docker images and containers, the v3.3 prompt's hashes on the Mac);
nothing was installed, started or changed. Every unverified fact is written as a verification step. The
design it implements is `AGENT-DESIGN.md` v3.3 and `plan/README.md`. Xiaohui Chen owns the project, makes
every decision marked stop-and-ask, and may change any part of this plan.

Cross-plan consistency review, 2026-10-06, by Claude Opus 5.5 via Claude Code: cross-milestone task IDs, shared files and contracts aligned with the other five milestone files and `plan/README.md` (details and the list of edits in `plan/REVIEW.md`). Read-only checks on the Mac only; nothing was run on the Spark.

Follow-up edit, 2026-10-24, by Claude Opus 5.5 via Claude Code: M2.T3 step 2 marks the roll-out keys and the roll-out fallback for `wheel_diameter_m` as superseded (M1.T9 writes the direct diameter; README S13). File reads on the Mac only.

Status pass, 2026-10-29, by Grok 4.7 via Cursor: M2.T4 stays blocked and also waits on M1.T16. Nothing was regenerated. Xiaohui Chen remains accountable for what he submits.
