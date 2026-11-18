"""The tag pilot's arithmetic (plan task M1.T8 step 8): per-placement summaries of detections against tape truth, and
the bm.detector_noise-1 model built from them. Standard library only; tools/tag_pilot.py feeds it.

Errors are always measured minus true. Bearings are degrees, counter-clockwise (left) positive, wrapped to
(-180, 180]. A frame counts as detected only when it holds the tag with the expected id; a frame that holds only
another id counts as a wrong-id frame and as a miss.

How the model's numbers are made (build_noise_model):

- range_bias_m {a, b}: least-squares line through (true range, median range error) of the placements of parts A and B
  that are reliable (below). With fewer than two distinct ranges: a = the mean error, b = 0.
- range_sigma_m {a, b}: for each of those placements, the root mean square over its detected frames of (range error
  minus the bias line); a least-squares line through (true range, that RMS). It therefore holds both the frame-to-frame
  noise and what the bias line leaves over at that placement. If the fitted line would go negative or has a negative
  slope, a = the RMS over all placements and b = 0.
- bearing_bias_deg: median over part A (tag on the car's centre line) of the placements' median bearing error.
- bearing_sigma_deg {a, b}: as range_sigma_m, for the bearing error minus bearing_bias_deg. The operator's error in
  squaring the car to the wall is inside this number, so it is an upper bound on the detector's own bearing noise;
  summarize_placement keeps the frame-to-frame figure (bearing_err_std_deg) separately.
- reliable placement: detection rate >= rate_threshold and |median range error| <= bias_limit_m.
- min_range_m, max_range_m: the ends of the longest unbroken run of reliable placements among parts A, D and E sorted
  by true range (a failed placement in the middle ends a run).
- max_incidence_deg: the largest incidence such that every part C placement at or below it is reliable; with no part C
  placement, the largest incidence among the reliable placements of the other parts.
- p_detect: one entry per placement (true range, incidence, detection rate).
- obs_frames, obs_min_frames: the proposed (window, min hits) if window_success_probability is at least
  window_target for every reliable placement; otherwise the first of the alternatives that is; otherwise the proposed
  pair unchanged (the caller reports which case happened through choose_window()).

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this module from the function list in plan task
M1.T8 step 8.
"""
import math
import statistics

SCHEMA = "bm.detector_noise/1"
RANGE_PARTS = ("A", "D", "E")
FIT_PARTS = ("A", "B")


def wrap_deg(a):
    a = math.fmod(a, 360.0)
    if a <= -180.0:
        a += 360.0
    elif a > 180.0:
        a -= 360.0
    return a


def fit_line(xs, ys):
    """Least squares (a, b) for y = a + b*x. ValueError with fewer than 2 points or when all xs are equal."""
    xs, ys = [float(x) for x in xs], [float(y) for y in ys]
    if len(xs) != len(ys):
        raise ValueError("xs and ys differ in length")
    if len(xs) < 2:
        raise ValueError("a line needs at least 2 points")
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 1e-18:
        raise ValueError("all x values are equal")
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return my - b * mx, b


def _truth(truth):
    x, y = float(truth["x_m"]), float(truth["y_m"])
    rng = math.hypot(x, y)
    bearing = math.degrees(math.atan2(y, x))
    inc = truth.get("incidence_deg")
    return rng, bearing, (abs(bearing) if inc is None or inc == "" else abs(float(inc)))


def summarize_placement(rows, truth):
    """rows: dicts for the frames of one placement, each with ``detected`` (0/1: the expected tag was found),
    ``id`` (the id found, or None), ``range_m`` and ``bearing_deg`` (when detected); truth: {x_m, y_m,
    incidence_deg} of the tag centre in base_link (incidence None: the car is squared to the wall, so the incidence
    equals the bearing's size), optionally ``tag_id``, ``part``, ``placement``, ``bearing_trusted``.

    Returns n_frames, n_detected, rate, n_wrong_id, range_true, bearing_true, incidence_deg, range_err_median,
    range_err_std, bearing_err_median_deg, bearing_err_std_deg (None without detections; std is the sample standard
    deviation, None with one detection), flags (the 0/1 detection sequence), range_errs and bearing_errs (per detected
    frame), and the truth's part / placement / bearing_trusted."""
    rng_true, bearing_true, incidence = _truth(truth)
    want_id = truth.get("tag_id")
    flags, range_errs, bearing_errs, wrong = [], [], [], 0
    for row in rows:
        found = row.get("id")
        found = None if found in ("", None) else int(float(found))        # rows read back from a CSV hold text
        hit = bool(int(float(row.get("detected") or 0)))
        if hit and want_id is not None and found is not None and int(found) != int(want_id):
            hit = False
        if not hit and found is not None and (want_id is None or int(found) != int(want_id)):
            wrong += 1
        flags.append(1 if hit else 0)
        if hit:
            range_errs.append(float(row["range_m"]) - rng_true)
            bearing_errs.append(wrap_deg(float(row["bearing_deg"]) - bearing_true))
    n, k = len(flags), sum(flags)

    def med(v):
        return statistics.median(v) if v else None

    def std(v):
        return statistics.stdev(v) if len(v) > 1 else None

    return {"placement": truth.get("placement"), "part": truth.get("part"),
            "bearing_trusted": bool(truth.get("bearing_trusted", True)),
            "n_frames": n, "n_detected": k, "rate": (k / n) if n else 0.0, "n_wrong_id": wrong,
            "range_true": rng_true, "bearing_true": bearing_true, "incidence_deg": incidence,
            "range_err_median": med(range_errs), "range_err_std": std(range_errs),
            "bearing_err_median_deg": med(bearing_errs), "bearing_err_std_deg": std(bearing_errs),
            "flags": flags, "range_errs": range_errs, "bearing_errs": bearing_errs}


def window_success_probability(flags, window, min_hits):
    """Fraction of all consecutive windows of `window` frames with at least min_hits detections (0.0 when there are
    fewer frames than one window)."""
    flags = [1 if f else 0 for f in flags]
    if window <= 0 or len(flags) < window:
        return 0.0
    total = len(flags) - window + 1
    good = sum(1 for i in range(total) if sum(flags[i:i + window]) >= min_hits)
    return good / total


def is_reliable(summary, rate_threshold=0.9, bias_limit_m=0.10):
    return (summary["rate"] >= rate_threshold and summary["range_err_median"] is not None
            and abs(summary["range_err_median"]) <= bias_limit_m)


def reliable_range(summaries, rate_threshold=0.9, bias_limit_m=0.10, parts=RANGE_PARTS):
    """(min, max) true range of the longest unbroken run of reliable placements among `parts`, sorted by range;
    (None, None) when there is none. Ties go to the run that reaches farther."""
    rows = sorted((s for s in summaries if s.get("part") in parts), key=lambda s: s["range_true"])
    best, run = None, []
    for s in rows + [None]:
        if s is not None and is_reliable(s, rate_threshold, bias_limit_m):
            run.append(s["range_true"])
            continue
        if run and (best is None or len(run) >= len(best)):
            best = run
        run = []
    return (best[0], best[-1]) if best else (None, None)


def max_incidence(summaries, rate_threshold=0.9, bias_limit_m=0.10):
    """Largest incidence with every part C placement at or below it reliable; without a usable part C, the largest
    incidence among the other reliable placements; 0.0 with nothing reliable."""
    by_angle = {}
    for s in summaries:
        if s.get("part") == "C":
            by_angle.setdefault(round(s["incidence_deg"], 1), []).append(is_reliable(s, rate_threshold, bias_limit_m))
    best = None
    for angle in sorted(by_angle):
        if not all(by_angle[angle]):
            break
        best = angle
    if best is not None:
        return best
    others = [s["incidence_deg"] for s in summaries
              if s.get("part") != "C" and is_reliable(s, rate_threshold, bias_limit_m)]
    return max(others) if others else 0.0


def choose_window(summaries, proposed=(5, 3), alternatives=((5, 2), (7, 3)), target=0.95, rate_threshold=0.9,
                  bias_limit_m=0.10):
    """((window, min_hits), verdict, worst probability of the chosen pair over the reliable placements).
    verdict: "confirmed" (the proposed pair reaches `target` on every reliable placement), "alternative" (one of
    the alternatives does), "not_met" (none does; the proposed pair is returned) or "no_data"."""
    reliable = [s for s in summaries if is_reliable(s, rate_threshold, bias_limit_m)]
    if not reliable:
        return tuple(proposed), "no_data", None
    for index, (window, hits) in enumerate((tuple(proposed),) + tuple(alternatives)):
        worst = min(window_success_probability(s["flags"], window, hits) for s in reliable)
        if worst >= target:
            return (window, hits), ("confirmed" if index == 0 else "alternative"), worst
    worst = min(window_success_probability(s["flags"], proposed[0], proposed[1]) for s in reliable)
    return tuple(proposed), "not_met", worst


def _rms(values):
    return math.sqrt(sum(v * v for v in values) / len(values)) if values else None


def _sigma_line(points):
    """points: (range, rms). A line through them that stays positive over their span, else a constant."""
    points = [(r, s) for r, s in points if s is not None]
    if not points:
        return {"a": 0.0, "b": 0.0}
    flat = {"a": _rms([s for _, s in points]), "b": 0.0}
    try:
        a, b = fit_line([r for r, _ in points], [s for _, s in points])
    except ValueError:
        return flat
    lo = min(r for r, _ in points)
    if b < 0 or a + b * lo <= 0 or a < 0:
        return flat
    return {"a": a, "b": b}


def build_noise_model(summaries, tag_black_size_m, source, rate_threshold=0.9, bias_limit_m=0.10,
                      obs_window=(5, 3), window_alternatives=((5, 2), (7, 3)), window_target=0.95):
    """A bm.detector_noise-1 dict from summarize_placement() results (each with ``part`` A-E). source: {log, date
    (YYYY-MM-DD), n_frames, n_placements}. ValueError when no placement of parts A or B is reliable (there is then
    nothing to fit)."""
    fit = [s for s in summaries if s.get("part") in FIT_PARTS and is_reliable(s, rate_threshold, bias_limit_m)]
    if not fit:
        raise ValueError("no reliable placement in parts A or B: nothing to fit")
    ranges = [s["range_true"] for s in fit]
    try:
        bias_a, bias_b = fit_line(ranges, [s["range_err_median"] for s in fit])
    except ValueError:
        bias_a, bias_b = sum(s["range_err_median"] for s in fit) / len(fit), 0.0
    range_sigma = _sigma_line([(s["range_true"], _rms([e - (bias_a + bias_b * s["range_true"]) for e in s["range_errs"]]))
                               for s in fit])
    centre = [s["bearing_err_median_deg"] for s in fit if s.get("part") == "A" and s.get("bearing_trusted", True)]
    if not centre:
        centre = [s["bearing_err_median_deg"] for s in fit if s.get("bearing_trusted", True)]
    bearing_bias = statistics.median(centre) if centre else 0.0
    bearing_sigma = _sigma_line([(s["range_true"], _rms([e - bearing_bias for e in s["bearing_errs"]]))
                                 for s in fit if s.get("bearing_trusted", True)])
    lo, hi = reliable_range(summaries, rate_threshold, bias_limit_m)
    if lo is None:
        lo, hi = min(ranges), max(ranges)
    (window, hits), _verdict, _worst = choose_window(summaries, obs_window, window_alternatives, window_target,
                                                     rate_threshold, bias_limit_m)
    return {
        "schema": SCHEMA,
        "range_bias_m": {"a": round(bias_a, 5), "b": round(bias_b, 5)},
        "range_sigma_m": {"a": round(range_sigma["a"], 5), "b": round(range_sigma["b"], 5)},
        "bearing_bias_deg": round(bearing_bias, 3),
        "bearing_sigma_deg": {"a": round(bearing_sigma["a"], 4), "b": round(bearing_sigma["b"], 4)},
        "min_range_m": round(lo, 3),
        "max_range_m": round(hi, 3),
        "max_incidence_deg": round(max_incidence(summaries, rate_threshold, bias_limit_m), 1),
        "p_detect": [{"range_m": round(s["range_true"], 3), "incidence_deg": round(s["incidence_deg"], 1),
                      "p": round(s["rate"], 3)} for s in sorted(summaries, key=lambda s: (s["range_true"], s["incidence_deg"]))],
        "obs_frames": int(window),
        "obs_min_frames": int(hits),
        "tag_black_size_m": float(tag_black_size_m),
        "source": {"log": str(source["log"]), "date": str(source["date"]), "n_frames": int(source["n_frames"]),
                   "n_placements": int(source["n_placements"])},
    }
