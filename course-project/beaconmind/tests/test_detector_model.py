"""Tag-pilot arithmetic (beaconmind.detector_model; plan task M1.T8 step 8). Pure Python.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote these tests (the first seven are the ones the plan names).
"""
import math

import pytest

from beaconmind import detector_model as dm


def rows(n, hits, range_m=1.0, bearing_deg=0.0, tag_id=3, wrong=0, noise=0.0):
    """n frame rows: the first `hits` detect the tag, the next `wrong` hold another id, the rest are empty."""
    out = []
    for i in range(n):
        if i < hits:
            wiggle = noise * ((i % 3) - 1)
            out.append({"detected": 1, "id": tag_id, "range_m": range_m + wiggle, "bearing_deg": bearing_deg + 10 * wiggle})
        elif i < hits + wrong:
            out.append({"detected": 0, "id": tag_id + 1, "range_m": "", "bearing_deg": ""})
        else:
            out.append({"detected": 0, "id": None, "range_m": "", "bearing_deg": ""})
    return out


def truth(x, y=0.0, part="A", incidence=None, tag_id=3, name=None, trusted=True):
    return {"x_m": x, "y_m": y, "incidence_deg": incidence, "tag_id": tag_id, "part": part,
            "placement": name or "%s-%.2f" % (part, x), "bearing_trusted": trusted}


def summary(x, hits=30, n=30, err=0.0, part="A", y=0.0, incidence=None, bearing_err=0.0, noise=0.0):
    t = truth(x, y, part, incidence)
    rng, bearing = math.hypot(x, y), math.degrees(math.atan2(y, x))
    return dm.summarize_placement(rows(n, hits, rng + err, bearing + bearing_err, noise=noise), t)


# ---- the tests plan M1.T8 names

def test_fit_line_exact():
    xs = [0.5, 1.0, 2.0, 3.0]
    a, b = dm.fit_line(xs, [0.01 + 0.02 * x for x in xs])
    assert a == pytest.approx(0.01, abs=1e-12) and b == pytest.approx(0.02, abs=1e-12)


def test_fit_line_needs_two_distinct_x():
    with pytest.raises(ValueError):
        dm.fit_line([1.0], [2.0])
    with pytest.raises(ValueError):
        dm.fit_line([1.0, 1.0, 1.0], [2.0, 3.0, 4.0])
    with pytest.raises(ValueError):
        dm.fit_line([1.0, 2.0], [2.0])


def test_summarize_counts_misses_and_wrong_ids():
    s = dm.summarize_placement(rows(30, 27, wrong=1), truth(1.0))
    assert s["n_frames"] == 30 and s["n_detected"] == 27 and s["rate"] == pytest.approx(27 / 30)
    assert s["n_wrong_id"] == 1
    assert s["flags"] == [1] * 27 + [0] * 3
    # a frame marked detected but holding another id is a wrong id, not a hit
    bad = rows(4, 4)
    bad[0]["id"] = 9
    s = dm.summarize_placement(bad, truth(1.0))
    assert s["n_detected"] == 3 and s["n_wrong_id"] == 1


def test_rows_read_back_from_a_csv_are_accepted():
    text_rows = [{"detected": "1", "id": "3", "range_m": "1.02", "bearing_deg": "-0.5"},
                 {"detected": "0", "id": "", "range_m": "", "bearing_deg": ""},
                 {"detected": "0", "id": "7", "range_m": "", "bearing_deg": ""}]
    s = dm.summarize_placement(text_rows, truth(1.0))
    assert s["n_detected"] == 1 and s["n_wrong_id"] == 1 and s["range_err_median"] == pytest.approx(0.02)


def test_bearing_error_wraps():
    t = {"x_m": -1.0, "y_m": -math.tan(math.radians(1.0)), "incidence_deg": 0.0}          # true bearing -179
    s = dm.summarize_placement([{"detected": 1, "id": 3, "range_m": 1.0, "bearing_deg": 179.0}], t)
    assert s["bearing_true"] == pytest.approx(-179.0)
    assert s["bearing_err_median_deg"] == pytest.approx(-2.0)


def test_window_probability():
    assert dm.window_success_probability([1, 1, 0, 1, 0, 0, 1, 1], 5, 3) == pytest.approx(0.5)
    assert dm.window_success_probability([1] * 10, 5, 3) == 1.0
    assert dm.window_success_probability([1, 1, 1], 5, 3) == 0.0


def test_noise_model_validates():
    from beaconmind.schemas import validate
    summaries = [summary(x, err=0.004 * x, noise=0.002, bearing_err=-0.8) for x in (0.8, 1.0, 1.5, 2.0, 2.5)]
    summaries += [summary(1.5, y=0.3, part="B", err=0.01, bearing_err=-0.6),
                  summary(1.0, part="C", incidence=30.0), summary(1.0, part="C", incidence=45.0),
                  summary(1.0, part="C", incidence=60.0, hits=10),
                  summary(0.7, part="D", hits=0), summary(3.0, part="E", hits=29), summary(3.5, part="E", hits=12)]
    model = dm.build_noise_model(summaries, 0.16, {"log": "test", "date": "2026-11-18", "n_frames": 360, "n_placements": 12})
    try:
        assert validate("detector_noise", model) == []
    except ImportError:
        pytest.skip("jsonschema is not installed")
    assert model["range_bias_m"]["b"] == pytest.approx(0.004, abs=0.002)
    assert model["bearing_bias_deg"] == pytest.approx(-0.8)
    assert model["min_range_m"] == pytest.approx(0.8) and model["max_range_m"] == pytest.approx(3.0)
    assert model["max_incidence_deg"] == 45.0
    assert (model["obs_frames"], model["obs_min_frames"]) == (5, 3)
    assert model["tag_black_size_m"] == 0.16 and len(model["p_detect"]) == 12
    assert model["range_sigma_m"]["a"] >= 0 and model["range_sigma_m"]["b"] >= 0
    assert model["bearing_sigma_deg"]["a"] > 0


def test_reliable_range_rule():
    low_rate = summary(1.0, hits=17, n=20)                     # 0.85
    biased = summary(1.5, err=0.12)
    good = summary(2.0)
    assert not dm.is_reliable(low_rate) and not dm.is_reliable(biased) and dm.is_reliable(good)
    assert dm.reliable_range([low_rate, biased, good]) == (2.0, 2.0)
    assert dm.is_reliable(summary(1.0, hits=18, n=20)) and dm.is_reliable(summary(1.5, err=-0.099))


# ---- more

def test_reliable_range_is_one_unbroken_run():
    s = [summary(0.6, hits=0, part="D"), summary(0.8), summary(1.0), summary(1.5, hits=5), summary(2.0), summary(2.5),
         summary(3.0, part="E"), summary(3.5, part="E", hits=3)]
    assert dm.reliable_range(s) == (2.0, 3.0)                  # the failure at 1.5 m ends the first run
    assert dm.reliable_range([summary(1.0, hits=0)]) == (None, None)
    assert dm.reliable_range([summary(1.0, part="B", y=0.2)]) == (None, None)     # part B is not a range placement


def test_squared_car_incidence_equals_bearing():
    s = dm.summarize_placement(rows(5, 5, math.hypot(2.0, 0.5), math.degrees(math.atan2(0.5, 2.0))), truth(2.0, 0.5, "B"))
    assert s["incidence_deg"] == pytest.approx(math.degrees(math.atan2(0.5, 2.0)))
    assert s["bearing_true"] > 0 and s["range_err_median"] == pytest.approx(0.0, abs=1e-12)
    s = dm.summarize_placement(rows(5, 5), truth(1.0, 0.0, "C", incidence=-45.0))
    assert s["incidence_deg"] == 45.0


def test_max_incidence():
    c = [summary(1.0, part="C", incidence=30.0), summary(1.5, part="C", incidence=30.0),
         summary(1.0, part="C", incidence=45.0), summary(1.5, part="C", incidence=45.0, hits=3),
         summary(1.0, part="C", incidence=60.0)]
    assert dm.max_incidence(c) == 30.0                         # 45 fails at one distance; 60 does not count after it
    assert dm.max_incidence([summary(1.5, y=0.4, part="B")]) == pytest.approx(math.degrees(math.atan2(0.4, 1.5)))
    assert dm.max_incidence([summary(1.0, hits=0)]) == 0.0


def test_choose_window():
    steady = [summary(1.0), summary(2.0)]
    assert dm.choose_window(steady) == ((5, 3), "confirmed", 1.0)
    flicker = dm.summarize_placement([{"detected": f, "id": 3, "range_m": 2.0, "bearing_deg": 0.0}
                                      for f in [1, 0, 1, 0, 1, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1] * 2], truth(2.0))
    assert flicker["rate"] < 0.9
    assert dm.choose_window([flicker], rate_threshold=0.7)[1] == "confirmed"
    gaps = dm.summarize_placement([{"detected": f, "id": 3, "range_m": 2.0, "bearing_deg": 0.0}
                                   for f in [1, 1, 0, 0, 0] * 6], truth(2.0))
    pair, verdict, worst = dm.choose_window([gaps], rate_threshold=0.3)
    assert pair == (5, 2) and verdict == "alternative" and worst == 1.0
    none = dm.summarize_placement([{"detected": f, "id": 3, "range_m": 2.0, "bearing_deg": 0.0}
                                   for f in [1, 0, 0, 0, 0, 0] * 5], truth(2.0))
    assert dm.choose_window([none], rate_threshold=0.1)[1] == "not_met"
    assert dm.choose_window([summary(1.0, hits=0)])[1] == "no_data"


def test_noise_model_needs_a_reliable_placement():
    with pytest.raises(ValueError):
        dm.build_noise_model([summary(1.0, hits=0)], 0.16, {"log": "x", "date": "2026-11-18", "n_frames": 30, "n_placements": 1})


def test_single_range_gives_a_constant_bias():
    model = dm.build_noise_model([summary(1.0, err=0.02)], 0.16,
                                 {"log": "x", "date": "2026-11-18", "n_frames": 30, "n_placements": 1})
    assert model["range_bias_m"] == {"a": 0.02, "b": 0.0}
    assert model["min_range_m"] == 1.0 and model["max_range_m"] == 1.0


def test_untrusted_bearings_stay_out_of_the_bearing_fit():
    good = [summary(x, bearing_err=0.5) for x in (1.0, 2.0)]
    aimed = dm.summarize_placement(rows(30, 30, 1.0, 9.0), truth(1.0, 0.0, "B", trusted=False, name="aimed"))
    model = dm.build_noise_model(good + [aimed], 0.16, {"log": "x", "date": "2026-11-18", "n_frames": 90, "n_placements": 3})
    assert model["bearing_bias_deg"] == pytest.approx(0.5)
    assert model["bearing_sigma_deg"]["a"] < 0.01
