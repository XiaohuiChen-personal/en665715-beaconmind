"""Floor check 2026-11-25, recomputed from the logs: the camera measurements (median range and bearing per tag, 10
frames, tools/tagmeas.py) turned into positions and headings, against the moves' own numbers.

Positions: least squares on the RANGES only (the pilot's range bias removed: true = measured - (0.00492 - 0.01658 r)),
because ranges are good to millimetres; the heading then from the bearings at that position (bearing bias removed).
For comparison the full resection (ranges and bearings, beaconmind.car.resection.resect) as the batch runner does it.
usage: floor_analysis.py LOGDIR WORLD.json   (LOGDIR holds floor-030825.log, verify-031432.log, scale-031706.log)

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this analysis."""
import json, math, re, sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4] / "beaconmind" / "src"))
from beaconmind.car import resection as R

logdir, world_path = sys.argv[1], sys.argv[2]
world = json.load(open(world_path))
TAGS = {}
for t in world["tags"]:
    TAGS.setdefault(t["id"], []).append(t)
BIAS_A, BIAS_B, BEAR_BIAS = 0.00492, -0.01658, -0.077
LENS = 0.12
TRACK = 0.1335
SCALE_L, SCALE_R, NOMINAL = 19385.0, 19804.0, 20523.86131811904


def meas_lines(path):
    out = []
    for line in open(path):
        m = re.match(r"MEAS (\S+) (\{.*\})", line.strip())
        if m:
            out.append((m.group(1), json.loads(m.group(2))))
        m = re.match(r"MOVE (\S+).*-> (\S+).*fwd=([+-][0-9.]+) dyaw=([+-][0-9.]+) L=(-?\d+) R=(-?\d+)", line.strip())
        if m:
            out.append(("MOVE", {"action": m.group(1), "result": m.group(2), "fwd": float(m.group(3)),
                                 "dyaw": float(m.group(4)), "L": int(m.group(5)), "R": int(m.group(6))}))
    return out


def tag_for(tid, guess, rng):
    """The surveyed tag of this id (ids 0, 2, 3 are on two tags: the one whose distance from the guess best matches
    the measured range)."""
    return min(TAGS[tid], key=lambda t: abs(math.hypot(t["x_m"] - guess[0], t["y_m"] - guess[1]) - rng))


def fix(meas, guess):
    dets = [(int(k), v["range_m"], v["bearing_deg"]) for k, v in meas["tags"].items() if int(k) in TAGS]
    pts = [(tag_for(i, guess, r), r - (BIAS_A + BIAS_B * r), b - BEAR_BIAS) for i, r, b in dets]
    x, y = guess
    for _ in range(50):                         # Gauss-Newton on the ranges
        jtj = [[0.0, 0.0], [0.0, 0.0]]
        jtr = [0.0, 0.0]
        for t, r, _b in pts:
            dx, dy = x - t["x_m"], y - t["y_m"]
            d = math.hypot(dx, dy)
            g = (dx / d, dy / d)
            res = d - r
            for i in range(2):
                jtr[i] += g[i] * res
                for j in range(2):
                    jtj[i][j] += g[i] * g[j]
        det = jtj[0][0] * jtj[1][1] - jtj[0][1] * jtj[1][0]
        if abs(det) < 1e-12:
            break
        sx = (jtj[1][1] * jtr[0] - jtj[0][1] * jtr[1]) / det
        sy = (-jtj[1][0] * jtr[0] + jtj[0][0] * jtr[1]) / det
        x, y = x - sx, y - sy
        if math.hypot(sx, sy) < 1e-7:
            break
    rms = math.sqrt(sum((math.hypot(x - t["x_m"], y - t["y_m"]) - r) ** 2 for t, r, _ in pts) / len(pts))
    heads = [math.degrees(math.atan2(t["y_m"] - y, t["x_m"] - x)) - b for t, _r, b in pts]
    ref = heads[0]
    th = ref + sum(R.wrap_deg(h - ref) for h in heads) / len(heads)
    spread = max(abs(R.wrap_deg(h - th)) for h in heads)
    full = R.resect([{"pose": None, "detections": [{"id": i, "range_m": r - (BIAS_A + BIAS_B * r), "bearing_deg": b - BEAR_BIAS}
                                                     for i, r, b in dets]}], world["tags"], prior={"x_m": x, "y_m": y, "theta_deg": th},
                    sigma_a_m=0.0063, sigma_b=0.017, rms_max_m=1.0, prior_gate_m=1.0, prior_gate_deg=45.0)
    return {"x": x, "y": y, "th": R.wrap_deg(th), "rms": rms, "spread": spread, "ids": sorted(i for i, _, _ in dets),
            "full": full}


def lens(p):
    return (p["x"] + LENS * math.cos(math.radians(p["th"])), p["y"] + LENS * math.sin(math.radians(p["th"])))


def show(name, logfile, guess):
    print("=" * 100)
    print(name, logfile)
    rows = meas_lines(logfile)
    prev = None
    moves = []
    for kind, d in rows:
        if kind == "MOVE":
            moves.append(d)
            continue
        p = fix(d, guess)
        guess = (p["x"], p["y"])
        f = p["full"]
        line = "%-10s tags %-16s axle (%.3f, %.3f) heading %7.2f  range rms %.4f m, heading spread %.2f deg" % (
            kind, p["ids"], p["x"], p["y"], p["th"], p["rms"], p["spread"])
        if f.get("ok"):
            line += " | resect (%.3f, %.3f) %7.2f" % (f["pose"]["x_m"], f["pose"]["y_m"], f["pose"]["theta_deg"])
        else:
            line += " | resect: %s" % f.get("why")
        print(line)
        if prev is not None and moves:
            dist = math.hypot(p["x"] - prev["x"], p["y"] - prev["y"])
            dth = R.wrap_deg(p["th"] - prev["th"])
            L, Rr = sum(m["L"] for m in moves), sum(m["R"] for m in moves)
            enc = (L / SCALE_L + Rr / SCALE_R) / 2
            print("           since %-8s: moved %.4f m by ranges, heading %+6.2f by tags | gyro %+6.2f | odometry printed %+.4f | "
                  "counts L %d R %d -> %+.4f m at the tape scales (%+.4f at nominal)"
                  % (prev["name"], dist, dth, sum(m["dyaw"] for m in moves), sum(m["fwd"] for m in moves), L, Rr, enc,
                     (L + Rr) / 2 / NOMINAL))
        p["name"] = kind
        prev = p
        moves = []
    return rows


show("F1-F3 (floor.sh)", logdir + "/floor-030825.log", (2.37, 2.9))
show("verify (car.json = the first estimate 18555 / 19096)", logdir + "/verify-031432.log", (2.6, 1.7))
show("tape-measured straight (scale4.sh)", logdir + "/scale-031706.log", (2.37, 2.9))
