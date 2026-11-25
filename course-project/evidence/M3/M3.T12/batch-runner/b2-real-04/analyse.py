"""The halt of b2-real-04 (2026-11-25) from its text records: the per-step fix statistic replayed fix by fix, the
transit north to S5 between its two circles under several hypotheses (slip on the forward moves, the gyro), and the
transit's forward moves with their slip flags.

usage (course-project/beaconmind, PYTHONPATH=src): python3 analyse.py BATCH_DIR
BATCH_DIR: data/batches/b2-real-04 (copied read-only from the Spark; text records only, no frames).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this analysis of the b2-real-04 halt."""
import json, math, os, sys
from beaconmind.car.backend import compose
from beaconmind.car.odometry import wrap_deg

batch = sys.argv[1]
ep = os.path.join(batch, "episodes", "ep01-a1")
m = json.load(open(os.path.join(batch, "manifest.json")))
e = m["episodes"][0]
print("== halt:", m["halt"]["detail"])


def rows(name):
    return [json.loads(l) for l in open(os.path.join(ep, name))]


def act(r):
    return ((r.get("executed") or {}).get("command") or {}).get("action") or "-"


seq = [("pre", r, t) for r, t in zip(rows("pre/steps.jsonl"), rows("pre/truth.jsonl"))]
if os.path.exists(os.path.join(ep, "backend", "steps.jsonl")):
    seq += [("ep", r, t) for r, t in zip(rows("backend/steps.jsonl"), rows("truth.jsonl"))]
print("== 1. the per-step fix statistic, fix by fix")
prev, leg, legacts = None, [0.0, 0.0], []
sxy = sxx = tot = 0.0
n = 0
for part, r, t in seq:
    tw = t["tracked_world"]
    o = r.get("odometry_exact")
    if prev is None:
        prev, psig = dict(tw["pose"]), tw["sigma_xy_m"]
        continue
    pred = compose(prev, o) if o else dict(prev)
    leg[0] += pred["x_m"] - prev["x_m"]
    leg[1] += pred["y_m"] - prev["y_m"]
    legacts.append(act(r))
    vf = t.get("view_fix") or {}
    moved = math.hypot(tw["pose"]["x_m"] - pred["x_m"], tw["pose"]["y_m"] - pred["y_m"])
    fix = (vf["pose"], vf["sigma_xy_m"], "view " + ",".join(vf.get("tags") or []), vf.get("kind")) if vf.get("ok") else \
        ((tw["pose"], tw["sigma_xy_m"], "circle", "circle") if moved > 0.005 else None)
    if fix:
        L = math.hypot(*leg)
        if L >= 0.05:
            innov = ((fix[0]["x_m"] - pred["x_m"]) * leg[0] + (fix[0]["y_m"] - pred["y_m"]) * leg[1]) / L
            var = max(fix[1], 0.01) ** 2 + psig ** 2
            sxy += L * innov / var
            sxx += L * L / var
            tot += L
            n += 1
            print("   %-4s row %3d %-14s (%s) leg %.3f m at %6.1f deg (%d forward, %d turns): fix %+.3f m along it (%+.0f %%), "
                  "fix sigma %.3f -> %+.1f %% +- %.1f %%" % (
                      part, t["row"], fix[2], fix[3], L, math.degrees(math.atan2(leg[1], leg[0])),
                      sum(a.startswith("FORWARD") for a in legacts), sum(a.startswith("TURN") for a in legacts),
                      innov, 100 * innov / L, fix[1], 100 * sxy / sxx, 100 / math.sqrt(sxx)))
        leg, legacts = [0.0, 0.0], []
    prev, psig = dict(tw["pose"]), tw["sigma_xy_m"]
print("   replayed: %+.1f %% +- %.1f %% over %.1f m, %d fixes" % (100 * sxy / sxx, 100 / math.sqrt(sxx), tot, n))

print("== 2. the transit, first circle to start circle")
st = rows("pre/steps.jsonl")
s0, s1 = e["first_fix"]["pose"], e["start_fix"]["pose_now"]
net = sum(r["odometry_exact"]["dtheta_deg"] for r in st if r.get("odometry_exact"))
print("   recorded:", {k: e["dead_reckoning_transit"][k] for k in ("by_odometry_m", "by_tags_m", "tags_over_odometry", "miss_m", "heading_miss_deg")})
print("   %d forward moves, %d turns, %.0f deg of rotation net" % (
    sum(act(r).startswith("FORWARD") for r in st), sum(act(r).startswith("TURN") for r in st), net))


def dr(fwd=1.0, gyro=1.0):
    p = dict(s0)
    for r in st:
        o = r.get("odometry_exact")
        if not o:
            continue
        k = fwd if act(r).startswith("FORWARD") else 1.0
        p = compose(p, {"forward_m": o["forward_m"] * k, "left_m": o["left_m"] * k, "dtheta_deg": o["dtheta_deg"] * gyro})
    return p


g = 1 + e["dead_reckoning_transit"]["heading_miss_deg"] / net
for name, kw in (("as recorded", {}), ("forward x0.78 (taped)", {"fwd": 0.78}), ("gyro x%.4f (closes the heading)" % g, {"gyro": g}),
                 ("forward x0.78, that gyro", {"fwd": 0.78, "gyro": g}), ("forward x0.70, that gyro", {"fwd": 0.70, "gyro": g})):
    p = dr(**kw)
    d_od = math.hypot(p["x_m"] - s0["x_m"], p["y_m"] - s0["y_m"])
    d_t = math.hypot(s1["x_m"] - s0["x_m"], s1["y_m"] - s0["y_m"])
    print("   %-34s by odometry %.3f m, by circles %.3f m, ratio %.3f, miss (%+.3f, %+.3f) m, heading %+.1f deg" % (
        name, d_od, d_t, d_t / d_od, s1["x_m"] - p["x_m"], s1["y_m"] - p["y_m"], wrap_deg(s1["theta_deg"] - p["theta_deg"])))

print("== 3. the transit's forward moves")
for r, t in zip(st, rows("pre/truth.jsonl")):
    if act(r).startswith("FORWARD"):
        tw = t["tracked_world"]["pose"]
        print("   row %3d %s at (%.2f, %.2f) heading %6.1f: yaw disagreement %4.1f deg, odometry %s, tags %s" % (
            t["row"], act(r), tw["x_m"], tw["y_m"], tw["theta_deg"], (r["executed"].get("diag") or {}).get("yaw_disagree_deg") or 0,
            (r["sense"].get("status") or {}).get("odometry_quality"), [(d["id"], d["range_m"]) for d in r["sense"]["detections"]]))
print("   range check:", e.get("range_moves"))
