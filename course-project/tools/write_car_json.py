#!/usr/bin/env python3
"""Build configs/car.json (schema bm.car/1) from a car measurement CSV (plan/M1-foundations.md M1.T9 step 5).

Usage (repository root, Mac venv):
    course-project/.venv/bin/python course-project/tools/write_car_json.py \
        course-project/evidence/M1/M1.T9/measurements-xiaohui-chen-2026-10-10.csv \
        --measured course-project/evidence/M1/M1.T9/measured.json \
        --updated 2026-10-10 --out course-project/configs/car.json

Input CSV: columns quantity, reading_1, reading_2, reading_3, unit, instrument, notes (the M1.T9 template,
course-project/tools/car_measurements_template.csv; assignments/assignment6/measurements.csv uses the same columns).
Lines starting with '#' are comments. Rules:
  - A row named <q>_corrected / <q>_recheck / <q>_remeasure / <q>_remeasure<N> is a later reading of <q> and
    replaces it; among several such rows the one further down the file wins. ros2_ws/src/beaconmind_description/
    test/test_urdf.py reads the CSV through read_csv and ROW_FOR_KEY below, so change them with care.
  - A row whose notes start with "SUPERSEDED" is not an input. Rows without a numeric reading_1 are skipped, except
    the text row imu_axes (unit "text", the description in reading_1), which is written as a string value.
  - Units: mm and m for lengths, g and kg for masses; every numeric value in car.json is in m or kg.
Each plan key (M1.T9 step 5 "Exact values keys") is looked up first under its own name, then under the row name
the 2026-10-10 session used (ROW_FOR_KEY). The writer also reads the rows in EXTRA_ROWS, which have no plan key.
A key with no row is OMITTED and listed under "omitted" in the printout; the writer never invents a value.

Heights. lens_z_m is the lens centre height above the FLOOR (M1.T9 step 3 says "measure as M1.T7 step 8", and
M1.T7 step 8 defines the camera's z_m that way). imu_z_m is the BNO055 board top above the AXLE midpoint, because
M1.T9 step 3 defines the IMU position "from the axle midpoint" and M2.T3/M2.T4 pass it to imu_link unchanged: a row
named imu_z_m is used as it is; otherwise imu_z_m is derived as S1_imu_board_top_h (above the floor) minus
wheel_diameter_m / 2 (the axle height that base_link uses).

Uncertainty (the "uncertainty" field, in the value's SI unit; every rule constant is SI, so typing a row in m or kg
instead of mm or g changes nothing):
  - two or more readings: max(half the spread, the single-reading rule below), as M1.T9 step 5 says;
  - one reading: 2 mm for a ruler/tape length, 5 mm when the notes say "around", 1 g for a scale reading;
  - axle-datum floor: every x measured from the axle line (AXLE_DATUM_ROWS, plan keys and 2026-10-10 row names)
    carries at least 3 mm (assignments/assignment6/review/MEASUREMENT-REVIEW.md #15);
  - stated exceptions in UNCERTAINTY_OVERRIDE: the wing depth B5b (review #7) and the two-scale mass;
  - a row whose instrument starts with "CAD" (a dimension read off the plate's CAD model, not a ruler) gets CAD_M,
    0.5 mm, before any of the rules above; the axle-datum floor still applies to such a row if it is an axle-line x;
  - derived values: first-order propagation, root-sum-square of the independent input terms (car_model.rss).
Plate front. When the CSV has the two CAD outline rows P1_plate_front_arc_radius and P2_plate_front_corner_radius, the
plate-front corners are the farthest points of the rounded front (an arc with its apex at B1 and two corner fillets,
car_model.rounded_front_corner); without them, the square corners (B1, +-B5 narrow / 2) of the 2026-10-10 build.
Status is "measured" for every value written here: each is a reading or arithmetic on readings, with ONE stated
assumption. `corners`, and therefore `sweep_radius_m`, include the ESP32-CAM front corners and the plate-front
corners, whose y = +-(measured width) / 2 ASSUMES that those parts are centred on y = 0 (their widths were measured,
their sideways offsets were not). The `source` text of both entries says so, and so does the derived.txt printout.
No other estimate or assumption is written to car.json.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-10-10: wrote this writer (mapping table, superseding rule,
uncertainty rules, derived keys, printout); later the same day, after a review, made imu_z_m axle-relative, let the
corners use the plan-key rows, read the imu_axes text row, and labelled the corners' centring assumption; after a
second review, put the uncertainty constants in SI units (an override used to be multiplied by the row's unit
factor, so a row typed in m or kg came out 1000x too uncertain) and made the 3 mm axle datum a floor for every
axle-line row (B3 and S1 x had been left at 2 mm); after a third review, only the docstring line naming
test_urdf.py's use of read_csv changed; 2026-10-16: added the CAD uncertainty rule (CAD_M), the two plate-front
outline rows (P1, P2) and the rounded plate-front corners, for the plate CAD a classmate shared
(the private course repo (plate CAD is not published here)). The measurements are Xiaohui Chen's; the CAD rows are the classmate's model.
AI-assisted: Claude Opus 5.5 (xhigh effort) via Cursor, 2026-10-29: made the K1_total_mass uncertainty reason generic
(it named only the 2026-10-10 readings); the value TWO_SCALE_KG and all logic are unchanged.
"""

import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path

COURSE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(COURSE / "beaconmind" / "src"))

from beaconmind import car_model  # noqa: E402  (standard library only)

SUPERSEDING_SUFFIX = re.compile(r"_(corrected|recheck|remeasure\d*)$")
TO_SI = {"mm": 0.001, "m": 1.0, "g": 0.001, "kg": 1.0}
SI_UNIT = {"mm": "m", "m": "m", "g": "kg", "kg": "kg"}

# Plan key -> the row name used on 2026-10-10 (assignments/assignment6/measurements.csv).
ROW_FOR_KEY = {
    "wheel_width_m": "W2_tyre_width",
    "track_outer_m": "W3_track_outer",
    "track_inner_m": "W3_track_inner",
    "caster_x_m": "C2_caster_contact_x",
    "caster_diameter_m": "C1_caster_wheel_diameter",
    "front_overhang_m": "B3_front_most_x",
    "rear_overhang_m": "B4_rear_most_x",
    "chassis_width_m": "B5_plate_width_max",
    "lens_x_m": "S3_lens_x",
    "lens_y_m": "S3_lens_y",
    "lens_z_m": "S3_lens_centre_h",
    "imu_x_m": "S1_imu_board_centre_x",
    "imu_y_m": "S1_imu_board_centre_y",
    "mass_kg": "K1_total_mass",
}
# imu_z_m has no alias: S1_imu_board_top_h is a height above the FLOOR, imu_z_m a height above the AXLE (docstring).
IMU_TOP_ROW = "S1_imu_board_top_h"
# Rows the writer reads that have no plan key, and what each one feeds (car_measurements_template.csv lists them all).
EXTRA_ROWS = {
    "W1_tyre_diameter_direct": "wheel_diameter_m when there is no roll-out (a direct, unloaded tyre diameter)",
    "B1_plate_front_x": "corners: the plate-front corners (x)",
    "B2_plate_rear_x": "corners: the rear wing tips (x = -B2 + B5b)",
    "B5_plate_width_narrow": "corners: the plate-front corners (y = +-width / 2, strip assumed centred)",
    "B5_plate_width_max": "corners: the rear wing tips (y); also chassis_width_m when that row is blank",
    "B5b_wing_depth_centre": "corners: the rear wing tips (x)",
    "B9_lowest_body_h": "chassis_height_m = B10_battery_holder_top_h - B9_lowest_body_h",
    "B10_battery_holder_top_h": "chassis_height_m",
    "B14_esp32cam_width": "corners: the ESP32-CAM front corners (y = +-width / 2, board assumed centred)",
    "C2b_caster_front_swung_x": "corners: the caster wheel's front with the caster swung fully forward",
    IMU_TOP_ROW: "imu_z_m = this - wheel_diameter_m / 2 when there is no imu_z_m row",
    "P1_plate_front_arc_radius": "corners: the plate-front corners (radius of the front-edge arc, apex at B1; with P2)",
    "P2_plate_front_corner_radius": "corners: the plate-front corners (radius of the two front corner fillets; with P1)",
}
FRONT_ARC_ROW, FRONT_CORNER_ROW = "P1_plate_front_arc_radius", "P2_plate_front_corner_radius"
# Raw keys in the order they are written (plan M1.T9 step 5 order).
RAW_KEYS = [
    "rollout_left_m", "rollout_right_m", "wheel_width_m", "track_outer_m", "track_inner_m", "caster_x_m",
    "caster_diameter_m", "front_overhang_m", "rear_overhang_m", "chassis_width_m", "lens_x_m", "lens_y_m",
    "lens_z_m", "imu_x_m", "imu_y_m", "imu_z_m", "mass_kg",
]
# Step-3 quantities the writer DERIVES (from the rows named in EXTRA_ROWS and the raw keys) instead of reading.
DERIVED_STEP3_KEYS = ["corners", "chassis_length_m", "chassis_height_m"]
TEXT_KEYS = ["imu_axes"]
ROLLOUT_REVS = 5  # M1.T9 step 3: five revolutions of each wheel

# Uncertainty exceptions. EVERY constant below is in SI units (m or kg) and is used as it is, so a row typed in m or
# kg gets the same uncertainty as one typed in mm or g (the template allows both).
#
# (a) Axle-datum floor. Every x measured from the drive-wheel axle line carries at least AXLE_DATUM_M, because the
#     axle line itself was located only to about 3 mm (assignments/assignment6/review/MEASUREMENT-REVIEW.md #15,
#     raised for B1/B2: "Keep 131 / 77 +- 3 mm"; the review's 3 mm is the total, so it is a floor, not added to the
#     2 mm ruler rule). It applies to each reading taken from that line, under its plan key and under its 2026-10-10
#     row name. A larger rule ('around' = 5 mm) or a larger half-spread still wins. y (from the centre line) and
#     heights (from the floor) use other datums and are not in the set.
AXLE_DATUM_M = 0.003
AXLE_DATUM_WHY = "axle-datum floor: x from the axle line, which is located to about 3 mm (review #15)"
AXLE_DATUM_ROWS = frozenset([
    # plan keys (M1.T9 step 3: "Axle line to ...", "from the axle midpoint")
    "front_overhang_m", "rear_overhang_m", "caster_x_m", "lens_x_m", "imu_x_m",
    # 2026-10-10 rows ("axle line to ...", "... BEHIND the axle line", "... ahead of axle line")
    "B1_plate_front_x", "B2_plate_rear_x", "B3_front_most_x", "B4_rear_most_x", "C2_caster_contact_x",
    "C2b_caster_front_swung_x", "S3_lens_x", "S1_imu_board_centre_x",
])
# (b) Exceptions that replace the single-reading rule, with the reason printed next to the value.
TWO_SCALE_KG = car_model.rss(0.001, 0.001)
TWO_SCALE_WHY = "sum of two 1 g scale readings (caster scale + drive-wheel scale)"
UNCERTAINTY_OVERRIDE = {
    "B5b_wing_depth_centre": (0.004, "review #7: photos suggest 35-37 mm against the 40 mm reading of 2026-10-10"),
    "K1_total_mass": (TWO_SCALE_KG, "two-scale rule (two 1 g readings, root-sum-square), kept for every whole-car "
                      "mass row; the K-row notes give the readings"),
    # The template's mass_kg row asks for the same two-scale sum (its notes: "write the SUM").
    "mass_kg": (TWO_SCALE_KG, TWO_SCALE_WHY + ", as the template's mass_kg row asks"),
}
RULER_M = 0.002
AROUND_M = 0.005
SCALE_KG = 0.001
# (c) A dimension read off the plate's CAD model (instrument "CAD ..."). The classmate's Onshape model and drawing of
#     the Emo chassis plate (the private course repo (plate CAD is not published here)) give the outline to 0.01 mm; 0.5 mm is an
#     ALLOWANCE for laser-cut tolerance, plate-to-plate variation and modelling, not a measured tolerance. Xiaohui's
#     plate was checked against the CAD by a plane homography on the bottom-view photo (16 features, residual rms
#     0.25 mm; wing depth 34.0 mm on the photo against 34.35 mm in the CAD): photo-check.txt in that folder.
CAD_M = 0.0005
CAD_WHY = "0.5 mm CAD allowance (plate CAD, the private course repo (plate CAD is not published here))"


class Reading:
    """One quantity after the superseding rule: readings in SI units plus the row it came from."""

    def __init__(self, row_name, readings_si, unit, instrument, notes):
        self.row_name = row_name
        self.readings = readings_si
        self.unit = unit
        self.instrument = instrument
        self.notes = notes

    @property
    def value(self):
        return car_model.mean_and_spread(self.readings)[0]

    def uncertainty(self):
        """(uncertainty in SI units, rule text). All the constants are SI, so the row's unit does not matter."""
        base = SUPERSEDING_SUFFIX.sub("", self.row_name)
        if self.instrument.upper().startswith("CAD"):
            # First: an override reason (e.g. review #7 on the 40 mm wing-depth reading) is about a ruler reading.
            single, rule = CAD_M, CAD_WHY
        elif base in UNCERTAINTY_OVERRIDE:
            single, rule = UNCERTAINTY_OVERRIDE[base]
        elif self.unit in ("g", "kg"):
            single, rule = SCALE_KG, "1 g scale rule; instrument: %s" % (self.instrument or "not stated")
        elif "around" in self.notes.lower():
            single, rule = AROUND_M, "5 mm rule: reading given as 'around'"
        else:
            single, rule = RULER_M, "2 mm ruler rule; instrument: %s" % (self.instrument or "not stated")
        if base in AXLE_DATUM_ROWS:
            if single < AXLE_DATUM_M:
                single, rule = AXLE_DATUM_M, AXLE_DATUM_WHY
            else:
                rule += "; above the 3 mm axle-datum floor"
        if len(self.readings) >= 2:
            half_spread = car_model.mean_and_spread(self.readings)[1] / 2.0
            if half_spread > single:
                return half_spread, "half the spread of %d readings" % len(self.readings)
            return single, rule + " (%d readings agree within it)" % len(self.readings)
        return single, rule


def read_csv(text):
    """CSV text -> {quantity: Reading}, with the superseding and SUPERSEDED rules (module docstring)."""
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    out, rank = {}, {}
    for row in csv.DictReader(lines):
        notes = row.get("notes") or ""
        if notes.lstrip().upper().startswith("SUPERSEDED"):
            continue
        unit = (row.get("unit") or "").strip()
        readings = []
        for col in ("reading_1", "reading_2", "reading_3"):
            cell = (row.get(col) or "").strip()
            if not cell:
                continue
            try:
                readings.append(float(cell))
            except ValueError:
                readings = []
                break
        if not readings or unit not in TO_SI:
            continue
        name = row["quantity"].strip()
        base = SUPERSEDING_SUFFIX.sub("", name)
        this_rank = 0 if base == name else 1
        if this_rank >= rank.get(base, -1):
            si = [r * TO_SI[unit] for r in readings]
            out[base] = Reading(name, si, unit, (row.get("instrument") or "").strip(), notes)
            rank[base] = this_rank
    return out


def read_text_rows(text):
    """CSV text -> {quantity: (row name, reading_1 text)} for the rows whose unit is "text", with the same
    superseding and SUPERSEDED rules as read_csv. Only TEXT_KEYS are written to car.json."""
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    out, rank = {}, {}
    for row in csv.DictReader(lines):
        if (row.get("notes") or "").lstrip().upper().startswith("SUPERSEDED"):
            continue
        cell = (row.get("reading_1") or "").strip()
        if (row.get("unit") or "").strip() != "text" or not cell:
            continue
        name = row["quantity"].strip()
        base = SUPERSEDING_SUFFIX.sub("", name)
        this_rank = 0 if base == name else 1
        if this_rank >= rank.get(base, -1):
            out[base], rank[base] = (name, cell), this_rank
    return out


def clean(x, ndigits=6):
    """Round to 1 micrometre (or 1 mg) to drop float noise; +0.0 turns -0.0 into 0.0."""
    return round(x, ndigits) + 0.0


def build(text, csv_name, updated, measured, evidence_dir="evidence/M1/M1.T9"):
    """Return (car.json dict, report lines). `text` is the CSV, `measured` the bm.car/1 `measured` block."""
    rows = read_csv(text)
    raw_ev = "%s/%s" % (evidence_dir, csv_name)
    der_ev = "%s/derived.txt" % evidence_dir
    values, report, omitted = {}, [], []

    def entry(value, unit, source, evidence, uncertainty):
        return {
            "value": value,
            "unit": unit,
            "status": "measured",
            "source": source,
            "evidence": evidence,
            "updated": updated,
            "uncertainty": None if uncertainty is None else clean(uncertainty, 4),
        }

    def row(key):
        if key in rows:
            return rows[key]
        name = ROW_FOR_KEY.get(key)
        return rows.get(name) if name else None

    def need(name):
        if name not in rows:
            raise KeyError("the CSV has no usable row %s" % name)
        return rows[name]

    # ---- raw keys
    found = {}
    for key in RAW_KEYS:
        r = row(key)
        if r is None:
            omitted.append(key)
            continue
        u, rule = r.uncertainty()
        found[key] = (r.value, u)
        values[key] = entry(clean(r.value), SI_UNIT[r.unit], "M1.T9 measurements.csv %s" % r.row_name, raw_ev, u)
        report.append("%-22s %10.6f %-2s +- %.4f  row %s (%s)" % (key, r.value, SI_UNIT[r.unit], u, r.row_name, rule))

    # ---- wheel diameter: roll-out if both wheels were rolled out, else the direct reading (labelled as such)
    if "rollout_left_m" in found and "rollout_right_m" in found:
        diam = {}
        for side in ("left", "right"):
            d = car_model.effective_diameter(found["rollout_%s_m" % side][0], ROLLOUT_REVS)
            u = found["rollout_%s_m" % side][1] / (ROLLOUT_REVS * math.pi)
            diam[side] = (d, u)
            values["wheel_diameter_%s_m" % side] = entry(clean(d), "m", "M1.T9 (derived)", der_ev, u)
            report.append("%-22s %10.6f m  +- %.4f  rollout_%s_m / (5 pi)" % ("wheel_diameter_%s_m" % side, d, u, side))
        d = (diam["left"][0] + diam["right"][0]) / 2.0
        u = car_model.rss(diam["left"][1] / 2.0, diam["right"][1] / 2.0)
        values["wheel_diameter_m"] = entry(clean(d), "m", "M1.T9 (derived)", der_ev, u)
        report.append("%-22s %10.6f m  +- %.4f  mean of the two wheels" % ("wheel_diameter_m", d, u))
    elif "W1_tyre_diameter_direct" in rows:
        r = rows["W1_tyre_diameter_direct"]
        u, rule = r.uncertainty()
        values["wheel_diameter_m"] = entry(
            clean(r.value), "m",
            "M1.T9 measurements.csv W1_tyre_diameter_direct (direct unloaded tyre diameter; NOT a roll-out)",
            raw_ev, u,
        )
        report.append("%-22s %10.6f m  +- %.4f  row W1_tyre_diameter_direct (%s); DIRECT, not a 5-rev roll-out"
                      % ("wheel_diameter_m", r.value, u, rule))
        omitted += ["wheel_diameter_left_m", "wheel_diameter_right_m"]
    else:
        omitted += ["wheel_diameter_m", "wheel_diameter_left_m", "wheel_diameter_right_m"]

    # ---- IMU height above the AXLE (M1.T9 step 3: position from the axle midpoint; module docstring "Heights")
    if "imu_z_m" not in values and IMU_TOP_ROW in rows and "wheel_diameter_m" in values:
        top = rows[IMU_TOP_ROW]
        u_top, rule = top.uncertainty()
        d_w, u_dw = values["wheel_diameter_m"]["value"], values["wheel_diameter_m"]["uncertainty"]
        z, u = top.value - d_w / 2.0, car_model.rss(u_top, u_dw / 2.0)
        values["imu_z_m"] = entry(
            clean(z), "m",
            "M1.T9 (derived): measurements.csv %s (board top above the floor) - wheel_diameter_m / 2 = board top "
            "above the axle midpoint" % top.row_name,
            der_ev, u,
        )
        omitted.remove("imu_z_m")
        report.append("%-22s %10.6f m  +- %.4f  row %s (%s) - wheel_diameter_m / 2; board top above the AXLE"
                      % ("imu_z_m", z, u, top.row_name, rule))

    # ---- track width
    if "track_outer_m" in found and "track_inner_m" in found:
        (o, uo), (i, ui) = found["track_outer_m"], found["track_inner_m"]
        tw, u = car_model.track_width(o, i), car_model.rss(uo / 2.0, ui / 2.0)
        values["track_width_m"] = entry(clean(tw), "m", "M1.T9 (derived)", der_ev, u)
        report.append("%-22s %10.6f m  +- %.4f  (track_outer_m + track_inner_m) / 2" % ("track_width_m", tw, u))
    else:
        omitted.append("track_width_m")

    # ---- chassis_*: the MAIN BODY without the drive wheels and without the camera stand. M1.T9 step 3 asks for the
    # whole car's bounding box; this is a recorded deviation for Xiaohui to accept (evidence/M1/M1.T9/README.md).
    if "front_overhang_m" in found and "rear_overhang_m" in found:
        (f, uf), (b, ub) = found["front_overhang_m"], found["rear_overhang_m"]
        values["chassis_length_m"] = entry(clean(f + b), "m", "M1.T9 (derived)", der_ev, car_model.rss(uf, ub))
        report.append("%-22s %10.6f m  +- %.4f  front_overhang_m + rear_overhang_m"
                      % ("chassis_length_m", f + b, car_model.rss(uf, ub)))
    else:
        omitted.append("chassis_length_m")
    if "chassis_width_m" not in found:
        omitted.append("chassis_width_m")
    if "B10_battery_holder_top_h" in rows and "B9_lowest_body_h" in rows:
        top, low = rows["B10_battery_holder_top_h"], rows["B9_lowest_body_h"]
        h, u = top.value - low.value, car_model.rss(top.uncertainty()[0], low.uncertainty()[0])
        values["chassis_height_m"] = entry(clean(h), "m", "M1.T9 (derived)", der_ev, u)
        report.append("%-22s %10.6f m  +- %.4f  B10_battery_holder_top_h - B9_lowest_body_h (main body; the camera"
                      " stand is excluded)" % ("chassis_height_m", h, u))
    else:
        omitted.append("chassis_height_m")

    # ---- corners (plan view, from the axle midpoint) and the sweep radius
    def need_key(key):
        r = row(key)
        if r is None:
            raise KeyError("the CSV has no usable row %s (or %s)" % (key, ROW_FOR_KEY.get(key, "-")))
        return r

    points = []  # (label, x, y, u_x, u_y, y_assumed): y_assumed = y comes from a width ASSUMED centred on y = 0
    try:
        if "wheel_diameter_m" not in values:
            raise KeyError("wheel_diameter_m")
        d_w, u_dw = values["wheel_diameter_m"]["value"], values["wheel_diameter_m"]["uncertainty"]
        front, rear, w3o = need_key("front_overhang_m"), need_key("rear_overhang_m"), need_key("track_outer_m")
        b1, b2 = need("B1_plate_front_x"), need("B2_plate_rear_x")
        b5n, b5m, b5b = need("B5_plate_width_narrow"), need("B5_plate_width_max"), need("B5b_wing_depth_centre")
        b14 = need("B14_esp32cam_width")
        c2b = need("C2b_caster_front_swung_x")
        for s in (1, -1):
            points.append(("ESP32-CAM front corner (front_overhang_m, +-B14 / 2; y ASSUMES the board is centred)",
                           front.value, s * b14.value / 2, front.uncertainty()[0], b14.uncertainty()[0] / 2, True))
        if FRONT_ARC_ROW in rows and FRONT_CORNER_ROW in rows:
            # The rounded front (CAD outline): the farthest point of the arc + fillet, not the square corner.
            p1, p2 = rows[FRONT_ARC_ROW], rows[FRONT_CORNER_ROW]
            fx, fy = car_model.rounded_front_corner(b1.value, b5n.value / 2, p1.value, p2.value)
            for s in (1, -1):
                points.append(("plate front corner (rounded front: apex at B1, sides +-B5 narrow / 2, front arc %s, "
                               "corner fillets %s; y ASSUMES the plate is centred)" % (p1.row_name, p2.row_name),
                               fx, s * fy, b1.uncertainty()[0], b5n.uncertainty()[0] / 2, True))
        else:
            for s in (1, -1):
                points.append(("plate front corner (B1, +-B5 narrow / 2; y ASSUMES the strip is centred)",
                               b1.value, s * b5n.value / 2, b1.uncertainty()[0], b5n.uncertainty()[0] / 2, True))
        for sx in (1, -1):
            for sy in (1, -1):
                points.append(("tyre outer corner", sx * d_w / 2, sy * w3o.value / 2, u_dw / 2,
                               w3o.uncertainty()[0] / 2, False))
        for s in (1, -1):
            points.append(("rear wing tip (-B2 + B5b, B5 max / 2)", -b2.value + b5b.value, s * b5m.value / 2,
                           car_model.rss(b2.uncertainty()[0], b5b.uncertainty()[0]), b5m.uncertainty()[0] / 2, False))
        points.append(("rear apex (rear_overhang_m, %s)" % rear.row_name, -rear.value, 0.0, rear.uncertainty()[0],
                       0.0, False))
        points.append(("caster swung fully forward (%s)" % c2b.row_name, c2b.value, 0.0, c2b.uncertainty()[0], 0.0,
                       False))
    except KeyError as exc:
        omitted += ["corners", "sweep_radius_m"]
        report.append("corners and sweep_radius_m omitted: %s" % exc)
    if points:
        corners = [[clean(p[1]), clean(p[2])] for p in points]
        u_xy = max(max(p[3], p[4]) for p in points)
        values["corners"] = entry(
            corners, "m",
            "M1.T9 (derived): plan-view extreme points from the axle midpoint (derived.txt); the ESP32-CAM front "
            "corners and the plate-front corners ASSUME those parts are centred on y = 0 (only their widths were "
            "measured)",
            der_ev, u_xy,
        )
        report.append("corners (x, y) from the axle midpoint, m; uncertainty = the largest coordinate term %.4f m:" % u_xy)
        radius = car_model.sweep_radius([(p[1], p[2]) for p in points])
        upper, farthest = 0.0, None
        for label, x, y, ux, uy, assumed in points:
            r = math.hypot(x, y)
            ur = car_model.rss(x / r * ux, y / r * uy) if r > 0 else max(ux, uy)
            upper = max(upper, r + ur)
            if farthest is None and r == radius:
                farthest = (label, assumed)
            report.append("    (%8.4f, %8.4f)  r = %.4f +- %.4f  %s" % (x, y, r, ur, label))
        u_sweep = upper - radius
        if farthest[1]:
            sweep_src = ("M1.T9 (derived): the largest distance over corners, reached at the %s, so sweep_radius_m "
                         "depends on that centring assumption" % farthest[0].split(" (")[0])
        else:
            sweep_src = ("M1.T9 (derived): the largest distance over corners, reached at the %s, which uses no "
                         "centring assumption" % farthest[0].split(" (")[0])
        values["sweep_radius_m"] = entry(clean(radius), "m", sweep_src, der_ev, u_sweep)
        report.append("%-22s %10.6f m  +- %.4f  max hypot over corners, at the %s; uncertainty = max(r + u_r) - max(r)"
                      % ("sweep_radius_m", radius, u_sweep, farthest[0]))

    # ---- text keys (imu_axes: which way the BNO055's printed axes point relative to the car)
    texts = read_text_rows(text)
    for key in TEXT_KEYS:
        if key in texts:
            name, value = texts[key]
            values[key] = entry(value, "text", "M1.T9 measurements.csv %s" % name, raw_ev, None)
            report.append("%-22s %r  row %s" % (key, value, name))
        else:
            omitted.append(key)

    omitted += ["counts_per_rev_left", "counts_per_rev_right", "ticks_per_wheel_rev"]
    doc = {"schema": "bm.car/1", "values": values, "measured": measured}
    return doc, report, sorted(set(omitted))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("csv", type=Path)
    ap.add_argument("--measured", type=Path, required=True, help="JSON file holding the bm.car/1 measured block")
    ap.add_argument("--updated", required=True, help="YYYY-MM-DD written into every value's 'updated'")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    measured = json.loads(args.measured.read_text(encoding="utf-8"))
    doc, report, omitted = build(args.csv.read_text(encoding="utf-8"), args.csv.name, args.updated, measured)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("write_car_json.py: %s -> %s" % (args.csv.name, args.out.name))
    print("\n".join(report))
    print("omitted (no reading in the CSV): %s" % ", ".join(omitted))
    try:
        from beaconmind.schemas import validate
    except ImportError:
        print("schema validation pending: beaconmind.schemas is not importable here")
        return 0
    errors = validate("car", doc)
    print("bm.car-1 validation: %s" % ("OK" if not errors else "; ".join(errors)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
