# b2-real-04, 2026-11-25: the halt at the start, on under-travel

The fourth real B2 batch (`data/batches/b2-real-04` on the Spark, commit `7a8b599`, 13:59:47 to 14:04:25 UTC; recorder
session `20261125-075943-batch-b2-real-04`; starts S5, S4, S3, 6 episodes, from the last pose of b2-real-03). After 132
moves, all `done` with no stall, it halted at the first forward moves of episode 1:
`odometry_scale: tag fixes land -56 % (+-18 %) of the distance from where the odometry puts the car (2.0 m driven, 5
fixes; limits +12 % ahead, -35 % behind; the range check has 1 measured forward moves, fewer than 3)`. The Pico then
dropped off the network (about 08:06 local). Every number below comes from the batch's text records, copied read-only,
by `analyse.py` (output `analyse-output.txt`).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: analysed the records and wrote this note and `analyse.py`.

**Verdict:** under-travel, the safe direction, read through four single-tag fixes that carry the tracked heading's
error. Not an encoder-scale error, and no danger to the car.

## What drove the −56 %

**The per-step statistic, replayed, gives exactly −56.5 % ± 18.3 % over 2.0 m and 5 fixes.** Four of the five fixes
were **single-tag position fixes** after northward legs of the transit to S5:

| Fix | Leg | Along the leg (share of it) | Fix σ |
| --- | --- | --- | --- |
| T01 | 0.51 m north | −0.22 m (−43 %) | 0.17 m |
| T00 | 0.50 m at 120° | −0.26 m (−52 %) | 0.15 m |
| T00 | 0.49 m north | −0.33 m (−67 %) | 0.15 m |
| T00 | 0.25 m at 66° | −0.23 m (−96 %) | 0.16 m |

The fifth fix, a two-tag fix of T05 and T16 after a FORWARD_25 at −31°, read −5 %.

**Why those fixes overstate it:**
- **Direction:** T00 (the desk) and T01 lie west and south-west of the car, so their lines of sight cross the
  northward motion. A single-tag fix takes the tracked heading as given, and a heading error moves it across the line
  of sight, that is, along the motion.
- **The heading here:** the transit's dead-reckoned heading ended **20.4°** off the start circle's, the gyro reading
  0.77 % short over 2,647° of net rotation (107 turns).

**The one ranged forward move read 0.99**, at −32°.

## Is the slip getting worse?

The transit north to S5, from the first circle to the start circle:
- **The record:** 1.61 m by odometry, 1.08 m by the circles, ratio 0.673, a 0.63 m miss.
- **The moves:** 7 FORWARD_25, 6 of them northward, and 107 turns.

| Hypothesis | Miss | Ratio |
| --- | --- | --- |
| as recorded | 0.63 m | 0.67 |
| gyro corrected (×1.0077: the heading closes) | 0.56 m | 0.66 |
| forward moves at the taped 0.78, gyro corrected | 0.22 m | 0.85 |
| forward moves at **0.70**, gyro corrected | **0.12 m** | 0.95 |

**Reading the table:**
- **Heading:** the 20° heading miss inflates the path numbers very little; the position miss is the forward moves'.
- **Slip:** they covered about **0.70** of their count here, against 0.78 taped (on the pilot's centre line, from y 1.9)
  and 0.82 to 0.94 by ranges earlier.
- **Place:** the worst moves are again the first northward ones from (2.45, 1.71) and (2.46, 1.95), flagged
  `slip_suspected` with 11.8° and 12.3° of wheel/gyro disagreement. That is the same spot as b2-real-02's S3 transit
  (rows 17 and 18, at (2.48, 1.57 to 1.82)). It is a worse patch at the start of the northward path, not necessarily a
  trend in time. No range pair measured those moves.

## What changed (after this batch, not used by it)

**The per-step statistic's under-travel side never halts on its own.** It is recorded beyond −45 % (−35 % in the
first version of this change)
(`per_step_drift.under_travel_beyond_the_floor`).

**The over-travel side is exactly as before:** +12 % and three standard errors, also while fewer than 3 forward moves
are ranged. Tests: b2-real-04's reading is now recorded rather than a halt; the same reading ahead (+56 %) still halts;
+13 % at 3.25 SE halts, at 2.6 SE not yet.

**Why this, of the three options:**
- **The risk:** under-travel is the safe direction (the car is behind where it thinks).
- **The reliability:** on the real car the statistic's under-travel readings are the least reliable reading of the
  scale: −27 % in b2-real-02 against −12 % by ranges, −56 % here against about −30 % on the forward moves.
- **Gross errors are still covered:** the range check halts below 0.55 (lowered from 0.65 the same evening, since the
  car covers 0.67 to 0.70 here), and the dead-reckoning drift halts below 0.5
  at the next circle.
- **The other two options were weaker.** A minimum number of fixes or distance would only postpone the same
  heading-driven reading. Feeding the transit drift forward would build the slip into the statistic's expectation,
  which is a correction model, the kind of change the study has not decided on.

## The Pico's dropouts and the STOP program's zeros

**The question:** while a latch exists, the STOP program (`ros_io.py`, `LATCHED_ZERO_PERIOD_S` 0.02) publishes a zero
on `/pico/cmd_vel` 50 times a second for as long as the latch stays.

**The dates:**
- Latches were set at 03:46:55, 05:29, 06:24, 07:35 and 08:04:25 local.
- The Pico dropped off at about 04:31 (44 minutes into the first latch) and about 08:06 (2 minutes into the last).
- The latches of 05:29 (35 minutes until b2-real-02), 06:24 (until the slip test) and 07:35 (24 minutes until
  b2-real-04) had none.
- Xiaohui also replugged the Pico at 03:26, before the practice batches.

**What the reference notes say** (`research/2026-10-24-car-firmware-lessons-and-pid.md`, F3 and F4):
- The firmware's main loop is busy about 12 % of the time at 94 passes per second.
- Its hardware watchdog reboots a car that hangs (8 s parked), and a reboot rejoins the network by itself.
- Its session rules wait 20 s before rebuilding a session.

None of this describes a state that needs a USB replug. A dropout that only a replug ends looks like the Pico losing
power, not the firmware.

**Assessment:**
- 50 messages a second is 2.5 times the 20 a second of every move, which the firmware handles for hours. Nothing in
  the notes ties zero floods to dropouts, and two of five latched periods is weak evidence.
- More likely: the USB power bank switching its port off (many banks cut a low, steady load after a while), or the
  cable disturbed when the car was carried.
- **A check:** log the bank's port with a USB power meter during a latched period, or run one latched hour with the
  STOP program's latched zeros at 5 a second and compare.
