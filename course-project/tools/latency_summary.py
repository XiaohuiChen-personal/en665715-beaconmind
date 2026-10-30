#!/usr/bin/env python3
"""Summarize smoke-harness JSONL decision latencies and a vLLM queue-probe log.

Reads one or more JSONL files written by assignments/assignment4/system-prompt/tools/smoke_test.py.
Latency per decision is the record's seconds field (wall time of step()). Records are
grouped by the thinking field. Length and context-overflow attempts stay in the
percentile (they are real decision attempts); their seconds are also listed in
length_or_overflow_s.

The probe log lines are "<epoch> running=<n> waiting=<n>" or "running=NA waiting=NA".
max_running and max_waiting are the maxima over numeric samples in the whole probe log
(the window that covers both sequential modes).

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the JSONL and queue-probe summary.
"""
import argparse
import csv
import json
import sys

from beaconmind.metrics.latency import summarize_latencies

COLUMNS = (
    "mode",
    "n",
    "p50_s",
    "p95_s",
    "max_s",
    "mean_turns",
    "mean_tool_calls",
    "mean_prompt_tokens_first_turn",
    "mean_completion_tokens_total",
    "n_errors",
    "n_all_pass",
    "n_length_or_overflow",
    "length_or_overflow_s",
    "first_record_s",
)


def _mode_name(thinking):
    if thinking == 1 or thinking is True:
        return "thinking-on"
    if thinking == 0 or thinking is False:
        return "thinking-off"
    return "thinking-{0}".format(thinking)


def _mean(nums):
    if not nums:
        return ""
    return sum(nums) / len(nums)


def _fmt(value):
    if value == "" or value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        text = "{0:.6f}".format(value).rstrip("0").rstrip(".")
        return text if text else "0"
    return str(value)


def _usage_number(usage, key):
    if not isinstance(usage, dict):
        return None
    value = usage.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _is_length_or_overflow(error):
    text = error if isinstance(error, str) else ""
    return text.startswith("length") or text.startswith("context overflow")


def load_records(paths):
    groups = []
    seen = {}
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise SystemExit("{0}:{1}: {2}".format(path, line_no, exc))
                if not isinstance(rec, dict) or "seconds" not in rec:
                    raise SystemExit("{0}:{1}: record has no seconds field".format(path, line_no))
                thinking = rec.get("thinking")
                mode = _mode_name(thinking)
                if mode not in seen:
                    seen[mode] = []
                    groups.append(mode)
                seen[mode].append(rec)
    return [(mode, seen[mode]) for mode in groups]


def summarize_mode(mode, records):
    seconds = []
    turns = []
    tool_calls = []
    prompt_first = []
    completion_total = []
    n_errors = 0
    n_all_pass = 0
    overflow_seconds = []
    for rec in records:
        seconds.append(rec["seconds"])
        turn_list = rec.get("turns") if isinstance(rec.get("turns"), list) else []
        turns.append(len(turn_list))
        calls = rec.get("calls") if isinstance(rec.get("calls"), list) else []
        tool_calls.append(len(calls))
        if turn_list:
            prompt = _usage_number(turn_list[0].get("usage"), "prompt_tokens")
            if prompt is not None:
                prompt_first.append(prompt)
        total_completion = 0.0
        saw_completion = False
        for turn in turn_list:
            if not isinstance(turn, dict):
                continue
            completion = _usage_number(turn.get("usage"), "completion_tokens")
            if completion is not None:
                total_completion += completion
                saw_completion = True
        if saw_completion:
            completion_total.append(total_completion)
        error = rec.get("error")
        if error:
            n_errors += 1
        if _is_length_or_overflow(error):
            overflow_seconds.append(rec["seconds"])
        check = rec.get("check") if isinstance(rec.get("check"), dict) else {}
        if check.get("all_pass") is True:
            n_all_pass += 1
    stats = summarize_latencies(seconds)
    return {
        "mode": mode,
        "n": stats["n"],
        "p50_s": stats["p50"],
        "p95_s": stats["p95"],
        "max_s": stats["max"],
        "mean_turns": _mean(turns),
        "mean_tool_calls": _mean(tool_calls),
        "mean_prompt_tokens_first_turn": _mean(prompt_first),
        "mean_completion_tokens_total": _mean(completion_total),
        "n_errors": n_errors,
        "n_all_pass": n_all_pass,
        "n_length_or_overflow": len(overflow_seconds),
        "length_or_overflow_s": ";".join(_fmt(s) for s in overflow_seconds),
        "first_record_s": seconds[0],
    }


def parse_probe(path):
    running_vals = []
    waiting_vals = []
    n_samples = 0
    n_na = 0
    first_epoch = None
    last_epoch = None
    first_line = ""
    last_line = ""
    with open(path, encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 3 or not parts[0].isdigit():
                raise SystemExit("{0}:{1}: unparsed probe line {2!r}".format(path, line_no, line))
            epoch = int(parts[0])
            if first_epoch is None:
                first_epoch = epoch
                first_line = line
            last_epoch = epoch
            last_line = line
            n_samples += 1
            run_tok = parts[1].split("=", 1)
            wait_tok = parts[2].split("=", 1)
            if len(run_tok) != 2 or run_tok[0] != "running" or len(wait_tok) != 2 or wait_tok[0] != "waiting":
                raise SystemExit("{0}:{1}: unparsed probe line {2!r}".format(path, line_no, line))
            if run_tok[1] == "NA" or wait_tok[1] == "NA":
                n_na += 1
                continue
            try:
                running_vals.append(int(float(run_tok[1])))
                waiting_vals.append(int(float(wait_tok[1])))
            except ValueError:
                raise SystemExit("{0}:{1}: non-numeric probe counts {2!r}".format(path, line_no, line))
    def _max(vals):
        return max(vals) if vals else "NA"
    return {
        "max_running": _max(running_vals),
        "max_waiting": _max(waiting_vals),
        "probe_samples": n_samples,
        "probe_na": n_na,
        "probe_numeric": len(running_vals),
        "probe_first_epoch": "" if first_epoch is None else first_epoch,
        "probe_last_epoch": "" if last_epoch is None else last_epoch,
        "probe_first_line": first_line,
        "probe_last_line": last_line,
    }


def main(argv):
    parser = argparse.ArgumentParser(description="Summarize smoke JSONL latencies and a vLLM queue probe.")
    parser.add_argument("jsonl", nargs="+", help="smoke_test.py JSONL files")
    parser.add_argument("--probe", required=True, help="vllm_queue_probe.sh log")
    parser.add_argument("--out", required=True, help="CSV path to write")
    args = parser.parse_args(argv)
    rows = [summarize_mode(mode, records) for mode, records in load_records(args.jsonl)]
    if not rows:
        raise SystemExit("no JSONL records")
    probe = parse_probe(args.probe)
    with open(args.out, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _fmt(row[key]) for key in COLUMNS})
    for row in rows:
        print(" ".join("{0}={1}".format(key, _fmt(row[key])) for key in COLUMNS))
    print("max_running={0}".format(probe["max_running"]))
    print("max_waiting={0}".format(probe["max_waiting"]))
    print("probe_samples={0}".format(probe["probe_samples"]))
    print("probe_na={0}".format(probe["probe_na"]))
    print("probe_numeric={0}".format(probe["probe_numeric"]))
    print("probe_first_epoch={0}".format(probe["probe_first_epoch"]))
    print("probe_last_epoch={0}".format(probe["probe_last_epoch"]))
    print("probe_first_line={0}".format(probe["probe_first_line"]))
    print("probe_last_line={0}".format(probe["probe_last_line"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
