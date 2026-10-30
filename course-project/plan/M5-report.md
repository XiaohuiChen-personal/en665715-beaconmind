# M5 — Report: the IEEE paper, written alongside M1–M4

Written 2026-10-05 for BeaconMind (EN.665.715 capstone; sole participant **Xiaohui Chen**; final deadline
**2026-12-13**; no dated schedule). This file follows `course-project/plan/README.md`, which wins over this
file where they disagree (README, top). Read README §1 (session protocol), §5 (conventions) and §10 before any
task here. Contracts are cited as "C<k>", conventions as "L<k>", open decisions as "OD<k>", README sections as
"README §<n>".

Facts in this file were checked on the Mac on 2026-10-05 (read-only):
`course-project/report/Chen-Project-Report.tex` (314 lines) builds to a 4-page PDF; 27 cite keys and 27 bib
entries match; 0 overfull boxes and 0 undefined references in the log; 5 `\laterdraft` uses plus 2 literal
"Reserved for a later draft" placeholders (abstract and index terms); the References heading starts on page 4.
Toolchain on the Mac: latexmk 4.87, pdfTeX 1.40.29 (TeX Live 2026, Homebrew), pdfinfo/pdftotext/pdftoppm 26.04.0,
chktex 1.7.9; `tikz`, `standalone`, `booktabs`, `flushend`, `subfig`, `cite` are installed; system `python3` is
3.13.7 with matplotlib 3.10.6 **and pytest 9.1.1** (re-checked 2026-10-06 with `python3 -m pytest --version`).
The instructor's template zip (`~/Downloads/Class Project Template.zip`) holds `IEEEtran.cls`,
`conference_101719.tex`, `IEEEabrv.bib`, `IEEEexample.bib`, `IEEEfull.bib`, `IEEEtran.bst`, `IEEEtranS.bst` and
**no README** (`unzip -l`, 2026-10-06); `conference_101719.tex` has six sections (Introduction, Related Works,
System Overview, Experiments, Results and Evaluation, Conclusion) and **states no page limit** (`unzip -p … 
conference_101719.tex | grep -niE "page|limit"` prints nothing). A copy is at
`course-project/report/sources/template-conference_101719.tex` (git-ignored, so it exists only on this Mac). No page
limit for the final report is recorded anywhere in the repository (searched 2026-10-05), so M5.T8 asks Xiaohui
(M6.T1 question 5 asks the same; M5.T8 reads M6.T1's answer first if it exists).

**Conventions used in this file.**
- `…/` inside a command means `/Users/xiaohuichen/Projects/EN.665.715/course-project/`.
- **Task status check.** Every prerequisite "task X done" is checked with
  `python3 /Users/xiaohuichen/Projects/EN.665.715/course-project/tools/task_status.py <task ID> [<task ID> …]`
  (Mac), the plan-wide helper of **README convention L12** (M1.T1 creates it; M5.T8 step 8b creates it from
  L12 if it is still missing). It prints one line per task, `<ID> <status>`, where status is `todo`,
  `in-progress`, `blocked`, `done`, `dropped (cut line)`, `NO-FILE` (the milestone file does not exist) or
  `NOT-FOUND` (the ID has no status-table row). "Expected `done`" below means the line ends in `done`. Do
  **not** use `grep "| <ID> |"` on a milestone file: each ID appears in two or three tables (status table,
  task list, entry criteria), so a grep shows several rows and the status is ambiguous.
- **Other milestones' task IDs used here** (checked against their files on 2026-10-06): M1.T12 camera bridge +
  `apriltag_ros` launch; M2.T5 = the complete Isaac twin (needs M2.T15, M2.T16); M2.T13 observation builder;
  M2.T14 report parser; M2.T18 frontier providers; M2.T19 B2 navigation missions; M2.T20 metrics for missions,
  SPL, exploration and refusal; M3.T12 = ≥ 10 real observation logs; M3.T13 out-of-band STOP hotkey and latch;
  M3.T17 ground-truth camera accuracy acceptance (5 cm / 3°); M3.T18 closed-loop real runs; M3.T19 replay of
  arms on the real logs; M4.T5 closed-loop sweep on held-out **kinsim** seeds; M4.T13 real-log replay sweep
  and sim-to-real gap; M4.T14 request-suite scoring; M4.T15 Isaac closed-loop confirmatory subset; **M4.T16
  final analysis, which writes `report/generated/tables/*.tex` and `report/generated/figures/*.pdf`** (M4 file,
  M4.T6 step 6 table) and `evidence/M4/M4.T16/results_summary.md`; M6.T1 writes
  `course-project/presentation/DELIVERABLES.md`; M6.T9 runs the ROSA demo in the twin.

---

## Goal

Turn `course-project/report/Chen-Project-Report.tex` from the graded Related Works draft (Section II and the
References only) into the complete final IEEE conference paper: Abstract, index terms, Introduction, a trimmed
Related Works, System Overview, Experiments, Results and Evaluation (with a Discussion and Limitations
subsection), Conclusion, an accurate generative-AI disclosure, and references, built with `latexmk`, within the
page budget, and adversarially reviewed with every round logged in `course-project/report/REVIEW.md`.

The report is written **alongside** M1–M4, not after them. 60 % of the project grade is preparation and
participation (AGENTS.md §5 "The course project"), so a staged report with review logs is itself graded
evidence.

## Exit criteria (M5 is done when…)

1. `python3 course-project/tools/check_report.py --final` prints `RESULT: PASS` (build exit 0, 0 overfull boxes,
   0 undefined references or citations, 0 unresolved `??`/`[?]`, 0 placeholders, 0 missing result numbers,
   every cite key has a bib entry and every bib entry is cited, page count within `report/budget.json`).
2. Every result number in the text is a `\bmnum{…}` macro and every results table is `\input` from
   `report/generated/`: either `report/generated/tab-*.tex` produced by `tools/report_assets.py` (M5-owned), or
   `report/generated/tables/*.tex` produced by M4.T16's `tools/make_report_assets.py` (M4-owned; never edited by
   M5). `python3 course-project/tools/report_assets.py --check` prints `assets: up to date`, and
   `shasum -a 256 -c course-project/evidence/M5/M5.T14/m4-assets.sha256` prints only `OK` lines (when M5.T14 ran).
3. `report/CLAIMS.md` has no row with status `pending:` and only `proposed:OD<k>` rows whose OD is still open.
4. The disclosure section matches `report/DISCLOSURE-LEDGER.md`, which Xiaohui confirmed row by row.
5. The final adversarial review (M5.T7) ended with a full round with **zero confirmed findings**
   (AGENTS.md §6.3), logged in `report/REVIEW.md`.
6. Xiaohui has read the final PDF end to end and said so (recorded in `CONTEXT.md`), because the disclosure
   states that they reviewed all AI-assisted content.

## What M5 unlocks

- M6.T5 (slides) reuses the architecture figure, the arena figure, the results figures and the `\bmnum`
  numbers (through `report/generated/numbers.json`).
- M6.T6 (final submission package) includes `report/Chen-Project-Report.pdf`.

## Entry criteria and prerequisites from other milestones

M5 has **no global entry criterion**: M5.T8, T1, T2 and T11 can start today. Each task names its own
prerequisites. Summary:

| M5 task | Needs (hard: must be `done`) | Uses if done (soft: otherwise write "planned" and log `pending:` in CLAIMS.md) |
| --- | --- | --- |
| M5.T8 | — | M6.T1 (`presentation/DELIVERABLES.md`, question 5: report page limit) |
| M5.T1 | M5.T8 | M1.T10 (settled ODs) |
| M5.T2 | M5.T8 | M1.T5, M1.T6, M1.T8, M1.T9, M1.T10, M1.T12, M2.T1, M2.T5, M2.T7, M2.T13, M2.T14, M3.T6, M3.T7, M3.T13, M6.T2, M6.T9 (implementation status) |
| M5.T3 | M5.T2, M1.T10 | M1.T7, M1.T8, M1.T9, M2.T2, M2.T5, M2.T6, M2.T8, M2.T9, M2.T10, M2.T20 |
| M5.T4 | M5.T3, M5.T9, M5.T10, M2.T12 | M2.T20 (closed-loop metrics), M3.T19 (real-log replay) |
| M5.T5 | M5.T4, and M5.T14 unless M5.T14 is `dropped (cut line)` | — |
| M5.T6 | M5.T5 | — |
| M5.T7 | M5.T1–T6, M5.T11–T15 (each `done` or `dropped (cut line)`) | M6.T1 |
| M5.T9 | M1.T1, M5.T8 | M2.T10 (`episodes.csv` columns) |
| M5.T10 | M1.T1, M2.T2, M2.T10, M2.T11 | M3.T10 (real arena spec) |
| M5.T11 | — | — |
| M5.T12 | M5.T1, M5.T2, M5.T3 | — |
| M5.T13 | M5.T3, M4.T1 | M3.T10, M3.T17 |
| M5.T14 | M5.T4, M4.T16 | M4.T13, M4.T15, M3.T19 |
| M5.T15 | M5.T5 | — |

## Status table

| Task | Title | Status | Effort | Evidence | Last updated | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| M5.T1 | Introduction | in-progress | S | — | 2026-10-29 | 2026-10-29: first draft (report first draft with experiments) |
| M5.T2 | System Overview, with the architecture figure | in-progress | M | — | 2026-10-29 | 2026-10-29: first draft with architecture figure, tool table and a ReAct trace |
| M5.T3 | Experiments (protocol, conditions, baselines, metrics) | in-progress | M | — | 2026-10-29 | needs M1.T10. 2026-10-29: first draft (six parts per the first-draft assignment) |
| M5.T4 | Results and Evaluation (tables and figures generated from `data/`, never typed by hand) | in-progress | M | — | 2026-10-29 | needs M2.T12. 2026-10-29: pilot results only, generated by `tools/pilot_analyze.py` |
| M5.T5 | Conclusion and limitations | in-progress | S | — | 2026-10-29 | 2026-10-29: short draft |
| M5.T6 | Trim Related Works to fit; references check | in-progress | S | — | 2026-10-29 | 2026-10-29: Related Works condensed and an evaluation-methods subsection added (14 verified references) |
| M5.T7 | Generative-AI disclosure, final build, adversarial review | todo | M | — | 2026-10-05 | last task |
| M5.T8 | Report requirements, page budget, preamble and build checker | todo | S | — | 2026-10-05 | do first |
| M5.T9 | Report numbers and tables pipeline (`tools/report_assets.py`) | todo | M | — | 2026-10-05 | needs M1.T1, M5.T8 |
| M5.T10 | Figure pipeline: arena and trajectory figures (`tools/report_figures.py`) | todo | M | — | 2026-10-05 | Spark host |
| M5.T11 | AI-disclosure ledger, reconciled with Xiaohui | todo | S | — | 2026-10-05 | |
| M5.T12 | Interim adversarial review of Sections I–IV | todo | S | — | 2026-10-05 | |
| M5.T13 | Experiments update: frozen pre-registration and the real setup | todo | S | — | 2026-10-05 | needs M4.T1 |
| M5.T14 | Results update to the full benchmark | todo | M | — | 2026-10-05 | needs M4.T16 |
| M5.T15 | Abstract, index terms and title check | todo | S | — | 2026-10-05 | |

## Task list

| ID | Title | Depends on (hard) | Effort | Machine |
| --- | --- | --- | --- | --- |
| M5.T8 | Report requirements, page budget, preamble and build checker | — (Xiaohui's answer) | S | Mac |
| M5.T1 | Introduction | M5.T8 | S | Mac |
| M5.T2 | System Overview, with the architecture figure | M5.T8 | M | Mac |
| M5.T11 | AI-disclosure ledger, reconciled with Xiaohui | — | S | Mac |
| M5.T9 | Report numbers and tables pipeline | M1.T1, M5.T8 | M | Mac |
| M5.T3 | Experiments | M5.T2, M1.T10 | M | Mac |
| M5.T12 | Interim adversarial review of Sections I–IV | M5.T1, T2, T3 | S | Mac (fresh sessions) |
| M5.T10 | Figure pipeline | M1.T1, M2.T2, M2.T10, M2.T11 | M | Spark host + Mac |
| M5.T4 | Results and Evaluation (first result) | M5.T3, T9, T10, M2.T12 | M | Mac (+ Spark host for figures) |
| M5.T13 | Experiments update | M5.T3, M4.T1 | S | Mac |
| M5.T14 | Results update to the full benchmark | M5.T4, M4.T16 | M | Mac (+ Spark host) |
| M5.T5 | Conclusion and limitations | M5.T4 (+ T14 unless dropped) | S | Mac |
| M5.T15 | Abstract, index terms and title check | M5.T5 | S | Mac |
| M5.T6 | Trim Related Works; references check | M5.T5 | S | Mac |
| M5.T7 | Disclosure, final build, final adversarial review | all M5 tasks | M | Mac (fresh sessions) |

## Suggested execution order (parallel groups)

The IDs were reserved before the order was known (README §3.2), so the order is not the numeric order.

1. **Group A — now, no other milestone needed.** M5.T8 first (one session; it waits for Xiaohui's page-budget
   answer but can finish everything else meanwhile). Then M5.T1, M5.T2 and M5.T11 in any order; they touch
   different parts of the `.tex` (T11 touches none).
2. **Group B — after M1.T1.** M5.T9 (code; Mac).
3. **Group C — after M1.T10.** M5.T3, then M5.T12 (interim review of I–IV).
4. **Group D — after M2.T2, M2.T10, M2.T11.** M5.T10 (code; Spark host). Can run alongside group C.
5. **Group E — after M2.T12 (the cut line's first result).** M5.T4.
6. **Group F — after M4.T1 / M4.T16.** M5.T13, then M5.T14. Skip both, status `dropped (cut line)`, if the cut
   line drops M4 (README §3.4).
7. **Group G — the finish.** M5.T5 → M5.T15 → M5.T6 → M5.T7, in that order.

**Calendar triggers for M5** (README §3.4; count the days left before 2026-12-13 at the start of each session):

| Days left | Rule for M5 |
| --- | --- |
| ≤ 42 | If M5.T1 or M5.T2 is not `done`, do them before any new M2–M4 task (they need no results) |
| ≤ 21 | Experiments are frozen. Run M5.T4/T14 on whatever results exist; then group G |
| ≤ 10 | M5.T6 must have started. If M5.T4 is not `done`, stop and ask Xiaohui (README §1.4 item 8): the default is to submit with Section V reporting the results that exist, labelled preliminary, and the missing parts as limitations |
| ≤ 7 | Only M5.T7 (and M6.T6) |

---

## M5-wide rules for writing the report (R1–R14)

Every M5 task obeys these. A reviewer (M5.T12, M5.T7) checks them.

- **R1 — Source order for statements about BeaconMind.** `AGENT-DESIGN.md` (v3.4 once M1.T10 is done, otherwise
  v3.3) first, then README §6 contracts, then `configs/*.json` and evidence files, then `APPROACH-LLM-SLAM.md`
  only where AGENT-DESIGN is silent. The first Related Works draft described BeaconMind from APPROACH and the
  round-1 review rated it critical (`report/REVIEW.md` round 1; `CONTEXT.md` "2026-10-01 class project report").
- **R2 — Built versus planned.** Write that something *is* built, measured or shown only when the task's evidence
  check passes (the plan's status table says `done` and the evidence file exists). Otherwise write "is planned" /
  "will" and add a `CLAIMS.md` row with status `pending:<task ID>`. Never smooth over a gap.
- **R3 — No hand-typed results.** Every number that comes from an experiment (errors, rates, counts of episodes,
  latencies, costs, p-values, confidence bounds) is written as `\bmnum{<key>}`; every results table is
  `\input{generated/tab-<name>.tex}`; every results figure is a PDF made by a script. The report pipeline only
  selects, formats and compares numbers against pre-registered thresholds; it never computes statistics (those
  come from M2.T10/M2.T12 and M4.T16, which runs the M4.T6 statistics library). Design values (move lengths, gates, budgets) may be typed but must equal
  `configs/dv.json` (C0), and each gets a `CLAIMS.md` row naming the key.
- **R4 — Labels.** Say `simulation (Isaac Sim)` (C3 `source: "sim"`), `kinematic simulation` (C3
  `source: "kinsim"`) or `real car` (`source: "real"`) for every result, and `replay` or `closed loop` for every
  result (AGENT-DESIGN D1a, D1d). The label comes from the `source` and `mode` columns of the result CSV, never
  from memory. Kinsim results appear in two cases: M4.T5's closed-loop sweep runs on kinsim seeds by design
  (`plan/M4-benchmark.md` M4.T5 title), and the README §3.4 fallback if the Isaac twin failed (only with
  Xiaohui's recorded approval). In both cases say so in the caption and in IV-D; never call a kinsim result
  "Isaac Sim".
- **R5 — Execution gate.** No sentence may imply an experiment ran unless its evidence exists. Anything that
  was planned but not run is either removed or stated as a limitation (AGENTS.md "Execution gate";
  README §1.3).
- **R6 — Proposed versus decided.** An item in the open-decision register (README §3.5) is written as
  "proposed" until `AGENT-DESIGN.md` records it as settled (M1.T10). Add a `CLAIMS.md` row `proposed:OD<k>`.
  Today the report already words the refusal suite (OD1), B2 (OD2), oracle association (OD3) and the stretch
  arms (OD4) as proposed (`report/REVIEW.md` "Open issues" item 1).
- **R7 — New references.** Before citing a new source: download it into `course-project/report/sources/`
  (git-ignored) with the AGENTS.md §4.1 download check (`pdfinfo` and the page-1 title via
  `pdftotext -f 1 -l 1 -layout <file> - | head -5`); find the claim in its text (`pdftotext -layout`); take
  the BibTeX from a primary record (arXiv API `https://export.arxiv.org/api/query?id_list=<id>`, the
  publisher page, or `https://api.crossref.org/works/<doi>`); pin arXiv versions with the version you read
  (as for Deng et al., `report/REVIEW.md` round 3). Software (Isaac Sim, vLLM, apriltag_ros, evo, GTSAM) is
  cited as `@misc` with the URL, the version actually used (from evidence), and `note = {Accessed
  YYYY-MM-DD}`. **Never cite a source you have not opened.** If a source cannot be retrieved, do not cite it;
  write the sentence without it or drop it.
- **R8 — Style.** IEEE conference style as in the existing Section II: `\textit{et~al.}`, `Fig.~\ref{…}`,
  `Table~\ref{…}`, `Section~\ref{…}`, `Eq.~\eqref{…}`, numbers and units joined with `~` (`0.25~m`), ranges
  with `--` inside `\mbox{}` where they could break, `\%` for percent, `\_` in identifiers in running text,
  identifiers such as tool names in `\texttt{}`. Impersonal voice ("BeaconMind", "the agent"); "my" only in
  the novelty sentence that already uses it. Define every acronym at first use **in reading order** (the
  Introduction now comes before Section II).
- **R9 — Figures.** Vector PDF only, made by a script or a standalone TikZ file under
  `course-project/report/figures/`; single-column figures at `width=\columnwidth`, two-column
  `figure*` at `width=\textwidth`; no text smaller than 7 pt at print size; Okabe–Ito colours
  (`#000000 #E69F00 #56B4E9 #009E73 #F0E442 #0072B2 #D55E00 #CC79A7`) with distinct line styles, so they
  survive greyscale printing; no Type 3 fonts (`pdffonts <file>.pdf` must not list `Type 3`). Each caption is
  self-contained: what is shown, sim or real, replay or closed loop, how many seeds and repeats.
- **R10 — Labels in the source.** Sections `sec:intro`, `sec:related`, `sec:overview`, `sec:experiments`,
  `sec:results`, `sec:conclusion`; subsections `ssec:<word>`; figures `fig:<name>`; tables `tab:<name>`;
  equations `eq:<name>`. M5.T8 renames the template's `sytem_overview`, `experiments`, `results` labels.
- **R11 — AI disclosure in the source.** Each task adds, directly under the `\section` it drafted, one comment
  line `% AI-assisted (<model you are running as>, <YYYY-MM-DD>): <what>` (L11), and adds a row to
  `report/DISCLOSURE-LEDGER.md` (M5.T11 creates it; if it does not exist yet, append the row to a list under
  "Ledger rows to add" in your `CONTEXT.md` entry).
- **R12 — Page budget.** Read `report/budget.json` (M5.T8). The per-section targets in M5.T8 step 6 guide the
  writing; only M5.T6 and M5.T7 enforce the total.
- **R13 — Privacy and secrets.** No photo with a person, pet or personal item; no Wi-Fi name, key, address or
  e-mail other than the author block (L8, L9, S12). `check_report.py` scans the PDF text.
- **R14 — The report never changes the design.** If writing reveals that two documents disagree, or that a
  design statement cannot be true, stop and ask (README §1.4 items 6 and 8). Do not "fix" it in prose.

## Shared tools and files for M5

| Path | What it is | Created by |
| --- | --- | --- |
| `course-project/report/Chen-Project-Report.tex` | The paper | exists |
| `course-project/report/mybibfile.bib` | Bibliography (plus `IEEEabrv.bib`) | exists |
| `course-project/report/REVIEW.md` | Review log: rounds 1–3 of the Related Works draft exist; M5 appends | exists |
| `course-project/report/budget.json` | Page budget, `bm.report_budget/1` | M5.T8 |
| `course-project/report/CLAIMS.md` | One row per non-obvious claim: section, claim, source, status | M5.T8 |
| `course-project/report/DISCLOSURE-LEDGER.md` | Who (which model, which tool) did what, with the source of each fact | M5.T11 |
| `course-project/tools/check_report.py` | Build and hygiene checker (stdlib only) | M5.T8, with its tests `beaconmind/tests/test_check_report.py` |
| `course-project/tools/report_assets.py` | CSV → `\bmnum` numbers, LaTeX tables, target outcomes (stdlib only) | M5.T9 |
| `course-project/report/assets.json` | Which source CSV feeds which number/table, `bm.report_assets/1` | M5.T9, filled by M5.T4/T14 |
| `course-project/report/generated/` (top level) | `numbers.tex`, `numbers.json`, `tab-*.tex`, `MANIFEST.txt` — generated by M5.T9's tool, never edited | M5.T9 |
| `course-project/report/generated/tables/`, `generated/figures/` | M4.T16's tables (`tab_*.tex`, `\hline` rules) and figures (`fig_*.pdf`, `fig_*.png`) — **owned by M4**; M5 only `\input`s / `\includegraphics` them and records their SHA-256 | M4.T16 |
| `course-project/tools/task_status.py` (README L12) | Prints task statuses from the milestone files' status tables (shared by every milestone) | M1.T1 (M5.T8 step 8b creates it if missing) |
| `course-project/tools/report_figures.py` | Arena and trajectory figures (matplotlib) | M5.T10 |
| `course-project/report/figures/` | `src/fig-architecture.tex` (standalone TikZ), `fig-architecture.pdf`, `generated/*.pdf` | M5.T2, M5.T10 |

**Generated-number key names** (used by M5.T4, M5.T14 and every `\bmnum`): lower case, characters
`[a-z0-9.-]` only, pattern `<metric>.<mode>.<condition>.<arm>[.<model_key>][.<stat>]`, where `<mode>` ∈ `replay`,
`closed`; `<condition>` ∈ `uni`, `dup`, `hid` (the short forms of M2's world IDs); `<arm>` is the arm in lower
case (`l2`, `b0`, `b1`, `b2`, `r`, …); `.<model_key>` is present only for LLM arms (B0, B1, B2 and R have no
model key); `<stat>` ∈ `median`, `q1`, `q3`, `mean`, `ci-lo`, `ci-hi`, `p50`, `p95`, `count`, `rate`.
Examples: `ate.replay.dup.l2.qwen35-a3b-think.median`, `ate.replay.dup.b1.median`. Counts that are not tied to
one metric use `n.<what>.<mode>` (`n.models.replay`, `n.seeds.replay`) and `k.repeats`.

**Build command (Mac)**, used by every task:
```bash
cd /Users/xiaohuichen/Projects/EN.665.715/course-project/report && \
  latexmk -pdf -interaction=nonstopmode -halt-on-error Chen-Project-Report.tex > build.out 2>&1; echo "latexmk exit $?"
```
**Check command (Mac):** `python3 /Users/xiaohuichen/Projects/EN.665.715/course-project/tools/check_report.py`
(draft mode) or `… --final` (M5.T7). It runs the build itself unless `--no-build` is given.
"Run the check; save `check_before.txt`" (or `check_after.txt`) in any task means exactly:
```bash
mkdir -p /Users/xiaohuichen/Projects/EN.665.715/course-project/evidence/M5/<task ID> && \
python3 /Users/xiaohuichen/Projects/EN.665.715/course-project/tools/check_report.py \
  > /Users/xiaohuichen/Projects/EN.665.715/course-project/evidence/M5/<task ID>/check_before.txt 2>&1; \
tail -1 /Users/xiaohuichen/Projects/EN.665.715/course-project/evidence/M5/<task ID>/check_before.txt
```
and the last line must be `RESULT: PASS` (for `check_before.txt`: if it is `RESULT: FAIL`, the build was broken
before the task started — stop and report it, README §1.4 item 3). Every writing task ends by saving
`check_after.txt` the same way, with `RESULT: PASS`, even where its steps only say "run the check".
Right after saving `check_before.txt`, also snapshot the source:
`cp …/report/Chen-Project-Report.tex …/evidence/M5/<task ID>/before.tex`. "Save the diff" then means
`diff -u …/evidence/M5/<task ID>/before.tex …/report/Chen-Project-Report.tex > …/evidence/M5/<task ID>/tex.diff`
(this task's changes only; `git diff` would also show earlier uncommitted tasks, because nothing is committed
without Xiaohui's request, L10).

**Visual check (Mac).** After any layout change, render only the pages you changed and look at them:
```bash
mkdir -p "$TMPDIR/bm-render" && pdftoppm -png -r 70 -f <first> -l <last> \
  /Users/xiaohuichen/Projects/EN.665.715/course-project/report/Chen-Project-Report.pdf "$TMPDIR/bm-render/p"
```
Then open the PNGs with your file-reading tool. Never write rendered pages into the repository.

### `CLAIMS.md` format (M5.T8 creates it)

```markdown
| ID | Section | Claim (short) | Source (doc:§, evidence path, configs key, or bib key) | Status |
| --- | --- | --- | --- | --- |
| C-III-01 | III-A | Tools are single-timestep | AGENT-DESIGN.md D1b | ok |
| C-III-07 | III-B | The Isaac twin publishes the same topics as the car | README C12; evidence/M2/M2.T5/… | pending:M2.T5 |
| C-IV-03 | IV-C | B1 uses oracle association when IDs repeat | proposal-talk-track.md "New in this revision" | proposed:OD3 |
```
Status is one of `ok`, `pending:<task ID>`, `proposed:OD<k>`. IDs are `C-<section roman>-<nn>`, never reused.

### Adversarial review protocol for the report (used by M5.T12 and M5.T7)

Based on AGENTS.md §6 (lenses, verify before fixing, loop until a clean round, log everything). The writer of
a section never reviews it in the same session.

**Lenses (one fresh reviewer per lens; a fresh subagent or, if the tool cannot spawn one, a new chat session
that has not seen the drafting):**

| Lens | Checks | Inputs the reviewer must open |
| --- | --- | --- |
| RL1 Source fidelity | Every sentence that cites a paper says what the paper says (numbers, model names, conditions) | the `.tex`, `report/sources/*.txt` (run `pdftotext -layout` on any PDF without a `.txt`) |
| RL2 Citation integrity | Every bib entry exists and matches its record (authors, title, venue, year, version); every `\cite` points to the right work | `mybibfile.bib`, the arXiv/Crossref/publisher records |
| RL3 Design consistency | Every statement about BeaconMind matches AGENT-DESIGN (current version), README §6 contracts, `configs/*.json`; "proposed"/"planned" wording follows R2 and R6 | the `.tex`, `AGENT-DESIGN.md`, `plan/README.md` §6, `configs/`, `CLAIMS.md` |
| RL4 Results integrity (only once Section V has results) | Every `\bmnum` key and table traces through `report/generated/MANIFEST.txt` to an evidence file; no claim goes beyond the numbers; sim/real and replay/closed-loop labels (R4); statistical claims match M4.T16 outputs (`evidence/M4/M4.T16/results.json`, `analysis_stdout.txt`); M4-owned tables match `evidence/M5/M5.T14/m4-assets.sha256` | the `.tex`, `report/assets.json`, `report/generated/`, `evidence/M2/`, `evidence/M4/`, `evidence/M5/` |
| RL5 Math, notation and figures | Equations, symbols, units, frames (C1); each figure shows what its caption says, with correct axes, legends, frames and sources | the `.tex`, `report/figures/`, README C1/C10 |
| RL6 Requirements, format, writing | Template sections present; page budget; IEEE style (R8); terms defined before use; the disclosure matches the ledger; `check_report.py` output | the PDF (render pages), the `.tex`, `budget.json`, `DISCLOSURE-LEDGER.md` |

**Reviewer prompt (paste verbatim, filling the angle brackets):**
```
You are an adversarial reviewer of an IEEE conference paper draft. Your lens is <lens name>: <lens checks>.
Your job is to find what is wrong; flag anything you cannot confirm. Do not edit any file.
Open these files yourself: <inputs for the lens>. The paper is
/Users/xiaohuichen/Projects/EN.665.715/course-project/report/Chen-Project-Report.tex (PDF next to it).
Review only: <sections in scope>.
Return ONLY a Markdown table with columns:
| ID | Severity (critical/major/minor) | Location (section + .tex line) | Problem | Evidence (file:line, URL, or record) | Proposed fix |
Severity: critical = false or unsupported claim, invented citation or number, safety-relevant misstatement,
inaccurate AI disclosure; major = misleading wording, design inconsistency, missing required element;
minor = style or clarity. If you find nothing, return the header row and one row "none".
```

**Executor procedure per round `n`:**
1. Run each lens in scope with the prompt. Save each raw table to
   `course-project/evidence/M5/<task ID>/round-<n>-<RLk>.md`.
2. **Verify before fixing** (AGENTS.md §6.2): for each finding open the cited source yourself and mark it
   `confirmed` or `rejected` with a one-line reason. Reviewers hallucinate too.
3. Fix every confirmed finding, and check the neighbouring sentences for the same error.
4. Rebuild and run `check_report.py`; it must not get worse.
5. Append to `course-project/report/REVIEW.md` a section `## Final report — round <n> (<task ID>, <date>)` with a
   table `| Lens | Findings (crit/major/minor) | Confirmed | Rejected |`, then one bullet per confirmed finding
   (what changed) and one per rejected finding (why).
6. **Loop:** run another full round until one full round (all lenses in scope) has **zero confirmed findings**.
   After every third round, tell Xiaohui the trend (findings per round) and ask whether to continue; the
   default is to continue.

---
## Tasks

### M5.T1 — Introduction

**Why.** The Introduction states the problem, the gap, BeaconMind in one paragraph, the research questions and
the contributions, and it now has to define the terms that Section II's first paragraph defines today, because
the Introduction comes first in reading order. Sources: `proposal-talk-track.md` slide 1 (gap and research
questions, lines 3–31), `AGENT-DESIGN.md` D1–D8, `APPROACH-LLM-SLAM.md` §4 (the four-question form, superseded
by the talk track's three accepted questions), the existing Section II (lines 59–74 of the `.tex` as of
2026-10-05).

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M5.T8 done | task | `python3 …/tools/task_status.py M5.T8` (Mac) | `done` |
| Checker present | file | `ls /Users/xiaohuichen/Projects/EN.665.715/course-project/tools/check_report.py` (Mac) | path printed |
| M1.T10 status (soft) | task | `python3 …/tools/task_status.py M1.T10` (Mac) | `done` → use settled wording; otherwise keep "proposed" (R6) |

**Inputs.**
- `course-project/report/Chen-Project-Report.tex` — all of it, especially Section II's first paragraph and the
  four subsection endings ("BeaconMind adopts…", "In none of…", "BeaconMind is designed around…", "BeaconMind
  uses this body of work…").
- `course-project/proposal-talk-track.md` slide 1 (lines 3–31: gap lines 18–24, research questions lines 26–31) and
  "New in this revision, for Xiaohui to confirm" (lines 201–212).
- `course-project/AGENT-DESIGN.md` D1, D2, D4, D5 (tools table), D6, D7 headings.
- `course-project/report/CLAIMS.md`, `budget.json` (section target from M5.T8 step 6).

**Steps.**
1. *Mac.* Run the check command; save its output as `evidence/M5/M5.T1/check_before.txt`. Expected: `RESULT: PASS`
   (draft mode). If it fails, stop: the build was broken before you started (README §1.4 item 3).
2. *Mac.* Under `\section{Introduction}\label{sec:intro}` replace `\laterdraft` with six parts — four paragraphs
   (context, gap, BeaconMind, roadmap) and two lists (research questions, contributions) — in this order. Target length: the M5.T8 target for Section I (default 500–600 words).
   1. **Context (3–4 sentences).** LLM agents turn instructions into robot plans; they are grounded and closed
      loop (`\cite{ahn2022saycan,huang2023inner,yao2023react}`); in the navigation and mapping systems reviewed
      in Section~II the pose and the map come from classical SLAM or a pre-built map
      (`\cite{rana2023sayplan,lee2026spatial,syarubany2026llm}`). Define **large language model (LLM)** and
      **simultaneous localization and mapping (SLAM)** here.
   2. **Gap (2–3 sentences).** No study the author found scores an LLM-maintained pose or landmark map against
      ground truth (the claim and its basis are in Section II's "In none of the language-model systems above…"
      paragraph; reuse its scope: "to my knowledge", and cite `sandfuchs2026llms` for the explicit
      "not SLAM" boundary). Say why it matters: it tells which SLAM decisions an LLM agent can be trusted with,
      and a negative outcome is informative (talk track lines 23–24).
   3. **BeaconMind (5–7 sentences).** Move here, rewritten, the content of Section II's first paragraph: the
      car (differential drive, wheel encoders, IMU, one monocular camera, no range sensor); the walled arena
      with AprilTags as **beacons** (define the term); identifiers that may repeat; the stop–observe–decide–move
      cycle; what the LLM decides (trust, association, acceptance of pose fixes and **loop closures** — define —,
      map updates, one of five bounded moves); that deterministic single-timestep tools compute every number
      and a validator gates every move (AGENT-DESIGN v3 split, D5, D6); that the same agent runs in an Isaac
      Sim twin and on the car (D1a). Use R2 for anything not yet built.
   4. **Research questions.** An `enumerate` with exactly the three accepted questions (talk track lines 26–31),
      worded as questions: (RQ1) estimation in replay against B1 (GTSAM) and B0 (dead reckoning), unique and
      duplicated IDs; (RQ2) closed loop and safety: exploration, missions, refusal of unsafe requests,
      invalid moves; (RQ3) models and transfer: accuracy per second and per dollar, loss on real-car logs.
      Label them `RQ1`–`RQ3` in the text so Sections IV–VI can refer to them.
   5. **Contributions.** An `itemize` of three or four items, chosen by status:
      - always: the L2 agent design (the LLM owns the belief, the map and every SLAM decision through
        single-timestep tools, below a deterministic validator);
      - always: the benchmark design (identical replayed logs from simulation and the real car, the B0, B1, B2
        baselines, the metrics in Section~IV); write "proposed" for B2 and the oracle association until OD2/OD3
        are settled (R6);
      - only if M2.T12 is `done`: "results for <n> models", with `\bmnum{n.models.replay}` (M5.T4 adds the key;
        until then write the item as "an evaluation protocol" and add `pending:M5.T4` to `CLAIMS.md`);
      - do **not** claim that code or data are released (nothing in the repository says they will be).
   6. **Roadmap (1 sentence).** "Section~\ref{sec:related} reviews…, Section~\ref{sec:overview} describes…,
      Section~\ref{sec:experiments}…, Section~\ref{sec:results}…, and Section~\ref{sec:conclusion} concludes."
3. *Mac.* Replace the **first paragraph of Section II** (from "BeaconMind, the system proposed in this project,"
   to "…how BeaconMind differs.") with this two-sentence lead-in, because its content moved into I-3:
   "Four strands of prior work shape BeaconMind's design. For each, this section summarizes what was shown,
   what it leaves open, and how BeaconMind differs." Keep everything else in Section II unchanged (M5.T6 owns
   the trimming). Check that every term the deleted paragraph defined (LLM, SLAM, beacon, pose belief, loop
   closure) is now defined in Section I: `grep -n "pose belief\|loop closure\|beacon" Chen-Project-Report.tex | head`.
4. *Mac.* Add the R11 comment under `\section{Introduction}` and append `CLAIMS.md` rows for each factual claim
   about BeaconMind in I-3 and each contribution (sources: AGENT-DESIGN section, talk track line).
5. *Mac.* Run the check command and save its output as `evidence/M5/M5.T1/check_after.txt`
   (`python3 …/tools/check_report.py > …/evidence/M5/M5.T1/check_after.txt; tail -1 …/evidence/M5/M5.T1/check_after.txt`).
   Fix until the last line is `RESULT: PASS`. Render the pages that hold Section I and the start of Section II and
   look at them (visual check above). Word count of Section I for `notes.md`:
   `pdftotext …/report/Chen-Project-Report.pdf - | awk '/^I\. I NTRODUCTION/{f=1} /^II\. R ELATED/{f=0} f' | wc -w`
   (plain `pdftotext`, **not** `-layout`, which mixes the two columns; IEEEtran's small caps print as
   `I. I NTRODUCTION` and `II. R ELATED W ORKS`, checked 2026-10-06. If the awk prints 0, run
   `pdftotext … - | grep -n "NTRODUCTION\|ELATED"` and adjust the two patterns to what it prints).
6. *Mac.* Save the diff (definition above) to `evidence/M5/M5.T1/tex.diff`.

**Deliverables.**
- `course-project/report/Chen-Project-Report.tex` (Section I written; Section II first paragraph replaced)
- `course-project/report/CLAIMS.md` (rows `C-I-*`)
- `course-project/report/Chen-Project-Report.pdf` (rebuilt)

**Tests.**
- Unit tests: none (prose).
- Smoke test (Mac): `python3 course-project/tools/check_report.py` → `RESULT: PASS`; `placeholders:` one fewer
  than in `check_before.txt`.
- Content check (Mac): `grep -c "RQ[123]" course-project/report/Chen-Project-Report.tex` ≥ 3;
  `grep -n "design stage" course-project/report/Chen-Project-Report.tex` prints nothing.

**Acceptance criteria.**
- [ ] Section I has context, gap, BeaconMind paragraph, RQ1–RQ3 list, contributions, roadmap.
- [ ] LLM, SLAM, beacon and loop closure are defined in Section I before Section II uses them.
- [ ] Section II's first paragraph is the two-sentence lead-in; the rest of Section II is unchanged
      (`tex.diff` shows no other Section II hunk).
- [ ] No contribution claims a result that has no evidence (R2, R5); proposed items say "proposed" (R6).
- [ ] `check_after.txt` shows `RESULT: PASS`.
- [ ] `CLAIMS.md` has a row for every BeaconMind claim in Section I.

**Evidence to save.** `course-project/evidence/M5/M5.T1/`: `check_before.txt`, `check_after.txt` (checker
outputs), `tex.diff`, `notes.md` (word count from `pdftotext` of the section, pages rendered and looked at).

**Pitfalls and known gotchas.**
- Do not describe BeaconMind from APPROACH (R1; `report/REVIEW.md` round 1, critical).
- The talk track's three research questions supersede APPROACH §4's four; RQ2 there (association) is folded into
  RQ1 in the accepted proposal.
- "The project is at the design stage" (old Section II) must not survive anywhere once results exist.
- The novelty sentence rests on a search of 2026-09-27 and 27 papers; an LLM-guided pedestrian dead-reckoning
  paper (Sensors 2026) was never opened (`report/REVIEW.md` "Open issues" item 2). Keep the hedge "to my
  knowledge"; M5.T6 re-checks it.

**Stop-and-ask conditions.** Section I cannot fit the M5.T8 target without dropping a research question or a
contribution; the talk track and AGENT-DESIGN disagree about what the agent decides (R14).

**Estimated effort.** S.

**AI-disclosure note.** Comment under the section: `% AI-assisted (<model>, <date>): drafted Section I and the
Section II lead-in.` Ledger row: "Section I, Section II lead-in — <model> via <tool> — drafted".

---

### M5.T2 — System Overview, with the architecture figure

**Why.** Section III describes the system the experiments test: the responsibility split (AGENT-DESIGN "The v3
split"), the hardware and the twin, perception and the observation (D5, C3), the tools (D5, C4), the per-step
procedure (D7), the report (D8), safety (D6) and the runtimes (D10). It is writable now from AGENT-DESIGN v3.3,
with the R2 wording for parts that are not built yet; M5.T3 re-syncs it to v3.4. The architecture figure is the
paper's main picture and is reused in the M6 slides.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M5.T8 done | task | `python3 …/tools/task_status.py M5.T8` (Mac) | `done` |
| TikZ and standalone | software | `kpsewhich tikz.sty standalone.cls` (Mac) | two paths (verified 2026-10-05) |
| Implementation status (soft) | tasks | for each task in step 2's table: `python3 …/tools/task_status.py <ID>` (Mac) | `done` → "built" wording; anything else → "planned" wording |

**Inputs.** `AGENT-DESIGN.md` (whole file; v3.4 if it exists — `head -1 course-project/AGENT-DESIGN.md`);
`plan/README.md` §6 C1–C5, C9, C11, C12, §8; `CONTEXT.md` "Hardware state"; `reference/hardware/wiring-plan.md`
§4 (pins, only if you mention them — prefer not to); `proposal-talk-track.md` lines 33–53 (system paragraph);
`assignments/assignment4/system-prompt/evidence/smoke-test.md` (only to cite the prompt's token count, 4,352).

**Steps.**
1. *Mac.* Run the check; save `evidence/M5/M5.T2/check_before.txt`.
2. *Mac.* Fill this status table in `evidence/M5/M5.T2/status.md` by running the check command for each task.
   It decides the tense of each sentence (R2):

   | Component | Task whose `done` makes it "built" | Built wording | Not-built wording |
   | --- | --- | --- | --- |
   | Geometry tools (reference implementation) | already built: `assignments/assignment4/system-prompt/tools/l2_geometry.py` (AGENT-DESIGN "Design values": self-checks pass) | "are implemented" | — |
   | System prompt v3.3 | already built (4,352 tokens, AGENT-DESIGN D10) | "the prompt (4,352 tokens)" | — |
   | Tool dispatch, validator, observation builder, report checks | M2.T1, M2.T13, M2.T14 (all three) | "implemented in Python" | "specified; implementation planned" |
   | Isaac Sim twin | M2.T5 | "an Isaac Sim <version from M1.T5> twin publishes…" | "a planned Isaac Sim twin will publish…" |
   | Camera, detector pipeline | M1.T6, M1.T12 (camera → `apriltag_ros`); M1.T8 (noise) | "measured range/bearing noise" (only if M1.T8 is `done`) | "to be calibrated" |
   | Pico move firmware, watchdog, out-of-band STOP | M3.T6, M3.T7, M3.T13 | "passed the wheels-down gate" (with the measured STOP time from `evidence/M3/M3.T7/`) | "planned" |
   | Harness, replay | M2.T7 | "implemented" | "planned" |
   | ROSA demo | M6.T2 (MCP server) and M6.T9 (runs in the twin) | "runs the same tools as MCP servers" | "is planned as the demonstration runtime" |

3. *Mac.* Create the architecture figure source `course-project/report/figures/src/fig-architecture.tex`
   (standalone TikZ) with exactly this content (fill in `<model>` and `<date>` only). It was compiled and rendered
   on the Mac on 2026-10-06 by the plan reviewer: natural size 526 × 250 pt, no Type 3 font, no overlapping text.
   Do not add, remove or rename nodes; wording changes only if AGENT-DESIGN v3.4 changes a component (R14).
   ```latex
   % AI-assisted (<model>, <date>): drew the BeaconMind architecture figure from AGENT-DESIGN D5/D6/D10 and README C12.
   \documentclass[tikz,border=2pt]{standalone}
   \usetikzlibrary{arrows.meta,calc}
   \begin{document}
   \begin{tikzpicture}[font=\footnotesize,
       box/.style={draw, rounded corners=1pt, align=center, minimum height=9mm, text width=28mm},
       llm/.style={box, fill=black!8, very thick},
       lab/.style={fill=white, inner sep=1pt, align=center},
       >={Stealth[length=1.8mm]}]
     \node[box] (cam)    at (0, 0)      {ESP32-CAM\\JPEG frames};
     \node[box] (pico)   at (0, -2.4)   {Pico 2 W: encoders,\\BNO055, bounded-\\move executor,\\watchdog};
     \node[box] (det)    at (3.5, 0)    {image\_proc +\\apriltag\_ros:\\tag detections};
     \node[box] (bridge) at (3.5, -2.4) {Pico bridge:\\odometry (chord\\at mid-heading)};
     \node[box] (obs)    at (7.0, -1.2) {Observation builder\\(robot stopped,\\$N$ frames)};
     \node[box] (base)   at (7.0, -3.4) {Baselines B0, B1, B2\\(same logs)};
     \node[box] (tools)  at (11.4, 1.1) {Single-timestep tools\\(odometry, gate, fix,\\map, predict,\\explore)};
     \node[llm] (llm)    at (11.4, -1.2) {LLM agent\\vLLM (local)\\or provider API};
     \node[box] (eval)   at (11.4, -5.9) {Evaluator\\(ground truth,\\metrics)};
     \node[box] (rep)    at (14.9, -1.2) {Belief report\\(pose, map, decision)};
     \node[box] (val)    at (14.9, -3.4) {Validator\\(move set, limits,\\safety flags, latch)};
     \node[box, dashed] (twin) at (0, -5.9) {Isaac Sim twin:\\replaces camera,\\Pico and car;\\ground-truth pose};
     \draw[->] (cam) -- (det);
     \draw[->] (pico) -- (bridge);
     \draw[->] (det.east) -- (obs.north west);
     \draw[->] (bridge.east) -- (obs.south west);
     \draw[->] (obs) -- node[lab, above=1mm] {step\\message} (llm);
     \draw[<->] (llm) -- node[lab, right=1mm] {tool calls} (tools);
     \draw[->] (llm) -- (rep);
     \draw[->] (rep) -- node[lab, right=1mm] {one move} (val);
     \draw[->] (val.south) -- (14.9, -4.6) -- node[lab, pos=0.45] {bounded move (Wi-Fi)} (0, -4.6) -- (pico.south);
     \draw[->] (obs) -- node[lab, right=1mm] {observation logs} (base);
     \draw[->] (base.east) -| (eval.north);
     \draw[->] (rep.east) -- ++(0.45, 0) |- (eval.east);
     \draw[->, dashed] (twin) -- node[lab] {ground truth} (eval);
     \draw[->, dashed] ($(twin.north)+(-0.8,0)$) -- ($(pico.south)+(-0.8,0)$);
   \end{tikzpicture}
   \end{document}
   ```
   If AGENT-DESIGN v3.4 exists and names a different detector or component, change only that box's text.
   Build it (Mac):
   ```bash
   mkdir -p /Users/xiaohuichen/Projects/EN.665.715/course-project/report/figures/src && \
   cd /Users/xiaohuichen/Projects/EN.665.715/course-project/report/figures/src && \
     latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir="$TMPDIR/bm-fig" fig-architecture.tex && \
     cp "$TMPDIR/bm-fig/fig-architecture.pdf" ../fig-architecture.pdf && \
     pdfinfo ../fig-architecture.pdf | grep "Page size"
   ```
   **Size check (keeps the text ≥ 7 pt at print size):** the figure is printed at `\textwidth` = 516 pt
   (7.16 in, IEEEtran two-column), so text at 8 pt prints at 8 × 516 / width. The printed width must be
   **≤ 590 pt** (expected 526 pt). If it is larger, reduce `text width` to 26mm and rebuild; if it is still
   larger, stop and ask.
   (`-outdir` keeps `.log`/`.aux` out of the repository; `.log` files under `report/figures/` are **not**
   git-ignored.) Then `pdffonts ../fig-architecture.pdf` must list no `Type 3`.
4. *Mac.* Under `\section{System Overview}\label{sec:overview}` replace `\laterdraft` with the following
   subsections (target length from M5.T8 step 6; default 1.3 pages including the figure and table):
   - `\subsection{Responsibility Split}\label{ssec:split}` — the stop–observe–decide–move cycle; what the LLM
     owns (pose belief, beacon map, every SLAM decision, the move choice); "tools compute every number and every
     gate flag; the LLM does no arithmetic beyond small integer counters" (AGENT-DESIGN "The v3 split"); single-
     timestep tools and why (D1b; nothing optimizes over history — that would be L3); stateless per-step calls
     carrying mission, operator request, observation and previous report (D5, D10). Insert the figure here:
     ```latex
     \begin{figure*}[t]
     \centering
     \includegraphics[width=\textwidth]{fig-architecture}
     \caption{BeaconMind architecture. … (state what is solid vs dashed; that the twin replaces camera, Pico and car
     with identical topics; that baselines read the same observation logs).}
     \label{fig:architecture}
     \end{figure*}
     ```
   - `\subsection{Platform and Simulation Twin}\label{ssec:platform}` — the car (Pico 2 W, TB6612FNG driver, two
     encoder motors, BNO055 in IMUPLUS, ESP32-CAM; no range sensor), the Spark (vLLM, Isaac Sim, the ROS 2 Humble
     container), Wi-Fi micro-ROS link, the twin (C12: same `/pico/*` interface through `sim_pico`). Use only
     facts from `CONTEXT.md` "Hardware state", README L5/C12 and AGENT-DESIGN; car dimensions only from
     `configs/car.json` if M1.T9 is done.
   - `\subsection{Observation}\label{ssec:observation}` — frames and units (C1: map frame = start pose, x toward
     the camera end, θ CCW), detector output as text (id, range, bearing, quality), odometry as a chord at
     mid-heading with gyro yaw, slip flags, status/error semantics, the precomputed `safety` flags (D5, C3). One
     short JSON-free description; do not paste the JSON.
   - `\subsection{Tools and Per-Step Procedure}\label{ssec:tools}` — a table `tab:tools` (`table` single column,
     `\footnotesize`, columns "Tool" and "Returns", one row per D5 tool, wording shortened from the D5 table;
     `move` and `emergency\_stop` may share a row); then the D7 procedure as a numbered list of six items
     (predict; associate with the gate classes matched/new/ambiguous/rejected; correct the pose with the
     `pose_source` ladder; update the map with tentative→confirmed at 2 observations and 0.40 m baseline and
     frozen confirmed anchors; loop closure accepted only inside a beacon fix; decide by the first matching
     row). Give the duplicated-ID labels `B<id>`, `B<id>b` (D3).
   - `\subsection{Belief Report and Safety Layers}\label{ssec:safety}` — the D8 report fields (one sentence); the
     harness is authoritative for state (D5: 0.005 m / 0.05°; a `state` violation, README C5 item 4); the four D6 layers
     (out-of-band STOP with persistent latch; validator and Pico caps, watchdog, stall/bump, boot id; prompt
     guardrails; the residual risk stated in the prompt). Only the out-of-band STOP and gate numbers that M3.T7
     measured may be stated as measured.
   - `\subsection{Runtimes}\label{ssec:runtimes}` — benchmark harness vs ROSA demo (D10: why ROSA is demo-only:
     47 built-in tools, 5,195 tokens of tool schemas and 819 tokens of fixed prompts; cite `royce2025rosa`); the
     three provider APIs (C11, no model prices here); sampling per model card; the logged hashes (L8).
5. *Mac.* Add `CLAIMS.md` rows (`C-III-*`) for every factual sentence; status per step 2.
6. *Mac.* Run the check; fix until `RESULT: PASS`. Render the page with Fig.~1 and the Section III pages; confirm
   that the figure text is readable at 100 % zoom and that the figure lands at the top of a page (IEEEtran puts
   `figure*` on the page **after** the one where it is defined; move the `figure*` block earlier in the source
   if it lands too late).
7. *Mac.* Save the check as `check_after.txt` and the diff as `evidence/M5/M5.T2/tex.diff` (definitions above).

**Deliverables.**
- `course-project/report/figures/src/fig-architecture.tex`, `course-project/report/figures/fig-architecture.pdf`
- `course-project/report/Chen-Project-Report.tex` (Section III, `tab:tools`, `fig:architecture`)
- `course-project/report/CLAIMS.md` (rows `C-III-*`)

**Tests.**
- Unit tests: none.
- Smoke tests (Mac): the figure build exits 0; `pdffonts course-project/report/figures/fig-architecture.pdf |
  grep -c "Type 3"` prints `0`; `check_report.py` → `RESULT: PASS`.
- Consistency test (Mac): every D5 tool name appears in the source, written with `\_`:
  ```bash
  cd /Users/xiaohuichen/Projects/EN.665.715/course-project/report && for t in compose_odometry gate_detection fix_pose \
    map_point update_beacon predict_observation exploration_summary move emergency_stop; do
    printf '%s %s\n' "$t" "$(grep -cF "${t//_/\\_}" Chen-Project-Report.tex)"; done
  ```
  Pass: nine lines, each count ≥ 1. Save as `evidence/M5/M5.T2/tools_check.txt`.
- Figure size test (Mac): `pdfinfo course-project/report/figures/fig-architecture.pdf | grep "Page size"` → width
  ≤ 590 pt (step 3).

**Acceptance criteria.**
- [ ] Six subsections present; Fig.~\ref{fig:architecture} and Table~\ref{tab:tools} referenced in the text.
- [ ] Every sentence about an unbuilt component uses the not-built wording of step 2; `status.md` saved.
- [ ] Every number in Section III is either a design value present in AGENT-DESIGN/`configs/dv.json` or a measured
      value with an evidence path in `CLAIMS.md`.
- [ ] No text in the figure is smaller than 7 pt at print size (check the render).
- [ ] `RESULT: PASS`.

**Evidence to save.** `course-project/evidence/M5/M5.T2/`: `check_before.txt`, `check_after.txt`, `status.md`,
`tex.diff`, `pdffonts.txt`, `tools_check.txt`, `notes.md` (pages rendered, the figure's page, the `pdfinfo` page size).

**Pitfalls and known gotchas.**
- Describe from AGENT-DESIGN, not APPROACH: APPROACH §5's diagram has a three-move set and "fusion mode TBD"
  (superseded by D4 and D5).
- `image_proc`, `apriltag_ros` and the twin are **unverified** until M1.T3/M1.T5 (README §9.1); use R2 wording.
- The Module 5 tilt firmware's "forward" is reversed relative to +x (C1 warning). Do not describe the tilt
  firmware as the project firmware.
- Underscores: `fix\_pose`, `gate\_detection` in text; inside `\texttt{}` still escape `_`.
- `figure*` cannot be placed at the bottom of a page in IEEEtran; `[t]` only.

**Stop-and-ask conditions.** AGENT-DESIGN v3.4 exists and contradicts something already written in Section III
(re-sync is M5.T3's job — note it and continue only if M5.T3 is next); a tool's behaviour in `l2_geometry.py`
differs from the D5 table (R14).

**Estimated effort.** M.

**AI-disclosure note.** Comment under the section and in `fig-architecture.tex`: `AI-assisted (<model>, <date>):
drafted Section III, Table <n> and the architecture figure.` Ledger row accordingly.

---

### M5.T3 — Experiments (protocol, conditions, baselines, metrics)

**Why.** Section IV states exactly what was run and how it is scored, so the results can be reproduced and
judged: arenas and conditions (C7), platform and sensing, arms and models (L2, B0, B1, B2, the roster; C11),
replay versus closed loop (D1d, C9), missions and budgets (D2, D4), metrics (C10) and statistics (C10.10). It
needs the open decisions settled (M1.T10) so that it does not describe a protocol that later changes.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M5.T2 done | task | `python3 …/tools/task_status.py M5.T2` (Mac) | `done` |
| M1.T10 done | task | `python3 …/tools/task_status.py M1.T10` (Mac) | `done` |
| AGENT-DESIGN v3.4 | file | `head -1 /Users/xiaohuichen/Projects/EN.665.715/course-project/AGENT-DESIGN.md` (Mac) | contains `v3.4` |
| Configs (soft) | files | `ls /Users/xiaohuichen/Projects/EN.665.715/course-project/configs/` (Mac) | `dv.json`; and if M1.T8/M1.T9 are done, `detector_noise.json`, `car.json`, `camera.json` |

**Inputs.** `AGENT-DESIGN.md` v3.4 (whole; and `git diff` against v3.3, see step 2); `plan/README.md` §3.5, §6
C0, C7–C11; `proposal-talk-track.md` lines 99–132 (metric application, statistics) and 201–212 (decisions to confirm); `APPROACH-LLM-SLAM.md` §8
(benchmark design); `configs/*.json`; the M2 file `plan/M2-sim-mvp.md` deliverables of M2.T2, M2.T8, M2.T9,
M2.T10 (what was actually implemented); `report/CLAIMS.md`.

**Steps.**
1. *Mac.* Run the check; save `evidence/M5/M5.T3/check_before.txt`.
2. *Mac.* **Re-sync Section III to v3.4.** Find the last commit whose `AGENT-DESIGN.md` is still v3.3, then
   diff the **working tree** against it (v3.4 may be uncommitted, because nothing is committed without
   Xiaohui's request, L10; so do not diff against `HEAD`):
   ```bash
   cd /Users/xiaohuichen/Projects/EN.665.715 && \
   for h in $(git log --format=%h -- course-project/AGENT-DESIGN.md); do
     git show "${h}:course-project/AGENT-DESIGN.md" | head -1 | grep -q "v3\.3" && { echo "v3.3 commit: ${h}"; V33=${h}; break; }
   done; \
   git diff "${V33}" -- course-project/AGENT-DESIGN.md > course-project/evidence/M5/M5.T3/agent-design-v33-v34.diff; \
   wc -l course-project/evidence/M5/M5.T3/agent-design-v33-v34.diff
   ```
   Expected: one `v3.3 commit: <hash>` line and a non-zero line count. No `v3.3 commit` line, or 0 lines while
   `head -1 course-project/AGENT-DESIGN.md` says v3.4 → stop and ask (README §1.4 item 3). For each changed decision, find the sentence
   in Sections I–III that states it (`grep -n`) and update it. Turn every `proposed:OD<k>` row of `CLAIMS.md`
   whose OD is now settled into `ok` and delete the word "proposed" from the matching sentence — including the
   four in Section II (refusal suite, B2, oracle association, stretch conditions). If an OD was settled
   **differently** from the default, rewrite the sentence to the settled choice.
3. *Mac.* Under `\section{Experiments}\label{sec:experiments}` replace `\laterdraft` with:
   - `\subsection{Arenas and Conditions}\label{ssec:arenas}` — simulated arenas generated from seeds (C7:
     convex rectangle 2.0–2.5 m a side, walls ≥ 0.30 m, 10–16 tags on walls spaced ≤ 0.8 m, beacon IDs 0–29,
     start pose ≥ 0.5 m from walls); conditions `unique` and `duplicated` (≤ 3 IDs twice, ≥ 1.5 m apart),
     `hidden` only if M4.T9 ran; dev seeds for tuning and held-out test seeds (C7 "Seeds"). Leave the comment
     `% FIGURE: arena (inserted by M5.T4)` at the end of this subsection and a claim row `pending:M5.T4`: the
     arena figure shows the world of the representative episode, which only M5.T4 chooses. The real arena: one paragraph,
     `pending:M3.T10` until M5.T13.
   - `\subsection{Sensing and Observation Pipeline}\label{ssec:sensing}` — camera calibration and HFOV (from
     `configs/camera.json` if M1.T7 is done), detector noise model (`configs/detector_noise.json`, M1.T8), the
     detection pipeline values `obs_settle_s`, `obs_frames`, `obs_min_frames` from `configs/dv.json` (C3),
     ground truth (C8: Isaac transform in sim; overhead camera with 5 cm / 3° acceptance on the car).
   - `\subsection{Arms, Baselines and Models}\label{ssec:arms}` — L2 (Section III); B0 dead reckoning; B1 GTSAM
     iSAM2 planar factor graph with oracle association when IDs repeat, an upper bound (cite
     `kaess2012isam2`; OD3); B2 the D7 procedure as code with the same tools (OD2); the random explorer R only if
     M4.T5 ran it (M4 adds arm `R`); L1/L3/N/V only if their M4 tasks (M4.T7–M4.T9) are `done`. The model roster: M5.T13 adds it from the frozen pre-registration, and M5.T14 replaces it with M4.T16's generated `tables/tab_roster.tex` — for now one sentence
     "The roster is fixed in the pre-registration" plus `pending:M4.T1`. Provider APIs and sampling (C11, D10).
   - `\subsection{Protocol}\label{ssec:protocol}` — replay (recorded observations, the model only estimates,
     decision `NONE`, moves refused; C9.2 replay rule) and closed loop (the agent's move executes); missions and
     step budgets (`steps_explore`, `steps_navigation` from `dv.json`); K repeats per seed; the frontier budget cap
     ($100 pilot, AGENT-DESIGN "API budget"); what each run logs (prompt, tool-schema and DV hashes; L8).
   - `\subsection{Metrics and Statistics}\label{ssec:metrics}` — use these equations verbatim (they restate C10.1
     and C10.5):
     ```latex
     \begin{equation}
     \mathrm{ATE}=\Big(\frac{1}{|\mathcal{T}|}\sum_{t\in\mathcal{T}}
       \big\lVert\mathbf{p}^{\mathrm{est}}_t-\mathbf{p}^{\mathrm{gt}}_t\big\rVert^{2}\Big)^{1/2}
     \label{eq:ate}
     \end{equation}
     ```
     with $\mathbf{p}$ the planar position in the map frame (start pose), $\mathcal{T}$ the steps with both
     values, **no alignment** (primary; OD5); then aligned ATE (SE(2) Umeyama, cite `sturm2012benchmark`), final
     pose error, RPE per metre as secondary. Map: correct entry within `0.30~m` of a tag with that ID (C10.3),
     phantoms, map RMSE, ID precision/recall. Association TP/FP/FN as C10.4, precision primary. Missions decided
     by the evaluator from ground truth at DONE (C10.5) and
     ```latex
     \begin{equation}
     \mathrm{SPL}=\frac{1}{N}\sum_{i=1}^{N}S_i\,\frac{\ell_i}{\max(p_i,\ell_i)}
     \label{eq:spl}
     \end{equation}
     ```
     with $\ell_i$ the straight-line distance from the mission start to the success region (cite
     `anderson2018evaluation`). Refusal (C10.6), validity (C10.7), latency p50/p95 with the 60~s gate and cost
     (C10.8). Statistics (C10.10): seed as the unit, Friedman then Holm-corrected Wilcoxon, exact McNemar on the
     first repeat, seed-clustered bootstrap CIs. New references for Friedman/Wilcoxon/Holm/McNemar or Umeyama
     are optional; if added, follow R7.
4. *Mac.* `CLAIMS.md` rows `C-IV-*` for every protocol fact with the config key or contract as source.
5. *Mac.* Run the check; fix until `RESULT: PASS`; render the Section IV pages.
6. *Mac.* Save the diff to `evidence/M5/M5.T3/tex.diff`.

**Deliverables.** `course-project/report/Chen-Project-Report.tex` (Section IV; Sections I–III re-synced);
`course-project/report/CLAIMS.md`; `course-project/evidence/M5/M5.T3/agent-design-v33-v34.diff`.

**Tests.**
- Unit tests: none.
- Smoke test (Mac): `check_report.py` → `RESULT: PASS`.
- Consistency tests (Mac), results written to `notes.md`:
  1. `grep -n "proposed" course-project/report/Chen-Project-Report.tex` — for every hit, name the `CLAIMS.md` row
     it belongs to; each must be a `proposed:OD<k>` row whose OD is still open in AGENT-DESIGN v3.4. A hit for a
     settled OD, or a `proposed:` row whose sentence lacks the word, is a failure to fix.
  2. Every design value quoted in Sections III–IV equals `configs/dv.json` (M1.T2 layout:
     `{"schema": "bm.dv/1", "values": {<key>: {"value", "unit", "status", …}}}`). For each quoted key run
     `python3 -c "import json,sys;v=json.load(open('/Users/xiaohuichen/Projects/EN.665.715/course-project/configs/dv.json'))['values'][sys.argv[1]];print(sys.argv[1],v['value'],v['unit'],v['status'])" <key>`
     and write the printed line next to the sentence. A `KeyError` means the key does not exist → do not quote the
     value; stop and ask if AGENT-DESIGN states it (R14).

**Acceptance criteria.**
- [ ] Section IV has the five subsections; Eq.~\eqref{eq:ate} and Eq.~\eqref{eq:spl} present and referenced.
- [ ] Every metric definition matches README C10 (same thresholds, same primary/secondary split).
- [ ] Sections I–III and Section II's "proposed" wording match AGENT-DESIGN v3.4.
- [ ] `pending:` rows exist for everything that waits on M4.T1, M3.T10, M3.T17, M5.T4.
- [ ] `RESULT: PASS`.

**Evidence to save.** `course-project/evidence/M5/M5.T3/`: `check_before.txt`, `check_after.txt`,
`agent-design-v33-v34.diff`, `tex.diff`, `notes.md`.

**Pitfalls and known gotchas.**
- APPROACH §8 T1 uses **aligned** ATE as primary; the talk track and OD5 make **unaligned** primary. Follow the
  settled OD5.
- Loop closures are rare at these DVs (AGENT-DESIGN D8 "Example 1 is a constructed step": 1 step with any loop
  closure in 300 runs). Say closures are pooled and counted (C10.4); do not promise a loop-closure precision.
- `done_range_m` 0.55 is a placeholder until M1.T8/M1.T9 (C0). Quote the value in `dv.json`, with its status.
- Do not write episode counts before M4.T1 freezes them.

**Stop-and-ask conditions.** v3.4 settles an OD in a way that makes a Section II claim false (Section II was graded;
Xiaohui decides whether to change it); `configs/dv.json` and AGENT-DESIGN disagree on a value (R14).

**Estimated effort.** M.

**AI-disclosure note.** `% AI-assisted (<model>, <date>): drafted Section IV and re-synced Sections I–III to
AGENT-DESIGN v3.4.`

---

### M5.T4 — Results and Evaluation (tables and figures generated from `data/`, never typed by hand)

**Why.** Section V answers RQ1–RQ3 with the first complete result, M2.T12 (the cut line: 2–3 models against B0,
B1, B2 in replay with duplicated IDs, plus closed-loop simulated episodes; README §3.1, §3.4). Every number goes
through the M5.T9 pipeline and every figure through M5.T10, so the text cannot drift from the data (R3).

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M5.T3, M5.T9, M5.T10 done | task | `for i in M5.T3 M5.T9 M5.T10; do python3 …/tools/task_status.py $i; done` (Mac) | three lines `done` |
| M2.T12 done | task | `python3 …/tools/task_status.py M2.T12` (Mac) | `done` |
| M2.T12 evidence on the Mac | files | `ls /Users/xiaohuichen/Projects/EN.665.715/course-project/evidence/M2/M2.T12/` (Mac) | CSV files listed |
| Spark reachable (for figures) | service | `ssh -o ConnectTimeout=15 -o BatchMode=yes xiaohui_chen@spark-2a60 'ls ~/Projects/EN.665.715/course-project/data/runs | head -3'` (Mac) | run directories listed |

**Inputs.** `plan/M2-sim-mvp.md` task M2.T12 (its Deliverables and Acceptance criteria; M2's exit criterion 6:
`evidence/M2/M2.T12/results.md` with a table and figure generated by `python -m beaconmind.results.first_result`)
and M2.T10 (the per-episode `episodes.csv` columns: `run_id, arm, model_key, episode_id, world_id, source,
condition, mode, mission, …, ate_unaligned_m, …` — **no `seed` column**; the seed is the `-s<seed>` suffix of
`world_id`); every CSV and `.md` in `evidence/M2/M2.T12/`; `report/assets.json`; `tools/report_assets.py --help`;
`tools/report_figures.py --help`; `report/CLAIMS.md`.

**Steps.**
1. *Mac.* Run the check; save `evidence/M5/M5.T4/check_before.txt`.
2. *Mac.* **Discover the inputs.** Read M2.T12's Deliverables. Copy the list of result CSV paths into
   `evidence/M5/M5.T4/inputs.md` with `wc -l` and the header line of each (`head -1`). If the CSVs on the Mac are
   older than the Spark's (`ssh … 'sha256sum ~/Projects/EN.665.715/course-project/evidence/M2/M2.T12/*.csv'`
   vs `shasum -a 256` on the Mac differ), pull them first:
   `/Users/xiaohuichen/Projects/EN.665.715/course-project/tools/pull_evidence.sh M2 M2.T12`.
   M2.T12 step 8 delivers this as `evidence/M2/M2.T12/summary_long.csv` (columns
   `arm,model_key,source,condition,mode,mission,metric,n,median,q1,q3,mean,pooled`) plus `episodes.csv`
   (cross-plan consistency review, 2026-10-06); use those two files as the sources.
   **Branch:** if `summary_long.csv` is absent or its header differs from that list → stop and ask (M2.T12 must
   deliver tables in CSV; do not compute them here).
   Also record the **exact spellings** used in the CSVs, because `where` filters compare strings exactly:
   `python3 -c "import csv,sys;r=list(csv.DictReader(open(sys.argv[1])));[print(c,sorted({x[c] for x in r})) for c in ('arm','model_key','condition','source','mode') if c in r[0]]" <csv>`
   for each CSV, into `inputs.md`. (The condition may be spelled `duplicated` or `dup`; use what is printed.)
3. *Mac.* **Declare the assets.** Edit `course-project/report/assets.json`: add each CSV under `sources`, and
   add `numbers`, `tables` and `targets` entries (format in M5.T9). Required content for the first result:
   - Table `tab-replay` (RQ1): rows = arms (B0, B1, B2, each L2 model); columns = median unaligned ATE (m) with
     IQR, aligned ATE, final position error (m) / heading error (deg), map RMSE (m), phantoms, association
     precision and recall; condition `duplicated` (and `unique` if M2.T12 ran it); `source` sim.
   - Table `tab-closed` (RQ2), if closed-loop episodes exist: per model, missions run, success rate with CI, SPL,
     tags mapped (%), refusal rate, unsafe requests executed, invalid move attempts per 100 decisions.
   - Numbers used in the text: at least `n.models.replay`, `n.seeds.replay`, `k.repeats`, the best L2 model's
     median ATE, B0's and B1's median ATE, the association precision of the best L2 model, latency p95 per model,
     cost per episode for any API model. Key names follow "Generated-number key names" above (for example
     `ate.replay.dup.l2.qwen35-a3b-think.median`, `ate.replay.dup.b1.median`). Counts (`n.models.replay`,
     `n.seeds.replay`, `k.repeats`) use `"agg": "count_distinct"` over the right column (M5.T9), never a typed
     number. The IQR is shown in the same cell as the median with a multi-field column (`"fields"` +
     `"pattern": "{0} [{1}, {2}]"`, M5.T9).
   - Targets (C10.11) that M2.T12 can already test, each with its threshold and comparator.
4. *Mac.* `python3 /Users/xiaohuichen/Projects/EN.665.715/course-project/tools/report_assets.py` → expected last
   line `assets: wrote <n> numbers, <m> tables, <k> targets`. Inspect `report/generated/tab-replay.tex`.
5. *Spark host* (via ssh from the Mac, inside `tmux new -s bm` or `tmux attach -t bm`). **Figures.** Make the
   trajectory figure for the representative episode and the arena figure of that episode's world (M5.T10 CLI;
   commands in M5.T10 step 8):
   1. Choose the model: the L2 model whose `ate.replay.dup.l2.<model_key>.median` is smallest in
      `report/generated/numbers.json` (ties → the model key that sorts first). Write it in `notes.md`.
   2. Pick the episode with `report_figures.py pick --episodes-csv <the per-episode episodes.csv that M2.T12's
      deliverables name, on the Spark> --arm L2 --model-key <model_key> --condition <spelling from inputs.md>
      --metric ate_unaligned_m > ~/bm-pick.txt; cat ~/bm-pick.txt` (rule in M5.T10: lower median of the per-episode
      ATE, ties → lowest seed). Copy the printed line into `evidence/M5/M5.T4/pick.txt`.
   3. `world_id` = the episode ID without its `-<mission>-k<repeat>` suffix (README L2):
      `echo "<episode_id>" | sed -E 's/-[A-Z_]+-k[0-9]+$//'`; check `ls data/worlds/<world_id>.json` exists. If it
      does not → stop and ask (README §1.4 item 3).
   4. Run the M5.T10 step 8 `trajectory` command with the run-log files of L2 (that model), B0 and B1 for that
      episode (`ls data/runs/*/<episode_id>.jsonl`; the arm is the second-to-last `-` part of the run ID, README L2)
      and the `arena` command for `<world_id>`. Both write into `report/figures/generated/`.
   Pull the PDFs:
   ```bash
   ssh -o ConnectTimeout=15 -o BatchMode=yes xiaohui_chen@spark-2a60 \
     'cd ~/Projects/EN.665.715 && tar czf - course-project/report/figures/generated' \
     | tar xzf - -C /Users/xiaohuichen/Projects/EN.665.715
   ```
6. *Mac.* Under `\section{Results and Evaluation}\label{sec:results}` replace `\laterdraft` with:
   - In Section IV-A, replace the comment `% FIGURE: arena (inserted by M5.T4)` with a single-column `figure`
     (`\includegraphics[width=\columnwidth]{fig-arena-<world_id>}` — found through `\graphicspath` in
     `figures/generated/`; `\label{fig:arena}`; caption: the
     world ID, its size, tag count and duplicated pairs from the `arena` command output, simulation, and the
     map-frame/arena-frame note), and set its `CLAIMS.md` row `pending:M5.T4` → `ok`.
   - `\subsection{Estimation in Replay (RQ1)}\label{ssec:rq1}` — `\input{generated/tab-replay}`; the trajectory
     figure (`figure`, `width=\columnwidth`, caption states episode id, condition, sim, replay, and that it was
     chosen by the median rule, not by hand); 2–3 paragraphs: L2 vs B0 vs B1 using `\bmnum`; association precision
     with duplicated IDs; what the trajectory figure shows. Use the pre-registered/targets outcome table if
     generated (`\input{generated/tab-targets}`).
   - `\subsection{Closed Loop and Safety (RQ2)}\label{ssec:rq2}` — only what closed-loop runs exist; otherwise one
     sentence that closed-loop results are in M5.T14 scope, with `pending:M5.T14`.
   - `\subsection{Models, Cost and Transfer (RQ3)}\label{ssec:rq3}` — latency p50/p95 per model (60 s gate), cost,
     real-log replay only if M3.T19 is `done` (replay of the arms on the real logs); else `pending:M5.T14`.
   - Leave a comment `% SUBSECTION Discussion and Limitations: M5.T5` at the end of the section.
   **Wording rules:** state every comparison with its number and direction; never "significantly" unless an
   M2.T12/M4.T16 test output says so (with the test name); a target that is not met is written as "not met" with
   the number; no adjective that the numbers do not support ("robust", "strong").
7. *Mac.* `CLAIMS.md` rows `C-V-*`: one per interpretive sentence, source = the `\bmnum` keys or table it rests on.
8. *Mac.* Run `python3 course-project/tools/report_assets.py --check` (expect `assets: up to date`) and the report
   check; fix until `RESULT: PASS`. Render the Section V pages.
9. *Mac.* Save the diff and copies of `report/generated/MANIFEST.txt` to `evidence/M5/M5.T4/`.

**Deliverables.** `course-project/report/assets.json`; `course-project/report/generated/*` (numbers, tables,
manifest); `course-project/report/figures/generated/fig-traj-<episode_id>.pdf`,
`fig-arena-<world_id>.pdf`; `course-project/report/Chen-Project-Report.tex` (Section V); `CLAIMS.md`.

**Tests.**
- Unit tests: those of M5.T8, M5.T9 and M5.T10 still pass (Mac: `cd /Users/xiaohuichen/Projects/EN.665.715/course-project/beaconmind
  && ../.venv/bin/python -m pytest -q tests/test_report_assets.py tests/test_check_report.py tests/test_report_figures.py`
  → `40 passed, 3 skipped`, i.e. 19 + 13 + 8 with the 3 matplotlib tests skipped).
- Smoke tests (Mac): `report_assets.py --check` → `assets: up to date`; `check_report.py` → `RESULT: PASS` with
  `missing numbers: 0`.
- Traceability test (Mac): for three `\bmnum` keys picked at random
  (`cd …/report && grep -o '\\bmnum{[^}]*}' Chen-Project-Report.tex | sort -u | sort -R | head -3`; macOS has no
  `shuf`), find each key's `number <key> = <value> <- <source> row <n>` line in `report/generated/MANIFEST.txt`,
  open that CSV row (`sed -n '<n+1>p' <csv>`; row 1 is the header) and confirm the printed value equals the CSV
  value after the declared format; write the three checks in `notes.md`.

**Acceptance criteria.**
- [ ] Section V-A has the generated replay table and the trajectory figure, with `\bmnum` numbers only.
- [ ] `sed -n '/section{Results and Evaluation}/,/section{Conclusion}/p' course-project/report/Chen-Project-Report.tex
      | grep -nE "[0-9]+\.[0-9]+|[0-9]+ ?(\\%|seeds|episodes|runs|models|of)"` finds no hand-typed result number
      (design values are allowed; list each hit and its `configs/dv.json` key in `notes.md`).
- [ ] The representative episode was chosen by the rule, recorded in `notes.md` with the `pick` output.
- [ ] Labels (R4) on every table and figure caption.
- [ ] `--check` up to date; `RESULT: PASS`.

**Evidence to save.** `course-project/evidence/M5/M5.T4/`: `check_before.txt`, `check_after.txt`, `inputs.md`,
`assets_run.txt` (output of step 4), `pick.txt` (output of the pick command), `MANIFEST.txt`, `tex.diff`, `notes.md`.

**Pitfalls and known gotchas.**
- A result CSV regenerated on the Spark after the pull silently changes the truth; `MANIFEST.txt` records SHA-256
  and `--check` detects it. Always pull before generating.
- `%` and `_` inside generated table cells must be escaped (M5.T9 test).
- `flushend` (preamble) can misplace floats on the last page; if a figure jumps or overlaps on the last page,
  remove `\usepackage{flushend}` and balance with `\IEEEtriggeratref{<n>}` instead (IEEEtran HOWTO).
- Do not copy numbers from M2.T12's narrative `.md`; use the CSV only.

**Stop-and-ask conditions.** M2.T12's numbers contradict its own narrative or acceptance criteria; a target is
missed and Xiaohui has not seen it yet (tell them before writing it up); a figure would show anything from a real
camera frame with a person in view (R13).

**Estimated effort.** M.

**AI-disclosure note.** `% AI-assisted (<model>, <date>): drafted Section V from generated tables and numbers.`

---
### M5.T5 — Conclusion and limitations

**Why.** A reader must be able to judge what the results do and do not show. This task writes the Discussion and
Limitations subsection at the end of Section V (the instructor's template has no separate Discussion section,
`report/sources/template-conference_101719.tex`) and Section VI, Conclusion, which answers RQ1–RQ3 in one
sentence each. It also closes every `pending:` claim: resolved claims become `ok`; claims whose task was dropped
become limitations.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M5.T4 done | task | `python3 …/tools/task_status.py M5.T4` (Mac) | `done` |
| M5.T14 done or dropped | task | `python3 …/tools/task_status.py M5.T14` (Mac) | `done` or `dropped (cut line)` |

**Inputs.** The whole `.tex`; `report/CLAIMS.md`; `report/generated/numbers.json` and `tab-targets.tex`;
`plan/README.md` §3.4 (cut line), C10.11 (targets); `AGENT-DESIGN.md` D1c (scope), D6 item 4 (residual risk), D8
("Example 1 is a constructed step" — loop closures are rare); the status tables of `plan/M1`–`M4` (which tasks
were dropped); `configs/dv.json` (how many values are still `status: "DV"`).

**Steps.**
1. *Mac.* Run the check; save `check_before.txt`.
2. *Mac.* **Resolve pending claims.** For each `pending:<ID>` row in `CLAIMS.md`, run `python3 …/tools/task_status.py <ID>`.
   `done` → update the sentence to the built/measured wording with the evidence path, set `ok`.
   `dropped (cut line)` or not done → rewrite the sentence so it no longer implies the work exists, add the point
   to the limitations list (step 3), set `ok` with source "limitation". Record each decision in `notes.md`.
3. *Mac.* Replace the comment `% SUBSECTION Discussion and Limitations: M5.T5` with
   `\subsection{Discussion and Limitations}\label{ssec:discussion}`: one paragraph per RQ interpreting the
   numbers already in Section V (no new numbers except `\bmnum`), then a limitations paragraph or `itemize`.
   Include each of these **only if it applies, each with its source in `CLAIMS.md`**:
   - arena scope: small, convex, empty, tags only on walls; no obstacle sensing (D1c, C7);
   - loop closures were rare (give the pooled count as `\bmnum{loopclosures.replay.dup.<arm>[.<model_key>].count}`
     only if a result CSV has a row with the pooled count — M4.T16's association table CSV or an M2.T12 summary
     row; never sum the per-episode `loop_closures` column here; D8 "Example 1 is a constructed step");
   - B1 used oracle association when IDs repeat, so it is an upper bound, not a competitor (OD3);
   - one model-agnostic prompt; model behaviour may depend on it (D10);
   - simulation fidelity: detector noise from the M1.T8 model; the kinematic-simulator fallback if used
     (README §3.4; label every such result per R4);
   - real-car evidence: number of real logs (M3.T12), ground-truth camera error (C8, `evidence/M3/M3.T17/`),
     Wi-Fi link quality (`CONTEXT.md` "Hardware state");
   - results from the kinematic simulator (M4.T5's closed-loop sweep, or the README §3.4 fallback), labelled per R4;
   - design values still unmeasured: count them with
     `python3 -c "import json;v=json.load(open('/Users/xiaohuichen/Projects/EN.665.715/course-project/configs/dv.json'))['values'];print(sum(x['status']=='DV' for x in v.values()), 'of', len(v))"`
     and type the two numbers with a `CLAIMS.md` row naming the file, the command and the date (a count of
     configuration entries is a design fact, not an experimental result, so R3 allows typing it);
   - model identity and price dates (C11 `price_checked`); the frontier budget cap limiting episodes;
   - stretch arms (L1, L3, N, V) and the hidden-ID condition not run (if not run);
   - the ROSA demo is not benchmark-comparable (D10);
   - every pre-registered target that was not met, by name.
4. *Mac.* Under `\section{Conclusion}\label{sec:conclusion}` replace `\laterdraft` with two paragraphs (target
   0.2 page): (a) one sentence per RQ with the headline `\bmnum` numbers and the direction of the result —
   a negative result is stated as plainly as a positive one; (b) future work limited to items the design
   documents name (L1/L3 arms, hidden IDs, image ablation, larger arenas, APPROACH §10 W6), without promises.
5. *Mac.* Run `report_assets.py --check` and the report check; render the pages; save diff.

**Deliverables.** `course-project/report/Chen-Project-Report.tex` (V-D, VI); `CLAIMS.md` with zero `pending:` rows.

**Tests.**
- Unit tests: none.
- Smoke tests (Mac): `grep -c "pending:" course-project/report/CLAIMS.md` → `0`; `check_report.py` → `RESULT: PASS`;
  `report_assets.py --check` → `assets: up to date`.

**Acceptance criteria.**
- [ ] V-D interprets each RQ and lists every applicable limitation with a source.
- [ ] Section VI answers RQ1–RQ3, numbers only via `\bmnum`.
- [ ] Every unmet target is named as unmet.
- [ ] `CLAIMS.md` has no `pending:` row.
- [ ] `RESULT: PASS`.

**Evidence to save.** `course-project/evidence/M5/M5.T5/`: `check_before.txt`, `check_after.txt`, `notes.md`
(pending-claim decisions), `tex.diff`.

**Pitfalls and known gotchas.**
- Do not restate the abstract; the Conclusion answers the questions.
- Do not invent causes for failures; give a cause only if a log or evidence file shows it (R5).
- "Significant" only with a test result (M4.T16 output, computed by the M4.T6 library).

**Stop-and-ask conditions.** The results answer an RQ negatively and the Introduction's contribution list implies
otherwise (Xiaohui decides the framing; the default is to keep the honest negative wording and adjust the
contribution item); a pending claim concerns a safety test (M3.T7) that was not done but a real-car result exists
(that would contradict safety rule S2; README §7).

**Estimated effort.** S.

**AI-disclosure note.** `% AI-assisted (<model>, <date>): drafted the Discussion and Limitations subsection and
Section VI.`

---

### M5.T6 — Trim Related Works to fit; references check

**Why.** Section II was written as a stand-alone graded milestone and is about 2.2 of 4 pages; `CONTEXT.md` ("2026-10-01
class project report") says it can be cut when other sections need the space. This task brings the paper inside
`report/budget.json` and checks every reference added since the graded draft, re-trying the two open
literature items in `report/REVIEW.md` ("Open issues" items 2 and 3).

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M5.T5 done | task | `python3 …/tools/task_status.py M5.T5` (Mac) | `done` |
| Budget set | file | `python3 -c "import json;print(json.load(open('/Users/xiaohuichen/Projects/EN.665.715/course-project/report/budget.json'))['max_pages'])"` (Mac) | an integer, not `None` |
| Network (for records) | service | `curl -sf "https://export.arxiv.org/api/query?id_list=2609.27340" | head -c 200` (Mac) | XML text |

**Inputs.** Section II of the `.tex`; `report/REVIEW.md` (all, especially "Open issues"); `mybibfile.bib`;
`git diff 37454f3 -- course-project/report/mybibfile.bib` (entries added after the graded draft);
`report/sources/*.txt`; the M5.T8 section targets.

**Steps.**
1. *Mac.* Run the check; save `check_before.txt`. Note `pages:` and where each section starts (render pages at
   `-r 50` and note the section starts in `notes.md`).
2. *Mac.* **Decide the cut.** Over budget by `d` pages → Section II must lose about `d` pages (more if other
   sections are also over target; never cut Sections III–V to save Section II). Within budget and Section II at
   or below its target → no trimming; go to step 5.
3. *Mac.* **Cut in this order**, rebuilding after each round, and log each removed sentence with its reason in
   `evidence/M5/M5.T6/cuts.md`:
   1. sentences in the three subsection-closing paragraphs that begin "BeaconMind adopts these lessons",
      "BeaconMind is designed around these findings" and "BeaconMind uses this body of work" (`.tex` lines 127,
      226 and 263 as of 2026-10-06; find them with `grep -n "BeaconMind adopts\|BeaconMind is designed around\|BeaconMind uses this body" Chen-Project-Report.tex`)
      that restate design now in Section III — replace those sentences with one sentence and
      `Section~\ref{sec:overview}`;
   2. secondary numbers of prior work that no later section uses (keep the numbers Table I or the gap argument
      relies on);
   3. if still over budget after 1 and 2: stop and ask Xiaohui (Section II was graded), proposing the default
      "merge II-A and II-B under one heading and drop their restated BeaconMind sentences", with the number of
      lines still to cut (`check_report.py` `pages:` line before and after rounds 1–2).
   **Never:** delete Table I; change a sourced fact other than by shortening; drop the gap paragraph ("In none
   of the language-model systems above…") or its hedge; change a "proposed"/settled word against `CLAIMS.md`.
4. *Mac.* After the cuts, `check_report.py` lists any "entry never cited". Remove those entries from
   `mybibfile.bib` (keep the PDFs in `sources/`), and log them in `cuts.md`.
5. *Mac.* **References check.** For every entry added since `37454f3`, apply R7: record per entry in
   `evidence/M5/M5.T6/refcheck.md` the source file in `sources/`, the page-1 title check output, the primary record
   URL and the date. For the whole file: no duplicate keys or titles
   (`grep -o "^@[a-zA-Z]*{[^,]*" mybibfile.bib | sort | uniq -d` prints nothing); arXiv entries carry the
   version read where numbers are quoted; system names protected with braces (`{GTSAM}`); `bibtex` warnings 0
   (`check_report.py` reports it).
6. *Mac.* **Retry the open items.** (a) Lee et al. arXiv:2609.27340: fetch the arXiv record; if a newer version
   or a published venue exists, re-check the quoted numbers (97.8 %, 99.8 %, 26 and 28 of 30) against it and update
   the entry. (b) The LLM-guided pedestrian dead-reckoning paper (Sensors 2026; `report/REVIEW.md` open issue 2):
   search for it (MDPI Sensors site search or Crossref query
   `https://api.crossref.org/works?query.bibliographic=LLM+pedestrian+dead+reckoning&filter=from-pub-date:2026-01-01&rows=5`).
   Branch: not found or not about an LLM maintaining a pose estimate → log it and keep the novelty sentence;
   it **does** report a trajectory error for an LLM-maintained estimate → stop and ask (the novelty claim in
   Sections I and II must change).
7. *Mac.* Run the check; confirm `pages` ≤ budget (`RESULT: PASS` in draft mode and no `WARN: over budget`);
   render all pages; save diff.

**Deliverables.** `course-project/report/Chen-Project-Report.tex` (Section II trimmed);
`course-project/report/mybibfile.bib`; `evidence/M5/M5.T6/cuts.md`, `refcheck.md`.

**Tests.**
- Unit tests: none.
- Smoke tests (Mac): `check_report.py` → `RESULT: PASS`, no `WARN: over budget`, `bibtex warnings 0`,
  `cited without entry: []; entry never cited: []`; the duplicate-key command prints nothing.

**Acceptance criteria.**
- [ ] Page count within `budget.json` in draft mode.
- [ ] Every cut logged with a reason; Table I and the gap paragraph intact.
- [ ] Every new bib entry has a `refcheck.md` row with a primary record.
- [ ] Open issues 2 and 3 of `report/REVIEW.md` retried and the outcome written there.

**Evidence to save.** `course-project/evidence/M5/M5.T6/`: `check_before.txt`, `check_after.txt`, `cuts.md`,
`refcheck.md`, `tex.diff`, `bib.diff`, `notes.md`.

**Pitfalls and known gotchas.**
- Li et al. is an ICLR 2026 **workshop** paper; keep it as an arXiv preprint (`report/REVIEW.md` rounds 1–2).
- Deng et al. numbers are from arXiv v2 (`report/REVIEW.md` round 3); do not "update" them to v1.
- Removing a sentence can orphan a citation silently (bibtex simply omits it); the checker's "entry never cited"
  catches it.
- Do not paraphrase a quoted phrase ("This is not SLAM: …") — quotes stay verbatim or go.

**Stop-and-ask conditions.** The budget cannot be met without cutting Table I or the gap paragraph; a new paper
undermines the novelty claim; a cited number no longer matches the current version of its source.

**Estimated effort.** S.

**AI-disclosure note.** `% AI-assisted (<model>, <date>): trimmed Section II and checked the references.` Ledger row.

---

### M5.T7 — Generative-AI disclosure, final build, adversarial review

**Why.** The final gate. The syllabus treats undisclosed AI use as misconduct (AGENTS.md §5 "Generative-AI
disclosure"), so the disclosure must name every model that assisted and what it did, and must be true on the day
of submission. The final adversarial review loops until a clean round (AGENTS.md §6.3). The build must be clean.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| All other M5 tasks finished | task | `for i in 1 2 3 4 5 6 8 9 10 11 12 13 14 15; do printf "M5.T$i "; python3 …/tools/task_status.py M5.T$i; done` (Mac) | every line `done`, or `dropped (cut line)` for T13/T14 only |
| Ledger confirmed | file | the ledger check below the table (Mac) | first two numbers equal (every row confirmed or corrected with a date), third `0` |
| No pending claims | file | `grep -c "pending:" …/report/CLAIMS.md` (Mac) | `0` |

Ledger check (Mac; the pipes are outside a table here, so copy them as written):
```bash
L=/Users/xiaohuichen/Projects/EN.665.715/course-project/report/DISCLOSURE-LEDGER.md
grep -cE '^[|] [0-9]+ [|]' "$L"                                              # number of ledger rows
grep -cE '[|] (yes|corrected) [0-9]{4}-[0-9]{2}-[0-9]{2} [|] *$' "$L"         # rows confirmed with a date
grep -c '| pending |' "$L"                                                    # must print 0
```

**Inputs.** The whole `.tex` and PDF; `report/DISCLOSURE-LEDGER.md`; `report/REVIEW.md`; `CLAIMS.md`;
`budget.json`; AGENTS.md §5 "Generative-AI disclosure" and §6; README L11, §10.

**Steps.**
1. *Mac.* Run `check_report.py` (draft mode); save `check_before.txt`.
2. *Mac.* **Ledger delta.** Add rows for any AI-assisted work since M5.T11 (every M5 task's ledger row; every
   task in M1–M4 whose deliverables the report relies on — read their AI-disclosure notes and the
   `Co-Authored-By` trailers: `git log --since=2026-10-05 --format='%h|%ad|%(trailers:key=Co-Authored-By,valueonly,separator=%x3B)|%s' --date=short -- course-project`).
   Ask Xiaohui to confirm the new rows (stop-and-ask; they answer "yes" per row or correct it).
3. *Mac.* **Write the disclosure** (`\section*{Generative AI Disclosure}`, before the bibliography), from the
   ledger only. Structure (one paragraph, or two if long):
   - per model, grouped: "<Model> (<vendor>), used through <tool>, <what it did> (<which sections or artifacts>)";
     the ledger today implies at least Claude Fable 5.1 via Claude Code (Section II, Table I, bibliography, review
     rounds 1–3), Claude Opus 5.5 via Claude Code (feasibility research, design documents and D1–D10 decisions
     under delegation, prompt v3.3, tools and harness of Module 4, this plan), Claude Opus 5.5 in Cursor and Cursor
     Grok 4.6 (proposal revision and its citation check, only if the report draws on them) and the executor
     models of M1–M5 as recorded;
   - one sentence that the language models **evaluated** in Section V are experimental subjects, not writing
     assistance;
   - the responsibility sentence, which must be true when the PDF is uploaded: "The author chose the project
     direction, built and wired the car, reviewed all AI-assisted content against the sources and the evidence
     before submission, and is responsible for its accuracy and originality." Remove "the author's review of some
     of those choices is still in progress" only if Xiaohui confirms they have finished that review (stop-and-ask);
     otherwise keep a true version of it.
4. *Mac.* **Remove draft scaffolding:** delete the line `\newcommand{\laterdraft}{\textit{Reserved for a later draft.}}`
   and the comment line above it (`% Marker for the sections that this draft does not cover.`); replace the three
   header comment lines that start `% DRAFT STATUS:`, `% AI assistance: Claude Fable 5.1` and
   `% section before the references.` with
   `% Final version, <YYYY-MM-DD>. AI assistance: see the Generative AI Disclosure section and report/DISCLOSURE-LEDGER.md.`
   Keep the per-section `% AI-assisted` comments.
5. *Mac.* `python3 course-project/tools/check_report.py --final` → must print `RESULT: PASS`. Fix and repeat.
6. *Mac (fresh sessions).* **Final adversarial review**, protocol above, all six lenses (RL1–RL6), all sections,
   rounds until one full round has zero confirmed findings. Evidence per round in `evidence/M5/M5.T7/`.
7. *Mac.* After the last round: `--final` check again; `pdffonts Chen-Project-Report.pdf | tail -n +3 | awk '{print $(NF-4)}' | sort | uniq -c`
   prints only `yes` (all fonts embedded; 6 `yes` on 2026-10-05); `pdffonts … | grep -c "Type 3"` → `0`;
   `pdfinfo Chen-Project-Report.pdf | grep -E "Title|Author|Pages|Page size"` shows the title, `Xiaohui Chen`,
   the page count and `612 x 792` (US letter, the IEEEtran default here). Render every page at `-r 70` and look at
   each one (margins, float placement, balanced last page, no text outside the columns).
8. **Xiaohui (stop-and-ask).** Ask them to read the whole PDF and confirm (a) they have read it, (b) the disclosure is
   true, (c) they are ready to submit. Record their answer and the date in `CONTEXT.md`. Do not mark M5.T7 `done`
   before they answer.
9. *Mac.* Save final evidence; update `CONTEXT.md` (milestone completion text below). Do not commit unless asked.

**Deliverables.** `course-project/report/Chen-Project-Report.tex` and `.pdf` (final); `report/REVIEW.md` (final
rounds); `report/DISCLOSURE-LEDGER.md` (complete); `course-project/evidence/M5/M5.T7/*`.

**Tests.**
- Unit tests: `cd /Users/xiaohuichen/Projects/EN.665.715/course-project/beaconmind && ../.venv/bin/python -m pytest -q
  tests/test_check_report.py tests/test_report_assets.py` → `… passed`, 0 failed.
- Smoke tests (Mac): `check_report.py --final` → `RESULT: PASS`; `report_assets.py --check` → `assets: up to date`;
  the `pdffonts` and `pdfinfo` checks of step 7.
- Review test: the last `REVIEW.md` round shows 0 confirmed findings across RL1–RL6.

**Acceptance criteria.**
- [ ] `--final` PASS (0 placeholders, within budget, clean log, all refs resolved, every bib entry cited).
- [ ] Disclosure matches the ledger row for row; every ledger row confirmed by Xiaohui.
- [ ] A clean final review round is logged.
- [ ] All fonts embedded, no Type 3, US letter.
- [ ] Xiaohui's read-through and readiness recorded in `CONTEXT.md`.

**Evidence to save.** `course-project/evidence/M5/M5.T7/`: `check_final.txt`, `assets_check.txt`, `pytest.txt`,
`pdffonts.txt`, `pdfinfo.txt`, `round-<n>-RL<k>.md` per lens and round, `ledger-delta.md`, `notes.md` (pages
looked at, Xiaohui's confirmation and date).

**Pitfalls and known gotchas.**
- Name the model you are actually running as (L11; AGENTS.md §5). Do not copy another session's model name.
- The talk track (and `build_proposal.py`'s header comment) name "Claude Opus 5.5 in Cursor" for the proposal
  revision, the deck's slide text says only "Claude Opus 5.5", while the report's draft
  disclosure names "Claude Fable 5.1 via Claude Code" for the report: both can be true (different artifacts and
  sessions); M5.T11 reconciles them. Do not merge them into one model.
- `flushend` and a `figure*` near the end can break the last-page balance (see M5.T4 pitfall).
- A stale `.aux` can hide an undefined reference; `latexmk` reruns as needed, and the checker reads the final log.

**Stop-and-ask conditions.** Any confirmed critical finding in a round after round 3; the disclosure's
responsibility sentence is not yet true; ≤ 7 days left and the review is not converging (default: submit after the
current round's fixes and list the unresolved findings as open issues in `REVIEW.md`, with Xiaohui's approval).

**Estimated effort.** M.

**AI-disclosure note.** `% AI-assisted (<model>, <date>): wrote the disclosure section from the ledger and ran the
final build and review.` Ledger row.

---

### M5.T8 — Report requirements, page budget, preamble and build checker

**Why.** Every other M5 task needs three things this task provides: the page budget (unknown today — no limit is
stated in the instructor's template or anywhere in the repository), a preamble that supports generated numbers,
tables and figures, and a repeatable build checker that reproduces the validation evidence of `report/REVIEW.md`
("Validation evidence") with one command.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| LaTeX toolchain | software | `latexmk -v \| grep Version; pdftotext -v 2>&1 \| head -1` (Mac) | `… Version 4.87`; `pdftotext version 26.04.0` (verified 2026-10-06) |
| System pytest | software | `python3 -m pytest --version` (Mac) | `pytest 9.1.1` (verified 2026-10-06). `No module named pytest` → stop and ask |
| Report builds today | build | the build command (Mac) | `latexmk exit 0` |
| M6.T1 status (soft) | task | read the `M6.T1` row of the `## Status table` in `…/plan/M6-demo-presentation.md` by eye (the status helper is created in this task), and `ls …/presentation/DELIVERABLES.md` (Mac) | `done` and the file exists → read its answer to question 5 (report page limit) before step 3 |

**Inputs.** `course-project/report/Chen-Project-Report.tex` (whole); `report/REVIEW.md` ("Validation evidence",
"Open issues"); `report/sources/template-conference_101719.tex`; the template zip
(`unzip -l "$HOME/Downloads/Class Project Template.zip"` lists 7 files and **no README**; if the zip is gone,
use the copy in `report/sources/`); AGENTS.md §5 "The course project"; `CONTEXT.md` "2026-10-01 class project
report"; `presentation/DELIVERABLES.md` (only if M6.T1 is `done`).

**Steps.**
1. *Mac.* Build and save the baseline:
   `mkdir -p /Users/xiaohuichen/Projects/EN.665.715/course-project/evidence/M5/M5.T8`, run the build command, then
   `cp /Users/xiaohuichen/Projects/EN.665.715/course-project/report/build.out /Users/xiaohuichen/Projects/EN.665.715/course-project/evidence/M5/M5.T8/build_baseline.txt`.
   Expected: `latexmk exit 0`. Also snapshot the source: `cp …/report/Chen-Project-Report.tex …/evidence/M5/M5.T8/before.tex`.
2. *Mac.* **Verify that no page limit is recorded.**
   `grep -rniE "page limit|pages? max|maximum of [0-9]+ pages|[0-9]+[- ]page" /Users/xiaohuichen/Projects/EN.665.715/AGENTS.md /Users/xiaohuichen/Projects/EN.665.715/course-project/*.md /Users/xiaohuichen/Projects/EN.665.715/course-project/presentation/*.md 2>/dev/null`
   and `unzip -p "$HOME/Downloads/Class Project Template.zip" conference_101719.tex | grep -niE "page|limit"`.
   Branch: M6.T1 is `done` and `DELIVERABLES.md` answers question 5 with a limit → use it, record that file as the
   source in `budget.json`, and skip question 1 in step 3. A limit is found anywhere else → write the hit into
   `answers.md` and still ask Xiaohui to confirm it (step 3, question 1). Nothing found (the state on
   2026-10-06; the grep may print hits about slide decks or other assignments — read each and ignore those that
   are not about this report) → step 3.
3. **Xiaohui (stop-and-ask).** Send them these questions, each with the recommended default:
   1. Page limit for the final report? *Default: none is stated; target **8 pages including references**
      (the usual IEEE conference length).* Alternatives: 6 pages if the instructor wants short papers; 10 if
      there is no limit and the results need it. Offer this message for them to send if they want to ask the
      instructor: "Is there a page limit for the final Class Project Report in the IEEE template, and do the
      references count toward it?"
   2. Do references count toward the limit? *Default: yes.*
   3. May Section II (already graded) be shortened to fit? *Default: yes, to about 1.4 pages, keeping Table I.*
   4. Author block: add an e-mail address? *Default: no* (none is recorded; `report/REVIEW.md` round 2).
   5. Appendix allowed (for example a prompt excerpt)? *Default: no appendix.*
   Record their answers verbatim, with the date, in `evidence/M5/M5.T8/answers.md`, and tell them that this also
   answers M6.T1 question 5 (so M6.T1 can copy it into `presentation/DELIVERABLES.md` instead of asking again).
   Wait for the answers. Meanwhile do steps 5–11 (they do not depend on them) and write `budget.json` with
   `"max_pages": null` until they answer. If the session must end before they answer, set M5.T8 to `blocked`
   with the reason "waiting for the page budget"; M5.T1, T2 and T11 may still start (they need only the checker
   and the preamble), but M5.T6 and M5.T7 may not.
4. *Mac.* Write `course-project/report/budget.json`:
   ```json
   {"schema": "bm.report_budget/1", "max_pages": 8, "references_count": true,
    "appendix_allowed": false, "author_email": null,
    "decided_by": "Xiaohui", "date": "YYYY-MM-DD", "source": "Xiaohui's answer in session of YYYY-MM-DD"}
   ```
   (values from their answers; `max_pages: null` and `decided_by: null` while unanswered).
5. *Mac.* **Preamble.** In `Chen-Project-Report.tex`, directly after `\usepackage{flushend}` and its comment,
   insert (this exact block was compiled on a copy of the report on 2026-10-06 by the plan reviewer: still 4
   pages, 0 overfull boxes, PDF Title/Author set, an unknown key printed `??test.key` with one
   `Package bmnum Warning`, a defined key printed its value):
   ```latex
   % AI-assisted (<model>, <date>): added booktabs, \bmnum and \pdfinfo.
   % Generated results tables use booktabs rules (tools/report_assets.py).
   \usepackage{booktabs}
   \graphicspath{{figures/}{figures/generated/}}
   % Result numbers: \bmnum{<key>} prints a value from generated/numbers.tex, written by
   % tools/report_assets.py. Never type a result by hand (plan/M5-report.md rule R3).
   % An unknown key prints ??<key> and a "Package bmnum Warning" that check_report.py counts.
   \makeatletter
   \newcommand{\bmnum}[1]{\@ifundefined{bmn@#1}{\textbf{??#1}\PackageWarning{bmnum}{Undefined number #1}}{\@nameuse{bmn@#1}}}
   \makeatother
   \IfFileExists{generated/numbers.tex}{\input{generated/numbers.tex}}{}
   \pdfinfo{/Title (BeaconMind: Can a Large Language Model Own Landmark SLAM?) /Author (Xiaohui Chen)}
   ```
   Replace the header comment line `% DRAFT STATUS: only Section II (Related Works) and the References are written.`
   with `% DRAFT STATUS: see course-project/plan/M5-report.md (status table).`
6. *Mac.* **Labels (R10).** First check nothing references the old labels:
   `grep -nE "ref\{(sytem_overview|experiments|results)\}" course-project/report/Chen-Project-Report.tex` → no output.
   Then: `\section{Introduction}` → `\section{Introduction}\label{sec:intro}`; `\label{sytem_overview}` →
   `\label{sec:overview}`; `\label{experiments}` → `\label{sec:experiments}`; `\label{results}` →
   `\label{sec:results}`; `\section{Conclusion}` → `\section{Conclusion}\label{sec:conclusion}`.
   **Section targets** — write this table into `evidence/M5/M5.T8/targets.md`, scaled for the decided budget.
   Let `B` = `max_pages` if `references_count` is true, else `max_pages + 1.2`. Keep the title block (0.3) and the
   references (1.2) fixed and multiply **every other row** (I–VI and the disclosure, which sum to 6.45 pages at
   B = 8) by `(B − 1.5) / 6.45`, rounding to 0.05 page. Word targets scale the same way.

   | Part | Target at 8 pages incl. references |
   | --- | --- |
   | Title, abstract, index terms | 0.3 page (abstract 150–220 words) |
   | I Introduction | 0.6 page (500–600 words) |
   | II Related Works | 1.4 pages incl. Table I (≈ 2.2 today) |
   | III System Overview | 1.4 pages incl. Fig. 1 (`figure*`) and the tools table |
   | IV Experiments | 1.1 pages incl. the arena figure |
   | V Results and Evaluation (incl. V-D) | 1.6 pages incl. 2 tables and 2 figures |
   | VI Conclusion | 0.2 page |
   | Disclosure | 0.15 page |
   | References | ≈ 1.2 pages (≈ 35 entries) |
7. *Mac.* **Folders:** `mkdir -p course-project/report/figures/src course-project/report/figures/generated
   course-project/report/generated` and `touch` a `.gitkeep` in the last two.
8. *Mac.* **Write `course-project/tools/check_report.py`** (Python ≥ 3.10, standard library only; runs with the Mac's
   system `python3`). Module docstring ends with the L11 line. Required functions (step 10 unit-tests them):
   ```python
   REPORT_DIR = Path(__file__).resolve().parents[1] / "report"
   TEX_NAME = "Chen-Project-Report.tex"
   BIB_NAME = "mybibfile.bib"                   # IEEEabrv.bib holds only @string abbreviations; never counted

   def strip_comments(tex: str) -> str          # per line, drop from an unescaped % to the end: re.sub(r"(?<!\\)%.*", "", line)
   def cite_keys(tex: str) -> set[str]          # after strip_comments: every key in r"\\cite\*?\{([^}]*)\}", split on ",", stripped;
                                                #   \bstctlcite never matches (the regex needs "\" directly before "cite")
   def bib_keys(bib: str) -> set[str]           # r"^\s*@(\w+)\s*\{\s*([^,\s]+)\s*," with re.M; skip entry types whose
                                                #   .lower() is ieeetranbstctl, comment, string or preamble
   def count_placeholders(tex: str) -> int      # after strip_comments and dropping the line containing "\newcommand{\laterdraft}":
                                                #   uses of "\laterdraft" + occurrences of "Reserved for a later draft"
   def log_problems(log: str) -> dict[str, int] # match the START of each message only (logs wrap at 79 characters):
                                                #   overfull = lines starting "Overfull \hbox" or "Overfull \vbox";
                                                #   undefined_refs = lines starting "LaTeX Warning: Reference `";
                                                #   undefined_cites = lines starting "LaTeX Warning: Citation `";
                                                #   missing_numbers = lines starting "Package bmnum Warning";
                                                #   errors = lines starting "! "
   def blg_warnings(blg: str) -> int            # N from "(There were N warnings)" or 1 from "(There was 1 warning)";
                                                #   else the N in "warning$ -- N" (bst warning$ call count); else 0.
                                                #   Return the larger of the two when both appear.
   def split_pages(pdf_text: str) -> list[str]  # split on "\f"; drop a trailing empty element
   def references_start_page(pages: list[str]) -> int | None   # first page matching r"R\s?EFERENCES" (1-based)
   def unresolved_marks(pdf_text: str) -> int   # count of "[?]" + count of r"\?\?(?![a-z0-9.\-])"
   def missing_numbers(pdf_text: str) -> list[str]  # sorted unique keys in r"\?\?([a-z0-9.\-]+)"
   def secrets_hits(text: str) -> int           # count of re.I matches of
                                                #   r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}|api[_-]key\s*[:=]|password\s*[:=]|\bssid\s*[:=]"
                                                #   (prose such as "API keys are stored on the Spark" or "task-specific" must not hit)
   def evaluate(m: dict, budget: dict | None, final: bool) -> tuple[str, list[str]]
       # m keys: latexmk_exit, pages, refs_page, log (dict above), blg, unresolved, missing (list), secrets,
       #   placeholders, cited_without_entry (list), entry_never_cited (list).
       # FAIL if: latexmk_exit != 0, any log value > 0, blg > 0, unresolved > 0, missing non-empty,
       #   cited_without_entry or entry_never_cited non-empty, secrets > 0;
       # final also FAILs if placeholders > 0 ("FAIL: placeholders"), budget is None or max_pages is None
       #   ("FAIL: budget not set"), or over budget ("FAIL: over budget");
       # draft adds the reason "WARN: over budget" but stays PASS.
       # over budget: pages > max_pages when references_count, else refs_page > max_pages.
   def main(argv: list[str] | None = None) -> int
       # flags --final, --no-build, --report-dir <dir> (default REPORT_DIR); returns 0 on PASS, 1 on FAIL
   ```
   `main` runs `latexmk -pdf -interaction=nonstopmode -halt-on-error Chen-Project-Report.tex` in the report
   directory (stdout and stderr into `build.out`) unless `--no-build`, reads `Chen-Project-Report.log`, `.blg`, the PDF
   text (`pdftotext <pdf> -`), the page count (`pdfinfo`, line `Pages:`), `mybibfile.bib` and `budget.json` if
   present, and prints exactly these lines:
   ```
   latexmk exit: <n>
   pages: <n> (references start on page <r>; budget: <not set | max N, references counted | max N, body only>)
   cite keys in .tex: <a>; entries in .bib: <b>; cited without entry: [<keys>]; entry never cited: [<keys>]
   log: overfull <n>, undefined references <n>, undefined citations <n>, missing numbers <n>, errors <n>; bibtex warnings <n>
   pdf: unresolved marks <n>, missing numbers <n>, secrets <n>
   placeholders: <n>
   <each reason on its own line, e.g. "FAIL: overfull boxes" or "WARN: over budget">
   RESULT: PASS|FAIL
   ```
   Key lists print as Python lists of sorted strings (`['a', 'b']`; `[]` when empty).
   **8b.** *Mac.* **Make sure the plan-wide status helper exists** (README convention L12; every later
   prerequisite uses it): `test -f course-project/tools/task_status.py && echo present`. If it is missing (M1.T1
   not done yet), create `course-project/tools/task_status.py` with **exactly** the source in README L12 (do not
   write a second helper; an earlier draft of this plan wrote `task_status.sh`, which the cross-plan consistency
   review of 2026-10-06 replaced with the single L12 helper). Then check it:
   `python3 course-project/tools/task_status.py M5.T8 M5.T99; echo "exit $?"` → `M5.T8 todo` (or its current
   status), `M5.T99 NOT-FOUND`, `exit 2`.
   **8c.** *Mac.* **Write the unit tests `course-project/beaconmind/tests/test_check_report.py`** (the 13 tests listed
   under Tests). Load the script by path, because tools are scripts, not package modules:
   ```python
   import importlib.util, pathlib
   TOOLS = pathlib.Path(__file__).resolve().parents[2] / "tools"
   def _load(name):
       spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
       mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
   ```
   If `course-project/beaconmind/` does not exist yet (M1.T1 not done), create only `beaconmind/tests/` and this
   one file; M1.T1's prerequisite check sees the folder and "continues only with the missing pieces" (M1.T1
   prerequisites table), so tell Xiaohui in the session summary that M1.T1 will find this file. Do **not**
   create `pyproject.toml` or `conftest.py`; they belong to M1.T1.
9. *Mac.* **Create `course-project/report/CLAIMS.md`** with the format above and seed rows for the existing
   Section II: the four proposed items (refusal suite `proposed:OD1`, coded baseline `proposed:OD2`, oracle
   association `proposed:OD3`, stretch conditions `proposed:OD4`, all with source
   `proposal-talk-track.md "New in this revision"`), and the novelty sentence (source
   `research/2026-09-27-llm-slam-feasibility/topic1-llm-as-slam-literature.md`; `report/REVIEW.md` open issue 2).
   The file holds a one-line header ("Claims register for the report; status values and rules:
   `course-project/plan/M5-report.md`") and the table only — no legend that contains the strings `pending:` or
   `proposed:`, because later checks count those strings with `grep -c`.
10. *Mac.* Run the unit tests. Before M1.T1 is `done` (no venv, no `conftest.py` yet), use the system Python:
    `cd /Users/xiaohuichen/Projects/EN.665.715/course-project/beaconmind && python3 -m pytest -q -p no:cacheprovider tests/test_check_report.py`
    (`python3 -m pytest --version` printed `pytest 9.1.1` on 2026-10-06; if it prints `No module named pytest`,
    stop and ask — do not `pip install` into the system Python). After M1.T1 is `done`, use
    `../.venv/bin/python -m pytest -q tests/test_check_report.py` instead (M1.T1's `conftest.py` imports
    `beaconmind`, which the system Python does not have). Expected final line: `13 passed`.
11. *Mac.* Run `python3 course-project/tools/check_report.py`; save output as `evidence/M5/M5.T8/check_after.txt`.
    Then run the status helper: `python3 course-project/tools/task_status.py M5.T8 M5.T99; echo "exit $?"`
    → `in-progress` (or `todo` if you have not updated the status table yet), then `no-row` and `exit 3`.
    Save as `evidence/M5/M5.T8/task_status.txt`.

**Deliverables.** `course-project/report/budget.json`; `course-project/report/CLAIMS.md`;
`course-project/tools/check_report.py`; `course-project/tools/task_status.py` (README L12);
`course-project/beaconmind/tests/test_check_report.py`; `course-project/report/Chen-Project-Report.tex` (preamble,
labels, header line); `course-project/report/figures/{src,generated}/`, `course-project/report/generated/.gitkeep`.

**Tests.**
- Unit tests, `course-project/beaconmind/tests/test_check_report.py` (13; command in step 10 → `13 passed`):
  - `test_strip_comments_keeps_escaped_percent` — `50\% done % note` → `50\% done `.
  - `test_cite_keys_multi_and_bstctl` — `\cite{a, b}\cite{c}\bstctlcite{X}` → `{"a", "b", "c"}`.
  - `test_cite_keys_ignores_commented` — `% \cite{x}` → empty set.
  - `test_bib_keys_excludes_control` — two `@article` entries plus `@IEEEtranBSTCTL{IEEEexample:BSTcontrol,` → the two
    article keys only.
  - `test_count_placeholders` — the `\newcommand{\laterdraft}{\textit{Reserved for a later draft.}}` line + two
    `\laterdraft` uses + one literal "Reserved for a later draft" → 3.
  - `test_log_problems_counts` — a synthetic log with one line each starting `Overfull \hbox`,
    ``LaTeX Warning: Reference `x' on page 1``, ``LaTeX Warning: Citation `y' on page 1``, `Package bmnum Warning`,
    `! Undefined control sequence` → each count 1; a wrapped line whose "undefined" is on the next line still counts.
  - `test_blg_warnings` — `(There were 2 warnings)` → 2; `(There was 1 warning)` → 1; `warning$ -- 0` alone → 0;
    no such lines → 0.
  - `test_references_start_page` — `["intro", "x R EFERENCES y"]` → 2; no match → `None`.
  - `test_unresolved_and_missing_numbers` — `see [?] and ?? and ??ate.x` → unresolved 2, missing `["ate.x"]`.
  - `test_secrets_hits` — `sk-abcdefghijklmnopqrstuv` → 1; `api_key = abc` → 1; `classid`, `task-specific-thing`,
    `API keys are stored on the Spark` → 0 each.
  - `test_evaluate_final_fails_on_placeholders` — placeholders 1, budget max 8, final → `FAIL` with
    `FAIL: placeholders` in the reasons; same metrics in draft mode → `PASS`.
  - `test_evaluate_draft_warns_over_budget` — pages 9, budget 8 counted → draft `PASS` with `WARN: over budget`;
    final → `FAIL` with `FAIL: over budget`; final with budget `None` → `FAIL: budget not set`.
  - `test_end_to_end_on_report_copy` — copies `course-project/report` (without `sources/`) to `tmp_path`, runs
    `main(["--report-dir", str(tmp_path)])` → 0; skipped unless `shutil.which` finds all of `latexmk`, `pdftotext`
    and `pdfinfo`.
- Smoke test (Mac): `python3 course-project/tools/check_report.py` on the current report. Expected, with the
  numbers measured on 2026-10-05 (the preamble edit must not change them):
  ```
  latexmk exit: 0
  pages: 4 (references start on page 4; budget: not set)
  cite keys in .tex: 27; entries in .bib: 27; cited without entry: []; entry never cited: []
  log: overfull 0, undefined references 0, undefined citations 0, missing numbers 0, errors 0; bibtex warnings 0
  pdf: unresolved marks 0, missing numbers 0, secrets 0
  placeholders: 7
  RESULT: PASS
  ```
  (With the budget set, the `pages:` line names it.) Then `python3 course-project/tools/check_report.py --final
  --no-build` → `FAIL: placeholders` (and `FAIL: budget not set` while `max_pages` is null) and `RESULT: FAIL`
  (proves the final mode bites). Save as `check_final_expected_fail.txt`.
- Macro smoke test (Mac): temporarily add `\bmnum{test.key}` to the abstract, run the checker → `missing numbers 1`
  in both the log and pdf lines and `RESULT: FAIL`; remove it and re-run → PASS. Save both outputs.
- Status helper smoke test: step 11 output.

**Acceptance criteria.**
- [ ] `budget.json` exists; `max_pages` is Xiaohui's answer (or `null` with the task `blocked` on their answer).
- [ ] Preamble, labels and folders as specified; the report still builds to the same 4 pages.
- [ ] Smoke outputs match the expected lines; the final-mode and macro tests fail as expected.
- [ ] `test_check_report.py`: `13 passed` (pasted in `pytest.txt`).
- [ ] `task_status.py` (README L12) prints `M5.T8 <status>` and `M5.T99 NOT-FOUND` (exit 2).
- [ ] `CLAIMS.md` seeded.

**Evidence to save.** `course-project/evidence/M5/M5.T8/`: `build_baseline.txt`, `before.tex`, `check_after.txt`,
`check_final_expected_fail.txt`, `macro_test_fail.txt`, `macro_test_pass.txt`, `pytest.txt`, `task_status.txt`,
`targets.md`, `answers.md` (Xiaohui's answers with the date), `tex.diff`.

**Pitfalls and known gotchas.**
- LaTeX logs wrap at 79 characters; a warning split over two lines may escape a regex. Match the start of the
  message only (as above).
- The Mac shell is **zsh**: write `${var}` before a `:` (zsh reads `"$h:c…"` as a modifier) and quote globs.
- `latexmk` exits 0 even when a reference is undefined; that is why the checker reads the log.
- `pdftotext` renders IEEEtran's small-caps heading as `R EFERENCES` (checked 2026-10-05); the regex allows the space.
- `report/build.out`, `Chen-Project-Report.log` and `.out` are git-ignored by explicit lines in the root
  `.gitignore`; `.aux`, `.bbl`, `.blg`, `.fls`, `.fdb_latexmk` by pattern. New `.log` files elsewhere are not.
- The template's own label `sytem_overview` is misspelled; nothing references it (checked 2026-10-05).

**Stop-and-ask conditions.** The page question (step 3) — always; the preamble edit changes the page count or
breaks Table I's placement.

**Estimated effort.** S.

**AI-disclosure note.** `check_report.py` docstring: `AI-assisted: <model> via <tool>, <date>: wrote the report
build checker.` In the `.tex`, a comment above the inserted preamble block:
`% AI-assisted (<model>, <date>): added booktabs, \bmnum and \pdfinfo.`

---
### M5.T9 — Report numbers and tables pipeline (`tools/report_assets.py`)

**Why.** Rule R3: no result is typed by hand. This task writes the tool that turns result CSVs (M2.T10/M2.T12
outputs, and the per-table CSVs of M4.T16's analysis) into `\bmnum` definitions, LaTeX tables, a target-outcome
table and a manifest with the SHA-256 of every source, plus a `--check` mode that detects stale outputs. It only
**selects, counts distinct values and formats**; it never computes a statistic. Standard library only, so it runs
on the Mac (L3 "core modules"). M4.T16 has its own generator for the M4 tables and figures
(`tools/make_report_assets.py`, writing `report/generated/tables/` and `report/generated/figures/`); this tool
never writes into those two subfolders and never reads them.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M1.T1 done (package skeleton, Mac venv, pytest config) | task | `python3 …/tools/task_status.py M1.T1` (Mac) | `done` |
| Mac venv runs pytest | software | `/Users/xiaohuichen/Projects/EN.665.715/course-project/.venv/bin/python -m pytest --version` (Mac) | `pytest <version>` |
| M5.T8 done | task | `python3 …/tools/task_status.py M5.T8` (Mac) | `done` (or `blocked` only on the page-budget answer; the checker and its tests must exist) |

**Inputs.** README L1–L4, L11, C10; `course-project/tools/check_report.py`; `plan/M2-sim-mvp.md` M2.T10 (the
`episodes.csv` columns) — the tool must not assume more than "a CSV with a header row".

**Steps.**
1. *Mac.* Write `course-project/tools/report_assets.py` (Python ≥ 3.10, stdlib only; docstring ends with the L11
   line). Paths in `assets.json` are relative to the **course-project root** (`--root`, default
   `Path(__file__).resolve().parents[1]`); `--assets` defaults to `<root>/report/assets.json`; every output goes to
   `<root>/report/generated/` (top level only). API:
   ```python
   class AssetError(Exception): ...
   KEY_RE = re.compile(r"^[a-z0-9][a-z0-9.\-]*$")
   def check_key(key: str) -> None                       # AssetError if KEY_RE does not match
   def load_csv(path: Path) -> list[dict[str, str]]       # csv.DictReader, encoding utf-8
   def select(rows, where: dict[str, str]) -> list[dict] # exact string equality on every where-column, rows in file order
   def resolve_number(spec: dict, rows: list[dict]) -> tuple[str, int]
       # returns (formatted value, 1-based data-row number; header excluded). spec keys: key, source, where, column,
       # format (optional), agg (optional). Without agg, `where` must select exactly one row, else AssetError whose
       # message contains the key and the match count. With "agg": "count_distinct", the value is the number of
       # distinct non-empty values of `column` among the selected rows (≥ 1 row required), row number 0.
   def format_value(raw: str, fmt: str | None, allow_missing: bool = False) -> str
       # "" → "--" if allow_missing else AssetError; fmt → fmt.format(float(raw)); no fmt → latex_escape(raw)
   def latex_escape(s: str) -> str                       # \ & % $ # _ { } ~ ^ escaped for text mode
   def pivot(rows, index: str, columns: str, values: str | list[str], order: list[str] | None = None) -> list[dict]
       # one output row per index value (in `order` if given, else first appearance), with field `<columns value>`
       # (one value column) or `<columns value>.<value column>` (a list); two input rows for the same
       # (index, columns) cell → AssetError naming both
   def render_cell(row: dict, col: dict) -> str
       # col has "field" (one value) or "fields" + "pattern" (e.g. "{0} [{1}, {2}]"); each value goes through
       # format_value(…, col.get("format"), col.get("allow_missing", False)) before it fills the pattern
   def render_numbers_tex(numbers: dict[str, str]) -> str
   def render_table_tex(spec: dict, rows: list[dict], source_rel: str, source_sha12: str) -> str
   def evaluate_target(value: float, op: str, threshold: float) -> bool   # op in <, <=, >, >=, ==
   def build(assets: dict, root: Path) -> dict[str, str]  # {path relative to root: file content}; deterministic
   def main(argv: list[str] | None = None) -> int         # --assets, --root, --check
   ```
   `assets.json` (`bm.report_assets/1`), stored at `course-project/report/assets.json`:
   ```json
   {"schema": "bm.report_assets/1",
    "sources": {"m2_replay": "evidence/M2/M2.T12/summary_replay.csv"},
    "numbers": [{"key": "ate.replay.dup.l2.qwen35-a3b-think.median", "source": "m2_replay",
                 "where": {"arm": "L2", "model_key": "qwen35-a3b-think", "condition": "duplicated",
                           "metric": "ate_unaligned_m"},
                 "column": "median", "format": "{:.2f}"},
                {"key": "n.models.replay", "source": "m2_replay", "where": {"arm": "L2"},
                 "column": "model_key", "agg": "count_distinct"}],
    "tables": [{"name": "replay", "source": "m2_replay", "where": {"condition": "duplicated"},
                "pivot": {"index": "arm_label", "columns": "metric", "values": ["median", "q1", "q3"],
                          "order": ["B0", "B1", "B2", "L2 Qwen3.5 (thinking)"]},
                "columns": [{"header": "Arm", "field": "arm_label"},
                            {"header": "ATE (m)", "fields": ["ate_unaligned_m.median", "ate_unaligned_m.q1",
                             "ate_unaligned_m.q3"], "pattern": "{0} [{1}, {2}]", "format": "{:.2f}"}],
                "caption": "…", "label": "tab:replay", "placement": "t", "wide": false}],
    "targets": [{"label": "Median final position error \\le 0.25 m",
                 "number": "final.replay.dup.l2.qwen35-a3b-think.median", "op": "<=", "threshold": 0.25}]}
   ```
   (The source path and column names in this example are illustrative; M5.T4 uses the real ones it recorded in
   `evidence/M5/M5.T4/inputs.md`.) `pivot` is optional. A target's `number` must be one of the declared keys.
   Outputs written by `build` (all under `report/generated/`, no timestamps anywhere, so `--check` is exact):
   - `numbers.tex`: first line `% GENERATED by tools/report_assets.py from report/assets.json; do not edit.`,
     then `\makeatletter`, one `\@namedef{bmn@<key>}{<value>}` per number in key order, `\makeatother`;
   - `numbers.json`: `{key: value}` sorted (M6 slides read it);
   - `tab-<name>.tex`: a header comment naming the source and its SHA-12, then `\begin{table}[<placement>]`
     (`table*` when `wide`), `\caption{…}`, `\label{…}`, `\centering`, `\footnotesize`, `tabular` with `l` for
     the first column and `r` for the others (override with `"align"`), `\toprule`, header row, `\midrule`,
     body rows, `\bottomrule`;
   - `tab-targets.tex` (only if `targets` is non-empty): columns Target, Value, Threshold, Outcome (`met` / `not met`);
   - `MANIFEST.txt`: `source <name> <path> sha256 <64 hex>`, `number <key> = <value> <- <source> row <n>` (`<n>` from
     `resolve_number`; `count_distinct` numbers print `rows <count of selected rows>` instead of `row <n>`),
     `table <name> rows <n>`, `target "<label>" <value> <op> <threshold> -> met|not met`.
   CLI output: `assets: wrote <n> numbers, <m> tables, <k> targets` (exit 0); `--check`: `assets: up to date`
   (exit 0) or one `assets: STALE <path>` line per differing or missing file (exit 1); errors: `assets: ERROR
   <message>` (exit 2). With no `assets.json`, print `assets: no assets.json; nothing to do` and exit 0.
2. *Mac.* Create the fixtures `course-project/beaconmind/tests/fixtures/report/summary.csv`:
   ```
   arm,arm_label,model_key,condition,metric,median,q1,q3,n_seeds
   B0,B0,,duplicated,ate_unaligned_m,0.412,0.300,0.520,30
   B1,B1,,duplicated,ate_unaligned_m,0.081,0.060,0.100,30
   B2,B2,rules_v1,duplicated,ate_unaligned_m,0.300,0.250,0.350,30
   L2,L2 Qwen,qwen35-a3b-think,duplicated,ate_unaligned_m,0.214,0.150,0.290,30
   L2,L2 Qwen,qwen35-a3b-think,duplicated,assoc_precision,0.93,0.90,0.96,30
   L2,L2 Qwen,qwen35-a3b-think,unique,ate_unaligned_m,,,,0
   ```
   (made-up fixture values; they appear only in tests) and `assets_fixture.json` whose single source is
   `"fix": "data/summary.csv"` (the CLI tests copy the CSV to `<tmp_path>/data/summary.csv` and use `tmp_path` as
   `--root`), with two numbers (`ate.replay.dup.b0.median`, `ate.replay.dup.l2.qwen35-a3b-think.median`), one `count_distinct` number (`n.arms`, column
   `arm`, `where` `{"condition": "duplicated"}` → `4`), one pivoted table (`where` condition `duplicated`, values
   `["median", "q1", "q3"]`, the IQR column above) and two targets (`ate.replay.dup.l2.qwen35-a3b-think.median` `<=` 0.25 → met; `ate.replay.dup.b0.median` `<=` 0.25 → not met).
3. *Mac.* Write `course-project/beaconmind/tests/test_report_assets.py`, loading the script with the `_load`
   helper of M5.T8 step 8c.
4. *Mac.* Run the tests (command below) until they pass; then run the tool against the real `report/` (no
   `assets.json` yet → `nothing to do`).

**Deliverables.** `course-project/tools/report_assets.py`; `course-project/beaconmind/tests/test_report_assets.py`;
`course-project/beaconmind/tests/fixtures/report/summary.csv`, `assets_fixture.json`.

**Tests.**
- Unit tests, `test_report_assets.py` (19):
  - `test_check_key_accepts_valid` — `ate.replay.dup.l2.qwen35-a3b-think.median` passes.
  - `test_check_key_rejects_underscore_and_upper` — `a_b` and `ATE` raise `AssetError`.
  - `test_select_single_row` — `{"arm": "B1", "metric": "ate_unaligned_m"}` selects one row with median `0.081`.
  - `test_number_zero_rows_raises` — `resolve_number` with a `where` matching nothing raises; message contains the key.
  - `test_number_two_rows_raises` — `{"arm": "L2", "condition": "duplicated"}` (two rows) raises; message contains `2`.
  - `test_number_row_index` — the B1 ATE number returns row number `2`.
  - `test_number_count_distinct` — `count_distinct` of `arm` over condition `duplicated` → `"4"`.
  - `test_format_value_two_decimals` — `("0.214", "{:.2f}")` → `0.21`.
  - `test_format_value_missing` — `("", "{:.2f}")` raises; with `allow_missing=True` → `--`.
  - `test_latex_escape` — `rules_v1 & 5%` → `rules\_v1 \& 5\%`.
  - `test_render_numbers_tex` — starts with `% GENERATED`, contains `\makeatletter`,
    `\@namedef{bmn@ate.x}{0.21}`, `\makeatother`.
  - `test_pivot_long_to_wide` — the duplicated-condition L2 rows become one row with fields
    `ate_unaligned_m.median` (`0.214`) and `assoc_precision.median` (`0.93`).
  - `test_pivot_duplicate_cell_raises` — pivoting all L2 rows on `index="arm"`, `columns="metric"` (the duplicated
    and unique ATE rows collide) raises `AssetError`.
  - `test_column_pattern_iqr` — `render_cell` with the IQR column on the L2 pivot row → `0.21 [0.15, 0.29]`.
  - `test_render_table_order_and_rules` — rows follow `order`; `\caption` precedes `\begin{tabular}`; contains
    `\toprule`, `\midrule`, `\bottomrule`; `rules\_v1` escaped if shown.
  - `test_targets_met_and_not_met` — 0.214 `<=` 0.25 → `met`; 0.412 `<=` 0.25 → `not met`.
  - `test_manifest_sha256` — the manifest's hash equals `hashlib.sha256` of the fixture bytes.
  - `test_build_is_deterministic` — two `build()` calls return equal dicts.
  - `test_cli_writes_then_check_passes_and_detects_stale` — `main(["--assets", f, "--root", tmp])` → 0; `--check`
    → 0 and prints `assets: up to date`; then append a space to `report/generated/numbers.tex` → `--check` returns 1
    and prints `assets: STALE report/generated/numbers.tex`.
- Command (Mac): `cd /Users/xiaohuichen/Projects/EN.665.715/course-project/beaconmind && ../.venv/bin/python -m pytest
  -q tests/test_report_assets.py tests/test_check_report.py` → expected final line `32 passed` (19 + 13).
- Same on the Spark host (Python 3.12) after `tools/sync_to_spark.sh`: `cd ~/Projects/EN.665.715/course-project/beaconmind
  && ~/.venvs/beaconmind/bin/python -m pytest -q tests/test_report_assets.py tests/test_check_report.py` →
  `31 passed, 1 skipped` if `latexmk`, `pdftotext` or `pdfinfo` is missing on the Spark host (not checked), or
  `32 passed` if all three exist; record which.
- Smoke test (Mac): `python3 course-project/tools/report_assets.py` → `assets: no assets.json; nothing to do`.

**Acceptance criteria.**
- [ ] `report_assets.py` is stdlib-only (`grep -E "^import|^from" course-project/tools/report_assets.py` shows only
      standard-library modules).
- [ ] 32 tests pass on the Mac; the Spark host run passes (one skip allowed).
- [ ] Outputs contain no timestamps; `--check` exact.

**Evidence to save.** `course-project/evidence/M5/M5.T9/`: `pytest_mac.txt`, `pytest_spark.txt`, `smoke.txt`.

**Pitfalls and known gotchas.**
- Python 3.10 compatibility (L3): `X | None` in annotations is fine in 3.10; no `tomllib`, no `match` needed.
- `csv` keeps every value as a string; compare `where` values as strings (`"30"`, not `30`).
- A format like `{:.1%}` multiplies by 100: use it only for fractions and say so in the header text.
- `\@namedef` needs `\makeatletter` — the generated file sets it itself, because it is `\input` in the preamble.
- Never let `build` write outside `report/generated/` top level: M4.T16 owns `report/generated/tables/` and
  `figures/`, and `--check` must not report them as stale.

**Stop-and-ask conditions.** none beyond README §1.4.

**Estimated effort.** M.

**AI-disclosure note.** Docstrings: `AI-assisted: <model> via <tool>, <date>: wrote the report assets tool` /
`… wrote the report assets tests.`

---

### M5.T10 — Figure pipeline: arena and trajectory figures (`tools/report_figures.py`)

**Why.** Section IV needs an arena figure (C7 world, tags, duplicated IDs, start pose) and Section V a trajectory
figure (ground truth vs the L2 estimate vs baselines, with the final beacon map) for a representative episode
chosen by a rule, not by hand (R3, R9). The data live on the Spark (`data/`, L8), so the script runs on the Spark
host venv, which has matplotlib through the `metrics` extra (L3).

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M1.T1, M2.T2, M2.T10, M2.T11 done | task | `for i in M1.T1 M2.T2 M2.T10 M2.T11; do python3 …/tools/task_status.py $i; done` (Mac) | four lines `done` |
| matplotlib in the Spark venv | software | `ssh -o ConnectTimeout=15 -o BatchMode=yes xiaohui_chen@spark-2a60 '~/.venvs/beaconmind/bin/python -c "import matplotlib; print(matplotlib.__version__)"'` (Mac) | a version. If `ModuleNotFoundError` → stop and ask (M1.T1 should have installed `[metrics]`; do not install packages outside the plan) |
| Run logs exist | data | `ssh … 'ls ~/Projects/EN.665.715/course-project/data/runs | head'` (Mac) | at least one run directory |

**Inputs.** README C1 (frames; map = start pose), C7 (world JSON), C9.2 (run log: `report_corrected.pose`,
`report_corrected.map`, `gt_pose_map`), L5, L6; `plan/M2-sim-mvp.md` M2.T10 (per-episode metrics CSV and its
columns); R9 (figure style).

**Steps.**
1. *Mac.* Write `course-project/tools/report_figures.py` (Python ≥ 3.10; imports matplotlib **inside** the plotting
   functions so the pure functions are importable without it; `matplotlib.use("Agg")`). API:
   ```python
   OKABE_ITO = ["#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7"]
   def world_to_map(start: dict, x: float, y: float) -> tuple[float, float]
       # dx, dy = x - x0, y - y0; x' = cos(t0)*dx + sin(t0)*dy; y' = -sin(t0)*dx + cos(t0)*dy  (C1; t0 in radians)
   def load_world(path: Path) -> dict                      # json; check "schema" == "bm.world/1"
   def load_runlog_poses(path: Path) -> tuple[list[dict], list[dict], list[dict]]
       # (estimate poses from report_corrected.pose, ground truth from gt_pose_map, final map from the last
       #  non-null report_corrected.map); steps with a null report_corrected are skipped for the estimate only
   def seed_of(row: dict) -> int
       # int(row["seed"]) if a non-empty "seed" column exists; else the digits after the last "-s" of
       # row["world_id"] (re.search(r"-s(\d+)$", world_id)); ValueError if neither exists. M2.T10's episodes.csv
       # has no seed column (its world_id is sim-<cond>-s<seed>).
   def pick_representative(rows: list[dict], metric: str, arm: str, model_key: str, condition: str) -> dict
       # keep rows with arm, model_key and condition equal (strings) and a non-empty metric; sort by
       # (float(metric), seed_of(row)); return sorted_rows[(n - 1) // 2] (lower median); ValueError if n == 0
   def plot_arena(world: dict, out_pdf: Path) -> dict      # returns {"n_tags": …, "n_duplicate_pairs": …}
   def plot_trajectories(world: dict, runs: dict[str, Path], out_pdf: Path) -> dict
       # ground truth from the first run; every run must have the same obs_id sequence (ValueError otherwise);
       # tags drawn in the map frame via world_to_map; returns {"n_steps": …, "labels": [...]}
   def main(argv: list[str] | None = None) -> int          # subcommands: arena, pick, trajectory
   ```
   Style (R9): figure 3.45 × 3.0 in, font size 8, `pdf.fonttype` 42, Okabe–Ito colours, ground truth solid black,
   L2 dashed, B0 dotted, B1 dash-dot; tags as squares labelled with the ID, duplicated IDs with a ring;
   start pose as an arrow; equal axis scale; axes "x (m)", "y (m)", frame named in the caption. Save with
   `fig.savefig(out_pdf, metadata={"CreationDate": None})` so the output is byte-identical between runs.
2. *Mac.* Fixtures in `course-project/beaconmind/tests/fixtures/report/`:
   - `world_small.json` — a plotting-only world (not a valid C7 arena: 4 tags): arena 2.0 × 2.0 m; tags
     T00 id 3 at (0.5, 0.0) wall S normal 90; T01 id 5 at (2.0, 1.0) wall E normal 180; T02 id 3 at (1.5, 2.0)
     wall N normal −90; T03 id 7 at (0.0, 1.2) wall W normal 0; `duplicates` `[["T00","T02"]]`; start pose
     (1.0, 1.0, 90.0); other C7 fields as in README C7.
   - `runlog_small.jsonl` — three `step` lines (`obs_id` `e-s000`…`e-s002`): `report_corrected` of step 0 =
     `{"pose": {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}, "map": []}`, of step 1 =
     `{"pose": {"x_m": 0.25, "y_m": 0.0, "theta_deg": 0.0}, "map": [{"beacon": "B5", "id": 5, "x_m": 1.0,
     "y_m": -1.0, "n_obs": 1, "state": "tentative", "suspect": false}]}` (the D8 field names), of step 2 = `null`;
     `gt_pose_map` (0,0,0), (0.24,0.01,0.5), (0.48,0.02,1.0) as `{"x_m", "y_m", "theta_deg"}`; then
     `{"type": "episode_footer", "steps": 3, "ended_by": "budget", "totals": {}}`.
   - `episodes.csv` — the M2.T10 column subset `episode_id,world_id,arm,model_key,condition,ate_unaligned_m` (no
     `seed` column, as in M2.T10) with five L2 rows, model key `qwen35-a3b-think`, condition `duplicated`, ATE
     0.5, 0.1, 0.3, 0.2, 0.4 in worlds `sim-dup-s2004`, `sim-dup-s2000`, `sim-dup-s2002`, `sim-dup-s2001`,
     `sim-dup-s2003` (episode IDs `<world_id>-EXPLORE-k0`), and one B0 row (empty model key) in `sim-dup-s2000`.
3. *Mac.* Write `course-project/beaconmind/tests/test_report_figures.py`. Load the script with the `_load` helper
   of M5.T9. Put `pytest.importorskip("matplotlib")` as the **first line inside each plotting test** (not at module
   level, which would skip the pure-function tests too).
4. *Mac.* `tools/sync_to_spark.sh`; then on the *Spark host* run the tests (command below).
5. *Spark host.* Smoke run on one real generated world. The smoke output goes into the **evidence** folder,
   not into `report/figures/generated/` (only M5.T4/T13/T14 put figures the paper uses there):
   ```bash
   cd ~/Projects/EN.665.715/course-project && W=$(ls data/worlds/sim-dup-s1*.json | head -1) && echo "$W" && \
   mkdir -p evidence/M5/M5.T10 && \
   ~/.venvs/beaconmind/bin/python tools/report_figures.py arena --world "$W" \
     --out evidence/M5/M5.T10/fig-arena-smoke.pdf | tee evidence/M5/M5.T10/smoke.txt
   ```
   Expected: the world path, then `arena: <n> tags, <d> duplicate pairs -> evidence/M5/M5.T10/fig-arena-smoke.pdf`
   with 10 ≤ n ≤ 16 and 1 ≤ d ≤ 3 (C7 duplicated condition). `ls` finds no `sim-dup-s1*` world → the dev worlds
   use another name; run `ls data/worlds | head` and use the first duplicated dev world it lists.
6. *Spark host.* `pdffonts evidence/M5/M5.T10/fig-arena-smoke.pdf | tee evidence/M5/M5.T10/pdffonts.txt | grep -c "Type 3"`
   → `0`. Then run the same `arena` command a second time into `/tmp/fig-arena-smoke-2.pdf` and compare
   `sha256sum evidence/M5/M5.T10/fig-arena-smoke.pdf /tmp/fig-arena-smoke-2.pdf` → equal hashes.
7. *Mac.* Pull the evidence (`bash /Users/xiaohuichen/Projects/EN.665.715/course-project/tools/pull_evidence.sh M5 M5.T10`),
   render `pdftoppm -png -r 100 -singlefile …/evidence/M5/M5.T10/fig-arena-smoke.pdf …/evidence/M5/M5.T10/fig-arena-smoke`
   and look at the PNG: tags on the walls, duplicated IDs ringed, start arrow inside the arena, axes in metres.
8. *Spark host.* **Commands for M5.T4/T14** (document them in the script's `--help`):
   ```bash
   ~/.venvs/beaconmind/bin/python tools/report_figures.py pick --episodes-csv <per-episode metrics CSV> \
     --arm L2 --model-key <model_key> --condition <condition spelling in that CSV> --metric ate_unaligned_m
   # → "episode_id=<id> world_id=<world_id> value=<v> seed=<s> n=<n>"
   ls data/runs/*/<episode_id>.jsonl          # one file per arm that replayed this episode
   ~/.venvs/beaconmind/bin/python tools/report_figures.py trajectory --world data/worlds/<world_id>.json \
     --est "L2=data/runs/<L2 run>/<episode_id>.jsonl" --est "B0=data/runs/<B0 run>/<episode_id>.jsonl" \
     --est "B1=data/runs/<B1 run>/<episode_id>.jsonl" --out report/figures/generated/fig-traj-<episode_id>.pdf
   ```

**Deliverables.** `course-project/tools/report_figures.py`; `course-project/beaconmind/tests/test_report_figures.py`;
fixtures `world_small.json`, `runlog_small.jsonl`, `episodes.csv`; the smoke figure
`course-project/evidence/M5/M5.T10/fig-arena-smoke.pdf` (evidence only, not used by the paper).

**Tests.**
- Unit tests, `test_report_figures.py`:
  - `test_world_to_map_start_is_origin` — the start position maps to (0, 0) within 1e-9.
  - `test_world_to_map_rotation` — start (1, 1, 90°): world (1, 2) → map (1, 0); world (2, 1) → map (0, −1).
  - `test_load_world_rejects_wrong_schema` — `"schema": "bm.obslog/1"` raises `ValueError`.
  - `test_load_runlog_poses_uses_corrected_report` — 2 estimate poses, 3 ground-truth poses, final map has B5.
  - `test_seed_from_world_id` — `seed_of({"world_id": "sim-dup-s2002"})` → 2002; `{"seed": "7", "world_id": "x"}` → 7;
    `{"world_id": "real-arena-1"}` raises `ValueError`.
  - `test_pick_representative_lower_median` — on `episodes.csv` returns the row with ATE 0.3 (world `sim-dup-s2002`).
  - `test_pick_representative_tie_breaks_by_seed` — three in-test rows: ATE 0.1 (`sim-dup-s2000`), 0.2
    (`sim-dup-s2005`), 0.2 (`sim-dup-s2001`) → the row of `sim-dup-s2001`.
  - `test_pick_representative_no_rows_raises` — unknown model key raises `ValueError`.
  - `test_plot_arena_summary_and_pdf` (matplotlib) — returns `{"n_tags": 4, "n_duplicate_pairs": 1}`; the file
    starts with `%PDF` and is > 1 kB.
  - `test_plot_trajectories_mismatched_obs_ids_raise` (matplotlib) — a second run with a different `obs_id` → `ValueError`.
  - `test_pdf_output_deterministic` (matplotlib) — two arena plots of the same world have equal SHA-256.
- Command (Spark host): `cd ~/Projects/EN.665.715/course-project/beaconmind && ~/.venvs/beaconmind/bin/python -m pytest
  -q tests/test_report_figures.py` → `11 passed`. On the Mac (`../.venv`, which has only the `dev` extra, so no
  matplotlib) → `8 passed, 3 skipped`.
- Smoke test (Spark host): step 5 prints the `arena:` line with 10–16 tags and 1–3 duplicate pairs; step 6 prints
  `0` and two equal SHA-256 hashes.

**Acceptance criteria.**
- [ ] 11 tests pass on the Spark host; the 8 pure-function tests also pass on the Mac.
- [ ] The smoke figure has no Type 3 fonts, is readable at print size, and uses the R9 palette and line styles.
- [ ] Figures are byte-identical across two runs.

**Evidence to save.** `course-project/evidence/M5/M5.T10/`: `pytest_spark.txt`, `pytest_mac.txt`, `smoke.txt`,
`pdffonts.txt`, `fig-arena-smoke.pdf`, `fig-arena-smoke.png` (rendered at `-r 100`, < 1 MB), `notes.md` (what the PNG
shows; the two hashes).

**Pitfalls and known gotchas.**
- Files created on the Spark must be pulled back in the same session or the next `sync_to_spark.sh` overwrites
  them (L6).
- The arena's `origin` is the inside south-west corner (C7); estimates are in the map frame (start pose). Mixing
  the two is the classic error: always transform tags with `world_to_map`.
- `theta_deg` is degrees in every JSON (C1); convert to radians only inside `world_to_map`.
- A run log step with `report_corrected: null` (a format violation, C5) has no estimate; do not interpolate.

**Stop-and-ask conditions.** The run-log fields differ from C9.2 (README §1.4 item 3); matplotlib missing from the
Spark venv.

**Estimated effort.** M.

**AI-disclosure note.** Docstrings: `AI-assisted: <model> via <tool>, <date>: wrote the report figure script and
its tests.`

---

### M5.T11 — AI-disclosure ledger, reconciled with Xiaohui

**Why.** The final disclosure must name every model and what it did (AGENTS.md §5). The project's artifacts name
different models: the report draft says Claude Fable 5.1 via Claude Code drafted Section II
(`Chen-Project-Report.tex` lines 8 and 295–307 as of 2026-10-06; commit `37454f3`, trailer `Claude Fable 5.1`); the proposal talk
track says Claude Opus 5.5 **in Cursor** drafted the proposal revision, Cursor Grok 4.6 re-checked citations,
Claude Opus 5.5 **in Claude Code** wrote the design documents, and GPT-5.6 Sol in Cursor helped with the first
proposal (`proposal-talk-track.md` "Generative-AI disclosure"); the deck says "Claude Opus 5.5 drafted this
revision and the design documents" without the tool (`build_proposal.py` lines 521–523, 804–806); the git `Co-Authored-By` trailers over the whole history (counted 2026-10-06) are
"Claude Fable 5.1" (7 commits), "Claude Opus 5 (1M context)" (6), "Claude Opus 5.5 (1M context)" (5),
"Claude Sonnet 5.5" (1) and "Cursor <email removed>" (16, model not named), and many commits have no
trailer. These can all be true for
different artifacts, but only Xiaohui knows. This task builds one ledger with a source for every row and has Xiaohui
confirm it.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| Git history readable | software | `git -C /Users/xiaohuichen/Projects/EN.665.715 log -1 --format=%h` (Mac) | a hash |

**Inputs.** The disclosure paragraphs of: `report/Chen-Project-Report.tex`, `report/REVIEW.md` (header),
`report/mybibfile.bib` (header), `proposal-talk-track.md`, `build_proposal.py` (lines 11–13, 521–523, 804–806),
`AGENT-DESIGN.md`, `APPROACH-LLM-SLAM.md`, `CONTEXT.md` ("Generative-AI provenance"), `plan/README.md` §10, every
`plan/M*.md` file's disclosure line; AGENTS.md §5 "Generative-AI disclosure".

**Steps.**
1. *Mac.* Collect the trailers:
   ```bash
   cd /Users/xiaohuichen/Projects/EN.665.715 && git log --format='%h|%ad|%(trailers:key=Co-Authored-By,valueonly,separator=%x3B)|%s' \
     --date=short -- course-project assignments/assignment4/system-prompt discussions/module4 discussions/module2 \
     > course-project/evidence/M5/M5.T11/git-trailers.txt
   ```
2. *Mac.* Collect in-file disclosures:
   `grep -rnE "AI-assisted|Generative-AI disclosure|Generative AI Disclosure|AI assistance" course-project
   assignments/assignment4/system-prompt discussions/module4 > course-project/evidence/M5/M5.T11/file-disclosures.txt`.
3. *Mac.* Write `course-project/report/DISCLOSURE-LEDGER.md` with a short header (purpose; scope rule below) and
   this table:
   `| # | Artifact or report part | Model | Tool | Dates | What it did | Source of this fact | Used by the report? | Confirmed by Xiaohui |`.
   Seed rows (each with its source; "Confirmed" = `pending`):
   1. Report Section II, Table I, bibliography, review rounds 1–3 — Claude Fable 5.1 — Claude Code — 2026-10-01.
   2. Earlier literature searches behind Section II — Claude Opus 5.5 — Claude Code and Cursor; citations
      re-checked by Grok 4.6 (report disclosure lines 300–302).
   3. Feasibility research, `APPROACH-LLM-SLAM.md`, `AGENT-DESIGN.md` D1–D10 (decisions under delegation),
      RobotSystemPrompts v3.3, geometry tools, rule simulator, smoke harness — Claude Opus 5.5 — Claude Code —
      2026-09-27/28.
   4. Module 4 MCP servers (`gate_detection`, `l2-episodes`) — per their own disclosure lines.
   5. Proposal revision (deck, talk track, build script) — Claude Opus 5.5 — Cursor; citation re-check and deck
      rebuild — Grok 4.6 — Cursor; first proposal version — GPT-5.6 Sol — Cursor.
   6. Implementation plan (`plan/README.md`, `plan/M5-report.md`, other milestone files) — Claude Opus 5.5 —
      Claude Code — 2026-10-05.
   7. One row per git trailer group not covered above (expected: "Claude Opus 5 (1M context)", "Claude Opus 5.5
      (1M context)", "Claude Sonnet 5.5", "Cursor <email removed>"; use whatever step 1 actually
      printed), with the files those commits touched (`git show --stat --format=%h <hash>`) and "Used by the
      report?" decided by the scope rule.
   8. One row per M1–M5 task done so far, from its AI-disclosure note.
   **Scope rule (proposed default):** the report's disclosure covers (a) the report's text, figures, tables,
   bibliography and reviews, and (b) the project artifacts whose content the report describes (design
   documents, prompt, code, data pipeline, analysis). Rows outside both are kept with "no".
4. *Mac.* Write the list of **inconsistencies to resolve** under the table, at least: (a) deck vs talk track tool
   for the proposal revision; (b) the "Claude Opus 5 (1M context)" and "Claude Opus 5.5 (1M context)" trailers vs the documents' "Claude Opus 5.5" (which model wrote what, and whether "Opus 5" is a different model); (c) which model the
   unnamed "Cursor" commits used; (d) whether the report draft's sentence "the author's review of some of those
   choices is still in progress" is still true.
5. **Xiaohui (stop-and-ask).** Show the ledger and the inconsistency list. For each row they answer yes or give the
   correction. In the last column ("Confirmed by Xiaohui") write exactly `yes YYYY-MM-DD`, or, if they corrected
   the row, edit the row's cells to their wording and write `corrected YYYY-MM-DD` (M5.T7's ledger check counts
   these two forms). Write their resolution of each inconsistency under the list. Ask whether they accept the scope
   rule and record the answer under the header.
6. *Mac.* Do **not** edit the report's disclosure now (M5.T7 writes it from the ledger). Update `CONTEXT.md`.

**Deliverables.** `course-project/report/DISCLOSURE-LEDGER.md`; `course-project/evidence/M5/M5.T11/git-trailers.txt`,
`file-disclosures.txt`.

**Tests.**
- Unit tests: none.
- Completeness check (Mac): every distinct value in the trailer column of `git-trailers.txt`
  (`cut -d'|' -f3 git-trailers.txt | tr ';' '\n' | sed 's/^ *//' | grep -v '^$' | sort -u`; the trailer is
  field 3 and the subject comes last, because a subject may contain `|`) appears in at least one ledger row
  (write the list and the matching row numbers in `notes.md`).
- Acceptance check: `grep -c "| pending |" course-project/report/DISCLOSURE-LEDGER.md` → `0` after Xiaohui's answers.

**Acceptance criteria.**
- [ ] Every row has a source; every trailer group is covered.
- [ ] Every inconsistency has Xiaohui's resolution written next to it.
- [ ] Every row confirmed (`yes <date>`) or corrected by Xiaohui.

**Evidence to save.** `course-project/evidence/M5/M5.T11/`: `git-trailers.txt`, `file-disclosures.txt`, `notes.md`
(completeness check, Xiaohui's answers with the date).

**Pitfalls and known gotchas.**
- Never guess which model a past session used; a row without a source stays `pending` until Xiaohui answers.
- Models **evaluated** in the benchmark are not assistance; they do not go in the ledger.
- Name the model you are running as in your own row (L11).

**Stop-and-ask conditions.** Step 5 always; any row whose source contradicts another source.

**Estimated effort.** S.

**AI-disclosure note.** Ledger row for this task: "<model> via <tool>, <date>: compiled the disclosure ledger from
git trailers and file disclosures."

---

### M5.T12 — Interim adversarial review of Sections I–IV

**Why.** Sections I–IV are written months before the results; reviewing them now catches design drift and
citation errors while the facts are fresh, and leaves M5.T7 a smaller final loop. It is also visible preparation
evidence (AGENTS.md §5, 60 % preparation and participation).

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M5.T1, T2, T3 done | task | `for i in M5.T1 M5.T2 M5.T3; do python3 …/tools/task_status.py $i; done` (Mac) | three lines `done` |
| Build clean | build | `python3 …/tools/check_report.py` (Mac) | `RESULT: PASS` |

**Inputs.** The review protocol above; the `.tex`; `CLAIMS.md`; `AGENT-DESIGN.md`; README §6; `report/sources/`.

**Steps.**
1. *Mac.* Save `check_before.txt`.
2. *Fresh sessions.* Run round 1 with lenses RL1 (Sections I and III–IV citations only — Section II was reviewed
   three times in 2026-10), RL2 (only entries added after `37454f3`), RL3, RL5 and RL6, scope Sections I–IV.
   RL4 is skipped (no results yet).
3. *Mac.* Verify, fix, rebuild, log (protocol steps 2–5) under `## Final report — round <n> (M5.T12, <date>)`.
4. Loop until a clean round, **at most three rounds** in this task; remaining confirmed findings go to
   `REVIEW.md` "Open issues" for M5.T7.
5. *Mac.* Save `check_after.txt`.

**Deliverables.** `course-project/report/REVIEW.md` (new rounds); fixed `.tex`; `evidence/M5/M5.T12/round-<n>-RL<k>.md`.

**Tests.**
- Unit tests: none (prose only; no code changes).
- Smoke test (Mac): `check_report.py` → `RESULT: PASS` after the fixes.
- Review test: each round's `REVIEW.md` table lists every lens run, and each finding is marked confirmed or rejected.

**Acceptance criteria.**
- [ ] Every finding verified against its source before any change (AGENTS.md §6.2).
- [ ] Either a clean round, or three rounds with the leftovers listed as open issues.
- [ ] `RESULT: PASS`.

**Evidence to save.** `course-project/evidence/M5/M5.T12/`: `check_before.txt`, `check_after.txt`, raw lens outputs.

**Pitfalls and known gotchas.** A reviewer may "correct" Section II towards APPROACH; R1 says AGENT-DESIGN wins. A
reviewer asking to cite Li et al. as a conference paper was rejected before (`report/REVIEW.md` round 2).

**Stop-and-ask conditions.** A confirmed critical finding in Section II (graded text); a finding that requires a
design change (R14).

**Estimated effort.** S.

**AI-disclosure note.** `REVIEW.md` round header names the reviewer model(s) and tool; ledger row.

---

### M5.T13 — Experiments update: frozen pre-registration and the real setup

**Why.** M4.T1 freezes endpoints, episode counts, seeds, roster and budget before the test seeds run (README §3.2);
M3.T10 and M3.T17 produce the measured real arena and the overhead ground-truth camera accuracy. Section IV must
state the protocol exactly as frozen and any deviation from it.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M5.T3 done | task | `python3 …/tools/task_status.py M5.T3` (Mac) | `done` |
| M4.T1 done | task | `python3 …/tools/task_status.py M4.T1` (Mac) | `done` |
| Pre-registration frozen | file | `ls /Users/xiaohuichen/Projects/EN.665.715/course-project/preregistration/` (Mac) | `PREREG.md`, `prereg.json`, `FROZEN.json`, `DEVIATIONS.md` (M4.T1 step 15). `FROZEN.json` missing → not frozen: stop |
| M3.T10, M3.T17 (soft) | task | `for i in M3.T10 M3.T17; do python3 …/tools/task_status.py $i; done` (Mac) | `done` → write the real setup (arena from M3.T10, ground-truth accuracy from M3.T17); else keep `pending:` |

**Inputs.** `preregistration/PREREG.md`, `prereg.json`, `FROZEN.json` (`frozen_at`, hashes), `DEVIATIONS.md`
(whole); `plan/M4-benchmark.md` M4.T1 deliverables; `configs/roster.json` (`bm.roster/1`, `selected`,
`closed_loop`), `configs/seeds.json`; `configs/arenas/real-*.json`; `evidence/M3/M3.T17/` (ground-truth camera
accuracy table); `configs/providers.json` (C11); Section IV.

**Steps.**
1. *Mac.* Save `check_before.txt`; record `shasum -a 256 …/preregistration/PREREG.md …/preregistration/prereg.json`
   in `notes.md` and compare with `FROZEN.json` → `sha256`. Different → stop and ask (the frozen files changed).
2. *Mac.* Update IV-A/IV-C/IV-D to the frozen values: seed ranges and counts, K, missions per seed, the roster
   (a `table` `tab:roster` with model, provider family, mode — thinking/effort — and role; typed from the
   frozen file, with one `CLAIMS.md` row per model citing the file and its SHA-12; **no prices**), the budget cap,
   the pre-registered hypotheses H1–H3 and targets (OD6), quoting them from `PREREG.md`. Add one sentence that the
   protocol was frozen before the test seeds ran, with the date from `FROZEN.json` → `frozen_at` (date part only).
   The roster table is replaced by M4.T16's generated `tables/tab_roster.tex` in M5.T14; keep this typed table
   short (model, provider family, mode, role).
3. *Mac.* Real setup (if M3.T10 and M3.T17 are `done`): arena size and tag count from `configs/arenas/real-*.json`;
   how tags were printed and measured (C7 `measured`); the overhead camera's measured error from
   `evidence/M3/M3.T17/` (C8: accepted within 5 cm / 3°). If only M3.T10 is done, describe the arena and keep the
   ground-truth sentence `pending:M3.T17`. Real-arena figure: run M5.T10 `arena` on `configs/arenas/real-<name>.json` on the
   Spark host and pull it. Photos: none unless Xiaohui provides one with no person or personal item in view (R13).
4. *Mac.* Deviations: read `preregistration/DEVIATIONS.md`; each entry (date, what, why, consequence) becomes a
   sentence in IV-D. File has only its header → write nothing (do not claim "no deviations"; M5.T14 re-reads the
   file after M4 finishes).
5. *Mac.* Update `CLAIMS.md` (`pending:M4.T1`, `pending:M3.T10`, `pending:M3.T17` → `ok` where
   resolved); run the check; render; save diff.

**Deliverables.** `course-project/report/Chen-Project-Report.tex` (Section IV); `CLAIMS.md`;
`report/figures/generated/fig-arena-real-<name>.pdf` (if the real arena exists).

**Tests.**
- Unit tests: none (prose only; no code changes).
- Smoke test (Mac): `check_report.py` → `RESULT: PASS`.
- Consistency test (Mac): every seed range, count and K in Section IV equals the pre-registration (list each pair
  in `notes.md`).

**Acceptance criteria.**
- [ ] Section IV matches the frozen pre-registration exactly; deviations stated if M4 recorded any.
- [ ] Real setup described only from M3 evidence.
- [ ] `RESULT: PASS`.

**Evidence to save.** `course-project/evidence/M5/M5.T13/`: `check_before.txt`, `check_after.txt`, `notes.md`, `tex.diff`.

**Pitfalls and known gotchas.** Never edit anything under `preregistration/` (README L1: never edited after
freezing). Model IDs and prices go stale (C11): in prose the report names models, not prices; prices appear only
inside M4.T16's generated `tab_roster.tex`, next to their `price_checked` date (M5.T14). The M4 file calls the
ground-truth accuracy evidence `evidence/M3/M3.T11/`; the M3 file moved that acceptance to M3.T17 — use
`evidence/M3/M3.T17/`, and if it is missing look in `evidence/M3/M3.T11/` and record which one you used.

**Stop-and-ask conditions.** The pre-registration and M4's actual runs disagree with no recorded deviation.

**Estimated effort.** S.

**AI-disclosure note.** `% AI-assisted (<model>, <date>): updated Section IV to the frozen pre-registration and the
real setup.`

---

### M5.T14 — Results update to the full benchmark

**Why.** M4 produces the held-out replay sweep (M4.T4), the closed-loop sweep on held-out kinsim seeds (M4.T5),
the request-suite scores (M4.T14), the real-log replay and sim-to-real gap (M4.T13), the Isaac closed-loop
confirmatory subset (M4.T15), and — in M4.T16 — the frozen analysis: `evidence/M4/M4.T16/results.json`,
`analysis_stdout.txt`, `results_summary.md` (the hand-off), the per-table CSVs in `data/results/final/` on the
Spark, and the generated `report/generated/tables/tab_*.tex` and `report/generated/figures/fig_*.pdf`
(`plan/M4-benchmark.md` M4.T6 step 6 table, M4.T16 steps 2–5). Section V must report them, with the hypotheses
H1–H3 and the targets T-a…T-k exactly as M4.T16 decided them. **Under the cut line** (README §3.4) M4 is reduced
to the real-log replay of 2–3 models; then this task reports only that (from M3.T19 or M4.T13), or is set
`dropped (cut line)` if nothing new exists. The M4 file says its hand-off goes to "M5.T4"; in this file the M4
hand-off is consumed **here**, because M5.T4 reports M2.T12's first result.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M5.T4 done | task | `python3 …/tools/task_status.py M5.T4` (Mac) | `done` |
| M4.T16 done | task | `python3 …/tools/task_status.py M4.T16` (Mac) | `done`. If M4 was cut (README §3.4), check `python3 …/tools/task_status.py M3.T19` instead: `done` → this task shrinks to the real-log replay of 2–3 models (step 0); otherwise set M5.T14 `dropped (cut line)` |
| M4 hand-off on the Mac | files | `ls …/evidence/M4/M4.T16/ …/report/generated/tables/ …/report/generated/figures/` (Mac) | `results.json`, `analysis_stdout.txt`, `results_summary.md`; `tab_*.tex`; `fig_*.pdf`. Missing → pull them (step 1) |
| Spark reachable | service | `ssh -o ConnectTimeout=15 -o BatchMode=yes xiaohui_chen@spark-2a60 'ls ~/Projects/EN.665.715/course-project/data/results/final/'` (Mac) | `results.json` and one CSV per table |

**Inputs.** `plan/M4-benchmark.md` M4.T6 step 6 (the table and figure list), M4.T16 (whole), and the deliverables of
M4.T4, M4.T5, M4.T13, M4.T14, M4.T15; `evidence/M4/M4.T16/results_summary.md`, `analysis_stdout.txt`,
`results.json`; `preregistration/PREREG.md`, `DEVIATIONS.md`; `report/assets.json`; Section V; R3, R4.

**Steps.**
0. *Cut-line variant only* (M4.T16 not done, M3.T19 done): pull `evidence/M3/M3.T19/`; add its result CSV to
   `assets.json` exactly as M5.T4 step 3 did (a `tab-real` table and `\bmnum` keys with `<mode>` `replay` and the
   real-log condition); write the RQ3 transfer paragraph in V-C (labels `real car`, `replay`, with the
   ground-truth camera error from `evidence/M3/M3.T17/` next to it, C8); then do steps 6–8 and skip the rest.
1. *Mac.* Save `check_before.txt` and `before.tex`. Pull the M4 hand-off:
   `bash /Users/xiaohuichen/Projects/EN.665.715/course-project/tools/pull_evidence.sh M4 M4.T16`, then
   ```bash
   ssh -o ConnectTimeout=15 -o BatchMode=yes xiaohui_chen@spark-2a60 \
     'cd ~/Projects/EN.665.715 && tar czf - course-project/report/generated/tables course-project/report/generated/figures' \
     | tar xzf - -C /Users/xiaohuichen/Projects/EN.665.715
   ```
2. *Spark host → Mac.* **Result CSVs as sources for `\bmnum`.** Copy the per-table CSVs (small) into evidence and
   pull them: `ssh … 'cd ~/Projects/EN.665.715/course-project && mkdir -p evidence/M5/M5.T14/results-final && cp data/results/final/*.csv evidence/M5/M5.T14/results-final/ && ls -la evidence/M5/M5.T14/results-final'`,
   then `bash …/tools/pull_evidence.sh M5 M5.T14`. Every file must be < 1 MB (L8); a larger one → stop and ask.
3. *Mac.* **Record the M4-owned assets.**
   `cd /Users/xiaohuichen/Projects/EN.665.715/course-project && shasum -a 256 report/generated/tables/*.tex report/generated/figures/*.pdf > evidence/M5/M5.T14/m4-assets.sha256`.
   For each figure: `pdffonts <file> | grep -c "Type 3"` → `0`; a Type 3 font → stop and ask for M4.T16's
   `make_report_assets.py` to be rerun with `pdf.fonttype` 42 (never edit a PDF). For each table:
   `head -5 <file>`; if it contains `\begin{table` → `\input` it directly; if it holds only a `tabular` → wrap
   the `\input` in a `table` environment written in the `.tex`, with a `\caption` naming the M4 sweep, R4 labels,
   the number of seeds and K, and a `\label{tab:<name>}`. **Never edit a file under `report/generated/tables/`
   or `figures/`**; regenerate through M4.T16 instead.
4. *Mac.* **Numbers.** Add the CSVs of step 2 to `assets.json` `sources` (paths `evidence/M5/M5.T14/results-final/<file>.csv`).
   Where M4 supersedes an M2.T12 number, keep the same key and change only its `source`/`where` (so the text
   stays put); list every switched key in `notes.md`. Use the **same number of decimals** as the M4 table that
   shows the same quantity (read it from the table file), so prose and table never disagree. Statistics: add
   `numbers` only for values present in the CSVs (test name, statistic, raw and Holm-adjusted p, CI bounds);
   write them as "… (Wilcoxon signed-rank with Holm correction, $p_{\text{Holm}}=\bmnum{…}$)". Never compute or
   round a p-value by hand. Run `python3 …/tools/report_assets.py` → `assets: wrote …`.
5. *Mac.* **Rewrite Section V** from `results_summary.md` and the tables (quote nothing that is not in a CSV or
   table):
   - V-A (RQ1): `tables/tab_replay_sim` and `tables/tab_assoc` replace `tab-replay` (remove `tab-replay` from
     `assets.json` `tables` when its content is fully covered; keep its numbers); H1's outcome from
     `tables/tab_hypotheses`; the trajectory figure: use M4.T16's `figures/fig_traj_example.pdf` (median-ATE seed of
     the selected model, the same rule as M5.T10) and remove the M5.T4 trajectory figure, so the paper shows one
     rule-chosen episode; `figures/fig_ate_box.pdf` if the page budget allows.
   - V-B (RQ2): `tables/tab_closed_loop` (label the kinsim sweep `kinematic simulation, closed loop`, and the
     M4.T15 subset `simulation (Isaac Sim), closed loop`, R4), `figures/fig_explore_curve.pdf`, `tables/tab_suite`
     (refusal), H2's outcome.
   - V-C (RQ3): `tables/tab_validity_cost`, `figures/fig_pareto.pdf`; transfer from `tables/tab_real` and
     `figures/fig_sim2real.pdf` only if M4.T13 is `done` (labels `real car`, `replay`; ground-truth camera error
     next to it, C8); H3's outcome.
   - Targets: `tables/tab_targets` replaces `tab-targets` (every target *met*, *not met* or *not measured* with
     the reason, as M4.T16 recorded).
   - The roster: replace the typed `tab:roster` of M5.T13 with `tables/tab_roster` (its prices carry their
     `price_checked` dates; prose still names no prices).
   - Deviations: re-read `preregistration/DEVIATIONS.md`; every entry is stated in IV-D (M5.T13's rule).
   Include M4 figures with `\includegraphics[width=\columnwidth]{generated/figures/<name>}` (`figure*` and
   `\textwidth` only for `fig_pareto` if its two panels are unreadable at one column).
6. *Mac.* `python3 …/tools/report_assets.py --check` → `assets: up to date`;
   `shasum -a 256 -c …/evidence/M5/M5.T14/m4-assets.sha256` → every line `OK` (run from the course-project folder);
   the report check → `RESULT: PASS`; render the Section V pages and look at every table and figure.
7. *Mac.* `CLAIMS.md`: `pending:M5.T14` → `ok` with the table or key as source.
8. *Mac.* Save `check_after.txt` and the diff.

**Deliverables.** `course-project/report/assets.json`; `report/generated/` (M5-owned files regenerated);
`course-project/evidence/M5/M5.T14/results-final/*.csv`, `m4-assets.sha256`; Section V (and IV-C roster, IV-D
deviations) of `Chen-Project-Report.tex`; `CLAIMS.md`.

**Tests.**
- Unit tests (Mac): `cd …/beaconmind && ../.venv/bin/python -m pytest -q tests/test_report_assets.py tests/test_check_report.py`
  → `32 passed` (no code change in this task; this proves the tools still work).
- Smoke tests (Mac): `report_assets.py --check` → `assets: up to date`; `shasum -a 256 -c` → all `OK`;
  `check_report.py` → `RESULT: PASS` with `missing numbers 0`.
- Traceability test (Mac): three random `\bmnum` keys traced through `MANIFEST.txt` to a row of a
  `results-final/*.csv` file (M5.T4's procedure), and one number in each of two M4 tables found in
  `evidence/M4/M4.T16/results.json` (`grep -n "<value>"`); write all five checks in `notes.md`.
- Consistency test (Mac): for every hypothesis and target, the outcome word in the text equals the one in
  `results_summary.md` (list the pairs in `notes.md`).

**Acceptance criteria.**
- [ ] Every RQ2/RQ3 statement rests on a generated number or table; statistical claims name the test and use M4's
      Holm-adjusted values.
- [ ] H1–H3 and every target T-a…T-k reported with the outcome M4.T16 recorded; unmet targets stated as unmet.
- [ ] Every result labelled with its source (`kinematic simulation`, `simulation (Isaac Sim)`, `real car`) and mode
      (R4); real-log results carry the ground-truth camera error (C8).
- [ ] No M4-owned file edited (`shasum -c` all `OK`).
- [ ] `RESULT: PASS`.

**Evidence to save.** `course-project/evidence/M5/M5.T14/`: `check_before.txt`, `before.tex`, `check_after.txt`,
`results-final/`, `m4-assets.sha256`, `assets_run.txt`, `MANIFEST.txt` (copy), `notes.md`, `tex.diff`.

**Pitfalls and known gotchas.**
- M4's tables use `\hline` (M4.T6 step 6, revised 2026-10-06: kept for consistency although M5.T8 loads
  `booktabs` — both work, so nothing needs changing). Mixed rule styles between M5- and M4-generated tables are acceptable; do not
  hand-edit either to match.
- Keeping the same keys when M4 supersedes M2 keeps the text stable, but the caption must say which sweep the
  table comes from. Closed-loop exploration figures and replay estimation tables must not be merged (D1d).
- `data/results/final/` stays on the Spark (L8); only the small CSV copies go into evidence.

**Stop-and-ask conditions.** M4 results contradict M2.T12's first result in direction (Xiaohui decides how to
present it; default: report M4 as the main result and mention the pilot difference in V-D); the frontier spend in
M4 exceeded the pre-registered budget (report it; ask first); `results_summary.md` and `analysis_stdout.txt`
disagree on an outcome; an M4 table or figure is missing from the M4.T6 list.

**Estimated effort.** M.

**AI-disclosure note.** `% AI-assisted (<model>, <date>): updated Section V to the full benchmark.`

---

### M5.T15 — Abstract, index terms and title check

**Why.** The abstract is written last because it states the results. IEEE abstracts are one paragraph without
citations; index terms are 4–6 phrases.

**Prerequisites.**
| Prerequisite | Kind | Check command (machine) | Expected result |
| --- | --- | --- | --- |
| M5.T5 done | task | `python3 …/tools/task_status.py M5.T5` (Mac) | `done` |

**Inputs.** The whole `.tex`; `report/generated/numbers.json`; `budget.json` (abstract length from M5.T8 step 6).

**Steps.**
1. *Mac.* Replace the abstract text with one paragraph of 150–220 words: problem (one sentence), gap (one), what
   BeaconMind is (two), evaluation (one: replay on simulated and real logs against B0/B1/B2, closed loop in
   simulation), headline results (two to three, `\bmnum` only), conclusion (one). No citations, no undefined
   acronyms (define LLM and SLAM inside the abstract).
2. *Mac.* Replace the index terms with: `large language models, simultaneous localization and mapping, fiducial
   markers, mobile robots, embodied agents, benchmarking` (default; adjust only if Section V's emphasis differs,
   keeping 4–6 terms).
3. *Mac.* **Title check.** Default: keep "BeaconMind: Can a Large Language Model Own Landmark SLAM?". A change is a
   stop-and-ask; if Xiaohui changes it, update `\title` and the `\pdfinfo` line together.
4. *Mac.* Word count: `pdftotext -f 1 -l 1 Chen-Project-Report.pdf - | awk '/Abstract/,/Index Terms/' | wc -w`
   (approximate; must be within 150–220 + the two marker words). Run the check; render page 1; save diff.

**Deliverables.** `course-project/report/Chen-Project-Report.tex` (abstract, index terms).

**Tests.**
- Unit tests: none (prose only; no code changes).
- Smoke tests (Mac): `check_report.py` → `RESULT: PASS`, `placeholders` reduced by 2; the word count in range.

**Acceptance criteria.**
- [ ] Abstract 150–220 words, no citation, results only via `\bmnum`.
- [ ] 4–6 index terms.
- [ ] Title unchanged or changed with Xiaohui's approval and `\pdfinfo` updated.

**Evidence to save.** `course-project/evidence/M5/M5.T15/`: `check_after.txt`, `wordcount.txt`, `tex.diff`.

**Pitfalls and known gotchas.** `\bmnum` inside the abstract works (it is ordinary text), but `pdftotext` word
counts include numbers; that is fine. The IEEEtran abstract heading is printed as "Abstract—".

**Stop-and-ask conditions.** Any title change.

**Estimated effort.** S.

**AI-disclosure note.** `% AI-assisted (<model>, <date>): drafted the abstract and index terms.`

---

## Milestone-level integration and smoke test (run in M5.T7, after the last fix)

All on the Mac unless stated.

1. **Reproducibility of numbers and tables.** Copy the inputs to a scratch tree and regenerate from nothing:
   ```bash
   S="$TMPDIR/bm-m5-int" && rm -rf "$S" && mkdir -p "$S" && cd /Users/xiaohuichen/Projects/EN.665.715/course-project && \
   COPYFILE_DISABLE=1 tar cf - report/assets.json evidence tools | tar xf - -C "$S" && \
   python3 tools/report_assets.py --assets "$S/report/assets.json" --root "$S" && \
   diff -r -x tables -x figures -x .gitkeep "$S/report/generated" report/generated && echo "generated: identical" && \
   shasum -a 256 -c evidence/M5/M5.T14/m4-assets.sha256 | grep -vc ": OK$"
   ```
   Expected: `assets: wrote …`, then `generated: identical` (M5-owned files only; `tables/` and `figures/` belong
   to M4.T16), then `0` (no M4-owned file changed; skip the `shasum` part if M5.T14 was dropped).
2. **Clean build from a copy.**
   ```bash
   C="$TMPDIR/bm-report-copy" && mkdir -p "$C" && cd /Users/xiaohuichen/Projects/EN.665.715/course-project && \
   COPYFILE_DISABLE=1 tar cf - --exclude report/sources report | tar xf - -C "$C" && \
   python3 tools/check_report.py --final --report-dir "$C/report" | tail -1
   ```
   → `RESULT: PASS` (proves the build needs nothing outside `report/`).
3. **Figures reproducible.** On the Spark host, re-run each `report_figures.py` command recorded in
   `evidence/M5/M5.T4/notes.md` (and M5.T13) with `--out /tmp/bm-repro/<same file name>` and compare
   `sha256sum /tmp/bm-repro/*.pdf` with `sha256sum report/figures/generated/*.pdf` → equal for each file. (M4-owned
   figures are M4.T16's responsibility; step 1's `shasum -c` covers them.)
4. **Unit tests.** Mac (from `course-project/beaconmind`): `../.venv/bin/python -m pytest -q tests/test_report_assets.py
   tests/test_check_report.py tests/test_report_figures.py` → `40 passed, 3 skipped` (the 3 plotting tests skip
   without matplotlib); Spark host: the same three files with `~/.venvs/beaconmind/bin/python` → `43 passed`, or
   `42 passed, 1 skipped` if the LaTeX tools are absent there (as recorded in M5.T9).
5. **Hygiene.** `grep -c "pending:" report/CLAIMS.md` → `0`; `grep -c "| pending |" report/DISCLOSURE-LEDGER.md` →
   `0`; `grep -nE "sk-|api_key|password|ssid" report/Chen-Project-Report.tex report/*.md` → nothing (L9).

Save all outputs in `course-project/evidence/M5/M5.T7/integration.txt`.

## Milestone exit checklist

- [ ] Status table: every task `done` or `dropped (cut line)` (only T13/T14 may be dropped, and only under the cut line).
- [ ] `check_report.py --final` → `RESULT: PASS`; page count within `budget.json`.
- [ ] `report_assets.py --check` → `assets: up to date`; integration test steps 1–5 pass.
- [ ] All six template sections present plus abstract, index terms, Discussion and Limitations, disclosure.
- [ ] `CLAIMS.md`: no `pending:`; `proposed:` only for ODs still open in AGENT-DESIGN.
- [ ] `DISCLOSURE-LEDGER.md` fully confirmed; the disclosure section matches it.
- [ ] `REVIEW.md` ends with a clean full round (RL1–RL6) and lists any open issues.
- [ ] Xiaohui read the PDF and confirmed readiness (date in `CONTEXT.md`).
- [ ] Nothing committed without Xiaohui's request (L10); when asked, stage only `course-project/report/`,
      `course-project/tools/report_*.py`, `course-project/tools/check_report.py`, `course-project/tools/task_status.py` (README L12),
      the new tests and fixtures,
      `course-project/evidence/M5/`, `course-project/plan/M5-report.md` and `course-project/CONTEXT.md`.

## `CONTEXT.md` update on completion

Add a dated section near the top (below the M0 section):

```markdown
## <YYYY-MM-DD> — M5 done: final report complete

- **Deliverable:** `report/Chen-Project-Report.pdf` (<n> pages; budget <B> pages, references <counted|not counted>),
  built with `latexmk`; `tools/check_report.py --final` PASS (`evidence/M5/M5.T7/check_final.txt`).
- **Content:** Sections I–VI, Discussion and Limitations (V-D), disclosure. Results from <M2.T12 only | M4 full
  benchmark>; <cut line invoked on <date> | not invoked>.
- **Numbers:** every result is a `\bmnum` key from `report/generated/` (`tools/report_assets.py`, manifest with
  SHA-256 of each source CSV). Figures from `tools/report_figures.py` (Spark host).
- **Review:** final rounds <n>–<m> in `report/REVIEW.md`; last round clean. Open issues: <list or none>.
- **Disclosure:** from `report/DISCLOSURE-LEDGER.md`, confirmed by Xiaohui on <date>.
- **Xiaohui read the final PDF on <date> and confirmed it is ready to submit.** Submit per M6.T1.
- **Not committed** unless stated: <files>.
```

Also replace the `CONTEXT.md` "2026-10-01 class project report" bullet "Later sections go into the same `.tex`…"
with a pointer to that new section.

## Risks specific to M5, with mitigations

| Risk | Effect | Mitigation |
| --- | --- | --- |
| No page limit known | Over-length or over-trimmed paper | M5.T8 asks Xiaohui first; budget in `budget.json`; checker enforces it in final mode |
| Results arrive late (cut line, M2.T12 or M4 slips) | Section V thin at the deadline | Sections I–IV written early (groups A–C); calendar triggers above; Section V can ship with M2.T12 results only, stated as such |
| Text drifts from the data | Wrong numbers in a graded paper | R3: `\bmnum` + generated tables + SHA-256 manifest + `--check`; traceability spot checks in M5.T4/T14 |
| Design drift (v3.3 → v3.4) after Sections I–III are written | Paper describes a superseded design | M5.T3 step 2 re-syncs from the AGENT-DESIGN diff; RL3 lens in M5.T12 and M5.T7 |
| Disclosure inaccurate or incomplete | Academic-integrity problem (AGENTS.md §5) | M5.T11 ledger with sources; Xiaohui confirms each row; M5.T7 writes the section only from the ledger |
| Reviewer hallucinations | Correct text "fixed" into wrong text | Verify-before-fix (AGENTS.md §6.2); rejected findings logged with reasons |
| Over-trimming Section II | Loses graded, verified content or orphans citations | M5.T6 cut order and "never" list; `entry never cited` check; cut log |
| A lower-end executor describes the design from APPROACH or memory | Critical consistency error (happened in round 1 of the draft) | R1; RL3 lens; `CLAIMS.md` sources per claim |
| Novelty claim weakened by new literature | Overclaiming | M5.T6 step 6 retries the open literature items; hedge kept; stop-and-ask |
| Type 3 fonts or unembedded fonts | Print or submission problems | `pdf.fonttype` 42; `pdffonts` checks in M5.T2, T10, T7 |
| `flushend` interacting with floats | Broken last page | M5.T4 pitfall: switch to `\IEEEtriggeratref` |
| Two generators write under `report/generated/` (M5.T9's tool and M4.T16's `make_report_assets.py`) | One overwrites or flags the other; prose and tables round differently | Ownership split: M5 owns the top level, M4 owns `tables/` and `figures/`; `--check` and the integration diff ignore M4's folders; M4 files are hash-recorded (`m4-assets.sha256`) and never edited; prose uses the M4 table's decimals (M5.T14 step 4) |
| Ambiguous status checks (an ID appears in several tables) | A lower-end executor starts a task whose prerequisite is not done | `tools/task_status.py` (README L12; M5.T8 step 8b checks it) reads only the status-table row |
| Spark-generated figures overwritten by a Mac push | Stale or missing figures | L6: pull in the same session; deterministic PDFs make regeneration safe |

## Generative-AI disclosure (this file)

Claude Opus 5.5 via Claude Code wrote this milestone plan on 2026-10-05: the task breakdown (M5.T1–T7 as reserved
in `plan/README.md` §3.2, plus T8–T15), the writing rules R1–R14, the review protocol adapted from AGENTS.md §6,
the specifications of `check_report.py`, `report_assets.py` and `report_figures.py` and their tests, the section
targets and every default marked as proposed. It ran read-only checks on the Mac on 2026-10-05 (the report build
outputs, cite and bib keys, placeholders, page and font checks, the LaTeX toolchain and package versions, the
instructor's template zip, git co-author trailers). Xiaohui Chen owns the project and the report, decides the page
budget, the disclosure ledger and the title, and reviews and may overturn any proposal here.

On 2026-10-06 Claude Opus 5.5 via Claude Code adversarially reviewed and corrected this file against the README,
AGENT-DESIGN v3.3, the M1–M4 and M6 plan files, the report sources and the repository state: it replaced the
ambiguous status greps with a status helper (now the README L12 `tools/task_status.py`), corrected cross-milestone task IDs (M3.T17, M3.T19, M2.T13,
M2.T14, M2.T20, M4.T16), reconciled the report pipeline with M4.T16's generated tables and figures, fixed the
`dv.json` access path, the BibTeX-warning and secret-scan rules, the ledger check and the v3.3 diff command,
moved the checker's unit tests into M5.T8, and supplied the architecture-figure source after compiling and
rendering it in a scratch directory (no file in the repository other than this plan was changed).

Cross-plan consistency review, 2026-10-06, by Claude Opus 5.5 via Claude Code: cross-milestone task IDs, shared files and contracts aligned with the other five milestone files and `plan/README.md` (details and the list of edits in `plan/REVIEW.md`). Read-only checks on the Mac only; nothing was run on the Spark.
