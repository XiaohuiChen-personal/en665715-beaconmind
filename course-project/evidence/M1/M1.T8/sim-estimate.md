# M1.T8 — expected tag range and bearing error against distance: a SIMULATED estimate (2026-11-18)

**Everything in this file is simulated.** No tag has been in front of the real camera yet (the tags are printed, not
mounted). The numbers say what the detector does with pictures drawn through the calibrated camera model; they are an
estimate to plan with, not the tag pilot's result. The pilot (`PROCEDURE.md`) replaces them.

Script: `evidence/M1/M1.T8/sim_estimate.py` (40 frames per distance and condition, seed 20261118, OpenCV 5.1 on the
Mac; about 10 minutes). Raw output: `sim-estimate-output.txt`, `sim-estimate-image.csv`, `sim-estimate-calibration.csv`.

## What was simulated

- **Camera:** `configs/camera.json` as it is (XGA 1024 × 768, fx 1181.5, plumb_bob distortion, lens 0.12 m ahead of the
  axle midpoint and 0.075 m up, roll +4.4°, pitch −3.9°, yaw +2.5°). Pictures are drawn ray by ray through the lens
  distortion and the mount rotation (`beaconmind.perception.synth`), not warped with a flat homography.
- **Tag:** 160 mm tag36h11 with its 20 mm white border, IDs 0–29, on a wall, centre 0.23 m up; at a random bearing where
  the whole tag is in the picture, turned up to 30° on its wall. Below 0.8 m a wall tag is not whole in the picture
  (next section), so the rows marked * use a tag held low (centre 0.095 m), as a bench stand would hold it.
- **Picture quality, "real-like":** the levels measured from real `bm_cam-0.2` XGA frames of 2026-11-18 (six frames of
  the paper checkerboard at 1.03 m, room light at night): printed black about 100 and paper about 185 grey levels, edge
  blur 0.75 px, sensor noise 2 grey levels before compression (1.1 was measured after it), JPEG at libjpeg quality 62
  (the camera's quality-12 luma table is the standard table × 0.75, i.e. quality 62.5).
- **Detector:** `beaconmind.perception.tags.detect_tags` with its defaults; range and bearing from the axle midpoint in
  the floor plane (contract C1).

## Finding 1 — how close a wall tag can be seen (geometry, not simulation noise)

The lens is 7.5 cm up and looks 3.9° up; the picture reaches 17.8° above the optical axis. A wall tag's black square
tops out at 31 cm (33 cm with the white border). So:

| Tag's bearing | Whole black square in the picture from | With its white border from |
| --- | --- | --- |
| 15° right | 1.09 m | 1.30 m |
| 10° right | 0.80 m | 0.86 m |
| 5° right | 0.76 m | 0.82 m |
| straight ahead | 0.74 m | 0.79 m |
| 5° left | 0.72 m | 0.77 m |
| 10° left | 0.70 m | 0.76 m |
| 15° left | 0.81 m | 0.92 m |

(range from the axle midpoint; positive bearing = tag to the car's left; the left/right difference comes from the 4.4°
roll and 2.5° yaw.) **Straight ahead the minimum is 0.74 m (0.79 m with the border).** In the simulated pilot the
detector found the tag at 0.75 m and not at 0.70 m. This is above `done_range_m` (0.55 m) and `forward_wall_limit_m`
(0.35 m) in `configs/dv.json`, and above the simulator's 0.25 m minimum range: **on the real car a tag straight ahead
disappears about 0.75 m before the wall.** What would change it:

| Change | Whole black square from | With border from | Cost |
| --- | --- | --- | --- |
| as mounted (pitch −3.9°) | 0.74 m | 0.79 m | — |
| camera tipped up to −8° | 0.63 m | 0.67 m | re-seat the camera, redo M1.T7 step 9 (10 minutes); tags at 3.5 m stay in view |
| camera tipped up to −12° | 0.55 m | 0.59 m | same |
| camera tipped up to −15° | 0.50 m | 0.54 m | same |
| tag centre 0.20 m instead of 0.23 m | 0.66 m | 0.72 m | not possible above the 12 cm baseboard without trimming the page |

## Finding 2 — error from the picture alone (random, per frame)

"Real-like" pictures; error = detected − true; 40 frames per row:

| Range (m) | Tag side (px) | Detected | Range error: mean (mm) | sd (mm) | 95 % of frames within (mm) | Bearing error: sd (°) | 95 % within (°) | Quality (median) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.40* | 675 | 40/40 | -0.0 | 0.0 | 0.0 | 0.003 | 0.006 | 0.99 |
| 0.50* | 498 | 40/40 | -0.0 | 0.0 | 0.0 | 0.003 | 0.005 | 0.99 |
| 0.60* | 392 | 40/40 | -0.0 | 0.0 | 0.1 | 0.001 | 0.003 | 1.00 |
| 0.80 | 273 | 40/40 | +0.0 | 0.1 | 0.2 | 0.001 | 0.001 | 0.99 |
| 1.00 | 213 | 40/40 | +0.0 | 0.2 | 0.4 | 0.001 | 0.002 | 0.99 |
| 1.25 | 165 | 40/40 | +0.2 | 0.4 | 0.8 | 0.001 | 0.002 | 0.99 |
| 1.50 | 136 | 40/40 | +0.2 | 0.5 | 1.1 | 0.001 | 0.002 | 0.99 |
| 1.75 | 115 | 40/40 | -0.2 | 1.1 | 1.7 | 0.001 | 0.002 | 0.98 |
| 2.00 | 101 | 40/40 | +0.2 | 1.2 | 2.2 | 0.001 | 0.002 | 0.96 |
| 2.25 | 89 | 40/40 | +0.2 | 1.8 | 3.5 | 0.002 | 0.005 | 0.96 |
| 2.50 | 80 | 40/40 | -0.1 | 2.5 | 4.7 | 0.002 | 0.003 | 0.97 |
| 2.75 | 73 | 40/40 | -0.6 | 2.0 | 3.8 | 0.001 | 0.003 | 0.97 |
| 3.00 | 67 | 40/40 | +0.0 | 3.3 | 6.0 | 0.002 | 0.003 | 0.96 |
| 3.25 | 61 | 40/40 | +0.6 | 3.3 | 5.8 | 0.002 | 0.002 | 0.97 |
| 3.50 | 57 | 40/40 | +1.1 | 3.2 | 6.3 | 0.002 | 0.003 | 0.97 |
| 4.00 | 50 | 40/40 | +0.8 | 4.8 | 8.1 | 0.002 | 0.004 | 0.96 |
| 5.00 | 39 | 40/40 | +3.6 | 4.0 | 9.2 | 0.001 | 0.002 | 0.93 |
| 6.00 | 33 | 18/40 | -1.2 | 11.2 | 21.1 | 0.001 | 0.003 | 0.72 |
| 7.00 | | 0/40 | | | | | | |
| 8.00 | | 0/40 | | | | | | |

\* tag held at 0.095 m (a wall tag is not in view this close).

The tag is still 57 px wide at 3.5 m. The rows beyond 5 m are cut by the detector's own range rule (`max_range_m`,
6 m), not by the picture: with that rule lifted this tag is found in 95 % of frames out to 8.25 m, where it is 24 px
wide (section "Smaller tags" below). (Corrected 2026-11-18: this paragraph first read "detection stops between 5 m and
7 m (about 33 px)".)

Harder pictures (detected / frames; range error mean ± sd; bearing error sd; median quality):

| Range (m) | soft and noisy | still moving | tone curve | dim |
| --- | --- | --- | --- | --- |
| 0.8 | 40/40; +0.0 ± 0.1 mm; 0.001°; 1.00 | 40/40; +0.0 ± 0.1 mm; 0.000°; 1.00 | 40/40; +0.6 ± 0.1 mm; 0.001°; 0.99 | 40/40; +0.1 ± 0.2 mm; 0.002°; 0.70 |
| 1.0 | 40/40; +0.1 ± 0.2 mm; 0.001°; 0.99 | 40/40; +0.0 ± 0.1 mm; 0.001°; 0.99 | 40/40; +0.9 ± 0.2 mm; 0.001°; 0.99 | 40/40; +0.2 ± 0.5 mm; 0.002°; 0.70 |
| 1.5 | 40/40; +0.2 ± 0.4 mm; 0.001°; 0.99 | 40/40; +0.1 ± 0.5 mm; 0.001°; 0.99 | 40/40; +2.5 ± 0.5 mm; 0.002°; 0.99 | 40/40; +0.7 ± 1.5 mm; 0.002°; 0.70 |
| 2.0 | 40/40; +0.4 ± 0.9 mm; 0.001°; 0.98 | 40/40; +0.1 ± 0.9 mm; 0.001°; 0.98 | 40/40; +4.4 ± 1.3 mm; 0.002°; 0.97 | 40/40; +1.7 ± 2.9 mm; 0.003°; 0.71 |
| 2.5 | 40/40; +0.7 ± 2.1 mm; 0.001°; 0.98 | 40/40; +0.1 ± 1.8 mm; 0.001°; 0.98 | 40/40; +6.7 ± 2.0 mm; 0.002°; 0.96 | 40/40; +1.6 ± 4.9 mm; 0.003°; 0.69 |
| 3.0 | 40/40; +0.7 ± 2.7 mm; 0.001°; 0.97 | 40/40; +0.1 ± 2.2 mm; 0.001°; 0.97 | 40/40; +9.6 ± 3.1 mm; 0.002°; 0.96 | 40/40; +1.4 ± 6.1 mm; 0.004°; 0.66 |
| 3.5 | 40/40; +0.9 ± 4.0 mm; 0.002°; 0.97 | 40/40; +0.9 ± 3.3 mm; 0.001°; 0.98 | 40/40; +13.9 ± 3.8 mm; 0.003°; 0.97 | 40/40; +2.8 ± 10.2 mm; 0.003°; 0.63 |

- "soft and noisy": twice the blur and twice the noise. "still moving": a 5 px sideways smear. "dim": a third of the
  real contrast, with more noise.
- "tone curve": if the camera's brightness curve is non-linear (gamma 2.2), blurred edges shift toward the dark side and
  the tag reads slightly small: a range bias that grows with distance (+4 mm at 2 m, +10 mm at 3 m). The real
  camera's curve is not known; the pilot's bias line `range_bias_m` absorbs this.

## Finding 3 — error from the calibration (systematic: the same for a whole session)

Exact corner pixels, pose solved with one camera parameter off by its recorded uncertainty. Each cell: range error and
bearing error for a tag straight ahead (in brackets: for a tag 15° to the left):

| One parameter off by | Tag at 1 m | at 2 m | at 3 m |
| --- | --- | --- | --- |
| focal length +1 % (the two tape checks read -0.1 % and -1.2 %) | +9 mm, +0.02° (+8 mm, -0.10°) | +19 mm, +0.02° (+16 mm, -0.11°) | +29 mm, +0.02° (+25 mm, -0.11°) |
| principal point cx +5 px | 0 mm, +0.21° (+2 mm, +0.20°) | 0 mm, +0.23° (+4 mm, +0.21°) | -1 mm, +0.23° (+6 mm, +0.22°) |
| principal point cy +5 px | 0 mm, -0.02° (-1 mm, -0.01°) | 0 mm, -0.02° (-1 mm, -0.01°) | -1 mm, -0.02° (-2 mm, -0.01°) |
| distortion k1 and k2 set to zero (worst case for the picture's edges) | -2 mm, -0.01° (-13 mm, +0.06°) | -2 mm, -0.00° (-23 mm, +0.05°) | -2 mm, -0.00° (-34 mm, +0.05°) |
| mount yaw +2 deg (uncertainty_deg in camera.json) | 0 mm, +1.76° (-1 mm, +1.77°) | 0 mm, +1.88° (-1 mm, +1.89°) | 0 mm, +1.92° (-1 mm, +1.92°) |
| mount pitch +2 deg | +5 mm, +0.01° (+5 mm, -0.06°) | +4 mm, +0.01° (+4 mm, -0.03°) | +4 mm, +0.00° (+4 mm, -0.01°) |
| mount roll +2 deg | 0 mm, -0.19° (-1 mm, -0.19°) | 0 mm, -0.03° (-1 mm, -0.03°) | 0 mm, +0.03° (-1 mm, +0.02°) |
| lens position x +5 mm (uncertainty_m in camera.json) | +5 mm, +0.00° (+5 mm, -0.07°) | +5 mm, +0.00° (+5 mm, -0.04°) | +5 mm, +0.00° (+5 mm, -0.03°) |
| tag size given 1 mm too large (a 160 mm black square entered as 161 mm) | +6 mm, -0.00° (+6 mm, +0.01°) | +12 mm, +0.00° (+12 mm, +0.01°) | +18 mm, +0.00° (+18 mm, +0.00°) |

- **Range** is dominated by the focal length: 1 % of the lens distance. The two tape checks of M1.T7 read −0.1 % and
  −1.2 %, so 1 % is a fair bound.
- **Bearing** is dominated by the camera's yaw: its ±2° uncertainty goes straight into every bearing (about 1.9° at
  2 m). The pilot measures this bias and corrects `extrinsics.yaw_deg`; afterwards the bound is how well the car was
  squared to the wall during the pilot (about 0.4° with eight placements squared to 1°).
- The distortion row is a worst case (no distortion correction at all): about 1 cm per metre at 15° off axis. The
  calibration board covered only 46 % of the picture, so the left third and the top and bottom bands are extrapolated;
  the true error there is somewhere between zero and this row.

## The estimate

Root sum of squares of the rows that apply (focal length 1 %, lens position 5 mm, pitch 2°, tag size 0.5 mm, the
tone-curve bias, and the per-frame noise):

| Range | Range error (1 sigma) | of which focal length / lens position / pitch / tag size / tone curve / frame noise (mm) | Bearing error without the yaw term | With a 2° yaw error | dv.json sigma (range, bearing) |
| --- | --- | --- | --- | --- | --- |
| 1 m | **12 mm (1.2 %)** | 9 / 5 / 5 / 3 / 1 / 0 | 0.30° | 1.79° | 0.10 m, 2.0° |
| 2 m | **21 mm (1.1 %)** | 19 / 5 / 4 / 6 / 4 / 1 | 0.25° | 1.90° | 0.15 m, 2.0° |
| 3 m | **32 mm (1.1 %)** | 29 / 5 / 4 / 9 / 10 / 3 | 0.26° | 1.94° | 0.20 m, 2.0° |

`configs/dv.json` assumes range sigma 0.05 + 0.05 r (0.10 m at 1 m, 0.15 m at 2 m, 0.20 m at 3 m) and bearing sigma
2.0°. **In simulation the range error is about 1.1 % of the range, five to eight times smaller than the design value
at every distance, and the error at 3 m (about 3 cm) is smaller than the design value assumes at 1 m.** The bearing
error is inside the design value only once the pilot has removed the yaw bias: before it, a 2° yaw error alone uses the
whole 2.0° budget (10 cm sideways at 3 m).

## What this means for the 2.0 m range limit (`reject_range_above_m`)

- Nothing in the simulation gets worse between 2.0 m and 3.5 m except linearly: every tag is found, the per-frame
  noise is 3–4 mm at 3–3.5 m, the quality stays near 1, and the tag is 57 px wide at 3.5 m (it decodes down to about
  22 px).
- The agent's own association gate is 0.3 m and 15° (up to 0.6 m and 30°), far wider than these errors.
- **So the simulation supports raising the limit to 3.0 m (or 3.5 m) for real runs**, which matters in the room:
  `evidence/M3/M3.T10/layout/coverage.txt` (computed for a 60° view) gives one heading a tag in 42 % of samples at
  2.0 m and 69 % at 3.0 m; with the measured 46.9° it is less at every limit (rerun it at 46.9°).
- **Not shown by the simulation, and to be checked by the pilot's part E before deciding:** glare and uneven light on
  the paper, a page that is not flat, the lens's sharpness away from the picture centre, the distortion model outside the
  calibrated 46 % of the picture, frames taken before the car has stopped rocking (`obs_settle_s`), and corrupt frames
  (21 of the 10,233 XGA frames recorded so far are truncated JPEGs).
- The decision is Xiaohui's; the frozen study's `configs/dv.json` is not edited here.

## Smaller tags instead of tipping the camera (added 2026-11-18, simulated)

The camera stays as it is. The tags are printed but not mounted, so their size can still change. Each alternative is a
black square of side s with a white border of s/8, its sheet's bottom edge on the baseboard's top (0.12 m), so its
centre is 0.12 + 0.625 s up. Script `sim_tag_sizes.py` (40 frames per cell, about 2 minutes); raw output
`sim-tag-sizes-output.txt`, `sim-tag-sizes.csv`, `sim-tag-sizes-far.csv`.

**Near limit:** range from the axle midpoint from which the whole black square is in the picture (in brackets: the
whole sheet with its white border). The detector needs the black square and a few pixels of white around it, so the
usable limit lies between the two numbers.

| Black side | Centre height | Straight ahead | 10° left | 10° right | 15° left | 15° right |
| --- | --- | --- | --- | --- | --- | --- |
| 160 mm as printed (Letter sheet) | 0.230 m | 0.74 m (0.79 m) | 0.70 m (0.76 m) | 0.80 m (0.86 m) | 0.81 m (0.92 m) | 1.09 m (1.30 m) |
| 160 mm (sheet trimmed to 200 mm) | 0.220 m | 0.71 m (0.77 m) | 0.68 m (0.73 m) | 0.77 m (0.83 m) | 0.80 m (0.92 m) | 1.10 m (1.31 m) |
| 140 mm | 0.207 m | 0.65 m (0.70 m) | 0.62 m (0.67 m) | 0.71 m (0.76 m) | 0.74 m (0.84 m) | 1.01 m (1.19 m) |
| 120 mm | 0.195 m | 0.59 m (0.63 m) | 0.57 m (0.61 m) | 0.64 m (0.69 m) | 0.68 m (0.77 m) | 0.92 m (1.07 m) |
| 100 mm | 0.182 m | 0.53 m (0.57 m) | 0.51 m (0.54 m) | 0.58 m (0.62 m) | 0.62 m (0.69 m) | 0.83 m (0.95 m) |
| 80 mm | 0.170 m | 0.47 m (0.50 m) | 0.45 m (0.48 m) | 0.51 m (0.54 m) | 0.55 m (0.61 m) | 0.73 m (0.84 m) |

**Far behaviour** with real-like frames: detection rate; range error mean ± sd. For the last four columns the
detector's own 6 m range rule (`max_range_m`) was lifted, so the picture decides.

| Black side | 1.5 m | 2.0 m | 2.5 m | 3.0 m | 3.5 m | Detection at or above 95 % out to | Tag width there | 40 px wide at | 27 px wide at (quality 0.5) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 160 mm | 100 %; +0.2 ± 0.7 mm | 100 %; -0.4 ± 1.6 mm | 100 %; +0.2 ± 2.0 mm | 100 %; +1.5 ± 2.4 mm | 100 %; +1.3 ± 3.7 mm | 8.25 m | 24 px | 4.8 m | 7.1 m |
| 140 mm | 100 %; +0.1 ± 0.8 mm | 100 %; -0.1 ± 1.8 mm | 100 %; +0.1 ± 2.4 mm | 100 %; +0.5 ± 2.8 mm | 100 %; +0.7 ± 5.7 mm | 7.50 m | 23 px | 4.3 m | 6.2 m |
| 120 mm | 100 %; +0.1 ± 1.4 mm | 100 %; +0.6 ± 1.8 mm | 100 %; +0.9 ± 2.2 mm | 100 %; +0.1 ± 3.5 mm | 100 %; +2.1 ± 3.2 mm | 7.00 m | 21 px | 3.7 m | 5.4 m |
| 100 mm | 100 %; +0.3 ± 1.0 mm | 100 %; +0.4 ± 2.2 mm | 100 %; +0.9 ± 3.5 mm | 100 %; +1.5 ± 3.1 mm | 100 %; +1.1 ± 4.3 mm | 5.25 m | 24 px | 3.1 m | 4.5 m |
| 80 mm | 100 %; +0.1 ± 1.3 mm | 100 %; -0.2 ± 2.2 mm | 100 %; +2.3 ± 2.7 mm | 100 %; +1.3 ± 3.4 mm | 100 %; -0.8 ± 6.9 mm | 4.50 m | 22 px | 2.5 m | 3.6 m |

- Every size is found in every frame out to 3.5 m, and the per-frame noise stays under 7 mm. In simulation the code
  stops decoding at about 21–24 px of tag width whatever the size.
- The last two columns are where to be careful. Real pictures will be softer than the simulated ones somewhere (off
  axis, uneven light), and the quality value falls with size below 40 px and reaches the agent's rejection threshold
  (0.5) at 27 px. A tag that is 40 px wide at the range limit keeps the margin the 160 mm tag has at 4.8 m.

**Calibration-dominated error** (root sum of squares as in "The estimate"; parts: focal length 1 % / lens position
5 mm / pitch 2° / tag size 0.5 mm / tone curve / frame noise):

| Black side | Range error at 2 m (1 sigma) | parts (mm) | Range error at 3 m | parts (mm) | Bearing at 2 m / 3 m without the yaw term | with a 2° yaw error |
| --- | --- | --- | --- | --- | --- | --- |
| 160 mm | 21 mm | 19 / 5 / 4 / 6 / 4 / 2 | 33 mm | 29 / 5 / 3 / 9 / 11 / 2 | 0.25° / 0.26° | 1.9° / 1.94° |
| 140 mm | 22 mm | 19 / 5 / 3 / 7 / 5 / 2 | 34 mm | 29 / 5 / 3 / 10 / 13 / 3 | 0.25° / 0.26° | 1.9° / 1.94° |
| 120 mm | 22 mm | 19 / 5 / 3 / 8 / 5 / 2 | 34 mm | 29 / 5 / 2 / 12 / 11 / 4 | 0.25° / 0.26° | 1.9° / 1.94° |
| 100 mm | 23 mm | 19 / 5 / 3 / 9 / 7 / 2 | 36 mm | 29 / 5 / 2 / 14 / 14 / 3 | 0.25° / 0.27° | 1.9° / 1.94° |
| 80 mm | 24 mm | 19 / 5 / 2 / 12 / 8 / 2 | 39 mm | 29 / 5 / 2 / 18 / 18 / 3 | 0.26° / 0.27° | 1.9° / 1.94° |

- The range error barely changes with size, because the focal-length term (1 % of the distance) does not depend on
  it. What grows for a small tag is the share of a 0.5 mm error in its printed size (0.3 % for 160 mm, 0.6 % for
  80 mm) and of the tone-curve bias. The bearing error does not depend on the size.

**Reading the tables together** (simulated; the pilot must confirm whichever is chosen):

| Black side | Near limit straight ahead (black square) | Against done_range_m 0.55 m | Comfortable far range (40 px) |
| --- | --- | --- | --- |
| 160 mm | 0.71 m | not whole at 0.55 m (short by 16 cm) | 4.8 m |
| 140 mm | 0.65 m | not whole at 0.55 m (short by 10 cm) | 4.3 m |
| 120 mm | 0.59 m | not whole at 0.55 m (short by 4 cm) | 3.7 m |
| 100 mm | 0.53 m | whole at 0.55 m | 3.1 m |
| 80 mm | 0.47 m | whole at 0.55 m | 2.5 m |

- 100 mm is the largest size whose black square is whole at the 0.55 m done range straight ahead (0.53 m); 80 mm has
  margin there (0.47 m). No size reaches the 0.35 m forward wall limit: even with the 80 mm tag the last 12 cm before
  that limit are blind. (The 160 mm row is the sheet trimmed to 200 mm; as printed on the Letter sheet it is 0.74 m.)
- Off to the right the picture is cut earlier (roll and yaw of the mount): at 15° right even the 80 mm tag needs
  0.73 m.

**Mixed sizes.** `detect_tags` now takes the tag size per ID: `tag_size_m` (and `tag_center_height_m`) may be a dict
`{id: value}` with an optional `"default"` entry, for example `{**{i: 0.16 for i in range(15)}, "default": 0.10}`. A
tag whose ID has no size is rejected (`no_size`), never guessed. Test: `test_mixed_tag_sizes_by_id` in
`beaconmind/tests/test_perception_tags.py`. Two things to keep in mind for a mixed room: an ID must have one size
everywhere (the two tags that share an ID on purpose must be the same size), and a wrong size for an ID scales that
tag's lens distance by the size ratio without any other symptom, so the size table belongs next to the world file.

## Checks behind these numbers

- The detector's tests (`beaconmind/tests/test_perception_tags.py`, `test_camera_model.py`) pass with OpenCV 5.1 (Mac),
  4.13 (Spark host) and 4.5.4 (the `beaconmind-ros` container).
- The camera-to-base transform was checked against real frames: solving the checkerboard of the extrinsics session
  (`20261118-020555-calibration-extrinsics`, four frames) and moving it into `base_link` gives a board whose long axis is
  level within 0.1°, whose short axis is vertical within 0.2°, and whose centre is 2.4 cm right of the centre line (tape:
  2.5 cm) and 1.03 m from the lens (tape: 1.04 m).
- No false detection in real frames: all 10,233 XGA frames recorded on 2026-11-18 (none shows a tag) give no detection,
  accepted or rejected, at 6.2 ms per frame on the Spark host.
- The twelve pages of the print file, drawn as whole Letter sheets (text and scale bar included) at 0.85–3.5 m on a
  darker wall and on a wall as bright as the paper, are all read with the right ID (120 of 120 simulated frames).

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote the simulation and this note. No measurement in it is
Xiaohui Chen's except the real-frame levels it starts from, which come from frames recorded in Xiaohui Chen's sessions.
