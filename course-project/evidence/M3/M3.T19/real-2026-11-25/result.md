# Real-log replay, set real-2026-11-25 (final set: 9 episodes + 1 flagged; Opus 5.5 and Qwen3.8 complete, Gemma 4 running)

Batch `b2-real-01 + b2-real-02 + b2-real-03 + b2-real-05 + b2-real-06` (config 611d90a41329, 1b3ab20f9758, af676fc3b9e6, 41867c0ec8b2, 2ba442d815b9, real car: True); 10 episodes, 850 steps; world `configs/arenas/real-room.json` (sha12 35572d7656f3); configs/dv-real.json sha12 ea2cd23f9186 (differs from the frozen file in reject_range_above_m, sigma_bearing_deg, sigma_range_a_m, sigma_range_b_per_m).

**Exploratory, not pre-registered.** The pre-registration reports the real logs descriptively, as the sim-to-real gap (evidence/M4/M4.T1/prereg.md section 6), and the end-circle value below was chosen after the data; these are descriptive tables, with no test and no verdict.

## Final-position error against the end circle (the truth used first; exploratory)

The end circle is the full circle the batch turns where the episode ended: 8 to 14 tags solved on their own geometry, not through the tracker. When the episode ended by DONE no move followed the agent's last report, so the circle measured that very pose (the manifest's `end_fix.pose`, in the map frame of the episode's start). n counts the episodes that have one; cm, heading in degrees. The heading column is not a result: the circle solves its starting heading from views placed by the odometry's own turns, which slip too; `logged truth off` below shows how far the batch's tracked truth sits from the circle, in position and heading.

| Arm | n | median | IQR | min | max | median heading error (deg) |
| --- | --- | --- | --- | --- | --- | --- |
| B0 | 8 | 38.2 | 26.2 to 73.1 | 11.1 | 111.6 | 16.7 |
| B2 | 8 | 7.9 | 5.6 to 15.2 | 1.3 | 23.2 | 8.2 |
| procedure | 8 | 7.9 | 5.6 to 15.2 | 1.3 | 23.2 | 8.2 |
| claude-opus-5-5 | 8 | 7.7 | 5.2 to 14.1 | 2.3 | 25.3 | 7.8 |
| qwen38-flash-xhigh | 8 | 7.5 | 4.0 to 13.4 | 1.2 | 56.2 | 7.8 |

Per episode (cm). `end circle`: tags, rms of its tag residuals, its stated sigma; `logged truth off`: the batch's tracked truth at the last step minus the circle (cm, degrees):

| Episode | Scenario | Steps | end circle | logged truth off | B0 | B2 | procedure | claude-opus-5-5 | qwen38-flash-xhigh |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b2-real-01 ep01-a1 | S1 | 83 | 9 tags, rms 2.3, sigma 2.4 | 6.6, -5.1 deg | 26.2 | 3.6 | 3.6 | 3.9 | 4.8 |
| b2-real-02 ep01-a1 | S1 | 56 | 8 tags, rms 4.0, sigma 2.8 | 4.2, -5.1 deg | 11.1 | 1.3 | 1.3 | 2.3 | 1.3 |
| b2-real-02 ep02-a1 | S2 | 62 | 14 tags, rms 2.6, sigma 2.6 | 7.6, -3.1 deg | 31.4 | 13.5 | 13.5 | 12.1 | 11.8 |
| b2-real-03 ep01-a1 | S1 | 56 | 13 tags, rms 2.2, sigma 2.6 | 14.6, -6.9 deg | 45.0 | 8.6 | 8.6 | 8.1 | 7.7 |
| b2-real-05 ep01-a1 | S5 | 114 | 15 tags, rms 2.7, sigma 2.5 | 9.3, -6.2 deg | 67.9 | 6.2 | 6.2 | 5.6 | 1.2 |
| b2-real-05 ep02-a1 | S4 | 132 | 11 tags, rms 4.9, sigma 2.8 | 8.3, -7.1 deg | 111.6 | 23.2 | 23.2 | 25.3 | 56.2 |
| b2-real-05 ep03-a1 | S3 | 141 | 13 tags, rms 2.9, sigma 2.3 | 6.2, -4.7 deg | 88.8 | 20.4 | 20.4 | 20.1 | 18.4 |
| b2-real-06 ep01-a1 | S4 | 80 | 5 tags, rms 3.2, sigma 3.4 | 5.9, -5.1 deg | 26.2 | 7.2 | 7.2 | 7.2 | 7.2 |

Listed apart, not in n above: episodes the coded procedure stopped itself (the frozen B2 on a branch it does not implement; the harness wrote the stopping step as the study's fallback, the previous report dead-reckoned, and no move followed, so the end circle measured that step's pose):

| Episode | Scenario | Steps | end circle | logged truth off | B0 | B2 | procedure | claude-opus-5-5 | qwen38-flash-xhigh |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b2-real-06 ep02-a1 | S3 | 45 | 7 tags, rms 4.5, sigma 3.1 | 5.1, -6.9 deg | 12.2 | 7.6 | 7.6 | 18.2 | 17.3 |

Without an end circle at the final report (only the tracker-dependent truths below):
- b2-real-03 ep02-a1: no end circle: the batch halted in it (stall).

## Against the last step's truth (tracker-dependent; exploratory)

The batch's own truth at the last step: the pose it tracks, odometry between tag fixes blended by inverse variance (PoseTracker: 5 % odometry sigma, plus the slip sigma the batch ran with), with its stated sigma. Without a slip sigma it is overconfident northward on this carpet. The batches' trackers: b2-real-01, b2-real-02, b2-real-03: slip sigma 0.00 + 0.00 x north per metre; b2-real-05, b2-real-06: slip sigma 0.30 + 0.00 x north per metre. The second table recomputes it offline from the logged rows, recomputed with `tools/recompute_truth.py` (slip sigma 0.30 + 0.00 x north per metre of forward move).

| Truth | Arm | n | median | IQR | min | max | median heading error (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| logged | B0 | 9 | 33.2 | 25.7 to 58.8 | 7.0 | 114.0 | 14.8 |
| logged | B2 | 9 | 10.1 | 6.9 to 19.7 | 2.8 | 29.1 | 3.2 |
| logged | procedure | 9 | 10.1 | 6.9 to 19.7 | 2.8 | 29.1 | 3.2 |
| logged | claude-opus-5-5 | 9 | 10.6 | 6.8 to 19.0 | 1.9 | 31.3 | 3.3 |
| logged | qwen38-flash-xhigh | 9 | 9.0 | 6.8 to 17.7 | 2.7 | 61.1 | 3.7 |
| recomputed | B0 | 9 | 38.1 | 25.7 to 59.0 | 7.5 | 114.0 |  |
| recomputed | B2 | 9 | 9.5 | 3.7 to 13.0 | 2.4 | 29.1 |  |
| recomputed | procedure | 9 | 9.5 | 3.7 to 13.0 | 2.4 | 29.1 |  |
| recomputed | claude-opus-5-5 | 9 | 8.2 | 3.4 to 13.0 | 1.6 | 31.3 |  |
| recomputed | qwen38-flash-xhigh | 9 | 7.8 | 5.1 to 13.0 | 2.4 | 61.1 |  |

Per episode (cm; each cell: against the logged truth / against the recomputed truth):

| Episode | logged sigma / recomputed sigma | B0 | B2 | procedure | claude-opus-5-5 | qwen38-flash-xhigh |
| --- | --- | --- | --- | --- | --- | --- |
| b2-real-01 ep01-a1 | 5.0 / 5.0 | 19.7 / 19.9 | 3.1 / 3.0 | 3.1 / 3.0 | 3.5 / 3.4 | 2.7 / 2.6 |
| b2-real-02 ep01-a1 | 5.0 / 5.0 | 7.0 / 7.5 | 2.8 / 2.4 | 2.8 / 2.4 | 1.9 / 1.6 | 2.8 / 2.4 |
| b2-real-02 ep02-a1 | 5.8 / 13.6 | 27.2 / 32.1 | 20.3 / 9.5 | 20.3 / 9.5 | 19.0 / 8.2 | 18.7 / 7.8 |
| b2-real-03 ep01-a1 | 5.0 / 5.0 | 33.2 / 38.1 | 6.9 / 3.7 | 6.9 / 3.7 | 6.8 / 2.8 | 9.0 / 5.6 |
| b2-real-03 ep02-a1 | 5.6 / 12.3 | 43.9 / 47.7 | 8.2 / 4.9 | 8.2 / 4.9 | 7.2 / 6.5 | 6.8 / 5.1 |
| b2-real-05 ep01-a1 | 5.0 / 5.0 | 58.8 / 59.0 | 10.1 / 10.0 | 10.1 / 10.0 | 10.6 / 10.5 | 9.0 / 8.9 |
| b2-real-05 ep02-a1 | 5.0 / 5.0 | 114.0 / 114.0 | 29.1 / 29.1 | 29.1 / 29.1 | 31.3 / 31.3 | 61.1 / 61.1 |
| b2-real-05 ep03-a1 | 5.0 / 5.0 | 83.2 / 83.2 | 19.7 / 19.7 | 19.7 / 19.7 | 20.0 / 20.0 | 17.7 / 17.7 |
| b2-real-06 ep01-a1 | 5.0 / 5.0 | 25.7 / 25.7 | 13.0 / 13.0 | 13.0 / 13.0 | 13.0 / 13.0 | 13.0 / 13.0 |
| b2-real-06 ep02-a1 (flagged: procedure_stopped) | 5.6 / 5.6 | 8.8 / 8.9 | 6.7 / 6.7 | 6.7 / 6.7 | 19.3 / 19.3 | 18.5 / 18.5 |

## Runs

Replayed steps (of the logs' steps), valid reports, harness fallbacks, repaired reports, step errors, `move` calls (the replay rule wants 0), cost, seconds per step.

| Arm | steps | valid | fallbacks | repaired | errors | move calls | cost (US$) | mean s/step | p95 s/step |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| procedure | 850 of 850 | 849 | 1 | 0 | 1 | 0 | 0.00 | 0.0 | 0.0 |
| claude-opus-5-5 | 850 of 850 | 850 | 0 | 0 | 0 | 25 | 63.02 | 18.0 | 24.5 |
| qwen38-flash-xhigh | 850 of 850 | 848 | 2 | 61 | 0 | 6 | 0.00 | 128.7 | 230.4 |

Not replayed: b2-real-02 ep03-a1 (did not end normally: {'code': 'odometry_scale', 'detail': 'tag fixes land -28 % (+-8 %) of the distance from where the odometry puts the car (10.5 m driven, 37 fixes; limit 12 %): the encoder scale is wrong, or the tags are', 'time_utc': '2026-11-25T12:24:02Z', 'safety': True}); b2-real-05 ep04-a1 (did not end normally: {'code': 'stall', 'detail': 'FORWARD_25: stall_right', 'time_utc': '2026-11-25T17:19:57Z', 'safety': True}); b2-real-06 ep03-a1 (did not end normally: {'code': 'telemetry_stale', 'detail': 'last telemetry 1.383 s ago (limit 1.0 s)', 'time_utc': '2026-11-25T17:43:22Z', 'safety': True})

Arms run in several folders (they differ only in the hashes of the replay code, runner_sha12, real_replay_sha12):

- procedure: `data/real-replay/real-2026-11-25/runs-trim/procedure` seeds 1001, 2001, 2002, 3001, 3002, config 7311982b3f21; `data/real-replay/real-2026-11-25/runs-trim/procedure+b2-real-05` seeds 4001, 4002, 4003, config f5b6ccd518a8; `data/real-replay/real-2026-11-25/runs-trim/procedure+b2-real-06` seeds 5001, 5002, config f5b6ccd518a8
- claude-opus-5-5: `data/real-replay/real-2026-11-25/runs-trim/claude-opus-5-5` seeds 1001, 2001, 2002, 3001, 3002, config cb003c0c0bff; `data/real-replay/real-2026-11-25/runs-trim/claude-opus-5-5+b2-real-05` seeds 4001, 4002, 4003, config 0940d79f59f3; `data/real-replay/real-2026-11-25/runs-trim/claude-opus-5-5+b2-real-06` seeds 5001, 5002, config 0940d79f59f3
- qwen38-flash-xhigh: `data/real-replay/real-2026-11-25/runs-trim/qwen38-flash-xhigh` seeds 1001, 2001, 2002, 3001, 3002, config 8969d38de361; `data/real-replay/real-2026-11-25/runs-trim/qwen38-flash-xhigh+b2-real-05` seeds 4001, 4002, 4003, config a433012d5409; `data/real-replay/real-2026-11-25/runs-trim/qwen38-flash-xhigh+b2-real-06` seeds 5001, 5002, config a433012d5409
