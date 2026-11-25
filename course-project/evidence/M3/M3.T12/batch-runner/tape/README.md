# Was the northward under-travel the pilot's tape? (2026-11-25)

The tag pilot laid painter's tape on the carpet: a centre line along x = 2.369, from under tag T03 out to y ≈ 3.7,
with 20 cm cross strips at its distance marks (`evidence/M1/M1.T8/PROCEDURE.md`). Several findings were made on or near
it:
- The 06:50 slip test, which read 0.78 north and 1.04 south.
- The first two right-wheel stalls.
- Most of the wheel-against-gyro `slip_suspected` flags.

Xiaohui removed the long centre line before `b2-real-06` (CONTEXT.md, 11:2x CST). This note splits every range-measured
forward move of the seven real batches by whether it ran on that line.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this note, `split.py` and `split-output.txt` from the
batches' text records (copied read-only from the Spark; no frames).

```
python3 course-project/evidence/M3/M3.T12/batch-runner/tape/split.py b2-real-01=data/batches/b2-real-01 ... b2-real-07=data/batches/b2-real-07
```

**Method.**
- **Ratio.** The range ratio is tags over odometry: 1.0 means the car covered its counted distance, below 1 it covered
  less.
- **Two sources.** *batch* is each batch's own range check as logged in the manifest's `range_moves` (b2-real-03
  onward). *recomputed* is the same measurement redone here from the detector's records, tag by tag, with the move's
  ratio taken as the median over its tags; it also covers b2-real-01 and 02. Where both exist they agree: the median
  difference over 76 matched moves is 0.000, and 90 % are within 0.010.
- **Two definitions of "on the line".**
  - The lead's: the axle midpoint's x within 0.17 m of 2.37 with y between 0.7 and 3.1, at some point of the move.
  - The b2-real-05 diagnosis's: the move passing within 0.10 m of the centre line.
- **Directions** are 90° sectors centred on north, south, east and west.
- **The tape's state.** b2-real-06 and 07 ran after the long line was removed (cross strips may remain).

## The split (batch source; moves × median ratio)

**Lead's criterion (x within 0.17 m of 2.37, y 0.7–3.1):**

| | North: on | North: off | South: on | South: off | East: on | East: off | West: on | West: off |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b2-real-03 | — | 4 × 0.840 | 3 × 0.991 | 2 × 0.983 | 3 × 0.949 | 5 × 0.905 | 5 × 0.987 | 5 × 0.939 |
| b2-real-04 | — | — | — | — | 1 × 0.991 | — | — | — |
| b2-real-05 | 4 × 0.887 | 15 × 0.821 | 10 × 0.999 | 22 × 1.024 | — | 13 × 0.958 | — | — |
| b2-real-06 (removed) | — | 8 × 0.832 | — | — | — | 7 × 0.959 | 1 × 0.882 | 1 × 0.822 |
| b2-real-07 (removed) | 1 × 0.838 | 1 × 0.803 | 2 × 1.018 | 1 × 0.992 | — | 1 × 0.864 | — | — |
| **pooled, tape down** | **4 × 0.887** | **19 × 0.827** | **13 × 0.996** | **24 × 1.018** | 4 × 0.957 | 18 × 0.951 | 5 × 0.987 | 5 × 0.939 |
| **pooled, tape removed** | 1 × 0.838 | **9 × 0.830** | 2 × 1.018 | 1 × 0.992 | — | 8 × 0.958 | 1 × 0.882 | 1 × 0.822 |

**0.10 m criterion, pooled:**

| | North: on | North: off | South: on | South: off | East: on | East: off | West: on | West: off |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tape down | 1 × 0.907 | **22 × 0.829** | 10 × 0.994 | 27 × 1.016 | 5 × 0.965 | 17 × 0.950 | 3 × 1.025 | 7 × 0.985 |
| tape removed | 1 × 0.838 | **9 × 0.830** | 2 × 1.018 | 1 × 0.992 | 2 × 0.972 | 6 × 0.958 | 1 × 0.882 | 1 × 0.822 |

The recomputed source adds the two earliest batches, all off the line: b2-real-01 north 1 × 0.882, b2-real-02 north
7 × 0.892. Pooled with the tape down, off the line, north reads 26 × 0.845 and south 27 × 1.016 (`split-output.txt`).

## The lead's numbers against this split

The lead's per-batch figures are reproduced exactly from the manifests' `range_moves` with two conventions:
- **Bins:** north means a heading of 30–150°, south 210–330°, and the rest is east/west.
- **Median:** for even n, the upper middle value.

| Batch | Lead's figures | Reproduced |
| --- | --- | --- |
| b2-real-03 | north 0.858 (6), south 0.985 (9), east/west 0.965 (12) | same |
| b2-real-05 | north 0.825 (19), south 1.016 (32), east/west 0.958 (13) | same |
| b2-real-06 | north 0.830 (9), east/west 0.959 (8) | same |

With the 90° sectors used here, b2-real-03 has 4 northward moves at 0.840 instead of 6 at 0.858, and b2-real-06 has 8
at 0.832; the other figures are unchanged.

The lead's on/off comparison pools all directions:

| Batch | Lead: on | Lead: off | Here, lead's criterion: on | Here: off |
| --- | --- | --- | --- | --- |
| b2-real-03 | 0.985 | 0.933 | 11 × 0.985 | 16 × 0.930 (upper middle) |
| b2-real-05 | 0.990 | 0.974 | 14 × 0.990 | 50 × 0.974 |

**I agree with the lead's result, with one caveat about how the comparison is made.**
- **Pooling over directions flatters the line.** Moves on the line were mostly south, east and west; nearly all
  northward moves were off it. Pooled, "on" therefore reads higher partly because it holds few northward moves.
- **Within each direction the conclusion still holds.** No direction is slower on the line:
  - north: 0.887 on (4 moves) against 0.827 off (19);
  - south: 0.996 on against 1.018 off;
  - east: 0.957 on against 0.951 off;
  - west: 0.987 on against 0.939 off.
- **The north–south difference is off the line:** 0.827 north against 1.018 south. It is the same after the line was
  removed: north 0.830 (9 moves).

## The wheel-against-gyro flags

`slip_suspected` flags on straight moves:

| | On the line (lead's criterion) | Off it |
| --- | --- | --- |
| tape down (b2-real-01 to 05) | **11 of 72 (15 %)** | 7 of 139 (5.0 %) |
| tape removed (06, 07) | 0 of 8 | 2 of 36 (5.6 %) |

The 0.10 m criterion gives 9 of 49 (18 %) on and 9 of 162 (5.6 %) off. In each flagged move on the line, the wheel
that rode the line counted 7 to 14 % short (`../b2-real-05/README.md` §3).

## Conclusion

- **The directional slip is real, and it is not the tape.** Off the line, the car covers about 0.83 of its counted
  distance going north (19–22 moves with the tape down) and about 1.02 going south (24–27 moves). After the line was
  removed, north is still 0.830 (9 moves). Per tag, the deficit shows on the tags of both walls a northward move
  ranges, and the same tags read 1.03–1.07 on southward moves, so it is not a mis-sized tag
  (`../b2-real-05/README.md` §4). On the line, no direction reads slower than off it.
- **The 06:50 taped test** read 0.78 north and 1.04 south. It agrees in direction and was a little stronger northward
  than the ranges off the line. It was one run on the tape, so the ranges are the better number.
- **The tape explains the wheel-against-gyro flags,** at three times the rate off the line and none on the old line
  after its removal. **It explains at most two of the three stalls.** The third (b2-real-07, (3.16, 2.16)) is 0.8 m
  east of the line, on fresh cells. The stalls point at the right wheel (`../b2-real-05/stalls.md`), and the tape
  spot may only have been where a binding right wheel gave out first.
