"""Anthropic Messages provider for the L2 replay loop (Claude Opus 5.5 arm).

The request settings and the tool loop are those of the 2026-10-29 pilot (harness/anthropic_replay.py at
commit 97028f8), moved here unchanged so harness/replay.py can drive any provider: claude-opus-5-5,
adaptive thinking (field omitted), output_config.effort medium, max_tokens 64000, no temperature, no forced
tool choice (evidence/M1/M1.T11/opus20-comparison.md). Prompt caching: one cache breakpoint at the end of
the system prompt (it covers tools and system) and one on the last block of the newest user turn, so each
tool turn reads the conversation so far from the cache. Thinking blocks are sent back unchanged inside the
tool loop, as the API requires.

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: wrote the tool loop (then in anthropic_replay.py).
Claude Opus 5.5 via Claude Code, 2026-11-10: moved it behind the provider interface of harness/replay.py.
"""
import copy
import json
import time

from beaconmind.harness import tools_d5 as t5
from beaconmind.harness.replay import step_message

SETTINGS = {"model": "claude-opus-5-5", "max_tokens": 64000, "output_config": {"effort": "medium"}}
# USD per million tokens (configs/providers.json and evidence/M1/M1.T11/model-candidates.md, checked 2026-10-07)
PRICE = {"input": 4.0, "cache_write_5m": 5.0, "cache_read": 0.20, "output": 20.0}
MAX_TURNS = 30
RETRY_STATUS = (408, 409, 429, 500, 502, 503, 504, 529)


def turn_cost(u):
    return (u.get("input_tokens", 0) * PRICE["input"] + u.get("cache_creation_input_tokens", 0) * PRICE["cache_write_5m"]
            + u.get("cache_read_input_tokens", 0) * PRICE["cache_read"] + u.get("output_tokens", 0) * PRICE["output"]) / 1e6


def _usage(resp):
    u = resp.usage
    d = u.model_dump() if hasattr(u, "model_dump") else dict(u or {})
    return {k: d.get(k) or 0 for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens",
                                        "cache_read_input_tokens")}


def _block(b):
    return b.model_dump(exclude_none=True) if hasattr(b, "model_dump") else b


def _with_breakpoint(messages):
    msgs = copy.deepcopy(messages)
    for m in msgs:
        if isinstance(m["content"], list):
            for blk in m["content"]:
                blk.pop("cache_control", None)
    last = msgs[-1]["content"]
    if isinstance(last, list) and last:
        last[-1]["cache_control"] = {"type": "ephemeral"}
    return msgs


def _call(client, kwargs, log):
    import anthropic
    for attempt in range(7):
        try:
            t0 = time.perf_counter()
            resp = client.messages.create(**kwargs)
            return resp, round(time.perf_counter() - t0, 3)
        except (anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
            reason = type(exc).__name__
        except anthropic.APIStatusError as exc:
            if exc.status_code not in RETRY_STATUS:
                raise
            reason = "http %s" % exc.status_code
        if attempt == 6:
            break
        wait = min(120, 5 * 2 ** attempt)
        log("retry in %ds (%s)" % (wait, reason))
        time.sleep(wait)
    raise RuntimeError("API retries exhausted (last: %s)" % reason)


def agent_step(client, system_blocks, tools, obs, prev, budget, log, settings=None):
    """One observation: the tool loop until a final text. Returns the step record fields."""
    settings = settings or SETTINGS
    messages = [{"role": "user", "content": [{"type": "text", "text": step_message(obs, prev)}]}]
    state = {"moved": None, "estop": False}
    calls, turns, t0 = [], [], time.perf_counter()
    final, error = None, None
    for _ in range(MAX_TURNS):
        if budget.exceeded():
            error = "budget cap reached"
            break
        kwargs = dict(settings, system=system_blocks, tools=tools, messages=_with_breakpoint(messages))
        resp, dt = _call(client, kwargs, log)
        u = _usage(resp)
        cost = turn_cost(u)
        budget.add(cost)
        content = list(resp.content)
        turns.append({"seconds": dt, "stop_reason": resp.stop_reason, "finish": resp.stop_reason, "usage": u,
                      "tokens": {"in": u["input_tokens"] + u["cache_creation_input_tokens"] + u["cache_read_input_tokens"],
                                 "cached_in": u["cache_read_input_tokens"], "out": u["output_tokens"], "reasoning": None},
                      "cost_usd": round(cost, 5), "model": getattr(resp, "model", None),
                      "thinking_chars": sum(len(getattr(b, "thinking", "") or "") for b in content)})
        if resp.stop_reason in ("max_tokens", "model_context_window_exceeded"):
            error = "length: %s" % resp.stop_reason
            break
        uses = [b for b in content if getattr(b, "type", None) == "tool_use"]
        if uses:
            messages.append({"role": "assistant", "content": [_block(b) for b in content]})
            results = []
            for b in uses:
                args = b.input if isinstance(b.input, dict) else {}
                args, coerced = t5.coerce_numeric_strings(args)      # the same rule as every arm (tools_d5)
                res = t5.rnd(t5.run_tool(b.name, args, obs, prev, state))
                call = {"tool": b.name, "args": args, "result": res}
                if coerced:
                    call["args_raw"] = b.input
                calls.append(call)
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(res)})
            messages.append({"role": "user", "content": results})
            continue
        final = "\n".join(getattr(b, "text", "") or "" for b in content if getattr(b, "type", None) == "text").strip()
        break
    else:
        error = "turn cap"
    return {"final_text": final, "calls": calls, "turns": turns, "state": state, "error": error,
            "seconds": round(time.perf_counter() - t0, 1),
            "cost_usd": round(sum(t["cost_usd"] for t in turns), 5)}


class AnthropicAgent:
    """Provider object for harness/replay.py. `key` names the configs/providers.json entry."""

    provider = "anthropic_messages"

    def __init__(self, client, key="claude-opus-5-5", settings=None):
        self.client, self.key = client, key
        self.settings = dict(settings or SETTINGS)
        self.arm = "L2:" + key           # "L2:claude-opus-5-5", the pilot's arm label
        self.tools = t5.anthropic_tool_defs()

    def header(self):
        return {"provider": self.provider, "settings": self.settings, "price_usd_per_mtok": PRICE,
                "max_turns": MAX_TURNS}

    def step(self, system_text, obs, prev, budget, log, sample_key=None):
        # built per call: no state shared between the threads of a run (the same blocks as the pilot's)
        blocks = [{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}]
        return agent_step(self.client, blocks, self.tools, obs, prev, budget, log, self.settings)
