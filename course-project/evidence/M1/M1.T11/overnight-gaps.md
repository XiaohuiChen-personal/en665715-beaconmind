# M1.T11 overnight gaps

Checked 2026-10-07T06:29:01Z against the acceptance list in `course-project/plan/M1-foundations.md` (M1.T11) and the files already in this folder. No API call was made. `secrets.env` was not opened. Files matching `opus20*` were not read or written.

The quality run in `quality-results.md` does not close the task. Xiaohui lifted the $5 cap for that run on 2026-10-07. The budget-guard demonstration the acceptance list still requires was never run, so the task stays in progress.

## Acceptance bullets

- **Spending approval with a date.** `quality-results.md` records the 2026-10-07 cap lift for the quality session. There is no `approval.md`. The lift waives the $5 cap for that run. It is not a budget-guard proof.
- **`model-ids.txt`.** Absent. `model-candidates.md` is a documentation retrieval from 2026-10-07. It is not `models.list()` output.
- **`api-facts.md`.** Absent. Prices and some request-field notes are in `model-candidates.md`. That file is not the acceptance file, and it was not copied or rewritten in this sweep.
- **`spike-openai.txt` and `spike-anthropic.txt`.** Absent. `quality-results.md` is K=1 on smoke scenarios S1–S4 (Sonnet 3/4, Sol 4/4, Opus 4/4, Astra 4/4; Fable not called). It is not the one-shot `compose_odometry` 0.25 m spike the acceptance line names, and it does not show the final pose in those two files.
- **`guard-refusal.txt`.** Absent. `beaconmind/harness/budget.py` and `tools/api_spike.py` are not in the tree. No run has shown `BudgetExceeded` before a request with no new ledger line. This is the demonstration that was never run.
- **Ledger total ≤ $5, and the leak check.** There is no `ledger-total.txt` and no spike ledger in this folder, so no spend total is on disk. `quality-results.md` says a pattern search of the evidence files then in this directory matched nothing. That sentence is not `guard-refusal.txt`, and it is not a ledger total. The $5 cap waiver does not fill this bullet.

## Other named evidence files

Also absent: `secrets-check.txt`, `summary.md`, and `frontier-latency.txt`. The task allows the optional frontier-latency step to be written as not run when OD8 does not need an API model. That sentence is not in a file here. OD8 is already pinned to the local Qwen3.8 model, so this optional file is not what blocks the task. The budget-guard bullet does.

M1.T11 was not marked done. No new provider call was made.

AI-assisted: Grok 4.7 via Cursor, 2026-10-07: compared the acceptance list with `quality-results.md` and the other files already in this folder, and wrote this gap note.
