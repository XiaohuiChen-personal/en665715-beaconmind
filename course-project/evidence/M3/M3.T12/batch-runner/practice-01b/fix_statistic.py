"""The practice batch's odometry_scale halt replayed from its records: the per-step statistic that halted it (the sum of
the fixes' innovations along the leg driven over the sum of the legs) and the noise-weighted estimate that replaced
it. usage (course-project/beaconmind, PYTHONPATH=src): python3 fix_statistic.py EPISODE_DIR

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this replay of the practice batch's halt."""
import json, math, sys
from beaconmind.car.backend import compose

ep = sys.argv[1]
rows = []
for part, steps in (("pre", "pre/steps.jsonl"), ("ep", "backend/steps.jsonl")):
    tr = [json.loads(l) for l in open("%s/%s" % (ep, "pre/truth.jsonl" if part == "pre" else "truth.jsonl"))]
    st = [json.loads(l) for l in open("%s/%s" % (ep, steps))]
    rows += [(part, t, s) for t, s in zip(tr, st)]
prev, leg = None, [0.0, 0.0]
old_sum = old_travel = sxy = sxx = 0.0
n = 0
for part, t, s in rows:
    after = t["tracked_world"]["pose"]
    odo = s.get("odometry_exact")
    if prev is not None and odo:
        before = compose(prev, odo)
        leg[0] += before["x_m"] - prev["x_m"]
        leg[1] += before["y_m"] - prev["y_m"]
    else:
        before = prev or after
    vf = t.get("view_fix") or {}
    if vf.get("ok") and prev is not None:
        L = math.hypot(*leg)
        if L >= 0.05:
            innov = ((vf["pose"]["x_m"] - before["x_m"]) * leg[0] + (vf["pose"]["y_m"] - before["y_m"]) * leg[1]) / L
            old_sum += innov
            old_travel += L
            n += 1
            var = vf["sigma_xy_m"] ** 2 + t["tracked_world"]["sigma_xy_m"] ** 2
            sxy += L * innov / var
            sxx += L * L / var
            print("%s row %2d %-12s leg %.3f m, fix %.3f m along it (sigma %.3f, %s, tags %s) -> old statistic %+.1f %%"
                  % (part, t["row"], t["action"], L, innov, vf["sigma_xy_m"], vf.get("kind"), vf.get("tags"),
                     100 * old_sum / old_travel))
        leg = [0.0, 0.0]
    prev = after
print("old statistic: %+.1f %% over %.2f m, %d fixes" % (100 * old_sum / old_travel, old_travel, n))
print("noise-weighted: %+.1f %% +- %.1f %% (one standard error)" % (100 * sxy / sxx, 100 / math.sqrt(sxx)))
