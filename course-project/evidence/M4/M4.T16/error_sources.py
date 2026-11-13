#!/usr/bin/env python3
"""Where each LLM arm's pose error comes from (post-hoc, exploratory; not part of the pre-registered analysis).

Written after the confirmatory analysis, because Gemma 4's ATE (median 69 cm) was four times dead reckoning's and
the plan asks for a bug check when a result is that surprising (plan/M4-benchmark.md M4.T16, stop-and-ask). It
reads the run logs only and changes nothing. Per arm, over all 30 seeds:
  1. parsing, checked independently of the harness's parser (which produced the scored pose, so re-running it would
     be circular): the final text's shape (bare JSON object / exactly one fenced JSON block / other), every
     top-level JSON object in it found with json.JSONDecoder.raw_decode, and whether the scored pose equals the pose
     of the only object that has one (a missing or non-finite value counts as a mismatch);
  2. step kinds: no tool call / tools without a successful fix_pose / a successful fix_pose / fallback, and each
     seed's final position error split by the kind of step on which it grew (the per-step changes of the position
     error against the simulator's truth telescope, so the four sums add up to 30 times the mean final position
     error; this splits the final error, not the ATE);
  3. pose jumps: non-fallback steps whose reported position is more than 5 cm from the harness prior (the previous
     report dead-reckoned through this step's odometry) with no successful fix_pose in the step;
  4. tool calls: calls with an empty object argument ({}), steps without a tool call whose final text contains
     tool-call markup (a call the server's parser could have missed), and the most frequent tool-error messages
     (numbers replaced by #).

Run from the repository root (stdlib only):
  python3 course-project/evidence/M4/M4.T16/error_sources.py \
      course-project/data/main/runs/drift2 > course-project/evidence/M4/M4.T16/error_sources.txt

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-13: wrote this check after the analysis and revised it after
the adversarial review the same day (the first version re-ran the harness's parser and could not flag a missing pose).
"""
import collections
import json
import math
import pathlib
import re
import sys

ARMS = ["claude-opus-5-5", "qwen38-flash-xhigh", "gemma4-26b"]
SEEDS = range(2000, 2030)
FENCE = re.compile(r"^\s*```(?:json)?\s*\n(.*?)\n?```\s*$", re.S)
MARKUP = re.compile(r"tool_call|<\|tool|\bcall:\w")


def rows(path):
    out, seen = [], set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if r["step"] not in seen:
                seen.add(r["step"])
                out.append(r)
    return sorted(out, key=lambda r: r["step"])


def dist(a, b):
    return math.hypot(a["x_m"] - b["x_m"], a["y_m"] - b["y_m"])


def top_level_objects(text):
    """Every top-level JSON object in the text, scanning from each '{' not inside an object already decoded."""
    dec, out, i = json.JSONDecoder(), [], 0
    while True:
        i = text.find("{", i)
        if i < 0:
            return out
        try:
            obj, end = dec.raw_decode(text, i)
        except ValueError:
            i += 1
            continue
        if isinstance(obj, dict):
            out.append(obj)
        i = end


def shape(text):
    t = text.strip()
    if t.startswith("{") and t.endswith("}"):
        return "bare JSON object"
    return "one fenced JSON block" if FENCE.match(t) else "other"


def same_pose(pose, scored):
    try:
        return all(math.isfinite(float(pose[k])) and abs(float(pose[k]) - float(scored[k])) <= 1e-9
                   for k in ("x_m", "y_m", "theta_deg"))
    except (KeyError, TypeError, ValueError):
        return False


def main(runs):
    runs = pathlib.Path(runs)
    for arm in ARMS:
        kinds, growth, errors = collections.Counter(), collections.defaultdict(float), collections.Counter()
        shapes, parse = collections.Counter(), collections.Counter()
        jumps, steps, empty_args, markup, final_err = 0, 0, 0, 0, 0.0
        for seed in SEEDS:
            prev_err = 0.0
            for r in rows(runs / arm / ("seed_%d.jsonl" % seed)):
                steps += 1
                calls = r.get("calls") or []
                ok_fix = any(c.get("tool") == "fix_pose" and (c.get("result") or {}).get("status") == "ok"
                             for c in calls)
                text = r.get("final_text") or ""
                if r["fallback"]:
                    kind = "fallback"
                else:
                    kind = "no tool call" if not calls else ("successful fix_pose" if ok_fix else "tools, no fix")
                    shapes[shape(text)] += 1
                    with_pose = [o for o in top_level_objects(text) if isinstance(o.get("pose"), dict)]
                    if len(with_pose) != 1:
                        parse["not exactly one object with a pose"] += 1
                    elif not same_pose(with_pose[0]["pose"], r["estimate_pose"]):
                        parse["pose differs from the scored pose"] += 1
                    else:
                        parse["matches the scored pose"] += 1
                    if r.get("harness_prior") and dist(r["estimate_pose"], r["harness_prior"]) > 0.05 and not ok_fix:
                        jumps += 1
                if not calls and MARKUP.search(text):
                    markup += 1
                for c in calls:
                    if any(v == {} for v in (c.get("args") or {}).values()):
                        empty_args += 1
                    res = c.get("result") or {}
                    if res.get("status") == "error":
                        errors[(c.get("tool"), re.sub(r"-?\d+(\.\d+)?", "#", str(res.get("error")))[:80])] += 1
                err = dist(r["estimate_pose"], r["truth"])
                kinds[kind] += 1
                growth[kind] += err - prev_err
                prev_err = err
            final_err += prev_err
        valid = steps - kinds["fallback"]
        print("== %s: %d steps, %d with a valid report" % (arm, steps, valid))
        print("  final text: " + ", ".join("%s %d" % kv for kv in sorted(shapes.items())))
        print("  independent parse: " + ", ".join("%s %d" % kv for kv in sorted(parse.items())))
        print("  final position error split by step kind (sums to %.2f m = 30 x mean final error %.2f m):"
              % (sum(growth.values()), final_err / 30))
        for kind in ("no tool call", "tools, no fix", "successful fix_pose", "fallback"):
            if kinds[kind]:
                share = "%4.1f %% of valid" % (100 * kinds[kind] / valid) if kind != "fallback" else "-"
                print("    %-20s %5d steps (%4.1f %% of all, %s), %+7.2f m, %+6.2f cm per step"
                      % (kind, kinds[kind], 100 * kinds[kind] / steps, share, growth[kind],
                         100 * growth[kind] / kinds[kind]))
        print("  jumps > 5 cm from the harness prior without a successful fix_pose: %d" % jumps)
        print("  calls with an empty object argument: %d; tool-free steps whose text has tool-call markup: %d"
              % (empty_args, markup))
        print("  tool-error results: %d; most frequent:" % sum(errors.values()))
        for (tool, msg), n in errors.most_common(5):
            print("    %4d %-17s %s" % (n, tool, msg))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
