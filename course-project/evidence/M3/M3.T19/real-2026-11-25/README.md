# Real-log replay set `real-2026-11-25` (M3.T19 / M4.T13): interim, Opus 5.5 done, Qwen3.8 and Gemma 4 running

The real car's B2 episodes of 2026-11-25 replayed offline through the model arms. Each step gives the arm the
observation the car's B2 saw, with the car's executed move held fixed. The arm's pose report is then scored
against the batch's truth at the last step (tag resection against the surveyed tags, with its sigma). The
pipeline, runner and dry rehearsal are described in [`../README.md`](../README.md).

## The set

`course-project/data/real-replay/real-2026-11-25/obslogs` holds one observation log per episode that ran to its own
end. Each batch has its own seed base (1000, 2000, 3000), and a converted batch keeps its seeds when another batch is
added ([`convert.txt`](convert.txt), [`obslogs-index.json`](obslogs-index.json)).

| Seed | Batch, episode | Scenario | Steps | Note |
| --- | --- | --- | --- | --- |
| 1001 | b2-real-01 ep01-a1 | S1 | 83 | batch halted after the episode and its end circle (odometry_scale) |
| 2001 | b2-real-02 ep01-a1 | S1 | 56 | |
| 2002 | b2-real-02 ep02-a1 | S2 | 62 | |
| 3001 | b2-real-03 ep01-a1 | S1 | 56 | |
| 3002 | b2-real-03 ep02-a1 | S2 | 81 | DONE at step 81, then a stall in the end circle halted the batch: no end circle, so only the tracker-dependent truths |

Not replayed: b2-real-02 ep03-a1, which was halted by odometry_scale before its own end. `b2-real-04` produced no
usable episode (it halted at step 19), so the set has 5 episodes.

The first three logs are byte-identical before and after b2-real-03 was added (sha12 a0634d20de1a, 9d9bd32d42ec,
d8923f129248). The converter and the analysis are at 73a53df and 34500ab. The end circle became the primary truth
in the commit after 34162ba, and the obslogs (the agents' input) did not change for it: the analysis reads the end
circles from the batch manifests under `course-project/data/batches`.

## Free check: the coded procedure equals the car's B2 at every step

The `procedure` arm runs the coded B2 procedure through the same runner, container and observation overlay. It gives
the live B2's estimate at 338 of 338 steps, on the Mac and in the Spark container
([`runs/procedure`](runs/procedure)). So the replay's input path reproduces what the car saw.

## Which truth: the end circle is primary

The batch's step truth is the pose it tracks: odometry between tag fixes, blended by inverse variance, with a 5 %
odometry sigma. On this carpet the car covers only 0.67 to 0.78 of its counted distance northward, so that truth is
overconfident:
- In simulation at 0.67 northward, the tracked truth's error reached a p95 of 0.10 to 0.13 m against a stated sigma
  of 5 to 6 cm.
- On the real episodes, the tracked end sits up to 14.6 cm from the end circle.

See [`../../M3.T12/batch-runner/truth-under-slip/README.md`](../../M3.T12/batch-runner/truth-under-slip/README.md)
(commit bf54dd9). The final errors therefore use three truths:

1. **The end circle (primary).** This is the full circle the batch turns where the episode ended. Its tags are solved
   on their own geometry, not through the tracker. All four episodes that have one ended by DONE, so no move followed
   the agent's last report, and the circle measured that very pose (the manifest's `end_fix.pose`, in the episode's
   map frame). n = 4.
2. **The last step's logged truth (secondary, tracker-dependent).** This is the batch's tracked pose at the last step,
   with its stated sigma.
3. **The same truth recomputed (secondary, tracker-dependent).** It is recomputed offline from the logged rows by
   `tools/recompute_truth.py BATCH_DIR --slip-sigma 0.3 --slip-north 0`. The tool reruns the batch's own per-step
   code (`replay_episode`) with an extra odometry sigma of 0.3 per metre of forward move. The analysis calls that
   function and takes the truth at the last record's row. Before using it, the analysis checks that the logged truth
   at that row is the obslog's last truth.

**The truth's own uncertainty, per episode:**

| Episode | End circle: tags, rms of tag residuals, stated sigma | Logged truth − end circle | Logged truth's stated sigma | Recomputed truth's sigma |
| --- | --- | --- | --- | --- |
| b2-real-01 ep01 | 9 tags, rms 2.3 cm, sigma 2.4 cm | 6.6 cm, −5.1° | 5.0 cm | 5.0 cm |
| b2-real-02 ep01 | 8 tags, rms 4.0 cm, sigma 2.8 cm | 4.2 cm, −5.1° | 5.0 cm | 5.0 cm |
| b2-real-02 ep02 | 14 tags, rms 2.6 cm, sigma 2.6 cm | 7.6 cm, −3.1° | 5.8 cm | 13.6 cm |
| b2-real-03 ep01 | 13 tags, rms 2.2 cm, sigma 2.6 cm | 14.6 cm, −6.9° | 5.0 cm | 5.0 cm |
| b2-real-03 ep02 | none: the batch halted in the end circle (a stall) | — | 5.6 cm | 12.3 cm |

The circle's positions are good to about 2–4 cm (rms of 8 to 14 tag residuals). Its heading is not a reference:
the circle solves its starting heading from views placed by the odometry's own turns, which slip too, and the tracked
heading sits 3 to 7° clockwise of it in all four episodes. So no heading result is drawn from the end circle.

## Opus 5.5 (Anthropic API; cap US$40 for the set, approved)

The run was done in two passes in one folder, so the cap counts both
([`runs/claude-opus-5-5`](runs/claude-opus-5-5), [`claude-opus-5-5.log`](claude-opus-5-5.log)):

- 12:47–13:11 UTC: seeds 1001, 2001 and 2002, US$14.13.
- 14:03–14:27 UTC: seeds 3001 and 3002, resumed with a reason.

In total: 338 of 338 steps, 338 valid reports, 0 harness fallbacks, 0 repaired reports, 0 step errors, US$23.90,
17.3 s per step (p95 22.5 s), 3 workers.

Final-position error, cm ([`interim-opus.md`](interim-opus.md), [`interim-opus.json`](interim-opus.json)):

**Against the end circle (primary; n = 4):**

| Arm | median | IQR | min | max |
| --- | --- | --- | --- | --- |
| B0 (dead reckoning) | 28.8 | 22.4 to 34.8 | 11.1 | 45.0 |
| B2 (the car's live procedure) | 6.1 | 3.1 to 9.8 | 1.3 | 13.5 |
| claude-opus-5-5 | 6.0 | 3.5 to 9.1 | 2.3 | 12.1 |

| Episode | B0 | B2 | Opus 5.5 |
| --- | --- | --- | --- |
| b2-real-01 ep01 | 26.2 | 3.6 | 3.9 |
| b2-real-02 ep01 | 11.1 | 1.3 | 2.3 |
| b2-real-02 ep02 | 31.4 | 13.5 | 12.1 |
| b2-real-03 ep01 | 45.0 | 8.6 | 8.1 |

**Against the last step's truth (secondary, tracker-dependent; n = 5):** each cell is logged / recomputed with
`--slip-sigma 0.3`.

| Arm | median | b2-real-01 ep01 | b2-real-02 ep01 | b2-real-02 ep02 | b2-real-03 ep01 | b2-real-03 ep02 (no end circle) |
| --- | --- | --- | --- | --- | --- | --- |
| B0 | 27.2 / 32.1 | 19.7 / 20.0 | 7.0 / 7.5 | 27.2 / 32.1 | 33.2 / 38.1 | 43.9 / 47.7 |
| B2 | 6.9 / 3.7 | 3.1 / 2.8 | 2.8 / 2.4 | 20.3 / 9.5 | 6.9 / 3.7 | 8.2 / 4.9 |
| Opus 5.5 | 6.8 / 3.3 | 3.5 / 3.3 | 1.9 / 1.6 | 19.0 / 8.2 | 6.8 / 2.8 | 7.2 / 6.5 |

**Reading it.**
- **Opus against B2.** Against the end circle, Opus is within 1.4 cm of B2 in every episode (median 6.0 against
  6.1 cm). Four episodes cannot separate the two; the simulated study's arm comparison stands on its own sample.
- **Which errors are resolvable.** The end circle resolves errors of a few centimetres (2–4 cm rms). The logged
  truth does not: it is up to 14.6 cm from the circle.
- **The two secondary truths disagree.** Recomputed with a slip-aware sigma, the last-step truth moves toward B2's
  and Opus's estimates in all five episodes (and away from B0's). That is expected rather than a confirmation: it
  gives more weight to the same tag fixes those estimators use. Its stated sigma grows to 12–14 cm on the S2 runs.
- **b2-real-03 ep02** has no independent final truth. Its B2 error is 8.2 cm against the logged truth and 4.9 cm
  against the recomputed one, whose sigma is 12.3 cm. It is not in the primary n.

An oddity, not a fault: Opus called `move` 7 times, always `move(NONE)`, after it had decided to stay. The
frozen replay refused each call ("replay mode: the log's move is already executed"), and every one of those steps
has a valid report. The study's simulated Opus runs do the same at the same rate: 37 `move(NONE)` calls in 1976 steps
(1.9 %), against 7 in 338 (2.1 %) here.

## Qwen3.8 and Gemma 4 (Spark GPU, one server at a time)

- Qwen3.8 (`qwen38-flash-xhigh`, vLLM 127.0.0.1:8000): seeds 1001, 2001 and 2002 ran 12:55–15:21 UTC with 3
  workers (config 8969d38de361): 201 of 201 steps, exit 0, no failed seed, all valid and no fallback in the log.
  At 15:22 the chain resumed the same folder with 3001 and 3002 (the Spark's replay code is unchanged, so the
  config tag matched).
- After that, [`chain.sh`](chain.sh) runs unattended in tmux `bm-rr-chain` and logs each stage to the set's
  `chain.log`:
  1. Resume the Qwen3.8 folder over the whole index, which adds 3001 and 3002.
  2. Stop the Qwen3.8 server and check that no model container is up and no process holds the GPU.
  3. Start the Gemma 4 vLLM server (`gemma4-26b`, 127.0.0.1:8001), run it over the whole index with one worker
     per episode, and stop the server.
- If the Spark clone is pulled past 73a53df, the hashes of the replay code in the config tag change, and the runner
  refuses to resume a folder. The chain then runs the new seeds into a sibling folder, `runs/<arm>+b2-real-03`.
  `tools/real_replay.py analyze` merges an arm's folders when the label is given twice. It refuses folders that
  differ in anything but those two hashes, and it refuses a seed found in two folders. This is also how a later
  batch (b2-real-04) adds to the set.

## Adding a batch later

```bash
# Mac or Spark host, repository root; a converted batch keeps its seeds, the new one gets the next seed base
python3 course-project/tools/real_replay.py convert --batch course-project/data/batches/b2-real-01 \
  --batch course-project/data/batches/b2-real-02 --batch course-project/data/batches/b2-real-03 \
  --batch course-project/data/batches/<new> --out course-project/data/real-replay/real-2026-11-25/obslogs
# each arm: resume its folder (or a sibling folder runs/<arm>+<new> if the replay code changed)
bash course-project/tools/real_replay.sh --provider <arm> --obslogs <set>/obslogs --out <set>/runs/<arm> \
  --cap-usd <cap> --workers <n> --resume-reason "add <new>"
python3 course-project/tools/real_replay.py analyze --obslogs <set>/obslogs --run procedure=<set>/runs/procedure \
  --run <arm>=<set>/runs/<arm> [--run <arm>=<set>/runs/<arm>+<new>] ... --out <stem>
```

The run rows (`seed_<n>.jsonl`, about 6 MB per arm) stay in `course-project/data/real-replay/real-2026-11-25/runs` on
the Spark and the Mac; this folder keeps the run headers, logs and results (text and JSON only).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: ran the replays, wrote this summary and chain.sh, and made
the end circle the primary truth of the analysis.
