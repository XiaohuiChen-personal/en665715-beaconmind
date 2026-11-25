"""The reviewer's guard Monte Carlo (probe/guardmc.py), extended: the tracker's slip sigma (0 or 0.3 x d) and three
guard settings: as now (the turn spare 0.05 m at a forward move's start and end, sigma floor 0.05), the spare 0.10 m,
or the sigma floor 0.10 m. Blind stretches of up to 8 moves (forward moves within the 0.75 m cap, and turns), each
allowed by the guard on the BELIEVED pose, while the real car under-travels by heading; the start pose's error is a
fix error of sd 0.06 m. Prints the smallest real turn room and footprint depth, and the stretches where either goes
below 0.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: extended the reviewer's guard Monte Carlo (probe/guardmc.py) with the slip sigma and margin variants."""
import json, math, random, sys
import beaconmind
from beaconmind.car import batch as B, config as C
ROOT = beaconmind.course_root()
WORLD = json.loads((ROOT / "configs/arenas/real-room.json").read_text())
car = C.load_car()
FOOT, SWEEP = [tuple(p) for p in car["corners"]], float(car["sweep_radius_m"])
def factor(h_deg, north, south=1.04, other=0.97):
    sn = math.sin(math.radians(h_deg))
    return other + (north - other) * sn if sn > 0 else other + (south - other) * (-sn)
def run(north, variant, slip, fix_err, n, seed):
    spare = 0.10 if variant == "spare0.10" else 0.05
    floor = 0.10 if variant == "floor0.10" else 0.05
    tm = {"turn0.08": 0.08, "turn0.10": 0.10}.get(variant, 0.03)
    g = B.MoveGuard(WORLD, FOOT, SWEEP, 0.15, 0.25, start_turn_margin_m=spare, turn_spare_m=spare, turn_margin_m=tm)
    rng = random.Random(seed)
    worst_turn = 9.0; worst_foot = 9.0; neg = 0; seqs = 0; moves = 0; refused = 0
    while seqs < n:
        real = {"x_m": rng.uniform(0.7, 3.8), "y_m": rng.uniform(0.05, 5.2), "theta_deg": rng.uniform(-180, 180)}
        if rng.random() < 0.5:
            real = {"x_m": rng.uniform(2.4, 3.7), "y_m": rng.uniform(0.3, 1.8), "theta_deg": rng.uniform(0, 180)}
        a = rng.uniform(0, 2 * math.pi); e = abs(rng.gauss(0, fix_err)) if fix_err else 0.0
        bel = {"x_m": real["x_m"] + e * math.cos(a), "y_m": real["y_m"] + e * math.sin(a), "theta_deg": real["theta_deg"]}
        t = B.PoseTracker(bel, floor, 2.0, floor, slip_sigma_per_m=slip)
        if g.check("TURN_LEFT_30", t.pose, t.sigma_xy_m) is not None or g.axle_depth(real) - SWEEP < 0.03:
            continue
        seqs += 1; blind = 0.0; bad = False
        for _ in range(8):
            act = rng.choice(["FORWARD_25", "FORWARD_25", "FORWARD_10", "TURN_LEFT_30", "TURN_RIGHT_30"])
            d = {"FORWARD_25": 0.25, "FORWARD_10": 0.10}.get(act, 0.0)
            if d and blind + d > 0.75 + 1e-9: continue
            if g.check(act, t.pose, t.sigma_xy_m) is not None:
                refused += 1
                continue
            moves += 1
            if d:
                blind += d
                odo = {"forward_m": d * math.cos(math.radians(1.7)), "left_m": d * math.sin(math.radians(1.7)), "dtheta_deg": 3.4}
                f = factor(real["theta_deg"] + 1.7, north)
                h = math.radians(real["theta_deg"] + 1.7)
                real = {"x_m": real["x_m"] + f * d * math.cos(h), "y_m": real["y_m"] + f * d * math.sin(h), "theta_deg": real["theta_deg"] + 3.4}
            else:
                dth = 30.0 if act == "TURN_LEFT_30" else -30.0
                odo = {"forward_m": 0.012, "left_m": 0.0, "dtheta_deg": dth}
                h = math.radians(real["theta_deg"])
                real = {"x_m": real["x_m"] + 0.012 * math.cos(h), "y_m": real["y_m"] + 0.012 * math.sin(h), "theta_deg": real["theta_deg"] + dth}
            t.predict(odo)
            room = g.axle_depth(real) - SWEEP; foot = g.footprint_depth(real)
            worst_turn = min(worst_turn, room); worst_foot = min(worst_foot, foot)
            if room < 0 or foot < 0: bad = True
        neg += bad
    return {"north": north, "variant": variant, "slip": slip, "stretches": seqs, "moves": moves, "refused": refused,
            "worst_turn_room": round(worst_turn, 4), "worst_foot": round(worst_foot, 4), "stretches_below_0": neg}
if __name__ == "__main__":
    N = int(sys.argv[1]); slip = float(sys.argv[2])
    variants = sys.argv[3].split(",") if len(sys.argv) > 3 else ["now", "spare0.10", "floor0.10"]
    norths = [float(x) for x in sys.argv[4].split(",")] if len(sys.argv) > 4 else [1.0, 0.78, 0.67, 0.55]
    for north in norths:
        for variant in variants:
            print(json.dumps(run(north, variant, slip, 0.06, N, 7)), flush=True)
