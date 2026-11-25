#!/usr/bin/env bash
# Second part of the real-log replay chain for set real-2026-11-25 (M3.T19), after b2-real-05 added three episodes
# (seeds 4001-4003) while chain.sh was running the Qwen3.8 resume for b2-real-03. chain.sh would have stopped the
# Qwen3.8 server and started Gemma 4 right after that resume, so its log (chain.log) was swapped for a FIFO nobody
# reads: its next log line blocks before the stop. This script:
#   1. waits for that Qwen3.8 resume (the runner chain.sh started) to exit, then ends chain.sh (blocked on the FIFO)
#      and puts chain.log back as a file;
#   2. resumes Qwen3.8 over the whole index; if the runner refuses because only the replay code's hashes changed (the
#      clone was pulled), the new seeds go to the sibling folder runs/<arm>+b2-real-05 (analyze merges them);
#   3. stops the Qwen3.8 server, checks that no model container is up and no process holds the GPU;
#   4. starts the Gemma 4 vLLM server, runs the Gemma arm over the whole index (workers from gemma-workers, default 8:
#      one per episode), stops the server.
# Usage (Spark, tmux bm-rr-chain2): bash chain2.sh <chain.sh shell pid> <the Qwen runner's pid>
# AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: written for the M3.T19 real-log replays.
set -u
cd "$HOME/Projects/en665715-beaconmind" || exit 1
R=course-project/data/real-replay/real-2026-11-25
T=course-project/tools
CHAIN_PID=$1
RUNNER_PID=$2
LOG=$R/chain.log
EARLY=$R/chain2.log
NEW_SEEDS=4001,4002,4003
SIBLING=b2-real-05
REASON="add b2-real-05 ep01-ep03 (seeds 4001, 4002, 4003)"
QLOG=$R/qwen38-flash-xhigh.log

note() { echo "$(date -u +%H:%M:%S) chain2: $*" >> "$EARLY"; }
say() { echo "$(date -u +%H:%M:%S) chain2: $*" >> "$LOG"; }
exits() { local n; n=$(grep -c '^EXIT' "$1" 2>/dev/null); echo "${n:-0}"; }
last_exit() { grep '^EXIT' "$1" | tail -1 | awk '{print $2}'; }

note "started; waiting for the Qwen3.8 runner (pid $RUNNER_PID) that chain.sh started"
while kill -0 "$RUNNER_PID" 2>/dev/null; do sleep 10; done
sleep 5
note "the Qwen3.8 runner exited: $(grep 'done: total spent' "$QLOG" | tail -1)"
if [ -p "$LOG" ]; then
  kill -KILL -- "-$CHAIN_PID" 2>/dev/null || kill -KILL "$CHAIN_PID" 2>/dev/null
  for _ in $(seq 1 30); do kill -0 "$CHAIN_PID" 2>/dev/null || break; sleep 1; done
  rm -f "$LOG"
  cat "$R/chain.log.part1" "$EARLY" > "$LOG"
  say "ended chain.sh (pid $CHAIN_PID, blocked on the FIFO before stopping Qwen3.8); chain.log restored"
else
  say "chain.log is not the FIFO: chain.sh may have gone on; stopping here"
  exit 1
fi

# run_arm <arm key> <log> [extra args...]: resume the arm's folder; on a refusal for code hashes only, the sibling folder
run_arm() {
  local arm="$1" log="$2"; shift 2
  say "$arm: resume runs/$arm over the whole index ($*)"
  bash $T/real_replay.sh --provider "$arm" --obslogs $R/obslogs --out "$R/runs/$arm" --resume-reason "$REASON" "$@" \
    >> "$log" 2>&1
  echo "EXIT $?" >> "$log"
  local code; code=$(last_exit "$log")
  if [ "$code" != 0 ] && tail -5 "$log" | grep -q "refusing to resume" \
     && tail -5 "$log" | grep "refusing to resume" | grep -qE "differs in \[('runner_sha12'|'real_replay_sha12')(, ('runner_sha12'|'real_replay_sha12'))?\]"; then
    say "$arm: the replay code changed on this clone (only its hashes differ); seeds $NEW_SEEDS go to runs/$arm+$SIBLING"
    bash $T/real_replay.sh --provider "$arm" --obslogs $R/obslogs --out "$R/runs/$arm+$SIBLING" --seeds "$NEW_SEEDS" "$@" \
      >> "$log" 2>&1
    echo "EXIT $?" >> "$log"
    code=$(last_exit "$log")
  fi
  say "$arm: exit $code; $(grep 'done: total spent' "$log" | tail -1)"
}

gpu_clear() {
  for _ in $(seq 1 12); do
    if ! docker ps --format '{{.Names}}' | grep -qxE 'bm-qwen38|bm-gemma4-vllm' \
       && [ -z "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null)" ]; then return 0; fi
    sleep 10
  done
  return 1
}

run_arm qwen38-flash-xhigh "$QLOG" --cap-usd 0 --workers 3

say "stopping the Qwen3.8 server: $(bash $T/serve_qwen38.sh stop 2>&1)"
if ! gpu_clear; then
  say "the GPU is not clear after stopping Qwen3.8; Gemma not started:"
  docker ps --format '{{.Names}} {{.Image}}' >> "$LOG"
  nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader >> "$LOG"
  exit 1
fi
say "GPU clear; starting Gemma 4 (vLLM): $(bash $T/serve_gemma4_vllm.sh start 2>&1 | tail -1)"
if ! bash $T/serve_gemma4_vllm.sh wait >> "$LOG" 2>&1; then
  say "Gemma 4 server did not become ready; stopping it: $(bash $T/serve_gemma4_vllm.sh stop 2>&1)"
  exit 1
fi
W=$(tr -dc '0-9' < "$R/gemma-workers" 2>/dev/null); W=${W:-8}
GLOG=$R/gemma4-26b.log
say "gemma4-26b: run over the whole index, $W workers"
bash $T/real_replay.sh --provider gemma4-26b --obslogs $R/obslogs --out "$R/runs/gemma4-26b" --cap-usd 0 --workers "$W" \
  >> "$GLOG" 2>&1
echo "EXIT $?" >> "$GLOG"
say "gemma4-26b: exit $(last_exit "$GLOG"); $(grep 'done: total spent' "$GLOG" | tail -1)"
say "stopping the Gemma 4 server: $(bash $T/serve_gemma4_vllm.sh stop 2>&1)"
say "done"
