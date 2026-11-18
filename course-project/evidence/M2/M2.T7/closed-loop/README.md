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

**Result in one paragraph.** One EXPLORE episode each of Claude Opus 5.5 and Claude Fable 5.2 in the simulated real
room (nominal tag layout, start (2.2, 2.6, 90°), measured-camera visibility, 2.0 m range, noise seed 1), and the coded
procedure B2 on the same world. **Both models made exactly the 45 moves B2 made, in the same order, and ended with
DONE at step 45**; no move was refused, no report was invalid. All three mapped 3 of the 12 tags in the simulator version these
runs used (a later version of the room simulator sees more: B2 then maps 5; see "What went wrong"). Cost US$2.01 (Opus 5.5)
and US$3.53 (Fable 5.2); about 10 s a step for both. **n = 1 episode per model: no difference between the models is
statistically established.**

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

## Commands

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

## Smoke tests (3 steps each, room)

| | Opus 5.5 | Fable 5.2 |
| --- | --- | --- |
| Steps, all reports valid | 3, yes | 3, yes |
| Moves executed | TURN_LEFT_30 × 3 (the first scan) | TURN_LEFT_30 × 3 |
| Tool calls; estimation-tool F1 | 8; 1.0 | 8; 1.0 |
| Mean time per step | 8.1 s | 6.4 s |
| Cost | US$0.13 | US$0.24 |

## Full episodes (room, noise seed 1; one episode per arm)

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

**In the two full episodes the validator never had to refuse**: every one of the 90 model `move` calls was allowed
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

Git-ignored, `course-project/data/closed-loop/20261118-room/` on the Spark, with a copy on the Mac (2.9 MB in all):

| Folder | Content | Size |
| --- | --- | --- |
| `claude-opus-5-5/` | `seed_1.jsonl` (46 step rows, 584 kB), `seed_1.runlog.jsonl` (C9.2, 454 kB), `seed_1.summary.json`, `seed_1.world.json`, `run.json`, `spend.jsonl` | 1.0 MB |
| `claude-fable-5-2/` | the same | 1.0 MB |
| `b2/` | the same, no spend | 764 kB |
| `smoke-claude-opus-5-5/`, `smoke-claude-fable-5-2/` | 3-step runs | 76 kB each |

Copied here (`runs/<arm>/`): `run.json` (configuration tag, file hashes, request settings), `seed_1.summary.json`,
`run.end-*.json`, and the terminal log of the three full runs. Also here: `scripted_validator_trace.json`,
`pytest_mac.txt`, `prereg_verify.txt`.

**Spend:** smoke US$0.13 + US$0.24, full episodes US$2.01 + US$3.53, **total US$5.91** of the approved US$40. The
plan's project ledger (`data/budget/ledger.jsonl`, C13) does not exist on the Spark, so, like `replay_run.py`, the
runner recorded spend in each run folder's `spend.jsonl`; it appends a C13 line per paid episode only if that ledger
exists.

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
- **The episode did not exercise the validator's refusals or any branching**, so it is a weak test of "the model
  chooses": the models chose what the procedure chooses, on an easy episode. A scenario that makes the loop branch
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
- B2 in the loop turns its unimplemented branches (`NotImplementedError`) into a counted fallback step; it does not
  use `kinsim_room.make_b2_policy`'s dead-end branch.
