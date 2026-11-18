#!/usr/bin/env python3
"""Save every camera frame of a recorded session (rule R2; plan task M3.T27). Spark host, standard library only.

    python3 course-project/tools/record_frames.py --base http://10.42.0.89 --out <session>/frames [--fps 5]

Asks bm_cam-0.2 for one frame after another (GET /capture) and keeps each JPEG exactly as received, named
<n>_<host receive time in ns>.jpg. frames/index.jsonl gets one line per request: request and response times (host
wall clock, ns), latency, size, SHA-256 prefix and the X-BM-* headers (camera sequence number, capture time,
width, height), or the error. frames/status.jsonl gets the camera's /status every --status-every seconds.
frames/latest.jpg always points at the newest frame, so a live viewer (calibration) reads that file instead of
opening a second connection: the camera serves one request at a time. SIGINT or SIGTERM ends the loop and prints a
summary line.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-18: wrote this frame saver.
"""
import argparse
import hashlib
import json
import os
import signal
import sys
import time
import urllib.error
import urllib.request

STOP = False


def _stop(_signum, _frame):
    global STOP
    STOP = True


def bm_headers(headers):
    """The X-BM-* headers, lower-cased, numbers as int where they parse."""
    out = {}
    for key, value in headers.items():
        k = str(key).lower()
        if k.startswith("x-bm-"):
            try:
                out[k] = int(value)
            except ValueError:
                out[k] = value
    return out


def frame_name(n, t_ns):
    return "%06d_%d.jpg" % (n, t_ns)


def grab(url, timeout):
    """(status, headers, body) of one GET."""
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.status, dict(resp.headers.items()), resp.read()


def point_latest(out_dir, name):
    tmp = os.path.join(out_dir, ".latest.tmp")
    try:
        os.remove(tmp)
    except FileNotFoundError:
        pass
    os.symlink(name, tmp)
    os.replace(tmp, os.path.join(out_dir, "latest.jpg"))


def run(base, out_dir, fps, status_every, timeout, max_seconds, grabber=grab, clock=time.time_ns, sleep=time.sleep):
    os.makedirs(out_dir, exist_ok=True)
    index = open(os.path.join(out_dir, "index.jsonl"), "a", encoding="utf-8")
    status = open(os.path.join(out_dir, "status.jsonl"), "a", encoding="utf-8")
    n = saved = errors = 0
    start = clock()
    next_status = start
    period = 1e9 / fps if fps > 0 else 0
    while not STOP and (max_seconds is None or clock() - start < max_seconds * 1e9):
        t_req = clock()
        if t_req >= next_status:
            try:
                _code, _hdr, body = grabber(base + "/status", timeout)
                status.write(json.dumps({"t_ns": clock(), "status": json.loads(body.decode("utf-8", "replace"))}) + "\n")
            except (OSError, ValueError, urllib.error.URLError) as exc:
                status.write(json.dumps({"t_ns": clock(), "error": "%s: %s" % (type(exc).__name__, exc)}) + "\n")
            status.flush()
            next_status = t_req + status_every * 1e9
            t_req = clock()
        n += 1
        rec = {"n": n, "t_req_ns": t_req}
        try:
            code, headers, body = grabber(base + "/capture", timeout)
            t_resp = clock()
            name = frame_name(n, t_resp)
            with open(os.path.join(out_dir, name), "wb") as fh:
                fh.write(body)
            point_latest(out_dir, name)
            rec.update({"file": name, "t_resp_ns": t_resp, "latency_ms": round((t_resp - t_req) / 1e6, 1),
                        "http": code, "bytes": len(body), "sha12": hashlib.sha256(body).hexdigest()[:12],
                        "headers": bm_headers(headers)})
            saved += 1
        except (OSError, urllib.error.URLError) as exc:
            rec.update({"t_resp_ns": clock(), "error": "%s: %s" % (type(exc).__name__, exc)})
            errors += 1
        index.write(json.dumps(rec) + "\n")
        index.flush()
        if period:
            wait = t_req + period - clock()
            if wait > 0:
                sleep(wait / 1e9)
    index.close()
    status.close()
    secs = (clock() - start) / 1e9
    line = "frames: stopped after %.1f s, %d saved, %d errors, %.2f frames/s" % (secs, saved, errors, saved / secs if secs else 0)
    print(line, flush=True)
    return saved, errors


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", required=True, help="camera base URL, e.g. http://10.42.0.89")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=float, default=5.0, help="target frames per second; 0 = as fast as the camera answers")
    ap.add_argument("--status-every", type=float, default=10.0)
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--max-seconds", type=float)
    args = ap.parse_args(argv)
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    print("frames: %s -> %s at %s frames/s" % (args.base, args.out, args.fps or "max"), flush=True)
    run(args.base.rstrip("/"), args.out, args.fps, args.status_every, args.timeout, args.max_seconds)


if __name__ == "__main__":
    main(sys.argv[1:])
