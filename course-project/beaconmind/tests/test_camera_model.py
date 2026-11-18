"""Camera model (beaconmind.camera_model; plan tasks M1.T7 and M1.T8): the field-of-view and pixel-angle formulas,
lens distortion, and the camera-to-base_link transform with its sign conventions.

Pure Python; the one comparison against OpenCV skips without it.
AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote these tests.
"""
import math

import pytest

from beaconmind import camera_model as cm

# configs/camera.json as calibrated on 2026-11-18, written out here so that a later change of the file (M1.T8 may
# refine the yaw) does not move the numbers these tests expect.
CAL = dict(width=1024, height=768, fx=1181.4979, fy=1176.6462, cx=498.4421, cy=380.7903,
           dist=(0.08327, -0.070267, -0.001828, -0.008513, 0.0),
           x_m=0.12, y_m=0.0, z_m=0.075, roll_deg=4.4, pitch_deg=-3.9, yaw_deg=2.5)


def cam(**changes):
    values = dict(CAL)
    values.update(changes)
    return cm.Camera(**values)


def level(**changes):
    values = dict(roll_deg=0.0, pitch_deg=0.0, yaw_deg=0.0)
    values.update(changes)
    return cam(**values)


# ---- the tests plan M1.T7 names

def test_hfov_90_when_fx_is_half_width():
    assert cm.hfov_deg(400, 800) == pytest.approx(90.0, abs=1e-12)


def test_hfov_60():
    assert cm.hfov_deg(400 / math.tan(math.radians(30)), 800) == pytest.approx(60.0, abs=1e-9)
    assert cm.vfov_deg(300 / math.tan(math.radians(30)), 600) == pytest.approx(60.0, abs=1e-9)


def test_center_pixel_is_zero_angles():
    assert cm.pixel_to_angles(320.0, 240.0, 500.0, 500.0, 320.0, 240.0) == (0.0, 0.0)


def test_left_pixel_has_positive_yaw():
    yaw, pitch = cm.pixel_to_angles(100.0, 240.0, 500.0, 500.0, 320.0, 240.0)
    assert yaw > 0 and pitch == 0
    assert yaw == pytest.approx(math.degrees(math.atan(220 / 500)))
    assert cm.pixel_to_angles(600.0, 240.0, 500.0, 500.0, 320.0, 240.0)[0] < 0


def test_up_pixel_has_positive_pitch_up():
    yaw, pitch = cm.pixel_to_angles(320.0, 40.0, 500.0, 500.0, 320.0, 240.0)
    assert pitch > 0 and yaw == 0
    assert cm.pixel_to_angles(320.0, 400.0, 500.0, 500.0, 320.0, 240.0)[1] < 0


# ---- the file

def test_load_camera_reads_the_calibration(course_root):
    import json
    doc = json.loads((course_root / "configs" / "camera.json").read_text(encoding="utf-8"))
    c = cm.load_camera()
    assert (c.width, c.height) == (doc["image_width"], doc["image_height"])
    assert c.fx == doc["camera_matrix"][0] and c.cy == doc["camera_matrix"][5]
    assert c.hfov_deg == pytest.approx(doc["hfov_deg"], abs=0.01)
    assert c.vfov_deg == pytest.approx(doc["vfov_deg"], abs=0.01)
    assert c.translation == (doc["extrinsics"]["x_m"], doc["extrinsics"]["y_m"], doc["extrinsics"]["z_m"])
    assert cm.load_camera(course_root / "configs" / "camera.json") == c


def test_unmeasured_extrinsics_are_refused():
    doc = {"image_width": 640, "image_height": 480, "camera_matrix": [500, 0, 320, 0, 500, 240, 0, 0, 1],
           "distortion": [0, 0, 0, 0, 0], "distortion_model": "plumb_bob",
           "extrinsics": {"x_m": 0.1, "y_m": 0.0, "z_m": 0.07, "roll_deg": None, "pitch_deg": 0.0, "yaw_deg": 0.0}}
    with pytest.raises(ValueError, match="roll_deg"):
        cm.Camera.from_dict(doc)
    doc["extrinsics"]["roll_deg"] = 0.0
    assert cm.Camera.from_dict(doc).fx == 500
    doc["camera_matrix"][1] = 0.5
    with pytest.raises(ValueError, match="skew"):
        cm.Camera.from_dict(doc)


def test_with_mount_changes_only_the_mount():
    c = cam().with_mount(yaw_deg=-1.0)
    assert c.yaw_deg == -1.0 and c.roll_deg == 4.4 and c.fx == CAL["fx"]
    with pytest.raises(TypeError):
        cam().with_mount(fx=1.0)


# ---- frames and signs

def test_level_camera_axes():
    c = level()
    assert c.direction_to_base((0, 0, 1)) == pytest.approx((1, 0, 0))      # optical axis = forward
    assert c.direction_to_base((1, 0, 0)) == pytest.approx((0, -1, 0))     # image right = the car's right
    assert c.direction_to_base((0, 1, 0)) == pytest.approx((0, 0, -1))     # image down = down


def test_rotation_is_a_proper_rotation():
    r = cam().rotation
    for i in range(3):
        for j in range(3):
            dot = sum(r[i][k] * r[j][k] for k in range(3))
            assert dot == pytest.approx(1.0 if i == j else 0.0, abs=1e-12)
    det = (r[0][0] * (r[1][1] * r[2][2] - r[1][2] * r[2][1]) - r[0][1] * (r[1][0] * r[2][2] - r[1][2] * r[2][0])
           + r[0][2] * (r[1][0] * r[2][1] - r[1][1] * r[2][0]))
    assert det == pytest.approx(1.0, abs=1e-12)


def test_rotation_order_is_yaw_pitch_roll():
    got = cm.mount_rotation(10.0, 20.0, 30.0)
    body = cm._matmul(cm.rot_z(30.0), cm._matmul(cm.rot_y(20.0), cm.rot_x(10.0)))
    want = cm._matmul(body, cm.OPTICAL_TO_BODY)
    assert all(got[i][j] == pytest.approx(want[i][j]) for i in range(3) for j in range(3))
    # the optical axis of a camera yawed 30 and pitched 20 (nose down): forward-left and down
    axis = cm._matvec(got, (0, 0, 1))
    assert axis[0] > 0 and axis[1] > 0 and axis[2] < 0
    assert math.degrees(math.atan2(axis[1], axis[0])) == pytest.approx(30.0)
    assert math.degrees(math.asin(-axis[2])) == pytest.approx(20.0)


def test_yaw_positive_points_left():
    # a camera that points left sees a target on the car's centre line to the right of the picture centre
    ahead = (2.0, 0.0, CAL["z_m"])
    u0, _ = level(dist=(0, 0, 0, 0, 0)).project_base(ahead)
    u, _ = level(dist=(0, 0, 0, 0, 0), yaw_deg=5.0).project_base(ahead)
    assert u0 == pytest.approx(CAL["cx"]) and u > u0
    assert math.degrees(math.atan((u - CAL["cx"]) / CAL["fx"])) == pytest.approx(5.0, abs=1e-6)
    assert level(yaw_deg=-5.0).project_base(ahead)[0] < CAL["cx"]


def test_pitch_positive_is_nose_down():
    # plan M1.T7 step 9: a target at lens height above the centre row (v < cy) means the camera points down
    ahead = (2.0, 0.0, CAL["z_m"])
    _, v = level(dist=(0, 0, 0, 0, 0), pitch_deg=5.0).project_base(ahead)
    assert v < CAL["cy"]
    assert math.degrees(math.atan((CAL["cy"] - v) / CAL["fy"])) == pytest.approx(5.0, abs=1e-6)
    assert level(pitch_deg=-5.0).project_base(ahead)[1] > CAL["cy"]


def test_roll_positive_turns_the_picture_content_counter_clockwise():
    # a level line in the world: with positive roll its right end is higher in the picture (smaller v)
    c = level(dist=(0, 0, 0, 0, 0), roll_deg=5.0)
    ul, vl = c.project_base((2.0, +0.3, CAL["z_m"]))        # left end
    ur, vr = c.project_base((2.0, -0.3, CAL["z_m"]))        # right end
    assert ul < ur and vr < vl
    slope = math.atan2((vl - vr) / CAL["fy"], (ur - ul) / CAL["fx"])     # fx and fy differ slightly
    assert math.degrees(slope) == pytest.approx(5.0, abs=1e-6)
    c = level(dist=(0, 0, 0, 0, 0), roll_deg=-5.0)
    assert c.project_base((2.0, -0.3, CAL["z_m"]))[1] > c.project_base((2.0, +0.3, CAL["z_m"]))[1]


def test_up_in_the_world_is_up_in_the_picture_and_left_is_left():
    c = cam()
    u0, v0 = c.project_base((1.5, 0.0, 0.10))
    assert c.project_base((1.5, 0.0, 0.40))[1] < v0          # higher point, smaller v
    assert c.project_base((1.5, 0.3, 0.10))[0] < u0          # point to the car's left, smaller u


def test_the_measured_mount_reproduces_the_extrinsics_record():
    # evidence/M1/M1.T7/extrinsics.md: the board centre, 2.5 cm right of the centre line and 1.04 m from the lens,
    # was seen 3.90 degrees right of the optical axis (2.5 yaw + 1.38 by tape). Its height, 0.12 m, is what
    # solvePnP gives for those frames through this transform. The mount is nose up, so a point at lens height is
    # below the picture centre.
    c = cam()
    u, v = c.project_base((0.12 + 1.04, -0.025, 0.12))
    yaw, _pitch = c.pixel_to_angles(u, v)
    assert yaw == pytest.approx(-3.9, abs=0.15)
    u, v = c.project_base((0.12 + 1.04, 0.0, 0.075))
    assert u > c.cx and v > c.cy


def test_base_optical_round_trip():
    c = cam()
    for p in ((1.0, 0.2, 0.23), (3.0, -1.0, 0.0), (0.5, 0.0, 0.3)):
        back = c.optical_to_base(c.base_to_optical(p))
        assert back == pytest.approx(p, abs=1e-12)
    assert c.optical_to_base((0.0, 0.0, 0.0)) == pytest.approx((0.12, 0.0, 0.075))


def test_range_and_bearing_are_from_the_axle_midpoint():
    c = level()
    rng, bearing = c.range_bearing((0.0, 0.0, 1.0))           # 1 m in front of the lens, on the optical axis
    assert rng == pytest.approx(1.12) and bearing == pytest.approx(0.0, abs=1e-9)
    rng, bearing = c.range_bearing((-0.5, 0.0, 0.88))         # half a metre to the image left = the car's left
    assert rng == pytest.approx(math.hypot(1.0, 0.5)) and bearing == pytest.approx(math.degrees(math.atan2(0.5, 1.0)))
    assert bearing > 0
    assert cm.range_bearing(0.0, -2.0) == pytest.approx((2.0, -90.0))
    assert cm.wrap_deg(190.0) == pytest.approx(-170.0) and cm.wrap_deg(-180.0) == pytest.approx(180.0)


# ---- lens

def test_distortion_round_trip():
    c = cam()
    for x, y in ((0.0, 0.0), (0.4, 0.3), (-0.42, -0.32), (0.1, -0.3)):
        xd, yd = c.distort_normalized(x, y)
        assert c.undistort_normalized(xd, yd) == pytest.approx((x, y), abs=1e-10)
    xd, yd = c.distort_normalized(0.4, 0.0)
    assert xd != pytest.approx(0.4, abs=1e-4)                 # the lens does bend the corner rays


def test_pixel_ray_round_trip_and_view_edges():
    c = cam()
    for p in ((1.0, 0.2, 0.23), (2.5, -0.6, 0.1)):
        u, v = c.project_base(p)
        ray = c.pixel_to_ray_base(u, v)
        d = [p[i] - c.translation[i] for i in range(3)]
        n = math.sqrt(sum(x * x for x in d))
        assert ray == pytest.approx(tuple(x / n for x in d), abs=1e-9)
    edges = c.view_edges_deg()
    assert all(v > 0 for v in edges.values())
    # pinhole figures 46.86 and 36.15; the true fields of view through the lens model are a little smaller
    assert edges["left"] + edges["right"] == pytest.approx(46.3, abs=0.2)
    assert edges["up"] + edges["down"] == pytest.approx(35.8, abs=0.2)
    assert c.hfov_deg == pytest.approx(46.86, abs=0.01) and c.vfov_deg == pytest.approx(36.15, abs=0.01)
    with pytest.raises(ValueError):
        c.project_optical((0.0, 0.0, -1.0))


def test_projection_matches_opencv():
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    c = cam()
    pts_base = [(1.0, 0.2, 0.23), (0.8, -0.25, 0.05), (3.0, 1.0, 0.4), (0.6, 0.0, 0.2)]
    pts_opt = np.array([c.base_to_optical(p) for p in pts_base])
    proj, _ = cv2.projectPoints(pts_opt, np.zeros(3), np.zeros(3), np.array(c.camera_matrix), np.array(c.dist))
    for mine, theirs in zip([c.project_base(p) for p in pts_base], proj.reshape(-1, 2)):
        assert mine == pytest.approx(tuple(theirs), abs=1e-6)
    und = cv2.undistortPoints(proj.reshape(-1, 1, 2), np.array(c.camera_matrix), np.array(c.dist)).reshape(-1, 2)
    for (u, v), (x, y) in zip(proj.reshape(-1, 2), und):
        assert c.undistort_normalized((u - c.cx) / c.fx, (v - c.cy) / c.fy) == pytest.approx((x, y), abs=1e-7)


# ---- when a wall tag is in view

def test_square_corner_order_is_the_viewers():
    # a tag 2 m ahead facing the car (normal toward -x): its left corners, as the car sees them, are on the car's left
    tl, tr, br, bl = cm.square_corners_base((2.0, 0.0, 0.23), 180.0, 0.08)
    assert tl == pytest.approx((2.0, 0.08, 0.31)) and tr == pytest.approx((2.0, -0.08, 0.31))
    assert br == pytest.approx((2.0, -0.08, 0.15)) and bl == pytest.approx((2.0, 0.08, 0.15))


def test_min_full_view_range_of_a_wall_tag():
    c = cam()
    black = cm.min_full_view_range(c, 0.23, 0.08, 0.0)
    page = cm.min_full_view_range(c, 0.23, 0.10, 0.0)
    assert black == pytest.approx(0.738, abs=0.003)            # the black square of a tag 0.23 m up, straight ahead
    assert page == pytest.approx(0.794, abs=0.003)             # the same with its 20 mm white border
    assert cm.square_in_view(c, black + 0.002, 0.0, 0.23, 0.08, margin_px=2.0)
    assert not cm.square_in_view(c, black - 0.005, 0.0, 0.23, 0.08, margin_px=2.0)
    # it is the top edge that leaves first, so a lower tag can come closer and a level camera sees less
    assert cm.min_full_view_range(c, 0.10, 0.08, 0.0) < 0.45
    assert cm.min_full_view_range(c.with_mount(pitch_deg=0.0), 0.23, 0.08, 0.0) > black + 0.05
    # near the side of the picture the tag needs more distance; outside the field of view it never fits
    assert cm.min_full_view_range(c, 0.23, 0.10, 15.0) > page
    assert cm.min_full_view_range(c, 0.23, 0.10, 40.0) is None
