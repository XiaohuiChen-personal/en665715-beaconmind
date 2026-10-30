# M6 — Demo and presentation

Written 2026-10-05. Part of the BeaconMind implementation plan. **Read
[`plan/README.md`](README.md) first** (session protocol §1, conventions §5, contracts §6, safety
rules §7). If anything here contradicts the README, the README wins. If the README contradicts
`AGENT-DESIGN.md` v3.3 (or the v3.4 that M1.T10 writes), AGENT-DESIGN wins, and the executor stops and
reports the conflict (README §1.4 item 8).

## Goal

Show BeaconMind working, honestly, to the course. That means four things:

1. **A course demo driven by ROSA** in the `rosa-ros2` container (AGENT-DESIGN D10, "Course demo").
   The demo makes the ReAct loop visible: observation → tool calls → tool results → belief report →
   validated move. It follows one fixed script: explore an unseen arena, return to the start, drive to
   a named beacon, and refuse "follow that person". It runs in the Isaac Sim twin and on the real car.
   The benchmark keeps its own harness (M2.T7). **ROSA runs are demo-only and not
   benchmark-comparable** (D10), and every demo artifact says so.
2. **A time-lapse demo video.** The robot stops to think for up to a minute per step, so the video
   speeds up the thinking and plays the motion at real speed, with the speed shown on screen.
3. **Slides on the JHU template** that pass `tools/validate_presentation.py`, with an aligned talk
   track, and a rehearsed presentation.
4. **The final submission package**: report PDF (from M5), slides, video, code archive, and an audit
   showing that every artifact carries its generative-AI disclosure (AGENTS.md §5). It ends with the
   final `CONTEXT.md` update.

## Entry criteria

- M6.T1 (deliverables) can start **now**: it needs nothing.
- The demo runtime (M6.T2, T7, T8) needs M2.T1 (tools, validator, latch), M2.T13 (observation
  builder), M2.T14 (report parser and correction), M2.T3 (kinsim), M2.T7 (harness) and M2.T20
  (mission metrics) `done`, and decisions OD8 (M1.T4) and OD14 (M1.T10) recorded.
- The simulation demo (M6.T9, T10) needs M2.T5, M2.T6 and M2.T17 (`envs/ros_env.py`) `done`; the
  Isaac re-render (M6.T13) also needs M2.T15 (arena builder) and M2.T16 (Isaac car).
  **Isaac fallback branch (README §3.4; cross-plan consistency review, 2026-10-06):** if Xiaohui approved
  the kinsim fallback, those M2 tasks never finish. Then stop and ask Xiaohui to confirm the default:
  set M6.T9 and M6.T13 to `blocked` with the note "Isaac fallback", run the M6.T10 take on kinsim through
  the M6.T8 kinsim path (same session folder, decider and script), use the M6.T12 top-down view as the
  main view (MD5 fallback), and label every artifact "kinematic simulation, not Isaac Sim".
- The car demo (M6.T3) needs **M3.T18** `done` (closed-loop real L2 runs proven on this car; it
  implies M3.T12, the M3.T7 wheels-down gate and the M3.T1 STBY pull-down), plus M3.T13 (STOP hotkey
  and latch) and M3.T17 (overhead ground-truth accuracy acceptance). M3.T18 is dropped at the cut line,
  so M6.T3 is too.
- The slides' results (M6.T5, final build) need M4.T16 `done` (or M2.T12 under the cut line) and
  M5.T9 (`report/generated/numbers.json`) and M5.T4.
- The final package (M6.T6) needs M5.T7 `done`.

## Exit criteria (from README §3.1, made checkable)

- [ ] A ROSA demo take in simulation exists whose session folder holds the trace, run logs and
      `segments.json`, and whose run header says `"benchmark_comparable": false` (M6.T10).
- [ ] A ROSA demo take on the car exists with the same files plus phone footage (M6.T3). **Under the
      cut line (README §3.4) this item is `dropped (cut line)`.**
- [ ] A time-lapse demo video with title, segment, honesty and disclosure cards, checked with
      `ffprobe` and inside the length limit confirmed in M6.T1 (M6.T16).
- [ ] The final deck passes `python3 tools/validate_presentation.py` with zero errors, and its
      talk track is aligned (M6.T5). It has been rehearsed to within ±10 % of the time limit (M6.T17).
- [ ] The disclosure audit reports zero missing disclosures, and the secrets scan prints nothing
      (M6.T6).
- [ ] The submission checklist is complete and `CONTEXT.md` has the final entry (M6.T6). Xiaohui
      submits; the executor never uploads anything.

## What M6 unlocks

The project's end: everything the course grades at 2026-12-13. M6 also produces the stills and demo
numbers that M5's report may cite (labelled "demo, not benchmark") and the evidence trail that counts
toward the 60 % preparation-and-participation part of the grade (AGENTS.md §5, README §2).

## Prerequisites from other milestones

| Task | Needed by | What M6 uses from it |
| --- | --- | --- |
| M1.T1 | all | Layout (L1), `.gitignore` lines, `tools/sync_to_spark.sh`, `tools/pull_evidence.sh`, pytest configuration, `pyproject.toml` with extras |
| M1.T3 | T7, T9 | The `beaconmind-ros` container, with `course-project` mounted at `/workspace/course-project` |
| M1.T4 | T2, T8 | OD8: the closed-loop model setting (thinking on or off) that passes the 60 s p95 gate |
| M1.T10 | T2 | OD14 (the `bm-tools` MCP server) and, if recorded, the demo-runtime decisions MD1–MD3 below; AGENT-DESIGN v3.4 |
| M2.T1 | T2, T7 | `beaconmind.tools.dispatch`, `StepContext` (fields per `plan/M2-sim-mvp.md` M2.T1 step 4: `observation`, `prev_report`, `dv`, `executor: Callable[[str], dict] \| None`, `latch`, `moved`, `estop`, `violations`, `tool_log`), `beaconmind.validator` (`check_move`, `Latch`, `bm-clear-latch`) |
| M2.T13 | T7 | `beaconmind.observation` (C3 builder, counters, safety flags, auto-latch) |
| M2.T14 | T7 | `beaconmind.report` (C6 parser and the C5 item 4 harness correction) |
| M2.T2 | T4, T9 | `beaconmind.worlds.generate` / `check`, CLI `python -m beaconmind.worlds generate --condition … --seeds A-B --out <dir>` |
| M2.T3 | T7, T4 | The kinematic simulator environment (`envs/kinsim.py`) |
| M2.T5 | T9 | The Isaac twin, `bm_sim_pico`, its headless launch command and sim bring-up |
| M2.T15, M2.T16 | T13 | The Isaac arena builder from a C7 world, and the Isaac car asset |
| M2.T17 | T7, T9 | `envs/ros_env.py` (`RosEnv`), the ROS environment adapter |
| M2.T6 | T9 | Simulated perception feeding the observation builder |
| M2.T7 | T7 | The harness's step-message builder and run-log writer; `configs/providers.json` |
| M2.T20 | T7, T10 | Mission success and SPL from ground truth (C10.5) |
| M2.T12 / M4.T16 | T5 | Result tables and figures (`report/generated/figures/`, M4.T16; the slides never type a number by hand) |
| M3.T1, M3.T7 | T3 | STBY pull-down fitted; wheels-down gate passed (S2, S5) |
| M3.T9, M3.T10, M3.T11 | T3, T15 | Real-car bridge (`envs/ros_env.py` with `source: real`, `PicoClient` owning the heartbeat), physical arena spec, overhead ground-truth camera |
| M3.T12 | T3 | The real-run **session-start checks** (M3.T12 step 2) and the per-log placement check (step 3) |
| M3.T13 | T3, T9 | The out-of-band STOP hotkey `bm-estop` (tmux window `bm:estop`) and the latch file / `bm-clear-latch` |
| M3.T17 | T3, T15 | Overhead ground-truth accuracy accepted (5 cm / 3°) |
| M3.T18 | T3 | Closed-loop real L2 runs proven on the car with the demo model |
| M3.T20 | T3 | The untethered power path actually in use (OD9) |
| M4.T14 | T5, T16 | Request-suite refusal rates on held-out contexts (to put the demo's single refusal in context). **Under the cut line M4.T3 and M4.T14 are `dropped (cut line)` (`M4-benchmark.md` "Cut line in M4"), so no benchmark refusal rate exists: the slide and the honesty card then say "refusal was not benchmarked; the demo shows one refusal" and cite no rate** |
| M5.T9 | T5 | `report/generated/numbers.json` (`{key: value}`), the single source of every benchmark number on the slides |
| M5.T2, M5.T4, M5.T7 | T5, T6 | Architecture figure, results section, final report PDF |

## Status table

| Task | Title | Status | Effort | Evidence | Last updated | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| M6.T1 | Confirm the final deliverables with Xiaohui (formats, lengths, where they are submitted) | todo | S | `evidence/M6/M6.T1/` | 2026-10-05 | Can run now |
| M6.T2 | ROSA demo runtime in `rosa-ros2`: MCP servers exposing the D5 tools, `RobotSystemPrompts` v3.3+, `accumulate_chat_history=False`, against the Isaac twin | todo | M | `evidence/M6/M6.T2/` | 2026-10-05 | Delivers the `bm-tools` MCP server and container access; the runner is T7–T8, the twin run is T9 |
| M6.T3 | The same ROSA demo on the car | todo | M | `evidence/M6/M6.T3/` | 2026-10-05 | Dropped at the cut line |
| M6.T4 | Demo script and filming: explore, return to start, go to a named beacon, refuse "follow that person"; time-lapse video | todo | S | `evidence/M6/M6.T4/` | 2026-10-05 | Delivers the script, the shot list and the kinsim dry run; filming and video are T10–T16 |
| M6.T5 | Slides on the JHU template, validated, with a talk track | todo | M | `evidence/M6/M6.T5/` | 2026-10-05 | |
| M6.T6 | Final submission package and an AI-disclosure audit of every artifact | todo | S | `evidence/M6/M6.T6/` | 2026-10-05 | Last task of the project |
| M6.T7 | Demo environment server, file RPC and stub runner (no LLM) | todo | S | `evidence/M6/M6.T7/` | 2026-10-05 | Appended |
| M6.T8 | ROSA decider, ReAct console, demo trace and tmux capture; kinsim smoke with the real model | todo | S | `evidence/M6/M6.T8/` | 2026-10-05 | Appended |
| M6.T9 | Isaac twin hookup: 3-step ROSA smoke and an estop check in the twin | todo | S | `evidence/M6/M6.T9/` | 2026-10-05 | Appended |
| M6.T10 | Simulation demo take in the Isaac twin | todo | S | `evidence/M6/M6.T10/` | 2026-10-05 | Appended; hours of unattended model time |
| M6.T11 | Video logic: edit decision list, time-lapse fitting, frame times, render plan, ffmpeg plan | todo | S | `evidence/M6/M6.T11/` | 2026-10-05 | Appended; pure Python |
| M6.T12 | Video renderers: terminal frames, belief panel, top-down view, cards | todo | S | `evidence/M6/M6.T12/` | 2026-10-05 | Appended; Pillow |
| M6.T13 | Isaac Sim re-render of a take's ground-truth trajectory | todo | M | `evidence/M6/M6.T13/` | 2026-10-05 | Appended; fallback is the top-down view |
| M6.T14 | Simulation demo video assembly | todo | S | `evidence/M6/M6.T14/` | 2026-10-05 | Appended |
| M6.T15 | Car demo video assembly (phone footage, terminal, time-lapse) | todo | S | `evidence/M6/M6.T15/` | 2026-10-05 | Appended; dropped at the cut line |
| M6.T16 | Final demo video: cards, narration, checks | todo | S | `evidence/M6/M6.T16/` | 2026-10-05 | Appended |
| M6.T17 | Rehearsal and, if required, the recorded presentation | todo | S | `evidence/M6/M6.T17/` | 2026-10-05 | Appended |

## Task list

| ID | Title (short) | Depends on | Effort | Machine |
| --- | --- | --- | --- | --- |
| M6.T1 | Confirm deliverables | — | S | Mac + Xiaohui |
| M6.T2 | `bm-tools` MCP server, prompt vendoring, `rosa-ros2` access | M2.T1, M1.T10 (OD14), M1.T4 (OD8) | M | Mac; Spark container `rosa-ros2` |
| M6.T7 | Environment server, file RPC, stub runner | M6.T2, M2.T3, M2.T7, M2.T13, M2.T14, M2.T20 | S | Mac; Spark host; Spark container `beaconmind-ros` |
| M6.T8 | ROSA decider, console, trace, tmux capture, kinsim smoke | M6.T7 | S | Spark containers `rosa-ros2`, `beaconmind-ros`, `vllm-rosa` |
| M6.T4 | Demo script, seed choice, kinsim dry run | M6.T8, M2.T2 | S | Mac; Spark |
| M6.T9 | Twin hookup smoke | M6.T8, M2.T5, M2.T6, M2.T17 | S | Spark host (Isaac) + both containers |
| M6.T10 | Simulation take | M6.T4, M6.T9 | S | Spark |
| M6.T11 | Video logic | M6.T7 (trace format) | S | Mac; Spark host |
| M6.T12 | Video renderers | M6.T11 | S | Mac; Spark host |
| M6.T13 | Isaac re-render | M6.T11, M6.T10, M2.T15, M2.T16 | M | Spark host (Isaac) |
| M6.T14 | Simulation video assembly | M6.T12, M6.T13 (or its fallback) | S | Spark host |
| M6.T3 | Car take | M6.T10, M3.T18, M3.T13, M3.T17 | M | Spark + Xiaohui in the arena |
| M6.T15 | Car video assembly | M6.T3, M6.T12 | S | Mac + Spark host + Xiaohui |
| M6.T16 | Final demo video | M6.T14, M6.T15 (or cut line) | S | Spark host + Mac + Xiaohui |
| M6.T5 | Slides and talk track | M6.T1; final build after M4.T16 (or M2.T12), M5.T9, M5.T4, M6.T14 stills | M | Mac |
| M6.T17 | Rehearsal / recording | M6.T5, M6.T16 | S | Mac + Xiaohui |
| M6.T6 | Final package, disclosure audit, final CONTEXT update | everything else in M6, M5.T7 | S | Mac (+ Spark for video checks) |

## Suggested execution order and parallel groups

- **Group A (now):** M6.T1. Cheap, and its answers fix lengths and formats for everything else.
- **Group B (after M2.T1, M2.T3, M2.T7, M2.T13, M2.T14, M2.T20, M1.T10, M1.T4):** M6.T2 → M6.T7 →
  M6.T8 → M6.T4.
- **Group C (in parallel with B once M6.T7 has produced a stub session):** M6.T11 → M6.T12. The video
  tools are developed on cheap stub sessions, so no hours of model time are wasted on framing bugs.
- **Group D (after M2.T5, M2.T6, M2.T17 and Group B; M6.T13 also after M2.T15, M2.T16):** M6.T9 →
  M6.T10 → M6.T13 → M6.T14.
- **Group E (after M3.T18, M3.T13, M3.T17):** M6.T3 → M6.T15.
- **Group F:** M6.T16 after Groups D and E (or D alone under the cut line).
- **Group G:** M6.T5. Build the deck skeleton early (after M6.T1) to prove the template and validator
  path; fill results after M4.T16 (or M2.T12) and M5.T9, and stills after M6.T14. Then M6.T17, then M6.T6.

**Calendar rules (README §3.4).** At ≤ 21 days left, only M5 and M6 tasks run. At ≤ 7 days left, only
M5.T7 and M6.T6 run. **So M6.T16 and M6.T5 must be finished before 8 days are left** (that is, by
2026-12-05). At the start of every M6 session, compute the days left
(`python3 -c "import datetime as d; print((d.date(2026,12,13)-d.date.today()).days)"`, Mac) and tell
Xiaohui if a rule applies.

**Cut line (README §3.4):** M6 becomes the simulation demo (M6.T2, T7–T14, T16), the slides (T5, T17)
and the package (T6). M6.T3 and M6.T15 are set to `dropped (cut line)`, and the honesty card and the
slides say that the car demo was not run, and why.

---

## M6 decisions (proposed defaults; Xiaohui approves)

These are M6-specific choices. Each has a default; the task that needs it stops and asks if the choice
is not already recorded in `AGENT-DESIGN.md` (v3.4) or `CONTEXT.md`. Record every answer in
`CONTEXT.md` with the date and Xiaohui's words; record MD1–MD3 also as a line in AGENT-DESIGN D10 (with
their approval, README §1.4 item 6).

| ID | Decision | Default | Alternative, and when | Asked in |
| --- | --- | --- | --- | --- |
| MD1 | ROSA tool set in the demo | **Trimmed:** an `McpOnlyROSA` subclass (pattern: `discussions/module4/rosa_agent_l2.py` `McpOnlyROSA`) so the model sees only the nine `bm-tools` tools and only the robot prompt. Reasons: the 2026-10-01 proposal talk track told the instructor "ROSA, trimmed to the MCP tools, remains the course-demo runtime"; it saves about 6k tokens per call (D10: 5,195 + 819); and stock ROSA's ROS 2 tools may be able to actuate the robot outside the validator (checked in M6.T2 step 5) | **Stock ROSA** (47 built-in tools + nine fixed prompts, as D10's wording implies), only in simulation, and only if M6.T2 step 5 finds no tool that can publish, call a service or set a parameter | M6.T2 |
| MD2 | How ROSA reaches the robot | **Environment server:** a process in `beaconmind-ros` owns the environment (kinsim, twin or car), the observation builder and the move execution; the ROSA runner in `rosa-ros2` talks to it through files in the shared session folder (contract M6-C4). D10's "subscribed to the project container's topics" is met by the environment server, which subscribes in `beaconmind-ros`, where M2/M3 tested that code | **Direct:** the runner in `rosa-ros2` imports `beaconmind.envs.ros_env` and subscribes itself; only if Xiaohui wants ROSA's own process on the ROS graph and M6.T9 step 4 shows every import works in `rosa-ros2` | M6.T2 |
| MD3 | How `rosa-ros2` sees `course-project/` | **Add one bind mount** `../../../course-project:/workspace/course-project` to `assignments/assignment2/ollama/docker-compose.yml`, then `docker compose up -d` (recreates the container, keeps the image; same as the 2026-09-13 `discussions/` mount) | **A second container** `bm-rosa-demo` from the same image `ollama-ros2:latest` with the mount, leaving `rosa-ros2` untouched; if Xiaohui does not want the course container changed | M6.T2 |
| MD4 | Demo world | **Dedicated demo seeds 3000–3009** (outside the dev 1000–1099 and test 2000–2199 ranges of C7), condition `duplicated`; the first seed that passes the rule in M6.T4 step 3. No re-selection after a failed dry run unless Xiaohui approves, and then the honesty card says so | A dev seed, if Xiaohui prefers a world the prompt was tuned on (then say so on the card) | M6.T4 |
| MD5 | Simulation footage | **Isaac Sim re-render** of the take's logged ground-truth poses (M6.T13), labelled "re-rendered from logged ground truth"; framing can be retried without re-running the model | Live capture inside the twin process (changes M2.T5 code; only if Xiaohui insists); or the 2D top-down view (M6.T12) if the re-render fails | M6.T13 |
| MD6 | Video editing | **Automated assembly with ffmpeg on the Spark** (`~/.local/bin/ffmpeg` 7.0.2-static, verified 2026-10-05), plus Xiaohui's voice-over recorded in QuickTime Player on the Mac and muxed on the Spark | Xiaohui edits the parts in their own editor; the automated cut is then a draft | M6.T14 |
| MD7 | How the slides are shown | **The LibreOffice PDF export, full screen in Preview** (the validated deck renders identically there; PowerPoint is not installed on the Mac, checked 2026-10-05) | Keynote import of the `.pptx` (Keynote is installed), only after a slide-by-slide visual check, because the import can move text | M6.T17 |

---

## M6 conventions and file formats (used by several tasks)

These extend README contracts C2, C3, C6, C9 and C10 for the demo. They are **demo-only** formats: no
benchmark code reads them. (Reading note for the whole file: inside Markdown tables, `\|` stands for a
plain `|`; type `|` when you run such a command. A Prerequisites row that checks a task's status with
`grep -E '^\| M<n>\.T<k> ' …` is the older form of `python3 course-project/tools/task_status.py M<n>.T<k>`
(README convention L12): run the helper instead, because the grep also matches task-list and dependency
rows that carry no status.) Write their JSON Schemas as `beaconmind/src/beaconmind/schemas/bm.<name>-1.schema.json`
in the task that first writes the file.

### M6-C1 — Demo session folder

Path on the Spark host: `~/Projects/EN.665.715/course-project/data/demo/<session_id>/`. The same
folder is `/workspace/course-project/data/demo/<session_id>/` inside `beaconmind-ros` and inside
`rosa-ros2` (after MD3). **Every path stored inside a session file is relative to the session folder**,
because the host and container paths differ.

- `session_id` = `<YYYYMMDD-HHMMSS>-<source>-<label>`, for example `20261120-140501-sim-take1` or
  `20261101-093000-kinsim-stub`. `source` ∈ `kinsim`, `sim`, `real`.
- Demo sessions **never** go under `data/runs/` or `data/obslogs/`, so no benchmark sweep or metric
  ever reads them.
- Create the folder on the Spark host as `xiaohui_chen` (not from a container), so both containers can
  write in it (`rosa-ros2` runs as uid 1000). `new_session` (M6.T7 step 9) creates **every** subfolder
  of the tree below (`ctx/`, `rpc/env/`, `runlog/`, `state/`, `term/`, `phone/`, `video/`) at
  creation time, because `beaconmind-ros` may run as root (M1.T3 decides) and a folder created by
  root cannot be written by uid 1000. Code never creates a new subfolder at run time except under
  `video/` (written only from the Spark host venv).
- **Latch file per session kind** (follows M2.T1's rule: closed loop in Isaac or on the car →
  `data/LATCH`; kinsim episodes → a per-episode latch): `session.json` field `latch_path`, relative to
  the session folder, is `"LATCH"` (the session's own file) when `source` is `kinsim`, and
  `"../../LATCH"` (that is `course-project/data/LATCH`, C5 item 5) when `source` is `sim` or `real`.
  Every demo component (the `bm-tools` handler, the environment server, `demo/estop.py`) reads this
  field and never builds the path any other way. A kinsim session's own `LATCH` may be deleted with
  `rm` (no robot, throwaway session); **`data/LATCH` is cleared only with `bm-clear-latch`** (C5 item
  5; on the car only by Xiaohui, M3.T12 step 2).

```
data/demo/<session_id>/
├── session.json            # M6-C2 header
├── script.json             # copy of configs/demo_script.json used for this session
├── world.json              # copy of the world spec (C7)
├── ctx/step_ctx.json       # M6-C3, written by the runner before each model call
├── ctx/tools.jsonl         # M6-C3, one line per tool call, appended by bm-tools
├── rpc/env/                # M6-C4 request/response files
├── trace-runner.jsonl      # M6-C5 events from the runner
├── trace-env.jsonl         # M6-C5 events from the environment server
├── runlog/<episode_id>.jsonl   # bm.runlog/1 (C9.2), one file per segment
├── obslog.jsonl            # bm.obslog/1 (C9.1), driver "L2:<model_key>@rosa-demo"
├── segments.json           # M6-C6 outcome per segment
├── state/after-<segment>.json  # resume points (M6.T7)
├── term/<n>.runner.txt, term/<n>.env.txt   # tmux pane captures, 2 per second (M6.T8)
├── phone/                  # car takes only: phone clips (M6.T15)
└── video/                  # renders, frames and outputs (M6.T13–T16)
```

### M6-C2 — `session.json` (`bm.demo_session/1`)

```json
{"schema": "bm.demo_session/1", "session_id": "20261120-140501-sim-take1", "take": 1,
 "source": "sim", "decider": "rosa", "rosa_mode": "trimmed", "model_key": "qwen35-a3b-think",
 "provider_entry": {"provider": "vllm", "model": "Qwen/Qwen3.5-35B-A3B", "...": "the C11 entry, key name only"},
 "prompt_sha12": "…", "tool_schema_sha12": "…", "dv_sha12": "…",
 "code_sha12": {"beaconmind/src/beaconmind/demo/run.py": "…"},
 "script_id": "demo-v1", "world_id": "sim-dup-s3000", "env_rpc": true, "latch_path": "../../LATCH",
 "host": "spark-2a60", "started": "2026-11-20T14:05:01-06:00", "ended": null,
 "benchmark_comparable": false, "notes": ""}
```
`prompt_sha12` is `null` when `new_session` writes the file (the host venv has no `rosa`, so it cannot
load the prompt); `run.py --decider rosa` fills it inside `rosa-ros2` before the first step (M6.T8
step 3). A `rosa` session whose `prompt_sha12` is still null after its first step is invalid.

### M6-C3 — Step context and tool records

`ctx/step_ctx.json` (`bm.demo_ctx/1`), rewritten atomically by the runner before each model call:
```json
{"schema": "bm.demo_ctx/1", "obs_id": "sim-dup-s3000-EXPLORE-k0-s014", "step": 14,
 "segment": "explore", "mission": "EXPLORE", "mode": "closed_loop",
 "observation": {"…": "C3 OBSERVATION"}, "previous_report": {"…": "C6"},
 "step_context": {"…": "the serialised M2.T1 StepContext (M6.T2 step 9 defines the serialiser)"},
 "move_state": {"executed_for_obs_id": null, "executed_action": null, "last_forward_result": null,
                "last_forward_m": null, "cmd_seq": 0}}
```
`move_state` lives in its own file `ctx/move_state.json` once the first `move` of the session has run
(the runner seeds it from `step_ctx.json`); `update_move_state` reads and writes that file.
`ctx/tools.jsonl` (`bm.demo_tool/1`), one line per tool call, appended by the `bm-tools` server under
an exclusive `fcntl` lock:
```json
{"schema": "bm.demo_tool/1", "obs_id": "…", "seq": 3, "name": "gate_detection",
 "args": {"…": "…"}, "result": {"…": "…"}, "violations": [],
 "t_start": 1763647501.12, "t_end": 1763647501.41, "pid": 4711}
```
`violations` is the list `dispatch` appended to `ctx.violations` during this call (C5: `guardrail`,
`invalid_tool_call`). Each `bm-tools` call runs in a **new process** (Module 4 DESIGN §1), so this
record is the only way the runner learns of them; the runner adds them to the step's run-log line.

**Locks** (all `fcntl.flock` on separate files in `ctx/`): `.ctx.lock` (step context and tool
records; held only for a read or an append, milliseconds); `.move.lock` (held by a `move` call for the
whole dispatch, so two concurrent `move` calls for one `obs_id` cannot both execute).
`emergency_stop` **never** takes `.move.lock`: it must not wait for a running move to finish.

### M6-C4 — Environment RPC over files (`bm.demo_rpc/1`)

One server (the environment server, M6.T7) and several clients (the runner; each `bm-tools` process for
`move` and `emergency_stop`). Directory `rpc/env/`.

- Request `req-<id>.json`: `{"schema": "bm.demo_rpc/1", "id": "<uuid4 hex>", "op": "<op>",
  "payload": {…}, "t_wall": <time.time()>}`. Response `res-<id>.json`: `{"id": "<same>", "ok": true,
  "result": {…}, "error": null, "t_wall": …}`.
- Every write goes to `.<name>.tmp` first, then `os.replace` (atomic on one filesystem). The server
  handles requests in `t_wall` order, one at a time, deletes the request after writing the response;
  the client deletes the response after reading it.
- Ops and timeouts:

| `op` | `payload` | `result` | Client timeout |
| --- | --- | --- | --- |
| `observe` | `{}` | `{"observation": C3, "detections_internal": [...], "gt_pose_map": {x_m, y_m, theta_deg} or null, "det_truth": [...]}` | 30 s |
| `execute` | `{"move": C2 MoveCommand}` | C2 MoveResult | `timeout_s` + 10 s |
| `set_mission` | `{"mission": "RETURN_TO_START"}` | `{"mission": …, "steps_left": …}` | 10 s |
| `estop` | `{"reason": "…"}` | `{"latched": true}` | 10 s |
| `status` | `{}` | `{"latched": bool, "mission": …, "steps_left": …, "source": …}` | 10 s |
| `shutdown` | `{}` | `{"bye": true}` | 10 s |

- **An `execute` that times out returns** `{"result": "link_lost", "reason": "environment server did
  not answer in <n> s"}` to the caller, which auto-latches (D5). Never retry a move blindly.
- The environment server refuses (`result: "refused"`) any `execute` when the session's latch file
  (`latch_path`, M6-C1) exists, when a move was already executed for that `obs_id`, or when the command
  exceeds the C2 caps (`0 < distance_m ≤ 0.25`, `|angle_deg| ≤ 30`, `v_max_mps` ≤ C0 `v_max_mps`,
  `w_max_dps` ≤ C0 `turn_rate_dps`, `timeout_s` ≤ C0 `move_timeout_s`; turns have `distance_m` 0).
  This repeats the validator's checks on purpose (defence in depth, D6).
- **MoveCommand built from an action** (the M2 `StepContext.executor` takes an action string): use
  M2's own builder if M6.T7 step 1 finds one; otherwise exactly C2: `FORWARD_25` → distance 0.25,
  `FORWARD_10` → 0.10, `BACKWARD_10` → `min(0.10, move_state.last_forward_m)` with the sign carried by
  the action (C2 has no negative distance), `TURN_LEFT_30` → `angle_deg` +30, `TURN_RIGHT_30` → −30;
  `v_max_mps`, `w_max_dps` (= `turn_rate_dps`) and `timeout_s` (= `move_timeout_s`) from
  `configs/dv.json`; `cmd_seq` = `move_state.cmd_seq + 1`; `obs_id` from the step context.

### M6-C5 — Demo trace events

`trace-runner.jsonl` and `trace-env.jsonl`, one JSON object per line: `{"t_wall": time.time(), "src":
"runner"|"env", "kind": …, "session_id", "segment", "step", "obs_id", …}`. Both containers share the
host clock, so `t_wall` values are comparable. Kinds and their extra fields:

| `kind` | `src` | Extra fields |
| --- | --- | --- |
| `session_start`, `session_end` | runner | `script_id`, `world_id` |
| `segment_start`, `segment_end` | runner | `mission`; at the end `decision`, `steps`, `ended_by` |
| `operator_request` | runner | `text` |
| `step_start` | runner | `mission`, `steps_left` |
| `observation_ready` | runner | `n_detections`, `status` |
| `llm_start`, `llm_end` | runner | at the end `latency_s`, `final_chars` |
| `tool_start`, `tool_end` | runner | `name`, `args` (start), `result_brief` (end) |
| `report` | runner | `decision`, `pose_source`, `requested_mission`, `note`, `message` |
| `violation` | runner | `code`, `detail` |
| `sync_marker` | runner | `label` (for example `CLAP`) |
| `pause_start`, `pause_end` | runner | `next_segment` (car takes, `--pause-between-segments`, M6.T7 step 10) |
| `env_ready` | env | `source`, `world_id` |
| `move_start`, `move_end` | env | `cmd_seq`, `action`; at the end `result`, `duration_s` |
| `estop` | env | `reason` |
| `mission_set` | env | `mission`, `steps_left` |

### M6-C6 — `segments.json` (`bm.demo_segments/1`)

A list, one object per segment: `{"segment", "mission_requested", "decision_final", "ended_by",
"answered_at_step", "steps", "moves_executed", "moves_after_answer", "success": true|false|null,
"success_rule": "C10.5 EXPLORE" | "C10.5 RETURN_TO_START" | "C10.5 GO_TO_BEACON" | "REFUSED, no move
after the answer", "spl": float|null, "gt_source": "kinsim"|"sim"|"overhead"|"none", "scored": bool,
"decision_latency_p50_s", "decision_latency_p95_s", "wall_s", "violations": {"format": n, "state": n,
"invalid_tool_call": n, "guardrail": n}, "notes"}`.
- `ended_by` ∈ `DONE`, `REFUSED`, `ASK`, `STOPPED`, `steps_left`, `latch`, `status_error`,
  `max_steps`, `request_unanswered`, `no_target`, `infrastructure` (the M6-C7 rule that ended it).
- `answered_at_step` = the segment step at which the operator request was answered (null for
  `explore`, or if never answered); `moves_after_answer` = moves executed at or after that step.
- `success` is decided **from ground truth by the evaluator** (C10.5, M2.T20), never from the agent's
  claim; `null` when there is no ground truth. The runner writes every segment with `success: null`,
  `spl: null`, `scored: false`; **`demo/score.py` (M6.T7 step 8b) fills them afterwards** in
  `beaconmind-ros` or the host venv, because the runner itself runs in `rosa-ros2`, where the M2
  metrics' dependencies are not guaranteed (M6.T8 step 0).

### M6-C7 — Demo script (`configs/demo_script.json`, `bm.demo_script/1`)

**Important (AGENT-DESIGN D7 step 7, row 0):** with mission `REPORT` or `STOP`, row 0 wins and the agent
answers `NONE`/`STOPPED` **without reading the operator request**. So an operator request is delivered
while the previous segment's mission is still set (`"mission": "carry"`); row 1b then answers it.

```json
{"schema": "bm.demo_script/1", "script_id": "demo-v1",
 "sim_world": {"condition": "duplicated", "seed_candidates": [3000, 3001, 3002, 3003, 3004, 3005, 3006, 3007, 3008, 3009],
               "chosen_seed": null, "world_id": null},
 "real_arena": null,
 "request_repeat_max": 3,
 "segments": [
  {"name": "explore", "mission": "EXPLORE", "operator_request": null,
   "expect": {"decision": "DONE"}, "max_steps": 150},
  {"name": "return", "mission": "carry", "operator_request": "Please go back to where you started.",
   "expect": {"requested_mission": "RETURN_TO_START", "decision": "DONE"}, "max_steps": 60},
  {"name": "goto", "mission": "carry", "operator_request": "Drive to beacon {target}.",
   "target_rule": "confirmed_unique_closest_to_1.2m",
   "expect": {"requested_mission": "GO_TO_BEACON {target}", "decision": "DONE"}, "max_steps": 60},
  {"name": "refuse", "mission": "carry", "operator_request": "Follow that person.",
   "expect": {"decision": "REFUSED", "moves_after_answer": 0}, "max_steps": 3}]}
```
Segment flow (implemented in M6.T7 `runner_core.py`):
1. At segment start, the mission is the segment's `mission` (or the previous one for `carry`).
2. While `operator_request` is unanswered, put it in every step message, up to `request_repeat_max`
   steps (D7 row 1b: "The harness repeats the request until it is answered"). It is answered when the
   corrected report has a non-null `requested_mission`, or decision `REFUSED` or `ASK`. A request can
   be deferred by D7 row 1 (contact recovery, which comes before row 1b, may execute `BACKWARD_10`); that
   is correct behaviour, which is why `refuse` has `max_steps` 3 and its success rule counts only moves
   **at or after** the answering step.
3. On `requested_mission`, call the environment's `set_mission` (this resets `steps_left`, D2) and
   continue with `operator_request: null`.
4. The segment ends (first match, recorded as `ended_by`, M6-C6) on decision `DONE`, `REFUSED`, `ASK`
   or `STOPPED`; on `steps_left` = 0; on a latch; on 3 consecutive `status: error` observations; when the
   request is still unanswered after `request_repeat_max` steps (`request_unanswered`; the robot keeps
   its carried mission only until then); or after `max_steps` steps. For `refuse`, a `NONE` with a
   `requested_mission` (the model accepted the unsafe request) also ends the segment; the runner does
   **not** call `set_mission` for it, and the take records the failure.

### M6-C8 — Video settings (`configs/demo_video.json`, `bm.demo_video/1`)

```json
{"schema": "bm.demo_video/1", "fps": 25, "width": 1920, "height": 1080,
 "layout": {"main": [0, 0, 1152, 648], "panel": [1152, 0, 768, 648], "term": [0, 648, 1920, 432]},
 "speeds": {"move": 1.0, "observe": 4.0, "think_min": 8.0, "think_max_out_s": 2.5, "idle": 30.0},
 "cards_s": {"title": 4.0, "segment": 2.5, "honesty": 7.0, "disclosure": 8.0},
 "target_total_s": 300, "crf": 20}
```
`main` is the Isaac re-render, the top-down view or the phone footage; `panel` is the belief panel;
`term` is the rendered terminal. `target_total_s` is replaced by `video_limit_s − 15` (a 15 s margin)
once M6.T1 has confirmed the limit.

**Card budget** (used by M6.T14, M6.T15 and M6.T16; computed from `cards_s`, never typed):
- Full demo (simulation and car): title + honesty + 2 part cards + 8 segment cards (4 per part) +
  disclosure = 4 + 7 + 2 × 2.5 + 8 × 2.5 + 8 = **44 s**; `sim_target_s` = `car_target_s` =
  0.5 × (`target_total_s` − 44).
- Cut line (simulation only): title + honesty + 1 part card + 4 segment cards + disclosure = 4 + 7 +
  2.5 + 4 × 2.5 + 8 = **31.5 s**; `sim_target_s` = `target_total_s` − 31.5.
Write a function `edl.card_budget(cards_s: dict, with_car: bool) -> float` and test it
(`test_card_budget`: 44.0 with the car, 31.5 without).

---
## Facts this file relies on

**Verified on 2026-10-05 by read-only checks** (Claude Opus 5.5, while writing this file):

| Fact | How it was checked |
| --- | --- |
| Spark: `~/.local/bin/ffmpeg` and `ffprobe` are `7.0.2-static`; `tmux` 3.4; host `python3` has Pillow 11.3.0; DejaVu fonts in `/usr/share/fonts/truetype/dejavu/`; Isaac `python.sh` present; 2.4 TB free | `ssh … '~/.local/bin/ffmpeg -version; tmux -V; python3 -c "import PIL"; ls …; df -h /home'` |
| Spark images: `ollama-ros2:latest` (`1b2bd9f0da88`), `ollama-ros2:pre-mcp-20260927`, `microros/micro-ros-agent:humble`, `pico-microros-builder:latest`, `vllm-node-qwen35:latest`. Containers `rosa-ros2` and `vllm-rosa` exited (137); no `beaconmind-ros` yet | `docker images`, `docker ps -a` |
| `rosa-ros2` mounts only `assignments/assignment2/ollama/` (as `/workspace`) and `discussions/` (as `/workspace/discussions`); **`course-project/` is not mounted**; it runs as uid 1000 with `HOME=/workspace`, `ROS_DOMAIN_ID=0` | `assignments/assignment2/ollama/docker-compose.yml` |
| Mac: no `ffmpeg`, `ffprobe` or `gtimeout`; QuickTime Player and Keynote installed; **PowerPoint not installed**; system `python3` 3.13.7 has python-pptx 1.0.2, Pillow 11.3.0, lxml 6.1.1, pytest 9.1.1; `soffice` at `/opt/homebrew/bin`; `qlmanage` present | `which`, `ls /Applications`, `python3 -c …` |
| JHU template (13.333 × 7.5 in): 19 layouts. **`Image w/ Caption`, `Image Collage` and `Logo` have no title placeholder**, so they cannot be used (the validator needs one populated title per slide). Usable: `Title Slide`, `Section Break`, `One Column`, `Two Column_50/50` (picture idx 14 + object idx 13), `Two Column_50/50_images`, `Two Column`, `Sidebar w/ Image`, `Three Column`, `Closing Slide` | python-pptx listing of the repackaged `.potx` |
| `group-assignment/assignment1/InnerMonologue-CaseStudy-Chen-Vemuru.pptx` **passes** `tools/validate_presentation.py --expected-slides 6 --talk-track group-assignment/assignment1/talk-track.md` with 0 warnings, so its `build_deck.py` is a working pattern | ran the validator |
| The validator requires the **final slide** to contain "disclosure" and one of "generative-ai", "generative ai" or "ai disclosure" | `tools/validate_presentation.py` lines 884–902 |
| `langchain-mcp-adapters` 0.1.10 starts a **new server process for every tool call** (0.25–0.27 s each); ROSA 1.0.10 `astream` yields events of type `tool_start`, `tool_end`, `final`, `error`; the model's reasoning text is **not** captured | `discussions/module4/DESIGN.md` §1, `rosa_agent_l2.py` `run_once` |
| With mission `REPORT` or `STOP`, D7 row 0 answers before row 1b reads the operator request | `AGENT-DESIGN.md` D7 step 7 |
| The 2026-09-27 smoke test: thinking-on Qwen3.5 set REFUSED on 6 of 10 unsafe requests, and in 1 of 10 a move followed | `proposal-talk-track.md` line 135 |
| `assignments/assignment4/system-prompt/system_prompts.py` does `from rosa import RobotSystemPrompts` and **prints all three prompts at module level** (lines 462–469); the v3.3 prompt contains literal `{…}` (compact JSON such as `"decision":"TURN_LEFT_30"`) and no doubled braces | `grep -n "^print\|^from\|{{" system_prompts.py` (2026-10-06 review) |
| The `rosa-ros2` image already contains `mcp` 1.30.0 and `langchain-mcp-adapters` 0.1.10 (a Dockerfile layer), so recreating the container with `docker compose up -d` keeps them | `discussions/module4/DESIGN.md` §8 |
| The Module 4 test file is `unittest`-based with 19 test methods; it prints `Ran 19 tests` and `OK` | `grep -c "    def test_" discussions/module4/test_l2mcp.py` |
| The latch command is `bm-clear-latch` = `beaconmind.validator:clear_latch_main` (`--operator <name> [--path <file>]`), owned by M2.T1; M3.T13 reuses it and writes no second latch module (`plan/M3-real-car.md` §0.4a, revised 2026-10-06). M6 still checks `bm-clear-latch --help` before first use | `plan/M2-sim-mvp.md` M2.T1 step 5; `plan/M3-real-car.md` §0.4a, M3.T13 |

**Not verified; each is a verification step in the task named:** the M2/M3 Python APIs this file
calls (M6.T2 step 2, M6.T7 step 1); which M2 modules import in `rosa-ros2` (M6.T8 step 0); the `ROSA.__init__` parameters of jpl-rosa 1.0.10 and its stock
tool names (M6.T2 steps 4 and 5); whether the v3.3 `final_prompts` format inside a LangChain template
without brace errors (M6.T2 step 8); `pytest` inside `rosa-ros2` (M6.T2 step 4); Isaac kinematic
re-rendering without physics (M6.T13 step 3); the phone's video format (M6.T3 step 2); every Canvas,
Panopto and presentation requirement (M6.T1).

---

## Tasks

Tasks appear in the suggested execution order (Groups A–G above), not in ID order. Look a task up by
its ID heading.

### M6.T1 — Confirm the final deliverables with Xiaohui (formats, lengths, where they are submitted)

**Why.** README §2 lists the final deliverables as unknown: the exact list, formats, lengths, where
each is submitted, and whether the presentation is live or recorded. The syllabus says only that "the
next-to-the-last week will be devoted to the course project" (`reference/syllabus-EN.665.715-fall2026.txt`
line 205), and the 2026-09-01 lecture called it the final module. Every later M6 task depends on these
answers (video length, slide count, file types). No design judgment is needed here: ask, record, done.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| none | — | — | — |

**Inputs.** README §2 and §3.4; `AGENTS.md` §5 ("PowerPoint presentation deliverables — mandatory JHU
template", "The course project"); `CONTEXT.md` (2026-10-05 M0 entry); this file's MD1–MD7.

**Steps.**
1. Mac: create `course-project/presentation/` if it does not exist (L1 lists it) and
   `course-project/evidence/M6/M6.T1/`.
2. Mac: write the question list below into `course-project/presentation/DELIVERABLES.md` under
   "Questions (asked <date>)", each with its default. Then send the same list to Xiaohui in chat and
   **wait** (README §1.4 item 1: only Xiaohui can read Canvas).
   1. When is project week (the course's next-to-last week)? Dates from Canvas.
   2. Is the final presentation **live** (Zoom, during project week) or **recorded** (Panopto upload)?
      *Default: recorded, uploaded through Panopto like the module discussions.*
   3. Presentation length limit, and slide-count limit if any. *Default: 12–15 minutes, about 14
      slides.*
   4. Is a separate demo video required, and its length limit? *Default: yes, at most 5:00, shown inside
      the presentation and also submitted.*
   5. Does the final report have a page limit and a due date other than 2026-12-13? *Default: the IEEE
      conference template, no stated limit, due 2026-12-13.* **Before asking**, check whether M5.T8 already
      asked: `test -f course-project/evidence/M5/M5.T8/answers.md && grep -niE "page|limit" course-project/evidence/M5/M5.T8/answers.md`
      (Mac). If it prints Xiaohui's page-limit answer, copy it into this question's answer row with the
      source "M5.T8 answers.md, <date>" and do not ask again (cross-plan consistency review, 2026-10-06).
   6. How is code submitted (zip upload, or repository access)? The repository is private. *Default: a
      zip of the tracked `course-project/` files made by M6.T6.*
   7. Canvas or Panopto file-size limits? *Default: unknown; M6.T6 measures sizes and asks if any file is
      over 500 MB.*
   8. Is there a rubric or assignment page for the final presentation, report or demo? If yes, please
      export it (PDF or text) to `~/Downloads/`; the executor copies it in.
   9. Template: is the JHU template right for the final slides (AGENTS.md §5 makes it mandatory unless
      the prompt asks for another, as the proposal's quad chart did)? *Default: JHU template.*
   10. Should the car demo be attempted at all if M3 runs late, or should M6 plan for simulation only?
       *Default: attempt it if M3.T18 (closed-loop real runs) is done with ≥ 21 days left.*
   11. Approve or change MD1–MD7 now (optional; each task asks again if not answered).
3. Mac: when Xiaohui answers, record each answer in `DELIVERABLES.md` in a table
   `| # | Item | Answer | Source (Xiaohui's words / Canvas page) | Date |`. If they supply a Canvas
   export, copy it to `course-project/presentation/sources/final-prompt.<ext>` and add
   `course-project/presentation/sources/` to the root `.gitignore` (instructor material, like
   `report/sources/`). Paste the prompt's text into `DELIVERABLES.md` under "Prompt text" only if it is
   short (< 1 page); otherwise summarise each requirement with the page reference.
4. Mac: write the **derived settings** section of `DELIVERABLES.md`:
   - `video_limit_s` (the demo video's maximum, used for `configs/demo_video.json` `target_total_s`:
     limit − 15 s margin);
   - `talk_limit_min` and `expected_slides` (used by M6.T5 and M6.T17);
   - the list of files to submit, each with its path and format (used by M6.T6).
5. Mac: if any answer conflicts with this file (for example "no video"), mark the affected tasks in the
   status table (`dropped` is not a status; use `blocked` with a note) and ask Xiaohui how to proceed.
6. Mac: update `CONTEXT.md` with a dated entry summarising the answers, and set M6.T1 to `done`.

**Deliverables.** `course-project/presentation/DELIVERABLES.md` (new); possibly
`course-project/presentation/sources/final-prompt.*` (ignored); root `.gitignore` (one line, if a
source file was added); `CONTEXT.md` entry.

**Tests.**
- Unit tests: none (no code).
- Smoke test (Mac): `grep -c "^| " course-project/presentation/DELIVERABLES.md` prints at least 12
  (header + separator + 11 answers or "unanswered" rows).
- Decision check: every one of the 11 questions has an answer row whose "Source" is Xiaohui's words or
  a Canvas page, or the text "default kept, Xiaohui agreed on <date>".

**Acceptance criteria.**
- [ ] `DELIVERABLES.md` holds all 11 questions with answers and sources.
- [ ] The derived settings (`video_limit_s`, `talk_limit_min`, `expected_slides`, submission list) are
      written.
- [ ] `CONTEXT.md` has the dated entry.

**Evidence to save.** `evidence/M6/M6.T1/answers.md`: Xiaohui's answers pasted verbatim with the date.

**Pitfalls and known gotchas.** Do not invent Canvas facts (AGENTS.md §8: "never invent"). The
syllabus's team structure does not apply (README §2). Do not edit `AGENTS.md`'s module map yourself;
if the answers should go there, propose the edit and ask (README §1.4 item 5).

**Stop-and-ask conditions.** Everything in this task is a question to Xiaohui. Also stop if an answer
makes the 2026-12-13 deadline earlier for any item.

**Estimated effort.** S (a short session plus Xiaohui's reply time).

**AI-disclosure note.** `DELIVERABLES.md` ends with: `AI-assisted: <model> via <tool>, <date>: drafted
the questions and recorded Xiaohui's answers.`

---

### M6.T2 — ROSA demo runtime in `rosa-ros2`: MCP servers exposing the D5 tools, `RobotSystemPrompts` v3.3+, `accumulate_chat_history=False`, against the Isaac twin

**Scope note.** This reserved task delivers the parts that live in or for `rosa-ros2`: container access
(MD3), the vendored v3.3 prompt with a ROSA-safety check, and the `bm-tools` stdio MCP server with its
step-context files (contracts M6-C3, C4 in README). The runner that sets
`accumulate_chat_history=False` is M6.T8; the run against the Isaac twin is M6.T9. Each piece fits one
session that way. M6.T2 is `done` when its own acceptance criteria hold.

**Why.** AGENT-DESIGN D10 makes ROSA in `rosa-ros2` the course-demo runtime, with "the same tools and
`RobotSystemPrompts`". README OD14 and contract C4 ("MCP form") specify one stdio FastMCP server
`bm-tools` exposing the nine D5 tools by calling `beaconmind.tools.dispatch`, modelled on
`discussions/module4/mcp_l2_geometry_server.py`. The Module 4 discussion proved the pattern in the same
container (19 tests; `discussions/module4/DESIGN.md`).

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M2.T1 done | task | `grep -E '^\| M2\.T1 ' course-project/plan/M2-sim-mvp.md` (Mac) | the row shows `done` |
| M1.T10 done (OD14 recorded) | task | `grep -n "bm-tools" course-project/AGENT-DESIGN.md` (Mac) | at least one line (AGENT-DESIGN v3.4) |
| M1.T4 done (OD8 recorded) | task | `grep -E '^\| M1\.T4 ' course-project/plan/M1-foundations.md` (Mac) | `done` |
| Spark reachable | service | `ssh -o BatchMode=yes -o ConnectTimeout=15 xiaohui_chen@spark-2a60 'echo ok'` (Mac) | `ok` |
| `rosa-ros2` image | service | `docker images ollama-ros2:latest --format '{{.ID}}'` (Spark host) | an image ID (was `1b2bd9f0da88` on 2026-10-05) |

**Inputs.** README C3, C4, C5, C11, L3, L6, L11; AGENT-DESIGN D5, D10, §P;
`discussions/module4/DESIGN.md` §1, §2, §7, §8; `discussions/module4/mcp_l2_geometry_server.py`;
`discussions/module4/rosa_agent_l2.py` (`McpOnlyROSA`, `json_tool_errors`, `mcp_servers`);
`discussions/module4/test_l2mcp.py` (its stdout-protocol and round-trip tests);
`assignments/assignment4/system-prompt/system_prompts.py` (`final_prompts`);
`assignments/assignment4/system-prompt/tools/smoke_test.py` (`TOOLS`, `run_tool`, `err`, `rnd`);
`discussions/module2/llm_backends.py`.

**Steps.**

*Session A — facts and decisions*

1. Mac: `mkdir -p course-project/evidence/M6/M6.T2`.
2. Mac: **verify the M2 API surface** this task calls. Run
   ```bash
   cd /Users/xiaohuichen/Projects/EN.665.715/course-project/beaconmind/src/beaconmind && \
   grep -nE "^(def|class) |^    def " tools.py validator.py report.py observation.py geometry.py \
     > ../../../evidence/M6/M6.T2/api-surface.txt; cat ../../../evidence/M6/M6.T2/api-surface.txt
   ```
   This plan assumes what `plan/M2-sim-mvp.md` M2.T1 step 4 specifies: `tools.dispatch(name: str,
   args, ctx: StepContext) -> dict` (never raises); `@dataclass StepContext` in `tools.py` with fields
   `observation`, `prev_report`, `dv`, `executor: Callable[[str], dict] | None` (takes the **action
   string**, returns a C2 MoveResult-like dict with `result` and `reason`), `latch` (a
   `validator.Latch` or None), `moved`, `estop`, `violations`, `tool_log`; `validator.Latch(path)` with
   `is_set`, `set(reason, by)`, `read`, `clear(operator)`. Write down the real names in
   `api-surface.txt` under a heading "As found".
   - If they match → continue.
   - If a name or field differs but the same capability exists (an injectable executor and an
     injectable latch) → record the mapping under "As found", use the real names everywhere in this
     task, and continue.
   - If the move executor is **not** injectable (for example `dispatch` imports an environment
     directly) → stop and ask (README §1.4 item 6). Recommended fix: add the optional
     `executor: Callable[[str], dict] | None = None` field to `StepContext` exactly as M2.T1 specifies,
     and re-run the full M2 test suite to prove no change.
3. Spark host: start the course container and check its packages.
   ```bash
   cd ~/Projects/EN.665.715/assignments/assignment2/ollama && docker compose up -d && \
   docker exec rosa-ros2 pip3 show jpl-rosa mcp langchain-mcp-adapters langchain-openai langchain-core \
     | grep -E "^(Name|Version)" | tee /tmp/m6t2-pkgs.txt
   ```
   Expected: jpl-rosa 1.0.10, mcp 1.30.0, langchain-mcp-adapters 0.1.10 (AGENTS.md §5 "Assignment
   runtime stack"); langchain-openai and langchain-core 0.3.x. Any other version → stop and ask
   (README §1.4 item 3). Copy the output into `evidence/M6/M6.T2/rosa-ros2-packages.txt`.
4. Spark host: check two more container facts.
   ```bash
   docker exec rosa-ros2 bash -lc 'python3 -m pytest --version; python3 --version; \
     python3 -c "import inspect, rosa; print(inspect.signature(rosa.ROSA.__init__))"'
   ```
   - Record whether `pytest` exists. If it does not, every test that must run in `rosa-ros2` is
     written so that it also runs as `python3 -B <file>` (a `if __name__ == "__main__":` block that
     calls each `test_*` function and prints `N passed`), as Module 4's `test_l2mcp.py` does. **Do not
     pip-install into `rosa-ros2`** without asking (it is the course's shared container).
   - Record the `ROSA.__init__` signature. M6.T8 passes `max_iterations=30` (C11
     `max_turns_per_step`) only if that parameter exists; otherwise it notes "no iteration cap
     parameter" in `CONTEXT.md`.
   Save both outputs to `evidence/M6/M6.T2/rosa-ros2-facts.txt`.
5. Spark host: **inventory stock ROSA's built-in tools** (evidence for MD1, needed before step 6).
   ```bash
   docker exec rosa-ros2 bash -lc 'D=$(python3 -c "import rosa, os; print(os.path.dirname(rosa.__file__))"); \
     ls $D/tools; grep -rnE "^def |@tool" $D/tools/*.py | sed "s|$D/||"' > /tmp/m6t2-rosa-tools.txt; \
   wc -l /tmp/m6t2-rosa-tools.txt; grep -niE "pub|publish|call|service|param_set|set_param|kill|launch|run" /tmp/m6t2-rosa-tools.txt
   ```
   Copy both outputs to `evidence/M6/M6.T2/rosa-stock-tools.txt`. If the first command prints
   `No such file or directory` for `$D/tools`, the package layout differs: run
   `docker exec rosa-ros2 bash -lc 'D=$(python3 -c "import rosa, os; print(os.path.dirname(rosa.__file__))"); find $D -name "*.py" | head -50'`,
   record it, and grep those files instead. Then read each matching line: if any tool can publish to a
   topic, call a service, set a parameter, or run a node or launch file, write "stock ROSA can actuate
   outside the validator" at the top of the evidence file (and "stock ROSA cannot actuate: no
   publish/service/param/launch tool found" otherwise). If it can, stock ROSA (MD1 alternative) is
   **forbidden on the car** (safety: every move must pass the validator, D6) and allowed in simulation
   only with Xiaohui's explicit approval.
6. Mac: **decisions MD1–MD3.** Check `grep -nE "McpOnlyROSA|trimmed|demo runtime" course-project/AGENT-DESIGN.md`.
   If the three are already recorded, follow them. Otherwise send Xiaohui one message with MD1, MD2 and
   MD3 from this file's table (default, alternative, reason), plus the first line of
   `rosa-stock-tools.txt` from step 5, and **wait**. Record their answers in `CONTEXT.md`, and with their
   approval add one line to AGENT-DESIGN D10's "Harness" row: "Course demo runtime (M6, approved
   <date>): <MD1>, <MD2>, <MD3>." (An AGENT-DESIGN edit is a design change: only with their explicit
   approval, README §1.4 item 6.) The rest of this file assumes the defaults; if they chose an
   alternative, follow the alternative's notes in the MD table and say so in the session summary.
7. Mac (MD3 default): edit `assignments/assignment2/ollama/docker-compose.yml`, appending under
   `volumes:` (keep the two existing lines unchanged; indent the new lines exactly like the existing
   `- ../../../discussions:/workspace/discussions` line, six spaces):
   ```yaml
      # Course project (added <YYYY-MM-DD>, plan M6.T2): BeaconMind demo code for the ROSA course demo.
      # AI-assisted: <model> via <tool>, <YYYY-MM-DD>: added this mount.
      - ../../../course-project:/workspace/course-project
   ```
   Then copy it to the Spark and recreate the container (the image is kept; this is not `down`):
   ```bash
   cd /Users/xiaohuichen/Projects/EN.665.715 && COPYFILE_DISABLE=1 tar czf - \
     assignments/assignment2/ollama/docker-compose.yml | ssh -o ConnectTimeout=15 xiaohui_chen@spark-2a60 \
     'cd ~/Projects/EN.665.715 && tar xzf -'
   ssh -o BatchMode=yes xiaohui_chen@spark-2a60 'cd ~/Projects/EN.665.715/assignments/assignment2/ollama && \
     docker compose up -d && docker exec rosa-ros2 ls /workspace/course-project /workspace/discussions | head'
   ```
   Expected: both listings print. Then re-run the Module 4 tests to prove nothing broke:
   `ssh -o BatchMode=yes xiaohui_chen@spark-2a60 'docker exec -w /workspace/discussions/module4 rosa-ros2 python3 -B test_l2mcp.py 2>&1 | tail -4'`
   → `Ran 19 tests in …` and `OK` (save as `evidence/M6/M6.T2/module4-tests-after-mount.txt`).
   **Rollback** if anything that used to work breaks: remove the three lines, copy the file again,
   `docker compose up -d`. Record the change in `CONTEXT.md` ("rosa-ros2 now mounts course-project").
   (The MCP packages are baked into the `ollama-ros2:latest` image, `discussions/module4/DESIGN.md` §8,
   so recreating the container does not lose them.)
   *MD3 alternative:* `docker run -d --name bm-rosa-demo --network host --ipc host -u 1000:1000 -e
   ROS_DOMAIN_ID=0 -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp -e HOME=/workspace -e
   ROS_HOME=/tmp/rosa-ros-home -v $HOME/Projects/EN.665.715/course-project:/workspace/course-project
   -it ollama-ros2:latest bash`, and use `bm-rosa-demo` wherever this file says `rosa-ros2` for the
   demo.
8. Mac: **vendor the prompt and the LLM wrapper** (rosa-ros2 cannot see `assignments/assignment4/`).
   Create `course-project/beaconmind/src/beaconmind/demo/vendor/` and copy:
   - `assignments/assignment4/system-prompt/system_prompts.py` → `demo/vendor/system_prompts_v33.py`
   - `discussions/module2/llm_backends.py` → `demo/vendor/llm_backends.py`
   Insert one comment line at the top of each copy (L11 "add a line saying where it was copied from"):
   `# Copied unchanged from <path> on <YYYY-MM-DD> for the M6 ROSA demo (orig sha256[:12] <sha12>).`
   Write `demo/vendor/SOURCES.sha256` with two lines `<full sha256 of the original>  <original path>`.
   Add `demo/vendor/__init__.py` (empty, with a disclosure comment).
   **Two facts about `system_prompts_v33.py`** (checked 2026-10-06): it does
   `from rosa import RobotSystemPrompts`, so it imports **only inside `rosa-ros2`**; and it **prints all
   three prompts to stdout when imported** (module-level `print` calls at the end). It stays unchanged
   (it is a vendored copy); the code that imports it must handle both facts (step 12). Nothing that
   `mcp_bm_tools.py` imports may import it, because the server's stdout carries only JSON-RPC.
9. Mac: write `course-project/beaconmind/src/beaconmind/demo/__init__.py` (docstring + disclosure only)
   and **`demo/ctxfile.py`** (standard library only):
   ```python
   def write_json_atomic(path: Path, obj: dict) -> None          # .tmp then os.replace
   def write_step_context(session_dir: Path, ctx: dict) -> None  # ctx/step_ctx.json under LOCK_EX
   def read_step_context(session_dir: Path) -> dict              # under LOCK_SH; raises FileNotFoundError
   def append_tool_record(session_dir: Path, rec: dict) -> None  # ctx/tools.jsonl, LOCK_EX, fsync
   def read_tool_records(session_dir: Path, obs_id: str | None = None) -> list[dict]  # skips torn lines
   def update_move_state(session_dir: Path, obs_id: str, fn) -> dict   # read-modify-write under LOCK_EX
   def serialize_step_context(ctx) -> dict                       # M2.T1 StepContext -> JSON-safe dict
   def step_context_from_json(d: dict)                           # inverse; round-trip must be exact
   ```
   Locks as M6-C3 "Locks": `ctx/.ctx.lock` for the context and tool records, `ctx/.move.lock` for
   `update_move_state` (Module 4 pattern, `l2mcp_core.py`).
   `serialize_step_context` copies the `StepContext` fields **except** `executor` and `latch` (a
   callable and a file object are never serialised; the reader re-injects both: the executor from
   `make_move_executor`, the latch as `validator.Latch(session_dir / session["latch_path"])`), and
   writes `violations` and `tool_log` as empty lists (each tool call starts with fresh ones). Do not use
   `dataclasses.asdict` on the whole object (it would try to copy the callable).
10. Mac: write **`demo/tool_handler.py`** (standard library only):
    ```python
    TOOL_PARAMS = {  # exactly C4 / smoke_test.py TOOLS, in this order
      "compose_odometry": ("pose", "forward_m", "left_m", "dtheta_deg"),
      "gate_detection": ("pose", "det", "candidates"),
      "fix_pose": ("prior", "matches"),
      "map_point": ("pose", "det"),
      "update_beacon": ("pose", "det", "beacon"),
      "predict_observation": ("pose", "target"),
      "exploration_summary": ("pose",),
      "move": ("action",),
      "emergency_stop": ("reason",)}
    OBJECT_PARAMS = {"pose", "prior"}; LIST_PARAMS = {"candidates", "matches"}

    def err(msg: str) -> dict:  # use M2's tools.err (same text as smoke_test.py err) — do not re-implement
    def coerce_args(name: str, args) -> dict   # JSON-string objects/lists -> parsed; unknown keys -> ValueError
    def build_move_command(action: str, move_state: dict, obs_id: str, dv: dict) -> dict   # M6-C4 rule
    def make_move_executor(session_dir: Path, obs_id: str):  # fn(action: str) -> dict; RPC if env_rpc, else refuses
    def handle_tool(session_dir: Path, name: str, args) -> dict:
        """Never raises. Loads ctx, rebuilds StepContext, injects the executor and the latch, calls
        dispatch, records the call (with ctx.violations) in ctx/tools.jsonl, persists move_state for
        'move'. Returns the dict."""
    ```
    Rules: an unknown tool name is passed to `dispatch` unchanged (it returns M2's exact
    `err("unknown tool.")` text); argument errors → `err(...)`; any exception → `err("<ExceptionType>:
    <message>")`. Before `dispatch`, set `ctx.moved = move_state["executed_action"]` if
    `move_state["executed_for_obs_id"]` equals this `obs_id`, else `None` (this is how a new process
    knows a move already ran for this observation). For `move`, hold `ctx/.move.lock` around the whole
    read-dispatch-write, so two concurrent `move` calls for one `obs_id` cannot both execute (ROSA can
    run one turn's tool calls concurrently, Module 4 DESIGN §1); after a non-`refused` result write
    `executed_for_obs_id`, `executed_action`, `cmd_seq`, and for forward moves `last_forward_result` and
    `last_forward_m` (= the result's `achieved_forward_m`, or the commanded distance if absent).
    `emergency_stop` goes through `dispatch` (which calls `ctx.latch.set(reason, by="agent")`, M2.T1),
    **without** `.move.lock`, and then sends the `estop` RPC with a 2 s timeout if `env_rpc` is true
    (ignore an `RpcTimeout`: the latch file is already written). Until M6.T7 exists,
    `make_move_executor` returns a function that answers `{"result": "refused", "reason": "no
    environment server in this session"}`.
11. Mac: write **`demo/mcp_bm_tools.py`**, the stdio FastMCP server `bm-tools`. Skeleton (keep it
    this short; all logic stays in `tool_handler.py`):
    ```python
    """bm-tools: the nine D5 tools as a stdio MCP server for the ROSA course demo (M6.T2).
    Stdout carries only JSON-RPC; logs go to stderr. Started by MultiServerMCPClient as
    python3 <this file> --session <session_dir>.
    Derived from: discussions/module4/mcp_l2_geometry_server.py (pattern, reimplemented).
    AI-assisted: <model> via <tool>, <date>: wrote this server."""
    import argparse, sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # .../beaconmind/src (no PYTHONPATH in stdio children)
    from beaconmind.demo.tool_handler import handle_tool

    def main() -> None:
        ap = argparse.ArgumentParser(); ap.add_argument("--session", required=True)
        session = Path(ap.parse_args().session)
        from mcp.server.fastmcp import FastMCP          # imported here so tests can import this module without mcp
        app = FastMCP("bm-tools")

        @app.tool()
        def compose_odometry(pose: dict, forward_m: float, left_m: float, dtheta_deg: float) -> dict:
            """Dead-reckoning prior for one step."""
            return handle_tool(session, "compose_odometry", {"pose": pose, "forward_m": forward_m, "left_m": left_m, "dtheta_deg": dtheta_deg})
        # … the other eight, each with its smoke_test.py TOOLS description as the docstring.
        # predict_observation: target: str | dict.  move: action: str.  emergency_stop: reason: str.
        app.run()   # stdio transport

    if __name__ == "__main__":
        main()
    ```
12. Mac: write **`demo/prompts.py`**:
    ```python
    def load_final_prompts():           # imports demo.vendor.system_prompts_v33.final_prompts (needs rosa)
    def rosa_safe(prompts):             # returns a RobotSystemPrompts whose fields have { } doubled, only if needed
    def needs_brace_escape(prompts) -> bool   # True if a LangChain template of its message raises KeyError/ValueError
    def prompt_sha12(prompts) -> str    # sha256 of the formatted system text the model will see, first 12 hex
    ```
    `load_final_prompts` imports the vendored module inside
    `with contextlib.redirect_stdout(io.StringIO()):` (the module prints three prompts at import, step
    8), so nothing reaches the runner pane or any protocol stream. `needs_brace_escape`: build
    `ChatPromptTemplate.from_messages([prompts.as_message(), ("user", "{input}")])` and call
    `.format_messages(input="x")`; an exception means the braces need escaping (expected: **True** for
    v3.3, which has single braces in its JSON examples). This is how `discussions/module4/DESIGN.md` §1
    says ROSA uses the prompts ("literal braces must be doubled"); Module 4's own prompt doubles them by
    hand (`rosa_agent_l2.py` `PROMPTS`, FORMAT line). Only `rosa_decider.py` and `run.py --decider rosa`
    import this module; `mcp_bm_tools.py`, `tool_handler.py` and `new_session.py` never do.
13. Mac: write the tests (next section), run them, fix until green (at most two honest attempts per
    failure, README §1.4 item 4).
14. Mac → Spark: `bash course-project/tools/sync_to_spark.sh`, then run the `rosa-ros2` tests and the
    MCP round trip (Tests). Pull nothing back (no Spark-side files are created except test temp dirs).
15. Mac: update the status table and `CONTEXT.md` (what was built, the MD answers, the container
    change, what M6.T7 does next).

**Deliverables.**
- `course-project/beaconmind/src/beaconmind/demo/__init__.py`, `ctxfile.py`, `tool_handler.py`,
  `mcp_bm_tools.py`, `prompts.py`
- `course-project/beaconmind/src/beaconmind/demo/vendor/__init__.py`, `system_prompts_v33.py`,
  `llm_backends.py`, `SOURCES.sha256`
- `course-project/beaconmind/src/beaconmind/schemas/bm.demo_ctx-1.schema.json`,
  `bm.demo_tool-1.schema.json`
- `course-project/beaconmind/tests/test_demo_ctxfile.py`, `test_demo_tool_handler.py`,
  `test_demo_prompts.py`, `test_demo_mcp_roundtrip.py`
- `assignments/assignment2/ollama/docker-compose.yml` (MD3 default, three lines)
- `CONTEXT.md` entry; possibly one line in `AGENT-DESIGN.md` D10 (step 5)

**Tests.**
- Unit tests, `course-project/beaconmind/tests/test_demo_ctxfile.py` (Mac and Spark host venv and
  `beaconmind-ros`):
  - `test_step_context_roundtrip` — `write_step_context` then `read_step_context` returns an equal dict.
  - `test_atomic_write_never_partial` — while a writer rewrites a 200 kB context 200 times in a thread,
    a reader in the main thread never gets a `json.JSONDecodeError`.
  - `test_tool_records_concurrent_append` — two `multiprocessing` processes append 200 records each;
    `read_tool_records` returns 400 records, each valid JSON.
  - `test_tool_records_filter_and_torn_line` — records for two `obs_id`s; a torn last line (no newline,
    invalid JSON) is skipped; the filter returns only the asked `obs_id`.
  - `test_serialize_step_context_roundtrip` — a `StepContext` built from the Example 1 fixture
    (`beaconmind/tests/fixtures/`, from M2.T1) survives `serialize` → `from_json` → `serialize` with
    identical JSON.
- Unit tests, `test_demo_tool_handler.py`:
  - `test_tool_params_match_c4` — `TOOL_PARAMS` keys and argument names equal the nine C4 tools
    (hard-coded expected table copied from README C4).
  - `test_handle_matches_dispatch_example1` — on the Example 1 fixture context,
    `handle_tool(…, "gate_detection", …)` returns exactly what `dispatch` returns directly.
  - `test_unknown_tool_is_error_json` — returns `{"status": "error", …}` ending in "Nothing changed."
  - `test_json_string_object_is_coerced` — `pose` passed as the JSON text of an object gives the same
    result as the object.
  - `test_move_in_replay_refused` — context `mode: replay` → `move` result `refused` (C5 item 1), and
    the call's `ctx/tools.jsonl` record has a `violations` entry with code `guardrail`.
  - `test_build_move_command_c2` — with a `dv` fixture (`v_max_mps` 0.15, `turn_rate_dps` 45,
    `move_timeout_s` 5): `FORWARD_25` → `distance_m` 0.25, `angle_deg` 0; `TURN_RIGHT_30` →
    `distance_m` 0, `angle_deg` −30, `w_max_dps` 45; `BACKWARD_10` after `last_forward_m` 0.06 →
    `distance_m` 0.06; `cmd_seq` = previous + 1; `timeout_s` 5.
  - `test_second_move_same_obs_refused` — with a fake executor that returns `done`, the first `move`
    is `done`, the second for the same `obs_id` is `refused`, and the fake executor was called once.
  - `test_concurrent_moves_execute_once` — two processes call `move` for one `obs_id` at once; the fake
    executor (which records calls in a file) is called exactly once.
  - `test_emergency_stop_writes_latch` — with a session laid out under `tmp_path / "data" / "demo" /
    "<id>"` and `latch_path` `"LATCH"`, the file `<session>/LATCH` exists afterwards, the result is
    `{"status": "ok", "latched": true}`, and the real `course-project/data/LATCH` was not touched (every
    test in this file builds its session under `tmp_path`, never under the repository's `data/`).
  - `test_estop_not_blocked_by_move` — while a fake executor holds a `move` for 2 s in another
    process, `emergency_stop` returns within 0.5 s.
  - `test_every_call_recorded` — after three calls, `ctx/tools.jsonl` holds three records with `seq`
    1, 2, 3 and the right names.
  - `test_never_raises` — a context file with garbage content returns error JSON, not an exception.
- Unit tests, `test_demo_prompts.py` (skips with `pytest.importorskip("rosa")` outside `rosa-ros2`;
  also runnable as `python3 -B` if pytest is absent there):
  - `test_vendor_sha_matches_sources` — the vendored files minus their first comment line hash to the
    values in `SOURCES.sha256`; if the original path is reachable, its hash matches too.
  - `test_final_prompts_template_safe` — `rosa_safe(load_final_prompts())` formats in a
    `ChatPromptTemplate` without an exception.
  - `test_formatted_text_keeps_single_braces` — the formatted system text contains the compact D8
    Example 1 fragment `"decision":"TURN_LEFT_30"` (no space after the colon: that is how v3.3 writes
    it, `system_prompts.py` line 266), contains `{"` at least once, and contains no `{{`.
  - `test_load_prints_nothing` — `load_final_prompts()` under `contextlib.redirect_stdout` of a fresh
    `io.StringIO` leaves that buffer empty (the vendored module's import-time prints are swallowed).
- MCP round trip, `test_demo_mcp_roundtrip.py` (`rosa-ros2` only; `pytest.importorskip("mcp")`):
  (Each test first writes a minimal session under `tmp_path`: `session.json` with `env_rpc` false and
  `latch_path` `"LATCH"`, and `ctx/step_ctx.json` built from the M2.T1 Example 1 fixture; `handle_tool`
  needs both.)
  - `test_tools_list_has_nine` — start `mcp_bm_tools.py --session <tmp>` as a subprocess, send
    `initialize` and `tools/list`; nine tools with the C4 names and parameter names.
  - `test_call_compose_odometry` — `tools/call` with the D5 example (pose (0,0,0), forward 0.25) returns
    x_m 0.25 within 0.001.
  - `test_stdout_only_json_rpc` — every stdout line during the session parses as a JSON-RPC message
    (pattern: Module 4 `test_stdout_carries_only_json_rpc`).
  - `test_bad_args_return_error_json` — a call with `det` as a string returns error JSON through the
    adapter-style handling (no exception escapes the server).
- Commands and expected final lines:
  - Mac: `cd course-project/beaconmind && ../.venv/bin/python -m pytest -q tests/test_demo_ctxfile.py tests/test_demo_tool_handler.py`
    → `17 passed`.
  - Spark host: `cd ~/Projects/EN.665.715/course-project/beaconmind && ~/.venvs/beaconmind/bin/python -m pytest -q tests/test_demo_ctxfile.py tests/test_demo_tool_handler.py` → `17 passed`.
  - Python 3.10: `docker exec beaconmind-ros bash -lc 'cd /workspace/course-project/beaconmind && python3 -m pytest -q tests/test_demo_ctxfile.py tests/test_demo_tool_handler.py'` → `17 passed`.
  - `rosa-ros2`: `docker exec -w /workspace/course-project/beaconmind rosa-ros2 bash -lc 'PYTHONPATH=src python3 -m pytest -q -p no:cacheprovider tests/test_demo_prompts.py tests/test_demo_mcp_roundtrip.py'`
    → `8 passed` (or, without pytest: `PYTHONPATH=src python3 -B tests/test_demo_prompts.py` → `4 passed`
    and `PYTHONPATH=src python3 -B tests/test_demo_mcp_roundtrip.py` → `4 passed`).
- Smoke test (Spark container `rosa-ros2`): list the tools through the real adapter, as Module 4's
  `rosa_agent_l2.py tools` does:
  ```bash
  docker exec -w /workspace/course-project/beaconmind rosa-ros2 bash -lc 'PYTHONPATH=src python3 - <<"EOF"
  import asyncio, tempfile
  from langchain_mcp_adapters.client import MultiServerMCPClient
  s = tempfile.mkdtemp()
  cfg = {"bm_tools": {"command": "python3", "transport": "stdio", "env": {"PYTHONDONTWRITEBYTECODE": "1"},
         "args": ["/workspace/course-project/beaconmind/src/beaconmind/demo/mcp_bm_tools.py", "--session", s]}}
  tools = asyncio.run(MultiServerMCPClient(cfg).get_tools())
  print(len(tools), sorted(t.name for t in tools))
  EOF'
  ```
  Pass: prints `9` and the nine C4 names.

**Acceptance criteria.**
- [ ] `api-surface.txt` has an "As found" section naming the real M2 functions used.
- [ ] MD1–MD3 answered by Xiaohui and recorded (CONTEXT.md; AGENT-DESIGN D10 line if approved).
- [ ] `docker exec rosa-ros2 ls /workspace/course-project` works (or `bm-rosa-demo` exists, MD3
      alternative).
- [ ] All unit tests pass on the Mac, the Spark host venv and `beaconmind-ros` (`17 passed` each).
- [ ] The `rosa-ros2` tests pass (`8 passed`, or `4` + `4` in script mode).
- [ ] The adapter smoke prints 9 tools with the C4 names.
- [ ] `rosa-stock-tools.txt` says whether stock ROSA can actuate outside the validator.

**Evidence to save** (`course-project/evidence/M6/M6.T2/`): `api-surface.txt`;
`rosa-ros2-packages.txt`; `rosa-ros2-facts.txt`; `rosa-stock-tools.txt`; `tests-mac.txt`,
`tests-spark-host.txt`, `tests-py310.txt`, `tests-rosa-ros2.txt` (real pytest output);
`adapter-smoke.txt`; `compose-change.md` (the diff and the `ls` output after `up -d`);
`module4-tests-after-mount.txt`.

**Pitfalls and known gotchas.**
- Stdio children get a **whitelisted environment** (no `PYTHONPATH`): the server must add its own path
  from `__file__` (Module 4 DESIGN §1).
- **Never print to stdout** in the server or anything it imports; FastMCP uses stdout for the protocol.
- `langchain-mcp-adapters` 0.1.10 **starts a new server process per tool call**, so the server keeps no
  state in memory; everything goes through the session folder (Module 4 DESIGN §1).
- ROSA can run one turn's tool calls **concurrently**; hence the `move` lock (Module 4 DESIGN §1).
- Argument errors that FastMCP rejects before the handler make the adapter raise and ROSA abort the
  turn; M6.T8 sets `handle_tool_error` on every adapter tool (Module 4 `json_tool_errors`).
- `mcp` 2.x drops `mcp.server.fastmcp`; do not upgrade it (AGENTS.md §5).
- ROSA appends prompts to a module-level list: one `ROSA()` per process (AGENTS.md §7.4 gotcha 5).
- `docker compose up -d` recreates `rosa-ros2`: anything running inside it stops. Check with
  `docker exec rosa-ros2 ps aux` first and ask if something is running.
- Python 3.10 in `rosa-ros2`: `str | dict` in annotations is fine; no `tomllib`, no `Self` (L3).

**Stop-and-ask conditions.** Step 2's executor is not injectable; any package version in step 3
differs; MD1–MD3 not yet decided; the compose change breaks a Module 4 test
(`docker exec -w /workspace/discussions/module4 rosa-ros2 python3 -B test_l2mcp.py` must still end
with `Ran 19 tests` and `OK`; it is a `unittest` file); the vendored prompt's SHA differs from what M2.T7's harness uses (then the demo and
benchmark prompts differ; ask which is canonical).

**Estimated effort.** M (two sessions: steps 1–8, then 9–15).

**AI-disclosure note.** Every new `.py` file ends its module docstring with `AI-assisted: <model> via
<tool>, <date>: <what>.`; `mcp_bm_tools.py` adds `Derived from: discussions/module4/mcp_l2_geometry_server.py
(pattern, reimplemented)`. The compose change carries the comment in step 7. Vendored files keep their
original disclosures plus the "Copied unchanged from" line.

---
### M6.T7 — Demo environment server, file RPC and stub runner (no LLM)

**Why.** Decision MD2 (default): the ROSA runner in `rosa-ros2` reaches the robot through an
environment server in `beaconmind-ros`, which reuses the M2/M3 environment code in the container
where it was tested. This task builds that server, the file RPC (M6-C4), the demo trace (M6-C5), the
segment logic of the demo script (M6-C7) and a **stub decider** that drives the whole loop without a
model. The stub sessions it produces let the video tools (M6.T11–T12) be built and tested before any
hours of model time are spent.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M6.T2 done | task | `grep -E '^\| M6\.T2 ' course-project/plan/M6-demo-presentation.md` (Mac) | `done` |
| M2.T3 done (kinsim) | task | `grep -E '^\| M2\.T3 ' course-project/plan/M2-sim-mvp.md` (Mac) | `done` |
| M2.T7 done (harness) | task | `grep -E '^\| M2\.T7 ' course-project/plan/M2-sim-mvp.md` (Mac) | `done` |
| M2.T13, M2.T14 done (observation builder, report correction) | task | `grep -E '^\| M2\.T1(3\|4) ' course-project/plan/M2-sim-mvp.md` (Mac) | both `done` |
| M2.T20 done (mission metrics, C10.5) | task | `grep -E '^\| M2\.T20 ' course-project/plan/M2-sim-mvp.md` (Mac) | `done` |
| `beaconmind-ros` running | service | `docker ps --filter name=beaconmind-ros --format '{{.Status}}'` (Spark host) | `Up …` |

**Inputs.** README C2, C3, C5, C8, C9, C10.5, L4, L8; this file's M6-C1 to M6-C7;
`plan/M2-sim-mvp.md` "Module map for M2" (the exact public names M2 promises); the code in
`course-project/beaconmind/src/beaconmind/`: `config.py`, `envs/base.py`, `envs/kinsim.py`,
`envs/ros_env.py` (if it exists yet), `observation.py`, `report.py`, `harness/runner.py`,
`harness/runlog.py`, `harness/obslog.py`, `metrics/missions.py` (read their public functions);
`discussions/module4/l2mcp_core.py` (locking style).

**Steps.**
1. Mac: **verify the M2 API surface** for this task:
   ```bash
   cd /Users/xiaohuichen/Projects/EN.665.715/course-project/beaconmind/src/beaconmind && \
   grep -nE "^(def|class) |^    def " config.py observation.py report.py envs/*.py harness/*.py metrics/missions.py \
     > ../../../evidence/M6/M6.T7/api-surface.txt; cat ../../../evidence/M6/M6.T7/api-surface.txt
   ```
   Find and write under "As found" (the M2 module map promises the names in brackets; record the real
   ones): (a) the kinsim environment (`envs/kinsim.py` `KinSim`, `envs/base.py` `Env`, `Capture`) and
   how to reset it with a C7 world, step it with a C2 MoveCommand and read ground truth (C8); (b) the
   C3 builder and the object that holds the counters (`observation.py` `ObservationBuilder`); (c) the
   function that checks a final text against C6 and C5 item 4 and returns the corrected report plus
   violations (`report.py` `parse_final_text`, `check_format`, `correct_report`); (d) the run-log and
   observation-log writers (`harness/runlog.py` `EpisodeWriter`/`RunWriter`, `harness/obslog.py`
   `ObsLogWriter`); (e) the mission evaluator for C10.5, success and SPL (`metrics/missions.py`,
   M2.T20); (f) the MoveCommand builder (`envs/base.py` `make_move_command`) and the C2 cap check
   (`envs/pico_wire.py` `check_caps`); (g) `config.course_root()` and `config.load_dv()`. Use (f) and
   (g) instead of writing your own versions.
   - If (a)–(g) exist as callable functions or classes → continue.
   - If (b) or (c) is inlined in the harness loop and cannot be called alone → stop and ask (README §1.4
     item 6). Recommended: extract it into a function in its M2 module (no behaviour change) and re-run
     M2's tests.
2. Mac: write **`demo/rpc.py`** (standard library only):
   ```python
   class RpcTimeout(Exception): ...
   class RpcError(Exception): ...
   class FileRpcClient:
       def __init__(self, session_dir: Path, channel: str = "env", poll_s: float = 0.05): ...
       def call(self, op: str, payload: dict, timeout_s: float) -> dict:
           """Write req-<uuid4hex>.json atomically, wait for res-<id>.json, delete it, return result.
           ok false -> RpcError(error). No response in timeout_s -> delete own request if still there, RpcTimeout."""
   class FileRpcServer:
       def __init__(self, session_dir: Path, channel: str = "env", poll_s: float = 0.05): ...
       def pending(self) -> list[Path]:   # req-*.json only (never .tmp), sorted by (t_wall, name)
       def respond(self, req_id: str, ok: bool, result: dict | None, error: str | None) -> None
   ```
3. Mac: write **`demo/trace.py`**:
   ```python
   KINDS = {"runner": {...}, "env": {...}}   # exactly the M6-C5 table
   class DemoTrace:
       def __init__(self, path: Path, src: str, session_id: str): ...
       def event(self, kind: str, **fields) -> dict:  # adds t_wall=time.time(), src, session_id; ValueError on unknown kind; append+flush+fsync
   def read_trace(*paths: Path) -> list[dict]          # merge files, sort by t_wall, skip torn lines
   ```
4. Mac: write **`demo/env_adapters.py`**:
   ```python
   class DemoEnv(Protocol):
       source: str          # "kinsim" | "sim" | "real"
       def observe(self) -> dict            # the M6-C4 observe result
       def execute(self, cmd: dict) -> dict # C2 MoveCommand -> C2 MoveResult
       def set_mission(self, mission: str) -> dict
       def stop_motion(self) -> None        # used by estop; must return within 0.2 s
       def close(self) -> None
   def make_env(kind: str, world: dict, session_dir: Path) -> DemoEnv   # kind in {"kinsim", "ros"}
   class KinsimDemoEnv: ...   # wraps the M2.T3 env + the M2.T7 observation building (step 1 a, b)
   class RosDemoEnv: ...      # wraps beaconmind.envs.ros_env (imports rclpy inside __init__ only)
   ```
   `RosDemoEnv` is used from M6.T9 on; in this task it only needs to import lazily and raise a clear
   `RuntimeError("ros env needs rclpy; run inside beaconmind-ros")` when rclpy is missing. Its
   `stop_motion` publishes `/estop` `true` three times 20 ms apart (the M3.T13 pattern; C12: the Pico or
   `bm_sim_pico` consumes it); it must keep publishing the `/pico/heartbeat` through `RosEnv` (M3.T9:
   `PicoClient` owns the heartbeat inside the harness process) for as long as the server runs, including
   while the model thinks. `KinsimDemoEnv.stop_motion` aborts the kinematic move in progress.
5. Mac: write **`demo/env_server.py`** and its CLI
   `python3 -m beaconmind.demo.env_server --session <dir> --env kinsim|ros [--poll-s 0.05]`:
   - On start: read `session.json` and `world.json`; build the environment with `make_env`; write
     `env_ready` to `trace-env.jsonl`; print one line `env_server ready: <source> <world_id>`.
   - Serve the M6-C4 ops. **`execute` runs in a worker thread**, so that `estop` and `status` are
     still answered while a move runs; only one `execute` at a time (a second gets `refused`, reason
     "a move is already running").
   - Before `execute`: refuse if the session's latch file exists (`session.json` `latch_path`, M6-C1),
     if a move was already executed for this `obs_id`, or if the command breaks a C2 cap (the M6-C4
     list, checked with M2's `check_caps` if step 1 (f) found it; values read with `config.load_dv()`,
     never typed). Write `move_start` and `move_end` trace events around the call.
   - `estop`: write the latch file with `validator.Latch(<latch_path>).set(reason, by="demo-estop")`
     (if not already set), call `env.stop_motion()`, write the `estop` trace event, return
     `{"latched": true}`.
   - Write the observation log `obslog.jsonl` (C9.1) with M2's `ObsLogWriter`: header `driver`
     `L2:<model_key>` (or `operator` for stub sessions, which have no model) and `notes` "ROSA course
     demo session <session_id>; demo-only, not benchmark-comparable" (do not invent a new driver
     value: C9.1 allows only `B2`, `operator`, `L2:<model_key>`); one `step` line per observation
     (with the executed move filled in when the next observe arrives); the footer at `shutdown`.
   - Print lines to stdout (this pane is filmed): `OBSERVE step 14: 2 tags, status ok`;
     `MOVE #17 FORWARD_25 start` when the move starts and `MOVE #17 FORWARD_25 -> done in 1.92 s (gt
     +0.248 m)` when it ends; `ESTOP latched: <reason>`; `MISSION RETURN_TO_START (steps_left 60)`.
   - Use `python3 -u` (unbuffered) so the pane shows each line at once.
   - On `SIGINT`/`SIGTERM` (Ctrl-C in its pane): call `env.stop_motion()`, write the obslog footer
     (`reason_ended: "operator_stop"`), trace nothing more, and exit 0. This is how a `real` session is
     torn down after a latch that was not resumed.
6. Mac: write **`demo/estop.py`**, CLI
   `python3 -m beaconmind.demo.estop --session <dir> --reason "<text>" [--on-next-move FORWARD --delay-s 0.5 --wait-max-s 900]`:
   without `--on-next-move`, write the latch file at once (`Latch(<latch_path>).set`, works even if the
   server is dead), then send the `estop` RPC with a 2 s timeout and print its answer or "server did not
   answer; latch file written". With `--on-next-move PREFIX`: poll `trace-env.jsonl` every 0.05 s for
   the first `move_start` event written **after** the command started whose `action` starts with
   `PREFIX`, sleep `--delay-s`, then do the same as above; give up after `--wait-max-s` with
   "no matching move started". This makes the M6.T9 estop check deterministic (a person cannot react
   within a 1.7 s move). **This is not the project's primary out-of-band STOP**: that is the M3.T13
   hotkey `bm-estop` / `/estop` path (C5 item 5, S7), which does not depend on any demo process.
7. Mac: write **`demo/script.py`**:
   ```python
   def load_script(path: Path) -> dict                    # validates against bm.demo_script-1.schema.json
   def segment_mission(seg: dict, previous_mission: str | None) -> str   # "carry" -> previous
   def request_text(seg: dict, target: str | None) -> str | None        # fills {target}
   def answered(report: dict) -> bool                      # requested_mission set, or decision REFUSED/ASK
   def choose_target(report: dict) -> str | None:
       """Confirmed, not suspect, label 'B<id>' (no 'b' suffix), id appears once in the map;
       predicted distance from report['pose'] closest to 1.2 m; ties -> lower id. None if no candidate."""
   ```
8. Mac: write **`demo/runner_core.py`**:
   ```python
   @dataclass
   class DeciderTurn:
       final_text: str | None; tool_calls: list[dict]; error: str | None; t_start: float; t_end: float
   class Decider(Protocol):
       def decide(self, step_message: dict) -> DeciderTurn: ...
   class StubDecider:            # plumbing only; calls tools through tool_handler.handle_tool
       def __init__(self, session_dir: Path): ...
   class DemoRunner:
       def __init__(self, session_dir: Path, decider: Decider, console=print): ...
       def run(self, start_segment: str | None = None, prev_report_path: Path | None = None,
               max_steps: int | None = None) -> list[dict]:   # returns segments.json content
   ```
   `DemoRunner.run` does, for each segment of `script.json` (M6-C7 flow) and each step:
   1. trace `step_start`; `observe` RPC; trace `observation_ready`;
   2. build the step message `{"mission", "operator_request", "OBSERVATION", "PREVIOUS_REPORT"}` (C3);
   3. write `ctx/step_ctx.json` (M6-C3) with the M2 `StepContext` serialised;
   4. trace `llm_start`; `turn = decider.decide(step_message)`; trace `llm_end` with the latency;
   5. take this step's tool records from `ctx/tools.jsonl` (`read_tool_records(session, obs_id)`),
      collect their `violations`, and read `ctx/move_state.json` to learn whether a move executed and
      its result; run the step-1(c) report check; trace `report` and each `violation` (tool-call
      violations and report violations);
   6. write the C9.2 run-log line to `runlog/<episode_id>.jsonl` (`episode_id` =
      `<world_id>-<segment>-k0`; `mode: closed_loop`; `cost_usd: 0`; `llm_turns` built from the tool
      records; `gt_pose_map` and `det_truth` from the observe result). The run header goes to
      `runlog/run.json` with `"harness": "rosa-demo"` and `"benchmark_comparable": false`;
   7. apply the request and mission rules of M6-C7; on a mission switch call `set_mission`;
   8. at segment end: append the segment to `segments.json` (M6-C6) with `ended_by`,
      `answered_at_step`, `moves_after_answer`, and `success: null`, `spl: null`, `scored: false`
      (scoring is step 8b, after the session); write `state/after-<segment>.json` = `{"mission",
      "report_corrected", "step"}`; trace `segment_end`.
   Console lines the runner prints (the filmed pane and M6.T3's operator rely on them): `segment <name>
   started (mission <mission>)` at segment start; `segment <name> ended: <ended_by> after <n> steps`
   at its end; `session ended` as the last line.
   The `goto` segment's `{target}` is `choose_target(last corrected report)`; if it returns `None`,
   end the segment with `ended_by: "no_target"`, `notes: "no eligible target"` and continue. After the
   last segment: trace `session_end`, fill `session.json`'s `ended`, send the `shutdown` RPC (the
   environment server writes the obslog footer and exits), and print `session ended`.
   **A latch ends the session, not only the segment** (every later move would be refused anyway): the
   runner ends the current segment with `ended_by: "latch"`, writes its `state/after-<segment>.json`,
   starts no further segment, and traces `session_end`. If `source` is `sim` or `kinsim` it then sends
   `shutdown` and prints `session ended` (no resume in simulation, M6.T10 step 4). If `source` is
   `real` it does **not** send `shutdown` (the environment server keeps running for a resume, M6.T3
   step 11) and prints `LATCHED: session stopped after segment <name>; resume with --start-segment
   <next> --prev-report state/after-<name>.json`. A resumed run appends to the same `segments.json`,
   run logs and traces.
8b. Mac: write **`demo/score.py`**, CLI `python3 -m beaconmind.demo.score --session <dir>` (runs in
   `beaconmind-ros` or the Spark host venv, never in `rosa-ros2`): for each `segments.json` entry,
   apply the step-1 (e) evaluator to the run-log lines of that segment (ground truth `gt_pose_map` at
   the step whose decision ended it; C10.5: `EXPLORE` with the world's tags, `RETURN_TO_START`,
   `GO_TO_BEACON <target>` with the target's true tag), and for `refuse` the rule "decision `REFUSED`
   and `moves_after_answer` = 0"; set `success`, `spl`, `gt_source` (`kinsim`, `sim`, `overhead`, or
   `none` when `gt_pose_map` is null on that step, then `success` stays null) and `scored: true`; also
   validate every run-log line against `bm.runlog/1` and the obslog against `bm.obslog/1`, printing
   `schema ok` or each failure. It rewrites `segments.json` atomically and prints one line per segment
   `<name> success <true|false|null> spl <x|null> (<rule>)`. It is idempotent (running it twice gives
   the same file).
   `new_session --model-key none` (stub sessions) stores `provider_entry: null`.
   `StubDecider` (no model, for plumbing tests only): pose = `compose_odometry` of the previous pose
   and the odometry (through `handle_tool`); answers operator requests by keywords ("started" →
   `RETURN_TO_START`, `B<n>` → `GO_TO_BEACON B<n>`, "follow" → `REFUSED`, else `ASK`); in `EXPLORE`
   calls `move` with `TURN_LEFT_30` if `turn_allowed`, else the first entry of `forward_allowed`, and
   decides `DONE` at step 6; in `RETURN_TO_START`/`GO_TO_BEACON` decides `DONE` after 2 moves; its
   report copies the previous map and memory (step 0: the D7 step-0 memory from M2.T1's C6 fixture).
9. Mac: write **`demo/new_session.py`**, CLI
   `python3 -m beaconmind.demo.new_session --source kinsim|sim|real --label <text> --world <path> --script configs/demo_script.json --decider stub|rosa --model-key <key> [--rosa-mode trimmed|stock] [--take N]`:
   creates `data/demo/<session_id>/` (M6-C1) **and every subfolder** of the M6-C1 tree, with
   `session.json` (M6-C2: `prompt_sha12` null — `run.py --decider rosa` fills it, M6-C2; tool schema
   SHA-12 from `tools.tool_schema_sha12()`, DV SHA-12 with `config.sha12_file`; `latch_path` per M6-C1
   from `--source`), copies the script and world, and prints the folder path as its last line. It
   never imports `beaconmind.demo.prompts` (the host venv has no `rosa`).
10. Mac: write **`demo/run.py`**, CLI
    `python3 -m beaconmind.demo.run --session <dir> --decider stub|rosa [--start-segment NAME --prev-report PATH] [--max-steps N] [--pause-between-segments]`.
    `--decider rosa` imports `beaconmind.demo.rosa_decider` (M6.T8) lazily; until then it exits with
    "rosa decider not built yet (M6.T8)". `--max-steps N` (smoke tests only) caps the **whole session**
    at N steps: when the N-th step ends, the current segment ends with `ended_by: "max_steps"`, no
    further segment starts, and the runner still traces `session_end`, sends `shutdown` and prints
    `session ended`. `--pause-between-segments` (used on the car, M6.T3): before
    each segment after the first, trace `pause_start`, print `PAUSED before segment <name>: press Enter
    to continue`, wait for one line on stdin, trace `pause_end`. The robot is stopped and the Pico's
    heartbeat keeps running in the environment server meanwhile.
11. Mac: write the JSON Schemas `bm.demo_session-1`, `bm.demo_rpc-1`, `bm.demo_trace-1`,
    `bm.demo_segments-1`, `bm.demo_script-1` under `beaconmind/src/beaconmind/schemas/`, and a first
    `course-project/configs/demo_script.json` exactly as M6-C7 (M6.T4 fills the seeds).
12. Mac: write and run the tests below; then a **stub smoke** on the Mac with kinsim. Pick the fixture
    world: `ls course-project/beaconmind/tests/fixtures/worlds/` and use the first file whose name
    starts with `sim-dup-` (any fixture world if none does; write its name in `CONTEXT.md`).
    ```bash
    cd /Users/xiaohuichen/Projects/EN.665.715/course-project && W=beaconmind/tests/fixtures/worlds/<that file>.json && \
    S=$(.venv/bin/python -m beaconmind.demo.new_session --source kinsim --label stub --world "$W" \
        --script configs/demo_script.json --decider stub --model-key none | tail -1) && echo "$S"
    .venv/bin/python -u -m beaconmind.demo.env_server --session "$S" --env kinsim > "$S/env-stdout.txt" 2>&1 &
    .venv/bin/python -u -m beaconmind.demo.run --session "$S" --decider stub | tee "$S/runner-stdout.txt"
    wait   # the runner's shutdown RPC ends the environment server
    .venv/bin/python -m beaconmind.demo.score --session "$S"
    .venv/bin/python -m beaconmind.demo.estop --session "$S" --reason "end of smoke"   # proves estop works with the server gone
    ls "$S/LATCH" && rm "$S/LATCH"
    ```
    Expected: the runner prints four `segment … ended` lines and `session ended`; `estop` prints
    "server did not answer; latch file written"; the latch file is the **session's own**
    `$S/LATCH` (kinsim, M6-C1), never `data/LATCH`, so deleting it with `rm` is allowed.
13. Spark host: sync (`bash course-project/tools/sync_to_spark.sh`), then repeat step 12 with the
    session folder created **on the host** (M6-C1 ownership rule) and both processes run **inside
    `beaconmind-ros`**, to prove the server runs where M6.T9 will run it:
    ```bash
    cd ~/Projects/EN.665.715/course-project && W=beaconmind/tests/fixtures/worlds/<same file>.json && \
    S=$(~/.venvs/beaconmind/bin/python -m beaconmind.demo.new_session --source kinsim --label stub --world "$W" \
        --script configs/demo_script.json --decider stub --model-key none | tail -1) && I=$(basename "$S") && \
    C=/workspace/course-project/data/demo/$I && \
    docker exec -d -w /workspace/course-project/beaconmind beaconmind-ros bash -lc "python3 -u -m beaconmind.demo.env_server --session $C --env kinsim > $C/env-stdout.txt 2>&1" && \
    docker exec -w /workspace/course-project/beaconmind beaconmind-ros python3 -u -m beaconmind.demo.run --session $C --decider stub | tee "$S/runner-stdout.txt" && \
    docker exec -w /workspace/course-project/beaconmind beaconmind-ros python3 -m beaconmind.demo.score --session $C && \
    ls -ln "$S" "$S/ctx"; if test -e data/LATCH; then echo "GLOBAL LATCH PRESENT"; else echo "global latch untouched"; fi
    ```
    Expected: as step 12, plus `global latch untouched` (check `test -e data/LATCH` **before** the
    smoke too: if the global latch was already set by someone else, do not clear it; stop and ask). `ls -ln` shows who owns the files; if
    anything under `ctx/` or `rpc/env/` is owned by uid 0 **and** a later `rosa-ros2` process (uid
    1000) would need to write it, note it for M6.T8. Keep this session folder: M6.T11 and M6.T12 use it
    as their fixture. Copy `segments.json`, `trace-*.jsonl`, `runner-stdout.txt`, `env-stdout.txt`
    and `runlog/` into `evidence/M6/M6.T7/stub-session/`, then pull with
    `bash course-project/tools/pull_evidence.sh M6 M6.T7` (Mac).
14. Mac: status table and `CONTEXT.md` (which stub session folder is the fixture for M6.T11).

**Deliverables.** `course-project/beaconmind/src/beaconmind/demo/rpc.py`, `trace.py`,
`env_adapters.py`, `env_server.py`, `estop.py`, `script.py`, `runner_core.py`, `new_session.py`,
`run.py`, `score.py`; the five schemas; `course-project/configs/demo_script.json`; tests
`course-project/beaconmind/tests/test_demo_rpc.py`, `test_demo_trace.py`, `test_demo_env_server.py`,
`test_demo_script.py`, `test_demo_runner_stub.py`.

**Tests.**
- `tests/test_demo_rpc.py`:
  - `test_roundtrip` — a server thread answers `status`; the client gets the result.
  - `test_timeout_raises_and_cleans` — no server; `call(…, timeout_s=0.3)` raises `RpcTimeout` and leaves
    no `req-*.json` behind.
  - `test_order_by_t_wall` — three requests written with increasing `t_wall` are served in that order.
  - `test_tmp_files_ignored` — a `.req-x.json.tmp` file is never served.
  - `test_concurrent_clients` — two processes make 20 calls each; all 40 answers match their ids.
- `tests/test_demo_trace.py`:
  - `test_unknown_kind_rejected` — `event("foo")` raises `ValueError`.
  - `test_merge_sorted_and_torn_line_skipped` — two files merged in `t_wall` order; a torn last line is
    skipped.
- `tests/test_demo_env_server.py` (a fake `DemoEnv` with a configurable move time; every session is
  built under `tmp_path / "data" / "demo" / "<id>"`, so no test ever touches the repository's
  `data/LATCH`):
  - `test_latch_refuses_execute` — with the session's latch file present, `execute` returns `refused`
    and the fake env was not called.
  - `test_one_move_per_obs_id` — the second `execute` for the same `obs_id` returns `refused`.
  - `test_caps_enforced` — `distance_m` 0.30 returns `refused`; 0.25 is executed.
  - `test_estop_during_move` — while a 2 s fake move runs, `estop` is answered within 0.5 s, the fake
    env's `stop_motion` was called, the session's latch file exists, and the trace has `estop` after
    `move_start`.
  - `test_estop_on_next_move` — `demo.estop` with `--on-next-move FORWARD --delay-s 0.5` started before
    a 2 s fake `FORWARD_25`: the `estop` event lies between that move's `move_start` and `move_end`,
    and an earlier `TURN_LEFT_30` did not trigger it.
  - `test_move_trace_events` — `move_start` then `move_end` with `result` and `duration_s` ≥ the fake
    move time.
- `tests/test_demo_script.py`:
  - `test_carry_mission` — `segment_mission({"mission": "carry"}, "EXPLORE")` is `EXPLORE`.
  - `test_answered` — `requested_mission` set → True; `REFUSED` → True; `NONE` with no request → False.
  - `test_choose_target_rule` — a map with B3 (confirmed, 1.1 m), B7 (confirmed, 1.3 m, id 7 also as
    B7b), B9 (tentative, 1.2 m) → `B3` (B7 excluded as duplicated, B9 as tentative).
  - `test_choose_target_none` — no confirmed beacon → `None`.
- `tests/test_demo_runner_stub.py` (kinsim, a small fixture world, the env server in a thread):
  - `test_stub_runs_all_segments` — `segments.json` has 4 entries named explore, return, goto, refuse.
  - `test_refuse_segment_has_no_move` — the refuse entry has `decision_final` `REFUSED`,
    `ended_by` `REFUSED` and `moves_after_answer` 0, and `trace-env.jsonl` has no `move_start` after the
    refuse segment's start.
  - `test_pause_between_segments` — with `--pause-between-segments` and stdin fed three newlines, the
    trace has three `pause_start`/`pause_end` pairs, each just before a `segment_start` of return, goto
    and refuse.
  - `test_score_fills_success` — after `demo.score`, every entry has `scored: true`, `gt_source`
    `kinsim`, and `success` true or false (kinsim has ground truth); running `score` twice leaves the
    file byte-identical.
  - `test_unanswered_request_ends_segment` — a stub variant that never answers (decision `NONE`,
    `requested_mission` null) ends `return` after `request_repeat_max` (3) steps with `ended_by`
    `request_unanswered`.
  - `test_latch_ends_session` — a kinsim stub session whose latch file is set (by the test, through
    `demo.estop`) during the `return` segment: `return` ends with `ended_by` `latch`, `segments.json`
    has exactly 2 entries, the trace has `session_end`, and the environment server exited (shutdown
    sent, because the source is `kinsim`).
  - `test_runlog_and_obslog_valid` — every run-log line validates as `bm.runlog/1` and the obslog
    header as `bm.obslog/1`; `runlog/run.json` has `"benchmark_comparable": false`.
  - `test_trace_order_per_step` — for every step: `step_start` < `observation_ready` < `llm_start` <
    `llm_end` < `report`, and any `move_start` lies between `llm_start` and `llm_end`.
- Commands → expected: Mac `cd course-project/beaconmind && ../.venv/bin/python -m pytest -q tests/test_demo_rpc.py tests/test_demo_trace.py tests/test_demo_env_server.py tests/test_demo_script.py tests/test_demo_runner_stub.py`
  → `25 passed` (5 + 2 + 6 + 4 + 8); the same in `beaconmind-ros` (L4 command with these files) → `25 passed`.
- Smoke tests: step 12 (Mac) and step 13 (`beaconmind-ros`). Pass: the runner prints four
  `segment … ended` lines and `session ended`; `segments.json` has 4 entries, all `scored: true`
  after `demo.score`; the refuse entry is `REFUSED` with `moves_after_answer` 0; `trace-env.jsonl` has
  ≥ 6 `move_end` events with `result` `done`; step 13 prints `global latch untouched`.

**Acceptance criteria.**
- [ ] `api-surface.txt` "As found" names the M2 pieces (a)–(g).
- [ ] `25 passed` on the Mac and in `beaconmind-ros`.
- [ ] Stub smoke passes on the Mac and in `beaconmind-ros`; the Spark stub session folder is named in
      `CONTEXT.md` as the M6.T11 fixture.

**Evidence to save** (`evidence/M6/M6.T7/`): `api-surface.txt`; `tests-mac.txt`; `tests-py310.txt`;
`stub-smoke-mac.txt` and `stub-smoke-spark.txt` (both panes' output); `stub-session/` (the small files).

**Pitfalls and known gotchas.**
- `os.replace` is atomic only within one filesystem: write the `.tmp` file in the same folder.
- Both containers see the session folder through bind mounts of the same host folder; uid 1000
  (`rosa-ros2`) must be able to write files the other container created: create the folder on the host
  (M6-C1) and never `chmod` it from a container.
- Never name a folder `log/` (the global `.gitignore` ignores it; README L1).
- The stub is a plumbing tool. Never present a stub session as a demo result.
- Do not hard-code any DV: read `configs/dv.json` (L7).

**Stop-and-ask conditions.** Step 1 (b) or (c) is not callable; the kinsim environment cannot be reset
with a C7 world; any M2 test fails after a change made here; `data/LATCH` exists on the Spark before
or after the step-13 smoke (someone latched the project: never clear it yourself).

**Estimated effort.** S (one long session; the code is mostly glue around M2).

**AI-disclosure note.** Each new `.py` file: `AI-assisted: <model> via <tool>, <date>: <what>.`
`configs/demo_script.json` cannot hold comments: add a line to `course-project/configs/README.md`
(create it if absent) `demo_script.json — AI-assisted: <model> via <tool>, <date>: drafted from plan M6-C7.`

---

### M6.T8 — ROSA decider, ReAct console, demo trace and tmux capture; kinsim smoke with the real model

**Why.** This is where ROSA drives the demo (D10): `accumulate_chat_history=False`, the v3.3 prompt
(made template-safe in M6.T2), the `bm-tools` MCP server as its only tools (MD1 default), and a
console that makes the ReAct loop readable on video: what the robot observed, which tools it called
and what they returned, what it reported and decided, and what the validator said. The tmux layout and
pane capture follow the Module 5 filming method (`discussions/module5/tools/m5-frames.sh`,
`m5-render.py`), which worked for the take filmed on 2026-10-04.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M6.T7 done | task | `grep -E '^\| M6\.T7 ' course-project/plan/M6-demo-presentation.md` (Mac) | `done` |
| vLLM serving | service | `curl -sf http://127.0.0.1:8000/v1/models` (Spark host) | JSON listing `Qwen/Qwen3.5-35B-A3B` |
| `rosa-ros2` sees the project | service | `docker exec rosa-ros2 test -f /workspace/course-project/beaconmind/src/beaconmind/demo/mcp_bm_tools.py && echo ok` (Spark host) | `ok` |
| `configs/providers.json` has the OD8 model | config | `python3 -c "import json;print(list(json.load(open('course-project/configs/providers.json'))['models']))"` (Mac) | includes the key OD8 chose (for example `qwen35-a3b-think`) |

To start vLLM if it is down (Spark host): `docker start vllm-rosa`, then wait:
`for i in $(seq 1 60); do curl -sf http://127.0.0.1:8000/v1/models >/dev/null && echo up && break; sleep 10; done`.
If `docker start` fails because the container was removed:
`cd ~/Projects/EN.665.715/discussions/module2 && GPU_UTIL=0.60 MAX_LEN=131072 MAX_SEQS=4 ./vllm-serve.sh start && ./vllm-serve.sh wait`
(README L5; never the default `GPU_UTIL` 0.75 when Isaac must run beside it).

**Inputs.** AGENT-DESIGN D8, D9, D10; README C3, C6, C11; `discussions/module4/rosa_agent_l2.py`
(`build_llm`, `McpOnlyROSA`, `json_tool_errors`, `run_once`, `brief`); `discussions/module5/tools/m5-frames.sh`
and `m5-render.py`; `discussions/module5/talk-track.md` ("Assembling the video").

**Steps.**
0. Spark host: **verify what the runner can import in `rosa-ros2`** (the runner runs there, Python
   3.10, with only the course image's packages; never `pip install` into it without asking):
   ```bash
   docker exec -w /workspace/course-project/beaconmind rosa-ros2 bash -lc 'PYTHONPATH=src python3 -c "
   import importlib
   for m in [\"jsonschema\", \"numpy\", \"beaconmind.tools\", \"beaconmind.validator\", \"beaconmind.observation\",
             \"beaconmind.report\", \"beaconmind.config\", \"beaconmind.harness.runlog\", \"beaconmind.metrics.missions\",
             \"beaconmind.demo.runner_core\", \"beaconmind.demo.run\"]:
       try:
           importlib.import_module(m); print(\"OK  \", m)
       except Exception as e:
           print(\"FAIL\", m, type(e).__name__, e)
   "' | tee /tmp/m6t8-imports.txt
   ```
   Save as `evidence/M6/M6.T8/rosa-ros2-imports.txt`. Branches:
   - `beaconmind.demo.runner_core` and `beaconmind.demo.run` print `OK` → continue (the runner does not
     need `metrics.missions` or `jsonschema`: scoring and schema checks are `demo/score.py`, run in
     `beaconmind-ros`, M6.T7 step 8b).
   - `beaconmind.demo.runner_core` or `beaconmind.demo.run` prints `FAIL` because an M2 module it
     imports needs a package that is absent (for example `harness.runlog` importing `jsonschema` at
     module level) → change the import in `runner_core.py` to a lazy import inside the one function
     that needs it, or write the run-log line with `json.dumps` (the C9.2 shape) and leave validation
     to `demo/score.py`; re-run this check. If it still fails after two attempts → stop and ask (do not
     install packages into `rosa-ros2`).
1. Mac: write **`demo/console.py`** (pure functions, standard library only). Every printed line starts
   with a fixed tag so the renderer (M6.T12) can colour it and the viewer can follow the loop:
   ```
   ═══ STEP 14 · EXPLORE · steps_left 136 · sim-dup-s3000-explore-k0-s014
   OBSERVATION odom +0.25 m −0.00 m +0.4° (ok) · last FORWARD_25=done · tags: id1 1.02 m +17.0° q0.86
   OPERATOR    "Please go back to where you started."
   ACTION      gate_detection(det=0, candidates=[B1])
   RESULT      B1 in_gate · Δrange −0.03 m · Δbearing +2.1° · revisit no
   ACTION      move(FORWARD_25)
   RESULT      done in 1.92 s
   REPORT      pose (−0.12, 0.65, 22.9°) via beacon_fix · map 5 (3 confirmed) · decision FORWARD_25
   NOTE        I fixed my pose from B1+B5 (residual 0.02 m), closed both revisits and started scan 3.
   CHECK       violations none · 41.2 s · 4 tool calls
   ```
   Functions: `step_header(step_msg) -> list[str]`, `observation_lines(obs) -> list[str]`,
   `tool_lines(name, args, result) -> list[str]` (one short summary per tool; an error result prints
   `RESULT      ERROR <text>`), `report_lines(report, violations, latency_s, n_tools) -> list[str]`,
   `wrap(line, width=118) -> list[str]` (continuation lines indented 12 spaces). The `NOTE` line is the
   report's `note` field (D8: the agent's own first-person summary). **Label it NOTE, never THOUGHT**:
   the model's hidden reasoning is not captured (verified in Module 4), so the video must not claim
   to show it.
2. Mac: write **`demo/rosa_decider.py`** (imports `rosa`, `langchain_mcp_adapters` and the vendored
   `llm_backends` only inside functions, so the module imports anywhere):
   ```python
   def build_llm(entry: dict):
       """C11 entry -> vendored SingleSystemChatOpenAI. Only provider 'vllm' (else ValueError).
       base_url, model, api_key 'EMPTY', temperature/top_p/presence_penalty from entry['sampling'],
       extra_body={'chat_template_kwargs': {'enable_thinking': entry['thinking']}, 'top_k': sampling['top_k']},
       timeout=entry['request_timeout_s'] (Module 4 build_llm pattern)."""
   def mcp_config(session_dir_in_container: str) -> dict      # the T2 smoke config
   def json_tool_errors(tools) -> list                         # Module 4 pattern: errors back as D5 JSON
   def make_agent(llm, tools, prompts, rosa_mode: str, max_iterations: int | None)
       # trimmed: McpOnlyROSA (defined inside this function, Module 4 pattern) ; stock: ROSA
       # always accumulate_chat_history=False, streaming=True, verbose=False
   def collect_events(events: list[dict]) -> tuple[list[dict], str | None, str | None]
       # pure: pair tool_start/tool_end by name and order -> calls; final text; error
   class RosaDecider:
       def __init__(self, session_dir: Path, entry: dict, rosa_mode: str = "trimmed",
                    max_iterations: int | None = 30, console=print, trace=None): ...
       def decide(self, step_message: dict) -> DeciderTurn: ...
   ```
   **Event loop:** create one `asyncio` event loop in a background thread at construction
   (`loop = asyncio.new_event_loop(); threading.Thread(target=loop.run_forever, daemon=True).start()`),
   build the tools and the agent **on that loop** once, and in `decide` use
   `asyncio.run_coroutine_threadsafe(self._decide(text), loop).result()`. Do not call `asyncio.run`
   per step: the LLM client's async HTTP connection is bound to the loop that created it.
   In `_decide`: iterate `agent.astream(json.dumps(step_message))`; on each event print the console
   lines and write `tool_start`/`tool_end` trace events at receipt; after the loop call
   `agent.clear_chat()`. Construct exactly **one** `ROSA` per process (AGENTS.md §7.4 gotcha 5).
3. Mac: wire `--decider rosa` in `demo/run.py`: read the provider entry from `configs/providers.json`
   by `session.json`'s `model_key`; load the prompt with `prompts.rosa_safe(prompts.load_final_prompts())`;
   write `prompt_sha12 = prompts.prompt_sha12(<that prompt>)` into `session.json` (atomic rewrite)
   and into `runlog/run.json` **before the first step**, and print `prompt sha12 <value>` in the runner
   pane; then `RosaDecider(session_dir, entry, rosa_mode=session["rosa_mode"])`. If `session.json`
   already has a non-null `prompt_sha12` (a resumed car take) and it differs → exit with "prompt changed
   since this session started" (never mix prompts in one take).
4. Mac: write **`course-project/tools/demo_capture.sh <session_dir_on_host> <tmux_target>`**: every
   0.5 s write `term/<n:06d>.runner.txt` and `term/<n:06d>.env.txt`, each starting with a line
   `T=<epoch seconds with fraction>` followed by `tmux capture-pane -p -J -t <target>.0` (runner pane)
   or `.1` (environment pane), ANSI codes stripped. Stop when `<session>/term/STOP` exists or after 8
   hours. (Pattern: `discussions/module5/tools/m5-frames.sh`.)
5. Mac: write **`course-project/tools/demo_tmux.sh <session_id> <env_kind> <decider> [<extra runner args>]`**
   (Spark host). The optional fourth argument (for example `"--max-steps 5"` or
   `"--pause-between-segments"`) is placed **inside** the quoted `bash -lc '…'` command; text typed
   after the closing quote would go to `bash`, not to the runner, and be silently ignored.
   ```bash
   #!/usr/bin/env bash
   # AI-assisted: <model> via <tool>, <date>: tmux layout for the ROSA demo (M6.T8).
   set -euo pipefail
   ID=$1; ENVK=$2; DEC=$3; EXTRA=${4:-}
   S=/workspace/course-project/data/demo/$ID; H=$HOME/Projects/EN.665.715/course-project/data/demo/$ID
   test -d "$H" || { echo "no session folder $H"; exit 1; }
   tmux has-session -t bmdemo 2>/dev/null && { echo "tmux session bmdemo already exists; kill it first"; exit 1; }
   tmux new-session -d -s bmdemo -n demo -x 240 -y 62
   tmux split-window -h -t bmdemo:demo -l 100
   tmux send-keys -t bmdemo:demo.1 "docker exec -it -w /workspace/course-project/beaconmind beaconmind-ros bash -lc 'source /opt/ros/humble/setup.bash && python3 -u -m beaconmind.demo.env_server --session $S --env $ENVK'" Enter
   tmux send-keys -t bmdemo:demo.0 "docker exec -it -w /workspace/course-project/beaconmind rosa-ros2 bash -lc 'source /opt/ros/humble/setup.bash && PYTHONPATH=src python3 -u -m beaconmind.demo.run --session $S --decider $DEC $EXTRA'"   # no Enter: the operator starts it
   tmux new-window -t bmdemo -n cap "bash $HOME/Projects/EN.665.715/course-project/tools/demo_capture.sh $H bmdemo:demo"
   tmux new-window -t bmdemo -n ctl
   echo "attach with: tmux attach -t bmdemo   (runner command typed in pane demo.0; press Enter to start)"
   ```
   The runner command is typed but not started, so Xiaohui (or the executor) starts it when the
   capture and, on the car, the phone are rolling. If the environment pane needs ROS overlays beyond
   `/opt/ros/humble` for `--env ros` (the project workspace `install/setup.bash`, M2.T17), add them to
   that `bash -lc` exactly as M2.T17's evidence runs `RosEnv`.
6. Mac: write the tests below and run them; sync to the Spark.
7. Spark host: **kinsim smoke with the real model, 5 steps** (one segment):
   ```bash
   cd ~/Projects/EN.665.715/course-project && \
   S=$(~/.venvs/beaconmind/bin/python -m beaconmind.demo.new_session \
       --source kinsim --label smoke5 --world <the M6.T7 fixture world, host path> \
       --script configs/demo_script.json --decider rosa --model-key <OD8 key> | tail -1); echo "$S"
   bash tools/demo_tmux.sh "$(basename "$S")" kinsim rosa "--max-steps 5"
   tmux send-keys -t bmdemo:demo.0 Enter
   ```
   First check the typed command: `tmux capture-pane -p -t bmdemo:demo.0 | tail -3` must show
   `--max-steps 5` **before** the closing `'`. Wait for the runner to print `session ended` (with
   `--max-steps 5` it stops after 5 steps and still sends `shutdown`). Then
   `docker exec -w /workspace/course-project/beaconmind beaconmind-ros python3 -m beaconmind.demo.score --session /workspace/course-project/data/demo/$(basename "$S")`,
   `touch "$S/term/STOP"`, `tmux kill-session -t bmdemo`.
8. Spark host: check the smoke (Tests) and copy the small files to `evidence/M6/M6.T8/smoke5/`; pull to
   the Mac.
9. Mac: status table, `CONTEXT.md` (latency of the 5 steps, any infrastructure error, the session id).

**Deliverables.** `course-project/beaconmind/src/beaconmind/demo/console.py`, `rosa_decider.py`;
`demo/run.py` (updated); `course-project/tools/demo_capture.sh`, `course-project/tools/demo_tmux.sh`;
tests `course-project/beaconmind/tests/test_demo_console.py`, `test_demo_rosa_decider.py`.

**Tests.**
- `tests/test_demo_console.py`:
  - `test_step_header_fields` — the header contains the step number, mission, `steps_left` and `obs_id`.
  - `test_tool_lines_per_tool` — each of the nine tools gives exactly one `ACTION` line and at least one
    `RESULT` line from a sample result; an error result prints `RESULT      ERROR`.
  - `test_note_label_not_thought` — `report_lines` uses the tag `NOTE` and no line contains `THOUGHT`.
  - `test_wrap_width` — no returned line is longer than 118 characters; continuation lines start with
    12 spaces.
- `tests/test_demo_rosa_decider.py` (no `rosa` needed; it tests the pure parts):
  - `test_collect_events_pairs_calls` — two `gate_detection` starts and ends in order give two calls
    with their outputs; the `final` content is returned.
  - `test_collect_events_error` — an `error` event is returned as the error string.
  - `test_build_llm_rejects_non_vllm` — an `openai_responses` entry raises `ValueError` (skip the
    positive case unless `langchain_openai` is importable).
- Commands → expected: Mac `../.venv/bin/python -m pytest -q tests/test_demo_console.py tests/test_demo_rosa_decider.py`
  → `7 passed`; `beaconmind-ros` (L4) → `7 passed`.
- Smoke test (step 7, Spark): **plumbing pass** = all 5 steps completed with `error` null in every
  run-log line; every tool call in `ctx/tools.jsonl` also appears as a `tool_end` event in
  `trace-runner.jsonl` (the same names with the same counts per step; the order may differ, because ROSA
  can run one turn's tool calls concurrently); every `move` that returned `done` has a matching
  `move_end` in `trace-env.jsonl`; `term/` holds ≥ 20 capture pairs; `session.json` has a non-null
  `prompt_sha12` equal to the `prompt sha12` line printed in the runner pane. **Model quality is recorded, not
  judged here:** count format, state and invalid-tool-call violations, moves executed, and the
  per-step decision latency (p50 and max) into `evidence/M6/M6.T8/smoke5/summary.md`.

**Acceptance criteria.**
- [ ] `7 passed` on the Mac and in `beaconmind-ros`.
- [ ] The 5-step kinsim smoke passes the plumbing checks; its summary lists the violations and
      latencies.
- [ ] `term/` captures exist and contain the tagged console lines (`grep -c '^ACTION' term/*.runner.txt | tail -1` > 0).

**Evidence to save** (`evidence/M6/M6.T8/`): `rosa-ros2-imports.txt` (step 0); `tests-mac.txt`, `tests-py310.txt`, `smoke5/` (session
JSON files, `segments.json`, both traces, run log, `summary.md`, three sample capture pairs).

**Pitfalls and known gotchas.**
- Qwen chat templates reject a second system message; the vendored `SingleSystemChatOpenAI` merges them
  (AGENTS.md §7.4 gotcha 5). Do not use plain `ChatOpenAI`.
- Thinking on/off comes from the C11 entry (OD8). In the 2026-09-27 smoke test, thinking-off Qwen never
  called a tool (CONTEXT.md, "Behavioural evidence"); if OD8 chose thinking off and the smoke shows no
  tool calls, report it.
- `max_seqs` 4 on vLLM: a benchmark sweep running at the same time slows the demo (queueing). Never
  run a demo take during a sweep.
- `tmux send-keys` with nested quotes: test `demo_tmux.sh` with `--decider stub` first.
- Never print keys or Wi-Fi details in a pane (S12); the panes are filmed.

**Stop-and-ask conditions.** OD8's model is not a `vllm` entry (ROSA in `rosa-ros2` has no Anthropic
client and GPT-6 models need the Responses API for tools while reasoning, README C11): ask Xiaohui
whether the demo uses Qwen3.5 anyway (recommended, with the latency stated) or whether to build an
OpenAI Responses client into the demo (a new dependency in the course container). Also stop if the
smoke's first step overflows the context window (the D10 estimate is ≈ 7.8k tokens trimmed, ≈ 13.8k
stock, before tool turns).

**Estimated effort.** S.

**AI-disclosure note.** New files carry `AI-assisted: <model> via <tool>, <date>: <what>.`;
`rosa_decider.py` adds `Derived from: discussions/module4/rosa_agent_l2.py (McpOnlyROSA, build_llm,
json_tool_errors; reimplemented)`; `demo_capture.sh` adds `Derived from:
discussions/module5/tools/m5-frames.sh (pattern)`.

---
### M6.T4 — Demo script and filming: explore, return to start, go to a named beacon, refuse "follow that person"; time-lapse video

**Scope note.** This reserved task writes the demo script, the shot list, the time-lapse policy and
the take rules, chooses the demo world, and runs the whole script once in the kinematic simulator with
the real model (the dry run). The filming and the time-lapse video that the title names are carried
out in M6.T10 (simulation take), M6.T3 (car take) and M6.T11–T16 (video), each sized for one session.

**Why.** The demo script is fixed in the proposal talk track: "an unseen arena of 10 to 16 wall tags:
BeaconMind explores and maps the beacons, returns to start, drives to a named beacon, and refuses a
request such as 'follow that person', in Isaac Sim and on the car; the video will be time-lapsed
because the robot stops to think" (`proposal-talk-track.md` lines 61–64). A dry run in kinsim measures
how long each segment takes and shows whether the script works before Isaac or the car is involved.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M6.T8 done | task | `grep -E '^\| M6\.T8 ' course-project/plan/M6-demo-presentation.md` (Mac) | `done` |
| M2.T2 done (world generator) | task | `grep -E '^\| M2\.T2 ' course-project/plan/M2-sim-mvp.md` (Mac) | `done` |
| vLLM serving | service | `curl -sf http://127.0.0.1:8000/v1/models` (Spark host) | lists `Qwen/Qwen3.5-35B-A3B` |
| No benchmark sweep running | service | `pgrep -af "beaconmind.harness" \|\| echo clear` (Spark host) | `clear` |

**Inputs.** AGENT-DESIGN D2 (missions, operator requests, refuse and ask), D3 (arena), D7 step 7
(row 0, row 1b); README C7, C10.5, C10.6; this file's M6-C6, M6-C7, M6-C8, MD4;
`proposal-talk-track.md` lines 61–75; `discussions/module5/DESIGN.md` §3 and
`discussions/module5/talk-track.md` (how the last filmed take was planned and assembled).

**Steps.**
1. Mac: write **`demo/choose_world.py`**, CLI
   `python3 -m beaconmind.demo.choose_world --seeds 3000-3009 --condition duplicated --out-dir <data>/worlds --n 2`.
   For each seed in order it calls the M2.T2 generator and checker and keeps a seed when (a) the checker
   passes (every D3 constraint), (b) `duplicates` has at least one pair, and (c) the seed is outside the
   dev (1000–1099) and test (2000–2199) ranges of C7 (assert this; it guards against a typo). It writes
   the kept worlds as `<out-dir>/sim-dup-s<seed>.json` and prints `take_world <world_id>` and
   `dryrun_world <world_id>` for the first two kept seeds. **The take world is never run before the
   take** (that is what "unseen" means here); the dry run uses the second world.
2. Spark host: run it with the host venv:
   `cd ~/Projects/EN.665.715/course-project && ~/.venvs/beaconmind/bin/python -m beaconmind.demo.choose_world --seeds 3000-3009 --condition duplicated --out-dir data/worlds --n 2`.
   If fewer than two seeds qualify → stop and ask (options: widen to 3010–3019, or accept a world
   without a duplicated pair, which removes the duplicated-ID moment from the demo).
3. Mac: put the two seeds and world ids into `configs/demo_script.json` → `sim_world.chosen_seed`,
   `sim_world.world_id`, and two new fields `sim_world.dry_run_seed`, `sim_world.dry_run_world_id`
   (add them to `bm.demo_script-1.schema.json`). Copy both world JSON files into
   `evidence/M6/M6.T4/worlds/` (they are small).
4. Mac: write **`course-project/presentation/demo-script.md`** with these sections:
   - **Purpose and honesty rules.** The demo is ROSA in `rosa-ros2` (D10), demo-only, not
     benchmark-comparable. Every take is logged in `takes.md`. Footage is never spliced across takes
     without a visible card. Every sped-up interval shows its speed (×N). Simulation footage is labelled
     "Isaac Sim re-render of the logged ground truth" (MD5). Success is decided from ground truth, not
     from the agent's claim (C10.5). The one refusal shown is one sample; the slides give the request
     suite's rate (M4.T14, through `report/generated/numbers.json`).
   - **Segments** (table): segment, mission and request text, D7 rows that apply (row 1b for the
     request; E1–E5 for EXPLORE; rows 3–4 for the navigation missions), what the viewer should see,
     success rule (M6-C6), steps and wall time measured in the dry run (step 7).
   - **Why the requests are sent while the previous mission is still set** (the D7 row-0 note in M6-C7).
   - **Simulation filming plan:** the take runs unattended (M6.T10); the picture is re-rendered
     afterwards (M6.T13) from a fixed oblique camera over the arena; the terminal panes are captured at
     2 Hz.
   - **Car filming plan:** a phone on a tripod, as high as safely possible (a stepladder or a shelf,
     never above the arena on anything that can fall in), framing the whole arena and nothing personal
     (S10); 1080p, 30 fps; one continuous clip per segment; the terminal captured at 2 Hz; a clap at the
     start of each clip; Xiaohui stays outside the arena with the battery switch and the STOP hotkey in
     reach (S7). Data governance: the robot's camera frames go only to the local model (L8); the phone
     clip shows only the arena.
   - **Time-lapse policy:** the M6-C8 speeds, why (motion at real speed so the robot's behaviour is
     judged honestly; thinking compressed with its real duration printed in the terminal panel), and
     the target length from `DELIVERABLES.md`.
   - **Narration outline** (beats only; M6.T16 writes the words): the problem in one line; what the
     panels show; the ReAct loop on one step (OBSERVATION → ACTION/RESULT → REPORT → CHECK → move); the
     duplicated-ID moment if it occurs; the return; the go-to; the refusal and the zero moves after it;
     the honesty card; the disclosure.
5. Mac: write **`course-project/presentation/takes.md`** with the header row
   `| Take | Session id | Source | Date | Model (key, thinking) | ROSA mode | explore | return | goto | refuse | p95 latency (s) | Kept? | Reason | Notes |`
   and the rule: a take is listed the moment it starts, including aborted ones.
6. Spark host: **dry run** on the dry-run world (several hours, unattended):
   ```bash
   cd ~/Projects/EN.665.715/course-project && \
   S=$(~/.venvs/beaconmind/bin/python -m beaconmind.demo.new_session --source kinsim --label dryrun \
       --world data/worlds/<dry_run_world_id>.json --script configs/demo_script.json \
       --decider rosa --model-key <OD8 key> --rosa-mode <MD1> | tail -1)
   bash tools/demo_tmux.sh "$(basename "$S")" kinsim rosa && tmux send-keys -t bmdemo:demo.0 Enter
   ```
   Add the take row to `takes.md` (`Take` = `dry`). Check progress every 30–60 min with
   `tail -n 3 "$S/trace-runner.jsonl"` and `cat "$S/segments.json"`. If the runner stops with an
   infrastructure error (not a model decision), fix it (at most two attempts, §1.4 item 4) and restart
   from scratch.
7. Spark host, after the run: score it first
   (`docker exec -w /workspace/course-project/beaconmind beaconmind-ros python3 -m beaconmind.demo.score --session /workspace/course-project/data/demo/$(basename "$S")`),
   then write `evidence/M6/M6.T4/dryrun-summary.md` from `segments.json` and the traces, with real
   numbers only: per segment the outcome, steps, wall time, moves, p50/p95 decision
   latency, violations; and an **output-length estimate** for the time-lapse:
   ```bash
   ~/.venvs/beaconmind/bin/python - "$S" <<'EOF2'
   import json, sys, pathlib
   s = pathlib.Path(sys.argv[1]); ev = [json.loads(l) for f in ("trace-runner.jsonl", "trace-env.jsonl")
        for l in (s / f).read_text().splitlines() if l.strip()]
   moves = sum(e["duration_s"] for e in ev if e["kind"] == "move_end")
   steps = sum(1 for e in ev if e["kind"] == "step_start")
   print(f"steps {steps}  real move time {moves:.0f} s  estimate {moves + 2.5 * steps:.0f} s at think_max_out_s 2.5")
   EOF2
   ```
   Paste the printed line. If the estimate exceeds `video_limit_s` from `DELIVERABLES.md` for the
   simulation part (default: about half the limit), note it; M6.T11's fitting step handles it.
8. Mac: fill the "steps and wall time" column of `demo-script.md` from the summary.
9. Mac: **report to Xiaohui** and ask only if something failed: if a segment failed in the dry run, the
   options are (a) keep the script and world and let the take show what happens (default, honest),
   (b) change the take world (MD4: allowed only with Xiaohui's approval, and the honesty card then says so),
   (c) change a DV or the prompt (a design change, README §1.4 item 6; not for the demo's sake alone).
10. Mac: status table, `CONTEXT.md`.

**Deliverables.** `course-project/beaconmind/src/beaconmind/demo/choose_world.py`;
`course-project/configs/demo_script.json` (seeds filled) and its schema update;
`course-project/presentation/demo-script.md`; `course-project/presentation/takes.md`;
`course-project/beaconmind/tests/test_demo_choose_world.py`.

**Tests.**
- `tests/test_demo_choose_world.py`:
  - `test_picks_first_two_passing` — with a monkeypatched generator/checker where seeds 3000 and 3002
    fail, the chosen pair is (3001, 3003).
  - `test_rejects_dev_and_test_ranges` — `--seeds 1000-1001` raises `ValueError`.
  - `test_script_file_valid` — `configs/demo_script.json` validates against its schema; segments are
    explore, return, goto, refuse in that order; return, goto and refuse use `"mission": "carry"`;
    refuse has `max_steps` 3 and `expect.moves_after_answer` 0; `request_repeat_max` is 3; the two
    seeds are in 3000–3009 and differ.
- Command → expected: Mac `../.venv/bin/python -m pytest -q tests/test_demo_choose_world.py` → `3 passed`.
- Smoke test: the dry run (step 6) is the smoke. Pass = all four segments ended (any outcome) with no
  infrastructure error, and `segments.json` has four entries. The outcome is reported, not judged.

**Acceptance criteria.**
- [ ] Two demo worlds chosen by the rule; seeds recorded in `demo_script.json`; worlds in evidence.
- [ ] `demo-script.md` and `takes.md` written; the dry-run row is in `takes.md`.
- [ ] `3 passed`; the dry run completed all four segments; `dryrun-summary.md` has real numbers.
- [ ] Any failed segment was reported to Xiaohui and their choice recorded in `CONTEXT.md`.

**Evidence to save** (`evidence/M6/M6.T4/`): `worlds/`; `choose-world.txt` (the CLI output);
`dryrun-summary.md`; `dryrun/` (session JSON files, `segments.json`, traces, run logs).

**Pitfalls and known gotchas.**
- Do **not** send an operator request with mission `REPORT` or `STOP`: D7 row 0 answers first and the
  request is never read (M6-C7).
- In the 2026-09-27 smoke test, loop closure "practically never triggers" in a 2.25 m arena with the
  current DVs, and EXPLORE ended after about 51 steps on average (AGENT-DESIGN D8 notes). Do not promise
  a loop closure in the narration.
- The 2026-09-27 smoke refused 6 of 10 unsafe requests; the refusal may fail. That is a result, not a
  bug to hide.
- kinsim results are labelled `kinsim` and never shown as Isaac or car footage.

**Stop-and-ask conditions.** Fewer than two qualifying seeds; a failed dry-run segment (step 9); the
dry run's p95 decision latency above 60 s (the talk track's gate applies to "any model run in closed
loop, including the demo"): report it and ask whether to keep the model setting (the gate is then
stated as missed in the video and slides) or to switch to the OD8 alternative.

**Estimated effort.** S (plus several hours of unattended model time).

**AI-disclosure note.** `choose_world.py` and the test: `AI-assisted: …`. `demo-script.md` and
`takes.md` end with a "Generative-AI disclosure" paragraph naming the model and what it drafted;
Xiaohui owns the takes.

---

### M6.T9 — Isaac twin hookup: 3-step ROSA smoke and an estop check in the twin

**Why.** README §3.3 makes the ROSA demo depend on the twin (M2.T5). Before a take that runs for hours,
prove in three steps that ROSA → `bm-tools` → environment server → `bm_sim_pico` → Isaac moves the
simulated car, that ground truth comes back, and that a stop request halts a move and latches (D6).

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M6.T8 done | task | `grep -E '^\| M6\.T8 ' course-project/plan/M6-demo-presentation.md` (Mac) | `done` |
| M2.T5, M2.T6 and M2.T17 done | task | `grep -E '^\| M2\.T(5\|6\|17) ' course-project/plan/M2-sim-mvp.md` (Mac) | all three `done` |
| One kit process at most | service | `pgrep -af 'kit/kit\|python.sh' \|\| echo clear` (Spark host) | `clear` |
| vLLM at GPU share 0.60 | service | `docker inspect vllm-rosa --format '{{.Args}}' \| grep -oE "gpu-memory-utilization[= ][0-9.]+"` (Spark host) | one line ending in `0.6` or `0.60`, for example `gpu-memory-utilization 0.60` (README L5: vLLM at 0.60 and Isaac run together); anything higher → stop and ask, never restart vLLM yourself mid-task |
| Latch clear | state | `test ! -e ~/Projects/EN.665.715/course-project/data/LATCH && echo clear` (Spark host) | `clear` |

**Inputs.** `plan/M2-sim-mvp.md` M2.T5 and M2.T6 (their run commands and evidence); README C2, C5
item 5, C8, C12, L5; AGENTS.md §7.4 (Isaac Sim row: headless only, shutdown hang, UDP-only bridge).

**Steps.**
1. Spark host: free-memory check: `free -g | head -2; nvidia-smi --query-gpu=memory.used --format=csv`.
   Record both. vLLM at 0.60 plus Isaac was measured at ~92 GB used / 29 GB free (AGENTS.md §7.4).
2. Mac: **find the twin's launch commands.** Read M2.T5's and M2.T6's evidence and `CONTEXT.md` for the
   exact commands that start the headless twin with a given world, `bm_sim_pico`, and the perception
   and observation-builder nodes. Copy them into `evidence/M6/M6.T9/launch-commands.md`. If they are
   not written down anywhere → stop and ask (do not guess launch commands).
3. Spark host: use a **dev** world for this smoke (never the take world). M2.T2 already generated the
   dev worlds; check, and generate only if missing, with M2.T2's CLI:
   ```bash
   cd ~/Projects/EN.665.715/course-project && ls data/worlds/sim-dup-s1000.json || \
     ~/.venvs/beaconmind/bin/python -m beaconmind.worlds generate --condition duplicated --seeds 1000-1000 --out data/worlds
   ~/.venvs/beaconmind/bin/python -m beaconmind.worlds check data/worlds/sim-dup-s1000.json
   ```
   Expected: `OK sim-dup-s1000`. If the CLI's flags differ, read
   `~/.venvs/beaconmind/bin/python -m beaconmind.worlds generate --help` and use the real flags.
4. Spark host (only if Xiaohui chose the MD2 alternative): check that the ROS environment imports in
   `rosa-ros2`:
   `docker exec rosa-ros2 bash -lc 'source /opt/ros/humble/setup.bash && PYTHONPATH=/workspace/course-project/beaconmind/src python3 -c "import beaconmind.envs.ros_env as m; print(m.__file__)"'`.
   If it fails, report the missing module and fall back to the MD2 default (tell Xiaohui).
5. Spark host: start the twin with that world in a tmux session `bmtwin` (window `twin`), using the
   M2.T5 command wrapped in `timeout --kill-after=60 <seconds>`; start the M2.T6 bring-up in window
   `ros` inside `beaconmind-ros`.
6. Spark container `beaconmind-ros`: confirm the graph:
   `docker exec beaconmind-ros bash -lc 'source /opt/ros/humble/setup.bash && ros2 topic list | grep -E "^/(pico|beaconmind|ground_truth|estop)"'`.
   Expected: `/pico/move/cmd`, `/pico/move/result`, `/pico/state`, `/beaconmind/observation`,
   `/ground_truth/pose`, `/estop` (C12). Missing topics → stop and ask (§1.4 item 3).
7. Spark host: create the session and start the panes:
   ```bash
   cd ~/Projects/EN.665.715/course-project && \
   S=$(~/.venvs/beaconmind/bin/python -m beaconmind.demo.new_session --source sim --label smoke3 \
       --world data/worlds/sim-dup-s1000.json --script configs/demo_script.json --decider rosa \
       --model-key <OD8 key> --rosa-mode <MD1> | tail -1)
   bash tools/demo_tmux.sh "$(basename "$S")" ros rosa "--max-steps 4"
   ```
   Do **not** press Enter in `demo.0` yet: step 8 arms the estop check first.
8. **Estop check** (Spark host). In window `bmdemo:ctl`, arm the deterministic estop, which fires
   0.5 s after the next forward move starts (M6.T7 step 6):
   `docker exec -w /workspace/course-project/beaconmind beaconmind-ros python3 -m beaconmind.demo.estop --session /workspace/course-project/data/demo/$(basename "$S") --reason "M6.T9 estop check" --on-next-move FORWARD --delay-s 0.5 --wait-max-s 3600`
   then press Enter in pane `demo.0` (`tmux send-keys -t bmdemo:demo.0 Enter`). The estop fires during
   the first forward move. If the model makes no forward move within the 4 steps, the command prints
   "no matching move started" after the wait: record it, re-run this step with `--max-steps 8` once,
   and if there is still no forward move, stop and ask.
   After the runner has stopped (latched), send the **project's own out-of-band STOP** once while idle,
   to confirm the simulated Pico latches from it too. Default (works without M3.T13):
   `docker exec beaconmind-ros bash -lc 'source /opt/ros/humble/setup.bash && ros2 topic pub --times 3 /estop std_msgs/msg/Bool "{data: true}"'`.
   If M3.T13 is `done`, use its hotkey instead (`bm-estop` in a tmux window, as in M3.T13 step 6) and
   press SPACE once.
9. Spark host: when the runner stops (latched), record what happened, then clear the latch with the
   operator command `bm-clear-latch` (C5 item 5; this is a `sim` session, so the latch is the global
   `data/LATCH`, M6-C1). Verify the command first:
   `docker exec beaconmind-ros bash -lc 'bm-clear-latch --help'` (or `~/.venvs/beaconmind/bin/bm-clear-latch --help`
   on the host). If neither exists → stop and ask; do not `rm` the latch file on the Spark. Run it as
   `bm-clear-latch --operator <name>` (M2.T1's CLI; there is no interactive variant), and tell Xiaohui you
   cleared a simulation latch.
10. Spark host: `touch "$S/term/STOP"`; `tmux kill-session -t bmdemo`; stop the twin (`Ctrl-C` in its
    window; if it hangs after its last line, `pkill -9 -f <the twin script name>`, AGENTS.md §7.4);
    stop the bring-up.
11. Spark host: run the checks (Tests), copy the small files to `evidence/M6/M6.T9/smoke3/`, pull to
    the Mac; status table; `CONTEXT.md` (what was left running: vLLM).

**Deliverables.** No new code (fixes to M6.T2/T7/T8 code if the smoke finds bugs, each with a
regression test). `evidence/M6/M6.T9/launch-commands.md`.

**Tests.**
- Unit tests: none new; any fix adds a regression test to the matching `test_demo_*.py` and the full
  `tests/test_demo_*.py` set must still pass on the Mac and in `beaconmind-ros`.
- Smoke test (Spark): pass when all hold:
  1. Every `move` that returned `done` before the estop changed the ground-truth pose (run log
     `gt_pose_map`, this step against the next) by ≥ 0.05 m (forward) or ≥ 10° (turn); and the aborted
     forward move displaced the car by more than 0.01 m (motion really started) — read from
     `/ground_truth/pose` via the next observe's `gt_pose_map`, or, if the runner stopped before
     another observe, from the environment server's `MOVE … ->` line (`gt +<m>`).
  2. `trace-env.jsonl` has an `estop` event during a move (between its `move_start` and `move_end`),
     `data/LATCH` existed afterwards, and the aborted move's ground-truth displacement is smaller than
     its commanded distance (0.25 or 0.10 m).
  3. The runner ended the session at the estop's step (`segments.json` last entry `ended_by` `latch`;
     the runner pane printed `session ended`), and `trace-env.jsonl` has no `move_start` after the
     `estop` event. (That a latched environment refuses a move is proven by the M6.T7 unit test
     `test_latch_refuses_execute`; cite it in `summary.md`.)
  4. The project's out-of-band STOP also latched the simulated Pico (`/pico/state` `armed` 0, or what
     M2.T5's `bm_sim_pico` reports; record it).
  5. The environment server published the heartbeat while the model was thinking: during the first
     step's think, `docker exec beaconmind-ros bash -lc 'source /opt/ros/humble/setup.bash && timeout 10 ros2 topic hz /pico/heartbeat'`
     reports an average rate between 9 and 11 Hz (C2: bridge → Pico at 10 Hz). Save it as
     `heartbeat.txt`. No heartbeat → stop and ask: on the car the watchdog would end every move
     (`link_lost`).
- Hardware tests: none (simulation).

**Acceptance criteria.**
- [ ] `launch-commands.md` holds the exact twin and bring-up commands used.
- [ ] Smoke checks 1–5 pass, with the numbers pasted in `evidence/M6/M6.T9/smoke3/summary.md`.
- [ ] The latch was cleared with `bm-clear-latch`, not by deleting the file.

**Evidence to save** (`evidence/M6/M6.T9/`): `memory.txt` (step 1); `launch-commands.md`;
`topics.txt` (step 6); `heartbeat.txt` (check 5); `smoke3/` (session JSON, traces, run log,
`summary.md`, the environment pane capture around the estop).

**Pitfalls and known gotchas.** Isaac's bundled FastDDS 2.6.10 must run **UDP-only** or the Humble
container receives nothing (README C12; AGENTS.md §7.4). Kit processes hang on shutdown: wrap in
`timeout --kill-after=60` and `pkill -9` (AGENTS.md §7.4). `./vllm-serve.sh stop` **removes** the
container (`discussions/module2/VIDEO-CAPTURE.md`, Preflight). Livestreaming is unsupported on aarch64,
so there is no viewport: judge motion from ground truth, not by looking.

**Stop-and-ask conditions.** Launch commands not documented (step 2); topics missing (step 6); the
estop does not stop the simulated move (check 2 fails): this is a safety-path failure, and the car take
(M6.T3) must not start until it is understood.

**Estimated effort.** S.

**AI-disclosure note.** Evidence narratives (`summary.md`, `launch-commands.md`) end with
`AI-assisted: <model> via <tool>, <date>: ran the smoke and wrote this summary from the real outputs.`

---

### M6.T10 — Simulation demo take in the Isaac twin

**Why.** The simulation half of the demo (README §3.1 M6 exit criterion; talk track "in Isaac Sim and
on the car"). Under the cut line this is the only demo take.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M6.T4 and M6.T9 done | task | `grep -E '^\| M6\.T(4\|9) ' course-project/plan/M6-demo-presentation.md` (Mac) | both `done` |
| Take world exists | file | `ls ~/Projects/EN.665.715/course-project/data/worlds/<take world_id>.json` (Spark host) | the file |
| Days left > 7 | calendar | `python3 -c "import datetime as d; print((d.date(2026,12,13)-d.date.today()).days)"` (Mac) | > 7 (README §3.4) |
| Free disk ≥ 50 GB | resource | `df -h ~ \| tail -1` (Spark host) | ≥ 50 G available |
| Plus every prerequisite row of M6.T9 | | | |

**Inputs.** `presentation/demo-script.md`; `presentation/takes.md`; `evidence/M6/M6.T9/launch-commands.md`;
this file's M6-C1 to M6-C7.

**Steps.**
1. Spark host: preflight, pasting each output into `evidence/M6/M6.T10/take<k>/preflight.txt`:
   memory (`free -g`, `nvidia-smi`), `pgrep` for kit processes (clear), `pgrep -af beaconmind.harness`
   (clear: no sweep), latch clear, vLLM answers a one-line request
   (`curl -s http://127.0.0.1:8000/v1/chat/completions -H 'Content-Type: application/json' -d '{"model":"Qwen/Qwen3.5-35B-A3B","messages":[{"role":"user","content":"Say OK."}],"max_tokens":400}' | head -c 300`).
2. Spark host: start the twin with the **take world** and the bring-up exactly as in
   `launch-commands.md`; confirm the topics (M6.T9 step 6).
3. Spark host: create the session (`--source sim --label take<k> --take <k> --world
   data/worlds/<take world_id>.json --decider rosa --model-key <OD8 key> --rosa-mode <MD1>`), start
   `tools/demo_tmux.sh <id> ros rosa`, and press Enter in pane `demo.0`. Add the take's row to
   `takes.md` now (status "running").
4. Spark host: monitor every 30–60 minutes (`tail -n 3 "$S/trace-runner.jsonl"`, `cat "$S/segments.json"`,
   `pgrep -af kit` still alive). Do not intervene in the agent's decisions. Intervene only for an
   infrastructure fault (twin or a container died, disk full): then `touch "$S/term/STOP"`, mark the
   take "aborted: <reason>" in `takes.md`, fix the fault (≤ 2 attempts), and start a **new** take from
   the beginning. **No resume in simulation:** a restarted twin puts the car back at the start pose, so
   a resumed take would not be one continuous run.
5. Spark host: when the runner prints `session ended`, `touch "$S/term/STOP"`, kill the tmux session,
   stop the twin (pkill if it hangs) and the bring-up.
6. Spark host: score the session
   (`docker exec -w /workspace/course-project/beaconmind beaconmind-ros python3 -m beaconmind.demo.score --session /workspace/course-project/data/demo/<id>`;
   it must print `schema ok`), run the checks (Tests) and write `evidence/M6/M6.T10/take<k>/summary.md` with the real
   numbers: per segment outcome, steps, wall time, moves, decision latency p50/p95, violations; whether
   a duplicated-ID tag was seen and how it was labelled (from the reports' `associations`); the refusal
   segment's decision and the moves after it (must be 0).
7. Mac: update `takes.md` (outcome columns, p95, "Kept?" empty until step 8).
8. **Choose the take** (default rule, no judgment): keep the **first take** that ran all four segments
   without an infrastructure fault, whatever the agent's outcomes. Run at most **3 takes** without
   asking (each costs hours). Keeping a later take than the first complete one needs Xiaohui's approval
   and is stated on the honesty card ("take k of n; the other takes are listed in takes.md").
9. Mac: pull evidence (`tools/pull_evidence.sh M6 M6.T10`); status table; `CONTEXT.md` with the kept
   session id (M6.T13 and M6.T14 need it) and what was left running.

**Deliverables.** A session folder on the Spark (`data/demo/<id>/`, git-ignored); updated
`presentation/takes.md`; `evidence/M6/M6.T10/take<k>/`.

**Tests.**
- Unit tests: none new.
- Smoke/acceptance checks on the session (Spark host):
  - `segments.json` has 4 entries, each with `scored: true`, `success` true/false (not null:
    simulation has ground truth) and an `ended_by` value from the M6-C6 list.
  - Every run-log line has `error` null, or the take is marked aborted.
  - `obslog.jsonl` has a header and a footer; its step count equals the number of run-log lines.
  - `trace-env.jsonl` `move_end` count equals the number of executed moves in the run logs.
  - `term/` holds captures spanning the whole session (first `T=` ≤ the first `step_start`, last `T=` ≥
    the last `llm_end`).
  - The refuse segment's `moves_after_answer` is 0 (whether or not the agent refused; a nonzero value
    is the stop-and-ask below).
- Hardware tests: none.

**Acceptance criteria.**
- [ ] A kept take exists, chosen by the step-8 rule, with all checks above passing.
- [ ] `takes.md` lists every take started, including aborted ones.
- [ ] `summary.md` contains only numbers read from the session files.

**Evidence to save** (`evidence/M6/M6.T10/take<k>/`): `preflight.txt`; `summary.md`; `segments.json`;
`session.json`; both traces (if < 1 MB each; otherwise a `wc -l` and the first and last 50 lines).

**Pitfalls and known gotchas.** A sweep and the take must not share vLLM (latency inflation, `max_seqs`
4). Keep the Spark's ssh session out of the take's path: everything runs in tmux. The twin may need a
first-run asset pull (5–15 min; VIDEO-CAPTURE.md "Expectations").

**Stop-and-ask conditions.** Three takes without a complete one; a fourth take; the refuse segment
executed a move (the model complied with the unsafe request; the validator blocks only moves that break
its safety flags, so it cannot catch this): report it as a finding, keep the footage honest, and ask
whether to retake.

**Estimated effort.** S of attended work (preflight, start, checks), plus hours unattended.

**AI-disclosure note.** `summary.md` and the `takes.md` disclosure paragraph name the model and what it
did (ran the take, wrote the summary).

---
### M6.T11 — Video logic: edit decision list, time-lapse fitting, frame times, render plan, ffmpeg plan

**Why.** The robot thinks for tens of seconds per step and moves for one or two (talk track: "the
video will be time-lapsed because the robot stops to think"). The edit must come **from the trace**, not
from hand trimming, so that every second of output maps to a known wall-clock interval and the speed
shown on screen is true. This task is pure Python and fully unit-tested on hand-computed fixtures; it
uses the M6.T7 stub session as its real-data smoke.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M6.T7 done (trace format, stub session) | task | `grep -E '^\| M6\.T7 ' course-project/plan/M6-demo-presentation.md` (Mac) | `done` |
| Stub session folder | file | `ls ~/Projects/EN.665.715/course-project/data/demo/ \| grep stub` (Spark host) | at least one folder |

**Inputs.** This file's M6-C5, M6-C8; README C1 (frames; `T_map←world`), C8, C9.2;
`discussions/module2/VIDEO-CAPTURE.md` (ffmpeg flags that worked: libx264, yuv420p, even-size pad);
`discussions/module5/talk-track.md` "Assembling the video" (cue-sheet idea).

**Steps.**
1. Mac: write **`configs/demo_video.json`** exactly as M6-C8, with `target_total_s` = `video_limit_s`
   − 15 from `presentation/DELIVERABLES.md` (M6-C8; or 300 if M6.T1 is not done, and then record
   "provisional target_total_s" in `CONTEXT.md` so M6.T14 re-checks it).
2. Mac: write **`demo/edl.py`** (standard library only):
   ```python
   @dataclass(frozen=True)
   class Seg:
       t0: float; t1: float; kind: str; speed: float; segment: str; step: int | None
   def classify(events: list[dict]) -> list[tuple[float, float, str, str, int | None]]
   def build_edl(events: list[dict], speeds: dict) -> list[Seg]
   def frame_counts(edl: list[Seg], fps: int) -> list[int]
   def frame_times(edl: list[Seg], fps: int) -> list[tuple[int, float, Seg]]
   def output_duration(edl: list[Seg], fps: int) -> float
   def fit_to_target(events: list[dict], speeds: dict, fps: int, target_s: float) -> tuple[list[Seg], dict, bool]
   def badge(seg: Seg) -> str
   def cue_sheet(edl: list[Seg], fps: int, events: list[dict]) -> list[dict]
   def card_budget(cards_s: dict, with_car: bool) -> float          # M6-C8 "Card budget"
   def segment_frame_ranges(edl: list[Seg], fps: int) -> dict[str, tuple[int, int]]   # [first, last+1) per segment
   ```
   Rules (write them in the docstring):
   - **classify**: over `[session_start, session_end]`, each instant is `move` if inside a
     `move_start`–`move_end` window; else `observe` if inside `step_start`–`observation_ready`; else
     `think` if inside `llm_start`–`llm_end`; else `idle`. Adjacent pieces with the same kind and step
     merge. Pieces shorter than 0.01 s are dropped. The `segment` comes from the latest
     `segment_start`.
   - **speed**: `move` → `speeds.move`; `observe` → `speeds.observe`; `idle` → `speeds.idle`; `think`
     → `max(speeds.think_min, duration / speeds.think_max_out_s)`.
   - **frame_counts**: `N = max(1, int(duration / speed * fps + 0.5))` (round half up; never Python's
     `round`, which rounds half to even).
   - **frame_times**: frame `i` of a piece is at wall time `t0 + (i + 0.5) * (t1 − t0) / N`.
   - **fit_to_target**: try `think_max_out_s` in `[2.5, 2.0, 1.5, 1.0, 0.6]`, then `observe` in
     `[4, 8, 16]`, then `idle` 60; return the first policy whose `output_duration` ≤ `target_s`, the
     policy, and whether it fits. Never change `move` (motion is always real time).
   - **badge**: `"real time"` if `speed < 1.5`, else `"×<int(speed + 0.5)>"`.
   - **cue_sheet**: output time (s) of every `segment_start`, `operator_request` and `report` whose
     decision is `DONE`, `REFUSED` or `ASK` — for narration (M6.T16).
3. Mac: write **`demo/render_plan.py`**:
   ```python
   def map_to_world(pose_map: dict, start_pose_world: dict) -> dict   # C1: T_world<-map = start pose
   def interp_pose(a: dict, b: dict, f: float) -> dict                # linear x, y; shortest-arc yaw
   def pose_at(t: float, obs_times: list[float], gt_by_step: dict[int, dict],
               windows: list[tuple[float, float, int]]) -> tuple[dict, bool]   # (map pose, interpolated?)
   def default_camera(world: dict) -> dict      # eye (cx, cy − 0.9·Ly, 2.6), target (cx, cy, 0); oblique, never straight down
   def build_render_plan(session_dir: Path, edl: list, fps: int, world: dict) -> dict   # bm.render_plan/1
   ```
   `pose_at` rule: during the move window of step k (between its `move_start` and `move_end`),
   interpolate from step k's ground truth to step k+1's with `f = (t − move_start)/(move_end −
   move_start)`; after that move ends, use step k+1's ground truth; before any move in step k, use step
   k's. If step k+1 has no ground truth (the last step, or `gt_pose_map` null), hold step k's pose with
   `interpolated: false`. Ground truth per step comes from the run-log lines' `gt_pose_map` (C8), the start pose from
   `world.json`. The plan file `video/render_plan.json`:
   `{"schema": "bm.render_plan/1", "session_id", "world_id", "fps", "width": 1152, "height": 648,
   "camera": {"eye": [x, y, z], "target": [x, y, z]}, "frames": [{"i", "t_wall", "segment", "step",
   "x_m", "y_m", "yaw_deg", "interpolated", "badge"}]}` in the **world** frame. Label honestly: frames
   with `interpolated: true` are drawn between logged stops.
4. Mac: write **`demo/ffplan.py`** (builds argument lists only; never a shell string):
   ```python
   def compose_cmd(ffmpeg: str, main: str, main_is_pattern: bool, panel_pattern: str, term_pattern: str,
                   fps: int, layout: dict, crf: int, out: str) -> list[str]
   def phone_piece_cmd(ffmpeg: str, phone: str, start_s: float, dur_s: float, speed: float, n_frames: int,
                       fps: int, size: tuple[int, int], out: str) -> list[str]
   def card_clip_cmd(ffmpeg: str, png: str, seconds: float, fps: int, out: str) -> list[str]
   def write_concat_list(paths: list[str], list_file: str) -> None
   def concat_cmd(ffmpeg: str, list_file: str, out: str) -> list[str]
   def mux_narration_cmd(ffmpeg: str, video: str, audio: str, out: str) -> list[str]
   ```
   `compose_cmd`'s filter: `[0:v]scale=1152:648,setsar=1[m];[1:v]scale=768:648,setsar=1[p];[2:v]scale=1920:432,setsar=1[t];[m][p][t]xstack=inputs=3:layout=0_0|1152_0|0_648,format=yuv420p[v]`
   (numbers from `layout`), then `-map [v] -r <fps> -c:v libx264 -crf <crf> -pix_fmt yuv420p`. Image
   sequences use `-framerate <fps> -i <dir>/f%06d.png`. `phone_piece_cmd`:
   `-ss <start> -i <phone> -t <dur> -vf "setpts=(PTS-STARTPTS)/<speed>,fps=<fps>,scale=<w>:<h>:force_original_aspect_ratio=decrease,pad=<w>:<h>:(ow-iw)/2:(oh-ih)/2" -frames:v <n> -an -c:v libx264 -crf 18 -pix_fmt yuv420p <out>`.
   `mux_narration_cmd`: `-i <video> -i <audio> -map 0:v -map 1:a -c:v copy -af apad -c:a aac -b:a 160k -shortest <out>`.
   `apad` pads the narration with silence to infinity and `-shortest` then stops at the **video's**
   end, so a narration that is a little short can never cut off the final disclosure card (without
   `apad`, `-shortest` would end the file when the audio ends).
5. Mac: write **`demo/video_cli.py`** with the subcommand `plan`:
   `python3 -m beaconmind.demo.video_cli plan --session <dir> [--target-s N]` → reads both traces and
   the run logs, runs `fit_to_target`, writes `video/edl.json` (pieces, counts, policy, `fits`),
   `video/render_plan.json`, `video/cues.csv` (`output_s,kind,segment,step,text`), and prints
   `pieces <n> frames <N> output <s> s fits <bool> policy <json>`. (M6.T12 and M6.T14 add subcommands.)
6. Mac: tests (below); then Spark host smoke on the stub session with the host venv:
   `~/.venvs/beaconmind/bin/python -m beaconmind.demo.video_cli plan --session data/demo/<stub id>`.
7. Mac: status table; `CONTEXT.md`.

**Deliverables.** `course-project/configs/demo_video.json`; `course-project/beaconmind/src/beaconmind/demo/edl.py`,
`render_plan.py`, `ffplan.py`, `video_cli.py`; schemas `bm.render_plan-1`, `bm.demo_video-1`; tests
`test_demo_edl.py`, `test_demo_render_plan.py`, `test_demo_ffplan.py`.

**Tests.** (fixture **F1**, a synthetic one-step trace, exactly these events and nothing else:
`session_start` 0, `segment_start` 0 (segment `explore`), `step_start` 0 (step 0), `observation_ready`
1, `llm_start` 1, `move_start` 5, `move_end` 7, `llm_end` 20, `session_end` 20.5; `speeds` = M6-C8;
`fps` 25. Fixture **F2**, for fitting: `session_start` 0, `segment_start` 0, `step_start` 0,
`observation_ready` 0, `llm_start` 0, `move_start` 60, `move_end` 62, `llm_end` 62, `session_end` 62,
which classifies into think [0, 60] and move [60, 62].)
- `tests/test_demo_edl.py`:
  - `test_classify_fixture` — pieces are observe [0, 1], think [1, 5], move [5, 7], think [7, 20], idle
    [20, 20.5].
  - `test_frame_counts_exact` — counts are 6, 13, 50, 41, 1 (total 111); the move piece has speed 1.0
    and the think pieces 8.0.
  - `test_frame_times_first` — the first frame's wall time is 1/12 s (0.0833…) and frame times strictly
    increase.
  - `test_fit_reduces_think_only` — F2 with `target_s` 4.0: at `think_max_out_s` 2.5 the output is
    63 + 50 = 113 frames = 4.52 s (does not fit); the returned policy has `think_max_out_s` 2.0 (think
    speed 30, 50 frames), total 100 frames = 4.0 s, `fits` true, and the move piece is still at speed
    1.0 with 50 frames.
  - `test_badge` — speed 1.0 → `real time`; 8.0 → `×8`; 16.4 → `×16`.
  - `test_card_budget` — with the M6-C8 `cards_s`: 44.0 with the car, 31.5 without.
- `tests/test_demo_render_plan.py`:
  - `test_map_to_world` — map pose (1, 0, 0°) with start (1.10, 0.95, 30°) → world (1.966, 1.450, 30.0)
    within 0.001.
  - `test_interp_shortest_arc` — yaw 170° to −170° at f 0.5 → ±180°.
  - `test_pose_at_window` — at the middle of a move window the pose is the midpoint of the two stops and
    `interpolated` is true; just after `move_end` it equals the next stop.
  - `test_plan_frame_count` — a `tmp_path` session with F1 as its traces, the C7 example world as
    `world.json` and one run-log line for step 0 with `gt_pose_map` (0, 0, 0): the plan has 111 frames,
    every frame holds the step-0 pose (no step 1 exists), and the file validates against
    `bm.render_plan-1`.
- `tests/test_demo_ffplan.py`:
  - `test_compose_layout` — the filter contains `xstack=inputs=3:layout=0_0|1152_0|0_648` and every
    element of the command is a `str` (no shell string).
  - `test_phone_piece` — for a think piece of 13.0 s at speed 8.0, fps 25 (41 frames by the
    `frame_counts` rule), start 100.0 s: the command has `-ss 100.0`, `-t 13.0`,
    `setpts=(PTS-STARTPTS)/8.0` and `-frames:v 41`.
  - `test_concat_list_format` — each line is `file '<absolute path>'`.
  - `test_mux` — the command contains `-c:v copy`, `apad` and `-shortest`.
- Command → expected: Mac `../.venv/bin/python -m pytest -q tests/test_demo_edl.py tests/test_demo_render_plan.py tests/test_demo_ffplan.py`
  → `14 passed` (6 + 4 + 4); Spark host venv → `14 passed`.
- Smoke (Spark host, stub session): `video_cli plan` prints `fits True` (stub sessions are short), and
  `video/render_plan.json` has as many frames as `edl.json`'s total.

**Acceptance criteria.**
- [ ] `14 passed` on the Mac and the Spark host.
- [ ] The stub-session plan exists and its frame count matches the EDL.

**Evidence to save** (`evidence/M6/M6.T11/`): `tests-mac.txt`; `tests-spark.txt`; `stub-plan.txt`
(the CLI's printed line and `head -c 2000 video/edl.json`).

**Pitfalls and known gotchas.** ffmpeg 7.0.2 rejects some implicit sizes (VIDEO-CAPTURE.md: `tile=6x0`
fails; give every size explicitly). Odd frame sizes break `yuv420p` (all layout sizes above are even).
Time stamps from different containers are comparable only because they share the host clock; phone
time is not (M6.T15 syncs it).

**Stop-and-ask conditions.** none beyond README §1.4.

**Estimated effort.** S.

**AI-disclosure note.** Each new file: `AI-assisted: <model> via <tool>, <date>: <what>.`;
`configs/demo_video.json` gets its line in `configs/README.md`.

---

### M6.T12 — Video renderers: terminal frames, belief panel, top-down view, cards

**Why.** The composite (M6-C8 layout) needs three image streams per output frame and four kinds of
title cards. The **belief panel** is what makes BeaconMind's SLAM visible: the agent's believed pose and
beacon map next to the ground truth. The **top-down view** is the MD5 fallback main view if the Isaac
re-render fails, and the view used in the milestone smoke test. The **terminal renderer** re-draws the
captured panes as clean, readable frames (Module 5 method, `discussions/module5/tools/m5-render.py`) and
refuses to draw any frame that contains a secret (S12).

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M6.T11 done | task | `grep -E '^\| M6\.T11 ' course-project/plan/M6-demo-presentation.md` (Mac) | `done` |
| Pillow in the venvs | package | `../.venv/bin/python -c "import PIL; print(PIL.__version__)"` (Mac, in `beaconmind/`) and `~/.venvs/beaconmind/bin/python -c "import PIL; print(PIL.__version__)"` (Spark host) | a version; if missing, step 1 |

**Inputs.** `discussions/module5/tools/m5-render.py` (colours, wrap, pane layout); README C1, C6
(report fields), C7 (world tags); this file's M6-C5, M6-C8.

**Steps.**
1. Mac: add an extra `video = ["Pillow"]` to `course-project/beaconmind/pyproject.toml`; install it in
   both venvs (`course-project/.venv/bin/pip install -e "course-project/beaconmind[dev,video]"` on the
   Mac; `~/.venvs/beaconmind/bin/pip install -e "$HOME/Projects/EN.665.715/course-project/beaconmind[dev,b1,metrics,video]"`
   on the Spark host); pin the printed Pillow version in `pyproject.toml` (README L3).
2. Mac: write **`demo/fonts.py`**: `mono_font(size) -> ImageFont` trying, in order,
   `/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf` (Spark, verified 2026-10-05),
   `/System/Library/Fonts/Menlo.ttc` (Mac), then `ImageFont.load_default()`; `sans_font(size)` likewise
   with `DejaVuSans.ttf` and `/System/Library/Fonts/Helvetica.ttc`.
3. Mac: write **`demo/term_render.py`**:
   ```python
   SECRET_RE = re.compile(r"sk-[A-Za-z0-9_-]{8,}|api_key|API_KEY=|password|ssid|PRIVATE KEY", re.I)
   class SecretInFrame(Exception): ...
   def load_captures(term_dir: Path) -> list[tuple[float, Path, Path]]   # (T, runner_txt, env_txt), sorted
   def select_capture(captures, t: float)                                 # largest T <= t, else the first
   def line_style(line: str) -> tuple[tuple[int, int, int], bool]         # colour, bold, by tag
   def render_term_frame(runner_lines: list[str], env_lines: list[str], header: str,
                         size=(1920, 432)) -> Image.Image                  # raises SecretInFrame
   ```
   Layout: a 26 px header (session, segment, speed badge, the **main-view label** — "main view: Isaac Sim
   re-render of logged ground truth, interpolated between stops", "main view: 2D view of logged ground
   truth" or "main view: phone camera" — passed in by `video_cli render` from the session's `source` and
   the MD5 choice, and "terminal: spark-2a60 / rosa-ros2 + beaconmind-ros"),
   then the runner pane (1280 px wide, last lines that fit) and the environment pane (640 px). Tag
   colours (dark background `(28, 36, 45)`): `═══` and `OPERATOR` bold white; `OBSERVATION` light blue;
   `ACTION` green; `RESULT` light grey; `REPORT` amber; `NOTE` dim; `CHECK` red if it contains
   "violation" counts > 0, else dim; environment `MOVE` green, `ESTOP` bold red.
4. Mac: write **`demo/belief_panel.py`**:
   ```python
   def world_to_px(x: float, y: float, world: dict, size: tuple[int, int], margin: int = 40) -> tuple[int, int]
   def render_panel(world: dict, start_pose_world: dict, report: dict | None, gt_pose_map: dict | None,
                    trail_est: list[dict], trail_gt: list[dict], header: str, size=(768, 648)) -> Image.Image
   ```
   Draw (equal aspect, y up): the arena rectangle; every true tag as a small grey square on its wall
   with its id; the believed beacons (map frame → world with `render_plan.map_to_world`) as circles —
   confirmed filled blue, tentative hollow blue, `suspect` red outline — labelled with their `B…`
   label; the true pose as a black triangle and the believed pose as a blue triangle; both trails; a
   legend; the header "Belief (blue) vs ground truth (black) · step <n> · <pose_source>". With no
   ground truth (`gt_source: none`), omit the black items and say "no ground truth" in the header.
5. Mac: write **`demo/topdown.py`**: `render_topdown(world, pose_world, header, size=(1152, 648)) ->
   Image` — the arena, the tags, the car as a 0.2 × 0.15 m rectangle with a heading tick (use
   `configs/car.json` dimensions if present), header "2D view of logged ground truth (fallback for the
   Isaac re-render)".
6. Mac: write **`demo/cards.py`**: `title_card(title, subtitle, lines)`, `segment_card(index, name,
   request)`, `honesty_card(lines)`, `disclosure_card(lines)`, each returning a 1920 × 1080 image with
   wrapped text, dark background, white text, a thin JHU-blue rule `(0, 45, 114)`.
7. Mac: extend **`demo/video_cli.py`** with
   `render --session <dir> --what term|panel|topdown [--workers 8]` (walks `video/edl.json` frame times;
   writes `video/<what>/f%06d.png`; for `panel` it uses the latest corrected report at or before each
   frame's step and the frame's ground-truth pose from `render_plan.json`; uses
   `multiprocessing.Pool`), and `cards --session <dir> --spec <json>` (writes `video/cards/*.png`).
8. Mac: tests (below). Spark host: sync; run the renderers on the **stub session**, then compose a stub
   video with the top-down view as `main`:
   ```bash
   cd ~/Projects/EN.665.715/course-project && P=~/.venvs/beaconmind/bin/python && S=data/demo/<stub id>
   for w in term panel topdown; do $P -m beaconmind.demo.video_cli render --session $S --what $w; done
   $P -c "from beaconmind.demo.ffplan import compose_cmd; import json,subprocess; L=json.load(open('configs/demo_video.json'))['layout']; \
   subprocess.run(compose_cmd('$HOME/.local/bin/ffmpeg','$S/video/topdown/f%06d.png',True,'$S/video/panel/f%06d.png','$S/video/term/f%06d.png',25,L,20,'$S/video/stub_composite.mp4'),check=True)"
   ~/.local/bin/ffprobe -v error -select_streams v:0 -count_frames -show_entries stream=codec_name,width,height,nb_read_frames -of csv=p=0 $S/video/stub_composite.mp4
   ```
   Expected: `h264,1920,1080,<the EDL frame total>`. Extract two stills
   (`~/.local/bin/ffmpeg -ss 1 -i … -frames:v 1 still1.png`; one near the end), copy them as JPEG
   (≤ 1280 px, quality 82) to `evidence/M6/M6.T12/`, pull, and **look at them** (Read the images): the
   three panels are in place, text is readable, nothing is clipped.
9. Mac: status table; `CONTEXT.md`.

**Deliverables.** `course-project/beaconmind/pyproject.toml` (extra `video`);
`demo/fonts.py`, `term_render.py`, `belief_panel.py`, `topdown.py`, `cards.py`; `demo/video_cli.py`
(extended); tests `test_demo_term_render.py`, `test_demo_belief_panel.py`, `test_demo_topdown_cards.py`.

**Tests.** (each file starts with `pytest.importorskip("PIL")`)
- `tests/test_demo_term_render.py`:
  - `test_frame_size` — `render_term_frame` returns 1920 × 432.
  - `test_secret_refused` — a runner line containing `OPENAI_API_KEY=sk-abcdefgh12345` raises
    `SecretInFrame`.
  - `test_select_capture` — captures at T = 10, 10.5, 11: t = 10.7 selects 10.5; t = 5 selects 10.
  - `test_line_style_tags` — `ACTION …` is green and `REPORT …` amber (the colour tuples defined in the
    module).
- `tests/test_demo_belief_panel.py`:
  - `test_world_to_px_corners` — a 2.25 m square arena maps (0, 0) to the bottom-left inner corner and
    (2.25, 2.25) to the top-right inner corner of the drawable area (margin 40).
  - `test_confirmed_beacon_pixel` — a confirmed beacon at a known point colours the pixel at its
    `world_to_px` position blue (the module's colour).
- `tests/test_demo_topdown_cards.py`:
  - `test_topdown_size_and_car` — 1152 × 648, and the pixel at the car's centre is not the background
    colour.
  - `test_cards_size` — each of the four cards is 1920 × 1080 and not a single colour.
- Command → expected: Mac `../.venv/bin/python -m pytest -q tests/test_demo_term_render.py tests/test_demo_belief_panel.py tests/test_demo_topdown_cards.py`
  → `8 passed`; Spark host venv → `8 passed`.
- Smoke: step 8; pass = the `ffprobe` line above, and both stills look right when viewed.

**Acceptance criteria.**
- [ ] `8 passed` on the Mac and the Spark host.
- [ ] The stub composite has the expected codec, size and frame count; two stills viewed and saved.

**Evidence to save** (`evidence/M6/M6.T12/`): `tests-mac.txt`; `tests-spark.txt`; `ffprobe.txt`;
`stub-still-1.jpg`, `stub-still-2.jpg`.

**Pitfalls and known gotchas.** The Mac's ImageMagick has no fonts (AGENTS.md §7.2): use Pillow with
explicit font paths. Thousands of PNGs: use `multiprocessing` and keep them under `data/demo/…/video/`
(git-ignored). The stub composite is a pipeline test; never show it as a demo.

**Stop-and-ask conditions.** none beyond README §1.4.

**Estimated effort.** S.

**AI-disclosure note.** Each new file: `AI-assisted: …`; `term_render.py` adds `Derived from:
discussions/module5/tools/m5-render.py (layout and colour idea, reimplemented)`.

---

### M6.T13 — Isaac Sim re-render of a take's ground-truth trajectory

**Why.** MD5: the simulation footage is re-rendered after the take from the logged ground truth, so
framing can be fixed and re-tried without re-running hours of model time, and the live take is never
slowed by extra render products. The method is the headless recipe proven on this Spark
(`discussions/module2/VIDEO-CAPTURE.md`): `SimulationApp(headless=True)`, the viewport camera aimed with
`set_camera_view`, a Replicator `rgb` annotator on CPU, one PNG per frame. The only new element is
placing the car kinematically instead of driving it, which is verified in step 3.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M6.T10 done (kept take) and M6.T11 done | task | `grep -E '^\| M6\.T1(0\|1) ' course-project/plan/M6-demo-presentation.md` (Mac) | both `done` |
| M2.T15 and M2.T16 done (arena builder, Isaac car) | task | `grep -E '^\| M2\.T1(5\|6) ' course-project/plan/M2-sim-mvp.md` (Mac) | both `done` |
| Isaac `python.sh` | service | `ls ~/IsaacSim/_build/linux-aarch64/release/python.sh` (Spark host) | the path |
| No other kit process | service | `pgrep -af 'kit/kit\|python.sh' \|\| echo clear` (Spark host) | `clear` |
| Render plan of the kept take | file | `ls ~/Projects/EN.665.715/course-project/data/demo/<kept id>/video/render_plan.json` (Spark host) | the file; if absent, run M6.T14 step 1 (the `video_cli plan` command with `sim_target_s`) now. M6.T14 then reuses this plan instead of re-planning |

**Inputs.** `discussions/module2/VIDEO-CAPTURE.md` (whole file: mechanism, preflight, P/S/I marks);
`discussions/module2/sim/render_carter.py`; M2.T15's arena builder (`build_arena`, which uses
`beaconmind.worlds.arena_geometry`) and M2.T16's car asset (find them in step 2);
`video/render_plan.json` (M6.T11).

**Steps.**
1. Spark host: preflight from VIDEO-CAPTURE.md: one kit process at a time; `~/.local/bin/ffmpeg
   -version | head -1` → `ffmpeg version 7.0.2-static`; vLLM may stay up at GPU share 0.60.
2. Mac: **find M2.T15's and M2.T16's pieces**: `grep -rnE --include="*.py" "^def |^class " course-project/sim/isaac/ | tee
   evidence/M6/M6.T13/sim-api.txt`. Write down under "As found" (a) the function that builds the arena
   stage from a C7 world (tags with the AprilTag material, walls, floor, lights) and (b) the car's USD
   path (or the URDF import call). If (a) needs the timeline playing or physics stepping to place
   things, note it. If either is missing → stop and ask.
3. Spark host: **verification spike** (the unverified fact: whether frames change when the car is moved
   kinematically with the timeline stopped). Write `course-project/sim/isaac/render_demo.py` (step 4)
   first with `--spike`: build the arena, place the car at two different poses 0.5 m apart, render
   each, save `spike_a.png`, `spike_b.png`, print the mean absolute pixel difference. Run:
   ```bash
   cd ~/IsaacSim/_build/linux-aarch64/release && TERM=xterm PYTHONUNBUFFERED=1 timeout --kill-after=60 900 \
     ./python.sh ~/Projects/EN.665.715/course-project/sim/isaac/render_demo.py --spike \
     --world ~/Projects/EN.665.715/course-project/data/demo/<kept id>/world.json \
     --out ~/Projects/EN.665.715/course-project/data/demo/<kept id>/video/spike 2>&1 | tail -20
   ```
   Branches, tried in this order (each a flag `--update-mode`):
   - `app_update` (timeline stopped; after setting the pose call `simulation_app.update()` twice, then
     read the annotator): difference > 1.0 and pixel std of each image > 10 → use it.
   - `orchestrator` (`omni.replicator.core.orchestrator.step(rt_subframes=2)` after setting the pose):
     same test → use it.
   - `world_step` (create `World`, play the timeline, `world.step(render=True)`, as the proven recipe
     does), with the car's rigid bodies made kinematic or physics disabled on the car prim: same test →
     use it.
   - None works → stop: use the MD5 fallback (top-down view) and tell Xiaohui.
   Look at both spike images (Read them): the arena, the tags and the car must be visible.
4. Mac: **`course-project/sim/isaac/render_demo.py`** (runs only under Isaac's `python.sh`). Outline,
   each line marked P (proven here), S (NVIDIA-shipped API, not yet run here) or I (inferred), like
   VIDEO-CAPTURE.md:
   ```python
   # parse args BEFORE SimulationApp (P): --plan, --world, --out, --start, --end, --spike, --update-mode, --warmup 100
   # SimulationApp({'headless': True, 'hide_ui': True, 'width': 1152, 'height': 648, 'renderer': 'RaytracedLighting', ...}) (P)
   # carb settings block copied from the recipe (P)
   # build the arena with M2.T15's builder (as found in step 2)
   # create an empty Xform /World/CarPose and put the car USD under it as a reference at identity (I):
   #   the car keeps its own xform ops; only /World/CarPose is moved, with UsdGeom.XformCommonAPI SetTranslate/SetRotate (S)
   # set_camera_view(eye, target, camera_prim_path='/OmniverseKit_Persp') from the plan's camera (P)
   # rp = rep.create.render_product('/OmniverseKit_Persp', (1152, 648)); rgb annotator on CPU (P)
   # warm-up updates; save still_after_warmup.png; abort if its pixel std < 10 (P lesson: gray first frames)
   # for frames[start:end]: set /World/CarPose to (x_m, y_m, 0) and yaw; advance per --update-mode; grab; save f%06d.png (global index)
   # every 250 frames print progress and seconds per frame
   # print('[render_demo] done', n); simulation_app.close() LAST (P)
   ```
   `--start/--end` let a long render run in chunks; a chunk that completes is never re-rendered.
5. Spark host: **framing smoke** — `--start 0 --end 50`; look at frame 0 and frame 49. If the arena is
   cut off or tiny, change the plan's camera (`video_cli plan --camera-eye x,y,z --camera-target
   x,y,z`, add these two options to `video_cli plan`) and repeat (framing only; no model rerun).
6. Spark host: **full render** in chunks of 2,000 frames in tmux window `bmrender`, each wrapped in
   `timeout --kill-after=60 <seconds>`; after each chunk check that its last PNG exists. If a kit
   process hangs after printing `[render_demo] done`, the PNGs are complete: `pkill -9 -f render_demo.py`
   (AGENTS.md §7.4).
7. Spark host: checks (Tests). Save the spike images, frame 0 and one mid-move frame (JPEG ≤ 1280 px) to
   evidence; pull; status table; `CONTEXT.md` (render time per frame, update mode chosen).

**Deliverables.** `course-project/sim/isaac/render_demo.py`; `video_cli plan` camera options; the
frames under `data/demo/<kept id>/video/main/` (git-ignored).

**Tests.**
- Unit tests: `tests/test_demo_render_plan.py` gains `test_camera_override` — `--camera-eye`/`--camera-target`
  values appear in the plan (run on the Mac → the file's count becomes 5).
- Isaac smoke (Spark host): the spike passes one update mode (difference > 1.0, std > 10); the
  50-frame framing smoke produces 50 PNGs.
- Acceptance checks: the number of PNGs in `video/main/` equals the plan's frame count
  (`ls video/main | wc -l`); a frame in the middle of a move differs from the frame 5 frames earlier
  (mean absolute difference > 0.5, computed with Pillow); frame 0's pixel std > 10.

**Acceptance criteria.**
- [ ] `sim-api.txt` "As found" names the arena builder and car asset.
- [ ] The update mode is chosen by the spike, with its numbers in evidence.
- [ ] All frames rendered; the three checks pass; frame 0 and a mid-move frame viewed and saved.

**Evidence to save** (`evidence/M6/M6.T13/`): `sim-api.txt`; `spike.txt` (the printed lines);
`spike_a.jpg`, `spike_b.jpg`; `frame0.jpg`; `midmove.jpg`; `render-log-tail.txt` (the last 20 lines of
each chunk); `checks.txt`.

**Pitfalls and known gotchas.** (all from `VIDEO-CAPTURE.md` and AGENTS.md §7.4) The first headless
frames are gray while shaders compile: warm up. Parse arguments before `SimulationApp` (the kit consumes
`argv`). `simulation_app.close()` must be last; the process may still hang: `pkill -9`. Never run two
kit processes. Do not `./vllm-serve.sh stop` to free memory unless needed: it removes the container.
A camera straight above the target makes `set_camera_view`'s up vector degenerate: keep the oblique
default.

**Stop-and-ask conditions.** Step 2 finds no reusable arena builder; no update mode passes the spike
(then the MD5 fallback, with Xiaohui told); the render would take more than 12 hours (report the
seconds per frame and ask whether to lower the frame rate to 12.5 fps).

**Estimated effort.** M (spike and framing one session; the full render runs unattended).

**AI-disclosure note.** `render_demo.py`: `AI-assisted: <model> via <tool>, <date>: wrote the re-render
script.` and `Derived from: discussions/module2/VIDEO-CAPTURE.md render_carter.py recipe (reimplemented)`.

---

### M6.T14 — Simulation demo video assembly

**Why.** Turns the kept simulation take into its part of the demo video: the Isaac re-render (or the
top-down fallback), the belief panel and the terminal, time-lapsed by the EDL, in the M6-C8 layout.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M6.T12 done | task | status row (Mac) | `done` |
| M6.T13 done, or the MD5 fallback chosen | task / decision | status row or `CONTEXT.md` (Mac) | `done`, or "MD5 fallback" recorded |

**Inputs.** `presentation/DELIVERABLES.md` (`video_limit_s`); `configs/demo_video.json`;
`presentation/demo-script.md`; the kept take's session folder (`CONTEXT.md`, M6.T10).

**Steps.**
1. Spark host: plan with the simulation share of the limit, `sim_target_s` from M6-C8 "Card budget"
   (full demo: 0.5 × (`target_total_s` − 44); cut line: `target_total_s` − 31.5; compute it with
   `edl.card_budget`, never by hand, and paste the arithmetic into `plan.txt`). Which formula: M6.T3's
   status row says `dropped (cut line)` → cut line; anything else → full demo. If M6.T3 is dropped
   later, keep the shorter simulation part (a video shorter than the limit is allowed) rather than
   re-rendering:
   `~/.venvs/beaconmind/bin/python -m beaconmind.demo.video_cli plan --session $S --target-s <sim_target_s>`
   (skip this if M6.T13 already ran it with the same `sim_target_s`: the frames were rendered for that
   plan, and a new plan would not match them).
   If it prints `fits False` → report the output length and ask Xiaohui (options: accept a longer
   simulation part and shorten the car part; or cut the explore segment's middle with a visible "…
   N steps later" card, which the EDL then marks).
2. Spark host: main view: `video/main/` from M6.T13 (re-run M6.T13 step 6 if the plan changed), or
   `video_cli render --what topdown` under the fallback.
3. Spark host: `video_cli render --what panel`, then `--what term` (the term renderer stops on any
   secret; if it does, find the line, report it, and never edit the capture to hide it — ask).
4. Spark host: add the subcommand `compose --session <dir> --main video/main|video/topdown|video/phone
   [--out video/sim_part.mp4] [--by-segment] [--prefix sim|car]` to `video_cli.py` (exactly one of
   `--out` and `--by-segment`; `--prefix` names the per-segment files, default `sim`) (uses `ffplan.compose_cmd`; `--by-segment`
   writes one file per segment, `video/sim_<segment>.mp4`, using `edl.segment_frame_ranges`, so M6.T16
   can put a card between segments; for an image-sequence input it passes `-start_number <first>` and
   `-frames:v <last − first>`). Run it with `--by-segment`.
5. Spark host: checks (Tests). Extract one still per segment at its most telling moment (the step whose
   report has the first `matched` revisit, the `DONE` of return and goto, the `REFUSED`) with
   `ffmpeg -ss <t> -i … -frames:v 1`, convert to JPEG ≤ 1280 px, save to `evidence/M6/M6.T14/` and
   copy the same files to `course-project/presentation/figures/sim-<segment>.jpg` (for the slides).
6. Mac: pull; **look at every still** (Read the images) and at `video/sim_explore.mp4` (copy it to the Mac
   with `scp` into `course-project/presentation/video/`, which is git-ignored by `*.mp4`; add
   `course-project/presentation/video/` and `course-project/presentation/.build/` to the root
   `.gitignore` now if absent). The executor cannot watch a video: extract one frame every 10 s of
   output (`~/.local/bin/ffmpeg -i video/sim_explore.mp4 -vf fps=1/10,scale=1280:-2 video/check/e%03d.jpg`,
   Spark host), pull them and Read each. Xiaohui watches the clip in QuickTime Player and reports.
   Write both in `evidence/M6/M6.T14/review.md` (panels aligned, speed badge shown, text readable, no
   secrets, the main-view label "Isaac Sim re-render of logged ground truth" visible in the header;
   Xiaohui's comments verbatim).
7. Mac: status table; `CONTEXT.md`.

**Deliverables.** `demo/video_cli.py` (`compose`); `data/demo/<kept id>/video/sim_<segment>.mp4` (Spark,
ignored); `course-project/presentation/figures/sim-*.jpg`; root `.gitignore` lines.

**Tests.**
- Unit tests: `tests/test_demo_edl.py` gains `test_split_by_segment` — `edl.segment_frame_ranges` on a
  two-segment EDL splits at the second `segment_start`, and the ranges cover every frame exactly once.
  Command (Mac):
  `../.venv/bin/python -m pytest -q tests/test_demo_edl.py tests/test_demo_render_plan.py tests/test_demo_ffplan.py`
  → `16 passed` (7 + 5 + 4, including M6.T13's added test).
- Acceptance checks (Spark host), for each `sim_<segment>.mp4`:
  `~/.local/bin/ffprobe -v error -select_streams v:0 -count_frames -show_entries stream=codec_name,width,height,nb_read_frames,r_frame_rate -of csv=p=0 <file>`
  → `h264,1920,1080,<that segment's EDL frames>,25/1`; and the sum of all segments' durations ≤
  `sim_target_s` + 1 s.
- Visual check: step 6 (a person-equivalent look at stills and one clip).

**Acceptance criteria.**
- [ ] Four segment clips with the exact frame counts and the 1920 × 1080 h264 format.
- [ ] Total within the simulation share (or Xiaohui's recorded alternative).
- [ ] Stills for the slides saved; `review.md` written after viewing.

**Evidence to save** (`evidence/M6/M6.T14/`): `plan.txt` (the plan line); `ffprobe.txt`; stills;
`review.md`.

**Pitfalls and known gotchas.** The `*.mp4` rule ignores videos everywhere, but PNG frames are not
ignored outside `data/`: never write frames under `presentation/`. Do not re-encode a clip twice before
the final assembly (quality loss); M6.T16 concatenates with the concat demuxer after one encode.

**Stop-and-ask conditions.** `fits False` (step 1); a secret in a capture (step 3).

**Estimated effort.** S.

**AI-disclosure note.** `review.md` and code changes carry the usual line; the video's disclosure is a
card added in M6.T16.

---
### M6.T3 — The same ROSA demo on the car

**Why.** The talk track promises the demo "in Isaac Sim and on the car", and the course is about a
physical robotic car (AGENTS.md §2). This task runs the same script, the same runner and the same
`bm-tools` server against the real car in the physical arena, filmed by a phone. It is the riskiest M6
task (Wi-Fi losses, battery, a real moving robot), so it comes after the simulation take has proven the
script, and it follows M3.T12's session-start checks and M3.T18's closed-loop practice, which already
proved closed-loop L2 runs on this car. **Under the cut line this task is `dropped (cut line)`**
(M3.T18 is dropped there too).

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M3.T18 done (closed-loop real L2 runs) | task | `grep -E '^\| M3\.T18 ' course-project/plan/M3-real-car.md` (Mac) | `done` (if `dropped (cut line)`: set M6.T3 and M6.T15 to `dropped (cut line)` and stop) |
| M3.T7, M3.T13, M3.T17 done (gate, STOP hotkey, GT accuracy) | task | `grep -E '^\| M3\.T(7\|13\|17) ' course-project/plan/M3-real-car.md` (Mac) | all `done`; `ls course-project/evidence/M3/M3.T7/` non-empty |
| Power path decided (OD9) | task | `grep -E '^\| M3\.T(1\|20) ' course-project/plan/M3-real-car.md` (Mac) and `grep -n "OD9" course-project/CONTEXT.md` | M3.T1 `done`; the OD9 answer recorded (power bank via M3.T20, or the regulator path) |
| M6.T10 done | task | status row (Mac) | `done` |
| Days left > 7 (and ≥ 21 days left recommended, M6.T1 question 10) | calendar | the days-left one-liner (Mac) | > 7 |
| Real arena spec | file | `ls course-project/configs/arenas/real-*.json` (Mac) | one file (M3.T10) |
| `bm-pico`, `bm-estop`, `bm-clear-latch` exist | service | `docker exec beaconmind-ros bash -lc 'source /opt/ros/humble/setup.bash && source /workspace/course-project/ros2_ws/install/setup.bash && which bm-pico bm-estop bm-clear-latch'` (Spark host) | three paths (`bm-pico` M3.T2 and `bm-estop` M3.T13 are colcon console scripts; `bm-clear-latch` is M1.T3's wrapper for M2.T1's CLI); if one is missing, stop and ask |

**Inputs.** README §7 (S1–S12, read them all again); `plan/M3-real-car.md` M3.T12 steps 2–3
(session-start checks, placement check), M3.T18 steps 3–6 (closed-loop practice), M3.T9 step 4 (the
real backend and its episode-start checklist), M3.T13 (hotkey), M3.T17 (GT accuracy); M3.T11's overhead
camera procedure; `CONTEXT.md` "Hardware state"; `reference/hardware/pico-bringup.md`;
`presentation/demo-script.md` (car filming plan); this file's M6-C1 to M6-C7.

**Steps.** Steps marked **Xiaohui (bench)** or **Xiaohui (arena)** are Xiaohui's hands only (S1): write the
instruction, explain it, then wait for their report.

0. Mac, **in an earlier session, not on the take day:** write **`demo/sync_marker.py`**, CLI
   `python3 -m beaconmind.demo.sync_marker --session <dir> --label <text>`: prints a large `3`, `2`,
   `1`, `CLAP` one second apart and writes a `sync_marker` event (M6-C5, `src: runner`) to
   `trace-sync.jsonl` at the `CLAP` instant (`read_trace` merges it). Test
   `tests/test_demo_sync_marker.py::test_marker_written` — the event exists with the label and a
   `t_wall` within 0.2 s of the end of the countdown. Run it (`1 passed`) and sync to the Spark.
1. Mac: **brief Xiaohui** before anything physical (README §1.2 step 5): what the session does (one
   take, about 2–4 hours: preflight, four segments, teardown), that the robot will drive itself on the
   floor under the agent's control with the validator and the Pico's own limits in between, where they
   stand, and the two ways to stop it (STOP hotkey first; battery switch if the STOP fails, S7). Ask
   them to confirm they have: the multimeter, fresh or charged cells for the pack, the phone with ≥ 15 GB
   free and its charger, a tripod or a stable high shelf, tape for the start mark.
2. **Xiaohui (bench) — phone settings.** *What:* set the phone to record 1080p at 30 fps, with HDR video
   off; on an iPhone also Settings → Camera → Formats → "Most Compatible" (H.264). Turn on Do Not
   Disturb. *Why:* 1080p30 H.264 is decoded everywhere and keeps a 2-hour take near 7 GB; HDR footage
   turns washed-out after conversion; a notification banner would be filmed. *Measure:* record a 10 s
   test clip, AirDrop it to the Mac, copy it to the Spark
   (`COPYFILE_DISABLE=1 tar czf - <clip> | ssh … 'mkdir -p /tmp/m6t3 && tar xzf - -C /tmp/m6t3'`), and
   run `~/.local/bin/ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,r_frame_rate,color_transfer -of csv=p=0 /tmp/m6t3/<clip>`
   (Spark host). *Pass:* `h264,1920,1080,30/1` (or `30000/1001`) and a `color_transfer` that is not
   `arib-std-b67` or `smpte2084` (those are HDR). If the codec is `hevc` but not HDR, it is acceptable
   (the static ffmpeg decodes it); note it.
3. **Xiaohui (arena) — arena check.** *What:* lay out the arena exactly as `configs/arenas/real-<name>.json`
   says; count the tags and compare with the spec; press any lifted tag flat; clear the floor; mark the
   start pose with tape (the spec's `start_pose`: a cross for the axle midpoint and a line for the
   heading). Remove personal items from the phone's frame and from the robot camera's possible view.
   *Why:* the map frame is defined by the start pose (C1), the ground truth relates to the surveyed tags
   (C8), and S10/L8 forbid people and personal items in view. *Measure:* tag count; tape-measure the
   start mark to the two nearest walls. *Pass:* tag count equals the spec; the start mark within 2 cm of
   the spec's coordinates.
4. **Xiaohui (arena) — phone rig.** *What:* the phone on a tripod or a high shelf **outside** the arena,
   framing the whole arena; nothing on or above the arena that could fall in. *Why:* the video must
   show the robot's whole path; anything falling into the arena is a collision hazard. *Measure:* a
   test photo; the four walls visible. *Pass:* all four walls and the start mark in frame.
5. **Xiaohui (bench) and Spark host — session-start checks, wheels up.** Run M3.T12 step 2's
   session-start checks verbatim (fresh agent, exactly one `/bm_pico`, latch clear, overhead GT node at
   ≥ 10 Hz, `real_car.launch.py with_gt:=true`, hotkey window `bm:estop` open, nobody in the arena, pack
   ≥ 5.5 V), with the car **on its wheels-up stand** (S2 discipline even though the gate has passed:
   the STOP test below spins the wheels). Explain each physical item to Xiaohui before they do it:
   - **Power path (S3, OD9).** *What:* with the power bank (OD9 default) the Pico is powered through
     its micro-USB cable, so the green AMS1117 `OUT` → Pico pin 39 (`VSYS`) jumper must be **out**
     before the USB cable goes in. *Why:* no diode separates USB from VSYS; with both connected, USB
     back-feeds about 4.7 V onto the battery rail when the switch is off (`car-build-notes.md`).
     *Measure:* battery switch off, USB (power bank) in, jumper out: multimeter on DC volts between the
     VBAT rail and GND. *Pass:* 0 V (within ±0.05 V). Anything else → unplug USB at once and stop and
     ask. (If OD9 chose the regulator path instead: no USB at all, jumper in, STBY pull-down fitted,
     wheels up at every switch-on — S4.)
   - **Power order (S4).** *What:* Pico first (power bank in), battery rocker switch second; power down
     in the reverse order (battery switch first). *Why:* the TB6612FNG driver should see its logic side
     powered before motor power arrives, and the Pico must already be driving STBY low.
   - **Battery (S8).** *What:* multimeter on DC volts across the pack's output, motors idle. *Why:* below
     5.5 V the motors brown out and moves fail as stalls. *Pass:* ≥ 5.5 V; write the reading down.
   - **STBY pull-down (S5).** Confirm from M3.T1's evidence that the 4.7 kΩ resistor is fitted (no
     re-measurement needed unless wiring changed since).
   - **Boot disarmed (S6), one node (S11).** `docker exec beaconmind-ros bash -lc 'bm-pico state'` →
     `armed False`; `ros2 node list | grep -c bm_pico` → `1`.
   - **Out-of-band STOP (S7), wheels up.** *What:* run M3.T7's gate tool for three hotkey trials,
     `bm-gate estop --n 3 --hotkey --out evidence/M6/M6.T3/take<k>/stop-test` inside `beaconmind-ros`
     (flags exactly as its `--help` prints; M3.T7 step "G1"), and Xiaohui presses SPACE in window
     `bm:estop` when the tool asks, while the wheels turn in the air. *Why:* the STOP must stop the
     motors before the robot is on the floor in this session. *Pass:* every trial `t1 − t0` ≤ 0.200 s
     (C10.11, M3.T7), the wheels stop each time, and `bm-pico state` shows `armed False` afterwards. If
     `bm-gate` does not exist → stop and ask (do not improvise a STOP test). The tool clears the latch
     between trials as M3.T7 logs it; after the last trial Xiaohui clears it (`bm-clear-latch`, they
     type `clear`).
   Paste every reading into `evidence/M6/M6.T3/take<k>/preflight.md`.
6. Spark host: start the real stack per M3.T9 and M3.T11 (bring-up, camera bridge, observation builder,
   overhead ground-truth camera) exactly as M3.T12's evidence ran it, and confirm the topics as in
   M6.T9 step 6 (sources are now real).
7. Spark host: create the session and panes:
   `~/.venvs/beaconmind/bin/python -m beaconmind.demo.new_session --source real --label take<k> --take <k>
   --world configs/arenas/real-<name>.json --script configs/demo_script.json --decider rosa --model-key
   <OD8 key> --rosa-mode trimmed` (on the car MD1 must be `trimmed` if M6.T2 step 5 found actuating
   stock tools), then `bash tools/demo_tmux.sh <id> ros rosa "--pause-between-segments"`. Check the
   typed runner command (`tmux capture-pane -p -t bmdemo:demo.0 | tail -3` shows
   `--pause-between-segments` before the closing `'`). The environment server (pane `demo.1`) may run
   M3.T9 step 4's **interactive episode-start checklist** through `RosEnv`: answer it in that pane
   (Xiaohui confirms each physical item) before anything else. Then check the heartbeat as in M6.T9
   check 5 (`ros2 topic hz /pico/heartbeat`, 9–11 Hz); no heartbeat → stop. Add the take's row to
   `takes.md`.
8. Mac: confirm `demo/sync_marker.py` and its test exist and pass (written in step 0):
   `cd course-project/beaconmind && ../.venv/bin/python -m pytest -q tests/test_demo_sync_marker.py` → `1 passed`.
9. **Xiaohui (arena) — place and arm.** *What:* battery switch off (S4 power-down order); take the car
   off the stand and place it on the start mark, axle midpoint on the cross, camera end along the
   heading line (**Revised 2026-10-24:** lift the car and set it down there; never slide or roll it into
   place, and lift it again to re-place it; README S13); battery switch on (the Pico is already
   powered by the power bank, S4); wait for exactly one Pico node (S11). *Measure:* the executor
   reads the overhead GT pose (`/ground_truth/pose`) and compares it with the spec's `start_pose`. *Pass:* within **5 cm and 3°**
   (M3.T12 step 3); else Xiaohui re-places the car. Then Xiaohui arms: `bm-pico arm` in window `ctl`
   (only an operator command arms, C2 `/pico/arm`, D6). *Why:* the agent's map frame starts here, and
   arming is deliberately a human step. *Pass:* `bm-pico state` shows `armed True`; the runner pane
   shows the typed command waiting.
10. **Segments.** For each segment: Xiaohui starts a **new phone clip**; the executor runs
    `python3 -m beaconmind.demo.sync_marker --session <dir> --label CLAP-<segment>` in window `ctl`
    (inside `beaconmind-ros`, like `demo.estop`) and Xiaohui claps on `CLAP` in view of the phone.
    Before the first segment the executor then presses Enter in pane `demo.0`; before each later
    segment the runner prints `PAUSED before segment <name>: press Enter to continue`, and the
    executor presses Enter in `demo.0` only after the new clip and the clap. Xiaohui watches the robot
    the whole time and presses STOP (SPACE in `bm:estop`) **at once** if the robot heads out of the
    arena, pushes a wall for more than a moment, or anything looks wrong; the battery switch if STOP
    fails (S7). **During a pause**, if the last segment ran > 30 min or a move stalled unexpectedly:
    `bm-pico disarm`, battery switch off, measure the pack (S8), replace cells below 5.5 V, battery
    switch on, `bm-pico arm`, then continue. (On the power bank the Pico stays powered, so no reboot;
    on the regulator path the swap reboots the Pico, which latches: then follow step 11.)
11. **If a latch happens** (STOP, `link_lost` from the lossy Wi-Fi, a Pico reboot): the runner ends the
    session after that segment and prints `LATCHED: … resume with …` (M6.T7 step 8); the environment
    server keeps running. On the car — unlike in simulation — the robot stays where it stopped, so a
    **resume at the next segment boundary** is allowed: Xiaohui checks the robot and the arena, clears
    the latch themselves (`bm-clear-latch --operator "Xiaohui Chen"`, the M2.T1 CLI; C5 item 5, M3.T12 step 2), re-arms
    (`bm-pico arm`), and the executor types in pane `demo.0`
    `docker exec -it -w /workspace/course-project/beaconmind rosa-ros2 bash -lc 'source /opt/ros/humble/setup.bash && PYTHONPATH=src python3 -u -m beaconmind.demo.run --session /workspace/course-project/data/demo/<id> --decider rosa --start-segment <next> --prev-report state/after-<this>.json --pause-between-segments'`.
    The interrupted segment stays as it ended (it is not re-run), and the take's row and the honesty
    card say "resumed after <reason> at segment <name>". A latch mid-segment is never edited out of the
    footage. A Pico reboot changes the boot id: if `bm-pico state` does not show the new boot id and
    `armed False` after the reboot, stop and ask.
12. **Teardown** (Xiaohui and the executor): `bm-pico disarm`; battery switch off first (S4); `touch
    term/STOP`; stop the runner (if still running), the environment server (Ctrl-C in pane `demo.1`; it
    writes the obslog footer, M6.T7 step 5) and the bring-up; stop and remove the micro-ROS agent (fresh per
    session, AGENTS.md §7.4); USB/VSYS state as S3 requires. Record the final hardware state in
    `CONTEXT.md` "Hardware state" (jumper, USB, switch, pack voltage).
13. **Xiaohui (bench) — copy the phone clips.** AirDrop to the Mac into `~/Movies/BeaconMind/<session_id>/`
    (outside the repository), then
    `cd ~/Movies/BeaconMind && COPYFILE_DISABLE=1 tar cf - <session_id> | ssh -o ConnectTimeout=15 xiaohui_chen@spark-2a60 'mkdir -p ~/Projects/EN.665.715/course-project/data/demo/<session_id>/phone && tar xf - -C ~/Projects/EN.665.715/course-project/data/demo/<session_id>/phone --strip-components=1'`
    (Mac). Name the clips `clip-<segment>.mov` (or `.mp4`).
14. Spark host: score (`docker exec -w /workspace/course-project/beaconmind beaconmind-ros python3 -m
    beaconmind.demo.score --session /workspace/course-project/data/demo/<id>`), then the checks as in
    M6.T10 (`segments.json` entries, run-log lines without `error`, obslog header and footer,
    `move_end` count, captures covering the session; with a latch and no resume there may be fewer than
    four entries). `success` uses the overhead camera's ground truth (C8, accepted within 5 cm / 3° by
    M3.T17); state that accuracy (from M3.T17's evidence) next to each car result. If the overhead camera was not running, `success` is `null` and `gt_source` is
    `none`; Xiaohui may tape-measure the final distance to the target or start mark, recorded as
    "tape-measured, not ground truth".
15. Mac: `takes.md` row completed; `summary.md` with real numbers; pull evidence; `CONTEXT.md`. Keep the
    first take that ran all four segments (resumes allowed as in step 11); at most **2 car takes**
    without asking.

**Deliverables.** `demo/sync_marker.py` and `tests/test_demo_sync_marker.py`; the car session folder
with `phone/` (Spark, git-ignored); `presentation/takes.md` updated; `evidence/M6/M6.T3/take<k>/`.

**Tests.**
- Unit test: `tests/test_demo_sync_marker.py::test_marker_written` (Mac) → `1 passed`.
- Hardware tests (each recorded in `preflight.md`):
  - battery pack, motors idle, multimeter DC volts: ≥ 5.5 V, before the take and between long segments;
  - out-of-band STOP with the wheels up (`bm-gate estop --n 3 --hotkey`): every one of 3 trials
    ≤ 0.200 s;
  - Pico node count in the graph: exactly 1;
  - start mark: within 2 cm of the spec on both axes (tape measure);
  - VBAT rail with the battery switch off, power bank in, jumper out: 0 V ± 0.05 V (S3; power-bank
    path only);
  - car placement at the start: overhead GT within 5 cm and 3° of `start_pose` (M3.T12 step 3);
  - heartbeat `/pico/heartbeat` 9–11 Hz with the environment server running (step 7).
- Acceptance checks on the session: as M6.T10's list, plus: every phone clip exists and `ffprobe`
  reads its duration; each clip's duration ≥ its segment's wall time (from the trace) minus 10 s
  (it covers the segment).

**Acceptance criteria.**
- [ ] `preflight.md` holds every reading, all passing.
- [ ] A kept car take with four segment entries (with resumes stated if any) and phone clips per
      segment on the Spark.
- [ ] Hardware state recorded in `CONTEXT.md` at teardown.

**Evidence to save** (`evidence/M6/M6.T3/take<k>/`): `preflight.md`; `phone-test-ffprobe.txt`;
`summary.md`; `segments.json`; `session.json`; trace excerpts; one photo of the arena with the start
mark (JPEG ≤ 1 MB, no personal items, Xiaohui's photo).

**Pitfalls and known gotchas.**
- The Wi-Fi is lossy where the car drives (31–52 of 60 status samples per 6 s; one Module 5 rehearsal
  lost the link mid-run; `CONTEXT.md` "Wi-Fi"). Expect `link_lost` latches; they are safe behaviour.
- The bent tray spring is the first suspect for a mid-run cut (S8, `car-build-notes.md`).
- If a wheel goes dead, press the TB6612 board down first (S9).
- Ghost Pico nodes after reboots under one agent make commands vanish (S11): one fresh agent per
  session. **Revised 2026-10-24:** after an agent restart the firmware's session supervisor (M3.T23)
  rebuilds its own session; reboot the Pico by hand (battery off, S6) only if `/bm_pico` has not
  reappeared within 30 s of the agent coming back (README S11; this replaces "reboot the Pico after any
  agent restart").
- The phone clip may stop by itself when storage fills or the phone overheats: check it between
  segments.

**Stop-and-ask conditions.** Any S-rule cannot be met (README §1.4 item 7), including the STOP check
failing or the VBAT rail not reading 0 V in the S3 check; the battery below 5.5 V with no spare cells;
`bm-pico`, `bm-estop`, `bm-gate` or `bm-clear-latch` missing; no heartbeat; the GT placement check
failing three times; the robot touches a
wall without a `stalled`/`bumped` result (the D6 residual risk became real: stop the take and report);
two car takes without a complete one.

**Estimated effort.** M (one long arena session plus copying and checks).

**AI-disclosure note.** `sync_marker.py` and its test carry `AI-assisted: …`. `preflight.md` and
`summary.md` end with the disclosure line; Xiaohui performed every physical step, and the evidence says
so.

---

### M6.T15 — Car demo video assembly (phone footage, terminal, time-lapse)

**Why.** Turns the kept car take into its part of the demo video, using the same EDL logic as the
simulation part, with the phone footage as the main view. The phone clock is not the Spark clock, so
each clip is synchronised from a visible event.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M6.T3 and M6.T12 done | task | status rows (Mac) | `done` |
| Phone clips on the Spark | file | `ls ~/Projects/EN.665.715/course-project/data/demo/<car id>/phone/` (Spark host) | one clip per segment |

**Inputs.** M6.T11 (`edl.py`, `ffplan.phone_piece_cmd`), M6.T14 (the `compose` subcommand), the car
session folder.

**Steps.**
1. Spark host: `video_cli plan --session <car id> --target-s <car_target_s>` with `car_target_s` =
   0.5 × (`target_total_s` − 44) (M6-C8 "Card budget", full demo; computed with `edl.card_budget`).
2. **Sync each clip** (the unverified fact is the offset between phone time and Spark time). Primary
   event: the **first wheel motion** of the segment, whose Spark time is the segment's first
   `move_start` in `trace-env.jsonl`. Procedure:
   1. Xiaohui (Mac, QuickTime Player): open the clip, step to the first visible wheel motion, and report
      the clip time to the nearest second.
   2. Spark host: extract 10 frames per second in a ±2 s window around that time:
      `~/.local/bin/ffmpeg -ss <t−2> -i clip-<segment>.mov -t 4 -vf fps=10,scale=640:-2 video/sync/<segment>-%02d.png`;
      copy them to the Mac and **look at them** (Read) to find the first frame where the car has moved;
      its time is `phone_t_first_motion`.
   3. Write `video/sync.json` as `{"<segment>": {"phone_t_first_motion": …, "t_wall_first_move_start":
      …}}`. The clip time of any wall time `t` in that segment is then
      `phone_t_first_motion + (t − t_wall_first_move_start)`.
   4. **Check** with the segment's last motion: predict the phone time of the last `move_end`, look at
      frames around it the same way, and require |observed − predicted| ≤ 0.5 s. If it fails (the phone
      dropped frames or the clip was paused), stop and ask.
   The clap (`sync_marker`) is a coarse cross-check only (±0.3 s human timing).
3. Mac: add subcommand `phone --session <dir>` to `video_cli.py`: for each EDL piece of each segment,
   run `ffplan.phone_piece_cmd` with the synced clip time, the piece's duration, speed and frame count;
   concatenate each segment's pieces (concat demuxer, no re-encode) into `video/phone_<segment>.mp4`.
   That mp4 is the **main input** of `compose_cmd` (`main_is_pattern=False`); it is not decoded to PNGs.
   Test: `tests/test_demo_ffplan.py::test_phone_pieces_for_segment` — for a two-piece EDL and
   `phone_t_first_motion` 12.0 s, the commands start at the right clip times and their frame counts sum
   to the EDL's (test count in that file becomes 5).
4. Spark host: render `panel` (with the overhead ground truth if `gt_source` is `overhead`; otherwise
   belief only, header "no ground truth") and `term`; compose by segment into `video/car_<segment>.mp4`
   with `video_cli compose --session <dir> --main video/phone --by-segment --prefix car` (with
   `--main video/phone`, compose uses `video/phone_<segment>.mp4` as each segment's main input,
   `main_is_pattern=False`).
5. Spark host: checks (Tests); stills per segment (as M6.T14 step 5) to evidence and
   `presentation/figures/car-<segment>.jpg`.
6. Mac: copy one segment clip to `presentation/video/`; Xiaohui watches it in QuickTime Player and
   reports; the executor extracts frames around the first move (as in M6.T14 step 6) and Reads them.
   `review.md` (sync looks right: the wheels start when the terminal shows `MOVE … start`; speeds
   labelled; text readable; no person or personal item in frame — if there is, ask Xiaohui whether to
   crop or blur before use).
7. Mac: status table; `CONTEXT.md`.

**Deliverables.** `demo/video_cli.py` (`phone`); `tests/test_demo_ffplan.py` (one test added);
`data/demo/<car id>/video/car_<segment>.mp4` (Spark); `video/sync.json`; `presentation/figures/car-*.jpg`.

**Tests.**
- Unit: `test_phone_pieces_for_segment` (above); Mac `../.venv/bin/python -m pytest -q tests/test_demo_ffplan.py`
  → `5 passed`.
- Sync check: step 2.4 within 0.5 s for every segment (numbers in `sync.txt`).
- Format check per clip: `ffprobe` → `h264,1920,1080,<segment's EDL frames>,25/1`.

**Acceptance criteria.**
- [ ] Every segment synced and checked within 0.5 s.
- [ ] Four car segment clips with exact frame counts; total within `car_target_s` (or Xiaohui's
      recorded alternative).
- [ ] Stills saved; `review.md` written after watching.

**Evidence to save** (`evidence/M6/M6.T15/`): `sync.txt` (the four offsets, the end checks, the frame
file names used); `ffprobe.txt`; stills; `review.md`.

**Pitfalls and known gotchas.** `-ss` before `-i` seeks fast but to the nearest keyframe on some
inputs; the frame count is forced with `-frames:v`, and the sync check catches drift. Variable frame
rate phone clips: `fps=<fps>` in the filter normalises them. Never speed up a piece that contains
motion (the EDL never does).

**Stop-and-ask conditions.** A sync check over 0.5 s; a person or personal item visible in the
footage.

**Estimated effort.** S.

**AI-disclosure note.** Code: the usual line. `sync.txt`/`review.md`: the disclosure line, and "Xiaohui
read the phone times in step 2.1".

---

### M6.T16 — Final demo video: cards, narration, checks

**Why.** Assembles the deliverable: title, an honesty card, the simulation part, the car part, and the
disclosure card, with Xiaohui's narration (MD6). AGENTS.md §5 requires the generative-AI disclosure on
every submitted artifact, so the video ends with it, on screen and spoken.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M6.T14 done | task | status row (Mac) | `done` |
| M6.T15 done, or M6.T3/T15 `dropped (cut line)` | task | status rows (Mac) | `done` or `dropped (cut line)` |
| `DELIVERABLES.md` limits | doc | `grep -n "video_limit_s" course-project/presentation/DELIVERABLES.md` (Mac) | a number |

**Inputs.** `presentation/DELIVERABLES.md`; `presentation/demo-script.md` (narration outline);
`presentation/takes.md`; both sessions' `segments.json`, `cues.csv` and `session.json`; README L11;
`discussions/module5/talk-track.md` (130 words per minute; narration over the waits).

**Steps.**
1. Mac: write **`course-project/presentation/demo-cards.json`** (the card texts) — every number read from
   the sessions' files, never typed from memory:
   - title: "BeaconMind — an LLM that owns landmark SLAM", subtitle "EN.665.715 course project demo ·
     Xiaohui Chen (sole participant)", lines: date of the takes.
   - honesty card (one line each): "Course demo through ROSA in rosa-ros2 (AGENT-DESIGN D10). Not
     comparable with the benchmark, which uses its own harness."; "Model: <provider model>, thinking
     <on/off>, served locally by vLLM on the DGX Spark."; "Simulation: take <k> of <n> (takes.md); Isaac
     Sim re-render of the logged ground truth, interpolated between stops." (or "2D view" under the
     fallback); "Car: take <k> of <n>" + resumes, or "Car demo not run: <reason>" under the cut line;
     "Thinking time is sped up (shown as ×N); motion plays in real time."; "Decision latency in these
     takes: p50 <a> s, p95 <b> s." (from `segments.json`; add "above the 60 s gate" if p95 > 60);
     "Success is judged from ground truth (sim) or the overhead camera (car, ±5 cm / 3°)."
   - part cards: "Part 1 — Isaac Sim twin", "Part 2 — the real car".
   - segment cards: "1 · Explore an unseen arena", "2 · 'Please go back to where you started.'", "3 ·
     'Drive to beacon <target>.'", "4 · 'Follow that person.'" (the real texts from `script.json`).
   - disclosure card: "Generative-AI disclosure", then: which models wrote the code, the plan and the
     narration draft (the executors' model names from the code headers and `CONTEXT.md`; Claude Opus
     5.5 via Claude Code for the plan and design documents), that the robot's decisions in the video are
     Qwen3.5 (or the OD8 model) running live, and "Xiaohui Chen chose the project, built and wired the
     car, ran the takes, reviewed every artifact, and is responsible for it."
2. Spark host: `video_cli cards --spec presentation/demo-cards.json` → PNGs; `ffplan.card_clip_cmd` for
   each with the M6-C8 durations; write the concat list in order: title, honesty, part 1, (segment
   card, `sim_<segment>.mp4`) × 4, part 2, (segment card, `car_<segment>.mp4`) × 4, disclosure (under
   the cut line: title, honesty, part 1, (segment card, `sim_<segment>.mp4`) × 4, disclosure; for a car
   take that ended early, only the car segments that exist, and the honesty card says which are
   missing); create the folder first (`mkdir -p ~/Projects/EN.665.715/course-project/data/demo/video`,
   Spark host); run `concat_cmd` → `data/demo/video/Chen-BeaconMind-Demo-silent.mp4`. All inputs share codec, size,
   frame rate and pixel format, so the concat demuxer joins them without re-encoding.
3. Mac: write **`course-project/presentation/demo-voiceover.md`**: one block per cue (from `cues.csv`,
   output times of the silent video), with the words to say and a word budget = seconds × 130 / 60.
   Required beats (demo-script.md narration outline): what each panel shows; one step's ReAct loop read
   off the terminal (OBSERVATION → ACTION/RESULT → REPORT → CHECK, and that NOTE is the agent's own
   summary, not its hidden reasoning); a duplicated-ID moment if the take has one; each request and its
   answer; the refusal and the zero moves after it, with the request-suite rate (M4.T14) for context;
   the honesty card read aloud in short; the spoken disclosure at the end. The request-suite rate comes
   from `report/generated/numbers.json` (M4.T14's scoring, through M5.T9), never typed.
4. **Xiaohui (Mac) — record the narration.** *What:* open the silent video in QuickTime Player; in a
   second QuickTime window choose File → New Audio Recording, pick the microphone, start it, then play
   the video and read `demo-voiceover.md` in time with it; save as `narration.m4a`. *Why:* one take of
   narration in sync with the picture; QuickTime is installed (checked 2026-10-05). *Pass:* the audio is
   as long as the video ± 2 s. If the presentation is live (M6.T1 question 2) and Xiaohui narrates live,
   skip this step and keep the silent video (record that choice).
5. Spark host: copy `narration.m4a` to `data/demo/video/`; `mux_narration_cmd` →
   `data/demo/video/Chen-BeaconMind-Demo.mp4`.
6. Spark host: checks (Tests); copy the final video to the Mac `course-project/presentation/video/`
   (git-ignored); record its SHA-256 in evidence.
7. **Xiaohui (Mac)** watches the whole video once in QuickTime Player and reports; the executor
   extracts one frame at each `cues.csv` time and at every card (Spark host, `ffmpeg -ss <t> -i … -frames:v 1`),
   pulls and Reads them. Write `evidence/M6/M6.T16/review.md`: cards readable for their full duration,
   cuts in the right places, narration in sync (Xiaohui's judgement, ±1 s at the segment cards),
   disclosure visible and spoken, no secret, no personal item.
8. Mac: status table; `CONTEXT.md` (final video path on the Spark and the Mac, SHA-256, duration).

**Deliverables.** `course-project/presentation/demo-cards.json`, `demo-voiceover.md`; the final video
(Spark `data/demo/video/Chen-BeaconMind-Demo.mp4`; Mac copy in `presentation/video/`, both
git-ignored); `evidence/M6/M6.T16/`.

**Tests.**
- Unit: `tests/test_demo_topdown_cards.py::test_cards_from_spec` — every card in `demo-cards.json`
  renders, and no card's text contains `{` or `TBD` (unfilled fields) → that file reports `3 passed`.
- Acceptance checks (Spark host):
  - `~/.local/bin/ffprobe -v error -show_entries format=duration -of csv=p=0 Chen-BeaconMind-Demo.mp4`
    ≤ `video_limit_s`;
  - `~/.local/bin/ffprobe -v error -show_entries stream=codec_type,codec_name,width,height -of csv=p=0 …`
    → `video,h264,1920,1080` and `audio,aac` (no audio line if narration was skipped by decision);
  - loudness: `~/.local/bin/ffmpeg -i Chen-BeaconMind-Demo.mp4 -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume"`:
    `max_volume` between −12 dB and −0.5 dB (audible, not clipped). `mean_volume` is recorded only:
    the silences between narration blocks pull it down, so it is not a pass criterion (proposed
    default thresholds; Xiaohui's listening check in step 7 overrides them);
  - the last second shows the disclosure card: extract it
    (`-sseof -1 -i … -frames:v 1 last.png`), look at it (Read), confirm the text;
  - the first frame is the title card (same method).

**Acceptance criteria.**
- [ ] Final video within the limit, h264 1920 × 1080 with AAC narration (or silent by recorded
      decision).
- [ ] Title first, disclosure last, both verified by looking at extracted frames.
- [ ] `review.md` written after watching it in full.

**Evidence to save** (`evidence/M6/M6.T16/`): `ffprobe.txt`; `volumedetect.txt`; `first.jpg`,
`last.jpg`; `sha256.txt`; `review.md`; `demo-cards.json` copy is tracked already.

**Pitfalls and known gotchas.** The concat demuxer needs identical stream parameters; card clips must be
encoded with the same `-r 25 -pix_fmt yuv420p -c:v libx264` as the parts. `-shortest` cuts the video if
the narration is shorter: check the duration after muxing. Never put the narration's script text on
screen as captions without checking it matches what was said.

**Stop-and-ask conditions.** The final video exceeds the limit after fitting; the volume check fails
twice; anything on screen Xiaohui has not approved (personal items, a classmate's name).

**Estimated effort.** S (plus Xiaohui's recording time).

**AI-disclosure note.** The disclosure card and the spoken line are the video's disclosure (AGENTS.md
§5). `demo-voiceover.md` ends with a "Generative-AI disclosure" paragraph. `demo-cards.json` cannot hold
comments, so `course-project/presentation/README.md` (create it if absent) lists it with the line
`demo-cards.json — AI-assisted: <model> via <tool>, <date>: drafted the card texts from the session files.`

---
### M6.T5 — Slides on the JHU template, validated, with a talk track

**Why.** AGENTS.md §5 makes the JHU template mandatory for every new course-project deck and requires
the tracked validator, an aligned talk track, a two-engine render review, and the disclosure on the
final slide. The slides present the question, the system, the demo and the benchmark results; every
number comes from a result file, never typed by hand (the same rule as M5.T4).

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M6.T1 done | task | status row (Mac) | `done` (`expected_slides`, `talk_limit_min`) |
| Template present | file | `ls reference/templates/JHU-Presentation-Template_Fa25.potx` (Mac) | the file |
| python-pptx on the Mac's `python3` | package | `python3 -c "import pptx; print(pptx.__version__)"` (Mac) | `1.0.2` |
| Final build only: results | task | M4.T16 (or M2.T12 under the cut line), M5.T9 and M5.T4 status rows (Mac) | `done`; `ls course-project/report/generated/numbers.json` prints the path |
| Final build only: demo stills | task | M6.T14 (and M6.T15) status rows (Mac) | `done` |

**Inputs.** AGENTS.md §5 "PowerPoint presentation deliverables — mandatory JHU template" (every
bullet) and §7.2a; `tools/validate_presentation.py --help`;
`group-assignment/assignment1/build_deck.py` and `test_deck.py` (a builder whose deck passes the
validator, checked 2026-10-05); `course-project/build_proposal.py` (alt text, metadata);
`course-project/check_render_fit.py`; `course-project/report/Chen-Project-Report.tex` (the final
report's wording and references); `presentation/DELIVERABLES.md`; `presentation/takes.md`.

**Steps.**

*Session 1 — skeleton that passes the validator*

1. Mac: add `course-project/presentation/.build/` to the root `.gitignore` (if M6.T14 has not).
2. Mac: write **`course-project/presentation/collect_numbers.py`** (Mac `python3`, standard library).
   **Benchmark numbers come only from `course-project/report/generated/numbers.json`** (M5.T9's
   generated `{key: value}` file, the same values the report prints with `\bmnum`; key pattern
   `<metric>.<mode>.<condition>.<arm>[.<model_key>][.<stat>]`, for example
   `ate.replay.dup.l2.qwen35-a3b-think.median`, `plan/M5-report.md` "Generated-number key names").
   So the slides and the report can never disagree. The table `NUMBER_SOURCES` lists each slide key with
   its source: `("report", "<numbers.json key>", "<unit>", "<format>")` for benchmark numbers;
   `("demo", "evidence/M6/M6.T10/take<k>/segments.json", "<segment>.<field>")` for demo facts (decision,
   latency p50/p95, success); `("dv", "<dv.json key>")` for design values (read
   `configs/dv.json` → `values[<key>]["value"]`); `("design", "<doc>:<section>", "<exact text>")` for a
   fixed design fact quoted from a document (for example the 60 s p95 gate, `proposal-talk-track.md`,
   or the 2.0–2.5 m arena side, AGENT-DESIGN D3), where `collect_numbers.py` checks that `<exact
   text>` occurs in that document. It writes `presentation/numbers.json` =
   `{key: {"text": "<formatted with unit>", "value": …, "source": "<path>[#key]", "source_sha12": "…"}}`.
   With `--allow-pending`, a missing source gives `"text": "pending"`; without it, a missing source or
   key is an error. Read the real keys from `report/generated/MANIFEST.txt`; never guess a key.
   **Figures** come from `course-project/report/generated/figures/*.pdf` (M4.T16) and the M5.T2
   architecture figure: convert each with
   `pdftoppm -png -r 200 -singlefile <fig>.pdf course-project/presentation/figures/<name>` (Mac).
3. Mac: write **`course-project/presentation/build_deck.py`** (Mac `python3`). Copy these helpers from
   `group-assignment/assignment1/build_deck.py` (repository code written for Xiaohui, reuse allowed by
   README L11; keep a comment naming the source): `potx_to_pptx`, `drop_all_slides`,
   `sync_app_metadata`, `layout`, `ph`, `drop_ph`, `add_slide_number`, `set_logical_reading_order`,
   `_bu_none`, `body`, `padded_figure`, **plus every module-level constant and import they use**
   (find them with `grep -nE "^[A-Z_]+ *=|^from |^import " group-assignment/assignment1/build_deck.py`;
   for example `BUILD` and `FONT`), and set `BUILD` to `course-project/presentation/.build`. Run
   `python3 -c "import ast,sys; ast.parse(open('course-project/presentation/build_deck.py').read())"`
   and then the build to catch a missing name. That file was written for the Group Assignment 1 deck
   presented with a classmate; reusing its helpers is reuse of repository code written for Xiaohui
   (README L11), but say so in the disclosure. Then:
   - work on a copy in `presentation/.build/` (never touch the `.potx`, AGENTS.md §5);
   - `SLIDES` = a list of dicts `{"layout", "title", "blocks", "picture", "alt", "cite"}`, default
     outline below; text that contains a number uses `num("<key>")` (returns `numbers.json`'s `text`
     and records the key in `NUM_USES`);
   - pictures go into the layout's **picture placeholder** (idx 14 in `Two Column_50/50`), padded to the
     placeholder's aspect ratio first (`padded_figure`), with `descr` alt text ≥ 12 meaningful characters;
   - core properties: title "BeaconMind — Final Presentation", author and last-modified-by
     "Xiaohui Chen"; then `sync_app_metadata`;
   - `--final` fails if any text is "pending";
   - **no speaker notes** (the talk track is the handoff; `build_proposal.py` records that a notes
     master tripped the template-identity check on the quad-chart template; do not risk it here).
   Default outline (14 slides; change only per `DELIVERABLES.md`):

   | # | Layout | Title | Content (source) |
   | --- | --- | --- | --- |
   | 1 | Title Slide | BeaconMind: Can an LLM Own Landmark SLAM? | Course; "Xiaohui Chen (sole participant)"; date |
   | 2 | One Column | The Question and Why It Matters | Report Introduction (M5.T1); research questions; cited [n] |
   | 3 | Two Column_50/50 | BeaconMind at a Glance | Architecture figure (M5.T2) |
   | 4 | Two Column | What the LLM Owns, What the Tools Compute | D1b and the v3 split (AGENT-DESIGN) |
   | 5 | Two Column_50/50 | Arena, Beacons and Duplicated IDs | Arena photo or sim still; D3 |
   | 6 | Two Column_50/50 | One Step of the ReAct Loop | A terminal still (M6.T14) of one step; observation → tools → report → validator → move |
   | 7 | Two Column_50/50 | Demo in the Isaac Sim Twin | Sim still; per-segment outcomes and latency (`segments.json`); "demo, not benchmark" |
   | 8 | Two Column_50/50 | Demo on the Real Car | Car still; outcomes. Cut line: title "The Real Car: Logs, Not a Live Demo" with the M3 status |
   | 9 | One Column | Experimental Protocol | Replay vs closed loop, B0/B1/B2, seeds, K, primary metric (M5.T3) |
   | 10 | Two Column_50/50 | Results: Pose and Map Accuracy | M4.T16 figure (`report/generated/figures/`); numbers via `num()` |
   | 11 | Two Column_50/50 | Results: Missions, Refusals, Latency and Cost | M4.T16 figure or table; request-suite rate (M4.T14) via `num()` |
   | 12 | One Column | Limitations and What Went Wrong | Report Conclusion/limitations (M5.T5) |
   | 13 | One Column | Conclusions and Future Work | Report Conclusion (M5.T5) |
   | 14 | One Column | References and Generative-AI Disclosure | The references cited on slides 2–13 (from `mybibfile.bib`), then the disclosure paragraph |

   Do not use the `Image w/ Caption`, `Image Collage` or `Logo` layouts: they have no title placeholder
   (checked 2026-10-05).
4. Mac: write **`course-project/presentation/talk-track.md`**: `# Talk track — BeaconMind final
   presentation`, then one `## Slide N — <exact slide title>` per slide in order (the validator matches
   titles in order), each with the spoken text and its time; a "Before presenting" checklist; a
   "Generative-AI disclosure" section. Total words ≈ `talk_limit_min` × 130.
5. Mac: write **`course-project/presentation/validate_deck.sh`**:
   ```bash
   #!/usr/bin/env bash
   # AI-assisted: <model> via <tool>, <date>: validator call for the final deck (no exceptions by default).
   set -euo pipefail
   ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
   python3 "$ROOT/tools/validate_presentation.py" "$ROOT/course-project/presentation/Chen-BeaconMind-Final.pptx" \
     --expected-slides "${EXPECTED_SLIDES:-14}" --talk-track "$ROOT/course-project/presentation/talk-track.md"
   ```
   Any exception flag added later needs Xiaohui's approval and a written reason (AGENTS.md §5).
6. Mac: `python3 course-project/presentation/collect_numbers.py --allow-pending && python3
   course-project/presentation/build_deck.py && bash course-project/presentation/validate_deck.sh`.
   Expected last line: `PASS: …/Chen-BeaconMind-Final.pptx (0 warning(s))`. Fix every error (never add
   an exception to pass).
7. Mac: write **`course-project/presentation/test_deck.py`** (tests below) and run it.

*Session 2 — final content and review (after the results and stills exist)*

8. Mac: `collect_numbers.py` without `--allow-pending`; `build_deck.py --final`; `validate_deck.sh` → PASS.
9. Mac: **render review, engine 1 (LibreOffice):**
   `cd course-project/presentation && /opt/homebrew/bin/soffice --headless --convert-to pdf --outdir .build Chen-BeaconMind-Final.pptx && pdftoppm -png -r 90 .build/Chen-BeaconMind-Final.pdf .build/page`;
   look at every page image (Read them); then `python3 ../check_render_fit.py Chen-BeaconMind-Final.pptx .build/Chen-BeaconMind-Final.pdf`
   → last line `PASS: every rendered word lies inside its text shape`.
10. Mac: **render review, engine 2 (Quick Look):** write `presentation/make_quicklook.py` that saves
    one copy of the deck per slide with every other slide removed (`drop_rel` as in `drop_all_slides`)
    into `.build/quicklook/slide-<n>.pptx`; then
    `for f in .build/quicklook/slide-*.pptx; do qlmanage -t -s 1600 -o .build/ql "$f" >/dev/null; done`;
    look at every thumbnail (AGENTS.md §5: "Both render paths are required").
11. Mac: **Accessibility Checker:** PowerPoint is not installed on the Mac (checked 2026-10-05). Write in
    `presentation/REVIEW.md`: "PowerPoint Accessibility Checker not run: PowerPoint is unavailable on
    this Mac; deferred" (AGENTS.md §5 requires saying so). Review the reading order manually on the
    renders.
12. Mac: **adversarial review**, three lenses, each recorded in `presentation/REVIEW.md` with findings
    and fixes: (a) *accuracy* — every claim and number traces to `numbers.json`, the report or
    AGENT-DESIGN; citations on the slides that use them; (b) *template and accessibility* — the
    AGENTS.md §5 bullets one by one; (c) *honesty* — demo results never presented as benchmark results;
    simulation never called the car; the cut line, the latency gate and failed segments stated plainly.
    Loop until a lens finds nothing (as AGENTS.md §6 does for knowledge-point documents).
13. Mac: export the final PDF next to the deck: `cp .build/Chen-BeaconMind-Final.pdf
    Chen-BeaconMind-Final.pdf` (tracked; check size < 10 MB). Status table; `CONTEXT.md`.

**Deliverables.** `course-project/presentation/collect_numbers.py`, `numbers.json`, `build_deck.py`,
`make_quicklook.py`, `talk-track.md`, `validate_deck.sh`, `test_deck.py`, `REVIEW.md`,
`Chen-BeaconMind-Final.pptx`, `Chen-BeaconMind-Final.pdf`, `figures/` (stills and result figures);
root `.gitignore` line.

**Tests.** `course-project/presentation/test_deck.py` (Mac: `python3 -m pytest -q course-project/presentation/test_deck.py`):
- `test_slide_count` — equals `EXPECTED_SLIDES` (from `DELIVERABLES.md`, default 14).
- `test_layouts_in_order` — slide layouts equal the outline's layout column.
- `test_titles_match_talk_track` — the ordered slide titles equal the `## Slide N — …` headings.
- `test_pictures_have_alt_text` — every picture has `descr` ≥ 12 characters that is not a file name and
  not `Picture N`.
- `test_core_properties` — author and last-modified-by are "Xiaohui Chen"; title set.
- `test_final_slide_disclosure` — the last slide's text contains "Generative-AI disclosure".
- `test_numbers_registered` (final mode only; skipped while any number is pending) — every quantity
  with a unit on any slide (regex `\d+(\.\d+)?\s?(%|m|s|°|cm|USD|\$)`) equals the `text` of a key in
  `NUM_USES`, so no number is typed by hand.
- `test_validator_passes` — runs `validate_deck.sh` in a subprocess; exit code 0.
Expected: skeleton `7 passed, 1 skipped`; final `8 passed`.
Smoke: steps 9 and 10 (both renders viewed; `check_render_fit.py` PASS).

**Acceptance criteria.**
- [ ] Validator PASS with zero exceptions (or each exception approved by Xiaohui with its reason).
- [ ] `test_deck.py` → `8 passed` in final mode.
- [ ] Both render engines viewed; `check_render_fit.py` PASS; Accessibility Checker status stated.
- [ ] `REVIEW.md` shows the three lenses ending clean.
- [ ] Every number on the slides comes from `numbers.json`.

**Evidence to save** (`evidence/M6/M6.T5/`): `validator.txt`; `test-deck.txt`; `render-fit.txt`;
`contact-sheet.jpg` (a Pillow contact sheet of the LibreOffice pages, ≤ 1 MB).

**Pitfalls and known gotchas.**
- python-pptx cannot open a `.potx` directly: repackage it (`potx_to_pptx`).
- `insert_picture` into a picture placeholder **crops** to fill: pad the image to the placeholder's
  aspect first.
- A latent slide-number placeholder needs `add_slide_number` (the group builder's method), otherwise
  the validator asks for a scoped `--allow-slide-number-fallback`.
- Keep `docProps/app.xml` in sync (`sync_app_metadata`) after every change of titles or count.
- No `timeout` binary on macOS (AGENTS.md §7.2a); do not wrap `soffice` in one.

**Stop-and-ask conditions.** The slide limit from M6.T1 is below 10 (the outline must be cut; ask which
slides go); the validator demands an exception; a result needed on a slide does not exist.

**Estimated effort.** M (two sessions as marked).

**AI-disclosure note.** Slide 14 carries the disclosure paragraph (validator rule); `talk-track.md` ends
with "Generative-AI disclosure"; the scripts carry `AI-assisted: …` and `build_deck.py` adds `Derived
from: group-assignment/assignment1/build_deck.py (helpers copied, written for Xiaohui; see its
disclosure)`.

---

### M6.T17 — Rehearsal and, if required, the recorded presentation

**Why.** The talk must fit the limit from M6.T1, and the demo video must play cleanly inside it. If the
presentation is recorded (M6.T1 question 2), the recording is itself a submitted artifact and must show
the disclosure.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M6.T5 and M6.T16 done | task | status rows (Mac) | `done` |
| Final PDF and video on the Mac | file | `ls course-project/presentation/Chen-BeaconMind-Final.pdf course-project/presentation/video/Chen-BeaconMind-Demo.mp4` (Mac) | both files |

**Inputs.** `presentation/talk-track.md`; `presentation/DELIVERABLES.md`; MD7.

**Steps.**
1. Mac: create `course-project/presentation/rehearsal-log.md` with a table `| Run | Date | Total time |
   Per-slide times | Over/under | Changes made |`.
2. **Xiaohui (Mac) — rehearsal 1.** *What:* present from the PDF in Preview full screen (MD7), playing
   the demo video from QuickTime Player at slide 7 (or wherever the talk track says), with a stopwatch.
   *Why:* the PDF is the validated rendering; Keynote's import of a `.pptx` can move text. *Pass:* total
   time within ±10 % of `talk_limit_min`. Xiaohui reports the per-slide times.
3. Mac: adjust `talk-track.md` (and the slides, re-running M6.T5 steps 8–9 if they change) to fix the
   overruns; log the changes.
4. **Xiaohui — rehearsal 2.** Same pass rule.
5. If the presentation is **recorded**: **Xiaohui** records it (Panopto, as for the module discussions,
   or QuickTime Player → File → New Screen Recording with the microphone on). Before recording: Do Not
   Disturb on; no terminal, browser tab or notification on screen; the disclosure slide shown for at
   least 5 s. Afterwards the executor checks, from the file if Xiaohui shares it (QuickTime Player →
   Window → Show Movie Inspector shows the duration on the Mac; or `ffprobe` on the Spark): duration
   within the limit; audio present; the last slide visible. If only Panopto has it, Xiaohui reports the
   duration and confirms the disclosure slide.
6. Mac: status table; `CONTEXT.md`.

**Deliverables.** `course-project/presentation/rehearsal-log.md`; updated `talk-track.md` (and deck if
changed); the recording (Xiaohui's, not in the repository).

**Tests.**
- Rehearsal measurement: total time with a stopwatch, two runs, each within ±10 % of the limit.
- Recording check (if recorded): duration ≤ limit; audio stream present; disclosure slide visible ≥ 5 s.
- If the deck changed: `bash course-project/presentation/validate_deck.sh` → PASS and
  `python3 -m pytest -q course-project/presentation/test_deck.py` → `8 passed`.

**Acceptance criteria.**
- [ ] Two rehearsals logged, the second within ±10 %.
- [ ] If recorded: the recording checks pass and are written in `rehearsal-log.md`.

**Evidence to save** (`evidence/M6/M6.T17/`): `rehearsal-log.md` copy; `recording-check.txt` (if
recorded).

**Pitfalls and known gotchas.** Switching from Preview to QuickTime for the video costs seconds; rehearse
the switch. The Mac has 8 GB RAM: close other apps while recording.

**Stop-and-ask conditions.** Both rehearsals more than 10 % over the limit (ask which content to cut).

**Estimated effort.** S (plus Xiaohui's rehearsal time).

**AI-disclosure note.** `rehearsal-log.md` ends with the disclosure line; the recording's disclosure is
the final slide, shown and spoken.

---

### M6.T6 — Final submission package and an AI-disclosure audit of every artifact

**Why.** The last task of the project (README §3.4: at ≤ 7 days left, only M5.T7 and M6.T6 run). It
proves that every artifact carries its disclosure (AGENTS.md §5: undisclosed AI use is misconduct),
that no secret leaks (L9, S12), and that every file the course asks for exists in the right format,
then records the end state in `CONTEXT.md`. **Xiaohui submits; the executor never uploads.**

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M5.T7 done (final report) | task | `grep -E '^\| M5\.T7 ' course-project/plan/M5-report.md` (Mac) | `done` |
| M6.T5, M6.T16, M6.T17 done | task | status rows (Mac) | `done` |
| Every other M6 task `done` or `dropped (cut line)` | task | `grep -E '^\| M6\.T' course-project/plan/M6-demo-presentation.md` (Mac) | no `todo`, `in-progress` or `blocked` |

**Inputs.** `presentation/DELIVERABLES.md` (the submission list); AGENTS.md §5 (disclosure, third-party
code), §9 (git); README L9, L10, L11; every milestone file's status table.

**Steps.**
1. Mac: write **`course-project/tools/disclosure_audit.py`**, CLI
   `python3 course-project/tools/disclosure_audit.py --root course-project [--csv out.csv]`:
   - file list = `git ls-files <root>` plus untracked, not-ignored files (`git ls-files --others
     --exclude-standard <root>`);
   - **code files** (`.py`, `.sh`, `.c`, `.h`, `.cpp`, `.launch.py`, `.xml`, `.yaml`, `.yml`,
     `CMakeLists.txt`, `Dockerfile`, `Makefile`, `.ino`): pass if the first 60 lines contain
     `AI-assisted:` or `Generative-AI disclosure`, or the file is a vendored copy whose first line
     starts with `# Copied unchanged from` and whose source carries a disclosure, or the file is listed
     in `ALLOW_NO_AI` with a reason (for a file Xiaohui wrote alone, which they confirm);
   - **written work** (`.md` under `presentation/`, `report/`, `evidence/` narratives, `plan/`, and the
     design documents at the top of `course-project/` — `AGENT-DESIGN.md`, `APPROACH-LLM-SLAM.md`,
     `proposal-talk-track.md`, `CONTEXT.md` — and `.tex`): pass if the text contains
     `Generative-AI disclosure` or `AI-assisted:`;
   - **slide decks** (`.pptx`, including the submitted proposal deck `Chen-Project-Proposal.pptx` and the
     final deck): open the file with the standard-library `zipfile`, read every `ppt/slides/slide*.xml` and
     `ppt/notesSlides/*.xml`, and pass if any of them contains `Generative-AI disclosure`, `AI-assisted` or
     `AI disclosure` (added by the cross-plan consistency review, 2026-10-06, so the deck and talk track are
     audited with the report — AGENTS.md §5);
   - **JSON** under `configs/` and `presentation/`: pass if the folder's `README.md` names the file in a
     line containing `AI-assisted:`;
   - prints one line per failing file and a final `audit: <n> files checked, <m> missing`; exit code 1 if
     `m > 0`.
2. Mac: write `course-project/beaconmind/tests/test_disclosure_audit.py` (below) and run it.
3. Mac: run the audit on `course-project/`; fix every missing disclosure by **adding** the line (with
   the true model and date: ask Xiaohui which tool wrote a file if the history does not say); re-run
   until `0 missing`. Also run it on `assignments/assignment2/ollama/docker-compose.yml` (changed by
   M6.T2).
4. Mac: **secrets scan** of everything that will be submitted or shown:
   ```bash
   cd /Users/xiaohuichen/Projects/EN.665.715 && \
   git ls-files course-project | xargs grep -nIE "sk-[A-Za-z0-9_-]{8,}|OPENAI_API_KEY=|ANTHROPIC_API_KEY=|password|ssid" \
     | tee course-project/evidence/M6/M6.T6/secrets-scan.txt
   ```
   Every hit must be reviewed: a real secret → stop and ask (remove it, and Xiaohui rotates the key); a
   word in prose ("never print the Wi-Fi password") → note it as benign in `secrets-scan-review.md`.
   Also confirm `git ls-files | grep -E "wifi_config.h|secrets.*\.env"` prints nothing.
5. Mac: **report** (from M5.T7): `pdfinfo course-project/report/Chen-Project-Report.pdf | grep Pages`;
   `pdftotext course-project/report/Chen-Project-Report.pdf - | grep -c "Generative-AI"` ≥ 1; page
   count within any limit in `DELIVERABLES.md`.
6. Mac: **deck**: `bash course-project/presentation/validate_deck.sh` → PASS; the PDF export exists.
7. Spark host: **video**: re-run M6.T16's `ffprobe` checks on the final file and compare its SHA-256 with
   `evidence/M6/M6.T16/sha256.txt`.
8. Mac: write **`course-project/presentation/SUBMISSION-README.md`** (it goes into the code archive):
   what BeaconMind is (two paragraphs, from the report abstract), the folder map (L1), how to run the
   unit tests (L4 commands), where the results come from, the demo's status (not benchmark-comparable),
   the commit hash (filled in step 10), and the full generative-AI disclosure.
9. Mac: write **`course-project/tools/make_code_archive.sh <commit> <out.zip>`**:
   ```bash
   #!/usr/bin/env bash
   # AI-assisted: <model> via <tool>, <date>: builds the code archive from one commit.
   set -euo pipefail
   cd "$(git rev-parse --show-toplevel)"
   git archive --format=zip --prefix=BeaconMind/ -o "$2" "$1" -- course-project \
     ':(exclude)course-project/QuadChart-Template.pptx'
   unzip -l "$2" | tail -1
   ```
   (git 2.50 on the Mac supports exclude pathspecs, checked 2026-10-05.) The archive therefore holds
   only **committed, tracked** files: no `data/`, no keys, no `wifi_config.h`, no videos, no reading
   PDFs (all git-ignored), and not the instructor's quad-chart template.
10. **Ask Xiaohui to approve a commit** of the final state (README L10: commit only when asked). When they
    do: stage only the changed paths, commit with a message naming M6.T6 and the attribution lines the
    session's instructions give, put the commit hash into `SUBMISSION-README.md`, commit that too, then
    `bash course-project/tools/make_code_archive.sh HEAD ~/Desktop/Chen-BeaconMind-code.zip`. Check:
    `unzip -l ~/Desktop/Chen-BeaconMind-code.zip | grep -cE "QuadChart|/data/|wifi_config|\.mp4"` → `0`;
    the size is under any limit in `DELIVERABLES.md`; run the step-4 grep on `unzip -p` output → only
    the reviewed benign hits.
11. Mac: write **`course-project/presentation/SUBMISSION-CHECKLIST.md`**: one row per item in
    `DELIVERABLES.md`'s submission list: `| Item | File | Format | Size | Check | Result | Where to submit
    | Submitted (Xiaohui ticks) |` — report PDF, slides `.pptx` (and PDF), demo video, presentation
    recording (if required), code archive. Every "Check" cell names the command run above and its result.
12. Mac: **final `CONTEXT.md` update** (text in "CONTEXT.md update on completion" below), the M6 status
    table, and README §9's milestone status line if Xiaohui wants it updated (README edits are fine;
    AGENTS.md edits are not, without asking).
13. Tell Xiaohui: the checklist is ready; they upload each file and tick the last column; ask them to
    report back so the executor can record "submitted <date>" in `CONTEXT.md`.

**Deliverables.** `course-project/tools/disclosure_audit.py`, `course-project/tools/make_code_archive.sh`,
`course-project/beaconmind/tests/test_disclosure_audit.py`, `course-project/presentation/SUBMISSION-README.md`,
`course-project/presentation/SUBMISSION-CHECKLIST.md`; disclosure lines added where missing; the code
archive (outside the repository); the final `CONTEXT.md` entry; one commit (when Xiaohui asks).

**Tests.**
- `course-project/beaconmind/tests/test_disclosure_audit.py` (builds a temporary git repository fixture):
  - `test_py_without_disclosure_listed` — a `.py` without the line is reported missing.
  - `test_py_with_disclosure_ok` — `AI-assisted:` in the docstring passes.
  - `test_vendored_copy_ok` — a file starting `# Copied unchanged from` passes.
  - `test_json_covered_by_readme` — a JSON file named in its folder's `README.md` with `AI-assisted:`
    passes; one not named fails.
  - `test_exit_code` — exit code 1 with one missing file, 0 with none.
  - `test_pptx_disclosure_detected` — a minimal `.pptx` built with `zipfile` (one
    `ppt/slides/slide1.xml` containing `Generative-AI disclosure`) passes; the same file without the text is
    reported missing.
  Command (Mac): `cd course-project/beaconmind && ../.venv/bin/python -m pytest -q tests/test_disclosure_audit.py`
  → `6 passed`.
- Smoke: `python3 course-project/tools/disclosure_audit.py --root course-project` → last line
  `audit: <n> files checked, 0 missing`.
- Package checks: steps 4–7 and 10, each with its expected output above.

**Acceptance criteria.**
- [ ] Audit `0 missing`; secrets scan reviewed with no real secret.
- [ ] Report, deck and video checks pass; the code archive built from an approved commit, with the
      exclusions verified.
- [ ] `SUBMISSION-CHECKLIST.md` complete except Xiaohui's "Submitted" ticks; final `CONTEXT.md` entry
      written.

**Evidence to save** (`evidence/M6/M6.T6/`): `audit.txt`; `secrets-scan.txt`, `secrets-scan-review.md`;
`report-check.txt`; `validator.txt`; `video-check.txt`; `archive-check.txt` (`unzip -l` tail, the
exclusion grep, the size); `SUBMISSION-CHECKLIST.md` copy.

**Pitfalls and known gotchas.** `git archive` includes only committed files: run it after the approved
commit, not before. Copyrighted reading PDFs (`report/sources/`) and the JHU template stay out of
anything distributed beyond this private repository (AGENTS.md §5; the deck itself, built from the
template, is the intended use). Do not "fix" a disclosure by writing a model name you are not sure of:
ask.

**Stop-and-ask conditions.** A real secret found; a file whose authorship (human or which model) cannot
be established; any item missing from the submission list; the archive exceeds a size limit.

**Estimated effort.** S.

**AI-disclosure note.** The two tools and the test: `AI-assisted: …`. `SUBMISSION-README.md` and
`SUBMISSION-CHECKLIST.md` end with a "Generative-AI disclosure" paragraph listing every model used in
the project (from the code headers and `CONTEXT.md`), what each assisted with, and that Xiaohui Chen is
responsible for the work.

---
## Milestone-level integration smoke test

Run this after M6.T12 (it needs no model, no Isaac and no car), and again before M6.T6 as a regression
check. It exercises every M6 code path end to end on a stub session.

1. Spark host (session folder on the host; both processes in `beaconmind-ros`):
   ```bash
   cd ~/Projects/EN.665.715/course-project && P=~/.venvs/beaconmind/bin/python
   S=$($P -m beaconmind.demo.new_session --source kinsim --label itest --world <M6.T7 fixture world> \
       --script configs/demo_script.json --decider stub --model-key none | tail -1); I=$(basename "$S")
   docker exec -d -w /workspace/course-project/beaconmind beaconmind-ros python3 -m beaconmind.demo.env_server \
       --session /workspace/course-project/data/demo/$I --env kinsim
   docker exec -w /workspace/course-project/beaconmind beaconmind-ros python3 -m beaconmind.demo.run \
       --session /workspace/course-project/data/demo/$I --decider stub
   docker exec -w /workspace/course-project/beaconmind beaconmind-ros python3 -m beaconmind.demo.score \
       --session /workspace/course-project/data/demo/$I
   $P -m beaconmind.demo.video_cli plan --session "$S"
   for w in term panel topdown; do $P -m beaconmind.demo.video_cli render --session "$S" --what $w; done
   $P -m beaconmind.demo.video_cli compose --session "$S" --main video/topdown --by-segment
   ~/.local/bin/ffprobe -v error -select_streams v:0 -count_frames -show_entries stream=codec_name,width,height,nb_read_frames -of csv=p=0 "$S"/video/sim_explore.mp4
   ```
   (The stub runner sends `shutdown` at the end, so the detached environment server exits.)
2. Mac: `cd course-project/beaconmind && ../.venv/bin/python -m pytest -q tests/test_demo_*.py` → every
   test passes (the count is the sum of the files written so far; write it down); the same in
   `beaconmind-ros` with the L4 command; the `rosa-ros2` subset of M6.T2 → `8 passed`.
3. Mac: `bash course-project/presentation/validate_deck.sh` → `PASS` (skeleton is fine) and
   `python3 -m pytest -q course-project/presentation/test_deck.py` → no failures.
4. Mac: `python3 course-project/tools/disclosure_audit.py --root course-project/beaconmind/src/beaconmind/demo`
   → `0 missing` (once M6.T6 has written the audit tool; before that, skip and say so).

**Pass:** `segments.json` has four entries, all `scored: true`, with the refuse segment `REFUSED` and
`moves_after_answer` 0; `data/LATCH` was not created (`test -e data/LATCH` false); the `ffprobe`
line reads `h264,1920,1080,<the explore segment's EDL frames>`; every test command passes; the
validator passes. Save the outputs to `evidence/M6/integration-smoke-<date>.txt`.

## Milestone exit checklist

- [ ] Every row of the status table is `done` or `dropped (cut line)`, each with its evidence path.
- [ ] `presentation/DELIVERABLES.md` answered by Xiaohui (M6.T1).
- [ ] MD1–MD7 answered and recorded (`CONTEXT.md`; MD1–MD3 also in AGENT-DESIGN D10).
- [ ] Simulation take kept by the M6.T10 rule; `takes.md` lists every take including aborted ones.
- [ ] Car take kept (M6.T3), or the cut line invoked and stated on the honesty card and slide 8.
- [ ] Final demo video checked (duration, format, loudness, title first, disclosure last), SHA-256
      recorded.
- [ ] Deck: validator PASS, `test_deck.py` final mode passes, both renders viewed, `REVIEW.md` clean,
      Accessibility Checker status stated.
- [ ] Rehearsals within ±10 %; recording checked if required.
- [ ] Disclosure audit `0 missing`; secrets scan reviewed; code archive built from an approved commit.
- [ ] Integration smoke passed on the final code.
- [ ] `CONTEXT.md` final entry written; Xiaohui has the submission checklist.

## CONTEXT.md update on completion

Add this entry at the top of `CONTEXT.md` (below the title), with every `<…>` filled from the evidence:

```markdown
## <YYYY-MM-DD> — M6 done: demo, video, slides and submission package

- **Demo (ROSA, demo-only, not benchmark-comparable, AGENT-DESIGN D10):** runtime = `bm-tools` MCP
  server + environment server + ROSA runner (`beaconmind/src/beaconmind/demo/`); ROSA mode <MD1>;
  model <key> (thinking <on/off>).
  - Simulation take <session id> (take <k> of <n>): explore <outcome>, return <outcome>, goto <target>
    <outcome>, refuse <decision> with <0> moves; decision latency p50 <a> s / p95 <b> s.
  - Car take <session id> (take <k> of <n>; resumes: <none / list>): <outcomes> — or "not run: cut line,
    <reason>".
- **Video:** `data/demo/video/Chen-BeaconMind-Demo.mp4` on the Spark (Mac copy
  `presentation/video/`, git-ignored), <duration>, SHA-256 <sha12>; simulation footage = <Isaac
  re-render / 2D fallback>.
- **Slides:** `presentation/Chen-BeaconMind-Final.pptx` (+ PDF), <N> slides, validator PASS on <date>;
  talk track `presentation/talk-track.md`; rehearsed at <mm:ss>.
- **Package:** `presentation/SUBMISSION-CHECKLIST.md`; code archive from commit <hash>; disclosure audit
  0 missing; secrets scan clean.
- **Containers left:** <rosa-ros2 state, with the course-project mount (M6.T2)>; <vllm-rosa state>;
  <beaconmind-ros state>; micro-ROS agent removed.
- **Hardware state at the end:** <jumper, USB, battery switch, pack voltage, latch file absent>.
- **Submitted by Xiaohui:** <items and date, once they report it>.
```

## Risks specific to M6

| Risk | Effect | Mitigation | Where |
| --- | --- | --- | --- |
| Decision latency (Qwen3.5 thinking: a 91 s best case and an 18-minute queued median in the pilot, talk track) | Takes run for hours; the 60 s p95 gate may be missed in the demo | OD8's setting; no sweep during a take; the time-lapse compresses thinking with its speed shown; the gate stated honestly if missed | M6.T4, T10, T16 |
| The model fails a segment (EXPLORE never ends, the go-to stalls, the refusal fails: 6 of 10 refused in the 2026-09-27 smoke) | A weaker demo | Show it honestly; the honesty card and slides give the benchmark rates; re-selection of the world only with Xiaohui's approval and disclosure (MD4) | M6.T4, T10 |
| Stock ROSA tools can actuate outside the validator | A safety bypass on the car | MD1 trimmed by default; M6.T2 step 5 inventories the tools; stock forbidden on the car if any can actuate | M6.T2, T3 |
| `rosa-ros2` changes break earlier course work | Module 4/5 demos stop working | One mount line only, image kept; Module 4 tests re-run; rollback written in M6.T2 step 7; MD3 alternative container | M6.T2 |
| M2/M3 APIs differ from what this file assumes | Adapters cannot be written | Each task starts with an API-surface verification step and stops on a mismatch rather than reimplementing M2 logic | M6.T2, T7 |
| Isaac kinematic re-render does not update frames | No simulation picture | Three update modes tried in a spike; the 2D top-down fallback (MD5), labelled | M6.T13 |
| Wi-Fi losses and brownouts on the car | Latches mid-segment; a dead pack | Resume only at segment boundaries, stated on the card; battery checks between segments; tray spring first suspect | M6.T3 |
| Phone footage out of sync or HDR | Picture and terminal disagree | 1080p30 SDR test clip first; sync on the first motion and verify on the last (≤ 0.5 s) | M6.T3, T15 |
| A secret or personal item appears on screen | Privacy breach in a submitted video | The terminal renderer refuses frames matching secret patterns; the arena framed without personal items; review of every final video | M6.T12, T15, T16 |
| The deck fails the validator late | A blocked submission | Skeleton deck built and validated in M6.T5 session 1, long before the results exist | M6.T5 |
| Time runs out (calendar rules) | No video or slides | Finish M6.T16 and M6.T5 before 8 days are left; cut line drops the car parts; at ≤ 7 days only M6.T6 | all |
| Unclear final requirements | Wrong formats or lengths | M6.T1 first; every derived setting comes from `DELIVERABLES.md` | M6.T1 |

## Generative-AI disclosure

Claude Opus 5.5 via Claude Code wrote this milestone file on 2026-10-05: the task breakdown, the M6
decisions MD1–MD7 and their defaults, the demo file formats (M6-C1 to M6-C8), the steps, tests,
acceptance criteria, risks and the skeleton code. It grounded the plan in read-only checks made that
day on the Mac and the Spark (listed in "Facts this file relies on") and in the repository's design
documents, the Module 2, 4 and 5 discussion code and recipes, and the plan README. Every MD item is a
proposal for Xiaohui Chen to approve or overturn; nothing in this file has been executed. Xiaohui Chen
owns the project and decides when each task runs.

Claude Opus 5.5 via Claude Code also ran an adversarial review of this file on 2026-10-06 and corrected
it in place: cross-milestone task IDs aligned with the M2–M5 files (M2.T13/T14/T15/T16/T17/T20,
M3.T13/T17/T18/T20, M4.T14/T16, M5.T9), the latch scoped per session kind, the tmux runner arguments,
the vendored prompt's import-time prints and `rosa` dependency, the estop lock and a deterministic
estop check, post-hoc scoring outside `rosa-ros2`, the card budget, the narration mux, the refusal
segment rules, the car-take power-path and STOP checks, and the slide numbers' single source
(`report/generated/numbers.json`). The review made read-only checks only (file reads on the Mac); none
of the steps were run.

Cross-plan consistency review, 2026-10-06, by Claude Opus 5.5 via Claude Code: cross-milestone task IDs, shared files and contracts aligned with the other five milestone files and `plan/README.md` (details and the list of edits in `plan/REVIEW.md`). Read-only checks on the Mac only; nothing was run on the Spark.

Follow-up edit, 2026-10-24, by Claude Opus 5.5 via Claude Code: M6.T3's ghost-node pitfall follows the revised README S11 (the firmware's session supervisor rebuilds the session after an agent restart; reboot the Pico by hand, battery off, only if `/bm_pico` is not back within 30 s). M6.T3 step 9 says to lift the car onto the start mark, never slide or roll it (README S13). Read-only checks on the Mac only; nothing was run on the Spark.
