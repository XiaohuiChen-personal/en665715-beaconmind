#!/usr/bin/env python3
"""Camera calibration with the phone checkerboard (plan task M1.T7, work list 2.3). Spark host: /usr/bin/python3
(OpenCV 4.13, numpy). Frames come from a recorded session (tools/record_session.sh, camera at XGA q12).

    # while Xiaohui holds the phone in front of the car's camera (the recorder's frame saver running):
    python3 course-project/tools/calibrate_camera.py live --session <session dir> [--target 30]
    # afterwards:
    python3 course-project/tools/calibrate_camera.py calibrate --session <session dir> \
        --out course-project/configs/camera.json --report <evidence>/calib-report.txt

live reads the session's frames/latest.jpg, finds the 12 x 5 inner corners of the phone board
(evidence/M1/M1.T7/board), keeps a frame only when the board is held still for two frames and adds a position,
distance or tilt the set still lacks, and writes calib/accepted.jsonl. It prints a status line per frame and, for
the operator who is holding the phone and cannot see a screen, lines starting with "SAY: " that the Mac can speak
(`... | grep --line-buffered '^SAY: ' | while read -r l; do say "${l#SAY: }"; done`). It first learns which way the
picture moves when the operator moves the board to their right (the camera faces them).
calibrate runs cv2.calibrateCamera (plumb-bob, 5 coefficients) on the kept frames, drops images whose RMS is above
twice the median once, recalibrates, and writes the report and camera.json (bm.camera-1; extrinsics null until
M1.T7 steps 8-9).

The corner refinement uses the half-window rule found by the board's simulated check (0.4 x the smallest corner
spacing, at most 11 px; evidence/M1/M1.T7/board/README.md). Distances assume the design's 66 deg field of view until
the calibration measures it; they only steer the operator.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-18: wrote this tool.
"""
import argparse
import json
import math
import os
import sys
import time

COLS, ROWS = 12, 5             # inner corners of checkerboard_12x5_2868x1320.png (the phone board; --cols/--rows)
SQUARE_M = 0.009111            # 165 px at 460 ppi (board README; ruler-check.md; --square-m)
NOMINAL_HFOV_DEG = 66.0        # steering only
GRID = (8, 6)                  # coverage cells over the image (4:3)
BANDS = (("close", 0.15, 0.25), ("middle", 0.25, 0.40), ("far", 0.40, 0.60))   # --bands for a larger board
PICTURE_SIDES = None           # spoken words for the picture's left and right sides (--picture-left/--picture-right)


def configure(cols=None, rows=None, square_m=None, bands=None, picture_sides=None):
    """Set the board and the distance bands (the paper board of 2026-11-18 is 9 x 6 inner corners of 23.28 mm,
    used at about 30-70 cm). bands: four edges in metres, close | middle | far."""
    global COLS, ROWS, SQUARE_M, BANDS, PICTURE_SIDES
    COLS, ROWS = cols or COLS, rows or ROWS
    SQUARE_M = square_m or SQUARE_M
    if bands:
        e = bands
        BANDS = (("close", e[0], e[1]), ("middle", e[1], e[2]), ("far", e[2], e[3]))
    if picture_sides:
        PICTURE_SIDES = picture_sides


def spoken_distance(band):
    lo = {b[0]: b[1] for b in BANDS}
    hi = {b[0]: b[2] for b in BANDS}
    mid = (hi["close"] + hi["middle"]) / 2 if band == "near" else (lo[band] + hi[band]) / 2
    return "about %d centimetres" % (5 * round(mid * 100 / 5))

# What the set needs, in the order the operator is asked for it (board README table, XGA bands of detect_sim_xga.txt)
# "near" = close or middle (up to 40 cm). First capture, 2026-11-18: at 20 cm a corner leaves only about 3 cm between
# "centre in the outer third" and "board out of view", too little to hit by hand, and Xiaohui held the phone at about
# 35 cm, so nearly every goal is "near" and only three ask for the far band (skipped if they do not come).
GOALS = ([("near", region, "flat") for region in ("centre", "top left", "top right", "bottom left", "bottom right")]
         + [("near", "any", tilt) for tilt in ("turned", "turned", "turned", "turned", "tipped", "tipped", "tipped", "tipped")]
         + [("near", region, "any") for region in ("left edge", "right edge", "top edge", "bottom edge")]
         + [("far", region, "any") for region in ("centre", "top left", "bottom right")])


# ---------------------------------------------------------------- pure helpers (tested without a camera)

def region_of(u, v):
    """Name of where a point lies in the image, u and v in 0..1 (0,0 = top left of the picture)."""
    col = 0 if u < 1 / 3 else 2 if u > 2 / 3 else 1
    row = 0 if v < 1 / 3 else 2 if v > 2 / 3 else 1
    return {(0, 0): "top left", (1, 0): "top edge", (2, 0): "top right", (0, 1): "left edge", (1, 1): "centre",
            (2, 1): "right edge", (0, 2): "bottom left", (1, 2): "bottom edge", (2, 2): "bottom right"}[(col, row)]


def band_of(dist_m):
    for name, lo, hi in BANDS:
        if lo <= dist_m < hi:
            return name
    return "too close" if dist_m < BANDS[0][1] else "too far"


def tilt_of(yaw_deg, pitch_deg):
    if abs(yaw_deg) < 15 and abs(pitch_deg) < 15:
        return "flat"
    if abs(yaw_deg) >= 20 and abs(yaw_deg) >= abs(pitch_deg):
        return "turned"
    if abs(pitch_deg) >= 20:
        return "tipped"
    return "slight"


def region_ok(region, u, v):
    """Does a board centred at (u, v) count for this goal region? Looser than region_of's thirds, so a corner or an
    edge can be reached without the board leaving the picture."""
    if region == "any":
        return True
    if region == "centre":
        return 0.3 <= u <= 0.7 and 0.3 <= v <= 0.7
    if region.endswith("edge"):
        side = region.split()[0]
        mid_u, mid_v = 0.25 <= u <= 0.75, 0.25 <= v <= 0.75
        return {"left": u < 0.38 and mid_v, "right": u > 0.62 and mid_v,
                "top": v < 0.38 and mid_u, "bottom": v > 0.62 and mid_u}[side]
    vert, horiz = region.split()
    return (v < 0.42 if vert == "top" else v > 0.58) and (u < 0.42 if horiz == "left" else u > 0.58)


def band_ok(band, obs_band):
    return obs_band in ("close", "middle") if band == "near" else obs_band == band


def goal_met(goal, obs):
    band, region, tilt = goal
    return (band_ok(band, obs["band"]) and region_ok(region, obs["u"], obs["v"])
            and (tilt == "any" or obs["tilt"] == tilt))


def open_goal_ids(kept, skipped=()):
    """Indices into GOALS of the goals not yet met; each kept frame fills at most one goal (first match in GOALS
    order). Indices in skipped are left out: live gives up on a goal after --skip-after seconds without progress."""
    remaining = [i for i in range(len(GOALS)) if i not in skipped]
    for obs in kept:
        for j, i in enumerate(remaining):
            if goal_met(GOALS[i], obs):
                del remaining[j]
                break
    return remaining


def open_goals(kept, skipped=()):
    return [GOALS[i] for i in open_goal_ids(kept, skipped)]


def coverage(corner_sets, width, height, grid=GRID):
    """Share of the GRID cells that hold at least one corner of the kept frames."""
    cells = set()
    for corners in corner_sets:
        for x, y in corners:
            cells.add((min(grid[0] - 1, int(x / width * grid[0])), min(grid[1] - 1, int(y / height * grid[1]))))
    return len(cells) / (grid[0] * grid[1])


def instruction(goal, obs, right_sign):
    """One spoken sentence that moves the operator from obs (or nothing seen) toward goal.
    right_sign: +1 if moving the board to the operator's right moves it right in the picture, -1 if left."""
    band, region, tilt = goal
    dist = spoken_distance(band)
    if obs is None:
        where = "" if region == "any" else " " + spoken_region(region, right_sign)
        how = {"flat": "flat to the camera", "turned": "turned about 30 degrees to one side",
               "tipped": "tipped about 30 degrees forward or back", "any": ""}[tilt]
        return "Hold the board %s from the camera%s%s." % (dist, (", " + how) if how else "", ("," + where) if where else "")
    hints = []
    if not band_ok(band, obs["band"]):
        order = [b[0] for b in BANDS]
        now = order.index(obs["band"]) if obs["band"] in order else (-1 if obs["band"] == "too close" else 3)
        want = order.index("middle" if band == "near" and now > 1 else "close" if band == "near" else band)
        hints.append("move it closer" if now > want else "move it farther away")
    if not region_ok(region, obs["u"], obs["v"]):
        hints.append(spoken_region(region, right_sign))
    if tilt == "flat" and obs["tilt"] != "flat":
        hints.append("hold it flat to the camera")
    elif tilt == "turned" and obs["tilt"] != "turned":
        hints.append("turn it about 30 degrees to one side")
    elif tilt == "tipped" and obs["tilt"] != "tipped":
        hints.append("tip it about 30 degrees forward or back")
    return ("Now " + ", and ".join(hints) + ".") if hints else "Hold still."


def spoken_region(region, right_sign):
    """The picture region as the operator facing the camera sees it."""
    words = []
    if "top" in region:
        words.append("up high")
    if "bottom" in region:
        words.append("down low")
    if "left" in region:
        words.append(PICTURE_SIDES[0] if PICTURE_SIDES else "to your right" if right_sign < 0 else "to your left")
    if "right" in region:
        words.append(PICTURE_SIDES[1] if PICTURE_SIDES else "to your left" if right_sign < 0 else "to your right")
    if region == "centre":
        words.append("in the middle")
    return "move it " + " and ".join(words)


def still_limit(corners, floor_px=1.5, share=0.12):
    """Largest mean corner motion between two frames that still counts as held still: a share of one square's size in
    the picture. A hand cannot hold better than about 1 mm, which is about 3.6 px at 22 cm in XGA (first capture,
    2026-11-18: a fixed 1.5 px rejected every frame), while a far board's smaller squares need a tighter limit."""
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    span = math.hypot(max(xs) - min(xs), max(ys) - min(ys))      # diagonal of the corner grid
    square_px = span / math.hypot(COLS - 1, ROWS - 1)
    return max(floor_px, share * square_px)


def come_back(last, right_sign):
    """What to say when the board was just seen at last = (u, v) and has left the picture."""
    u, v = last
    words = []
    if u < 0.3 or u > 0.7:                       # back toward the middle of the picture
        picture_right = u < 0.3
        if PICTURE_SIDES:
            words.append("a little " + PICTURE_SIDES[1 if picture_right else 0])
        else:
            words.append("a little to your right" if picture_right == (right_sign > 0) else "a little to your left")
    if v < 0.3:
        words.append("a little lower")
    elif v > 0.7:
        words.append("a little higher")
    if not words:
        return "I lost the board. Keep all of the phone in view, and avoid glare."
    return "The board went out of view. Come back " + " and ".join(words) + "."


def is_new_view(obs, kept, d_centre=0.10, d_size=0.15, d_angle=12.0):
    """Free mode: a view is worth keeping when it differs from every kept one in where the board is, how large it
    looks, or how it is tilted."""
    for k in kept:
        if (math.hypot(obs["u"] - k["u"], obs["v"] - k["v"]) < d_centre
                and abs(math.log(obs["dist_m"] / k["dist_m"])) < d_size
                and abs(obs["yaw_deg"] - k["yaw_deg"]) < d_angle and abs(obs["pitch_deg"] - k["pitch_deg"]) < d_angle):
            return False
    return True


def next_hint(obs, kept):
    """Free mode, board held by hand: the first move from the current view that (a) keeps the whole board in the
    picture and (b) gives a view the set does not have yet. obs carries hw, hh: the board's half-width and
    half-height in the picture (0..1), page margin included. The capture of 2026-11-18 showed why both checks are
    needed: a hint that only looked at the emptiest side asked for "lower" when the board was already at the bottom
    edge and that view was already kept."""
    hw, hh = obs.get("hw", 0.25), obs.get("hh", 0.25)
    m = 0.03
    cand = []
    if hw > 0.22:                                    # the board fills too much of the picture: distance first
        cand.append((dict(obs, dist_m=obs["dist_m"] * 1.4), "Move the board farther from the camera."))
    for du, words in ((-0.2, "Move the board to your left."), (0.2, "Move the board to your right.")):
        if hw + m <= obs["u"] + du <= 1 - hw - m:
            cand.append((dict(obs, u=obs["u"] + du), words))
    for dv, words in ((-0.2, "Move the board higher."), (0.2, "Move the board lower.")):
        if hh + m <= obs["v"] + dv <= 1 - hh - m:
            cand.append((dict(obs, v=obs["v"] + dv), words))
    cand.append((dict(obs, yaw_deg=obs["yaw_deg"] + 30), "Turn the board about 30 degrees, like opening a door."))
    cand.append((dict(obs, yaw_deg=obs["yaw_deg"] - 30), "Turn the board about 30 degrees the other way."))
    cand.append((dict(obs, pitch_deg=obs["pitch_deg"] + 30), "Tip the top of the board away from the camera."))
    cand.append((dict(obs, pitch_deg=obs["pitch_deg"] - 30), "Tip the top of the board toward the camera."))
    cand.append((dict(obs, dist_m=obs["dist_m"] * 1.4), "Move the board farther from the camera."))
    if hw * 1.4 < 0.42:
        cand.append((dict(obs, dist_m=obs["dist_m"] / 1.4), "Bring the board closer."))
    for view, words in cand:
        if is_new_view(view, kept):
            return words
    return "Try anywhere new."


def aim_hint(corner_sets, width, height, hold="car"):
    """Free mode with the board fixed on a wall and the car held in the hands: which way to aim the car so the
    board lands in the emptiest part of the picture. Turning the camera right moves the board left in the picture;
    tipping it up moves the board down."""
    count = {"left": 0, "right": 0, "top": 0, "bottom": 0}
    for corners in corner_sets:
        for x, y in corners:
            count["left" if x < width / 2 else "right"] += 1
            count["top" if y < height / 2 else "bottom"] += 1
    side = min(count, key=count.get)
    if hold == "board":   # the operator faces the camera and the picture is a mirror for them (direction check)
        return {"left": "Move the board to your left.", "right": "Move the board to your right.",
                "top": "Move the board higher.", "bottom": "Move the board lower."}[side]
    return {"left": "Aim the car a little more to the right.", "right": "Aim the car a little more to the left.",
            "top": "Tip the car's nose down a little.", "bottom": "Tip the car's nose up a little."}[side]


def camera_json(K, dist, rms, n, width, height, frame_size, quality, status, capture_url, today):
    fx, fy = K[0][0], K[1][1]
    name, _, version = status.get("fw", "unknown-0").rpartition("-")
    return {
        "schema": "bm.camera/1", "image_width": width, "image_height": height, "frame_size": frame_size,
        "jpeg_quality": quality, "distortion_model": "plumb_bob",
        "camera_matrix": [round(float(v), 4) for row in K for v in row],   # bm.camera-1: 9 numbers, row-major
        "distortion": [round(float(v), 6) for v in dist], "rms_px": round(float(rms), 4),
        "hfov_deg": round(math.degrees(2 * math.atan(width / (2 * fx))), 2),
        "vfov_deg": round(math.degrees(2 * math.atan(height / (2 * fy))), 2), "n_images": n,
        "extrinsics": {"parent": None, "child": None, "x_m": None, "y_m": None, "z_m": None, "roll_deg": None,
                       "pitch_deg": None, "yaw_deg": None, "uncertainty_m": None, "uncertainty_deg": None},
        "firmware": {"name": name or "unknown", "version": version, "vflip": bool(status.get("vflip", 0)),
                     "hmirror": bool(status.get("hmirror", 0))},
        "capture_url": capture_url, "calibrated": today,
    }


# ---------------------------------------------------------------- OpenCV parts

def board_points():
    import numpy as np
    return np.array([[c * SQUARE_M, r * SQUARE_M, 0.0] for r in range(ROWS) for c in range(COLS)], np.float32)


def find_board(gray, fast=False, sb=False):
    """(12*5, 2) refined corners or None. fast: reject a frame without a board quickly (live). sb: fall back to
    findChessboardCornersSB, which is slow on a frame without a board, so live does not use it."""
    import cv2
    import numpy as np
    flags = cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE | (cv2.CALIB_CB_FAST_CHECK if fast else 0)
    ok, c = cv2.findChessboardCorners(gray, (COLS, ROWS), flags)
    if not ok:
        if not sb:
            return None
        ok, c = cv2.findChessboardCornersSB(gray, (COLS, ROWS), cv2.CALIB_CB_NORMALIZE_IMAGE | cv2.CALIB_CB_ACCURACY)
        return c.reshape(-1, 2) if ok else None
    g = c.reshape(ROWS, COLS, 2)
    spacing = min(np.linalg.norm(np.diff(g, axis=1), axis=2).min(), np.linalg.norm(np.diff(g, axis=0), axis=2).min())
    half = max(2, min(11, int(0.4 * spacing)))
    c = cv2.cornerSubPix(gray, c, (half, half), (-1, -1), (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.001))
    return c.reshape(-1, 2)


def describe(corners, width, height):
    """Where the board is, how far (nominal lens) and how it is tilted."""
    import cv2
    import numpy as np
    f = width / 2 / math.tan(math.radians(NOMINAL_HFOV_DEG / 2))
    K = np.array([[f, 0, width / 2], [0, f, height / 2], [0, 0, 1]])
    ok, rvec, tvec = cv2.solvePnP(board_points(), corners.astype(np.float32), K, None)
    R, _ = cv2.Rodrigues(rvec)
    n = R[:, 2]                                  # board normal in camera coordinates
    yaw = math.degrees(math.atan2(n[0], -n[2] if n[2] < 0 else n[2]))
    pitch = math.degrees(math.atan2(n[1], -n[2] if n[2] < 0 else n[2]))
    u, v = corners[:, 0].mean() / width, corners[:, 1].mean() / height
    dist = float(np.linalg.norm(tvec))
    return {"u": round(float(u), 3), "v": round(float(v), 3), "dist_m": round(dist, 3), "yaw_deg": round(yaw, 1),
            "pitch_deg": round(pitch, 1), "region": region_of(u, v), "band": band_of(dist), "tilt": tilt_of(yaw, pitch)}


def live(args):
    import cv2
    import numpy as np
    frames = os.path.join(args.session, "frames")
    out = os.path.join(args.session, "calib")
    os.makedirs(out, exist_ok=True)
    acc_path = os.path.join(out, "accepted.jsonl")
    kept = [json.loads(l) for l in open(acc_path)] if os.path.exists(acc_path) else []
    acc = open(acc_path, "a")
    say_every = args.say_every
    last_name = prev = last_seen = None
    last_say = 0.0
    misses = 0
    skipped = set()
    target_id, target_since, last_kept = None, time.time(), time.time()
    with open(os.path.join(out, "board.json"), "w") as fh:     # calibrate reads the same board back
        json.dump({"cols": COLS, "rows": ROWS, "square_m": SQUARE_M, "bands": [BANDS[0][1]] + [b[2] for b in BANDS],
                   "picture_sides": PICTURE_SIDES}, fh)
    right_sign = args.right_sign
    probe = []                                    # direction check: board u while the operator moves right

    def say(text):
        nonlocal last_say
        print("SAY: " + text, flush=True)
        last_say = time.time()

    if args.free:
        say("Calibration. Hold the board in front of the camera and move it around slowly. Pause a moment in each "
            "place." if args.hold == "board" else
            "Calibration. Point the car's camera at the board on the wall, and hold steady.")
    elif right_sign == 0:
        say("Calibration. First a direction check. Hold the board flat in the middle, %s from the camera, then "
            "slowly move it to your own right, as you face the camera." % spoken_distance("near"))
    else:
        sides = "" if PICTURE_SIDES else " Left and right mean your own left and right as you face the camera."
        say("Calibration.%s %s" % (sides, instruction(open_goals(kept)[0], None, right_sign)) if open_goals(kept) else "Done.")
    deadline = time.time() + args.max_minutes * 60
    while time.time() < deadline:
        try:
            name = os.readlink(os.path.join(frames, "latest.jpg"))
        except OSError:
            time.sleep(0.2)
            continue
        if name == last_name:
            time.sleep(0.05)
            continue
        last_name = name
        gray = cv2.imread(os.path.join(frames, name), cv2.IMREAD_GRAYSCALE)
        if gray is None:
            continue
        h, w = gray.shape
        corners = find_board(gray, fast=True)
        if corners is None:
            prev = None
            misses += 1
            print("%s no board" % name, flush=True)
            lost_recently = last_seen is not None and time.time() - last_seen[2] < 3.0
            if lost_recently and misses >= 3 and right_sign != 0 and not args.free and time.time() - last_say > 2.5:
                say(come_back(last_seen[:2], right_sign))
                last_seen = None
            elif time.time() - last_say > say_every:
                say("I cannot see the whole board. Bring it back to the middle." if args.free and args.hold == "board"
                    else "I cannot see the board. Point the camera straight at it." if args.free else
                    "I cannot see the whole board. Keep all of the phone in the camera's view, and avoid glare.")
            continue
        obs = describe(corners, w, h)
        last_seen = (obs["u"], obs["v"], time.time())
        misses = 0
        if args.free:                             # no targets: keep every steady view that is new
            obs["hw"] = round(float(corners[:, 0].max() - corners[:, 0].min()) / w / 2 * (COLS + 2.5) / (COLS - 1), 3)
            obs["hh"] = round(float(corners[:, 1].max() - corners[:, 1].min()) / h / 2 * (ROWS + 2.5) / (ROWS - 1), 3)
            still = prev is not None and float(np.abs(corners - prev).mean()) < still_limit(corners, args.still_px)
            prev = corners
            cov = coverage([k["corners"] for k in kept], w, h)
            print("%s u=%.2f v=%.2f d=%.2f yaw=%+.0f pitch=%+.0f still=%s kept=%d coverage=%.2f" % (
                name, obs["u"], obs["v"], obs["dist_m"], obs["yaw_deg"], obs["pitch_deg"], still, len(kept), cov), flush=True)
            if still and is_new_view(obs, kept):
                rec = dict(obs, file=name, corners=[[round(float(x), 3), round(float(y), 3)] for x, y in corners],
                           width=w, height=h)
                kept.append(rec)
                acc.write(json.dumps(rec) + "\n")
                acc.flush()
                prev = None
                cov = coverage([k["corners"] for k in kept], w, h)
                if len(kept) >= args.target and cov >= args.coverage:
                    say("Done. %d views kept. You can put the car down." % len(kept))
                    break
                say("Got it, %d." % len(kept))
            elif time.time() - last_say > say_every:
                say("Hold steady for a moment." if not kept or (not still and is_new_view(obs, kept)) else
                    next_hint(obs, kept) if args.hold == "board" else aim_hint([k["corners"] for k in kept], w, h))
            continue
        if right_sign == 0:                       # learn left/right from the operator's move to their right
            probe.append(obs["u"])
            if len(probe) >= 6 and abs(probe[-1] - probe[0]) > 0.15:
                right_sign = 1 if probe[-1] > probe[0] else -1
                print("direction: moving right moves the board %s in the picture" % ("right" if right_sign > 0 else "left"))
                say("Thanks. " + instruction(open_goals(kept)[0], None, right_sign))
            elif time.time() - last_say > say_every:
                say("Keep moving it slowly to your right.")
            prev = corners
            continue
        still = prev is not None and float(np.abs(corners - prev).mean()) < still_limit(corners, args.still_px)
        prev = corners
        goals = open_goals(kept, skipped)
        ids = open_goal_ids(kept, skipped)
        if ids and ids[0] != target_id:              # the clock runs per target, not per kept frame
            target_id, target_since = ids[0], time.time()
        if goals and time.time() - target_since > args.skip_after:   # do not get stuck on one position
            skipped.add(open_goal_ids(kept, skipped)[0])
            print("skipped goal %s" % (goals[0],), flush=True)
            goals = open_goals(kept, skipped)
            target_since = time.time()
            say("Let's skip that one. " + (instruction(goals[0], None, right_sign) if goals else "Anywhere new, near the edges."))
            continue
        cov = coverage([k["corners"] for k in kept], w, h)
        print("%s %s %s %s d=%.2f yaw=%+.0f pitch=%+.0f still=%s kept=%d coverage=%.2f" % (
            name, obs["region"], obs["band"], obs["tilt"], obs["dist_m"], obs["yaw_deg"], obs["pitch_deg"], still,
            len(kept), cov), flush=True)
        enough = not goals and len(kept) >= args.target and (
            cov >= args.coverage or time.time() - last_kept > 60)   # nothing new for a minute: stop asking
        if enough:
            say("Done. %d frames kept, coverage %d percent. You can put the phone down." % (len(kept), round(cov * 100)))
            break
        useful = any(goal_met(g, obs) for g in goals) or (not goals and coverage(
            [k["corners"] for k in kept] + [corners.tolist()], w, h) > cov + 0.02)
        if still and useful:
            rec = dict(obs, file=name, corners=[[round(float(x), 3), round(float(y), 3)] for x, y in corners],
                       width=w, height=h)
            kept.append(rec)
            acc.write(json.dumps(rec) + "\n")
            acc.flush()
            prev = None
            last_kept = time.time()
            goals = open_goals(kept, skipped)
            nxt = instruction(goals[0], None, right_sign) if goals else "Now anywhere new, especially near the edges."
            say("Got it, %d. %s" % (len(kept), nxt))
        elif time.time() - last_say > say_every:
            say(instruction(goals[0], obs, right_sign) if goals else "Anywhere new, especially near the edges.")
    acc.close()
    print("live: %d frames kept in %s" % (len(kept), acc_path), flush=True)
    return 0


def calibrate(args):
    import cv2
    import numpy as np
    acc = [json.loads(l) for l in open(os.path.join(args.session, "calib", "accepted.jsonl"))]
    w, h = acc[0]["width"], acc[0]["height"]
    img = [np.array(a["corners"], np.float32).reshape(-1, 1, 2) for a in acc]
    lines = ["calibrate_camera.py calibrate, %s, OpenCV %s" % (time.strftime("%Y-%m-%d %H:%M:%S %Z"), cv2.__version__),
             "session %s; %d frames kept by live; image %dx%d; board %dx%d inner corners, square %.6f m" % (
                 args.session, len(acc), w, h, COLS, ROWS, SQUARE_M)]
    pts = board_points()
    obj = [pts for _ in acc]

    def run(idx):
        rms, K, dist, rv, tv = cv2.calibrateCamera([obj[i] for i in idx], [img[i] for i in idx], (w, h), None, None)
        per = []
        for j, i in enumerate(idx):
            p, _ = cv2.projectPoints(obj[i], rv[j], tv[j], K, dist)
            per.append(float(np.sqrt(np.mean(np.sum((p.reshape(-1, 2) - img[i].reshape(-1, 2)) ** 2, axis=1)))))
        return rms, K, dist.ravel(), per

    idx = list(range(len(acc)))
    rms, K, dist, per = run(idx)
    med = float(np.median(per))
    drop = [i for i, e in zip(idx, per) if e > 2 * med]
    lines.append("first pass: rms %.4f px over %d images; per-image median %.4f px; dropped %s" % (
        rms, len(idx), med, [acc[i]["file"] for i in drop] or "none"))
    if drop:
        idx = [i for i in idx if i not in drop]
        rms, K, dist, per = run(idx)
    cov = coverage([acc[i]["corners"] for i in idx], w, h)
    status = json.load(open(os.path.join(args.session, "meta", "camera_status_start.json")))
    meta = json.load(open(os.path.join(args.session, "meta", "session.json")))
    cj = camera_json(K.tolist(), dist.tolist(), rms, len(idx), w, h, status.get("framesize", "?"),
                     int(status.get("quality", 0)), status, "http://%s/capture" % meta.get("camera_ip", "?"),
                     time.strftime("%Y-%m-%d"))
    fx, fy = K[0][0], K[1][1]
    lines += ["final: rms %.4f px over %d images (per-image max %.4f px)" % (rms, len(idx), max(per)),
              "fx %.2f fy %.2f (fx/fy %.4f, within 3 %%: %s) cx %.2f cy %.2f" % (
                  fx, fy, fx / fy, abs(fx / fy - 1) <= 0.03, K[0][2], K[1][2]),
              "distortion k1 k2 p1 p2 k3: %s" % " ".join("%+.5f" % v for v in dist),
              "hfov %.2f deg (design value 60), vfov %.2f deg" % (cj["hfov_deg"], cj["vfov_deg"]),
              "coverage %.2f of the %dx%d grid" % (cov, GRID[0], GRID[1]),
              "bands kept: %s" % {b: sum(acc[i]["band"] == b for i in idx) for b in ("close", "middle", "far")},
              "tilts kept: %s" % {t: sum(acc[i]["tilt"] == t for i in idx) for t in ("flat", "turned", "tipped", "slight")},
              "pass (>= 15 images, rms <= 1.0 px, coverage >= 0.8, fx/fy within 3 %%): %s" % (
                  len(idx) >= 15 and rms <= 1.0 and cov >= 0.8 and abs(fx / fy - 1) <= 0.03)]
    if args.out:
        with open(args.out, "w") as fh:
            json.dump(cj, fh, indent=1)
            fh.write("\n")
        lines.append("wrote %s" % args.out)
    text = "\n".join(lines)
    print(text)
    if args.report:
        with open(args.report, "w") as fh:
            fh.write(text + "\n")
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    lv = sub.add_parser("live")
    lv.add_argument("--session", required=True)
    lv.add_argument("--target", type=int, default=30)
    lv.add_argument("--coverage", type=float, default=0.8)
    lv.add_argument("--still-px", type=float, default=1.5)
    lv.add_argument("--say-every", type=float, default=7.0)
    lv.add_argument("--right-sign", type=int, default=0, choices=(-1, 0, 1), help="skip the direction check")
    lv.add_argument("--max-minutes", type=float, default=20)
    lv.add_argument("--skip-after", type=float, default=40, help="seconds on one position before skipping it")
    lv.add_argument("--free", action="store_true",
                    help="no target positions: keep every steady view that differs from the kept ones (board fixed "
                         "on a wall, the car held in the hands)")
    lv.add_argument("--hold", choices=("car", "board"), default="car", help="free mode: what the operator moves")
    lv.add_argument("--bands", help="four distance edges in metres, close|middle|far, e.g. 0.25,0.40,0.60,0.85")
    lv.add_argument("--picture-left", help="spoken words for the picture's left side, e.g. 'away from the closet door'")
    lv.add_argument("--picture-right", help="spoken words for the picture's right side")
    cal = sub.add_parser("calibrate")
    cal.add_argument("--session", required=True)
    cal.add_argument("--out")
    cal.add_argument("--report")
    for p in (lv, cal):
        p.add_argument("--cols", type=int, help="inner corners per row (default: the phone board's 12)")
        p.add_argument("--rows", type=int, help="inner corners per column (default 5)")
        p.add_argument("--square-m", type=float, help="square size in metres (default 0.009111)")
    args = ap.parse_args(argv)
    board_file = os.path.join(args.session, "calib", "board.json")
    if args.cmd == "calibrate" and os.path.exists(board_file) and not (args.cols or args.rows or args.square_m):
        b = json.load(open(board_file))                      # the board live used, unless given here
        configure(b["cols"], b["rows"], b["square_m"], b["bands"])
    else:
        sides = (args.picture_left, args.picture_right) if getattr(args, "picture_left", None) else None
        bands = [float(x) for x in args.bands.split(",")] if getattr(args, "bands", None) else None
        configure(args.cols, args.rows, args.square_m, bands, sides)
    args.square_m = SQUARE_M
    if args.cmd == "live":
        try:
            return live(args)
        except KeyboardInterrupt:          # stopped by the operator or by pkill -INT; accepted.jsonl is already flushed
            print("live: stopped", flush=True)
            return 0
    return calibrate(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
