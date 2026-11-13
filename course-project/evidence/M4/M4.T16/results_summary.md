# M4.T16 (reduced; work list 1.8): results of the main simulated study

The pre-registered analysis of the held-out replay sweep (`evidence/M4/M4.T1/prereg.md`, frozen at 0f2f88e), run on
2026-11-13. This page is the hand-off to the report (M5.T14) and the slides. Every number below is copied from
`analysis_stdout.txt` / `study_summary.json` (the frozen analysis), `judge_summary.txt` (the note rubric) or
`error_sources.txt` (a post-hoc check), and is rounded here only for reading.

**Status: confirmatory.** `study_analyze.py --prereg` found no provenance problem (`"status_reasons": []`): the arms,
seeds and observation-log hashes match `prereg.json`; every row and run header carries its arm's frozen
configuration tag; every launch was from a clean tree; and B1 is the calibrated online estimate. `prereg_freeze.py
--verify` passed before the analysis (`prereg_verify.txt`: all 29 files and 30 logs match; environment OK). A second
run of the analysis wrote byte-identical outputs.

## What was run

| Arm | Run (CST) | Steps | Fallbacks | Repaired reports | Infrastructure events | Spend |
| --- | --- | --- | --- | --- | --- | --- |
| Opus 5.5 (`claude-opus-5-5`, config b003c274bbb8) | 2026-11-10 02:06–03:35 | 1,976 / 1,976 | 1 (no parse) | 0 | none | US$143.97 (cap 250) |
| Gemma 4 (`gemma4-26b`, 9cad251b7f18) | 2026-11-10 02:06 – 11-12 14:50 | 1,976 / 1,976 | 78 (70 no parse, 8 output cap) | 0 | 79 client timeouts (3,600 s) in 66 steps: 77 retried, and the third timeout of seeds 2008 and 2021 at step 0 stopped those seeds, which the one pre-registered resume completed (`run.resume-20261112T120146.json`) | US$0 (GPU) |
| Qwen3.8 (`qwen38-flash-xhigh`, 488f835d69b5) | 2026-11-12 14:54 – 11-13 08:07 | 1,976 / 1,976 | 12 (5 no parse, 4 pose not numeric, 3 map malformed) | 97 | none | US$0 (GPU) |

All runs were launched from commit 61ca2c7 with a clean tree. No step is missing for any arm (`"missing_steps": {}`),
so no step was padded as a fallback, and the sensitivity analysis (H1 without unfinished seeds) is empty: it is H1
itself. The pre-registration classes the timeouts as infrastructure events (§3): a timed-out request was sent again,
and no step was written until a reply came back, so none of them is scored. See the note at analysis time below:
for Gemma 4 a timeout was probably a long generation, so its retries favour it. Judge: 900 notes, 0 errors,
US$6.27 (cap 25).

## Primary endpoint: ATE-RMSE per seed (cm; 30 seeds, report precision)

| | B0 dead reckoning | B1 factor graph | B2 coded procedure | Opus 5.5 | Qwen3.8 | Gemma 4 |
| --- | --- | --- | --- | --- | --- | --- |
| Median | 16.74 | 1.23 | 11.68 | 12.06 | 11.92 | 69.33 |
| Mean [bootstrap 95 %] | 16.2 [14.2, 18.1] | 1.34 [1.21, 1.49] | 13.1 [11.0, 15.4] | 13.1 [11.0, 15.4] | 12.0 [10.5, 13.5] | 80.6 [66.6, 96.6] |
| Range | 4.8–26.6 | 0.7–2.4 | 4.6–31.3 | 4.6–31.3 | 4.6–22.0 | 13.4–227.1 |

Figures: `report/figures/fig_study.{pdf,png}` (the frozen analysis's figure, linear axis);
`fig_study_log.{pdf,png}` (the same strips on a log axis) and `fig_study_h1.{pdf,png}` (H1's paired differences
with the estimates and intervals), both drawn by `make_figures.py` from this folder's outputs.

## Family 1 (primary): H1, does the arm track better than dead reckoning?

Holm over the three arms at α = 0.05. "Practical" needs the interval's upper end below −3 cm.

| Arm | Test | Estimate of ATE(arm) − ATE(B0) [exact 95 %] | Seeds better / worse / tied | p | Holm p | Outcome |
| --- | --- | --- | --- | --- | --- | --- |
| Opus 5.5 | signed-rank (G1 −0.27) | HL **−2.83 cm** [−4.93, −0.75] | 21 / 6 / 3 | 0.0012 | **0.0025** | **rejected**; not practical (upper end −0.75 cm) |
| Qwen3.8 | signed-rank (G1 −0.44) | HL **−4.00 cm** [−6.06, −1.85] | 23 / 5 / 2 | 2.4 × 10⁻⁵ | **7.2 × 10⁻⁵** | **rejected**; not practical (upper end −1.85 cm) |
| Gemma 4 | sign test (G1 1.36 > 1) | median **+56.7 cm** [+38.2, +79.2] | 1 / 29 / 0 | ≈ 1.00 | ≈ 1.00 | **not rejected**: worse than dead reckoning on 29 of 30 seeds |

Means with bootstrap intervals (descriptive): Opus −3.04 cm [−4.90, −1.23], Qwen3.8 −4.15 cm [−5.95, −2.47],
Gemma 4 +64.4 cm [+50.1, +80.8]. Rank-biserial: −0.65, −0.81, +1.00; Cohen's d_z: −0.58, −0.84, +1.46. The
frozen code computes the Hodges–Lehmann estimates and intervals over all 30 differences, tied seeds included, while
the tests drop the ties (Wilcoxon's rule).

**Reading.** Opus 5.5 and Qwen3.8 track the car better than dead reckoning, by about 3–4 cm in ATE (a sixth to a
quarter of B0's 16.7 cm median). That is statistically supported but not practically: each interval reaches above
−3 cm, as the power analysis predicted (P(practical support) was 0.009–0.033 in every scenario). Gemma 4 is far worse
than dead reckoning.

## Family 2 (secondary): H2, within twice the factor graph's error? Not tested

The serial gate opens family 2 only if every H1 is rejected. Gemma 4's H1 was not, so H2 is **not tested** for any
arm and none is rejected (the pre-registered rule; not a choice made after seeing the data). Descriptively it would
have failed for every arm. On every seed, every arm's ATE is more than twice B1's: 30 of 30 values of
log(ATE/ATE_B1) − log 2 are positive. The HL estimates, converted to ATE/ATE_B1, are 8.9 [7.5, 11.1] (Opus), 8.6
[7.3, 10.1] (Qwen3.8) and 57 [43, 71] (Gemma 4). The pre-registration expected this (§5: for an arm that reproduces the procedure,
log(ATE/ATE_B1) − log 2 had median 1.62 on 99 dev seeds, a ratio of about 10, and was never below 0).

## H4 (secondary, own family): do the three models differ?

Friedman χ² = 51.9, p = 5.4 × 10⁻¹², Kendall's W = **0.865**. Mean ranks: Qwen3.8 1.42, Opus 1.58, Gemma 4 3.00.
The pairs are therefore interpreted (two-sided exact signed-rank, Holm):

| Pair (first − second) | HL [95 %] | Mean | Seeds used (non-tied) | Holm p |
| --- | --- | --- | --- | --- |
| Opus − Qwen3.8 | +0.05 cm [0.00, +0.30] | +1.11 cm | 15 | 0.022 |
| Opus − Gemma 4 | −64.0 cm [−79.3, −49.9] | −67.5 cm | 30 | 5.6 × 10⁻⁹ |
| Qwen3.8 − Gemma 4 | −65.0 cm [−80.3, −51.1] | −68.6 cm | 30 | 5.6 × 10⁻⁹ |

Opus and Qwen3.8 have the same ATE on 15 of the 30 seeds. Of the other 15, Qwen3.8 is lower on 10 and Opus on 5;
a sign test on that split would give p ≈ 0.30. The signed-rank result (Holm p 0.022) comes from the sizes: Opus's
five lower seeds are all within 0.45 cm, while Qwen3.8 has the three largest differences (2012: 18.0 cm, 2014:
6.9 cm, 2017: 6.4 cm), which also carry the 1.1 cm mean. The frozen Hodges–Lehmann estimate uses all 30
differences, including the 15 zeros, so its interval [0.00, +0.30] touches 0 while the test, which drops the zeros,
rejects. Read it as: Qwen3.8 was lower on a few seeds by a few centimetres and otherwise tied with Opus. With K = 1
(one run per seed and arm), H4 compares single runs, so run-to-run variation inside an arm is part of these
differences. Both are far better than Gemma 4.

## Descriptive: fidelity to the procedure, maps, reports, cost

**L2 − B2** (the report's "what would change my mind", which prereg §5 lists as descriptive: an arm whose ATE is
within 1 cm of B2's on every seed adds no estimation value beyond the code it executes; computed from
`study_per_seed.csv`):

| Arm | Seeds within 1 cm of B2 | Identical to B2 | Median L2 − B2 | Seeds more than 1 cm from B2 (L2 − B2) |
| --- | --- | --- | --- | --- |
| Opus 5.5 | 28 / 30 | 9 | 0.00 cm | 2027 (−3.2), 2029 (+1.2) |
| Qwen3.8 | 26 / 30 | 6 | −0.01 cm | 2012 (−18.0), 2014 (−6.9), 2017 (−6.4), 2027 (−3.2) |
| Gemma 4 | 0 / 30 | 0 | +61.4 cm | all 30 |

So the criterion is not met in its strict "every seed" form for either strong arm, but nearly so. Both reproduce
the coded procedure's estimate on most seeds. For Opus the gain over dead reckoning is, in effect, the procedure's
own: the same paired estimate for B2 − B0 (computed here with the frozen `metrics/stats.py`, descriptive) is HL −2.74
cm [−4.87, −0.75], B2 better on 20 seeds, worse on 6 and tied on 4, against Opus's −2.83. Qwen3.8's −4.00 is about
1.3 cm more. That margin comes from its four departures from the procedure, all of which lowered the error. This is
the kind of added estimation value the criterion asks about, but it rests on four seeds of a single run each (K = 1)
and is descriptive. On seed 2027 both arms departed identically. At step 66 they accepted two revisits (B9, B5) as
loop closures, which the gate tool reported in gate and B2's procedure rejected, and the fix lowered their ATE by
3.2 cm. Whether B2's rejection follows the prompt's loop-closure rule was not checked. Opus and Qwen3.8 each had 841
steps with a successful `fix_pose`; Gemma 4 had 246 (`error_sources.txt`).

| Metric (per seed: median, or total over 30 seeds) | Opus 5.5 | Qwen3.8 | Gemma 4 | B2 |
| --- | --- | --- | --- | --- |
| Final position error (median) | 12.4 cm | 10.9 cm | 110.0 cm | 12.7 cm |
| Heading RMSE (median) | 13.9° | 13.9° | 12.2° | 14.2° |
| Pose score max(0, 1 − ATE/0.25 m) (median) | 0.518 | 0.523 | 0.000 | 0.533 |
| Worst seed (ATE) | 2012 (31.3 cm) | 2000 (22.0 cm) | 2018 (227.1 cm) | 2012 (31.3 cm) |
| Valid-report rate (median) | 1.000 | 1.000 | 0.959 | — |
| Map precision / recall (median) | 0.917 / 0.875 | 0.923 / 0.917 | 0.647 / 0.833 | 0.875 / 0.875 |
| Map RMSE over correct entries (median) | 14.7 cm | 14.7 cm | 11.2 cm | 14.5 cm |
| Phantom map entries (total) | 39 | 36 | 195 | 43 |
| Association precision, duplicated IDs (median) | 1.000 | 1.000 | 0.919 | 1.000 |
| Tool-call F1 against the procedure (median) | 0.964 | 0.901 | 0.528 | — |
| Pose-source agreement with the procedure (median) | 1.000 | 1.000 | 0.532 | — |
| Unverified fix claims (total) | 0 | 2 | 141 | — |
| Pose / map state-violation rate (mean) | 0 / 0 | 0.05 % / 0.11 % | 2.7 % / 2.2 % | — |
| Move calls, refused in replay (total) | 37 (and 6 `emergency_stop`) | 12 | 133 | — |
| Tool-error results (total) | 140 | 862 | 448 | — |
| Tool calls per step (median) | 3.74 | 4.13 | 1.78 | — |
| Output tokens per step (median) | 2,401 | 3,146 | 8,606 | — |
| Step latency, pooled p50 / p95 (8 or 16 seeds at once) | 19.6 / 25.5 s | 218 / 426 s | 1,097 / 2,030 s | — |
| US$ per seed (median) | 4.76 | 0 | 0 | — |

Latency was measured with 8 seeds sharing a server (16 for Gemma 4), so it is not the closed-loop latency. B1, the
factor graph, has a median final error of 1.4 cm, heading RMSE of 1.2° and pose score of 0.951. Gemma 4's lower map
RMSE is over correct entries only (a tag of the right ID within 0.30 m), so it is measured on its smaller set of
correct entries. Qwen3.8's 862 tool errors are mostly `fix_pose` called with an empty match list (538), which is a
call that should not have been made, and `gate_detection` given map-entry objects where the tool expects labels (285
of its 287 "not a label" errors). The tool refused them and nothing changed.

## Note rubric (descriptive; GPT-6.1 Sol, 10 notes per seed and arm, `judge_summary.txt`)

| Arm | Rubric (mean of seed means) [95 %] | Faithful / coverage / uncertainty / concise (0–2) | Failed the faithfulness gate | Steps with a judgeable note |
| --- | --- | --- | --- | --- |
| Opus 5.5 | 0.955 [0.935, 0.971] | 1.96 / 1.98 / 1.92 / 1.66 | 5 / 300 | 99.9 % |
| Qwen3.8 | 0.935 [0.916, 0.951] | 1.94 / 1.95 / 1.76 / 1.88 | 5 / 300 | 99.3 % |
| Gemma 4 | 0.407 [0.359, 0.455] | 1.10 / 1.61 / 0.48 / 1.89 | 131 / 300 | 96.1 % |

The sample is drawn only from valid reports with a note, so an arm's invalid steps are never judged. That can only
flatter the arm with the most invalid reports (Gemma 4, 3.9 % of its steps excluded). The last column gives each
arm's share, as pre-registered.

## Post-hoc check: why Gemma 4 is worse than dead reckoning (exploratory)

The plan asks for a bug check when a result is surprising enough to make a bug plausible. `error_sources.py` was
run after the analysis and reads the run logs only. It finds the cause mostly in the model's behaviour:
- **Not a parsing artefact.** The check uses its own JSON decoder, not the harness's parser, which produced the
  scored pose. Each of Gemma 4's 1,898 valid final texts is a bare JSON object (466) or exactly one fenced JSON block
  (1,432). The pose of its one top-level object equals the scored pose on all 1,898; a missing or non-finite value
  would count as a mismatch. The same holds for all 1,975 of Opus's. For Qwen3.8 it holds for 1,868; the other 96
  are reports repaired by the pre-registered closing-character rule, which a strict decoder cannot read.
- **The error builds up on steps without tools.** Gemma 4 answered without calling any tool on 1,060 steps: 53.6 % of
  all its steps, or 55.8 % of its valid reports. On those steps its position error grew by 2.47 cm per step, against
  at most 0.42 cm per step for any kind of step of Opus or Qwen3.8. The per-step changes add up to each seed's final
  position error (not its ATE). Of Gemma 4's 31.98 m, summed over the 30 seeds, 26.21 m grew on steps without tools,
  4.59 m on steps with tools but no successful `fix_pose`, 0.65 m on steps with one and 0.53 m on fallbacks. Opus
  called a tool on every valid step. Qwen3.8 skipped tools on 36 valid steps (1.8 %), plus 4 fallbacks, one of which
  was a tool call written as plain text (seed 2027, step 27).
- **Invented pose changes.** On 215 steps, Gemma 4's reported position moved more than 5 cm from the harness prior
  (its previous report dead-reckoned) without a successful `fix_pose` (Qwen3.8: 2; Opus: 0). It also claimed 141 full
  fixes that the step's own `fix_pose` results did not support (`unverified_fix_claims`).
- **Tool misuse when it did use tools.** Its most frequent tool errors: `compose_odometry` with an empty pose (131),
  `fix_pose` with an empty match list (85), and `fix_pose` naming a beacon that was not a confirmed, non-suspect map
  entry (52 + 19 for "b" labels). Empty object arguments (`{}`) occur only in Gemma 4's calls (151; none for the
  other arms). The raw tool-call text is not logged, so a vLLM gemma4 tool-parser artefact is not ruled out for
  these. It cannot explain the tool-free steps: none of their final texts contains tool-call markup.

## Deviations and notes at analysis time

- **No deviation from the pre-registered analysis.** The frozen `study_analyze.py` ran unchanged with the
  pre-registered command line.
- **Done after the analysis, outside the frozen files and labelled as such:** `error_sources.py` (above),
  `judge_summary.py` (the rubric table; the frozen files define the judge run but not a summary of it) and
  `make_figures.py` (two presentation figures, no new statistics).
- **Gemma 4's timeouts were probably long generations.** Its median decoding rate was 7.2 tokens/s per turn (p90
  10.3), so the 32,768-token output cap takes about 76 minutes to reach, longer than the 60-minute client timeout. The
  premise of deviation 12 (prereg §8), that a runaway generation ends as a counted fallback instead of a timeout,
  therefore did not hold for Gemma 4. All 8 of its output-cap fallbacks came from turns that decoded at 10.7
  tokens/s or faster. Under §3 a timeout is an infrastructure event, so these steps were re-asked and the new answer
  was scored. That is no deviation, but each retry is a fresh draw, which can only help Gemma 4, so its 78
  fallbacks are a lower bound. Its H1 and H4 outcomes would not change.
- **Fonts.** The frozen figure `fig_study.pdf`, like `fig_pilot.pdf`, embeds Type 3 fonts (matplotlib's default),
  which M5.T14's `pdffonts` check rejects. `fig_study_log.pdf` and `fig_study_h1.pdf` use TrueType. The report
  should use them, or a TrueType redraw of `fig_study` (same data).
- **Steps of the unreduced M4.T16 not run** (they belong to the full benchmark that the re-scope of 2026-11-09
  replaced): the evo cross-check, `make_report_assets.py` and its LaTeX tables, `check_holdout.py` and the ledger
  report. The held-out guard they served is covered by the freeze: `prereg_freeze.py --verify` confirms the 30
  observation logs and every frozen file; each run's configuration tag and clean-tree launch is checked by the
  analysis; and no LLM ran on seeds 2000–2029 before the freeze (prereg.md §2, §7).
- **Servers after the sweep.** The Gemma 4 vLLM container stopped when its arm finished (2026-11-12). `bm-qwen38`
  was stopped on 2026-11-13 after the analysis (`bash course-project/tools/serve_qwen38.sh start` restarts it).
- **Data.** The run logs, judge output, B1 output and observation logs stay in `course-project/data/main/`
  (git-ignored, about 185 MB) on the Spark, with a copy on the Mac made on 2026-11-13. The judge's items and scores are
  also kept in `judge/` here (under 1 MB).

## Files

| File | What it is |
| --- | --- |
| `analysis_stdout.txt` | The frozen analysis's printout, exactly |
| `study_summary.json`, `study_per_seed.csv` | Its full output: every test, metric and per-seed value |
| `prereg_verify.txt` | `prereg_freeze.py --verify`, run before the analysis |
| `judge/` | `items.jsonl` (the sampled notes), `sol.jsonl` (the judge's levels, reasons, cost), `availability.json`, `judge_stdout.txt` |
| `judge_summary.py`, `judge_summary.txt` | The rubric summary |
| `error_sources.py`, `error_sources.txt` | The post-hoc check on Gemma 4 |
| `make_figures.py` | Draws `report/figures/fig_study_log.*` and `fig_study_h1.*` |

Commands (repository root): the analysis and the verify as in `tools/study_analyze.py`'s header and
`tools/prereg_freeze.py --verify` (Spark host venv); then `python3 course-project/evidence/M4/M4.T16/judge_summary.py
course-project/data/main/judge/drift2`, `python3 course-project/evidence/M4/M4.T16/error_sources.py
course-project/data/main/runs/drift2` (both stdlib; their outputs are identical on the Mac and the Spark), and
`python3 course-project/evidence/M4/M4.T16/make_figures.py` (run on the Mac, matplotlib 3.10.6; the strips use
seeded random jitter, so the figures are the same on every run).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-13: ran the judge, the verify and the frozen analysis; wrote the
three post-hoc scripts; wrote this summary. An independent adversarial review (a separate Claude Opus 5.5 agent, the
same day) checked every number against the source files and found no wrong statistic. It found 11 wording,
interpretation and post-hoc-script problems, among them the rubric-sample direction, the circular parse check, the
Gemma 4 timeouts and the Opus − Qwen3.8 reading. All were verified against the logs and fixed here and in the
scripts. The pre-registered design is in `evidence/M4/M4.T1/`.
