#!/usr/bin/env bash
# Car network check for plan §3.6 work list 0.3 (Spark host, no sudo).
#
#   bash course-project/tools/car_net.sh status          radio, access point, the car and camera, the camera's /status
#   bash course-project/tools/car_net.sh relay-start     start the camera relay for containers (tmux session bm-cam-relay)
#   bash course-project/tools/car_net.sh relay-stop
#
# Before it: Xiaohui runs the private course repo's access-point script in a terminal of his own, because it needs sudo:
#   sudo bash ~/Projects/EN.665.715/discussions/module9/tools/ap_net.sh up 11
# and powers the car (Pico image buildK2a_d485d7ab) and the camera (bm_cam-0.2, access-point build). Both were flashed for
# the access point on 2026-11-01 and know no other network. The access point is 2.4 GHz channel 11, 10.42.0.1.
# Addresses seen so far: car 10.42.0.138, camera 10.42.0.89 (DHCP; this script finds them again from the ARP table).
# The Spark's wired Ethernet stays up meanwhile, so the Spark keeps its internet and Tailscale.
#
# AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote this check.
set -uo pipefail
IF=wlP9s9
AP=10.42.0.1
REPO="$(cd "$(dirname "$0")/../.." && pwd)"

find_camera() {   # the host on the access point that answers the bm_cam /status endpoint
  local ip
  for ip in $(ip neigh show dev "$IF" 2>/dev/null | awk '/10\.42\.0\./{print $1}') 10.42.0.89; do
    if curl -sf -m 2 "http://$ip/status" 2>/dev/null | grep -q '"fw"'; then echo "$ip"; return 0; fi
  done
  return 1
}

case "${1:-status}" in
  status)
    echo "--- radio $IF"
    ip -4 -br addr show "$IF" 2>/dev/null || echo "no $IF"
    nmcli -t -f NAME,DEVICE,STATE con show --active 2>/dev/null | grep -E "car-ap|$IF" || echo "access point connection not active (run ap_net.sh up with sudo)"
    if ! ip -4 addr show "$IF" 2>/dev/null | grep -q "$AP"; then echo "NOT READY: $IF does not hold $AP"; exit 1; fi
    echo "--- hosts on the access point (ARP)"
    ping -c 1 -W 1 -b 10.42.0.255 >/dev/null 2>&1 || true
    ip neigh show dev "$IF" | awk '/10\.42\.0\./{print $1, $NF}'
    echo "--- camera"
    if CAM=$(find_camera); then
      echo "camera at $CAM"; curl -s -m 3 "http://$CAM/status"; echo
    else
      echo "camera not found (power it, wait 20 s, run again)"
    fi
    echo "--- micro-ROS agent (UDP 8888)"
    ss -uln 2>/dev/null | grep -q ":8888 " && echo "something listens on UDP 8888" || echo "no agent on UDP 8888 (start it before the car can join ROS)"
    echo "--- relay"
    tmux has-session -t bm-cam-relay 2>/dev/null && echo "relay running (containers use http://172.17.0.1:18080)" || echo "relay not running"
    ;;
  relay-start)
    CAM=$(find_camera) || { echo "camera not found"; exit 1; }
    tmux has-session -t bm-cam-relay 2>/dev/null && { echo "relay already running"; exit 0; }
    tmux new-session -d -s bm-cam-relay "python3 '$REPO/course-project/tools/camera_relay.py' $CAM"
    sleep 1; curl -s -m 3 http://172.17.0.1:18080/status && echo && echo "relay up: http://172.17.0.1:18080 -> $CAM"
    ;;
  relay-stop)
    tmux kill-session -t bm-cam-relay 2>/dev/null && echo "relay stopped" || echo "relay was not running"
    ;;
  *)
    echo "usage: $0 status|relay-start|relay-stop"; exit 2
    ;;
esac
