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


def test_save_frames_keeps_every_good_frame_and_indexes_every_request(tmp_path):
    """--save (rule R2). AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-18."""
    import json

    probe = load_probe()
    good = b"\xff\xd8frame\xff\xd9"
    probe.save_frames(str(tmp_path), [
        (0, 200, {"X-BM-Seq": "5", "X-BM-Width": "1600", "Content-Type": "image/jpeg"}, good, 812.34),
        (1, 503, {}, b"busy", 10.0),
    ])
    lines = [json.loads(l) for l in (tmp_path / "index.jsonl").read_text().splitlines()]
    assert lines[0] == {"i": 0, "http": 200, "latency_ms": 812.3, "bytes": len(good), "file": "000.jpg",
                        "headers": {"x-bm-seq": "5", "x-bm-width": "1600"}}
    assert "file" not in lines[1] and lines[1]["http"] == 503
    assert (tmp_path / "000.jpg").read_bytes() == good and not (tmp_path / "001.jpg").exists()
