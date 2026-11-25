"""Was the northward under-travel the tag pilot's tape? The range ratio (tags over odometry) of every forward move of
the real batches b2-real-01 to 07, split by whether the move ran on the tape line, by direction of travel.

usage (repository root): python3 course-project/evidence/M3/M3.T12/batch-runner/tape/split.py LABEL=BATCH_DIR ...
BATCH_DIR: data/batches/<label> (copied read-only from the Spark; text records only).

Two sources of the ratio per move:
- "batch": the batch's own range check, as it logged it (the manifest's range_moves; b2-real-03 onward). Its pose
  x_m, y_m is the end of the move; the start is taken back along the heading by the move's odometry length.
- "recomputed": every forward move of 0.20 m or more done, from the detector's millimetre record before and after it,
  tag by tag (the pilot's range bias removed, 0.785 to 3.0 m, within 30 degrees of ahead, the id resolved to a
  surveyed tag by the tracked pose); the move's ratio is the median over its tags. This covers b2-real-01 and 02 too,
  whose manifests predate range_moves.

Two criteria for "on the tape line" (the pilot's centre line along x = 2.369, from under T03 out to y = 3.67):
- the lead's: some point of the move with the axle midpoint's x within 0.17 m of 2.37 and y between 0.7 and 3.1 (a
  wheel track crossing or riding the line);
- the b2-real-05 diagnosis's: the move passing within 0.10 m of the centre line.
Directions by the heading at mid-move: north 45-135, south 225-315, east 315-45, west 135-225 degrees.
b2-real-06 and 07 ran after Xiaohui removed the long centre line (cross strips may remain).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this split."""
import json
import math
import os
import statistics
import sys

TAPE_X, TAPE_Y0, TAPE_Y1 = 2.369, 0.071, 0.071 + 3.6
AFTER_REMOVAL = {"b2-real-06", "b2-real-07"}
HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = json.load(open(os.path.join(HERE, "..", "..", "..", "..", "..", "configs", "arenas", "real-room.json")))


def rows(path):
    return [json.loads(l) for l in open(path)] if os.path.exists(path) else []


def med(v):
    return statistics.median(v) if v else None


def points(x0, y0, x1, y1, n=21):
    return [(x0 + i / (n - 1.0) * (x1 - x0), y0 + i / (n - 1.0) * (y1 - y0)) for i in range(n)]


def on_lead(x0, y0, x1, y1):
    return any(abs(x - 2.37) <= 0.17 and 0.7 <= y <= 3.1 for x, y in points(x0, y0, x1, y1))


def on_diag(x0, y0, x1, y1):
    return min(math.hypot(x - TAPE_X, max(TAPE_Y0 - y, 0.0, y - TAPE_Y1)) for x, y in points(x0, y0, x1, y1)) <= 0.10


def direction(h):
    h = h % 360.0
    return "north" if 45 <= h < 135 else "south" if 225 <= h < 315 else "east" if (h >= 315 or h < 45) else "west"


def batch_moves(label, bdir):
    m = json.load(open(os.path.join(bdir, "manifest.json")))
    out, seen = [], set()
    for e in m["episodes"]:
        for r in e.get("range_moves") or []:
            if r["time_utc"] in seen:
                continue
            seen.add(r["time_utc"])
            h = math.radians(r["heading_deg"])
            out.append({"x0": r["x_m"] - r["forward_m"] * math.cos(h), "y0": r["y_m"] - r["forward_m"] * math.sin(h),
                        "x1": r["x_m"], "y1": r["y_m"], "heading": r["heading_deg"], "ratio": r["scale"]})
    return out


def detections(step, pose):
    out = {}
    th = math.radians(pose["theta_deg"])
    for d in step.get("detections_internal") or []:
        xyz = d.get("base_xyz_m")
        if d.get("id") is None or not xyz:
            continue
        r = math.hypot(xyz[0], xyz[1])
        b = math.atan2(xyz[1], xyz[0])
        r -= 0.00492 - 0.01658 * r
        if not (0.785 <= r <= 3.0) or abs(math.degrees(b)) > 30.0:
            continue
        wx, wy = pose["x_m"] + r * math.cos(th + b), pose["y_m"] + r * math.sin(th + b)
        near = sorted((math.hypot(t["x_m"] - wx, t["y_m"] - wy), t["uid"]) for t in WORLD["tags"] if t["id"] == int(d["id"]))
        if not near or near[0][0] > 1.0 or (len(near) > 1 and near[1][0] - near[0][0] < 1.0):
            continue
        out[near[0][1]] = (r, b)
    return out


def recomputed_moves(bdir):
    m = json.load(open(os.path.join(bdir, "manifest.json")))
    out = []
    for e in m["episodes"]:
        ep = os.path.join(bdir, "episodes", e["id"])
        for sp, tp in (("pre/steps.jsonl", "pre/truth.jsonl"), ("backend/steps.jsonl", "truth.jsonl"), ("post/steps.jsonl", "post/truth.jsonl")):
            S, T = rows(os.path.join(ep, sp)), rows(os.path.join(ep, tp))
            for i in range(1, min(len(S), len(T))):
                ex = S[i].get("executed") or {}
                odo = S[i].get("odometry_exact") or {}
                if (ex.get("command") or {}).get("action") not in ("FORWARD_25", "FORWARD_10") or \
                        (ex.get("result") or {}).get("result") != "done" or odo.get("forward_m", 0.0) < 0.20:
                    continue
                p0, p1 = T[i - 1]["tracked_world"]["pose"], T[i]["tracked_world"]["pose"]
                before, after = detections(S[i - 1], p0), detections(S[i], p1)
                ux, uy = odo["forward_m"], odo.get("left_m", 0.0)
                uu = ux * ux + uy * uy
                ratios = []
                for uid in set(before) & set(after):
                    (r1, b1), (r2, _) = before[uid], after[uid]
                    tx, ty = r1 * math.cos(b1), r1 * math.sin(b1)
                    tu = tx * ux + ty * uy
                    predicted = math.hypot(tx - ux, ty - uy)
                    if abs(tu - uu) / max(predicted, 1e-6) < 0.5 * math.sqrt(uu) or abs(r2 - predicted) > 1.5 * math.sqrt(uu) + 0.10:
                        continue
                    disc = tu * tu - uu * (r1 * r1 - r2 * r2)
                    if disc >= 0:
                        ratios.append((tu - math.sqrt(disc)) / uu)
                if ratios:
                    out.append({"x0": p0["x_m"], "y0": p0["y_m"], "x1": p1["x_m"], "y1": p1["y_m"],
                                "heading": p0["theta_deg"] + 0.5 * odo.get("dtheta_deg", 0.0), "ratio": med(ratios)})
    return out


FLAGS = {}


def straights(bdir):
    """Every straight move with a tracked pose before and after: on the line by both criteria, and flagged or not."""
    m = json.load(open(os.path.join(bdir, "manifest.json")))
    out = []
    for e in m["episodes"]:
        ep = os.path.join(bdir, "episodes", e["id"])
        for sp, tp in (("pre/steps.jsonl", "pre/truth.jsonl"), ("backend/steps.jsonl", "truth.jsonl"), ("post/steps.jsonl", "post/truth.jsonl")):
            S, T = rows(os.path.join(ep, sp)), rows(os.path.join(ep, tp))
            for i in range(1, min(len(S), len(T))):
                act = ((S[i].get("executed") or {}).get("command") or {}).get("action") or ""
                if not (act.startswith("FORWARD") or act.startswith("BACKWARD")):
                    continue
                p0, p1 = T[i - 1]["tracked_world"]["pose"], T[i]["tracked_world"]["pose"]
                flag = ((S[i].get("sense") or {}).get("status") or {}).get("odometry_quality") == "slip_suspected"
                out.append({"lead": on_lead(p0["x_m"], p0["y_m"], p1["x_m"], p1["y_m"]),
                            "diag": on_diag(p0["x_m"], p0["y_m"], p1["x_m"], p1["y_m"]), "flag": flag})
    return out


def cell(v):
    return "%2d x %s" % (len(v), "%.3f" % med(v) if v else "  -  ")


def table(title, groups):
    """groups: [(name, moves)]; prints on/off by both criteria, by direction."""
    print(title)
    print("%-22s %-6s | lead's criterion: on the line | off it     || 0.10 m criterion: on | off" % ("", ""))
    for name, mv in groups:
        for d in ("north", "south", "east", "west"):
            sel = [x for x in mv if direction(x["heading"]) == d]
            if not sel:
                continue
            a = [x["ratio"] for x in sel if x["lead"]]
            b = [x["ratio"] for x in sel if not x["lead"]]
            c = [x["ratio"] for x in sel if x["diag"]]
            e = [x["ratio"] for x in sel if not x["diag"]]
            print("%-22s %-6s | %-29s | %-10s || %-20s | %s" % (name, d, cell(a), cell(b), cell(c), cell(e)))
        a = [x["ratio"] for x in mv if x["lead"]]
        b = [x["ratio"] for x in mv if not x["lead"]]
        c = [x["ratio"] for x in mv if x["diag"]]
        e = [x["ratio"] for x in mv if not x["diag"]]
        print("%-22s %-6s | %-29s | %-10s || %-20s | %s" % (name, "all", cell(a), cell(b), cell(c), cell(e)))
    print()


def main():
    data = {}
    for arg in sys.argv[1:]:
        label, bdir = arg.split("=", 1)
        data[label] = {"batch": batch_moves(label, bdir), "recomputed": recomputed_moves(bdir)}
        FLAGS[label] = straights(bdir)
        for src in data[label].values():
            for x in src:
                x["lead"] = on_lead(x["x0"], x["y0"], x["x1"], x["y1"])
                x["diag"] = on_diag(x["x0"], x["y0"], x["x1"], x["y1"])
    labels = list(data)
    for src in ("batch", "recomputed"):
        groups = [("%s%s" % (l, " (removed)" if l in AFTER_REMOVAL else ""), data[l][src]) for l in labels if data[l][src]]
        down = [x for l in labels if l not in AFTER_REMOVAL for x in data[l][src]]
        gone = [x for l in labels if l in AFTER_REMOVAL for x in data[l][src]]
        groups += [("pooled, tape down", down), ("pooled, tape removed", gone)]
        table("== range ratio, source: %s (moves x median)" % src, groups)

    print("== the lead's per-batch numbers set against the batch source, each direction pooled over on and off the line")
    for l in labels:
        mv = data[l]["batch"]
        if not mv:
            print("  %-10s (no range_moves in the manifest)" % l)
            continue
        by = {d: [x["ratio"] for x in mv if direction(x["heading"]) == d] for d in ("north", "south", "east", "west")}
        ew = by["east"] + by["west"]
        print("  %-10s north %s   south %s   east/west %s" % (l, cell(by["north"]), cell(by["south"]), cell(ew)))
    print("  and all directions pooled, on against off the line, both criteria:")
    for l in labels:
        mv = data[l]["batch"]
        if mv:
            print("  %-10s lead's: on %s, off %s | 0.10 m: on %s, off %s" % (
                l, cell([x["ratio"] for x in mv if x["lead"]]), cell([x["ratio"] for x in mv if not x["lead"]]),
                cell([x["ratio"] for x in mv if x["diag"]]), cell([x["ratio"] for x in mv if not x["diag"]])))

    print()
    print("== the wheel-against-gyro flags (slip_suspected: wheel and gyro yaw disagree > 11 deg) on straight moves, on and off")
    print("   the line by the lead's criterion and by 0.10 m")
    for l in labels:
        st = FLAGS[l]
        print("  %-10s%s straights %3d: lead's on %3d (flagged %d), off %3d (flagged %d) | 0.10 m on %3d (flagged %d), off %3d (flagged %d)" % (
            l, " (removed)" if l in AFTER_REMOVAL else "          ", len(st),
            sum(1 for x in st if x["lead"]), sum(1 for x in st if x["lead"] and x["flag"]),
            sum(1 for x in st if not x["lead"]), sum(1 for x in st if not x["lead"] and x["flag"]),
            sum(1 for x in st if x["diag"]), sum(1 for x in st if x["diag"] and x["flag"]),
            sum(1 for x in st if not x["diag"]), sum(1 for x in st if not x["diag"] and x["flag"])))

    print()
    print("== the two sources against each other: moves logged by the batch and recomputed, matched by position")
    for l in labels:
        bm, rm = data[l]["batch"], data[l]["recomputed"]
        diffs = []
        for b in bm:
            best = min(rm, key=lambda r: math.hypot(r["x1"] - b["x1"], r["y1"] - b["y1"]), default=None)
            if best and math.hypot(best["x1"] - b["x1"], best["y1"] - b["y1"]) < 0.03:
                diffs.append(best["ratio"] - b["ratio"])
        if diffs:
            print("  %-10s %d matched, recomputed minus logged: median %+.3f, 90 %% within %.3f" % (
                l, len(diffs), med(diffs), sorted(abs(d) for d in diffs)[int(0.9 * (len(diffs) - 1))]))


if __name__ == "__main__":
    main()
