"""One closed-loop run folder (harness/closed_loop.py, tools/closed_loop_run.py) as a timeline of steps, for the video.

Reads, and never writes: seed_<n>.jsonl (one row per step: observation, tool calls, model turns with their seconds
and cost, the report, the move calls with the validator's verdict, the executed move, the true pose), and when
present seed_<n>.world.json (the simulator's map-frame scene), seed_<n>.summary.json, run.json, seed_<n>.moves.jsonl
(commanded / result times of every move, host epoch), spend.jsonl (one line per model turn, host epoch), and for a
real car backend/steps.jsonl (one line per sensing: host time, frames, detections).

Two time bases:

- "steps" (the simulated part): source time is the sum of the step durations the harness logged (`seconds`), so the
  clock on screen ends at the summary's time.total_s. Inside a step, a tool call is placed at the end of the model
  turn that made it (turn i made `tool_uses` calls; turns[].seconds are summed from the step's start). The simulated
  move is instantaneous; it happens at the step's end.
- "epoch" (the real car): host epoch seconds. Turn ends come from spend.jsonl (matched to the rows' turns in order),
  moves from seed_<n>.moves.jsonl, sensing times from backend/steps.jsonl when present.

Every pose here is in the episode's map frame (plan C1: the start pose is the origin). check_against_summary()
recomputes the numbers the video shows and compares them with the harness's own summary, so a reader error cannot
reach the screen silently.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote this reader.
"""
import glob
import json
import math
import os
from dataclasses import dataclass, field

def _c10_radius():
    """plan C10.3's radius, as metrics/pilot.py map_scores_c10 applies it (0.30 m)."""
    import inspect

    from beaconmind.metrics import pilot
    return inspect.signature(pilot.map_scores_c10).parameters["radius"].default


MAP_RADIUS_M = _c10_radius()


@dataclass
class Call:
    tool: str
    args: dict
    result: object
    t: float                  # source time at which the model made the call (end of its turn)
    ok: bool                  # False when the tool answered with an error


@dataclass
class Step:
    k: int
    t0: float                 # source time the step starts (its observation is available)
    t1: float                 # source time the step ends (after its move)
    t_report: float           # source time the report is written (end of the last model turn)
    move_t0: float            # source time the move starts (== move_t1 in the simulator: instantaneous)
    move_t1: float
    seconds: float
    turn_ends: list
    turn_costs: list
    calls: list
    observation: dict
    raw_dets: list
    report: dict              # what the step carried forward (the written report, or the harness's fallback)
    decision: str
    move: dict = None         # the executed move {action, result, ...} or None
    move_calls: list = field(default_factory=list)
    violations: list = field(default_factory=list)
    truth: dict = None        # true pose at this step's observation (map frame); None when there is none
    estimate: dict = None     # the pose the agent carried forward from this step
    prior: dict = None        # the previous estimate composed with this step's odometry (the first tool call's answer)
    fallback: bool = False
    note: str = None


@dataclass
class Episode:
    run_dir: str
    seed: int
    steps: list
    tags: list                # the true tags, map frame: [{tag, id, x_m, y_m, normal_deg, uid, wall}]
    scene: dict               # walls_polygon, drive_polygon, obstacles (map frame); None when unknown
    start_pose_world: dict
    summary: dict
    run: dict
    time_base: str
    epoch0: float = None      # host epoch of source time 0, when known
    end: dict = None          # the last row's episode_end {ended_by, detail}
    cost_total: float = 0.0
    move_windows: list = field(default_factory=list)

    @property
    def total_s(self):
        return self.steps[-1].t1 if self.steps else 0.0

    def logged_time(self, t):
        """Source time t without the drawn motion before it (simulator: the harness's own clock; the clock stands
        still while a drawn move plays). On the epoch time base it is the time since the episode's start."""
        if self.time_base == "epoch":
            return t - (self.epoch0 or 0.0)
        drawn = sum(max(0.0, min(t, b) - a) for a, b in self.move_windows if a < t)
        return t - drawn

    def step_at(self, t):
        """Index of the step whose interval holds source time t (clamped to the first and last step)."""
        lo, hi = 0, len(self.steps) - 1
        if t <= self.steps[0].t0:
            return 0
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.steps[mid].t0 <= t:
                lo = mid
            else:
                hi = mid - 1
        return lo

    def cost_at(self, t):
        """US$ spent on model turns that ended at or before source time t."""
        total = 0.0
        for s in self.steps:
            if s.t0 > t:
                break
            for te, c in zip(s.turn_ends, s.turn_costs):
                if te <= t:
                    total += c
        return total


# ---------------------------------------------------------------- reading

def _jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def find_seed(run_dir, seed=None):
    if seed is not None:
        return int(seed)
    names = sorted(glob.glob(os.path.join(run_dir, "seed_*.jsonl")))
    seeds = sorted({int(os.path.basename(n).split("_")[1].split(".")[0]) for n in names})
    if len(seeds) != 1:
        raise ValueError("%s holds %d seeds %s; name one" % (run_dir, len(seeds), seeds))
    return seeds[0]


def tool_ok(result):
    """False when a tool answered with an error (a refused move is not a tool error: it is the validator)."""
    return not (isinstance(result, dict) and result.get("status") == "error")


def place_calls(calls, turns, t0, t_end):
    """[Call] with the source time each was made: the end of the turn that made it (turn i made tool_uses calls).
    Without turns (a coded procedure) the calls are spread evenly over the step."""
    out = []
    uses = [int(t.get("tool_uses") or 0) for t in turns]
    if turns and sum(uses) == len(calls):
        ends, acc = [], t0
        for t in turns:
            acc += float(t.get("seconds") or 0.0)
            ends.append(min(acc, t_end))
        i = 0
        for end, n in zip(ends, uses):
            for _ in range(n):
                c = calls[i]
                out.append(Call(c.get("tool"), c.get("args") or {}, c.get("result"), end, tool_ok(c.get("result"))))
                i += 1
        return out
    n = len(calls)
    for i, c in enumerate(calls):
        t = t0 + (i + 1) * (t_end - t0) / (n + 1)
        out.append(Call(c.get("tool"), c.get("args") or {}, c.get("result"), t, tool_ok(c.get("result"))))
    return out


def move_seconds(move):
    """How long a move takes at its commanded limits (bm.move/1: distance_m at v_max_mps, angle_deg at w_max_dps).
    Used to draw a simulated move, which the simulator itself executes in no time. 0 when the command is missing."""
    cmd = (move or {}).get("command") or {}
    try:
        d = abs(float(cmd.get("distance_m") or 0.0)) / float(cmd["v_max_mps"]) if cmd.get("distance_m") else 0.0
        a = abs(float(cmd.get("angle_deg") or 0.0)) / float(cmd["w_max_dps"]) if cmd.get("angle_deg") else 0.0
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return 0.0
    return d + a


def load_episode(run_dir, seed=None, time_base="steps", backend_steps=None, draw_motion=False):
    """Episode of one run folder. time_base "steps" (simulator) or "epoch" (real car; needs the epoch logs).
    draw_motion (steps time base only): give every executed move the duration it takes at its commanded speed limits
    (move_seconds), inserted after the step's report; Episode.logged_time() then takes those drawn seconds out
    again, so the clock on screen stays the harness's own."""
    seed = find_seed(run_dir, seed)
    rows = sorted(_jsonl(os.path.join(run_dir, "seed_%d.jsonl" % seed)), key=lambda r: r["step"])
    if [r["step"] for r in rows] != list(range(len(rows))):
        raise ValueError("%s: steps are not 0..n-1" % run_dir)
    p = lambda name: os.path.join(run_dir, name)  # noqa: E731
    world = _json(p("seed_%d.world.json" % seed)) if os.path.exists(p("seed_%d.world.json" % seed)) else {}
    summary = _json(p("seed_%d.summary.json" % seed)) if os.path.exists(p("seed_%d.summary.json" % seed)) else {}
    run = _json(p("run.json")) if os.path.exists(p("run.json")) else {}
    moves = _jsonl(p("seed_%d.moves.jsonl" % seed)) if os.path.exists(p("seed_%d.moves.jsonl" % seed)) else []
    spend = _jsonl(p("spend.jsonl")) if os.path.exists(p("spend.jsonl")) else []
    scene = world.get("scene")
    tags = (scene or {}).get("tags") or world.get("world") or []
    tags = [{k: t.get(k) for k in ("tag", "id", "x_m", "y_m", "normal_deg", "uid", "wall")} for t in tags]

    if time_base == "steps":
        steps, t, windows = [], 0.0, []
        for r in rows:
            sec = float(r.get("seconds") or 0.0)
            d = move_seconds(r.get("executed_move")) if (draw_motion and r.get("executed_move")) else 0.0
            steps.append(_step(r, t, t + sec, t + sec, t + sec + d))
            if d > 0:
                windows.append((t + sec, t + sec + d))
            t += sec + d
        epoch0 = None
    elif time_base == "epoch":
        steps, epoch0, windows = _epoch_steps(rows, moves, spend, backend_steps)
    else:
        raise ValueError("time_base must be 'steps' or 'epoch'")
    ep = Episode(run_dir=run_dir, seed=seed, steps=steps, tags=tags, scene=scene,
                 start_pose_world=world.get("start_pose") or (scene or {}).get("start_pose_world"),
                 summary=summary, run=run, time_base=time_base, epoch0=epoch0, move_windows=windows)
    ep.cost_total = sum(sum(s.turn_costs) for s in steps)
    ep.end = rows[-1].get("episode_end") if rows else None
    return ep


def _step(r, t0, t_report, move_t0, move_t1, turn_ends=None, t1=None):
    turns = r.get("turns") or []
    if turn_ends is None:
        calls = place_calls(r.get("calls") or [], turns, t0, t_report)
        acc, turn_ends = t0, []
        for tr in turns:
            acc += float(tr.get("seconds") or 0.0)
            turn_ends.append(min(acc, t_report))
    else:
        calls = place_calls_at(r.get("calls") or [], turns, turn_ends, t0, t_report)
    report = r.get("next_prev") or r.get("report") or {}
    return Step(k=r["step"], t0=t0, t1=move_t1 if t1 is None else t1, t_report=t_report, move_t0=move_t0,
                move_t1=move_t1, seconds=float(r.get("seconds") or 0.0), turn_ends=turn_ends,
                turn_costs=[float(tr.get("cost_usd") or 0.0) for tr in turns], calls=calls,
                observation=r.get("observation") or {}, raw_dets=(r.get("raw") or {}).get("detections") or [],
                report=report, decision=r.get("decision") or report.get("decision"),
                move=r.get("executed_move"), move_calls=r.get("move_calls") or [],
                violations=r.get("violations") or [], truth=r.get("truth"),
                estimate=r.get("estimate_pose") or report.get("pose"), prior=r.get("harness_prior"),
                fallback=bool(r.get("fallback")), note=report.get("note"))


def place_calls_at(calls, turns, turn_ends, t0, t_end):
    uses = [int(t.get("tool_uses") or 0) for t in turns]
    if turns and len(turn_ends) == len(turns) and sum(uses) == len(calls):
        out, i = [], 0
        for end, n in zip(turn_ends, uses):
            for _ in range(n):
                c = calls[i]
                out.append(Call(c.get("tool"), c.get("args") or {}, c.get("result"), end, tool_ok(c.get("result"))))
                i += 1
        return out
    return place_calls(calls, [], t0, t_end)


def _epoch_steps(rows, moves, spend, backend_steps):
    """Steps on the host epoch clock (real car, or a simulated run whose epoch logs are complete)."""
    n_turns = sum(len(r.get("turns") or []) for r in rows)
    turn_t = [float(s["t"]) for s in spend] if spend and len(spend) == n_turns else None
    if n_turns and turn_t is None:
        raise ValueError("spend.jsonl has %d lines for %d model turns: cannot place the turns in time"
                         % (len(spend), n_turns))
    cmd = {m["step"]: float(m["t"]) for m in moves if m.get("phase") == "commanded"}
    res = {m["step"]: float(m["t"]) for m in moves if m.get("phase") == "result"}
    sense = {}
    for b in backend_steps or []:
        if b.get("type", "step") == "step" and b.get("t_unix") is not None:
            sense.setdefault(int(b["step"]), float(b["t_unix"]))
    steps, i, starts = [], 0, []
    for r in rows:
        turns = r.get("turns") or []
        ends = turn_t[i:i + len(turns)] if turn_t else []
        i += len(turns)
        k = r["step"]
        if k in sense:
            t0 = sense[k]
        elif ends:
            t0 = ends[0] - float(turns[0].get("seconds") or 0.0)
        elif k - 1 in res:
            t0 = res[k - 1]
        elif k in cmd:
            t0 = cmd[k]
        else:
            raise ValueError("step %d has no time in the logs" % k)
        t_report = ends[-1] if ends else cmd.get(k, t0)
        m0 = cmd.get(k, t_report)
        m1 = res.get(k, m0)
        starts.append(t0)
        steps.append((r, t0, t_report, m0, m1, ends))
    out = []
    for j, (r, t0, t_report, m0, m1, ends) in enumerate(steps):
        t1 = starts[j + 1] if j + 1 < len(starts) else max(t_report, m1)
        out.append(_step(r, t0, t_report, m0, m1, turn_ends=ends, t1=max(t1, m1, t_report)))
    epoch0 = out[0].t0 if out else None
    windows = [(s.move_t0, s.move_t1) for s in out if s.move and s.move_t1 > s.move_t0]
    return out, epoch0, windows


# ---------------------------------------------------------------- map and pose helpers

def mapped_tags(map_entries, tags, radius=MAP_RADIUS_M):
    """Indices of the true tags that a map entry finds (plan C10.3, as metrics/pilot.py map_scores_c10: each entry
    is checked against its nearest tag with the same ID)."""
    hit = set()
    for b in map_entries or []:
        if not isinstance(b, dict) or not _finite(b.get("x_m")) or not _finite(b.get("y_m")):
            continue
        cands = [(math.hypot(b["x_m"] - t["x_m"], b["y_m"] - t["y_m"]), t["tag"]) for t in tags if t["id"] == b.get("id")]
        if cands:
            d, tag = min(cands)
            if d <= radius:
                hit.add(tag)
    return hit


def _finite(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def wrap_deg(a):
    return (a + 180.0) % 360.0 - 180.0


def interp_pose(a, b, f):
    """Linear in x and y, shortest arc in heading; f in [0, 1]."""
    f = min(1.0, max(0.0, f))
    th = a["theta_deg"] + wrap_deg(b["theta_deg"] - a["theta_deg"]) * f
    return {"x_m": a["x_m"] + (b["x_m"] - a["x_m"]) * f, "y_m": a["y_m"] + (b["y_m"] - a["y_m"]) * f,
            "theta_deg": wrap_deg(th)}


def pose_error_m(a, b):
    return math.hypot(a["x_m"] - b["x_m"], a["y_m"] - b["y_m"])


# ---------------------------------------------------------------- the state drawn at one instant

@dataclass
class View:
    """What the screen shows at one source instant."""
    k: int                    # the step shown in the panel
    t: float
    truth: dict
    belief: dict
    belief_is_report: bool    # True once this step's report is written (else the odometry prior)
    map_entries: list
    mapped: set
    detected: set             # true tag indices seen in this step's observation
    calls: list               # the calls made so far in this step
    report_shown: bool
    moving: bool
    trail_truth: list
    trail_belief: list
    cost: float


def _glide(anim_s, step, nxt):
    """Source seconds over which step's move is drawn: its real duration, or anim_s when that is longer, but never
    more than 60 % of the next step (so the next step's panel still shows)."""
    real = step.move_t1 - step.move_t0
    if nxt is None:
        return max(real, anim_s)
    return max(real, min(anim_s, 0.6 * (nxt.t1 - nxt.t0)))


def view_at(ep, t, anim_s=0.0):
    """The View at source time t. The move of step k is drawn as a glide from step k's true pose to step k+1's
    over [move_t0, move_t0 + max(anim_s, move_t1 - move_t0)] (in the simulator the move takes no time; anim_s is
    then only a drawing aid); the panel keeps step k until the glide has ended."""
    i = ep.step_at(t)
    s = ep.steps[i]
    if i > 0:
        prev = ep.steps[i - 1]
        glide_end = prev.move_t0 + _glide(anim_s, prev, s)
        if prev.move and t < glide_end:
            i, s = i - 1, prev
    nxt = ep.steps[i + 1] if i + 1 < len(ep.steps) else None
    glide = _glide(anim_s, s, nxt)
    moving = bool(s.move and nxt and t >= s.move_t0 and glide > 0)
    f = min(1.0, (t - s.move_t0) / glide) if moving else 0.0
    truth = s.truth
    if moving and s.truth and nxt.truth:
        truth = interp_pose(s.truth, nxt.truth, f)
    report_shown = t >= s.t_report
    prev_est = ep.steps[i - 1].estimate if i > 0 else s.prior
    if report_shown:
        belief = s.estimate
        if moving and nxt and nxt.prior:
            belief = interp_pose(s.estimate, nxt.prior, f)
    else:
        belief = s.prior or prev_est
    entries = (s.report.get("map") if report_shown else (ep.steps[i - 1].report.get("map") if i > 0 else [])) or []
    trail_t = [st.truth for st in ep.steps[:i + 1] if st.truth] + ([truth] if moving and truth else [])
    trail_b = [st.estimate for st in ep.steps[:i] if st.estimate] + ([belief] if belief else [])
    return View(k=s.k, t=t, truth=truth, belief=belief, belief_is_report=report_shown, map_entries=entries,
                mapped=mapped_tags(entries, ep.tags), detected={d.get("_tag") for d in s.raw_dets
                                                                 if d.get("_tag") is not None},
                calls=[c for c in s.calls if c.t <= t], report_shown=report_shown, moving=moving,
                trail_truth=trail_t, trail_belief=trail_b, cost=ep.cost_at(t))


# ---------------------------------------------------------------- consistency with the harness's summary

def check_against_summary(ep):
    """[(what, from the step rows, from summary.json, agrees)]; raises nothing (the caller decides)."""
    s = ep.summary
    out = []

    def add(what, mine, theirs, tol=0.0):
        ok = theirs is not None and (abs(mine - theirs) <= tol if isinstance(mine, float) else mine == theirs)
        out.append((what, mine, theirs, ok))

    add("steps", len(ep.steps), s.get("steps"))
    add("moves executed", sum(1 for st in ep.steps if st.move and st.move.get("result") != "refused"),
        s.get("moves_executed"))
    add("refused move calls", sum(1 for st in ep.steps for m in st.move_calls
                                  if m.get("tool_result") in ("refused", "error")), s.get("refused_move_calls"))
    final_map = ep.steps[-1].report.get("map") if ep.steps else []
    add("tags mapped within 0.30 m", len(mapped_tags(final_map, ep.tags)), (s.get("map") or {}).get("tags_found"))
    add("map entries", len(final_map or []), (s.get("map") or {}).get("n_entries"))
    add("ended by", (ep.end or {}).get("ended_by"), s.get("ended_by"))
    if ep.time_base == "steps":
        add("time total (s)", round(sum(st.seconds for st in ep.steps), 6), round((s.get("time") or {}).get("total_s", -1), 6), 1e-6)
    add("cost (US$)", round(ep.cost_total, 6), round(s.get("cost_usd", -1.0), 6), 1e-6)
    return out
