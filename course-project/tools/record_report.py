#!/usr/bin/env python3
"""Write a recorded session's README.md and the operator's templates (rule R2; plan task M3.T27). Standard library only.

    python3 course-project/tools/record_report.py <session dir>     # called by record_session.sh stop
    iw dev wlP9s9 station dump | python3 course-project/tools/record_report.py --redact

The README holds what the recorder knows: the session's metadata, what ran (terminal/), the bag's topics and message
counts, the frames, the link (ping gaps), the micro-ROS agent's sessions (a Pico reboot shows as a new one) and every
file with its size and SHA-256 prefix (frames are summarised; each frame's hash is in frames/index.jsonl). It leaves the
motor-battery voltage and the room for the operator, who also fills tape.md and notes.md (made once, never overwritten).
--redact cuts every MAC address to its last three bytes (AGENTS.md §5).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-18: wrote this report.
"""
import hashlib
import json
import os
import re
import sys

MAC = re.compile(r"\b(?:[0-9a-fA-F]{2}:){3}((?:[0-9a-fA-F]{2}:){2}[0-9a-fA-F]{2})\b")
REPLY = re.compile(r"^\[(\d+\.\d+)\] .*icmp_seq=(\d+) .*time=([\d.]+) ms")
NO_ANSWER = re.compile(r"^\[(\d+\.\d+)\] no answer yet for icmp_seq=(\d+)")
SUMMARY = re.compile(r"(\d+) packets transmitted, (\d+) received")
TOPIC = re.compile(r"Topic: (\S+) \| Type: (\S+) \| Count: (\d+)")
ANSI = re.compile(r"\x1b\[[0-9;]*m")  # the micro-ROS agent colours its log


def redact(text):
    return MAC.sub(r"..:\1", text)


def pct(values, q):
    """Nearest-rank percentile (the rule of beaconmind.metrics.latency), None for no values."""
    if not values:
        return None
    s = sorted(values)
    k = max(1, -(-len(s) * q // 100))
    return s[int(k) - 1]


def parse_ping(path):
    if not os.path.exists(path):
        return None
    times, rtts, seqs, missed = [], [], set(), set()
    sent = received = None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = REPLY.match(line)
            if m:
                times.append(float(m.group(1)))
                seqs.add(int(m.group(2)))
                rtts.append(float(m.group(3)))
                continue
            m = NO_ANSWER.match(line)
            if m:
                missed.add(int(m.group(2)))
            m = SUMMARY.search(line)
            if m:
                sent, received = int(m.group(1)), int(m.group(2))
    if sent is None:  # no summary (ping killed hard): count what was seen
        sent = max(seqs | missed) if (seqs or missed) else 0
        received = len(seqs)
    gaps = [b - a for a, b in zip(times, times[1:])]
    return {"sent": sent, "received": received, "loss_pct": round(100.0 * (sent - received) / sent, 2) if sent else None,
            "rtt_ms_p50": pct(rtts, 50), "rtt_ms_p99": pct(rtts, 99), "rtt_ms_max": max(rtts) if rtts else None,
            "longest_gap_s": round(max(gaps), 3) if gaps else None, "gaps_over_0_5_s": sum(g > 0.5 for g in gaps)}


def parse_bag_info(path):
    if not os.path.exists(path):
        return None
    text = open(path, encoding="utf-8", errors="replace").read()
    out = {"topics": [(m.group(1), m.group(2), int(m.group(3))) for m in TOPIC.finditer(text)]}
    for key in ("Duration", "Messages", "Bag size", "Storage id"):
        m = re.search(r"^%s:\s+(.+)$" % key, text, re.M)
        out[key] = m.group(1).strip() if m else None
    return out


def frames_summary(frames_dir):
    path = os.path.join(frames_dir, "index.jsonl")
    if not os.path.exists(path):
        return None
    ok, errors, lat, sizes, total = [], 0, [], {}, 0
    for line in open(path, encoding="utf-8"):
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if "error" in rec:
            errors += 1
            continue
        ok.append(rec["t_resp_ns"])
        lat.append(rec["latency_ms"])
        total += rec.get("bytes", 0)
        h = rec.get("headers", {})
        key = "%sx%s" % (h.get("x-bm-width", "?"), h.get("x-bm-height", "?"))
        sizes[key] = sizes.get(key, 0) + 1
    span = (max(ok) - min(ok)) / 1e9 if len(ok) > 1 else 0
    return {"saved": len(ok), "errors": errors, "fps": round((len(ok) - 1) / span, 2) if span else None,
            "latency_ms_p50": pct(lat, 50), "latency_ms_p95": pct(lat, 95), "sizes": sizes, "bytes": total}


def agent_sessions(path):
    if not os.path.exists(path):
        return None
    lines = [ANSI.sub("", l) for l in open(path, encoding="utf-8", errors="replace") if "session established" in l]
    return {"established": len(lines), "lines": [redact(" ".join(l.split()))[:160] for l in lines[-10:]]}


def terminal_runs(term_dir):
    runs = []
    if not os.path.isdir(term_dir):
        return runs
    for name in sorted(os.listdir(term_dir)):
        info = {"file": name}
        with open(os.path.join(term_dir, name), encoding="utf-8", errors="replace") as fh:
            for line in fh:
                for key in ("cmd", "start", "end", "exit"):
                    if line.startswith("# %s: " % key):
                        info[key] = line[len("# %s: " % key):].strip()
        runs.append(info)
    return runs


def sha12(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()[:12]


def inventory(session):
    rows, frames = [], [0, 0]
    for root, _dirs, files in os.walk(session):
        for f in sorted(files):
            p = os.path.join(root, f)
            rel = os.path.relpath(p, session)
            if os.path.islink(p):
                continue
            if rel.startswith("frames" + os.sep) and f.endswith(".jpg"):
                frames[0] += 1
                frames[1] += os.path.getsize(p)
                continue
            if rel in ("README.md",):
                continue
            rows.append((rel, os.path.getsize(p), sha12(p)))
    return sorted(rows), frames


def fmt(v, unit=""):
    return "—" if v is None else "%s%s" % (v, unit)


def load_json(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_templates(session, meta):
    tape = os.path.join(session, "tape.md")
    if not os.path.exists(tape):
        with open(tape, "w", encoding="utf-8") as fh:
            fh.write("# Tape readings — session %s\n\nOne row per reading, taken by the operator. Distances in cm unless "
                     "the unit says otherwise.\n\n| Time | What was measured | From | Reading | Unit | Who | Note |\n"
                     "| --- | --- | --- | --- | --- | --- | --- |\n|  |  |  |  |  |  |  |\n" % meta.get("id", "?"))
    notes = os.path.join(session, "notes.md")
    if not os.path.exists(notes):
        with open(notes, "w", encoding="utf-8") as fh:
            fh.write("# Operator notes — session %s\n\n- Motor battery before / after (multimeter): ____ V / ____ V\n"
                     "- Car placement and start pose:\n- What happened, in order:\n- Anything unusual (a reboot, a touch, "
                     "a person in view, light changes):\n" % meta.get("id", "?"))


def write_readme(session):
    meta = load_json(os.path.join(session, "meta", "session.json"))
    stop = load_json(os.path.join(session, "meta", "stop.json"))
    cam = load_json(os.path.join(session, "meta", "camera_status_start.json"))
    bag = parse_bag_info(os.path.join(session, "meta", "bag_info.txt"))
    frames = frames_summary(os.path.join(session, "frames"))
    pings = {k: parse_ping(os.path.join(session, "logs", "ping_%s.txt" % k)) for k in ("car", "cam")}
    agent = agent_sessions(os.path.join(session, "logs", "micro_ros_agent.log"))
    agent_before = agent_sessions(os.path.join(session, "logs", "micro_ros_agent_before.log"))
    runs = terminal_runs(os.path.join(session, "terminal"))
    write_templates(session, meta)
    rows, nframes = inventory(session)
    L = ["# Session %s" % meta.get("id", os.path.basename(session.rstrip(os.sep))), "",
         "Recorded under rule R2 (plan/README.md §3.6) by `tools/record_session.sh` (plan task M3.T27). Generated by "
         "`tools/record_report.py`; the operator fills `tape.md` and `notes.md`.", "",
         "| Field | Value |", "| --- | --- |",
         "| Purpose | %s%s |" % (meta.get("label", "—"), (": " + meta["note"]) if meta.get("note") else ""),
         "| Operator | %s |" % (meta.get("operator") or "____ (fill in)"),
         "| Start (local) | %s |" % meta.get("start_local", "—"),
         "| End (local) | %s (%s) |" % (stop.get("end_local", "—"), stop.get("reason", "—")),
         "| Host, repository | %s, commit %s%s |" % (meta.get("host", "—"), meta.get("git_commit", "—"),
                                                     " with uncommitted changes" if meta.get("git_dirty") else ""),
         "| Pico firmware | %s (documented build; K2 does not publish a build id, and only this build joins the access "
         "point) |" % meta.get("pico_build", "—"),
         "| Camera | %s at %s; %s |" % (cam.get("fw", "not reached"), meta.get("camera_ip") or "—",
                                       ", ".join("%s %s" % (k, cam[k]) for k in ("framesize", "quality", "rssi") if k in cam) or "—"),
         "| Car on the network | %s |" % (meta.get("car_ip") or "not seen at start"),
         "| Motor battery | ____ V before, ____ V after (multimeter; the firmware does not measure it) |",
         "| Room and floor | ____ (the arena room: `evidence/M3/M3.T10/`) |",
         "| Clock | Spark NTP synchronised: %s. Film `tools/session_clock.py` at the start of every phone video. |"
         % meta.get("ntp_synced", "—"), ""]
    L += ["## What ran", ""]
    if runs:
        L += ["| Log | Command | Start | Exit |", "| --- | --- | --- | --- |"]
        L += ["| `terminal/%s` | `%s` | %s | %s |" % (r["file"], r.get("cmd", "?")[:120], r.get("start", "?"), r.get("exit", "?"))
              for r in runs]
    else:
        L += ["No command was run through `record_session.sh run`."]
    L += ["", "## Captures", ""]
    if bag and bag["topics"]:
        L += ["**Bag** (`bag/`, %s): %s, %s messages." % (bag.get("Storage id"), bag.get("Duration"), bag.get("Messages")), "",
              "| Topic | Type | Messages |", "| --- | --- | --- |"]
        L += ["| `%s` | `%s` | %d |" % t for t in sorted(bag["topics"])]
        L += ["", "The bag holds every topic that has a publisher. Topics the car only subscribes to (its inputs "
              "`/pico/cmd_vel` and `/pico/imu/std`) appear once something publishes them."]
    else:
        L += ["**Bag:** no topic recorded (see `logs/rosbag.log` and `meta/bag_info.txt`)."]
    L += [""]
    if frames:
        L += ["**Frames** (`frames/`): %d saved, %d failed requests, %s frames/s, latency p50 %s ms / p95 %s ms, sizes %s, "
              "%.1f MB." % (frames["saved"], frames["errors"], fmt(frames["fps"]), fmt(frames["latency_ms_p50"]),
                            fmt(frames["latency_ms_p95"]), ", ".join("%s × %d" % kv for kv in sorted(frames["sizes"].items())) or "—",
                            frames["bytes"] / 1e6)]
    else:
        L += ["**Frames:** not recorded by the recorder (`--camera off`, or no camera)."]
    for key, name in (("car", "car"), ("cam", "camera")):
        p = pings[key]
        if p:
            L += ["", "**Link to the %s** (`logs/ping_%s.txt`, 5 pings a second): %s sent, %s received (loss %s %%), "
                  "round trip p50 %s ms, p99 %s ms, max %s ms; longest gap between replies %s s; %d gaps over 0.5 s."
                  % (name, key, p["sent"], p["received"], fmt(p["loss_pct"]), fmt(p["rtt_ms_p50"]), fmt(p["rtt_ms_p99"]),
                     fmt(p["rtt_ms_max"]), fmt(p["longest_gap_s"]), p["gaps_over_0_5_s"])]
    if agent is not None:
        L += ["", "**micro-ROS agent** (`logs/micro_ros_agent.log`): %d session(s) established during the recording "
              "(each is the Pico joining; any here means it reconnected or rebooted mid-session)." % agent["established"]]
    if agent_before is not None:
        L += ["", "Before the recording (`logs/micro_ros_agent_before.log`, the agent's last 200 lines): %d session(s) "
              "established%s." % (agent_before["established"],
                                  ", the last: `%s`" % agent_before["lines"][-1][:110] if agent_before["lines"] else "")]
    L += ["", "## Files", "", "%d frames, %.1f MB in `frames/` (hashes in `frames/index.jsonl`)." % (nframes[0], nframes[1] / 1e6), "",
          "| File | Bytes | SHA-256 (12) |", "| --- | --- | --- |"]
    L += ["| `%s` | %d | `%s` |" % r for r in rows]
    with open(os.path.join(session, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    return os.path.join(session, "README.md")


def main(argv):
    if argv and argv[0] == "--redact":
        for line in sys.stdin:
            sys.stdout.write(redact(line))
        sys.stdout.flush()
        return 0
    if len(argv) != 1 or not os.path.isdir(argv[0]):
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    print(write_readme(argv[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
