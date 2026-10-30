"""Tests for beaconmind.car_model and course-project/tools/write_car_json.py (plan M1.T9 step 5 test list).

The two hand-turn encoder tests of the plan (test_handturn_parse_counters, test_handturn_summary) are not here:
the encoder part of M1.T9 was postponed, so tools/encoder_handturn.py does not exist yet.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-10-10: wrote these tests; later the same day, after a review,
added the imu_z_m (axle-relative), imu_axes, corner-assumption and template tests; after a second review, added the
row-unit tests (m / kg rows), the axle-datum asserts and the uncertainty comparison of the template test;
2026-10-16: added the plate-CAD tests (rounded front, CAD rows) and made test_configs_car_json_is_the_writer_output
follow the CSV and date that car.json names (it was tied to the 2026-10-10 file).
AI-assisted: Claude Opus 5.5 (xhigh effort) via Cursor, 2026-10-29: followed the writer's generic corner label
("front-most corner"; it was "ESP32-CAM front corner") in test_writer_rows_rules_and_derived; the checks are the same.
After a review the same day: followed the corners / sweep source texts that state both assumptions, and added
test_row_specific_uncertainty_applies_to_the_exact_row_name_only (ROW_UNCERTAINTY).
"""
import csv
import importlib.util
import io
import json
import math

import pytest

from beaconmind import car_model, course_root
from beaconmind.schemas import validate


def _writer():
    path = course_root() / "tools" / "write_car_json.py"
    spec = importlib.util.spec_from_file_location("write_car_json", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MEASURED = {"by": "test", "date": "2026-10-10", "instruments": ["ruler"], "notes": "synthetic"}

# A small CSV in the 2026-10-10 row names: every row the writer reads, plus the traps it must handle.
SYNTHETIC = "\n".join(
    [
        "# synthetic test CSV",
        "quantity,reading_1,reading_2,reading_3,unit,instrument,notes",
        "W1_tyre_diameter_direct,66,,,mm,ruler,direct",
        "W2_tyre_width,26,,,mm,ruler,x",
        "W3_track_outer,180,,,mm,ruler,x",
        "W3_track_inner,130,,,mm,ruler,x",
        "C1_caster_wheel_diameter,24,,,mm,ruler,x",
        "C2_caster_contact_x,90,,,mm,ruler,'around 9 cm'",
        "C2b_caster_front_swung_x,120,,,mm,ruler,first",
        "C2b_caster_front_swung_x_remeasure,125,,,mm,ruler,second",
        "B1_plate_front_x,120,,,mm,ruler,x",
        "B2_plate_rear_x,70,,,mm,ruler,x",
        "B3_front_most_x,128,,,mm,ruler,x",
        "B4_rear_most_x,70,,,mm,ruler,x",
        "B5_plate_width_max,140,,,mm,ruler,x",
        "B5_plate_width_narrow,90,,,mm,ruler,x",
        "B5b_wing_depth_centre,35,,,mm,ruler,x",
        'B5c_wing_width_20mm_in,151,,,mm,ruler,"SUPERSEDED - not an input"',
        "B9_lowest_body_h,28,,,mm,ruler,x",
        "B10_battery_holder_top_h,64,,,mm,ruler,x",
        "B14_esp32cam_width,20,,,mm,ruler,x",
        "S3_lens_x,110,,,mm,ruler,x",
        "S3_lens_y,0,,,mm,ruler,x",
        "S3_lens_centre_h,70,,,mm,ruler,x",
        "S1_imu_board_centre_x,-60,,,mm,ruler,x",
        "S1_imu_board_centre_y,-20,,,mm,ruler,sign error",
        "S1_imu_board_centre_y_corrected,20,,,mm,observation,fixed",
        "S1_imu_board_top_h,58,,,mm,ruler,x",
        "K1_total_mass,500,,,g,scales,x",
        "C0_caster_type,swivel,,,text,photo,a text row",
        "imu_axes,x arrow toward the camera; y arrow to the robot left,,,text,photo,synthetic",
    ]
)


def test_effective_diameter():
    assert abs(car_model.effective_diameter(1.021, 5) - 0.06500) <= 1e-4


def test_track_width_mean():
    assert abs(car_model.track_width(0.180, 0.130) - 0.155) <= 1e-12


def test_sweep_radius_max():
    assert abs(car_model.sweep_radius([(0.1, 0.05), (-0.12, 0.09)]) - 0.15) <= 1e-12


def test_counts_per_rev():
    assert car_model.counts_per_rev(21600, 21600, 10) == 4320.0


def test_mean_and_spread():
    mean, spread = car_model.mean_and_spread([1.0, 1.2, 1.1])
    assert abs(mean - 1.1) <= 1e-12 and abs(spread - 0.2) <= 1e-12


def test_car_json_validates():
    doc, _, _ = _writer().build(SYNTHETIC, "synthetic.csv", "2026-10-10", MEASURED)
    assert validate("car", doc) == []


def test_writer_rows_rules_and_derived():
    """Superseding rows win, SUPERSEDED rows are ignored, units become SI, uncertainties follow the stated rules."""
    doc, _, omitted = _writer().build(SYNTHETIC, "synthetic.csv", "2026-10-10", MEASURED)
    v = doc["values"]
    assert v["imu_y_m"]["value"] == 0.02 and "corrected" in v["imu_y_m"]["source"]
    assert v["mass_kg"]["value"] == 0.5 and v["mass_kg"]["unit"] == "kg"
    assert v["mass_kg"]["uncertainty"] == round(math.sqrt(2) * 0.001, 4)
    assert v["caster_x_m"]["uncertainty"] == 0.005  # notes say 'around'
    assert v["wheel_width_m"]["uncertainty"] == 0.002  # single ruler reading
    # The 3 mm axle-datum floor (review #15) holds for every x from the axle line, under either naming scheme:
    assert v["rear_overhang_m"]["uncertainty"] == 0.003  # B4
    assert v["front_overhang_m"]["uncertainty"] == 0.003  # B3 (axle line to the front-most point)
    assert v["imu_x_m"]["uncertainty"] == 0.003  # S1_imu_board_centre_x (behind the axle line)
    assert v["lens_y_m"]["uncertainty"] == 0.002  # y is from the centre line: no axle-datum floor
    assert v["chassis_length_m"]["uncertainty"] == round(math.hypot(0.003, 0.003), 4)
    assert next(c for c in v["corners"]["value"] if c[1] == 0.045)[0] == 0.12  # B1 front corner, x from B1
    assert v["track_width_m"]["value"] == 0.155 and v["track_width_m"]["source"] == "M1.T9 (derived)"
    assert v["chassis_height_m"]["value"] == 0.036 and v["chassis_length_m"]["value"] == 0.198
    # The direct diameter fills wheel_diameter_m, says so, and no roll-out key is invented.
    assert v["wheel_diameter_m"]["value"] == 0.066 and "NOT a roll-out" in v["wheel_diameter_m"]["source"]
    for key in ("rollout_left_m", "rollout_right_m", "wheel_diameter_left_m", "wheel_diameter_right_m",
                "counts_per_rev_left", "counts_per_rev_right", "ticks_per_wheel_rev"):
        assert key not in v and key in omitted
    # The later C2b re-measure (125) is the swung-forward caster corner; the front-most corner (128, 10) is farthest.
    assert [0.125, 0.0] in v["corners"]["value"]
    assert abs(v["sweep_radius_m"]["value"] - math.hypot(0.128, 0.010)) <= 1e-6
    assert all(e["status"] == "measured" for e in v.values())
    # imu_z_m is the board top above the AXLE (M1.T9 step 3): S1_imu_board_top_h 58 mm - 66 mm / 2 = 25 mm.
    assert v["imu_z_m"]["value"] == 0.025 and "above the axle" in v["imu_z_m"]["source"]
    assert v["imu_z_m"]["uncertainty"] == round(math.hypot(0.002, 0.001), 4) and "imu_z_m" not in omitted
    assert v["lens_z_m"]["value"] == 0.07  # the lens stays a height above the FLOOR (M1.T7 step 8)
    # The assumptions behind the front-most / plate-front corners (width, centring) are stated, and the farthest corner
    # names them.
    assert "ASSUME" in v["corners"]["source"] and "as wide as the ESP32-CAM board" in v["corners"]["source"]
    assert "front-most corner" in v["sweep_radius_m"]["source"]
    assert "depends on what that corner's y assumes" in v["sweep_radius_m"]["source"]
    # The imu_axes text row becomes a string value; other text rows (C0_caster_type) are not written.
    assert v["imu_axes"]["value"] == "x arrow toward the camera; y arrow to the robot left"
    assert v["imu_axes"]["unit"] == "text" and v["imu_axes"]["uncertainty"] is None and "imu_axes" not in omitted
    assert "C0_caster_type" not in v


def test_row_specific_uncertainty_applies_to_the_exact_row_name_only():
    """ROW_UNCERTAINTY (2026-10-29) is keyed by the exact row name: B3_front_most_x_remeasure gets rss(3 mm, 5 mm)
    with its stated reason (even with 'around' in its notes), while the base-name row B3_front_most_x and another
    superseding name, B3_front_most_x_corrected, keep the 3 mm axle-datum floor."""
    writer = _writer()
    exact = SYNTHETIC + "\nB3_front_most_x_remeasure,168,,,mm,not stated,a stick-out of around 4 cm"
    rows = writer.read_csv(exact)
    assert rows["B3_front_most_x"].row_name == "B3_front_most_x_remeasure"
    u, rule = rows["B3_front_most_x"].uncertainty()
    assert u == car_model.rss(0.003, 0.005) and rule == writer.ROW_UNCERTAINTY["B3_front_most_x_remeasure"][1]
    v = writer.build(exact, "synthetic.csv", "2026-10-10", MEASURED)[0]["values"]
    assert v["front_overhang_m"]["value"] == 0.168 and v["front_overhang_m"]["uncertainty"] == 0.0058
    assert v["chassis_length_m"]["uncertainty"] == round(car_model.rss(car_model.rss(0.003, 0.005), 0.003), 4)
    # The base-name row (the fixture's B3, 128 mm) and a differently named later row keep the ordinary rules.
    assert writer.read_csv(SYNTHETIC)["B3_front_most_x"].uncertainty()[0] == 0.003
    other = writer.read_csv(SYNTHETIC + "\nB3_front_most_x_corrected,168,,,mm,not stated,x")["B3_front_most_x"]
    assert other.row_name == "B3_front_most_x_corrected" and other.uncertainty()[0] == 0.003


def _in_m_and_kg(text, only=None):
    """The same CSV with mm rows rewritten in m and g rows in kg (readings / 1000); `only` limits it to those rows."""
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    body = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    for row in csv.reader(body):
        if row[0] != "quantity" and row[4] in ("mm", "g") and (only is None or row[0] in only):
            row = [row[0]] + [repr(float(c) / 1000) if c.strip() else c for c in row[1:4]] \
                + [{"mm": "m", "g": "kg"}[row[4]]] + row[5:]
        w.writerow(row)
    return out.getvalue()


def test_override_uncertainty_does_not_depend_on_the_row_unit():
    """Review fix: the override and floor constants are SI. B1/B4 typed in m and K1 in kg keep 0.003 m and 0.0014 kg
    (before the fix they came out as 3.0 m and 1.4142 kg, because the mm/g constants were multiplied by the m/kg
    factor 1.0)."""
    writer = _writer()
    text = _in_m_and_kg(SYNTHETIC, only={"B1_plate_front_x", "B4_rear_most_x", "K1_total_mass"})
    assert "B1_plate_front_x,0.12,,,m" in text and "K1_total_mass,0.5,,,kg" in text
    assert writer.read_csv(text)["B1_plate_front_x"].uncertainty()[0] == 0.003
    v = writer.build(text, "synthetic.csv", "2026-10-10", MEASURED)[0]["values"]
    assert v["rear_overhang_m"]["uncertainty"] == 0.003
    assert v["mass_kg"]["uncertainty"] == 0.0014 and v["mass_kg"]["value"] == 0.5
    assert v["corners"]["uncertainty"] <= 0.005 and v["sweep_radius_m"]["uncertainty"] < 0.01


def test_whole_csv_in_m_and_kg_builds_the_same_car_json():
    """Every row typed in m / kg instead of mm / g gives the same values (within 1e-12 m) and the same uncertainties."""
    writer = _writer()
    a = writer.build(SYNTHETIC, "synthetic.csv", "2026-10-10", MEASURED)[0]["values"]
    b = writer.build(_in_m_and_kg(SYNTHETIC), "synthetic.csv", "2026-10-10", MEASURED)[0]["values"]
    assert sorted(a) == sorted(b)
    for key in a:
        assert b[key]["uncertainty"] == a[key]["uncertainty"], key
        if key == "corners":
            assert b[key]["value"] == a[key]["value"]
        elif isinstance(a[key]["value"], str):
            assert b[key]["value"] == a[key]["value"]
        else:
            assert abs(b[key]["value"] - a[key]["value"]) <= 1e-12, key


def test_writer_imu_z_row_is_used_as_is():
    """A plan-key imu_z_m row (already above the axle) is written unchanged; S1_imu_board_top_h is then not used."""
    text = SYNTHETIC + "\nimu_z_m,24,,,mm,ruler,board top above the axle"
    v = _writer().build(text, "synthetic.csv", "2026-10-10", MEASURED)[0]["values"]
    assert v["imu_z_m"]["value"] == 0.024 and v["imu_z_m"]["source"] == "M1.T9 measurements.csv imu_z_m"


def test_writer_rollout_branch():
    """With both roll-outs present, the diameters are derived per wheel (distance / (5 pi)) and averaged."""
    text = SYNTHETIC.replace(
        "W1_tyre_diameter_direct,66,,,mm,ruler,direct",
        "rollout_left_m,1.021,1.022,1.020,m,tape,x\nrollout_right_m,1.0367,,,m,tape,x\nW1_tyre_diameter_direct,66,,,mm,ruler,direct",
    )
    doc, _, omitted = _writer().build(text, "synthetic.csv", "2026-10-10", MEASURED)
    v = doc["values"]
    assert abs(v["wheel_diameter_left_m"]["value"] - 1.021 / (5 * math.pi)) <= 1e-6
    assert abs(v["wheel_diameter_right_m"]["value"] - 1.0367 / (5 * math.pi)) <= 1e-6
    mean = (1.021 + 1.0367) / 2 / (5 * math.pi)
    assert abs(v["wheel_diameter_m"]["value"] - mean) <= 1e-6 and v["wheel_diameter_m"]["source"] == "M1.T9 (derived)"
    assert v["rollout_left_m"]["uncertainty"] == 0.002  # three readings 1 mm apart: the 2 mm rule is larger
    assert "wheel_diameter_left_m" not in omitted


def test_configs_car_json_is_the_writer_output():
    """configs/car.json equals what the writer builds from the M1.T9 evidence CSV (no hand edits) and validates.

    The CSV is the one car.json's values name in their "evidence" fields (exactly one), and the date is the one in their
    "updated" fields (exactly one), so a rebuild from a new evidence CSV needs no edit here; a hand edit of any value,
    uncertainty, source, date or the measured block still fails the equality."""
    root = course_root()
    car_path = root / "configs" / "car.json"
    ev = root / "evidence" / "M1" / "M1.T9"
    if not car_path.is_file():
        pytest.skip("configs/car.json (M1.T9) not written yet")
    car = json.loads(car_path.read_text(encoding="utf-8"))
    assert validate("car", car) == []
    named = {e["evidence"] for e in car["values"].values() if str(e.get("evidence", "")).endswith(".csv")}
    dates = {e["updated"] for e in car["values"].values()}
    assert len(named) == 1 and len(dates) == 1, (named, dates)
    csv_path = root / named.pop()
    assert csv_path.parent == ev, csv_path
    measured = json.loads((ev / "measured.json").read_text(encoding="utf-8"))
    doc, _, _ = _writer().build(csv_path.read_text(encoding="utf-8"), csv_path.name, dates.pop(), measured)
    assert car == doc


# ---------------------------------------------------------------- the plate CAD (2026-10-16)

# The Emo chassis plate CAD (the private course repo (plate CAD is not published here)), in mm: front arc R135.14, corner fillets R8, sides
# at +-50; with the apex at 130.49 mm the STEP outline puts the fillet centre at x = 26.86 + 88.492 mm and the
# fillet/arc tangent point at (26.86 + 96.043, 44.643) mm (step-outline.txt: STEP origin 26.86 mm behind the axle line).
CAD_FRONT = (0.13049, 0.050, 0.13514, 0.008)


def _sampled_front(front_x, half_width, arc_radius, corner_radius, n=20000):
    """Dense samples of the rounded front's upper half (fillet, then main arc), for an independent maximum."""
    g = car_model.rounded_front(front_x, half_width, arc_radius, corner_radius)
    (xf, yf), cx = g["fillet_centre"], g["arc_centre_x"]
    a0 = math.atan2(g["arc_tangent"][1] - yf, g["arc_tangent"][0] - xf)
    b0 = math.atan2(g["arc_tangent"][1], g["arc_tangent"][0] - cx)
    pts = [(xf + corner_radius * math.cos(a0 + (math.pi / 2 - a0) * k / n),
            yf + corner_radius * math.sin(a0 + (math.pi / 2 - a0) * k / n)) for k in range(n + 1)]
    pts += [(cx + arc_radius * math.cos(b0 * k / n), arc_radius * math.sin(b0 * k / n)) for k in range(n + 1)]
    return pts


def test_rounded_front_matches_the_step_outline():
    g = car_model.rounded_front(*CAD_FRONT)
    assert abs(g["arc_centre_x"] - (0.13049 - 0.13514)) <= 1e-12
    assert abs(g["fillet_centre"][0] - (0.02686 + 0.088492)) <= 2e-6 and abs(g["fillet_centre"][1] - 0.042) <= 1e-12
    assert abs(g["arc_tangent"][0] - (0.02686 + 0.096043)) <= 2e-6 and abs(g["arc_tangent"][1] - 0.044643) <= 2e-6
    assert g["side_tangent"] == (g["fillet_centre"][0], 0.05)
    # The fillet touches the main arc: its centre is R - r from the arc centre.
    assert abs(math.hypot(g["fillet_centre"][0] - g["arc_centre_x"], g["fillet_centre"][1]) - (0.13514 - 0.008)) <= 1e-12


@pytest.mark.parametrize("front", [CAD_FRONT, (0.20, 0.05, 0.10, 0.01), (0.10, 0.05, 0.30, 0.02), (0.13, 0.05, 0.051, 0.008)])
def test_rounded_front_corner_is_the_farthest_outline_point(front):
    """The analytic candidate set gives the same farthest point as dense sampling of the outline (several shapes:
    the plate CAD, an arc centre ahead of the axle, a nearly straight front, a nearly half-circle front)."""
    p = car_model.rounded_front_corner(*front)
    best = max(_sampled_front(*front), key=lambda q: math.hypot(*q))
    assert abs(math.hypot(*p) - math.hypot(*best)) <= 1e-9 and math.dist(p, best) <= 1e-5


def test_rounded_front_corner_plate_cad_value():
    x, y = car_model.rounded_front_corner(*CAD_FRONT)
    assert abs(x - 0.122870) <= 1e-6 and abs(y - 0.044737) <= 1e-6 and abs(math.hypot(x, y) - 0.130761) <= 1e-6


def test_rounded_front_rejects_impossible_radii():
    for bad in ((0.13, 0.05, 0.13514, 0.0), (0.13, 0.05, 0.04, 0.008), (0.13, 0.05, 0.13514, 0.06)):
        with pytest.raises(ValueError):
            car_model.rounded_front(*bad)


CAD_ROWS = "\n".join([
    "B5b_wing_depth_centre_corrected,30,,,mm,CAD: synthetic plate model,x",
    "B5_plate_width_max_corrected,138,,,mm,CAD: synthetic plate model,x",
    "P1_plate_front_arc_radius,135.14,,,mm,CAD: synthetic plate model,x",
    "P2_plate_front_corner_radius,8,,,mm,CAD: synthetic plate model,x",
])


def test_writer_cad_rows():
    """CAD rows supersede the ruler rows, get the 0.5 mm CAD allowance (before the B5b review override), and the P1/P2
    rows turn the square plate-front corners into the farthest points of the rounded front."""
    writer = _writer()
    rows = writer.read_csv(SYNTHETIC + "\n" + CAD_ROWS)
    assert rows["B5b_wing_depth_centre"].row_name == "B5b_wing_depth_centre_corrected"
    assert rows["B5b_wing_depth_centre"].uncertainty()[0] == 0.0005  # not the 4 mm review #7 override
    assert writer.read_csv(SYNTHETIC)["B5b_wing_depth_centre"].uncertainty()[0] == 0.004  # the ruler reading keeps it
    v = writer.build(SYNTHETIC + "\n" + CAD_ROWS, "synthetic.csv", "2026-10-10", MEASURED)[0]["values"]
    assert v["chassis_width_m"]["value"] == 0.138 and v["chassis_width_m"]["uncertainty"] == 0.0005
    # Synthetic plate: apex B1 = 120 mm, strip 90 mm wide.
    fx, fy = car_model.rounded_front_corner(0.120, 0.045, 0.13514, 0.008)
    corners = v["corners"]["value"]
    assert [round(fx, 6), round(fy, 6)] in corners and [round(fx, 6), round(-fy, 6)] in corners
    assert [0.12, 0.045] not in corners  # the square corner is gone
    assert [-0.04, 0.069] in corners  # rear wing tip (-B2 + CAD depth, CAD width / 2) = (-0.070 + 0.030, 0.069)
    assert len(corners) == len(writer.build(SYNTHETIC, "s.csv", "2026-10-10", MEASURED)[0]["values"]["corners"]["value"])
    # Only one of the two outline rows: square corners, as without either.
    half = SYNTHETIC + "\n" + CAD_ROWS.splitlines()[2]
    assert [0.12, 0.045] in writer.build(half, "s.csv", "2026-10-10", MEASURED)[0]["values"]["corners"]["value"]


# ---------------------------------------------------------------- the M1.T9 step 2 template

TEMPLATE_COLUMNS = ["quantity", "reading_1", "reading_2", "reading_3", "unit", "instrument", "notes"]


def _template():
    path = course_root() / "tools" / "car_measurements_template.csv"
    text = path.read_text(encoding="utf-8")
    body = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    comments = "\n".join(ln for ln in text.splitlines() if ln.startswith("#"))
    return text, list(csv.DictReader(body)), comments, body[0]


def test_template_lists_every_quantity():
    """One blank row per step-3 quantity the writer reads (plan key names) and per extra row it reads; the
    step-3 quantities it derives are named in the header comment; no instruction text triggers the 'around' rule."""
    writer = _writer()
    _, rows, comments, header = _template()
    assert header.split(",") == TEMPLATE_COLUMNS
    names = [r["quantity"] for r in rows]
    assert len(names) == len(set(names))
    expected = writer.RAW_KEYS + writer.TEXT_KEYS + list(writer.EXTRA_ROWS)
    assert sorted(names) == sorted(expected)
    for key in writer.DERIVED_STEP3_KEYS:
        assert key in comments, key
    for r in rows:
        assert not any((r[c] or "").strip() for c in ("reading_1", "reading_2", "reading_3")), r["quantity"]
        assert "around" not in (r["notes"] or "").lower(), r["quantity"]
        assert r["unit"] in ("mm", "g", "text"), r["quantity"]


def test_template_blank_builds_nothing():
    """The blank template goes through the writer without error and gives no value at all (nothing invented)."""
    writer = _writer()
    text = _template()[0]
    doc, _, omitted = writer.build(text, "template.csv", "2026-10-10", MEASURED)
    assert doc["values"] == {}
    assert set(writer.RAW_KEYS + writer.TEXT_KEYS + writer.DERIVED_STEP3_KEYS) <= set(omitted)


# Uncertainties that legitimately differ between the 2026-10-10 CSV and the same readings typed into the template:
# the 'around' rule reads the NOTES, and the 2026-10-10 notes say "around 10 cm" (C2), "around 12 cm" (S3_lens_x) and
# "around 14 cm" (C2b remeasure2) while the template's notes are instructions without that word. Those rows then get
# the 3 mm axle-datum floor instead of 5 mm. (evidence build, filled template), in m:
TEMPLATE_UNCERTAINTY_DIFFERENCES = {
    "caster_x_m": (0.005, 0.003),
    "lens_x_m": (0.005, 0.003),
    # Evidence: the swung-forward caster (0.140 +- 0.005) gives the largest r + u_r = 0.145, so 0.145 - 0.140218.
    # Template: that point is 0.140 +- 0.003, so the plate-front corner's 0.140218 + 0.0028 is the largest.
    "sweep_radius_m": (0.0048, 0.0028),
}


def test_template_filled_under_plan_keys_matches_the_evidence_build():
    """The 2026-10-10 readings typed into the template's plan-key rows (in m and kg) give the same car.json values as
    the 2026-10-10 CSV with its own row names, so the writer reads a filled template completely. The uncertainties
    are equal too (the axle-datum floor and the two-scale mass apply under both names), except the three stated in
    TEMPLATE_UNCERTAINTY_DIFFERENCES, which come from the word 'around' in the 2026-10-10 notes."""
    writer = _writer()
    ev = course_root() / "evidence" / "M1" / "M1.T9" / "measurements-xiaohui-chen-2026-10-10.csv"
    if not ev.is_file():
        pytest.skip("the M1.T9 evidence CSV is not present")
    ev_text = ev.read_text(encoding="utf-8")
    readings = writer.read_csv(ev_text)
    _, rows, _, _ = _template()
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(TEMPLATE_COLUMNS)
    for r in rows:
        src = readings.get(r["quantity"]) or readings.get(writer.ROW_FOR_KEY.get(r["quantity"], ""))
        if src is None:
            w.writerow([r[c] for c in TEMPLATE_COLUMNS])
            continue
        cells = [repr(x) for x in src.readings] + [""] * (3 - len(src.readings))
        w.writerow([r["quantity"]] + cells + [writer.SI_UNIT[src.unit], r["instrument"], r["notes"]])
    filled = writer.build(out.getvalue(), "filled.csv", "2026-10-10", MEASURED)[0]["values"]
    expected = writer.build(ev_text, ev.name, "2026-10-10", MEASURED)[0]["values"]
    assert sorted(filled) == sorted(expected)
    for key, e in expected.items():
        if key == "corners":
            assert filled[key]["value"] == e["value"]
        else:
            assert abs(filled[key]["value"] - e["value"]) <= 1e-12, key
        if key in TEMPLATE_UNCERTAINTY_DIFFERENCES:
            assert (e["uncertainty"], filled[key]["uncertainty"]) == TEMPLATE_UNCERTAINTY_DIFFERENCES[key], key
        else:
            assert filled[key]["uncertainty"] == e["uncertainty"], key
