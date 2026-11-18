# Unattended batch runner for real-car episodes (plan §3.6 "Unattended batches"; tasks M3.T12 and M3.T18), 2026-11-18

Status: **code and tests only, verified on the simulated car in the simulated room. Nothing was published on the
real car's ROS graph; no batch has run on the car.** The stand test and the floor check
(`../../M3.T6/README.md` section 5) stay attended and must pass first: the runner refuses a real batch without a
recorded pass marker (below). The folder is M3.T12's because that task is the real B2 episodes; the same runner
serves the live-model episodes of M3.T18 (`--policy <model key>`).

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote the runner, the resection, the tests and this
note. Xiaohui Chen approved unattended batches on 2026-11-18 (plan README §3.6) and runs the attended tests.

## Files (under `course-project/`)

| File | What |
| --- | --- |
| `beaconmind/src/beaconmind/car/resection.py` (new) | pose from the surveyed tags: `resect` (two tags or more, repeated ids handled), `position_fix` (one tag and the tracked heading) |
| `beaconmind/src/beaconmind/car/batch.py` (new) | `PoseTracker`, `MoveGuard`, `Monitor` (the halts), `BatchEnv` (the harness's environment), `BatchRunner`, `dry_rig`, the pass marker |
| `tools/car_batch.py` (new) | `run`, `record-pass`, `clear-halt`, `status` |
| `tools/car_batch.sh` (new) | Spark host: starts the R2 recorder for the whole batch, runs the tool in a `beaconmind-ros` container, stops the recorder |
| `beaconmind/tests/test_car_batch.py` (new) | 80 tests |
| `car/telemetry.py`, `link.py`, `ros_io.py`, `simcar.py` (my own, changed) | the Pico's supply voltage (telemetry field 5); `car_state` carries `drive_status`, `vsys_min_mv`, `agent_rx_age_ms` |
| `car/camera.py` (my own, changed) | a frame whose counter (`X-BM-Seq`) repeats is a stale picture: an error |

The 29 frozen study files are untouched: `prereg_freeze.py --verify` prints
`files and logs: OK, all 29 files and 30 logs match`.

## What a batch does

`bash course-project/tools/car_batch.sh <label> run --world <world file> --scenarios <start poses> --initial-pose x,y,theta --episodes N --policy b2`

The batch's folder is `course-project/data/batches/<label>/`: every rerun with the same label finds the earlier
halt, manifest and spend there (it is deliberately not inside a recorder session, which is new on every run).

1. **Refuses to start** unless: the pass marker is valid; the recorder is recording (and its tmux session is
   alive); the project latch `data/LATCH` is clear; no `HALT.LATCH` is in the batch folder; the manifest does not
   say `running` (an earlier run that died without a record: it then writes the halt itself); no other program
   holds the car link; the manifest is of the same configuration.
2. **Drive map:** sets 0.25 / 0.33 (`--drive-map`) and reads it back from telemetry; anything else halts before
   any move.
3. **First circle:** twelve left turns with a view at each heading. The first circle of a process is solved
   **without** the taped pose and then compared with it: more than 0.5 m or 30° apart is a halt (one of the two is
   wrong and a person must say which). Until a circle has confirmed the pose no forward move runs, no per-step
   view is trusted, and the taped pose must leave 0.65 m of room around the car's sweep circle.
4. **Per episode:** drive to the start pose with the five C2 moves only (face it, go, look again;
   `--start-attempts` 3, tolerance `--start-tol-m` 0.20 m, `--start-tol-deg` 20°); the circle after arriving is
   the start-of-episode ground truth and the origin of the map frame the agent sees; the transit is measured by
   odometry and by the tags (**encoder-scale check**, below); the episode runs through `harness/closed_loop.py`
   `run_episode` (B2 or a model) on `BatchEnv`; a last circle gives the end pose.
5. **Every move** — the agent's, the scans', the transit's — passes the guard, and the car is looked at again
   (fresh telemetry; a camera frame if none arrived for 3 s) immediately before it.
6. **Outputs** in the batch folder: `manifest.json` (`bm.car_batch/1`), `summary.txt`, `HALT.LATCH` when halted,
   `spend.jsonl`, and per episode `episodes/<id>/`: the harness's `seed_<n>.jsonl` and `.moves.jsonl`,
   `truth.jsonl` (ground truth per step), `backend/steps.jsonl`, `pre/` and `post/` (scans and transit). In the
   recorder's session: every frame (`frames_backend/`), the move logs (`moves/`), `batch_markers.jsonl` with each
   episode's start and end.
7. **Resume:** after an operator has looked at the car and cleared the halt, the same command with the car's new
   taped pose, or `--initial-pose last` when nobody moved the car (the pose the batch last tracked). Finished
   episodes are skipped. An unfinished episode is never replayed; it runs again as a new attempt (`ep02-a2`); one
   left `running` by a dead process becomes `abandoned`. Step, time and spend caps count the whole batch across its
   runs.

World file, start poses and range limit are parameters (`--world`, `--scenarios` / `--scenario-ids` / `--start`,
`--max-range`): the tag configuration is still being chosen.

## The pass marker

`course-project/data/real/ATTENDED_PASS.json` (git-ignored, on the Spark), written only by

`bash course-project/tools/car_batch.sh - record-pass --operator <name> --stand-session <session> --floor-session <session>`

which a person runs after the attended stand test and floor check have passed. It requires two **different**
recorded sessions under `data/real/`, the stand session with at least 5 and the floor session with at least 10 move
logs that ended `done`. It stores hashes of `configs/car.json`, `configs/dv.json` and the twelve modules of the car
package. A real batch is refused when the marker is missing, older than 7 days (or dated in the future), or any of
those files differs today (the comparison runs over today's file list, not over what the marker chooses to
contain). What it cannot know: whether the tests' pass criteria were met. It records that a named person said so
and which sessions show it. The firmware on the car is not in it (checked at the start through the telemetry
layout and the drive map); the world file is a parameter of each batch.

## Ground truth

Per plan §3.6 the pose comes from the surveyed tags, not tape. All of it is recorded with its uncertainty:

- **Full-circle fix** (episode start and end; `first_fix`, `start_fix`, `end_fix` in the manifest): twelve views
  joined by the turns' odometry, then the rigid transform onto the surveyed tag positions (`resection.py`). Not
  taken when its tags disagree by more than 0.08 m rms (a tag surveyed wrongly). When its position sigma exceeds
  0.15 m (few tags, or far ones) it is not taken alone: once an earlier circle has confirmed the pose it is
  blended with the tracked pose and the result must be within 0.15 m; a first circle is never blended with a tape
  reading.
- **Per-step fix** (`truth.jsonl`, `view_fix`): two or more tags in the step's picture give a pose; one tag and the
  tracked heading give a position; otherwise `no_fix: true`. A fix farther from the tracked pose than three
  combined sigmas plus 5 cm is not used; three in a row halt the batch.
- **Tracked pose** (`truth_map`; also what `env.truth()` gives the harness, with `fix`, `sigma_xy_m`,
  `sigma_theta_deg`, `steps_since_fix`): odometry between fixes, each fix blended in by inverse variance. The
  position sigma never goes below 0.05 m: fixes of one tag repeat its survey and range-scale error.

What the stated sigma covers: noise and geometry, with an assumed per-tag noise of 0.03 m + 0.04 × range
(`fix_sigma_a_m`, `fix_sigma_b`: **assumed, to be replaced by the tag pilot's figures**, work list 2.4). What it
does not cover: a common range-scale error of the camera and errors in the surveyed tag positions. The plan's three
tape readings (first start, last end, one spot check) bound those. The agent sees none of this.

`final_pose_error` compares the agent's last report with the tracked pose at that observation (the move decided in
the last step runs afterwards); `tracked_minus_end_scan` says how far the tracked pose was from what the end circle
then measured; `odometry_scale_check` holds the transit's two lengths.

## The guard

The free area is the world file's `arena.drive_polygon_m` (inside the walls, in front of the desk line
x = 0.66 m; convex, counter-clockwise, checked) minus every obstacle box. Everything else is a wall, known or not.

- **Straight move:** the footprint (`configs/car.json` `corners`, cables included) at the end of the move, taken
  4 cm longer and at ±5° of heading, must stay `--wall-margin` (0.15 m) plus two sigma of the position (at most
  +0.15 m) inside the free area; and the move must end where a turn is still allowed with 5 cm to spare.
- **Turn:** the sweep circle (0.178 m) must stay 0.03 m plus one sigma (at most +0.10 m) inside the free area.
- **Far from the last tag fix:** no straight move may take the distance driven since the last tag fix past
  0.75 m (`max_blind_travel_m`). Whatever the odometer's error, it then stays inside the wall margin. Turns stay
  allowed (turning is how a tag comes into view); the transit looks around with a full circle when it gets there.
- **Uncertain pose:** position sigma above 0.25 m, or a pose that is not a number, blocks every move and halts.
- Inside an episode a blocked move comes back `refused` (`batch guard: ...`) and nothing moves; the `safety` flags
  the agent sees are the guard's, intersected with the backend's own. A blocked scan or transit move halts.

**The guard is only as good as the tracked pose.** Three things keep the tracked pose honest: the first circle is
compared with the tape; fixes that disagree with it are refused; and the encoder scale is checked twice (the
transit between two full-circle fixes must measure the same length by odometry and by the tags within 10 % plus
the fixes' own uncertainty when it is 0.3 m or longer; and during episodes, fixes that keep landing ahead of or
behind the odometry by more than 12 % of the distance driven halt the batch). What still gets through: one tag
surveyed 0.3 m wrong, seen alone, pulls the tracked pose up to 0.33 m while the stated sigma stays near 0.1 m; in
the reviewer's probe the simulated footprint then came within 4 cm of the edge of the driving area (not past it).
**So the tag centres in the world file must be measured, not nominal, before an unattended batch.**

## Health halts

A halt ends the whole batch and is never retried. It writes `<batch>/HALT.LATCH` (the harness watches it and the
project latch) and, for the codes marked S, sets the project latch `data/LATCH` too. If `HALT.LATCH` cannot be
written the project latch is set whatever the code. Afterwards: look at the car;
`car_batch.sh - clear-halt --out course-project/data/batches/<label> --operator <name>`; if the project latch is
set, `car.sh clear-latch --operator <name>`; then the `run` command again.

| Code | Fires when | S | Test (`test_car_batch.py`) |
| --- | --- | --- | --- |
| `latch` | the project latch exists (STOP program, operator) or `HALT.LATCH` appears | — | `test_halt_latch_appears`, `test_halt_file_appearing_mid_run`, `test_halt_in_preflight_from_the_latch_and_the_car` |
| `link_lost` | a move ended `link_lost`, or the executor latched on one | S | `test_halt_link_lost_when_telemetry_stops_mid_move` |
| `car_restart` | the car's restart counter changed, or a step has no odometry | S | `test_halt_car_restart` |
| `telemetry_stale` | telemetry older than 1.0 s at a sensing or before a move; the executor refused for no telemetry | S | `test_halt_telemetry_stale`, `test_telemetry_stopping_between_moves_is_named_and_sends_no_move` |
| `command_timeout` | the car reports its command-timeout stop (drive status 2) | S | `test_halt_command_timeout_seen` |
| `car_disarmed`, `imu` | the car reports itself disarmed / IMU not ready | S | `test_halt_in_preflight_...`, `test_halt_imu_not_ready_before_a_move` |
| `camera` | no frame at a stop or before a move; frames missing at 2 stops in a row; a stale frame | S | `test_halt_camera_down`, `test_halt_camera_frames_missing_twice`, `test_a_stale_camera_frame_is_an_error` |
| `supply_low` | the Pico's supply (telemetry field 5) under `--min-vsys-mv` 4300 | S | `test_halt_supply_low` |
| `stall` | a move ended `stalled` | S | `test_halt_stall` |
| `move_timeout` | a move ended `timeout` (blocked, or fading motor batteries) | S | `test_halt_move_timeout`, `test_halt_slow_car_times_out` |
| `slow` | a FORWARD_25 peaked under `--min-forward-speed` (off by default) | S | `test_halt_slow_forward_move` |
| `executor_refused` | the executor refused a move the guard allowed (e.g. the drive map was lost) | S | `test_halt_executor_refusal` |
| `no_fix` | `--no-fix-steps` (24) steps without any tag fix; no full-circle fix at a start pose or at the first circle; the first circle disagrees with the tape | S | `test_halt_repeated_no_fix`, `test_the_first_circle_speaks_without_the_tape_and_a_disagreement_halts` |
| `fix_conflict` | three fixes in a row far from the tracked pose | S | `test_halt_fix_conflict` |
| `odometry_scale` | the transit's two lengths differ; or fixes keep landing ahead of / behind the odometry | S | `test_the_transit_checks_the_encoder_scale_before_any_episode`, `test_a_wrong_encoder_scale_halts_before_the_car_reaches_a_wall` |
| `pose_uncertain` | tracked position sigma above 0.25 m | S | `test_halt_pose_too_uncertain` |
| `outside_drive_area` | the tracked pose is outside the free area | S | `test_halt_pose_outside_the_driving_area` |
| `guard_blocked` | a scan or transit move was blocked; no room for the first circle | S | `test_halt_no_room_for_the_first_scan`, `test_the_first_circle_needs_room_for_a_wrong_tape` |
| `start_pose` | the start pose not reached within tolerance after the attempts | S | `test_halt_start_pose_not_reached` |
| `drive_map` | the car does not report the drive map that was set | S | `test_halt_drive_map_does_not_take` |
| `recorder` | the recorder session is no longer active, or has written nothing for 2 minutes (rule R2) | S | `test_halt_recorder_stops`, `test_a_recorder_that_stopped_writing_is_noticed` |
| `episode_wall_clock` | an episode (scans included) runs past `--episode-minutes` (60) | S | `test_halt_episode_wall_clock` |
| `batch_wall_clock`, `batch_steps` | the batch, over all its runs, passes `--batch-hours` (6) or `--batch-steps` (2,500 moves) | — | `test_halt_batch_wall_clock_and_step_cap`, `test_the_move_cap_counts_the_whole_batch_not_one_run`, `test_the_wall_clock_cap_counts_the_whole_batch` |
| `usd_cap` | spend reached `--cap-usd` (no request is sent after it; spend is appended to `spend.jsonl` as it happens and counted again on a rerun) | — | `test_halt_usd_cap` |
| `harness_latch` | the harness latched the episode (two error observations, contacts) | S | `test_halt_harness_latch` |
| `interrupted` | Ctrl+C, SIGTERM, SIGHUP | — | `test_an_interrupted_episode_is_halted_in_the_manifest`, `test_terminate_and_hangup_end_like_an_interrupt` |
| `harness_error`, `error` | another harness error; any exception; a manifest that cannot be written; an earlier run that died without a record | — / S | `test_halt_on_an_unexpected_error`, `test_a_run_that_died_without_a_record_needs_an_operator`, `test_a_halt_that_cannot_be_written_sets_the_project_latch` |

`test_a_fault_while_the_agent_thinks_stops_the_next_move` runs seven of these faults while a (simulated) model
thinks for 20 s between two steps: no move is sent after the fault appears.

Not a halt: an episode the harness ends with `no_progress`, or the coded procedure stopping at a branch it does
not implement (`driver stopped`). The car is healthy; it is that episode's result and the next episode starts
with a transit elsewhere.

**Battery.** Telemetry has no motor-battery signal: field 5 is the Pico's own supply (the power bank), and the
motors run from their own AA pack. Fading motor batteries show as slower moves: the runner halts on any move
`timeout` and, when `--min-forward-speed` is set from the floor check's figures, on a slow FORWARD_25. Without that
setting a slowly fading pack is caught only at the first timeout.

Each halt test asserts through one helper: status `halted` with that code in the result, the manifest and
`summary.txt`; `HALT.LATCH` written; the project latch set for S codes; not one motion command published from the
moment the halt was recorded; the simulated car at rest for the next 2 s; a second run refused with no move sent.

## Dry run (`--dry-run`)

The same code on `dry_rig`: the simulated car (firmware model) placed in the world file's room, detections drawn
by the room simulator (`envs/kinsim_room.py`: field of view, range window, camera noise preset), walls that block
the wheels on contact. No ROS, camera, marker or recorder; its own latch file inside the batch folder.

`dry-runs.txt`: the five scenario start poses of `configs/arenas/real-room-scenarios.json` in the nominal room,
B2, full 150-step budget, four seeds per range limit, final code:

| Range limit | Batches complete | Episodes done | Halts |
| --- | --- | --- | --- |
| 2.0 m | 0 of 4 | 10 of 20 | four `no_fix` (24 steps without a tag fix) |
| 2.5 m | 3 of 4 | 17 of 20 | one `no_fix` |

Every episode recorded as done ended by the agent's own DONE (27 of 27; the guard refused no move of B2's in
them, because the `safety` flags already told it). Start-pose miss 0.02 to 0.19 m, inside the tolerance; B2's
final pose error against the batch's pose 0.00 to 0.02 m. Before the limit on distance driven without a tag fix
was added (review finding 8) the same runs gave 1 of 4 and 4 of 4: that limit costs a `no_fix` halt in tag-poor
stretches and is what keeps a wrong encoder scale from reaching a wall.
So with this layout an unattended batch needs the longer range limit or more tags in reach: at
2.0 m the halts are the runner doing its job, and each one costs a visit. The simulated odometry and tag noise are
mild (no scale error, no carpet veer unless asked), so the dry runs prove the logic and the bookkeeping, not the
real accuracy of resection.

## Tests

- Mac (Python 3.13), `pytest-mac.txt`: `tests/test_car_batch.py` **80 passed**; whole suite **590 passed, 10
  skipped**; `prereg_freeze.py --verify` OK.
- Container on the Spark (Python 3.10.12, `--network none`, ROS_DOMAIN_ID 42), `pytest-container.txt`: the batch
  file with the five car test files **275 passed, 1 skipped**.

Beyond the halts: resection recovers exact poses, stays inside three stated sigmas with 2 % / 1° noise in at least
190 of 200 draws, refuses one tag, unknown ids, a pose far from the prior, a bad residual, numbers that are not
finite, and tags with repeated ids it cannot tell apart; twelve narrow views give one fix; the guard blocks moves
toward each wall and the desk line, turns near the edge, everything when the pose is uncertain, and the desk box
even without a separate driving area; after any forward move the guard allows, a turn is still allowed; a
two-episode batch reaches both start poses within tolerance as the simulator's truth confirms, keeps the tracked
pose within three sigma of the truth at every step, and never puts the simulated footprint outside the driving
area; a tag surveyed 0.4 m wrong and an odometer reading 25 % short both halt with the simulated car clear of the
walls.

## Independent review (halt logic), 2026-11-18

A fresh agent reviewed the code adversarially: 1,140 fault-injection runs on the simulated car and targeted probes
(session scratchpad `review2/`). What held before any fix: no move was commanded after a halt was recorded or
after a latch file existed. Its findings and what was done:

| # | Finding | Outcome | Test |
| --- | --- | --- | --- |
| 1 (critical) | a rerun through the wrapper got a fresh folder: earlier halt, manifest and spend unseen | fixed: the batch folder is `data/batches/<label>`, independent of the recorder session | `test_a_rerun_from_the_tracked_pose_with_a_new_process` |
| 2 (critical) | after a restart the tracker believed the taped pose and a transit move ran on it; resume rarely worked | fixed: the first circle is required, solved without the tape and compared with it; no view is trusted and no forward move runs before it; room for a wrong tape is required; the tracked pose is saved and `--initial-pose last` restores it. The reviewer's probe: 128 of 128 wrong-pose restarts now halt at the first circle | `test_the_first_circle_speaks_...`, `test_no_forward_move_before_a_circle_has_confirmed_the_pose`, `test_the_first_circle_needs_room_for_a_wrong_tape`, `test_a_resumed_batch_takes_the_cars_new_taped_pose` |
| 3 | one mis-surveyed tag made the tracker confidently wrong; the footprint reached the wall | reduced, not closed: sigma floor 0.05 m, fixes that disagree are refused, full-circle residual limit 0.08 m, wall margin 0.15 m. Reviewer's probe on the final code: no run reaches the edge; the smallest true clearance over all its tag cases is 4 cm (a tag 0.3 m wrong, tracked pose 0.33 m off). See "The guard" for what remains | `test_a_tag_surveyed_wrongly_halts_before_the_car_reaches_a_wall`, `test_a_fix_that_disagrees_with_the_tracked_pose_is_not_blended_in` |
| 4 | a halt that could not be written was lost; `_save` raised out of `run()`; the rerun drove | fixed: project latch on a failed halt write; manifest write errors halt; a manifest left `running` refuses and writes the halt | `test_a_halt_that_cannot_be_written_sets_the_project_latch`, `test_a_run_that_died_without_a_record_needs_an_operator` |
| 5 | health was judged on the previous sensing, so one more move ran | fixed: fresh car state and a camera probe before every move | `test_a_fault_while_the_agent_thinks_stops_the_next_move` (7 faults) |
| 6 | SIGTERM and SIGHUP left no halt record | fixed: both end like Ctrl+C; the wrapper `exec`s Python and says to run under tmux | `test_terminate_and_hangup_end_like_an_interrupt` (handler and source text; not run under docker) |
| 7 | caps were per process | fixed: moves and wall clock count over all runs of the batch | `test_the_move_cap_counts_the_whole_batch_not_one_run`, `test_the_wall_clock_cap_counts_the_whole_batch` |
| 8 | an odometer reading 25 % short was not covered by sigma; wall reached | fixed three ways: no straight move takes the distance driven since the last tag fix past 0.75 m; the transit of 0.3 m or more between two full-circle fixes is measured by odometry and by the tags before any episode; fixes that keep landing ahead of the odometry halt. The reviewer's probe now: smallest true clearance +0.885 m, no contact | `test_no_straight_move_takes_the_car_far_from_its_last_tag_fix`, `test_the_transit_checks_the_encoder_scale_before_any_episode`, `test_a_wrong_encoder_scale_halts_before_the_car_reaches_a_wall` |
| 9 | one paid request after a halt (the harness asks the agent once more before it ends the episode) | declined here: it is in `harness/closed_loop.py`; no move results (the move is refused); cost one request | — |
| 10 | the pass marker could be satisfied by one arbitrary session; the fingerprint compared the marker's own keys; few files hashed | fixed: two different sessions with enough `done` moves; today's file list; `car.json`, `dv.json` and the whole car package | `test_pass_marker` |
| 11 | obstacles were never checked | fixed | `test_obstacles_count_even_without_a_separate_driving_area` |
| 12 | after Ctrl+C the episode stayed `running` | fixed | `test_an_interrupted_episode_is_halted_in_the_manifest` |
| 13 | a NaN range gave a NaN pose | fixed: such detections never reach a fix | `test_detections_that_are_not_numbers_never_reach_the_pose` |
| 14 | a crashed recorder left `.active` behind | fixed: the wrapper checks the recorder's tmux session; the batch halts when the session's logs stop changing for 2 minutes | `test_a_recorder_that_stopped_writing_is_noticed` (the wrapper's check is untested) |
| 15 | `supply_low` is the Pico's supply; fading motor batteries only show as stall/timeout | as designed; stated above ("Battery") | — |
| 16 | wrapper: `--batch-hours=7` not parsed; `--out` outside the repository vanished with the container | fixed in the wrapper (syntax-checked only) | — |
| 17 | wall-clock caps are checked only when the harness asks for a step; a hung model call overruns them | declined: the car is at rest during it, and the provider's own request timeout (900 s) ends it | — |
| 18 | telemetry lost between moves was called `executor_refused` | fixed | `test_telemetry_stopping_between_moves_is_named_and_sends_no_move` |

Tests the review called weak: the halt helper now counts commands from the moment of the halt; the restart test
asserts the manifest and the rerun; resume is tested through the tool with a new process and `last`; halts for
`imu`, `fix_conflict`, `harness_latch`, `move_timeout`, `executor_refused`, the preflight latch and car checks and
a halt file appearing mid-run have their own tests. Still without a test: `guard_blocked` and `car_restart` raised
inside a scan, `usd_cap` between two episodes, and everything in `car_batch.sh`.

## Before the first real batch (attended)

1. Stand test and floor check pass; `record-pass`.
2. The **measured** world file (tag centres as mounted), the chosen range limit, the start poses; one dry run
   with exactly those arguments.
3. Put the car at least 0.7 m from every edge of the driving area and tape its pose. Choose a first start pose
   at least 0.3 m away, so the encoder scale is checked in the first transit.
4. The first one or two episodes attended (plan §3.6): watch the first circle, the transit and one guard
   refusal; tape the first start pose against `start_pose_world` in the manifest.
5. `--min-forward-speed` from the floor check's peak speeds, if a fading pack should halt early.
6. Run the wrapper inside tmux.

## Open items

- Nothing here has run on the car. Real resection accuracy is unknown (no real frame with a tag existed when this
  was written); `fix_sigma_*` are assumptions; the dry runs use nominal tag positions.
- A full circle costs 12 moves (about half a minute on the car); three are made per episode.
- `car_batch.sh` was syntax-checked only: it has not started a recorder or a container.
- The guard's remaining hole is the one named above: a badly surveyed tag seen alone. A car placed with a pose
  the tape got wrong by less than the first circle's gate (0.5 m, 30 degrees) turns its first circle on that pose:
  hence the 0.7 m of room asked for at the start.
- The limit on distance driven without a tag fix makes `no_fix` halts more likely where tags are sparse (table
  above); with the measured layout, check the dry run before choosing the range limit and the start poses.
