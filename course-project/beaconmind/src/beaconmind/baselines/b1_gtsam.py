"""Arm B1: a planar factor graph solved incrementally with GTSAM's iSAM2, with oracle data association and
online odometry-scale calibration.

B1 is the reference the LLM arms are compared with in H2 (report Section IV-A; plan/README.md OD3): it sees the
same recorded odometry and detections as every other arm, but it is told which physical tag produced each
detection (the simulator's `_tag`), so association errors cannot happen. It is meant to be a strong causal
estimator with the same information plus perfect association.

Model (Dellaert & Kaess, "Factor Graphs for Robot Perception", 2017, Sec. 2; GTSAM's planar SLAM example
`python/gtsam/examples/PlanarSLAMExample.py` names the pose, landmark and bearing-range parts):
- one Pose2 variable x_t per step; a prior on x_0 at the start pose (the map frame, as for every arm);
- one Point2 variable per physical tag, and a BearingRangeFactor2D per detection; GTSAM's bearing is measured
  counter-clockwise from the pose's x axis, which is beaconmind.geometry's bearing_deg;
- odometry: with `calibrate_scale=True` (the B1 of the study), two scalar variables s_f and s_t (forward and turn
  odometry scale) with a weak prior N(1, 0.05) each, and one factor per move whose error, in x_{t-1}'s frame, is
      e = [ dx - f/s_f,  dy - l/s_f,  wrap(dtheta - th/s_t) ],   (dx, dy, dtheta) = x_{t-1}.between(x_t)
  (f, l, th: the logged move). So B1 learns a systematic odometry bias from the landmarks instead of being told it
  (the 2 % over-read of the drift block is unknown to every arm). With `calibrate_scale=False` the move is an
  ordinary BetweenFactorPose2 (the first version, kept for comparison): its sigmas are zero-mean, so under a
  systematic bias it is overconfident (adversarial review of 2026-11-10: turn residuals 2.2 sigma RMS at 2 %
  drift), and its median online ATE on dev seeds was about 1.7 times the calibrated one.
Noise: the simulator's sigmas, taken from the log's `noise` block, plus the logged values' rounding
(odometry and ranges to 0.01, angles to 0.1, a uniform error with SD = step / sqrt(12)):
  forward  sqrt((wheel_scale_sigma * |f|)^2 + r_m^2)    lateral 1 mm      heading 0.05 deg   (forward moves)
  turn     sqrt(gyro_sigma_deg^2 + r_deg^2)              translation 1 mm                     (turns)
  range    sqrt((range_sigma_a_m + range_sigma_b * r)^2 + r_m^2)   bearing sqrt(bearing_sigma_deg^2 + r_deg^2)
The 1 mm and 0.05 deg terms encode a fact of the kinematic simulator: a forward move is exactly straight and a
turn exactly in place. They are informative constraints, true only for kinsim logs, so this model must not be run
on real-car logs (`build_and_solve` refuses a log whose `noise` block lacks the simulator's keys).
Estimates: after each step's iSAM2 update, x_t's estimate is B1's **online** pose for step t (the same causal
information the other arms have); this is the trajectory the study scores (pre-registration, evidence/M4/M4.T1).
The final estimate of every pose (the smoothed trajectory, which uses later data) and of every tag (B1's map) is
kept too, as secondary output. Solver: relinearisation threshold 0.001, relinearizeSkip 1, two extra updates per
step, Gauss-Newton wildfire threshold 0, and every estimate is a full back-substitution (`calculateBestEstimate`).
With `calculateEstimate` and the default wildfire threshold (0.001) the final trajectory was up to 1.3 mm from the
batch optimum on dev seeds 1000 and 1004; with these settings it is within 0.02 mm. `batch_check` compares the
final estimate (positions, headings, tags) with a batch Levenberg-Marquardt solve of the same graph.

Requires gtsam (Spark host venv ~/.venvs/beaconmind, gtsam 4.3.0); not used by the agent containers.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote this baseline; the scale calibration follows a
variant proposed by an adversarial-review subagent (Claude Opus 5.5) the same day.
"""
import math
import time

import numpy as np

try:
    import gtsam
except ImportError:  # the Mac and the agent containers have no gtsam; tests skip
    gtsam = None

ROUND_M = 0.01 / math.sqrt(12)        # logged forward_m and range_m have 2 decimals
ROUND_DEG = 0.1 / math.sqrt(12)       # logged dtheta_deg and bearing_deg have 1 decimal
TINY_M, TINY_DEG = 0.001, 0.05
PRIOR_SIGMA = (1e-4, 1e-4, 1e-4)
SCALE_PRIOR_SIGMA = 0.05
NOISE_KEYS = ("wheel_scale_sigma", "gyro_sigma_deg", "range_sigma_a_m", "range_sigma_b", "bearing_sigma_deg")
SOLVER = {"relinearize_threshold": 0.001, "relinearize_skip": 1, "wildfire_threshold": 0.0, "extra_updates": 2,
          "estimate": "calculateBestEstimate", "scale_prior": [1.0, SCALE_PRIOR_SIGMA]}
JAC_EPS = 1e-7


def _X(t):
    return gtsam.symbol("x", t)


def _L(tag):
    return gtsam.symbol("l", tag)


def _S(i):
    return gtsam.symbol("s", i)       # s0 forward scale, s1 turn scale


def _pose2(p):
    return gtsam.Pose2(p["x_m"], p["y_m"], math.radians(p["theta_deg"]))


def _pose_dict(p):
    return {"x_m": p.x(), "y_m": p.y(), "theta_deg": math.degrees(p.theta())}


def odometry_sigmas(odo, noise):
    """(sigma_x, sigma_y, sigma_theta_rad) of one logged move."""
    f, dth = abs(odo["forward_m"]), abs(odo["dtheta_deg"])
    if f > 0 and dth == 0:
        return (math.hypot(noise["wheel_scale_sigma"] * f, ROUND_M), TINY_M, math.radians(TINY_DEG))
    if f == 0 and dth > 0:
        return (TINY_M, TINY_M, math.radians(math.hypot(noise["gyro_sigma_deg"], ROUND_DEG)))
    # neither move type of the simulator: a general move gets both sigmas
    return (math.hypot(noise["wheel_scale_sigma"] * f, ROUND_M), math.hypot(noise["wheel_scale_sigma"] * f, ROUND_M),
            math.radians(math.hypot(noise["gyro_sigma_deg"], ROUND_DEG)))


def detection_sigmas(range_m, noise):
    """(sigma_bearing_rad, sigma_range_m) of one detection (GTSAM orders bearing first)."""
    return (math.radians(math.hypot(noise["bearing_sigma_deg"], ROUND_DEG)),
            math.hypot(noise["range_sigma_a_m"] + noise["range_sigma_b"] * range_m, ROUND_M))


def detection_factor(t, det, noise):
    """The BearingRangeFactor2D of one detection at step t (landmark = the detection's true tag)."""
    sb, sr = detection_sigmas(det["range_m"], noise)
    return gtsam.BearingRangeFactor2D(_X(t), _L(det["_tag"]), gtsam.Rot2.fromDegrees(det["bearing_deg"]), det["range_m"],
                                      gtsam.noiseModel.Diagonal.Sigmas([sb, sr]))


def scaled_odometry_error(meas, p1, p2, s_f, s_t):
    """Error of one move with scale variables: x_{t-1}.between(x_t) minus the move divided by the scales."""
    b = p1.between(p2)
    return np.array([b.x() - meas[0] / s_f, b.y() - meas[1] / s_f, math.remainder(b.theta() - meas[2] / s_t, 2 * math.pi)])


def odometry_factor(t, odo, noise, calibrate_scale):
    """The factor of the move that led to step t."""
    meas = (odo["forward_m"], odo["left_m"], math.radians(odo["dtheta_deg"]))
    model = gtsam.noiseModel.Diagonal.Sigmas(list(odometry_sigmas(odo, noise)))
    if not calibrate_scale:
        return gtsam.BetweenFactorPose2(_X(t - 1), _X(t), gtsam.Pose2(*meas), model)
    k1, k2, kf, kt = _X(t - 1), _X(t), _S(0), _S(1)

    def error(this, values, H):
        p1, p2 = values.atPose2(k1), values.atPose2(k2)
        sf, st = float(values.atVector(kf)[0]), float(values.atVector(kt)[0])
        e = scaled_odometry_error(meas, p1, p2, sf, st)
        if H is not None:        # central differences in the tangent spaces GTSAM retracts in
            J1, J2 = np.zeros((3, 3)), np.zeros((3, 3))
            for i in range(3):
                d = np.zeros(3)
                d[i] = JAC_EPS
                J1[:, i] = (scaled_odometry_error(meas, p1.retract(d), p2, sf, st)
                            - scaled_odometry_error(meas, p1.retract(-d), p2, sf, st)) / (2 * JAC_EPS)
                J2[:, i] = (scaled_odometry_error(meas, p1, p2.retract(d), sf, st)
                            - scaled_odometry_error(meas, p1, p2.retract(-d), sf, st)) / (2 * JAC_EPS)
            # analytic derivatives with respect to the scales
            J3 = np.array([[meas[0] / sf ** 2], [meas[1] / sf ** 2], [0.0]])
            J4 = np.array([[0.0], [0.0], [meas[2] / st ** 2]])
            H[0], H[1], H[2], H[3] = J1, J2, J3, J4
        return e
    return gtsam.CustomFactor(model, [k1, k2, kf, kt], error)


def build_and_solve(doc, extra_updates=2, calibrate_scale=True):
    """Run B1 on one recorded kinsim episode (kinsim_lite.run_episode output, as tools/pilot_record.py writes it).
    Returns {online, smoothed, map, scales, ...}; `online` is the scored trajectory."""
    if gtsam is None:
        raise ImportError("gtsam is not installed")
    noise = doc.get("noise") or {}
    missing = [k for k in NOISE_KEYS if k not in noise]
    if missing:
        raise ValueError("log has no kinsim noise block (missing %s): B1's odometry model is for kinsim logs only" % missing)
    tag_id = {t["tag"]: t["id"] for t in doc["world"]}
    params = gtsam.ISAM2Params()
    params.setRelinearizeThreshold(SOLVER["relinearize_threshold"])
    params.relinearizeSkip = SOLVER["relinearize_skip"]
    gn = gtsam.ISAM2GaussNewtonParams()
    gn.setWildfireThreshold(SOLVER["wildfire_threshold"])
    params.setOptimizationParams(gn)
    isam = gtsam.ISAM2(params)
    graph_all = gtsam.NonlinearFactorGraph()
    init_all = gtsam.Values()
    online, seen = [], set()
    t0 = time.perf_counter()
    est_prev = None
    for t, rec in enumerate(doc["records"]):
        raw = rec["raw"]
        graph, values = gtsam.NonlinearFactorGraph(), gtsam.Values()
        if t == 0:
            x0 = gtsam.Pose2(0.0, 0.0, 0.0)
            graph.add(gtsam.PriorFactorPose2(_X(0), x0, gtsam.noiseModel.Diagonal.Sigmas(list(PRIOR_SIGMA))))
            values.insert(_X(0), x0)
            if calibrate_scale:
                for i in (0, 1):
                    graph.add(gtsam.PriorFactorVector(_S(i), np.array([1.0]),
                                                      gtsam.noiseModel.Isotropic.Sigma(1, SCALE_PRIOR_SIGMA)))
                    values.insert(_S(i), np.array([1.0]))
            guess = x0
        else:
            odo = raw["odometry"]
            if odo is None:
                raise ValueError("step %d has no odometry" % t)
            graph.add(odometry_factor(t, odo, noise, calibrate_scale))
            guess = est_prev.compose(gtsam.Pose2(odo["forward_m"], odo["left_m"], math.radians(odo["dtheta_deg"])))
            values.insert(_X(t), guess)
        for d in raw["detections"]:
            graph.add(detection_factor(t, d, noise))
            if d["_tag"] not in seen:
                a = guess.theta() + math.radians(d["bearing_deg"])
                values.insert(_L(d["_tag"]), gtsam.Point2(guess.x() + d["range_m"] * math.cos(a),
                                                          guess.y() + d["range_m"] * math.sin(a)))
                seen.add(d["_tag"])
        isam.update(graph, values)
        for _ in range(extra_updates):
            isam.update()
        est = isam.calculateBestEstimate()
        est_prev = est.atPose2(_X(t))
        online.append(_pose_dict(est_prev))
        graph_all.push_back(graph)
        init_all.insert(values)
    final = isam.calculateBestEstimate()
    seconds = time.perf_counter() - t0
    smoothed = [_pose_dict(final.atPose2(_X(t))) for t in range(len(doc["records"]))]
    tmap = []
    for tag in sorted(seen):
        p = final.atPoint2(_L(tag))
        tmap.append({"beacon": "T%d" % tag, "tag": tag, "id": tag_id[tag], "x_m": float(p[0]), "y_m": float(p[1])})
    scales = ({"forward": float(final.atVector(_S(0))[0]), "turn": float(final.atVector(_S(1))[0])}
              if calibrate_scale else None)
    return {"online": online, "smoothed": smoothed, "map": tmap, "scales": scales, "calibrate_scale": calibrate_scale,
            "seconds": round(seconds, 3), "n_factors": graph_all.size(), "n_tags": len(seen),
            "graph": graph_all, "initial": init_all, "final": final}


def batch_check(result):
    """Largest differences between iSAM2's final estimate and a batch Levenberg-Marquardt solve of the same graph
    from the same initial values: {position_m, heading_deg, tag_m}. A check that the incremental solver
    converged (it cannot detect a local minimum that both share)."""
    lm = gtsam.LevenbergMarquardtOptimizer(result["graph"], result["initial"], gtsam.LevenbergMarquardtParams()).optimize()
    final = result["final"]
    pos = hd = tag = 0.0
    for t in range(len(result["smoothed"])):
        p, q = final.atPose2(_X(t)), lm.atPose2(_X(t))
        pos = max(pos, math.hypot(q.x() - p.x(), q.y() - p.y()))
        hd = max(hd, abs(math.degrees(math.remainder(q.theta() - p.theta(), 2 * math.pi))))
    for m in result["map"]:
        a, b = final.atPoint2(_L(m["tag"])), lm.atPoint2(_L(m["tag"]))
        tag = max(tag, math.hypot(a[0] - b[0], a[1] - b[1]))
    return {"position_m": pos, "heading_deg": hd, "tag_m": tag}
