# M4.T1 pre-registration and analysis — adversarial review and fixes (2026-11-10, before the freeze)

Under review: `prereg.md`, `tools/study_analyze.py`, `tools/study_judge.py`, `tools/prereg_freeze.py` (and, through
them, `metrics/pilot.py`). One independent reviewer (statistics, pre-registration and code lenses), dev data only.
New after the review: `metrics/stats.py` + `tests/test_stats.py`, `tests/test_study_analyze.py`,
`tools/prereg_power.py` + `power.txt`.

| # | Severity | Finding | Verified | Fix |
| --- | --- | --- | --- | --- |
| 1 | critical | The confirmatory family could shrink after the data were seen: plan §3.6's "if time runs short" cuts (drop B1, drop Gemma) were not in the pre-registration, and the analysis built the family from the command line | Confirmed (`--b1` absent skipped H2 silently; arms from `--arms`) | Families fixed in `prereg.md` §5: a test not run counts as p = 1; plan §3.6 says the cuts do not shrink the families after the freeze; `study_analyze.py` takes the arms from `prereg.json`, fills absent tests with p = 1, and labels the output "exploratory" unless arms, seeds, B1, every row's config tag, a clean launch tree and the log hashes match |
| 2 | major | SciPy's `method="exact"` falls back to a normal approximation when any difference is zero (n = 30), and is not exact with tied \|d\| | Confirmed with the reviewer's cases | `metrics/stats.py` `signed_rank_test`: zeros dropped, exact permutation distribution over doubled midranks (exact with ties); tests compare it with SciPy's exact test without ties or zeros (equal to 1e-10) and with brute-force enumeration with ties and zeros |
| 3 | major | Plausible model output crashed the analysis (unhashable beacon labels, mixed det types, a one-element `first_seen_from`, `"matches": 5`) | Confirmed: each reproduced; `IndexError` from `estimate_step` reproduced in a test | `LabelTracker` ignores associations with non-integer det or non-string label; `call_matches` treats any malformed argument as a non-match; `gold_calls` treats any exception as "gold unavailable" (counted); association agreement uses a total, hashable key; `map_scores_c10` skips non-numeric entries. The pilot analysis rerun after these changes reproduces `pilot_summary.json` exactly |
| 4 | major | `describe()` took metric keys from the first seed only, dropping a metric that was None there | Confirmed | Union of keys over seeds, n per metric; test |
| 5 | major | The missing-data rule was an undeclared deviation; a binding Opus cap was undefined; resumes uncontrolled | Confirmed | Declared (deviation 16); cap US$250 against an expected US$150–160 (pilot cost per step by step band), with the rule if it binds; a resume needs `--resume-reason` and is recorded; sensitivity analysis without unfinished seeds |
| 6 | major | The freeze missed files (prereg.md itself, the freeze tool, `pilot_judge.py`, `__init__.py`, the chat template, image and model ids, package versions); `--verify` used the current list and command-line seeds; the analysis checked no run provenance | Confirmed | `prereg_freeze.py` freezes all of them plus the power script and its output, records the environment, precomputes each arm's config tag, refuses a dirty tree, and `--verify` checks exactly the frozen lists and the environment; `study_analyze.py` checks tags, launch cleanliness, log hashes and B1's calibration |
| 7 | major | Estimand mismatch (bootstrap mean vs the report's median difference vs the test's pseudo-median); the practical flag ignored significance | Confirmed | Hodges–Lehmann estimate with its exact interval (median and order-statistic interval under the sign test); practical = rejected and upper end < −3 cm |
| 8 | major | The power statement was overconfident (one scenario, the pilot's 5-seed SD) | Confirmed (reviewer reproduced 0.98 and 0.86) | `tools/prereg_power.py` (committed) with four scenarios, both Holm ends, the practical-support probability, and H2's dev outlook; table in `prereg.md` §5 |
| 9 | minor | Contradictions inside the draft (max_tokens 64,000 vs 32,768; "gate used for nothing else") | Confirmed | Fixed; §7 lists what the gate was used for |
| 10 | minor | Undeclared differences from the report (both judges on every note; B1 "offline"; median interval; H4; retries; pooled latency; worst seed) | Confirmed | Declared as deviations 7, 10, 15, 17, 18, 20; pooled latency and worst seed added |
| 11 | minor | Skew rule under-specified (G1 vs g1, zeros, scope) | Confirmed | Specified: G1 (`bias=False`) of all 30 values including zeros, families 1 and 2 only; H4 pairs always signed-rank, interpreted only if Friedman p < 0.05 |
| 12 | minor | B0 rounded once at the output while a dead-reckoning arm rounds every step: a no-skill arm could pass H1 about 4 % of the time at α/6 | Confirmed (reviewer's simulation) | B0 is the dead-reckoning chain rounded at every step; a test shows an all-padded arm equals B0 exactly (d = 0, dropped by the test) |
| 13 | minor | Judge pool favours arms with fewer invalid reports; a binding cap would cut the last arm | Confirmed | Items interleaved by seed across arms; each arm's share of judgeable steps written to `availability.json` and reported |
| 14 | nit | Holm rejected on `<`; no versions or freeze commit in the summary; torn last line crashed `load_run` | Confirmed | Reject at adjusted p ≤ α; versions and frozen commit recorded; torn last line ignored |

**Design change made from finding 8's evidence:** H2 is expected to fail (dev seeds: log(ATE_B2/ATE_B1) − log 2 median
1.62, never below 0), and under one Holm family it would lower H1's levels to α/6–α/4. The report labels H1 primary and
H2 secondary, so the families are now serial-gated (deviation 14): this follows the report's own labels and costs H2
nothing it could otherwise have won.

**Incident during the fixes:** `pull_evidence.sh` copied the Spark's older `prereg.md` over the newer Mac copy; the
rewrite was restored from the session, and the script now extracts with `--keep-newer-files` (tested: a newer local file
is kept, an older one updated).

## Tests after the fixes

Mac: `PYTHONPATH=src python3 -m pytest -q -p no:cacheprovider` → `106 passed, 3 skipped` (before the container and gtsam
runs below). The final counts are in CONTEXT.md's 2026-11-10 entry.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: verified and fixed the findings (the review itself was an
independent Claude Opus 5.5 subagent).
