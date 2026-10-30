# M2.T4, 2026-10-29: the URDF updated to the M1.T16 car (660 g, power bank)

M2.T4 stays **blocked** on `configs/camera.json` (M1.T7) and the `load_car` view (M2.T3). This pass did the part
M1.T16 unblocked: the mass, the centre of mass and the power-bank box, from Xiaohui Chen's 2026-10-29 readings
(`evidence/M1/M1.T16/measurements.md`, section "Decisions for M2.T4"). Branch `urdf/m1t16-measured-mass`, based on
`main` at `abde7a7`.

## What changed in the model

| | Before (`abde7a7`) | After |
| --- | --- | --- |
| Total mass (`car.json` `mass_kg`) | 0.506 kg (`K1_total_mass`, 2026-10-10) | **0.660 kg** (`K1_total_mass_remeasure`, 2026-10-29) |
| Two-scale split (extras `caster_load` / `drive_wheels_load`) | 142 / 364 g, caster turned sideways | **58 / 602 g**, caster not turned sideways |
| Whole-car centre of mass x | 33.676 mm | **10.545 mm** (middle value, ±1.8 mm with the assumed 20 mm trail; 8.8–11.2 mm from the readings alone) |
| `chassis_link` mass | 0.421 kg | **0.575 kg** (stand-in part masses unchanged) |
| `chassis_link` inertial origin | (35.974, −0.238, 14.5) mm | (8.809, −0.174, 14.5) mm |
| Power bank | not modelled | box `power_bank` on `chassis_link`, x −85 to −15 mm, y ±35 mm, 17–42 mm above the floor; geometry only, no link, no mass of its own |
| Gearbox boxes (`motor_x_min`, photo ESTIMATE ±6 mm) | rear end −16 mm | **−15 mm**, clipped to the measured bank front face (agent decision, below) |
| `front_overhang_m` | 0.138 ± 0.003 m (ESP32-CAM, no cable) | **0.178 ± 0.0058 m** (the camera cable's tip, `B3_front_most_x_remeasure`) |
| `rear_overhang_m` | 0.07649 ± 0.003 m (plate rear apex) | **0.148 ± 0.003 m** (the Pico cable, `B4_rear_most_x_remeasure`) |
| `chassis_length_m` / `sweep_radius_m` | 0.21449 / 0.140 m | **0.326 ± 0.0066 / 0.178281 ± 0.0058 m** (front-most corners (0.178, ±0.010): the cable taken as wide as the board and centred) |
| Cables in the URDF | none | `front_camera_cable` (x 0.138–0.178, visual + collision), `rear_pico_cable` (x −0.148 to −0.085, visual only); ends measured, cross-sections ASSUMED |

Unchanged on purpose: ride height (30 / 46 / 43 mm), camera and IMU poses, wheels, track, caster position and
`chassis_height_m`. The ESP32-CAM board box still ends at 138 mm (new row `B14b_esp32cam_front_x`).

**The footprint (added after 23:45 CDT).** Xiaohui measured the camera cable 40 mm past the old 138 mm front-most
point and chose to keep both cables as they are and have the footprint follow them, and to add the cables to the URDF
(`evidence/M1/M1.T16/measurements.md`). `front_overhang_m` carries ±5.8 mm (138 ± 3 mm plus "4cm" read to the
nearest cm, ± 5 mm, root-sum-square) through a writer exception keyed to that one row. Agent decisions for Xiaohui to
accept: the front cable envelope has a collider, so the simulated car's first front wall contact matches
`front_overhang_m`; the rear loop is visual only (a rigid box hanging toward the floor would be a false floor contact),
so the simulated first rear wall contact is the bank's rear face, 63 mm short of the footprint and of the planned
kinsim body. Design-value consequences (proposals only, `dv.json` unchanged): `evidence/M1/M1.T9/derived-dv-proposals.md`.

The data chain was followed: a new CSV `evidence/M1/M1.T9/measurements-2026-10-29-with-m1t16-mass.csv` (the
2026-10-16 file unchanged plus `K1`/`K2` `_remeasure` rows, `B15_bank_*` rows and two cable rows that are not model
inputs) → `tools/write_car_json.py` → `configs/car.json` (only `mass_kg` changed in value) → `gen_props.py` →
`car_props.xacro`; the extras and the main xacro were edited by hand. Details: `evidence/M1/M1.T9/README.md`
(2026-10-29 section).

New checks: xacro guards that the two-scale split and the total are one weighing (within 2.5 g), that the bank box
sits above the floor, below the measured rear plate underside and outside the gearbox boxes, and that no `body_box`
has zero or negative size; tests `test_power_bank_box_matches_measurements` and
`test_inertias_are_physical_and_chassis_is_the_uniform_box`, and a split-sum check in `test_com_matches_lever_rule`.
The test file now reads the extras' source CSV from this public repo; before, it pointed at a private-repo path and
errored here.

## Runs (real output in this folder)

| File | Where | Result |
| --- | --- | --- |
| `baseline-abde7a7/colcon_test.txt` | `beaconmind-ros:humble`, unmodified `main` | **21 tests, 1 error, 1 failure, 1 skipped**: two breakages from the public-repo move (`car_props.xacro` named the pre-scrub `car.json` hash; the extras CSV path pointed into the private repo) |
| `pkg_check.txt` | same image, this branch | `xacro`, `robot_state_publisher`, `tf2_ros` found; ros-humble-xacro 2.1.1 |
| `colcon_test.txt` | same | `colcon build --symlink-install` OK; **24 tests, 0 errors, 0 failures, 1 skipped** (`test_optical_frame_matches_camera_json`: no `camera.json`) |
| `expand_check.txt` | same | xacro wrote `sim/isaac/assets/beaconmind_car.urdf` (sha256 `f1116ee5…`); `check_urdf` parses it, 8 links |
| `tf2_echo.txt` | same | `robot_state_publisher` up; `base_link → camera_optical_frame` (0.120, 0, 0.0415) m, RPY (−90, 0, −90)°; IMU, caster, chassis as before; published masses 0.575 + 2 × 0.03 + 0.01 + 0.01 + 0.005 = 0.660 kg |
| `gz_sdf.txt` | Spark host, `gz sdf` 14.9.0 (Jazzy vendor) | converts with empty stderr; lumped body 0.600 kg + two 0.03 kg wheels = 0.660 kg; lumped centre of mass x 0.0116 m = 0.660 × 0.010545 / 0.600; two cable visuals, one cable collision (the front) |
| `urdf_named_diff.txt` | Mac | only the two motor boxes, the new `power_bank` box and front cable box (visual + collision), the rear cable visual and the `chassis_link` inertial differ from `main`'s expansion |
| `mac_pytest.txt` | Mac, pip xacro 2.1.1 | 23 passed, 1 skipped; `gen_props.py --check` up to date; `beaconmind` 65 passed, 1 skipped |

Container runs used a throwaway `docker run --rm --network none` from the `beaconmind-ros:humble` image on a scratch
copy of the branch (`ROS_DOMAIN_ID=73`, `ROS_LOCALHOST_ONLY=1`), not the standing `beaconmind-ros` container or the
Spark's repo mirror.

## Adversarial review (one round, four lenses)

Four independent reviewers, each checking claims against the primary sources (measurements.md, the CSVs, the
expanded URDF, the Isaac Sim 5.1 importer source and the sdformat spec on the Spark), each with mutation tests on
scratch copies. No critical finding. Every number and decision was confirmed. Each finding below was verified by the
coordinator before it was fixed.

| # | Lens | Severity | Finding | Disposition |
| --- | --- | --- | --- | --- |
| 1 | data chain, math | major | `test_com_matches_lever_rule` now reads the same CSV as `car.json`, so a later total weighed without a new split passed all tests (reproduced: 700 g vs 58 + 602 g) | confirmed; fixed: xacro guard and test check that split and total agree within 2.5 g (the 700 g case now stops xacro) |
| 2 | ROS, data chain | major | the new CSV was untracked; every test needs it | confirmed; committed with the change |
| 3 | source, data chain | major | handoff docs (`AGENTS.md`, `CONTEXT.md`, plan, this README) still described the 0.506 kg car; no saved run evidence | confirmed; updated, and this folder holds the runs |
| 4 | ROS, math | major / minor | the new COM and the bank collider change sim behaviour: caster lifts at about 2.2 m/s² forward acceleration (7.15 m/s² before); the bank's rear-bottom edge is the first rear contact at about 11.8° nose-up; rear clearance 17 mm; the bank has no physics material in the M2.T16 list | confirmed (recomputed from the expansion); recorded as M2.T16 notes in the xacro comments; no value change |
| 5 | math | minor | with the caster sphere at the trailing contact (0.100 m) and the middle COM, the model's static caster load is 69.6 g against the 58 g weighed | confirmed; recorded as the expected M2.T16 settle value; Xiaohui's middle-value decision kept |
| 6 | math | minor | the ±1.8 mm assumes the 20 mm trail; the swung-forward reading limits the forward contact to 127.5 mm (COM 8.8–11.2 mm) | confirmed; comments and CSV notes say so; value unchanged |
| 7 | math, ROS | minor | bank guards could misfire on touching faces (float sums), lacked a height term, compared with the level plate (44.5 mm) instead of the measured rear underside (43 mm); no check for degenerate or below-floor boxes | confirmed; fixed (`bank_top_h` rounded, complete interval test, rear underside, `body_box` size guard, floor guard) |
| 8 | math | minor | no test pinned the inertia (a swapped call passed) | confirmed; new inertia test |
| 9 | source, math, ROS | minor | inertia comment said the bank is outside the inertia box (it is mostly inside; only its lower 13 mm is below) | confirmed; reworded |
| 10 | source, data chain | minor | "directly behind the gearboxes" is not measured; the 1 mm `motor_x_min` move is an agent decision | confirmed; reworded as an estimate clipped to the measured bank face, listed for Xiaohui to accept |
| 11 | ROS | minor | the Isaac note asked for an import log with no warnings about the massless links; importer 2.4.30 always warns for them (`UrdfImporter.cpp:393`, `:608`) | confirmed in the source; reworded |
| 12 | ROS | minor | self-collision claim uncited; M2.T16 relies on a default | confirmed (`IUrdf.h:71` `selfCollision = false`; sdformat 1.11 `self_collide` default false); cited, and M2.T16 told to set it off explicitly |
| 13 | source, data chain | minor | generator comments hard-coded readings and dates the props test cannot keep honest; `evidence_csv()` fallback text | confirmed; generic texts, explicit fallback |
| 14 | source | minor | new CSV lacked an AI line; inherited "Battery OFF" header; the configuration list comes from the M1.T16 prerequisite, not the reading record | confirmed; header and notes fixed |
| 15 | source | minor | private-repo paths unlabelled in an edited comment and the M1.T9 README | confirmed; labelled |
| 16 | various | nit | K1 reason text, test docstring "exact", wheel-joint history, `package.xml` description, README scope line, interpreter line in `derived.txt` | confirmed; fixed |
| — | math | nit | sub-micrometre face snapping | rejected: readings are whole millimetres |
| — | source, data chain | nit | `measured.date` stays 2026-10-10 | kept: the schema has one date (the first measurement); the notes record 2026-10-29 |

**Second round (cables and footprint, after 23:45 CDT).** Two reviewers (source fidelity / data chain / scope; and
geometry / simulator / tests), with mutation tests. No critical finding; the chain reproduced byte for byte.

| # | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| 17 | major | with both cables visual only, Isaac and Gazebo would first touch a wall 40 mm (front) and 63 mm (rear) short of the `car.json` footprint and the planned kinsim body | confirmed; front cable given a collider (agent decision); rear offset documented in the xacro and the M2.T16 notes |
| 18 | major | handoff docs still forbade the footprint change | confirmed; `AGENTS.md`, `CONTEXT.md`, plan, both READMEs updated |
| 19 | minor | ±5 mm on 178 mm dropped the 138 mm reading's ±3 mm, and the word "around" was the agent's | confirmed; ±5.8 mm through a writer exception keyed to the exact row, with a test; "around" removed |
| 20 | minor | the sweep radius rests on two assumptions (cable width and centring), the rear point on y = 0 | confirmed; stated in `car.json`, the writer, the README and the xacro |
| 21 | minor | the board front shared the B3 row name with the cable tip; board and cable widths were not tied to B14 (mutations passed) | confirmed; new row `B14b_esp32cam_front_x`, width checks in the test |
| 22 | minor | the 7 mm lowest cable point may be under the car (the camera cable seems to run forward under the bank); the Pico plug above the breadboard is outside the rear envelope | confirmed from the photos (no front photo); envelope wording says so |
| 23 | minor | the front cable visual will show at the bottom of a simulated camera image | recorded as an M2.T16 check (estimate, not rendered) |
| 24 | nit | guard messages, the X1 note, docstrings, the template's AI line, stale "at the time" wording | fixed |

Open, outside this change (for Xiaohui; also in `CONTEXT.md`):

- Accept or reject the 1 mm gearbox-box change (`motor_x_min` −16 → −15 mm), the front-cable collider and the
  visual-only rear cable.
- The cables' sideways position and width (they set the sweep radius through an assumption), and a front photo of the
  camera cable's route.
- `configs/dv.json` (`done_range_m` placeholder 0.55 vs the proposal 0.628 m; OD17's margin).
- `plan/M2-sim-mvp.md` (M2.T16) says `merge_fixed_joints = True` "would delete the camera frames"; in importer 2.4.30 a massless fixed child becomes an Xform under its parent instead (`UrdfImporter.cpp` 295–310, per the ROS reviewer; not re-run here).
- The Spark's private-repo mirror predates the Module 6 snapshot commit; `git pull` it before the lab is next used.

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: the URDF/xacro, generator, writer-text, test and CSV edits
(Claude Opus 5.5 at xhigh effort, as the plan requires for this URDF), the container and Gazebo runs, the four-lens
review and this record. The measurements are Xiaohui Chen's. Xiaohui Chen is accountable for the project.
