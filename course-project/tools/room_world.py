#!/usr/bin/env python3
"""Write the room's world file (bm.world/1) from the tag layout (work list 3.1 and 2.5, plan M2.T3 / M3.T10).

Nominal positions (before the tags are measured):
    python3 course-project/tools/room_world.py --out course-project/configs/arenas/real-room-nominal.json

Measured positions (after mounting): the centre of each tag in centimetres along its wall from the corner the
mounting sheet names (evidence/M3/M3.T10/layout/mounting.md), either read from the sheet's last column once it is
filled in, or given on the command line:
    python3 course-project/tools/room_world.py --measured-md course-project/evidence/M3/M3.T10/layout/mounting.md \\
        --measured-by "Xiaohui Chen" --date 2026-11-19 --instrument "tape measure" --error-cm 0.5 \\
        --out course-project/configs/arenas/real-room.json
    python3 course-project/tools/room_world.py --measured T00=158,T01=60,... (all twelve) --measured-by ... --out ...

The world's frame is the survey's (room-survey.md): origin at corner 5, y along the desk wall towards corner 1, x
towards the window wall, metres. arena.polygon_m is the room's walls, arena.drive_polygon_m the driving area (the
room with its desk-wall side moved to the desk's front line), arena.obstacles the desk. IDs, tag size and heights come
from layout.json (the layout that was printed); wall directions and the room come from tools/room_layout.py. The
start pose written is scenario S1 of configs/arenas/real-room-scenarios.json unless --start is given; the simulator
takes any other start pose as an argument. Checks before writing: every tag on its wall, duplicated IDs at least
1.5 m apart, the start pose at least 0.5 m inside the driving area, and the schema (when jsonschema is installed).

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this tool.
"""
import argparse
import json
import math
import pathlib
import re
import sys

TOOLS = pathlib.Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(ROOT / "beaconmind" / "src"))
import room_layout as rl  # noqa: E402

DEFAULT_LAYOUT = ROOT / "evidence" / "M3" / "M3.T10" / "layout" / "layout.json"
DEFAULT_SCENARIOS = ROOT / "configs" / "arenas" / "real-room-scenarios.json"
FALLBACK_START = {"x_m": 2.2, "y_m": 2.6, "theta_deg": 90.0}
MIN_DUP_SEPARATION_M = 1.5   # AGENT-DESIGN D3
MIN_START_INSET_M = 0.5      # plan C7
BASEBOARD_M = 0.12           # room-survey.md: a tag's sheet stands on the baseboard's top

# Layout variants. "printed" is evidence/M3/M3.T10/layout/layout.json as it is. The others add tags (wall key of
# tools/room_layout.py, metres from that wall's corner) and may move printed ones inside their slide ranges; the
# extra positions are the output of `tools/room_rehearsal.py layout-search` (see evidence/M3/M3.T12/rehearsal-b2.md).
PLUS8 = [("angled", 0.20), ("window", 2.15), ("window", 1.25), ("window", 3.14), ("window", 0.14), ("w295", 2.00),
         ("w295", 2.69), ("window", 4.04)]      # in the order the search chose them
LAYOUTS = {
    "printed": {"extra": [], "moves": {}},
    "plus4": {"extra": PLUS8[:4], "moves": {}},
    "plus8": {"extra": PLUS8, "moves": {}},
}


def wall_of(key):
    return next(w for w in rl.WALLS if w["key"] == key)


def tag_xy(wall, along_m):
    ux, uy, length = rl.unit(rl.CORNERS[wall["from"]], rl.CORNERS[wall["to"]])
    if not 0.0 <= along_m <= length:
        raise ValueError("%.3f m is off the %s (%.3f m long)" % (along_m, wall["name"], length))
    x0, y0 = rl.CORNERS[wall["from"]]
    return round(x0 + ux * along_m, 3), round(y0 + uy * along_m, 3)


def parse_measured_md(text):
    """{uid: cm} from the mounting sheet's table: first column the tag, last column the measured centre."""
    out = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 7 and re.fullmatch(r"T\d\d", cells[0]) and cells[-1]:
            m = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*(?:cm)?", cells[-1])
            if not m:
                raise ValueError("cannot read the measured centre of %s: %r" % (cells[0], cells[-1]))
            out[cells[0]] = float(m.group(1))
    return out


def parse_measured_arg(text):
    out = {}
    for part in text.split(","):
        uid, _, cm = part.partition("=")
        out[uid.strip()] = float(cm)
    return out


def layout_tags(layout, variant="printed"):
    """The printed layout's tag rows plus the variant's extra tags (uids T12..., IDs not used by the printed twelve),
    with the variant's moves applied."""
    spec = LAYOUTS[variant]
    rows = [dict(t, along_m=spec["moves"].get(t["uid"], t["along_m"])) for t in layout["tags"]]
    free = [i for i in range(30) if i not in {t["id"] for t in rows}]
    for k, (wall_key, along) in enumerate(spec["extra"]):
        rows.append({"uid": "T%02d" % (len(layout["tags"]) + k), "id": free[k], "wall": wall_key,
                     "from": wall_of(wall_key)["from"], "along_m": along, "z_m": layout["tags"][0]["z_m"]})
    return rows


def build_world(layout, measured_cm=None, measured_meta=None, start=None, world_id=None, variant="printed",
                tag_black_mm=None, centre_z_m=None):
    """The bm.world/1 document. measured_cm: {uid: cm along the wall from the tag's named corner} for every tag, or
    None for the nominal positions. variant: a key of LAYOUTS. tag_black_mm: another tag size than the printed
    160 mm; its centre height defaults to the sheet (1.25 x the black side) standing on the 12 cm baseboard."""
    black = layout["tag"]["black_size_m"] if tag_black_mm is None else tag_black_mm / 1000.0
    resized = abs(black - layout["tag"]["black_size_m"]) > 1e-9
    z_all = centre_z_m if centre_z_m is not None else (round(BASEBOARD_M + 1.25 * black / 2, 4) if resized else None)
    tags = []
    for t in layout_tags(layout, variant):
        wall = wall_of(t["wall"])
        if wall["from"] != t["from"]:
            raise ValueError("%s: layout.json measures from %s, room_layout.py from %s" % (t["uid"], t["from"], wall["from"]))
        along = t["along_m"] if measured_cm is None else measured_cm[t["uid"]] / 100.0
        x, y = tag_xy(wall, along)
        if measured_cm is None and "x_m" in t and t["uid"] not in LAYOUTS[variant]["moves"] \
                and math.hypot(x - t["x_m"], y - t["y_m"]) > 0.002:
            raise ValueError("%s: layout.json and room_layout.py disagree on the nominal position" % t["uid"])
        nx, ny = rl.inward_normal(wall)
        tags.append({"uid": t["uid"], "id": t["id"], "family": layout["tag"]["family"],
                     "black_size_m": black, "border_size_m": round(black / 4, 4),
                     "wall": t["wall"], "x_m": x, "y_m": y, "z_m": t["z_m"] if z_all is None else z_all,
                     "normal_deg": round(math.degrees(math.atan2(ny, nx)), 1)})
    room = [list(rl.CORNERS[c]) for c in rl.POLYGON]
    drive = [[round(v, 4) for v in p] for p in rl.drive_polygon()]
    d = rl.DESK
    desk = [[d["x0"], d["y0"]], [d["x1"], d["y0"]], [d["x1"], d["y1"]], [d["x0"], d["y1"]]]
    ids = [t["id"] for t in tags]
    dups = sorted([t["uid"] for t in tags if t["id"] == i] for i in sorted(set(ids)) if ids.count(i) > 1)
    nominal = measured_cm is None
    name = "real-room" if variant == "printed" and not resized else "real-room-%s-%dmm" % (variant, round(black * 1000))
    return {
        "$comment": "AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: generated by tools/room_world.py from "
                    "evidence/M3/M3.T10/layout/layout.json and room-survey.md. %s wall_height_m is the tag centre "
                    "height plus half a tag (the height the tags need); the room's walls are full-height and were not "
                    "measured. Layout variant: %s; tag black side %.0f mm." % ("NOMINAL tag positions (the mounting sheet's targets, not measurements): for "
                                   "rehearsal only." if nominal else "Tag positions as measured after mounting.",
                                   variant, black * 1000),
        "schema": "bm.world/1", "world_id": world_id or (name + "-nominal" if nominal else name),
        "source": "real", "seed": 1,
        "generator": {"name": "tools/room_world.py (layout %s)" % layout["seed"], "version": "1"},
        "condition": "duplicated",
        "arena": {"shape": "polygon",
                  "size_m": [round(max(p[0] for p in room), 3), round(max(p[1] for p in room), 3)],
                  "wall_height_m": round(max(t["z_m"] for t in tags) + black / 2, 3),
                  "origin": layout["frame"], "polygon_m": room, "drive_polygon_m": drive,
                  "obstacles": [{"name": "desk", "polygon_m": desk, "occludes": True}]},
        "tags": tags, "duplicates": dups, "roof_tags": [],
        "start_pose": dict(start or FALLBACK_START),
        "measured": None if nominal else dict(measured_meta, along_wall_cm=measured_cm),
    }


def check_world(world):
    """Problems as a list of strings (empty = fine)."""
    from beaconmind.envs import kinsim_room as kr
    problems = []
    arena = world["arena"]
    room, drive = [tuple(p) for p in arena["polygon_m"]], [tuple(p) for p in arena["drive_polygon_m"]]
    for name, poly in (("polygon_m", room), ("drive_polygon_m", drive)):
        if not kr.is_convex_ccw(poly):
            problems.append("%s is not convex counter-clockwise" % name)
    for p in drive:
        if kr.inside_depth(room, p) < -1e-6:
            problems.append("driving-area corner %s is outside the room" % (p,))
    for t in world["tags"]:
        if abs(kr.inside_depth(room, (t["x_m"], t["y_m"]))) > 0.005:
            problems.append("%s is not on a wall" % t["uid"])
        nx, ny = math.cos(math.radians(t["normal_deg"])), math.sin(math.radians(t["normal_deg"]))
        if kr.inside_depth(room, (t["x_m"] + 0.05 * nx, t["y_m"] + 0.05 * ny)) <= 0:
            problems.append("%s's normal does not point into the room" % t["uid"])
    by_uid = {t["uid"]: t for t in world["tags"]}
    for group in world["duplicates"]:
        if len(group) != 2:
            problems.append("ID used %d times: %s" % (len(group), group))
            continue
        a, b = by_uid[group[0]], by_uid[group[1]]
        sep = math.hypot(a["x_m"] - b["x_m"], a["y_m"] - b["y_m"])
        if sep < MIN_DUP_SEPARATION_M:
            problems.append("%s and %s share ID %d and are %.2f m apart (< %.1f m)" % (
                group[0], group[1], a["id"], sep, MIN_DUP_SEPARATION_M))
    s = world["start_pose"]
    if kr.inside_depth(drive, (s["x_m"], s["y_m"])) < MIN_START_INSET_M:
        problems.append("the start pose is less than %.1f m inside the driving area" % MIN_START_INSET_M)
    try:
        from beaconmind.schemas import validate
        problems += ["schema: %s" % e for e in validate("world", world)]
    except ImportError:
        pass
    return problems


def default_start(path=DEFAULT_SCENARIOS):
    try:
        doc = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        return dict(doc["scenarios"][0]["start_pose"])
    except (OSError, KeyError, IndexError, ValueError):
        return dict(FALLBACK_START)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--layout", default=str(DEFAULT_LAYOUT))
    ap.add_argument("--out", required=True)
    ap.add_argument("--measured-md", help="the filled-in mounting sheet")
    ap.add_argument("--measured", help="T00=158,T01=60,... centimetres from each tag's named corner")
    ap.add_argument("--measured-by")
    ap.add_argument("--date")
    ap.add_argument("--instrument", default="tape measure")
    ap.add_argument("--error-cm", type=float, help="estimated error of one reading, cm")
    ap.add_argument("--start", help="x_m,y_m,theta_deg in the room frame (default: scenario S1)")
    ap.add_argument("--world-id")
    ap.add_argument("--variant", default="printed", choices=sorted(LAYOUTS))
    ap.add_argument("--tag-mm", type=float, help="black side of the tags in mm (default: the printed 160 mm)")
    ap.add_argument("--centre-z", type=float, help="tag centre height in m (default: the sheet on the baseboard)")
    args = ap.parse_args(argv)
    layout = json.loads(pathlib.Path(args.layout).read_text(encoding="utf-8"))
    measured, meta = None, None
    if args.measured_md or args.measured:
        measured = (parse_measured_md(pathlib.Path(args.measured_md).read_text(encoding="utf-8")) if args.measured_md
                    else parse_measured_arg(args.measured))
        uids = [t["uid"] for t in layout_tags(layout, args.variant)]
        missing, extra = [u for u in uids if u not in measured], [u for u in measured if u not in uids]
        if missing or extra:
            sys.exit("measured centres: missing %s, unknown %s (all %d tags are needed)" % (
                missing or "none", extra or "none", len(uids)))
        if not (args.measured_by and args.date and args.error_cm is not None):
            sys.exit("a measured world needs --measured-by, --date and --error-cm (plan C7 `measured`)")
        meta = {"by": args.measured_by, "date": args.date, "instrument": args.instrument,
                "error_estimate_m": args.error_cm / 100.0,
                "what": "tag centres along each wall from the corner named on the mounting sheet; the room's corners "
                        "are the least-squares fit of evidence/M3/M3.T10/room-survey.md",
                "nominal_shift_cm": {t["uid"]: round(measured[t["uid"]] - t["along_m"] * 100, 1)
                                     for t in layout_tags(layout, args.variant)}}
    start = default_start()
    if args.start:
        x, y, th = (float(v) for v in args.start.split(","))
        start = {"x_m": x, "y_m": y, "theta_deg": th}
    try:
        world = build_world(layout, measured, meta, start, args.world_id, args.variant, args.tag_mm, args.centre_z)
    except ValueError as exc:
        sys.exit(str(exc))
    problems = check_world(world)
    if problems:
        sys.exit("not written:\n  " + "\n  ".join(problems))
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(world, indent=1) + "\n", encoding="utf-8")
    print("wrote %s: %s, %d tags, duplicates %s, start %s" % (out, world["world_id"], len(world["tags"]),
                                                             world["duplicates"], world["start_pose"]))


if __name__ == "__main__":
    main()
