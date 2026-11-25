"""Every number the video and its narration show, each with the file it was read from (standard library only).

Two sources, never typed by hand:

1. tools/report_assets.py (build_numbers on the evidence files, converted with its own plain()): the same strings
   the report and the slides print, so the video cannot disagree with them (cl.* for the closed-loop episodes,
   cam.hfov for the camera).
2. The episode's own log folder (episode.py) for what the report does not quote: per-step state, time and cost,
   the episode date, the start pose, the noise seed, the world; and summary.json for counts the report does not
   carry (refusals, emergency stops, tool errors).

Numbers(...)[key] -> text; .source(key) -> where it came from; fill(template) replaces {{key}} and refuses an
unknown key (as report_assets.slide_outline does). manifest() lists them all for the evidence.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote this module.
"""
import datetime
import importlib.util
import json
import os
import re

KEY_RE = re.compile(r"\{\{([a-z0-9._-]+)\}\}")
REPORT_KEYS = ("cl.opus.steps", "cl.opus.moves", "cl.opus.ate", "cl.opus.b0-ate", "cl.opus.tags-found", "cl.n-tags",
               "cl.opus.cost", "cl.opus.p95", "cl.opus.agree-steps", "cl.opus.position-fixes", "cl.range-m",
               "cl.opus.model", "cl.opus.effort", "cl.opus.path-m", "cl.prompt", "cam.hfov")


def load_report_assets(course_root):
    path = os.path.join(course_root, "tools", "report_assets.py")
    spec = importlib.util.spec_from_file_location("report_assets", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Numbers:
    def __init__(self):
        self._v = {}

    def put(self, key, value, source):
        if not re.fullmatch(r"[a-z0-9._-]+", key):
            raise ValueError("bad number key %r" % key)
        if key in self._v and self._v[key][0] != str(value):
            raise ValueError("number %r given twice with different values (%r, %r)" % (key, self._v[key][0], value))
        self._v[key] = (str(value), source)

    def __getitem__(self, key):
        try:
            return self._v[key][0]
        except KeyError:
            raise KeyError("no number %r (known: %s)" % (key, ", ".join(sorted(self._v)))) from None

    def __contains__(self, key):
        return key in self._v

    def source(self, key):
        return self._v[key][1]

    def keys(self):
        return sorted(self._v)

    def fill(self, text):
        return KEY_RE.sub(lambda m: self[m.group(1)], text)

    def manifest(self):
        return "\n".join("%s | %s | %s" % (k, self._v[k][0], self._v[k][1]) for k in self.keys()) + "\n"


def mmss(seconds):
    s = int(seconds + 0.5)
    return "%d:%02d" % (s // 60, s % 60)


def report_numbers(course_root, keys=REPORT_KEYS):
    ra = load_report_assets(course_root)
    built = ra.build_numbers(ra.load())
    out = Numbers()
    for k in keys:
        out.put(k, ra.plain(built[k][0]), "report_assets.py: " + built[k][1])
    return out


def episode_numbers(nums, ep, evidence_summary_path, prefix="sim"):
    """Add the episode's own numbers (prefix.*) to `nums`, after checking the log folder's summary is the evidence
    copy byte for byte when an evidence path is given."""
    src = os.path.relpath(ep.run_dir)
    if evidence_summary_path:
        mine = os.path.join(ep.run_dir, "seed_%d.summary.json" % ep.seed)
        with open(mine, "rb") as a, open(evidence_summary_path, "rb") as b:
            if a.read() != b.read():
                raise ValueError("%s differs from the evidence copy %s" % (mine, evidence_summary_path))
    s, run = ep.summary, ep.run
    started = run.get("started")
    if started:
        day = datetime.datetime.strptime(started[:10], "%Y-%m-%d").date()
        nums.put(prefix + ".date", day.isoformat(), src + "/run.json started")
        nums.put(prefix + ".date-long", "%d %s %d" % (day.day, day.strftime("%B"), day.year), src + "/run.json started")
    env = run.get("env") or {}
    if env.get("start"):
        x, y, th = (float(v) for v in env["start"].split(","))
        nums.put(prefix + ".start", "(%.2f, %.2f, %d°)" % (x, y, round(th)), src + "/run.json env start")
    if env.get("drive_inset") is not None:
        nums.put(prefix + ".inset-m", "%.1f" % float(env["drive_inset"]), src + "/run.json env drive_inset")
    if run.get("seeds"):
        nums.put(prefix + ".noise-seed", str(run["seeds"][0]), src + "/run.json seeds")
    wf = run.get("world_file")
    if wf:
        nums.put(prefix + ".world", os.path.basename(wf), src + "/run.json world_file")
    nums.put(prefix + ".steps", str(len(ep.steps)), src + "/seed_%d.jsonl rows" % ep.seed)
    nums.put(prefix + ".tags", str(len(ep.tags)), src + "/seed_%d.world.json scene.tags" % ep.seed)
    ids = [t["id"] for t in ep.tags]
    dups = sorted({i for i in ids if ids.count(i) > 1})
    nums.put(prefix + ".dup-ids", ", ".join(str(i) for i in dups[:-1]) + (" and %d" % dups[-1] if len(dups) > 1
                                                                          else str(dups[0]) if dups else "none"),
             src + "/seed_%d.world.json (IDs on two tags)" % ep.seed)
    total = sum(st.seconds for st in ep.steps)
    nums.put(prefix + ".time-mmss", mmss(total), src + "/seed_%d.jsonl seconds, summed" % ep.seed)
    nums.put(prefix + ".time-min", "%.1f" % (total / 60.0), src + "/seed_%d.jsonl seconds, summed" % ep.seed)
    nums.put(prefix + ".step-mean-s", "%.0f" % ((s.get("time") or {}).get("mean_s", 0)), src + " summary time mean_s")
    nums.put(prefix + ".cost", "%.2f" % ep.cost_total, src + "/seed_%d.jsonl turns cost_usd, summed" % ep.seed)
    nums.put(prefix + ".refused", str(s.get("refused_move_calls")), "seed_%d.summary.json refused_move_calls" % ep.seed)
    nums.put(prefix + ".estops", str(s.get("emergency_stops")), "seed_%d.summary.json emergency_stops" % ep.seed)
    nums.put(prefix + ".phantoms", str((s.get("map") or {}).get("phantoms")), "seed_%d.summary.json map phantoms" % ep.seed)
    nums.put(prefix + ".tool-errors", str((s.get("violations_by_code") or {}).get("invalid_tool_call", 0)),
             "seed_%d.summary.json violations_by_code invalid_tool_call" % ep.seed)
    nums.put(prefix + ".tool-calls", str((s.get("tools") or {}).get("calls")), "seed_%d.summary.json tools calls" % ep.seed)
    nums.put(prefix + ".fallbacks", str(s.get("fallbacks")), "seed_%d.summary.json fallbacks" % ep.seed)
    nums.put(prefix + ".ended-by", str(s.get("ended_by")), "seed_%d.summary.json ended_by" % ep.seed)
    nums.put(prefix + ".map-rmse-cm", "%.1f" % (100 * (s.get("map") or {}).get("map_rmse_m", float("nan"))),
             "seed_%d.summary.json map map_rmse_m (m to cm)" % ep.seed)
    nums.put(prefix + ".final-pos-cm", "%.1f" % (100 * (s.get("pose") or {}).get("final_pos_m", float("nan"))),
             "seed_%d.summary.json pose final_pos_m (m to cm)" % ep.seed)
    nums.put(prefix + ".turns", str(sum(len(st.turn_ends) for st in ep.steps)), "seed_%d.jsonl turns, counted" % ep.seed)
    return nums


def rule_numbers(nums):
    """Constants of the rules the video names, read from the code that applies them."""
    import inspect

    from beaconmind.envs import kinsim_lite as ks
    from beaconmind.metrics import pilot as pm
    radius = inspect.signature(pm.map_scores_c10).parameters["radius"].default
    nums.put("rule.map-radius-m", "%.2f" % radius, "metrics/pilot.py map_scores_c10 radius (plan C10.3)")
    nums.put("rule.wall-limit-m", "%.2f" % ks.WALL_LIMIT_M, "envs/kinsim_lite.py WALL_LIMIT_M")
    side = ks.ARENA["x1"] - ks.ARENA["x0"]
    nums.put("rule.square-m", "%.2f" % side, "envs/kinsim_lite.py ARENA (x1 - x0)")
    return nums


def scripted_numbers(nums, trace_path):
    """The scripted validator trace (evidence/M2/M2.T7/closed-loop/scripted_validator_trace.json)."""
    with open(trace_path, encoding="utf-8") as fh:
        tr = json.load(fh)
    src = os.path.relpath(trace_path)
    refused = [(st["step"], m) for st in tr["steps"] for m in st.get("move_calls") or []
               if m.get("tool_result") == "refused"]
    nums.put("val.steps", str(tr["result"]["steps"]), src + " result steps")
    nums.put("val.refused", str(len(refused)), src + " move_calls refused, counted")
    nums.put("val.ended-by", tr["result"]["ended_by"], src + " result ended_by")
    return nums
