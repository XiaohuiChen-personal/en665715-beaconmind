"""L2 single-timestep geometry (AGENT-DESIGN v3.3, D3 frames and D5 tools).

Map frame = the robot's pose at its first observation; x forward (toward the camera/caster
end), y left, theta and bearing counter-clockwise positive, degrees, wrapped to (-180, 180].
Every function here uses one step's data only. Nothing optimises over observation history.

Thresholds are read from configs/dv.json (contract C0 plus the literals this module used to
hard-code). SECTOR_BLOCK_DIST_M and SECTOR_BLOCK_HALF_DEG in the reference are unused there
and are not design values here. The 1e-12 determinant floor in _sigma is a numeric guard,
not a design value.

AI-assisted: written by Claude Opus 5.5 (Claude Code), 2026-09-27. The 2-D rigid alignment in
fix_pose is the standard closed-form least-squares fit (Kabsch/Umeyama without scale), and the
sigma estimate is a first-order (Gauss-Newton) covariance. Both are reimplemented here, not
copied.
Derived from: assignments/assignment4/system-prompt/tools/l2_geometry.py (copied 2026-10-06; constants moved to configs/dv.json).
AI-assisted: Grok 4.7 via Cursor, 2026-10-06: ported the reference into beaconmind.geometry and replaced hard-coded thresholds with configs/dv.json.
"""
import math

from beaconmind.dv import dv_get, load_dv


def wrap_deg(a):
    a = math.fmod(a, 360.0)
    if a <= -180.0:
        a += 360.0
    elif a > 180.0:
        a -= 360.0
    return a


def compose_odometry(pose, forward_m, left_m, dtheta_deg):
    """x' = x + f cos(th) - l sin(th); y' = y + f sin(th) + l cos(th); th' = wrap(th + dth)."""
    x, y, th = pose["x_m"], pose["y_m"], math.radians(pose["theta_deg"])
    return {"x_m": x + forward_m * math.cos(th) - left_m * math.sin(th),
            "y_m": y + forward_m * math.sin(th) + left_m * math.cos(th),
            "theta_deg": wrap_deg(pose["theta_deg"] + dtheta_deg)}


def map_point(pose, range_m, bearing_deg):
    a = math.radians(pose["theta_deg"] + bearing_deg)
    return {"x_m": pose["x_m"] + range_m * math.cos(a), "y_m": pose["y_m"] + range_m * math.sin(a)}


def predict_observation(pose, point, blocked_heading_deg=None, dv=None):
    """Range/bearing of a point from pose. With blocked_heading_deg (read by the harness from the
    previous report's memory), also near_blocked: the target direction is within near_blocked_deg of it."""
    dv = dv or load_dv()
    dx, dy = point["x_m"] - pose["x_m"], point["y_m"] - pose["y_m"]
    out = {"range_m": math.hypot(dx, dy),
           "bearing_deg": wrap_deg(math.degrees(math.atan2(dy, dx)) - pose["theta_deg"])}
    # near_blocked is always present (False when no heading is blocked), as the prompt's TOOLS line promises
    limit = dv_get(dv, "near_blocked_deg")
    out["near_blocked"] = (blocked_heading_deg is not None
                           and abs(wrap_deg(math.degrees(math.atan2(dy, dx)) - blocked_heading_deg)) <= limit)
    return out


def distance(a, b):
    return {"d_m": math.hypot(a["x_m"] - b["x_m"], a["y_m"] - b["y_m"])}


def gate_detection(pose, det, candidates, travel_since_fix_m=0.0, odometer_m=None, turns_since_fix=0, dv=None):
    """det: {range_m, bearing_deg}; candidates: {label: point or map entry}. Returns wrapped deltas,
    the point distance and in_gate per candidate. The gate widens with travel since the last full
    fix and with turns since that fix, then caps. If a candidate carries odo_last_seen_m and state,
    also returns travel_since_seen_m and revisit."""
    dv = dv or load_dv()
    t = min(max(travel_since_fix_m, 0.0), dv_get(dv, "gate_travel_cap_m"))
    g_r = min(dv_get(dv, "gate_range_m") + dv_get(dv, "gate_widen_range_per_m") * t,
              dv_get(dv, "gate_cap_range_m"))
    g_b = min(dv_get(dv, "gate_bearing_deg")
              + dv_get(dv, "gate_widen_bearing_per_m") * t
              + dv_get(dv, "gate_widen_bearing_per_turn_deg") * max(turns_since_fix, 0),
              dv_get(dv, "gate_cap_bearing_deg"))
    new_pt = map_point(pose, det["range_m"], det["bearing_deg"])
    out = []
    revisit_m = dv_get(dv, "revisit_travel_m")
    for label, pt in candidates.items():
        pr = predict_observation(pose, pt, dv=dv)
        d_r = det["range_m"] - pr["range_m"]
        d_b = wrap_deg(det["bearing_deg"] - pr["bearing_deg"])
        row = {"beacon": label, "pred_range_m": pr["range_m"], "pred_bearing_deg": pr["bearing_deg"],
               "d_range_m": d_r, "d_bearing_deg": d_b,
               "point_distance_m": distance(new_pt, pt)["d_m"],
               "in_gate": abs(d_r) <= g_r and abs(d_b) <= g_b}
        if odometer_m is not None and "odo_last_seen_m" in pt:
            row["travel_since_seen_m"] = odometer_m - pt["odo_last_seen_m"]
            row["revisit"] = pt.get("state") == "confirmed" and row["travel_since_seen_m"] >= revisit_m
        out.append(row)
    return {"new_point": new_pt, "gate_range_m": g_r, "gate_bearing_deg": g_b, "candidates": out}


def _resection(obs, mp):
    n = len(obs)
    ox, oy = sum(p[0] for p in obs) / n, sum(p[1] for p in obs) / n
    mx, my = sum(p[0] for p in mp) / n, sum(p[1] for p in mp) / n
    sxx = sum((o[0] - ox) * (m[0] - mx) + (o[1] - oy) * (m[1] - my) for o, m in zip(obs, mp))
    sxy = sum((o[0] - ox) * (m[1] - my) - (o[1] - oy) * (m[0] - mx) for o, m in zip(obs, mp))
    th = math.atan2(sxy, sxx)
    c, s = math.cos(th), math.sin(th)
    return mx - (c * ox - s * oy), my - (s * ox + c * oy), th


def _sigma(pose_xyth, dets, points, dv=None):
    """First-order covariance of (x, y, th) from range/bearing measurements (DV noise model)."""
    dv = dv or load_dv()
    range_a = dv_get(dv, "sigma_range_a_m")
    range_b = dv_get(dv, "sigma_range_b_per_m")
    bearing_rad = math.radians(dv_get(dv, "sigma_bearing_deg"))
    x, y, th = pose_xyth
    H, W = [], []
    for d, p in zip(dets, points):
        dx, dy = p[0] - x, p[1] - y
        q = dx * dx + dy * dy
        r = math.sqrt(q)
        H.append([-dx / r, -dy / r, 0.0])
        W.append(1.0 / (range_a + range_b * d["range_m"]) ** 2)
        H.append([dy / q, -dx / q, -1.0])
        W.append(1.0 / bearing_rad ** 2)
    A = [[sum(W[k] * H[k][i] * H[k][j] for k in range(len(H))) for j in range(3)] for i in range(3)]
    a, b, c_, d, e, f, g, h, i = A[0][0], A[0][1], A[0][2], A[1][0], A[1][1], A[1][2], A[2][0], A[2][1], A[2][2]
    det = a * (e * i - f * h) - b * (d * i - f * g) + c_ * (d * h - e * g)
    if abs(det) < 1e-12:
        return float("inf"), float("inf")
    cxx = (e * i - f * h) / det
    cyy = (a * i - c_ * g) / det
    ctt = (a * e - b * d) / det
    return math.sqrt(max(cxx, 0) + max(cyy, 0)), math.degrees(math.sqrt(max(ctt, 0)))


def fix_pose(prior, matches, dv=None):
    """matches: [{det: {range_m, bearing_deg}, point: {x_m, y_m}}] from ONE observation, confirmed
    beacons only. Returns a full resection (>=2 matches) and a heading-held position fix (>=1)."""
    dv = dv or load_dv()
    out = {"full": None, "position": None}
    if not matches:
        return {"status": "error", "error": "no matched confirmed beacons in this step. Nothing changed."}
    obs = [(m["det"]["range_m"] * math.cos(math.radians(m["det"]["bearing_deg"])),
            m["det"]["range_m"] * math.sin(math.radians(m["det"]["bearing_deg"]))) for m in matches]
    mp = [(m["point"]["x_m"], m["point"]["y_m"]) for m in matches]
    if len(matches) >= 2:
        tx, ty, th = _resection(obs, mp)
        c, s = math.cos(th), math.sin(th)
        res = math.sqrt(sum(((c * o[0] - s * o[1] + tx) - p[0]) ** 2 + ((s * o[0] + c * o[1] + ty) - p[1]) ** 2
                            for o, p in zip(obs, mp)) / len(obs))
        sxy, sth = _sigma((tx, ty, th), [m["det"] for m in matches], mp, dv=dv)
        full = {"x_m": tx, "y_m": ty, "theta_deg": wrap_deg(math.degrees(th)), "residual_m": res,
                "sigma_xy_m": sxy, "sigma_theta_deg": sth,
                "well_conditioned": sxy <= dv_get(dv, "well_cond_sigma_xy_m") and sth <= dv_get(dv, "well_cond_sigma_theta_deg")}
        full["delta_m"] = distance(full, prior)["d_m"]
        full["delta_deg"] = wrap_deg(full["theta_deg"] - prior["theta_deg"])
        full["within_prior_gate"] = (full["delta_m"] <= dv_get(dv, "prior_gate_m")
                                     and abs(full["delta_deg"]) <= dv_get(dv, "prior_gate_deg"))
        # a fix good enough to override a drifted prior (beacon count, residual and sigma from C0)
        full["relocalisation_ok"] = (len(matches) >= dv_get(dv, "reloc_min_beacons")
                                     and res <= dv_get(dv, "reloc_residual_m")
                                     and sxy <= dv_get(dv, "reloc_sigma_xy_m")
                                     and sth <= dv_get(dv, "reloc_sigma_theta_deg"))
        full["n_beacons"] = len(matches)
        out["full"] = full
    # heading-held position fix: keep the prior heading, average the per-beacon positions
    ps = []
    for m in matches:
        a = math.radians(prior["theta_deg"] + m["det"]["bearing_deg"])
        ps.append((m["point"]["x_m"] - m["det"]["range_m"] * math.cos(a),
                   m["point"]["y_m"] - m["det"]["range_m"] * math.sin(a)))
    px, py = sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps)
    spread = max(math.hypot(p[0] - px, p[1] - py) for p in ps)
    pos = {"x_m": px, "y_m": py, "theta_deg": prior["theta_deg"], "spread_m": spread}
    pos["delta_m"] = distance(pos, prior)["d_m"]
    pos["within_prior_gate"] = pos["delta_m"] <= dv_get(dv, "position_fix_gate_m")
    # heading_safe: every beacon's bearing already agrees with the prior heading within heading_safe_deg,
    # so the position shift is not a disguised heading error (review v2 finding 18)
    head = dv_get(dv, "heading_safe_deg")
    pos["heading_safe"] = all(
        abs(wrap_deg(m["det"]["bearing_deg"] - predict_observation(prior, m["point"], dv=dv)["bearing_deg"])) <= head
        for m in matches)
    out["position"] = pos
    out["status"] = "ok"
    return out


def update_beacon(entry, det, pose):
    """Running mean of one beacon with one new detection seen from `pose`; baseline for confirmation."""
    new_pt = map_point(pose, det["range_m"], det["bearing_deg"])
    k = entry["n_obs"] + 1
    x = entry["x_m"] + (new_pt["x_m"] - entry["x_m"]) / k
    y = entry["y_m"] + (new_pt["y_m"] - entry["y_m"]) / k
    fs = {"x_m": entry["first_seen_from"][0], "y_m": entry["first_seen_from"][1]}
    return {"x_m": x, "y_m": y, "n_obs": k, "baseline_m": distance(fs, pose)["d_m"]}


def exploration_summary(pose, beacons, scan_points, blocked_heading_deg=None, dv=None):
    """12 map-frame sectors (sector_width_deg). Wall distance is the nearest mapped beacon
    inside that window; max_leg_moves is 1 when none lie that way, otherwise a clamped step
    count. new_place is true when no scan point is within new_place_m."""
    dv = dv or load_dv()
    ignore = dv_get(dv, "scan_point_ignore_m")
    lookahead = dv_get(dv, "leg_lookahead_m")
    width = dv_get(dv, "sector_width_deg")
    clearance = dv_get(dv, "sector_wall_clearance_m")
    leg_step = dv_get(dv, "sector_leg_step_m")
    max_moves = int(dv_get(dv, "sector_max_leg_moves"))
    unknown_moves = int(dv_get(dv, "sector_unknown_leg_moves"))
    weight = dv_get(dv, "interior_weight")
    new_place_m = dv_get(dv, "new_place_m")
    blocked_half = dv_get(dv, "near_blocked_deg")
    others = [p for p in scan_points if math.hypot(p[0] - pose["x_m"], p[1] - pose["y_m"]) > ignore]
    nearest = min((math.hypot(p[0] - pose["x_m"], p[1] - pose["y_m"]) for p in scan_points), default=None)
    if beacons:
        cx = sum(b["x_m"] for b in beacons) / len(beacons)
        cy = sum(b["y_m"] for b in beacons) / len(beacons)
        cdir = math.degrees(math.atan2(cy - pose["y_m"], cx - pose["x_m"]))
        cdist = math.hypot(cx - pose["x_m"], cy - pose["y_m"])
    sectors = []
    n_sectors = int(round(360.0 / width))
    for k in range(n_sectors):
        h = wrap_deg(k * width)
        hp = {"x_m": pose["x_m"], "y_m": pose["y_m"], "theta_deg": h}
        ests = [predict_observation(hp, b, dv=dv)["range_m"] for b in beacons
                if abs(predict_observation(hp, b, dv=dv)["bearing_deg"]) <= width]
        wall = min(ests) if ests else None
        if wall is None:
            moves = unknown_moves
        else:
            moves = max(0, min(max_moves, int(math.floor((wall - clearance) / leg_step))))
        blocked = moves == 0 or (
            blocked_heading_deg is not None and abs(wrap_deg(h - blocked_heading_deg)) <= blocked_half)
        ahead = (pose["x_m"] + lookahead * math.cos(math.radians(h)),
                 pose["y_m"] + lookahead * math.sin(math.radians(h)))
        nov = min((math.hypot(ahead[0] - p[0], ahead[1] - p[1]) for p in others), default=lookahead)
        interior = math.cos(math.radians(h - cdir)) if beacons and cdist > ignore else 0.0
        sectors.append({"heading_deg": h, "wall_est_m": wall, "max_leg_moves": moves, "blocked": blocked,
                        "novelty_m": nov, "interior": interior, "score": nov + weight * interior,
                        "turns": round(wrap_deg(h - pose["theta_deg"]) / width)})
    return {"nearest_scan_point_m": nearest, "new_place": nearest is None or nearest >= new_place_m,
            "sectors": sectors}
