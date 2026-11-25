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

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this module; made the end circle the primary truth.
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
    if end_map is None and not entry.get("end_fix"):
        # the end circle itself was interrupted (b2-real-03 ep02: a stall in it): there is no end-circle pose; the end
        # pose is the last step's truth, and the analysis leaves the "vs end circle" column empty for it
        tm = truth_rows[-1]["truth_map"]
        end_map, end_source = {k: tm[k] for k in ("x_m", "y_m", "theta_deg")}, LAST_STEP_TRUTH
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
LAST_STEP_TRUTH = "last step's truth (no end circle)"


# The coded procedure stopping itself (closed_loop: `error`, detail "driver stopped: ..."; the frozen B2 on a branch it
# does not implement, such as the dead end kinsim_room.make_b2_policy() handles). The harness writes that step as a
# fallback (the previous report dead-reckoned), the study's rule for a step without a valid report, and no move
# follows, so the log is complete to its last step and the end circle measured that step's pose. Converted, but
# flagged: the analysis lists such an episode apart from the ones that ended by DONE or the budget.
PROCEDURE_STOPPED = "procedure_stopped"


def procedure_stopped(entry):
    res = entry.get("result") or {}
    return res.get("ended_by") == "error" and str(res.get("detail") or "").startswith("driver stopped")


def finished(entry):
    """True when the episode ran to its own end (DONE, or the step budget, or the coded procedure stopping itself,
    which is flagged) with every step written: status "done", or status "halted" by something after the agent's last
    step (result complete): a check after the episode (car/batch.py checks the odometry over the episode after
    run_episode has returned), or a halt inside the end circle (a stall)."""
    res = entry.get("result") or {}
    if not res.get("complete") or (res.get("ended_by") not in END_NORMALLY and not procedure_stopped(entry)):
        return False
    return entry.get("status") in ("done", "halted")


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
        if procedure_stopped(e):
            note = "flagged %s: %s" % (PROCEDURE_STOPPED, (e.get("result") or {}).get("detail"))
            doc["real"]["note"] = note
        elif e.get("status") != "done":
            code = (e.get("halt") or {}).get("code") if isinstance(e.get("halt"), dict) else e.get("halt")
            if e.get("end_fix"):
                note = "completed; batch halted after the end by %s" % code
            else:
                note = "completed; end circle interrupted by %s" % code
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


# A later batch added to a set can need a sibling run folder per arm (runs/<arm>+<batch>): the runner refuses to
# resume a folder once its config tag changed, and the tag holds the hashes of tools/real_replay.py and this file.
# The parts of one arm may differ only in those two hashes; everything that shapes the agent's input must match.
CODE_SHAS = ("runner_sha12", "real_replay_sha12")
SAME_ACROSS_PARTS = ("provider_key", "provider_entry", "agent", "arm", "repeat", "max_steps", "sha12", "dv",
                     "observation_overlay", "obslog_schema", "runner", "prompt_file")


def _folders(spec):
    return [spec] if isinstance(spec, str) else list(spec)


def check_parts(folders):
    """[{folder, config, git_commit, runner_sha12, real_replay_sha12, seeds}] for one arm's run folders (run.json);
    ValueError when they differ in anything but the code hashes, or when a seed is in more than one of them."""
    parts, seen = [], {}
    for f in _folders(folders):
        with open(os.path.join(f, "run.json"), encoding="utf-8") as fh:
            head = json.load(fh)
        for seed in sorted(int(n[5:-6]) for n in os.listdir(f) if n.startswith("seed_") and n.endswith(".jsonl")):
            if seed in seen:
                raise ValueError("seed %d is in two run folders of one arm: %s and %s" % (seed, seen[seed], f))
            seen[seed] = f
        parts.append(dict({k: head.get(k) for k in ("config", "git_commit") + CODE_SHAS}, folder=f, head=head,
                          seeds=sorted(s for s, g in seen.items() if g == f)))
    for p in parts[1:]:
        diff = [k for k in SAME_ACROSS_PARTS if p["head"].get(k) != parts[0]["head"].get(k)]
        if diff:
            raise ValueError("%s and %s differ in %s (only %s may)" % (parts[0]["folder"], p["folder"], diff,
                                                                       ", ".join(CODE_SHAS)))
    for p in parts:
        del p["head"]
    return parts


def _arm_rows(folders, seed):
    rows = []
    for f in _folders(folders):
        path = os.path.join(f, "seed_%d.jsonl" % seed)
        if os.path.exists(path):
            if rows:
                raise ValueError("seed %d is in more than one run folder of %s" % (seed, folders))
            rows = _jsonl(path)
    return rows


# ---------------------------------------------------------------- the truths of the final pose
#
# On the slipping carpet the batch's step truth (the pose it tracks: odometry between tag fixes, PoseTracker) is
# overconfident: northward the car covers 0.67 to 0.78 of its counted distance, and in simulation the tracked truth's
# error reached a p95 of 0.10 to 0.13 m against a stated 5 to 6 cm (evidence/M3/M3.T12/batch-runner/truth-under-slip).
# The primary truth of an episode's final pose is therefore its end circle: a full circle of 8 to 14 tags, solved on its
# own geometry, at the very pose of the agent's last report when the episode ended by DONE (no move follows). The last
# step's tracked truth stays as a secondary, tracker-dependent truth, and so does the same truth recomputed offline with
# a slip-aware tracker (tools/recompute_truth.py).

RECOMPUTE_TOOL = "tools/recompute_truth.py"


def end_circle_truth(entry):
    """(truth, None) with the end circle's own pose (end_fix.pose, the pose where the circle began) in the episode's
    map frame, its rms, tag count and sigmas; or (None, why) when the episode has no end circle at its final report."""
    ef = entry.get("end_fix") or {}
    res = entry.get("result") or {}
    halt = entry.get("halt")
    code = halt.get("code") if isinstance(halt, dict) else halt
    if not ef:
        return None, ("no end circle: the batch halted in it (%s)" % code) if entry.get("status") == "halted" \
            else "no end circle"
    if not ef.get("ok") or not ef.get("pose") or ef.get("tracked_only"):
        return None, "the end circle gave no fix (%s)" % (ef.get("why") or "tracked pose only")
    if ef.get("blended_with_tracked_pose"):
        return None, "the end circle's fix was blended with the tracked pose (not independent of the tracker)"
    if res.get("ended_by") != "DONE" and not procedure_stopped(entry):
        return None, "ended by %s: the last move ran after the agent's last report" % res.get("ended_by")
    return {"pose": to_map_pose(entry["start_pose_world"], ef["pose"]), "rms_m": ef.get("rms_m"),
            "n_tags": ef.get("n_tags"), "sigma_xy_m": ef.get("sigma_xy_m"),
            "sigma_theta_deg": ef.get("sigma_theta_deg")}, None


def independent_truths(docs, batches_root, recompute=None):
    """{seed: {end_circle, end_circle_why, recomputed, recomputed_why}} from the batches' manifests under
    batches_root (the obslogs, which are the agent's input, stay as they are). recompute(batch_dir, entry, n_rows) ->
    {pose, sigma_xy_m, logged_pose, replay_halts}: the recomputed and the logged truth at row n_rows - 1 (the last
    record's row), map frame; the logged one must be the record's truth, or the rows did not line up."""
    manifests, out = {}, {}
    for seed, d in sorted(docs.items()):
        real = d.get("real") or {}
        name, ep = real.get("batch"), real.get("episode")
        t = {"end_circle": None, "end_circle_why": None, "recomputed": None, "recomputed_why": None,
             "logged_tracker": None}
        bdir = os.path.join(batches_root, name) if name else None
        if name and name not in manifests:
            path = os.path.join(bdir, "manifest.json")
            manifests[name] = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None
        if manifests.get(name):
            # the tracker the batch ran (its step truth): PoseTracker's slip-aware odometry sigma, 0 before b2-real-05
            params = manifests[name].get("params") or {}
            t["logged_tracker"] = {"slip_sigma_per_m": float(params.get("odometry_slip_sigma_per_m") or 0.0),
                                   "slip_north_per_m": float(params.get("odometry_slip_north_per_m") or 0.0)}
        entry = next((e for e in (manifests.get(name) or {}).get("episodes", []) if e.get("id") == ep), None)
        if entry is None:
            t["end_circle_why"] = t["recomputed_why"] = "no manifest entry for %s %s under %s" % (name, ep, batches_root)
        else:
            t["end_circle"], t["end_circle_why"] = end_circle_truth(entry)
            if procedure_stopped(entry):
                t["flag"] = PROCEDURE_STOPPED
            if t["end_circle"]:
                # how far the batch's logged (tracked) truth at the last step sits from the circle
                last, ec = d["records"][-1]["truth"], t["end_circle"]["pose"]
                t["end_circle"]["logged_truth_off_m"] = math.hypot(last["x_m"] - ec["x_m"], last["y_m"] - ec["y_m"])
                t["end_circle"]["logged_truth_off_deg"] = wrap_deg(last["theta_deg"] - ec["theta_deg"])
            if recompute is None:
                t["recomputed_why"] = "not recomputed"
            else:
                rec = recompute(bdir, entry, len(d["records"]))
                last = d["records"][-1]["truth"]
                off = math.hypot(rec["logged_pose"]["x_m"] - last["x_m"], rec["logged_pose"]["y_m"] - last["y_m"])
                if off > 0.001:
                    raise ValueError("seed %s: the recomputation's row %d is not the record's (logged truths %.3f m "
                                     "apart)" % (seed, len(d["records"]) - 1, off))
                t["recomputed"] = {k: rec[k] for k in ("pose", "sigma_xy_m", "replay_halts")}
        out[seed] = t
    return out


def final_errors(docs, runs, truths=None):
    """{arm: {seed: row}} with the final-position and heading error of each episode against the batch's tracked truth
    at the last step (final_m, final_deg), and with `truths` (independent_truths) against the end circle
    (vs_end_circle_m, vs_end_circle_deg) and the recomputed last-step truth (vs_recomputed_m); against the simulator's
    truth when the log has it (a dry run).
    `runs` = {arm label: run folder, or a list of an arm's run folders}. B0 and B2 come from the logs themselves. An arm's episode counts only when every
    step of it was replayed."""
    out = {"B0": {}, "B2": {}}
    for arm in runs:
        out[arm] = {}
    for seed, d in sorted(docs.items()):
        recs = d["records"]
        last = recs[-1]
        truth = last["truth"]
        ests = {"B0": ks.dead_reckoning(recs)[-1], "B2": last.get("b2_estimate") or (last.get("report") or {}).get("pose")}
        for arm, folders in runs.items():
            rows = _arm_rows(folders, seed)
            ests[arm] = rows[-1]["estimate_pose"] if len(rows) == len(recs) else None
        if last.get("truth_sim"):
            out.setdefault("_truth_check", {})[seed] = {"truth_last": truth, "truth_sim_last": last["truth_sim"]}
        for arm, est in ests.items():
            if est is None:
                out[arm][seed] = {"episode": d["real"]["episode"], "complete": False}
                continue
            e = _err(est, truth)
            row = {"episode": d["real"]["episode"], "batch": d["real"].get("batch"), "scenario": d["real"]["scenario"],
                   "steps": len(recs),
                   "complete": True, "final_m": e["m"], "final_deg": e["deg"],
                   "truth_sigma_xy_m": truth.get("sigma_xy_m"), "truth_is_a_fix": truth.get("fix"),
                   "estimate": est}
            t = (truths or {}).get(seed) or {}
            if t.get("flag"):
                row["flag"] = t["flag"]
            if t.get("end_circle"):
                ec = _err(est, t["end_circle"]["pose"])
                row["vs_end_circle_m"], row["vs_end_circle_deg"] = ec["m"], ec["deg"]
            if t.get("recomputed"):
                row["vs_recomputed_m"] = _err(est, t["recomputed"]["pose"])["m"]
            if last.get("truth_sim"):
                row["vs_sim_truth_m"] = _err(est, last["truth_sim"])["m"]
            out[arm][seed] = row
    return out


def run_stats(docs, runs):
    """{arm: {steps, expected_steps, valid, fallbacks, repaired, errors, move_calls, cost_usd, mean_s, p95_s}} from
    the run folders' rows."""
    out = {}
    for arm, folders in runs.items():
        rows = []
        for seed in docs:
            rows += _arm_rows(folders, seed)
        secs = sorted(float(r.get("seconds") or 0.0) for r in rows)
        out[arm] = {"steps": len(rows), "expected_steps": sum(len(d["records"]) for d in docs.values()),
                    "valid": sum(1 for r in rows if (r.get("checks") or {}).get("valid")),
                    "fallbacks": sum(1 for r in rows if r.get("fallback")),
                    "repaired": sum(1 for r in rows if (r.get("checks") or {}).get("repaired_chars")),
                    "errors": sum(1 for r in rows if r.get("error")),
                    "move_calls": sum(1 for r in rows for c in r.get("calls") or [] if c.get("tool") == "move"),
                    "cost_usd": sum(float(r.get("cost_usd") or 0.0) for r in rows),
                    "mean_s": statistics.fmean(secs) if secs else None,
                    "p95_s": secs[max(0, math.ceil(0.95 * len(secs)) - 1)] if secs else None}
    return out


def _q(values, q):
    s = sorted(values)
    if not s:
        return None
    pos = (len(s) - 1) * q
    lo, hi = int(math.floor(pos)), int(math.ceil(pos))
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def _dist(m, deg=None):
    return {"n": len(m), "median_m": _q(m, 0.5), "q1_m": _q(m, 0.25), "q3_m": _q(m, 0.75),
            "min_m": min(m) if m else None, "max_m": max(m) if m else None,
            "mean_m": statistics.fmean(m) if m else None, "median_deg": _q(deg or [], 0.5)}


def summarize(errors):
    """{arm: {n, n_incomplete, n_flagged, end_circle, last_step, recomputed, median_vs_sim_truth_m}}; each truth's
    entry is {n, median_m, q1_m, q3_m, min_m, max_m, mean_m, median_deg} over the complete episodes that have that
    truth and are not flagged (a flagged episode, such as one the coded procedure stopped, is listed apart).
    end_circle is the primary truth; last_step (with median_truth_sigma_m, the tracker's stated sigma) and recomputed
    depend on the tracker."""
    out = {}
    for arm, by_seed in errors.items():
        if arm.startswith("_"):
            continue
        rows = [r for r in by_seed.values() if r.get("complete") and not r.get("flag")]
        ec = [r for r in rows if "vs_end_circle_m" in r]
        last = _dist([r["final_m"] for r in rows], [r["final_deg"] for r in rows])
        last["median_truth_sigma_m"] = _q([r["truth_sigma_xy_m"] for r in rows if r.get("truth_sigma_xy_m") is not None], 0.5)
        out[arm] = {"n": len(rows), "n_incomplete": sum(1 for r in by_seed.values() if not r.get("complete")),
                    "n_flagged": sum(1 for r in by_seed.values() if r.get("complete") and r.get("flag")),
                    "end_circle": _dist([r["vs_end_circle_m"] for r in ec], [r["vs_end_circle_deg"] for r in ec]),
                    "last_step": last,
                    "recomputed": _dist([r["vs_recomputed_m"] for r in rows if "vs_recomputed_m" in r]),
                    "median_vs_sim_truth_m": _q([r["vs_sim_truth_m"] for r in rows if "vs_sim_truth_m" in r], 0.5)}
    return out


def _cm(v):
    return "" if v is None else "%.1f" % (100 * v)


def _deg(v):
    return "" if v is None else "%.1f" % v


def _dist_row(cells, d):
    return "| %s | %d | %s | %s to %s | %s | %s | %s |" % (" | ".join(cells), d["n"], _cm(d["median_m"]), _cm(d["q1_m"]),
                                                        _cm(d["q3_m"]), _cm(d["min_m"]), _cm(d["max_m"]),
                                                        _deg(d["median_deg"]))


def result_markdown(title, index, errors, summary, order, stats=None, truths=None, truth_settings=None):
    truths, ts = truths or {}, truth_settings or {}
    seeds = sorted(errors["B0"])
    lines = ["# %s" % title, "",
             "Batch `%s` (config %s, real car: %s); %d episodes, %d steps; world `%s` (sha12 %s); %s." % (
                 index["batch"], index.get("batch_config"), index.get("real_car"), len(index["episodes"]),
                 index["steps"], index["world_file"], index["world_sha12"], index.get("dv_file")), "",
             "**Exploratory, not pre-registered.** The pre-registration reports the real logs descriptively, as the "
             "sim-to-real gap (evidence/M4/M4.T1/prereg.md section 6), and the end-circle value below was chosen after "
             "the data; these are descriptive tables, with no test and no verdict.", "",
             "## Final-position error against the end circle (the truth used first; exploratory)", "",
             "The end circle is the full circle the batch turns where the episode ended: 8 to 14 tags solved on their "
             "own geometry, not through the tracker. When the episode ended by DONE no move followed the agent's last "
             "report, so the circle measured that very pose (the manifest's `end_fix.pose`, in the map frame of the "
             "episode's start). n counts the episodes that have one; cm, heading in degrees. The heading column is "
             "not a result: the circle solves its starting heading from views placed by the odometry's own turns, "
             "which slip too; `logged truth off` below shows how far the batch's tracked truth sits from the circle, "
             "in position and heading.", "",
             "| Arm | n | median | IQR | min | max | median heading error (deg) |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for arm in order:
        if arm in summary:
            lines.append(_dist_row([arm], summary[arm]["end_circle"]))
    flagged = [s for s in seeds if (truths.get(s) or {}).get("flag")]
    with_ec = [s for s in seeds if (truths.get(s) or {}).get("end_circle") and s not in flagged]

    def ec_table(chosen):
        out = ["| Episode | Scenario | Steps | end circle | logged truth off | " + " | ".join(order) + " |",
               "| --- | --- | --- | --- | --- | " + " | ".join("---" for _ in order) + " |"]
        for seed in chosen:
            b0, ec = errors["B0"][seed], truths[seed]["end_circle"]
            cells = []
            for arm in order:
                r = errors.get(arm, {}).get(seed)
                cells.append(_cm(r.get("vs_end_circle_m")) if r and r.get("complete") else "incomplete")
            off = "%s, %+.1f deg" % (_cm(ec["logged_truth_off_m"]), ec["logged_truth_off_deg"]) \
                if ec.get("logged_truth_off_m") is not None else ""
            out.append("| %s %s | %s | %s | %s tags, rms %s, sigma %s | %s | %s |" % (
                b0.get("batch") or "", b0["episode"], b0.get("scenario"), b0.get("steps"), ec.get("n_tags"),
                _cm(ec.get("rms_m")), _cm(ec.get("sigma_xy_m")), off, " | ".join(cells)))
        return out

    lines += ["", "Per episode (cm). `end circle`: tags, rms of its tag residuals, its stated sigma; `logged truth off`: "
              "the batch's tracked truth at the last step minus the circle (cm, degrees):", ""] + ec_table(with_ec)
    if flagged:
        lines += ["", "Listed apart, not in n above: episodes the coded procedure stopped itself (the frozen B2 on a "
                  "branch it does not implement; the harness wrote the stopping step as the study's fallback, the "
                  "previous report dead-reckoned, and no move followed, so the end circle measured that step's pose):",
                  ""]
        lines += ec_table([s for s in flagged if truths[s].get("end_circle")])
        for seed in flagged:
            if not truths[seed].get("end_circle"):
                b0 = errors["B0"][seed]
                lines.append("- %s %s: %s." % (b0.get("batch") or "", b0["episode"], truths[seed].get("end_circle_why")))
    without = [s for s in seeds if s not in with_ec and s not in flagged]
    if without:
        lines += ["", "Without an end circle at the final report (only the tracker-dependent truths below):"]
        for seed in without:
            b0 = errors["B0"][seed]
            lines.append("- %s %s: %s." % (b0.get("batch") or "", b0["episode"],
                                           (truths.get(seed) or {}).get("end_circle_why") or "no end circle"))
    rec_label = "recomputed with `%s` (slip sigma %.2f + %.2f x north per metre of forward move)" % (
        ts.get("recompute_tool", RECOMPUTE_TOOL), ts.get("slip_sigma") or 0.0, ts.get("slip_north") or 0.0) \
        if ts.get("recomputed") else None
    trackers = {}
    for seed in seeds:
        lt = (truths.get(seed) or {}).get("logged_tracker")
        if lt is not None:
            trackers.setdefault((lt["slip_sigma_per_m"], lt["slip_north_per_m"]), []).append(errors["B0"][seed].get("batch"))
    tracker_note = "; ".join("%s: slip sigma %.2f + %.2f x north per metre" % (
        ", ".join(sorted(set(b for b in batches if b))), a, n) for (a, n), batches in sorted(trackers.items()))
    lines += ["", "## Against the last step's truth (tracker-dependent; exploratory)", "",
              "The batch's own truth at the last step: the pose it tracks, odometry between tag fixes blended by "
              "inverse variance (PoseTracker: 5 %% odometry sigma, plus the slip sigma the batch ran with), with its "
              "stated sigma. Without a slip sigma it is overconfident northward on this carpet. The batches' trackers: "
              "%s. %s" % (tracker_note or "not known (no manifests)",
                          "The second table recomputes it offline from the logged rows, %s." % rec_label if rec_label
                          else "Not recomputed here."), "",
              "| Truth | Arm | n | median | IQR | min | max | median heading error (deg) |",
              "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for arm in order:
        if arm in summary:
            lines.append(_dist_row(["logged", arm], summary[arm]["last_step"]))
    if rec_label:
        for arm in order:
            if arm in summary:
                lines.append(_dist_row(["recomputed", arm], summary[arm]["recomputed"]))
    lines += ["", "Per episode (cm; each cell: against the logged truth%s):" % (
        " / against the recomputed truth" if rec_label else ""), "",
              "| Episode | logged sigma%s | " % (" / recomputed sigma" if rec_label else "") + " | ".join(order) + " |",
              "| --- | --- | " + " | ".join("---" for _ in order) + " |"]
    for seed in seeds:
        b0 = errors["B0"][seed]
        rec = (truths.get(seed) or {}).get("recomputed")
        cells = []
        for arm in order:
            r = errors.get(arm, {}).get(seed)
            if not (r and r.get("complete")):
                cells.append("incomplete")
            else:
                cells.append(_cm(r["final_m"]) + ((" / " + _cm(r.get("vs_recomputed_m"))) if rec_label else ""))
        lines.append("| %s %s%s | %s%s | %s |" % (b0.get("batch") or "", b0["episode"],
                                                " (flagged: %s)" % truths[seed]["flag"] if seed in flagged else "",
                                                _cm(b0.get("truth_sigma_xy_m")),
                                              (" / " + _cm(rec["sigma_xy_m"]) if rec else " / ") if rec_label else "",
                                              " | ".join(cells)))
    sims = [summary[a]["median_vs_sim_truth_m"] for a in order if a in summary and summary[a]["median_vs_sim_truth_m"] is not None]
    if sims:
        lines += ["", "Against the simulator's own pose (dry run only), median: " + "; ".join(
            "%s %s" % (a, _cm(summary[a]["median_vs_sim_truth_m"])) for a in order
            if a in summary and summary[a]["median_vs_sim_truth_m"] is not None) + " cm."]
    gaps = [math.hypot(d_t["x_m"] - d_s["x_m"], d_t["y_m"] - d_s["y_m"]) for d_t, d_s in
            ((r["truth_last"], r["truth_sim_last"]) for r in errors.get("_truth_check", {}).values())]
    if gaps:
        lines += ["", "The batch's truth itself against the simulator's (dry run only, last step): median %.1f cm, max "
                  "%.1f cm over %d episodes." % (100 * _q(gaps, 0.5), 100 * max(gaps), len(gaps))]
    if stats:
        lines += ["", "## Runs", "", "Replayed steps (of the logs' steps), valid reports, harness fallbacks, repaired "
                  "reports, step errors, `move` calls (the replay rule wants 0), cost, seconds per step.", "",
                  "| Arm | steps | valid | fallbacks | repaired | errors | move calls | cost (US$) | mean s/step | p95 s/step |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for arm, st in stats.items():
            lines.append("| %s | %d of %d | %d | %d | %d | %d | %d | %.2f | %s | %s |" % (
                arm, st["steps"], st["expected_steps"], st["valid"], st["fallbacks"], st["repaired"], st["errors"],
                st["move_calls"], st["cost_usd"], "" if st["mean_s"] is None else "%.1f" % st["mean_s"],
                "" if st["p95_s"] is None else "%.1f" % st["p95_s"]))
    if index.get("excluded"):
        lines += ["", "Not replayed: " + "; ".join("%s %s (%s)" % (x.get("batch", ""), x["episode"], x["reason"])
                                                   for x in index["excluded"])]
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
