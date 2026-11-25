#!/usr/bin/env bash
# Take over the real-log replay chain for set real-2026-11-25 (M3.T19) when a batch adds episodes while the chain is
# running Qwen3.8 (which it would stop next, before Gemma 4). Before starting this, the running chain's log (chain.log)
# is moved to SAVED_PART and replaced by a FIFO nobody reads: the chain's next log line blocks before the Qwen3.8 stop.
# This script:
#   1. waits for the running chain's Qwen3.8 runner to exit, then ends that chain (blocked on the FIFO) and puts
#      chain.log back as a file (SAVED_PART, then this script's own early lines);
#   2. resumes Qwen3.8 over the whole index; if the runner refuses because only the replay code's hashes changed (the
#      clone was pulled), the new seeds go to the sibling folder runs/<arm>+SIBLING (analyze merges an arm's folders);
#   3. stops the Qwen3.8 server, checks that no model container is up and no process holds the GPU;
#   4. starts the Gemma 4 vLLM server, runs the Gemma arm over the whole index (workers from gemma-workers, default:
#      one per episode), stops the server.
# Usage (Spark, in tmux): bash takeover.sh CHAIN_PID RUNNER_PID NEW_SEEDS SIBLING SAVED_PART EARLY_LOG
#   chain2.sh was this script for b2-real-05 (seeds 4001-4003); takeover.sh b2-real-06 (5001, 5002) took over from it.
# AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: written for the M3.T19 real-log replays.
set -u
cd "$HOME/Projects/en665715-beaconmind" || exit 1
R=course-project/data/real-replay/real-2026-11-25
T=course-project/tools
CHAIN_PID=$1
RUNNER_PID=$2
NEW_SEEDS=$3
SIBLING=$4
SAVED_PART=$R/$5
EARLY=$R/$6
LOG=$R/chain.log
REASON="add $SIBLING (seeds $NEW_SEEDS)"
ME=$(basename "$EARLY" .log)
QLOG=$R/qwen38-flash-xhigh.log

note() { echo "$(date -u +%H:%M:%S) $ME: $*" >> "$EARLY"; }
say() { echo "$(date -u +%H:%M:%S) $ME: $*" >> "$LOG"; }
exits() { local n; n=$(grep -c '^EXIT' "$1" 2>/dev/null); echo "${n:-0}"; }
last_exit() { grep '^EXIT' "$1" | tail -1 | awk '{print $2}'; }

note "started; waiting for the Qwen3.8 runner (pid $RUNNER_PID) that the running chain (pid $CHAIN_PID) started"
while kill -0 "$RUNNER_PID" 2>/dev/null; do sleep 10; done
sleep 5
note "the Qwen3.8 runner exited: $(grep 'done: total spent' "$QLOG" | tail -1)"
if [ -p "$LOG" ]; then
  kill -KILL -- "-$CHAIN_PID" 2>/dev/null || kill -KILL "$CHAIN_PID" 2>/dev/null
  for _ in $(seq 1 30); do kill -0 "$CHAIN_PID" 2>/dev/null || break; sleep 1; done
  rm -f "$LOG"
  cat "$SAVED_PART" "$EARLY" > "$LOG"
  say "ended the running chain (pid $CHAIN_PID, blocked on the FIFO before stopping Qwen3.8); chain.log restored"
else
  note "chain.log is not the FIFO: the running chain may have gone on; stopping here"
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
