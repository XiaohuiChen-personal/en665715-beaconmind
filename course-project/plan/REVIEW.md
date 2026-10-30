# BeaconMind plan — review log

Owner: **Xiaohui Chen** (sole participant). Plan written 2026-10-05; reviewed 2026-10-06. Nothing
here is committed (README L10).

This log has three parts:

- **Part A** lists each milestone's own adversarial review: what the reviewer found and how it was fixed.
- **Part B** is the cross-plan consistency review. It checked the six milestone files against each other
  and against `README.md`, and records what it found and changed.
- **Part C** lists what is still open and needs Xiaohui.

Severity: **high** means a lower-end executor would fail or do the wrong thing. **med** means it would
probably stall or guess. **low** means a wording or robustness problem.

---

## Part A — Per-milestone reviews (2026-10-06)

### M1 — Foundations and open decisions (`M1-foundations.md`, 14 tasks)

| Sev | Finding | Fix applied |
| --- | --- | --- |
| high | Many steps needed a keyboard or an attached terminal: "press Enter" scripts, foreground `ros2 launch`/`tf2_echo`/miniterm, `docker run -it` over BatchMode ssh, an attached tmux, and terminal beeps Xiaohui could not hear | §0.3 now defines four patterns: background-in-container, detached-on-host, one command per physical action, and per-machine evidence paths. The recorder takes one placement per call (`--placement`). `encoder_handturn.py` has `zero`/`read`/`summarize` subcommands. New `tools/serial_read.py`. The agent runs with `docker run -d --rm`. `run_latency.sh` runs in detached tmux. Calibration uses the flash-LED cue. Every foreground ROS read has a `timeout` |
| high | T2 schema `$id`s were relative, so the `$ref` from bm.step-1 to the observation schema would not resolve | Every `$id` is absolute (`https://schemas.beaconmind.invalid/…`), with a local registry and no network fetch |
| high | T2 `test_example1_numbers` could not be written from the vendored files, and Example 3 said "inspect the structure" | The step now gives the exact MAP constants, the call sequence and the rounding. Both recipes were checked against `l2_geometry.py` and reproduce `fewshot-numbers.json` |
| high | `test_dv_units_match_suffix` contradicted the `_per_m` keys, `pack_min_v` had no unit, and `gate_widen_range_per_m → 1/m` was wrong | Added an ordered first-match unit rule (`_per_m`, `_per_turn_deg`, `_mps`, `_dps`, `_ms`, `_m`, `_deg`, `_s`, `_v`); the test re-implements it |
| high | T9 hand-turn count: the counter has no direction, the car stayed on the floor, and the parser did not know the `PINTEST` banner | Added a one-direction counting rule, a wheels-free set-up and tape pointer, banner-skipping parsing with the exact reply strings, and parser and summary tests |
| high | T5 piped the Isaac kit through `tee \| grep \| head`, so SIGPIPE could kill it; it also used relative log paths and `…` placeholders | Output now goes to a log file that is filtered afterwards. Exit codes are interpreted (0, or 124 after DONE). Paths are absolute, and Run 2 has an exact export block |
| high | The T12 fault check expected `down` after about 2 s, but 10 errors × 2 s timeout is about 20 s, and the ESP32 resets its sequence on reboot | Changed to a 40 s unplug with a status logger: stale ≤ 3 s, down ≤ 30 s, ok again ≤ 30 s. The bridge accepts a sequence reset |
| med | MoveCommand said 10 fields (it has 9); the providers schema had no required or optional fields | Listed the 9 fields. Defined `{schema, models}` with required and optional fields per entry |
| med | Evidence files had no commands that wrote them; the Spark evidence directory was never created; the Mac's egg-info could be synced over the Spark's | Added `mkdir`/`tee` commands. `sync_to_spark.sh` excludes `*.egg-info` and `.pytest_cache`. `test_no_folder_named_log` prunes `data/` and `ros2_ws/` |
| med | T3 "one graph" had no ordering; a placeholder image name; a generic compose project name; a missing `video/` directory; an unverified `cv2.aruco` claim | Fixed the start order. Named the canvas output. Added `name: beaconmind` and `mkdir -p video`. The aruco claim is now a verification step |
| med | T4 probe metric parsing, `n_all_pass` and `n_errors` were unspecified; the effect of OD8's sequential client on episodes was unstated | Parsing now uses `awk '{print $NF}'`, and the fields are named. `od8-decision.md` must state "one request at a time" |
| med | T5 did not say how the AprilTag MDL and its texture are referenced; the offline self-test had no expected output | Default is the asset-server MDL, with local copies as fallback. Self-test intrinsics and the expected 0.693 m ± 2 % are given |
| med | T6 pinned arduino-cli from the "latest" URL, passed a by-id symlink to `--device`, did not verify PSRAM or Pillow, and gave no LED eye-safety note | The version is pinned via `arduino-cli version`, the link is resolved with `readlink -f`, and checks for PSRAM and Pillow were added along with the LED note |
| med | T7 distance used `‖t‖` (a corner, not the board centre); the yaw target sat on the chassis centre line; paper size was unspecified; the camera IP could change | Uses the board-centre depth. The target is on the lens line. Landscape Letter, with an A4 option. Added a DHCP fallback that reads the IP over serial |
| med | T8 did not say which way the size factor goes; placements could fall inside the car | Explicit formula and restart. Added a minimum-distance guard |
| med | T9 roll-out measured both wheels in one push; the overhang ignored the planned right-angle plug; the hash check and flashes were not captured | Each wheel gets its own floor marks. The overhang is flagged for re-measurement in M3.T1. A separate `sha256sum` check runs before flashing, and the flash output is tee'd |
| low | T11: compose might not recreate the container; the ledger path was relative; a bad ledger line could be skipped | Uses `--force-recreate ros` with absolute paths. Added `test_ledger_bad_line_raises` |
| low | T14 stale-line grep phrases did not match `CONTEXT.md`; it appended to the "slide may claim" list; I7 wrote to `/tmp` | Uses the real phrases. The slide list is marked as history. I7 writes a unique file under `data/latency` |
| low | T10 grep assumed OD ids in headings; OD14 was missing | Each item is headed with its OD id; OD14 was added |
| low | `\|` escapes could be copied literally; the T2 hash check had no expected values | Added the copy note and recorded the 2026-10-06 hashes |

### M2 — Minimum viable simulated result (`M2-sim-mvp.md`, 20 tasks)

| Sev | Finding | Fix applied |
| --- | --- | --- |
| high | The parity fixture globbed `r2/v7-*.jsonl`, but the S1–S4 files are byte-identical splits of `v7-think.jsonl`, so every case would run twice | Reads only `v7-think.jsonl` and `v7-nothink.jsonl` and expects `40 records read, 14 with calls, 117 calls` |
| high | M2 read flat car/noise keys that M1 never writes, so a `KeyError` was certain | M2.T3 now has config **views** (`load_car`, `load_detector_noise`, `load_odometry_noise`, `load_camera`) with mapping tables, defaults recorded as `assumptions`, σ/p helpers, and `tests/test_config_views.py` |
| high | M2.T7 rewrote `harness/budget.py` and `tests/test_budget.py`, which M1.T11 owns | M2.T7 verifies first and only appends `entry_cost_usd` and `RunBudget`. Its tests are in `tests/test_budget_run.py` |
| high | It dropped README's M1.T11 dependency on its own authority | Turned into a waiver Xiaohui approves once (now README **OD18**) |
| high | A model saying DONE ended the replay early, so arms would be scored on different steps | Replay runs to the end of the log; DONE/STOPPED/ASK/REFUSED are logged only. Added a test |
| high | M2.T18 put live frontier calls inside pytest (README L4 forbids this), and the cost estimate was wrong | Replaced with `tools/frontier_smoke.py`, a worst-case estimate, and approval up to $2.50 |
| high | The Spark has no `assignments/` checkout, so the parity tests would fail there | Vendored the reference into `tests/reference_v33/` with `SOURCES.sha256`, plus a copy-unchanged test |
| med | The prompt MD5 was truncated and its ending was wrong | Full digest `3b78a2301cf261379a51e6871574f0fa` |
| med | D5 says every tool returns `status`, but parity omits it | Made it a stop-and-ask (now README **OD16**) |
| med | `sim_extra` would break the `bm.detector_noise/1` schema; the p_detect fit was vague | New `configs/sim_extra.json` (`bm.sim_extra/1`), with an exact fit and a ±20 % post-injection check |
| med | The URDF camera pose came from the wrong file; prerequisites and the pull-back were missing | Reads `camera.json` `extrinsics` through the view. Added the prerequisites and the pull-back |
| med | `pgrep`/`pkill -f` over ssh matched their own shell | Bracket patterns (`[k]it/kit`) |
| med | Isaac camera images over UDP-only DDS were never proven | Added an M2.T16 branch with three options and a stop-and-ask |
| med | `test_bump_into_wall` was impossible; the integration moves could reach a wall | Wall at 0.20 m. The sequence is balanced, with a check that `axle_to_front_m < 0.25` |
| med | Smoke steps lacked exact commands or a working directory; container context was missing | Exact commands, `ls -td` lookups, a container-shell convention and a global `mkdir -p` rule |
| med | The world-checker test required exactly one code | Asserts membership; the clean fixture must return `[]` |
| med | The S1 smoke-report test depended on an unknown run | Pinned to S1 run 5 (all_pass, 8 calls) |
| low | Replay `last_move` off-by-one; the 0.005 m tolerance boundary; kinsim visibility threshold; kinsim arm state; host scripts without the package; no pull-back of Spark-generated tracked files; miscellaneous | Clarified each one; added an epsilon and a boundary test; threshold set to ≥ 6/12 with diagnostics; `reset/disarm/estop`; `sys.path` insert; tar pull-backs; disclosure paragraph |

### M3 — Real car (`M3-real-car.md`, 20 tasks)

| Sev | Finding | Fix applied |
| --- | --- | --- |
| high | Wire-codec collision with M2.T5 (`pico_wire.py` and the test file name) | New §0.4a ownership table. M3 extends `envs/pico_wire.py` additively. Its tests are in `tests/test_pico_wire_real.py` |
| high | A second latch module and a duplicate `bm-clear-latch` | M3.T13 reuses M2.T1's `validator.Latch` and CLI and keeps only the hotkey node |
| high | Twin and car mapped estop differently | Three options, and Xiaohui picks one for both (now README **OD15**) |
| high | The UMBmark `straight2m` pattern drives through the arena wall | Replaced with `straight1m`, plus a clearance check |
| high | A restarted client could start below the Pico's `last_cmd_seq` (BAD_SEQ), with no heartbeat warm-up | `first_seq()` = `last_cmd_seq + 1` from `/pico/state`, ≥ 3 heartbeats before arm/send, and a `bm-pico move` subcommand |
| high | The odometry calibration could be silently ignored (one nominal key against per-wheel keys) | Key mapping, cross-check with M1.T9, and `real_wheel_m()` with tests |
| high | The overhead-webcam spec (≥ 90° diagonal) was too narrow, and the camera would be bought before the coverage check | Computes the minimum H/V FOV from the mount height first (≈ 60° each), requires fixed focus, and adds a rational-model branch |
| high | Real runs used vague CLIs; no `--env real` existed | Exact commands; adds `--env real` and `--source real` with a parser test |
| med | Untracked per-start worlds; relative paths; system `python3` | Tracked `configs/arenas/real-a-<n>.json`, venv commands, and `qc_log` reuse |
| med | The micro-ROS toolchain omitted known bare-metal flags | Listed as build facts with a "compare the first error" rule |
| med | Reboot loop could block longer than the watchdog; self-reboots with the battery on were not explained | 100 ms ping, ≤ 200 ms block, `watchdog_update()`, and a safety note (S5 pull-down) |
| med | Free-text wire vectors | Exact two-kind grammar with 12 vectors |
| med | Test counts were wrong; `main.c` did not print the events the smoke test expects; contact-trial latch behaviour and the CSV split were unclear; static-obs run command was missing | Each corrected |
| low | Non-integer tag cell size; ambiguous Wi-Fi sample wording; fork-after-rclpy; back-EMF and wobble | Each fixed (1 px per cell then scaling; "arrived"; `spawn`; pitfall added) |

### M4 — Full benchmark (`M4-benchmark.md`, 16 tasks)

| Sev | Finding | Fix applied |
| --- | --- | --- |
| high | First-match grep status checks could read the wrong table row | Introduced `tools/task_status.py` (now plan-wide: README **L12**) |
| high | M2.T13–T20, M3.T17 and M3.T19 dependencies were missing | Added to the entry criteria, the task list and the prerequisites |
| high | Interface names guessed differently from M2's module map | I1–I12 rewritten from M2's table; I13 (Isaac launch) added |
| high | log_id and world_id spellings contradicted M2 | Corrected (`-B2-i1`/`-k1`, `sim-hid-`, `sim-uni-`), with `tests/test_obslog_plan.py` |
| high | Pilot budget broke the $100 cap ($5 + $15 + $85) | T = min($80, $100 − P), per model = min($20, T ÷ n), and a stop if T < $10 |
| high | Power analysis used α/2 instead of the Holm first step α/3 | α = 0.05/3 |
| high | Closed-loop compute estimate was wrong | Shown arithmetic: ≈ 240 decision-hours per model, about 60–80 h at concurrency 4 |
| med | Arm-R decision came after the freeze; RandomExplorer seed was not tied to the repeat | Moved before the freeze; `rng_key` includes the episode; repeat-noise check (arm R is now README **OD20**) |
| med | Frontier gate "3/4" contradicted its thresholds; undefined CLI options; roster keys did not match C11 | Full CLI, a 4/4 rule, placeholder keys taken from `providers.json` |
| med | Budget option 3 conflicted with tier A; no budget option covered real-log replay | Fixed the tiering and added real replay at K=1 |
| med | Unconditional stretch ban at ≤ 42 days | Made conditional on M2.T12 |
| med | `vllm-serve.sh` stop/start removes `vllm-rosa` | Use `docker stop`/`start` |
| med | Incomplete commands and `…` paths | Short-form expansion rules and full paths |
| med | Request-suite context procedure vague; overloaded `executed_move`; missing `requires` | Defined experiments, flags and prereg fields; `suite_executed`; `requires: mapped_unique` |
| med | Host venv could import SDKs it lacks; no Isaac adapter | Lazy imports, `configs/isaac_launch.json`, `test_job_adapters.py` |
| med | `build_jobs` keys undefined; only four hashed files | Listed the keys; `analysis_code_sha12` and `harness_code_sha12`, with `--compare` |
| med | Real-log list had no construction rule; wrong NN reasoning for B1; no V-probe renderer | Built from M3's CSV; B1 keeps the oracle; render-at-pose verification |
| med | evo cross-check vague; `sample_episodes.py` unspecified | Exact commands, spec and 2 tests |
| low | Scope note for M4.T4 vs M4.T13; second integration run ambiguous; fallback header; served-model match; MAX_SEQS; numpy on the Mac | Each fixed |

### M5 — Report (`M5-report.md`, 15 tasks)

| Sev | Finding | Fix applied |
| --- | --- | --- |
| high | Grep status checks printed several rows | A status helper (first `task_status.sh`; the consistency review replaced it with README **L12** `task_status.py`) |
| high | Wrong cross-milestone IDs (M3.T11/T17, M3.T12/T19, M2.T13/T14/T20, M1.T12, M3.T13, M6.T9, M4.T16) | Checked list of external IDs; tables corrected |
| high | M5 regenerated M4.T16's tables and figures | Ownership split: M4 owns `report/generated/{tables,figures}/`, and M5 `\input`s them with a SHA-256 check |
| high | Rule R4 could not label kinsim closed-loop results | Label taken from the CSV's `source`/`mode` |
| high | Wrong `dv.json` access path | `['values'][key]` |
| high | `check_report.py` had no tests until T9 | 13 tests in M5.T8, run with the Mac's system pytest |
| high | Checker spec was wrong (BibTeX warning count, over-broad secrets regex, wrapped log lines) | Corrected parsers and a narrower regex, tested |
| high | `git diff <v3.3>..HEAD` missed an uncommitted v3.4; zsh `$h:c` trap | Tested loop and a zsh pitfall note |
| high | Ledger confirmation grep could never match | Fixed the values and the counts |
| high | Architecture figure left to judgement | Full TikZ source, compiled and size-tested |
| med | Report-assets API gaps; `episodes.csv` has no seed; condition spellings assumed; baseline key names; page-limit source; arena figure ownership; M4 freeze files; per-task diffs; git trailer parsing | Each fixed (`resolve_number`, `render_cell`, `seed_of`, key convention, DELIVERABLES reuse, etc.) |
| low | Wording and fact errors | Corrected in place |

### M6 — Demo and presentation (`M6-demo-presentation.md`, 17 tasks)

| Sev | Finding | Fix applied |
| --- | --- | --- |
| high | Wrong M3 IDs (M3.T12 vs T18, T1 vs T13, T11 vs T17; M3.T20 missing) | Corrected throughout. The car take requires M3.T18, T7, T13, T17 and the OD9 path |
| high | Wrong M2 IDs (T13/T14/T20/T17/T15/T16) | Prerequisites rewritten, with M2 symbol names |
| high | Slide numbers came from M4.T6/M4.T3 and re-parsed CSVs | Slides read only `report/generated/numbers.json` (M5.T9); final results from M4.T16/M4.T14 |
| high | `--max-steps` was appended outside the quoted command | `demo_tmux.sh` takes it as a 4th argument inside the quotes, with a check |
| high | The vendored prompt module imports `rosa` and prints at import | `prompt_sha12` filled in `rosa-ros2`; import wrapped in `redirect_stdout` |
| high | Stub sessions wrote and `rm`'d the global `data/LATCH` | Per-session `latch_path` rule using M2's `Latch` |
| high | `emergency_stop` could be blocked by a running move | Split locks, with a non-blocking test |
| high | Executor contract did not match M2's `StepContext` | Uses M2's fields, the MoveCommand builder rule, and `\|angle\|` caps |
| high | Estop check relied on a missing log line and human reaction time | Server start/end lines; `--on-next-move` estop |
| high | Heartbeat during long thinking was unchecked | Environment server keeps the heartbeat; 9–11 Hz check |
| high | Unverified imports in `rosa-ros2` | Import check step; scoring moved to `demo/score.py` in `beaconmind-ros` |
| high | The car take lacked beginner what/why and concrete checks | Steps 5–11 rewritten (power path, STOP test ≤ 0.200 s, placement, disarm, latch only by Xiaohui, resume) |
| med | Step order; a compact-JSON test; the refuse segment; card budget; narration `apad`; fixtures; "watch" steps; folder ownership; obslog driver label; latch ending | Each fixed |
| low | Machine label; Module 4 test output; world generation; vLLM expected output; deck helper constants; tool-call order | Each fixed |

---

## Part B — Cross-plan consistency review (2026-10-06)

**Method.** I read `README.md` in full and the summary, status, task-list, entry-criteria and dependency
sections of all six milestone files, then every passage those sections point to across files. I wrote two
scratch scripts on the Mac:

- **Dependency check:** parses each file's task-list "Depends on" column into a graph and checks it for
  cycles and dangling IDs. Result: **102 tasks, no cycles, no reference to a missing task**. It also
  computes effort-weighted critical paths.
- **Status helper test:** runs the L12 status helper over every task ID. Result: 102 rows read, all `todo`.

I also searched every file for task IDs above each milestone's maximum (none outside test fixtures such as
`M5.T99`). Nothing was run on the Spark. All edits are under `course-project/plan/`.

### B1. Cross-milestone references, deliverables and contracts

| # | Sev | Inconsistency | Fix |
| --- | --- | --- | --- |
| 1 | high | **Three spend ledgers.** M1.T11 used `data/api_spike/ledger.jsonl`, M2.T7 `data/spend/ledger.jsonl` (and said the spike did not count toward $100), and M4.T10 `data/budget/ledger.jsonl` (counted the spike, did not see M2's spend). The $100 pilot cap could have been exceeded without any guard noticing | New README contract **C13**: one ledger `data/budget/ledger.jsonl`, with fixed keys, phases `m1_spike`/`m2`/`gate`/`pilot`/`sweep`/`stretch`, and a `pilot` group capped at $100. M2.T7 `RunBudget` writes there with phase `m2` and imports the spike total. M4.T10 adds `m2` to `PHASE_GROUPS` and imports `m1_spike` only once. M1.T11 writes `ledger-total.txt` in a fixed format |
| 2 | high | **Three different task-status helpers**: M3's `status()` grep function, M4's `task_status.py` and M5's `task_status.sh`, with different outputs; M1, M2 and M6 used greps | Single helper in new README convention **L12** (exact source, tested over all 102 tasks). M1.T1 step 6 creates it. M3, M4 and M5 call it; M1, M2 and M6 conventions say their grep rows are the older form. M5.T8 step 8b now only creates it if missing |
| 3 | high | **Estop result mapping** differed between twin (M2.T5: `refused`) and car (M3: `link_lost` + flag); M3 could only list M2 lines to change | Registered as **OD15** (default (a) `link_lost` + bit 2), asked in M1.T10, else by whichever of M2.T5 or M3.T2 runs first. M2.T5's executor, test name and smoke check now follow OD15; M3.T2 checks for an existing answer first |
| 4 | high | **`car.json` key names** were never fixed: M1.T9 listed raw quantities; M2.T3's view accepted several spellings; M3 read top-level keys that do not exist in `bm.car/1` | M1.T9 step 5 now lists the exact `values` keys (raw + derived `wheel_diameter_*`, `track_width_m`, `sweep_radius_m`, `counts_per_rev_*`, `ticks_per_wheel_rev`). M3 §0.4a reads them through `config.load_car()` and writes its calibration keys in the same per-value form |
| 5 | high | **M5.T4 needed a long-format CSV** from M2.T12, but M2.T12 wrote only Markdown tables, so M5.T4's branch would always stop | M2.T12 step 8 writes `summary_long.csv` (exact columns) and a copy of `episodes.csv`; new test `test_summary_long_columns_and_rows` (6 tests). M5.T4 points at the file |
| 6 | high | **`bm-clear-latch` did not exist inside `beaconmind-ros`**: M1.T3 puts the package on `PYTHONPATH`, so no console scripts are installed, yet M3.T13 and M6 call `bm-clear-latch` in the container | M1.T3's Dockerfile installs a one-line wrapper `/usr/local/bin/bm-clear-latch` → `python3 -m beaconmind.validator clear-latch`. README L3 and C5.5 record it. M6's checks source the workspace and use `--operator` (there is no interactive "type clear" variant) |
| 7 | high | **The real-car chain depends on the Isaac chain**: M3.T9 extends M2.T17's `ros_env.py`, so under the README §3.4 Isaac fallback, M3.T9 (and the real logs in the cut line) would be blocked indefinitely | M3.T9 step 1 has an Isaac-fallback branch: it creates `envs/ros_env.py` to M2.T6/M2.T17's specification. M3.T9's prerequisites now list M1.T12, M1.T13, M2.T13, M2.T6, M2.T17 and M2.T11. M6 has an Isaac-fallback branch (kinsim take and top-down view). README §3.4 describes the fallback's effect on M3, M4 and M6 |
| 8 | med | M4 handed off to **M5.T4** and **M5.T3**, but the M5 tasks that consume M4 are **M5.T14** and **M5.T13**; M4 cited `evidence/M3/M3.T11/` for the ground-truth error (now M3.T17, `configs/overhead_camera.json`) | Corrected in M4's "What M4 unlocks", the M4.T16 title and steps, the CONTEXT template, the cross-milestone section and the M4.T13 inputs, step 6 and task list |
| 9 | med | M2.T15 said "if M1.T5 showed the texture method failing", but M1.T5 tests only the AprilTag MDL | M2.T15 step 1 says its spike is the first test of the texture method, with three branches |
| 10 | med | M3.T12 used B2 as the driver, but B2's move decisions are M2.T19 and the recorder CLI is M2.T11; neither was a prerequisite | Added to M3.T12's prerequisites and task list, with the operator branch if M2.T19 is not done |
| 11 | med | M3.T2/T7/T9/T11–T19 needed the Pico node visible from `beaconmind-ros` (now M1.T13) and the camera bridge (M1.T12), but listed only M1.T3/M1.T7 | M3 entry table and task list now name M1.T13 and M1.T12 |
| 12 | med | M6 still described the M2/M3 latch disagreement as current; M6 "type `clear`" | M6 fact row and both latch steps corrected (M2.T1 CLI, `--operator`) |
| 13 | med | M6 used "M4.T3 dev dry run" for refusal rates under the cut line, but M4's cut line drops M4.T3 and M4.T14 | M6 says no benchmark refusal rate exists at the cut line and the slide states it |
| 14 | med | M6.T1 and M5.T8 both asked the report page limit | M6.T1 question 5 first reads `evidence/M5/M5.T8/answers.md` |
| 15 | med | Stale notes: M4.T6 "report does not load `booktabs`" (M5.T8 loads it); M5's matching pitfall | Both updated (keep `\hline`; both work) |
| 16 | low | M1, M2 and M3 "What … unlocks" lists did not match the files (for example M2 "M6.T2 needs M2.T5", M3 "M4.T4 includes real logs", M1 "M1.T5, T8, T9 → M2.T4–T6") | Rewritten to match the consolidated graph |
| 17 | low | README L2 `world_id` = `sim-<condition>-s<seed>` contradicted the short forms every file uses (`sim-dup-`), and log_id suffixes were undefined | L2 now gives `uni/dup/hid`, the `i<k>`/`k<k>` suffixes, and `real-a-<n>` |
| 18 | low | README C9.2 lacked the footer `detail` and M2's revised replay rule (runs to log end; `last_move` from the logged observation) | C9.2 updated |
| 19 | low | README L3 (`pip install -e` in the container), L5 (agent only `-it`) and L6 (excludes) differed from M1.T3 and M1.T1's reviewed choices | README accepts the M1 choices (PYTHONPATH + wrappers; `-d` agent for non-interactive sessions; extra excludes) |
| 20 | low | README §4.3 template example used a plain grep for status | Uses the L12 helper |

### B2. Duplicated ownership and orphaned scope

| # | Sev | Finding | Fix |
| --- | --- | --- | --- |
| 21 | med | **Two tag-sheet generators**: M1.T3 `tools/make_tags.py` (`--black-mm --dpi`) and M3.T10 `tools/make_tag_sheets.py`. A third, M2.T15 `make_tag_textures.py`, is Isaac-only and is kept | M3.T10 step 4 reuses `make_tags.py`'s marker function (or extends it) and checks that the sizes agree. Its test moved to `beaconmind/tests/` (L4) with `importorskip("cv2")` |
| 22 | med | **AI-disclosure audit missed the decks and the design documents**: `disclosure_audit.py` covered `.md` only under `presentation/`, `report/` and `evidence/`, so `proposal-talk-track.md`, `AGENT-DESIGN.md`, `plan/` and every `.pptx` (proposal deck and final deck) were unchecked | M6.T6 audit now covers the top-level design docs, `plan/`, and `.pptx` slides and notes (stdlib `zipfile`), with `test_pptx_disclosure_detected` (6 tests) |
| 23 | low | M3.T19 (real replay) and M4.T13 (real replay sweep) overlap | Already settled by M4: reuse only when the hashes match the freeze. Recorded in M3 "What M3 unlocks" |
| 24 | — | Scope coverage check: W0 (M1.T3, T13), W1 (M1.T9, M2.T4, T15, T16, T5), W2 (M1.T6–T8, T12), W3 (M3.T2–T7, T14), W4 (M2.T8, T9, T19), W5 (M2.T7, T18), W6 (M4.T8), W7 (M4), W8 (M3.T10, T11, T17); open decisions (M1.T10 + README §3.5); MCP doc update (M1.T10 §M); CONTEXT refresh (M1.T14, each milestone's completion template, M6.T6 final); latency re-measure (M1.T4, M4.T11); Isaac spike (M1.T5, M2.T15); STBY pull-down (M3.T1); untethered power (M3.T20); data governance (M1.T10 block 12, M4.T2 `governance.py`, README L8); API budget (M1.T11, M2.T7, M4.T10, C13); refusal suite (M4.T3/T14, metrics M2.T20); AI disclosures (M5.T11/T7, M6.T5, M6.T6 audit); ROSA demo D10 (M6.T2, T7–T10, T3) | **Nothing orphaned.** Only the disclosure audit's coverage was incomplete (item 22) |

### B3. README updates

- **§3.2 Milestone index:** every file, its task count, every task ID with its effort and title, and a
  paragraph explaining how the originally reserved IDs were split.
- **§3.3 Consolidated dependency graph:** a summary mermaid graph (labels quoted for safe parsing) and a
  per-task prerequisite table generated from the six task lists, with the soft and conditional edges listed.
- **§3.4 Cut line and critical paths:** the cut line restated with the current IDs; effort totals; four
  computed critical paths (to M2.T12, to submission, bench chain, demo chain); and the effect of the Isaac
  fallback.
- **§3.5:** OD15–OD20 added, plus a pointer to M6's MD1–MD7.
- **Conventions and contracts:** L1, L2, L3, L5 and L6 adjusted; new L12. C2, C5.5, C8, C9.2 and C10.8
  adjusted; new C13.
- **§9:** status of each file and task counts. **§9.1:** two facts updated. **§10:** disclosure updated.

**Critical path (effort-weighted: S = 1, M = 2.5, L = 4.5 sessions):**
M1.T1 → M1.T2 → M2.T1 → M2.T13 → M2.T3 → M2.T4 → M2.T16 → M2.T5 → M2.T6 → M2.T17 → M2.T11 →
**M2.T12 (cut-line result, ≈ 24 sessions)**. To submission, the chain continues from M2.T11 →
M3.T9 → M3.T16 → M3.T12 → M3.T19 → M4.T13 → M4.T16 → M5.T14 → M5.T5 → M5.T6 → M5.T7 → M6.T6
(≈ 45 sessions). The bench chain (M1.T3 → M1.T13 → M3.T2 … M3.T7 → M3.T10 → M3.T8 → M3.T15 →
M3.T12, ≈ 28.5 sessions) runs in parallel.

---

## Part C — Open items that need Xiaohui

### Decisions to make (each has a default; the task named asks if it was not answered earlier)

1. **OD19 — scope against effort.** The full plan is about 198 sessions and the cut line about 163.
   There are 68 days left as of 2026-10-06. Default: plan the full scope but commit to the cut line and
   apply the §3.4 triggers. Alternative: adopt the cut line now.
2. **M1.T10 decision sheet (20 blocks):** OD1–OD5, OD7, OD8, OD11, OD12, OD14, API budget, data
   governance, W0, DV updates, and the new **OD15** (estop mapping), **OD16** (tool `status` key),
   **OD17** (C0/C2 additions: `bump_lin_acc_mps2`, `sweep_margin_m`, subscriptions, refusal reasons,
   diagnostic topics) and **OD18** (the M1.T11 waiver for M2.T7–T10).
3. **OD20 — random-explorer arm R** (M4.T5 step 3, before the freeze).
4. **M6 MD1–MD7** (ROSA trimmed vs stock, environment server, the `rosa-ros2` mount, demo seeds,
   re-render footage, ffmpeg assembly, slide display), and **M6.T1's eleven deliverable questions**,
   including the report page limit (shared with M5.T8).
5. **Money:** the STBY resistor, stand and overhead webcam (M3.T1, whose FOV must be computed from their
   ceiling height first); frontier spend for M1.T11 (≤ $5), M2.T18 (≤ $2.50) and the M4 pilot and sweep
   caps.
6. **AI-disclosure reconciliation** of the report ledger (M5.T11), and reading the final PDF (M5 exit).

### Unresolved facts (each is a verification step inside the task named; nothing was executed on the Spark)

- `apriltag_ros` TF frame names and parameters; `image_proc` rectify executable; `cv2.aruco` in Ubuntu
  22.04 `python3-opencv`; ESP32 Arduino core aarch64 toolchains and PSRAM default; AprilTag MDL
  parameters; vLLM metric names (M1.T3, T5, T6, T4).
- Isaac URDF importer headless enable, OmniGraph input names, and camera images over UDP-only FastDDS
  (M2.T16).
- Whether `beaconmind-ros` can launch Isaac jobs on the host for M4.T15 and the M4.T8 N arm (M4.T10 I13).
  A host-side runner may be needed.
- Frontier model IDs, prices and option names (M1.T11, re-checked before any spend).
- `normal_sigma_deg` (tag-normal σ) is not measured by M1.T8; M2 defaults it to 10° as a recorded
  assumption.
- Whether `latexmk`/`pdftotext` exist on the Spark host (M5.T9 counts allow either).
- The ≥ 40 GB free-memory threshold for Isaac + vLLM (M4.T15) is a judgement, not a measurement.
- The overhead webcam's availability at the needed FOV (about 60° H and V).

### Known deviations from AGENT-DESIGN wording, kept on purpose

- M2.T15 renders tags with a textured quad by default rather than the AprilTag MDL. §W W1 asks that
  "the Isaac AprilTag material" decode; a texture material decodes the same tag. If Xiaohui reads §W
  literally, they should say so before M2.T15.
- M6 MD1's "trimmed ROSA" default departs from D10's wording ("stock ROSA"); M6.T2 asks first.

### Minor items not changed (low risk, noted for the next editor)

- Report figures live in two trees: M5.T10 writes `report/figures/generated/`, while M4.T16 owns
  `report/generated/{tables,figures}/`. Both are documented in M5. M6 slides read M4's folder, which
  exists at the cut line because M4.T16 runs in reduced form.
- M3's status-table Evidence column shows `—` instead of the evidence path.

---

## Part D — Revision from the Assignment 7 firmware lessons (2026-10-24)

**Why.** Xiaohui asked to document the firmware research and to "modify the task plan accordingly ... add tasks
such as tuning PID", and decided that the project may reuse the instructor's code; since 2026-10-23 the car's wheels
are never turned by hand. The facts are in [`../research/2026-10-24-car-firmware-lessons-and-pid.md`](../research/2026-10-24-car-firmware-lessons-and-pid.md)
(F1-F11), and the list of changed sections is in its §5, in README §3.2 ("Revision of 2026-10-24") and in the new
`CONTEXT.md` entry.

**How.** One editor per file (`M3-real-car.md`, `README.md`, `CONTEXT.md`), then three adversarial reviewers with
separate lenses (template and executability by a lower-end model; facts against the cited sources; cross-file
consistency and the safety rules), one skeptic who tried to refute every finding, and one fixer per file. A second
pass then synced `M1-foundations.md`, `M6-demo-presentation.md` and the M3 effort sizes, with a read-only
consistency check over every plan file and `AGENT-DESIGN.md`.

**Findings.** 67 raised, 47 confirmed by the skeptic and fixed: template 2 high, 18 med, 6 low; facts 3 med, 8 low;
consistency 4 high, 2 med, 4 low. By file: M3 35, README 5, research note 3, CONTEXT 1, other files 3 (handed to the
second pass or to Xiaohui). The high ones:

| Sev | Finding | Fix applied |
| --- | --- | --- |
| high | M3.T22's drive arm could never count: its pattern could not reach the required 600 s of wheel motion | the arm's pattern and counting rule rewritten so it can pass |
| high | M3.T23 said every `wifi_roam_*` call outside the init is already inside `#if WIFI_ROAM_MODE >= 1`; `poll_one()` calls one in every mode | the statement corrected, with the call named |
| high | M1.T13 still expected the Module 5 tilt image and `/pico2w_led` on a Pico that runs the Assignment 7 firmware | second pass: M1.T13 updated for `/pico_odometry` (or `/bm_pico` after M3.T14), the agent-container check and the 30 s session rule |
| high | M3.T2's new rule (STBY raised only by the control context while armed with a fresh heartbeat) blocked every BENCH motion command the later tasks need | a BENCH-only exception in M3.T2, used by M3.T3, and a check in M3.T6 that a disarmed production image refuses a move |
| high | M3.T22's drive arms ran the motors with the battery on under firmware that boots armed and can reboot itself, without the STBY pull-down | M3.T1 (pull-down fitted) is a prerequisite of the drive arms, with a safety note in step 1 |
| high | `pico_serial.py`'s redaction (any line containing `SSID` or `PASSWORD`) would hide the radio read-back line M3.T23's boot test needs | a narrower redaction pattern plus a test, and the read-back line required unredacted |

**Second pass.** The sync of M1, M6 and the M3 effort sizes was followed by a read-only check of every plan file and
`AGENT-DESIGN.md`. It found no remaining 1000 ms watchdog, 200 ms or ping-reboot rule and no "write fresh" wording, and
listed 23 smaller items (a missing M3.T20 edge for M3.T24 in the README, the UDP 8888 port also held by `m7-gazebo`,
two names for the counts-per-turn key, the README still naming J1 as the car's firmware, placement steps that did not
say "lift, never roll it into place", and stale encoder sides in superseded lines). A final fix pass applied them to
README, M3, M1, M2 and M6 before the commit; `CONTEXT.md` was updated by the orchestrator.

**Left for Xiaohui.**
- `AGENTS.md` was updated at Xiaohui's request on 2026-10-24 (§5: the instructor-code exception and the rule that
  lab firmware carries the Wi-Fi fix; §2; §7.4: J2 on the car, session rebuild after an agent restart), so the older
  rules no longer conflict; M3.T14's pitfall about the conflict can be read as history.
- OD21 (does a `link_lost` stop latch the episode on this link?) waits for M3.T22's measurements.
- The instructor's PID source is only in `~/Downloads/pid-source-files.html` until M3.T4 step 0 archives it.
- The `ab_run.sh` / `ab_compare.py` helpers of the 2026-10-24 Wi-Fi runs were session scratch; M3.T22 writes repo
  versions.

---

## Generative-AI disclosure

Claude Opus 5.5 via Claude Code wrote this review log on 2026-10-06. Part A summarizes the six
per-milestone adversarial reviews, which were also run by Claude Opus 5.5. Part B is the cross-plan
consistency review: Claude read the plan files, wrote the scratch dependency and status-helper checks,
and ran them on the Mac. It made the edits listed above, only in `course-project/plan/`. Nothing was run
on the Spark and nothing was committed. Every default and fix here is a proposal. Xiaohui Chen owns the
project and decides every item in Part C.

Part D (2026-10-24) was written by Claude Opus 5.5 via Claude Code from the outputs of the review workflows it ran
(editors, reviewers, a skeptic and fixers, all Claude Opus 5.5). Nothing in it was run on the car. Xiaohui Chen made
the decisions it records and decides the items left open.
