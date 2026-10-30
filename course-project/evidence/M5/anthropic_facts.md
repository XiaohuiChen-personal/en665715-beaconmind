# Anthropic API facts (official docs), retrieved 2026-10-29

Sources (all fetched 2026-10-29):

- Pricing: <https://platform.claude.com/docs/en/about-claude/pricing>
- Prompt caching: <https://platform.claude.com/docs/en/build-with-claude/prompt-caching>
- Models overview (model id): <https://platform.claude.com/docs/en/about-claude/models/overview>

The pricing page says "For the most current pricing information, visit claude.com/pricing."
I did not fetch claude.com/pricing; the numbers below are from the docs pages above. The pricing
table on the prompt-caching page is identical to the one on the pricing page for Claude Opus 5.5.

## (a) Price per million tokens (MTok), model id `claude-opus-5-5`

The models overview lists Claude API ID `claude-opus-5-5` for **Claude Opus 5.5** (also the alias;
"Every Claude model ID is a pinned snapshot, including the dateless IDs used from the 4.6 generation on").

| Item | Claude Opus 5.5 | Source wording |
| --- | --- | --- |
| Base input | **$4 / MTok** | pricing table, "Base input tokens" |
| 5-minute cache write | **$5 / MTok** (1.25× base) | "5m cache writes" |
| 1-hour cache write | **$8 / MTok** (2× base) | "1h cache writes" |
| Cache read ("Cache hits and refreshes") | **$0.20 / MTok** (0.05× base) | footnote 2: "Cache hits and refreshes on Claude Opus 5.5 and Claude Sonnet 5.5 are priced at 0.05x the base input price." |
| Output | **$20 / MTok** | "Output tokens" |

Exact table row (pricing page): `| Claude Opus 5.5 | $4 / MTok | $5 / MTok | $8 / MTok | $0.20 / MTok2 | $20 / MTok |`

Note the exception: most models read from cache at 0.1× base, but **Opus 5.5 reads at 0.05×**. Pricing
page: "On Claude Opus 5.5 and Claude Sonnet 5.5, a cache hit costs 5% of the standard input price
($0.20 USD per million tokens on Claude Opus 5.5, $0.10 USD on Claude Sonnet 5.5)." (Elsewhere the page
still says "A cache hit costs 10% of the standard input price" as the general rule.)

Related modifiers on the same page, in case the report needs them:

- Batch API: 50 % off, so Opus 5.5 batch is **$2 input / $10 output** per MTok.
- Fast mode (Opus 5.5): **$8 input / $40 output** per MTok; "Prompt caching multipliers apply on top of fast mode pricing."
- Long context: "Claude 4.6 and later models (except Claude Haiku 5.5) and Claude Mythos Preview include the full 1M token context window at standard pricing." Opus 5.5 has a 1M-token context window (models overview).
- Data residency: US-only inference via `inference_geo` is a 1.1× multiplier on all token categories, including cache writes and reads (Claude 4.6 and later).
- The multipliers "stack with other pricing modifiers, including the Batch API discount and data residency."

## (b) Prompt caching mechanics

**Two ways to enable it** (prompt-caching page, top): "Automatic caching: Add a single `cache_control`
field at the top level of your request. The system automatically applies the cache breakpoint to the last
cacheable block and moves it forward as conversations grow." and "Explicit cache breakpoints: Place
`cache_control` directly on individual content blocks for fine-grained control over exactly what gets cached."

**Where breakpoints go and the prefix order:**

- "Prompt caching references the entire prompt: `tools`, `system`, and `messages` (in that order), up to and including the block designated with `cache_control`."
- "Cache prefixes are created in the following order: `tools`, `system`, then `messages`. This order forms a hierarchy where each level builds upon the previous ones."
- Tools: "Tool definitions can be cached by placing `cache_control` on the last tool in your `tools` array. All tools defined before and including that tool are cached as a single prefix."
- System: the examples put `"cache_control": {"type": "ephemeral"}` on a text block inside the `system` array (for example the last system block holding a long document).
- Messages: cacheable blocks include "Text messages: Content blocks in the `messages.content` array, for both user and assistant turns", "Images and documents: … in user turns", and "Tool use and tool results: … in both user and assistant turns".
- Cannot be cached directly: thinking blocks ("cannot be cached directly with `cache_control`", though they are cached as part of earlier assistant turns), sub-content blocks such as citations, and empty text blocks.
- Invalidation follows the same hierarchy: "Changes at each level invalidate that level and all subsequent levels." Changing tool definitions invalidates the whole cache.
- Placement rule: "Place `cache_control` on the last block whose prefix is identical across the requests you want to share a cache."
- Writes and lookback: "Cache writes occur only at your breakpoint." Reads walk backward from each breakpoint, and "The lookback window is 20 blocks."

**Maximum number of breakpoints:** "You can define up to 4 cache breakpoints". With automatic caching:
"the automatic cache breakpoint uses one of the 4 available breakpoint slots", and "If 4 explicit
block-level breakpoints already exist, the API returns a 400 error (no slots left for automatic caching)."

**Minimum cacheable prompt length** (Claude API, Claude Platform on AWS, Google Cloud (Google managed), Microsoft Foundry):

- **512 tokens for Claude Opus 5.5** (same list: Fable 5.1, Mythos 5.1, Opus 5, Sonnet 5.5, Fable 5, Mythos 5, Haiku 5.5)
- 1,024 tokens for Claude Opus 4.8 (also Sonnet 5, Sonnet 4.6, Sonnet 4.5, Opus 4.1, Opus 4, Sonnet 4)
- 2,048 tokens for Claude Opus 4.7 and Mythos Preview
- 4,096 tokens for Claude Opus 4.6 and Opus 4.5
- "Shorter prompts cannot be cached, even if marked with `cache_control`. Any requests to cache fewer than this number of tokens are processed without caching, and no error is returned."

**Usage fields** (in `usage`, or the `message_start` event when streaming):

- `cache_creation_input_tokens`: "Number of tokens written to the cache when creating a new entry"
- `cache_read_input_tokens`: "Number of tokens retrieved from the cache for this request"
- `input_tokens`: "Number of input tokens that were not read from or used to create a cache (that is, tokens after the last cache breakpoint)"
- "total_input_tokens = cache_read_input_tokens + cache_creation_input_tokens + input_tokens"
- There is also a `cache_creation` object split by lifetime (`ephemeral_5m_input_tokens`, `ephemeral_1h_input_tokens`); "the current `cache_creation_input_tokens` field equals the sum of the values in the `cache_creation` object."
- To check for a miss: "if both `cache_creation_input_tokens` and `cache_read_input_tokens` are 0, the prompt was not cached".

**Cache lifetime:**

- "By default, the cache has a 5-minute lifetime. The cache is refreshed for no additional cost each time the cached content is used."
- "The lifetime is measured from the start of the request that writes or reads the cache entry, not from the end of its response."
- 1-hour option: `{"type": "ephemeral", "ttl": "1h"}`, charged at 2× base input for the write.
- "Currently, `ephemeral` is the only supported cache type, which by default has a 5-minute lifetime."
- Concurrency: "a cache entry only becomes available after the first response starts."
- Supported models: "Prompt caching (both automatic and explicit) is supported on all active Claude models."

## (c) Automatic caching option

**Yes.** Add one top-level `"cache_control": {"type": "ephemeral"}` field to the Messages request (the
docs' own examples use `"model": "claude-opus-5-5"`). "The system automatically applies the cache breakpoint
to the last cacheable block", and "the cache point moves forward automatically as conversations grow." The
docs call it "the recommended starting point for most use cases" (pricing page). It uses a 5-minute TTL by
default, and `"ttl": "1h"` is accepted. "Pricing, minimum token thresholds, context ordering requirements, and
the 20-block lookback window all apply the same as with explicit breakpoints." It can be combined with
explicit breakpoints (it takes one of the 4 slots). It is available everywhere "except the legacy Amazon
Bedrock (Opus 4.6 and earlier) integration". Caveat from the docs: if the last block changes on every
request (for example a timestamp), automatic caching never hits, so use an explicit breakpoint at the end of
the static prefix instead.

Not found on these pages: nothing asked for in (a)–(c) was missing.
