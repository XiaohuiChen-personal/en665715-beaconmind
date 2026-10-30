"""Scaffold tests for the BeaconMind package layout.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the five scaffold tests.
"""
import os
import sys

import beaconmind


def test_package_version():
    assert beaconmind.__version__ == "0.1.0"


def test_python_is_supported():
    assert sys.version_info >= (3, 10)


def test_markers_registered(pytestconfig):
    raw = pytestconfig.getini("markers")
    if isinstance(raw, str):
        entries = raw.splitlines()
    else:
        entries = list(raw)
    names = []
    for entry in entries:
        text = str(entry).strip()
        if not text:
            continue
        names.append(text.split(":", 1)[0].strip())
    for required in ("llm", "isaac", "hardware", "gtsam"):
        assert required in names, names


def test_layout_folders_exist(course_root):
    required = (
        "beaconmind/src/beaconmind",
        "ros2_ws/src",
        "firmware/pico/beaconmind_fw/logic",
        "firmware/pico/tests",
        "firmware/esp32cam",
        "sim/isaac",
        "docker",
        "configs/arenas",
        "tools",
        "evidence",
        "preregistration",
        "presentation",
    )
    missing = [rel for rel in required if not (course_root / rel).is_dir()]
    assert missing == [], missing


def test_no_folder_named_log(course_root):
    prune = {".venv", "data", "node_modules", "ros2_ws"}
    found = []
    for dirpath, dirnames, _filenames in os.walk(course_root):
        if "log" in dirnames:
            found.append(os.path.join(dirpath, "log"))
        dirnames[:] = [name for name in dirnames if name not in prune]
    assert found == [], found
