#!/usr/bin/env bash
# Run tools/car_batch.py on the Spark: the R2 recorder for the whole batch, then the batch in a one-off container.
#
#   bash course-project/tools/car_batch.sh <label> run --world course-project/configs/arenas/<world>.json \
#        --scenarios course-project/configs/arenas/real-room-scenarios.json --initial-pose 2.5,1.5,90 --episodes 10 --policy b2
#   bash course-project/tools/car_batch.sh - record-pass --operator xiaohui --stand-session <s> --floor-session <s> --world <w>
#   bash course-project/tools/car_batch.sh - clear-halt --out course-project/data/batches/<label> --operator xiaohui
#   BM_ROS_DOMAIN_ID=42 ... (a simulated car node; never the real car)
#
# The batch folder is course-project/data/batches/<label> (unless --out or --label is given): a rerun with the same
# label finds the earlier halt, manifest and spend. Run it inside tmux (or with nohup): a closed ssh session ends it.
# For `run` without --dry-run it starts the recorder (tools/record_session.sh start batch-<label> --camera off: the
# batch itself is the camera's one client and saves every frame) unless a session is already active, with a watchdog
# longer than the batch's own cap, and stops it when the batch ends, halted or not. A real run is refused (nothing
# sent) when the recorder's start checks did not find the car, the camera or the micro-ROS agent (no ping log could
# show the link gaps, rule R2), or when an already active session polls the camera (the batch must be its only
# client). The batch halts by itself if the recorder stops first (rule R2). Paths under course-project/ are mapped to
# /workspace. The container gets the secrets file only for a model policy's key (as tools/closed_loop_run.sh).
#
# Stopping a batch: the STOP key or `car.sh stop` (the latch: the batch halts at its next check), Ctrl+C in its tmux
# window, closing that window, or `docker stop bm-batch-<label>`. Each ends with a halt record (`interrupted`, or
# `latch`). A `kill` of this script's own process does NOT reach the container: the batch goes on until it ends.
# The container is named bm-batch-<label>, so a second run of the same batch cannot start while one is running.
# Exit status: the batch's own (0 complete, 3 halted, 2 refused), also after Ctrl+C; 2 when this script refuses.
#
# AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this wrapper.
# AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: first real execution on the Spark; fixed a recorder left
# running when its start reported an error, kept the batch's exit status after a signal, named the container, refused a
# real run without the car, camera and agent in the recorder's checks or with a camera-polling session.
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
  for popt in --out --latch --marker --world --scenarios --prompt --detector-noise; do
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
NAME=()
if [ "$CMD" = "run" ]; then
  [ "$LABEL" = "-" ] && [ "$HAS_OUT" = 0 ] && { echo "car_batch.sh: run needs a label (first argument)" >&2; exit 2; }
  [ "$HAS_OUT" = 0 ] && ARGS+=" --label $(printf '%q' "$LABEL")"
  # one container per batch: docker refuses a second run of the same label while the first is running
  CNAME="bm-batch-$(printf '%s' "$LABEL" | tr -c 'a-zA-Z0-9_.-' '-')"
  [ "$LABEL" = "-" ] && CNAME="bm-batch-$$"
  NAME=(--name "$CNAME")
fi

STARTED=0
SIGNALLED=""
stop_recorder() { if [ "$STARTED" = 1 ]; then bash "$CP/tools/record_session.sh" stop "batch ended" || true; fi; }
trap stop_recorder EXIT
# Ctrl+C or a closed window reaches the container through docker (its signal proxy) and the batch writes its halt; this
# script only notes it, waits for the batch to end and keeps its exit status. Before the batch starts it aborts.
trap 'SIGNALLED=1' INT TERM HUP

if [ "$CMD" = "run" ] && [ "$DRY" = 0 ] && [ "$DOMAIN" = 0 ]; then
  if [ -f "$CP/data/real/.active" ]; then
    # a session is marked active: it must really be recording (a crashed recorder leaves the mark behind)
    tmux has-session -t bm-rec 2>/dev/null || { echo "car_batch.sh: data/real/.active exists but the recorder (tmux bm-rec) is not running: stop or repair it first; nothing was sent" >&2; exit 2; }
    if grep -q '"camera_mode": "poll"' "$CP/data/real/$(cat "$CP/data/real/.active")/meta/session.json" 2>/dev/null; then
      echo "car_batch.sh: the active recorder session polls the camera; the batch must be the camera's only client. Stop that session (record_session.sh stop) and let car_batch.sh start its own with --camera off; nothing was sent" >&2
      exit 2
    fi
  else
    WATCHDOG="$(python3 -c "import sys; print(float(sys.argv[1]) + 1.0)" "$HOURS")" || { echo "car_batch.sh: --batch-hours $HOURS is not a number" >&2; exit 2; }
    bash "$CP/tools/record_session.sh" start "batch-$LABEL" --camera off --max-hours "$WATCHDOG" \
      --note "unattended batch (tools/car_batch.sh)"
    rc=$?
    # whatever its exit status says, a session that is now marked active is ours to stop at the end
    [ -f "$CP/data/real/.active" ] && STARTED=1
    if [ "$rc" != 0 ] || [ "$STARTED" = 0 ]; then
      echo "car_batch.sh: the recorder's start failed (exit $rc)$([ "$STARTED" = 1 ] && echo '; the session it began is stopped'); nothing was sent" >&2
      exit 2
    fi
  fi
  # the recorder's own start checks: without the car, the camera or the agent the batch cannot run, and the session
  # would hold no ping log of the link (rule R2)
  CHECKS="$CP/data/real/$(cat "$CP/data/real/.active" 2>/dev/null)/meta/checks.txt"
  MISSING="$(grep -E '^(car: NOT FOUND|camera: NOT FOUND|micro-ROS agent: NOT RUNNING)' "$CHECKS" 2>/dev/null)"
  if [ ! -f "$CHECKS" ] || [ -n "$MISSING" ]; then
    echo "car_batch.sh: the recorder's start checks ($CHECKS) say:" >&2
    printf '  %s\n' "${MISSING:-the checks file is missing}" >&2
    echo "  bash course-project/tools/car_net.sh status; nothing was sent$([ "$STARTED" = 1 ] && echo ' (the session started here is stopped)')" >&2
    exit 2
  fi
fi
[ -n "$SIGNALLED" ] && { echo "car_batch.sh: interrupted before the batch started; nothing was sent" >&2; exit 130; }

SECRETS=()
[ -f "$HOME/.config/beaconmind/secrets.env" ] && SECRETS=(--env-file "$HOME/.config/beaconmind/secrets.env")
docker run --rm --init ${NAME[@]+"${NAME[@]}"} --network host --user "$(id -u):$(id -g)" ${SECRETS[@]+"${SECRETS[@]}"} \
  -e ROS_DOMAIN_ID="$DOMAIN" -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
  -e FASTRTPS_DEFAULT_PROFILES_FILE=/workspace/course-project/docker/fastdds_udp.xml \
  -e HOME=/tmp/bmhome -e ROS_LOG_DIR=/tmp/bmhome/ros_log -e PYTHONUNBUFFERED=1 -e PYTHONDONTWRITEBYTECODE=1 \
  -e BM_GIT_COMMIT="$COMMIT" -e BM_GIT_DIRTY="$DIRTY" -e BM_HOST="$(hostname)" \
  -v "$REPO":/workspace beaconmind-ros:humble \
  bash -lc "mkdir -p /tmp/bmhome && source /opt/ros/humble/setup.bash && exec python3 /workspace/course-project/tools/car_batch.py$ARGS"
rc=$?
[ -n "$SIGNALLED" ] && echo "car_batch.sh: the batch was interrupted; its exit status is $rc" >&2
exit "$rc"
