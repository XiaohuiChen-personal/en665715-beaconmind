"""The three right-wheel stalls of 2026-11-25 and each wheel's duty against speed through the day, from the recorder
sessions' move logs (both wheels' tick counts and duties at about 50 Hz) and the batches' text records.

usage (repository root):
  python3 course-project/evidence/M3/M3.T12/batch-runner/b2-real-05/stalls.py LABEL=MOVES_DIR[,BATCH_DIR] ...
MOVES_DIR: a recorder session's moves/ folder; BATCH_DIR (optional): data/batches/<label>, for the tracked poses and the
Pico's supply reading (car_state.vsys_min_mv).

It prints:
- each stalled move: its heading and place, and both wheels' duty and speed every ~0.1 s;
- per session, each wheel's median speed in bins of commanded duty, over all straight moves (both wheels driven
  forward), and the duty each wheel needed for 0.10-0.13 m/s;
- per session, the firmware's stall-assist kicks (a stopped, driven wheel pushed at duty 0.8), by wheel;
- per batch, the lowest Pico supply reading (that is the Pico's power bank; the motors' AA pack is not measured).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this comparison of the stalls."""
import glob
import json
import math
import os
import statistics
import sys

TPM = {"l": 19385.0, "r": 19804.0}      # configs/car.json ticks per metre
BINS = [(0.30, 0.35), (0.35, 0.40), (0.40, 0.45), (0.45, 0.50), (0.50, 0.55), (0.55, 0.60), (0.60, 0.65), (0.65, 0.70)]


def rows(path):
    return [json.loads(l) for l in open(path)] if os.path.exists(path) else []


def med(v):
    return statistics.median(v) if v else None


def windows(r):
    start = next((x for x in r if x.get("ev") == "start"), None)
    stop = next((x for x in r if x.get("ev") == "stop"), None)
    tel = [x for x in r if x.get("ev") == "tel"]
    if start is None or len(tel) < 3:
        return []
    out, last = [], tel[0]
    for x in tel[1:]:
        dt = x["t_rx"] - last["t_rx"]
        if dt < 0.08:
            continue
        out.append({"t": x["t_rx"] - start["t"], "vl": (x["l"] - last["l"]) / dt / TPM["l"], "vr": (x["r"] - last["r"]) / dt / TPM["r"],
                    "dl": x["duty"][0], "dr": x["duty"][1], "after_stop": stop is not None and x["t_rx"] > stop["t"]})
        last = x
    return out


def poses(bdir):
    """obs_id -> (tracked pose before the move, after it)."""
    out = {}
    if not bdir:
        return out
    m = json.load(open(os.path.join(bdir, "manifest.json")))
    for e in m["episodes"]:
        ep = os.path.join(bdir, "episodes", e["id"])
        for sp, tp in (("pre/steps.jsonl", "pre/truth.jsonl"), ("backend/steps.jsonl", "truth.jsonl"), ("post/steps.jsonl", "post/truth.jsonl")):
            S, T = rows(os.path.join(ep, sp)), rows(os.path.join(ep, tp))
            for i in range(1, min(len(S), len(T))):
                oid = ((S[i].get("executed") or {}).get("command") or {}).get("obs_id")
                if oid:
                    out[oid] = (T[i - 1]["tracked_world"]["pose"], T[i]["tracked_world"]["pose"])
    return out


def vsys(bdir):
    v = []
    if not bdir:
        return v
    for f in glob.glob(os.path.join(bdir, "episodes", "*", "*steps.jsonl")) + glob.glob(os.path.join(bdir, "episodes", "*", "*", "steps.jsonl")):
        for s in rows(f):
            x = (s.get("car_state") or {}).get("vsys_min_mv")
            if x:
                v.append(x)
    return v


def main():
    sessions = []
    for arg in sys.argv[1:]:
        label, dirs = arg.split("=", 1)
        mdir, bdir = (dirs.split(",") + [None])[:2]
        sessions.append((label, mdir, bdir))

    print("== 1. The stalled moves: heading and place (tracked), then every ~0.1 s: t, duty L / R, speed L / R (m/s)")
    for label, mdir, bdir in sessions:
        where = poses(bdir)
        for path in sorted(glob.glob(os.path.join(mdir, "move_*.jsonl"))):
            r = rows(path)
            stop = next((x for x in r if x.get("ev") == "stop"), {})
            if stop.get("result") != "stalled":
                continue
            head = next((x for x in r if x.get("ev") == "header"), {})
            oid = (head.get("cmd") or {}).get("obs_id")
            p = where.get(oid)
            place = "from (%.2f, %.2f, %.0f deg) to (%.2f, %.2f, %.0f deg)" % (
                p[0]["x_m"], p[0]["y_m"], p[0]["theta_deg"], p[1]["x_m"], p[1]["y_m"], p[1]["theta_deg"]) if p else "(no pose)"
            print("%s %s %s: %s, %s" % (label, os.path.basename(path), (head.get("cmd") or {}).get("action"), stop.get("reason"), place))
            for w in windows(r):
                print("   t %5.2f  duty %+.3f / %+.3f  speed %+.3f / %+.3f%s" % (w["t"], w["dl"], w["dr"], w["vl"], w["vr"],
                                                                           "  (after the stop)" if w["after_stop"] else ""))

    print()
    print("== 2. Straight moves: each wheel's median speed (m/s) by its commanded duty; samples while driven, before the stop")
    print("%-12s %s" % ("session", "  ".join("%.2f-%.2f L / R" % b for b in BINS)))
    need = {}
    for label, mdir, bdir in sessions:
        cells = {b: {"l": [], "r": []} for b in BINS}
        need[label] = {"l": [], "r": []}
        for path in sorted(glob.glob(os.path.join(mdir, "move_*.jsonl"))):
            if "_FORWARD_" not in os.path.basename(path):
                continue
            for w in windows(rows(path)):
                if w["after_stop"]:
                    continue
                for k in ("l", "r"):
                    d, v = w["d" + k], w["v" + k]
                    for b in BINS:
                        if b[0] <= d < b[1]:
                            cells[b][k].append(v)
                    if 0.10 <= v <= 0.13:
                        need[label][k].append(d)
        print("%-12s %s" % (label, "  ".join(
            "%s / %s (%3d)" % ("%.3f" % med(cells[b]["l"]) if cells[b]["l"] else "  -  ",
                               "%.3f" % med(cells[b]["r"]) if cells[b]["r"] else "  -  ",
                               min(len(cells[b]["l"]), len(cells[b]["r"]))) for b in BINS)))
    print("duty each wheel needed while it ran at 0.10-0.13 m/s on straights: median (n)")
    for label, *_ in sessions:
        l, r = need[label]["l"], need[label]["r"]
        print("  %-12s left %s (%d)  right %s (%d)  right minus left %s" % (
            label, "%.3f" % med(l) if l else "-", len(l), "%.3f" % med(r) if r else "-", len(r),
            "%+.3f" % (med(r) - med(l)) if l and r else "-"))

    print()
    print("== 2b. Straights where a wheel, past the first 0.4 s, was driven 0.08 above the duty it normally needs at cruise")
    print("   (right 0.60, left 0.72; their medians at 0.10-0.13 m/s are about 0.52 and 0.64) yet ran under 0.10 m/s: the speed")
    print("   loop pushing a wheel that is held back. Per session: such moves out of all straights; then each, with its place")
    held = {}
    for label, mdir, bdir in sessions:
        where = poses(bdir)
        n_straight, found = 0, []
        for path in sorted(glob.glob(os.path.join(mdir, "move_*.jsonl"))):
            if "_FORWARD_" not in os.path.basename(path):
                continue
            n_straight += 1
            r = rows(path)
            oid = (next((x for x in r if x.get("ev") == "header"), {}).get("cmd") or {}).get("obs_id")
            stop = next((x for x in r if x.get("ev") == "stop"), {})
            hits = {"r": [], "l": []}
            for w in windows(r):
                if w["after_stop"] or w["t"] < 0.4:
                    continue
                for k, o, lim in (("r", "l", 0.60), ("l", "r", 0.72)):
                    if w["d" + k] >= lim and w["v" + k] < 0.10:
                        hits[k].append((w["t"], w["d" + k], w["v" + k], w["v" + o], w["d" + o]))
            for k in ("r", "l"):
                if hits[k]:
                    p = where.get(oid)
                    found.append((k, os.path.basename(path), p, hits[k], stop.get("result")))
        held[label] = (n_straight, found)
        print("  %-12s %3d straights: right held back in %d, left in %d" % (
            label, n_straight, sum(1 for f in found if f[0] == "r"), sum(1 for f in found if f[0] == "l")))
    for label, (n_straight, found) in held.items():
        for k, name, p, hits, result in found:
            place = "(%.2f, %.2f, %.0f deg)" % (p[0]["x_m"], p[0]["y_m"], p[0]["theta_deg"]) if p else "(no pose)"
            print("    %-12s %s %s, %s wheel, result %s: %s" % (
                label, name, place, "right" if k == "r" else "left", result,
                "; ".join("t %.2f duty %.3f speed %.3f (other wheel %.3f at %.3f)" % h for h in hits)))

    print()
    print("== 3. The firmware's stall-assist kicks (a stopped, driven wheel pushed at duty 0.8), per session")
    for label, mdir, bdir in sessions:
        n, kicks = 0, {"left": 0, "right": 0, "both/unclear": 0}
        kinds = {}
        for path in sorted(glob.glob(os.path.join(mdir, "move_*.jsonl"))):
            r = rows(path)
            tel = [x for x in r if x.get("ev") == "tel"]
            n += 1
            for a, b in zip(tel, tel[1:]):
                if b.get("assists", 0) > a.get("assists", 0):
                    dl, dr = abs(b["duty"][0]), abs(b["duty"][1])
                    w = "right" if dr >= 0.79 and dl < 0.79 else "left" if dl >= 0.79 and dr < 0.79 else "both/unclear"
                    kicks[w] += 1
                    kind = "turn" if "_TURN_" in os.path.basename(path) else "straight"
                    kinds[(w, kind)] = kinds.get((w, kind), 0) + 1
        print("  %-12s %4d moves: right %2d, left %2d, unclear %d; %s" % (
            label, n, kicks["right"], kicks["left"], kicks["both/unclear"],
            ", ".join("%s in %ss %d" % (w, k, c) for (w, k), c in sorted(kinds.items())) or "none"))

    print()
    print("== 4. The Pico's supply (car_state.vsys_min_mv: the Pico's own power bank, not the motors' AA pack)")
    for label, mdir, bdir in sessions:
        v = vsys(bdir)
        print("  %-12s %s" % (label, "lowest %d mV, median %d mV over %d readings" % (min(v), med(v), len(v)) if v else
                               "not in this batch's records" if bdir else "(no batch records given)"))


if __name__ == "__main__":
    main()
