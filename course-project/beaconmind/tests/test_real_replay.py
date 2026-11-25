"""Tests of the real-log replay (beaconmind/real_replay.py, tools/real_replay.py).

A small batch folder is made in tmp_path the way car/batch.py lays it out: the closed-loop harness drives the coded
procedure (B2) in the room simulator for a few steps, and truth.jsonl and manifest.json are written beside the rows.
No network: model arms are the free procedure stand-in or the test suite's scripted Anthropic client.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote these tests.
"""
import importlib.util
import json
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
    err = rr.final_errors({1: doc}, {})
    assert "vs_end_circle_m" in err["B2"][1]


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
    docs = {1: {"records": recs, "real": {"episode": "ep01-a1", "scenario": "S1", "end_pose_map": {"x_m": 1.0, "y_m": 0.01}}}}
    run = tmp_path / "arm"
    run.mkdir()
    (run / "seed_1.jsonl").write_text("".join(json.dumps({"estimate_pose": p}) + "\n" for p in (
        {"x_m": 0, "y_m": 0, "theta_deg": 0}, {"x_m": 0.94, "y_m": 0.08, "theta_deg": -3.0})))
    err = rr.final_errors(docs, {"arm": str(run)})
    assert err["B0"][1]["final_m"] == pytest.approx(0.03)
    assert err["B2"][1]["final_m"] == pytest.approx(0.05) and err["B2"][1]["final_deg"] == pytest.approx(2.0)
    assert err["arm"][1]["final_m"] == pytest.approx(0.1) and err["arm"][1]["vs_end_circle_m"] == pytest.approx(0.0921954, abs=1e-6)
    s = rr.summarize(err)
    assert s["arm"]["n"] == 1 and s["arm"]["median_m"] == pytest.approx(0.1) and s["B0"]["median_truth_sigma_m"] == 0.05
    (run / "seed_1.jsonl").write_text(json.dumps({"estimate_pose": {"x_m": 0, "y_m": 0, "theta_deg": 0}}) + "\n")
    err = rr.final_errors(docs, {"arm": str(run)})                    # one step short: not counted
    assert err["arm"][1]["complete"] is False and rr.summarize(err)["arm"]["n_incomplete"] == 1


def test_estimate_from_the_study_rates():
    idx = {"episodes": [{"steps": 100}, {"steps": 50}]}
    e = rr.estimate(idx)
    assert e["claude-opus-5-5"]["usd"] == pytest.approx(150 * 0.0729)
    assert e["qwen38-flash-xhigh"]["hours_throughput"] == pytest.approx(150 * 31.3 / 3600)
    assert e["gemma4-26b"]["hours_longest_episode"] == pytest.approx(100 * 1240.4 / 3600)
