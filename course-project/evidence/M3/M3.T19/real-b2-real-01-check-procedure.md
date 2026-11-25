# Real batch b2-real-01, episode 1: free check of the replay pipeline

Batch `b2-real-01` (config 611d90a41329, real car: True); 1 episodes, 83 steps; world `configs/arenas/real-room.json` (sha12 35572d7656f3); configs/dv-real.json sha12 ea2cd23f9186 (differs from the frozen file in reject_range_above_m, sigma_bearing_deg, sigma_range_a_m, sigma_range_b_per_m).

Final-position error at the last step against the batch's truth (tag resection against the surveyed tags, in the map frame of the episode's start), in cm. `vs end circle`: against the position of the full circle the batch turns after the episode; `vs simulator truth`: only a dry run has it.

| Arm | n | median | IQR | min | max | median heading error (deg) | median truth sigma | vs end circle (median) | vs simulator truth (median) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 | 1 | 19.7 | 19.7 to 19.7 | 19.7 | 19.7 | 7.7 | 5.0 | 26.1 | none |
| B2 | 1 | 3.1 | 3.1 to 3.1 | 3.1 | 3.1 | 3.7 | 5.0 | 3.4 | none |
| procedure (stand-in) | 1 | 3.1 | 3.1 to 3.1 | 3.1 | 3.1 | 3.7 | 5.0 | 3.4 | none |

Per episode (final-position error, cm; `truth sigma`: the batch's own uncertainty of its truth):

| Episode | Scenario | Steps | truth sigma | B0 | B2 | procedure (stand-in) |
| --- | --- | --- | --- | --- | --- | --- |
| ep01-a1 | S1 | 83 | 5.0 | 19.7 | 3.1 | 3.1 |
