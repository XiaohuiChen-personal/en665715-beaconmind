#!/usr/bin/env bash
# Run tools/car_move.py in a one-off beaconmind-ros container with the project's ROS environment (Spark host).
#
#   bash course-project/tools/car.sh state
#   bash course-project/tools/car.sh stop-key                              # its own terminal; SPACE = STOP + latch
#   bash course-project/tools/car.sh move FORWARD_25 --i-am-at-the-car
#   bash course-project/tools/car.sh clear-latch --operator xiaohui
#   BM_ROS_DOMAIN_ID=42 bash course-project/tools/car.sh sim-car            # a simulated car, never on domain 0
#
# The environment is the recorder's (tools/record_session.sh ros_once): host network, UDP-only Fast DDS profile,
# ROS_DOMAIN_ID 0 unless BM_ROS_DOMAIN_ID says otherwise (0 is the real car's domain; anything else cannot reach it).
# The repository is mounted at /workspace, so the container and the host share course-project/data (the latch file,
# the recorder's session, the move logs).
#
# AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this wrapper.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
IMAGE=beaconmind-ros:humble
DOMAIN="${BM_ROS_DOMAIN_ID:-0}"
TTY=()
if [ -t 0 ] && [ -t 1 ]; then TTY=(-it); fi
ARGS=""
for a in "$@"; do ARGS+=" $(printf '%q' "$a")"; done
exec docker run --rm "${TTY[@]}" --network host --user "$(id -u):$(id -g)" \
  -e ROS_DOMAIN_ID="$DOMAIN" -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
  -e FASTRTPS_DEFAULT_PROFILES_FILE=/workspace/course-project/docker/fastdds_udp.xml \
  -e HOME=/tmp/bmhome -e ROS_LOG_DIR=/tmp/bmhome/ros_log -e PYTHONUNBUFFERED=1 \
  -v "$REPO":/workspace "$IMAGE" \
  bash -lc "mkdir -p /tmp/bmhome && source /opt/ros/humble/setup.bash && exec python3 /workspace/course-project/tools/car_move.py$ARGS"
