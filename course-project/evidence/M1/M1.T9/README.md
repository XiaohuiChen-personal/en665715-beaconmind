# M1.T9 evidence: car measurements and `configs/car.json`

**Measured by Xiaohui Chen on 2026-10-10** at the bench (car on the floor, battery switch off, camera fitted, no
USB cable). On 2026-10-29, for M1.T16, he weighed the whole car and the two-scale split again, read the power-bank
box (B15 rows), the cable points (X1, now superseded by `B4_rear_most_x_remeasure`; X2) and the camera cable's tip
(`B3_front_most_x_remeasure`), and decided the footprint; the board's own front was re-filed as `B14b` (section below). The 2026-10-10
readings were taken for the Module 6 Gazebo lab and reviewed there
(`assignments/assignment6/review/MEASUREMENT-REVIEW.md` in the private course repo, round 1: 54 findings, each
re-checked against the photos and the arithmetic). This task turns them into the project's `configs/car.json` (schema `bm.car/1`).
M1.T9 is **blocked**, not done (plan README §1.2 step 4, §1.4 items 1 and 8): the remaining work needs Xiaohui at
the bench or his decisions. See "What is still missing".

## 2026-10-29 update: the M1.T16 mass

Xiaohui weighed the car as it is now (M1.T16, `evidence/M1/M1.T16/measurements.md`), in what `measurements.md` calls
the "staying configuration"; the M1.T16 prerequisites in `plan/M1-foundations.md` define it as bank fixed, four cells
in, camera on, only the cables that stay on the car. The battery switch state at that weighing was not recorded (the
"Battery OFF" on the CSV's first line describes the earlier rows). So `car.json` is now built from
**`measurements-2026-10-29-with-m1t16-mass.csv`**: the 2026-10-16 CSV unchanged (every row; only dated `#` comment
lines added at the top) plus these rows at the end:

| Row | Reading | Used for |
| --- | --- | --- |
| `K1_total_mass_remeasure` (→ `mass_kg`) | **660 g**, one Pitney Bowes postal scale (5 kg × 1 g) | `car.json` `mass_kg`; replaces `K1_total_mass` (506 g, 2026-10-10) |
| `K2_caster_load_remeasure`, `K2_drive_wheels_load_remeasure` | **58 g + 602 g** = 660 g, two scales of that model side by side; caster **not** turned sideways, trail direction unknown | `car_geometry_extras.xacro` (`caster_load`, `drive_wheels_load`, `com_x`) |
| `B15_bank_front_x`, `B15_bank_rear_x`, `B15_bank_bottom_h`, `B15_bank_height`, `B15_bank_width`, `B15_bank_tyre_gap` | 15 and 85 mm behind the axle, 17 mm above the floor, 25 mm tall, 70 mm wide, 18 mm to each tyre | the power-bank box in `car_geometry_extras.xacro` (geometry only) |
| `X1_pico_usb_cable_rear_x`, `X2_lowest_cable_h` | 148 mm behind the axle, 7 mm above the floor | X1: **superseded** by `B4_rear_most_x_remeasure` (the same reading, footprint update below); X2: the bottom of the URDF's visual-only rear cable, not a `car.json` input |
| `B3_front_most_x_remeasure`, `B4_rear_most_x_remeasure` (added later the same day) | 178 mm ahead of the axle (the camera cable, 40 mm past `B3_front_most_x`), 148 mm behind (the Pico cable) | `front_overhang_m`, `rear_overhang_m` (footprint update below) |

Effect of the weighing on `car.json`: `mass_kg` 0.506 → **0.660 kg** (± 0.0014 kg, the same two-scale rule: 58 g +
602 g, which one scale read as 660 g); its `source` names `K1_total_mass_remeasure`. Every entry's `evidence` and
`updated` now name the new CSV (or `derived.txt`) and 2026-10-29, and the `measured` block notes the update. At that
step nothing else changed (checked key by key); the footprint update below came later the same day.

**The footprint, first kept (history).** At first `front_overhang_m`, `rear_overhang_m`, `chassis_length_m`,
`corners` and `sweep_radius_m` were deliberately not updated: the bank's rear face (85 mm behind the axle) is 8.5 mm
behind the plate's rear apex (`rear_overhang_m` was 76.49 mm), the Pico's USB cable reaches 148 mm behind the axle,
outside the 0.140 m sweep radius of the time, and the front-most point of the camera's cable was not yet measured.
`chassis_height_m` still stays the gearbox-bottom-to-battery-top 36 mm, which the URDF guard and the chassis inertia
box use, although the bank (17 mm above the floor) is now the lowest body point. Ride height, camera stand, BNO055,
antenna, tyres and cell type are unchanged (`evidence/M1/M1.T16/confirm.md`).

### Later on 2026-10-29: the footprint, by Xiaohui's decision

Xiaohui read the camera's USB cable (chat, 23:45 CDT): "The cable at the front sticks out 4cm than the original",
confirmed as 40 mm past `B3_front_most_x` (138 mm), i.e. **178 mm** ahead of the axle line, to the nearest centimetre
("4cm" read to the nearest centimetre, the agent's reading: ±5 mm on the 40 mm, so ±5.8 mm on the 178 mm with B3's
3 mm, a stated row exception in `write_car_json.py`, `ROW_UNCERTAINTY`); its y and height were not given. He then chose to keep the cables as they are
and update the footprint now (instead of rerouting them or leaving it open). Rows `B3_front_most_x_remeasure` (178 mm)
and `B4_rear_most_x_remeasure` (148 mm, the Pico cable, the same reading as X1, which is now `SUPERSEDED`) were added
to the same CSV, and `car.json` was rebuilt:

| Key | Before | After | ± | Note |
| --- | --- | --- | --- | --- |
| `front_overhang_m` | 0.138 m | **0.178 m** | 0.0058 | the camera cable's tip; root-sum-square of 3 mm (B3) and 5 mm ("4cm") |
| `rear_overhang_m` | 0.07649 m | **0.148 m** | 0.003 | the Pico cable; axle-datum floor |
| `chassis_length_m` | 0.21449 m | **0.326 m** | 0.0066 | the whole car with its cables |
| `corners` | (0.138, ±0.010), (−0.07649, 0) | **(0.178, ±0.010), (−0.148, 0)** | 0.0058 | other corners unchanged |
| `sweep_radius_m` | 0.140 m (the swung caster) | **0.178281 m** | 0.0058 | hypot(0.178, 0.010), at the front-most corners, which rest on **two assumptions**: the cable taken as wide as the ESP32-CAM board, and centred (deviation 8) |

Every other value and uncertainty is unchanged (checked key by key). The writer's corner labels and the corners /
`sweep_radius_m` `source` texts became generic ("front-most corner", "rear-most point") and state both assumptions,
because those points are no longer the ESP32-CAM board and the plate's rear apex; its one logic change is the
exact-row uncertainty exception for `B3_front_most_x_remeasure` (`ROW_UNCERTAINTY`, ±5.8 mm). The original
`B3_front_most_x` reading (138 mm) is re-filed as row `B14b_esp32cam_front_x`, the board's own front, which the URDF
reads and `car.json` does not. The URDF draws the cables as envelope boxes (`car_geometry_extras.xacro`, "Cables"): the
front one with a collider, so the simulated first front wall contact is at `front_overhang_m` (an agent decision for
Xiaohui to accept), the rear one visual only (it hangs toward the floor), so the simulated first rear wall contact is
the bank's rear face, 63 mm short of `rear_overhang_m`. The ESP32-CAM board box still ends at 138 mm.

The centre of mass is not a `car.json` key. Xiaohui's decision is to use the middle value, 0.0105 m ahead of the
axle, ± 0.0018 m for the unknown caster trail direction (2026-10-10: 0.0337 m). `car_geometry_extras.xacro`
implements it with the caster's swivel x C3 (120 mm) as the lever arm: 120 × 58 / 660 = 0.0105 m. The ± 0.0018 m
assumes the 20 mm trail of the 2026-10-10 notes; from the readings alone (the swung-forward caster front, about
140 mm, limits the forward contact to about 127.5 mm) the range is 0.0088 to 0.0112 m, and 0.0105 m lies inside
both. `write_car_json.py` changed only the reason text of the K1 uncertainty (now generic; it named only the
2026-10-10 readings); its logic and `TWO_SCALE_KG` are unchanged.

## 2026-10-16 update: the plate outline from a classmate's CAD

A classmate shared, with the instructor's permission, an Onshape model and drawing of the Emo chassis
plate: `the private course repo (plate CAD is not published here)` (files, what a STEP file is, every dimension, and the checks). Its hole
pattern matches **this car's** plate on the bottom-view photo to 0.25 mm rms (16 features), and on that photo the wing
depth is 34.0 mm, not the 40 mm of the ruler reading. So `car.json` is now built from
**`measurements-2026-10-16-with-plate-cad.csv`**: the 2026-10-10 CSV unchanged (all 47 lines) plus superseding rows
from the CAD (instrument `CAD ...`, ±0.5 mm allowance) and two rows fitted to the CAD length (instrument `fit ...`):

| Row | 2026-10-10 | 2026-10-16 | Source |
| --- | --- | --- | --- |
| `B5_plate_width_max` (→ `chassis_width_m`) | 150 mm ± 2 | **147.92 mm ± 0.5** | CAD |
| `B5_plate_width_narrow` | 100 mm ± 2 | **100 mm ± 0.5** | CAD (agrees) |
| `B5b_wing_depth_centre` | 40 mm ± 4 | **34.35 mm ± 0.5** | CAD; photo 34.0 |
| `P1_plate_front_arc_radius`, `P2_plate_front_corner_radius` (new rows) | – (square corners assumed) | **135.14 mm, 8 mm ± 0.5** | CAD |
| `B1_plate_front_x` | 131 mm ± 3 | **130.49 mm ± 3** | fit: B1 + B2 to the CAD length 206.98 mm |
| `B2_plate_rear_x`, `B4_rear_most_x` (→ `rear_overhang_m`) | 77 mm ± 3 | **76.49 mm ± 3** | fit |

Effect on `car.json`: `chassis_width_m` 0.14792 ± 0.0005, `rear_overhang_m` 0.07649, `chassis_length_m` 0.21449
± 0.0042; the plate-front corners follow the rounded front (`car_model.rounded_front_corner`): (0.1229, ±0.0447) m,
r = 0.1308 m instead of (0.131, ±0.050), r = 0.1402 m; so `sweep_radius_m` is **0.140 ± 0.005 m**, now reached at the
caster swung fully forward on the centre line, with **no centring assumption** (deviation 8 below no longer sets the
sweep radius). Nothing else changed: wheel diameter, tyre width, track, caster, camera, IMU, heights and mass are the
2026-10-10 readings (the CAD has no wheels). `measured.json` notes, `derived.txt` and `schema-validate.txt` were
re-written; the run logs are in `plate-cad-2026-10-16/` (Mac pytest 63 passed; `beaconmind-ros` Python 3.10 pytest
63 passed; colcon 21 tests, 0 failures, 1 skipped; the expanded URDF compared by element name).

`write_car_json.py` gained the CAD rule (instrument starting `CAD` → 0.5 mm, applied before the B5b review override,
whose reason concerns the 40 mm ruler reading), the P1/P2 rows (`EXTRA_ROWS`, and the template has them) and the
rounded plate-front corners; without P1/P2 it builds the square corners exactly as before (the 2026-10-10 CSV still
gives the old `car.json` values). `test_configs_car_json_is_the_writer_output` now reads the CSV and date that
`car.json` names instead of the 2026-10-10 file name.

## Files

| File | What it holds |
| --- | --- |
| `measurements-xiaohui-chen-2026-10-10.csv` | Xiaohui's readings: an unchanged copy of `assignments/assignment6/measurements.csv`, a private course repo file (sha256 `f26dbb39…25e573da`, same as the source) |
| `measurements-2026-10-16-with-plate-cad.csv` | The CSV `car.json` was built from between 2026-10-16 and 2026-10-29: the 2026-10-10 copy plus the plate-CAD and fit rows (2026-10-16 section) |
| `measurements-2026-10-29-with-m1t16-mass.csv` | **The CSV `car.json` is built from since 2026-10-29**: the 2026-10-16 file unchanged plus the M1.T16 mass, power-bank and cable rows (2026-10-29 section) |
| `plate-cad-2026-10-16/` | The 2026-10-16 run logs: `pytest-mac.txt`, `pytest-py310.txt`, `colcon-test.txt`, `urdf-named-diff.txt` |
| `measured.json` | The `measured` block written into `car.json`: who, when, instruments, and the deviations and conventions below |
| `derived.txt` | Output of `course-project/tools/write_car_json.py` (re-run 2026-10-29 for the M1.T16 mass and the cable footprint; first line = the command and the interpreter): every value, its source row, its uncertainty and the rule used, the corners (each labelled, the assumed ones marked), the derived keys, the omitted keys, and the schema check |
| `schema-validate.txt` | `python -m beaconmind.schemas car ../configs/car.json` → `OK ../configs/car.json (1 objects)` |
| `pytest-mac.txt`, `pytest-py310.txt` | `beaconmind` tests after the second review's fixes: Mac 55 passed; `beaconmind-ros` (Python 3.10) 55 passed. They include `tests/test_car_model.py` (15 tests, among them `test_configs_car_json_is_the_writer_output`: `car.json` is exactly what the writer builds from this CSV; three tests of the template; two tests that rows typed in m / kg give the same uncertainties as rows in mm / g) |
| `derived-dv-proposals.md` | Step 6: `done_range_m` 0.588 ± 0.003 m (placeholder 0.55), sweep radius 0.140 m, the nose-to-wall check, and why metres-per-count is not yet computable (written for the earlier footprint; `sweep_radius_m` is 0.178281 m since 2026-10-29, resting on two assumptions: deviation 8) |

The step-2 template is `course-project/tools/car_measurements_template.csv` (written 2026-10-10 after the review,
not used for the 2026-10-10 readings, which were taken for the Module 6 lab with their own row names). It has one
blank row per step-3 quantity the writer reads, under the plan's key names, plus the extra rows the writer reads
(`EXTRA_ROWS` in `write_car_json.py`); the derived quantities (`corners`, `chassis_length_m`, `chassis_height_m`)
are explained in its header comment. `test_template_filled_under_plan_keys_matches_the_evidence_build` checks that
the 2026-10-10 readings typed into its plan-key rows (in m and kg) give the same `car.json` values and the same
uncertainties, except three that it states: `caster_x_m` and `lens_x_m` (5 → 3 mm) and `sweep_radius_m`
(0.0048 → 0.0028 m), because the 5 mm rule reads the word "around" in the notes, which the 2026-10-10 rows have and
the template's instruction notes do not.

**Rebuilding `car.json` from the filled template (what else must happen in that session; third review).**
- Keep the filled CSV in this folder: the writer names `evidence/M1/M1.T9/<file name>` in every raw value's `evidence`
  field, and the URDF tests read the CSV from there.
- `ros2_ws/src/beaconmind_description/test/test_urdf.py` needs **no** edit: its measurement-based tests read the CSV that
  `car.json` names, through `write_car_json.read_csv` and `ROW_FOR_KEY` (plan keys first, then the 2026-10-10 row
  names), and use the roll-out diameter when both roll-outs exist. Before the third review they were tied to the
  2026-10-10 row names and would have failed (`evidence/M2/M2.T4/measurement_csv_test.txt`).
- Run `gen_props.py` again (M2.T4 step 7), so `car_props.xacro` follows the new `car.json`.
- **Edit `car_geometry_extras.xacro` by hand** for every re-measured row it uses (B1, B2, B5 narrow, B5b, B14 width, B9,
  B10 battery-holder top, and the part boxes, C3 and K2, which the template does not have; the full list is in
  `evidence/M2/M2.T4/README.md`). Only B9/B10 (the xacro guard) and a new total mass (`test_com_matches_lever_rule`)
  are caught if this is forgotten.

Photos: `assignments/assignment6/photos/` in the private course repo (bottom view, camera stand, battery holder, breadboard, wing close-up,
the two-scale weighing). They are **not copied here**: they show the desk, screens or a hand, and the plan forbids
personal items in evidence photos (plan README L8; `photos/README.md`). The plan's `car-top.jpg`,
`car-side.jpg` and `imu-orientation.jpg` (ruler in view, nothing personal in frame) do not exist yet.

## Method

- Lengths: one ruler/tape reading per quantity, in mm. The CSV names a ruler for rows B9 and B10; the other length
  rows say "not stated", and they are treated as ruler readings. x is measured forward from the drive-wheel axle
  line (+x toward the camera lens / caster end, the front Xiaohui confirmed), y to the robot's left, heights from
  the floor.
- Mass (since 2026-10-29, M1.T16): the whole car on one Pitney Bowes postal scale (5 kg × 1 g): 660 g; the same
  sitting split over two scales of that model, caster on one (not turned sideways) and both drive wheels on the
  other: 58 g + 602 g = 660 g. Until 2026-10-29 (the 2026-10-10 weighing): the car stood with its caster turned
  sideways on one Pitney Bowes kitchen scale (5 kg × 1 g) and both drive wheels on an identical scale at the same
  height: 142 g + 364 g = 506 g.
- `course-project/tools/write_car_json.py` maps the CSV rows onto the plan's keys (M1.T9 step 5), converts to m and
  kg, applies the superseding rule (a `_corrected` / `_recheck` / `_remeasure*` row replaces the earlier row;
  `SUPERSEDED` rows are not inputs), computes the derived keys, and validates the result.

| `car.json` key | Value | ± | From |
| --- | --- | --- | --- |
| `wheel_diameter_m` | 0.067 m | 0.002 | `W1_tyre_diameter_direct` (**direct, unloaded; not a roll-out**) |
| `wheel_width_m` | 0.027 m | 0.002 | `W2_tyre_width` |
| `track_outer_m`, `track_inner_m` | 0.160, 0.107 m | 0.002 | `W3_track_outer`, `W3_track_inner` |
| `track_width_m` | 0.1335 m | 0.0014 | derived: (outer + inner) / 2 |
| `caster_x_m` | 0.100 m | 0.005 | `C2_caster_contact_x` ("around"; trailing caster's floor contact) |
| `caster_diameter_m` | 0.025 m | 0.002 | `C1_caster_wheel_diameter_recheck` (re-check of the first 25 mm reading) |
| `front_overhang_m` | 0.178 m (0.138 until 2026-10-29) | 0.0058 (0.003 until 2026-10-29) | `B3_front_most_x_remeasure` (the camera's USB cable, 40 mm past `B3_front_most_x`; root-sum-square of 3 mm and 5 mm, a stated row exception); until 2026-10-29 `B3_front_most_x` (ESP32-CAM USB-C side, **no cable**; axle-datum floor) |
| `rear_overhang_m` | 0.148 m (0.07649 until 2026-10-29; 0.077 until 2026-10-16) | 0.003 | `B4_rear_most_x_remeasure` (the Pico's USB cable; axle-datum floor); until 2026-10-29 `B4_rear_most_x_corrected` (= plate rear apex; fitted to the CAD length) |
| `chassis_length_m` | 0.326 m (0.21449 until 2026-10-29; 0.215 until 2026-10-16) | 0.0066 (0.0042 until 2026-10-29) | derived: front + rear overhang (since 2026-10-29 the whole car with its cables) |
| `chassis_width_m` | 0.14792 m (0.150 until 2026-10-16) | 0.0005 | `B5_plate_width_max_corrected` (CAD; widest **body** point, tyres excluded; over the tyres 0.160 m): **deviation 7** |
| `chassis_height_m` | 0.036 m | 0.0028 | derived: `B10_battery_holder_top_h` 66 − `B9_lowest_body_h` 30 mm (**main body**; the camera stand reaches ~100 mm; since 2026-10-29 the power bank's bottom, 17 mm, is lower than `B9`, and this key is deliberately left as it is): **deviation 7** |
| `lens_x_m`, `lens_y_m`, `lens_z_m` | 0.120, 0.000, 0.075 m | 0.005, 0.002, 0.002 | `S3_lens_x` ("around"), `S3_lens_y`, `S3_lens_centre_h` (height above the **floor**) |
| `imu_x_m`, `imu_y_m` | −0.061, +0.020 m | 0.003, 0.002 | `S1_imu_board_centre_x` (axle-datum floor), `S1_imu_board_centre_y_corrected` (robot LEFT) |
| `imu_z_m` | 0.0265 m | 0.0022 | derived: `S1_imu_board_top_h` 60 mm (board top above the floor) − `wheel_diameter_m` / 2 = 33.5 mm, i.e. the board top above the **axle** midpoint, as M1.T9 step 3 defines the IMU position; ± = root-sum-square of 2 mm and 1 mm |
| `mass_kg` | 0.660 kg (0.506 until 2026-10-29) | 0.0014 | `K1_total_mass_remeasure` = 660 g on one scale = 58 g + 602 g (M1.T16; ± = root-sum-square of two 1 g readings, as for `K1_total_mass` = 142 g + 364 g on 2026-10-10) |
| `corners` | 12 points | 0.0058 (0.005 until 2026-10-29) | derived plan-view extremes (`derived.txt` lists them); four of them **assume** a centred part, and since 2026-10-29 the two front-most ones also take the camera cable as wide as the board: **deviation 8** |
| `sweep_radius_m` | 0.178281 m (0.140 until 2026-10-29; 0.1402 until 2026-10-16) | 0.0058 (0.005 until 2026-10-29) | derived: max distance over `corners`, reached since 2026-10-29 at the front-most corners (two assumptions: the camera cable taken as wide as the board, and centred); from 2026-10-16 at the caster swung fully forward (no assumption); before that at the plate's square front corners, one of the assumed ones: **deviation 8** |

Every value has `status: "measured"` (a reading, or arithmetic on readings), with the stated assumptions of
deviation 8 (centring; since 2026-10-29 also the camera cable's width), which the `source` text of `corners` and
`sweep_radius_m` names. Raw values cite their CSV row in
`source`; derived values have a `source` starting `"M1.T9 (derived)"` and `evidence: "evidence/M1/M1.T9/derived.txt"`.

**Uncertainty rule** (the `uncertainty` field, in m or kg): 2 mm for a single ruler reading, 5 mm when the reading
was given as "around", 1 g per scale reading. Exceptions: **every x measured from the drive-wheel axle line carries at
least 3 mm**, because the axle line itself is located to about 3 mm (review #15 raised it for B1/B2, "Keep 131 / 77
± 3 mm"; the 3 mm is the review's total, so it is a floor, not added to the 2 mm). That covers B1, B2, B3
(`front_overhang_m`), B4 (`rear_overhang_m`) and `S1_imu_board_centre_x` (`imu_x_m`) at 3 mm, while the "around" rows
C2 (`caster_x_m`), C2b and `S3_lens_x` (`lens_x_m`) keep their 5 mm. The wing depth B5b has 4 mm (review #7), and the
two-scale mass has root-sum-square(1 g, 1 g) = 1.4 g. Derived values by first-order root-sum-square propagation. The
sweep radius uses the largest `r + u_r` over the points minus the largest `r`. B1 feeds the plate-front corners
(±0.0028 m in radius), and so the sweep radius. Every rule constant is stored in SI units, so a template row typed in
m or kg gets the same uncertainty as one typed in mm or g.

## Deviations from the M1.T9 procedure (recorded, not hidden; each is for Xiaohui to accept or redo)

1. **One reading per quantity, not three.** There is no repeatability check, so the plan's spread test
   (2 mm / 5 mm) could not be applied; the uncertainty rule above stands in for it.
2. **No 5-revolution roll-out.** Xiaohui measured the tyre diameter directly (unloaded) instead. `wheel_diameter_m`
   holds that reading, which is the key the M2.T3 view reads first; its `source` says it is not a roll-out.
   `rollout_left_m`, `rollout_right_m`, `wheel_diameter_left_m`, `wheel_diameter_right_m` are omitted rather than
   invented. A loaded rolling diameter can differ from the unloaded one, so odometry (M3.T3/M3.T8) must not rely
   on 0.067 m without a roll-out or a driven-distance check.
3. **Encoder counts per wheel revolution postponed** (step 4 needs the Pico on USB with the diagnostic firmware).
   `counts_per_rev_left`, `counts_per_rev_right`, `ticks_per_wheel_rev` are omitted, which the plan allows; the
   M2.T3 view then uses the nominal 4320 with an `assumptions` entry. The Pico was not touched in this session.
4. **No USB cable fitted** when `front_overhang_m` was first measured (2026-10-10; and when the car was weighed then; the
   2026-10-29 weighing was in the staying configuration, which the M1.T16 prerequisites define with the cables that
   stay on the car). Since 2026-10-29 `front_overhang_m` is the camera cable's tip, `B3_front_most_x_remeasure`
   (178 mm ± 5.8 mm, "4cm" read to the nearest centimetre); a finer reading with the operating cable can still come from
   M3.T1. The 2026-10-10 reading (138 mm, no cable) stays in the CSV as `B14b_esp32cam_front_x`, the board's own front.
5. **`imu_axes` not recorded** (no photo of the BNO055's printed axes from above).
6. **Camera not calibrated** (M1.T7 not done): `lens_*` are ruler readings, not `camera.json` extrinsics, and the
   camera's mount angles are unknown (the URDF assumes 0).
7. **`chassis_width_m` and `chassis_height_m` are the main body, not the whole car (so was `chassis_length_m` until
   2026-10-29; since then it is the whole car's length with its cables).** M1.T9 step 3
   defines them as the "Bounding box of the whole car". `car.json` holds the body without the drive wheels and
   without the camera stand, under the plan's key names, because that is what the URDF chassis box draws (M2.T4
   step 5, `body_width`) and what M2.T3 maps to `body_width_m` for kinsim's contact corners. The whole-car figures
   are: length 0.215 m (0.2145 m since the 2026-10-16 plate CAD; the same, except that the caster swung fully forward reaches x = 0.140 m, beyond the
   0.138 m nose; see `corners`; since 2026-10-29 `chassis_length_m` itself is the whole car's length with its cables,
   0.326 m), width **0.160 m** over the tyres (`track_outer_m`, not the body's 0.150 m, 0.148 m since the 2026-10-16 plate CAD), height about
   **0.100 m** from the floor to the camera-stand top (`B10_camera_stand_top_h`, "around 10 cm"; not 0.036 m).
   This is also a plan inconsistency (README §1.4 item 8: M1.T9 says whole car, M2.T4/M2.T3 use the key as the
   body width). Xiaohui to decide: accept the body meaning (and the plan text is amended), or store the whole-car
   box under these keys and give the URDF/kinsim body figures other keys. Kept as is so the URDF does not change.
8. **`corners`, and so `sweep_radius_m`, rest on stated assumptions.** The front-most corners (until 2026-10-29 the
   ESP32-CAM board's own, (0.138, ±0.010)) and the plate-front corners (square at (0.131, ±0.050) before the plate
   CAD) take y = ±(measured width) / 2: those parts are assumed centred on y = 0, since only the widths (B14 20 mm,
   B5 narrow 100 mm) were measured. Until 2026-10-16 the square
   plate-front corners were the farthest points and set `sweep_radius_m` = 0.140218 m (a strip 5 mm off centre would
   have raised it by about 2 mm); from the plate CAD on they are rounded, (0.1229, ±0.0447) m, and the sweep radius
   0.140 m was set by the caster on the centre line, so this assumption did not move it. Since 2026-10-29 the
   front-most corners are the camera cable's tip taken as wide as the ESP32-CAM board, (0.178, ±0.010) m; they are
   the farthest points, so `sweep_radius_m` = 0.178281 m depends on **two** assumptions: the cable is as wide as the
   board, and centred (its y and width were not given). The rear-most point, the Pico cable at (−0.148, 0), takes
   y = 0 (its y was not given), while the URDF's rear cable envelope is ±35 mm wide; the sweep radius does not depend
   on that, because the rear point could move about 99 mm sideways before it reached 0.178281 m.
   The stick antenna was not measured (review #9, Xiaohui's decision: thin and inside the footprint).

## Conventions to keep in mind

- `lens_z_m` is a height above the **floor**: M1.T9 step 3 says to measure the lens "as M1.T7 step 8", and M1.T7
  step 8 defines the camera's `z_m` as the lens centre height above the floor. The URDF's `base_link` is at
  **axle height**, `wheel_diameter_m / 2` = 0.0335 m above the floor, so the generated `car_props.xacro` subtracts
  the wheel radius for the camera (`camera_z` = 0.075 − 0.0335 = 0.0415 m).
- `imu_z_m` is a height above the **axle midpoint** (0.0265 m), because M1.T9 step 3 defines the IMU position
  "from the axle midpoint" and M2.T3 (`imu_xyz_m`) and M2.T4 (`imu_link` at `imu_x/y/z`) pass it to the URDF
  unchanged. `write_car_json.py` derives it from the floor reading `S1_imu_board_top_h` (0.060 m) minus the wheel
  radius; `car_props.xacro` uses it as `imu_z` directly and adds the radius back only for `imu_top_h`, the floor
  height of the board box. (Until the 2026-10-10 review, `car.json` stored the floor height 0.060 m under
  `imu_z_m`, and only `gen_props.py` subtracted the radius; a plan-following consumer would have put the IMU
  33.5 mm too high. The expanded URDF is byte-identical before and after this change.)
- `chassis_*`: see deviation 7.

## What is still missing for M1.T9 to be `done` (why the status is `blocked`)

- Three readings per quantity within the spread limits, or Xiaohui accepting the single readings as the recorded
  exception (the acceptance item allows "a note explaining any exception"; this README is that note, but the
  decision is Xiaohui's).
- Xiaohui's decision on deviation 7 (body vs whole-car `chassis_*`) and deviation 8 (accept the centring
  assumption, or measure the ESP32-CAM's and the plate strip's sideways offsets).
- The 5-revolution roll-out of each wheel (or Xiaohui accepting the direct diameter).
- Encoder counts (3 trials per wheel) or a recorded decision by Xiaohui to postpone them to M3.T3.
- `car-top.jpg`, `car-side.jpg`, `imu-orientation.jpg` and `imu_axes`.
- `CONTEXT.md` firmware / jumper / USB / battery record after the encoder step (unchanged: the Pico was not used).
- The plan's `encoder_handturn.py` and its two tests (not written, because the encoder step was postponed).
- Done since the first write-up: the step-2 template `course-project/tools/car_measurements_template.csv` (it was
  missing and not listed here). `write_car_json.py` now also reads an `imu_axes` text row, so filling that row is
  enough to put `imu_axes` into `car.json`. Since the third review the URDF tests follow whichever CSV `car.json`
  names, so the bench session needs no test edit; it does need the hand edits of `car_geometry_extras.xacro` listed
  above.

## Generative-AI disclosure

The measurements and photos are Xiaohui Chen's. Claude Opus 5.5 via Claude Code (2026-10-10) wrote
`course-project/tools/write_car_json.py`, `course-project/tools/car_measurements_template.csv`,
`beaconmind/src/beaconmind/car_model.py`, `beaconmind/tests/test_car_model.py`, `measured.json`,
`derived-dv-proposals.md` and this README, and generated `configs/car.json` with the writer; later the same day it
applied the review fixes (axle-relative `imu_z_m`, deviations 7 and 8, the B1 override, the template, the
`imu_axes` text row); after a second review the same day, it put the uncertainty constants in SI units (a
row typed in m or kg used to get an uncertainty 1000× too large; `car.json` was not affected, and that fix alone
rebuilt it byte-identical), extended the 3 mm axle-datum floor to every axle-line row (B3 and S1 x had been left at
2 mm, so `front_overhang_m`, `imu_x_m` and `chassis_length_m` changed their ± and nothing else), and added the m/kg
and template uncertainty tests; after a third review the same day, it wrote the "Rebuilding `car.json` from the filled
template" notes above (the URDF tests were changed in `evidence/M2/M2.T4/`; nothing in this folder's data changed).

AI-assisted: Claude Opus 5.5 (xhigh effort) via Cursor, 2026-10-29: wrote `measurements-2026-10-29-with-m1t16-mass.csv`
(a copy of the 2026-10-16 CSV plus rows that transcribe Xiaohui Chen's M1.T16 readings from
`evidence/M1/M1.T16/measurements.md`), updated `measured.json`, the K1 reason text in `write_car_json.py` and this
README, rebuilt `configs/car.json` with the writer and saved its output as `derived.txt`; after a review the same
day, sourced the configuration list to the M1.T16 prerequisites, stated the unrecorded battery state, corrected who
decided what about the centre of mass, made the K1 reason text generic and labelled the private-repo files (no value
changed); later the same day, after Xiaohui's cable reading and footprint decision, added the B3/B4 remeasure rows,
superseded X1, made the writer's corner labels generic, rebuilt `car.json` and `derived.txt` and wrote the footprint
section above; after a review of that, added the `ROW_UNCERTAINTY` exception (±5.8 mm on the 178 mm), the
`B14b_esp32cam_front_x` row, and the wording on the two assumptions behind the sweep radius, and rebuilt `car.json`
and `derived.txt` again. The readings and the footprint decision are Xiaohui Chen's.
