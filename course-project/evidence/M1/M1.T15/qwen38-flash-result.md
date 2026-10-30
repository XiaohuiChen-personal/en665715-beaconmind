# Qwen3.8-Flash-Next — M1.T15 candidate 1

Checkpoint loaded: `nvidia/Qwen3.8-Flash-Next-NVFP4`, hybrid layout
`fc694b54fb0174e0913e6adf86691ef85a4ead47-fp8hybrid`. Recipe
https://github.com/blazux/qwen3.8-Flash-DGX at `5d944b3`, image
`qwen38-flash-dgx:v0.30`, container `qwen38-flash`. The harness still sends
model `Qwen/Qwen3.5-35B-A3B`; the server was given that served name so the
unchanged harness could call it. `Qwen/Qwen3.8-27B-FP8` in the cache is a
different checkpoint (`model_type` `qwen3_5`) and was not loaded.

The checkpoint chat template branches on `enable_thinking`, so both modes were
run: 4 scenarios × K=5, stamp `20261006-212041`. Harness hash
`d624ca121856d64b35af17bf3c868c6525e307ea274ee152233738fe82c93126`.

From `tools/latency_summary.py` (`qwen38-flash-latency-summary.txt`):

- Thinking on: p50 98.9 s, p95 164.5 s, max 198 s, n_all_pass 14/20. p95 ≤ 60 s: no.
- Thinking off: p50 11.7 s, p95 82.9 s, max 87.5 s, n_all_pass 0/20. p95 ≤ 60 s: no. The summary reports n_errors 7; each of those records has error `turn cap`.
- Queue: max_running 1, max_waiting 0 (1492 numeric samples, 0 NA).

The gate needs p95 ≤ 60 s and n_all_pass > 0. Neither mode meets it.

`docker stop qwen38-flash` after the summary. The container was not removed and the weights were not deleted. `vllm-rosa` stayed stopped.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, wrote this note from the command output above.
