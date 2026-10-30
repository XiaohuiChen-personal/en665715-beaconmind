# Floor view at UXGA: M1.T6 step 14 picture check

2026-10-07, 00:10–00:12 CDT. Xiaohui said the car was ready. The camera USB was already unplugged. Three live `GET /capture` frames were saved and read. This note applies the M1.T6 step 14 pass rule to those pixels. M1.T6 is not done: the other acceptance items are still open, and M1.T7 has not started.

## Capture

- **USB.** On the Spark at 2026-10-07T05:10:07Z, `lsusb` had no `0843:5740`, and `/dev/serial/by-id/usb-FIREPHX_USB_SER_FX2348N-if00` was absent. The serial port was not opened.
- **Status.** `GET http://192.168.4.24/status` returned 200 in one try (5 s timeout). Body saved on the Mac as `course-project/evidence/M1/M1.T6/floor-status.txt`: `fw` `bm_cam-0.1`, `framesize` `UXGA`, width 1600, height 1200, quality 10, `vflip` 0, `hmirror` 0, `rssi_dbm` −67, `uptime_ms` 44856, `frames` 0. No neighbor probe was needed.
- **Command.** From the Spark, no `/led` request, no reset, no flash:

```bash
curl -sS -D floor-$i.hdr -o floor-$i.jpg -m 20 \
  -w "floor-$i http=%{http_code} bytes=%{size_download}\n" \
  "http://192.168.4.24/capture"
# sleep 2 between the three requests
```

- **HTTP.** Each response was 200 `image/jpeg`. `X-BM-Seq` was 1, then 2, then 3. Capture timestamps (`X-BM-Capture-Us`) were 141815976, 145484772, and 149225733, so the frames are 3.67 s and 3.74 s apart. Request starts were 05:11:48, 05:11:51, and 05:11:55 UTC.

| File | Bytes | Decoded size | Start / end | `X-BM-Seq` |
| --- | ---: | --- | --- | ---: |
| `floor-1.jpg` | 316,572 | 1600×1200 | `ffd8` / `ffd9` | 1 |
| `floor-2.jpg` | 315,379 | 1600×1200 | `ffd8` / `ffd9` | 2 |
| `floor-3.jpg` | 315,347 | 1600×1200 | `ffd8` / `ffd9` | 3 |

The same three files, with the same SHA-256, are on the Spark and the Mac in this folder, and on the Mac at `/Users/xiaohuichen/Desktop/beaconmind-camera/`. Header copies `floor-1.hdr`, `floor-2.hdr`, and `floor-3.hdr` stayed on the Spark next to the JPEGs.

## What the pixels show

The car is still. Mean absolute difference between frames is about 10 gray levels (largest single-pixel difference 140–154), which is noise and JPEG change, not a new object. All three frames are the same forward view: a dim room, wood floor in the lower half, light columns and a chair farther back. The lens is looking into the room, not at the ceiling, a page, or a blank wall.

The left 15% of the width (about columns 0–230) is darker than the middle (column-mean luma about 32 versus about 78). It is a dark part of the room: grain, two small distant lights, and the floor line continuing through it. Brightness rises gradually over a few hundred columns. There is no hard silhouette of the ESP32-CAM board, the USB lip, or the ribbon. That dark band stops before the center (columns 480–1120) and before the lower-middle floor band (columns 400–1200, rows 660–1104). The right edge is a dark vertical surface of the room with the floor in front of it. Its column-mean luma is about 73, close to the middle of the frame, so it is not a cover over the lens. The bottom strip is wood floor (mean luma about 82), not a board.

## Per frame

**`floor-1.jpg`.** Board, USB lip, and ribbon in the center or the lower-middle: no. Usable forward view: yes (columns, chair, floor ahead). Focus: sharp at one high-contrast edge. On the eight rows y=516–523, mean luma falls from 159 at x=1036 to 36 at x=1039, about 120 levels in two pixels (the light column against the darker opening). Exposure: ok. Full-frame luma ≤ 8 is 1.6% of pixels; luma ≥ 247 is 0.1%. The center has 0.3% ≤ 8 and no pixels ≥ 247. The lower-middle has 0.1% ≤ 8 and no pixels ≥ 247. It is not a solid black or white frame.

**`floor-2.jpg`.** Same scene and the same column edge (159 at x=1036 to 35 at x=1039 on those rows). Board, USB, and ribbon still absent from the center and the lower-middle. Forward view usable. Exposure in the same range (full-frame ≤ 8 is 1.6%, ≥ 247 is 0.1%).

**`floor-3.jpg`.** Same scene and the same column edge (160 at x=1036 to 47 at x=1039). Board, USB, and ribbon still absent from the center and the lower-middle. Forward view usable. Exposure in the same range (full-frame ≤ 8 is 1.5%, ≥ 247 is 0.1%).

The near floor is softer than that column edge. Plank seams are still visible in the lower-middle, and that region is not a blur blob or a clip. The step 14 bar used here is one sharp high-contrast edge in the set, plus a clear center and lower-middle. Both hold in every frame.

## Task status

This check passes. M1.T6 stays `in-progress`. The status table's other acceptance items are not all met: there is still no `bracket-side.jpg` / `bracket-top.jpg` pair, no `serial-boot.txt`, no `first-frame.jpg`, no `probe-rate.txt` / `probe-freshness.txt`, and no `picture-quality.md` under the plan's `forward-*.jpg` names. Those were not created in this session. M1.T7 was not started.

AI-assisted: Grok 4.7 via Cursor, 2026-10-07: captured the three floor JPEGs and wrote this review.

verdict: pass
