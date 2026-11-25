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
