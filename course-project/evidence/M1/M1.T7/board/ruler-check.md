# Board size check (2026-11-18)

Xiaohui showed `checkerboard_12x5_2868x1320.png` full screen in Photos (landscape, controls hidden) and measured with a
**tape measure** (no millimetre ruler at hand), through the glass:

| Span | Expected (1:1 at 460 ppi) | Read | Within ±1.0 mm |
| --- | --- | --- | --- |
| 13 squares, long side | 118.4 mm | about 120 mm | no (+1.6 mm) |
| 6 squares, short side | 54.7 mm | about 55 mm | yes (+0.3 mm) |

Decision (Claude, under the README's own reasoning): keep `square_m = 0.009111`. A tape read through glass is good to
about 1–2 mm; Photos shows a 2868 × 1320 PNG on a 2868 × 1320 screen 1:1, and the 460 ppi pitch agrees with Apple's
diagonal to 0.04 %; a real rescaling would stretch both spans by the same factor, and the short span does not show
it. The square size does not change the intrinsics or the distortion, only distances to the board (M1.T7's distance
check and extrinsics); tag ranges use the tags' own printed size. Phone settings: auto-brightness off, Do Not Disturb
on, auto-lock 5 minutes (the longest this phone offers; tap the screen during the capture).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-18: wrote this record. Xiaohui Chen took the readings.
