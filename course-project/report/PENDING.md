# Placeholders in the report (2026-11-18; updated 2026-11-25)

Every `\pending{...}` in `Chen-Project-Report.tex` prints in red as **[PENDING: ...]**. List them with
`python3 course-project/tools/report_assets.py --pending` (5 today, in the four rows below). To fill one: add the numbers to
`tools/report_assets.py` from the evidence file (so they stay generated), replace the `\pending{}` with prose that
uses `\bmnum{...}`, rebuild, and delete the row here. Xiaohui found no page limit on Canvas (2026-11-24); the report
is 15 pages. Keep it tight anyway: every page is read by a grader.

| # | Where | What goes there | Evidence that will supply it | Work-list item |
| --- | --- | --- | --- | --- |
| 1 | Abstract, last sentence but one | Qwen3.8's and Gemma 4's median final-position error on the real logs against the end circle | `evidence/M3/M3.T19/real-2026-11-25/result.json` when their replays finish (add their keys to `REAL_ARMS` in `tools/report_assets.py`) | 3.6 |
| 5 | V-G, Table VI | The Qwen3.8 and Gemma 4 rows (median, IQR, range; n = 8) and a sentence in "Real-log replay" | the same `result.json` | 3.6 |
| 6 | V-G, "Closed loop on the car" | The three closed-loop Opus 5.5 episodes on the car after the right motor is replaced (one filmed): missions completed, steps, moves refused, emergency stops, final-position error against the end circle, step latency, cost | the recorded car sessions and their batch folders | 3.5 |
| 7 | VI, end | Whether Qwen3.8 and Gemma 4 keep the simulated ordering on the real logs, and what the closed-loop car episodes showed | rows 1, 5 and 6 | — |

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
AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: updated it after filling the real-car parts.
