#!/usr/bin/env bash
# Run tools/replay_run.py in a one-off beaconmind-ros container on the Spark (start it inside tmux).
# Usage (Spark host, any directory):  bash course-project/tools/replay_run.sh --provider <key> --obslogs <dir> --out <dir> ...
# Path arguments (--obslogs, --out, --providers, --prompt, as "--opt value" or "--opt=value") may be relative to the
# repository root (course-project/..., ./course-project/...) or absolute inside the repository; anything else is
# refused, because a path outside the mounted repository would be written inside the throwaway container.
# The container uses the host network (vLLM on 127.0.0.1:8000, Ollama on 127.0.0.1:11435) and the secrets env_file
# (ANTHROPIC_API_KEY for the Opus arm; never printed). It records the git commit and, for the local servers, the
# host-side server facts the container cannot see (image digest, chat-template hash, Ollama settings).
# AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote this launcher (from tools/pilot_run.sh).
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
PATH_OPTS="--obslogs --out --providers --prompt"
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

# host-side facts about the local model servers ("{}" for anything not running)
INFO="$(python3 - <<'PYINFO'
import hashlib, json, subprocess
def out(*a):
    try:
        return subprocess.check_output(list(a), text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None
info = {}
if "bm-qwen38" in (out("docker", "ps", "--format", "{{.Names}}") or "").split():
    info["vllm_container"] = "bm-qwen38"
    info["image_id"] = out("docker", "inspect", "bm-qwen38", "--format", "{{.Image}}")
    mounts = json.loads(out("docker", "inspect", "bm-qwen38", "--format", "{{json .Mounts}}") or "[]")
    src = next((m["Source"] for m in mounts if m.get("Destination") == "/qwen38/chat_template.jinja"), None)
    if src:
        info["chat_template_sha12"] = hashlib.sha256(open(src, "rb").read()).hexdigest()[:12]
if out("tmux", "has-session", "-t", "bm-gemma4") is not None:
    info["ollama_server"] = "bm-gemma4 on 127.0.0.1:11435, OLLAMA_NUM_PARALLEL=8, OLLAMA_CONTEXT_LENGTH=65536 (tools/serve_gemma4.sh)"
    info["ollama_binary"] = out("/usr/local/bin/ollama", "--version")
print(json.dumps(info))
PYINFO
)"

exec docker run --rm --init --user "$(id -u):$(id -g)" -e HOME=/tmp --network host \
  --env-file "$HOME/.config/beaconmind/secrets.env" \
  -e PYTHONPATH=/workspace/course-project/beaconmind/src -e PYTHONDONTWRITEBYTECODE=1 \
  -e BM_GIT_COMMIT="$COMMIT" -e BM_GIT_DIRTY="$DIRTY" -e BM_SERVER_INFO="$INFO" -e BM_HOST="$(hostname)" \
  -v "$REPO":/workspace beaconmind-ros:humble \
  python3 /workspace/course-project/tools/replay_run.py "${ARGS[@]}"
