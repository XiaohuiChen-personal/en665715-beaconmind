#!/usr/bin/env python3
"""Generate urdf/car_props.xacro from configs/car.json, plus configs/camera.json when it exists (M2.T4 step 4).

Usage (repository root):
    python3 course-project/ros2_ws/src/beaconmind_description/beaconmind_description/gen_props.py \
        --car course-project/configs/car.json --camera course-project/configs/camera.json \
        --out course-project/ros2_ws/src/beaconmind_description/urdf/car_props.xacro
Add --check to compare instead of writing: exit 1 with a unified diff if the file is out of date. A --camera
path that does not exist means "no camera.json yet" (M1.T7 not done). A camera.json whose extrinsics are still null
(M1.T7 writes it that way until its step 8) is used only for what it has: extrinsics_used() decides, separately for
x/y/z and for the angles, whether the view takes them from camera.json, and every comment and the printout say
which source the value came from. Standard library only; Python 3.10+.

What it reads. M2.T4 says this script reads the VIEW beaconmind.config.load_car(car, camera) (M2.T3 step 2),
never the raw M1 keys. M2.T3 is not written yet, so load_car_standin() below is a STAND-IN for that view: it
implements the M2.T3 car-view mapping table for bm.car/1 and bm.camera/1 and nothing more. When M2.T3 lands,
make build_view() call beaconmind.config.load_car instead and delete the stand-in; test_props_up_to_date then
shows whether the generated text changed. Three URDF inputs are not view keys, so they are read from car.json's
raw values (RAW_KEYS): track_outer_m and track_inner_m (the tyre faces, for the guard in
beaconmind_car.urdf.xacro that keeps the motor boxes off the tyres) and caster_diameter_m (the caster sphere's
radius; the view carries only the sphere's centre).

What it does not generate. Geometry that car.json does not carry (plate outline, part boxes, stand-in part
masses, the lever-rule inputs for the centre of mass) is in the hand-written urdf/car_geometry_extras.xacro,
which beaconmind_car.urdf.xacro includes after car_props.xacro.

Heights. car.json lens_z_m and camera.json extrinsics z_m (M1.T7 step 8) are heights above the FLOOR; the URDF's
base_link is at AXLE height, so the xacro subtracts wheel_radius (camera_z = camera_h - wheel_radius). car.json
imu_z_m is already a height above the AXLE midpoint (M1.T9 step 3 defines the IMU position "from the axle midpoint";
write_car_json.py derives it from the floor reading), so it is imu_z as it is; the generated file adds wheel_radius
back only for imu_top_h, the floor height that the board box in beaconmind_car.urdf.xacro uses.

AI-assisted: Claude Opus 5.5 (xhigh effort) via Claude Code, 2026-10-10: wrote this generator, the load_car
stand-in and optical_to_link_rpy_deg (reimplemented from the M2.T3 step 2 mapping table in
course-project/plan/M2-sim-mvp.md, not copied from any code); later the same day, after a review, switched the IMU
height to the axle-relative imu_z_m; after a second review, added extrinsics_used() so the camera comments and the
printout follow the source the view actually used (a camera.json with null extrinsics had been labelled as
calibrated).
AI-assisted: Claude Opus 5.5 (xhigh effort) via Cursor, 2026-10-29: made the generated texts independent of particular
readings and dates, so test_props_up_to_date can keep them honest (the mass, front- and rear-overhang comments point to
the source row's notes and to car_geometry_extras.xacro / evidence/M1/M1.T16 instead of quoting readings; the header
names the CSV car.json uses, through evidence_csv(), which says so explicitly when car.json names none or several).
The values and the logic that produces them are unchanged.
"""

import argparse
import difflib
import hashlib
import json
import math
import sys
from pathlib import Path

ROLLOUT_REVS = 5  # M1.T9 step 3: each roll-out covers five revolutions
NOMINAL_TICKS = 4320  # README §9.1: 12 PPR x 4 edges x 90:1 gearbox (nominal, not measured)
RAW_KEYS = ("track_outer_m", "track_inner_m", "caster_diameter_m")
# The camera mount may be off level by a few degrees (M1.T7 step 9 pass: |pitch|, |yaw| <= 5, |roll| <= 3); a
# camera_link angle beyond this bound means camera.json's angles were read in the wrong convention.
MAX_MOUNT_DEG = 20.0


# ----------------------------------------------------------------------------------------- small helpers

def sha12(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]


def repo_relative(path):
    """'course-project/...' when the path is inside the course-project tree (same text on the Mac, the Spark
    and in the container), else the bare file name."""
    parts = Path(path).resolve().parts
    if "course-project" in parts:
        return "/".join(parts[parts.index("course-project"):])
    return Path(path).name


def fmt(x):
    """A float literal xacro reads back as the same float (repr round-trips; +0.0 turns -0.0 into 0.0)."""
    return repr(float(x) + 0.0)


def rpy_matrix(roll, pitch, yaw):
    """URDF fixed-axis rotation R = Rz(yaw) Ry(pitch) Rx(roll), radians, as rows."""
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    return [
        [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
        [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
        [-sp, cp * sr, cp * cr],
    ]


def matrix_rpy(m):
    """Inverse of rpy_matrix (away from pitch = +-90 deg): (roll, pitch, yaw) in radians."""
    pitch = math.asin(max(-1.0, min(1.0, -m[2][0])))
    return math.atan2(m[2][1], m[2][2]), pitch, math.atan2(m[1][0], m[0][0])


def optical_to_link_rpy_deg(roll_deg, pitch_deg, yaw_deg):
    """base_link -> camera_optical_frame rpy (degrees) -> base_link -> camera_link rpy (degrees).

    camera_link -> camera_optical_frame is the fixed REP 103 rotation rpy = (-90, 0, -90) deg, so
    R_link = R_opt * R_fixed^-1 (M2.T3 step 2). (-90, 0, -90) maps to (0, 0, 0): a level camera looking along +x.
    """
    r_opt = rpy_matrix(*(math.radians(a) for a in (roll_deg, pitch_deg, yaw_deg)))
    r_fixed = rpy_matrix(-math.pi / 2, 0.0, -math.pi / 2)
    r_link = [[sum(r_opt[i][k] * r_fixed[j][k] for k in range(3)) for j in range(3)] for i in range(3)]
    return [math.degrees(a) for a in matrix_rpy(r_link)]


# ----------------------------------------------------------------------------- the load_car stand-in

def unwrap(values):
    """bm.car/1 'values' -> {key: value}: a per-value object {"value": ...} is unwrapped to its value."""
    return {k: (v["value"] if isinstance(v, dict) and "value" in v else v) for k, v in values.items()}


def read_camera(camera_path):
    """The parsed camera.json, or None when camera_path is None or the file does not exist (M1.T7 not done)."""
    if camera_path is None or not Path(camera_path).is_file():
        return None
    return json.loads(Path(camera_path).read_text(encoding="utf-8"))


def _number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def extrinsics_used(cam):
    """(xyz_from_camera, rpy_from_camera) for a parsed camera.json (or None): does the view take camera_xyz_m and
    camera_rpy_deg from camera.json?

    The file existing is not enough: M1.T7 writes camera.json with null extrinsics until its step 8 fills them
    (bm.camera/1 allows null), and step 8 may fill x/y/z before the angles. So xyz comes from camera.json only when
    x_m, y_m and z_m are ALL numbers, the angles only when roll_deg, pitch_deg and yaw_deg all are; otherwise the
    view falls back to the car.json lens readings and the ASSUMED [0, 0, 0] (M2.T3 mapping table). The view
    stand-in and the comments render() writes both use this one rule, so a comment cannot claim calibrated
    extrinsics the view did not use.
    """
    ext = (cam or {}).get("extrinsics") or {}
    xyz = all(_number(ext.get(k)) for k in ("x_m", "y_m", "z_m"))
    rpy = all(_number(ext.get(k)) for k in ("roll_deg", "pitch_deg", "yaw_deg"))
    return xyz, rpy


def load_car_standin(car_path, camera_path=None):
    """STAND-IN for beaconmind.config.load_car(path, camera_path) (M2.T3 step 2, not written yet).

    Builds the car VIEW from a bm.car/1 file with the M2.T3 "Car view mapping" table (first source present
    wins; stated defaults are listed in view["assumptions"]; KeyError names every key with neither a source nor
    a default). A camera_path that is None or does not exist means no camera.json. Returns the view dict,
    including "status" ("measured") and "assumptions" (list of strings).
    """
    car = json.loads(Path(car_path).read_text(encoding="utf-8"))
    if car.get("schema") != "bm.car/1":
        raise ValueError("%s is not a bm.car/1 file (schema = %r)" % (car_path, car.get("schema")))
    v = unwrap(car["values"])
    cam = read_camera(camera_path)
    ext = (cam or {}).get("extrinsics") or {}
    xyz_from_cam, rpy_from_cam = extrinsics_used(cam)
    view, assumptions, missing = {}, [], []

    def first(*keys):
        for key in keys:
            if v.get(key) is not None:
                return v[key]
        return None

    # wheel_diameter_m: wheel_diameter_m or effective_diameter_m; else mean of the roll-outs / (5 pi)
    d = first("wheel_diameter_m", "effective_diameter_m")
    if d is None and v.get("rollout_left_m") is not None and v.get("rollout_right_m") is not None:
        d = (v["rollout_left_m"] + v["rollout_right_m"]) / 2.0 / (ROLLOUT_REVS * math.pi)
    view["wheel_diameter_m"] = d
    # track_width_m: track_width_m; else (outer + inner) / 2
    tw = first("track_width_m")
    if tw is None and v.get("track_outer_m") is not None and v.get("track_inner_m") is not None:
        tw = (v["track_outer_m"] + v["track_inner_m"]) / 2.0
    view["track_width_m"] = tw
    view["axle_to_front_m"] = first("front_overhang_m")
    view["axle_to_rear_m"] = first("rear_overhang_m")
    view["body_width_m"] = first("chassis_width_m")
    for key, default in (("chassis_height_m", 0.06), ("wheel_width_m", 0.025)):
        view[key] = first(key)
        if view[key] is None:
            view[key] = default
            assumptions.append("%s: %s (stand-in; visuals, collision height and inertia only)" % (key, default))
    sr = first("sweep_radius_m")
    if sr is None and v.get("corners"):
        sr = max(math.hypot(x, y) for x, y in v["corners"])
    view["sweep_radius_m"] = sr
    # camera_xyz_m: camera.json extrinsics [x_m, y_m, z_m] when all three are numbers; else the car.json lens readings
    if xyz_from_cam:
        xyz = [ext["x_m"], ext["y_m"], ext["z_m"]]
    else:
        xyz = [v.get("lens_x_m"), v.get("lens_y_m"), v.get("lens_z_m")]
    view["camera_xyz_m"] = None if any(c is None for c in xyz) else [float(c) for c in xyz]
    view["lens_height_m"] = None if view["camera_xyz_m"] is None else view["camera_xyz_m"][2]
    # camera_rpy_deg (camera_link, x forward): from the extrinsics' optical-frame rpy; else [0, 0, 0], assumed
    if rpy_from_cam:
        view["camera_rpy_deg"] = optical_to_link_rpy_deg(ext["roll_deg"], ext["pitch_deg"], ext["yaw_deg"])
    else:
        view["camera_rpy_deg"] = [0.0, 0.0, 0.0]
        assumptions.append("camera_rpy_deg: [0, 0, 0] (no calibrated extrinsics: configs/camera.json %s)"
                           % ("absent" if cam is None else "has null angles"))
    imu = [v.get("imu_x_m"), v.get("imu_y_m"), v.get("imu_z_m")]
    view["imu_xyz_m"] = None if any(c is None for c in imu) else [float(c) for c in imu]
    if isinstance(v.get("mass_kg"), (int, float)):
        view["mass_kg"] = v["mass_kg"]
    else:
        view["mass_kg"] = 0.8
        assumptions.append("mass_kg: 0.8 (not measured; Isaac physics only)")
    ticks = first("counts_per_rev", "ticks_per_wheel_rev")
    if ticks is None and v.get("counts_per_rev_left") is not None and v.get("counts_per_rev_right") is not None:
        ticks = (v["counts_per_rev_left"] + v["counts_per_rev_right"]) / 2.0
    if ticks is None:
        ticks = NOMINAL_TICKS
        assumptions.append("ticks_per_wheel_rev: %d (nominal, README 9.1; encoder counts not measured)" % NOMINAL_TICKS)
    view["ticks_per_wheel_rev"] = ticks
    if v.get("caster_x_m") is not None and v.get("caster_diameter_m") is not None and d is not None:
        view["caster_xyz_m"] = [v["caster_x_m"], 0.0, v["caster_diameter_m"] / 2.0 - d / 2.0]
    else:
        view["caster_xyz_m"] = None

    missing = sorted(k for k, val in view.items() if val is None)
    if missing:
        raise KeyError("car.json/camera.json provide no value and no stated default for: %s" % ", ".join(missing))
    view["status"] = "measured"
    view["assumptions"] = assumptions
    return view


def build_view(car_path, camera_path):
    """The one place that obtains the view. M2.T3: replace with beaconmind.config.load_car(car_path, camera_path)."""
    return load_car_standin(car_path, camera_path)


# ----------------------------------------------------------------------------------- the generated text

def evidence_csv(entries):
    """The measurement CSV that car.json's values name in their "evidence" fields. When they name none or several,
    say so explicitly ("car.json names N CSVs: a, b"; sorted, so the generated text stays deterministic)."""
    named = sorted({e["evidence"] for e in entries.values()
                    if isinstance(e, dict) and str(e.get("evidence", "")).endswith(".csv")})
    if len(named) == 1:
        return named[0]
    return "car.json names %d CSVs: %s" % (len(named), ", ".join(named) if named else "none")


def describe(entries, key):
    """'car.json <key> = <value> <unit>, <status> +- <u> <unit> (<source>)' for one per-value object."""
    if key not in entries:
        return "car.json has no %s; the view derived the value from other keys" % key
    e = entries[key]
    unc = "" if e.get("uncertainty") is None else " +- %s %s" % (fmt(e["uncertainty"]), e["unit"])
    return "car.json %s = %s %s, %s%s (%s)" % (key, json.dumps(e["value"]), e["unit"], e["status"], unc, e["source"])


def render(car_path, camera_path=None):
    """Return the full text of car_props.xacro for these inputs (deterministic: no dates, no absolute paths)."""
    view = build_view(car_path, camera_path)
    car = json.loads(Path(car_path).read_text(encoding="utf-8"))
    entries = car["values"]
    raw = unwrap(entries)
    for key in RAW_KEYS:
        if raw.get(key) is None:
            raise KeyError("car.json has no %s (M1.T9 must measure it; do not invent it)" % key)
    cam = read_camera(camera_path)
    has_camera = cam is not None
    # Where the view's camera pose came from (extrinsics_used): label each value by that, not by the file existing.
    xyz_from_cam, rpy_from_cam = extrinsics_used(cam)

    # Checks that stop generation instead of writing a wrong model.
    wheel_radius = round(view["wheel_diameter_m"] / 2, 6)
    caster_radius = round(raw["caster_diameter_m"] / 2, 6)
    if caster_radius <= 0:
        raise ValueError("caster radius must be > 0 so the caster sphere touches the floor, got %r" % caster_radius)
    if abs(round(caster_radius - wheel_radius, 6) - view["caster_xyz_m"][2]) > 1e-9:
        raise ValueError("caster sphere z from caster_diameter_m disagrees with the view's caster_xyz_m")
    if abs(view["track_width_m"] - (raw["track_outer_m"] + raw["track_inner_m"]) / 2) > 1e-9:
        raise ValueError("track_width_m %r is not (track_outer_m + track_inner_m) / 2" % view["track_width_m"])
    if rpy_from_cam:
        bad = [a for a in view["camera_rpy_deg"] if abs(a) > MAX_MOUNT_DEG]
        if bad:
            raise ValueError(
                "camera_link rpy %r deg is beyond +-%s deg: camera.json extrinsics roll/pitch/yaw do not read as the "
                "base_link -> camera_optical_frame rotation M2.T3 expects (M1.T7 step 9 records mount angles near "
                "0 instead). Settle the convention before generating." % (view["camera_rpy_deg"], MAX_MOUNT_DEG))

    def lit(name, value, comment):
        return [comment, '  <xacro:property name="%s" value="%s"/>' % (name, fmt(value))]

    def expr(name, text, comment):
        return [comment, '  <xacro:property name="%s" value="%s"/>' % (name, text)]

    def c(text):
        return "  <!-- %s -->" % text

    xyz, rpy = view["camera_xyz_m"], view["camera_rpy_deg"]
    if xyz_from_cam:
        cam_src = "configs/camera.json extrinsics (view camera_xyz_m)"
        cam_z_src = "configs/camera.json extrinsics z_m, lens height above the FLOOR (M1.T7 step 8)"
    else:
        why = "configs/camera.json extrinsics x_m/y_m/z_m are not all set" if has_camera else "no camera.json"
        cam_src = "%s, so the view uses the ruler reading" % why
        cam_z_src = "%s; lens height above the FLOOR" % describe(entries, "lens_z_m")
        if has_camera:
            cam_z_src += "; " + cam_src
    if rpy_from_cam:
        rpy_src = "view camera_rpy_deg = optical_to_link_rpy_deg(camera.json roll/pitch/yaw), in radians"
    else:
        rpy_src = ("ASSUMED by the view: camera_rpy_deg = [0, 0, 0] (%s); the M1.T7 calibration sets it"
                   % ("configs/camera.json roll_deg/pitch_deg/yaw_deg are not all set" if has_camera
                      else "no camera.json"))

    lines = [
        '<?xml version="1.0"?>',
        "<!--",
        "  GENERATED by beaconmind_description/gen_props.py (M2.T4 step 4). Do not edit by hand: change",
        "  configs/car.json (M1.T9, course-project/tools/write_car_json.py) or configs/camera.json (M1.T7) and run",
        "  gen_props.py again. test_props_up_to_date fails while this file is out of date.",
        "",
        "  AI-assisted: Claude Opus 5.5 (xhigh effort) via Claude Code, 2026-10-10: wrote the generator that writes",
        "  this file. AI-assisted: Claude Opus 5.5 (xhigh effort) via Cursor, 2026-10-29: made its comment texts",
        "  independent of particular readings. The readings behind it are Xiaohui Chen's, except the CSV rows whose",
        "  instrument starts with 'CAD' (a classmate's plate CAD); each CSV row carries its own date.",
        "",
        "  Inputs:",
        "    %s  sha256 %s..." % (repo_relative(car_path), sha12(car_path)),
        "    camera.json: %s" % (("%s  sha256 %s...; extrinsics used: x/y/z %s, roll/pitch/yaw %s"
                                  % (repo_relative(camera_path), sha12(camera_path),
                                     "yes" if xyz_from_cam else "NO (not all set; car.json lens readings)",
                                     "yes" if rpy_from_cam else "NO (not all set; ASSUMED 0)"))
                                 if has_camera else "absent (M1.T7 calibration not done)"),
        "  Read through load_car_standin(), the stand-in for the M2.T3 view beaconmind.config.load_car.",
        "  View status: %s. View assumptions (values from a stated default, not a measurement):" % view["status"],
    ]
    lines += ["    - %s" % a for a in view["assumptions"]] or ["    (none)"]
    lines += [
        "",
        "  Only the numbers car.json (and camera.json) carry are here. Plate outline, part boxes, part masses and the",
        "  centre-of-mass inputs are in the hand-written car_geometry_extras.xacro (same folder).",
        "",
        "  Conventions (M2.T4 / README C1): base_link = midpoint between the two drive-wheel centres, AT AXLE HEIGHT",
        "  (z = 0 at the axle). +x = toward the camera lens / caster end (the car's front). +y = robot left. +z = up.",
        "  Lengths in metres, masses in kg, angles in radians. Values named *_h are heights above the FLOOR (model",
        "  z = floor height - wheel_radius); camera_h is one, imu_z (car.json imu_z_m) is already above the AXLE.",
        "  Each comment gives the car.json entry: value, status, uncertainty and source row.",
        "  Source CSV (named by car.json's evidence fields): %s." % evidence_csv(entries),
        "  Derived values: evidence/M1/M1.T9/derived.txt.",
        "-->",
        '<robot xmlns:xacro="http://www.ros.org/wiki/xacro">',
        "",
        c("================= Drive wheels ================="),
    ]
    lines += lit("wheel_diameter", view["wheel_diameter_m"], c(describe(entries, "wheel_diameter_m")))
    lines += expr("wheel_radius", "${round(wheel_diameter / 2, 6)}", c("derived: wheel_diameter / 2"))
    wheel_width_note = (describe(entries, "wheel_width_m") if "wheel_width_m" in entries
                        else "ASSUMED by the view: wheel_width_m stand-in")
    lines += lit("wheel_width", view["wheel_width_m"], c(wheel_width_note))
    lines += lit("track_outer", raw["track_outer_m"],
                 c(describe(entries, "track_outer_m") + "; outer tyre face to outer tyre face"))
    lines += lit("track_inner", raw["track_inner_m"],
                 c(describe(entries, "track_inner_m") + "; inner face to inner face"))
    lines += lit("track_width", view["track_width_m"],
                 c("view track_width_m, " + describe(entries, "track_width_m")
                   + " = (track_outer + track_inner) / 2, wheel centre to wheel centre"))
    lines += expr("wheel_separation", "${track_width}",
                  c("alias used by the Gazebo DiffDrive plugin and the instructor's lab file: identical to track_width"))
    lines += [
        "",
        c("================= Body extents ================="),
    ]
    lines += lit("axle_to_front", view["axle_to_front_m"],
                 c("view axle_to_front_m, " + describe(entries, "front_overhang_m")
                   + "; front-most point (B3: the ESP32-CAM's USB-C side); the source row's notes in the CSV say"
                   " whether a cable was fitted"))
    lines += lit("axle_to_rear", view["axle_to_rear_m"],
                 c("view axle_to_rear_m, " + describe(entries, "rear_overhang_m")
                   + "; rear-most point of the PLATE (B4); parts reaching further back are recorded in"
                   " car_geometry_extras.xacro and evidence/M1/M1.T16"))
    lines += lit("body_width", view["body_width_m"],
                 c("view body_width_m, " + describe(entries, "chassis_width_m")
                   + "; widest body point = the rear wing (tyres excluded)"))
    height_note = (describe(entries, "chassis_height_m") if "chassis_height_m" in entries
                   else "ASSUMED by the view: chassis_height_m stand-in")
    lines += lit("chassis_height", view["chassis_height_m"],
                 c("view chassis_height_m, " + height_note
                   + "; main body height (gearbox bottoms to battery-holder top), used for the chassis inertia box"))
    lines += [
        "",
        c("================= Camera (the lens = optical centre; camera_link sits here) ================="),
    ]
    if xyz_from_cam:
        lines += lit("camera_x", xyz[0], c("view camera_xyz_m[0], " + cam_src))
        lines += lit("camera_y", xyz[1], c("view camera_xyz_m[1], " + cam_src))
    else:
        lines += lit("camera_x", xyz[0], c("view camera_xyz_m[0], " + describe(entries, "lens_x_m") + "; " + cam_src))
        lines += lit("camera_y", xyz[1], c("view camera_xyz_m[1], " + describe(entries, "lens_y_m") + "; " + cam_src))
    lines += lit("camera_h", view["lens_height_m"], c("view lens_height_m, " + cam_z_src))
    lines += expr("camera_z", "${round(camera_h - wheel_radius, 6)}",
                  c("derived: camera_h - wheel_radius (base_link is at axle height)"))
    lines += lit("camera_roll", math.radians(rpy[0]), c(rpy_src))
    lines += lit("camera_pitch", math.radians(rpy[1]), c(rpy_src))
    lines += lit("camera_yaw", math.radians(rpy[2]), c(rpy_src))
    lines += [
        "",
        c("================= IMU (the BNO055 board centre, at its top surface) ================="),
    ]
    lines += lit("imu_x", view["imu_xyz_m"][0], c("view imu_xyz_m[0], " + describe(entries, "imu_x_m")))
    lines += lit("imu_y", view["imu_xyz_m"][1],
                 c("view imu_xyz_m[1], " + describe(entries, "imu_y_m") + "; +y = robot LEFT"))
    lines += lit("imu_z", view["imu_xyz_m"][2],
                 c("view imu_xyz_m[2], " + describe(entries, "imu_z_m") + "; board top above the AXLE (base_link)"))
    lines += expr("imu_top_h", "${round(imu_z + wheel_radius, 6)}",
                  c("derived: imu_z + wheel_radius = board top above the FLOOR (for the board box)"))
    lines += [
        "",
        c("================= Caster (swivel: white wheel in a metal fork) ================="),
    ]
    lines += lit("caster_diameter", raw["caster_diameter_m"], c(describe(entries, "caster_diameter_m")))
    lines += expr("caster_radius", "${round(caster_diameter / 2, 6)}",
                  c("derived: caster_diameter / 2. gen_props.py and beaconmind_car.urdf.xacro stop if it is not positive."))
    lines += lit("caster_x", view["caster_xyz_m"][0],
                 c("view caster_xyz_m[0], " + describe(entries, "caster_x_m")
                   + "; floor contact with the caster TRAILING"))
    lines += lit("caster_y", view["caster_xyz_m"][1],
                 c("view caster_xyz_m[1] = 0.0 (the view puts the caster on the centre line; IMG_7436 shows it within"
                   " about 4 mm)"))
    lines += expr("caster_z", "${round(caster_radius - wheel_radius, 6)}",
                  c("derived: caster sphere centre = caster_radius - wheel_radius, so the sphere touches the floor"
                    " (equals view caster_xyz_m[2])"))
    lines += [
        "",
        c("================= Mass ================="),
    ]
    lines += lit("mass", view["mass_kg"],
                 c("view mass_kg, " + describe(entries, "mass_kg") + "; whole car as weighed; the source row's notes in"
                   " the CSV say what was on the car")
                 if "mass_kg" in entries else c("ASSUMED by the view: mass_kg stand-in"))
    lines += ["", "</robot>", ""]
    return "\n".join(lines)


def main(argv=None):
    pkg = Path(__file__).resolve().parents[1]
    course = Path(__file__).resolve().parents[4]
    ap = argparse.ArgumentParser(description="Write car_props.xacro from configs/car.json (+ camera.json).")
    ap.add_argument("--car", type=Path, default=course / "configs" / "car.json")
    ap.add_argument("--camera", type=Path, default=course / "configs" / "camera.json")
    ap.add_argument("--out", type=Path, default=pkg / "urdf" / "car_props.xacro")
    ap.add_argument("--check", action="store_true", help="compare with --out instead of writing it")
    args = ap.parse_args(argv)

    text = render(args.car, args.camera)
    if args.check:
        current = args.out.read_text(encoding="utf-8") if args.out.is_file() else ""
        if current == text:
            print("up to date: %s" % args.out)
            return 0
        sys.stdout.writelines(difflib.unified_diff(
            current.splitlines(True), text.splitlines(True), str(args.out), "generated"))
        return 1
    args.out.write_text(text, encoding="utf-8")
    cam = read_camera(args.camera)
    if cam is None:
        cam_note = "camera.json absent"
    else:
        xyz_from_cam, rpy_from_cam = extrinsics_used(cam)
        cam_note = "camera.json present; camera x/y/z from %s; camera angles %s" % (
            "camera.json extrinsics" if xyz_from_cam else "car.json lens_*_m (camera.json x_m/y_m/z_m not all set)",
            "from camera.json extrinsics" if rpy_from_cam else "ASSUMED 0 (camera.json roll/pitch/yaw not all set)")
    print("wrote %s from %s (%s)" % (args.out, args.car, cam_note))
    return 0


if __name__ == "__main__":
    sys.exit(main())
