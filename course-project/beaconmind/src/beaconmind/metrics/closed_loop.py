"""Episode summary and scores of one closed-loop run log (harness/closed_loop.py rows; plan C10).

The scores are those of the replay study, computed by the same functions (metrics/pilot.py) on the same row fields:
ATE and final-pose error of the pose the arm carried forward, against the simulator's true pose at every
observation; map error, precision and recall (C10.3); association precision and recall (C10.4); tool-call
precision, recall and F1 of the estimation tools against the coded procedure's calls on the very input the arm
received. B0 (dead reckoning) is computed on the same odometry, so it is the baseline of this very trajectory.

Closed-loop only: moves by type, refused `move` calls by reason, the episode's end, and how often the decision and
the memory written in the report equal what the coded procedure (kinsim_lite.decide_step) decides from the arm's own
input. In a closed loop every arm drives its own trajectory, so two arms' numbers are not paired step by step.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this summary (work list 4.1).
"""
import math
import statistics

from beaconmind.envs import kinsim_lite as ks
from beaconmind.metrics import pilot as pm

ESTIMATION_TOOLS = ("compose_odometry", "gate_detection", "fix_pose", "map_point", "update_beacon")


def _rank(values, q):
    s = sorted(values)
    return s[max(0, math.ceil(q / 100 * len(s)) - 1)] if s else None


def procedure_decision(obs, prev):
    """(decision, memory) the coded procedure reaches from this input, or None when it cannot process it."""
    try:
        est = ks.estimate_step(obs, prev)
        mem = ks.initial_memory() if prev is None else prev["memory"]
        return ks.decide_step(est, mem, obs["safety"], obs["counters"]["steps_left"])
    except Exception:  # noqa: BLE001  (an unimplemented branch, or a previous report the procedure cannot read)
        return None


def summarize(rows, world):
    """Summary dict of one episode. `rows` are the step rows in order; `world` is the simulator's tag list
    ([{tag, id, x_m, y_m, ...}]), used for scoring only."""
    rows = sorted(rows, key=lambda r: r["step"])
    n = len(rows)
    if not n or [r["step"] for r in rows] != list(range(n)):
        raise ValueError("empty or non-contiguous run log")
    end = rows[-1].get("episode_end") or {"ended_by": None, "detail": "incomplete"}
    truth = [r["truth"] for r in rows]
    ids = [t["id"] for t in world]
    dup = {i for i in ids if ids.count(i) == 2}
    out = {"arm": rows[0]["arm"], "seed": rows[0]["seed"], "steps": n, "ended_by": end["ended_by"], "detail": end["detail"],
           "n_tags": len(world), "n_dup_ids": len(dup)}

    # ---- moves, refusals, validity
    moves, refused, results = {}, {}, {}
    for r in rows:
        ex = r.get("executed_move")
        if ex:
            results[ex["result"]] = results.get(ex["result"], 0) + 1
            if ex["result"] != "refused":
                moves[ex["action"]] = moves.get(ex["action"], 0) + 1
        for v in r.get("move_calls") or []:
            if v["tool_result"] in ("refused", "error"):
                key = str(v["tool_reason"])
                refused[key] = refused.get(key, 0) + 1
    codes = {}
    for r in rows:
        for v in r.get("violations") or []:
            codes[v["code"]] = codes.get(v["code"], 0) + 1
    out.update(moves_executed=sum(moves.values()), moves_by_type=dict(sorted(moves.items())), move_results=results,
               move_calls=sum(len(r.get("move_calls") or []) for r in rows),
               refused_move_calls=sum(refused.values()), refused_by_reason=refused, violations_by_code=codes,
               steps_without_move=sum(1 for r in rows if not r.get("executed_move")),
               fallbacks=sum(1 for r in rows if r["fallback"]), repaired_reports=sum(1 for r in rows if r["checks"].get("repaired_chars")),
               valid_rate=sum(1 for r in rows if r["checks"]["valid"]) / n,
               step_errors=sum(1 for r in rows if r.get("error")),
               emergency_stops=sum(1 for r in rows for c in r["calls"] if c.get("tool") == "emergency_stop"),
               path_length_m=sum(abs((r["raw"]["odometry"] or {}).get("forward_m", 0.0)) for r in rows))

    # ---- trajectory: the arm and B0 on the same odometry
    for name, poses in (("pose", [r["estimate_pose"] for r in rows]), ("b0", ks.dead_reckoning(rows))):
        e = pm.trajectory_errors(poses, truth)
        out[name] = {k: e[k] for k in ("ate_m", "heading_rmse_deg", "final_pos_m", "final_heading_deg", "max_pos_m")}

    # ---- map and association
    reports, prevs = [r["next_prev"] for r in rows], [r["prev_report"] for r in rows]
    final_map = (reports[-1] or {}).get("map") or []
    ms = pm.map_scores_c10(final_map, world)
    tr, res = pm.LabelTracker(), []
    for rep, prev, r in zip(reports, prevs, rows):
        res += tr.score_step(rep, prev, r["raw"]["detections"], dup)
    a_all, a_dup = pm.association_scores(res), pm.association_scores([x for x in res if x[0]])
    seen = {d["_tag"] for r in rows for d in r["raw"]["detections"]}
    out["map"] = dict(ms, confirmed=sum(1 for b in final_map if isinstance(b, dict) and b.get("state") == "confirmed"),
                      tags_found=round(ms["map_recall"] * len(world)), tags_ever_detected=len(seen),
                      assoc_precision=a_all["precision"], assoc_recall=a_all["recall"],
                      assoc_precision_dup=a_dup["precision"], assoc_recall_dup=a_dup["recall"], assoc_counts=a_all)

    # ---- tool calls against the procedure's calls on the same input; decisions against the procedure's decision
    tp = fp = fn = skipped = 0
    by_tool, dec_same, mem_same, dec_n, viol_pose, viol_checked, map_bad = {}, 0, 0, 0, 0, 0, 0
    for r in rows:
        for c in r["calls"]:
            by_tool[c.get("tool")] = by_tool.get(c.get("tool"), 0) + 1
        gold = pm.gold_calls(r["observation"], r["prev_report"])
        if gold is None:
            skipped += 1
        else:
            a, b, c2 = pm.match_calls([c for c in r["calls"] if c.get("tool") in ESTIMATION_TOOLS], gold)
            tp, fp, fn = tp + a, fp + b, fn + c2
        if r["checks"]["valid"]:
            want = procedure_decision(r["observation"], r["prev_report"])
            if want is not None:
                dec_n += 1
                dec_same += r["report"].get("decision") == want[0]
                mem_same += r["report"].get("memory") == want[1]
            sv = pm.state_violations(r)
            if sv["pose"] is not None:
                viol_checked += 1
                viol_pose += not sv["pose"]
            map_bad += sv["map_bad"]
    out["tools"] = dict(pm.prf(tp, fp, fn), calls=sum(by_tool.values()), calls_per_step=sum(by_tool.values()) / n,
                        by_tool=dict(sorted(by_tool.items(), key=lambda kv: -kv[1])), gold_skipped=skipped,
                        scored_tools=list(ESTIMATION_TOOLS))
    out["procedure_agreement"] = {"steps_compared": dec_n, "decision": dec_same / dec_n if dec_n else None,
                                  "memory": mem_same / dec_n if dec_n else None}
    out["state_violations"] = {"pose_checked": viol_checked, "pose_bad": viol_pose, "map_entries_bad": map_bad}

    # ---- time, tokens, cost
    secs = [float(r.get("seconds") or 0.0) for r in rows]
    tok = {"in": 0, "cached_in": 0, "out": 0}
    for r in rows:
        for t in r.get("turns") or []:
            for k in tok:
                tok[k] += int((t.get("tokens") or {}).get(k) or 0)
    cost = sum(float(r.get("cost_usd") or 0.0) for r in rows)
    out["time"] = {"total_s": sum(secs), "mean_s": statistics.fmean(secs), "p50_s": _rank(secs, 50), "p95_s": _rank(secs, 95),
                   "max_s": max(secs), "turns_per_step": sum(len(r.get("turns") or []) for r in rows) / n}
    out["tokens"] = tok
    out["cost_usd"] = cost
    out["cost_per_step_usd"] = cost / n
    return out


def table(summaries):
    """A Markdown comparison table of several episode summaries (one column each, plus B0 of each trajectory)."""
    def f(v, spec="%.3f"):
        return "n/a" if v is None else spec % v

    def cm(v):
        return "n/a" if v is None else "%.1f" % (100 * v)
    rows = [
        ("Episode end", lambda s: "%s (%s)" % (s["ended_by"], str(s["detail"])[:40])),
        ("Steps", lambda s: str(s["steps"])),
        ("Moves executed", lambda s: str(s["moves_executed"])),
        ("Moves by type", lambda s: ", ".join("%s %d" % (k.replace("FORWARD", "F").replace("TURN_LEFT", "L").replace("TURN_RIGHT", "R")
                                                          .replace("BACKWARD", "B"), v) for k, v in s["moves_by_type"].items()) or "none"),
        ("Path length (odometry, m)", lambda s: f(s["path_length_m"], "%.2f")),
        ("Refused move calls (reasons)", lambda s: "%d%s" % (s["refused_move_calls"], " (%s)" % "; ".join(
            "%s: %d" % kv for kv in s["refused_by_reason"].items()) if s["refused_by_reason"] else "")),
        ("Steps without an executed move", lambda s: str(s["steps_without_move"])),
        ("Fallbacks / repaired reports", lambda s: "%d / %d" % (s["fallbacks"], s["repaired_reports"])),
        ("ATE (cm)", lambda s: cm(s["pose"]["ate_m"])),
        ("B0 ATE on the same odometry (cm)", lambda s: cm(s["b0"]["ate_m"])),
        ("Final position error (cm)", lambda s: cm(s["pose"]["final_pos_m"])),
        ("B0 final position error (cm)", lambda s: cm(s["b0"]["final_pos_m"])),
        ("Final heading error (deg)", lambda s: f(s["pose"]["final_heading_deg"], "%.1f")),
        ("Heading RMSE (deg)", lambda s: f(s["pose"]["heading_rmse_deg"], "%.1f")),
        ("Tags found within 0.30 m / in the world", lambda s: "%d / %d" % (s["map"]["tags_found"], s["n_tags"])),
        ("Tags ever detected", lambda s: str(s["map"]["tags_ever_detected"])),
        ("Map entries (confirmed, phantoms)", lambda s: "%d (%d, %d)" % (s["map"]["n_entries"], s["map"]["confirmed"], s["map"]["phantoms"])),
        ("Map RMSE (cm)", lambda s: cm(s["map"]["map_rmse_m"])),
        ("Map precision / recall", lambda s: "%s / %s" % (f(s["map"]["map_precision"], "%.2f"), f(s["map"]["map_recall"], "%.2f"))),
        ("Association precision / recall", lambda s: "%s / %s" % (f(s["map"]["assoc_precision"], "%.2f"), f(s["map"]["assoc_recall"], "%.2f"))),
        ("Tool calls (per step)", lambda s: "%d (%.1f)" % (s["tools"]["calls"], s["tools"]["calls_per_step"])),
        ("Estimation-tool F1 vs the procedure (P / R)", lambda s: "%s (%s / %s)" % (f(s["tools"]["f1"]), f(s["tools"]["precision"]), f(s["tools"]["recall"]))),
        ("Decision = procedure's / memory = procedure's", lambda s: "%s / %s" % (f(s["procedure_agreement"]["decision"]), f(s["procedure_agreement"]["memory"]))),
        ("State violations: pose / map entries", lambda s: "%d of %d / %d" % (s["state_violations"]["pose_bad"], s["state_violations"]["pose_checked"], s["state_violations"]["map_entries_bad"])),
        ("Time per step: mean / median / max (s)", lambda s: "%.1f / %.1f / %.1f" % (s["time"]["mean_s"], s["time"]["p50_s"], s["time"]["max_s"])),
        ("Episode time (min)", lambda s: "%.1f" % (s["time"]["total_s"] / 60)),
        ("Tokens: input (cached) / output", lambda s: "%d (%d) / %d" % (s["tokens"]["in"], s["tokens"]["cached_in"], s["tokens"]["out"])),
        ("Cost (US$): episode / per step", lambda s: "%.2f / %.3f" % (s["cost_usd"], s["cost_per_step_usd"])),
    ]
    head = "| Measure | " + " | ".join(s.get("label") or s["arm"] for s in summaries) + " |"
    lines = [head, "| --- |" + " --- |" * len(summaries)]
    for name, fn in rows:
        lines.append("| %s | %s |" % (name, " | ".join(fn(s) for s in summaries)))
    return "\n".join(lines)
