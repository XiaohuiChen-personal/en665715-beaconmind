# M6.T15 — car part: input path, time alignment and layout, tested on stand-in data (2026-11-25)

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24/25: wrote the car part and its tests, ran the pipeline test
and wrote this record.

**No real footage exists yet.** Xiaohui will film one real run (rule R2 as changed on 2026-11-24). What is built is
the path from that run's files to the video part, tested end to end on a real recorder session with stand-ins for the
phone clip and the harness trace.

## Inputs and layout (`beaconmind/src/beaconmind/demo/car_part.py`; how-to in `presentation/demo-video.md`)

- Recorder session `data/real/<id>/`: camera frames with their host receive time (`frames_backend/` or `frames/`,
  `index.jsonl` with the X-BM headers).
- The harness's run folder: `seed_<n>.jsonl`, `seed_<n>.moves.jsonl` (commanded and result times),
  `spend.jsonl` (one line per model turn), `backend/steps.jsonl` (each sensing: host time, the frames it used, the
  fused detections). The harness rows' own `truth` (the batch's tag resection) is drawn when present.
- The phone clip and clock readings `"<seconds into the clip>=<epoch shown by tools/session_clock.py>"`. One reading
  fixes the offset; readings at least 60 s apart also fit the phone's clock rate (closer readings cannot: the clock
  prints 0.1 s); a rate further than 0.2 % from 1, or readings 0.3 s apart in offset, is refused as a misreading.
- The surveyed world file and the episode's start pose, so the room is drawn in the episode's map frame.

Everything is placed on the Spark's epoch clock. Motion plays at the first of `move_speeds` (1, 2, 3, 4) that lets the
part fit its target (real time when it can); the waits between moves take the smallest whole factor that fits the
rest (`timeline.fit_mixed`). The header shows both speeds ("waiting ×N", "driving ×M"), the playing one filled. Layout:
phone video (1130 × 636), the car's camera (while a step is being decided: the frame its detector used, with the
fused detections outlined; while moving: the newest frame), the room from above with the detections drawn as rays
from the believed pose, and the step panel. The part's target is 85 s, so the whole video with it stays inside the
course's 3:00 to 5:00 (`evidence/M6/M6.T11/README.md`).

## Pipeline test (`python3 course-project/tools/demo_video.py car-test --session <session> --car-target-s <s>`)

Inputs: recorder session `20261118-015528-calibration-distance-check` (57 camera frames over 12 s, copied from the
Spark with `tar` over `ssh`; it stays in the git-ignored `data/real/`); a stand-in trace (the first 4 steps of the
simulated Opus episode, re-timed into the session's window, each with a 1.2 s move, sensings pointing at the
session's frames); a stand-in phone clip that films a fake session clock and carries its own epoch in a 24-bit stripe,
starting 3.863 s before the first camera frame. The clock is "read" as a person would, to 0.1 s, at 1.0 s and 16.6 s
of the clip. The rendered part is decoded again and the stripe in the phone tile is compared with the instant each
frame should show.

| Target | Waits | Motion | Fits | Frames checked | Max error | Mean error |
| --- | --- | --- | --- | --- | --- | --- |
| 24 s | ×1 | real time | yes | 57 | 0.05 s | 0.028 s |
| 14 s | ×3 | real time | yes | 35 | 0.04 s | 0.026 s |
| 10 s | ×5 | ×2 (real time did not fit) | yes | 19 | 0.05 s | 0.029 s |

The fitted offset is 1794988525.6 against the true 1794988525.626 (the 0.1 s reading); the rest is the phone clip's
frame spacing (1/30 s). Full outputs: `car-test-24s.txt`, `car-test-14s.txt`, `car-test-10s.txt` (the stand-in run is
12 s long, so these targets play the same role as 85 s does for a 20-minute episode).

A first run of the time-lapsed case found an error of 0.83 s: ffmpeg's `fps` filter keeps, for each output frame, the
last input frame before the next half frame, so starting the decode half a frame late shifted every sped-up frame by
half its interval. The decode now starts at the piece's start; `tests/test_demo_car.py` checks a real-time and a ×8
piece against the stripe within 1/30 s.

The layout was looked at in stills of the test render (not kept: the camera frames show a private room): phone tile,
camera tile with "detector input of step 3" and the stand-in detection outlined and labelled, room view with the
detection ray, step panel; the header says "PIPELINE TEST" and the provenance line says what is a stand-in.

## Tests

`beaconmind/tests/test_demo_car.py` (4): the frame index prefers `frames_backend/` and skips failed requests; the
backend's fused detections are joined to every frame they used; the stripe code; the phone-clip alignment through
ffmpeg (skipped without ffmpeg). Output with the other demo tests: `evidence/M6/M6.T11/tests-mac.txt`.

## Not tested (needs the real run)

- A real phone clip (variable frame rate, rotation metadata, a clock read off a real screen).
- A real batch episode folder: `frames_backend/`, `backend/steps.jsonl` with real fused detections and their outlines,
  the resection truth in the rows, a B2 episode without model turns (its steps are timed from the backend's sensing
  times and the moves; covered by `test_epoch_time_base_uses_the_host_clock` only).
- Phone-camera privacy: the real clip must be looked at before anyone else sees it.
