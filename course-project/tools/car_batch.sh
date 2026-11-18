#!/usr/bin/env bash
# Run tools/car_batch.py on the Spark: the R2 recorder for the whole batch, then the batch in a one-off container.
#
#   bash course-project/tools/car_batch.sh <label> run --world course-project/configs/arenas/<world>.json \
#        --scenarios course-project/configs/arenas/real-room-scenarios.json --initial-pose 2.5,1.5,90 --episodes 10 --policy b2
#   bash course-project/tools/car_batch.sh - record-pass --operator xiaohui --stand-session <s> --floor-session <s>
#   bash course-project/tools/car_batch.sh - clear-halt --out course-project/data/real/<session>/batch --operator xiaohui
#   BM_ROS_DOMAIN_ID=42 ... (a simulated car node; never the real car)
#
# The batch folder is course-project/data/batches/<label> (unless --out or --label is given): a rerun with the same
# label finds the earlier halt, manifest and spend. Run it inside tmux (or with nohup): a closed ssh session ends it.
# For `run` without --dry-run it starts the recorder (tools/record_session.sh start batch-<label> --camera off: the
# batch itself is the camera's one client and saves every frame) unless a session is already active, with a watchdog
# longer than the batch's own cap, and stops it when the batch ends, halted or not. The batch halts by itself if the
# recorder stops first (rule R2). Paths under course-project/ are mapped to /workspace. The container gets the secrets
# file only for a model policy's key (as tools/closed_loop_run.sh).
#
# AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this wrapper.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
CP="$REPO/course-project"
LABEL="${1:?usage: car_batch.sh <label|-> <car_batch.py arguments>}"; shift
DOMAIN="${BM_ROS_DOMAIN_ID:-0}"
COMMIT="$(git -C "$REPO" rev-parse --short=12 HEAD 2>/dev/null || echo unknown)"
DIRTY="$(git -C "$REPO" status --porcelain -- course-project/beaconmind course-project/tools course-project/configs course-project/prompts 2>/dev/null | wc -l)"

ARGS=""; DRY=0; CMD="${1:-}"; HOURS=6; HAS_OUT=0
prev=""
for a in "$@"; do
  opt="${a%%=*}"; val=""
  [[ "$a" == --*=* ]] && val="${a#*=}"
  case "$a" in
    "$REPO"/*) a="/workspace/${a#"$REPO"/}" ;;
    course-project/*) a="/workspace/$a" ;;
    --*="$REPO"/*) a="$opt=/workspace/${val#"$REPO"/}" ;;
    --*=course-project/*) a="$opt=/workspace/$val" ;;
  esac
  # a path option must stay inside the repository: anything else would be written inside the container and vanish
  for popt in --out --latch --marker --world --scenarios --prompt; do
    v=""
    [ "$prev" = "$popt" ] && v="$a"
    [ "$opt" = "$popt" ] && [ -n "$val" ] && v="${a#*=}"
    if [ -n "$v" ] && [[ "$v" != /workspace/* ]]; then
      echo "car_batch.sh: $popt $v is outside the repository; nothing was sent" >&2; exit 2
    fi
  done
  [ "$a" = "--dry-run" ] && DRY=1
  [ "$prev" = "--batch-hours" ] && HOURS="$a"
  [ "$opt" = "--batch-hours" ] && [ -n "$val" ] && HOURS="$val"
  { [ "$opt" = "--out" ] || [ "$opt" = "--label" ]; } && HAS_OUT=1
  prev="$a"
  ARGS+=" $(printf '%q' "$a")"
done
# the batch's folder is found by its label on every rerun (halt, manifest and spend live there, not in a recorder session)
if [ "$CMD" = "run" ] && [ "$HAS_OUT" = 0 ]; then
  [ "$LABEL" = "-" ] && { echo "car_batch.sh: run needs a label (first argument)" >&2; exit 2; }
  ARGS+=" --label $(printf '%q' "$LABEL")"
fi

STARTED=0
if [ "$CMD" = "run" ] && [ "$DRY" = 0 ] && [ "$DOMAIN" = 0 ]; then
  if [ -f "$CP/data/real/.active" ]; then
    # a session is marked active: it must really be recording (a crashed recorder leaves the mark behind)
    tmux has-session -t bm-rec 2>/dev/null || { echo "car_batch.sh: data/real/.active exists but the recorder (tmux bm-rec) is not running: stop or repair it first; nothing was sent" >&2; exit 2; }
  else
    WATCHDOG="$(python3 -c "import sys; print(float(sys.argv[1]) + 1.0)" "$HOURS")" || { echo "car_batch.sh: --batch-hours $HOURS is not a number" >&2; exit 2; }
    bash "$CP/tools/record_session.sh" start "batch-$LABEL" --camera off --max-hours "$WATCHDOG" \
      --note "unattended batch (tools/car_batch.sh)" || { echo "car_batch.sh: the recorder did not start; nothing was sent" >&2; exit 2; }
    STARTED=1
  fi
fi
stop_recorder() { if [ "$STARTED" = 1 ]; then bash "$CP/tools/record_session.sh" stop "batch ended" || true; fi; }
trap stop_recorder EXIT
trap 'exit 130' INT TERM HUP        # the container gets the signal through docker; this only makes the EXIT trap run

SECRETS=()
[ -f "$HOME/.config/beaconmind/secrets.env" ] && SECRETS=(--env-file "$HOME/.config/beaconmind/secrets.env")
docker run --rm --init --network host --user "$(id -u):$(id -g)" "${SECRETS[@]}" \
  -e ROS_DOMAIN_ID="$DOMAIN" -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
  -e FASTRTPS_DEFAULT_PROFILES_FILE=/workspace/course-project/docker/fastdds_udp.xml \
  -e HOME=/tmp/bmhome -e ROS_LOG_DIR=/tmp/bmhome/ros_log -e PYTHONUNBUFFERED=1 -e PYTHONDONTWRITEBYTECODE=1 \
  -e BM_GIT_COMMIT="$COMMIT" -e BM_GIT_DIRTY="$DIRTY" -e BM_HOST="$(hostname)" \
  -v "$REPO":/workspace beaconmind-ros:humble \
  bash -lc "mkdir -p /tmp/bmhome && source /opt/ros/humble/setup.bash && exec python3 /workspace/course-project/tools/car_batch.py$ARGS"
exit $?
