#!/usr/bin/env python3
"""SIMULATED comparison of smaller wall tags (plan task M1.T8; the near limit of evidence/M1/M1.T8/sim-estimate.md).
Nothing here is a measurement of the real camera.

    python3 course-project/evidence/M1/M1.T8/sim_tag_sizes.py [--n 40] [--out course-project/evidence/M1/M1.T8]

The camera stays as mounted (configs/camera.json). Each alternative tag is a tag36h11 black square of side s with a
white border of s/8 on every side, its sheet's bottom edge on the top of the 0.12 m baseboard, so its centre is
0.12 + 0.625 s above the floor. For each size:

1. geometry: the range from the axle midpoint from which the whole black square (and the whole sheet) is in the
   picture, straight ahead and at 10 and 15 degrees to each side (beaconmind.camera_model.min_full_view_range, tag
   facing the axle midpoint, 2 px margin);
2. far behaviour: "real-like" simulated frames (as sim_estimate.py: blur 0.75 px, noise 2, JPEG q62, black 100, white
   185, wall 150; random bearing in view, turned up to 30 degrees on the wall), detection rate and range error at
   1.5 to 3.5 m, then outward in 0.25 m steps until the detection rate falls below 95 % (the detector's 6 m range
   rule is lifted for this, so the picture decides);
3. calibration: exact corners solved with one camera parameter off (focal length 1 %, lens position 5 mm, pitch 2
   degrees, tag size 0.5 mm, principal point 5 px, roll 2 degrees, yaw 2 degrees), and the tone-curve range bias
   (gamma 2.2, 20 frames), combined by root sum of squares as in sim-estimate.md.

Writes sim-tag-sizes.csv, sim-tag-sizes-far.csv and sim-tag-sizes-output.txt.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this script.
"""
import argparse
import csv
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
COURSE = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(COURSE, "beaconmind", "src"))

import cv2                                                     # noqa: E402
import numpy as np                                             # noqa: E402

from beaconmind import camera_model as cm                      # noqa: E402
from beaconmind.perception import synth, tags                  # noqa: E402

BASEBOARD_M = 0.12
SIZES_M = (0.16, 0.14, 0.12, 0.10, 0.08)
BEARINGS = (-15.0, -10.0, 0.0, 10.0, 15.0)
RANGES = (1.5, 2.0, 2.5, 3.0, 3.5)
LOOK = dict(wall=150.0, black=100.0, white=185.0)


def centre_height(size_m):
    return BASEBOARD_M + 0.625 * size_m


def random_tag(camera, rng, range_m, size_m, height_m):
    for _ in range(400):
        r = range_m * (1.0 + rng.uniform(-0.02, 0.02))
        bearing = rng.uniform(-22.0, 22.0)
        inc = rng.uniform(-30.0, 30.0)
        if cm.square_in_view(camera, r, bearing, height_m, 0.625 * size_m, margin_px=6.0, incidence_deg=inc):
            return synth.tag_at(int(rng.integers(0, 30)), r, bearing, height_m, incidence_deg=inc, size_m=size_m), r, bearing
    raise RuntimeError("no placement in view at %.2f m" % range_m)


def frames_at(camera, rng, range_m, size_m, n, **changes):
    """(detected, range errors, bearing errors, side px, quality) over n simulated frames."""
    height = centre_height(size_m)
    er, eb, sides, quals = [], [], [], []
    for _ in range(n):
        tag, r, bearing = random_tag(camera, rng, range_m, size_m, height)
        frame = synth.real_like(synth.render_scene(camera, [tag], **LOOK), rng=rng, **changes)
        # max_range_m is lifted (default 6 m) so that the picture, not that rule, decides where detection ends
        good = [d for d in tags.detect_tags(frame, camera, tag_size_m=size_m, max_range_m=50.0) if d["id"] == tag["id"]]
        if good:
            er.append(good[0]["range_m"] - r)
            eb.append(good[0]["bearing_deg"] - bearing)
            sides.append(good[0]["side_px"])
            quals.append(good[0]["quality"])
    return len(er), np.array(er), np.array(eb), sides, quals


def solve_with(camera_true, camera_used, range_m, bearing_deg, size_m, size_used):
    tag = synth.tag_at(3, range_m, bearing_deg, centre_height(size_m), size_m=size_m)
    pix = synth.tag_corners_px(camera_true, tag)
    k, d = np.array(camera_used.camera_matrix), np.array(camera_used.dist)
    norm = cv2.undistortPoints(pix.reshape(-1, 1, 2), k, d).reshape(-1, 2)
    best = None
    for rvec, tvec in tags._poses(norm, size_used):
        fields = tags._pose_fields(camera_used, rvec, tvec)
        proj, _ = cv2.projectPoints(tags.object_corners(size_used), rvec, tvec, k, d)
        err = float(np.sqrt(np.mean(np.sum((proj.reshape(4, 2) - pix) ** 2, axis=1))))
        if best is None or err < best[0]:
            best = (err, fields)
    return best[1]["range_m"] - range_m, best[1]["bearing_deg"] - bearing_deg


def changed(camera, **changes):
    values = {n: getattr(camera, n) for n in ("width", "height", "fx", "fy", "cx", "cy", "dist", "x_m", "y_m", "z_m",
                                               "roll_deg", "pitch_deg", "yaw_deg")}
    values.update(changes)
    return cm.Camera(**values)


def budget(camera, size_m, range_m, noise_sd_m, noise_sd_deg, tone_bias_m):
    """(range 1-sigma m, its parts, bearing without yaw deg, bearing with a 2 degree yaw error deg)."""
    focal = changed(camera, fx=camera.fx * 1.01, fy=camera.fy * 1.01)
    parts = {
        "focal 1 %": solve_with(camera, focal, range_m, 0.0, size_m, size_m)[0],
        "lens x 5 mm": solve_with(camera, changed(camera, x_m=camera.x_m + 0.005), range_m, 0.0, size_m, size_m)[0],
        "pitch 2 deg": solve_with(camera, changed(camera, pitch_deg=camera.pitch_deg + 2.0), range_m, 0.0, size_m, size_m)[0],
        "tag size 0.5 mm": solve_with(camera, camera, range_m, 0.0, size_m, size_m + 0.0005)[0],
        "tone curve": tone_bias_m,
        "frame noise": noise_sd_m,
    }
    rng_sigma = math.sqrt(sum(v * v for v in parts.values()))
    b_parts = [solve_with(camera, changed(camera, cx=camera.cx + 5.0), range_m, 0.0, size_m, size_m)[1],
               solve_with(camera, changed(camera, roll_deg=camera.roll_deg + 2.0), range_m, 0.0, size_m, size_m)[1],
               solve_with(camera, focal, range_m, 15.0, size_m, size_m)[1], noise_sd_deg]
    b0 = math.sqrt(sum(v * v for v in b_parts))
    yaw = solve_with(camera, changed(camera, yaw_deg=camera.yaw_deg + 2.0), range_m, 0.0, size_m, size_m)[1]
    return rng_sigma, parts, b0, math.hypot(b0, yaw)


def main(argv):
    parser = argparse.ArgumentParser(description="SIMULATED comparison of smaller wall tags.")
    parser.add_argument("--n", type=int, default=40)
    parser.add_argument("--seed", type=int, default=20261118)
    parser.add_argument("--out", default=HERE)
    args = parser.parse_args(argv)
    camera = cm.load_camera()
    t0 = time.time()
    rows, far_rows = [], []
    lines = ["SIMULATED comparison of wall-tag sizes (evidence/M1/M1.T8/sim_tag_sizes.py). Not a measurement.",
             "OpenCV %s, %d frames per cell, seed %d; camera as mounted (roll %+.1f pitch %+.1f yaw %+.1f)"
             % (cv2.__version__, args.n, args.seed, camera.roll_deg, camera.pitch_deg, camera.yaw_deg),
             "sheet bottom on the %.2f m baseboard, white border 1/8 of the black side" % BASEBOARD_M, ""]
    for size in SIZES_M:
        height = centre_height(size)
        row = {"black_side_mm": round(size * 1000), "centre_height_m": round(height, 4),
               "sheet_top_m": round(height + 0.625 * size, 4)}
        for bearing in BEARINGS:
            for half, key in ((size / 2.0, "black"), (0.625 * size, "sheet")):
                v = cm.min_full_view_range(camera, height, half, bearing)
                row["near_%s_%+d_m" % (key, bearing)] = "" if v is None else round(v, 3)
        rng = np.random.default_rng(args.seed)
        noise = {}
        for range_m in RANGES:
            n_det, er, eb, sides, quals = frames_at(camera, rng, range_m, size, args.n)
            noise[range_m] = (float(er.std(ddof=1)) if n_det > 1 else 0.0, float(eb.std(ddof=1)) if n_det > 1 else 0.0)
            row["rate_%.1f" % range_m] = round(n_det / args.n, 3)
            row["range_err_mean_mm_%.1f" % range_m] = round(1000 * float(er.mean()), 1) if n_det else ""
            row["range_err_sd_mm_%.1f" % range_m] = round(1000 * noise[range_m][0], 1) if n_det else ""
            far_rows.append({"black_side_mm": row["black_side_mm"], "range_m": range_m, "detected": n_det, "n": args.n,
                             "side_px": round(float(np.mean(sides)), 1) if sides else "",
                             "quality_median": round(float(np.median(quals)), 2) if quals else ""})
            print("  %3d mm  %.2f m  %d/%d" % (row["black_side_mm"], range_m, n_det, args.n), flush=True)
        # outward until the rate falls below 95 %
        below, range_m, last_ok = None, RANGES[-1], RANGES[-1] if row["rate_%.1f" % RANGES[-1]] >= 0.95 else None
        for r in RANGES:
            if row["rate_%.1f" % r] < 0.95 and below is None:
                below = r
        while below is None and range_m < 12.0:
            range_m += 0.25
            n_det, er, eb, sides, quals = frames_at(camera, rng, range_m, size, args.n)
            far_rows.append({"black_side_mm": row["black_side_mm"], "range_m": range_m, "detected": n_det, "n": args.n,
                             "side_px": round(float(np.mean(sides)), 1) if sides else "",
                             "quality_median": round(float(np.median(quals)), 2) if quals else ""})
            print("  %3d mm  %.2f m  %d/%d" % (row["black_side_mm"], range_m, n_det, args.n), flush=True)
            if n_det / args.n < 0.95:
                below = range_m
            else:
                last_ok = range_m
        row["last_range_at_95pct_m"] = last_ok if last_ok is not None else ""
        row["first_range_below_95pct_m"] = below if below is not None else ""
        px = [f["side_px"] for f in far_rows if f["black_side_mm"] == row["black_side_mm"] and f["range_m"] == last_ok]
        row["side_px_at_last_95pct"] = px[0] if px else ""
        for range_m in (2.0, 3.0):
            n_det, er, _eb, _s, _q = frames_at(camera, rng, range_m, size, max(args.n // 2, 4), gamma=2.2)
            tone = float(er.mean()) if n_det else 0.0
            sigma, parts, b0, b_yaw = budget(camera, size, range_m, noise[range_m][0], noise[range_m][1], tone)
            row["range_sigma_mm_%.0fm" % range_m] = round(1000 * sigma, 1)
            row["range_parts_mm_%.0fm" % range_m] = " / ".join("%.0f" % (1000 * abs(v)) for v in parts.values())
            row["bearing_sigma_deg_%.0fm" % range_m] = round(b0, 2)
            row["bearing_sigma_with_yaw_deg_%.0fm" % range_m] = round(b_yaw, 2)
        rows.append(row)
        lines.append("black side %d mm: centre %.4f m, sheet top %.3f m" % (row["black_side_mm"], height, row["sheet_top_m"]))
        lines.append("  near limit, black square (sheet): " + "; ".join(
            "%+d deg %s (%s)" % (b, row["near_black_%+d_m" % b], row["near_sheet_%+d_m" % b]) for b in BEARINGS))
        lines.append("  detection rate / range error mean, sd (mm): " + "; ".join(
            "%.1f m %.0f %% %s, %s" % (r, 100 * row["rate_%.1f" % r], row["range_err_mean_mm_%.1f" % r], row["range_err_sd_mm_%.1f" % r])
            for r in RANGES))
        lines.append("  detection at or above 95 %% out to %s m (tag %s px wide there); below 95 %% at %s m"
                     % (row["last_range_at_95pct_m"], row["side_px_at_last_95pct"], row["first_range_below_95pct_m"]))
        for range_m in (2.0, 3.0):
            lines.append("  %.0f m: range 1 sigma %.1f mm (focal / lens x / pitch / size / tone / noise: %s); bearing %.2f deg, "
                         "%.2f deg with a 2 deg yaw error"
                         % (range_m, row["range_sigma_mm_%.0fm" % range_m], row["range_parts_mm_%.0fm" % range_m],
                            row["bearing_sigma_deg_%.0fm" % range_m], row["bearing_sigma_with_yaw_deg_%.0fm" % range_m]))
        lines.append("")
    lines.append("run time %.0f s" % (time.time() - t0))
    for name, data in (("sim-tag-sizes.csv", rows), ("sim-tag-sizes-far.csv", far_rows)):
        with open(os.path.join(args.out, name), "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(data[0].keys()))
            writer.writeheader()
            writer.writerows(data)
    text = "\n".join(lines) + "\n"
    with open(os.path.join(args.out, "sim-tag-sizes-output.txt"), "w", encoding="utf-8") as handle:
        handle.write(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
