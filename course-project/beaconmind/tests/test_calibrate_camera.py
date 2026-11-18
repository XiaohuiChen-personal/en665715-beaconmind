"""Phone-board calibration tool (tools/calibrate_camera.py, plan task M1.T7).

The guidance helpers run everywhere; the synthetic calibration needs OpenCV and skips without it.
AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-18: wrote these tests.
"""
import importlib.util
import json
import math
from pathlib import Path

import pytest

from beaconmind.schemas import validate

TOOLS = Path(__file__).resolve().parents[2] / "tools"
BOARD = Path(__file__).resolve().parents[2] / "evidence" / "M1" / "M1.T7" / "board" / "checkerboard_12x5_2868x1320.png"


def load():
    spec = importlib.util.spec_from_file_location("calibrate_camera", TOOLS / "calibrate_camera.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_regions_bands_and_tilts():
    cc = load()
    assert cc.region_of(0.1, 0.1) == "top left" and cc.region_of(0.5, 0.5) == "centre"
    assert cc.region_of(0.9, 0.5) == "right edge" and cc.region_of(0.5, 0.95) == "bottom edge"
    assert [cc.band_of(d) for d in (0.1, 0.2, 0.3, 0.5, 0.7)] == ["too close", "close", "middle", "far", "too far"]
    assert cc.tilt_of(5, -8) == "flat" and cc.tilt_of(30, 5) == "turned" and cc.tilt_of(-3, -28) == "tipped"
    assert cc.tilt_of(17, 0) == "slight"


def test_each_kept_frame_fills_one_goal():
    cc = load()
    obs = {"band": "close", "region": "centre", "u": 0.5, "v": 0.5, "tilt": "flat"}
    assert len(cc.open_goals([obs])) == len(cc.GOALS) - 1
    assert len(cc.open_goals([obs, obs])) == len(cc.GOALS) - 1  # a second identical frame adds nothing
    turned = {"band": "middle", "region": "top left", "u": 0.2, "v": 0.2, "tilt": "turned"}
    assert len(cc.open_goals([obs, turned, turned])) == len(cc.GOALS) - 3


def test_corners_are_reachable_without_leaving_the_picture():
    cc = load()
    # the first capture: at 20 cm the board could not be both in the outer third and whole in view
    assert cc.region_ok("top left", 0.40, 0.40) and not cc.region_ok("top left", 0.45, 0.30)
    assert cc.region_ok("left edge", 0.35, 0.5) and not cc.region_ok("left edge", 0.35, 0.1)
    assert cc.region_ok("centre", 0.62, 0.38) and not cc.region_ok("centre", 0.75, 0.5)
    near_corner = {"band": "middle", "region": "top right", "u": 0.6, "v": 0.4, "tilt": "flat"}
    assert cc.goal_met(("near", "top right", "flat"), near_corner)
    assert not cc.goal_met(("near", "top right", "flat"), dict(near_corner, band="far"))


def test_come_back_points_toward_the_middle():
    cc = load()
    # mirror-like picture (moving right moves the board right): lost at picture-left -> come back to your right
    assert cc.come_back((0.1, 0.5), +1) == "The board went out of view. Come back a little to your right."
    assert cc.come_back((0.1, 0.5), -1) == "The board went out of view. Come back a little to your left."
    assert cc.come_back((0.8, 0.1), +1) == "The board went out of view. Come back a little to your left and a little lower."
    assert cc.come_back((0.5, 0.5), +1).startswith("I lost the board")


def test_instructions_follow_the_operators_left_and_right():
    cc = load()
    goal = ("close", "top left", "flat")
    # the camera faces the operator: if moving right moves the board left in the picture, picture-left is their right
    assert "up high and to your right" in cc.instruction(goal, None, -1)
    assert "up high and to your left" in cc.instruction(goal, None, +1)
    far = {"band": "far", "region": "top left", "u": 0.2, "v": 0.2, "tilt": "flat"}
    assert cc.instruction(goal, far, -1) == "Now move it closer."
    close_wrong = {"band": "close", "region": "centre", "u": 0.5, "v": 0.5, "tilt": "turned"}
    assert cc.instruction(goal, close_wrong, -1) == "Now move it up high and to your right, and hold it flat to the camera."
    assert cc.instruction(("near", "top left", "flat"), far, +1) == "Now move it closer."


def test_coverage_counts_grid_cells():
    cc = load()
    assert cc.coverage([[(0, 0), (1023, 767)]], 1024, 768) == 2 / 48
    corners = [[(x * 1024 / 8 + 5, y * 768 / 6 + 5) for x in range(8) for y in range(6)]]
    assert cc.coverage(corners, 1024, 768) == 1.0


def test_camera_json_validates_with_null_extrinsics():
    cc = load()
    cj = cc.camera_json([[800.0, 0, 512.0], [0, 801.0, 384.0], [0, 0, 1]], [0.1, -0.2, 0.0, 0.0, 0.05], 0.31, 24,
                        1024, 768, "XGA", 12, {"fw": "bm_cam-0.2", "vflip": 0, "hmirror": 1},
                        "http://10.42.0.89/capture", "2026-11-18")
    assert validate("camera", cj) == []
    assert cj["firmware"] == {"name": "bm_cam", "version": "0.2", "vflip": False, "hmirror": True}
    assert abs(cj["hfov_deg"] - math.degrees(2 * math.atan(512 / 800))) < 0.01


def test_synthetic_views_give_back_the_lens(tmp_path):
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    cc = load()
    board = cv2.imread(str(BOARD), cv2.IMREAD_GRAYSCALE)
    phone = np.full((board.shape[0] + 200, board.shape[1] + 200), 200, np.uint8)
    phone[100:-100, 100:-100] = board
    mm = 25.4 / 460 / 1000                               # metres per board pixel
    w, h, fx = 1024, 768, 800.0
    K = np.array([[fx, 0, 512], [0, fx, 384], [0, 0, 1.0]])
    S = np.array([[mm, 0, -phone.shape[1] / 2 * mm], [0, mm, -phone.shape[0] / 2 * mm], [0, 0, 1]])
    s = tmp_path / "session"
    (s / "calib").mkdir(parents=True)
    (s / "meta").mkdir()
    (s / "meta" / "camera_status_start.json").write_text('{"fw": "bm_cam-0.2", "framesize": "XGA", "quality": 12, '
                                                          '"vflip": 0, "hmirror": 1}')
    (s / "meta" / "session.json").write_text('{"camera_ip": "10.42.0.89"}')
    kept = 0
    with open(s / "calib" / "accepted.jsonl", "w") as acc:
        for i, (d, yaw, pitch, du, dv) in enumerate([(dd, y, p, u, v) for dd in (0.2, 0.3, 0.45)
                                                     for (y, p) in ((0, 0), (30, 0), (0, 30), (-25, 20))
                                                     for (u, v) in ((-0.3, -0.25), (0.3, 0.25))]):
            a, b = math.radians(yaw), math.radians(pitch)
            R = (np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
                 @ np.array([[1, 0, 0], [0, math.cos(b), -math.sin(b)], [0, math.sin(b), math.cos(b)]]))
            t = np.array([du * 512 / fx * d, dv * 384 / fx * d, d])
            img = cv2.warpPerspective(phone, K @ np.column_stack([R[:, 0], R[:, 1], t]) @ S, (w, h), borderValue=120)
            corners = cc.find_board(cv2.GaussianBlur(img, (0, 0), 0.8))
            if corners is None:
                continue
            kept += 1
            acc.write(json.dumps({"file": "%03d.jpg" % i, "corners": corners.tolist(), "width": w, "height": h,
                                  "band": "close", "tilt": "flat"}) + "\n")
    assert kept >= 15
    out = tmp_path / "camera.json"

    class A:
        session, square_m, report = str(s), cc.SQUARE_M, None
    A.out = str(out)
    cc.calibrate(A)
    cj = json.loads(out.read_text())
    assert validate("camera", cj) == []
    m = cj["camera_matrix"]                              # row-major 3 x 3
    assert abs(m[0] / fx - 1) < 0.01 and abs(m[4] / fx - 1) < 0.01
    assert abs(m[2] - 512) < 6 and abs(m[5] - 384) < 6
    assert cj["rms_px"] < 0.5                            # unsmoothed warp in the test: about 0.3 px


def test_still_limit_follows_the_square_size():
    cc = load()
    # a 22 cm view in XGA: squares about 33 px -> about 4 px allowed (a fixed 1.5 px rejected every handheld frame)
    grid = [(c * 33.0, r * 33.0) for r in range(cc.ROWS) for c in range(cc.COLS)]
    assert abs(cc.still_limit(grid) - 0.12 * 33.0) < 0.05
    tiny = [(c * 5.0, r * 5.0) for r in range(cc.ROWS) for c in range(cc.COLS)]
    assert cc.still_limit(tiny) == 1.5


def test_skipped_goals_are_left_out_by_index():
    cc = load()
    turned = cc.GOALS.index(("near", "any", "turned"))
    assert cc.GOALS.count(("near", "any", "turned")) == 4        # repeated goals: skipping one leaves three
    ids = cc.open_goal_ids([], {0, turned})
    assert 0 not in ids and turned not in ids and len(ids) == len(cc.GOALS) - 2
    assert cc.open_goals([], {0, turned}).count(("near", "any", "turned")) == 3


def test_paper_board_settings_and_door_words():
    cc = load()
    cc.configure(9, 6, 0.023283, [0.25, 0.40, 0.60, 0.85], ("away from the closet door", "toward the closet door"))
    assert (cc.COLS, cc.ROWS, cc.SQUARE_M) == (9, 6, 0.023283)
    assert [cc.band_of(d) for d in (0.2, 0.3, 0.5, 0.7, 0.9)] == ["too close", "close", "middle", "far", "too far"]
    assert cc.spoken_distance("near") == "about 50 centimetres" and cc.spoken_distance("far") == "about 70 centimetres"
    assert cc.spoken_region("top left", +1) == "move it up high and away from the closet door"
    assert cc.come_back((0.1, 0.5), +1) == "The board went out of view. Come back a little toward the closet door."
    assert len(cc.board_points()) == 54


def test_free_mode_keeps_new_views_and_hints_the_empty_side():
    cc = load()
    a = {"u": 0.5, "v": 0.5, "dist_m": 0.6, "yaw_deg": 0.0, "pitch_deg": 0.0}
    assert cc.is_new_view(a, []) and not cc.is_new_view(dict(a, u=0.55), [a])
    assert cc.is_new_view(dict(a, u=0.7), [a]) and cc.is_new_view(dict(a, yaw_deg=20.0), [a])
    assert cc.is_new_view(dict(a, dist_m=0.8), [a])
    right_only = [[(900.0, 300.0), (800.0, 500.0)]]                # corners only in the picture's right half
    assert cc.aim_hint(right_only, 1024, 768) == "Aim the car a little more to the right."


def test_next_hint_only_asks_for_reachable_new_views():
    cc = load()
    # the 2026-11-18 capture: a board filling half the picture, at its lowest reachable spot, flat views all kept
    kept = [{"u": u, "v": v, "dist_m": 0.45, "yaw_deg": 4.0, "pitch_deg": 3.0}
            for u, v in ((0.49, 0.55), (0.50, 0.65), (0.48, 0.34), (0.62, 0.30), (0.36, 0.28), (0.48, 0.78))]
    obs = {"u": 0.53, "v": 0.78, "dist_m": 0.46, "yaw_deg": 3.0, "pitch_deg": 2.0, "hw": 0.30, "hh": 0.21}
    assert cc.next_hint(obs, kept) == "Move the board farther from the camera."   # never "lower": it cannot go lower
    small = dict(obs, v=0.5, hw=0.15, hh=0.12, dist_m=0.8)
    far_kept = kept + [dict(k, dist_m=0.8) for k in kept] + [dict(small)]
    assert cc.next_hint(small, far_kept) in ("Move the board to your left.", "Move the board to your right.")
    assert "lower" not in cc.next_hint(dict(small, v=0.86), far_kept)
