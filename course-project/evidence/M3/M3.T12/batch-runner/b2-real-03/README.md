# b2-real-03, 2026-11-25: the stall in episode 2's end circle

The third real B2 batch (`data/batches/b2-real-03` on the Spark, commit `7a8b599`, started 13:26:01 UTC; recorder
session `20261125-072556-batch-b2-real-03`).

- **Episode 1** (S1): ended DONE after 56 steps, final pose error 0.07 m.
- **Episode 2** (S2): ended DONE after 81 steps at 13:35:10, final pose error 0.08 m.
- **The halt:** at 13:35:23 the 6th turn of episode 2's end circle halted the batch: `stall: TURN_LEFT_30:
  stall_right`. The car stopped and the project latch was set.

Every number below comes from copies of the batch's text records and the session's move logs, by `stall.py` (output
`stall-output.txt`).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: analysed the records and wrote this note and `stall.py`.

**Verdict:** most likely a marginal-duty stall of the right (outer) motor at the slow end of a pivot on carpet, and
not a fading battery. The car stood in open floor, 1.2 m or more from every known edge. But the stall is an outlier:
it is the only slow end of the batch's 191 left turns where the right wheel came under 0.029 m/s. So a local cause (a
snag in the carpet, something on the floor at that spot) cannot be excluded remotely, and a look at the floor settles
it. b2-real-04 later started from this spot without a stall.

## The stalled turn

- **The command:** a TURN_LEFT_30 at 0.6 rad/s, slowing to the minimum rate of 0.3 rad/s near its end. The duty rose
  from ±0.146 to ±0.341, then fell to ±0.295 for the slow phase.
- **The right wheel slowed to a stop:**
  - it ran at +0.08 to +0.10 m/s;
  - at duty 0.295 it decelerated over about 0.13 s: 0.074, 0.044, 0.049, 0.019, 0.033, 0.013, 0.006, 0.000 m/s;
  - its count froze at +798 from +0.634 to +0.844 s.
- **The rest of the car kept moving.** Meanwhile the left wheel kept turning at −0.035 m/s, and the gyro kept turning
  the car at about 12°/s. A pivot about a stopped right wheel gives 0.035 / 0.1335 ≈ 15°/s, while a dead encoder on a
  turning right wheel would give about 49°/s. So the wheel really stopped.
- **Which rule halted it:** the executor's stall rule (a wheel under 0.01 m/s for 0.2 s while commanded) fired at
  +0.844 s, at 27° of the 30°. The firmware did not cut off (`cut` 0, `cutoffs` 0), and there was no bump.
- **It had not happened before.** In the batch's 190 earlier left turns, the right wheel's lowest speed at the slow
  end (after the highest duty, at about 0.295) was **0.029 to 0.07 m/s**, median 0.067. None went below 0.02 m/s, and
  2 went below 0.03. The stalled turn is the only one that slowed to a stop there.
  - Corrected 2026-11-25: a first version said 41 of 190 turns nearly stopped at that duty. It had also counted the
    start ramp, where the duty passes 0.283 on its way up while the wheel is only starting.
  - `tools/stall_check.py --turn-margins` reports the slow end only. Besides the stall, 4 turns had the **left** (inner)
    wheel at 0.017 to 0.019 m/s there.
- **No battery fade within the batch.** Wheel speed per unit duty while cruising:

  | Part of the batch | Left | Right | Turn duration |
  | --- | --- | --- | --- |
  | first third of the turns | 0.148 m/s | 0.245 m/s | 0.99 s |
  | middle third | 0.148 m/s | 0.246 m/s | 0.99 s |
  | last third | 0.151 m/s | 0.249 m/s | 0.98 s |
  | FORWARD_25, first half | 0.183 m/s | 0.225 m/s | |
  | FORWARD_25, second half | 0.185 m/s | 0.227 m/s | |

## Where the car stood

- **The place:** the end circle turned in place around (2.38 to 2.42, 1.54 to 1.59). After the stall the tracked pose
  was (2.415, 1.539, 30°), σ 0.050.
- **The clearance:** the axle was 1.41 m inside the driving area, with 1.23 m of turn room. The desk (x < 0.66) was
  1.75 m away.
- **The camera's view was clear.** The view after the stall saw T06 at 1.78 m and T14 at 1.58 m, consistent with that
  pose.
- **The carpet patch:** the spot lies in the patch where the car slips northward (x 2.4 to 3.0, y 1.4 to 2.7,
  `../b2-real-02/`).

**Other flags:**
- the batch had 1 stall, 2 `slip_suspected` and no bumps;
- telemetry age was at most 0.037 s;
- `lost_samples` was 25 (cumulative);
- `vsys_min_mv` was 4,689 (the Pico's supply);
- the log has no corrupt JPEG warnings.

## How to tell the causes apart remotely

- **A blockage:** an abrupt stop at cruise duty; the other wheel or the gyro also stopping, or a bump flag; a pose near
  an edge; the same place again.
- **A weak battery:** wheel speed per unit duty falling across a batch, and stalls at higher duty.
- **A marginal-duty stall (this one):** a gradual slowdown only at the turn's minimum duty, the other wheel and the gyro
  still moving, open floor, no trend, and earlier near-misses at the same duty.

## Episode 2's record

- **It ended DONE,** and its `final_pose_error` was written (0.082 m, truth a tag fix with σ 0.056), because that is
  written before the end circle.
- **But the stall came inside the end circle,** and `end_pose_*` and the `done` status were written only after it. So
  the episode stayed `halted` without an end pose.
- **For the replay,** its log is complete apart from the end circle's confirmation: every step, the step truth from tag
  fixes, and the final error.
- **Fixed since (not in the code this batch ran):** the end pose is now written from the tracked pose, and the episode
  marked done, before the end circle. The circle's result replaces it when the circle succeeds (`end_pose_source`).

## The classifier

`tools/stall_check.py BATCH_DIR SESSION_DIR` prints this signature for the stalled move of any halted batch, read-only:
- the duty at the stop against the move's highest;
- whether the deceleration was gradual or abrupt;
- the other wheel and the gyro while the wheel stood;
- the firmware cut-off and bump flags;
- the footprint's clearance inside the driving area;
- earlier stalls within 0.30 m.

It ends with "marginal-duty stall, clear of everything" or "possible blockage: do not restart" and the reasons. On
this batch's records it says the former (`tests/test_stall_check.py` covers both verdicts).

## The duty-floor cure: what it would take (not done)

**The change:** `W_MIN_RPS` in `beaconmind/src/beaconmind/car/config.py`, 0.3 → 0.35 rad/s. That is the rate a turn
slows to for its last degrees, and with it the lowest duty of a turn: today 0.295. There the right wheel kept 0.029 to
0.07 m/s in 190 turns and stopped once.

**What it invalidates:**
- **The pass marker.** `config.py` is fingerprinted, so `record-pass` must run again after the checks below.
- **The turn's stop timing.** The executor stops a turn at the gyro's angle minus a coast lead, the angle the car still
  turns after the zero. At the higher final rate the car coasts about 17 % farther (about 0.2° per 30° turn at today's
  coast time of 0.067 s). The coast time adapts move by move (`adapt_coast`, weight 0.5), so it settles within a few
  turns, but the floor check's turn result (F3: three turns each way within 8° of 90°, the gyro within 4° of the tags)
  was measured with 0.3 and no longer stands.
- **The stand test's turns** (S4, S5: wheels up, timing out by design) were run with 0.3. Their pass criteria do not
  depend on the rate, but they are the record of that tuning.
- **The simulated car** uses the same config, so the dry runs change slightly and must be run again.

**The test on the car**, attended, motor battery on:
1. **Stand:** S4 and S5 once each (a left and a right turn, wheels up). Expect `timeout`, the wheels turning the right
   way.
2. **Floor:** F3 again: three TURN_LEFT_30 and three TURN_RIGHT_30, the angles measured by the tags against the gyro,
   to the same criteria.
3. **The stall probe:** three full circles (36 × TURN_LEFT_30) at about (2.4, 1.55), where b2-real-03 stalled. Read
   the right wheel's minimum speed at each turn's lowest duty with `stall_check.py --turn-margins`. It passes with no
   stall and that minimum above 0.03 m/s in at least 35 of the 36 turns. Today: 188 of 190 above 0.03, one stall.
4. **Then:** `record-pass` and the exact-argument dry run.

**What not to do:** lengthening the stall window at the minimum duty would hide this case, but it weakens the stall
rule everywhere it fires. Not recommended.
