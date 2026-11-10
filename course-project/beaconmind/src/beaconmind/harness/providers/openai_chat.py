"""OpenAI-compatible Chat Completions provider for the L2 replay loop: vLLM and Ollama.

Arms (configs/providers.json, provider "vllm" or "ollama"):
- Qwen3.8-Flash-Next (NVFP4) on vLLM (tools/serve_qwen38.sh): thinking on, the chat template's
  `reasoning_effort` passed through `chat_template_kwargs`, the checkpoint's generation_config sampling
  (temperature 1.0, top_p 0.95, top_k 20) sent explicitly.
- Gemma 4 26B-A4B on Ollama's /v1 endpoint: thinking on (Ollama's default for this model); the Modelfile's
  sampling (temperature 1, top_k 64, top_p 0.95, the Gemma model-card values) is left to the server, so no
  sampling field is sent.

The tool loop is the Module 4 smoke harness's (assignments/assignment4/system-prompt/tools/smoke_test.py
`run_scenario`, private course repo): the same tool schemas, `tools_d5.run_tool` answers each call, a turn
that ends with finish_reason "length" executes no partial tool call, 30 turns at most. Two changes from it:
- The model's reasoning is sent back inside the tool loop in the message field the server maps to the
  template's thinking: `reasoning` for both servers here. The vLLM build of tools/serve_qwen38.sh renders it as
  <think>text</think> in the replayed assistant turn, while a `reasoning_content` field is dropped and an inline
  <think> in `content` (smoke_test.py's method) is rendered after a second, empty think block (checked with
  /tokenize and /detokenize on 2026-11-10; configs/providers.json `reasoning_replay_check`). Ollama maps
  `reasoning` to the message's thinking.
- Each request carries a sampling seed derived from (sample_key, turn, repeat), so a rerun of the same
  configuration asks for the same samples (batching and speculative decoding still make vLLM output not
  bit-exact).
Every turn's reasoning text is logged (`turns[i].reasoning`) for failure analysis and trace figures.

Failure handling (the same semantics as the Anthropic provider; adversarial review of 2026-11-10):
- the output cap (`max_tokens`, 32768 for the local arms: 14 times the largest turn seen in the dev gate) is
  reached well before the client timeout (3600 s), so a runaway generation ends with finish_reason "length" and
  becomes a counted fallback step instead of a timeout;
- connection errors and HTTP 408/409/429/5xx are retried up to 7 attempts, a client timeout up to 3 (a timeout
  means the server stalled, and a vLLM request is cancelled server-side when the client gives up); after that the
  error propagates, the step is not written and the seed stops (a rerun resumes it);
- an HTTP 400 that reports a context-length overflow is a model failure: the step ends with an error and a
  fallback. Any other 400 is a malformed request (a harness or server problem) and propagates;
- a finish_reason other than "stop", "tool_calls" or "length" ends the step with an error, and no partial tool
  call is executed.
Every turn record carries normalised `tokens` {in, cached_in, out, reasoning} and `finish`, as the Anthropic
provider's do (plan C9.2).

Local models cost nothing per token; `cost_usd` is 0 and the shared Budget never stops them.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote this provider.
"""
import hashlib
import json
import time

from beaconmind.harness import tools_d5 as t5
from beaconmind.harness.replay import step_message

MAX_TURNS = 30
RETRYABLE_STATUS = (408, 409, 429, 500, 502, 503, 504)
ATTEMPTS, TIMEOUT_ATTEMPTS = 7, 3


def sample_seed(sample_key, turn, repeat):
    h = hashlib.sha256(("%s|%d|%d" % (sample_key, turn, repeat)).encode()).hexdigest()
    return int(h[:8], 16) & 0x7FFFFFFF


def _reasoning(msg):
    """The reasoning text of a response message: vLLM's `reasoning_content` (or `reasoning` in newer
    servers) and Ollama's `reasoning`. Pydantic keeps unknown response fields in model_extra."""
    extra = getattr(msg, "model_extra", None) or {}
    for k in ("reasoning_content", "reasoning"):
        v = extra.get(k)
        if not isinstance(v, str):
            v = getattr(msg, k, None)
        if isinstance(v, str) and v:
            return v
    return None


def _usage(resp):
    u = getattr(resp, "usage", None)
    if u is None:
        return {}
    d = u.model_dump() if hasattr(u, "model_dump") else dict(u)
    out = {"prompt_tokens": d.get("prompt_tokens") or 0, "completion_tokens": d.get("completion_tokens") or 0}
    det = d.get("prompt_tokens_details") or {}
    out["cached_tokens"] = det.get("cached_tokens") or 0
    cdet = d.get("completion_tokens_details") or {}
    if cdet.get("reasoning_tokens") is not None:
        out["reasoning_tokens"] = cdet["reasoning_tokens"]
    return out


def tokens(u):
    """Provider-neutral token counts of one turn (OpenAI prompt_tokens already include the cached tokens)."""
    if not u:
        return {"in": None, "cached_in": None, "out": None, "reasoning": None}
    return {"in": u["prompt_tokens"], "cached_in": u["cached_tokens"], "out": u["completion_tokens"],
            "reasoning": u.get("reasoning_tokens")}


def is_context_overflow(text):
    t = text.lower()
    return ("context" in t and ("length" in t or "window" in t)) or "maximum model length" in t or "too many tokens" in t


class OpenAIChatAgent:
    """Provider object for harness/replay.py over an OpenAI-compatible /v1/chat/completions endpoint.

    cfg is one configs/providers.json entry (schema bm.providers/1): provider, model, base_url, thinking,
    sampling, max_turns_per_step, request_timeout_s and options. Options used here:
      max_tokens            output cap per turn (the same 64000 as the Opus arm)
      chat_template_kwargs  passed through extra_body (vLLM)
      reasoning_replay_field  the assistant-message field that carries the reasoning back ("reasoning");
                            null sends no reasoning back
      extra_body            any other server-specific request fields
    """

    def __init__(self, client, key, cfg, repeat=0):
        self.client, self.key, self.cfg, self.repeat = client, key, cfg, repeat
        self.provider = cfg["provider"]
        self.model = cfg["model"]
        self.arm = "L2:" + key
        self.options = dict(cfg.get("options") or {})
        self.max_turns = int(cfg.get("max_turns_per_step") or MAX_TURNS)
        self.tools = t5.openai_tool_defs()
        self.replay_field = self.options.get("reasoning_replay_field")

    def header(self):
        return {"provider": self.provider, "model": self.model, "base_url": self.cfg.get("base_url"),
                "thinking": self.cfg.get("thinking"), "sampling": self.cfg.get("sampling") or {},
                "options": self.options, "max_turns": self.max_turns, "repeat": self.repeat,
                "request_timeout_s": self.cfg.get("request_timeout_s")}

    def request(self, messages, seed):
        kw = {"model": self.model, "messages": messages, "tools": self.tools, "seed": seed}
        if self.options.get("max_tokens"):
            kw["max_tokens"] = int(self.options["max_tokens"])
        extra = dict(self.options.get("extra_body") or {})
        samp = dict(self.cfg.get("sampling") or {})
        for k in ("temperature", "top_p", "presence_penalty"):
            if k in samp:
                kw[k] = samp.pop(k)
        extra.update(samp)                       # top_k and other non-OpenAI sampling fields
        if self.options.get("chat_template_kwargs") is not None:
            extra["chat_template_kwargs"] = dict(self.options["chat_template_kwargs"])
        if extra:
            kw["extra_body"] = extra
        return kw

    def _call(self, kwargs, log):
        import openai
        timeouts = 0
        for attempt in range(ATTEMPTS):
            try:
                t0 = time.perf_counter()
                resp = self.client.chat.completions.create(**kwargs)
                return resp, round(time.perf_counter() - t0, 3)
            except openai.APITimeoutError:
                timeouts += 1
                reason = "timeout"
                if timeouts >= TIMEOUT_ATTEMPTS:
                    raise RuntimeError("server timed out %d times on one request" % timeouts)
            except openai.APIConnectionError as exc:
                reason = type(exc).__name__
            except openai.APIStatusError as exc:
                if exc.status_code not in RETRYABLE_STATUS:
                    raise
                reason = "http %s" % exc.status_code
            if attempt == ATTEMPTS - 1:
                break
            wait = min(120, 5 * 2 ** attempt)
            log("retry in %ds (%s)" % (wait, reason))
            time.sleep(wait)
        raise RuntimeError("server unavailable after %d attempts (last: %s)" % (ATTEMPTS, reason))

    def step(self, system_text, obs, prev, budget, log, sample_key=None):
        import openai
        messages = [{"role": "system", "content": system_text}, {"role": "user", "content": step_message(obs, prev)}]
        state = {"moved": None, "estop": False}
        calls, turns, t0 = [], [], time.perf_counter()
        final, error = None, None
        key = sample_key if sample_key is not None else "step-%s" % obs.get("obs_id")
        for turn in range(self.max_turns):
            seed = sample_seed(key, turn, self.repeat)
            try:
                resp, dt = self._call(self.request(messages, seed), log)
            except openai.BadRequestError as exc:
                if not is_context_overflow(str(exc)):
                    raise                                # a malformed request: a harness or server problem
                error = "context overflow: %s" % str(exc)[:300]
                break
            ch = resp.choices[0]
            m = ch.message
            reasoning = _reasoning(m)
            tcs = list(m.tool_calls or [])
            u = _usage(resp)
            turns.append({"seconds": dt, "finish_reason": ch.finish_reason, "finish": ch.finish_reason, "usage": u,
                          "tokens": tokens(u), "model": getattr(resp, "model", None), "seed": seed,
                          "n_tool_calls": len(tcs), "content_chars": len(m.content or ""),
                          "reasoning_chars": len(reasoning or ""), "reasoning": reasoning, "cost_usd": 0.0})
            if ch.finish_reason == "length":            # truncated: do not execute partial tool calls
                error = "length: the reply hit max_tokens or the context window"
                break
            if ch.finish_reason not in ("stop", "tool_calls"):
                error = "finish: %s" % ch.finish_reason
                break
            if tcs:
                amsg = {"role": "assistant", "content": m.content or "", "tool_calls": []}
                for i, tc in enumerate(tcs):
                    amsg["tool_calls"].append({"id": tc.id or "call_%d_%d" % (turn, i), "type": "function",
                                               "function": {"name": tc.function.name,
                                                            "arguments": tc.function.arguments or "{}"}})
                if self.replay_field and reasoning:
                    amsg[self.replay_field] = reasoning
                messages.append(amsg)
                for tc_msg in amsg["tool_calls"]:
                    name, raw = tc_msg["function"]["name"], tc_msg["function"]["arguments"]
                    try:
                        args = json.loads(raw)
                    except (TypeError, ValueError):
                        args = None
                    if not isinstance(args, dict):
                        res = t5.err("The arguments are not a JSON object.")
                        calls.append({"tool": name, "args": {}, "args_raw": raw, "result": res})
                    else:
                        res = t5.rnd(t5.run_tool(name, args, obs, prev, state))
                        calls.append({"tool": name, "args": args, "result": res})
                    messages.append({"role": "tool", "tool_call_id": tc_msg["id"], "content": json.dumps(res)})
                continue
            final = (m.content or "").strip()
            break
        else:
            error = "turn cap"
        return {"final_text": final, "calls": calls, "turns": turns, "state": state, "error": error,
                "seconds": round(time.perf_counter() - t0, 1), "cost_usd": 0.0}
