# ESP32-CAM picture quality: desk frames compared with a phone photo

Date: 2026-10-06. Task: M1.T6 (camera). This note answers two questions from Xiaohui. Is this the best
picture the ESP32-CAM will give? Why do the frames not show the ESP32 board or the area just in front of
the lens? It also says what the Isaac Sim camera must and must not assume. The same text is kept in
`course-project/evidence/M1/M1.T6/camera-quality.md` and `course-project/sim/isaac/REAL-CAMERA.md`.

This is not the M1.T6 step 14 picture-quality check. M1.T6 is not done. M1.T7 has not started. For this
note no frame was captured, nothing was flashed, and nothing was committed.

## Short answer

- **Best quality?** Not proven. These are the best frames the current firmware settings have produced,
  but a larger frame size, a lower JPEG quality number, manual exposure or sharpness, and brighter light
  have not been tried. The main defect is softness: a high-contrast edge takes about 6–11 pixels to go
  from dark to light. Compression adds well under 1 pixel of that, so changing the quality number will
  not fix it. A larger frame size is not proven to help either, because it would sample the same optical
  blur with more pixels.
- **Is the board in the frame?** No. No board edge, USB plug, ribbon or latch appears in any of the three
  frames. The board lies flat below the lens, and the lens looks level or slightly up, so the board is
  below the bottom edge of the picture. The old prediction that the board would cover the lower view does
  not hold for these frames. They do not prove the board stays out of view when the lens is tilted down
  at the floor; only the step 14 floor frames can show that.
- **Why is the near desk missing?** It is below the frame, not blurred away. The nearest things in the
  picture sit in its bottom band, and they are about as soft as the far wall.
- **For Isaac Sim:** do not match a phone photo. Render 800×600, blur it, add noise, compress it to a
  JPEG of about 30–35 KB for a similar scene, keep the near field out of view, and label the 60° HFOV as
  a design value until M1.T7 measures it.

## Evidence

| File | What it is | Key facts |
| --- | --- | --- |
| `course-project/evidence/M1/M1.T6/pictures/capture-1.jpg`, `capture-2.jpg`, `capture-3.jpg` | three frames from `GET http://192.168.4.24/capture`, about 1 s apart, car on a desk | 31,918 / 33,402 / 32,071 bytes; 800×600; each starts `ffd8` and ends `ffd9`; `X-BM-Seq` 1, 2, 3 |
| `course-project/evidence/M1/M1.T6/http-status.txt` | `/status` JSON fetched before those frames | `framesize` SVGA, 800×600, `quality` 12, `vflip` 0, `hmirror` 0, `psram` true, `frames` 0, `rssi_dbm` −58 |
| `course-project/evidence/M1/M1.T6/pictures/desk-review.md` | the capture record | HTTP codes, byte counts, sequence numbers; flash LED not used |
| `course-project/evidence/M1/M1.T6/serial-boot-dout-rst2.txt` | serial log after the DOUT bootloader write | `BM_CAM READY ip=192.168.4.24 rssi=-57 fw=bm_cam-0.1` (line 53); 94 of its 105 lines are `cam_hal: FB-OVF`, before and after that line |
| `course-project/evidence/M1/M1.T6/serial-boot-dout.txt`, `serial-boot-dout-more.txt` | shorter logs from the same image | 2 of 2 and 14 of 14 lines are `cam_hal: FB-OVF` |
| `course-project/evidence/M1/M1.T6/dout-write.txt` | esptool output | chip `ESP32-D0WD-V3 (revision v3.1)`: a plain ESP32, not an S2 or S3 |
| `course-project/evidence/M1/M1.T6/toolchain.txt` | builder image record | Arduino core `esp32:esp32@3.3.12` |
| `course-project/firmware/esp32cam/bm_cam/bm_cam.ino` | the running sketch, `bm_cam-0.1` | camera settings in `startCamera()`, lines 107–143 |
| Phone photo `IMG_7414` (Xiaohui, 2026-10-06), at `/Users/xiaohuichen/.cursor/projects/Users-xiaohuichen-Projects-EN-665-715/assets/IMG_7414-b5f651b6-1f37-4cd9-a814-f05c2dd1af40.jpg` | the desk scene from above and beside the car; a 1024×768 copy | not copied into the repo, because personal mail is legible in it (plan README L8) |
| Upstream `espressif/esp32-camera`, master commit `2bba0d1d57` (committed 2026-09-28, retrieved 2026-10-06): `driver/cam_hal.c`, `driver/sensor.c`, `sensors/ov3660.c`, `sensors/private_include/ov3660_settings.h`, `Kconfig` | the camera driver source | Upstream line numbers below refer to this commit. The core's `versions.txt` lists `espressif__esp32-camera:` with no version, so the exact revision built into core 3.3.12 is not confirmed. The core's `libespressif__esp32-camera.a` contains the same `cam_hal: FB-OVF` string and the `cam_verify_jpeg_eoi` function. |

Three more files, `pictures/current-1.jpg` to `current-3.jpg` (timestamped 21:25, 31,189–32,026 bytes),
appeared while this note was being written. I did not capture them. Their mean absolute luma difference
from `capture-1.jpg` is about 3.1, the same as between the three captures, so they show the same desk
view. They are not otherwise reviewed here.

## 1. What the camera was set to

| Setting | Value | Where it is set or checked |
| --- | --- | --- |
| Frame size | `FRAMESIZE_SVGA`, 800×600 | sketch line 129; all three files decode as 800×600 |
| JPEG quality | `jpeg_quality = 12` | sketch line 130 |
| What the number means | 0–63, lower = higher quality. It is the OV3660's own compression setting (the driver writes it to the sensor register `COMPRESSION_CTRL07`), not the 1–100 libjpeg scale. | core header `esp_camera.h` line 150 ("0-63 lower means higher quality"); upstream `ov3660.c` `set_quality`, lines 413–419 |
| Frame buffers | 2, in PSRAM, `CAMERA_GRAB_LATEST` | sketch lines 131–133 |
| `/capture` | takes one frame and hands it back to the driver unsent, then takes a fresh frame and serves it | sketch lines 72–93 |
| Clock | XCLK 20 MHz | sketch line 125 |
| Flip and mirror | `vflip` 0, `hmirror` 0 (compile-time defaults) | sketch lines 22–27 and 140–141 |
| Exposure, gain, white balance, sharpness, denoise | not set, so the driver and sensor defaults (automatic) apply | the sketch calls no other sensor setter. The OV3660 driver offers `set_sharpness`, `set_denoise`, `set_gainceiling`, `set_ae_level`, `set_aec_value` and `set_agc_gain` (upstream `ov3660.c` lines 1018–1051) |

Two cautions:

- `/status` writes `"framesize": "SVGA"` and `"quality": 12` as fixed text (sketch lines 63–64). It does
  not read them back from the sensor. The 800×600 decode confirms the frame size on its own. The JPEG
  tables (section 2) fit a moderate quality setting but do not prove the register value.
- The step 12 orientation check (printed text held in front of the lens) has not been done. The picture
  is right side up (desk at the bottom), but left–right mirroring is not verified. Section 4 gives a hint
  that it may be mirrored.

## 2. What the frames measure

Measured on the Mac with Pillow 11.3.0 and numpy 2.3.3, in an ad hoc script that was not saved as a tool.
The "10–90 % edge width" is the distance in pixels over which a dark-to-light edge rises from 10 % to
90 % of its step. A perfectly sharp edge measures about 1 px with this method.

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

The residual is each pixel minus its 7×7 neighbourhood mean.

Other facts from the files:

- **JPEG structure.** Baseline JFIF, two quantization tables, 4:2:2 chroma subsampling. Compared with the
  standard libjpeg luminance table, the luma table matches about libjpeg quality 62. That is my estimate,
  from the median ratio of the 64 entries. It is a moderate quality, not a very high one.
- **Frame-to-frame change.** Mean absolute luma difference 2.9–3.1. The three frames are the same view;
  the differences are noise and compression.
- **Colour.** The cabinet averages RGB (57, 53, 34) in the frames, against (47, 25, 8) for the same
  panelling in the phone photo. The ESP32's automatic white balance and exposure turn the warm-lit wood
  olive-brown and lift the shadows.
- **Compression control.** I encoded synthetic edges with Pillow at quality 62, 4:2:2, and measured them
  the same way. Compression changed an edge's 10–90 % width by at most 0.6 px, whether the edge sat on
  the 8-pixel block grid or off it. For example, an edge blurred with a Gaussian of σ = 3 px went from
  8.0 to 8.6 px, and a hard step from 0.8 to 1.0 px. One compression artifact is visible in the real
  frames: on the right-hand edge, the last part of the drop happens in a single pixel at x = 776, which is
  an 8-pixel block boundary. Compression changes the shape of an edge; it does not turn a sharp edge into
  a 6–11 px wide one.
- **Limits of these numbers.** Real edges are not ideal steps (the rail is a rounded moulding, the paper
  may cast a shadow), so the widths are upper bounds on the camera's own blur. The residuals include any
  fine wood or wall texture, so they are upper bounds on noise.

## 3. Is this the best this setup can do?

Each cause on its own:

**Lens focus and optics: the main limit.** The cleanest edges take about 6–8 px to rise at 800×600, and
a two-step edge about 11 px. The near objects (the paper, about 6 px; the cable loop, about 8 px) are no
softer than the far panelling (about 7–8 px). So the softness looks like a general property of the lens
and sensor path, not a near object out of focus. The focus distance of this lens is not known. Firmware
cannot change the focus: the driver's autofocus option is for the OV5640 only (upstream `Kconfig` lines
52–58, "depends on OV5640_SUPPORT"; the core's `sdkconfig` line 2785 has it unset). Three things were not
checked. First, whether the clear lens film is completely off: no red tab is visible in the phone photo,
but a clear film cannot be seen at that size. Second, whether the lens is smudged. Third, whether this
module's lens can be turned to refocus; I did not verify that. Turning a glued lens can damage the module
and would invalidate any calibration, so it is Xiaohui's decision, not a default step.

**Resolution choice: a design choice, not the ceiling.** SVGA was chosen in plan M1.T6 step 8: with the
60° HFOV design value, a 0.16 m tag at 2.0 m spans about 55 px, and frames stay small for Wi-Fi. The
driver allows the OV3660 up to QXGA, 2048×1536 (upstream `sensor.c` line 8; `ov3660.c` `set_framesize`
clamps to QXGA at lines 315–318). At SVGA the driver puts the sensor in 2×2 binning, because binning is
switched on whenever the width and height are at most half of the 2048×1536 maximum (`ov3660.c` line 326;
`ov3660_settings.h` line 11). The sensor then scales its 1024×768 binned output down to 800×600. XGA
(1024×768) is also binned; UXGA (1600×1200) and QXGA are read without binning. No size other than SVGA
has been tried on this board, so these frames do not prove the sensor's limit. But if the lens is the
limit, a bigger frame shows the same blur over more pixels: edges get wider in pixels, not crisper. Plan
M1.T6 step 13 says a change of frame size or quality would redo M1.T7, so either needs Xiaohui's approval.

**JPEG quality number: not the cause of the softness.** 12 is on the better side of the 0–63 scale, and
the tables it produced are about libjpeg quality 62. A lower number, such as 10 or 8, would give finer
quantization, fewer 8×8 block artifacts and larger files. It has not been tried on this board. The control
in section 2 shows compression adds at most about 0.6 px to an edge, so a quality-number change cannot
fix 6–11 px of softness. There is room for larger frames: the sketch leaves `jpeg_buffer_size` at 0, so in
JPEG mode each frame buffer is width × height / 5 = 96,000 bytes at SVGA (upstream `cam_hal.c` lines
586–596; `CONFIG_CAMERA_JPEG_MODE_FRAME_SIZE_AUTO=y` at the core's `sdkconfig` line 2809). The frames are
about 32 KB.

**Exposure: acceptable, and it adds grain.** The scene was a dim evening desk under warm light, on
automatic exposure. Nothing is clipped to black. The white paper is clipped in places (about 4 % of all
pixels are ≥ 250). The dark wood shows grain, worst in the blue channel (section 2). Exposure is not why
the edges are soft. More light would reduce the grain. Manual exposure, gain ceiling, sharpness and
denoise have not been tried.

**`FB-OVF` drops: they cost frames, not picture quality.** On a plain ESP32 (this chip is an
ESP32-D0WD-V3) the driver's DMA-to-PSRAM mode is off; it exists only on the S2 and S3 (upstream
`cam_hal.c` lines 576–580). So every frame is copied from small DMA buffers into the frame buffer.
`cam_hal: FB-OVF` is printed when the bytes for one frame would overflow that 96,000-byte buffer
(`cam_hal.c` lines 296–302 and 373–378). That frame is cut short. The driver then rejects any frame with
no JPEG end marker (`FF D9`) and waits for the next one (`cam_hal.c` lines 740–776, in `cam_take`). So a
served frame is a complete JPEG, as all three are. The drops cost frame rate and freshness instead. Served
frames are about 32 KB, a third of the buffer, so normal frame size does not explain the overflow. The
cause has not been diagnosed, and no test was run. The logs have no timestamps, so a drop rate cannot be
computed. Serial was not recorded during the desk captures, so whether drops happened then is unknown. The
step 13 rate and freshness probes have not run.

**Verdict.** These are the best frames this firmware has produced at its current settings, on a dim desk.
They are not shown to be the camera's best. The main defect, softness of about 6–11 px per edge at
800×600, comes from the optics. Neither a quality-number change nor a larger frame size is expected to
remove it.

## 4. Why the board and the near foreground are missing

**The scene, from the phone photo.** The camera module stands upright, fixed to a grey Technic angle beam
at the battery-holder end of the car. Its lens points toward the USB-C end (left in the photo), roughly
level. The ESP32-CAM board lies flat under and in front of the lens, and the white USB-C cable goes into
the base board. The caster is under the USB-C end. A white power bank lies on the desk beside the car.
White mail and a lined pad with a red rule lie on the desk near the car, on the phone's side. Farther
away, at the back of the desk, are a coiled white cable, a black pen, a router, a laptop on a stand, and
dark wood panelling.

**What the lens recorded.** The panelling fills most of every frame. Its top rail and the pale wall above
it are at the top, so the lens looks level or slightly upward. The desk shows only as a band at the
bottom of the frame, from about row 490 of 600 downward. In that band are a soft white loop with a dark
bar under it at the lower left, most likely the coiled cable and the black pen, and a bright, soft white
shape with a faint red streak at the lower right, probably paper. No text is legible, so I cannot say
which sheet it is.

**A hint that the image is mirrored.** The cable loop and the pen are at the back of the desk, beside the
panelling. The papers are on the near side of the car. For a lens that points toward the photo's left,
the image's left should be toward the papers and its right toward the back of the desk. The frames show
the opposite. The panelling rails also slope down to the right. That is what a left–right mirrored image
would show. It is a hint from rough scene geometry, not a check; step 12's printed-text test decides it.
If the image is mirrored, every bearing has the wrong sign, and tags may fail to decode.

**The board is not in the frame.** No board edge, USB plug, ribbon or latch appears anywhere, including
the bottom rows. The board is below the lens and the lens looks level or up, so the board falls below the
bottom edge of the picture. This is geometry, not something blocking the lens.
`reference/hardware/esp32cam-notes.md` §7 predicted that "the lower part of a forward view will include
the board's own front edge and the USB plug". These frames do not show that for this mount at this angle.
They also do not prove the opposite for step 14: tilting the lens down to see the floor may bring the
board's front edge into the bottom of the frame. Only the step 14 floor frames can settle it.

**The near foreground is below the frame, not blurred out.** The caster, the near end of the power bank,
the papers beside the car and the first part of the desk ahead all lie below the lowest direction the
lens can see. The phone sees them because it was held above and beside the car, looking down. The nearest
objects that are in the frame are about as soft as the far wall, so blur is not what removes the near
field. The lens height, pitch and roll have not been measured (M1.T6 step 3 level report; M1.T7
extrinsics). If the design vertical field of view of about 46.8° held (from the 60° HFOV at 4:3), the
bottom edge of the frame would be about 23° below the lens axis, and anything seen more steeply than that
below the axis would be out of view. That angle comes from a design value, not a measurement.

**Why the phone photo looks so much better.** It was taken from a different place, higher and beside the
car, with autofocus on the car, by a much larger camera. The copy here is 1024×768. Even the phone photo
is not sharp everywhere: its background panelling is blurred. It shows the scene; it is not a target for
the ESP32 frames.

## 5. Step 14 (read only; the plan was not edited)

This desk set does not meet the M1.T6 step 14 pass rule, and it is not a step 14 set at all:

- The car was on a desk, not on the floor, and the lower part of the view is not the floor ahead.
- The frames were about 1 s apart; the rule asks for at least 3 s. `X-BM-Seq` does increase (1, 2, 3).
- The files are `capture-*.jpg`, not `forward-*.jpg` with `.hdr` files, `led-off.txt` and
  `picture-quality.md`.
- The board is absent and no frame is a solid black or white clip. Those parts of the rule would be met.
- The rule needs "at least one frame shows a sharp high-contrast edge". The crispest edges here take about
  6–8 px to rise; I would call that soft, not sharp. The rule gives no number, so this is a judgement for
  the step 14 review.

M1.T6 stays not done. M1.T7 must not start from these frames.

## 6. What Isaac Sim must not assume, and what it should do

The Isaac camera stands in for this camera (plan README C12: `/camera/image_raw` comes from the Isaac
camera in the twin, and from `bm_camera_bridge` decoding the ESP32 JPEG on the car). If the sim image is
much cleaner than the real one, tags will decode farther and more reliably in the sim than on the car, and
sim results will be too optimistic.

**Must not assume:**

1. Phone-photo sharpness, or the crisp edges of an ideal pinhole render.
2. The near field a person sees. The car's own board, the caster and the floor just ahead are not in the
   real picture at this mount.
3. Clean, decodable tags at the bottom of the frame or very close to the car.
4. A noise-free 800×600 image, or a lossless PNG. The real frames are compressed JPEGs with grain.
5. A measured field of view. HFOV 60° is a design value (`course-project/AGENT-DESIGN.md` D3, "Camera
   HFOV | 60°"). M1.T7 has not run.
6. A steady frame rate with every frame fresh. `FB-OVF` drops are logged, and step 13 has not measured
   rate or freshness.
7. Correct left–right orientation of the real image. Step 12's printed-text check has not been done.

**Should do, until M1.T7 and step 14 give measured values:**

- **Resolution:** 800×600, 4:3. Use fx = fy until calibration says otherwise.
- **Field of view:** HFOV 60° and VFOV about 46.8° (2·atan(0.75·tan 30°)), both labelled as design values
  in every sim result. Replace them with `course-project/configs/camera.json` after M1.T7.
- **Softness:** blur the render so that a high-contrast edge rises from 10 % to 90 % over about 6–8 px at
  800×600, and up to about 11 px at worst. A Gaussian blur with σ ≈ 2.5–3 px gives 6–8 px; σ ≈ 4 px gives
  about 10 px. Use the same blur at every distance unless later measurements show otherwise.
- **Noise:** add sensor noise before compression. Tune it so that, after compression, a flat dark patch
  (mean luma about 45) has a standard deviation of about 2–3 levels in red and green and about 5–6 in
  blue, and a bright patch (mean about 150) about 3 levels in each channel.
- **JPEG:** encode each sim frame as a baseline JPEG with 4:2:2 chroma at roughly libjpeg quality 60. Real
  frames of this dim indoor scene were 31–34 KB. A sim frame of a similar scene that is several times that
  size carries detail the real camera does not deliver. Give the tag detector the decoded JPEG, not the
  raw render.
- **Exposure:** dim indoor light with automatic exposure. Allow white paper and tag borders to clip a
  little (about 4 % of pixels were ≥ 250 here).
- **Near field:** take the camera's height and pitch from M1.T7. Until then, do not count a tag near the
  bottom edge or very close to the car as reliably seen, and do not draw the car's own board in view
  unless the step 14 floor frames show it.
- **Upper bound:** the M1.T5 AprilTag spike, as planned, renders PNG frames from an ideal pinhole camera.
  Treat its decode distances as an upper bound for the real camera, not as its range.

## 7. Open items

- Check by eye that the lens film is fully off and the lens is clean.
- M1.T6 step 12 (orientation with printed text, which settles the mirroring hint), step 13 (rate and
  freshness, and whether the `FB-OVF` drops matter), and step 14 (floor frames and `picture-quality.md`).
- M1.T7: intrinsics, HFOV, VFOV and extrinsics. A slanted-edge measurement on a printed target would
  replace the edge widths above with a proper sharpness figure.
- Untried settings: a lower quality number, a larger frame size, sharpness, denoise and manual exposure.
  Each needs Xiaohui's approval first, because a frame-size or quality change redoes M1.T7 and any of them
  changes the detector noise that M1.T8 measures.
- The cause of `FB-OVF` is not diagnosed.

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-06: compared the desk frames with the phone photo and wrote this note.
