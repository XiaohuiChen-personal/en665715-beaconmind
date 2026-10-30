#!/usr/bin/env python3
"""Draw AprilTag 36h11 markers for BeaconMind print files and synthetic frames.

Each print file is one tag36h11 marker plus a white border of one eighth of the
black side on every side (160 mm black becomes a 200 mm sheet). Canvas mode
pastes that same bordered tag, centred, on a mid-grey image.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote tag rendering, canvas paste, and the self-test.
Derived from: none (OpenCV library calls only).
"""

import argparse
import os
import sys
import tempfile

import cv2
import numpy as np


def black_side_px(black_mm, dpi):
    """Pixel width of the black square, forced to a multiple of the 8 tag cells."""
    return 8 * int(round(float(black_mm) / 25.4 * float(dpi) / 8.0))


def mm_from_px(px, dpi):
    return float(px) / float(dpi) * 25.4


def dictionary():
    return cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)


def render_marker(tag_id, side_px):
    marker = cv2.aruco.generateImageMarker(dictionary(), int(tag_id), int(side_px))
    if marker is None or marker.shape[0] != side_px or marker.shape[1] != side_px:
        raise RuntimeError(
            "generateImageMarker returned an unexpected image for id {0}".format(tag_id)
        )
    return marker


def add_white_border(marker):
    side = int(marker.shape[0])
    border = side // 8
    return cv2.copyMakeBorder(
        marker, border, border, border, border, cv2.BORDER_CONSTANT, value=255
    ), border


def print_name(tag_id, black_mm, dpi):
    return "tag36h11_{0}_black{1}mm_{2}dpi.png".format(int(tag_id), int(black_mm), int(dpi))


def canvas_name(tag_id, width, height, tag_px):
    return "tag36h11_{0}_canvas{1}x{2}_tag{3}px.png".format(
        int(tag_id), int(width), int(height), int(tag_px)
    )


def measured_black_width(path):
    image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise RuntimeError("could not read {0}".format(path))
    columns = (image < 128).any(axis=0)
    return int(columns.sum())


def write_print_tag(out_dir, tag_id, black_mm, dpi):
    side = black_side_px(black_mm, dpi)
    bordered, border = add_white_border(render_marker(tag_id, side))
    name = print_name(tag_id, black_mm, dpi)
    path = os.path.join(out_dir, name)
    if not cv2.imwrite(path, bordered):
        raise RuntimeError("could not write {0}".format(path))
    total = side + 2 * border
    line = (
        "{0} id={1} black_side_px={2} white_border_px={3} total_side_px={4} "
        "black_side_mm={5:.2f} total_side_mm={6:.2f}"
    ).format(
        name,
        int(tag_id),
        side,
        border,
        total,
        mm_from_px(side, dpi),
        mm_from_px(total, dpi),
    )
    return path, line


def write_canvas_tag(out_dir, tag_id, width, height, tag_px):
    bordered, border = add_white_border(render_marker(tag_id, tag_px))
    tag_h, tag_w = bordered.shape[:2]
    if tag_w > width or tag_h > height:
        raise RuntimeError(
            "tag {0}x{1} does not fit on a {2}x{3} canvas".format(tag_w, tag_h, width, height)
        )
    canvas = np.full((int(height), int(width)), 128, dtype=np.uint8)
    x0 = (int(width) - tag_w) // 2
    y0 = (int(height) - tag_h) // 2
    canvas[y0 : y0 + tag_h, x0 : x0 + tag_w] = bordered
    name = canvas_name(tag_id, width, height, tag_px)
    path = os.path.join(out_dir, name)
    if not cv2.imwrite(path, canvas):
        raise RuntimeError("could not write {0}".format(path))
    line = (
        "{0} id={1} black_side_px={2} white_border_px={3} total_tag_px={4} canvas={5}x{6}"
    ).format(name, int(tag_id), int(tag_px), border, tag_w, int(width), int(height))
    return path, line


def write_size_list(out_dir, lines):
    path = os.path.join(out_dir, "expected_printed_sizes.txt")
    header = (
        "# black square plus a white border of 1/8 of the black side on every side\n"
        "# black_side_px = 8 * round(black_mm / 25.4 * dpi / 8); 160 mm at 300 dpi -> 1888 px = 159.85 mm\n"
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(header)
        for line in lines:
            handle.write(line + "\n")
    return path


def generate(out_dir, ids, black_mm, dpi, canvas_px, tag_px):
    os.makedirs(out_dir, exist_ok=True)
    lines = []
    paths = []
    for tag_id in ids:
        if canvas_px is None:
            path, line = write_print_tag(out_dir, tag_id, black_mm, dpi)
        else:
            path, line = write_canvas_tag(out_dir, tag_id, canvas_px[0], canvas_px[1], tag_px)
        paths.append(path)
        lines.append(line)
    write_size_list(out_dir, lines)
    return paths


def decode_ids(path):
    image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    detector = cv2.aruco.ArucoDetector(dictionary())
    _corners, ids, _rejected = detector.detectMarkers(image)
    if ids is None:
        return []
    return [int(value) for value in np.asarray(ids).flatten()]


def selftest():
    out_dir = tempfile.mkdtemp(prefix="bm-tags-")
    try:
        ids = [0, 1, 2, 3]
        paths = generate(out_dir, ids, 160.0, 300, None, None)
        decoded = 0
        for tag_id, path in zip(ids, paths):
            found = decode_ids(path)
            width = measured_black_width(path)
            if found != [tag_id]:
                raise SystemExit(
                    "selftest failed: {0} decoded {1}, expected [{2}]".format(path, found, tag_id)
                )
            if abs(width - 1888) > 1:
                raise SystemExit(
                    "selftest failed: {0} black side {1} px, expected 1888".format(path, width)
                )
            decoded += 1
        print("selftest ok: {0}/4 ids decoded, black side 1888 px".format(decoded))
    finally:
        for name in os.listdir(out_dir):
            os.remove(os.path.join(out_dir, name))
        os.rmdir(out_dir)


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Draw tag36h11 markers.")
    parser.add_argument("--ids", type=int, nargs="+", help="tag ids to draw")
    parser.add_argument("--black-mm", type=float, default=160.0, help="black-square edge in millimetres")
    parser.add_argument("--dpi", type=int, default=300, help="print resolution")
    parser.add_argument("--out", help="output directory")
    parser.add_argument("--canvas-px", type=int, nargs=2, metavar=("W", "H"), help="canvas width and height")
    parser.add_argument("--tag-px", type=int, help="black-square side in pixels for canvas mode")
    parser.add_argument("--selftest", action="store_true", help="decode ids 0-3 and check the 1888 px black side")
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    if args.selftest:
        selftest()
        return 0
    if not args.ids or not args.out:
        raise SystemExit("make_tags.py requires --ids and --out (or --selftest)")
    if (args.canvas_px is None) != (args.tag_px is None):
        raise SystemExit("--canvas-px and --tag-px must be given together")
    generate(args.out, args.ids, args.black_mm, args.dpi, args.canvas_px, args.tag_px)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
