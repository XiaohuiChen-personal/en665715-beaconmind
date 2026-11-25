# M1.T8 — the tag pilot's noise model and the two changes made to it for real runs (2026-11-25)

`tools/tag_pilot.py analyze` wrote the model from session `20261125-020811-tag-pilot`; its output is kept unchanged in
this folder as `detector_noise.json`. `configs/detector_noise.json`, which the batch runner (`--detector-noise`) and
`tools/real_dv.py` read, is that model with two fields changed (the schema allows no comment field, so they are
recorded here):

| Field | Pilot output | Used for real runs | Why |
| --- | --- | --- | --- |
| `bearing_sigma_deg.a` | 0.8765 | **1.86** | The pilot's figure is the scatter of part A's 8 straight-ahead placements around their median. Across all 15 placements that saw the tag (parts A, D, E, R) the median bearing errors run from +3.3° at 0.79 m to −1.6° at 3.14 m: a pattern with range, not noise (fit: −2.7° + atan(0.085 m / r), RMS residual 0.67° against 1.69° for a constant). Its cause is not known: `car.json` has the lens on the centre line (lens_y 0.000 ± 0.002 m, measured 2026-10-29) and the tape line meets the wall within about 1 cm of the tag (frame A01); the camera yaw of 11-18 is +2.5° from a tape offset or −1.0° if the car was square, so a yaw error of the fitted size is possible. Side bearings (part B) were not measured (Xiaohui's decision). The real-run value is therefore the RMS of all 15 placements' bearing errors about zero, 1.852° rounded up. |
| `max_incidence_deg` | 0.0 | **60.0** | No incidence placements (part C) were run (Xiaohui's decision), so the pilot's rule ("the largest incidence among the reliable placements of the other parts") returned 0°, which would reject every tag not seen head-on. 60° is the design's incidence limit (the simulator's and the layout's coverage rule), unmeasured. |

Everything else is the pilot's: range bias +0.0049 − 0.0166 r m (reads 1.2–1.7 % short, as the 11-18 distance checks
did), range sigma 0.0013 + 0.0004 r m, bearing bias −0.077°, reliable range 0.785–3.135 m (every frame detected from
0.785 m to 3.135 m; none at 0.735 m), window 5 / 3 confirmed. The tag centre the camera sees is 0.215 m above the
carpet, which agrees with Xiaohui's tape reading (21.5 cm) and not with the layout's 0.23 m: the world file is rebuilt
with 0.215 m.

**How the pilot deviated from `PROCEDURE.md`** (Xiaohui's decisions, 2026-11-25): only the centre line was laid (no
part B or C, no marks beyond 3.0 m); the centre line was laid by eye from a book's corner instead of the equal-distance
construction (the truth is measured from W along that line, so its squareness does not enter the range or bearing
truth); the **camera lens**, not the axle, was put over each tick, so every placement's true axle distance is the tick
plus `lens_x_m` 0.12 m (`placements.csv` `measured_x_m`), which makes the pilot unable to check `lens_x_m` itself; a tape
measure was used instead of a ruler. Placement A01 was marked twice (the first time the frames were read with only two
detector passes, 3 of 30 found; see `third-pass-2026-11-25.md`); the analysis uses the second window. The live checks
during the session ran the third detector pass added in-process (a scratch wrapper on the Spark); the analysis ran on
commit `6fa8b0e`, which has that pass in `perception/tags.py`.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: ran the pilot's recording and analysis, fitted the bearing
pattern and made these two changes. The placements and tape readings are Xiaohui Chen's.
