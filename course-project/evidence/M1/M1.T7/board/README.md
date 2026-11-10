# M1.T7 calibration board: a checkerboard shown on the phone

Decided 2026-11-10 by Xiaohui: the camera calibration target is a checkerboard shown full screen on their
phone, held in front of the car's camera, instead of the printed 25 mm board in M1.T7 steps 1–2. The printed
board remains the fallback if the phone fails the checks below.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: generated the board, ran the detection check,
wrote this page.

## Files

| File | What it is |
| --- | --- |
| `checkerboard_12x5_2868x1320.png` | The board, 2868 × 1320 px, 8-bit grey, the phone's native landscape resolution. Also copied to the Mac's `~/Downloads/` for AirDrop. |
| `checkerboard_12x5_2868x1320.json` | Its geometry (`bm.checkerboard-1`), with the PNG's SHA-256 (`339306a2…e9edc`). |
| `detect_sim.py`, `detect_sim.txt` | The simulated detection check (below) and its output. |
| `detect_sim_fixed11.txt` | The same check with the plan's fixed 11 × 11 sub-pixel window, for comparison. |
| `../../../tools/make_checkerboard.py` | The generator; `beaconmind/tests/test_make_checkerboard.py` checks every square pixel-exact. |

Regenerate with:

```
python3 course-project/tools/make_checkerboard.py --screen 2868x1320 --ppi 460 --squares 13x6 \
    --label "iPhone 18 Pro Max" --out course-project/evidence/M1/M1.T7/board/checkerboard_12x5_2868x1320.png
```

## Geometry

The phone is an iPhone 18 Pro Max (found from the photo metadata of Xiaohui's pictures). Apple's specification
gives 2868 × 1320 px at 460 ppi. That is 0.055217 mm per pixel; Apple's 6.86-inch rectangle diagonal gives
460.2 ppi, which agrees to 0.04 %.

| Quantity | Value |
| --- | --- |
| Squares | 13 × 6 (columns × rows, landscape); top-left square black |
| OpenCV pattern size (inner corners) | **12 × 5 = 60 corners** (`--cols 12 --rows 5`) |
| Square | 165 px = **9.111 mm** (predicted, 1:1 display) |
| Board | 2145 × 990 px = 118.4 × 54.7 mm |
| White border | 361 / 362 px left/right (≈ 20 mm), 165 px top/bottom (one square, 9.1 mm) |

Why this pattern:
- The screen's short side (72.9 mm) limits the board. Six rows of squares plus a one-square white border
  top and bottom gives the largest whole-pixel squares (165 px, because 1320 / 8 = 165 exactly).
- Thirteen columns then use the long side, leaving about 20 mm of white at each end. That keeps the Dynamic
  Island and the rounded screen corners off the board.
- 13 + 6 is odd, so the board looks different after a half turn and OpenCV never confuses the corner order.
- The plan's printed 10 × 7 board would fit in a 9-square height, giving 146 px (8.06 mm) squares and
  54 corners. This one has 13 % larger squares and 60 corners.
- The white border matters: OpenCV's detector needs white around the outer squares. The black bezel and
  the metal frame start right after it.

## Putting it on the phone

1. AirDrop `~/Downloads/checkerboard_12x5_2868x1320.png` from the Mac to the phone; it lands in Photos.
2. Open it in Photos, turn rotation lock **off**, hold the phone in landscape, and tap once to hide the
   controls. The board fills the screen edge to edge. Do not pinch or double-tap (both zoom).
3. For the session:
   - **Auto-Brightness off:** Settings → Accessibility → Display & Text Size. Set brightness to about 75 %, so
     the exposure does not change between frames.
   - **Auto-Lock → Never:** Settings → Display & Brightness. Restore it afterwards.
   - **Do Not Disturb on, and no music or timer running.** A notification banner or an expanded Dynamic
     Island covering the board spoils a frame.

## Ruler check (before the capture)

- **What:** lay a millimetre ruler flat on the glass. Measure the span of the 13 squares along the long
  side, from the outer edge of the first square to the outer edge of the last. Then measure the 6 squares
  along the short side. Look straight down at the scale to avoid parallax through the glass; read to 0.5 mm.
- **Pass:** 118.4 ± 1.0 mm and 54.7 ± 1.0 mm. The phone then shows the PNG 1:1, and calibration uses
  `square_m = 0.009111`; the pixel pitch is known better than a ruler can read. If either span is outside,
  Photos has scaled the image. Use the measured long span ÷ 13 and note it.
- **Why it matters less than it seems:** the square size does not change `fx`, `fy`, `cx`, `cy` or the
  distortion, which come from the board's shape. It scales only distances (`solvePnP` translations), so it
  matters for the distance check and the extrinsics (M1.T7 steps 7–9).

## Holding the phone during the capture (replaces the distances in M1.T7 step 4)

- **How to hold it:** hold the phone by its two short ends with your fingers off the screen, and keep the
  whole phone inside the camera image. Tilt it so ceiling lights do not reflect into the camera.
- **Distances:** the board is 118 mm wide, not the printed board's 250 mm, so every distance shrinks by
  about half. The ranges below assume a 66° lens. Treat them as a starting point; the calibration
  measures the real field of view.

| Frames | UXGA 1600 × 1200 | VGA 640 × 480 | Pose |
| --- | --- | --- | --- |
| 10 | 0.20–0.30 m | 0.12–0.18 m | flat to the camera, board in each of the four image corners and the centre |
| 10 | 0.30–0.50 m | 0.18–0.28 m | tilted 30–45° left, right, up and down |
| 10 | 0.50–0.80 m | 0.28–0.40 m | various positions |
| 10 | free | free | especially near the image edges |

- **Test frame first:** capture one frame at the closest distance and look at it.
  - The squares must be sharp. The lens is fixed-focus, so if they are soft, start the bands farther away.
  - Look for dark horizontal bands. The OLED dims by flickering, and the camera's rolling shutter can catch
    the flicker; if bands appear, raise the brightness.
  - There must be no glare patch.
- The capture size must be settled first (M1.T17): intrinsics cannot be scaled from VGA to UXGA.

## Simulated detection check (2026-11-10)

**Method.** `detect_sim.py` (Spark host, OpenCV 4.13) builds each view as follows:
- poses the PNG, with a black bezel and a bright frame around it, in 3-D at each distance;
- uses tilts of 0°, 40° yaw, 40° pitch and 30° + 30°, at three image positions;
- renders it supersampled, then adds blur, noise and JPEG compression;
- compares the detected corners with the exact projected ones.

The results are summarised from `detect_sim.txt` and count only views with every corner inside the image.

| Size | Distance | Classic: found | Classic: worst RMS | SB: found | SB: worst RMS |
| --- | --- | --- | --- | --- | --- |
| UXGA | 0.15–0.70 m | 51/51 | 0.13 px | 50/51 | 0.34 px |
| UXGA | 0.90–1.10 m | 19/24 | 0.23 px | 24/24 | 0.38 px |
| VGA | 0.12–0.35 m | 32/35 | 0.21 px | 34/35 | 0.31 px |
| VGA | 0.45–0.55 m | 17/24 | 0.35 px | 23/24 | 0.41 px |

The mean bias over all detections is 0.01–0.02 px. The misses are mostly steep tilts toward an image corner
at long range. One is a view whose white border ran off the image edge, which is why the whole phone must
stay in view.

What this means for `calibrate_camera.py` (M1.T7 step 5):
- **Pattern size:** pass `--cols 12 --rows 5`. "All 54 corners" in the plan becomes all 60.
- **Sub-pixel window:** size `cornerSubPix`'s window from the detected corner spacing. Use a half-window
  of 0.4 × the smallest distance between neighbouring detected corners, at most 11. Do **not** use the
  plan's fixed 11 × 11 (half-window 11). Its 23 px search area is larger than a square at UXGA from about
  0.5 m and at VGA from about 0.18 m, and corners then snap to their neighbours.
  - **Fixed window, same views (`detect_sim_fixed11.txt`):** the worst RMS is 5.7–8.1 px at UXGA from
    0.5 m and 2.6–8.8 px at VGA from 0.18 m.
  - **Window from the nominal square size:** a first run sized the window from the nominal square size
    instead of the spacing. Steep views near an image corner then gave 1.6–2.4 px RMS and up to 5.4 px
    errors, because the foreshortened squares were smaller than the window.
  - **Spacing rule:** the classic detector's worst RMS anywhere is 0.35 px.
- **SB detector:** when the classic detector finds nothing, try `findChessboardCornersSB` (exhaustive,
  accuracy flags). It finds more boards at range, at somewhat lower precision; use it as a fallback, not
  first.

Limits:
- This is a simulation, so lens distortion, real defocus, glare and screen flicker are absent. It shows
  that the board and its border are detectable at these sizes. It does not show the real error.
- The real camera's calibration RMS (M1.T7 step 6) is the test that counts.

## Record (fill in at the bench)

| Date | 13-square span (mm) | 6-square span (mm) | Pass? | `square_m` used | Brightness | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| | | | | | | |
