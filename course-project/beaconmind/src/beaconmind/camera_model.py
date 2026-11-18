"""Camera geometry for the car's ESP32-CAM: configs/camera.json (bm.camera-1) as a pinhole + plumb_bob model, and
the camera-to-base_link transform from its extrinsics (plan tasks M1.T7 and M1.T8). Standard library only.

Frames (plan/README.md contract C1):

- ``base_link``: origin on the floor under the wheel-axle midpoint, x forward (toward the camera end), y left, z up.
  ``extrinsics.z_m`` is the lens height above the floor, so a point's base_link z is its height above the floor.
- ``camera_optical_frame``: origin at the lens, z forward along the optical axis, x to the image right, y down the
  image. Pixel (u, v): u grows to the right, v grows downward.

Mount angles (signs as recorded in evidence/M1/M1.T7/extrinsics.md and plan M1.T7 step 9):

- ``yaw_deg``   positive = the camera points to the car's left  (a rotation about base_link +z, counter-clockwise).
- ``pitch_deg`` positive = the camera points down, "nose down"  (a rotation about base_link +y; REP 103 sign).
- ``roll_deg``  positive = the picture content is turned counter-clockwise on the screen, which is the camera body
  turned clockwise as seen from behind it (a rotation about base_link +x; REP 103 sign).

Rotation order (a choice made here; extrinsics.md gives three angles and no order): the URDF / REP 103 fixed-axis
roll-pitch-yaw order, the same order ``static_transform_publisher`` and a URDF ``rpy`` use,

    R(base_link <- camera_optical_frame) = Rz(yaw) @ Ry(pitch) @ Rx(roll) @ R0,

where R0 maps the optical axes of a level, forward-looking camera to the body axes (optical z -> base x, optical x ->
base -y, optical y -> base -z). With the measured angles (4.4, -3.9, 2.5 degrees) the other orders differ from this
one by at most about 0.3 degrees, well inside the 2 degree uncertainty recorded with them.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this module (the plumb_bob formulas are the standard
Brown-Conrady model as OpenCV documents it for calibrateCamera, reimplemented here in plain Python, not copied).
"""
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

# R0: columns are the optical axes written in body axes (x_opt = -y_body, y_opt = -z_body, z_opt = +x_body).
OPTICAL_TO_BODY = ((0.0, 0.0, 1.0),
                   (-1.0, 0.0, 0.0),
                   (0.0, -1.0, 0.0))


# ------------------------------------------------------------------ the M1.T7 formulas

def hfov_deg(fx, width):
    """Horizontal field of view of a pinhole camera: 2 atan(width / (2 fx)), degrees."""
    return math.degrees(2.0 * math.atan(float(width) / (2.0 * float(fx))))


def vfov_deg(fy, height):
    """Vertical field of view of a pinhole camera: 2 atan(height / (2 fy)), degrees."""
    return math.degrees(2.0 * math.atan(float(height) / (2.0 * float(fy))))


def pixel_to_angles(u, v, fx, fy, cx, cy):
    """(yaw_deg, pitch_deg) of the ray through pixel (u, v) of an undistorted pinhole image, in the camera's own
    frame. yaw is positive to the image left (u < cx; the +y side of base_link for a level camera), pitch is positive
    up (v < cy). Each is the plane angle atan(offset / focal), as plan M1.T7 step 9 uses them."""
    yaw = math.degrees(math.atan((float(cx) - float(u)) / float(fx)))
    pitch = math.degrees(math.atan((float(cy) - float(v)) / float(fy)))
    return yaw, pitch


# ------------------------------------------------------------------ small 3 x 3 helpers (tuples of rows)

def _matmul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def _matvec(a, p):
    return tuple(a[i][0] * p[0] + a[i][1] * p[1] + a[i][2] * p[2] for i in range(3))


def _transpose(a):
    return tuple(tuple(a[j][i] for j in range(3)) for i in range(3))


def rot_x(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return ((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c))


def rot_y(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return ((c, 0.0, s), (0.0, 1.0, 0.0), (-s, 0.0, c))


def rot_z(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))


def mount_rotation(roll_deg, pitch_deg, yaw_deg):
    """R(base_link <- camera_optical_frame) = Rz(yaw) Ry(pitch) Rx(roll) R0 as a tuple of three rows.
    Signs: yaw + = camera points left, pitch + = nose down, roll + = picture content turned counter-clockwise."""
    body = _matmul(rot_z(yaw_deg), _matmul(rot_y(pitch_deg), rot_x(roll_deg)))
    return _matmul(body, OPTICAL_TO_BODY)


def wrap_deg(a):
    """Wrap to (-180, 180], as beaconmind.geometry.wrap_deg does."""
    a = math.fmod(a, 360.0)
    if a <= -180.0:
        a += 360.0
    elif a > 180.0:
        a -= 360.0
    return a


def range_bearing(x_m, y_m):
    """C1 observation geometry of a base_link point: floor-plane range from the axle midpoint and the bearing from
    +x, counter-clockwise (left) positive, degrees."""
    return math.hypot(x_m, y_m), math.degrees(math.atan2(y_m, x_m))


# ------------------------------------------------------------------ the camera

@dataclass(frozen=True)
class Camera:
    """Intrinsics, plumb_bob distortion and mount of one calibrated camera at one image size."""
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float
    dist: tuple = (0.0, 0.0, 0.0, 0.0, 0.0)            # k1, k2, p1, p2, k3 (OpenCV order)
    x_m: float = 0.0                                    # lens position in base_link
    y_m: float = 0.0
    z_m: float = 0.0
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0
    source: str = ""
    rotation: tuple = field(init=False, repr=False, compare=False, default=None)   # R(base <- optical)

    def __post_init__(self):
        if len(self.dist) != 5:
            raise ValueError("plumb_bob needs 5 distortion coefficients, got %d" % len(self.dist))
        if self.fx <= 0 or self.fy <= 0 or self.width <= 0 or self.height <= 0:
            raise ValueError("focal lengths and the image size must be positive")
        object.__setattr__(self, "rotation", mount_rotation(self.roll_deg, self.pitch_deg, self.yaw_deg))

    # ---- construction

    @classmethod
    def from_dict(cls, doc, source=""):
        """From a bm.camera-1 document. Extrinsics that are still null (before M1.T7 step 8) are refused: tag
        geometry from the axle midpoint needs them."""
        if doc.get("distortion_model", "plumb_bob") != "plumb_bob":
            raise ValueError("only the plumb_bob distortion model is implemented")
        k = [float(v) for v in doc["camera_matrix"]]
        if len(k) != 9:
            raise ValueError("camera_matrix must hold 9 numbers, row-major")
        if abs(k[1]) > 1e-9 or abs(k[3]) > 1e-9 or abs(k[6]) > 1e-9 or abs(k[7]) > 1e-9 or abs(k[8] - 1.0) > 1e-9:
            raise ValueError("camera_matrix must be [fx 0 cx; 0 fy cy; 0 0 1] (no skew)")
        ext = doc["extrinsics"]
        names = ("x_m", "y_m", "z_m", "roll_deg", "pitch_deg", "yaw_deg")
        missing = [n for n in names if ext.get(n) is None]
        if missing:
            raise ValueError("camera extrinsics are not measured yet: %s" % ", ".join(missing))
        return cls(width=int(doc["image_width"]), height=int(doc["image_height"]),
                   fx=k[0], fy=k[4], cx=k[2], cy=k[5], dist=tuple(float(v) for v in doc["distortion"]),
                   source=str(source), **{n: float(ext[n]) for n in names})

    def with_mount(self, **changes):
        """A copy with other mount values (x_m, y_m, z_m, roll_deg, pitch_deg, yaw_deg)."""
        values = {n: getattr(self, n) for n in ("width", "height", "fx", "fy", "cx", "cy", "dist", "x_m", "y_m",
                                                 "z_m", "roll_deg", "pitch_deg", "yaw_deg", "source")}
        unknown = set(changes) - {"x_m", "y_m", "z_m", "roll_deg", "pitch_deg", "yaw_deg"}
        if unknown:
            raise TypeError("not a mount value: %s" % ", ".join(sorted(unknown)))
        values.update(changes)
        return Camera(**values)

    # ---- numbers other code wants

    @property
    def hfov_deg(self):
        return hfov_deg(self.fx, self.width)

    @property
    def vfov_deg(self):
        return vfov_deg(self.fy, self.height)

    @property
    def camera_matrix(self):
        """3 x 3 as a tuple of rows (numpy.array(camera.camera_matrix) for OpenCV)."""
        return ((self.fx, 0.0, self.cx), (0.0, self.fy, self.cy), (0.0, 0.0, 1.0))

    @property
    def translation(self):
        """Lens position in base_link, metres."""
        return (self.x_m, self.y_m, self.z_m)

    # ---- lens distortion (normalised image coordinates x = X/Z, y = Y/Z)

    def distort_normalized(self, x, y):
        k1, k2, p1, p2, k3 = self.dist
        r2 = x * x + y * y
        radial = 1.0 + r2 * (k1 + r2 * (k2 + r2 * k3))
        xd = x * radial + 2.0 * p1 * x * y + p2 * (r2 + 2.0 * x * x)
        yd = y * radial + p1 * (r2 + 2.0 * y * y) + 2.0 * p2 * x * y
        return xd, yd

    def undistort_normalized(self, xd, yd, iterations=30):
        """Inverse of distort_normalized by fixed-point iteration (converges fast for this lens: the correction is
        a few percent at the image corners)."""
        k1, k2, p1, p2, k3 = self.dist
        x, y = xd, yd
        for _ in range(iterations):
            r2 = x * x + y * y
            radial = 1.0 + r2 * (k1 + r2 * (k2 + r2 * k3))
            dx = 2.0 * p1 * x * y + p2 * (r2 + 2.0 * x * x)
            dy = p1 * (r2 + 2.0 * y * y) + 2.0 * p2 * x * y
            nx, ny = (xd - dx) / radial, (yd - dy) / radial
            if abs(nx - x) < 1e-13 and abs(ny - y) < 1e-13:
                x, y = nx, ny
                break
            x, y = nx, ny
        return x, y

    # ---- projection

    def project_optical(self, p):
        """Pixel (u, v) of a point given in camera_optical_frame, with distortion. ValueError behind the lens."""
        if p[2] <= 1e-9:
            raise ValueError("the point is not in front of the camera (z = %.4f m)" % p[2])
        xd, yd = self.distort_normalized(p[0] / p[2], p[1] / p[2])
        return self.fx * xd + self.cx, self.fy * yd + self.cy

    def project_base(self, p):
        """Pixel (u, v) of a base_link point, with distortion."""
        return self.project_optical(self.base_to_optical(p))

    def in_image(self, u, v, margin_px=0.0):
        return margin_px <= u <= self.width - 1 - margin_px and margin_px <= v <= self.height - 1 - margin_px

    def pixel_to_ray_optical(self, u, v):
        """Unit vector, in camera_optical_frame, of the ray through the (distorted) pixel (u, v)."""
        x, y = self.undistort_normalized((u - self.cx) / self.fx, (v - self.cy) / self.fy)
        n = math.sqrt(x * x + y * y + 1.0)
        return (x / n, y / n, 1.0 / n)

    def pixel_to_ray_base(self, u, v):
        """The same ray as a unit vector in base_link axes (direction only; it starts at the lens)."""
        return _matvec(self.rotation, self.pixel_to_ray_optical(u, v))

    def pixel_to_angles(self, u, v):
        """pixel_to_angles() for a real (distorted) pixel: the lens distortion is removed first."""
        x, y = self.undistort_normalized((u - self.cx) / self.fx, (v - self.cy) / self.fy)
        return math.degrees(math.atan(-x)), math.degrees(math.atan(-y))

    def view_edges_deg(self):
        """Angles from the optical axis to the middle of each image edge, lens distortion removed:
        {"left", "right", "up", "down"} in degrees, all positive. Their sums are the true fields of view, which
        differ a little from the pinhole hfov_deg / vfov_deg."""
        left, _ = self.pixel_to_angles(0.0, self.cy)
        right, _ = self.pixel_to_angles(self.width - 1.0, self.cy)
        _, up = self.pixel_to_angles(self.cx, 0.0)
        _, down = self.pixel_to_angles(self.cx, self.height - 1.0)
        return {"left": left, "right": -right, "up": up, "down": -down}

    # ---- frames

    def optical_to_base(self, p):
        """A point in camera_optical_frame -> base_link (metres)."""
        q = _matvec(self.rotation, p)
        return (q[0] + self.x_m, q[1] + self.y_m, q[2] + self.z_m)

    def base_to_optical(self, p):
        """A point in base_link -> camera_optical_frame (metres)."""
        d = (p[0] - self.x_m, p[1] - self.y_m, p[2] - self.z_m)
        return _matvec(_transpose(self.rotation), d)

    def direction_to_base(self, d):
        """A direction (no translation) from optical axes to base_link axes."""
        return _matvec(self.rotation, d)

    def range_bearing(self, p_optical):
        """(range_m, bearing_deg) from the axle midpoint in the floor plane (contract C1) of a point given in
        camera_optical_frame."""
        b = self.optical_to_base(p_optical)
        return range_bearing(b[0], b[1])


def default_camera_path():
    import beaconmind
    return beaconmind.course_root() / "configs" / "camera.json"


def load_camera(path=None):
    """Camera from a bm.camera-1 file; configs/camera.json when path is None."""
    path = Path(path) if path is not None else default_camera_path()
    with open(path, encoding="utf-8") as handle:
        doc = json.load(handle)
    return Camera.from_dict(doc, source=str(path))


# ------------------------------------------------------------------ what a wall tag needs to be in view

def square_corners_base(center_xyz, facing_yaw_deg, half_side_m):
    """Four corners (base_link) of an upright square of half side half_side_m centred at center_xyz whose outward
    normal is horizontal and points along facing_yaw_deg (a base_link yaw). Order as a viewer in front of it sees
    them: top-left, top-right, bottom-right, bottom-left."""
    n = (math.cos(math.radians(facing_yaw_deg)), math.sin(math.radians(facing_yaw_deg)))
    # the viewer looks along -n; the viewer's right is -n turned 90 degrees clockwise, i.e. n turned 90 degrees
    # counter-clockwise: (-n_y, n_x)
    right = (-n[1], n[0])
    cx, cy, cz = center_xyz
    h = half_side_m
    return [(cx - h * right[0], cy - h * right[1], cz + h),
            (cx + h * right[0], cy + h * right[1], cz + h),
            (cx + h * right[0], cy + h * right[1], cz - h),
            (cx - h * right[0], cy - h * right[1], cz - h)]


def square_in_view(camera, range_m, bearing_deg, center_height_m, half_side_m, margin_px=0.0, incidence_deg=0.0):
    """True when the whole upright square is inside the picture. The square's centre is at (range, bearing) from the
    axle midpoint and center_height_m above the floor; it faces the axle midpoint, turned by incidence_deg about
    the vertical."""
    b = math.radians(bearing_deg)
    centre = (range_m * math.cos(b), range_m * math.sin(b), center_height_m)
    facing = bearing_deg + 180.0 + incidence_deg
    for corner in square_corners_base(centre, facing, half_side_m):
        try:
            u, v = camera.project_base(corner)
        except ValueError:
            return False
        if not camera.in_image(u, v, margin_px):
            return False
    return True


def min_full_view_range(camera, center_height_m=0.23, half_side_m=0.10, bearing_deg=0.0, margin_px=2.0,
                        incidence_deg=0.0, far_m=6.0, step_m=0.001):
    """Smallest range from the axle midpoint (metres) at which an upright square stays wholly in the picture for
    every range from there out to far_m; None if it is not in view at far_m. half_side_m 0.10 is the 160 mm tag
    with its 20 mm white border, 0.08 the black square alone. Walks inward from far_m in step_m steps, so a square
    that leaves the top of the picture when close is caught whatever the mount angles are."""
    r = far_m
    if not square_in_view(camera, r, bearing_deg, center_height_m, half_side_m, margin_px, incidence_deg):
        return None
    while r - step_m > 0.0 and square_in_view(camera, r - step_m, bearing_deg, center_height_m, half_side_m,
                                              margin_px, incidence_deg):
        r -= step_m
    return r
