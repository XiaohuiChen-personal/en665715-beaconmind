# 2026-10-29 — URDF, Pico firmware, and camera status

Research-only. No URDF, `car.json`, firmware, or evidence file was edited. No new mass, intrinsics, or calibration was measured. The chip was not re-read on this date. Xiaohui Chen decides the open questions at the end.

This note is the context store for the 2026-10-29 plan and `CONTEXT.md` pass.

## 1. URDF still models the 2026-10-10 car

Checked in the files, not regenerated:

| Fact | Where |
| --- | --- |
| Total mass 0.506 kg | `course-project/configs/car.json` `mass_kg`; `course-project/ros2_ws/src/beaconmind_description/urdf/car_props.xacro` (`mass` 0.506). Source named there: 2026-10-10 weighing, batteries in, camera fitted, no cable |
| Chassis mass 0.421 kg is the leftover after stand-in part masses | `urdf/beaconmind_car.urdf.xacro`: 0.506 − 2×0.030 − 0.010 − 0.010 − 0.005 = 0.421. The part masses are stand-ins (`urdf/car_geometry_extras.xacro`) |
| Centre of mass x is the two-scale split | `car_geometry_extras.xacro`: `com_x = caster_swivel_x * caster_load / mass`, with swivel x 0.120 m, caster load 0.142 kg, drive-wheel load 0.364 kg. The file's comment: 120 × 142 / 506 = 33.676 mm. A new total weight alone does not move this |
| Inertia is a uniform brick | `beaconmind_car.urdf.xacro`: "box approximation", one uniform solid box. Not measured |
| No power-bank link and no cable | Those xacro files. The 2026-10-10 notes say no USB cable |

Ride height already in the URDF, from the 2026-10-10 readings (`car_geometry_extras.xacro`): gearbox bottom `lowest_body_h` 0.030 m; plate underside 0.046 m at the caster end and 0.043 m at the wing end, each ±2 mm. One new check is warranted because the right motor was replaced on 2026-10-23 with a different NULLLAB model (`CONTEXT.md` 2026-10-24). Leave those three URDF values if the new readings are still about 30 mm / 46 mm front / 43 mm rear within 2 mm. That check does not block writing a new mass.

### Power bank, known and unknown

`reference/hardware/car-build-notes.md`, "Decision 2026-10-20": a black rectangular two-port USB power bank, size measured by Xiaohui as 70 × 70 × 25 mm. The same table says port types and faces are not recorded, and mass, capacity, output rating, and where it sits are not recorded. No brand is named there. Do not add one.

`CONTEXT.md` (2026-10-24) already says that since 2026-10-20 the Pico runs from that bank and the motors from the AA pack. That is the wiring in use. It is not M3.T20. M3.T20 is the project's own power-path trial (jumper-out check, 30-minute auto-off, arena watchdog). It stays todo.

`assignments/assignment8/figures/item6-photo-overview.jpg` (Module 8 floor photo, 2026-10-25) shows USB leads leaving the robot. The bank body is outside the frame. No photo in the repo was found whose caption shows the bank fixed on the chassis.

### Measurements that block a URDF of the car as it is now

Ask Xiaohui. Do not invent the numbers. Do not write them into `car.json` or the xacro until he has measured them and M2.T4 runs. This is M1.T16, not a second copy of M1.T9. M1.T9's lens rows stay partial: one reading each on 2026-10-10, `lens_x_m` 0.12, `lens_y_m` 0.0, `lens_z_m` 0.075 (height above the floor) in `car.json`.

1. Whole-car mass with the bank fixed as it will stay, four cells in, camera on, and only the cables that stay on the car.
2. The same configuration on two scales, as on 2026-10-10: caster turned sideways on one scale, both drive wheels on the other. `com_x` is that split, not a third weighing.
3. Bank alone, grams.
4. Bank box in the axle frame. +x toward the camera. +y robot left when looking toward the camera. Rear and front faces, left and right faces, bottom and top above the floor, which face is down, how it is fixed. Which of 70 / 70 / 25 is the height is still unknown.
5. Front-most and side-most point of any plug or cable bend that stays on the car, and whether the bank sticks out past the camera board (138 mm ahead of the axle in the 2026-10-10 notes), the rear wing tip, the outside of the tyres, or the 0.140 m sweep.

Also ask, do not remeasure unless he says something moved: camera stand, BNO055, antenna, tyre set, cell type. The 2026-10-25 overview still shows a camera at the front of the plate and an upright antenna; that is not a confirmation that nothing moved. Lens numbers stay the 2026-10-10 single readings until he says the stand moved. URDF camera rpy stays 0, 0, 0 and is already labeled assumed until M1.T7 (`car_props.xacro`).

M2.T4 stays blocked. It already waits on `camera.json` and `car.json`. Regenerating the URDF also waits on the new mass, the two-scale split, and the bank box. Nothing was regenerated on 2026-10-29.

## 2. Pico firmware: K2 is the documented image; the EKF was on the host

### What is on the car, according to the docs

AGENTS.md §7.4 and `assignments/assignment8/review/FIRMWARE-REVIEW.md`: since 2026-10-25 the flashed image is Build K2, `~/fw_builds_m8/buildK2_bd46b95f.{uf2,elf}`. The one-flash fallback named there is J2, `~/fw_builds_m7/buildJ2_b4298742.uf2`. The 2026-10-24 `CONTEXT.md` entry names J1 (`buildJ1_9849874a`) as the one-flash fallback for J2. Chain as written: K2, then J2, then J1. The chip was not re-checked on 2026-10-29. Confirm it is still K2 before any port or flash.

K2 is the Module 8 port of J2 (`assignments/assignment8/module-8-sensor-fusion/firmware/pico_fusion/`). It is open-loop duty. It boots armed and speaks `/pico/cmd_vel`. Node `pico_fusion`. It publishes `sensor_msgs/Imu` on `/pico/imu/data` at 50 Hz (`pico_fusion.c` header). J2's `/pico/imu/heading` is a Float32 and cannot feed `ekf.yaml` `imu0`. That is why M3.T23's copy source is this tree, not Assignment 7 `pico_odometry/`.

`course-project/firmware/pico/` has no firmware sources. The only files found on 2026-10-29 are `beaconmind_fw/logic/.gitkeep` and `tests/.gitkeep`. The port has not been done. M3.T23 stays todo.

### What the Module 8 squares actually showed

The EKF ran on the host in `robot_localization` (`ekf_node`), not on the Pico. Report: `assignments/assignment8/Chen_Xiaohui_Module8_Sensor_Fusion_Lab.tex`, Results table. Tape averages for the counter-clockwise 1 m squares:

- Steered by the fused pose: 17.5 cm (runs r04–r06 tape columns 11.5, 32.0, 9.0 cm).
- Steered by the wheels: 6.5 cm (r10–r12: 9.0, 5.0, 5.5 cm).
- Orientation standard deviation tuned from 2.0° to 1.0° (t01–t03): mean 11.2 cm, still worse than 6.5 cm.

The report's cause is turn coast, not a bad IMU. The fused estimate measured the overshoot; `move_test.py` stopped the turn from the host pose, and the car coasted past. Run r07: two Wi-Fi stalls, about 17 cm of wheel motion never entered the fused distance, because only wheel speed is fused (report discussion; `evidence/floor-runs.csv` notes counts 1.176 m against fused 1.006 m).

Gazebo with a planted 1% left-encoder over-read did favor the EKF as an estimator (report items 2–3). On this car the left encoder's edge-mode scale already agreed with the compass within about 0.3% in pivots (`CONTEXT.md` 2026-10-24, floor runs `m32a`–`m32c`). That Gazebo failure mode was not this car's. A wheel-speed PID has never run on this Pico. The Module 7 PID discussion was Gazebo only. "EKF firmware beat PID" is not supported. PID and EKF do different jobs.

### Working design (the plan, not a flashed image)

Xiaohui asked for a design and said a hybrid or a new firmware is acceptable. No earlier decision in `CONTEXT.md` or the plan picked an on-Pico EKF. This is the design written into the plan on 2026-10-29. He can override the rejected on-Pico option.

- New BeaconMind firmware. K2 is the port source, not the image to keep. Contract C2 is different: bounded moves, boots disarmed, `/pico/arm`, `/estop`, heartbeat.
- Port K2's Wi-Fi supervisor, session supervisor, roaming, safety, deadman, and stall cut-off, and K2's IMU behaviour (`sensor_msgs/Imu` contents, 50 Hz, live uncertainty, BNO055 re-setup, K-specific client key). Build with `WIFI_SESSION_TOLERANCE=1` and `WIFI_ROAM_MODE=1` (`assignments/assignment8/tools/build-firmware.sh`: K2 is the roam variant; the CMake default of roam mode is 0). Never commit `wifi_config.h`. Never print the SSID, password, or a full BSSID.
- On the Pico, close moves locally. Distance stops on encoder counts. Turns and straight heading use the BNO055 yaw read on the Pico, with a coast lead measured on these motors. Do not stop a move on the host fused pose. That policy produced the 17.5 cm squares. During a stall the host filter goes blind and the Pico still has the gyro and the counts. The coast lead is not the PID and is not Module 8's `--coast-time 0.09` copied as if it had fixed the squares (that value was already applied, and the fused squares still ran long).
- Wheel speed: per-wheel feed-forward from a curve measured on these motors, then the instructor PID only if M3.T21 shows the motors can hold about 0.05 m/s per wheel. The current map cannot command that speed (2026-10-24: the lowest commandable duty moved each wheel about 0.17 m/s). Sim gains do not transfer. If the motors cannot hold about 0.05 m/s, the 45°/s limit is a C0 change, not an EKF change. The existing short-time fallback stays: feed-forward, count stops, and IMU-closed turns. The PID is not yet justified by a real-car run.
- Host `robot_localization` EKF is a pose estimate for logs and for the agent between moves. It is not in the turn-stop path. A small host adapter may build `sensor_msgs/Imu` and `/wheel/odom` from C2's `/pico/imu` and `/pico/wheels` so the Pico does not grow a fifth publisher (M3.T26). The move executor does not stop on `/odometry/filtered` (M3.T6).
- No on-Pico EKF. None was built or measured. Rejected because the measured failure was using the host pose as the stop signal. An on-Pico filter was never the thing that ran.

### Entity limits

Module 5 library, still the one K2 links: `assignments/assignment5/module-5-imu-tilt-control/micro-ros-builder/colcon.meta` sets `RMW_UXRCE_MAX_PUBLISHERS=3` and `RMW_UXRCE_MAX_SUBSCRIPTIONS=2`. `pico_fusion.c` says the same, and the Module 8 review counted 3/3 publishers and 2/2 subscriptions. Later builds did not raise the limit. M3.T14 is the task that rebuilds the library at 6 and 6. It stays todo. It remains the gate before extra Pico topics.

M3.T21 and M3.T22 stay todo. Module 8 streamed the camera on the floor (`assignments/assignment8/VISION-SETUP.md`) and did not run M3.T22's four arms of at least 600 s each.

## 3. Camera: firmware exists; calibration does not

`bm_cam-0.2` (`course-project/firmware/esp32cam/bm_cam_v02/`) is one image for the Module 8 lab and the project. It boots at VGA 640×480, JPEG quality 12. `/control` can select larger sizes and does not keep frame size across reboot. Flashed 2026-10-25. IP 192.168.5.49 (`CONTEXT.md` 2026-10-25; `VISION-SETUP.md`). `hmirror 1` was saved in flash. The flashed binary's source default was 0. A later source default of 1, sha `e95de293…` in that CONTEXT entry, was not flashed. The chip is the earlier binary, sha `e4d483a8…` in the same entry. `VISION-SETUP.md` records the saved mirror and the IP and does not repeat those hashes.

There is no `configs/camera.json`. There is no `evidence/M1/M1.T7/`. No checkerboard, distortion, or RMS. M1.T7 stays todo. A vision-language demo (Gemma or Claude describing a photo and driving toward a ball) is not a calibration. The Isaac render's 60° design and `fx=fy=1385.641` (`evidence/M1/M1.T5/checkpoint.md`) are not measurements of this lens. A 66° figure was not found as a stored measurement of this lens in the course-project files checked on 2026-10-29. The only lens pose numbers are the single 2026-10-10 ruler readings in `car.json`.

M1.T5 is done and is an AprilTag render spike. Its design intrinsics do not go into `camera.json`.

### Camera task status (2026-10-29)

| Task | Status | Why it stays there |
| --- | --- | --- |
| M1.T5 | done | Isaac version and tag spike. Not a chassis calibration |
| M1.T6 | in-progress | Shared JPEG firmware exists. VGA boot logged (`evidence/M1/M1.T6/bm_cam_v02/serial-boot-3.txt`, `BM_CAM READY`). `toolchain.txt` exists. Floor pictures passed on 2026-10-07 for bm_cam-0.1 at UXGA, hmirror 0, 192.168.4.24. That address is gone. Still open: level reading, bracket photos, named files (`first-frame.jpg`, `picture-quality.md`, `forward-*.jpg`, `probe-rate.txt`, `probe-freshness.txt`) against the step-13 bars. Desk UXGA timing misses ≥ 3 frames/s (`CONTEXT.md` 2026-10-25) |
| M1.T7 | todo | Not calibrated. Module 8's vision demo and bm_cam-0.2 are not this task |
| M1.T8 | todo | Tag pilot and `detector_noise.json` not done |
| M1.T9 | blocked | 2026-10-10 `car.json` exists. Lens rows are one reading each (partial). Bank measurements are M1.T16 |
| M1.T12 | todo | Camera ROS bridge not done |
| M1.T13 | todo | Live Pico in the project graph not done. Uses K2 without reflashing; chip not re-checked 2026-10-29 |
| M2.T6 | todo | Simulated perception |
| M2.T16 | todo | Isaac car and calibrated camera |
| M3.T9 | todo | Real-car bridge |
| M3.T10 | todo | Physical arena |
| M3.T11 | todo | Overhead webcam. Module 8's ESP32-CAM does not count |
| M3.T16 | todo | Real observation pipeline |
| M3.T17 | todo | Ground-truth accuracy |
| M3.T22 | todo | Four ≥ 600 s arms not run. Module 8's floor stream is not those arms |

### New plan work

- M1.T16 — mass, two-scale split, bank box, stick-out. M2.T4 waits on the blocking rows. Ride height is in the same task and does not by itself block the mass update.
- M1.T17 — settle capture size before M1.T7. The 2026-10-06 decision says UXGA quality 10. Module 8 never left VGA, and desk UXGA timing misses 3 frames/s. Intrinsics cannot be scaled from VGA to UXGA. Done when a dated choice names width, height, and JPEG quality after a floor-spot `camera_probe.py --n 100` at that setting, and the "must be 1600×1200" sentences are edited if the choice is not UXGA. Not a second calibration.
- M3.T25 — camera Wi-Fi rejoin while running, or a dated decision that a replug at the floor spot is the procedure. `bm_cam-0.2` picks a mesh node only at boot (`VISION-SETUP.md`, 2026-10-25). At the floor spot the camera was about −70 to −78 dBm with multi-second photos until a replug, then about −49 dBm. The Pico already rechecks. M3.T22 only measures the link. This task does not invent a firmware change.
- M3.T26 — host adapter from C2 `/pico/imu` and `/pico/wheels` into the EKF inputs, and the rule that the move executor does not stop on `/odometry/filtered`.
- Coast lead — extended inside M3.T6, not a second executor task.

M1.T7's "must be 1600×1200" sentences stay until M1.T17 chooses. This note does not choose UXGA or VGA.

## 4. Open questions (unanswered)

- Bank make and model if printed on the case. Which of 70 / 70 / 25 mm is the height. Where it is fixed. Bank mass. Whole-car mass. Two-scale split. Whether plugs or the bank stick out. Whether the camera stand, BNO055, antenna, tyres, or cell type changed when the bank was added.
- Confirm the chip is still K2 before any port or flash. Not re-checked on 2026-10-29.
- Capture size for calibration: UXGA quality 10 versus VGA quality 12, after the floor-spot probe. Not chosen here.
- For `camera.json`, whether `z_m` is a floor height or an axle height, and whether the angles are small mount angles or the full optical rotation. `CAMERA_CONVENTION_SETTLED` stays false.
- Whether the single 2026-10-10 lens readings are accepted until the stand is confirmed unmoved.
- Whether the saved `hmirror 1` is enough, or the unflashed binary whose source default is 1 should be flashed. Nothing was flashed on 2026-10-29.
- The host EKF as pose-only is the working design. Xiaohui can override it and ask for an on-Pico filter. Until he does, the plan is the hybrid above, not "EKF undecided".
