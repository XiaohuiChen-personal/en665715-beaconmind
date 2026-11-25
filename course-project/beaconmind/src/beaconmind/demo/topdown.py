"""The room seen from above: walls, desk, driving area, the tags, the car's true and believed pose, the paths, the
camera's field of view and the agent's beacon map (Pillow; drawn at `ss` times the size, then scaled down, so lines
are smooth).

Frames: everything arrives in the episode's map frame (start pose at the origin, x forward, y left, angles
counter-clockwise). `view_rot_deg` rotates the picture on the screen (a rotation, never a mirror, so a left turn is
counter-clockwise on screen); 180 puts the desk wall at the bottom with the room as Xiaohui's survey sketch draws it
"seen from above" (evidence/M3/M3.T10/room-survey.md) for the start pose (2.50, 1.50, 90 deg).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote this renderer.
"""
import math

from PIL import Image, ImageChops, ImageDraw

from . import draw as D


def convex_hull(points):
    pts = sorted(set((float(x), float(y)) for x, y in points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


class TopDown:
    def __init__(self, scene, tags, size, footprint=None, lens_x_m=0.12, hfov_deg=None, range_m=None,
                 view_rot_deg=180.0, margin_px=58, ss=2, labels=None, scale_bar="left"):
        self.scene, self.tags, self.size, self.ss = scene, tags, tuple(size), ss
        self.W, self.H = self.size[0] * ss, self.size[1] * ss
        self.rot = math.radians(view_rot_deg)
        self.footprint = convex_hull(footprint) if footprint else [(0.178, 0.0), (0.12, 0.075), (-0.148, 0.075),
                                                                    (-0.148, -0.075), (0.12, -0.075)]
        self.lens_x, self.hfov, self.range = lens_x_m, hfov_deg, range_m
        self.labels = labels or {}
        self.scale_bar = scale_bar
        walls = scene["walls_polygon"]
        uv = [self._rot(x, y) for x, y in walls]
        u0, u1 = min(u for u, _ in uv), max(u for u, _ in uv)
        v0, v1 = min(v for _, v in uv), max(v for _, v in uv)
        m = margin_px * ss
        self.scale = min((self.W - 2 * m) / (u1 - u0), (self.H - 2 * m) / (v1 - v0))
        self.ox = (self.W - self.scale * (u1 - u0)) / 2 - self.scale * u0
        self.oy = (self.H - self.scale * (v1 - v0)) / 2 + self.scale * v1
        self._bg = None
        self._mask = None

    # -------------------------------------------------------------- geometry
    def _rot(self, x, y):
        c, s = math.cos(self.rot), math.sin(self.rot)
        return c * x - s * y, s * x + c * y

    def px(self, x, y):
        """Map-frame metres -> pixel at the supersampled size."""
        u, v = self._rot(x, y)
        return self.ox + self.scale * u, self.oy - self.scale * v

    def px_out(self, x, y):
        """Map-frame metres -> pixel in the output image."""
        a, b = self.px(x, y)
        return a / self.ss, b / self.ss

    def pose_poly(self, pose, pts):
        th = math.radians(pose["theta_deg"])
        c, s = math.cos(th), math.sin(th)
        return [self.px(pose["x_m"] + c * x - s * y, pose["y_m"] + s * x + c * y) for x, y in pts]

    # -------------------------------------------------------------- static layer
    def background(self):
        if self._bg is not None:
            return self._bg
        ss = self.ss
        img = Image.new("RGB", (self.W, self.H), D.BG)
        dr = ImageDraw.Draw(img)
        walls = [self.px(x, y) for x, y in self.scene["walls_polygon"]]
        dr.polygon(walls, fill=D.FLOOR)
        drive = self.scene.get("drive_polygon")
        if drive:
            dp = [self.px(x, y) for x, y in drive]
            dr.polygon(dp, fill=D.DRIVE)
            self._dashed_poly(dr, dp, D.FAINT, 2 * ss, 10 * ss, 8 * ss)
        for ob in self.scene.get("obstacles") or []:
            poly = [self.px(x, y) for x, y in ob["polygon"]]
            dr.polygon(poly, fill=D.DESK, outline=D.MUTED)
            cx = sum(p[0] for p in poly) / len(poly)
            cy = sum(p[1] for p in poly) / len(poly)
            f = D.sans(17 * ss)
            name = ob.get("name", "")
            dr.text((cx - D.text_w(dr, name, f) / 2, cy - 11 * ss), name, font=f, fill=D.MUTED)
        dr.line(walls + [walls[0]], fill=D.WALL, width=5 * ss, joint="curve")
        # scale bar: 1 m
        x0, y0 = 22 * ss, self.H - 24 * ss
        if self.scale_bar == "right":
            x0 = self.W - self.scale - 80 * ss
        dr.line([(x0, y0), (x0 + self.scale, y0)], fill=D.INK, width=3 * ss)
        for xx in (x0, x0 + self.scale):
            dr.line([(xx, y0 - 7 * ss), (xx, y0 + 7 * ss)], fill=D.INK, width=3 * ss)
        f = D.sans(16 * ss)
        dr.text((x0 + self.scale + 10 * ss, y0 - 11 * ss), "1 m", font=f, fill=D.INK)
        for text, (x, y) in self.labels.items():
            p = self.px(x, y)
            dr.text((p[0] - D.text_w(dr, text, f) / 2, p[1] - 10 * ss), text, font=f, fill=D.MUTED)
        self._bg = img
        mask = Image.new("L", (self.W, self.H), 0)
        ImageDraw.Draw(mask).polygon(walls, fill=255)
        self._mask = mask
        return img

    @staticmethod
    def _dashed(dr, a, b, fill, width, dash, gap):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L == 0:
            return
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        d = 0.0
        while d < L:
            e = min(L, d + dash)
            dr.line([(a[0] + ux * d, a[1] + uy * d), (a[0] + ux * e, a[1] + uy * e)], fill=fill, width=width)
            d = e + gap

    def _dashed_poly(self, dr, pts, fill, width, dash, gap):
        for a, b in zip(pts, pts[1:] + pts[:1]):
            self._dashed(dr, a, b, fill, width, dash, gap)

    # -------------------------------------------------------------- one frame
    def render(self, truth=None, belief=None, map_entries=(), mapped=(), detected=(), trail_truth=(),
               trail_belief=(), show_fov=True, start=None):
        ss = self.ss
        img = self.background().copy()
        dr = ImageDraw.Draw(img)
        cam_pose = truth
        if show_fov and cam_pose and self.hfov and self.range:
            self._fov(img, cam_pose)
            dr = ImageDraw.Draw(img)
        if cam_pose:
            cx, cy = self._lens(cam_pose)
            for t in self.tags:
                if t["tag"] in detected:
                    dr.line([(cx, cy), self.px(t["x_m"], t["y_m"])], fill=D.SEEN, width=2 * ss)
        # paths
        if len(trail_truth) > 1:
            dr.line([self.px(p["x_m"], p["y_m"]) for p in trail_truth], fill=D.TRUTH, width=3 * ss, joint="curve")
        if len(trail_belief) > 1:
            pts = [self.px(p["x_m"], p["y_m"]) for p in trail_belief]
            for a, b in zip(pts, pts[1:]):
                self._dashed(dr, a, b, D.BELIEF, 3 * ss, 7 * ss, 5 * ss)
        # tags
        side = 9 * ss
        f_id = D.sans(17 * ss, "bold")
        for t in self.tags:
            x, y = self.px(t["x_m"], t["y_m"])
            if t["tag"] in detected:
                dr.ellipse([x - 17 * ss, y - 17 * ss, x + 17 * ss, y + 17 * ss], fill=D.SEEN_FILL, outline=D.SEEN,
                           width=2 * ss)
            fill = D.MAPPED if t["tag"] in mapped else D.UNMAPPED
            edge = D.MAPPED if t["tag"] in mapped else D.UNMAPPED_EDGE
            dr.rectangle([x - side, y - side, x + side, y + side], fill=fill, outline=edge, width=2 * ss)
            # the label goes outside the wall: against the tag's normal (which points into the room)
            a = math.radians(t.get("normal_deg") or 0.0)
            ox, oy = self.px(t["x_m"] - 0.21 * math.cos(a), t["y_m"] - 0.21 * math.sin(a))
            label = str(t["id"])
            w = D.text_w(dr, label, f_id)
            dr.text((ox - w / 2, oy - 11 * ss), label, font=f_id,
                    fill=D.MAPPED if t["tag"] in mapped else D.MUTED)
        # the agent's map
        for b in map_entries or []:
            try:
                x, y = self.px(float(b["x_m"]), float(b["y_m"]))
            except (KeyError, TypeError, ValueError):
                continue
            r = 15 * ss
            conf = b.get("state") == "confirmed"
            dr.ellipse([x - r, y - r, x + r, y + r], outline=D.BELIEF if conf else D.BELIEF_LIGHT,
                       width=(4 if conf else 3) * ss)
        if start:
            x, y = self.px(start["x_m"], start["y_m"])
            r = 11 * ss
            dr.ellipse([x - r, y - r, x + r, y + r], outline=D.INK, width=3 * ss)
            dr.line([(x - 1.6 * r, y), (x + 1.6 * r, y)], fill=D.INK, width=2 * ss)
            dr.line([(x, y - 1.6 * r), (x, y + 1.6 * r)], fill=D.INK, width=2 * ss)
        # car: truth filled, belief outlined on top of it
        if truth:
            poly = self.pose_poly(truth, self.footprint)
            dr.polygon(poly, fill=D.TRUTH, outline=(255, 255, 255), width=2 * ss)
            arrow = self.pose_poly(truth, [(0.15, 0.0), (-0.04, 0.042), (-0.04, -0.042)])   # slender: clearly a heading
            dr.polygon(arrow, fill=(255, 255, 255))
        if belief:
            poly = self.pose_poly(belief, self.footprint)
            dr.polygon(poly, outline=D.BELIEF, width=4 * ss)
            tip = self.pose_poly(belief, [(0.10, 0.0), (0.34, 0.0)])
            dr.line(tip, fill=D.BELIEF, width=4 * ss)
        return img.resize(self.size, Image.LANCZOS)

    def _lens(self, pose):
        th = math.radians(pose["theta_deg"])
        return self.px(pose["x_m"] + self.lens_x * math.cos(th), pose["y_m"] + self.lens_x * math.sin(th))

    def _fov(self, img, pose):
        th = math.radians(pose["theta_deg"])
        lx, ly = pose["x_m"] + self.lens_x * math.cos(th), pose["y_m"] + self.lens_x * math.sin(th)
        half = math.radians(self.hfov / 2.0)
        n = 24
        pts = [self.px(lx, ly)] + [self.px(lx + self.range * math.cos(th - half + 2 * half * i / n),
                                          ly + self.range * math.sin(th - half + 2 * half * i / n))
                                  for i in range(n + 1)]
        wedge = Image.new("L", img.size, 0)
        ImageDraw.Draw(wedge).polygon(pts, fill=80)
        wedge = ImageChops.multiply(wedge, self._mask)
        img.paste(Image.new("RGB", img.size, D.SEEN_FILL), (0, 0), wedge)
