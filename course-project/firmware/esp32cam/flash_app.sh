#!/usr/bin/env bash
# App-only flash of a built sketch at 0x10000 (Spark host). This board boots only with the DOUT
# bootloader that is already at 0x1000 (evidence/M1/M1.T6/dout-write.txt); a DIO bootloader
# reboots in a loop (serial-boot-dio-rst.txt). So this never writes 0x1000, 0x8000 or 0xe000,
# the same way the UXGA image was written (evidence/M1/M1.T6/uxga-write.txt).
#
# Before running: hold IO0 on the base board, press and release RST, release IO0 (download mode;
# this base board does not enter it by itself). After "Hash of data verified": press RST.
#
# Usage: flash_app.sh SKETCH [PORT]    e.g. flash_app.sh bm_cam_v02
#        PORT defaults to the single /dev/serial/by-id link whose name does not contain Pico.
#
# AI-assisted: Claude Opus 5.5 via Claude Code, 2026-10-25: wrote this script.
# Copied from: course-project/firmware/esp32cam/flash.sh on 2026-10-25 (port selection; its
#   disclosure: Grok 4.7 via Cursor, 2026-10-06).
set -euo pipefail
cd "$(dirname "$0")"

SKETCH=${1:-}
if [[ ! "$SKETCH" =~ ^[A-Za-z0-9_]+$ ]]; then
  echo "usage: flash_app.sh SKETCH [PORT]" >&2
  exit 2
fi
APP="$SKETCH/build/$SKETCH.ino.bin"
PARTS="$SKETCH/build/$SKETCH.ino.partitions.bin"
# The partition table on the chip: written at 0x8000 by the full DIO upload of 2026-10-06
# (course-project/CONTEXT.md, entry "2026-10-06 — M1.T6 DIO upload"; the core saved a copy as
# bm_cam/build/bm_cam.ino.partitions_flashed.bin on the Spark) and left in place by the later
# DOUT bootloader and app-only writes. sha256 of its 3072-byte image (huge_app, esp32cam default).
ON_CHIP_PARTS_SHA=aaae2888c5a6a348004b5b436f47abb25ae32e72d9003902955a998eda723edd
for f in "$APP" "$PARTS"; do
  if [ ! -s "$f" ]; then
    echo "flash_app.sh: no $f; run build.sh $SKETCH first" >&2
    exit 2
  fi
done
# An app-only write is safe only if the build expects the partition table already on the chip.
if [ "$(sha256sum "$PARTS" | cut -d' ' -f1)" != "$ON_CHIP_PARTS_SHA" ]; then
  echo "flash_app.sh: $PARTS is not the partition table on the chip; refusing" >&2
  exit 2
fi

if [[ "${2:-}" == *Pico* ]]; then
  echo "flash_app.sh: refusing to flash a Pico port" >&2
  exit 2
fi
if [ "$#" -ge 2 ]; then
  PORT=$2
else
  shopt -s nullglob
  chosen=()
  for link in /dev/serial/by-id/*; do
    if [[ "$(basename "$link")" != *Pico* ]]; then
      chosen+=("$link")
    fi
  done
  if [ "${#chosen[@]}" -ne 1 ]; then
    echo "flash_app.sh: need exactly one non-Pico /dev/serial/by-id link, found ${#chosen[@]}" >&2
    exit 2
  fi
  PORT=${chosen[0]}
fi
if [[ "$(basename "$PORT")" == *Pico* ]]; then
  echo "flash_app.sh: refusing to flash a Pico port" >&2
  exit 2
fi
DEV=$(readlink -f "$PORT")

sha256sum "$APP"
docker run --rm --device "$DEV" -v "$PWD/$SKETCH":/src/"$SKETCH" bm-esp32-builder \
  /root/.arduino15/packages/esp32/tools/esptool_py/5.3.1/esptool --chip esp32 --port "$DEV" \
  --baud 460800 --before no-reset --after no-reset write-flash -z \
  --flash-mode keep --flash-freq keep --flash-size keep \
  0x10000 /src/"$SKETCH"/build/"$SKETCH".ino.bin
echo "flash_app.sh: written. Press RST on the base board to start the new app."
