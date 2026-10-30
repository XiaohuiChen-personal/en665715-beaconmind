# The real ESP32-CAM, as the Isaac Sim camera must model it (UXGA 1600×1200, JPEG quality 10)

Date: 2026-10-06. Task: M1.T6 (camera). The firmware is settled at **UXGA 1600×1200, JPEG quality 10**
(Xiaohui's decision, 2026-10-06). This note says what the Isaac Sim camera must and must not copy from
the real camera. It started as a copy of `course-project/evidence/M1/M1.T6/camera-quality.md`, which
compared the earlier SVGA 800×600, quality-12 frames with a phone photo. It was then updated to UXGA.
`camera-quality.md` was not edited and still describes SVGA. The record of the UXGA view is
`course-project/evidence/M1/M1.T6/pictures/desk-review.md`, and section 4 below matches it.

This is not the M1.T6 step 14 picture-quality check. M1.T6 is not done. M1.T7 has not started. For this
update no frame was captured, nothing was flashed, and nothing was committed.

## Short answer

- **Operating mode.** UXGA 1600×1200, `jpeg_quality` 10, one frame buffer in PSRAM. `/status` reports
  `UXGA`, 1600×1200, `quality` 10, and the three desk frames decode as 1600×1200.
- **Picture quality.** Still soft, and much grainier than SVGA. The cleanest edge takes about 10 px to
  rise at 1600 wide, about 5 px at 800-wide scale against 6.5 px for SVGA by the same method. So UXGA is
  a little crisper, not sharp. In the dark wood, per-pixel noise is four to five times the SVGA level.
  The SVGA binning and downscale had been averaging it away.
- **Field of view.** The same as SVGA's to within about half a percent (scale 1.004). The UXGA view sits
  about 2.7 % of the frame width to one side of the SVGA view.
- **Is the board in the frame?** No. No board edge, USB plug, ribbon, beam, chassis plate or caster appears
  in any of the three UXGA frames.
- **Why is the near desk missing?** It is below the frame, not blurred away. The lens sits just above the
  board and looks forward, about level.
- **For Isaac Sim:** do not match a phone photo. Render 1600×1200, blur it, add heavy grain, and compress
  it to a 4:2:2 JPEG at about libjpeg quality 69 (about 330 KB for a dim scene like the desk). Keep the
  car and the near floor out of view, and label the 60° HFOV as a design value until M1.T7 measures it.

## Evidence

| File | What it is | Key facts |
| --- | --- | --- |
| `course-project/evidence/M1/M1.T6/pictures/uxga-1.jpg`, `uxga-2.jpg`, `uxga-3.jpg` | three UXGA frames, car on a desk; saved on the Spark at 21:48:07, 21:48:12 and 21:48:18 CDT | 327,546 / 331,816 / 343,838 bytes; 1600×1200; each starts `ffd8` and ends `ffd9`. HTTP codes and `X-BM-Seq` headers were not saved |
| Spark `/tmp/bm-status-body.txt` (21:47:36) | `/status` JSON fetched before those frames | `framesize` UXGA, 1600×1200, `quality` 10, `vflip` 0, `hmirror` 0, `psram` true, `frames` 0, `rssi_dbm` −69 |
| `course-project/evidence/M1/M1.T6/pictures/desk-review.md` | the UXGA view record | mount, aim, what is and is not in the frame, UXGA against SVGA measurements |
| `course-project/evidence/M1/M1.T6/uxga-build.txt`, `uxga-write.txt` | UXGA compile and app-only write | compile note `frame_size=FRAMESIZE_UXGA width=1600 height=1200 jpeg_quality=10 fb_count=1`; app written at 0x10000 only, hash verified |
| `course-project/evidence/M1/M1.T6/serial-boot-uxga.txt` | serial log for the UXGA image | 0 bytes: nothing recorded |
| `course-project/evidence/M1/M1.T6/serial-boot-dout-rst2.txt` | serial log from the earlier SVGA image | `BM_CAM READY ip=192.168.4.24 rssi=-57 fw=bm_cam-0.1` (line 53); 94 of its 105 lines are `cam_hal: FB-OVF` |
| `course-project/evidence/M1/M1.T6/dout-write.txt` | esptool output | chip `ESP32-D0WD-V3 (revision v3.1)`: a plain ESP32, not an S2 or S3 |
| `course-project/evidence/M1/M1.T6/toolchain.txt` | builder image record | Arduino core `esp32:esp32@3.3.12` |
| `course-project/firmware/esp32cam/bm_cam/bm_cam.ino` | the running sketch, `bm_cam-0.1` (UXGA build) | camera settings in `startCamera()`, lines 144–181 |
| Earlier SVGA frames `capture-1..3.jpg` (31,918 / 33,402 / 32,071 bytes) and `current-1..3.jpg` | 800×600, quality 12 | **deleted 2026-10-06** at Xiaohui's request. The numbers measured on them are kept below and marked as such |
| Phone photo `IMG_7414` (Xiaohui, 2026-10-06), at `/Users/xiaohuichen/.cursor/projects/Users-xiaohuichen-Projects-EN-665-715/assets/IMG_7414-b5f651b6-1f37-4cd9-a814-f05c2dd1af40.jpg` | the desk scene from above and beside the car; a 1024×768 copy | not copied into the repo, because personal mail is legible in it (plan README L8) |
| Upstream `espressif/esp32-camera`, master commit `2bba0d1d57` (committed 2026-09-28, retrieved 2026-10-06): `driver/cam_hal.c`, `driver/sensor.c`, `sensors/ov3660.c`, `sensors/private_include/ov3660_settings.h`, `Kconfig` | the camera driver source | Upstream line numbers below refer to this commit, as cited in `camera-quality.md`; they were not re-checked for this update. The exact revision built into core 3.3.12 is not confirmed. |

## 1. What the camera is set to

| Setting | Value | Where it is set or checked |
| --- | --- | --- |
| Frame size | `FRAMESIZE_UXGA`, 1600×1200 | sketch line 166; all three files decode as 1600×1200; `/status` reports `UXGA` |
| JPEG quality | `jpeg_quality = BM_JPEG_QUALITY` = 10 | sketch lines 54 and 167; `/status` reports 10 |
| What the number means | 0–63, lower = higher quality. It is the OV3660's own compression setting (the driver writes it to the sensor register `COMPRESSION_CTRL07`), not the 1–100 libjpeg scale. | core header `esp_camera.h` line 150 ("0-63 lower means higher quality"); upstream `ov3660.c` `set_quality`, lines 413–419 |
| Frame buffers | 1, in PSRAM, `CAMERA_GRAB_LATEST` | sketch lines 55 and 168–170 |
| `/capture` | takes one frame and hands it back to the driver unsent, then takes a fresh frame and serves it | sketch lines 109–130 |
| Clock | XCLK 20 MHz | sketch line 162 |
| Flip and mirror | `vflip` 0, `hmirror` 0 (compile-time defaults) | sketch lines 23–28 and 177–178 |
| Exposure, gain, white balance, sharpness, denoise | not set, so the driver and sensor defaults (automatic) apply | the sketch calls no other sensor setter. The OV3660 driver offers `set_sharpness`, `set_denoise`, `set_gainceiling`, `set_ae_level`, `set_aec_value` and `set_agc_gain` (upstream `ov3660.c` lines 1018–1051) |
| Earlier setting (superseded) | SVGA 800×600, quality 12, 2 frame buffers | `camera-quality.md` §1 |

Two cautions:

- `/status` now reports the driver's own record (`sensor->status.framesize` and `.quality`, sketch lines
  89–96). That is the value the driver was asked to set, not a register read back from the sensor. The
  1600×1200 decode confirms the frame size by itself. The JPEG luma table (section 2) is finer than the
  SVGA quality-12 table, which fits a lower quality number, but it does not prove the register value.
- The step 12 orientation check (printed text held in front of the lens) has not been done. The picture
  is right side up (desk at the bottom), but left–right mirroring is not verified. Section 4 gives a hint
  that it may be mirrored.

## 2. What the frames measure

### 2.1 UXGA frames (the operating mode), remeasured 2026-10-06

Measured on the Mac with Python 3.13.7, Pillow 11.3.0 and numpy 2.3.3, in an ad hoc script that was not
saved as a tool. The "10–90 % edge width" is the vertical distance over which a dark-to-light edge rises
from 10 % to 90 % of its step. It is taken from an edge profile averaged over 200–240 columns. A
perfectly sharp edge measures about 1–2 px with this method. The residual is each pixel minus its 7×7
neighbourhood mean.

| Measure | uxga-1 | uxga-2 | uxga-3 |
| --- | --- | --- | --- |
| Bytes | 327,546 | 331,816 | 343,838 |
| Mean luma (0–255) | 74.8 | 75.3 | 75.0 |
| 1st / 50th / 99th percentile luma | 16 / 60 / 254 | 16 / 61 / 254 | 15 / 61 / 254 |
| Pixels ≥ 250 (near white) | 3.66 % | 3.74 % | 3.70 % |
| Pixels ≤ 5 (near black) | 0.09 % | 0.10 % | 0.12 % |
| Edge width: top rail of the panelling against the pale wall (far) | 10.0 px | 9.75 px | 10.25 px |
| Edge width: top of the white paper, lower right | 13.25 px | 13.25 px | 13.25 px |
| Edge width: top of the white coil, lower left | 16.25 px | 16.0 px | 16.5 px |
| Flat-patch residual, dark wood (mean luma ≈ 49), R / G / B standard deviation | 10.6 / 10.7 / 12.0 | 11.0 / 11.2 / 12.4 | 12.2 / 12.3 / 13.6 |
| Flat-patch residual, pale wall (mean luma ≈ 166), R / G / B standard deviation | 1.4 / 1.3 / 2.4 | 1.4 / 1.3 / 1.8 | 1.3 / 1.3 / 2.4 |

The same script was run on the SVGA frames `capture-1..3.jpg` before they were deleted, using the same
edges and patches, mapped across:

| Measure | SVGA q12 | UXGA q10 | UXGA, in 800-wide pixels |
| --- | --- | --- | --- |
| Edge: rail against the pale wall | 6.3–6.8 px | 9.8–10.3 px | 4.9–5.1 px |
| Edge: top of the white paper | 7.3–7.5 px | 13.3 px | 6.6 px |
| Edge: top of the white coil | 8.0 px | 16.0–16.5 px | 8.0–8.3 px |
| Dark wood residual R / G / B | 2.3–2.5 / 2.4–2.7 / 4.8–5.8 | 10.6–12.2 / 10.7–12.3 / 12.0–13.6 | 8.2–9.2 / 8.4–9.7 / 11.3–12.4 (after a 2× box downscale) |
| Pale wall residual R / G / B | 0.6–0.7 / 0.5–0.7 / 1.0–1.2 | 1.3–1.4 / 1.3 / 1.8–2.4 | 1.6–1.7 / 1.6–1.7 / 2.4–3.1 |

Other facts from the UXGA files:

- **JPEG structure.** Baseline JFIF, two quantization tables, 4:2:2 chroma subsampling. The luma table
  is closest to libjpeg quality 69 (my estimate, from a log-ratio fit to the standard table). The SVGA
  quality-12 frames came out at about 62 by both this fit and the first version of this note.
- **Frame-to-frame change.** Mean absolute luma difference 10.6–11.0 between the three frames, which
  were 5–7 s apart. At SVGA it was 2.9–3.1. Most of the difference is grain.
- **Colour.** The dark wood averages RGB (56, 47–48, 34–37), against (57, 53, 32) at SVGA and (47, 25, 8)
  in the phone photo. Automatic white balance still turns the warm-lit wood olive-brown.
- **Field of view against SVGA.** Nine features were matched between `capture-1.jpg` and `uxga-1.jpg`
  (both blurred, at 800-wide scale). The best fit is a scale of 1.004 and a rotation of 0.2°, with a
  shift of −21.7 px across and −1.1 px down (about −43 px at UXGA), leaving 2.4 px rms. So the field of
  view is the same to within about half a percent. The view moved sideways by about 2.7 % of the width
  (about 1.8° under the 60° design HFOV). Whether the car or camera was nudged during the reflash, or
  the sensor reads a slightly offset window at UXGA, is not settled.
- **Limits of these numbers.** Real edges are not ideal steps (the rail is a rounded moulding, the paper
  is curled, the coil is round), so the widths are upper bounds on the camera's own blur. The residuals
  include any fine wood or wall texture, so they are upper bounds on noise. These patches differ from
  those of section 2.2, so compare residuals within a table, not across tables.

### 2.2 Earlier SVGA frames: measured on the earlier 800×600 frames, not remeasured

These numbers were measured on `capture-1..3.jpg` (800×600, quality 12; deleted 2026-10-06) with the
per-column method of the first version of this note. They stay valid as a record of SVGA. For the
operating mode, use section 2.1.

| Measure | capture-1 | capture-2 | capture-3 |
| --- | --- | --- | --- |
| Bytes | 31,918 | 33,402 | 32,071 |
| Mean luma (0–255) | 77.7 | 76.7 | 77.4 |
| 1st / 50th / 99th percentile luma | 23 / 62 / 254 | 21 / 61 / 254 | 23 / 62 / 254 |
| Pixels ≥ 250 (near white) | 3.95 % | 4.00 % | 3.92 % |
| Pixels ≤ 5 (near black) | 0.00 % | 0.01 % | 0.00 % |
| Edge width: top rail of the panelling against the pale wall (14 columns) | 7.7 px | 7.5 px | 7.3 px |
| Edge width: top of the white paper, lower right (11 columns) | 5.9 px | 5.9 px | 5.9 px |
| Edge width: top of the white cable loop, lower left (16 columns) | 8.3 px | 8.2 px | 8.1 px |
| Edge width: pale wall to the dark strip at the right edge (18 rows; a two-step edge) | 10.5 px | 10.5 px | 11.2 px |
| Flat-patch residual, dark cabinet (mean luma ≈ 45), R / G / B standard deviation | 2.2 / 2.4 / 5.2 | 2.7 / 2.8 / 5.8 | 2.5 / 2.6 / 5.7 |
| Flat-patch residual, pale wall (mean luma ≈ 154), R / G / B standard deviation | 2.8 / 2.8 / 2.8 | 3.0 / 2.9 / 3.0 | 2.8 / 2.8 / 2.9 |

**Compression control (done for SVGA, not repeated for UXGA).** Synthetic edges encoded with Pillow at
quality 62, 4:2:2, and measured the same way changed width by at most 0.6 px. For example, an edge
blurred with a Gaussian of σ = 3 px went from 8.0 to 8.6 px, and a hard step from 0.8 to 1.0 px.
Compression changes the shape of an edge; it does not turn a sharp edge into a 6–11 px wide one.

## 3. Is this the best this setup can do?

Each cause on its own:

**Lens focus and optics: still the main limit on sharpness.** At UXGA the far rail edge rises over about
10 px. At 800-wide scale that is about 5 px, against 6.5 px for SVGA by the same method, so the SVGA
binning and downscale added some blur. The edge is still about five times wider than a sharp one. At
UXGA the near edges (the coil, 16 px; the paper, 13 px) are softer than the far rail. At SVGA they looked
about as soft as the far panelling, so the earlier statement that the softness is the same at every
distance does not hold at UXGA. It may be focus, or the rounded coil and curled paper; it is not settled.
The focus distance of this lens is not known. Firmware cannot change the focus: the driver's autofocus
option is for the OV5640 only (upstream `Kconfig` lines 52–58, "depends on OV5640_SUPPORT"; the core's
`sdkconfig` line 2785 has it unset). Three things were not checked. First, whether the clear lens film
is completely off. Second, whether the lens is smudged. Third, whether this module's lens can be turned
to refocus. Turning a glued lens can damage the module and would invalidate any calibration, so it is
Xiaohui's decision, not a default step.

**Resolution: UXGA is now the operating mode.** The driver allows the OV3660 up to QXGA, 2048×1536
(upstream `sensor.c` line 8; `ov3660.c` `set_framesize` clamps to QXGA at lines 315–318). At SVGA and XGA
the driver puts the sensor in 2×2 binning; UXGA and QXGA are read without binning (`ov3660.c` line 326;
`ov3660_settings.h` line 11). That fits what the frames show: more detail per degree at UXGA, and far
more grain per pixel, because binning no longer averages it. The field of view did not change (section
2.1). The plan still describes SVGA, quality 12 (M1.T6 step 8; `fx 693` for an 800-wide image; the
M1.T5 spike's `--width 800 --height 600`). That text was not edited, and plan M1.T6 step 13 says a
change of frame size or quality redoes M1.T7.

**JPEG quality number: 10, not the cause of the softness.** The tables it produced are close to libjpeg
quality 69, finer than SVGA's 62. The sketch leaves `jpeg_buffer_size` at 0, and `camera-quality.md`
gives the automatic JPEG frame buffer as width × height / 5 (upstream `cam_hal.c` lines 586–596;
`CONFIG_CAMERA_JPEG_MODE_FRAME_SIZE_AUTO=y` at the core's `sdkconfig` line 2809). At UXGA that is
384,000 bytes. The desk frames are 327,546–343,838 bytes, 85–90 % of it.

**Exposure: as before; grain is now the cost.** The scene was a dim evening desk under warm light, on
automatic exposure. The white paper clips in places (about 3.7 % of pixels are ≥ 250) and almost
nothing clips to black (≤ 0.12 %). The dark wood carries heavy coloured grain at UXGA (section 2.1).
More light would reduce it. Manual exposure, gain ceiling, sharpness and denoise have not been tried.

**`FB-OVF` drops: a closer risk at UXGA.** On a plain ESP32 (this chip is an ESP32-D0WD-V3) the driver's
DMA-to-PSRAM mode is off; it exists only on the S2 and S3 (upstream `cam_hal.c` lines 576–580). So every
frame is copied from small DMA buffers into the frame buffer. `cam_hal: FB-OVF` is printed when one
frame's bytes would overflow that buffer (`cam_hal.c` lines 296–302 and 373–378). That frame is cut
short, and the driver rejects any frame with no JPEG end marker (`FF D9`) and waits for the next one
(`cam_hal.c` lines 740–776, in `cam_take`). So a served frame is a complete JPEG, as all three UXGA frames
are. At SVGA, frames were a third of the buffer and the logged overflows were not explained by frame
size. At UXGA they fill 85–90 % of it, so a busier or brighter scene could overflow on size alone.
`serial-boot-uxga.txt` is empty, so whether drops happen at UXGA is unknown. The step 13 rate and
freshness probes have not run.

**Verdict.** At UXGA quality 10 the frames are a little crisper than SVGA in angle and much grainier per
pixel. They are still soft: the optics limit sharpness, and noise is the new cost. Neither is proven to
be the camera's best, because manual exposure, more light and sharpness or denoise settings are untried.

## 4. Viewpoint: where the lens points and what it sees

This section matches `desk-review.md` (2026-10-06).

**Mount, from the phone photo.** The camera module stands upright against the grey Technic angle beam,
at the battery-holder end of the ESP32-CAM board. The board lies flat on top of the caster end of the
clear chassis, with its USB-C plug at the far end. The black lens barrel lies roughly horizontal and points
over the board toward the USB-C plug and the caster. That is **forward**, the project's +x
(`course-project/AGENT-DESIGN.md` D3: "camera/caster end = front"). The lens sits just above the
board's top surface, and the board runs on ahead of and below it. Any sideways offset from the car's long
axis looks small in the photo but is not measured.

**Aim, from the UXGA frames: forward and about level, possibly tipped a little up, not down.**

- A vertical surface fills about the top four-fifths of the frame: dark wood panelling, with its top rail
  and a pale wall above it at the top right. A lens tipped down would show more desk and less wall.
- The desk shows only as a band along the bottom, from about row 970 near x = 900 to about row 1,100 at
  the right edge, and below a white coil from about row 1,045 on the left. That is the lowest 8–20 % of
  the frame height.
- Nothing belonging to the car is in view. The board lies ahead of and below the lens, so its front edge
  would enter the bottom rows first if the lens tipped down. It is not there.
- No large roll: the panel stiles stand within about 4° of the image vertical. Fits of the stiles are
  too noisy to measure roll or pitch.
- The wall's two horizontal mouldings (at 20.7° and 18.2° in the image) meet far to the right near row
  1,070–1,100, which would put the horizon below the centre: an upward tilt. The lines are almost
  parallel, so this is a weak hint, and no angle is given.

The lens height, pitch, roll and yaw are not measured (M1.T7 extrinsics).

**In the frame:** the dark wood panelling (two raised panels, the stile between them, a stile on the
left, the right panel's right edge); its top rail sloping down to the right at about 20° in the image;
a pale cream wall at the top right; at the far right edge, a dark vertical frame with a light ledge (not
identified); along the bottom, the reddish-brown desk top. On the desk are a white coiled object with a
curved loop and a black rod at the lower left (probably the cable coil and pen from the back of the desk
in the phone photo), a grey-brown textured object (not identified), and white paper with a crumpled top
edge and a faint red line at the lower centre and right, cut off by the bottom edge.

**Not in the frame:** the ESP32-CAM board, USB-C plug and cable bend, ribbon, Technic beam, chassis plate
and caster; the paper directly under and beside the car, including the pad's label next to the caster;
and the desk right in front of the car. Because the board's front edge is out of view, the desk under
the car's nose, which lies lower still, is out of view too. The power bank beside the car cannot be
picked out.

**A hint that the image is mirrored (carried forward; the UXGA frames show the same layout).** The cable
coil and the pen are at the back of the desk, beside the panelling. The papers are on the near side of
the car. For a lens that points toward the photo's left, the image's left should be toward the papers
and its right toward the back of the desk. The frames show the opposite. The panelling rails also slope
down to the right. That is what a left–right mirrored image would show. It is a hint from rough scene
geometry, not a check; step 12's printed-text test decides it. If the image is mirrored, every bearing
has the wrong sign, and tags may fail to decode.

**Why the phone photo looks so much better.** It was taken from a different place, higher and beside the
car, with autofocus on the car, by a much larger camera. Even the phone photo is not sharp everywhere:
its background panelling is blurred. It shows the scene; it is not a target for the ESP32 frames.

## 5. Step 14 (read only; the plan was not edited)

The UXGA desk set does not meet the M1.T6 step 14 pass rule, and it is not a step 14 set at all:

- The car was on a desk, not on the floor, and the lower part of the view is not the floor ahead.
- The frames are `uxga-*.jpg`, not `forward-*.jpg` with `.hdr` files, `led-off.txt` and
  `picture-quality.md`. Their HTTP headers, including `X-BM-Seq`, were not saved. They were saved
  5–7 s apart.
- The board is absent and no frame is a solid black or white clip. Those parts of the rule would be met.
- The rule needs "at least one frame shows a sharp high-contrast edge". The crispest edge here takes
  about 10 px to rise at 1600 wide. I would call that soft, not sharp. The rule gives no number, so this
  is a judgement for the step 14 review.

M1.T6 stays not done. M1.T7 must not start from these frames.

## 6. What Isaac Sim must not assume, and what it should do

The Isaac camera stands in for this camera (plan README C12: `/camera/image_raw` comes from the Isaac
camera in the twin, and from `bm_camera_bridge` decoding the ESP32 JPEG on the car). If the sim image is
much cleaner than the real one, tags will decode farther and more reliably in the sim than on the car, and
sim results will be too optimistic.

**Must not assume:**

1. Phone-photo sharpness, or the crisp edges of an ideal pinhole render.
2. The near field a person sees. The phone looks down from above and beside the car. The ESP32 lens sits
   just above the board and sees none of the car and none of the desk or floor just ahead of its nose.
3. Clean, decodable tags at the bottom of the frame or very close to the car.
4. A noise-free 1600×1200 image, or a lossless PNG. The real frames are compressed JPEGs with heavy
   grain.
5. A measured field of view. HFOV 60° is a design value (`course-project/AGENT-DESIGN.md` D3, "Camera
   HFOV | 60°"). M1.T7 has not run.
6. A steady frame rate with every frame fresh. `FB-OVF` drops were logged at SVGA, UXGA frames fill
   85–90 % of the buffer, and step 13 has not measured rate or freshness.
7. Correct left–right orientation of the real image. Step 12's printed-text check has not been done.

**Should do, until M1.T7 and step 14 give measured values:**

- **Pose.** Lens on the car, just above the ESP32-CAM board at the caster end, axis along +x (forward),
  about level, possibly tipped a little up, never down, with no roll. Take x, z, pitch and yaw from
  M1.T7. Until then, record them in every sim result as unmeasured.
- **View check.** Facing a wall like the desk scene, a vertical surface fills most of the frame, the
  floor shows only as a band along the bottom, and no part of the car is in view.
- **Resolution:** 1600×1200, 4:3. Use fx = fy until calibration says otherwise.
- **Field of view:** HFOV 60° and VFOV about 46.8° (2·atan(0.75·tan 30°)), so fx = fy ≈ 1386 px at 1600
  wide. Label both angles as design values in every sim result. Replace them with
  `course-project/configs/camera.json` after M1.T7.
- **Softness:** blur the render so that a far high-contrast edge rises from 10 % to 90 % over about
  10 px at 1600 wide (a Gaussian with σ ≈ 4 px), and allow 13–16 px (σ ≈ 5–6.5 px) for near objects.
  For a Gaussian blur the 10–90 % width is about 2.56 σ.
- **Noise:** add sensor noise before compression. Tune it so that, after compression, a flat dark patch
  (mean luma about 49) has a per-pixel residual of about 11–12 levels in red and green and 12–14 in blue,
  and a bright patch (mean about 166) about 1.3 in red and green and about 2 in blue.
- **JPEG:** encode each sim frame as a baseline JPEG with 4:2:2 chroma at about libjpeg quality 69. The
  real frames of this dim indoor scene were 320–336 KiB. A sim frame of a similar scene several times
  smaller is missing the grain; one much larger carries detail the camera does not deliver. Give the tag
  detector the decoded JPEG, not the raw render.
- **Exposure:** dim indoor light with automatic exposure. Allow white paper and tag borders to clip a
  little (about 3.7 % of pixels were ≥ 250 here).
- **Near field:** with the design values, the lower edge of the frame is 23.4° below the axis at level
  pitch. So floor nearer than about 2.3 × the lens height ahead of the lens is out of view, and an upward
  tilt pushes that limit farther out. The lens height is not measured. Until M1.T7, do not count a tag
  near the bottom edge or very close to the car as reliably seen, and do not draw the car's own board in
  view unless the step 14 floor frames show it.
- **Upper bound:** the M1.T5 AprilTag spike, as planned, renders 800×600 PNG frames from an ideal pinhole
  camera. Treat its decode distances as an upper bound for the real camera, not as its range.

## 7. Open items

- Check by eye that the lens film is fully off and the lens is clean.
- M1.T6 step 12 (orientation with printed text, which settles the mirroring hint), step 13 (rate and
  freshness at UXGA, and whether `FB-OVF` drops happen with UXGA frames at 85–90 % of the buffer), and
  step 14 (floor frames and `picture-quality.md`).
- M1.T7 at UXGA: intrinsics, HFOV, VFOV and extrinsics (lens height, pitch, roll, yaw). A slanted-edge
  measurement on a printed target would replace the edge widths above with a proper sharpness figure.
- The plan still says SVGA, quality 12 (M1.T6 step 8, the `fx 693` example, and the M1.T5 spike's
  800×600). Updating it is Xiaohui's call.
- The 2.7 % sideways shift between the SVGA and UXGA views: a nudge during the reflash, or a readout
  window offset. It does not matter once M1.T7 calibrates at UXGA.
- Untried settings: sharpness, denoise, gain ceiling and manual exposure. Each changes the detector noise
  that M1.T8 measures.
- The cause of the `FB-OVF` drops logged at SVGA is not diagnosed.

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-06: compared the desk frames with the phone photo and wrote this note.
AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-06: rewrote the desk review from the UXGA frames, and updated this note to UXGA 1600×1200 quality 10 to match it.
