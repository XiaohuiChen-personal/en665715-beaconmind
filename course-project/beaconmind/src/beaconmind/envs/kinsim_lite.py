"""Kinematic pilot simulator ("kinsim-lite") and the coded per-step procedure (arm B2).

Derived from backstory_sim.py in the private course repo
(assignments/assignment4/system-prompt/tools/, written by Claude Opus 5.5 on 2026-09-27 for
Xiaohui Chen's Module 4 work). Ported onto beaconmind.geometry and split into
estimate_step (AGENT-DESIGN D7 rules 1-6; it also lists the tool calls the procedure makes,
which are the gold calls for tool-call F1) and decide_step (D7 rule 7, EXPLORE rows).
The noise model is the placeholder of plan/M2-sim-mvp.md M2.T3; the world generator follows
AGENT-DESIGN D3 (tags on the walls, at most two physical tags per ID, copies >= 1.5 m apart).

Not implemented, so they raise NotImplementedError instead of deviating (as in the original):
drift recovery and relocalisation, ambiguous associations, the E2 abandon branch, an E5 leg with
no forward move. Contacts, slips and null tag IDs are not simulated. Moves always complete.

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: ported and restructured the simulator,
added the noise model, the world generator and the gold-call lists.
"""
import copy
import math
import random

from beaconmind import geometry as g

# The DV arena of the Module 4 backstory: a 2.25 m square, start pose (0, 0, 0) facing +x.
ARENA = {"x0": -1.0, "x1": 1.25, "y0": -1.0, "y1": 1.25}

# plan/M2-sim-mvp.md M2.T3 placeholder fixtures (detector_noise_placeholder.json and
# configs/odometry_noise.json as specified there); quality is the backstory's constant.
NOISE = {
    "hfov_deg": 60.0, "min_range_m": 0.25, "max_range_m": 1.5, "max_incidence_deg": 60.0,
    "range_sigma_a_m": 0.01, "range_sigma_b": 0.03, "bearing_sigma_deg": 1.0, "p_detect": 0.95,
    "wheel_scale_sigma": 0.02, "gyro_sigma_deg": 0.3, "quality": 0.9,
}
WALL_LIMIT_M = 0.35          # backstory validator DV: a forward move leaves >= 0.35 m to the wall
STEPS_BUDGET = 150           # AGENT-DESIGN D4, EXPLORE
DONE_RANGE_M = 0.55          # configs/dv.json done_range_m (placeholder)
FIX_SOURCES = ("beacon_fix", "relocalised")


class GoldUnavailable(Exception):
    """The coded procedure cannot process this input (an unimplemented branch or a malformed report)."""


# ---------------------------------------------------------------- world and sensing

def make_world(seed, n_dup=3):
    """Seeded D3 world: 12-16 tags spread over the four walls, IDs from 0-29, n_dup IDs used twice
    with the two copies >= 1.5 m apart. Each tag: {tag, id, x_m, y_m, wall}."""
    rng = random.Random("world-%s" % seed)
    side = ARENA["x1"] - ARENA["x0"]
    n = rng.randint(12, 16)
    counts = [n // 4] * 4
    for i in rng.sample(range(4), n % 4):
        counts[i] += 1
    pos = []
    for wall, k in zip("SENW", counts):
        for i in range(k):
            s = (i + 0.5) / k * side + rng.uniform(-0.05, 0.05)
            if wall == "S":
                p = (ARENA["x0"] + s, ARENA["y0"])
            elif wall == "E":
                p = (ARENA["x1"], ARENA["y0"] + s)
            elif wall == "N":
                p = (ARENA["x1"] - s, ARENA["y1"])
            else:
                p = (ARENA["x0"], ARENA["y1"] - s)
            pos.append((round(p[0], 3), round(p[1], 3), wall))
    for _ in range(200):
        order = list(range(n))
        rng.shuffle(order)
        ids = rng.sample(range(30), n - n_dup)
        tags = [None] * n
        for k, idx in enumerate(order[: n - n_dup]):
            tags[idx] = ids[k]
        free = order[n - n_dup:]
        ok = True
        for id_ in rng.sample(ids, len(ids)):
            if not free:
                break
            src = tags.index(id_)
            far = [f for f in free if math.hypot(pos[f][0] - pos[src][0], pos[f][1] - pos[src][1]) >= 1.5]
            if far:
                f = far[0]
                tags[f] = id_
                free.remove(f)
        if free:
            ok = False
        if ok:
            return [{"tag": i, "id": tags[i], "x_m": pos[i][0], "y_m": pos[i][1], "wall": pos[i][2]}
                    for i in range(n)]
    raise RuntimeError("no D3 world for seed %s" % seed)


def _normal(t):
    return {"S": (0.0, 1.0), "N": (0.0, -1.0), "W": (1.0, 0.0), "E": (-1.0, 0.0)}[t["wall"]]


def incidence_deg(pose, t):
    dx, dy = pose["x_m"] - t["x_m"], pose["y_m"] - t["y_m"]
    r = math.hypot(dx, dy)
    nx, ny = _normal(t)
    return math.degrees(math.acos(max(-1.0, min(1.0, (dx * nx + dy * ny) / r))))


def detect(world, pose, rng):
    """Tags inside the field of view, the range window and the incidence limit, each kept with
    probability p_detect, with range noise N(0, a + b*r) and bearing noise N(0, sigma)."""
    out = []
    for t in world:
        o = g.predict_observation(pose, t)
        r, b = o["range_m"], o["bearing_deg"]
        if abs(b) > NOISE["hfov_deg"] / 2 or not NOISE["min_range_m"] <= r <= NOISE["max_range_m"]:
            continue
        if incidence_deg(pose, t) > NOISE["max_incidence_deg"]:
            continue
        if rng.random() > NOISE["p_detect"]:
            continue
        rn = r + rng.gauss(0.0, NOISE["range_sigma_a_m"] + NOISE["range_sigma_b"] * r)
        bn = b + rng.gauss(0.0, NOISE["bearing_sigma_deg"])
        out.append({"id": t["id"], "range_m": round(rn, 2), "bearing_deg": round(bn, 1),
                    "quality": NOISE["quality"], "_tag": t["tag"]})
    for i, d in enumerate(out):
        d["det"] = i
    return out


def wall_distance_ahead(pose):
    x, y, th = pose["x_m"], pose["y_m"], math.radians(pose["theta_deg"])
    c, s = math.cos(th), math.sin(th)
    ts = []
    if c > 1e-9:
        ts.append((ARENA["x1"] - x) / c)
    if c < -1e-9:
        ts.append((ARENA["x0"] - x) / c)
    if s > 1e-9:
        ts.append((ARENA["y1"] - y) / s)
    if s < -1e-9:
        ts.append((ARENA["y0"] - y) / s)
    return min(t for t in ts if t >= 0)


def forward_allowed(pose):
    d = wall_distance_ahead(pose)
    return [m for m, step in (("FORWARD_25", 0.25), ("FORWARD_10", 0.10)) if d - step >= WALL_LIMIT_M]


def initial_memory():
    return {"scan_points": [], "scan_index": 0, "scan_turns_left": 0, "scan_added": 0, "scans_without_new": 0,
            "legs_since_scan": 0, "target_heading_deg": None, "leg_moves_left": 0, "blocked_heading_deg": None,
            "recovery": "none", "stuck": 0}


def rp(p):
    return {"x_m": round(p["x_m"], 2), "y_m": round(p["y_m"], 2), "theta_deg": round(p["theta_deg"], 1)}


# ---------------------------------------------------------------- D7 rules 1-6 (estimation)

def _pose(p):
    return {"x_m": float(p["x_m"]), "y_m": float(p["y_m"]), "theta_deg": float(p["theta_deg"])}


def estimate_step(obs, prev_report):
    """D7 rules 1-6 for one observation. obs carries detections (det, id, range_m, bearing_deg),
    odometry (or None at step 0) and counters (travel_since_fix_m, odometer_m, turns_since_fix).
    Returns prior, pose, pose_source, associations (with gate results), new map, new entries,
    loop closures and `calls`: the tool calls the procedure makes, as (name, args) pairs."""
    try:
        return _estimate(obs, prev_report)
    except NotImplementedError:
        raise
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        raise GoldUnavailable("%s: %s" % (type(exc).__name__, exc)) from exc


def _estimate(obs, prev_report):
    calls = []
    dets = obs["detections"]
    counters = obs["counters"]
    if prev_report is None:
        prior = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
        cur_map = []
    else:
        odo = obs["odometry"]
        prev_pose = _pose(prev_report["pose"])
        prior = g.compose_odometry(prev_pose, odo["forward_m"], odo["left_m"], odo["dtheta_deg"])
        calls.append(("compose_odometry", {"pose": prev_pose, "forward_m": odo["forward_m"],
                                           "left_m": odo["left_m"], "dtheta_deg": odo["dtheta_deg"]}))
        cur_map = copy.deepcopy(prev_report["map"])
    # rule 3: association
    assoc = []
    for d in dets:
        cands = {b["beacon"]: b for b in cur_map if b["id"] == d["id"]}
        if not cands:
            assoc.append(({"det": d["det"], "id": d["id"], "beacon": "B%d" % d["id"], "result": "new"}, None))
            continue
        calls.append(("gate_detection", {"pose": prior, "det": d["det"], "candidates": sorted(cands)}))
        gd = g.gate_detection(prior, d, cands, counters["travel_since_fix_m"], counters["odometer_m"],
                              counters["turns_since_fix"])
        ing = [c for c in gd["candidates"] if c["in_gate"]]
        if len(ing) == 1:
            a = {"det": d["det"], "id": d["id"], "beacon": ing[0]["beacon"], "result": "matched"}
        elif len(ing) > 1:
            raise NotImplementedError("ambiguous association")
        elif all(c["point_distance_m"] > 1.0 for c in gd["candidates"]):
            labs = set(cands)
            if "B%d" % d["id"] in labs and "B%db" % d["id"] in labs:
                a = {"det": d["det"], "id": d["id"], "beacon": None, "result": "rejected"}
            else:
                lab = "B%db" % d["id"] if "B%d" % d["id"] in labs else "B%d" % d["id"]
                a = {"det": d["det"], "id": d["id"], "beacon": lab, "result": "new"}
        else:
            near = min(gd["candidates"], key=lambda c: c["point_distance_m"])["beacon"]
            a = {"det": d["det"], "id": d["id"], "beacon": near, "result": "rejected", "conflict": True}
        assoc.append((a, gd))
    single_conf = {b["id"] for b in cur_map if b["state"] == "confirmed"
                   and sum(1 for c in cur_map if c["id"] == b["id"]) == 1}
    if sum(1 for a, _ in assoc if a["id"] in single_conf and a["result"] != "matched") >= 3:
        raise NotImplementedError("drift recovery")
    # rule 4: pose correction
    bmap = {b["beacon"]: b for b in cur_map}
    dmap = {d["det"]: d for d in dets}
    matched = [(dmap[a["det"]], bmap[a["beacon"]]) for a, _ in assoc if a["result"] == "matched"]
    conf = [(d, b) for d, b in matched if b["state"] == "confirmed" and not b.get("suspect", False)]
    pose_source, pose, fix_beacons = "odometry", prior, []
    if conf:
        calls.append(("fix_pose", {"prior": prior, "matches": [{"det": d["det"], "beacon": b["beacon"]} for d, b in conf]}))
        fx = g.fix_pose(prior, [{"det": d, "point": b} for d, b in conf])
        full, pos = fx["full"], fx["position"]
        if full and full["well_conditioned"] and full["within_prior_gate"]:
            pose_source, pose = "beacon_fix", {k: full[k] for k in ("x_m", "y_m", "theta_deg")}
            fix_beacons = [b["beacon"] for _, b in conf]
        elif full and full["relocalisation_ok"] and not full["within_prior_gate"]:
            raise NotImplementedError("relocalised")
        elif pos["within_prior_gate"] and pos["heading_safe"]:
            pose_source, pose = "position_fix", {k: pos[k] for k in ("x_m", "y_m", "theta_deg")}
        else:
            pose_source = "prior_kept"
    if pose_source == "prior_kept":
        assoc = [(dict(a, result="rejected", beacon=None), gd) for a, gd in assoc]
    # rules 5 and 6: map update and loop closure (first_seen_scan is set after the decision)
    new_map = copy.deepcopy(cur_map)
    nm = {b["beacon"]: b for b in new_map}
    new_entries, loop_closure = [], []
    for (a, gd), d in zip(assoc, dets):
        if a["result"] == "new":
            calls.append(("map_point", {"pose": pose, "det": d["det"]}))
            p = g.map_point(pose, d["range_m"], d["bearing_deg"])
            e = {"beacon": a["beacon"], "id": d["id"], "x_m": round(p["x_m"], 2), "y_m": round(p["y_m"], 2),
                 "n_obs": 1, "state": "tentative", "first_seen_from": [round(pose["x_m"], 2), round(pose["y_m"], 2)],
                 "first_seen_scan": None, "odo_last_seen_m": counters["odometer_m"], "conflicts": 0, "suspect": False}
            new_map.append(e)
            new_entries.append(e)
        elif a["result"] == "matched":
            b = nm[a["beacon"]]
            if b["state"] == "tentative":
                calls.append(("update_beacon", {"pose": pose, "det": d["det"], "beacon": b["beacon"]}))
                u = g.update_beacon(b, d, pose)
                b.update(x_m=round(u["x_m"], 2), y_m=round(u["y_m"], 2), n_obs=u["n_obs"])
                if u["n_obs"] >= 2 and u["baseline_m"] >= 0.40:
                    b["state"] = "confirmed"
            b["conflicts"], b["suspect"] = 0, False
            cand = next(c for c in gd["candidates"] if c["beacon"] == a["beacon"])
            if cand.get("revisit"):
                loop_closure.append({"beacon": a["beacon"], "accepted": pose_source == "beacon_fix" and a["beacon"] in fix_beacons,
                                     "reason": "revisit in %s" % pose_source})
            b["odo_last_seen_m"] = counters["odometer_m"]
        elif a.get("conflict") and pose_source in ("beacon_fix", "position_fix"):
            b = nm[a["beacon"]]
            b["conflicts"] = b.get("conflicts", 0) + 1
            b["suspect"] = b["conflicts"] >= 2
    return {"prior": prior, "pose": pose, "pose_source": pose_source, "assoc": assoc, "cur_map": cur_map,
            "new_map": new_map, "new_entries": new_entries, "loop_closure": loop_closure, "calls": calls}


# ---------------------------------------------------------------- D7 rule 7 (EXPLORE decision)

def decide_step(est, mem, safety, steps_left):
    """EXPLORE rows E1-E5 on the estimate of this step. Returns (decision, new memory)."""
    pose, cur_map, new_entries = est["pose"], est["cur_map"], est["new_entries"]
    m2 = copy.deepcopy(mem)
    n_new = len(new_entries)
    scan_before = m2["scan_turns_left"] > 0
    state = {"counted": False, "started": False}
    ex = g.exploration_summary(pose, cur_map, m2["scan_points"], m2["blocked_heading_deg"])

    def e2():
        if not safety["turn_allowed"]:
            raise NotImplementedError("E2 abandon branch (turns are always allowed in this simulation)")
        m2["scan_turns_left"] -= 1
        if m2["scan_turns_left"] == 0:
            m2["scan_added"] += n_new
            state["counted"] = True
            m2["scans_without_new"] = 0 if m2["scan_added"] > 0 else m2["scans_without_new"] + 1
        return "TURN_LEFT_30"

    def e4():
        m2["scan_points"].append([round(pose["x_m"], 2), round(pose["y_m"], 2)])
        m2["scan_index"] += 1
        m2.update(scan_added=0, scan_turns_left=12, legs_since_scan=0, target_heading_deg=None)
        state["started"] = True
        return e2()

    def e3():
        sec = next(s for s in ex["sectors"] if s["heading_deg"] == m2["target_heading_deg"])
        if sec["turns"] != 0:
            return "TURN_LEFT_30" if sec["turns"] > 0 else "TURN_RIGHT_30"
        if safety["forward_allowed"]:
            m2["leg_moves_left"] -= 1
            return safety["forward_allowed"][0]
        m2["leg_moves_left"] = 0
        return None

    def e4_or_e5(after_e5=False):
        if (ex["new_place"] or m2["legs_since_scan"] >= 2) and safety["scan_allowed"]:
            return e4()
        if after_e5:
            raise NotImplementedError("E5 leg with no forward move and no E4")
        cands = [s for s in ex["sectors"] if not s["blocked"]]
        if not cands:
            return "DONE"
        best = max(cands, key=lambda s: (round(s["score"], 9), -abs(s["turns"]), s["turns"] > 0))
        m2["target_heading_deg"] = best["heading_deg"]
        m2["leg_moves_left"] = best["max_leg_moves"]
        m2["legs_since_scan"] += 1
        return e3() or e4_or_e5(after_e5=True)

    # backstory_sim.py's E1 test, kept as written there (a new entry this step always blocks E1)
    tentative_blocks = any(b["state"] == "tentative" and b["first_seen_scan"] >= m2["scan_index"] - 1
                           for b in cur_map) or bool(new_entries)
    if (m2["scans_without_new"] >= 2 and not tentative_blocks) or steps_left == 0:
        decision = "DONE"
    elif m2["scan_turns_left"] > 0:
        decision = e2()
    elif m2["leg_moves_left"] > 0:
        decision = e3() or e4_or_e5()
    else:
        decision = e4_or_e5()
    if not state["counted"] and (scan_before or state["started"]):
        m2["scan_added"] += n_new
    return decision, m2


# ---------------------------------------------------------------- closed-loop episode with arm B2

def counters_from(odometer_m, travel_since_fix_m, turns_since_fix):
    return {"odometer_m": round(odometer_m, 2), "travel_since_fix_m": round(travel_since_fix_m, 2),
            "turns_since_fix": turns_since_fix}


def run_episode(seed, max_steps=STEPS_BUDGET, n_dup=3, odo_bias=0.0):
    """Closed-loop EXPLORE episode driven by the coded procedure (arm B2). Returns
    {"seed", "world", "records"}; each record holds the truth pose, the raw observation (with
    each detection's true tag in `_tag`), B2's report and B2's tool calls.
    odo_bias: systematic odometry over-read (forward distance and turn angle both reported as
    (1 + odo_bias) times the true move) for the baseline sensitivity sweep; 0 in the pilot."""
    world = make_world(seed, n_dup=n_dup)
    rng = random.Random("noise-%s" % seed)
    truth = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
    prev_report, last_move, odo = None, None, None
    odometer, travel, turns = 0.0, 0.0, 0
    records = []
    for step in range(max_steps):
        dets = detect(world, truth, rng)
        steps_left = STEPS_BUDGET - step
        safety = {"forward_allowed": forward_allowed(truth),
                  "backward_allowed": bool(last_move and last_move.startswith("FORWARD")),
                  "turn_allowed": True, "scan_allowed": True}
        raw = {"step": step, "odometry": odo,
               "last_move": {"action": last_move, "result": "done"} if last_move else None,
               "counters": dict(counters_from(odometer, travel, turns), steps_left=steps_left),
               "safety": safety, "detections": dets}
        est = estimate_step(raw, prev_report)
        mem = initial_memory() if prev_report is None else prev_report["memory"]
        decision, m2 = decide_step(est, mem, safety, steps_left)
        for e in est["new_entries"]:
            e["first_seen_scan"] = m2["scan_index"]
        report = {"step": step, "mode": "closed_loop", "mission": "EXPLORE", "pose": rp(est["pose"]),
                  "pose_source": est["pose_source"],
                  "associations": [{k: v for k, v in a.items() if k != "conflict"} for a, _ in est["assoc"]],
                  "loop_closure": est["loop_closure"], "map": est["new_map"], "memory": m2, "decision": decision,
                  "move_result": "done" if decision.startswith(("FORWARD", "TURN", "BACKWARD")) else "not_called",
                  "requested_mission": None, "message": None, "note": None}
        records.append({"step": step, "truth": dict(truth), "raw": raw, "report": report,
                        "calls": [[n, a] for n, a in est["calls"]]})
        if decision == "DONE":
            break
        if est["pose_source"] in FIX_SOURCES:
            travel, turns = 0.0, 0
        if decision.startswith("FORWARD"):
            f = 0.25 if decision == "FORWARD_25" else 0.10
            truth = g.compose_odometry(truth, f, 0.0, 0.0)
            fm = round(f * (1 + odo_bias + rng.gauss(0.0, NOISE["wheel_scale_sigma"])), 2)
            odometer += fm
            travel += fm
            odo = {"forward_m": fm, "left_m": 0.0, "dtheta_deg": 0.0}
        else:
            dth = 30.0 if decision == "TURN_LEFT_30" else -30.0
            truth = g.compose_odometry(truth, 0.0, 0.0, dth)
            turns += 1
            odo = {"forward_m": 0.0, "left_m": 0.0,
                   "dtheta_deg": round(dth * (1 + odo_bias) + rng.gauss(0.0, NOISE["gyro_sigma_deg"]), 1)}
        last_move = decision
        prev_report = report
    return {"seed": seed, "world": world, "records": records}


# ---------------------------------------------------------------- replay inputs and arm B0

def as_observation(seed, raw, counters, mode="replay"):
    """C3 OBSERVATION for the agent: the raw record without the true tag, with the arm's own
    counters (travel_since_fix_m and turns_since_fix depend on the arm's own fix history)."""
    odo = raw["odometry"]
    return {"obs_id": "s%s-%03d" % (seed, raw["step"]), "step": raw["step"], "source": "sim", "mode": mode,
            "status": "ok", "error": None, "sensors": {"camera": "ok", "imu": "ok", "pico": "armed"},
            "odometry": dict(odo, quality="ok") if odo else None, "last_move": raw["last_move"],
            "counters": {"steps_left": raw["counters"]["steps_left"], "odometer_m": counters["odometer_m"],
                         "travel_since_fix_m": counters["travel_since_fix_m"],
                         "turns_since_fix": counters["turns_since_fix"], "consecutive_contacts": 0,
                         "consecutive_slips": 0, "consecutive_errors": 0, "latched": False},
            "safety": dict(raw["safety"], done_range_m=DONE_RANGE_M),
            "detections": [{k: v for k, v in d.items() if k != "_tag"} for d in raw["detections"]]}


class CounterTracker:
    """Harness counters for one arm: odometer, travel and turns since the arm's last full fix."""

    def __init__(self):
        self.odometer, self.travel, self.turns = 0.0, 0.0, 0

    def before_step(self, raw, prev_pose_source):
        """Update with the move that led to this observation, after the previous report."""
        if prev_pose_source in FIX_SOURCES:
            self.travel, self.turns = 0.0, 0
        odo = raw["odometry"]
        if odo:
            if odo["forward_m"]:
                self.odometer += abs(odo["forward_m"])
                self.travel += abs(odo["forward_m"])
            elif raw["last_move"] and raw["last_move"]["action"].startswith("TURN"):
                self.turns += 1
        return counters_from(self.odometer, self.travel, self.turns)


def dead_reckoning(records):
    """Arm B0: compose the odometry from the start pose; no map."""
    pose, out = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}, []
    for r in records:
        odo = r["raw"]["odometry"]
        if odo:
            pose = g.compose_odometry(pose, odo["forward_m"], odo["left_m"], odo["dtheta_deg"])
        out.append(dict(pose))
    return out
