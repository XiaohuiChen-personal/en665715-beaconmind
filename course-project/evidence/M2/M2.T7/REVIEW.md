# M2.T7 / M2.T14 (replay harness, providers, CLI) — adversarial review and fixes (2026-11-10)

Code: `harness/replay.py`, `harness/providers/openai_chat.py`, `harness/providers/anthropic_messages.py`,
`harness/anthropic_replay.py` (shim), `harness/tools_d5.py`, `tools/replay_run.py`, `tools/replay_run.sh`,
`configs/providers.json` + schema, `metrics/pilot.py` (`state_violations`), tests `tests/test_replay_harness.py`.

## Checks before the review

- **Reasoning replay rendered on the live server** (vLLM in `bm-qwen38`, `/tokenize` + `/detokenize`): a message
  field `reasoning` renders as `<think>text</think>` in the replayed assistant turn; `reasoning_content` is dropped
  (an empty think block); the Module 4 harness's inline `<think>` in `content` renders after a second, empty think
  block. The provider sends `reasoning`.
- **Gemma 4 through Ollama's `/v1`**: well-formed tool calls with ids, `reasoning` returned (thinking on by default),
  tool messages accepted, prompt caching active (probe 2026-11-09).
- **Live smoke**: Qwen3.8 xhigh 3 steps (all valid, poses equal B2's, 6/9 calls match the procedure), Opus 3 steps
  (US$0.14, 7/7 calls match).

## Review (one independent reviewer; 13 findings) — each verified, then fixed

| # | Severity | Finding | Verified | Fix |
| --- | --- | --- | --- | --- |
| 1 | critical (Gemma) / major | The 1,800 s client timeout is shorter than a 64,000-token generation at the measured decode rates, a timeout was retried 7 times with the same sampling seed (about 3.6 h per turn), so a runaway generation became a failed seed instead of a counted `length` fallback; on the 1-slot system Ollama one runaway would time out every queued seed | Confirmed: gate turns max 2,347 completion tokens (median 441); vLLM aggregate generation ~125 tok/s at 8 requests, 60-80 at 4; system Ollama `n_seq_max = 1` | Local `max_tokens` 32,768 and timeout 3,600 s (the cap is reached first); a timeout is retried 3 times, other connection errors 7, then the error propagates and the step is not written; Gemma runs on a user-level Ollama with 8 slots (`tools/serve_gemma4.sh`); no sleep after the last attempt |
| 2 | major | A resume never checked that it matches the original run | Confirmed | `replay_run.py` hashes the invariant configuration (provider entry, agent settings, repeat, step limit, prompt, design values, providers file, every harness file) into a `config` tag; a resume under another tag, or with a changed observation log, is refused; every row carries the tag and `replay_seed` refuses to append to rows of another tag |
| 3a | major | "Scored as written" contradicts AGENT-DESIGN D5, plan C5.4/C3 ("the tool-derived value is used", `state_violation` logged), and no violation was measured | Confirmed | Decision kept (it measures the agent; H1 asks about the agent's estimate) and recorded: D5 v3.4 note, C5.4 note, pre-registration deviation 11; `metrics/pilot.py` `state_violations` measures pose and map violations by C5.4's rule (0 on the coded procedure's own reports, seed 1003) and `study_analyze.py` reports their rates |
| 3b | major | Report: five seeds in parallel; CLI default 4 | Confirmed | The study uses 8 (vLLM's slots), pre-registration deviation 13 |
| 3c | major | Report: a failing call is attempted 7 times, then the seed is rerun or incomplete; the local path turned every HTTP 400 into a fallback | Confirmed | Only a context-length 400 is a step-level model failure; any other 400 propagates (seed stops, step not written), as on the Anthropic path |
| 3d | major | C9.2's stop after three consecutive policy errors is not implemented | Confirmed | Not applied by decision (every step is scored; infrastructure failures stop the seed instead): C9.2 note, deviation 11 |
| 3e | major | D10 says no output cap below the window for self-hosted models | Confirmed | Deviation 12 with the reason (finding 1) |
| 4 | minor | Turn records differ by provider (usage keys; Anthropic input excludes cached tokens, OpenAI's includes them) | Confirmed | Both providers add normalised `tokens` {in, cached_in, out, reasoning} and `finish`; `study_analyze.py` sums input without double counting |
| 5 | minor | A 400 is handled differently per provider | Confirmed | See 3c |
| 6 | minor | `verify_fix` trusted the agent's own `prior` argument, so a fix computed from a wrong prior could reset the counters | Confirmed | A fix verifies only if its `prior` equals the harness's own (`harness_prior`: PREVIOUS_REPORT's pose composed with the odometry) |
| 7 | minor | Race: two threads could see `system=None` on the first Opus call | Confirmed by reading (the attributes were set in two statements) | System blocks are built per call (the same blocks as before) |
| 8 | minor | The shim lost `_call`, `_with_breakpoint`, `_block`, used by `tools/pilot_trace.py` | Confirmed | Re-exported |
| 9 | minor | Resume test stopped before the first fix; the `relocalised` assertion was vacuous; BadRequest, finish-reason, several-fix_pose and error-result paths untested | Confirmed | New tests (below); a mutation run shows they fail when the logic is broken |
| 10 | minor | CLI: exit 0 at the cap; duplicate seeds; a torn last line made a resume impossible; Ctrl-C did not stop queued seeds; spend of crashed steps was lost | Confirmed | Exit codes 0/1/2/130; seeds de-duplicated; a torn last line is cut with a log line; Ctrl-C cancels queued seeds; spend appended to `spend.jsonl` as it happens and read back on resume; `run.end-*.json` written |
| 11 | minor | `--out=...` and `./course-project/...` were not mapped; an absolute path outside the repo would be written inside the throwaway container | Confirmed | `replay_run.sh` maps both forms and refuses paths outside the repository |
| 12 | minor | Provenance gaps: server identity, chat-template hash, Ollama settings, `dv.py`, end time, host; Opus options in providers.json ignored | Confirmed | `run.json` records the server's `/version` (vLLM) or `/api/version` and model digest (Ollama), the host-side image id and chat-template hash or Ollama server settings, the host and `dv.py`'s hash; `run.end-*.json` the end; the runner refuses Opus options that differ from the provider's fixed settings |
| 13 | nit | `_num` raised OverflowError on a huge integer; the medium entry's sampling note said xhigh | Confirmed | Fixed |

Checked and found correct by the reviewer (not repeated here): resume equivalence across fixes; `verify_fix`'s
tolerance, wrap and edge cases; the Anthropic path sends byte-identical requests to the pilot's code at HEAD (202 of
202 requests on a 101-step mock); identical step message and tools for every arm; request construction; no partial
tool call on `length`; budget locking; no secrets logged.

## Tests

`beaconmind-ros` on the Spark (Python 3.10, openai 3.26.0, anthropic 1.11.0):
`python3 -m pytest -q -p no:cacheprovider` → `110 passed, 2 skipped`. Mutation check of the new tests (each mutation
in a scratch copy, control first):

```
control: 21 passed
prior_ignored: 1 failed (test_verify_fix_rules)
resume_no_counter_src: 1 failed (test_resume_across_fixes_equals_an_uninterrupted_run)
overflow_raises: 1 failed (test_context_overflow_is_a_fallback_but_other_400s_raise)
```

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote the harness, verified and fixed the findings (the
review was an independent Claude Opus 5.5 subagent).
