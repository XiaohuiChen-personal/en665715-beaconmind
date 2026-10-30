# Ternary-Bonsai-2-27B llama.cpp fallback

Date: 2026-10-06

Xiaohui's decision: if no DGX Spark vLLM build exists for Ternary-Bonsai-2-27B, serve the 2-bit GGUF with llama.cpp.

Filename: `Ternary-Bonsai-2-27B-PQ2_0.gguf`

Repo: https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf

Do not start this model until the Qwen 3.8 latency run has finished and GPU memory is free.

Disclosure: AI-assisted: Grok 4.7 via Cursor, 2026-10-06: recorded the llama.cpp fallback.
