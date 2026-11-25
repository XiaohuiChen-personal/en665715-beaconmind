"""Tests of beaconmind.demo.episode (the run-folder reader) and beaconmind.demo.numbers.

A three-step run folder is written by hand in tmp_path, in the harness's row format; the real simulated episode is
checked against its own summary when its git-ignored log folder is present (skipped otherwise).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote these tests.
"""
import json
import os

import pytest

import beaconmind
from beaconmind.demo import episode as E
from beaconmind.demo import numbers as N

TAGS = [{"tag": 0, "id": 3, "x_m": 1.0, "y_m": 0.0, "normal_deg": 180.0},
        {"tag": 1, "id": 3, "x_m": -1.0, "y_m": 0.0, "normal_deg": 0.0},     # the same ID on another wall
        {"tag": 2, "id": 7, "x_m": 0.0, "y_m": 1.0, "normal_deg": -90.0}]


def _row(k, truth, est, prior, calls, uses, secs, cost, move, mapping, decision=None, end=None):
    turns = [{"seconds": s, "tool_uses": u, "cost_usd": c} for s, u, c in zip(secs, uses, cost)]
    rep = {"step": k, "pose": est, "pose_source": "odometry", "map": mapping, "decision": decision or move,
           "note": "step %d" % k}
    return {"step": k, "truth": truth, "estimate_pose": est, "harness_prior": prior, "seconds": sum(secs),
            "turns": turns, "calls": calls, "observation": {"detections": [{"det": 0, "id": 3, "range_m": 1.0,
                                                                            "bearing_deg": 0.0}]},
            "raw": {"detections": [{"det": 0, "id": 3, "_tag": 0}]}, "report": rep, "next_prev": rep,
            "decision": decision or move, "fallback": False,
            "executed_move": {"action": move, "result": "done"} if move else None,
            "move_calls": [{"action": move, "tool_result": "done", "validator_ok": True}] if move else [],
            "violations": [], "episode_end": end}


def _pose(x, y, th):
    return {"x_m": x, "y_m": y, "theta_deg": th}


@pytest.fixture
def run(tmp_path):
    c = lambda tool: {"tool": tool, "args": {}, "result": {"x_m": 0, "y_m": 0, "theta_deg": 0}}  # noqa: E731
    m1 = [{"beacon": "B3", "id": 3, "x_m": 1.05, "y_m": 0.0, "state": "tentative"}]
    m2 = m1 + [{"beacon": "B7", "id": 7, "x_m": 0.0, "y_m": 1.4, "state": "tentative"}]      # 0.40 m off: not mapped
    rows = [
        _row(0, _pose(0, 0, 0), _pose(0, 0, 0), _pose(0, 0, 0), [c("exploration_summary"), c("move")], [1, 1, 0],
             [2.0, 3.0, 5.0], [0.01, 0.02, 0.03], "TURN_LEFT_30", m1),
        _row(1, _pose(0, 0, 30), _pose(0, 0, 29.5), _pose(0, 0, 29.0), [c("compose_odometry"), c("move")], [2, 0],
             [4.0, 4.0], [0.04, 0.05], "FORWARD_25", m2),
        _row(2, _pose(0.217, 0.125, 30), _pose(0.21, 0.13, 29.5), _pose(0.2, 0.12, 29.5), [], [0], [3.0], [0.01],
             None, m2, decision="DONE", end={"ended_by": "DONE", "detail": "decision"}),
    ]
    with open(tmp_path / "seed_7.jsonl", "w") as fh:
        fh.writelines(json.dumps(r) + "\n" for r in rows)
    world = {"start_pose": _pose(2.0, 1.0, 90.0), "scene": {"walls_polygon": [[-2, -2], [2, -2], [2, 2], [-2, 2]],
                                                          "tags": TAGS}}
    (tmp_path / "seed_7.world.json").write_text(json.dumps(world))
    summary = {"steps": 3, "moves_executed": 2, "refused_move_calls": 0, "ended_by": "DONE",
               "map": {"tags_found": 1, "n_entries": 2}, "time": {"total_s": 21.0}, "cost_usd": 0.16}
    (tmp_path / "seed_7.summary.json").write_text(json.dumps(summary))
    return tmp_path


def test_steps_time_base_sums_the_logged_step_times(run):
    ep = E.load_episode(str(run))
    assert ep.seed == 7 and len(ep.steps) == 3
    assert [(s.t0, s.t1) for s in ep.steps] == [(0.0, 10.0), (10.0, 18.0), (18.0, 21.0)]
    assert ep.total_s == 21.0
    # a call is placed at the end of the turn that made it
    assert [round(c.t, 6) for c in ep.steps[0].calls] == [2.0, 5.0]
    assert [round(c.t, 6) for c in ep.steps[1].calls] == [14.0, 14.0]
    assert ep.cost_at(5.0) == pytest.approx(0.03) and ep.cost_at(100.0) == pytest.approx(0.16)
    assert ep.step_at(-1.0) == 0 and ep.step_at(10.0) == 1 and ep.step_at(20.9) == 2


def test_calls_without_turns_are_spread_over_the_step():
    calls = [{"tool": "a"}, {"tool": "b"}, {"tool": "c"}]
    placed = E.place_calls(calls, [], 0.0, 8.0)
    assert [c.t for c in placed] == [2.0, 4.0, 6.0]
    assert E.tool_ok({"status": "error", "error": "x"}) is False and E.tool_ok({"result": "refused"}) is True


def test_mapped_tags_uses_the_nearest_tag_with_the_same_id():
    assert E.mapped_tags([{"id": 3, "x_m": 0.9, "y_m": 0.1}], TAGS) == {0}
    assert E.mapped_tags([{"id": 3, "x_m": -0.8, "y_m": 0.0}], TAGS) == {1}
    assert E.mapped_tags([{"id": 7, "x_m": 0.0, "y_m": 1.31}], TAGS) == set()         # 0.31 m: outside 0.30 m
    assert E.mapped_tags([{"id": 9, "x_m": 0.0, "y_m": 1.0}, {"id": 3, "x_m": "?"}], TAGS) == set()


def test_view_before_and_after_the_report_and_during_the_glide(run):
    ep = E.load_episode(str(run))
    v = E.view_at(ep, 1.0)                      # step 0, before its report: the prior, the empty earlier map
    assert v.k == 0 and not v.report_shown and v.belief == _pose(0, 0, 0) and v.mapped == set()
    assert [c.tool for c in v.calls] == []
    v = E.view_at(ep, 3.0)
    assert [c.tool for c in v.calls] == ["exploration_summary"]
    # at the move (t = 10) with a 2 s glide the panel keeps step 0 and the car turns halfway at t = 11
    v = E.view_at(ep, 11.0, anim_s=2.0)
    assert v.k == 0 and v.moving and v.report_shown
    assert v.truth["theta_deg"] == pytest.approx(15.0)
    assert v.mapped == {0} and v.detected == {0}
    v = E.view_at(ep, 12.5, anim_s=2.0)          # glide over: step 1, prior shown until its report
    assert v.k == 1 and not v.moving and v.belief == _pose(0, 0, 29.0)
    v = E.view_at(ep, 19.0, anim_s=2.0)          # step 1's forward move; the glide is cut to 1.8 s (60 % of step 2)
    assert v.k == 1 and v.moving
    assert v.truth["x_m"] == pytest.approx(0.217 / 1.8)
    assert len(v.trail_truth) == 3
    v = E.view_at(ep, 20.0, anim_s=2.0)
    assert v.k == 2 and not v.moving


def test_glide_never_takes_more_than_most_of_the_next_step(run):
    ep = E.load_episode(str(run))
    # step 2 lasts 3 s: a 10 s glide of step 1's move is cut to 60 % of it
    assert E._glide(10.0, ep.steps[1], ep.steps[2]) == pytest.approx(1.8)
    assert E._glide(10.0, ep.steps[2], None) == pytest.approx(10.0)


def test_interp_pose_takes_the_short_way_round():
    p = E.interp_pose(_pose(0, 0, 170.0), _pose(2, 0, -170.0), 0.5)
    assert abs(abs(p["theta_deg"]) - 180.0) < 1e-9 and p["x_m"] == 1.0


def test_check_against_summary_finds_a_disagreement(run):
    ep = E.load_episode(str(run))
    assert all(ok for *_rest, ok in E.check_against_summary(ep))
    ep.summary["cost_usd"] = 0.17
    ep.summary["map"]["tags_found"] = 2
    bad = {w for w, _a, _b, ok in E.check_against_summary(ep) if not ok}
    assert bad == {"cost (US$)", "tags mapped within 0.30 m"}


def test_epoch_time_base_uses_the_host_clock(run):
    rows = [json.loads(line) for line in open(run / "seed_7.jsonl")]
    spend, t = [], 1000.0
    for r in rows:
        for tr in r["turns"]:
            t += tr["seconds"]
            spend.append({"t": t, "usd": tr["cost_usd"]})
        t += 1.5                                       # each step's move takes 1.5 s on the car
    (run / "spend.jsonl").write_text("".join(json.dumps(s) + "\n" for s in spend))
    moves = [{"step": 0, "phase": "commanded", "t": 1010.0}, {"step": 0, "phase": "result", "t": 1011.5},
             {"step": 1, "phase": "commanded", "t": 1019.5}, {"step": 1, "phase": "result", "t": 1021.0}]
    (run / "seed_7.moves.jsonl").write_text("".join(json.dumps(m) + "\n" for m in moves))
    ep = E.load_episode(str(run), time_base="epoch", backend_steps=[{"type": "step", "step": 1, "t_unix": 1011.6}])
    assert ep.epoch0 == pytest.approx(1000.0)
    assert ep.steps[1].t0 == pytest.approx(1011.6)                         # the sensing time, when logged
    assert ep.steps[0].t_report == pytest.approx(1010.0)
    assert (ep.steps[0].move_t0, ep.steps[0].move_t1) == (1010.0, 1011.5)
    assert ep.move_windows == [(1010.0, 1011.5), (1019.5, 1021.0)]
    assert ep.steps[2].t0 == pytest.approx(1021.0)                         # after step 1's move result
    (run / "spend.jsonl").write_text(json.dumps(spend[0]) + "\n")
    with pytest.raises(ValueError):
        E.load_episode(str(run), time_base="epoch")


def test_numbers_fill_and_refuse_unknown_keys():
    n = N.Numbers()
    n.put("a.b", "4.60", "here")
    assert n.fill("US${{a.b}}") == "US$4.60"
    with pytest.raises(KeyError):
        n.fill("{{a.c}}")
    with pytest.raises(ValueError):
        n.put("a.b", "4.61", "elsewhere")
    assert N.mmss(1129.8) == "18:50"


SIM_RUN = os.path.join(str(beaconmind.course_root()), "data", "closed-loop", "20261118-room-final", "claude-opus-5-5")


@pytest.mark.skipif(not os.path.isdir(SIM_RUN), reason="the simulated episode's logs are git-ignored and not here")
def test_the_simulated_episode_agrees_with_its_summary():
    ep = E.load_episode(SIM_RUN)
    rows = E.check_against_summary(ep)
    assert [w for w, *_x, ok in rows if not ok] == []
    assert {w for w, *_x in rows} >= {"steps", "tags mapped within 0.30 m", "cost (US$)", "time total (s)"}
