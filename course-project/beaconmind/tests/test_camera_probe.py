"""Pure helpers for the ESP32-CAM HTTP probe.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the M1.T6 camera_probe helper tests.
"""
import importlib.util
from pathlib import Path


def load_probe():
    path = Path(__file__).resolve().parents[2] / "tools" / "camera_probe.py"
    spec = importlib.util.spec_from_file_location("camera_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_headers():
    probe = load_probe()
    parsed = probe.parse_headers({"X-BM-Seq": "7", "X-BM-Capture-Us": "1234567"})
    assert parsed == {"seq": 7, "capture_us": 1234567}
    missing = probe.parse_headers({})
    assert missing == {"seq": None, "capture_us": None}


def test_seq_strictly_increasing():
    probe = load_probe()
    assert probe.seq_strictly_increasing([1, 2, 4]) is True
    assert probe.seq_strictly_increasing([1, 1]) is False


def test_brightness_jump():
    probe = load_probe()
    assert probe.brightness_jump(50, 61) is True
    assert probe.brightness_jump(50, 59) is False


# AI-assisted: Claude Opus 5.5 via Claude Code, 2026-10-25: tests for the bm_cam-0.2 mode helpers.
def test_parse_frame_size():
    probe = load_probe()
    assert probe.parse_frame_size({"X-BM-Width": "1600", "x-bm-height": "1200"}) == (1600, 1200)
    assert probe.parse_frame_size({"X-BM-Width": "640"}) is None
    assert probe.parse_frame_size({}) is None


def test_control_path():
    probe = load_probe()
    assert probe.control_path("uxga", 10) == "/control?framesize=uxga&quality=10"
    assert probe.control_path("vga") == "/control?framesize=vga"
    assert probe.control_path(quality=12) == "/control?quality=12"
    for bad in [("hd", None), (None, 9), (None, 64), (None, True), (None, None)]:
        try:
            probe.control_path(*bad)
        except ValueError:
            continue
        raise AssertionError("control_path accepted {0}".format(bad))
