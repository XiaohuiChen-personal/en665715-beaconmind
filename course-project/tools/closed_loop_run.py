#!/usr/bin/env python3
"""Run one closed-loop EXPLORE episode per seed in the simulator: the driver's own moves are validated and executed.

Run inside beaconmind-ros on the Spark through tools/closed_loop_run.sh (it mounts the repository and the secrets
env_file, and passes the git commit); B2 needs no key and also runs on any host with Python:
  bash course-project/tools/closed_loop_run.sh --driver claude-opus-5-5 --env square --seeds 1010 \
      --out course-project/data/closed-loop/<name>/claude-opus-5-5 --cap-usd 15
  python3 course-project/tools/closed_loop_run.py --driver b2 --env room --world course-project/configs/arenas/real-room-nominal.json \
      --start 2.2,2.6,90 --seeds 1 --out course-project/data/closed-loop/<name>/b2 --cap-usd 0

- --driver: `b2` (the coded procedure through the same loop and tools; free) or a key of configs/providers.json or
  configs/providers_demo.json whose provider is anthropic_messages. The frozen `claude-opus-5-5` entry runs with the
  study's request settings unchanged; other entries take model, max_tokens and effort from their `options`.
- --env square: the study's 2.25 m arena (envs/kinsim_lite.py; the seed picks the world and the noise).
  --env room: envs/kinsim_room.py on --world with --start, --preset, --max-range, --odometry, --drive-inset (the seed
  picks the noise); B2 is then kinsim_room.make_b2_policy(). --prompt selects the system prompt (default: the
  study's frozen v3.3; prompts/robot_system_prompt_v3.3-room.txt states the room's 3.0 m range limit).
- The spend cap is hard: spend is appended to <out>/spend.jsonl as it happens (and counted again on a resume), no
  request is sent once it is reached, and an API driver needs a positive --cap-usd. If the project ledger
  data/budget/ledger.jsonl (plan C13) exists, one line per paid episode is appended to it.
- Resumable with --resume-reason under the same configuration only (the `config` tag hashes the provider entry, the
  request settings, the environment, the step limit, the prompt, the design values and every harness file). A resume
  re-simulates the logged moves and refuses to continue if the simulator does not reproduce the logged observations.
- Per seed: seed_<n>.jsonl (one row per step: the replay row's fields plus the closed-loop fields),
  seed_<n>.summary.json (metrics/closed_loop.py), seed_<n>.runlog.jsonl (plan C9.2, bm.runlog/1) and, if the
  episode latched, seed_<n>.LATCH. run.json holds the configuration and the simulated world (ground truth: it stays
  in the git-ignored data folder and is never sent to a model).
- --dv FILE (2026-11-24): the design values the run uses, e.g. configs/dv-real.json (tools/real_dv.py; it may differ
  from the frozen file only in the pilot's noise model and the range limit). Default: the frozen configs/dv.json.
  run.json records the file and its sha12 (`dv_file`); a run with another file is another configuration.
- Exit code 0 when every episode is complete, 2 when the spend cap stopped one, 1 when one failed (rerun to resume),
  3 when an episode latched: a latch ends the whole batch (the seeds after it are not run) until an operator clears
  it. `seed_<n>.moves.jsonl` is the write-ahead list of every move sent to the executor.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this runner (work list 4.1), following
tools/replay_run.py's conventions (configuration tag, spend file, lock, resume rule).
AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: added --dv (beaconmind/dv_real.py).
"""
import argparse
import fcntl
import hashlib
import json
import os
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "beaconmind" / "src"))
from beaconmind import dv as dvmod  # noqa: E402
from beaconmind import dv_real  # noqa: E402
from beaconmind.harness import closed_loop as cl  # noqa: E402
from beaconmind.harness import replay as rp  # noqa: E402
from beaconmind.metrics import closed_loop as mc  # noqa: E402

SRC = ROOT / "beaconmind" / "src" / "beaconmind"
HASHED = ("geometry.py", "dv.py", "envs/kinsim_lite.py", "envs/kinsim_room.py", "harness/tools_d5.py",
          "harness/replay.py", "harness/providers/anthropic_messages.py", "harness/closed_loop.py",
          "harness/validator.py")
PROVIDER_FILES = (ROOT / "configs" / "providers.json", ROOT / "configs" / "providers_demo.json")
FROZEN_OPUS = "claude-opus-5-5"


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def sha12(p):
    p = pathlib.Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12] if p.exists() else None


def seed_list(text):
    out = []
    for part in text.split(","):
        a, _, b = part.partition("-")
        for s in (range(int(a), int(b) + 1) if b else [int(a)]):
            if s not in out:
                out.append(s)
    return out


def provider_entry(key):
    """(entry, file) of a model key; a key must not be defined in both provider files."""
    hits = []
    for f in PROVIDER_FILES:
        if f.exists():
            models = json.loads(f.read_text(encoding="utf-8"))["models"]
            if key in models:
                hits.append((models[key], f))
    if len(hits) != 1:
        sys.exit("driver key %s: found in %d provider files (need exactly one of %s)" % (
            key, len(hits), ", ".join(f.name for f in PROVIDER_FILES)))
    return hits[0]


def anthropic_settings(key, cfg):
    """(request settings, price table) of an Anthropic entry. The frozen Opus entry uses the provider's own SETTINGS
    and PRICE, exactly as tools/replay_run.py does."""
    from beaconmind.harness.providers import anthropic_messages as am
    opt = cfg.get("options") or {}
    if key == FROZEN_OPUS:
        if cfg["model"] != am.SETTINGS["model"] or opt.get("max_tokens") != am.SETTINGS["max_tokens"] \
                or opt.get("effort") != am.SETTINGS["output_config"]["effort"]:
            sys.exit("configs/providers.json's Opus entry differs from the provider's fixed SETTINGS %s" % am.SETTINGS)
        return dict(am.SETTINGS), dict(am.PRICE)
    for need in ("max_tokens", "effort", "price_cache_write_5m_usd_per_mtok"):
        if need not in opt:
            sys.exit("provider entry %s: options.%s is required" % (key, need))
    p = cfg["price_usd_per_mtok"]
    if p.get("cached_input") is None:
        sys.exit("provider entry %s: price_usd_per_mtok.cached_input is required" % key)
    return ({"model": cfg["model"], "max_tokens": opt["max_tokens"], "output_config": {"effort": opt["effort"]}},
            {"input": p["input"], "cache_write_5m": opt["price_cache_write_5m_usd_per_mtok"],
             "cache_read": p["cached_input"], "output": p["output"]})


def build_driver(key, with_client=True, room=False):
    """(driver, provider entry or None, provider file or None, sdk versions)."""
    if key.lower() == "b2":
        if room:        # the room needs the dead-end branch the square never reaches (kinsim_room.make_b2_policy)
            from beaconmind.envs import kinsim_room as kr
            return cl.B2Driver(kr.make_b2_policy(), "kinsim_room.make_b2_policy()"), None, None, {}
        return cl.B2Driver(), None, None, {}
    cfg, path = provider_entry(key)
    if cfg["provider"] != "anthropic_messages":
        sys.exit("driver %s: provider %s is not supported by this runner (anthropic_messages or b2)" % (key, cfg["provider"]))
    settings, price = anthropic_settings(key, cfg)
    client, sdk = None, {}
    if with_client:
        import anthropic
        api_key = os.environ.get(cfg["api_key_env"] or "ANTHROPIC_API_KEY")
        if not api_key:
            sys.exit("%s is not set" % (cfg["api_key_env"] or "ANTHROPIC_API_KEY"))
        client = anthropic.Anthropic(api_key=api_key, timeout=cfg.get("request_timeout_s") or 900, max_retries=0)
        sdk = {"anthropic_sdk": anthropic.__version__}
    return cl.AnthropicDriver(client, key, settings, price), cfg, path, sdk


def build_env(args):
    if args.env == "square":
        return cl.KinsimSquareEnv()
    if not args.world:
        sys.exit("--env room needs --world")
    start = None
    if args.start:
        x, y, th = (float(v) for v in args.start.split(","))
        start = {"x_m": x, "y_m": y, "theta_deg": th}
    return cl.room_env(args.world, start_pose=start, preset=args.preset, max_range_m=args.max_range, odometry=args.odometry,
                       drive_inset_m=args.drive_inset)


def env_args(args):
    keys = ("env",) if args.env == "square" else ("env", "start", "preset", "max_range", "odometry", "drive_inset")
    out = {k: getattr(args, k) for k in keys}
    if args.env == "room":
        out["world_sha12"] = sha12(args.world)
    return out


def ledger_line(path, run_id, seed, driver, cfg, summary):
    """Plan C13: one line per paid episode, only if the project ledger already exists."""
    if not path.exists() or not summary["cost_usd"]:
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "phase": "m2", "run_id": run_id,
                             "episode_id": "seed_%d" % seed, "model_key": driver.key, "provider": cfg["provider"],
                             "tokens_in": summary["tokens"]["in"], "tokens_out": summary["tokens"]["out"],
                             "tokens_cached": summary["tokens"]["cached_in"], "cost_usd": round(summary["cost_usd"], 5),
                             "label": "closed loop"}) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--driver", required=True, help="b2, or a model key of configs/providers.json / providers_demo.json")
    ap.add_argument("--env", choices=("square", "room"), default="square")
    ap.add_argument("--world", default=None, help="room: world file (bm.world/1 with a polygon arena)")
    ap.add_argument("--start", default=None, help="room: start pose x,y,theta_deg in the world file's frame")
    ap.add_argument("--preset", default="camera", help="room: noise preset of envs/kinsim_room.py")
    ap.add_argument("--max-range", type=float, default=2.0, help="room: detection range limit (m)")
    ap.add_argument("--odometry", default="study", help="room: study or carpet")
    ap.add_argument("--drive-inset", type=float, default=0.0, help="room: driving area moved in from every wall (m)")
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-steps", type=int, default=cl.STEPS_BUDGET)
    ap.add_argument("--cap-usd", type=float, required=True, help="hard spend cap of this run folder; 0 only for b2")
    ap.add_argument("--resume-reason", default=None, help="required to resume an existing run; recorded")
    ap.add_argument("--watch-latch", action="append", default=[], metavar="FILE",
                    help="another latch file to obey (repeatable), e.g. the project-wide data/LATCH: the run does not "
                         "start while it exists, and an episode latches when it appears")
    ap.add_argument("--prompt", default=str(ROOT / "prompts" / "robot_system_prompt_v3.3.txt"))
    ap.add_argument("--dv", default=None, help="design-values file (default: the frozen configs/dv.json), e.g. "
                                               "configs/dv-real.json from tools/real_dv.py")
    args = ap.parse_args()
    dv_path = dv_real.resolve_arg(args.dv)
    if dv_path is not None:
        problems = dv_real.check_file(dv_path)
        if problems:
            sys.exit("--dv: " + "; ".join(problems))
    with dv_real.use_dv(dv_path) as dv_rec:     # the frozen modules read these values; restored on the way out
        run(args, dv_rec)


def run(args, dv_rec):
    if not 1 <= args.max_steps <= cl.STEPS_BUDGET:
        sys.exit("--max-steps must be 1..%d (the EXPLORE step budget)" % cl.STEPS_BUDGET)

    driver, cfg, cfg_path, sdk = build_driver(args.driver, room=args.env == "room")
    paid = cfg is not None
    if paid and args.cap_usd <= 0:
        sys.exit("an API driver needs a positive --cap-usd")
    dv = dvmod.load_dv()
    seeds = seed_list(args.seeds)
    invariant = {"driver": args.driver, "provider_entry": cfg, "agent": driver.header(), "arm": driver.arm,
                 "max_steps": args.max_steps, "env": env_args(args), "max_idle_steps": cl.MAX_IDLE_STEPS,
                 "autolatch_contacts": int(dv["autolatch_contacts"]),
                 "sha12": {"prompt": sha12(args.prompt), "dv.json": sha12(ROOT / "configs" / "dv.json"),
                           "providers_file": sha12(cfg_path) if cfg_path else None, **{f: sha12(SRC / f) for f in HASHED}}}
    if not dv_rec["frozen"]:
        invariant["dv_file"] = dv_rec      # (only then: a run on the frozen file keeps its configuration tag)
    config = hashlib.sha256(json.dumps(invariant, sort_keys=True).encode()).hexdigest()[:12]

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    lock = open(out_dir / ".lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        sys.exit("another run is already writing %s" % out_dir)
    resumes = sorted(out_dir.glob("run.resume-*.json"))
    if (out_dir / "run.json").exists():
        if not args.resume_reason:
            sys.exit("%s already has a run (%d resumes so far): give --resume-reason to resume it" % (out_dir, len(resumes)))
        first = json.loads((out_dir / "run.json").read_text())
        if first.get("config") != config:
            diff = [k for k in invariant if first.get(k) != invariant[k]]
            sys.exit("refusing to resume %s under another configuration (run.json %s, now %s; differs in %s)"
                     % (out_dir, first.get("config"), config, diff))
    system_text = pathlib.Path(args.prompt).read_text(encoding="utf-8")
    spend_path = out_dir / "spend.jsonl"
    budget = rp.Budget(args.cap_usd if args.cap_usd > 0 else float("inf"), rp.spent_in(spend_path), path=spend_path)
    run_id = out_dir.name
    header = dict(invariant, config=config, run_id=run_id, prompt_file=pathlib.Path(args.prompt).name,
                  provider_file=cfg_path.name if cfg_path else None, seeds=seeds, cap_usd=args.cap_usd,
                  world_file=args.world, dv_file=dv_rec,
                  git_commit=os.environ.get("BM_GIT_COMMIT"), git_dirty=os.environ.get("BM_GIT_DIRTY"),
                  host=os.environ.get("BM_HOST"), python=sys.version.split()[0], **sdk,
                  resume_reason=args.resume_reason, earlier_resumes=len(resumes),
                  started=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    name = "run.json" if not (out_dir / "run.json").exists() else "run.resume-%s.json" % time.strftime("%Y%m%dT%H%M%S")
    (out_dir / name).write_text(json.dumps(header, indent=1))
    log("start %s, env %s, config %s, seeds %s, max %d steps, spent so far $%.2f, cap %s" % (
        driver.arm, args.env, config, seeds, args.max_steps, budget.spent,
        "none" if budget.cap == float("inf") else "$%.2f" % budget.cap))

    failed, capped, latched, results = [], [], [], {}
    for seed in seeds:
        env = build_env(args)
        path = out_dir / ("seed_%d.jsonl" % seed)
        try:
            res = cl.run_episode(driver, system_text, env, seed, path, budget, args.max_steps, log, config=config,
                                 autolatch_contacts=int(dv["autolatch_contacts"]), watch_latch_paths=args.watch_latch)
        except KeyboardInterrupt:
            log("interrupted during seed %d; the unfinished step is not written" % seed)
            failed.append(seed)
            break
        except Exception as exc:  # report and stop: a rerun resumes at the unwritten step
            failed.append(seed)
            log("seed %d failed: %s: %s" % (seed, type(exc).__name__, str(exc)[:400]))
            continue
        results[str(seed)] = res
        rows = rp.load_done(path, log)
        if rows:
            (out_dir / ("seed_%d.world.json" % seed)).write_text(json.dumps(env.describe(), default=list))
            summary = mc.summarize(rows, env.describe()["world"])
            summary["complete"] = res["complete"]
            (out_dir / ("seed_%d.summary.json" % seed)).write_text(json.dumps(summary, indent=1))
            with open(out_dir / ("seed_%d.runlog.jsonl" % seed), "w", encoding="utf-8") as fh:
                for line in cl.to_runlog(rows, run_id, "seed_%d" % seed):
                    fh.write(json.dumps(line) + "\n")
            if res["complete"] and paid:
                ledger_line(ROOT / "data" / "budget" / "ledger.jsonl", run_id, seed, driver, cfg, summary)
            print(mc.table([summary]), flush=True)
        if not res["complete"]:
            capped.append(seed)
        if res["ended_by"] == "latch":
            # a latch stops the batch, not only the episode: only an operator clears it (D5, D6)
            latched.append(seed)
            log("seed %d latched (%s): the remaining seeds are not run" % (seed, res["detail"]))
            break
        log("seed %d: %s" % (seed, "ended by %s (%s) after %d steps" % (res["ended_by"], res["detail"], res["steps"])
                             if res["complete"] else "stopped at the spend cap before step %d" % res["steps"]))
    end = {"ended": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "spent_usd": budget.spent, "failed": failed, "capped": capped,
           "latched": latched, "results": results, "config": config}
    (out_dir / ("run.end-%s.json" % time.strftime("%Y%m%dT%H%M%S"))).write_text(json.dumps(end, indent=1))
    log("done: total spent $%.2f; failed seeds: %s; stopped at the cap: %s" % (budget.spent, failed or "none", capped or "none"))
    sys.exit(1 if failed else 3 if latched else 2 if capped else 0)


if __name__ == "__main__":
    main()
