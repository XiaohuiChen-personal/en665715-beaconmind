#!/usr/bin/env python3
"""Re-run one logged pilot step with the full transcript kept (thinking summaries, text, tool calls and
results), for the report's example ReAct trace. Same inputs, prompt, tools and settings as the pilot.

Run inside beaconmind-ros with the secrets env_file (see pilot_replay.py):
  python3 tools/pilot_trace.py --run data/pilot-20261029/opus --pick --out evidence/M4/M4.T11/trace_example.json
--pick chooses the first step (seeds in order) whose report creates a duplicated-ID label (B<id>b) while
matching a confirmed beacon, with at most 6 tool calls; --seed/--step choose a step directly.

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: wrote this script.
"""
import argparse
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "beaconmind" / "src"))
sys.path.insert(0, str(ROOT / "tools"))
from beaconmind.harness import anthropic_replay as ar  # noqa: E402
from beaconmind.harness import tools_d5 as t5  # noqa: E402
from pilot_judge import load_rows  # noqa: E402


def pick(rows):
    """First match of, in order: a duplicated-ID new label with a fix; a duplicated-ID new label; a fix."""
    def dup_new(r):
        return any(a.get("result") == "new" and str(a.get("beacon", "")).endswith("b") for a in (r["report"] or {}).get("associations") or [])

    def fixed(r):
        return (r["report"] or {}).get("pose_source") in ("beacon_fix", "position_fix")
    ordered = sorted(rows, key=lambda r: (r["seed"], r["step"]))
    for test in (lambda r: dup_new(r) and fixed(r), dup_new, fixed):
        for r in ordered:
            if test(r) and len(r["calls"]) <= 6:
                return r
    raise SystemExit("no step matches --pick")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pick", action="store_true")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--step", type=int)
    args = ap.parse_args()
    rows = load_rows(args.run)
    row = pick(rows) if args.pick else next(r for r in rows if r["seed"] == args.seed and r["step"] == args.step)
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], timeout=900, max_retries=2)
    system_text = (ROOT / "prompts" / "robot_system_prompt_v3.3.txt").read_text(encoding="utf-8")
    system_blocks = [{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}]
    obs, prev = row["observation"], row["prev_report"]
    user = json.dumps({"mission": "EXPLORE", "operator_request": None, "OBSERVATION": obs, "PREVIOUS_REPORT": prev})
    messages = [{"role": "user", "content": [{"type": "text", "text": user}]}]
    state, transcript = {"moved": None, "estop": False}, []
    for _ in range(ar.MAX_TURNS):
        # display "summarized" returns the thinking text; the pilot runs left it unset (empty thinking text)
        resp, dt = ar._call(client, dict(ar.SETTINGS, thinking={"type": "adaptive", "display": "summarized"},
                                         system=system_blocks, tools=t5.anthropic_tool_defs(),
                                         messages=ar._with_breakpoint(messages)), print)
        content = list(resp.content)
        turn = {"seconds": dt, "blocks": []}
        for b in content:
            if b.type == "thinking":
                turn["blocks"].append({"type": "thinking", "text": b.thinking})
            elif b.type == "text":
                turn["blocks"].append({"type": "text", "text": b.text})
            elif b.type == "tool_use":
                turn["blocks"].append({"type": "tool_use", "name": b.name, "input": b.input})
        uses = [b for b in content if b.type == "tool_use"]
        transcript.append(turn)
        if not uses:
            break
        messages.append({"role": "assistant", "content": [ar._block(b) for b in content]})
        results = []
        for b in uses:
            res = t5.rnd(t5.run_tool(b.name, b.input if isinstance(b.input, dict) else {}, obs, prev, state))
            turn["blocks"].append({"type": "tool_result", "name": b.name, "result": res})
            results.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(res)})
        messages.append({"role": "user", "content": results})
    final = "\n".join(bl["text"] for bl in transcript[-1]["blocks"] if bl["type"] == "text")
    out = {"seed": row["seed"], "step": row["step"], "truth": row["truth"], "observation": obs,
           "prev_report_pose": (prev or {}).get("pose"), "transcript": transcript, "final_report": t5.parse_report(final),
           "logged_report": row["report"], "settings": ar.SETTINGS}
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.out).write_text(json.dumps(out, indent=1))
    print("seed %d step %d: %d turns; final pose %s (logged %s); note: %s" % (
        row["seed"], row["step"], len(transcript), (out["final_report"] or {}).get("pose"), row["report"]["pose"],
        (out["final_report"] or {}).get("note")))


if __name__ == "__main__":
    main()
