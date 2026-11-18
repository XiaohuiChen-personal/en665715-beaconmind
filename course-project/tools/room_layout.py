#!/usr/bin/env python3
"""Tag layout for the real arena: the room the Spark is in (work list 2.5, plan task M3.T10).

Usage (needs Pillow; --print-pdf also needs OpenCV with cv2.aruco):
    python3 course-project/tools/room_layout.py --out DIR [--seed real-room-1] [--print-pdf PATH]

Writes to DIR: layout.json (nominal tag positions), mounting.md (the mounting sheet), coverage.txt (how much of the
driving area sees a tag, against the 2.25 m arena of the simulated study) and plan.png. With --print-pdf, a US-Letter
PDF at 300 dpi: page 1 is the mounting sheet, then one page per tag. Each tag sits so that the page's bottom edge,
resting on the top of the baseboard, puts the tag's centre at TAG_CENTRE_Z_M.

Room: course-project/evidence/M3/M3.T10/room-survey.md (Xiaohui Chen's tape readings of 2026-11-17 and their
least-squares fit). Frame: origin at corner 5 (desk wall / 295 cm wall), y along the desk wall towards corner 1,
x towards the window wall; metres. The tag positions are nominal: the world file uses the positions measured after
mounting. The ID rule is the one of beaconmind.envs.kinsim_lite.make_world (AGENT-DESIGN D3): IDs from 0-29, N_DUP
IDs used twice, the two copies at least 1.5 m apart. The visibility test mirrors kinsim_lite.detect (range and bearing
from the pose point, field of view, range window, incidence limit) without its random drop-outs.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-17: wrote this tool from the survey and the kinsim rules.
"""
import argparse
import json
import math
import os
import random
import sys

# ---------------------------------------------------------------- the room (room-survey.md, fitted 2026-11-17)

CORNERS = {  # metres, frame above
    "corner 5": (0.000, 0.000), "corner 4": (2.950, 0.088), "corner 3": (3.824, 0.954),
    "corner 2": (3.808, 5.224), "corner 1": (0.000, 5.120),
}
POLYGON = ["corner 5", "corner 4", "corner 3", "corner 2", "corner 1"]  # counter-clockwise, interior on the left

DESK = {"x0": 0.0, "x1": 0.66, "y0": 2.21, "y1": 3.63}  # 66 cm deep; 221 cm from corner 5, 142 cm long
DRIVE_EDGE_X_M = 0.66  # the driving area's edge along the desk wall: a straight line at the desk's front
PAGE_W_M = 0.2159      # US Letter
CLEAR_M = 0.13         # tag centre to trim or corner: half a page plus 2 cm
SLIDE_M = 0.20         # how far a tag may slide from its nominal spot to clear an outlet
TAG_CENTRE_Z_M = 0.23  # baseboard 12 cm + 11.0 cm from the page's bottom edge to the tag centre
BLACK_MM = 160.0
N_DUP = 3

# Each wall: the corner its distances are measured from, the other corner, the stretches (from that corner, metres)
# a tag centre may use, and how many tags it gets. Door stretches are the outer trim edges Xiaohui measured.
WALLS = [
    {"key": "desk", "name": "desk wall", "from": "corner 5", "to": "corner 1",
     "spans": [(1.02, 2.21)], "tags": 1,
     "note": "between the entrance trim and the desk; an outlet (the Spark's power brick) is in this stretch"},
    {"key": "w295", "name": "295 cm wall", "from": "corner 5", "to": "corner 4",
     "spans": [(0.0, 2.95)], "tags": 3, "note": "one outlet on this wall"},
    {"key": "angled", "name": "angled section", "from": "corner 4", "to": "corner 3",
     "spans": [(0.0, 1.23)], "tags": 1, "nominal": [0.85],
     "note": "one outlet, about 0.5 m from corner 4 in IMG_8151 (estimate); the tag sits towards corner 3"},
    {"key": "window", "name": "window wall", "from": "corner 3", "to": "corner 2",
     "spans": [(0.0, 4.27)], "tags": 4, "note": "low outlets; the windows are far above the tags"},
    {"key": "doors", "name": "doors wall", "from": "corner 1", "to": "corner 2",
     "spans": [(0.0, 0.54), (1.45, 2.16), (3.05, 3.81)], "tags": 3, "nominal": [0.27, 1.65, 3.43],
     "note": "bare stretches 54 / 71 / 76 cm from corner 1; the outlet between the doors is about 1.9 m from corner 1 "
             "in IMG_8148 (estimate), so that tag sits towards door 1"},
]

# kinsim_lite.NOISE placeholders and configs/dv.json
HFOV_DEG, MIN_RANGE_M, MAX_INCIDENCE_DEG = 60.0, 0.25, 60.0
STUDY_ARENA = {"x0": -1.0, "x1": 1.25, "y0": -1.0, "y1": 1.25}


def unit(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy)
    return dx / n, dy / n, n


def inward_normal(wall):
    """Interior is on the left of the counter-clockwise walk."""
    i, j = POLYGON.index(wall["from"]), POLYGON.index(wall["to"])
    a, b = (CORNERS[wall["from"]], CORNERS[wall["to"]]) if (i + 1) % 5 == j else (CORNERS[wall["to"]], CORNERS[wall["from"]])
    ux, uy, _ = unit(a, b)
    return -uy, ux


def nominal_positions(wall):
    """Spread the wall's tags evenly over its usable centre range (each stretch shrunk by CLEAR_M at both ends),
    in proportion to stretch length, so a wall with several stretches gets one tag per stretch when counts allow."""
    usable = [(a + CLEAR_M, b - CLEAR_M) for a, b in wall["spans"] if b - a > 2 * CLEAR_M]
    if "nominal" in wall:
        assert all(any(a <= s <= b for a, b in usable) for s in wall["nominal"]), wall["key"]
        return wall["nominal"]
    if len(usable) == wall["tags"]:
        return [round((a + b) / 2, 2) for a, b in usable]
    (a, b), = usable
    k = wall["tags"]
    return [round(a + (b - a) * (i + 0.5) / k, 2) for i in range(k)]


def build_tags():
    tags = []
    for wall in WALLS:
        ux, uy, length = unit(CORNERS[wall["from"]], CORNERS[wall["to"]])
        nx, ny = inward_normal(wall)
        for s in nominal_positions(wall):
            x0, y0 = CORNERS[wall["from"]]
            tags.append({"wall": wall["key"], "wall_name": wall["name"], "from": wall["from"], "along_m": s,
                         "x_m": round(x0 + ux * s, 3), "y_m": round(y0 + uy * s, 3), "z_m": TAG_CENTRE_Z_M,
                         "normal_deg": round(math.degrees(math.atan2(ny, nx)), 1),
                         "slide_m": [[round(max(a + CLEAR_M, s - SLIDE_M), 2), round(min(b - CLEAR_M, s + SLIDE_M), 2)]
                                     for a, b in wall["spans"] if a + CLEAR_M <= s <= b - CLEAR_M][0]})
    for i, t in enumerate(tags):
        t["uid"] = "T%02d" % i
    return tags


def assign_ids(tags, seed, n_dup=N_DUP):
    """kinsim_lite.make_world's ID rule on these positions."""
    rng = random.Random("room-%s" % seed)
    n = len(tags)
    pos = [(t["x_m"], t["y_m"]) for t in tags]
    for _ in range(200):
        order = list(range(n))
        rng.shuffle(order)
        ids = rng.sample(range(30), n - n_dup)
        out = [None] * n
        for k, idx in enumerate(order[: n - n_dup]):
            out[idx] = ids[k]
        free = order[n - n_dup:]
        for id_ in rng.sample(ids, len(ids)):
            if not free:
                break
            src = out.index(id_)
            far = [f for f in free if math.dist(pos[f], pos[src]) >= 1.5]
            if far:
                out[far[0]] = id_
                free.remove(far[0])
        if not free:
            for t, id_ in zip(tags, out):
                t["id"] = id_
            return
    raise RuntimeError("no ID assignment for seed %s" % seed)


# ---------------------------------------------------------------- coverage

def inside(poly, p):
    """Point in a convex counter-clockwise polygon."""
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        if (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) < 0:
            return False
    return True


def dist_to_edges(poly, p):
    best = float("inf")
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        ux, uy, n = unit(a, b)
        t = max(0.0, min(n, (p[0] - a[0]) * ux + (p[1] - a[1]) * uy))
        best = min(best, math.hypot(p[0] - (a[0] + ux * t), p[1] - (a[1] + uy * t)))
    return best


def segment_hits_box(p, q, box):
    """Liang-Barsky clip of segment p-q against an axis-aligned box."""
    t0, t1 = 0.0, 1.0
    dx, dy = q[0] - p[0], q[1] - p[1]
    for d, lo, hi, s in ((dx, box["x0"], box["x1"], p[0]), (dy, box["y0"], box["y1"], p[1])):
        if abs(d) < 1e-12:
            if s < lo or s > hi:
                return False
            continue
        a, b = (lo - s) / d, (hi - s) / d
        t0, t1 = max(t0, min(a, b)), min(t1, max(a, b))
        if t0 > t1:
            return False
    return True


def visible_range(pose, tag, occluders=()):
    """The tag's range if it passes every test but the upper range limit, else None."""
    dx, dy = tag["x_m"] - pose[0], tag["y_m"] - pose[1]
    r = math.hypot(dx, dy)
    if r < MIN_RANGE_M:
        return None
    b = (math.degrees(math.atan2(dy, dx)) - pose[2] + 180.0) % 360.0 - 180.0
    if abs(b) > HFOV_DEG / 2:
        return None
    nx, ny = math.cos(math.radians(tag["normal_deg"])), math.sin(math.radians(tag["normal_deg"]))
    if math.degrees(math.acos(max(-1.0, min(1.0, (-dx * nx - dy * ny) / r)))) > MAX_INCIDENCE_DEG:
        return None
    if any(segment_hits_box(pose[:2], (tag["x_m"], tag["y_m"]), box) for box in occluders):
        return None
    return r


def coverage(drive_poly, tags, ranges, inset=0.30, step=0.10, occluders=()):
    xs = [p[0] for p in drive_poly]
    ys = [p[1] for p in drive_poly]
    poses = []
    x = min(xs)
    while x <= max(xs):
        y = min(ys)
        while y <= max(ys):
            if inside(drive_poly, (x, y)) and dist_to_edges(drive_poly, (x, y)) >= inset:
                poses.extend((x, y, th) for th in range(0, 360, 10))
            y += step
        x += step
    seen = [[(i, r) for i, r in ((i, visible_range(p, t, occluders)) for i, t in enumerate(tags)) if r is not None]
            for p in poses]
    out = {}
    n_pos = len(poses) // 36
    for rmax in ranges:
        counts = [sum(r <= rmax for _, r in rs) for rs in seen]
        # a full turn in place: the 36 headings of one position, consecutive in `poses`
        turn = [{i for rs in seen[k * 36:(k + 1) * 36] for i, r in rs if r <= rmax} for k in range(n_pos)]
        out[rmax] = (sum(c >= 1 for c in counts) / len(counts), sum(c >= 2 for c in counts) / len(counts),
                     sum(len(s) >= 1 for s in turn) / n_pos, sum(len(s) >= 2 for s in turn) / n_pos)
    return out, n_pos


def study_tags(seed):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "beaconmind", "src"))
    from beaconmind.envs import kinsim_lite as ks
    normals = {"S": 90.0, "E": 180.0, "N": -90.0, "W": 0.0}
    return [{"x_m": t["x_m"], "y_m": t["y_m"], "normal_deg": normals[t["wall"]]} for t in ks.make_world(seed)]


def drive_polygon():
    """The room with the desk-wall side moved to the desk's front edge (keeps it convex)."""
    c = CORNERS
    return [(DRIVE_EDGE_X_M, c["corner 5"][1] + (c["corner 4"][1] - c["corner 5"][1]) * DRIVE_EDGE_X_M / c["corner 4"][0]),
            c["corner 4"], c["corner 3"], c["corner 2"],
            (DRIVE_EDGE_X_M, c["corner 1"][1] + (c["corner 2"][1] - c["corner 1"][1]) * DRIVE_EDGE_X_M / c["corner 2"][0])]


# ---------------------------------------------------------------- outputs

def write_mounting(path, tags, seed):
    dup = {t["id"] for t in tags if sum(u["id"] == t["id"] for u in tags) > 1}
    lines = ["# Mounting sheet — BeaconMind room layout `%s`" % seed, "",
             "Each tag's page goes with its **bottom edge resting on the top of the baseboard** (tag centre %.0f cm "
             "above the carpet), its printed arrow up. The distance is from the named corner, along the wall at "
             "baseboard height, to the **centre of the tag**. If the spot covers an outlet or trim, slide the page "
             "along the wall within the range given and write down where its centre ended up." % (TAG_CENTRE_Z_M * 100),
             "", "| Tag | ID | Wall | From | Nominal centre (cm) | May slide within (cm) | Measured centre (cm) |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for t in tags:
        lines.append("| %s | %d%s | %s | %s | %.0f | %.0f–%.0f | |" % (
            t["uid"], t["id"], " (twice)" if t["id"] in dup else "", t["wall_name"], t["from"], t["along_m"] * 100,
            t["slide_m"][0] * 100, t["slide_m"][1] * 100))
    lines += ["", "IDs marked (twice) are used on two tags on purpose (the study's duplicated-ID condition); the two "
              "copies are at least 1.5 m apart.", ""]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def draw_plan(path, tags, drive_poly):
    from PIL import Image, ImageDraw, ImageFont
    s, pad = 150, 90  # pixels per metre, margin
    w, h = int(3.9 * s) + 2 * pad, int(5.3 * s) + 2 * pad
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=15)
    P = lambda x, y: (pad + x * s, h - pad - y * s)
    room = [P(*CORNERS[c]) for c in POLYGON]
    d.polygon(room, outline="black", width=3)
    d.rectangle([P(DESK["x0"], DESK["y1"]), P(DESK["x1"], DESK["y0"])], fill="#d9c7a7", outline="black")
    d.text(P(0.08, 2.95), "desk", fill="black", font=font)
    for y0, y1 in ((0.025, 1.02),):
        d.line([P(0, y0), P(0, y1)], fill="#c0392b", width=7)
    d.text(P(0.08, 0.5), "entrance", fill="#c0392b", font=font)
    for a, b in ((0.54, 1.45), (2.16, 3.05)):
        y = lambda x: CORNERS["corner 1"][1] + (CORNERS["corner 2"][1] - CORNERS["corner 1"][1]) * x / CORNERS["corner 2"][0]
        d.line([P(a, y(a)), P(b, y(b))], fill="#c0392b", width=7)
    d.line([P(0, 3.63), P(0, 5.12)], fill="#7f8c8d", width=7)
    d.text(P(0.08, 4.3), "jack", fill="#7f8c8d", font=font)
    dp = [P(*p) for p in drive_poly]
    for i in range(len(dp)):
        a, b = dp[i], dp[(i + 1) % len(dp)]
        n = int(math.dist(a, b) // 12)
        for k in range(0, n, 2):
            d.line([(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n),
                    (a[0] + (b[0] - a[0]) * (k + 1) / n, a[1] + (b[1] - a[1]) * (k + 1) / n)], fill="#2e86c1", width=2)
    for name, (x, y) in CORNERS.items():
        d.text((P(x, y)[0] + (8 if x > 1 else -78), P(x, y)[1] + (6 if y < 1 else -22)), name, fill="black", font=font)
    for t in tags:
        x, y = P(t["x_m"], t["y_m"])
        d.rectangle([x - 7, y - 7, x + 7, y + 7], fill="black")
        nx, ny = math.cos(math.radians(t["normal_deg"])), math.sin(math.radians(t["normal_deg"]))
        label = "%s id%d" % (t["uid"], t["id"])
        lw = d.textlength(label, font=font)
        cx, cy = x + nx * 16, y - ny * 16           # just inside the room, along the wall's normal
        lx = cx if nx > 0.5 else cx - lw if nx < -0.5 else cx - lw / 2
        ly = cy - 8 if abs(ny) <= 0.5 else (cy - 18 if ny > 0 else cy + 2)
        d.text((lx, ly), label, fill="black", font=font)
    d.text((pad, 20), "BeaconMind room layout (nominal). Dashed: driving area. Red: door trim. 1 m = %d px" % s,
           fill="black", font=font)
    img.save(path)


def render_pdf(path, tags, seed):
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import make_tags as mt
    dpi = 300
    page_w, page_h = int(8.5 * dpi), int(11 * dpi)
    mm = lambda v: int(round(v / 25.4 * dpi))
    side = mt.black_side_px(BLACK_MM, dpi)                     # 1888 px = 159.85 mm
    border = side // 8                                          # make_tags' white border
    total = side + 2 * border
    bottom_gap = mm(TAG_CENTRE_Z_M * 1000 - 120.0) - total // 2  # page bottom on the 12 cm baseboard top
    font_path = next(p for p in ("/System/Library/Fonts/Supplemental/Arial.ttf",
                                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf") if os.path.exists(p))
    mono_path = next(p for p in ("/System/Library/Fonts/Supplemental/Courier New.ttf",
                                 "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf") if os.path.exists(p))
    big, mid, small = (ImageFont.truetype(font_path, s) for s in (110, 52, 40))
    mono = ImageFont.truetype(mono_path, 38)
    dup = {t["id"] for t in tags if sum(u["id"] == t["id"] for u in tags) > 1}
    detector = cv2.aruco.ArucoDetector(mt.dictionary())
    pages, report = [], []

    def scale_bar(d, y):
        x0 = mm(20)
        d.rectangle([x0, y, x0 + mm(100), y + mm(2)], fill="black")
        for k in range(11):
            d.line([x0 + mm(10 * k), y - mm(3 if k % 5 == 0 else 1.5), x0 + mm(10 * k), y], fill="black", width=3)
        d.text((x0 + mm(103), y - mm(4)), "100 mm: check with a ruler", fill="black", font=small)

    sheet = Image.new("L", (page_w, page_h), 255)
    d = ImageDraw.Draw(sheet)
    d.text((mm(20), mm(18)), "BeaconMind room layout %s: mounting sheet" % seed, fill=0, font=mid)
    y = mm(34)
    d.text((mm(20), y), "%-4s %-4s %-15s %-9s %-7s %-8s %s" % (
        "Tag", "ID", "Wall", "From", "Centre", "Slide", "Measured centre"), fill=0, font=mono)
    d.text((mm(20), y + mm(5)), "%-4s %-4s %-15s %-9s %-7s %-8s" % ("", "", "", "", "(cm)", "(cm)"), fill=0, font=mono)
    y += mm(5)
    for t in tags:
        y += mm(11)
        d.text((mm(20), y), "%-4s %-4s %-15s %-9s %-7.0f %-8s ____________" % (
            t["uid"], "%d%s" % (t["id"], "*" if t["id"] in dup else ""), t["wall_name"], t["from"],
            t["along_m"] * 100, "%.0f-%.0f" % (t["slide_m"][0] * 100, t["slide_m"][1] * 100)), fill=0, font=mono)
    y += mm(16)
    for line in ("* used on two tags on purpose; the two copies are at least 1.5 m apart.",
                 "Distances: from the named corner, along the wall at baseboard height, to the tag's centre.",
                 "Each page's bottom edge rests on the top of the baseboard (tag centre %.0f cm up)." % (TAG_CENTRE_Z_M * 100),
                 "Print every page at 100 %% (Actual size). Each black square must measure %.0f mm +/- 1 mm." % BLACK_MM):
        d.text((mm(20), y), line, fill=0, font=small)
        y += mm(9)
    scale_bar(d, y + mm(10))
    pages.append(sheet)

    for t in tags:
        tag = mt.add_white_border(mt.render_marker(t["id"], side))[0]
        page = Image.new("L", (page_w, page_h), 255)
        x0, y0 = (page_w - total) // 2, page_h - bottom_gap - total
        page.paste(Image.fromarray(tag), (x0, y0))
        d = ImageDraw.Draw(page)
        d.text((mm(20), mm(14)), "%s   ID %d" % (t["uid"], t["id"]), fill=0, font=big)
        d.text((mm(20), mm(36)), "%s, %.0f cm from %s to the tag's centre" % (t["wall_name"], t["along_m"] * 100, t["from"]),
               fill=0, font=mid)
        d.text((mm(20), mm(46)), "Bottom edge of this page on top of the baseboard.  THIS SIDE UP  ^", fill=0, font=small)
        if t["id"] in dup:
            d.text((mm(20), mm(53)), "ID %d is on two tags on purpose." % t["id"], fill=0, font=small)
        scale_bar(d, mm(62))
        arr = np.asarray(page)
        corners, ids, _ = detector.detectMarkers(arr)
        found = [] if ids is None else [int(v) for v in ids.flatten()]
        black_px = int((arr[y0:y0 + total, :] < 128).any(axis=0).sum())  # columns with black, tag rows only
        centre_from_bottom_mm = (page_h - (y0 + total / 2)) / dpi * 25.4
        report.append("%s id=%d decoded=%s black_side_px=%d (%.2f mm) centre_above_page_bottom=%.1f mm" % (
            t["uid"], t["id"], found, black_px, black_px / dpi * 25.4, centre_from_bottom_mm))
        if found != [t["id"]]:
            raise SystemExit("page for %s decodes as %s, expected [%d]" % (t["uid"], found, t["id"]))
        pages.append(page)
    pages[0].save(path, save_all=True, append_images=pages[1:], resolution=float(dpi))
    return report


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seed", default="real-room-1")
    ap.add_argument("--out", required=True)
    ap.add_argument("--print-pdf")
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    tags = build_tags()
    assign_ids(tags, args.seed)
    drive = drive_polygon()
    layout = {"layout": "bm.room_layout (draft; the world file is made from the measured positions)",
              "seed": args.seed, "frame": "origin corner 5; y along the desk wall to corner 1; x to the window wall; m",
              "corners_m": CORNERS, "desk_box_m": DESK, "drive_polygon_m": [list(p) for p in drive],
              "tag": {"family": "tag36h11", "black_size_m": BLACK_MM / 1000, "border_size_m": BLACK_MM / 4000},
              "tags": tags,
              "duplicates": sorted([[t["uid"] for t in tags if t["id"] == i] for i in {t["id"] for t in tags}
                                    if sum(t["id"] == i for t in tags) > 1])}
    with open(os.path.join(args.out, "layout.json"), "w", encoding="utf-8") as fh:
        json.dump(layout, fh, indent=1)
    write_mounting(os.path.join(args.out, "mounting.md"), tags, args.seed)
    draw_plan(os.path.join(args.out, "plan.png"), tags, drive)

    ranges = (1.5, 2.0, 2.5, 3.0)
    room_cov, n_room = coverage(drive, tags, ranges, occluders=(DESK,))
    a = STUDY_ARENA
    study_poly = [(a["x0"], a["y0"]), (a["x1"], a["y0"]), (a["x1"], a["y1"]), (a["x0"], a["y1"])]
    study = {r: [0.0] * 4 for r in ranges}
    seeds = range(2000, 2030)
    for sd in seeds:
        cov, n_study = coverage(study_poly, study_tags(sd), ranges, step=0.10)
        for r in ranges:
            for j in range(4):
                study[r][j] += cov[r][j] / len(seeds)
    lines = ["Coverage. One heading: share of (position, heading) samples that see at least 1 / at least 2 tags.",
             "Full turn: share of positions where a turn in place (36 headings) sees at least 1 tag / 2 different tags.",
             "Visibility as kinsim_lite.detect: field of view %.0f deg, range %.2f m to the limit below, incidence <= %.0f deg,"
             % (HFOV_DEG, MIN_RANGE_M, MAX_INCIDENCE_DEG),
             "range and bearing from the pose point; no random drop-outs. Positions at least 0.30 m inside the driving",
             "area, headings every 10 deg. Room: %d positions (10 cm grid), the desk blocks the view. Study arena: the"
             % n_room,
             "2.25 m square with make_world seeds 2000-2029 (%d positions each, 10 cm grid), averaged." % n_study,
             "kinsim's placeholder range limit is 1.5 m; configs/dv.json rejects detections beyond 2.0 m.", "",
             "             one heading: room      study      | full turn: room       study",
             "max range    >=1     >=2     >=1     >=2      |  >=1     >=2      >=1     >=2"]
    for r in ranges:
        lines.append("%6.1f m   %5.1f%%  %5.1f%%  %5.1f%%  %5.1f%%     | %5.1f%%  %5.1f%%   %5.1f%%  %5.1f%%" % (
            (r,) + tuple(100 * room_cov[r][j] for j in (0, 1)) + tuple(100 * study[r][j] for j in (0, 1))
            + tuple(100 * room_cov[r][j] for j in (2, 3)) + tuple(100 * study[r][j] for j in (2, 3))))
    with open(os.path.join(args.out, "coverage.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    if args.print_pdf:
        for line in render_pdf(args.print_pdf, tags, args.seed):
            print(line)
    for t in tags:
        print(t["uid"], t["id"], t["wall_name"], t["from"], "%.0f cm" % (t["along_m"] * 100),
              "slide %.0f-%.0f" % (t["slide_m"][0] * 100, t["slide_m"][1] * 100))
    print("duplicates:", layout["duplicates"])


if __name__ == "__main__":
    main(sys.argv[1:])
