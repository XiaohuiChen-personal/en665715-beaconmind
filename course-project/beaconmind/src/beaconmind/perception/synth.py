"""Synthetic camera frames of wall tags, drawn through the calibrated camera model (lens distortion and mount angles
included), for the perception tests, tools/tag_pilot.py --selftest and the M1.T8 simulation estimate.

Every frame made here is SIMULATED. Nothing in this module reads the real camera.

How a frame is drawn. For every sub-pixel sample of the output picture the lens distortion is removed
(cv2.undistortPoints), the ray is turned into base_link with the camera's mount rotation and intersected with the tag's
plane; the hit point is looked up in the tag's texture (the marker with its white border). Samples are averaged per
pixel (a box filter over supersample x supersample samples), which stands for the pixel's light-collecting area.
The frame is therefore exact for the model in configs/camera.json; it is not made by warping with a homography, which
would leave the lens distortion out.

Tag frame: x to the viewer's right, y up, z out of the tag toward the viewer. A tag's pose is its centre in base_link
(z = height above the floor), the yaw of its outward normal in base_link, and optionally a lean (top tipped back, away
from the viewer, degrees) and a spin in its own plane (counter-clockwise as the viewer sees it, degrees).

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this renderer.
"""
import math

import cv2
import numpy as np

from beaconmind.perception.tags import marker_image

# What real bm_cam-0.2 XGA frames looked like on 2026-11-18 (room light at night, paper checkerboard about 1.03 m
# from the lens; sessions calibration-distance-check and calibration-extrinsics, six frames): printed black about
# 100 and white paper about 185 grey levels, edge blur about 0.75 px (10-90 % rise of a square's edge / 2.563),
# frame-to-frame noise after JPEG about 1.1 grey levels, JPEG luma table = the standard table scaled by 0.75
# (libjpeg quality 62.5), 4:2:2, about 26 kB per frame.
REAL_FRAME_2026_11_18 = {"black": 100.0, "white": 185.0, "wall": 150.0, "blur_sigma_px": 0.75, "noise_sigma": 2.0,
                         "jpeg_quality": 62}


def tag_axes(normal_yaw_deg, lean_deg=0.0, spin_deg=0.0):
    """3 x 3 array whose columns are the tag's x (viewer's right), y (up) and z (outward normal) axes in base_link."""
    p = math.radians(normal_yaw_deg)
    x = np.array([-math.sin(p), math.cos(p), 0.0])
    y = np.array([0.0, 0.0, 1.0])
    z = np.array([math.cos(p), math.sin(p), 0.0])
    if lean_deg:
        # top tipped back: rotate y and z about x so that y moves toward -z
        a = math.radians(lean_deg)
        y, z = math.cos(a) * y - math.sin(a) * z, math.sin(a) * y + math.cos(a) * z
    if spin_deg:
        # counter-clockwise for the viewer, who looks along -z: x moves toward y
        a = math.radians(spin_deg)
        x, y = math.cos(a) * x + math.sin(a) * y, -math.sin(a) * x + math.cos(a) * y
    return np.stack([x, y, z], axis=1)


def tag_at(tag_id, range_m, bearing_deg, height_m=0.23, incidence_deg=0.0, lean_deg=0.0, spin_deg=0.0,
           size_m=0.16, border_m=None):
    """A tag dict for render_scene: centre at (range, bearing) from the axle midpoint (contract C1), height_m above
    the floor, facing the axle midpoint and then turned by incidence_deg about the vertical (positive = its normal
    turned counter-clockwise seen from above)."""
    b = math.radians(bearing_deg)
    return {"id": int(tag_id), "x_m": range_m * math.cos(b), "y_m": range_m * math.sin(b), "z_m": float(height_m),
            "normal_yaw_deg": bearing_deg + 180.0 + incidence_deg, "lean_deg": float(lean_deg),
            "spin_deg": float(spin_deg), "size_m": float(size_m),
            "border_m": float(size_m) / 8.0 if border_m is None else float(border_m)}


def tag_corners_base(tag):
    """The black square's four corners in base_link, in the detector's order (top-left, top-right, bottom-right,
    bottom-left as the viewer sees the upright tag)."""
    axes = tag_axes(tag["normal_yaw_deg"], tag.get("lean_deg", 0.0), tag.get("spin_deg", 0.0))
    c = np.array([tag["x_m"], tag["y_m"], tag["z_m"]], dtype=float)
    h = tag.get("size_m", 0.16) / 2.0
    return [c + axes[:, 0] * sx * h + axes[:, 1] * sy * h for sx, sy in ((-1, 1), (1, 1), (1, -1), (-1, -1))]


def tag_corners_px(camera, tag):
    """Where the black square's corners fall in the picture (distortion included): 4 x 2 array of (u, v)."""
    return np.array([camera.project_base(tuple(p)) for p in tag_corners_base(tag)], dtype=float)


def _extents(tag):
    """(left, right, up, down): how far the tag's sheet reaches from the tag centre, metres, as the viewer sees it."""
    page = tag.get("page")
    if page is not None:
        image, mpp = np.asarray(page["image"]), float(page["m_per_px"])
        cx, cy = page["center_px"]
        return cx * mpp, (image.shape[1] - cx) * mpp, cy * mpp, (image.shape[0] - cy) * mpp
    half = tag.get("size_m", 0.16) / 2.0 + tag.get("border_m", tag.get("size_m", 0.16) / 8.0)
    return half, half, half, half


def _texture(tag, cell_px):
    """(texture, metres per texture pixel): the marker with its white border, or the caller's whole printed page,
    float32 grey levels 0..255."""
    size, border = tag.get("size_m", 0.16), tag.get("border_m", tag.get("size_m", 0.16) / 8.0)
    page = tag.get("page")
    if page is not None:
        image = np.asarray(page["image"])
        if image.ndim == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image.astype(np.float32), float(page["m_per_px"])
    marker = tag.get("marker")
    if marker is None:
        side = 8 * int(cell_px)
        marker = marker_image(tag["id"], side)
        pad = int(round(side * border / size))
        marker = cv2.copyMakeBorder(marker, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=255)
    else:
        # a caller's picture (tools/make_tags.py: black square plus a white border of 1/8 of its side)
        marker = np.asarray(marker)
        if marker.ndim == 3:
            marker = cv2.cvtColor(marker, cv2.COLOR_BGR2GRAY)
    total_m = size + 2.0 * border
    return marker.astype(np.float32), total_m / marker.shape[1]


def render_scene(camera, tags, wall=128.0, black=0.0, white=255.0, supersample=None, shade=None):
    """Grey uint8 frame (camera.height x camera.width) showing the tags on a uniform background.

    tags: dicts from tag_at() (or with the same keys); an optional "marker" key holds a ready picture of the tag with
    its white border (as tools/make_tags.py draws it); an optional "page" key holds a whole printed sheet instead:
    {"image": grey picture, "m_per_px": metres per picture pixel, "center_px": (column, row) of the tag's centre in
    it}. wall, black, white: grey levels of the background, the printed black and the paper. supersample: samples per pixel side (default: chosen per tag from its size in the picture, 3
    to 8). shade: optional (gain_left, gain_right) pair, a linear brightness ramp across the picture.
    Later tags are drawn over earlier ones."""
    height, width = camera.height, camera.width
    frame = np.full((height, width), float(wall), dtype=np.float32)
    k = np.array(camera.camera_matrix, dtype=np.float64)
    d = np.array(camera.dist, dtype=np.float64)
    rot = np.array(camera.rotation, dtype=np.float64)                 # base <- optical
    lens = np.array(camera.translation, dtype=np.float64)
    for tag in tags:
        axes = tag_axes(tag["normal_yaw_deg"], tag.get("lean_deg", 0.0), tag.get("spin_deg", 0.0))
        centre = np.array([tag["x_m"], tag["y_m"], tag["z_m"]], dtype=float)
        left, right, up, down = _extents(tag)
        outline = []
        for ax, by in ((-left, up), (right, up), (right, -down), (-left, -down), (0, up), (right, 0), (0, -down), (-left, 0)):
            p = centre + axes[:, 0] * ax + axes[:, 1] * by
            try:
                outline.append(camera.project_base(tuple(p)))
            except ValueError:
                outline = None
                break
        if outline is None:
            continue                                                  # behind the camera: not drawn
        outline = np.array(outline)
        u0, v0 = np.floor(outline.min(axis=0)).astype(int) - 2
        u1, v1 = np.ceil(outline.max(axis=0)).astype(int) + 2
        u0, v0, u1, v1 = max(u0, 0), max(v0, 0), min(u1, width - 1), min(v1, height - 1)
        if u1 < u0 or v1 < v0:
            continue                                                  # wholly outside the picture
        black_px = np.array([camera.project_base(tuple(q)) for q in tag_corners_base(tag)])
        side_px = float(np.mean([np.linalg.norm(black_px[i] - black_px[(i + 1) % 4]) for i in range(4)]))
        ss = int(supersample) if supersample else int(min(8, max(3, math.ceil(400.0 / max(side_px, 1.0)))))
        texture, m_per_px = _texture(tag, max(8, int(math.ceil(side_px * ss / 8.0))))
        texture = float(black) + texture * (float(white) - float(black)) / 255.0
        # sub-pixel sample positions: pixel i covers [i - 0.5, i + 0.5]
        offs = (np.arange(ss) + 0.5) / ss - 0.5
        us = (np.arange(u0, u1 + 1)[:, None] + offs[None, :]).reshape(-1)
        vs = (np.arange(v0, v1 + 1)[:, None] + offs[None, :]).reshape(-1)
        grid_u, grid_v = np.meshgrid(us, vs)
        pts = np.stack([grid_u.reshape(-1), grid_v.reshape(-1)], axis=1).reshape(-1, 1, 2)
        norm = cv2.undistortPoints(pts, k, d).reshape(-1, 2)
        rays = np.concatenate([norm, np.ones((norm.shape[0], 1))], axis=1) @ rot.T      # base_link directions
        denom = rays @ axes[:, 2]
        with np.errstate(divide="ignore", invalid="ignore"):
            s = ((centre - lens) @ axes[:, 2]) / denom
        hit = lens[None, :] + rays * s[:, None] - centre[None, :]
        a = hit @ axes[:, 0]
        b = hit @ axes[:, 1]
        col = (a + left) / m_per_px - 0.5
        row = (up - b) / m_per_px - 0.5
        inside = (s > 0) & (a >= -left) & (a <= right) & (b <= up) & (b >= -down) & np.isfinite(s)
        col = np.where(inside, col, -10.0).astype(np.float32).reshape(grid_u.shape)
        row = np.where(inside, row, -10.0).astype(np.float32).reshape(grid_u.shape)
        sampled = cv2.remap(texture, col, row, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        alpha = inside.reshape(grid_u.shape).astype(np.float32)
        h_out, w_out = v1 - v0 + 1, u1 - u0 + 1
        sampled = (sampled * alpha).reshape(h_out, ss, w_out, ss).mean(axis=(1, 3))
        alpha = alpha.reshape(h_out, ss, w_out, ss).mean(axis=(1, 3))
        region = frame[v0:v1 + 1, u0:u1 + 1]
        frame[v0:v1 + 1, u0:u1 + 1] = region * (1.0 - alpha) + sampled
    if shade is not None:
        ramp = np.linspace(float(shade[0]), float(shade[1]), width, dtype=np.float32)
        frame = frame * ramp[None, :]
    return np.clip(np.rint(frame), 0, 255).astype(np.uint8)


def degrade(frame, blur_sigma_px=0.0, noise_sigma=0.0, jpeg_quality=None, rng=None, motion_px=0.0, gamma=None):
    """Blur, sensor noise and JPEG, in the order a camera applies them. frame: grey uint8. blur_sigma_px: Gaussian
    blur (lens and focus); motion_px: length in pixels (made odd) of a horizontal box blur (the car still turning); noise_sigma: Gaussian
    noise in grey levels, added before compression; jpeg_quality: libjpeg quality (62 is closest to the camera's
    quality 12), None for no compression; gamma: when given, blur acts on linear light and the picture is encoded
    with this gamma afterwards (grey = 255 (linear)^(1/gamma)), as a camera's tone curve does; the black and white
    levels of the input are kept. Returns grey uint8."""
    out = frame.astype(np.float32)
    if gamma:
        out = 255.0 * np.power(out / 255.0, float(gamma))             # to linear light
    if blur_sigma_px and blur_sigma_px > 0:
        out = cv2.GaussianBlur(out, (0, 0), float(blur_sigma_px))
    if motion_px and motion_px > 1:
        n = int(round(motion_px)) | 1                                 # odd, so the blur does not shift the picture
        out = cv2.filter2D(out, -1, np.full((1, n), 1.0 / n, dtype=np.float32), borderType=cv2.BORDER_REPLICATE)
    if gamma:
        out = 255.0 * np.power(np.clip(out, 0, 255) / 255.0, 1.0 / float(gamma))
    if noise_sigma and noise_sigma > 0:
        rng = rng if rng is not None else np.random.default_rng(0)
        out = out + rng.normal(0.0, float(noise_sigma), out.shape).astype(np.float32)
    out = np.clip(np.rint(out), 0, 255).astype(np.uint8)
    if jpeg_quality is not None:
        ok, buf = cv2.imencode(".jpg", cv2.cvtColor(out, cv2.COLOR_GRAY2BGR), [cv2.IMWRITE_JPEG_QUALITY, int(jpeg_quality)])
        if not ok:
            raise RuntimeError("JPEG encoding failed")
        out = cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
    return out


def real_like(frame, rng=None, **changes):
    """degrade() with the values measured from real frames (REAL_FRAME_2026_11_18); keyword arguments override."""
    values = {"blur_sigma_px": REAL_FRAME_2026_11_18["blur_sigma_px"], "noise_sigma": REAL_FRAME_2026_11_18["noise_sigma"],
              "jpeg_quality": REAL_FRAME_2026_11_18["jpeg_quality"]}
    values.update(changes)
    return degrade(frame, rng=rng, **values)
