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

**What changed in the batch runner** (`beaconmind/src/beaconmind/car/batch.py`, 2026-11-25): the encoder scale is
now judged by the ranges along each straight move (`range_scale_of_move`, `range_scale_halt`: the median over the
moves so far must stay within 12 %, 15 % on the first move alone), besides the transit and, new, each episode
between its start and end circles. The per-step position statistic stays, weighted by the fixes' noise and halting
only beyond three standard errors. The review's fault injection (an odometer reading 25 % short, 8-tag room at 2.5 m)
is unchanged and halts in every seed; 25 % short, 25 % long and 15 % short halt in every one of five seeds in both
the 8-tag and the 20-tag room, on the ranges, the car at least 0.47 m from any wall; a correct odometer completes
(tests named in `../README.md`, the `odometry_scale` row). The practice batch's six moves replayed through the new
check: no halt at any move.
