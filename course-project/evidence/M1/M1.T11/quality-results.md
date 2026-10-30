# M1.T11 frontier quality check

Run 2026-10-07 in `beaconmind-ros` (anthropic 1.11.0, openai 3.26.0). K=1 on the four Module 4 smoke scenarios, in order S1, S2, S3, S4. The prompt text, tool schemas, `run_tool`, and `check` are the Module 4 smoke harness (`assignments/assignment4/system-prompt/tools/smoke_test.py` and `evidence/print-output.txt`). No temperature, top_p, or forced `tool_choice` was sent. No request returned HTTP 400, so there was no retry.

Settings from the docs re-read the same day:

- `claude-sonnet-5-5`: `thinking.type=between_tools` at `output_config.effort=high` (up-front thinking off; accepted at high or below).
- `claude-opus-5-5`: thinking field omitted (adaptive, always on). `output_config.effort=medium` (the documented default). `between_tools` is rejected on this model.
- `gpt-6-sol`: Responses API `reasoning.effort=none`.
- `gpt-6-astra`: Responses API `reasoning.effort=high`. `none` is rejected on this model.
- `claude-fable-5-1`: not called. Both Claude models called `compose_odometry`, so the tool task did not fail.

The served model id on every turn matched the requested id. Token counts are the API usage fields summed across the turns of that scenario set. OpenAI `input_tokens` includes the cached portion; `cached` is `input_tokens_details.cached_tokens`. Astra's `output_tokens` include 289 reasoning tokens. Sol reported 0 reasoning tokens.

| Model | Pass | Seconds (S1, S2, S3, S4) | Tool called | Failure mode | Tokens in / out / cached |
| --- | --- | --- | --- | --- | --- |
| `claude-sonnet-5-5` | 3/4 | 17.4, 18.9, 19.7, 16.9 | yes on all four | S4: final text is a sentence followed by JSON, so `check` does not parse it | 239157 / 7401 / 0 |
| `gpt-6-sol` | 4/4 | 16.5, 12.8, 11.3, 10.5 | yes on all four | none | 135232 / 2897 / 122888 |
| `claude-opus-5-5` | 4/4 | 16.3, 20.3, 21.2, 17.4 | yes on all four | none | 216225 / 6498 / 0 |
| `gpt-6-astra` | 4/4 | 23.9, 22.4, 18.2, 20.4 | yes on all four | none | 129479 / 3274 / 117015 |

Sonnet S4 still called tools (6 calls, including `compose_odometry`) in 16.9 s. The harness scores it FAIL because `json.loads` is applied to the whole final string. That string begins `The summary isn't needed for a REFUSED decision...` and then a JSON object. This note does not re-score that object.

`quality-records.jsonl` has one row per scenario, including tool names and the final text. Thinking signatures are omitted. `quality-run.log` is the runner stdout.

M1.T11 stays `todo`. This run does not write the budget guard, `model-ids.txt`, `api-facts.md`, or the guard-refusal proof in the task's acceptance list. Xiaohui lifted the $5 cap for this session on 2026-10-07.

No API key, authorization header, or secrets file contents were written into this directory. A pattern search of these evidence files for key material and credential field names matched nothing.

AI-assisted: Grok 4.7 via Cursor, 2026-10-07: ran the quality tool-call check.
