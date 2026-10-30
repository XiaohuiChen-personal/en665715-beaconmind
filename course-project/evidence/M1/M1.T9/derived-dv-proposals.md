# M1.T9 step 6: design-value proposals from the car measurements (for M1.T10)

Written 2026-10-10 from `configs/car.json` (Xiaohui Chen's readings of 2026-10-10). These are **proposals**.
`configs/dv.json` was not edited: a changed design value needs Xiaohui's approval in M1.T10 (plan README §1.4
item 6). Arithmetic below; the inputs and their uncertainties are in `derived.txt`.

| Item | Formula | Inputs | Result | Current DV | Note |
| --- | --- | --- | --- | --- | --- |
| `done_range_m` | `forward_wall_limit_m` + `front_overhang_m` + 0.10 m (AGENT-DESIGN D2) | 0.35 (DV) + 0.138 ± 0.003 + 0.10 | **0.588 ± 0.003 m** (only `front_overhang_m` carries an uncertainty) | 0.55 (placeholder) | 0.038 m more than the placeholder. `front_overhang_m` was measured with **no USB cable** in the ESP32-CAM; the operating cable (M3.T1) can only lengthen it, so re-compute then |
| Turn/scan clearance | `sweep_radius_m` + margin (README C5) | **2026-10-16:** 0.140 ± 0.005 m (was 0.1402 ± 0.0048 m); margin `sweep_margin_m` 0.05 is proposed in OD17, not approved | **0.190 m** if OD17's margin is adopted (unchanged) | none yet | **Since 2026-10-16** (plate CAD, `measurements-2026-10-16-with-plate-cad.csv`) the plate's front corners are rounded (R135.14 arc, R8 fillets), so their farthest points are (0.1229, ±0.0447) m, r = 0.1308 m; the farthest point of the car is now the caster swung fully forward, (0.140, 0) on the centre line, which needs no centring assumption. Before: the farthest points were square plate-front corners (0.131, ±0.050), whose y assumed the strip centred on y = 0, and a strip 5 mm off centre would have raised the radius by about 2 mm (hypot(0.131, 0.055) = 0.1421 m) |
| `forward_wall_limit_m` vs the car's nose | `front_overhang_m` must be well inside the limit | 0.138 ± 0.003 m vs 0.35 m (DV) | 0.212 ± 0.003 m between the nose and a wall at the limit, taking the wall distance from the axle midpoint as C1's ranges are | 0.35 | The minimum reliable tag range (M1.T8) is not measured yet, so the second half of this check is pending |
| Odometry scale | metres per count = π · D / counts_per_rev | D = 0.067 m (direct, unloaded); counts **not measured** | 4.87 × 10⁻⁵ m/count **only with the nominal 4320** | — | Not a measurement: needs the encoder counts (postponed) and preferably the roll-out diameter (not done). M3.T3/M3.T8 replace it |

Generative-AI disclosure: Claude Opus 5.5 via Claude Code (2026-10-10) computed and wrote these proposals from
Xiaohui Chen's measurements; after a second review (same day) it raised the ± of `front_overhang_m` from 0.002 to
0.003 m (the 3 mm axle-datum floor of review #15 now covers `B3_front_most_x`, which is measured from the same axle
line as B1/B2) and gave `done_range_m` and the nose-to-wall distance that ±. No design value was changed.
