# Real-log replay: exploratory paired differences and per-step traces (not pre-registered)

Set `b2-real-01 + b2-real-02 + b2-real-03 + b2-real-05 + b2-real-06`: 9 episodes in the main analysis, 1 flagged and kept apart; cm.

**Exploratory, not pre-registered.** The pre-registration reports the real logs descriptively (prereg.md section 6), the value compared here was chosen after the data, and there is no significance claim from a handful of episodes (evidence/M5/requirements.md). Each line is a paired difference: the study's estimator (Hodges-Lehmann with its exact 95 % interval, or the median with its exact interval when the skewness switch applies) and the episodes below and above zero. No p-values, no multiplicity correction, no verdicts. H2 (against B1) is not run: B1 needs oracle association, which the real logs do not have.

## Final-position error against the end circle (n = 8; exploratory, not pre-registered)

Arm - B0. B2 - B0 is the procedure's own gain over dead reckoning; a model that follows the procedure inherits it, so a model's gain over B0 is the procedure's, not the model's:

| Difference | n | estimate (cm) | 95 % interval (cm) | estimator | episodes below / above zero |
| --- | --- | --- | --- | --- | --- |
| B2 - B0 | 8 | -40.1 | -68.4 to -16.1 | Hodges-Lehmann | 8 / 0 |
| Opus 5.5 - B0 | 8 | -40.7 | -68.7 to -15.5 | Hodges-Lehmann | 8 / 0 |

Model - B2 (what the model adds to or loses against the procedure it was given):

| Difference | n | estimate (cm) | 95 % interval (cm) | estimator | episodes below / above zero |
| --- | --- | --- | --- | --- | --- |
| Opus 5.5 - B2 | 8 | -0.1 | -0.8 to 1.0 | Hodges-Lehmann | 4 / 3 |

- Opus 5.5 within 1 cm of B2 on every episode: no

## Final-position error against the last step's logged truth (tracker-dependent) (n = 9; exploratory, not pre-registered)

Arm - B0. B2 - B0 is the procedure's own gain over dead reckoning; a model that follows the procedure inherits it, so a model's gain over B0 is the procedure's, not the model's:

| Difference | n | estimate (cm) | 95 % interval (cm) | estimator | episodes below / above zero |
| --- | --- | --- | --- | --- | --- |
| B2 - B0 | 9 | -31.0 | -56.2 to -10.4 | Hodges-Lehmann | 9 / 0 |
| Opus 5.5 - B0 | 9 | -31.5 | -55.8 to -10.6 | Hodges-Lehmann | 9 / 0 |

Model - B2 (what the model adds to or loses against the procedure it was given):

| Difference | n | estimate (cm) | 95 % interval (cm) | estimator | episodes below / above zero |
| --- | --- | --- | --- | --- | --- |
| Opus 5.5 - B2 | 9 | -0.0 | -0.9 to 1.1 | Hodges-Lehmann | 4 / 4 |

- Opus 5.5 within 1 cm of B2 on every episode: no

## Final-position error against the recomputed truth (tracker-dependent) (n = 9; exploratory, not pre-registered)

Arm - B0. B2 - B0 is the procedure's own gain over dead reckoning; a model that follows the procedure inherits it, so a model's gain over B0 is the procedure's, not the model's:

| Difference | n | estimate (cm) | 95 % interval (cm) | estimator | episodes below / above zero |
| --- | --- | --- | --- | --- | --- |
| B2 - B0 | 9 | -34.5 | -59.7 to -14.8 | Hodges-Lehmann | 9 / 0 |
| Opus 5.5 - B0 | 9 | -35.3 | -59.0 to -15.0 | Hodges-Lehmann | 9 / 0 |

Model - B2 (what the model adds to or loses against the procedure it was given):

| Difference | n | estimate (cm) | 95 % interval (cm) | estimator | episodes below / above zero |
| --- | --- | --- | --- | --- | --- |
| Opus 5.5 - B2 | 9 | 0.2 | -0.8 to 1.3 | Hodges-Lehmann | 3 / 5 |

- Opus 5.5 within 1 cm of B2 on every episode: no

## ATE over all steps against the logged truth (tracker-dependent) (n = 9; exploratory, not pre-registered)

Arm - B0. B2 - B0 is the procedure's own gain over dead reckoning; a model that follows the procedure inherits it, so a model's gain over B0 is the procedure's, not the model's:

| Difference | n | estimate (cm) | 95 % interval (cm) | estimator | episodes below / above zero |
| --- | --- | --- | --- | --- | --- |
| B2 - B0 | 9 | -8.1 | -35.3 to -3.2 | median | 8 / 1 |
| Opus 5.5 - B0 | 9 | -7.9 | -34.7 to -0.9 | median | 8 / 1 |

Model - B2 (what the model adds to or loses against the procedure it was given):

| Difference | n | estimate (cm) | 95 % interval (cm) | estimator | episodes below / above zero |
| --- | --- | --- | --- | --- | --- |
| Opus 5.5 - B2 | 9 | 0.1 | -0.0 to 0.6 | median | 2 / 7 |

- Opus 5.5 within 1 cm of B2 on every episode: no

## Run behaviour (the main episodes)

| Arm | steps | valid | fallbacks | repaired | step errors | calls per step | tool names as the procedure's | mean / median / p95 s per step | cost (US$) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| procedure | 805 of 805 | 805 | 0 | 0 | 0 | 3.20 |  | 0.0 / 0.0 / 0.0 | 0.00 |
| Opus 5.5 | 805 of 805 | 805 | 0 | 0 | 0 | 3.33 | 97 % | 18.2 / 18.4 / 24.6 | 60.41 |

`tool names as the procedure's`: per step, the share of tool calls (by name, `move` left out) the arm has in common with the coded procedure on the same input; the study's call precision and recall also match the arguments, which the trimmed rows here do not keep.

Pose source as the procedure's (the steps where both reported one; the study's pose-source agreement), and the arm's differences from the procedure:

- Opus 5.5: 98.5 % of 805 steps; position_fix instead of prior_kept: 5; prior_kept instead of position_fix: 5; beacon_fix instead of position_fix: 1; position_fix instead of beacon_fix: 1

## Per-step traces

Error against the batch's logged (tracked) truth at 25/50/75/100 % of each episode (tracker-dependent), and where each LLM arm's estimate first parts from B2's by more than 5 cm (truth-free):

| Seed | steps | B0 25/50/75/100 % | B2 25/50/75/100 % | Opus 5.5 25/50/75/100 % | Opus 5.5 parts from B2 (first step; steps beyond; largest gap) |
| --- | --- | --- | --- | --- | --- |
| 1001 | 83 | 0.7/12.7/16.5/20.0 | 0.7/3.8/3.9/3.1 | 1.5/4.4/5.9/3.5 | 62; 1; 8.5 cm at 62 |
| 2001 | 56 | 0.8/1.5/2.5/6.4 | 0.8/3.3/1.1/2.8 | 1.0/3.3/1.1/1.9 | never |
| 2002 | 62 | 1.6/13.5/26.4/25.4 | 1.6/10.3/16.2/20.3 | 1.6/8.4/9.8/19.0 | 45; 2; 7.8 cm at 46 |
| 3001 | 56 | 2.5/5.3/13.9/32.3 | 2.5/2.9/7.6/6.9 | 2.6/3.8/30.8/6.8 | 41; 7; 25.1 cm at 41 |
| 3002 | 81 | 3.1/7.3/27.3/43.7 | 13.4/8.0/18.5/8.2 | 13.4/7.0/19.1/7.2 | never |
| 4001 | 114 | 6.5/17.5/26.5/62.0 | 14.9/14.1/8.1/10.1 | 13.6/15.1/9.1/10.6 | 81; 1; 22.5 cm at 81 |
| 4002 | 132 | 9.6/17.3/45.6/117.5 | 5.9/13.3/9.8/29.1 | 5.0/11.0/10.7/31.3 | 34; 13; 9.2 cm at 67 |
| 4003 | 141 | 14.7/52.2/75.0/84.2 | 8.9/18.6/16.3/19.7 | 10.3/17.5/16.0/20.0 | 109; 7; 24.6 cm at 119 |
| 5001 | 80 | 5.1/13.0/10.2/25.7 | 1.6/5.5/9.5/13.0 | 1.6/5.5/9.5/13.0 | never |
| 5002 (flagged) | 45 | 4.9/3.4/6.5/8.7 | 4.9/8.3/13.2/6.7 | 4.8/7.4/12.3/19.3 | 44; 1; 12.7 cm at 44 |
