"""Tests of the real-log replay (beaconmind/real_replay.py, tools/real_replay.py).

A small batch folder is made in tmp_path the way car/batch.py lays it out: the closed-loop harness drives the coded
procedure (B2) in the room simulator for a few steps, and truth.jsonl and manifest.json are written beside the rows.
No network: model arms are the free procedure stand-in or the test suite's scripted Anthropic client.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote these tests.
"""
import importlib.util
import json
import math
import os
import pathlib

import pytest

import beaconmind
from beaconmind.envs import kinsim_lite as ks
from beaconmind.harness import closed_loop as cl
from beaconmind.harness import replay as rp
from beaconmind import real_replay as rr

ROOT = pathlib.Path(beaconmind.course_root())
WORLD = ROOT / "configs" / "arenas" / "real-room.json"
START = {"x_m": 2.5, "y_m": 1.5, "theta_deg": 90.0}

spec = importlib.util.spec_from_file_location("real_replay_tool", ROOT / "tools" / "real_replay.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def _episode(ep_dir, seed, steps, status_error_at=None):
    """Closed-loop rows of B2 in the room simulator and the matching truth.jsonl (truth = the simulator's pose)."""
    os.makedirs(ep_dir, exist_ok=True)
    env = cl.room_env(str(WORLD), start_pose=START, max_range_m=3.0)
    path = os.path.join(ep_dir, "seed_%d.jsonl" % seed)
    cl.run_episode(cl.B2Driver(), "SYSTEM", env, seed, path, rp.Budget(float("inf")), steps, lambda m: None, config="t")
    rows = [json.loads(line) for line in open(path)]
    with open(path, "w") as fh:
        for r in rows:
            r["truth"] = dict(r["truth"], source="tag_fix", fix=True, sigma_xy_m=0.05, sigma_theta_deg=2.0)
            if r["step"] == status_error_at:
                r["observation"]["status"], r["observation"]["error"] = "error", "camera stale"
            fh.write(json.dumps(r) + "\n")
    with open(os.path.join(ep_dir, "truth.jsonl"), "w") as fh:
        for k, r in enumerate(rows):
            fh.write(json.dumps({"row": k, "truth_map": r["truth"], "no_fix": False, "view_fix": {"kind": "position"}})
                     + "\n")
    return rows


@pytest.fixture
def batch(tmp_path):
    b = tmp_path / "batches" / "b-test"
    rows1 = _episode(str(b / "episodes" / "ep01-a1"), 1, 6, status_error_at=3)
    _episode(str(b / "episodes" / "ep02-a1"), 2, 4)
    end = rows1[-1]["truth"]
    man = {"schema": "bm.car_batch/1", "config": "c0ffee", "real_car": False, "status": "complete", "halt": None,
           "params": {"world_path": str(WORLD), "dv_file": "configs/dv-real.json", "max_range_m": 3.0},
           "episodes": [
               {"index": 0, "id": "ep01-a1", "attempt": 1, "scenario": "S1", "policy": "b2", "seed": 1,
                "status": "done", "result": {"complete": True, "ended_by": "budget", "steps": 6},
                "start_pose_world": START, "end_pose_map": {"x_m": end["x_m"] + 0.01, "y_m": end["y_m"],
                                                           "theta_deg": end["theta_deg"]},
                "end_fix": {"ok": True, "sigma_xy_m": 0.02}},
               {"index": 1, "id": "ep02-a1", "attempt": 1, "scenario": "S2", "policy": "b2", "seed": 2,
                "status": "halted", "result": {"complete": False}, "halt": "no_fix", "start_pose_world": START},
               {"index": 1, "id": "ep02-a2", "attempt": 2, "scenario": "S2", "policy": "b2", "seed": 2,
                "status": "done", "result": {"complete": True, "ended_by": "budget", "steps": 4},
                "start_pose_world": START}]}
    os.rename(b / "episodes" / "ep02-a1", b / "episodes" / "ep02-a2")
    (b / "manifest.json").write_text(json.dumps(man))
    return b


def _as_real_folder(batch):
    """Make the fixture look like the first real batch b2-real-01 (2026-11-25): real car, detections without a true tag
    (`_tag` null), observations with source "real", one step's odometry flagged slip_suspected, and episode 1 halted
    by a check after its end, so the manifest has status "halted", no end_pose_map and no final_pose_error, but a
    complete result and the end circle's fix with its pose_now."""
    path = batch / "episodes" / "ep01-a1" / "seed_1.jsonl"
    rows = [json.loads(line) for line in open(path)]
    for r in rows:
        for d in r["raw"]["detections"]:
            d["_tag"] = None
        r["observation"]["source"] = "real"
        if r["step"] == 2 and r["observation"]["odometry"]:
            r["observation"]["odometry"]["quality"] = "slip_suspected"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    man = json.loads((batch / "manifest.json").read_text())
    man.update(real_car=True, status="halted", halt={"code": "odometry_scale", "detail": "after the episode"})
    e = man["episodes"][0]
    end_world = {"x_m": 2.31, "y_m": 1.62, "theta_deg": 130.0}
    e.update(status="halted", halt={"code": "odometry_scale", "detail": "after the episode"},
             result={"complete": True, "ended_by": "DONE", "detail": "decision", "steps": 6},
             end_fix={"ok": True, "pose": {"x_m": 2.3, "y_m": 1.6, "theta_deg": 129.0}, "pose_now": end_world,
                      "sigma_xy_m": 0.024})
    for k in ("end_pose_map", "end_pose_world", "final_pose_error"):
        e.pop(k, None)
    (batch / "manifest.json").write_text(json.dumps(man))
    return end_world


def test_an_episode_halted_only_after_its_end_is_converted(batch, tmp_path):
    end_world = _as_real_folder(batch)
    idx = rr.convert_batch(str(batch), str(tmp_path / "o"))
    ep = [e for e in idx["episodes"] if e["episode"] == "ep01-a1"]
    assert ep and ep[0]["note"] == "completed; batch halted after the end by odometry_scale"
    assert ep[0]["end_pose_source"] == "end_fix.pose_now" and idx["real_car"] is True
    doc = json.loads((tmp_path / "o" / "seed_1.json").read_text())
    assert doc["real"]["end_pose_map"] == pytest.approx(rr.to_map_pose(START, end_world))
    assert all(d["_tag"] is None for r in doc["records"] for d in r["raw"]["detections"])
    assert doc["records"][2]["observation_real"]["odometry_quality"] == "slip_suspected"
    # the free arm still reproduces B2 on it, and sees the real observation's flags
    out = tmp_path / "runs"
    assert tool.cmd_run(_args(provider="procedure", obslogs=str(tmp_path / "o"), out=str(out))) == 0
    rows = [json.loads(line) for line in open(out / "seed_1.jsonl")]
    assert [r["estimate_pose"] for r in rows] == [rec["b2_estimate"] for rec in doc["records"]]
    assert rows[2]["observation"]["odometry"]["quality"] == "slip_suspected" and rows[2]["observation"]["source"] == "real"
    # the end circle is the manifest's end_fix.pose (where the circle began), not the pose after it (pose_now)
    truths = rr.independent_truths({1: doc}, str(batch.parent))
    circle = rr.to_map_pose(START, {"x_m": 2.3, "y_m": 1.6, "theta_deg": 129.0})
    assert truths[1]["end_circle"]["pose"] == pytest.approx(circle) and truths[1]["end_circle"]["sigma_xy_m"] == 0.024
    err = rr.final_errors({1: doc}, {}, truths)
    b2 = doc["records"][-1]["b2_estimate"]
    assert err["B2"][1]["vs_end_circle_m"] == pytest.approx(math.hypot(b2["x_m"] - circle["x_m"], b2["y_m"] - circle["y_m"]))


def test_the_end_circle_is_a_truth_only_for_the_pose_it_measured():
    entry = {"start_pose_world": START, "status": "done", "result": {"complete": True, "ended_by": "DONE"},
             "end_fix": {"ok": True, "pose": dict(START), "rms_m": 0.02, "n_tags": 9, "sigma_xy_m": 0.024}}
    t, why = rr.end_circle_truth(entry)
    assert why is None and t["pose"] == pytest.approx({"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}) and t["n_tags"] == 9
    assert rr.end_circle_truth(dict(entry, result={"complete": True, "ended_by": "budget"}))[1].startswith("ended by budget")
    assert rr.end_circle_truth(dict(entry, end_fix=dict(entry["end_fix"], blended_with_tracked_pose=True)))[0] is None
    assert rr.end_circle_truth(dict(entry, end_fix={"ok": False, "why": "poorly conditioned"}))[0] is None
    assert rr.end_circle_truth(dict(entry, end_fix={"ok": True, "pose_now": dict(START), "tracked_only": True}))[0] is None
    assert "halted in it (stall)" in rr.end_circle_truth(dict(entry, end_fix=None, status="halted",
                                                              halt={"code": "stall"}))[1]


def test_an_episode_halted_before_its_end_is_not_converted(batch, tmp_path):
    _as_real_folder(batch)
    man = json.loads((batch / "manifest.json").read_text())
    man["episodes"][0]["result"] = {"complete": False, "ended_by": "halt", "detail": "odometry_scale"}
    (batch / "manifest.json").write_text(json.dumps(man))
    idx = rr.convert_batch(str(batch), str(tmp_path / "o"))
    assert "ep01-a1" not in [e["episode"] for e in idx["episodes"]]
    assert [x for x in idx["excluded"] if x["episode"] == "ep01-a1"][0]["reason"].startswith("did not end normally")


def test_convert_keeps_truth_b2_and_the_real_observation(batch, tmp_path):
    out = tmp_path / "obslogs"
    idx = rr.convert_batch(str(batch), str(out))
    assert [e["episode"] for e in idx["episodes"]] == ["ep01-a1", "ep02-a2"]
    assert [x["episode"] for x in idx["excluded"]] == ["ep02-a1"] and "did not end normally" in idx["excluded"][0]["reason"]
    assert idx["steps"] == 10 and idx["world_sha12"] == rr.sha12_bytes(WORLD.read_bytes())
    doc = json.loads((out / "seed_1.json").read_text())
    assert doc["schema"] == rr.SCHEMA and [r["step"] for r in doc["records"]] == list(range(6))
    rows = [json.loads(line) for line in open(batch / "episodes" / "ep01-a1" / "seed_1.jsonl")]
    assert doc["records"][2]["truth"] == rows[2]["truth"] and doc["records"][2]["truth"]["sigma_xy_m"] == 0.05
    assert doc["records"][2]["b2_estimate"] == rows[2]["estimate_pose"]
    assert doc["records"][3]["observation_real"]["status"] == "error"
    # the tags are in the episode's map frame: the start pose is the origin
    from beaconmind.envs import kinsim_room as kr
    t0 = kr.load_world(str(WORLD))["tags"][0]
    mx, my = kr.to_map(START, t0["x_m"], t0["y_m"])
    assert any(abs(t["x_m"] - mx) < 1e-6 and abs(t["y_m"] - my) < 1e-6 for t in doc["world"])


def test_truth_rows_must_match_the_steps(batch, tmp_path):
    tr = batch / "episodes" / "ep01-a1" / "truth.jsonl"
    lines = tr.read_text().splitlines()
    tr.write_text("\n".join(lines[:-2]) + "\n")                  # two rows short: refused
    idx = rr.convert_batch(str(batch), str(tmp_path / "o1"))
    assert "ep01-a1" in [x["episode"] for x in idx["excluded"]]
    tr.write_text("\n".join(lines) + "\n" + json.dumps(dict(json.loads(lines[-1]), row=6)) + "\n")
    idx = rr.convert_batch(str(batch), str(tmp_path / "o2"))  # one more row after a last executed move: accepted
    assert "ep01-a1" in [e["episode"] for e in idx["episodes"]]


def test_the_real_observation_reaches_the_step_message(batch, tmp_path):
    rr.convert_batch(str(batch), str(tmp_path / "o"))
    _, docs = rr.load_obslogs(str(tmp_path / "o"))
    raw = docs[1]["records"][3]["raw"]
    counters = {"odometer_m": 0.0, "travel_since_fix_m": 0.0, "turns_since_fix": 0}
    orig = ks.as_observation
    with rr.real_observations(list(docs.values())):
        obs = ks.as_observation(1, raw, counters)
        assert obs["status"] == "error" and obs["error"] == "camera stale" and obs["source"] == "sim"
    assert ks.as_observation is orig
    assert ks.as_observation(1, raw, counters)["status"] == "ok"


def _args(**kw):
    a = tool.parser().parse_args(["run", "--provider", kw.pop("provider"), "--obslogs", kw.pop("obslogs"),
                                  "--out", kw.pop("out"), "--cap-usd", str(kw.pop("cap", 0))] + kw.pop("extra", []))
    return a


def test_the_free_stand_in_reproduces_b2_through_the_runner(batch, tmp_path):
    rr.convert_batch(str(batch), str(tmp_path / "o"))
    out = tmp_path / "runs" / "procedure"
    code = tool.cmd_run(_args(provider="procedure", obslogs=str(tmp_path / "o"), out=str(out)))
    assert code == 0
    run = json.loads((out / "run.json").read_text())
    assert run["dv"]["file"] == "configs/dv-real.json" and run["dv"]["sha12"] and not run["dv"]["frozen"]
    assert run["prompt_file"] == "robot_system_prompt_v3.3-room.txt" and run["observation_overlay"]
    _, docs = rr.load_obslogs(str(tmp_path / "o"))
    for seed, d in docs.items():
        rows = [json.loads(line) for line in open(out / ("seed_%d.jsonl" % seed))]
        assert len(rows) == len(d["records"])
        assert [r["estimate_pose"] for r in rows] == [rec["b2_estimate"] for rec in d["records"]]
        assert not any(c["tool"] == "move" for r in rows for c in r["calls"])
    rows = [json.loads(line) for line in open(out / "seed_1.jsonl")]
    assert rows[3]["observation"]["status"] == "error"
    # a second run into the same folder needs a resume reason
    with pytest.raises(SystemExit):
        tool.cmd_run(_args(provider="procedure", obslogs=str(tmp_path / "o"), out=str(out)))


def test_prompt_and_design_values_must_agree(batch, tmp_path):
    rr.convert_batch(str(batch), str(tmp_path / "o"))
    assert tool.prompt_range_limit("... rejected if quality < 0.5, range_m > 3.0, or ...") == 3.0
    with pytest.raises(SystemExit):        # the room prompt (3.0 m) with the frozen design values (2.0 m)
        tool.cmd_run(_args(provider="procedure", obslogs=str(tmp_path / "o"), out=str(tmp_path / "r"),
                           extra=["--dv", "frozen"]))


class _AlwaysNone(dict):
    def get(self, key, default=None):
        return {"decision": "NONE"}


def test_a_scripted_anthropic_arm_runs_with_its_cost_and_cap(batch, tmp_path):
    pytest.importorskip("anthropic")
    from beaconmind.harness.providers import anthropic_messages as am
    from test_closed_loop import ScriptedModel                   # the suite's fake Anthropic client (no network)
    rr.convert_batch(str(batch), str(tmp_path / "o"))
    out = tmp_path / "runs" / "opus"
    agent = am.AnthropicAgent(ScriptedModel(_AlwaysNone()), "claude-opus-5-5")
    code = tool.cmd_run(_args(provider="claude-opus-5-5", obslogs=str(tmp_path / "o"), out=str(out), cap=0.05,
                              extra=["--workers", "1"]), agent=agent)
    assert code == 2                                             # the spend cap stopped it
    spent = rp.spent_in(out / "spend.jsonl")
    assert 0.05 <= spent < 0.2
    code = tool.cmd_run(_args(provider="claude-opus-5-5", obslogs=str(tmp_path / "o"), out=str(out), cap=50,
                              extra=["--resume-reason", "test: raise the cap"]), agent=agent)
    assert code == 0
    run = json.loads((out / "run.json").read_text())
    assert run["provider_key"] == "claude-opus-5-5" and run["dv"]["sha12"] and run["agent"]["provider"] == "anthropic_messages"
    rows = {s: [json.loads(line) for line in open(out / ("seed_%d.jsonl" % s))] for s in (1, 2)}
    assert [len(rows[1]), len(rows[2])] == [6, 4]
    assert all(r["cost_usd"] > 0 for rs in rows.values() for r in rs) and all(r["checks"]["valid"] for r in rows[1])
    assert rows[1][3]["observation"]["status"] == "error"


def test_final_errors_and_summary_by_hand(tmp_path):
    truth = {"x_m": 1.0, "y_m": 0.0, "theta_deg": 0.0, "sigma_xy_m": 0.05, "fix": True}
    recs = [{"step": 0, "raw": {"odometry": None}, "truth": dict(truth, x_m=0.0), "b2_estimate": {"x_m": 0, "y_m": 0, "theta_deg": 0}},
            {"step": 1, "raw": {"odometry": {"forward_m": 0.97, "left_m": 0.0, "dtheta_deg": 0.0}}, "truth": truth,
             "b2_estimate": {"x_m": 1.03, "y_m": 0.04, "theta_deg": 2.0}}]
    docs = {1: {"records": recs, "real": {"episode": "ep01-a1", "scenario": "S1"}}}
    truths = {1: {"end_circle": {"pose": {"x_m": 1.0, "y_m": 0.01, "theta_deg": 1.0}},
                  "recomputed": {"pose": {"x_m": 0.98, "y_m": 0.0, "theta_deg": 0.0}, "sigma_xy_m": 0.1}}}
    run = tmp_path / "arm"
    run.mkdir()
    (run / "seed_1.jsonl").write_text("".join(json.dumps({"estimate_pose": p}) + "\n" for p in (
        {"x_m": 0, "y_m": 0, "theta_deg": 0}, {"x_m": 0.94, "y_m": 0.08, "theta_deg": -3.0})))
    err = rr.final_errors(docs, {"arm": str(run)}, truths)
    assert err["B0"][1]["final_m"] == pytest.approx(0.03)
    assert err["B2"][1]["final_m"] == pytest.approx(0.05) and err["B2"][1]["final_deg"] == pytest.approx(2.0)
    assert err["arm"][1]["final_m"] == pytest.approx(0.1)
    assert err["arm"][1]["vs_end_circle_m"] == pytest.approx(0.0921954, abs=1e-6) and err["arm"][1]["vs_end_circle_deg"] == pytest.approx(4.0)
    assert err["B2"][1]["vs_recomputed_m"] == pytest.approx(math.hypot(0.05, 0.04))
    s = rr.summarize(err)
    assert s["arm"]["n"] == 1 and s["arm"]["end_circle"]["median_m"] == pytest.approx(0.0921954, abs=1e-6)
    assert s["arm"]["last_step"]["median_m"] == pytest.approx(0.1) and s["B0"]["last_step"]["median_truth_sigma_m"] == 0.05
    assert s["arm"]["recomputed"]["n"] == 1
    assert rr.summarize(rr.final_errors(docs, {"arm": str(run)}))["arm"]["end_circle"]["n"] == 0   # no truths: no circle
    (run / "seed_1.jsonl").write_text(json.dumps({"estimate_pose": {"x_m": 0, "y_m": 0, "theta_deg": 0}}) + "\n")
    err = rr.final_errors(docs, {"arm": str(run)}, truths)            # one step short: not counted
    assert err["arm"][1]["complete"] is False and rr.summarize(err)["arm"]["n_incomplete"] == 1


def test_estimate_from_the_study_rates():
    idx = {"episodes": [{"steps": 100}, {"steps": 50}]}
    e = rr.estimate(idx)
    assert e["claude-opus-5-5"]["usd"] == pytest.approx(150 * 0.0729)
    assert e["qwen38-flash-xhigh"]["hours_throughput"] == pytest.approx(150 * 31.3 / 3600)
    assert e["gemma4-26b"]["hours_longest_episode"] == pytest.approx(100 * 1240.4 / 3600)


def test_a_set_of_batches_keeps_its_seeds_and_grows_on_a_rerun(batch, tmp_path):
    second = tmp_path / "batches" / "b-two"
    _episode(str(second / "episodes" / "ep01-a1"), 1, 3)
    man = json.loads((batch / "manifest.json").read_text())
    man["episodes"] = [dict(man["episodes"][0], result={"complete": True, "ended_by": "budget", "steps": 3})]
    (second / "manifest.json").write_text(json.dumps(man))
    out = tmp_path / "set"
    idx = rr.convert_batches([str(batch)], str(out))
    assert [(b["batch"], b["seed_base"]) for b in idx["batches"]] == [("b-test", 1000)]
    assert [e["seed"] for e in idx["episodes"]] == [1001, 1002]
    first_sha = {e["seed"]: e["sha12"] for e in idx["episodes"]}
    idx = rr.convert_batches([str(second)], str(out))                 # a later batch: added, the first one kept
    assert [(b["batch"], b["seed_base"]) for b in idx["batches"]] == [("b-test", 1000), ("b-two", 2000)]
    assert [e["seed"] for e in idx["episodes"]] == [1001, 1002, 2001] and idx["steps"] == 13
    idx = rr.convert_batches([str(batch), str(second)], str(out))     # converting again writes the same bytes
    assert {e["seed"]: e["sha12"] for e in idx["episodes"] if e["seed"] < 2000} == first_sha
    doc = json.loads((out / "seed_2001.json").read_text())
    assert doc["seed"] == 2001 and doc["real"]["batch_seed"] == 1 and doc["real"]["batch"] == "b-two"
    with pytest.raises(ValueError):                                   # a single-batch folder is not a set
        rr.convert_batch(str(batch), str(tmp_path / "single"))
        rr.convert_batches([str(batch)], str(tmp_path / "single"))


def test_the_logs_do_not_depend_on_the_working_directory(batch, tmp_path, monkeypatch):
    shas = []
    for cwd in (ROOT, ROOT.parent):
        monkeypatch.chdir(cwd)
        idx = rr.convert_batch(str(batch), str(tmp_path / ("o-%d" % len(shas))))
        shas.append([e["sha12"] for e in idx["episodes"]])
        assert idx["world_file"] == "configs/arenas/real-room.json"
    assert shas[0] == shas[1]


def test_an_episode_whose_end_circle_was_interrupted_is_converted(batch, tmp_path):
    """b2-real-03 ep02 (2026-11-25): DONE at its last step, then a stall inside the end circle halted the batch, so
    the manifest has no end_fix and no end_pose_*, but a complete result and the final error."""
    _as_real_folder(batch)
    man = json.loads((batch / "manifest.json").read_text())
    e = man["episodes"][0]
    e["halt"] = {"code": "stall", "detail": "TURN_LEFT_30: stall_right"}
    for k in ("end_fix", "end_pose_map", "end_pose_world"):
        e.pop(k, None)
    (batch / "manifest.json").write_text(json.dumps(man))
    idx = rr.convert_batch(str(batch), str(tmp_path / "o"))
    ep = [x for x in idx["episodes"] if x["episode"] == "ep01-a1"][0]
    assert ep["note"] == "completed; end circle interrupted by stall"
    assert ep["end_pose_source"] == rr.LAST_STEP_TRUTH
    doc = json.loads((tmp_path / "o" / "seed_1.json").read_text())
    last = doc["records"][-1]["truth"]
    assert doc["real"]["end_pose_map"] == {k: last[k] for k in ("x_m", "y_m", "theta_deg")}
    truths = rr.independent_truths({1: doc}, str(batch.parent))
    assert truths[1]["end_circle"] is None and "halted in it (stall)" in truths[1]["end_circle_why"]
    err = rr.final_errors({1: doc}, {}, truths)
    assert "vs_end_circle_m" not in err["B2"][1] and err["B2"][1]["complete"]       # no end circle: no such column
    s = rr.summarize(err)["B2"]
    assert s["end_circle"]["n"] == 0 and s["end_circle"]["median_m"] is None and s["last_step"]["n"] == 1


def test_an_arm_in_sibling_run_folders_is_analysed_as_one(batch, tmp_path):
    """A batch added later runs into runs/<arm>+<batch> when the replay code changed (the runner refuses to resume the
    first folder then); analyze merges an arm's folders, refuses a seed in two of them, and refuses folders that
    differ in more than the code hashes."""
    rr.convert_batch(str(batch), str(tmp_path / "o"))
    o, runs = str(tmp_path / "o"), tmp_path / "runs"
    seeds = sorted(rr.load_obslogs(o)[1])
    assert len(seeds) >= 2
    for name, part in (("procedure", seeds[:1]), ("procedure+later", seeds[1:])):
        assert tool.cmd_run(_args(provider="procedure", obslogs=o, out=str(runs / name),
                                  extra=["--seeds", ",".join(map(str, part))])) == 0

    def analyze(*folders, out="r"):
        argv = ["analyze", "--obslogs", o, "--out", str(tmp_path / out)]
        for f in folders:
            argv += ["--run", "proc=%s" % (runs / f)]
        return tool.cmd_analyze(tool.parser().parse_args(argv))

    assert analyze("procedure", "procedure+later") == 0
    res = json.loads((tmp_path / "r.json").read_text())
    assert all(res["errors"]["proc"][str(s)]["complete"] for s in seeds)
    assert res["errors"]["proc"] == res["errors"]["B2"]                 # the stand-in is B2 at every step
    assert [p["seeds"] for p in res["run_parts"]["proc"]] == [seeds[:1], seeds[1:]]
    assert res["run_stats"]["proc"]["steps"] == res["run_stats"]["proc"]["expected_steps"]
    assert "Arms run in several folders" in (tmp_path / "r.md").read_text()
    with pytest.raises(SystemExit):                                     # one seed in two folders of an arm
        analyze("procedure", "procedure+later", "procedure")
    head = json.loads((runs / "procedure+later" / "run.json").read_text())
    (runs / "procedure+later" / "run.json").write_text(json.dumps(dict(head, max_steps=10)))
    with pytest.raises(SystemExit):                                     # differs in more than the code hashes
        analyze("procedure", "procedure+later")
    (runs / "procedure+later" / "run.json").write_text(json.dumps(dict(head, real_replay_sha12="0" * 12)))
    assert analyze("procedure", "procedure+later") == 0                 # the code hashes may differ


def test_the_analysis_recomputes_the_truth_with_the_batchs_own_tool(tmp_path, monkeypatch):
    """A dry batch on the simulated car, converted and analysed with tools/recompute_truth.py: with the tracker the
    batch ran (slip sigma 0) the recomputed truth is the logged one, the end circle comes from the manifest for the
    episodes that ended by DONE, and the result names the tool and its parameters."""
    from test_recompute_truth import dry_batch
    b = dry_batch(tmp_path, monkeypatch)
    o = tmp_path / "o"
    idx = rr.convert_batch(str(b), str(o))
    assert idx["episodes"]
    argv = ["analyze", "--obslogs", str(o), "--batches", str(b.parent), "--out", str(tmp_path / "r")]
    assert tool.cmd_analyze(tool.parser().parse_args(argv + ["--slip-sigma", "0"])) == 0
    res = json.loads((tmp_path / "r.json").read_text())
    assert res["truth_settings"]["recompute_tool"] == "tools/recompute_truth.py" and res["truth_settings"]["slip_sigma"] == 0
    man = json.loads((b / "manifest.json").read_text())
    circles = 0
    for e in idx["episodes"]:
        row, t = res["errors"]["B2"][str(e["seed"])], res["truths"][str(e["seed"])]
        assert row["vs_recomputed_m"] == pytest.approx(row["final_m"], abs=0.005)
        entry = [x for x in man["episodes"] if x["id"] == e["episode"]][0]
        if entry["result"]["ended_by"] == "DONE" and (entry.get("end_fix") or {}).get("ok"):
            assert t["end_circle"]["pose"] == pytest.approx(rr.to_map_pose(entry["start_pose_world"], entry["end_fix"]["pose"]))
            assert row["vs_end_circle_m"] >= 0
            circles += 1
    assert circles >= 1 and res["summary"]["B2"]["end_circle"]["n"] == circles
    assert all(res["truths"][str(e["seed"])]["logged_tracker"] == {"slip_sigma_per_m": 0.0, "slip_north_per_m": 0.0}
               for e in idx["episodes"])                              # the dry batch ran the tracker without a slip sigma
    md = (tmp_path / "r.md").read_text()
    assert "tools/recompute_truth.py" in md and "slip sigma 0.00" in md and "the truth used first" in md
    assert "Exploratory, not pre-registered" in md and "confirmatory" not in md
    assert "The batches' trackers: batch: slip sigma 0.00 + 0.00 x north per metre." in md
    assert tool.cmd_analyze(tool.parser().parse_args(argv + ["--slip-sigma", "0.3"])) == 0
    assert "slip sigma 0.30" in (tmp_path / "r.md").read_text()


def test_an_episode_the_procedure_stopped_is_converted_flagged_and_listed_apart(batch, tmp_path):
    """b2-real-06 ep02 (2026-11-25): the frozen B2 met a branch it does not implement ("driver stopped"); the harness
    wrote that step as a fallback and no move followed, so the end circle measured that step's pose. Converted, with a
    flag; its end circle is a truth; the main statistics leave it out and the result lists it apart."""
    _as_real_folder(batch)
    man = json.loads((batch / "manifest.json").read_text())
    e = man["episodes"][0]
    e.update(status="done", halt=None, result={"complete": True, "ended_by": "error", "steps": 6,
                                               "detail": "driver stopped: B2 stopped: E5 leg with no forward move and no E4"})
    (batch / "manifest.json").write_text(json.dumps(man))
    o = tmp_path / "o"
    idx = rr.convert_batch(str(batch), str(o))
    ep = [x for x in idx["episodes"] if x["episode"] == "ep01-a1"][0]
    assert ep["note"].startswith("flagged procedure_stopped: driver stopped")
    _, docs = rr.load_obslogs(str(o))
    truths = rr.independent_truths(docs, str(batch.parent))
    assert truths[1]["flag"] == rr.PROCEDURE_STOPPED and truths[1]["end_circle"] is not None
    assert "flag" not in truths[2]
    err = rr.final_errors(docs, {}, truths)
    s = rr.summarize(err)["B2"]
    assert err["B2"][1]["flag"] == rr.PROCEDURE_STOPPED and "vs_end_circle_m" in err["B2"][1]
    assert s["n"] == 1 and s["n_flagged"] == 1 and s["last_step"]["n"] == 1 and s["end_circle"]["n"] == 0
    md = rr.result_markdown("t", idx, err, rr.summarize(err), ["B0", "B2"], truths=truths)
    assert "Listed apart, not in n above" in md and "ep01-a1 (flagged: procedure_stopped)" in md
    # the batch's other endings by error are still not converted
    e["result"] = {"complete": True, "ended_by": "error", "detail": "no_progress", "steps": 6}
    (batch / "manifest.json").write_text(json.dumps(man))
    assert [x["episode"] for x in rr.convert_batch(str(batch), str(tmp_path / "o2"))["excluded"]][:1] == ["ep01-a1"]
