# b2-real-02, 2026-11-25: the halt in the S3 transit, a physical slip

The second real B2 batch (`data/batches/b2-real-02` on the Spark, commit `490fedb`, 12:04:56 to 12:24:02 UTC;
recorder session `20261125-060452-batch-b2-real-02`).

- **Episode 1** (S1): ended DONE after 56 steps, final pose error 0.03 m.
- **Episode 2** (S2): ended DONE after 62 steps, final pose error 0.20 m.
- **The halt:** in the transit to S3, on the per-step fix statistic: `odometry_scale: tag fixes land -28 % (+-8 %) of
  the distance from where the odometry puts the car (10.5 m driven, 37 fixes; limit 12 %)`. The car stopped and the
  project latch was set.

The latch stays set: the halt is physical. Xiaohui's slip test (below) has since measured the cause. Every number below comes from the
batch's text records, copied read-only from the Spark (no frames), by `analyse.py` (output `analyse-output.txt`).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: analysed the records and wrote this note and `analyse.py`.

**Verdict: physical.** On northward moves the car covers markedly less ground than its wheels count, and the shortfall
grew during the batch. This is wheel slip, or something on the floor. It is not the encoder scale and not a software
fault. The per-step statistic measured it correctly; it only blamed the wrong cause.

## The slip, by heading and by time (the range check, the pilot's range bias removed)

| Forward moves measured | n | Tags over odometry |
| --- | --- | --- |
| episode 1, heading north (30° to 150°) | 1 | 0.94 |
| episode 1, other headings | 9 | mean 0.97 (0.79 to 1.04) |
| episode 2, north | 3 | mean 0.90 (0.86 to 0.94) |
| episode 2, other headings | 8 | mean 0.94 (0.87 to 0.98) |
| episode 3 transit, north | 4 | mean 0.85 (0.82 to 0.91) |
| **all north** | 8 | **median 0.88** |
| **all other** | 17 | **median 0.97** |
| whole batch | 25 | median 0.938 (limit 1 ± 0.12; no halt) |
| last 10 moves | 10 | median 0.904 (limit 0.88; no halt yet, falling) |

**The motion itself did not change:**

| | FORWARD_25 moves | Mean duration | Mean peak speed |
| --- | --- | --- | --- |
| episode 1 | 7 | 2.83 s | 0.118 m/s |
| episode 2 | 20 | 2.81 s | 0.122 m/s |
| episode 3 | 14 | 2.74 s | 0.124 m/s |

The wheels turned as before; the car went less far.

**The S3 transit, between its two circles** at (2.46, 1.34) and (2.50, 2.60):
- 8 northward FORWARD_25 (1.96 m by odometry) and 122 turns.
- **1.90 m by odometry, 1.26 m by the circles (ratio 0.663)**, a miss of (−0.12, −0.64) m.
- Taking the forward moves at 0.70 of their odometry closes the miss to 0.09 m. The gyro (×1.009) and the turns'
  axle shift do not close it.

**The dead-reckoning drift records:**

| Stretch | Ratio | Miss | Heading |
| --- | --- | --- | --- |
| episode 1 transit | 1.151 | 0.099 m | +9.4° |
| episode 1 | 1.191 | 0.134 m | +10.4° |
| episode 2 transit | 0.872 | **0.459 m** | +9.5° |
| episode 2 | 0.732 | **0.325 m** | +12.6° |

**The halting statistic, replayed:** −27.3 % ± 8.1 % over 10.5 m and 37 fixes, exactly what the batch reported.
- 65 % of it came from the S3 transit. Its largest single part was a T10 fix after a 0.74 m blind northward leg,
  which put the car 0.295 m short.
- Next came T00 fixes (the desk tag, to the west, about 2.6 m away) after each 0.49 m northward leg, putting the car
  0.19 to 0.29 m short.
- Single-tag fixes seen across the motion also carry the tracked heading's error, which inflates the shortfall's size
  but not its sign. The circles confirm the shortfall.

## The suspected floor area

**x 2.4 to 3.0 m, y 1.4 to 2.7 m** (arena frame; y grows toward the doors wall), and northward travel in general.

- **Where the moves were flagged:** the first northward FORWARD_25 of the S3 transit (rows 17 and 18, at x 2.48,
  y 1.57 to 1.82) were flagged `slip_suspected`, with wheel/gyro yaw disagreements of 11.2° and 12.5°; the unflagged
  straights show 0.3° to 9.9°, median about 3°. The third flagged move was the first straight of episode 2's transit (14.7°).
- **The same band as b2-real-01:** its slip was a northward FORWARD_25 near x 2.95, y 1.4 to 1.9 (yaw disagreement
  16.7°, range check 0.88), `../b2-real-01/`.
- **The trend over time:** the decline on non-northward moves (0.97 to 0.94 within 10 minutes) also points at the
  wheels themselves: lint on the tyres, a tyre slipping on its hub, or grip.

## The slip test (Xiaohui, 2026-11-25, recorder session `20261125-064330-slip-test`)

**Setup:** 4 × FORWARD_25 each way on the tag pilot's centre line (x ≈ 2.37 m). The lens position was read on the tape
ticks: distance from the baseboard under T03, perpendicular to the 295 cm wall, good to about ±2 cm. Recomputed by
`slip_test.py` (output `slip_test-output.txt`) from the session's move logs with the floor check's F4 geometry: the
lens is 0.12 m ahead of the axle, and the axle's chord is taken as an arc turning by the gyro's angle.

| Run | Lens (along the line) | Across, to the car's left | Gyro | Odometry | Axle path (arc) | True over odometry |
| --- | --- | --- | --- | --- | --- | --- |
| north, away from T03 | 2.00 → 2.75 m | 0.135 m | +12.10° | 0.9764 m | 0.7621 m | **0.780 ± 0.020** |
| south, toward T03 | 3.00 → 2.00 m | 0.135 m | +11.83° | 0.9718 m | 1.0104 m | **1.040 ± 0.021** |

**What the wheels did:**
- **Northward**, the left wheel counted more than the right on three of the four moves (5,129 against 4,448 at most),
  while the gyro said the car turned left by 2.4° to 3.4° each time. The left wheel turned more than the car moved.
- **Southward**, the counts follow the turn (the right wheel ahead), as on the floor check.
- **Inspection:** Xiaohui found nothing unusual on the wheels or the floor.

**Conclusion (the lead's, and these numbers agree):** travel on this carpet depends on direction (its pile). The
encoder scale was calibrated southward (F4 drove toward the 295 cm wall). This is a property of the floor, not a
fault. The range check's split in b2-real-02 (north median 0.88, other headings 0.97) shows the same thing more
mildly, because its "north" spans 30° to 150°.

## What the batch runner does with it (the version after b2-real-02, not used by it)

**Limits by physical risk:**
- **Farther than counted (dangerous):** the car going farther than its odometry says is the dangerous direction,
  toward a wall ahead. It keeps its tight limit: the range check at +12 % (15 % on the first move); the per-step fix
  statistic at +12 % beyond three standard errors.
- **Less far than counted (safe):** allowed down to a floor: the range check's median to **0.65**, the per-step
  statistic to **−35 %**. The measured slip is 0.78 taped northward and 0.82 to 0.94 by ranges, so 0.65 leaves 0.13
  below the worst real value. A factor-two error (0.50) still halts.
- **Dead-reckoning drift:** its gross bound is now 1.6 above and 0.5 below. The real car reached 0.73 over episode 2
  and 0.66 between the S3 transit's circles.

**What a 35 % under-travel does between fixes:**
- **The tracked pose runs ahead.** The blind cap stops a straight run at 0.75 m by odometry, which at 0.65 is 0.49 m on
  the floor. So the tracked pose can run up to 0.26 m ahead of the car, along its heading.
- **Walls ahead and turns stay safe.** Toward a wall ahead that errs on the safe side: the guard sees the car nearer
  the wall than it is. For a turn, the car's true position lies between the last fix and the tracked pose. The guard
  allowed a turn at the end of every straight. The area where a turn fits is convex (the driving area is convex, and
  the desk lies outside it), so the sweep circle also fits at every point between.
- **A backward move stays inside the margin.** A BACKWARD_10, offered only right after a FORWARD_10, takes the car
  about 2.6 cm behind its start at 0.78 forward and 1.04 back: inside the 0.15 m wall margin.
- **The next fix still lands.** A 0.26 m gap stays inside what a fix may differ by (three combined sigmas plus 5 cm:
  about 0.28 m for a 5 cm fix, more for a single far tag). No real batch has had a fix refused as far from the
  tracked pose.
- **The tracker's sigma understates the error.** The odometry noise of 5 % of the distance driven understates a
  22 % slip. That error lies along the motion and in the safe direction, but the stated sigma is too small northward.

**The cost:**
- **Wrong scales that now pass:** an odometer reading up to 35 % long (the car covering 0.65 to 0.88 of what it counts)
  no longer halts as a wrong scale. In fault injection, four-episode batches with odometers 25 % and 35 % long
  completed in both rooms, 3 of 3 seeds each. The simulated car stayed at least 0.39 m inside the driving area, with
  no contact.
- **Wrong scales that still halt:** an odometer reading 25 % short halts in every run, as before.

**Rehearsed on a simulated carpet:** `../rehearse_slip.py` (log `rehearse_slip-7a8b599-log.txt`).
- **The slip model:** the simulated car's true travel is scaled by 0.91 − 0.13 sin(direction of travel): 0.78
  northward, 1.04 southward, 0.91 east and west. Its wheels count the full distance.
- **The run:** the exact real arguments at `7a8b599`. It completed, 10 of 10 episodes done, 1,602 moves.
- **The slip by heading recorded in the manifest** recovers the pattern. The range check's medians over the 45°
  sectors:

  | Sector | Median | Moves |
  | --- | --- | --- |
  | north (90°) | 0.80 | 15 |
  | 45° | 0.84 | 14 |
  | east (0°) | 0.94 | 19 |
  | south (270°) | 1.08 | 4 |

  The south figure is the batch removing a range bias that the simulator does not have, about +1.6 %.
- **The drift measurements:**

  | Measurement | Value | Limit |
  | --- | --- | --- |
  | per-step drift | −16 % ± 4 % | −35 % |
  | dead-reckoning ratios, transits | 0.78 to 1.04 | 0.5 |
  | dead-reckoning ratios, episodes | 0.86 to 1.08 | 0.5 |

- **The tracked pose** ended within 0.003 to 0.027 m of every end circle, and B2's final errors were 0.003 to
  0.071 m.

**An option for Xiaohui, not implemented:** correct the odometry by heading, for example forward distance ×
(0.78 + 0.26 × sin² of the angle from north) fitted to the slip test and the ranges. That would remove most of the
northward drift that misled B2 in episode 2, but it changes the odometry every agent sees. That is a design change for
the study, to decide before any batch whose results are compared, not a safety fix.

## Episode 2's 0.20 m final error

**The truth is sound:**
- the truth at that step was a tag fix (σ 0.058 m);
- the end circle (14 tags, rms 0.026 m) put the tracked pose within 0.077 m.

**B2's own estimate drifted:** 0.10 m at step 16 (its third FORWARD_25), 0.17 m at step 31, about 0.20 m from step 40
on, always too far south in the map frame. B2 believed odometry that over-reports on this floor. That is the agent's
result and is reported as such.

## Physical checks

- **Moves:** all 442 `done`; stall 0, bump 0; `slip_suspected` on 3 moves (above).
- **Car state:** telemetry age at most 0.058 s; agent receive age at most 1.0 s; cutoffs 0; boots 0;
  `lost_samples` 1; `vsys_min_mv` 4,708 (the Pico's supply; the motor pack's voltage is not measured).
- **Frames:** 5 frames at every step, none truncated by size.
- **Corrupt JPEGs:** the log has 8 "Corrupt JPEG data" warnings, and they cost no detections. Only two frames lost
  every tag their four sibling frames saw (episode 1 pre row 3, episode 2 pre row 6), and both steps still reported
  those tags, because a tag needs 3 of the 5 frames.

## What changed in the batch runner (after this batch, not used by it)

The per-step fix statistic now halts only while the range check cannot vouch for the scale (`per_step_scale_halt`):
- **Gate open:** fewer than 3 measured forward moves, or the range check itself out of tolerance. Then the statistic
  halts as before. With the range check off, it remains the layer that halts a wrong encoder scale (the review; test
  `test_with_the_range_check_off_the_per_step_fixes_still_halt_a_wrong_scale`).
- **Gate closed:** otherwise the statistic is recorded (`per_step_drift` and `halt_held_back_by_the_range_check` in
  the manifest) and does not halt.
- **On this batch:** the gate would have held the 12:24 halt back (range 0.938 and 0.904, both inside ±0.12). The range
  window was falling toward its own limit, though, so the next northward moves would probably have halted the batch
  on the slip itself.
