# M3.T10 — layout `real-room-2`: the twelve printed tags plus eight (2026-11-18)

Layout C20, chosen by the lead from the layout search (`evidence/M3/M3.T12/`): the twelve 160 mm tags of `real-room-1`
stay where the first mounting sheet puts them, with their IDs, and eight more 160 mm tag36h11 pages are added, centre
0.23 m up like the others. Everything here is **nominal** (targets for mounting); nothing is mounted or measured yet.

| Tag | ID | Wall | Centre, from |
| --- | --- | --- | --- |
| T12 | 1 | angled section | 20 cm from corner 4 |
| T16 | 7 | window wall | 14 cm from corner 3 |
| T14 | 5 | window wall | 125 cm from corner 3 |
| T13 | 4 | window wall | 215 cm from corner 3 |
| T15 | 6 | window wall | 314 cm from corner 3 |
| T19 | 11 | window wall | 404 cm from corner 3 |
| T17 | 8 | 295 cm wall | 200 cm from corner 5 |
| T18 | 9 | 295 cm wall | 269 cm from corner 5 |

Made with `tools/room_layout.py --seed real-room-2 --hfov-deg 46.9 --ranges 2.0 2.5 3.0 --world
configs/arenas/real-room-plus8-160mm-nominal.json --print-pdf … --pdf-pages new --sheet-pdf …` (the full command's output
is `run.txt`; tests in `beaconmind/tests/test_room_layout.py`).

## Files

- `layout.json` — all 20 tags (the added ones carry `"added": true`).
- `mounting.md` — the mounting sheet for all 20, in wall order, new pages marked.
- `plan.png` — the room with the 20 tags; the added ones in blue.
- `checks.txt` — clashes, what could not be checked, narrowed slide ranges, neighbours per wall, and the comparison
  with the world file.
- `coverage.txt` — how much of the driving area sees a tag at range limits 2.0, 2.5 and 3.0 m, at the calibrated field of
  view, for the 20 tags and for the printed 12 alone.
- `pdf-check.txt` — the print file read back: page size, IDs, the black square's size.
- Print files (git-ignored, on the Mac): `data/real/tags/room-layout-real-room-2-new-tags.pdf` (the 8 new pages only,
  same page format as `room-layout-real-room-1.pdf`) and `data/real/tags/room-layout-real-room-2-mounting-sheet.pdf`
  (the sheet for all 20, one page). **Not printed yet.**

## What the checks say

- **World file:** all 20 tags agree with `configs/arenas/real-room-plus8-160mm-nominal.json` in name, ID, x, y (to the
  millimetre), height, normal and size.
- **Clashes: none found** among door trims, wall ends and corners (13 cm from a tag centre), the Ethernet stretch of the
  desk wall, the two outlets whose place is known, neighbouring pages, and the ID rule (IDs 0–29, three IDs used twice,
  the copies at least 1.5 m apart; the eight new IDs are used once each).
- **Not checkable:** the outlets of the 295 cm wall (5 tags, 2 of them new), the window wall (9 tags, 5 new) and the
  desk wall were never located along their walls, so a new page may land on one. The mounting rule covers it (slide the
  page inside its range, write down the centre), but the ranges are tighter now (next point).
- **Tight spots to know before mounting.**
  - T16 (ID 7) is 14 cm from corner 3: its page ends 3 cm from the corner and it can slide only away from it (13–27 cm).
  - T12 (ID 1) is 20 cm from corner 4; the angled section's outlet is estimated (from a photo) at about 50 cm, 13 cm
    beyond the page's edge. If T12 slides beyond about 33 cm it reaches that outlet.
  - Six printed tags lose part of their slide range because a new page is now a neighbour: T03 (ID 23) from 217–257 cm
    to 230–241 cm, T06 (ID 12) to 156–177 cm, T08 (ID 2) to 351–372 cm, T07 (ID 28) to 251–277 cm, T05 (ID 3) to
    50–82 cm, T02 (ID 3) to 128–162 cm. If an outlet forces one of them further, its new neighbour has to move too.
    Closest neighbours: T03 and T18 (32 cm centre to centre, 10 cm of wall between the pages).

## Coverage at the calibrated field of view (46.9°)

The first layout's table (`../layout/coverage.txt`) used the simulator's placeholder 60°. Share of (position, heading)
samples that see at least one / at least two tags, and of positions where a full turn in place sees at least one / two:

| Rule | Range limit | 20 tags: one heading ≥1 / ≥2 | 20 tags: full turn ≥1 / ≥2 | Printed 12: one heading ≥1 / ≥2 | Printed 12: full turn ≥1 / ≥2 |
| --- | --- | --- | --- | --- | --- |
| A. tag centre inside 46.9° (the simulator's rule) | 2.0 m | 41.8 % / 20.3 % | 96.7 % / 86.7 % | 35.4 % / 3.7 % | 96.6 % / 85.0 % |
| | 2.5 m | 55.8 % / 30.0 % | 99.7 % / 98.7 % | 49.8 % / 10.3 % | 99.7 % / 98.7 % |
| | 3.0 m | 67.1 % / 38.5 % | 100.0 % / 100.0 % | 61.6 % / 19.3 % | 100.0 % / 99.9 % |
| B. whole tag sheet in the picture (camera model) | 2.0 m | 30.0 % / 12.7 % | 92.8 % / 80.3 % | 24.3 % / 1.0 % | 91.9 % / 71.5 % |
| | 2.5 m | 43.4 % / 21.8 % | 98.5 % / 96.3 % | 38.0 % / 5.0 % | 98.0 % / 92.8 % |
| | 3.0 m | 54.9 % / 29.6 % | 99.3 % / 98.3 % | 49.9 % / 11.8 % | 98.8 % / 96.7 % |

Rule B asks for the whole sheet (black square and white border) inside the picture through `configs/camera.json`, with
the lens distortion, the mount's roll, pitch and yaw, and the lens 0.12 m ahead of the pose point; it therefore also has
the near limit (about 0.79 m straight ahead) that rule A's 0.25 m ignores. It is the more faithful of the two. Both keep
the 60° incidence limit and the desk as an occluder; neither has random drop-outs. What the eight tags buy is mostly
**two tags in one picture** (at 2.0 m: 1 % → 13 % of samples under rule B), which is what a full pose fix needs.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: extended the layout tool, ran it and the PDF check, and
wrote this note and the generated files beside it. The layout choice is the lead's; the room readings are Xiaohui Chen's.
