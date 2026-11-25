"""The halt of b2-real-01 (2026-11-25) from its text records: the range check over its forward moves, the
dead-reckoning drift of the transit and of episode 1 under several hypotheses, where along the episode it grew, and
the circles refitted with the gyro's turn angles scaled.

usage (course-project/beaconmind, PYTHONPATH=src): python3 analyse.py BATCH_DIR WORLD_JSON
BATCH_DIR: data/batches/b2-real-01 (copied read-only from the Spark; text records only, no frames).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this analysis of the b2-real-01 halt."""
import json, math, os, sys
from beaconmind.car import batch as B
from beaconmind.car.backend import compose
from beaconmind.car.resection import resect

batch, world_path = sys.argv[1], sys.argv[2]
ep = os.path.join(batch, "episodes", "ep01-a1")
world = json.load(open(world_path))
tags = [{"id": t["id"], "uid": t.get("uid"), "x_m": t["x_m"], "y_m": t["y_m"]} for t in world["tags"]]
m = json.load(open(os.path.join(batch, "manifest.json")))
e = m["episodes"][0]


def rows(name):
    return [json.loads(l) for l in open(os.path.join(ep, name))]


pre, epi, post = rows("pre/steps.jsonl"), rows("backend/steps.jsonl"), rows("post/steps.jsonl")
tr_pre, tr_ep = rows("pre/truth.jsonl"), rows("truth.jsonl")

print("== halt:", m["halt"]["detail"])
print("== 1. the range check (the batch's own code, the pilot's range bias removed)")
params = B.BatchParams(world_path="x", start_poses=[], initial_pose={"x_m": 0, "y_m": 0, "theta_deg": 0}, max_range_m=3.0,
                       range_bias_a_m=0.00492, range_bias_b=-0.01658, range_min_m=0.785)
env = B.BatchEnv.__new__(B.BatchEnv)
env.params, env.tags = params, tags
env.tracker = B.PoseTracker({"x_m": 0, "y_m": 0, "theta_deg": 0}, 0.05, 2.0)
for part, st, tr in (("pre", pre, tr_pre), ("episode", epi, tr_ep)):
    env.range_before, prev = None, None
    for i, r in enumerate(st):
        o = r.get("odometry_exact")
        env.tracker.pose = compose(prev, o) if (prev is not None and o) else dict(tr[i]["tracked_world"]["pose"])
        n = len(env.tracker.range_moves)
        env._range_check(o, r["sense"], r, i == 0)
        if len(env.tracker.range_moves) > n:
            s_, k = env.tracker.range_moves[-1]
            print("   %-7s step %2d forward %.3f m: tags over odometry %.3f (%d pairs)" % (part, r["step"], o["forward_m"], s_, k))
        prev = dict(tr[i]["tracked_world"]["pose"])
print("   median %.3f over %d forward moves (%d pairs); halt: %s" % (env.tracker.range_scale() + (B.range_scale_halt(env.tracker, params),)))

print("== 2. the circles")
for k in ("first_fix", "start_fix", "end_fix"):
    f = e[k]
    print("   %-9s %2d tags, rms %.3f m, sigma %.3f m, pose after the circle (%.3f, %.3f, %.1f)" % (
        k, f["n_tags"], f["rms_m"], f["sigma_xy_m"], f["pose_now"]["x_m"], f["pose_now"]["y_m"], f["pose_now"]["theta_deg"]))
print("   transit as recorded:", e.get("odometry_scale_check"))
print("   episode as recorded:", e.get("odometry_scale_check_episode"))


def kind(o):
    return "turn" if abs(o["dtheta_deg"]) > 15 else ("straight" if abs(o["forward_m"]) > 0.05 else "none")


def dr(rs, start, turn_xy=1.0, gyro=1.0, slip_steps=(), slip=1.0):
    p = dict(start)
    for part, r in rs:
        o = r.get("odometry_exact")
        if not o:
            continue
        f, l = o["forward_m"], o["left_m"]
        if kind(o) == "turn":
            f, l = f * turn_xy, l * turn_xy
        if part == "episode" and r["step"] in slip_steps:
            f, l = f * slip, l * slip
        p = compose(p, {"forward_m": f, "left_m": l, "dtheta_deg": o["dtheta_deg"] * gyro})
    return p


def show(name, rs, start, end, **kw):
    p = dr(rs, start, **kw)
    d_od = math.hypot(p["x_m"] - start["x_m"], p["y_m"] - start["y_m"])
    d_t = math.hypot(end["x_m"] - start["x_m"], end["y_m"] - start["y_m"])
    print("   %-44s miss %.3f m (dx %+.3f, dy %+.3f), heading %+5.1f deg, by odometry %.3f m, by tags %.3f m, ratio %.3f" % (
        name, math.hypot(end["x_m"] - p["x_m"], end["y_m"] - p["y_m"]), end["x_m"] - p["x_m"], end["y_m"] - p["y_m"],
        B.wrap_deg(end["theta_deg"] - p["theta_deg"]), d_od, d_t, d_t / d_od))


print("== 3. dead reckoning under hypotheses")
transit = [("pre", r) for r in pre]
episode = [("episode", r) for r in epi] + [("post", r) for r in post]
print("   transit (first circle to start circle):")
show("as recorded", transit, e["first_fix"]["pose"], e["start_fix"]["pose_now"])
show("gyro turn angles x1.0075", transit, e["first_fix"]["pose"], e["start_fix"]["pose_now"], gyro=1.0075)
print("   episode (start circle to end circle):")
s0, s1 = e["start_fix"]["pose_now"], e["end_fix"]["pose_now"]
show("as recorded", episode, s0, s1)
show("turns in place (no axle shift)", episode, s0, s1, turn_xy=0.0)
show("turn shift x2", episode, s0, s1, turn_xy=2.0)
show("gyro turn angles x1.0079", episode, s0, s1, gyro=1.0079)
show("steps 24-26 at 0.86 of their odometry", episode, s0, s1, slip_steps={24, 25, 26}, slip=0.86)
show("steps 24-26 at 0.80 of their odometry", episode, s0, s1, slip_steps={24, 25, 26}, slip=0.80)

print("== 4. along the episode: odometry alone from the start circle against the step fixes")
p = dict(s0)
for r, t in zip(epi, tr_ep):
    o = r.get("odometry_exact")
    if o:
        p = compose(p, o)
    vf = t.get("view_fix") or {}
    ex = (r.get("executed") or {})
    yaw = (ex.get("diag") or {}).get("yaw_disagree_deg")
    if vf.get("ok") or (t.get("action") or "").startswith("FORWARD"):
        fp = vf.get("pose")
        print("   row %2d %-12s odometry (%.2f, %.2f)%s%s" % (
            t["row"], t.get("action"), p["x_m"], p["y_m"],
            "  fix %-14s (%.2f, %.2f) fix - odometry (%+.2f, %+.2f)" % (",".join(vf.get("tags") or []), fp["x_m"], fp["y_m"], fp["x_m"] - p["x_m"], fp["y_m"] - p["y_m"]) if fp else "",
            "  wheel/gyro yaw disagreement %.1f deg" % yaw if yaw is not None and (t.get("action") or "").startswith("FORWARD") else ""))
print("   end circle (%.2f, %.2f): - odometry (%+.2f, %+.2f)" % (s1["x_m"], s1["y_m"], s1["x_m"] - p["x_m"], s1["y_m"] - p["y_m"]))

print("== 5. the circles refitted with the gyro's turn angles scaled (rows of each circle from the step logs)")


def refit(rs, k):
    views, q = [], {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
    for i, r in enumerate(rs):
        o = r.get("odometry_exact")
        if i > 0 and o:
            q = compose(q, {"forward_m": o["forward_m"], "left_m": o["left_m"], "dtheta_deg": o["dtheta_deg"] * k})
        views.append({"pose": dict(q), "detections": [d for d in r["sense"]["detections"] if d.get("id") is not None]})
    return resect(views, tags, prior=None, sigma_a_m=0.0062, sigma_b=0.0378, max_range_m=3.0)


for name, rs in (("first circle", pre[1:14]), ("start circle", pre[-13:]), ("end circle", post[:13])):
    print("   %-12s %s" % (name, "; ".join("x%.3f rms %.3f" % (k, refit(rs, k)["rms_m"]) for k in (1.0, 1.005, 1.01, 1.015, 1.02))))
