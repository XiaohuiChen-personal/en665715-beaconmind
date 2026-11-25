"""The encoder scales of the floor check (2026-11-25), recomputed: from the tape-measured straight (what car.json now
holds) and, for comparison, from wall-tag fixes (the kind of estimate commit 75be6fa held). Numbers from
scale-031706.log, floor-030825.log and floor_analysis-output.txt beside this file; geometry from car.json (track
0.1335 m, lens 0.12 m ahead of the axle) and configs/arenas/real-room.json (T03 and the 295 cm wall).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this computation."""
import math

TRACK, LENS = 0.1335, 0.12
# the tape-measured straight: four FORWARD_25 (scale-031706.log)
L = 4518 + 4506 + 4434 + 4471
R = 4675 + 4746 + 4781 + 4674
GYRO = 2.88 + 2.64 + 2.97 + 3.64
# Xiaohui's tape: the lens over the tag pilot's 2.75 m tick on the centre line (ticks are from the baseboard), then
# 1.83 m from the baseboard and 0.19 m left of the line; line frame: x toward the wall, y to the car's left
th = math.radians(GYRO)
lens0, lens1 = (0.0, 0.0), (2.75 - 1.83, 0.19)
axle0 = (lens0[0] - LENS, lens0[1])                                   # heading 0 at the start (on the line)
axle1 = (lens1[0] - LENS * math.cos(th), lens1[1] - LENS * math.sin(th))
chord = math.hypot(axle1[0] - axle0[0], axle1[1] - axle0[1])
arc = chord * (th / 2) / math.sin(th / 2)                             # the same chord on a circular arc
left, right = arc - TRACK / 2 * th, arc + TRACK / 2 * th
print("tape straight: counts L %d R %d, gyro %.2f deg" % (L, R, GYRO))
print("  axle start %s end (%.4f, %.4f) -> chord %.4f m, arc %.4f m (circular arc with the gyro's turn)" % (axle0, axle1[0], axle1[1], chord, arc))
print("  wheel travel L %.4f m, R %.4f m -> L %.0f, R %.0f counts per metre" % (left, right, L / left, R / right))
print("  each 1 cm of tape error changes the arc by %.1f %%" % (100 * 0.01 / arc))
straight = math.hypot(axle1[0] - axle0[0], axle1[1] - axle0[1])
print("  (a straight chord instead of the arc: %.4f m -> L %.0f, R %.0f)" % (straight, L / (straight - TRACK / 2 * th), R / (straight + TRACK / 2 * th)))

# the same straight by wall-tag fixes (floor_analysis-output.txt, S0 and S4; positions from bias-corrected ranges)
def lens_at(x, y, hdg):
    return x + LENS * math.cos(math.radians(hdg)), y + LENS * math.sin(math.radians(hdg))
s0, s4 = lens_at(2.231, 2.960, -84.74), lens_at(2.510, 2.041, -74.19)
# the tape's line in the room frame: from T03 (2.369, 0.071) out of the 295 cm wall (corner (0,0) to (2.95, 0.088))
a = math.atan2(0.088, 2.95)
n = (-math.sin(a), math.cos(a))                                       # into the room
left_dir = (math.cos(a), math.sin(a))                                 # the car's left when it faces the wall
t03 = (2.369, 0.071)
tape0 = (t03[0] + n[0] * (0.015 + 2.75), t03[1] + n[1] * (0.015 + 2.75))
tape1 = (t03[0] + n[0] * (0.015 + 1.83) + left_dir[0] * 0.19, t03[1] + n[1] * (0.015 + 1.83) + left_dir[1] * 0.19)
for name, tag, tape in (("start", s0, tape0), ("end", s4, tape1)):
    d = (tag[0] - tape[0], tag[1] - tape[1])
    along = -(d[0] * n[0] + d[1] * n[1])
    side = d[0] * left_dir[0] + d[1] * left_dir[1]
    print("  lens at the %-5s by tags (%.3f, %.3f), by tape (%.3f, %.3f): %+.3f m along the line, %+.3f m sideways" % (
        name, tag[0], tag[1], tape[0], tape[1], along, side))
dt = (s4[0] - s0[0], s4[1] - s0[1])
print("  lens moved by tags %.3f m along, %.3f m sideways; by tape %.3f along, %.3f sideways" % (
    -(dt[0] * n[0] + dt[1] * n[1]), dt[0] * left_dir[0] + dt[1] * left_dir[1], 2.75 - 1.83, 0.19))

# the first kind of estimate: tag fixes before and after the four straights of F1 (floor_analysis-output.txt)
def scales(p0, p1, counts_l, counts_r):
    chord = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    turn = math.radians(p1[2] - p0[2])
    arc = chord * (turn / 2) / math.sin(turn / 2)
    return chord, arc, counts_l / (arc - TRACK / 2 * turn), counts_r / (arc + TRACK / 2 * turn)
for name, p0, p1, cl, cr in (("F0 -> F1.4", (2.307, 2.979, -89.14), (2.498, 1.947, -75.66), 4881 + 4883 + 4848 + 4856, 5098 + 5148 + 5180 + 5232),
                             ("S0 -> S4", (2.231, 2.960, -84.74), (2.510, 2.041, -74.19), L, R)):
    chord, arc, sl, sr = scales(p0, p1, cl, cr)
    print("tag fixes %s: chord %.4f m, arc %.4f m -> L %.0f, R %.0f counts per metre" % (name, chord, arc, sl, sr))
