# Course Project Context

Last updated: 2026-10-29

**Project name: BeaconMind** (chosen 2026-09-28). "Beacon" for the AprilTags on the walls, "Mind" for
the language model that owns the pose belief, the beacon map and the SLAM decisions. Use this name in
course-facing work (posts, videos, proposal updates); "LLM as SLAM" and "the L2 agent" remain the
technical terms in the design documents. ("TagSLAM" was avoided: it is an existing tag-based SLAM system.)

This is the canonical handoff document for the EN.665.715 course project. Read it before
doing any course-project work and update it at the end of every course-project session.

## 2026-10-29 (night) — M2.T4: URDF updated to the M1.T16 car (660 g, power bank, cables in the footprint)

Branch `urdf/m1t16-measured-mass` (PR into `main`), made in a separate worktree because another agent was working
on `main`. Record, run logs and review: `evidence/M2/M2.T4/2026-10-29-m1t16/README.md`. This entry replaces the
"URDF still the 2026-10-10 car" statements of the earlier 2026-10-29 entries below, and settles open item (5) of
the pilot entry below (the sweep-radius / cable decision: Xiaohui kept the cables and the footprint follows them).

- **Model now:** total mass **0.660 kg** (`car.json` `mass_kg`, from the new CSV
  `evidence/M1/M1.T9/measurements-2026-10-29-with-m1t16-mass.csv` through `write_car_json.py`); two-scale split
  58 / 602 g; whole-car centre of mass **0.010545 m** ahead of the axle (Xiaohui's middle value, ±0.0018 m with the
  assumed 20 mm caster trail; 8.8–11.2 mm from the readings alone); chassis 0.575 kg; a geometry-only `power_bank`
  box on `chassis_link` (x −85 to −15 mm, y ±35 mm, 17–42 mm above the floor). Unchanged: ride height
  30 / 46 / 43 mm, lens pose, camera rpy 0, IMU pose, wheels, caster, `chassis_height_m`.
- **Footprint (after 23:45 CDT):** Xiaohui read the camera cable 40 mm past the old 138 mm front-most point
  (178 mm ahead of the axle) and chose to keep both cables as they are and have the footprint follow them:
  `front_overhang_m` **0.178 ± 0.0058 m**, `rear_overhang_m` **0.148 m** (the Pico cable), `chassis_length_m`
  0.326 m, `sweep_radius_m` **0.178281 m** (front-most corners (0.178, ±0.010): the cable taken as wide as the board
  and centred, an assumption). The URDF draws both cables as envelope boxes (ends measured, cross-sections ASSUMED);
  the ESP32-CAM board box still ends at 138 mm. Design-value proposals recomputed (`done_range_m` about 0.628 m, turn
  clearance about 0.228 m) in `evidence/M1/M1.T9/derived-dv-proposals.md`; `configs/dv.json` not edited.
- **Agent decisions for Xiaohui to accept:** the gearbox boxes' rear end (a photo ESTIMATE, ±6 mm) moved from −16 to
  −15 mm so they do not share volume with the measured bank front face (whether the parts touch is not measured);
  the front cable box has a collider, so the simulated car's first front wall contact matches `front_overhang_m`;
  the rear cable is visual only (a rigid box hanging toward the floor would be a false floor contact), so the
  simulated first rear wall contact is the bank's rear face, 63 mm short of the footprint and of the planned kinsim
  body.
- **Checks:** `beaconmind-ros:humble` (throwaway `--network none` container on a scratch copy): colcon **24 tests,
  0 errors, 0 failures, 1 skipped** (no `camera.json`); `check_urdf` OK; TF unchanged (`base_link →
  camera_optical_frame` 0.120, 0, 0.0415 m); `gz sdf` 14.9 converts with no warnings, 0.660 kg. Unmodified `main`
  had 2 broken URDF tests after the public-repo move (stale `car.json` hash in `car_props.xacro`; the extras CSV path
  pointed into the private repo); both fixed. `beaconmind` pytest 65 passed, 1 skipped.
- **Review:** one round, four lenses (source fidelity, math and geometry, data chain and tests, ROS and simulator),
  plus a two-lens round on the cable and footprint change (fixed: front-cable collider, ±5.8 mm through a row-specific
  writer exception, a separate board-front row, width checks tied to the board's measured width, two-assumption wording).
  No critical finding; every number confirmed. Fixed: a guard and a test that the split and the total are one
  weighing (a later total without a new split used to pass), bank guards (rounding, completeness, measured rear
  underside), a `body_box` size guard, an inertia test, and comment accuracy (inertia box, Isaac massless-link
  warnings, self-collision sources, private-repo labels, the CSV's AI line).
- **Notes for M2.T16 (Isaac twin), in the xacro comments:** the caster lifts at about 2.2 m/s² forward acceleration
  (7.15 m/s² for the old model), so ramp wheel commands and log pitch; the bank's rear-bottom edge is the first rear
  contact at about 11.8° nose-up, rear clearance 17 mm, and the bank collider needs a physics material; set
  self-collision off explicitly; importer 2.4.30 warns for the massless `base_link` and `camera_optical_frame`; with
  the caster sphere at the trailing contact the model's static caster load is 69.6 g against the 58 g weighed; the
  front cable collider needs a physics material too, and the front cable box will show at the bottom of the simulated
  camera image (compare the first rendered frame with a real one).
- **Open for Xiaohui:** the three agent decisions above; the cables' sideways position and width (the sweep radius
  assumes them) and a front photo of the camera cable's route; `configs/dv.json` against the recomputed proposals; the
  planned kinsim body's front corners (r = 0.193 m) lie outside the 0.178 m sweep radius (M2.T3); the bank alone (not
  weighed); re-weighing with the caster turned sideways would remove
  the ±1.8 mm. The plan's M2.T16 claim that `merge_fixed_joints = True` "would delete the camera frames" does not
  match importer 2.4.30 per the ROS reviewer (not re-run). The Spark's private-repo mirror predates the Module 6
  snapshot commit: `git pull` it before that lab is used again.
- **Status:** M2.T4 stays `blocked` (M1.T7 `camera.json`, M2.T3 `load_car`). M1.T16 stays `in-progress`.

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: this entry, the worktree and PR, the container and Gazebo runs,
and the review; the URDF/xacro edits were made by Claude Opus 5.5 at xhigh effort, as the 2026-10-06 rule asks.

## 2026-10-29 (night) — first-draft pilot run and report draft written

For the Class Project Report "First Draft with Experiments" (due 2026-11-03), Xiaohui delegated the work fully
("fully automate the process", 2026-10-29 22:37 CDT). Done this session:

- **Pilot code (public, tested):** `beaconmind/envs/kinsim_lite.py` (port of the Module 4 simulator with the M2.T3
  placeholder noise, seeded D3 worlds with 3 duplicated IDs, `odo_bias`), `harness/tools_d5.py`,
  `harness/anthropic_replay.py` (prompt caching, retries, budget cap, resume, fallback), `metrics/pilot.py` (C10.3
  map, C10.4 association, tool-call P/R/F1), `metrics/judge.py` (rubric and LLM judge with automated calibration),
  `tools/pilot_*.py`; `prompts/robot_system_prompt_v3.3.txt` published (Xiaohui's approval). `tests/test_pilot.py`
  24 passed (Mac and `beaconmind-ros`). Adversarial code review logged in `evidence/M4/M4.T11/CODE-REVIEW.md`.
- **Pilot run (Spark, 2026-10-29 22:53-23:32 CDT):** Claude Opus 5.5 in replay on dev seeds 1000-1004, kinsim only,
  two conditions: no drift (416 steps, US$31.19) and 2 % systematic odometry over-read (314 steps, US$23.92). All
  reports valid. Judges: GPT-6.1 Sol and Gemma 4 26B (Xiaohui's choice), calibrated without hand labels.
  Everything is in `evidence/M4/M4.T11/` (README, `pilot_summary.json`); raw logs stay in
  `data/pilot-20261029/` on the Spark.
- **Findings (pilot, not claims):** the agent executed the procedure almost exactly (same pose source on every step,
  same association decision for every detection, tool-call recall 1.00); its ATE tracked B2 within 0.5 cm; it lost
  to dead reckoning without drift and beat it on all 5 seeds with 2 % drift (mean -2.7 cm, below the 3 cm SESOI).
  A 100-seed baseline sweep puts the B2-over-B0 crossover between 0.5 and 1 % drift; B2's unimplemented branches stop
  1, 5 and 21 of 100 seeds at 2, 3 and 5 % drift.
- **Plan consequences:** odometry drift becomes a blocked factor and H1 moves to the 2 % block (report §IV-A);
  implement relocalization before larger drift; M2.T14 state correction still missing (counters reset on claimed
  fixes); the main study must test what the LLM adds beyond the procedure.
- **Report:** `report/Chen-Project-Report.tex` now has all eight sections; generated inputs `pilot_macros.tex`,
  `tab_pilot.tex`, `tab_judge.tex`, `fig_trace.tex`, `figures/fig_pilot.pdf`; hand-drafted `fig_architecture.tex`,
  `tab_tools.tex`. Build with `latexmk -pdf`. Plan rows M2.T3, M2.T7, M2.T8, M2.T10, M4.T11, M5.T1-T6 set to in-progress.
- **Judges:** evidence version 1 (tool results and report only) made Sol fail 21 of 730 notes, mostly for facts
  the agent had but the evidence lacked; version 2 (rules, observation, maps, full tool results) fails 1. Sol is the
  selected judge (all thresholds met); Gemma fails coverage (weighted kappa 0.41). Judge spend US$10.27.
- **Draft review:** one adversarial round (three reviewers), all findings verified and logged in
  `report/REVIEW-DRAFT.md`. PDF 11 pages, clean build.
- **Open for Xiaohui:** (1) commit and push the pilot code and evidence, or the report's repository link does not
  show it; (2) measure the camera tilt (inclinometer) so IV-B can state it; (3) the real arena floor; (4) the
  frontier-model sweep budget (the full K = 3 Opus design would cost about US$1,000); (5) the sweep-radius/cable
  decision from M1.T16.

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: wrote the pilot code, ran the pilot and the analysis, drafted
the report and this entry.

## 2026-10-29 (late) — M1.T16 measured: 660 g car, bank box, URDF may now be regenerated

Xiaohui measured the car as it is now. Evidence: `evidence/M1/M1.T16/measurements.md`, `confirm.md`, `photos/`.
M1.T16 is `in-progress` (bank alone, front camera cable and the sweep-radius decision are open).
This entry replaces the earlier "do not regenerate the URDF" rule: the mass and the bank are now measured.

- **Mass 0.660 kg** (was 0.506). Two-scale split 58 g front (caster) / 602 g drive wheels, caster not turned
  sideways. **Centre of mass 0.0105 m ahead of the axle** (middle value, ±0.0018 m; Xiaohui chose the middle value).
- **Power bank:** 70 × 70 × 25 mm lying flat under the plate at the breadboard end (the back), 3M double-sided
  tape. x −0.085 to −0.015 m, y centred (±0.035 m), z 0.017 to 0.042 m above the floor. It is now the lowest
  body point (17 mm). Model it as geometry only; its mass stays in the measured total (bank not weighed).
- **Ride height unchanged** (30 / 46 / 43 mm). Camera stand, BNO055, antenna, tyres, cells unchanged.
- **Open:** the rear Pico cable reaches 148 mm behind the axle, outside the 0.140 m sweep radius; the camera is
  now powered from the bank and its cable sticks out at the front (front-most point not measured). Do not change
  `sweep_radius_m` or the front overhang until Xiaohui settles these (reroute with right-angle plugs per
  AGENT-DESIGN §W, or enlarge the radius).
- **Next:** M2.T4 can update `car.json` (mass) and the URDF (mass, `com_x`, bank box) from these numbers.
  Earlier rule still in force: the URDF subagent is Claude Opus 5.5 at xhigh effort (2026-10-06 entry).

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: recorded Xiaohui's measurements, the checks and this entry.

## 2026-10-29 — status pass: K2, uncalibrated camera, URDF still the 2026-10-10 car

Full record: [`research/2026-10-29-urdf-firmware-camera-status.md`](research/2026-10-29-urdf-firmware-camera-status.md).
No URDF, `car.json`, firmware, or evidence file was changed. No new mass or intrinsics. The Pico chip was not re-read.
The 2026-10-24 "Hardware state now" bullets are history for that day; where they name Build J2 as the image on the car, this entry replaces them.

**Pico image the docs name.** Since 2026-10-25 the flashed image is Build K2, `~/fw_builds_m8/buildK2_bd46b95f` (AGENTS.md §7.4; `assignments/assignment8/review/FIRMWARE-REVIEW.md`). One-flash fallback is J2, `~/fw_builds_m7/buildJ2_b4298742`. J1 (`buildJ1_9849874a`) is the fallback the 2026-10-24 entry named for J2. K2 is open-loop duty, node `pico_fusion`, boots armed, `/pico/cmd_vel`, and publishes `sensor_msgs/Imu` on `/pico/imu/data` at 50 Hz. It is not the project firmware. `course-project/firmware/pico/` still has no sources (only `.gitkeep` files). Confirm the chip is still K2 before any port or flash.

**Firmware design (the plan, not a flashed image).** Xiaohui asked for a design and accepted a hybrid or a new firmware. Nothing already in `CONTEXT.md` or the plan had chosen an on-Pico EKF, so the plan now says:

- New BeaconMind firmware. K2 is the port source (M3.T23, still todo), not the image to keep. Contract C2 stays: bounded moves, boot disarmed, `/pico/arm`, `/estop`, heartbeat.
- Port K2's Wi-Fi supervisor, session supervisor, roaming, safety, deadman, stall cut-off, and K2's IMU behaviour. `WIFI_SESSION_TOLERANCE=1`, `WIFI_ROAM_MODE=1`. Never commit `wifi_config.h`.
- Close moves on the Pico: distance on encoder counts, turns and straight heading on the Pico's BNO055 yaw, with a coast lead measured on these motors (M3.T6). Do not stop a move on `/odometry/filtered`. Module 8's fused squares ended 17.5 cm from the start against 6.5 cm when steered by the wheels, because the host pose was the stop signal and the car coasted (`assignments/assignment8/Chen_Xiaohui_Module8_Sensor_Fusion_Lab.tex`).
- Wheel PID only if M3.T21 shows these motors can hold about 0.05 m/s. Until then, feed-forward plus count stops plus IMU-closed turns. If they cannot hold that speed, the 45°/s limit is a C0 change, not an EKF change. Sim gains do not transfer. The PID is not justified by a real-car run yet.
- Host `robot_localization` is a pose for logs and for the agent between moves (M3.T26). No on-Pico EKF: none was built, and the measured failure was the stop signal, not a missing on-Pico filter. Xiaohui can override that rejection.

**Camera.** `bm_cam-0.2` is flashed (2026-10-25), IP 192.168.5.49, boots VGA 640×480 quality 12. Saved `hmirror` is 1. The unflashed source default of 1 is sha `e95de293…`; the chip is `e4d483a8…` (`CONTEXT.md` entry of 2026-10-25). There is no `configs/camera.json` and no `evidence/M1/M1.T7/`. M1.T7 is not done. Module 8's vision demo is not a calibration. M1.T6 stays in-progress. The 2026-10-07 floor-picture pass was `bm_cam-0.1` at 192.168.4.24; that address is gone.

**URDF.** Still the 2026-10-10 car: total mass 0.506 kg, chassis leftover 0.421 kg, `com_x` from the two-scale split (caster 0.142 kg, drive wheels 0.364 kg, swivel x 0.120 m), inertia a uniform brick, no power-bank link. A new total weight does not fix the centre of mass. The bank in `reference/hardware/car-build-notes.md` (2026-10-20) is a black two-port block, 70 × 70 × 25 mm. Mass, capacity, output rating, port types, and mounting pose are unrecorded. No brand. The Module 8 overview photo shows USB leads leaving the robot; the bank body is outside the frame. M3.T20 stays todo: the split in use is not that trial.

**Not done, and not marked done.** M1.T7, M1.T6 (in-progress), M1.T8, M1.T9 (blocked; lens rows partial), M1.T12, M1.T13, M2.T4 (blocked), M2.T6, M2.T16, M3.T9, M3.T10, M3.T11, M3.T14, M3.T16, M3.T17, M3.T20, M3.T21, M3.T22, M3.T23. New and still todo: M1.T16 (mass and bank box), M1.T17 (capture size), M3.T25 (camera rejoin or a replug decision), M3.T26 (host EKF adapter). The coast lead is an addition to M3.T6, which stays todo.

**Open questions for Xiaohui.** Do not treat this entry as answering them.

- Bank make and model if printed; which of 70 / 70 / 25 mm is the height; where it is fixed; bank mass; whole-car mass; two-scale split; whether plugs or the bank stick out; whether the camera stand, BNO055, antenna, tyres, or cell type changed when the bank was added.
- Confirm the chip is still K2 before any port or flash.
- Capture size: UXGA quality 10 versus VGA quality 12, after a floor-spot `camera_probe.py --n 100`. Not chosen.
- For `camera.json`: `z_m` as floor height or axle height, and small mount angles or the full optical rotation. `CAMERA_CONVENTION_SETTLED` stays false.
- Whether the single 2026-10-10 lens readings (0.12 m forward, 0.0 m lateral, 0.075 m above the floor) are accepted until the stand is confirmed unmoved.
- Whether saved `hmirror` 1 is enough, or the unflashed binary whose source default is 1 should be flashed. Do not flash it from this note.
- Host EKF as pose-only is the working design. He can override the on-Pico option.

**Next.** Xiaohui: the open questions above, especially the bank measurements (M1.T16) and the capture-size probe (M1.T17), and a yes that the chip is still K2 before M3.T23. Do not regenerate the URDF. Do not flash.

AI-assisted: Grok 4.7 via Cursor, 2026-10-29: this status pass (this entry, the research note, and the plan status updates). Xiaohui Chen remains accountable for what he submits.

## 2026-10-25 — camera firmware bm_cam-0.2 built (one image for the Module 8 lab and the project); not flashed

**⚠ Flashing rule (read before touching the camera):** this ESP32-CAM boots only with the DOUT-mode bootloader at
0x1000 (`evidence/M1/M1.T6/dout-write.txt`; the DIO bootloader boot-loops, `serial-boot-dio-rst.txt`). Never use
`arduino-cli upload`, PlatformIO Upload (the Module 8 guide's Step 9.3) or a merged image. `flash.sh` now refuses.
Flash the app only: on the Spark, `bash firmware/esp32cam/build.sh bm_cam_v02`, Xiaohui holds IO0 and taps RST,
`bash firmware/esp32cam/flash_app.sh bm_cam_v02` (writes 0x10000 only, after checking the partition table's sha256
`aaae2888…`), then Xiaohui taps RST. Also in `reference/hardware/esp32cam-notes.md` §8 and AGENTS.md §7.4.

- **Why:** Xiaohui chose one firmware for the Module 8 camera-vision discussion (instructor lab guide 2, which expects
  the instructor's VGA sketch) and the project (M1.T6 contract). Research and the requirement sweep: the camera-vision
  sources are archived in `assignments/assignment8/sources/`, and the instructor's pristine firmware is in
  `assignments/assignment8/guide-original/firmware/esp32cam_camera/`.
- **What:** `firmware/esp32cam/bm_cam_v02/bm_cam_v02.ino` (fw `bm_cam-0.2`) = the instructor's sketch plus bm_cam-0.1's
  project contract. It boots at **VGA q12** (2 × 480,000 B PSRAM buffers, sized for UXGA). `/control` switches among
  4:3 sizes up to UXGA, quality 10-63 and vflip/hmirror; the frame size is not kept across a reboot, and
  `save=1` stores the orientation in NVS. Endpoints `/`, `/capture` (`?flash=1`), `/status`, `/led` (30 s auto-off),
  `/control`. `/capture` serves only a frame whose readout started after the request (driver `fb->timestamp`) and
  whose JPEG SOF size equals the mode. Headers `X-BM-Seq`, `X-BM-Capture-Us`, `X-BM-Frame-Us`, `X-BM-Uptime-Ms`,
  `X-BM-Width`, `X-BM-Height`. Serial: `BM_CAM READY ip=… rssi=… fw=bm_cam-0.2` and the guide's `Photo URL: …` every
  10 s. Wi-Fi: all-channel scan with the strongest node, power save off, the core's auto-reconnect, and a forced retry
  after 20 s down. The SSID is never printed. VFLIP default 0 (bm_cam-0.1 frames were upright with 0); mirroring
  is still to be tested with printed text on the preview page.
- **The 2026-10-06 project mode decision (UXGA q10) is unchanged.** Project tools must set it with
  `/control?framesize=uxga&quality=10` and check `X-BM-Width/Height`; `tools/camera_probe.py --mode uxga --quality 10`
  does (new flags, plus a `size_mismatch` count). The plan has dated notes in M1.T6 (box under "Why"; steps 9, 11, 12
  and 14; the step 14 `PATH` variable bug fixed), M1.T7 and M1.T12.
- **Checks run:** compiled on the Spark (`arduino-cli --warnings all`, FQBN `esp32:esp32:esp32cam:FlashFreq=40,FlashMode=dio`)
  with **0 warnings**; the build on the chip (with the merged-frame fix) is 1,026,585 B (32 %), app sha256 `e4d483a8…`
  (the first flashed build, without the fix, was `cf660bc1…`). The app image is valid (esptool image-info), and the partition table
  is byte-identical to the chip's. Host tests `firmware/esp32cam/tests/run_host_tests.sh` pass as C and C++ on the Mac
  and the Spark (JPEG size reader on two real UXGA frames, VGA/progressive SVGA/EXIF QVGA frames and a 700-byte
  truncation sweep; query and number parsers). `beaconmind` pytest 65 passed. `camera_probe.py` was run end to end
  against a local fake of the HTTP contract.
- **Review:** a 5-lens adversarial review with per-lens refutation confirmed 23 findings (0 critical, 2 major
  documentation findings, the rest minor or nits). The firmware fixes: LED auto-off race, rollback of a failed `/control`,
  strict query parsing, a bounded wait (`esp_camera_available_frames`, 1.5 s), split serial lines, a "Forget saved
  orientation" button, the partition guard pinned by sha256, and comment and provenance corrections. The two majors
  were the DOUT rule missing from the plan and docs, and project tools not setting the mode; both are now documented,
  and the probe sets the mode. An independent check of the fixes then confirmed them, and its 1 new minor finding (an
  empty query piece such as `a=1&&save=1` was allowed but its keys were missed) and 11 nits were fixed too: `/led`
  key check, a `fresh_timeouts` counter in `/status`, a `BM_CAM MODE` serial line every 10 s, a flash hold that does
  not restart the LED's auto-off timer, ordered rollback with clearer messages, and preview-page fixes. Not run on hardware: frame rate, freshness, FB-OVF at 480 KB buffers, the mirror
  test, and the Wi-Fi behaviour on the mesh.
- **Flashed the same evening (camera on the Spark's USB, Xiaohui doing IO0+RST and RST):** `flash_app.sh bm_cam_v02`
  twice, both `Hash of data verified`. The chip runs **bm_cam-0.2** at **192.168.5.49** (a new DHCP address; .24 is gone).
  The full boot log `evidence/M1/M1.T6/bm_cam_v02/serial-boot-3.txt` shows the DOUT bootloader, `Camera ready: OV3660,
  640 x 480 JPEG.`, the READY line every 10 s, no FB-OVF and no SSID. `/status` and three captures (640x480, all
  `X-BM-*` headers) are in the same folder. Malformed queries return 400. The size switch was checked both ways
  (VGA→UXGA→VGA, 0 size discards).
- **Found on the hardware: merged frames.** The driver sometimes leaves 2-6 frames in one buffer and trims it at the
  last EOI (5 of 40 VGA photos; a 126 KB buffer held a 19 KB image). This is very likely the old FB-OVF mystery: at
  SVGA with 96 KB buffers, merges overflowed. The second build sends only the first image (`bm_jpeg_first_image_len`,
  host-tested, including on the real merged files) and counts the rest (`merged_buffers` 21 of 60; no served photo
  held more than one image). The cause (a missed frame end) is open, and merged buffers still cost latency.
- **First rate data (desk, −48 to −59 dBm, not the floor spot):** VGA q12 request median 0.11-0.14 s, max 0.42 s; UXGA q10
  median 0.48 s, max 1.9 s, 219 KB per frame. At UXGA, the step 13 bar of ≥ 3 frames/s looks out of reach. Run the
  real `camera_probe.py --n 100` at the floor spot before the mode decision.
- **Mirror test done (M1.T6 step 12, phone showing "ABC 123", about 30 cm):** with hmirror 0 the text came out
  reversed, though upright. With `/control?hmirror=1` it read normally, so it was saved (`/control?save=1`), and after an
  RST `/status` still showed `vflip 0, hmirror 1, orientation saved` (uptime 11 s). Evidence (text-only crops; the full
  photos showed part of a person and were not kept): `assignments/assignment8/evidence/ball-test-2026-10-25/`. So
  the earlier "mirroring hint" (camera-quality.md) was right, and every bearing from older frames had the wrong sign.
  The source default is now `CAMERA_HMIRROR 1` (built with 0 warnings, sha `e95de293…`, **not flashed**: the chip runs
  `e4d483a8…`, built with 0, and its saved NVS value 1 gives the same picture). Redo the test if the module is remounted.
- **State:** `bm_cam/build/` on the Spark keeps the 0.1 app (`bm_cam.ino.bin`, sha256 `f724e0c4…`) as the one-flash
  fallback. The camera's USB stayed in the Spark. M1.T6 stays in-progress (the step 13 probes and the named
  acceptance files are still open).
- **Next:** `camera_probe.py --n 100` at the boot VGA and with `--mode uxga --quality 10` at the floor spot, plus
  the freshness test (M1.T6 step 13).
- **Not committed.**

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-10-25: researched the requirements, wrote bm_cam-0.2, its host test,
`flash_app.sh`, the `build.sh`/`flash.sh`/`camera_probe.py` changes and the plan and doc notes, ran the builds, tests
and the review, and wrote this entry.

## 2026-10-24 — car firmware lessons; plan revised

Full record: [`research/2026-10-24-car-firmware-lessons-and-pid.md`](research/2026-10-24-car-firmware-lessons-and-pid.md)
(F1–F11 below are its facts). **Read it before M3.T2, T3, T4, T6, T7, T14 and the four new tasks M3.T21–T24.** No
project task was run: the car work since 2026-10-19 was Assignment 7 (bench log
`assignments/assignment7/evidence/new-motor-bench-2026-10-20.md`), and this entry records what it changed for the
project. Line numbers are as of 2026-10-24.

**Hardware state now** (replaces the matching bullets of "Hardware state (as of 2026-10-05)" and of the 2026-10-11 entry). **Superseded for the flashed image on 2026-10-29:** the docs name Build K2, not J2. Read the 2026-10-29 entry. The bullets below are what was true on 2026-10-24.

- **Firmware on 2026-10-24: Assignment 7 Build J2** (`~/fw_builds_m7/buildJ2_b4298742.{uf2,elf}` on the Spark), flashed 2026-10-24. Not the image the docs name after 2026-10-25 (that is K2; see 2026-10-29).
  after five review rounds; it passed its T1 boot check, a 3-min floor check and a 20-min floor soak (bench log, the
  "Floor spot, J2" entry), and drove the first floor runs of the current motors (`m32a`-`m32c`). J1
  (`buildJ1_9849874a`) is the one-flash fallback. Both are the instructor's Module 7 guide code plus this car's Wi-Fi,
  session and safety layers (F1); J2 adds the chip's emergency roaming and the host's node choice. Node
  `pico_odometry`; best-effort `/pico/cmd_vel` in; `/pico/wheel_ticks`, `/pico/imu/heading`, `/pico/drive/status`
  out. Open loop: one duty map for both wheels, linear cap 0.30 m/s (`drive_control.c:37`, twice the project's 0.15),
  500 ms command timeout, a 600 ms deadman in a 10 ms timer interrupt that drops STBY, a stall cut-off. It is **not**
  the project firmware (no `/pico/arm`, `/estop`, latch, moves or boot id; C2), and it **boots armed** after a normal
  power-up (F11). Hardware watchdog 2 s driving / 8 s parked / 16 s while connecting (`safety.h:45-51`). The Module 6
  drive image of the 2026-10-11 entry is no longer on the Pico.
- **First floor runs of the current motors (2026-10-24, F6):** the left encoder's scale agrees with the compass within
  0.3 %; the car veers right 4-5° per 34 cm forward (right wheel 2.5-3 % slower) and goes straight in reverse; a
  commanded 45°/s turn ran at about 160°/s because the lowest duty this firmware sends moves each wheel about
  0.17 m/s. Both are inputs to M3.T21 (the wheel PID and the low-speed hold).
- **Agent restarts under J1:** quiet from 1.5 s of agent silence, motors stopped and disarmed from 3 s (re-arm
  needed), session rebuilt only after 20 s, on an IP change or when the agent is proven restarted
  (`pico_odometry.c:207,214,215`). On the bench a `docker restart` of the agent was rebuilt 7.7 s after the agent came
  back, with no reboot and no Wi-Fi rejoin (bench log, J1 T2b). So the 2026-10-05 bullet's "reboot the Pico after the
  agent restarts" does not apply to J1. The Assignment 7 agent is the `m7-micro-ros-agent` container (bench log stage 0).
- **Motors:** the left was replaced on 2026-10-22 (same blue 1:90 TT model). **Right #3** is a different model, a blue
  NULLLAB 1:90 TT "Low Noise & Hybrid Gear", fitted 2026-10-23 on the same cable, rows 25–26 and driver channel A. It is
  **lifted-tested only** (`m30a`: every wheel turned as commanded; at the same duty the right is 1–5 % slower than the
  left; both lose 7–8 % when driven together on the shared AA pack); its one floor run (`m31a`, Build I) stopped before
  any motion on a session rebuild. 3 of the 4 original-model motors failed within days (F6). Driver: the spare
  TB6612FNG board (HW-166) since 2026-10-19 (`reference/hardware/car-build-notes.md`).
- **Sides: channel A drives the RIGHT wheel** (IMU-verified 2026-10-11). **Encoders: left = `GP16`/`GP17`, right =
  `GP18`/`GP19`** (`encoders.h:9-15`), the opposite of the 2026-10-05 bullet and of the plan's old pin table. Nominal
  4,320 counts per wheel turn. The left encoder's two channels are not a clean quadrature pair, so the firmware counts
  its edges (**edge mode**, `encoders.h:20-30`); in floor pivots its scale agrees with the compass within about 0.3 %
  (`m32a`, 2026-10-24), re-checked with the project firmware in M3.T24. The right decodes plain x4 (about 1.6 % lost
  at duty 0.96).
- **PWM: the instructor's 1.2 kHz** (`tb6612.c:37-48`). A 20 kHz trial on 2026-10-17 cut Wi-Fi losses in pivots but
  was reverted (one wheel stuck in pivots, old motors, sagging pack); M3.T4 re-tests it before measuring the duty curve.
- **Power:** since 2026-10-20 the Pico runs from a two-port USB power bank on the car (the camera is meant for its
  second port but was unplugged for the Wi-Fi tests and has not streamed from the car); the AA pack (Energizer L91,
  fresh 2026-10-21) runs the motors only; the green AMS1117 wire is out (`car-build-notes.md`, "Decision 2026-10-20"
  and "Decision 2026-10-21"). The project's own power-bank trial is still M3.T20. **The STBY pull-down (S5) is still
  NOT fitted** (M3.T1); it protects the Assignment 7 firmware too, which can reboot itself with the battery on (F11).
  Measure the pack before each use (S8).
- **No hand-turning of the wheels since 2026-10-23 (Xiaohui).** Counts per turn and encoder signs come from powered
  runs (M3.T3: wheels up, a tape flag filmed in slow motion; M3.T24: the IMU on the floor).
- **The Pico:** not CPU-bound (about 12 % of one core; the second core unused), but its main loop blocks 0.6–2.2 s on
  the radio (F3). The project's PID, heartbeat watchdog and move executor therefore run on core 1 or a 10 ms
  repeating-timer interrupt, never only in the main loop.

**Wi-Fi, in two lines** (F2; `assignments/assignment7/evidence/wifi-survey-2026-10-23.md`; `floor_logs/ab_1024/`):
- The house mesh is 6 eero nodes, every 2.4 GHz radio on channel 6 (about 55 % busy); at the car's floor spot the
  network itself stalls for seconds (Spark→Pico ping p90 485–1845 ms, p99 2.5–11 s on 2026-10-23), and no firmware removes that.
- On J1 at the spot (2026-10-24, parked, listen only, no camera) the longest telemetry gap was 0.29 s and 1.10 s in two
  3-min runs and 1.28 s in a 20-min soak, never longer than the ping's own pause; the link **with the camera streaming
  and the wheels running** is not measured (M3.T22), and it decides whether a 500 ms watchdog and a 0.2 s STOP are reachable.

**Decisions by Xiaohui (2026-10-24, recorded in the research note):**
- (a) **The project may reuse the instructor's code**: the Module 5/6/7 guide firmware (`tb6612.c`, `encoders.c`,
  `bno055.c`, `picow_udp_transport.c`, `CMakeLists.txt`, `lwipopts.h`) and the Module 7 PID's `pid.c` /
  `wheel_control.c`, which exist only at `~/Downloads/pid-source-files.html` on the Mac until M3.T4 step 0 archives
  them. Reused code keeps a comment naming the instructor file; every part Claude changed keeps its AI disclosure.
  Upstream, tutorial and internet code is still never pasted (README L11).
- (b) Revise the plan from this research and add tasks such as PID tuning (below).
- (c) No hand-turning of the wheels (above).

**Plan changes made on 2026-10-24** (`plan/README.md`, `plan/M3-real-car.md`; list in the research note §5):
- **New tasks:** **M3.T21** Wheel-speed PID tuning on the stand: step responses, low-speed hold, battery range (needs
  M3.T4, M3.T1); **M3.T22** Link baseline at the floor spot with the camera streaming (Assignment 7 firmware as the
  instrument) (needs M1.T1; the camera arms need M1.T6 and the drive arms M3.T1); **M3.T23** Port the Assignment 7 link and safety layer into
  the project firmware (needs M3.T14; M3.T2 now needs it); **M3.T24** Floor re-tune of the wheel PID and the left
  encoder's scale (after the wheels-down gate) (needs M3.T7, M3.T20 and M3.T21; must finish before M3.T8).
- **New open decision OD21** (README §3.5): does a `link_lost` stop latch the episode on this link? Default: keep C5's
  auto-latch and set `watchdog_ms` from the M3.T22/M3.T7 data. Settled by Xiaohui after M3.T22.
- **Changed:** README L11 (the reuse rule), §7 S11 (the firmware's session supervisor rebuilds its session after an
  agent restart; reboot the Pico by hand only if `/bm_pico` has not reappeared within 30 s), §3.2–§3.4 and §9 (the new
  tasks); M3 §0.6 facts (encoder sides, motors, edge mode, 1.2 kHz, Build J1); M3.T2 (the 2 / 8 / 16 s watchdog
  pattern and the supervisor; control loops off the main loop); M3.T3 (powered counts per turn); M3.T4 (step 0 archives
  the instructor's PID; a 1.2 vs 20 kHz A/B before the curve; the PID at 100 Hz in the control context; the full tuning
  moved to M3.T21); M3.T5, T6, T14 (reuse wording); M3.T7 G0 takes M3.T22's baseline.
- **Suggested order** (research note §4): J2's floor A/B (Assignment 7) → M3.T1 → M3.T22 → M3.T14, M3.T23, M3.T2 →
  M3.T3, M3.T4, M3.T21, M3.T5, M3.T6, M3.T7 → M3.T24 → M3.T8. If time runs short: safety and the move executor
  first, then the IMU heading loop, then the wheel PID (§3).
- **`AGENTS.md` updated (Xiaohui's request, 2026-10-24):** §5 has the instructor-code exception (decision (a)) and a
  new rule, "Car firmware for labs — always carry the Wi-Fi fix": every later lab's Pico firmware is ported onto the
  current Build J2 instead of flashing the instructor's main as given; §2 points to the exception; §7.4 then recorded J2 on
  the car and that J1 and later rebuild their session after an agent restart. **As of 2026-10-29, AGENTS.md §7.4 records K2 (`buildK2_bd46b95f`) since 2026-10-25, with J2 as the one-flash fallback.** This paragraph is the 2026-10-24 edit, not the current image.

**Left running / not done.** No course-project task was run. Left running on the Spark: the Assignment 7 containers
`m7-micro-ros-agent` and `m7-gazebo` (the car's agent; `m7-gazebo` also holds UDP 8888, so stop both, with Xiaohui's
OK, before any project agent starts). The car that evening: Build J2 on the power bank, disarmed until the arm marker. The image name was superseded on 2026-10-29 (K2; chip not re-checked that day).
**Committed and pushed on 2026-10-24** together with the Assignment 7 Builds H to J2 work (see `git log`).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-10-24: wrote this entry from the research note, the Assignment 7
bench log, the Wi-Fi survey, `car-build-notes.md` and the firmware sources. The car work and the decisions are Xiaohui Chen's.

## 2026-10-06 — M1.T1 scaffolding done

M1.T1 is done. Evidence is `course-project/evidence/M1/M1.T1/`.

- **Venvs.** Mac: `course-project/.venv` (Python 3.13.7). Spark host: `~/.venvs/beaconmind` (Python 3.12.3).
- **Sync.** The Spark mirror of `course-project/` was updated with `course-project/tools/sync_to_spark.sh`. Spark-side evidence was pulled back in this session with `course-project/tools/pull_evidence.sh M1 M1.T1`. Pull again before the next Mac→Spark sync if the Spark has written anything newer.
- **gtsam.** `gtsam==4.3.0` is installed in the Spark cp312 venv (`pip-freeze-spark.txt` also lists `evo==1.37.1` and `statsmodels==0.15.0`). `import gtsam` succeeds. The module has no `__version__` attribute, so the task import line printed `gtsam imported`. `importlib.metadata.version("gtsam")` is `4.3.0`.
- **Pins on the Mac** in `beaconmind/pyproject.toml`: `pytest==9.1.1`, `jsonschema==4.26.0`, `gtsam==4.3.0`, `numpy==2.5.3`, `scipy==1.18.1`, `statsmodels==0.15.0`, `evo==1.37.1`, `matplotlib==3.11.2`. `providers` is still a lower bound. The Spark copy of `pyproject.toml` is still the pre-pin lower bounds, because the pins were written after the sync. The installed Spark packages are the pinned versions.
- **Tests.** `pytest-mac.txt` and `pytest-spark.txt` both end with `5 passed in 0.01s`.
- **Host C compiler present; firmware logic tests run on the Spark host.** `cc (Ubuntu 11.5.0-1ubuntu1~24.04.1) 11.5.0`, GNU Make 4.3 (`env-spark.txt`).
- **Left running.** Nothing from this task. tmux session `bm-m1t1` has finished. `rosa-ros2` and `vllm-rosa` are still exited. vLLM is not serving. No serial devices. Ethernet `192.168.5.1/22` is still on `enP7s7`. Scratch logs on the Spark home directory: `~/bm-m1t1-install.sh`, `~/bm-m1t1-install.log`, `~/bm-m1t1-pip.log`. Spark data directories exist under `course-project/data/` and are git-ignored. There is no `course-project/data/` on the Mac.
- **Git HEADs differ.** The editable-install lines record each clone's HEAD: Mac `c6abbd7`, Spark `82b0293`. The tar sync does not move either HEAD.
- **Next.** M1.T2 was not started.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, wrote the BeaconMind package skeleton, pytest scaffolding, sync and environment scripts, `pyproject.toml`, the `.gitignore` block, and this entry.

## 2026-10-05 — M0 closed: course fit settled

Confirmed by Xiaohui on 2026-10-05:

- **No Course Project Description exists or will arrive.** The documents in this folder are the
  full specification.
- **Individual project.** Xiaohui Chen is the sole participant and owner. The syllabus's
  Customer/Seller team structure does not apply.
- **The instructor accepted the direction change** to BeaconMind. The revised proposal and the
  Related Works & References PDF were both submitted to Canvas and received **full credit**.
- **Final deadline: 2026-12-13.** No dated schedule is kept, because Xiaohui decides when each
  milestone is carried out.
- **The task-level implementation plan is [`plan/`](plan/README.md):** milestones M1–M6, each
  broken into tasks with context, steps, deliverables and tests. Use it as the starting point for any
  implementation session.

## Direction chosen 2026-09-27 — history (feasibility and acceptance now settled)

Xiaohui chose to make the project **"LLM as SLAM"**: the car explores an **unknown** arena,
printed AprilTags act as **beacons**, and a language model keeps the pose belief and beacon
map, recognises revisits and chooses where to explore. The project **benchmarks many models**
(GPT-6 Astra/Sol/Luna, Claude Opus 5.5 and Fable 5.1, open-weight models on the Spark, and
navigation foundation models) in **Isaac Sim and the real world**. A 10-agent research workflow,
with every claim adversarially verified, found it **feasible with conditions, and novel at its core** (no
precedent for an LLM owning the SLAM decisions). The conditions are: a beacon map in a clear arena (no range sensor); stop-observe-think-act; detector
output rather than pixels for text models; aliased-beacon conditions; a classical GTSAM
reference. A three-lens adversarial review of the approach document followed; its 29 distinct findings
were confirmed and fixed.

- Approach: [`APPROACH-LLM-SLAM.md`](APPROACH-LLM-SLAM.md) — idea, feasibility verdict, the
  L0–L3 responsibility ladder, benchmark, model roster, cost, workstreams, risks.
- Evidence: [`research/2026-09-27-llm-slam-feasibility/`](research/2026-09-27-llm-slam-feasibility/README.md).
- **Status:** chosen by Xiaohui on 2026-09-27, contingent on feasibility, which the research
  supports with conditions. Still open:
  - ~~the revised D1 specifics for the Module 4 prompt assignment~~ — settled: D1–D10 were
    decided by Claude under Xiaohui's delegation in [`AGENT-DESIGN.md`](AGENT-DESIGN.md), now
    **v3.3**. The Module 4 prompt is built on it; Xiaohui's review was done on 2026-09-27;
  - ~~whether the instructor must accept a change from the 2026-09-14 proposal~~ — accepted
    (2026-10-05 note above);
  - ~~the team/role structure~~ — individual project (2026-10-05 note above).

  The known-map design below is kept as history.

## 2026-10-01 proposal revision (instructor feedback)

The 2026-09-14 submitted quad chart was the known-route "Landmark-Grounded Natural-Language
Mission Rover". The instructor accepted the technical direction and the listed outcomes /
conditions / metrics / targets, and asked for two revisions before updating the grade:

1. **Stronger problem motivation**, with evidence from prior work on language-conditioned
   planning, closed-loop verification, and embodied-agent failure modes — not an assumed gap.
2. **How the already-listed metrics will be applied**: how map-frame pose error is measured,
   how mission success is decided, and how unsafe or invalid actions are rejected.

The working deck is now **BeaconMind** (`Chen-Project-Proposal.pptx`, two slides):

- Slide 1 is still the instructor quad chart (problem, questions, approach/tools, system
  diagram, expected outcomes, participant). The problem statement now cites [1–14]; the
  outcomes quadrant now states how pose error, success, and refusal are applied, with
  targets scoped to replay vs. closed-loop vs. the car.
- Slide 2 is a backup "Two Content" slide: the cited finding for each source, and the
  measurement protocol. The official prompt asked for one slide; slide 1 stands alone if
  Canvas should receive only the quad chart.

Generator: `build_proposal.py`. Talk track: `proposal-talk-track.md`. Validator:
`validate_proposal.sh` (instructor template, not the canonical JHU theme). Fit check:
`check_render_fit.py` on the LibreOffice PDF.

Implementation that the slide may claim as done (the rest is planned):

- car wired and rails measured;
- Pico 2 W micro-ROS over Wi-Fi, instructor LED image only (no motor/encoder/IMU firmware);
- L2 geometry tools and rule-level simulator;
- RobotSystemPrompts v3.3, 80-run smoke test vs. a control
  (`assignments/assignment4/system-prompt/`);
- MCP `gate_detection` + episodic memory under ROSA, 19 tests pass
  (`discussions/module4/`).

Open items that still block a full project claim (instructor acceptance and the team question
were settled on 2026-10-05): Isaac Sim twin; Pico move firmware; camera stood upright and
calibrated.

## 2026-10-01 class project report — Related Works & References draft

The final report is an IEEE conference paper built from the instructor's `Class Project
Template.zip` (`conference_101719.tex`, IEEEtran class, `mybibfile.bib`). It lives in
[`report/`](report/REVIEW.md) and is built locally, not on Overleaf:
`cd course-project/report && latexmk -pdf Chen-Project-Report.tex`.

- **This milestone (10 points):** only Section II (Related Works) and the References are
  written; every other section is a one-line placeholder. Submit `report/Chen-Project-Report.pdf`
  (4 pages) to Canvas. **Submitted; full credit (confirmed 2026-10-05).** No due date was found on the assignment page or in the Module 5 lecture
  notes; check Canvas.
- **Content:** four strands (language-conditioned planning and closed-loop agents; language
  models in navigation, mapping and SLAM; limits of LLM spatial reasoning and the case for tools;
  fiducial SLAM and evaluation practice), each ending with how BeaconMind differs, plus Table I
  (who supplies pose and map in seven prior systems versus BeaconMind). 27 references, each
  checked against the paper and a publisher or arXiv record. PDFs are in `report/sources/`
  (git-ignored).
- **Review:** three adversarial rounds, logged in `report/REVIEW.md`. Round 1 caught that the
  draft described BeaconMind from `APPROACH-LLM-SLAM.md` where `AGENT-DESIGN.md` v3.3 supersedes
  it. **Describe BeaconMind from `AGENT-DESIGN.md` first.**
- **For Xiaohui to confirm** (the report words these as "proposed"): the refusal request suite,
  the coded per-step baseline (B2), true association for the GTSAM reference when IDs repeat,
  and L1/L3 as stretch arms. They are still only in `proposal-talk-track.md`.
- **Later sections** go into the same `.tex`. Section II is long for a final paper (about two
  pages) and can be cut when the other sections need the space.
- Committed in `37454f3`.

**Behavioural evidence (2026-09-27, Module 4 smoke tests; `assignments/assignment4/system-prompt/evidence/smoke-test.md`).**
- **Round 1** (the first final prompt, 16k window): 1 of 12 runs passed. With thinking off, the
  model skipped the tools; with thinking on, it mislabelled the duplicated tag.
- **Xiaohui's decision (v3.3):** add a duplicated-tag-id example (Example 3, with a simulated
  history) and raise the prompt budget instead of cutting rules (Claude set 4,500). The final is
  4,352 tokens.
- **Review fixes (five adversarial rounds):** a scan-bookkeeping rule (E2/E4 `scan_added`), a
  corrected smoke harness, and scenarios taken from a simulated history (`tools/backstory_sim.py`,
  `tools/build_scenarios.py`).
- **Round 2** (control against v3.3; 131,072 window; model-card sampling; 80 runs):
  - Thinking on: all checks passed in 8/20 against 3/20, and the duplicate was labelled correctly
    in 11/15 against 5/15. Neither is significant at K = 5 (p = 0.16 and 0.07).
  - Refusals did not improve.
  - Thinking off: 0/20 for both prompts, and v3.3 never called a tool (p = 0.02).
- **Design findings for W3:**
  - Thinking mode (or a stronger model) looks necessary for the L2 agent.
  - Raise K.
  - Loop closure practically never triggers in simulation of this arena with the current DVs (1.5 m
    revisit, E1 ending after two empty scans).
- **Server:** `vllm-rosa` runs Qwen3.5-35B-A3B at `--max-model-len 131072` (GPU share 0.60,
  `--max-num-seqs 4`). It is left running for the MCP-server work that follows Module 4.

Decisions made 2026-09-27:
- Simulator: **Isaac Sim, not Gazebo** (NVIDIA stack, career value). Isaac Sim 5.1 on the Spark
  is now an unsupported release; 6.0 went GA on 2026-06-08. Decide which to use in W1.
- **URDF and the Isaac Sim twin of the car get their own session** (workstream W1). No
  simulation runs until it exists. It needs physical measurements of the car, taken with the
  camera stood upright first.
- Frontier models are welcome in the project (they were excluded from the old model plan).

### Hardware state (as of 2026-10-05)

**Superseded.** The flashed image, the camera firmware, and what is still open are in the 2026-10-29 entry. This section is the 2026-10-05 snapshot. In particular, "stand the camera up, flash and calibrate it" is not the current camera state: bm_cam-0.2 is flashed and M1.T7 is still not done.

> **Superseded in part by the 2026-10-24 entry at the top** (firmware, motors, encoder sides, PWM, power path, the agent-restart rule); kept as history.

Sources: `reference/hardware/wiring-plan.md` §4, `pico-bringup.md`, `car-build-notes.md` (updates of
2026-10-01), `discussions/module5/DESIGN.md` §1 and §6 (floor sessions of 2026-10-04), AGENTS.md §7.4,
and a read-only check of spark-2a60 at 2026-10-05 23:30 CDT (`docker ps -a`, `ls /dev/ttyACM*`,
`ip -4 addr`). Safety rules for every task: `plan/README.md` §7.

- **Wiring.** The car is fully wired and was measured on 2026-09-20: left `+` = 5.03 V (buck), middle
  `+` = 3.3 V (Pico pin 36), right `+` = 6.67 V then (4×AA alkaline via the switch). **GPIO since
  2026-10-01:** `GP0` SDA, `GP1` SCL → BNO055; `GP2` PWMA, `GP3` AIN2, `GP4` AIN1, `GP5` STBY, **`GP10` BIN1,
  `GP11` BIN2, `GP12` PWMB** → TB6612FNG; `GP16`/`GP17` right encoder A/B; `GP18`/`GP19` left encoder A/B.
  Channel A = left wheel, B = right wheel **(the plan; contradicted 2026-10-11: on the car channel A drives the RIGHT
  wheel, and the encoder sides are unverified, see the 2026-10-11 entry)**. `GP6`–`GP8` are free. The submitted Assignment 3 diagram
  (`Chen-Assign3.fzz`) is out of date for the three moved wires (`wiring-plan.md` §4).
- **Superseded 2026-10-11: the Pico now runs the Module 6 sim-to-real drive firmware (see the 2026-10-11 entry).**
  Before that: **the instructor's Module 5 IMU-tilt image** (project name still `pico2w_led`,
  node `/pico2w_led`; UF2 sha256 `9e1725d4…f59314`; flashed 2026-10-01), no longer the LED-only image. It
  publishes `/pico/imu/pitch` (10 Hz), takes `/pico/tilt/request` (`1`/`-1` arm, `0` idle probe) and reports
  `/pico/tilt/status` (1–8). **Hazard:** once armed, a 2° tilt held 100 ms runs both wheels at 100 % PWM for
  10 s; an armed request never times out and there is no disarm message. The encoders are wired but this
  image does not read them. Build and flash: `assignments/assignment5/module-5-imu-tilt-control/spark-build.sh`
  and `spark-flash.sh`. There is still **no project firmware** (moves, encoders, watchdog).
- **Bring-up tests.** Closed: the BNO055 answers at `0x28` (chip ID `0xA0`), STBY goes high, and both
  channels run and reverse (2026-10-01). Still open: encoder quadrature direction per wheel, and counts
  per wheel revolution (nominal 4320 edges for both channels; the 1.5 s pulse test gave 4070–4520 edges for
  motor A and 4743–4917 for motor B, `assignments/assignment5/evidence/diagnostics/pintest-pulse-results.txt`).
- **Directions.** The tilt firmware's "forward" drives the **drive wheels first, camera end trailing**,
  which is the opposite of the project's +x (camera/caster end = front, AGENT-DESIGN D3). On the floor a
  10 s full-power run covered about 1.5–2 m (estimate) (`discussions/module5/DESIGN.md` §1). An arc toward the slower
  motor A was predicted there, not recorded; motor A turned out to be the RIGHT wheel (2026-10-11 entry), and the drift
  observed under the Module 6 drive firmware is a LEFT veer (research note F6). The BNO055's pitch axis lies along the car.
- **Dead right wheel (2026-10-01), fixed:** the TB6612FNG board was not fully seated, so its `BO2` pin
  (row 24) touched only under pressure. Pressing the board down fixed it. Watch item: if a wheel goes dead,
  press the driver board down first (`car-build-notes.md`).
- **Power.** Last recorded state (end of the Module 5 filming, 2026-10-04): **regulator path, `VSYS`
  jumper IN, USB out**, battery switch to be left OFF (Xiaohui was told; not confirmed). **Pull the jumper
  before any USB connection.** Checked 2026-10-05: no Pico on the Spark's USB (no `/dev/ttyACM*`). No
  STBY pull-down is fitted and no resistor or power bank is owned (2026-10-04); the Module 5 waiver does
  not carry over: the 4.7 kΩ pull-down is mandatory before any project wheels-down run (AGENT-DESIGN §W).
  Power-up order: Pico first, battery switch second.
- **Battery.** 6.67 V on 2026-09-20; 5.7–5.9 V at the driver on 2026-10-01; one Module 5 filming take
  ended because the pack died (`discussions/module5/DESIGN.md` step 3.2). Measure before the next use; replace below 5.5 V. The bent tray spring is
  still the first suspect for brownouts.
- **Camera unchanged:** ESP32-CAM with OV3660 on its own USB-C, taped **flat, looking at the ceiling**; it
  must be stood upright before any tag work. No project firmware; `esptool` and `arduino-cli` are absent on
  the Spark.
- **Wi-Fi.** The home mesh is lossy where the car drives: 31–52 of 60 status samples per 6 s at the start
  of the floor lane and 22 of 60 at its far end; one rehearsal lost the link mid-run
  (`discussions/module5/DESIGN.md` step 2.5). This matters for the watchdog period (W3).
- **micro-ROS agent policy (AGENTS.md §7.4, since 2026-10-01):** there is no standing agent container.
  Each session starts a fresh one (`docker run --rm -it --name pico-micro-ros-agent --network host
  microros/micro-ros-agent:humble udp4 --port 8888 -v6`) and removes it at the end. After the agent
  restarts, reboot the Pico (it cannot reconnect). Read the graph inside `rosa-ros2` and expect exactly one
  `/pico2w_led`; ghost nodes appear after Pico reboots under one agent. The firmware has the agent address
  `192.168.5.1:8888` compiled in; the Spark's Ethernet address was still `192.168.5.1` on 2026-10-05.
- **Containers on the Spark (2026-10-05 23:30 CDT):** `rosa-ros2` and `vllm-rosa` both **exited** (about
  41 h earlier, after the Module 5 session); no `pico-micro-ros-agent` container. `docker start vllm-rosa`
  restarts the server with its last arguments (Qwen3.5-35B-A3B, `--max-model-len 131072`, GPU share 0.60,
  `--max-num-seqs 4`). The project container `beaconmind-ros` does not exist yet (plan M1.T3).
- **Still open:** stand the camera up, flash and calibrate it (plan M1.T6–T8); car dimensions: measured
  2026-10-10 and written to `configs/car.json`, but single readings, no roll-out and no encoder counts (M1.T9,
  blocked on Xiaohui; see the 2026-10-10 entry at the end); the STBY pull-down and the power
  path (M3.T1); project move firmware with watchdog and stall detection (M3.T2–T7); encoder direction
  (M3.T3).
- **Watch items:** the tray spring; pack voltage; the driver board's seating; Wi-Fi range.

## 2026-09-14 design and status — everything below this line predates 2026-09-27 (history)

- Milestone: project-proposal quad chart.
- Decision: build a **landmark-grounded natural-language mission rover**.
- Student and project owner: **Xiaohui Chen**.
- Team arrangement: **individual project**.
- Hardware scope: **base kit only**; no additional electronic sensors are planned.
- Learning priority: balance robotics, perception, and agent reasoning.
- Model-serving direction: **vLLM on the DGX Spark**, with empirical model selection rather
  than a fixed Ollama model.
- Working proposal deck: `course-project/Chen-Project-Proposal.pptx`.
- Proposal review: passes validation against the instructor-supplied quad-chart template
  with documented geometry/custom-placement warnings; LibreOffice and Quick Look renders
  show no clipping. It is not canonical-JHU-template compliant because the instructor's
  required template has a different theme and layout signature.
- Implementation has not started. The immediate deliverable is the single-slide proposal.

## Proposal requirements

The supplied proposal description requires one completed PowerPoint quad-chart slide:

1. A specific problem statement explaining the task and why it matters.
2. Two or three project questions.
3. The approach and ROSA tools, including sensors, actuators, and any added hardware.
4. A system illustration showing inputs, processing, and outputs.
5. Expected demo behavior and measurable evaluation criteria.
6. The participant name and individual contribution.

Supplied source artifacts as of 2026-09-14:

- `/Users/xiaohuichen/Downloads/Project Proposal.epub`
- `/Users/xiaohuichen/Downloads/QuadChart-1.pptx`
- `/Users/xiaohuichen/Downloads/Module3_Hardware_Assembly_Wiring_Slides-1.pptx`

The proposal is explicitly a starting point rather than a binding final design.

## Selected project

### Working title

**Landmark-Grounded Natural-Language Mission Rover**

### Core idea

A user gives the rover a multi-step instruction such as:

> Go past the blue station, inspect station C, and return home by the shorter route.

The DGX Spark converts the instruction into a sequence of bounded ROSA tools. The physical
cart follows known safe routes, uses wheel encoders and the BNO055 for local motion
estimation, and uses printed AprilTags to identify destinations and correct accumulated
odometry drift. The agent verifies intermediate results and replans when an expected
landmark is absent or the rover reaches the wrong station.

### Why this project was selected

The project deliberately spans the course's major learning areas:

- differential-drive kinematics and closed-loop wheel control;
- encoder odometry, IMU integration, and localization error;
- camera calibration and fiducial-marker perception;
- ROS 2 topics, services/actions, TF, diagnostics, and failure handling;
- ReAct/ROSA planning, constrained tool invocation, memory, and replanning;
- local LLM/VLM inference on the DGX Spark;
- simulation-to-real transfer and quantitative embodied-agent evaluation.

It remains feasible for one student because the arena and routes are controlled and the
landmarks provide inexpensive, reproducible visual ground truth.

## Draft research questions

1. Does perception-conditioned replanning achieve a higher mission-success rate than a
   one-shot language-generated plan?
2. How much do BNO055 integration and AprilTag landmark corrections reduce final position
   and heading error relative to encoder odometry alone?
3. Which vLLM-served model provides the best valid-tool-call rate, mission success, and
   latency on the DGX Spark?

These are working questions for the proposal and may be narrowed after initial feasibility
tests.

## System boundary and architecture

### DGX Spark: stationary high-level computer

The DGX Spark remains off the cart and connected to its supplied AC power. It is responsible
for:

- ROS 2 Jazzy coordination for the physical robot;
- local LLM/VLM serving through vLLM;
- natural-language mission parsing and ROSA/ReAct planning;
- AprilTag detection and selected semantic image inspection;
- landmark registry, mission memory, and route selection;
- state estimation and high-level waypoint control;
- experiment logging, metrics, and report generation.

The DGX sends only validated, bounded motion goals or velocity setpoints. The LLM/VLM never
controls motor PWM and never belongs in the wheel-control feedback loop.

### Model-serving and selection strategy

Do not use `llama3.2` for the course project. Serve candidate models through vLLM and select
the final planning model from measured results rather than preference alone.

- vLLM's OpenAI-compatible API replaces the fixed Ollama path so the same ROSA-facing
  interface can benchmark several larger models already available on the DGX Spark.
- **Qwen3.5-35B-A3B** is the starting candidate because local vision input and tool calling
  have already been demonstrated on this Spark.
- **Qwen3.8-27B-FP8** and **Gemma 4-26B-A4B-it** are locally cached comparison candidates,
  but their vLLM compatibility, prompt behavior, tool use, latency, and memory use remain
  unverified for this project.
- Compare valid structured-tool-call rate, simulated mission success, p50/p95 latency,
  memory use, and failure categories before choosing the model for physical trials.
- Keep the model out of continuous control regardless of which candidate wins.

### Raspberry Pi Pico 2 W: cart-side real-time authority

The Pico is responsible for:

- Hall-encoder counting and wheel-speed estimation;
- fixed-rate left/right wheel PID;
- BNO055 sampling;
- TB6612FNG direction and PWM outputs;
- acceleration and command bounds;
- motor-disable, watchdog, and fail-stop behavior.

A stale command, lost connection, invalid command, reset, or software fault must stop the
motors locally without waiting for the DGX or LLM.

### ESP32-CAM: visual sensor

The ESP32-CAM sends compressed JPEG snapshots or a modest-rate MJPEG stream over Wi-Fi to a
DGX-side bridge. Images do not pass through the Pico. Conventional AprilTag detection runs
frequently; slower VLM observations are event-driven and never safety-critical.

### ROSA tool boundary

Candidate bounded tools are:

- `get_robot_state`
- `find_landmark`
- `navigate_to_landmark`
- `verify_arrival`
- `rotate_scan`
- `inspect_station`
- `mark_checkpoint`
- `choose_route`
- `return_home`
- `stop`

Each tool must validate arguments, operating state, speed and distance limits, timeout, and
result status. Continuous low-level control stays outside the agent.

### Agent prompt and ROS 2 interfaces

The agent prompt will provide:

- the mission role and safety boundary;
- the landmark registry and current robot state;
- the allowed tool schemas and argument constraints;
- an observe → verify → replan policy;
- explicit instructions to report uncertainty and stop after failed validation.

Planned ROS 2 interfaces include:

- `/odom` for fused or wheel odometry;
- `/imu/data` for BNO055-derived IMU data;
- `/camera/image/compressed` for DGX-side camera consumers;
- bounded `/cmd_vel` output from the validated motion layer;
- actions or services behind each ROSA tool with explicit success/failure results.

## Landmark plan

Use printed fiducial markers rather than additional electronic hardware.

- Preferred family: AprilTag `36h11`.
- Assign one unique tag to each station and one to the home location.
- Print on matte paper or cardstock with a white border.
- Mount each tag flat and rigidly on cardboard, foam board, or a wall near camera height.
- Measure each tag's physical side length and surveyed arena pose.
- Store a registry mapping tag ID to semantic name and map pose.
- Print a checkerboard or ChArUco target and calibrate the actual ESP32 camera.
- Measure the camera-to-robot mounting transform after final assembly.

Initial operation can use tag identity only for station confirmation. The advanced version
will estimate relative camera pose from the tag corners and use known landmark poses to
correct odometry.

Materials expected to be sufficient:

- printer access;
- matte paper or cardstock;
- cardboard or foam board;
- painter's tape or removable adhesive;
- ruler or measuring tape;
- printed camera-calibration target.

No additional electronic component is required for the selected landmark design.

## Arena and safety scope

The base kit has no verified range sensor. AprilTags provide localization but do not detect
obstacles. Therefore:

- operate at low speed in a supervised, controlled arena;
- use predefined clear lanes or a known waypoint graph;
- exclude people, pets, moving obstacles, stairs, and drop-offs from the test area;
- enforce conservative motion limits and a locally testable Pico watchdog;
- provide an immediately accessible motor-disable control;
- do not claim general autonomous navigation or dynamic obstacle avoidance.

Adding a ToF sensor, bumper, depth camera, or lidar is outside the currently selected
base-kit-only scope. If later added, update this document before relying on it.

## Planned evaluation

Primary metrics:

- complete mission success rate;
- correct waypoint and action order;
- final position and heading error;
- path length and path-efficiency/SPL-style score;
- number of replans;
- invalid or rejected tool-call rate;
- p50/p95 latency from mission command to accepted bounded tool;
- human interventions and categorized failure modes.

Planned comparisons:

- one-shot plan versus perception-conditioned replanning;
- encoder-only odometry versus encoder plus IMU;
- dead reckoning versus dead reckoning with landmark correction;
- Qwen3.5-35B-A3B versus Qwen3.8-27B-FP8 versus Gemma 4-26B-A4B-it, after each
  candidate passes basic serving and structured-tool-call gates;
- bounded ROSA tools versus a deliberately more permissive high-level interface.

Simulation should provide exact ground truth before the same conditions are tested in the
physical arena.

Preliminary proposal targets, not measured outcomes:

- at least 80% success over 30 held-out physical missions with the selected model;
- median final map-frame error no greater than 0.25 m and 15 degrees;
- cessation of the Pico's motor command within 0.5 seconds after communication loss.

## Known hardware and integration uncertainties

> **2026-09-27 note:** some items below are resolved or partly resolved; see the hardware state
> at the top. Item 1: the camera is an OV3660 (confirmed from the ribbon marking). Item 5: Wi-Fi
> micro-ROS works for the LED image (2026-09-23). Items 3 and 4 are partly resolved: the encoders
> run at 3.3 V, and the rails and the AMS1117 3.3 V output are measured. Items 2 and 6–8 are
> still open.

Do not produce final wiring or odometry constants until these are resolved:

1. The Module 3 slides identify an OV2640 camera, while prior repository notes identify an
   OV3660. Confirm the physical sensor and board markings.
2. The exact 1:90 Hall-encoder motor and the meaning of its stated `12 PPR` are unverified.
   Determine counts per output-shaft revolution experimentally or from the exact datasheet.
3. The encoder supply voltage, output type, motor stall current, and safe TB6612FNG loading
   require exact part identification.
4. AMS1117 devices are linear LDO regulators, not buck converters. Verify the actual power
   modules, battery chemistry, voltage range, thermal margin, and current capability.
5. Pico 2 W/RP2350 wireless micro-ROS transport is not yet proven in this environment.
   Validate it early; retain serial bring-up or a custom Pico-to-DGX UDP bridge as a fallback.
6. Magnetic interference from motors and wiring may degrade BNO055 heading. Measure this
   rather than assuming absolute heading is reliable.
7. Camera resolution, field of view, focus, frame rate, JPEG size, latency, and clock behavior
   must be measured on the actual ESP32-CAM assembly.
8. Qwen3.8-27B-FP8 and Gemma 4-26B-A4B-it are candidates, not proven project backends.
   Validate serving, structured tool calls, and ROSA compatibility before comparing quality.

## Immediate next steps

1. Review the drafted quad chart in PowerPoint when available and run its Accessibility
   Checker before submission.
2. Keep the generative-AI disclosure visible in the submitted slide.
3. Upload `course-project/Chen-Project-Proposal.pptx` to Canvas after personal review.
4. Confirm the physical labels and purchase details for the camera, motors, battery, and
   regulator modules.
5. Define a small candidate arena and landmark registry.
6. Prove AprilTag generation and detection against actual ESP32-CAM frames.
7. Prove the Pico communication path and fail-stop watchdog before free-wheel testing.
8. Build a simulation baseline before integrating the physical cart.

## Sources used in the decision

Retrieved 2026-09-14:

- NVIDIA, *DGX Spark User Guide — Hardware Overview*:
  <https://docs.nvidia.com/dgx/dgx-spark/hardware.html>
- Raspberry Pi, *Pico 2 W documentation*:
  <https://pip.raspberrypi.com/documents/RP-008304-DS>
- Toshiba, *TB6612FNG Datasheet*:
  <https://toshiba.semicon-storage.com/info/TB6612FNG_datasheet_en_20141001.pdf?did=10660&prodName=TB6612FNG>
- Bosch Sensortec, *BNO055 Datasheet*:
  <https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bno055-ds000.pdf>
- Espressif, *ESP32 Camera Driver*:
  <https://github.com/espressif/esp32-camera>
- AprilRobotics, *AprilTag*:
  <https://github.com/AprilRobotics/apriltag>
- OpenCV, *Detection of ArUco Markers*:
  <https://docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html>
- NASA JPL et al., *ROSA: A ROS Agent*:
  <https://arxiv.org/abs/2410.06472>
- Anderson et al., *On Evaluation of Embodied Navigation Agents*:
  <https://arxiv.org/abs/1807.06757>

## Generative-AI provenance

2026-09-27 update: Claude Opus 5.5 via Claude Code ran the LLM-as-SLAM feasibility research,
drafted `APPROACH-LLM-SLAM.md`, and wrote the direction-change and hardware-state sections
above. The direction itself is Xiaohui Chen's.

GPT-5.6 Sol in Cursor assisted with researching the supplied requirements and hardware,
comparing project concepts, and drafting this context record. Xiaohui Chen selected the
project direction and remains responsible for reviewing, understanding, and validating the
design before submission or implementation.

## 2026-10-06 — M1.T2 contracts

M1.T2 is done on the Mac and the Spark host. Evidence is `course-project/evidence/M1/M1.T2/`. The Python 3.10 run is deferred to M1.T14: M1.T3 was `in-progress`, not `done`, when this task finished, so `beaconmind-ros` was not used and T3 was not started.

- **Part A.** Vendored `l2_geometry.py` and `fewshot-numbers.json` under `beaconmind/tests/fixtures/reference/`. Their SHA-256 values match the task's expected hashes (`eb19b5d9…6e60243f`, `3f830176…1c3258`). Public repo, 2026-10-29: `l2_geometry.py` is not in this tree. It stays in the private course repo. `fewshot-numbers.json` is here, and `test_matches_reference_random` skips without the reference file. `configs/dv.json` has **66** keys in `values`: the 53 C0 keys, in C0 order, at the C0 values, plus 13 literals from `l2_geometry.py` (the 12 named in the task, plus `sector_unknown_leg_moves` = 1 from the `1 if wall is None` branch). `sigma_range_b_per_m` is unit `m/m` because the ordered unit rule matches `_per_m`; the step-2 table's unit column said `1`. Unused `SECTOR_BLOCK_*` constants were not added. `beaconmind.geometry` has no `import numpy`.
- **Part B.** Fourteen draft 2020-12 schemas, `python -m beaconmind.schemas`, `configs/providers.json`, and the seven contract fixtures. The schema CLI printed `OK` for `dv.json`, `providers.json`, and each fixture.
- **Tests.** Mac `pytest-mac.txt`: `37 passed in 0.37s`. Spark host Python 3.12.3 `pytest-spark.txt`: `37 passed in 0.28s`. Both are 0 failed. The plan's expected 31 is the scaffold (5) plus this task (5 + 8 + 13). The extra 6 are `tests/test_latency.py`, already in the tree from another task. The Mac venv check therefore printed more than the plan's `5 passed`, with 0 failed. `pytest-geometry-verbose.txt` names `test_matches_reference_random PASSED` and `test_example1_numbers PASSED`.
- **Schema CLI shell.** The task's `for` loop leaves `$f` unquoted. zsh does not split that into two arguments, so the first run only printed usage. The saved `schema-cli.txt` is the same loop run under bash, and every line is `OK`.
- **Name note, not a field change.** AGENT-DESIGN D5 logs a mismatch as `state_violation`. README C5 calls that code `state`. The run-log schema leaves `code` as a string, so this task did not pick one name and did not change a C0 value.
- **Left running.** Nothing from this task. No container was started. No hardware was touched.
- **Not committed.**

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, wrote `dv.json`, `providers.json`, `dv.py`, the geometry port, the JSON Schemas, the schema CLI, the contract tests and fixtures, the evidence files, and this entry. The geometry port keeps the reference disclosure from Claude Opus 5.5 (2026-09-27).

## 2026-10-06 — M1.T6 camera

M1.T6 is blocked after step 7. It is not done. Step 14 is pending. Evidence so far is `course-project/evidence/M1/M1.T6/` (`usb-and-load.txt` from the earlier identification, `toolchain.txt`, `camera-pins.txt`).

- **Last completed step.** Step 7. The AI-Thinker pin block was read from the pinned image's `camera_pins.h` and saved. Steps 8–15 were not done. The sketch, `build.sh`, and `flash.sh` were not written. The serial port was not opened.
- **Toolchain (step 6).** Spark image `bm-esp32-builder`. The Dockerfile is pinned to arduino-cli 1.5.2-rc.1 and `esp32:esp32@3.3.12`. The pinned rebuild printed `EXIT:0`. FQBN printed by the image: `esp32:esp32:esp32cam` (AI Thinker ESP32-CAM). Image id `sha256:a17e85dbf1c11c724dc8cd44bfeb1bd3b66b1bbab4c63934d4e3280080a419e4`.
- **USB.** Unchanged from the 19:13 CDT identification: FIREPHX `0843:5740`, driver `cdc_acm`, node `/dev/ttyACM0`, by-id `usb-FIREPHX_USB_SER_FX2348N-if00`. This session did not open that node.
- **Why upload stopped.** `arduino-cli board details -b esp32:esp32:esp32cam` lists six menus: CPUFreq, FlashFreq, FlashMode, PartitionScheme, DebugLevel, EraseFlash. None is a USB, CDC, or ACM choice, and none is a flash voltage. `boards.txt` has a fixed `upload.speed=460800`, `serial.disableDTR=true`, `serial.disableRTS=true`, and empty `upload.flags`. Those values were not passed to an upload. No baud and no flash voltage were selected.
- **HTTP.** No capture URL was requested. There is no status code.
- **Step 14.** Pending. No forward-view frames were saved, and `picture-quality.md` was not written.
- **Checked menu defaults, unused.** CPUFreq=240, FlashFreq=80, FlashMode=qio, PartitionScheme=huge_app, DebugLevel=none, EraseFlash=none. The QIO menu item in `boards.txt` sets `build.flash_mode=dio` and `build.boot=qio`. That line was read and not overridden. PSRAM is a build define (`-DBOARD_HAS_PSRAM`), not a menu.
- **Wi-Fi header.** Present and git-ignored. It was not printed and not compiled.
- **Tests.** Spark host Python has Pillow 11.3.0. Mac `course-project/.venv` ran `pytest course-project/beaconmind/tests/test_camera_probe.py`: `3 passed in 0.05s`.
- **Hardware.** Camera USB was left connected. The battery switch was already confirmed OFF and was not touched. Pico USB was already out. M1.T7 was not started.
- **Left running.** `vllm-rosa` was still serving after the pinned rebuild (`curl` to `http://127.0.0.1:8000/v1/models` returned HTTP 200). `beaconmind-ros` was still up. Isaac was not started. `rosa-ros2` was not stopped or started. tmux `bm-m1t6` is an idle shell after the image build. tmux `bm-m1t4` was not touched.
- **Not committed.**

Xiaohui's next decision is whether a later session may upload with the bare FQBN `esp32:esp32:esp32cam` and the core's own recipe, adding no baud flag and no flash-voltage flag. After `GET /capture` returns HTTP 200, put the car on the floor in its normal stance, battery switch OFF, flash LED off, and aim the lens forward so the lower part of the frame is the floor ahead. One of those frames needs a sharp high-contrast edge. Do not use the ceiling, a hand, a dark room, a page held against the lens, or the close wall from the LED freshness test.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, wrote the builder Dockerfile, the serial reader, the capture probe and its tests, the pin and toolchain notes, and this entry.

## 2026-10-06 — M1.T6 camera upload

The stop after step 7 was lifted. `esp32cam-notes.md` §5 and §8 agree with a bare `esp32:esp32:esp32cam` upload: firmware loads through the base board USB-C, and those notes do not set a baud or a flash voltage. M1.T6 is blocked on the upload. It is not done. Step 14 is pending.

- **Last completed work.** Steps 8–10. The sketch compiled. Step 11's upload did not. `arduino-cli` 1.5.2-rc.1 rejected a mount at `/src` (`Can't open sketch: main file missing from sketch: /src/src.ino`), so the sketch directory is mounted as `/src/bm_cam`. The FQBN stayed bare.
- **Size.** `Sketch uses 1026609 bytes (32%) of program storage space. Maximum is 3145728 bytes.` Globals `59312 bytes (18%)`. Saved in `evidence/M1/M1.T6/build-size.txt`.
- **USB before the upload.** `/dev/serial/by-id/usb-FIREPHX_USB_SER_FX2348N-if00` still pointed at `/dev/ttyACM0`, and `lsusb` still showed `0843:5740`. The same check passed again after the compile. The port was not opened until `flash.sh`.
- **Upload.** Did not succeed. esptool v5.3.1 on `/dev/ttyACM0` printed: `A fatal error occurred: Failed to connect to ESP32: Wrong boot mode detected (0x12)! The chip needs to be in download mode.` No baud flag and no flash-voltage flag were added. The serial monitor was not opened.
- **HTTP.** No capture URL was requested. There is no status code.
- **Step 14.** Pending.
- **Hardware.** Camera USB left connected. Battery switch was not turned on. Pico USB was not plugged in. The flash LED was not blinked.
- **Left running.** `vllm-rosa` answered `http://127.0.0.1:8000/v1/models` with HTTP 200 after the failed upload. `beaconmind-ros` was still up. Isaac was not started. `rosa-ros2` was not stopped or started. tmux `bm-m1t6` and `bm-m1t4` were left in place.
- **Not committed.**

Xiaohui: leave the battery switch off and leave the camera USB where it is. Hold the base board's `IO0` button, press and release `RST`, then release `IO0`. That is the download-mode step in `esp32cam-notes.md` §8. Say when that is done and the same bare-FQBN `flash.sh` can be retried. After `GET /capture` returns HTTP 200, aim the car on the floor, battery off, flash LED off, lens forward so the lower frame is the floor ahead, with one sharp high-contrast edge.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, wrote the camera sketch, `build.sh`, `flash.sh`, the size note, and this entry.

## 2026-10-06 — M1.T6 upload retry

The upload succeeded. M1.T6 is not done. Step 14 is pending. HTTP was not reached.

- **Upload.** `flash.sh` with bare FQBN `esp32:esp32:esp32cam`. The FIREPHX by-id link still resolved to `/dev/ttyACM0`, and `lsusb` still showed `0843:5740`. The port was not opened before esptool. esptool v5.3.1 printed `Hash of data verified.` and `Hard resetting via RTS pin...` `FLASH_EXIT:0`. The app image was 1026752 bytes written at `0x00010000`. Recorded in `evidence/M1/M1.T6/upload.txt`.
- **Serial.** `serial_read.py` for 30 s with `--esp32-reset` wrote `serial-boot.txt` at 0 bytes. Two later sniffs, without another RTS pulse, were also 0 bytes. No `BM_CAM READY` line, so there is no camera IP.
- **HTTP.** No URL was requested. There is no status code. A scan of `192.168.4.0/22` found no response body containing `bm_cam-0.1`.
- **Step 14.** Pending.
- **Left running.** `vllm-rosa` had answered `/v1/models` with HTTP 200 during this session. `beaconmind-ros` was not stopped. Isaac was not started. `rosa-ros2` was not stopped or started. Battery switch was not turned on.
- **Not committed.**

The flashed image is on the chip. The boot log did not come back over the FIREPHX serial port, so the rate and freshness probes did not run.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, recorded this upload result.

## 2026-10-06 — M1.T6 after RST

After RST alone, 20664 serial bytes arrived at 115200 with DTR and RTS held false. The log repeats `rst:0x10 (RTCWDT_RTC_RESET),boot:0x12 (SPI_FAST_FLASH_BOOT)` and contains no `BM_CAM READY`, no camera-probe line, no brownout line, and no IP. HTTP was not requested. Step 14 stays pending. M1.T6 is not done. `vllm-rosa` still returned HTTP 200. Saved as `evidence/M1/M1.T6/serial-boot-rst.txt`.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, recorded this boot log.

## 2026-10-06 — M1.T6 boot-loop cause

The 20,664-byte log is the ROM bootloader only: `mode:DIO, clock div:1`, then `load:0x3fff0030,len:4876`, then `load:0x07800040,len:4232256`, then `rst:0x10 (RTCWDT_RTC_RESET)`. The ELF has no 4 MB segment, and there is no Guru Meditation, brownout, or `BM_CAM` line. The flashed image was bare `esp32:esp32:esp32cam` with `CONFIG_SPIRAM=y` and `--flash-freq 80m`. `boards.txt` documents `FlashFreq=40`. `build.sh` and `flash.sh` now pass that option. Nothing was uploaded. No button yet.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, set the documented 40 MHz flash-frequency option.

## 2026-10-06 — M1.T6 40 MHz compile

`build.sh` compiled with `esp32:esp32:esp32cam:FlashFreq=40` and exited 0. The new `flash_args` line is `--flash-mode dio --flash-freq 40m --flash-size 4MB`. Sketch size is unchanged: `Sketch uses 1026609 bytes (32%) of program storage space.` The bootloader and app binaries differ from the 80 MHz copies that were flashed. `flash.sh` was not run. The serial port was not opened.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, recorded this compile.

## 2026-10-06 — M1.T6 40 MHz upload

The 40 MHz image uploaded. esptool printed `Hash of data verified.` and `Hard resetting via RTS pin...` The bootloader image header is `Flash freq: 40m`. The upload recipe passes `--flash-freq keep`, which leaves that header in place; `flash_args` still says `--flash-freq 40m`. A 25 s read at 115200 with DTR and RTS held false, and a second 20 s read the same way, both returned 0 bytes. That is not the `len:4232256` loop, and there is no `BM_CAM READY` line and no IP. HTTP was not requested. Step 14 stays pending. M1.T6 is not done. `vllm-rosa` still returned HTTP 200.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, recorded this upload.

## 2026-10-06 — M1.T6 40 MHz boot after RST

After RST alone, 20756 bytes arrived at 115200. The clock is now `mode:DIO, clock div:2`, and the loop is still `load:0x07800040,len:4242496` then `rst:0x10 (RTCWDT_RTC_RESET)`. No `BM_CAM READY`, no IP, no brownout. HTTP was not requested. Another flash frequency was not tried. Step 14 stays pending. M1.T6 is not done. `vllm-rosa` still returned HTTP 200.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, recorded this boot log.

## 2026-10-06 — M1.T6 image check

The 40 MHz files are coherent. Bootloader segment 0 is `0x3fff0030` length 4876, and segment 1 is `0x40078000` length `0x40bc` (16572). The ROM line `load:0x07800040,len:4242496` is that header read one byte early (`0x40bc40` = 4242496). The upload wrote `0x1000`, `0x8000`, `0xe000`, and `0x10000`, and esptool printed `Hash of data verified`. Flash mode in the image and in the log is DIO, which is what the default `FlashMode=qio` menu item sets. No button. Nothing was uploaded in this check.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, checked the image headers against the boot log.

## 2026-10-06 — M1.T6 DIO bootloader compile

`FlashMode=dio` selects `bootloader_dio_40m.elf` (`build.boot=dio`). The image on the chip used the default `FlashMode=qio`, which selects `bootloader_qio_40m.elf`. Both set `build.flash_mode=dio`. Rebuilt with `esp32:esp32:esp32cam:FlashFreq=40,FlashMode=dio`. `flash_args` is still `--flash-mode dio --flash-freq 40m --flash-size 4MB`. Sketch size `1026625` bytes. The new bootloader is 23520 bytes and is not the previous file. Upload has not run. The serial port was not opened.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, compiled the DIO bootloader image.

## 2026-10-06 — M1.T6 DIO upload

The staged bootloader was the 23520-byte DIO file, with `flash_args` `--flash-mode dio --flash-freq 40m`. esptool wrote it at `0x1000`, the partition table at `0x8000`, `boot_app0` at `0xe000`, and the app at `0x10000`, and printed `Hash of data verified`. A 20 s read at 115200 with DTR and RTS held false returned 0 bytes. No `BM_CAM READY`, no IP, no `0x07800040` line. HTTP was not requested. Step 14 stays pending. M1.T6 is not done. `vllm-rosa` still returned HTTP 200.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, recorded this upload.

## 2026-10-06 — M1.T6 DIO boot after RST

After RST alone, 19418 bytes arrived at 115200. The log repeats `mode:DIO, clock div:2`, `load:0x3fff0030,len:4640`, then `load:0x0780000b,len:4001856`, then `rst:0x10 (RTCWDT_RTC_RESET)`. That is the same failed second load. No `BM_CAM READY`, no IP, no brownout. HTTP was not requested. Another frequency or flash mode was not tried. Step 14 stays pending. M1.T6 is not done. `vllm-rosa` still returned HTTP 200.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, recorded this boot log.

## 2026-10-06 — M1.T4 latency

M1.T4 measurements are done. The OD8 proposal is not approved, so the task stays `in-progress`. Evidence is `course-project/evidence/M1/M1.T4/`. The JSONL files and the full probe log stay on the Spark at `course-project/data/latency/20261006-185238-*`.

- **Thinking on** (n = 20): p50 327.9 s, p95 555.7 s, max 761.5 s, n_all_pass 5.
- **Thinking off** (n = 20): p50 13.7 s, p95 18.8 s, max 18.9 s, n_all_pass 0.
- **Queue:** max_running 1, max_waiting 0 (3259 numeric samples, no waiting request).
- **Proposal, pending Xiaohui:** Qwen3.5 thinking on is replay-only, because p95 is above 60 s. Thinking off is inside 60 s but n_all_pass is 0, so it is not the closed-loop setting. Closed-loop runs and the demo use an API model chosen in M1.T11 and M1.T10. Any closed-loop episode that still uses this local model runs one at a time on `vllm-rosa` (`--max-num-seqs` was left at 4; the container was not recreated).
- **Left running.** `vllm-rosa` is serving `Qwen/Qwen3.5-35B-A3B`. `beaconmind-ros` was already up from another task and was not stopped. `rosa-ros2` was not started. tmux `bm-m1t4` has finished. `gpu-free.txt` is written. No frontier API was called.
- **Not committed.**

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, wrote the latency module, the summary and probe scripts, the OD8 proposal, and this entry.

## 2026-10-06 — M1.T15 local candidates

On 2026-10-06 Xiaohui rejected Qwen3.5-35B-A3B as the closed-loop model ("Qwen 3.5 performance is really bad and should not be used") and did not approve the OD8 API-model proposal. M1.T4 stays in-progress with the measured result (thinking-on p95 555.7 s, n_all_pass 5/20; thinking-off p95 18.8 s, n_all_pass 0/20; max_waiting 0; max_running 1). M1.T15 measures Qwen3.8-Flash-Next (`nvidia/Qwen3.8-Flash-Next-NVFP4`, not the cached `Qwen/Qwen3.8-27B-FP8`) and then Ternary Bonsai 2 27B, one model at a time, on the same Module 4 harness, with the same gate (p95 ≤ 60 s and n_all_pass > 0). OD8 stays unapproved until both runs exist. AI-assisted: Grok 4.7 via Cursor, 2026-10-06: added the two-model latency and pass measurement.

## 2026-10-06 — M1.T15 Bonsai speed

Ternary Bonsai `PTQ1_0` on the Prism CPU llama.cpp binary is not a fast decider. Stamp `20261006-221722`, thinking on: 0 decisions finished. The first prompt was 6103 tokens in 851.51 s (7.17 tok/s); generation was still going at 2799 tokens and 3.97 tok/s, with no tool call recorded. That `llama-server` and tmux `bm-m1-bonsai` were stopped at 22:43 CT. The on-disk CUDA llama.cpp (GB10, SM 12.1) rejects this file (ggml type 143). Prism publishes no Linux aarch64 CUDA build. M1.T15 stays in progress. OD8 stays unapproved. Note: `evidence/M1/M1.T15/bonsai-speed.md`. AI-assisted: Grok 4.7 via Cursor, 2026-10-06.

## 2026-10-06 — M1.T3 beaconmind-ros

M1.T3 is done. Evidence is `course-project/evidence/M1/M1.T3/`.

- **Container.** Image `beaconmind-ros:humble`, container `beaconmind-ros`, left running (`restart: "no"`). Start with `cd course-project/docker && docker compose up -d` on the Spark. Python 3.10.12. Fast DDS `2.6.12-1jammy.20260725.060440`. Pip in the image: openai 3.26.0, anthropic 1.11.0, jsonschema 4.26.0, pytest 9.1.1. `providers` in `pyproject.toml` is pinned to the openai and anthropic versions. The package is on `PYTHONPATH` (`/workspace/course-project/beaconmind/src`); there is no editable install in the container.
- **Graph.** `/chassis/odom` in the container at about 16.3 Hz, one Odometry message (`frame_id: odom`, `child_frame_id: base_link`). AprilTag id 3, family `tag36h11`, TF child frame `tag36h11:3` (README C1). One `ros2 node list -a` shows `/apriltag` and `/_Robots_Robot_0_transform_tree_odometry_ros2_publish_odometry`. The default `ros2 node list` hides that Isaac node because the name starts with `_`. `/chassis/odom` and `/apriltag/detections` were both in the topic list.
- **SHM litmus.** `ls /dev/shm | grep -c fastrtps_port` printed 72. Those files are dated Oct 3–4 and none were created during the launch. They were not deleted.
- **Python 3.10.** `pytest-py310.txt` ends with `11 passed in 0.01s` (scaffold tests plus `test_latency.py`, which were the tests on the Spark at that run).
- **Left running.** `beaconmind-ros` is up. `vllm-rosa` was left running (EngineCore still resident after `gpu-free.txt`). `rosa-ros2` was not started. Isaac `sim_server.py` was stopped. tmux `bm-m1t3` has finished. The Pico half of W0 is still M1.T13.
- **Not committed.**

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, wrote the Humble image, compose file, UDP profile, tag tools, `beaconmind_bringup`, the C1 frame line, and this entry.

## 2026-10-06 — M1.T6 desk pictures

The camera answered HTTP. M1.T6 is not done. Step 14 is not a pass: the robot was on a desk, and the lens was not aimed at the floor. Do not start M1.T7 from these frames.

- **HTTP.** From the Spark, `GET http://192.168.4.24/status` returned 200 (198 bytes, `bm_cam-0.1`, SVGA, `frames` 0). Three `GET /capture` calls, about one second apart, returned 200 with JPEG bodies of 31918, 33402, and 32071 bytes (`X-BM-Seq` 1, 2, 3). The flash LED was not commanded. The board was not reset and was not flashed.
- **Files.** Spark and Mac: `course-project/evidence/M1/M1.T6/pictures/capture-1.jpg`, `capture-2.jpg`, `capture-3.jpg`. Also on the Mac Desktop at `beaconmind-camera/`. Note: `pictures/desk-review.md`. Each frame shows a dark cabinet and a desk, soft focus, not a failure image. Floor-tag occlusion cannot be judged from these files.
- **Left running.** `vllm-rosa` and `beaconmind-ros` were not stopped.
- **Not committed.**

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, captured the desk JPEGs and wrote the picture note.

## 2026-10-06 — URDF subagent

The subagent that writes this URDF must be Claude Opus 5.5 at xhigh effort (Cursor model slug `claude-opus-5-5-xhigh`); do not use a different model for that task, as requested by Xiaohui on 2026-10-06. See M2.T4 in `plan/M2-sim-mvp.md`. AI-assisted: Grok 4.7 via Cursor, 2026-10-06: recorded the URDF subagent model.

## 2026-10-06 — Bonsai deferred to research

On 2026-10-06 at 23:58 CT Xiaohui made Bonsai a research action item only. Do not serve it, do not download more weights, and do not run llama.cpp. Ternary-Bonsai-2-27B was tried as `PTQ1_0` on Prism CPU llama.cpp (stamp `20261006-221722`): about 4 tok/s and 0 finished decisions. It is not a closed-loop candidate. The CUDA llama.cpp on the Spark cannot load ggml type 143. Future research may look for an aarch64 CUDA build that understands that type. Notes: `evidence/M1/M1.T15/bonsai-research.md` and `bonsai-speed.md`.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: recorded the Qwen3.8 pin, deferred Bonsai, and started M1.T5.

## 2026-10-06 — closed-loop model pinned

On 2026-10-06 at 23:58 CT Xiaohui pinned the closed-loop model. Their words: "pin the qwen 3.8 flash next". The served checkpoint is `nvidia/Qwen3.8-Flash-Next-NVFP4` (not `Qwen/Qwen3.8-27B-FP8`). Stamp `20261006-212041`, from `qwen38-flash-latency-summary.txt`: thinking-on p50 98.9 s, p95 164.5 s, max 198 s, n_all_pass 14/20 (S1 4/5, S2 4/5, S3 4/5, S4 2/5; mean 6.2 tool calls). Thinking-off p95 82.9 s, n_all_pass 0/20, 7 `turn cap` errors. The 60 s p95 gate was missed. Xiaohui is pinning this model anyway and will explore other models later. Thinking-on is the mode that produced the passes. Thinking-off is not usable. The Qwen 3.5 measurement in M1.T4 is unchanged. Evidence: `evidence/M1/M1.T15/od8-pin.md` and the decision section of `evidence/M1/M1.T4/od8-decision.md`.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: recorded the Qwen3.8 pin, deferred Bonsai, and started M1.T5.

## 2026-10-07 — M1.T6 floor pictures

The camera USB was unplugged. M1.T6 is not done. The step 14 floor check is a pass. Do not start M1.T7 until the rest of the M1.T6 acceptance items are met.

- **USB.** Spark `lsusb` at 2026-10-07T05:10:07Z had no `0843:5740`. The FIREPHX by-id link was absent. The serial port was not opened. Nothing was flashed, reset, or commanded on `/led`. No motor or tilt command was published. `vllm-rosa` and Isaac were not stopped.
- **HTTP.** `GET http://192.168.4.24/status` returned 200: UXGA 1600×1200, quality 10, `rssi_dbm` −67, `uptime_ms` 44856, `frames` 0. Saved on the Mac as `evidence/M1/M1.T6/floor-status.txt`.
- **Frames.** Three `GET /capture` calls, 2 s apart, HTTP 200, `X-BM-Seq` 1, 2, 3. `floor-1.jpg` 316572 bytes, `floor-2.jpg` 315379 bytes, `floor-3.jpg` 315347 bytes, each 1600×1200, `ffd8`…`ffd9`. Copies are on the Spark and the Mac under `evidence/M1/M1.T6/pictures/`, and on the Mac Desktop at `beaconmind-camera/`. Review: `pictures/floor-review.md`, last line `verdict: pass`. The board, USB lip, and ribbon do not cover the center or the lower-middle. One column edge falls about 120 gray levels in two pixels. No frame is a black or white clip.
- **Not committed.**

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-07, captured the floor JPEGs and wrote the review and this entry.

## 2026-10-07 — M1.T5 AprilTag spike, lifetime measured, OD7 awaiting approval

M1.T5 is not done. Xiaohui has not approved the Isaac version.

The kept Isaac 5.1 render is `data/renders/spike-20261007-001302` on the Spark (`READY 6.8`, `DONE`). UXGA 1600×1200, HFOV 60°, asset-server AprilTag MDL. Offline decode (`evidence/M1/M1.T5/detect-offline.csv`) got id 3 in 4 of 4 frames, ranges 0.5020 / 1.0032 / 1.5129 / 2.0340 m. `apriltag_ros` on the 1.0 m frame returned id 3 (`apriltag-ros-on-render.txt`). The launch and the publisher were stopped. Isaac 6.0 was not built; `v6.0.1` is in `isaac6-tags.txt`.

Kit lifetime (`evidence/M1/M1.T5/kit-lifetime.md`): both 900 s holds reached `DONE` with exit 0. Base kit: `READY 6.7`, last `ALIVE 906.7` (tmux `bm-m1t5-life` finished, log mtime 2026-10-07 00:30:49 -0500). ROS-bridge kit, Humble `rclpy`, UDP-only DDS: `READY 7.1`, last `ALIVE 907.1` (tmux `bm-m1t5-ros` finished, log mtime 2026-10-07 00:47:08 -0500). Self-kill was not reproduced in 900 s. Jazzy was not sourced.

OD7 proposes Isaac Sim 5.1.0-rc.19 for M2 (`od7-decision.md`). That file does not contain Xiaohui's approval. The status row stays `in-progress`.

- **Left running.** `beaconmind-ros` is up. `vllm-rosa` and `qwen38-flash` stayed exited. Nothing was `docker rm`'d. The ESP32 serial port was not opened. No Isaac kit was left running. tmux `bm-m1t11` was already present and was not used.
- **Not committed.**

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: recorded the Qwen3.8 pin, deferred Bonsai, and started M1.T5.
AI-assisted: Grok 4.7 via Cursor, 2026-10-07: finished both kit-lifetime runs and wrote the evidence notes. The model did not approve OD7.

## 2026-10-07 — OD7 Isaac 5.1 approved

On 2026-10-07 at 00:51 CT Xiaohui approved OD7. Their words: "Yes, keep 5.1 for the simulator work."

The approved version is Isaac Sim 5.1.0-rc.19 (`5.1.0-rc.19+main.0.aa503a9b.local`), already installed. Isaac 6.0 stays unbuilt.

M1.T5 is done. The acceptance items were already on disk: `mdl-parameters.txt` lists the MDL identifiers; `detect-offline.csv` has id 3 in 4 of 4 with each range within 5 percent; `apriltag-ros-on-render.txt` has id 3; `kit-lifetime.md` records both 900 s runs at `DONE` with exit 0 (launch-to-READY 6.7 s and 7.1 s). The approval is in `evidence/M1/M1.T5/od7-decision.md`. The status-row note is `OD7 approved 2026-10-07: Isaac Sim 5.1.0-rc.19`.

M2 was not started. Isaac 6.0 was not built. The camera and API keys were not touched.

- **Not committed.**

AI-assisted: Grok 4.7 via Cursor, 2026-10-07: recorded the Isaac 5.1 approval.

## 2026-10-07 — Python 3.10 tests

The deferred M1.T2 contract tests passed in `beaconmind-ros` on spark-2a60. Container Python is 3.10.12. The README L4 command was `docker exec beaconmind-ros bash -lc 'cd /workspace/course-project/beaconmind && python3 -m pytest -q'`. The log is `evidence/M1/M1.T2/pytest-py310.txt`. Its last line is `40 passed in 0.26s`. The container was already up, so the image was not rebuilt. `vllm-rosa` and `qwen38-flash` stayed exited. M1.T7, M1.T8, M1.T9, M1.T10, M1.T12, and M1.T13 were not started. The M1.T11 evidence folder, the secrets file, and the camera serial port were left alone. Nothing was committed.

AI-assisted: Grok 4.7 via Cursor, 2026-10-07: ran the deferred 3.10 tests.

## 2026-10-07 — M1 overnight sweep (no hardware, no API)

M1.T6 stays `in-progress`. UXGA HTTP capture, the floor-review `verdict: pass`, and the USB-unplugged check are already on disk. The level reading, the h/d ruler photo, and several named acceptance files are not. Gaps: `evidence/M1/M1.T6/overnight-gaps.md`. M1.T7 was not started.

M1.T11 moved from `todo` to `in-progress`. The K=1 quality note does not meet the acceptance list. The $5 cap was already lifted for that run. The budget-guard demonstration was never run, and it was not run in this sweep. Gaps: `evidence/M1/M1.T11/overnight-gaps.md`.

M1.T7, M1.T8, M1.T9, M1.T10, M1.T12, M1.T13, M1.T14, M1.T15, and M2 were not started. The camera, vLLM, Isaac, and the secrets file were not touched. Nothing was committed.

AI-assisted: Grok 4.7 via Cursor, 2026-10-07: checked the M1 acceptance lists against evidence already on disk and wrote the gap notes.

## 2026-10-07 — Opus 5.5 K=5 comparison

Xiaohui approved a 1-1 comparison of `claude-opus-5-5` against the Qwen3.8-Flash-Next thinking-on smoke (stamp `20261006-212041`). M1.T11 stays `in-progress`.

- **Run.** tmux `bm-m1t11-opus20` on spark-2a60, one client, 4 scenarios × K=5. Adaptive thinking (field omitted) and `output_config.effort=medium`. Exit 0 at 2026-10-07T01:31:13-05:00. vLLM was not started. The camera was not touched. `beaconmind-ros` stayed up. The one-off container `bm-opus20` was removed when the run exited.
- **Result.** n=20, p50 18.8 s, p95 21.8 s, max 22.2 s, n_all_pass 20/20 (S1–S4 each 5/5), mean tool calls 5.75, n_errors 0. Qwen thinking-on remains p50 98.9 s, p95 164.5 s, n_all_pass 14/20. Evidence: `evidence/M1/M1.T11/opus20-comparison.md`.
- **Not committed.**

AI-assisted: Grok 4.7 via Cursor, 2026-10-07: ran the 20-decision Opus comparison.

## 2026-10-10 — M1.T9 `car.json` and M2.T4 URDF generator (both blocked)

M1.T9 and M2.T4 are `blocked`, not done (plan README §1.2 step 4 and §1.4; first recorded as `in-progress`, corrected
after a review the same morning). M1.T9 is blocked on Xiaohui: the remaining work is bench work (§1.4 item 1) and
his decisions on the recorded deviations (§1.4 item 8). M2.T4 is blocked on its prerequisites M1.T7 (todo), M1.T9
(blocked) and M2.T3 (todo), and on the camera.json convention conflict below; its package was built ahead and runs.
Evidence: `evidence/M1/M1.T9/` and `evidence/M2/M2.T4/` (each has a `README.md`).

- **What was measured.** Xiaohui measured the car on 2026-10-10 for the Module 6 Gazebo lab (`assignments/assignment6/measurements.csv`, reviewed in `assignments/assignment6/review/MEASUREMENT-REVIEW.md`; unchanged copy `evidence/M1/M1.T9/measurements-xiaohui-chen-2026-10-10.csv`). One ruler/tape reading per quantity and a two-scale weighing. Key numbers: tyre diameter 67 mm (direct, unloaded, **not** a roll-out), tyre width 27 mm, track 133.5 mm wheel centre to wheel centre (outer 160 / inner 107), front overhang 138 mm (ESP32-CAM USB-C side, **no cable**), rear overhang 77 mm, body width 150 mm (the rear wing), main body height 36 mm, caster contact x 100 mm ("around"), caster diameter 25 mm, lens (120, 0) mm and 75 mm above the floor, BNO055 board centre (−61, +20 = robot LEFT) mm with its top 60 mm above the floor (26.5 mm above the axle), mass 506 g (142 g caster + 364 g drive wheels), sweep radius 0.140 m.
- **`configs/car.json`** (`bm.car/1`) is valid: `python -m beaconmind.schemas car ../configs/car.json` printed `OK ../configs/car.json (1 objects)`. It is written by `course-project/tools/write_car_json.py` from the evidence CSV and `evidence/M1/M1.T9/measured.json` (the `measured` block with the deviations); `beaconmind/tests/test_car_model.py::test_configs_car_json_is_the_writer_output` fails if `car.json` is edited by hand. Every value is `status: "measured"` with an uncertainty (2 mm ruler, 5 mm "around", 1 g per scale reading; at least 3 mm for every x measured from the axle line, review #15, so B1, B2, B3 `front_overhang_m`, B4 `rear_overhang_m` and S1 x `imu_x_m` carry 3 mm while the "around" rows keep 5 mm; 4 mm for B5b; root-sum-square for derived values; every rule constant is in SI units, so template rows typed in m or kg get the same uncertainty). `lens_z_m` is a height above the **floor** (M1.T7 step 8's camera `z_m`); `imu_z_m` is the board top above the **axle** midpoint, 0.0265 m (M1.T9 step 3: "from the axle midpoint"), derived from the 60 mm floor reading minus the 33.5 mm wheel radius. The URDF's `base_link` is at axle height. Omitted, not invented: `rollout_left_m`/`rollout_right_m`, per-wheel diameters, encoder counts, `imu_axes`. Blank template for the next measuring session: `course-project/tools/car_measurements_template.csv` (plan key names; the writer reads it, including an `imu_axes` text row).
- **M1.T9 still needs:** three readings per quantity (or Xiaohui accepting the single readings), the 5-revolution roll-out (or accepting the direct diameter), encoder counts per wheel revolution (postponed: they need the Pico; Xiaohui to confirm whether they move to M3.T3), the photos `car-top.jpg`, `car-side.jpg`, `imu-orientation.jpg` with nothing personal in frame (the lab photos show the desk and screens, so they were not copied), and `imu_axes`. **Two more decisions for Xiaohui** (README deviations 7 and 8): (7) `chassis_length_m`/`chassis_width_m`/`chassis_height_m` hold the main body (0.215 × 0.150 × 0.036 m), not the whole-car bounding box M1.T9 step 3 defines (0.160 m wide over the tyres, about 0.100 m tall to the camera-stand top), because the URDF body box and M2.T3's `body_width_m` use the body; this is also a plan inconsistency (M1.T9 vs M2.T3/M2.T4). (8) `corners` and `sweep_radius_m` (0.140 m, set by the plate-front corners) assume the ESP32-CAM and the plate's front strip are centred on y = 0; only their widths were measured. `derived-dv-proposals.md` proposes `done_range_m` 0.588 ± 0.003 m (placeholder 0.55) for M1.T10; `dv.json` was not changed.
- **URDF.** `ros2_ws/src/beaconmind_description/beaconmind_description/gen_props.py` writes `urdf/car_props.xacro` from `car.json` (and `camera.json` once it exists); never edit that file by hand. It reads `car.json` through `load_car_standin()`, a stand-in for the M2.T3 view `beaconmind.config.load_car`; when M2.T3 lands, switch `build_view()` to it. Geometry `car.json` does not carry (plate outline, part boxes, stand-in part masses, centre-of-mass inputs) is hand-written in `urdf/car_geometry_extras.xacro`. `beaconmind_car.urdf.xacro` includes both and stops if `chassis_height` disagrees with `battery_top_h − lowest_body_h`.
- **Expanded URDF unchanged.** `course-project/sim/isaac/assets/beaconmind_car.urdf` (xacro output, 17 KB, pulled back to the Mac). `evidence/M2/M2.T4/urdf_diff.txt`: 214 elements and 406 numbers compared with the pre-change expansion, 0 mismatches (only the main file's header comment changed); the Module 6 lab wrapper expands byte-identically before and after, so the lab's screenshots still match the model. Tool: `course-project/tools/urdf_compare.py`. Re-checked after the second review's fixes (`urdf_diff.txt` section E, 08:32): the description expansion is still byte-identical to `sim/isaac/assets/beaconmind_car.urdf` (`81a7d617…`) and numerically identical to the pre-change one; the lab wrapper expands byte-identically from the pre-session, previous and current package (`2cc877fb…` from one fixed path). After the third review's fixes (section F, 09:04; extras comments only): the description is still byte-identical (`81a7d617…`), and the lab wrapper, copied this time from the current `module-6-gazebo-sim/urdf/gazebo_car.urdf.xacro`, expands byte-identically from the pre-session, round-3 and current package (`92eff3de…`; 434 numbers, 0 mismatches).
- **Tests.** `colcon test` in `beaconmind-ros`: 18 passed, 1 skipped (`test_optical_frame_matches_camera_json`, no `camera.json`); `colcon test-result`: 19 tests, 0 errors, 0 failures, 1 skipped (same after the review fixes, 08:02 CDT). After the second review's fixes (08:33 CDT, domain 141; re-run 08:37 after the last file sync, same result): 19 passed, 1 skipped; 20 tests, 0 errors, 0 failures, 1 skipped. That round's new test, `test_gen_props_camera_labels_follow_the_extrinsics_used`, never skips (it writes its synthetic camera.json files in a temporary folder). The skipped test is `test_optical_frame_matches_camera_json`: it skips **only** while `configs/camera.json` is absent; once the file exists it compares the TF with the extrinsics (`z_m − wheel_radius`, full rpy) and **fails** until `CAMERA_CONVENTION_SETTLED` in `test/test_urdf.py` is set after Xiaohui settles the convention (checked with synthetic camera.json files: `evidence/M2/M2.T4/camera_json_test.txt`). After the third review's fixes (09:04 CDT, domain 141): 19 passed, 1 skipped; 20 tests, 0 errors, 0 failures, 1 skipped (`colcon_test.txt` (f)); with a calibrated synthetic camera.json, regenerated props and the flag set, the whole suite gives 19 passed, 1 skipped, the skip then being `test_optical_frame_pose_from_measurements` (`camera_json_test.txt` case 7). `beaconmind` pytest after the review fixes: Mac 53 passed; `beaconmind-ros` (Python 3.10) 53 passed; after the second review's fixes: Mac 55 passed, `beaconmind-ros` 55 passed; after the third review's fixes: the same 55 on both. TF smoke test: `tf2_echo base_link camera_optical_frame` = (0.120000, 0.000000, 0.041500) m, RPY (−90, 0, −90)° = the measured lens with the mount angles assumed 0 (no `camera.json`).
- **pytest plugin issue (container).** `beaconmind-ros` has pip pytest 9.1.1, which rejects Humble's `launch_testing` pytest plugin (`PluginValidationError … {'path'}`), so `colcon test` exactly as M2.T4 step 8 writes it gives `1 test, 1 error`. Run it as `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 colcon test --packages-select beaconmind_description`. The lasting fix belongs to the M1.T3 image (set the variable in the compose file or pin a pytest Humble's plugins accept); the image was not changed.
- **sdformat-12 material bug (from the Module 6 lab, kept in the shared URDF).** Gazebo Fortress's URDF-to-SDF step (sdformat 12) resolves a by-name `<material>` only for the first `<visual>` of a link, so later visuals turned black; every visual now carries its inline `<color>` (`test_every_visual_has_inline_colour`). Related: sdformat's converter drops `<gazebo reference>` friction for a link whose `<collision>` has a `name`, so the wheel and caster collisions stay unnamed.
- **Plan conflict for Xiaohui (README §1.4 item 8), before M1.T7 fills `camera.json`:** M1.T7 step 8 defines `extrinsics.z_m` as the lens height above the floor, but M2.T4 puts `base_link` at axle height and expects the TF z to equal `z_m` (33.5 mm apart). M1.T7 step 9 also records small mount angles where M2.T3 expects the full base_link → optical rotation. `gen_props.py` treats `z_m` as a floor height and refuses camera angles beyond ±20°. The `chassis_*` meaning (deviation 7 above) is the second plan inconsistency for Xiaohui.
- **Left running / Spark state.** Nothing from this task is running now. `robot_state_publisher` (domain 47, `ROS_LOCALHOST_ONLY=1`) was stopped at the end of the build. **Correction:** this entry first said "nothing new is running", but the end check (`pgrep -af "robot_state_publisher|tf2_echo|ros2 launch"`) missed the **ROS 2 CLI daemon** that step 9's `ros2` calls had started in `beaconmind-ros` at 07:34 (pid 1682, `ros2-daemon --ros-domain-id 47`, `ROS_LOCALHOST_ONLY=1`). A review found it; it was stopped at ~07:52 with `ros2 daemon stop` (same domain) and `docker exec beaconmind-ros pgrep -af ros2` then found nothing (`evidence/M2/M2.T4/daemon_stop.txt`). Dead entries remain: `tf2_echo` (pid 1645) and the stopped daemon (pid 1682) are `<defunct>`; the container's PID 1 is `sleep infinity`, which never reaps orphans (two older `python3` zombies, pids 313 and 919, predate this session). **Host daemon (update, second review):** a second `ros2-daemon` on the Spark host (pid 308295, domain 87, started 06:08 from `/tmp/bmcheck` by a host-Jazzy check of `beaconmind_description` from this Mac) was recorded as running at 07:52; it had **exited by about 08:15 CDT** (the reviewer's host `ps`), and a host check at 08:24 (`pgrep` for `ros2cli.daemon`/`ros2-daemon`: none; `/proc/308295` gone) confirmed no ros2 daemon on the host. Nothing to stop; the earlier "stop it" action is withdrawn (`evidence/M2/M2.T4/daemon_stop.txt`, update at the end). The only ROS-related host entry is pid 357075 `[tf2_echo] <defunct>`, the container's zombie 1645 seen from the host. Zombies use no CPU and hold no DDS participant; they go away when the container restarts. `init: true` in `course-project/docker/docker-compose.yml` would reap them (an M1.T3 image/compose change, not made here). `beaconmind-ros` was already up and stays up. colcon outputs are under `ros2_ws/build`, `install`, `log` (git-ignored). Spark-only scratch: `course-project/data/m2t4-lab/` (lab-wrapper comparison inputs and the guard test copy), `data/m2t4-round2/` (the review re-check: expansions, colcon output, the synthetic camera.json cases), `data/m2t4-round3/` (the second review's re-check: expansions, the lab-wrapper copy, colcon and pytest output), `data/m2t4-round4/` (the third review: synthetic inputs and their script, package copies per case, expansions, `before.txt`/`b2a.txt`/`after.txt`/`lab2.txt`) and `data/m2t4-description-launch.log`. The third review started no ROS node (xacro, colcon build/test and pytest only); its end check found no ROS process on the host and only the old zombie 1645 in the container. A stray `course-project/log/` made by a `colcon version-check` run from the container's working directory was removed. For about two minutes the Spark copy had a guard written with `abs`, which xacro does not provide, so xacro failed then; fixed to `math.fabs`. No hardware, Pico, camera, vLLM, Isaac or other container was touched.
- **Sync.** The changed paths were synced Mac → Spark with tar (sha256 identical on both sides); Spark-written evidence and the expanded URDF were pulled back with scp in this session.
- **Review fixes (same morning, ~07:50–08:10).** A review of this entry found seven defects; all were verified and fixed: the leftover daemon above; `imu_z_m` changed from floor height to axle-relative (`write_car_json.py`, `gen_props.py`; the expanded URDF is **byte-identical**, sha256 `81a7d617…`, and the Module 6 lab wrapper expands byte-identically from the original, previous and new package, `evidence/M2/M2.T4/urdf_diff.txt` section D); the `chassis_*` meaning recorded as deviation 7; the camera.json test given its comparison; statuses set to `blocked`; the missing step-2 template written; the writer's docstring and the B1/B2/B4 override text corrected and the corners' centring assumption named in `car.json` (`corners`/`sweep_radius_m` `source`) as deviation 8.
- **Second review (~08:20–08:40).** Six defects, all verified and fixed: (1) `write_car_json.py` multiplied its mm/g uncertainty overrides by the row's unit factor, so a template row typed in m or kg got an uncertainty 1000× too large (`car.json` was unaffected: the SI-unit fix alone rebuilt it byte-identical); the constants are now SI, and tests cover m/kg rows and compare the template build's uncertainties (three stated differences, all from the word "around" in the 2026-10-10 notes); (2) `gen_props.py` labelled the camera values "configs/camera.json extrinsics" whenever the file existed, even with null extrinsics (which M1.T7 writes until its step 8); `extrinsics_used()` now decides per x/y/z and per angles, with a test; (3) the 3 mm axle-datum floor now covers every axle-line row, so `front_overhang_m` and `imu_x_m` are ±0.003 m, `chassis_length_m` ±0.0042 m and `done_range_m` 0.588 ± 0.003 m (`car_props.xacro` changed in comments only); (4) the M2.T4 status row no longer calls the expanded URDF byte-identical to the pre-change one (numerically identical; the lab-wrapper expansion is the byte-identical one); (5) the host-daemon record above; (6) the Module 6 pointers below.
- **Third review (~08:55–09:10).** Four defects, all reproduced on the Spark in `beaconmind-ros` (scratch `data/m2t4-round4/`) and fixed: (1) `test_optical_frame_pose_from_measurements` always compared the optical frame with the 2026-10-10 ruler lens readings and required camera rpy 0, so the documented route to done (camera.json → `gen_props.py` → flag `True`) gave `1 failed, 19 passed`; it now leaves out the x/y/z and/or angles that `gen_props.extrinsics_used()` takes from camera.json and skips when all six come from it (`camera_json_test.txt` cases 6–9); (2) the measurement-based URDF tests read only `assignments/assignment6/measurements.csv` under its 2026-10-10 row names, so a `car.json` rebuilt from the template failed them (8 `KeyError`s; with a roll-out, 4 failures); they now read the CSV that `car.json`'s `evidence` fields name, through `write_car_json.read_csv` and `ROW_FOR_KEY`, with the roll-out diameter when both roll-outs exist, and the lever-rule test reads the extras' source CSV (`measurement_csv_test.txt`; CSV-derived expectations are compared within 2e-6 m, `MEAS_TOL`, because `car.json` and the xacro each round to 1 µm); (3) the URDF's departures from M2.T4 step 5 were not recorded (next bullet), and the `car_geometry_extras.xacro` comment credited the camera 10 g and IMU 5 g stand-ins to "project defaults, M2.T4" (they are the Module 6 guide's; comment-only fix, expansion byte-identical); (4) the "Tests." bullet named the wrong test as the one that skips (reworded above). Found on the way: the Spark's mirror of `assignments/assignment6/lab-step10/gazebo_car.urdf.xacro` is older than the Mac's (its header AI note only), and sections B, D2 and E2 of `urdf_diff.txt` expanded that copy; same model (`urdf_diff.txt` F3). It was not re-synced, because the lab files are outside this task.
- **URDF deviations from M2.T4 step 5, for Xiaohui (`evidence/M2/M2.T4/README.md`; kept as they are so the Module 6 lab's model does not change):** (1) `chassis_link` is 12 boxes at the measured heights (gearbox bottoms 3.5 mm below the axle, plate 11–14 mm above it, camera stand up to 66.5 mm), not one `body_width` × `chassis_height` box with its bottom at the axle; (2) chassis mass 0.421 kg, not step 5's 0.436 kg, because the camera (10 g) and IMU (5 g) stand-ins sit on their own links, with a 0.208 × 0.100 × 0.036 m inertia box at the chassis centre of mass that gives the whole car the lever-rule centre of mass; (3) `camera_link` and `imu_link` carry those inertials (Module 6 guide defaults; step 5 gives none); (4) wheel joints rpy (−π/2, 0, 0) with axis 0 0 1 (the same +y spin axis as step 5's axis 0 1 0); (5) sphere wheel collisions (Module 6 guide §5.1); (6) visual-only caster fork and camera-module boxes. The total mass, the C1 frames and every joint position are as step 5 says.
- **Module 6 lab note: stale pointers to `car_props.xacro` (not edited).** Splitting the hand-written props moved the reviewed plate outline, part boxes, part masses and the centre-of-mass inputs (`caster_swivel_x` 0.120 from C3, `caster_load` 142 g, `com_x`) into the hand-written `car_geometry_extras.xacro`; `car_props.xacro` is now generated from `car.json`. `assignments/assignment6/derived-values.md` line 3 ("Superseded … by the reviewed values in `…/car_props.xacro` (… COM x 33.7 mm from the 120 mm pivot, the 151 mm wing reading is not used)") and the header comment (line 14, "through car_props.xacro") of `assignments/assignment6/lab-step10/gazebo_car.urdf.xacro` and its copy `module-6-gazebo-sim/urdf/gazebo_car.urdf.xacro` (identical on the Mac; the Spark's `lab-step10` mirror is older by its header AI note) still point at `car_props.xacro` alone. They are lab deliverables, so they were not changed; Xiaohui (or the lab owner) should make them read "car_props.xacro (generated from car.json) + car_geometry_extras.xacro (hand-written)". The wrapper's line 105 (wheel_separation/wheel_radius from car_props.xacro) is still right, and comment edits do not change the expanded model. Details: `evidence/M2/M2.T4/README.md`.
- **Next.** Xiaohui: decide deviations 1–3, 7 and 8 (`evidence/M1/M1.T9/README.md`), the six M2.T4 step-5 deviations above (accept, or have the plan text changed) and the camera.json `z_m`/angle convention; fix the two Module 6 pointers above if the lab files are edited again. M1.T7 calibration at the bench, with all six extrinsics in `camera.json`, then `gen_props.py` again and set `CAMERA_CONVENTION_SETTLED` per the decision; colcon should then give `20 tests, 0 errors, 0 failures, 1 skipped`, the skip being `test_optical_frame_pose_from_measurements` (with the flag still `False`, or with null angles, `test_optical_frame_matches_camera_json` fails by design). The rest of M1.T9 at the bench with the template: keep the filled CSV in `evidence/M1/M1.T9/` (`car.json` names it and `test_urdf.py` reads it from there; no test edit needed), run `write_car_json.py` and `gen_props.py`, and **hand-edit `car_geometry_extras.xacro` in the same session** for every re-measured row it uses (list in the M2.T4 README; only B9/B10 and a new total mass are caught by a check). M2.T3 (`load_car`).
- **Not committed.**

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-10-10: wrote `car_model.py`, `write_car_json.py`, `test_car_model.py`, `gen_props.py`, `car_geometry_extras.xacro` (moved the reviewed values and comments), the edits to `beaconmind_car.urdf.xacro` and `test_urdf.py`, `urdf_compare.py`, generated `configs/car.json` and `car_props.xacro`, ran the M2.T4 steps, and wrote the evidence notes and this entry; later the same morning applied the review fixes listed above (including `tools/car_measurements_template.csv`) and re-ran the checks; then applied the second review's fixes (SI uncertainty constants and the axle-datum floor in `write_car_json.py`, `extrinsics_used()` in `gen_props.py`, their tests, the regenerated `car.json`/`car_props.xacro`/`derived.txt`, the evidence and plan-row corrections) and re-ran the writer, the schema check, both pytest suites, colcon and the before/after expansions; then applied the third review's fixes (`test_urdf.py`: the camera parts taken from camera.json left out of the measured-pose test, and the measurement tests reading the CSV `car.json` names through `write_car_json.py`'s reader; the stand-in-mass comments of `car_geometry_extras.xacro`; the step-5 deviation list; the template's keep-the-copy note; `measurement_csv_test.txt`, `camera_json_test.txt` cases 6–9, `colcon_test.txt` (f), `urdf_diff.txt` F) and re-ran colcon, both pytest suites and the expansions. The measurements are Xiaohui Chen's.

## 2026-10-11 — Module 6 sim-to-real drive lessons (read before M3.T3, M3.T4, M3.T8, and the twin's actuator model)

Full record: [`research/2026-10-11-sim-to-real-drive-lessons.md`](research/2026-10-11-sim-to-real-drive-lessons.md)
(sources: `discussions/module6/`, the agent logs in `assignments/assignment6/module-6-gazebo-sim/sim-to-real/logs/`).

- **Pico firmware now:** the instructor's Module 6 drive image (`/pico2w_drive`: `/pico/cmd_vel` in;
  `/pico/imu/heading`, `/pico/imu/pitch`, `/pico/drive/status` out; 0.5 s command timeout; encoders not read) with
  two changes in `drive_control.c`: the wheel remap `tb6612_set(-right_duty, -left_duty)` and calibrated constants
  `MIN_DUTY 0.36`, `MAX_WHEEL_SPEED_MPS 0.20`, `WHEEL_SEPARATION_M 0.134` (consistent fit 0.39/0.215; slip documented).
  Its micro-ROS Agent ran as the `micro-ros-agent` container of the Module 6 Gazebo compose project.
- **Channel A drives the right wheel** (camera end = front), verified with the IMU; the wiring documents say left.
  Encoder sides are unverified.
- **Open loop is not enough:** with the instructor's constants a 40 cm command gave 20 cm and a 180° turn 143°;
  two calibrations reached ≈40 cm and 189° at 0.08 m/s, but a left veer of +1° to +30° per move remains. Straight and
  pivot loads need separate duty→speed lines; short-move averages understate steady speed.
- **Evaluation lesson:** the filmed route ended ≈21 cm out (±3 cm), close to Gazebo's 20 cm, but 40° off in heading: report heading error.
- **Agent-safety lesson:** ROSA(ros_version=2) adds shell-backed built-in tools (`ros2_param_set`, `ros2_service_call`); restrict the
  tool list in code (research note F10).
- **Open items** O1–O6 in the research note (veer cause, encoder mapping, steady-state speed and battery, pivot
  translation, untested consistent constants, short-move losses). Pack voltage not metered this session.
- **Power state at the end of the session (2026-10-11 ~03:10 CDT):** on the floor on battery, VSYS jumper IN, USB out;
  Xiaohui to switch the battery OFF (not confirmed).


## 2026-10-16 — plate outline from a classmate's CAD (car.json + URDF rebuilt; wheels unchanged)

A classmate shared (with the instructor's permission) an Onshape STEP model and an A3 drawing of the Emo
chassis plate, for the Module 7 odometry lab's "correct the measurements" step. Kept with notes and tools in
`the private course repo (plate CAD is not published here)` (README there: what a STEP file is, every dimension, the checks).

- **It is this car's plate.** A plane homography from 16 CAD features to the bottom-view photo `IMG_7436` fits to
  1.34 px rms (≈ 0.25 mm). On that photo the wing depth is **34.0 mm** (CAD 34.35; the 2026-10-10 ruler reading was 40,
  already flagged by review #7). The front of the plate is hidden on the photo and is not photo-checked.
- **New evidence CSV** `evidence/M1/M1.T9/measurements-2026-10-16-with-plate-cad.csv`: the 2026-10-10 CSV unchanged plus
  superseding rows. CAD (±0.5 mm allowance): width 147.92, strip 100, wing depth 34.35, front arc R135.14 and R8 corner
  fillets (new rows P1/P2). Fit: B1 130.49, B2 = B4 76.49 mm (the two ruler readings fitted to the CAD length 206.98).
- **car.json** (rebuilt by `tools/write_car_json.py`, which gained a CAD uncertainty rule and the rounded plate-front
  corners): `chassis_width_m` 0.14792, `rear_overhang_m` 0.07649, `chassis_length_m` 0.21449, plate-front corners
  (0.1229, ±0.0447) instead of (0.131, ±0.050), `sweep_radius_m` 0.1402 → **0.140** (now the caster swung forward;
  no centring assumption). **Unchanged:** wheel diameter 0.067 (direct, unloaded), tyre width 0.027, track 0.1335,
  caster, camera, IMU, heights, mass. The CAD has no wheels; the instructor's 2.5 in / 5 in / 1 in (Module 7 guide,
  2026-10-13 lecture in Granola) are the nominal course robot, not measurements of this car.
- **URDF:** `car_props.xacro` regenerated; `car_geometry_extras.xacro` plate rows hand-edited (CAD/fit labels);
  `beaconmind_car.urdf.xacro` draws the rounded front (3 slices) and snaps plate-slice boundaries to a 2 µm grid (the
  first colcon run caught a 1 µm wing-slice overlap). New test `test_plate_outline_matches_measurements`; `test_car_model.py`
  +8 tests, and `test_configs_car_json_is_the_writer_output` now follows the CSV/date `car.json` names.
  `sim/isaac/assets/beaconmind_car.urdf` regenerated (sha256 `d0b2ffbf…`): only plate boxes and chassis iyy/izz changed.
- **Tests:** Mac `beaconmind` 63 passed; `beaconmind-ros` Python 3.10 63 passed; colcon 21 tests, 0 failures, 1 skipped
  (camera.json). Logs: `evidence/M1/M1.T9/plate-cad-2026-10-16/`.
- **For the Module 7 lab (not the project):** the plate does not enter odometry. The real-robot constants stay
  D 0.067 m and L 0.1335 m as the starting point; the lab's own steps measure CPR (step 7.5) and the effective D and L
  (step 9.2: do the 360° spin after restarting with the new D, or use L_new = L_old·(A/360)·(D_new/D_old)).
- **Spark:** files synced by tar (the Spark copies matched git HEAD first). Scratch `course-project/data/m7-plate-cad/`.
  No ROS node or daemon started; the only ROS process in `beaconmind-ros` is the old `tf2_echo` zombie (pid 1645).
  Containers seen running: `beaconmind-ros`, `gazebo-sim`, `micro-ros-agent`, `qwen38-flash` (not touched).
  The Module 6 lab wrapper includes this URDF, so a re-run of that lab would show the new plate.
- **Not committed.**

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-10-16: analysed the CAD files and the photo, wrote the reference
folder and its tools, the writer/geometry/test changes, the new CSV rows, the xacro edits, ran the builds and tests,
and wrote this entry. The CAD files are a classmate's; the 2026-10-10 readings are Xiaohui Chen's.
