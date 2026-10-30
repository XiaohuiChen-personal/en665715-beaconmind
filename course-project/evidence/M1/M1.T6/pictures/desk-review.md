# Desk view at UXGA: what the ESP32-CAM lens records

2026-10-06. The firmware is settled at UXGA 1600×1200, JPEG quality 10. This note says, from the pixels,
where the lens points and what it sees, so the Isaac Sim camera can copy the real camera rather than a
phone photo. The car was on a desk, not on the floor. These frames are not an M1.T6 step 14 set, step 14
is not a pass, M1.T6 is not done, and M1.T7 has not started. For this note nothing was flashed, no
frame was captured, and nothing was committed.

## Files

| File | Bytes | Decoded size | Start / end | Saved on the Spark (CDT) |
| --- | ---: | --- | --- | --- |
| `uxga-1.jpg` | 327,546 | 1600×1200 | `ffd8` / `ffd9` | 21:48:07 |
| `uxga-2.jpg` | 331,816 | 1600×1200 | `ffd8` / `ffd9` | 21:48:12 |
| `uxga-3.jpg` | 343,838 | 1600×1200 | `ffd8` / `ffd9` | 21:48:18 |

- **Camera state.** `GET /status`, saved on the Spark as `/tmp/bm-status-body.txt` at 21:47:36:
  `fw` `bm_cam-0.1`, `framesize` `UXGA`, 1600×1200, `quality` 10, `vflip` 0, `hmirror` 0, `rssi_dbm`
  −69, `frames` 0. This firmware reads these values from the driver's sensor status (`bm_cam.ino`
  `sendStatus()`), not from fixed text. The HTTP codes and `X-BM-Seq` headers of the three captures
  were not saved, so they are not recorded here.
- **Copies.** The same three files, with the same SHA-256, are on the Spark and on the Mac (this
  folder and `/Users/xiaohuichen/Desktop/beaconmind-camera/`). The earlier SVGA files
  (`capture-1..3.jpg`, `current-1..3.jpg`) were deleted from all three places on 2026-10-06 at
  Xiaohui's request.
- **Phone photo.** `IMG_7414` (Xiaohui, 2026-10-06), a 1024×768 copy at
  `/Users/xiaohuichen/.cursor/projects/Users-xiaohuichen-Projects-EN-665-715/assets/IMG_7414-b5f651b6-1f37-4cd9-a814-f05c2dd1af40.jpg`.
  It is not copied into the repo, because personal mail is legible in it (plan README L8).
- **Size.** About 330 KB per frame (320–336 KiB). That is about ten times the earlier SVGA frames
  (31–34 KB) for four times the pixels. Each file is a baseline JFIF with two quantization tables and
  4:2:2 chroma. Its luma table is closest to libjpeg quality 69 (my estimate; the SVGA quality-12
  frames were about 62).
- **Buffer margin (not tested).** `camera-quality.md` gives the automatic JPEG buffer as width × height
  / 5. At UXGA that is 384,000 bytes, so these frames fill 85–90 % of it. A busier or brighter scene
  could overflow (`cam_hal: FB-OVF`) and drop frames. `serial-boot-uxga.txt` is empty, so whether drops
  happen at UXGA is unknown.

## 1. Where the lens points, relative to the chassis

**Mount, from the phone photo.** The camera module stands upright against the grey Technic angle
beam, at the battery-holder end of the ESP32-CAM board. The board lies flat on top of the caster end
of the clear chassis, with its USB-C plug at the far end. The black lens barrel lies roughly horizontal and points
over the board toward the USB-C plug and the caster. That is **forward**, the project's +x
(`AGENT-DESIGN.md` D3: "camera/caster end = front"). The lens sits just above the board's top surface,
and the board runs on ahead of and below it. Any sideways offset from the car's long axis looks small
in the photo but is not measured.

**Aim, from the UXGA frames: forward and about level, possibly tipped a little up, not down.**

- A vertical surface fills about the top four-fifths of the frame: dark wood panelling, with its top
  rail and the pale wall above it at the top right. A lens tipped down would show more desk and less
  wall.
- The desk shows only as a band along the bottom. Its upper edge is at about row 970 near x = 900,
  about 1,000 at x = 1,200, about 1,070 at x = 1,400 and about 1,100 at the right edge. On the left, a
  white coil hides it; the desk shows below the coil from about row 1,045. So the desk takes the lowest
  8–20 % of the frame height.
- Nothing belonging to the car appears in any frame. The board lies ahead of and below the lens, so its
  front edge would enter the bottom rows first if the lens tipped down. It is not there.
- No large roll: the panel stiles stand within about 4° of the image vertical in every frame. My
  frame-by-frame fits of the stiles disagree by a few degrees, so they measure neither roll nor pitch.
- The wall's two horizontal mouldings (the rail's top edge, at 20.7° in the image, and the groove along
  the panel tops, at 18.2°) meet far to the right, near row 1,070–1,100. That would put the horizon
  below the centre row, which means an upward tilt. The two lines are almost parallel, so this is only
  a weak hint, and no angle is given.

The lens height, pitch, roll and yaw are not measured. They come from the M1.T7 extrinsics.

## 2. What is in the frame, and what is not

**In the frame:**

- Dark wood panelling over most of the frame: two raised panels, the stile between them (near x 970–1,060),
  a stile on the left (near x 270) and the right panel's right edge (near x 1,430).
- The panelling's top rail across the top, sloping down to the right at about 20° in the image, and a
  pale cream wall above it at the top right.
- At the far right edge, a dark vertical frame with a light ledge. I cannot identify it.
- Along the bottom, the reddish-brown desk top. On it, at the lower left, are a white coiled object
  with a curved loop, a grey-brown textured object to its right, and a black rod lying across the lower
  left. At the lower centre and right is white paper with a crumpled top edge and a faint red line, cut
  off by the bottom edge of the frame. The coil and the rod are probably the white cable coil and the
  black pen that the phone photo shows at the back of the desk, and the paper is probably the lined pad
  or the mail on it. None of these is legible, so none is confirmed.

**Not in the frame:**

- The ESP32-CAM board, its USB-C plug and cable bend, the ribbon, the Technic beam, the clear chassis
  plate and the caster. None appears in any of the three frames.
- The paper directly under and beside the car, including the pad's label next to the caster. The only
  paper in view is a sheet that enters at the bottom edge, farther away.
- The desk right in front of the car. The phone sees it because it looks down from above and beside the
  car. Because the board's front edge is out of view, the desk under the car's nose, which lies lower
  still, is out of view too.
- The white power bank beside the car cannot be picked out in the frames.

## 3. Softness and exposure compared with `camera-quality.md`

I measured all six files with one ad hoc script before the SVGA files were deleted (Python 3.13.7,
Pillow 11.3.0, numpy 2.3.3; not saved as a tool). An edge width is the vertical distance over which a
dark-to-light edge rises from 10 % to 90 %. It is taken from an edge profile averaged over 100–240
columns. This method, and the patches used, differ from `camera-quality.md`, so its SVGA numbers differ
a little from the ones below. Compare within this table.

| Measure | SVGA q12 (`capture-1..3`) | UXGA q10 (`uxga-1..3`) | UXGA, in 800-wide pixels |
| --- | --- | --- | --- |
| Edge: rail top against the pale wall (far) | 6.3–6.8 px | 9.8–10.3 px | 4.9–5.1 px |
| Edge: top of the white paper, lower right | 7.3–7.5 px | 13.3 px | 6.6 px |
| Edge: top of the white coil, lower left | 8.0 px | 16.0–16.5 px | 8.0–8.3 px |
| Mean luma (0–255) | 76.7–77.7 | 74.8–75.3 | |
| 1st / 50th / 99th percentile luma | 21–23 / 61–62 / 254 | 15–16 / 60–61 / 254 | |
| Pixels ≥ 250 / ≤ 5 | 3.8–3.9 % / ≤ 0.01 % | 3.7 % / 0.09–0.12 % | |
| Dark wood patch: residual R / G / B (pixel minus 7×7 mean) | 2.3–2.5 / 2.4–2.7 / 4.8–5.8 | 10.6–12.2 / 10.7–12.3 / 12.0–13.6 | 8.2–9.2 / 8.4–9.7 / 11.3–12.4 |
| Pale wall patch: residual R / G / B | 0.6–0.7 / 0.5–0.7 / 1.0–1.2 | 1.3–1.4 / 1.3 / 1.8–2.4 | 1.6–1.7 / 1.6–1.7 / 2.4–3.1 |
| Frame-to-frame mean absolute luma difference | 2.9–3.1 (`camera-quality.md`) | 10.6–11.0 | |
| Dark wood patch mean RGB | (57, 53, 32) | (56, 47–48, 34–37) | |

What this means in plain language:

- **Softness: still soft, a little crisper than at SVGA.** The cleanest edge, the far rail against the
  pale wall, takes about 10 px to rise at 1600 wide. A sharp edge would take 1–2 px. As a share of the
  frame width, that edge is about a quarter narrower than at SVGA (5 against 6.5 px at 800-wide scale),
  so the SVGA binning and downscale added some blur. The near edges (the coil and the paper) rise over
  13–16 px, which is softer than the far rail. At SVGA they looked about as soft as the far wall.
  So `camera-quality.md`'s statement that near objects are no softer than the far panelling does not
  carry over to UXGA. The cause may be focus, or the rounded coil and curled paper; it is not settled.
- **Exposure: same as before.** Dim, warm evening light on automatic exposure. The white paper clips in
  places (about 3.7 % of pixels are ≥ 250), and almost nothing clips to black. The wood comes out
  olive-brown rather than the phone photo's red-brown.
- **Grain: different, much heavier.** In the dark wood, per-pixel noise is four to five times the SVGA
  level, and still about three and a half times after halving the resolution. It shows as coloured
  speckle across the panelling, and it is why consecutive frames differ by about 11 levels instead of
  about 3. At SVGA the sensor's 2×2 binning and downscale averaged it away.

**The UXGA view has the same field of view as SVGA, shifted sideways.** Nine features were matched
between `capture-1.jpg` and `uxga-1.jpg` (both blurred, at 800-wide scale). The best fit is a scale of
1.004 and a rotation of 0.2°, with a shift of −21.7 px across and −1.1 px down (about −43 px at
UXGA), leaving a residual of 2.4 px rms. So the field of view matches SVGA's to within about half a
percent, and the view moved sideways by about 2.7 % of the frame width (about 1.8° under the 60° design
HFOV). I cannot tell whether the car or camera was nudged during the reflash or whether the sensor reads
a slightly offset window at UXGA. The UXGA frames are the reference from now on.

## 4. Simulator camera

**Copy:**

- **Pose.** Lens on the car, just above the ESP32-CAM board at the caster end, axis along +x (forward),
  about level, possibly tipped a little up, never down, with no roll. Take x, z, pitch and yaw from M1.T7;
  until then, do not put numbers on them.
- **View.** Facing a wall like this one, a vertical surface fills most of the frame, the floor shows only
  as a band along the bottom, and no part of the car is ever in view.
- **Image.** 1600×1200 (4:3). Encode a baseline JPEG with 4:2:2 chroma at about libjpeg quality 69,
  about 330 KB for a dim indoor scene like this one, and give the tag detector the decoded JPEG.
- **Field of view.** HFOV 60° and VFOV about 46.8°, so fx = fy ≈ 1386 px at 1600 wide. These are
  design values (`AGENT-DESIGN.md` D3); label them as such in every sim result until M1.T7's
  `camera.json` replaces them.
- **Softness.** Blur so that a far high-contrast edge rises over about 10 px at 1600 wide (a Gaussian
  with σ ≈ 4 px), and allow 13–16 px (σ ≈ 5–6.5 px) for near objects.
- **Noise and exposure.** Heavy grain. After compression, a flat dark patch (mean luma about 49) should
  have a per-pixel residual of about 11–12 levels in red and green and 12–14 in blue, and a bright
  patch (mean about 166) about 1.3 in red and green and about 2 in blue. Use dim indoor light on
  automatic exposure, and let white paper and tag borders clip a little.

**Do not copy:**

- **Phone sharpness**, or the clean edges of an ideal pinhole render.
- **The near field the eye sees.** The phone looks down from above and beside the car. The ESP32 lens
  sits just above the board and sees none of the car and none of the desk in front of its nose. Do not
  render the board, the plug, the caster or the floor just ahead of the car into view, and do not count
  a tag at the very bottom edge, or very close to the car, as seen. With the design values (lower edge
  23.4° below the axis at level pitch), floor nearer than about 2.3 × the lens height ahead of the lens
  is out of view, and an upward tilt pushes that limit farther out. The lens height is not measured.
- **An unmeasured 60° field of view stated as fact.** It is a design value until M1.T7.
- **A known left–right orientation.** The step 12 printed-text check has not been done. The mirroring
  hint in `camera-quality.md` §4 is still open.

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-06: rewrote the desk review from the UXGA frames.
