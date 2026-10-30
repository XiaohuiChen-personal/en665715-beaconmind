#!/usr/bin/env python3
"""Module 4 smoke scenarios on frontier APIs.

The default is one pass of each scenario (K=1) across the roster. ``--k`` repeats
each scenario, and ``--model`` keeps the queue to one id so a repeat cannot call
the rest of the roster. Pass checks stay in smoke_test.check.

The prompt text, tool names, tool JSON schemas, tool execution, and pass checks
come from assignments/assignment4/system-prompt/tools/smoke_test.py. This file
only changes the HTTP client. It does not send temperature, top_p, or a forced
tool_choice: Anthropic rejects non-default sampling and forced tool use, and
OpenAI accepts temperature only at reasoning effort none.

Request fields, re-read 2026-10-07:
- Sonnet 5.5: thinking {"type": "between_tools"} at output_config.effort high
  (https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking).
  Opus 5.5 and Fable 5.1 reject between_tools and disabled; thinking stays adaptive.
- gpt-6-sol: Responses API reasoning {"effort": "none"}
  (https://developers.openai.com/api/docs/models/gpt-6-sol).
- gpt-6-astra: none is rejected. This run uses effort high
  (https://developers.openai.com/api/docs/guides/reasoning).
- Assistant thinking/reasoning items are sent back unchanged inside the tool loop.

AI-assisted: Grok 4.7 via Cursor, 2026-10-07: wrote the frontier quality runner.
AI-assisted: Grok 4.7 via Cursor, 2026-10-07: added --k and --model for the Opus K=5 run.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)

ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = ROOT / "assignments/assignment4/system-prompt/tools"
PROMPT_PATH = ROOT / "assignments/assignment4/system-prompt/evidence/print-output.txt"
OUT_DIR = ROOT / "course-project/evidence/M1/M1.T11"
SCENARIO_ORDER = (
    "S1_duplicate_new",
    "S2_refuse_request",
    "S3_third_id_rejected",
    "S4_refuse_in_explore",
)
MAX_TURNS = 30
MAX_TOKENS = 64000
REQUEST_TIMEOUT_S = 900

# Documented request settings. Fable is appended only if both Claude models fail the tool task.
MODELS = [
    {
        "id": "claude-sonnet-5-5",
        "provider": "anthropic",
        "thinking": {"type": "between_tools"},
        "output_config": {"effort": "high"},
        "reasoning": None,
    },
    {
        "id": "gpt-6-sol",
        "provider": "openai",
        "thinking": None,
        "output_config": None,
        "reasoning": {"effort": "none"},
    },
    {
        "id": "claude-opus-5-5",
        "provider": "anthropic",
        "thinking": None,
        "output_config": {"effort": "medium"},
        "reasoning": None,
    },
    {
        "id": "gpt-6-astra",
        "provider": "openai",
        "thinking": None,
        "output_config": None,
        "reasoning": {"effort": "high"},
    },
]
FABLE = {
    "id": "claude-fable-5-1",
    "provider": "anthropic",
    "thinking": None,
    "output_config": {"effort": "high"},
    "reasoning": None,
}

_SECRET_RE = re.compile(
    r"(sk-ant-[A-Za-z0-9_\-]{8,}|sk-[A-Za-z0-9_\-]{8,}|Authorization:\s*\S+|x-api-key[:\s]+\S+)",
    re.I,
)


def redact(text, secrets):
    out = text if isinstance(text, str) else str(text)
    for value in secrets.values():
        if value and value in out:
            out = out.replace(value, "[redacted]")
    return _SECRET_RE.sub("[redacted]", out)


def load_secrets(path):
    raw = Path(path).read_text(encoding="utf-8")
    vals = {}
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("export "):
            s = s[len("export "):].strip()
        if "=" not in s:
            continue
        key, value = s.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        vals[key.strip()] = value
    return vals


def load_prompt():
    text = PROMPT_PATH.read_text(encoding="utf-8")
    marker = "=== FINAL PROMPT ==="
    system_text = text[text.index(marker) + len(marker):].strip()
    return system_text


def anthropic_tools(smoke):
    return [
        {"name": name, "description": desc, "input_schema": smoke.schema(props)}
        for name, desc, props in smoke.TOOLS
    ]


def openai_tools(smoke):
    return [
        {
            "type": "function",
            "name": name,
            "description": desc,
            "parameters": smoke.schema(props),
        }
        for name, desc, props in smoke.TOOLS
    ]


def usage_dump(usage):
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    if isinstance(usage, dict):
        return usage
    return {"repr": type(usage).__name__}


def add_usage(total, part):
    for key, value in part.items():
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            total[key] = total.get(key, 0) + value
        elif isinstance(value, dict):
            bucket = total.setdefault(key, {})
            if isinstance(bucket, dict):
                add_usage(bucket, value)


def scrub(obj):
    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            if key in ("signature", "encrypted_content", "encrypted_reasoning") and isinstance(value, str):
                out[key] = "<omitted %d chars>" % len(value)
            else:
                out[key] = scrub(value)
        return out
    if isinstance(obj, list):
        return [scrub(item) for item in obj]
    return obj


def settings_of(spec):
    return {
        "thinking": spec.get("thinking"),
        "output_config": spec.get("output_config"),
        "reasoning": spec.get("reasoning"),
        "store": spec.get("store"),
        "max_tokens": MAX_TOKENS,
        "temperature": None,
        "tool_choice": None,
    }


def block_dict(block):
    if hasattr(block, "model_dump"):
        return block.model_dump(exclude_none=True)
    return block


def error_body(exc, secrets):
    body = getattr(exc, "body", None)
    if body is None:
        body = getattr(exc, "message", None)
    if body is None:
        body = str(exc)
    if not isinstance(body, str):
        try:
            body = json.dumps(body)
        except TypeError:
            body = str(body)
    status = getattr(exc, "status_code", None)
    return status, redact(body, secrets)[:2000]


def correct_spec(spec, message):
    """One documented correction. Returns a new spec, or None when there is no correction."""
    msg = message.lower()
    nxt = dict(spec)
    if spec["provider"] == "anthropic" and spec.get("thinking") and "between_tools" in msg:
        nxt["thinking"] = None
        nxt["retry_note"] = "omitted thinking after between_tools was rejected; adaptive is the documented fallback"
        return nxt
    if spec["provider"] == "anthropic" and spec.get("output_config") and "output_config" in msg and (
        "unknown" in msg or "extra" in msg or "unexpected" in msg or "not supported" in msg
    ):
        nxt["output_config"] = None
        nxt["retry_note"] = "omitted output_config after it was rejected"
        return nxt
    if spec["provider"] == "openai" and spec.get("store") is False and "store" in msg:
        nxt["store"] = None
        nxt["retry_note"] = "omitted store after it was rejected"
        return nxt
    if spec["provider"] == "openai" and spec.get("reasoning", {}) and spec["reasoning"].get("effort") == "none" and (
        "none" in msg and ("not support" in msg or "unsupported" in msg or "invalid" in msg)
    ):
        nxt["reasoning"] = None
        nxt["retry_note"] = "omitted reasoning.effort none after it was rejected; server default applies"
        return nxt
    if spec["provider"] == "openai" and spec.get("reasoning", {}) and spec["reasoning"].get("effort") == "high" and (
        "high" in msg and ("not support" in msg or "unsupported" in msg or "invalid" in msg)
    ):
        nxt["reasoning"] = None
        nxt["retry_note"] = "omitted reasoning.effort high after it was rejected; server default applies"
        return nxt
    return None


class StopModel(RuntimeError):
    def __init__(self, message, spec):
        super().__init__(message)
        self.spec = spec


def call_anthropic(client, spec, system_text, messages, tools, secrets):
    kwargs = {
        "model": spec["id"],
        "max_tokens": MAX_TOKENS,
        "system": system_text,
        "messages": messages,
        "tools": tools,
    }
    if spec.get("thinking"):
        kwargs["thinking"] = spec["thinking"]
    if spec.get("output_config"):
        kwargs["output_config"] = spec["output_config"]
    try:
        t0 = time.perf_counter()
        resp = client.messages.create(**kwargs)
        return resp, round(time.perf_counter() - t0, 3), spec
    except Exception as exc:
        status, body = error_body(exc, secrets)
        if status != 400:
            raise StopModel("http %s: %s" % (status, body), spec) from exc
        nxt = correct_spec(spec, body)
        if nxt is None:
            raise StopModel("http 400: %s" % body, spec) from exc
        print("retry %s once: %s" % (spec["id"], nxt.get("retry_note")), flush=True)
        print("first error: %s" % body[:500], flush=True)
        kwargs["model"] = nxt["id"]
        kwargs.pop("thinking", None)
        kwargs.pop("output_config", None)
        if nxt.get("thinking"):
            kwargs["thinking"] = nxt["thinking"]
        if nxt.get("output_config"):
            kwargs["output_config"] = nxt["output_config"]
        try:
            t0 = time.perf_counter()
            resp = client.messages.create(**kwargs)
            return resp, round(time.perf_counter() - t0, 3), nxt
        except Exception as exc2:
            status2, body2 = error_body(exc2, secrets)
            raise StopModel("retry http %s: %s" % (status2, body2), nxt) from exc2


def call_openai(client, spec, system_text, input_list, tools, secrets):
    kwargs = {
        "model": spec["id"],
        "instructions": system_text,
        "input": input_list,
        "tools": tools,
        "max_output_tokens": MAX_TOKENS,
    }
    if spec.get("store") is not False:
        pass
    else:
        kwargs["store"] = False
    if spec.get("reasoning"):
        kwargs["reasoning"] = spec["reasoning"]
    try:
        t0 = time.perf_counter()
        resp = client.responses.create(**kwargs)
        return resp, round(time.perf_counter() - t0, 3), spec
    except Exception as exc:
        status, body = error_body(exc, secrets)
        if status != 400:
            raise StopModel("http %s: %s" % (status, body), spec) from exc
        nxt = correct_spec(spec, body)
        if nxt is None:
            raise StopModel("http 400: %s" % body, spec) from exc
        print("retry %s once: %s" % (spec["id"], nxt.get("retry_note")), flush=True)
        print("first error: %s" % body[:500], flush=True)
        kwargs.pop("reasoning", None)
        kwargs.pop("store", None)
        if nxt.get("reasoning"):
            kwargs["reasoning"] = nxt["reasoning"]
        if nxt.get("store") is False:
            kwargs["store"] = False
        try:
            t0 = time.perf_counter()
            resp = client.responses.create(**kwargs)
            return resp, round(time.perf_counter() - t0, 3), nxt
        except Exception as exc2:
            status2, body2 = error_body(exc2, secrets)
            raise StopModel("retry http %s: %s" % (status2, body2), nxt) from exc2


def run_anthropic_scenario(client, spec, system_text, tools, scen, smoke, secrets):
    obs, prev = scen["observation"], scen["prev_report"]
    user = json.dumps({
        "mission": scen["mission"],
        "operator_request": scen["operator_request"],
        "OBSERVATION": obs,
        "PREVIOUS_REPORT": prev,
    })
    messages = [{"role": "user", "content": user}]
    state = {"moved": None, "estop": False}
    calls, turns = [], []
    t0 = time.perf_counter()
    active = spec

    def done(final=None, error=None):
        out = {
            "final": final,
            "calls": calls,
            "turns": turns,
            "state": state,
            "seconds": round(time.perf_counter() - t0, 1),
            "settings": settings_of(active),
        }
        if error:
            out["error"] = error
        return out

    for _ in range(MAX_TURNS):
        resp, dt, active = call_anthropic(client, active, system_text, messages, tools, secrets)
        content = list(resp.content)
        stop = resp.stop_reason
        turns.append({
            "seconds": dt,
            "stop_reason": stop,
            "usage": usage_dump(resp.usage),
            "model": getattr(resp, "model", None),
        })
        tool_uses = [block for block in content if getattr(block, "type", None) == "tool_use"]
        if stop in ("max_tokens", "model_context_window_exceeded"):
            return done(error="length: the reply ran out of window (%s)" % stop)
        if tool_uses:
            messages.append({"role": "assistant", "content": [block_dict(block) for block in content]})
            results = []
            for block in tool_uses:
                args = block.input if isinstance(block.input, dict) else {}
                res = smoke.rnd(smoke.run_tool(block.name, args, obs, prev, state))
                calls.append({"tool": block.name, "args": args, "result": res})
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(res),
                })
            messages.append({"role": "user", "content": results})
            continue
        texts = [block.text or "" for block in content if getattr(block, "type", None) == "text"]
        return done(final="\n".join(texts).strip())
    return done(error="turn cap")


def run_openai_scenario(client, spec, system_text, tools, scen, smoke, secrets):
    obs, prev = scen["observation"], scen["prev_report"]
    user = json.dumps({
        "mission": scen["mission"],
        "operator_request": scen["operator_request"],
        "OBSERVATION": obs,
        "PREVIOUS_REPORT": prev,
    })
    input_list = [{"role": "user", "content": user}]
    state = {"moved": None, "estop": False}
    calls, turns = [], []
    t0 = time.perf_counter()
    active = dict(spec)
    if "store" not in active:
        active["store"] = False

    def done(final=None, error=None):
        out = {
            "final": final,
            "calls": calls,
            "turns": turns,
            "state": state,
            "seconds": round(time.perf_counter() - t0, 1),
            "settings": settings_of(active),
        }
        if error:
            out["error"] = error
        return out

    for _ in range(MAX_TURNS):
        resp, dt, active = call_openai(client, active, system_text, input_list, tools, secrets)
        status = getattr(resp, "status", None)
        incomplete = getattr(resp, "incomplete_details", None)
        incomplete_reason = getattr(incomplete, "reason", None) if incomplete else None
        output = list(resp.output or [])
        turns.append({
            "seconds": dt,
            "stop_reason": status,
            "incomplete_reason": incomplete_reason,
            "output_types": [getattr(item, "type", None) for item in output],
            "usage": usage_dump(resp.usage),
            "model": getattr(resp, "model", None),
        })
        if status == "incomplete" and incomplete_reason == "max_output_tokens":
            return done(error="length: the reply ran out of window (max_output_tokens)")
        function_calls = [item for item in output if getattr(item, "type", None) == "function_call"]
        if function_calls:
            input_list.extend(output)
            for item in function_calls:
                try:
                    args = json.loads(item.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                if not isinstance(args, dict):
                    args = {}
                res = smoke.rnd(smoke.run_tool(item.name, args, obs, prev, state))
                calls.append({"tool": item.name, "args": args, "result": res})
                input_list.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(res),
                })
            continue
        return done(final=(resp.output_text or "").strip())
    return done(error="turn cap")


def record_of(model_id, scenario, out, head, info, run_no=1):
    usage = {}
    request_seconds = []
    for turn in out.get("turns") or []:
        add_usage(usage, turn.get("usage") or {})
        if "seconds" in turn:
            request_seconds.append(turn["seconds"])
    failed = [key for key, value in head.items() if value is False]
    calls = out.get("calls") or []
    return {
        "model": model_id,
        "scenario": scenario,
        "run": run_no,
        "seconds": out.get("seconds"),
        "all_pass": bool(head.get("all_pass")),
        "failed": failed,
        "error": out.get("error", ""),
        "tool_called": bool(calls),
        "compose_odometry_called": any(c.get("tool") == "compose_odometry" for c in calls),
        "tools": [c.get("tool") for c in calls],
        "n_tool_calls": len(calls),
        "usage": usage,
        "request_seconds": request_seconds,
        "settings": out.get("settings"),
        "served_model": [t.get("model") for t in (out.get("turns") or [])],
        "info": info,
        "final": out.get("final"),
    }


def failed_tool_task(rows):
    if not rows:
        return True
    if any(row.get("skipped") for row in rows):
        return False
    if all(row.get("error") and not row.get("tool_called") for row in rows):
        return True
    return not any(row.get("compose_odometry_called") for row in rows)


def _skip_row(spec, scenario, run_no, settings):
    return {
        "model": spec["id"],
        "scenario": scenario,
        "run": run_no,
        "seconds": None,
        "all_pass": False,
        "failed": ["not run"],
        "error": "not run: previous request stopped this model",
        "tool_called": False,
        "compose_odometry_called": False,
        "tools": [],
        "n_tool_calls": 0,
        "usage": {},
        "request_seconds": [],
        "settings": settings,
    }


def run_model(spec, client, system_text, tools, smoke, secrets, handle, repeats=1):
    rows = []
    print("=== %s settings %s" % (spec["id"], json.dumps(settings_of(spec))), flush=True)
    print("k %d" % repeats, flush=True)
    active = spec
    jobs = [(name, run_no) for name in SCENARIO_ORDER for run_no in range(1, repeats + 1)]
    for job_i, (name, run_no) in enumerate(jobs):
        scen = smoke.SCENARIOS[name]
        try:
            if spec["provider"] == "anthropic":
                out = run_anthropic_scenario(client, active, system_text, tools, scen, smoke, secrets)
            else:
                out = run_openai_scenario(client, active, system_text, tools, scen, smoke, secrets)
            saved = out.get("settings") or {}
            active = dict(spec)
            active["thinking"] = saved.get("thinking")
            active["output_config"] = saved.get("output_config")
            active["reasoning"] = saved.get("reasoning")
            if "store" in saved:
                active["store"] = saved.get("store")
        except StopModel as exc:
            out = {
                "final": None,
                "calls": [],
                "turns": [],
                "state": {"moved": None, "estop": False},
                "seconds": 0.0,
                "error": redact(str(exc), secrets),
                "settings": settings_of(exc.spec),
            }
            try:
                head, info = smoke.check(name, out)
            except Exception as check_exc:
                head, info = {"all_pass": False, "check_error": "%s: %s" % (type(check_exc).__name__, check_exc)}, {}
            row = record_of(spec["id"], name, out, head, info, run_no)
            rows.append(row)
            handle.write(json.dumps(scrub(row)) + "\n")
            handle.flush()
            print("%s %s run %d STOP %s" % (spec["id"], name, run_no, row["error"][:300]), flush=True)
            for later_name, later_run in jobs[job_i + 1:]:
                skip = _skip_row(spec, later_name, later_run, settings_of(exc.spec))
                rows.append(skip)
                handle.write(json.dumps(skip) + "\n")
                handle.flush()
            return rows
        try:
            head, info = smoke.check(name, out)
        except Exception as check_exc:
            head, info = {"all_pass": False, "check_error": "%s: %s" % (type(check_exc).__name__, check_exc)}, {}
        row = record_of(spec["id"], name, out, head, info, run_no)
        rows.append(row)
        handle.write(json.dumps(scrub(row)) + "\n")
        handle.flush()
        print(
            spec["id"], name, "run", run_no,
            "%ss" % out.get("seconds"),
            "%d tool calls" % len(out.get("calls") or []),
            "PASS" if head.get("all_pass") else "FAIL",
            row["failed"],
            (out.get("error") or "")[:200],
            flush=True,
        )
    return rows


def token_brief(usage):
    if not usage:
        return "n/a"
    inp = usage.get("input_tokens")
    out = usage.get("output_tokens")
    cached = None
    details = usage.get("input_tokens_details") or usage.get("prompt_tokens_details") or {}
    if isinstance(details, dict):
        cached = details.get("cached_tokens")
    if cached is None:
        cached = usage.get("cache_read_input_tokens")
    return "in %s / out %s / cached %s" % (inp, out, cached)


def write_markdown(path, by_model):
    lines = [
        "# M1.T11 frontier quality check",
        "",
        "Run 2026-10-07 in `beaconmind-ros` (anthropic 1.11.0, openai 3.26.0). K=1 on the four Module 4 smoke scenarios. Prompt, tool schemas, `run_tool`, and `check` are the Module 4 smoke harness. No temperature, top_p, or forced tool_choice was sent.",
        "",
        "Settings from the docs re-read the same day: Sonnet `thinking.type=between_tools` at effort `high`; Opus adaptive thinking (the field omitted) at effort `medium`; Sol Responses `reasoning.effort=none`; Astra Responses `reasoning.effort=high` (`none` is rejected). Fable runs only if both Claude models fail the tool task, meaning no scenario called `compose_odometry` or every scenario errored before a tool call.",
        "",
        "| Model | Pass | Seconds by scenario | Tool called | Failure mode | Tokens |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for model_id, rows in by_model.items():
        passes = sum(1 for row in rows if row.get("all_pass"))
        seconds = ", ".join(
            "%s %s" % (row["scenario"].split("_", 1)[0], row.get("seconds"))
            for row in rows
        )
        tools = ", ".join(
            "%s %s" % (row["scenario"].split("_", 1)[0], "yes" if row.get("tool_called") else "no")
            for row in rows
        )
        modes = []
        for row in rows:
            if row.get("all_pass"):
                continue
            detail = row.get("error") or ", ".join(row.get("failed") or [])
            detail = " ".join(str(detail).split())[:300]
            modes.append("%s: %s" % (row["scenario"].split("_", 1)[0], detail.replace("|", "/")))
        usage = {}
        for row in rows:
            add_usage(usage, row.get("usage") or {})
        lines.append("| `%s` | %d/4 | %s | %s | %s | %s |" % (
            model_id, passes, seconds, tools,
            "; ".join(modes) if modes else "none",
            token_brief(usage),
        ))
    lines += [
        "",
        "Per-scenario records, including the final text and the tool names, are in `quality-records.jsonl`. Thinking signatures are omitted from that file.",
        "",
        "No API key, Authorization header, or secrets file contents were written here.",
        "",
        "AI-assisted: Grok 4.7 via Cursor, 2026-10-07: ran the quality tool-call check.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Frontier quality smoke, four scenarios")
    parser.add_argument("--secrets-file", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--k", type=int, default=1, help="repeats of each scenario; default 1")
    parser.add_argument("--model", default="", help="run only this model id")
    parser.add_argument("--records", default="", help="JSONL path; default quality-records.jsonl")
    parser.add_argument("--markdown", default="", help="markdown path; default quality-results.md when --records is unset")
    args = parser.parse_args()
    if args.k < 1:
        print("k must be >= 1")
        return 1
    if args.k != 1 and not args.model:
        print("k other than 1 requires --model")
        return 1

    sys.path.insert(0, str(TOOLS_DIR))
    import smoke_test

    system_text = load_prompt()
    missing = [name for name in SCENARIO_ORDER if name not in smoke_test.SCENARIOS]
    if missing:
        print("missing scenarios: %s" % missing)
        return 1
    queue = list(MODELS)
    if args.model:
        queue = [spec for spec in MODELS if spec["id"] == args.model]
        if not queue:
            print("model id not in the roster: %s" % args.model)
            return 1
    print("prompt_chars %d scenarios %s tools %d k %d queue %s" % (
        len(system_text), ",".join(SCENARIO_ORDER), len(smoke_test.TOOLS),
        args.k, ",".join(spec["id"] for spec in queue),
    ), flush=True)
    if args.dry_run:
        for spec in queue:
            print(spec["id"], json.dumps(settings_of(spec)))
        return 0
    if not args.secrets_file:
        print("secrets file path missing")
        return 1
    secrets = load_secrets(args.secrets_file)
    openai_key = secrets.get("OPENAI_API_KEY") or ""
    anthropic_key = secrets.get("ANTHROPIC_API_KEY") or ""
    print("keys openai=%s anthropic=%s" % (bool(openai_key), bool(anthropic_key)), flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_path = Path(args.records) if args.records else OUT_DIR / "quality-records.jsonl"
    if args.markdown:
        md_path = Path(args.markdown)
    elif args.records:
        md_path = None
    else:
        md_path = OUT_DIR / "quality-results.md"
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    by_model = {}
    import anthropic
    from openai import OpenAI
    anthropic_client = anthropic.Anthropic(api_key=anthropic_key, timeout=REQUEST_TIMEOUT_S) if anthropic_key else None
    openai_client = OpenAI(api_key=openai_key, timeout=REQUEST_TIMEOUT_S) if openai_key else None
    a_tools = anthropic_tools(smoke_test)
    o_tools = openai_tools(smoke_test)
    index = 0
    with jsonl_path.open("w", encoding="utf-8") as handle:
        while index < len(queue):
            spec = queue[index]
            index += 1
            key_ok = anthropic_key if spec["provider"] == "anthropic" else openai_key
            if not key_ok:
                row = {
                    "model": spec["id"],
                    "scenario": "all",
                    "run": None,
                    "seconds": None,
                    "all_pass": False,
                    "failed": ["not run"],
                    "error": "%s empty; provider skipped" % (
                        "ANTHROPIC_API_KEY" if spec["provider"] == "anthropic" else "OPENAI_API_KEY"
                    ),
                    "skipped": True,
                    "tool_called": False,
                    "compose_odometry_called": False,
                    "tools": [],
                    "n_tool_calls": 0,
                    "usage": {},
                }
                by_model[spec["id"]] = [row]
                handle.write(json.dumps(row) + "\n")
                handle.flush()
                print(row["error"], spec["id"], flush=True)
                continue
            client = anthropic_client if spec["provider"] == "anthropic" else openai_client
            tools = a_tools if spec["provider"] == "anthropic" else o_tools
            rows = run_model(
                spec, client, system_text, tools, smoke_test, secrets, handle, repeats=args.k,
            )
            by_model[spec["id"]] = rows
            if md_path is not None:
                write_markdown(md_path, by_model)
            if (
                not args.model
                and spec["id"] == "claude-opus-5-5"
                and "claude-fable-5-1" not in by_model
            ):
                sonnet_rows = by_model.get("claude-sonnet-5-5") or []
                opus_rows = rows
                if sonnet_rows and failed_tool_task(sonnet_rows) and failed_tool_task(opus_rows):
                    print("both Claude models failed the tool task; adding claude-fable-5-1", flush=True)
                    queue.append(FABLE)
                else:
                    print("fable not run: a Claude model called compose_odometry or was skipped", flush=True)
    if md_path is not None:
        write_markdown(md_path, by_model)
        print("wrote %s" % md_path, flush=True)
    print("wrote %s" % jsonl_path, flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(1)
