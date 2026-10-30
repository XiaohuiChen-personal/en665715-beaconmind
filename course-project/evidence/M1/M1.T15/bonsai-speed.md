# Ternary Bonsai — too slow to use as a decider

Date: 2026-10-06. Stamp of the stopped harness: `20261006-221722`. M1.T15 is not done. OD8 is not approved. Qwen 3.8 was not restarted and its numbers were not rewritten.

## Finished decisions

None. `bonsai-smoke.log` ends at `SMOKE_THINK_START 2026-10-06T22:17:22-05:00`. `20261006-221722-bonsai-ptq1-think.jsonl` is 0 bytes, so no scenario completed and no tool call was recorded.

The one in-flight request, thinking on, was stopped at 2026-10-06T22:43:21-05:00 (about 26 minutes):

- Prompt: 6103 tokens, 851.51 s, 7.17 tokens/s (`prompt processing, n_tokens = 6103, progress = 1.00`).
- Generation still running: 2799 tokens at 3.97 tokens/s (`n_gen = 2799, tg = 3.97 t/s`). No finish, so no tool call returned.

That is already far above a fast tool-calling pace. The smoke was stopped so it would not keep the machine busy.

## What was stopped

- `llama-server` PID 1577607, and the smoke processes 1577600, 1577601, 1577662, and `smoke_test.py` 1577666.
- tmux `bm-m1-bonsai` is gone. Port 8000 is down.
- A later CUDA load probe (PID 1618729, port 8011) exited on its own because the model failed to load. That port is down too.
- `qwen38-flash` and `vllm-rosa` were already exited. They were not started.

## Why it is slow

The harness used the Prism **CPU** binary, not the GPU:

- Binary: `/home/xiaohui_chen/bonsai-m1/llama-prism-b10754-2459f68/llama-server` (aarch64, build 10754, commit `2459f68`). `ldd` shows `libggml` and `libggml-base` only.
- Flags: `-ngl 0 -np 1 -t 18 -c 65536 --reasoning auto`. No GPU layers.
- File loaded: `Ternary-Bonsai-2-27B-PTQ1_0.gguf` (5,946,648,928 bytes, GGUF architecture `qwen35`). `PQ2_0` is not on disk and was not loaded. The CPU server had already reported this file as `PTQ1_0 - 1.75 bpw ternary`.
- Thinking was on (`smoke_test.py … 5 1`). The first prompt alone was 6103 tokens. At 7.17 tokens/s that is 851 s before the first generated token, then about 4 tokens/s of reasoning with no `max_tokens` cap.

Earlier non-harness checks, already recorded in `bonsai-ptq1-in-progress.md` and not rerun here: CPU thinking, 33 completion tokens in 15.58 s; Vulkan, 30 completion tokens in 20.35 s. Vulkan was slower and was not used again.

## No faster path on this machine

A CUDA llama.cpp is on the Spark, and it does see the GB10:

- Path: `/home/xiaohui_chen/Projects/llama.cpp/build/bin/llama-server`
- `version: 8401 (a69d54f99)`, built for Linux aarch64, `GGML_CUDA=ON`, `CUDA : ARCHS = 1210`, device NVIDIA GB10 compute capability 12.1.
- Source remote: https://github.com/ggerganov/llama.cpp (stock), not the Prism fork.

It cannot run this GGUF. Load failed in about 2 s:

`gguf_init_from_file_impl: tensor 'output.weight' has invalid ggml type 143. should be in [0, 41)`

Stock ggml types stop at 40 (`GGML_TYPE_COUNT = 41`), including `TQ1_0` / `TQ2_0`. This file’s type id is 143. The Prism CPU library tells a mismatched file to use `PQ2_0` (ggml type id 142). Neither 142 nor 143 is in the CUDA build. No tool-calling prompt was sent.

Prism’s own release has no Linux aarch64 CUDA build. Latest tag checked 2026-10-06: https://github.com/PrismML-Eng/llama.cpp/releases/tag/prism-b10754-2459f68 (published 2026-10-02). Linux CUDA assets are x64 only (`linux-cuda-12.4-x64`, `12.8-x64`, `13.3-x64`). The aarch64 Linux assets are `llama-prism-b10754-2459f68-bin-ubuntu-arm64.tar.gz` (the CPU build already used) and `llama-prism-b10754-2459f68-bin-ubuntu-vulkan-arm64.tar.gz`. `win-cuda-13.4-arm64` is Windows, not this machine. The demo script says CUDA and ROCm builds are x64 only: https://github.com/PrismML-Eng/Bonsai-demo/blob/main/scripts/download_binaries.sh

`ghcr.io/ggml-org/llama.cpp:server-cuda` is present (arm64, created 2026-04-19) and was not started. It is stock ggml-org, the same family that rejects type 143.

Bonsai on this Spark is not a fast decider. The only binary that can load `PTQ1_0` is the CPU one, at about 7 tokens/s prefill and 4 tokens/s decode.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, wrote this note from the Spark log, process list, and the CUDA load error above.
