"""Replay harness for the L2 agent on the Anthropic Messages API (the pilot's LLM arm).

One stateless call per observation (AGENT-DESIGN D5, D10): the step message carries the mission,
the OBSERVATION and the agent's own PREVIOUS_REPORT; the agent calls the D5 tools, which
tools_d5.run_tool answers; its final text is the D8 report. In replay mode the moves are the
logged ones and the agent only estimates. The harness keeps the per-arm counters
(kinsim_lite.CounterTracker) and, when a report is invalid, carries the last valid report forward
with its pose dead-reckoned through the odometry (logged as `fallback`).

Request settings are those of the 2026-10-07 Opus K=5 run (evidence/M1/M1.T11/opus20-comparison.md):
claude-opus-5-5, adaptive thinking (field omitted), output_config.effort medium, max_tokens 64000,
no temperature, no forced tool choice. Prompt caching: one cache breakpoint at the end of the system
prompt (it covers tools and system) and one on the last block of the newest user turn, so each tool
turn reads the conversation so far from the cache.
Derived from: course-project/tools/quality_smoke.py run_anthropic_scenario (same loop), with
caching, retries, a spend cap, resumable logs and the multi-step replay added.

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: wrote the multi-step replay harness.
"""
import copy
import json
import threading
import time

from beaconmind import geometry as g
from beaconmind.envs import kinsim_lite as ks
from beaconmind.harness import tools_d5 as t5

SETTINGS = {"model": "claude-opus-5-5", "max_tokens": 64000, "output_config": {"effort": "medium"}}
# USD per million tokens (configs/providers.json and evidence/M1/M1.T11/model-candidates.md, checked 2026-10-07)
PRICE = {"input": 4.0, "cache_write_5m": 5.0, "cache_read": 0.20, "output": 20.0}
MAX_TURNS = 30
RETRY_STATUS = (408, 409, 429, 500, 502, 503, 504, 529)


class Budget:
    def __init__(self, cap_usd, spent=0.0):
        self.cap, self.spent, self.lock = cap_usd, spent, threading.Lock()

    def add(self, usd):
        with self.lock:
            self.spent += usd
            return self.spent

    def exceeded(self):
        with self.lock:
            return self.spent >= self.cap


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
        wait = min(120, 5 * 2 ** attempt)
        log("retry in %ds (%s)" % (wait, reason))
        time.sleep(wait)
    raise RuntimeError("API retries exhausted")


def agent_step(client, system_blocks, tools, obs, prev, budget, log):
    """One observation: the tool loop until a final text. Returns the step record fields."""
    user = json.dumps({"mission": "EXPLORE", "operator_request": None, "OBSERVATION": obs, "PREVIOUS_REPORT": prev})
    messages = [{"role": "user", "content": [{"type": "text", "text": user}]}]
    state = {"moved": None, "estop": False}
    calls, turns, t0 = [], [], time.perf_counter()
    final, error = None, None
    for _ in range(MAX_TURNS):
        if budget.exceeded():
            error = "budget cap reached"
            break
        kwargs = dict(SETTINGS, system=system_blocks, tools=tools, messages=_with_breakpoint(messages))
        resp, dt = _call(client, kwargs, log)
        u = _usage(resp)
        cost = turn_cost(u)
        budget.add(cost)
        content = list(resp.content)
        turns.append({"seconds": dt, "stop_reason": resp.stop_reason, "usage": u, "cost_usd": round(cost, 5),
                      "model": getattr(resp, "model", None),
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
                res = t5.rnd(t5.run_tool(b.name, args, obs, prev, state))
                calls.append({"tool": b.name, "args": args, "result": res})
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


def fallback_report(last_valid, odo, step):
    """Last valid report with its pose dead-reckoned through this step's odometry."""
    rep = copy.deepcopy(last_valid) if last_valid else {"pose": {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0},
                                                         "map": [], "memory": ks.initial_memory()}
    if odo:
        p = g.compose_odometry(rep["pose"], odo["forward_m"], odo["left_m"], odo["dtheta_deg"])
        rep["pose"] = ks.rp(p)
    rep.update(step=step, pose_source="odometry", associations=[], loop_closure=[], decision="NONE",
               note="harness fallback: the agent's report was invalid")
    return rep


def replay_seed(client, system_text, log_doc, out_path, budget, max_steps, log=print):
    """Replay one recorded episode through the agent, appending one JSON line per step to out_path.
    Resumes after the last step already in out_path."""
    seed = log_doc["seed"]
    system_blocks = [{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}]
    tools = t5.anthropic_tool_defs()
    done = []
    try:
        with open(out_path, encoding="utf-8") as fh:
            done = [json.loads(line) for line in fh if line.strip()]
    except FileNotFoundError:
        pass
    tracker = ks.CounterTracker()
    prev, last_valid, prev_source = None, None, None
    for rec in done:
        tracker.before_step(rec["raw"], prev_source)
        prev = rec["next_prev"]
        last_valid = rec["last_valid"]
        prev_source = rec["prev_source_for_counters"]
    records = log_doc["records"][:max_steps]
    with open(out_path, "a", encoding="utf-8") as fh:
        for rec in records[len(done):]:
            if budget.exceeded():
                log("seed %s: budget cap reached before step %d" % (seed, rec["step"]))
                return False
            counters = tracker.before_step(rec["raw"], prev_source)
            obs = ks.as_observation(seed, rec["raw"], counters, mode="replay")
            out = agent_step(client, system_blocks, tools, obs, prev, budget, lambda m: log("seed %s step %d: %s" % (seed, rec["step"], m)))
            if out["error"] == "budget cap reached":
                # a harness-side abort: leave the step unwritten so a resume re-runs it
                log("seed %s: budget cap reached during step %d; step not written" % (seed, rec["step"]))
                return False
            rep = t5.parse_report(out["final_text"])
            checks = t5.report_checks(rep, obs)
            if checks["valid"]:
                estimate, next_prev, fallback = rep, rep, False
                last_valid = rep
            else:
                estimate = fallback_report(prev, rec["raw"]["odometry"], rec["step"])
                next_prev, fallback = estimate, True
            prev_source = estimate.get("pose_source")
            row = {"seed": seed, "step": rec["step"], "arm": "L2:" + SETTINGS["model"], "truth": rec["truth"],
                   "raw": rec["raw"], "observation": obs, "prev_report": prev, "report": rep, "checks": checks,
                   "fallback": fallback, "estimate_pose": estimate["pose"], **out,
                   "next_prev": next_prev, "last_valid": last_valid, "prev_source_for_counters": prev_source}
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            log("seed %s step %d: %.1fs %d calls $%.3f valid=%s fallback=%s total=$%.2f %s" % (
                seed, rec["step"], out["seconds"], len(out["calls"]), out["cost_usd"], checks["valid"], fallback,
                budget.spent, out["error"] or ""))
            prev = next_prev
    return True
