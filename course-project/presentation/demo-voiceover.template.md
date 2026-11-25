# Demo video narration: template

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: drafted these narration blocks. Xiaohui Chen records the
voice-over and may reword any block.

This file is the source of `presentation/demo-voiceover.md`, which `python3 course-project/tools/demo_video.py
narration` writes with each block's start and end time and its word budget (130 words a minute). Edit here, then
rerun the command. Rules:

- A block starts with `@@ <cue>`; the cues are in `course-project/data/video/cues.csv` after `demo_video.py plan`.
- `{{key}}` is a number from the evidence and log files (`demo_video.py numbers` lists them). Do not type a number.
- Say only what the screen shows or the logs hold; the model's hidden reasoning is not logged, so never narrate it.
- The video must also work silent: never put information only in the narration.
- Blocks for the car part (`car.*`) are left out until the car part exists.

@@ title
This is BeaconMind, my project for Embodied Agentic AI. I'm Xiaohui Chen.

@@ idea
A language model drives a small robot car. It sees tags on the walls, calls geometry tools, keeps its own pose and
map, and a validator checks every move.

@@ sim.part
First, a simulation of my room: one episode in which Claude Opus 5.5 chose every move.

@@ sim.legend
Left: the room from above. Black is the true pose, blue is what the model believes. Right: each step, as the
harness logged it.

@@ sim.episode
The model starts by turning in place, scanning for tags.

@@ sim.mapped-all
Green squares: tags it has mapped; its blue estimates sit on the tags. This runs {{sim.factor}} times faster than
real time.

@@ sim.detail
Now one step at {{sim.detail-speed}} times real speed. It composes odometry, matches each detection to a known
beacon, then fixes its position.

@@ sim.detail.end
It writes its report: the decision, its pose after the position fix, and a one-line note. Both move checks allow the turn, and
only then is it executed. From here it keeps scanning; after two scans with no new beacon, its own rules end the
exploration. Notice the blue path staying on the black one.

@@ sim.result
It stopped by itself after {{cl.opus.steps}} steps, with {{cl.opus.tags-found}} of {{cl.n-tags}} tags mapped and no
phantoms. Its pose error was {{cl.opus.ate}} centimetres, against {{cl.opus.b0-ate}} for dead reckoning alone.

@@ sim.validator
What does a refused move look like? This is a scripted test, not a model.

@@ sim.validator.clip
Near the wall, the flags allow no forward move. The scripted model asks anyway; both checks refuse, and
nothing moves. After the emergency stop, every move is refused.

@@ car.part
Second, the real car, driven by the same harness and the same validator.

@@ car.episode
Top left, the phone video; below it, the car's own camera with the tags it detected, and the room from above. The
waiting is sped up; the motion plays in real time.

@@ closing
So a language model can run the whole loop, with a validator guarding every move. One episode is a demonstration;
the statistics are in the report.

@@ disclosure
Generative AI helped write this project and this video, as listed on screen and in the report. I'm responsible
for it.
