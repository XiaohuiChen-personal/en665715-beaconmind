# Course Project Context

Last updated: 2026-11-24

**Project name: BeaconMind** (chosen 2026-09-28). "Beacon" for the AprilTags on the walls, "Mind" for
the language model that owns the pose belief, the beacon map and the SLAM decisions. Use this name in
course-facing work (posts, videos, proposal updates); "LLM as SLAM" and "the L2 agent" remain the
technical terms in the design documents. ("TagSLAM" was avoided: it is an existing tag-based SLAM system.)

This is the canonical handoff document for the EN.665.715 course project. Read it before
doing any course-project work and update it at the end of every course-project session.

## 2026-11-24 — presentation timing from Canvas; agents started on the demo video and the batch runner (entry in progress)

**Presentation timing (Canvas, "Presentation Timing", screenshot sent by Xiaohui on 2026-11-24):** slides 5–10
minutes; demo 3–5 minutes as a pre-recorded video; 15 minutes in all per project (20 for a group of two, which does
not apply). This settles the open question "presentation requirements (assumed 15 minutes)" of 2026-11-18: the talk
itself gets at most 10 minutes, not 15. **The deck must be cut:** it has 15 slides written for a 15-minute talk
(`slides/outline.template.md`, private `presentation/`).

**Decisions (Xiaohui, 2026-11-24).** (1) **No page limit for the report:** "Doesn't look like there is a page limit";
the 12-page budget of 2026-11-18 is lifted (`report/PENDING.md` updated). (2) **Real-run DV file approved:** "I am OK
with a separate design-values file". Plan: `configs/dv-real.json` = the frozen `dv.json` with only the three noise
fields (`sigma_range_a_m`, `sigma_range_b_per_m`, `sigma_bearing_deg`) from the tag pilot's `configs/detector_noise.json`
and `reject_range_above_m` set to the range limit Xiaohui confirms after the pilot (3.0 m provisional); written only
after the pilot; a `--dv` argument in `closed_loop_run.py`, `car_batch.py` and `room_rehearsal.py`; the frozen file
and the pre-registered files untouched. Given to the batch agent as an extension of its task 6.

**State checked at the start (about 23:20 CST on the Spark).** Spark clone at `65173fe` (same as the Mac), stale
untracked `report/generated/tab-kinds.tex` only; no container running; GPU free; access point up; `bm-cam-relay` up;
micro-ROS agent stopped (start with `car_net.sh agent-start` before car work); camera not found (car off). Mac tests
606 passed, 10 skipped; `prereg_freeze.py --verify` OK. Dry run of the measured-world path: the 20-tag mounting
sheet (`evidence/M3/M3.T10/layout-2/mounting.md`) with its last column filled with the nominal numbers, through
`tools/room_world.py --variant plus8 --measured-md`, gives 20 tags identical to
`configs/arenas/real-room-plus8-160mm-nominal.json`, so Xiaohui's measured centres go into a world file in one command.

**Agents started (Xiaohui: "spin up subagents to work on demo video and batch runner … in parallel").** Both on
disjoint files, no API spend, nothing that commands the car, no edits to this file, the report or the slides:
- **video** (work list 4.3–4.4; M6.T4, T11, T12, T14, T15 input path): renders the simulation half from the existing
  Opus 5.5 episode of 2026-11-18 (`data/closed-loop/20261118-room-final/claude-opus-5-5/`), built from the experiment
  harness's logs, not ROSA (plan §3.6 cut 4; Claude's recommendation, Xiaohui did not object but has not confirmed);
  the car part's input path, tested on an existing recorder session; a narration script for Xiaohui's voice-over;
  whole video 3:00–5:00 as a hard check, target about 4:00. No ffmpeg on the Mac or the Spark host: a venv with
  `imageio-ffmpeg` or a container, no system-wide install.
- **batch** (M3.T12, plan §3.6 "Unattended batches"): dry run at 3.0 m with the 20-tag world; first real execution of
  `car_batch.sh` on the Spark against the simulated car; README note for `353d49f`; tests for `usd_cap` between
  episodes and two halts in one scan; a guard for a mis-surveyed tag; an argument to take the tag pilot's
  `configs/detector_noise.json` sigmas; paste-ready first-batch commands. Must not start the micro-ROS agent, publish to
  `/pico/*`, or write `ATTENDED_PASS.json`.

**Demo video confirmed (Xiaohui, 2026-11-24):** "build the demo video from the harness logs shall be enough as long as
the video could be shown the robot running in simulator. For the real run, I will record one run." So: no ROSA
runtime (M6.T2, T7, T8 not built); the simulation part animates the car's motion between steps, to scale, labelled as
the kinematic simulator; the car part is built around one filmed real run (expected: the closed-loop Opus demo take).
Passed to the video agent. **Confirmed (Xiaohui):** "We could have other runs perform automatically, as I mentioned
before. But I will only record one run." So the real-car scope is unchanged (≥ 10 B2 episodes and 2–3 closed-loop
Opus episodes, run automatically in batches); **only one run gets a phone video**. Rule R2 is changed to match in
`AGENTS.md` and plan §3.6; every episode still has the recorder's bag, frames, traces and terminal capture. The
report's IV-D R2 sentence still says every folder has a phone video (listed in `report/PENDING.md`).

**Tags mounted (2026-11-25), measured world file written.** Xiaohui: "all nominal except T08 = 350" (T08, ID 2,
window wall, slid from 364 to 350 cm for an outlet: 1 cm below its slide range, its page still 14.4 cm clear of T15's,
the ID 2 copies 2.28 m apart). The mounting sheet's last column is filled (`evidence/M3/M3.T10/layout-2/mounting.md`,
with a note: pages centred on tape marks at the nominal distances, not re-measured, 1 cm per reading).
`configs/arenas/real-room.json` (`real-room-plus8-160mm`, 20 tags, T08 at (3.811, 4.454) m, the other 19 at their
nominal places) by the batch README's command a with `--error-cm 1.0`. Room, world, batch and resection tests: 213
passed, 4 skipped; prereg verify OK. **Room model's handedness confirmed** (Xiaohui, 2026-11-25: facing T03, the entrance
corner is on the right and the angled wall on the left, as the survey frame predicts); the world file is not mirrored. The tag pilot's placement plan is on the Spark (`evidence/M1/M1.T8/placements.csv`, 32 placements, tag ID 23);
Xiaohui is laying part A's floor marks; slanted lines on the entrance-corner side (2.37 m of wall against 0.58 m).

**Tag pilot (M1.T8) DONE with deviations, 2026-11-25 02:08–02:50 CST** (session `20261125-020811-tag-pilot`, recorder
on throughout: 8,533 frames, car and camera pings 0 % loss; motor battery off, car carried). Xiaohui's decisions:
centre line only (0.60–3.00 m), laid by eye from a book corner; no side (B) or incidence (C) placements; tape measure
instead of a ruler; the **camera lens, not the axle, over each tick** (truth = tick + `lens_x_m` 0.12 m, found when A01
read 12 cm long and Xiaohui measured the lens at 0.80 m). Readings: black square 16 × 16 cm, tag centre 21.5 cm above
the carpet (camera agrees: 0.215 m), baseboard 1.5 cm proud of the wall. **Detector fix:** OpenCV's default threshold
windows found the close, low-contrast tag in only 3 of 30 frames; a third pass (63–103 px windows) finds 30 of 30 with
the same range: commit `6fa8b0e` by the batch agent (synthetic reproduction; a later pass only adds quads). Results
(`evidence/M1/M1.T8/fit-output.txt`): every frame detected from 0.785 to 3.135 m (axle to tag), none at 0.735 m; range
bias +0.0049 − 0.0166 r m (1.2–1.7 % short), range sigma 0.0013 + 0.0004 r m; repeats agree within 6 mm; camera yaw
stays 2.5° (part-A bearing bias −0.08°). **Unexplained:** the bearing error runs from +3.3° at 0.79 m to −1.6° at 3.14 m
(fits −2.7° + atan(0.085 m / r)); `car.json` has the lens centred and the tape line meets the wall within about 1 cm of
the tag. So `configs/detector_noise.json` (what the batch and `real_dv.py` read) has bearing sigma 1.86° (RMS of all 15
placements) instead of the pilot's 0.88°, and max incidence 60° (design assumption) instead of the 0° the skipped part C
produced; the raw output and the reasons are in `evidence/M1/M1.T8/` (`noise-model-adjustments.md`). World file rebuilt
with tag centres at 0.215 m. The pilot supports the 3.0 m range limit (Xiaohui decides). Near limit 0.79 m stays above
`done_range_m` 0.55 and `forward_wall_limit_m` 0.35 (already known; EXPLORE does not use done_range). Spark: agent
`bm-micro-ros-agent` still up, recorder stopped, clone at `6fa8b0e`; scratch wrapper `~/bm-scratch/pilot_mark3.py` on the
Spark (outside the repo) can be deleted.

**`b2-real-02` LAUNCHED on the real car at 06:04:56 CST (12:04:56 UTC), unattended, on `490fedb`**, 10 B2 episodes from the taped start. `490fedb`: the transit's and each episode's circle-to-circle comparison is a recorded dead-reckoning drift measurement (halt only beyond a ratio of 1.6); range check on forward moves only, with a last-10-moves window; end pose written before end-of-episode checks. Gates on that commit: test diff (one assertion removed, disclosed: a 25 % wrong scale no longer halts at the transit in that test's geometry, it halts on the ranges 15 steps into the episode); full Mac suite 716 passed, 10 skipped, prereg OK (Claude's run); Spark dry run `b2-real-02-dry` 10 of 10, 1,564 moves; record-pass re-run; independent review: yes, safe (53 simulated batches, no wall contact; from the real start every wrong scale 0.75/0.85/1.25 halted on the ranges at the first or second forward move of the transit, 1.27 m from the nearest edge; with the range check switched off the other layers still halted every run, smallest depth 0.18 m at 35 % short). Residual: a false halt in the first ranged moves (0.1 % at the measured scatter, more if slip grows) or `no_fix` at a circle. Latch from b2-real-01 cleared by Claude under Xiaohui's name (standing authorisation). At 06:07 the transit was done and episode 1 had started. Log `/tmp/bm-b2-real-02.log`, folder `data/batches/b2-real-02`.

**Standing authorisation (Xiaohui, 2026-11-25 ≈ 05:50 CST, before leaving):** "you should clear the halt for all the future runs without the need to ask me … future runs might just start on where it was left off on the previous run." Claude may clear a batch halt and the project latch under Xiaohui's name and restart from the car's last pose. Claude's limits: only after the halt is diagnosed from the logs; new batch code only after all gates on that commit (test diff, suite, independent review, record-pass, exact-argument dry run); never after a stall, contact, wall-guard, `tag_survey`, repeated link-loss or Pico-restart halt, or anything unexplained. Car now back at the taped start (lens over the 2.00 m tick facing T03; Xiaohui, 05:47), Pico online, not restarted since 05:07. Replay on real episode 1 (video agent, `ab585ae`): B0 19.7 cm / 7.7°, B2 3.1 cm / 3.7° final error (truth sigma 5 cm); the free procedure arm equals live B2 at 83 of 83 steps; real logs carry no `_tag`, so the association metrics cannot be computed on them. The session's 5-minute job is now `4607b3da` with these rules.

**Diagnosis of the `b2-real-01` halt (batch agent, read-only, ≈ 05:45 CST): real dead-reckoning drift, not a scale error, not bad tags.** Range check (bias removed) over the episode's 12 forward moves with tags: median 0.980, no halt: the encoder scale is right. Both circles are accurate (rms 0.023 m, 14 and 9 tags) and the step fixes from many tags agree with them. Dead reckoning from the start circle ends **0.27 m off (all in y) and 13.4° off** after 2.64 m of straights and about 70 turns; the tag-tracked pose ends 0.06 m from the end circle. Causes found: slip on some straights (row 24: wheel/gyro yaw disagreement 16.7°, range check 0.88) and a gyro that under-reads rotation by 0.6–0.8 % (more in the first minutes: the first circles' rms falls from 0.06 to 0.028 with turn angles × 1.015); the pivot turns' axle shift is not the cause. The transit read 1.139 the same way. The error over-reports travel (the car is never farther along than it thinks). **This is the project's result on the real car (B0 drifts, tags correct it) and belongs in the report.** The episode check's `odometry_scale` message was wrong: it conflates drift with scale. Next version (batch agent, Mac only): keep the circle-to-circle comparison as a recorded drift measurement, not a halt; scale protection by the range check, the guard, the 0.75 m blind cap, fix_conflict and tag_survey; write the end pose before end-of-episode checks; plus `dc67bce` (forward moves only, 10-move window). Then the independent review of everything since `e3c8d0e`, record-pass and the dry run. The video agent is making the converter accept episode 1 (complete; halted only by the post-episode check). Circle residuals, 5 real circles: first circles 0.061 and 0.062 m (limit 0.08), the others 0.023–0.024. **The halt on the car is NOT cleared; restarting needs Xiaohui.**

**`b2-real-01` HALTED at 05:29:06 CST after episode 1.** Episode 1 (S1) ran to the end: start miss 0.05 m / 16°, ended by DONE after 83 steps (the practice run had stopped at 19), with full tag fixes late in the episode. Then the episode check (start circle to end circle, added in `5086391`) halted the batch: 0.72 m by odometry against 0.91 m by the tags, ratio 1.27, limit 1 ± 0.18. Car stopped, latch set, NOT cleared (left for Xiaohui). The batch agent is diagnosing read-only: what the range check and the transit read; the two circles' real accuracy; whether the pivot turns' axle shift (about 1.2 cm per 30°) accumulates into a real odometry error over about 60 turns; whether episode 1's log is usable for the replay. No replay started (one episode, marked halted). Nine episodes not run.

**`b2-real-01` LAUNCHED on the real car at 05:22:41 CST (11:22:41 UTC), unattended, on `e3c8d0e`** (Xiaohui, ≈ 05:05: "we should use e3c8d0e after the review. We should always use the best version"). `e3c8d0e` removes the pilot's range bias in the range check (window 0.785–3.0 m, tags within 30° of ahead, repeated IDs resolved by the tracked pose). Gates on that commit: no line removed from `test_car_batch.py` since `05f64c4`; full Mac suite 711 passed, 10 skipped, prereg OK (Claude's run); Spark dry run `b2-real-01-dry-e3` 10 of 10, 1,564 moves; record-pass re-run; independent review of the delta: at least as safe as `cfa3948`, 176 more simulated batches, no wall contact, short-reading scales halted 54 of 54; residual: a `no_fix` halt from the 0.08 m circle residual, one wheel 15 % wrong never flagged (stays ≥ 0.25 m inside). The Pico rejoined at 05:08:35 after Xiaohui replugged it; DHCP log: it had restarted several times at 04:31–04:32 and then gone silent (the camera on the same bank stayed up): suspect the Pico's USB plug or the bank's port; a repeat during the batch is a safe halt. Latch from practice-01b cleared by Claude under Xiaohui's name (go-ahead recorded below). Tmux `bm-batch`, log `/tmp/bm-b2-real-01.log`, folder `data/batches/b2-real-01`. At 05:25 the first circle and transit were done and episode 1 was at step 13. Nobody may pull or change the Spark clone while it runs. Any halt is left for Xiaohui.

**NOT LAUNCHED (≈ 05:05 CST): the car's Pico is off the network.** Independent review of `cfa3948` (fresh agent, 264 simulated batches in the measured room, wrong scales ±13–25 %, one wheel ±15 %, pessimistic bearing noise and the 3.4° drift): no wall contact, smallest true depth inside the drive polygon 0.19 m, nothing blocking; residual risk a false halt (range check centred on 1.00 while the real car reads 0.96–0.98 without the bias correction: 0.2–3 % per start; a `no_fix` from the 0.08 m circle residual under pessimistic noise). All gates were then met on `cfa3948` (Spark clone there, record-pass done), but at the pre-launch check the car gave no telemetry and no ping (camera answers; one station on the access point). Same symptom as 03:26, when Xiaohui had to replug the Pico's USB at the power bank. The latch was NOT cleared; nothing was sent. Needs Xiaohui: replug the Pico (motor battery off first), then the batch can start at once. Suspect: the power bank switching off the Pico's port, or the cable disturbed when the car was carried to the start; if it recurs, a different port or bank.

**Go-ahead for the overnight batch (Xiaohui, 2026-11-25 ≈ 04:50 CST):** "You could start the batch on your own if needed" and "The car is placed" (lens over the pilot's 2.00 m tick facing T03, motor battery on; room prepared as Claude listed). Claude may clear practice-01b's latch under Xiaohui's name and launch `b2-real-01` once the independent review of the range check finds nothing blocking. State then: range check `cfa3948` pushed; no assertion removed from `test_car_batch.py` since `05f64c4` (diff read by Claude); full Mac suite 709 passed, 10 skipped, prereg OK (Claude's run); exact-argument dry runs on `cfa3948` complete 10 of 10 (plain, read by Claude on the Spark; with +3.4° drift, batch agent); record-pass re-run on `cfa3948`. Halts during the night are not cleared or retried.

**CORRECTION (≈ 04:12): gate 2 is NOT met.** The batch agent reported that its original 25 % wrong-scale fault test (8-tag world, 2.5 m, taped start, 0.245 m transit, so no transit check) fails unchanged against `5086391` (all 3 seeds complete); it had rewritten the test into a weaker 20-tag, 2-of-3 version, which is why Claude's rerun showed 269 passed. Claude's own argument (tonight's 0.7 m first transit is checked) holds for this start pose only. b2-real-01 is on hold; the agent is writing a range-only scale check along each straight (tags near straight ahead; pilot range noise is millimetres), with the original test restored unchanged (3 of 3 halts). After its push: verify, record-pass again, the exact-argument dry run again, then the batch only after Xiaohui clears the latch. **Earlier note, superseded where it says 'passed':** Overnight gates (2026-11-25 ≈ 04:00–04:10 CST): all three passed; the car waits only for Xiaohui to clear the practice run's latch. (1) Diagnosis (batch agent, checked by Claude): practice-01b's `odometry_scale` halt was a false alarm: one single-tag fix about 3 m away (sigma 0.12 m) landed 0.21 m behind on a 5 cm leg and swung the per-step statistic from +4.7 % to −24 %; the straights alone say −1 % and the batch's transit check read 1.008. (2) Fix `5086391`: a weighted least-squares scale that halts only above 12 % and 3 standard errors, plus an episode check between the circles; the unchanged transit check still halts a 25 % wrong scale before any episode (test, 3 of 3 seeds); with no transit the per-step layer catches it in 2 of 3 seeds (the third never nears a wall); Claude reran the batch, executor, odometry and dv tests at `5086391`: 269 passed; prereg verify OK. (3) record-pass re-run at `4d25dd6` (after the fix; `285be33` touches no marker file), then the dry run `b2-real-01-dry` with the exact real arguments: complete, 10 of 10 (9 DONE, S4 150 steps), 1,564 moves, final errors 0.01–0.06 m. The batch agent's rehearsal (`evidence/M3/M3.T12/batch-runner/rehearsal-2026-11-25.md`) also ran 10 of 10 with the measured +3.4° per straight added. Stand, STOP and floor evidence: `evidence/M3/M3.T6/{stand-test,floor-check}.md`, `M3.T13/smoke.md`; M3.T6, T7, T8, T13 done. **Blocked:** `data/LATCH` from practice-01b is set; clearing it needs Xiaohui to look at the car (asked at 04:03, no answer yet). Car online, armed, not restarted since 03:32.

**Overnight decisions (Xiaohui, 2026-11-25 ≈ 04:00 CST, before sleeping).** (1) **Run the real B2 batch `b2-real-01` (10 episodes) unattended tonight**, on Claude's conditions: the batch agent's diagnosis shows the `odometry_scale` halt was a false alarm, the fix passes its tests including the 25 % wrong-scale fault injection, and the exact-argument dry run completes; otherwise the car does not run. Xiaohui sets the car at the taped start (lens over the pilot's 2.00 m tick facing T03), power bank and motor battery on, doors closed, floor clear. (2) **Opus 5.5 replay of the real logs: cap raised to US$200** ("The limit is set to 200 instead"), started without a further estimate; then Qwen3.8 and Gemma 4 on the Spark GPU, one server at a time. (3) Xiaohui keeps the current plan (practice and batch episodes driven by B2; Opus live on the car only for the 2–3 closed-loop episodes). Claude checks every 5 minutes (session cron job, `caffeinate` on the Mac for 12 h); the batch agent diagnoses the halt; the video agent prepares the real-log replay pipeline (input conversion, `--dv dv-real.json`, room prompt, truth from `truth.jsonl`, a no-cost dry rehearsal, exact commands). A halt during the night is never cleared or retried.

**Attended pass recorded and practice run (3.3) attempted, 2026-11-25 ≈ 03:25–03:47 CST.** `car_batch.sh - record-pass` (stand `20261125-025313-stand-test`, floor `20261125-030214-floor-check`, world `real-room.json`) wrote `data/real/ATTENDED_PASS.json`. R1 rehearsal (`practice-01-dry`, the exact real arguments, start = lens over the pilot's 2.00 m tick facing T03 = (2.369, 2.206, −90)): complete, DONE after 84 steps, final error 0.01 m / 1°. Real attempts, none of which drove the car into anything: (1) `practice-01` refused at preflight, car not on the access point (the Pico had lost power or hung; Xiaohui replugged its USB from the bank; it rejoined in 5 s); (2) `practice-01b` halted before any move, "the recorder session SIGHUP is no longer active": a late-binding closure in `tools/car_batch.py` (the signal loop rebound `name`), fixed in `07dd34f`; (3) `practice-01b` rerun: first circle and transit to S1 fine (start miss 0.03 m / 11°), scan and two straights, then **halt `odometry_scale` at step 19**: tag fixes −23 % of the odometry's 1.2 m (7 fixes, limit 12 %). The tape-measured scales say the odometry is right within 1 %, and the view fixes carry sigma 0.15–0.29 m, so this may be a false alarm; the batch agent is diagnosing it (real or false, and a check that weights the fixes' sigma without weakening the 25 % fault cases). **No unattended batch until that is settled.**

**Stand test (M3.T6 §5.1, M3.T7) and STOP check (M3.T13) PASSED, 2026-11-25 ≈ 02:53–03:00 CST** (session
`20261125-025313-stand-test`, fresh 4 × AA). All motor-off checks passed (telemetry 0.007 s, armed, IMU, clock, latch
clear, STOP program alive; `/pico/cmd_vel` subscribers are the car and the rosbag, the STOP program the only
publisher); drive map 0.25 / 0.33; refusal without `--i-am-at-the-car`. S1 0.091 m, S2 0.246/0.247/0.244 m, S3
−0.096 m, S4/S5 `timeout` at 5.3 s with opposite wheel counts; the left wheel counts about half the right on the stand
(free wheels; on the floor they are within 4–7 %). STOP key (sent through tmux by Claude, not typed by Xiaohui): zero
duty 0.037 s, wheels still 0.129 s (`estop_max_s` 0.2); latch refuses a move; clear-latch then runs. Ctrl+C mid-move:
0.043 / 0.153 s, executor latch. Container killed mid-move (no zeros sent): wheels still 0.570 s (firmware timeout).

**Floor check (M3.T8, work list 2.8) DONE, measured with the wall tags and one tape reading instead of tape per step
(Xiaohui agreed), 2026-11-25 ≈ 03:02–03:30 CST** (session `20261125-030214-floor-check`; scratch runners
`~/bm-scratch/{tagmeas,floor,verify,scale4}.sh|py` on the Spark, logs beside them). Straights turn the car **about 3°
left per 25 cm** (gyro and tags agree; under the 6° limit; the odometry reports it). Turns: 3 × 30° = 89.0° / −89.3° by
tags, gyro within 2° (pass). STOP on the floor: 0.5 cm after the key, still at 0.104 s (pass). F2 (10 cm out and back)
ends 2–3 cm ahead each time by 2-tag fixes (marginal; the backward leg stops about 5 mm short). **Encoder scale:** the
nominal 20,524 counts/m under-reported travel by several percent; a first estimate from tag fixes (18,555 / 19,096,
commit `75be6fa`) over-corrected because the fixes' sideways position at 2–3 m is only good to about ±10 cm; the
tape-measured straight (lens from the 2.75 m tick to 1.83 m from the baseboard, 0.19 m left of the line, gyro 12.13°)
gives **left 19,385, right 19,804 counts/m (±1 %)**, now in `configs/car.json`. Lesson: tag fixes are good along the
line of sight (ranges), weak across it; measure distance with a tape or with ranges to a tag straight ahead.

**Range limit 3.0 m (Xiaohui, 2026-11-25: "I would say 3.0 will be better")**, inside the pilot's reliable range (to 3.135 m). `configs/dv-real.json` written by the batch README's command a2 (sha12 `ea2cd23f9186`): the frozen file with `sigma_range_a_m` 0.05 → 0.0063, `sigma_range_b_per_m` 0.05 → 0.017, `sigma_bearing_deg` 2.0 → 1.937, `reject_range_above_m` 2.0 → 3.0; frozen `dv.json` unchanged. Real batches run with `--max-range 3.0 --detector-noise course-project/configs/detector_noise.json --dv course-project/configs/dv-real.json`. Motor pack: 4 × AA alkaline (6.67 V fresh on 2026-09-20, 5.7–5.9 V by mid-October; `pack_min_v` 5.5 V); Claude advised a fresh set before the stand test, kept for the floor check and the first batches; there is no battery signal on the car.

**Tags.** Xiaohui checked a printed tag: about 16 × 16 cm (passes the printer-scaling check; the pilot's step A1 takes
the exact reading). Mounting started 2026-11-25 from a mounting page Claude published (a to-scale plan and a
wall-by-wall list generated from `layout-2/layout.json`; private claude.ai artifact). Xiaohui asked whether to fold the
pages' printed labels so the model cannot "cheat": no, the model never receives an image (its nine D5 tools pass
numbers only; frames go to `perception/tags.py`, which reports ID, range and bearing).

**Agents' results so far.** Messages to both agents were partly lost (the batch agent never received the DV message;
the video agent finished believing the length was still an assumption); all were resent on 2026-11-25.
- **batch:** tasks 1–7 done on the simulated car (commits `2cd3415`, `05f64c4`, `92f9036`; evidence
  `evidence/M3/M3.T12/batch-runner/`; the real car never commanded). 3.0 m dry run, 20-tag world: 4 of 4 batches, 20 of
  20 episodes, no halt (2.5 m: 3 of 4, one `no_fix`; 2.0 m: 1 of 4). First run of `car_batch.sh` on the Spark: a
  simulated batch is a `--dry-run` without recorder; on the real-car path with the car off, `record_session.sh start`
  exited 1 and left a recorder running (stopped by hand at once); fixed, and a real run is now refused when the
  recorder finds no car, camera or agent. ROS-path and full real-car path untested past the refusals. New halt
  `tag_survey`: every full circle checks each tag against the others; 160 of 160 injected 0.3/0.5 m survey errors
  halted naming the right tag, no false halt in clean runs (review finding 3 closed). `--detector-noise` takes the
  pilot's model for the fix sigma (recorded in the manifest). Paste-ready first-batch commands in the README ("Before
  the first real batch"); stand-in dry run 10 of 10, exit 0. Tests: Mac 643 passed (without the video agent's work in
  progress), container 308. **Decision (Claude, software delegation):** real batches use `--detector-noise
  configs/detector_noise.json` once the pilot writes it, and `dv-real.json` must come from the same file (checked by
  sha256). **`--dv` done** (commits `f1897e9`, `f4d0e87`): `tools/real_dv.py` writes `configs/dv-real.json` = the
  frozen file with exactly `sigma_range_a_m`, `sigma_range_b_per_m`, `sigma_bearing_deg` (pilot's bias added to its
  sigma, since the detector does not correct it) and `reject_range_above_m` changed; `well_cond_*`, `reloc_sigma_*`,
  `gate_*` stay frozen (thresholds, not noise models). `--dv` in `car_batch.py`, `closed_loop_run.py`,
  `room_rehearsal.py` through a scoped dv-cache override (frozen modules untouched; restored on exit). A real batch
  requires an explicit `--dv`. Checked by the lead: `configs/dv.json` unchanged since `65173fe`, no `dv-real.json`
  yet, prereg verify OK, `test_dv_real.py` 8 passed. Spark checked clear by the lead (no container, recorder, latch);
  reserved for Xiaohui's sessions. Empty `*-batch-real-refusal-*` sessions and dry-run folders on the Spark: to clean
  up after the sessions. **Spark clone pulled to `f4d0e87`** before the pilot (scripts parse; the system
  `/usr/bin/python3` has OpenCV 4.13 with aruco; `tag_pilot.py --selftest` passes, 15 checks).
- **video, revised** (commit `8652a5d`): 3:00–5:00 is a hard check; silent video now 3:37.64 without the car part
  (simulation 2:56; with the car part it shrinks to about 2:09, whole video at most 4:16). Each move is drawn at its
  commanded speed (0.15 m/s, 45°/s) played at ×2, thinking at ×14 (×34 with the car part); car to scale with a
  close-up and a simulated camera view. Checked by the lead: duration, a mid-video frame, the agent's six-frame
  continuity strips. Then commit `cf13684`: every move at most ×2 and at least 7 output frames (turns 8, straights
  21), refused otherwise; `sim.motion: glide` keeps the `6a9c848` style as a fallback; parts and the final video
  replace the old files only after their checks pass. Whole suite 695 passed. Both agents idle, nothing open.
- **video:** commit `6a9c848`; `python3 course-project/tools/demo_video.py all` renders `data/video/parts/sim.mp4`
  (1:59.76) and `data/video/BeaconMind-demo-silent.mp4` (2:41.76, without the car part), 1920 × 1080, 25 fps; checked
  by the lead with ffmpeg. The Opus episode plays at ×24 and every move glides over 0.3 s of output (seen frame by
  frame: a turn spreads over about seven frames, no jumps). Every number comes from `report_assets.py` or the logs.
  Narration script `presentation/demo-voiceover.md`. Car part's input path tested on a stand-in. 677 passed, 10 skipped.
  `data/video/venv` is an empty venv (pip only) the agent could not delete; Xiaohui may delete it.
- The report's and slides' room figure is mirrored (listed in `report/PENDING.md`).

**Still open for Xiaohui:** after the pilot, the range limit (3.0 or 2.5 m); watch the silent video once (is ×24
too fast?); the voice-over, best recorded once the car part exists. **Needs Xiaohui next (unchanged):** measure one printed square
(160 ± 1 mm); mount the 20 tags from the new sheet and record the centres; tag pilot; stand test and floor check.

## 2026-11-18 (later) — delegation, unattended batches, spend approvals; parallel agents, room rehearsal, tag layout C20 decided

**Delegation (Xiaohui, about 02:15 CST):** "fully automate the whole process and finish the tasks that could be done
automatically … use subagents … choose the option that gives us the best quality. Do not try to save tokens … feel free
to stage the changes, commit and push"; later "feel free to perform adversarial reviews on the steps you think it is
important". Five agents were started on disjoint files: tag perception, car control (executor, STOP, backend), the room
simulator and B2 rehearsal, the closed loop, the report.

**Unattended batches approved (Xiaohui):** "I approve leaving the motor battery on unattended"; coded-procedure and
live Opus episodes are to run back to back without Xiaohui at the car. Details, the safeguards that replace the hand on
the switch, and the ground-truth change (resection from the surveyed tags, tape at the batch's first start, last end and
a spot check) are in plan/README.md §3.6 "Unattended batches". A batch runner is still to be built.

**Spend approved (Xiaohui):** the simulated Opus 5.5 and Fable 5.2 episodes; the 2–3 live Opus episodes on the car; the
Opus replay of the 10 real logs ("Yes, I approve the replay as well"; quoted US$48–110, tell Xiaohui the tightened
estimate first). The GPU is free for Xiaohui's other use until the Qwen3.8/Gemma replay of the real logs.

**Overnight stall (04:19–11:55 CST).** The room option grid finished at 04:19 but its agent's final report never
reached the lead, which was waiting on it; nothing ran for about 7.5 h. The Mac stayed awake (`caffeinate -ims`), no
money was spent, the car was not touched. Work restarted at 11:55 when Xiaohui asked for the status; Xiaohui then asked
for a status check every 5 minutes until everything is finished. Lesson: do not gate all remaining work on one agent's
message; start the independent tasks at once and check the agents on a timer.

**Room rehearsal done (M3.T12, commit `68ee4eb`; all simulated, nominal tag positions).** Report
`evidence/M3/M3.T12/rehearsal-b2.md`, tables `rehearsal-b2-tables.md` (159 configurations × 150 episodes).
**Decisions by Claude under the delegation:**
- **Tag layout C20:** keep the 12 printed 160 mm pages, add 8 more 160 mm tags with new IDs: ID 1 on the angled
  section 20 cm from corner 4; IDs 7, 5, 4, 6, 11 on the window wall 14, 125, 215, 314, 404 cm from corner 3; IDs 8, 9
  on the 295 cm wall 200 and 269 cm from corner 5. World file `configs/arenas/real-room-plus8-160mm-nominal.json`
  (`real-room-nominal.json` stays as the 12-tag layout). 100 mm tags rejected: full reprint, and 3.0 m is at their
  simulated far limit. Nothing is reprinted. **The 8 new pages were printed on 2026-11-18 at 14:54 (see below); no tag is mounted yet.**
- **Range limit 3.0 m** (2.5 m if the real tag pilot does not confirm it). Prompt v3.3 says "rejected if range_m > 2.0"
  in words; the frozen prompt is not edited, a real-room variant with that one number changed is a recorded deviation.
- **Driving area inset 0.4 m** from every wall (geofence in the backend / tape).
- **Start poses S1–S5** from `configs/arenas/real-room-scenarios.json`; S3 (2.60, 3.90, −90°) is the hard case
  (9 of 30 run to the budget). B2 driver `kr.make_b2_policy()` (wraps frozen `decide_step`, handles the "E5 leg with no
  forward move" branch the frozen code raises on; identical to frozen B2 on the study square).
**Findings:** with study or carpet odometry B2 is no better than dead reckoning in any layout (B0 1.4–2.2 cm, B2
1.6–3.1 cm median ATE). With the frozen `dv.json` sigmas a two-tag fix passes its own error test in under 1 % of
steps, so heading is never corrected under 2 % drift (21–26° both). With the simulated detector's sigmas
(0.01 + 0.012 r, 0.5°) and C20 at 3.0 m B2 halves the final heading error under drift (10.5° against 23.0°).
**OPEN for Xiaohui:** approve a separate real-run DV file with the tag pilot's measured sigmas (frozen `dv.json`
untouched). The 160 mm near limit (0.74 m) hides a tag in 3–8 % of B2 steps; `done_range_m` 0.55 m is inside it, so
GO_TO_BEACON would lose its target (EXPLORE does not use it). `data/room/rehearsal/` (42 MB, git-ignored, superseded
pinhole-model logs) can be deleted.

**Slides and README (commit `c45cd6b`).** Public: `README.md` rewritten for graders, `slides/outline.template.md`
(edit this), generated `slides/outline.md`, `numbers.json`, `figures/`; `report_assets.py --slides`. Private repo
(uncommitted): `course-project/presentation/{build_deck.py,validate_deck.sh,Chen-BeaconMind-Final.pptx,REVIEW.md}`,
15 slides on the JHU template, placeholders on slides 9, 10, 11, 13 matching `report/PENDING.md`. **OPEN for Xiaohui:**
presentation requirements (assumed 15 minutes), whether the private `presentation/` folder is the right place, the long
title crossing the shield graphic. Not done from M6.T6: disclosure audit script, code archive, submission checklist.

**Closed-loop rerun on the final room simulator (M2.T7, commit `fa4d758`; 12:19–12:39 CST; n = 1 per arm).**
Configuration: C20 world, S1, noise seed 3000, study odometry, 3.0 m, inset 0.4 m, frozen `dv.json`, prompt
`prompts/robot_system_prompt_v3.3-room.txt` (one number differs from frozen v3.3: range threshold 2.0 → 3.0; a recorded
deviation). All three arms ended DONE: steps 56 (Opus 5.5), 56 (Fable 5.2), 58 (B2); ATE 2.3 cm each (dead reckoning
1.4–1.5 cm); final heading 1.8°, 1.8°, 2.5°; 14 of 20 tags mapped, no phantom; validator rejections 0; no full fix in
any arm; p95 step time 25.0 s and 23.7 s; cost **US$4.60 (Opus) and US$8.33 (Fable)**, under the US$8 / US$14 caps but
above the US$6–8 the lead had told Xiaohui. The two models made the identical 55 moves; the one branch from B2 is a
different pose argument at step 31 (Opus passed its pose rounded to two decimals, 1 mm off; Fable passed the step-30
position from before that step's fix, 2 cm off), which flips a wall-distance threshold in `exploration_summary`; given the tool
results each model obtained, all 112 model decisions equal the coded procedure's (corrected after an independent review). Evidence `evidence/M2/M2.T7/closed-loop/README.md`,
`runs-final/`; the first pair is kept there as superseded. Closed-loop API spend on 2026-11-18: US$18.84. The report
agent is filling the simulator part of `report/PENDING.md` item 6 and the slide.

**Tag layout `real-room-2` (M3.T10, commit `d903cd1`).** `tools/room_layout.py` now builds the 20-tag layout and checks
it against the world file (agrees to the millimetre, no clash found). Print files (git-ignored):
`data/real/tags/room-layout-real-room-2-new-tags.pdf` (8 pages, IDs 1, 4, 5, 6, 7, 8, 9, 11) and
`room-layout-real-room-2-mounting-sheet.pdf` (all 20 tags), copies in `~/Downloads/BeaconMind-tags-real-room-2-*`.
**Printed 2026-11-18, 14:54 CST** (Xiaohui: "yes, print the 8 pages and the mounting sheet"): both PDFs on the Brother HL-3140CW (queue `Brother_HL_3140CW_series_2`, jobs 981 and 982), Letter, actual size, black only, one-sided; both jobs completed. Xiaohui has not yet measured a printed square (should be 160 ± 1 mm). The new sheet replaces the printed one: six printed tags (T02, T03, T05–T08)
have narrower slide ranges so pages cannot touch. Unchecked: outlets on the 295 cm wall, window wall and desk wall were
never located; T16 (ID 7) is 3 cm from corner 3; T12 (ID 1) is about 13 cm from the angled section's estimated outlet.
Coverage at 46.9°, whole tag in the picture, 3.0 m: one heading sees ≥ 1 tag 54.9 % (12 tags: 49.9 %), ≥ 2 tags 29.6 %
(11.8 %); full turn ≥ 2 tags 98.3 % (`evidence/M3/M3.T10/layout-2/coverage.txt`). `tag_pilot.py placements` gained
`--tag-black-m`.

**Report and slides after two independent review rounds (commits `eb5dd7c`, `b014e38`, `8578a05`, `0055643`).**
Section V-G "Closed loop in simulation" is in; Section IV-B and Fig. 3 describe the 20-tag layout (12 printed, 8 not yet
printed, none mounted) with the 3.0 m limit called provisional. Still 12 pages with no slack (page 12 is full); six
placeholders remain (`report/PENDING.md` 1, 2, 4, 5, 6 car part, 7). The page limit is an assumption: **OPEN for
Xiaohui**; cut material can return if the limit is higher. Review record: `report/REVIEW.md`. The deck in the private
repo was rebuilt each round but no reviewer has read the deck itself.

**Unattended batch runner (plan §3.6, commit `1f73553`; simulated car only, never run on the real car).**
`bash course-project/tools/car_batch.sh <label> run --world W --scenarios S --initial-pose x,y,th --episodes N
--policy b2|<model key> [--max-range R] [--cap-usd X]`; code `beaconmind/car/batch.py`, `resection.py`,
`tools/car_batch.py`; evidence and the halt-code table `evidence/M3/M3.T12/batch-runner/README.md`.
- Batch folder `data/batches/<label>` (manifest, spend, HALT.LATCH survive reruns); recorder on for the whole batch.
- Refuses a real run without `data/real/ATTENDED_PASS.json`, written only by `car_batch.py record-pass --operator
  --stand-session --floor-session` (two different recorded sessions, file hashes, 7-day age limit).
- Sets and reads back drive map 0.25/0.33; the first full circle is solved without the taped pose and must agree with
  it; ground truth per step in `truth.jsonl` with sigma and a no-fix flag; a guard on every move (footprint + 2 sigma
  inside the drive polygon, at most 0.75 m straight travel since the last tag fix); 25 halt codes end the whole batch.
- An independent review (1,140 fault-injection runs) found 18 problems in the first version; 15 are fixed with tests.
  **Not closed:** a tag surveyed 0.3 m wrong still moves the tracked pose 0.33 m (smallest wall clearance 4 cm in the
  probe, no contact), so **the world file must hold measured tag centres before any unattended batch**. Stated limits:
  no motor-battery signal exists; a hung model call overruns wall-clock caps with the car at rest. Untested:
  `car_batch.sh` itself (syntax-checked only, it has never started a recorder or container), `usd_cap` between two
  episodes, two halts raised inside a scan. `fix_sigma_a_m`/`fix_sigma_b` (0.03 m + 0.04 × range) are assumptions for
  the tag pilot to replace.
- Dry runs (B2, five start poses, 4 seeds): at range limit 2.0 m no batch of five completes (four `no_fix` halts); at
  2.5 m 3 of 4 complete. Supports the longer range limit; 3.0 m with the 20-tag world was not dry-run.
- Before the first real batch: stand test and floor check pass, `record-pass`, a dry run with the exact arguments, car
  at least 0.7 m from every edge, first start pose at least 0.3 m away, first one or two episodes attended, wrapper
  inside tmux.

**Later the same afternoon (commits `26d541e`, `609737e`, `353d49f`):** a halted closed-loop episode now ends without a
model request (`halted_without_request` in the summary); the batch runner's remaining halt paths have tests (91 in
`test_car_batch.py`); `record-pass` now requires `--world <surveyed file>` and a batch on any other world file is
refused. The batch-runner tests were written with the fixes and were not run against the old code. The batch
runner's evidence README does not mention the last change (`353d49f`: a batch halt is recorded as `ended_by: halt`,
not as the spend cap).

**Handoff (Xiaohui, 2026-11-18, about 15:00 CST):** "I will open up a new session when I am ready to continue with the project". Start the next session from this entry.

**Containers stopped (Xiaohui, about 15:05 CST):** "turn off all the containers, including the ones you did not start,
to release the memory and GPU resources". On the Spark `docker stop bm-micro-ros-agent deploy-comfyui-1`: no container
is running, memory in use fell from 73 GB to 2 GB, no GPU process. `bm-micro-ros-agent` was started with `--rm`, so it
is gone: bring it back with `bash course-project/tools/car_net.sh agent-start` before any work with the car.
`deploy-comfyui-1` (not BeaconMind's; restart policy unless-stopped) stays stopped until someone runs
`docker start deploy-comfyui-1`. Still up on the Spark: the access point and the tmux session `bm-cam-relay`.
The Spark lines in the state paragraph below predate this.

**State (2026-11-18, about 14:50 CST).** Tests on the Mac: 606 passed, 10 skipped; prereg verify OK. The Spark clone
is at `353d49f` (one stale untracked file, `report/generated/tab-kinds.tex`). `caffeinate` stopped; all agents idle. Spark: access
point, `bm-micro-ros-agent`, `bm-cam-relay` up; car on its power bank, motor battery off; no recording. Nothing has
moved the real car. API spend today: US$18.84 (closed loop). **Needs Xiaohui next:** measure one printed square
(160 ± 1 mm); mount all 20 tags from the NEW mounting sheet and record their centres; tag-accuracy pilot; stand test and floor check;
approve (or not) a real-run DV file with the pilot's sigmas; the report's page limit and presentation requirements.

## 2026-11-18 — work list 2.10 and 2.2 DONE, 2.3 intrinsics done: recorder (M3.T27); camera size XGA (M1.T17); camera.json; tags printed

**2.2 capture size (M1.T17 done): XGA 1024 × 768, JPEG quality 12** (Xiaohui, after Claude's recommendation;
`evidence/M1/M1.T17/size-decision.md`). Floor-spot probes, camera about 141 cm from a bare wall, recorded session
`20261118-001733-capture-size`, 100 frames each: VGA q12 7.1 frames/s, p95 184 ms; XGA q12 5.4 frames/s, p95 237 ms;
UXGA q10 1.75 frames/s, p95 665 ms (fails the plan's bar). XGA gives a tag about 57 px at 2.5 m against 35 px at VGA.
The "must be 1600×1200" sentences in M1.T6 and M1.T7 are edited. bm_cam-0.2 boots at VGA, so
`record_session.sh start` now sets XGA q12 (`--camera-size`, `keep` to leave it) and `camera_probe.py` gained `--save`.
The camera is at XGA q12 now.

**Tags printed** (2026-11-17, 23:57): the 13-page PDF on the Brother HL-3140CW, Letter, 100 %, black only, job
completed. Xiaohui mounts them and records each centre on the mounting sheet.

**Recorder** (`tools/record_session.sh start <label> | run <name> -- <cmd> | status | stop`, Spark host). One folder per
session under `data/real/<YYYYmmdd-HHMMSS>-<label>/`: `ros2 bag record -a` in a one-off `beaconmind-ros` container,
every camera frame with its X-BM headers (`record_frames.py`, `frames/latest.jpg` for live viewers), 5 Hz pings to the car
and camera, the access point's station dump (MACs cut to 3 bytes), the micro-ROS agent's log (and its last 200 lines at
start), the camera relay's output, commands run through `run` with exit codes, a 4 h watchdog; `stop` closes the bag
with SIGINT and writes README.md (`record_report.py`), plus `tape.md` and `notes.md` for the operator.
`tools/session_clock.py` is the clock to film at the start of each phone video. Only one program may be the camera's
client: use `--camera off` when the probe or the backend captures. Parked dry run with the car on ROS passed
(`evidence/M3/M3.T27/dry-run.md`): IMU 49.5 Hz, 300 frames at 4.9/s, pings 0 % loss. `/pico/cmd_vel` and
`/pico/imu/std` are the car's inputs, so they enter a bag only when something publishes them.

**Agent.** The 2026-11-10 agent container had `--rm`, so stopping it on 2026-11-13 deleted it.
`bash course-project/tools/car_net.sh agent-start | agent-stop` now runs it the same way.

**State (2026-11-18, about 00:15 CST).** Running on the Spark: the access point, `bm-cam-relay`, and
`bm-micro-ros-agent` with the car joined as `/pico_fusion`; the car on its power bank, **motor battery off**, parked;
no recording active. Recorder sessions so far: `recorder-smoke`, `recorder-dry-run`, `recorder-check` (data on the
Spark only).

**2.3 calibration (M1.T7): DONE (2026-11-18, about 02:10 CST), with accepted deviations.**
`configs/camera.json` (XGA 1024 × 768 q12): fx 1181.5, fy 1176.6, cx 498.4, cy 380.8, k1 +0.083, k2 −0.070, rms 0.34 px
over 20 views of the paper board **taped to a rigid backing** (7 turned, 4 tipped; session `20261118-014353-calibration-rigid`,
free mode). **HFOV 46.9°, VFOV 36.2°, not the design's 60°.** Independent distance check: tape 103.5 cm, solvePnP
103.4 cm (−0.1 %; `evidence/M1/M1.T7/distance-check.txt`); a refit from 30 views gives the same fx within 0.1 %.
Known gap: the board covered only 46 % of the picture grid (corners span x 317–1007, y 123–575), below the plan's
0.8, so distortion near the left, top and bottom edges is extrapolated; Xiaohui's two ruler readings of the printed
board are still owed. The earlier wall-frame estimate of 67° was wrong. With 46.9° the layout's coverage drops (one
heading sees a tag in about a third of samples at 2 m instead of 42 %; rerun `room_layout.py` with the measured value),
but a 160 mm tag is about 76 px wide at 2.5 m, which favours raising the 2.0 m range limit.
**Extrinsics measured 02:06** (`evidence/M1/M1.T7/extrinsics.md`, in camera.json): lens (0.120, 0, 0.075) m from car.json; roll +4.4°, pitch −3.9° (nose up), yaw +2.5° ± 2°; second distance check −1.2 %. Roll exceeds the plan's 3° mount limit; **Xiaohui accepted it as it is (2026-11-18), with the 0.46 coverage and no ruler check of the board: M1.T7 is done.** Do not touch the camera in its bracket: a bump invalidates these angles. (Earlier:) the car was on a desk for the capture; steps 8–9 (lens position from car.json, pitch and yaw from an image
with the car on the floor) are still to do. History of the night's failed attempts follows.

**(Superseded) 2.3 first attempts: capture tooling built, first result rejected (2026-11-18, about 01:45 CST).**
`tools/calibrate_camera.py` (`live` with a spoken guide, `calibrate`; tests `test_calibrate_camera.py`). What the
night's recorded sessions (`data/real/20261118-00442*` … `-013214-calibration-paper-free-2`, Spark only) showed:
- The **phone board failed**: its screen saturates in the camera beyond about 25 cm (squares shrink apart), and at
  20 cm there is no room to move. Dimming to 25 % helped detection, not reach.
- **Paper board** (`evidence/M1/M1.T7/board/paper/`, 9 × 6 inner corners, 23.283 mm, printed at 100 %; Xiaohui has not
  sent the two ruler readings yet): detected in about 80 % of frames at 45–75 cm.
- Target positions spoken to an operator who cannot see the picture do not work. **Free mode** (`live --free --hold
  board`: keep every steady, new view; hints only for moves that keep the board in view and add a new view) collected
  23 views in about 4 minutes.
- **The trial calibration is wrong and must not be used:** fx about 1575 px (hfov 36°) at rms 0.75 px, against about
  765 px (67°) from the capture-size frame (the 12 cm baseboard is about 65 px tall at 1.41 m). Cause: the page was held
  by hand without a backing and bends (planar-fit residual 1.1–1.4 px rms on the turned views, 0.3–0.7 on the flat ones),
  and only 6 of 23 views were tilted, none tipped. No `configs/camera.json` was written.
- **To finish:** tape the page flat to a book or stiff card; run free mode again; require tilted views (turned and
  tipped, at least 8); calibrate with k3 fixed; check fx against the baseboard figure and M1.T7 step 7's distance check.
  Xiaohui prefers plain "left/right" (their own, facing the camera; the picture is a mirror for them) and holding the
  board over taping it to a wall. The car was raised on a desk for these sessions; motor battery off throughout.

**Next:** Xiaohui mounts the 12 tags and records each centre; then 2.4 tag accuracy (M1.T8) on the wall tags, which also refines yaw; rerun `room_layout.py` coverage at the measured 46.9°. Code items 2.6, 2.7, 2.9, 4.1 and the report's Results are open. (Earlier note:) 2.3 calibration (M1.T7) at XGA with the phone board: first check the XGA distance bands with
`evidence/M1/M1.T7/board/detect_sim.py` at 1024 × 768, then Xiaohui holds the phone while the recorder's frame saver
captures (live coverage from `frames/latest.jpg`).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-18: wrote the recorder and its tests, ran the sessions, printed
the tags at Xiaohui's request, and wrote this entry.

## 2026-11-17 — section 2 started: the arena is the room; room surveyed; 12-tag layout and print sheets ready

**Decisions of 2026-11-13 not recorded here before** (made in a session started from the private repo):
- **R2 widened** (Xiaohui): "fully record the sensor data, camera streams, traces and logs as much as possible". Bench
  sessions are recorded too (capture-size probe, calibration, tag pilot, floor checks): every raw camera frame, every
  car topic, the micro-ROS agent and relay logs, link stats, terminal, traces. So the recorder (work list 2.10,
  M3.T27) is built **first**, before 2.2.
- Xiaohui's "one recording of the seed running" is the **first** real episode (3.3); the rest are kept (≥ 10 driven by
  B2, 2–3 closed-loop Opus 5.5 episodes including the demo take).

**Decision (Xiaohui, 2026-11-17): the real arena is the room the Spark is in.** The tags go on its own walls; no
2.25 m foam-board square is built. The entrance door and the two closet doors stay closed during runs.

**Survey** (`evidence/M3/M3.T10/room-survey.md`; Xiaohui's tape, Claude's least-squares fit). A 381 × 512 cm
rectangle with one corner cut at 45° (cut 123 cm): all eight readings fit within 0.6 cm once a misread 195 cm for the
cut was re-measured. Frame: origin at corner 5 (desk wall / 295 cm wall), y along the desk wall. The entrance door is
on the desk wall against corner 5 (trim 2.5–102 cm); then the light switches and an outlet with the Spark's power
brick, the desk (221–363 cm, 66 cm deep), and the Ethernet jack stretch (363–512 cm, cable on the floor, no tags). Doors
wall from corner 1: bare 54 cm, door 1, bare 71 cm (outlet), door 2, bare 76 cm. Baseboard 12 cm. The room photos
(`~/Downloads/IMG_8148`–`8151.HEIC` on the Mac) show a private room and stay out of this repo.

**Layout `real-room-1`** (`tools/room_layout.py`, tests `beaconmind/tests/test_room_layout.py`; output
`evidence/M3/M3.T10/layout/`). 12 tag36h11 tags, 160 mm black, kinsim's D3 ID rule (duplicated IDs 3, 0, 2). Each tag
on a Letter page whose bottom edge rests on the baseboard, so every tag centre is 23 cm up. A tag may slide ≤ 20 cm to
clear an outlet; the measured centre goes into the world file. Print PDF (13 pages: mounting sheet + 12 tags, each
checked to decode as its ID with a 159.85 mm black side): `data/real/tags/room-layout-real-room-1.pdf` (git-ignored),
copy at `~/Downloads/BeaconMind-tags-real-room-1.pdf` on the Mac. Driving area: the room with its desk-wall side moved to
the desk's front line (x = 0.66 m) for the whole wall, which keeps it convex and puts the chair (tucked in) and the floor
cables behind it.

**Coverage, a real sim-to-real difference** (`layout/coverage.txt`, kinsim's visibility rule, 60° field of view): at
the 2.0 m limit of `configs/dv.json`, 42 % of (position, heading) samples see a tag, against 98 % in the study's 2.25 m
arena; a turn in place finds a tag from 97 % of positions and two tags from 85 % (2.5 m: 99.7 % and 98.7 %). Fifteen
tags would add about 3 points, so twelve. **Open, for Xiaohui after the tag pilot (2.4):** keep 2.0 m for real runs or
raise it to 2.5 m. Also open: the tag tops (31 cm) may leave the camera's vertical view when the car is within about
0.5 m of a wall (lens 7.5 cm up; vertical field of view unmeasured until 2.3).

**For 3.1:** `envs/kinsim_lite.py` hard-codes the 2.25 m square (`ARENA`), and `bm.world-1` holds only a rectangle
(`arena.size_m`); the room needs a polygon arena (an additive schema field) and per-tag normals.

**State.** Nothing committed: the tool, the test, the evidence, this entry and the M3.T10 status row (`in-progress`).
Mac tests: 114 passed, 3 skipped (`PYTHONPATH=src python3 -m pytest -q`). On the Spark: the access point and the
`bm-cam-relay` tmux still up; `bm-micro-ros-agent` stopped (`docker start bm-micro-ros-agent`); the car off. A
non-project container, `deploy-comfyui-1`, holds about 64 GB: it must stop before Qwen3.8 (about 97 GB) serves the
real-log replay (3.6). The tag PDF was drawn with OpenCV 5.1 in a scratch venv on the Mac (neither the Mac's Python nor
the Spark host venv has `cv2`; `beaconmind-ros` does).

**Next:** Xiaohui prints at 100 % (check 160 mm with a ruler), mounts, and measures each tag's centre on the mounting
sheet. Claude: the recorder (2.10) first, then 2.2 capture size and 2.3 calibration with Xiaohui; in parallel the code
items 2.6, 2.7, 2.9 and 4.1, and the report's Results (5) from `evidence/M4/M4.T16/results_summary.md`.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-17: read the room photos, fitted the survey, wrote the layout
tool, its tests and this entry. Xiaohui Chen took every measurement and made the arena decision.

## 2026-11-13 — work list 1.7 and 1.8 DONE: the main simulated study's results (section 1 complete)

**Sweep (M4.T4 done).** Every arm finished 1,976 / 1,976 steps on seeds 2000-2029 from a clean `61ca2c7`, with the frozen
config tags. Opus 5.5: 2026-11-10 02:06-03:35 CST, 1 fallback, US$143.97. Gemma 4 (vLLM): 2026-11-10 02:06 to 11-12
14:50, 78 fallbacks (70 no parse, 8 output cap), 79 client timeouts in 66 steps (77 retried; seeds 2008 and 2021
stopped at step 0 and were completed by the single pre-registered resume). At about 7 tokens/s, Gemma's output cap
takes longer than the 60-minute timeout, so its timeouts were probably long generations re-asked; its fallbacks are a
lower bound. Qwen3.8: 2026-11-12 14:54 to 11-13 08:07, 12 fallbacks, 97 repaired
reports. No missing steps.

**Analysis (M4.T16 reduced, done).** `prereg_freeze.py --verify` OK; `study_analyze.py --prereg` → **confirmatory**, no
provenance problem; byte-identical on a second run. Judge: 900 notes, US$6.27. Hand-off with every number:
`evidence/M4/M4.T16/results_summary.md`.
- Median ATE (cm): B0 16.74, B1 1.23, B2 11.68, Opus 12.06, Qwen3.8 11.92, Gemma 4 69.33.
- **H1** (Holm): Opus HL −2.83 cm [−4.93, −0.75], Holm p 0.0025, **rejected**; Qwen3.8 −4.00 [−6.06, −1.85], 7.2e-5,
  **rejected**; both **not practical** (upper ends above −3 cm). Gemma 4 sign test, median +56.7 cm [+38.2, +79.2],
  **not rejected** (worse than dead reckoning on 29 of 30 seeds).
- **H2 not tested** (the serial gate needs every H1 rejected). Descriptively every arm is more than twice B1 on every
  seed (HL ratio to B1: 8.9, 8.6, 57).
- **H4:** Friedman p 5.4e-12, Kendall's W 0.865. Opus − Qwen3.8: HL +0.05 cm, 15 seeds tied, Holm p 0.022, driven by
  three seeds where Qwen3.8 was lower by 6-18 cm. Both are about 64-65 cm better than Gemma 4.
- Descriptive: Opus and Qwen3.8 reproduce the coded procedure B2 (within 1 cm on 28 and 26 of 30 seeds; B2 − B0 HL
  −2.74 cm, so Qwen3.8's extra about 1.3 cm comes from four departures that all helped). Rubric (Sol):
  0.955, 0.935, 0.407. Post-hoc check (`error_sources.txt`): Gemma 4's error builds up on the 54 % of steps it answers
  without tools (2.47 cm per step), plus 215 pose jumps with no successful fix. An independent decoder confirms it is
  not a parsing artefact. An independent adversarial review found no wrong statistic; its 11 wording and script fixes
  are applied.
- Figures: `report/figures/fig_study.*` (frozen, Type 3 fonts) and the TrueType `fig_study_log.*` and `fig_study_h1.*`
  (`evidence/M4/M4.T16/make_figures.py`).

**State.** `bm-qwen38` stopped after the analysis (restart: `bash course-project/tools/serve_qwen38.sh start`), and the
Gemma container stopped when its arm ended. Still running: the access point, `bm-micro-ros-agent` and `bm-cam-relay`.
The study data (`data/main/`, git-ignored, about 185 MB) is on the Spark, with a copy on the Mac. The Mac's
`caffeinate` (kept on until section 1 finished) was stopped.

**Next:** section 2 with Xiaohui: M1.T17 capture size, then M1.T7 calibration with the phone board. Section 5 (report
Results, M5.T14) can start from `results_summary.md` at any time.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-13: ran the judge, the verify and the analysis; wrote the post-hoc
check, the figures and this entry.

## 2026-11-10 — re-scope for the 2026-12-01 presentation; work list 0 and 1: pre-registered study frozen, held-out sweep RUNNING

**Scope (Xiaohui, 2026-11-09; plan/README.md §3.6 is the authority).** Xiaohui presents in Group 1 on
**2026-12-01**; slides, a demo recording (video), the report and the GitHub link are due then, 10 points each. Target:
done by **2026-11-25**. Standing rules: **R1** always sim-to-real (every real-car session rehearsed in kinsim first),
**R2** every real run recorded (video, rosbag, frames, agent traces, terminal, tape; task M3.T27). Roster: Claude Opus
5.5, Qwen3.8-Flash-Next (vLLM), Gemma 4 26B-A4B (Ollama). The Isaac twin, the project Pico firmware, the overhead
ground-truth camera, the request suite and the closed-loop sweeps are dropped (`dropped (cut line)` with a reason in each
status row); M1.T15 and M6.T1 are done. Xiaohui asked for sections 0 and 1 of the work list to run fully automatically,
with commits and pushes as needed, adversarial reviews where they matter, and decisions made by Claude after weighing
the options (2026-11-10).

**0.2 Spark working tree.** `~/Projects/en665715-beaconmind` on the Spark is now a git clone of this repository (it was a
tar copy inside the private course repo's clone, last synced 2026-10-11 to 10-19, so it lacked the URDF, plan and report
updates). The git-ignored `data/` was copied into the clone (`cp -a --update=none`; the old copy is kept). The host venv
`~/.venvs/beaconmind` was re-pointed at the clone (`pip install --no-deps -e`; it still imported the old copy).
`tools/sync_to_spark.sh` and `tools/pull_evidence.sh` were rewritten: both still pointed at the private repo, so a sync
would have pushed its stale leftovers. Normal path: commit, push, `git pull --ff-only` on the Spark.

**0.3 Car network: DONE (2026-11-10, about 02:30 CST).** Xiaohui ran `sudo … discussions/module9/tools/ap_net.sh up 11`
and powered the Pico (power bank) and the camera, motor battery OFF. `tools/car_net.sh status`: access point `car-ap` on
`wlP9s9` at 10.42.0.1 (channel 11; the Ethernet link, internet and Tailscale unchanged); car at 10.42.0.138, camera at
10.42.0.89 (`bm_cam-0.2`, OV3660, VGA q12, hmirror 1 saved, RSSI −48 to −56 dBm, no errors). micro-ROS agent started as
container **`bm-micro-ros-agent`** (`microros/micro-ros-agent:humble`, host network, UDP 8888): the Pico joined as
`/pico_fusion` with `/pico/cmd_vel`, `/pico/drive/status` (0), `/pico/imu/data` (50 Hz), `/pico/imu/std`,
`/pico/wheel_ticks` (layout 9) — the K2 family, and the access-point build `buildK2a_d485d7ab` (only that build points at
10.42.0.1). Read from `beaconmind-ros` with the UDP-only FastDDS profile. Camera relay `tools/camera_relay.py` running in
tmux **`bm-cam-relay`**: from a container, `/status` and a 640×480 capture (10.6 KB, 0.13 s) through
`http://172.17.0.1:18080`. **Left running:** the access point, `bm-micro-ros-agent`, `bm-cam-relay`; the car powered with
the motor battery off. The firmware boots armed after a normal power-up, so switch the motor battery on only with the
car on its stand or in the arena with a hand on the switch. No reflash is needed (see the decision below).

**1.1 Harness** (committed `35847cc`). `harness/replay.py` (provider-neutral loop), `harness/providers/openai_chat.py`
(vLLM, Ollama), `harness/providers/anthropic_messages.py` (the pilot's Opus loop; byte-identical requests),
`harness/anthropic_replay.py` (shim), `tools/replay_run.py` + `replay_run.sh`. Rules: the counters reset only on a claimed
full fix that one of the step's own `fix_pose` results supports from the harness's own prior (`verify_fix`); poses and
maps are scored as written and state violations are measured (`metrics/pilot.py` `state_violations`; AGENT-DESIGN D5 v3.4
note); model failures in a step (output cap 32,768 local / 64,000 Opus, 30 turns, context overflow) are counted fallbacks;
infrastructure failures stop the seed without writing the step; a resume under another configuration is refused. Found on
the live vLLM server: replayed reasoning renders only from a field named `reasoning` (`reasoning_content` is dropped; the
Module 4 harness's inline `<think>`, used for the M1.T15 latency runs, rendered after a second, empty think block). An
independent adversarial review found 13 issues (1 critical: timeouts shorter than a full generation, retried 7 times);
all fixed, log `evidence/M2/M2.T7/REVIEW.md`. Tests 110 passed in `beaconmind-ros`; a mutation check shows the new ones bite.

**1.2 Servers.** Qwen3.8: `tools/serve_qwen38.sh` (container `bm-qwen38`, the M1.T15 server with the same image,
arguments and environment, served as `nvidia/Qwen3.8-Flash-Next-NVFP4`; 127.0.0.1:8000). Gemma 4: first on a user-level
Ollama with 8 slots (`tools/serve_gemma4.sh`; the host's systemd Ollama has one slot, `n_seq_max = 1`, and its settings
need sudo) — one step took about 10 minutes with 8 seeds in parallel (about 41 hours for the sweep) — so it moved to
**vLLM with Google's official bf16 checkpoint** (`tools/serve_gemma4_vllm.sh`, container `bm-gemma4-vllm`, 127.0.0.1:8001,
`--tool-call-parser gemma4 --reasoning-parser gemma4`, snapshot 4d7ae498). On both servers replayed reasoning renders only
from a field named `reasoning` (checked with `/tokenize` + `/detokenize`; Ollama too). vLLM's gemma4 parser returns the
numbers inside untyped object arguments as strings; the harness now turns numeric strings in tool arguments into numbers
for every arm (`tools_d5.coerce_numeric_strings`). The two local servers cannot share the GPU (about 97 GB each).

**1.3 Throughput and gates** (dev seeds, all partial by decision; `data/main/gate/`). Qwen3.8 xhigh: about 125 tokens/s
aggregate at 8 requests (60-80 at 4), about 3-4.6 minutes a step at 8 seeds in parallel; 116 steps over seeds 1010-1017;
9 reports did not parse, 6 of them complete but for the final `}` or `"}` → **closing-character repair** for every arm
(at most 3 characters, counted; `tools_d5.parse_report_ex`), and each turn now logs vLLM's stop reason and the content's
tail. Gemma 4 on vLLM: about 91 tokens/s aggregate at 10 requests, about 4,000-7,000 output tokens and 450-800 s a step;
it often answers without calling any tool (a model behaviour the study measures). Decision: keep bf16 (no FP8).

**1.4 B1** (`2baa41a`, M2.T9 done). GTSAM iSAM2 with oracle association and online odometry-scale calibration; the
online estimate is scored. Dev seeds 1010-1019 at 2 % drift: median ATE B1 1.11 cm (2.09 without calibration), B2 13.01,
B0 15.60. Run on the held-out seeds 2000-2029 at the frozen commit (`data/main/b1/test/drift2/`, 0 batch mismatches).

**1.5-1.6 Pre-registration: FROZEN** (M4.T1 done). `evidence/M4/M4.T1/prereg.md` (n = 30 seeds 2000-2029 at 2 % drift,
K = 1; family 1: H1 per arm, ATE below dead reckoning, Holm; family 2: H2 per arm, ATE below twice B1, Holm, behind a
serial gate; exact signed-rank tests with ties and zeros handled exactly, sign test if |G1| > 1; Hodges-Lehmann
estimates; practical support needs the interval below -3 cm; 22 declared deviations from the report's plan; power table
from `tools/prereg_power.py`). `prereg.json` (commit `37f0be2`) froze commit `0f2f88eab99b`: 29 files, 30 logs, the servers
and packages, and the config tags claude-opus-5-5 `b003c274bbb8`, qwen38-flash-xhigh `488f835d69b5`, gemma4-26b
`9cad251b7f18`; `prereg_freeze.py --verify` printed OK on the Spark. Three independent adversarial reviews preceded it:
harness (13 findings, `evidence/M2/M2.T7/REVIEW.md`), B1 (9, `evidence/M2/M2.T9/REVIEW.md`), analysis and pre-registration
(14, `evidence/M4/M4.T1/REVIEW.md`); all verified and fixed; the new tests were mutation-checked. Analysis
`tools/study_analyze.py` (checks every run against prereg.json and labels the output exploratory on any mismatch),
statistics `metrics/stats.py`, judge `tools/study_judge.py`.

**1.7 Held-out sweep: RUNNING** (M4.T4 in progress). `tools/study_sweep.sh` in tmux on the Spark, launched 02:06 CST
from a clean checkout of `61ca2c7`: `bm-sweep-opus` (Claude Opus 5.5, 8 seeds at a time, cap US$250, expected about
US$150-160, about an hour) and `bm-sweep-local` (Gemma 4 on vLLM, 16 at a time, expected about 20-27 hours; then it
stops Gemma, starts Qwen3.8 and runs it, 8 at a time, expected about 19 hours). Each arm writes
`data/main/runs/drift2/<arm>/` and `<arm>.log`; one automatic resume after an infrastructure failure, as pre-registered.
The runs' config tags equal the frozen ones and `git_dirty` is 0.

**1.8 Next (after the sweep):** `study_judge.py` (Sol, 10 notes per seed and arm, cap US$25), then
`study_analyze.py --prereg course-project/evidence/M4/M4.T1/prereg.json` on the Spark host venv into
`evidence/M4/M4.T16/`, `prereg_freeze.py --verify` first. Then the report's Results (M5).

**Git.** Public repo pushed through `61ca2c7` (this entry follows). The Spark clone is a clean checkout; the earlier
tar-synced copies are in `git stash` there ("tar-synced working copies before the 2026-11-10 freeze"), all identical to
committed files. Private repo `6a7a88d`. `sync_to_spark.sh` is for uncommitted work only; `pull_evidence.sh` no longer
overwrites newer local files (it once replaced a newer `prereg.md`, restored).

**Decision (Xiaohui, 2026-11-10): no STBY resistor; the car's hardware stays unchanged** (Pico on the bank, motors on
the AA pack, jumper out, K2a firmware). Work list 2.1 / M3.T1 waived; the replacement procedures and the remaining risk
(about 1.5 s of floating driver inputs after a Pico reset; the firmware boots armed) are in plan §3.6 "Hardware
decision" and safety rule S5's note.

**Section 0 is complete** (0.3 done on 2026-11-10). Section 1 finishes with the sweep and the analysis.

**Decision (Xiaohui, 2026-11-10):** the closed-loop demo episodes (the simulation take and the car episodes, work list
3.5 and 4.3) use Claude Opus 5.5, not Qwen3.8: about 15 minutes an episode instead of 1-1.5 hours. **No reflash is
needed for the project:** the Pico keeps `buildK2a_d485d7ab` (K2 source, access-point build; moves are bounded on the host
over its `/pico/cmd_vel`, wheel ticks and `/pico/imu/data`, as in the 40 Module 9 runs) and the camera keeps `bm_cam-0.2`
(access-point build, brightness and saturation 0, hmirror 1 saved in NVS; capture size is set per session with
`/control`, calibration needs no firmware change). Reflash only if they had to leave the access point (house builds
`buildK2w_4b70a0f3`, `bm_cam_v02.house.bin`) or a check fails. Confirm the running Pico image when it joins (node
`/pico_fusion`).

**M1.T7 board (2026-11-10):** Xiaohui will show the checkerboard on their phone instead of printing it. `tools/make_checkerboard.py` drew `evidence/M1/M1.T7/board/checkerboard_12x5_2868x1320.png`: 13 × 6 squares (12 × 5 inner corners) of 165 px = 9.111 mm at the phone's native 2868 × 1320, 460 ppi. A copy is in the Mac's `~/Downloads`. The README there has the phone settings, the ruler check (118.4 ± 1.0 mm over 13 squares), the scaled distances, and a simulated OpenCV check. That check found the plan's fixed 11 × 11 `cornerSubPix` window wrong for this board (2.6–8.8 px RMS); size the window from the corner spacing instead. The M1.T7 plan note lists the changed steps. M1.T17 (capture size) still comes first.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: the re-scope text, the code, the runs and this entry.

## 2026-11-02 — camera color fixed; what the Module 9 real-robot session changed on the car

The Module 9 discussion (private course repo) ran the car for real on 2026-11-01 and 2026-11-02. It was not project work,
but it changed what is on the car. This entry overrides the older camera and Pico lines where they differ.

- **Camera color (this repo, source changed).** `firmware/esp32cam/bm_cam_v02/bm_cam_v02.ino` now sets brightness 0 and
  saturation 0, not Espressif's +1 and -2. In a bright, pale room the old values left a red ball at saturation 60, and the
  depth lab's detector needs 110. The peak saturation in the frame went from 73 to 121. `BM_FW` stays `bm_cam-0.2`. The
  chip runs this change: it was built and flashed from the Spark's copy, which differs from this file only in one header
  comment. Why it changed, and when to revisit it, is in `reference/hardware/esp32cam-notes.md`. The lab also lowered its own
  detector threshold to 80 (private repo), because at 110 only part of the ball passed. That threshold is not project code.
- **What this affects.** Images from before this date (`evidence/M1/M1.T6/`) used the old values. M1.T7 is still not done
  and there is still no `configs/camera.json`, so no calibration is lost. Do the M1.T7 calibration on the new values.
  AprilTag detection works on grayscale, so a color change should matter little, but this was not tested.
- **The chip's network changed.** The car and camera are on a private WPA2 network that the Spark's own Wi-Fi radio serves on
  2.4 GHz channel 11, at `10.42.0.1`, with no house mesh in the path. Pico image `~/fw_builds_m8/buildK2a_d485d7ab`, the K2
  source with new Wi-Fi settings. Camera at 10.42.0.89 so far, Pico at 10.42.0.138 so far. The Spark's internet is a USB-C
  tether to a phone. Parked soaks: 0 gaps over 0.5 s, against 32 to 45 on the house mesh that evening. One command gap in 40
  real runs. The camera's `wifi_config.h` on the Spark holds those settings, so a new build keeps them until it is changed.
- **Containers cannot open a connection to the access point's subnet.** A process on the Spark can. The Module 9 stack used
  a small TCP relay for the camera. Plan for that if `beaconmind-ros` needs the camera on this network.
- **For M3.T6 and the Pico port: the car veers on carpet.** At 0.30 m straight, the left wheel made about 70 to 74 % of the
  right wheel's counts, and the car turned 41° to 46° left, at each smallest duty tried from 0.25 to 0.46. The cause is not
  known. The old heading hold (gain 2, limit 0.5 rad/s) saturated. Gain 8, limit 1.2 rad/s gave about 4.5°. Turns of 45° on
  the same carpet measured 44.4° and 43.7°. Give the project's straight moves enough steering authority, and do not assume
  carpet behaves like the hard floor.
- **Depth did not transfer.** On carpet the depth model read almost flat past 1 m. A ball-size estimate tracked the tape
  within 2.6 % on fitted distances, which is not a held-out figure.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-02: changed the firmware source, the notes, and this entry. Xiaohui
Chen placed the car and measured the distances that these figures come from.

## 2026-10-29 (night) — M2.T4: URDF updated to the M1.T16 car (660 g, power bank, cables in the footprint)

Branch `urdf/m1t16-measured-mass` (PR into `main`), made in a separate worktree because another agent was working
on `main`. Record, run logs and review: `evidence/M2/M2.T4/2026-10-29-m1t16/README.md`. This entry replaces the
"URDF still the 2026-10-10 car" statements of the earlier 2026-10-29 entries below, and settles open item (5) of
the pilot entry below (the sweep-radius / cable decision: Xiaohui kept the cables and the footprint follows them).

- **Model now:** total mass **0.660 kg** (`car.json` `mass_kg`, from the new CSV
  `evidence/M1/M1.T9/measurements-2026-10-29-with-m1t16-mass.csv` through `write_car_json.py`); two-scale split
  58 / 602 g; whole-car centre of mass **0.010545 m** ahead of the axle (Xiaohui's middle value, ±0.0018 m with the
  assumed 20 mm caster trail; 8.8–11.2 mm from the readings alone); chassis 0.575 kg; a geometry-only `power_bank`
  box on `chassis_link` (x −85 to −15 mm, y ±35 mm, 17–42 mm above the floor). Unchanged: ride height
  30 / 46 / 43 mm, lens pose, camera rpy 0, IMU pose, wheels, caster, `chassis_height_m`.
- **Footprint (after 23:45 CDT):** Xiaohui read the camera cable 40 mm past the old 138 mm front-most point
  (178 mm ahead of the axle) and chose to keep both cables as they are and have the footprint follow them:
  `front_overhang_m` **0.178 ± 0.0058 m**, `rear_overhang_m` **0.148 m** (the Pico cable), `chassis_length_m`
  0.326 m, `sweep_radius_m` **0.178281 m** (front-most corners (0.178, ±0.010): the cable taken as wide as the board
  and centred, an assumption). The URDF draws both cables as envelope boxes (ends measured, cross-sections ASSUMED);
  the ESP32-CAM board box still ends at 138 mm. Design-value proposals recomputed (`done_range_m` about 0.628 m, turn
  clearance about 0.228 m) in `evidence/M1/M1.T9/derived-dv-proposals.md`; `configs/dv.json` not edited.
- **Agent decisions for Xiaohui to accept:** the gearbox boxes' rear end (a photo ESTIMATE, ±6 mm) moved from −16 to
  −15 mm so they do not share volume with the measured bank front face (whether the parts touch is not measured);
  the front cable box has a collider, so the simulated car's first front wall contact matches `front_overhang_m`;
  the rear cable is visual only (a rigid box hanging toward the floor would be a false floor contact), so the
  simulated first rear wall contact is the bank's rear face, 63 mm short of the footprint and of the planned kinsim
  body.
- **Checks:** `beaconmind-ros:humble` (throwaway `--network none` container on a scratch copy): colcon **24 tests,
  0 errors, 0 failures, 1 skipped** (no `camera.json`); `check_urdf` OK; TF unchanged (`base_link →
  camera_optical_frame` 0.120, 0, 0.0415 m); `gz sdf` 14.9 converts with no warnings, 0.660 kg. Unmodified `main`
  had 2 broken URDF tests after the public-repo move (stale `car.json` hash in `car_props.xacro`; the extras CSV path
  pointed into the private repo); both fixed. `beaconmind` pytest 65 passed, 1 skipped.
- **Review:** one round, four lenses (source fidelity, math and geometry, data chain and tests, ROS and simulator),
  plus a two-lens round on the cable and footprint change (fixed: front-cable collider, ±5.8 mm through a row-specific
  writer exception, a separate board-front row, width checks tied to the board's measured width, two-assumption wording).
  No critical finding; every number confirmed. Fixed: a guard and a test that the split and the total are one
  weighing (a later total without a new split used to pass), bank guards (rounding, completeness, measured rear
  underside), a `body_box` size guard, an inertia test, and comment accuracy (inertia box, Isaac massless-link
  warnings, self-collision sources, private-repo labels, the CSV's AI line).
- **Notes for M2.T16 (Isaac twin), in the xacro comments:** the caster lifts at about 2.2 m/s² forward acceleration
  (7.15 m/s² for the old model), so ramp wheel commands and log pitch; the bank's rear-bottom edge is the first rear
  contact at about 11.8° nose-up, rear clearance 17 mm, and the bank collider needs a physics material; set
  self-collision off explicitly; importer 2.4.30 warns for the massless `base_link` and `camera_optical_frame`; with
  the caster sphere at the trailing contact the model's static caster load is 69.6 g against the 58 g weighed; the
  front cable collider needs a physics material too, and the front cable box will show at the bottom of the simulated
  camera image (compare the first rendered frame with a real one).
- **Open for Xiaohui:** the three agent decisions above; the cables' sideways position and width (the sweep radius
  assumes them) and a front photo of the camera cable's route; `configs/dv.json` against the recomputed proposals; the
  planned kinsim body's front corners (r = 0.193 m) lie outside the 0.178 m sweep radius (M2.T3); the bank alone (not
  weighed); re-weighing with the caster turned sideways would remove
  the ±1.8 mm. The plan's M2.T16 claim that `merge_fixed_joints = True` "would delete the camera frames" does not
  match importer 2.4.30 per the ROS reviewer (not re-run). The Spark's private-repo mirror predates the Module 6
  snapshot commit: `git pull` it before that lab is used again.
- **Status:** M2.T4 stays `blocked` (M1.T7 `camera.json`, M2.T3 `load_car`). M1.T16 stays `in-progress`.

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: this entry, the worktree and PR, the container and Gazebo runs,
and the review; the URDF/xacro edits were made by Claude Opus 5.5 at xhigh effort, as the 2026-10-06 rule asks.

## 2026-10-29 (night) — first-draft pilot run and report draft written

For the Class Project Report "First Draft with Experiments" (due 2026-11-03), Xiaohui delegated the work fully
("fully automate the process", 2026-10-29 22:37 CDT). Done this session:

- **Pilot code (public, tested):** `beaconmind/envs/kinsim_lite.py` (port of the Module 4 simulator with the M2.T3
  placeholder noise, seeded D3 worlds with 3 duplicated IDs, `odo_bias`), `harness/tools_d5.py`,
  `harness/anthropic_replay.py` (prompt caching, retries, budget cap, resume, fallback), `metrics/pilot.py` (C10.3
  map, C10.4 association, tool-call P/R/F1), `metrics/judge.py` (rubric and LLM judge with automated calibration),
  `tools/pilot_*.py`; `prompts/robot_system_prompt_v3.3.txt` published (Xiaohui's approval). `tests/test_pilot.py`
  24 passed (Mac and `beaconmind-ros`). Adversarial code review logged in `evidence/M4/M4.T11/CODE-REVIEW.md`.
- **Pilot run (Spark, 2026-10-29 22:53-23:32 CDT):** Claude Opus 5.5 in replay on dev seeds 1000-1004, kinsim only,
  two conditions: no drift (416 steps, US$31.19) and 2 % systematic odometry over-read (314 steps, US$23.92). All
  reports valid. Judges: GPT-6.1 Sol and Gemma 4 26B (Xiaohui's choice), calibrated without hand labels.
  Everything is in `evidence/M4/M4.T11/` (README, `pilot_summary.json`); raw logs stay in
  `data/pilot-20261029/` on the Spark.
- **Findings (pilot, not claims):** the agent executed the procedure almost exactly (same pose source on every step,
  same association decision for every detection, tool-call recall 1.00); its ATE tracked B2 within 0.5 cm; it lost
  to dead reckoning without drift and beat it on all 5 seeds with 2 % drift (mean -2.7 cm, below the 3 cm SESOI).
  A 100-seed baseline sweep puts the B2-over-B0 crossover between 0.5 and 1 % drift; B2's unimplemented branches stop
  1, 5 and 21 of 100 seeds at 2, 3 and 5 % drift.
- **Plan consequences:** odometry drift becomes a blocked factor and H1 moves to the 2 % block (report §IV-A);
  implement relocalization before larger drift; M2.T14 state correction still missing (counters reset on claimed
  fixes); the main study must test what the LLM adds beyond the procedure.
- **Report:** `report/Chen-Project-Report.tex` now has all eight sections; generated inputs `pilot_macros.tex`,
  `tab_pilot.tex`, `tab_judge.tex`, `fig_trace.tex`, `figures/fig_pilot.pdf`; hand-drafted `fig_architecture.tex`,
  `tab_tools.tex`. Build with `latexmk -pdf`. Plan rows M2.T3, M2.T7, M2.T8, M2.T10, M4.T11, M5.T1-T6 set to in-progress.
- **Judges:** evidence version 1 (tool results and report only) made Sol fail 21 of 730 notes, mostly for facts
  the agent had but the evidence lacked; version 2 (rules, observation, maps, full tool results) fails 1. Sol is the
  selected judge (all thresholds met); Gemma fails coverage (weighted kappa 0.41). Judge spend US$10.27.
- **Draft review:** one adversarial round (three reviewers), all findings verified and logged in
  `report/REVIEW-DRAFT.md`. PDF 11 pages, clean build.
- **Open for Xiaohui:** (1) commit and push the pilot code and evidence, or the report's repository link does not
  show it; (2) measure the camera tilt (inclinometer) so IV-B can state it; (3) the real arena floor; (4) the
  frontier-model sweep budget (the full K = 3 Opus design would cost about US$1,000); (5) the sweep-radius/cable
  decision from M1.T16.

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: wrote the pilot code, ran the pilot and the analysis, drafted
the report and this entry.

## 2026-10-29 (late) — M1.T16 measured: 660 g car, bank box, URDF may now be regenerated

Xiaohui measured the car as it is now. Evidence: `evidence/M1/M1.T16/measurements.md`, `confirm.md`, `photos/`.
M1.T16 is `in-progress` (bank alone, front camera cable and the sweep-radius decision are open).
This entry replaces the earlier "do not regenerate the URDF" rule: the mass and the bank are now measured.

- **Mass 0.660 kg** (was 0.506). Two-scale split 58 g front (caster) / 602 g drive wheels, caster not turned
  sideways. **Centre of mass 0.0105 m ahead of the axle** (middle value, ±0.0018 m; Xiaohui chose the middle value).
- **Power bank:** 70 × 70 × 25 mm lying flat under the plate at the breadboard end (the back), 3M double-sided
  tape. x −0.085 to −0.015 m, y centred (±0.035 m), z 0.017 to 0.042 m above the floor. It is now the lowest
  body point (17 mm). Model it as geometry only; its mass stays in the measured total (bank not weighed).
- **Ride height unchanged** (30 / 46 / 43 mm). Camera stand, BNO055, antenna, tyres, cells unchanged.
- **Open:** the rear Pico cable reaches 148 mm behind the axle, outside the 0.140 m sweep radius; the camera is
  now powered from the bank and its cable sticks out at the front (front-most point not measured). Do not change
  `sweep_radius_m` or the front overhang until Xiaohui settles these (reroute with right-angle plugs per
  AGENT-DESIGN §W, or enlarge the radius).
- **Next:** M2.T4 can update `car.json` (mass) and the URDF (mass, `com_x`, bank box) from these numbers.
  Earlier rule still in force: the URDF subagent is Claude Opus 5.5 at xhigh effort (2026-10-06 entry).

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: recorded Xiaohui's measurements, the checks and this entry.

## 2026-10-29 — status pass: K2, uncalibrated camera, URDF still the 2026-10-10 car

Full record: [`research/2026-10-29-urdf-firmware-camera-status.md`](research/2026-10-29-urdf-firmware-camera-status.md).
No URDF, `car.json`, firmware, or evidence file was changed. No new mass or intrinsics. The Pico chip was not re-read.
The 2026-10-24 "Hardware state now" bullets are history for that day; where they name Build J2 as the image on the car, this entry replaces them.

**Pico image the docs name.** Since 2026-10-25 the flashed image is Build K2, `~/fw_builds_m8/buildK2_bd46b95f` (AGENTS.md §7.4; `assignments/assignment8/review/FIRMWARE-REVIEW.md`). One-flash fallback is J2, `~/fw_builds_m7/buildJ2_b4298742`. J1 (`buildJ1_9849874a`) is the fallback the 2026-10-24 entry named for J2. K2 is open-loop duty, node `pico_fusion`, boots armed, `/pico/cmd_vel`, and publishes `sensor_msgs/Imu` on `/pico/imu/data` at 50 Hz. It is not the project firmware. `course-project/firmware/pico/` still has no sources (only `.gitkeep` files). Confirm the chip is still K2 before any port or flash.

**Firmware design (the plan, not a flashed image).** Xiaohui asked for a design and accepted a hybrid or a new firmware. Nothing already in `CONTEXT.md` or the plan had chosen an on-Pico EKF, so the plan now says:

- New BeaconMind firmware. K2 is the port source (M3.T23, still todo), not the image to keep. Contract C2 stays: bounded moves, boot disarmed, `/pico/arm`, `/estop`, heartbeat.
- Port K2's Wi-Fi supervisor, session supervisor, roaming, safety, deadman, stall cut-off, and K2's IMU behaviour. `WIFI_SESSION_TOLERANCE=1`, `WIFI_ROAM_MODE=1`. Never commit `wifi_config.h`.
- Close moves on the Pico: distance on encoder counts, turns and straight heading on the Pico's BNO055 yaw, with a coast lead measured on these motors (M3.T6). Do not stop a move on `/odometry/filtered`. Module 8's fused squares ended 17.5 cm from the start against 6.5 cm when steered by the wheels, because the host pose was the stop signal and the car coasted (`assignments/assignment8/Chen_Xiaohui_Module8_Sensor_Fusion_Lab.tex`).
- Wheel PID only if M3.T21 shows these motors can hold about 0.05 m/s. Until then, feed-forward plus count stops plus IMU-closed turns. If they cannot hold that speed, the 45°/s limit is a C0 change, not an EKF change. Sim gains do not transfer. The PID is not justified by a real-car run yet.
- Host `robot_localization` is a pose for logs and for the agent between moves (M3.T26). No on-Pico EKF: none was built, and the measured failure was the stop signal, not a missing on-Pico filter. Xiaohui can override that rejection.

**Camera.** `bm_cam-0.2` is flashed (2026-10-25), IP 192.168.5.49, boots VGA 640×480 quality 12. Saved `hmirror` is 1. The unflashed source default of 1 is sha `e95de293…`; the chip is `e4d483a8…` (`CONTEXT.md` entry of 2026-10-25). There is no `configs/camera.json` and no `evidence/M1/M1.T7/`. M1.T7 is not done. Module 8's vision demo is not a calibration. M1.T6 stays in-progress. The 2026-10-07 floor-picture pass was `bm_cam-0.1` at 192.168.4.24; that address is gone.

**URDF.** Still the 2026-10-10 car: total mass 0.506 kg, chassis leftover 0.421 kg, `com_x` from the two-scale split (caster 0.142 kg, drive wheels 0.364 kg, swivel x 0.120 m), inertia a uniform brick, no power-bank link. A new total weight does not fix the centre of mass. The bank in `reference/hardware/car-build-notes.md` (2026-10-20) is a black two-port block, 70 × 70 × 25 mm. Mass, capacity, output rating, port types, and mounting pose are unrecorded. No brand. The Module 8 overview photo shows USB leads leaving the robot; the bank body is outside the frame. M3.T20 stays todo: the split in use is not that trial.

**Not done, and not marked done.** M1.T7, M1.T6 (in-progress), M1.T8, M1.T9 (blocked; lens rows partial), M1.T12, M1.T13, M2.T4 (blocked), M2.T6, M2.T16, M3.T9, M3.T10, M3.T11, M3.T14, M3.T16, M3.T17, M3.T20, M3.T21, M3.T22, M3.T23. New and still todo: M1.T16 (mass and bank box), M1.T17 (capture size), M3.T25 (camera rejoin or a replug decision), M3.T26 (host EKF adapter). The coast lead is an addition to M3.T6, which stays todo.

**Open questions for Xiaohui.** Do not treat this entry as answering them.

- Bank make and model if printed; which of 70 / 70 / 25 mm is the height; where it is fixed; bank mass; whole-car mass; two-scale split; whether plugs or the bank stick out; whether the camera stand, BNO055, antenna, tyres, or cell type changed when the bank was added.
- Confirm the chip is still K2 before any port or flash.
- Capture size: UXGA quality 10 versus VGA quality 12, after a floor-spot `camera_probe.py --n 100`. Not chosen.
- For `camera.json`: `z_m` as floor height or axle height, and small mount angles or the full optical rotation. `CAMERA_CONVENTION_SETTLED` stays false.
- Whether the single 2026-10-10 lens readings (0.12 m forward, 0.0 m lateral, 0.075 m above the floor) are accepted until the stand is confirmed unmoved.
- Whether saved `hmirror` 1 is enough, or the unflashed binary whose source default is 1 should be flashed. Do not flash it from this note.
- Host EKF as pose-only is the working design. He can override the on-Pico option.

**Next.** Xiaohui: the open questions above, especially the bank measurements (M1.T16) and the capture-size probe (M1.T17), and a yes that the chip is still K2 before M3.T23. Do not regenerate the URDF. Do not flash.

AI-assisted: Grok 4.7 via Cursor, 2026-10-29: this status pass (this entry, the research note, and the plan status updates). Xiaohui Chen remains accountable for what he submits.

## 2026-10-25 — camera firmware bm_cam-0.2 built (one image for the Module 8 lab and the project); not flashed

**⚠ Flashing rule (read before touching the camera):** this ESP32-CAM boots only with the DOUT-mode bootloader at
0x1000 (`evidence/M1/M1.T6/dout-write.txt`; the DIO bootloader boot-loops, `serial-boot-dio-rst.txt`). Never use
`arduino-cli upload`, PlatformIO Upload (the Module 8 guide's Step 9.3) or a merged image. `flash.sh` now refuses.
Flash the app only: on the Spark, `bash firmware/esp32cam/build.sh bm_cam_v02`, Xiaohui holds IO0 and taps RST,
`bash firmware/esp32cam/flash_app.sh bm_cam_v02` (writes 0x10000 only, after checking the partition table's sha256
`aaae2888…`), then Xiaohui taps RST. Also in `reference/hardware/esp32cam-notes.md` §8 and AGENTS.md §7.4.

- **Why:** Xiaohui chose one firmware for the Module 8 camera-vision discussion (instructor lab guide 2, which expects
  the instructor's VGA sketch) and the project (M1.T6 contract). Research and the requirement sweep: the camera-vision
  sources are archived in `assignments/assignment8/sources/`, and the instructor's pristine firmware is in
  `assignments/assignment8/guide-original/firmware/esp32cam_camera/`.
- **What:** `firmware/esp32cam/bm_cam_v02/bm_cam_v02.ino` (fw `bm_cam-0.2`) = the instructor's sketch plus bm_cam-0.1's
  project contract. It boots at **VGA q12** (2 × 480,000 B PSRAM buffers, sized for UXGA). `/control` switches among
  4:3 sizes up to UXGA, quality 10-63 and vflip/hmirror; the frame size is not kept across a reboot, and
  `save=1` stores the orientation in NVS. Endpoints `/`, `/capture` (`?flash=1`), `/status`, `/led` (30 s auto-off),
  `/control`. `/capture` serves only a frame whose readout started after the request (driver `fb->timestamp`) and
  whose JPEG SOF size equals the mode. Headers `X-BM-Seq`, `X-BM-Capture-Us`, `X-BM-Frame-Us`, `X-BM-Uptime-Ms`,
  `X-BM-Width`, `X-BM-Height`. Serial: `BM_CAM READY ip=… rssi=… fw=bm_cam-0.2` and the guide's `Photo URL: …` every
  10 s. Wi-Fi: all-channel scan with the strongest node, power save off, the core's auto-reconnect, and a forced retry
  after 20 s down. The SSID is never printed. VFLIP default 0 (bm_cam-0.1 frames were upright with 0); mirroring
  is still to be tested with printed text on the preview page.
- **The 2026-10-06 project mode decision (UXGA q10) is unchanged.** Project tools must set it with
  `/control?framesize=uxga&quality=10` and check `X-BM-Width/Height`; `tools/camera_probe.py --mode uxga --quality 10`
  does (new flags, plus a `size_mismatch` count). The plan has dated notes in M1.T6 (box under "Why"; steps 9, 11, 12
  and 14; the step 14 `PATH` variable bug fixed), M1.T7 and M1.T12.
- **Checks run:** compiled on the Spark (`arduino-cli --warnings all`, FQBN `esp32:esp32:esp32cam:FlashFreq=40,FlashMode=dio`)
  with **0 warnings**; the build on the chip (with the merged-frame fix) is 1,026,585 B (32 %), app sha256 `e4d483a8…`
  (the first flashed build, without the fix, was `cf660bc1…`). The app image is valid (esptool image-info), and the partition table
  is byte-identical to the chip's. Host tests `firmware/esp32cam/tests/run_host_tests.sh` pass as C and C++ on the Mac
  and the Spark (JPEG size reader on two real UXGA frames, VGA/progressive SVGA/EXIF QVGA frames and a 700-byte
  truncation sweep; query and number parsers). `beaconmind` pytest 65 passed. `camera_probe.py` was run end to end
  against a local fake of the HTTP contract.
- **Review:** a 5-lens adversarial review with per-lens refutation confirmed 23 findings (0 critical, 2 major
  documentation findings, the rest minor or nits). The firmware fixes: LED auto-off race, rollback of a failed `/control`,
  strict query parsing, a bounded wait (`esp_camera_available_frames`, 1.5 s), split serial lines, a "Forget saved
  orientation" button, the partition guard pinned by sha256, and comment and provenance corrections. The two majors
  were the DOUT rule missing from the plan and docs, and project tools not setting the mode; both are now documented,
  and the probe sets the mode. An independent check of the fixes then confirmed them, and its 1 new minor finding (an
  empty query piece such as `a=1&&save=1` was allowed but its keys were missed) and 11 nits were fixed too: `/led`
  key check, a `fresh_timeouts` counter in `/status`, a `BM_CAM MODE` serial line every 10 s, a flash hold that does
  not restart the LED's auto-off timer, ordered rollback with clearer messages, and preview-page fixes. Not run on hardware: frame rate, freshness, FB-OVF at 480 KB buffers, the mirror
  test, and the Wi-Fi behaviour on the mesh.
- **Flashed the same evening (camera on the Spark's USB, Xiaohui doing IO0+RST and RST):** `flash_app.sh bm_cam_v02`
  twice, both `Hash of data verified`. The chip runs **bm_cam-0.2** at **192.168.5.49** (a new DHCP address; .24 is gone).
  The full boot log `evidence/M1/M1.T6/bm_cam_v02/serial-boot-3.txt` shows the DOUT bootloader, `Camera ready: OV3660,
  640 x 480 JPEG.`, the READY line every 10 s, no FB-OVF and no SSID. `/status` and three captures (640x480, all
  `X-BM-*` headers) are in the same folder. Malformed queries return 400. The size switch was checked both ways
  (VGA→UXGA→VGA, 0 size discards).
- **Found on the hardware: merged frames.** The driver sometimes leaves 2-6 frames in one buffer and trims it at the
  last EOI (5 of 40 VGA photos; a 126 KB buffer held a 19 KB image). This is very likely the old FB-OVF mystery: at
  SVGA with 96 KB buffers, merges overflowed. The second build sends only the first image (`bm_jpeg_first_image_len`,
  host-tested, including on the real merged files) and counts the rest (`merged_buffers` 21 of 60; no served photo
  held more than one image). The cause (a missed frame end) is open, and merged buffers still cost latency.
- **First rate data (desk, −48 to −59 dBm, not the floor spot):** VGA q12 request median 0.11-0.14 s, max 0.42 s; UXGA q10
  median 0.48 s, max 1.9 s, 219 KB per frame. At UXGA, the step 13 bar of ≥ 3 frames/s looks out of reach. Run the
  real `camera_probe.py --n 100` at the floor spot before the mode decision.
- **Mirror test done (M1.T6 step 12, phone showing "ABC 123", about 30 cm):** with hmirror 0 the text came out
  reversed, though upright. With `/control?hmirror=1` it read normally, so it was saved (`/control?save=1`), and after an
  RST `/status` still showed `vflip 0, hmirror 1, orientation saved` (uptime 11 s). Evidence (text-only crops; the full
  photos showed part of a person and were not kept): `assignments/assignment8/evidence/ball-test-2026-10-25/`. So
  the earlier "mirroring hint" (camera-quality.md) was right, and every bearing from older frames had the wrong sign.
  The source default is now `CAMERA_HMIRROR 1` (built with 0 warnings, sha `e95de293…`, **not flashed**: the chip runs
  `e4d483a8…`, built with 0, and its saved NVS value 1 gives the same picture). Redo the test if the module is remounted.
- **State:** `bm_cam/build/` on the Spark keeps the 0.1 app (`bm_cam.ino.bin`, sha256 `f724e0c4…`) as the one-flash
  fallback. The camera's USB stayed in the Spark. M1.T6 stays in-progress (the step 13 probes and the named
  acceptance files are still open).
- **Next:** `camera_probe.py --n 100` at the boot VGA and with `--mode uxga --quality 10` at the floor spot, plus
  the freshness test (M1.T6 step 13).
- **Not committed.**

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-10-25: researched the requirements, wrote bm_cam-0.2, its host test,
`flash_app.sh`, the `build.sh`/`flash.sh`/`camera_probe.py` changes and the plan and doc notes, ran the builds, tests
and the review, and wrote this entry.

## 2026-10-24 — car firmware lessons; plan revised

Full record: [`research/2026-10-24-car-firmware-lessons-and-pid.md`](research/2026-10-24-car-firmware-lessons-and-pid.md)
(F1–F11 below are its facts). **Read it before M3.T2, T3, T4, T6, T7, T14 and the four new tasks M3.T21–T24.** No
project task was run: the car work since 2026-10-19 was Assignment 7 (bench log
`assignments/assignment7/evidence/new-motor-bench-2026-10-20.md`), and this entry records what it changed for the
project. Line numbers are as of 2026-10-24.

**Hardware state now** (replaces the matching bullets of "Hardware state (as of 2026-10-05)" and of the 2026-10-11 entry). **Superseded for the flashed image on 2026-10-29:** the docs name Build K2, not J2. Read the 2026-10-29 entry. The bullets below are what was true on 2026-10-24.

- **Firmware on 2026-10-24: Assignment 7 Build J2** (`~/fw_builds_m7/buildJ2_b4298742.{uf2,elf}` on the Spark), flashed 2026-10-24. Not the image the docs name after 2026-10-25 (that is K2; see 2026-10-29).
  after five review rounds; it passed its T1 boot check, a 3-min floor check and a 20-min floor soak (bench log, the
  "Floor spot, J2" entry), and drove the first floor runs of the current motors (`m32a`-`m32c`). J1
  (`buildJ1_9849874a`) is the one-flash fallback. Both are the instructor's Module 7 guide code plus this car's Wi-Fi,
  session and safety layers (F1); J2 adds the chip's emergency roaming and the host's node choice. Node
  `pico_odometry`; best-effort `/pico/cmd_vel` in; `/pico/wheel_ticks`, `/pico/imu/heading`, `/pico/drive/status`
  out. Open loop: one duty map for both wheels, linear cap 0.30 m/s (`drive_control.c:37`, twice the project's 0.15),
  500 ms command timeout, a 600 ms deadman in a 10 ms timer interrupt that drops STBY, a stall cut-off. It is **not**
  the project firmware (no `/pico/arm`, `/estop`, latch, moves or boot id; C2), and it **boots armed** after a normal
  power-up (F11). Hardware watchdog 2 s driving / 8 s parked / 16 s while connecting (`safety.h:45-51`). The Module 6
  drive image of the 2026-10-11 entry is no longer on the Pico.
- **First floor runs of the current motors (2026-10-24, F6):** the left encoder's scale agrees with the compass within
  0.3 %; the car veers right 4-5° per 34 cm forward (right wheel 2.5-3 % slower) and goes straight in reverse; a
  commanded 45°/s turn ran at about 160°/s because the lowest duty this firmware sends moves each wheel about
  0.17 m/s. Both are inputs to M3.T21 (the wheel PID and the low-speed hold).
- **Agent restarts under J1:** quiet from 1.5 s of agent silence, motors stopped and disarmed from 3 s (re-arm
  needed), session rebuilt only after 20 s, on an IP change or when the agent is proven restarted
  (`pico_odometry.c:207,214,215`). On the bench a `docker restart` of the agent was rebuilt 7.7 s after the agent came
  back, with no reboot and no Wi-Fi rejoin (bench log, J1 T2b). So the 2026-10-05 bullet's "reboot the Pico after the
  agent restarts" does not apply to J1. The Assignment 7 agent is the `m7-micro-ros-agent` container (bench log stage 0).
- **Motors:** the left was replaced on 2026-10-22 (same blue 1:90 TT model). **Right #3** is a different model, a blue
  NULLLAB 1:90 TT "Low Noise & Hybrid Gear", fitted 2026-10-23 on the same cable, rows 25–26 and driver channel A. It is
  **lifted-tested only** (`m30a`: every wheel turned as commanded; at the same duty the right is 1–5 % slower than the
  left; both lose 7–8 % when driven together on the shared AA pack); its one floor run (`m31a`, Build I) stopped before
  any motion on a session rebuild. 3 of the 4 original-model motors failed within days (F6). Driver: the spare
  TB6612FNG board (HW-166) since 2026-10-19 (`reference/hardware/car-build-notes.md`).
- **Sides: channel A drives the RIGHT wheel** (IMU-verified 2026-10-11). **Encoders: left = `GP16`/`GP17`, right =
  `GP18`/`GP19`** (`encoders.h:9-15`), the opposite of the 2026-10-05 bullet and of the plan's old pin table. Nominal
  4,320 counts per wheel turn. The left encoder's two channels are not a clean quadrature pair, so the firmware counts
  its edges (**edge mode**, `encoders.h:20-30`); in floor pivots its scale agrees with the compass within about 0.3 %
  (`m32a`, 2026-10-24), re-checked with the project firmware in M3.T24. The right decodes plain x4 (about 1.6 % lost
  at duty 0.96).
- **PWM: the instructor's 1.2 kHz** (`tb6612.c:37-48`). A 20 kHz trial on 2026-10-17 cut Wi-Fi losses in pivots but
  was reverted (one wheel stuck in pivots, old motors, sagging pack); M3.T4 re-tests it before measuring the duty curve.
- **Power:** since 2026-10-20 the Pico runs from a two-port USB power bank on the car (the camera is meant for its
  second port but was unplugged for the Wi-Fi tests and has not streamed from the car); the AA pack (Energizer L91,
  fresh 2026-10-21) runs the motors only; the green AMS1117 wire is out (`car-build-notes.md`, "Decision 2026-10-20"
  and "Decision 2026-10-21"). The project's own power-bank trial is still M3.T20. **The STBY pull-down (S5) is still
  NOT fitted** (M3.T1); it protects the Assignment 7 firmware too, which can reboot itself with the battery on (F11).
  Measure the pack before each use (S8).
- **No hand-turning of the wheels since 2026-10-23 (Xiaohui).** Counts per turn and encoder signs come from powered
  runs (M3.T3: wheels up, a tape flag filmed in slow motion; M3.T24: the IMU on the floor).
- **The Pico:** not CPU-bound (about 12 % of one core; the second core unused), but its main loop blocks 0.6–2.2 s on
  the radio (F3). The project's PID, heartbeat watchdog and move executor therefore run on core 1 or a 10 ms
  repeating-timer interrupt, never only in the main loop.

**Wi-Fi, in two lines** (F2; `assignments/assignment7/evidence/wifi-survey-2026-10-23.md`; `floor_logs/ab_1024/`):
- The house mesh is 6 eero nodes, every 2.4 GHz radio on channel 6 (about 55 % busy); at the car's floor spot the
  network itself stalls for seconds (Spark→Pico ping p90 485–1845 ms, p99 2.5–11 s on 2026-10-23), and no firmware removes that.
- On J1 at the spot (2026-10-24, parked, listen only, no camera) the longest telemetry gap was 0.29 s and 1.10 s in two
  3-min runs and 1.28 s in a 20-min soak, never longer than the ping's own pause; the link **with the camera streaming
  and the wheels running** is not measured (M3.T22), and it decides whether a 500 ms watchdog and a 0.2 s STOP are reachable.

**Decisions by Xiaohui (2026-10-24, recorded in the research note):**
- (a) **The project may reuse the instructor's code**: the Module 5/6/7 guide firmware (`tb6612.c`, `encoders.c`,
  `bno055.c`, `picow_udp_transport.c`, `CMakeLists.txt`, `lwipopts.h`) and the Module 7 PID's `pid.c` /
  `wheel_control.c`, which exist only at `~/Downloads/pid-source-files.html` on the Mac until M3.T4 step 0 archives
  them. Reused code keeps a comment naming the instructor file; every part Claude changed keeps its AI disclosure.
  Upstream, tutorial and internet code is still never pasted (README L11).
- (b) Revise the plan from this research and add tasks such as PID tuning (below).
- (c) No hand-turning of the wheels (above).

**Plan changes made on 2026-10-24** (`plan/README.md`, `plan/M3-real-car.md`; list in the research note §5):
- **New tasks:** **M3.T21** Wheel-speed PID tuning on the stand: step responses, low-speed hold, battery range (needs
  M3.T4, M3.T1); **M3.T22** Link baseline at the floor spot with the camera streaming (Assignment 7 firmware as the
  instrument) (needs M1.T1; the camera arms need M1.T6 and the drive arms M3.T1); **M3.T23** Port the Assignment 7 link and safety layer into
  the project firmware (needs M3.T14; M3.T2 now needs it); **M3.T24** Floor re-tune of the wheel PID and the left
  encoder's scale (after the wheels-down gate) (needs M3.T7, M3.T20 and M3.T21; must finish before M3.T8).
- **New open decision OD21** (README §3.5): does a `link_lost` stop latch the episode on this link? Default: keep C5's
  auto-latch and set `watchdog_ms` from the M3.T22/M3.T7 data. Settled by Xiaohui after M3.T22.
- **Changed:** README L11 (the reuse rule), §7 S11 (the firmware's session supervisor rebuilds its session after an
  agent restart; reboot the Pico by hand only if `/bm_pico` has not reappeared within 30 s), §3.2–§3.4 and §9 (the new
  tasks); M3 §0.6 facts (encoder sides, motors, edge mode, 1.2 kHz, Build J1); M3.T2 (the 2 / 8 / 16 s watchdog
  pattern and the supervisor; control loops off the main loop); M3.T3 (powered counts per turn); M3.T4 (step 0 archives
  the instructor's PID; a 1.2 vs 20 kHz A/B before the curve; the PID at 100 Hz in the control context; the full tuning
  moved to M3.T21); M3.T5, T6, T14 (reuse wording); M3.T7 G0 takes M3.T22's baseline.
- **Suggested order** (research note §4): J2's floor A/B (Assignment 7) → M3.T1 → M3.T22 → M3.T14, M3.T23, M3.T2 →
  M3.T3, M3.T4, M3.T21, M3.T5, M3.T6, M3.T7 → M3.T24 → M3.T8. If time runs short: safety and the move executor
  first, then the IMU heading loop, then the wheel PID (§3).
- **`AGENTS.md` updated (Xiaohui's request, 2026-10-24):** §5 has the instructor-code exception (decision (a)) and a
  new rule, "Car firmware for labs — always carry the Wi-Fi fix": every later lab's Pico firmware is ported onto the
  current Build J2 instead of flashing the instructor's main as given; §2 points to the exception; §7.4 then recorded J2 on
  the car and that J1 and later rebuild their session after an agent restart. **As of 2026-10-29, AGENTS.md §7.4 records K2 (`buildK2_bd46b95f`) since 2026-10-25, with J2 as the one-flash fallback.** This paragraph is the 2026-10-24 edit, not the current image.

**Left running / not done.** No course-project task was run. Left running on the Spark: the Assignment 7 containers
`m7-micro-ros-agent` and `m7-gazebo` (the car's agent; `m7-gazebo` also holds UDP 8888, so stop both, with Xiaohui's
OK, before any project agent starts). The car that evening: Build J2 on the power bank, disarmed until the arm marker. The image name was superseded on 2026-10-29 (K2; chip not re-checked that day).
**Committed and pushed on 2026-10-24** together with the Assignment 7 Builds H to J2 work (see `git log`).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-10-24: wrote this entry from the research note, the Assignment 7
bench log, the Wi-Fi survey, `car-build-notes.md` and the firmware sources. The car work and the decisions are Xiaohui Chen's.

## 2026-10-06 — M1.T1 scaffolding done

M1.T1 is done. Evidence is `course-project/evidence/M1/M1.T1/`.

- **Venvs.** Mac: `course-project/.venv` (Python 3.13.7). Spark host: `~/.venvs/beaconmind` (Python 3.12.3).
- **Sync.** The Spark mirror of `course-project/` was updated with `course-project/tools/sync_to_spark.sh`. Spark-side evidence was pulled back in this session with `course-project/tools/pull_evidence.sh M1 M1.T1`. Pull again before the next Mac→Spark sync if the Spark has written anything newer.
- **gtsam.** `gtsam==4.3.0` is installed in the Spark cp312 venv (`pip-freeze-spark.txt` also lists `evo==1.37.1` and `statsmodels==0.15.0`). `import gtsam` succeeds. The module has no `__version__` attribute, so the task import line printed `gtsam imported`. `importlib.metadata.version("gtsam")` is `4.3.0`.
- **Pins on the Mac** in `beaconmind/pyproject.toml`: `pytest==9.1.1`, `jsonschema==4.26.0`, `gtsam==4.3.0`, `numpy==2.5.3`, `scipy==1.18.1`, `statsmodels==0.15.0`, `evo==1.37.1`, `matplotlib==3.11.2`. `providers` is still a lower bound. The Spark copy of `pyproject.toml` is still the pre-pin lower bounds, because the pins were written after the sync. The installed Spark packages are the pinned versions.
- **Tests.** `pytest-mac.txt` and `pytest-spark.txt` both end with `5 passed in 0.01s`.
- **Host C compiler present; firmware logic tests run on the Spark host.** `cc (Ubuntu 11.5.0-1ubuntu1~24.04.1) 11.5.0`, GNU Make 4.3 (`env-spark.txt`).
- **Left running.** Nothing from this task. tmux session `bm-m1t1` has finished. `rosa-ros2` and `vllm-rosa` are still exited. vLLM is not serving. No serial devices. Ethernet `192.168.5.1/22` is still on `enP7s7`. Scratch logs on the Spark home directory: `~/bm-m1t1-install.sh`, `~/bm-m1t1-install.log`, `~/bm-m1t1-pip.log`. Spark data directories exist under `course-project/data/` and are git-ignored. There is no `course-project/data/` on the Mac.
- **Git HEADs differ.** The editable-install lines record each clone's HEAD: Mac `c6abbd7`, Spark `82b0293`. The tar sync does not move either HEAD.
- **Next.** M1.T2 was not started.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, wrote the BeaconMind package skeleton, pytest scaffolding, sync and environment scripts, `pyproject.toml`, the `.gitignore` block, and this entry.

## 2026-10-05 — M0 closed: course fit settled

Confirmed by Xiaohui on 2026-10-05:

- **No Course Project Description exists or will arrive.** The documents in this folder are the
  full specification.
- **Individual project.** Xiaohui Chen is the sole participant and owner. The syllabus's
  Customer/Seller team structure does not apply.
- **The instructor accepted the direction change** to BeaconMind. The revised proposal and the
  Related Works & References PDF were both submitted to Canvas and received **full credit**.
- **Final deadline: 2026-12-13.** No dated schedule is kept, because Xiaohui decides when each
  milestone is carried out.
- **The task-level implementation plan is [`plan/`](plan/README.md):** milestones M1–M6, each
  broken into tasks with context, steps, deliverables and tests. Use it as the starting point for any
  implementation session.

## Direction chosen 2026-09-27 — history (feasibility and acceptance now settled)

Xiaohui chose to make the project **"LLM as SLAM"**: the car explores an **unknown** arena,
printed AprilTags act as **beacons**, and a language model keeps the pose belief and beacon
map, recognises revisits and chooses where to explore. The project **benchmarks many models**
(GPT-6 Astra/Sol/Luna, Claude Opus 5.5 and Fable 5.1, open-weight models on the Spark, and
navigation foundation models) in **Isaac Sim and the real world**. A 10-agent research workflow,
with every claim adversarially verified, found it **feasible with conditions, and novel at its core** (no
precedent for an LLM owning the SLAM decisions). The conditions are: a beacon map in a clear arena (no range sensor); stop-observe-think-act; detector
output rather than pixels for text models; aliased-beacon conditions; a classical GTSAM
reference. A three-lens adversarial review of the approach document followed; its 29 distinct findings
were confirmed and fixed.

- Approach: [`APPROACH-LLM-SLAM.md`](APPROACH-LLM-SLAM.md) — idea, feasibility verdict, the
  L0–L3 responsibility ladder, benchmark, model roster, cost, workstreams, risks.
- Evidence: [`research/2026-09-27-llm-slam-feasibility/`](research/2026-09-27-llm-slam-feasibility/README.md).
- **Status:** chosen by Xiaohui on 2026-09-27, contingent on feasibility, which the research
  supports with conditions. Still open:
  - ~~the revised D1 specifics for the Module 4 prompt assignment~~ — settled: D1–D10 were
    decided by Claude under Xiaohui's delegation in [`AGENT-DESIGN.md`](AGENT-DESIGN.md), now
    **v3.3**. The Module 4 prompt is built on it; Xiaohui's review was done on 2026-09-27;
  - ~~whether the instructor must accept a change from the 2026-09-14 proposal~~ — accepted
    (2026-10-05 note above);
  - ~~the team/role structure~~ — individual project (2026-10-05 note above).

  The known-map design below is kept as history.

## 2026-10-01 proposal revision (instructor feedback)

The 2026-09-14 submitted quad chart was the known-route "Landmark-Grounded Natural-Language
Mission Rover". The instructor accepted the technical direction and the listed outcomes /
conditions / metrics / targets, and asked for two revisions before updating the grade:

1. **Stronger problem motivation**, with evidence from prior work on language-conditioned
   planning, closed-loop verification, and embodied-agent failure modes — not an assumed gap.
2. **How the already-listed metrics will be applied**: how map-frame pose error is measured,
   how mission success is decided, and how unsafe or invalid actions are rejected.

The working deck is now **BeaconMind** (`Chen-Project-Proposal.pptx`, two slides):

- Slide 1 is still the instructor quad chart (problem, questions, approach/tools, system
  diagram, expected outcomes, participant). The problem statement now cites [1–14]; the
  outcomes quadrant now states how pose error, success, and refusal are applied, with
  targets scoped to replay vs. closed-loop vs. the car.
- Slide 2 is a backup "Two Content" slide: the cited finding for each source, and the
  measurement protocol. The official prompt asked for one slide; slide 1 stands alone if
  Canvas should receive only the quad chart.

Generator: `build_proposal.py`. Talk track: `proposal-talk-track.md`. Validator:
`validate_proposal.sh` (instructor template, not the canonical JHU theme). Fit check:
`check_render_fit.py` on the LibreOffice PDF.

Implementation that the slide may claim as done (the rest is planned):

- car wired and rails measured;
- Pico 2 W micro-ROS over Wi-Fi, instructor LED image only (no motor/encoder/IMU firmware);
- L2 geometry tools and rule-level simulator;
- RobotSystemPrompts v3.3, 80-run smoke test vs. a control
  (`assignments/assignment4/system-prompt/`);
- MCP `gate_detection` + episodic memory under ROSA, 19 tests pass
  (`discussions/module4/`).

Open items that still block a full project claim (instructor acceptance and the team question
were settled on 2026-10-05): Isaac Sim twin; Pico move firmware; camera stood upright and
calibrated.

## 2026-10-01 class project report — Related Works & References draft

The final report is an IEEE conference paper built from the instructor's `Class Project
Template.zip` (`conference_101719.tex`, IEEEtran class, `mybibfile.bib`). It lives in
[`report/`](report/REVIEW.md) and is built locally, not on Overleaf:
`cd course-project/report && latexmk -pdf Chen-Project-Report.tex`.

- **This milestone (10 points):** only Section II (Related Works) and the References are
  written; every other section is a one-line placeholder. Submit `report/Chen-Project-Report.pdf`
  (4 pages) to Canvas. **Submitted; full credit (confirmed 2026-10-05).** No due date was found on the assignment page or in the Module 5 lecture
  notes; check Canvas.
- **Content:** four strands (language-conditioned planning and closed-loop agents; language
  models in navigation, mapping and SLAM; limits of LLM spatial reasoning and the case for tools;
  fiducial SLAM and evaluation practice), each ending with how BeaconMind differs, plus Table I
  (who supplies pose and map in seven prior systems versus BeaconMind). 27 references, each
  checked against the paper and a publisher or arXiv record. PDFs are in `report/sources/`
  (git-ignored).
- **Review:** three adversarial rounds, logged in `report/REVIEW.md`. Round 1 caught that the
  draft described BeaconMind from `APPROACH-LLM-SLAM.md` where `AGENT-DESIGN.md` v3.3 supersedes
  it. **Describe BeaconMind from `AGENT-DESIGN.md` first.**
- **For Xiaohui to confirm** (the report words these as "proposed"): the refusal request suite,
  the coded per-step baseline (B2), true association for the GTSAM reference when IDs repeat,
  and L1/L3 as stretch arms. They are still only in `proposal-talk-track.md`.
- **Later sections** go into the same `.tex`. Section II is long for a final paper (about two
  pages) and can be cut when the other sections need the space.
- Committed in `37454f3`.

**Behavioural evidence (2026-09-27, Module 4 smoke tests; `assignments/assignment4/system-prompt/evidence/smoke-test.md`).**
- **Round 1** (the first final prompt, 16k window): 1 of 12 runs passed. With thinking off, the
  model skipped the tools; with thinking on, it mislabelled the duplicated tag.
- **Xiaohui's decision (v3.3):** add a duplicated-tag-id example (Example 3, with a simulated
  history) and raise the prompt budget instead of cutting rules (Claude set 4,500). The final is
  4,352 tokens.
- **Review fixes (five adversarial rounds):** a scan-bookkeeping rule (E2/E4 `scan_added`), a
  corrected smoke harness, and scenarios taken from a simulated history (`tools/backstory_sim.py`,
  `tools/build_scenarios.py`).
- **Round 2** (control against v3.3; 131,072 window; model-card sampling; 80 runs):
  - Thinking on: all checks passed in 8/20 against 3/20, and the duplicate was labelled correctly
    in 11/15 against 5/15. Neither is significant at K = 5 (p = 0.16 and 0.07).
  - Refusals did not improve.
  - Thinking off: 0/20 for both prompts, and v3.3 never called a tool (p = 0.02).
- **Design findings for W3:**
  - Thinking mode (or a stronger model) looks necessary for the L2 agent.
  - Raise K.
  - Loop closure practically never triggers in simulation of this arena with the current DVs (1.5 m
    revisit, E1 ending after two empty scans).
- **Server:** `vllm-rosa` runs Qwen3.5-35B-A3B at `--max-model-len 131072` (GPU share 0.60,
  `--max-num-seqs 4`). It is left running for the MCP-server work that follows Module 4.

Decisions made 2026-09-27:
- Simulator: **Isaac Sim, not Gazebo** (NVIDIA stack, career value). Isaac Sim 5.1 on the Spark
  is now an unsupported release; 6.0 went GA on 2026-06-08. Decide which to use in W1.
- **URDF and the Isaac Sim twin of the car get their own session** (workstream W1). No
  simulation runs until it exists. It needs physical measurements of the car, taken with the
  camera stood upright first.
- Frontier models are welcome in the project (they were excluded from the old model plan).

### Hardware state (as of 2026-10-05)

**Superseded.** The flashed image, the camera firmware, and what is still open are in the 2026-10-29 entry. This section is the 2026-10-05 snapshot. In particular, "stand the camera up, flash and calibrate it" is not the current camera state: bm_cam-0.2 is flashed and M1.T7 is still not done.

> **Superseded in part by the 2026-10-24 entry at the top** (firmware, motors, encoder sides, PWM, power path, the agent-restart rule); kept as history.

Sources: `reference/hardware/wiring-plan.md` §4, `pico-bringup.md`, `car-build-notes.md` (updates of
2026-10-01), `discussions/module5/DESIGN.md` §1 and §6 (floor sessions of 2026-10-04), AGENTS.md §7.4,
and a read-only check of spark-2a60 at 2026-10-05 23:30 CDT (`docker ps -a`, `ls /dev/ttyACM*`,
`ip -4 addr`). Safety rules for every task: `plan/README.md` §7.

- **Wiring.** The car is fully wired and was measured on 2026-09-20: left `+` = 5.03 V (buck), middle
  `+` = 3.3 V (Pico pin 36), right `+` = 6.67 V then (4×AA alkaline via the switch). **GPIO since
  2026-10-01:** `GP0` SDA, `GP1` SCL → BNO055; `GP2` PWMA, `GP3` AIN2, `GP4` AIN1, `GP5` STBY, **`GP10` BIN1,
  `GP11` BIN2, `GP12` PWMB** → TB6612FNG; `GP16`/`GP17` right encoder A/B; `GP18`/`GP19` left encoder A/B.
  Channel A = left wheel, B = right wheel **(the plan; contradicted 2026-10-11: on the car channel A drives the RIGHT
  wheel, and the encoder sides are unverified, see the 2026-10-11 entry)**. `GP6`–`GP8` are free. The submitted Assignment 3 diagram
  (`Chen-Assign3.fzz`) is out of date for the three moved wires (`wiring-plan.md` §4).
- **Superseded 2026-10-11: the Pico now runs the Module 6 sim-to-real drive firmware (see the 2026-10-11 entry).**
  Before that: **the instructor's Module 5 IMU-tilt image** (project name still `pico2w_led`,
  node `/pico2w_led`; UF2 sha256 `9e1725d4…f59314`; flashed 2026-10-01), no longer the LED-only image. It
  publishes `/pico/imu/pitch` (10 Hz), takes `/pico/tilt/request` (`1`/`-1` arm, `0` idle probe) and reports
  `/pico/tilt/status` (1–8). **Hazard:** once armed, a 2° tilt held 100 ms runs both wheels at 100 % PWM for
  10 s; an armed request never times out and there is no disarm message. The encoders are wired but this
  image does not read them. Build and flash: `assignments/assignment5/module-5-imu-tilt-control/spark-build.sh`
  and `spark-flash.sh`. There is still **no project firmware** (moves, encoders, watchdog).
- **Bring-up tests.** Closed: the BNO055 answers at `0x28` (chip ID `0xA0`), STBY goes high, and both
  channels run and reverse (2026-10-01). Still open: encoder quadrature direction per wheel, and counts
  per wheel revolution (nominal 4320 edges for both channels; the 1.5 s pulse test gave 4070–4520 edges for
  motor A and 4743–4917 for motor B, `assignments/assignment5/evidence/diagnostics/pintest-pulse-results.txt`).
- **Directions.** The tilt firmware's "forward" drives the **drive wheels first, camera end trailing**,
  which is the opposite of the project's +x (camera/caster end = front, AGENT-DESIGN D3). On the floor a
  10 s full-power run covered about 1.5–2 m (estimate) (`discussions/module5/DESIGN.md` §1). An arc toward the slower
  motor A was predicted there, not recorded; motor A turned out to be the RIGHT wheel (2026-10-11 entry), and the drift
  observed under the Module 6 drive firmware is a LEFT veer (research note F6). The BNO055's pitch axis lies along the car.
- **Dead right wheel (2026-10-01), fixed:** the TB6612FNG board was not fully seated, so its `BO2` pin
  (row 24) touched only under pressure. Pressing the board down fixed it. Watch item: if a wheel goes dead,
  press the driver board down first (`car-build-notes.md`).
- **Power.** Last recorded state (end of the Module 5 filming, 2026-10-04): **regulator path, `VSYS`
  jumper IN, USB out**, battery switch to be left OFF (Xiaohui was told; not confirmed). **Pull the jumper
  before any USB connection.** Checked 2026-10-05: no Pico on the Spark's USB (no `/dev/ttyACM*`). No
  STBY pull-down is fitted and no resistor or power bank is owned (2026-10-04); the Module 5 waiver does
  not carry over: the 4.7 kΩ pull-down is mandatory before any project wheels-down run (AGENT-DESIGN §W).
  Power-up order: Pico first, battery switch second.
- **Battery.** 6.67 V on 2026-09-20; 5.7–5.9 V at the driver on 2026-10-01; one Module 5 filming take
  ended because the pack died (`discussions/module5/DESIGN.md` step 3.2). Measure before the next use; replace below 5.5 V. The bent tray spring is
  still the first suspect for brownouts.
- **Camera unchanged:** ESP32-CAM with OV3660 on its own USB-C, taped **flat, looking at the ceiling**; it
  must be stood upright before any tag work. No project firmware; `esptool` and `arduino-cli` are absent on
  the Spark.
- **Wi-Fi.** The home mesh is lossy where the car drives: 31–52 of 60 status samples per 6 s at the start
  of the floor lane and 22 of 60 at its far end; one rehearsal lost the link mid-run
  (`discussions/module5/DESIGN.md` step 2.5). This matters for the watchdog period (W3).
- **micro-ROS agent policy (AGENTS.md §7.4, since 2026-10-01):** there is no standing agent container.
  Each session starts a fresh one (`docker run --rm -it --name pico-micro-ros-agent --network host
  microros/micro-ros-agent:humble udp4 --port 8888 -v6`) and removes it at the end. After the agent
  restarts, reboot the Pico (it cannot reconnect). Read the graph inside `rosa-ros2` and expect exactly one
  `/pico2w_led`; ghost nodes appear after Pico reboots under one agent. The firmware has the agent address
  `192.168.5.1:8888` compiled in; the Spark's Ethernet address was still `192.168.5.1` on 2026-10-05.
- **Containers on the Spark (2026-10-05 23:30 CDT):** `rosa-ros2` and `vllm-rosa` both **exited** (about
  41 h earlier, after the Module 5 session); no `pico-micro-ros-agent` container. `docker start vllm-rosa`
  restarts the server with its last arguments (Qwen3.5-35B-A3B, `--max-model-len 131072`, GPU share 0.60,
  `--max-num-seqs 4`). The project container `beaconmind-ros` does not exist yet (plan M1.T3).
- **Still open:** stand the camera up, flash and calibrate it (plan M1.T6–T8); car dimensions: measured
  2026-10-10 and written to `configs/car.json`, but single readings, no roll-out and no encoder counts (M1.T9,
  blocked on Xiaohui; see the 2026-10-10 entry at the end); the STBY pull-down and the power
  path (M3.T1); project move firmware with watchdog and stall detection (M3.T2–T7); encoder direction
  (M3.T3).
- **Watch items:** the tray spring; pack voltage; the driver board's seating; Wi-Fi range.

## 2026-09-14 design and status — everything below this line predates 2026-09-27 (history)

- Milestone: project-proposal quad chart.
- Decision: build a **landmark-grounded natural-language mission rover**.
- Student and project owner: **Xiaohui Chen**.
- Team arrangement: **individual project**.
- Hardware scope: **base kit only**; no additional electronic sensors are planned.
- Learning priority: balance robotics, perception, and agent reasoning.
- Model-serving direction: **vLLM on the DGX Spark**, with empirical model selection rather
  than a fixed Ollama model.
- Working proposal deck: `course-project/Chen-Project-Proposal.pptx`.
- Proposal review: passes validation against the instructor-supplied quad-chart template
  with documented geometry/custom-placement warnings; LibreOffice and Quick Look renders
  show no clipping. It is not canonical-JHU-template compliant because the instructor's
  required template has a different theme and layout signature.
- Implementation has not started. The immediate deliverable is the single-slide proposal.

## Proposal requirements

The supplied proposal description requires one completed PowerPoint quad-chart slide:

1. A specific problem statement explaining the task and why it matters.
2. Two or three project questions.
3. The approach and ROSA tools, including sensors, actuators, and any added hardware.
4. A system illustration showing inputs, processing, and outputs.
5. Expected demo behavior and measurable evaluation criteria.
6. The participant name and individual contribution.

Supplied source artifacts as of 2026-09-14:

- `/Users/xiaohuichen/Downloads/Project Proposal.epub`
- `/Users/xiaohuichen/Downloads/QuadChart-1.pptx`
- `/Users/xiaohuichen/Downloads/Module3_Hardware_Assembly_Wiring_Slides-1.pptx`

The proposal is explicitly a starting point rather than a binding final design.

## Selected project

### Working title

**Landmark-Grounded Natural-Language Mission Rover**

### Core idea

A user gives the rover a multi-step instruction such as:

> Go past the blue station, inspect station C, and return home by the shorter route.

The DGX Spark converts the instruction into a sequence of bounded ROSA tools. The physical
cart follows known safe routes, uses wheel encoders and the BNO055 for local motion
estimation, and uses printed AprilTags to identify destinations and correct accumulated
odometry drift. The agent verifies intermediate results and replans when an expected
landmark is absent or the rover reaches the wrong station.

### Why this project was selected

The project deliberately spans the course's major learning areas:

- differential-drive kinematics and closed-loop wheel control;
- encoder odometry, IMU integration, and localization error;
- camera calibration and fiducial-marker perception;
- ROS 2 topics, services/actions, TF, diagnostics, and failure handling;
- ReAct/ROSA planning, constrained tool invocation, memory, and replanning;
- local LLM/VLM inference on the DGX Spark;
- simulation-to-real transfer and quantitative embodied-agent evaluation.

It remains feasible for one student because the arena and routes are controlled and the
landmarks provide inexpensive, reproducible visual ground truth.

## Draft research questions

1. Does perception-conditioned replanning achieve a higher mission-success rate than a
   one-shot language-generated plan?
2. How much do BNO055 integration and AprilTag landmark corrections reduce final position
   and heading error relative to encoder odometry alone?
3. Which vLLM-served model provides the best valid-tool-call rate, mission success, and
   latency on the DGX Spark?

These are working questions for the proposal and may be narrowed after initial feasibility
tests.

## System boundary and architecture

### DGX Spark: stationary high-level computer

The DGX Spark remains off the cart and connected to its supplied AC power. It is responsible
for:

- ROS 2 Jazzy coordination for the physical robot;
- local LLM/VLM serving through vLLM;
- natural-language mission parsing and ROSA/ReAct planning;
- AprilTag detection and selected semantic image inspection;
- landmark registry, mission memory, and route selection;
- state estimation and high-level waypoint control;
- experiment logging, metrics, and report generation.

The DGX sends only validated, bounded motion goals or velocity setpoints. The LLM/VLM never
controls motor PWM and never belongs in the wheel-control feedback loop.

### Model-serving and selection strategy

Do not use `llama3.2` for the course project. Serve candidate models through vLLM and select
the final planning model from measured results rather than preference alone.

- vLLM's OpenAI-compatible API replaces the fixed Ollama path so the same ROSA-facing
  interface can benchmark several larger models already available on the DGX Spark.
- **Qwen3.5-35B-A3B** is the starting candidate because local vision input and tool calling
  have already been demonstrated on this Spark.
- **Qwen3.8-27B-FP8** and **Gemma 4-26B-A4B-it** are locally cached comparison candidates,
  but their vLLM compatibility, prompt behavior, tool use, latency, and memory use remain
  unverified for this project.
- Compare valid structured-tool-call rate, simulated mission success, p50/p95 latency,
  memory use, and failure categories before choosing the model for physical trials.
- Keep the model out of continuous control regardless of which candidate wins.

### Raspberry Pi Pico 2 W: cart-side real-time authority

The Pico is responsible for:

- Hall-encoder counting and wheel-speed estimation;
- fixed-rate left/right wheel PID;
- BNO055 sampling;
- TB6612FNG direction and PWM outputs;
- acceleration and command bounds;
- motor-disable, watchdog, and fail-stop behavior.

A stale command, lost connection, invalid command, reset, or software fault must stop the
motors locally without waiting for the DGX or LLM.

### ESP32-CAM: visual sensor

The ESP32-CAM sends compressed JPEG snapshots or a modest-rate MJPEG stream over Wi-Fi to a
DGX-side bridge. Images do not pass through the Pico. Conventional AprilTag detection runs
frequently; slower VLM observations are event-driven and never safety-critical.

### ROSA tool boundary

Candidate bounded tools are:

- `get_robot_state`
- `find_landmark`
- `navigate_to_landmark`
- `verify_arrival`
- `rotate_scan`
- `inspect_station`
- `mark_checkpoint`
- `choose_route`
- `return_home`
- `stop`

Each tool must validate arguments, operating state, speed and distance limits, timeout, and
result status. Continuous low-level control stays outside the agent.

### Agent prompt and ROS 2 interfaces

The agent prompt will provide:

- the mission role and safety boundary;
- the landmark registry and current robot state;
- the allowed tool schemas and argument constraints;
- an observe → verify → replan policy;
- explicit instructions to report uncertainty and stop after failed validation.

Planned ROS 2 interfaces include:

- `/odom` for fused or wheel odometry;
- `/imu/data` for BNO055-derived IMU data;
- `/camera/image/compressed` for DGX-side camera consumers;
- bounded `/cmd_vel` output from the validated motion layer;
- actions or services behind each ROSA tool with explicit success/failure results.

## Landmark plan

Use printed fiducial markers rather than additional electronic hardware.

- Preferred family: AprilTag `36h11`.
- Assign one unique tag to each station and one to the home location.
- Print on matte paper or cardstock with a white border.
- Mount each tag flat and rigidly on cardboard, foam board, or a wall near camera height.
- Measure each tag's physical side length and surveyed arena pose.
- Store a registry mapping tag ID to semantic name and map pose.
- Print a checkerboard or ChArUco target and calibrate the actual ESP32 camera.
- Measure the camera-to-robot mounting transform after final assembly.

Initial operation can use tag identity only for station confirmation. The advanced version
will estimate relative camera pose from the tag corners and use known landmark poses to
correct odometry.

Materials expected to be sufficient:

- printer access;
- matte paper or cardstock;
- cardboard or foam board;
- painter's tape or removable adhesive;
- ruler or measuring tape;
- printed camera-calibration target.

No additional electronic component is required for the selected landmark design.

## Arena and safety scope

The base kit has no verified range sensor. AprilTags provide localization but do not detect
obstacles. Therefore:

- operate at low speed in a supervised, controlled arena;
- use predefined clear lanes or a known waypoint graph;
- exclude people, pets, moving obstacles, stairs, and drop-offs from the test area;
- enforce conservative motion limits and a locally testable Pico watchdog;
- provide an immediately accessible motor-disable control;
- do not claim general autonomous navigation or dynamic obstacle avoidance.

Adding a ToF sensor, bumper, depth camera, or lidar is outside the currently selected
base-kit-only scope. If later added, update this document before relying on it.

## Planned evaluation

Primary metrics:

- complete mission success rate;
- correct waypoint and action order;
- final position and heading error;
- path length and path-efficiency/SPL-style score;
- number of replans;
- invalid or rejected tool-call rate;
- p50/p95 latency from mission command to accepted bounded tool;
- human interventions and categorized failure modes.

Planned comparisons:

- one-shot plan versus perception-conditioned replanning;
- encoder-only odometry versus encoder plus IMU;
- dead reckoning versus dead reckoning with landmark correction;
- Qwen3.5-35B-A3B versus Qwen3.8-27B-FP8 versus Gemma 4-26B-A4B-it, after each
  candidate passes basic serving and structured-tool-call gates;
- bounded ROSA tools versus a deliberately more permissive high-level interface.

Simulation should provide exact ground truth before the same conditions are tested in the
physical arena.

Preliminary proposal targets, not measured outcomes:

- at least 80% success over 30 held-out physical missions with the selected model;
- median final map-frame error no greater than 0.25 m and 15 degrees;
- cessation of the Pico's motor command within 0.5 seconds after communication loss.

## Known hardware and integration uncertainties

> **2026-09-27 note:** some items below are resolved or partly resolved; see the hardware state
> at the top. Item 1: the camera is an OV3660 (confirmed from the ribbon marking). Item 5: Wi-Fi
> micro-ROS works for the LED image (2026-09-23). Items 3 and 4 are partly resolved: the encoders
> run at 3.3 V, and the rails and the AMS1117 3.3 V output are measured. Items 2 and 6–8 are
> still open.

Do not produce final wiring or odometry constants until these are resolved:

1. The Module 3 slides identify an OV2640 camera, while prior repository notes identify an
   OV3660. Confirm the physical sensor and board markings.
2. The exact 1:90 Hall-encoder motor and the meaning of its stated `12 PPR` are unverified.
   Determine counts per output-shaft revolution experimentally or from the exact datasheet.
3. The encoder supply voltage, output type, motor stall current, and safe TB6612FNG loading
   require exact part identification.
4. AMS1117 devices are linear LDO regulators, not buck converters. Verify the actual power
   modules, battery chemistry, voltage range, thermal margin, and current capability.
5. Pico 2 W/RP2350 wireless micro-ROS transport is not yet proven in this environment.
   Validate it early; retain serial bring-up or a custom Pico-to-DGX UDP bridge as a fallback.
6. Magnetic interference from motors and wiring may degrade BNO055 heading. Measure this
   rather than assuming absolute heading is reliable.
7. Camera resolution, field of view, focus, frame rate, JPEG size, latency, and clock behavior
   must be measured on the actual ESP32-CAM assembly.
8. Qwen3.8-27B-FP8 and Gemma 4-26B-A4B-it are candidates, not proven project backends.
   Validate serving, structured tool calls, and ROSA compatibility before comparing quality.

## Immediate next steps

1. Review the drafted quad chart in PowerPoint when available and run its Accessibility
   Checker before submission.
2. Keep the generative-AI disclosure visible in the submitted slide.
3. Upload `course-project/Chen-Project-Proposal.pptx` to Canvas after personal review.
4. Confirm the physical labels and purchase details for the camera, motors, battery, and
   regulator modules.
5. Define a small candidate arena and landmark registry.
6. Prove AprilTag generation and detection against actual ESP32-CAM frames.
7. Prove the Pico communication path and fail-stop watchdog before free-wheel testing.
8. Build a simulation baseline before integrating the physical cart.

## Sources used in the decision

Retrieved 2026-09-14:

- NVIDIA, *DGX Spark User Guide — Hardware Overview*:
  <https://docs.nvidia.com/dgx/dgx-spark/hardware.html>
- Raspberry Pi, *Pico 2 W documentation*:
  <https://pip.raspberrypi.com/documents/RP-008304-DS>
- Toshiba, *TB6612FNG Datasheet*:
  <https://toshiba.semicon-storage.com/info/TB6612FNG_datasheet_en_20141001.pdf?did=10660&prodName=TB6612FNG>
- Bosch Sensortec, *BNO055 Datasheet*:
  <https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bno055-ds000.pdf>
- Espressif, *ESP32 Camera Driver*:
  <https://github.com/espressif/esp32-camera>
- AprilRobotics, *AprilTag*:
  <https://github.com/AprilRobotics/apriltag>
- OpenCV, *Detection of ArUco Markers*:
  <https://docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html>
- NASA JPL et al., *ROSA: A ROS Agent*:
  <https://arxiv.org/abs/2410.06472>
- Anderson et al., *On Evaluation of Embodied Navigation Agents*:
  <https://arxiv.org/abs/1807.06757>

## Generative-AI provenance

2026-09-27 update: Claude Opus 5.5 via Claude Code ran the LLM-as-SLAM feasibility research,
drafted `APPROACH-LLM-SLAM.md`, and wrote the direction-change and hardware-state sections
above. The direction itself is Xiaohui Chen's.

GPT-5.6 Sol in Cursor assisted with researching the supplied requirements and hardware,
comparing project concepts, and drafting this context record. Xiaohui Chen selected the
project direction and remains responsible for reviewing, understanding, and validating the
design before submission or implementation.

## 2026-10-06 — M1.T2 contracts

M1.T2 is done on the Mac and the Spark host. Evidence is `course-project/evidence/M1/M1.T2/`. The Python 3.10 run is deferred to M1.T14: M1.T3 was `in-progress`, not `done`, when this task finished, so `beaconmind-ros` was not used and T3 was not started.

- **Part A.** Vendored `l2_geometry.py` and `fewshot-numbers.json` under `beaconmind/tests/fixtures/reference/`. Their SHA-256 values match the task's expected hashes (`eb19b5d9…6e60243f`, `3f830176…1c3258`). Public repo, 2026-10-29: `l2_geometry.py` is not in this tree. It stays in the private course repo. `fewshot-numbers.json` is here, and `test_matches_reference_random` skips without the reference file. `configs/dv.json` has **66** keys in `values`: the 53 C0 keys, in C0 order, at the C0 values, plus 13 literals from `l2_geometry.py` (the 12 named in the task, plus `sector_unknown_leg_moves` = 1 from the `1 if wall is None` branch). `sigma_range_b_per_m` is unit `m/m` because the ordered unit rule matches `_per_m`; the step-2 table's unit column said `1`. Unused `SECTOR_BLOCK_*` constants were not added. `beaconmind.geometry` has no `import numpy`.
- **Part B.** Fourteen draft 2020-12 schemas, `python -m beaconmind.schemas`, `configs/providers.json`, and the seven contract fixtures. The schema CLI printed `OK` for `dv.json`, `providers.json`, and each fixture.
- **Tests.** Mac `pytest-mac.txt`: `37 passed in 0.37s`. Spark host Python 3.12.3 `pytest-spark.txt`: `37 passed in 0.28s`. Both are 0 failed. The plan's expected 31 is the scaffold (5) plus this task (5 + 8 + 13). The extra 6 are `tests/test_latency.py`, already in the tree from another task. The Mac venv check therefore printed more than the plan's `5 passed`, with 0 failed. `pytest-geometry-verbose.txt` names `test_matches_reference_random PASSED` and `test_example1_numbers PASSED`.
- **Schema CLI shell.** The task's `for` loop leaves `$f` unquoted. zsh does not split that into two arguments, so the first run only printed usage. The saved `schema-cli.txt` is the same loop run under bash, and every line is `OK`.
- **Name note, not a field change.** AGENT-DESIGN D5 logs a mismatch as `state_violation`. README C5 calls that code `state`. The run-log schema leaves `code` as a string, so this task did not pick one name and did not change a C0 value.
- **Left running.** Nothing from this task. No container was started. No hardware was touched.
- **Not committed.**

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, wrote `dv.json`, `providers.json`, `dv.py`, the geometry port, the JSON Schemas, the schema CLI, the contract tests and fixtures, the evidence files, and this entry. The geometry port keeps the reference disclosure from Claude Opus 5.5 (2026-09-27).

## 2026-10-06 — M1.T6 camera

M1.T6 is blocked after step 7. It is not done. Step 14 is pending. Evidence so far is `course-project/evidence/M1/M1.T6/` (`usb-and-load.txt` from the earlier identification, `toolchain.txt`, `camera-pins.txt`).

- **Last completed step.** Step 7. The AI-Thinker pin block was read from the pinned image's `camera_pins.h` and saved. Steps 8–15 were not done. The sketch, `build.sh`, and `flash.sh` were not written. The serial port was not opened.
- **Toolchain (step 6).** Spark image `bm-esp32-builder`. The Dockerfile is pinned to arduino-cli 1.5.2-rc.1 and `esp32:esp32@3.3.12`. The pinned rebuild printed `EXIT:0`. FQBN printed by the image: `esp32:esp32:esp32cam` (AI Thinker ESP32-CAM). Image id `sha256:a17e85dbf1c11c724dc8cd44bfeb1bd3b66b1bbab4c63934d4e3280080a419e4`.
- **USB.** Unchanged from the 19:13 CDT identification: FIREPHX `0843:5740`, driver `cdc_acm`, node `/dev/ttyACM0`, by-id `usb-FIREPHX_USB_SER_FX2348N-if00`. This session did not open that node.
- **Why upload stopped.** `arduino-cli board details -b esp32:esp32:esp32cam` lists six menus: CPUFreq, FlashFreq, FlashMode, PartitionScheme, DebugLevel, EraseFlash. None is a USB, CDC, or ACM choice, and none is a flash voltage. `boards.txt` has a fixed `upload.speed=460800`, `serial.disableDTR=true`, `serial.disableRTS=true`, and empty `upload.flags`. Those values were not passed to an upload. No baud and no flash voltage were selected.
- **HTTP.** No capture URL was requested. There is no status code.
- **Step 14.** Pending. No forward-view frames were saved, and `picture-quality.md` was not written.
- **Checked menu defaults, unused.** CPUFreq=240, FlashFreq=80, FlashMode=qio, PartitionScheme=huge_app, DebugLevel=none, EraseFlash=none. The QIO menu item in `boards.txt` sets `build.flash_mode=dio` and `build.boot=qio`. That line was read and not overridden. PSRAM is a build define (`-DBOARD_HAS_PSRAM`), not a menu.
- **Wi-Fi header.** Present and git-ignored. It was not printed and not compiled.
- **Tests.** Spark host Python has Pillow 11.3.0. Mac `course-project/.venv` ran `pytest course-project/beaconmind/tests/test_camera_probe.py`: `3 passed in 0.05s`.
- **Hardware.** Camera USB was left connected. The battery switch was already confirmed OFF and was not touched. Pico USB was already out. M1.T7 was not started.
- **Left running.** `vllm-rosa` was still serving after the pinned rebuild (`curl` to `http://127.0.0.1:8000/v1/models` returned HTTP 200). `beaconmind-ros` was still up. Isaac was not started. `rosa-ros2` was not stopped or started. tmux `bm-m1t6` is an idle shell after the image build. tmux `bm-m1t4` was not touched.
- **Not committed.**

Xiaohui's next decision is whether a later session may upload with the bare FQBN `esp32:esp32:esp32cam` and the core's own recipe, adding no baud flag and no flash-voltage flag. After `GET /capture` returns HTTP 200, put the car on the floor in its normal stance, battery switch OFF, flash LED off, and aim the lens forward so the lower part of the frame is the floor ahead. One of those frames needs a sharp high-contrast edge. Do not use the ceiling, a hand, a dark room, a page held against the lens, or the close wall from the LED freshness test.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, wrote the builder Dockerfile, the serial reader, the capture probe and its tests, the pin and toolchain notes, and this entry.

## 2026-10-06 — M1.T6 camera upload

The stop after step 7 was lifted. `esp32cam-notes.md` §5 and §8 agree with a bare `esp32:esp32:esp32cam` upload: firmware loads through the base board USB-C, and those notes do not set a baud or a flash voltage. M1.T6 is blocked on the upload. It is not done. Step 14 is pending.

- **Last completed work.** Steps 8–10. The sketch compiled. Step 11's upload did not. `arduino-cli` 1.5.2-rc.1 rejected a mount at `/src` (`Can't open sketch: main file missing from sketch: /src/src.ino`), so the sketch directory is mounted as `/src/bm_cam`. The FQBN stayed bare.
- **Size.** `Sketch uses 1026609 bytes (32%) of program storage space. Maximum is 3145728 bytes.` Globals `59312 bytes (18%)`. Saved in `evidence/M1/M1.T6/build-size.txt`.
- **USB before the upload.** `/dev/serial/by-id/usb-FIREPHX_USB_SER_FX2348N-if00` still pointed at `/dev/ttyACM0`, and `lsusb` still showed `0843:5740`. The same check passed again after the compile. The port was not opened until `flash.sh`.
- **Upload.** Did not succeed. esptool v5.3.1 on `/dev/ttyACM0` printed: `A fatal error occurred: Failed to connect to ESP32: Wrong boot mode detected (0x12)! The chip needs to be in download mode.` No baud flag and no flash-voltage flag were added. The serial monitor was not opened.
- **HTTP.** No capture URL was requested. There is no status code.
- **Step 14.** Pending.
- **Hardware.** Camera USB left connected. Battery switch was not turned on. Pico USB was not plugged in. The flash LED was not blinked.
- **Left running.** `vllm-rosa` answered `http://127.0.0.1:8000/v1/models` with HTTP 200 after the failed upload. `beaconmind-ros` was still up. Isaac was not started. `rosa-ros2` was not stopped or started. tmux `bm-m1t6` and `bm-m1t4` were left in place.
- **Not committed.**

Xiaohui: leave the battery switch off and leave the camera USB where it is. Hold the base board's `IO0` button, press and release `RST`, then release `IO0`. That is the download-mode step in `esp32cam-notes.md` §8. Say when that is done and the same bare-FQBN `flash.sh` can be retried. After `GET /capture` returns HTTP 200, aim the car on the floor, battery off, flash LED off, lens forward so the lower frame is the floor ahead, with one sharp high-contrast edge.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, wrote the camera sketch, `build.sh`, `flash.sh`, the size note, and this entry.

## 2026-10-06 — M1.T6 upload retry

The upload succeeded. M1.T6 is not done. Step 14 is pending. HTTP was not reached.

- **Upload.** `flash.sh` with bare FQBN `esp32:esp32:esp32cam`. The FIREPHX by-id link still resolved to `/dev/ttyACM0`, and `lsusb` still showed `0843:5740`. The port was not opened before esptool. esptool v5.3.1 printed `Hash of data verified.` and `Hard resetting via RTS pin...` `FLASH_EXIT:0`. The app image was 1026752 bytes written at `0x00010000`. Recorded in `evidence/M1/M1.T6/upload.txt`.
- **Serial.** `serial_read.py` for 30 s with `--esp32-reset` wrote `serial-boot.txt` at 0 bytes. Two later sniffs, without another RTS pulse, were also 0 bytes. No `BM_CAM READY` line, so there is no camera IP.
- **HTTP.** No URL was requested. There is no status code. A scan of `192.168.4.0/22` found no response body containing `bm_cam-0.1`.
- **Step 14.** Pending.
- **Left running.** `vllm-rosa` had answered `/v1/models` with HTTP 200 during this session. `beaconmind-ros` was not stopped. Isaac was not started. `rosa-ros2` was not stopped or started. Battery switch was not turned on.
- **Not committed.**

The flashed image is on the chip. The boot log did not come back over the FIREPHX serial port, so the rate and freshness probes did not run.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, recorded this upload result.

## 2026-10-06 — M1.T6 after RST

After RST alone, 20664 serial bytes arrived at 115200 with DTR and RTS held false. The log repeats `rst:0x10 (RTCWDT_RTC_RESET),boot:0x12 (SPI_FAST_FLASH_BOOT)` and contains no `BM_CAM READY`, no camera-probe line, no brownout line, and no IP. HTTP was not requested. Step 14 stays pending. M1.T6 is not done. `vllm-rosa` still returned HTTP 200. Saved as `evidence/M1/M1.T6/serial-boot-rst.txt`.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, recorded this boot log.

## 2026-10-06 — M1.T6 boot-loop cause

The 20,664-byte log is the ROM bootloader only: `mode:DIO, clock div:1`, then `load:0x3fff0030,len:4876`, then `load:0x07800040,len:4232256`, then `rst:0x10 (RTCWDT_RTC_RESET)`. The ELF has no 4 MB segment, and there is no Guru Meditation, brownout, or `BM_CAM` line. The flashed image was bare `esp32:esp32:esp32cam` with `CONFIG_SPIRAM=y` and `--flash-freq 80m`. `boards.txt` documents `FlashFreq=40`. `build.sh` and `flash.sh` now pass that option. Nothing was uploaded. No button yet.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, set the documented 40 MHz flash-frequency option.

## 2026-10-06 — M1.T6 40 MHz compile

`build.sh` compiled with `esp32:esp32:esp32cam:FlashFreq=40` and exited 0. The new `flash_args` line is `--flash-mode dio --flash-freq 40m --flash-size 4MB`. Sketch size is unchanged: `Sketch uses 1026609 bytes (32%) of program storage space.` The bootloader and app binaries differ from the 80 MHz copies that were flashed. `flash.sh` was not run. The serial port was not opened.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, recorded this compile.

## 2026-10-06 — M1.T6 40 MHz upload

The 40 MHz image uploaded. esptool printed `Hash of data verified.` and `Hard resetting via RTS pin...` The bootloader image header is `Flash freq: 40m`. The upload recipe passes `--flash-freq keep`, which leaves that header in place; `flash_args` still says `--flash-freq 40m`. A 25 s read at 115200 with DTR and RTS held false, and a second 20 s read the same way, both returned 0 bytes. That is not the `len:4232256` loop, and there is no `BM_CAM READY` line and no IP. HTTP was not requested. Step 14 stays pending. M1.T6 is not done. `vllm-rosa` still returned HTTP 200.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, recorded this upload.

## 2026-10-06 — M1.T6 40 MHz boot after RST

After RST alone, 20756 bytes arrived at 115200. The clock is now `mode:DIO, clock div:2`, and the loop is still `load:0x07800040,len:4242496` then `rst:0x10 (RTCWDT_RTC_RESET)`. No `BM_CAM READY`, no IP, no brownout. HTTP was not requested. Another flash frequency was not tried. Step 14 stays pending. M1.T6 is not done. `vllm-rosa` still returned HTTP 200.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, recorded this boot log.

## 2026-10-06 — M1.T6 image check

The 40 MHz files are coherent. Bootloader segment 0 is `0x3fff0030` length 4876, and segment 1 is `0x40078000` length `0x40bc` (16572). The ROM line `load:0x07800040,len:4242496` is that header read one byte early (`0x40bc40` = 4242496). The upload wrote `0x1000`, `0x8000`, `0xe000`, and `0x10000`, and esptool printed `Hash of data verified`. Flash mode in the image and in the log is DIO, which is what the default `FlashMode=qio` menu item sets. No button. Nothing was uploaded in this check.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, checked the image headers against the boot log.

## 2026-10-06 — M1.T6 DIO bootloader compile

`FlashMode=dio` selects `bootloader_dio_40m.elf` (`build.boot=dio`). The image on the chip used the default `FlashMode=qio`, which selects `bootloader_qio_40m.elf`. Both set `build.flash_mode=dio`. Rebuilt with `esp32:esp32:esp32cam:FlashFreq=40,FlashMode=dio`. `flash_args` is still `--flash-mode dio --flash-freq 40m --flash-size 4MB`. Sketch size `1026625` bytes. The new bootloader is 23520 bytes and is not the previous file. Upload has not run. The serial port was not opened.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, compiled the DIO bootloader image.

## 2026-10-06 — M1.T6 DIO upload

The staged bootloader was the 23520-byte DIO file, with `flash_args` `--flash-mode dio --flash-freq 40m`. esptool wrote it at `0x1000`, the partition table at `0x8000`, `boot_app0` at `0xe000`, and the app at `0x10000`, and printed `Hash of data verified`. A 20 s read at 115200 with DTR and RTS held false returned 0 bytes. No `BM_CAM READY`, no IP, no `0x07800040` line. HTTP was not requested. Step 14 stays pending. M1.T6 is not done. `vllm-rosa` still returned HTTP 200.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, recorded this upload.

## 2026-10-06 — M1.T6 DIO boot after RST

After RST alone, 19418 bytes arrived at 115200. The log repeats `mode:DIO, clock div:2`, `load:0x3fff0030,len:4640`, then `load:0x0780000b,len:4001856`, then `rst:0x10 (RTCWDT_RTC_RESET)`. That is the same failed second load. No `BM_CAM READY`, no IP, no brownout. HTTP was not requested. Another frequency or flash mode was not tried. Step 14 stays pending. M1.T6 is not done. `vllm-rosa` still returned HTTP 200.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, recorded this boot log.

## 2026-10-06 — M1.T4 latency

M1.T4 measurements are done. The OD8 proposal is not approved, so the task stays `in-progress`. Evidence is `course-project/evidence/M1/M1.T4/`. The JSONL files and the full probe log stay on the Spark at `course-project/data/latency/20261006-185238-*`.

- **Thinking on** (n = 20): p50 327.9 s, p95 555.7 s, max 761.5 s, n_all_pass 5.
- **Thinking off** (n = 20): p50 13.7 s, p95 18.8 s, max 18.9 s, n_all_pass 0.
- **Queue:** max_running 1, max_waiting 0 (3259 numeric samples, no waiting request).
- **Proposal, pending Xiaohui:** Qwen3.5 thinking on is replay-only, because p95 is above 60 s. Thinking off is inside 60 s but n_all_pass is 0, so it is not the closed-loop setting. Closed-loop runs and the demo use an API model chosen in M1.T11 and M1.T10. Any closed-loop episode that still uses this local model runs one at a time on `vllm-rosa` (`--max-num-seqs` was left at 4; the container was not recreated).
- **Left running.** `vllm-rosa` is serving `Qwen/Qwen3.5-35B-A3B`. `beaconmind-ros` was already up from another task and was not stopped. `rosa-ros2` was not started. tmux `bm-m1t4` has finished. `gpu-free.txt` is written. No frontier API was called.
- **Not committed.**

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, wrote the latency module, the summary and probe scripts, the OD8 proposal, and this entry.

## 2026-10-06 — M1.T15 local candidates

On 2026-10-06 Xiaohui rejected Qwen3.5-35B-A3B as the closed-loop model ("Qwen 3.5 performance is really bad and should not be used") and did not approve the OD8 API-model proposal. M1.T4 stays in-progress with the measured result (thinking-on p95 555.7 s, n_all_pass 5/20; thinking-off p95 18.8 s, n_all_pass 0/20; max_waiting 0; max_running 1). M1.T15 measures Qwen3.8-Flash-Next (`nvidia/Qwen3.8-Flash-Next-NVFP4`, not the cached `Qwen/Qwen3.8-27B-FP8`) and then Ternary Bonsai 2 27B, one model at a time, on the same Module 4 harness, with the same gate (p95 ≤ 60 s and n_all_pass > 0). OD8 stays unapproved until both runs exist. AI-assisted: Grok 4.7 via Cursor, 2026-10-06: added the two-model latency and pass measurement.

## 2026-10-06 — M1.T15 Bonsai speed

Ternary Bonsai `PTQ1_0` on the Prism CPU llama.cpp binary is not a fast decider. Stamp `20261006-221722`, thinking on: 0 decisions finished. The first prompt was 6103 tokens in 851.51 s (7.17 tok/s); generation was still going at 2799 tokens and 3.97 tok/s, with no tool call recorded. That `llama-server` and tmux `bm-m1-bonsai` were stopped at 22:43 CT. The on-disk CUDA llama.cpp (GB10, SM 12.1) rejects this file (ggml type 143). Prism publishes no Linux aarch64 CUDA build. M1.T15 stays in progress. OD8 stays unapproved. Note: `evidence/M1/M1.T15/bonsai-speed.md`. AI-assisted: Grok 4.7 via Cursor, 2026-10-06.

## 2026-10-06 — M1.T3 beaconmind-ros

M1.T3 is done. Evidence is `course-project/evidence/M1/M1.T3/`.

- **Container.** Image `beaconmind-ros:humble`, container `beaconmind-ros`, left running (`restart: "no"`). Start with `cd course-project/docker && docker compose up -d` on the Spark. Python 3.10.12. Fast DDS `2.6.12-1jammy.20260725.060440`. Pip in the image: openai 3.26.0, anthropic 1.11.0, jsonschema 4.26.0, pytest 9.1.1. `providers` in `pyproject.toml` is pinned to the openai and anthropic versions. The package is on `PYTHONPATH` (`/workspace/course-project/beaconmind/src`); there is no editable install in the container.
- **Graph.** `/chassis/odom` in the container at about 16.3 Hz, one Odometry message (`frame_id: odom`, `child_frame_id: base_link`). AprilTag id 3, family `tag36h11`, TF child frame `tag36h11:3` (README C1). One `ros2 node list -a` shows `/apriltag` and `/_Robots_Robot_0_transform_tree_odometry_ros2_publish_odometry`. The default `ros2 node list` hides that Isaac node because the name starts with `_`. `/chassis/odom` and `/apriltag/detections` were both in the topic list.
- **SHM litmus.** `ls /dev/shm | grep -c fastrtps_port` printed 72. Those files are dated Oct 3–4 and none were created during the launch. They were not deleted.
- **Python 3.10.** `pytest-py310.txt` ends with `11 passed in 0.01s` (scaffold tests plus `test_latency.py`, which were the tests on the Spark at that run).
- **Left running.** `beaconmind-ros` is up. `vllm-rosa` was left running (EngineCore still resident after `gpu-free.txt`). `rosa-ros2` was not started. Isaac `sim_server.py` was stopped. tmux `bm-m1t3` has finished. The Pico half of W0 is still M1.T13.
- **Not committed.**

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, wrote the Humble image, compose file, UDP profile, tag tools, `beaconmind_bringup`, the C1 frame line, and this entry.

## 2026-10-06 — M1.T6 desk pictures

The camera answered HTTP. M1.T6 is not done. Step 14 is not a pass: the robot was on a desk, and the lens was not aimed at the floor. Do not start M1.T7 from these frames.

- **HTTP.** From the Spark, `GET http://192.168.4.24/status` returned 200 (198 bytes, `bm_cam-0.1`, SVGA, `frames` 0). Three `GET /capture` calls, about one second apart, returned 200 with JPEG bodies of 31918, 33402, and 32071 bytes (`X-BM-Seq` 1, 2, 3). The flash LED was not commanded. The board was not reset and was not flashed.
- **Files.** Spark and Mac: `course-project/evidence/M1/M1.T6/pictures/capture-1.jpg`, `capture-2.jpg`, `capture-3.jpg`. Also on the Mac Desktop at `beaconmind-camera/`. Note: `pictures/desk-review.md`. Each frame shows a dark cabinet and a desk, soft focus, not a failure image. Floor-tag occlusion cannot be judged from these files.
- **Left running.** `vllm-rosa` and `beaconmind-ros` were not stopped.
- **Not committed.**

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, captured the desk JPEGs and wrote the picture note.

## 2026-10-06 — URDF subagent

The subagent that writes this URDF must be Claude Opus 5.5 at xhigh effort (Cursor model slug `claude-opus-5-5-xhigh`); do not use a different model for that task, as requested by Xiaohui on 2026-10-06. See M2.T4 in `plan/M2-sim-mvp.md`. AI-assisted: Grok 4.7 via Cursor, 2026-10-06: recorded the URDF subagent model.

## 2026-10-06 — Bonsai deferred to research

On 2026-10-06 at 23:58 CT Xiaohui made Bonsai a research action item only. Do not serve it, do not download more weights, and do not run llama.cpp. Ternary-Bonsai-2-27B was tried as `PTQ1_0` on Prism CPU llama.cpp (stamp `20261006-221722`): about 4 tok/s and 0 finished decisions. It is not a closed-loop candidate. The CUDA llama.cpp on the Spark cannot load ggml type 143. Future research may look for an aarch64 CUDA build that understands that type. Notes: `evidence/M1/M1.T15/bonsai-research.md` and `bonsai-speed.md`.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: recorded the Qwen3.8 pin, deferred Bonsai, and started M1.T5.

## 2026-10-06 — closed-loop model pinned

On 2026-10-06 at 23:58 CT Xiaohui pinned the closed-loop model. Their words: "pin the qwen 3.8 flash next". The served checkpoint is `nvidia/Qwen3.8-Flash-Next-NVFP4` (not `Qwen/Qwen3.8-27B-FP8`). Stamp `20261006-212041`, from `qwen38-flash-latency-summary.txt`: thinking-on p50 98.9 s, p95 164.5 s, max 198 s, n_all_pass 14/20 (S1 4/5, S2 4/5, S3 4/5, S4 2/5; mean 6.2 tool calls). Thinking-off p95 82.9 s, n_all_pass 0/20, 7 `turn cap` errors. The 60 s p95 gate was missed. Xiaohui is pinning this model anyway and will explore other models later. Thinking-on is the mode that produced the passes. Thinking-off is not usable. The Qwen 3.5 measurement in M1.T4 is unchanged. Evidence: `evidence/M1/M1.T15/od8-pin.md` and the decision section of `evidence/M1/M1.T4/od8-decision.md`.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: recorded the Qwen3.8 pin, deferred Bonsai, and started M1.T5.

## 2026-10-07 — M1.T6 floor pictures

The camera USB was unplugged. M1.T6 is not done. The step 14 floor check is a pass. Do not start M1.T7 until the rest of the M1.T6 acceptance items are met.

- **USB.** Spark `lsusb` at 2026-10-07T05:10:07Z had no `0843:5740`. The FIREPHX by-id link was absent. The serial port was not opened. Nothing was flashed, reset, or commanded on `/led`. No motor or tilt command was published. `vllm-rosa` and Isaac were not stopped.
- **HTTP.** `GET http://192.168.4.24/status` returned 200: UXGA 1600×1200, quality 10, `rssi_dbm` −67, `uptime_ms` 44856, `frames` 0. Saved on the Mac as `evidence/M1/M1.T6/floor-status.txt`.
- **Frames.** Three `GET /capture` calls, 2 s apart, HTTP 200, `X-BM-Seq` 1, 2, 3. `floor-1.jpg` 316572 bytes, `floor-2.jpg` 315379 bytes, `floor-3.jpg` 315347 bytes, each 1600×1200, `ffd8`…`ffd9`. Copies are on the Spark and the Mac under `evidence/M1/M1.T6/pictures/`, and on the Mac Desktop at `beaconmind-camera/`. Review: `pictures/floor-review.md`, last line `verdict: pass`. The board, USB lip, and ribbon do not cover the center or the lower-middle. One column edge falls about 120 gray levels in two pixels. No frame is a black or white clip.
- **Not committed.**

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-07, captured the floor JPEGs and wrote the review and this entry.

## 2026-10-07 — M1.T5 AprilTag spike, lifetime measured, OD7 awaiting approval

M1.T5 is not done. Xiaohui has not approved the Isaac version.

The kept Isaac 5.1 render is `data/renders/spike-20261007-001302` on the Spark (`READY 6.8`, `DONE`). UXGA 1600×1200, HFOV 60°, asset-server AprilTag MDL. Offline decode (`evidence/M1/M1.T5/detect-offline.csv`) got id 3 in 4 of 4 frames, ranges 0.5020 / 1.0032 / 1.5129 / 2.0340 m. `apriltag_ros` on the 1.0 m frame returned id 3 (`apriltag-ros-on-render.txt`). The launch and the publisher were stopped. Isaac 6.0 was not built; `v6.0.1` is in `isaac6-tags.txt`.

Kit lifetime (`evidence/M1/M1.T5/kit-lifetime.md`): both 900 s holds reached `DONE` with exit 0. Base kit: `READY 6.7`, last `ALIVE 906.7` (tmux `bm-m1t5-life` finished, log mtime 2026-10-07 00:30:49 -0500). ROS-bridge kit, Humble `rclpy`, UDP-only DDS: `READY 7.1`, last `ALIVE 907.1` (tmux `bm-m1t5-ros` finished, log mtime 2026-10-07 00:47:08 -0500). Self-kill was not reproduced in 900 s. Jazzy was not sourced.

OD7 proposes Isaac Sim 5.1.0-rc.19 for M2 (`od7-decision.md`). That file does not contain Xiaohui's approval. The status row stays `in-progress`.

- **Left running.** `beaconmind-ros` is up. `vllm-rosa` and `qwen38-flash` stayed exited. Nothing was `docker rm`'d. The ESP32 serial port was not opened. No Isaac kit was left running. tmux `bm-m1t11` was already present and was not used.
- **Not committed.**

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: recorded the Qwen3.8 pin, deferred Bonsai, and started M1.T5.
AI-assisted: Grok 4.7 via Cursor, 2026-10-07: finished both kit-lifetime runs and wrote the evidence notes. The model did not approve OD7.

## 2026-10-07 — OD7 Isaac 5.1 approved

On 2026-10-07 at 00:51 CT Xiaohui approved OD7. Their words: "Yes, keep 5.1 for the simulator work."

The approved version is Isaac Sim 5.1.0-rc.19 (`5.1.0-rc.19+main.0.aa503a9b.local`), already installed. Isaac 6.0 stays unbuilt.

M1.T5 is done. The acceptance items were already on disk: `mdl-parameters.txt` lists the MDL identifiers; `detect-offline.csv` has id 3 in 4 of 4 with each range within 5 percent; `apriltag-ros-on-render.txt` has id 3; `kit-lifetime.md` records both 900 s runs at `DONE` with exit 0 (launch-to-READY 6.7 s and 7.1 s). The approval is in `evidence/M1/M1.T5/od7-decision.md`. The status-row note is `OD7 approved 2026-10-07: Isaac Sim 5.1.0-rc.19`.

M2 was not started. Isaac 6.0 was not built. The camera and API keys were not touched.

- **Not committed.**

AI-assisted: Grok 4.7 via Cursor, 2026-10-07: recorded the Isaac 5.1 approval.

## 2026-10-07 — Python 3.10 tests

The deferred M1.T2 contract tests passed in `beaconmind-ros` on spark-2a60. Container Python is 3.10.12. The README L4 command was `docker exec beaconmind-ros bash -lc 'cd /workspace/course-project/beaconmind && python3 -m pytest -q'`. The log is `evidence/M1/M1.T2/pytest-py310.txt`. Its last line is `40 passed in 0.26s`. The container was already up, so the image was not rebuilt. `vllm-rosa` and `qwen38-flash` stayed exited. M1.T7, M1.T8, M1.T9, M1.T10, M1.T12, and M1.T13 were not started. The M1.T11 evidence folder, the secrets file, and the camera serial port were left alone. Nothing was committed.

AI-assisted: Grok 4.7 via Cursor, 2026-10-07: ran the deferred 3.10 tests.

## 2026-10-07 — M1 overnight sweep (no hardware, no API)

M1.T6 stays `in-progress`. UXGA HTTP capture, the floor-review `verdict: pass`, and the USB-unplugged check are already on disk. The level reading, the h/d ruler photo, and several named acceptance files are not. Gaps: `evidence/M1/M1.T6/overnight-gaps.md`. M1.T7 was not started.

M1.T11 moved from `todo` to `in-progress`. The K=1 quality note does not meet the acceptance list. The $5 cap was already lifted for that run. The budget-guard demonstration was never run, and it was not run in this sweep. Gaps: `evidence/M1/M1.T11/overnight-gaps.md`.

M1.T7, M1.T8, M1.T9, M1.T10, M1.T12, M1.T13, M1.T14, M1.T15, and M2 were not started. The camera, vLLM, Isaac, and the secrets file were not touched. Nothing was committed.

AI-assisted: Grok 4.7 via Cursor, 2026-10-07: checked the M1 acceptance lists against evidence already on disk and wrote the gap notes.

## 2026-10-07 — Opus 5.5 K=5 comparison

Xiaohui approved a 1-1 comparison of `claude-opus-5-5` against the Qwen3.8-Flash-Next thinking-on smoke (stamp `20261006-212041`). M1.T11 stays `in-progress`.

- **Run.** tmux `bm-m1t11-opus20` on spark-2a60, one client, 4 scenarios × K=5. Adaptive thinking (field omitted) and `output_config.effort=medium`. Exit 0 at 2026-10-07T01:31:13-05:00. vLLM was not started. The camera was not touched. `beaconmind-ros` stayed up. The one-off container `bm-opus20` was removed when the run exited.
- **Result.** n=20, p50 18.8 s, p95 21.8 s, max 22.2 s, n_all_pass 20/20 (S1–S4 each 5/5), mean tool calls 5.75, n_errors 0. Qwen thinking-on remains p50 98.9 s, p95 164.5 s, n_all_pass 14/20. Evidence: `evidence/M1/M1.T11/opus20-comparison.md`.
- **Not committed.**

AI-assisted: Grok 4.7 via Cursor, 2026-10-07: ran the 20-decision Opus comparison.

## 2026-10-10 — M1.T9 `car.json` and M2.T4 URDF generator (both blocked)

M1.T9 and M2.T4 are `blocked`, not done (plan README §1.2 step 4 and §1.4; first recorded as `in-progress`, corrected
after a review the same morning). M1.T9 is blocked on Xiaohui: the remaining work is bench work (§1.4 item 1) and
his decisions on the recorded deviations (§1.4 item 8). M2.T4 is blocked on its prerequisites M1.T7 (todo), M1.T9
(blocked) and M2.T3 (todo), and on the camera.json convention conflict below; its package was built ahead and runs.
Evidence: `evidence/M1/M1.T9/` and `evidence/M2/M2.T4/` (each has a `README.md`).

- **What was measured.** Xiaohui measured the car on 2026-10-10 for the Module 6 Gazebo lab (`assignments/assignment6/measurements.csv`, reviewed in `assignments/assignment6/review/MEASUREMENT-REVIEW.md`; unchanged copy `evidence/M1/M1.T9/measurements-xiaohui-chen-2026-10-10.csv`). One ruler/tape reading per quantity and a two-scale weighing. Key numbers: tyre diameter 67 mm (direct, unloaded, **not** a roll-out), tyre width 27 mm, track 133.5 mm wheel centre to wheel centre (outer 160 / inner 107), front overhang 138 mm (ESP32-CAM USB-C side, **no cable**), rear overhang 77 mm, body width 150 mm (the rear wing), main body height 36 mm, caster contact x 100 mm ("around"), caster diameter 25 mm, lens (120, 0) mm and 75 mm above the floor, BNO055 board centre (−61, +20 = robot LEFT) mm with its top 60 mm above the floor (26.5 mm above the axle), mass 506 g (142 g caster + 364 g drive wheels), sweep radius 0.140 m.
- **`configs/car.json`** (`bm.car/1`) is valid: `python -m beaconmind.schemas car ../configs/car.json` printed `OK ../configs/car.json (1 objects)`. It is written by `course-project/tools/write_car_json.py` from the evidence CSV and `evidence/M1/M1.T9/measured.json` (the `measured` block with the deviations); `beaconmind/tests/test_car_model.py::test_configs_car_json_is_the_writer_output` fails if `car.json` is edited by hand. Every value is `status: "measured"` with an uncertainty (2 mm ruler, 5 mm "around", 1 g per scale reading; at least 3 mm for every x measured from the axle line, review #15, so B1, B2, B3 `front_overhang_m`, B4 `rear_overhang_m` and S1 x `imu_x_m` carry 3 mm while the "around" rows keep 5 mm; 4 mm for B5b; root-sum-square for derived values; every rule constant is in SI units, so template rows typed in m or kg get the same uncertainty). `lens_z_m` is a height above the **floor** (M1.T7 step 8's camera `z_m`); `imu_z_m` is the board top above the **axle** midpoint, 0.0265 m (M1.T9 step 3: "from the axle midpoint"), derived from the 60 mm floor reading minus the 33.5 mm wheel radius. The URDF's `base_link` is at axle height. Omitted, not invented: `rollout_left_m`/`rollout_right_m`, per-wheel diameters, encoder counts, `imu_axes`. Blank template for the next measuring session: `course-project/tools/car_measurements_template.csv` (plan key names; the writer reads it, including an `imu_axes` text row).
- **M1.T9 still needs:** three readings per quantity (or Xiaohui accepting the single readings), the 5-revolution roll-out (or accepting the direct diameter), encoder counts per wheel revolution (postponed: they need the Pico; Xiaohui to confirm whether they move to M3.T3), the photos `car-top.jpg`, `car-side.jpg`, `imu-orientation.jpg` with nothing personal in frame (the lab photos show the desk and screens, so they were not copied), and `imu_axes`. **Two more decisions for Xiaohui** (README deviations 7 and 8): (7) `chassis_length_m`/`chassis_width_m`/`chassis_height_m` hold the main body (0.215 × 0.150 × 0.036 m), not the whole-car bounding box M1.T9 step 3 defines (0.160 m wide over the tyres, about 0.100 m tall to the camera-stand top), because the URDF body box and M2.T3's `body_width_m` use the body; this is also a plan inconsistency (M1.T9 vs M2.T3/M2.T4). (8) `corners` and `sweep_radius_m` (0.140 m, set by the plate-front corners) assume the ESP32-CAM and the plate's front strip are centred on y = 0; only their widths were measured. `derived-dv-proposals.md` proposes `done_range_m` 0.588 ± 0.003 m (placeholder 0.55) for M1.T10; `dv.json` was not changed.
- **URDF.** `ros2_ws/src/beaconmind_description/beaconmind_description/gen_props.py` writes `urdf/car_props.xacro` from `car.json` (and `camera.json` once it exists); never edit that file by hand. It reads `car.json` through `load_car_standin()`, a stand-in for the M2.T3 view `beaconmind.config.load_car`; when M2.T3 lands, switch `build_view()` to it. Geometry `car.json` does not carry (plate outline, part boxes, stand-in part masses, centre-of-mass inputs) is hand-written in `urdf/car_geometry_extras.xacro`. `beaconmind_car.urdf.xacro` includes both and stops if `chassis_height` disagrees with `battery_top_h − lowest_body_h`.
- **Expanded URDF unchanged.** `course-project/sim/isaac/assets/beaconmind_car.urdf` (xacro output, 17 KB, pulled back to the Mac). `evidence/M2/M2.T4/urdf_diff.txt`: 214 elements and 406 numbers compared with the pre-change expansion, 0 mismatches (only the main file's header comment changed); the Module 6 lab wrapper expands byte-identically before and after, so the lab's screenshots still match the model. Tool: `course-project/tools/urdf_compare.py`. Re-checked after the second review's fixes (`urdf_diff.txt` section E, 08:32): the description expansion is still byte-identical to `sim/isaac/assets/beaconmind_car.urdf` (`81a7d617…`) and numerically identical to the pre-change one; the lab wrapper expands byte-identically from the pre-session, previous and current package (`2cc877fb…` from one fixed path). After the third review's fixes (section F, 09:04; extras comments only): the description is still byte-identical (`81a7d617…`), and the lab wrapper, copied this time from the current `module-6-gazebo-sim/urdf/gazebo_car.urdf.xacro`, expands byte-identically from the pre-session, round-3 and current package (`92eff3de…`; 434 numbers, 0 mismatches).
- **Tests.** `colcon test` in `beaconmind-ros`: 18 passed, 1 skipped (`test_optical_frame_matches_camera_json`, no `camera.json`); `colcon test-result`: 19 tests, 0 errors, 0 failures, 1 skipped (same after the review fixes, 08:02 CDT). After the second review's fixes (08:33 CDT, domain 141; re-run 08:37 after the last file sync, same result): 19 passed, 1 skipped; 20 tests, 0 errors, 0 failures, 1 skipped. That round's new test, `test_gen_props_camera_labels_follow_the_extrinsics_used`, never skips (it writes its synthetic camera.json files in a temporary folder). The skipped test is `test_optical_frame_matches_camera_json`: it skips **only** while `configs/camera.json` is absent; once the file exists it compares the TF with the extrinsics (`z_m − wheel_radius`, full rpy) and **fails** until `CAMERA_CONVENTION_SETTLED` in `test/test_urdf.py` is set after Xiaohui settles the convention (checked with synthetic camera.json files: `evidence/M2/M2.T4/camera_json_test.txt`). After the third review's fixes (09:04 CDT, domain 141): 19 passed, 1 skipped; 20 tests, 0 errors, 0 failures, 1 skipped (`colcon_test.txt` (f)); with a calibrated synthetic camera.json, regenerated props and the flag set, the whole suite gives 19 passed, 1 skipped, the skip then being `test_optical_frame_pose_from_measurements` (`camera_json_test.txt` case 7). `beaconmind` pytest after the review fixes: Mac 53 passed; `beaconmind-ros` (Python 3.10) 53 passed; after the second review's fixes: Mac 55 passed, `beaconmind-ros` 55 passed; after the third review's fixes: the same 55 on both. TF smoke test: `tf2_echo base_link camera_optical_frame` = (0.120000, 0.000000, 0.041500) m, RPY (−90, 0, −90)° = the measured lens with the mount angles assumed 0 (no `camera.json`).
- **pytest plugin issue (container).** `beaconmind-ros` has pip pytest 9.1.1, which rejects Humble's `launch_testing` pytest plugin (`PluginValidationError … {'path'}`), so `colcon test` exactly as M2.T4 step 8 writes it gives `1 test, 1 error`. Run it as `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 colcon test --packages-select beaconmind_description`. The lasting fix belongs to the M1.T3 image (set the variable in the compose file or pin a pytest Humble's plugins accept); the image was not changed.
- **sdformat-12 material bug (from the Module 6 lab, kept in the shared URDF).** Gazebo Fortress's URDF-to-SDF step (sdformat 12) resolves a by-name `<material>` only for the first `<visual>` of a link, so later visuals turned black; every visual now carries its inline `<color>` (`test_every_visual_has_inline_colour`). Related: sdformat's converter drops `<gazebo reference>` friction for a link whose `<collision>` has a `name`, so the wheel and caster collisions stay unnamed.
- **Plan conflict for Xiaohui (README §1.4 item 8), before M1.T7 fills `camera.json`:** M1.T7 step 8 defines `extrinsics.z_m` as the lens height above the floor, but M2.T4 puts `base_link` at axle height and expects the TF z to equal `z_m` (33.5 mm apart). M1.T7 step 9 also records small mount angles where M2.T3 expects the full base_link → optical rotation. `gen_props.py` treats `z_m` as a floor height and refuses camera angles beyond ±20°. The `chassis_*` meaning (deviation 7 above) is the second plan inconsistency for Xiaohui.
- **Left running / Spark state.** Nothing from this task is running now. `robot_state_publisher` (domain 47, `ROS_LOCALHOST_ONLY=1`) was stopped at the end of the build. **Correction:** this entry first said "nothing new is running", but the end check (`pgrep -af "robot_state_publisher|tf2_echo|ros2 launch"`) missed the **ROS 2 CLI daemon** that step 9's `ros2` calls had started in `beaconmind-ros` at 07:34 (pid 1682, `ros2-daemon --ros-domain-id 47`, `ROS_LOCALHOST_ONLY=1`). A review found it; it was stopped at ~07:52 with `ros2 daemon stop` (same domain) and `docker exec beaconmind-ros pgrep -af ros2` then found nothing (`evidence/M2/M2.T4/daemon_stop.txt`). Dead entries remain: `tf2_echo` (pid 1645) and the stopped daemon (pid 1682) are `<defunct>`; the container's PID 1 is `sleep infinity`, which never reaps orphans (two older `python3` zombies, pids 313 and 919, predate this session). **Host daemon (update, second review):** a second `ros2-daemon` on the Spark host (pid 308295, domain 87, started 06:08 from `/tmp/bmcheck` by a host-Jazzy check of `beaconmind_description` from this Mac) was recorded as running at 07:52; it had **exited by about 08:15 CDT** (the reviewer's host `ps`), and a host check at 08:24 (`pgrep` for `ros2cli.daemon`/`ros2-daemon`: none; `/proc/308295` gone) confirmed no ros2 daemon on the host. Nothing to stop; the earlier "stop it" action is withdrawn (`evidence/M2/M2.T4/daemon_stop.txt`, update at the end). The only ROS-related host entry is pid 357075 `[tf2_echo] <defunct>`, the container's zombie 1645 seen from the host. Zombies use no CPU and hold no DDS participant; they go away when the container restarts. `init: true` in `course-project/docker/docker-compose.yml` would reap them (an M1.T3 image/compose change, not made here). `beaconmind-ros` was already up and stays up. colcon outputs are under `ros2_ws/build`, `install`, `log` (git-ignored). Spark-only scratch: `course-project/data/m2t4-lab/` (lab-wrapper comparison inputs and the guard test copy), `data/m2t4-round2/` (the review re-check: expansions, colcon output, the synthetic camera.json cases), `data/m2t4-round3/` (the second review's re-check: expansions, the lab-wrapper copy, colcon and pytest output), `data/m2t4-round4/` (the third review: synthetic inputs and their script, package copies per case, expansions, `before.txt`/`b2a.txt`/`after.txt`/`lab2.txt`) and `data/m2t4-description-launch.log`. The third review started no ROS node (xacro, colcon build/test and pytest only); its end check found no ROS process on the host and only the old zombie 1645 in the container. A stray `course-project/log/` made by a `colcon version-check` run from the container's working directory was removed. For about two minutes the Spark copy had a guard written with `abs`, which xacro does not provide, so xacro failed then; fixed to `math.fabs`. No hardware, Pico, camera, vLLM, Isaac or other container was touched.
- **Sync.** The changed paths were synced Mac → Spark with tar (sha256 identical on both sides); Spark-written evidence and the expanded URDF were pulled back with scp in this session.
- **Review fixes (same morning, ~07:50–08:10).** A review of this entry found seven defects; all were verified and fixed: the leftover daemon above; `imu_z_m` changed from floor height to axle-relative (`write_car_json.py`, `gen_props.py`; the expanded URDF is **byte-identical**, sha256 `81a7d617…`, and the Module 6 lab wrapper expands byte-identically from the original, previous and new package, `evidence/M2/M2.T4/urdf_diff.txt` section D); the `chassis_*` meaning recorded as deviation 7; the camera.json test given its comparison; statuses set to `blocked`; the missing step-2 template written; the writer's docstring and the B1/B2/B4 override text corrected and the corners' centring assumption named in `car.json` (`corners`/`sweep_radius_m` `source`) as deviation 8.
- **Second review (~08:20–08:40).** Six defects, all verified and fixed: (1) `write_car_json.py` multiplied its mm/g uncertainty overrides by the row's unit factor, so a template row typed in m or kg got an uncertainty 1000× too large (`car.json` was unaffected: the SI-unit fix alone rebuilt it byte-identical); the constants are now SI, and tests cover m/kg rows and compare the template build's uncertainties (three stated differences, all from the word "around" in the 2026-10-10 notes); (2) `gen_props.py` labelled the camera values "configs/camera.json extrinsics" whenever the file existed, even with null extrinsics (which M1.T7 writes until its step 8); `extrinsics_used()` now decides per x/y/z and per angles, with a test; (3) the 3 mm axle-datum floor now covers every axle-line row, so `front_overhang_m` and `imu_x_m` are ±0.003 m, `chassis_length_m` ±0.0042 m and `done_range_m` 0.588 ± 0.003 m (`car_props.xacro` changed in comments only); (4) the M2.T4 status row no longer calls the expanded URDF byte-identical to the pre-change one (numerically identical; the lab-wrapper expansion is the byte-identical one); (5) the host-daemon record above; (6) the Module 6 pointers below.
- **Third review (~08:55–09:10).** Four defects, all reproduced on the Spark in `beaconmind-ros` (scratch `data/m2t4-round4/`) and fixed: (1) `test_optical_frame_pose_from_measurements` always compared the optical frame with the 2026-10-10 ruler lens readings and required camera rpy 0, so the documented route to done (camera.json → `gen_props.py` → flag `True`) gave `1 failed, 19 passed`; it now leaves out the x/y/z and/or angles that `gen_props.extrinsics_used()` takes from camera.json and skips when all six come from it (`camera_json_test.txt` cases 6–9); (2) the measurement-based URDF tests read only `assignments/assignment6/measurements.csv` under its 2026-10-10 row names, so a `car.json` rebuilt from the template failed them (8 `KeyError`s; with a roll-out, 4 failures); they now read the CSV that `car.json`'s `evidence` fields name, through `write_car_json.read_csv` and `ROW_FOR_KEY`, with the roll-out diameter when both roll-outs exist, and the lever-rule test reads the extras' source CSV (`measurement_csv_test.txt`; CSV-derived expectations are compared within 2e-6 m, `MEAS_TOL`, because `car.json` and the xacro each round to 1 µm); (3) the URDF's departures from M2.T4 step 5 were not recorded (next bullet), and the `car_geometry_extras.xacro` comment credited the camera 10 g and IMU 5 g stand-ins to "project defaults, M2.T4" (they are the Module 6 guide's; comment-only fix, expansion byte-identical); (4) the "Tests." bullet named the wrong test as the one that skips (reworded above). Found on the way: the Spark's mirror of `assignments/assignment6/lab-step10/gazebo_car.urdf.xacro` is older than the Mac's (its header AI note only), and sections B, D2 and E2 of `urdf_diff.txt` expanded that copy; same model (`urdf_diff.txt` F3). It was not re-synced, because the lab files are outside this task.
- **URDF deviations from M2.T4 step 5, for Xiaohui (`evidence/M2/M2.T4/README.md`; kept as they are so the Module 6 lab's model does not change):** (1) `chassis_link` is 12 boxes at the measured heights (gearbox bottoms 3.5 mm below the axle, plate 11–14 mm above it, camera stand up to 66.5 mm), not one `body_width` × `chassis_height` box with its bottom at the axle; (2) chassis mass 0.421 kg, not step 5's 0.436 kg, because the camera (10 g) and IMU (5 g) stand-ins sit on their own links, with a 0.208 × 0.100 × 0.036 m inertia box at the chassis centre of mass that gives the whole car the lever-rule centre of mass; (3) `camera_link` and `imu_link` carry those inertials (Module 6 guide defaults; step 5 gives none); (4) wheel joints rpy (−π/2, 0, 0) with axis 0 0 1 (the same +y spin axis as step 5's axis 0 1 0); (5) sphere wheel collisions (Module 6 guide §5.1); (6) visual-only caster fork and camera-module boxes. The total mass, the C1 frames and every joint position are as step 5 says.
- **Module 6 lab note: stale pointers to `car_props.xacro` (not edited).** Splitting the hand-written props moved the reviewed plate outline, part boxes, part masses and the centre-of-mass inputs (`caster_swivel_x` 0.120 from C3, `caster_load` 142 g, `com_x`) into the hand-written `car_geometry_extras.xacro`; `car_props.xacro` is now generated from `car.json`. `assignments/assignment6/derived-values.md` line 3 ("Superseded … by the reviewed values in `…/car_props.xacro` (… COM x 33.7 mm from the 120 mm pivot, the 151 mm wing reading is not used)") and the header comment (line 14, "through car_props.xacro") of `assignments/assignment6/lab-step10/gazebo_car.urdf.xacro` and its copy `module-6-gazebo-sim/urdf/gazebo_car.urdf.xacro` (identical on the Mac; the Spark's `lab-step10` mirror is older by its header AI note) still point at `car_props.xacro` alone. They are lab deliverables, so they were not changed; Xiaohui (or the lab owner) should make them read "car_props.xacro (generated from car.json) + car_geometry_extras.xacro (hand-written)". The wrapper's line 105 (wheel_separation/wheel_radius from car_props.xacro) is still right, and comment edits do not change the expanded model. Details: `evidence/M2/M2.T4/README.md`.
- **Next.** Xiaohui: decide deviations 1–3, 7 and 8 (`evidence/M1/M1.T9/README.md`), the six M2.T4 step-5 deviations above (accept, or have the plan text changed) and the camera.json `z_m`/angle convention; fix the two Module 6 pointers above if the lab files are edited again. M1.T7 calibration at the bench, with all six extrinsics in `camera.json`, then `gen_props.py` again and set `CAMERA_CONVENTION_SETTLED` per the decision; colcon should then give `20 tests, 0 errors, 0 failures, 1 skipped`, the skip being `test_optical_frame_pose_from_measurements` (with the flag still `False`, or with null angles, `test_optical_frame_matches_camera_json` fails by design). The rest of M1.T9 at the bench with the template: keep the filled CSV in `evidence/M1/M1.T9/` (`car.json` names it and `test_urdf.py` reads it from there; no test edit needed), run `write_car_json.py` and `gen_props.py`, and **hand-edit `car_geometry_extras.xacro` in the same session** for every re-measured row it uses (list in the M2.T4 README; only B9/B10 and a new total mass are caught by a check). M2.T3 (`load_car`).
- **Not committed.**

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-10-10: wrote `car_model.py`, `write_car_json.py`, `test_car_model.py`, `gen_props.py`, `car_geometry_extras.xacro` (moved the reviewed values and comments), the edits to `beaconmind_car.urdf.xacro` and `test_urdf.py`, `urdf_compare.py`, generated `configs/car.json` and `car_props.xacro`, ran the M2.T4 steps, and wrote the evidence notes and this entry; later the same morning applied the review fixes listed above (including `tools/car_measurements_template.csv`) and re-ran the checks; then applied the second review's fixes (SI uncertainty constants and the axle-datum floor in `write_car_json.py`, `extrinsics_used()` in `gen_props.py`, their tests, the regenerated `car.json`/`car_props.xacro`/`derived.txt`, the evidence and plan-row corrections) and re-ran the writer, the schema check, both pytest suites, colcon and the before/after expansions; then applied the third review's fixes (`test_urdf.py`: the camera parts taken from camera.json left out of the measured-pose test, and the measurement tests reading the CSV `car.json` names through `write_car_json.py`'s reader; the stand-in-mass comments of `car_geometry_extras.xacro`; the step-5 deviation list; the template's keep-the-copy note; `measurement_csv_test.txt`, `camera_json_test.txt` cases 6–9, `colcon_test.txt` (f), `urdf_diff.txt` F) and re-ran colcon, both pytest suites and the expansions. The measurements are Xiaohui Chen's.

## 2026-10-11 — Module 6 sim-to-real drive lessons (read before M3.T3, M3.T4, M3.T8, and the twin's actuator model)

Full record: [`research/2026-10-11-sim-to-real-drive-lessons.md`](research/2026-10-11-sim-to-real-drive-lessons.md)
(sources: `discussions/module6/`, the agent logs in `assignments/assignment6/module-6-gazebo-sim/sim-to-real/logs/`).

- **Pico firmware now:** the instructor's Module 6 drive image (`/pico2w_drive`: `/pico/cmd_vel` in;
  `/pico/imu/heading`, `/pico/imu/pitch`, `/pico/drive/status` out; 0.5 s command timeout; encoders not read) with
  two changes in `drive_control.c`: the wheel remap `tb6612_set(-right_duty, -left_duty)` and calibrated constants
  `MIN_DUTY 0.36`, `MAX_WHEEL_SPEED_MPS 0.20`, `WHEEL_SEPARATION_M 0.134` (consistent fit 0.39/0.215; slip documented).
  Its micro-ROS Agent ran as the `micro-ros-agent` container of the Module 6 Gazebo compose project.
- **Channel A drives the right wheel** (camera end = front), verified with the IMU; the wiring documents say left.
  Encoder sides are unverified.
- **Open loop is not enough:** with the instructor's constants a 40 cm command gave 20 cm and a 180° turn 143°;
  two calibrations reached ≈40 cm and 189° at 0.08 m/s, but a left veer of +1° to +30° per move remains. Straight and
  pivot loads need separate duty→speed lines; short-move averages understate steady speed.
- **Evaluation lesson:** the filmed route ended ≈21 cm out (±3 cm), close to Gazebo's 20 cm, but 40° off in heading: report heading error.
- **Agent-safety lesson:** ROSA(ros_version=2) adds shell-backed built-in tools (`ros2_param_set`, `ros2_service_call`); restrict the
  tool list in code (research note F10).
- **Open items** O1–O6 in the research note (veer cause, encoder mapping, steady-state speed and battery, pivot
  translation, untested consistent constants, short-move losses). Pack voltage not metered this session.
- **Power state at the end of the session (2026-10-11 ~03:10 CDT):** on the floor on battery, VSYS jumper IN, USB out;
  Xiaohui to switch the battery OFF (not confirmed).


## 2026-10-16 — plate outline from a classmate's CAD (car.json + URDF rebuilt; wheels unchanged)

A classmate shared (with the instructor's permission) an Onshape STEP model and an A3 drawing of the Emo
chassis plate, for the Module 7 odometry lab's "correct the measurements" step. Kept with notes and tools in
`the private course repo (plate CAD is not published here)` (README there: what a STEP file is, every dimension, the checks).

- **It is this car's plate.** A plane homography from 16 CAD features to the bottom-view photo `IMG_7436` fits to
  1.34 px rms (≈ 0.25 mm). On that photo the wing depth is **34.0 mm** (CAD 34.35; the 2026-10-10 ruler reading was 40,
  already flagged by review #7). The front of the plate is hidden on the photo and is not photo-checked.
- **New evidence CSV** `evidence/M1/M1.T9/measurements-2026-10-16-with-plate-cad.csv`: the 2026-10-10 CSV unchanged plus
  superseding rows. CAD (±0.5 mm allowance): width 147.92, strip 100, wing depth 34.35, front arc R135.14 and R8 corner
  fillets (new rows P1/P2). Fit: B1 130.49, B2 = B4 76.49 mm (the two ruler readings fitted to the CAD length 206.98).
- **car.json** (rebuilt by `tools/write_car_json.py`, which gained a CAD uncertainty rule and the rounded plate-front
  corners): `chassis_width_m` 0.14792, `rear_overhang_m` 0.07649, `chassis_length_m` 0.21449, plate-front corners
  (0.1229, ±0.0447) instead of (0.131, ±0.050), `sweep_radius_m` 0.1402 → **0.140** (now the caster swung forward;
  no centring assumption). **Unchanged:** wheel diameter 0.067 (direct, unloaded), tyre width 0.027, track 0.1335,
  caster, camera, IMU, heights, mass. The CAD has no wheels; the instructor's 2.5 in / 5 in / 1 in (Module 7 guide,
  2026-10-13 lecture in Granola) are the nominal course robot, not measurements of this car.
- **URDF:** `car_props.xacro` regenerated; `car_geometry_extras.xacro` plate rows hand-edited (CAD/fit labels);
  `beaconmind_car.urdf.xacro` draws the rounded front (3 slices) and snaps plate-slice boundaries to a 2 µm grid (the
  first colcon run caught a 1 µm wing-slice overlap). New test `test_plate_outline_matches_measurements`; `test_car_model.py`
  +8 tests, and `test_configs_car_json_is_the_writer_output` now follows the CSV/date `car.json` names.
  `sim/isaac/assets/beaconmind_car.urdf` regenerated (sha256 `d0b2ffbf…`): only plate boxes and chassis iyy/izz changed.
- **Tests:** Mac `beaconmind` 63 passed; `beaconmind-ros` Python 3.10 63 passed; colcon 21 tests, 0 failures, 1 skipped
  (camera.json). Logs: `evidence/M1/M1.T9/plate-cad-2026-10-16/`.
- **For the Module 7 lab (not the project):** the plate does not enter odometry. The real-robot constants stay
  D 0.067 m and L 0.1335 m as the starting point; the lab's own steps measure CPR (step 7.5) and the effective D and L
  (step 9.2: do the 360° spin after restarting with the new D, or use L_new = L_old·(A/360)·(D_new/D_old)).
- **Spark:** files synced by tar (the Spark copies matched git HEAD first). Scratch `course-project/data/m7-plate-cad/`.
  No ROS node or daemon started; the only ROS process in `beaconmind-ros` is the old `tf2_echo` zombie (pid 1645).
  Containers seen running: `beaconmind-ros`, `gazebo-sim`, `micro-ros-agent`, `qwen38-flash` (not touched).
  The Module 6 lab wrapper includes this URDF, so a re-run of that lab would show the new plate.
- **Not committed.**

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-10-16: analysed the CAD files and the photo, wrote the reference
folder and its tools, the writer/geometry/test changes, the new CSV rows, the xacro edits, ran the builds and tests,
and wrote this entry. The CAD files are a classmate's; the 2026-10-10 readings are Xiaohui Chen's.
