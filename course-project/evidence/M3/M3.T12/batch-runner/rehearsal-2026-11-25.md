# Rehearsal of the first real batch (rule R1), 2026-11-25

The first real B2 batch's command, run on the simulated car (`--dry-run`) on the Spark through `tools/car_batch.sh`,
with the real arguments: the measured world `configs/arenas/real-room.json`, the tag pilot's
`configs/detector_noise.json`, the real-run design values `configs/dv-real.json`, range limit 3.0 m, the scenario
starts S1 to S5 twice, and the initial pose where Xiaohui put the car for the practice run (2.369, 2.206, −90°: on
the tag pilot's line, facing T03). Run twice: r1 at commit `5086391` (the fix-statistic change), r2 at `cfa3948`
(the range check, below), each plain and with the measured heading drift. Logs (step lines left out):
`rehearsal-2026-11-25-logs.txt` (r1), `rehearsal-2026-11-25-r2-logs.txt` (r2).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: ran the rehearsals and wrote this note.

```bash
A="--world course-project/configs/arenas/real-room.json --scenarios course-project/configs/arenas/real-room-scenarios.json \
   --initial-pose 2.369,2.206,-90 --episodes 10 --policy b2 --max-range 3.0 \
   --detector-noise course-project/configs/detector_noise.json --dv course-project/configs/dv-real.json --dry-run"
bash course-project/tools/car_batch.sh b2-real-01-dry-r2 run $A --out course-project/data/batches/b2-real-01-dry-r2-20261125
python3 course-project/evidence/M3/M3.T12/batch-runner/rehearse_drift.py 3.4 run $A \
   --out course-project/data/batches/b2-real-01-dry-r2drift-20261125      # host venv; the measured heading drift added
# (r1: label b2-real-01-dry, out ...-r1-20261125 and ...-r1drift-20261125)
```

## The start poses in the measured world

From `configs/arenas/real-room.json`'s driving area and `configs/car.json`'s footprint (MoveGuard, sigma 0.05 m):

| Pose | Axle inside the driving area | Room for a circle (axle depth − 0.178 m sweep) | Turn / forward allowed | Tags within 3.0 m |
| --- | --- | --- | --- | --- |
| initial, README (2.20, 2.00, 90) | 1.54 m | 1.36 m (the first circle needs 0.83) | yes / both | 16 |
| initial, this rehearsal and the practice run (2.369, 2.206, −90) | 1.45 m | 1.27 m | yes / both | 16 |
| S1 (2.50, 1.50, 90) | 1.32 m | 1.14 m | yes / both | 15 |
| S2 (1.75, 1.40, 0) | 1.09 m | 0.91 m | yes / both | 13 |
| S3 (2.60, 3.90, −90) | 1.21 m | 1.03 m | yes / both | 11 |
| S4 (1.50, 4.00, 45) | 0.84 m | 0.66 m | yes / both | 11 |
| S5 (2.25, 2.60, 180) | 1.57 m | 1.39 m | yes / both | 18 |

All valid. S4 has the least room and the fewest tags (it is the corner where the 2.5 m dry runs halted).

## Results

| Run | Simulated car | Batch | Episodes | Moves | Steps per episode | Transit scale check | Episode scale check (new) | Guard refusals | `tag_survey` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| r1 | as configured (car.json's scales, no drift) | complete, exit 0 | 10 of 10 (9 DONE, S4's second ran its 150 steps) | 1,564 | 43–150 | 0.994–1.005 (9 checked) | 0.998–1.004 (8 checked) | 0 | none |
| r1drift | + 3.4° left at the end of every forward straight, −3.4° every backward one (151 moves, +513°) | complete, exit 0 | 10 of 10 (all DONE) | 1,457 | 48–102 | 0.997–1.003 (10) | 0.994–1.005 (10) | 0 | none |
| r2 (`cfa3948`) | as r1 | complete | the same ten episodes as r1 (the range check only watches) | 1,564 | 43–150 | as r1 | as r1 | 0 | none |
| r2drift (`cfa3948`) | as r1drift | complete | the same ten as r1drift | 1,457 | 48–102 | as r1drift | as r1drift | 0 | none |

The range check in r2 (tags over odometry, median over the batch's straight moves so far, at each episode's end):
0.998 to 1.003, finally 0.998 over 103 straight moves and 173 range pairs; r2drift 1.000 to 1.008, finally 1.002
over 83 moves and 131 pairs. Limit 1 ± 0.12.

Both: the sigma sources agree (`dv-real.json` and the fix sigma from the same `detector_noise.json`, sha256
`68ff4796…`); all 20 tags compared and trusted by the end; start-pose miss up to 0.20 m and 17°, inside the
tolerance; B2's final pose error against the batch's pose 0.00 to 0.06 m. The simulated clock ran 33 and 31 minutes for
the ten episodes, a floor for the real batch (frames, links and settling make it longer).

**Which represents the real car:** r1drift. The floor check measured a left turn of 2.6 to 4.5° at every straight move
whatever its length (`../../M3.T6/floor-check.md`), the gyro reports it, and the simulated car's own model (wheel
gains under the heading hold) does not produce it (at most 0.75° per move). It costs nothing here: the odometry carries
the turn, so the tracked pose stays right, and B2 re-aims after every look.

**What neither represents:** the real camera's bearing errors. The tag pilot found a bearing error that runs from +3.3°
at 0.79 m to −1.6° at 3.1 m, and `detector_noise.json` carries 1.86° of bearing sigma; the simulated camera has 0.3°.
That is what made the real practice run (`data/batches/practice-01b` on the Spark) halt `odometry_scale` at −23 % with a
correct odometer: one single-tag fix about 3 m away landed 0.21 m behind the tracked pose after a 5 cm leg (five turns),
and the old statistic (the sum of the innovations over the sum of the legs) let that one fix decide
(`practice-01b/`). Commit `5086391` replaced it by a weighted least-squares estimate that halts only beyond 12 %
**and** three standard errors (on practice-01b's numbers: −10 % ± 22 %, no halt) and added the same check as the
transit's over each episode, between its start and end circles; but that alone no longer caught the review's injected
25 % error in every seed. Commit `cfa3948` added the check that does: the ranges to the tags seen before and after
each straight move, which the camera measures well and the bearing errors barely touch. On practice-01b's six
straight moves it says 0.92 to 1.03 per move, median 0.96 (no halt at any move); every injected 25 % error, short or
long, halts on it. The real practice batch's own ranges are the evidence that it holds on the real car; the next
practice run is the first live test.

## Not rehearsed

- The real camera's bearing pattern and its occasional 0.1–0.2 m single-tag fixes (above).
- The real car's turns not being in place (the axle moves about 1.3 cm forward per 30°), which the simulated car does
  not do; the odometry reports it.
- Links, frames and the recorder (a dry run has none).
