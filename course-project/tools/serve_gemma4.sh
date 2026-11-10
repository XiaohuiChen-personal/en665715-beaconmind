#!/usr/bin/env bash
# Serve Gemma 4 26B-A4B for the BeaconMind L2 arm with parallel requests, without touching the system Ollama.
#
# Usage (Spark host):  bash course-project/tools/serve_gemma4.sh start|wait|stop|status|logs
#
# Why: the host's systemd Ollama (0.40.11, 127.0.0.1:11434) runs with one request slot (its log shows
# `n_seq_max = 1`), so eight replay episodes would queue behind one another, and changing the service's
# environment needs sudo. This script starts a second `ollama serve` as this user on 127.0.0.1:11435, with the same
# binary and the same model store (read only: /usr/share/ollama/.ollama/models; OLLAMA_NOPRUNE keeps it from
# writing there), so the arm uses exactly the model the pilot judge and Module 9 used (`gemma4:26b-a4b-it-bf16`,
# same manifest and blobs, same Modelfile defaults), with 8 slots of 65,536 tokens each.
# Memory: about 52 GB of weights plus the KV cache; it cannot share the GPU with tools/serve_qwen38.sh (about 97 GB).
#
# AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote this launcher.
set -euo pipefail

SESSION=bm-gemma4
PORT=11435
MODEL=gemma4:26b-a4b-it-bf16
LOG="$HOME/bm-scratch/ollama-${PORT}.log"
mkdir -p "$HOME/bm-scratch"

up() { curl -sf -m 5 "http://127.0.0.1:${PORT}/api/version" >/dev/null; }

case "${1:-}" in
  start)
    if up; then echo "already serving on ${PORT}"; exit 0; fi
    if docker ps --format '{{.Names}}' | grep -qx bm-qwen38; then echo "bm-qwen38 is running; stop it first"; exit 1; fi
    tmux new-session -d -s "$SESSION" \
      "OLLAMA_HOST=127.0.0.1:${PORT} OLLAMA_MODELS=/usr/share/ollama/.ollama/models OLLAMA_NOPRUNE=1 \
       OLLAMA_NUM_PARALLEL=8 OLLAMA_CONTEXT_LENGTH=65536 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_KEEP_ALIVE=-1 \
       /usr/local/bin/ollama serve >> '${LOG}' 2>&1"
    echo "started ${SESSION} on 127.0.0.1:${PORT} (log ${LOG}); run: $0 wait"
    ;;
  wait)
    for _ in $(seq 1 60); do up && break; sleep 2; done
    up || { echo "server did not come up"; tail -20 "$LOG"; exit 1; }
    # load the model with an empty request and keep it resident
    curl -sf -m 600 "http://127.0.0.1:${PORT}/api/generate" -d "{\"model\":\"${MODEL}\",\"keep_alive\":-1}" >/dev/null
    curl -s "http://127.0.0.1:${PORT}/api/ps"; echo
    grep -E "n_seq_max|n_ctx|OLLAMA_NUM_PARALLEL" "$LOG" | tail -4
    ;;
  stop)
    curl -s -m 30 "http://127.0.0.1:${PORT}/api/generate" -d "{\"model\":\"${MODEL}\",\"keep_alive\":0}" >/dev/null || true
    tmux kill-session -t "$SESSION" 2>/dev/null && echo "stopped ${SESSION}" || echo "${SESSION} was not running"
    ;;
  status)
    up && { echo "serving on ${PORT}"; curl -s "http://127.0.0.1:${PORT}/api/ps"; echo; } || echo "not serving"
    ;;
  logs)
    tail -n "${2:-40}" "$LOG"
    ;;
  *)
    echo "usage: $0 start|wait|stop|status|logs [n]"; exit 2
    ;;
esac
