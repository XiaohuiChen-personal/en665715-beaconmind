#!/usr/bin/env python3
"""Tag pilot (plan task M1.T8): range and bearing error of the tag detector against tape truth, from the frames of a
recorded session, and configs/detector_noise.json (bm.detector_noise-1) fitted from them.

The car stands at taped places in front of ONE wall tag while tools/record_session.sh records; this tool never talks
to the camera or the car, it only reads the session's frames/ folder. Operator procedure:
course-project/evidence/M1/M1.T8/PROCEDURE.md. Spark host, /usr/bin/python3 (OpenCV, numpy).

    tag_pilot.py placements --tag-id 15 --out course-project/data/real/tag_pilot_placements.csv
                            [--tag-black-m 0.16] [--tag-height-m 0.23]
        Writes the placement plan, fitted to the calibrated field of view (configs/camera.json) and to the distance
        from which the whole tag is in the picture. --tag-black-m is the black square's edge (the sheet is taken as
        that plus a white border of one eighth on each side); --tag-height-m the tag centre's height above the floor.
    tag_pilot.py mark --placement A05 [--session DIR] [--placements CSV] [--frames 30]
        Run when the car stands at placement A05: waits --settle seconds, takes the next --frames frames the recorder
        saves, detects, prints one line (frames, detected, median range and bearing, error against the tape), and
        appends the frame window to <session>/tag_pilot/marks.csv. --session defaults to the newest session.
    tag_pilot.py analyze --session DIR --placements CSV --evidence course-project/evidence/M1/M1.T8
                         [--out course-project/configs/detector_noise.json]
        Detects in every marked frame, compares with the tape truth, writes frames.csv, per-placement.csv,
        fit-output.txt, dv-findings.md, repeat-check.txt, size-convention.txt and detector_noise.json into --evidence
        (and noise.png when matplotlib is installed), and the model to --out when given.
    tag_pilot.py --selftest [--keep DIR]
        The whole chain on SIMULATED frames (beaconmind.perception.synth); writes nothing into the repository.

Placements CSV (one row per place the car stands): placement, part (A range on the centre line, B bearing, C
incidence, D near limit, E far limit, R repeat), x_m and y_m = the tag centre in base_link by the plan (forward of
the axle midpoint, left of the centre line), measured_x_m and measured_y_m = the operator's tape readings when they
differ from the plan (blank = as planned), incidence_deg (blank = the car is squared to the wall, so the incidence
equals the bearing's size), bearing_trusted (0 = the car's heading was set by eye along a slanted line, so the
bearing error is left out of the fit), tag_id, repeat_of, first_frame and last_frame (blank when `mark` recorded
them), note. Truth: range = hypot(x, y) from the axle midpoint, bearing = atan2(y, x), left positive (contract C1).

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this tool.
"""
import argparse
import csv
import datetime
import json
import math
import os
import re
import statistics
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
COURSE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(COURSE, "beaconmind", "src"))

from beaconmind import camera_model as cm                      # noqa: E402
from beaconmind import detector_model as dm                    # noqa: E402

FIELDS = ["placement", "part", "x_m", "y_m", "measured_x_m", "measured_y_m", "incidence_deg", "bearing_trusted",
          "tag_id", "repeat_of", "first_frame", "last_frame", "note"]
MARK_FIELDS = ["placement", "first_frame", "last_frame", "marked_utc", "n_frames", "n_detected", "median_range_m",
               "median_bearing_deg"]
FRAME_RE = re.compile(r"^(\d+)_(\d+)\.jpg$")
TAG_HEIGHT_M = 0.23            # wall tags: centre 0.23 m above the floor (layout real-room-1)
TAG_HALF_WITH_BORDER_M = 0.10  # 160 mm black + 20 mm white border on each side
FRONT_OVERHANG_M = 0.178       # configs/car.json front_overhang_m (camera cable tip), 2026-10-29


# ------------------------------------------------------------------ the plan

def sheet_half_m(tag_black_m):
    """Half the side of a tag's sheet: the black square plus a white border of one eighth of it on each side."""
    return 0.625 * float(tag_black_m)


def squared_in_view(camera, x_m, y_m, height_m=TAG_HEIGHT_M, half_m=TAG_HALF_WITH_BORDER_M, margin_px=8.0):
    """Whole tag (with border) in the picture when the car is squared to the wall: tag centre at (x, y) in
    base_link, its normal pointing back along -x."""
    rng, bearing = math.hypot(x_m, y_m), math.degrees(math.atan2(y_m, x_m))
    return cm.square_in_view(camera, rng, bearing, height_m, half_m, margin_px, incidence_deg=-bearing)


def max_side_offset(camera, x_m, side, height_m=TAG_HEIGHT_M, half_m=TAG_HALF_WITH_BORDER_M):
    """Largest sideways offset (m, positive number) at forward distance x_m with the whole tag still in the picture;
    side +1 = tag to the car's left, -1 = right. 0.0 when it is not in view even on the centre line."""
    y, step = 0.0, 0.005
    if not squared_in_view(camera, x_m, 0.0, height_m, half_m):
        return 0.0
    while y + step < 3.0 and squared_in_view(camera, x_m, side * (y + step), height_m, half_m):
        y += step
    return y


def plan_rows(camera, tag_id, height_m=TAG_HEIGHT_M, far_m=3.5, tag_black_m=0.16):
    """The placement plan as a list of row dicts, for a tag whose black square is tag_black_m wide and whose centre
    is height_m above the floor."""
    half = sheet_half_m(tag_black_m)
    near = cm.min_full_view_range(camera, height_m, half, 0.0, margin_px=8.0)
    first = math.ceil(near * 20.0) / 20.0                                   # next 5 cm step
    rows = []

    def add(part, x, y=0.0, incidence="", trusted=1, repeat_of="", note=""):
        index = sum(1 for r in rows if r["part"] == part) + 1
        rows.append({"placement": "%s%02d" % (part, index), "part": part, "x_m": "%.3f" % x, "y_m": "%.3f" % y,
                     "measured_x_m": "", "measured_y_m": "", "incidence_deg": incidence, "bearing_trusted": trusted,
                     "tag_id": tag_id, "repeat_of": repeat_of, "first_frame": "", "last_frame": "", "note": note})

    a_dist = [first] + [d for d in (1.00, 1.25, 1.50, 1.75, 2.00, 2.25, 2.50) if d > first + 0.04]
    for x in a_dist:
        add("A", x, note="centre line; whole tag in view from %.2f m" % near if x == first else "centre line")
    for x in (1.50, 2.50):
        for side in (1, -1):
            limit = max_side_offset(camera, x, side, height_m, half)
            for share in (0.5, 0.9):
                y = round(side * share * limit, 2)
                if abs(y) >= 0.05:
                    add("B", x, y, note="tag %.1f deg to the car's %s; car squared to the wall"
                        % (abs(math.degrees(math.atan2(y, x))), "left" if side > 0 else "right"))
    for r in (1.00, 1.50):
        for inc in (30, 45, 60):
            add("C", r, 0.0, incidence=inc, trusted=0,
                note="car on a floor line %d deg off the wall's normal, %.2f m from the tag, pointing at the tag" % (inc, r))
    for x in (first - 0.05, first - 0.10, first - 0.15, first - 0.20):
        if x >= FRONT_OVERHANG_M + 0.03:
            add("D", x, note="near limit: expect the tag's top to leave the picture; stop when two in a row fail")
    for x in (2.75, 3.00, 3.25, 3.50):
        if x <= far_m + 1e-9:
            add("E", x, note="far limit: stop when the rate is under 0.9 or the room ends")
    a_ids = {float(r["x_m"]): r["placement"] for r in rows if r["part"] == "A"}
    for x in (1.00, 2.00):
        if x in a_ids:
            add("R", x, repeat_of=a_ids[x], note="repeat of %s at the end of the session" % a_ids[x])
    return rows


def write_rows(path, rows, fields=FIELDS):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _num(text):
    text = "" if text is None else str(text).strip()
    return float(text) if text else None


def truth_of(row, wall_offset_m=0.0):
    """Truth dict for detector_model.summarize_placement from one placements row: the tape readings where given,
    else the plan; wall_offset_m is added to x (the baseboard's thickness when the tape was butted against it)."""
    x = _num(row.get("measured_x_m"))
    y = _num(row.get("measured_y_m"))
    x = (x if x is not None else float(row["x_m"])) + wall_offset_m
    y = y if y is not None else float(row["y_m"])
    trusted = str(row.get("bearing_trusted", "1")).strip() not in ("0", "false", "False", "no")
    return {"placement": row["placement"], "part": row["part"], "x_m": x, "y_m": y,
            "incidence_deg": _num(row.get("incidence_deg")), "bearing_trusted": trusted,
            "tag_id": int(float(row["tag_id"])) if str(row.get("tag_id", "")).strip() else None,
            "repeat_of": (row.get("repeat_of") or "").strip()}


# ------------------------------------------------------------------ sessions and frames

def newest_session(real_root):
    """Newest session folder (by name: they start with YYYYmmdd-HHMMSS) that has a frames/ folder."""
    names = sorted(n for n in os.listdir(real_root) if os.path.isdir(os.path.join(real_root, n, "frames")))
    if not names:
        raise SystemExit("no session with a frames/ folder under %s" % real_root)
    return os.path.join(real_root, names[-1])


def frame_index(session):
    """{frame number: path} of the recorder's frames (<n>_<host receive time in ns>.jpg)."""
    out = {}
    folder = os.path.join(session, "frames")
    for name in os.listdir(folder):
        m = FRAME_RE.match(name)
        if m:
            out[int(m.group(1))] = os.path.join(folder, name)
    return out


def frame_stamp_ns(path):
    m = FRAME_RE.match(os.path.basename(path))
    return int(m.group(2)) if m else None


def pick_detection(accepted, truth, gate_m=None):
    """The detection of one frame that is the pilot tag, and what else was seen.

    Returns (det or None, wrong_id or None, others). The pilot tag is the accepted detection with the expected id
    nearest to the taped position, if it is within the gate (0.4 m + 0.15 m per metre of range by default): the room's
    other tags, some with the same id, are also in view and must not be mistaken for it. A detection with another id
    inside 0.3 m of the taped position is the pilot tag read with a wrong id."""
    rng = math.hypot(truth["x_m"], truth["y_m"])
    gate = gate_m if gate_m is not None else 0.4 + 0.15 * rng
    best, best_d, wrong, others = None, None, None, 0
    for det in accepted:
        d = math.hypot(det["base_xyz_m"][0] - truth["x_m"], det["base_xyz_m"][1] - truth["y_m"])
        if truth.get("tag_id") is None or det["id"] == truth["tag_id"]:
            if d <= gate and (best is None or d < best_d):
                best, best_d = det, d
            else:
                others += 1
        elif d <= 0.3:
            wrong = det["id"]
        else:
            others += 1
    return best, wrong, others


def detect_frames(session_frames, numbers, truth, camera, tag_black_m, settings=None):
    """Per-frame rows (dicts) for the frame numbers of one placement."""
    import cv2
    from beaconmind.perception import tags
    rows = []
    for index, n in enumerate(numbers):
        path = session_frames.get(n)
        row = {"placement": truth["placement"], "frame_idx": index, "frame": n,
               "file": os.path.basename(path) if path else "", "stamp_ns": frame_stamp_ns(path) if path else "",
               "detected": 0, "id": None, "x_b": "", "y_b": "", "z_b": "", "range_m": "", "bearing_deg": "",
               "decision_margin": "", "hamming": "", "quality": "", "reproj_px": "", "side_px": "", "note": ""}
        image = cv2.imread(path, cv2.IMREAD_GRAYSCALE) if path else None
        if image is None:
            row["note"] = "frame missing or unreadable"
            rows.append(row)
            continue
        if image.shape != (camera.height, camera.width):
            row["note"] = "frame is %dx%d, not the calibrated size" % (image.shape[1], image.shape[0])
            rows.append(row)
            continue
        accepted, rejected = tags.detect_tags(image, camera, tag_size_m=tag_black_m, return_rejected=True,
                                              **(settings or {}))
        det, wrong, _others = pick_detection(accepted, truth)
        if det is not None:
            row.update({"detected": 1, "id": det["id"], "x_b": round(det["base_xyz_m"][0], 4),
                        "y_b": round(det["base_xyz_m"][1], 4), "z_b": round(det["base_xyz_m"][2], 4),
                        "range_m": round(det["range_m"], 4), "bearing_deg": round(det["bearing_deg"], 3),
                        "decision_margin": round(det["decision_margin"], 1), "hamming": det["hamming"],
                        "quality": round(det["quality"], 3), "reproj_px": round(det["reproj_px"], 3),
                        "side_px": round(det["side_px"], 1)})
        elif wrong is not None:
            row["id"] = wrong
            row["note"] = "wrong id"
        elif rejected:
            row["note"] = "rejected: " + ",".join(sorted({"%s(id %d)" % (r["reject"], r["id"]) for r in rejected}))
        rows.append(row)
    return rows


# ------------------------------------------------------------------ mark

def cmd_mark(args):
    session = args.session or newest_session(os.path.join(COURSE, "data", "real"))
    camera = cm.load_camera(args.camera)
    row = None
    if args.placements:
        matches = [r for r in read_rows(args.placements) if r["placement"] == args.placement]
        if not matches:
            raise SystemExit("placement %s is not in %s" % (args.placement, args.placements))
        row = matches[0]
    truth = truth_of(row, args.wall_offset_m) if row else None
    if truth:
        print("%s: tag %s; tape truth x %.3f m, y %+.3f m -> range %.3f m, bearing %+.1f deg"
              % (args.placement, truth["tag_id"], truth["x_m"], truth["y_m"],
                 math.hypot(truth["x_m"], truth["y_m"]), math.degrees(math.atan2(truth["y_m"], truth["x_m"]))), flush=True)
    time.sleep(args.settle)
    have = frame_index(session)
    first = (max(have) + 1) if have else 1
    deadline = time.time() + args.timeout
    while True:
        have = frame_index(session)
        got = [n for n in sorted(have) if n >= first]
        # the newest file may still be being written: use it only once a later one exists, or after the wait below
        if len(got) > args.frames or time.time() > deadline:
            break
        time.sleep(0.2)
    numbers = got[:args.frames]
    if not numbers:
        raise SystemExit("no new frame arrived in %s within %.0f s: is the recorder running with the camera on?"
                         % (os.path.join(session, "frames"), args.timeout))
    if truth:
        rows = detect_frames(have, numbers, truth, camera, args.tag_black_m)
    else:
        # no plan row: the nearest detection of --tag-id (or of any id) stands for the pilot tag
        rows = _detect_free(have, numbers, args.tag_id, camera, args.tag_black_m)
    hits = [r for r in rows if r["detected"]]
    med_r = statistics.median(r["range_m"] for r in hits) if hits else None
    med_b = statistics.median(r["bearing_deg"] for r in hits) if hits else None
    line = "%s frames=%d detected=%d" % (args.placement, len(rows), len(hits))
    if hits:
        line += " median_range=%.3f m median_bearing=%+.2f deg" % (med_r, med_b)
        if truth:
            line += " | error %+.3f m %+.2f deg" % (med_r - math.hypot(truth["x_m"], truth["y_m"]),
                                                   dm.wrap_deg(med_b - math.degrees(math.atan2(truth["y_m"], truth["x_m"]))))
    notes = sorted({r["note"] for r in rows if r["note"]})
    if notes:
        line += " | " + "; ".join(notes)
    print(line, flush=True)
    out_dir = os.path.join(session, "tag_pilot")
    os.makedirs(out_dir, exist_ok=True)
    marks = os.path.join(out_dir, "marks.csv")
    new = not os.path.exists(marks)
    with open(marks, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MARK_FIELDS)
        if new:
            writer.writeheader()
        writer.writerow({"placement": args.placement, "first_frame": numbers[0], "last_frame": numbers[-1],
                         "marked_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "n_frames": len(rows), "n_detected": len(hits),
                         "median_range_m": "" if med_r is None else "%.4f" % med_r,
                         "median_bearing_deg": "" if med_b is None else "%.3f" % med_b})
    print("recorded frames %d-%d in %s" % (numbers[0], numbers[-1], marks), flush=True)
    return 0


def _detect_free(have, numbers, tag_id, camera, tag_black_m):
    """mark without a plan row: per frame, the nearest accepted detection (of tag_id when given)."""
    import cv2
    from beaconmind.perception import tags
    rows = []
    for index, n in enumerate(numbers):
        image = cv2.imread(have[n], cv2.IMREAD_GRAYSCALE)
        row = {"placement": "", "frame_idx": index, "frame": n, "detected": 0, "note": ""}
        if image is None or image.shape != (camera.height, camera.width):
            row["note"] = "frame unreadable or not the calibrated size"
            rows.append(row)
            continue
        dets = [d for d in tags.detect_tags(image, camera, tag_size_m=tag_black_m) if tag_id is None or d["id"] == tag_id]
        if dets:
            det = min(dets, key=lambda d: d["range_m"])
            row.update({"detected": 1, "id": det["id"], "range_m": det["range_m"], "bearing_deg": det["bearing_deg"]})
        rows.append(row)
    return rows


# ------------------------------------------------------------------ analyze

def windows_of(rows, marks_path):
    """{placement: (first_frame, last_frame)}: the placements file's own columns win; otherwise the LAST mark of
    that placement (a placement marked again replaces its earlier window)."""
    out = {}
    if marks_path and os.path.exists(marks_path):
        for mark in read_rows(marks_path):
            out[mark["placement"]] = (int(mark["first_frame"]), int(mark["last_frame"]))
    for row in rows:
        a, b = _num(row.get("first_frame")), _num(row.get("last_frame"))
        if a is not None and b is not None:
            out[row["placement"]] = (int(a), int(b))
    return out


def dv_values():
    try:
        from beaconmind.dv import load_dv
        return load_dv()
    except Exception as exc:                                    # the file is optional for this tool
        print("note: configs/dv.json not read (%s); the design-value comparison is skipped" % exc)
        return {}


def analyze(session, placements_path, evidence, out=None, marks=None, camera_path=None, tag_black_m=0.16,
            wall_offset_m=0.0, rate_threshold=0.9, bias_limit_m=0.10, log_name=None, date=None, simulated=False,
            settings=None, quiet=False):
    """Run the whole analysis; returns (model dict or None, summaries, report text)."""
    from beaconmind.schemas import validate
    camera = cm.load_camera(camera_path) if not isinstance(camera_path, cm.Camera) else camera_path
    rows = read_rows(placements_path)
    marks = marks or os.path.join(session, "tag_pilot", "marks.csv")
    windows = windows_of(rows, marks)
    have = frame_index(session)
    os.makedirs(evidence, exist_ok=True)
    frame_rows, summaries, skipped = [], [], []
    for row in rows:
        truth = truth_of(row, wall_offset_m)
        if row["placement"] not in windows:
            skipped.append(row["placement"])
            continue
        a, b = windows[row["placement"]]
        per_frame = detect_frames(have, list(range(a, b + 1)), truth, camera, tag_black_m, settings)
        frame_rows.extend(per_frame)
        summary = dm.summarize_placement(per_frame, truth)
        summary["repeat_of"] = truth["repeat_of"]
        summary["x_m"], summary["y_m"] = truth["x_m"], truth["y_m"]
        hits = [r for r in per_frame if r["detected"]]
        summary["range_median"] = statistics.median(r["range_m"] for r in hits) if hits else None
        summary["bearing_median"] = statistics.median(r["bearing_deg"] for r in hits) if hits else None
        summary["quality_median"] = statistics.median(r["quality"] for r in hits) if hits else None
        summary["side_px_median"] = statistics.median(r["side_px"] for r in hits) if hits else None
        summary["z_median"] = statistics.median(r["z_b"] for r in hits) if hits else None
        summaries.append(summary)
    frame_fields = ["placement", "frame_idx", "frame", "file", "stamp_ns", "detected", "id", "x_b", "y_b", "z_b",
                    "range_m", "bearing_deg", "decision_margin", "hamming", "quality", "reproj_px", "side_px", "note"]
    write_rows(os.path.join(evidence, "frames.csv"), frame_rows, frame_fields)

    def fmt(v, spec="%.4f"):
        return "" if v is None else spec % v

    table = [{"placement": s["placement"], "part": s["part"], "x_m": "%.3f" % s["x_m"], "y_m": "%.3f" % s["y_m"],
              "range_true": "%.4f" % s["range_true"], "bearing_true": "%.3f" % s["bearing_true"],
              "incidence_deg": "%.1f" % s["incidence_deg"], "n_frames": s["n_frames"], "n_detected": s["n_detected"],
              "rate": "%.3f" % s["rate"], "n_wrong_id": s["n_wrong_id"], "range_median": fmt(s["range_median"]),
              "range_err_median": fmt(s["range_err_median"]), "range_err_std": fmt(s["range_err_std"]),
              "bearing_median": fmt(s["bearing_median"], "%.3f"),
              "bearing_err_median_deg": fmt(s["bearing_err_median_deg"], "%.3f"),
              "bearing_err_std_deg": fmt(s["bearing_err_std_deg"], "%.3f"),
              "bearing_trusted": int(s["bearing_trusted"]), "tag_height_median_m": fmt(s["z_median"], "%.3f"),
              "side_px_median": fmt(s["side_px_median"], "%.1f"), "quality_median": fmt(s["quality_median"], "%.2f"),
              "window_5_3": "%.3f" % dm.window_success_probability(s["flags"], 5, 3),
              "reliable": int(dm.is_reliable(s, rate_threshold, bias_limit_m))} for s in summaries]
    write_rows(os.path.join(evidence, "per-placement.csv"), table, list(table[0].keys()) if table else ["placement"])

    fit_set = [s for s in summaries if s["part"] != "R"]
    dv = dv_values()
    proposed = (int(dv.get("obs_frames", 5)), int(dv.get("obs_min_frames", 3)))
    label = "SIMULATED " if simulated else ""
    lines = ["%sTag pilot analysis (tools/tag_pilot.py analyze), %s" % (label, datetime.date.today().isoformat()),
             "session: %s" % os.path.basename(os.path.normpath(session)),
             "camera: %s (%d x %d, fx %.1f, yaw %+.2f deg, pitch %+.2f, roll %+.2f)"
             % (os.path.basename(camera.source) or "given", camera.width, camera.height, camera.fx, camera.yaw_deg,
                camera.pitch_deg, camera.roll_deg),
             "tag black square: %.4f m; wall offset added to x: %.3f m" % (tag_black_m, wall_offset_m),
             "placements analysed: %d (%d frames); without a frame window, skipped: %s"
             % (len(summaries), len(frame_rows), ", ".join(skipped) or "none"), ""]
    lines.append("%-5s %-4s %7s %8s %5s %5s %9s %8s %9s %8s %6s" % ("place", "part", "range", "bearing", "inc", "rate",
                                                                    "r err", "r sd", "b err", "b sd", "side"))
    for s in summaries:
        lines.append("%-5s %-4s %7.3f %+8.2f %5.1f %5.2f %9s %8s %9s %8s %6s"
                     % (s["placement"], s["part"], s["range_true"], s["bearing_true"], s["incidence_deg"], s["rate"],
                        fmt(s["range_err_median"], "%+.4f"), fmt(s["range_err_std"]),
                        fmt(s["bearing_err_median_deg"], "%+.3f"), fmt(s["bearing_err_std_deg"], "%.3f"),
                        fmt(s["side_px_median"], "%.0f")))
    lines.append("(errors = measured - tape; r in m, b in degrees; sd = frame to frame within the placement)")
    lines.append("")
    model = None
    n_frames = sum(s["n_frames"] for s in fit_set)
    source = {"log": log_name or ("%s%s frames.csv" % (label, os.path.basename(os.path.normpath(session)))),
              "date": date or session_date(session), "n_frames": n_frames, "n_placements": len(fit_set)}
    try:
        model = dm.build_noise_model(fit_set, tag_black_m, source, rate_threshold, bias_limit_m, obs_window=proposed)
    except ValueError as exc:
        lines.append("NO MODEL: %s" % exc)
    if model is not None:
        errors = validate("detector_noise", model)
        if errors:
            raise SystemExit("the fitted model does not validate against bm.detector_noise-1: %s" % errors)
        with open(os.path.join(evidence, "detector_noise.json"), "w", encoding="utf-8") as handle:
            json.dump(model, handle, indent=1)
            handle.write("\n")
        if out:
            os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
            with open(out, "w", encoding="utf-8") as handle:
                json.dump(model, handle, indent=1)
                handle.write("\n")
        (window, hits), verdict, worst = dm.choose_window(fit_set, proposed, target=0.95, rate_threshold=rate_threshold,
                                                          bias_limit_m=bias_limit_m)
        rb, rs, bs = model["range_bias_m"], model["range_sigma_m"], model["bearing_sigma_deg"]
        lines += ["model (bm.detector_noise-1)%s:" % (" -- SIMULATED, not a measurement" if simulated else ""),
                  "  range bias  = %+.4f %+.4f * r  m" % (rb["a"], rb["b"]),
                  "  range sigma = %.4f + %.4f * r  m   (1 m: %.3f, 2 m: %.3f, 3 m: %.3f)"
                  % (rs["a"], rs["b"], rs["a"] + rs["b"], rs["a"] + 2 * rs["b"], rs["a"] + 3 * rs["b"]),
                  "  bearing bias = %+.3f deg (median over part A)" % model["bearing_bias_deg"],
                  "  bearing sigma = %.3f + %.3f * r deg (includes the operator's error in squaring the car)" % (bs["a"], bs["b"]),
                  "  reliable range %.2f .. %.2f m (rate >= %.2f and |median range error| <= %.2f m; parts A, D, E)"
                  % (model["min_range_m"], model["max_range_m"], rate_threshold, bias_limit_m),
                  "  max incidence %.1f deg" % model["max_incidence_deg"],
                  "  obs_frames / obs_min_frames = %d / %d (%s; worst window probability %s)"
                  % (window, hits, verdict, fmt(worst, "%.3f")), ""]
        within = [s["bearing_err_std_deg"] for s in fit_set if s["bearing_err_std_deg"] is not None and dm.is_reliable(s)]
        if within:
            lines.append("frame-to-frame bearing sd, median over reliable placements: %.3f deg (the detector alone)"
                         % statistics.median(within))
        within_r = [(s["range_true"], s["range_err_std"]) for s in fit_set if s["range_err_std"] is not None and dm.is_reliable(s)]
        if within_r:
            lines.append("frame-to-frame range sd by placement: " + ", ".join("%.2f m: %.4f" % p for p in sorted(within_r)))
        bias = model["bearing_bias_deg"]
        part_a = [s["bearing_err_median_deg"] for s in fit_set
                  if s["part"] == "A" and s["bearing_trusted"] and dm.is_reliable(s, rate_threshold, bias_limit_m)]
        spread = statistics.stdev(part_a) if len(part_a) > 1 else None
        stderr = spread / math.sqrt(len(part_a)) if spread is not None else None
        if spread is not None:
            lines.append("part-A bearing errors: %d placements, sd between placements %.2f deg (mostly how well the car "
                         "was squared to the wall each time), so the bias is known to about +-%.2f deg"
                         % (len(part_a), spread, stderr))
        if abs(bias) > 1.0 and (stderr is None or abs(bias) > 2.0 * stderr):
            lines.append("CAMERA YAW (plan step 10): the part-A bearing bias is %+.2f deg, beyond 1.0. It is the camera's yaw "
                         "misalignment: set extrinsics.yaw_deg = %.2f - (%+.2f) = %.2f in configs/camera.json (record old "
                         "and new), then run analyze again." % (bias, camera.yaw_deg, bias, camera.yaw_deg - bias))
        elif abs(bias) > 1.0:
            lines.append("camera yaw: the part-A bearing bias is %+.2f deg, beyond 1.0, but not clear of its own "
                         "uncertainty (+-%.2f deg): repeat part A with the car squared more carefully before changing "
                         "extrinsics.yaw_deg (%.2f)." % (bias, stderr, camera.yaw_deg))
        else:
            lines.append("camera yaw: the part-A bearing bias is %+.2f deg, within 1.0; extrinsics.yaw_deg stays %.2f."
                         % (bias, camera.yaw_deg))
        heights = [s["z_median"] for s in fit_set if s["z_median"] is not None and dm.is_reliable(s)]
        if heights:
            lines.append("tag centre height seen: median %.3f m (the tags hang at %.2f m; a difference that grows with "
                         "range points at the camera's pitch)" % (statistics.median(heights), TAG_HEIGHT_M))
    report = "\n".join(lines) + "\n"
    with open(os.path.join(evidence, "fit-output.txt"), "w", encoding="utf-8") as handle:
        handle.write(report)
    write_size_convention(evidence, summaries, simulated, camera.x_m)
    write_repeat_check(evidence, summaries, simulated)
    if model is not None:
        write_dv_findings(evidence, model, fit_set, dv, proposed, simulated, rate_threshold, bias_limit_m)
        plot(evidence, fit_set, model, simulated)
    if not quiet:
        print(report)
        print("written to %s: frames.csv, per-placement.csv, fit-output.txt, size-convention.txt, repeat-check.txt%s"
              % (evidence, ", detector_noise.json, dv-findings.md" if model else ""))
        if out and model:
            print("model written to %s" % out)
    return model, summaries, report


def session_date(session):
    m = re.match(r"^(\d{4})(\d{2})(\d{2})-", os.path.basename(os.path.normpath(session)))
    return "%s-%s-%s" % m.groups() if m else datetime.date.today().isoformat()


def write_size_convention(evidence, summaries, simulated, lens_x_m=0.12):
    """Plan step 7: at the 1.00 m centre-line placement the median range must be 1.00 +- 0.05 m; a factor 1.25 either
    way means the tag size was given with (or without) the white border."""
    cands = [s for s in summaries if s["part"] == "A" and s["range_median"] is not None]
    text = ["%sTag-size convention check (plan M1.T8 step 7)" % ("SIMULATED " if simulated else "")]
    if not cands:
        text.append("no part-A placement with detections: not checked")
    else:
        s = min(cands, key=lambda c: abs(c["range_true"] - 1.0))
        ratio = s["range_median"] / s["range_true"]
        lens_true = s["range_true"] - lens_x_m
        lens_ratio = (s["range_median"] - lens_x_m) / lens_true
        text.append("placement %s: tape %.3f m, median detected %.3f m, ratio %.3f" % (s["placement"], s["range_true"], s["range_median"], ratio))
        if abs(s["range_median"] - s["range_true"]) <= 0.05:
            text.append("OK: within 0.05 m. tag_size_m is the edge of the black square, as beaconmind.perception.tags uses it.")
        elif abs(lens_ratio - 1.25) < 0.08 or abs(lens_ratio - 0.8) < 0.06:
            text.append("WRONG SIZE: the lens distance is off by about a factor 1.25. The tag size given does not match the "
                        "black square's edge; correct --tag-black-m and run again.")
        else:
            text.append("STOP AND ASK: off by more than 0.05 m and not by the 1.25 factor: the calibration, the lens "
                        "position or the tape reading may be wrong.")
    with open(os.path.join(evidence, "size-convention.txt"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(text) + "\n")


def write_repeat_check(evidence, summaries, simulated):
    by_id = {s["placement"]: s for s in summaries}
    text = ["%sRepeat check (plan M1.T8: the repeated placements must agree with their first runs within 1 cm)"
            % ("SIMULATED " if simulated else "")]
    any_row = False
    for s in summaries:
        first = by_id.get(s.get("repeat_of") or "")
        if s["part"] != "R" or first is None:
            continue
        any_row = True
        if s["range_median"] is None or first["range_median"] is None:
            text.append("%s vs %s: no detection in one of them" % (s["placement"], first["placement"]))
            continue
        diff = s["range_median"] - first["range_median"]
        text.append("%s vs %s: %.4f m and %.4f m, difference %+.4f m: %s"
                    % (s["placement"], first["placement"], s["range_median"], first["range_median"], diff,
                       "OK" if abs(diff) <= 0.01 else "FAIL (the car or the tape marks moved; find out and repeat)"))
    if not any_row:
        text.append("no repeat placement (part R) was recorded")
    with open(os.path.join(evidence, "repeat-check.txt"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(text) + "\n")


def write_dv_findings(evidence, model, summaries, dv, proposed, simulated, rate_threshold, bias_limit_m):
    (window, hits), verdict, worst = dm.choose_window(summaries, proposed, target=0.95, rate_threshold=rate_threshold,
                                                      bias_limit_m=bias_limit_m)
    rs, bs = model["range_sigma_m"], model["bearing_sigma_deg"]
    out = ["# M1.T8 design-value findings%s" % (" (SIMULATED selftest, not a measurement)" if simulated else ""), "",
           "Proposals for M1.T10 only; `configs/dv.json` is not edited here.", "",
           "| Value | In dv.json | Pilot | Verdict |", "| --- | --- | --- | --- |"]

    def row(name, current, found, verdict_text):
        out.append("| `%s` | %s | %s | %s |" % (name, current, found, verdict_text))

    word = {"confirmed": "confirmed", "alternative": "proposed change", "not_met": "NOT met by any tried pair",
            "no_data": "no data"}[verdict]
    row("obs_frames / obs_min_frames", "%s / %s" % (dv.get("obs_frames", "?"), dv.get("obs_min_frames", "?")),
        "%d / %d, worst window probability %s" % (window, hits, "n/a" if worst is None else "%.3f" % worst), word)
    row("obs_settle_s", dv.get("obs_settle_s", "?"), "not measurable with the car standing still",
        "open: compare with the frame latency (M1.T17: p95 237 ms at XGA) and the vibration check of M3.T9")
    limit = dv.get("reject_range_above_m")
    row("reject_range_above_m", limit if limit is not None else "?", "max reliable range %.2f m" % model["max_range_m"],
        "may be raised (decision for Xiaohui)" if limit is not None and model["max_range_m"] > limit + 0.2
        else ("lower it" if limit is not None and model["max_range_m"] < limit else "keep"))
    wall = dv.get("forward_wall_limit_m")
    if wall is not None:
        ok = model["min_range_m"] < wall
        row("forward_wall_limit_m (W2: min reliable range must be below it)", wall,
            "min reliable range %.2f m" % model["min_range_m"],
            "ok" if ok else "FAILS: a tag straight ahead is lost before the wall limit; flag for M1.T10")
    done = dv.get("done_range_m")
    if done is not None:
        row("done_range_m", done, "min reliable range %.2f m" % model["min_range_m"],
            "ok" if model["min_range_m"] < done else "FAILS: the target tag cannot be seen at the done range; flag for M1.T10")
    a, b = dv.get("sigma_range_a_m"), dv.get("sigma_range_b_per_m")
    if a is not None and b is not None:
        row("sigma_range_a_m + sigma_range_b_per_m * r", "%.3f m at 1 m, %.3f m at 2 m" % (a + b, a + 2 * b),
            "%.3f m at 1 m, %.3f m at 2 m" % (rs["a"] + rs["b"], rs["a"] + 2 * rs["b"]),
            "dv is conservative" if rs["a"] + 2 * rs["b"] <= a + 2 * b else "dv is too small")
    sb = dv.get("sigma_bearing_deg")
    if sb is not None:
        row("sigma_bearing_deg", sb, "%.2f deg at 1 m, %.2f deg at 2 m (upper bound)" % (bs["a"] + bs["b"], bs["a"] + 2 * bs["b"]),
            "dv is conservative" if bs["a"] + 2 * bs["b"] <= sb else "dv is too small")
    out += ["", "Range bias line %+.4f %+.4f r m; bearing bias %+.2f deg; max incidence %.0f deg."
            % (model["range_bias_m"]["a"], model["range_bias_m"]["b"], model["bearing_bias_deg"], model["max_incidence_deg"]),
            "", "AI-assisted: tools/tag_pilot.py (Claude Fable 5.2 via Claude Code, 2026-11-18) wrote this table on %s from %s"
            % (datetime.date.today().isoformat(),
               "simulated frames; nothing in it is a measurement." if simulated
               else "the pilot's numbers. The placements and tape readings are Xiaohui Chen's.")]
    with open(os.path.join(evidence, "dv-findings.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(out) + "\n")


def plot(evidence, summaries, model, simulated):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    rb, rs, bs = model["range_bias_m"], model["range_sigma_m"], model["bearing_sigma_deg"]
    for s in summaries:
        if s["range_err_median"] is None:
            continue
        colour = {"A": "tab:blue", "B": "tab:orange", "C": "tab:green", "D": "tab:red", "E": "tab:purple"}.get(s["part"], "grey")
        axes[0].errorbar(s["range_true"], s["range_err_median"], yerr=s["range_err_std"] or 0.0, fmt="o", color=colour, ms=4)
        if s["bearing_trusted"]:
            axes[1].errorbar(s["range_true"], s["bearing_err_median_deg"], yerr=s["bearing_err_std_deg"] or 0.0, fmt="o",
                             color=colour, ms=4)
    xs = [model["min_range_m"], model["max_range_m"]]
    axes[0].plot(xs, [rb["a"] + rb["b"] * x for x in xs], "k-", label="bias line")
    for sign in (1, -1):
        axes[0].plot(xs, [rb["a"] + rb["b"] * x + sign * (rs["a"] + rs["b"] * x) for x in xs], "k--", lw=0.8)
        axes[1].plot(xs, [model["bearing_bias_deg"] + sign * (bs["a"] + bs["b"] * x) for x in xs], "k--", lw=0.8)
    axes[1].plot(xs, [model["bearing_bias_deg"]] * 2, "k-")
    axes[0].set_xlabel("true range from the axle midpoint (m)")
    axes[0].set_ylabel("range error, measured - tape (m)")
    axes[1].set_xlabel("true range from the axle midpoint (m)")
    axes[1].set_ylabel("bearing error (deg)")
    fig.suptitle("%sTag pilot: median error per placement (bars: frame-to-frame sd); lines: bias and +-sigma"
                 % ("SIMULATED: " if simulated else ""), fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(evidence, "noise.png"), dpi=110)
    plt.close(fig)
    return True


def cmd_analyze(args):
    model, _summaries, _report = analyze(args.session, args.placements, args.evidence, out=args.out, marks=args.marks,
                                         camera_path=args.camera, tag_black_m=args.tag_black_m,
                                         wall_offset_m=args.wall_offset_m, rate_threshold=args.rate_threshold,
                                         bias_limit_m=args.bias_limit_m)
    return 0 if model is not None else 1


# ------------------------------------------------------------------ selftest (simulated)

def selftest(keep=None, frames_per_placement=12, seed=7, verbose=True):
    """The chain on simulated frames: a plan, a fake session folder with the recorder's file names, analyze, checks.
    The simulated camera really points 1.5 degrees further left than the camera file says, the operator's placements
    are off by a few millimetres and about a degree, and every tenth frame beyond 2.6 m is blurred beyond reading.
    Returns 0 when every check holds."""
    import cv2
    import numpy as np
    from beaconmind.perception import synth
    from beaconmind.schemas import validate
    rng = np.random.default_rng(seed)
    camera = cm.load_camera()
    true_camera = camera.with_mount(yaw_deg=camera.yaw_deg + 1.5)
    tag_id = 15
    root = keep or tempfile.mkdtemp(prefix="bm-tag-pilot-selftest-")
    session = os.path.join(root, "20261118-000000-SIMULATED-tag-pilot")
    os.makedirs(os.path.join(session, "frames"), exist_ok=True)
    evidence = os.path.join(root, "evidence")
    rows = plan_rows(camera, tag_id)
    n = 0
    t_ns = 1794989156000000000
    first_runs = {}
    for row in rows:
        x, y = float(row["x_m"]), float(row["y_m"])
        inc = _num(row["incidence_deg"])
        # where the car really ended up: a few mm off the marks; heading a degree off (two when aimed by eye)
        if row["repeat_of"]:
            dx, dy, dth = first_runs[row["repeat_of"]]
            dx, dy = dx + rng.normal(0, 0.001), dy + rng.normal(0, 0.001)
        else:
            dx, dy = rng.normal(0, 0.004), rng.normal(0, 0.004)
            dth = rng.normal(0, 1.0 if inc is None else 2.0)
        first_runs[row["placement"]] = (dx, dy, dth)
        xa, ya = x + dx, y + dy
        c, s = math.cos(math.radians(-dth)), math.sin(math.radians(-dth))     # tag position in the turned car's frame
        xt, yt = c * xa - s * ya, s * xa + c * ya
        rng_true, bearing = math.hypot(xt, yt), math.degrees(math.atan2(yt, xt))
        # squared to the wall: the tag's normal points back along the wall's normal, i.e. -x of the unturned car
        normal_yaw = (180.0 - dth) if inc is None else (bearing + 180.0 + inc)
        tag = synth.tag_at(tag_id, rng_true, bearing, TAG_HEIGHT_M)
        tag["normal_yaw_deg"] = normal_yaw
        clean = synth.render_scene(true_camera, [tag], wall=150.0, black=100.0, white=185.0)
        row["first_frame"] = n + 1
        for index in range(frames_per_placement):
            n += 1
            t_ns += 200000000
            unreadable = rng_true > 2.6 and index % 10 == 9
            frame = synth.real_like(clean, rng=rng, blur_sigma_px=6.0 if unreadable else 0.75)
            cv2.imwrite(os.path.join(session, "frames", "%06d_%d.jpg" % (n, t_ns)), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        row["last_frame"] = n
    placements = os.path.join(root, "tag_pilot_placements.csv")
    write_rows(placements, rows)
    model, summaries, report = analyze(session, placements, evidence, camera_path=camera, simulated=True, quiet=True,
                                       log_name="SIMULATED selftest frames (tools/tag_pilot.py --selftest)",
                                       date=datetime.date.today().isoformat())
    by_part = {}
    for s in summaries:
        by_part.setdefault(s["part"], []).append(s)
    near = cm.min_full_view_range(camera, TAG_HEIGHT_M, 0.08, 0.0)
    checks = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    check("a model was fitted", model is not None)
    if model is not None:
        check("the model validates against bm.detector_noise-1", validate("detector_noise", model) == [])
        check("bearing bias shows the 1.5 deg yaw offset", abs(model["bearing_bias_deg"] + 1.5) < 0.7,
              "%+.2f deg" % model["bearing_bias_deg"])
        check("the report proposes the yaw correction (file value minus the bias)",
              ("= %.2f in configs/camera.json" % (camera.yaw_deg - model["bearing_bias_deg"])) in report,
              "%.2f; the simulated camera's true yaw is %.2f" % (camera.yaw_deg - model["bearing_bias_deg"], camera.yaw_deg + 1.5))
        check("range bias within 2 cm over 1-3 m",
              all(abs(model["range_bias_m"]["a"] + model["range_bias_m"]["b"] * r) < 0.02 for r in (1.0, 2.0, 3.0)),
              "%+.4f %+.4f r" % (model["range_bias_m"]["a"], model["range_bias_m"]["b"]))
        check("range sigma at 2 m under 3 cm", model["range_sigma_m"]["a"] + 2 * model["range_sigma_m"]["b"] < 0.03)
        check("min reliable range is the whole-tag distance", near - 0.06 <= model["min_range_m"] <= near + 0.12,
              "%.2f m (black square whole from %.2f m)" % (model["min_range_m"], near))
        check("max reliable range reaches the far placements", model["max_range_m"] >= 3.0, "%.2f m" % model["max_range_m"])
        check("max incidence found in part C", model["max_incidence_deg"] >= 45.0, "%.0f deg" % model["max_incidence_deg"])
        check("p_detect lists every analysed placement", len(model["p_detect"]) == len([s for s in summaries if s["part"] != "R"]))
    check("every placement of parts A, B and C was detected",
          all(s["rate"] >= 0.9 for p in "ABC" for s in by_part.get(p, [])))
    check("the closest near-limit placements lose the tag", any(s["rate"] == 0.0 for s in by_part.get("D", [])))
    check("unreadable frames are counted as misses", any(0.0 < s["rate"] < 1.0 for s in by_part.get("E", [])))
    with open(os.path.join(evidence, "repeat-check.txt"), encoding="utf-8") as handle:
        repeat = handle.read()
    check("repeat placements agree within 1 cm", "OK" in repeat and "FAIL" not in repeat)
    with open(os.path.join(evidence, "size-convention.txt"), encoding="utf-8") as handle:
        check("size convention check passes", "OK: within 0.05 m" in handle.read())
    failed = [c for c in checks if not c[1]]
    if verbose:
        print(report)
        for name, ok, detail in checks:
            print("%s  %s%s" % ("PASS" if ok else "FAIL", name, (" [" + detail + "]") if detail else ""))
        print("selftest %s: %d checks, %d placements, %d SIMULATED frames; files in %s%s"
              % ("FAILED" if failed else "ok", len(checks), len(summaries), n, root, "" if keep else " (temporary)"))
    if not keep and not failed:
        import shutil
        shutil.rmtree(root, ignore_errors=True)
    return 1 if failed else 0


# ------------------------------------------------------------------ command line

def cmd_placements(args):
    camera = cm.load_camera(args.camera)
    if not args.tag_black_m > 0:
        raise SystemExit("--tag-black-m must be positive")
    rows = plan_rows(camera, args.tag_id, args.tag_height_m, args.far_m, args.tag_black_m)
    write_rows(args.out, rows)
    near_black = cm.min_full_view_range(camera, args.tag_height_m, args.tag_black_m / 2.0, 0.0)
    near_page = cm.min_full_view_range(camera, args.tag_height_m, sheet_half_m(args.tag_black_m), 0.0)
    print("%d placements written to %s" % (len(rows), args.out))
    print("field of view %.1f x %.1f deg; a %.0f mm tag %.2f m up, straight ahead, is whole in the picture from %.2f m "
          "(black square) / %.2f m (with its white border) from the axle midpoint"
          % (camera.hfov_deg, camera.vfov_deg, args.tag_black_m * 1000, args.tag_height_m, near_black, near_page))
    for row in rows:
        x, y = float(row["x_m"]), float(row["y_m"])
        print("  %-4s x %.2f m  y %+.2f m  (range %.2f m, bearing %+5.1f deg)%s  %s"
              % (row["placement"], x, y, math.hypot(x, y), math.degrees(math.atan2(y, x)),
                 "  incidence %s deg" % row["incidence_deg"] if row["incidence_deg"] != "" else "", row["note"]))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description="Tag pilot (M1.T8): detector error against tape truth.")
    parser.add_argument("--selftest", action="store_true", help="run the chain on SIMULATED frames")
    parser.add_argument("--keep", help="with --selftest: keep the simulated session and outputs in this folder")
    sub = parser.add_subparsers(dest="command")
    p = sub.add_parser("placements", help="write the placement plan")
    p.add_argument("--out", required=True)
    p.add_argument("--tag-id", type=int, required=True, help="id of the wall tag the pilot uses")
    p.add_argument("--tag-height-m", type=float, default=TAG_HEIGHT_M, help="tag centre above the floor, metres")
    p.add_argument("--tag-black-m", type=float, default=0.16, help="edge of the black square, metres")
    p.add_argument("--far-m", type=float, default=3.5, help="longest distance the room allows")
    p.add_argument("--camera", default=None)
    p.set_defaults(func=cmd_placements)
    p = sub.add_parser("mark", help="record the frame window of one placement and print its detections")
    p.add_argument("--placement", required=True)
    p.add_argument("--session", default=None, help="session folder (default: the newest under data/real)")
    p.add_argument("--placements", default=None, help="the plan, to print the error against the tape")
    p.add_argument("--frames", type=int, default=30)
    p.add_argument("--settle", type=float, default=1.0)
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument("--tag-id", type=int, default=None)
    p.add_argument("--tag-black-m", type=float, default=0.16)
    p.add_argument("--wall-offset-m", type=float, default=0.0)
    p.add_argument("--camera", default=None)
    p.set_defaults(func=cmd_mark)
    p = sub.add_parser("analyze", help="detect, compare with the tape, fit the noise model")
    p.add_argument("--session", required=True)
    p.add_argument("--placements", required=True)
    p.add_argument("--evidence", required=True, help="folder for the tables and reports")
    p.add_argument("--out", default=None, help="write the model here too (course-project/configs/detector_noise.json)")
    p.add_argument("--marks", default=None, help="default: <session>/tag_pilot/marks.csv")
    p.add_argument("--tag-black-m", type=float, default=0.16, help="ruler-measured edge of the black square, metres")
    p.add_argument("--wall-offset-m", type=float, default=0.0,
                   help="added to every x: the baseboard's thickness when the tape was butted against the baseboard")
    p.add_argument("--rate-threshold", type=float, default=0.9)
    p.add_argument("--bias-limit-m", type=float, default=0.10)
    p.add_argument("--camera", default=None)
    p.set_defaults(func=cmd_analyze)
    return parser


def main(argv):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest(keep=args.keep)
    if not args.command:
        parser.error("give a command (placements, mark, analyze) or --selftest")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
