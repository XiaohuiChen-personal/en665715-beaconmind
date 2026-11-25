# The batch's ground truth on the slipping carpet, 2026-11-25

The batch's ground truth for every step is the pose it tracks: odometry between tag fixes, each fix blended in by
inverse variance (`PoseTracker`). The tracker assumes odometry errors of 5 % of the distance driven. On this carpet the
car covers 0.67 to 0.78 of its counted distance northward and 1.04 southward (`../b2-real-02/`, `../b2-real-04/`), so
the tracker is too sure of its odometry northward. Far single-tag fixes get too little weight, and the truth runs
ahead of the car with a stated sigma of 5 to 6 cm.

This note measures that, tries a slip-aware odometry sigma, and recomputes the five real episodes' truth offline.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: ran the measurements and wrote this note,
`slip_sigma_exp.py`, `tools/recompute_truth.py` and the slip option in `PoseTracker`. Later the same day: §5 and §6
(the factor-two errors, the range gate and the early blind limit; the same-tag rule), `factor_two_probe.py`,
`blind_cap_cost.py`, `same_tag_exp.py`, `wrong_tag_walk.py`, `tag_probe_rule.py`.

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
| north 0.78 | 10 of 10 (one: the B2 dead end, see below) | 0.056 / 0.256 m | 0 % | 0.196 | 0.78–1.05 |
| north 0.67 | **10 of 10** | 0.118 / 0.305 m | 0 % | 0.307 | 0.47–1.16 (the 0.47 no longer halts) |
| north 0.60 | halted `pose_uncertain` after 8 done | 0.153 / 0.406 m | 1.9 % | 0.373 | 0.60–1.10 |

**The 0.60 halt is the same-tag rule, not changed here** (proposed to the lead). On a long run of single-tag fixes of
one tag, the tracked sigma may move with the fix but never shrink, so it climbs past 0.25 m by the slip sigma while
the pose is within a few centimetres. North 0.60 is below anything measured on the real car. (Changed in §6, on
the lead's decision: this run now completes 10 of 10.)

## 5. The drift's path share kept; the range gate; the early blind limit (later on 2026-11-25)

**The drift bound.** For one commit (`9dd80e9`) the dead-reckoning drift was record-only, on a decision of the lead's
that crossed with their acceptance of the path share (Finding 1). The lead kept the path share: it still halts a
factor-two error on a straight path. It is back as in `19f71e6`, and it now does halt something: in the 20-tag room's
factor-two over-travel, seeds 2 and 3, it halted the first transit 0.31 m inside the driving area (below). On the
real car it has stayed well clear: b2-real-05's largest miss over path was 0.24 (`../b2-real-05/`).

**What halts a factor-two scale error** (`factor_two_probe.py`, `factor_two_probe-output.txt`, the table in
`../README.md`). The range check halts both directions at the first ranged forward move. Two changes make that so:
- **The range check's same-tag gate** dropped a factor-two over-travel as another tag: the range missed its
  prediction by a whole move, over the gate of half a move plus 0.10 m. The gate is now 1.5 moves plus 0.10 m
  (approved by the lead). The real room's over-travel now halts on the ranges, 1.27 m inside, where on `19f71e6`
  only `fix_conflict` caught it, 0.49 m inside.
- **The early blind limit.** In the 20-tag test room a factor-two over-travel drove blind from its first forward
  moves (no tag in view) and reached a wall: 2 of 3 seeds with the range check, 3 of 3 without, and the same on
  `19f71e6`. Until the range check has 3 ranged forward moves, the car now drives at most 0.30 m (one FORWARD_25)
  without a tag fix (`blind_limit_m`; approved by the lead). With the range check working, no seed reaches a wall
  (0.31 m or more inside).
- **What remains:** with the range check switched off (an artificial fault), the 20-tag room's seed 1 still reaches a
  wall. Single far tags fix the pose after every move, so the blind count restarts, but with too little weight to
  catch up with the car.

**Its cost** (`blind_cap_cost.py`, `blind_cap_cost-output.txt`, a correct odometer, four-episode batches, 3 seeds, on
against off):
- **Real room:** the first transit took one more attempt, and so one more circle, in 3 of 3 seeds. Whole batches took
  between 66 moves fewer and 71 more.
- **20-tag room:** between 41 moves fewer and 20 more.
- All 12 batches completed, at least 0.25 m inside (0.26 m without the limit).
- **The ten-episode dry runs** (exact real arguments, plain and north 0.78, 0.67, 0.60) were move for move the same
  with it, because their first forward moves are ranged (`same-tag-dry-runs-log.txt`, which also stands for these).

## 6. The same-tag rule: a repeated fix leaves the sigma no larger than its own (the lead's decision, 2026-11-25)

The measurements of this section ran on `9dd80e9`'s code (the drift record-only, no early blind limit); each compares
the two rules on the same code.

**The rule.** A fix that rests on exactly the tags of the last fix repeats that fix's survey and range-scale error.
Until now it moved the pose but left the position sigma as it was, so on a long run of one tag's fixes the slip sigma
built up between them with nothing to bring it down: at north 0.60 the sigma passed `sigma_block_m` (0.25 m) and the
batch halted `pose_uncertain`, with the pose within a few centimetres of the truth (§4, the final dry runs). Now
such a fix sets the sigma to min(the sigma, the fix's sigma) (`PoseTracker._shrink`, in `correct` and
`correct_position`). It never takes the sigma below what one fix of that tag says, and never below the
inverse-variance result that a fix on new tags would give: no gain from repeating a survey error. Test:
`test_a_same_tag_fix_leaves_the_sigma_no_larger_than_its_own`.

**On the simulated carpet** (`same_tag_exp.py`, `same_tag_exp-output.jsonl`; ten-episode B2 batches, the exact real
arguments, `--slip-sigma 0.3`, the slip of §1, old rule against new on the same code, 3 seeds each):

| North | Rule | Completed | Halts | Truth p95 / max | Beyond 2 σ | σ max | Smallest true depth |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.67 | old | 3 of 3 | none | 0.113–0.131 / 0.246–0.256 m | 0 % | 0.201–0.249 m | 0.282 m |
| 0.67 | new | 3 of 3 | none | 0.113–0.131 / 0.246–0.256 m | 0 % | 0.181–0.189 m | 0.282 m |
| 0.60 | old | 2 of 3 | 1 × `pose_uncertain` (seed 1, after 7) | 0.139–0.191 / 0.371–0.419 m | 1.4–2.3 % | 0.245–0.251 m | 0.311 m |
| 0.60 | new | **3 of 3** | none | 0.139–0.173 / 0.371–0.419 m | 1.6–1.7 % | 0.177–0.219 m | 0.268 m |

The pose errors are unchanged: the rule moves the sigma, not the pose. The largest sigma comes down by 0.015 to 0.07 m,
and the share of steps beyond 2 σ stays where it was. The smallest depth at 0.60 (0.268 m) is seed 1's, which now
drives all ten episodes instead of seven; it is above the 0.15 m wall margin. The old-rule rows repeat §1's "0.3 × d"
rows exactly, so the code changed since then (the turn margin, the range gate) changed none of these runs. (A first
run of this script reused worker processes and stacked the simulated slip on itself; its output was thrown away. The
script now captures the car's step once, and each worker runs one batch.)

**A tag surveyed 0.3 m wrong, fixed again and again** (`wrong_tag_walk.py`, `wrong_tag_walk-output.txt`). Set-up:
the test's walk at the window wall, with T06 in the world file 0.3 m into the room and the camera seeing T06 alone.
The tag steers without a check, which is what a tag already trusted would do before a later circle names it. With
the check on, the circle names T06 and halts `tag_survey` before any forward move
(`test_a_tag_surveyed_wrongly_by_d_cannot_pull_the_car_toward_its_wall`).

| Case | Rule | σ along the walk | Pull (tracked − true x) | Forward moves, then refused | Smallest true depth |
| --- | --- | --- | --- | --- | --- |
| no slip sigma | old and new alike | 0.092 → 0.105 m | −0.22 m | 9 | 0.178 m |
| slip sigma 0.3 | old and new alike | 0.094 → 0.135 m | −0.24 m | 9 | 0.178 m |
| slip sigma 0.3, σ 0.25 before the walk | old | 0.163 → 0.193 m | −0.29 m | 10 | 0.081 m |
| slip sigma 0.3, σ 0.25 before the walk | new | 0.163 → 0.145 → 0.164 m | −0.29 m | 10 | 0.081 m |

What the rule does here:
- **To σ.** It changes σ only where σ is above the tag's own fix sigma. T06 seen alone at 1 to 2 m gives
  0.145–0.215 m, so in the first two cases nothing changes. With σ grown to 0.25 m first, the new rule brings σ down
  to the fix's 0.145 m, against 0.177 m under the old rule.
- **To the guard.** It changes nothing here. The guard's straight-move margin adds two σ capped at 0.15 m, and the
  turn margin adds one σ capped at 0.10 m. Both caps are reached at σ 0.075 and 0.10 m, so with σ above 0.10 m the
  guard decides the same under either rule: the same moves, the same refusal, the same depth.
- **The 0.081 m.** That depth in the grown-σ case comes from the first T06 fix after the turn, an ordinary
  inverse-variance blend, the same in both rules: the larger the σ, the harder the wrong tag pulls. A wrong tag
  trusted before a circle names it is the tag check's to catch, not the guard's.

**Mis-surveyed tags, the whole probe** (`tag_probe_rule.py`: the review's `tag_probe.py` with the tag check on in
both modes, the mode now being the rule). Set-up: the 20-tag room, each tag in turn moved 0.1, 0.3 or 0.5 m in each
of four directions in the world file, plus 8 clean seeds; three-episode B2 batches.
- **Without the slip sigma** (`tag_probe_rule-output.jsonl`, 248 runs per rule): **all 248 pairs are identical in
  every field.** At 0.1 m all complete. At 0.3 and 0.5 m every run halts `tag_survey` naming the moved tag (80 of 80),
  with no contact, at least 0.275 m inside the driving area, and the tracked pose within 0.067 m.
- **With the slip sigma 0.3, the 0.3 m shifts** (`tag_probe_rule-slip0.3-d0.3.jsonl`, 80 runs per rule): **again
  identical, 80 of 80**, and again all named. The slip sigma did change 16 of these runs against the run without it
  (moves, errors), so it was on.

Before `tag_survey` caught it, a tag surveyed 0.3 m wrong steered step fixes in 3 runs of 80: T14 −y twice, T17 +x
and T17 +y once each. At those fixes the sigma was at its 0.05 m floor and the tracked pose within 0.066 m of the
truth. In the 20-tag room σ stays near the floor, because nearly every step has a fix and the check names the tag at
the first circle that sees it with others, so the rule has nothing to act on. It acts where σ has grown above a
tag's own fix sigma: the long northward runs of the carpet table above, and the grown-σ walk.

### The dry runs of this commit (`--slip-sigma 0.3`, exact real arguments)

Log: `same-tag-dry-runs-log.txt`, the runs of the commit after `9dd80e9` (the same-tag rule, the range gate, the
early blind limit, the path share kept). The same four runs on `9dd80e9` (the drift record-only, no early limit)
gave the same numbers, move for move. Against §4's runs:

| Run | Result | Truth p95 / max against the car | Beyond 2 σ | σ max | Miss over path, max (halts above 0.6) | Net ratios | Drift halts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| plain | 10 of 10 | 0.008 / 0.020 m | 0 % | 0.177 m | 0.000 | 0.99–1.00 | none |
| north 0.78 | 10 of 10 (one: the B2 dead end, see below) | 0.057 / 0.256 m | 0 % | 0.188 m | 0.196 | 0.78–1.05 | none |
| north 0.67 | 10 of 10 | 0.122 / 0.305 m | 0 % | 0.162 m | 0.307 | 0.67–1.16 | none |
| north 0.60 | **10 of 10** (§4: `pose_uncertain` after 8) | 0.138 / 0.406 m | 1.6 % | 0.180 m (§4: 0.259) | 0.373 | 0.60–1.10 | none |

**Correction (later on 2026-11-25).** The "10 of 10" at north 0.78 in §4's and §6's dry-run tables (not §3's) counts an episode
the coded procedure stopped itself. Episode 3 (S3) ended after 74 steps at "E5 leg with no forward move and no E4",
the dead end of the frozen `kinsim_lite` B2. The manifest counts it as done (measured at its end circle), and so did
these summaries. Real batches ran that frozen procedure until the change recorded in `../b2-policy/`. With the room's
procedure (`kinsim_room.make_b2_policy`) all ten end by DONE.

