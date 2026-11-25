# The batch's ground truth on the slipping carpet, 2026-11-25

The batch's ground truth for every step is the pose it tracks: odometry between tag fixes, each fix blended in by
inverse variance (`PoseTracker`). The tracker assumes odometry errors of 5 % of the distance driven. On this carpet the
car covers 0.67 to 0.78 of its counted distance northward and 1.04 southward (`../b2-real-02/`, `../b2-real-04/`), so
the tracker is too sure of its odometry northward. Far single-tag fixes get too little weight, and the truth runs
ahead of the car with a stated sigma of 5 to 6 cm.

This note measures that, tries a slip-aware odometry sigma, and recomputes the five real episodes' truth offline.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: ran the measurements and wrote this note,
`slip_sigma_exp.py`, `tools/recompute_truth.py` and the slip option in `PoseTracker`.

## 1. A slip-aware odometry sigma, prototyped (not switched on)

**The option:** `PoseTracker(..., slip_sigma_per_m, slip_north_per_m)` and `BatchParams.odometry_slip_sigma_per_m`,
`odometry_slip_north_per_m`, both 0 by default (the tracker as before). A forward move of d metres adds
(a + b × max(0, sin heading)) × d to the position sigma, in quadrature.

**The measurement:** ten-episode batches with the exact real arguments on the simulated car, on a carpet at 0.67 and at
0.60 northward (1.04 southward), 3 seeds each (`slip_sigma_exp.py`, output `slip_sigma_exp-output.jsonl`). The truth
error is the tracked pose against the simulated car's own.

| Tracker | North | Completed | Halts | Truth error: p95 / max (all rows) | Episode rows: p95 / max | Rows beyond 2 σ | Fixes refused | Guard refusals |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| as now (5 %) | 0.67 | 1 of 3 | 2 × `fix_conflict` (episode 8) | 0.20–0.22 / 0.50–0.63 m | 0.10–0.13 / 0.13–0.25 m | 13–14 % | 2–3 | 0 |
| as now | 0.60 | 0 of 3 | 3 × `fix_conflict` | 0.25 / 0.63–0.72 m | 0.13–0.16 / 0.19–0.30 m | 17 % | 3 | 0 |
| **0.3 × d** | 0.67 | **3 of 3** | none | 0.11–0.13 / 0.25 m | 0.06–0.11 / 0.14–0.24 m | **0 %** | 0 | 0 |
| 0.3 × d | 0.60 | 2 of 3 | 1 × `pose_uncertain` | 0.14–0.19 / 0.37–0.42 m | 0.07–0.09 / 0.24–0.29 m | 1–2 % | 0 | 0 |
| 0.10 + 0.25 × north | 0.67 | 3 of 3 | none | 0.11–0.13 / 0.25–0.38 m | 0.07–0.10 / 0.13–0.25 m | 0 % | 0 | 0 |
| 0.10 + 0.25 × north | 0.60 | 1 of 3 | 2 × `pose_uncertain` | 0.14–0.15 / 0.37–0.41 m | 0.09–0.10 / 0.14–0.30 m | 0–0.4 % | 0 | 0 |

**Reading it:**
- **At the carpet's real northward travel (0.67 to 0.70),** 0.3 × d halves the truth error (all rows p95 0.20 to about
  0.12 m), makes the stated sigma honest (no row beyond 2 σ, against 13 %), and removes the false `fix_conflict` halts
  (3 of 3 completed, against 1 of 3). It cost no guard refusal in any run.
- **The heading-aware variant** does no better at 0.67 and worse at 0.60, so the simple one is preferred.
- **At 0.60,** below anything measured on the real car, the larger sigma runs into `sigma_block_m` (0.25 m) during
  the long northward transit to S3 and halts `pose_uncertain` instead. A repeated fix from the same single tag does not
  shrink the sigma (the tracker's same-tag rule), so the sigma climbs over several blind stretches.
- **The cost:** guard margins of 2 σ (at most 0.15 m) and larger stated sigmas in the truth logs. It is a tracker
  change, so it needs a review and a new pass marker.

## 2. The real episodes' final errors, and which truth to trust

**The tool:** `tools/recompute_truth.py BATCH_DIR [--slip-sigma A] [--slip-north B]` replays the batch's own per-step
code (`BatchEnv._post`) over an episode's logged rows, from the tracked pose logged at its first row, with the chosen
tracker setting. It is analysis only. With the tracker the batch ran it reproduces the logged truth: 0.000 to 0.001 m
on the five real episodes, and within 0.003 m in a dry batch (`tests/test_recompute_truth.py`). Output:
`real-episodes-recomputed.txt`.

| Episode | Final error, logged truth (σ 5–6 cm) | Recomputed, 0.3 × d | Against the end circle | Tracked end − end circle: logged → recomputed | End circle |
| --- | --- | --- | --- | --- | --- |
| b2-real-01 ep1 (S1) | 0.031 m | 0.028 m | **0.036 m** | 0.066 → 0.063 m | 9 tags, rms 0.023 |
| b2-real-02 ep1 (S1) | 0.028 m | 0.024 m | **0.013 m** | 0.042 → 0.037 m | 8 tags, rms 0.040 |
| b2-real-02 ep2 (S2) | 0.203 m | 0.095 m | **0.135 m** | 0.076 → 0.040 m | 14 tags, rms 0.026 |
| b2-real-03 ep1 (S1) | 0.069 m | 0.037 m | **0.086 m** | 0.146 → 0.091 m | 13 tags, rms 0.022 |
| b2-real-03 ep2 (S2) | 0.082 m | 0.049 m | none (the stall) | — | — |

**How wrong the logged final truth can be.**
- **In simulation:** at 0.67 northward, the episode rows' truth error reached a p95 of 0.10 to 0.13 m and a maximum of
  0.13 to 0.25 m against a stated 5 to 6 cm.
- **On the real episodes:** the slip-aware recomputation moves the final truth by up to 0.112 m (b2-real-02 ep2). The
  logged tracked end sits up to 0.146 m from an end circle of rms 0.022 m (b2-real-03 ep1). A final error of a few
  centimetres against the logged truth is therefore not resolvable on this carpet.

**The trustworthy truth is the end circle.** All four real episodes with an end circle ended by DONE, so no move
followed the agent's last report, and the end circle measured that very pose. It is a full circle of 8 to 14 tags,
solved on its own geometry; the tracked pose only resolves repeated tag ids within 1 m. Its residuals are 0.022 to
0.040 m. Recommendations for the report:
- **Final error:** use the end-circle column wherever an end circle exists.
- **b2-real-03 ep2,** whose end circle the stall interrupted: give the slip-aware recomputed 0.049 m, with its larger
  uncertainty stated, or mark it as without an independent final truth.
- **The logged step truth:** carries the tracker's overconfidence on northward stretches. Recomputed offline with
  0.3 × d it moves closer to the end circle in every episode that has one.

## 3. Switched on for real batches: `--slip-sigma 0.3`

The lead's decision (2026-11-25): real batches run with 0.3 × d, as an explicit argument of `tools/car_batch.py`
(`--slip-sigma`), recorded in the manifest (`params.odometry_slip_sigma_per_m`) and printed at the start. A real batch
refuses to start without it stated (0 states it off); dry runs and tests default to 0.

**Exact-argument dry runs with `--slip-sigma 0.3`** (log `slip-sigma-0.3-dry-runs-log.txt`):

| Run | Result | Truth error against the car: p95 / max | Rows beyond 2 σ |
| --- | --- | --- | --- |
| plain | 10 of 10 | 0.007 / 0.012 m | 0 % |
| north 0.78 | 10 of 10 | 0.067 / 0.245 m | 0 % |
| north 0.67 | **halted after 8 episodes, all 8 done** | 0.124 / 0.305 m | 0 % |

**The north-0.67 halt:**
- **What fired:** the dead-reckoning gross bound on the under-travel side. Episode 8 measured 0.73 m by odometry
  against 0.34 m by the circles: ratio 0.47, below 0.5.
- **Why:** on a carpet whose slip depends on direction, a short net displacement made of moves north and south shrinks
  much more than any one move. For example, 0.5 m north and 0.2 m south by odometry come out as 0.335 and 0.208 m on
  the floor: net 0.30 m by odometry, 0.13 m on the floor.
- **How rare:** over 130 transit and episode measurements on the simulated carpets this is the only ratio under 0.6.
  With 0.6 m or more of net distance by the circles, the lowest is 0.604, at north 0.60.
- **Not caused by the slip sigma:** the ratio does not use the tracker's sigma.
- **A possible change, not made:** judge the under-travel side only over net distances of 0.6 m or more.

## 4. The review of 927e44c: four findings, folded into this commit

The reviewer's verdict on 927e44c was yes: 24 ten-episode batches, no wall contact, smallest depth 0.196 m, and every
over-travel fault halted (12 of 12). It made four further findings; each is answered here.

### Finding 1: the gross drift bound was not a clean scale test

**The problem.** On a carpet that slips by direction, an out-and-back path changes the odometry's net displacement by
any factor, so the net length ratio is no scale test. Two correct cars false-halted on it:
- the reviewer's, at north 0.60: 0.79 m by odometry against 1.29 m by the circles, ratio 1.63 against the bound 1.6;
- mine (above), at north 0.67: 0.73 m against 0.34 m, ratio 0.47 against 0.5.

**The change.** The bound now compares the **miss with the path driven**. It halts when the miss, less the two circles'
own 2 σ, is more than **0.6 of the path driven by odometry** (`path_gross_share`). The miss can never exceed the path
times the largest share by which one move goes wrong (the triangle inequality): 0.45 at the 0.55 floor, plus what a
heading error swings.

**How it compares with what was seen:**
- **Real:** the eight real transits and episodes that have a miss on record read 0.012 to 0.207 (b2-real-04's transit,
  with its 20° heading miss).
- **Simulated:** the carpets read up to 0.30 at north 0.67 and 0.37 at 0.60 (`margin_cost-output.jsonl`,
  `final-dry-runs-log.txt`).
- **Faults:** a factor-two error on a straight path (a transit) misses by the whole path, which is 1.0 of it, and
  halts. The test uses b2-real-01's geometry, odometry reading half of 0.91 m.

**What it no longer catches.** An odometer reading double, so that the car covers half its count, comes out at 0.5 of
the path and passes this bound. That is the range floor's case (0.55) and a safe direction. The net ratio is still
recorded (`tags_over_odometry`), and the fields `path_m`, `miss_over_path` and `gross_share` are new.

### Finding 2: the turn margin against fix error

**The problem.** With a start error of sd 0.06 m (a fix error, larger than the 0.05 m floor), the reviewer's Monte
Carlo found 3 stretches in 60,000 whose real sweep circle crossed the edge by up to 0.016 m. Its suggestion: about
0.10 m in place of 0.05 m, for the turn margin or the sigma floor.

**The evaluation.** I ran it with the slip sigma both on and off (`guard_mc.py`, output `guard_mc-output.jsonl`), and
measured the cost in ten-episode batches on the carpet with `--slip-sigma 0.3`, 3 seeds each at north 0.67 and 0.78
(`margin_cost.py`, output `margin_cost-output.jsonl`):

| Guard setting | Monte Carlo: stretches below 0 in 60,000 | Worst real turn room / footprint | Carpet batches completed | Guard refusals |
| --- | --- | --- | --- | --- |
| as before (turn margin 0.03, spare 0.05, floor 0.05) | 3 (every north, slip on or off) | −0.016 / −0.016 m | 6 of 6 | 0 |
| spare 0.10 at the start and end of forward moves | 3 | −0.016 / −0.016 m | 6 of 6 | 0 |
| sigma floor 0.10 | 0 | +0.007 / +0.009 m | **4 of 6** (2 × `pose_uncertain` at 0.67) | 0 |
| turn margin 0.08 | 0 | +0.007 / +0.009 m | 6 of 6 | 0 |
| **turn margin 0.10** | **0** | **+0.016 / +0.022 m** | **6 of 6** | **0** |

**Reading the table:**
- **The spare does not help.** The 3 stretches go wrong at a **turn** made where the believed pose, not the real one,
  had just enough room. So the spare on forward moves changes nothing, and the turn's own margin (0.03 m plus one
  sigma) is what was thin.
- **The sigma floor is costly.** It fixes the Monte Carlo, but with the slip sigma it pushes the tracked sigma over
  0.25 m on long northward runs, through the same-tag rule.

**The choice:** `MoveGuard.turn_margin_m` and `BatchParams.turn_margin_m` are now **0.10 m** (were 0.03). Two guard
tests were moved by 7 cm to the new margin: a turn 0.07 m from the edge is now refused and one at 0.14 m allowed, and
a FORWARD_10 near the window wall is now tested from 3.30 m (was 3.35 m).

### Finding 3: the concavity argument and a turn inside a blind stretch

Written into `../b2-real-02/README.md` where the argument is made. It does not cover a blind stretch with a turn in it:
the car is then beside the tracked path. By the reviewer's geometry the worst case leaves about 0.02 m of real turn
room at 0.55 and 0.05 m at 0.67, positive only thanks to the start margin. The fix error at the stretch's start is
finding 2.

### Finding 4: an exception inside the end circle

**Before:** a halt inside the end circle left the episode `done`, but an unexpected exception there marked it
`failed`. Resume reruns every episode that is not `done` (`BatchRunner.run`), so a finished episode would have been
driven again, and the replay converter skips it.

**Now:** both leave it `done`, with the exception recorded as `post_episode_error`. The batch still halts on it (code
`error`). Test: `test_an_error_inside_the_end_circle_leaves_the_episode_done_and_resume_skips_it`.

### The final dry runs (this commit, `--slip-sigma 0.3`, exact real arguments)

Log: `final-dry-runs-log.txt`.

| Run | Result | Truth p95 / max against the car | Beyond 2 σ | Miss over path, max | Net ratios recorded |
| --- | --- | --- | --- | --- | --- |
| plain | 10 of 10 | 0.008 / 0.020 m | 0 % | 0.000 | 0.99–1.00 |
| north 0.78 | 10 of 10 | 0.056 / 0.256 m | 0 % | 0.196 | 0.78–1.05 |
| north 0.67 | **10 of 10** | 0.118 / 0.305 m | 0 % | 0.307 | 0.47–1.16 (the 0.47 no longer halts) |
| north 0.60 | halted `pose_uncertain` after 8 done | 0.153 / 0.406 m | 1.9 % | 0.373 | 0.60–1.10 |

**The 0.60 halt is the same-tag rule, not changed here** (proposed to the lead). On a long run of single-tag fixes of
one tag, the tracked sigma may move with the fix but never shrink, so it climbs past 0.25 m by the slip sigma while
the pose is within a few centimetres. North 0.60 is below anything measured on the real car.
