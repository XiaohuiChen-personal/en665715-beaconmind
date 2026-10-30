# M1.T6 overnight gaps

Checked 2026-10-07T06:29:01Z against the acceptance list in `course-project/plan/M1-foundations.md` (M1.T6) and the files already in this folder. Status stays `in-progress`. No level reading was invented. The camera, serial port, vLLM, and Isaac were not used.

## Already on disk

- **UXGA firmware.** `floor-status.txt` is `bm_cam-0.1`, framesize UXGA, 1600×1200, quality 10. The sketch sets `FRAMESIZE_UXGA`.
- **HTTP.** `pictures/floor-review.md` records three `GET http://192.168.4.24/capture` responses, each HTTP 200, `X-BM-Seq` 1 then 2 then 3, JPEG magic `ffd8`…`ffd9`.
- **Floor picture check.** `pictures/floor-review.md` ends with `verdict: pass`.
- **USB unplugged.** The same note records Spark `lsusb` at 2026-10-07T05:10:07Z with no `0843:5740` and no FIREPHX by-id link. The serial port was not opened.
- **Toolchain row.** `toolchain.txt` has arduino-cli 1.5.2-rc.1, esp32 core 3.3.12, FQBN `esp32:esp32:esp32cam`.

## Gaps (these keep the task in progress)

- **Wi-Fi on battery is not stated.** USB-out plus `rssi_dbm` −67 shows the board answered on Wi-Fi while the USB serial device was absent. No file in this folder records the battery-switch position, the pack voltage, or that the camera’s 5 V came from the battery. The task text for the floor capture says the battery switch is OFF. A desk-session note mentions a power bank in a phone photo; that is a different session and is not a battery reading.
- **Level reading is missing.** There is no degree reading from a square or a phone level app. `bracket-side.jpg` and `bracket-top.jpg` are absent. `camera-quality.md` says lens height, pitch, and roll have not been measured.
- **h/d ruler photo is missing.** The task says the ±3° level report and the h/d ruler photo stay required on their own. No ruler photo and no h or d number are in this folder.
- **`serial-boot.txt` does not show `BM_CAM READY`.** The file exists and is 0 bytes. `serial-boot-uxga.txt` is also 0 bytes. `BM_CAM READY ip=192.168.4.24 rssi=-57 fw=bm_cam-0.1` is line 53 of `serial-boot-dout-rst2.txt`. A search of that file for `ssid` or `pass` printed nothing. The acceptance line names `serial-boot.txt`.
- **`first-frame.jpg` is missing.** The printed-text upright / not-mirrored check is not recorded. `camera-quality.md` only notes a mirroring hint.
- **`probe-rate.txt` and `probe-freshness.txt` are missing.** `camera-quality.md` says the step 13 rate and freshness probes have not run. No stop-and-ask outcome for those thresholds is recorded.
- **The named step 14 files are missing.** There is no `forward-1.jpg`, `forward-2.jpg`, `forward-3.jpg`, or `picture-quality.md`. The pass is on `pictures/floor-1.jpg`, `floor-2.jpg`, `floor-3.jpg`, and `pictures/floor-review.md`. Those are not the filenames in the acceptance list.
- **Other named evidence files are also absent:** `usb-before-after.txt`, `status.json`, `led-off.txt`, and the three `forward-*.hdr` files. `usb-and-load.txt` and `floor-status.txt` are different files.

M1.T7 was not started.

AI-assisted: Grok 4.7 via Cursor, 2026-10-07: compared the acceptance list with the files already on disk and wrote this gap note.
