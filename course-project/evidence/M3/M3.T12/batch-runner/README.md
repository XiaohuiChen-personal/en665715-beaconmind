# Unattended batch runner for real-car episodes (plan §3.6 "Unattended batches"; tasks M3.T12 and M3.T18), 2026-11-18

Status: **code and tests only, verified on the simulated car in the simulated room. Nothing was published on the
real car's ROS graph; no batch has run on the car.** On 2026-11-24 the wrapper ran on the Spark for the first time
(simulated car; the real-car path to its refusal), a check of the surveyed tags against each other closed the open
review finding 3, and the fix sigma can come from the tag pilot (sections marked 2026-11-24). The stand test and the floor check
(`../../M3.T6/README.md` section 5) stay attended and must pass first: the runner refuses a real batch without a
recorded pass marker (below). The folder is M3.T12's because that task is the real B2 episodes; the same runner
serves the live-model episodes of M3.T18 (`--policy <model key>`).

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote the runner, the resection, the tests and this
note. Xiaohui Chen approved unattended batches on 2026-11-18 (plan README §3.6) and runs the attended tests.
AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: ran the wrapper on the Spark and fixed it, added the tag check
(`tag_survey`), `--detector-noise`, `--dv` and `tools/real_dv.py`, the tests named below, the 3.0 m dry runs and the
first batch's commands; edited this note.
AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: diagnosed the false `odometry_scale` halt of the first real
practice batch (`practice-01b/`), added the range check along straight moves and the episode scale check, weighted the
per-step statistic by the fixes' noise, ran the first batch's rehearsal
(`rehearsal-2026-11-25.md`, `rehearse_drift.py`) and filled in the record-pass command; edited this note.

## Files (under `course-project/`)

| File | What |
| --- | --- |
| `beaconmind/src/beaconmind/car/resection.py` (new) | pose from the surveyed tags: `resect` (two tags or more, repeated ids handled), `position_fix` (one tag and the tracked heading) |
| `beaconmind/src/beaconmind/car/batch.py` (new) | `PoseTracker`, `MoveGuard`, `Monitor` (the halts), `BatchEnv` (the harness's environment), `BatchRunner`, `dry_rig`, the pass marker |
| `tools/car_batch.py` (new) | `run`, `record-pass`, `clear-halt`, `status` |
| `tools/car_batch.sh` (new) | Spark host: starts the R2 recorder for the whole batch, runs the tool in a `beaconmind-ros` container (`bm-batch-<label>`), stops the recorder |
| `beaconmind/tests/test_car_batch.py` (new) | 114 tests (91 on 2026-11-18) |
| `beaconmind/tests/test_car_batch_wrapper.py` (2026-11-24) | 11 tests: `car_batch.sh` and `record_session.sh status` under bash with stand-ins for docker, tmux and the recorder |
| `tools/record_session.sh` (the recorder, M3.T27; changed 2026-11-24) | `status`, and so `start`, no longer exits 1 when the start checks found no car (see "First execution"); the clock line is for the one filmed demo run only |
| `beaconmind/src/beaconmind/dv_real.py`, `tools/real_dv.py` (2026-11-24) | `configs/dv-real.json` and the `--dv` switch ("Design values for real runs") |
| `beaconmind/tests/test_dv_real.py` (2026-11-24) | 9 tests |
| `tools/closed_loop_run.py`, `closed_loop_run.sh`, `room_rehearsal.py` (changed 2026-11-24) | `--dv <file>` |
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
6. **Tags** (2026-11-24): every full circle compares each tag with the others; a tag that keeps disagreeing halts the
   batch (`tag_survey`), and only tags compared closely enough steer a step's fix ("The check of the surveyed tags").
7. **Outputs** in the batch folder: `manifest.json` (`bm.car_batch/1`; `tag_check` holds each tag's comparison),
   `summary.txt`, `HALT.LATCH` when halted,
   `spend.jsonl`, and per episode `episodes/<id>/`: the harness's `seed_<n>.jsonl` and `.moves.jsonl`,
   `truth.jsonl` (ground truth per step), `backend/steps.jsonl`, `pre/` and `post/` (scans and transit). In the
   recorder's session: every frame (`frames_backend/`), the move logs (`moves/`), `batch_markers.jsonl` with each
   episode's start and end.
8. **Resume:** after an operator has looked at the car and cleared the halt, the same command with the car's new
   taped pose, or `--initial-pose last` when nobody moved the car (the pose the batch last tracked). Finished
   episodes are skipped. An unfinished episode is never replayed; it runs again as a new attempt (`ep02-a2`); one
   left `running` by a dead process becomes `abandoned`. Step, time and spend caps count the whole batch across its
   runs.

World file, start poses and range limit are parameters (`--world`, `--scenarios` / `--scenario-ids` / `--start`,
`--max-range`): the tag configuration is still being chosen.

## The pass marker

`course-project/data/real/ATTENDED_PASS.json` (git-ignored, on the Spark), written only by

`bash course-project/tools/car_batch.sh - record-pass --operator <name> --stand-session <session> --floor-session <session> --world <world file>`

which a person runs after the attended stand test and floor check have passed. It requires two **different**
recorded sessions under `data/real/`, the stand session with at least 5 and the floor session with at least 10 move
logs that ended `done`. It stores hashes of `configs/car.json`, `configs/dv.json`, the twelve modules of the car
package and the world file named with `--world` (the surveyed one). A real batch is refused when the marker is
missing, older than 7 days (or dated in the future), when its `--world` is not that file byte for byte, or any of
those files differs today (the comparison runs over today's file list, not over what the marker chooses to
contain). What it cannot know: whether the tests' pass criteria were met. It records that a named person said so
and which sessions show it. The firmware on the car is not in it (checked at the start through the telemetry
layout and the drive map).

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
  `sigma_theta_deg`, `steps_since_fix`): odometry between fixes, each fix blended in by inverse variance. A fix
  resting on exactly the tags of the fix before it moves the pose but does not shrink the sigma (it repeats that
  tag's survey and range-scale error), and the position sigma never goes below 0.05 m, so the guard's margin is
  never under 0.25 m.

What the stated sigma covers: noise and geometry, with a per-tag noise of `fix_sigma_a_m` + `fix_sigma_b` × range:
by default the **assumed** 0.03 m + 0.04 × range; with `--detector-noise course-project/configs/detector_noise.json`
(2026-11-24) the tag pilot's measured model (`bm.detector_noise/1`, written by `tools/tag_pilot.py analyze --out`),
mapped by `batch.fix_sigma_from_detector_noise`: along the line of sight |range bias| + range sigma, across it the
range times |bearing bias| + bearing sigma at `--max-range`, and the isotropic bound a + hypot(b_along, b_across) × r
of the two (the detector does not correct the bias, so it counts as error). The manifest's
`params.fix_sigma_source` says which was used (file, its sha256, the pilot's log and date, the numbers), the summary
prints it, and a different source is a different batch configuration. A `--max-range` beyond the pilot's reliable
range is printed and recorded as a WARNING. `configs/dv.json` (the frozen study's values) is neither read for this
nor changed. What the sigma does not cover: a common range-scale error of the camera and errors in the surveyed tag
positions. The plan's three tape readings (first start, last end, one spot check) bound those; a wrong tag position
is also looked for by the tag check below. The agent sees none of this.

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
behind the odometry by more than 12 % of the distance driven halt the batch). What got through until 2026-11-24:
one tag surveyed 0.3 m wrong, seen alone, pulled the tracked pose up to 0.33 m while the stated sigma stayed near
0.1 m; in the reviewer's probe the simulated footprint came within 4 cm of the edge of the driving area. That is
now closed by the tag check (next section). **The tag centres in the world file must still be measured, not
nominal:** the check halts on a wrong one, it does not correct it.

## Design values for real runs: `--dv` (2026-11-24)

Xiaohui approved a separate design-values file for real runs ("I am OK with a separate design-values file").
`tools/real_dv.py` writes `configs/dv-real.json` (schema `bm.dv/1`, the frozen file's keys) after the pilot: the frozen
`configs/dv.json` with exactly four fields changed, each with its own `source`, `evidence` (the noise file and its
sha12) and `updated`, and a `$comment` listing them with the sha12 of both files. It refuses to write if anything
else would differ, refuses the frozen file as its output, and refuses a range limit beyond the range the pilot
found reliable unless `--beyond-pilot-range` (Xiaohui's explicit decision). The mapping (`beaconmind/dv_real.py`):
range sigma = (|range bias a| + sigma a) + (|range bias b| + sigma b) r, since the detector does not correct the
bias; bearing sigma (one value for every range in the agent's model) = |bearing bias| + the pilot's bearing sigma at
the range limit; rounded up, never under 0.005 m or 0.1 degrees. **Not changed, and why:** `well_cond_sigma_*` and
`reloc_sigma_*` are acceptance thresholds on a fix's computed uncertainty, a requirement on the result, not a model
of the camera; the room rehearsal showed that with the frozen sigmas almost no two-tag fix passes them, so honest
(measured) sigmas are what should change, and scaling the thresholds with them would cancel that. The association
gates (`gate_*`) also cover pose drift and stay.

`--dv <file>` in `tools/car_batch.py`, `tools/closed_loop_run.py` (and its `.sh`) and `tools/room_rehearsal.py one`
(also `run_cell(dv=<file>)`): the default stays the frozen file. The frozen modules (`geometry.py`, `dv.py`,
`kinsim_lite.py`, ...) read their values through `beaconmind.dv.load_dv()`, which caches the parsed default file;
`dv_real.use_dv` puts the chosen file's values there for the run and restores exactly what was there afterwards (also
after an exception, also inside the rehearsal's own `dv_override`); no frozen file is edited and
`prereg_freeze.py --verify` stays OK. A `--dv` file is refused unless it is `bm.dv/1` with the frozen keys and differs
only in the four fields. Records: `run.json`'s `dv_file` (file, sha12, canonical sha12, the differing values; a run
on another file is another configuration, a run on the frozen file keeps its old configuration tag), the batch
manifest's `params.dv_file` and summary line, the rehearsal's output. **One measurement for both sigmas** (the lead's
decision, 2026-11-25, under Xiaohui's software delegation): a real batch runs with `--detector-noise
course-project/configs/detector_noise.json` and with a `--dv` that `real_dv.py` made from that same file. The dv
file's three sigma entries carry the noise file's sha256 in their `evidence`; the batch compares it with the sha256
of `--detector-noise`, records the result in `params.sigma_sources` ("agree: ... sha256 ...", or what differs) and
the summary, and refuses a real batch without either argument, with the frozen `dv.json`, or with files that do not
agree (listed with the pass marker's refusals, before anything is sent). The `--dv` file's range limit must also
equal `--max-range`. A dry run defaults to the frozen file and is refused only when two given files disagree. Tests:
`beaconmind/tests/test_dv_real.py` (a fixture noise file; `configs/dv-real.json` is not written until the pilot).

## The check of the surveyed tags against each other (2026-11-24; review finding 3)

The residual risk once the centres are measured is a wrong number on the mounting sheet (a misread or a slip of
the pen). Nothing about the car tells a tag that is 0.3 m off from one that is right, except the other tags.

- **Leave one out** (`resection.check_tags`, in every fit of four tags or more: in practice every full circle, ~15
  tags at 3.0 m in the 20-tag room). Each tag is compared with where the other tags put it; its limit is
  max(0.15 m, 4 sigma), sigma from its range (the fix sigma) and the fit's uncertainty at it. While the worst tag
  exceeds its limit and more than three would remain, it is set aside and the rest compared again among themselves
  (so one bad tag does not smear its error onto the good ones). Repeated ids (0, 2, 3 are on two tags each) are
  compared by tag (`T02`, `T05`), after the assignment the fit chose; a check whose assignment is ambiguous is not
  made.
- **Adding up** (`batch.TagCheck`): each comparison is a vector with weight 1/sigma^2. A tag whose weighted mean is
  farther from its survey than max(0.15 m, 4 sigma_mean) halts the batch: **`tag_survey`** (safety: the project
  latch too), naming the tag, its id, its surveyed centre, where the other tags put it and over how many
  comparisons. One circle names a tag 0.5 m off (assumed noise) or 0.3 m off (noise like the simulated camera's);
  with the assumed noise a 0.3 m error at 1.7 m needs two circles. Under 0.15 m nothing is named: that is inside
  the guard's 0.25 m and below what measurement on the wall should miss.
- **Trust before use:** a step's fix (two tags, or one tag and the tracked heading) uses only tags whose mean is
  within max(0.15 m, 3 sigma_mean) of their survey with that bound at most 0.30 m. So a tag more than 0.30 m off is
  never trusted, and a tag not yet compared, or compared only from far, steers nothing. The disagreement test and
  the `fix_conflict` count still use every tag, exactly as before: the trust rule only decides what moves the pose.
  Full circles use every tag (they are where tags get compared). The evidence is per process: a resumed batch
  compares again from its first circle. The manifest's `tag_check` lists every tag's mean, sigma, limits and verdict.

What it costs and what it buys, all on the simulated car (`tag-check-probe.txt`, `dry-runs-2026-11-24.txt`):

- **The hole, made direct** (`test_a_tag_surveyed_wrongly_by_d_cannot_pull_the_car_toward_its_wall`): T06 surveyed
  d into the room, seen alone, the car driving FORWARD_10 at the window wall while the guard allows. Before: the
  tracked pose lagged the truth by about two thirds of d and the true footprint came to 0.18 m (d = 0.3) and 0.08 m
  (d = 0.5) of the edge while the guard believed it kept 0.25 m. Now: the circle halts `tag_survey` naming T06
  (0.3 and 0.5 m) before any forward move; without a circle T06 is unchecked and steers nothing (tracked within
  3 cm of the truth); 0.1 m is not named and keeps more than the 0.25 m.
- **Whole batches with one tag moved** (every tag of the 20, 0.1 / 0.3 / 0.5 m along ±x and ±y, B2, S1, S3, S4,
  3.0 m, assumed noise; 80 runs per size): with the check every 0.3 m and 0.5 m case (160 of 160) halted
  `tag_survey` naming the moved tag, the tracked pose within 0.07 m of the truth until then; 0.1 m: 78 complete, 2
  `odometry_scale`, none named. Before: 0.3 m gave 66 `no_fix`, 5 `odometry_scale` and 9 complete batches with the
  tracked pose up to 0.17 m off (0.28 m at 0.5 m). No contact in any run (`tag-check-probe.txt`).
- **Cost in the dry runs:** 20-tag room at 3.0 m: 4 of 4 batches complete with and without the check; no clean tag
  came near its limit (largest mean/limit 0.06 with the assumed noise, 0.10 with pilot-like noise, 0.14 anywhere in
  the grid). At 2.5 m one batch of four halts `no_fix` in S4 (the corner with fewest tags) where it completed
  before: until a tag is compared it steers nothing. Clean runs of the probe: 7 of 8 complete (one `no_fix` in S4)
  against 8 of 8. In the 12-tag layout at 2.0 m few circles hold four tags, so few tags can be
  compared at all: there the rule turns into `no_fix` halts (two older tests about resume and the odometer bias
  run with `tag_trust=False` for that reason, said in each).

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
| `odometry_scale` | the ranges to the tags seen before and after each straight move change by another distance than the odometry's (median over the moves so far off by more than 12 %, 15 % on the first move; 2026-11-25, after a false halt of the first real practice batch: `practice-01b/`, `rehearsal-2026-11-25.md`); the transit's two lengths differ; the episode's two lengths (start circle to end circle, odometry alone against the circles' fixes) differ; or the per-step fixes put the scale off by more than 12 % **and** three standard errors (weighted by each fix's noise) | S | `test_the_transit_checks_the_encoder_scale_before_any_episode`, `test_a_wrong_encoder_scale_halts_before_the_car_reaches_a_wall` (unchanged since review finding 8), `test_the_ranges_catch_a_wrong_encoder_scale_either_way_in_both_rooms`, `test_the_practice_batch_ranges_say_its_odometer_was_right`, `test_the_range_of_a_tag_along_a_straight_move_measures_the_scale`, `test_noisy_fixes_after_short_legs_do_not_call_a_correct_odometer_biased` |
| `pose_uncertain` | tracked position sigma above 0.25 m, or a tracked pose that is not a number | S | `test_halt_pose_too_uncertain` |
| `detector` | a detection whose range or bearing is not a number | S | `test_detections_that_are_not_numbers_never_reach_the_pose` |
| `outside_drive_area` | the tracked pose is outside the free area | S | `test_halt_pose_outside_the_driving_area` |
| `guard_blocked` | a scan or transit move was blocked; no room for the first circle | S | `test_halt_no_room_for_the_first_scan`, `test_the_first_circle_needs_room_for_a_wrong_tape` |
| `start_pose` | the start pose not reached within tolerance after the attempts | S | `test_halt_start_pose_not_reached` |
| `drive_map` | the car does not report the drive map that was set | S | `test_halt_drive_map_does_not_take` |
| `recorder` | the recorder session is no longer active, or has written nothing for 2 minutes (rule R2) | S | `test_halt_recorder_stops`, `test_a_recorder_that_stopped_writing_is_noticed` |
| `episode_wall_clock` | an episode (scans included) runs past `--episode-minutes` (60) | S | `test_halt_episode_wall_clock` |
| `batch_wall_clock`, `batch_steps` | the batch, over all its runs, passes `--batch-hours` (6) or `--batch-steps` (2,500 moves) | — | `test_halt_batch_wall_clock_and_step_cap`, `test_the_move_cap_counts_the_whole_batch_not_one_run`, `test_the_wall_clock_cap_counts_the_whole_batch` |
| `tag_survey` (2026-11-24) | the other tags keep putting one tag farther from its surveyed centre than its limit ("The check of the surveyed tags") | S | `test_a_batch_with_one_tag_surveyed_wrongly_by_d`, `test_a_tag_surveyed_wrongly_by_d_cannot_pull_the_car_toward_its_wall`, `test_the_circle_names_the_tag_surveyed_wrongly` |
| `usd_cap` | spend reached `--cap-usd` (no request is sent after it; spend is appended to `spend.jsonl` as it happens and counted again on a rerun) | — | `test_halt_usd_cap`; between two episodes, and a rerun at the cap: `test_usd_cap_between_two_episodes_is_the_check_before_the_next_episode` |
| `harness_latch` | the harness latched the episode (two error observations, contacts) | S | `test_halt_harness_latch` |
| `interrupted` | Ctrl+C, SIGTERM, SIGHUP (only the first counts; later ones are ignored while the car stops and the halt is written, 2026-11-24) | — | `test_an_interrupted_episode_is_halted_in_the_manifest`, `test_terminate_and_hangup_end_like_an_interrupt`, `test_signals_in_quick_succession_still_leave_one_halt_record`; through docker on the Spark: "First execution" |
| `harness_error`, `error` | another harness error; any exception; a manifest that cannot be written; an earlier run that died without a record | — / S | `test_halt_on_an_unexpected_error`, `test_a_run_that_died_without_a_record_needs_an_operator`, `test_a_halt_that_cannot_be_written_sets_the_project_latch` |

`test_a_fault_while_the_agent_thinks_stops_the_next_move` runs seven of these faults while a (simulated) model
thinks for 20 s between two steps: no move is sent after the fault appears.

**Two halts at once** (2026-11-24, `test_two_faults_inside_one_scan_keep_the_first_cause`): the first cause found is
the batch's halt in the result, the manifest, the summary, `HALT.LATCH` and the project latch; a second one in the
same sensing or later in the same circle does not write over it, and no move follows. (After a non-safety halt a
later safety condition therefore does not set the project latch; the batch is halted and refuses to rerun until
cleared either way.)

**A halt is recorded as a halt, not as the spend cap** (commit `353d49f`): when the agent wrapper refuses a request
because the batch has just halted, the harness reports its own "budget cap reached"; the episode entry then says
`ended_by: halt` with the real cause in `detail`, and the batch's halt keeps the real code (`supply_low` in
`test_a_request_refused_by_the_wrapper_is_recorded_as_the_halt_not_as_the_spend_cap`), not `usd_cap`.

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

**2026-11-24: the 20-tag world and 3.0 m** (`dry-runs-2026-11-24.txt`). The same command, seeds and settings, with
`--world course-project/configs/arenas/real-room-plus8-160mm-nominal.json` (C20, nominal centres) and also at 3.0 m
in the 12-tag world. First on the code of 2026-11-18 (commit `65173fe`; it reproduces the table above move for
move), then on today's code with the tag check:

| World | Range limit | Code of 2026-11-18: batches complete, episodes done, halts | With the tag check (2026-11-24) |
| --- | --- | --- | --- |
| 12 tags | 3.0 m | 3 of 4, 17 of 20, one `no_fix` (S3) | 3 of 4, 17 of 20, one `no_fix` (S3) |
| 20 tags | 2.0 m | 0 of 4, 12 of 20, four `no_fix` (S3, S4, S4, S5) | 1 of 4, 13 of 20, three `no_fix` (S3, S4, S4) |
| 20 tags | 2.5 m | 4 of 4, 20 of 20, none | 3 of 4, 18 of 20, one `no_fix` (S4) |
| 20 tags | **3.0 m** | **4 of 4, 20 of 20, none** | **4 of 4, 20 of 20, none** |

At 3.0 m with 20 tags (today's code) every episode reached its start pose (miss 0.01 to 0.14 m), the transit's
odometer check read 0.994 to 1.003, no move of B2's was refused by the guard, B2's final pose error against the
batch's pose was 0.00 to 0.04 m, all 20 episodes ended by B2's DONE (44 to 148 steps), all 20 tags were trusted by
the end of each batch, and no tag came near its halt limit (largest mean/limit 0.08 over all 24 batches; no
`tag_survey`). This supports the 3.0 m limit with the 20-tag layout, pending the tag pilot. At 2.5 m the check costs
one batch of four (S4, the corner with fewest tags: until a tag is compared it steers nothing); 2.0 m is not usable
with either code. In the 12-tag world 3.0 m changes little against 2.5 m (one S3 halt in four).

## Tests

- 2026-11-25, Mac, after the same-file rule: the whole suite **695 passed, 10 skipped** (demo-video tests included), `tests/test_dv_real.py` 9 of them. Earlier, commit `f1897e9`: `tests/test_dv_real.py` **8 passed**; the suite without the demo-video tests
  **651 passed, 10 skipped** (with them, run while the video agent was editing its files, 2 of theirs failed; run
  alone a minute later, theirs: 47 passed); `prereg_freeze.py --verify` OK.
- 2026-11-24, Mac (Python 3.13), `pytest-mac.txt`: `tests/test_car_batch.py` **114 passed**, `tests/test_car_batch_wrapper.py` **11 passed**; whole suite **643 passed, 10 skipped** (without the demo-video agent's three untracked test files, work in progress in the same tree); `prereg_freeze.py --verify` OK (29 files, 30 logs).
- 2026-11-25, container on the Spark (Python 3.10.12, `--network none`, ROS_DOMAIN_ID 42), commit `9cd1624` (a
  scratch checkout: the main clone is reserved for the hands-on sessions), `pytest-container.txt`: the batch file,
  the wrapper file, `test_dv_real.py` and the five car test files **317 passed, 1 skipped** (`f1897e9`: 316;
  `05f64c4`, without the dv tests: 308).
  (On `2cd3415` the new quick-signals test failed there: Python 3.10 printed "Signal 2 ignored due to race
  condition" for a signal already pending when the handler became SIG_IGN; the later signals now go to a no-op
  Python handler instead.)
- 2026-11-18: Mac `tests/test_car_batch.py` 91 passed, whole suite 605 passed, 10 skipped; container 286 passed,
  1 skipped.

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
| 3 | one mis-surveyed tag made the tracker confidently wrong; the footprint reached the wall | **closed 2026-11-24** by the tag check (halt `tag_survey`, trust before use; "The check of the surveyed tags"); before that reduced, not closed: no sigma shrink on a repeated tag set, sigma floor 0.05 m (so the margin is never under 0.25 m), fixes that disagree are refused, full-circle residual limit 0.08 m, wall margin 0.15 m. Reviewer's probe on the final code: no run reaches the edge; the smallest true clearance over all its tag cases is 4 cm (a tag 0.3 m wrong, tracked pose 0.33 m off). See "The guard" for what remains | `test_a_tag_surveyed_wrongly_halts_before_the_car_reaches_a_wall`, `test_repeated_fixes_from_the_same_tag_do_not_shrink_the_uncertainty`, `test_guard_margin_has_a_floor_that_no_fix_can_lower`, `test_a_fix_that_disagrees_with_the_tracked_pose_is_not_blended_in` |
| 4 | a halt that could not be written was lost; `_save` raised out of `run()`; the rerun drove | fixed: project latch on a failed halt write; manifest write errors halt; a manifest left `running` refuses and writes the halt | `test_a_halt_that_cannot_be_written_sets_the_project_latch`, `test_a_run_that_died_without_a_record_needs_an_operator` |
| 5 | health was judged on the previous sensing, so one more move ran | fixed: fresh car state and a camera probe before every move | `test_a_fault_while_the_agent_thinks_stops_the_next_move` (7 faults) |
| 6 | SIGTERM and SIGHUP left no halt record | fixed: both end like Ctrl+C; the wrapper `exec`s Python and says to run under tmux | `test_sigterm_during_a_batch_leaves_a_halt_record` (a real process, SIGTERM mid-batch; not under docker), `test_terminate_and_hangup_end_like_an_interrupt` |
| 7 | caps were per process | fixed: moves and wall clock count over all runs of the batch | `test_the_move_cap_counts_the_whole_batch_not_one_run`, `test_the_wall_clock_cap_counts_the_whole_batch` |
| 8 | an odometer reading 25 % short was not covered by sigma; wall reached | fixed three ways: no straight move takes the distance driven since the last tag fix past 0.75 m; the transit of 0.3 m or more between two full-circle fixes is measured by odometry and by the tags before any episode; fixes that keep landing ahead of the odometry halt. The reviewer's probe now: smallest true clearance +0.885 m, no contact | `test_no_straight_move_takes_the_car_far_from_its_last_tag_fix`, `test_the_transit_checks_the_encoder_scale_before_any_episode`, `test_a_wrong_encoder_scale_halts_before_the_car_reaches_a_wall` |
| 9 | one paid request after a halt (the harness asked the agent once more before it ended the episode) | fixed from this side: the agent is wrapped (`HaltAwareDriver`); before every request the latch, the clocks and the car are checked, and once halted no request is sent. (The harness as it stands today also ends the episode at its latch check before asking.) | `test_no_paid_request_is_sent_after_a_halt`, `test_the_driver_wrapper_sends_no_request_once_halted` |
| 10 | the pass marker could be satisfied by one arbitrary session; the fingerprint compared the marker's own keys; few files hashed | fixed: two different sessions with enough `done` moves; today's file list; `car.json`, `dv.json`, the whole car package and the world file. Not in it: the firmware (not a file here) | `test_pass_marker`, `test_pass_marker_is_for_one_world_file` |
| 11 | obstacles were never checked | fixed | `test_obstacles_count_even_without_a_separate_driving_area` |
| 12 | after Ctrl+C the episode stayed `running` | fixed | `test_an_interrupted_episode_is_halted_in_the_manifest` |
| 13 | a NaN range gave a NaN pose | fixed: such detections never reach a fix, and one halts the batch (`detector`) | `test_detections_that_are_not_numbers_never_reach_the_pose` |
| 14 | a crashed recorder left `.active` behind | fixed: the wrapper checks the recorder's tmux session; the batch halts when the session's logs stop changing for 2 minutes | `test_a_recorder_that_stopped_writing_is_noticed`; the wrapper's check: `test_an_active_session_is_used_not_stopped_unless_it_polls_the_camera` (2026-11-24) |
| 15 | `supply_low` is the Pico's supply; fading motor batteries only show as stall/timeout | documented, not fixable in software: the car has no motor-battery signal ("Battery" above). A supply reading of 0 or none does not halt (the simulated and real firmware always send one) | — |
| 16 | wrapper: `--batch-hours=7` not parsed; `--out` outside the repository vanished with the container | fixed in the wrapper; run on the Spark 2026-11-24 | `test_refusals_before_anything_starts` |
| 17 | wall-clock caps are checked only when the harness asks for a step; a hung model call overruns them | documented limit: the caps are checked before every request and every move, not during a request. The car is at rest meanwhile, and the provider's own request timeout (900 s, `tools/closed_loop_run.py`) ends the call; a cap can therefore be overrun by at most one request | — |
| 18 | telemetry lost between moves was called `executor_refused` | fixed | `test_telemetry_stopping_between_moves_is_named_and_sends_no_move` |

Tests the review called weak: the halt helper now counts commands from the moment of the halt and watches the
simulated car's true footprint in every batch test; the restart, link-lost and slow-car tests assert one code, the
manifest and the rerun; resume is tested through the tool with a new process and `last`; the faults are also
planted while the car stands (the agent thinking). Halt paths that had no test and now have one: `imu`,
`fix_conflict`, `harness_latch`, `move_timeout`, `executor_refused`, `interrupted`, the preflight latch and car
checks, a halt file appearing mid-run, `guard_blocked` and a car restart inside a scan, the first circle failing
twice, `usd_cap` between two episodes, an exception from the car link inside an episode, the unwritable halt, and
SIGTERM on a real process. The tests were written with the fixes; the old code's failures are the reviewer's
reproductions (its probe scripts), which were re-run on the final code. Still without a test: `harness_error`
other than the two non-halting kinds, and everything in `car_batch.sh` (syntax-checked only).

## First execution of `car_batch.sh` on the Spark (2026-11-24)

The car powered off, the micro-ROS agent stopped, the camera off; clone at `65173fe`. Logs in
`wrapper-spark-2026-11-24.txt`. Nothing was published on a `/pico/*` topic; no pass marker exists or was written.

- **A simulated batch is a `--dry-run` through the wrapper.** The wrapper starts no recorder for it (by design:
  `--dry-run` or a ROS domain other than 0), and runs the batch in a one-off `beaconmind-ros` container. The first
  run (`dry-wrapper-20261124`, 2 episodes S1, S2, 30 steps, 3.0 m, 20 tags) worked as written: complete, 168 moves,
  the folder in `data/batches/` owned by the user, the container gone. A batch that drives a simulated car node over
  ROS (`BM_ROS_DOMAIN_ID=42`, `car.sh sim-car`) is refused by `car_batch.py` for want of the pass marker and a
  recorder session, as the refusal is meant to; it was not worked around. So the ROS path of a batch is untested
  until the real car.
- **Stopping it** (dry runs through docker, 30 episodes each): Ctrl+C in the tmux window, closing the window
  (SIGHUP), `docker stop`, and Ctrl+C twice 50 ms apart all ended with `halted: interrupted`, `HALT.LATCH` written,
  the running episode `halted`, no container left. A `kill -TERM` of the wrapper's own process did **not** stop the
  batch (it finished two more episodes until the container was stopped): the wrapper waits for its container. Now
  said in the wrapper; the container is named `bm-batch-<label>` so `docker stop bm-batch-<label>` is the way, and a
  second run of the same batch cannot start beside the first.
- **The real-car path, car off — a bug found.** `car_batch.sh real-refusal-a run ...` without `--dry-run`: the
  recorder started (`car: NOT FOUND`, `camera: NOT FOUND`, `micro-ROS agent: NOT RUNNING`; no ping windows, since
  there was nothing to ping) but `record_session.sh start` exited 1, because its closing `status` ended with `tail
  ping_car.txt | sed` under `pipefail` and there was no ping log. The wrapper took that for "the recorder did not
  start", exited 2 and **left the session recording** (`.active`, tmux `bm-rec`, container `bm-rec-bag`, a 7-hour
  watchdog). It was stopped by hand at once (`record_session.sh stop`). Fixed twice: `status` returns 0 without a
  ping log; the wrapper stops any session that is marked active after its start call, whatever the exit status.
- **Hardened while there:** a real run is refused (nothing sent, the session it started stopped) when the
  recorder's start checks say `car: NOT FOUND`, `camera: NOT FOUND` or `micro-ROS agent: NOT RUNNING` (the batch
  could not run, and the session would hold no ping log of the link gaps, rule R2), or when an already active session
  polls the camera (the batch must be its only client); the wrapper returns the batch's own exit status after
  Ctrl+C (it returned 130); `car_batch.py` ignores every stop signal after the first, so a second Ctrl+C cannot
  break off a move's stop or a half-written halt record. All of it in `test_car_batch_wrapper.py` (bash with
  stand-ins; against the scripts of 2026-11-18 all 11 fail on the Mac).
- **After the fixes, on the Spark** (clone at `2cd3415`): the same real-car-path run is refused at the recorder's
  checks, naming the agent, the camera and the car, and the session it started is stopped (`.active` gone, no
  `bm-rec`, no `bm-rec-bag`), exit 2; on ROS domain 42 the batch itself refuses (no pass marker, no recorder
  session), exit 2; Ctrl+C on a dry run in tmux gives exit 3 (`halted: interrupted`); a second run of a running
  label is refused by docker (exit 125) and leaves the first alone; `docker stop bm-batch-<label>` gives exit 3
  (`halted: interrupted`).

## Before the first real batch (attended)

1. Stand test and floor check pass (`../../M3.T6/README.md` section 5).
2. The tags mounted, their centres measured and written into
   `evidence/M3/M3.T10/layout-2/mounting.md` (last column); the tag pilot analysed
   (`tools/tag_pilot.py analyze ... --out course-project/configs/detector_noise.json`); Xiaohui's range limit decided
   (3.0 m, or 2.5 m if the pilot does not confirm it); `configs/dv-real.json` written (step a2); all committed and
   pulled on the Spark.
3. Put the car at least **0.85 m** from every edge of the driving area (the first circle needs 0.83 m: sweep
   0.178 + margin 0.15 + the 0.5 m the tape may be wrong; README said 0.7 m before 2026-11-24) and tape its pose.
   Choose a first start pose at least 0.3 m away, so the encoder scale is checked in the first transit.
4. The first one or two episodes attended (plan §3.6): watch the first circle, the transit and one guard
   refusal; tape the first start pose against `start_pose_world` in the manifest.
5. `--min-forward-speed` from the floor check's peak speeds, if a fading pack should halt early.
6. Run the wrapper inside tmux.

**The commands, ready to paste** (Spark, `cd ~/Projects/en665715-beaconmind`). Only the world file changes after
the measurements: `real-room.json` is what step a writes. Fill in the two session names, the date, the measured
pose, and the label if this is not the first batch. No phone video is needed for a batch (rule R2 since
2026-11-24: only the one run filmed for the demo has one; the recorder records every batch episode).

```bash
# a. the measured world (Mac or Spark; then commit it, push, git pull --ff-only on the other)
python3 course-project/tools/room_world.py --variant plus8 \
    --measured-md course-project/evidence/M3/M3.T10/layout-2/mounting.md \
    --measured-by "Xiaohui Chen" --date <YYYY-MM-DD> --instrument "tape measure" --error-cm 0.5 \
    --out course-project/configs/arenas/real-room.json

# a2. the real-run design values: the frozen dv.json with the pilot's noise model and the range limit (3.0 or 2.5,
#     Xiaohui's decision after the pilot; the same number goes into --max-range below)
python3 course-project/tools/real_dv.py --noise course-project/configs/detector_noise.json --reject-range 3.0 \
    --evidence course-project/evidence/M1/M1.T8 --out course-project/configs/dv-real.json

# b. the pass marker, after the stand test and the floor check (their recorder session folders under data/real/;
#    filled in 2026-11-25: ../../M3.T6/stand-test.md, ../../M3.T6/floor-check.md). Run it again after any change to
#    car.json, dv.json, the car package's modules or the world file: the marker fingerprints them
bash course-project/tools/car_batch.sh - record-pass --operator "Xiaohui Chen" \
    --stand-session 20261125-025313-stand-test --floor-session 20261125-030214-floor-check \
    --world course-project/configs/arenas/real-room.json

# c. the dry run with exactly the real arguments (simulated car, the same container; no recorder, no car)
bash course-project/tools/car_batch.sh b2-real-01-dry run \
    --world course-project/configs/arenas/real-room.json \
    --scenarios course-project/configs/arenas/real-room-scenarios.json \
    --initial-pose 2.20,2.00,90 --episodes 10 --policy b2 --max-range 3.0 \
    --detector-noise course-project/configs/detector_noise.json --dv course-project/configs/dv-real.json \
    --dry-run --out course-project/data/batches/b2-real-01-dry
bash course-project/tools/car_batch.sh - status --out course-project/data/batches/b2-real-01-dry

# d. the real batch, inside tmux (tmux new -s bm-batch), the car taped at the --initial-pose
bash course-project/tools/car_batch.sh b2-real-01 run \
    --world course-project/configs/arenas/real-room.json \
    --scenarios course-project/configs/arenas/real-room-scenarios.json \
    --initial-pose 2.20,2.00,90 --episodes 10 --policy b2 --max-range 3.0 \
    --detector-noise course-project/configs/detector_noise.json --dv course-project/configs/dv-real.json

# e. after a halt: look at the car, then
bash course-project/tools/car_batch.sh - clear-halt --out course-project/data/batches/b2-real-01 --operator "Xiaohui Chen"
bash course-project/tools/car.sh clear-latch --operator "Xiaohui Chen"     # if the project latch is set
#    and the same command as d with the car's new taped pose, or --initial-pose last if nobody moved it
```

Notes: `--initial-pose 2.20,2.00,90` is a suggestion (1.5 m or more from every edge, 0.58 m from S1); tape the car
wherever it really stands and use that in c and d alike. `--episodes 10` runs S1 to S5 twice (the scenario file's
"2 B2 episodes" each). `--max-range 3.0` is provisional: if the pilot's reliable range ends below it, the batch
prints a WARNING and the plan says 2.5 m (change it in a2, c and d alike: the batch refuses a `--dv` whose range
limit differs from `--max-range`, and a `--dv` not made from the given `--detector-noise`). Real batches run with the
pilot's file (the lead's decision, 2026-11-25): a real batch refuses to start without `--detector-noise` and a `--dv`
made from that same file; the manifest's `params.sigma_sources` says they agree, with the sha256. If
the demo run Xiaohui films is ever driven through `car_batch.sh`, the phone starts filming
`python3 course-project/tools/session_clock.py <session>` once the wrapper has printed the session name, before the
first circle; no other batch is filmed. Step c with the nominal 20-tag world as a stand-in for `real-room.json`
(2026-11-25, `dry-runs-2026-11-24.txt` section C, without `--detector-noise`, which does not exist yet; through the
wrapper on the Spark, commit `05f64c4`): **complete, 10 of 10 episodes** (S1 to S5 twice), 1,453 moves, start miss
0.02 to 0.20 m, B2's final pose error 0.01 to 0.03 m, 9 episodes ended by B2's DONE and one (S4) ran its 150
steps, all 20 tags compared and trusted, exit 0. On `2cd3415` the same command had halted `no_fix` after 35
moves (from (2.20, 2.00) no tag is near enough for one circle to trust it with the assumed noise, and the second
circle counted its own views); fixed in `05f64c4`.

## Open items

- Nothing here has run on the car. Real resection accuracy is unknown (no real frame with a tag existed when this
  was written); `fix_sigma_*` are assumed until `--detector-noise` is given the pilot's file; the dry runs use
  nominal tag positions.
- A full circle costs 12 moves (about half a minute on the car); three are made per episode.
- `car_batch.sh` has run on the Spark for dry runs and for its refusals; its real-car path past the refusal (the
  recorder running for a whole batch, the recorder-silence halt, stopping the recorder after a real batch) has not
  run, and cannot without the pass marker.
- The tag check names a tag the others disagree with; it cannot name one that is wrong together with the others
  (all tags shifted alike, a wrong room frame: the tape readings at the first start and last end bound that), nor
  a tag never seen with three others in one circle (it then steers no fix: in a tag-poor corner that shows as
  `no_fix` halts). Under 0.15 m nothing is named. A car placed with a pose the tape got wrong by less than the first
  circle's gate (0.5 m, 30 degrees) turns its first circle on that pose: hence the 0.85 m of room asked for.
- The limit on distance driven without a tag fix makes `no_fix` halts more likely where tags are sparse (table
  above); with the measured layout, check the dry run before choosing the range limit and the start poses.
