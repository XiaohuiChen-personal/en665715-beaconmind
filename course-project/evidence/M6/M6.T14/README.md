# M6.T14 — simulation part of the demo video, and the assembled silent video (2026-11-25)

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24/25: built and rendered the part, looked at the stills and
wrote this record. Xiaohui Chen has not watched the video yet.

## What was rendered

The take is the existing closed-loop episode of 2026-11-18, Claude Opus 5.5 in the simulated room
(`data/closed-loop/20261118-room-final/claude-opus-5-5/`, git-ignored; configuration and results in
`evidence/M2/M2.T7/closed-loop/README.md`). **No model was called and nothing was spent for the video**: it replays
the logged tool calls, results, reports, moves and poses. The Isaac re-render (M6.T13, MD5) is not used; the view is
the 2D room from above, the plan's fallback, which Xiaohui accepted on 2026-11-24 ("as long as the video could be
shown the robot running in simulator").

Part 1 (119.76 s): part card (8 s) · how to read the screen (12 s, a real frame with numbered callouts) · the episode,
56 steps and 1129.8 s of logged time at ×24, step 23 (the first position fix) at ×2 with each tool call appearing when
the model made it, a 5 s pause on that step's report and verdict, a 3 s pause on the last report (DONE) · result card
(14 s) · validator card (7 s) and a 13 s clip of the scripted test model (labelled "SCRIPTED TEST: a scripted test
model, not a real model") refusing FORWARD_25 at the wall, BACKWARD_10 after a turn, and every move after its
emergency stop. The whole silent video adds the title, the idea, the summary and the disclosure cards.

## One command, and its output (`python3 course-project/tools/demo_video.py all`, Mac, 2026-11-25)

```
sim part: data/video/parts/sim.mp4, 2994 frames, 119.8 s of video, rendered in 193 s
car part: no inputs configured (configs/demo_video.json car.inputs is null): left out
cards: closing, disclosure, idea, title
assembled: data/video/BeaconMind-demo-silent.mp4, 161.76 s, 4044 frames (planned 4044)
no narration audio configured (narration_audio is null): the silent video is the output
narration: presentation/demo-voiceover.md, 13 blocks, over budget: none
stills: 22 in data/video/stills
python3 tools/demo_video.py all  274.65s user 18.29s system 144% cpu 3:22.05 total
```

ffmpeg is the static 7.1 build inside the `imageio-ffmpeg` wheel already in the Mac's Python 3.13 (nothing installed
system-wide; a git-ignored venv `data/video/venv` was created first and turned out to be unnecessary).

## The files (`probe.txt`, decoded by ffmpeg itself; the wheel has no ffprobe)

```
ffmpeg: ffmpeg version 7.1 Copyright (c) 2000-2024 the FFmpeg developers
data/video/parts/sim.mp4  codec h264  1920x1080  25 fps  2994 frames  119.76 s  audio False
data/video/BeaconMind-demo-silent.mp4  codec h264  1920x1080  25 fps  4044 frames  161.76 s  audio False
8ff585b9f7f2898aff2c9d310233483ac9a6eebc0997fae4a5b70ab995f05bf4  data/video/parts/sim.mp4
a127289e1082b60b6d791e16dd625dbac765acee470998ffb92e526a538f9127  data/video/BeaconMind-demo-silent.mp4
7346585 data/video/BeaconMind-demo-silent.mp4
6740738 data/video/parts/sim.mp4
```

Paths are relative to `course-project/` on the Mac; both files are git-ignored. The frame counts equal the plan's
(2994 = the part's planned frames; 4044 = the edit decision list's total), and the simulation part is within its
120 s target.

## Checks

- Every number on screen comes from `tools/report_assets.py` or the logs (`evidence/M6/M6.T11/numbers.txt`); the
  logs agree with the run's summary (`evidence/M6/M6.T11/check.txt`).
- Stills of every cue and of the middle of every item were extracted and looked at (`evidence/M6/M6.T12/README.md`
  lists what was found and fixed); the header's speed badge shows "×24 time-lapse", "×2 slow motion" or "paused" on
  every frame; the provenance line names the kinematic simulator, the nominal tag positions, the noise seed and the
  drawn glide.
- `grep -nE "sk-|api_key|password|ssid"` over this folder and `evidence/M6/M6.T11/`, `M6.T12/`, `M6.T15/`, `M6.T4/`
  prints nothing.

## Not done

- **Nobody has watched the video at speed.** I can only look at stills; Xiaohui should watch
  `data/video/BeaconMind-demo-silent.mp4` once (QuickTime Player) and say what to change. The plan's `review.md`
  waits for that.
- The time-lapse runs at ×24 (about 0.9 s a step): the step panel is readable only in the slowed step and the pauses;
  a longer simulation target slows it (parameter `sim.target_s`).
- No narration audio yet (Xiaohui records it from `presentation/demo-voiceover.md`).
