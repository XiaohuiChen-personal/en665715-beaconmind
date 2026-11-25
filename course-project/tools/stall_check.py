#!/usr/bin/env python3
"""Classify the stall that halted a batch, read-only: python3 course-project/tools/stall_check.py BATCH_DIR SESSION_DIR

Or, for the stall probe of the duty-floor change: stall_check.py --turn-margins SESSION_DIR prints, for every turn in
the session's move logs, each wheel's lowest speed at the turn's slow end (after its highest duty, at 0.75 to 0.9 of
it: the minimum-rate duty, not the stop), and how many turns fell below 0.02 m/s.

BATCH_DIR is data/batches/<label>; SESSION_DIR is the batch's recorder session, data/real/<...>-batch-<label> (its
moves/ folder holds every move's log with the car's telemetry). Nothing is written and nothing is sent to the car.

It prints the signature of the stalled move:
- the stalled wheel's duty at the stop, and the move's highest duty;
- whether the wheel slowed gradually or stopped abruptly;
- whether the other wheel and the gyro were still moving while it stood;
- the firmware's cut-off and the bump flag;
- the tracked pose's clearance to the edge of the driving area (walls, the desk);
- whether the batch had another stall within 0.30 m of that place.

It ends with a one-line verdict:
- "marginal-duty stall, clear of everything": every one of those signs points to a motor stalling at the slow end
  of a move on carpet, in open floor;
- "possible blockage: do not restart" and the reasons, otherwise.

Background: the b2-real-03 stall (2026-11-25, evidence/M3/M3.T12/batch-runner/b2-real-03/). In 41 of 190 left turns
the right wheel nearly stopped at the turn's minimum duty and recovered; once it did not.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this classifier.
"""
import glob
import json
import math
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "beaconmind" / "src"))

CLEAR_M = 0.30          # the footprint at least this far inside the driving area counts as clear of everything
SAME_PLACE_M = 0.30     # another stall nearer than this counts as the same place
STOPPED_MPS = 0.01      # the executor's stall speed
MOVING_MPS = 0.01
ABRUPT_DROP_MPS = 0.05  # from above this to below STOPPED_MPS in one telemetry sample: abrupt


def move_logs(session):
    return sorted(glob.glob(os.path.join(session, "moves", "move_*.jsonl")))


def read_move(path):
    rows = [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]
    results = [r["result"] for r in rows if r.get("ev") == "result" and isinstance(r.get("result"), dict)]
    return rows, (results[-1] if results else None)


def wheel_speeds(tel, ticks_per_m):
    out = []
    for a, b in zip(tel, tel[1:]):
        dt = b["t_rx"] - a["t_rx"]
        if dt > 0:
            out.append({"t": b["t_rx"], "v": [(b["l"] - a["l"]) / dt / ticks_per_m[0], (b["r"] - a["r"]) / dt / ticks_per_m[1]],
                        "duty": b["duty"], "yaw": b["yaw"], "cut": b.get("cut")})
    return out


def signature(path):
    rows, result = read_move(path)
    header = rows[0]
    cfg = header.get("config") or {}
    tpm = (float(cfg.get("ticks_per_m_left") or 19385.0), float(cfg.get("ticks_per_m_right") or 19804.0))
    tel = [r for r in rows if r.get("ev") == "tel"]
    stop = [r for r in rows if r.get("ev") == "stop"]
    reason = (result or {}).get("reason") or (stop[-1].get("reason") if stop else None) or ""
    wheel = 1 if "right" in reason else 0
    other = 1 - wheel
    v = wheel_speeds(tel, tpm)
    t_stop = stop[-1]["t"] if stop else (v[-1]["t"] if v else 0.0)
    driven = [s for s in v if s["t"] <= t_stop + 1e-6 and abs(s["duty"][wheel]) > 0]
    sig = {"move": os.path.basename(path), "action": header["cmd"]["action"], "result": (result or {}).get("result"),
           "reason": reason, "wheel": "right" if wheel else "left", "bump": bool((result or {}).get("bump")),
           "firmware_cut": any(s.get("cut") for s in v), "duty_at_stop": None, "max_duty": None, "deceleration": None,
           "other_wheel_mps": None, "gyro_deg_while_stopped": None}
    if not driven:
        return sig
    sig["duty_at_stop"] = abs(driven[-1]["duty"][wheel])
    sig["max_duty"] = max(abs(s["duty"][wheel]) for s in driven)
    # the run of samples at the end in which the stalled wheel stood
    k = len(driven)
    while k > 0 and abs(driven[k - 1]["v"][wheel]) < STOPPED_MPS:
        k -= 1
    still = driven[k:]
    before = driven[:k]
    if still and before:
        last_moving = abs(before[-1]["v"][wheel])
        sig["deceleration"] = "abrupt" if last_moving > ABRUPT_DROP_MPS else "gradual"
        sig["decel_mps"] = [round(abs(s["v"][wheel]), 3) for s in before[-6:]] + [0.0]
    elif still:
        sig["deceleration"] = "stood from the start"
    if still:
        sig["stood_s"] = round(still[-1]["t"] - still[0]["t"] + (still[0]["t"] - before[-1]["t"] if before else 0.0), 3)
        sig["other_wheel_mps"] = round(sorted(abs(s["v"][other]) for s in still)[len(still) // 2], 3)
        sig["gyro_deg_while_stopped"] = round(abs(still[-1]["yaw"] - (before[-1]["yaw"] if before else still[0]["yaw"])), 2)
    return sig


def batch_rows(batch):
    """Every step row of the batch with its truth row, in time order: (steps row, truth row)."""
    out = []
    for steps in glob.glob(os.path.join(batch, "episodes", "*", "*", "steps.jsonl")) + \
            glob.glob(os.path.join(batch, "episodes", "*", "steps.jsonl")):
        d = os.path.dirname(steps)
        truth = os.path.join(d, "truth.jsonl") if os.path.basename(d) != "backend" else os.path.join(os.path.dirname(d), "truth.jsonl")
        if not os.path.exists(truth):
            continue
        st = [json.loads(line) for line in open(steps, encoding="utf-8") if line.strip()]
        tr = [json.loads(line) for line in open(truth, encoding="utf-8") if line.strip()]
        out += list(zip(st, tr))
    return sorted(out, key=lambda rt: rt[0].get("t_unix") or 0.0)


def turn_margins(session):
    """Every turn's lowest wheel speed at its slow end, and the count of near-stalls."""
    near, n = 0, 0
    for path in move_logs(session):
        rows, result = read_move(path)
        if not rows or not rows[0].get("cmd", {}).get("action", "").startswith("TURN") or result is None:
            continue
        cfg = rows[0].get("config") or {}
        tpm = (float(cfg.get("ticks_per_m_left") or 19385.0), float(cfg.get("ticks_per_m_right") or 19804.0))
        v = wheel_speeds([r for r in rows if r.get("ev") == "tel"], tpm)
        lows = []
        for w in (0, 1):
            driven = [s for s in v if abs(s["duty"][w]) > 0]
            if not driven:
                lows.append(None)
                continue
            top = max(abs(s["duty"][w]) for s in driven)
            last_top = max(i for i, s in enumerate(driven) if abs(s["duty"][w]) >= top - 1e-9)
            # the slow end: after the last sample at the highest duty, at the turn's minimum-rate duty (0.75 to 0.9 of
            # the highest: 0.295 of 0.341 today), not the stop itself or a trim
            slow = [abs(s["v"][w]) for s in driven[last_top + 1:] if 0.75 * top <= abs(s["duty"][w]) < 0.9 * top]
            lows.append(min(slow) if slow else None)
        n += 1
        low = min(x for x in lows if x is not None) if any(x is not None for x in lows) else None
        near += low is not None and low < 0.02
        print("%s %-13s %-8s lowest at the slow end: left %s right %s m/s" % (
            os.path.basename(path), rows[0]["cmd"]["action"], result.get("result"),
            "%.3f" % lows[0] if lows[0] is not None else "-", "%.3f" % lows[1] if lows[1] is not None else "-"))
    print("%d turns; %d with a wheel below 0.02 m/s at the slow end" % (n, near))
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 2 and argv[0] == "--turn-margins":
        return turn_margins(argv[1])
    if len(argv) != 2:
        sys.exit(__doc__.split("\n")[0])
    batch, session = argv
    man = json.loads(open(os.path.join(batch, "manifest.json"), encoding="utf-8").read())
    print("batch %s: %s, halt %s" % (os.path.basename(os.path.normpath(batch)), man.get("status"),
                                     (man.get("halt") or {}).get("detail")))
    logs = move_logs(session)
    stalled = [p for p in logs if (read_move(p)[1] or {}).get("result") == "stalled"]
    if not stalled:
        print("no stalled move in %s" % os.path.join(session, "moves"))
        return 2
    sig = signature(stalled[-1])
    print("stalled move: %s %s, %s (%s wheel)" % (sig["move"], sig["action"], sig["reason"], sig["wheel"]))
    print("  duty at the stop %.3f (the move's highest %.3f)" % (sig["duty_at_stop"] or 0, sig["max_duty"] or 0))
    print("  deceleration: %s %s" % (sig["deceleration"], sig.get("decel_mps", "")))
    print("  while it stood (%.2f s): other wheel %s m/s, gyro turned %s deg" % (sig.get("stood_s") or 0, sig["other_wheel_mps"],
                                                                         sig["gyro_deg_while_stopped"]))
    print("  firmware cut-off %s, bump %s" % (sig["firmware_cut"], sig["bump"]))

    from beaconmind.car import batch as B
    from beaconmind.car.config import load_car
    world_path = man["params"]["world_path"]
    world_path = world_path if os.path.isabs(world_path) else str(ROOT / world_path)
    world = json.loads(open(world_path, encoding="utf-8").read())
    car = load_car()
    p = man["params"]
    guard = B.MoveGuard(world, [tuple(c) for c in car["corners"]], float(car["sweep_radius_m"]), p["wall_margin_m"],
                        p["sigma_block_m"])
    rows = batch_rows(batch)
    stalls = [(s, t) for s, t in rows if ((s.get("executed") or {}).get("result") or {}).get("result") == "stalled"]
    here = (stalls[-1][1] if stalls else rows[-1][1])["tracked_world"]
    pose = here["pose"]
    depth = guard.footprint_depth(pose)
    print("  tracked pose (%.3f, %.3f, %.1f deg), sigma %.3f m: footprint %.2f m inside the driving area, axle %.2f m, "
          "turn room %.2f m" % (pose["x_m"], pose["y_m"], pose["theta_deg"], here["sigma_xy_m"], depth,
                                guard.axle_depth(pose), guard.axle_depth(pose) - guard.sweep_radius_m))
    earlier = [t["tracked_world"]["pose"] for s, t in stalls[:-1]]
    near = [q for q in earlier if math.hypot(q["x_m"] - pose["x_m"], q["y_m"] - pose["y_m"]) < SAME_PLACE_M]
    print("  stalls in this batch: %d; earlier ones within %.2f m of here: %d" % (len(stalls), SAME_PLACE_M, len(near)))

    reasons = []
    if sig["firmware_cut"]:
        reasons.append("the firmware cut the motors")
    if sig["bump"]:
        reasons.append("a bump was flagged")
    if sig["deceleration"] != "gradual":
        reasons.append("the wheel stopped %s" % (sig["deceleration"] or "without a record"))
    if not sig["max_duty"] or (sig["duty_at_stop"] or 0) > 0.9 * sig["max_duty"]:
        reasons.append("it stalled at full duty, not at the slow end of the move")
    if (sig["other_wheel_mps"] or 0) < MOVING_MPS:
        reasons.append("the other wheel stood too")
    if (sig["gyro_deg_while_stopped"] or 0) < 1.0 and sig["action"].startswith("TURN"):
        reasons.append("the car stopped turning")
    if depth < CLEAR_M:
        reasons.append("the footprint is only %.2f m inside the driving area" % depth)
    if near:
        reasons.append("another stall happened within %.2f m" % SAME_PLACE_M)
    if reasons:
        print("VERDICT: possible blockage: do not restart (%s)" % "; ".join(reasons))
        return 1
    print("VERDICT: marginal-duty stall, clear of everything")
    return 0


if __name__ == "__main__":
    sys.exit(main())
