"""Provider-neutral replay loop for the L2 agent (AGENT-DESIGN D5, D10; plan/README.md C3, C5, C9).

One stateless agent call per recorded observation: the step message carries the mission, the
OBSERVATION and the agent's own PREVIOUS_REPORT; the agent answers with tool calls (resolved by
tools_d5.run_tool) and a final D8 report. In replay mode the moves are the logged ones and the agent
only estimates. Every arm sees the identical step message, whatever its provider.

State rules (pre-registration, evidence/M4/M4.T1/prereg.md; AGENT-DESIGN v3.4 note on D5):
- The counters `travel_since_fix_m` and `turns_since_fix` are harness state. They reset only when a claimed full
  fix is supported by one of the step's own `fix_pose` results whose `prior` argument is the harness's own prior
  (PREVIOUS_REPORT's pose composed with this step's odometry) and whose fix the reported pose equals
  (`verify_fix`). That is the coded procedure's reset rule applied to the agent's own state. The 2026-10-29 pilot
  reset them on the agent's claim alone.
- The reported pose and map are scored as the agent wrote them; the harness does not overwrite them with tool
  values. Disagreements with the tool results are measured afterwards (metrics/pilot.py `state_violations`).
- An invalid report (unparseable, non-numeric or non-finite pose, malformed map) is replaced by the previous report
  dead-reckoned through this step's odometry (`fallback`, counted). A report whose content is complete but whose
  last one to three closing characters are missing is completed and counted (`checks.repaired_chars`,
  tools_d5.parse_report_ex), the same rule for every arm. Model failures inside a step (output cap,
  turn cap, context overflow) produce such a fallback row.
- Infrastructure failures (a server that keeps refusing or timing out after the provider's retries, a malformed
  request) raise out of `replay_seed` without writing the step, so a rerun resumes at that step (report Section
  IV-D: attempted up to seven times, the seed rerun once, otherwise scored as incomplete).

Each provider supplies an object with
  .arm                                   e.g. "L2:qwen38-flash-xhigh"
  .step(system_text, obs, prev, budget, log, sample_key) -> dict with final_text, calls, turns, state, error,
        seconds, cost_usd
and the loop below is the same for all of them.

Derived from: the 2026-10-29 pilot's harness/anthropic_replay.py replay_seed, generalised over providers, with
fix verification, spend persistence, torn-line recovery and a configuration tag added.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: split the pilot loop out of the Anthropic harness and
added the parts listed above (several after an adversarial review the same day).
"""
import copy
import json
import os
import threading
import time

from beaconmind import geometry as g
from beaconmind.envs import kinsim_lite as ks
from beaconmind.harness import tools_d5 as t5

# A pose must match a tool result to report rounding: 2-dp positions, 1-dp headings (the same tolerance as the
# tool-call matching rule of metrics/pilot.py).
FIX_TOL_M, FIX_TOL_DEG = 0.011, 0.11
MISSION = "EXPLORE"


class Budget:
    """Spend cap shared by the threads of one run (US$). With `path`, every addition is appended to that file at
    once, so a crash between steps cannot lose spend that a resume must count. Local models cost 0."""

    def __init__(self, cap_usd, spent=0.0, path=None):
        self.cap, self.spent, self.path, self.lock = cap_usd, spent, path, threading.Lock()

    def add(self, usd):
        with self.lock:
            self.spent += usd
            if self.path and usd:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"t": round(time.time(), 3), "usd": usd}) + "\n")
            return self.spent

    def exceeded(self):
        with self.lock:
            return self.spent >= self.cap


def spent_in(path):
    """Total of a Budget spend file (a torn last line, from a kill mid-write, is ignored)."""
    total = 0.0
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    total += json.loads(line)["usd"]
                except (ValueError, KeyError):
                    continue
    except FileNotFoundError:
        pass
    return total


def step_message(obs, prev):
    """The user message of one step: identical for every provider."""
    return json.dumps({"mission": MISSION, "operator_request": None, "OBSERVATION": obs, "PREVIOUS_REPORT": prev})


def harness_prior(obs, prev):
    """The prior the procedure uses: PREVIOUS_REPORT's pose composed with this step's odometry (start pose at step 0)."""
    if prev is None or not isinstance(prev.get("pose"), dict):
        return {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
    odo = obs.get("odometry")
    p = prev["pose"]
    try:
        p = {k: float(p[k]) for k in ("x_m", "y_m", "theta_deg")}
    except (KeyError, TypeError, ValueError):
        return None
    if not odo:
        return p
    return g.compose_odometry(p, odo["forward_m"], odo["left_m"], odo["dtheta_deg"])


def fallback_report(prev, odo, step):
    """The report the arm carried into this step, with its pose dead-reckoned through this step's odometry."""
    rep = copy.deepcopy(prev) if prev else {"pose": {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0},
                                            "map": [], "memory": ks.initial_memory()}
    if odo:
        p = g.compose_odometry(rep["pose"], odo["forward_m"], odo["left_m"], odo["dtheta_deg"])
        rep["pose"] = ks.rp(p)
    rep.update(step=step, pose_source="odometry", associations=[], loop_closure=[], decision="NONE",
               note="harness fallback: the agent's report was invalid")
    return rep


def close(pose, ref):
    try:
        return (abs(float(pose["x_m"]) - float(ref["x_m"])) <= FIX_TOL_M
                and abs(float(pose["y_m"]) - float(ref["y_m"])) <= FIX_TOL_M
                and abs(g.wrap_deg(float(pose["theta_deg"]) - float(ref["theta_deg"]))) <= FIX_TOL_DEG)
    except (KeyError, TypeError, ValueError):
        return False


def verify_fix(report, calls, prior=None):
    """The pose source the counters should use, and whether a claimed full fix was verified.

    A claimed `beacon_fix` counts only if one of this step's fix_pose calls (a) was given the harness's own prior
    (`prior`, from `harness_prior`; skipped when None), (b) returned a `full` fix that is well conditioned and inside
    the prior gate, and (c) the reported pose equals that fix (to report rounding). A claimed `relocalised` needs
    (a), a `full` fix with relocalisation_ok, and (c). Otherwise the counters treat the step as having no fix.
    Returns (counter_source, verified): counter_source is "unverified_fix" for a claim that fails; verified is None
    when no full fix was claimed."""
    src = (report or {}).get("pose_source")
    if src not in ks.FIX_SOURCES:
        return src, None
    pose = (report or {}).get("pose")
    for c in calls or []:
        if c.get("tool") != "fix_pose":
            continue
        res = c.get("result")
        full = res.get("full") if isinstance(res, dict) else None
        if not isinstance(full, dict):
            continue
        if prior is not None and not close((c.get("args") or {}).get("prior") or {}, prior):
            continue
        ok = (full.get("well_conditioned") is True and full.get("within_prior_gate") is True) if src == "beacon_fix" \
            else full.get("relocalisation_ok") is True
        if ok and close(pose, full):
            return src, True
    return "unverified_fix", False


def load_done(out_path, log=print):
    """The rows already written. A torn last line (the process was killed mid-write) is cut off the file."""
    try:
        with open(out_path, encoding="utf-8") as fh:
            lines = fh.read().split("\n")
    except FileNotFoundError:
        return []
    rows, good = [], 0
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
            good = i + 1
        except ValueError:
            if any(x.strip() for x in lines[i + 1:]):
                raise ValueError("%s: unreadable line %d is not the last one" % (out_path, i + 1))
            log("%s: dropping a torn last line (%d bytes)" % (out_path, len(line)))
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write("".join(x + "\n" for x in lines[:good] if x.strip()))
            break
    return rows


def replay_seed(agent, system_text, log_doc, out_path, budget, max_steps, log=print, config=None):
    """Replay one recorded episode through `agent`, appending one JSON line per step to out_path.
    Resumes after the last step already in out_path; a row written under another `config` tag is refused.
    Returns True when every step is written, False when the budget cap stopped it (the unfinished step is left
    unwritten, so a resume re-runs it). Infrastructure failures raise without writing the step."""
    seed = log_doc["seed"]
    done = load_done(out_path, log)
    if config is not None and any(r.get("config", config) != config for r in done):
        raise ValueError("%s holds rows of another configuration; refusing to mix them" % out_path)
    tracker = ks.CounterTracker()
    prev, last_valid, counter_src = None, None, None
    for rec in done:
        tracker.before_step(rec["raw"], counter_src)
        prev, last_valid = rec["next_prev"], rec["last_valid"]
        counter_src = rec.get("counter_source", rec.get("prev_source_for_counters"))
    records = log_doc["records"][:max_steps]
    for rec in records[len(done):]:
        if budget.exceeded():
            log("seed %s: budget cap reached before step %d" % (seed, rec["step"]))
            return False
        counters = tracker.before_step(rec["raw"], counter_src)
        obs = ks.as_observation(seed, rec["raw"], counters, mode="replay")
        out = agent.step(system_text, obs, prev, budget,
                         lambda m, s=rec["step"]: log("seed %s step %d: %s" % (seed, s, m)),
                         sample_key="%s-%d" % (seed, rec["step"]))
        if out["error"] == "budget cap reached":
            log("seed %s: budget cap reached during step %d; step not written" % (seed, rec["step"]))
            return False
        rep, repaired = t5.parse_report_ex(out["final_text"])
        checks = t5.report_checks(rep, obs)
        checks["repaired_chars"] = repaired
        if checks["valid"]:
            estimate, next_prev, fallback = rep, rep, False
            last_valid = rep
        else:
            estimate = fallback_report(prev, rec["raw"]["odometry"], rec["step"])
            next_prev, fallback = estimate, True
        prior = harness_prior(obs, prev)
        counter_src, fix_verified = verify_fix(estimate, out["calls"], prior) if not fallback else ("odometry", None)
        row = {"seed": seed, "step": rec["step"], "arm": agent.arm, "config": config, "truth": rec["truth"],
               "raw": rec["raw"], "observation": obs, "prev_report": prev, "harness_prior": prior, "report": rep,
               "checks": checks, "fallback": fallback, "estimate_pose": estimate["pose"], **out,
               "next_prev": next_prev, "last_valid": last_valid,
               "prev_source_for_counters": estimate.get("pose_source"),   # the claimed source (pilot field name)
               "counter_source": counter_src, "fix_verified": fix_verified}
        with open(out_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        log("seed %s step %d: %.1fs %d calls $%.3f valid=%s fallback=%s fix=%s total=$%.2f %s" % (
            seed, rec["step"], out["seconds"], len(out["calls"]), out["cost_usd"], checks["valid"], fallback,
            fix_verified, budget.spent, out["error"] or ""))
        prev = next_prev
    return True
