"""Offline replay of the real car's B2 episodes through the model arms (plan section 3.6 work list 3.6; M3.T19, M4.T13).

The batch runner (car/batch.py) writes one folder per episode, data/batches/<label>/episodes/<id>/: the closed-loop
harness's rows (seed_<n>.jsonl: raw sensing, the observation the driver saw, B2's report and calls, the executed
move), truth.jsonl (one line per step: the batch's ground truth, tag resection against the surveyed world, in the
episode's map frame, with its sigma) and the manifest entry (start pose, end-of-episode full-circle fix, result).
The frozen replay loop (harness/replay.py replay_seed) reads observation logs in the study's format (C9.1,
tools/pilot_record.py / kinsim_room.run_episode): {seed, world, records: [{step, truth, raw, report, calls}], noise,
arena}. So:

- episode_to_obslog()  converts one episode; convert_batch() a whole batch (only episodes that ran to their own end:
                       status done, or halted by a check after the end, noted in index.json; the others are listed
                       with the reason). Each record keeps the truth with its sigma, B2's own
                       estimate (the reference row), and `observation_real`: the fields of the observation the driver
                       really saw that the frozen kinsim_lite.as_observation cannot rebuild from `raw` (source "real",
                       status and error, sensors, odometry quality, the validator's counters).
- real_observations()  puts those fields back into the step message during a replay: kinsim_lite.as_observation is
                       wrapped for the block (a real step with `status: error` must reach the model as an error, prompt
                       row 0). No frozen file is edited; on exit the original function is back.
- ProcedureAgent       a free, deterministic stand-in for a model arm with the provider interface: the coded procedure's
                       estimation on the replayed observation, its tool calls through the frozen dispatcher, decision
                       NONE (replay mode). It checks the pipeline end to end without a model call: its final poses
                       must equal B2's own.
- final_errors(), summarize(), result_markdown()   the result per arm: final-position error per episode against the
                       batch's truth at the last step (with its sigma), B0 (dead reckoning on the same odometry) and B2
                       (the live driver) as reference rows, median and spread.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this module.
"""
import contextlib
import copy
import glob
import hashlib
import json
import math
import os
import statistics
import time

from beaconmind import geometry as g
from beaconmind.envs import kinsim_lite as ks
from beaconmind.harness import tools_d5 as t5

SCHEMA = "bm.real_obslog/1"
OVERLAY_FIELDS = ("source", "status", "error", "sensors", "odometry.quality", "counters.latched",
                  "counters.consecutive_contacts", "counters.consecutive_slips", "counters.consecutive_errors")


def _jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def wrap_deg(a):
    return (a + 180.0) % 360.0 - 180.0


def sha12_bytes(data):
    return hashlib.sha256(data).hexdigest()[:12]


def to_map_pose(start, pose):
    """An arena-frame pose in the map frame of `start` (plan C1; car/batch.py to_map_pose)."""
    th = math.radians(start["theta_deg"])
    dx, dy = pose["x_m"] - start["x_m"], pose["y_m"] - start["y_m"]
    return {"x_m": dx * math.cos(th) + dy * math.sin(th), "y_m": -dx * math.sin(th) + dy * math.cos(th),
            "theta_deg": wrap_deg(pose["theta_deg"] - start["theta_deg"])}


# ---------------------------------------------------------------- conversion

def observation_real(obs):
    """The overlay fields of a logged observation (see OVERLAY_FIELDS)."""
    odo = obs.get("odometry") or {}
    c = obs.get("counters") or {}
    return {"source": obs.get("source"), "status": obs.get("status", "ok"), "error": obs.get("error"),
            "sensors": obs.get("sensors"), "odometry_quality": odo.get("quality"),
            "counters": {k: c.get(k) for k in ("latched", "consecutive_contacts", "consecutive_slips",
                                               "consecutive_errors") if k in c}}


def episode_to_obslog(batch_dir, entry, world_doc, world_file=None):
    """The observation log of one finished episode (manifest `entry`). ValueError when the folder is not usable."""
    from beaconmind.envs import kinsim_room as kr
    seed = int(entry["seed"])
    ep_dir = os.path.join(batch_dir, "episodes", entry["id"])
    rows = sorted(_jsonl(os.path.join(ep_dir, "seed_%d.jsonl" % seed)), key=lambda r: r["step"])
    if not rows or [r["step"] for r in rows] != list(range(len(rows))):
        raise ValueError("%s: steps are not 0..n-1" % entry["id"])
    truth_rows = _jsonl(os.path.join(ep_dir, "truth.jsonl"))
    # one truth row per step's sensing; an episode whose last step still executed a move (the step budget) has the
    # sensing after it as one more row, which no step uses
    extra = len(truth_rows) - len(rows)
    if not (extra == 0 or (extra == 1 and rows[-1].get("executed_move"))):
        raise ValueError("%s: %d truth rows for %d steps" % (entry["id"], len(truth_rows), len(rows)))
    if any(t.get("row", k) != k for k, t in enumerate(truth_rows)):
        raise ValueError("%s: truth.jsonl rows are not numbered 0..n" % entry["id"])
    truth_rows = truth_rows[:len(rows)]
    start = entry["start_pose_world"]
    records = []
    for r, t in zip(rows, truth_rows):
        tm = t["truth_map"]
        if r.get("truth") is not None and any(abs(r["truth"][k] - tm[k]) > 1e-9 for k in ("x_m", "y_m", "theta_deg")):
            raise ValueError("%s step %d: the row's truth differs from truth.jsonl" % (entry["id"], r["step"]))
        rec = {"step": r["step"], "truth": dict(tm), "raw": r["raw"], "report": r.get("report"),
               "calls": r.get("calls"), "b2_estimate": r.get("estimate_pose"),
               "observation_real": observation_real(r.get("observation") or {}),
               "truth_no_fix": t.get("no_fix"), "truth_view_fix": (t.get("view_fix") or {}).get("kind")}
        if t.get("sim_truth_world"):
            rec["truth_sim"] = to_map_pose(start, t["sim_truth_world"])
        records.append(rec)
    scene = kr.room_scene(world_doc, start_pose=start)
    end_fix = entry.get("end_fix") or {}
    end_map, end_source = entry.get("end_pose_map"), "manifest end_pose_map" if entry.get("end_pose_map") else None
    if end_map is None and end_fix.get("ok") and end_fix.get("pose_now"):
        # a batch halted by a check after the episode writes no end_pose_map; the end circle's own result is the pose
        # the batch tracked after it (car/batch.py sets end_pose_world from that same tracked pose)
        end_map, end_source = to_map_pose(start, end_fix["pose_now"]), "end_fix.pose_now"
    return {"schema": SCHEMA, "seed": seed, "world": scene["world"], "arena": scene["arena"], "records": records,
            "noise": None,
            "real": {"batch": os.path.basename(os.path.normpath(batch_dir)), "episode": entry["id"],
                     "attempt": entry.get("attempt"), "scenario": entry.get("scenario"), "policy": entry.get("policy"),
                     "ended_by": (entry.get("result") or {}).get("ended_by"), "steps": len(records),
                     "start_pose_world": start, "world_file": world_file, "world_id": world_doc.get("world_id"),
                     "end_pose_map": end_map, "end_pose_source": end_source,
                     "end_fix_sigma_xy_m": end_fix.get("sigma_xy_m"),
                     "end_fix_ok": end_fix.get("ok"), "final_pose_error_batch": entry.get("final_pose_error"),
                     "real_car": None}}


END_NORMALLY = ("DONE", "budget")


def finished(entry):
    """True when the episode ran to its own end (DONE, or the step budget) with every step written: status "done",
    or status "halted" by a check that ran after the episode (result complete, ended normally; car/batch.py checks
    the end circle and the odometry over the episode after run_episode has returned)."""
    res = entry.get("result") or {}
    if not res.get("complete") or res.get("ended_by") not in END_NORMALLY:
        return False
    return entry.get("status") == "done" or (entry.get("status") == "halted" and entry.get("end_fix") is not None)


def _course_rel(path):
    """A path relative to course-project/ (so the logs' bytes do not depend on the directory the tool ran in)."""
    import beaconmind
    root = os.path.realpath(str(beaconmind.course_root()))
    p = os.path.realpath(path)
    return os.path.relpath(p, root) if p.startswith(root + os.sep) else p


def convert_batch(batch_dir, out_dir, world_path=None, seed_base=0, write_index=True):
    """Write <out_dir>/seed_<n>.json for every episode that ran to its end and index.json; returns the index. The log's
    seed is seed_base + the batch's own seed of the episode (convert_batches gives every batch its own base)."""
    with open(os.path.join(batch_dir, "manifest.json"), encoding="utf-8") as fh:
        man = json.load(fh)
    world_path = world_path or man["params"]["world_path"]
    if not os.path.isabs(world_path):
        import beaconmind
        world_path = os.path.join(str(beaconmind.course_root()), world_path)
    with open(world_path, "rb") as fh:
        world_bytes = fh.read()
    world_doc = json.loads(world_bytes)
    os.makedirs(out_dir, exist_ok=True)
    index = {"schema": "bm.real_obslog_index/1", "batch": os.path.basename(os.path.normpath(batch_dir)),
             "batch_config": man.get("config"), "real_car": man.get("real_car"), "status": man.get("status"),
             "halt": man.get("halt"), "world_file": _course_rel(world_path), "world_sha12": sha12_bytes(world_bytes),
             "dv_file": man["params"].get("dv_file"), "max_range_m": man["params"].get("max_range_m"),
             "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "episodes": [], "excluded": []}
    by_index = {}
    for e in man.get("episodes") or []:
        by_index.setdefault(e["index"], []).append(e)
    for idx in sorted(by_index):
        tries = by_index[idx]
        done = [e for e in tries if finished(e)]
        for e in tries:
            if e not in done[-1:]:
                if e in done:
                    reason = "superseded by a later attempt"
                else:
                    reason = "did not end normally: %s" % (e.get("halt") or e.get("result"))
                    if done:
                        reason += "; a later attempt replaces it"
                index["excluded"].append({"episode": e["id"], "status": e.get("status"), "reason": reason})
        if not done:
            continue
        e = done[-1]
        try:
            doc = episode_to_obslog(batch_dir, e, world_doc, index["world_file"])
            doc["seed"] = seed_base + doc["seed"]
            doc["real"]["batch_seed"] = int(e["seed"])
        except (OSError, ValueError, KeyError) as exc:
            index["excluded"].append({"episode": e["id"], "status": e.get("status"), "reason": str(exc)})
            continue
        doc["real"]["real_car"] = man.get("real_car")
        note = None
        if e.get("status") != "done":
            note = "completed; batch halted after the end by %s" % ((e.get("halt") or {}).get("code") or e.get("halt"))
            doc["real"]["note"] = note
        data = json.dumps(doc).encode()
        path = os.path.join(out_dir, "seed_%d.json" % doc["seed"])
        with open(path, "wb") as fh:
            fh.write(data)
        last = doc["records"][-1]
        index["episodes"].append({"seed": doc["seed"], "batch": index["batch"], "episode": e["id"],
                                  "scenario": e.get("scenario"),
                                  "steps": len(doc["records"]), "ended_by": doc["real"]["ended_by"],
                                  "truth_sigma_xy_m_last": last["truth"].get("sigma_xy_m"),
                                  "truth_is_a_fix_last": last["truth"].get("fix"), "sha12": sha12_bytes(data),
                                  "note": note, "end_pose_source": doc["real"]["end_pose_source"]})
    for x in index["excluded"]:
        x["batch"] = index["batch"]
    index["steps"] = sum(e["steps"] for e in index["episodes"])
    if write_index:
        with open(os.path.join(out_dir, "index.json"), "w", encoding="utf-8") as fh:
            json.dump(index, fh, indent=1)
    return index


SET_SCHEMA = "bm.real_obslog_set/1"
SEED_STRIDE = 1000


def convert_batches(batch_dirs, out_dir, world_path=None):
    """One observation-log set from several batches, built so that a rerun adds to it: each batch keeps the seed base
    it got the first time (1000, 2000, ... in the order first seen, recorded in index.json `batches`), an episode's
    log is seed_base + its own seed, and a batch converted before but not named this time keeps its earlier entries.
    A rerun writes the same bytes for an episode that has not changed, so the replay runner resumes on them."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "index.json")
    old = None
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            old = json.load(fh)
        if old.get("schema") != SET_SCHEMA:
            raise ValueError("%s holds a single-batch index; use a new folder for a set" % out_dir)
    registry = list((old or {}).get("batches") or [])
    names = [b["batch"] for b in registry]
    for bd in batch_dirs:
        name = os.path.basename(os.path.normpath(bd))
        if name not in names:
            registry.append({"batch": name, "seed_base": SEED_STRIDE * (len(registry) + 1)})
            names.append(name)
    given = {os.path.basename(os.path.normpath(bd)): bd for bd in batch_dirs}
    episodes, excluded = [], []
    for b in registry:
        if b["batch"] in given:
            sub = convert_batch(given[b["batch"]], out_dir, world_path, seed_base=b["seed_base"], write_index=False)
            b.update({k: sub.get(k) for k in ("batch_config", "real_car", "status", "halt", "world_file", "world_sha12",
                                              "dv_file", "max_range_m")})
            b["converted"] = sub["created"]
            episodes += sub["episodes"]
            excluded += sub["excluded"]
        else:
            episodes += [e for e in old["episodes"] if e.get("batch") == b["batch"]]
            excluded += [x for x in old.get("excluded", []) if x.get("batch") == b["batch"]]
    worlds = {b.get("world_sha12") for b in registry}
    index = {"schema": SET_SCHEMA, "batch": " + ".join(names), "batches": registry,
             "batch_config": ", ".join(str(b.get("batch_config")) for b in registry),
             "real_car": all(b.get("real_car") for b in registry),
             "world_file": ", ".join(sorted({str(b.get("world_file")) for b in registry})),
             "world_sha12": ", ".join(sorted(str(w) for w in worlds)),
             "dv_file": "; ".join(sorted({str(b.get("dv_file")) for b in registry})),
             "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
             "episodes": sorted(episodes, key=lambda e: e["seed"]), "excluded": excluded}
    index["steps"] = sum(e["steps"] for e in index["episodes"])
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=1)
    return index


# ---------------------------------------------------------------- the real observation in the step message

@contextlib.contextmanager
def real_observations(docs):
    """Inside the block, kinsim_lite.as_observation (what the frozen replay loop builds each step message with) also
    sets the overlay fields of the logged real observation of that (seed, step). Thread-safe for reading; the table
    is filled before the block."""
    table = {(d["seed"], r["step"]): r.get("observation_real") for d in docs for r in d["records"]}
    orig = ks.as_observation

    def as_observation(seed, raw, counters, mode="replay"):
        obs = orig(seed, raw, counters, mode)
        ov = table.get((seed, raw["step"]))
        if ov:
            for k in ("source", "status"):
                if ov.get(k) is not None:
                    obs[k] = ov[k]
            if ov.get("status") == "error" or ov.get("error") is not None:
                obs["error"] = ov.get("error")
            if isinstance(ov.get("sensors"), dict):
                obs["sensors"] = dict(ov["sensors"])
            if obs.get("odometry") and ov.get("odometry_quality"):
                obs["odometry"]["quality"] = ov["odometry_quality"]
            obs["counters"].update({k: v for k, v in (ov.get("counters") or {}).items() if v is not None})
        return obs
    ks.as_observation = as_observation
    try:
        yield table
    finally:
        ks.as_observation = orig


# ---------------------------------------------------------------- a free stand-in for a model arm

class ProcedureAgent:
    """The coded procedure's estimation on the replayed observation, with the provider interface of the replay loop
    (harness/replay.py): its tool calls go through the frozen dispatcher (tools_d5.run_tool), its report carries
    decision NONE (replay mode). No network, no cost."""

    arm = "L2:procedure-replay"
    provider = "coded_procedure"

    def header(self):
        return {"provider": self.provider, "settings": {"policy": "kinsim_lite.estimate_step + decide_step, decision "
                                                                   "NONE in replay"}, "price_usd_per_mtok": None,
                "max_turns": None}

    def step(self, system_text, obs, prev, budget, log, sample_key=None):
        t0 = time.perf_counter()
        state, calls = {"moved": None, "estop": False}, []
        try:
            est = ks.estimate_step(obs, prev)
            mem = ks.initial_memory() if prev is None else prev["memory"]
            _decision, m2 = ks.decide_step(est, mem, obs["safety"], obs["counters"]["steps_left"])
        except Exception as exc:  # noqa: BLE001 - a step the procedure cannot process: the loop's fallback row
            return {"final_text": None, "calls": [], "turns": [], "state": state,
                    "error": "procedure: %s: %s" % (type(exc).__name__, exc),
                    "seconds": round(time.perf_counter() - t0, 3), "cost_usd": 0.0}
        for e in est["new_entries"]:
            e["first_seen_scan"] = m2["scan_index"]
        for name, args in est["calls"]:
            calls.append({"tool": name, "args": args, "result": t5.rnd(t5.run_tool(name, args, obs, prev, state))})
        report = {"step": obs["step"], "mode": obs.get("mode", "replay"), "mission": "EXPLORE",
                  "pose": ks.rp(est["pose"]), "pose_source": est["pose_source"],
                  "associations": [{k: v for k, v in a.items() if k != "conflict"} for a, _ in est["assoc"]],
                  "loop_closure": est["loop_closure"], "map": est["new_map"], "memory": m2, "decision": "NONE",
                  "move_result": "not_called", "requested_mission": None, "message": None, "note": None}
        return {"final_text": json.dumps(report), "calls": calls, "turns": [], "state": state, "error": None,
                "seconds": round(time.perf_counter() - t0, 3), "cost_usd": 0.0}


# ---------------------------------------------------------------- results

def _err(est, truth):
    return {"m": math.hypot(est["x_m"] - truth["x_m"], est["y_m"] - truth["y_m"]),
            "deg": abs(wrap_deg(est["theta_deg"] - truth["theta_deg"]))}


def load_obslogs(obslog_dir):
    with open(os.path.join(obslog_dir, "index.json"), encoding="utf-8") as fh:
        index = json.load(fh)
    docs = {}
    for e in index["episodes"]:
        with open(os.path.join(obslog_dir, "seed_%d.json" % e["seed"]), encoding="utf-8") as fh:
            docs[e["seed"]] = json.load(fh)
    return index, docs


def final_errors(docs, runs):
    """{arm: {seed: row}} with the final-position and heading error of each episode against the batch's truth at the
    last step (and the end-of-episode circle's position, and the simulator's truth when the log has it).
    `runs` = {arm label: run folder}. B0 and B2 come from the logs themselves. An arm's episode counts only when every
    step of it was replayed."""
    out = {"B0": {}, "B2": {}}
    for arm in runs:
        out[arm] = {}
    for seed, d in sorted(docs.items()):
        recs = d["records"]
        last = recs[-1]
        truth = last["truth"]
        ests = {"B0": ks.dead_reckoning(recs)[-1], "B2": last.get("b2_estimate") or (last.get("report") or {}).get("pose")}
        for arm, folder in runs.items():
            path = os.path.join(folder, "seed_%d.jsonl" % seed)
            rows = _jsonl(path) if os.path.exists(path) else []
            ests[arm] = rows[-1]["estimate_pose"] if len(rows) == len(recs) else None
        if last.get("truth_sim"):
            out.setdefault("_truth_check", {})[seed] = {"truth_last": truth, "truth_sim_last": last["truth_sim"]}
        for arm, est in ests.items():
            if est is None:
                out[arm][seed] = {"episode": d["real"]["episode"], "complete": False}
                continue
            e = _err(est, truth)
            row = {"episode": d["real"]["episode"], "scenario": d["real"]["scenario"], "steps": len(recs),
                   "complete": True, "final_m": e["m"], "final_deg": e["deg"],
                   "truth_sigma_xy_m": truth.get("sigma_xy_m"), "truth_is_a_fix": truth.get("fix"),
                   "estimate": est}
            end = d["real"].get("end_pose_map")
            if end:
                row["vs_end_circle_m"] = math.hypot(est["x_m"] - end["x_m"], est["y_m"] - end["y_m"])
            if last.get("truth_sim"):
                row["vs_sim_truth_m"] = _err(est, last["truth_sim"])["m"]
            out[arm][seed] = row
    return out


def _q(values, q):
    s = sorted(values)
    if not s:
        return None
    pos = (len(s) - 1) * q
    lo, hi = int(math.floor(pos)), int(math.ceil(pos))
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def summarize(errors):
    """{arm: {n, n_incomplete, median_m, q1_m, q3_m, min_m, max_m, mean_m, median_deg, median_truth_sigma_m,
    median_vs_end_circle_m, median_vs_sim_truth_m}}."""
    out = {}
    for arm, by_seed in errors.items():
        if arm.startswith("_"):
            continue
        rows = [r for r in by_seed.values() if r.get("complete")]
        m = [r["final_m"] for r in rows]
        out[arm] = {"n": len(rows), "n_incomplete": sum(1 for r in by_seed.values() if not r.get("complete")),
                    "median_m": _q(m, 0.5), "q1_m": _q(m, 0.25), "q3_m": _q(m, 0.75),
                    "min_m": min(m) if m else None, "max_m": max(m) if m else None,
                    "mean_m": statistics.fmean(m) if m else None,
                    "median_deg": _q([r["final_deg"] for r in rows], 0.5),
                    "median_truth_sigma_m": _q([r["truth_sigma_xy_m"] for r in rows if r.get("truth_sigma_xy_m") is not None], 0.5),
                    "median_vs_end_circle_m": _q([r["vs_end_circle_m"] for r in rows if "vs_end_circle_m" in r], 0.5),
                    "median_vs_sim_truth_m": _q([r["vs_sim_truth_m"] for r in rows if "vs_sim_truth_m" in r], 0.5)}
    return out


def _cm(v):
    return "" if v is None else "%.1f" % (100 * v)


def result_markdown(title, index, errors, summary, order):
    lines = ["# %s" % title, "",
             "Batch `%s` (config %s, real car: %s); %d episodes, %d steps; world `%s` (sha12 %s); %s." % (
                 index["batch"], index.get("batch_config"), index.get("real_car"), len(index["episodes"]),
                 index["steps"], index["world_file"], index["world_sha12"], index.get("dv_file")),
             "", "Final-position error at the last step against the batch's truth (tag resection against the surveyed "
             "tags, in the map frame of the episode's start), in cm. `vs end circle`: against the position of the "
             "full circle the batch turns after the episode; `vs simulator truth`: only a dry run has it.", "",
             "| Arm | n | median | IQR | min | max | median heading error (deg) | median truth sigma | vs end circle (median) | vs simulator truth (median) |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for arm in order:
        s = summary.get(arm)
        if not s:
            continue
        lines.append("| %s | %d%s | %s | %s to %s | %s | %s | %s | %s | %s | %s |" % (
            arm, s["n"], (" (+%d incomplete)" % s["n_incomplete"]) if s["n_incomplete"] else "", _cm(s["median_m"]),
            _cm(s["q1_m"]), _cm(s["q3_m"]), _cm(s["min_m"]), _cm(s["max_m"]),
            "" if s["median_deg"] is None else "%.1f" % s["median_deg"], _cm(s["median_truth_sigma_m"]),
            _cm(s["median_vs_end_circle_m"]), _cm(s["median_vs_sim_truth_m"]) or "none"))
    gaps = [math.hypot(d_t["x_m"] - d_s["x_m"], d_t["y_m"] - d_s["y_m"]) for d_t, d_s in
            ((r["truth_last"], r["truth_sim_last"]) for r in errors.get("_truth_check", {}).values())]
    if gaps:
        lines += ["", "The batch's truth itself against the simulator's (dry run only, last step): median %.1f cm, max "
                  "%.1f cm over %d episodes." % (100 * _q(gaps, 0.5), 100 * max(gaps), len(gaps))]
    lines += ["", "Per episode (final-position error, cm; `truth sigma`: the batch's own uncertainty of its truth):", "",
              "| Episode | Scenario | Steps | truth sigma | " + " | ".join(order) + " |",
              "| --- | --- | --- | --- | " + " | ".join("---" for _ in order) + " |"]
    for seed in sorted(errors["B0"]):
        b0 = errors["B0"][seed]
        cells = []
        for arm in order:
            r = errors.get(arm, {}).get(seed)
            cells.append(_cm(r["final_m"]) if r and r.get("complete") else "incomplete")
        lines.append("| %s | %s | %s | %s | %s |" % (b0["episode"], b0.get("scenario"), b0.get("steps"),
                                                    _cm(b0.get("truth_sigma_xy_m")), " | ".join(cells)))
    if index.get("excluded"):
        lines += ["", "Not replayed: " + "; ".join("%s (%s)" % (x["episode"], x["reason"]) for x in index["excluded"])]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- time and cost

# Measured in the pre-registered study's held-out sweep (data/main/runs/drift2/<arm>: run.json `started` to the last
# run.end `ended`, 1,976 steps over 30 seeds each; evidence/M3/M3.T19/README.md shows the arithmetic):
STUDY_RATES = {
    "claude-opus-5-5": {"usd_per_step": 0.0729, "wall_s_per_step": 2.71, "latency_s": 19.3, "workers": 8},
    "qwen38-flash-xhigh": {"usd_per_step": 0.0, "wall_s_per_step": 31.3, "latency_s": 236.2, "workers": 8},
    "gemma4-26b": {"usd_per_step": 0.0, "wall_s_per_step": 110.6, "latency_s": 1240.4, "workers": 16},
}


def estimate(index, rates=STUDY_RATES):
    """{arm: {steps, usd, hours_throughput, hours_longest_episode}}: cost from the study's US$ per step; time between
    the study's throughput (steps x wall seconds per step at its parallelism) and the longest episode replayed alone at
    the study's per-step latency (a lower bound when there are fewer episodes than workers)."""
    steps = [e["steps"] for e in index["episodes"]]
    out = {}
    for arm, r in rates.items():
        out[arm] = {"steps": sum(steps), "usd": sum(steps) * r["usd_per_step"],
                    "hours_throughput": sum(steps) * r["wall_s_per_step"] / 3600.0,
                    "hours_longest_episode": (max(steps) if steps else 0) * r["latency_s"] / 3600.0,
                    "workers_in_study": r["workers"]}
    return out
