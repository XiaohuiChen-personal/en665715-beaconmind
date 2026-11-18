# M5.T8 — report requirements: what is recorded, what is unknown (2026-11-18)

Where I looked: this repository (`AGENTS.md`, `course-project/CONTEXT.md`, `plan/README.md` §3.6, `plan/M5-report.md`,
`report/REVIEW.md`, `report/REVIEW-DRAFT.md`; `presentation/` is empty and `evidence/M6/M6.T1/` does not exist), the
private course repository (its `AGENTS.md`, the syllabus text, `course-project/report/sources/`), and the assignment
pages Xiaohui saved on the Mac for the first draft. The assignment texts are private course material: they are
summarised here in my own words and not copied.

## Recorded requirements

| Requirement | Source | Status in the 2026-11-18 draft |
| --- | --- | --- |
| The report is one of four deliverables, 10 points each, due at the presentation on 2026-12-01 | `AGENTS.md` §1; plan §3.6 | draft; real-car parts pending |
| Written in the instructor's IEEEtran conference template (`conference_101719.tex`); the template overrides the syllabus's cover sheet and "page x of y" | `report/REVIEW.md` rounds 1–2; private `AGENTS.md` | kept |
| Eight parts: Abstract, Introduction, Related Works, System Overview, Experiments, Results and Evaluation, Conclusion, References | first-draft assignment page | all present |
| Abstract of 150–250 words: problem, approach, evaluation, finding | first-draft assignment page | about 240 words without the pending sentence |
| Introduction: problem and motivation, goal, 2–4 contributions, research questions, roadmap | first-draft assignment page | present (4 contributions, RQ1–RQ4) |
| System Overview: architecture figure, tool table (name, purpose, inputs/outputs, safety checks), one ReAct trace, repository link | first-draft assignment page | Fig. 1, Table II, Fig. 2, link |
| Experiments in six parts, in this order: research questions and hypotheses (H0, H1, sidedness, α, smallest difference that matters, written before the data); setup (hardware, software with versions and model names, environment, configuration table, code link); metrics and ground truth (0–1 scores, tool-call F1 with the matching rule, rubric with anchors, judge and its calibration, label noise, labels frozen); numbered procedure (sample size, randomisation, logging, failed runs, safety, the pilot); statistical plan (descriptives, tests and why, effect sizes, multiplicity, outliers and missing data, power, held-out data, what would change the conclusion); at least five confounders with a control each, plus internal, external and construct threats | first-draft assignment page and its rubric | IV-A to IV-F |
| Results: tables and figures numbered, captioned and referred to; no significance claim from a handful of trials; pilot numbers labelled as pilot | first-draft assignment page | V; the pilot is V-F |
| References through BibTeX with `\cite`; every cite has an entry and every entry is cited; at least 5 credible sources, at least 2 on evaluation or statistics | first-draft assignment page | 41 entries, all cited |
| A short generative-AI disclosure naming the model and what it helped with; Xiaohui is accountable | `AGENTS.md` §8 | section before the references |
| Submit the compiled PDF only | first-draft assignment page | — |

## Length

The only length guidance found is for the **first draft**: "a rough guide" of 6–8 pages in total with about 2 pages
of Experiments, and that quality matters more than length. No page limit for the final report is recorded anywhere
I looked, and the template has none. The first draft was 11 pages. This draft is **12 pages** (about 9.7 of body and
2.3 of references), with the placeholders taking about a third of a column.

## Unknown — for Xiaohui

1. **Is there a page limit for the final report, and do the references count?** (`plan/M5-report.md` M5.T8 step 3
   question 1 was never answered.) If the limit is 10 or 8, the cuts in order of least loss are: shorten Related
   Works (about 2 pages with Table I; it was graded already, and M5.T6 plans this); move the rubric anchors and the
   list of deviations to the repository with a pointer; drop the ReAct trace figure or the tools table's check
   column; show one study figure instead of two.
2. Is there a separate assignment page or rubric for the **final** report? Only the first-draft page was found.
3. Author block: no e-mail address is given (none is recorded; open since `report/REVIEW.md` round 2).
4. The disclosure says the author "reviews the AI-assisted content against the code, logs and sources". That must be
   true when the PDF is submitted.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: searched for the requirements and wrote this record.
