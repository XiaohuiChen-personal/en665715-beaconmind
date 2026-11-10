"""Geometry of the phone-screen checkerboard (tools/make_checkerboard.py, M1.T7).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote these tests.
"""
import importlib.util
import json
from pathlib import Path

import pytest

pytest.importorskip("PIL")


def load_tool():
    path = Path(__file__).resolve().parents[2] / "tools" / "make_checkerboard.py"
    spec = importlib.util.spec_from_file_location("make_checkerboard", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_layout_iphone_18_pro_max():
    geo = load_tool().layout(2868, 1320, 13, 6, quiet=1.0)
    assert geo["square_px"] == 165  # 1320 / (6 + 2) = 165 exactly; width allows 2868 / 15 = 191
    assert geo["board_px"] == [2145, 990]
    assert geo["quiet_px"] == {"left": 361, "right": 362, "top": 165, "bottom": 165}


def test_layout_keeps_the_quiet_zone_and_refuses_bad_boards():
    tool = load_tool()
    for w, h, c, r in [(2868, 1320, 13, 6), (2532, 1170, 10, 7), (1080, 2400, 6, 13), (1000, 999, 4, 7)]:
        geo = tool.layout(w, h, c, r, quiet=1.0)
        assert min(geo["quiet_px"].values()) >= geo["square_px"]
    with pytest.raises(ValueError, match="half turn"):
        tool.layout(2868, 1320, 12, 6)  # even x even: 180-degree symmetric
    with pytest.raises(ValueError, match="half turn"):
        tool.layout(2868, 1320, 13, 7)  # odd x odd: also symmetric
    with pytest.raises(ValueError, match="px"):
        tool.layout(100, 60, 13, 6)


def test_drawn_squares_are_exact(tmp_path):
    tool = load_tool()
    out = tmp_path / "board.png"
    assert tool.main(["--screen", "2868x1320", "--ppi", "460", "--squares", "13x6", "--out", str(out)]) == 0
    from PIL import Image

    img = Image.open(out)
    assert img.size == (2868, 1320) and img.mode == "L"
    px = img.load()
    s, x0, y0 = 165, 361, 165
    for r in range(6):
        for c in range(13):
            want = 0 if (r + c) % 2 == 0 else 255
            left, top = x0 + c * s, y0 + r * s
            for dx, dy in [(0, 0), (s - 1, 0), (0, s - 1), (s - 1, s - 1), (s // 2, s // 2)]:
                assert px[left + dx, top + dy] == want, (r, c, dx, dy)
    # outside the board everything is white; just outside each edge too
    assert img.crop((0, 0, x0, 1320)).getextrema() == (255, 255)
    assert img.crop((x0 + 13 * s, 0, 2868, 1320)).getextrema() == (255, 255)
    assert img.crop((0, 0, 2868, y0)).getextrema() == (255, 255)
    assert img.crop((0, y0 + 6 * s, 2868, 1320)).getextrema() == (255, 255)
    # black pixel count = 39 black squares of 165 x 165
    assert img.histogram()[0] == 39 * s * s and img.histogram()[0] + img.histogram()[255] == 2868 * 1320

    side = json.loads(out.with_suffix(".json").read_text())
    assert side["inner_corners"] == [12, 5] and side["inner_corner_count"] == 60
    assert side["square_mm_predicted"] == pytest.approx(165 * 25.4 / 460, abs=1e-4)
    assert side["board_mm_predicted"] == [pytest.approx(118.44, abs=0.01), pytest.approx(54.67, abs=0.01)]


def test_bad_arguments_exit_2(tmp_path, capsys):
    tool = load_tool()
    assert tool.main(["--screen", "2868", "--ppi", "460", "--out", str(tmp_path / "x.png")]) == 2
    assert tool.main(["--screen", "2868x1320", "--ppi", "0", "--out", str(tmp_path / "x.png")]) == 2
    assert not (tmp_path / "x.png").exists()
