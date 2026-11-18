#!/usr/bin/env python3
"""Tag layout for the real arena: the room the Spark is in (work list 2.5, plan task M3.T10).

Usage (needs Pillow; --print-pdf also needs OpenCV with cv2.aruco):
    python3 course-project/tools/room_layout.py --out DIR [--seed real-room-1] [--print-pdf PATH]
    python3 course-project/tools/room_layout.py --out DIR --seed real-room-2 --hfov-deg 46.9 --world WORLD.json \
        [--print-pdf PATH --pdf-pages new] [--sheet-pdf PATH]

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

Layout "real-room-2" (2026-11-18) is the twelve tags of "real-room-1" as printed, with their IDs, plus the eight tags
of EXTRA_TAGS (layout C20, chosen by the lead from tools/room_rehearsal.py's search). For it the tool also writes
checks.txt: every clash found (door trim, corner, the Ethernet stretch, a known outlet, a neighbouring page, the ID
rule) and, with --world, every difference from that world file. A clash is reported, never repaired by moving a tag.
--pdf-pages new prints only the added tags' pages (no sheet page); --sheet-pdf writes the mounting sheet for all tags
as a one-page PDF. --hfov-deg and --min-range-m set the coverage table's field of view and near limit (defaults: the
simulator's placeholders, 60 degrees and 0.25 m); with a calibrated configs/camera.json the table gains a block that
asks for the whole tag in the picture through the camera model (beaconmind.camera_model).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-17: wrote this tool from the survey and the kinsim rules.
AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: added layout real-room-2, the clash and world-file checks,
the new-pages and sheet PDFs, and the coverage options.
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

# Layout real-room-2: the printed twelve plus these, as (wall key, metres from the wall's `from` corner to the tag
# centre, tag ID), in uid order T12, T13, ... (the order of tools/room_world.py's PLUS8, which gives them the IDs the
# printed twelve leave free, ascending).
EXTRA_TAGS = {
    "real-room-2": {"base": "real-room-1",
                    "extra": [("angled", 0.20, 1), ("window", 2.15, 4), ("window", 1.25, 5), ("window", 3.14, 6),
                              ("window", 0.14, 7), ("w295", 2.00, 8), ("w295", 2.69, 9), ("window", 4.04, 11)]},
}
PAGE_GAP_M = 0.01      # two pages on one wall keep at least this much bare wall between them
ETHERNET_SPAN = ("desk", 3.63, 5.12)   # desk wall, metres from corner 5: the jack and its cable, no tags (Xiaohui)
# Outlets whose place along a wall is known, as estimates read from the room photos (room-survey.md): wall key ->
# metres from the wall's `from` corner. An outlet is taken as 0.12 m wide. The outlets of the 295 cm wall, the window
# wall and the desk wall were never located along their walls, so those walls cannot be checked here.
OUTLETS_M = {"angled": [0.50], "doors": [1.90]}
OUTLET_HALF_M = 0.06
UNLOCATED_OUTLETS = {"w295": "one outlet, place along the wall not recorded",
                     "window": "low outlets, places along the wall not recorded",
                     "desk": "one outlet (the Spark's power brick) between the entrance trim and the desk, place not recorded"}

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


def wall_by_key(key):
    return next(w for w in WALLS if w["key"] == key)


def build_layout(seed):
    """The tags of a named layout. "real-room-1" (or any other seed): the twelve nominal positions with IDs drawn for
    that seed. A key of EXTRA_TAGS: its base layout unchanged, then the extra tags with the IDs given there; slide
    ranges are then narrowed so that no two pages on one wall can meet (limit_slides)."""
    spec = EXTRA_TAGS.get(seed)
    tags = build_tags()
    assign_ids(tags, spec["base"] if spec else seed)
    if not spec:
        return tags
    for wall_key, s, tag_id in spec["extra"]:
        wall = wall_by_key(wall_key)
        ux, uy, length = unit(CORNERS[wall["from"]], CORNERS[wall["to"]])
        nx, ny = inward_normal(wall)
        x0, y0 = CORNERS[wall["from"]]
        span = [(a, b) for a, b in wall["spans"] if a <= s <= b]
        lo, hi = (span[0][0] + CLEAR_M, span[0][1] - CLEAR_M) if span else (s, s)
        tags.append({"wall": wall["key"], "wall_name": wall["name"], "from": wall["from"], "along_m": s,
                     "x_m": round(x0 + ux * s, 3), "y_m": round(y0 + uy * s, 3), "z_m": TAG_CENTRE_Z_M,
                     "normal_deg": round(math.degrees(math.atan2(ny, nx)), 1),
                     "slide_m": [round(min(s, max(lo, s - SLIDE_M)), 2), round(max(s, min(hi, s + SLIDE_M)), 2)],
                     "uid": "T%02d" % len(tags), "id": tag_id, "added": True})
    limit_slides(tags)
    return tags


def limit_slides(tags):
    """Narrow slide ranges so that two neighbouring pages on one wall cannot overlap whatever both do: each of the
    two keeps its side of the midpoint between their nominal centres, less half a page and half the gap."""
    need = (PAGE_W_M + PAGE_GAP_M) / 2.0
    for key in {t["wall"] for t in tags}:
        row = sorted((t for t in tags if t["wall"] == key), key=lambda t: t["along_m"])
        for a, b in zip(row, row[1:]):
            mid = (a["along_m"] + b["along_m"]) / 2.0
            hi, lo = math.floor((mid - need) * 100) / 100.0, math.ceil((mid + need) * 100) / 100.0
            # never past the tag's own nominal place: if the nominal places already overlap, check_layout says so
            a["slide_m"] = [a["slide_m"][0], max(a["along_m"], min(a["slide_m"][1], hi))]
            b["slide_m"] = [min(b["along_m"], max(b["slide_m"][0], lo)), b["slide_m"][1]]


def check_layout(tags):
    """(clashes, notes): every problem of the nominal layout as a sentence, and what could not be checked.
    Clashes: a tag centre outside its wall's usable stretches (door trim, wall end) or closer than CLEAR_M to their
    ends; a page reaching into the Ethernet stretch; a page over an outlet whose place is known; two pages on one wall
    closer than PAGE_GAP_M at their nominal places, or able to meet inside their slide ranges; two walls' pages meeting
    round a corner; an ID outside 0-29, used more than twice, the wrong number of doubled IDs, or two copies of an ID
    less than 1.5 m apart. Nothing is moved."""
    clashes, notes = [], []
    half = PAGE_W_M / 2.0
    for t in tags:
        wall = wall_by_key(t["wall"])
        s = t["along_m"]
        length = unit(CORNERS[wall["from"]], CORNERS[wall["to"]])[2]
        if not any(a + CLEAR_M - 1e-9 <= s <= b - CLEAR_M + 1e-9 for a, b in wall["spans"]):
            inside_span = [(a, b) for a, b in wall["spans"] if a <= s <= b]
            if inside_span:
                a, b = inside_span[0]
                clashes.append("%s (id %d): centre %.0f cm from %s on the %s is %.0f cm from the end of its bare stretch "
                               "(%.0f-%.0f cm); a page needs %.0f cm (door trim or corner)"
                               % (t["uid"], t["id"], s * 100, t["from"], t["wall_name"], min(s - a, b - s) * 100,
                                  a * 100, b * 100, CLEAR_M * 100))
            else:
                clashes.append("%s (id %d): centre %.0f cm from %s is not on a bare stretch of the %s (door or off the "
                               "wall, which is %.0f cm long)" % (t["uid"], t["id"], s * 100, t["from"], t["wall_name"], length * 100))
        if t["wall"] == ETHERNET_SPAN[0] and s + half > ETHERNET_SPAN[1] and s - half < ETHERNET_SPAN[2]:
            clashes.append("%s (id %d): the page reaches into the Ethernet stretch of the desk wall (%.0f-%.0f cm from "
                           "corner 5)" % (t["uid"], t["id"], ETHERNET_SPAN[1] * 100, ETHERNET_SPAN[2] * 100))
        for outlet in OUTLETS_M.get(t["wall"], ()):
            if abs(s - outlet) < half + OUTLET_HALF_M:
                clashes.append("%s (id %d): the page (%.0f-%.0f cm from %s) covers the outlet estimated at %.0f cm on the %s"
                               % (t["uid"], t["id"], (s - half) * 100, (s + half) * 100, t["from"], outlet * 100, t["wall_name"]))
    for key in {t["wall"] for t in tags}:
        row = sorted((t for t in tags if t["wall"] == key), key=lambda t: t["along_m"])
        for a, b in zip(row, row[1:]):
            gap = b["along_m"] - a["along_m"] - PAGE_W_M
            if gap < PAGE_GAP_M - 1e-9:
                clashes.append("%s and %s overlap on the %s: centres %.0f and %.0f cm, pages %.1f cm wide"
                               % (a["uid"], b["uid"], a["wall_name"], a["along_m"] * 100, b["along_m"] * 100, PAGE_W_M * 100))
            elif b["slide_m"][0] - a["slide_m"][1] - PAGE_W_M < PAGE_GAP_M - 1e-9:
                clashes.append("%s and %s can meet on the %s if both slide towards each other (%s up to %.0f cm, %s down "
                               "to %.0f cm)" % (a["uid"], b["uid"], a["wall_name"], a["uid"], a["slide_m"][1] * 100,
                                                b["uid"], b["slide_m"][0] * 100))
    # pages of two walls round a shared corner: each page edge must stay on its own wall
    for t in tags:
        wall = wall_by_key(t["wall"])
        length = unit(CORNERS[wall["from"]], CORNERS[wall["to"]])[2]
        if t["along_m"] - half < 0 or t["along_m"] + half > length:
            clashes.append("%s (id %d): the page sticks out past the end of the %s" % (t["uid"], t["id"], t["wall_name"]))
    ids = [t["id"] for t in tags]
    for i in sorted(set(ids)):
        same = [t for t in tags if t["id"] == i]
        if not 0 <= i <= 29:
            clashes.append("id %d is outside 0-29" % i)
        if len(same) > 2:
            clashes.append("id %d is on %d tags (at most two)" % (i, len(same)))
        if len(same) == 2:
            d = math.dist((same[0]["x_m"], same[0]["y_m"]), (same[1]["x_m"], same[1]["y_m"]))
            if d < 1.5:
                clashes.append("the two tags with id %d (%s, %s) are %.2f m apart, under 1.5 m" % (i, same[0]["uid"], same[1]["uid"], d))
    doubled = sum(1 for i in set(ids) if ids.count(i) == 2)
    if doubled != N_DUP:
        clashes.append("%d IDs are used twice; the layout rule asks for %d" % (doubled, N_DUP))
    for key in sorted({t["wall"] for t in tags}):
        if key in UNLOCATED_OUTLETS:
            notes.append("not checked, %s: %s. Tags there: %s. The mounting rule applies: slide the page inside its "
                         "range if it would cover an outlet, and write down the centre."
                         % (wall_by_key(key)["name"], UNLOCATED_OUTLETS[key],
                            ", ".join("%s at %.0f cm" % (t["uid"], t["along_m"] * 100)
                                      for t in sorted(tags, key=lambda t: t["along_m"]) if t["wall"] == key)))
    notes.append("the outlet places used (angled section 50 cm from corner 4, doors wall 190 cm from corner 1) are "
                 "estimates from photos; the outlet height (31 cm) is inside a page's height (12-40 cm), so a page at an "
                 "outlet's place does cover it")
    return clashes, notes


def compare_with_world(tags, world):
    """Differences between the layout and a bm.world/1 document's tags, as sentences: uid set, ID, position to the
    millimetre (the world file's three decimals), height, normal to 0.1 degree, tag size."""
    out = []
    theirs = {t["uid"]: t for t in world["tags"]}
    mine = {t["uid"]: t for t in tags}
    for uid in sorted(set(theirs) ^ set(mine)):
        out.append("%s is only in the %s" % (uid, "world file" if uid in theirs else "layout"))
    for uid in sorted(set(theirs) & set(mine)):
        a, b = mine[uid], theirs[uid]
        if a["id"] != b["id"]:
            out.append("%s: id %d in the layout, %d in the world file" % (uid, a["id"], b["id"]))
        for key in ("x_m", "y_m", "z_m"):
            if abs(a[key] - b[key]) > 0.0005:
                out.append("%s: %s %.3f in the layout, %.3f in the world file" % (uid, key, a[key], b[key]))
        if abs((a["normal_deg"] - b["normal_deg"] + 180.0) % 360.0 - 180.0) > 0.05:
            out.append("%s: normal %.1f in the layout, %.1f in the world file" % (uid, a["normal_deg"], b["normal_deg"]))
        if a["wall"] != b.get("wall", a["wall"]):
            out.append("%s: wall %s in the layout, %s in the world file" % (uid, a["wall"], b["wall"]))
        if abs(b.get("black_size_m", BLACK_MM / 1000) - BLACK_MM / 1000) > 1e-9:
            out.append("%s: black side %.0f mm in the world file, %.0f mm printed" % (uid, b["black_size_m"] * 1000, BLACK_MM))
    return out


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


def visible_range(pose, tag, occluders=(), hfov_deg=None, min_range_m=None, camera=None):
    """The tag's range if it passes every test but the upper range limit, else None. hfov_deg and min_range_m default
    to the simulator's placeholders (HFOV_DEG, MIN_RANGE_M). With camera (a beaconmind.camera_model.Camera) the field
    of view and near-limit tests are replaced by: the whole tag sheet (black square and white border, centre
    TAG_CENTRE_Z_M up) is in the picture, lens distortion and mount angles included."""
    dx, dy = tag["x_m"] - pose[0], tag["y_m"] - pose[1]
    r = math.hypot(dx, dy)
    if r < (MIN_RANGE_M if min_range_m is None else min_range_m):
        return None
    b = (math.degrees(math.atan2(dy, dx)) - pose[2] + 180.0) % 360.0 - 180.0
    if camera is not None:
        if abs(b) > 40.0:
            return None
        inc = (tag["normal_deg"] - pose[2] - b - 180.0 + 180.0) % 360.0 - 180.0
        from beaconmind import camera_model as cm
        if not cm.square_in_view(camera, r, b, tag.get("z_m", TAG_CENTRE_Z_M), BLACK_MM / 1000 * 0.625, 2.0, inc):
            return None
    elif abs(b) > (HFOV_DEG if hfov_deg is None else hfov_deg) / 2:
        return None
    nx, ny = math.cos(math.radians(tag["normal_deg"])), math.sin(math.radians(tag["normal_deg"]))
    if math.degrees(math.acos(max(-1.0, min(1.0, (-dx * nx - dy * ny) / r)))) > MAX_INCIDENCE_DEG:
        return None
    if any(segment_hits_box(pose[:2], (tag["x_m"], tag["y_m"]), box) for box in occluders):
        return None
    return r


def coverage(drive_poly, tags, ranges, inset=0.30, step=0.10, occluders=(), hfov_deg=None, min_range_m=None,
             camera=None):
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
    far = max(ranges)
    seen = [[(i, r) for i, r in ((i, visible_range(p, t, occluders, hfov_deg, min_range_m, camera))
                                 for i, t in enumerate(tags) if math.hypot(t["x_m"] - p[0], t["y_m"] - p[1]) <= far)
             if r is not None] for p in poses]
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
             ""]
    added = any(t.get("added") for t in tags)
    if added:
        lines += ["Rows marked **new** are the pages added by this layout; the others are the pages already printed. "
                  "The table is in wall order (each wall from its named corner), so neighbours are next to each other. "
                  "A slide range is narrower than before where a new page is a neighbour: inside the ranges given, no "
                  "two pages can touch.", ""]
        order = {w["key"]: i for i, w in enumerate(WALLS)}
        rows = sorted(tags, key=lambda t: (order[t["wall"]], t["along_m"]))
        lines += ["| Tag | ID | Page | Wall | From | Nominal centre (cm) | May slide within (cm) | Measured centre (cm) |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        for t in rows:
            lines.append("| %s | %d%s | %s | %s | %s | %.0f | %.0f–%.0f | |" % (
                t["uid"], t["id"], " (twice)" if t["id"] in dup else "", "**new**" if t.get("added") else "printed",
                t["wall_name"], t["from"], t["along_m"] * 100, t["slide_m"][0] * 100, t["slide_m"][1] * 100))
    else:
        lines += ["| Tag | ID | Wall | From | Nominal centre (cm) | May slide within (cm) | Measured centre (cm) |",
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
    crowded = any(t.get("added") for t in tags)
    drawn = []
    for t in tags:
        x, y = P(t["x_m"], t["y_m"])
        d.rectangle([x - 7, y - 7, x + 7, y + 7], fill="#1f4e9c" if t.get("added") else "black")
        nx, ny = math.cos(math.radians(t["normal_deg"])), math.sin(math.radians(t["normal_deg"]))
        label = "%s id%d" % (t["uid"], t["id"])
        lw = d.textlength(label, font=font)
        cx, cy = x + nx * 16, y - ny * 16           # just inside the room, along the wall's normal
        lx = cx if nx > 0.5 else cx - lw if nx < -0.5 else cx - lw / 2
        ly = cy - 8 if abs(ny) <= 0.5 else (cy - 18 if ny > 0 else cy + 2)
        if crowded and abs(ny) > 0.5:
            # labels along a wall drawn left to right: every second one a line further into the room
            rank = sorted(u["along_m"] for u in tags if u["wall"] == t["wall"]).index(t["along_m"])
            ly += (-17 if ny > 0 else 17) * (rank % 2)
        if crowded:
            # a label that would cover an earlier one moves along its wall (down the picture) until it is free
            while any(lx < r[2] and lx + lw > r[0] and ly < r[3] and ly + 16 > r[1] for r in drawn):
                ly += 17
            drawn.append((lx, ly, lx + lw, ly + 16))
        d.text((lx, ly), label, fill="#1f4e9c" if t.get("added") else "black", font=font)
    title = "BeaconMind room layout (nominal). Dashed: driving area. Red: door trim. 1 m = %d px" % s
    if any(t.get("added") for t in tags):
        title = "BeaconMind room layout, %d tags (nominal). Blue: added tags. Dashed: driving area. Red: door trim." % len(tags)
    d.text((pad, 20), title, fill="black", font=font)
    img.save(path)


def render_pdf(path, tags, seed, which="all", sheet_path=None):
    """Write the print PDF (US Letter, 300 dpi). which "all": the mounting sheet, then one page per tag (the format
    of layout real-room-1's file). which "new": only the pages of the tags a layout adds, no sheet page. sheet_path:
    also write the mounting sheet alone, as a one-page PDF. path may be None when only the sheet is wanted. Every tag
    page written is decoded and its black square measured; the lines returned say what was found."""
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
    added = any(t.get("added") for t in tags)
    if added:
        # wall order, so that neighbours are next to each other; a column says which pages are new
        order = {w["key"]: i for i, w in enumerate(WALLS)}
        d.text((mm(20), y), "%-4s %-4s %-8s %-15s %-9s %-7s %-8s %s" % (
            "Tag", "ID", "Page", "Wall", "From", "Centre", "Slide", "Measured centre"), fill=0, font=mono)
        d.text((mm(20), y + mm(5)), "%-4s %-4s %-8s %-15s %-9s %-7s %-8s" % ("", "", "", "", "", "(cm)", "(cm)"), fill=0, font=mono)
        y += mm(5)
        for t in sorted(tags, key=lambda t: (order[t["wall"]], t["along_m"])):
            y += mm(8.5)
            d.text((mm(20), y), "%-4s %-4s %-8s %-15s %-9s %-7.0f %-8s ____________" % (
                t["uid"], "%d%s" % (t["id"], "*" if t["id"] in dup else ""), "NEW" if t.get("added") else "printed",
                t["wall_name"], t["from"], t["along_m"] * 100,
                "%.0f-%.0f" % (t["slide_m"][0] * 100, t["slide_m"][1] * 100)), fill=0, font=mono)
        y += mm(12)
        d.text((mm(20), y), "NEW = page added by this layout. Rows are in wall order. Inside the slide ranges no two pages touch.",
               fill=0, font=small)
        y += mm(9)
    else:
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
    if y + mm(12) > page_h:
        raise SystemExit("the mounting sheet does not fit on one page (%d tags)" % len(tags))
    if sheet_path:
        sheet.save(sheet_path, resolution=float(dpi))
        report.append("mounting sheet for %d tags: %s" % (len(tags), sheet_path))
    if path is None:
        return report
    if which == "all":
        pages = [sheet]
        chosen = tags
    elif which == "new":
        pages = []
        chosen = [t for t in tags if t.get("added")]
        if not chosen:
            raise SystemExit("layout %s adds no tags: nothing to print with --pdf-pages new" % seed)
    else:
        raise SystemExit("--pdf-pages must be all or new")

    for t in chosen:
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


def load_camera_model(path=None):
    """The calibrated camera (beaconmind.camera_model.Camera) for the whole-tag coverage block, or None when the
    package or configs/camera.json is not there."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "beaconmind", "src"))
    try:
        from beaconmind import camera_model as cm
        return cm.load_camera(path)
    except Exception as exc:
        print("note: no camera model (%s); the whole-tag coverage block is left out" % exc)
        return None


def coverage_lines(tags, drive, ranges, hfov_deg, min_range_m, base_tags=None, camera=None, with_study=True):
    """The text of coverage.txt and the numbers behind it ({block name: {range: 4 shares}})."""
    numbers = {}
    room_cov, n_room = coverage(drive, tags, ranges, occluders=(DESK,), hfov_deg=hfov_deg, min_range_m=min_range_m)
    numbers["room"] = room_cov
    lines = ["Coverage. One heading: share of (position, heading) samples that see at least 1 / at least 2 tags.",
             "Full turn: share of positions where a turn in place (36 headings) sees at least 1 tag / 2 different tags.",
             "Visibility as kinsim_lite.detect: field of view %s deg, range %.2f m to the limit below, incidence <= %.0f deg,"
             % ("%.0f" % hfov_deg if abs(hfov_deg - round(hfov_deg)) < 1e-9 else "%.1f" % hfov_deg, min_range_m, MAX_INCIDENCE_DEG),
             "range and bearing from the pose point; no random drop-outs. Positions at least 0.30 m inside the driving",
             "area, headings every 10 deg. Room: %d positions (10 cm grid), the desk blocks the view." % n_room]
    if with_study:
        a = STUDY_ARENA
        study_poly = [(a["x0"], a["y0"]), (a["x1"], a["y0"]), (a["x1"], a["y1"]), (a["x0"], a["y1"])]
        study = {r: [0.0] * 4 for r in ranges}
        seeds = range(2000, 2030)
        for sd in seeds:
            cov, n_study = coverage(study_poly, study_tags(sd), ranges, step=0.10)
            for r in ranges:
                for j in range(4):
                    study[r][j] += cov[r][j] / len(seeds)
        numbers["study"] = study
        lines[-1] += " Study arena: the"
        lines += ["2.25 m square with make_world seeds 2000-2029 (%d positions each, 10 cm grid), averaged." % n_study,
                  "kinsim's placeholder range limit is 1.5 m; configs/dv.json rejects detections beyond 2.0 m.", "",
                  "             one heading: room      study      | full turn: room       study",
                  "max range    >=1     >=2     >=1     >=2      |  >=1     >=2      >=1     >=2"]
        for r in ranges:
            lines.append("%6.1f m   %5.1f%%  %5.1f%%  %5.1f%%  %5.1f%%     | %5.1f%%  %5.1f%%   %5.1f%%  %5.1f%%" % (
                (r,) + tuple(100 * room_cov[r][j] for j in (0, 1)) + tuple(100 * study[r][j] for j in (0, 1))
                + tuple(100 * room_cov[r][j] for j in (2, 3)) + tuple(100 * study[r][j] for j in (2, 3))))
        return lines, numbers

    def block(title, cov, base):
        out = ["", title,
               "             one heading           | full turn            %s" % ("| the printed %d alone: one heading, full turn" % len(base_tags) if base else ""),
               "max range    >=1     >=2           |  >=1     >=2         %s" % ("|  >=1     >=2      >=1     >=2" if base else "")]
        for r in ranges:
            row = "%6.1f m   %5.1f%%  %5.1f%%          | %5.1f%%  %5.1f%%" % ((r,) + tuple(100 * cov[r][j] for j in range(4)))
            if base:
                row += "       | %5.1f%%  %5.1f%%   %5.1f%%  %5.1f%%" % tuple(100 * base[r][j] for j in range(4))
            out.append(row)
        return out

    base_cov = None
    if base_tags:
        base_cov, _ = coverage(drive, base_tags, ranges, occluders=(DESK,), hfov_deg=hfov_deg, min_range_m=min_range_m)
        numbers["room_base"] = base_cov
    lines += block("A. Simulator's rule (tag centre inside the field of view), %d tags:" % len(tags), room_cov, base_cov)
    if camera is not None:
        cam_cov, _ = coverage(drive, tags, ranges, occluders=(DESK,), min_range_m=0.0, camera=camera)
        numbers["camera"] = cam_cov
        cam_base = None
        if base_tags:
            cam_base, _ = coverage(drive, base_tags, ranges, occluders=(DESK,), min_range_m=0.0, camera=camera)
            numbers["camera_base"] = cam_base
        lines += block("B. Camera model (configs/camera.json: the WHOLE tag sheet, black square and white border, inside the\n"
                       "   picture, with lens distortion, the mount's roll, pitch and yaw and the lens 0.12 m ahead of the pose\n"
                       "   point; this also gives the near limit, about 0.79 m straight ahead), %d tags:" % len(tags),
                       cam_cov, cam_base)
        lines += ["", "Block B is the stricter and more faithful one: the detector needs the whole black square and some white",
                  "around it. Both blocks keep the incidence limit and the desk; neither has random drop-outs."]
    return lines, numbers


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seed", default="real-room-1", help="real-room-1, or real-room-2 (the printed twelve plus eight)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--print-pdf")
    ap.add_argument("--pdf-pages", default="all", choices=("all", "new"),
                    help="all: the sheet and every tag; new: only the tags the layout adds")
    ap.add_argument("--sheet-pdf", help="write the mounting sheet alone as a one-page PDF")
    ap.add_argument("--hfov-deg", type=float, default=HFOV_DEG, help="field of view for the coverage table")
    ap.add_argument("--min-range-m", type=float, default=MIN_RANGE_M, help="near limit for the coverage table")
    ap.add_argument("--ranges", type=float, nargs="+", default=None, help="range limits of the coverage table, metres")
    ap.add_argument("--world", help="bm.world/1 file the layout must agree with (to the millimetre)")
    ap.add_argument("--camera", help="camera file for the whole-tag coverage block (default configs/camera.json)")
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    tags = build_layout(args.seed)
    extended = args.seed in EXTRA_TAGS
    drive = drive_polygon()
    layout = {"layout": "bm.room_layout (draft; the world file is made from the measured positions)",
              "seed": args.seed, "frame": "origin corner 5; y along the desk wall to corner 1; x to the window wall; m",
              "corners_m": CORNERS, "desk_box_m": DESK, "drive_polygon_m": [list(p) for p in drive],
              "tag": {"family": "tag36h11", "black_size_m": BLACK_MM / 1000, "border_size_m": BLACK_MM / 4000},
              "tags": tags,
              "duplicates": sorted([[t["uid"] for t in tags if t["id"] == i] for i in {t["id"] for t in tags}
                                    if sum(t["id"] == i for t in tags) > 1])}
    if extended:
        layout["base"] = EXTRA_TAGS[args.seed]["base"]
        layout["added"] = [t["uid"] for t in tags if t.get("added")]
    with open(os.path.join(args.out, "layout.json"), "w", encoding="utf-8") as fh:
        json.dump(layout, fh, indent=1)
    write_mounting(os.path.join(args.out, "mounting.md"), tags, args.seed)
    draw_plan(os.path.join(args.out, "plan.png"), tags, drive)

    failed = False
    if extended or args.world:
        clashes, notes = check_layout(tags)
        check = ["Checks of layout %s (%d tags), tools/room_layout.py. Nominal positions; nothing was moved." % (args.seed, len(tags)), "",
                 "Clashes (door trim, corner, Ethernet stretch, known outlets, neighbouring pages, ID rule): %s"
                 % ("none" if not clashes else "%d" % len(clashes))]
        check += ["  CLASH: " + c for c in clashes]
        check += ["", "Not checkable from the survey:"] + ["  " + n for n in notes]
        base = build_layout(EXTRA_TAGS[args.seed]["base"]) if extended else None
        if base:
            narrowed = [(t, b) for t, b in zip(tags, base) if t["slide_m"] != b["slide_m"]]
            check += ["", "Slide ranges narrowed because a new page is a neighbour (the tag itself is not moved):"]
            check += ["  %s (id %d, %s, nominal %.0f cm): %.0f-%.0f cm, was %.0f-%.0f cm"
                      % (t["uid"], t["id"], t["wall_name"], t["along_m"] * 100, t["slide_m"][0] * 100, t["slide_m"][1] * 100,
                         b["slide_m"][0] * 100, b["slide_m"][1] * 100) for t, b in narrowed] or ["  none"]
            check += ["", "Neighbours on each wall (centre to centre, cm from the wall's corner; a page is %.1f cm wide):" % (PAGE_W_M * 100)]
            for wall in WALLS:
                row = sorted((t for t in tags if t["wall"] == wall["key"]), key=lambda t: t["along_m"])
                length = unit(CORNERS[wall["from"]], CORNERS[wall["to"]])[2]
                check.append("  %s (%.0f cm from %s): %s" % (wall["name"], length * 100, wall["from"], ", ".join(
                    "%s%s %.0f" % (t["uid"], "*" if t.get("added") else "", t["along_m"] * 100) for t in row)))
            check.append("  (* = added)")
        if args.world:
            with open(args.world, encoding="utf-8") as fh:
                world = json.load(fh)
            diffs = compare_with_world(tags, world)
            check += ["", "Against the world file %s (%s, %d tags), positions to the millimetre: %s"
                      % (os.path.basename(args.world), world.get("world_id"), len(world["tags"]),
                         "all %d tags agree (uid, id, x, y, z, normal, size)" % len(tags) if not diffs else "%d differences" % len(diffs))]
            check += ["  DIFFERENCE: " + x for x in diffs]
            failed = failed or bool(diffs)
        failed = failed or bool(clashes)
        with open(os.path.join(args.out, "checks.txt"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(check) + "\n")
        print("\n".join(check))
        print()

    ranges = tuple(args.ranges) if args.ranges else (1.5, 2.0, 2.5, 3.0)
    if extended:
        lines, _numbers = coverage_lines(tags, drive, ranges, args.hfov_deg, args.min_range_m,
                                         base_tags=[t for t in tags if not t.get("added")],
                                         camera=load_camera_model(args.camera), with_study=False)
    else:
        lines, _numbers = coverage_lines(tags, drive, ranges, args.hfov_deg, args.min_range_m)
    with open(os.path.join(args.out, "coverage.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    if args.print_pdf or args.sheet_pdf:
        for line in render_pdf(args.print_pdf, tags, args.seed, args.pdf_pages, args.sheet_pdf):
            print(line)
    for t in tags:
        print(t["uid"], t["id"], t["wall_name"], t["from"], "%.0f cm" % (t["along_m"] * 100),
              "slide %.0f-%.0f" % (t["slide_m"][0] * 100, t["slide_m"][1] * 100))
    print("duplicates:", layout["duplicates"])
    if failed:
        print("LAYOUT CHECKS FAILED: see checks.txt")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
