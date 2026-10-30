"""Geometry port tests.

The byte-identical assignment solution l2_geometry.py is not in this public repo.
It stays in the private course repo at
assignments/assignment4/system-prompt/tools/l2_geometry.py.
Tests that compare against that file skip when it is absent.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the reference-match, example and gate tests.
AI-assisted: Grok 4.7 via Cursor, 2026-10-29: skip the unpublished reference file.
"""
import hashlib
import importlib.util
import json
import math
import random
from pathlib import Path

import pytest

from beaconmind.dv import load_dv
from beaconmind.geometry import (
    compose_odometry,
    exploration_summary,
    fix_pose,
    gate_detection,
    map_point,
    predict_observation,
    update_beacon,
    wrap_deg,
)

# Map entries from assignments/assignment4/system-prompt/tools/fewshot_scenario.py MAP.
B1 = {"x_m": 1.27, "y_m": 0.63, "state": "confirmed", "odo_last_seen_m": 1.25}
B5 = {"x_m": 0.42, "y_m": 1.22, "state": "confirmed", "odo_last_seen_m": 1.00}

REF_DIR = Path(__file__).parent / "fixtures" / "reference"


def _reference():
    # Not published: private course repo
    # assignments/assignment4/system-prompt/tools/l2_geometry.py
    path = REF_DIR / "l2_geometry.py"
    if not path.is_file():
        pytest.skip(
            "l2_geometry.py stays in the private course repo "
            "(assignments/assignment4/system-prompt/tools/l2_geometry.py)"
        )
    spec = importlib.util.spec_from_file_location("l2_geometry_reference", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fewshot():
    return json.loads((REF_DIR / "fewshot-numbers.json").read_text(encoding="utf-8"))


def _assert_close(got, exp, path):
    if isinstance(got, bool) or isinstance(exp, bool):
        assert isinstance(got, bool) and isinstance(exp, bool) and got == exp, (path, got, exp)
        return
    if got is None or exp is None:
        assert got is None and exp is None, (path, got, exp)
        return
    if isinstance(got, (int, float)) and isinstance(exp, (int, float)):
        if isinstance(got, float) and math.isnan(got):
            assert isinstance(exp, float) and math.isnan(exp), (path, got, exp)
            return
        if math.isinf(got) or math.isinf(exp):
            assert got == exp, (path, got, exp)
            return
        assert abs(float(got) - float(exp)) < 1e-9, (path, got, exp)
        return
    if isinstance(got, dict):
        assert isinstance(exp, dict) and set(got) == set(exp), (path, set(got), set(exp))
        for key in got:
            _assert_close(got[key], exp[key], path + "." + str(key))
        return
    if isinstance(got, list):
        assert isinstance(exp, list) and len(got) == len(exp), (path, got, exp)
        for index, (left, right) in enumerate(zip(got, exp)):
            _assert_close(left, right, "%s[%d]" % (path, index))
        return
    assert got == exp, (path, got, exp)


def _round_pose(pose):
    return {
        "x_m": round(pose["x_m"], 2),
        "y_m": round(pose["y_m"], 2),
        "theta_deg": round(pose["theta_deg"], 1),
    }


def _round_gate(row):
    out = {}
    for key, value in row.items():
        if isinstance(value, float):
            out[key] = round(value, 1) if "bearing" in key else round(value, 2)
        else:
            out[key] = value
    return out


def _round_fix(row):
    out = {}
    for key, value in row.items():
        if isinstance(value, float):
            out[key] = round(value, 1) if "deg" in key else round(value, 3)
        else:
            out[key] = value
    return out


def test_vendored_reference_hash():
    recorded = {}
    for line in (REF_DIR / "SOURCES.sha256").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        recorded[name.strip()] = digest
    # l2_geometry.py is not shipped. See _reference().
    assert "l2_geometry.py" not in recorded
    assert set(recorded) == {"fewshot-numbers.json"}
    for name, digest in recorded.items():
        actual = hashlib.sha256((REF_DIR / name).read_bytes()).hexdigest()
        assert actual == digest, name


def test_wrap_deg_edges():
    assert wrap_deg(180) == 180
    assert wrap_deg(-180) == 180
    assert wrap_deg(540) == 180
    assert abs(wrap_deg(-175 - 178) - 7.0) < 1e-9


def test_compose_odometry_heading_90():
    pose = compose_odometry({"x_m": 0.0, "y_m": 0.0, "theta_deg": 90.0}, 0.25, 0.0, 0.0)
    assert abs(pose["x_m"]) < 1e-12
    assert abs(pose["y_m"] - 0.25) < 1e-12
    assert pose["theta_deg"] == 90.0


def test_matches_reference_random():
    ref = _reference()
    rng = random.Random(20261005)
    for index in range(200):
        pose = {
            "x_m": rng.uniform(-2.0, 2.0),
            "y_m": rng.uniform(-2.0, 2.0),
            "theta_deg": rng.uniform(-180.0, 180.0),
        }
        forward_m = rng.uniform(-0.25, 0.25)
        left_m = rng.uniform(-0.1, 0.1)
        dtheta_deg = rng.uniform(-30.0, 30.0)
        _assert_close(
            compose_odometry(pose, forward_m, left_m, dtheta_deg),
            ref.compose_odometry(pose, forward_m, left_m, dtheta_deg),
            "compose[%d]" % index,
        )
        range_m = rng.uniform(0.05, 2.5)
        bearing_deg = rng.uniform(-180.0, 180.0)
        _assert_close(
            map_point(pose, range_m, bearing_deg),
            ref.map_point(pose, range_m, bearing_deg),
            "map[%d]" % index,
        )
        point = {"x_m": rng.uniform(-2.0, 2.0), "y_m": rng.uniform(-2.0, 2.0)}
        _assert_close(
            predict_observation(pose, point),
            ref.predict_observation(pose, point),
            "predict[%d]" % index,
        )
        blocked = rng.uniform(-180.0, 180.0)
        _assert_close(
            predict_observation(pose, point, blocked),
            ref.predict_observation(pose, point, blocked),
            "predict_blocked[%d]" % index,
        )
        candidates = {}
        for label_i in range(rng.randint(1, 3)):
            entry = {"x_m": rng.uniform(-2.0, 2.0), "y_m": rng.uniform(-2.0, 2.0)}
            if rng.random() < 0.7:
                entry["state"] = rng.choice(("confirmed", "tentative"))
                entry["odo_last_seen_m"] = rng.uniform(0.0, 5.0)
            candidates["C%d" % label_i] = entry
        det = {"range_m": range_m, "bearing_deg": bearing_deg}
        travel = rng.uniform(0.0, 4.0)
        turns = rng.randint(0, 40)
        odometer = rng.uniform(0.0, 8.0)
        _assert_close(
            gate_detection(pose, det, candidates, travel, odometer, turns),
            ref.gate_detection(pose, det, candidates, travel, odometer, turns),
            "gate[%d]" % index,
        )
        matches = []
        for _match_i in range(rng.randint(2, 4)):
            matches.append({
                "det": {
                    "range_m": rng.uniform(0.2, 2.0),
                    "bearing_deg": rng.uniform(-80.0, 80.0),
                },
                "point": {"x_m": rng.uniform(-2.0, 2.0), "y_m": rng.uniform(-2.0, 2.0)},
            })
        _assert_close(
            fix_pose(pose, matches),
            ref.fix_pose(pose, matches),
            "fix[%d]" % index,
        )
        beacon = {
            "x_m": rng.uniform(-2.0, 2.0),
            "y_m": rng.uniform(-2.0, 2.0),
            "n_obs": rng.randint(1, 6),
            "first_seen_from": [rng.uniform(-1.0, 1.0), rng.uniform(-1.0, 1.0)],
        }
        _assert_close(
            update_beacon(beacon, det, pose),
            ref.update_beacon(beacon, det, pose),
            "update[%d]" % index,
        )
        beacons = [
            {"x_m": rng.uniform(-2.0, 2.0), "y_m": rng.uniform(-2.0, 2.0)}
            for _beacon_i in range(rng.randint(0, 4))
        ]
        scans = [
            [rng.uniform(-2.0, 2.0), rng.uniform(-2.0, 2.0)]
            for _scan_i in range(rng.randint(0, 4))
        ]
        blocked_heading = None if rng.random() < 0.5 else rng.uniform(-180.0, 180.0)
        _assert_close(
            exploration_summary(pose, beacons, scans, blocked_heading),
            ref.exploration_summary(pose, beacons, scans, blocked_heading),
            "explore[%d]" % index,
        )


def test_example1_numbers():
    example = _fewshot()["example1"]
    d0, d1 = example["detections"]
    prior = compose_odometry(example["prev_pose"], **example["odometry"])
    g0 = gate_detection(
        prior, d0, {"B1": B1}, example["travel_since_fix_m"], example["odometer_m"]
    )["candidates"][0]
    g1 = gate_detection(
        prior, d1, {"B5": B5}, example["travel_since_fix_m"], example["odometer_m"]
    )["candidates"][0]
    full = fix_pose(prior, [{"det": d0, "point": B1}, {"det": d1, "point": B5}])["full"]
    pose = {"x_m": full["x_m"], "y_m": full["y_m"], "theta_deg": full["theta_deg"]}
    assert _round_pose(prior) == example["prior"]
    assert _round_pose(pose) == example["pose"]
    assert _round_gate(g0) == example["gate_B1"]
    assert _round_gate(g1) == example["gate_B5"]
    assert _round_fix(full) == example["fix_full"]


def test_example3_numbers():
    example = _fewshot()["example3"]
    report = json.loads(example["output_json"])
    by_label = {entry["beacon"]: entry for entry in report["map"]}
    b6 = by_label["B6"]
    b2 = by_label["B2"]
    d0 = next(det for det in example["detections"] if det["id"] == 6)
    d1 = next(det for det in example["detections"] if det["id"] == 2)
    prior = compose_odometry(example["prev_pose"], **example["odometry"])
    gate_b6 = gate_detection(
        prior, d0, {"B6": b6},
        example["travel_since_fix_m"], example["odometer_m"], example["turns_since_fix"],
    )["candidates"][0]
    gate_b2 = gate_detection(
        prior, d1, {"B2": b2},
        example["travel_since_fix_m"], example["odometer_m"], example["turns_since_fix"],
    )["candidates"][0]
    position = fix_pose(prior, [{"det": d0, "point": b6}])["position"]
    pose = {"x_m": position["x_m"], "y_m": position["y_m"], "theta_deg": position["theta_deg"]}
    b2b = map_point(pose, d1["range_m"], d1["bearing_deg"])
    assert _round_pose(prior) == example["prior"]
    assert _round_gate(gate_b6) == example["gate_B6"]
    assert _round_gate(gate_b2) == example["gate_id2_vs_B2"]
    assert _round_fix(position) == example["fix_position"]
    assert _round_pose(pose) == example["pose"]
    assert {key: round(value, 2) for key, value in b2b.items()} == example["B2b_point"]


def test_gate_widening_caps():
    pose = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
    det = {"range_m": 1.0, "bearing_deg": 0.0}
    gated = gate_detection(
        pose, det, {"C": {"x_m": 1.0, "y_m": 0.0}},
        travel_since_fix_m=10, turns_since_fix=100,
    )
    assert gated["gate_range_m"] == 0.60
    assert gated["gate_bearing_deg"] == 30.0


def test_dv_override_changes_gate():
    pose = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
    det = {"range_m": 1.20, "bearing_deg": 0.0}
    candidates = {"C": {"x_m": 1.0, "y_m": 0.0}}
    default = gate_detection(pose, det, candidates, 0.0, None, 0)
    assert default["candidates"][0]["in_gate"] is True
    overridden = dict(load_dv())
    overridden["gate_range_m"] = 0.10
    tight = gate_detection(pose, det, candidates, 0.0, None, 0, dv=overridden)
    assert tight["candidates"][0]["in_gate"] is False
