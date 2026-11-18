"""Tag detection and tag geometry (beaconmind.perception.tags; plan task M1.T8, contracts C1 and C3).

Every frame here is synthetic: a tools/make_tags.py marker placed at a known pose and drawn through the calibrated
camera model, lens distortion and mount angles included (beaconmind.perception.synth), then detected. The whole file
skips without OpenCV or numpy.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote these tests.
"""
import importlib.util
import math
from pathlib import Path

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")
if not hasattr(cv2, "aruco"):
    pytest.skip("this OpenCV build has no aruco module", allow_module_level=True)

from beaconmind import camera_model as cm                                    # noqa: E402
from beaconmind.perception import synth, tags                                 # noqa: E402

TOOLS = Path(__file__).resolve().parents[2] / "tools"

# configs/camera.json of 2026-11-18, written out so that a later yaw refinement does not move these tests.
CAL = dict(width=1024, height=768, fx=1181.4979, fy=1176.6462, cx=498.4421, cy=380.7903,
           dist=(0.08327, -0.070267, -0.001828, -0.008513, 0.0),
           x_m=0.12, y_m=0.0, z_m=0.075, roll_deg=4.4, pitch_deg=-3.9, yaw_deg=2.5)
CAM = cm.Camera(**CAL)
WALL_TAG_HEIGHT = 0.23
LOOK = dict(wall=150.0, black=100.0, white=185.0)        # grey levels of real frames (synth.REAL_FRAME_2026_11_18)


def _make_tags():
    spec = importlib.util.spec_from_file_location("make_tags", TOOLS / "make_tags.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MAKE_TAGS = _make_tags()
_MARKERS = {}


def marker(tag_id):
    """The picture tools/make_tags.py prints for this id: the black square (40 px per cell) plus its white border.
    OpenCV before 4.7 has no generateImageMarker, which make_tags.py calls; there the same picture comes from
    tags.marker_image and make_tags' own border function."""
    if tag_id not in _MARKERS:
        try:
            square = MAKE_TAGS.render_marker(tag_id, 320)
        except AttributeError:
            square = tags.marker_image(tag_id, 320)
        _MARKERS[tag_id], border = MAKE_TAGS.add_white_border(square)
        assert border == 40
    return _MARKERS[tag_id]


def tag_at(tag_id, range_m, bearing_deg, height_m=WALL_TAG_HEIGHT, **pose):
    tag = synth.tag_at(tag_id, range_m, bearing_deg, height_m, **pose)
    tag["marker"] = marker(tag_id)
    return tag


def frame(tag_list, camera=CAM, **look):
    values = dict(LOOK)
    values.update(look)
    return synth.render_scene(camera, tag_list, **values)


def only(dets):
    assert len(dets) == 1, [(d["id"], d.get("reject")) for d in dets]
    return dets[0]


def height_for(range_m):
    """Wall tags are 0.23 m up and are whole in the picture only from about 0.8 m; closer placements use a tag held
    low, as on the bench stand of the tag pilot."""
    return WALL_TAG_HEIGHT if range_m >= 0.85 else 0.095


def grid():
    cases = []
    for range_m in (0.4, 0.5, 0.6, 0.8, 1.0, 1.5, 2.0, 2.5, 3.0):
        for bearing in (-20.0, -15.0, -10.0, -5.0, 0.0, 5.0, 10.0, 15.0, 20.0):
            half = 0.08 if range_m < 0.5 else 0.10       # at 0.4 m only the black square fits in the picture
            if cm.square_in_view(CAM, range_m, bearing, height_for(range_m), half, margin_px=6.0):
                cases.append((range_m, bearing))
    return cases


GRID = grid()


def test_grid_covers_the_field_of_view():
    assert {r for r, _ in GRID} == {0.4, 0.5, 0.6, 0.8, 1.0, 1.5, 2.0, 2.5, 3.0}
    bearings = {b for _, b in GRID}
    assert min(bearings) <= -15.0 and max(bearings) >= 15.0
    assert len(GRID) >= 40


# ------------------------------------------------------------------ markers

def test_marker_image_is_the_make_tags_marker():
    try:
        want = MAKE_TAGS.render_marker(7, 160)
    except AttributeError:
        pytest.skip("tools/make_tags.py needs OpenCV 4.7+ (generateImageMarker)")
    assert np.array_equal(tags.marker_image(7, 160), want)


def test_marker_cells_have_a_black_ring():
    cells = tags.marker_cells(3)
    assert cells.shape == (8, 8)
    assert cells[0].sum() == 0 and cells[-1].sum() == 0 and cells[:, 0].sum() == 0 and cells[:, -1].sum() == 0
    assert 0 < cells[1:-1, 1:-1].sum() < 36
    assert not np.array_equal(tags.marker_cells(3), tags.marker_cells(4))


# ------------------------------------------------------------------ range and bearing

@pytest.mark.parametrize("range_m,bearing_deg", GRID)
def test_range_and_bearing_on_clean_frames(range_m, bearing_deg):
    tag = tag_at(3, range_m, bearing_deg, height_for(range_m))
    det = only(tags.detect_tags(frame([tag]), CAM))
    assert det["id"] == 3 and det["refined"]
    assert det["range_m"] == pytest.approx(range_m, rel=0.005)                # asked: about 2 %
    assert det["bearing_deg"] == pytest.approx(bearing_deg, abs=0.1)          # asked: about 0.5 degree
    assert det["base_xyz_m"][2] == pytest.approx(height_for(range_m), abs=0.005)
    assert det["reproj_px"] < 0.3 and det["hamming"] == 0
    assert 0.5 <= det["quality"] <= 1.0


@pytest.mark.parametrize("range_m,bearing_deg", GRID)
def test_range_and_bearing_on_real_like_frames(range_m, bearing_deg):
    # blur, sensor noise and JPEG at the levels measured from real frames; a tag turned 25 degrees on its wall
    rng = np.random.default_rng(int(range_m * 1000) + int(bearing_deg) + 100)
    tag = tag_at(11, range_m, bearing_deg, height_for(range_m), incidence_deg=25.0 if range_m >= 0.6 else 0.0)
    picture = synth.real_like(frame([tag]), rng=rng)
    det = only(tags.detect_tags(picture, CAM))
    assert det["id"] == 11
    assert det["range_m"] == pytest.approx(range_m, rel=0.02)
    assert det["bearing_deg"] == pytest.approx(bearing_deg, abs=0.5)
    assert det["quality"] >= 0.5


def test_range_is_from_the_axle_midpoint_not_the_lens():
    det = only(tags.detect_tags(frame([tag_at(3, 1.0, 0.0)]), CAM))
    lens_to_tag = math.sqrt((1.0 - 0.12) ** 2 + (WALL_TAG_HEIGHT - 0.075) ** 2)
    assert det["camera_range_m"] == pytest.approx(lens_to_tag, abs=0.003)
    assert det["range_m"] == pytest.approx(1.0, abs=0.003)
    assert det["range_m"] - det["camera_range_m"] > 0.09
    assert det["base_xyz_m"] == pytest.approx([1.0, 0.0, WALL_TAG_HEIGHT], abs=0.004)


# ------------------------------------------------------------------ signs: left/right, up/down, roll

def test_left_is_positive_bearing():
    left = only(tags.detect_tags(frame([tag_at(3, 1.5, +12.0)]), CAM))
    right = only(tags.detect_tags(frame([tag_at(3, 1.5, -12.0)]), CAM))
    assert left["bearing_deg"] == pytest.approx(12.0, abs=0.1) and right["bearing_deg"] == pytest.approx(-12.0, abs=0.1)
    assert left["center_px"][0] < CAM.cx < right["center_px"][0]             # left in the room = left in the picture
    assert left["base_xyz_m"][1] > 0 > right["base_xyz_m"][1]


def test_higher_tag_is_higher_in_base_link_and_in_the_picture():
    low = only(tags.detect_tags(frame([tag_at(3, 1.5, 4.0, 0.15)]), CAM))
    high = only(tags.detect_tags(frame([tag_at(3, 1.5, 4.0, 0.40)]), CAM))
    assert low["base_xyz_m"][2] == pytest.approx(0.15, abs=0.004)
    assert high["base_xyz_m"][2] == pytest.approx(0.40, abs=0.004)
    assert high["center_px"][1] < low["center_px"][1]
    # height does not leak into the floor-plane range
    assert low["range_m"] == pytest.approx(1.5, abs=0.004) and high["range_m"] == pytest.approx(1.5, abs=0.004)


@pytest.mark.parametrize("roll,pitch,yaw", [(9.0, 0.0, 0.0), (-9.0, 0.0, 0.0), (0.0, 6.0, 0.0), (0.0, -6.0, 0.0),
                                            (0.0, 0.0, 7.0), (0.0, 0.0, -7.0), (8.0, -5.0, 6.0), (-7.0, 4.0, -5.0),
                                            (10.0, 6.0, -8.0)])
def test_mount_angles_are_taken_out(roll, pitch, yaw):
    # asymmetric placement (left of centre, above the lens), so a wrong sign of any angle moves the answer
    camera = CAM.with_mount(roll_deg=roll, pitch_deg=pitch, yaw_deg=yaw)
    tag = tag_at(5, 1.6, 7.0, 0.20, incidence_deg=20.0)
    det = only(tags.detect_tags(frame([tag], camera), camera))
    assert det["range_m"] == pytest.approx(1.6, abs=0.005)
    assert det["bearing_deg"] == pytest.approx(7.0, abs=0.1)
    assert det["base_xyz_m"][2] == pytest.approx(0.20, abs=0.005)
    assert cm.wrap_deg(det["normal_yaw_deg"] - tag["normal_yaw_deg"]) == pytest.approx(0.0, abs=2.0)
    assert det["up_error_deg"] < 2.0


def test_ignoring_the_mount_gives_the_expected_wrong_answer():
    # the same picture read with a level, straight camera: bearing is off by the yaw, height by pitch and roll
    picture = frame([tag_at(5, 2.0, 0.0)])
    level = CAM.with_mount(roll_deg=0.0, pitch_deg=0.0, yaw_deg=0.0)
    good = only(tags.detect_tags(picture, CAM))
    naive = only(tags.detect_tags(picture, level))
    assert good["bearing_deg"] == pytest.approx(0.0, abs=0.1)
    assert naive["bearing_deg"] == pytest.approx(-2.5 * (2.0 - 0.12) / 2.0, abs=0.3)   # yaw seen from the lens
    assert naive["base_xyz_m"][2] < good["base_xyz_m"][2] - 0.08                       # nose-up mount ignored
    assert naive["up_error_deg"] == pytest.approx(math.hypot(4.4, 3.9), abs=1.0)       # roll and pitch show as tilt


def test_roll_sign_with_two_tags():
    # two tags at the same height left and right: with the measured roll (+4.4) the right one is higher in the
    # picture, and both still come out at the same height above the floor
    dets = tags.detect_tags(frame([tag_at(1, 1.8, 10.0), tag_at(2, 1.8, -10.0)]), CAM)
    assert [d["id"] for d in dets] == [1, 2]                                           # sorted left to right
    left, right = dets
    assert right["center_px"][1] < left["center_px"][1]
    assert left["base_xyz_m"][2] == pytest.approx(right["base_xyz_m"][2], abs=0.004)


# ------------------------------------------------------------------ orientation of the tag

@pytest.mark.parametrize("incidence", [-50.0, -30.0, 0.0, 30.0, 50.0])
def test_normal_yaw_and_incidence(incidence):
    tag = tag_at(9, 1.2, 5.0, incidence_deg=incidence)
    det = only(tags.detect_tags(frame([tag]), CAM))
    assert cm.wrap_deg(det["normal_yaw_deg"] - tag["normal_yaw_deg"]) == pytest.approx(0.0, abs=1.5)
    assert det["incidence_deg"] == pytest.approx(abs(incidence), abs=1.5)
    assert det["range_m"] == pytest.approx(1.2, abs=0.005) and det["bearing_deg"] == pytest.approx(5.0, abs=0.1)
    if incidence:
        assert det["normal_yaw_alt_deg"] is not None


def test_exact_corners_that_break_ippe_still_give_a_pose():
    # OpenCV 5.1's IPPE returns not-a-number for the noise-free corners of this placement; _poses must recover
    tag = synth.tag_at(3, 1.0, 0.0, WALL_TAG_HEIGHT)
    pix = synth.tag_corners_px(CAM, tag)
    norm = cv2.undistortPoints(pix.reshape(-1, 1, 2), np.array(CAM.camera_matrix), np.array(CAM.dist)).reshape(-1, 2)
    poses = tags._poses(norm, 0.16)
    assert poses and all(np.all(np.isfinite(r)) and np.all(np.isfinite(t)) for r, t in poses)
    rng, bearing = CAM.range_bearing(tuple(poses[0][1]))
    assert rng == pytest.approx(1.0, abs=1e-4) and bearing == pytest.approx(0.0, abs=1e-3)


def test_leaning_and_spun_tags():
    lean = only(tags.detect_tags(frame([tag_at(4, 1.2, 0.0, lean_deg=12.0)]), CAM))
    assert lean["up_error_deg"] == pytest.approx(12.0, abs=1.5)
    spun = only(tags.detect_tags(frame([tag_at(4, 1.2, 0.0, spin_deg=90.0)]), CAM))
    assert spun["up_error_deg"] == pytest.approx(90.0, abs=1.5)                        # a page mounted on its side
    assert spun["range_m"] == pytest.approx(1.2, abs=0.005)


# ------------------------------------------------------------------ rejection rules

def test_id_outside_the_layout_is_rejected():
    accepted, rejected = tags.detect_tags(frame([tag_at(40, 1.2, 0.0)]), CAM, return_rejected=True)
    assert accepted == [] and [(d["id"], d["reject"]) for d in rejected] == [(40, "id_out_of_range")]
    assert only(tags.detect_tags(frame([tag_at(40, 1.2, 0.0)]), CAM, id_range=(0, 586)))["id"] == 40


def test_cut_off_tag_is_never_accepted():
    # a wall tag closer than its whole-tag distance: the top leaves the picture
    for range_m in (0.45, 0.55, 0.65, 0.70):
        accepted, _rejected = tags.detect_tags(frame([tag_at(3, range_m, 0.0)]), CAM, return_rejected=True)
        assert accepted == []
    # a tag half out of the right side
    accepted, _rejected = tags.detect_tags(frame([tag_at(3, 1.5, -22.5)]), CAM, return_rejected=True)
    assert accepted == []
    # a corner inside the border margin is the at_border rule
    edge = cm.min_full_view_range(CAM, WALL_TAG_HEIGHT, 0.08, 0.0, margin_px=0.5)
    accepted, rejected = tags.detect_tags(frame([tag_at(3, edge, 0.0)]), CAM, return_rejected=True, border_px=8.0)
    assert accepted == [] and all(d["reject"] == "at_border" for d in rejected)


def test_small_far_tag_is_rejected_as_too_small():
    picture = frame([tag_at(3, 3.0, 0.0)])
    assert only(tags.detect_tags(picture, CAM))["side_px"] == pytest.approx(65.5, abs=3.0)
    accepted, rejected = tags.detect_tags(picture, CAM, return_rejected=True, min_side_px=80.0)
    assert accepted == [] and only(rejected)["reject"] == "too_small"


def test_height_rule():
    picture = frame([tag_at(3, 2.5, 0.0, 0.60)])                                       # a tag 0.6 m up is not a wall tag
    assert len(tags.detect_tags(picture, CAM)) == 1                                    # rule off by default
    accepted, rejected = tags.detect_tags(picture, CAM, tag_center_height_m=WALL_TAG_HEIGHT, return_rejected=True)
    assert accepted == [] and only(rejected)["reject"] == "height"
    assert len(tags.detect_tags(frame([tag_at(3, 1.5, 0.0)]), CAM, tag_center_height_m=WALL_TAG_HEIGHT)) == 1


def test_range_and_view_angle_rules():
    picture = frame([tag_at(3, 2.0, 0.0, incidence_deg=40.0)])
    assert len(tags.detect_tags(picture, CAM)) == 1
    accepted, rejected = tags.detect_tags(picture, CAM, return_rejected=True, max_range_m=1.5)
    assert accepted == [] and only(rejected)["reject"] == "range"
    accepted, rejected = tags.detect_tags(picture, CAM, return_rejected=True, max_view_angle_deg=30.0)
    assert accepted == [] and only(rejected)["reject"] == "oblique"


def test_low_contrast_is_rejected_by_margin():
    picture = frame([tag_at(3, 1.2, 0.0)], black=120.0, white=132.0, wall=126.0)
    accepted, rejected = tags.detect_tags(picture, CAM, return_rejected=True)
    assert accepted == []
    assert all(d["reject"] == "low_margin" for d in rejected)                          # or not found at all


@pytest.mark.parametrize("look", [dict(LOOK), dict(wall=135.0, black=120.0, white=148.0)])
def test_tag_near_the_top_of_the_picture_at_normal_and_low_contrast(look):
    # a wall tag at its closest whole-tag distance sits just under the picture's top edge. The large threshold
    # windows that a low-contrast tag needs must not cost the normal-contrast one (tags.ARUCO_PASSES).
    rng = np.random.default_rng(21)
    found = 0
    cases = [(r, b, inc) for r in (0.80, 0.82) for b in (-4.0, 0.0, 4.0, 8.0) for inc in (-20.0, 0.0, 20.0)
             if cm.square_in_view(CAM, r, b, WALL_TAG_HEIGHT, 0.10, margin_px=4.0, incidence_deg=inc)]
    assert len(cases) >= 12
    for range_m, bearing, inc in cases:
        tag = tag_at(6, range_m, bearing, incidence_deg=inc)
        picture = synth.real_like(frame([tag], **look), rng=rng, noise_sigma=3.0)
        dets = tags.detect_tags(picture, CAM)
        if len(dets) == 1 and dets[0]["id"] == 6:
            found += 1
            assert dets[0]["range_m"] == pytest.approx(range_m, rel=0.01)
    assert found == len(cases)


def test_find_quads_single_pass_and_two_pass():
    picture = frame([tag_at(3, 1.5, 0.0)])
    both = tags.find_quads(picture)
    assert [tag_id for _quad, tag_id in both] == [3]                     # found by both passes, listed once
    one = tags.find_quads(picture, {"adaptiveThreshWinSizeMax": 23})
    assert [tag_id for _quad, tag_id in one] == [3]
    assert np.allclose(both[0][0], one[0][0], atol=2.0)
    with pytest.raises(AttributeError):
        tags.find_quads(picture, {"noSuchField": 1})


def test_empty_and_noise_frames_give_nothing():
    assert tags.detect_tags(np.full((768, 1024), 128, np.uint8), CAM) == []
    noise = np.random.default_rng(5).integers(0, 256, (768, 1024), dtype=np.uint8)
    assert tags.detect_tags(noise, CAM) == []
    assert tags.detect_tags(noise, CAM, return_rejected=True) == ([], [])


def test_input_checks():
    with pytest.raises(ValueError, match="640 x 480"):
        tags.detect_tags(np.zeros((480, 640), np.uint8), CAM)
    with pytest.raises(TypeError):
        tags.detect_tags(np.zeros((768, 1024), np.float32), CAM)
    with pytest.raises(TypeError, match="min_size"):
        tags.detect_tags(np.zeros((768, 1024), np.uint8), CAM, min_size=3)
    with pytest.raises(ValueError):
        tags.detect_tags(np.zeros((768, 1024), np.uint8), CAM, tag_size_m=0.0)


def test_bgr_frame_gives_the_same_answer():
    grey = frame([tag_at(3, 1.3, -6.0)])
    a = only(tags.detect_tags(grey, CAM))
    b = only(tags.detect_tags(cv2.cvtColor(grey, cv2.COLOR_GRAY2BGR), CAM))
    assert a["range_m"] == pytest.approx(b["range_m"], abs=1e-9) and a["bearing_deg"] == pytest.approx(b["bearing_deg"], abs=1e-9)


def test_tag_size_scales_the_range_from_the_lens():
    # the size convention: tag_size_m is the edge of the black square. A wrong size scales the lens distance.
    picture = frame([tag_at(3, 1.5, 0.0)])
    right = only(tags.detect_tags(picture, CAM))
    wrong = only(tags.detect_tags(picture, CAM, tag_size_m=0.20))
    assert wrong["camera_range_m"] == pytest.approx(1.25 * right["camera_range_m"], rel=1e-3)


# ------------------------------------------------------------------ quality, code check

def test_code_check_and_quality():
    near = only(tags.detect_tags(frame([tag_at(3, 1.0, 0.0)]), CAM))
    assert near["hamming"] == 0
    assert near["decision_margin"] == pytest.approx((185.0 - 100.0) / 2.0, abs=3.0)
    assert near["contrast"] == pytest.approx(85.0, abs=3.0)
    assert near["quality"] > 0.95
    rng = np.random.default_rng(3)
    blurred = only(tags.detect_tags(synth.real_like(frame([tag_at(3, 3.0, 0.0)]), rng=rng, blur_sigma_px=2.0), CAM))
    assert 0.0 < blurred["quality"] < near["quality"]
    assert blurred["decision_margin"] < near["decision_margin"]
    assert tags.quality_of(near) == pytest.approx(near["quality"])
    weak = dict(near, min_side_px=27.0)
    assert tags.quality_of(weak) == pytest.approx(0.5)                                # (27 - 14) / (40 - 14)
    assert tags.quality_of(dict(near, hamming=3)) == 0.0
    assert tags.quality_of(dict(near, reproj_px=99.0)) == 0.0


def test_corner_refit_beats_the_detectors_corners():
    rng = np.random.default_rng(8)
    refined, raw = [], []
    for range_m in (1.5, 2.0, 2.5, 3.0):
        picture = synth.real_like(frame([tag_at(3, range_m, 3.0)]), rng=rng)
        refined.append(abs(only(tags.detect_tags(picture, CAM))["range_m"] - range_m) / range_m)
        raw.append(abs(only(tags.detect_tags(picture, CAM, refine=False))["range_m"] - range_m) / range_m)
    assert max(refined) < 0.005
    assert sum(refined) < sum(raw)


# ------------------------------------------------------------------ several tags, several frames, the observation

def test_two_tags_with_the_same_id():
    # the layout repeats ids on two tags; both must come out, left one first
    dets = tags.detect_tags(frame([tag_at(3, 2.0, -9.0), tag_at(3, 1.4, 11.0)]), CAM)
    assert [d["id"] for d in dets] == [3, 3]
    assert dets[0]["bearing_deg"] == pytest.approx(11.0, abs=0.1) and dets[0]["range_m"] == pytest.approx(1.4, abs=0.005)
    assert dets[1]["bearing_deg"] == pytest.approx(-9.0, abs=0.1) and dets[1]["range_m"] == pytest.approx(2.0, abs=0.005)


def _stop(n_frames, tag_list, seed, drop=()):
    rng = np.random.default_rng(seed)
    clean = frame(tag_list)
    out = []
    for index in range(n_frames):
        out.append([] if index in drop else tags.detect_tags(synth.real_like(clean, rng=rng), CAM))
    return out


def test_fuse_frames_follows_contract_c3():
    stop = _stop(5, [tag_at(3, 2.0, -9.0), tag_at(3, 1.4, 11.0), tag_at(7, 1.0, 0.0)], seed=4, drop=(2,))
    fused = tags.fuse_frames(stop, obs_frames=5, obs_min_frames=3)
    assert [f["id"] for f in fused] == [3, 7, 3]                                       # left to right, two tags "3"
    assert all(f["frames_seen"] == 4 and f["quality"] == pytest.approx(0.8) for f in fused)
    assert fused[0]["range_m"] == pytest.approx(1.4, abs=0.01) and fused[2]["range_m"] == pytest.approx(2.0, abs=0.01)
    assert fused[1]["bearing_deg"] == pytest.approx(0.0, abs=0.2)
    assert all(f["range_sd_m"] is not None and f["range_sd_m"] < 0.01 for f in fused)
    # seen in too few frames: dropped
    assert tags.fuse_frames(stop[:3], obs_frames=5, obs_min_frames=3) == []
    assert tags.fuse_frames([], obs_frames=0) == []
    one = tags.fuse_frames(stop[:1], obs_min_frames=1)
    assert len(one) == 3 and one[0]["range_sd_m"] is None and one[0]["quality"] == 1.0


def test_observation_list_matches_the_schema():
    from beaconmind.schemas import validate
    dets = tags.detect_tags(frame([tag_at(3, 2.0, -9.0), tag_at(12, 1.4, 11.0)]), CAM)
    listed = tags.to_observation_detections(dets)
    assert listed == [{"det": 0, "id": 12, "range_m": 1.4, "bearing_deg": 11.0, "quality": listed[0]["quality"]},
                      {"det": 1, "id": 3, "range_m": 2.0, "bearing_deg": -9.0, "quality": listed[1]["quality"]}]
    assert all(round(d["quality"], 2) == d["quality"] and 0.5 <= d["quality"] <= 1.0 for d in listed)
    assert [d["id"] for d in tags.to_observation_detections(dets, hide_ids=True)] == [None, None]
    observation = {
        "obs_id": "real-s000", "step": 0, "source": "real", "mode": "closed_loop", "status": "ok", "error": None,
        "sensors": {"camera": "ok", "imu": "ok", "pico": "armed"}, "odometry": None,
        "last_move": {"action": "FORWARD_10", "result": "not_called"},
        "counters": {"steps_left": 150, "odometer_m": 0.0, "travel_since_fix_m": 0.0, "turns_since_fix": 0,
                     "consecutive_contacts": 0, "consecutive_slips": 0, "consecutive_errors": 0, "latched": False},
        "safety": {"forward_allowed": [], "backward_allowed": False, "turn_allowed": True, "scan_allowed": True,
                   "done_range_m": 0.55},
        "detections": listed}
    try:
        errors = validate("observation", observation)
    except ImportError:
        pytest.skip("jsonschema is not installed")
    assert errors == []
    internal = tags.to_internal_detections(dets)
    assert [d["det"] for d in internal] == [0, 1] and internal[0]["id"] == 12
    assert internal[0]["base_xyz_m"][2] == pytest.approx(WALL_TAG_HEIGHT, abs=0.005) and internal[0]["frames_seen"] == 1
    fused = tags.fuse_frames([dets, dets, dets])
    assert tags.to_observation_detections(fused)[0]["quality"] == 1.0
    assert tags.to_internal_detections(fused)[0]["frames_seen"] == 3


def letter_page(tag_id, dpi=150):
    """A US-Letter sheet laid out as tools/room_layout.py prints the wall tags: the tag (make_tags marker with its
    white border) centred sideways, its centre 110 mm above the sheet's bottom edge, a title, text lines and a 100 mm
    scale bar above it. Returns the "page" dict synth.render_scene takes."""
    mm = dpi / 25.4
    width, height = int(round(8.5 * dpi)), int(round(11 * dpi))
    page = np.full((height, width), 255, np.uint8)
    side = 8 * int(round(160.0 * mm / 8.0))
    sheet = cv2.resize(marker(tag_id), (side + 2 * (side // 8),) * 2, interpolation=cv2.INTER_NEAREST)
    cy = height - 110.0 * mm
    x0, y0 = (width - sheet.shape[1]) // 2, int(round(cy - sheet.shape[0] / 2.0))
    page[y0:y0 + sheet.shape[0], x0:x0 + sheet.shape[1]] = sheet
    cv2.putText(page, "T%02d  ID %d" % (tag_id, tag_id), (int(20 * mm), int(28 * mm)), cv2.FONT_HERSHEY_SIMPLEX, 0.09 * mm, 0, 4)
    cv2.putText(page, "Bottom edge of this page on top of the baseboard", (int(20 * mm), int(48 * mm)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.03 * mm, 0, 2)
    page[int(62 * mm):int(64 * mm), int(20 * mm):int(120 * mm)] = 0                    # the scale bar
    return {"image": page, "m_per_px": 0.0254 / dpi, "center_px": (x0 + sheet.shape[1] / 2.0, y0 + sheet.shape[0] / 2.0)}


@pytest.mark.parametrize("wall", [150.0, 185.0, 90.0])
def test_whole_printed_page_on_walls_of_different_brightness(wall):
    # the sheet is not square around the tag, carries text and a black bar, and on a wall as bright as the paper
    # (185) its outline disappears; on a darker wall it is one more quad around the tag
    rng = np.random.default_rng(int(wall))
    for tag_id, range_m, bearing in ((23, 0.9, 3.0), (3, 1.6, -9.0), (15, 2.4, 8.0), (29, 3.2, -4.0)):
        tag = synth.tag_at(tag_id, range_m, bearing, WALL_TAG_HEIGHT, incidence_deg=20.0)
        tag["page"] = letter_page(tag_id)
        picture = synth.real_like(synth.render_scene(CAM, [tag], wall=wall, black=100.0, white=185.0), rng=rng)
        accepted, rejected = tags.detect_tags(picture, CAM, tag_center_height_m=WALL_TAG_HEIGHT, return_rejected=True)
        det = only(accepted)
        assert det["id"] == tag_id and rejected == []
        assert det["range_m"] == pytest.approx(range_m, rel=0.01)
        assert det["bearing_deg"] == pytest.approx(bearing, abs=0.2)


# ------------------------------------------------------------------ the renderer itself

def test_renderer_puts_corners_where_the_camera_model_says():
    # independent of the detector: the black square's corner pixels found by thresholding the rendered picture
    tag = tag_at(3, 1.0, 6.0)
    picture = synth.render_scene(CAM, [tag], wall=255.0, black=0.0, white=255.0)
    ys, xs = np.nonzero(picture < 128)
    want = synth.tag_corners_px(CAM, tag)
    # (1.5 px: the square is turned by the roll, so its extreme tips cover less than half a pixel)
    assert xs.min() == pytest.approx(want[:, 0].min(), abs=1.5) and xs.max() == pytest.approx(want[:, 0].max(), abs=1.5)
    assert ys.min() == pytest.approx(want[:, 1].min(), abs=1.5) and ys.max() == pytest.approx(want[:, 1].max(), abs=1.5)
    # top-left of the upright tag is up and to the left in the picture
    assert want[0][0] < want[1][0] and want[0][1] < want[3][1]


def test_degrade_keeps_size_and_type():
    picture = frame([tag_at(3, 1.5, 0.0)])
    out = synth.degrade(picture, blur_sigma_px=1.0, noise_sigma=3.0, jpeg_quality=62, motion_px=4, gamma=2.2,
                        rng=np.random.default_rng(1))
    assert out.shape == picture.shape and out.dtype == np.uint8
    assert not np.array_equal(out, picture)
    assert np.array_equal(synth.degrade(picture), picture)
