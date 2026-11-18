# Closed loop in the simulator (work list 4.1; M2.T1 validator part, M2.T7 closed-loop part, M2.T19)

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote the closed-loop harness, the validator, the runner,
the tests and this note, and ran the episodes below. Xiaohui Chen approved the API spend.

Date: 2026-11-18 (runs 02:37 to 02:47 CST; the container's log times are UTC). Code state: commit `898f3d0` plus the
uncommitted new files listed below (`git_dirty` in each `run.json`).

## What this is

In the pre-registered study every model read the **same recorded** observations (replay). Here the model's own move
is checked, executed in the simulator, and decides what it sees next. The pieces of the study that are frozen by the
pre-registration (prompt v3.3, tools, provider tool loop, report parser, fallback and repair rules, counter rule) are
imported unchanged; `prereg_freeze.py --verify` still prints OK (`prereg_verify.txt`).

**Result in one paragraph (final episodes, 2026-11-18, final room simulator).** One EXPLORE episode each of
Claude Opus 5.5, Claude Fable 5.2 and the coded procedure B2 in the simulated real room: 20-tag nominal layout,
start S1 (2.50, 1.50, 90°), measured-camera visibility, 3.0 m range limit, 0.4 m inset of the driving area, noise
seed 3000. All three ended with DONE and mapped 14 of the 20 tags with no phantom; ATE 2.3 cm for all three; no
move was refused, no report was invalid, no emergency stop. **The two models made the identical 55 moves (56
steps); B2 made 57 (58 steps).** The models left B2's path at step 35, and the cause is the pose each gave to
`exploration_summary` at step 31: B2 passed its unrounded pose (−0.4392, −0.2389) and was told a 2-move leg;
Opus 5.5 passed that pose rounded to two decimals (−0.44, −0.24), and Fable 5.2 passed (−0.46, −0.23), the
odometry prior of that step (the step-30 position, before the step's position fix), and both were told a 1-move
leg. Given the tool result each model obtained there, every later decision is the coded procedure's: recomputed
from each step's observation and the model's own previous report, the procedure's decision equals the model's at
all 56 steps of both models. Cost
US$4.60 (Opus 5.5) and US$8.33 (Fable 5.2); about 20 s a step for both. **n = 1 episode per arm: no difference
between the models is statistically established, and the episode shows agreement with the coded procedure, not a
difference in driving.**

A first pair of episodes, run earlier the same night on a draft of the room simulator, is kept below, labelled
superseded.

## Files

| File | What |
| --- | --- |
| `beaconmind/src/beaconmind/harness/validator.py` | Move checks, refusal reasons, safety block, auto-latch, per-episode latch file |
| `beaconmind/src/beaconmind/harness/closed_loop.py` | Step loop, environment protocol and adapters (study square, room), B2 driver, Anthropic driver, C9.2 export |
| `beaconmind/src/beaconmind/metrics/closed_loop.py` | Episode summary and scores (uses the frozen `metrics/pilot.py`), comparison table |
| `tools/closed_loop_run.py`, `tools/closed_loop_run.sh` | Runner (configuration tag, hard spend cap, resume) and its container launcher |
| `configs/providers_demo.json` | The Claude Fable 5.2 entry (`configs/providers.json` is frozen) |
| `beaconmind/tests/test_validator.py` (21 tests), `tests/test_closed_loop.py` (30 tests) | No network |

## Design and decisions

Each one is where the design left something open; the choice is the one closest to AGENT-DESIGN D4-D8 and the frozen
prompt, and the reason is given.

1. **What executes is the accepted `move(action)` tool call, not the text of the report.** The prompt says "Move
   only via move(action)" and "8 Call move(action) for a move decision"; M2.T1 calls the tool "the only path to
   motion". The frozen tool dispatcher (`tools_d5.run_tool`) already answers `move` in closed-loop mode with the
   prompt's contract (`done`, or `refused` with a reason, at most one accepted move per `obs_id`). The loop takes the
   move the dispatcher accepted, checks it again with `validator.check_move`, and only then sends it to the
   environment. The report's `decision` is logged beside it (`decision`, `decision_written`), and a disagreement is a
   `decision_mismatch` violation. A move decision written without a `move` call executes nothing.
2. **A second, independent check before execution.** `validator.check_move` gives the same verdict and the same
   reason text as the dispatcher for every case the dispatcher knows (tested over 1,344 combinations), and adds the two
   refusals of D5 that the dispatcher lacks: `status: error` and `steps_left` 0. If the two ever disagree the move is
   not executed (`validator_override`). The check fails closed: a missing or non-boolean flag refuses the move. The environment is a third guard: it refuses a forward move its own wall
   check does not allow (C2: the executor enforces its own limits).
3. **Refusals are answered inside the step**, as guardrail 1 says ("A refused move does not use up the step: decide
   again ..."): the tool result is `{"result": "refused", "reason": ...}` and the model may call `move` again. The
   **next** OBSERVATION's `last_move` then says what happened: the executed move with the executor's result;
   `{action, "refused"}` if the step's only move calls were refused; `{action, "not_called"}` if the report named a
   move that was never called; null if the step decided no move. A step without motion has zero odometry, never null
   (null means a Pico reboot and triggers `emergency_stop`).
4. **An invalid report after an accepted move: the move is still executed** (unless a latch is set by then, see 5).
   The model was already told `done`. The
   report is replaced by the replay fallback (previous report dead-reckoned through this step's odometry, decision
   NONE), exactly as `harness/replay.py` does.
5. **Latch (C5.2, D6).** Sources: `emergency_stop`; 2 consecutive contacts (`stalled` or `bumped`;
   `autolatch_contacts` from `configs/dv.json`) or any `link_lost`; 2 consecutive error observations; null odometry
   after step 0 (a Pico reboot); and a latch file written by someone else (the episode's own `seed_<n>.LATCH` or any
   `--watch-latch` path such as the project-wide `data/LATCH`), read before every observation and again just before
   a move is executed. One contact does not latch, because D7 row 1 recovers from it with BACKWARD_10. **Nothing is
   executed once a latch is set**, including a move the tool accepted earlier in the same step (the model called
   `move` and then `emergency_stop`, or a STOP arrived while the model was thinking): safety is put before the `done`
   the model was told. A latched episode ends (`ended_by: latch`), leaves `seed_<n>.LATCH`, and the runner does not
   start the remaining seeds (exit code 3); only `python -m beaconmind.harness.validator clear-latch <file>
   --operator <name>` removes the file. The slip auto-latch is not implemented (no environment reports slips).
6. **`backward_allowed`** is true only directly after an executed forward move whose result was done, stalled or
   bumped (D4).
7. **How an episode ends** (C9.2 `ended_by`): decision DONE; decision STOPPED; latch; step budget (150 observations,
   `steps_left` counts down from 150 as in `kinsim_lite.run_episode`); or 3 consecutive steps without an executed
   move (`error`, `no_progress`). The last rule is new: nobody answers an ASK in an unattended run, and a model that
   never calls `move` would otherwise idle to the budget. The USD cap never ends an episode: the unfinished step is
   not written and nothing is executed, so a rerun resumes it.
8. **State rules are the replay's**: counters reset only on a verified full fix (`verify_fix`), the pose and map are
   scored as written, invalid reports become counted fallbacks, a report missing up to three closing characters is
   repaired and counted.
9. **Resume re-simulates, and only a simulator can be resumed.** A rerun replays the logged moves through the
   simulator and refuses to continue unless every logged observation and true pose is reproduced exactly. An
   environment must declare `deterministic_replay = True` for that; a real car never does, so a resume can never
   drive logged moves a second time. Every move is also written to `seed_<n>.moves.jsonl` before the executor is
   called (`commanded`) and after (`result`), so a crash between the two leaves a trace. A provider failure raises before anything is
   written or executed, so there is never a half-written step.
10. **B2 goes through the same loop**: `B2Driver` makes the procedure's tool calls through the same dispatcher
    (including `move`) and answers with its report as JSON text. On the study square it reproduces
    `kinsim_lite.run_episode` step for step (truth, raw observation, report; seeds 1003 and 1010 in the tests), and
    in the room it reproduces `kinsim_room.run_episode`. That is the check that the loop and the adapters are right.
11. **The model never sees ground truth.** The true tag behind a detection (`_tag`), the true pose and the world
    stay in the log; a test serialises every request and checks that none of them appears.

**Environment protocol** (docstring of `closed_loop.py`): `env.source`, `env.describe()`, `env.reset(seed)`,
`env.step(action or None)`, `env.truth()`. `KinsimSquareEnv` is the study's 2.25 m square; `room_env(...)` wraps
`envs/kinsim_room.py` `KinSimEnv`. For a step in which the agent does not move the adapter calls `KinSimEnv.observe()` (added by the simulator's
author on 2026-11-18 at this loop's request; the first pair of episodes ran before it existed, through two private
fields, on a path those episodes never took).

## Request settings: Opus 5.5 against Fable 5.2

Both go through the same frozen tool loop (`harness/providers/anthropic_messages.py` `agent_step`), so the system
block, the nine tools, the two cache breakpoints, the retry rule (7 attempts), the turn cap (30) and the client
(non-streaming, 900 s timeout, SDK retries off, `anthropic` 1.11.0) are identical.

| Setting | Claude Opus 5.5 (frozen entry) | Claude Fable 5.2 (`providers_demo.json`) |
| --- | --- | --- |
| `model` | `claude-opus-5-5` | `claude-fable-5-2` |
| `max_tokens` | 64000 | 64000 |
| `output_config.effort` | `medium` (this model's default) | `medium` (one level **below** this model's default, `high`) |
| `thinking` | field omitted (adaptive, cannot be disabled) | field omitted (adaptive, always on) |
| Sampling, `tool_choice` | not sent | not sent |
| Price, US$ per million tokens: input / 5-minute cache write / cache read / output | 4 / 5 / 0.20 / 20 | 8 / 10 / 0.20 / 40 |

Differences, all of them: the model id; the price; and that `medium` sits at the default for Opus 5.5 and one level
under the default for Fable 5.2 (the same value was kept so the request is the same; a run at Fable's default would be
a different comparison). Neither request asks for the server-side refusal fallback the Claude API guide recommends
by default: a silent switch to another model would spoil a model comparison, so a refusal would have been a counted
harness fallback. None occurred (every turn's `model` field is the requested one). Fable 5.2 needs 30-day data
retention on the account; the requests were accepted. Fable prices are from the Claude API reference bundled with
Claude Code (cached 2026-11-03); the frozen loop books Opus prices, so the Fable driver books the difference per
turn and the spend cap counts real dollars (tested).

## Commands (tests, and the first pair)

```bash
# Mac: tests
cd course-project/beaconmind && PYTHONPATH=src python3 -m pytest -q tests/test_closed_loop.py tests/test_validator.py   # 51 passed
PYTHONPATH=src python3 -m pytest -q                                                                               # 422 passed, 9 skipped
python3 course-project/tools/prereg_freeze.py --verify --out course-project/evidence/M4/M4.T1/prereg.json          # OK

# Spark (after tools/sync_to_spark.sh); D=course-project/data/closed-loop/20261118-room
W="--env room --world course-project/configs/arenas/real-room-nominal.json --seeds 1"
bash course-project/tools/closed_loop_run.sh --driver claude-opus-5-5  $W --max-steps 3 --cap-usd 1.5 --out $D/smoke-claude-opus-5-5
bash course-project/tools/closed_loop_run.sh --driver claude-fable-5-2 $W --max-steps 3 --cap-usd 2.5 --out $D/smoke-claude-fable-5-2
bash course-project/tools/closed_loop_run.sh --driver b2               $W --cap-usd 0  --out $D/b2
bash course-project/tools/closed_loop_run.sh --driver claude-opus-5-5  $W --cap-usd 12 --out $D/claude-opus-5-5     # tmux bm-cl-opus
bash course-project/tools/closed_loop_run.sh --driver claude-fable-5-2 $W --cap-usd 22 --out $D/claude-fable-5-2    # tmux bm-cl-fable
```

The room configuration is `KinSimEnv.room`'s defaults as of this run (`envs/kinsim_room.py` SHA-256 prefix
`eefded236771`): the world file's own start pose (2.2, 2.6, 90°) in the room frame, the `camera` preset (visibility
from `configs/camera.json`), 2.0 m range limit, the study's odometry noise (not the `carpet` option). The seed (1)
selects the noise stream. The tag positions are the mounting sheet's **nominal** ones, not measurements.

## Final episodes (final room simulator, 2026-11-18 12:19 to 12:39 CST)

Configuration, set by the lead and identical for the three arms:

| Item | Value |
| --- | --- |
| Simulator | `envs/kinsim_room.py`, SHA-256 prefix `33a3c5d49239` (final; unchanged since commit `ea6263f`) |
| World | `configs/arenas/real-room-plus8-160mm-nominal.json` (layout C20: 20 tags, 160 mm, **nominal** positions), SHA-256 prefix `5fbd24da13ce` |
| Start pose | S1 of `configs/arenas/real-room-scenarios.json`: (2.50, 1.50, 90°) in the room frame |
| Sensing | `camera` preset (`beaconmind.camera_model`), range limit 3.0 m |
| Odometry | `study` preset; noise seed 3000 |
| Driving area | inset 0.4 m from every side |
| Design values | the frozen `configs/dv.json`, no sigma override |
| Prompt | `prompts/robot_system_prompt_v3.3-room.txt` (SHA-256 prefix `807e29927b2b`), see the deviation below |
| B2 | `kinsim_room.make_b2_policy()` through the same loop and tools |
| Spend caps | US$8 (Opus 5.5), US$14 (Fable 5.2); neither was reached |

**Documented deviation from the study prompt.** The frozen v3.3 prompt says "rejected if ... range_m > 2.0", which
contradicts a 3.0 m range limit. The frozen file is untouched; the room variant differs from it in that one number
and nothing else (`diff prompts/robot_system_prompt_v3.3.txt prompts/robot_system_prompt_v3.3-room.txt`):

```
33c33
< 3 Per detection: rejected if quality < 0.5, range_m > 2.0, or a non-null id outside 0-29. ...
---
> 3 Per detection: rejected if quality < 0.5, range_m > 3.0, or a non-null id outside 0-29. ...
```

The variant file carries no comment line of its own because every character of it is sent to the model; it was made
by Claude Fable 5.2 via Claude Code on 2026-11-18 by replacing that number. So these episodes are **not** runs of the
study's prompt, and their numbers are not comparable with the study's replay results on that account either.

```bash
# Spark; D=course-project/data/closed-loop/20261118-room-final
W="--env room --world course-project/configs/arenas/real-room-plus8-160mm-nominal.json --start 2.5,1.5,90 --preset camera \
   --max-range 3.0 --odometry study --drive-inset 0.4 --seeds 3000 --prompt course-project/prompts/robot_system_prompt_v3.3-room.txt"
bash course-project/tools/closed_loop_run.sh --driver b2               $W --cap-usd 0  --out $D/b2
bash course-project/tools/closed_loop_run.sh --driver claude-opus-5-5  $W --cap-usd 8  --out $D/claude-opus-5-5     # tmux bm-cl-opus
bash course-project/tools/closed_loop_run.sh --driver claude-fable-5-2 $W --cap-usd 14 --out $D/claude-fable-5-2    # tmux bm-cl-fable
```

| Measure | Opus 5.5 | Fable 5.2 | B2 (coded procedure) |
| --- | --- | --- | --- |
| Outcome | DONE (decision), not capped | DONE (decision), not capped | DONE (decision) |
| Steps | 56 | 56 | 58 |
| Moves executed | 55 | 55 | 57 |
| Moves by type | F_25 6, L_30 44, R_30 5 | F_25 6, L_30 44, R_30 5 | F_10 1, F_25 6, L_30 39, R_30 11 |
| Path length (odometry, m) | 1.51 | 1.51 | 1.60 |
| Validator rejections (refused move calls) | 0 | 0 | 0 |
| Emergency stops | 0 | 0 | 0 |
| Fallbacks / repaired reports | 0 / 0 | 0 / 0 | 0 / 0 |
| ATE (cm) | 2.3 | 2.3 | 2.3 |
| B0 (dead reckoning) ATE on the same odometry (cm) | 1.5 | 1.5 | 1.4 |
| Final position error (cm) | 2.0 | 2.0 | 1.7 |
| B0 final position error (cm) | 2.2 | 2.2 | 1.7 |
| Final heading error (deg) | 1.8 | 1.8 | 2.5 |
| Heading RMSE (deg) | 1.3 | 1.3 | 1.6 |
| Steps with a full fix / a position fix | 0 % / 37.5 % (21 of 56) | 0 % / 37.5 % (21 of 56) | 0 % / 41.4 % (24 of 58) |
| Tags mapped within 0.30 m / in the world | 14 / 20 | 14 / 20 | 14 / 20 |
| Tags ever detected | 14 | 14 | 14 |
| Map entries (confirmed, phantoms) | 14 (12, 0) | 14 (12, 0) | 14 (12, 0) |
| Map RMSE (cm) | 4.6 | 4.5 | 4.4 |
| Association precision / recall | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| Tool calls (per step) | 280 (5.0) | 286 (5.1) | 286 (4.9) |
| Estimation-tool F1 against the procedure (P / R) | 0.985 (0.971 / 1.000) | 0.973 (0.948 / 1.000) | 1.000 |
| Decision equals the procedure's on the arm's own input / memory equals | 1.000 / 0.982 | 1.000 / 0.982 | 1.000 / 1.000 |
| State violations: pose / map entries | 0 of 56 / 0 | 0 of 56 / 0 | 0 of 58 / 0 |
| Invalid tool calls | 2 | 0 | 0 |
| Model turns (per step) | 286 (5.1) | 248 (4.4) | none |
| Time per step: mean / median / 95th percentile / max (s) | 20.2 / 21.3 / 25.0 / 29.5 | 18.7 / 19.6 / 23.7 / 26.5 | 0.0 |
| Wall time of the episode (min) | 18.8 | 17.5 | 0.0 |
| Tokens: input (of which cached) / output | 3,164,131 (2,908,947) / 137,258 | 2,737,356 (2,483,218) / 132,409 | none |
| Cost (US$): episode / per step | 4.60 / 0.082 | 8.33 / 0.149 | 0 |

How to read it:

- **n = 1 per arm.** One world, one start, one noise seed, one sample of each model. Nothing here supports a
  statement that one model is better than the other, or than B2.
- **Opus 5.5 against Fable 5.2: the same episode.** Both made the identical 55 moves, so they received the identical
  56 observations (checked row for row) and wrote the same pose at 55 of 56 steps. What differs: Fable 5.2 made 6
  more tool calls (8 more `gate_detection`, 2 more `exploration_summary`, 2 fewer `update_beacon` and `fix_pose`),
  9 estimation calls the procedure does not make against Opus 5.5's 5; Opus 5.5 called `fix_pose` twice with an
  empty match list (a tool error it recovered from), Fable 5.2 never; Fable 5.2 used fewer turns (248 against 286)
  and 1.3 minutes less; it cost 1.81 times as much. Map RMSE 4.5 against 4.6 cm comes from map entries written
  1 cm apart. With one episode each, none of these is more than an observation.
- **Where the models left B2's path, and why it is not a driving decision.** Steps 0 to 34 are move for move
  B2's. At step 31 the procedure chooses a leg toward the −60° sector and reads its `max_leg_moves` from
  `exploration_summary`. B2 calls the tool with its unrounded pose (−0.4392, −0.2389) and gets 2 (wall estimate
  1.18 m). Opus 5.5 called it with the two-decimal pose of its report (−0.44, −0.24) and got 1 (wall estimate
  1.07 m): a rounding of 1 mm. Fable 5.2 called it with (−0.46, −0.23), the odometry prior of that step (the
  step-30 position, which its `fix_pose` call had just corrected to (−0.439, −0.239)), and also got 1 (1.08 m):
  not a rounding but the wrong pose, 2 cm away, although its report then carried the fixed pose. Both wrote
  `leg_moves_left` 1 where the procedure writes 2. Their leg therefore ended one move earlier;
  at step 35 B2 took the leg's second forward move (FORWARD_10) and the models chose the next leg (the 90° sector),
  which is exactly what the coded procedure decides from the models' own state. From then on the trajectories
  differ: the models finished two steps earlier, with the same 14 tags. The prompt gives poses to two decimals and
  tool results come back with three, so a threshold inside a tool can flip on a millimetre (Opus 5.5's case); the
  study's replay could not show this, because there the moves were the log's.
- **Agreement with the coded procedure, not a difference in driving.** The agreement figure is computed per step
  by running the frozen coded procedure (`kinsim_lite.estimate_step` and `decide_step`) on the observation the
  model received and the model's own previous report, and comparing its decision with the report's `decision`; it
  is 112 of 112. It takes the model's state as given: the memory that differs from B2's since step 31
  (`leg_moves_left`) is part of that state, so the figure says the models followed the procedure from where they
  were, not that they stayed on B2's path (they did not, from step 35). The procedure's memory equals the
  model's at 55 of 56 steps; the one difference is step 31. This episode is evidence that both models execute the written procedure
  in a closed loop (validated, executed moves; no fallback), not evidence about how either would drive where the
  procedure is silent.
- **No full fix in any arm; a position fix on 37.5 % to 41.4 % of steps.** Two confirmed tags were seldom in one
  picture, and when they were the full fix was not well conditioned (the models say so in their notes).
- **Dead reckoning (B0) is again at least as good as every arm on ATE** (1.4 to 1.5 cm against 2.3 cm): 1.5 m of
  travel with the study's small odometry noise and no drift, so there is little for a position fix to correct.
- **14 of 20 tags are mapped by every arm.** The procedure ends by rule E1 after two scans without a new beacon.
- **The validator never had to refuse**: all 110 model `move` calls were allowed by the flags the model had been
  given, accepted by both checks and executed. `seed_3000.moves.jsonl` lists each commanded move and its result.
- Time per step doubled against the first pair (20 s against 10 s) because most steps of this episode had
  detections to associate (5 turns a step against 4).

## First pair, superseded (draft room simulator, 02:37 to 02:47 CST)

Kept as the first run. It is superseded because it ran on a draft of the room simulator (`envs/kinsim_room.py`
SHA-256 prefix `eefded236771`, never committed) with the 12-tag world, the 2.0 m limit and the frozen v3.3 prompt;
the final simulator's camera model sees tags that draft did not. Its numbers must not be quoted as the rehearsal.

### Smoke tests (3 steps each, room, draft simulator)

| | Opus 5.5 | Fable 5.2 |
| --- | --- | --- |
| Steps, all reports valid | 3, yes | 3, yes |
| Moves executed | TURN_LEFT_30 × 3 (the first scan) | TURN_LEFT_30 × 3 |
| Tool calls; estimation-tool F1 | 8; 1.0 | 8; 1.0 |
| Mean time per step | 8.1 s | 6.4 s |
| Cost | US$0.13 | US$0.24 |

### Full episodes of the first pair (12-tag room, noise seed 1; one episode per arm)

| Measure | Opus 5.5 | Fable 5.2 | B2 (coded procedure) |
| --- | --- | --- | --- |
| Episode end | DONE (decision) | DONE (decision) | DONE (decision) |
| Steps | 46 | 46 | 46 |
| Moves executed | 45 | 45 | 45 |
| Moves by type | F_25 5, L_30 37, R_30 3 | F_25 5, L_30 37, R_30 3 | F_25 5, L_30 37, R_30 3 |
| Path length (odometry, m) | 1.24 | 1.24 | 1.24 |
| Refused move calls | 0 | 0 | 0 |
| Fallbacks / repaired reports | 0 / 0 | 0 / 0 | 0 / 0 |
| ATE (cm) | 2.0 | 2.0 | 1.6 |
| B0 (dead reckoning) ATE on the same odometry (cm) | 0.7 | 0.7 | 0.7 |
| Final position error (cm) | 3.4 | 3.4 | 2.4 |
| B0 final position error (cm) | 1.3 | 1.3 | 1.3 |
| Final heading error (deg) | 0.4 | 0.4 | 0.4 |
| Heading RMSE (deg) | 0.5 | 0.5 | 0.5 |
| Tags found within 0.30 m / in the world | 3 / 12 | 3 / 12 | 3 / 12 |
| Tags ever detected | 3 | 3 | 3 |
| Map entries (confirmed, phantoms) | 3 (3, 0) | 3 (3, 0) | 3 (3, 0) |
| Map RMSE (cm) | 1.8 | 1.8 | 1.8 |
| Map precision / recall | 1.00 / 0.25 | 1.00 / 0.25 | 1.00 / 0.25 |
| Association precision / recall | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| Tool calls (per step) | 155 (3.4) | 159 (3.5) | 155 (3.4) |
| Estimation-tool F1 against the procedure (P / R) | 1.000 (1.000 / 1.000) | 0.977 (0.955 / 1.000) | 1.000 |
| Decision equals the procedure's / memory equals the procedure's | 1.000 / 0.978 | 1.000 / 0.978 | 1.000 / 1.000 |
| State violations: pose / map entries | 0 of 46 / 0 | 0 of 46 / 0 | 0 of 46 / 0 |
| Model turns | 193 | 172 | none |
| Time per step: mean / median / max (s) | 11.0 / 10.1 / 20.8 | 9.5 / 9.2 / 15.4 | 0.0 |
| Episode time (min) | 8.4 | 7.3 | 0.0 |
| Tokens: input (of which cached) / output | 1,857,322 (1,731,818) / 51,996 | 1,645,207 (1,520,674) / 49,654 | none |
| Cost (US$): episode / per step | 2.01 / 0.044 | 3.53 / 0.077 | 0 |

How to read it:

- **n = 1 per model.** One world, one start, one noise seed, one sample of each model. Nothing here supports a
  statement that one model is better. What it shows is that both ran the whole closed loop without a single invalid
  report, refused move or harness intervention, and that both followed the procedure to the same 45 moves.
- **Same moves, so same observations: this comparison shows agreement with the coded procedure, not a difference
  in driving.** Because every decision equalled B2's, all three arms saw the identical 46 observations (checked: the
  raw records and the true poses are equal row for row). The episode is a closed loop in mechanism, but it did not
  branch, so it says nothing about which model would drive better where the procedure leaves a choice or where a
  model departs from it.
- **The 0.4 cm ATE difference from B2 is a rounding artefact, the same for both models.** At step 33 the
  `compose_odometry` tool returned y = −1.245 (tools round to 3 decimals); both models rounded that to −1.25 in the
  report, while the coded procedure rounds its unrounded value (−1.2447…) to −1.24. The 1 cm stays in the pose for
  the last 13 steps (no fix after it) and in one `scan_points` entry, which is the "memory 0.978". It is inside the
  state-violation tolerance (1.1 cm), so it counts as no violation.
- **Dead reckoning (B0) beats every arm here** (0.7 cm against 1.6 to 2.0 cm). The episode is short (1.24 m of
  travel, 40 turns) with the study's small odometry noise and no drift, and only two steps had a fix at all
  (`position_fix`) and none a full fix: no step of this episode had two confirmed tags in one picture. The room
  rehearsal finds a full fix (`beacon_fix`) on under 1 % of B2's steps with this camera and the 12-tag layout
  (`evidence/M3/M3.T12/fix-conditioning.txt`). The study's drift condition is where the fixes paid off. This is a
  finding about the room scenario, not about the models.
- **Only 3 of 12 tags are mapped by every arm** (5 by B2 on the later simulator version). The procedure ends by
  rule E1 after two scans without a new beacon; from this start, with a 2.0 m range limit and a 46.9° field of
  view, that is what it reaches. For the rehearsal of the real run this is the main message: the layout, the range
  limit or the start pose need attention before a real EXPLORE episode will map the room (see
  `evidence/M3/M3.T10/layout/coverage.txt` and the room rehearsal, `evidence/M3/M3.T12/`).
- **Fable 5.2's one departure**: at step 43 (no detections) it called `fix_pose` with an empty match list; the tool
  answered with an error and the model went on correctly (`invalid_tool_call` × 1; its other three extra calls were a
  second `exploration_summary` and two extra `gate_detection` calls). Opus 5.5 made exactly the procedure's calls.
- **Fable 5.2 used fewer turns** (172 against 193) because it more often put several tool calls in one turn; at
  twice the token price it still cost 1.76 times as much.
- Cost per step (US$0.044 for Opus 5.5) is below the study's US$0.073 because most steps of this episode had no
  detection.

## The validator acting

**In no real episode did the validator have to refuse.** In the first pair every one of the 90 model `move` calls was allowed
by the safety flags the model had been given, was accepted by the dispatcher and by the second check, and was
executed. At step 44, where `forward_allowed` was empty, both models turned. One executed step as logged
(Opus 5.5, step 14):

```json
{"step": 14, "decision": "TURN_RIGHT_30",
 "move_calls": [{"action": "TURN_RIGHT_30", "tool_result": "done", "tool_reason": null,
                 "validator_ok": true, "validator_reason": null, "agree": true}],
 "executed_move": {"action": "TURN_RIGHT_30", "result": "done", "reason": null,
                   "odometry": {"forward_m": 0.0, "left_m": 0.0, "dtheta_deg": -29.9},
                   "command": {"schema": "bm.move/1", "cmd_seq": 14, "obs_id": "s1-014", "action": "TURN_RIGHT_30",
                               "distance_m": 0.0, "angle_deg": -30.0, "v_max_mps": 0.15, "w_max_dps": 45.0, "timeout_s": 5.0}},
 "next_last_move": {"action": "TURN_RIGHT_30", "result": "done"}, "violations": [],
 "validator": {"latched": false, "latch_reason": null, "consecutive_contacts": 0}, "episode_end": null}
```

and the next observation the model received (step 15) carries that move and its measured odometry:
`"odometry": {"forward_m": 0.0, "left_m": 0.0, "dtheta_deg": -29.9, "quality": "ok"}, "last_move": {"action":
"TURN_RIGHT_30", "result": "done"}`.

**The refusal paths are shown by a scripted model, not by a real one** (`scripted_validator_trace.json`: the test
suite's fake client, no network, study square seed 1010, through the real provider tool loop). Excerpt:

- Step 4, at the wall (`forward_allowed: []`): `move(FORWARD_25)` → `{"result": "refused", "reason": "not in
  forward_allowed"}` (violation `guardrail`); the scripted model then calls `move(TURN_LEFT_30)` in the same step →
  `done`, executed; the true pose stays at x = 0.85 m and turns to 30°.
- Step 5: the only call is `move(BACKWARD_10)` → refused, `backward not allowed` (the last move was a turn). Nothing
  is executed; the next observation shows `last_move: {"action": "BACKWARD_10", "result": "refused"}` and zero
  odometry.
- Step 6: `emergency_stop` and then `move(TURN_LEFT_30)` → refused, `latched`; the episode ends with `ended_by:
  latch`, `detail: "emergency_stop: scripted test"`, and the latch file is written.

Other paths covered only by tests: a move decision without a `move` call (`not_called`), a report decision that
differs from the accepted move, an invalid report after an accepted move, two contacts (auto-latch), the executor's
own refusal, the spend cap before and inside a step, a provider failure, a torn last line, a resume the simulator
does not reproduce.

## Review for the real car: ways around the validator, ways past a latch (2026-11-18, second pass)

A later batch runner will drive the real car through this loop unattended, so the loop was read again with two
questions. Each gap found was closed and has a test (`tests/test_closed_loop.py`, `tests/test_validator.py`).

**Can a move execute without passing `check_move`?** A new move reaches `env.step(action)` in one place only, after
(a) the dispatcher accepted it, (b) `check_move` accepted it against the same observation, (c) the provider's
`state["moved"]` equals the accepted call (otherwise the step raises), and (d) no latch is set at that moment.

| # | Way found | Was | Now |
| --- | --- | --- | --- |
| 1 | **Resume**: a rerun sent every logged move to the environment again without any check (right for a simulator, a second drive for a real car) | open | Only an environment with `deterministic_replay = True` is resumed; anything else raises before `reset` is followed by any move |
| 2 | A flag that is missing or of the wrong type read as permission (`steps_left` absent → allowed; `"false"` → true; a string `forward_allowed` matched by substring) | open | Fail closed: missing or non-boolean flags refuse; a missing `counters` or `safety` block raises before execution |
| 3 | The executor reports a different move from the one commanded, or none | accepted silently | The step raises; the write-ahead file shows the commanded move |
| 4 | A crash between the executor call and the log line left no trace of a move that ran | open | `seed_<n>.moves.jsonl`: `commanded` before, `result` after |
| 5 | `status: error`: the frozen dispatcher answers `done` | already refused by the second check | Tested end to end with an environment that reports errors |
| 6 | Several accepted calls, or a call list that disagrees with the provider's state | already raised or refused | Tested by the fuzz test |

Fuzz test: a scripted model makes random sequences of valid, invalid and repeated `move` calls and emergency stops
over 12 episodes; every action the environment received was one `check_move` allows for that step's observation,
at most one per step, none after a latch, and the car never left the arena.

**Can the loop continue after a latch?**

| # | Way found | Was | Now |
| --- | --- | --- | --- |
| 1 | A latch file written by someone else during the episode (the out-of-band STOP, an operator) was read only at the start | open | Read before every observation and again just before execution; `--watch-latch` adds the project-wide file |
| 2 | `move` accepted, then `emergency_stop` in the same step: the move still ran | open (by design: "the model was told done") | Not executed: nothing runs once a latch is set |
| 3 | The runner went on to the next seed after a latched episode | open | The batch stops (exit code 3); a latch file present at the start refuses every episode |
| 4 | Error observations and a Pico reboot did not latch (C5.2) | not implemented | 2 consecutive errors or null odometry after step 0 latch; the observation then says `latched: true` and every move is refused by both checks |
| 5 | An unreadable latch file (an operator's `touch`) counted as no latch | open | Any existing file is a latch |
| 6 | A latched episode rerun | already refused (the end row, or the latch file) | unchanged |

Left for the real-car backend, outside this loop: the latch must also disarm the car (the loop only stops sending
moves); two runner processes on different output folders could command one car (the lock is per folder); and the
executor must itself enforce the caps of C2 (the simulators' own wall check is the stand-in here).

## Where the logs are

Git-ignored, under `course-project/data/closed-loop/` on the Spark, with a copy on the Mac:

| Folder | Content | Size |
| --- | --- | --- |
| `20261118-room-final/claude-opus-5-5/` | `seed_3000.jsonl` (56 step rows, 1.3 MB), `seed_3000.runlog.jsonl` (C9.2, 1.1 MB), `seed_3000.moves.jsonl`, `seed_3000.summary.json`, `seed_3000.world.json`, `run.json`, `spend.jsonl` | 2.3 MB |
| `20261118-room-final/claude-fable-5-2/` | the same | 2.3 MB |
| `20261118-room-final/b2/` | the same, no spend | 2.0 MB |
| `20261118-room/` (first pair, superseded) | `claude-opus-5-5/`, `claude-fable-5-2/`, `b2/` (seed 1), two 3-step smoke folders | 2.9 MB |

Copied here: `runs-final/<arm>/` and, for the first pair, `runs/<arm>/`, each with `run.json` (configuration tag,
file hashes, request settings), the episode summary, `run.end-*.json` and the terminal log. Also here:
`scripted_validator_trace.json`, `pytest_mac.txt`, `prereg_verify.txt`. The final runs' `run.json` shows git commit
`898f3d0` with uncommitted files: the Spark clone had not been pulled, and the code was copied over it with
`tools/sync_to_spark.sh`; the file hashes in `run.json` identify what ran (`harness/closed_loop.py` `e3764ab6480d`,
`harness/validator.py` `f713f548012e`, `envs/kinsim_room.py` `33a3c5d49239`).

**Spend:** first pair US$5.91 (smoke 0.13 + 0.24, episodes 2.01 + 3.53); final episodes US$4.60 + US$8.33 =
US$12.93; **total US$18.84**. The plan's project ledger (`data/budget/ledger.jsonl`, C13) does not exist on the
Spark, so, like `replay_run.py`, the runner recorded spend in each run folder's `spend.jsonl`; it appends a C13 line
per paid episode only if that ledger exists.

## What went wrong or is not as clean as it should be

- **The room simulator changed after these episodes, so they rehearse an earlier draft of it.** The runs used
  `envs/kinsim_room.py` with SHA-256 prefix `eefded236771` (in each `run.json`); its author was still working on
  it, and the file at 02:51 CST (`5cf06de07ffb`) sees tags the earlier one did not (first difference: step 5, tag
  id 3 at 1.8 m). With the later file B2 on the same world and seed runs **56 steps and maps 5 of 12 tags** (ATE
  2.1 cm) instead of 46 steps and 3 tags. The earlier file was never committed, so the three episodes cannot be
  reproduced bit for bit; their logs hold every observation. The comparison between the arms stands (all three ran
  on the same simulator version, and B2's log from that version is beside the models'), but "3 of 12 tags" is a
  figure of the draft simulator. Rerunning the pair on the final simulator would cost about US$6 to US$8 and was
  not done: the approved spend was one episode per model.
- **Two lines of `harness/closed_loop.py` changed after the runs** (hash `f5a28b21c15d` in `run.json`): on a
  **resume**, the idle counter now uses the live loop's rule (an executor-refused move counts as no motion), and an
  unused import was removed. Neither is on the path the runs took (no resume, no refusal); the B2 parity tests on
  the study square and in the room pass with the final code. Because the configuration tag hashes these files, the
  run folders cannot be resumed (they are complete).
- **Neither pair exercised the validator's refusals**, and the only branch (final episodes, step 35) came from a
  rounding, so both are weak tests of "the model chooses": the models chose what the procedure chooses. A scenario that makes the loop branch
  (drift, a start near a wall, the `carpet` odometry, 2.5 m range) was not run: the approved spend was for one
  episode per model.
- **Thinking text is not in the logs.** The frozen request omits `thinking.display`, whose default returns empty
  thinking blocks, so the traces hold tool calls, results, the report and its one-sentence `note`, not the reasoning.
- **The contracts' schemas and the frozen code disagreed in three places; fixed on 2026-11-18 by the lead's
  decision.** `bm.observation-1` did not allow `last_move: null` (sent at step 0), and `bm.report-1` allowed neither
  `note: null` nor a null `beacon` in a rejected association, both of which the coded procedure writes, so
  `bm.step-1` rejected such a PREVIOUS_REPORT. Both schemas are widened additively (a null beacon only with result
  `rejected`). Checked on the study's data: of 2,597 coded-procedure steps (40 observation logs) every observation,
  report and step message now validates (before: 2,557, 0 and 0); of 1,050 sampled model reports 1,041 validate
  (before 959; the other 9 are real model errors such as a missing `beacon` key); nothing that validated before
  fails now. Tests: `tests/test_schemas_widened.py`.
- **C9.2 fields the simulator cannot fill** are zeros in the export (`boot_id`, encoder ticks, `duration_s`).
- **Not implemented:** missions other than EXPLORE and operator requests (the loop always sends `mission: EXPLORE`,
  `operator_request: null`); the slip auto-latch; the out-of-band STOP hotkey itself (work list 2.7; the loop obeys
  the latch file it would write); drivers other
  than B2 and Anthropic models (the OpenAI-compatible provider would need the same thin driver).
- **Which B2 ran.** First pair: the frozen procedure (`kinsim_lite.estimate_step` + `decide_step`) through the loop.
  Final episodes: `kinsim_room.make_b2_policy()` through the loop (`run.json`: `"policy":
  "kinsim_room.make_b2_policy()"`), which is the same frozen procedure plus a rule for the dead end the written
  procedure leaves open. That rule did not fire in this episode: rerunning the frozen procedure on each of B2's 58
  logged steps raises nowhere and reproduces all 58 reports, and it raises on none of the models' 112 steps either.
  So the B2 column is the procedure as written. Had a branch the procedure does not implement been reached, the
  B2 driver would have ended the episode (`error`, "driver stopped"), not driven on.
