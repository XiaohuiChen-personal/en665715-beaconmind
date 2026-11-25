#!/usr/bin/env python3
"""Rehearse the real-room sessions in the room simulator with the coded procedure B2 (work list 3.2, rule R1).

Pure Python, no model calls; about 0.5 s an episode, run --jobs at a time.

    # the option grid (tag size and height, tag count, range limit, odometry; DV noise model frozen and measured)
    python3 course-project/tools/room_rehearsal.py grid --groups options,options-dv,study-preset --seeds 3000-3029 \\
        --json course-project/evidence/M3/M3.T12/rehearsal-b2.json --logs course-project/data/room/rehearsal --save-seeds 5
    # the detail runs for one configuration (per start pose, driver, driving-area inset, bearing bias, range sweep)
    python3 course-project/tools/room_rehearsal.py grid --groups scenarios,driver,inset,bias,range --focus B:2.5 \\
        --seeds 3000-3029 --json course-project/evidence/M3/M3.T12/rehearsal-b2.json
    python3 course-project/tools/room_rehearsal.py tables --json course-project/evidence/M3/M3.T12/rehearsal-b2.json \\
        --out course-project/evidence/M3/M3.T12/rehearsal-b2-tables.md
    python3 course-project/tools/room_rehearsal.py one --option A --scenario S1 --range 2.5 --seed 3000 --trace
    python3 course-project/tools/room_rehearsal.py layout-search --range 2.5 --add 8 [--measured-sigma]
    python3 course-project/tools/room_rehearsal.py conditioning

`grid` adds its cells to the JSON file (a cell run again replaces the old one); `tables` writes every table from that
file, so every number in the tables is computed here from the episodes. Logs are kinsim_lite episode documents
(seed_<n>.json, as tools/pilot_record.py writes them), so tools/replay_run.py, tools/b1_run.py and the metrics read
them unchanged:  <logs>/<world_id>/<preset>-r<range>-<odometry>[-dv-measured]/<scenario>/seed_<n>.json

Options (OPTIONS below): A the printed layout (12 tags, 160 mm, centre 0.23 m); B the same places with 100 mm tags
centred 0.1825 m up (a 125 mm sheet standing on the baseboard); C16 / C20 the printed layout plus 4 / 8 tags of
160 mm; D16 / D20 the same with 100 mm tags. Worlds are built in memory by tools/room_world.py.

Odometry: `study` (kinsim_lite's noise, no bias), `drift2` (the main study's held-out condition: distance and turn
angle over-read by 2 %), `carpet` (kinsim_room.CARPET: the car veers on a forward move, turns fall short).

DV noise model: `frozen` = configs/dv.json as it is; `measured` = kinsim_room.MEASURED_SIGMA_DV through
kinsim_room.dv_override (the three sigma values fix_pose's conditioning test uses, set to the simulated estimate of
the tag detector; no file is edited); or (`one --dv FILE`, run_cell(dv=FILE)) a design-values file such as
configs/dv-real.json from tools/real_dv.py, through beaconmind/dv_real.use_dv (2026-11-24).

Metrics per episode (plan C10; truth is the simulator's): steps, how it ended, share of steps by pose source, ATE-RMSE
and final pose error of B2 and of dead reckoning B0, tags seen and tags mapped (a map entry within 0.30 m of a tag
with its ID), phantom entries, duplicated-ID pairs seen and mapped as two beacons, association outcomes
(metrics/pilot.py LabelTracker), steps in which the camera's near limit hid a tag, and the footprint's smallest
clearance to a wall or the desk.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this tool.
AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: --dv takes a design-values file (dv_scope).
"""
import argparse
import collections
import json
import math
import multiprocessing
import pathlib
import statistics
import sys

TOOLS = pathlib.Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(ROOT / "beaconmind" / "src"))
from beaconmind import dv_real  # noqa: E402
from beaconmind.envs import kinsim_lite as ks  # noqa: E402
from beaconmind.envs import kinsim_room as kr  # noqa: E402
from beaconmind.metrics import pilot as pm  # noqa: E402
import room_world as rw  # noqa: E402

ODOMETRY = {"study": ("study", 0.0), "drift2": ("study", 0.02), "carpet": ("carpet", 0.0)}
OPTIONS = {
    "A": {"label": "A: 12 tags, 160 mm, centre 0.23 m (as printed)", "variant": "printed", "tag_mm": None},
    "B": {"label": "B: 12 tags, 100 mm, centre 0.18 m", "variant": "printed", "tag_mm": 100.0},
    "C16": {"label": "C16: 16 tags, 160 mm", "variant": "plus4", "tag_mm": None},
    "C20": {"label": "C20: 20 tags, 160 mm", "variant": "plus8", "tag_mm": None},
    "D16": {"label": "D16: 16 tags, 100 mm", "variant": "plus4", "tag_mm": 100.0},
    "D20": {"label": "D20: 20 tags, 100 mm", "variant": "plus8", "tag_mm": 100.0},
}
RANGES = (2.0, 2.5, 3.0)
LAYOUT = ROOT / "evidence" / "M3" / "M3.T10" / "layout" / "layout.json"
SCENARIOS = ROOT / "configs" / "arenas" / "real-room-scenarios.json"


def seed_list(text):
    out = []
    for part in text.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b) + 1)) if b else [int(a)]
    return out


def option_world(option):
    o = OPTIONS[option]
    layout = json.loads(LAYOUT.read_text(encoding="utf-8"))
    return rw.build_world(layout, start=rw.default_start(), variant=o["variant"], tag_black_mm=o["tag_mm"])


def load_scenarios(path=SCENARIOS):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))["scenarios"]


def near_limit_steps(env, recs):
    """Steps in which at least one tag would have been detected-in-view but for the picture's top edge: the tag
    passes every visibility test once its centre is put at lens height (so it cannot leave the picture vertically)."""
    cam = env.noise.get("camera")
    if cam is None:
        return 0
    z = kr.camera_of(cam).z_m
    n = 0
    for r in recs:
        for t in env.scene["tags"]:
            if kr.visible(env.scene, r["truth"], t, env.noise) is None \
                    and kr.visible(env.scene, r["truth"], dict(t, z_m=z), env.noise) is not None:
                n += 1
                break
    return n


def episode_metrics(ep, env=None):
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
    if env is not None:
        out["share_steps_near_limit"] = near_limit_steps(env, recs) / len(recs)
    seen = {d["_tag"] for r in recs for d in r["raw"]["detections"]}
    final_map = recs[-1]["report"]["map"]
    ms = pm.map_scores_c10(final_map, world)
    out.update(tags_seen=len(seen), tags_mapped=round(ms["map_recall"] * len(world)), n_tags=len(world),
               map_entries=ms["n_entries"], phantoms=ms["phantoms"],
               confirmed=sum(b["state"] == "confirmed" for b in final_map), map_rmse_m=ms["map_rmse_m"])
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


def dv_scope(dv):
    """The design values a rehearsal runs with: `frozen`, `measured` (kinsim_room.MEASURED_SIGMA_DV) or a file."""
    if dv in ("frozen", "measured"):
        return kr.dv_override(**(kr.MEASURED_SIGMA_DV if dv == "measured" else {}))
    return dv_real.use_dv(dv)


def dv_tag(dv):
    return "" if dv == "frozen" else "-dv-measured" if dv == "measured" else "-dv-%s" % pathlib.Path(dv).stem


def run_cell(world, scenarios, seeds, preset, max_range, odometry, policy="block", patience=2, inset=0.0,
             noise_overrides=None, dv="frozen", log_dir=None, save_seeds=0):
    """All scenarios x seeds for one configuration. Returns the per-episode metric rows."""
    odo, bias = ODOMETRY[odometry]
    pol = kr.b2_step if policy == "frozen" else kr.make_b2_policy(dead_end="block", patience=patience)
    rows = []
    with dv_scope(dv):
        for sc in scenarios:
            for k, seed in enumerate(seeds):
                env = kr.KinSimEnv.room(world, sc["start_pose"], preset_name=preset, max_range_m=max_range,
                                        odometry=odo, odo_bias=bias, drive_inset_m=inset, noise_overrides=noise_overrides)
                ep = kr.run_episode(env, seed, policy=pol)
                rows.append(dict(episode_metrics(ep, env), scenario=sc["id"], seed=seed))
                if log_dir is not None and k < save_seeds and ep["records"]:
                    d = pathlib.Path(log_dir) / world["world_id"] / ("%s-r%.1f-%s%s" % (
                        preset, max_range, odometry, dv_tag(dv))) / sc["id"]
                    d.mkdir(parents=True, exist_ok=True)
                    ep["rehearsal"] = {"scenario": sc["id"], "preset": preset, "max_range_m": max_range,
                                       "odometry": odometry, "policy": policy, "patience": patience,
                                       "drive_inset_m": inset, "dv": dv,
                                       "dv_values": kr.MEASURED_SIGMA_DV if dv == "measured" else None,
                                       "dv_file": None if dv in ("frozen", "measured") else dv_real.record(dv)}
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
        "episodes": n, "scored": len(scored), "done": ends["DONE"], "budget": ends["budget"],
        "not_implemented": ends["not_implemented"], "not_implemented_branches": dict(detail),
        "steps_median": med(rows, "steps"), "steps_iqr": quartiles(rows, "steps"),
        "share_beacon_fix": mean(scored, "share_beacon_fix"), "share_position_fix": mean(scored, "share_position_fix"),
        "share_any_fix": mean(scored, "share_any_fix"), "share_prior_kept": mean(scored, "share_prior_kept"),
        "episodes_with_full_fix": sum(r["share_beacon_fix"] > 0 for r in scored),
        "share_steps_with_detection": mean(scored, "share_steps_with_detection"),
        "share_steps_two_detections": mean(scored, "share_steps_two_detections"),
        "share_steps_near_limit": mean(scored, "share_steps_near_limit"),
        "ate_b2_median_m": med(scored, "ate_b2_m"), "ate_b0_median_m": med(scored, "ate_b0_m"),
        "ate_diff_median_m": statistics.median(diff) if diff else None,
        "ate_b2_lower": sum(d < 0 for d in diff), "ate_b2_higher": sum(d > 0 for d in diff),
        "final_pos_b2_median_m": med(scored, "final_pos_b2_m"), "final_pos_b0_median_m": med(scored, "final_pos_b0_m"),
        "final_heading_b2_median_deg": med(scored, "final_heading_b2_deg"),
        "final_heading_b0_median_deg": med(scored, "final_heading_b0_deg"),
        "n_tags": scored[0]["n_tags"] if scored else None,
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
        "outside_drive_episodes": sum(r["outside_drive_steps"] > 0 for r in scored),
        "path_median_m": med(scored, "path_m"),
    }


# ---------------------------------------------------------------- the grid

def cell(group, name, option="A", preset="camera", max_range=2.5, odometry="study", dv="frozen", **kw):
    return dict(group=group, name=name, option=option, preset=preset, max_range=max_range, odometry=odometry, dv=dv, **kw)


def build_cells(groups, focus):
    f_opt, f_range = focus
    cells = []
    if "options" in groups:
        for odo in ODOMETRY:
            for opt in OPTIONS:
                for r in RANGES:
                    cells.append(cell("options", "%s, %.1f m" % (opt, r), opt, max_range=r, odometry=odo, save=True))
    if "options-dv" in groups:
        for odo in ("study", "drift2"):
            for opt in OPTIONS:
                for r in RANGES:
                    cells.append(cell("options-dv", "%s, %.1f m" % (opt, r), opt, max_range=r, odometry=odo,
                                      dv="measured", save=True))
    if "study-preset" in groups:
        for odo in ODOMETRY:
            for r in RANGES:
                cells.append(cell("study-preset", "study preset, %.1f m" % r, "A", preset="study", max_range=r,
                                  odometry=odo, save=True))
    base = dict(option=f_opt, max_range=f_range)
    for dv in ("frozen", "measured"):
        tag = "" if dv == "frozen" else ", measured DV sigmas"
        if "scenarios" in groups:
            for odo in ("study", "drift2"):
                for sid in ("S1", "S2", "S3", "S4", "S5"):
                    cells.append(cell("scenarios", sid, odometry=odo, dv=dv, only=sid, **base))
        if "driver" in groups:
            for odo in ("study", "carpet"):
                cells.append(cell("driver", "B2 as frozen" + tag, odometry=odo, dv=dv, policy="frozen", **base))
                cells.append(cell("driver", "dead end defined" + tag, odometry=odo, dv=dv, **base))
                cells.append(cell("driver", "dead end defined, E1 after 4 scans" + tag, odometry=odo, dv=dv, patience=4, **base))
        if "inset" in groups:
            for inset in (0.0, 0.2, 0.4):
                cells.append(cell("inset", "inset %.1f m%s" % (inset, tag), odometry="carpet", dv=dv, inset=inset, **base))
        if "bias" in groups:
            for b in (0.0, 2.0):
                cells.append(cell("bias", "bearing bias %+.0f deg%s" % (b, tag), odometry="study", dv=dv,
                                  noise_overrides={"bearing_bias_deg": b}, **base))
    if "range" in groups:
        for r in (1.5, 2.0, 2.5, 3.0, 3.5, 4.0):
            cells.append(cell("range", "%.1f m" % r, f_opt, max_range=r, odometry="study"))
    for c in cells:
        if c["group"] not in ("options", "options-dv", "study-preset"):
            c["focus"] = "%s:%.1f" % (f_opt, f_range)
    return cells


_WORK = {}


def _run(job):
    c, seeds, logs, save_seeds = job
    if c["option"] not in _WORK:
        _WORK[c["option"]] = option_world(c["option"])
    scenarios = [s for s in load_scenarios() if c.get("only") in (None, s["id"])]
    rows = run_cell(_WORK[c["option"]], scenarios, seeds, c["preset"], c["max_range"], c["odometry"],
                    policy=c.get("policy", "block"), patience=c.get("patience", 2), inset=c.get("inset", 0.0),
                    noise_overrides=c.get("noise_overrides"), dv=c["dv"],
                    log_dir=logs if c.get("save") else None, save_seeds=save_seeds)
    return dict(c, seeds=len(seeds), summary=summarise(rows))


def cell_key(c):
    return json.dumps([c["group"], c["name"], c["option"], c["preset"], c["max_range"], c["odometry"], c["dv"],
                       c.get("focus")])


def cmd_grid(args):
    f_opt, _, f_range = args.focus.partition(":")
    cells = build_cells(args.groups.split(","), (f_opt, float(f_range)))
    seeds = seed_list(args.seeds)
    path = pathlib.Path(args.json)
    doc = json.loads(path.read_text(encoding="utf-8")) if path.exists() and not args.fresh else {"cells": []}
    have = {cell_key(c): i for i, c in enumerate(doc["cells"])}
    jobs = [(c, seeds, args.logs, args.save_seeds) for c in cells]
    with multiprocessing.Pool(args.jobs) as pool:
        for done in pool.imap_unordered(_run, jobs):
            done["seed_range"] = args.seeds
            k = cell_key(done)
            if k in have:
                doc["cells"][have[k]] = done
            else:
                have[k] = len(doc["cells"])
                doc["cells"].append(done)
            print("%s / %s / %s / %s / dv %s: %d episodes" % (done["group"], done["name"], done["odometry"],
                                                              done["preset"], done["dv"], done["summary"]["episodes"]),
                  flush=True)
    doc["scenarios"] = load_scenarios()
    doc["options"] = OPTIONS
    doc["measured_sigma_dv"] = kr.MEASURED_SIGMA_DV
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- tables

def f(v, fmt="%.1f", none="-"):
    return none if v is None else fmt % v


HEAD = ("| %s | ended: DONE / budget / B2 stopped | steps, median (IQR) | steps with a tag / with two, %% | "
        "fix share, %%: full / position / any | prior kept, %% | episodes with a full fix | ATE cm, median: B2 / B0 "
        "(B2 lower in) | final position error cm: B2 / B0 | final heading error deg: B2 / B0 | tags seen / mapped / "
        "in the room | duplicated pairs seen / mapped as two | wrong matches | steps where the near limit hid a tag, %% "
        "| closest to a wall, cm (episodes touching) |")


def table_row(name, s):
    name = name.replace(" | ", ", ")
    iqr = s["steps_iqr"]
    return ("| %s | %d / %d / %d | %s (%s) | %s / %s | %s / %s / %s | %s | %d of %d | %s / %s (%d of %d) | %s / %s | "
            "%s / %s | %s / %s / %s | %d / %d | %d | %s | %s (%d) |" % (
                name, s["done"], s["budget"], s["not_implemented"], f(s["steps_median"], "%.0f"),
                "%.0f-%.0f" % tuple(iqr) if iqr else "-",
                f(100 * s["share_steps_with_detection"]), f(100 * s["share_steps_two_detections"]),
                f(100 * s["share_beacon_fix"], "%.2f"), f(100 * s["share_position_fix"]), f(100 * s["share_any_fix"]),
                f(100 * s["share_prior_kept"]), s["episodes_with_full_fix"], s["scored"],
                f(100 * s["ate_b2_median_m"]), f(100 * s["ate_b0_median_m"]), s["ate_b2_lower"], s["scored"],
                f(100 * s["final_pos_b2_median_m"]), f(100 * s["final_pos_b0_median_m"]),
                f(s["final_heading_b2_median_deg"]), f(s["final_heading_b0_median_deg"]),
                f(s["tags_seen_mean"]), f(s["tags_mapped_mean"]), f(s["n_tags"], "%d"), s["dup_pairs_seen"],
                s["dup_pairs_mapped_twice"], s["assoc_fp"],
                f(None if s["share_steps_near_limit"] is None else 100 * s["share_steps_near_limit"]),
                f(100 * s["min_clearance_m"], "%.0f"), s["contact_episodes"]))


def table(title, label, rows):
    return "\n".join(["**%s**" % title, "", HEAD % label, "|" + " --- |" * 15] + [table_row(n, s) for n, s in rows]) + "\n"


def cmd_tables(args):
    doc = json.loads(pathlib.Path(args.json).read_text(encoding="utf-8"))
    cells = doc["cells"]
    order = list(doc["options"])
    pick = lambda **kw: sorted((c for c in cells if all(c.get(k) == v for k, v in kw.items())),
                               key=lambda c: (order.index(c["option"]), c["max_range"], c.get("inset", 0.0)))
    n_ep = lambda cs: sorted({c["summary"]["episodes"] for c in cs})
    out = ["<!-- Generated by tools/room_rehearsal.py tables from rehearsal-b2.json; do not edit by hand. -->", "",
           "Driver in every table unless a row says otherwise: B2 with the dead-end branch defined "
           "(kinsim_room.make_b2_policy), E1 as written; camera noise preset; five start poses pooled. ATE and final "
           "errors are against the simulator's truth; B0 is dead reckoning on the same odometry. \"B2 stopped\" = an "
           "unimplemented branch of the coded procedure. Fix shares are means over episodes of the share of steps. "
           "Options: " + "; ".join(o["label"] for o in doc["options"].values()) + ".", ""]
    for dv, group, title in (("frozen", "options", "Table 1%s. Options and range limits, DV noise model as frozen in configs/dv.json"),
                             ("measured", "options-dv", "Table 2%s. The same with the DV noise model set to the simulated "
                              "estimate (kinsim_room.MEASURED_SIGMA_DV %s)" % ("%s", doc["measured_sigma_dv"]))):
        for letter, odo in zip("abc", ODOMETRY):
            cs = pick(group=group, odometry=odo)
            if cs:
                out.append(table((title % letter) + "; %s odometry; %s episodes per row" % (odo, n_ep(cs)),
                                 "option, range limit", [(c["name"], c["summary"]) for c in cs]))
    for letter, odo in zip("abc", ODOMETRY):
        cs = pick(group="study-preset", odometry=odo)
        if cs:
            out.append(table("Table 3%s. The study's placeholder noise preset (60 deg view, no near limit) on option A; "
                             "%s odometry; %s episodes per row" % (letter, odo, n_ep(cs)), "preset, range limit",
                             [(c["name"], c["summary"]) for c in cs]))
    focuses = sorted({c["focus"] for c in cells if c.get("focus")})
    for fc in focuses:
        scen = {s["id"]: s["start_pose"] for s in doc["scenarios"]}
        for dv in ("frozen", "measured"):
            for odo in ("study", "drift2"):
                cs = pick(group="scenarios", focus=fc, dv=dv, odometry=odo)
                if cs:
                    out.append(table("Table 4 (%s, DV %s, %s odometry). Per start pose; %s episodes per row" % (
                        fc, dv, odo, n_ep(cs)), "start pose (room frame)",
                        [("%s (%.2f, %.2f, %.0f deg)" % (c["name"], scen[c["name"]]["x_m"], scen[c["name"]]["y_m"],
                                                         scen[c["name"]]["theta_deg"]), c["summary"]) for c in cs]))
        for group, title in (("driver", "Table 5 (%s). The driver: B2 as frozen, with the dead-end branch defined, with a more patient E1"),
                             ("inset", "Table 6 (%s). Driving area moved in from every edge, carpet odometry"),
                             ("bias", "Table 7 (%s). A constant bearing offset (the camera's yaw is known to +-2 deg before the pilot)")):
            cs = pick(group=group, focus=fc)
            if cs:
                out.append(table((title % fc) + "; %s episodes per row" % n_ep(cs), "odometry: variant",
                                 [("%s: %s" % (c["odometry"], c["name"]), c["summary"]) for c in cs]))
        cs = pick(group="range", focus=fc)
        if cs:
            out.append(table("Table 8 (option %s). Range limit sweep, study odometry, DV frozen; %s episodes per row"
                             % (fc.split(":")[0], n_ep(cs)), "range limit", [(c["name"], c["summary"]) for c in cs]))
    text = "\n".join(out)
    if args.out:
        pathlib.Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text)


def cmd_one(args):
    world = option_world(args.option)
    sc = next(s for s in load_scenarios() if s["id"] == args.scenario)
    odo, bias = ODOMETRY[args.odometry]
    if args.dv not in ("frozen", "measured"):
        problems = dv_real.check_file(args.dv)
        if problems:
            sys.exit("--dv: " + "; ".join(problems))
    with dv_scope(args.dv):
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
    print(json.dumps(dict(episode_metrics(ep, env), dv=args.dv if args.dv in ("frozen", "measured")
                          else dv_real.record(args.dv)), indent=1))
    if args.out:
        pathlib.Path(args.out).write_text(json.dumps(ep), encoding="utf-8")


def cmd_conditioning(args):
    """How often can fix_pose's full fix be `well_conditioned` (sigma_xy <= 0.15 m and sigma_theta <= 8 deg under the
    DV noise model) for tags that share one picture? Random sets of 2-4 tags at bearings inside the half field of view
    (less the tag's own half width) and ranges in [0.75, far]; `same wall`: all at the same depth ahead (a wall seen
    square-on), `any depth`: independent ranges."""
    import random
    from beaconmind import geometry as g
    from beaconmind.dv import load_dv
    rng = random.Random(args.seed)
    pose = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
    half = 22.4
    print("fix_pose full fix: share of random tag sets in one 46 deg picture that are well conditioned "
          "(%d sets per cell, seed %d)" % (args.samples, args.seed))
    print("| DV noise model | tags in the picture | same wall, depth 0.75-2.5 m | any depth 0.75-2.5 m |")
    print("| --- | --- | --- | --- |")
    for label, dv in (("configs/dv.json (range 0.05 + 0.05 r m, bearing 2.0 deg)", load_dv()),
                      ("MEASURED_SIGMA_DV (range 0.01 + 0.012 r m, bearing 0.5 deg)", dict(load_dv(), **kr.MEASURED_SIGMA_DV))):
        for k in (2, 3, 4):
            cells = []
            for same_wall in (True, False):
                ok = 0
                for _ in range(args.samples):
                    depth = rng.uniform(0.75, 2.5)
                    matches = []
                    for _ in range(k):
                        r0 = depth if same_wall else rng.uniform(0.75, 2.5)
                        b = rng.uniform(-1.0, 1.0) * (half - math.degrees(math.atan(0.08 / r0)))
                        r = r0 / math.cos(math.radians(b)) if same_wall else r0
                        matches.append({"det": {"range_m": r, "bearing_deg": b}, "point": g.map_point(pose, r, b)})
                    ok += g.fix_pose(pose, matches, dv=dv)["full"]["well_conditioned"]
                cells.append("%.1f %%" % (100.0 * ok / args.samples))
            print("| %s | %d | %s | %s |" % (label, k, cells[0], cells[1]))


def cmd_layout_search(args):
    """Greedy choice of extra tag positions: each step adds the candidate that most raises the share of poses from
    which a full fix is possible in one picture (fix_pose's `well_conditioned` on the tags in view, true geometry),
    ties broken by the share of poses with two tags in view. Poses: a 0.25 m grid at least --inset inside the
    driving area, 12 headings. Candidates: every 5 cm along the walls' usable stretches (tools/room_layout.py WALLS),
    at least --spacing from every tag already placed."""
    from beaconmind import geometry as g
    from beaconmind.dv import load_dv
    world = option_world("A")
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
        return {"x_m": x, "y_m": y, "normal_deg": math.degrees(math.atan2(ny, nx)), "n": (nx, ny), "z_m": proto["z_m"],
                "half_m": proto["black_size_m"] / 2, "wall": wall_key, "along": along}

    def seen_from(tag):
        return {k for k, pose in enumerate(poses) if kr.visible(scene, pose, tag, noise) is not None}

    placed = []
    for t in world["tags"]:
        nd = math.radians(t["normal_deg"])
        placed.append(dict(t, n=(math.cos(nd), math.sin(nd)), half_m=t["black_size_m"] / 2))
    cands = []
    for w in rw.rl.WALLS:
        for a, b in w["spans"]:
            s = a + args.spacing / 2 + 0.02
            while s <= b - args.spacing / 2 - 0.02 + 1e-9:
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
            gain = sum(1 for k in cv if k not in fix and k in at and fixable(k, at[k] + [c]))
            gain2 = sum(1 for k in cv if k not in two and k in at)
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
    g_ = sub.add_parser("grid")
    g_.add_argument("--groups", default="options,options-dv,study-preset",
                    help="options, options-dv, study-preset, scenarios, driver, inset, bias, range")
    g_.add_argument("--focus", default="A:2.5", help="OPTION:RANGE for the detail groups")
    g_.add_argument("--seeds", default="3000-3029")
    g_.add_argument("--json", required=True)
    g_.add_argument("--fresh", action="store_true", help="start the JSON file again instead of adding to it")
    g_.add_argument("--logs")
    g_.add_argument("--save-seeds", type=int, default=5, help="save the logs of the first N seeds of the option cells")
    g_.add_argument("--jobs", type=int, default=max(1, multiprocessing.cpu_count() - 1))
    g_.set_defaults(func=cmd_grid)
    t_ = sub.add_parser("tables")
    t_.add_argument("--json", required=True)
    t_.add_argument("--out")
    t_.set_defaults(func=cmd_tables)
    o = sub.add_parser("one")
    o.add_argument("--option", default="A", choices=sorted(OPTIONS))
    o.add_argument("--scenario", default="S1")
    o.add_argument("--preset", default="camera")
    o.add_argument("--range", type=float, default=2.5)
    o.add_argument("--odometry", default="study", choices=sorted(ODOMETRY))
    o.add_argument("--dv", default="frozen", help="frozen (configs/dv.json), measured (kinsim_room.MEASURED_SIGMA_DV), "
                                                "or a design-values file such as configs/dv-real.json")
    o.add_argument("--seed", type=int, default=3000)
    o.add_argument("--policy", default="block", choices=("block", "frozen"))
    o.add_argument("--patience", type=int, default=2)
    o.add_argument("--inset", type=float, default=0.0)
    o.add_argument("--trace", action="store_true")
    o.add_argument("--out")
    o.set_defaults(func=cmd_one)
    ls = sub.add_parser("layout-search")
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
