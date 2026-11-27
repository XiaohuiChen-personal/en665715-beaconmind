# Real-log replay set `real-2026-11-25` (M3.T19 / M4.T13): final set, all three models complete

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

## Which truth: the end circle first

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

**What the end circle is not.**
- **It is not independent of the estimators.** It shares the tags, the camera and the world file (the surveyed tag
  positions) with B2's and the models' estimates. Dead reckoning (B0) shares none of them. An error in the survey or
  the detector moves the truth and the tag-based estimates together.
- **Its ranges read short.** The detector's ranges read 1.2–1.7 % short (range bias +0.0049 − 0.0166 r m,
  `evidence/M1/M1.T8/noise-model-adjustments.md`).
- **It is anchored on the start circle.** The map frame is the episode's start pose, which the start circle fixed.
- **Nothing checks it.** There is no independent measurement of the final pose (no tape, motion capture or second
  sensor).

So it is the best truth these logs have, not an external one. The comparison it supports most firmly is between
estimators of the same kind (B2 against the models), and less firmly any tag-based estimate against B0.

The circle's positions are good to 2–5 cm. Its heading is not a reference. The circle solves its starting heading
from views placed by the odometry's own turns, which slip too, and the tracked heading sits 3–7° clockwise of it in
all nine circles. No heading result is drawn from the end circle.

## Free check: the coded procedure reproduces the car's B2

The `procedure` arm runs the coded B2 through the same runner, container and observation overlay. It gives the live
B2's estimate at 850 of 850 steps. That includes 5002's stopping step, where it raises the same `NotImplementedError`
and falls back to the same pose.

## Results: all three models ([`result.md`](result.md), [`result.json`](result.json), [`stats.md`](stats.md), [`stats.json`](stats.json))

**Every table below is exploratory, not pre-registered.** The pre-registration reports the real logs descriptively,
as the sim-to-real gap (prereg.md §6). The end-circle value was chosen after the data. Nothing here is a test.

**Final-position error against the end circle (n = 8; 3002 has no circle, 5002 is listed apart), cm:**

| Arm | median | IQR | min | max |
| --- | --- | --- | --- | --- |
| B0 (dead reckoning) | 38.2 | 26.2 to 73.1 | 11.1 | 111.6 |
| B2 (the car's live procedure) | 7.9 | 5.6 to 15.2 | 1.3 | 23.2 |
| Opus 5.5 | 7.7 | 5.2 to 14.1 | 2.3 | 25.3 |
| Qwen3.8 | 7.5 | 4.0 to 13.4 | 1.2 | 56.2 |
| Gemma 4 | 83.5 | 64.0 to 163.8 | 6.4 | 486.8 |

| Seed | Start | Steps | B0 | B2 | Opus 5.5 | Qwen3.8 | Gemma 4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1001 | S1 | 83 | 26.2 | 3.6 | 3.9 | 4.8 | 81.1 |
| 2001 | S1 | 56 | 11.1 | 1.3 | 2.3 | 1.3 | 81.9 |
| 2002 | S2 | 62 | 31.4 | 13.5 | 12.1 | 11.8 | 12.7 |
| 3001 | S1 | 56 | 45.0 | 8.6 | 8.1 | 7.7 | 6.4 |
| 4001 | S5 | 114 | 67.9 | 6.2 | 5.6 | 1.2 | 137.3 |
| 4002 | S4 | 132 | 111.6 | 23.2 | 25.3 | 56.2 | 486.8 |
| 4003 | S3 | 141 | 88.8 | 20.4 | 20.1 | 18.4 | 243.3 |
| 5001 | S4 | 80 | 26.2 | 7.2 | 7.2 | 7.2 | 85.2 |
| *apart:* 5002 (flagged) | S3 | 45 | 12.2 | 7.6 | 18.2 | 17.3 | 56.6 |

**Against the last step's truth (tracker-dependent; n = 9 with 3002):**

| Arm | median, logged / recomputed | 3002 alone, logged / recomputed |
| --- | --- | --- |
| B0 | 33.2 / 38.1 cm | 43.9 / 47.7 cm |
| B2 | 10.1 / 9.5 cm | 8.2 / 4.9 cm |
| Opus 5.5 | 10.6 / 8.2 cm | 7.2 / 6.5 cm |
| Qwen3.8 | 9.0 / 7.8 cm | 6.8 / 5.1 cm |
| Gemma 4 | 91.1 / 91.1 cm | 137.7 / 136.7 cm |

**Paired differences against the end circle (n = 8)** ([`stats.md`](stats.md)):
- **Estimators:** arm − B0 uses family 1's estimator: Hodges–Lehmann, or the median when the adjusted skewness
  exceeds 1, the switch prereg.md §5 sets for families 1 and 2 only. It fired for Gemma 4 − B0. Model − B2 and the
  comparisons between models use Hodges–Lehmann without the switch, as the study's pairwise comparisons do, with the
  median as a note.
- **No tests:** no p-values and no verdicts. H2 (against B1) is not run: B1 needs oracle association, which the real
  logs do not have.

| Difference | estimate (cm) | 95 % interval (cm) | estimator | episodes below / above zero | median (interval), a note |
| --- | --- | --- | --- | --- | --- |
| B2 − B0 | −40.1 | −68.4 to −16.1 | Hodges–Lehmann | 8 / 0 | |
| Opus 5.5 − B0 | −40.7 | −68.7 to −15.5 | Hodges–Lehmann | 8 / 0 | |
| Qwen3.8 − B0 | −37.9 | −62.9 to −15.5 | Hodges–Lehmann | 8 / 0 | |
| Gemma 4 − B0 | +64.2 | −38.6 to +375.1 | median (skewness switch) | 2 / 6 | |
| Opus 5.5 − B2 | −0.1 | −0.8 to +1.0 | Hodges–Lehmann | 4 / 3 | −0.1 (−1.3 to +2.1) |
| Qwen3.8 − B2 | −0.4 | −2.9 to +16.5 | Hodges–Lehmann | 4 / 2 | −0.4 (−5.0 to +33.0) |
| Gemma 4 − B2 | +104.4 | +37.7 to +272.0 | Hodges–Lehmann | 2 / 6 | +79.2 (−2.1 to +463.6) |
| Opus 5.5 − Qwen3.8 | +0.4 | −15.3 to +2.4 | Hodges–Lehmann | 2 / 5 | +0.4 (−30.9 to +4.4) |
| Opus 5.5 − Gemma 4 | −104.6 | −270.5 to −37.8 | Hodges–Lehmann | 7 / 1 | −78.7 (−461.5 to +1.7) |
| Qwen3.8 − Gemma 4 | −106.6 | −255.6 to −37.5 | Hodges–Lehmann | 7 / 1 | −79.2 (−430.6 to +1.2) |

Mean ranks among the models (1 = smallest error): Qwen3.8 1.44, Opus 5.5 1.81, Gemma 4 2.75.

**Runs** (all 850 steps unless noted; the nine main episodes alone are in [`stats.md`](stats.md)):

| | Opus 5.5 | Qwen3.8 | Gemma 4 |
| --- | --- | --- | --- |
| Serving | Anthropic API | Qwen3.8-Flash-Next NVFP4 on vLLM (`bm-qwen38`) | Google's bf16 Gemma 4 26B-A4B on vLLM (`bm-gemma4-vllm`, `tools/serve_gemma4_vllm.sh`) |
| Valid reports | 850 | 848 | 811 |
| Fallbacks | 0 | 2 (invalid reports) | 39: 27 invalid reports, 12 replies that hit the output or context limit |
| Repaired reports | 0 | 61 | 0 |
| Step errors | 0 | 0 | 12 (the same 12 limit hits) |
| `move` calls, all refused by the replay | 25, all `move(NONE)` | 6, all `move(NONE)` | 79 real moves: 72 TURN_LEFT_30, 4 TURN_RIGHT_30, 3 FORWARD_25 |
| Seconds per step, mean (p95) | 18.0 (24.5) | 128.7 (230.4) | 987.7 (1593.1) |
| Workers | 3 (2 for b2-real-06) | 3, then 3 + 2 side by side | 10 (one per episode) |
| Cost | US$63.02 | none | none |

- **Pose source as the procedure's** (nine main episodes): Opus 98.5 %, Qwen3.8 98.5 %, Gemma 4 56.8 % of steps.
- **Tool names as the procedure's:** 97 %, 81 % and 49 % of calls.
- **Calls per step**, the refused `move` calls included: 3.33, 3.92 and 2.60, against the procedure's 3.20. Without
  the `move` calls: 3.30, 3.92 and 2.50.
- **Tag fixes claimed without a `fix_pose` call that step:** Opus 0 of 329, Qwen3.8 0 of 326, Gemma 4 74 of 179 (76
  over all ten episodes).
  - Gemma's 179 include 2 claims under its own label "relocalised". 72 of its 74 had no tool call at all.
  - All 37 of its beacon-fix and "relocalised" claims without a call carry `fix_verified: false` in the run files.
  - **The limit of this count:** it checks that `fix_pose` was called that step, not that the call succeeded, and the
    harness verifies full (beacon) fixes only.
- **Gemma's wall time:** 34.25 h, from 23:09:36 UTC on 11-25 to 09:24:36 on 11-27.
  - 20 requests hit the client timeout (3,600 s) and were retried under the pre-registered rule, at most twice on one
    step (1001 step 9). Every step completed.
  - A retry is a fresh draw that can only help Gemma, so its fallback count is a lower bound, as in the study.

**The gain over dead reckoning is the procedure's, not Opus's or Qwen3.8's:** B2 shows the same gain, and a model
that follows the procedure inherits it. Neither of the two is within 1 cm of B2 on every episode, and eight episodes
cannot order them: their intervals straddle zero by many centimetres. Gemma 4 ends worse than B2 on six of eight
episodes, by 77 to 464 cm, and 0.8 and 2.2 cm better on the other two (2002 and 3001).

## What the per-step traces show ([`stats.md`](stats.md), [`stats.json`](stats.json))

**A prompt rule that the coded procedure does not have.**
- **The rule:** the room prompt's rule 2 says to compose the odometry with forward and left set to 0 when its quality
  is `slip_suspected` (`prompts/robot_system_prompt_v3.3-room.txt`, line 32). The frozen procedure has no such rule:
  `kinsim_lite` does not simulate slips, and its `estimate_step` ignores the quality flag.
- **Where it fired:** on the real logs the flag fired at four steps: 1001/24, 3001/41, 3002/78 and 4001/81, each a
  forward move of 0.24–0.25 m by odometry. Opus and Qwen3.8 zeroed that move each time, as told; B2 composed it.
- **Gemma 4 applied the rule once of four:** it composed 0 at 3002/78, the full 0.24 m at 4001/81, and made no
  `compose_odometry` call at 1001/24 or 3001/41 (the `slip_suspected` field of [`stats.json`](stats.json)).
- **Whether the move happened** shows at the next tag fix, not in the batch's tracked truth, which composes the same
  odometry:
  - **1001/24, 3002/78 and 4001/81: the move was real.** A tag fix at the flagged step itself put the car 20–24 cm
    from B2's, Opus's and Qwen3.8's estimate of the step before. They took that fix at once, so the rule changed
    nothing there, except for Opus at 4001/81, which kept its zeroed prior (22.5 cm from B2) until the beacon fix at
    step 82.
  - **3001/41: no fix followed at once, and this case cannot separate the rule from the floor's ordinary shortfall.**
    - No fix followed for six steps. When one came (the models at 47, B2 at 48), Opus's and Qwen3.8's zeroed track was
      5.4 cm from B2's fix, and B2's full composition 20.4 cm. So the models ended nearer the next fix.
    - But three forward moves lie between the flag and the fix: steps 41, 42 and 43, 0.75 m by odometry, roughly
      northward. Only the first was flagged.
    - The northward travel ratio measured on this carpet, 0.827 (`evidence/M3/M3.T12/batch-runner/tape/split-output.txt`,
      pooled, tape down, north), alone predicts about 13 cm of shortfall over the three.
- **Reading:** so several of the places where Opus and Qwen3.8 part from B2 are this rule, not a model error. The rule
  changed nothing at two of the four flagged steps, held Opus back for one step at the third, and at the fourth left
  the models nearer the next fix, for a reason the data cannot separate from the floor's slip. The study's simulation
  never exercised it.

**Opus 5.5.**
- Its departures from B2 were transient: the slip rule above, and opposite accept-or-keep decisions on single-tag
  position fixes at 4003 steps 109–119.
- The next beacon fix closed each one, and Opus ends within 2.2 cm of B2 on all nine main episodes.

**Qwen3.8.**
- Like Opus, it ends within 2.2 cm of B2 on seven main episodes. It is 5.0 cm away on 4001 and 33.1 cm away on 4002.
- On 4002 (56.2 cm, against B2's 23.2), from step 67, where it took a beacon fix and the procedure a position fix, it
  carried a 10–20 cm offset. At steps 130–131 it kept its prior where the procedure accepted a beacon fix and then a
  position fix.

**Gemma 4 departs from the procedure early and stays away.**
- **Early departure:** it parts from B2's estimate by more than 5 cm within 13–36 steps in every episode. Its largest
  gaps range from 26 cm (3001) to 487 cm (4002).
- **The largest errors come from claimed tag fixes it did not compute.**
  - **The measure:** a jump is the distance from the estimate to the dead-reckoned prior the harness logs for that
    step (`harness_prior`, the previous report composed with the step's odometry). The `jumps` field of
    [`stats.json`](stats.json) has it.
  - **The eight largest, main episodes:** 4002/65 (2.35 m), 4002/66 (2.32), 4003/98 (2.29), 3002/57 (1.62), 4001/75
    (1.56), 4002/117 (1.47), 4002/32 (1.14) and 1001/43 (1.11).
  - **Seven of the eight are position fixes it reported with no tool call at all.**
  - **4002/32 is a second kind of error:** a `prior_kept` report with four tool calls, `fix_pose` among them, whose
    pose is 1.14 m from its prior.
  - **Beyond 0.5 m:** Gemma has 11 jumps that are fixes claimed without `fix_pose` and 1 of the other kind. Opus and
    Qwen3.8 have none; their largest are 0.30 and 0.25 m.
  - Over the nine main episodes it claimed 179 tag fixes, 74 of them without `fix_pose`. Opus and Qwen3.8 never did.
- **Its pose source differs from the procedure's on 43 % of steps.** It often keeps its prior, or composes odometry
  only, where the procedure takes a fix, and sometimes the reverse.
- **It skipped the `compose_odometry` tool on 264 of the 840 moved steps.** On the turns among them with no fix, it
  still updated its heading by the odometry's turn in 174 of 185 cases, so skipping the tool is not what moves it
  away.
- **It tried to drive.** Its 79 `move` calls were real moves, all refused by the replay; the other two only ever
  called `move(NONE)`.
- **Its two good episodes** are 3001 (6.4 cm) and 2002 (12.7 cm). Its largest gaps to B2 there were 26 and 51 cm;
  on 3001 the gap closed to 3 cm by the end, on 2002 it ended at 20 cm.
- **On the long episodes** its error grows to 1.4–4.9 m: 4001, 4002 and 4003, with 114–141 steps.

**The flagged episode (5002, step 44).**
- **B2:** the live B2 crashed in its decision step and fell back to dead reckoning, 7.6 cm from the end circle. Run
  on that observation, the frozen `estimate_step` would have made a position fix 7.7 cm from the circle, so the crash
  did not change B2's error.
- **Opus and Qwen3.8** applied fixes there instead. Opus took a two-tag beacon fix that `fix_pose` verified and ended
  18.2 cm from the circle; Qwen3.8 ended 17.3 cm away.
- **Gemma 4** ended 56.6 cm away. It had parted from B2 at step 14, with its largest gap (72 cm) at step 32, a beacon
  fix it claimed without a tool call.

**Episode length.** For B0, B2, Opus and Qwen3.8, the two largest errors are on the two longest episodes (4002 and
4003, 132 and 141 steps): B0 111.6 and 88.8, B2 23.2 and 20.4, Opus 25.3 and 20.1, Qwen3.8 56.2 and 18.4 cm. Gemma 4's
two largest are on the same two (486.8 and 243.3 cm).

## What is established, what is not, and what not to conclude

**Established (on these 8 + 1 episodes, against the end circle).**
- B2, Opus 5.5 and Qwen3.8 all end well below dead reckoning: about 40 cm lower by Hodges–Lehmann, 8 of 8 episodes.
- Opus 5.5 and Qwen3.8 end within a few centimetres of B2 on most episodes. Opus is within 2.2 cm of B2's estimate at
  the end of all nine main episodes.
- Gemma 4 ends far from B2 on six of eight episodes (median 83.5 cm against B2's 7.9). It claims tag fixes it did not
  compute, which the other two models never do.
- The models carry out a prompt rule (zero a slip-flagged move) that the coded procedure lacks. On the real logs it
  fired four times. At three of them a tag fix at the same step put the car 20–24 cm from the estimates of the step
  before, so the move was real. The fourth cannot separate the rule from the floor's ordinary northward shortfall.

**Not established.**
- Any ordering between Opus 5.5 and Qwen3.8: their difference's interval runs from −15.3 to +2.4 cm.
- Whether either adds anything to the procedure: Opus − B2 is −0.1 cm (−0.8 to +1.0).
- Any statistical claim at all: n = 8, exploratory, with no test.

**A reader must not conclude:**
- **That the models' gain over B0 is their own.** B2 shows the same gain, so it is the procedure's.
- **That the end circle is independent ground truth.** It shares the tags, camera and world file with B2's and the
  models' estimates, and B0 shares none. Its ranges read 1.2–1.7 % short, it is anchored on the start circle, and
  nothing checks it.
- **That headings were measured.** The circle's heading is not a reference.
- **That these logs test the pre-registered hypotheses.** They do not. The study's tests stand on the simulated
  sample.
- **That Gemma 4's real-log result says how it would drive the car.** These are replays of B2-driven episodes: every
  arm sees the moves B2 chose.

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
  final-position error against the end circle: B0 38.2, B2 7.9, Opus 5.5 7.7, Qwen3.8 7.5 and Gemma 4 83.5 cm
  (medians, n = 8). Label it exploratory.
- **Row 5, V-G "Real-log replay":** episodes and steps, the per-arm median with IQR against the end circle, the
  truth's uncertainty and limits, and the paired differences with their intervals (the tables above). The tape
  mentioned in the row was not used: the end circle is the ground truth.
  - The row also asks for the same per arm "in each simulated rehearsal" and the sim-to-real gap. The room rehearsals
    ran B0 and B2 only, not the model arms, so that part is not available from this folder.
- **Row 7, VI end:** whether the simulated ordering held on the real logs, in part.
  - On the real logs, Opus and Qwen3.8 tie B2 and beat B0 by the procedure's own margin. Gemma 4 falls far behind
    all three tag-based arms, and its median is higher than B0's.
  - The closed loop is still to come.
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
wrote the analysis, this summary and the scripts in this folder. 2026-11-27: scored Gemma 4, wrote
the findings for all three models and answered review findings 46 to 51.