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


# ---------------------------------------------------------------- layout real-room-2 (the printed twelve plus eight)
# AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote the tests below.

WORLD_2 = Path(__file__).resolve().parents[2] / "configs" / "arenas" / "real-room-plus8-160mm-nominal.json"


def test_real_room_2_is_the_printed_twelve_plus_the_eight_chosen():
    rl = load_tool()
    old, new = rl.build_layout("real-room-1"), rl.build_layout("real-room-2")
    assert len(old) == 12 and len(new) == 20
    for a, b in zip(old, new):                       # the printed pages keep their place, ID and name
        assert all(a[k] == b[k] for k in ("uid", "id", "wall", "along_m", "x_m", "y_m", "normal_deg"))
        assert not b.get("added")
        assert a["slide_m"][0] <= b["slide_m"][0] <= b["along_m"] <= b["slide_m"][1] <= a["slide_m"][1]
    added = new[12:]
    assert [(t["uid"], t["wall"], round(t["along_m"] * 100), t["id"]) for t in added] == [
        ("T12", "angled", 20, 1), ("T13", "window", 215, 4), ("T14", "window", 125, 5), ("T15", "window", 314, 6),
        ("T16", "window", 14, 7), ("T17", "w295", 200, 8), ("T18", "w295", 269, 9), ("T19", "window", 404, 11)]
    assert all(t["added"] and t["z_m"] == 0.23 for t in added)
    ids = [t["id"] for t in new]
    assert sorted(ids.count(i) for i in set(ids)).count(2) == rl.N_DUP and max(ids.count(i) for i in ids) == 2
    assert not {t["id"] for t in added} & {t["id"] for t in old}
    room = [rl.CORNERS[c] for c in rl.POLYGON]
    for t in added:                                  # on the wall, facing into the room
        nx, ny = math.cos(math.radians(t["normal_deg"])), math.sin(math.radians(t["normal_deg"]))
        assert rl.inside(room, (t["x_m"] + 0.05 * nx, t["y_m"] + 0.05 * ny))
        assert not rl.inside(room, (t["x_m"] - 0.05 * nx, t["y_m"] - 0.05 * ny))


def test_real_room_2_agrees_with_the_world_file_to_the_millimetre():
    import copy
    import json
    rl = load_tool()
    tags = rl.build_layout("real-room-2")
    world = json.loads(WORLD_2.read_text(encoding="utf-8"))
    assert len(world["tags"]) == 20
    assert rl.compare_with_world(tags, world) == []
    off = copy.deepcopy(world)
    off["tags"][13]["y_m"] += 0.001                  # one millimetre
    off["tags"][17]["id"] = 12
    off["tags"][5]["normal_deg"] = 0.0
    off["tags"].pop()
    found = rl.compare_with_world(tags, off)
    assert len(found) == 4
    assert any("T13: y_m" in f for f in found) and any("T17: id 8" in f for f in found)
    assert any("T05: normal" in f for f in found) and any("T19 is only in the layout" in f for f in found)
    assert rl.compare_with_world(tags[:12], json.loads(
        (WORLD_2.parent / "real-room-nominal.json").read_text(encoding="utf-8"))) == []


def test_real_room_2_has_no_clash_and_pages_cannot_touch():
    rl = load_tool()
    tags = rl.build_layout("real-room-2")
    clashes, notes = rl.check_layout(tags)
    assert clashes == []
    # the outlets of three walls were never located: the check says so instead of passing silently
    assert sum(n.startswith("not checked") for n in notes) == 3
    for key in {t["wall"] for t in tags}:
        row = sorted((t for t in tags if t["wall"] == key), key=lambda t: t["along_m"])
        wall = rl.wall_by_key(key)
        for t in row:
            assert t["slide_m"][0] <= t["along_m"] <= t["slide_m"][1]
            assert any(a + rl.CLEAR_M - 1e-9 <= t["slide_m"][0] and t["slide_m"][1] <= b - rl.CLEAR_M + 1e-9
                       for a, b in wall["spans"])
        for a, b in zip(row, row[1:]):               # even with both slid towards each other
            assert b["slide_m"][0] - a["slide_m"][1] >= rl.PAGE_W_M + rl.PAGE_GAP_M - 1e-9
    assert rl.check_layout(rl.build_layout("real-room-1"))[0] == []


def test_check_layout_reports_each_kind_of_clash_and_moves_nothing():
    rl = load_tool()

    def with_tag(wall_key, along_m, tag_id, base="real-room-2"):
        tags = rl.build_layout(base)
        wall = rl.wall_by_key(wall_key)
        ux, uy, _ = rl.unit(rl.CORNERS[wall["from"]], rl.CORNERS[wall["to"]])
        x0, y0 = rl.CORNERS[wall["from"]]
        tags.append({"uid": "T99", "id": tag_id, "wall": wall_key, "wall_name": wall["name"], "from": wall["from"],
                     "along_m": along_m, "x_m": x0 + ux * along_m, "y_m": y0 + uy * along_m, "z_m": 0.23,
                     "normal_deg": 0.0, "slide_m": [along_m, along_m], "added": True})
        before = [(t["uid"], t["along_m"]) for t in tags]
        clashes, _notes = rl.check_layout(tags)
        assert [(t["uid"], t["along_m"]) for t in tags] == before
        return clashes

    assert any("not on a bare stretch" in c for c in with_tag("doors", 1.00, 13))            # on door 1
    assert any("door trim or corner" in c for c in with_tag("doors", 0.50, 13))              # 4 cm from door 1's trim
    assert any("door trim or corner" in c for c in with_tag("window", 0.05, 13))             # page round corner 3
    assert any("Ethernet stretch" in c for c in with_tag("desk", 3.60, 13))
    assert any("not on a bare stretch" in c for c in with_tag("desk", 0.50, 13))             # the entrance door
    assert any("covers the outlet" in c for c in with_tag("angled", 0.45, 13))
    assert any("overlap on the window wall" in c for c in with_tag("window", 0.30, 13))      # 16 cm from T16
    assert any("under 1.5 m" in c for c in with_tag("w295", 1.00, 10, base="real-room-1"))   # second id 10, 0.42 m away
    assert any("outside 0-29" in c for c in with_tag("w295", 1.03, 31))
    assert with_tag("w295", 1.03, 15) == ["4 IDs are used twice; the layout rule asks for 3"]  # a fourth doubled ID
    assert any("can meet" in c for c in with_tag("w295", 1.00, 13))                          # T01 may slide up to 78 cm
    assert with_tag("w295", 1.03, 13) == []                                                  # a free, bare spot


def test_visibility_takes_the_calibrated_field_of_view_and_the_camera_model():
    rl = load_tool()
    tag = {"x_m": 0.0, "y_m": 1.6, "normal_deg": 0.0, "z_m": 0.23}
    off_axis = (1.5, 1.6, 180.0 - 26.0)              # tag 26 degrees to one side
    assert rl.visible_range(off_axis, tag) == 1.5                         # inside the placeholder 60 degrees
    assert rl.visible_range(off_axis, tag, hfov_deg=46.9) is None         # outside the calibrated 46.9
    assert rl.visible_range((1.5, 1.6, 180.0 - 20.0), tag, hfov_deg=46.9) == 1.5
    assert rl.visible_range((0.5, 1.6, 180.0), tag, min_range_m=0.8) is None
    from beaconmind import camera_model as cm
    camera = cm.Camera(width=1024, height=768, fx=1181.4979, fy=1176.6462, cx=498.4421, cy=380.7903,
                       dist=(0.08327, -0.070267, -0.001828, -0.008513, 0.0),
                       x_m=0.12, y_m=0.0, z_m=0.075, roll_deg=4.4, pitch_deg=-3.9, yaw_deg=2.5)
    assert rl.visible_range((1.0, 1.6, 180.0), tag, camera=camera, min_range_m=0.0) == 1.0
    assert rl.visible_range((0.7, 1.6, 180.0), tag, camera=camera, min_range_m=0.0) is None       # top cut off
    # the whole sheet must be in the picture: a centre 20 degrees to the right is in the field of view, the sheet is not
    assert rl.visible_range((1.5, 1.6, 180.0 + 20.0), tag, hfov_deg=46.9) == 1.5
    assert rl.visible_range((1.5, 1.6, 180.0 + 20.0), tag, camera=camera, min_range_m=0.0) is None
    # and the picture reaches further to the car's left than to its right (the mount's yaw and roll)
    assert rl.visible_range((1.5, 1.6, 180.0 - 17.0), tag, camera=camera, min_range_m=0.0) == 1.5


def test_coverage_of_the_twenty_tags_is_better_than_of_the_twelve():
    rl = load_tool()
    tags = rl.build_layout("real-room-2")
    drive = rl.drive_polygon()
    more, n = rl.coverage(drive, tags, (2.0, 3.0), step=0.4, occluders=(rl.DESK,), hfov_deg=46.9)
    less, _ = rl.coverage(drive, tags[:12], (2.0, 3.0), step=0.4, occluders=(rl.DESK,), hfov_deg=46.9)
    wide, _ = rl.coverage(drive, tags[:12], (2.0, 3.0), step=0.4, occluders=(rl.DESK,))
    assert n > 40
    for r in (2.0, 3.0):
        assert more[r][0] > less[r][0] and more[r][1] > less[r][1]        # one heading: at least 1, at least 2 tags
        assert wide[r][0] > less[r][0]                                    # 60 degrees saw more than 46.9 does
        assert less[r][2] == wide[r][2]                                   # a full turn does not depend on the view angle
