"""Room geometry, tag placement and the ID rule of the real-arena layout (tools/room_layout.py, M3.T10).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-17: wrote these tests.
"""
import importlib.util
import math
from pathlib import Path


def load_tool():
    path = Path(__file__).resolve().parents[2] / "tools" / "room_layout.py"
    spec = importlib.util.spec_from_file_location("room_layout", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_room_is_convex_counter_clockwise_and_matches_the_tape():
    rl = load_tool()
    pts = [rl.CORNERS[c] for c in rl.POLYGON]
    for i in range(5):
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % 5]
        assert (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]) > 0  # left turn at every corner
    lengths = [math.dist(pts[i], pts[(i + 1) % 5]) for i in range(5)]
    for got, read in zip(lengths, (2.95, 1.23, 4.27, 3.81, 5.12)):  # room-survey.md readings
        assert abs(got - read) < 0.005


def test_normals_point_into_the_room_and_tags_stay_clear():
    rl = load_tool()
    tags = rl.build_tags()
    assert len(tags) == 12
    for t in tags:
        nx, ny = math.cos(math.radians(t["normal_deg"])), math.sin(math.radians(t["normal_deg"]))
        assert rl.inside([rl.CORNERS[c] for c in rl.POLYGON], (t["x_m"] + 0.05 * nx, t["y_m"] + 0.05 * ny))
        wall = next(w for w in rl.WALLS if w["key"] == t["wall"])
        lo, hi = t["slide_m"]
        assert lo <= t["along_m"] <= hi and hi - lo <= 2 * rl.SLIDE_M + 1e-9
        assert any(a + rl.CLEAR_M <= lo and hi <= b - rl.CLEAR_M + 1e-9 for a, b in wall["spans"])


def test_ids_follow_the_d3_rule_even_after_sliding():
    rl = load_tool()
    tags = rl.build_tags()
    rl.assign_ids(tags, "real-room-1")
    ids = [t["id"] for t in tags]
    assert all(0 <= i <= 29 for i in ids)
    assert sorted(ids.count(i) for i in set(ids)).count(2) == rl.N_DUP
    assert max(ids.count(i) for i in ids) == 2
    for i in set(ids):
        pair = [t for t in tags if t["id"] == i]
        if len(pair) == 2:
            # worst case: both copies slide towards each other by the full allowance
            assert math.dist((pair[0]["x_m"], pair[0]["y_m"]), (pair[1]["x_m"], pair[1]["y_m"])) - 2 * rl.SLIDE_M >= 1.5
    again = rl.build_tags()
    rl.assign_ids(again, "real-room-1")
    assert [t["id"] for t in again] == ids  # seeded


def test_visibility_respects_view_range_incidence_and_the_desk():
    rl = load_tool()
    tag = {"x_m": 0.0, "y_m": 1.6, "normal_deg": 0.0}  # on the desk wall, facing +x
    assert rl.visible_range((1.0, 1.6, 180.0), tag) == 1.0
    assert rl.visible_range((1.0, 1.6, 0.0), tag) is None            # behind the camera
    assert rl.visible_range((0.3, 3.0, 255.0), tag) is None          # incidence above 60 deg
    # incidence 56 deg passes, but the line of sight crosses the desk's front at y = 2.59 m
    assert abs(rl.visible_range((1.0, 3.1, 236.0), tag) - math.hypot(1.0, 1.5)) < 1e-9
    assert rl.visible_range((1.0, 3.1, 236.0), tag, (rl.DESK,)) is None
