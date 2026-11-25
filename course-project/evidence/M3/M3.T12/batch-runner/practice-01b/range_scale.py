"""Encoder scale from ranges along the motion: for each straight move, the tags seen before and after it, the range
after the move against the range the odometry predicts. Reads a batch's episode step logs (pre/ and backend/).
usage: python3 range_scale.py EPISODE_DIR [--bias]   (EPISODE_DIR: data/batches/practice-01b/episodes/ep01-a1 on
the Spark, read-only; --bias removes the tag pilot's range bias first)

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this check of the practice batch's odometry_scale halt."""
import json, math, sys

ep = sys.argv[1]
bias = "--bias" in sys.argv


def corr(xy):
    if not bias:
        return xy
    r = math.hypot(*xy)
    t = r * 1.01658 - 0.00492           # tag pilot: true = measured - (0.00492 - 0.01658 r)
    return (xy[0] * t / r, xy[1] * t / r)


def tags(row):
    out = {}
    for d in row.get("detections_internal") or []:
        out.setdefault(d["id"], []).append(corr(tuple(d["base_xyz_m"][:2])))
    return out


num = den = 0.0
per = []
for part in ("pre", "backend"):
    rows = [json.loads(l) for l in open("%s/%s/steps.jsonl" % (ep, part))]
    for a, b in zip(rows, rows[1:]):
        odo = b.get("odometry_exact")
        if not odo or b["step"] != a["step"] + 1 or abs(odo["forward_m"]) < 0.05:
            continue
        u = (odo["forward_m"], odo["left_m"])
        before, after = tags(a), tags(b)
        for tid in before:
            if tid not in after or len(before[tid]) != 1 or len(after[tid]) != 1:
                continue
            T, A = before[tid][0], after[tid][0]
            r1, r2 = math.hypot(*T), math.hypot(*A)
            bearing = math.degrees(math.atan2(T[1], T[0]))
            uu, tu = u[0] ** 2 + u[1] ** 2, T[0] * u[0] + T[1] * u[1]
            disc = tu * tu - uu * (r1 * r1 - r2 * r2)
            if disc < 0:
                continue
            s = (tu - math.sqrt(disc)) / uu
            pred = math.hypot(T[0] - u[0], T[1] - u[1])
            # weight: how much the range change says about the scale (d r2 / d s), noise 3 mm per range pair
            g = abs(tu - uu) / max(pred, 1e-6)
            num += g * g * s
            den += g * g
            per.append((part, b["step"], tid, r1, bearing, r2, pred, s))
            print("%-7s step %2d tag %2d  before %.3f m at %+5.1f deg  after %.3f m, odometry predicts %.3f m"
                  "  -> scale (tags over odometry) %.3f" % (part, b["step"], tid, r1, bearing, r2, pred, s))
print("weighted mean tags over odometry: %.3f (%d range pairs, range bias %s)" % (num / den, len(per),
      "corrected" if bias else "not corrected"))
