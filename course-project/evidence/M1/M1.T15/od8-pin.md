# OD8 pin — Qwen3.8-Flash-Next

Date: 2026-10-06, 23:58 CT.

Xiaohui's words, recorded verbatim: "pin the qwen 3.8 flash next".

That sentence is the approval for the closed-loop model identity. The 60 s p95 gate was missed. Xiaohui is pinning this model anyway and will explore other models later.

## What is pinned

- Checkpoint that was served: `nvidia/Qwen3.8-Flash-Next-NVFP4`. This is not `Qwen/Qwen3.8-27B-FP8`.
- Mode: thinking on. That is the mode that produced the passes. Thinking off is not usable.
- Stamp: `20261006-212041`.
- One client at a time. Queue from `qwen38-flash-latency-summary.txt`: `max_running=1`, `max_waiting=0`.

Numbers below are copied from `qwen38-flash-latency-summary.txt` and from a read-only count of the stamp's JSONL on the Spark (2026-10-06). The harness was not rerun.

Thinking on (`20261006-212041-qwen38-flash-think.jsonl`, n = 20):

`mode=thinking-on n=20 p50_s=98.9 p95_s=164.5 max_s=198 mean_turns=6.3 mean_tool_calls=6.2 mean_prompt_tokens_first_turn=6135.5 mean_completion_tokens_total=3838.95 n_errors=0 n_all_pass=14`

Per scenario, `check.all_pass`: S1 4/5, S2 4/5, S3 4/5, S4 2/5.

Thinking off (`20261006-212041-qwen38-flash-nothink.jsonl`, n = 20):

`mode=thinking-off n=20 p50_s=11.7 p95_s=82.9 max_s=87.5 mean_turns=11.55 mean_tool_calls=11.2 mean_prompt_tokens_first_turn=6099.5 mean_completion_tokens_total=1173 n_errors=7 n_all_pass=0`

Per scenario, `check.all_pass`: S1 0/5, S2 0/5, S3 0/5, S4 0/5. The seven errors are all `turn cap`.

p95 is above 60 s in both modes. Neither mode meets the gate (p95 ≤ 60 s and n_all_pass > 0). The pin stands anyway.

The Qwen 3.5 measurement in `evidence/M1/M1.T4/` is unchanged. The same approval is appended to `evidence/M1/M1.T4/od8-decision.md`.

## Generative-AI disclosure

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: recorded the Qwen3.8 pin, deferred Bonsai, and started M1.T5.
