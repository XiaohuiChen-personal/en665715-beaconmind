# Demo video: how it is made (notes)

The demo recording is one of the four deliverables due at the presentation on 2026-12-01 (`plan/README.md` §3.6).
It is rendered by code from the experiment harness's logs, not from ROSA (cut 4 of §3.6; Xiaohui, 2026-11-24: "build
the demo video from the harness logs shall be enough as long as the video could be shown the robot running in
simulator. For the real run, I will record one run."). The simulation part draws the car to scale, moving between the
logged poses, labelled as the kinematic simulator; the car part is built around the one filmed real run. Videos and
frames are git-ignored: they live in `course-project/data/video/`.

## One command

```bash
python3 course-project/tools/demo_video.py all        # Mac (Pillow + the ffmpeg in the imageio-ffmpeg wheel)
```

It checks the logs against the run's own summary, writes the numbers manifest, renders the simulation part, the car
part (when its inputs are configured), the cards, joins them without re-encoding, writes the narration script with
its timings and exports stills. The parts on their own: `plan`, `numbers`, `check`, `sim`, `car`, `cards`,
`assemble`, `narration`, `stills`, and `car-test` (the car layout on stand-in data).

| File | What |
| --- | --- |
| `configs/demo_video.json` | durations, targets, the run folders, the car's inputs (`car.inputs`, null until real footage exists), `narration_audio` |
| `presentation/demo-cards.json` | card texts with `{{key}}` numbers |
| `presentation/demo-voiceover.template.md` | narration blocks tied to cues |
| `presentation/demo-voiceover.md` | generated narration script with start and end times and word budgets |
| `beaconmind/src/beaconmind/demo/` | the code: `timeline` (pure time-lapse logic), `episode` (log reader), `numbers`, `topdown`, `simcam`, `panels`, `cards`, `ffmpeg`, `sim_part`, `car_part`, `narration`, `video_cli` |
| `data/video/` (git-ignored) | `parts/*.mp4`, `cards/*.png`, `edl.json`, `cues.csv`, `numbers.txt`, `BeaconMind-demo-silent.mp4`, `stills/`, `car-test/` |

## Rules the code keeps

- **No number is typed.** On-screen and spoken numbers come from `tools/report_assets.py` (the same strings as the
  report and slides) or from the episode's log folder; `demo_video.py numbers` lists every one with its source.
  `demo_video.py check` recomputes steps, moves, refusals, tags mapped, map entries, total time and cost from the
  step rows and compares them with the harness's summary; `all` stops on any difference.
- **The robot is seen running.** The simulator moves the car instantly, so each logged move is drawn at the speed
  limits its command carries (0.15 m/s, 45°/s): the car, drawn to scale with its wheels, turns and drives smoothly
  between the logged poses, in the room view, in a close-up that follows it, and in a simulated camera view.
- **Speed is always on screen.** The header shows two speeds, thinking and driving, the playing one filled, or
  "paused". The simulated part fits the smallest whole thinking factor into its target; driving plays at ×2, one step
  at ×2 with a pause on its report. The car part plays motion in real time when it fits (else ×2, ×3, ×4) and speeds
  up the waits. The clock is the harness's own: it stands still while a drawn move plays.
- **Labels are honest.** "SIMULATION · Kinematic simulator (kinsim) · Claude Opus 5.5 drives"; the provenance line
  says kinsim, nominal tag positions, one episode, the noise seed, and that the moves are drawn at their commanded
  speed because the simulator moves instantly. The validator clip is labelled "SCRIPTED TEST: a scripted test model, not a real model".
- **Nothing hidden is narrated.** The logs hold tool calls, results, the report and its one-sentence note, not the
  model's reasoning; the panel shows only those.
- **Orientation.** The room is drawn as Xiaohui's survey sketch shows it "seen from above" (desk wall at the bottom,
  the 295 cm wall on the right), a rotation of the simulator's map frame, never a mirror, so a left turn turns
  counter-clockwise on screen.

## Length (course requirement)

Course requirement (Canvas, Presentation Timing), as reported by Xiaohui on 2026-11-24: the demo is a pre-recorded
video of **3 to 5 minutes** (slides 5 to 10 minutes, 15 minutes per project in all). `length_s` in
`configs/demo_video.json` (180 to 300 s, aim 240 s) is a hard check: `plan` prints it, `assemble` refuses to join a
video outside it and checks the joined file again. The simulation part's target is 130 s with the car part (whole video
at most about 4:16) and 180 s without it (now 3:38), so the video is inside the bound either way. The narration is
generated from the same plan, so its times always match.

## The car part, once real episodes exist (Xiaohui and the batch runner)

1. During the filmed episode (rule R2 since 2026-11-24: only this one run has a phone video) the recorder runs
   (`tools/record_session.sh`), the harness writes its run folder, and the phone films `tools/session_clock.py` for
   2 to 3 s at the start and, if possible, again at the end (two readings at least a minute apart also fix the
   phone's clock rate; closer readings fix only the offset).
2. Copy the phone clip into the session folder on the Spark (`data/real/<session>/phone/`), then copy the session and
   the batch's episode folder to the Mac with `tar` over `ssh` (never rsync).
3. Read the clock twice in the clip: open it in QuickTime Player, step to a frame where the clock is sharp, note the
   clip time (seconds) and the epoch the clock shows; again near the end. `demo_video.py` turns them into the offset
   and rate (a rate more than 0.2 % from 1 is refused as a misreading).
4. Fill `car.inputs` in `configs/demo_video.json` (the keys are listed under `$inputs_example`), then run `all`.
5. Look at the car part's stills before anyone else sees them: the phone and the car's camera show a private room.
   Nothing from them goes into the repository.

The layout and the alignment were tested on a real recorder session with a stand-in phone clip and a stand-in trace
(`evidence/M6/M6.T15/README.md`).

## Narration

Xiaohui records the voice-over from `presentation/demo-voiceover.md` (QuickTime Player, File > New Audio Recording,
while the silent video plays), saves `data/video/narration.m4a`, sets `narration_audio` and runs
`demo_video.py assemble`. The mux pads the audio with silence, so the video always runs to its last card.

Generative-AI disclosure: AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote the video pipeline, these
notes, the card texts and the narration draft. Xiaohui Chen records the narration and decides what is shown.
