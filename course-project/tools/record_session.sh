#!/usr/bin/env bash
# Session recorder for rule R2 (plan/README.md §3.6; plan task M3.T27, work list 2.10). Spark host, no sudo.
#
#   bash course-project/tools/record_session.sh start <label> [--operator NAME] [--note TEXT]
#                                                         [--camera poll|off] [--fps N] [--max-hours H]
#   bash course-project/tools/record_session.sh run <name> -- <command> [args...]
#   bash course-project/tools/record_session.sh status
#   bash course-project/tools/record_session.sh stop
#
# start makes course-project/data/real/<YYYYmmdd-HHMMSS>-<label>/ (git-ignored) and starts, each in a window of tmux
# session bm-rec, from a script it writes into the session's meta/run/:
#   bag       ros2 bag record -a: every topic on the ROS graph (the car's included), in a one-off beaconmind-ros container
#   frames    every camera frame and the camera's /status (tools/record_frames.py). Use --camera off when another program
#             is the camera's client (the camera serves one request at a time); that program then saves its own frames
#             into the session
#   ping-car, ping-cam   5 pings a second, time-stamped (link gaps)
#   wifi      the access point's station dump every 5 s (signal, bit rate, retries; MAC addresses cut to 3 bytes)
#   agent     the micro-ROS agent's log (each Pico connection shows as a new session)
#   watchdog  stops the session after --max-hours (default 4), so a forgotten recording cannot fill the disk
# It also appends the camera relay's output (tmux session bm-cam-relay) to the session. `run` runs one command with its
# output and exit code kept in terminal/. stop ends every capture, closes the bag cleanly and writes README.md
# (tools/record_report.py); tape.md and notes.md are for the operator. Film tools/session_clock.py with the phone at the
# start of every video. The recorder only records: it never publishes a topic and never moves the car.
#
# AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-18: wrote this recorder. The pattern (one folder per session, a
# clock for the phone, tmux) follows the Module 9 real-robot tools in the private course repo; no code was copied.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
CP="$REPO/course-project"
ROOT="$CP/data/real"
ACTIVE="$ROOT/.active"
SELF="$CP/tools/record_session.sh"
S=bm-rec
IF=wlP9s9
AP=10.42.0.1
IMAGE=beaconmind-ros:humble
BAG_C=bm-rec-bag
AGENT_C=bm-micro-ros-agent
RELAY_S=bm-cam-relay
PICO_BUILD="${BM_PICO_BUILD:-buildK2a_d485d7ab}"

die() { echo "record_session: $*" >&2; exit 1; }
now_utc() { date -u +%Y-%m-%dT%H:%M:%S.%3NZ; }
running() { docker ps -q --filter "name=^$1\$" | grep -q .; }

ros_env=(-e ROS_DOMAIN_ID=0 -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp
         -e FASTRTPS_DEFAULT_PROFILES_FILE=/workspace/course-project/docker/fastdds_udp.xml
         -e HOME=/tmp/bmhome -e ROS_LOG_DIR=/tmp/bmhome/ros_log)

ros_once() {   # one command in a one-off beaconmind-ros container, the compose service's environment
  docker run --rm --network host --user "$(id -u):$(id -g)" "${ros_env[@]}" -v "$REPO":/workspace "$IMAGE" \
    bash -lc "mkdir -p /tmp/bmhome && source /opt/ros/humble/setup.bash && $1"
}

find_camera() {  # the host on the access point that answers bm_cam's /status (as tools/car_net.sh)
  local ip
  for ip in $(ip neigh show dev "$IF" 2>/dev/null | awk '/10\.42\.0\./ && !/FAILED/ {print $1}') 10.42.0.89; do
    if curl -sf -m 2 "http://$ip/status" 2>/dev/null | grep -q '"fw"'; then echo "$ip"; return 0; fi
  done
  return 1
}

find_car() {     # the other host on the access point that answers a ping
  local ip
  for ip in $(ip neigh show dev "$IF" 2>/dev/null | awk '/10\.42\.0\./ && !/FAILED/ {print $1}') 10.42.0.138; do
    [ "$ip" = "${1:-}" ] && continue
    if ping -c 1 -W 1 "$ip" >/dev/null 2>&1; then echo "$ip"; return 0; fi
  done
  return 1
}

active_dir() { [ -f "$ACTIVE" ] || die "no active session"; echo "$ROOT/$(cat "$ACTIVE")"; }

window() {       # window <name> <script body>: write meta/run/<name>.sh and run it in tmux session $S
  local name="$1" body="$2" f="$DIR/meta/run/$1.sh"
  printf '#!/usr/bin/env bash\n# %s window of session %s, written by record_session.sh\necho $$ > %q\n%s\n' \
    "$name" "$ID" "$DIR/meta/run/$name.pid" "$body" > "$f"
  if tmux has-session -t "$S" 2>/dev/null; then
    tmux new-window -d -t "$S" -n "$name" "bash '$f'"
  else
    tmux new-session -d -s "$S" -n "$name" -x 200 -y 50 "bash '$f'"
  fi
}

start() {
  local label="${1:-}" operator="" note="" camera=poll fps=5 maxh=4
  [ -n "$label" ] || die "usage: start <label> [--operator NAME] [--note TEXT] [--camera poll|off] [--fps N] [--max-hours H]"
  shift
  while [ $# -gt 0 ]; do
    case "$1" in
      --operator) operator="$2"; shift 2 ;;
      --note) note="$2"; shift 2 ;;
      --camera) camera="$2"; shift 2 ;;
      --fps) fps="$2"; shift 2 ;;
      --max-hours) maxh="$2"; shift 2 ;;
      *) die "unknown option $1" ;;
    esac
  done
  [[ "$camera" =~ ^(poll|off)$ ]] || die "--camera must be poll or off"
  [ -f "$ACTIVE" ] && die "session $(cat "$ACTIVE") is still active; stop it first"
  tmux has-session -t "$S" 2>/dev/null && die "tmux session $S exists without an active session; look at it, then: tmux kill-session -t $S"
  running "$BAG_C" && die "container $BAG_C is still running; look at it, then: docker stop $BAG_C"
  label=$(printf '%s' "$label" | tr 'A-Z' 'a-z' | tr -c 'a-z0-9-' '-' | sed -e 's/--*/-/g' -e 's/^-//' -e 's/-$//')
  ID="$(date +%Y%m%d-%H%M%S)-$label"
  DIR="$ROOT/$ID"
  mkdir -p "$DIR"/frames "$DIR"/logs "$DIR"/terminal "$DIR"/meta/run || die "cannot make $DIR"
  local start_iso cam="" car="" avail
  start_iso=$(now_utc)

  # checks: recorded, and only the missing image or disk space refuse the session
  {
    echo "checks at $start_iso"
    ip -4 addr show "$IF" 2>/dev/null | grep -q "$AP" && echo "access point: $IF holds $AP" || echo "access point: NOT UP ($IF does not hold $AP)"
    running "$AGENT_C" && echo "micro-ROS agent: $AGENT_C running" || echo "micro-ROS agent: NOT RUNNING (bash course-project/tools/car_net.sh agent-start)"
    tmux has-session -t "$RELAY_S" 2>/dev/null && echo "camera relay: tmux $RELAY_S up" || echo "camera relay: not running"
    if cam=$(find_camera); then echo "camera: $cam"; else cam=""; echo "camera: NOT FOUND"; fi
    if car=$(find_car "$cam"); then echo "car: $car answers"; else car=""; echo "car: NOT FOUND on the access point"; fi
    echo "ntp: $(timedatectl show -p NTPSynchronized --value 2>/dev/null || echo unknown)"
  } | tee "$DIR/meta/checks.txt"
  cam=$(awk '/^camera: [0-9]/{print $2}' "$DIR/meta/checks.txt")
  car=$(awk '/^car: [0-9]/{print $2}' "$DIR/meta/checks.txt")
  docker image inspect "$IMAGE" >/dev/null 2>&1 || die "image $IMAGE missing"
  avail=$(df -BG --output=avail "$ROOT" | tail -1 | tr -dc 0-9)
  [ "${avail:-0}" -ge 20 ] || die "only ${avail} GB free under $ROOT"
  [ -n "$cam" ] && curl -sf -m 3 "http://$cam/status" > "$DIR/meta/camera_status_start.json"
  # the agent logs only events (a Pico joining), so keep its recent log: the car's connection state at the start
  running "$AGENT_C" && docker logs --timestamps --tail 200 "$AGENT_C" > "$DIR/logs/micro_ros_agent_before.log" 2>&1

  ID="$ID" LABEL="$label" OPERATOR="$operator" NOTE="$note" CAMERA="$camera" FPS="$fps" MAXH="$maxh" \
  START_ISO="$start_iso" CAM_IP="$cam" CAR_IP="$car" PICO_BUILD="$PICO_BUILD" REPO="$REPO" python3 - "$DIR/meta/session.json" <<'PY'
import json, os, socket, subprocess, sys, time
e = os.environ
git = lambda *a: subprocess.run(["git", "-C", e["REPO"], *a], capture_output=True, text=True).stdout.strip()
ntp = subprocess.run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"], capture_output=True, text=True).stdout.strip()
json.dump({"id": e["ID"], "label": e["LABEL"], "operator": e["OPERATOR"], "note": e["NOTE"], "start_utc": e["START_ISO"],
           "start_local": time.strftime("%Y-%m-%d %H:%M:%S %Z"), "host": socket.gethostname(),
           "git_commit": git("rev-parse", "--short=12", "HEAD"),
           "git_dirty": bool([l for l in git("status", "--porcelain").splitlines() if not l.startswith("??")]),
           "camera_mode": e["CAMERA"], "fps": float(e["FPS"]), "max_hours": float(e["MAXH"]), "camera_ip": e["CAM_IP"],
           "car_ip": e["CAR_IP"], "pico_build": e["PICO_BUILD"], "ntp_synced": ntp or "unknown"},
          open(sys.argv[1], "w"), indent=1)
PY

  window watchdog "sleep $(python3 -c "print(int(float('$maxh') * 3600))")
echo \"watchdog: \$(date -u +%FT%TZ) after $maxh h\" >> '$DIR/logs/watchdog.log'
setsid bash '$SELF' stop watchdog >> '$DIR/logs/watchdog.log' 2>&1 < /dev/null &
sleep 600"
  local bagcmd="mkdir -p /tmp/bmhome && source /opt/ros/humble/setup.bash && exec ros2 bag record -a --include-hidden-topics -o /workspace/course-project/data/real/$ID/bag"
  window bag "exec docker run --rm --init --name $BAG_C --network host --user $(id -u):$(id -g) ${ros_env[*]} -v '$REPO':/workspace $IMAGE bash -lc '$bagcmd' > '$DIR/logs/rosbag.log' 2>&1"
  if [ "$camera" = poll ] && [ -n "$cam" ]; then
    window frames "exec python3 '$CP/tools/record_frames.py' --base http://$cam --out '$DIR/frames' --fps $fps > '$DIR/logs/frames.log' 2>&1"
  fi
  [ -n "$car" ] && window ping-car "exec ping -D -O -i 0.2 $car > '$DIR/logs/ping_car.txt' 2>&1"
  [ -n "$cam" ] && window ping-cam "exec ping -D -O -i 0.2 $cam > '$DIR/logs/ping_cam.txt' 2>&1"
  window wifi "while :; do echo \"=== \$(date +%s.%N)\"; iw dev $IF station dump 2>&1 | python3 '$CP/tools/record_report.py' --redact; sleep 5; done > '$DIR/logs/wifi_stations.txt'"
  running "$AGENT_C" && window agent "exec docker logs -f --timestamps --since '$start_iso' $AGENT_C > '$DIR/logs/micro_ros_agent.log' 2>&1"
  # without -o: a pipe left open by an earlier session is replaced, not toggled off
  tmux has-session -t "$RELAY_S" 2>/dev/null && tmux pipe-pane -t "$RELAY_S" "cat >> '$DIR/logs/camera_relay.log'"
  echo "$ID" > "$ACTIVE"

  echo
  echo "recording session $ID"
  echo "  folder  $DIR"
  echo "  windows $(tmux list-windows -t "$S" -F '#W' | tr '\n' ' ')"
  echo "  clock   python3 course-project/tools/session_clock.py $ID   (film it at the start of the phone video)"
  echo "  stop    bash course-project/tools/record_session.sh stop"
  sleep 3
  status
}

run_cmd() {
  local dir name n f rc
  dir=$(active_dir) || exit 1
  name="${1:-}"; [ -n "$name" ] || die "usage: run <name> -- <command> [args...]"
  shift; [ "${1:-}" = "--" ] && shift
  [ $# -gt 0 ] || die "usage: run <name> -- <command> [args...]"
  n=$(find "$dir/terminal" -maxdepth 1 -name '*.log' | wc -l)
  f="$dir/terminal/$(printf '%02d' $((n + 1)))-$name.log"
  { echo "# session: $(basename "$dir")"; echo "# cmd: $(printf '%q ' "$@")"; echo "# cwd: $PWD"; echo "# start: $(now_utc)"; } > "$f"
  "$@" 2>&1 | tee -a "$f"
  rc=${PIPESTATUS[0]}
  { echo "# end: $(now_utc)"; echo "# exit: $rc"; } >> "$f"
  return "$rc"
}

status() {
  if [ ! -f "$ACTIVE" ]; then echo "no active session"; return 0; fi
  local dir; dir=$(active_dir)
  echo "active: $(cat "$ACTIVE")"
  local p name
  for p in "$dir"/meta/run/*.pid; do
    [ -f "$p" ] || continue
    name=$(basename "$p" .pid)
    if kill -0 "$(cat "$p")" 2>/dev/null; then echo "  $name: running"; else echo "  $name: NOT RUNNING"; fi
  done
  running "$BAG_C" && echo "  bag container: running" || echo "  bag container: NOT RUNNING"
  echo "  bag: $(du -sh "$dir/bag" 2>/dev/null | cut -f1)  frames: $(grep -c '"file"' "$dir/frames/index.jsonl" 2>/dev/null || echo 0)"
  tail -n 1 "$dir/logs/ping_car.txt" 2>/dev/null | sed 's/^/  car ping: /'
}

stop() {
  local reason="${1:-operator}" dir id p pid i
  dir=$(active_dir) || exit 1
  id=$(basename "$dir")
  echo "stopping $id ($reason)"
  if running "$BAG_C"; then   # SIGINT lets rosbag2 close the bag and write metadata.yaml
    docker kill -s INT "$BAG_C" >/dev/null
    for i in $(seq 1 30); do running "$BAG_C" || break; sleep 1; done
    if running "$BAG_C"; then echo "bag: still running after 30 s; docker stop"; docker stop -t 10 "$BAG_C" >/dev/null; fi
  fi
  if [ -d "$dir/bag" ] && [ ! -f "$dir/bag/metadata.yaml" ]; then
    echo "bag: no metadata.yaml; reindexing"
    ros_once "ros2 bag reindex /workspace/course-project/data/real/$id/bag" > "$dir/logs/bag_reindex.log" 2>&1
  fi
  for p in "$dir"/meta/run/*.pid; do
    [ -f "$p" ] || continue
    case "$(basename "$p")" in watchdog.pid|bag.pid) continue ;; esac
    kill -INT "$(cat "$p")" 2>/dev/null
  done
  sleep 2
  for p in "$dir"/meta/run/*.pid; do
    [ -f "$p" ] || continue
    [ "$(basename "$p")" = watchdog.pid ] && continue
    pid=$(cat "$p"); kill -0 "$pid" 2>/dev/null && kill -TERM "$pid" 2>/dev/null
  done
  if tmux has-session -t "$RELAY_S" 2>/dev/null; then
    tmux pipe-pane -t "$RELAY_S"
    tmux capture-pane -p -S - -t "$RELAY_S" > "$dir/logs/camera_relay_pane.txt"
  fi
  local cam; cam=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('camera_ip',''))" "$dir/meta/session.json" 2>/dev/null)
  [ -n "$cam" ] && curl -sf -m 3 "http://$cam/status" > "$dir/meta/camera_status_end.json"
  if [ -d "$dir/bag" ]; then ros_once "ros2 bag info /workspace/course-project/data/real/$id/bag" > "$dir/meta/bag_info.txt" 2>&1; fi
  python3 -c "import json,sys,time; json.dump({'end_utc': sys.argv[2], 'end_local': time.strftime('%Y-%m-%d %H:%M:%S %Z'), 'reason': sys.argv[3]}, open(sys.argv[1], 'w'), indent=1)" \
    "$dir/meta/stop.json" "$(now_utc)" "$reason"
  python3 "$CP/tools/record_report.py" "$dir" > /dev/null
  rm -f "$ACTIVE"
  echo "stopped: $dir"
  sed -n '1,60p' "$dir/README.md"
  tmux kill-session -t "$S" 2>/dev/null   # last: the watchdog runs this from inside the session (detached by setsid)
  return 0
}

cmd="${1:-}"; shift || true
case "$cmd" in
  start) start "$@" ;;
  run) run_cmd "$@" ;;
  status) status ;;
  stop) stop "$@" ;;
  *) sed -n '2,9p' "$0"; exit 2 ;;
esac
