"""AprilTag 36h11 detection and tag geometry from one camera frame (plan task M1.T8; contracts C1 and C3).

    from beaconmind.camera_model import load_camera
    from beaconmind.perception.tags import detect_tags, to_observation_detections
    dets = detect_tags(frame, load_camera())            # frame: grey or BGR uint8, 1024 x 768
    obs_list = to_observation_detections(dets)          # the bm.observation-1 "detections" list

What one detection holds (all angles in degrees, all lengths in metres):

- ``id``; ``range_m`` and ``bearing_deg``: floor-plane range from the wheel-axle midpoint to the tag centre and its
  bearing from the car's +x axis, counter-clockwise (left) positive: contract C1, the numbers
  ``beaconmind.geometry.predict_observation`` gives in the simulator. NOT the distance from the lens.
- ``base_xyz_m``: the tag centre in base_link (z = height above the floor).
- ``camera_xyz_m``, ``camera_rvec``: the tag pose in camera_optical_frame (Rodrigues vector; the tag frame has x to
  the viewer's right, y up, z out of the tag toward the viewer). ``camera_range_m``: straight-line lens-to-centre.
- ``normal_yaw_deg``: yaw in base_link of the tag's outward normal; ``normal_yaw_alt_deg``: the same for the second
  solution of the planar-pose ambiguity (None when there is none). ``incidence_deg``: floor-plane angle between that
  normal and the line from the tag to the axle midpoint (the simulator's definition, 0 = facing the car).
  ``view_angle_deg``: 3-D angle between the normal and the line from the tag to the lens. ``up_error_deg``: how far
  the tag's own "up" is from vertical (a wall tag reads near 0; a large value at short range means a tilted page or
  wrong mount angles).
- ``reproj_px``: RMS distance between the four measured corners and the corners of the fitted pose, in pixels;
  ``reproj_alt_px`` for the second solution.
- ``side_px`` (mean) and ``min_side_px``: side lengths of the black square in the picture; ``corners_px``: the four
  refined corners (top-left, top-right, bottom-right, bottom-left of the upright tag); ``center_px``.
- ``hamming``: number of the 36 data cells read on the wrong side of the black/white threshold when this module
  re-reads the tag under the refined corners. ``decision_margin``: mean over the 36 data cells of the distance in
  grey levels from the cell's brightness to that threshold, counted negative for a wrong cell. Both are computed
  here because OpenCV's aruco detector reports neither; decision_margin is in the spirit of AprilTag 3's value of the
  same name but is not the same number.
- ``quality`` in 0..1, see quality_of().
- ``refined``: True when the corners come from the edge fit, False when the fit failed and the detector's own
  corners were used.

Pipeline. (1) cv2.aruco finds and decodes candidate quads (DICT_APRILTAG_36h11; both the OpenCV 4.5 function API and
the 4.7+ ArucoDetector class are supported), in three passes with small, large and larger threshold windows (ARUCO_PASSES). (2) Corners are refitted here, the same way on every OpenCV version: sub-
pixel edge points along each side of the black square, lens distortion removed, a straight line fitted to each side,
corners = line intersections. (3) cv2.solvePnPGeneric with SOLVEPNP_IPPE_SQUARE on the undistorted corners gives up
to two poses; the one with the smaller reprojection error is kept unless the two errors are close, in which case the
pose whose tag stands more upright wins (tags are on walls). (4) The tag centre goes through the camera's mount
rotation and lens offset into base_link (camera_model.py), and range and bearing are taken there in the floor plane.

A detection is rejected (it is then only in the second list of detect_tags(..., return_rejected=True), with
``reject`` naming the rule) when: ``id_out_of_range`` its id is outside id_range (0..29; the 36h11 family has 587
codes, so other ids are false reads or foreign tags); ``too_small`` its shortest side is under min_side_px;
``at_border`` a corner is within border_px of the picture's edge (a cut-off tag gives a wrong size and so a wrong
range); ``pnp_failed``; ``behind`` the pose is not in front of the lens; ``reproj`` the reprojection error is above
max_reproj_px + max_reproj_rel * side_px; ``hamming`` more than max_hamming data cells read wrong; ``low_margin`` the
decision margin is under min_margin; ``oblique`` view_angle_deg is above max_view_angle_deg; ``range`` range_m is
above max_range_m; ``height`` (only when tag_center_height_m is given) the tag centre's height above the floor is
off by more than height_tol_m + height_tol_per_m * range_m; ``no_size`` tag_size_m is a per-id dict without this id
and without a "default"; ``duplicate`` the detector returned the same tag twice
(same id, centres closer than half a side) and this is the one with the larger reprojection error.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this module. The approach (quad detection, edge-line
corner refit, planar pose with two solutions) follows the published descriptions of AprilTag 2 (Wang and Olson, IROS
2016) and of IPPE (Collins and Bartoli, IJCV 2014) as OpenCV implements them; the code here calls OpenCV and is not
copied from either.
AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: added the third pass of ARUCO_PASSES (63 to 103 px windows),
from the tag pilot's real frames of 2026-11-25.
"""
import math

import cv2
import numpy as np

from beaconmind.camera_model import range_bearing, wrap_deg

FAMILY = "tag36h11"
CELLS = 8                      # 6 x 6 data cells inside a one-cell black ring

DEFAULTS = {
    "id_range": (0, 29),
    "min_side_px": 14.0,
    "border_px": 3.0,
    "max_reproj_px": 1.0,
    "max_reproj_rel": 0.02,
    "max_hamming": 2,
    "min_margin": 8.0,
    "max_view_angle_deg": 75.0,
    "max_range_m": 6.0,
    "height_tol_m": 0.10,
    "height_tol_per_m": 0.06,
    # quality_of()
    "quality_side_full_px": 40.0,
    "quality_margin_full": 20.0,
    # pose choice between the two planar solutions
    "ambiguity_ratio": 2.0,
    "ambiguity_floor_px": 0.3,
}


# ------------------------------------------------------------------ OpenCV aruco, both API generations

def aruco_dictionary():
    aruco = cv2.aruco
    if hasattr(aruco, "getPredefinedDictionary"):
        return aruco.getPredefinedDictionary(aruco.DICT_APRILTAG_36h11)
    return aruco.Dictionary_get(aruco.DICT_APRILTAG_36h11)


def marker_image(tag_id, side_px):
    """The black square of tag `tag_id` (ring included, no white border) as a side_px x side_px uint8 picture."""
    aruco = cv2.aruco
    if hasattr(aruco, "generateImageMarker"):
        return aruco.generateImageMarker(aruco_dictionary(), int(tag_id), int(side_px))
    return aruco.drawMarker(aruco_dictionary(), int(tag_id), int(side_px))


_BITS = {}


def marker_cells(tag_id):
    """8 x 8 array, 1 for a white cell and 0 for a black one (row 0 = the tag's top)."""
    tag_id = int(tag_id)
    if tag_id not in _BITS:
        _BITS[tag_id] = (marker_image(tag_id, CELLS) > 127).astype(np.uint8)
    return _BITS[tag_id]


# The quad search runs once per entry, each a set of cv2.aruco.DetectorParameters fields changed from OpenCV's
# defaults, and the finds are merged. Pass 1 is OpenCV's own adaptive-threshold windows (3, 13, 23 px). Pass 2 uses
# large windows (33 and 53 px): a low-contrast tag that fills much of the picture is outlined only with those
# (simulated frames at a third of the real contrast, tag at 0.8 m: 32 of 40 found by pass 1 alone, 40 of 40 with
# both). The passes are separate because OpenCV keeps one quad per group of nearby quads over all windows before it
# decodes: with every window in one pass, a tag near the top of the picture was lost in 3 of 40 simulated frames at
# normal contrast that pass 1 alone finds.
# Pass 3 (63, 83, 103 px; 2026-11-25) is for a close tag wider than pass 2's windows. Real frames of the tag pilot,
# placement A01: tag T03 (id 23) about 0.8 m from the lens, about 240 px wide, grey 41 to 189 in its region; passes 1
# and 2 found it in 3 of 30 frames (nothing rejected: the quad search never outlined it), with pass 3 in 30 of 30,
# median range 0.937 m and bearing +0.19 degrees as in the 3, about 8 ms per frame more on the Spark. Simulated
# (test_a_close_low_contrast_blurred_tag_needs_the_largest_windows): the same tag at 0.937 m, 18 grey levels of
# contrast, blur 2 px: passes 1 and 2 accept 3 of 20 frames, all three passes 20 of 20. A later pass only ADDS
# quads that no earlier pass found (find_quads), so a pass can never cost a detection the earlier ones make.
ARUCO_PASSES = ({}, {"adaptiveThreshWinSizeMin": 33, "adaptiveThreshWinSizeMax": 53, "adaptiveThreshWinSizeStep": 20},
                {"adaptiveThreshWinSizeMin": 63, "adaptiveThreshWinSizeMax": 103, "adaptiveThreshWinSizeStep": 20})

_DETECTORS = {}


def _detector(overrides):
    """A callable gray -> (corners, ids) built once per parameter set. Corner refinement is off: refine_corners()
    below does it, so that the result does not depend on the OpenCV version."""
    overrides = dict(overrides or {})
    key = tuple(sorted(overrides.items()))
    if key in _DETECTORS:
        return _DETECTORS[key]
    aruco = cv2.aruco
    legacy = not hasattr(aruco, "ArucoDetector")
    params = aruco.DetectorParameters_create() if legacy else aruco.DetectorParameters()
    params.cornerRefinementMethod = aruco.CORNER_REFINE_NONE
    if legacy:
        # OpenCV before 4.7 drops the inner one of two nested quads whose corners are closer than
        # minMarkerDistanceRate (0.05) of the perimeter, and a tag's black square sits inside the quad its white
        # border makes on a darker wall (corner distance 0.044 of the perimeter with a 1/8 border): the tag would
        # be thrown away before decoding. 0.02 keeps both; 4.7+ decodes every quad of such a group itself.
        params.minMarkerDistanceRate = 0.02
    for name, value in overrides.items():
        if not hasattr(params, name):
            raise AttributeError("cv2.aruco.DetectorParameters has no field %r in OpenCV %s" % (name, cv2.__version__))
        setattr(params, name, value)
    dictionary = aruco_dictionary()
    if hasattr(aruco, "ArucoDetector"):
        det = aruco.ArucoDetector(dictionary, params)

        def run(gray):
            corners, ids, _rejected = det.detectMarkers(gray)
            return corners, ids
    else:
        def run(gray):
            corners, ids, _rejected = aruco.detectMarkers(gray, dictionary, parameters=params)
            return corners, ids
    _DETECTORS[key] = run
    return run


def find_quads(gray, aruco_params=None):
    """[(corners (4, 2) float64, id)] of the decoded quads in a grey picture. With aruco_params None the passes of
    ARUCO_PASSES run and a later pass adds only quads no earlier pass found (same id, centre within half a side);
    with aruco_params (a dict of cv2.aruco.DetectorParameters fields) there is one pass with exactly those."""
    passes = ARUCO_PASSES if aruco_params is None else (aruco_params,)
    found = []
    for overrides in passes:
        corners_list, ids = _detector(overrides)(gray)
        if ids is None:
            continue
        for quad, tag_id in zip(corners_list, np.asarray(ids).reshape(-1)):
            quad = np.asarray(quad, dtype=np.float64).reshape(4, 2)
            centre = quad.mean(axis=0)
            side = float(np.mean([np.linalg.norm(quad[(i + 1) % 4] - quad[i]) for i in range(4)]))
            if any(int(tag_id) == other_id and np.linalg.norm(other.mean(axis=0) - centre) < 0.5 * side
                   for other, other_id in found):
                continue
            found.append((quad, int(tag_id)))
    return found


def to_gray(image):
    """Grey uint8 from a grey, BGR or BGRA uint8 array."""
    image = np.asarray(image)
    if image.dtype != np.uint8:
        raise TypeError("the frame must be uint8, got %s" % image.dtype)
    if image.ndim == 2:
        return image
    if image.ndim == 3 and image.shape[2] == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if image.ndim == 3 and image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    if image.ndim == 3 and image.shape[2] == 1:
        return image[:, :, 0]
    raise ValueError("unsupported frame shape %r" % (image.shape,))


# ------------------------------------------------------------------ corners

def _sample(gray_f, pts):
    """Bilinear samples of a float32 picture at an (n, 2) array of (u, v)."""
    mx = pts[:, 0].astype(np.float32).reshape(1, -1)
    my = pts[:, 1].astype(np.float32).reshape(1, -1)
    return cv2.remap(gray_f, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE).reshape(-1)


def _undistort(pts, k, d):
    return cv2.undistortPoints(np.asarray(pts, dtype=np.float64).reshape(-1, 1, 2), k, d).reshape(-1, 2)


def _distort(norm, k, d):
    obj = np.concatenate([np.asarray(norm, dtype=np.float64), np.ones((len(norm), 1))], axis=1)
    out, _ = cv2.projectPoints(obj, np.zeros(3), np.zeros(3), k, d)
    return out.reshape(-1, 2)


def _fit_line(points):
    """Total-least-squares line through (n, 2) points: (point on the line, unit direction), one pass of trimming
    points beyond 2.5 robust standard deviations."""
    keep = np.ones(len(points), dtype=bool)
    for _ in range(2):
        p = points[keep]
        c = p.mean(axis=0)
        _u, _s, vt = np.linalg.svd(p - c)
        direction, normal = vt[0], vt[1]
        resid = (points - c) @ normal
        scale = 1.4826 * np.median(np.abs(resid[keep])) + 1e-12
        new_keep = np.abs(resid) <= 2.5 * scale
        if new_keep.sum() < 4 or new_keep.sum() == keep.sum():
            break
        keep = new_keep
    return c, direction


def _intersect(line_a, line_b):
    (pa, da), (pb, db) = line_a, line_b
    m = np.array([[da[0], -db[0]], [da[1], -db[1]]])
    if abs(np.linalg.det(m)) < 1e-12:
        return None
    t = np.linalg.solve(m, pb - pa)
    return pa + t[0] * da


def refine_corners(gray_f, quad, k, d):
    """Refit the four corners of a detected black square from its edges.

    gray_f: float32 picture; quad: (4, 2) corners from the detector in its order. Along each side, between the
    corners, profiles perpendicular to the side are sampled (bilinear, 0.25 px steps); the edge point of a profile is
    the centroid of its rising brightness gradient going from the black ring out into the white border, re-centred
    once. The edge points have the lens distortion removed, a line is fitted to each side, and adjacent lines are
    intersected. Returns (corners in normalised undistorted coordinates (4, 2), corners in pixels (4, 2)) or None
    when a side has too few usable points (the caller then keeps the detector's corners)."""
    quad = np.asarray(quad, dtype=np.float64).reshape(4, 2)
    centre = quad.mean(axis=0)
    sides = [np.linalg.norm(quad[(i + 1) % 4] - quad[i]) for i in range(4)]
    cell = float(np.mean(sides)) / CELLS
    half_w = float(np.clip(0.8 * cell, 2.0, 5.0))
    steps = np.arange(-half_w, half_w + 1e-9, 0.25)
    lines = []
    for i in range(4):
        a, b = quad[i], quad[(i + 1) % 4]
        length = sides[i]
        if length < 6.0:
            return None
        along = (b - a) / length
        normal = np.array([along[1], -along[0]])
        if np.dot(normal, (a + b) / 2.0 - centre) < 0:
            normal = -normal                                  # outward: from the black ring to the white border
        margin = min(0.35, (half_w + 1.0) / length)
        n_pts = int(np.clip(round(length * (1.0 - 2.0 * margin)), 5, 80))
        ts = np.linspace(margin, 1.0 - margin, n_pts)
        base = a[None, :] + ts[:, None] * (b - a)[None, :]
        offset = np.zeros(n_pts)
        valid = np.ones(n_pts, dtype=bool)
        for _ in range(2):
            pts = (base + offset[:, None] * normal[None, :])[:, None, :] + steps[None, :, None] * normal[None, None, :]
            prof = _sample(gray_f, pts.reshape(-1, 2)).reshape(n_pts, len(steps))
            grad = np.clip(np.diff(prof, axis=1), 0.0, None)   # rising = black -> white going outward
            mid = (steps[:-1] + steps[1:]) / 2.0
            weight = grad.sum(axis=1)
            valid = weight > 4.0                               # at least 4 grey levels of rise across the profile
            shift = np.where(valid, (grad * mid[None, :]).sum(axis=1) / np.maximum(weight, 1e-9), 0.0)
            offset = offset + shift
        if valid.sum() < max(4, n_pts // 3):
            return None
        edge_px = (base + offset[:, None] * normal[None, :])[valid]
        lines.append(_fit_line(_undistort(edge_px, k, d)))
    corners = []
    for i in range(4):
        p = _intersect(lines[i - 1], lines[i])                 # corner i joins side i-1 and side i
        if p is None:
            return None
        corners.append(p)
    norm = np.array(corners)
    pix = _distort(norm, k, d)
    if np.max(np.linalg.norm(pix - quad, axis=1)) > max(3.0, 0.75 * cell):
        return None                                            # the fit ran away from the detector's quad
    return norm, pix


# ------------------------------------------------------------------ re-reading the code

def read_cells(gray_f, corners_px):
    """Mean brightness of each of the 8 x 8 cells of the tag whose black square has these corners (3 x 3 samples in
    the middle 60 % of each cell)."""
    src = np.array([[0, 0], [CELLS, 0], [CELLS, CELLS], [0, CELLS]], dtype=np.float32)
    h = cv2.getPerspectiveTransform(src, np.asarray(corners_px, dtype=np.float32).reshape(4, 2))
    sub = np.array([0.2, 0.5, 0.8])
    grid = (np.arange(CELLS)[:, None] + sub[None, :]).reshape(-1)
    gx, gy = np.meshgrid(grid, grid)
    pts = cv2.perspectiveTransform(np.stack([gx.reshape(-1), gy.reshape(-1)], axis=1).reshape(-1, 1, 2).astype(np.float32), h)
    vals = _sample(gray_f, pts.reshape(-1, 2)).reshape(CELLS, 3, CELLS, 3)
    return vals.mean(axis=(1, 3))


def code_check(gray_f, corners_px, tag_id):
    """(hamming, decision_margin, contrast): see the module docstring. contrast = mean white cell - mean black cell."""
    cells = read_cells(gray_f, corners_px)
    want = marker_cells(tag_id).astype(bool)
    white, black = cells[want], cells[~want]
    if white.size == 0 or black.size == 0:
        return 36, 0.0, 0.0
    threshold = (white.mean() + black.mean()) / 2.0
    signed = np.where(want, cells - threshold, threshold - cells)[1:-1, 1:-1]
    return int((signed < 0).sum()), float(signed.mean()), float(white.mean() - black.mean())


# ------------------------------------------------------------------ pose

def object_corners(tag_size_m):
    """Corner coordinates in the tag frame, in the detector's order and the order SOLVEPNP_IPPE_SQUARE requires."""
    h = float(tag_size_m) / 2.0
    return np.array([[-h, h, 0.0], [h, h, 0.0], [h, -h, 0.0], [-h, -h, 0.0]], dtype=np.float64)


def _ippe(obj, img):
    """(rvec, tvec) pairs with finite numbers from SOLVEPNP_IPPE_SQUARE; [] when OpenCV raises or returns none."""
    eye, nodist = np.eye(3), np.zeros(5)
    try:
        if hasattr(cv2, "solvePnPGeneric"):
            out = cv2.solvePnPGeneric(obj, img, eye, nodist, flags=cv2.SOLVEPNP_IPPE_SQUARE)
            pairs = [(out[1][i], out[2][i]) for i in range(int(out[0]))]
        else:
            ok, rvec, tvec = cv2.solvePnP(obj, img, eye, nodist, flags=cv2.SOLVEPNP_IPPE_SQUARE)
            pairs = [(rvec, tvec)] if ok else []
    except cv2.error:
        return []
    pairs = [(np.asarray(r, dtype=np.float64).reshape(3), np.asarray(t, dtype=np.float64).reshape(3)) for r, t in pairs]
    return [(r, t) for r, t in pairs if np.all(np.isfinite(r)) and np.all(np.isfinite(t))]


def _poses(norm_corners, tag_size_m):
    """Up to two (rvec, tvec) for undistorted, normalised corners, in OpenCV's order (best reprojection first).

    IPPE returns not-a-number for some exact corner sets (seen with OpenCV 5.1 on noise-free corners of a tag 1 m
    straight ahead): such solutions are dropped, the solve is repeated with the corners moved by 1e-9 (far below
    any measurable difference), and if that fails too the iterative solver gives one pose."""
    obj = object_corners(tag_size_m)
    img = np.asarray(norm_corners, dtype=np.float64).reshape(4, 1, 2)
    poses = _ippe(obj, img)
    if not poses:
        nudge = 1e-9 * np.array([[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0], [0.0, -1.0]]).reshape(4, 1, 2)
        poses = _ippe(obj, img + nudge)
    if not poses:
        try:
            ok, rvec, tvec = cv2.solvePnP(obj, img, np.eye(3), np.zeros(5), flags=cv2.SOLVEPNP_ITERATIVE)
        except cv2.error:
            ok = False
        if ok and np.all(np.isfinite(rvec)) and np.all(np.isfinite(tvec)):
            poses = [(np.asarray(rvec, dtype=np.float64).reshape(3), np.asarray(tvec, dtype=np.float64).reshape(3))]
    return poses


def _reproj_px(rvec, tvec, tag_size_m, corners_px, k, d):
    proj, _ = cv2.projectPoints(object_corners(tag_size_m), rvec, tvec, k, d)
    return float(np.sqrt(np.mean(np.sum((proj.reshape(4, 2) - corners_px) ** 2, axis=1))))


def _pose_fields(camera, rvec, tvec):
    """Geometry of one pose in base_link."""
    rot_bo = np.array(camera.rotation)
    r_tag, _ = cv2.Rodrigues(rvec)
    base = rot_bo @ tvec + np.array(camera.translation)
    normal_b = rot_bo @ r_tag[:, 2]
    up_b = rot_bo @ r_tag[:, 1]
    rng, bearing = range_bearing(float(base[0]), float(base[1]))
    normal_yaw = math.degrees(math.atan2(normal_b[1], normal_b[0]))
    to_axle = math.degrees(math.atan2(-base[1], -base[0]))
    dist = float(np.linalg.norm(tvec))
    view = math.degrees(math.acos(float(np.clip(np.dot(r_tag[:, 2], -tvec / max(dist, 1e-12)), -1.0, 1.0))))
    return {"range_m": rng, "bearing_deg": bearing, "base_xyz_m": [float(v) for v in base],
            "camera_xyz_m": [float(v) for v in tvec], "camera_rvec": [float(v) for v in rvec],
            "camera_range_m": dist, "normal_yaw_deg": normal_yaw,
            "incidence_deg": abs(wrap_deg(normal_yaw - to_axle)), "view_angle_deg": view,
            "up_error_deg": math.degrees(math.acos(float(np.clip(up_b[2], -1.0, 1.0))))}


def quality_of(det, settings=None):
    """Single-frame quality in 0..1: the smallest of three scores, so one weak property is enough to lower it.

    - size:   0 at min_side_px (the rejection limit), 1 from quality_side_full_px (40 px) upward, linear between,
              taken on the tag's shortest side;
    - fit:    1 - reproj_px / (max_reproj_px + max_reproj_rel * side_px), i.e. 1 for a perfect corner fit and 0 at the
              rejection limit;
    - code:   decision_margin / quality_margin_full (20 grey levels) capped at 1, times (1 - hamming / (max_hamming + 1)).

    The agent's prompt rejects a detection whose quality is under 0.5 (configs/dv.json reject_quality_below), so 0.5
    here means: a tag about 27 px on its shortest side, or a corner fit half way to the rejection limit, or a code
    margin of 10 grey levels (black and white 20 grey levels apart; real frames of 2026-11-18 show about 85). The
    multi-frame value of contract C3 (frames seen / frames taken) is fuse_frames()."""
    s = dict(DEFAULTS)
    s.update(settings or {})
    span = max(s["quality_side_full_px"] - s["min_side_px"], 1e-9)
    size = (det["min_side_px"] - s["min_side_px"]) / span
    fit = 1.0 - det["reproj_px"] / (s["max_reproj_px"] + s["max_reproj_rel"] * det["side_px"])
    code = min(det["decision_margin"] / s["quality_margin_full"], 1.0) * (1.0 - det["hamming"] / (s["max_hamming"] + 1.0))
    return float(min(1.0, max(0.0, min(size, fit, code))))


# ------------------------------------------------------------------ the detector

def _drop_duplicates(accepted, rejected):
    """One detection per physical tag: of accepted detections with the same id whose centres are closer than half a
    tag side in the picture, the one with the smaller reprojection error stays; the others go to `rejected` as
    ``duplicate``. (Two different tags with one id are never that close.)"""
    kept = []
    for det in sorted(accepted, key=lambda f: f["reproj_px"]):
        centre = np.array(det["center_px"])
        if any(k["id"] == det["id"] and np.linalg.norm(np.array(k["center_px"]) - centre) < 0.5 * max(k["side_px"], det["side_px"])
               for k in kept):
            det["reject"] = "duplicate"
            rejected.append(det)
        else:
            kept.append(det)
    return kept


def _per_id(value, tag_id):
    """value for this id: a plain number (or None) applies to every id; a mapping gives id -> value, with an optional
    "default" entry for the ids it does not list. Returns (found, value)."""
    if isinstance(value, dict):
        if tag_id in value:
            return True, value[tag_id]
        if "default" in value:
            return True, value["default"]
        return False, None
    return True, value


def detect_tags(image, camera, tag_size_m=0.16, *, tag_center_height_m=None, return_rejected=False,
                refine=True, upright_prior=True, aruco_params=None, **settings):
    """Tags in one frame, with range and bearing from the axle midpoint (contract C1).

    image: grey or BGR uint8 array of the camera's calibrated size (ValueError otherwise: intrinsics belong to one
    resolution). camera: beaconmind.camera_model.Camera. tag_size_m: edge of the black square (0.16 m; use the
    ruler-measured value). tag_center_height_m: the tags' centre height above the floor (0.23 for the wall tags)
    turns on the ``height`` rule; None leaves it off. For a room with tags of more than one size, either may be a
    dict {id: value} with an optional "default" entry, for example {**{i: 0.16 for i in range(15)}, "default": 0.10};
    a tag whose id has no size is rejected as ``no_size`` (its range cannot be known). refine=False keeps the detector's own corners.
    upright_prior=False always takes the pose with the smaller reprojection error. aruco_params: fields of
    cv2.aruco.DetectorParameters for a single quad search instead of the two of ARUCO_PASSES. settings: any key of
    DEFAULTS.

    Returns the accepted detections sorted left to right (bearing descending), or (accepted, rejected) with
    return_rejected=True. Each is a dict as the module docstring lists; numbers are not rounded here."""
    unknown = set(settings) - set(DEFAULTS)
    if unknown:
        raise TypeError("unknown setting(s): %s" % ", ".join(sorted(unknown)))
    s = dict(DEFAULTS)
    s.update(settings)
    gray = to_gray(image)
    if gray.shape[1] != camera.width or gray.shape[0] != camera.height:
        raise ValueError("the frame is %d x %d but the camera is calibrated at %d x %d"
                         % (gray.shape[1], gray.shape[0], camera.width, camera.height))
    sizes = tag_size_m.values() if isinstance(tag_size_m, dict) else [tag_size_m]
    if not all(v is not None and v > 0 for v in sizes):
        raise ValueError("tag_size_m must be positive")
    k = np.array(camera.camera_matrix, dtype=np.float64)
    d = np.array(camera.dist, dtype=np.float64)
    quads = find_quads(gray, aruco_params)
    accepted, rejected = [], []
    if not quads:
        return (accepted, rejected) if return_rejected else accepted
    gray_f = gray.astype(np.float32)
    for quad, tag_id in quads:
        has_size, size_m = _per_id(tag_size_m, int(tag_id))
        _has_height, height_m = _per_id(tag_center_height_m, int(tag_id))
        det = {"id": int(tag_id), "family": FAMILY, "tag_size_m": float(size_m) if has_size else None, "reject": None}
        fitted = refine_corners(gray_f, quad, k, d) if refine else None
        if fitted is None:
            norm, pix = _undistort(quad, k, d), quad
        else:
            norm, pix = fitted
        det["refined"] = fitted is not None
        sides = [float(np.linalg.norm(pix[(i + 1) % 4] - pix[i])) for i in range(4)]
        det["corners_px"] = [[float(u), float(v)] for u, v in pix]
        det["center_px"] = [float(v) for v in pix.mean(axis=0)]
        det["side_px"] = float(np.mean(sides))
        det["min_side_px"] = float(np.min(sides))
        hamming, margin, contrast = code_check(gray_f, pix, det["id"])
        det["hamming"], det["decision_margin"], det["contrast"] = hamming, margin, contrast

        def reject(reason, det=det):
            det["reject"] = reason
            det.setdefault("quality", 0.0)
            rejected.append(det)

        lo, hi = s["id_range"]
        if not lo <= det["id"] <= hi:
            reject("id_out_of_range")
            continue
        if not has_size:
            reject("no_size")
            continue
        if det["min_side_px"] < s["min_side_px"]:
            reject("too_small")
            continue
        edge = s["border_px"]
        if (pix[:, 0].min() < edge or pix[:, 1].min() < edge or pix[:, 0].max() > camera.width - 1 - edge
                or pix[:, 1].max() > camera.height - 1 - edge):
            reject("at_border")
            continue
        poses = _poses(norm, size_m)
        if not poses:
            reject("pnp_failed")
            continue
        cands = []
        for rvec, tvec in poses:
            if tvec[2] <= 0:
                continue
            fields = _pose_fields(camera, rvec, tvec)
            fields["reproj_px"] = _reproj_px(rvec, tvec, size_m, pix, k, d)
            cands.append(fields)
        if not cands:
            reject("behind")
            continue
        cands.sort(key=lambda f: f["reproj_px"])
        best = cands[0]
        alt = cands[1] if len(cands) > 1 else None
        if (alt is not None and upright_prior
                and alt["reproj_px"] <= max(s["ambiguity_ratio"] * best["reproj_px"], s["ambiguity_floor_px"])
                and alt["up_error_deg"] < best["up_error_deg"]):
            best, alt = alt, best
        det.update(best)
        det["reproj_alt_px"] = alt["reproj_px"] if alt else None
        det["normal_yaw_alt_deg"] = alt["normal_yaw_deg"] if alt else None
        det["quality"] = quality_of(det, s)
        if det["reproj_px"] > s["max_reproj_px"] + s["max_reproj_rel"] * det["side_px"]:
            reject("reproj")
            continue
        if det["hamming"] > s["max_hamming"]:
            reject("hamming")
            continue
        if det["decision_margin"] < s["min_margin"]:
            reject("low_margin")
            continue
        if det["view_angle_deg"] > s["max_view_angle_deg"]:
            reject("oblique")
            continue
        if det["range_m"] > s["max_range_m"]:
            reject("range")
            continue
        if height_m is not None:
            off = abs(det["base_xyz_m"][2] - float(height_m))
            if off > s["height_tol_m"] + s["height_tol_per_m"] * det["range_m"]:
                reject("height")
                continue
        accepted.append(det)
    accepted = _drop_duplicates(accepted, rejected)
    accepted.sort(key=lambda f: -f["bearing_deg"])
    return (accepted, rejected) if return_rejected else accepted


# ------------------------------------------------------------------ several frames, and the observation

def fuse_frames(frames, obs_frames=None, obs_min_frames=3, match_radius_m=0.30):
    """Contract C3's detection pipeline over the frames of one stop: keep tags seen in at least obs_min_frames
    frames, take the median position of each in base_link, range = hypot(x, y), bearing = atan2(y, x),
    quality = frames seen / frames taken.

    frames: one list of accepted detections per frame (from detect_tags). obs_frames: frames taken (default: the
    number of lists). Two tags may carry the same id (the layout repeats ids), so detections are grouped by id AND
    position: a detection joins the group of its id whose median position is within match_radius_m, else starts a
    new group. Returns fused detections sorted left to right, each with id, range_m, bearing_deg, base_xyz_m,
    quality, frames_seen, frames, frame_quality_median, normal_yaw_deg and normal_yaw_alt_deg (medians),
    range_sd_m and bearing_sd_deg (sample standard deviations over the frames seen, None for one frame)."""
    frames = list(frames)
    n_frames = int(obs_frames) if obs_frames is not None else len(frames)
    if n_frames <= 0:
        return []
    groups = []
    for index, dets in enumerate(frames):
        used = set()
        for det in dets:
            xy = np.array(det["base_xyz_m"][:2])
            choice, best = None, match_radius_m
            for gi, group in enumerate(groups):
                if group["id"] != det["id"] or gi in used:
                    continue
                centre = np.median(np.array([m["base_xyz_m"][:2] for m in group["members"]]), axis=0)
                dist = float(np.linalg.norm(centre - xy))
                if dist <= best:
                    choice, best = gi, dist
            if choice is None:
                groups.append({"id": det["id"], "members": [det], "frames": [index]})
                used.add(len(groups) - 1)
            else:
                groups[choice]["members"].append(det)
                groups[choice]["frames"].append(index)
                used.add(choice)
    out = []
    for group in groups:
        seen = len(group["members"])
        if seen < obs_min_frames:
            continue
        xyz = np.median(np.array([m["base_xyz_m"] for m in group["members"]]), axis=0)
        rng, bearing = range_bearing(float(xyz[0]), float(xyz[1]))
        ranges = [m["range_m"] for m in group["members"]]
        bearings = [wrap_deg(m["bearing_deg"] - bearing) for m in group["members"]]

        def circ_median(key, members=group["members"]):
            vals = [m[key] for m in members if m.get(key) is not None]
            if not vals:
                return None
            ref = vals[0]
            return wrap_deg(ref + float(np.median([wrap_deg(v - ref) for v in vals])))

        out.append({"id": group["id"], "range_m": rng, "bearing_deg": bearing, "base_xyz_m": [float(v) for v in xyz],
                    "quality": min(1.0, seen / float(n_frames)), "frames_seen": seen, "frames": n_frames,
                    "frame_quality_median": float(np.median([m["quality"] for m in group["members"]])),
                    "normal_yaw_deg": circ_median("normal_yaw_deg"),
                    "normal_yaw_alt_deg": circ_median("normal_yaw_alt_deg"),
                    "range_sd_m": float(np.std(ranges, ddof=1)) if seen > 1 else None,
                    "bearing_sd_deg": float(np.std(bearings, ddof=1)) if seen > 1 else None})
    out.sort(key=lambda f: -f["bearing_deg"])
    return out


def to_observation_detections(detections, hide_ids=False):
    """The ``detections`` list of a bm.observation-1 document from detect_tags() or fuse_frames() output:
    [{"det": index, "id": int or None, "range_m", "bearing_deg", "quality"}], rounded as contract C1 says (0.01 m,
    0.1 degree, 0.01), numbered left to right. hide_ids=True writes id null (the hidden-ID condition).
    Nothing is filtered here: the agent's own rules reject low quality and long range."""
    out = []
    for index, det in enumerate(sorted(detections, key=lambda f: -f["bearing_deg"])):
        out.append({"det": index, "id": None if hide_ids else int(det["id"]),
                    "range_m": round(float(det["range_m"]), 2), "bearing_deg": round(float(det["bearing_deg"]), 1),
                    "quality": round(float(min(1.0, max(0.0, det["quality"]))), 2)})
    return out


def to_internal_detections(detections):
    """The harness's ``detections_internal`` (contract C3; run log only, never the prompt): per detection, in the
    same order and numbering as to_observation_detections, the tag position in base_link, the tag-normal yaw for both
    pose solutions, and the frames seen (1 for a single frame)."""
    out = []
    for index, det in enumerate(sorted(detections, key=lambda f: -f["bearing_deg"])):
        out.append({"det": index, "id": int(det["id"]),
                    "base_xyz_m": [round(float(v), 4) for v in det["base_xyz_m"]],
                    "normal_yaw_deg": None if det.get("normal_yaw_deg") is None else round(float(det["normal_yaw_deg"]), 1),
                    "normal_yaw_alt_deg": (None if det.get("normal_yaw_alt_deg") is None
                                           else round(float(det["normal_yaw_alt_deg"]), 1)),
                    "frames_seen": int(det.get("frames_seen", 1)),
                    "reproj_px": None if det.get("reproj_px") is None else round(float(det["reproj_px"]), 3),
                    "side_px": None if det.get("side_px") is None else round(float(det["side_px"]), 1)})
    return out
