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
| 1001 | b2-real-01 ep01-a1 | S1 | 83 | batch halted after the episode (odometry_scale); end pose from the end circle's `pose_now` |
| 2001 | b2-real-02 ep01-a1 | S1 | 56 | |
| 2002 | b2-real-02 ep02-a1 | S2 | 62 | |
| 3001 | b2-real-03 ep01-a1 | S1 | 56 | |
| 3002 | b2-real-03 ep02-a1 | S2 | 81 | DONE at step 81, then a stall in the end circle halted the batch: no end circle, end pose from the last step's truth, no "vs end circle" value |

Not replayed: b2-real-02 ep03-a1, which was halted by odometry_scale before its own end. `b2-real-04` was still
running when this was written and is not in the set.

The first three logs are byte-identical before and after b2-real-03 was added (sha12 a0634d20de1a, 9d9bd32d42ec,
d8923f129248). The converter and the analysis are at 73a53df and 34500ab.

## Free check: the coded procedure equals the car's B2 at every step

The `procedure` arm runs the coded B2 procedure through the same runner, container and observation overlay. It gives
the live B2's estimate at 338 of 338 steps, on the Mac and in the Spark container
([`runs/procedure`](runs/procedure)). So the replay's input path reproduces what the car saw.

## Opus 5.5 (Anthropic API; cap US$40 for the set, approved)

The run was done in two passes in one folder, so the cap counts both
([`runs/claude-opus-5-5`](runs/claude-opus-5-5), [`claude-opus-5-5.log`](claude-opus-5-5.log)):

- 12:47–13:11 UTC: seeds 1001, 2001 and 2002, US$14.13.
- 14:03–14:27 UTC: seeds 3001 and 3002, resumed with a reason.

In total: 338 of 338 steps, 338 valid reports, 0 harness fallbacks, 0 repaired reports, 0 step errors, US$23.90,
17.3 s per step (p95 22.5 s), 3 workers.

Final-position error at the last step, cm ([`interim-opus.md`](interim-opus.md), [`interim-opus.json`](interim-opus.json)):

| Arm | n | median | IQR | min | max | median heading error (deg) | vs end circle (median) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B0 (dead reckoning) | 5 | 27.2 | 19.7 to 33.2 | 7.0 | 43.9 | 7.7 | 28.8 |
| B2 (the car's live procedure) | 5 | 6.9 | 3.1 to 8.2 | 2.8 | 20.3 | 3.7 | 6.1 |
| claude-opus-5-5 | 5 | 6.8 | 3.5 to 7.2 | 1.9 | 19.0 | 3.7 | 5.9 |

| Episode | truth sigma | B0 | B2 | Opus 5.5 |
| --- | --- | --- | --- | --- |
| b2-real-01 ep01 | 5.0 | 19.7 | 3.1 | 3.5 |
| b2-real-02 ep01 | 5.0 | 7.0 | 2.8 | 1.9 |
| b2-real-02 ep02 | 5.8 | 27.2 | 20.3 | 19.0 |
| b2-real-03 ep01 | 5.0 | 33.2 | 6.9 | 6.8 |
| b2-real-03 ep02 | 5.6 | 43.9 | 8.2 | 7.2 |

Opus is within a few centimetres of B2 in every episode. Both are inside or near the truth's own sigma (5–6 cm),
except b2-real-02 ep02, where B2 and Opus both end about 20 cm off. Five episodes cannot separate the two; the
simulated study's arm comparison stands on its own sample.

An oddity, not a fault: Opus called `move` 7 times, always `move(NONE)`, after it had decided to stay. The
frozen replay refused each call ("replay mode: the log's move is already executed"), and every one of those steps
has a valid report. The study's simulated Opus runs do the same at the same rate: 37 `move(NONE)` calls in 1976 steps
(1.9 %), against 7 in 338 (2.1 %) here.

## Qwen3.8 and Gemma 4 (Spark GPU, one server at a time)

- Qwen3.8 (`qwen38-flash-xhigh`, vLLM 127.0.0.1:8000): seeds 1001, 2001 and 2002 started at 12:55 UTC with 3
  workers (config 8969d38de361). At 14:12 it was at 109 of 201 steps, all valid, 0 fallbacks, 8 repaired, 127 s
  per step.
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

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: ran the replays, wrote this summary and chain.sh.
