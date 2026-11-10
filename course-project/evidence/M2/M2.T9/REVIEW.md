# M2.T9 (B1, GTSAM iSAM2) — build notes, adversarial review and fixes (2026-11-10)

Code: `beaconmind/src/beaconmind/baselines/b1_gtsam.py`, `tools/b1_run.py`, `beaconmind/tests/test_b1_gtsam.py`.
Runs: Spark host venv `~/.venvs/beaconmind` (Python 3.12, gtsam 4.3.0), dev seeds only (1000–1019).

## Decision: the scored B1 trajectory is the online estimate (`b1_mode_decision`)

| Option | For | Against |
| --- | --- | --- |
| **Online** (x_t's iSAM2 estimate right after step t) — chosen | Causal, like every other arm (B0, B2 and each LLM only use data up to step t), so H2 compares estimators with the same information except association | Worse than smoothing |
| Smoothed (final estimate of every pose) | The best B1 can do | Uses data after step t that no other arm has; the online/smoothed ATE ratio on dev seeds was 1.12 without drift and 1.31 with drift (review finding 2), which would move H2's ratio by up to 30 % |

The smoothed trajectory is kept in every output file as secondary data. The report's earlier word "offline"
(Section IV-B) refers to running B1 after the episode on the recorded log, not to smoothing; the report must say "online
estimate" when it is next edited (M5.T13).

## Build notes

- GTSAM's ISAM2 default wildfire threshold (0.001) with `calculateEstimate` left the final trajectory up to 1.3 mm from
  the batch Levenberg-Marquardt optimum (dev seeds 1000, 1004; graph error 188.58 vs 187.69). With wildfire 0 and
  `calculateBestEstimate` the difference is below 0.02 mm. Relinearisation thresholds from 0.01 down to 1e-6 changed
  nothing.

## Adversarial review (one reviewer, B1 lens; 9 findings) — each verified, then fixed

| # | Severity | Finding | Verified | Fix |
| --- | --- | --- | --- | --- |
| 1 | major | Under the 2 % drift the odometry sigmas are zero-mean but the data are biased: turn residuals +1.81 sigma mean (2.23 RMS), forward +0.87 (1.33 RMS); a self-calibrating variant had 1.75x lower median ATE on 99 dev seeds, so B1 was not an upper bound in the block H2 is tested in | Confirmed by arithmetic: 2 % of 30 deg = 0.6 deg = 2.0 sigma of the 0.30 deg turn sigma; 2 % of 0.25 m = 0.005 m = 0.87 of 0.0058 m | B1 now estimates two odometry scales (forward, turn) with a weak prior N(1, 0.05) inside the graph (`calibrate_scale=True`, the study's B1). Dev seeds 1010–1019 at 2 % drift: median online ATE 1.11 cm (uncalibrated 2.09 cm, B2 13.01 cm, B0 15.60 cm); scales estimated 1.017–1.031 (true 1.02). The uncalibrated version stays available (`--no-scale`) |
| 2 | major | Which B1 trajectory enters H2 was not fixed | Confirmed (`b1_run.py` wrote both, marked neither) | Online, decided above; `b1_run.py` writes `"scored": "online"`, `study_analyze.py` refuses any other |
| 3 | major | The tests did not catch mutations that weaken B1 (swapped bearing/range sigmas, odometry sigmas x10, default wildfire) | Confirmed by the reviewer's mutation run | New tests: factor sigmas, their order and units read from the built factors; normalised residuals RMS in 0.9–1.1 without drift; scale recovery and an ATE regression bound at 2 % drift; batch check of positions, headings and tags; causality including heading. Mutation run below |
| 4 | minor | Noiseless test tolerance 1e-3 against an actual 1.8e-16 | Confirmed | 1e-6 m and 1e-4 deg, online and smoothed, every mapped tag (both copies of duplicated IDs), both variants, scales = 1 |
| 5 | minor | `b1_run.py` crashed on seeds the recorder skipped; bare KeyError on a log without a `noise` block | Confirmed (recorder skips NotImplementedError seeds) | Missing seeds are listed and skipped; a log without the kinsim noise keys is refused with a clear message |
| 6 | minor | B1's scored poses were unrounded while every reported pose is rounded | Confirmed (rounding adds about 4 mm RMS) | `study_analyze.py` scores B0 and B1 at report precision (`kinsim_lite.rp`) |
| 7 | minor | The docstring's 1.3 mm wildfire claim was not reproduced; `batch_check` compared positions only | Partly: the 1.3 mm was measured with `calculateEstimate` (the reviewer kept `calculateBestEstimate`) | Docstring states the exact setting; `batch_check` now compares positions, headings and tags; `b1_run.py` flags a mismatch and exits 1 |
| 8 | minor | The 1 mm / 0.05 deg odometry terms are informative kinsim facts, wrong for real-car logs | Confirmed | Docstring says so; B1 refuses logs without the kinsim noise block. B1 is not planned on real logs (plan §3.6 work list 3.6 replays only the LLM arms) |
| 9 | nit | "Deterministic" output contains `seconds`; provenance lacked commit, runner hash, solver settings; tests not marked `gtsam`; causality test ignored heading | Confirmed | All fixed (`pytestmark = pytest.mark.gtsam`; run with `-m gtsam`) |

Checked and found correct by the reviewer (not repeated here): Pose2 composition equals `compose_odometry`; the
between-factor and bearing-range conventions; no ground truth beyond `_tag` is read; landmark keys per physical tag;
the online estimate equals a batch solve of each prefix; edge cases (one step, no detections, tags seen once).

## Mutation test of the new tests (Spark, `BM_COURSE_ROOT` set; control first)

```
control: 11 passed in 2.55s
swap_sigmas: 2 failed, 9 passed   (test_detection_factor_order_units_and_sigmas, test_scale_calibration_...)
odo_x10: 3 failed, 8 passed       (test_odometry_factor_sigmas[True], [False], test_scale_calibration_...)
odo_div3: 2 failed, 9 passed      (test_odometry_factor_sigmas[True], [False])
old_solver: 1 failed, 10 passed   (test_b1_beats_dead_reckoning_and_b2_and_matches_batch)
online_is_smoothed: 1 failed      (test_online_is_causal)
no_scale_default: 1 failed        (test_scale_calibration_learns_the_drift_and_beats_the_uncalibrated_graph)
bearing_deg_unit: 4 failed        (factor sigmas, calibration, scale, batch tests)
scale_jac_sign: 2 failed          (scale calibration, batch tests)
```

A first mutation run without `BM_COURSE_ROOT` "caught" every mutation in 0.24 s; its control failed too (the copied
package could not find the course root), so those results were discarded.

## Final test run (Spark host venv)

`~/.venvs/beaconmind/bin/python -m pytest -q -p no:cacheprovider -m gtsam tests/test_b1_gtsam.py` → `11 passed in 3.66s`.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote B1, ran the checks, verified and fixed the review
findings (the review itself was an independent Claude Opus 5.5 subagent).
