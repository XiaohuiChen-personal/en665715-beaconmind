#!/usr/bin/env bash
# Run tools/closed_loop_run.py in a one-off beaconmind-ros container on the Spark (start it inside tmux).
# Usage (Spark host, any directory):  bash course-project/tools/closed_loop_run.sh --driver <key|b2> --seeds <n> --out <dir> ...
# Path arguments (--out, --world, --prompt, as "--opt value" or "--opt=value") may be relative to the repository
# root (course-project/...) or absolute inside the repository; anything else is refused, because a path outside the
# mounted repository would be written inside the throwaway container.
# The container gets the secrets env_file (ANTHROPIC_API_KEY for the Claude drivers; never printed) and the git commit.
# It needs no local model server and does not touch the car, the micro-ROS agent or the camera relay.
# AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this launcher after the pattern of tools/replay_run.sh.
# AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: --dv is a path option (mapped into /workspace).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
COMMIT="$(git -C "$REPO" rev-parse --short=12 HEAD 2>/dev/null || echo unknown)"
DIRTY="$(git -C "$REPO" status --porcelain -- course-project/beaconmind course-project/tools course-project/configs course-project/prompts 2>/dev/null | wc -l)"

map_path() {   # repository-relative or absolute-in-repo path -> /workspace path
  local p="$1"
  p="${p#./}"
  case "$p" in
    "$REPO"/*) echo "/workspace/${p#"$REPO"/}" ;;
    course-project/*) echo "/workspace/$p" ;;
    /workspace/*) echo "$p" ;;
    *) echo "refused path outside the repository: $1" >&2; return 1 ;;
  esac
}

ARGS=()
PATH_OPTS="--out --world --prompt --watch-latch --dv"
while [ "$#" -gt 0 ]; do
  a="$1"; shift
  opt="${a%%=*}"
  if [[ " $PATH_OPTS " == *" $opt "* ]]; then
    if [[ "$a" == *=* ]]; then v="${a#*=}"; else v="${1:?$a needs a value}"; shift; fi
    ARGS+=("$opt" "$(map_path "$v")")
  else
    ARGS+=("$a")
  fi
done

exec docker run --rm --init --user "$(id -u):$(id -g)" -e HOME=/tmp --network host \
  --env-file "$HOME/.config/beaconmind/secrets.env" \
  -e PYTHONPATH=/workspace/course-project/beaconmind/src -e PYTHONDONTWRITEBYTECODE=1 \
  -e BM_GIT_COMMIT="$COMMIT" -e BM_GIT_DIRTY="$DIRTY" -e BM_HOST="$(hostname)" \
  -v "$REPO":/workspace beaconmind-ros:humble \
  python3 /workspace/course-project/tools/closed_loop_run.py "${ARGS[@]}"
