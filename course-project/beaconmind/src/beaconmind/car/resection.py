"""The car's pose in the arena frame from the surveyed wall tags (resection), with its uncertainty.

Plan/README.md section 3.6, "Unattended batches": with nobody at the car, ground truth is no longer a tape reading
but the pose computed from the surveyed tags, at each episode's start and end from a full circle of views and at
each step from the tags in that step's picture. This module is that computation and nothing else: no I/O, no ROS.

Input: views. A view is what the camera saw from one stop: the car's pose at that stop in a reference robot frame
(for a scan: the odometry since the scan began; for a single step: the origin) and the detections there (id,
range from the axle midpoint, bearing, left positive). Every detection becomes a point in the reference frame;
points of one physical tag (same id, close together) are averaged into one. The fix is the rigid transform
(rotation and translation, no scale) that best maps those points onto the tags' surveyed positions, in closed
form (two-dimensional Procrustes).

Tag ids repeat in the layout (two tags may carry one id), so every way of assigning the seen tags to surveyed
tags of the same id is tried and the one with the smallest residual wins; a fix is refused when the runner-up is
nearly as good (within 1.5 times the best residual plus 0.10 m) and no prior pose settles it.

What the reported uncertainty is: the linearised covariance of the fit with one standard deviation per tag,
sigma = max(fit residual, range_sigma_a + range_sigma_b x range) (the design values of configs/dv.json for the
second term). It reflects noise and geometry. It does NOT reflect a common range scale error of the camera or an
error in the surveyed tag positions: both move every fix the same way and must be bounded by the tape checks the
plan keeps (the batch's first start, its last end, one spot check).

A tag surveyed wrongly is looked for separately (check_tags): when four tags or more are in one fit (a full circle,
nearly always), each is compared with where the OTHER tags put it (leave one out), and the worst one is set aside
while it is farther from its surveyed centre than its noise explains; what is left is the clean set. The batch adds
these comparisons up over all its fits (batch.TagCheck), halts on a tag that keeps disagreeing, and lets only tags
that have been compared closely enough steer a fix by themselves (`trusted`).

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this resection.
AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: added the leave-one-out tag check and the trusted-tag filter.
"""
import itertools
import math

from .odometry import wrap_deg

MIN_TAGS = 2                # two tags fix a rigid transform; one does not
CLUSTER_M = 0.40            # points of one id closer than this are one physical tag
MAX_ASSIGNMENTS = 4096


def usable_detection(det):
    """A detection with finite numbers and a positive range (anything else must never reach a pose)."""
    try:
        r, b = float(det["range_m"]), float(det["bearing_deg"])
    except (KeyError, TypeError, ValueError):
        return False
    return math.isfinite(r) and math.isfinite(b) and r > 0.0


def view_points(views):
    """Every detection of every view as a point in the reference robot frame:
    [{"id", "x", "y", "range_m", "view"}]."""
    out = []
    for index, view in enumerate(views):
        pose = view.get("pose") or {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
        for det in view["detections"]:
            if det.get("id") is None or not usable_detection(det):
                continue
            a = math.radians(pose["theta_deg"] + det["bearing_deg"])
            out.append({"id": int(det["id"]), "x": pose["x_m"] + det["range_m"] * math.cos(a),
                        "y": pose["y_m"] + det["range_m"] * math.sin(a), "range_m": float(det["range_m"]),
                        "view": index})
    return out


def group_points(points, cluster_m=CLUSTER_M):
    """One entry per physical tag seen: points of the same id within cluster_m of the group's mean are merged.
    [{"id", "x", "y", "range_m" (smallest), "n"}]."""
    groups = []
    for p in points:
        for g in groups:
            if g["id"] == p["id"] and math.hypot(g["x"] - p["x"], g["y"] - p["y"]) <= cluster_m:
                n = g["n"]
                g["x"], g["y"] = (g["x"] * n + p["x"]) / (n + 1), (g["y"] * n + p["y"]) / (n + 1)
                g["range_m"], g["n"] = min(g["range_m"], p["range_m"]), n + 1
                break
        else:
            groups.append({"id": p["id"], "x": p["x"], "y": p["y"], "range_m": p["range_m"], "n": 1})
    return groups


def solve_rigid(src, dst, weights=None):
    """(theta_rad, tx, ty) of the rotation and translation that best map the points src onto dst (weighted least
    squares), and the weighted root-mean-square residual."""
    n = len(src)
    w = weights or [1.0] * n
    total = sum(w)
    sx = sum(wi * p[0] for wi, p in zip(w, src)) / total
    sy = sum(wi * p[1] for wi, p in zip(w, src)) / total
    dx = sum(wi * p[0] for wi, p in zip(w, dst)) / total
    dy = sum(wi * p[1] for wi, p in zip(w, dst)) / total
    a = b = 0.0
    for wi, p, q in zip(w, src, dst):
        px, py, qx, qy = p[0] - sx, p[1] - sy, q[0] - dx, q[1] - dy
        a += wi * (px * qx + py * qy)
        b += wi * (px * qy - py * qx)
    theta = math.atan2(b, a)
    c, s = math.cos(theta), math.sin(theta)
    tx, ty = dx - (c * sx - s * sy), dy - (s * sx + c * sy)
    sq = 0.0
    for wi, p, q in zip(w, src, dst):
        ex, ey = c * p[0] - s * p[1] + tx - q[0], s * p[0] + c * p[1] + ty - q[1]
        sq += wi * (ex * ex + ey * ey)
    return theta, tx, ty, math.sqrt(sq / total)


def _inverse3(m):
    (a, b, c), (d, e, f), (g, h, i) = m
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if abs(det) < 1e-18:
        return None
    return [[(e * i - f * h) / det, (c * h - b * i) / det, (b * f - c * e) / det],
            [(f * g - d * i) / det, (a * i - c * g) / det, (c * d - a * f) / det],
            [(d * h - e * g) / det, (b * g - a * h) / det, (a * e - b * d) / det]]


def _covariance(groups, theta, sigmas):
    """Covariance of (tx, ty, theta) for residuals R(theta) s + t - d with one sigma per point."""
    c, s = math.cos(theta), math.sin(theta)
    info = [[0.0] * 3 for _ in range(3)]
    for g, sigma in zip(groups, sigmas):
        jx = (1.0, 0.0, -s * g["x"] - c * g["y"])
        jy = (0.0, 1.0, c * g["x"] - s * g["y"])
        for row in (jx, jy):
            for i in range(3):
                for j in range(3):
                    info[i][j] += row[i] * row[j] / (sigma * sigma)
    return _inverse3(info)


CHECK_MIN_TAGS = 4          # a tag is compared with at least three others (two others fix nothing to compare with)


def _predict(groups, src, dst, weights, sig, i, base):
    """Where the tags of `base` (indices, i not among them) put tag i, as the error vector from its surveyed centre,
    and the per-axis sigma of that comparison: tag i's own noise and the uncertainty of the fit at tag i."""
    others = [j for j in base if j != i]
    theta, tx, ty, rms = solve_rigid([src[j] for j in others], [dst[j] for j in others], [weights[j] for j in others])
    c, s = math.cos(theta), math.sin(theta)
    x, y = src[i]
    ex, ey = c * x - s * y + tx - dst[i][0], s * x + c * y + ty - dst[i][1]
    cov = _covariance([groups[j] for j in others], theta, [max(rms, sig[j]) for j in others])
    if cov is None:
        return (ex, ey), float("inf")
    var = 0.0
    for row in ((1.0, 0.0, -s * x - c * y), (0.0, 1.0, c * x - s * y)):
        var += sum(row[a] * cov[a][b] * row[b] for a in range(3) for b in range(3))
    return (ex, ey), math.sqrt(sig[i] ** 2 + max(var, 0.0) / 2.0)


def check_tags(groups, combo, sigma_a_m, sigma_b, k=4.0, min_m=0.15):
    """Is every tag of this fit where the others say it is? groups: the tags seen (resect's groups), combo: the
    surveyed tag each was assigned to. Each tag is compared with the fit of the others (leave one out); while the
    worst exceeds its limit max(min_m, k sigma) and more than three would remain, it is set aside, and the rest are
    compared again among themselves. A tag set aside is then compared with the fit of the clean rest.

    Returns {"tags": [{"tag", "id", "dx_m", "dy_m", "residual_m", "sigma_m", "limit_m", "range_m", "outlier"}],
    "outliers": [tags set aside], "resolved": False when four or fewer tags still disagree (no clean reference)}.
    Positive dx, dy: the other tags see this tag at a larger x, y than the world file has it."""
    n = len(groups)
    src = [(g["x"], g["y"]) for g in groups]
    dst = [(tag["x_m"], tag["y_m"]) for _, tag in combo]
    sig = [sigma_a_m + sigma_b * g["range_m"] for g in groups]
    weights = [1.0 / (v * v) for v in sig]
    kept, removed = list(range(n)), []
    while True:
        res = {i: _predict(groups, src, dst, weights, sig, i, kept) for i in kept}
        score = {i: math.hypot(*res[i][0]) / max(min_m, k * res[i][1]) for i in kept}
        worst = max(kept, key=lambda i: score[i])
        if score[worst] <= 1.0 or len(kept) <= 3:
            break
        kept.remove(worst)
        removed.append(worst)
    resolved = all(score[i] <= 1.0 for i in kept)
    rows = []
    for i in range(n):
        (ex, ey), sigma = res[i] if i in kept else _predict(groups, src, dst, weights, sig, i, kept)
        tag = combo[i][1]
        rows.append({"tag": tag.get("uid", tag["id"]), "id": int(tag["id"]), "dx_m": round(ex, 4), "dy_m": round(ey, 4),
                     "residual_m": round(math.hypot(ex, ey), 4), "sigma_m": round(sigma, 4),
                     "limit_m": round(max(min_m, k * sigma), 4), "range_m": round(groups[i]["range_m"], 3),
                     "outlier": i in removed})
    return {"tags": rows, "outliers": [rows[i]["tag"] for i in removed], "resolved": resolved}


def resect(views, tags, prior=None, sigma_a_m=0.05, sigma_b=0.05, rms_max_m=0.15, ambiguity_ratio=1.5,
           prior_gate_m=0.5, prior_gate_deg=25.0, max_range_m=None, tag_check=None, trusted=None):
    """The pose of the reference robot frame in the arena frame, or a refusal.

    views: [{"pose": {x_m, y_m, theta_deg} or None, "detections": [{id, range_m, bearing_deg}]}].
    tags: the surveyed tags [{"id", "x_m", "y_m", ("uid")}] in the arena frame.
    prior: {x_m, y_m, theta_deg} where the car is believed to be, or None. With a prior, a fix farther from it
    than the gates is refused ("far_from_prior"), and the prior settles which of two tags with one id was seen.
    max_range_m: detections beyond it are ignored (the detector's trusted range).
    tag_check: {"k", "min_m"} to compare every tag with the others when CHECK_MIN_TAGS or more are in the fit and the
    assignment of repeated ids is not ambiguous (check_tags); the result is under "check", on a refusal too.
    trusted: a set of tag uids, or None. The assignment uses every surveyed tag (so a repeated id is never given to
    the wrong copy because the right one is not trusted), then only trusted tags enter the pose.

    Returns {"ok": True, "pose": {x_m, y_m, theta_deg}, "sigma_xy_m", "sigma_theta_deg", "rms_m", "n_tags",
    "n_points", "tags": [uids or ids], "runner_up_rms_m", "check", "untrusted"} or {"ok": False, "why": ...,
    "n_tags": ...}."""
    points = view_points(views)
    if max_range_m is not None:
        points = [p for p in points if p["range_m"] <= max_range_m]
    known = {}
    for index, tag in enumerate(tags):
        known.setdefault(int(tag["id"]), []).append((index, tag))
    groups = [g for g in group_points(points) if g["id"] in known]
    if len(groups) < MIN_TAGS:
        return {"ok": False, "why": "fewer than %d surveyed tags in view" % MIN_TAGS, "n_tags": len(groups)}
    choices = [known[g["id"]] for g in groups]
    count = 1
    for c in choices:
        count *= len(c)
    if count > MAX_ASSIGNMENTS:
        return {"ok": False, "why": "too many ways to assign repeated ids (%d)" % count, "n_tags": len(groups)}
    src = [(g["x"], g["y"]) for g in groups]
    weights = [1.0 / (sigma_a_m + sigma_b * g["range_m"]) ** 2 for g in groups]
    solutions = []
    for combo in itertools.product(*choices):
        if len({index for index, _ in combo}) != len(combo):
            continue                    # two seen tags cannot be the same surveyed tag
        dst = [(tag["x_m"], tag["y_m"]) for _, tag in combo]
        theta, tx, ty, rms = solve_rigid(src, dst, weights)
        pose = {"x_m": tx, "y_m": ty, "theta_deg": wrap_deg(math.degrees(theta))}
        far = None
        if prior is not None:
            far = (math.hypot(tx - prior["x_m"], ty - prior["y_m"]) > prior_gate_m
                   or abs(wrap_deg(pose["theta_deg"] - prior["theta_deg"])) > prior_gate_deg)
        solutions.append({"rms": rms, "pose": pose, "theta": theta, "combo": combo, "far": far})
    if not solutions:
        return {"ok": False, "why": "no consistent assignment of the tags seen", "n_tags": len(groups)}
    if prior is not None:
        near = [s for s in solutions if not s["far"]]
        if not near:
            best = min(solutions, key=lambda s: s["rms"])
            return {"ok": False, "why": "far_from_prior", "n_tags": len(groups), "pose": best["pose"],
                    "rms_m": best["rms"]}
        solutions = near
    solutions.sort(key=lambda s: s["rms"])
    best = solutions[0]
    runner_up = solutions[1]["rms"] if len(solutions) > 1 else None
    ambiguous = runner_up is not None and runner_up < ambiguity_ratio * best["rms"] + 0.10
    check = None
    if tag_check is not None and len(groups) >= CHECK_MIN_TAGS and not ambiguous:
        check = check_tags(groups, best["combo"], sigma_a_m, sigma_b, k=tag_check.get("k", 4.0),
                           min_m=tag_check.get("min_m", 0.15))
    if best["rms"] > rms_max_m:
        return {"ok": False, "why": "residual %.2f m above %.2f m" % (best["rms"], rms_max_m), "n_tags": len(groups),
                "rms_m": best["rms"], "check": check}
    if ambiguous:
        return {"ok": False, "why": "ambiguous: two assignments of repeated ids fit about equally well",
                "n_tags": len(groups), "rms_m": best["rms"], "runner_up_rms_m": runner_up}
    use = list(range(len(groups)))
    untrusted = []
    if trusted is not None:
        use = [i for i, (_, tag) in enumerate(best["combo"]) if tag.get("uid", tag["id"]) in trusted]
        untrusted = [tag.get("uid", tag["id"]) for i, (_, tag) in enumerate(best["combo"]) if i not in use]
        if len(use) < MIN_TAGS:
            return {"ok": False, "why": "fewer than %d checked tags in view" % MIN_TAGS, "n_tags": len(use),
                    "untrusted": untrusted, "check": check}
    theta, rms, pose = best["theta"], best["rms"], best["pose"]
    if untrusted:                       # the same assignment, without the tags not yet checked
        theta, tx, ty, rms = solve_rigid([(groups[i]["x"], groups[i]["y"]) for i in use],
                                         [(best["combo"][i][1]["x_m"], best["combo"][i][1]["y_m"]) for i in use],
                                         [weights[i] for i in use])
        pose = {"x_m": tx, "y_m": ty, "theta_deg": wrap_deg(math.degrees(theta))}
        if prior is not None and (math.hypot(tx - prior["x_m"], ty - prior["y_m"]) > prior_gate_m
                                  or abs(wrap_deg(pose["theta_deg"] - prior["theta_deg"])) > prior_gate_deg):
            return {"ok": False, "why": "far_from_prior", "n_tags": len(use), "pose": pose, "rms_m": rms,
                    "untrusted": untrusted, "check": check}
    sigmas = [max(rms, sigma_a_m + sigma_b * groups[i]["range_m"]) for i in use]
    cov = _covariance([groups[i] for i in use], theta, sigmas)
    if cov is None or cov[0][0] < 0 or cov[1][1] < 0 or cov[2][2] < 0:
        return {"ok": False, "why": "degenerate geometry", "n_tags": len(use), "rms_m": rms, "check": check}
    return {"ok": True, "pose": pose, "sigma_xy_m": math.sqrt(cov[0][0] + cov[1][1]),
            "sigma_theta_deg": math.degrees(math.sqrt(cov[2][2])), "rms_m": rms, "n_tags": len(use),
            "n_points": len(points), "tags": [best["combo"][i][1].get("uid", best["combo"][i][1]["id"]) for i in use],
            "runner_up_rms_m": runner_up, "check": check, "untrusted": untrusted}


def position_fix(detections, tags, prior, prior_sigma_theta_deg, sigma_a_m=0.05, sigma_b=0.05, bearing_sigma_deg=2.0,
                 gate_m=0.5, max_range_m=None, trusted=None):
    """A position (not a heading) from a single view, using the heading the car is believed to have: each tag in
    view puts the car at (tag position) - (range, bearing) turned by that heading. One tag is enough. A tag with a
    repeated id is taken as the surveyed tag that puts the car nearest the prior; estimates farther than gate_m
    from the prior are dropped.

    trusted: a set of tag uids, or None: a detection whose tag (chosen among all surveyed tags of its id) is not in
    it gives no estimate (and is not counted as far from the prior).

    Returns {"ok": True, "kind": "position", "pose": {x_m, y_m, theta_deg (the prior's)}, "sigma_xy_m", "n_tags"}
    or {"ok": False, "why": ...}. The uncertainty of each estimate is the range noise and the heading and bearing
    uncertainty swung over the range; estimates are averaged by inverse variance."""
    total = wx = wy = 0.0
    used, dropped, names, untrusted = 0, 0, [], []
    for det in detections:
        if det.get("id") is None or not usable_detection(det) or (max_range_m is not None and det["range_m"] > max_range_m):
            continue
        a = math.radians(prior["theta_deg"] + det["bearing_deg"])
        best = None
        for tag in tags:
            if int(tag["id"]) != int(det["id"]):
                continue
            x, y = tag["x_m"] - det["range_m"] * math.cos(a), tag["y_m"] - det["range_m"] * math.sin(a)
            dist = math.hypot(x - prior["x_m"], y - prior["y_m"])
            if best is None or dist < best[0]:
                best = (dist, x, y, tag.get("uid", tag["id"]))
        if best is None:
            continue
        if trusted is not None and best[3] not in trusted:
            untrusted.append(best[3])
            continue
        if best[0] > gate_m:
            dropped += 1
            continue
        names.append(best[3])
        swing = det["range_m"] * math.radians(math.hypot(prior_sigma_theta_deg, bearing_sigma_deg))
        sigma = math.hypot(sigma_a_m + sigma_b * det["range_m"], swing)
        w = 1.0 / (sigma * sigma)
        total, wx, wy, used = total + w, wx + w * best[1], wy + w * best[2], used + 1
    if not used:
        why = "far_from_prior" if dropped else ("no checked tag in view" if untrusted else "no surveyed tag in view")
        out = {"ok": False, "why": why, "n_tags": 0}
        if untrusted:
            out["untrusted"] = untrusted
        return out
    return {"ok": True, "kind": "position", "pose": {"x_m": wx / total, "y_m": wy / total, "theta_deg": prior["theta_deg"]},
            "sigma_xy_m": math.sqrt(1.0 / total), "sigma_theta_deg": None, "n_tags": used, "tags": names,
            "untrusted": untrusted}

