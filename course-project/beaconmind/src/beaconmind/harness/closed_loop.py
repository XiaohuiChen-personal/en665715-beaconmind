"""Closed loop in the simulator: the agent's own move is validated, executed, and decides the next observation
(work list 4.1; AGENT-DESIGN D4-D8; plan C2, C3, C5, C9; M2.T7 closed-loop part, M2.T19).

The replay study (harness/replay.py) fed every arm the same recorded observations. Here each step is:

  environment -> raw observation -> OBSERVATION (validator's safety flags and latch, the arm's own counters)
  -> driver.step(...)  (the frozen provider tool loop, or the coded procedure B2 through the same tools)
  -> report parsed and checked exactly as in replay (same fallback and repair rules, same counter rule)
  -> the accepted move is checked again by harness/validator.py and sent to the environment
  -> one JSON line per step (the replay row's fields plus the closed-loop fields).

What executes (the contract of the frozen v3.3 prompt, "Move only via move(action) ... at most one executed move per
obs_id"; M2.T1: the `move` tool is the only path to motion):
- The move that runs is the one `move(action)` call the tool dispatcher accepted in this step
  (`out["state"]["moved"]`), and only if `validator.check_move` accepts it too and no latch is set at the moment of
  execution (emergency_stop later in the same step, an auto-latch, a latch file that appeared while the model was
  thinking). It runs even when the step's report is invalid (a fallback), because the model was already told
  `done`. `env.step(action)` is called in exactly one place for a new move, behind those checks; a write-ahead
  line in `<episode>.moves.jsonl` records every commanded move before the executor is called.
- The report's `decision` is logged beside it. A move decision without an accepted `move` call executes nothing
  (`move_result` would be `not_called`); a disagreement is logged as `decision_mismatch`.
- A refused `move` is answered `{"result": "refused", "reason": ...}` inside the step, so the model can decide
  again in the same step, as guardrail 1 of the prompt says. The next OBSERVATION's `last_move` then tells what
  happened: the executed move with the executor's result; `{action, "refused"}` when the step's only move calls
  were refused (or the validator or executor overruled an accepted one); `{action, "not_called"}` when the report
  named a move that was never called; null when the step decided no move. A step without motion has zero odometry
  (never null: null means a Pico reboot).
- In this simulator a move completes at once, so the dispatcher's in-step answer `done` is true. An executor that
  can stall would report the real result in the next `last_move` (D7 row 1 reads it there).

How an episode ends (C9.2 `ended_by`): the report's decision is DONE (`DONE`) or STOPPED (`STOPPED`); the latch is set
by emergency_stop or the validator's auto-latch (`latch`); the step budget is used up (`budget`, detail `steps`, or
`max_steps` for a shortened run); the driver itself stops (`error`, detail `driver stopped`: B2 on a branch the
procedure does not implement); MAX_IDLE_STEPS consecutive steps executed no move (`error`, detail `no_progress`:
nobody answers an ASK in an unattended run, and a model that never calls `move` would otherwise idle to the budget).
The USD cap does not end an episode: the unfinished step is left unwritten and a rerun resumes it.

Environment protocol (anything with these four members can be driven; `KinsimSquareEnv` below is the study's
2.25 m square, `RawStepEnv` adapts a simulator that returns kinsim_lite raw steps):
  env.source                 "sim" | "kinsim" | "real"            (OBSERVATION.source)
  env.describe() -> dict     arena, noise, world: for run.json and scoring only, never shown to the model
  env.reset(seed) -> sense   the first sensing
  env.step(action) -> sense  execute one D4 move (or None: sense again without moving), then sense
  env.truth() -> pose        ground truth, for scoring only
  env.deterministic_replay   optional, default false: true only for a simulator that reproduces an episode from
                             the seed and the move sequence. Only such an environment can be resumed, because a
                             resume sends the logged moves again; a real car never sets it.
A sense is {"odometry": {forward_m, left_m, dtheta_deg} | None, "move": {"action", "result", "reason"} | None,
"safety": {"forward_allowed": [...], optional "turn_allowed", "scan_allowed", "backward_allowed"},
"detections": [{det, id, range_m, bearing_deg, quality, _tag}]}, plus optionally, for a backend that can fail,
"status": {"status": "ok" | "error", "error": text | None, "sensors": {camera, imu, pico}, "odometry_quality":
"ok" | "slip_suspected"} (car/backend.py's form; the same keys flat in the sense are accepted too). The observation
then carries them (C3), and no move runs on `status: error`.
`step(action)` must report the commanded move back in "move"; anything else stops the episode with an exception.
`_tag` (the true tag) is stripped before the model sees anything. The environment must be deterministic given the seed and the move sequence: a resume re-simulates
the logged moves and refuses to continue if the observations differ.

Derived from: harness/replay.py `replay_seed` (the step bookkeeping) and envs/kinsim_lite.py `run_episode` (how a
raw step is produced from a pose, a move and noise); both are imported, not copied, except the move-noise lines of
`run_episode`, which are repeated in `KinsimSquareEnv.step` because `run_episode` has no step function.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote the closed loop, the environment adapters, the
B2 and Anthropic drivers and the C9.2 export.
"""
import json
import os
import pathlib
import random
import time

from beaconmind import geometry as g
from beaconmind.envs import kinsim_lite as ks
from beaconmind.harness import replay as rp
from beaconmind.harness import tools_d5 as t5
from beaconmind.harness import validator as vd

STEPS_BUDGET = ks.STEPS_BUDGET
MAX_IDLE_STEPS = 3
MISSION = rp.MISSION
MOVE_GEOMETRY = {"FORWARD_25": (0.25, 0.0), "FORWARD_10": (0.10, 0.0), "BACKWARD_10": (0.10, 0.0),
                 "TURN_LEFT_30": (0.0, 30.0), "TURN_RIGHT_30": (0.0, -30.0)}
MOVE_LIMITS = {"v_max_mps": 0.15, "w_max_dps": 45.0, "timeout_s": 5.0}    # configs/dv.json v_max_mps, turn_rate_dps, move_timeout_s


class ResumeMismatch(RuntimeError):
    """The simulator did not reproduce a logged step, so the episode cannot be continued."""


# ---------------------------------------------------------------- environments

class KinsimSquareEnv:
    """The study's arena (kinsim_lite: 2.25 m square, seeded D3 world, placeholder noise) behind the protocol.
    Driven by B2 it reproduces kinsim_lite.run_episode step for step (tests/test_closed_loop.py)."""

    source = "sim"
    deterministic_replay = True        # a resume may send the logged moves again: this is a simulator

    def __init__(self, n_dup=3, odo_bias=0.0):
        self.n_dup, self.odo_bias = n_dup, odo_bias
        self.world, self._rng, self._truth, self._last_forward = None, None, None, 0.0

    def describe(self):
        return {"env": "kinsim_lite study square", "arena": ks.ARENA, "noise": dict(ks.NOISE, odo_bias=self.odo_bias),
                "n_dup": self.n_dup, "wall_limit_m": ks.WALL_LIMIT_M, "world": self.world,
                "contacts_simulated": False}

    def reset(self, seed):
        self.world = ks.make_world(seed, n_dup=self.n_dup)
        self._rng = random.Random("noise-%s" % seed)
        self._truth = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
        self._last_forward = 0.0
        return self._sense(None, None)

    def truth(self):
        return dict(self._truth)

    def _sense(self, odo, move):
        return {"odometry": odo, "move": move, "detections": ks.detect(self.world, self._truth, self._rng),
                "safety": {"forward_allowed": ks.forward_allowed(self._truth), "turn_allowed": True, "scan_allowed": True}}

    def step(self, action):
        if action is None:
            return self._sense({"forward_m": 0.0, "left_m": 0.0, "dtheta_deg": 0.0}, None)
        if action not in vd.MOVES:
            raise ValueError("not a move: %r" % (action,))
        zero = {"forward_m": 0.0, "left_m": 0.0, "dtheta_deg": 0.0}
        rng, bias = self._rng, self.odo_bias
        if action.startswith("FORWARD"):
            # the executor's own limit (C2: the Pico refuses what is outside its caps); the validator refuses first
            if action not in ks.forward_allowed(self._truth):
                return self._sense(zero, {"action": action, "result": "refused", "reason": "executor: wall limit"})
            f = MOVE_GEOMETRY[action][0]
            self._truth = g.compose_odometry(self._truth, f, 0.0, 0.0)
            odo = dict(zero, forward_m=round(f * (1 + bias + rng.gauss(0.0, ks.NOISE["wheel_scale_sigma"])), 2))
            self._last_forward = f
        elif action == "BACKWARD_10":
            f = min(0.10, self._last_forward)        # D4: the lesser of 0.10 m and what the previous forward move covered
            if f <= 0.0:
                return self._sense(zero, {"action": action, "result": "refused", "reason": "executor: no forward move before"})
            self._truth = g.compose_odometry(self._truth, -f, 0.0, 0.0)
            odo = dict(zero, forward_m=-round(f * (1 + bias + rng.gauss(0.0, ks.NOISE["wheel_scale_sigma"])), 2))
            self._last_forward = 0.0
        else:
            dth = MOVE_GEOMETRY[action][1]
            self._truth = g.compose_odometry(self._truth, 0.0, 0.0, dth)
            odo = dict(zero, dtheta_deg=round(dth * (1 + bias) + rng.gauss(0.0, ks.NOISE["gyro_sigma_deg"]), 1))
            self._last_forward = 0.0
        a = ks.ARENA
        if not (a["x0"] < self._truth["x_m"] < a["x1"] and a["y0"] < self._truth["y_m"] < a["y1"]):
            raise RuntimeError("simulator error: the car left the arena after %s" % action)
        return self._sense(odo, {"action": action, "result": "done", "reason": None})


class RawStepEnv:
    """Adapter for a simulator whose reset(seed) and step(move) return kinsim_lite raw steps
    ({"odometry", "last_move": {"action", "result"} | None, "safety": {...}, "detections": [...]}), such as
    envs/kinsim_room.py KinSimEnv. `truth_fn(sim)` gives the true pose, `describe_fn(sim)` the description for
    run.json, and `idle_fn(sim)` a raw step sensed again without moving (a step in which the agent decided no move).
    The simulator's own counters are ignored: the harness keeps the arm's counters (verified fixes only)."""

    deterministic_replay = True        # a simulator: a resume may send the logged moves again

    def __init__(self, sim, truth_fn, describe_fn, idle_fn, source="sim"):
        self.sim, self._truth_fn, self._describe_fn, self._idle_fn, self.source = sim, truth_fn, describe_fn, idle_fn, source

    def describe(self):
        return self._describe_fn(self.sim)

    def truth(self):
        t = self._truth_fn(self.sim)
        return {k: t[k] for k in ("x_m", "y_m", "theta_deg")}

    @staticmethod
    def _sense(raw, action):
        move = None
        if action is not None:
            lm = raw.get("last_move") or {}
            if lm.get("action") != action:
                raise RuntimeError("the simulator reports last_move %r after %s" % (lm, action))
            move = {"action": action, "result": lm["result"],
                    "reason": "executor: not allowed by the simulator" if lm["result"] == "refused" else None}
        odo = raw.get("odometry")
        if odo is not None:
            odo = {k: odo[k] for k in ("forward_m", "left_m", "dtheta_deg")}
        elif raw.get("step"):
            odo = {"forward_m": 0.0, "left_m": 0.0, "dtheta_deg": 0.0}
        return {"odometry": odo, "move": move, "safety": dict(raw["safety"]), "detections": raw["detections"]}

    def reset(self, seed):
        return self._sense(self.sim.reset(seed), None)

    def step(self, action):
        if action is None:
            sense = self._sense(self._idle_fn(self.sim), None)
            sense["odometry"] = {"forward_m": 0.0, "left_m": 0.0, "dtheta_deg": 0.0}
            return sense
        return self._sense(self.sim.step(action), action)


def room_env(world, start_pose=None, preset="camera", max_range_m=2.0, odometry="study", drive_inset_m=0.0):
    """envs/kinsim_room.py KinSimEnv for a world file (the real room) behind the protocol."""
    from beaconmind.envs import kinsim_room as kr
    sim = kr.KinSimEnv.room(world, start_pose=start_pose, preset_name=preset, max_range_m=max_range_m, odometry=odometry,
                            drive_inset_m=drive_inset_m)

    def describe(s):
        return {"env": "kinsim_room", "world_file": str(world) if not isinstance(world, dict) else None,
                "start_pose": start_pose, "preset": preset, "max_range_m": max_range_m, "odometry": odometry,
                "drive_inset_m": drive_inset_m, "session": getattr(s, "session", None), "noise": s.noise, "carpet": s.carpet, "wall_limit_m": s.wall_limit_m, "scene": s.scene,
                "world": s.world, "contacts_simulated": False}

    def idle(s):
        return s.observe()             # sense again from the unchanged pose: zero odometry, last_move None, new draws

    return RawStepEnv(sim, lambda s: s.truth_pose(), describe, idle)


# ---------------------------------------------------------------- drivers

class B2Driver:
    """The coded procedure as a driver with the provider interface: it makes its tool calls through the same
    dispatcher as a model, including `move`, and answers with its report as JSON text. Free and deterministic: the
    reference for every closed-loop episode.

    `policy(raw, prev_report) -> (report, calls, est)` is the procedure: by default the frozen kinsim_lite one
    (estimate_step + decide_step, as kinsim_lite.run_episode applies it); for the room, envs/kinsim_room.py
    `make_b2_policy()` (the same code plus the dead-end branch the square never needed). A branch the procedure does
    not implement stops the episode (`stop` in the step record; the loop ends it as `error`, "driver stopped")."""

    arm, provider = "B2", "coded_procedure"

    def __init__(self, policy=None, policy_name="kinsim_lite"):
        self.policy, self.policy_name = policy or self._frozen, policy_name

    @staticmethod
    def _frozen(raw, prev):
        est = ks.estimate_step(raw, prev)
        mem = ks.initial_memory() if prev is None else prev["memory"]
        decision, m2 = ks.decide_step(est, mem, raw["safety"], raw["counters"]["steps_left"])
        for e in est["new_entries"]:
            e["first_seen_scan"] = m2["scan_index"]
        report = {"step": raw["step"], "mode": "closed_loop", "mission": MISSION, "pose": ks.rp(est["pose"]),
                  "pose_source": est["pose_source"],
                  "associations": [{k: v for k, v in a.items() if k != "conflict"} for a, _ in est["assoc"]],
                  "loop_closure": est["loop_closure"], "map": est["new_map"], "memory": m2, "decision": decision,
                  "move_result": "not_called", "requested_mission": None, "message": None, "note": None}
        return report, est["calls"], est

    def header(self):
        return {"provider": self.provider, "settings": {"policy": self.policy_name}, "price_usd_per_mtok": None,
                "max_turns": None}

    def step(self, system_text, obs, prev, budget, log, sample_key=None):
        t0 = time.perf_counter()
        state, calls = {"moved": None, "estop": False}, []

        def call(name, args):
            res = t5.rnd(t5.run_tool(name, args, obs, prev, state))
            calls.append({"tool": name, "args": args, "result": res})
            return res

        def out(final, error, stop=None):
            rec = {"final_text": final, "calls": calls, "turns": [], "state": state, "error": error,
                   "seconds": round(time.perf_counter() - t0, 3), "cost_usd": 0.0}
            if stop:
                rec["stop"] = stop
            return rec

        try:
            report, gold, est = self.policy(obs, prev)
        except NotImplementedError as exc:
            return out(None, "B2 stopped: %s" % exc, stop="B2 stopped: %s" % exc)
        except (ks.GoldUnavailable, KeyError, TypeError) as exc:
            return out(None, "B2 cannot process this step: %s: %s" % (type(exc).__name__, exc))
        for name, args in gold:
            call(name, args)
        call("exploration_summary", {"pose": est["pose"]})
        decision = report["decision"]
        report["move_result"] = call("move", {"action": decision})["result"] if decision in vd.MOVES else "not_called"
        return out(json.dumps(report), None)


def price_cost(usage, price):
    """US$ of one Anthropic turn from its usage block and a price table {input, cache_write_5m, cache_read, output}
    in US$ per million tokens."""
    return (usage.get("input_tokens", 0) * price["input"] + usage.get("cache_creation_input_tokens", 0) * price["cache_write_5m"]
            + usage.get("cache_read_input_tokens", 0) * price["cache_read"] + usage.get("output_tokens", 0) * price["output"]) / 1e6


class _ClientTap:
    """Stands between the frozen tool loop and the Anthropic client for one step. It changes no request and no
    response. It notes, per response, how many tool calls the turn holds (the frozen loop keeps one flat call list)
    and any refusal details, and it books the difference between this model's price and the price table the frozen
    loop was written with (Claude Opus 5.5's), so the spend cap counts real dollars for every model."""

    def __init__(self, client, price, base_cost, usage_of, budget):
        self._client, self._price, self._base_cost, self._usage_of, self._budget = client, price, base_cost, usage_of, budget
        self.messages, self.turns = self, []

    def create(self, **kwargs):
        resp = self._client.messages.create(**kwargs)
        usage = self._usage_of(resp)
        cost = price_cost(usage, self._price)
        delta = cost - self._base_cost(usage)
        if abs(delta) > 1e-12:
            self._budget.add(delta)
        details = getattr(resp, "stop_details", None)
        if details is not None and hasattr(details, "model_dump"):
            details = details.model_dump(exclude_none=True)
        self.turns.append({"cost_usd": cost, "stop_details": details,
                           "tool_uses": sum(1 for b in resp.content if getattr(b, "type", None) == "tool_use")})
        return resp


class AnthropicDriver:
    """A Claude model through the frozen Anthropic tool loop (harness/providers/anthropic_messages.py `agent_step`):
    the same system block, tools, cache breakpoints, retry rule and turn cap as the study's Opus 5.5 arm. Only the
    request settings (model, max_tokens, effort) and the price table are parameters."""

    provider = "anthropic_messages"

    def __init__(self, client, key, settings, price):
        from beaconmind.harness.providers import anthropic_messages as am
        self._am, self.client, self.key = am, client, key
        self.settings, self.price = dict(settings), dict(price)
        self.arm = "L2:" + key
        self.tools = t5.anthropic_tool_defs()

    def header(self):
        return {"provider": self.provider, "settings": self.settings, "price_usd_per_mtok": self.price,
                "max_turns": self._am.MAX_TURNS}

    def step(self, system_text, obs, prev, budget, log, sample_key=None):
        am = self._am
        tap = _ClientTap(self.client, self.price, am.turn_cost, am._usage, budget)
        blocks = [{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}]
        out = am.agent_step(tap, blocks, self.tools, obs, prev, budget, log, self.settings)
        if len(tap.turns) != len(out["turns"]):
            raise RuntimeError("internal error: %d responses seen for %d logged turns" % (len(tap.turns), len(out["turns"])))
        for turn, seen in zip(out["turns"], tap.turns):
            turn["cost_usd"] = round(seen["cost_usd"], 5)
            turn["tool_uses"] = seen["tool_uses"]
            if seen["stop_details"]:
                turn["stop_details"] = seen["stop_details"]
        out["cost_usd"] = round(sum(t["cost_usd"] for t in out["turns"]), 5)
        return out


# ---------------------------------------------------------------- one step, shared by the live loop and a resume

class _Episode:
    """The harness state of one episode: counters, validator, the pending sensing and the next `last_move`."""

    def __init__(self, env, seed, validator):
        self.env, self.seed, self.val = env, seed, validator
        self.tracker = ks.CounterTracker()
        self.sense = env.reset(seed)
        self.last_move = None              # what the next OBSERVATION shows as last_move
        self.motion = None                 # the move that actually ran before this observation (for the counters)
        self.counter_src = None

    def observe(self, step):
        """(raw, obs) for this step from the pending sensing. The validator sees the observation first (latch files,
        error and reboot auto-latch), so a latched observation says so."""
        st = self.sense.get("status") or {}
        if not isinstance(st, dict):                       # the flat form: status, error and sensors beside each other
            st = {"status": st, "error": self.sense.get("error"), "sensors": self.sense.get("sensors")}
        status = st.get("status", "ok")
        self.val.poll()
        self.val.note_observation(step, status, self.sense["odometry"] is None)
        counters = self.tracker.before_step({"odometry": self.sense["odometry"], "last_move": self.motion}, self.counter_src)
        raw = {"step": step, "odometry": self.sense["odometry"], "last_move": self.last_move,
               "counters": dict(counters, steps_left=STEPS_BUDGET - step),
               "safety": self.val.safety(self.sense["safety"]), "detections": self.sense["detections"]}
        obs = ks.as_observation(self.seed, raw, counters, mode="closed_loop")
        obs["source"] = self.env.source
        if status != "ok":
            obs["status"], obs["error"] = "error", str(st.get("error") or "environment error")
        if isinstance(st.get("sensors"), dict):
            obs["sensors"] = dict(st["sensors"])
        if st.get("odometry_quality") == "slip_suspected" and obs["odometry"]:
            obs["odometry"]["quality"] = "slip_suspected"
        obs["counters"].update(self.val.counters())
        return raw, obs

    def advance(self, action, last_move_if_idle, continuing):
        """Send `action` to the environment (None: no move this step) and take the next sensing. Returns the executed
        move record or None. With no move and `continuing` false (the episode ends here) nothing is sensed."""
        if action is None:
            self.val.after_step(None)
            self.last_move, self.motion = last_move_if_idle, None
            if continuing:
                self.sense = self.env.step(None)
            return None
        self.sense = self.env.step(action)
        mv = self.sense.get("move")
        if not isinstance(mv, dict) or mv.get("action") != action or mv.get("result") not in vd.RESULTS:
            raise RuntimeError("the environment did not report the commanded move %s: %r" % (action, mv))
        self.val.after_step({"action": action, "result": mv["result"]})
        self.last_move = {"action": action, "result": mv["result"]}
        self.motion = self.last_move if mv["result"] in vd.MOTION_RESULTS else None
        return {"action": action, "result": mv["result"], "reason": mv.get("reason"), "odometry": self.sense["odometry"]}


def _idle_last_move(verdicts, accepted, decision):
    """The next OBSERVATION's last_move for a step in which no move was sent to the executor."""
    if accepted is not None:                                   # accepted by the dispatcher, overruled by the validator
        return {"action": accepted["action"], "result": "refused"}
    named = [v["action"] for v in verdicts if v["action"] in vd.MOVES]
    if named:
        return {"action": named[-1], "result": "refused"}
    if decision in vd.MOVES:
        return {"action": decision, "result": "not_called"}
    return None


def _journal(path, record):
    """Write-ahead note of a move: `commanded` before the executor is called, `result` after. If the process dies
    between the two, the step row is missing but this file shows that a move was sent."""
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(record, t=round(time.time(), 3))) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def run_episode(agent, system_text, env, seed, out_path, budget, max_steps=STEPS_BUDGET, log=print, config=None,
                autolatch_contacts=vd.AUTOLATCH_CONTACTS, max_idle_steps=MAX_IDLE_STEPS, watch_latch_paths=()):
    """Run (or resume) one closed-loop EXPLORE episode, appending one JSON line per step to out_path.

    Returns {"complete": bool, "ended_by", "detail", "steps"}: complete is False when the USD cap stopped the
    episode before a step was written (rerun to resume). Infrastructure failures raise without writing the step and
    without moving the simulated car. A latched episode leaves `<out_path stem>.LATCH`; it is not resumed.
    `watch_latch_paths`: other latch files to obey (the project-wide data/LATCH on the real car): none may exist at
    the start, and one appearing during the episode latches it. Only an environment with `deterministic_replay`
    true (a simulator) can be resumed, because a resume sends the logged moves to the environment again."""
    out_path = pathlib.Path(out_path)
    latch_path = out_path.with_suffix(".LATCH")
    done = rp.load_done(out_path, log)
    if config is not None and any(r.get("config", config) != config for r in done):
        raise ValueError("%s holds rows of another configuration; refusing to mix them" % out_path)
    if done and done[-1].get("episode_end"):
        end = done[-1]["episode_end"]
        return {"complete": True, "ended_by": end["ended_by"], "detail": end["detail"], "steps": len(done)}
    for path in [latch_path] + list(watch_latch_paths):
        if vd.read_latch_file(path):
            raise RuntimeError("%s exists: latched (operator: python -m beaconmind.harness.validator clear-latch)" % path)
    if done and not getattr(env, "deterministic_replay", False):
        raise ResumeMismatch("%s has %d logged steps, but this environment cannot be re-simulated (a resume would "
                             "drive the logged moves again): start a new episode" % (out_path, len(done)))
    ep = _Episode(env, seed, vd.Validator(autolatch_contacts, latch_path=None))
    journal = out_path.with_suffix(".moves.jsonl")
    prev, last_valid, idle = None, None, 0
    for rec in done:                                           # resume: re-simulate the logged moves
        raw, _ = ep.observe(rec["step"])
        if raw != rec["raw"] or ep.env.truth() != rec["truth"]:
            raise ResumeMismatch("%s: the simulator does not reproduce logged step %d" % (out_path, rec["step"]))
        ex = rec.get("executed_move")
        ep.advance(ex["action"] if ex else None, rec.get("next_last_move"), True)
        ep.counter_src = rec.get("counter_source")
        prev, last_valid = rec["next_prev"], rec["last_valid"]
        idle = 0 if (ex and ex["result"] in vd.MOTION_RESULTS) else idle + 1
    ep.val.latch_path, ep.val.watch_paths = latch_path, list(watch_latch_paths)
    for step in range(len(done), max_steps):
        if budget.exceeded():
            log("seed %s: budget cap reached before step %d" % (seed, step))
            return {"complete": False, "ended_by": None, "detail": "usd cap", "steps": step}
        raw, obs = ep.observe(step)
        truth = ep.env.truth()
        out = agent.step(system_text, obs, prev, budget, lambda m, s=step: log("seed %s step %d: %s" % (seed, s, m)),
                         sample_key="%s-%d" % (seed, step))
        if out["error"] == "budget cap reached":
            log("seed %s: budget cap reached during step %d; step not written, nothing executed" % (seed, step))
            return {"complete": False, "ended_by": None, "detail": "usd cap", "steps": step}
        # ---- the report: the same rules as harness/replay.py replay_seed
        rep, repaired = t5.parse_report_ex(out["final_text"])
        checks = t5.report_checks(rep, obs)
        checks["repaired_chars"] = repaired
        if checks["valid"]:
            estimate, next_prev, fallback = rep, rep, False
            last_valid = rep
        else:
            estimate = rp.fallback_report(prev, raw["odometry"], step)
            next_prev, fallback = estimate, True
        prior = rp.harness_prior(obs, prev)
        counter_src, fix_verified = rp.verify_fix(estimate, out["calls"], prior) if not fallback else ("odometry", None)
        # ---- the decision as written, and the move the tools accepted
        written = estimate.get("decision")
        decision = written if isinstance(written, str) and written in vd.DECISIONS else "NONE"
        violations = []
        if fallback:
            violations.append({"code": "format", "detail": "invalid report (%s); harness fallback" % (out["error"] or "no valid JSON report")})
        elif decision != written:
            violations.append({"code": "format", "detail": "decision %r is not a D8 decision; treated as NONE" % (written,)})
        for c in out["calls"]:
            if isinstance(c.get("result"), dict) and c["result"].get("status") == "error":
                violations.append({"code": "invalid_tool_call", "detail": "%s: %s" % (c.get("tool"), c["result"].get("error"))})
        verdicts, accepted = vd.audit_move_calls(out["calls"], obs)
        state = out.get("state") or {}
        if (accepted["action"] if accepted else None) != state.get("moved"):
            raise RuntimeError("step %d: the provider's move state %r does not match its call list" % (step, state.get("moved")))
        for v in verdicts:
            if v["tool_result"] in ("refused", "error"):
                violations.append({"code": "guardrail", "detail": "move %r refused: %s" % (v["action"], v["tool_reason"])})
        if state.get("estop"):
            reasons = [str((c.get("args") or {}).get("reason")) for c in out["calls"] if c.get("tool") == "emergency_stop"]
            ep.val.latch("emergency_stop: %s" % "; ".join(reasons), by="agent")
        action = None
        if accepted is not None:
            # the last look before motion: the model's turn took seconds, and a STOP may have arrived meanwhile
            why = accepted["validator_reason"] if not accepted["validator_ok"] else \
                ("latched" if (ep.val.poll() or ep.val.latched) else None)
            if why is None:
                action = accepted["action"]
            else:
                violations.append({"code": "validator_override", "detail": "move %r was accepted by the tool but refused "
                                   "by the validator: %s" % (accepted["action"], why)})
        if decision != (state.get("moved") or (decision if decision not in vd.MOVES else None)):
            violations.append({"code": "decision_mismatch", "detail": "report decision %s, accepted move call %s"
                               % (decision, state.get("moved"))})
        # ---- execute, then decide whether the episode goes on
        end = None
        if action is not None:
            _journal(journal, {"step": step, "obs_id": obs["obs_id"], "phase": "commanded", "action": action})
            executed = ep.advance(action, None, True)
            _journal(journal, {"step": step, "obs_id": obs["obs_id"], "phase": "result", "action": action,
                               "result": executed["result"]})
            if executed["result"] == "refused":
                violations.append({"code": "executor_refused", "detail": "%s: %s" % (action, executed["reason"])})
        else:
            executed = None
        idle = 0 if (executed and executed["result"] in vd.MOTION_RESULTS) else idle + 1
        if ep.val.latched:
            end = ("latch", ep.val.latch_reason)
        elif out.get("stop"):
            end = ("error", "driver stopped: %s" % out["stop"])
        elif decision == "DONE":
            end = ("DONE", "decision")
        elif decision == "STOPPED":
            end = ("STOPPED", "decision")
        elif idle >= max_idle_steps:
            end = ("error", "no_progress: %d consecutive steps without an executed move (last decision %s)" % (idle, decision))
        elif step == max_steps - 1:
            end = ("budget", "steps" if max_steps >= STEPS_BUDGET else "max_steps")
        if action is None:
            ep.advance(None, _idle_last_move(verdicts, accepted, decision), end is None)
        ep.counter_src = counter_src
        if executed:
            executed["command"] = move_command(step, obs["obs_id"], action)
        row = {"seed": seed, "step": step, "arm": agent.arm, "config": config, "mode": "closed_loop", "truth": truth,
               "raw": raw, "observation": obs, "prev_report": prev, "harness_prior": prior, "report": rep,
               "checks": checks, "fallback": fallback, "estimate_pose": estimate["pose"], **out,
               "next_prev": next_prev, "last_valid": last_valid,
               "prev_source_for_counters": estimate.get("pose_source"),
               "counter_source": counter_src, "fix_verified": fix_verified,
               "decision": decision, "decision_written": written, "move_calls": verdicts, "executed_move": executed,
               "next_last_move": ep.last_move, "violations": violations,
               "validator": {"latched": ep.val.latched, "latch_reason": ep.val.latch_reason,
                             "consecutive_contacts": ep.val.consecutive_contacts},
               "episode_end": {"ended_by": end[0], "detail": end[1]} if end else None}
        with open(out_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        log("seed %s step %d: %.1fs %d calls $%.3f valid=%s fallback=%s fix=%s decision=%s executed=%s total=$%.2f %s" % (
            seed, step, out["seconds"], len(out["calls"]), out["cost_usd"], checks["valid"], fallback, fix_verified,
            written, "%s:%s" % (executed["action"], executed["result"]) if executed else None, budget.spent,
            out["error"] or ""))
        prev = next_prev
        if end:
            log("seed %s: episode ended by %s (%s) after %d steps" % (seed, end[0], end[1], step + 1))
            return {"complete": True, "ended_by": end[0], "detail": end[1], "steps": step + 1}
    raise RuntimeError("internal error: the step loop ended without an end reason")


# ---------------------------------------------------------------- C2 command and C9.2 export

def move_command(cmd_seq, obs_id, action):
    """The C2 MoveCommand (bm.move/1) of an executed move."""
    dist, ang = MOVE_GEOMETRY[action]
    return dict({"schema": "bm.move/1", "cmd_seq": cmd_seq, "obs_id": obs_id, "action": action,
                 "distance_m": dist, "angle_deg": ang}, **MOVE_LIMITS)


def _move_result(executed):
    """The C2 MoveResult (bm.move_result/1) of a simulated move. The simulator has no encoders, boot id or clock:
    those fields are 0, and the motion fields are the simulated odometry."""
    odo = executed.get("odometry") or {}
    return {"schema": "bm.move_result/1", "cmd_seq": executed["command"]["cmd_seq"], "result": executed["result"],
            "reason": executed.get("reason"), "boot_id": 0, "duration_s": 0.0, "enc_left_ticks": 0, "enc_right_ticks": 0,
            "gyro_dyaw_deg": float(odo.get("dtheta_deg") or 0.0), "achieved_forward_m": float(odo.get("forward_m") or 0.0),
            "stall": executed["result"] == "stalled", "bump": executed["result"] == "bumped"}


def to_runlog(rows, run_id, episode_id):
    """The episode as plan C9.2 lines (bm.runlog/1): one `step` line per row and an `episode_footer`.

    `llm_turns[].tool_calls` holds each turn's calls when the driver recorded how many each turn made (the Anthropic
    driver does); otherwise all of a step's calls are listed under its first turn. `report_corrected` is the report
    carried into the next step (the report as written, or the fallback): this harness measures state violations
    and does not correct them (AGENT-DESIGN D5 v3.4 note)."""
    lines, t_tokens, cost, wall = [], {"in": 0, "cached_in": 0, "out": 0}, 0.0, 0.0
    for r in rows:
        calls, turns, k = list(r.get("calls") or []), [], 0
        t_start = 0.0
        for i, t in enumerate(r.get("turns") or []):
            n = t.get("tool_uses") if t.get("tool_uses") is not None else (len(calls) if i == 0 else 0)
            tok = t.get("tokens") or {}
            turns.append({"turn": i, "t_start": round(t_start, 3), "latency_s": float(t.get("seconds") or 0.0),
                          "finish_reason": str(t.get("finish") or t.get("stop_reason") or ""),
                          "tokens_in": int(tok.get("in") or 0), "tokens_out": int(tok.get("out") or 0),
                          "tokens_reasoning": int(tok.get("reasoning") or 0), "tokens_cached_in": int(tok.get("cached_in") or 0),
                          "tool_calls": [{"name": str(c.get("tool")), "args": c.get("args"), "result": c.get("result"),
                                          "error": c["result"].get("error") if isinstance(c.get("result"), dict)
                                          and c["result"].get("status") == "error" else None} for c in calls[k:k + n]]})
            k += n
            t_start += float(t.get("seconds") or 0.0)
            for key in t_tokens:
                t_tokens[key] += int(tok.get(key) or 0)
        ex = r.get("executed_move")
        obs = r["observation"]
        lines.append({"type": "step", "schema": "bm.runlog/1", "run_id": run_id, "episode_id": episode_id,
                      "step": r["step"], "obs_id": obs["obs_id"], "mode": obs["mode"], "source": obs["source"],
                      "mission": MISSION, "operator_request": None,
                      "step_message": json.loads(rp.step_message(obs, r["prev_report"])), "llm_turns": turns,
                      "final_text": r.get("final_text") or "", "report": r.get("report"), "report_corrected": r["next_prev"],
                      "violations": r.get("violations") or [],
                      "executed_move": {"command": ex["command"], "result": _move_result(ex)} if ex else None,
                      "decision_latency_s": float(r.get("seconds") or 0.0), "cost_usd": float(r.get("cost_usd") or 0.0),
                      "gt_pose_map": {k2: float(r["truth"][k2]) for k2 in ("x_m", "y_m", "theta_deg")},
                      "det_truth": [{"det": d["det"], "uid": "T%02d" % d["_tag"] if isinstance(d["_tag"], int) else str(d["_tag"])}
                                    for d in r["raw"]["detections"]],
                      "error": r.get("error")})
        cost += float(r.get("cost_usd") or 0.0)
        wall += float(r.get("seconds") or 0.0)
    end = (rows[-1].get("episode_end") if rows else None) or {"ended_by": "error", "detail": "incomplete"}
    lines.append({"type": "episode_footer", "steps": len(rows), "ended_by": end["ended_by"], "detail": str(end["detail"]),
                  "totals": {"tokens": t_tokens, "cost_usd": round(cost, 5), "wall_s": round(wall, 1)}})
    return lines


