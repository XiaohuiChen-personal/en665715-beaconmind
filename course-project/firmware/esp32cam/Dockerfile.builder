# AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the ESP32-CAM Arduino CLI builder (M1.T6, OD12).
# ESP32-CAM build/flash toolchain (OD12): Arduino CLI + the esp32 core, pinned after first install.
# Derived from: none (Arduino CLI and the esp32 core are the toolchain; sketch code is not copied from an example).
# Pinned from the first image: arduino-cli 1.5.2-rc.1 and esp32:esp32 3.3.12.
FROM python:3.12-bookworm
RUN curl -fsSL -o /tmp/acli.tgz https://downloads.arduino.cc/arduino-cli/arduino-cli_1.5.2-rc.1_Linux_ARM64.tar.gz \
    && tar -xzf /tmp/acli.tgz -C /usr/local/bin arduino-cli && rm /tmp/acli.tgz
RUN arduino-cli config init \
    && arduino-cli config add board_manager.additional_urls https://espressif.github.io/arduino-esp32/package_esp32_index.json \
    && arduino-cli core update-index && arduino-cli core install esp32:esp32@3.3.12
RUN arduino-cli core list && arduino-cli board listall | grep -i -E "esp32cam|ai.?thinker"
