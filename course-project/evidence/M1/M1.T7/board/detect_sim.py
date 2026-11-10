"""Simulated camera views of the phone checkerboard: does OpenCV find all corners, and how accurately?

M1.T7 board check, run on the Spark host (cv2 4.13, numpy). The lens is not calibrated yet, so the views
assume a 66 degree horizontal field of view (fx 1232 px at UXGA 1600 x 1200, 492.8 px at VGA 640 x 480).
Each view: the PNG framed by a 2.2 mm black bezel and a bright metal frame on a grey room, posed in 3-D,
rendered 4x supersampled and area-averaged, Gaussian blur sigma 1 px, noise sigma 3, JPEG quality 75.
Ground truth: the exact inner corners projected through the same homography. Classic =
findChessboardCorners + cornerSubPix with the half-window 0.4 x the smallest detected corner spacing
(at most 11); SB = findChessboardCornersSB (exhaustive, accuracy).

Usage: python3 detect_sim.py checkerboard_12x5_2868x1320.png checkerboard_12x5_2868x1320.json > detect_sim.txt

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote this check.
"""
import json
import math
import sys

import cv2
import numpy as np

png, side = sys.argv[1], sys.argv[2]
spec = json.load(open(side))
board = cv2.imread(png, cv2.IMREAD_GRAYSCALE)
H0, W0 = board.shape
s = spec["square_px"]
x0, y0 = spec["origin_px"]
cols, rows = spec["inner_corners"]
mm_px = 25.4 / spec["display"]["ppi"]

# phone: screen + 2.2 mm black bezel + 3 mm bright metal frame, on a mid-grey room
bez, frame = 40, 55
phone = np.full((H0 + 2 * (bez + frame), W0 + 2 * (bez + frame)), 200, np.uint8)
phone[frame:-frame, frame:-frame] = 8
phone[frame + bez:-(frame + bez), frame + bez:-(frame + bez)] = board
off = bez + frame
# ground-truth inner corners in phone-image pixel coordinates (pixel centres at integers)
gt = np.array([[off + x0 + (c + 1) * s - 0.5, off + y0 + (r + 1) * s - 0.5]
               for r in range(rows) for c in range(cols)], np.float64)


def view(res, fx, dist_m, yaw_deg, pitch_deg, du, dv, rng):
    w, h = res
    K = np.array([[fx, 0, w / 2], [0, fx, h / 2], [0, 0, 1]])
    ph, pw = phone.shape
    # phone plane coords (m) centred on the phone
    S = np.array([[mm_px / 1000, 0, -pw / 2 * mm_px / 1000], [0, mm_px / 1000, -ph / 2 * mm_px / 1000], [0, 0, 1]])
    a, b = math.radians(yaw_deg), math.radians(pitch_deg)
    Ry = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    Rx = np.array([[1, 0, 0], [0, math.cos(b), -math.sin(b)], [0, math.sin(b), math.cos(b)]])
    R = Ry @ Rx
    # place the centre at pixel offset (du, dv) as a fraction of the half-image
    t = np.array([du * (w / 2) / fx * dist_m, dv * (h / 2) / fx * dist_m, dist_m])
    Hm = K @ np.column_stack([R[:, 0], R[:, 1], t]) @ S
    S4 = np.array([[4, 0, 1.5], [0, 4, 1.5], [0, 0, 1]])
    big = cv2.warpPerspective(phone, S4 @ Hm, (4 * w, 4 * h), flags=cv2.INTER_LINEAR, borderValue=120)
    img = cv2.resize(big, (w, h), interpolation=cv2.INTER_AREA)
    img = cv2.GaussianBlur(img, (0, 0), 1.0)
    img = np.clip(img.astype(np.float32) + rng.normal(0, 3, img.shape), 0, 255).astype(np.uint8)
    ok, enc = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 75])
    img = cv2.imdecode(enc, cv2.IMREAD_GRAYSCALE)
    proj = cv2.perspectiveTransform(gt.reshape(-1, 1, 2), Hm).reshape(-1, 2)
    inside = (proj.min(0) > 0).all() and (proj[:, 0].max() < w) and (proj[:, 1].max() < h)
    sq_px = fx * spec["square_mm_predicted"] / 1000 / dist_m
    return img, proj, inside, sq_px


def detect(img, sq_px, sb):
    if sb:
        ok, c = cv2.findChessboardCornersSB(img, (cols, rows), cv2.CALIB_CB_NORMALIZE_IMAGE | cv2.CALIB_CB_EXHAUSTIVE
                                             | cv2.CALIB_CB_ACCURACY)
        return ok, (c.reshape(-1, 2) if ok else None)
    ok, c = cv2.findChessboardCorners(img, (cols, rows), cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE)
    if not ok:
        return ok, None
    g = c.reshape(rows, cols, 2)
    spacing = min(np.linalg.norm(np.diff(g, axis=1), axis=2).min(), np.linalg.norm(np.diff(g, axis=0), axis=2).min())
    half = max(2, min(11, int(0.4 * spacing)))
    c = cv2.cornerSubPix(img, c, (half, half), (-1, -1),
                         (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.001))
    return ok, c.reshape(-1, 2)


def err(found, proj):
    d = np.linalg.norm(found[:, None, :] - proj[None, :, :], axis=2)
    j = d.argmin(1)
    v = found - proj[j]
    BIAS.append(v.mean(0))
    nn = np.linalg.norm(v, axis=1)
    return float(np.sqrt((nn ** 2).mean())), float(nn.max())


BIAS = []
rng = np.random.default_rng(1)
print(f"cv2 {cv2.__version__}; board {cols}x{rows} inner corners, square {spec['square_mm_predicted']} mm")
print(f"{'res':5} {'d_m':>5} {'yaw':>4} {'pit':>4} {'pos':>9} {'sq_px':>6} | classic ok rms/max px | SB ok rms/max px")
cases = []
for res, fx, dists in [((1600, 1200), 1232.0, [0.15, 0.20, 0.30, 0.50, 0.70, 0.90, 1.10]),
                       ((640, 480), 492.8, [0.12, 0.18, 0.25, 0.35, 0.45, 0.55])]:
    for d in dists:
        for yaw, pit in [(0, 0), (40, 0), (0, 40), (30, 30)]:
            for du, dv in [(0, 0), (0.55, 0.55), (-0.6, -0.5)]:
                cases.append((res, fx, d, yaw, pit, du, dv))
summary = {}
for res, fx, d, yaw, pit, du, dv in cases:
    img, proj, inside, sq_px = view(res, fx, d, yaw, pit, du, dv, rng)
    if not inside:
        continue
    row = []
    for sb in (False, True):
        ok, found = detect(img, sq_px, sb)
        row.append((ok, err(found, proj) if ok else (math.nan, math.nan)))
    key = ("UXGA" if res[0] == 1600 else "VGA", d)
    summary.setdefault(key, []).append(row)
    tag = "UXGA" if res[0] == 1600 else "VGA"
    print(f"{tag:5} {d:5.2f} {yaw:4d} {pit:4d} {f'{du:+.2f},{dv:+.2f}':>9} {sq_px:6.1f} | "
          f"{'Y' if row[0][0] else 'n'} {row[0][1][0]:5.3f}/{row[0][1][1]:5.3f} | "
          f"{'Y' if row[1][0] else 'n'} {row[1][1][0]:5.3f}/{row[1][1][1]:5.3f}")
print("\nsummary (views with the whole board inside the image): found classic / SB of n, worst rms px")
for (tag, d), rows_ in summary.items():
    n = len(rows_)
    fc = sum(r[0][0] for r in rows_)
    fs = sum(r[1][0] for r in rows_)
    wc = max((r[0][1][0] for r in rows_ if r[0][0]), default=math.nan)
    ws = max((r[1][1][0] for r in rows_ if r[1][0]), default=math.nan)
    print(f"{tag:5} {d:5.2f} m: classic {fc}/{n} (worst rms {wc:.3f}), SB {fs}/{n} (worst rms {ws:.3f})")

b = np.array(BIAS); print(f"mean bias over all detections: dx {b[:,0].mean():+.3f} px, dy {b[:,1].mean():+.3f} px")
