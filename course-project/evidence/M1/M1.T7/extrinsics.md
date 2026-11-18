# M1.T7 steps 8–9 — camera extrinsics (2026-11-18)

**Position (step 8), from `configs/car.json` (M1.T9 measurements, 2026-10-29):** lens x 0.120 m ahead of the axle
midpoint (±0.005), y 0.000 m (±0.002), z 0.075 m above the floor (±0.002). Not re-measured today.

**Angles (step 9).** Recorded session `20261118-020555-calibration-extrinsics` (Spark): car on the carpet facing a wall,
the paper board (rigid backing) upright on the floor against that wall. Xiaohui's tape: lens to board 104–104.5 cm; the
car's centre line 2.5 cm to the left of the board's centre. `solvePnP` with `configs/camera.json` on 58 of 58 frames
(method changed from the plan's "target at lens height": the board's own pose gives the vertical and the wall normal).

| Angle | Value | How | Plan's mount limit |
| --- | --- | --- | --- |
| roll | **+4.4°** (sd 0.01) | slope of the board's long axis in the camera; positive = picture content turned counter-clockwise | 3° — **exceeded** |
| pitch | **−3.9°** (sd 0.15), nose **up** | the board's vertical axis against the optical axis; positive = nose down | 5° — ok |
| yaw | **+2.5°** (camera points left) from the tape offset; −1.0° if the car was exactly square to the wall | board centre seen 3.90° right of the optical axis, 1.38° right of the centre line by tape | 5° — ok |

Uncertainty: the two yaw methods differ by 3.5° (the car was squared and centred by eye), and pitch and roll assume the
board stood vertical with a level bottom edge on carpet; `uncertainty_deg` is set to 2.0. M1.T8 refines yaw from the
bearing bias of the wall tags. Cross-checks: distance 103.0 cm against the tape's 104–104.5 cm (−1.2 %, second distance
check, inside 2 %); lens 6.3 cm above the board's bottom edge against 7.5 cm above the floor in car.json (carpet pile and
wheel sink are of that order).

**Open (Xiaohui):** the roll is above the plan's 3° mount limit. It is recorded in `camera.json` and tag geometry
corrects for it, so the choice is to accept it or re-seat the camera (which would need this step again, not the lens
calibration).

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: computed the angles and wrote this record. Xiaohui Chen
placed the car and board and took the tape readings.
