# M1.T11 frontier model candidates

Retrieved 2026-10-07. This note checks the five names Xiaohui named that day against public Anthropic and OpenAI docs. No Anthropic or OpenAI API call was made, no key was read, and no money was spent. M1.T11 stays `todo`.

The spike rule in `course-project/plan/M1-foundations.md` (M1.T11) is one real tool call per provider family: OpenAI Responses and Anthropic Messages. The whole spike budget is ≤ $5. Keys, when used later, live only in `~/.config/beaconmind/secrets.env` on the Spark. That file was not opened.

Cursor product slugs are not API model ids. The public API id is the value in the docs tables below.

## Sources

| Page | URL | Retrieved |
| --- | --- | --- |
| Claude models overview | https://docs.anthropic.com/en/docs/about-claude/models/overview | 2026-10-07 |
| Claude Opus 5.5 | https://platform.claude.com/docs/en/models/opus-5-5/overview | 2026-10-07 |
| Claude Sonnet 5.5 | https://platform.claude.com/docs/en/models/sonnet-5-5/overview | 2026-10-07 |
| Claude Fable 5.1 | https://platform.claude.com/docs/en/models/fable-5-1/overview | 2026-10-07 |
| Claude pricing | https://platform.claude.com/docs/en/docs/about-claude/pricing | 2026-10-07 |
| GPT-6 Sol | https://developers.openai.com/api/docs/models/gpt-6-sol | 2026-10-07 |
| GPT-6 Astra | https://developers.openai.com/api/docs/models/gpt-6-astra | 2026-10-07 |
| OpenAI pricing | https://developers.openai.com/api/docs/pricing | 2026-10-07 |
| Using GPT-6 | https://developers.openai.com/api/docs/guides/latest-model | 2026-10-07 |

`https://platform.openai.com/docs/models` timed out on this retrieval and is not used below.

## Candidates

Prices are USD per million tokens, standard short-context rates. Cache reads are listed where the same page publishes them. None of these names is unconfirmed.

| Name | API id | Tool calling | Published price | Fit for a 60 s tool-calling robot loop |
| --- | --- | --- | --- | --- |
| opus 5.5 | `claude-opus-5-5` | Yes, on the Messages API. The overview lists tool use for every current Claude model. Forced `tool_choice` returns an error. Thinking is adaptive and always on. | $4 input / $20 output; cache read $0.20; 5m cache write $5 | Documented latency is Moderate, and thinking cannot be turned off. Quality fallback if Sonnet's decisions are wrong. |
| sonnet 5.5 | `claude-sonnet-5-5` | Yes, on the Messages API. Forced tool use returns an error. `between_tools` turns off up-front thinking and works at `high` effort or below. | $2 input / $10 output; cache read $0.20; 5m cache write $2.50 | Best Anthropic fit: the docs call it Fast and "the best combination of speed and intelligence." Default effort is `high`. |
| fable 5.1 | `claude-fable-5-1` | Yes, on the Messages API. Forced tool use returns an error. Thinking is adaptive and always on. Default effort is `high`. | $10 input / $50 output; cache read $0.25; 5m cache write $12.50 | Skip for this spike. Documented latency is Slower. Anthropic says to use it when Opus 5.5 at higher effort still falls short. |
| gpt 6 sol | `gpt-6-sol` | Yes. The model page lists function calling as supported. Built-in tools and function calling use the Responses API. Chat Completions function calling works only with `reasoning_effort` set to `none`. | On the model page: $2 input / $0.20 cached input / $2.50 cache writes / $10 output. Not in the flagship table on the pricing page (that table lists `gpt-6.1-sol` instead). | Best OpenAI fit: documented for complex coding and agentic workflows, and `reasoning.effort` includes `none` through `max` (default `medium`). |
| gpt 6 astra | `gpt-6-astra` | Yes. The model page lists function calling as supported. The Using GPT-6 guide says tool calling requires the Responses API. `reasoning.effort` is `low`, `medium`, `high`, `xhigh`, and `max` (no `none`). | $10 input / $1 cached input / $12.50 cache writes / $50 output (model page and the pricing page, standard short context). Long context above 272K input tokens is 2× input and 1.5× output for the full request. | Skip for this spike. It is the most capable GPT-6 model, at five times Sol's token price, and it cannot turn reasoning off. |

Cursor slugs seen in this environment, and the public API ids they do not replace:

| Cursor slug | Public API id to use |
| --- | --- |
| `claude-opus-5-5-xhigh` | `claude-opus-5-5` |
| `claude-sonnet-5-5-high` | `claude-sonnet-5-5` |
| `claude-fable-5-1-thinking-high` | `claude-fable-5-1` |
| `gpt-5.6-sol-xhigh` | Not `gpt-6-sol`. The pricing page lists a separate model, `gpt-5.6-sol`, under Cyber models at $4 input / $20 output. The named "gpt 6 sol" id is `gpt-6-sol`. |

The Using GPT-6 guide also documents a newer Sol, `gpt-6.1-sol`, at $2 input / $0.10 cached input / $10 output on the standard short-context pricing table, and says to review the migration guide before switching off `gpt-6-sol`. It is the same provider family. It is not one of the five named models, so it is not a third spike call.

## Recommended set

Call two models, one per provider family:

1. **Anthropic Messages:** `claude-sonnet-5-5`
2. **OpenAI Responses:** `gpt-6-sol`

That pair is the smallest set that answers both questions: each named model is a documented API model, and one fast tool-calling model from each family is enough for the spike. Sonnet is the speed pick inside the Claude lineup. Sol is the agentic pick inside the named OpenAI pair, and it is the OpenAI id M1.T11 already expects.

Skip for this spike:

- **Fable 5.1** (`claude-fable-5-1`). Real, and the wrong first call: Slower, thinking always on, default effort `high`, $50 per million output tokens.
- **GPT-6 Astra** (`gpt-6-astra`). Real, and the wrong first OpenAI call: same $10 / $50 token price, no `none` effort, aimed at the most demanding work.
- **Opus 5.5** (`claude-opus-5-5`). Real, and still the model Anthropic says to start with when quality is the open question. Skip it on this spike because the missed course gate is p95 ≤ 60 s, Opus latency is Moderate, and its thinking cannot be turned off. Call it later only if Sonnet's tool decision is wrong.

M1.T11 step 7 still names `--model-key claude-opus-5-5` for the Anthropic call and `--model-key gpt-6-sol-low` for the OpenAI call. Both of those API ids exist in the docs retrieved today. Choosing Sonnet instead of Opus is a selection for the 60 s loop, not a missing-id stop. `models.list()` on the Spark, inside the container, is still the free account check before any spend.

## Expected spend for one short tool call each

These are arithmetic on the published rates, not measured invoices. A tool round-trip is two billed requests: the model calls the tool, then the harness sends the tool result back. No cache, no batch, no fast mode, short context.

Illustration, 2,000 input tokens and 1,000 output tokens on each of the two requests, at $2 / $10 per million:

- One provider: `2 × (2,000 × 2 + 1,000 × 10) / 1,000,000 = $0.028`
- Sonnet plus Sol: **$0.056**

The spike's own reserve, checked before each request, is 2,000 input plus 8,000 output tokens. If both requests on both providers consume that whole reserve:

- One provider: `2 × (2,000 × 2 + 8,000 × 10) / 1,000,000 = $0.168`
- Sonnet plus Sol: **$0.336**

Both figures sit well under the $5 cap. The same reserve on Fable or Astra, at $10 / $50, is `2 × (2,000 × 10 + 8,000 × 50) / 1,000,000 = $0.84` per provider. One 100,000-token output on either of those models is `100,000 × 50 / 1,000,000 = $5.00`, which is the whole spike cap. That is a reason to keep them out of the first call.

## Disclosure

AI-assisted: Grok 4.7 via Cursor, 2026-10-07: researched the frontier candidates.
