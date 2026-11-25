# The three right-wheel stalls of 2026-11-25: a weak or a binding right wheel?

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this comparison, `stalls.py` and `stalls-output.txt`
from the batches' text records and the recorder sessions' move logs (copied read-only from the Spark after b2-real-07
halted; no frames).

Sources:
- The move logs of the floor check (03:02 CST) and of b2-real-02 through 07. They hold both wheels' ticks and duties at
  about 50 Hz.
- The tracked poses from the batch records.
- b2-real-01's session was not copied.

```
python3 course-project/evidence/M3/M3.T12/batch-runner/b2-real-05/stalls.py floor-check=<session>/moves \
  b2-real-02=<session>/moves,data/batches/b2-real-02 ... b2-real-07=<session>/moves,data/batches/b2-real-07
```

## The three stalled moves

| Stall | Move, heading, place | The right wheel up to the stop | The left wheel |
| --- | --- | --- | --- |
| b2-real-03, 13:35 UTC | TURN_LEFT_30 (right wheel forward), heading 3° → 30°, at (2.41, 1.54) | 0.092 m/s at duty 0.32; at the turn's floor duty of 0.295 it fell to 0.049, 0.009, 0 | backward at 0.034–0.037 m/s, same duty |
| b2-real-05, 17:19 UTC | FORWARD_25, heading −62° → −68° (south-east), (2.28, 2.12) → (2.39, 1.92) | cruise 0.134 m/s at duty 0.556; in the slow-down 0.110 (duty 0.36), 0.070 (0.33), 0.017 (0.36), 0 (0.42) | cruise 0.137 at 0.625; 0.081–0.067 at the stop |
| b2-real-07, 18:27 UTC | FORWARD_25, heading 75° → 71° (north-north-east), (3.11, 1.93) → (3.16, 2.16) | **mid-cruise dip to 0.049 m/s at duty 0.535** (the left at 0.095), back to 0.141; in the slow-down 0.083 (0.29), 0.048 (0.30), 0.046 (0.32), 0.008 (0.33), 0 (0.375) | 0.06–0.11 m/s, duty 0.35–0.43 at the stop |

The three share some things and differ in others.
- **What they share:** each time the right wheel stopped at low duty (0.30–0.42) while the left kept turning. No
  firmware cut-off or bump was recorded.
- **What differs:** headings (east, south-east, north-north-east) and places (two at the old tape line, one 0.8 m east
  of it). Only the third came after the fresh AA cells (fitted before b2-real-06).
- **The b2-real-07 move also shows a mid-cruise dip,** at normal duty, before its slow-down.

## Duty against speed for each wheel, through the day

Each wheel's median duty while it ran at 0.10–0.13 m/s on straight moves:

| Session (local time) | Left | Right | Right minus left |
| --- | --- | --- | --- |
| floor check (03:02) | 0.654 (127 samples) | 0.518 (121) | −0.136 |
| b2-real-02 (06:05) | 0.643 (403) | 0.521 (418) | −0.122 |
| b2-real-03 (07:26) | 0.641 (426) | 0.526 (415) | −0.115 |
| b2-real-04 (07:59) | 0.627 (121) | 0.533 (105) | −0.094 |
| b2-real-05 (10:50) | 0.631 (1,244) | 0.526 (1,284) | −0.105 |
| b2-real-06 (11:29, fresh AA cells) | 0.633 (367) | 0.522 (404) | −0.111 |
| b2-real-07 (12:24) | 0.607 (60) | 0.535 (62) | −0.072 |

- **The right wheel needs less duty than the left for the same speed, all day, b2-real-07 included.** When it turns
  freely, it is the stronger or freer side of the car.
- **Its need hardly moved:** 0.518 → 0.535 over the day (+3 %; b2-real-07 is only 62 samples).
- **The gap narrowed mostly from the left:** the left's need fell from 0.654 to 0.607.
- **At low duty the right wheel also runs faster than the left all day.** At duty 0.35–0.40 it does 0.085–0.099 m/s;
  b2-real-07 gives 0.091. The left does 0.010–0.072 (`stalls-output.txt` §2).
- **Conclusion:** no sign of a right motor that is weak or getting weaker in its normal running.

**What did appear late in the day is the right wheel held back while driven hard.** These are straights where, past
the first 0.4 s, the speed loop pushed the right wheel to duty 0.60–0.72 (0.08 to 0.20 above its cruise need) and it
still ran at 0.05–0.08 m/s:

| Session | Straights | Right wheel held back | Left wheel held back (duty ≥ 0.72, < 0.10 m/s) |
| --- | --- | --- | --- |
| floor check, b2-real-02, 03, 04, 05 | 209 | **0** | 0 |
| b2-real-06 | 37 | **1**: at (1.78, 2.68), 0.06 m/s for about 1 s while its duty rose to 0.715 | 0 |
| b2-real-07 | 7 | **2**: at (2.41, 2.23), 0.046–0.081 m/s at duty 0.60–0.70; at (2.90, 1.89), 0.051–0.056 m/s at 0.61–0.65 | 0 |

Two of these three are 0.5–0.6 m from the old tape line. In each the move still completed.

## The firmware's stall-assist kicks

A kick is the firmware pushing a stopped, driven wheel at duty 0.8.

| Session | Moves | Right wheel | Left wheel |
| --- | --- | --- | --- |
| floor check | 23 | 0 | 0 |
| b2-real-02 | 442 | 0 | 3 (turns) |
| b2-real-03 | 246 | 0 | 0 |
| b2-real-04 | 132 | 0 | 0 |
| b2-real-05 | 803 | 3 (turns) | 8 (turns) |
| b2-real-06 | 396 | **8** (turns) | 1 (turn) |
| b2-real-07 | 71 | 0 | 0 |

## The supply voltage

The motors' AA pack is not measured. Neither the move logs nor the batch records nor the session meta has a motor
supply field. The one supply reading is `car_state.vsys_min_mv`, the Pico's own supply from its power bank. It held
steady all day: lowest 4,614–4,682 mV and median 4,686–4,689 mV per batch, against the batch's 4,300 mV limit. The
b2-real-07 stall came about an hour after fresh AA cells were fitted.

## Verdict: intermittent binding or drag on the right wheel, worsening through the afternoon; not a weak motor

- **The right wheel is not weak in its normal running.**
  - It needs about 0.52–0.53 duty for 0.10–0.13 m/s, all day, against the left's 0.61–0.65.
  - It runs faster than the left at low duty.
  - Its need did not grow, even across the battery change.
- **But it is now being held back, intermittently and more often:**
  - assist kicks: none on the right through b2-real-04, then 3 in b2-real-05 and 8 in b2-real-06 (none in
    b2-real-07's 71 moves);
  - straights with the right wheel driven to 0.60–0.72 duty yet running at about 0.06 m/s: none in 209 through
    b2-real-05, then 1 in b2-real-06 and 2 of 7 in b2-real-07;
  - stalls at 13:35, 17:19 and 18:27 UTC, each at a move's low-duty end, at different headings and places;
  - the last stall is 0.8 m from the tape and came about an hour after fresh AA cells.
- **What fits:** something that comes and goes and holds back the right motor's shaft. When it holds, the speed loop
  raises the duty and the wheel still crawls; at the low duty of a move's end, it stops. That fits a rub or wound
  fibre more than a uniformly weak motor.
  - Fibre or hair wound round the right axle between the wheel and the motor housing.
  - The right tyre rubbing the body, the chassis or a cable.
  - Grit in the right gearbox.
  - A worn spot on the motor's brushes. This one the records cannot tell apart from a rub: they have no shaft angle.

**What Xiaohui should look at first,** with the motor battery off:
1. **Turn the right wheel by hand against the left.** Feel for a tight spot or a scrape once per turn. Then look
   between the right wheel and the motor housing for wound carpet fibre or hair.
2. **Check the right tyre's clearance** to the body and any cable, and that the wheel sits square on its shaft.
3. **If both are clean,** run the right motor on the stand (wheels up) at low duty and watch whether it stops at one
   shaft position (a brush or commutator spot) or keeps turning.
