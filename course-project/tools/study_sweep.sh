#!/usr/bin/env bash
# Run the main study's held-out replay sweep (pre-registration evidence/M4/M4.T1/prereg.md §3), from a clean checkout.
#
# Usage (Spark host, inside tmux):
#   bash course-project/tools/study_sweep.sh opus     # Claude Opus 5.5, 8 seeds at a time, cap US$250 (API; no GPU)
#   bash course-project/tools/study_sweep.sh local    # Gemma 4 on vLLM (16 at a time), then switch the GPU, Qwen3.8 (8)
# Each arm writes course-project/data/main/runs/drift2/<arm>/ and appends to <arm>.log there. A seed stopped by an
# infrastructure failure (replay_run.py exit 1) gets the pre-registered single resume, with its reason recorded. A cap
# stop (exit 2) is left for a person to check, as the pre-registration says.
#
# AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote this runner.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO"
OBS=course-project/data/main/obslogs/test/drift2
RUNS=course-project/data/main/runs/drift2
SEEDS=2000-2029
mkdir -p "$RUNS"

run_arm() {   # key workers cap
  local key=$1 workers=$2 cap=$3 rc
  echo "=== $(date -Is) $key: start (commit $(git rev-parse --short=12 HEAD), dirty $(git status --porcelain | wc -l))" | tee -a "$RUNS/$key.log"
  bash course-project/tools/replay_run.sh --provider "$key" --obslogs "$OBS" --out "$RUNS/$key" --seeds "$SEEDS" \
    --max-steps 150 --cap-usd "$cap" --workers "$workers" 2>&1 | tee -a "$RUNS/$key.log"
  rc=${PIPESTATUS[0]}
  if [ "$rc" -eq 1 ]; then
    echo "=== $(date -Is) $key: a seed failed; the single resume (prereg §3)" | tee -a "$RUNS/$key.log"
    bash course-project/tools/replay_run.sh --provider "$key" --obslogs "$OBS" --out "$RUNS/$key" --seeds "$SEEDS" \
      --max-steps 150 --cap-usd "$cap" --workers "$workers" \
      --resume-reason "automatic single resume after an infrastructure failure (prereg section 3)" 2>&1 | tee -a "$RUNS/$key.log"
    rc=${PIPESTATUS[0]}
  fi
  echo "=== $(date -Is) $key: finished, exit $rc" | tee -a "$RUNS/$key.log"
  return "$rc"
}

case "${1:-}" in
  opus)
    run_arm claude-opus-5-5 8 250
    ;;
  local)
    bash course-project/tools/serve_gemma4_vllm.sh status | grep -q "serving" || {
      bash course-project/tools/serve_qwen38.sh stop; bash course-project/tools/serve_gemma4_vllm.sh start
      bash course-project/tools/serve_gemma4_vllm.sh wait || exit 1; }
    run_arm gemma4-26b 16 0
    bash course-project/tools/serve_gemma4_vllm.sh stop
    sleep 10
    bash course-project/tools/serve_qwen38.sh start && bash course-project/tools/serve_qwen38.sh wait || exit 1
    run_arm qwen38-flash-xhigh 8 0
    ;;
  *)
    echo "usage: $0 opus|local"; exit 2
    ;;
esac
