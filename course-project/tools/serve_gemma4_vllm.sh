#!/usr/bin/env bash
# Serve Gemma 4 26B-A4B (google/gemma-4-26B-A4B-it, bf16) with vLLM on the Spark, for the BeaconMind L2 arm.
#
# Usage (Spark host):  bash course-project/tools/serve_gemma4_vllm.sh start|wait|stop|status|logs
#
# Why vLLM: on the user-level Ollama (tools/serve_gemma4.sh, 8 slots) a gate step took about 10 minutes with 8 seeds
# in parallel (about 8.5 tokens/s per slot, about 5,000 thinking tokens a step), about 41 hours for the held-out
# sweep; vLLM's continuous batching serves the same model far faster. The weights are Google's official checkpoint
# (not the locally built GGUF in Ollama), the image is the one that serves Qwen3.8 (vLLM 0.30.0, proven on this GPU),
# and the model's own parsers turn tool calls and thinking into OpenAI fields (`--tool-call-parser gemma4
# --reasoning-parser gemma4`). Thinking is switched on per request (`chat_template_kwargs.enable_thinking`).
# Binds 127.0.0.1:8001. Memory: --gpu-memory-utilization 0.80 (about 97 GB), so it cannot share the GPU with
# tools/serve_qwen38.sh; stop one before starting the other.
#
# AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote this launcher.
set -euo pipefail

NAME=bm-gemma4-vllm
IMAGE=qwen38-flash-dgx:v0.30
SERVED=google/gemma-4-26B-A4B-it
PORT=8001
SNAPDIR="$HOME/.cache/huggingface/hub/models--google--gemma-4-26B-A4B-it/snapshots"

ready() { curl -sf -m 5 "http://127.0.0.1:${PORT}/v1/models" | grep -q "\"${SERVED}\""; }

case "${1:-}" in
  start)
    if docker ps --format '{{.Names}}' | grep -qx "$NAME"; then echo "$NAME already running"; exit 0; fi
    if docker ps --format '{{.Names}}' | grep -qx bm-qwen38; then echo "bm-qwen38 is running; stop it first"; exit 1; fi
    if tmux has-session -t bm-gemma4 2>/dev/null; then echo "the Ollama Gemma server (bm-gemma4) is running; stop it first"; exit 1; fi
    REV="$(ls "$SNAPDIR" | head -1)"
    [ -n "$REV" ] || { echo "no snapshot under $SNAPDIR"; exit 1; }
    docker rm "$NAME" >/dev/null 2>&1 || true
    docker run -d --name "$NAME" --gpus all --ipc host --shm-size 16g -p "127.0.0.1:${PORT}:8000" \
      -e HF_HOME=/hf -e HF_HUB_OFFLINE=1 -v "$HOME/.cache/huggingface:/hf" --entrypoint vllm "$IMAGE" \
      serve "/hf/hub/models--google--gemma-4-26B-A4B-it/snapshots/${REV}" --served-model-name "$SERVED" \
      --host 0.0.0.0 --port 8000 --max-model-len 65536 --max-num-seqs 16 --gpu-memory-utilization 0.80 \
      --enable-prefix-caching --enable-chunked-prefill --max-num-batched-tokens 8192 \
      --enable-auto-tool-choice --tool-call-parser gemma4 --reasoning-parser gemma4 >/dev/null
    echo "started $NAME (snapshot $REV); run: $0 wait"
    ;;
  wait)
    for _ in $(seq 1 180); do
      if ready; then echo "ready: ${SERVED} on 127.0.0.1:${PORT}"; exit 0; fi
      if ! docker ps --format '{{.Names}}' | grep -qx "$NAME"; then echo "$NAME exited:"; docker logs --tail 40 "$NAME"; exit 1; fi
      sleep 10
    done
    echo "not ready after 30 min"; exit 1
    ;;
  stop)
    docker stop "$NAME" >/dev/null 2>&1 && echo "stopped $NAME" || echo "$NAME was not running"
    ;;
  status)
    docker ps -a --filter "name=^${NAME}$" --format '{{.Names}}\t{{.Status}}'
    ready && echo "serving ${SERVED}" || echo "not serving"
    ;;
  logs)
    docker logs --tail "${2:-60}" "$NAME"
    ;;
  *)
    echo "usage: $0 start|wait|stop|status|logs [n]"; exit 2
    ;;
esac
