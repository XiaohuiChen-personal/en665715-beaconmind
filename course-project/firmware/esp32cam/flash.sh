#!/usr/bin/env bash
# AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the ESP32-CAM upload wrapper (M1.T6).
# AI-assisted: Claude Opus 5.5 via Claude Code, 2026-10-25: disabled it. 'arduino-cli upload' writes
#   the build's DIO bootloader at 0x1000 with --flash-mode keep (core 3.3.12 platform.txt:348), and
#   this board reboots in a loop with a DIO bootloader (evidence/M1/M1.T6/serial-boot-dio-rst.txt).
#   The working method is an app-only write at 0x10000: flash_app.sh. The old command is in git.
echo "flash.sh: disabled; it would replace the DOUT bootloader. Use: flash_app.sh SKETCH [PORT]" >&2
exit 2
