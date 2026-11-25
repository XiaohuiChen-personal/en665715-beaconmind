# M6.T11 — video logic: time-lapse pieces, frame times, fitting, clock sync, edit decision list (2026-11-25)

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24/25: wrote the code, the tests and this record.

Re-scoped by plan §3.6 (cut 4, confirmed by Xiaohui on 2026-11-24: "build the demo video from the harness logs shall be
enough as long as the video could be shown the robot running in simulator"): the video is rendered from the experiment
harness's run folders, not from a ROSA session, so the trace format of M6.T7 is replaced by the closed-loop harness's
own logs (`seed_<n>.jsonl`, `moves.jsonl`, `spend.jsonl`, `backend/steps.jsonl`). The rules of the plan's `edl.py`
are kept where they still apply (half-up frame counts, centred frame times, speed badge, card budget as a sum of
parameters), and the names changed with the content.

## Code (all under `course-project/`)

| File | What |
| --- | --- |
| `beaconmind/src/beaconmind/demo/timeline.py` | Pieces (a source interval at a speed, or a held instant), frame counts (half up), frame times (centred), `fit_sim_factor` (smallest whole time-lapse factor that fits, one slowed step and pauses kept), `car_pieces` / `fit_think_speed` (motion at real time, waits sped up; reports `fits False` instead of speeding up motion), `clock_sync` (phone clock to the Spark's epoch from `tools/session_clock.py` readings), `latest_at`, the sequence plan, word budgets. Standard library only. |
| `beaconmind/src/beaconmind/demo/episode.py` | Reads a run folder into a timeline of steps: tool calls placed at the end of the model turn that made them, cost per turn, true and believed pose, the map; two time bases ("steps" for the simulator, "epoch" for the car); `view_at` (what the screen shows at an instant) and `check_against_summary` (recomputes the shown numbers and compares them with the harness's summary). |
| `beaconmind/src/beaconmind/demo/numbers.py` | Every number on screen and in the narration with its source: `tools/report_assets.py` (the report's and slides' strings), the run folder, the rule constants read from the code that applies them. |
| `beaconmind/src/beaconmind/demo/video_cli.py`, `tools/demo_video.py` | The one command (`all`) and its parts; `plan` writes `data/video/edl.json` and `cues.csv` without rendering. |
| `configs/demo_video.json` | Durations and targets (parameters), run folders, the car's inputs (null until real footage exists). |
| `beaconmind/tests/test_demo_timeline.py` (14), `test_demo_episode.py` (10) | Hand-computed fixtures. |

## Tests (Mac, `cd course-project/beaconmind && PYTHONPATH=src python3 -m pytest -q tests/test_demo_*.py`)

```
.......................................                                  [100%]
39 passed in 1.21s
```

(39 = these 24 and the 15 of M6.T12/M6.T15 in `test_demo_render.py` and `test_demo_car.py`.) Full suite on the Mac
after the last change: `677 passed, 10 skipped in 169.82s`. Not run on the Spark (no render runs there; the tests
need no service, and Pillow and ffmpeg tests skip cleanly where they are absent).

## The logs agree with the harness's summary (`python3 course-project/tools/demo_video.py check`)

```
steps                        logs 56             summary 56             OK
moves executed               logs 55             summary 55             OK
refused move calls           logs 0              summary 0              OK
tags mapped within 0.30 m    logs 14             summary 14             OK
map entries                  logs 14             summary 14             OK
ended by                     logs DONE           summary DONE           OK
time total (s)               logs 1129.8         summary 1129.8         OK
cost (US$)                   logs 4.60225        summary 4.60225        OK
```

`all` stops before rendering if any line differs. The log folder's `seed_3000.summary.json` is also compared byte for
byte with the evidence copy in `evidence/M2/M2.T7/closed-loop/runs-final/claude-opus-5-5/`.

## Edit decision list (`python3 course-project/tools/demo_video.py plan`)

```
   0.00 s  title       card    6.00 s
   6.00 s  idea        card   14.00 s
  20.00 s  sim         part  119.76 s
 139.76 s  closing     card   12.00 s
 151.76 s  disclosure  card   10.00 s
total 161.76 s (4044 frames); simulation time-lapse x24 over 1129.8 s of logged time
```

The simulation part's target is 120 s (assumption, below); with its cards (part 8 s, how to read 12 s, result 14 s,
validator card 7 s and a 13 s scripted clip), step 23 at ×2 (11.7 s), a 5 s pause on its report and a 3 s pause on the
last report, the smallest whole factor that fits is ×24. `edl.json` (pieces, cue times) and `cues.csv` are copied
here; `numbers.txt` lists every number with its source.

**Length assumption** (no course requirement known on 2026-11-24): the whole video about 3 to 4 minutes, the
simulation part about 2 minutes, the car part about 70 s once it exists. All are parameters in
`configs/demo_video.json`.

## Not done, or different from the plan text

- No terminal capture and no ROSA trace exist (cut 4), so there is no terminal renderer; the step panel is drawn from
  the run log (M6.T12).
- The plan's `render_plan.json` and `ffplan.py` were folded into `episode.view_at` and `demo/ffmpeg.py`; no
  intermediate PNG frames are written (frames are piped to ffmpeg).
- The smoke on an M6.T7 stub session does not apply; the smoke is the real render (M6.T14).
