# Ternary Bonsai 2 27B — M1.T15 candidate 2, stopped

Stopped 2026-10-06 22:43 CT. The harness finished 0 decisions. Do not resume tmux `bm-m1-bonsai`. Measured pace and the CUDA result are in `bonsai-speed.md`.

No harness percentiles. Do not treat the short checks below as p50 or p95.

The file in use is `prism-ml/Ternary-Bonsai-2-27B-gguf` `Ternary-Bonsai-2-27B-PTQ1_0.gguf` (5,946,648,928 bytes, server meta `PTQ1_0 - 1.75 bpw ternary`). It loaded. `PQ2_0` was not needed.

vLLM was not used. Upstream vLLM GGUF coverage does not include this pack's types (PTQ1_0 / PQ2_0). vLLM PR 39713 is an older Prism Q1_0 (types 42 and 43), not this pack, and it is not an aarch64 SM 12.1 build. Checked:

- https://github.com/vllm-project/vllm/pull/39713
- https://github.com/vllm-project/vllm/blob/main/docs/features/quantization/README.md
- https://github.com/ollama/ollama/issues/18521
- https://github.com/PrismML-Eng/llama.cpp/releases/tag/prism-b10754-2459f68

That PrismML release has Linux CUDA builds for x64 only. Its aarch64 artifacts are `llama-prism-b10754-2459f68-bin-ubuntu-arm64.tar.gz` (CPU) and `llama-prism-b10754-2459f68-bin-ubuntu-vulkan-arm64.tar.gz`. The demo script says CUDA and ROCm builds are x64 only: https://github.com/PrismML-Eng/Bonsai-demo/blob/main/scripts/download_binaries.sh

The harness is running on the CPU binary (`llama-server` build 10754, commit `2459f68b5`), `-ngl 0 -np 1 -c 65536`, alias `Qwen/Qwen3.5-35B-A3B`, stamp `20261006-221722`. `enable_thinking` is honored: a non-harness check with thinking on returned `reasoning_content` (33 completion tokens in 15.58 s). The Vulkan binary was tried and not used for the harness; a non-harness check there took 20.35 s for 30 completion tokens, and `nvidia-smi` showed no compute process on the CPU server.

Before the stop, tmux session `bm-m1-bonsai` had one slot processing (`running=1` `waiting=0`). `/metrics` returns HTTP 501, so this probe is not the vLLM queue metric. `qwen38-flash` and `vllm-rosa` were already stopped and were not removed. The session is now dead; see `bonsai-speed.md`.

Poll:

```bash
ssh -o ConnectTimeout=15 -o BatchMode=yes xiaohui_chen@spark-2a60 'tmux has-session -t bm-m1-bonsai && echo ALIVE || echo DEAD; grep -E "^(S[0-9]|THINK_|NOTHINK_|LATENCY|SUMMARY)" /home/xiaohui_chen/bonsai-smoke.log; STAMP=$(cat ~/Projects/EN.665.715/course-project/evidence/M1/M1.T15/bonsai-ptq1-stamp.txt); wc -l ~/Projects/EN.665.715/course-project/data/latency/${STAMP}-bonsai-ptq1-*.jsonl'
```

When `SUMMARY_DONE` is in the log, the percentiles are in `bonsai-ptq1-latency-summary.txt` on the Spark.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, wrote this note from the commands above.
