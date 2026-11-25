"""The slip test of 2026-11-25 (recorder session 20261125-064330-slip-test): 4 x FORWARD_25 northward and 4 x
FORWARD_25 southward on the tag pilot's centre line (x about 2.37 m), the lens read on the tape ticks (distance from
the baseboard under T03, perpendicular to the 295 cm wall; good to about 2 cm). The true path of the axle against the
odometry's, with the geometry of the floor check's F4 (lens 0.12 m ahead of the axle; the chord taken as an arc
turning by the gyro's angle).

usage: python3 slip_test.py MOVES_DIR   (the session's moves/ folder, copied read-only from the Spark)

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this recomputation of the slip test."""
import glob, json, math, os, sys

LENS_M = 0.12
# the operator's tape readings (the lead's message of 2026-11-25): lens from, lens to (along the line, metres from the
# baseboard), and where it ended across the line (to the car's left)
RUNS = {"north (away from T03)": {"from": 2.00, "to": 2.75, "left": 0.135, "sign": +1},
        "south (toward T03)": {"from": 3.00, "to": 2.00, "left": 0.135, "sign": -1}}

files = sorted(glob.glob(os.path.join(sys.argv[1], "move_*_FORWARD_25.jsonl")))
results = []
for f in files:
    rows = [json.loads(l) for l in open(f)]
    res = [r["result"] for r in rows if isinstance(r.get("result"), dict) and "achieved_forward_m" in r["result"]][-1]
    results.append((os.path.basename(f).split("_")[1], res))
assert len(results) == 8, len(results)
for (name, run), moves in zip(RUNS.items(), (results[:4], results[4:])):
    odo = sum(r["achieved_forward_m"] for _, r in moves)
    gyro = sum(r["gyro_dyaw_deg"] for _, r in moves)
    along = run["sign"] * (run["to"] - run["from"])            # distance the lens moved along the line, forward
    th = math.radians(gyro)
    axle_end = (along - LENS_M * math.cos(th), run["left"] - LENS_M * math.sin(th))
    axle_start = (-LENS_M, 0.0)
    chord = math.hypot(axle_end[0] - axle_start[0], axle_end[1] - axle_start[1])
    arc = chord * (th / 2) / math.sin(th / 2) if th else chord
    print("%s, moves at %s" % (name, ", ".join(t for t, _ in moves)))
    for t, r in moves:
        print("   %s achieved_forward_m %.4f, counts left %d right %d, gyro %+.2f deg, %.2f s" % (
            t, r["achieved_forward_m"], r["enc_left_ticks"], r["enc_right_ticks"], r["gyro_dyaw_deg"], r["duration_s"]))
    print("   odometry %.4f m, gyro %+.2f deg; lens %.2f -> %.2f m, %.3f m to the left; axle chord %.4f m, arc %.4f m;"
          " true over odometry %.3f (+-%.3f for 2 cm of tape)" % (odo, gyro, run["from"], run["to"], run["left"], chord,
                                                                 arc, arc / odo, 0.02 / odo))
