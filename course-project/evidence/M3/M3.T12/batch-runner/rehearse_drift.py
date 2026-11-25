"""Rehearsal of the first real batch with the floor check's heading drift in the simulated car (2026-11-25).

The real car turned left by 3.4 deg on average at every straight move (FORWARD_25 2.6-4.4, FORWARD_10 3.0-4.5;
BACKWARD_10 -3.2 to -3.6: gyro, tags agree), and its gyro and odometry report it. The simulated car's own model
(wheel gains under the executor's heading hold) gives at most 0.75 deg, so here the turn is added: when the
executor sends the zero that ends a straight move, the simulated car turns another DRIFT_DEG (forward) or
-DRIFT_DEG (backward) about its axle at 20 deg/s, which its IMU reports (the yaw comes from the true heading).
Then tools/car_batch.py runs with the arguments given on the command line.
usage (repository root): python3 course-project/evidence/M3/M3.T12/batch-runner/rehearse_drift.py DRIFT_DEG <car_batch.py arguments>

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this rehearsal wrapper."""
import importlib.util, math, pathlib, sys
REPO = pathlib.Path.cwd() / "course-project"
sys.path.insert(0, str(REPO / "beaconmind" / "src"))
from beaconmind.car import simcar as S

DRIFT = float(sys.argv[1])
RATE = math.radians(20.0)
orig_receive, orig_step = S.SimCar._receive, S.SimCar.step
COUNT = {"kicks": 0, "deg": 0.0}


def _receive(self, v, w, stamp, marker):
    sign = getattr(self, "_straight_sign", 0)
    if v == 0.0 and w == 0.0 and sign:
        self._kick = math.radians(DRIFT) * sign
        self._straight_sign = 0
        COUNT["kicks"] += 1
        COUNT["deg"] += DRIFT * sign
    elif v != 0.0 and abs(w) < 1e-6:
        self._straight_sign = 1 if v > 0 else -1
    elif w != 0.0:
        self._straight_sign = 0
    return orig_receive(self, v, w, stamp, marker)


def step(self, dt):
    orig_step(self, dt)
    k = getattr(self, "_kick", 0.0)
    if k:
        d = math.copysign(min(abs(k), RATE * dt), k)
        self.theta += d
        self._kick = k - d


S.SimCar._receive, S.SimCar.step = _receive, step
spec = importlib.util.spec_from_file_location("car_batch", REPO / "tools" / "car_batch.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
code = tool.main(sys.argv[2:])
print("drift added: %d straight moves, %+.1f deg in all (%.1f deg each)" % (COUNT["kicks"], COUNT["deg"], DRIFT))
sys.exit(code)
