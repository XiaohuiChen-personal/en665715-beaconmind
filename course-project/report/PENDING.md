# Placeholders in the report (2026-11-18)

Every `\pending{...}` in `Chen-Project-Report.tex` prints in red as **[PENDING: ...]**. List them with
`python3 course-project/tools/report_assets.py --pending` (6 today). To fill one: add the numbers to
`tools/report_assets.py` from the evidence file (so they stay generated), replace the `\pending{}` with prose that
uses `\bmnum{...}`, rebuild, and delete the row here. The report is 12 full pages. The 12-page budget was an assumption; Xiaohui found no page limit on Canvas (2026-11-24), so the real-car results may take the room they need and material cut in the 2026-11-18 review rounds may return. Keep it tight anyway: every page is read by a grader.

| # | Where | What goes there | Evidence that will supply it | Work-list item |
| --- | --- | --- | --- | --- |
| 1 | Abstract, last sentence | One sentence: the number of recorded real episodes and each arm's final-position error on the real logs | the real-log replay's result file | 3.4, 3.6 |
| 2 | III, Safety | One sentence on the host-side bounded-move executor and the out-of-band STOP as built and tested (stop time, checks passed) | the car executor's and the STOP's evidence under `evidence/M3/` | 2.6, 2.7 |
| 4 | IV-B, Real environment | The measured tag centres and start pose (real world file); the detector's range and bearing error on real frames; **confirm or change the 3.0 m range limit after the tag pilot** (the report calls it provisional: the value used in the rehearsals) | `evidence/M3/M3.T10/` (mounting sheet, world file); `evidence/M1/M1.T8/` | 2.4, 2.5 |
| 5 | V-G, Real-log replay | Number of real episodes driven by B2 and their steps; per arm (B0, B2, Opus, Qwen3.8, Gemma 4) the median final-position error (ground truth: the full-turn resection against the surveyed tags per episode, tape at the batch's first start and last end), with its uncertainty; the same in each simulated rehearsal; the difference (sim-to-real gap) | `evidence/M3/M3.T12/`, `evidence/M3/M3.T19/` (expected folders) | 3.2, 3.4, 3.6 |
| 6 | V-G, Closed loop in simulation (end of the paragraph) | Closed-loop episodes **on the car** (2–3): missions completed, steps, moves refused, emergency stops, final-position error, step latency, cost. The simulator part is filled (2026-11-18): one episode each of B2, Opus 5.5 and Fable 5.2 from `evidence/M2/M2.T7/closed-loop/runs-final/` | the recorded car sessions | 3.5 |
| 7 | VI, end | Two sentences: did the simulated ordering of the arms hold on the real logs, how large was the gap, what did the closed loop show | items 5 and 6 | — |

Filled on 2026-11-18 and removed from the table (the numbers are kept, so 3 is unused): item 3, the room's coverage at the measured 46.9° field of view and the 3.0 m range limit, from `evidence/M3/M3.T10/layout-2/coverage.txt` with the 20-tag layout; and the simulator part of item 6.

Also to update when the real work lands (not marked in the PDF): the real-car procedure in IV-D and the ground-truth paragraph in IV-C are written as *planned* (batches of episodes with the motor battery left on, software halts, resection ground truth; Xiaohui's approval of 2026-11-18) and must be changed to what was done; Table II's footnote and Fig. 1's dotted validator once the closed loop has run; Fig. 1's dashed nodes (camera relay and detector,
bounded moves, room simulator, ROSA demo, tape ground truth) become solid as each is built; the sentence "No real
episode has been run" in V-G; limitation (1) in V-H; the IV-F confounder "Real car"; Fig. 3's caption if the measured
tag centres replace the nominal ones.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this list with the report rewrite.
