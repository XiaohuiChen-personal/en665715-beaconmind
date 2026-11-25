#!/usr/bin/env bash
# The rest of the real-log replay set real-2026-11-25 on the Spark, unattended (M3.T19; the lead's order of 2026-11-25:
# Opus, then Qwen3.8, then Gemma 4, one GPU model server at a time). Runs in tmux bm-rr-chain; every stage goes to
# chain.log next to this file.
#   1. wait for the running Qwen3.8 arm (tmux bm-rr-qwen, seeds 1001/2001/2002) to write its EXIT line;
#   2. resume it with the whole index (adds b2-real-03's seeds 3001 and 3002, and finishes any seed left incomplete);
#      if the runner refuses because only the replay code's hashes changed (a pull on this clone), run the new seeds
#      into the sibling folder runs/<arm>+b2-real-03 instead (tools/real_replay.py analyze merges an arm's folders);
#   3. stop the Qwen3.8 server, check that no container serves a model and no process holds the GPU;
#   4. start the Gemma 4 vLLM server, wait for it, run the Gemma arm over the whole index, stop the server.
# The Gemma worker count is read from gemma-workers in this folder when that stage starts (default 5, one per episode).
# AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: written for the M3.T19 real-log replays.
set -u
cd "$HOME/Projects/en665715-beaconmind" || exit 1
R=course-project/data/real-replay/real-2026-11-25
T=course-project/tools
LOG=$R/chain.log
NEW_SEEDS=3001,3002
SIBLING=b2-real-03
REASON="add b2-real-03 ep01 and ep02 (seeds 3001, 3002)"

say() { echo "$(date -u +%H:%M:%S) chain: $*" | tee -a "$LOG"; }
exits() { local n; n=$(grep -c '^EXIT' "$1" 2>/dev/null); echo "${n:-0}"; }
last_exit() { grep '^EXIT' "$1" | tail -1 | awk '{print $2}'; }

# run_arm <arm key> <log> [extra args...]: resume the arm's folder; on a refusal for code hashes only, the sibling folder
run_arm() {
  local arm="$1" log="$2"; shift 2
  local n; n=$(exits "$log")
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

say "started; waiting for the Qwen3.8 arm's first run (tmux bm-rr-qwen) to end"
QLOG=$R/qwen38-flash-xhigh.log
while [ "$(exits "$QLOG")" -lt 1 ]; do sleep 60; done
say "qwen38-flash-xhigh first run: exit $(last_exit "$QLOG"); $(grep 'done: total spent' "$QLOG" | tail -1)"

run_arm qwen38-flash-xhigh "$QLOG" --cap-usd 0 --workers 3

say "stopping the Qwen3.8 server: $(bash $T/serve_qwen38.sh stop 2>&1)"
if ! gpu_clear; then
  say "the GPU is not clear after stopping Qwen3.8; Gemma not started:"
  docker ps --format '{{.Names}} {{.Image}}' | tee -a "$LOG"
  nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader | tee -a "$LOG"
  exit 1
fi
say "GPU clear; starting Gemma 4 (vLLM): $(bash $T/serve_gemma4_vllm.sh start 2>&1 | tail -1)"
if ! bash $T/serve_gemma4_vllm.sh wait >> "$LOG" 2>&1; then
  say "Gemma 4 server did not become ready; stopping it: $(bash $T/serve_gemma4_vllm.sh stop 2>&1)"
  exit 1
fi
W=$(tr -dc '0-9' < "$R/gemma-workers" 2>/dev/null); W=${W:-5}
GLOG=$R/gemma4-26b.log
say "gemma4-26b: run over the whole index, $W workers"
bash $T/real_replay.sh --provider gemma4-26b --obslogs $R/obslogs --out "$R/runs/gemma4-26b" --cap-usd 0 --workers "$W" \
  >> "$GLOG" 2>&1
echo "EXIT $?" >> "$GLOG"
say "gemma4-26b: exit $(last_exit "$GLOG"); $(grep 'done: total spent' "$GLOG" | tail -1)"
say "stopping the Gemma 4 server: $(bash $T/serve_gemma4_vllm.sh stop 2>&1)"
say "done"
