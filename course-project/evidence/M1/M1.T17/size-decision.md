# M1.T17 — camera capture size: decision (2026-11-18)

**Choice (Xiaohui Chen, 2026-11-18): XGA, 1024 × 768 pixels, JPEG quality 12** (`bm_cam-0.2`:
`GET /control?framesize=xga&quality=12`). M1.T7 calibrates at this size, and every later capture uses it.

## The probes it rests on

Floor spot in the arena room, the camera about 141 cm from a bare wall (Xiaohui's tape), the car parked with the motor
battery off. `tools/camera_probe.py --n 100` per setting, run on the Spark host inside the recorded session
`20261118-001733-capture-size` (`tools/record_session.sh`, the probe as the camera's only client, every frame kept with
`--save`). Output: `probe-n100.txt`; the session's README: `session-README.md`.

| Setting | OK | Frames/s | Latency p50 / p95 / max | Mean JPEG | Size check | Plan bar (≥ 3 frames/s, p95 ≤ 500 ms) |
| --- | --- | --- | --- | --- | --- | --- |
| VGA 640 × 480, q12 (boot setting, not switched) | 100/100 | 7.107 | 126.2 / 184.3 / 233.0 ms | 9 314 B | — | pass |
| XGA 1024 × 768, q12 | 100/100 | 5.395 | 181.1 / 236.8 / 283.8 ms | 22 394 B | 0 mismatches | pass |
| UXGA 1600 × 1200, q10 | 100/100 | 1.751 | 557.5 / 664.9 / 781.6 ms | 107 194 B | 0 mismatches | **fail** |

Camera sequence numbers rose strictly in every run. The link held throughout: 473 / 473 pings to the car and to the
camera, longest gap 0.31 s. The camera was set back to VGA q12 at the end (its boot setting).

## Why XGA (Claude's recommendation, Xiaohui's choice)

- The room puts tags 2–2.5 m away more often than the study's 2.25 m arena (`evidence/M3/M3.T10/layout/coverage.txt`).
  A 160 mm tag spans about 44 / 35 px at 2 / 2.5 m in VGA and about 71 / 57 px in XGA (estimates from the design's 60°
  field of view; M1.T7 measures the real one), so XGA gives 1.6 times the pixels per tag for detection and range.
- XGA passes the plan's bar with room to spare. UXGA fails it (1.75 frames/s, p95 665 ms), and its frames looked soft.
- Sizes up to XGA are binned on the OV3660 and UXGA is not, so K is never scaled between them (M1.T7 pitfall).

## Edits made in the same session (plan step 3)

The choice is not UXGA quality 10, so the "must be 1600×1200" sentences were edited in `plan/M1-foundations.md`:
M1.T6 step 13's pass-threshold note, M1.T7's 2026-10-29 note, its *Why* paragraph (now `/control?framesize=xga&quality=12`
and the 1024 × 768 size check) and its first pitfall; the 2026-11-10 phone-board notes gained the XGA distance band
(about 0.15–0.60 m, to check with `detect_sim.py` at 1024 × 768) and the square size at 1 m (about 7 px).

## Consequence for every session

`bm_cam-0.2` boots at VGA and does not keep a `/control` size across a reboot. Every program that captures must set XGA
q12 first and drop frames whose `X-BM-Width` / `X-BM-Height` are not 1024 × 768. `tools/record_session.sh` now does
that at `start` (`--camera-size`, default `xga`, quality 12).

`configs/camera.json` still does not exist; M1.T7 is still todo.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-18: ran the probes and wrote the record. Xiaohui Chen chose the size.
