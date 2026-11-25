# M6.T12 — video renderers: the room from above, the close-up, the simulated camera, the step panel, cards (2026-11-25)

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24/25: wrote the renderers and tests, looked at every still
listed below, and wrote this record.

Xiaohui's condition for the harness-log video (2026-11-24): "as long as the video could show the robot running in the
simulator". So the simulation part shows the car driving, not a diagram that updates once per step.

## Code (`course-project/beaconmind/src/beaconmind/demo/`)

| File | What |
| --- | --- |
| `draw.py` | Fonts by path (Helvetica Neue and Menlo on the Mac, DejaVu on the Spark), colours, wrapping. |
| `topdown.py` | The room from above in the episode's map frame: walls, desk, driving area, the 20 tags with IDs (green once the model's map holds an entry with that ID within the C10.3 radius, yellow when seen this step), the model's beacon estimates (blue rings), the true pose and the believed pose (blue outline), both paths, the start, the camera's field of view (46.9° from `configs/camera.json`, the run's 3.0 m range, clipped to the room). **The car to scale** from `configs/car.json`: the footprint (corners), both wheels (diameter, tyre width, outer track), a heading arrow and the lens. The same class draws the **close-up** that follows the car (380 px/m, 20 cm scale bar). Drawn at twice the size and scaled down. |
| `simcam.py` | **What the camera would see** at the true pose: walls and floor as two flat colours split at the projected wall base, each tag's page and black square projected with `beaconmind.camera_model` (the room simulator's own projection); amber = reported to the model this step, grey = in the picture but not reported. Labelled "simulated camera view (camera.json)". |
| `panels.py` | Header (stat chips and a two-part speed badge: thinking and driving, the playing one filled, or "paused"); the step panel (1 observation, 2 tool calls with their answers in the order and at the time the model made them, 3 report and its `note`, 4 validator verdict and executed move; a compact form for the simulation layout); legend; the car-camera tile for the real car. |
| `cards.py` | Title, part, explanation-with-picture (numbered callouts), result and disclosure cards; refuses a card with an unfilled `{{key}}` or "TBD". |
| `sim_part.py` | The simulation part: layout, frames, cards and the scripted validator clip (its accepted moves also drawn at the commanded speed, in real time). |
| `beaconmind/tests/test_demo_render.py` (11) | Rotation is never a mirror, the car where its pose is, header chips, tool-call wording, cards refuse unfilled fields, ffmpeg argument lists, the stripe code, narration timing, every card and narration block fills from the logs, the plan fits its target and the course's length bound. |

**Screen (1920 × 1080):** header; the room (1130 × 860) with the legend below; on the right the close-up (390 × 292)
and the simulated camera (390 × 292) above the step panel (790 × 664); the provenance line at the bottom says
"kinsim (kinematic simulator) · 20 nominal tag positions · one episode, noise seed 3000, 2026-11-18 · moves drawn at
the commanded 0.15 m/s and 45°/s (the simulator moves instantly) · replayed from the logs". The header reads
"SIMULATION · Kinematic simulator (kinsim) · Claude Opus 5.5 drives".

**Orientation.** The simulator's map frame is rotated 180° on screen: desk wall at the bottom, the 295 cm wall on the
right, as Xiaohui's survey sketch draws the room "seen from above" (`evidence/M3/M3.T10/room-survey.md`); a rotation,
never a mirror, so a left turn turns counter-clockwise. The report's Fig. 3 (`fig-room`) is the mirror image of that
sketch; the lead has listed it in `report/PENDING.md`.

## Motion is continuous (consecutive frames of the rendered video)

`motion-continuity.jpg`: six consecutive frames (25 fps) of `data/video/BeaconMind-demo-silent.mp4` from inside two
moves: top two rows, step 17's FORWARD_25 (close-up and room view): the car advances a little in every frame, the
start mark recedes; bottom two rows, step 5's TURN_LEFT_30: the heading turns a little in every frame. No jump from
pose to pose. In the log the frames' source times are 1/25 s × 2 apart (driving at ×2).

## Stills looked at (Read, full size)

Every cue and the middle of every item of each render, plus zooms of the car. Found and fixed, over three renders:

| Still | Found | Fixed |
| --- | --- | --- |
| zoom of the car at step 2 | the heading triangle read as pointing the wrong way | a slender arrow; checked zoomed at two headings |
| step 23 slowed | "→" missing in Helvetica Neue (a box); the banner hid tag labels; header text overlapped the badge | no arrows in sans text; banner moved; stat chips |
| step 23 report | on screen for only 0.3 s in the first render | a labelled 5 s pause on the report and the verdict |
| last step | the DONE report was never visible before the cut | a labelled 3 s pause |
| simulated camera, first version | huge black wedges: the distortion polynomial folds points far outside the picture back in | points more than 25 % outside the calibrated picture are dropped |
| close-up | the 1 m scale bar was wider than the close-up | the scale bar picks 1 m, 50, 20 or 10 cm |
| compact step panel at step 23 | the validator's last line fell off the panel | smaller compact fonts, note at most 3 lines |
| how-to-read card | text ran off the bottom; callouts covered content | shorter text, callouts outside the picture |
| result card, scripted clip, title card | (first render) notes above the table, labels clipped or on lines, the rule touching the title | fixed in the first round |

Final stills (simulation only, 1280 × 720 JPEG): `still-legend-card.jpg`, `still-timelapse-step12.jpg`,
`still-driving-step17.jpg`, `still-slowed-step23.jpg`, `still-paused-step23.jpg`, `still-driving-step34.jpg`,
`still-paused-done.jpg`, `still-result-card.jpg`, `still-validator-scripted.jpg`, `still-last-disclosure.jpg`. All 24
stills of the final render are in `data/video/stills/` (git-ignored). No still of the car part is kept here: its camera
frames show a private room.

## Not done

- The simulated camera draws no desk, no tag pattern and no lighting; it shows where the tags fall in the picture.
- The renderers were not run on the Spark.
