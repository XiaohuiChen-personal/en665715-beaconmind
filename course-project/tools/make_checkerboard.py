#!/usr/bin/env python3
"""Draw a checkerboard calibration target for a phone screen, at the screen's native resolution (M1.T7).

The board is shown full screen on a phone held in front of the car's camera. It is drawn pixel-exact at the
screen's native size, so each square is a whole number of screen pixels and its physical size follows from
the screen's pixel density. A ruler check on the phone confirms the display is 1:1
(evidence/M1/M1.T7/board/README.md).

Usage (Mac or Spark host; Pillow only):
  python3 course-project/tools/make_checkerboard.py --screen 2868x1320 --ppi 460 --squares 13x6 \
      --label "iPhone 18 Pro Max" --out course-project/evidence/M1/M1.T7/board/checkerboard_12x5_2868x1320.png

--squares counts squares (columns x rows, landscape). OpenCV's pattern size is the inner corners, one fewer
each way. The square is the largest whole number of pixels that leaves a white quiet zone of at least
--quiet squares on every side, because OpenCV's detector needs a white border around the board. One square
count must be even and the other odd, so the board looks different after a half turn and the corner order
is never ambiguous. A JSON sidecar with the geometry is written next to the PNG.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote this generator for the phone-screen board.
"""
import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

MM_PER_INCH = 25.4


def parse_pair(text, name):
    """Parse 'AxB' into two positive ints."""
    try:
        a, b = (int(v) for v in text.lower().split("x"))
    except ValueError:
        raise ValueError(f"{name} must look like 13x6, got {text!r}") from None
    if a <= 0 or b <= 0:
        raise ValueError(f"{name} must be positive, got {text!r}")
    return a, b


def layout(width, height, cols, rows, quiet=1.0, min_square=8):
    """Square size and placement: the largest whole-pixel square with >= quiet squares of white on each side."""
    if cols < 3 or rows < 3:
        raise ValueError("need at least 3 x 3 squares (2 x 2 inner corners)")
    if (cols + rows) % 2 == 0:
        raise ValueError(f"{cols} x {rows} squares look the same after a half turn; make one count even, one odd")
    if quiet < 0:
        raise ValueError("quiet must be >= 0")
    square = int(min(width / (cols + 2 * quiet), height / (rows + 2 * quiet)))
    if square < min_square:
        raise ValueError(f"squares would be {square} px; use fewer squares or a larger screen")
    board_w, board_h = cols * square, rows * square
    x0, y0 = (width - board_w) // 2, (height - board_h) // 2
    return {
        "square_px": square,
        "origin_px": [x0, y0],
        "board_px": [board_w, board_h],
        "quiet_px": {"left": x0, "right": width - x0 - board_w, "top": y0, "bottom": height - y0 - board_h},
    }


def draw(width, height, cols, rows, square, x0, y0):
    """8-bit grey image: white background, black squares where (row + col) is even (top-left is black)."""
    from PIL import Image, ImageDraw

    img = Image.new("L", (width, height), 255)
    pen = ImageDraw.Draw(img)
    for r in range(rows):
        for c in range(cols):
            if (r + c) % 2 == 0:
                left, top = x0 + c * square, y0 + r * square
                pen.rectangle([left, top, left + square - 1, top + square - 1], fill=0)  # inclusive corners
    return img


def spec(width, height, ppi, cols, rows, quiet, geo, label):
    """Everything a later calibration needs to know about the board, with the predicted physical sizes."""
    mm = MM_PER_INCH / ppi
    s = geo["square_px"]
    return {
        "schema": "bm.checkerboard-1",
        "generated": datetime.date.today().isoformat(),
        "generator": "course-project/tools/make_checkerboard.py",
        "display": {"label": label, "screen_px": [width, height], "ppi": ppi, "orientation": "landscape"},
        "squares": [cols, rows],
        "inner_corners": [cols - 1, rows - 1],
        "inner_corner_count": (cols - 1) * (rows - 1),
        "top_left_square": "black",
        "quiet_min_squares": quiet,
        **geo,
        "square_mm_predicted": round(s * mm, 4),
        "board_mm_predicted": [round(cols * s * mm, 2), round(rows * s * mm, 2)],
        "note": "Predicted sizes hold only when the phone shows the PNG 1:1 (full screen, not zoomed). "
                "Confirm with the ruler check in evidence/M1/M1.T7/board/README.md; calibration uses square_m "
                "= square_mm_predicted / 1000 if the check passes, else the measured long span / cols / 1000.",
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--screen", required=True, help="native screen size in landscape, WIDTHxHEIGHT pixels")
    ap.add_argument("--ppi", type=float, required=True, help="screen pixel density (pixels per inch)")
    ap.add_argument("--squares", default="13x6", help="squares, COLSxROWS (default 13x6 = 12x5 inner corners)")
    ap.add_argument("--quiet", type=float, default=1.0, help="minimum white border, in squares (default 1)")
    ap.add_argument("--label", default="", help="device name stored in the metadata")
    ap.add_argument("--out", required=True, help="output PNG; the JSON sidecar gets the same stem")
    args = ap.parse_args(argv)

    try:
        width, height = parse_pair(args.screen, "--screen")
        cols, rows = parse_pair(args.squares, "--squares")
        if args.ppi <= 0:
            raise ValueError("--ppi must be positive")
        geo = layout(width, height, cols, rows, args.quiet)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    from PIL.PngImagePlugin import PngInfo

    info = spec(width, height, args.ppi, cols, rows, args.quiet, geo, args.label)
    img = draw(width, height, cols, rows, geo["square_px"], *geo["origin_px"])
    meta = PngInfo()
    meta.add_text("Title", f"Checkerboard {cols - 1}x{rows - 1} inner corners, {geo['square_px']} px squares")
    meta.add_text("Description", json.dumps({k: info[k] for k in
                                             ("display", "squares", "inner_corners", "square_px",
                                              "square_mm_predicted")}))
    meta.add_text("Software", info["generator"])
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, format="PNG", pnginfo=meta, optimize=True)
    info["png"] = out.name
    info["png_sha256"] = hashlib.sha256(out.read_bytes()).hexdigest()
    out.with_suffix(".json").write_text(json.dumps(info, indent=2) + "\n")

    q = geo["quiet_px"]
    print(f"wrote {out} ({width} x {height} px) and {out.with_suffix('.json').name}")
    print(f"squares {cols} x {rows}; OpenCV pattern size (inner corners) {cols - 1} x {rows - 1} "
          f"= {info['inner_corner_count']} corners")
    print(f"square {geo['square_px']} px = {info['square_mm_predicted']:.3f} mm at {args.ppi:g} ppi; "
          f"board {info['board_mm_predicted'][0]:.1f} x {info['board_mm_predicted'][1]:.1f} mm")
    print(f"white border px: left {q['left']}, right {q['right']}, top {q['top']}, bottom {q['bottom']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
