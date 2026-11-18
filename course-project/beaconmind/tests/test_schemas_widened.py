"""Tests of the additive widening of bm.observation-1 and bm.report-1 (2026-11-18): what the frozen simulator and the
coded procedure write is now accepted, and what was rejected for a real reason still is.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote these tests.
"""
import copy

import pytest

from beaconmind.envs import kinsim_lite as ks
from beaconmind.schemas import validate


@pytest.fixture(scope="module")
def episode():
    return ks.run_episode(1003)


def _obs(episode, i):
    raw = episode["records"][i]["raw"]
    return ks.as_observation(episode["seed"], raw, raw["counters"])


def test_observation_last_move_may_be_null(episode):
    obs = _obs(episode, 0)
    assert obs["last_move"] is None and validate("observation", obs) == []
    assert validate("observation", _obs(episode, 1)) == []


def test_observation_last_move_is_still_checked(episode):
    obs = _obs(episode, 1)
    for bad in ({"action": "JUMP", "result": "done"}, {"action": "FORWARD_25", "result": "great"},
                {"action": "FORWARD_25"}, {"action": "FORWARD_25", "result": "done", "extra": 1}, "FORWARD_25", 0):
        assert validate("observation", dict(obs, last_move=bad)) != []
    missing = {k: v for k, v in obs.items() if k != "last_move"}
    assert validate("observation", missing) != []


def _report_with_rejection(episode):
    for rec in episode["records"]:
        if any(a["result"] == "rejected" and a["beacon"] is None for a in rec["report"]["associations"]):
            return copy.deepcopy(rec["report"])
    rep = copy.deepcopy(next(r["report"] for r in episode["records"] if r["report"]["associations"]))
    rep["associations"][0].update(beacon=None, result="rejected")
    return rep


def test_report_note_may_be_null_and_a_rejected_association_may_have_no_beacon(episode):
    rep = _report_with_rejection(episode)
    assert rep["note"] is None
    assert any(a["beacon"] is None for a in rep["associations"])
    assert validate("report", rep) == []
    assert validate("report", dict(rep, note="I rejected one detection.")) == []


@pytest.mark.parametrize("result", ["matched", "new", "ambiguous"])
def test_a_null_beacon_is_only_for_rejected(episode, result):
    rep = _report_with_rejection(episode)
    next(a for a in rep["associations"] if a["beacon"] is None)["result"] = result
    assert validate("report", rep) != []


def test_report_is_still_checked(episode):
    rep = _report_with_rejection(episode)
    labelled = copy.deepcopy(rep)
    labelled["associations"][0]["beacon"] = "tag7"
    assert validate("report", labelled) != []
    no_key = copy.deepcopy(rep)
    del no_key["associations"][0]["beacon"]
    assert validate("report", no_key) != []
    assert validate("report", dict(rep, note=5)) != []
    assert validate("report", {k: v for k, v in rep.items() if k != "note"}) != []


def test_a_whole_coded_episode_validates(episode):
    """Every observation, report and step message of a B2 episode (what the study's logs and prompts carry)."""
    prev = None
    for i, rec in enumerate(episode["records"]):
        obs = _obs(episode, i)
        assert validate("observation", obs) == []
        assert validate("report", rec["report"]) == []
        assert validate("step", {"mission": "EXPLORE", "operator_request": None, "OBSERVATION": obs,
                                 "PREVIOUS_REPORT": prev}) == []
        prev = rec["report"]
