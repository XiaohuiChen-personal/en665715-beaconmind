"""A tag surveyed 0.3 m wrong, fixed again and again before tag_survey can catch it: what the same-tag rule does to
the position sigma and to the guard. The test's walk (test_a_tag_surveyed_wrongly_by_d_cannot_pull_the_car_toward_its_wall):
T06 (window wall, id 12) is in the world file 0.3 m into the room; the camera sees T06 alone; the car drives FORWARD_10
at the window wall for as long as the guard allows. "Before tag_survey catches it" is made explicit by letting the
tag steer without a check (tag_check_k inf, tag_trust off: a tag that a circle had trusted). Old rule against new,
slip sigma 0 and 0.3. Per step: the position sigma, tracked minus true x (the pull), the true footprint depth and the
room the guard believes it has.
usage (course-project/beaconmind): python3 wrong_tag_walk.py [d]

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this measurement."""
import math, sys, tempfile, pathlib
sys.path.insert(0, "src"); sys.path.insert(0, "tests")
from beaconmind.car import batch as B
from beaconmind.car.latch import Latch
from beaconmind.harness import closed_loop as cl, replay as rp
import test_car_batch as T
NEW = B.PoseTracker._shrink


def old(self, same, a, b, fix_sigma):
    if not same:
        self.sigma_xy_m = max(math.sqrt(a * b / (a + b)), self.floor_m)


def walk(d, rule, slip, sigma0=None):
    B.PoseTracker._shrink = NEW if rule == "new" else old
    tmp = pathlib.Path(tempfile.mkdtemp())
    place = {"x_m": 2.6, "y_m": 2.58, "theta_deg": 0.0}
    p = B.BatchParams(world_path="x", start_poses=[dict(place, id="P")], initial_pose=dict(place), max_range_m=3.0,
                      tag_check_k=float("inf"), tag_trust=False, odometry_slip_sigma_per_m=slip)
    rig = B.dry_rig(T.WORLD20, place, latch=Latch(tmp / "LATCH"), seed=1, max_range_m=3.0)
    r = B.BatchRunner(p, rig, T.world_with("T06", -d, 0.0), tmp / "b", driver=cl.B2Driver(),
                      budget=rp.Budget(float("inf")), log=lambda *a: None, run_episode=cl.run_episode)
    r.preflight()
    env = r._service_env("t", str(tmp / "t"))
    env.reset(1)
    r.localised = env.use_views = True
    real = env.inner.detector
    env.inner.detector = lambda jpegs, n=None: dict(real(jpegs, n), detections=[
        x for x in real(jpegs, n)["detections"] if x.get("id") == 12])
    while abs(B.wrap_deg(r.tracker.pose["theta_deg"])) > 15:
        env.step("TURN_RIGHT_30" if r.tracker.pose["theta_deg"] > 0 else "TURN_LEFT_30")
    if sigma0 is not None:                  # as after a blind stretch: the last fix was T06's, the sigma has grown
        r.tracker.sigma_xy_m = sigma0
    rows = []
    for i in range(25):
        if r.monitor.halted:
            break
        res = env.step("FORWARD_10")["move"]["result"]
        t = rig.sim_truth_fn()
        believed = r.guard.footprint_depth(r.tracker.pose)
        rows.append((i + 1, res, r.tracker.sigma_xy_m, r.tracker.pose["x_m"] - t["x_m"], r.guard.footprint_depth(t), believed))
        if res != "done":
            break
    return rows, r.monitor.halted, bool(rig.link.sim.p.blocked_left or rig.link.sim.p.blocked_right)


if __name__ == "__main__":
    d = float(sys.argv[1]) if len(sys.argv) > 1 else 0.3
    for slip, sigma0 in ((0.0, None), (0.3, None), (0.3, 0.25)):
        for rule in ("old", "new"):
            rows, halt, contact = walk(d, rule, slip, sigma0)
            print("== T06 surveyed %.1f m into the room, steering; same-tag rule %s, slip sigma %.1f%s: %d forward moves, halt %s, contact %s"
                  % (d, rule, slip, "" if sigma0 is None else ", the sigma at %.2f before the walk" % sigma0,
                     sum(x[1] == "done" for x in rows), (halt or {}).get("code"), contact))
            print("   step result   sigma   tracked-true x   true depth   believed depth")
            for x in rows:
                print("   %4d %-8s %6.3f   %+8.3f m      %6.3f m     %6.3f m" % x)
