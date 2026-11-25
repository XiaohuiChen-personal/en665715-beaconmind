# Dry rehearsal of the real-log replay (simulated car, batch b2-real-01-dry-r1-20261125)

Batch `b2-real-01-dry-r1-20261125` (config 9b9aaa7efdc3, real car: False); 10 episodes, 732 steps; world `configs/arenas/real-room.json` (sha12 35572d7656f3); configs/dv-real.json sha12 ea2cd23f9186 (differs from the frozen file in reject_range_above_m, sigma_bearing_deg, sigma_range_a_m, sigma_range_b_per_m).

Final-position error at the last step against the batch's truth (tag resection against the surveyed tags, in the map frame of the episode's start), in cm. `vs end circle`: against the position of the full circle the batch turns after the episode; `vs simulator truth`: only a dry run has it.

| Arm | n | median | IQR | min | max | median heading error (deg) | median truth sigma | vs end circle (median) | vs simulator truth (median) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 | 10 | 2.2 | 1.5 to 2.8 | 1.1 | 5.0 | 0.2 | 5.0 | 2.1 | 2.3 |
| B2 | 10 | 2.9 | 2.2 to 4.8 | 0.8 | 5.5 | 0.8 | 5.0 | 3.0 | 3.0 |
| procedure (stand-in) | 10 | 2.9 | 2.2 to 4.8 | 0.8 | 5.5 | 0.8 | 5.0 | 3.0 | 3.0 |

The batch's truth itself against the simulator's (dry run only, last step): median 0.3 cm, max 0.6 cm over 10 episodes.

Per episode (final-position error, cm; `truth sigma`: the batch's own uncertainty of its truth):

| Episode | Scenario | Steps | truth sigma | B0 | B2 | procedure (stand-in) |
| --- | --- | --- | --- | --- | --- | --- |
| ep01-a1 | S1 | 56 | 5.0 | 1.4 | 4.9 | 4.9 |
| ep02-a1 | S2 | 43 | 5.0 | 1.8 | 0.8 | 0.8 |
| ep03-a1 | S3 | 104 | 5.0 | 2.9 | 5.2 | 5.2 |
| ep04-a1 | S4 | 64 | 5.4 | 2.6 | 1.4 | 1.4 |
| ep05-a1 | S5 | 57 | 5.0 | 1.1 | 2.5 | 2.5 |
| ep06-a1 | S1 | 69 | 5.0 | 2.8 | 4.3 | 4.3 |
| ep07-a1 | S2 | 70 | 5.0 | 2.7 | 3.0 | 3.0 |
| ep08-a1 | S3 | 69 | 5.0 | 1.3 | 2.2 | 2.2 |
| ep09-a1 | S4 | 150 | 5.0 | 5.0 | 5.5 | 5.5 |
| ep10-a1 | S5 | 50 | 5.0 | 1.7 | 2.9 | 2.9 |
