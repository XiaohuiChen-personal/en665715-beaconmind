# Pre-registration of the main simulated study (M4.T1, reduced; plan/README.md §3.6 work list 1.5)

Written 2026-11-10, before any held-out run of any LLM arm and before any metric was computed on the held-out seeds.
`prereg.json`, written by `tools/prereg_freeze.py` on the Spark from a clean checkout, holds the SHA-256 of every
frozen file (this document, the freeze tool, the power script and its output, the prompt, the design values, the
providers file, every harness, baseline, metric, statistics and analysis source), of every held-out observation log,
the model servers' identities, the package versions, and each LLM arm's configuration tag.
`prereg_freeze.py --verify` must print OK before the sweep and again before the analysis.

The study carries out the plan in the report's Section IV ("Experiments", written 2026-10-29 before any held-out data
existed), with the deviations in §8. The decisions in §§1–7 were taken by Claude Opus 5.5 under Xiaohui Chen's
delegation of 2026-11-10 ("evaluate each option … and choose the option that has the best quality"); the roster and
the scope are Xiaohui's (2026-11-09). Three independent adversarial reviews (harness, B1, this analysis plan) preceded
the freeze; their findings and fixes are in `evidence/M2/M2.T7/REVIEW.md`, `evidence/M2/M2.T9/REVIEW.md` and
`REVIEW.md` in this folder.

## 1. Questions

RQ1 (primary, estimation): replayed on held-out simulated logs with duplicated tag IDs and a 2 % systematic odometry
over-read, does an LLM agent that keeps its own pose and map through the nine D5 tools track the car better than dead
reckoning (H1), and is it within twice a factor-graph reference's error (H2)? RQ2 (secondary, descriptive):
association, map and fidelity to the procedure. RQ4 (secondary, new): do the three models differ (H4)?

## 2. Data

- **Simulator:** `envs/kinsim_lite.py` with the plan's placeholder noise model (60° field of view, 0.25–1.5 m,
  incidence ≤ 60°, p_detect 0.95, range SD 0.01 + 0.03 r m, bearing SD 1.0°, wheel scale SD 2 %, gyro SD 0.3° per
  turn) and a **2 % systematic over-read** of forward distance and turn angle. Worlds: 12–16 tags on the walls of a
  2.25 m square, three IDs used twice with the copies ≥ 1.5 m apart.
- **Seeds:** the held-out block **2000–2029 (n = 30)**. Rule fixed in advance: a seed whose B2 episode reaches an
  unimplemented branch is replaced by the next unused seed from 2030 upward. Recorded on 2026-11-10 (seeds 2000–2034,
  `data/main/obslogs/test/drift2/record.log`): no seed failed, so none is replaced. 1,976 steps in all (episodes of
  51–104 steps, each ending at B2's DONE). Nothing but the recorder's summary line (steps, tags, duplicated IDs, last
  decision) and the episode lengths (for the spend estimate) was looked at.

## 3. Arms

| Arm | Definition |
| --- | --- |
| B0 | Dead reckoning: the logged odometry composed from the start pose, **rounded to report precision at every step** (as an arm that only dead-reckons through its own reports would be, so such an arm ties B0) |
| B1 | GTSAM 4.3.0 iSAM2 over the same odometry and detections with **oracle association** and **online odometry-scale calibration** (forward and turn scale variables, prior N(1, 0.05); the bias itself is not given); the simulator's sigmas plus the logs' rounding; **the online (causal) estimate** of each step, rounded to report precision (`baselines/b1_gtsam.py`; `evidence/M2/M2.T9/REVIEW.md`) |
| B2 | The coded procedure (AGENT-DESIGN D7), which also chose the moves of every log |
| L2: `claude-opus-5-5` | Anthropic Messages, adaptive thinking, effort medium, max_tokens 64,000, prompt caching (the 2026-10-29 pilot's settings) |
| L2: `qwen38-flash-xhigh` | `nvidia/Qwen3.8-Flash-Next-NVFP4` on vLLM (`tools/serve_qwen38.sh`, the M1.T15 server), thinking on at the template's default effort `xhigh` (the model card's benchmark setting), temperature 1.0, top_p 0.95, top_k 20 (the checkpoint's generation config), max_tokens 32,768, a per-request sampling seed |
| L2: `gemma4-26b` | `gemma4:26b-a4b-it-bf16` on a user-level Ollama 0.40.11 with 8 slots (`tools/serve_gemma4.sh`; the same model files as the host's Ollama), thinking on (Ollama's default for this model), the Modelfile's sampling (temperature 1, top_k 64, top_p 0.95), max_tokens 32,768, a per-request sampling seed |

Every LLM arm gets the byte-identical system prompt (`prompts/robot_system_prompt_v3.3.txt`), step message and nine
tools, at most 30 turns per step, one stateless call per observation, replay mode (moves are refused). Reasoning is
sent back inside a step's tool loop (Anthropic thinking blocks; the `reasoning` field for the local servers, checked
by rendering on the live vLLM server). **Repeats: K = 1.** Seeds run 8 at a time, in an order shuffled with seed
20261110. The Opus arm's spend cap is **US$250** (expected about US$150–160: the pilot's mean cost per step was
US$0.070–0.079 in every 20-step band, p90 about US$0.092; 1,976 steps). If the cap binds, the run stops, the cause is
checked, and the remaining steps are run after a recorded increase; the cap is a guard against runaway spend, not a
design element.

**Harness rules** (`harness/replay.py`): the counters `travel_since_fix_m` and `turns_since_fix` reset only on a
claimed full fix that one of the step's own `fix_pose` results supports, given the harness's own prior (`verify_fix`);
the reported pose and map are scored **as the agent wrote them** (never replaced by tool values), and their
disagreements with the tools are measured (`state_violations`, plan C5.4's rule); a report that does not parse, or
has a non-finite or non-numeric pose or a malformed map, is replaced by the previous report dead-reckoned through the
step's odometry (`fallback`, counted). A report whose text stops one to three closing characters short (an open
string's quote and closing brackets, nothing else) is completed and counted as `repaired` (`tools_d5.parse_report_ex`,
the same rule for every arm). Model failures inside a step — the output cap, the 30-turn cap, a context
overflow, an unexpected finish reason — end the step as such a fallback. Infrastructure failures — a server that
still fails after 7 attempts (3 for a client timeout of 3,600 s), a malformed request — stop the seed without writing
the step.

**Missing data.** A seed stopped by an infrastructure failure is resumed (each resume records its reason in
`run.resume-*.json`, and a resume under any other configuration is refused); a seed that stops a second time for an
infrastructure failure is not run again, and its remaining steps are scored as invalid-report fallbacks (the arm's
last report dead-reckoned forward), counted and listed. Every arm therefore keeps all 30 pairs. Sensitivity analysis:
H1 without the seeds an arm did not finish (descriptive).

## 4. Metrics (report Section IV-C; `tools/study_analyze.py`, `metrics/pilot.py`, `metrics/stats.py`)

- **Primary endpoint:** unaligned ATE-RMSE over all steps of the episode, in the start-pose frame, per seed, every arm
  at report precision (2-dp positions, 1-dp headings).
- Secondary: final position error, heading RMSE, pose score max(0, 1 − ATE/0.25 m); map RMSE over correct entries, ID
  precision and recall (correct = a tag with that ID within 0.30 m); association precision and recall (all detections,
  and duplicated IDs only; target precision 0.90); tool-call precision, recall and F1 against the procedure's calls on
  the same input (0.011 m, 0.11°); pose-source and association agreement with the procedure; pose and map
  state-violation rates; valid-report rate, fallbacks, unverified fix claims, tool-error results; latency (per-seed
  median and 95th percentile, and pooled over all steps of an arm; at 8 concurrent seeds, so not the closed-loop
  gate), tokens, US$. Each with n, mean and median with 10,000-resample bootstrap intervals (seed 12345), range and
  the worst seed.
- **Note rubric** (descriptive): GPT-6.1 Sol (selected in the pilot under its fixed rule), evidence version 2, on 10
  random valid-report steps per seed and arm (`tools/study_judge.py`, seed 777, cap US$25), reported with each arm's
  share of steps that have a judgeable note.

## 5. Hypotheses and tests

| Family | ID | H0 | H1 (one-sided) | On the 30 per-seed values |
| --- | --- | --- | --- | --- |
| 1 (primary) | H1[arm], arm ∈ {Opus, Qwen3.8, Gemma 4} | median(ATE_arm − ATE_B0) ≥ 0 | < 0 | the test below |
| 2 (secondary) | H2[arm] | median(log(ATE_arm / ATE_B1) − log 2) ≥ 0 | < 0 | the test below |

- **Multiplicity: serial gatekeeping at family-wise α = 0.05.** Family 1 is tested with Holm's step-down procedure at
  α; family 2 is tested, with Holm at α, only if every hypothesis of family 1 is rejected; otherwise family 2 is
  reported as not tested. A hypothesis is rejected when its Holm-adjusted p-value is ≤ α. **The families are fixed:**
  a test that is not run (an arm or B1 missing for any reason, including the plan's "if time runs short" cuts)
  counts as p = 1 inside its family.
- **Test:** the exact one-sided Wilcoxon signed-rank test, with zero differences dropped (Wilcoxon's rule) and the
  p-value from the exact permutation distribution of the positive-rank sum over doubled midranks (exact with ties;
  `metrics/stats.py`). If the adjusted skewness G1 (`scipy.stats.skew`, `bias=False`) of all 30 values, zeros
  included, exceeds 1 in absolute value, the exact one-sided sign test (zeros dropped) replaces it for that hypothesis.
  The switch applies to families 1 and 2 only.
- **Estimand and interval:** the Hodges–Lehmann estimate (the median of the Walsh averages, the signed-rank test's
  estimand) with its exact 95 % interval from the Walsh-average order statistics; under the sign test, the sample
  median with its exact order-statistic interval. Also reported: mean with bootstrap interval, rank-biserial
  correlation (Kerby 2014), Cohen's d_z, the number of seeds with a negative and with a positive difference.
- **Practical reading of H1:** supported in practice only if H1 is rejected **and** the interval's upper end is below
  −3 cm (the report's smallest difference that matters). A rejected H1 inside that band is reported as statistically
  but not practically supported.
- **H4 (secondary, own family):** the Friedman test over the three LLM arms' ATE with Kendall's W; then the three
  pairwise two-sided exact signed-rank tests with Holm (Hodges–Lehmann estimates and intervals), interpreted only if
  the Friedman test is significant at 0.05.
- **Descriptive only:** every other metric; L2 − B2 per arm (the report's "what would change my mind": an arm whose
  ATE is within 1 cm of B2's on every seed adds no estimation value beyond the code it executes).
- **Power** (`tools/prereg_power.py`, output `power.txt`; n = 30, exact test as above, 4,000 simulations). For an
  arm's H1, Holm puts its level between α/3 and α.

  | Scenario for an arm's per-seed differences | P(reject at α/3) | P(reject at α) | P(practical support) |
  | --- | --- | --- | --- |
  | pilot effect, Normal(−2.70 cm, 3.11 cm) (Opus, 5 dev seeds) | 0.993 | 0.999 | 0.009 |
  | pilot mean, SD at its 95 % upper bound (8.94 cm) | 0.283 | 0.461 | 0.021 |
  | the 3 cm threshold, Normal(−3.00 cm, 3.11 cm) | 0.999 | 1.000 | 0.033 |
  | an arm that reproduces the procedure (B2 − B0 resampled from 99 dev seeds: mean −3.04 cm, SD 4.73 cm) | 0.883 | 0.956 | 0.025 |

  So H1 is well powered at the effects seen so far, but practical support (an interval wholly below −3 cm) needs a
  true effect of about −5 cm and is unlikely. H2 is expected to fail: for an arm that reproduces the procedure,
  log(ATE/ATE_B1) − log 2 had median 1.62 (range 0.45–2.68) over 99 dev seeds, never below 0. That is why H2 is behind
  the gate: it cannot cost H1 power.

## 6. What is not tested here

H3 (closed-loop navigation success, report Section IV-A) is not tested: there is no closed-loop sweep in the re-scoped
plan; the demo's closed-loop episodes are reported descriptively. The no-drift block and the unique-ID condition are
not run. The real-car logs (plan §3.6 work list 3.4) are replayed through the same three arms later and reported as
the sim-to-real gap, descriptively (tape ground truth cannot resolve 3 cm).

## 7. Development data, and what it was used for

- The 2026-10-29 pilot (Opus on dev seeds 1000–1004, both drift levels): the effect size and SD in §5's power table.
- Gate runs of 2026-11-10 on dev seeds 1010–1017 at 2 % drift (Qwen3.8 xhigh; Gemma 4), full episodes, 8 at a time
  (`data/main/gate/`; `evidence/M4/M4.T2/`). Used for: checking that each arm completes episodes with valid reports;
  the output cap of the local arms (the largest Qwen turn was 2,347 tokens, median 441); the 8 parallel seeds (vLLM's
  aggregate generation was about 125 tokens/s at 8 requests, 60–80 at 4); K = 1 (about 160 Qwen steps an hour). No
  prompt, tool, threshold, metric or test was changed after looking at any LLM output in them.
- B0, B1, B2 on dev seeds: B1's design (the scale calibration, after the B1 review) and §5's power rows.

## 8. Deviations from the report's plan of 2026-10-29, with reasons

1. **Three LLM arms instead of one** (Xiaohui's roster, 2026-11-09). H1 and H2 are tested per arm.
2. **K = 1 for every arm** (the report planned K = 3 for local arms): the Qwen3.8 arm alone needs about 13–15
   GPU-hours for one repeat of 30 seeds, and the project must finish by 2026-11-25. The seed is the unit either way.
3. **One condition:** the no-drift block (the pilot showed no headroom over dead reckoning there) and the unique-ID
   condition are not run.
4. **Placeholder noise model:** the report said the camera's measured noise would replace it before the confirmatory
   runs; the measured model needs the real-camera work of plan §3.6 section 2, which comes later. Every arm sees the
   same logs, and the real-log replay measures the gap.
5. **No Isaac Sim subset** (the twin is dropped, plan §3.6).
6. **H3 not tested** (no closed-loop sweep).
7. **One judge on a sample:** the report ran both judges on every note; here only the pilot's selected judge (Sol) on
   10 notes per seed and arm (the rubric is descriptive).
8. **Harness change since the pilot:** the counters reset only on verified fixes.
9. **Sample size 30** as the report planned (the user's earlier cost estimate assumed 20 seeds).
10. **B1:** the report calls B1 "offline … (upper bound)"; here B1 runs after the episode on the recorded log, but
    the scored trajectory is its online (causal) estimate (the smoothed one is kept as secondary data), and it
    calibrates the odometry scale (without that it is not an upper bound under drift).
11. **No state correction, no early stop:** AGENT-DESIGN D5 and plan C5.4 say the harness replaces a reported value
    that disagrees with the tools; here poses and maps are scored as written and the violations are reported (D5 v3.4
    note). Plan C9.2's stop after three consecutive policy errors is not applied: every step is scored.
12. **Output caps:** D10 says no output cap below the server window for self-hosted models; the local arms get 32,768
    tokens per turn (14 times the largest gate turn) so that a runaway generation ends as a counted fallback instead
    of a timeout; Opus keeps the pilot's 64,000.
13. **Eight seeds in parallel** (the report said five), for vLLM's throughput. Latency is measured under load.
14. **Multiplicity:** the report said Holm over H1–H3 at 0.05 and called H2 secondary; here H1 (three tests) is the
    primary family and H2 is behind a serial gate (§5), so a secondary hypothesis expected to fail cannot reduce the
    primary family's power.
15. **Effect estimate:** the report promised "the median difference with its interval"; here the Hodges–Lehmann
    estimate (the signed-rank test's own estimand, a median of Walsh averages) with its exact interval, and the plain
    median with its exact interval under the sign test; the mean with a bootstrap interval is descriptive.
16. **Missing data:** the report said a seed that still fails is "scored as incomplete"; here its remaining steps are
    scored as invalid-report fallbacks (§3), so every pair is kept, with a sensitivity analysis.
17. **Retries:** the report said an API call is attempted up to seven times; here 7 for connection errors and HTTP
    408/409/429/5xx, 3 for a client timeout (a stalled server; vLLM cancels the request), none for a malformed request.
18. **H4 is new** (RQ4), with its own family.
19. **B0 is rounded at every step** (report precision), so a pure dead-reckoning arm ties it exactly; the pilot
    rounded nothing in B0.
20. **Latency:** besides the per-seed 95th percentiles, a 95th percentile pooled over all of an arm's steps.
21. **Closing-character repair** (new; the pilot's parser had none): in the Qwen3.8 gate, 9 of about 110 reports did
    not parse; 6 of them were complete except for the final `}` or `"}` (the server's own short answers came back
    whole, so the cause, model or server, is not known; each turn now logs vLLM's stop reason and the content's last
    characters). Counting those as invalid would score punctuation, not estimation. The rule completes at most three
    closing characters, applies to every arm, and the count of repaired reports is reported per arm.

## 9. Freeze

The frozen commit, every hash and each arm's configuration tag are in `prereg.json` (written by
`tools/prereg_freeze.py` on the Spark host from a clean checkout of the commit that holds this file). The held-out
runs are launched from a clean tree; each run's configuration tag must equal the frozen one.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: drafted this pre-registration, ran the power analysis and
took the design decisions marked above under Xiaohui Chen's delegation; Xiaohui chose the roster and the scope.
