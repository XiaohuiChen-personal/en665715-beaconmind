# M6.T14 — simulation part of the demo video, and the assembled silent video (2026-11-25)

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24/25: built and rendered the part, looked at the stills and
wrote this record. Xiaohui Chen has not watched the video yet.

## What was rendered

The take is the existing closed-loop episode of 2026-11-18, Claude Opus 5.5 in the simulated room
(`data/closed-loop/20261118-room-final/claude-opus-5-5/`, git-ignored; configuration and results in
`evidence/M2/M2.T7/closed-loop/README.md`). **No model was called and nothing was spent for the video**: it replays
the logged tool calls, results, reports, moves and poses. The Isaac re-render (M6.T13, MD5) is not used; the view is
the 2D room from above with the car drawn to scale, accepted by Xiaohui on 2026-11-24 ("as long as the video could
show the robot running in the simulator").

**Motion.** kinsim moves the car instantly. Each of the 55 executed moves is drawn at the speed limits its logged
command carries (`bm.move/1`: 0.15 m/s, 45°/s): 42.7 s of motion in all, played at ×2, the car turning and driving
smoothly (consecutive-frame check in `evidence/M6/M6.T12/README.md`). The model's 1129.8 s of thinking play at ×14
(the smallest whole factor that fits); every move covers 8 (turn) or 21 (straight) output frames; step 23, the first position fix, plays at ×2 with each tool call appearing
when the model made it, followed by a 5 s pause on its report; a 3 s pause holds the last report (DONE). The header
always shows both speeds, the playing one filled. The clock is the harness's own (it stands still while a drawn
move plays) and ends at 18:49 (1129.8 s, the summary's total).

Part 1 (175.64 s): part card (8 s) · how to read the screen (14 s) · the episode · result card (14 s) · validator card
(7 s) and a 13 s clip of the scripted test model (labelled "SCRIPTED TEST: a scripted test model, not a real model")
refused at the wall, after a turn, and after its emergency stop. The silent video adds title, idea, summary and
disclosure cards.

## Length

**Course requirement (Canvas, Presentation Timing), as reported by Xiaohui on 2026-11-24: 3 to 5 minutes.** The
assembly checks it (`evidence/M6/M6.T11/README.md`). Now, without the car part: **217.64 s (3:38)**. With the car
part the simulation part shrinks to 128.9 s (thinking ×34) and the whole video is at most 4:16 (car part 85 s).

## One command, and its output (`python3 course-project/tools/demo_video.py all`, Mac, 2026-11-25)

```
sim part: data/video/parts/sim.mp4, 4391 frames, 175.6 s of video, rendered in 352 s (motion: commanded)
car part: no inputs configured (configs/demo_video.json car.inputs is null): left out
cards: closing, disclosure, idea, title
assembled: data/video/BeaconMind-demo-silent.mp4, 217.64 s, 5441 frames (planned 5441)
length check: 217.64 s is inside 180-300 s
no narration audio configured (narration_audio is null): the silent video is the output
narration: presentation/demo-voiceover.md, 15 blocks, over budget: none
stills: 24 in data/video/stills
python3 tools/demo_video.py all  456.89s user 26.91s system 133% cpu 6:02.26 total
```

The render with the motion guards and the safe replacement is byte for byte the same video as the one before them
(same SHA-256 below).

ffmpeg is the static 7.1 build inside the `imageio-ffmpeg` wheel already in the Mac's Python 3.13 (nothing installed
system-wide; a git-ignored venv `data/video/venv` was created first and turned out to be unnecessary).

## The files (`probe.txt`, decoded by ffmpeg itself; the wheel has no ffprobe)

```
ffmpeg: ffmpeg version 7.1 Copyright (c) 2000-2024 the FFmpeg developers
data/video/parts/sim.mp4  codec h264  1920x1080  25 fps  4391 frames  175.64 s  audio False
data/video/BeaconMind-demo-silent.mp4  codec h264  1920x1080  25 fps  5441 frames  217.64 s  audio False
1dfbdba6d388e5848b44460bfcf61c470ded97037ca3a9cca8db5c981ca22bf8  data/video/parts/sim.mp4
2341d7c56b3117c62a21ebf29645a48794ff1792cd423f6f9f10d2ad83ca332f  data/video/BeaconMind-demo-silent.mp4
```

Paths are relative to `course-project/` on the Mac; both files are git-ignored. The frame counts equal the plan's.

## Checks

- Every number on screen comes from `tools/report_assets.py`, the logs, or the code that applies a rule
  (`evidence/M6/M6.T11/numbers.txt`); the logs agree with the run's summary (`evidence/M6/M6.T11/check.txt`).
- Stills of every cue and of the middle of every item, and six consecutive frames inside two moves, were looked at
  (`evidence/M6/M6.T12/README.md`).
- `grep -nE "sk-|api_key|password|ssid"` over `evidence/M6/` prints only this line.

## Not done

- **Nobody has watched the video at speed.** I can only look at frames; Xiaohui should watch
  `data/video/BeaconMind-demo-silent.mp4` once and say what to change. The plan's `review.md` waits for that.
- With the car part present, thinking runs at ×34 (about 0.6 s a step) and the step panel is readable only in the
  slowed step and the pauses.
- No narration audio yet (Xiaohui records it from `presentation/demo-voiceover.md`).
