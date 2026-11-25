# Real-log replay, set real-2026-11-25 (interim: Opus 5.5 only)

Batch `b2-real-01 + b2-real-02 + b2-real-03` (config 611d90a41329, 1b3ab20f9758, af676fc3b9e6, real car: True); 5 episodes, 338 steps; world `configs/arenas/real-room.json` (sha12 35572d7656f3); configs/dv-real.json sha12 ea2cd23f9186 (differs from the frozen file in reject_range_above_m, sigma_bearing_deg, sigma_range_a_m, sigma_range_b_per_m).

Final-position error at the last step against the batch's truth (tag resection against the surveyed tags, in the map frame of the episode's start), in cm. `vs end circle`: against the position of the full circle the batch turns after the episode; `vs simulator truth`: only a dry run has it.

| Arm | n | median | IQR | min | max | median heading error (deg) | median truth sigma | vs end circle (median) | vs simulator truth (median) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 | 5 | 27.2 | 19.7 to 33.2 | 7.0 | 43.9 | 7.7 | 5.0 | 28.8 | none |
| B2 | 5 | 6.9 | 3.1 to 8.2 | 2.8 | 20.3 | 3.7 | 5.0 | 6.1 | none |
| procedure | 5 | 6.9 | 3.1 to 8.2 | 2.8 | 20.3 | 3.7 | 5.0 | 6.1 | none |
| claude-opus-5-5 | 5 | 6.8 | 3.5 to 7.2 | 1.9 | 19.0 | 3.7 | 5.0 | 5.9 | none |

Per episode (final-position error, cm; `truth sigma`: the batch's own uncertainty of its truth):

| Episode | Scenario | Steps | truth sigma | B0 | B2 | procedure | claude-opus-5-5 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| b2-real-01 ep01-a1 | S1 | 83 | 5.0 | 19.7 | 3.1 | 3.1 | 3.5 |
| b2-real-02 ep01-a1 | S1 | 56 | 5.0 | 7.0 | 2.8 | 2.8 | 1.9 |
| b2-real-02 ep02-a1 | S2 | 62 | 5.8 | 27.2 | 20.3 | 20.3 | 19.0 |
| b2-real-03 ep01-a1 | S1 | 56 | 5.0 | 33.2 | 6.9 | 6.9 | 6.8 |
| b2-real-03 ep02-a1 | S2 | 81 | 5.6 | 43.9 | 8.2 | 8.2 | 7.2 |

Runs: replayed steps (of the logs' steps), valid reports, harness fallbacks, repaired reports, step errors, `move` calls (the replay rule wants 0), cost, seconds per step.

| Arm | steps | valid | fallbacks | repaired | errors | move calls | cost (US$) | mean s/step | p95 s/step |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| procedure | 338 of 338 | 338 | 0 | 0 | 0 | 0 | 0.00 | 0.0 | 0.0 |
| claude-opus-5-5 | 338 of 338 | 338 | 0 | 0 | 0 | 7 | 23.90 | 17.3 | 22.5 |

Not replayed: b2-real-02 ep03-a1 (did not end normally: {'code': 'odometry_scale', 'detail': 'tag fixes land -28 % (+-8 %) of the distance from where the odometry puts the car (10.5 m driven, 37 fixes; limit 12 %): the encoder scale is wrong, or the tags are', 'time_utc': '2026-11-25T12:24:02Z', 'safety': True})
