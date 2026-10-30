# Adversarial review of the pilot code (2026-10-29)

One independent reviewer (a Claude Opus 5.5 subagent in Cursor) applied four lenses (port fidelity, metric
correctness, harness and API correctness, test adequacy) to `envs/kinsim_lite.py`, `harness/tools_d5.py`,
`harness/anthropic_replay.py`, `metrics/pilot.py`, `tools/pilot_*.py` and `tests/test_pilot.py`, while the
paid runs were in progress. It ran local scripts only and edited nothing. Each finding was then checked
against the code by the main agent before any change.

## What the reviewer verified as correct (by running it)

- Simulator port: against the original `backstory_sim.run` with the same detector, 100 seeds (6,929 steps)
  gave identical reports, truth, counters and odometry (3,684 odometry, 1,834 position_fix, 1,189 prior_kept,
  222 beacon_fix steps; 286 `B<id>b` creations; 44 loop closures).
- Geometry port: 18,000 random calls gave identical outputs from `geometry.py` and the private `l2_geometry.py`.
- Gold calls: all 7,776 of B2's gold calls replayed through `run_tool` reproduce B2's prior, fix and new entries.
- `TOOLS`, `run_tool`, the prompt file and `as_observation` match the Module 4 originals (apart from the
  documented replay-mode changes).
- The harness with a mock oracle client: 40/40 valid steps, F1 1.0; an interrupted and resumed run equals an
  uninterrupted one; cost formula correct; thinking blocks passed back; two cache breakpoints.

## Findings and dispositions

| # | Severity | Finding | Verified | Change |
| --- | --- | --- | --- | --- |
| 1 | critical if the cap trips | A budget-cap abort mid-step was written as a permanent fallback row | confirmed | `replay_seed` now returns without writing the step; test `test_budget_cap_leaves_no_fallback_and_resume_completes`. Neither pilot run reached its cap (`budget_aborts` = 0 in `pilot_summary.json`) |
| 2 | major | `prf(0, 0, k)` gave F1 None instead of 0 | confirmed | F1 = 2TP/(2TP+FP+FN); test added |
| 3 | major | Association labels were bound from `new` claims that never reached the carried map | confirmed | Labels bind only when the label is in the carried map; "already mapped" comes from the previous map; tests added |
| 4 | major | The association scorer could not produce C10.4 (no FN for omitted or mislabelled re-sightings; dup flag from the reported id) | confirmed | Every detection is scored (an omitted re-sighting is FN); dup flag from the true id; `association_scores` gives C10.4 precision and recall |
| 5 | major | `map_errors` did not implement C10.3 | confirmed | Removed; `map_scores_c10` (ID within 0.30 m, phantoms, RMSE over correct entries, precision, recall) is used; test added |
| 6 | major (design) | No harness state correction (C5.4); counters reset on the agent's claimed pose source | confirmed | Not changed for the pilot; stated in the README and in the report's Procedure section |
| 7 | major (tests) | The gold self-test was circular; the harness had no tests | confirmed | Added a non-circular dispatcher replay test and a mock-client harness test |
| 8 | minor | A call with a string `det` counted as a match | confirmed | `call_matches` requires integer indices; test added; `non_int_det_calls` reported |
| 9 | minor | Steps without gold calls drop out of F1 silently | confirmed | `gold_skipped` is reported per seed |
| 10 | minor | Turns billed before an exception are not logged; exit code 0 on a failed seed | confirmed | Not changed; no exception occurred in the pilot runs |
| 11 | minor | `run.json` lacked hashes and was overwritten on resume | confirmed | Hashes of the prompt, `dv.json` and four code files added; a resume writes `run.resume-<time>.json` (applies to future runs) |
| 12 | minor | 45 of 100 generated worlds exceed the D3 0.8 m tag spacing (worst 0.843 m) | confirmed (gap along the walls: worst 0.843 m, 45 of 100 worlds; pilot seeds 1000-1004: 0.74-0.80 m, only seed 1004 above at 0.803 m) | Not changed (it would change the pilot worlds); stated in the report |
| 13 | minor | kinsim-lite simplifications: visibility from the axle midpoint, one frame per observation, `source: sim` instead of `kinsim` | confirmed | Not changed; stated as limits |
| 14 | minor | `trajectory_errors` silently truncated; lenient parser; step-0 fallback fields; docstring | confirmed | Length check added; the others are noted (no fallback occurred) |
| 15 | minor, unverified | Cache-breakpoint look-back; sync script path | not verified | No change; files are synced by tar from the public repo |

Tests after the fixes: `tests/test_pilot.py` 24 passed on the Mac (Python 3.13) and in `beaconmind-ros`
(Python 3.10).

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: the review (subagent), the verification and the fixes.
