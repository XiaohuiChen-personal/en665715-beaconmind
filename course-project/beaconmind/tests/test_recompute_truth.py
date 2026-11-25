"""tools/recompute_truth.py: the batch's step truth recomputed offline from its logged rows.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote these tests.
"""
import importlib.util
import json
import math
import pathlib

from beaconmind.car import batch as B
from beaconmind.car import simcar as S
from beaconmind.car.latch import Latch
from beaconmind.harness import closed_loop as cl
from beaconmind.harness import replay as rp

ROOT = pathlib.Path(__file__).resolve().parents[2]
PLACE = {"x_m": 2.369, "y_m": 2.206, "theta_deg": -90.0}


def load_tool():
    spec = importlib.util.spec_from_file_location("recompute_truth", ROOT / "tools" / "recompute_truth.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    return tool


def dry_batch(tmp_path, monkeypatch, north=None):
    """Two episodes in the real room on the simulated car; with north, on a carpet where the car covers that share of
    its counted distance northward (1.04 southward) while its wheels count all of it."""
    if north is not None:
        real = S.SimCar.step
        theta0 = math.radians(PLACE["theta_deg"])

        def slipping(self, dt):
            x0, y0 = self.x, self.y
            real(self, dt)
            dx, dy = self.x - x0, self.y - y0
            if dx or dy:
                k = (north + 1.04) / 2 - (1.04 - north) / 2 * math.sin(theta0 + math.atan2(dy, dx))
                self.x, self.y = x0 + k * dx, y0 + k * dy
        monkeypatch.setattr(S.SimCar, "step", slipping)
    world = json.loads((ROOT / "configs" / "arenas" / "real-room.json").read_text())
    starts = [{"id": "S1", "x_m": 2.50, "y_m": 1.50, "theta_deg": 90.0}, {"id": "S2", "x_m": 1.75, "y_m": 1.40, "theta_deg": 0.0}]
    params = B.BatchParams(world_path="configs/arenas/real-room.json", start_poses=starts, initial_pose=dict(PLACE),
                           episodes=2, max_steps=60, max_range_m=3.0)
    rig = B.dry_rig(world, PLACE, latch=Latch(tmp_path / "LATCH"), seed=1, max_range_m=3.0)
    runner = B.BatchRunner(params, rig, world, tmp_path / "batch", driver=cl.B2Driver(), budget=rp.Budget(float("inf")),
                           log=lambda *a: None, run_episode=cl.run_episode)
    runner.run()
    return tmp_path / "batch"


def test_with_the_batchs_own_tracker_the_replay_reproduces_the_logged_truth(tmp_path, monkeypatch):
    """The replay runs the batch's own per-step code over the logged rows: with the tracker the batch ran, every
    step's truth comes out as logged, within millimetres (the log rounds the sigmas it starts from, and the batch's tag
    trust is not replayed: here up to 0.003 m; on the five real episodes 0.000 to 0.001 m)."""
    tool = load_tool()
    batch = dry_batch(tmp_path, monkeypatch)
    out = tmp_path / "report.json"
    assert tool.main([str(batch), "--out", str(out)]) == 0
    report = json.loads(out.read_text())
    assert len(report) == 2 and all(r["largest_difference_from_the_logged_truth_m"] < 0.01 for r in report), report


def test_on_a_slipping_carpet_a_slip_aware_tracker_brings_the_truth_nearer_the_car(tmp_path, monkeypatch):
    """On a simulated carpet at 0.67 northward, the truth recomputed with 0.3 x distance of slip sigma is nearer the
    simulated car's own pose (p95 and max over the steps) than the truth the batch logged."""
    tool = load_tool()
    batch = dry_batch(tmp_path, monkeypatch, north=0.67)
    out = tmp_path / "report.json"
    assert tool.main([str(batch), "--slip-sigma", "0.3", "--out", str(out)]) == 0
    report = json.loads(out.read_text())
    logged = max(r["sim_logged_p95_max_m"][1] for r in report)
    recomputed = max(r["sim_recomputed_p95_max_m"][1] for r in report)
    assert recomputed < logged, report
