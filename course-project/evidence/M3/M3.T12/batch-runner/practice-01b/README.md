# The practice batch's `odometry_scale` halt, 2026-11-25: a false alarm

Batch `practice-01b` on the Spark (`data/batches/practice-01b`, created 09:33:34 UTC; recorder session
`20261125-033329-batch-practice-01b`): one B2 episode at S1 on the real car, start taped at (2.369, 2.206, −90). The
first circle, the transit to S1 (start miss 0.03 m / 11°), the scan, five turns and two `FORWARD_25` ran; at step 19
the batch halted: `odometry_scale: tag fixes land -23 % of the distance from where the odometry puts the car (1.2 m
driven, 7 fixes; limit 12 %)`. The car stopped; nothing unsafe. The encoder scales were the floor check's tape values
(`../../../M3.T6/floor-check.md`, F4), which the batch's pass marker fingerprints.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: analysed the batch's text records (copied read-only from the
Spark; no frames) and wrote this note and the two scripts.

**Verdict: false alarm. The odometer was right.**

1. **The ranges along the motion** (`range_scale.py`, output `range_scale-output.txt`): for each of the six straight
   moves, every tag seen before and after it (positions in the car frame from the detector's own record,
   `detections_internal`), the range after the move against the range the odometry predicts. Tags over odometry per
   move 0.97, 1.03, 0.99, 0.95, 0.94, 0.92 (14 range pairs, 0.93 m driven), weighted mean **0.98**; with the tag
   pilot's range bias removed **1.00**. Ranges are what the camera measures best (pilot: millimetres), and a tag
   ahead of the car makes them insensitive to the bearing errors.
2. **The batch's own transit check** between two full circles, in the same batch: 0.688 m by odometry, 0.694 m by the
   tags, ratio **1.008**.
3. **What halted it** (`fix_statistic.py`, output `fix_statistic-output.txt`): the per-step statistic was the sum of
   each position fix's innovation along the leg driven over the sum of the legs. One single-tag fix of T02, about
   3 m away (sigma 0.12 m), landed 0.21 m behind the tracked pose after a 5 cm leg (five turns, each moving the axle
   about 1 cm), and took the statistic from +5 % to −24 %. (Replayed from the logged poses the statistic ends at
   −18 % over the same 1.23 m and 7 fixes; the batch's own −23 % used its internal pose before each fix, which the
   logs do not hold exactly.) Weighted by each fix's own noise the same fixes say −10 % ± 22 %: nothing.

**What changed in the batch runner** (`beaconmind/src/beaconmind/car/batch.py`, 2026-11-25, commits `5086391`,
`cfa3948` and the one after it): the encoder scale is now judged by the ranges along each straight move
(`range_scale_of_move`, `range_scale_halt`, `BatchEnv._range_check`):

- **Straight moves only:** a move counts when the odometry moved the axle 5 cm or more (a 30° turn moves it about
  1.3 cm, so turns add nothing).
- **Which tags:** seen once before and once after the move, within 30° of straight ahead both times (the camera sees
  ±23.5°, so on the car this is every tag in view), with both ranges inside the pilot's reliable window (0.785 m to
  `--max-range` 3.0 m; the pilot's 3.135 m is farther), weighted by how much the range says about the scale.
- **Repeated ids:** each detection is resolved to one surveyed tag by where the tracked pose puts it (the nearest
  surveyed tag of that id within 1 m, any other at least 1 m farther; the real room's repeated ids hang 2.28 to
  5.52 m apart); otherwise it is not used.
- **Range bias:** the tag pilot's model (measured − true = 0.00492 − 0.01658 r, `configs/detector_noise.json`) is
  removed first when the batch runs with `--detector-noise`, as every real batch must.
- **Halt:** the median over the straight moves so far, each move one estimate, off 1 by more than 12 %, and at least
  3 × 5 % / √moves: 15 % for the first move, 12 % from the second. N = 1: in the review's fault injection (8-tag
  room, 2.5 m, seed 3) only one straight move of the whole episode has a tag in view before and after, and the
  injected 25 % error shows there as 1.29; one move of the real car scatters 0.94 to 1.05 (practice-01b, range bias
  removed; SD 0.04), so 15 % is three of its sigmas from a correct odometer.

**practice-01b through the new check** (the batch's own code, `test_the_practice_batch_ranges_say_its_odometer_was_right`):
per move 0.989, 1.049, 1.003, 0.965, 0.955, 0.935 with the range bias removed, median **0.977**; no halt at any move.
The same batch's transit check read 1.008: 0.031 apart, 1.2 standard errors of the median (1.25 × 5 % / √6 =
0.026), and well inside the transit's own uncertainty (two circle fixes of about 5 cm over 0.69 m, about ±0.10).
Raw ranges (what `cfa3948` used) give median 0.961.

Kept: the transit check; the same check over each episode between its start and end circles; the per-step position
statistic, weighted by each fix's noise and halting only beyond 12 % and three standard errors. The review's fault
injection (an odometer reading 25 % short, 8-tag room at 2.5 m) is unchanged since `05f64c4` and halts 3 of 3; 25 %
short and 25 % long halt 3 of 3 in both the 8-tag and the 20-tag room, on the ranges; a correct odometer completes
(tests named in `../README.md`, the `odometry_scale` row).
