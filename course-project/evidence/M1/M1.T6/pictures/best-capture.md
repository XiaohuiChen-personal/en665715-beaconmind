# Current SVGA capture (quality not raised)

2026-10-06. These three files are the running `bm_cam-0.1` stills. They are not a higher-quality set. M1.T6 is not done.

The sketch sets framesize and JPEG quality only in `startCamera()`: `config.frame_size = FRAMESIZE_SVGA` and `config.jpeg_quality = 12`. `GET /status` prints those values from a fixed string (`SVGA`, 800, 600, quality 12). The only HTTP routes are `GET /capture`, `GET /status`, and `GET /led`. None of them takes a framesize or quality argument, and the sketch never calls `set_framesize` or `set_quality`. The board was not reflashed, not reset, and the flash LED was not commanded.

`jpeg_quality` on this sketch is the esp32-camera `camera_config_t` field. In the pinned core this firmware builds with (esp32 3.3.12, `esp32-libs/.../esp_camera.h`), that field is documented as 0–63, and a lower number is higher quality. The sketch itself only assigns 12.

The Spark fetched `GET http://192.168.4.24/status` (HTTP 200, `fw` `bm_cam-0.1`, SVGA, quality 12, `vflip` 0, `hmirror` 0, `psram` true, `frames` 3). It then fetched `GET /capture` three times, one second apart. Each body started with `FFD8` and ended with `FFD9`, so all three were saved.

| File | HTTP | Width | Height | Bytes | Start | End | `X-BM-Seq` | `X-BM-Uptime-Ms` |
| --- | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: |
| `current-1.jpg` | 200 | 800 | 600 | 32026 | `ffd8` | `ffd9` | 4 | 851448 |
| `current-2.jpg` | 200 | 800 | 600 | 31463 | `ffd8` | `ffd9` | 5 | 852637 |
| `current-3.jpg` | 200 | 800 | 600 | 31189 | `ffd8` | `ffd9` | 6 | 853862 |

Mac checks: Pillow and `sips` both read each Desktop copy as an 800×600 JPEG. The same three files are on the Spark at `course-project/evidence/M1/M1.T6/pictures/` and in `/tmp/bm-cam-current/`, and on the Mac in this folder and in `/Users/xiaohuichen/Desktop/beaconmind-camera/`.

These settings are the same as SVGA quality 12, not higher. A real improvement needs a sketch change and a later reflash: set `frame_size` to a larger `framesize_t` than `FRAMESIZE_SVGA` (the same core's `sensor.h` lists `FRAMESIZE_UXGA` as 1600×1200; this sketch does not), set `jpeg_quality` below 12, and stop hardcoding the `/status` JSON.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, captured the three JPEGs from the Spark and wrote this note.
