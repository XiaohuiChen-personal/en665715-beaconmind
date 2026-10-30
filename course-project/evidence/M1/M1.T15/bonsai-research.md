# Bonsai — research only

Date: 2026-10-06, 23:58 CT. Xiaohui decided Bonsai is a research action item only.

Do not serve it. Do not download more weights. Do not run llama.cpp.

## What was tried

Ternary-Bonsai-2-27B, file `Ternary-Bonsai-2-27B-PTQ1_0.gguf`, on the Prism CPU llama.cpp binary. Stamp `20261006-221722`. Generation was still at 3.97 tok/s (2799 tokens) when the process was stopped; the prompt was 6103 tokens at 7.17 tok/s. Finished decisions: 0. No tool call was recorded. Detail is in `bonsai-speed.md`.

It is not a closed-loop candidate.

## CUDA

The CUDA llama.cpp on the Spark cannot load this file. The load error was `tensor 'output.weight' has invalid ggml type 143`. Stock ggml types on that build stop at 40. Prism publishes no Linux aarch64 CUDA build (checked 2026-10-06; see `bonsai-speed.md`). Future research may look for an aarch64 CUDA build that understands type 143. That search is not part of the closed-loop pin, and it is not a reason to start llama.cpp again.

## Generative-AI disclosure

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: recorded the Qwen3.8 pin, deferred Bonsai, and started M1.T5.
