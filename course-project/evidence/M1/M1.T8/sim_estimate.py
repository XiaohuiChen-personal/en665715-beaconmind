#!/usr/bin/env python3
"""SIMULATED estimate of the tag detector's range and bearing error against distance (plan task M1.T8, before the
real pilot). Nothing here is a measurement of the real camera.

    python3 course-project/evidence/M1/M1.T8/sim_estimate.py [--n 40] [--out course-project/evidence/M1/M1.T8]

Part 1, image effects (random, per frame). A 160 mm tag36h11 tag is drawn through configs/camera.json (lens distortion
and mount angles included; beaconmind.perception.synth) at a random bearing inside the picture, turned up to 30 degrees
on its wall, then blurred, given sensor noise and JPEG-compressed, and detected with beaconmind.perception.tags. The
conditions are listed in CONDITIONS; "real-like" uses the levels measured from real bm_cam-0.2 XGA frames
(synth.REAL_FRAME_2026_11_18). Wall tags hang 0.23 m up and are whole in the picture only from about 0.8 m, so the
rows below that distance use a tag held low (0.095 m), as a bench stand would.

Part 2, calibration effects (systematic, the same for a whole session). The four corner pixels of a tag are computed
exactly with the camera file, then the pose is solved with a camera whose one parameter is off by its recorded
uncertainty. No picture is drawn for this part.

Writes sim-estimate-image.csv, sim-estimate-calibration.csv and sim-estimate-output.txt next to this script (or --out).

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this script.
"""
import argparse
import csv
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

DISTANCES = (0.4, 0.5, 0.6, 0.8, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5)
FAR = (4.0, 5.0, 6.0, 7.0, 8.0)
LOOK = dict(wall=150.0, black=100.0, white=185.0)
CONDITIONS = (
    ("real-like", "blur 0.75 px, noise 2, JPEG q62 (camera quality 12)", {}, {}),
    ("soft and noisy", "blur 1.5 px, noise 4, JPEG q62", {"blur_sigma_px": 1.5, "noise_sigma": 4.0}, {}),
    ("still moving", "real-like plus 5 px horizontal motion blur", {"motion_px": 5.0}, {}),
    ("tone curve", "real-like, blur applied in linear light (gamma 2.2)", {"gamma": 2.2}, {}),
    ("dim", "real-like at a third of the contrast (black 120, white 148), noise 3", {"noise_sigma": 3.0},
     {"wall": 135.0, "black": 120.0, "white": 148.0}),
)


def height_for(range_m):
    return 0.23 if range_m >= 0.78 else 0.095


def random_tag(camera, rng, range_m, max_incidence=30.0):
    """A tag at about range_m, at a random bearing where it is whole in the picture, turned on its wall."""
    half = 0.08 if range_m < 0.5 else 0.10
    for _ in range(200):
        r = range_m * (1.0 + rng.uniform(-0.02, 0.02))
        bearing = rng.uniform(-22.0, 22.0)
        inc = rng.uniform(-max_incidence, max_incidence) if range_m >= 0.6 else 0.0
        if cm.square_in_view(camera, r, bearing, height_for(range_m), half, margin_px=6.0, incidence_deg=inc):
            return synth.tag_at(int(rng.integers(0, 30)), r, bearing, height_for(range_m), incidence_deg=inc), r, bearing
    raise RuntimeError("no placement in view at %.2f m" % range_m)


def image_part(camera, n, seed):
    rows = []
    for name, _text, changes, look in CONDITIONS:
        rng = np.random.default_rng(seed)
        values = dict(LOOK)
        values.update(look)
        for range_m in DISTANCES + (FAR if name == "real-like" else ()):
            er, eb, sides, quals, wrong = [], [], [], [], 0
            for _ in range(n):
                tag, r, bearing = random_tag(camera, rng, range_m)
                frame = synth.real_like(synth.render_scene(camera, [tag], **values), rng=rng, **changes)
                dets = tags.detect_tags(frame, camera)
                good = [d for d in dets if d["id"] == tag["id"]]
                wrong += len(dets) - len(good)
                if good:
                    er.append(good[0]["range_m"] - r)
                    eb.append(good[0]["bearing_deg"] - bearing)
                    sides.append(good[0]["side_px"])
                    quals.append(good[0]["quality"])
            row = {"condition": name, "range_m": range_m, "tag_height_m": height_for(range_m), "n": n,
                   "detected": len(er), "wrong_id": wrong}
            if er:
                er, eb = np.array(er), np.array(eb)
                row.update({"side_px": round(float(np.mean(sides)), 1), "quality_median": round(float(np.median(quals)), 2),
                            "range_err_mean_m": round(float(er.mean()), 4),
                            "range_err_sd_m": round(float(er.std(ddof=1)), 4) if len(er) > 1 else 0.0,
                            "range_err_p95_abs_m": round(float(np.percentile(np.abs(er), 95)), 4),
                            "bearing_err_mean_deg": round(float(eb.mean()), 3),
                            "bearing_err_sd_deg": round(float(eb.std(ddof=1)), 3) if len(eb) > 1 else 0.0,
                            "bearing_err_p95_abs_deg": round(float(np.percentile(np.abs(eb), 95)), 3)})
            rows.append(row)
            print("  %-15s %.2f m  detected %d/%d" % (name, range_m, len(er), n), flush=True)
    return rows


def solve_with(camera_true, camera_used, range_m, bearing_deg, tag_size_true=0.16, tag_size_used=0.16):
    """Range and bearing the detector's geometry gives when the picture comes from camera_true and the pose is solved
    with camera_used (exact corner pixels, no image noise)."""
    tag = synth.tag_at(3, range_m, bearing_deg, 0.23, size_m=tag_size_true)
    pix = synth.tag_corners_px(camera_true, tag)
    k, d = np.array(camera_used.camera_matrix), np.array(camera_used.dist)
    norm = cv2.undistortPoints(pix.reshape(-1, 1, 2), k, d).reshape(-1, 2)
    best = None
    for rvec, tvec in tags._poses(norm, tag_size_used):
        fields = tags._pose_fields(camera_used, rvec, tvec)
        proj, _ = cv2.projectPoints(tags.object_corners(tag_size_used), rvec, tvec, k, d)
        err = float(np.sqrt(np.mean(np.sum((proj.reshape(4, 2) - pix) ** 2, axis=1))))
        if best is None or err < best[0]:
            best = (err, fields)
    return best[1]["range_m"], best[1]["bearing_deg"]


def scaled(camera, **changes):
    values = {n: getattr(camera, n) for n in ("width", "height", "fx", "fy", "cx", "cy", "dist", "x_m", "y_m", "z_m",
                                               "roll_deg", "pitch_deg", "yaw_deg")}
    values.update(changes)
    return cm.Camera(**values)


def calibration_part(camera):
    k1, k2, p1, p2, k3 = camera.dist
    cases = (
        ("focal length +1 % (the two tape checks read -0.1 % and -1.2 %)", scaled(camera, fx=camera.fx * 1.01, fy=camera.fy * 1.01), 0.16),
        ("principal point cx +5 px", scaled(camera, cx=camera.cx + 5.0), 0.16),
        ("principal point cy +5 px", scaled(camera, cy=camera.cy + 5.0), 0.16),
        ("distortion k1 and k2 set to zero (worst case for the picture's edges)", scaled(camera, dist=(0.0, 0.0, p1, p2, k3)), 0.16),
        ("mount yaw +2 deg (uncertainty_deg in camera.json)", scaled(camera, yaw_deg=camera.yaw_deg + 2.0), 0.16),
        ("mount pitch +2 deg", scaled(camera, pitch_deg=camera.pitch_deg + 2.0), 0.16),
        ("mount roll +2 deg", scaled(camera, roll_deg=camera.roll_deg + 2.0), 0.16),
        ("lens position x +5 mm (uncertainty_m in camera.json)", scaled(camera, x_m=camera.x_m + 0.005), 0.16),
        ("tag size given 1 mm too large (a 160 mm black square entered as 161 mm)", camera, 0.161),
    )
    rows = []
    for text, used, size_used in cases:
        for range_m in (1.0, 2.0, 3.0):
            for bearing in (0.0, 15.0):
                r, b = solve_with(camera, used, range_m, bearing, tag_size_used=size_used)
                rows.append({"perturbation": text, "range_m": range_m, "bearing_deg": bearing,
                             "range_err_m": round(r - range_m, 4), "bearing_err_deg": round(b - bearing, 3)})
    return rows


def write_csv(path, rows):
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(argv):
    parser = argparse.ArgumentParser(description="SIMULATED range and bearing error of the tag detector.")
    parser.add_argument("--n", type=int, default=40, help="frames per distance and condition")
    parser.add_argument("--seed", type=int, default=20261118)
    parser.add_argument("--out", default=HERE)
    args = parser.parse_args(argv)
    camera = cm.load_camera()
    t0 = time.time()
    lines = ["SIMULATED tag-detector error estimate (evidence/M1/M1.T8/sim_estimate.py). Not a measurement.",
             "OpenCV %s, numpy %s, %d frames per distance and condition, seed %d" % (cv2.__version__, np.__version__, args.n, args.seed),
             "camera: %s, %d x %d, HFOV %.1f, VFOV %.1f, mount roll %+.1f pitch %+.1f yaw %+.1f"
             % (os.path.basename(camera.source), camera.width, camera.height, camera.hfov_deg, camera.vfov_deg,
                camera.roll_deg, camera.pitch_deg, camera.yaw_deg), ""]
    lines.append("Whole-tag distance from the axle midpoint for a wall tag (centre 0.23 m up), by bearing:")
    for half, label in ((0.08, "black square"), (0.10, "with white border")):
        cells = []
        for bearing in (-15, -10, -5, 0, 5, 10, 15):
            v = cm.min_full_view_range(camera, 0.23, half, float(bearing))
            cells.append("%+d deg: %s" % (bearing, "never" if v is None else "%.2f m" % v))
        lines.append("  %-18s %s" % (label, "; ".join(cells)))
    edges = camera.view_edges_deg()
    lines.append("  view through the lens model: %.1f deg left, %.1f right, %.1f up, %.1f down of the optical axis"
                 % (edges["left"], edges["right"], edges["up"], edges["down"]))
    lines.append("")
    image_rows = image_part(camera, args.n, args.seed)
    write_csv(os.path.join(args.out, "sim-estimate-image.csv"), image_rows)
    for name, text, _c, _l in CONDITIONS:
        lines.append("Image effects, condition '%s': %s" % (name, text))
        lines.append("  range  height  side    rate    range err m: mean      sd  p95|e|   bearing err deg: mean     sd  p95|e|  quality")
        for row in image_rows:
            if row["condition"] != name:
                continue
            if row["detected"]:
                lines.append("  %5.2f  %5.3f  %4.0f  %3d/%-3d              %+.4f  %.4f  %.4f                  %+.3f  %.3f   %.3f     %.2f%s"
                             % (row["range_m"], row["tag_height_m"], row["side_px"], row["detected"], row["n"],
                                row["range_err_mean_m"], row["range_err_sd_m"], row["range_err_p95_abs_m"],
                                row["bearing_err_mean_deg"], row["bearing_err_sd_deg"], row["bearing_err_p95_abs_deg"],
                                row["quality_median"], "  wrong ids: %d" % row["wrong_id"] if row["wrong_id"] else ""))
            else:
                lines.append("  %5.2f  %5.3f     -    0/%-3d" % (row["range_m"], row["tag_height_m"], row["n"]))
        lines.append("")
    cal_rows = calibration_part(camera)
    write_csv(os.path.join(args.out, "sim-estimate-calibration.csv"), cal_rows)
    lines.append("Calibration effects (exact corners, one parameter off at a time): range error m / bearing error deg")
    lines.append("  %-78s %-27s %-27s %-27s" % ("", "1 m (bearing 0 | 15 deg)", "2 m (bearing 0 | 15 deg)", "3 m (bearing 0 | 15 deg)"))
    texts = []
    for row in cal_rows:
        if row["perturbation"] not in texts:
            texts.append(row["perturbation"])
    for text in texts:
        cells = []
        for range_m in (1.0, 2.0, 3.0):
            pair = [r for r in cal_rows if r["perturbation"] == text and r["range_m"] == range_m]
            cells.append(" | ".join("%+.3f %+.2f" % (r["range_err_m"], r["bearing_err_deg"]) for r in pair))
        lines.append("  %-78s %-27s %-27s %-27s" % (text[:78], cells[0], cells[1], cells[2]))
    lines.append("")
    lines.append("run time %.0f s" % (time.time() - t0))
    text = "\n".join(lines) + "\n"
    with open(os.path.join(args.out, "sim-estimate-output.txt"), "w", encoding="utf-8") as handle:
        handle.write(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
