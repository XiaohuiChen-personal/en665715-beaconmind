"""Tests of arm B1 (baselines/b1_gtsam.py). They need gtsam: run on the Spark host venv with `-m gtsam`
(the default addopts deselect them; elsewhere they skip).

The tests are written so that the mutations found by the 2026-11-10 adversarial review fail them: swapped
bearing/range sigmas, inflated or deflated odometry sigmas, an unconverged solver, and a non-causal online estimate.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote these tests.
"""
import copy
import math
import statistics

import pytest

gtsam = pytest.importorskip("gtsam")

from beaconmind.baselines import b1_gtsam as b1  # noqa: E402
from beaconmind.envs import kinsim_lite as ks  # noqa: E402
from beaconmind.metrics import pilot as pm  # noqa: E402

pytestmark = pytest.mark.gtsam
DEV = range(1000, 1010)


def _doc(seed, bias=0.0):
    ep = ks.run_episode(seed, odo_bias=bias)
    ep["noise"] = dict(ks.NOISE, odo_bias=bias)
    return ep


def _docs(bias):
    out = []
    for s in DEV:
        try:
            out.append(_doc(s, bias))
        except NotImplementedError:
            pass
    return out


def _noiseless(doc):
    """The same episode with every measurement replaced by its exact value: B1 must then return the truth."""
    d = copy.deepcopy(doc)
    world = {t["tag"]: t for t in d["world"]}
    recs = d["records"]
    for i, r in enumerate(recs):
        if i > 0:
            a, b = recs[i - 1]["truth"], r["truth"]
            dth = ks.g.wrap_deg(b["theta_deg"] - a["theta_deg"])
            th = math.radians(a["theta_deg"])
            dx, dy = b["x_m"] - a["x_m"], b["y_m"] - a["y_m"]
            r["raw"]["odometry"] = {"forward_m": dx * math.cos(th) + dy * math.sin(th),
                                    "left_m": -dx * math.sin(th) + dy * math.cos(th), "dtheta_deg": dth}
        for det in r["raw"]["detections"]:
            o = ks.g.predict_observation(r["truth"], world[det["_tag"]])
            det["range_m"], det["bearing_deg"] = o["range_m"], o["bearing_deg"]
    return d


@pytest.mark.parametrize("calibrate", [True, False])
def test_noiseless_measurements_recover_the_truth(calibrate):
    doc = _noiseless(_doc(1002))
    res = b1.build_and_solve(doc, calibrate_scale=calibrate)
    truth = [r["truth"] for r in doc["records"]]
    for traj in (res["online"], res["smoothed"]):
        e = pm.trajectory_errors(traj, truth)
        assert e["ate_m"] < 1e-6 and e["heading_rmse_deg"] < 1e-4
    world = {t["tag"]: t for t in doc["world"]}
    assert len(res["map"]) == len({d["_tag"] for r in doc["records"] for d in r["raw"]["detections"]})
    assert all(math.hypot(m["x_m"] - world[m["tag"]]["x_m"], m["y_m"] - world[m["tag"]]["y_m"]) < 1e-6 for m in res["map"])
    if calibrate:
        assert abs(res["scales"]["forward"] - 1) < 1e-6 and abs(res["scales"]["turn"] - 1) < 1e-6


def test_detection_factor_order_units_and_sigmas():
    det = {"_tag": 3, "range_m": 1.20, "bearing_deg": -21.6}
    f = b1.detection_factor(5, det, ks.NOISE)
    sig = list(f.noiseModel().sigmas())
    assert sig[0] == pytest.approx(math.radians(math.hypot(1.0, 0.1 / math.sqrt(12))))            # bearing first, radians
    assert sig[1] == pytest.approx(math.hypot(0.01 + 0.03 * 1.20, 0.01 / math.sqrt(12)))           # range second, metres
    m = f.measured()
    assert m.bearing().degrees() == pytest.approx(-21.6) and m.range() == pytest.approx(1.20)
    assert list(f.keys()) == [gtsam.symbol("x", 5), gtsam.symbol("l", 3)]


@pytest.mark.parametrize("calibrate", [True, False])
def test_odometry_factor_sigmas(calibrate):
    fwd = b1.odometry_factor(4, {"forward_m": 0.25, "left_m": 0.0, "dtheta_deg": 0.0}, ks.NOISE, calibrate)
    sx, sy, st = fwd.noiseModel().sigmas()
    assert sx == pytest.approx(math.hypot(0.02 * 0.25, 0.01 / math.sqrt(12))) and sy == pytest.approx(b1.TINY_M)
    assert st == pytest.approx(math.radians(b1.TINY_DEG))
    turn = b1.odometry_factor(4, {"forward_m": 0.0, "left_m": 0.0, "dtheta_deg": 30.1}, ks.NOISE, calibrate)
    assert turn.noiseModel().sigmas()[2] == pytest.approx(math.radians(math.hypot(0.3, 0.1 / math.sqrt(12))))
    keys = list(fwd.keys())
    assert keys[:2] == [gtsam.symbol("x", 3), gtsam.symbol("x", 4)] and len(keys) == (4 if calibrate else 2)


def test_scale_jacobians_match_finite_differences():
    meas = (0.25, 0.0, math.radians(30.0))
    p1, p2 = gtsam.Pose2(0.1, 0.2, 0.3), gtsam.Pose2(0.33, 0.31, 0.82)
    sf, st, eps = 1.02, 0.98, 1e-6
    e = b1.scaled_odometry_error(meas, p1, p2, sf, st)
    dsf = (b1.scaled_odometry_error(meas, p1, p2, sf + eps, st) - e) / eps
    dst = (b1.scaled_odometry_error(meas, p1, p2, sf, st + eps) - e) / eps
    assert dsf == pytest.approx([meas[0] / sf ** 2, meas[1] / sf ** 2, 0.0], abs=1e-5)
    assert dst == pytest.approx([0.0, 0.0, meas[2] / st ** 2], abs=1e-5)


def test_noise_model_is_calibrated_without_drift():
    """Normalised residuals of every factor type against the truth have RMS close to 1 (inflated or deflated
    sigmas, or a bearing/range swap, fail this)."""
    z = {"forward": [], "turn": [], "bearing": [], "range": []}
    for doc in _docs(0.0):
        recs = doc["records"]
        world = {t["tag"]: t for t in doc["world"]}
        for i, r in enumerate(recs):
            if i > 0:
                odo = r["raw"]["odometry"]
                a, b = recs[i - 1]["truth"], r["truth"]
                sx, _, st = b1.odometry_sigmas(odo, ks.NOISE)
                if odo["forward_m"]:
                    z["forward"].append((odo["forward_m"] - math.hypot(b["x_m"] - a["x_m"], b["y_m"] - a["y_m"])) / sx)
                else:
                    dth = math.radians(ks.g.wrap_deg(b["theta_deg"] - a["theta_deg"]))
                    z["turn"].append((math.radians(odo["dtheta_deg"]) - dth) / st)
            for d in r["raw"]["detections"]:
                o = ks.g.predict_observation(r["truth"], world[d["_tag"]])
                sb, sr = b1.detection_sigmas(d["range_m"], ks.NOISE)
                z["bearing"].append(math.radians(ks.g.wrap_deg(d["bearing_deg"] - o["bearing_deg"])) / sb)
                z["range"].append((d["range_m"] - o["range_m"]) / sr)
    for k, v in z.items():
        rms = math.sqrt(sum(x * x for x in v) / len(v))
        assert 0.9 < rms < 1.1, (k, rms, len(v))


def test_scale_calibration_learns_the_drift_and_beats_the_uncalibrated_graph():
    docs = _docs(0.02)
    cal, raw, fwd, turn = [], [], [], []
    for doc in docs:
        truth = [r["truth"] for r in doc["records"]]
        r1 = b1.build_and_solve(doc)
        cal.append(pm.trajectory_errors(r1["online"], truth)["ate_m"])
        raw.append(pm.trajectory_errors(b1.build_and_solve(doc, calibrate_scale=False)["online"], truth)["ate_m"])
        fwd.append(r1["scales"]["forward"])
        turn.append(r1["scales"]["turn"])
    assert abs(statistics.median(fwd) - 1.02) < 0.005 and abs(statistics.median(turn) - 1.02) < 0.005
    assert statistics.median(cal) < 0.015, statistics.median(cal)          # regression bound (dev seeds 1000-1009)
    assert sum(c < r for c, r in zip(cal, raw)) >= len(docs) - 1


def test_b1_beats_dead_reckoning_and_b2_and_matches_batch():
    for seed in (1000, 1004):
        doc = _doc(seed, 0.02)
        res = b1.build_and_solve(doc)
        truth = [r["truth"] for r in doc["records"]]
        e1 = pm.trajectory_errors(res["online"], truth)["ate_m"]
        assert e1 < pm.trajectory_errors(ks.dead_reckoning(doc["records"]), truth)["ate_m"]
        assert e1 < pm.trajectory_errors([r["report"]["pose"] for r in doc["records"]], truth)["ate_m"]
        bc = b1.batch_check(res)
        assert bc["position_m"] < 1e-4 and bc["heading_deg"] < 0.01 and bc["tag_m"] < 1e-4, bc
        ms = pm.map_scores_c10(res["map"], doc["world"])
        assert ms["phantoms"] == 0 and ms["map_rmse_m"] < 0.05


def test_online_is_causal():
    """The online pose of step t must not change when later steps are removed from the log."""
    doc = _doc(1001, 0.02)
    full = b1.build_and_solve(doc)["online"]
    cut = copy.deepcopy(doc)
    cut["records"] = cut["records"][:20]
    short = b1.build_and_solve(cut)["online"]
    for a, b in zip(full[:20], short):
        assert abs(a["x_m"] - b["x_m"]) < 1e-9 and abs(a["y_m"] - b["y_m"]) < 1e-9
        assert abs(ks.g.wrap_deg(a["theta_deg"] - b["theta_deg"])) < 1e-7


def test_refuses_a_log_without_the_kinsim_noise_block():
    doc = _doc(1000)
    del doc["noise"]
    with pytest.raises(ValueError, match="kinsim"):
        b1.build_and_solve(doc)
