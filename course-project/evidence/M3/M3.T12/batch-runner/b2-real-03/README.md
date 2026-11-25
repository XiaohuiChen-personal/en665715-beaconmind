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

**Verdict:** a marginal-duty stall of the right (outer) motor at the slow end of a pivot on carpet. It was not a
blockage and not a fading battery. The car stood in open floor, 1.2 m or more from every known edge. An unknown object
on the floor cannot be excluded remotely; a look at the floor settles it.

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
- **The same near-stop happened before.** In **41 of the batch's 190 earlier left turns** the right wheel, at that same
  duty (0.28 to 0.31), dropped to 0.004 to 0.02 m/s and recovered within the 0.2 s window (median minimum 0.037 m/s).
  This time it did not recover in time.
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

## Possible cures (not done; for the lead and Xiaohui)

- **Raise the turn's minimum duty,** for example `w_min_rps` 0.3 to 0.35. This touches the executor's tuning and the
  coast-lead calibration.
- **Not recommended: lengthen the stall window** at the minimum duty only. That weakens the stall rule.
