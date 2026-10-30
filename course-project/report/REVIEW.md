# Review log — Class Project Report, Related Works & References draft

Deliverable: `Chen-Project-Report.pdf` (source `Chen-Project-Report.tex`, bibliography
`mybibfile.bib`), built from the instructor's `Class Project Template.zip`
(`conference_101719.tex`, IEEEtran conference class). Written and reviewed 2026-10-01 by
Claude Fable 5.1 via Claude Code; every reviewer below was a fresh subagent with no access to
the drafting context.

## What was checked before writing

- All 27 cited papers were downloaded to `sources/` (git-ignored) and page 1 of each PDF was
  matched to the intended title and authors.
- Each claim was located in the paper's text before it was written into the section.
- BibTeX metadata came from primary records: the arXiv API, the PMLR proceedings pages
  (6 papers), Crossref (8 DOIs), and the NeurIPS proceedings page. DBLP rate-limited every
  request and was not used.

## Round 1 — three lenses

| Lens | Result |
| --- | --- |
| Source fidelity (all 27 sources opened) | 0 critical, 7 minor — all confirmed |
| Citation integrity (every entry checked against a network record) | 0 critical, 3 minor — 2 applied, 1 no-change |
| Requirements, design-document consistency, writing, format | 2 critical, 7 major, 10 minor — confirmed, except as noted |

Confirmed and fixed:

- **Design consistency (critical).** The draft described BeaconMind from `APPROACH-LLM-SLAM.md`,
  which `AGENT-DESIGN.md` v3.3 supersedes. "Never pixels" contradicted the planned image
  ablation, and "single-observation geometry" was the superseded wording (v3.3: single-timestep
  tools, including a multi-beacon pose fix). Both rewritten from `AGENT-DESIGN.md` D1, D5, D7.
- **LLM role overstated.** "Detection gating" is a tool in v3.3, and the LLM does not compute
  coordinates. The text now says the tools do the arithmetic and the LLM decides which results
  enter the belief, and it names the coded per-step procedure as a baseline.
- **Jiang et al.** The 92-point gain was credited to the deterministic walker alone; the paper
  attributes it to the walker plus the cell-type prompt and dead-end retreat. The sentence that
  said stateless calls "avoid the long in-context sequences" named a cause the paper rules out;
  it now cites the paper's isolated-versus-in-loop measurement and says the question is open.
- **SEO-SLAM.** Its merging agent uses 3D coordinates as well as semantics; the text no longer
  calls the merging purely semantic.
- **Li et al.** Added the model variant (Gemini-2.5-Flash), the chain-of-thought condition, and
  that the "visual grid" is a character grid.
- **Smaller fixes:** "only" removed for VLFM; NoMaD no longer called a foundation model; "the
  benchmarks above" narrowed to the two maze studies; "define" changed to "formalize" for Sturm
  et al.; an anachronistic causal claim about 2026 diagnostics; universal claims scoped to
  "reviewed here"; terms defined at first use (beacon, loop closure, frontier, data association,
  dead reckoning, ROS, LLM-Modulo); the missing "no range sensor" contrast; a result, limitation
  or tie to BeaconMind added for ROSA, the survey, VLFM, L3MVN, SEO-SLAM, Sandfuchs et al. and
  NoMaD.
- **Bibliography:** NeurIPS volume 37 and pages 100428–100534 added (checked on the proceedings
  page); system names protected in two titles; a note on the SayCan entry giving its CoRL record.

No change: the citation reviewer found that Li et al. is listed on OpenReview as an ICLR 2026
**workshop** paper although its PDF header says "conference paper"; the arXiv citation was kept.

## Round 2 — two lenses on the revised text

| Lens | Result |
| --- | --- |
| Source fidelity | 0 critical, 4 minor — all confirmed and fixed |
| Design consistency, requirements, writing, format | 0 critical, 5 major, 33 minor — 1 rejected, the rest applied or noted below |

Confirmed and fixed:

- Sandfuchs et al.: "reasoning-tuned models reliably complete navigation" holds only for GPT-5
  and GPT-OSS-120B; now named.
- SEO-SLAM does score the semantic precision and recall of its edited map; the "none can
  report" sentence now says so and is limited to pose and geometric-map accuracy.
- Lee et al.: the model also judges coverage from the map image; wording corrected.
- NoMaD keeps a topological map; "no pose or map" changed to "no metric pose or map".
- Three evaluation items that `proposal-talk-track.md` lists as awaiting the student's
  confirmation (the refusal suite, the coded baseline, true association for the reference when
  identifiers repeat) are now worded as "proposed".
- The per-step procedure is stated before the coded baseline is mentioned; replay versus closed
  loop is explained; "history" changed to "the map built so far"; stateless call described as in
  D5; "ceiling" changed to "best-case reference".
- Disclosure: names the earlier AI-assisted literature searches and says the student's review of
  some design choices is still in progress.
- Format: `et~al.` and unbreakable ranges; SafeAgentBench cited as v5 (2025), the version that
  was read; "Proceedings of the"; Table I moved so it prints at the top of page 2.

Rejected: a request to cite Li et al. as an ICLR 2026 conference paper. OpenReview
(`ICLR.cc/2026/Workshop/World_Models`, checked 2026-10-01) shows a workshop paper; the entry
stays an arXiv preprint with a workshop note.

Not changed, for the student to decide:

- The author block says "individual project"; the team/role question is still open in
  `CONTEXT.md`.
- The author block has no e-mail address (no JHU address is recorded in the repository).
- The page count is 4 because the review added comparisons; the template's own page style has no
  page numbers, and the assignment's template takes precedence over the syllabus cover-sheet and
  "page x of y" convention.

## Round 3 — one reviewer, all lenses, on the twice-revised text

Result: 0 critical, 5 minor — all confirmed and fixed. Parts A (sources) and B (design
documents) were otherwise clean; Part C (build mechanics) was clean.

- SEO-SLAM also reports the absolute pose error of its optimized trajectory (Table III), not
  only semantic precision and recall. The text now says so and adds that the estimate remains
  the optimizer's, so the gap sentence still holds.
- Deng et al.: the 0.66 / 0.99 / 0.91 figures are from arXiv v2 (v1 has 0.64 / 0.97 / 0.92); the
  entry now pins `arXiv:2601.22228v2`.
- The stateless step message also carries the operator request (`AGENT-DESIGN.md` D5); added.
- NoMaD is a candidate exploration baseline that cannot be scored on pose or map error; the
  "exploration only" wording was changed to match `APPROACH-LLM-SLAM.md`.
- "Stretch conditions" for the no-tool and LLM-over-GTSAM variants is on the unconfirmed list in
  `proposal-talk-track.md`; now worded "proposed as stretch conditions".

**No fourth round was run.** After round 3 the only edits were those five, plus one clause added
to fill a column gap on page 3 ("what the LLM adds beyond the procedure … would be scored by the
request suite", taken from `proposal-talk-track.md`). Each was checked by hand against the source
line the reviewer cited, but not by a fresh reviewer.

## Open issues

1. Three evaluation choices are described as "proposed" because `proposal-talk-track.md` lists
   them as awaiting the student's confirmation: the refusal request suite, the coded per-step
   baseline, and true association for the GTSAM reference when identifiers repeat. So is the
   "stretch conditions" scope. If she confirms them, record them in `AGENT-DESIGN.md`.
2. The novelty sentence ("no prior study reports a trajectory or map error for a landmark-SLAM
   estimate maintained by an LLM") rests on the 2026-09-27 feasibility search and this session's
   reading of 27 papers. One possibly related paper (an LLM-guided pedestrian dead-reckoning
   study, Sensors 2026) could not be opened then and was not retried here.
3. Twelve of the 27 references are arXiv preprints; Lee et al. (arXiv:2609.27340, 2026-09-23) is
   a week old and carries the section's most specific prior-system numbers.
4. The disclosure says the author "reviews all AI-assisted content against the sources before
   submission". That is a statement about the student's own action and must be true when the PDF
   is uploaded.

## Validation evidence (final build, 2026-10-01)

Command: `latexmk -pdf -interaction=nonstopmode -halt-on-error Chen-Project-Report.tex` (exit 0).

```
cite keys in .tex: 27; entries in .bib: 27; cited without entry: []; entry never cited: []
pages: 4
unresolved [?] in PDF: 0
undefined/rerun/overfull/error lines in .log: 0
You've used 28 entries,          (27 references + the IEEEtran control entry)
warning$ -- 0
reference labels rendered: 27
placeholders: 7                  (abstract, index terms, sections I, III, IV, V, VI)
```

All four pages were rendered with `pdftoppm` and read as images after the last build: the title
and author block, Table I at the top of page 2, no text in the margins, and a balanced reference
list on page 4.

Template changes, all in the preamble: `subfig` loaded with `caption=false` so IEEEtran's own
table-caption format applies; `flushend` to balance the last page; `\bstctlcite` plus an
`@IEEEtranBSTCTL` entry so that more than six authors print as "et al."; the instructor's 48
sample entries removed from `mybibfile.bib`.
