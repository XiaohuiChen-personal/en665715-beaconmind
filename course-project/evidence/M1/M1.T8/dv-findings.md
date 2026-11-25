# M1.T8 design-value findings

Proposals for M1.T10 only; `configs/dv.json` is not edited here.

| Value | In dv.json | Pilot | Verdict |
| --- | --- | --- | --- |
| `obs_frames / obs_min_frames` | 5 / 3 | 5 / 3, worst window probability 1.000 | confirmed |
| `obs_settle_s` | 0.3 | not measurable with the car standing still | open: compare with the frame latency (M1.T17: p95 237 ms at XGA) and the vibration check of M3.T9 |
| `reject_range_above_m` | 2.0 | max reliable range 3.13 m | may be raised (decision for Xiaohui) |
| `forward_wall_limit_m (W2: min reliable range must be below it)` | 0.35 | min reliable range 0.79 m | FAILS: a tag straight ahead is lost before the wall limit; flag for M1.T10 |
| `done_range_m` | 0.55 | min reliable range 0.79 m | FAILS: the target tag cannot be seen at the done range; flag for M1.T10 |
| `sigma_range_a_m + sigma_range_b_per_m * r` | 0.100 m at 1 m, 0.150 m at 2 m | 0.002 m at 1 m, 0.002 m at 2 m | dv is conservative |
| `sigma_bearing_deg` | 2.0 | 0.88 deg at 1 m, 0.88 deg at 2 m (upper bound) | dv is conservative |

Range bias line +0.0049 -0.0166 r m; bearing bias -0.08 deg; max incidence 0 deg.

AI-assisted: tools/tag_pilot.py (Claude Fable 5.2 via Claude Code, 2026-11-18) wrote this table on 2026-11-25 from the pilot's numbers. The placements and tape readings are Xiaohui Chen's.
