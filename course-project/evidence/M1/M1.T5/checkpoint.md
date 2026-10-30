# M1.T5 checkpoint — 2026-10-07 00:48 CT

Status: in progress. Steps 2–9 and the Isaac 6.0 tag listing are done. OD7 is a proposal of 5.1 in `od7-decision.md`. Xiaohui has not approved it. Leave the status row `in-progress`.

## Done

- MDL identifiers: `mdl-parameters.txt`. Texture is 263×274 RGBA. Parameters: `tag_mosaic`, `tag_size` 10, `tags_per_row` 24, `spacing` 1, `tag_id`.
- API: `api-sources.txt`. Material loaded from the asset server (`MATERIAL_SOURCE asset-server`).
- Detector self-test on the Spark: `detect-selftest.txt` (`selftest ok: id 3, range 0.697 m`).
- Kept render: `data/renders/spike-20261007-001302` on the Spark. `READY 6.8`, `DONE`, `exit=0`. UXGA 1600×1200, HFOV 60°, fx=fy=1385.641. Do not repeat those renders.
- Offline decode (`detect-offline.csv`), id 3 in 4 of 4, range within 5%.
- `apriltag_ros` on `tag3_d1.0.png`: id 3, family `tag36h11`, hamming 0 (`apriltag-ros-on-render.txt`). The launch and the publisher were stopped. `beaconmind-ros` was left up.
- Isaac 6.0 tags include `v6.0.1` (`isaac6-tags.txt`). Not built. `/home` has 2.2T free.
- Downscaled frames: `render-d1.0.png`, `render-d2.0.png`.
- Kit lifetime (`kit-lifetime.md`):
  - Base, tmux `bm-m1t5-life` finished. `READY 6.7`, last `ALIVE 906.7`, `DONE`, `exit=0`. Log mtime 2026-10-07 00:30:49 -0500.
  - ROS bridge, tmux `bm-m1t5-ros` finished. `READY 7.1`, last `ALIVE 907.1`, `DONE`, `exit=0`. Humble `rclpy` loaded. Log mtime 2026-10-07 00:47:08 -0500.
  - Self-kill not reproduced in 900 s.

Earlier renders that did not decode are in `render-attempts.md`.

## Left alone

`vllm-rosa` and `qwen38-flash` were left exited. Nothing was `docker rm`'d. The ESP32 serial port was not opened. `beaconmind-ros` stayed up. tmux `bm-m1t11` was already present at 00:46 CT and was not used.

## Next

Xiaohui approves or changes the 5.1 recommendation in `od7-decision.md`. Do not start another Isaac kit for M1.T5. Do not mark M1.T5 done until that approval and the date are in `od7-decision.md`.

## Generative-AI disclosure

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: recorded the Qwen3.8 pin, deferred Bonsai, and started M1.T5.
AI-assisted: Grok 4.7 via Cursor, 2026-10-07: finished both kit-lifetime runs and updated this checkpoint.
