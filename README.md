# BeaconMind

Xiaohui Chen's individual class project for JHU EN.665.715, *Embodied Agentic AI for Robotic Control*.

**The question.** Can a large language model keep the pose and the landmark map of a small robot itself, instead of
handing that job to a classical estimator? A small differential-drive car explores a walled arena whose only
landmarks are AprilTags, and some tag IDs repeat. At every stop a stateless ReAct agent receives the odometry
increment and the tag detections as text, calls deterministic geometry tools, and decides which detections to
trust, which beacon each belongs to, and which pose and map to report. Code does the geometry; in closed loop a
validator checks every move.

- Report: [`course-project/report/Chen-Project-Report.pdf`](course-project/report/Chen-Project-Report.pdf) (IEEE
  format, 12 pages)
- Slide outline with speaker notes: [`course-project/slides/outline.md`](course-project/slides/outline.md)
- Demo recording: not recorded yet (see "Status")

## Result so far

A pre-registered study in a kinematic simulator: three models replayed the same 30 held-out episodes (1,976 steps)
with a 2 % odometry over-read, against dead reckoning (B0), a factor graph given the true association (B1) and the
agent's procedure written as code (B2). The outcome measure is the trajectory error (ATE-RMSE) per episode.

| Arm | Median trajectory error | Against dead reckoning (per-episode difference, exact 95 % interval) | Outcome of H1 |
| --- | --- | --- | --- |
| B0 dead reckoning | 16.7 cm | | |
| B1 factor graph, true association | 1.23 cm | | |
| B2 coded procedure | 11.7 cm | −2.74 cm [−4.87, −0.75] (descriptive) | |
| Claude Opus 5.5 | 12.1 cm | −2.83 cm [−4.93, −0.75] | rejected (Holm p = 0.0025), not practical |
| Qwen3.8-Flash-Next | 11.9 cm | −4.00 cm [−6.06, −1.85] | rejected (Holm p = 7.2 × 10⁻⁵), not practical |
| Gemma 4 26B | 69.3 cm | +56.7 cm [+38.2, +79.2] | not rejected: worse on 29 of 30 episodes |

What this does and does not show:

- Two models tracked the car better than dead reckoning. The gain is statistically supported and **not practically
  supported**: both intervals reach above the −3 cm that was set in advance as the smallest difference that matters.
- Those two models largely **reproduced the coded procedure** (within 1 cm of it on 28 and 26 of 30 episodes), which a
  short program computes at negligible cost. Their error stayed several times the factor graph's; that comparison
  (H2) was **not tested**, because the pre-registered gate needed every H1 rejected.
- Gemma 4 answered more than half of its steps without calling a tool and was much worse than dead reckoning (found
  in a post hoc check of the logs).
- In closed loop, where the model's own move is executed, there is so far one simulated episode per arm (n = 1) in a
  simulator of the real room, with a one-number variant of the prompt. Claude Opus 5.5 and Claude Fable 5.2 made
  the same moves as each other and, given the tool results each obtained, the coded procedure's decisions. That
  shows agreement with the procedure; it is not a result about driving. The episode had no odometry over-read and
  little travel, so there was little to correct, and dead reckoning was at least as accurate.
- **Limits.** Everything above is simulated: a kinematic simulator with placeholder sensor noise, one prompt, one
  run per episode, one drift level. It is a replay, so the coded procedure chose every move and the agent's own moves
  were not evaluated. The factor graph was given the true association. Copies of a repeated tag ID were far apart,
  so association was easy.

Every number in the report and in this table comes from `course-project/evidence/M4/M4.T16/` (the frozen analysis's
output) through `course-project/tools/report_assets.py`. The pre-registration, with its 22 declared deviations, is
`course-project/evidence/M4/M4.T1/prereg.md`; it is a self-registration in this repository, frozen by file hash
minutes before the runs.

## Status (2026-11-18)

Done: the simulated study and its analysis; the report for everything measured; the camera calibration; the survey
of the real arena (a room) and its 20-tag layout (a 3.0 m range limit is provisional until a tag pilot on real
frames); the recorder that keeps every real session; one closed-loop
episode per arm in a simulator of that room.

In progress, and **not results yet**: 12 of the 20 tags are printed and none is mounted; the car executor, the out-of-band stop,
tag perception, the simulator of the real room and the closed loop are written and tested against a simulated car,
not yet run on the car; no real episode has been recorded; the demo video does not exist yet. The report marks each
missing result in red, and `course-project/report/PENDING.md` lists them.

## Reproduce

Commands are run from the repository root. They were run on macOS with Python 3.13; the package needs Python 3.10
or later.

**Tests** (about 80 seconds; needs `pytest`, `numpy`, `scipy` and `jsonschema`; tests that need a GPU model server,
the car, GTSAM or an unpublished assignment file are skipped):

```bash
cd course-project/beaconmind && PYTHONPATH=src python3 -m pytest -q
```

Last run here: 499 passed, 10 skipped.

**The report's numbers and tables** (standard library only). This rewrites `course-project/report/generated/`
(`numbers.tex`, the two results tables, the room figure, and `MANIFEST.txt`, which names the evidence file behind
every number) from the analysis outputs in `course-project/evidence/`:

```bash
python3 course-project/tools/report_assets.py
python3 course-project/tools/report_assets.py --check     # prints "assets: up to date"
python3 course-project/tools/report_assets.py --pending   # lists the results still missing from the report
```

**The report PDF** (needs a TeX installation with `latexmk` and IEEEtran, which is in the folder):

```bash
cd course-project/report && latexmk -pdf -interaction=nonstopmode -halt-on-error Chen-Project-Report.tex
```

**The slide outline and its figures** (needs `pdflatex` and `pdftoppm`):

```bash
python3 course-project/tools/report_assets.py --slides
```

**What cannot be rerun from this repository alone.** The raw run logs of the study (about 185 MB: every step of
every model) are not in the repository; the analysis outputs computed from them are
(`course-project/evidence/M4/M4.T16/study_summary.json`, `study_per_seed.csv`, `judge_summary.txt`,
`error_sources.txt`). Rerunning the models needs an Anthropic API key and a GPU server for the two local models
(`course-project/tools/replay_run.py`, `study_sweep.sh`); rerunning the frozen analysis
(`course-project/tools/study_analyze.py`) and the freeze check (`course-project/tools/prereg_freeze.py --verify`)
needs those logs.

## Map of the repository

| Path | What it is |
| --- | --- |
| [`AGENTS.md`](AGENTS.md) | Rules for anyone, including an AI agent, working in this repository |
| [`course-project/CONTEXT.md`](course-project/CONTEXT.md) | The project's dated handoff log; the newest entry is the current state |
| [`course-project/AGENT-DESIGN.md`](course-project/AGENT-DESIGN.md) | The agent's design: missions, moves, tools, validator, the per-step procedure |
| `course-project/prompts/` | The system prompt (v3.3) every model received |
| `course-project/beaconmind/` | The Python package and its tests: simulators (`envs/`), tools and replay harness, validator and closed loop (`harness/`), baselines (`baselines/`), metrics and statistics (`metrics/`), tag perception (`perception/`), the car executor (`car/`) |
| `course-project/tools/` | Scripts: running and analysing the study, the report's numbers, camera calibration, room layout, session recorder |
| `course-project/configs/` | Design values, the car's measurements, the camera calibration, model settings, arena files |
| `course-project/evidence/` | What was measured, by task: `M4/M4.T1` pre-registration, `M4/M4.T16` study results, `M1/M1.T7` camera calibration, `M3/M3.T10` room survey and tag layout, `M4/M4.T11` the pilot |
| `course-project/report/` | The report: LaTeX source, PDF, generated numbers, review logs (`REVIEW.md`), missing results (`PENDING.md`) |
| `course-project/slides/` | Slide outline with speaker notes and the slide figures (the deck itself uses a university template that is not redistributed here) |
| `course-project/plan/` | The task plan; `README.md` §3.6 is the scope that applies |
| `course-project/firmware/esp32cam/` | The camera's firmware |
| `course-project/ros2_ws/`, `course-project/docker/` | The car's URDF and bring-up packages; the ROS 2 Humble container |
| `reference/hardware/` | Pin maps, wiring plan and build notes for the car |

## The car

A two-wheel differential-drive car with a caster, 0.66 kg:

- Raspberry Pi Pico 2 W (RP2350) running micro-ROS over Wi-Fi; it drives two 1:90 TT gear motors with Hall
  quadrature encoders through a TB6612FNG driver and reads a BNO055 inertial measurement unit.
- ESP32-CAM (OV3660) serving JPEG frames over HTTP, used at 1024 × 768; calibrated horizontal field of view 46.9°.
- Power: a 4 × AA pack for the motors, a USB power bank for the Pico and the camera.
- Host: an NVIDIA DGX Spark, which runs the ROS 2 container, the simulators, the two local models and the Wi-Fi
  access point the car joins.

The car runs a build of the course's lab firmware; the bounded moves and the stop are done on the host. Pin maps
and the wiring plan are in `reference/hardware/`. Network names, passwords, addresses and keys are not in this
repository: `wifi_config.h` stays on the machine that flashes the boards.

## Generative-AI disclosure

Generative AI did most of the drafting, coding and running in this project, under Xiaohui Chen's direction.

- **Claude Opus 5.5** (Anthropic; through Cursor and Claude Code): the design documents and the system prompt, the
  simulator, harness, baselines, metrics and analysis code, the pre-registration, the pilot and the study runs, the
  first draft of the report, the camera firmware, the car model, the session recorder and the room-layout tools.
- **Claude Fable 5.2** (through Claude Code): the camera-calibration records, tag perception, the car executor, the
  room simulator and the closed loop, the rewrite of the report for the main study, the script that generates the
  report's numbers, the slide outline, and this README.
- **Claude Fable 5.1**: the first Related Works section of the report and its references.
- **Grok 4.7** (through Cursor): the early package (schemas, configuration files, the geometry port and its tests,
  the first camera sketch, the ROS 2 container, latency probes) and the first version of this README and of
  `AGENTS.md`.
- **GPT-5.6 Sol** (through Cursor): early comparison of project ideas.
- Fresh AI reviewer agents checked the code, the pre-registration, the analysis and the report; their findings are
  logged in the `REVIEW.md` files.
- Claude Opus 5.5, Qwen3.8-Flash-Next and Gemma 4 26B are also the systems under test, as is Claude Fable 5.2 in
  the simulated closed-loop episode, and GPT-6.1 Sol scored the
  agents' notes.

Files carry an `AI-assisted:` line naming the model and what it did. Xiaohui Chen chose the question, the models
and the scope, took every physical measurement, and is accountable for everything submitted.
