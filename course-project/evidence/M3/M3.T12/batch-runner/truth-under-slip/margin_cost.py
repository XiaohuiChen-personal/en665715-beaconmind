"""The cost of the guard settings in ten-episode batches with the exact real arguments and --slip-sigma 0.3 on the
simulated carpet (north 0.67 and 0.78, south 1.04), 3 seeds each: completions, guard refusals, halts.
usage (course-project/beaconmind): python3 margin_cost.py VARIANT OUT_JSON   VARIANT: now | spare0.10 | floor0.10

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this cost measurement of the guard settings."""
import json, math, sys, tempfile, pathlib, glob
sys.path.insert(0, "src")
from beaconmind.car import batch as B, simcar as S
from beaconmind.car.latch import Latch
from beaconmind.harness import closed_loop as cl, replay as rp
variant = sys.argv[1]
root = pathlib.Path("..")
world = json.load(open(root / "configs/arenas/real-room.json"))
scen = json.load(open(root / "configs/arenas/real-room-scenarios.json"))
starts = [dict(sc["start_pose"], id=sc["id"]) for sc in scen["scenarios"]]
place = {"x_m": 2.369, "y_m": 2.206, "theta_deg": -90.0}
TH0 = math.radians(place["theta_deg"]); orig = S.SimCar.step; NORTH = {"v": 0.67}
def slip_step(self, dt):
    x0, y0 = self.x, self.y; orig(self, dt); dx, dy = self.x - x0, self.y - y0
    if dx or dy:
        n = NORTH["v"]; k = (n + 1.04) / 2 - (1.04 - n) / 2 * math.sin(TH0 + math.atan2(dy, dx)); self.x, self.y = x0 + k * dx, y0 + k * dy
S.SimCar.step = slip_step
extra = {"now": {}, "spare0.10": {"start_turn_margin_m": 0.10, "turn_spare_m": 0.10}, "floor0.10": {"fix_floor_m": 0.10},
         "turn0.08": {"turn_margin_m": 0.08}, "turn0.10": {"turn_margin_m": 0.10}}[variant]
results = []
for north in (0.67, 0.78):
    NORTH["v"] = north
    for seed in (1, 2, 3):
        out = pathlib.Path(tempfile.mkdtemp())
        params = B.BatchParams(world_path="x", start_poses=starts, initial_pose=dict(place), episodes=10, max_steps=150, max_range_m=3.0,
                               range_bias_a_m=0.00492, range_bias_b=-0.01658, range_min_m=0.785, odometry_slip_sigma_per_m=0.3, **extra)
        rig = B.dry_rig(world, place, latch=Latch(out / "LATCH"), seed=seed, max_range_m=3.0)
        runner = B.BatchRunner(params, rig, world, out / "batch", driver=cl.B2Driver(), budget=rp.Budget(float("inf")), log=lambda *a: None, run_episode=cl.run_episode)
        res = runner.run(); m = json.load(open(out / "batch/manifest.json"))
        mop = [((e.get(k) or {}).get("miss_over_path")) for e in m["episodes"] for k in ("dead_reckoning_transit", "dead_reckoning_episode")]
        r = {"variant": variant, "north": north, "seed": seed, "status": res["status"], "halt": (res.get("halt") or {}).get("code"),
             "halt_detail": (res.get("halt") or {}).get("detail", "")[:120],
             "done": sum(e["status"] == "done" for e in m["episodes"]), "moves": m["moves_sent"],
             "guard_refusals": sum(e.get("guard_blocked_moves", 0) for e in m["episodes"]),
             "miss_over_path_max": max([x for x in mop if x is not None] or [0])}
        results.append(r); print(json.dumps(r), flush=True)
json.dump(results, open(sys.argv[2], "w"))
