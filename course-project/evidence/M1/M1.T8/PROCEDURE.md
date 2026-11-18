# M1.T8 tag pilot — operator procedure

What it gives: how far off the detector's range and bearing are at known distances and angles, from how close and how far
a wall tag is usable, and `configs/detector_noise.json`. It also checks the camera's yaw. About 1.5 hours.

This replaces the plan's layout (a tag on a stand moved in front of a parked car): the tags are on the walls now, so **the
car is carried to taped places in front of one wall tag**. Nothing drives. Motor battery **off** for the whole session; the
camera runs from the power bank.

## Numbers to know first (from `configs/camera.json`, computed by `beaconmind.camera_model`)

- The picture is 46.9° wide and 36.2° high (pinhole figures; through the lens model 46.3° × 35.8°: 22.4° to the left of the
  optical axis, 23.9° right, 17.8° up, 18.1° down). The lens is 7.5 cm above the floor and looks 3.9° up.
- A wall tag's centre is 23 cm up, so its top is 31 cm up (33 cm with the white border). **Straight ahead, the whole black
  square is in the picture only from 0.74 m (axle midpoint to wall); with its white border from 0.79 m.** Closer than
  that the top of the tag is cut off and there is no detection. With a level camera it would be 0.86 m / 0.92 m: the 3.9°
  nose-up mount helps.
- Off to the side it needs more room: at 10° left 0.70 m, at 10° right 0.80 m, at 15° left 0.81 m, at 15° right 1.09 m
  (black square; the left/right difference comes from the 4.4° roll and the 2.5° yaw).
- So the plan starts at 0.85 m (the first 5 cm step with a few pixels to spare), and its near-limit part (D) goes down
  to 0.65 m to confirm where detection stops.

## What you need

A tape measure (3.5 m or more), painter's tape, a pen, a ruler, a set square or a large book (for right angles), and the
car with the camera on. The floor in front of the tag clear for 3.6 m, and about 1 m to each side at 2.5 m.

## Which tag

**T03 (ID 23) on the 295 cm wall** is the best choice: its ID is used once, and the room's long side (5 m) is in front
of it. Any tag with 3.6 m of clear floor in front works; avoid IDs 3, 0 and 2 (each is on two tags).

## A. Marks on the floor (about 30 minutes)

1. **Tag check.** With the ruler: the black square's width and height (to 0.5 mm; expected 159.9 mm), and the height of
   the tag's centre above the carpet (expected 23 cm). Write both down.
2. **Baseboard.** Measure how far the baseboard stands out from the wall (ruler on top of it), in mm. The tape will be
   butted against the baseboard, and this number is added to every distance (`--wall-offset-m`).
3. **Centre line** (a line on the floor, square to the wall, starting under the tag's centre):
   - Mark point **W** on the floor at the baseboard, exactly under the tag's centre (hang the tape from the tag centre, or
     use the set square against the wall).
   - Mark **L** and **R** on the floor at the baseboard, 60 cm to the left and right of W.
   - Find the floor point **F** about 2 m out where the tape reads the same length from L and from R (for example 2.10 m
     from both). W–F is square to the wall.
   - Lay painter's tape from W through F out to 3.6 m. Check: at the far end, the distances to L and R still agree within
     1 cm.
4. **Distance marks.** With the tape's end against the baseboard at W, mark on the centre line (a short cross strip at each,
   at right angles, 20 cm wide; label them): **0.65, 0.70, 0.75, 0.80, 0.85, 1.00, 1.25, 1.50, 1.75, 2.00, 2.25, 2.50,
   2.75, 3.00, 3.25, 3.50 m**. (The tool prints the exact list; if it differs, the tool's list wins.)
5. **Side marks** for the bearing part: the tool prints 8 places at 1.50 m and 2.50 m from the wall with a sideways offset
   `y` (for example +0.26 m = the tag is 0.26 m to the car's **left**, so the car stands 0.26 m to the **right** of the
   centre line, seen facing the wall). For each: mark the spot (distance from the baseboard, offset from the centre line),
   and lay a 40 cm strip through it **parallel to the centre line** (same offset at both ends).
6. **Slanted lines** for the incidence part, on whichever side has free floor: from W, lines at 30°, 45° and 60° off the
   centre line. Their end points, measured as (distance from the baseboard, sideways from the centre line): 30° →
   (1.73 m, 1.00 m); 45° → (1.41 m, 1.41 m); 60° → (1.00 m, 1.73 m). Each end point is 2.00 m from W; check that with the
   tape. On each line mark 1.00 m and 1.50 m from W.

## B. Recording (Spark host, in `~/Projects/en665715-beaconmind`)

Claude can type these; Xiaohui places the car and says "placed".

```bash
# 1. start the recorder (camera at XGA q12, frames saved 5 per second)
bash course-project/tools/record_session.sh start tag-pilot --operator "Xiaohui Chen" \
  --note "M1.T8 tag pilot on wall tag T03 id 23; motor battery off; car carried by hand"

# 2. the placement plan, once (prints every place with its distance and offset)
/usr/bin/python3 course-project/tools/tag_pilot.py placements --tag-id 23 \
  --out course-project/evidence/M1/M1.T8/placements.csv

# 3. for every placement, after "placed" (30 frames, about 8 seconds; 0.012 = a 12 mm baseboard, use yours)
bash course-project/tools/record_session.sh run mark-A01 -- /usr/bin/python3 course-project/tools/tag_pilot.py mark \
  --placement A01 --placements course-project/evidence/M1/M1.T8/placements.csv --wall-offset-m 0.012
```

The `mark` line answers with one line, for example
`A02 frames=30 detected=30 median_range=1.008 m median_bearing=-0.42 deg | error -0.004 m -0.42 deg`.

**How the car stands at a placement**

- The **axle line** (the line through the two drive-wheel hubs) is over the cross strip, and the middle of the car is on
  the centre line (or on the side strip). Look straight down at each wheel hub.
- The car points **at the wall, parallel to the centre line**: sight along the car's side against the tape. This matters:
  1 cm of twist across the wheels is 4° of bearing. Take the time; it is the largest error in the bearing numbers.
- On a slanted line (part C) the car stands with its axle midpoint on the 1.00 m or 1.50 m mark and points along the line
  at W.
- Hands and feet out of the picture, then say "placed".
- If the car is not exactly on the mark, do not nudge it for a millimetre: read the tape and put the true numbers in the
  row's `measured_x_m` / `measured_y_m` columns of `placements.csv` (distance from the baseboard; left of the centre
  line positive for the **tag**, that is, the car to the right).

**Order and stop rules**

1. Part A (A01…), then **stop and look at A02 (1.00 m)**: the median range must be 1.00 ± 0.05 m. If it reads about
   1.22 m or 0.82 m, the tag size is wrong by the white border (factor 1.25 on the lens distance); anything else off by
   more than 5 cm: stop and ask, the calibration or a tape reading is wrong.
2. Part B, part C.
3. Part D from the farthest to the nearest; stop after two placements in a row with `detected=0`.
4. Part E outward; stop when `detected` falls under 27 of 30 or the room ends.
5. Part R (repeats of 1.00 m and 2.00 m): must agree with A within 1 cm; if not, the marks or the tape moved.
6. Skip a placement the room does not allow; say so, and it stays out of the analysis.

```bash
# 4. stop the recorder, then analyse (black square size from step A1 in metres; your baseboard number)
bash course-project/tools/record_session.sh stop
/usr/bin/python3 course-project/tools/tag_pilot.py analyze \
  --session course-project/data/real/<the session folder> \
  --placements course-project/evidence/M1/M1.T8/placements.csv \
  --evidence course-project/evidence/M1/M1.T8 \
  --out course-project/configs/detector_noise.json --tag-black-m 0.1599 --wall-offset-m 0.012
```

`analyze` checks the model against the `bm.detector_noise-1` schema itself and refuses to write one that fails.

Then on the Mac: `bash course-project/tools/pull_evidence.sh M1 M1.T8`.

## C. What comes out, and what to decide

In `course-project/evidence/M1/M1.T8/`: `frames.csv` (every frame), `per-placement.csv`, `fit-output.txt` (the table, the
model, the yaw line), `noise.png`, `size-convention.txt`, `repeat-check.txt`, `dv-findings.md`, `detector_noise.json`.

- **Camera yaw.** If `fit-output.txt` says the part-A bearing bias is beyond ±1.0° and clear of its own uncertainty, it
  prints the new `extrinsics.yaw_deg`. Change that one number in `configs/camera.json` (note old and new), run `analyze`
  again. If it says the bias is not clear of its uncertainty, repeat part A with more care in squaring the car.
- **Range limit.** `dv-findings.md` compares the largest reliable range with `reject_range_above_m` (2.0 m). Raising it is
  Xiaohui's decision (it changes the frozen study's setting for real runs only; record it in CONTEXT.md).
- **Near limit.** The smallest reliable range will be about 0.75–0.80 m, above `done_range_m` (0.55 m) and
  `forward_wall_limit_m` (0.35 m). `dv-findings.md` flags this; see `sim-estimate.md` for what it means.

## D. Things that spoil the result

- Bright light or a window behind or beside the tag (glare on the paper); note the lighting in `notes.md`.
- A tag page that is not flat on the wall, or not upright.
- The car on the carpet's edge or on a cable: the lens height and pitch change.
- Touching the camera in its bracket: the mount angles in `camera.json` are then wrong (redo M1.T7 step 9).

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this procedure and computed the distances in it. The
marks, tape readings and placements are Xiaohui Chen's.
