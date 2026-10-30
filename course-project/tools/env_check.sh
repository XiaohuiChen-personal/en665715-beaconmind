#!/usr/bin/env bash
# AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the Spark host environment check.
set -euo pipefail

echo "== date"
date

echo "== python3"
python3 --version

echo "== venv"
if [ -x "$HOME/.venvs/beaconmind/bin/python" ]; then
  "$HOME/.venvs/beaconmind/bin/python" --version
else
  echo "no venv"
fi

echo "== cc"
cc --version | sed -n '1p'

echo "== docker compose"
docker compose version

echo "== docker ps"
docker ps -a --format '{{.Names}} {{.Status}}'

echo "== vllm"
if ! curl -sf --max-time 5 http://127.0.0.1:8000/v1/models; then
  echo "vLLM not serving"
fi

echo "== serial"
shopt -s nullglob
serial_devices=(/dev/ttyACM* /dev/ttyUSB*)
shopt -u nullglob
if [ "${#serial_devices[@]}" -eq 0 ]; then
  echo "no serial devices"
else
  ls "${serial_devices[@]}"
fi

echo "== ip"
if ! ip -4 addr show | grep 192.168.5.1; then
  echo "192.168.5.1 not present"
fi
