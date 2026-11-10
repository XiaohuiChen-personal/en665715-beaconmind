#!/usr/bin/env python3
"""Replay recorded episodes through one L2 arm (any provider in configs/providers.json).

Run inside beaconmind-ros on the Spark, through tools/replay_run.sh (it mounts the repository and the
secrets env_file, and passes the git commit):
  bash course-project/tools/replay_run.sh --provider qwen38-flash-xhigh \
      --obslogs course-project/data/<study>/obslogs/drift2 --out course-project/data/<study>/runs/drift2/qwen38-flash-xhigh \
      --seeds 2000-2019 --max-steps 150 --cap-usd 0 --workers 4

- Providers: "anthropic_messages" (Claude Opus 5.5, ANTHROPIC_API_KEY from the environment, never printed),
  "vllm" and "ollama" (OpenAI-compatible /v1 on the Spark's loopback). Local arms cost 0, so --cap-usd 0
  means no cap for them; an API arm needs a positive cap.
- Resumable: re-running continues each seed after its last logged step, but only under the same configuration:
  the provider entry, the agent settings, the repeat index, the step limit, and the hashes of the prompt, the
  design values, the providers file, every harness source file and every observation log must equal run.json's
  (their hash is the `config` tag written into every row). A lock file stops two runs from writing the same folder.
- Spend is appended to <out>/spend.jsonl as it happens, so a resume counts the cost of steps that crashed.
- Exit code 0 when every seed is complete, 2 when the spend cap stopped one, 1 when a seed failed (rerun to resume
  it), 130 on Ctrl-C (running steps finish, queued seeds are cancelled).
- Seeds run --workers at a time, in an order shuffled with --order-seed (recorded in run.json).
- run.json records the provider entry, the request settings, SHA-256 prefixes of the prompt, the design
  values, the providers file and every harness source file, the SDK versions, the server's model list
  (local arms) and the git commit; a resumed run writes run.resume-<time>.json instead.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote this runner (generalised from
tools/pilot_replay.py of the 2026-10-29 pilot).
"""
import argparse
import concurrent.futures as cf
import fcntl
import hashlib
import json
import os
import pathlib
import random
import sys
import threading
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "beaconmind" / "src"))
from beaconmind.harness import replay as rp  # noqa: E402

PRINT = threading.Lock()
SRC = ROOT / "beaconmind" / "src" / "beaconmind"
HASHED = ("geometry.py", "dv.py", "envs/kinsim_lite.py", "harness/tools_d5.py", "harness/replay.py",
          "harness/providers/anthropic_messages.py", "harness/providers/openai_chat.py")


def log(msg):
    with PRINT:
        print(time.strftime("%H:%M:%S"), msg, flush=True)


def seed_list(text):
    out = []
    for part in text.split(","):
        a, _, b = part.partition("-")
        for s in (range(int(a), int(b) + 1) if b else [int(a)]):
            if s not in out:
                out.append(s)
    return out


def sha12(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:12]


def get_json(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.load(r)
    except Exception as exc:  # recorded as it is
        return {"error": "%s: %s" % (type(exc).__name__, exc)}


def server_identity(cfg):
    """What the container can see of the model server; tools/replay_run.sh adds the host-side facts."""
    root = cfg["base_url"].rstrip("/").rsplit("/v1", 1)[0]
    if cfg["provider"] == "vllm":
        return {"version": get_json(root + "/version")}
    if cfg["provider"] == "ollama":
        tags = get_json(root + "/api/tags")
        digest = next((m.get("digest") for m in tags.get("models", []) if m.get("name") == cfg["model"]), None) \
            if isinstance(tags, dict) else None
        return {"version": get_json(root + "/api/version"), "model_digest": digest}
    return {}


def served_models(base_url):
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/models", timeout=10) as r:
            return [m.get("id") for m in json.load(r).get("data", [])]
    except Exception as exc:  # recorded, and checked below
        return {"error": "%s: %s" % (type(exc).__name__, exc)}


def build_agent(key, cfg, repeat):
    if cfg["provider"] == "anthropic_messages":
        import anthropic
        from beaconmind.harness.providers import anthropic_messages as am
        api_key = os.environ.get(cfg["api_key_env"] or "ANTHROPIC_API_KEY")
        if not api_key:
            sys.exit("%s is not set" % (cfg["api_key_env"] or "ANTHROPIC_API_KEY"))
        if cfg["model"] != am.SETTINGS["model"]:
            sys.exit("the Anthropic provider is written for %s, not %s" % (am.SETTINGS["model"], cfg["model"]))
        opt = cfg.get("options") or {}
        if opt.get("max_tokens", am.SETTINGS["max_tokens"]) != am.SETTINGS["max_tokens"] or \
                opt.get("effort", am.SETTINGS["output_config"]["effort"]) != am.SETTINGS["output_config"]["effort"]:
            sys.exit("configs/providers.json's Opus options differ from the provider's fixed SETTINGS %s" % am.SETTINGS)
        client = anthropic.Anthropic(api_key=api_key, timeout=cfg.get("request_timeout_s") or 900, max_retries=0)
        return am.AnthropicAgent(client, key), {"anthropic_sdk": anthropic.__version__}
    if cfg["provider"] in ("vllm", "ollama"):
        import openai
        from beaconmind.harness.providers import openai_chat as oc
        models = served_models(cfg["base_url"])
        if not isinstance(models, list) or cfg["model"] not in models:
            sys.exit("%s does not serve %s: %s" % (cfg["base_url"], cfg["model"], models))
        client = openai.OpenAI(base_url=cfg["base_url"], api_key="none", timeout=cfg.get("request_timeout_s") or 1800,
                               max_retries=0)
        return oc.OpenAIChatAgent(client, key, cfg, repeat=repeat), {"openai_sdk": openai.__version__,
                                                                     "served_models": models}
    sys.exit("provider %s is not supported by this runner" % cfg["provider"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--provider", required=True, help="key in configs/providers.json")
    ap.add_argument("--obslogs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--max-steps", type=int, default=150)
    ap.add_argument("--cap-usd", type=float, required=True, help="spend cap for API arms; 0 = no cap (local arms only)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--repeat", type=int, default=0, help="repeat index k (changes the local sampling seeds)")
    ap.add_argument("--order-seed", type=int, default=20261110)
    ap.add_argument("--providers", default=str(ROOT / "configs" / "providers.json"))
    ap.add_argument("--prompt", default=str(ROOT / "prompts" / "robot_system_prompt_v3.3.txt"))
    args = ap.parse_args()

    cfgs = json.loads(pathlib.Path(args.providers).read_text(encoding="utf-8"))["models"]
    if args.provider not in cfgs:
        sys.exit("unknown provider key %s (have: %s)" % (args.provider, ", ".join(cfgs)))
    cfg = cfgs[args.provider]
    is_local = cfg["provider"] in ("vllm", "ollama")
    if args.cap_usd <= 0 and not is_local:
        sys.exit("an API arm needs a positive --cap-usd")
    agent, sdk = build_agent(args.provider, cfg, args.repeat)

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    lock = open(out_dir / ".lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        sys.exit("another replay_run.py is already writing %s" % out_dir)
    system_text = pathlib.Path(args.prompt).read_text(encoding="utf-8")
    seeds = seed_list(args.seeds)
    missing = [s for s in seeds if not (pathlib.Path(args.obslogs) / ("seed_%d.json" % s)).exists()]
    if missing:
        sys.exit("no observation log for seeds %s in %s" % (missing, args.obslogs))
    order = list(seeds)
    random.Random(args.order_seed).shuffle(order)

    invariant = {"provider_key": args.provider, "provider_entry": cfg, "agent": agent.header(), "arm": agent.arm,
                 "repeat": args.repeat, "max_steps": args.max_steps,
                 "sha12": {"prompt": sha12(args.prompt), "dv.json": sha12(ROOT / "configs" / "dv.json"),
                           "providers.json": sha12(args.providers), **{f: sha12(SRC / f) for f in HASHED}}}
    obslog_sha = {str(s): sha12(pathlib.Path(args.obslogs) / ("seed_%d.json" % s)) for s in seeds}
    config = hashlib.sha256(json.dumps(invariant, sort_keys=True).encode()).hexdigest()[:12]
    if (out_dir / "run.json").exists():
        first = json.loads((out_dir / "run.json").read_text())
        if first.get("config") != config:
            diff = [k for k in invariant if first.get(k) != invariant[k]]
            sys.exit("refusing to resume %s under another configuration (run.json config %s, now %s; differs in %s)"
                     % (out_dir, first.get("config"), config, diff or "an older run.json without a config tag"))
        old_logs = first.get("obslog_sha12", {})
        changed = [s for s in obslog_sha if s in old_logs and old_logs[s] != obslog_sha[s]]
        if changed:
            sys.exit("observation logs changed since run.json for seeds %s" % changed)
    spend_path = out_dir / "spend.jsonl"
    budget = rp.Budget(args.cap_usd if args.cap_usd > 0 else float("inf"), rp.spent_in(spend_path), path=spend_path)

    header = dict(invariant, config=config, prompt_file=pathlib.Path(args.prompt).name, obslogs=str(args.obslogs),
                  seeds=seeds, order=order, order_seed=args.order_seed, cap_usd=args.cap_usd, workers=args.workers,
                  git_commit=os.environ.get("BM_GIT_COMMIT"), git_dirty=os.environ.get("BM_GIT_DIRTY"),
                  server=dict(server_identity(cfg), host_side=json.loads(os.environ.get("BM_SERVER_INFO") or "{}"))
                  if cfg["provider"] in ("vllm", "ollama") else None,
                  host=os.environ.get("BM_HOST"), python=sys.version.split()[0], **sdk,
                  started=time.strftime("%Y-%m-%dT%H:%M:%S%z"), obslog_sha12=obslog_sha)
    name = "run.json" if not (out_dir / "run.json").exists() else "run.resume-%s.json" % time.strftime("%Y%m%dT%H%M%S")
    (out_dir / name).write_text(json.dumps(header, indent=1))
    log("start %s (%s %s), config %s, %d seeds, %d workers, spent so far $%.2f, cap %s" % (
        args.provider, cfg["provider"], cfg["model"], config, len(seeds), args.workers, budget.spent,
        "none" if budget.cap == float("inf") else "$%.2f" % budget.cap))

    def one(seed):
        doc = json.loads((pathlib.Path(args.obslogs) / ("seed_%d.json" % seed)).read_text(encoding="utf-8"))
        return seed, rp.replay_seed(agent, system_text, doc, out_dir / ("seed_%d.jsonl" % seed), budget,
                                    args.max_steps, log, config=config)

    failed, capped, interrupted = [], [], False
    pool = cf.ThreadPoolExecutor(max_workers=max(1, args.workers))
    futs = {pool.submit(one, s): s for s in order}
    try:
        for fut in cf.as_completed(futs):
            try:
                seed, ok = fut.result()
                if not ok:
                    capped.append(seed)
                log("seed %d finished: %s" % (seed, "complete" if ok else "stopped at the cap"))
            except Exception as exc:  # report and keep the other seeds running; a rerun resumes it
                failed.append(futs[fut])
                log("seed %d failed: %s: %s" % (futs[fut], type(exc).__name__, str(exc)[:300]))
    except KeyboardInterrupt:
        interrupted = True
        log("interrupted: queued seeds cancelled; steps already running will finish")
        pool.shutdown(wait=True, cancel_futures=True)
    else:
        pool.shutdown(wait=True)
    end = {"ended": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "spent_usd": budget.spent, "failed": failed,
           "capped": capped, "interrupted": interrupted, "config": config}
    (out_dir / ("run.end-%s.json" % time.strftime("%Y%m%dT%H%M%S"))).write_text(json.dumps(end, indent=1))
    log("done: total spent $%.2f; failed seeds: %s; stopped at the cap: %s" % (budget.spent, failed or "none",
                                                                              capped or "none"))
    sys.exit(130 if interrupted else 1 if failed else 2 if capped else 0)


if __name__ == "__main__":
    main()
