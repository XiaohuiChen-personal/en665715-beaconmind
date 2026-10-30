"""Design-value registry tests for configs/dv.json.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the C0 key, value, unit and hash tests.
"""
import json

import pytest

from beaconmind import course_root
from beaconmind.dv import dv_get, dv_sha12, load_dv

# Copied from plan/README.md contract C0, one key per row, in that order.
C0_KEYS = (
    "gate_range_m",
    "gate_bearing_deg",
    "gate_widen_range_per_m",
    "gate_widen_bearing_per_m",
    "gate_widen_bearing_per_turn_deg",
    "gate_cap_range_m",
    "gate_cap_bearing_deg",
    "revisit_travel_m",
    "prior_gate_m",
    "prior_gate_deg",
    "position_fix_gate_m",
    "heading_safe_deg",
    "well_cond_sigma_xy_m",
    "well_cond_sigma_theta_deg",
    "reloc_min_beacons",
    "reloc_residual_m",
    "reloc_sigma_xy_m",
    "reloc_sigma_theta_deg",
    "confirm_n_obs",
    "confirm_baseline_m",
    "suspect_conflicts",
    "reject_quality_below",
    "reject_range_above_m",
    "conflict_radius_m",
    "new_place_m",
    "scan_turns",
    "v_max_mps",
    "move_timeout_s",
    "turn_rate_dps",
    "steps_explore",
    "steps_navigation",
    "done_range_m",
    "success_margin_beacon_m",
    "success_bearing_deg",
    "success_start_m",
    "slip_yaw_disagree_deg",
    "slip_range_min_m",
    "slip_range_frac",
    "slip_ahead_deg",
    "slip_dropout_m",
    "autolatch_contacts",
    "autolatch_slips",
    "autolatch_errors",
    "stall_grace_ms",
    "stall_window_ms",
    "stall_frac",
    "estop_max_s",
    "watchdog_ms",
    "obs_frames",
    "obs_min_frames",
    "obs_settle_s",
    "forward_wall_limit_m",
    "pack_min_v",
)


def unit_for(key):
    """M1.T2 step 2 unit rule. First match wins."""
    if key == "gate_widen_range_per_m":
        return "m/m"
    if key == "gate_widen_bearing_per_m":
        return "deg/m"
    if key == "gate_widen_bearing_per_turn_deg":
        return "deg/turn"
    if key.endswith("_per_m"):
        return "m/m"
    if key.endswith("_mps"):
        return "m/s"
    if key.endswith("_dps"):
        return "deg/s"
    if key.endswith("_ms"):
        return "ms"
    if key.endswith("_m"):
        return "m"
    if key.endswith("_deg"):
        return "deg"
    if key.endswith("_s"):
        return "s"
    if key.endswith("_v"):
        return "V"
    return "1"


def test_dv_has_every_c0_key():
    loaded = load_dv()
    missing = [key for key in C0_KEYS if key not in loaded]
    assert missing == [], missing


def test_dv_c0_values_unchanged():
    loaded = load_dv()
    expected = {
        "gate_range_m": 0.30,
        "gate_bearing_deg": 15.0,
        "revisit_travel_m": 1.5,
        "v_max_mps": 0.15,
        "done_range_m": 0.55,
        "watchdog_ms": 500,
    }
    for key, value in expected.items():
        assert loaded[key] == value


def test_dv_units_match_suffix():
    path = course_root() / "configs" / "dv.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    for key, entry in document["values"].items():
        assert entry["unit"] == unit_for(key), key
    assert document["values"]["gate_widen_range_per_m"]["unit"] == "m/m"
    assert document["values"]["pack_min_v"]["unit"] == "V"


def test_dv_sha12_is_stable(tmp_path):
    first = dv_sha12()
    second = dv_sha12()
    assert first == second
    assert len(first) == 12
    assert all(ch in "0123456789abcdef" for ch in first)
    source = course_root() / "configs" / "dv.json"
    document = json.loads(source.read_text(encoding="utf-8"))
    document["values"]["gate_range_m"]["value"] = 0.31
    copy = tmp_path / "dv.json"
    copy.write_text(json.dumps(document), encoding="utf-8")
    assert dv_sha12(copy) != first


def test_dv_get_missing_key_raises():
    with pytest.raises(KeyError) as caught:
        dv_get(load_dv(), "not_a_dv_key")
    assert "not_a_dv_key" in str(caught.value)
