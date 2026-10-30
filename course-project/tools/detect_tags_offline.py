#!/usr/bin/env python3
"""Decode tag36h11 markers in still images and estimate range with solvePnP.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: recorded the Qwen3.8 pin, deferred Bonsai, and started M1.T5.
Derived from: course-project/tools/make_tags.py (canvas self-test only).
"""

import argparse
import json
import math
import os
import sys
import tempfile

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_tags


def detector():
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
    return cv2.aruco.ArucoDetector(dictionary)


def object_corners(black_m):
    half = float(black_m) / 2.0
    # OpenCV IPPE_SQUARE order: top-left, top-right, bottom-right, bottom-left.
    return np.array(
        [[-half, half, 0.0], [half, half, 0.0], [half, -half, 0.0], [-half, -half, 0.0]],
        dtype=np.float32,
    )


def load_intrinsics(path):
    with open(path, encoding="utf-8") as handle:
        doc = json.load(handle)
    matrix = np.array(
        [[doc["fx"], 0.0, doc["cx"]], [0.0, doc["fy"], doc["cy"]], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )
    return matrix, np.zeros((5, 1), dtype=np.float64)


def pose_of(corners, black_m, camera_matrix, dist):
    image_points = np.asarray(corners, dtype=np.float32).reshape(4, 2)
    ok, _rvec, tvec = cv2.solvePnP(
        object_corners(black_m),
        image_points,
        camera_matrix,
        dist,
        flags=cv2.SOLVEPNP_IPPE_SQUARE,
    )
    if not ok:
        return None
    vec = np.asarray(tvec, dtype=np.float64).reshape(3)
    range_m = float(np.linalg.norm(vec))
    bearing_deg = math.degrees(math.atan2(float(vec[0]), float(vec[2])))
    return range_m, bearing_deg


def rows_for_image(path, black_m, camera_matrix, dist):
    image = cv2.imread(path, cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError("could not read {0}".format(path))
    _corners, ids, _rejected = detector().detectMarkers(image)
    name = os.path.basename(path)
    if ids is None:
        return ["{0},,,".format(name)]
    lines = []
    for index, tag_id in enumerate(np.asarray(ids).flatten()):
        pose = pose_of(_corners[index], black_m, camera_matrix, dist)
        if pose is None:
            lines.append("{0},{1},,".format(name, int(tag_id)))
            continue
        range_m, bearing_deg = pose
        lines.append("{0},{1},{2:.4f},{3:.3f}".format(name, int(tag_id), range_m, bearing_deg))
    return lines


def selftest():
    out_dir = tempfile.mkdtemp(prefix="bm-detect-")
    try:
        paths = make_tags.generate(out_dir, [3], 160.0, 300, (800, 600), 160)
        fx = fy = 693.0
        cx, cy = 400.0, 300.0
        matrix = np.array([[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]], dtype=np.float64)
        dist = np.zeros((5, 1), dtype=np.float64)
        image = cv2.imread(paths[0], cv2.IMREAD_COLOR)
        _corners, ids, _rejected = detector().detectMarkers(image)
        if ids is None or [int(v) for v in np.asarray(ids).flatten()] != [3]:
            raise SystemExit("selftest failed: ids {0}".format(ids))
        range_m, bearing_deg = pose_of(_corners[0], 0.16, matrix, dist)
        pinhole = 693.0 * 0.16 / 160.0
        if abs(range_m - pinhole) / pinhole > 0.02 or abs(bearing_deg) >= 0.5:
            raise SystemExit(
                "selftest failed: range {0:.4f} pinhole {1:.4f} bearing {2:.3f}".format(
                    range_m, pinhole, bearing_deg
                )
            )
        print(
            "selftest ok: id 3, range {0:.3f} m (pinhole {1:.3f} m), bearing {2:.1f} deg".format(
                range_m, pinhole, bearing_deg
            )
        )
    finally:
        for name in os.listdir(out_dir):
            os.remove(os.path.join(out_dir, name))
        os.rmdir(out_dir)


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Decode tag36h11 stills.")
    parser.add_argument("images", nargs="*")
    parser.add_argument("--family", default="36h11")
    parser.add_argument("--black-m", type=float, default=0.16)
    parser.add_argument("--intrinsics", default="")
    parser.add_argument("--selftest", action="store_true")
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    if args.family != "36h11":
        raise SystemExit("only family 36h11 is implemented")
    if args.selftest:
        selftest()
        return 0
    if not args.images or not args.intrinsics:
        raise SystemExit("detect_tags_offline.py needs images and --intrinsics, or --selftest")
    camera_matrix, dist = load_intrinsics(args.intrinsics)
    for path in args.images:
        for line in rows_for_image(path, args.black_m, camera_matrix, dist):
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
