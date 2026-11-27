# Real-log replay: exploratory paired differences and per-step traces (not pre-registered)

Set `b2-real-01 + b2-real-02 + b2-real-03 + b2-real-05 + b2-real-06`: 9 episodes in the main analysis, 1 flagged and kept apart; cm.

**Exploratory, not pre-registered.** The pre-registration reports the real logs descriptively (prereg.md section 6), the value compared here was chosen after the data, and there is no significance claim from a handful of episodes (evidence/M5/requirements.md). Each line is a paired difference: the study's estimator and the episodes below and above zero. Arm - B0 uses family 1's estimator: Hodges-Lehmann with its exact 95 % interval, or the median with its exact interval when the adjusted skewness exceeds 1 (the switch the pre-registration sets for families 1 and 2 only). Model - B2 and the comparisons between models use Hodges-Lehmann without the switch, as the study's pairwise comparisons do, with the median as a note. No p-values, no multiplicity correction, no verdicts. H2 (against B1) is not run: B1 needs oracle association, which the real logs do not have.

## Final-position error against the end circle (n = 8; exploratory, not pre-registered)

Arm - B0. B2 - B0 is the procedure's own gain over dead reckoning; a model that follows the procedure inherits it, so a model's gain over B0 is the procedure's, not the model's:

| Difference | n | estimate (cm) | 95 % interval (cm) | estimator | episodes below / above zero |
| --- | --- | --- | --- | --- | --- |
| B2 - B0 | 8 | -40.1 | -68.4 to -16.1 | Hodges-Lehmann | 8 / 0 |
| Opus 5.5 - B0 | 8 | -40.7 | -68.7 to -15.5 | Hodges-Lehmann | 8 / 0 |
| Qwen3.8 - B0 | 8 | -37.9 | -62.9 to -15.5 | Hodges-Lehmann | 8 / 0 |
| Gemma 4 - B0 | 8 | 64.2 | -38.6 to 375.1 | median | 2 / 6 |

Model - B2 (what the model adds to or loses against the procedure it was given):

| Difference | n | estimate (cm) | 95 % interval (cm) | estimator | episodes below / above zero | median (interval), a note |
| --- | --- | --- | --- | --- | --- | --- |
| Opus 5.5 - B2 | 8 | -0.1 | -0.8 to 1.0 | Hodges-Lehmann | 4 / 3 | -0.1 (-1.3 to 2.1) |
| Qwen3.8 - B2 | 8 | -0.4 | -2.9 to 16.5 | Hodges-Lehmann | 4 / 2 | -0.4 (-5.0 to 33.0) |
| Gemma 4 - B2 | 8 | 104.4 | 37.7 to 272.0 | Hodges-Lehmann | 2 / 6 | 79.2 (-2.1 to 463.6) |

- Opus 5.5 within 1 cm of B2 on every episode: no
- Qwen3.8 within 1 cm of B2 on every episode: no
- Gemma 4 within 1 cm of B2 on every episode: no

Between the models (mean rank, 1 = smallest error: Opus 5.5 1.81, Qwen3.8 1.44, Gemma 4 2.75):

| Difference | n | estimate (cm) | 95 % interval (cm) | estimator | episodes below / above zero | median (interval), a note |
| --- | --- | --- | --- | --- | --- | --- |
| Opus 5.5 - Qwen3.8 | 8 | 0.4 | -15.3 to 2.4 | Hodges-Lehmann | 2 / 5 | 0.4 (-30.9 to 4.4) |
| Opus 5.5 - Gemma 4 | 8 | -104.6 | -270.5 to -37.8 | Hodges-Lehmann | 7 / 1 | -78.7 (-461.5 to 1.7) |
| Qwen3.8 - Gemma 4 | 8 | -106.6 | -255.6 to -37.5 | Hodges-Lehmann | 7 / 1 | -79.2 (-430.6 to 1.2) |

## Final-position error against the last step's logged truth (tracker-dependent) (n = 9; exploratory, not pre-registered)

Arm - B0. B2 - B0 is the procedure's own gain over dead reckoning; a model that follows the procedure inherits it, so a model's gain over B0 is the procedure's, not the model's:

| Difference | n | estimate (cm) | 95 % interval (cm) | estimator | episodes below / above zero |
| --- | --- | --- | --- | --- | --- |
| B2 - B0 | 9 | -31.0 | -56.2 to -10.4 | Hodges-Lehmann | 9 / 0 |
| Opus 5.5 - B0 | 9 | -31.5 | -55.8 to -10.6 | Hodges-Lehmann | 9 / 0 |
| Qwen3.8 - B0 | 9 | -30.6 | -51.3 to -10.6 | Hodges-Lehmann | 9 / 0 |
| Gemma 4 - B0 | 9 | 79.0 | -18.2 to 158.2 | median | 2 / 7 |

Model - B2 (what the model adds to or loses against the procedure it was given):

| Difference | n | estimate (cm) | 95 % interval (cm) | estimator | episodes below / above zero | median (interval), a note |
| --- | --- | --- | --- | --- | --- | --- |
| Opus 5.5 - B2 | 9 | -0.0 | -0.9 to 1.1 | Hodges-Lehmann | 4 / 4 | 0.0 (-1.0 to 0.5) |
| Qwen3.8 - B2 | 9 | -0.4 | -1.5 to 15.5 | Hodges-Lehmann | 5 / 2 | -0.4 (-1.6 to 2.1) |
| Gemma 4 - B2 | 9 | 105.3 | 36.0 to 265.4 | Hodges-Lehmann | 1 / 8 | 83.2 (1.3 to 221.7) |

- Opus 5.5 within 1 cm of B2 on every episode: no
- Qwen3.8 within 1 cm of B2 on every episode: no
- Gemma 4 within 1 cm of B2 on every episode: no

Between the models (mean rank, 1 = smallest error: Opus 5.5 1.72, Qwen3.8 1.61, Gemma 4 2.67):

| Difference | n | estimate (cm) | 95 % interval (cm) | estimator | episodes below / above zero | median (interval), a note |
| --- | --- | --- | --- | --- | --- | --- |
| Opus 5.5 - Qwen3.8 | 9 | 0.1 | -14.7 to 1.3 | Hodges-Lehmann | 3 / 5 | 0.4 (-2.2 to 1.5) |
| Opus 5.5 - Gemma 4 | 9 | -105.7 | -264.3 to -36.2 | Hodges-Lehmann | 8 / 1 | -84.1 (-221.4 to -1.3) |
| Qwen3.8 - Gemma 4 | 9 | -107.0 | -249.4 to -35.5 | Hodges-Lehmann | 7 / 2 | -83.2 (-223.7 to 0.8) |

## Final-position error against the recomputed truth (tracker-dependent) (n = 9; exploratory, not pre-registered)

Arm - B0. B2 - B0 is the procedure's own gain over dead reckoning; a model that follows the procedure inherits it, so a model's gain over B0 is the procedure's, not the model's:

| Difference | n | estimate (cm) | 95 % interval (cm) | estimator | episodes below / above zero |
| --- | --- | --- | --- | --- | --- |
| B2 - B0 | 9 | -34.5 | -59.7 to -14.8 | Hodges-Lehmann | 9 / 0 |
| Opus 5.5 - B0 | 9 | -35.3 | -59.0 to -15.0 | Hodges-Lehmann | 9 / 0 |
| Qwen3.8 - B0 | 9 | -33.4 | -51.5 to -15.0 | Hodges-Lehmann | 9 / 0 |
| Gemma 4 - B0 | 9 | 78.0 | -17.9 to 158.2 | median | 2 / 7 |

Model - B2 (what the model adds to or loses against the procedure it was given):

| Difference | n | estimate (cm) | 95 % interval (cm) | estimator | episodes below / above zero | median (interval), a note |
| --- | --- | --- | --- | --- | --- | --- |
| Opus 5.5 - B2 | 9 | 0.2 | -0.8 to 1.3 | Hodges-Lehmann | 3 / 5 | 0.3 (-0.8 to 1.6) |
| Qwen3.8 - B2 | 9 | -0.0 | -1.2 to 15.8 | Hodges-Lehmann | 4 / 3 | 0.0 (-1.7 to 2.0) |
| Gemma 4 - B2 | 9 | 106.6 | 38.6 to 265.4 | Hodges-Lehmann | 1 / 8 | 83.2 (4.7 to 221.7) |

- Opus 5.5 within 1 cm of B2 on every episode: no
- Qwen3.8 within 1 cm of B2 on every episode: no
- Gemma 4 within 1 cm of B2 on every episode: no

Between the models (mean rank, 1 = smallest error: Opus 5.5 1.72, Qwen3.8 1.50, Gemma 4 2.78):

| Difference | n | estimate (cm) | 95 % interval (cm) | estimator | episodes below / above zero | median (interval), a note |
| --- | --- | --- | --- | --- | --- | --- |
| Opus 5.5 - Qwen3.8 | 9 | 0.2 | -14.5 to 1.5 | Hodges-Lehmann | 3 / 5 | 0.4 (-2.8 to 1.5) |
| Opus 5.5 - Gemma 4 | 9 | -106.3 | -264.3 to -39.0 | Hodges-Lehmann | 8 / 1 | -84.0 (-221.4 to -6.0) |
| Qwen3.8 - Gemma 4 | 9 | -107.1 | -249.4 to -39.3 | Hodges-Lehmann | 8 / 1 | -83.2 (-223.7 to -6.4) |

## ATE over all steps against the logged truth (tracker-dependent) (n = 9; exploratory, not pre-registered)

Arm - B0. B2 - B0 is the procedure's own gain over dead reckoning; a model that follows the procedure inherits it, so a model's gain over B0 is the procedure's, not the model's:

| Difference | n | estimate (cm) | 95 % interval (cm) | estimator | episodes below / above zero |
| --- | --- | --- | --- | --- | --- |
| B2 - B0 | 9 | -8.1 | -35.3 to -3.2 | median | 8 / 1 |
| Opus 5.5 - B0 | 9 | -7.9 | -34.7 to -0.9 | median | 8 / 1 |
| Qwen3.8 - B0 | 9 | -8.0 | -31.8 to -0.7 | median | 8 / 1 |
| Gemma 4 - B0 | 9 | 47.5 | 12.6 to 94.0 | Hodges-Lehmann | 2 / 7 |

Model - B2 (what the model adds to or loses against the procedure it was given):

| Difference | n | estimate (cm) | 95 % interval (cm) | estimator | episodes below / above zero | median (interval), a note |
| --- | --- | --- | --- | --- | --- | --- |
| Opus 5.5 - B2 | 9 | 0.3 | -0.5 to 3.0 | Hodges-Lehmann | 2 / 7 | 0.1 (-0.0 to 0.6) |
| Qwen3.8 - B2 | 9 | 0.0 | -0.6 to 3.0 | Hodges-Lehmann | 5 / 4 | -0.0 (-0.5 to 3.5) |
| Gemma 4 - B2 | 9 | 64.4 | 18.5 to 115.7 | Hodges-Lehmann | 0 / 9 | 51.5 (6.4 to 122.5) |

- Opus 5.5 within 1 cm of B2 on every episode: no
- Qwen3.8 within 1 cm of B2 on every episode: no
- Gemma 4 within 1 cm of B2 on every episode: no

Between the models (mean rank, 1 = smallest error: Opus 5.5 1.61, Qwen3.8 1.39, Gemma 4 3.00):

| Difference | n | estimate (cm) | 95 % interval (cm) | estimator | episodes below / above zero | median (interval), a note |
| --- | --- | --- | --- | --- | --- | --- |
| Opus 5.5 - Qwen3.8 | 9 | 0.1 | -1.4 to 0.5 | Hodges-Lehmann | 3 / 5 | 0.0 (-0.2 to 0.3) |
| Opus 5.5 - Gemma 4 | 9 | -63.0 | -115.2 to -18.5 | Hodges-Lehmann | 9 / 0 | -51.3 (-122.4 to -3.6) |
| Qwen3.8 - Gemma 4 | 9 | -63.2 | -113.8 to -18.5 | Hodges-Lehmann | 9 / 0 | -51.4 (-122.7 to -3.6) |

## The steps flagged slip_suspected (4)

The room prompt's rule 2 composes such a step with forward and left set to 0; the coded procedure (B2) has no such rule. Whether the flagged move happened shows at the next tag fix: each arm's estimate from the step before any arm's fix, against the fix B2 then takes (cm). The batch's tracked truth composes the same odometry, so it cannot tell.

| Seed/step | odometry forward (m) | B2 composed | Opus 5.5 composed | Qwen3.8 composed | Gemma 4 composed | first tag fix (step: by) | B2's fix at step | distance to it from the step before: B2 / Opus 5.5 / Qwen3.8 / Gemma 4 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1001/24 | 0.24 | 0.24 | 0.00 | 0.00 |  | 24: B2, Opus 5.5, Qwen3.8 | 24 | 20.2 / 22.5 / 23.4 / 3.6 |
| 3001/41 | 0.25 | 0.25 | 0.00 | 0.00 |  | 47: Opus 5.5, Qwen3.8, Gemma 4 | 48 | 20.4 / 5.4 / 5.4 / 6.7 |
| 3002/78 | 0.25 | 0.25 | 0.00 | 0.00 | 0.00 | 78: B2, Opus 5.5, Qwen3.8 | 78 | 24.2 / 24.5 / 23.3 / 142.2 |
| 4001/81 | 0.24 | 0.24 | 0.00 | 0.00 | 0.24 | 81: B2, Qwen3.8 | 81 | 21.8 / 22.5 / 17.0 / 171.4 |

## Run behaviour (the main episodes)

| Arm | steps | valid | fallbacks | repaired | step errors | calls per step | tool names as the procedure's | mean / median / p95 s per step | cost (US$) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| procedure | 805 of 805 | 805 | 0 | 0 | 0 | 3.20 |  | 0.0 / 0.0 / 0.0 | 0.00 |
| Opus 5.5 | 805 of 805 | 805 | 0 | 0 | 0 | 3.33 | 97 % | 18.2 / 18.4 / 24.6 | 60.41 |
| Qwen3.8 | 805 of 805 | 803 | 2 | 57 | 0 | 3.92 | 81 % | 127.6 / 118.5 / 226.4 | 0.00 |
| Gemma 4 | 805 of 805 | 768 | 37 | 0 | 12 | 2.60 | 49 % | 983.6 / 869.5 / 1592.7 | 0.00 |

`tool names as the procedure's`: per step, the share of tool calls (by name, `move` left out) the arm has in common with the coded procedure on the same input; the study's call precision and recall also match the arguments, which the trimmed rows here do not keep.

Tag fixes claimed (pose source beacon_fix, position_fix or relocalised) and how many of them came without a `fix_pose` call that step (a fix the arm did not compute with the tools):

- Opus 5.5: 329 claimed, 0 without `fix_pose`
- Qwen3.8: 326 claimed, 0 without `fix_pose`
- Gemma 4: 179 claimed, 74 without `fix_pose`

Pose source as the procedure's (the steps where both reported one; the study's pose-source agreement), and the arm's differences from the procedure:

- Opus 5.5: 98.5 % of 805 steps; position_fix instead of prior_kept: 5; prior_kept instead of position_fix: 5; beacon_fix instead of position_fix: 1; position_fix instead of beacon_fix: 1
- Qwen3.8: 98.5 % of 803 steps; prior_kept instead of position_fix: 5; position_fix instead of prior_kept: 4; beacon_fix instead of position_fix: 1; prior_kept instead of beacon_fix: 1; odometry instead of position_fix: 1
- Gemma 4: 56.8 % of 768 steps; prior_kept instead of odometry: 65; prior_kept instead of position_fix: 51; odometry instead of position_fix: 48; prior_kept instead of beacon_fix: 47; odometry instead of beacon_fix: 34; position_fix instead of odometry: 24; position_fix instead of beacon_fix: 13; beacon_fix instead of odometry: 13; position_fix instead of prior_kept: 10; beacon_fix instead of position_fix: 7; beacon_fix instead of prior_kept: 6; prior instead of odometry: 5; odometry instead of prior_kept: 5; none instead of odometry: 1; relocalised instead of odometry: 1; prior instead of beacon_fix: 1; relocalised instead of beacon_fix: 1

## Per-step traces

Error against the batch's logged (tracked) truth at 25/50/75/100 % of each episode (tracker-dependent), and where each LLM arm's estimate first parts from B2's by more than 5 cm (truth-free):

| Seed | steps | B0 25/50/75/100 % | B2 25/50/75/100 % | Opus 5.5 25/50/75/100 % | Qwen3.8 25/50/75/100 % | Gemma 4 25/50/75/100 % | Opus 5.5 parts from B2 (first step; steps beyond; largest gap) | Qwen3.8 parts from B2 (first step; steps beyond; largest gap) | Gemma 4 parts from B2 (first step; steps beyond; largest gap) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1001 | 83 | 0.7/12.7/16.5/20.0 | 0.7/3.8/3.9/3.1 | 1.5/4.4/5.9/3.5 | 2.1/5.2/6.9/2.7 | 24.1/78.5/72.8/74.6 | 62; 1; 8.5 cm at 62 | 62; 1; 9.5 cm at 62 | 18; 64; 79.4 cm at 39 |
| 2001 | 56 | 0.8/1.5/2.5/6.4 | 0.8/3.3/1.1/2.8 | 1.0/3.3/1.1/1.9 | 1.0/3.3/1.1/2.8 | 2.8/2.8/98.0/86.0 | never | never | 25; 28; 99.0 cm at 39 |
| 2002 | 62 | 1.6/13.5/26.4/25.4 | 1.6/10.3/16.2/20.3 | 1.6/8.4/9.8/19.0 | 1.6/8.4/9.8/18.7 | 14.4/41.3/35.1/9.0 | 45; 2; 7.8 cm at 46 | 45; 2; 7.8 cm at 46 | 13; 27; 51.1 cm at 46 |
| 3001 | 56 | 2.5/5.3/13.9/32.3 | 2.5/2.9/7.6/6.9 | 2.6/3.8/30.8/6.8 | 2.6/3.8/30.8/9.0 | 2.6/5.1/31.8/8.2 | 41; 7; 25.1 cm at 41 | 41; 7; 25.1 cm at 41 | 20; 10; 26.1 cm at 42 |
| 3002 | 81 | 3.1/7.3/27.3/43.7 | 13.4/8.0/18.5/8.2 | 13.4/7.0/19.1/7.2 | 13.4/10.0/18.5/6.8 | 54.4/20.5/176.5/137.7 | never | 46; 7; 6.4 cm at 50 | 16; 63; 172.7 cm at 60 |
| 4001 | 114 | 6.5/17.5/26.5/62.0 | 14.9/14.1/8.1/10.1 | 13.6/15.1/9.1/10.6 | 14.3/13.4/7.7/9.0 | 4.1/15.7/168.3/145.2 | 81; 1; 22.5 cm at 81 | 50; 11; 18.0 cm at 104 | 13; 94; 168.3 cm at 81 |
| 4002 | 132 | 9.6/17.3/45.6/117.5 | 5.9/13.3/9.8/29.1 | 5.0/11.0/10.7/31.3 | 5.0/13.6/10.7/61.1 | 114.9/238.1/36.5/481.9 | 34; 13; 9.2 cm at 67 | 67; 14; 33.1 cm at 131 | 13; 119; 486.9 cm at 121 |
| 4003 | 141 | 14.7/52.2/75.0/84.2 | 8.9/18.6/16.3/19.7 | 10.3/17.5/16.0/20.0 | 9.6/18.6/16.0/17.7 | 7.5/14.0/238.5/241.4 | 109; 7; 24.6 cm at 119 | never | 36; 98; 259.6 cm at 125 |
| 5001 | 80 | 5.1/13.0/10.2/25.7 | 1.6/5.5/9.5/13.0 | 1.6/5.5/9.5/13.0 | 1.6/5.5/9.5/13.0 | 2.3/3.9/23.6/91.1 | never | never | 16; 47; 78.2 cm at 79 |
| 5002 (flagged) | 45 | 4.9/3.4/6.5/8.7 | 4.9/8.3/13.2/6.7 | 4.8/7.4/12.3/19.3 | 4.8/7.4/16.4/18.5 | 5.5/13.3/59.4/57.3 | 44; 1; 12.7 cm at 44 | 32; 5; 12.0 cm at 44 | 14; 31; 72.4 cm at 32 |
