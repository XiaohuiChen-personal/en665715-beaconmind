# M6.T12 — video renderers: the room from above, the step panel, header, legend, cards (2026-11-25)

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24/25: wrote the renderers and tests, looked at every still
listed below, and wrote this record.

## Code (`course-project/beaconmind/src/beaconmind/demo/`)

| File | What |
| --- | --- |
| `draw.py` | Fonts by path (Helvetica Neue and Menlo on the Mac, DejaVu on the Spark), colours, wrapping. |
| `topdown.py` | The room from above in the episode's map frame: walls, desk, driving area, the 20 tags with IDs (green once the model's map holds an entry with that ID within the C10.3 radius, yellow when seen this step), the model's beacon estimates (blue rings), true pose (black, the car's footprint from `configs/car.json` to scale) and believed pose (blue outline), both paths, the start, the camera's field of view (46.9° from `configs/camera.json`, the run's 3.0 m range limit, clipped to the room). Drawn at twice the size and scaled down. |
| `panels.py` | Header with stat chips (real time, model cost, tags mapped, the believed pose's error) and the speed badge; the step panel (1 the observation, 2 the tool calls with their answers in the order and at the time the model made them, 3 the report and its `note`, 4 the validator's verdict and the executed move); legend; the car-camera tile (frame letterboxed, each fused detection outlined by projecting its base_link position with `camera_model`). |
| `cards.py` | Title, part, explanation-with-picture (numbered callouts), result and disclosure cards; refuses a card with an unfilled `{{key}}` or "TBD". |
| `sim_part.py` | The simulation part's frames, its cards and the scripted validator clip. |
| `beaconmind/tests/test_demo_render.py` (11) | Rotation is never a mirror, the car where its pose is, chips that do not fit are dropped, tool-call wording, cards refuse unfilled fields, ffmpeg argument lists, the stripe code, narration timing, every card and narration block fills from the logs, the plan fits its target. |

**Orientation.** The simulator's map frame (start at the origin) is rotated 180° on screen. That puts the desk wall at
the bottom, the 295 cm wall on the right and the angled section top right, as Xiaohui's survey sketch draws the room
"seen from above" (`evidence/M3/M3.T10/room-survey.md`), and it is a rotation, so a left turn is counter-clockwise on
screen. **Observation for the report:** `report/generated/fig-room.tex` (`tools/report_assets.py figure_room`,
also `slides/figures/fig-room.png`) draws the room's y axis to the right and x up, which is the mirror image of that
sketch (the 295 cm wall and the angled section appear on the left), while its caption says "seen from above". Not
changed here (not this task's files).

## Stills looked at (Read, full size, from the rendered MP4s)

From `data/video/parts/sim.mp4` (first render) and `data/video/BeaconMind-demo-silent.mp4` (final render); every
problem found was fixed and the part rendered again:

| Still | Found | Fixed |
| --- | --- | --- |
| part card, legend card | callouts covered the label, the panel text and the legend | moved off the content |
| time-lapse at step 2, zoomed | the white heading triangle was nearly equilateral and read as pointing the wrong way | a slender arrow; checked zoomed at two headings |
| step 23 slowed | "→" missing in Helvetica Neue (a box); the banner hid the tag labels and the scale bar; header text overlapped the badge | no arrows in sans text; banner moved into the floor area; header as stat chips |
| step 23 report | the report was on screen only for the 0.3 s glide (in the simulator the move follows the report at once) | a labelled 5 s pause ("paused") on the report and the verdict |
| last step | the DONE report was never visible before the cut | a labelled 3 s pause on the last report |
| result card | notes above the table; a wrapped row's shading too short | table first; shading follows wrapped rows |
| scripted validator clip | tag labels clipped, the scale bar on a label, the wall-limit label on the dashed line, the earlier refusal in a step disappeared | larger margin, label in the legend, refusals listed cumulatively, labels on a white box |
| title card | the rule touched the title | spaced |

Copies of the final stills (simulation only, 1280 × 720 JPEG): `still-legend-card.jpg`, `still-timelapse-step12.jpg`,
`still-slowed-step23.jpg`, `still-paused-step23.jpg`, `still-paused-done.jpg`, `still-result-card.jpg`,
`still-validator-scripted.jpg`, `still-last-disclosure.jpg`. All 22 stills of the final render (every cue and the
middle of every item) are in `data/video/stills/` (git-ignored). No still of the car part is kept here: its camera
frames show a private room.

## Not done

- No terminal renderer and no belief panel as separate images (the plan's M6-C8 three-stream layout); the step panel
  and the room view carry that content.
- The renderers were not run on the Spark (nothing needs them there).
