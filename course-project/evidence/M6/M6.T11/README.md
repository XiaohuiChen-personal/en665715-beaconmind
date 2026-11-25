# M6.T11 — video logic: time-lapse pieces, frame times, fitting, clock sync, edit decision list (2026-11-25)

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24/25: wrote the code, the tests and this record (revised on
2026-11-25 for the course's length bound and the drawn motion).

Re-scoped by plan §3.6 (cut 4, confirmed by Xiaohui on 2026-11-24: "build the demo video from the harness logs shall be
enough as long as the video could be shown the robot running in simulator"): the video is rendered from the experiment
harness's run folders, not from a ROSA session, so the trace format of M6.T7 is replaced by the closed-loop harness's
own logs (`seed_<n>.jsonl`, `moves.jsonl`, `spend.jsonl`, `backend/steps.jsonl`). The rules of the plan's `edl.py`
are kept where they still apply (half-up frame counts, centred frame times, speed badge, card budget as a sum of
parameters), and the names changed with the content.

## Code (all under `course-project/`)

| File | What |
| --- | --- |
| `beaconmind/src/beaconmind/demo/timeline.py` | Pieces (a source interval at a speed, or a held instant), frame counts (half up), frame times (centred), `mixed_pieces` / `fit_mixed` (drawn motion at its own speed, one slowed step, pauses, and the smallest whole thinking factor that fits the rest; `fits False` instead of speeding up motion), `check_length` (the course's bound), `clock_sync` (phone clock to the Spark's epoch from `tools/session_clock.py` readings), `latest_at`, word budgets. Standard library only. |
| `beaconmind/src/beaconmind/demo/episode.py` | Reads a run folder into a timeline of steps: tool calls placed at the end of the model turn that made them, cost per turn, true and believed pose, the map; two time bases ("steps" for the simulator, "epoch" for the car); `draw_motion`: each simulated move gets the time it takes at its logged commanded limits (`bm.move/1` v_max_mps 0.15, w_max_dps 45), and `logged_time` takes that drawn time out of the clock again; `view_at` (what the screen shows at an instant) and `check_against_summary`. |
| `beaconmind/src/beaconmind/demo/numbers.py` | Every number on screen and in the narration with its source: `tools/report_assets.py` (the report's and slides' strings), the run folder, the rule constants read from the code that applies them. |
| `beaconmind/src/beaconmind/demo/video_cli.py`, `tools/demo_video.py` | The one command (`all`) and its parts; `plan` writes `data/video/edl.json` and `cues.csv` without rendering. |
| `configs/demo_video.json` | Durations and targets (parameters), run folders, the car's inputs (null until real footage exists). |
| `beaconmind/tests/test_demo_timeline.py` (17), `test_demo_episode.py` (11) | Hand-computed fixtures. |

## Tests (Mac, `cd course-project/beaconmind && PYTHONPATH=src python3 -m pytest -q tests/test_demo_*.py`)

```
...........................................                              [100%]
43 passed in 1.36s
```

(43 = these 28 and the 15 of M6.T12/M6.T15 in `test_demo_render.py` and `test_demo_car.py`.) The full Mac suite is in
the commit record below. Not run on the Spark (no render runs there; Pillow and ffmpeg tests skip cleanly where they
are absent).

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

## Length: a hard check

**Course requirement (Canvas, Presentation Timing), as reported by Xiaohui on 2026-11-24: the demo is a pre-recorded
video of 3 to 5 minutes** (slides 5 to 10 minutes, 15 minutes per project in all). `configs/demo_video.json`
`length_s` = 180 to 300 s, aim 240 s. `demo_video.py plan` prints the check and exits 1 outside it; `assemble` refuses
to join the parts when the planned length is outside it, and after joining decodes the file again and moves it to
`*-REJECTED.mp4` when its length or frame count is wrong (tests: `test_length_check_is_the_course_bound`,
`test_the_plan_fits_the_simulation_target`). The simulation part's target depends on whether the car part exists:
130 s with it (then at most 42 s of cards + 128.9 s + 85 s of car = 4:16), 180 s without it, so the video stays inside
the bound even if the filmed run does not happen.

## Edit decision list now (`python3 course-project/tools/demo_video.py plan`, no car part yet)

```
   0.00 s  title       card    6.00 s
   6.00 s  idea        card   14.00 s
  20.00 s  sim         part  175.64 s
 195.64 s  closing     card   12.00 s
 207.64 s  disclosure  card   10.00 s
total 217.64 s (5441 frames); simulation: thinking x14, drawn motion x2, over 1172.5 s of logged time and drawn motion
length check: inside 180-300 s
```

Inside the simulation part: part card 8 s, how to read the screen 14 s, the episode (1129.8 s of logged thinking at
×14, 42.7 s of drawn motion at ×2, step 23 at ×2 with a 5 s pause on its report, a 3 s pause on the last report),
result card 14 s, validator card 7 s and the 13 s scripted clip. With the car part present the thinking factor becomes
×34 (computed, not rendered). `edl.json` (pieces, cue times) and `cues.csv` are copied here; `numbers.txt` lists every
number with its source.

## Not done, or different from the plan text

- No terminal capture and no ROSA trace exist (cut 4), so there is no terminal renderer; the step panel is drawn from
  the run log (M6.T12).
- The plan's `render_plan.json` and `ffplan.py` were folded into `episode.view_at` and `demo/ffmpeg.py`; no
  intermediate PNG frames are written (frames are piped to ffmpeg).
- The smoke on an M6.T7 stub session does not apply; the smoke is the real render (M6.T14).
- The drawn motion is constant speed at the commanded limits: the simulator has no acceleration and no move duration
  (its log holds `duration_s` 0), so how a real move speeds up and slows down is not shown.
