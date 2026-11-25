# A third quad-search pass for close tags (`perception/tags.py` `ARUCO_PASSES[2]`), 2026-11-25

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24/25: added the pass, the tests and this note. The real-frame
numbers are the lead agent's measurement on the Spark during Xiaohui Chen's tag pilot; no real frame is in this
repository (they show the room).

## What was seen on real frames

Tag pilot, 2026-11-25, placement A01: tag T03 (id 23) about 0.8 m from the lens, about 240 px wide in the XGA frame,
grey 41 to 189 in its region. `perception/tags.py` with its two passes (pass 1: OpenCV's adaptive-threshold windows
3, 13, 23 px; pass 2: 33 and 53 px) detected it in **3 of 30** frames. Nothing was rejected: OpenCV's quad search never
outlined the tag in the other 27. A third, separate pass with windows 63, 83 and 103 px
(`adaptiveThreshWinSizeMin` 63, `Max` 103, `Step` 20) gave **30 of 30**, with the same median range 0.937 m and bearing
+0.19 degrees as the 3 frames found before, at about 8 ms more per frame on the Spark. (A pass with
`adaptiveThreshConstant` 3 also gave 30 of 30; the window pass was chosen because it follows pass 2's design.)

## The change

`ARUCO_PASSES` gets that pass as its third entry; the comment above it carries the numbers above. Nothing else in the
detector changes: the corner refit, the pose, every rejection rule and their thresholds are as before.

## Why it cannot cost a detection the first two passes make

`find_quads` runs the passes one after another on the same grey picture and keeps a quad of a later pass only when no
earlier pass found a quad with the same id whose centre is within half a side of it. The quads of passes 1 and 2 are
kept exactly as they were, in the same order; pass 3 can only append. `detect_tags` then treats every quad the same
way it did before, so every detection the two passes produce is produced again with the same corners, range and
bearing. What a third pass could add is a detection that was not there before: a tag the earlier passes missed (the
point), or a false read, which then faces the unchanged rules (id range, Hamming distance, decision margin,
reprojection error, height). A far tag is small in the picture, so the large windows matter least there; nothing in
the merge depends on range.

## Checks (simulated frames; `beaconmind/tests/test_perception_tags.py`)

Run on the Mac in two scratch environments, because the Mac's own Python has no OpenCV (so the perception tests skip
there): OpenCV 4.13.0 (the Spark host's version, `ArucoDetector` API) and OpenCV 4.5.5 contrib (the 4.5 function API,
as the `beaconmind-ros` container's 4.5.4). Not run in the container itself: the Spark is reserved for the hands-on
sessions.

| Check | OpenCV 4.13.0 | OpenCV 4.5.5 |
| --- | --- | --- |
| `test_a_close_low_contrast_blurred_tag_needs_the_largest_windows`: T03 at 0.937 m, black 131 / white 149 on a wall of 150, blur 2 px, noise 2, JPEG 62, 20 seeds: accepted by passes 1+2 / by all three | 3 / 20 of 20 | 0 / 19 of 20 |
| `test_a_later_pass_never_loses_or_moves_an_earlier_find`: the range grid (0.4 to 3.0 m, bearings to ±20°, tag turned 25°, real-like blur, noise and JPEG; 49 frames) and far pairs at 2.0 to 3.5 m in two looks (8 frames): quads / detections / detections at 2 m or more, two passes -> three | 65 -> 65 / 65 -> 65 / 34 -> 34; every two-pass quad first and unchanged | the same |
| pass 3 by itself, median time per frame (Mac) | 1.3 ms | 1.4 ms |
| `test_perception_tags.py`, `test_tag_pilot.py`, `test_pilot.py` | 181 passed | 179 passed, 2 skipped |

The synthetic reproduction is of the same failure, not of the same picture: the simulator reaches it at a lower
contrast (18 grey levels) than the room did, with the blur a fixed-focus lens has that close. What it shares with the
real frames is that only windows wider than 53 px outline the tag. At 16 grey levels pass 3 also outlines the tag
but the decision-margin rule rejects it, as before.

## Untested

- The `beaconmind-ros` container's own OpenCV 4.5.4 build (tested: 4.5.5 contrib, the same API generation).
- The real frames on the committed code: the 30 of 30 is the lead's measurement with the same pass added by hand.
- Whether pass 3 adds false reads on real frames of the room: none appeared on the simulated frames, and the
  rejection rules are unchanged.
