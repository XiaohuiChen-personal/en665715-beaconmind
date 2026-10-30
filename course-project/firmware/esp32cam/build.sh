#!/usr/bin/env bash
# AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the ESP32-CAM compile wrapper (M1.T6).
# AI-assisted: Grok 4.7 via Cursor, 2026-10-06: set FlashFreq=40,FlashMode=dio.
# AI-assisted: Claude Opus 5.5 via Claude Code, 2026-10-25: added the SKETCH argument (bm_cam_v02)
#   and --warnings all.
# FlashMode=dio selects bootloader_dio_40m.elf (both FlashMode menu items set build.flash_mode=dio).
# The chip runs that bootloader with its header rewritten to DOUT
# (evidence/M1/M1.T6/dout-write.txt); the bootloader this script builds is never flashed
# (flash_app.sh writes only the app).
# Usage (Spark host): build.sh [SKETCH]   SKETCH defaults to bm_cam (bm_cam-0.1).
set -euo pipefail
cd "$(dirname "$0")"
SKETCH=${1:-bm_cam}
if [[ ! "$SKETCH" =~ ^[A-Za-z0-9_]+$ ]] || [ ! -f "$SKETCH/$SKETCH.ino" ]; then
  echo "build.sh: no sketch $SKETCH/$SKETCH.ino" >&2
  exit 2
fi
if [ ! -s "$SKETCH/wifi_config.h" ]; then
  echo "copy $SKETCH/wifi_config.h.example to $SKETCH/wifi_config.h and fill it in" >&2
  exit 1
fi
# arduino-cli 1.5.2-rc.1 requires the sketch directory name to match the .ino
# (a /src mount looks for /src/src.ino).
docker run --rm -v "$PWD/$SKETCH":/src/"$SKETCH" bm-esp32-builder \
  arduino-cli compile --fqbn esp32:esp32:esp32cam:FlashFreq=40,FlashMode=dio --warnings all \
  --output-dir /src/"$SKETCH"/build /src/"$SKETCH"
