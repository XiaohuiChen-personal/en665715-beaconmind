# OD8 — closed-loop model setting (proposal)

Date of the measurement: 2026-10-06 (Spark local time). Stamp: `20261006-185238`.
Status: **superseded 2026-10-06, 23:58 CT.** The Qwen 3.5 rule outcome below is unchanged. Xiaohui did not approve the API-model proposal. They pinned a different model. See "Xiaohui's decision".

## What was measured

One client at a time, on the existing `vllm-rosa` container. The container was started with `docker start`. It was not recreated. `docker inspect` recorded:

- `--max-model-len 131072`
- `--max-num-seqs 4`
- `--gpu-memory-utilization 0.60`

The prompt, the sampling, and the scenarios were the Module 4 v3.3 smoke harness (`smoke_test.py` SHA-256 `d624ca121856d64b35af17bf3c868c6525e307ea274ee152233738fe82c93126`). Each mode is 4 scenarios × K = 5, so n = 20. Decision latency is the record's `seconds` field.

Numbers below are the lines printed by `tools/latency_summary.py` into `latency-summary.txt`.

Thinking on:

`mode=thinking-on n=20 p50_s=327.9 p95_s=555.7 max_s=761.5 mean_turns=6.95 mean_tool_calls=7.5 mean_prompt_tokens_first_turn=6097.5 mean_completion_tokens_total=9342.2 n_errors=0 n_all_pass=5 n_length_or_overflow=0 length_or_overflow_s= first_record_s=405.8`

Thinking off:

`mode=thinking-off n=20 p50_s=13.7 p95_s=18.8 max_s=18.9 mean_turns=1 mean_tool_calls=0 mean_prompt_tokens_first_turn=6099.5 mean_completion_tokens_total=436.1 n_errors=0 n_all_pass=0 n_length_or_overflow=0 length_or_overflow_s= first_record_s=13.5`

Queue probe, over the whole run:

`max_running=1`
`max_waiting=0`
`probe_samples=3259`
`probe_na=0`
`probe_numeric=3259`
`probe_first_epoch=1791330758`
`probe_last_epoch=1791337370`
`probe_first_line=1791330758 running=0 waiting=0`
`probe_last_line=1791337370 running=1 waiting=0`

Those epochs are 2026-10-06T23:52:38Z and 2026-10-07T01:42:50Z. The last printed probe line is `1791337370 running=1 waiting=0`. At 2026-10-07T01:48:02Z, `vllm:num_requests_running` and `vllm:num_requests_waiting` both read 0.0. No numeric probe sample had `waiting` greater than 0 (`max_waiting=0`, `probe_na=0`, `probe_numeric=3259`), and `max_running` is 1.

With n = 20, nearest-rank p95 is the 19th of the 20 sorted decision times (`ceil(95/100 × 20) − 1` is the index of that element). The p95 values above are that rank. The first record of each mode is inside the percentile (`first_record_s` above). It was not dropped. There were no `length` or `context overflow` errors (`n_errors=0`, `n_length_or_overflow=0`), so there is no separate overflow latency. The percentile is all 20 decision attempts in each mode.

## Rule

README OD8, applied in M1.T4 step 9. The gate is p95 ≤ 60 s (README C10.8).

1. Thinking-on p95 is 555.7 s, which is above 60 s. The closed-loop local setting is not Qwen3.5 thinking on.
2. Thinking-off p95 is 18.8 s, which is within 60 s, but `n_all_pass` is 0, which is not greater than 0. Thinking off is not the closed-loop setting. Its pass count is 0 of 20, and `mean_tool_calls` is 0.
3. The remaining branch is the proposal below.

## Proposal

Qwen3.5-35B-A3B with thinking on runs **replay only**. Replay has no 60 s latency gate. Closed-loop runs and the demo use an API model chosen in M1.T11 and M1.T10.

Closed-loop episodes with this model run one at a time (no parallel episodes on `vllm-rosa`). README OD8's phrase "at `MAX_SEQS` 1" is met by that sequential-client condition. The server was not recreated, so `--max-num-seqs` is still 4. One client at a time is what kept `max_waiting` at 0.

No frontier API was called for this measurement.

## Question for Xiaohui

Do you approve this proposal?

- Qwen3.5 thinking on is replay-only.
- Qwen3.5 thinking off is not the closed-loop setting.
- Closed-loop runs and the demo use an API model chosen in M1.T11 and M1.T10.
- Any closed-loop episode that still uses this local model runs one at a time on `vllm-rosa`.

Reply with approval or with the setting you want instead. The answer will be recorded verbatim, with the date, in this file and in `CONTEXT.md`.

**Xiaohui's answer:** recorded 2026-10-06, 23:58 CT, in "Xiaohui's decision" below. The proposal in this file was not approved.

## Generative-AI disclosure

Grok 4.7 via Cursor, 2026-10-06, drafted this proposal from `latency-summary.txt`. The decision times were produced by `smoke_test.py` on the Spark. The summary numbers were not typed by hand.

## Xiaohui's decision

Date: 2026-10-06, 23:58 CT.

Xiaohui's words, recorded verbatim: "pin the qwen 3.8 flash next".

That sentence is the OD8 approval for the model identity. It does not approve the API-model proposal above. The Qwen 3.5 numbers in this file stay as measured.

Pinned closed-loop setting:

- Model: Qwen3.8-Flash-Next. The served checkpoint was `nvidia/Qwen3.8-Flash-Next-NVFP4`, not `Qwen/Qwen3.8-27B-FP8`.
- Mode: thinking on. That is the mode that produced the passes. Thinking off is not usable.
- Stamp `20261006-212041`, from `evidence/M1/M1.T15/qwen38-flash-latency-summary.txt`: thinking-on p50 98.9 s, p95 164.5 s, max 198 s, n_all_pass 14/20, mean tool calls 6.2. A read-only count of that JSONL is S1 4/5, S2 4/5, S3 4/5, S4 2/5. Thinking-off p95 82.9 s, n_all_pass 0/20, 7 errors, each `turn cap`.
- The 60 s p95 gate was missed. Xiaohui is pinning this model anyway and will explore other models later.

The same text is in `evidence/M1/M1.T15/od8-pin.md`. The harness was not rerun.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: recorded the Qwen3.8 pin, deferred Bonsai, and started M1.T5.
