"""The nine D5 tools as the agent sees them, the dispatcher that answers them, and the report parser.

Tool names, descriptions and argument types are the ones the Module 4 smoke harness sent
(plan/README.md C4: schemas as in assignments/assignment4/system-prompt/tools/smoke_test.py
`TOOLS`, private course repo), so the pilot's agent sees the same tools as the M1.T11 runs.
run_tool resolves `det` against this step's OBSERVATION and beacon labels against
PREVIOUS_REPORT's map, as AGENT-DESIGN D5 specifies, and refuses what the validator refuses.
Derived from: smoke_test.py `run_tool` (same behaviour, ported to beaconmind.geometry, plus the
replay-mode move refusal).

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: ported the tool table and dispatcher,
added the replay-mode rules and the tolerant report parser.
"""
import json
import re

from beaconmind import geometry as g

TOOLS = [
    ("compose_odometry", "Dead-reckoning prior for one step.",
     {"pose": "object", "forward_m": "number", "left_m": "number", "dtheta_deg": "number"}),
    ("gate_detection", "Gate one detection of this observation against map beacons (labels from PREVIOUS_REPORT).",
     {"pose": "object", "det": "integer", "candidates": "array"}),
    ("fix_pose", "Pose fix from matched confirmed beacons of this observation.",
     {"prior": "object", "matches": "array"}),
    ("map_point", "Map-frame point of a detection seen from pose.", {"pose": "object", "det": "integer"}),
    ("update_beacon", "Running-mean update of a tentative beacon with one detection.",
     {"pose": "object", "det": "integer", "beacon": "string"}),
    ("predict_observation", "Predicted range/bearing to a beacon label or a point {x_m, y_m}.",
     {"pose": "object", "target": "string_or_object"}),
    ("exploration_summary", "12 map-frame sectors with blocked, max_leg_moves, score, turns; new_place.",
     {"pose": "object"}),
    ("move", "Execute one bounded move.", {"action": "string"}),
    ("emergency_stop", "Latch the robot; only the operator clears it.", {"reason": "string"}),
]
MOVES = ("FORWARD_25", "FORWARD_10", "BACKWARD_10", "TURN_LEFT_30", "TURN_RIGHT_30")


def schema(props):
    js = {}
    for k, t in props.items():
        if t == "string_or_object":
            js[k] = {"anyOf": [{"type": "string"}, {"type": "object"}]}
        elif t == "array":
            js[k] = {"type": "array", "items": {}}
        else:
            js[k] = {"type": t}
    return {"type": "object", "properties": js, "required": list(props)}


def anthropic_tool_defs():
    return [{"name": n, "description": d, "input_schema": schema(p)} for n, d, p in TOOLS]


def rnd(o):
    if isinstance(o, float):
        return round(o, 3)
    if isinstance(o, dict):
        return {k: rnd(v) for k, v in o.items()}
    if isinstance(o, list):
        return [rnd(v) for v in o]
    return o


def err(msg):
    return {"status": "error", "error": msg + " Nothing changed."}


def run_tool(name, args, obs, prev, state):
    """Answer one tool call. `state` holds {"moved": action or None, "estop": bool} for this step."""
    dets = {d["det"]: d for d in obs["detections"]}
    bmap = {b["beacon"]: b for b in (prev or {}).get("map", [])}
    mem = (prev or {}).get("memory") or {}
    c, sf = obs["counters"], obs["safety"]
    try:
        if name == "compose_odometry":
            return g.compose_odometry(args["pose"], args["forward_m"], args["left_m"], args["dtheta_deg"])
        if name == "gate_detection":
            labels = args.get("candidates", [])
            bad = [lab for lab in labels if not isinstance(lab, str) or lab not in bmap]
            if bad:
                return err("%s is not a label in PREVIOUS_REPORT's map." % bad)
            cands = {lab: bmap[lab] for lab in labels}
            return g.gate_detection(args["pose"], dets[args["det"]], cands, c["travel_since_fix_m"],
                                    c["odometer_m"], c["turns_since_fix"])
        if name == "fix_pose":
            ms = []
            for m in args["matches"]:
                b = bmap.get(m["beacon"])
                if not b or b["state"] != "confirmed" or b.get("suspect"):
                    return err("%s is not a confirmed, non-suspect beacon in PREVIOUS_REPORT." % m["beacon"])
                ms.append({"det": dets[m["det"]], "point": b})
            return g.fix_pose(args["prior"], ms)
        if name == "map_point":
            d = dets[args["det"]]
            return g.map_point(args["pose"], d["range_m"], d["bearing_deg"])
        if name == "update_beacon":
            b = bmap.get(args["beacon"])
            if not b:
                return err("%s is not a label in PREVIOUS_REPORT's map." % args["beacon"])
            if b["state"] == "confirmed":
                return err("%s is confirmed; confirmed beacons never move." % args["beacon"])
            return g.update_beacon(b, dets[args["det"]], args["pose"])
        if name == "predict_observation":
            t = args["target"]
            if isinstance(t, str):
                t = json.loads(t) if t.strip().startswith("{") else bmap[t]
            return g.predict_observation(args["pose"], t, mem.get("blocked_heading_deg"))
        if name == "exploration_summary":
            return g.exploration_summary(args["pose"], (prev or {}).get("map", []), mem.get("scan_points", []),
                                         mem.get("blocked_heading_deg"))
        if name == "move":
            a = args["action"]
            if obs["mode"] == "replay":
                return {"result": "refused", "reason": "replay mode: the log's move is already executed"}
            if state["estop"] or c["latched"]:
                return {"result": "refused", "reason": "latched"}
            if a not in MOVES:
                return {"result": "refused", "reason": "not a move"}
            if state["moved"]:
                return {"result": "refused", "reason": "one executed move per obs_id"}
            if a.startswith("FORWARD") and a not in sf["forward_allowed"]:
                return {"result": "refused", "reason": "not in forward_allowed"}
            if a == "BACKWARD_10" and not sf["backward_allowed"]:
                return {"result": "refused", "reason": "backward not allowed"}
            if a.startswith("TURN") and not sf["turn_allowed"]:
                return {"result": "refused", "reason": "turn not allowed"}
            state["moved"] = a
            return {"result": "done", "reason": None}
        if name == "emergency_stop":
            state["estop"] = True
            return {"status": "ok", "latched": True}
    except Exception as e:  # tool misuse is reported to the model as the real validator would
        return err("%s: %s." % (type(e).__name__, e))
    return err("unknown tool.")


def parse_report(text):
    """The D8 report from the final text: the whole text, a fenced block, or the outermost {...}."""
    if not text:
        return None
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    for cand in (t, t[t.find("{"): t.rfind("}") + 1] if "{" in t else ""):
        try:
            rep = json.loads(cand)
            if isinstance(rep, dict):
                return rep
        except (ValueError, TypeError):
            continue
    return None


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def report_checks(rep, obs):
    """Validity of a replay-mode report. `valid` needs a parsed report with a numeric pose and a
    map list; the other flags are reported, not gating."""
    rep = rep if isinstance(rep, dict) else None
    pose = rep.get("pose") if rep else None
    pose_ok = isinstance(pose, dict) and all(_num(pose.get(k)) for k in ("x_m", "y_m", "theta_deg"))
    entries = rep.get("map") if rep else None
    map_ok = isinstance(entries, list) and all(
        isinstance(b, dict) and isinstance(b.get("beacon"), str) and _num(b.get("x_m")) and _num(b.get("y_m"))
        and _num(b.get("id")) and b.get("state") in ("tentative", "confirmed") for b in entries)
    return {"parses": rep is not None, "pose_numeric": pose_ok, "map_wellformed": map_ok,
            "step_matches": rep is not None and rep.get("step") == obs["step"],
            "decision_none": rep is not None and rep.get("decision") == "NONE",
            "valid": rep is not None and pose_ok and map_ok}
