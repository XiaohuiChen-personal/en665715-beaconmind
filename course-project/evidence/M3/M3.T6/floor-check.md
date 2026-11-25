# Floor check, 2026-11-25 (README section 5.2; work list 2.8; plan task M3.T8)

Session `20261125-030214-floor-check` on the Spark (recorder on; 03:02 to about 03:30 CST); operator Xiaohui Chen; the
car on the arena's carpet, the motor pack of the stand test, the drive map of the stand test (0.25 / 0.33, no restart
in between: `boots` 0 in the car state of F5). The runners were the lead agent's scratch scripts on the Spark; they and
their logs are copied unchanged into `floor-check-runs/` (provenance). Every number below was recomputed on
2026-11-25 from those logs and the session's bag by `floor-check-runs/floor_analysis.py` and `scale_geometry.py`
(outputs beside them) and `stand-test-runs/stopan.py`. No camera frame is in the repository.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: recomputed the numbers from the logs and wrote this record.
The check was run by Xiaohui Chen with the lead agent; the tape readings are Xiaohui's.

**Result: F1, F3, F5 pass; F2 marginal (the return leg); F4 replaced the encoder scales in `configs/car.json` (left
19,385, right 19,804 counts per metre); since checked once by tags (the first practice batch's transit: ratio
1.008), not yet by tape.** Straight moves turn the car
about 3.4° left each.

## Method: the wall tags instead of tape per step (Xiaohui agreed)

Instead of lifting the car back to a taped cross and taping every step, the car drove the sequence in one go and was
measured after every step by the camera: `tagmeas.py` waits 1.5 s, then takes the median range and bearing of each
tag over 10 frames. Here those are turned into a pose against `configs/arenas/real-room.json`: the position by least
squares on the **ranges** with the tag pilot's range bias removed (true = measured − (0.00492 − 0.01658 r)), the
heading from the bearings at that position. Ranges are good to millimetres (pilot: sigma 1.3 mm + 0.4 mm per metre
after the bias), so distances **along the line of sight** are good; the tags of this check all hang on one wall, so
the position **across** it rests on the narrow angles between them and is only good to about ±4 cm at 2 to 3 m
(compared with the tape below; the lead's first pose fixes, with bearings in them, were worse, about ±10 cm). One
tape reading (F4) settled the distance.

## F1: `FORWARD_25` four times (from 2.9 m in front of the 295 cm wall, toward it)

Pass criteria: `done`; from the third run on, the distance 0.25 m within 2 cm; the printed `achieved_forward_m` within
1 cm of it; heading change under 6°.

| Run | Result | Printed (nominal scale) | Counts L / R | Distance at the F4 scales | By the ranges | Heading: gyro / tags |
| --- | --- | --- | --- | --- | --- | --- |
| F1.1 | done | 0.2431 | 4,881 / 5,098 | 0.2546 | 0.267 | +3.76 / +4.24 |
| F1.2 | done | 0.2444 | 4,883 / 5,148 | 0.2559 | 0.278 | +3.69 / +3.51 |
| F1.3 | done | 0.2443 | 4,848 / 5,180 | 0.2558 | 0.255 | +3.11 / +3.00 |
| F1.4 | done | 0.2458 | 4,856 / 5,232 | 0.2573 | 0.266 | +3.41 / +2.72 |

Distance: pass (0.255 to 0.257 m by the counts at the measured scale; the range-based numbers carry the ±4 cm
sideways error). Heading: pass (under 4.3° each). The printed distance: **failed at the nominal scale** (1.1 to 1.2 cm
short every time): the nominal 20,524 counts per metre under-reported travel by 4 to 6 %, which is what F4 measured and
fixed. After F4 the printed distance is the counts at the measured scale by construction.

## F2: `FORWARD_10` then `BACKWARD_10 --prev-forward <achieved>`, three times

Pass criteria: forward 0.10 m within 1.5 cm; the car back within 1.5 cm of where it started.

| Cycle | Forward: printed / at the F4 scales | Backward printed | Net by the counts | Ranges to tags 1 and 9 after the cycle |
| --- | --- | --- | --- | --- |
| 1 | 0.0942 / 0.0987 | −0.0888 | +0.6 cm | −2.5 / −1.9 cm |
| 2 | 0.0945 / 0.0990 | −0.0836 | +1.2 cm | −2.7 / −3.0 cm |
| 3 | 0.0959 / 0.1004 | −0.0902 | +0.6 cm | −2.4 / −1.8 cm |

Forward: pass. Return: **marginal**. By its own odometry each backward leg stops 5 to 11 mm short of its forward leg
(the counts leave the car 0.6 to 1.2 cm ahead: inside 1.5 cm), but the camera sees the car 1.8 to 3.0 cm closer to
both tags after every cycle (ranges, bias-scaled; the position fixes put it 3.0 to 3.4 cm along), so it creeps forward
by more than the counts say, probably wheel slip when the direction reverses. Little depends on it: B2 offers
`BACKWARD_10` only right after a `FORWARD_10`, and the batch runner's tracked pose takes the next tag fix.

## F3: `TURN_LEFT_30` × 3, then `TURN_RIGHT_30` × 3

Pass criteria: each `done`; the three sum to 90° within 8; the gyro's sum within 4° of the measured angle.

| Set | Each (gyro) | Sum: gyro / tags | Pass |
| --- | --- | --- | --- |
| left | +29.51, +28.65, +29.03 | +87.19 / +88.94 | yes (1.1° from 90; gyro 1.75° from the tags) |
| right | −30.66, −28.47, −29.43 | −88.56 / −89.15 | yes (0.9° from 90; gyro 0.59° from the tags) |

The turns are not quite in place: the left wheel's counts are about half the right's (left −400 to −508, right +976 to
+1,006 per left turn), so the axle moves about 1.3 cm forward per 30° (the odometry reports it: +0.012 to +0.014 m).
The turn rate is above the design's 45°/s (README section 6, open item 3; unchanged).

## F4: the encoder scale

Pass criterion: the taped length of four `FORWARD_25` against the sum of `achieved_forward_m`, ratio 0.97 to 1.03;
the counts give `enc_ticks_per_m_left/right`.

**The tape-measured straight** (`scale4.sh`, `scale-031706.log`; what `configs/car.json` holds since commit `a9a2cf2`):

- Xiaohui put the camera lens over the tag pilot's 2.75 m tick on its centre line (ticks are measured from the
  baseboard under tag T03, perpendicular to the 295 cm wall), the car on the line facing the wall. Four
  `FORWARD_25`; then the lens was **1.83 m from the baseboard and 0.19 m left of the line** (tape).
- Counts: left 4,518 + 4,506 + 4,434 + 4,471 = **17,929**; right 4,675 + 4,746 + 4,781 + 4,674 = **18,876**; gyro
  2.88 + 2.64 + 2.97 + 3.64 = **12.13°** left.
- Geometry (line frame, x toward the wall): lens 0.12 m ahead of the axle, so the axle went from (−0.120, 0) to
  (0.92 − 0.12 cos 12.13°, 0.19 − 0.12 sin 12.13°) = (0.8027, 0.1648): chord **0.9373 m**; on a circular arc turning
  12.13° that is **0.9390 m**. With the track 0.1335 m the wheels travelled 0.9390 ∓ 0.0668 × 0.2117 rad: left
  **0.9249 m**, right **0.9532 m**.
- Scales: left 17,929 / 0.9249 = **19,385**, right 18,876 / 0.9532 = **19,804** counts per metre. Each centimetre of
  tape error moves both by 1.1 % (car.json states ±1 %, 194 and 198). Taking the chord as a straight line instead of
  the arc gives 19,422 / 19,840 (0.2 %).
- The ratio criterion, against what the car printed during that straight (its car.json then held the first estimate
  below): 0.9775 m printed, 0.939 m by the tape, **0.961: outside 0.97 to 1.03**; at the nominal scale the same counts
  print 0.897 m, ratio 1.047. Both are why the scale was replaced; with the new values the ratio is 1.000 by
  construction.

**The first estimate it replaced** (commit `75be6fa`, left 18,555, right 19,096): computed from wall-tag fixes before
and after F1's four straights. The same computation here, with the range-based positions above, gives 18,787 / 19,349
(F0 → F1.4) and 18,883 / 19,379 (over the tape-measured straight itself): 2 to 3 % below the tape values, because the
fixes overstate the sideways part of the path. Against the tape over that straight: the lens positions by the tags
are 0.7 cm and 0.4 cm off along the line, but 4.4 cm and 3.9 cm off sideways, in opposite directions, so the tags put
the sideways travel at 0.273 m where the tape says 0.19 m (`scale_geometry-output.txt`). Lesson (as in CONTEXT): tag
fixes are good along the line of sight and weak across it; measure a distance with a tape, or with the ranges to a
tag straight ahead.

**The verify run** (`verify.sh`, between the two estimates, car.json holding 18,555 / 19,096): two `FORWARD_25` printed
0.2433 and 0.2482 m, while their counts at the tape scales are 0.234 and 0.239 m, and the range to tag 1, nearly
straight ahead, fell by 0.230 m (0.233 bias-scaled) in the first: the first estimate made the car stop 1.1 to 1.6 cm
short per 25 cm, which is why the tape straight was driven.

**Checked since, by tags only:** the first real practice batch (`data/batches/practice-01b` on the Spark, created
09:33:34 UTC, with these scales: its pass marker of 09:23:46 UTC fingerprints car.json) measured its transit between
two full-circle fixes as 0.688 m by odometry and 0.694 m by the tags, ratio **1.008** (limit 10 % plus the fixes'
uncertainty). No taped straight has been driven with them. The same batch then halted `odometry_scale` at −23 %: a
false alarm of the batch runner's per-step statistic (one noisy single-tag fix after a 5 cm leg), fixed in commit
`5086391` (`../M3.T12/batch-runner/rehearsal-2026-11-25.md`).

## F5: STOP on the floor

SPACE during `FORWARD_25` at 09:10:20 UTC (`02-floor-F5-stop.log`): the latch at 09:10:21.826 (`by: bm_stop`), zero
commands at once, the car's duty 0 after **0.028 s**, the wheels still after **0.103 s**; after the key the wheels
turned 44 and 53 counts, **2.3 and 2.7 mm**. The move ended `link_lost` / `estop`. Pass (within about 5 cm).

## Heading drift on straight moves

Every straight move turned the car left, and about as much at 10 cm as at 25 cm, so it is a turn per move more than a
curvature: `FORWARD_25` +2.64 to +4.43° (ten moves, mean +3.41°), `FORWARD_10` +2.98 to +4.45°, `BACKWARD_10` −3.20 to
−3.64° (gyro; the tags agree within about 1°). The heading hold does not remove it (F1: under the 6° limit). The gyro
reports it, so the odometry the agent and the batch runner see carries it; what it changes is the path: the car does
not go where a straight line from its start heading points. The batch rehearsal of 2026-11-25 ran once with this turn
added to the simulated car (`../M3.T12/batch-runner/rehearsal-2026-11-25.md`).

## Open

- The final encoder scales have no taped check yet; one transit of the practice batch checked them by tags (1.008).
- F2's return leg overshoots by 2 to 3 cm per cycle by the camera.
- The left/right asymmetry (turns and straights) and the turn rate above 45°/s stay as they are (README section 6).
