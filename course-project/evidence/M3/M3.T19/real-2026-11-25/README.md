# Real-log replay set `real-2026-11-25` (M3.T19 / M4.T13): final set; Opus 5.5 complete, Qwen3.8 and Gemma 4 running

The real car's B2 episodes of 2026-11-25 are replayed offline through the model arms. At each step the arm gets the
observation the car's B2 saw, with the car's executed move held fixed. Its final pose report is scored against
independent truth. The pipeline, runner and dry rehearsal are described in [`../README.md`](../README.md).

**The set is final** (Xiaohui, 2026-11-25): the right motor is failing and no more coded-procedure episodes will be
run. It holds 9 episodes that ended by DONE, plus one the coded procedure stopped itself, which is listed apart.
The three closed-loop Opus episodes planned after the motor swap are not part of it.

## The set: 10 seeds, 850 steps, all five start poses

`course-project/data/real-replay/real-2026-11-25/obslogs` ([`convert.txt`](convert.txt),
[`obslogs-index.json`](obslogs-index.json)). Each batch has its own seed base. A converted batch keeps its seeds and
bytes when another batch is added: the first five logs were byte-identical through every reconvert.

| Seed | Batch, episode | Start | Steps | Ended | End circle (tags, rms) | Batch tracker slip sigma |
| --- | --- | --- | --- | --- | --- | --- |
| 1001 | b2-real-01 ep01 | S1 | 83 | DONE (batch halted after it: odometry_scale) | 9, 2.3 cm | 0 |
| 2001 | b2-real-02 ep01 | S1 | 56 | DONE | 8, 4.0 cm | 0 |
| 2002 | b2-real-02 ep02 | S2 | 62 | DONE | 14, 2.6 cm | 0 |
| 3001 | b2-real-03 ep01 | S1 | 56 | DONE | 13, 2.2 cm | 0 |
| 3002 | b2-real-03 ep02 | S2 | 81 | DONE (a stall halted the batch inside the end circle) | none | 0 |
| 4001 | b2-real-05 ep01 | S5 | 114 | DONE | 15, 2.7 cm | 0.3 per m |
| 4002 | b2-real-05 ep02 | S4 | 132 | DONE | 11, 4.9 cm | 0.3 per m |
| 4003 | b2-real-05 ep03 | S3 | 141 | DONE | 13, 2.9 cm | 0.3 per m |
| 5001 | b2-real-06 ep01 | S4 | 80 | DONE | 5, 3.2 cm | 0.3 per m |
| 5002 | b2-real-06 ep02 | S3 | 45 | **flagged:** the procedure stopped itself | 7, 4.5 cm | 0.3 per m |

Not replayed, because they did not end normally:
- b2-real-02 ep03 (odometry_scale);
- b2-real-05 ep04 (a stall at step 19);
- b2-real-06 ep03 (telemetry_stale, a Pico dropout at step 4);
- b2-real-04, which gave no usable episode.

**The flagged episode (5002).**
- **What happened:** the frozen B2 met a branch it does not implement ("E5 leg with no forward move and no E4").
- **How the log treats it:** the harness wrote that step as the study's fallback, the previous report dead-reckoned
  through the step's odometry. This is the pre-registered rule for a step without a valid report.
- **Why it is scored:** no move followed, so the end circle measured that step's pose. The pre-registration scores
  every logged step whatever ended the episode, and the room rehearsal keeps "the records up to the stop"
  ([`../../M3.T12/rehearsal-b2.md`](../../M3.T12/rehearsal-b2.md), item 3). So it is converted and scored, but listed
  apart and kept out of every median.
- **Why the car's B2 met this branch:** `tools/car_batch.py` builds its driver without `room=True`, so the real
  batches drove the frozen `B2Driver()`. The study's room B2 (`kinsim_room.make_b2_policy()`, enforced by
  `tools/report_assets.py`) handles this branch. The rehearsal measured the frozen one stopping there in 15–16 of 150
  room episodes. Before the branch both act identically, so the other nine episodes are unaffected.

## Which truth: the end circle is primary

The batch's step truth is the pose it tracks: odometry between tag fixes, blended by inverse variance. On this carpet
the car covers 0.67 to 0.78 of its counted distance northward. With the plain 5 % odometry sigma
(b2-real-01 to -03), that truth was overconfident: in simulation, the p95 error was 0.10–0.13 m against a stated
5–6 cm ([`../../M3.T12/batch-runner/truth-under-slip/README.md`](../../M3.T12/batch-runner/truth-under-slip/README.md)).
From b2-real-05 on, the batches ran a slip sigma of 0.3 per metre. The final errors use three truths:

1. **The end circle (primary).** This is the full circle the batch turns where the episode ended, 5 to 15 tags solved
   on their own geometry, not through the tracker. When the episode ended by DONE, or the procedure stopped itself,
   no move followed the last report, so the circle measured that pose (`end_fix.pose`, in the episode's map frame).
   It is read from the batch manifests; the agents' input (the obslogs) does not carry it.
2. **The last step's logged truth (secondary, tracker-dependent).**
3. **The same truth recomputed (secondary, tracker-dependent).** It is recomputed offline by `tools/recompute_truth.py`
   (its `replay_episode`, at slip sigma 0.3 + 0 × north per metre). For b2-real-05 and -06, which ran that setting,
   the recomputed truth equals the logged one exactly, as it should.

**The truth's own uncertainty:**

| Seed | End circle: tags, rms, stated sigma | Logged truth − end circle | Logged truth sigma | Recomputed truth sigma |
| --- | --- | --- | --- | --- |
| 1001 | 9, 2.3 cm, 2.4 cm | 6.6 cm, −5.1° | 5.0 cm | 5.0 cm |
| 2001 | 8, 4.0 cm, 2.8 cm | 4.2 cm, −5.1° | 5.0 cm | 5.0 cm |
| 2002 | 14, 2.6 cm, 2.6 cm | 7.6 cm, −3.1° | 5.8 cm | 13.6 cm |
| 3001 | 13, 2.2 cm, 2.6 cm | 14.6 cm, −6.9° | 5.0 cm | 5.0 cm |
| 3002 | none | — | 5.6 cm | 12.3 cm |
| 4001 | 15, 2.7 cm, 2.5 cm | 9.3 cm, −6.2° | 5.0 cm | 5.0 cm |
| 4002 | 11, 4.9 cm, 2.8 cm | 8.3 cm, −7.1° | 5.0 cm | 5.0 cm |
| 4003 | 13, 2.9 cm, 2.3 cm | 6.2 cm, −4.7° | 5.0 cm | 5.0 cm |
| 5001 | 5, 3.2 cm, 3.4 cm | 5.9 cm, −5.1° | 5.0 cm | 5.0 cm |
| 5002 (flagged) | 7, 4.5 cm, 3.1 cm | 5.1 cm, −6.9° | 5.6 cm | 5.6 cm |

The circle's positions are good to 2–5 cm. Its heading is not a reference. The circle solves its starting heading
from views placed by the odometry's own turns, which slip too, and the tracked heading sits 3–7° clockwise of it in
all nine circles. No heading result is drawn from the end circle.

## Free check: the coded procedure reproduces the car's B2

The `procedure` arm runs the coded B2 through the same runner, container and observation overlay. It gives the live
B2's estimate at 850 of 850 steps. That includes 5002's stopping step, where it raises the same `NotImplementedError`
and falls back to the same pose.

## Results: Opus 5.5 complete ([`result.md`](result.md), [`result.json`](result.json))

**Final-position error against the end circle (primary; n = 8; 3002 has no circle, 5002 is listed apart), cm:**

| Arm | median | IQR | min | max |
| --- | --- | --- | --- | --- |
| B0 (dead reckoning) | 38.2 | 26.2 to 73.1 | 11.1 | 111.6 |
| B2 (the car's live procedure) | 7.9 | 5.6 to 15.2 | 1.3 | 23.2 |
| claude-opus-5-5 | 7.7 | 5.2 to 14.1 | 2.3 | 25.3 |

| Seed | Start | B0 | B2 | Opus 5.5 |
| --- | --- | --- | --- | --- |
| 1001 | S1 | 26.2 | 3.6 | 3.9 |
| 2001 | S1 | 11.1 | 1.3 | 2.3 |
| 2002 | S2 | 31.4 | 13.5 | 12.1 |
| 3001 | S1 | 45.0 | 8.6 | 8.1 |
| 4001 | S5 | 67.9 | 6.2 | 5.6 |
| 4002 | S4 | 111.6 | 23.2 | 25.3 |
| 4003 | S3 | 88.8 | 20.4 | 20.1 |
| 5001 | S4 | 26.2 | 7.2 | 7.2 |
| *apart:* 5002 (flagged) | S3 | 12.2 | 7.6 | 18.2 |

**Against the last step's truth (secondary; n = 9 with 3002), median, logged / recomputed:** B0 33.2 / 38.1, B2
10.1 / 9.5, Opus 10.6 / 8.2 cm. 3002 alone, logged / recomputed: B0 43.9 / 47.7, B2 8.2 / 4.9, Opus 7.2 / 6.5 cm.

**Runs:**
- Opus: 850 of 850 steps, 850 valid reports (805 of 805 on the nine episodes), 0 fallbacks, 0 repaired, 0 step
  errors. 18.0 s per step (p95 24.5 s).
- Spend: US$63.02 by the replayed rows' costs (US$60.41 on the nine, US$2.61 on 5002). The three ledgers total
  US$63.22, which includes the crash allowance below. The cap was US$70 for the set.
- Opus made 25 `move` calls, all `move(NONE)`, all refused by the replay ("the log's move is already executed"), all
  on steps with valid reports. That is 2.9 % of steps; the study's simulated Opus did the same at 1.9 %.

**Reading it.**
- **Opus against B2:** against the end circle, Opus is within 2.1 cm of B2 in all eight episodes, so the two cannot
  be separated here.
- **Errors grow with episode length:** both lie at 20–25 cm on the two longest episodes (S4 and S3 of b2-real-05,
  132 and 141 steps), where B0 is 89–112 cm off.
- **The flagged episode** is the one place where they part: Opus 18.2 against B2 7.6 cm.
- **The simulated study's arm comparison** stands on its own, larger sample.

## Qwen3.8 and Gemma 4: running

- **Qwen3.8** (`qwen38-flash-xhigh`, vLLM): 1001–3002 are complete. 4001–4003 resumed after the crash, and 5001/5002
  started at 18:31:56, side by side on one server, 5 concurrent. Expected end about 23:30 UTC (seed 4003, about
  2.6 min per step). At 19:13 UTC: 483 steps, 481 valid reports, 2 fallbacks (3001 step 8 and 4003 step 8, both
  invalid reports), 31 repaired, 0 step errors.
- **Gemma 4** (`gemma4-26b`, vLLM): starts after Qwen on all 10 seeds, one worker per episode.

## How it ran: folders, chains, the crash, the resume rule

**Folders per arm.** The Spark's clone was pulled to 19f71e6 during the day, which changes the replay code's hashes
in the runner's config tag, so the runner refuses to resume a folder under the new code. Batches added after that run
in sibling folders `runs/<arm>+<batch>`, and `tools/real_replay.py analyze` merges an arm's folders. It refuses
folders that differ in anything but those two hashes, and a seed found in two folders. Nothing in the agents' input
(prompt, design values, harness, providers) changed between the commits (`git diff 7a8b599 19f71e6`). See
[`result.md`](result.md) for each folder's seeds and config tag. The run headers (`run.json`, `run.resume-*.json`,
`run.end-*.json`) of the Opus and procedure folders are in [`runs/`](runs).

**Chains.** One GPU model server at a time; Opus runs on the API beside them.
1. [`chain.sh`](chain.sh) ran Qwen and would then have gone to Gemma.
2. When b2-real-05 and then b2-real-06 arrived during a Qwen run, the running chain's log was swapped for a FIFO
   nobody read. Its next log line then blocked before the Qwen server stop, while its Qwen runner ran on untouched.
   A second script took over when that runner ended: [`chain2.sh`](chain2.sh), then [`takeover.sh`](takeover.sh).
   SIGSTOP does not hold a tmux pane process, because tmux continues it.
3. Since the crash, [`replay_chain.sh`](replay_chain.sh) is one script that can be re-run. A part whose seeds are all
   complete is skipped. A part with a run.json is resumed with the reason, otherwise started. A part whose lock a
   runner holds is waited for. At start it repairs a crash's torn or zero-filled tails in folders no runner holds.
   [`chain.log`](chain.log) has every stage.

**The crash.** The Spark lost power at 18:13:57 UTC (the journal ends without a shutdown) and rebooted at 18:14:40.
- Every runner, chain and the Qwen server were gone.
- The seed rows were intact. The Opus b2-real-06 spend ledger ended in 393 zero bytes without a newline. The replay's
  `spent_in` skips such a line, but the next entry would have been appended onto it and lost from the cap.
- It was repaired before the resume. The original is kept
  ([`runs/claude-opus-5-5+b2-real-06/spend.jsonl.crash-20261125T181357`](runs/claude-opus-5-5+b2-real-06)). The
  ledger was cut at the first zero byte, and two labelled entries were appended: US$0.2062 that the written rows
  prove was spent, and US$0.20 for the two steps in flight.

**The resume rule** is the pre-registration's (`evidence/M4/M4.T1/prereg.md` §3, missing data):
- a seed stopped by an infrastructure failure is resumed, each resume records its reason in `run.resume-*.json`, and
  a resume under any other configuration is refused;
- a seed stopped a second time is not run again, and its remaining steps are scored as fallbacks.

The power loss was the first such stop for 4001–4003 (Qwen) and 5001/5002 (Opus). Each resume header carries the
reason, and each config tag matched.

## For the report (`report/PENDING.md`)

- **Row 1, the abstract's last sentence:** the number of real episodes (9 + 1 flagged, 850 steps), and each arm's
  final-position error against the end circle. Opus, B2 and B0 are filled here; Qwen3.8 and Gemma 4 follow.
- **Row 5, V-G "Real-log replay":** episodes and steps, and the per-arm median with IQR against the end circle and
  its uncertainty (the tables above). The tape mentioned in the row was not used: the end circle is the ground truth.
  The row also asks for the same per arm "in each simulated rehearsal" and the sim-to-real gap. The room rehearsals
  ran B0 and B2 only, not the model arms, so that part needs the model arms on a simulated room set. It is not
  available from this folder.
- **Row 7, VI end:** whether the simulated ordering held on the real logs, in part. On the real logs Opus ties B2 and
  both beat B0 by a wide margin; the closed loop is still to come.
- **The "also to update" list:** IV-C's ground-truth paragraph should become this end circle, with the tracked truth
  as secondary. IV-D's real-car procedure should become the batches as run. V-G's "No real episode has been run" no
  longer holds.

## Re-running or extending

```bash
# Spark, repository root: continue whatever is unfinished (after a reboot, for example)
tmux new -d -s bm-rr-chain "bash course-project/data/real-replay/real-2026-11-25/replay_chain.sh 'the reason'"
# the analysis (Mac or Spark); give an arm's label once per folder
python3 course-project/tools/real_replay.py analyze --obslogs <set>/obslogs \
  --run claude-opus-5-5=<set>/runs/claude-opus-5-5 --run claude-opus-5-5=<set>/runs/claude-opus-5-5+b2-real-05 ... \
  --out <stem>
```

The full run rows (about 6 MB per arm and pass) stay in `course-project/data/real-replay/real-2026-11-25/runs` on the
Spark. The Mac's analysis uses copies trimmed to what `analyze` reads ([`trim_runs.py`](trim_runs.py), 0.8 MB). This
folder keeps the run headers, logs, scripts and results, as text and JSON only.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: ran the replays and the chains, repaired the crash's ledger,
wrote the analysis, this summary and the scripts in this folder.
