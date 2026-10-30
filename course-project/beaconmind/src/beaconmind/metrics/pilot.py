"""Pilot metrics: trajectory, map and association error against simulator truth, and tool-call
precision/recall/F1 against the coded procedure's calls on the same input.

Ground truth: the simulator's true pose at every step and the true tag behind every detection
(kinsim_lite records it in `_tag`). Gold tool calls: kinsim_lite.estimate_step applied to the very
OBSERVATION and PREVIOUS_REPORT the agent received, so a call is judged against what the D7
procedure would call from the agent's own state (plan/README.md C10; tool-call F1 as in the
Module 9 notes, with an argument-matching rule in the spirit of BFCL's AST matching).

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: wrote these metric definitions and code.
"""
import math

from beaconmind.envs import kinsim_lite as ks
from beaconmind.geometry import wrap_deg

POSE_TOL_M, POSE_TOL_DEG, ODO_TOL = 0.011, 0.11, 1e-6   # 2-dp pose rounding plus margin


# ---------------------------------------------------------------- trajectory

def trajectory_errors(est, truth):
    """est, truth: lists of poses. Returns ATE-RMSE (m, unaligned: the map frame is the start pose),
    heading RMSE (deg), final position error (m), final heading error (deg) and the per-step errors."""
    if not est or len(est) != len(truth):
        raise ValueError("trajectory lengths differ or are empty: %d vs %d" % (len(est), len(truth)))
    pos = [math.hypot(e["x_m"] - t["x_m"], e["y_m"] - t["y_m"]) for e, t in zip(est, truth)]
    hd = [abs(wrap_deg(e["theta_deg"] - t["theta_deg"])) for e, t in zip(est, truth)]
    n = len(pos)
    return {"ate_m": math.sqrt(sum(p * p for p in pos) / n), "heading_rmse_deg": math.sqrt(sum(h * h for h in hd) / n),
            "final_pos_m": pos[-1], "final_heading_deg": hd[-1], "max_pos_m": max(pos), "per_step_m": pos}


# ---------------------------------------------------------------- map and association

class LabelTracker:
    """Which physical tag each map label stands for. A label is bound to a tag when an association
    labelled `new` creates it AND the label is in the map the arm carries forward from that step."""

    def __init__(self):
        self.tag_of = {}

    def score_step(self, report, prev_report, raw_dets, dup_ids):
        """Score every detection of this step (plan/README.md C10.4). `report` is the report the arm
        carries forward, `prev_report` the one it received. A detection of a tag already in the
        previous map: TP = matched to the beacon created from that tag, FP = matched to another tag's
        beacon, FN = labelled new, ambiguous or rejected, or not associated at all. A first sighting
        labelled new is NEW_OK (NEW_BAD if the label already stands for another tag). dup_ids are the
        IDs that two physical tags share. Returns [(true_id_is_duplicated, outcome)]."""
        prev_labels = {b.get("beacon") for b in (prev_report or {}).get("map") or [] if isinstance(b, dict)}
        mapped = {self.tag_of[lab] for lab in prev_labels if lab in self.tag_of}
        assoc = {}
        for a in (report or {}).get("associations") or []:
            if isinstance(a, dict) and isinstance(a.get("det"), int) and not isinstance(a.get("det"), bool):
                assoc.setdefault(a["det"], a)
        out = []
        for d in raw_dets:
            tag, dup = d["_tag"], d["id"] in dup_ids
            a = assoc.get(d["det"])
            kind, lab = (a.get("result"), a.get("beacon")) if a else (None, None)
            if kind == "matched":
                out.append((dup, "TP" if self.tag_of.get(lab) == tag else "FP"))
            elif tag in mapped:
                out.append((dup, "FN"))
            elif kind == "new":
                out.append((dup, "NEW_OK" if self.tag_of.get(lab, tag) == tag else "NEW_BAD"))
            else:
                out.append((dup, "OTHER"))
        carried = {b.get("beacon") for b in (report or {}).get("map") or [] if isinstance(b, dict)}
        for d in raw_dets:
            a = assoc.get(d["det"])
            if a and a.get("result") == "new" and a.get("beacon") in carried and a.get("beacon") not in self.tag_of:
                self.tag_of[a["beacon"]] = d["_tag"]
        return out


def association_scores(outcomes):
    """C10.4 precision (primary) and recall over re-sightings, from score_step outcomes."""
    tp = sum(1 for _, o in outcomes if o == "TP")
    fp = sum(1 for _, o in outcomes if o == "FP")
    fn = sum(1 for _, o in outcomes if o == "FN")
    return {"precision": tp / (tp + fp) if tp + fp else None, "recall": tp / (tp + fn) if tp + fn else None,
            "tp": tp, "fp": fp, "fn": fn, "new_bad": sum(1 for _, o in outcomes if o == "NEW_BAD")}


def map_scores_c10(final_map, world, radius=0.30):
    """C10.3: an entry is correct if a physical tag with the same ID lies within `radius`; otherwise a
    phantom. RMSE over correct entries, ID precision (correct / entries) and recall (tags with a correct
    entry / tags in the world)."""
    errs, hit = [], set()
    for b in final_map or []:
        cands = [(math.hypot(b["x_m"] - t["x_m"], b["y_m"] - t["y_m"]), t["tag"]) for t in world if t["id"] == b.get("id")]
        near = min(cands) if cands else None
        if near and near[0] <= radius:
            errs.append(near[0])
            hit.add(near[1])
    n = len(final_map or [])
    return {"map_rmse_m": math.sqrt(sum(e * e for e in errs) / len(errs)) if errs else None,
            "map_precision": len(errs) / n if n else None, "map_recall": len(hit) / len(world),
            "phantoms": n - len(errs), "n_entries": n}


# ---------------------------------------------------------------- tool calls

def _pose_close(a, b):
    try:
        return (abs(float(a["x_m"]) - float(b["x_m"])) <= POSE_TOL_M and abs(float(a["y_m"]) - float(b["y_m"])) <= POSE_TOL_M
                and abs(wrap_deg(float(a["theta_deg"]) - float(b["theta_deg"]))) <= POSE_TOL_DEG)
    except (KeyError, TypeError, ValueError):
        return False


def call_matches(pred, gold):
    """Matching rule: same tool and equivalent arguments.
    compose_odometry: odometry values equal and pose within tolerance; gate_detection: same det,
    same candidate set, pose within tolerance; fix_pose: same set of (det, beacon) pairs, prior within
    tolerance; map_point: same det, pose within tolerance; update_beacon: same det and beacon,
    pose within tolerance. Tolerance: 0.011 m and 0.11 deg (2-dp rounding of reported poses)."""
    name, args = pred["tool"], pred.get("args") or {}
    gname, gargs = gold
    if name != gname:
        return False

    def det_ok(v):
        return isinstance(v, int) and not isinstance(v, bool)
    if "det" in gargs and not det_ok(args.get("det")):
        return False
    if name == "fix_pose" and not all(isinstance(m, dict) and det_ok(m.get("det")) for m in args.get("matches") or []):
        return False
    try:
        if name == "compose_odometry":
            return (_pose_close(args["pose"], gargs["pose"])
                    and all(abs(float(args[k]) - float(gargs[k])) <= ODO_TOL for k in ("forward_m", "left_m", "dtheta_deg")))
        if name == "gate_detection":
            return (int(args["det"]) == gargs["det"] and sorted(args.get("candidates") or []) == gargs["candidates"]
                    and _pose_close(args["pose"], gargs["pose"]))
        if name == "fix_pose":
            got = sorted((int(m["det"]), m["beacon"]) for m in args["matches"])
            want = sorted((m["det"], m["beacon"]) for m in gargs["matches"])
            return got == want and _pose_close(args["prior"], gargs["prior"])
        if name == "map_point":
            return int(args["det"]) == gargs["det"] and _pose_close(args["pose"], gargs["pose"])
        if name == "update_beacon":
            return (int(args["det"]) == gargs["det"] and args["beacon"] == gargs["beacon"]
                    and _pose_close(args["pose"], gargs["pose"]))
    except (KeyError, TypeError, ValueError):
        return False
    return False


def match_calls(pred_calls, gold_calls):
    """Greedy one-to-one matching in call order. Returns (tp, fp, fn)."""
    used = [False] * len(gold_calls)
    tp = 0
    for p in pred_calls:
        for i, gc in enumerate(gold_calls):
            if not used[i] and call_matches(p, gc):
                used[i] = True
                tp += 1
                break
    return tp, len(pred_calls) - tp, len(gold_calls) - tp


def gold_calls(obs, prev_report):
    """The D7 procedure's calls on this input, or None when the procedure cannot process it."""
    try:
        return ks.estimate_step(obs, prev_report)["calls"]
    except (NotImplementedError, ks.GoldUnavailable):
        return None


def prf(tp, fp, fn):
    """Precision, recall and F1 = 2TP / (2TP + FP + FN); F1 is None only when there is nothing to score."""
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f = 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else None
    return {"precision": p, "recall": r, "f1": f, "tp": tp, "fp": fp, "fn": fn}


# ---------------------------------------------------------------- scores in [0, 1]

def linear_score(error, tolerance):
    """max(0, 1 - error / tolerance): 1 is perfect, 0 at or beyond the tolerance (Module 9 notes, eq. 3.2)."""
    return max(0.0, 1.0 - error / tolerance)
