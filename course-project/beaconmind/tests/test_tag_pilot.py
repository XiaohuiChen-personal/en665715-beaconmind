"""Tag-pilot tool (tools/tag_pilot.py; plan task M1.T8): the placement plan, truth handling, frame windows, and the
whole chain on simulated frames. The plan and truth tests are pure Python; the rest needs OpenCV and skips without it.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote these tests.
"""
import importlib.util
import math
import threading
import time
from pathlib import Path

import pytest

from beaconmind import camera_model as cm

TOOLS = Path(__file__).resolve().parents[2] / "tools"

CAM = cm.Camera(width=1024, height=768, fx=1181.4979, fy=1176.6462, cx=498.4421, cy=380.7903,
                dist=(0.08327, -0.070267, -0.001828, -0.008513, 0.0),
                x_m=0.12, y_m=0.0, z_m=0.075, roll_deg=4.4, pitch_deg=-3.9, yaw_deg=2.5)


def load():
    spec = importlib.util.spec_from_file_location("tag_pilot", TOOLS / "tag_pilot.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_plan_fits_the_field_of_view():
    tp = load()
    rows = tp.plan_rows(CAM, 15)
    names = [r["placement"] for r in rows]
    assert len(names) == len(set(names))
    parts = {p: [r for r in rows if r["part"] == p] for p in "ABCDER"}
    assert all(parts[p] for p in "ABCDER")
    near = cm.min_full_view_range(CAM, 0.23, 0.10, 0.0, margin_px=8.0)
    # parts A, B, E: the whole tag with its border is in the picture at every placement
    for r in parts["A"] + parts["B"] + parts["E"] + parts["R"]:
        assert tp.squared_in_view(CAM, float(r["x_m"]), float(r["y_m"])), r["placement"]
    assert float(parts["A"][0]["x_m"]) == pytest.approx(math.ceil(near * 20) / 20)
    assert [float(r["x_m"]) for r in parts["A"]][-1] == 2.5 and [float(r["x_m"]) for r in parts["E"]][-1] == 3.5
    # part B reaches both sides and stays inside the 46.9 degree field of view
    bearings = [math.degrees(math.atan2(float(r["y_m"]), float(r["x_m"]))) for r in parts["B"]]
    assert max(bearings) > 12 and min(bearings) < -12 and max(abs(b) for b in bearings) < CAM.hfov_deg / 2
    # part D goes below the whole-tag distance and never puts the car's nose into the wall
    assert all(float(r["x_m"]) < near for r in parts["D"])
    assert all(float(r["x_m"]) >= tp.FRONT_OVERHANG_M + 0.03 for r in rows)
    assert {int(r["incidence_deg"]) for r in parts["C"]} == {30, 45, 60}
    assert all(int(r["bearing_trusted"]) == 0 for r in parts["C"])
    by_name = {r["placement"]: r for r in rows}
    assert all(by_name[r["repeat_of"]]["x_m"] == r["x_m"] for r in parts["R"])
    assert all(int(r["tag_id"]) == 15 for r in rows)


def test_plan_follows_the_tag_size(tmp_path, capsys):
    tp = load()
    assert [r["x_m"] for r in tp.plan_rows(CAM, 15, tag_black_m=0.16)] == [r["x_m"] for r in tp.plan_rows(CAM, 15)]
    small = tp.plan_rows(CAM, 15, height_m=0.1825, tag_black_m=0.10)       # a 100 mm tag standing on the baseboard
    near = cm.min_full_view_range(CAM, 0.1825, 0.0625, 0.0, margin_px=8.0)
    first = float([r for r in small if r["part"] == "A"][0]["x_m"])
    assert first == pytest.approx(math.ceil(near * 20) / 20) and first < 0.70 < float(tp.plan_rows(CAM, 15)[0]["x_m"])
    for r in small:
        if r["part"] in "ABE":
            assert tp.squared_in_view(CAM, float(r["x_m"]), float(r["y_m"]), 0.1825, tp.sheet_half_m(0.10)), r["placement"]
    # a smaller sheet can stand further to the side
    assert tp.max_side_offset(CAM, 1.5, +1, 0.1825, tp.sheet_half_m(0.10)) > tp.max_side_offset(CAM, 1.5, +1)
    out = tmp_path / "plan.csv"
    assert tp.main(["placements", "--tag-id", "7", "--out", str(out), "--tag-black-m", "0.10", "--tag-height-m", "0.1825"]) == 0
    assert "a 100 mm tag 0.18 m up" in capsys.readouterr().out
    assert [r["x_m"] for r in tp.read_rows(str(out))] == [r["x_m"] for r in small]
    with pytest.raises(SystemExit):
        tp.main(["placements", "--tag-id", "7", "--out", str(out), "--tag-black-m", "0"])


def test_max_side_offset_is_asymmetric_like_the_mount():
    tp = load()
    left, right = tp.max_side_offset(CAM, 2.5, +1), tp.max_side_offset(CAM, 2.5, -1)
    assert 0.5 < right < left < 1.2          # the camera points 2.5 degrees left, so the left side reaches further
    assert tp.max_side_offset(CAM, 0.5, +1) == 0.0


def test_truth_uses_the_tape_readings_and_the_wall_offset(tmp_path):
    tp = load()
    rows = tp.plan_rows(CAM, 7)
    rows[1]["measured_x_m"] = "1.013"
    rows[1]["measured_y_m"] = "-0.006"
    path = tmp_path / "plan.csv"
    tp.write_rows(str(path), rows)
    back = tp.read_rows(str(path))
    assert [r["placement"] for r in back] == [r["placement"] for r in rows]
    t = tp.truth_of(back[1], wall_offset_m=0.012)
    assert t["x_m"] == pytest.approx(1.025) and t["y_m"] == pytest.approx(-0.006) and t["tag_id"] == 7
    assert t["incidence_deg"] is None and t["bearing_trusted"] is True
    t0 = tp.truth_of(back[0])
    assert t0["x_m"] == float(rows[0]["x_m"]) and t0["y_m"] == 0.0
    c = tp.truth_of([r for r in back if r["part"] == "C"][0])
    assert c["incidence_deg"] == 30.0 and c["bearing_trusted"] is False


def test_windows_last_mark_wins_and_plan_columns_win(tmp_path):
    tp = load()
    marks = tmp_path / "marks.csv"
    tp.write_rows(str(marks), [{"placement": "A01", "first_frame": 5, "last_frame": 34},
                               {"placement": "A02", "first_frame": 40, "last_frame": 69},
                               {"placement": "A01", "first_frame": 80, "last_frame": 109}], tp.MARK_FIELDS)
    rows = [{"placement": "A01", "first_frame": "", "last_frame": ""},
            {"placement": "A02", "first_frame": "200", "last_frame": "229"},
            {"placement": "A03", "first_frame": "", "last_frame": ""}]
    assert tp.windows_of(rows, str(marks)) == {"A01": (80, 109), "A02": (200, 229)}
    assert tp.windows_of(rows, str(tmp_path / "none.csv")) == {"A02": (200, 229)}


def test_pick_detection_tells_the_pilot_tag_from_the_rooms_other_tags():
    tp = load()
    truth = {"x_m": 2.0, "y_m": 0.0, "tag_id": 3}

    def det(tag_id, x, y):
        return {"id": tag_id, "base_xyz_m": [x, y, 0.23]}

    best, wrong, others = tp.pick_detection([det(3, 2.02, 0.01), det(3, 2.1, 1.5), det(10, 2.0, -0.9)], truth)
    assert best["base_xyz_m"][0] == 2.02 and wrong is None and others == 2
    best, wrong, _ = tp.pick_detection([det(3, 2.1, 1.5)], truth)          # only the other tag with id 3
    assert best is None and wrong is None
    best, wrong, _ = tp.pick_detection([det(11, 2.05, 0.0)], truth)        # the pilot tag read as another id
    assert best is None and wrong == 11
    assert tp.session_date("/x/20261120-101500-tag-pilot") == "2026-11-20"


def test_selftest_on_simulated_frames(capsys):
    pytest.importorskip("cv2")
    pytest.importorskip("numpy")
    pytest.importorskip("jsonschema")
    tp = load()
    assert tp.selftest(frames_per_placement=10, verbose=True) == 0
    out = capsys.readouterr().out
    assert "FAIL" not in out and "SIMULATED" in out and "selftest ok" in out


def test_mark_and_analyze_a_session(tmp_path, capsys):
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    pytest.importorskip("jsonschema")
    from beaconmind.perception import synth
    tp = load()
    camera_file = tp.cm.default_camera_path()
    camera = cm.load_camera(camera_file)
    session = tmp_path / "20261119-120000-tag-pilot"
    (session / "frames").mkdir(parents=True)
    plan = [r for r in tp.plan_rows(camera, 15) if r["placement"] in ("A02", "A06")]
    plan_path = tmp_path / "plan.csv"
    tp.write_rows(str(plan_path), plan)
    rng = np.random.default_rng(2)
    counter = {"n": 0}

    def feed(x_m, count):
        clean = synth.render_scene(camera, [synth.tag_at(15, x_m, 0.0, 0.23)], wall=150.0, black=100.0, white=185.0)
        for _ in range(count):
            counter["n"] += 1
            name = "%06d_%d.jpg" % (counter["n"], 1794989156000000000 + counter["n"] * 200000000)
            tmp = session / "frames" / (".tmp-" + name)
            cv2.imwrite(str(tmp), synth.real_like(clean, rng=rng), [cv2.IMWRITE_JPEG_QUALITY, 95])
            tmp.rename(session / "frames" / name)
            time.sleep(0.02)

    feed(1.0, 3)                                               # frames from before the mark must not be used
    for row in plan:
        worker = threading.Thread(target=lambda x=float(row["x_m"]): (time.sleep(0.3), feed(x, 8)))
        worker.start()
        code = tp.main(["mark", "--placement", row["placement"], "--session", str(session), "--placements",
                        str(plan_path), "--frames", "6", "--settle", "0", "--timeout", "20"])
        worker.join()
        assert code == 0
    out = capsys.readouterr().out
    assert "A02 frames=6 detected=6" in out and "A06 frames=6 detected=6" in out
    marks = tp.read_rows(str(session / "tag_pilot" / "marks.csv"))
    assert [(m["placement"], int(m["first_frame"]), int(m["last_frame"])) for m in marks] == [("A02", 4, 9), ("A06", 12, 17)]
    evidence = tmp_path / "evidence"
    out_file = tmp_path / "detector_noise.json"
    code = tp.main(["analyze", "--session", str(session), "--placements", str(plan_path), "--evidence", str(evidence),
                    "--out", str(out_file)])
    assert code == 0
    import json
    model = json.loads(out_file.read_text(encoding="utf-8"))
    assert model["schema"] == "bm.detector_noise/1" and model["source"]["date"] == "2026-11-19"
    assert model["source"]["n_frames"] == 12 and model["source"]["n_placements"] == 2
    assert model["min_range_m"] == 1.0 and model["max_range_m"] == 2.0
    assert abs(model["range_bias_m"]["a"] + model["range_bias_m"]["b"] * 1.5) < 0.01
    assert abs(model["bearing_bias_deg"]) < 0.2
    for name in ("frames.csv", "per-placement.csv", "fit-output.txt", "dv-findings.md", "repeat-check.txt",
                 "size-convention.txt", "detector_noise.json"):
        assert (evidence / name).is_file(), name
    frames = tp.read_rows(str(evidence / "frames.csv"))
    assert len(frames) == 12 and all(f["detected"] == "1" for f in frames)
    assert "OK: within 0.05 m" in (evidence / "size-convention.txt").read_text(encoding="utf-8")
