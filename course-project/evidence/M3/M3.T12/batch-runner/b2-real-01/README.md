# b2-real-01, 2026-11-25: the halt after episode 1, and what it measured

The first real B2 batch (`data/batches/b2-real-01` on the Spark, commit `e3c8d0e`, started 11:22:41 UTC; recorder
session `20261125-052236-batch-b2-real-01`). Episode 1 (S1) ended by DONE after 83 steps. Then, after its end circle,
the batch halted: `odometry_scale: the episode (start circle to end circle) measures 0.72 m by odometry and 0.91 m by
the tags (ratio 1.27, limit 1 +- 0.18)`. The car stopped and the project latch was set. Every number below comes from
the batch's text records, copied read-only from the Spark (no frames), by `analyse.py` (output
`analyse-output.txt`).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: analysed the records and wrote this note and `analyse.py`.

**Verdict:** real dead-reckoning drift. It was not an encoder-scale error and not bad tag fixes. Odometry alone,
from the start circle, ended **0.27 m** from where the end circle put the car (0.00 m in x, −0.27 m in y; heading
13.4° off). The pose the batch tracked with a tag fix at every step ended **0.06 m** from the end circle. The halt
message's "the encoder scale in configs/car.json is wrong" was itself wrong.

## The evidence

1. **The encoder scale is right.** The range check (the batch's own code; the pilot's range bias removed) read
   tags over odometry per forward move 1.000, 0.993, 0.975, 0.948 (transit), then 0.939, 0.991, 0.882, 0.962,
   1.009, 1.006, 0.984, 0.930 (episode): median **0.980** over 12 moves and 19 range pairs. It never halted. The
   two path comparisons were the odd ones out: 1.14 over the transit and 1.27 over the episode.
2. **The circles are accurate.** The start circle fitted 14 tags with rms 0.023 m (sigma 0.026 m). The end circle
   fitted 9 tags with rms 0.023 m (sigma 0.024 m). Step fixes from many different tags (T02/T01, T03/T17/T02,
   T12/T18, T04, T16, T05, T06/T14, T18) agree with them and with each other within a few centimetres. So the 0.27 m
   is about ten times the circles' accuracy. It is not a fix error.
3. **Where the drift came from** (section 3 and 4 of the output):
   - **The turns' axle shift is not the cause.** Each 30° turn moves the axle about 1.2 cm by its encoders: left
     turns +1.22 cm forward, right turns −1.11 cm. The odometry carries that shift. Turns in place (shift removed)
     make the miss worse (0.31 m), and twice the shift changes it little (0.25 m).
   - **The gyro reads short, but that is not the cause of the position miss.** Dead reckoning ended 13.4° off in
     heading over about 1,700° of net rotation (0.8 %), and the transit 8.6° off over 1,380° (0.6 %). Scaling the
     turn angles to remove the heading miss leaves the position miss at 0.32 m.
   - **It starts at three northward FORWARD_25** (rows 24 to 26, heading about 83°, around x 2.95 m, y 1.4 to 1.9 m).
     Row 24 had a wheel/gyro yaw disagreement of **16.7°**; the other straights had 1.0 to 3.6°, and row 51 had 6.1°.
     Its encoders counted left 5,024 against right 4,560. The range check read **0.88** on it (T07 at 2.49 m), so
     the car went about 12 % less far than its wheels turned. Rows 25 and 26 had no tag in view. After them the
     fixes put the car about 0.12 m short in y. Taking rows 24 to 26 at 0.80 to 0.86 of their odometry explains 0.10
     to 0.15 m of the 0.27 m.
   - **The rest grew slowly:** −0.13 m by row 45, −0.17 m at row 51, −0.21 m at row 56, −0.23 m at row 78, and
     −0.27 m after the end circle's 12 turns. No single event stands out.
4. **The error is in the safe direction for a wall ahead.** Odometry over-reported the distance travelled, so the
   car was never farther along than it believed.

## What changed in the batch runner

- **The comparison is now a recorded measurement.** The transit's and each episode's start-circle-to-end-circle
  comparison is kept in the manifest as **dead-reckoning drift** (`dead_reckoning_transit`, `dead_reckoning_episode`;
  fields and the reason in `../README.md`). It halts only on a gross error: a length ratio beyond 1.6 either way,
  more than twice the largest real drift (1.27).
- **The scale is the range check's job.** The encoder scale is checked by the range check, on forward moves only,
  with a 10-move window as well (`dc67bce`).
- **The end pose comes first.** `end_pose_map`, `end_pose_world` and `final_pose_error` are written before any
  end-of-episode check. An episode that ended and was measured stays `done` when a later check halts the batch.
- **What is lost**, and what still protects the car, is written out in `../README.md` under "What is lost with it".

## Findings, no correction yet

**The gyro reads rotation 0.6 to 1.5 % short, most in the first minutes.**

| Where | Heading miss | Rotation | Share |
| --- | --- | --- | --- |
| episode | 13.4° | about 1,700° net | 0.8 % |
| transit | 8.6° | about 1,380° net | 0.6 % |
| first circle (refit, see below) | | | about 1.5 % |
| floor check F3, left turns (tags against gyro) | | | 1.9 % |

- **The first circle prefers a larger gyro scale.** Refitted with the gyro's turn angles × 1.015, the first circle's
  rms falls from 0.052 to 0.028 m. The same holds in practice-01b, which started from the same taped spot: 0.050 to
  0.028 m. The start circle is best at × 1.000 and the end circle does not care. That suggests the IMU settling
  during its first minutes.
- **A correction would change the odometry.** A gyro scale (or warm-up) correction would tighten dead reckoning and
  the first circle, but it is for Xiaohui and the lead to decide, after a measurement on the floor.

**The circle residual limit (`scan_rms_max_m` 0.08 m) is thin only at the first circle.**

| Circles | rms | Tags | Mean range |
| --- | --- | --- | --- |
| first: practice-01b, b2-real-01 (same taped spot) | 0.061, 0.062 m | 16 | 2.1 m |
| start: practice-01b, b2-real-01 | 0.024, 0.023 m | 15, 14 | 1.8 m |
| end: b2-real-01 | 0.023 m | 9 | 1.4 m |

- **The first-circle residual is systematic.** The same tags carry it in both batches: the w295 tags seen first
  (T12, T18, T03, T17) have dx +0.07 to +0.09 m, and T00, T01, T02, seen last, have dx −0.05 to −0.17 m. Most of it
  is the gyro above.
- **No change to the limit.** The data supports no change for the other circles, and the limit is left as it is.

## Episode 1 for the replay

Episode 1 is a complete real B2 episode:
- ended by DONE at 83 steps, `result.complete` true;
- step truth from tag fixes throughout;
- end circle fixed with 9 tags.

Its manifest entry, written by `e3c8d0e`, says `status: halted` and lacks `end_pose_map` and `final_pose_error`,
because the halt was raised before they were written. Commit `ab585ae` (not mine) lets `real_replay.convert_batch`
accept such an episode, one that ran to its end before a post-episode check halted the batch. With the change above,
a later batch records such an episode as `done`, with its end pose, in the first place.
