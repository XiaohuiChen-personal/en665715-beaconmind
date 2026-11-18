"""Validator below the LLM for closed-loop episodes (AGENT-DESIGN D4, D5 "Validator", D6 layer 2; plan C5.1, C5.2, C5.5).

Two jobs, both deterministic:

1. `check_move` decides whether one `move(action)` may run against one OBSERVATION. Inside a step the model is
   answered by the frozen tool dispatcher (`tools_d5.run_tool`, the code the v3.3 prompt was tested on); this module
   repeats the decision independently before anything is executed, with the same refusal texts for the cases the
   dispatcher knows, plus the two cases of D5 that the dispatcher does not check: `status: error` and a move beyond
   `steps_left`. A move runs only when both agree.
2. `Validator` holds the episode state the design gives the validator: the last executed move (for
   `backward_allowed`, D4), the count of consecutive contacts, and the latch. It builds the `safety` block and the
   latch fields of the OBSERVATION and auto-latches as C5.2 says.

Refusal reasons (the text the model reads in the tool result; the first that applies):
  "replay mode: the log's move is already executed"   mode is replay (C5.1)
  "status error"                                      OBSERVATION.status is error                (this module only)
  "latched"                                           the latch is set, or emergency_stop was called this step
  "not a move"                                        the action is not one of the five D4 moves
  "one executed move per obs_id"                      a move was already accepted against this observation
  "no steps left"                                     counters.steps_left is 0                    (this module only)
  "not in forward_allowed"                            a forward move that safety.forward_allowed does not list
  "backward not allowed"                              BACKWARD_10 while safety.backward_allowed is false
  "turn not allowed"                                  a turn while safety.turn_allowed is false

Choices the design leaves open, decided here (2026-11-18):
- Auto-latch follows C5.2 and configs/dv.json: after `autolatch_contacts` (2) consecutive contacts (`stalled` or
  `bumped`), or any `link_lost`. One contact does not latch, because D7 row 1 recovers from it with BACKWARD_10.
  A `done` move clears the contact count; a step without an executed move leaves it unchanged.
- `backward_allowed` is true only for the observation directly after an executed forward move whose result was
  done, stalled or bumped (D4), and only if the environment does not forbid it.
- The latch is per episode (C5.5: kinsim episodes use `<episode>.LATCH`, never the project-wide data/LATCH). Only
  `clear_latch_file` with an operator's name removes it.
- Error and reboot auto-latches (C5.2) act on what an observation shows: `autolatch_errors` (2) consecutive
  observations with status error, or null odometry after step 0. The slip auto-latch is not implemented: no
  environment reports `slip_suspected` yet.
- A latch file written by someone else (the out-of-band STOP of work list 2.7, an operator's `touch`) is obeyed:
  `Validator.poll` reads the episode's file and any watched path before every observation and again just before
  a move is executed.
- Everything fails closed: a safety flag that is missing or not a boolean refuses the move.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this validator for the closed loop (work list 4.1,
M2.T1 part, M2.T7).
"""
import json
import os
import time

from beaconmind.harness import tools_d5 as t5

MOVES = t5.MOVES
DECISIONS = MOVES + ("DONE", "NONE", "STOPPED", "ASK", "REFUSED")
RESULTS = ("done", "stalled", "bumped", "timeout", "link_lost", "refused", "not_called")
MOTION_RESULTS = ("done", "stalled", "bumped", "timeout", "link_lost")   # the car may have moved
CONTACT_RESULTS = ("stalled", "bumped")
AUTOLATCH_CONTACTS = 2      # configs/dv.json autolatch_contacts (the runner passes the file's value)
AUTOLATCH_ERRORS = 2        # configs/dv.json autolatch_errors


def check_move(action, obs, moved=None, estop=False):
    """(allowed, reason) for one move request against one OBSERVATION. `moved` is the move already accepted against
    this observation (or None) and `estop` whether emergency_stop was called earlier in the step.
    It fails closed: a flag that is missing or of the wrong type refuses the move (and a malformed observation
    without `counters` or `safety` raises, which stops the step before anything is executed)."""
    counters, safety = obs["counters"], obs["safety"]
    if obs.get("mode") != "closed_loop":
        return False, "replay mode: the log's move is already executed"
    if obs.get("status") != "ok":
        return False, "status error"
    if estop or counters.get("latched") is not False:          # a missing or non-boolean flag counts as latched
        return False, "latched"
    if not isinstance(action, str) or action not in MOVES:
        return False, "not a move"
    if moved:
        return False, "one executed move per obs_id"
    left = counters.get("steps_left")
    if not isinstance(left, int) or isinstance(left, bool) or left <= 0:
        return False, "no steps left"
    fwd = safety.get("forward_allowed")
    if action.startswith("FORWARD") and not (isinstance(fwd, (list, tuple)) and action in fwd):
        return False, "not in forward_allowed"
    if action == "BACKWARD_10" and safety.get("backward_allowed") is not True:
        return False, "backward not allowed"
    if action.startswith("TURN") and safety.get("turn_allowed") is not True:
        return False, "turn not allowed"
    return True, None


def audit_move_calls(calls, obs):
    """Re-decide every `move` call of one step in call order, beside what the tool dispatcher answered.

    Returns (verdicts, accepted). Each verdict: {action, tool_result, tool_reason, validator_ok, validator_reason,
    agree}. `accepted` is the verdict of the one call the dispatcher accepted (result not `refused`), or None."""
    verdicts, accepted, moved, estop = [], None, None, False
    for c in calls or []:
        if c.get("tool") == "emergency_stop":
            estop = True
        if c.get("tool") != "move":
            continue
        action = (c.get("args") or {}).get("action") if isinstance(c.get("args"), dict) else None
        res = c.get("result") if isinstance(c.get("result"), dict) else {}
        tool_result = res.get("result") if "result" in res else "error"
        ok, reason = check_move(action, obs, moved=moved, estop=estop)
        tool_ok = tool_result not in ("refused", "error")
        v = {"action": action, "tool_result": tool_result, "tool_reason": res.get("reason") or res.get("error"),
             "validator_ok": ok, "validator_reason": reason, "agree": ok == tool_ok}
        verdicts.append(v)
        if tool_ok:
            moved, accepted = action, v
    return verdicts, accepted


class Validator:
    """Episode state of the validator: last executed move, contact count, latch."""

    def __init__(self, autolatch_contacts=AUTOLATCH_CONTACTS, latch_path=None, autolatch_errors=AUTOLATCH_ERRORS,
                 watch_paths=()):
        self.autolatch_contacts, self.autolatch_errors = autolatch_contacts, autolatch_errors
        self.latch_path = latch_path       # this episode's latch file (written when the validator or the agent latches)
        self.watch_paths = list(watch_paths)   # other latch files to obey, e.g. the project-wide data/LATCH (C5.5)
        self.latched, self.latch_reason = False, None
        self.consecutive_contacts, self.consecutive_errors = 0, 0
        self.last_executed = None          # {"action", "result"} of the move executed in the previous step, or None

    # ---- what the OBSERVATION carries

    def safety(self, env_safety):
        """The `safety` block (without done_range_m, which kinsim_lite.as_observation adds). forward_allowed comes
        from the environment's wall check; turn and scan flags default to true when it reports none."""
        fwd = [m for m in ("FORWARD_25", "FORWARD_10") if m in (env_safety.get("forward_allowed") or [])]
        last = self.last_executed
        back = bool(last and last["action"].startswith("FORWARD") and last["result"] in ("done", "stalled", "bumped"))
        return {"forward_allowed": fwd, "backward_allowed": back and env_safety.get("backward_allowed", True) is not False,
                "turn_allowed": env_safety.get("turn_allowed", True) is not False,
                "scan_allowed": env_safety.get("scan_allowed", True) is not False}

    def counters(self):
        return {"consecutive_contacts": self.consecutive_contacts, "consecutive_errors": self.consecutive_errors,
                "latched": self.latched}

    def poll(self):
        """Obey a latch file written by someone else (the out-of-band STOP, an operator): the episode's own file and
        every watched path. Called before each observation and again just before a move is executed."""
        if self.latched:
            return True
        for path in ([self.latch_path] if self.latch_path else []) + self.watch_paths:
            found = read_latch_file(path)
            if found is not None:
                self.latched = True
                self.latch_reason = "latch file %s: %s" % (os.path.basename(str(path)), found.get("reason"))
                return True
        return False

    def note_observation(self, step, status, odometry_is_null):
        """C5.2 on what an observation shows: a Pico reboot (null odometry after step 0) latches at once, and so do
        `autolatch_errors` consecutive observations whose status is not ok."""
        if status != "ok":
            self.consecutive_errors += 1
        else:
            self.consecutive_errors = 0
        if step > 0 and odometry_is_null:
            self.latch("auto: null odometry after step 0 (Pico reboot)", by="validator")
        elif self.consecutive_errors >= self.autolatch_errors:
            self.latch("auto: %d consecutive error observations" % self.consecutive_errors, by="validator")

    # ---- what changes it

    def after_step(self, executed):
        """Record the outcome of one step. `executed` is {"action", "result"} for a move sent to the executor (its
        result may be `refused` by the executor's own limits), or None when no move was sent."""
        if executed and executed["result"] in MOTION_RESULTS:
            self.last_executed = {"action": executed["action"], "result": executed["result"]}
            if executed["result"] in CONTACT_RESULTS:
                self.consecutive_contacts += 1
            elif executed["result"] == "done":
                self.consecutive_contacts = 0
            if executed["result"] == "link_lost":
                self.latch("auto: link_lost", by="validator")
            elif self.consecutive_contacts >= self.autolatch_contacts:
                self.latch("auto: %d consecutive contacts" % self.consecutive_contacts, by="validator")
        else:
            self.last_executed = None

    def latch(self, reason, by):
        if self.latched:
            return
        self.latched, self.latch_reason = True, reason
        if self.latch_path:
            write_latch_file(self.latch_path, reason, by)


# ---------------------------------------------------------------- the per-episode latch file (C5.5)

def write_latch_file(path, reason, by):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"latched": True, "reason": reason, "by": by, "t": time.strftime("%Y-%m-%dT%H:%M:%S%z")}, fh)
        fh.write("\n")


def read_latch_file(path):
    """The latch record, or None when there is no file. A file that exists but cannot be read as JSON is still a
    latch (an operator may create it with `touch`)."""
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except FileNotFoundError:
        return None
    try:
        doc = json.loads(text)
        return doc if isinstance(doc, dict) else {"latched": True, "reason": "unreadable latch file", "by": "unknown"}
    except ValueError:
        return {"latched": True, "reason": "unreadable latch file", "by": "unknown"}


def clear_latch_file(path, operator):
    """Remove a latch file. Only an operator clears a latch (D5): a name is required and is logged beside the file."""
    if not operator or not str(operator).strip():
        raise ValueError("an operator name is required to clear a latch")
    old = read_latch_file(path)
    if old is None:
        return False
    with open(str(path) + ".cleared.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"cleared_by": str(operator), "t": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "latch": old}) + "\n")
    os.remove(path)
    return True


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Clear a per-episode latch file (operator only).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("clear-latch")
    c.add_argument("path")
    c.add_argument("--operator", required=True)
    args = ap.parse_args(argv)
    print("cleared" if clear_latch_file(args.path, args.operator) else "no latch file at %s" % args.path)


if __name__ == "__main__":
    main()
