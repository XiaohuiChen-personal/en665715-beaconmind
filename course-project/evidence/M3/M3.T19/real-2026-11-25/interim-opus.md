# Real-log replay, set real-2026-11-25 (interim: Opus 5.5 only)

Batch `b2-real-01 + b2-real-02 + b2-real-03` (config 611d90a41329, 1b3ab20f9758, af676fc3b9e6, real car: True); 5 episodes, 338 steps; world `configs/arenas/real-room.json` (sha12 35572d7656f3); configs/dv-real.json sha12 ea2cd23f9186 (differs from the frozen file in reject_range_above_m, sigma_bearing_deg, sigma_range_a_m, sigma_range_b_per_m).

## Final-position error against the end circle (the primary truth)

The end circle is the full circle the batch turns where the episode ended: 8 to 14 tags solved on their own geometry, not through the tracker. When the episode ended by DONE no move followed the agent's last report, so the circle measured that very pose (the manifest's `end_fix.pose`, in the map frame of the episode's start). n counts the episodes that have one; cm, heading in degrees. The heading column is not a result: the circle solves its starting heading from views placed by the odometry's own turns, which slip too; `logged truth off` below shows how far the batch's tracked truth sits from the circle, in position and heading.

| Arm | n | median | IQR | min | max | median heading error (deg) |
| --- | --- | --- | --- | --- | --- | --- |
| B0 | 4 | 28.8 | 22.4 to 34.8 | 11.1 | 45.0 | 12.6 |
| B2 | 4 | 6.1 | 3.1 to 9.8 | 1.3 | 13.5 | 7.6 |
| procedure | 4 | 6.1 | 3.1 to 9.8 | 1.3 | 13.5 | 7.6 |
| claude-opus-5-5 | 4 | 6.0 | 3.5 to 9.1 | 2.3 | 12.1 | 7.6 |

Per episode (cm). `end circle`: tags, rms of its tag residuals, its stated sigma; `logged truth off`: the batch's tracked truth at the last step minus the circle (cm, degrees):

| Episode | Scenario | Steps | end circle | logged truth off | B0 | B2 | procedure | claude-opus-5-5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b2-real-01 ep01-a1 | S1 | 83 | 9 tags, rms 2.3, sigma 2.4 | 6.6, -5.1 deg | 26.2 | 3.6 | 3.6 | 3.9 |
| b2-real-02 ep01-a1 | S1 | 56 | 8 tags, rms 4.0, sigma 2.8 | 4.2, -5.1 deg | 11.1 | 1.3 | 1.3 | 2.3 |
| b2-real-02 ep02-a1 | S2 | 62 | 14 tags, rms 2.6, sigma 2.6 | 7.6, -3.1 deg | 31.4 | 13.5 | 13.5 | 12.1 |
| b2-real-03 ep01-a1 | S1 | 56 | 13 tags, rms 2.2, sigma 2.6 | 14.6, -6.9 deg | 45.0 | 8.6 | 8.6 | 8.1 |

Without an end circle at the final report (only the tracker-dependent truths below):
- b2-real-03 ep02-a1: no end circle: the batch halted in it (stall).

## Against the last step's truth (secondary, tracker-dependent)

The batch's own truth at the last step: the pose it tracks, odometry between tag fixes blended by inverse variance (PoseTracker, 5 % odometry sigma), with its stated sigma. On this carpet it is overconfident northward. The second table recomputes it offline from the logged rows, recomputed with `tools/recompute_truth.py` (slip sigma 0.30 + 0.00 x north per metre of forward move).

| Truth | Arm | n | median | IQR | min | max | median heading error (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| logged | B0 | 5 | 27.2 | 19.7 to 33.2 | 7.0 | 43.9 | 7.7 |
| logged | B2 | 5 | 6.9 | 3.1 to 8.2 | 2.8 | 20.3 | 3.7 |
| logged | procedure | 5 | 6.9 | 3.1 to 8.2 | 2.8 | 20.3 | 3.7 |
| logged | claude-opus-5-5 | 5 | 6.8 | 3.5 to 7.2 | 1.9 | 19.0 | 3.7 |
| recomputed | B0 | 5 | 32.1 | 20.0 to 38.1 | 7.5 | 47.7 |  |
| recomputed | B2 | 5 | 3.7 | 2.8 to 4.9 | 2.4 | 9.5 |  |
| recomputed | procedure | 5 | 3.7 | 2.8 to 4.9 | 2.4 | 9.5 |  |
| recomputed | claude-opus-5-5 | 5 | 3.3 | 2.8 to 6.5 | 1.6 | 8.2 |  |

Per episode (cm; each cell: against the logged truth / against the recomputed truth):

| Episode | logged sigma / recomputed sigma | B0 | B2 | procedure | claude-opus-5-5 |
| --- | --- | --- | --- | --- | --- |
| b2-real-01 ep01-a1 | 5.0 / 5.0 | 19.7 / 20.0 | 3.1 / 2.8 | 3.1 / 2.8 | 3.5 / 3.3 |
| b2-real-02 ep01-a1 | 5.0 / 5.0 | 7.0 / 7.5 | 2.8 / 2.4 | 2.8 / 2.4 | 1.9 / 1.6 |
| b2-real-02 ep02-a1 | 5.8 / 13.6 | 27.2 / 32.1 | 20.3 / 9.5 | 20.3 / 9.5 | 19.0 / 8.2 |
| b2-real-03 ep01-a1 | 5.0 / 5.0 | 33.2 / 38.1 | 6.9 / 3.7 | 6.9 / 3.7 | 6.8 / 2.8 |
| b2-real-03 ep02-a1 | 5.6 / 12.3 | 43.9 / 47.7 | 8.2 / 4.9 | 8.2 / 4.9 | 7.2 / 6.5 |

## Runs

Replayed steps (of the logs' steps), valid reports, harness fallbacks, repaired reports, step errors, `move` calls (the replay rule wants 0), cost, seconds per step.

| Arm | steps | valid | fallbacks | repaired | errors | move calls | cost (US$) | mean s/step | p95 s/step |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| procedure | 338 of 338 | 338 | 0 | 0 | 0 | 0 | 0.00 | 0.0 | 0.0 |
| claude-opus-5-5 | 338 of 338 | 338 | 0 | 0 | 0 | 7 | 23.90 | 17.3 | 22.5 |

Not replayed: b2-real-02 ep03-a1 (did not end normally: {'code': 'odometry_scale', 'detail': 'tag fixes land -28 % (+-8 %) of the distance from where the odometry puts the car (10.5 m driven, 37 fixes; limit 12 %): the encoder scale is wrong, or the tags are', 'time_utc': '2026-11-25T12:24:02Z', 'safety': True})
