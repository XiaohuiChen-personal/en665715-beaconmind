# Opus 5.5 K=5 vs Qwen3.8-Flash-Next thinking-on

Xiaohui approved this comparison on 2026-10-07. M1.T11 stays `in-progress`. This note does not close the budget guard or the other acceptance files.

Both arms are 4 scenarios × K=5 = 20 decisions, one client at a time. The prompt, tool schemas, `run_tool`, and `check` are the Module 4 smoke harness (`assignments/assignment4/system-prompt/tools/smoke_test.py`, sha256 `d624ca121856d64b35af17bf3c868c6525e307ea274ee152233738fe82c93126`). Pass checks were not changed.

Opus used the same request settings as the K=1 line that passed 4/4. From `opus20-run.log`:

`{"thinking": null, "output_config": {"effort": "medium"}, "reasoning": null, "store": null, "max_tokens": 64000, "temperature": null, "tool_choice": null}`

The queue was only `claude-opus-5-5`. Sonnet, Sol, Astra, and Fable were not called. Every served model id in `opus20-records.jsonl` is `claude-opus-5-5`. The run started `2026-10-07T01:24:51-05:00` and exited 0 at `2026-10-07T01:31:13-05:00` in tmux `bm-m1t11-opus20` (session ended; container `bm-opus20` removed). vLLM was not started. The camera was not touched.

Percentiles use the same nearest-rank rule as `beaconmind.metrics.latency` (`ceil(q/100*n)-1`). For n=20, p50 is the 10th sorted value and p95 is the 19th. Sorted Opus seconds: 16.6, 16.7, 17.1, 17.2, 17.3, 17.7, 18.1, 18.2, 18.4, 18.8, 18.8, 19.2, 19.6, 19.7, 19.9, 20.7, 21.5, 21.5, 21.8, 22.2.

Qwen thinking-on numbers are copied from `evidence/M1/M1.T15/qwen38-flash-latency-summary.txt` (stamp `20261006-212041`) and the per-scenario count in `evidence/M1/M1.T15/od8-pin.md`. That arm was not rerun.

| Field | Opus 5.5, effort medium | Qwen3.8-Flash-Next, thinking on |
| --- | --- | --- |
| n | 20 | 20 |
| p50 | 18.8 s | 98.9 s |
| p95 | 21.8 s | 164.5 s |
| max | 22.2 s | 198 s |
| n_all_pass | 20/20 | 14/20 |
| S1 | 5/5 | 4/5 |
| S2 | 5/5 | 4/5 |
| S3 | 5/5 | 4/5 |
| S4 | 5/5 | 2/5 |
| mean tool calls | 5.75 | 6.2 |
| n_errors | 0 | 0 |

Opus p95 is 21.8 s, under the 60 s gate, and every scenario passed. Qwen thinking-on p95 is 164.5 s, and 6 of 20 decisions failed the same checker (4 of those 6 are S4).

Records: `opus20-records.jsonl` (20 lines). Runner stdout: `opus20-run.log`. The K=1 files `quality-records.jsonl`, `quality-results.md`, and `quality-run.log` were not rewritten.

No API key or secrets-file contents were written into these files.

AI-assisted: Grok 4.7 via Cursor, 2026-10-07: ran the 20-decision Opus comparison.
