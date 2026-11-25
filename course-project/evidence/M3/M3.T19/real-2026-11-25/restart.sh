#!/usr/bin/env bash
# Restart of the real-log replay chain for set real-2026-11-25 (M3.T19) after the Spark crashed at 18:13:57 UTC
# (the journal ends without a shutdown; it rebooted at 18:14:40). Every runner, chain and the Qwen3.8 server were gone.
# Runs in tmux bm-rr-restart, logging each stage to chain.log:
#   1. checks that no model container is up and no process holds the GPU, starts the Qwen3.8 server and waits for it;
#   2. side by side on that server: resumes runs/qwen38-flash-xhigh+b2-real-05 (seeds 4001-4003, interrupted by the
#      crash; a resume with its reason, the pre-registered rule for an infrastructure failure) and runs
#      runs/qwen38-flash-xhigh+b2-real-06 (seeds 5001, 5002; its own log);
#   3. stops the Qwen3.8 server, checks the GPU is clear;
#   4. starts the Gemma 4 vLLM server, runs the Gemma arm over the whole index (workers from gemma-workers, default one
#      per episode), stops the server.
# AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: written for the M3.T19 real-log replays.
set -u
cd "$HOME/Projects/en665715-beaconmind" || exit 1
R=course-project/data/real-replay/real-2026-11-25
T=course-project/tools
LOG=$R/chain.log
CRASH="the Spark crashed at 18:13:57 UTC (journal ends without a shutdown) and rebooted"
QLOG=$R/qwen38-flash-xhigh.log
QLOG6=$R/qwen38-flash-xhigh+b2-real-06.log

say() { echo "$(date -u +%H:%M:%S) restart: $*" >> "$LOG"; }
last_exit() { grep '^EXIT' "$1" | tail -1 | awk '{print $2}'; }

gpu_clear() {
  for _ in $(seq 1 12); do
    if ! docker ps --format '{{.Names}}' | grep -qxE 'bm-qwen38|bm-gemma4-vllm' \
       && [ -z "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null)" ]; then return 0; fi
    sleep 10
  done
  return 1
}

say "started"
if ! gpu_clear; then
  say "a model container is up or a process holds the GPU; nothing started:"
  docker ps --format '{{.Names}} {{.Image}}' >> "$LOG"
  exit 1
fi
say "starting Qwen3.8: $(bash $T/serve_qwen38.sh start 2>&1 | tail -1)"
if ! bash $T/serve_qwen38.sh wait >> "$LOG" 2>&1; then
  say "Qwen3.8 server did not become ready; stopping it: $(bash $T/serve_qwen38.sh stop 2>&1)"
  exit 1
fi

say "qwen38-flash-xhigh: resume runs/qwen38-flash-xhigh+b2-real-05 (4001-4003) and run runs/qwen38-flash-xhigh+b2-real-06 (5001, 5002) side by side"
( bash $T/real_replay.sh --provider qwen38-flash-xhigh --obslogs $R/obslogs --out "$R/runs/qwen38-flash-xhigh+b2-real-05" \
    --seeds 4001,4002,4003 --cap-usd 0 --workers 3 --resume-reason "$CRASH" >> "$QLOG" 2>&1; echo "EXIT $?" >> "$QLOG" ) &
A=$!
( bash $T/real_replay.sh --provider qwen38-flash-xhigh --obslogs $R/obslogs --out "$R/runs/qwen38-flash-xhigh+b2-real-06" \
    --seeds 5001,5002 --cap-usd 0 --workers 2 >> "$QLOG6" 2>&1; echo "EXIT $?" >> "$QLOG6" ) &
B=$!
wait $A $B
say "qwen38-flash-xhigh+b2-real-05: exit $(last_exit "$QLOG"); $(grep 'done: total spent' "$QLOG" | tail -1)"
say "qwen38-flash-xhigh+b2-real-06: exit $(last_exit "$QLOG6"); $(grep 'done: total spent' "$QLOG6" | tail -1)"

say "stopping the Qwen3.8 server: $(bash $T/serve_qwen38.sh stop 2>&1)"
if ! gpu_clear; then
  say "the GPU is not clear after stopping Qwen3.8; Gemma not started:"
  docker ps --format '{{.Names}} {{.Image}}' >> "$LOG"
  exit 1
fi
say "GPU clear; starting Gemma 4 (vLLM): $(bash $T/serve_gemma4_vllm.sh start 2>&1 | tail -1)"
if ! bash $T/serve_gemma4_vllm.sh wait >> "$LOG" 2>&1; then
  say "Gemma 4 server did not become ready; stopping it: $(bash $T/serve_gemma4_vllm.sh stop 2>&1)"
  exit 1
fi
W=$(tr -dc '0-9' < "$R/gemma-workers" 2>/dev/null)
W=${W:-$(python3 -c "import json,sys; print(len(json.load(open(sys.argv[1]))['episodes']))" "$R/obslogs/index.json")}
GLOG=$R/gemma4-26b.log
say "gemma4-26b: run over the whole index, $W workers"
bash $T/real_replay.sh --provider gemma4-26b --obslogs $R/obslogs --out "$R/runs/gemma4-26b" --cap-usd 0 --workers "$W" \
  >> "$GLOG" 2>&1
echo "EXIT $?" >> "$GLOG"
say "gemma4-26b: exit $(last_exit "$GLOG"); $(grep 'done: total spent' "$GLOG" | tail -1)"
say "stopping the Gemma 4 server: $(bash $T/serve_gemma4_vllm.sh stop 2>&1)"
say "done"
