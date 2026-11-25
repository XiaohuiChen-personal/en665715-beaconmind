#!/usr/bin/env python3
"""Replay the real car's B2 episodes through the model arms (plan section 3.6 work list 3.6; M3.T19, M4.T13).

    python3 course-project/tools/real_replay.py convert --batch course-project/data/batches/<label> \\
        --out course-project/data/real-replay/<label>/obslogs
    bash course-project/tools/real_replay.sh run --provider <key> --obslogs <dir> --out <dir> --cap-usd <X> \\
        [--dv course-project/configs/dv-real.json] [--prompt course-project/prompts/robot_system_prompt_v3.3-room.txt]
    python3 course-project/tools/real_replay.py run --provider procedure ...      # free stand-in, no container needed
    python3 course-project/tools/real_replay.py analyze --obslogs <dir> --run <arm>=<run dir> ... --out <file stem>
        (give one arm label twice for its sibling run folders, e.g. runs/<arm> and runs/<arm>+b2-real-03)
        [--compare <rehearsal analysis.json>]

convert   one observation log per finished episode (beaconmind/real_replay.py: truth from truth.jsonl, B2's own
          estimate kept as the reference, the real observation's status fields kept) and index.json.
run       the frozen replay loop (harness/replay.py replay_seed) with what the real runs need and the frozen runner
          (tools/replay_run.py, frozen by the pre-registration, so not edited) does not have: --dv (the real-run design
          values, through beaconmind.dv_real.use_dv; default configs/dv-real.json), the real-room prompt variant by
          default, the real observations' status fields in the step message (real_replay.real_observations), a check
          that the prompt's range limit equals the design values' reject_range_above_m, and provider `procedure` (the
          coded procedure as a free stand-in model). Everything else is the frozen runner's own code, imported from
          it: provider construction and checks, the configuration tag, resume rules, the spend cap and its ledger,
          workers, exit codes. run.json records the dv file and its sha12, the overlay and the config tag (which
          therefore differs from the study's).
analyze   final-position error per episode and arm, B0 and B2 as reference rows, median and spread. The primary truth
          is the end circle (the batch manifest's end_fix.pose, for episodes that ended by DONE; --batches); the
          batch's tracked truth at the last step and the same recomputed by tools/recompute_truth.py with a slip-aware
          tracker (--slip-sigma, default 0.3; --no-recompute) are secondary, tracker-dependent columns. --compare
          gives the gap to another set (the simulated rehearsal), against the end circle.
estimate  cost and time of each study arm on a converted set, from the study's measured rates.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this tool; made the end circle the primary truth. Derived from: tools/replay_run.py main()
(the same steps, reused by import where it could be; the loop body is the frozen one).
"""
import argparse
import concurrent.futures as cf
import fcntl
import hashlib
import importlib.util
import json
import os
import pathlib
import random
import re
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "beaconmind" / "src"))
from beaconmind import dv_real  # noqa: E402
from beaconmind import real_replay as rr  # noqa: E402
from beaconmind.harness import replay as rp  # noqa: E402

DEFAULT_PROMPT = ROOT / "prompts" / "robot_system_prompt_v3.3-room.txt"
DEFAULT_DV = ROOT / "configs" / "dv-real.json"


def frozen_runner():
    """tools/replay_run.py as a module (its main() is not run)."""
    spec = importlib.util.spec_from_file_location("replay_run_frozen", ROOT / "tools" / "replay_run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def prompt_range_limit(text):
    m = re.search(r"rejected if quality < [0-9.]+, range_m > ([0-9.]+)", text)
    return float(m.group(1)) if m else None


# ---------------------------------------------------------------- convert

def cmd_convert(a):
    if len(a.batch) == 1 and not a.set:
        idx = rr.convert_batch(a.batch[0], a.out, a.world)
    else:
        idx = rr.convert_batches(a.batch, a.out, a.world)
    print("converted %d episodes, %d steps, into %s" % (len(idx["episodes"]), idx["steps"], a.out))
    for e in idx["episodes"]:
        print("  seed %-5d %-12s %-8s %-3s %4d steps  ended %-8s  last truth sigma %.3f m (%s)" % (
            e["seed"], e.get("batch", ""), e["episode"], e["scenario"], e["steps"], e["ended_by"],
            e["truth_sigma_xy_m_last"] or -1,
            "tag fix" if e["truth_is_a_fix_last"] else "tracked since the last fix"))
        if e.get("note"):
            print("           %s; end pose from %s" % (e["note"], e.get("end_pose_source")))
    for x in idx["excluded"]:
        print("  excluded %s %s: %s" % (x.get("batch", ""), x["episode"], x["reason"]))
    return 0


# ---------------------------------------------------------------- run

def cmd_run(a, agent=None, sdk=None):
    """`agent` (tests only): a provider object to use instead of building one for a.provider."""
    fr = frozen_runner()
    dv_path = dv_real.resolve_arg(a.dv)
    if dv_path is not None:
        problems = dv_real.check_file(dv_path)
        if problems:
            sys.exit("--dv: " + "; ".join(problems))
    dvrec = dv_real.record(dv_path)
    system_text = pathlib.Path(a.prompt).read_text(encoding="utf-8")
    limit = prompt_range_limit(system_text)
    import beaconmind.dv as dvm
    reject = (dvm.load_dv(dv_path) if dv_path else dvm.load_dv())["reject_range_above_m"]
    if limit is None or abs(limit - float(reject)) > 1e-9:
        sys.exit("the prompt's range limit (%s m) differs from the design values' reject_range_above_m (%s m)"
                 % (limit, reject))

    if a.provider == "procedure":
        agent, sdk, cfg = rr.ProcedureAgent(), {}, {"provider": "coded_procedure", "model": None}
        inv = {"provider_key": "procedure", "provider_entry": cfg, "agent": agent.header(), "arm": agent.arm,
               "repeat": a.repeat, "max_steps": a.max_steps,
               "sha12": {"prompt": fr.sha12(a.prompt), **{f: fr.sha12(fr.SRC / f) for f in fr.HASHED}}}
    else:
        cfgs = json.loads(pathlib.Path(a.providers).read_text(encoding="utf-8"))["models"]
        if a.provider not in cfgs:
            sys.exit("unknown provider key %s (have: %s)" % (a.provider, ", ".join(cfgs)))
        cfg = cfgs[a.provider]
        if a.cap_usd <= 0 and cfg["provider"] not in ("vllm", "ollama"):
            sys.exit("an API arm needs a positive --cap-usd")
        if agent is None:
            agent, sdk = fr.build_agent(a.provider, cfg, a.repeat)
        inv, _ = fr.config_invariant(a.provider, a.providers, a.prompt, a.repeat, a.max_steps)
    sdk = sdk or {}
    inv = dict(inv, dv=dvrec, observation_overlay=list(rr.OVERLAY_FIELDS), obslog_schema=rr.SCHEMA,
               runner="tools/real_replay.py", runner_sha12=fr.sha12(__file__),
               real_replay_sha12=fr.sha12(ROOT / "beaconmind" / "src" / "beaconmind" / "real_replay.py"))
    config = hashlib.sha256(json.dumps(inv, sort_keys=True).encode()).hexdigest()[:12]

    obslogs = pathlib.Path(a.obslogs)
    index = json.loads((obslogs / "index.json").read_text(encoding="utf-8"))
    seeds = fr.seed_list(a.seeds) if a.seeds else [e["seed"] for e in index["episodes"]]
    missing = [s for s in seeds if not (obslogs / ("seed_%d.json" % s)).exists()]
    if missing:
        sys.exit("no observation log for seeds %s in %s" % (missing, obslogs))
    docs = {s: json.loads((obslogs / ("seed_%d.json" % s)).read_text(encoding="utf-8")) for s in seeds}
    if any(d.get("schema") != rr.SCHEMA for d in docs.values()):
        sys.exit("%s does not hold real-replay observation logs (convert the batch first)" % obslogs)
    order = list(seeds)
    random.Random(a.order_seed).shuffle(order)

    out_dir = pathlib.Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    lock = open(out_dir / ".lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        sys.exit("another replay is already writing %s" % out_dir)
    obslog_sha = {str(s): fr.sha12(obslogs / ("seed_%d.json" % s)) for s in seeds}
    resumes = sorted(out_dir.glob("run.resume-*.json"))
    if (out_dir / "run.json").exists() and not a.resume_reason:
        sys.exit("%s already has a run (%d resumes so far): give --resume-reason to resume it" % (out_dir, len(resumes)))
    if (out_dir / "run.json").exists():
        first = json.loads((out_dir / "run.json").read_text())
        if first.get("config") != config:
            diff = [k for k in inv if first.get(k) != inv[k]]
            sys.exit("refusing to resume %s under another configuration (run.json %s, now %s; differs in %s)"
                     % (out_dir, first.get("config"), config, diff))
        old = first.get("obslog_sha12", {})
        changed = [s for s in obslog_sha if s in old and old[s] != obslog_sha[s]]
        if changed:
            sys.exit("observation logs changed since run.json for seeds %s" % changed)
    spend_path = out_dir / "spend.jsonl"
    budget = rp.Budget(a.cap_usd if a.cap_usd > 0 else float("inf"), rp.spent_in(spend_path), path=spend_path)
    is_local = cfg.get("provider") in ("vllm", "ollama")
    header = dict(inv, config=config, prompt_file=pathlib.Path(a.prompt).name, obslogs=str(obslogs),
                  batch=index.get("batch"), batch_config=index.get("batch_config"), real_car=index.get("real_car"),
                  seeds=seeds, order=order, order_seed=a.order_seed, cap_usd=a.cap_usd, workers=a.workers,
                  git_commit=os.environ.get("BM_GIT_COMMIT"), git_dirty=os.environ.get("BM_GIT_DIRTY"),
                  server=dict(fr.server_identity(cfg), host_side=json.loads(os.environ.get("BM_SERVER_INFO") or "{}"))
                  if is_local else None, host=os.environ.get("BM_HOST"), python=sys.version.split()[0], **sdk,
                  resume_reason=a.resume_reason, earlier_resumes=len(resumes),
                  started=time.strftime("%Y-%m-%dT%H:%M:%S%z"), obslog_sha12=obslog_sha)
    name = "run.json" if not (out_dir / "run.json").exists() else "run.resume-%s.json" % time.strftime("%Y%m%dT%H%M%S")
    (out_dir / name).write_text(json.dumps(header, indent=1))
    fr.log("start %s (%s), config %s, %d seeds, %d workers, dv %s sha12 %s, prompt %s, spent so far $%.2f, cap %s" % (
        a.provider, cfg.get("model"), config, len(seeds), a.workers, dvrec["file"], dvrec["sha12"],
        pathlib.Path(a.prompt).name, budget.spent, "none" if budget.cap == float("inf") else "$%.2f" % budget.cap))

    failed, capped, interrupted = [], [], False
    with dv_real.use_dv(dv_path), rr.real_observations(list(docs.values())):
        def one(seed):
            return seed, rp.replay_seed(agent, system_text, docs[seed], out_dir / ("seed_%d.jsonl" % seed), budget,
                                        a.max_steps, fr.log, config=config)
        pool = cf.ThreadPoolExecutor(max_workers=max(1, a.workers))
        futs = {pool.submit(one, s): s for s in order}
        try:
            for fut in cf.as_completed(futs):
                try:
                    seed, ok = fut.result()
                    if not ok:
                        capped.append(seed)
                    fr.log("seed %d finished: %s" % (seed, "complete" if ok else "stopped at the cap"))
                except Exception as exc:  # report and keep the others running; a rerun resumes it
                    failed.append(futs[fut])
                    fr.log("seed %d failed: %s: %s" % (futs[fut], type(exc).__name__, str(exc)[:300]))
        except KeyboardInterrupt:
            interrupted = True
            fr.log("interrupted: queued seeds cancelled; steps already running will finish")
            pool.shutdown(wait=True, cancel_futures=True)
        else:
            pool.shutdown(wait=True)
    end = {"ended": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "spent_usd": budget.spent, "failed": failed,
           "capped": capped, "interrupted": interrupted, "config": config}
    (out_dir / ("run.end-%s.json" % time.strftime("%Y%m%dT%H%M%S"))).write_text(json.dumps(end, indent=1))
    fr.log("done: total spent $%.2f; failed seeds: %s; stopped at the cap: %s" % (budget.spent, failed or "none",
                                                                                 capped or "none"))
    return 130 if interrupted else 1 if failed else 2 if capped else 0


# ---------------------------------------------------------------- analyze

def cmd_analyze(a):
    index, docs = rr.load_obslogs(a.obslogs)
    runs = {}
    for spec in a.run or []:
        label, _, folder = spec.partition("=")
        if not folder:
            sys.exit("--run takes <arm label>=<run folder>")
        runs.setdefault(label, []).append(folder)       # a label given twice: one arm's sibling folders
    try:
        parts = {label: rr.check_parts(folders) for label, folders in runs.items()}
    except (ValueError, OSError) as exc:
        sys.exit("run folders: %s" % exc)
    runs = {label: folders[0] if len(folders) == 1 else folders for label, folders in runs.items()}
    settings = {"primary": "end circle (manifest end_fix.pose, episodes that ended by DONE)",
                "batches_root": a.batches, "recomputed": a.slip_sigma is not None}
    if a.slip_sigma is not None:
        settings.update(recompute_tool=rr.RECOMPUTE_TOOL, slip_sigma=a.slip_sigma, slip_north=a.slip_north,
                        recompute_command="python3 course-project/%s BATCH_DIR --slip-sigma %g --slip-north %g" % (
                            rr.RECOMPUTE_TOOL, a.slip_sigma, a.slip_north))
    recompute = recompute_with_tool(a.slip_sigma, a.slip_north) if a.slip_sigma is not None else None
    truths = rr.independent_truths(docs, a.batches, recompute)
    errors = rr.final_errors(docs, runs, truths)
    summary = rr.summarize(errors)
    order = ["B0", "B2"] + list(runs)
    stats = rr.run_stats(docs, runs)
    md = rr.result_markdown(a.title or "Real-log replay: final-position error per arm", index, errors, summary, order,
                            stats, truths, settings)
    if a.compare:
        other = json.loads(pathlib.Path(a.compare).read_text(encoding="utf-8"))
        md += "\nGap to `%s` (%s): median final-position error here minus there, cm.\n\n" % (
            other["index"]["batch"], a.compare)
        md += "| Arm | here | there | gap |\n| --- | --- | --- | --- |\n"
        if any("end_circle" not in v for v in other["summary"].values()):
            sys.exit("%s was analysed before the end circle became the primary truth: analyse it again" % a.compare)
        md = md.replace("Gap to `", "Gap (against the end circle) to `", 1)
        for arm in order:
            h = summary.get(arm, {}).get("end_circle", {}).get("median_m")
            t = other["summary"].get(arm, {}).get("end_circle", {}).get("median_m")
            md += "| %s | %s | %s | %s |\n" % (arm, rr._cm(h), rr._cm(t), rr._cm(h - t) if h is not None and t is not None else "")
    several = {label: p for label, p in parts.items() if len(p) > 1}
    if several:
        md += "\nArms run in several folders (they differ only in the hashes of the replay code, %s):\n\n" % (
            ", ".join(rr.CODE_SHAS))
        for label, p in several.items():
            md += "- %s: %s\n" % (label, "; ".join("`%s` seeds %s, config %s" % (
                x["folder"], ", ".join(map(str, x["seeds"])), x["config"]) for x in p))
    doc = {"schema": "bm.real_replay_result/2", "index": index, "runs": runs, "run_parts": parts,
           "truth_settings": settings, "truths": {str(k): v for k, v in truths.items()}, "summary": summary,
           "run_stats": stats,
           "errors": {arm: {str(k): v for k, v in by.items()} for arm, by in errors.items()},
           "created": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    pathlib.Path(a.out + ".json").write_text(json.dumps(doc, indent=1))
    pathlib.Path(a.out + ".md").write_text(md)
    sys.stdout.write(md)
    return 0


def recompute_with_tool(slip_sigma, slip_north):
    """recompute(batch_dir, entry, n_rows) for rr.independent_truths: tools/recompute_truth.py's own replay_episode
    (the batch's per-step code over the logged rows, with a slip-aware tracker), set up as its main() does; the
    recomputed and the logged truth at row n_rows - 1, in the episode's map frame."""
    spec = importlib.util.spec_from_file_location("recompute_truth", ROOT / rr.RECOMPUTE_TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from beaconmind.car import batch as B
    setup = {}

    def one(batch_dir, entry, n_rows):
        if batch_dir not in setup:
            man = json.loads((pathlib.Path(batch_dir) / "manifest.json").read_text(encoding="utf-8"))
            fields = set(B.BatchParams.__dataclass_fields__)
            params = B.BatchParams(**{k: v for k, v in man["params"].items() if k in fields})
            wp = man["params"]["world_path"]
            world = json.loads((pathlib.Path(wp) if os.path.isabs(wp) else ROOT / wp).read_text(encoding="utf-8"))
            setup[batch_dir] = params, world
        params, world = setup[batch_dir]
        rows, halts = mod.replay_episode(batch_dir, entry, params, world, slip_sigma, slip_north)
        start = entry["start_pose_world"]
        _, _, new, logged = rows[n_rows - 1]
        return {"pose": rr.to_map_pose(start, new["pose"]), "sigma_xy_m": new["sigma_xy_m"],
                "logged_pose": logged["truth_map"], "replay_halts": [h[0] for h in halts]}
    return one


def cmd_estimate(a):
    index = json.loads((pathlib.Path(a.obslogs) / "index.json").read_text(encoding="utf-8"))
    est = rr.estimate(index)
    print("%s: %d episodes, %d steps (longest %d)" % (index["batch"], len(index["episodes"]), index["steps"],
                                                      max(e["steps"] for e in index["episodes"])))
    for arm, e in est.items():
        print("  %-20s cost US$%7.2f   time %.1f h at the study's throughput, %.1f h for the longest episode alone at "
              "the study's latency" % (arm, e["usd"], e["hours_throughput"], e["hours_longest_episode"]))
    return 0


def parser():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("convert")
    c.add_argument("--batch", required=True, action="append", help="batch folder; repeat it for a set of batches")
    c.add_argument("--set", action="store_true", help="write a set (index of several batches, seed bases 1000, "
                                                      "2000, ...) even for one batch; a rerun adds to it")
    c.add_argument("--out", required=True)
    c.add_argument("--world", default=None, help="world file (default: the batch manifest's)")
    r = sub.add_parser("run")
    r.add_argument("--provider", required=True, help="key in configs/providers.json, or `procedure`")
    r.add_argument("--obslogs", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--seeds", default=None, help="default: every episode in index.json")
    r.add_argument("--max-steps", type=int, default=150)
    r.add_argument("--cap-usd", type=float, required=True)
    r.add_argument("--workers", type=int, default=4)
    r.add_argument("--repeat", type=int, default=0)
    r.add_argument("--order-seed", type=int, default=20261125)
    r.add_argument("--resume-reason", default=None)
    r.add_argument("--providers", default=str(ROOT / "configs" / "providers.json"))
    r.add_argument("--prompt", default=str(DEFAULT_PROMPT))
    r.add_argument("--dv", default=str(DEFAULT_DV), help="design values (default configs/dv-real.json; 'frozen' for "
                                                         "the frozen configs/dv.json)")
    n = sub.add_parser("analyze")
    n.add_argument("--batches", default=str(ROOT / "data" / "batches"),
                   help="folder of the batch folders (their manifests give the end circles)")
    n.add_argument("--slip-sigma", type=float, default=0.3,
                   help="recompute the last-step truth with %s at this slip sigma (per metre of forward move)"
                        % "tools/recompute_truth.py")
    n.add_argument("--slip-north", type=float, default=0.0)
    n.add_argument("--no-recompute", dest="slip_sigma", action="store_const", const=None)
    n.add_argument("--obslogs", required=True)
    n.add_argument("--run", action="append", help="<arm label>=<run folder>, repeatable")
    n.add_argument("--out", required=True, help="output stem: writes <stem>.json and <stem>.md")
    n.add_argument("--title", default=None)
    n.add_argument("--compare", default=None, help="another analysis .json (the simulated rehearsal) for the gap")
    e = sub.add_parser("estimate")
    e.add_argument("--obslogs", required=True)
    return ap


def main(argv=None):
    a = parser().parse_args(argv)
    return {"convert": cmd_convert, "run": cmd_run, "analyze": cmd_analyze, "estimate": cmd_estimate}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
