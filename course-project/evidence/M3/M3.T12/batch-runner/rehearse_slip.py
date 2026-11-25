"""Rehearsal of a batch on a carpet whose slip depends on direction, as the slip test of 2026-11-25 measured it:
northward the car covers 0.78 of its counted distance, southward 1.04 (b2-real-02/). The simulated car's true
displacement is scaled by k(h) = 0.91 - 0.13 sin(h), h its world direction of travel (north = 90 deg: 0.78; south:
1.04; east and west 0.91), while its wheels count the full distance. Then tools/car_batch.py runs with the arguments
given.

usage (repository root): python3 course-project/evidence/M3/M3.T12/batch-runner/rehearse_slip.py [--north K]
<car_batch.py arguments> (needs --initial-pose x,y,theta: the simulated car's frame starts there, so its world heading
is theta + its own). --north K: the northward factor (default 0.78; b2-real-04's transit suggested about 0.70, and
0.67 was asked for); southward stays 1.04, and k(h) = (K + 1.04) / 2 - (1.04 - K) / 2 sin(h).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this rehearsal wrapper (and its --north option)."""
import importlib.util
import math
import pathlib
import sys

REPO = pathlib.Path.cwd() / "course-project"
sys.path.insert(0, str(REPO / "beaconmind" / "src"))
from beaconmind.car import simcar as S  # noqa: E402

args = sys.argv[1:]
NORTH, SOUTH = 0.78, 1.04
if args and args[0] == "--north":
    NORTH = float(args[1])
    args = args[2:]
THETA0 = math.radians(float(args[args.index("--initial-pose") + 1].split(",")[2]))
orig_step = S.SimCar.step
STATS = {"m_counted": 0.0, "m_true": 0.0}


def k_of(direction):
    return (NORTH + SOUTH) / 2.0 - (SOUTH - NORTH) / 2.0 * math.sin(direction)


def step(self, dt):
    x0, y0 = self.x, self.y
    orig_step(self, dt)
    dx, dy = self.x - x0, self.y - y0
    d = math.hypot(dx, dy)
    if d > 0:
        k = k_of(THETA0 + math.atan2(dy, dx))       # the direction of travel in the world frame
        self.x, self.y = x0 + k * dx, y0 + k * dy
        STATS["m_counted"] += d
        STATS["m_true"] += k * d


S.SimCar.step = step
spec = importlib.util.spec_from_file_location("car_batch", REPO / "tools" / "car_batch.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
code = tool.main(args)
print("carpet slip added (north %.2f, south %.2f): %.2f m counted, %.2f m on the floor (%.3f)" % (
    NORTH, SOUTH, STATS["m_counted"], STATS["m_true"], STATS["m_true"] / max(STATS["m_counted"], 1e-9)))
sys.exit(code)
