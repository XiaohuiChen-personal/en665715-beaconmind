#!/usr/bin/env python3
"""Rehearse the real-room sessions in the room simulator with the coded procedure B2 (work list 3.2, rule R1).

Usage (pure Python, no model calls; about 0.1 s an episode):
    python3 course-project/tools/room_rehearsal.py grid --seeds 3000-3029 \\
        --logs course-project/data/room/rehearsal --save-seeds 5 \\
        --json course-project/evidence/M3/M3.T12/rehearsal-b2.json \\
        --tables course-project/evidence/M3/M3.T12/rehearsal-b2-tables.md
    python3 course-project/tools/room_rehearsal.py one --scenario S1 --preset camera --range 2.5 --seed 3000 --trace

`grid` runs every scenario of configs/arenas/real-room-scenarios.json for the noise presets, range limits and
odometry conditions given, then the variant runs (range sweep, B2 as frozen, driving-area inset, extra tags, bearing
bias, E1 patience), and writes the per-cell statistics as JSON and as Markdown tables. Every number in the tables is
computed here from the episodes. Logs are kinsim_lite episode documents (seed_<n>.json, as tools/pilot_record.py
writes them), so tools/replay_run.py, tools/b1_run.py and the metrics read them unchanged:
    <logs>/<world_id>/<preset>-r<range>-<odometry>/<scenario>/seed_<n>.json

Odometry conditions: `study` (kinsim_lite's noise, no bias), `drift2` (the main study's held-out condition: distance
and turn angle over-read by 2 %), `carpet` (kinsim_room.CARPET: the car veers on a forward move, turns fall short).

Metrics per episode (plan C10; truth is the simulator's): steps, how it ended, share of steps by pose source, ATE-RMSE
and final pose error of B2 and of dead reckoning B0, tags seen and tags mapped (a map entry within 0.30 m of a tag
with its ID), phantom entries, duplicated-ID pairs seen and mapped as two beacons, association outcomes
(metrics/pilot.py LabelTracker), and the footprint's smallest clearance to a wall or the desk.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this tool.
"""
import argparse
import collections
import copy
import json
import math
import pathlib
import statistics
import sys

TOOLS = pathlib.Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(ROOT / "beaconmind" / "src"))
from beaconmind.envs import kinsim_lite as ks  # noqa: E402
from beaconmind.envs import kinsim_room as kr  # noqa: E402
from beaconmind.metrics import pilot as pm  # noqa: E402

ODOMETRY = {"study": ("study", 0.0), "drift2": ("study", 0.02), "carpet": ("carpet", 0.0)}
# Extra tags for the "more tags" variant: (wall key of tools/room_layout.py, metres from the wall's corner, ID).
# Each sits about 0.5 m from a tag of the printed layout, so two tags share a picture more often.
EXTRA_TAGS = [("window", 1.13, 5), ("window", 3.14, 7), ("w295", 1.93, 9), ("doors", 3.18, 11), ("desk", 1.95, 13),
              ("w295", 1.03, 17)]
EXTRA_MOVES = {"T11": 3.63, "T00": 1.41}     # inside the mounting sheet's slide ranges


def seed_list(text):
    out = []
    for part in text.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b) + 1)) if b else [int(a)]
    return out


def with_extra_tags(world):
    import room_world as rw
    world = copy.deepcopy(world)
    for t in world["tags"]:
        if t["uid"] in EXTRA_MOVES:
            t["x_m"], t["y_m"] = rw.tag_xy(rw.wall_of(t["wall"]), EXTRA_MOVES[t["uid"]])
    for k, (wall, along, tag_id) in enumerate(EXTRA_TAGS):
        w = rw.wall_of(wall)
        x, y = rw.tag_xy(w, along)
        nx, ny = rw.rl.inward_normal(w)
        world["tags"].append(dict(world["tags"][0], uid="T%02d" % (len(world["tags"])), id=tag_id, wall=wall, x_m=x,
                                  y_m=y, normal_deg=round(math.degrees(math.atan2(ny, nx)), 1)))
    world["world_id"] += "+6tags"
    return world


def episode_metrics(ep):
    recs, world = ep["records"], ep["world"]
    out = {"steps": len(recs), "ended_by": ep["ended_by"].split(":")[0],
           "ended_detail": ep["ended_by"].partition(": ")[2] or None}
    if not recs:
        return out
    truth = [r["truth"] for r in recs]
    b2 = pm.trajectory_errors([r["report"]["pose"] for r in recs], truth)
    b0 = pm.trajectory_errors(ks.dead_reckoning(recs), truth)
    for name, e in (("b2", b2), ("b0", b0)):
        out.update({"ate_%s_m" % name: e["ate_m"], "final_pos_%s_m" % name: e["final_pos_m"],
                    "final_heading_%s_deg" % name: e["final_heading_deg"]})
    src = collections.Counter(r["report"]["pose_source"] for r in recs)
    for k in ("beacon_fix", "relocalised", "position_fix", "prior_kept", "odometry"):
        out["share_" + k] = src[k] / len(recs)
    out["share_any_fix"] = (src["beacon_fix"] + src["relocalised"] + src["position_fix"]) / len(recs)
    out["share_steps_with_detection"] = sum(bool(r["raw"]["detections"]) for r in recs) / len(recs)
    out["share_steps_two_detections"] = sum(len(r["raw"]["detections"]) >= 2 for r in recs) / len(recs)
    seen = {d["_tag"] for r in recs for d in r["raw"]["detections"]}
    final_map = recs[-1]["report"]["map"]
    ms = pm.map_scores_c10(final_map, world)
    out.update(tags_seen=len(seen), tags_mapped=round(ms["map_recall"] * len(world)), map_entries=ms["n_entries"],
               phantoms=ms["phantoms"], confirmed=sum(b["state"] == "confirmed" for b in final_map),
               map_rmse_m=ms["map_rmse_m"])
    ids = [t["id"] for t in world]
    dup_ids = {i for i in ids if ids.count(i) > 1}
    pairs_seen = pairs_two = 0
    for i in dup_ids:
        tags = [t for t in world if t["id"] == i]
        if all(t["tag"] in seen for t in tags):
            pairs_seen += 1
            hit = set()
            for b in final_map:
                if b["id"] == i:
                    near = min(tags, key=lambda t: math.hypot(b["x_m"] - t["x_m"], b["y_m"] - t["y_m"]))
                    if math.hypot(b["x_m"] - near["x_m"], b["y_m"] - near["y_m"]) <= 0.30:
                        hit.add(near["tag"])
            pairs_two += len(hit) == 2
    out.update(dup_pairs_seen=pairs_seen, dup_pairs_mapped_twice=pairs_two)
    tracker, outcomes, prev = pm.LabelTracker(), [], None
    for r in recs:
        outcomes += tracker.score_step(r["report"], prev, r["raw"]["detections"], dup_ids)
        prev = r["report"]
    a = pm.association_scores(outcomes)
    out.update(assoc_tp=a["tp"], assoc_fp=a["fp"], assoc_fn=a["fn"], assoc_new_bad=a["new_bad"],
               assoc_fp_dup=sum(1 for dup, o in outcomes if dup and o == "FP"))
    clear = [min(i["wall_m"], i["obstacle_m"] if i["obstacle_m"] is not None else i["wall_m"]) for i in ep["info"]]
    out.update(min_clearance_m=min(clear), contact_steps=sum(c <= 0 for c in clear),
               outside_drive_steps=sum(i["drive_m"] < 0 for i in ep["info"]),
               path_m=sum(abs(r["raw"]["odometry"]["forward_m"]) for r in recs if r["raw"]["odometry"]))
    return out


def run_cell(world, scenarios, seeds, preset, max_range, odometry, policy="block", patience=2, inset=0.0,
             noise_overrides=None, log_dir=None, save_seeds=0):
    """All scenarios x seeds for one configuration. Returns the per-episode metric rows."""
    odo, bias = ODOMETRY[odometry]
    pol = kr.b2_step if policy == "frozen" else kr.make_b2_policy(dead_end="block", patience=patience)
    rows = []
    for sc in scenarios:
        for k, seed in enumerate(seeds):
            env = kr.KinSimEnv.room(world, sc["start_pose"], preset_name=preset, max_range_m=max_range, odometry=odo,
                                    odo_bias=bias, drive_inset_m=inset, noise_overrides=noise_overrides)
            ep = kr.run_episode(env, seed, policy=pol)
            row = dict(episode_metrics(ep), scenario=sc["id"], seed=seed)
            rows.append(row)
            if log_dir is not None and k < save_seeds and ep["records"]:
                d = pathlib.Path(log_dir) / world["world_id"] / ("%s-r%.1f-%s" % (preset, max_range, odometry)) / sc["id"]
                d.mkdir(parents=True, exist_ok=True)
                ep["rehearsal"] = {"scenario": sc["id"], "preset": preset, "max_range_m": max_range,
                                   "odometry": odometry, "policy": policy, "patience": patience, "drive_inset_m": inset}
                (d / ("seed_%d.json" % seed)).write_text(json.dumps(ep), encoding="utf-8")
    return rows


def med(rows, key):
    vals = [r[key] for r in rows if r.get(key) is not None]
    return statistics.median(vals) if vals else None


def mean(rows, key):
    vals = [r[key] for r in rows if r.get(key) is not None]
    return statistics.fmean(vals) if vals else None


def quartiles(rows, key):
    vals = sorted(r[key] for r in rows if r.get(key) is not None)
    if len(vals) < 4:
        return None
    q = statistics.quantiles(vals, n=4, method="inclusive")
    return [q[0], q[2]]


def summarise(rows):
    n = len(rows)
    ends = collections.Counter(r["ended_by"] for r in rows)
    detail = collections.Counter(r["ended_detail"] for r in rows if r["ended_detail"])
    scored = [r for r in rows if r["steps"]]
    diff = [r["ate_b2_m"] - r["ate_b0_m"] for r in scored]
    return {
        "episodes": n, "scored": len(scored), "done": ends["DONE"], "budget": ends["budget"], "not_implemented": ends["not_implemented"],
        "not_implemented_branches": dict(detail),
        "steps_median": med(rows, "steps"), "steps_iqr": quartiles(rows, "steps"),
        "share_beacon_fix": mean(scored, "share_beacon_fix"), "share_position_fix": mean(scored, "share_position_fix"),
        "share_any_fix": mean(scored, "share_any_fix"), "share_prior_kept": mean(scored, "share_prior_kept"),
        "share_steps_with_detection": mean(scored, "share_steps_with_detection"),
        "share_steps_two_detections": mean(scored, "share_steps_two_detections"),
        "ate_b2_median_m": med(scored, "ate_b2_m"), "ate_b0_median_m": med(scored, "ate_b0_m"),
        "ate_diff_median_m": statistics.median(diff) if diff else None,
        "ate_b2_lower": sum(d < 0 for d in diff), "ate_b2_higher": sum(d > 0 for d in diff),
        "final_pos_b2_median_m": med(scored, "final_pos_b2_m"), "final_pos_b0_median_m": med(scored, "final_pos_b0_m"),
        "final_heading_b2_median_deg": med(scored, "final_heading_b2_deg"),
        "final_heading_b0_median_deg": med(scored, "final_heading_b0_deg"),
        "tags_seen_mean": mean(scored, "tags_seen"), "tags_mapped_mean": mean(scored, "tags_mapped"),
        "tags_mapped_min": min((r["tags_mapped"] for r in scored), default=None),
        "tags_mapped_max": max((r["tags_mapped"] for r in scored), default=None),
        "confirmed_mean": mean(scored, "confirmed"), "phantoms_mean": mean(scored, "phantoms"),
        "dup_pairs_seen_episodes": sum(r["dup_pairs_seen"] > 0 for r in scored),
        "dup_pairs_seen": sum(r["dup_pairs_seen"] for r in scored),
        "dup_pairs_mapped_twice": sum(r["dup_pairs_mapped_twice"] for r in scored),
        "assoc_tp": sum(r["assoc_tp"] for r in scored), "assoc_fp": sum(r["assoc_fp"] for r in scored),
        "assoc_fn": sum(r["assoc_fn"] for r in scored), "assoc_fp_dup": sum(r["assoc_fp_dup"] for r in scored),
        "assoc_new_bad": sum(r["assoc_new_bad"] for r in scored),
        "min_clearance_m": min((r["min_clearance_m"] for r in scored), default=None),
        "contact_episodes": sum(r["contact_steps"] > 0 for r in scored),
        "clearance_below_5cm_episodes": sum(r["min_clearance_m"] < 0.05 for r in scored),
        "outside_drive_episodes": sum(r["outside_drive_steps"] > 0 for r in scored),
        "path_median_m": med(scored, "path_m"),
    }


def f(v, fmt="%.1f", none="-"):
    return none if v is None else fmt % v


HEAD = ("| %s | ended: DONE / budget / B2 stopped | steps (median, IQR) | fix share: full / position / prior kept | "
        "ATE cm, median: B2 / B0 | B2 lower ATE in | final error cm: B2 / B0 | final heading deg: B2 / B0 | "
        "tags seen / mapped (of %d) | duplicated pairs: seen / mapped as two | wrong matches | closest to a wall cm "
        "(episodes touching) |")


def table(title, label, cells, n_tags=12):
    lines = ["**%s**" % title, "", HEAD % (label, n_tags), "|" + " --- |" * 12]
    for name, s in cells:
        iqr = s["steps_iqr"]
        lines.append("| %s | %d / %d / %d | %s (%s) | %s / %s / %s %% | %s / %s | %d of %d | %s / %s | %s / %s | "
                     "%s / %s | %d / %d | %d | %s (%d) |" % (
                         name, s["done"], s["budget"], s["not_implemented"], f(s["steps_median"], "%.0f"),
                         "%.0f-%.0f" % tuple(iqr) if iqr else "-",
                         f(100 * s["share_beacon_fix"]), f(100 * s["share_position_fix"]), f(100 * s["share_prior_kept"]),
                         f(100 * s["ate_b2_median_m"]), f(100 * s["ate_b0_median_m"]), s["ate_b2_lower"],
                         s["scored"],
                         f(100 * s["final_pos_b2_median_m"]), f(100 * s["final_pos_b0_median_m"]),
                         f(s["final_heading_b2_median_deg"]), f(s["final_heading_b0_median_deg"]),
                         f(s["tags_seen_mean"]), f(s["tags_mapped_mean"]), s["dup_pairs_seen"],
                         s["dup_pairs_mapped_twice"], s["assoc_fp"], f(100 * s["min_clearance_m"], "%.0f"),
                         s["contact_episodes"]))
    return "\n".join(lines) + "\n"


def cmd_grid(args):
    world = kr.load_world(args.world)
    scenarios = json.loads(pathlib.Path(args.scenarios).read_text(encoding="utf-8"))["scenarios"]
    seeds = seed_list(args.seeds)
    presets, ranges, odos = args.presets.split(","), [float(v) for v in args.ranges.split(",")], args.odometry.split(",")
    result = {"world": world["world_id"], "scenarios": scenarios, "seeds": args.seeds, "main": [], "per_scenario": [],
              "variants": [], "argv": sys.argv[1:]}
    out = ["<!-- Generated by tools/room_rehearsal.py grid; do not edit by hand. -->", "",
           "World `%s`, %d scenarios x %d noise seeds (%s) = %d episodes per row; driver: B2 with the dead-end branch "
           "defined (kinsim_room.make_b2_policy), E1 as written. ATE and final errors against the simulator's truth; "
           "B0 = dead reckoning on the same odometry. \"B2 stopped\" = an unimplemented branch of the coded procedure."
           % (world["world_id"], len(scenarios), len(seeds), args.seeds, len(scenarios) * len(seeds)), ""]
    main = {}
    for odo in odos:
        cells = []
        for preset in presets:
            for r in ranges:
                rows = run_cell(world, scenarios, seeds, preset, r, odo, log_dir=args.logs, save_seeds=args.save_seeds)
                main[(preset, r, odo)] = rows
                s = summarise(rows)
                result["main"].append({"preset": preset, "max_range_m": r, "odometry": odo, "summary": s})
                cells.append(("%s, %.1f m" % (preset, r), s))
                print("main %s %.1f %s: %d episodes" % (preset, r, odo, len(rows)), flush=True)
        out.append(table("Table 1 (%s odometry). Noise preset and range limit, all scenarios pooled" % odo,
                         "preset, range limit", cells))
    for preset, r, odo in [(p, r, o) for p, r, o in main if p == args.detail_preset and o in args.detail_odometry.split(",")]:
        cells = []
        for sc in scenarios:
            s = summarise([row for row in main[(preset, r, odo)] if row["scenario"] == sc["id"]])
            result["per_scenario"].append({"preset": preset, "max_range_m": r, "odometry": odo, "scenario": sc["id"],
                                           "summary": s})
            p = sc["start_pose"]
            cells.append(("%s (%.2f, %.2f, %.0f deg)" % (sc["id"], p["x_m"], p["y_m"], p["theta_deg"]), s))
        out.append(table("Table 2. Per start pose: %s preset, %.1f m, %s odometry (%d seeds each)" % (
            preset, r, odo, len(seeds)), "scenario (start pose, room frame)", cells))

    def variant(group, name, n_tags=12, w=world, **kw):
        rows = run_cell(w, scenarios, seeds, **kw)
        s = summarise(rows)
        result["variants"].append({"group": group, "name": name, "config": {k: v for k, v in kw.items()}, "summary": s})
        print("variant %s / %s" % (group, name), flush=True)
        return name, s

    base = dict(preset="camera", odometry="study")
    out.append(table("Table 3. Range limit sweep (camera preset, study odometry). Beyond 2.5 m the noise model is an "
                     "extrapolation", "range limit",
                     [variant("range", "%.1f m" % r, max_range=r, **base) for r in (1.5, 2.0, 2.5, 3.0, 3.5, 4.0)]))
    cells = []
    for r in (2.0, 2.5):
        for odo in ("study", "carpet"):
            b = dict(preset="camera", max_range=r, odometry=odo)
            cells.append(variant("driver", "%.1f m, %s: B2 as frozen" % (r, odo), policy="frozen", **b))
            cells.append(variant("driver", "%.1f m, %s: dead end defined" % (r, odo), **b))
            cells.append(variant("driver", "%.1f m, %s: dead end defined, E1 after 4 scans" % (r, odo), patience=4, **b))
    out.append(table("Table 4. The driver: B2 as frozen, with the dead-end branch defined, and with a more patient E1 "
                     "(camera preset)", "range limit, odometry: driver", cells))
    cells = []
    for r in (2.0, 2.5):
        for inset in (0.0, 0.2, 0.4):
            cells.append(variant("inset", "%.1f m, inset %.1f m" % (r, inset), preset="camera", max_range=r,
                                 odometry="carpet", inset=inset))
    out.append(table("Table 5. Driving area moved in from every edge (camera preset, carpet odometry)",
                     "range limit, inset", cells))
    more = with_extra_tags(world)
    cells = []
    for r in (2.0, 2.5):
        for odo in ("study", "drift2"):
            b = dict(preset="camera", max_range=r, odometry=odo)
            cells.append(variant("tags", "%.1f m, %s: 12 tags" % (r, odo), **b))
            cells.append(variant("tags", "%.1f m, %s: 18 tags" % (r, odo), w=more, **b))
    out.append(table("Table 6. Six more tags, each about 0.5 m from a tag of the printed layout (camera preset; "
                     "\"of 12\" reads \"of 18\" on the 18-tag rows)", "range limit, odometry: layout", cells))
    cells = []
    for r in (2.0, 2.5):
        for bias in (0.0, 2.0):
            cells.append(variant("bearing_bias", "%.1f m, bearing bias %+.0f deg" % (r, bias), preset="camera",
                                 max_range=r, odometry="study", noise_overrides={"bearing_bias_deg": bias}))
    out.append(table("Table 7. A constant bearing offset (the camera's yaw is known to +-2 deg; camera preset, study "
                     "odometry)", "range limit, bias", cells))
    if args.json:
        pathlib.Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(args.json).write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    text = "\n".join(out)
    if args.tables:
        pathlib.Path(args.tables).write_text(text, encoding="utf-8")
    else:
        print(text)


def cmd_one(args):
    world = kr.load_world(args.world)
    scenarios = json.loads(pathlib.Path(args.scenarios).read_text(encoding="utf-8"))["scenarios"]
    sc = next(s for s in scenarios if s["id"] == args.scenario)
    odo, bias = ODOMETRY[args.odometry]
    env = kr.KinSimEnv.room(world, sc["start_pose"], preset_name=args.preset, max_range_m=args.range, odometry=odo,
                            odo_bias=bias, drive_inset_m=args.inset)
    pol = kr.b2_step if args.policy == "frozen" else kr.make_b2_policy(patience=args.patience)
    ep = kr.run_episode(env, args.seed, policy=pol)
    if args.trace:
        for r in ep["records"]:
            w = kr.to_world(env.scene["start_pose_world"], r["truth"])
            rep = r["report"]
            print("%3d room (%.2f, %.2f, %4.0f) sees %-24s %-12s %-13s map %d" % (
                r["step"], w["x_m"], w["y_m"], w["theta_deg"],
                ",".join("%s@%.1f" % (world["tags"][d["_tag"]]["uid"], d["range_m"]) for d in r["raw"]["detections"]),
                rep["pose_source"], rep["decision"], len(rep["map"])))
    print(json.dumps(episode_metrics(ep), indent=1))
    if args.out:
        pathlib.Path(args.out).write_text(json.dumps(ep), encoding="utf-8")


def cmd_conditioning(args):
    """How often can fix_pose's full fix be `well_conditioned` (configs/dv.json: sigma_xy <= 0.15 m and sigma_theta
    <= 8 deg under the DV noise model) for tags that share one picture? Random sets of 2-4 tags at bearings inside
    the half field of view (less the tag's own half width) and ranges in [near, far]."""
    import random
    from beaconmind import geometry as g
    rng = random.Random(args.seed)
    pose = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
    print("fix_pose full fix: share of random tag sets that are well conditioned (%d sets per cell, seed %d)" % (
        args.samples, args.seed))
    print("| field of view | tags in the picture | ranges 0.65-1.5 m | ranges 0.65-2.5 m | best sigma_xy m | best sigma_theta deg |")
    print("| --- | --- | --- | --- | --- | --- |")
    for label, half in (("46.9 deg (measured camera)", 46.86 / 2), ("60 deg (study placeholder)", 30.0)):
        for k in (2, 3, 4):
            cells, best_xy, best_th = [], float("inf"), float("inf")
            for far in (1.5, 2.5):
                ok = 0
                for _ in range(args.samples):
                    matches = []
                    for _ in range(k):
                        r = rng.uniform(0.65, far)
                        b = rng.uniform(-1.0, 1.0) * (half - math.degrees(math.atan(0.10 / r)))
                        matches.append({"det": {"range_m": r, "bearing_deg": b}, "point": g.map_point(pose, r, b)})
                    full = g.fix_pose(pose, matches)["full"]
                    ok += full["well_conditioned"]
                    best_xy, best_th = min(best_xy, full["sigma_xy_m"]), min(best_th, full["sigma_theta_deg"])
                cells.append("%.2f %%" % (100.0 * ok / args.samples))
            print("| %s | %d | %s | %s | %.3f | %.1f |" % (label, k, cells[0], cells[1], best_xy, best_th))


def cmd_layout_search(args):
    """Greedy choice of extra tag positions: each step adds the candidate that most raises the share of poses from
    which a full fix is possible in one picture (fix_pose's `well_conditioned` on the tags in view, true geometry).
    Poses: a 0.25 m grid at least --inset inside the driving area, 12 headings. Candidates: every 5 cm along the
    walls' usable stretches (tools/room_layout.py WALLS), at least --spacing from every tag already placed."""
    import room_world as rw
    from beaconmind import geometry as g
    from beaconmind.dv import load_dv
    world = kr.load_world(args.world)
    noise = kr.preset("camera", max_range_m=args.range)
    dv = dict(load_dv(), **(kr.MEASURED_SIGMA_DV if args.measured_sigma else {}))
    print("fix_pose noise model: %s" % ("kinsim_room.MEASURED_SIGMA_DV %s" % kr.MEASURED_SIGMA_DV if args.measured_sigma
                                        else "configs/dv.json as frozen"))
    drive = [tuple(p) for p in world["arena"]["drive_polygon_m"]]
    xs, ys = [p[0] for p in drive], [p[1] for p in drive]
    poses = []
    for i in range(int((max(xs) - min(xs)) / 0.25) + 1):
        for j in range(int((max(ys) - min(ys)) / 0.25) + 1):
            x, y = min(xs) + 0.25 * i, min(ys) + 0.25 * j
            if kr.inside_depth(drive, (x, y)) >= args.inset:
                poses += [{"x_m": x, "y_m": y, "theta_deg": 30.0 * k} for k in range(12)]
    scene = {"obstacles": [{"polygon": [tuple(q) for q in o["polygon_m"]], "occludes": o.get("occludes", True)}
                           for o in world["arena"].get("obstacles", [])]}
    proto = world["tags"][0]

    def as_tag(wall_key, along):
        w = rw.wall_of(wall_key)
        x, y = rw.tag_xy(w, along)
        nx, ny = rw.rl.inward_normal(w)
        nd = math.degrees(math.atan2(ny, nx))
        return {"x_m": x, "y_m": y, "normal_deg": nd, "n": (nx, ny), "z_m": proto["z_m"],
                "half_m": proto["black_size_m"] / 2, "wall": wall_key, "along": along}

    def seen_from(tag):
        return {k for k, pose in enumerate(poses) if kr.visible(scene, pose, tag, noise) is not None}

    placed = []
    for t in world["tags"]:
        nd = math.radians(t["normal_deg"])
        placed.append(dict(t, n=(math.cos(nd), math.sin(nd)), half_m=t["black_size_m"] / 2))
    half_sheet = args.spacing / 2
    cands = []
    for w in rw.rl.WALLS:
        for a, b in w["spans"]:
            s = a + half_sheet + 0.02
            while s <= b - half_sheet - 0.02 + 1e-9:
                cands.append(as_tag(w["key"], round(s, 2)))
                s += 0.05
    vis = [seen_from(t) for t in placed]
    cvis = [seen_from(c) for c in cands]

    def fixable(k, tags_here):
        if len(tags_here) < 2:
            return False
        ms = [{"det": {kk: v for kk, v in g.predict_observation(poses[k], t).items() if kk != "near_blocked"},
               "point": {"x_m": t["x_m"], "y_m": t["y_m"]}} for t in tags_here]
        return g.fix_pose(poses[k], ms, dv=dv)["full"]["well_conditioned"]

    def score(tags, viss):
        at = collections.defaultdict(list)
        for t, v in zip(tags, viss):
            for k in v:
                at[k].append(t)
        return ({k for k, ts in at.items() if len(ts) >= 2}, {k for k, ts in at.items() if fixable(k, ts)}, at)

    two, fix, at = score(placed, vis)
    print("%d poses (%d positions x 12 headings), range limit %.1f m, %d candidates" % (
        len(poses), len(poses) // 12, args.range, len(cands)))
    print("printed layout: a tag in view %.1f %%, two or more %.1f %%, a full fix possible %.1f %% of poses" % (
        100 * len(at) / len(poses), 100 * len(two) / len(poses), 100 * len(fix) / len(poses)))
    for step in range(args.add):
        best = None
        for c, cv in zip(cands, cvis):
            if any(math.hypot(c["x_m"] - t["x_m"], c["y_m"] - t["y_m"]) < args.spacing for t in placed):
                continue
            gain = sum(1 for k in cv if k not in fix and fixable(k, at.get(k, []) + [c]))
            gain2 = sum(1 for k in cv if k not in two and len(at.get(k, [])) >= 1)
            if best is None or (gain, gain2) > best[0]:
                best = ((gain, gain2), c, cv)
        (gain, gain2), c, cv = best
        placed.append(c)
        vis.append(cv)
        two, fix, at = score(placed, vis)
        print("add %d: %s wall at %.2f m -> a tag in view %.1f %%, two or more %.1f %%, full fix possible %.1f %%" % (
            step + 1, c["wall"], c["along"], 100 * len(at) / len(poses), 100 * len(two) / len(poses),
            100 * len(fix) / len(poses)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("grid", "one"):
        p = sub.add_parser(name)
        p.add_argument("--world", default=str(ROOT / "configs" / "arenas" / "real-room-nominal.json"))
        p.add_argument("--scenarios", default=str(ROOT / "configs" / "arenas" / "real-room-scenarios.json"))
    g = sub.choices["grid"]
    g.add_argument("--seeds", default="3000-3029")
    g.add_argument("--presets", default="study,camera")
    g.add_argument("--ranges", default="2.0,2.5")
    g.add_argument("--odometry", default="study,drift2,carpet")
    g.add_argument("--detail-preset", default="camera")
    g.add_argument("--detail-odometry", default="study")
    g.add_argument("--logs")
    g.add_argument("--save-seeds", type=int, default=5, help="save the logs of the first N seeds of every main cell")
    g.add_argument("--json")
    g.add_argument("--tables")
    g.set_defaults(func=cmd_grid)
    o = sub.choices["one"]
    o.add_argument("--scenario", default="S1")
    o.add_argument("--preset", default="camera")
    o.add_argument("--range", type=float, default=2.0)
    o.add_argument("--odometry", default="study", choices=sorted(ODOMETRY))
    o.add_argument("--seed", type=int, default=3000)
    o.add_argument("--policy", default="block", choices=("block", "frozen"))
    o.add_argument("--patience", type=int, default=2)
    o.add_argument("--inset", type=float, default=0.0)
    o.add_argument("--trace", action="store_true")
    o.add_argument("--out")
    o.set_defaults(func=cmd_one)
    ls = sub.add_parser("layout-search")
    ls.add_argument("--world", default=str(ROOT / "configs" / "arenas" / "real-room-nominal.json"))
    ls.add_argument("--range", type=float, default=2.5)
    ls.add_argument("--add", type=int, default=8)
    ls.add_argument("--spacing", type=float, default=0.25, help="smallest distance between two tag centres, m")
    ls.add_argument("--inset", type=float, default=0.35)
    ls.add_argument("--measured-sigma", action="store_true",
                    help="judge a full fix with kinsim_room.MEASURED_SIGMA_DV instead of configs/dv.json's noise model")
    ls.set_defaults(func=cmd_layout_search)
    c = sub.add_parser("conditioning")
    c.add_argument("--samples", type=int, default=20000)
    c.add_argument("--seed", type=int, default=1)
    c.set_defaults(func=cmd_conditioning)
    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
