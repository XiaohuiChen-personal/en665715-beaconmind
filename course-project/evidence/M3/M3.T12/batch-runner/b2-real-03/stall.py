"""The stall that halted b2-real-03 (2026-11-25): the stalled turn's telemetry sample by sample, the right wheel's
speed at the same duty in every earlier left turn of the batch, wheel speed per unit duty over the batch (a fading
battery would show), and where the car stood.

usage: python3 stall.py MOVES_DIR BATCH_DIR WORLD_JSON   (the recorder session's moves/ and data/batches/b2-real-03,
copied read-only from the Spark; run from course-project/beaconmind with PYTHONPATH=src for the last part)

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this analysis of the b2-real-03 stall."""
import glob, json, os, statistics, sys

moves_dir, batch, world_path = sys.argv[1], sys.argv[2], sys.argv[3]
TPM_L, TPM_R = 19385.0, 19804.0


def load(f):
    rows = [json.loads(l) for l in open(f)]
    return rows, [r for r in rows if r.get("ev") == "tel"], [r for r in rows if r.get("ev") == "result"][-1]["result"]


turns = sorted(glob.glob(os.path.join(moves_dir, "*TURN_LEFT_30.jsonl")))
stalled = [f for f in turns if load(f)[2]["result"] == "stalled"]
print("== the stalled move:", os.path.basename(stalled[0]))
rows, tel, res = load(stalled[0])
t0 = [r for r in rows if r.get("ev") == "start"][0]["t"]
print("   result", {k: res[k] for k in ("result", "reason", "duration_s", "enc_left_ticks", "enc_right_ticks", "gyro_dyaw_deg", "stall", "bump")})
prev = None
for r in rows:
    if r.get("ev") == "cmd":
        print("   t %+.3f command w %.3f rad/s" % (r["t"] - t0, r["w"]))
    elif r.get("ev") == "tel":
        v = ""
        if prev:
            dt = r["t_rx"] - prev["t_rx"]
            v = "left %+.3f right %+.3f m/s" % ((r["l"] - prev["l"]) / dt / TPM_L, (r["r"] - prev["r"]) / dt / TPM_R)
        print("   t %+.3f counts left %+6d right %+6d  %-30s yaw %7.2f  duty %s  cut %s" % (
            r["t_rx"] - t0, r["l"] - tel[0]["l"], r["r"] - tel[0]["r"], v, r["yaw"], r["duty"], r["cut"]))
        prev = r
    elif r.get("ev") == "stop":
        print("   t %+.3f STOP %s %s" % (r["t"] - t0, r.get("result"), r.get("reason")))

print("== the right wheel at the slow end of every left turn (its duty 0.28 to 0.31)")
mins, eff = [], []
for f in turns:
    rows, tel, res = load(f)
    v_end, e_l, e_r = [], [], []
    for a, b in zip(tel, tel[1:]):
        dt = b["t_rx"] - a["t_rx"]
        if dt <= 0:
            continue
        vl, vr = (b["l"] - a["l"]) / dt / TPM_L, (b["r"] - a["r"]) / dt / TPM_R
        dl, dr = b["duty"]
        if 0.28 <= dr <= 0.31:
            v_end.append(vr)
        if abs(dl) >= 0.28:
            e_l.append(abs(vl) / abs(dl))
        if abs(dr) >= 0.28:
            e_r.append(abs(vr) / abs(dr))
    if res["result"] != "stalled" and v_end:
        mins.append(min(v_end))
    eff.append((rows[0]["time_utc"], statistics.median(e_l) if e_l else None, statistics.median(e_r) if e_r else None, res["duration_s"]))
print("   %d earlier left turns: right-wheel minimum speed median %.3f m/s; under 0.02 m/s in %d of them (lowest %.3f)" % (
    len(mins), statistics.median(mins), sum(1 for m in mins if m < 0.02), min(mins)))
third = len(eff) // 3
for name, part in (("first third", eff[:third]), ("middle third", eff[third:2 * third]), ("last third", eff[2 * third:])):
    print("   %-12s %3d turns: wheel speed per unit duty left %.3f right %.3f m/s, duration %.2f s" % (
        name, len(part), statistics.median([p[1] for p in part if p[1]]), statistics.median([p[2] for p in part if p[2]]),
        statistics.median([p[3] for p in part])))

print("== where the car stood (the end circle of episode 2)")
from beaconmind.car import batch as B
from beaconmind.car.config import load_car
world = json.load(open(world_path))
car = load_car()
p = B.BatchParams(world_path="x", start_poses=[], initial_pose={"x_m": 0, "y_m": 0, "theta_deg": 0})
g = B.MoveGuard(world, [tuple(c) for c in car["corners"]], float(car["sweep_radius_m"]), p.wall_margin_m, p.sigma_block_m)
st = [json.loads(l) for l in open(os.path.join(batch, "episodes", "ep02-a1", "post", "steps.jsonl"))]
tr = [json.loads(l) for l in open(os.path.join(batch, "episodes", "ep02-a1", "post", "truth.jsonl"))]
for r, t in zip(st, tr):
    pose = t["tracked_world"]["pose"]
    print("   row %d %-12s tracked (%.3f, %.3f, %6.1f): axle %.2f m inside the driving area, turn room %.2f m, tags %s" % (
        t["row"], ((r.get("executed") or {}).get("command") or {}).get("action"), pose["x_m"], pose["y_m"], pose["theta_deg"],
        g.axle_depth(pose), g.axle_depth(pose) - g.sweep_radius_m, [(d["id"], d["range_m"]) for d in r["sense"]["detections"]]))
print("   car state:", {k: st[-1]["car_state"].get(k) for k in ("cutoffs", "vsys_min_mv", "lost_samples", "boots", "telemetry_age_s")})
