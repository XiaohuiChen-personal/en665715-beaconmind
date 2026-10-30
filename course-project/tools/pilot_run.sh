#!/usr/bin/env bash
# Run the pilot's Opus replay on the Spark inside a one-off beaconmind-ros container (start it in tmux).
# Usage: bash tools/pilot_run.sh <run_dir_name> <seeds> <max_steps> <cap_usd> [obslogs_dir_name]
# AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: wrote this launcher.
set -euo pipefail
RUN=${1:?run dir name}; SEEDS=${2:?seeds}; MAXS=${3:?max steps}; CAP=${4:?cap usd}; OBS=${5:-obslogs}
cd "$(dirname "$0")/.."
docker run --rm --user 1000:1000 -e HOME=/tmp --network host \
  --env-file "$HOME/.config/beaconmind/secrets.env" \
  -e PYTHONPATH=/workspace/course-project/beaconmind/src -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$HOME/Projects/EN.665.715":/workspace beaconmind-ros:humble \
  python3 /workspace/course-project/tools/pilot_replay.py \
    --obslogs "/workspace/course-project/data/pilot-20261029/$OBS" \
    --out "/workspace/course-project/data/pilot-20261029/$RUN" \
    --seeds "$SEEDS" --max-steps "$MAXS" --cap-usd "$CAP"
