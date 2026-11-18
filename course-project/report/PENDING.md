# Placeholders in the report (2026-11-18)

Every `\pending{...}` in `Chen-Project-Report.tex` prints in red as **[PENDING: ...]**. List them with
`python3 course-project/tools/report_assets.py --pending` (7 today). To fill one: add the numbers to
`tools/report_assets.py` from the evidence file (so they stay generated), replace the `\pending{}` with prose that
uses `\bmnum{...}`, rebuild, and delete the row here. The report is 12 full pages with no slack: each filled placeholder should take about the space its red text takes now (about 22 column lines in all), or something else must be cut.

| # | Where | What goes there | Evidence that will supply it | Work-list item |
| --- | --- | --- | --- | --- |
| 1 | Abstract, last sentence | One sentence: the number of recorded real episodes and each arm's final-position error on the real logs | the real-log replay's result file | 3.4, 3.6 |
| 2 | III, Safety | One sentence on the host-side bounded-move executor and the out-of-band STOP as built and tested (stop time, checks passed) | the car executor's and the STOP's evidence under `evidence/M3/` | 2.6, 2.7 |
| 3 | IV-B, Real environment | The room's coverage at the measured 46.9° field of view (one heading; full turn, two tags) and the range limit chosen for real runs (2.0 or 2.5 m) | rerun `tools/room_layout.py` with the measured field of view → `evidence/M3/M3.T10/layout/coverage.txt`; Xiaohui's range-limit decision | 2.4, 2.5 |
| 4 | IV-B, Real environment | The measured tag centres and start pose (real world file); the detector's range and bearing error on real frames | `evidence/M3/M3.T10/` (mounting sheet, world file); `evidence/M1/M1.T8/` | 2.4, 2.5 |
| 5 | V-G, Real-log replay | Number of real episodes driven by B2 and their steps; per arm (B0, B2, Opus, Qwen3.8, Gemma 4) the median final-position error (ground truth: the full-turn resection against the surveyed tags per episode, tape at the batch's first start and last end), with its uncertainty; the same in each simulated rehearsal; the difference (sim-to-real gap) | `evidence/M3/M3.T12/`, `evidence/M3/M3.T19/` (expected folders) | 3.2, 3.4, 3.6 |
| 6 | V-G, Closed loop | Closed-loop episodes: one each of Opus 5.5 and Fable 5.2 in the room simulator, and 2–3 on the car: missions completed, steps, moves refused, emergency stops, final-position error, p95 step latency, cost. If a Fable 5.2 episode is reported, add the model to Table III or name its settings in the text | `evidence/M2/M2.T7/closed-loop/README.md`; the recorded car sessions | 4.1, 3.5 |
| 7 | VI, end | Two sentences: did the simulated ordering of the arms hold on the real logs, how large was the gap, what did the closed loop show | items 5 and 6 | — |

Also to update when the real work lands (not marked in the PDF): the real-car procedure in IV-D and the ground-truth paragraph in IV-C are written as *planned* (batches of episodes with the motor battery left on, software halts, resection ground truth; Xiaohui's approval of 2026-11-18) and must be changed to what was done; Table II's footnote and Fig. 1's dotted validator once the closed loop has run; Fig. 1's dashed nodes (camera relay and detector,
bounded moves, room simulator, ROSA demo, tape ground truth) become solid as each is built; the sentence "No real
episode has been run" in V-G; limitation (1) in V-H; the IV-F confounder "Real car"; Fig. 3's caption if the measured
tag centres replace the nominal ones.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this list with the report rewrite.
