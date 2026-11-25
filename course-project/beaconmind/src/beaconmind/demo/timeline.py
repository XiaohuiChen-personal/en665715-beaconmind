"""Time-lapse arithmetic of the demo video: which source instant each output frame shows (standard library only).

A part of the video is a list of Pieces. A piece plays the source interval [w0, w1] (seconds on the source's own
clock: the summed step times of a simulated episode, or the Spark's epoch clock for a real one) at `speed` source
seconds per output second. Rules (plan M6.T11, kept):

- frame count of a piece: N = max(1, floor(out_s * fps + 0.5)), out_s = (w1 - w0) / speed (half up, never Python's
  round(), which rounds half to even);
- frame i of a piece shows the source instant w0 + (i + 0.5) * (w1 - w0) / N, so frame times strictly increase;
- the speed printed on screen is the piece's speed: "real time" below 1.5, else "x<int(speed + 0.5)>".

Simulated part: one time-lapse factor for the whole episode, except one step shown slowly (fit_sim_factor picks the
smallest whole factor whose output fits the target). Real part: motion plays at move_speed (real time by default)
and the waits between moves are sped up (fit_think_speed picks the smallest whole speed that fits; motion is never
sped up to make it fit).

Phone clock: the phone video begins by filming tools/session_clock.py, which prints the Spark's epoch time to 0.1 s.
One reading (phone time, epoch shown) gives the offset; two or more give offset and rate by least squares
(ClockSync). A rate further than max_rate_error from 1 is refused: it means a misread clock, not a phone.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote this module.
"""
import bisect
import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Piece:
    """Source interval [w0, w1] at `speed`; or, with hold_s, the single instant w0 held for hold_s seconds (a pause,
    labelled "paused" on screen)."""
    w0: float
    w1: float
    speed: float
    label: str = "timelapse"
    hold_s: float = None
    info: dict = field(default_factory=dict, compare=False)

    def __post_init__(self):
        if not (self.w1 >= self.w0):
            raise ValueError("piece ends before it starts: %r" % (self,))
        if not (self.speed > 0):
            raise ValueError("piece speed must be positive: %r" % (self,))
        if self.hold_s is not None and (self.w1 != self.w0 or not self.hold_s > 0):
            raise ValueError("a hold is one instant held for a positive time: %r" % (self,))

    @property
    def out_s(self):
        return self.hold_s if self.hold_s is not None else (self.w1 - self.w0) / self.speed


def hold(w, seconds, label="hold"):
    return Piece(w, w, 1.0, label, hold_s=float(seconds))


def n_frames(piece, fps):
    """Frames of one piece (half up, at least one)."""
    return max(1, int(math.floor(piece.out_s * fps + 0.5)))


def frame_counts(pieces, fps):
    return [n_frames(p, fps) for p in pieces]


def output_duration(pieces, fps):
    return sum(frame_counts(pieces, fps)) / float(fps)


def frame_times(pieces, fps):
    """[(output frame index, source time, piece index)] for every frame of the pieces, in order."""
    out, k = [], 0
    for j, p in enumerate(pieces):
        n = n_frames(p, fps)
        step = (p.w1 - p.w0) / n
        for i in range(n):
            out.append((k, p.w0 if p.hold_s is not None else p.w0 + (i + 0.5) * step, j))
            k += 1
    return out


def speed_badge(speed):
    return "real time" if speed < 1.5 else "\u00d7%d" % int(speed + 0.5)


def piece_badge(piece):
    """What the screen says about a piece's speed."""
    if piece.hold_s is not None:
        return "paused"
    return speed_badge(piece.speed)


def piece_starts(pieces, fps):
    """Output time (s) at which each piece starts."""
    out, k = [], 0
    for n in frame_counts(pieces, fps):
        out.append(k / float(fps))
        k += n
    return out


def output_time_of(pieces, fps, w):
    """Output time (s) at which source time w is shown (the first frame at or after it); None outside the pieces."""
    starts = piece_starts(pieces, fps)
    for p, t0, n in zip(pieces, starts, frame_counts(pieces, fps)):
        if p.hold_s is not None:
            continue
        if p.w0 <= w <= p.w1:
            frac = 0.0 if p.w1 == p.w0 else (w - p.w0) / (p.w1 - p.w0)
            return t0 + min(n - 1, max(0, int(math.ceil(frac * n - 0.5)))) / float(fps)
    return None


# ---------------------------------------------------------------- simulated part

def sim_pieces(total_s, factor, detail=None, detail_speed=2.0, hold_s=0.0):
    """Pieces of a simulated episode of total_s source seconds at one time-lapse factor; `detail` = (d0, d1), a
    source interval shown at detail_speed instead, followed by a pause of hold_s at d1 (when hold_s > 0)."""
    if detail is None:
        return [Piece(0.0, total_s, float(factor), "timelapse")]
    d0, d1 = detail
    if not (0.0 <= d0 < d1 <= total_s):
        raise ValueError("detail interval %r is not inside [0, %s]" % (detail, total_s))
    out = []
    if d0 > 0:
        out.append(Piece(0.0, d0, float(factor), "timelapse"))
    out.append(Piece(d0, d1, float(detail_speed), "detail"))
    if hold_s and hold_s > 0:
        out.append(hold(d1, hold_s))
    if d1 < total_s:
        out.append(Piece(d1, total_s, float(factor), "timelapse"))
    return out


def fit_sim_factor(total_s, target_out_s, fps, detail=None, detail_speed=2.0, max_factor=1000, hold_s=0.0):
    """(factor, pieces): the smallest whole time-lapse factor whose pieces last at most target_out_s."""
    if target_out_s <= 0:
        raise ValueError("target_out_s must be positive")
    rest = total_s - ((detail[1] - detail[0]) if detail else 0.0)
    budget = target_out_s - ((detail[1] - detail[0]) / detail_speed + (hold_s or 0.0) if detail else 0.0)
    if budget <= 0:
        raise ValueError("the slow step alone (%.1f s) does not fit in %.1f s"
                         % ((detail[1] - detail[0]) / detail_speed, target_out_s))
    factor = max(1, int(math.ceil(rest / budget)))
    while factor <= max_factor:
        pieces = sim_pieces(total_s, factor, detail, detail_speed, hold_s)
        if output_duration(pieces, fps) <= target_out_s + 1e-9:
            return factor, pieces
        factor += 1
    raise ValueError("no factor up to %d fits %.1f s" % (max_factor, target_out_s))


# ---------------------------------------------------------------- real part

def car_pieces(t0, t1, move_windows, think_speed, move_speed=1.0):
    """Pieces over [t0, t1]: each move window (start, end) at move_speed, everything between at think_speed.
    Windows are clipped to [t0, t1]; overlapping windows are merged."""
    wins = sorted((max(t0, a), min(t1, b)) for a, b in move_windows if b > t0 and a < t1 and b > a)
    merged = []
    for a, b in wins:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    out, cur = [], t0
    for a, b in merged:
        if a > cur:
            out.append(Piece(cur, a, float(think_speed), "think"))
        out.append(Piece(a, b, float(move_speed), "move"))
        cur = b
    if t1 > cur:
        out.append(Piece(cur, t1, float(think_speed), "think"))
    return out


def fit_think_speed(t0, t1, move_windows, target_out_s, fps, move_speed=1.0, max_speed=2000):
    """(think speed, pieces, fits): the smallest whole think speed >= 1 whose output fits target_out_s. Motion
    stays at move_speed; when even the fastest think speed does not fit, fits is False (report it, never cut
    motion)."""
    base = car_pieces(t0, t1, move_windows, 1.0, move_speed)
    moving = sum(p.out_s for p in base if p.label == "move")
    waiting = sum(p.w1 - p.w0 for p in base if p.label == "think")
    speed = 1 if target_out_s <= moving or waiting == 0 else max(1, int(math.ceil(waiting / (target_out_s - moving))))
    while speed <= max_speed:
        pieces = car_pieces(t0, t1, move_windows, speed, move_speed)
        if output_duration(pieces, fps) <= target_out_s + 1e-9:
            return speed, pieces, True
        if target_out_s <= moving:
            break
        speed += 1
    return max_speed, car_pieces(t0, t1, move_windows, max_speed, move_speed), False


# ---------------------------------------------------------------- waits, motion, a slowed step and pauses

def mixed_pieces(t0, t1, move_windows, think_speed, move_speed=1.0, slow=None, slow_speed=2.0, holds=()):
    """Pieces over [t0, t1]: the move windows at move_speed ("move"), the `slow` interval (s0, s1) outside the moves
    at slow_speed ("detail"), everything else at think_speed ("think"); `holds` = [(instant, seconds)] pauses
    inserted at those instants (labelled "hold"). Adjacent pieces of the same kind and speed are merged."""
    cuts = {t0, t1}
    wins = [(max(t0, a), min(t1, b)) for a, b in move_windows if b > a and b > t0 and a < t1]
    for a, b in wins:
        cuts.update((a, b))
    if slow:
        cuts.update((max(t0, slow[0]), min(t1, slow[1])))
    hold_at = {}
    for w, sec in holds:
        if not (t0 <= w <= t1):
            raise ValueError("hold at %s is outside [%s, %s]" % (w, t0, t1))
        cuts.add(w)
        hold_at[w] = hold_at.get(w, 0.0) + float(sec)
    cuts = sorted(cuts)
    out = []

    def add(p):
        if out and out[-1].hold_s is None and p.hold_s is None and out[-1].label == p.label \
                and out[-1].speed == p.speed and out[-1].w1 == p.w0:
            out[-1] = Piece(out[-1].w0, p.w1, p.speed, p.label)
        else:
            out.append(p)
    for a, b in zip(cuts, cuts[1:]):
        if a in hold_at and (not out or out[-1].hold_s is None or out[-1].w0 != a):
            add(hold(a, hold_at.pop(a)))
        mid = (a + b) / 2.0
        if any(x <= mid <= y for x, y in wins):
            add(Piece(a, b, float(move_speed), "move"))
        elif slow and slow[0] <= mid <= slow[1]:
            add(Piece(a, b, float(slow_speed), "detail"))
        else:
            add(Piece(a, b, float(think_speed), "think"))
    for w in sorted(hold_at):                  # a pause at the very end
        add(hold(w, hold_at[w]))
    return out


def fit_mixed(t0, t1, move_windows, target_out_s, fps, move_speed=1.0, slow=None, slow_speed=2.0, holds=(),
              max_speed=5000):
    """(think speed, pieces, fits): the smallest whole think speed whose pieces fit target_out_s; the motion, the slowed
    interval and the pauses keep their speeds. fits is False when they alone are longer than the target."""
    fixed = mixed_pieces(t0, t1, move_windows, 1.0, move_speed, slow, slow_speed, holds)
    fixed_out = sum(p.out_s for p in fixed if p.label != "think")
    waiting = sum(p.w1 - p.w0 for p in fixed if p.label == "think")
    if target_out_s <= fixed_out:
        return max_speed, mixed_pieces(t0, t1, move_windows, max_speed, move_speed, slow, slow_speed, holds), False
    speed = max(1, int(math.ceil(waiting / (target_out_s - fixed_out)))) if waiting else 1
    while speed <= max_speed:
        pieces = mixed_pieces(t0, t1, move_windows, speed, move_speed, slow, slow_speed, holds)
        if output_duration(pieces, fps) <= target_out_s + 1e-9:
            return speed, pieces, True
        speed += 1
    return max_speed, mixed_pieces(t0, t1, move_windows, max_speed, move_speed, slow, slow_speed, holds), False


def check_length(total_s, bounds):
    """None when total_s is inside bounds = (low, high) seconds, else the reason (the assembly refuses it)."""
    lo, hi = bounds
    if total_s < lo - 1e-9:
        return "the video is %.1f s, shorter than the required %.0f s" % (total_s, lo)
    if total_s > hi + 1e-9:
        return "the video is %.1f s, longer than the allowed %.0f s" % (total_s, hi)
    return None


# ---------------------------------------------------------------- phone clock

@dataclass(frozen=True)
class ClockSync:
    """epoch = offset + rate * phone_s (phone_s: seconds from the start of the phone clip)."""
    offset: float
    rate: float = 1.0
    readings: tuple = ()

    def epoch(self, phone_s):
        return self.offset + self.rate * phone_s

    def phone(self, epoch):
        return (epoch - self.offset) / self.rate

    def residuals(self):
        return [e - self.epoch(p) for p, e in self.readings]


def parse_reading(text):
    """'<phone seconds>=<epoch seconds>' -> (phone_s, epoch)."""
    try:
        a, b = text.split("=")
        return float(a), float(b)
    except ValueError:
        raise ValueError("a clock reading is '<phone seconds>=<epoch shown>', got %r" % text) from None


def clock_sync(readings, max_rate_error=0.002, min_span_for_rate=60.0):
    """ClockSync from [(phone_s, epoch)]: one reading fixes the offset (rate 1); readings that span at least
    min_span_for_rate seconds of the clip are fitted (offset and rate); closer readings cannot measure a rate (the clock
    prints 0.1 s, so 0.1 s over 13 s is already 0.8 %): the rate stays 1 and the offset is their mean."""
    readings = [(float(p), float(e)) for p, e in readings]
    if not readings:
        raise ValueError("at least one clock reading is needed")
    span = max(p for p, _ in readings) - min(p for p, _ in readings)
    if len(readings) == 1 or span < min_span_for_rate:
        off = sum(e - p for p, e in readings) / len(readings)
        if any(abs((e - p) - off) > 0.3 for p, e in readings):
            raise ValueError("clock readings disagree by more than 0.3 s: a reading is wrong")
        return ClockSync(off, 1.0, tuple(readings))
    mp = sum(p for p, _ in readings) / len(readings)
    me = sum(e for _, e in readings) / len(readings)
    spp = sum((p - mp) ** 2 for p, _ in readings)
    if spp < 1.0:
        raise ValueError("clock readings must be at least a few seconds apart in the clip")
    rate = sum((p - mp) * (e - me) for p, e in readings) / spp
    if abs(rate - 1.0) > max_rate_error:
        raise ValueError("clock readings give a rate of %.5f (more than %.3f from 1): a reading is wrong"
                         % (rate, max_rate_error))
    return ClockSync(me - rate * mp, rate, tuple(readings))


def latest_at(times, t):
    """Index of the last of the sorted `times` at or before t, or None."""
    i = bisect.bisect_right(times, t)
    return i - 1 if i else None


# ---------------------------------------------------------------- the whole video

def plan_sequence(items, durations):
    """[{id, kind, start_s, dur_s}] for the sequence items (dicts with id, kind, and seconds for cards) given the
    measured durations of the rendered parts ({id: seconds}); an item whose duration is None is left out."""
    out, t = [], 0.0
    for it in items:
        d = it.get("seconds") if it["kind"] == "card" else durations.get(it["id"])
        if d is None:
            continue
        out.append({"id": it["id"], "kind": it["kind"], "start_s": t, "dur_s": float(d)})
        t += float(d)
    return out


def card_seconds(items, ids=None):
    """Total seconds of the card items (all of them, or those in ids)."""
    return sum(float(it["seconds"]) for it in items if it["kind"] == "card" and (ids is None or it["id"] in ids))


def word_budget(seconds, words_per_min=130):
    """Words that fit in `seconds` of narration at words_per_min (plan M6.T16: 130 words a minute)."""
    return int(seconds * words_per_min / 60.0)
