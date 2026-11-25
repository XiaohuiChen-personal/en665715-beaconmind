#!/usr/bin/env python3
"""Write configs/dv-real.json: the frozen configs/dv.json with the tag pilot's noise model and the chosen range limit.

    python3 course-project/tools/real_dv.py --noise course-project/configs/detector_noise.json --reject-range 3.0 \
        --evidence course-project/evidence/M1/M1.T8 --out course-project/configs/dv-real.json

Only after the tag pilot (tools/tag_pilot.py analyze --out course-project/configs/detector_noise.json) and Xiaohui
Chen's decision on the range limit (3.0 m, or 2.5 m if the pilot does not confirm it). Exactly four fields differ from
the frozen file: sigma_range_a_m, sigma_range_b_per_m, sigma_bearing_deg (from the pilot) and reject_range_above_m
(this argument); each has its own source, evidence and updated date, and a $comment lists them with both files'
sha12. Anything else that would differ refuses the write (beaconmind/dv_real.py says how the numbers map and why the
well_cond_* and reloc_sigma_* thresholds stay frozen). configs/dv.json itself is never written.

Then: --dv course-project/configs/dv-real.json in tools/car_batch.py, tools/closed_loop_run.py, tools/room_rehearsal.py.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote this tool.
"""
import argparse
import datetime
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "beaconmind" / "src"))

from beaconmind import dv_real  # noqa: E402

FROZEN = ROOT / "configs" / "dv.json"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--noise", required=True, help="the tag pilot's bm.detector_noise/1 file (configs/detector_noise.json)")
    ap.add_argument("--reject-range", type=float, required=True, help="the range limit Xiaohui chose after the pilot, m")
    ap.add_argument("--out", default=str(ROOT / "configs" / "dv-real.json"))
    ap.add_argument("--evidence", help="where the pilot's analysis is (e.g. course-project/evidence/M1/M1.T8)")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--beyond-pilot-range", action="store_true",
                    help="allow --reject-range beyond the range the pilot found reliable (Xiaohui's explicit decision)")
    ap.add_argument("--force", action="store_true", help="replace an existing --out")
    args = ap.parse_args(argv)
    out = pathlib.Path(args.out)
    if out.resolve() == FROZEN.resolve():
        print("refused: %s is the frozen file; it is never written" % out, file=sys.stderr)
        return 2
    if out.exists() and not args.force:
        print("refused: %s exists (--force replaces it)" % out, file=sys.stderr)
        return 2
    try:
        raw = pathlib.Path(args.noise).read_bytes()
        model = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError) as exc:
        print("refused: --noise %s cannot be read: %s" % (args.noise, exc), file=sys.stderr)
        return 2
    try:
        from beaconmind.schemas import validate
        errors = validate("detector_noise", model)
    except ImportError:
        errors = []
    if errors:
        print("refused: %s is not a valid bm.detector_noise/1 document: %s" % (args.noise, "; ".join(errors[:3])),
              file=sys.stderr)
        return 2
    frozen_doc = json.loads(FROZEN.read_text(encoding="utf-8"))
    evidence = os.path.relpath(pathlib.Path(args.evidence).resolve(), ROOT) if args.evidence else None
    try:
        doc = dv_real.build_real_dv(frozen_doc, dv_real.sha12(FROZEN), model, dv_real._rel(args.noise),
                                    dv_real.sha12(args.noise), args.reject_range, args.date, evidence=evidence,
                                    beyond_pilot=args.beyond_pilot_range)
    except ValueError as exc:
        print("refused: %s" % exc, file=sys.stderr)
        return 2
    try:
        from beaconmind.schemas import validate
        errors = validate("dv", doc)
    except ImportError:
        errors = []
    if errors:
        print("refused: the document would not validate against bm.dv/1: %s" % errors[:3], file=sys.stderr)
        return 2
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    problems = dv_real.check_file(tmp)
    if problems:
        tmp.unlink()
        print("refused: %s" % "; ".join(problems), file=sys.stderr)
        return 2
    os.replace(tmp, out)
    for key in dv_real.CHANGEABLE:
        print("%-22s %8s -> %8s" % (key, frozen_doc["values"][key]["value"], doc["values"][key]["value"]))
    print("wrote %s (sha12 %s); configs/dv.json unchanged (sha12 %s)" % (out, dv_real.sha12(out), dv_real.sha12(FROZEN)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
