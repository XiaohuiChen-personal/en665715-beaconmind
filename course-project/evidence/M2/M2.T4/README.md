# M2.T4 evidence: the car URDF generated from `configs/car.json` (2026-10-10)

M2.T4 is **blocked**, not done (plan README §1.2 step 4: its prerequisites M1.T7, M1.T9 and M2.T3 are not done;
§1.4 item 8: the camera.json conventions below are a plan conflict for Xiaohui). The package, the generator and the
tests were built ahead and run, and the TF smoke test passes against the measured lens position; the acceptance
items that need `configs/camera.json` (M1.T7) cannot pass yet. Everything ran on spark-2a60 inside `beaconmind-ros`
(ROS 2 Humble; the repository is bind-mounted at `/workspace`, checked with `docker inspect`, see `pkg_check.txt`),
with `ROS_DOMAIN_ID=47` and `ROS_LOCALHOST_ONLY=1` for every ROS process. The launch was stopped at the end, but
the ROS 2 CLI daemon that step 9's `ros2` calls had started (domain 47) was missed by the end check and stayed up
until a review found it; it was stopped at ~07:52 CDT (`daemon_stop.txt`).

## 2026-10-29: the M1.T16 car (the URDF DID change)

Full record, run logs and the four-lens review: [`2026-10-29-m1t16/`](2026-10-29-m1t16/README.md). Total mass
0.506 → **0.660 kg**, two-scale split 58 / 602 g, whole-car centre of mass 33.676 → **10.545 mm** (middle value,
±1.8 mm), chassis mass 0.421 → **0.575 kg**, a geometry-only `power_bank` box on `chassis_link`, the gearbox boxes'
estimated rear end −16 → −15 mm; after 23:45 CDT, by Xiaohui's decision to keep the cables, `front_overhang_m`
0.178 m, `rear_overhang_m` 0.148 m, `sweep_radius_m` 0.178 m, and two cable boxes (front with a collider, rear visual
only). `colcon test` in `beaconmind-ros:humble`: **24 tests, 0 errors, 0 failures, 1 skipped** (unmodified `main`
gave 21 tests, 1 error, 1 failure, 1 skipped after the public-repo move). Since 2026-10-29 the Module 6 lab mounts a frozen snapshot in the private course
repo, so sections below that tie the URDF to the lab are history. Where the sections below quote 0.506 kg, 0.421 kg,
33.676 mm or 12 boxes, they describe the 2026-10-10 / 2026-10-16 model.

## 2026-10-16: the plate outline from a classmate's CAD (the URDF DID change)

The plate rows of `car_geometry_extras.xacro` now come from a classmate's CAD of the Emo chassis plate
(`the private course repo (plate CAD is not published here)`; `car.json` side: `evidence/M1/M1.T9/README.md`, 2026-10-16 section).
`beaconmind_car.urdf.xacro` gained the rounded front (an R135.14 arc with R8 corner fillets, drawn as 3
`plate_front_slice` boxes after the full-width strip, which now ends where the fillets start at x = 115.35 mm) and puts
plate-slice boundaries on a 2 µm grid (`snap2um`): with the CAD's 34.35 mm wing the 8.5875 mm slices otherwise overlap
by 1 µm after `body_box`'s 1 µm rounding, which `test_chassis_boxes_do_not_overlap` caught on the first run. A new test,
`test_plate_outline_matches_measurements`, checks the plate boxes against the plate rows of the CSV `car.json` names.

Expanded URDF (`sim/isaac/assets/beaconmind_car.urdf`, sha256 `d0b2ffbf…`; before `81a7d617…`), compared by element
name (`evidence/M1/M1.T9/plate-cad-2026-10-16/urdf-named-diff.txt`): 34 of the 45 named elements are identical; the
changes are the plate boxes only (strip 168 → 157.492 mm long, the 4 wing slices re-shaped for the 34.35 × 73.96 mm
half-ellipse, 3 new front slices 99.2 / 89.2 / 52.0 mm wide) and the chassis inertia's iyy/izz (box length 208 →
206.98 mm). Joints, wheels, caster, camera, IMU, masses and the chassis centre of mass are unchanged.
`colcon test` (`beaconmind-ros`, domain 141, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`): **21 tests, 0 errors, 0 failures,
1 skipped** (`test_optical_frame_matches_camera_json`, no `camera.json`). The Module 6 lab wrapper includes this URDF,
so a re-run of that lab would draw the new plate; its submitted screenshots show the 2026-10-10 model.

## Files

| File | Step | Result |
| --- | --- | --- |
| `pkg_check.txt` | 2 | `ros2 pkg prefix` finds `xacro`, `robot_state_publisher`, `tf2_ros` (all `/opt/ros/humble`); package versions; the `/workspace` mount |
| `colcon_test.txt` | 8 | build OK. `colcon test` as the plan writes it: **1 test, 1 error** (pytest 9.1.1 rejects Humble's `launch_testing` plugin: `PluginValidationError … {'path'} … not … in the hookspec`). With `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`: **18 passed, 1 skipped**; `colcon test-result`: `19 tests, 0 errors, 0 failures, 1 skipped`. Section (d) is the re-run after the review fixes: the same result. Section (e) is the re-run after the second review's fixes (domain 141): **19 passed, 1 skipped**, `20 tests, 0 errors, 0 failures, 1 skipped` (the new test is `test_gen_props_camera_labels_follow_the_extrinsics_used`). Section (f) is the re-run after the third review's fixes: **19 passed, 1 skipped**, `20 tests, 0 errors, 0 failures, 1 skipped` |
| `camera_json_test.txt` | — | `test_optical_frame_matches_camera_json` against SYNTHETIC `camera.json` files in a scratch folder (not calibrations): skipped without the file; with a file and the convention unsettled it **fails** (match or not); with the flag set in a scratch copy it passes on a matching file and fails on a mismatching one. Cases 6–9 (third review) run the **whole suite** with a regenerated `car_props.xacro`: before the fix, a calibrated synthetic `camera.json` with the flag set gave `1 failed, 19 passed` (`test_optical_frame_pose_from_measurements`); after it, `19 passed, 1 skipped` |
| `measurement_csv_test.txt` | — | third review: the measurement-based tests against a `car.json` rebuilt from the M1.T9 template (SYNTHETIC: the 2026-10-10 readings re-typed under the plan key names, and a roll-out variant). Before the fix: 8 failed (`KeyError` on the 2026-10-10 row names) and 4 failed; after it: `19 passed, 1 skipped` in both, while a disagreeing CSV and a re-weighed mass still fail |
| `daemon_stop.txt` | — | the leftover `ros2-daemon` (domain 47) in `beaconmind-ros`, before and after `ros2 daemon stop`; a host daemon on domain 87 from an earlier check, recorded as running at 07:52 and found **gone** by ~08:15 (update at the end of the file: host `ps` at 08:24 shows no ros2 daemon) |
| `tf2_echo.txt` | 9 | expanded URDF written to `sim/isaac/assets/beaconmind_car.urdf`; `robot_state_publisher` up; `tf2_echo base_link camera_optical_frame -p 6`; full-precision `/tf_static`; clean stop; launch log |
| `urdf_diff.txt` | — | before/after proof that the expanded URDF did not change (below); section D is the re-check after the review fixes, section E after the second review's fixes, section F after the third review's fixes (F3 corrects which lab-wrapper copy sections B, D2 and E2 expanded) |
| `urdf_before.urdf` | — | the expansion of the hand-written package before this session's edits (the "before" side) |

## The expanded URDF did not change (`urdf_diff.txt`)

The hand-written `car_props.xacro` was replaced by a generated one, and the values `car.json` does not carry moved
to the hand-written `car_geometry_extras.xacro`. `course-project/tools/urdf_compare.py` compared the before and
after expansions element by element: **214 elements, 406 numbers (every origin, box, cylinder, sphere, mass,
inertia, colour and axis), 0 mismatches**: the description is **numerically identical, not byte-identical** to the
pre-change expansion. The only text change is the header comment of `beaconmind_car.urdf.xacro` (2 lines replaced by
4; `urdf_compare.py` counts 6 changed lines). The Module 6 lab wrapper (`gazebo_car.urdf.xacro`, which includes this description and
adds the instructor's `<gazebo>` blocks) expands to **byte-identical** output before and after (same sha256), so the
lab's screenshots still show this model.

**Re-checked after the review fixes (section D).** `car.json` `imu_z_m` became the height above the axle
(0.0265 m, as M1.T9 step 3 defines it) instead of above the floor (0.060 m), so `car_props.xacro` now takes `imu_z`
straight from `car.json` and derives `imu_top_h = imu_z + wheel_radius` (before: the reverse). The new expansion is
**byte-identical** to `sim/isaac/assets/beaconmind_car.urdf` (sha256 `81a7d617…`, same command as step 9), so
`urdf_compare.py` against `urdf_before.urdf` gives the same 0 mismatches. The lab wrapper, expanded from one fixed
path with its include pointed at the original (pre-session), the previous and the new description, gives three
byte-identical files (sha256 `8fa2107b…`; the earlier `d2a41cbe…` differs only because xacro writes the input path
into its banner comment).

**Re-checked after the second review's fixes (section E).** `car.json` changed only in three uncertainties
(`front_overhang_m` and `imu_x_m` 0.002 → 0.003 m, `chassis_length_m` 0.0036 → 0.0042 m: the 3 mm axle-datum floor
now covers every axle-line reading), so the regenerated `car_props.xacro` differs from the previous one in comments
only (the `car.json` sha256 line and those two ± values). The description's expansion is again byte-identical to
`sim/isaac/assets/beaconmind_car.urdf` (`81a7d617…`); against the pre-session `urdf_before.urdf` it is, as before,
**numerically identical, not byte-identical** (214 elements, 406 numbers, 0 mismatches; the 6 header-comment lines of
section A differ). The lab wrapper, expanded from one fixed path with its include pointed at the pre-session, the
previous and the current package, gives three byte-identical files (`2cc877fb…`; section D's `8fa2107b…` differs
only in xacro's banner line, which prints the input path), 434 numbers, 0 mismatches.

**Re-checked after the third review's fixes (section F).** Only comments of `car_geometry_extras.xacro` changed (the
stated source of the stand-in masses), and comments of an included file do not reach the expansion: the description
expands **byte-identically** to `sim/isaac/assets/beaconmind_car.urdf` (`81a7d617…`), still numerically identical to the
pre-session expansion (214 elements, 406 numbers, 0 mismatches). The lab wrapper, this time copied from the **current**
`module-6-gazebo-sim/urdf/gazebo_car.urdf.xacro` (the file the lab container uses), expands to three byte-identical
files from the pre-session, round-3 and current package (`92eff3de…`; 434 numbers, 0 mismatches). **Correction (F3):**
sections B, D2 and E2 copied the Spark's mirror of `lab-step10/gazebo_car.urdf.xacro`, which is older than the Mac's
(only its header AI-note lines 3–4 differ); on the Mac the two wrapper copies are identical. Same model either way
(`urdf_compare.py`: 434 numbers, 0 mismatches). The lab files were not edited and the Spark mirror was not re-synced.

## TF against the measured lens pose (no `camera.json` yet)

| | x (m) | y (m) | z (m) | roll, pitch, yaw (deg) |
| --- | --- | --- | --- | --- |
| Expected from `car.json` (`lens_x_m`, `lens_y_m`, `lens_z_m` − `wheel_diameter_m`/2) and REP 103 with the mount angles ASSUMED 0 | 0.120 | 0.000 | 0.075 − 0.0335 = 0.0415 | −90, 0, −90 |
| `tf2_echo base_link camera_optical_frame` | 0.120000 | 0.000000 | 0.041500 | −90.000000, −0.000000, −90.000000 |
| Difference | 0 | 0 | 0 | 0 |

Pass against the plan's limits (1 mm, 0.1°), but this only shows that the URDF reproduces the ruler readings. The
plan's check is against `camera.json` `extrinsics` from the calibration, which does not exist.

## Deviations from M2.T4 step 5 (recorded for Xiaohui; the URDF stays as it is for the Module 6 lab)

The shared description was reviewed for the Module 6 lab before it became M2.T4's URDF, and it departs from the letter
of step 5 in the ways below. None changes the total mass (0.506 kg), the frames of C1 or any joint position step 5
fixes. Xiaohui to accept each one, or to have the plan text changed; changing the URDF instead would change the lab's
model, whose screenshots are taken.

**2026-10-29 numbers.** The six deviations still hold for the M1.T16 model, with these values: total 0.660 kg; chassis
0.575 kg against step 5's `mass − 2·0.03 − 0.01` = 0.590 kg; chassis centre of mass (8.809, −0.174, 14.5) mm for a
whole-car centre of mass of 10.545 mm; 16 chassis boxes (15 since the 2026-10-16 rounded front, plus the power bank). The Module 6 reason no longer applies:
the lab uses a frozen snapshot since 2026-10-29 ([`2026-10-29-m1t16/`](2026-10-29-m1t16/README.md)).

1. **`chassis_link` is 12 boxes at the measured heights, not one box with its bottom at the axle.** Step 5: a box from
   `−axle_to_rear` to `+axle_to_front`, `body_width` wide, `chassis_height` tall, bottom at the axle. The URDF draws the
   plate strip and 4 wing slices (z +11 to +14 mm, i.e. 44.5–47.5 mm above the floor), the two TT gearboxes (bottoms
   3.5 mm **below** the axle, z −3.5 to +11 mm), the breadboard, the BNO055 board, the battery holder, the ESP32-CAM
   stack and the camera stand (top z +66.5 mm). Its x extent is the step's (−0.077 to +0.138 m); its widest point is
   ±74.4 mm (the stepped half-ellipse of the 150 mm wing).
2. **Chassis mass 0.421 kg, not step 5's 0.436 kg; and its inertia box.** Step 5: `mass − 2·0.03 − 0.01` = 0.436 kg.
   The URDF also subtracts the camera (0.010 kg) and IMU (0.005 kg) stand-ins, which it puts on `camera_link` and
   `imu_link` (item 3). The chassis inertia is a solid box of 0.208 × 0.100 × 0.036 m (plate length × strip width ×
   main-body height) centred on a chassis centre of mass (x 35.97 mm, y −0.24 mm, z 14.5 mm) that makes the whole car's
   centre of mass the lever-rule value (33.676 mm) — step 5 says neither.
3. **`camera_link` (0.010 kg) and `imu_link` (0.005 kg) carry inertials; step 5 gives them none.** Those two masses are
   the Module 6 guide's defaults (the instructor's `guide-original/urdf/gazebo_car.urdf.xacro`: camera_link 0.01,
   imu_link 0.005 kg; `assignments/assignment6/derived-values.md` line 41), not M2.T4 values. The wheel (0.030 kg each)
   and caster (0.010 kg) stand-ins are step 5's. `car_geometry_extras.xacro` used to credit all four to "project
   defaults, M2.T4"; that comment now names each source (third review; comment-only, section F).
4. **Wheel joints `rpy (−π/2, 0, 0)` with `axis 0 0 1`, not `axis 0 1 0`.** The same spin axis in `base_link` (+y).
   Kept from the instructor's Module 6 model, whose DiffDrive plugin uses this joint layout, and so that the tyre
   cylinder needs no extra rotation; explained in `beaconmind_car.urdf.xacro` and checked by
   `test_wheel_separation_equals_track_width`.
5. **Wheel collision is a sphere of `wheel_radius`; the visual is the cylinder.** Step 5 says "cylinder links". The
   sphere is the Module 6 guide's choice (its section 5.1: one contact point in the middle of the tyre; a cylinder made
   the simulated robot turn about 20 % more than its odometry), explained in `beaconmind_car.urdf.xacro`.
6. Visual-only extras step 5 does not list: a fork block on `caster_link` and a camera-module box on `camera_link`.

## What is still missing for M2.T4 to be `done`

- **M1.T7 `configs/camera.json`**: then `gen_props.py` reads its extrinsics and step 9 is re-run against it.
  M1.T7 writes the file with null extrinsics until its step 8; `gen_props.py` then keeps the `car.json` lens
  readings and the ASSUMED 0 angles and says so in each comment and in its printout (`extrinsics_used()`, separately
  for x/y/z and for the angles; checked by `test_gen_props_camera_labels_follow_the_extrinsics_used`).
  `test_optical_frame_matches_camera_json` skips only while the file is absent; once it exists the test compares
  the composed `base_link → camera_optical_frame` with `x_m`, `y_m`, `z_m − wheel_radius` and the rpy rotation, and
  it **fails** with a message naming the conflict until `CAMERA_CONVENTION_SETTLED` in `test/test_urdf.py` is set
  to `True` after Xiaohui decides (so it cannot stay silently skipped).
  **The route to done, and what it gives (third review):** M1.T7 writes `configs/camera.json` with **all six**
  extrinsics → run `gen_props.py` again → set `CAMERA_CONVENTION_SETTLED = True` (after the decision below) → colcon
  should report `20 tests, 0 errors, 0 failures, 1 skipped`. The skipped test is then
  `test_optical_frame_pose_from_measurements`: it compares the pose with the `car.json` lens readings only for the parts
  `gen_props.py` did **not** take from `camera.json` (`extrinsics_used()`), so with all six from the calibration it
  checks the fixed REP 103 joint and skips. Before this fix it compared the calibrated pose with the ruler readings and
  failed (`camera_json_test.txt` case 6: `1 failed, 19 passed`; case 7 after the fix: `19 passed, 1 skipped`). Interim
  states, both failing **by design**: the flag still `False` → 1 failure (case 8); angles still null →
  `test_optical_frame_matches_camera_json` fails "extrinsics lack numbers" (case 9).
- **A convention to settle first (plan conflict, README §1.4 item 8):** M1.T7 step 8 defines `extrinsics.z_m` as the
  lens height above the **floor**, while M2.T4 puts `base_link` at **axle height** (wheel joints at z = 0) and says
  the TF translation must equal `z_m`. They differ by the wheel radius (33.5 mm). `gen_props.py` treats `z_m` as a
  floor height (`camera_z = camera_h − wheel_radius`), consistent with M1.T7. Similarly, M1.T7 step 9 records small
  mount angles while M2.T3's `optical_to_link_rpy_deg` expects the full base_link → optical rotation;
  `gen_props.py` refuses camera angles beyond ±20° rather than guess.
- **M2.T3 `beaconmind.config.load_car`**: `gen_props.py` uses `load_car_standin()` (the M2.T3 mapping table,
  re-implemented inside the generator) until it exists; then `build_view()` switches to it.
- **M1.T9 done** (blocked: single readings, no roll-out, no encoder counts, `chassis_*` meaning and the corners'
  centring assumption to accept: `evidence/M1/M1.T9/README.md`). **When `car.json` is rebuilt from the filled
  template** (third review): `test/test_urdf.py` needs no edit, because its measurement-based tests read the CSV that
  `car.json`'s `evidence` fields name, through `write_car_json.read_csv` and the plan-key table `ROW_FOR_KEY`, with the
  roll-out diameter when both roll-outs exist (`measurement_csv_test.txt`). The filled CSV must therefore sit where
  `car.json` says, `evidence/M1/M1.T9/<file name>` (the plan's evidence folder; the writer always writes that folder
  plus the CSV's file name), or the tests stop with "measurement CSV … not found". **`car_geometry_extras.xacro` does
  need a hand edit in the same session** for every row it uses that is re-measured: B1, B2, B5 narrow, B5b, B14 width
  (also template rows, which feed `corners`), B9 and the B10 battery-holder top (`chassis_height`), and rows the
  template does not have: B8 (plate underside), the B10/B12/B13 breadboard and battery-holder boxes, the B14 front-top
  height, the B10 camera-stand top, C3 (swivel x) and K2 (the two-scale loads). The xacro guard catches B9/B10, and
  `test_com_matches_lever_rule` catches a `car.json` mass from a new weighing while `caster_load` is still the
  2026-10-10 one (`measurement_csv_test.txt` case A4); nothing catches B1, B2, B5 narrow, B5b or B14.
- **Deviations from step 5** (section above): for Xiaohui to accept or have the plan changed.
- The test count is 20, not the plan's 9: the 9 planned tests, 7 model checks kept from the Module 6 review, and
  4 new ones for the generator (`test_props_files_do_not_overlap`, `test_gen_props_rejects_bad_input`,
  `test_gen_props_camera_labels_follow_the_extrinsics_used`, `test_optical_to_link_rpy`). In the third review the
  model check `test_read_measurements_honours_superseding_rows` became `test_measurement_reader_follows_the_writer_rules`
  (same rules, now on the reader the tests use, plus plan keys and roll-outs). Expected values computed from the CSV are
  compared within 2e-6 m (`MEAS_TOL`; car.json and the xacro each round to 1 µm, so a mean of three readings or a
  roll-out can land about 1.5 µm away); the plan's 1e-6 is kept for everything else.
- `colcon test` needs `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` in `beaconmind-ros` until the M1.T3 image pins a pytest
  that Humble's plugins accept or sets the variable.

## Module 6 lab: stale pointers to `car_props.xacro` (recorded here, the lab files were NOT edited)

This task split the reviewed, hand-written `car_props.xacro` in two: `car_props.xacro` is now GENERATED from
`configs/car.json` and holds only what `car.json` carries (wheel, track, overhangs, body width and height, lens, IMU,
caster diameter and contact, total mass), and the rest moved to the hand-written `car_geometry_extras.xacro`: the
plate outline (B1, B2, B5 narrow, B5b, the half-ellipse wing), the part boxes, the stand-in part masses, and the
centre-of-mass inputs (`caster_swivel_x` = C3 0.120 m, `caster_load` 142 g, `com_x` = 33.676 mm). The model did not
change (above), but three Module 6 lab texts still name `car_props.xacro` for values that now live in
`car_geometry_extras.xacro`:

- `assignments/assignment6/derived-values.md` line 3: "Superseded … by the reviewed values in
  `…/urdf/car_props.xacro` (… COM x 33.7 mm from the 120 mm pivot, the 151 mm wing reading is not used)". The COM
  inputs and the wing are in `car_geometry_extras.xacro` now.
- `assignments/assignment6/lab-step10/gazebo_car.urdf.xacro` and its copy
  `assignments/assignment6/module-6-gazebo-sim/urdf/gazebo_car.urdf.xacro` (identical on the Mac; the Spark's mirror of
  the `lab-step10` copy is older by its header AI note, `urdf_diff.txt` F3), header line 14: the body's numbers come
  "from my own measurements … through car_props.xacro". (Line 105, "Measured values from the shared description
  (car_props.xacro)", is still right: `wheel_separation` and `wheel_radius` are in the generated file.)

They are lab deliverables, so they were left as they are. Suggested wording for Xiaohui (or whoever edits the lab
files): "car_props.xacro (generated from configs/car.json) + car_geometry_extras.xacro (hand-written)". The wrapper
lines are XML comments, so changing them would not change the expanded model; check the lab's expansion again if
they are edited.

## Generative-AI disclosure

Claude Opus 5.5 (xhigh effort) via Claude Code (2026-10-10) wrote `gen_props.py`, `car_geometry_extras.xacro` (the
reviewed values and comments moved out of the earlier hand-written props file), the edits to
`beaconmind_car.urdf.xacro` and `test/test_urdf.py`, `course-project/tools/urdf_compare.py`, ran the steps above and
wrote this README; later the same day it applied the review fixes (axle-relative IMU height, the camera.json test's
comparison, the daemon stop, the `blocked` status) and re-ran the checks; after a second review the same day, it made
`gen_props.py` label the camera values by the extrinsics the view actually used (`extrinsics_used()` and its test),
regenerated `car_props.xacro` (comments only), re-ran the before/after expansions (section E) and colcon (section e),
corrected the host-daemon record and wrote the Module 6 pointer note above; after a third review the same day, it made
`test_optical_frame_pose_from_measurements` leave out the camera values taken from `camera.json`, made the
measurement-based tests read the CSV that `car.json` names (through `write_car_json.py`'s reader and plan-key table),
corrected the stand-in-mass comments of `car_geometry_extras.xacro`, wrote the step-5 deviation list above, ran the
synthetic full-suite cases (`camera_json_test.txt` 6–9, `measurement_csv_test.txt`), colcon (section f) and the
expansions (section F), and found the stale Spark mirror of the lab wrapper. The car measurements are Xiaohui Chen's.
