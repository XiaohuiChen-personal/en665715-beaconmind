# Adversarial review of the first full draft (2026-10-29/30)

One round, as Xiaohui asked. Three independent reviewers (Claude Opus 5.5 subagents in Cursor), each with its
own lenses, read the compiled PDF, the LaTeX source and the evidence. None edited files. Every finding was then
checked by the main agent against the source, the code or the logs before anything was changed. The earlier
Related Works review is `REVIEW.md`.

| Reviewer | Lenses | Result |
| --- | --- | --- |
| A | Requirement coverage against the assignment and rubric; writing and formatting (all pages rendered) | 7 critical, 13 major, 18 minor |
| B | Every number, statistic and empirical claim, recomputed independently from the raw logs | 4 critical, 7 major, 12 minor; all core numbers reproduced |
| C | Citation integrity (bib keys, claims against `evidence/M5/eval_refs.md` and the reviewed 2026-10-01 text); design, hardware and software accuracy against AGENT-DESIGN, plan, CONTEXT, `car.json`, `reference/hardware/` | 0 critical, 9 major, 16 minor, 5 nits |

## Confirmed and fixed (grouped)

- **Missing required items:**
  - Table III is now referenced in the text.
  - The rubric anchors for all four criteria are written out (from `metrics/judge.py`).
  - The camera tilt is stated as not measured, with how and when it will be measured. It is not invented.
  - H0/H1 are given for H2 and H3; the 0.15 and 0.90 thresholds are justified, and the tolerance reasons are tied to the plan.
  - The real-car procedure is a numbered list with end conditions.
  - The logging fields and the scored-results columns are named.
  - Software settings were added: ROSA 1.0.10, Gazebo not used, temperatures not set, the Qwen checkpoint, input tokens per step, code paths.
  - The real environment was added (tags, ceiling webcam, lighting record, Wi-Fi).
- **False or overstated statements:**
  - The "power curve" pointer is replaced by a description of the normal-model simulation.
  - The extra-call list now adds up (3 others) and gives precision per block.
  - The tables and text now agree on medians: Table IV shows median and range, and the macros use medians.
  - Unbuilt parts are no longer described as working (Isaac twin, latching STOP, standby pull-down, validator auto-latch, vLLM/Ollama agent back ends in Fig. 1).
  - Table II's state check is marked as not in the pilot harness.
  - The pilot cost now separates the agent from the judges (Sol US$3.51 + US$6.76).
  - "Exactly as accurate" became "within about 0.5 cm".
  - The judge evidence is called "extended", and the remaining omitted field is named, since it caused the one remaining gate failure.
  - The sweep crossover is stated for medians only.
  - The duplicated-ID precision is qualified: the copies are at least 1.5 m apart against a gate of at most 0.6 m, which is a validity threat. The phantoms under drift are reported.
  - The power sensitivity is given (the SD interval is 1.9-8.9 cm, and power at the upper end is 0.33).
  - The p-value is framed against Holm's α/3.
  - The uncached Opus cost is corrected (54,124 tokens, US$0.25 per decision, re-computed from `evidence/M1/M1.T11/opus20-records.jsonl`).
  - The API-failure rule now matches the code and M4.T1.
  - The battery is checked before each episode (S8), not per block.
  - The K = 3 Opus sweep was replaced: frontier models run at K = 1 within a sweep budget still to be set, because the full design would cost about US$1,000.
- **Citations:**
  - Restored to the reviewed wording: Jiang et al.'s cell-type prompt and dead-end retreat; Li et al.'s chain-of-thought; Sturm "formalize"; Lee et al.'s "spatial-reasoning navigation trials"; "identified in the literature search"; L3MVN "selects".
  - Two paraphrases were softened: Dror et al. now reads "most NLP setups", and Gorilla/BFCL "in the spirit of".
  - The bib header now records the 14 new entries.
- **Judges:**
  - Inter-judge agreement is reported with κ and the ceiling effect.
  - The Gemma real-note run is reported as partial.
  - "Held out" for the judge items became "calibration seeds 1001-1004".
  - The analysis and the archived judge files now come from the same snapshot (Gemma stopped first).
- **Trace (Fig. 2):** re-run with the API's summarized-thinking display (`thinking.display = "summarized"`), so the Thought rows show the model's own summaries. The caption names the setting, says the results are abridged, and says the logged note differs only in wording.
- **Late fixes (2026-10-30):** "6-DOF" spelled out; Zheng et al.'s 85 %/81 % qualified as MT-Bench expert votes without ties; the DGX Spark's memory given as the 128 GB specification in the text and Fig. 1 (the OS reports 121 GB).
- **Typography and names:** real minus signs, American spelling, a defined "coded procedure" (B2) and L2, ATE-RMSE defined, no "D7" or task IDs in the text, the overlong pilot sentence split into a list.

## Not changed, with reason

- **Calibrate the judges against the author's own scores (A8).** Xiaohui ruled out hand scoring (2026-10-29). The draft says so and describes the automated checks that take its place.
- **The camera tilt value (A3).** It needs a physical measurement by Xiaohui. It is not invented.
- **Length (A38).** The draft is 11 pages, about 9.5 of body plus references. Section II-B was condensed and the disclosure shortened. Further cuts would remove required Experiments content; Table I stays as the Related Works synthesis.
- **"The code is public" (C2).** The pilot code is not yet committed or pushed. Committing and pushing to the public repo is left to Xiaohui. Until then the link shows the M1.T16 state.
- **Pre-registration not yet revised (C20).** The draft says the plan's M4.T1 will be revised to match before it is frozen.
- **Fig. 1 STOP drawn as a separate link (C21).** Kept as a conceptual out-of-band path; minor.
- **Holm vs fixed-sequence testing (B23).** Kept Holm, as in the plan; the no-drift test is now explicitly outside the family.

## Validation after the fixes

- `latexmk -pdf Chen-Project-Report.tex`: exit 0. No LaTeX errors, no overfull boxes, no undefined references or citations, and 0 BibTeX warnings. 41 references, all cited.
- Abstract: 247 words with the macros expanded. No placeholder text left.
- All numbers come from `pilot_macros.tex`, `tab_pilot.tex`, `tab_judge.tex` and `fig_trace.tex`, generated by `tools/pilot_analyze.py` and `tools/pilot_trace_tex.py` from `evidence/M4/M4.T11/`.
- Pages rendered and inspected: Fig. 1, Table II, Fig. 2, Table III, Table IV with Fig. 3, and Table V.

AI-assisted: Claude Opus 5.5 via Cursor ran the review (subagents), verified the findings and applied the fixes.
