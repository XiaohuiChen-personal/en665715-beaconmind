"""The halt of b2-real-02 (2026-11-25) from its text records: the range check per forward move (by heading and by
time), the dead-reckoning drift records, the per-step fix statistic replayed with what drove it, the S3 transit
between its two circles under several hypotheses, B2's own estimate against the truth in episode 2, and the physical
checks (stall, slip flags, telemetry, frames).

usage (course-project/beaconmind, PYTHONPATH=src): python3 analyse.py BATCH_DIR WORLD_JSON
BATCH_DIR: data/batches/b2-real-02 (copied read-only from the Spark; text records only, no frames).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this analysis of the b2-real-02 halt."""
import collections, glob, json, math, os, statistics, sys
from beaconmind.car import batch as B
from beaconmind.car.backend import compose
from beaconmind.car.odometry import wrap_deg

batch, world_path = sys.argv[1], sys.argv[2]
world = json.load(open(world_path))
tags = [{"id": t["id"], "uid": t.get("uid"), "x_m": t["x_m"], "y_m": t["y_m"]} for t in world["tags"]]
m = json.load(open(os.path.join(batch, "manifest.json")))
PARTS = (("pre", "pre/steps.jsonl", "pre/truth.jsonl"), ("ep", "backend/steps.jsonl", "truth.jsonl"),
         ("post", "post/steps.jsonl", "post/truth.jsonl"))
phases = []
for e in m["episodes"]:
    for part, sf, tf in PARTS:
        p = os.path.join(batch, "episodes", e["id"], sf)
        if os.path.exists(p):
            phases.append((e["id"], part, [json.loads(l) for l in open(p)],
                           [json.loads(l) for l in open(os.path.join(batch, "episodes", e["id"], tf))]))


def action(r):
    return ((r.get("executed") or {}).get("command") or {}).get("action") or "-"


print("== halt:", m["halt"]["detail"])
print("== 1. the range check per forward move (the batch's own code, the pilot's range bias removed)")
params = B.BatchParams(world_path="x", start_poses=[], initial_pose={"x_m": 0, "y_m": 0, "theta_deg": 0}, max_range_m=3.0,
                       range_bias_a_m=0.00492, range_bias_b=-0.01658, range_min_m=0.785)
env = B.BatchEnv.__new__(B.BatchEnv)
env.params, env.tags = params, tags
env.tracker = B.PoseTracker({"x_m": 0, "y_m": 0, "theta_deg": 0}, 0.05, 2.0)
rows_fwd = []
for ep, part, st, tr in phases:
    env.range_before, prev = None, None
    for i, r in enumerate(st):
        o = r.get("odometry_exact")
        env.tracker.pose = compose(prev, o) if (prev is not None and o) else dict(tr[i]["tracked_world"]["pose"])
        n = len(env.tracker.range_moves)
        env._range_check(o, r["sense"], r, i == 0)
        if action(r).startswith(("FORWARD", "BACKWARD")):
            res = (r["executed"].get("result") or {})
            diag = r["executed"].get("diag") or {}
            tw = tr[i]["tracked_world"]["pose"]
            s = env.tracker.range_moves[-1] if len(env.tracker.range_moves) > n else None
            q = (r["sense"].get("status") or {}).get("odometry_quality")
            rows_fwd.append((ep, part, r, tw, res, diag, s, q))
            print("   %s %-4s %3d %s %-11s at (%.2f, %.2f) heading %6.1f  %-5s %.2f s, peak %.3f m/s, yaw disagreement %5.1f deg, "
                  "odometry %-14s %s" % (ep[:4], part, r["step"], r["time_utc"][11:19], action(r), tw["x_m"], tw["y_m"],
                                         tw["theta_deg"], res.get("result"), res.get("duration_s") or 0,
                                         diag.get("peak_speed_mps") or 0, diag.get("yaw_disagree_deg") or 0, q,
                                         "range %.3f (%d pairs)" % s if s else ""))
        prev = dict(tr[i]["tracked_world"]["pose"])
whole, recent = env.tracker.range_scale(), env.tracker.range_scale(last=10)
print("   whole batch: median %.3f over %d moves; last 10: median %.3f; halt: %s" % (whole[0], whole[1], recent[0],
                                                                                    B.range_scale_halt(env.tracker, params)))
north = [s[0] for ep, part, r, tw, res, diag, s, q in rows_fwd if s and 30 < tw["theta_deg"] < 150]
other = [s[0] for ep, part, r, tw, res, diag, s, q in rows_fwd if s and not 30 < tw["theta_deg"] < 150]
print("   by heading: north (30 to 150 deg) n %d median %.3f; other n %d median %.3f" % (
    len(north), statistics.median(north), len(other), statistics.median(other)))
for ep in sorted({x[0] for x in rows_fwd}):
    for name, test in (("north", lambda h: 30 < h < 150), ("other", lambda h: not 30 < h < 150)):
        v = [s[0] for e, part, r, tw, res, diag, s, q in rows_fwd if e == ep and s and test(tw["theta_deg"])]
        f25 = [(res.get("duration_s"), diag.get("peak_speed_mps")) for e, part, r, tw, res, diag, s, q in rows_fwd
               if e == ep and action(r) == "FORWARD_25"]
        if v:
            print("   by time: %s %-5s n %d mean %.3f" % (ep, name, len(v), statistics.mean(v)))
    if f25:
        print("   %s FORWARD_25: mean duration %.2f s, mean peak speed %.3f m/s (%d moves)" % (
            ep, statistics.mean(d for d, _ in f25), statistics.mean(p for _, p in f25), len(f25)))

print("== 2. the dead-reckoning drift records")
for e in m["episodes"]:
    for k in ("dead_reckoning_transit", "dead_reckoning_episode"):
        d = e.get(k)
        if d and d.get("checked"):
            print("   %s %-22s ratio %.3f, miss %.3f m (world %s), heading miss %+.1f deg, circles' sigma %s" % (
                e["id"], k, d["tags_over_odometry"], d["miss_m"], d["miss_world_m"], d["heading_miss_deg"], d["circle_sigmas_xy_m"]))

print("== 3. the per-step fix statistic replayed, and what drove it")
prev, leg, acts = None, [0.0, 0.0], []
sxy = sxx = total = 0.0
n = 0
contrib = []
for ep, part, st, tr in phases:
    for r, t in zip(st, tr):
        tw = t["tracked_world"]
        o = r.get("odometry_exact")
        if prev is None:
            prev, prev_sig = dict(tw["pose"]), tw["sigma_xy_m"]
            continue
        pred = compose(prev, o) if o else dict(prev)
        leg[0] += pred["x_m"] - prev["x_m"]
        leg[1] += pred["y_m"] - prev["y_m"]
        acts.append(action(r))
        vf = t.get("view_fix") or {}
        moved = math.hypot(tw["pose"]["x_m"] - pred["x_m"], tw["pose"]["y_m"] - pred["y_m"])
        fix = (vf["pose"], vf["sigma_xy_m"], "view " + ",".join(vf.get("tags") or [])) if vf.get("ok") else \
            ((tw["pose"], tw["sigma_xy_m"], "circle") if moved > 0.005 else None)
        if fix:
            L = math.hypot(*leg)
            if L >= 0.05:
                innov = ((fix[0]["x_m"] - pred["x_m"]) * leg[0] + (fix[0]["y_m"] - pred["y_m"]) * leg[1]) / L
                var = max(fix[1], 0.01) ** 2 + prev_sig ** 2
                sxy += L * innov / var
                sxx += L * L / var
                total += L
                n += 1
                contrib.append((L * innov / var, ep, part, t["row"], fix[2], L, math.degrees(math.atan2(leg[1], leg[0])),
                                innov, fix[1], sum(a.startswith("FORWARD") for a in acts), sum(a.startswith("TURN") for a in acts)))
            leg, acts = [0.0, 0.0], []
        prev, prev_sig = dict(tw["pose"]), tw["sigma_xy_m"]
print("   replayed: %+.1f %% +- %.1f %% over %.1f m, %d fixes" % (100 * sxy / sxx, 100 / math.sqrt(sxx), total, n))
tot = sum(c[0] for c in contrib)
for c in sorted(contrib)[:10]:
    print("   %5.0f %% of it: %s %-4s row %3d %-24s leg %.3f m at %6.1f deg (%d forward, %d turns), fix %+.3f m along it, "
          "fix sigma %.3f" % (100 * c[0] / tot, c[1][:4], c[2], c[3], c[4][:24], c[5], c[6], c[9], c[10], c[7], c[8]))
byph = collections.defaultdict(float)
for c in contrib:
    byph["%s %s" % (c[1], c[2])] += c[0]
print("   share by phase:", {k: "%.0f %%" % (100 * v / tot) for k, v in byph.items()})

print("== 4. the S3 transit between its two circles (episode 3, pre)")
st, tr = [(s, t) for ep, part, s, t in phases if ep == "ep03-a1" and part == "pre"][0]
sets, prev = [], None
for i, (r, t) in enumerate(zip(st, tr)):
    o = r.get("odometry_exact")
    if prev is not None and o:
        pred = compose(prev, o)
        if math.hypot(t["tracked_world"]["pose"]["x_m"] - pred["x_m"], t["tracked_world"]["pose"]["y_m"] - pred["y_m"]) > 0.005 \
                and not (t.get("view_fix") or {}).get("ok"):
            sets.append(i)
    prev = dict(t["tracked_world"]["pose"])
a, b = sets[0], sets[-1]
s0, s1 = tr[a]["tracked_world"]["pose"], tr[b]["tracked_world"]["pose"]
print("   circles at rows %d and %d: (%.2f, %.2f) to (%.2f, %.2f)" % (tr[a]["row"], tr[b]["row"], s0["x_m"], s0["y_m"], s1["x_m"], s1["y_m"]))


def dr(fwd=1.0, gyro=1.0, turn_xy=1.0):
    p = dict(s0)
    for r in st[a + 1:b + 1]:
        o = r.get("odometry_exact")
        if not o:
            continue
        k = fwd if action(r).startswith("FORWARD") else (turn_xy if action(r).startswith("TURN") else 1.0)
        p = compose(p, {"forward_m": o["forward_m"] * k, "left_m": o["left_m"] * k, "dtheta_deg": o["dtheta_deg"] * gyro})
    return p


nf = sum(action(r).startswith("FORWARD") for r in st[a + 1:b + 1])
nt = sum(action(r).startswith("TURN") for r in st[a + 1:b + 1])
for name, kw in (("as recorded", {}), ("forward moves x0.83", {"fwd": 0.83}), ("forward moves x0.70", {"fwd": 0.70}),
                 ("gyro x1.009", {"gyro": 1.009}), ("turns in place", {"turn_xy": 0.0})):
    p = dr(**kw)
    d_od = math.hypot(p["x_m"] - s0["x_m"], p["y_m"] - s0["y_m"])
    d_t = math.hypot(s1["x_m"] - s0["x_m"], s1["y_m"] - s0["y_m"])
    print("   %-22s (%d forward, %d turns) by odometry %.3f m, by circles %.3f m, ratio %.3f, miss (%+.3f, %+.3f) m, heading %+.1f deg" % (
        name, nf, nt, d_od, d_t, d_t / d_od, s1["x_m"] - p["x_m"], s1["y_m"] - p["y_m"], wrap_deg(s1["theta_deg"] - p["theta_deg"])))

print("== 5. episode 2: B2's own estimate against the truth (map frame)")
for r in (json.loads(l) for l in open(os.path.join(batch, "episodes", "ep02-a1", "seed_2.jsonl"))):
    est, t = r.get("estimate_pose"), r["truth"]
    if est and t and r["step"] % 5 == 0 or r["step"] in (16, 31, 61):
        if est and t:
            print("   step %2d B2 (%.2f, %.2f) truth (%.2f, %.2f) %s: error %.3f m" % (
                r["step"], est["x_m"], est["y_m"], t["x_m"], t["y_m"], "tag fix" if t.get("fix") else "tracked",
                math.hypot(est["x_m"] - t["x_m"], est["y_m"] - t["y_m"])))
e2 = [e for e in m["episodes"] if e["id"] == "ep02-a1"][0]
print("   final_pose_error %s; tracked_minus_end_scan %s; end circle %d tags, rms %.3f m" % (
    e2["final_pose_error"], e2["tracked_minus_end_scan"], e2["end_fix"]["n_tags"], e2["end_fix"]["rms_m"]))

print("== 6. physical checks")
results, stall, bump, slip, ages, rx, frames, blank = collections.Counter(), 0, 0, [], [], [], collections.Counter(), []
for ep, part, st, tr in phases:
    for r in st:
        res = (r.get("executed") or {}).get("result") or {}
        if r.get("executed"):
            results[res.get("result")] += 1
        stall += bool(res.get("stall"))
        bump += bool(res.get("bump"))
        if (r["sense"].get("status") or {}).get("odometry_quality") == "slip_suspected":
            slip.append("%s %s row %d %s" % (ep[:4], part, r["step"], action(r)))
        cs = r.get("car_state") or {}
        ages.append(cs.get("telemetry_age_s") or 0)
        rx.append(cs.get("agent_rx_age_ms") or 0)
        frames[len(r.get("frames") or [])] += 1
        counts = [len(p.get("detections") or []) for p in (r.get("per_frame") or [])]
        for i, c in enumerate(counts):
            if c == 0 and sum(1 for o in counts[:i] + counts[i + 1:] if o >= 2) >= 3:
                blank.append("%s %s row %d, frames %s, step's tags %s" % (ep[:4], part, r["step"], counts,
                                                                         [d["id"] for d in r["sense"]["detections"]]))
last = phases[-1][2][-1].get("car_state") or {}
print("   move results %s; stall %d, bump %d; slip_suspected %d: %s" % (dict(results), stall, bump, len(slip), slip))
print("   telemetry age max %.3f s; agent receive age max %d ms; car state at the end: cutoffs %s, boots %s, lost_samples %s, "
      "vsys_min_mv %s" % (max(ages), max(rx), last.get("cutoffs"), last.get("boots"), last.get("lost_samples"), last.get("vsys_min_mv")))
print("   frames per step %s; frames that lost every tag their four siblings saw: %d %s" % (dict(frames), len(blank), blank))
