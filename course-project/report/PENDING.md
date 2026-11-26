# Placeholders in the report (2026-11-18; updated 2026-11-25)

Every `\pending{...}` in `Chen-Project-Report.tex` prints in red as **[PENDING: ...]**. List them with
`python3 course-project/tools/report_assets.py --pending` (4 today, one per row below). To fill one: add the numbers to
`tools/report_assets.py` from the evidence file (so they stay generated), replace the `\pending{}` with prose that
uses `\bmnum{...}`, rebuild, and delete the row here. Xiaohui found no page limit on Canvas (2026-11-24); the report
is 17 pages. Keep it tight anyway: every page is read by a grader.

| # | Where | What goes there | Evidence that will supply it | Work-list item |
| --- | --- | --- | --- | --- |
| 1 | Abstract, last sentence but one | Gemma 4's median final-position error on the real logs against the end circle (Qwen3.8 filled 2026-11-25) | `evidence/M3/M3.T19/real-2026-11-25/result.json` when their replays finish (add their keys to `REAL_ARMS` in `tools/report_assets.py`) | 3.6 |
| 5 | V-G, Table VI | The Gemma 4 row (median, IQR, range; n = 8), and Gemma 4 in the paragraphs "The models against the procedure", "Paired differences" and "Other truths and runs" (Qwen3.8 filled 2026-11-25) | the same `result.json` | 3.6 |
| 6 | V-G, "Closed loop on the car" | The three closed-loop Opus 5.5 episodes on the car, in a later session after the right motor is replaced (one filmed): missions completed, steps, moves refused, emergency stops, final-position error against the end circle, step latency, cost | the recorded car sessions and their batch folders | 3.5 |
| 7 | VI, end | Whether Gemma 4 keeps the simulated ordering on the real logs, and what the closed-loop car episodes showed | rows 1, 5 and 6 | — |

Filled on 2026-11-25 and removed from the table: item 2 (III, Safety: the STOP and the host-side moves as checked on
the car, `evidence/M3/M3.T13/smoke.md`, `evidence/M3/M3.T6/`); item 4 (IV-B: the mounted tags, the tag centre height,
the detector on real frames, the confirmed 3.0 m range limit, `evidence/M1/M1.T8/`, `evidence/M3/M3.T10/layout-2/mounting.md`);
item 5's episodes, steps and the B0, B2 and Opus 5.5 results with their uncertainty (Table VI); item 1's and item
7's parts for those arms. Filled on 2026-11-18: item 3 (coverage) and the simulator part of item 6.

**Not a placeholder: not run (decided 2026-11-25; Xiaohui did not object to dropping it).** Row 5 also asked for each
arm's result "in each simulated rehearsal" and the difference (the sim-to-real gap). The room rehearsal ran only B2
and B0 (their gap is in V-G). The model arms' comparison on a simulated room set was not run; V-G says so and what it
would need: simulated room episodes (the rehearsal's logs, or new ones with the pilot's noise model and a
direction-dependent slip) converted like the real logs and replayed through each model arm with the same
final-position metric. Do not fill it with anything else.

**Decisions for Xiaohui (from the report review, 2026-11-25; not marked in the PDF):**
- **Length (review finding 27).** The report is 17 pages against the first-draft guide of 6–8
  (`evidence/M5/requirements.md`); no page limit was found on Canvas. Nothing was cut. The cheapest cuts, if wanted:
  the note rubric's level anchors in IV-C (keep the criteria and weights, point to the rubric file); the list of the
  pre-registration's 22 deviations in IV-E (replace by a pointer to `prereg.md` §8); the camera calibration detail in
  IV-B (keep the field of view and the reprojection error).
- **Author e-mail (finding 32).** The template's author block shows an e-mail line; the report has none. Add one only
  if Xiaohui wants it (agents do not add an address).

Also to update when the car's closed loop has run (not marked in the PDF): Table II's footnote and Fig. 1's dotted
validator (the closed-loop validator has run only in simulation); Section III's "ROSA (1.0.10) is planned as the
demonstration runtime" if ROSA stays unbuilt (Fig. 1 already marks it planned, not built). The slide deck itself
(not the generated `slides/numbers.json`, `outline.md` and `figures/`, which `tools/report_assets.py --slides` wrote
on 2026-11-25 with the un-mirrored room figure) still has to be rebuilt from them.

Done on 2026-11-25 from the old "also to update" list: IV-C's ground truth and IV-D's procedure as run; the R2
sentence (only the demo run is filmed); "No real episode has been run" in V-G; limitation (1); the IV-F confounder
"Real car"; Fig. 3 drawn as seen from above (it was a mirror image) with the mounted tags and a new caption; Fig. 1's
built nodes (camera relay and detector, bounded moves, STOP, room simulator, tag-resection ground truth) drawn as
built.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this list with the report rewrite.
AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: updated it after filling the real-car parts and the first review.
