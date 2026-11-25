"""The b2-real-05 stall (2026-11-25) and the day's batches, from their text records: the motors through the day, the
stalled move, where the slip flags, the stalls and the worst range ratios lie against the tag pilot's tape line, and
the range ratios by heading on and off that line.

usage (repository root):
  python3 course-project/evidence/M3/M3.T12/batch-runner/b2-real-05/analyse.py OUT_SVG [floor-check=LOG] LABEL=BATCH_DIR[,MOVES_DIR] ...
  (LABEL=,MOVES_DIR: a session's telemetry alone, without a batch copy; floor-check=,MOVES_DIR for the floor check's)
LOG: the floor check's move log (evidence/M3/M3.T6/floor-check-runs/floor-030825.log): each move's duration and counts.
LABEL: b2-real-01 ... b2-real-05. BATCH_DIR: data/batches/<label> (copied read-only from the Spark; text records only).
MOVES_DIR (optional): the batch's recorder session's moves/ folder (one log per move, with the car's telemetry: both
wheels' tick counts and duties at about 50 Hz). Without it the motor numbers come from the batch's own per-move
diagnostics (duration, peak speed, each wheel's distance) only. OUT_SVG: the floor map written.

The tape (CONTEXT.md, 2026-11-25 11:31; evidence/M1/M1.T8/PROCEDURE.md): the tag pilot's painter's tape ran from under
tag T03 (2.369, 0.071) square to the wall, i.e. along x = 2.369 from y about 0.07 out to 3.6 m, with 20 cm cross strips
at the distance marks 0.65 to 3.50 m from the baseboard. Xiaohui removed the long centre line at about 11:25 CST.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this analysis of the b2-real-05 stall."""
import glob
import json
import math
import os
import statistics
import sys

TAPE_X = 2.369
TAPE_Y0, TAPE_Y1 = 0.071, 0.071 + 3.6
MARKS = [0.65, 0.70, 0.75, 0.80, 0.85, 1.00, 1.25, 1.50, 1.75, 2.00, 2.25, 2.50, 2.75, 3.00, 3.25, 3.50]
NEAR_M = 0.10           # a move "on the tape" passes within this of the centre line (wheels at +-0.067 m of the axle)
TPM = {"l": 19385.0, "r": 19804.0}      # configs/car.json ticks per metre (left, right)
STALLS = {}


def rows(path):
    return [json.loads(l) for l in open(path)] if os.path.exists(path) else []


def med(v):
    return statistics.median(v) if v else float("nan")


def load_batch(label, bdir):
    """Every move of a batch: phase, action, result, the backend's diagnostics, the slip flag, the tracked pose before and
    after (arena frame)."""
    out = []
    m = json.load(open(os.path.join(bdir, "manifest.json")))
    for e in m["episodes"]:
        ep = os.path.join(bdir, "episodes", e["id"])
        prev = None
        for phase, sp, tp in (("pre", "pre/steps.jsonl", "pre/truth.jsonl"), ("episode", "backend/steps.jsonl", "truth.jsonl"),
                              ("post", "post/steps.jsonl", "post/truth.jsonl")):
            for s, t in zip(rows(os.path.join(ep, sp)), rows(os.path.join(ep, tp))):
                ex = s.get("executed") or {}
                cmd, res, diag = ex.get("command") or {}, ex.get("result") or {}, ex.get("diag") or {}
                pose = t["tracked_world"]["pose"]
                if cmd.get("action"):
                    st = ((s.get("sense") or {}).get("status") or {})
                    out.append({"batch": label, "episode": e["id"], "phase": phase, "step": s.get("step"),
                                "time_utc": s.get("time_utc"), "t_unix": s.get("t_unix"), "obs_id": cmd.get("obs_id"),
                                "action": cmd["action"], "result": res.get("result"), "reason": res.get("reason"),
                                "duration_s": res.get("duration_s"), "diag": diag,
                                "slip": st.get("odometry_quality") == "slip_suspected",
                                "before": prev, "after": dict(pose)})
                prev = dict(pose)
    if (m.get("halt") or {}).get("code") == "stall":
        STALLS[label] = dict(m["last_tracked_pose_world"]["pose"], detail=m["halt"]["detail"], time=m["halt"]["time_utc"])
    return m, out


def tape_distance(x0, y0, x1, y1):
    """Smallest distance from the segment (x0,y0)-(x1,y1) to the tape's centre line."""
    best = 9.9
    for i in range(21):
        f = i / 20.0
        x, y = x0 + f * (x1 - x0), y0 + f * (y1 - y0)
        dy = max(TAPE_Y0 - y, 0.0, y - TAPE_Y1)
        best = min(best, math.hypot(x - TAPE_X, dy))
    return best


HALF_TRACK = 0.1335 / 2         # configs/car.json track width: each wheel 6.7 cm from the axle midpoint


def wheels_to_tape(before, after):
    """Each wheel's smallest distance from the tape's centre line over a move (left, right): the wheels stand
    HALF_TRACK either side of the axle midpoint, square to the heading."""
    out = []
    for side in (1.0, -1.0):                                    # left, right
        best = 9.9
        for i in range(11):
            f = i / 10.0
            x = before["x_m"] + f * (after["x_m"] - before["x_m"])
            y = before["y_m"] + f * (after["y_m"] - before["y_m"])
            h = math.radians(before["theta_deg"] + f * ((after["theta_deg"] - before["theta_deg"] + 180) % 360 - 180))
            wx, wy = x - side * HALF_TRACK * math.sin(h), y + side * HALF_TRACK * math.cos(h)
            best = min(best, math.hypot(wx - TAPE_X, max(TAPE_Y0 - wy, 0.0, wy - TAPE_Y1)))
        out.append(best)
    return out


def telemetry(path):
    """One move's telemetry: per wheel, speed (m/s, over >= 0.08 s windows) and duty, from the move's start."""
    r = rows(path)
    head = next((x for x in r if x.get("ev") == "header"), {})
    tel = [x for x in r if x.get("ev") == "tel"]
    stop = next((x for x in r if x.get("ev") == "stop"), None)
    start = next((x for x in r if x.get("ev") == "start"), None)
    if len(tel) < 3 or start is None:
        return None
    t0 = start["t"]
    win, last = [], tel[0]
    for x in tel[1:]:
        dt = x["t_rx"] - last["t_rx"]
        if dt < 0.08:
            continue
        win.append({"t": x["t_rx"] - t0, "vl": (x["l"] - last["l"]) / dt / TPM["l"], "vr": (x["r"] - last["r"]) / dt / TPM["r"],
                    "dl": x["duty"][0], "dr": x["duty"][1], "stopped": stop is not None and x["t_rx"] > stop["t"]})
        last = x
    kicks = []                  # the firmware's stall assist: a wheel's duty set to +-0.8 for a moment (counter "assists")
    for a, b in zip(tel, tel[1:]):
        if b.get("assists", 0) > a.get("assists", 0):
            dl, dr = abs(b["duty"][0]), abs(b["duty"][1])
            kicks.append({"t": round(b["t_rx"] - t0, 2), "wheel": "right" if dr >= 0.79 and dl < 0.79 else
                          "left" if dl >= 0.79 and dr < 0.79 else "both/unclear"})
    return {"obs_id": (head.get("cmd") or {}).get("obs_id"), "action": (head.get("cmd") or {}).get("action"), "win": win,
            "kicks": kicks,
            "stop_t": (stop["t"] - t0) if stop else None, "result": (stop or {}).get("result"), "reason": (stop or {}).get("reason")}


def wheel_numbers(tm):
    """Per wheel: peak |speed|, time to 90 % of it, the highest |duty|, and |speed| per |duty| while driven (|duty| >= 0.3,
    before the stop); slow moments: |speed| < 0.03 m/s while |duty| >= 0.3 after the wheel had reached 0.05 m/s."""
    out = {}
    w = [x for x in tm["win"] if not x["stopped"]]
    for k in ("l", "r"):
        v = [abs(x["v" + k]) for x in w]
        d = [abs(x["d" + k]) for x in w]
        if not v:
            return None
        pk = max(v)
        t90 = next((x["t"] for x, s in zip(w, v) if s >= 0.9 * pk), None)
        per = [s / dd for s, dd in zip(v, d) if dd >= 0.3]
        moving, slow = False, []
        for x, s, dd in zip(w, v, d):
            moving = moving or s >= 0.05
            if moving and dd >= 0.3 and s < 0.03:
                slow.append((round(x["t"], 2), round(s, 3), round(dd, 3)))
        out[k] = {"peak": pk, "t90": t90, "duty_max": max(d), "per_duty": med(per), "slow": slow}
    return out


def main():
    svg_path = sys.argv[1]
    batches, floor = [], None
    for arg in sys.argv[2:]:
        label, dirs = arg.split("=", 1)
        if label == "floor-check" and not dirs.startswith(","):
            floor = dirs
            continue
        bdir, mdir = (dirs.split(",") + [None])[:2]
        if not bdir:                                # telemetry only (a session without a batch copy)
            TELEMETRY_ONLY.append((label, mdir))
            continue
        BATCH_DIRS[label] = bdir
        m, mv = load_batch(label, bdir)
        batches.append((label, m, mv, mdir))
    allmoves = [x for b in batches for x in b[2]]

    print("== 1. The motors through the day, from each batch's per-move diagnostics (all moves that ran)")
    print("batch       first move (UTC)  | FORWARD_25: n, median duration s, peak speed m/s, s_right/s_left, speed at stop | "
          "TURN_*_30: n, median duration s, peak rate deg/s")
    if floor:
        import re
        fl = [re.search(r"MOVE (\S+) -> (\S+).*L=(-?\d+) R=(-?\d+) dur=([\d.]+)", l) for l in open(floor)]
        f = [(float(x.group(5)), int(x.group(3)) / TPM["l"], int(x.group(4)) / TPM["r"]) for x in fl if x and x.group(1) == "FORWARD_25"]
        tr = [float(x.group(5)) for x in fl if x and x.group(1).startswith("TURN_")]
        print("%-11s %s | %3d %.2f   -   %.3f   -   | %3d %.2f   -   (the log has durations and counts only)" % (
            "floor check", "09:08 (03:08 CST)", len(f), med([v[0] for v in f]), med([v[2] / v[1] for v in f]), len(tr), med(tr)))
    for label, m, mv, mdir in batches:
        f = [x for x in mv if x["action"] == "FORWARD_25" and x["diag"].get("s_left_m")]
        tr = [x for x in mv if x["action"].startswith("TURN_") and x["diag"]]
        print("%-11s %s | %3d %.2f %.3f %.3f %.3f | %3d %.2f %.1f" % (
            label, (mv[0]["time_utc"] or "")[11:19] if mv else "-", len(f), med([x["duration_s"] for x in f if x["duration_s"]]),
            med([x["diag"]["peak_speed_mps"] for x in f]), med([x["diag"]["s_right_m"] / x["diag"]["s_left_m"] for x in f if x["diag"]["s_left_m"] > 0.05]),
            med([x["diag"]["speed_at_stop_mps"] for x in f]), len(tr), med([x["duration_s"] for x in tr if x["duration_s"]]),
            med([x["diag"].get("peak_rate_dps", float("nan")) for x in tr])))

    print()
    print("== 1b. From the recorder sessions' telemetry (both wheels, ~50 Hz), where copied: |speed| per |duty| while driven,")
    print("   peak |speed|, time to 90 % of it, highest |duty|; medians over the batch's moves")
    slow_moves, kicks, counted = {}, {}, {}
    for label, m, mv, mdir in [("floor check" if l == "floor-check" else l, None, None, d) for l, d in TELEMETRY_ONLY
                               if l == "floor-check"] + batches + [(l, None, None, d) for l, d in TELEMETRY_ONLY if l != "floor-check"]:
        if not mdir:
            print("%-11s session telemetry not copied" % label)
            continue
        per = {"FORWARD_25": [], "TURN": []}
        for path in sorted(glob.glob(os.path.join(mdir, "move_*.jsonl"))):
            tm = telemetry(path)
            if tm is None:
                continue
            wn = wheel_numbers(tm)
            if wn is None:
                continue
            kind = "FORWARD_25" if tm["action"] == "FORWARD_25" else ("TURN" if (tm["action"] or "").startswith("TURN_") else None)
            if kind:
                per[kind].append(wn)
                if wn["r"]["slow"] or wn["l"]["slow"]:
                    slow_moves.setdefault(label, []).append((os.path.basename(path), tm, wn))
            for k in tm["kicks"]:
                kicks.setdefault(label, []).append((os.path.basename(path), tm, k))
            counted[label] = counted.get(label, 0) + 1
        for kind, L in per.items():
            if not L:
                continue
            row = []
            for k in ("l", "r"):
                row.append("%s: %.3f m/s/duty, peak %.3f, t90 %.2f s, duty max %.3f" % (
                    k.upper(), med([w[k]["per_duty"] for w in L if not math.isnan(w[k]["per_duty"])]), med([w[k]["peak"] for w in L]),
                    med([w[k]["t90"] for w in L if w[k]["t90"] is not None]), med([w[k]["duty_max"] for w in L])))
            ratio = med([w["r"]["per_duty"] / w["l"]["per_duty"] for w in L
                         if w["l"]["per_duty"] and not math.isnan(w["l"]["per_duty"]) and not math.isnan(w["r"]["per_duty"])])
            slow = sum(1 for w in L if w["r"]["slow"]), sum(1 for w in L if w["l"]["slow"])
            print("%-11s %-10s n %3d | %s | %s | R/L per duty %.3f | moves with a slow moment: right %d, left %d" % (
                label, kind, len(L), row[0], row[1], ratio, slow[0], slow[1]))

    print()
    print("== 1c. Moves with a slow moment (a wheel under 0.03 m/s at duty >= 0.3 after it had reached 0.05 m/s), per session:")
    where = {(x["batch"], x["obs_id"]): x for x in allmoves if x["obs_id"]}
    for label, L in slow_moves.items():
        for name, tm, wn in L:
            x = where.get((label, tm["obs_id"]))
            loc = ""
            if x and x["before"] and x["after"]:
                wl, wr = wheels_to_tape(x["before"], x["after"])
                loc = " from (%.2f, %.2f, %.0f) to (%.2f, %.2f); wheels from the tape line L %.3f R %.3f m" % (
                    x["before"]["x_m"], x["before"]["y_m"], x["before"]["theta_deg"], x["after"]["x_m"], x["after"]["y_m"], wl, wr)
            for k in ("r", "l"):
                if wn[k]["slow"]:
                    print("  %-10s %s %s: %s wheel slow at %s (t s, speed m/s, duty); result %s %s%s" % (
                        label, name, tm["action"], "right" if k == "r" else "left", wn[k]["slow"][:4], tm["result"],
                        tm["reason"] or "", loc))

    print()
    print("== 1d. The firmware's stall assist (a wheel kicked at duty 0.8 when it stops while driven), per session:")
    for label in counted:
        L = kicks.get(label, [])
        by = {}
        for name, tm, k in L:
            by[(k["wheel"], "turn" if (tm["action"] or "").startswith("TURN_") else "straight")] = by.get(
                (k["wheel"], "turn" if (tm["action"] or "").startswith("TURN_") else "straight"), 0) + 1
        print("  %-11s %4d moves, %2d kicks: %s" % (label, counted[label], len(L),
                                                 ", ".join("%s wheel in a %s %d" % (w, kind, n) for (w, kind), n in sorted(by.items())) or "none"))
    print("  turns and kicks by where the car stood (north strip y >= 3.3 m against the rest), the sessions with a batch:")
    for label in counted:
        turns_at = [x for x in allmoves if x["batch"] == label and x["action"].startswith("TURN_") and x["before"]]
        if not turns_at:
            continue
        kick_at = [where.get((label, tm["obs_id"])) for name, tm, k in kicks.get(label, [])]
        kick_at = [x for x in kick_at if x and x["before"]]
        n_n = sum(1 for x in turns_at if x["before"]["y_m"] >= 3.3)
        k_n = sum(1 for x in kick_at if x["before"]["y_m"] >= 3.3)
        print("    %-11s turns north %4d, kicks there %2d | turns elsewhere %4d, kicks there %2d" % (
            label, n_n, k_n, len(turns_at) - n_n, len(kick_at) - k_n))
    print("  each kick: session, move, wheel, the axle midpoint's and the wheels' nearest approach to the tape line")
    for label, L in kicks.items():
        for name, tm, k in L:
            x = where.get((label, tm["obs_id"]))
            loc = "(no batch pose)"
            if x and x["before"]:
                KICK_POINTS.append((x["before"]["x_m"], x["before"]["y_m"], k["wheel"], label))
            if x and x["before"] and x["after"]:
                wl, wr = wheels_to_tape(x["before"], x["after"])
                loc = "at (%.2f, %.2f, %.0f): mid %.3f, L %.3f, R %.3f m" % (x["before"]["x_m"], x["before"]["y_m"],
                                                                           x["before"]["theta_deg"], x["tape_m"] if "tape_m" in x else
                                                                           tape_distance(x["before"]["x_m"], x["before"]["y_m"],
                                                                                         x["after"]["x_m"], x["after"]["y_m"]), wl, wr)
            print("    %-10s %-44s %-6s t %.2f s  %s; result %s" % (label, name, k["wheel"], k["t"], loc, tm["result"]))

    print()
    print("== 2. The stalled moves (the batch's diagnostics)")
    for label, m, mv, mdir in batches:
        for x in mv:
            if x["result"] == "stalled":
                d = x["diag"]
                print("%s %s %s step %s %s %s: %s; duration %.2f s, achieved %.3f m, s_left %.3f s_right %.3f m, gyro %.1f deg, "
                      "encoder yaw %.1f deg, peak %.3f m/s, at the stop %.3f m/s; from (%.2f, %.2f, %.0f) to (%.2f, %.2f, %.0f); "
                      "nearest the tape line %.3f m (wheels: left %.3f, right %.3f)" % (
                          label, x["episode"], x["phase"], x["step"], x["time_utc"], x["action"], x["reason"], x["duration_s"] or 0,
                          d.get("odometry", {}).get("forward_m", 0.0), d.get("s_left_m", 0), d.get("s_right_m", 0),
                          d.get("odometry", {}).get("dtheta_deg", 0), d.get("encoder_yaw_deg", 0), d.get("peak_speed_mps", 0),
                          d.get("speed_at_stop_mps", 0), *(x["before"][k] for k in ("x_m", "y_m", "theta_deg")),
                          *(x["after"][k] for k in ("x_m", "y_m", "theta_deg")),
                          tape_distance(x["before"]["x_m"], x["before"]["y_m"], x["after"]["x_m"], x["after"]["y_m"]),
                          *wheels_to_tape(x["before"], x["after"])))

    print()
    print("== 3. Where: slip flags, stalls and the range ratios against the tape line (moves with a pose before and after)")
    placed = [x for x in allmoves if x["before"] and x["after"] and x["batch"] not in TAPE_GONE]
    print("(batches run after the long tape was removed are left out of this section: %s)" % ", ".join(sorted(TAPE_GONE)))
    for x in placed:
        x["tape_m"] = tape_distance(x["before"]["x_m"], x["before"]["y_m"], x["after"]["x_m"], x["after"]["y_m"])
    fw = [x for x in placed if x["action"] in ("FORWARD_25", "FORWARD_10", "BACKWARD_10", "BACKWARD_25")]
    turns = [x for x in placed if x["action"].startswith("TURN_")]
    for name, group in (("straight moves", fw), ("turns", turns)):
        near = [x for x in group if x["tape_m"] <= NEAR_M]
        sl = [x for x in group if x["slip"]]
        sln = [x for x in sl if x["tape_m"] <= NEAR_M]
        print("%s: %d, of them %d (%.0f %%) within %.2f m of the tape line; slip flags %d, of them %d within it (%s)" % (
            name, len(group), len(near), 100.0 * len(near) / max(1, len(group)), NEAR_M, len(sl), len(sln),
            "%.0f %% of the moves there against %.1f %% elsewhere" % (100.0 * len(sln) / max(1, len(near)),
                                                                     100.0 * (len(sl) - len(sln)) / max(1, len(group) - len(near)))))
    print("every slip-flagged move: batch episode phase step action, from -> to, the axle midpoint's and each wheel's")
    print("nearest approach to the tape line, the wheel-gyro yaw disagreement, the wheels' distances s_left / s_right")
    for x in placed:
        if x["slip"]:
            wl, wr = wheels_to_tape(x["before"], x["after"])
            print("  %-10s %s %-7s %3s %-13s (%.2f, %.2f, %4.0f) -> (%.2f, %.2f)  mid %.3f  L %.3f  R %.3f m  %.1f deg  %.3f / %.3f m" % (
                x["batch"], x["episode"], x["phase"], x["step"], x["action"], x["before"]["x_m"], x["before"]["y_m"],
                x["before"]["theta_deg"], x["after"]["x_m"], x["after"]["y_m"], x["tape_m"], wl, wr,
                x["diag"].get("yaw_disagree_deg", 0.0), x["diag"].get("s_left_m", 0.0), x["diag"].get("s_right_m", 0.0)))
    print("the stalls:")
    for label, s in STALLS.items():
        print("  %-10s %s at (%.2f, %.2f, %.0f), %s: %.3f m from the tape line" % (
            label, s["detail"], s["x_m"], s["y_m"], s["theta_deg"], s["time"], abs(s["x_m"] - TAPE_X)))

    rng = []
    for label, m, mv, mdir in batches:
        seen = set()
        for e in m["episodes"]:
            for r in e.get("range_moves") or []:
                if r["time_utc"] in seen:
                    continue
                seen.add(r["time_utc"])
                h = math.radians(r["heading_deg"])
                x0, y0 = r["x_m"] - r["forward_m"] * math.cos(h), r["y_m"] - r["forward_m"] * math.sin(h)
                rng.append(dict(r, batch=label, x0=x0, y0=y0, tape_m=tape_distance(x0, y0, r["x_m"], r["y_m"])))
    rng.sort(key=lambda r: r["scale"])
    print("range-measured forward moves: %d over the batches; the 12 lowest ratios and the 5 highest:" % len(rng))
    for r in rng[:12] + rng[-5:]:
        print("  %-10s %s heading %6.1f  (%.2f, %.2f) -> (%.2f, %.2f)  ratio %.3f  nearest the tape line %.3f m" % (
            r["batch"], r["time_utc"][11:19], r["heading_deg"], r["x0"], r["y0"], r["x_m"], r["y_m"], r["scale"], r["tape_m"]))

    print()
    print("== 4. Range ratios (tags over odometry) by direction of travel, on and off the tape line (within %.2f m)" % NEAR_M)

    def sector(h):
        h = h % 360.0
        return "north (45-135)" if 45 <= h < 135 else "south (225-315)" if 225 <= h < 315 else \
            "east (315-45)" if (h >= 315 or h < 45) else "west (135-225)"
    groups = {}
    for r in rng:
        keys = [(r["batch"], sector(r["heading_deg"]), r["tape_m"] <= NEAR_M)]
        if r["batch"] not in TAPE_GONE:
            keys.append(("all with the tape", sector(r["heading_deg"]), r["tape_m"] <= NEAR_M))
        for key in keys:
            groups.setdefault(key, []).append(r["scale"])
    for label in [b[0] for b in batches] + ["all with the tape"]:
        for sec in ("north (45-135)", "south (225-315)", "east (315-45)", "west (135-225)"):
            on, off = groups.get((label, sec, True), []), groups.get((label, sec, False), [])
            if on or off:
                print("%-17s %-16s on the tape%s: n %2d median %s | off it: n %3d median %s" % (
                    label, sec, " line (removed)" if label in TAPE_GONE else "", len(on), "%.3f" % med(on) if on else "  -  ", len(off), "%.3f" % med(off) if off else "  -  "))
    print("each batch's own slip_by_heading (the manifest, last episode: the batch so far, 45-degree sectors by heading):")
    for label, m, mv, mdir in batches:
        tab = None
        for e in m["episodes"]:
            tab = e.get("slip_by_heading") or tab
        if tab:
            print("  %-10s %s" % (label, "  ".join("%g: %d x %.3f" % (t["heading_deg"], t["moves"], t["median"]) for t in tab)))
        else:
            print("  %-10s (no slip_by_heading in this manifest)" % label)

    per_tag(batches)
    write_svg(svg_path, batches, placed, rng)
    print()
    print("map written:", os.path.basename(svg_path))


def per_tag(batches):
    """The range ratio of every forward move, tag by tag (not the batch's median over a move's tags): a car that covers
    less than its count shows it on every tag it ranges; a tag whose printed size differs from the world file's 0.16 m
    shows it on that tag alone, whatever the direction. Same preparation as the batch's range check, done here
    independently: the detector's millimetre record, the pilot's range bias removed, 0.785 to 3.0 m, within 30 degrees
    of ahead, the id resolved to a surveyed tag by the tracked pose, forward moves of 0.20 m or more by odometry."""
    world = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..", "configs",
                                        "arenas", "real-room.json")))
    tags = world["tags"]

    def dets(step, pose):
        out = {}
        th = math.radians(pose["theta_deg"])
        for d in step.get("detections_internal") or []:
            xyz = d.get("base_xyz_m")
            if d.get("id") is None or not xyz:
                continue
            r = math.hypot(xyz[0], xyz[1])
            b = math.degrees(math.atan2(xyz[1], xyz[0]))
            r -= 0.00492 - 0.01658 * r
            if not (0.785 <= r <= 3.0) or abs(b) > 30.0:
                continue
            wx, wy = pose["x_m"] + r * math.cos(th + math.radians(b)), pose["y_m"] + r * math.sin(th + math.radians(b))
            near = sorted((math.hypot(t["x_m"] - wx, t["y_m"] - wy), t["uid"], t["wall"]) for t in tags if t["id"] == int(d["id"]))
            if not near or near[0][0] > 1.0 or (len(near) > 1 and near[1][0] - near[0][0] < 1.0):
                continue
            out[near[0][1]] = (r, math.radians(b), near[0][2])
        return out

    res = []
    for label, m, mv, mdir in batches:
        for e in m["episodes"]:
            ep = os.path.join(BATCH_DIRS[label], "episodes", e["id"])
            for sp, tp in (("pre/steps.jsonl", "pre/truth.jsonl"), ("backend/steps.jsonl", "truth.jsonl"), ("post/steps.jsonl", "post/truth.jsonl")):
                S, T = rows(os.path.join(ep, sp)), rows(os.path.join(ep, tp))
                for i in range(1, min(len(S), len(T))):
                    ex = S[i].get("executed") or {}
                    act = (ex.get("command") or {}).get("action")
                    odo = S[i].get("odometry_exact") or {}
                    if act not in ("FORWARD_25", "FORWARD_10") or (ex.get("result") or {}).get("result") != "done" or odo.get("forward_m", 0) < 0.20:
                        continue
                    before, after = dets(S[i - 1], T[i - 1]["tracked_world"]["pose"]), dets(S[i], T[i]["tracked_world"]["pose"])
                    ux, uy = odo["forward_m"], odo.get("left_m", 0.0)
                    uu = ux * ux + uy * uy
                    heading = T[i - 1]["tracked_world"]["pose"]["theta_deg"] + 0.5 * odo.get("dtheta_deg", 0.0)
                    for uid in set(before) & set(after):
                        r1, b1, wall = before[uid]
                        r2 = after[uid][0]
                        tx, ty = r1 * math.cos(b1), r1 * math.sin(b1)
                        tu = tx * ux + ty * uy
                        predicted = math.hypot(tx - ux, ty - uy)
                        if abs(tu - uu) / max(predicted, 1e-6) < 0.5 * math.sqrt(uu) or abs(r2 - predicted) > 1.5 * math.sqrt(uu) + 0.10:
                            continue
                        disc = tu * tu - uu * (r1 * r1 - r2 * r2)
                        if disc < 0:
                            continue
                        res.append({"batch": label, "tag": uid, "wall": wall, "heading": heading,
                                    "ratio": (tu - math.sqrt(disc)) / uu, "x": T[i]["tracked_world"]["pose"]["x_m"],
                                    "y": T[i]["tracked_world"]["pose"]["y_m"]})

    def sector(h):
        h = h % 360.0
        return "north" if 45 <= h < 135 else "south" if 225 <= h < 315 else "east" if (h >= 315 or h < 45) else "west"
    print()
    print("== 4b. Range ratio per tag (each tag ranged before and after a forward move), by direction of travel and wall:")
    print("   median (n). A car covering less than its count shows on every wall it ranges; a mis-sized tag on its own wall.")
    for label in sorted({r["batch"] for r in res}) + ["all"]:
        sel = [r for r in res if label == "all" or r["batch"] == label]
        for sec in ("north", "south", "east", "west"):
            by = {}
            for r in sel:
                if sector(r["heading"]) == sec:
                    by.setdefault(r["wall"], []).append(r["ratio"])
            if by:
                print("  %-10s %-5s %s" % (label, sec, "  ".join("%s %.3f (%d)" % (w, med(v), len(v)) for w, v in sorted(by.items()))))
    print("   per tag, all batches, all directions: median (n)")
    by = {}
    for r in res:
        by.setdefault((r["wall"], r["tag"], sector(r["heading"])), []).append(r["ratio"])
    for (wall, tag, sec), v in sorted(by.items()):
        if len(v) >= 2:
            print("    %-7s %-4s %-5s %.3f (%d)" % (wall, tag, sec, med(v), len(v)))


BATCH_DIRS = {}
TELEMETRY_ONLY = []
TAPE_GONE = {"b2-real-06"}
KICK_POINTS = []      # run after Xiaohui removed the long centre line (CONTEXT.md, 2026-11-25 11:2x CST)


def write_svg(path, batches, placed, rng):
    poly = batches[-1][1]["config"]["world"]["arena"]["drive_polygon_m"] if "world" in batches[-1][1].get("config", {}) else \
        [[0.66, 0.0197], [2.95, 0.088], [3.824, 0.954], [3.808, 5.224], [0.66, 5.138]]
    S, X0, Y1 = 120.0, 0.4, 5.4                     # pixels per metre; the arena from x 0.4, y up to 5.4

    def px(x, y):
        return (x - X0) * S + 20, (Y1 - y) * S + 20
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" font-family="sans-serif" font-size="11">' % (
        (4.1 - X0) * S + 260, (Y1 + 0.1) * S + 40), '<rect width="100%" height="100%" fill="#fff"/>']
    out.append('<polygon points="%s" fill="#f6f6f2" stroke="#888"/>' % " ".join("%.0f,%.0f" % px(*p) for p in poly))
    a, b = px(TAPE_X, TAPE_Y0), px(TAPE_X, TAPE_Y1)
    out.append('<line x1="%.0f" y1="%.0f" x2="%.0f" y2="%.0f" stroke="#e0a800" stroke-width="%.1f" opacity="0.7"/>' % (
        a[0], a[1], b[0], b[1], 0.048 * S))
    for d in MARKS:
        c, e = px(TAPE_X - 0.10, TAPE_Y0 + d), px(TAPE_X + 0.10, TAPE_Y0 + d)
        out.append('<line x1="%.0f" y1="%.0f" x2="%.0f" y2="%.0f" stroke="#e0a800" stroke-width="3" opacity="0.7"/>' % (c[0], c[1], e[0], e[1]))
    for x in placed:
        if x["action"].startswith("FORWARD") or x["action"].startswith("BACKWARD"):
            c, e = px(x["before"]["x_m"], x["before"]["y_m"]), px(x["after"]["x_m"], x["after"]["y_m"])
            out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#c8c8c8" stroke-width="1"/>' % (c[0], c[1], e[0], e[1]))
    for r in rng[:12]:
        c, e = px(r["x0"], r["y0"]), px(r["x_m"], r["y_m"])
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#2b6cb0" stroke-width="3"/>' % (c[0], c[1], e[0], e[1]))
    for x in placed:
        if x["slip"]:
            c, e = px(x["before"]["x_m"], x["before"]["y_m"]), px(x["after"]["x_m"], x["after"]["y_m"])
            out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#d53f8c" stroke-width="3"/>' % (c[0], c[1], e[0], e[1]))
            out.append('<circle cx="%.1f" cy="%.1f" r="3" fill="#d53f8c"/>' % e)
    for x, y, wheel, label in KICK_POINTS:
        c = px(x, y)
        out.append('<rect x="%.1f" y="%.1f" width="7" height="7" fill="%s" stroke="#333" stroke-width="0.5"/>' % (
            c[0] - 3.5, c[1] - 3.5, "#ff8c00" if wheel == "right" else "#38a169" if wheel == "left" else "#999"))
    for label, s in STALLS.items():
        c = px(s["x_m"], s["y_m"])
        out.append('<circle cx="%.1f" cy="%.1f" r="7" fill="none" stroke="#c00" stroke-width="2.5"/>' % c)
        out.append('<text x="%.0f" y="%.0f" fill="#c00">%s stall</text>' % (c[0] + 9, c[1] + 4, label))
    lx = (4.1 - X0) * S + 40
    for i, (col, txt) in enumerate((("#e0a800", "pilot tape: centre line x = 2.369 and cross strips"),
                                    ("#c8c8c8", "every straight move (tracked)"), ("#2b6cb0", "12 lowest range ratios"),
                                    ("#d53f8c", "slip_suspected moves"), ("#c00", "stalls"),
                                    ("#ff8c00", "stall-assist kick, right wheel (turns)"),
                                    ("#38a169", "stall-assist kick, left wheel (turns)"))):
        out.append('<rect x="%.0f" y="%d" width="14" height="6" fill="%s"/><text x="%.0f" y="%d">%s</text>' % (
            lx, 30 + 18 * i, col, lx + 20, 37 + 18 * i, txt))
    out.append('<text x="%.0f" y="%d">arena frame, metres; y north (up), x east (right)</text>' % (lx, 30 + 18 * 8))
    out.append('<text x="%.0f" y="%d">straights, slip flags, stalls: b2-real-01 to 05 (tape down);</text>' % (lx, 30 + 18 * 9))
    out.append('<text x="%.0f" y="%d">kicks and low ratios: b2-real-02 to 06 (06: long tape removed)</text>' % (lx, 30 + 18 * 10))
    for v in range(1, 6):
        c = px(X0, v)
        out.append('<text x="2" y="%.0f">y %d</text>' % (c[1] + 4, v))
    for v in range(1, 4):
        c = px(v, 0)
        out.append('<text x="%.0f" y="%.0f">x %d</text>' % (c[0] - 8, (Y1 + 0.1) * S + 34, v))
    out.append("<!-- AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: drawn by analyse.py from the batches' text records -->")
    out.append("</svg>")
    open(path, "w").write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
