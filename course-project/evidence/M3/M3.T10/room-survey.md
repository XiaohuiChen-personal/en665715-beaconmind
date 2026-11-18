# M3.T10 — room survey, first pass (2026-11-17)

Decision (Xiaohui, 2026-11-17): the real arena is the room the Spark is in. The tags go on the room's own walls; no
2.25 m foam-board square is built. The two closet doors and the entrance door stay closed during runs.

Readings by Xiaohui Chen, tape measure, 2026-11-17. Photos stay on the Mac (`~/Downloads/IMG_8148`–`8151.HEIC`); they
show a private room and are not put in this public repository.

**Corrected sketch (after IMG_8151, 2026-11-17).** Seen from above; `o` marks a low outlet or jack. The first sketch
put the entrance on the 295 cm wall and the 149 cm stretch at the entrance end; both were wrong. The wall called
"entrance wall" in the readings below is the 295 cm wall, which has no door.

Drawn with the desk wall along the bottom (redrawn after Xiaohui read the first version as putting the door off the
desk wall): the entrance door, the switches, the desk and the Ethernet jack are all on the desk wall.

```
                        window wall 427 (2 windows)
     corner 2 ┌────────────────────────────────────┐ corner 3
     [door 2] ┃                                     ╲  angled section 123
              │                                      ╲
              │                                       │ corner 4
   doors wall │              open carpet              │ 295 cm wall
   381        │                                       │ (one outlet,
     [door 1] ┃                                       │  no door)
     corner 1 └─[jack]────[==desk===]──o─sw─[ENTRANCE]┘ corner 5
                   149        142           221
                            desk wall 512
```

`o` outlet (with the Spark's power brick), `sw` light switches, `[jack]` outlet + Ethernet jack with the cable on the
floor (no tags there). The desk is 66 cm deep.

How the photos fit it: IMG_8149 was taken in the entrance doorway (desk to the left, the doors wall far left, the
window wall and the angled section on the right, the 295 cm wall alongside); IMG_8148 from the window side looking at
the desk (entrance frame on the left, in line with the desk wall, hallway behind it); IMG_8150 shows the 149 cm stretch
with door 1's trim close to corner 1; IMG_8151 from door 2 looking across to corner 5, with the desk wall, the entrance
door at the corner, the 295 cm wall (one outlet, a door stop), the angled section (one outlet) and the window wall in
that order.

| Item | Reading |
| --- | --- |
| Entrance wall, desk-wall corner to the angled section | 295 cm |
| Angled section | 195 cm |
| Window wall | 427 cm |
| Doors wall | 381 cm |
| Desk wall: corner with the 295 cm wall → desk, desk, desk → doors-wall corner | 221 + 142 + 149 = 512 cm (Xiaohui, 2026-11-17: the 149 cm stretch with the Ethernet jack is on the doors-wall side, not the entrance side as first assumed) |
| Desk depth, wall to front edge | 66 cm |
| Door widths: entrance, door 1 (desk side), door 2 | 81, 71, 69 cm (trim not stated) |
| Outlet height | 31 cm (bottom edge or centre not stated) |
| Baseboard height | 12 cm |
| Diagonals | not measured (tape too short) |
| Corner 5 (entrance wall / desk wall), chord between the two marks | 139 cm, marks 100 cm along each wall → 88.1° |
| Corner 4 (angled section / entrance wall), chord | 185.5 cm, marks 100 cm along each wall → 136.1° |
| Corner 3 (window wall / angled section), chord | about 184 cm, marks 100 cm along each wall → 133.8° (Xiaohui: "there might be some measurement errors throughout") |
| Ethernet jack and cable (desk wall, 149 cm section) | no tags there (Xiaohui) |

## Check

The five lengths do not close with square corners: square corners at the doors wall would make the angled section
121 cm, not 195 cm. Two different shapes fit all five lengths, for example a square doors wall with the entrance wall
at 106.5° to the desk wall, or a square desk wall with the window wall at 101.5° to the doors wall. The corner angles
are needed before the layout.

With corner 5 known (88.1°), the five lengths leave one free parameter, so one more corner fixes the shape and the others
check it. With corner 5 at 88.1°, the angle between the angled section and the entrance wall comes out at 152–160° and the
window-wall/angled corner at 99–108°, for a desk/doors corner of 88–92°: the "angled section" would bend only about 25°
from the entrance wall's line. Corners 3 and 4 have no door in the way of a 100 cm leg.

**After corner 4 (136.1°).** Solving with all five lengths and corners 4 and 5 gives a strange room: the desk/doors
corner at 99.3° and the doors wall tilted 9° from square (chord at corner 1 would be 152.4 cm). Four readings instead
agree with a simple shape: a 381 × 512 cm rectangle with one corner cut off at about 45°. The entrance wall (295) and
the window wall (427) put the cut's ends 86 and 85 cm from that corner; the cut is then 121 cm long, with corners of
135.3° and 134.7°, against the measured 136.1° (corner 4) and a square corner 5 (measured 88.1°). Only the angled
section's 195 cm disagrees. Next: re-measure the angled section corner to corner, and corner 1 (141.4 cm with
100/100 legs if square, 152.4 cm if the 195 cm stands).

**After corner 3 (133.8°): the shape is still open, and the paragraph above overstated the case.** A least-squares fit
of all eight readings (lengths σ 1.5 cm, chords σ 1 cm) fits every reading within 1.5 cm with the 195 cm kept, at the
price of two unusual corners: desk/doors 100.8° and doors/window 85.7°. The rectangle with a 45° cut (desk/doors and
doors/window both 90°, cut 121 cm) fits every reading except the 195 cm (off by 74 cm) and corner 5's chord (off by
2.4 cm). Corner 3 fits both within tape error (184.4 cm predicted for the rectangle, 182.9 cm for the fit with 195), so
it does not decide. One reading does: the angled section again (121 vs 195 cm), or corner 1 or 2 with 100/100 legs
(about 141 cm if square, about 154 cm or 136 cm if the 195 cm stands).

**Settled after the angled section was re-measured (about 123 cm).** The 195 cm reading was wrong; it is dropped.
Least-squares fit of the eight readings (lengths σ 1.5 cm, chords σ 1 cm): every reading within 0.6 cm (lengths
within 0.1 cm, chords +0.3, +0.6, +0.5 cm), RMS normalised residual 0.28. Frame: origin at the corner of the desk wall
and the 295 cm wall, y along the desk wall towards the doors wall, x towards the window wall. Corners (cm):

| Corner | Point (x, y) cm | Interior angle |
| --- | --- | --- |
| 5: desk wall / 295 cm wall | (0.0, 0.0) | 88.3° |
| 4: 295 cm wall / angled section | (295.0, 8.8) | 137.0° |
| 3: angled section / window wall | (382.4, 95.4) | 134.5° |
| 2: window wall / doors wall | (380.8, 522.4) | 88.6° |
| 1: doors wall / desk wall | (0.0, 512.0) | 91.6° |

Within tape error this is a 381 × 512 cm rectangle with one corner cut at 45°.

**Where the entrance door is: resolved by IMG_8151.** On the desk wall, inside the 221 cm stretch, its trim starting at
corner 5; the 295 cm wall has no door. The shape and the fit above are unchanged (only labels and features moved).
Xiaohui then measured, to the outer edges of the trim: entrance trim 2.5 and 102 cm from corner 5 on the desk wall;
doors wall from corner 1: bare 54 cm, door 1, bare 71 cm, door 2, bare 76 cm (so about 10 cm of trim a side).

## Status of the requests made during the survey

1. Corner angles: corners 3, 4 and 5 measured; with the re-measured cut that fixes the shape (corners 1 and 2 not needed).
2. Door trim edges: measured (above).
3. Outlet positions: not measured; a tag slides up to 20 cm to clear one when mounted, and its measured centre is used.
4. Desk-wall order: corrected by Xiaohui (the 149 cm Ethernet stretch is on the doors-wall side; see the table).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-17: read the room's layout from Xiaohui's photos, wrote this record
and the closure check. Xiaohui Chen took the measurements.

## Tag layout `real-room-1` (2026-11-17)

Generated by `tools/room_layout.py --out evidence/M3/M3.T10/layout --print-pdf data/real/tags/room-layout-real-room-1.pdf`
(output in `layout/run.txt`; tests `beaconmind/tests/test_room_layout.py`). Twelve tag36h11 tags, 160 mm black, IDs by
kinsim's D3 rule (IDs 0–29, three IDs used twice, copies at least 1.5 m apart, at least 1.8 m before sliding). Each
tag's page stands with its bottom edge on the 12 cm baseboard, so every tag centre is 23 cm above the carpet.

| Wall (from) | Tags (nominal centre, cm) |
| --- | --- |
| desk wall (corner 5) | T00 id 15 at 161 (between the entrance trim and the desk) |
| 295 cm wall (corner 5) | T01 id 10 at 58, T02 id 3 at 148, T03 id 23 at 237 |
| angled section (corner 4) | T04 id 0 at 85 (towards corner 3, clear of the outlet seen in IMG_8151) |
| window wall (corner 3) | T05 id 3 at 63, T06 id 12 at 163, T07 id 28 at 264, T08 id 2 at 364 |
| doors wall (corner 1) | T09 id 0 at 27, T10 id 2 at 165 (towards door 1, clear of the outlet), T11 id 29 at 343 |

Duplicated IDs: 3 (T02, T05), 0 (T04, T09), 2 (T08, T10). A tag may slide up to 20 cm along its wall to clear an
outlet; the measured centre is what the world file uses. Print check of every page: the tag decodes as its ID, the
black square is 1888 px at 300 dpi (159.85 mm), the tag centre is 110.0 mm above the page's bottom edge.

**Coverage** (`layout/coverage.txt`, kinsim's visibility rule without drop-outs, 60° field of view): at the 2.0 m
range limit of `configs/dv.json`, 42 % of (position, heading) samples in the room see a tag, against 98 % in the study's
2.25 m arena; but a turn in place finds a tag from 97 % of positions and two different tags from 85 % (2.5 m: 99.7 %
and 98.7 %; the study arena 100 % at every limit). Fifteen tags instead of twelve add about 3 points, so the layout
keeps twelve. Whether real runs keep the 2.0 m limit or move to 2.5 m is for Xiaohui to decide after the tag-accuracy
pilot (work list 2.4, M1.T8) measures range error at 2–2.5 m; it does not change the printed layout.
