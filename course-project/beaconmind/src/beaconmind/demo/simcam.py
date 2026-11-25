"""What the car's camera would see in the simulator: the wall tags projected through configs/camera.json.

A drawing, not an image: the floor and the walls as two flat colours split at the line where the walls meet the
floor, and every tag's black square projected with beaconmind.camera_model (intrinsics, distortion and the measured
mount, the same projection the room simulator uses to decide what is in the picture: envs/kinsim_room.py
tag_in_picture). A tag the simulator reported as detected at this step is outlined in amber; a tag in the picture
but not reported (beyond the range limit, too oblique, or a random drop-out) stays grey. The desk is not drawn.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this view.
"""
import math

from PIL import Image, ImageDraw

from beaconmind import camera_model as cm

from . import draw as D

WALL = (222, 224, 228)
FLOOR = (196, 189, 176)


def to_base(pose, x, y):
    """Map-frame point -> base_link of the car at `pose` (as envs/kinsim_room.py to_base)."""
    th = math.radians(pose["theta_deg"])
    dx, dy = x - pose["x_m"], y - pose["y_m"]
    return dx * math.cos(th) + dy * math.sin(th), -dx * math.sin(th) + dy * math.cos(th)


def project(camera, p, margin=0.25):
    """Pixel of a base_link point, or None when it is behind the lens or more than `margin` (a fraction of the
    picture) outside it: the distortion polynomial is only valid inside the calibrated picture, and far outside it
    folds points back in."""
    q = camera.base_to_optical(p)
    if q[2] <= 0.05:
        return None
    xn, yn = q[0] / q[2], q[1] / q[2]
    lo_x, hi_x = (0 - camera.cx) / camera.fx, (camera.width - camera.cx) / camera.fx
    lo_y, hi_y = (0 - camera.cy) / camera.fy, (camera.height - camera.cy) / camera.fy
    mx, my = margin * (hi_x - lo_x), margin * (hi_y - lo_y)
    if not (lo_x - mx <= xn <= hi_x + mx and lo_y - my <= yn <= hi_y + my):
        return None
    try:
        return camera.project_optical(q)
    except ValueError:
        return None


def floor_line(camera, pose, walls, n_per_m=40):
    """Pixels (u, v) where the walls meet the floor, sorted by u (points behind the lens dropped)."""
    pts = []
    for (x0, y0), (x1, y1) in zip(walls, walls[1:] + walls[:1]):
        n = max(2, int(math.hypot(x1 - x0, y1 - y0) * n_per_m))
        for i in range(n + 1):
            bx, by = to_base(pose, x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n)
            if bx <= 0.05:
                continue
            uv = project(camera, (bx, by, 0.0))
            if uv:
                pts.append(uv)
    return sorted(pts)


def render(size, camera, pose, tags, walls, detected=(), caption=None):
    """The simulated picture at `pose` (map frame), scaled to `size` (the camera's aspect is kept)."""
    W, H = size
    s = min(W / float(camera.width), H / float(camera.height))
    ox, oy = (W - camera.width * s) / 2, (H - camera.height * s) / 2
    img = Image.new("RGB", size, (16, 18, 22))
    dr = ImageDraw.Draw(img)
    x0, y0, x1, y1 = ox, oy, ox + camera.width * s, oy + camera.height * s
    dr.rectangle([x0, y0, x1, y1], fill=WALL)
    line = floor_line(camera, pose, walls)
    if len(line) >= 2:
        poly = [(ox + u * s, oy + v * s) for u, v in line]
        poly = [(x0, poly[0][1])] + poly + [(x1, poly[-1][1]), (x1, y1), (x0, y1)]
        dr.polygon([(min(max(px, x0), x1), min(max(py, y0), y1)) for px, py in poly], fill=FLOOR)
    f = D.sans(max(12, int(18 * s / 0.38)), "bold")
    for t in tags:
        bx, by = to_base(pose, t["x_m"], t["y_m"])
        if bx <= 0.05:
            continue
        facing = t["normal_deg"] - pose["theta_deg"]
        corners = cm.square_corners_base((bx, by, t.get("z_m") or 0.23), facing, t.get("half_m") or 0.08)
        uv = [project(camera, c) for c in corners]
        if any(p is None for p in uv):
            continue
        if all(not camera.in_image(u, v) for u, v in uv):
            continue
        page = cm.square_corners_base((bx, by, t.get("z_m") or 0.23), facing, 1.4 * (t.get("half_m") or 0.08))
        puv = [project(camera, c) for c in page]
        if all(p is not None for p in puv):                 # the white paper around the black square
            dr.polygon([(ox + u * s, oy + v * s) for u, v in puv], fill=(250, 250, 250))
        pts = [(ox + u * s, oy + v * s) for u, v in uv]
        seen = t["tag"] in detected
        dr.polygon(pts, fill=(12, 12, 12), outline=D.SEEN_FILL if seen else (255, 255, 255), width=3 if seen else 1)
        side = max(p[0] for p in pts) - min(p[0] for p in pts)
        if seen or side >= 14:                       # far, tiny tags stay unlabelled
            label = "ID %s" % t["id"]
            lx = min(p[0] for p in pts)
            ly = min(p[1] for p in pts) - f.size - 6
            dr.text((lx, ly), label, font=f, fill=D.SEEN if seen else D.MUTED)
    # the frame outside the picture, then the caption
    img.paste((16, 18, 22), (0, 0, W, int(y0)))
    img.paste((16, 18, 22), (0, int(y1) + 1, W, H))
    if caption:
        fc = D.sans(16)
        dr.rectangle([0, H - 26, W, H], fill=(16, 18, 22))
        dr.text((8, H - 23), caption, font=fc, fill=(225, 225, 225))
    return img
