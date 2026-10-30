#!/usr/bin/env python3
"""Measure ESP32-CAM HTTP capture rate, latency, and LED freshness.

PIL is imported only inside the functions that decode a frame. Percentiles use
beaconmind.metrics.latency when that package imports, and the same nearest-rank
rule otherwise.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the M1.T6 capture probe.
AI-assisted: Claude Opus 5.5 via Claude Code, 2026-10-25: added --mode/--quality (bm_cam-0.2 boots at
VGA, so the probe sets the project mode through /control first) and the per-frame size check.
Derived from: course-project/beaconmind/src/beaconmind/metrics/latency.py:percentile_nearest_rank
(same nearest-rank rule, reimplemented for the fallback).
"""
import argparse
import io
import math
import sys
import time
import urllib.error
import urllib.request


def parse_headers(headers):
    """Return seq and capture_us from a header mapping. Missing keys are None."""
    found = {}
    for key, value in headers.items():
        found[str(key).lower()] = value
    seq = found.get("x-bm-seq")
    capture = found.get("x-bm-capture-us")
    return {
        "seq": int(seq) if seq is not None else None,
        "capture_us": int(capture) if capture is not None else None,
    }


MODES = ("qvga", "vga", "svga", "xga", "uxga")


def parse_frame_size(headers):
    """(width, height) from bm_cam-0.2's X-BM-Width/X-BM-Height, or None when either is missing."""
    found = {str(key).lower(): value for key, value in headers.items()}
    width = found.get("x-bm-width")
    height = found.get("x-bm-height")
    if width is None or height is None:
        return None
    return int(width), int(height)


def control_path(mode=None, quality=None):
    """The bm_cam-0.2 /control path that selects a frame size and/or JPEG quality."""
    parts = []
    if mode is not None:
        if mode not in MODES:
            raise ValueError("mode must be one of " + ", ".join(MODES))
        parts.append("framesize=" + mode)
    if quality is not None:
        if isinstance(quality, bool) or not isinstance(quality, int) or not 10 <= quality <= 63:
            raise ValueError("quality must be an integer from 10 to 63")
        parts.append("quality={0}".format(quality))
    if not parts:
        raise ValueError("give a mode or a quality")
    return "/control?" + "&".join(parts)


def set_mode(url, mode, quality, timeout):
    """Send /control and return the (width, height) the camera now reports in /status."""
    import json

    status, _headers, body, _elapsed = fetch(_join(url, control_path(mode, quality)), timeout)
    if status != 200:
        raise ValueError("/control answered {0}: {1}".format(status, body.decode(errors="replace").strip()))
    state = json.loads(body)
    print(
        "mode framesize={0} width={1} height={2} quality={3} fw={4}".format(
            state.get("framesize"), state.get("width"), state.get("height"), state.get("quality"),
            state.get("fw")
        )
    )
    return int(state["width"]), int(state["height"])


def seq_strictly_increasing(seqs):
    """True when each sequence number is greater than the one before it."""
    return all(later > earlier for earlier, later in zip(seqs, seqs[1:]))


def brightness_jump(baseline, frame, fraction=0.20):
    """True when frame mean brightness is more than fraction above baseline."""
    return frame > baseline * (1.0 + fraction)


def percentile_nearest_rank(values, q):
    """Nearest-rank percentile, matching beaconmind.metrics.latency."""
    if isinstance(q, bool) or not isinstance(q, (int, float)):
        raise ValueError("q must be a number in (0, 100]")
    if not (0 < q <= 100):
        raise ValueError("q must be in (0, 100]")
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        raise ValueError("empty list")
    if isinstance(q, int) or q == int(q):
        rank = (int(q) * n + 99) // 100 - 1
    else:
        rank = math.ceil(q / 100.0 * n) - 1
    if rank < 0 or rank >= n:
        raise ValueError("nearest-rank index out of range")
    return ordered[rank]


def summarize_latencies(values):
    """n, p50, p95, max, mean. Prefer beaconmind.metrics.latency."""
    try:
        from beaconmind.metrics.latency import summarize_latencies as package_summary
    except ImportError:
        package_summary = None
    if package_summary is not None:
        return package_summary(values)
    sample = list(values)
    n = len(sample)
    if n == 0:
        raise ValueError("empty list")
    return {
        "n": n,
        "p50": percentile_nearest_rank(sample, 50),
        "p95": percentile_nearest_rank(sample, 95),
        "max": max(sample),
        "mean": sum(sample) / n,
    }


def _join(url, path):
    return url.rstrip("/") + path


def fetch(url, timeout):
    """GET url. Returns status, header dict, body, and seconds."""
    started = time.perf_counter()
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            headers = {key: value for key, value in response.headers.items()}
            status = response.status
    except urllib.error.HTTPError as exc:
        body = exc.read()
        headers = {key: value for key, value in exc.headers.items()}
        status = exc.code
    elapsed = time.perf_counter() - started
    return status, headers, body, elapsed


def jpeg_ok(body):
    return len(body) >= 4 and body[:2] == b"\xff\xd8" and body[-2:] == b"\xff\xd9"


def mean_brightness(body):
    """Mean 0-255 luminance. Imports PIL here so the Mac tests can load this file."""
    from PIL import Image

    image = Image.open(io.BytesIO(body)).convert("L")
    pixels = list(image.getdata())
    if not pixels:
        raise ValueError("empty frame")
    return sum(pixels) / len(pixels)


def run_rate(url, n, timeout, expected_size=None):
    """expected_size: (width, height) set by --mode; frames of another size count as size_mismatch."""
    latencies_ms = []
    seqs = []
    sizes = []
    ok = 0
    size_mismatch = 0
    wall_start = time.perf_counter()
    for _ in range(n):
        status, headers, body, elapsed = fetch(_join(url, "/capture"), timeout)
        latencies_ms.append(elapsed * 1000.0)
        if status == 200 and jpeg_ok(body):
            ok += 1
            sizes.append(len(body))
            parsed = parse_headers(headers)
            if parsed["seq"] is not None:
                seqs.append(parsed["seq"])
            if expected_size is not None and parse_frame_size(headers) != expected_size:
                size_mismatch += 1
    wall = time.perf_counter() - wall_start
    summary = summarize_latencies(latencies_ms)
    fps = (n / wall) if wall > 0 else 0.0
    mean_size = (sum(sizes) / len(sizes)) if sizes else 0.0
    strict = seq_strictly_increasing(seqs) and len(seqs) == ok and ok == n
    print("ok {0}/{1}".format(ok, n))
    print(
        "latency_ms p50={0:.1f} p95={1:.1f} max={2:.1f}".format(
            summary["p50"], summary["p95"], summary["max"]
        )
    )
    print("fps={0:.3f}".format(fps))
    print("seq_strict={0}".format("true" if strict else "false"))
    print("mean_jpeg_bytes={0:.0f}".format(mean_size))
    passed = ok == n and summary["p95"] <= 500.0 and fps >= 3.0 and strict
    if expected_size is not None:
        print("size_mismatch={0} (expected {1}x{2})".format(size_mismatch, *expected_size))
        passed = passed and size_mismatch == 0
    print("pass_rate={0}".format("yes" if passed else "no"))
    return 0


def run_freshness(url, trials, timeout):
    """LED-off baseline, then time until a frame is more than 20% brighter.

    Each trial ends with the LED off. A trial that never jumps inside 5 s is
    recorded as no_jump and is not a pass.
    """
    staleness = []
    for trial in range(1, trials + 1):
        try:
            fetch(_join(url, "/led?on=0"), timeout)
            time.sleep(1.0)
            status, _headers, body, _elapsed = fetch(_join(url, "/capture"), timeout)
            if status != 200 or not jpeg_ok(body):
                print("trial {0} baseline_http={1}".format(trial, status))
                continue
            baseline = mean_brightness(body)
            t0 = time.perf_counter()
            fetch(_join(url, "/led?on=1"), timeout)
            jumped = False
            deadline = t0 + 5.0
            while time.perf_counter() < deadline:
                status, _headers, body, _elapsed = fetch(_join(url, "/capture"), timeout)
                if status == 200 and jpeg_ok(body):
                    bright = mean_brightness(body)
                    if brightness_jump(baseline, bright):
                        delta = time.perf_counter() - t0
                        staleness.append(delta)
                        print(
                            "trial {0} staleness_s={1:.3f} baseline={2:.1f} bright={3:.1f}".format(
                                trial, delta, baseline, bright
                            )
                        )
                        jumped = True
                        break
            if not jumped:
                print("trial {0} no_jump baseline={1:.1f}".format(trial, baseline))
        finally:
            try:
                fetch(_join(url, "/led?on=0"), timeout)
            except (urllib.error.URLError, TimeoutError, OSError):
                print("trial {0} led_off_failed".format(trial))
    if not staleness:
        print("freshness_s p95=none")
        print("pass_freshness=no")
        return 0
    summary = summarize_latencies(staleness)
    print(
        "freshness_s n={0} p50={1:.3f} p95={2:.3f} max={3:.3f}".format(
            summary["n"], summary["p50"], summary["p95"], summary["max"]
        )
    )
    passed = summary["n"] == trials and summary["p95"] <= 1.0
    print("pass_freshness={0}".format("yes" if passed else "no"))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description="Probe the BeaconMind camera HTTP server.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--n", type=int)
    parser.add_argument("--freshness", type=int)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--mode", choices=MODES,
                        help="bm_cam-0.2: set this frame size through /control first (it boots at vga)")
    parser.add_argument("--quality", type=int, help="bm_cam-0.2: set this JPEG quality (10-63) first")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if (args.n is None) == (args.freshness is None):
        print("camera_probe: pass exactly one of --n or --freshness", file=sys.stderr)
        return 2
    try:
        expected_size = None
        if args.mode is not None or args.quality is not None:
            expected_size = set_mode(args.url, args.mode, args.quality, args.timeout)
        if args.n is not None:
            return run_rate(args.url, args.n, args.timeout, expected_size)
        return run_freshness(args.url, args.freshness, args.timeout)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        print("camera_probe: {0}".format(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
