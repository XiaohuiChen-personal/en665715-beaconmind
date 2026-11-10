#!/usr/bin/env python3
"""Run arm B1 (GTSAM iSAM2, oracle association, odometry-scale calibration) on recorded kinsim episodes.

Run on the Spark host venv (gtsam 4.3.0), from the repository root:
  ~/.venvs/beaconmind/bin/python course-project/tools/b1_run.py --obslogs course-project/data/main/obslogs/test/drift2 \
      --out course-project/data/main/b1/test/drift2 --seeds 2000-2029
Each seed gives <out>/seed_<n>.json: the online pose per step (the scored trajectory), the smoothed poses, the final
tag map, the estimated odometry scales, the batch check, the run time, and provenance (git commit, SHA-256
prefixes of the log, the B1 module and this runner, the solver settings). The estimates are deterministic; only the
`seconds` field differs between runs. Seeds the recorder skipped (no log file) are listed and skipped.
`--no-scale` runs the first version without scale calibration (written with a `-noscale` suffix) for comparison.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote this runner.
"""
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "beaconmind" / "src"))
from beaconmind.baselines import b1_gtsam as b1  # noqa: E402

BATCH_TOL = {"position_m": 1e-4, "heading_deg": 0.01, "tag_m": 1e-4}


def seed_list(text):
    out = []
    for part in text.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b) + 1)) if b else [int(a)]
    return out


def sha12(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:12]


def gtsam_version():
    try:
        from importlib.metadata import version
        return version("gtsam")
    except Exception:
        return None


def git_commit():
    try:
        c = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "--short=12", "HEAD"], text=True).strip()
        dirty = subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain", "--",
                                         "beaconmind/src/beaconmind/baselines", "tools/b1_run.py"], text=True).strip()
        return c + ("+dirty" if dirty else "")
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--obslogs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--no-scale", action="store_true", help="the first version, without odometry-scale calibration")
    args = ap.parse_args()
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    calibrate = not args.no_scale
    prov = {"git_commit": git_commit(), "gtsam": gtsam_version(), "solver": b1.SOLVER, "calibrate_scale": calibrate,
            "sha12": {"b1_gtsam.py": sha12(b1.__file__), "b1_run.py": sha12(__file__)}}
    skipped, flagged = [], []
    for seed in seed_list(args.seeds):
        path = pathlib.Path(args.obslogs) / ("seed_%d.json" % seed)
        if not path.exists():
            skipped.append(seed)
            print("seed %d: no log (the recorder skips seeds whose B2 episode failed); skipped" % seed)
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        res = b1.build_and_solve(doc, calibrate_scale=calibrate)
        bc = b1.batch_check(res)
        bad = {k: v for k, v in bc.items() if v > BATCH_TOL[k]}
        if bad:
            flagged.append(seed)
        rec = {"seed": seed, "arm": "B1" if calibrate else "B1-noscale", "scored": "online", "online": res["online"],
               "smoothed": res["smoothed"], "map": res["map"], "scales": res["scales"], "seconds": res["seconds"],
               "n_factors": res["n_factors"], "n_tags": res["n_tags"], "batch_check": bc, "batch_flag": bad or None,
               "provenance": dict(prov, obslog_sha12=sha12(path))}
        name = "seed_%d.json" % seed if calibrate else "seed_%d-noscale.json" % seed
        (out / name).write_text(json.dumps(rec), encoding="utf-8")
        sc = res["scales"]
        print("seed %d: %d steps, %d tags, %d factors, %.2fs, scales %s, batch diff %.1e m / %.1e deg / %.1e m%s" % (
            seed, len(res["online"]), res["n_tags"], res["n_factors"], res["seconds"],
            "f %.4f t %.4f" % (sc["forward"], sc["turn"]) if sc else "-", bc["position_m"], bc["heading_deg"], bc["tag_m"],
            "  BATCH MISMATCH" if bad else ""))
    print("done: %d skipped %s, %d batch mismatches %s" % (len(skipped), skipped or "", len(flagged), flagged or ""))
    sys.exit(1 if flagged else 0)


if __name__ == "__main__":
    main()
