# b2-real-05: the second right-wheel stall, the tape, and the day's motors (2026-11-25)

The fifth real B2 batch: commit `19f71e6`, `--slip-sigma 0.3`, 16:50:38 to 17:19:57 UTC. It ran 803 moves, with no
scale or drift halt. Three episodes are done: S5 after 114 steps, S4 after 132, S3 after 141. The batch then halted
at step 19 of episode 4 (S5) on `stall: FORWARD_25: stall_right`.

Xiaohui then found the cause at the car, at about 11:22 CST (CONTEXT.md): "The right wheel was right at the tape on the
carpet. This is the same place where previous halt happens." The tape is the tag pilot's painter's tape. Its centre
line runs along x = 2.369 from under T03 out to y ≈ 3.7, with 20 cm cross strips at the distance marks
(`evidence/M1/M1.T8/PROCEDURE.md`). Xiaohui removed the long centre line and fitted fresh AA cells before `b2-real-06`
(17:29–17:43 UTC, no stall, ended by a Pico dropout). b2-real-06 is used here as the after-the-tape comparison.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this diagnosis, `analyse.py`, `analyse-output.txt`
and `floor-map.svg` from the batches' text records.

**Sources.**
- All are text records, copied read-only from the Spark after `b2-real-06` ended: `data/batches/b2-real-01` … `06`, and
  the recorder sessions' move logs of the floor check, b2-real-02, 03, 04, 05 and 06. The move logs hold each wheel's
  ticks and duty at about 50 Hz.
- No frames were copied. b2-real-01's session was not copied.
- The tracked poses carry their sigma: 0.05 m on most steps, 0.11 m at the b2-real-05 stall. So positions against a
  5 cm tape are good to about a wheel's width, not better.

```
python3 course-project/evidence/M3/M3.T12/batch-runner/b2-real-05/analyse.py floor-map.svg \
  floor-check=course-project/evidence/M3/M3.T6/floor-check-runs/floor-030825.log floor-check=,<floor-check session>/moves \
  b2-real-01=data/batches/b2-real-01 b2-real-02=data/batches/b2-real-02,<session>/moves \
  b2-real-03=data/batches/b2-real-03,<session>/moves b2-real-04=data/batches/b2-real-04,<session>/moves \
  b2-real-05=data/batches/b2-real-05,<session>/moves b2-real-06=data/batches/b2-real-06,<session>/moves
python3 course-project/tools/stall_check.py data/batches/b2-real-05 <b2-real-05 session>
python3 <19f71e6's tools/recompute_truth.py> data/batches/b2-real-05 --slip-sigma 0.3   # and 0; the same for b2-real-06
```

## 1. The motors through the day: neither wheel is weakening

**Each wheel's speed per unit duty** while driven (|duty| ≥ 0.3), medians over each session's FORWARD_25 moves (turns
in brackets). Columns: left, right, time to 90 % of peak (L / R), highest duty (L / R).

| Session (UTC) | Left | Right | Time to 90 % of peak (L / R) | Highest duty (L / R) |
| --- | --- | --- | --- | --- |
| floor check (09:02) | 0.164 (0.116) | 0.222 (0.228) | 0.69 / 0.38 s | 0.682 / 0.587 |
| b2-real-02 (12:05) | 0.173 (0.130) | 0.223 (0.232) | 0.63 / 0.46 s | 0.689 / 0.585 |
| b2-real-03 (13:26) | 0.185 (0.148) | 0.227 (0.241) | 0.47 / 0.30 s | 0.669 / 0.579 |
| b2-real-04 (13:59) | 0.190 (0.153) | 0.227 (0.236) | 0.41 / 0.31 s | 0.655 / 0.583 |
| b2-real-05 (16:50) | 0.195 (0.159) | **0.235 (0.244)** | 0.45 / 0.29 s | 0.661 / 0.582 |
| b2-real-06 (17:29, fresh AA cells) | 0.200 (0.154) | 0.240 (0.251) | 0.45 / 0.29 s | 0.666 / 0.581 |

The batches' own per-move diagnostics agree. The median FORWARD_25 took 2.75 s in b2-real-01 and 2.61 s in
b2-real-05 (2.56 s in b2-real-06), with peak speed 0.124 → 0.130 m/s. The right/left distance ratio stayed between
1.00 and 1.04, and turns took 1.01 → 0.97 s.

**Both wheels got slightly more speed per duty as the day went on.** The right wheel never needed more duty, and it
reached its peak sooner than the left in every session. The fresh cells changed little (right 0.235 → 0.240). Nothing
here points to a weakening right motor or a flat pack.

**What did change: the firmware's stall assist.** When a driven wheel stops, the firmware kicks it at duty 0.8.

| Session | Moves | Kicks | Which wheel |
| --- | --- | --- | --- |
| floor check | 23 | 0 | — |
| b2-real-02 | 442 | 3 | left, turns |
| b2-real-03 | 246 | 0 | — |
| b2-real-04 | 132 | 0 | — |
| b2-real-05 | 803 | 11 | 8 left, 3 right, all in turns |
| b2-real-06 | 395 | 9 | 8 right, 1 left, all in turns |

Every kick came at a turn's slow end, at duty 0.30–0.34, and every one got the wheel going again. 12 of the 23 kicks
came in the north strip of the room (y ≥ 3.3 m): 12 in 349 turns there, against 11 in 1,438 turns elsewhere. Only
b2-real-05 and 06 turned there; the earlier batches made one turn there between them.

## 2. The stalled moves

**b2-real-05, ep04 step 18, FORWARD_25 → `stall_right`.** From the move's telemetry and `stall_check.py`
(`analyse-output.txt` §1c, §2b):
- **Before the stop:** the move cruised normally, left 0.137 m/s at duty 0.62, right 0.134 m/s at duty 0.56.
- **At the stop:** in the slow-down at its end, the right wheel fell from 0.110 m/s at duty 0.36 to 0.070, 0.017,
  then 0.000 m/s at duty 0.42. Meanwhile the left wheel still turned at 0.08–0.07 m/s.
- **No assist kick came:** the move was stopped as a stall (the 0.2 s stall window) before any kick.
- **`stall_check.py`:** gradual deceleration, the other wheel at 0.07 m/s, the gyro turning 4.2° while the wheel stood,
  no cut-off, no bump, 1.34 m inside the driving area. Verdict "marginal-duty stall, clear of everything".
- **Batch diagnostics:** 2.37 s, 0.227 m achieved (left 0.236 m, right 0.218 m), gyro −5.8°.
- **Path:** tracked from (2.28, 2.12, −62°) to (2.39, 1.92, −68°), south-east across the tape's centre line.

**b2-real-03, ep02 post step 7, TURN_LEFT_30 → `stall_right`:** a turn at its minimum duty (`../b2-real-03/`), at
(2.41, 1.54), 0.043 m from the centre line.

By the tracked poses the left wheel passed nearer the centre line than the right in both stalls (0.003 against
0.040 m; 0.012 against 0.047 m). That is within the poses' sigma, so the records cannot say which wheel was on the
tape. Xiaohui saw the right one.

**The right wheel's other slow moments in b2-real-05's straights:** one. In the move at 17:07:10 (ep03's transit,
the flagged move pre 24), the right wheel fell to 0.024 m/s at duty 0.31 at the very end of the move. Its tracked
path was 0.024 m from the centre line. Both right-wheel slow moments in straights, the stall included, came with the
right wheel at the tape line. The other 97 FORWARD_25 moves had none.

## 3. Where: slip flags, stalls, kicks, worst range ratios (`floor-map.svg`)

b2-real-01 to 05, with the tape down, by the tracked poses:

| | Within 0.10 m of the tape line | Elsewhere |
| --- | --- | --- |
| straight moves | 49 of 211 (23 %) | 162 |
| `slip_suspected` straights (wheel and gyro yaw disagree > 11°) | **9 (18 % of the moves there)** | 9 (5.6 %) |
| turns | 283 of 1,560 (18 %) | 1,277 (no turn flagged anywhere) |
| stalls | **both** (0.022 and 0.046 m from it) | none |

- **On the tape, the wheel that counts short is the one on the tape.** 11 of the 18 flagged straights had a wheel
  within 0.045 m of the centre line. In each, that wheel counted 7 to 14 % fewer ticks than the other, while the gyro
  disagreed by 11 to 20°.
  - Right wheel on the line: s_right 0.226–0.237 m against s_left 0.255–0.264 m. Seven moves: b2-real-04 pre 50;
    b2-real-05 ep03 pre 24 and 63–66, ep04 pre 83.
  - Left wheel on the line: s_left 0.228–0.233 m against s_right 0.259–0.263 m. Four moves: b2-real-02 ep03 pre 17–18;
    b2-real-04 pre 16–17.
- Off the tape, the other 7 flagged moves all had the right wheel counting less: 0.229–0.236 m against 0.254–0.260 m.
- **The stalls and the flags go with the tape.** Both stalls are within 0.05 m of its centre line, where 18 to 23 % of
  the moves ran (chance for both: about 4 %). The flags are three times as frequent there. This agrees with what
  Xiaohui saw.
- **Removing the long line did not clear the spot.** A turn of b2-real-06's first circle, at (2.35, 2.15) on the
  former centre line, needed three right-wheel kicks. Something is still there: a cross strip, adhesive, or the floor itself.
- **The low range ratios do not go with the tape.** The 12 lowest ratios (0.765–0.825; three of them from b2-real-06)
  are all northward moves, headings 67–138°, 0.29 to 0.73 m from the line (blue on the map).

## 4. Slip by heading, in the light of the tape

b2-real-05's own `slip_by_heading` (manifest, the whole batch; sector by heading, moves × median):
0°: 11 × 0.958 · 45°: 6 × 0.901 · **90°: 14 × 0.823** · 135°: 1 × 0.797 · 225°: 9 × 1.003 · **270°: 16 × 1.029** ·
315°: 7 × 1.001. b2-real-03's was 90°: 3 × 0.846, 180°: 5 × 0.963, 225°: 5 × 0.992. b2-real-01 and 02 predate the
table.

Range ratios split by the tape (range-measured forward moves; "on" = within 0.10 m of the centre line):

| Direction | b2-real-01–05, on the tape | b2-real-01–05, off it | b2-real-06 (long tape removed) |
| --- | --- | --- | --- |
| north (45–135°) | 1 move, 0.907 | **22 moves, median 0.829** | **8 moves, 0.832** |
| south (225–315°) | 10, 0.994 | **27, 1.016** | — |
| east | 5, 0.965 | 17, 0.950 | 7, 0.959–0.972 |
| west | 3, 1.025 | 7, 0.985 | 2 |

**A tag printed at another size** than the world file's 0.16 m would scale every range to that tag, in every
direction. Per tag (`analyse-output.txt` §4b), the deficit follows the motion, not a tag:
- On northward moves both walls ahead read low: the door wall 0.830 (24 pairs), the window wall 0.866 (42).
- The same window-wall tags read near or above 1 in other directions: T05 0.932 east and 1.067 south; T07 0.968 east
  and 0.864 north; T16 0.966 east and 1.026 south.

**So the north/south difference is measured off the tape and after its removal, on tags of several walls, in every
batch that drove north.** That is five of six; b2-real-04 had no northward ranged move. The 06:50 taped test, run on
the tape line, read 0.78 north and 1.04 south. Off the tape the ranges read about 0.83 north and 1.02 south. **The tape
explains the stalls and the wheel-against-gyro flags. It does not explain the northward under-travel.** These records
do not say what does: the carpet's pile, a slope, or the car.

## 5. Truth with the slip sigma on

Method: `tools/recompute_truth.py` as of `19f71e6`, the code both batches ran. Replayed at their own 0.3, the logged
end is reproduced within 0.001 m. b2-real-05 ep01's mid-episode truth differs by up to 0.108 m, because the replay
does not reproduce the batch's tag trust.

| Episode | Agent's final error against the end circle | Tracked end − end circle, as run (0.3) | Replayed without (0) |
| --- | --- | --- | --- |
| b2-real-05 ep01 S5 | 0.062 m | 0.093 m | 0.129 m |
| b2-real-05 ep02 S4 | 0.232 m | 0.083 m | 0.070 m |
| b2-real-05 ep03 S3 | 0.204 m | 0.062 m | 0.071 m |
| b2-real-06 ep01 S4 | 0.072 m | 0.059 m | 0.104 m |
| b2-real-06 ep02 S3 | (the procedure stopped it) | 0.051 m | 0.061 m |

The earlier batches ran without the slip sigma. Their replays with it are in
`../truth-under-slip/real-episodes-recomputed.txt`:

| Episode | Agent's final error against the end circle | Tracked end − end circle, as run (0) | Replayed with 0.3 |
| --- | --- | --- | --- |
| b2-real-01 ep01 S1 | 0.036 m | 0.066 m | 0.063 m |
| b2-real-02 ep01 S1 | 0.013 m | 0.042 m | 0.037 m |
| b2-real-02 ep02 S2 | 0.135 m | 0.076 m | 0.040 m |
| b2-real-03 ep01 S1 | 0.086 m | 0.146 m | 0.091 m |

**Did it help? Yes, a little, and consistently.**
- With the slip sigma, the tracked end is nearer the end circle in 8 of 9 episodes: median 0.010 m nearer, mean
  0.021 m, at most 0.055 m.
- The exception is b2-real-05 ep02, 0.013 m farther.
- The agent's own final errors against the end circle do not depend on it.
- b2-real-05's drift between circles: transits 0.75 to 0.80 tags over odometry, episodes 0.81 to 1.61. The miss over
  path was at most 0.24, well under the 0.6 bound. The range check read 0.98 over 62 forward moves.

## 6. What Xiaohui should check, most likely first

1. **The spot around (2.35–2.41, 1.5–2.2), the old centre line from 1.4 to 2.2 m out from T03's wall.** Both stalls,
   most flagged moves, and b2-real-06's three right-wheel kicks with the long tape already gone are there. Look for
   leftover cross strips (the 1.50, 1.75 and 2.00 m marks are there), adhesive, or a seam or ridge in the carpet.
2. **The right wheel, its tyre and gearbox.** Look for fibre or hair on the axle, a tyre not seated, or rubbing. It is
   the wheel kicked 8 times in b2-real-06 with fresh cells, in three turns 0.3 to 1.0 m off the tape as well as
   on the line. Off the tape it is also the one that counts short in flagged moves. Its speed per duty is not falling (§1), so look for
   drag that comes and goes, not a weak motor.
3. **The floor in the north strip (y ≥ 3.3 m):** a rug edge, a different pile, or a threshold. Turns there needed a
   kick four times as often as elsewhere.
4. **The AA pack: least likely.** Speed per duty rose all day, and the fresh cells changed little.

The stalls come at a move's slowest part: a turn's minimum duty (0.30–0.34), or the slow-down at a straight's end
(duty 0.31–0.42). Raising those minimums is a code question for the lead, not something to check at the car.

## Addendum, after b2-real-07 (12:27 CST): a third stall, away from the tape

This note was written before b2-real-07. That batch ended on a third right-wheel stall: `FORWARD_25`, duty 0.375 at
the stop (the move's highest 0.590), the left wheel at 0.067 m/s, tracked pose (3.16, 2.16, 72°). That is 0.8 m east of
the old tape line, on fresh AA cells (CONTEXT.md; its records are not analysed here). The tape does not explain this
one. **The order in §6 changes:** the right wheel, tyre and gearbox come first. All three stalls are on the right
wheel at the slow end of a move (duty 0.295 in the b2-real-03 turn, 0.375 and 0.418 in the two straights), and in
b2-real-06 the right wheel needed 8 of the 9 assist kicks.
The tape spot comes second: two stalls and most wheel-against-gyro flags sit there. §1 still holds: the right wheel's
speed per duty did not fall over the day, so the fault comes and goes (drag, a fibre on the axle, a tyre, the
gearbox), and the motor itself is not weakening.
AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this addendum.
