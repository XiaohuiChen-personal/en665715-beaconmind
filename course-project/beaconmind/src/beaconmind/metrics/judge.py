"""Rubric and LLM judge for the agent's `note` (the one free-text field of a replay report), with the
pieces of a fully automated calibration: known-label synthetic notes, fabrication injection, and
invariance variants.

What is scored. The prompt tells the agent: "note and message: one sentence, first person as the
robot, uncertainty stated plainly" and "TONE: Terse, literal, numeric" (prompts/robot_system_prompt_v3.3.txt;
AGENT-DESIGN D9: "Never report a success that no tool result shows"). A note has no single right
string, so it is scored with a rubric (Module 9 notes §11-§14): three criteria scored by an LLM judge
and one scored by code, levels 0-2, weights summing to 1, and a gate on faithfulness.

The judge sees EVIDENCE built by code from the step (tool results, the report's own fields, and a
checklist of material map events), the anchors, and the note. It returns a short reason first and then
one integer level per criterion, constrained by a JSON schema (Ollama structured outputs), at
temperature 0 with a fixed seed. All arithmetic is done here, never by the judge.

Calibration without human labels: (1) known-label items, notes assembled by code from a real step's
evidence with controlled defects, so every expected level is known by construction; (2) fabrication
injection into real notes, which must drive faithfulness to 0; (3) invariance: repeat runs, reversed
anchor order and a neutral padding sentence must not change the levels; (4) agreement between two
judges from different model families, both different from the agent's (Anthropic).

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: designed the rubric and the calibration, wrote this module.
"""
import json
import random
import re
import urllib.request

WEIGHTS = {"faithful": 0.40, "coverage": 0.25, "uncertainty": 0.25, "concise": 0.10}
JUDGED = ("faithful", "coverage", "uncertainty")

ANCHORS = {
    "faithful": {
        "title": "Faithful to the evidence (one idea: is every statement true?)",
        0: "The note asserts an event that did not happen in this step's EVIDENCE (a pose fix, match, new beacon, "
           "rejection, confirmation or loop closure that is not there), or states a pose source different from "
           "the report's pose_source.",
        1: "Every event the note asserts did happen, but one detail is wrong: a beacon label is wrong for a real "
           "event (for example B3 instead of B3b), or a number differs from the EVIDENCE by more than rounding.",
        2: "Every event and every detail in the note is supported by the EVIDENCE.",
    },
    "coverage": {
        "title": "Covers the material map events (one idea: is anything important left out?)",
        0: "The note leaves out two or more of the MATERIAL EVENTS listed in the EVIDENCE.",
        1: "The note leaves out exactly one of the MATERIAL EVENTS.",
        2: "The note mentions every MATERIAL EVENT, by label or as a group (for example 'added two new "
           "beacons'), or the list of MATERIAL EVENTS is empty.",
    },
    "uncertainty": {
        "title": "States how reliable the pose is (one idea: can the reader tell how much to trust the pose?)",
        0: "The note does not say how the pose was obtained.",
        1: "The note says how the pose was obtained but gives no reason or quality figure for it.",
        2: "The note says how the pose was obtained and gives the reason or a quality figure: for a pose from "
           "odometry, a kept prior or a position fix, why no full fix was made (for example 'no confirmed "
           "beacon', 'the fix was outside the prior gate'); for a beacon fix, the beacons used or the residual.",
    },
}

POSE_WORDS = {
    "beacon_fix": "a full beacon fix", "position_fix": "a position-only fix (heading kept)",
    "relocalised": "a relocalisation fix", "prior_kept": "the odometry prior (a fix was computed and rejected)",
    "odometry": "odometry only",
}


# ---------------------------------------------------------------- evidence

def _labels(entries):
    return {b.get("beacon") for b in entries or [] if isinstance(b, dict)}


def material_events(report, prev_report):
    """Map events a reader needs (pose reliability is a separate criterion): new beacons, rejected
    detections, beacons confirmed this step, loop closures, and duplicated-ID labels (B<id>b)."""
    ev = []
    rep = report or {}
    prev_map = {b.get("beacon"): b for b in (prev_report or {}).get("map") or [] if isinstance(b, dict)}
    for a in rep.get("associations") or []:
        if not isinstance(a, dict):
            continue
        if a.get("result") == "new":
            dup = " (a second tag with id %s)" % a.get("id") if str(a.get("beacon", "")).endswith("b") else ""
            ev.append("new tentative beacon %s from det %s%s" % (a.get("beacon"), a.get("det"), dup))
        elif a.get("result") in ("rejected", "ambiguous"):
            ev.append("det %s (id %s) %s" % (a.get("det"), a.get("id"), a.get("result")))
    for b in rep.get("map") or []:
        if isinstance(b, dict) and b.get("state") == "confirmed" and prev_map.get(b.get("beacon"), {}).get("state") == "tentative":
            ev.append("%s became confirmed" % b.get("beacon"))
    for lc in rep.get("loop_closure") or []:
        if isinstance(lc, dict):
            ev.append("loop closure on %s %s" % (lc.get("beacon"), "accepted" if lc.get("accepted") else "not accepted"))
    return ev


EVIDENCE_VERSION = 2   # v1 (2026-10-29) lacked the rules, the observation and map states: see rules_text


def _short(res):
    """A tool result without the twelve exploration sectors (replay never needs them)."""
    if not isinstance(res, dict):
        return res
    return {k: v for k, v in res.items() if k != "sectors"}


def rules_text(dv=None):
    """The procedure's rules and thresholds the agent was given (prompt v3.3, AGENT-DESIGN D7), with the
    numbers read from configs/dv.json, so that a correct note quoting them is not judged invented."""
    from beaconmind.dv import load_dv
    v = dv or load_dv()
    return [
        "A tentative beacon becomes confirmed when n_obs >= %g and baseline_m >= %.2f m (distance from where it was first seen)."
        % (v["confirm_n_obs"], v["confirm_baseline_m"]),
        "Only confirmed, non-suspect beacons can be used by fix_pose; confirmed beacons are never moved.",
        "Association gate %.2f m / %g deg, widened by %.2f m and %g deg per metre of travel since the last full fix and %g deg per "
        "turn since it (cap %.2f m / %g deg); candidates are map entries with the detection's ID."
        % (v["gate_range_m"], v["gate_bearing_deg"], v["gate_widen_range_per_m"], v["gate_widen_bearing_per_m"],
           v["gate_widen_bearing_per_turn_deg"], v["gate_cap_range_m"], v["gate_cap_bearing_deg"]),
        "A detection in gate with exactly one candidate is matched; none in gate and every candidate more than %.1f m away is new "
        "(labelled B<id>b if B<id> exists); otherwise rejected." % v["conflict_radius_m"],
        "pose_source: beacon_fix if the full fix is well_conditioned (sigma <= %.2f m / %g deg) and within the prior gate "
        "(%.2f m / %g deg); position_fix if the position fix is within %.2f m of the prior and heading_safe (every bearing within "
        "%g deg); prior_kept if a fix was computed but neither held (then every detection is rejected and the map is unchanged); "
        "odometry if no matched confirmed beacon." % (v["well_cond_sigma_xy_m"], v["well_cond_sigma_theta_deg"], v["prior_gate_m"],
                                                      v["prior_gate_deg"], v["position_fix_gate_m"], v["heading_safe_deg"]),
        "A loop closure is a matched confirmed beacon with at least %.1f m of travel since last seen; it is accepted only in a "
        "beacon_fix that used that beacon." % v["revisit_travel_m"],
        "In replay mode the robot does not move and the decision is NONE.",
    ]


def build_evidence(row):
    """EVIDENCE for one logged step (a pilot run row), version 2: the rules, the observation the agent received,
    the previous and new map entries with their states, every tool call with its full result (exploration
    sectors dropped), the report's structured fields, and the material-event checklist."""
    rep = row.get("report") or {}
    prev = row.get("prev_report")
    obs = row.get("observation") or {}

    def entries(m):
        return [{k: b.get(k) for k in ("beacon", "id", "x_m", "y_m", "n_obs", "state", "suspect", "first_seen_from")}
                for b in (m or {}).get("map") or [] if isinstance(b, dict)]
    calls = [{"tool": c["tool"], "args": c.get("args") or {}, "result": _short(c.get("result"))} for c in row.get("calls") or []]
    return {
        "mode": "replay (the robot does not move; the logged move was already executed)",
        "step": row.get("step"),
        "rules": rules_text(),
        "observation": {"odometry": obs.get("odometry"), "last_move": obs.get("last_move"), "counters": obs.get("counters"),
                        "detections": obs.get("detections")},
        "previous_pose": (prev or {}).get("pose"),
        "previous_map": entries(prev),
        "tool_results": calls,
        "report_fields": {"pose": rep.get("pose"), "pose_source": rep.get("pose_source"),
                          "associations": rep.get("associations"), "loop_closure": rep.get("loop_closure"),
                          "map": entries(rep), "map_labels": sorted(l for l in _labels(rep.get("map")) if l)},
        "material_events": material_events(rep, prev),
    }


# ---------------------------------------------------------------- code-scored criterion

def sentences(note):
    s = re.sub(r"(\d)\.(\d)", r"\1<dot>\2", note.strip())
    return [p for p in re.split(r"(?<=[.!?])\s+", s) if p.strip()]


def concise_level(note):
    """Code-scored: 2 = one sentence of at most 45 words, in the first person; 1 = at most two sentences and
    60 words; 0 = longer, not first person, contains JSON braces, or empty."""
    if not isinstance(note, str) or not note.strip() or "{" in note:
        return 0
    n_s, n_w = len(sentences(note)), len(note.split())
    first = re.search(r"\b(I|my|me)\b", note) is not None
    if not first:
        return 0
    if n_s == 1 and n_w <= 45:
        return 2
    if n_s <= 2 and n_w <= 60:
        return 1
    return 0


# ---------------------------------------------------------------- the judge

SCHEMA = {"type": "object",
          "properties": {"reason": {"type": "string"},
                         "faithful": {"type": "integer", "enum": [0, 1, 2]},
                         "coverage": {"type": "integer", "enum": [0, 1, 2]},
                         "uncertainty": {"type": "integer", "enum": [0, 1, 2]}},
          "required": ["reason", "faithful", "coverage", "uncertainty"]}


def judge_prompt(evidence, note, reverse_anchors=False):
    order = (2, 1, 0) if reverse_anchors else (0, 1, 2)
    lines = ["You are grading one status note written by a robot's SLAM agent after one step.",
             "Score each criterion 0, 1 or 2 using ONLY the anchors below and ONLY the EVIDENCE given.",
             "Judge each criterion on its own idea; do not let one fault lower another criterion.",
             "Length and style do not matter here. Do not reward a longer note.",
             "First write one or two sentences of reason, then the three levels. Return JSON only.", "", "ANCHORS:"]
    for k in JUDGED:
        lines.append("%s - %s" % (k, ANCHORS[k]["title"]))
        for lv in order:
            lines.append("  %d: %s" % (lv, ANCHORS[k][lv]))
    lines += ["", "EVIDENCE:", json.dumps(evidence, separators=(",", ":")), "", "NOTE:", json.dumps(note)]
    return "\n".join(lines)


def ollama_judge(model, prompt, url="http://127.0.0.1:11434/api/chat", seed=101, num_ctx=16384, timeout=600):
    """Thinking is off: with Gemma 4's default thinking a single judgment took ~1,900 tokens (~70 s);
    with think=false it took 72 tokens (5.2 s) on the Spark (2026-10-29)."""
    body = {"model": model, "stream": False, "format": SCHEMA, "think": False, "keep_alive": "30m",
            "options": {"temperature": 0, "seed": seed, "num_ctx": num_ctx},
            "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        out = json.load(resp)
    content = out["message"]["content"]
    levels = json.loads(content)
    for k in JUDGED:
        if levels.get(k) not in (0, 1, 2):
            raise ValueError("judge level out of range: %r" % levels)
    return {"levels": {k: levels[k] for k in JUDGED}, "reason": levels.get("reason", ""),
            "eval_count": out.get("eval_count"), "prompt_eval_count": out.get("prompt_eval_count"),
            "total_duration_s": (out.get("total_duration") or 0) / 1e9}


STRICT_SCHEMA = dict(SCHEMA, additionalProperties=False)
JUDGE_PRICE = {  # USD per million tokens (evidence/M1/M1.T11/model-candidates.md, OpenAI pricing table, 2026-10-07)
    "gpt-6.1-sol": {"input": 2.0, "cached_input": 0.10, "output": 10.0},
}

# Judges (Xiaohui, 2026-10-29): GPT-6.1 Sol (OpenAI API) and Gemma 4 26B (local, Ollama). Neither is
# from the agent's family (Anthropic), which removes the self-preference risk by design.
# Judge-selection rule, fixed on 2026-10-29 before any judge was run on pilot data. A judge is
# eligible to produce the reported rubric scores only if, on the calibration sets, (a) linear-weighted
# kappa against the known levels is >= 0.6 and exact accuracy >= 0.7 for each judged criterion,
# (b) it gives faithful = 0 to >= 80 % of real notes with an injected false claim, and (c) >= 90 % of
# levels are unchanged by a repeat run, by reversed anchor order and by a neutral padding sentence.
# Among eligible judges, the one with the highest mean known-label accuracy is used; a tie goes to the
# local judge.
THRESHOLDS = {"kappa": 0.6, "accuracy": 0.7, "fabrication_detect": 0.8, "invariance": 0.9}


def _levels_from_text(text):
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip())
    obj = json.loads(t[t.find("{"): t.rfind("}") + 1])
    for k in JUDGED:
        if obj.get(k) not in (0, 1, 2):
            raise ValueError("judge level out of range: %r" % obj)
    return {k: obj[k] for k in JUDGED}, obj.get("reason", "")


def openai_judge(client, model, prompt, effort="medium"):
    """OpenAI Responses API with a strict JSON-schema output (structured outputs)."""
    r = client.responses.create(model=model, input=prompt, reasoning={"effort": effort},
                                text={"format": {"type": "json_schema", "name": "rubric_levels",
                                                 "schema": STRICT_SCHEMA, "strict": True}})
    levels, reason = _levels_from_text(r.output_text)
    u = r.usage
    cached = getattr(getattr(u, "input_tokens_details", None), "cached_tokens", 0) or 0
    p = JUDGE_PRICE[model]
    cost = ((u.input_tokens - cached) * p["input"] + cached * p["cached_input"] + u.output_tokens * p["output"]) / 1e6
    return {"levels": levels, "reason": reason, "input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
            "cost_usd": cost}


def score(levels, concise):
    """Weighted rubric score in [0, 1] (Module 9 eq. 11.1) with the faithfulness gate."""
    allv = dict(levels, concise=concise)
    assert abs(sum(WEIGHTS.values()) - 1) < 1e-9
    s = sum(WEIGHTS[k] * allv[k] / 2 for k in WEIGHTS)
    return 0.0 if allv["faithful"] == 0 else s


# ---------------------------------------------------------------- calibration items

def _pose_clause(evidence, with_reason):
    rf = evidence["report_fields"]
    src = rf.get("pose_source")
    words = POSE_WORDS.get(src, src)
    pose = rf.get("pose") or {}
    base = "my pose (%.2f, %.2f, %.1f) comes from %s" % (pose.get("x_m", 0), pose.get("y_m", 0), pose.get("theta_deg", 0), words)
    if not with_reason:
        return base
    fix = next((c["result"] for c in evidence["tool_results"] if c["tool"] == "fix_pose" and isinstance(c["result"], dict)
                and "error" not in c["result"]), None)
    full, pos = (fix or {}).get("full"), (fix or {}).get("position")
    if src == "beacon_fix" and full:
        return base + " (residual %.2f m)" % (full.get("residual_m") or 0)
    if src == "odometry":
        return base + " because no matched confirmed beacon gave a fix"
    if src == "position_fix":
        why = ("only one confirmed beacon matched" if not full else
               "the full fix was not well conditioned" if not full.get("well_conditioned") else
               "the full fix was outside the prior gate")
        return base + " because %s, so I kept my heading" % why
    if src == "prior_kept" and pos:
        why = ("the position fix was outside the prior gate" if not pos.get("within_prior_gate") else
               "the beacon bearings disagreed with my heading")
        return base + " because %s, so I kept the prior" % why
    return None


def _event_clause(e):
    m = re.match(r"new tentative beacon (\S+) from det (\S+)(.*)", e)
    if m:
        return "I added %s as a new tentative beacon%s" % (m.group(1), m.group(3))
    m = re.match(r"det (\S+) \(id (\S+)\) (rejected|ambiguous)", e)
    if m:
        return ("I rejected det %s (id %s)" if m.group(3) == "rejected" else "det %s (id %s) was ambiguous") % (m.group(1), m.group(2))
    m = re.match(r"(\S+) became confirmed", e)
    if m:
        return "I confirmed %s" % m.group(1)
    m = re.match(r"loop closure on (\S+) (accepted|not accepted)", e)
    if m:
        return ("I accepted a loop closure on %s" if m.group(2) == "accepted" else "I did not accept the loop closure on %s") % m.group(1)
    return "I noted that " + e


def synth_note(evidence, drop_events=0, pose_mode="reason", fabricate=None, wrong_label=False):
    """A note assembled by code from the evidence with controlled defects, and its expected levels.
    drop_events: how many material events to leave out; pose_mode: 'reason' | 'plain' | 'none';
    fabricate: a false clause (expected faithful 0); wrong_label: swap one real label for a wrong one
    (expected faithful 1)."""
    events = list(evidence["material_events"])
    if drop_events > len(events):
        return None
    kept = events[: len(events) - drop_events]
    parts = []
    if pose_mode != "none":
        clause = _pose_clause(evidence, pose_mode == "reason")
        if clause is None:
            return None
        parts.append(clause)
    parts += [_event_clause(e) for e in kept]
    text = "; ".join(parts) if parts else "I processed this step"
    text = text[0].upper() + text[1:]
    exp = {"faithful": 2, "coverage": 2 if len(events) - len(kept) == 0 else (1 if len(events) - len(kept) == 1 else 0),
           "uncertainty": {"reason": 2, "plain": 1, "none": 0}[pose_mode]}
    if wrong_label:
        labs = re.findall(r"\bB\d+b?\b", text)
        if not labs:
            return None
        lab = labs[-1]
        swapped = lab[:-1] if lab.endswith("b") else lab + "b"
        if swapped in evidence["report_fields"]["map_labels"]:
            return None
        text = re.sub(r"\b%s\b" % re.escape(lab), swapped, text, count=1)
        exp["faithful"] = 1
    if fabricate:
        text += "; " + fabricate
        exp["faithful"] = 0
    return {"note": text + ".", "expected": exp}


def fabrication(evidence, rng):
    """A clause asserting an event that did not happen in this step."""
    rf = evidence["report_fields"]
    labels = set(rf["map_labels"])
    unused = [i for i in range(30) if "B%d" % i not in labels]
    options = []
    if rf.get("pose_source") != "beacon_fix":
        options.append("I fixed my pose from B%d and B%d with a full beacon fix" % tuple(rng.sample(unused, 2)))
    options.append("I closed a loop on B%d and accepted it" % rng.choice(unused))
    options.append("I confirmed B%d" % rng.choice(unused))
    return rng.choice(options)


PADDING = " This note covers step %d of the replay."


def unsupported_labels(note, report):
    """Code cross-check: beacon labels named in the note that appear nowhere in the report."""
    rep = report or {}
    known = _labels(rep.get("map")) | {a.get("beacon") for a in rep.get("associations") or [] if isinstance(a, dict)} \
        | {lc.get("beacon") for lc in rep.get("loop_closure") or [] if isinstance(lc, dict)}
    return sorted(set(re.findall(r"\bB\d+b?\b", note or "")) - known)


# ---------------------------------------------------------------- agreement statistics (pure Python)

def weighted_kappa(a, b, levels=(0, 1, 2)):
    """Cohen's kappa with linear weights (Cohen 1968): 1 - sum(w*o)/sum(w*e), w = |i-j|."""
    n = len(a)
    if n == 0:
        return None
    k = len(levels)
    idx = {v: i for i, v in enumerate(levels)}
    obs = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        obs[idx[x]][idx[y]] += 1.0 / n
    pa = [sum(obs[i][j] for j in range(k)) for i in range(k)]
    pb = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    num = sum(abs(i - j) * obs[i][j] for i in range(k) for j in range(k))
    den = sum(abs(i - j) * pa[i] * pb[j] for i in range(k) for j in range(k))
    return None if den == 0 else 1.0 - num / den


def rng_for(tag):
    return random.Random("judge-%s" % tag)
