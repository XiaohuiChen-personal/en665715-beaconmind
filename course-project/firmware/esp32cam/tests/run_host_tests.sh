#!/usr/bin/env bash
# Host test for bm_cam_v02/bm_cam_util.h (Mac or Spark host; needs cc, and python3 with Pillow for
# the encoder-made frames). Real ESP32-CAM UXGA frames come from evidence/M1/M1.T6/pictures/.
# AI-assisted: Claude Opus 5.5 via Claude Code, 2026-10-25: wrote this runner.
set -euo pipefail
cd "$(dirname "$0")"
PICS=../../../evidence/M1/M1.T6/pictures
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

cc -std=c11 -Wall -Wextra -Werror -O1 -o "$TMP/test_bm_cam_util" test_bm_cam_util.c
# The same header must also compile as C++ (the sketch includes it): build the test as C++ too.
c++ -std=c++17 -Wall -Wextra -Werror -O1 -x c++ -o "$TMP/test_bm_cam_util_cpp" test_bm_cam_util.c

args=()
for f in floor-1.jpg uxga-3.jpg; do
  [ -f "$PICS/$f" ] && args+=("$PICS/$f" 1600 1200)
done
if python3 -c "import PIL" 2>/dev/null; then
  python3 - "$TMP" <<'PY'
import sys
from PIL import Image
out = sys.argv[1]
Image.new("RGB", (640, 480), (200, 30, 30)).save(f"{out}/vga.jpg", quality=85)
Image.new("RGB", (800, 600), (30, 30, 200)).save(f"{out}/svga_progressive.jpg", progressive=True)
Image.new("RGB", (320, 240), (30, 200, 30)).save(f"{out}/qvga_exif.jpg", exif=b"Exif\x00\x00" + b"\x00" * 32)
PY
  args+=("$TMP/vga.jpg" 640 480 "$TMP/svga_progressive.jpg" 800 600 "$TMP/qvga_exif.jpg" 320 240)
fi
"$TMP/test_bm_cam_util" "${args[@]}"
"$TMP/test_bm_cam_util_cpp" "${args[@]}" | tail -1
