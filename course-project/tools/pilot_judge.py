#!/usr/bin/env python3
"""Score the pilot agent's notes with two LLM judges and run the automated judge calibration.

Item sets (built deterministically from the pilot run logs):
  real  every valid replay report's note;
  kl    known-label notes assembled by code from source steps whose report agrees with the coded
        procedure (so the evidence is unambiguous), 3 variants per step rotating over 7 defect types;
        seed 1000 items are "dev" (not used for any reported calibration number), the rest "test";
  fab   40 real notes (seeds 1001-1004) with one false clause appended (expected faithful = 0);
  rep / rev / pad  the same 40 real notes judged again, with the anchors listed 2-1-0, and with a
        neutral padding sentence appended (levels must not change).
Judges: gemma (gemma4:26b-a4b-it-bf16 on Ollama, local) and sol (gpt-6.1-sol, OpenAI Responses API).

Run inside beaconmind-ros on the Spark (openai SDK; Ollama reached on 127.0.0.1 with --network host):
  python3 tools/pilot_judge.py --runs data/pilot-20261029/opus --out data/pilot-20261029/judge \
      --judges gemma,sol --cap-usd 25
Resumable: items already in <out>/<judge>.jsonl are skipped. Keys come from the environment only.

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: wrote this runner.
"""
import argparse
import concurrent.futures as cf
import json
import os
import pathlib
import random
import re
import sys
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "beaconmind" / "src"))
from beaconmind.envs import kinsim_lite as ks  # noqa: E402
from beaconmind.metrics import judge as J  # noqa: E402

VARIANTS = ["clean", "plain", "none", "drop1", "drop2", "fab", "wrong"]
LOCK = threading.Lock()


def load_rows(runs):
    rows = []
    for p in sorted(pathlib.Path(runs).glob("seed_*.jsonl")):
        seen = set()
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r["step"] in seen:      # keep the first record of a step
                continue
            seen.add(r["step"])
            rows.append(r)
    return rows


def agrees_with_procedure(r):
    try:
        est = ks.estimate_step(r["observation"], r["prev_report"])
    except (NotImplementedError, ks.GoldUnavailable):
        return False
    rep = r["report"]
    want = sorted((a["det"], a["result"], a["beacon"]) for a, _ in est["assoc"])
    got = sorted((a.get("det"), a.get("result"), a.get("beacon")) for a in rep.get("associations") or [])
    return rep.get("pose_source") == est["pose_source"] and want == got


def variant(ev, kind, rng):
    if kind == "clean":
        return J.synth_note(ev)
    if kind == "plain":
        return J.synth_note(ev, pose_mode="plain")
    if kind == "none":
        return J.synth_note(ev, pose_mode="none")
    if kind == "drop1":
        return J.synth_note(ev, drop_events=1) if ev["material_events"] else None
    if kind == "drop2":
        return J.synth_note(ev, drop_events=2) if len(ev["material_events"]) >= 2 else None
    if kind == "fab":
        return J.synth_note(ev, fabricate=J.fabrication(ev, rng))
    if kind == "wrong":
        return J.synth_note(ev, wrong_label=True)
    raise ValueError(kind)


def _valid(rows):
    return [r for r in rows if r["checks"]["valid"] and isinstance(r["report"].get("note"), str) and r["report"]["note"].strip()]


def build_items(rows, extra=()):
    """rows: the calibration-source run (its condition name is 'nominal'); extra: [(condition, rows)]
    whose notes are scored as real notes only."""
    items = []
    valid = _valid(rows)
    for cond, rs in [("nominal", rows)] + list(extra):
        for r in _valid(rs):
            items.append({"id": "real:%s:%d:%d" % (cond, r["seed"], r["step"]), "set": "real", "cond": cond, "seed": r["seed"],
                          "step": r["step"], "note": r["report"]["note"], "evidence": J.build_evidence(r), "reverse": False,
                          "expected": None})
    rng = J.rng_for("kl")
    by_seed = {}
    for r in valid:
        by_seed.setdefault(r["seed"], []).append(r)
    k = 0
    for seed in sorted(by_seed):
        pool = [r for r in by_seed[seed] if agrees_with_procedure(r)]
        strata = {}
        for r in pool:
            strata.setdefault((r["report"]["pose_source"], bool(J.material_events(r["report"], r["prev_report"]))), []).append(r)
        chosen = []
        for key in sorted(strata):
            chosen += rng.sample(strata[key], min(2, len(strata[key])))
        chosen = sorted(rng.sample(chosen, min(6, len(chosen))), key=lambda r: r["step"])
        for r in chosen:
            ev = J.build_evidence(r)
            made = 0
            for j in range(len(VARIANTS)):
                kind = VARIANTS[(k + j) % len(VARIANTS)]
                v = variant(ev, kind, rng)
                if v is None:
                    continue
                items.append({"id": "kl:%d:%d:%s" % (seed, r["step"], kind), "set": "kl", "split": "dev" if seed == 1000 else "test",
                              "seed": seed, "step": r["step"], "kind": kind, "note": v["note"], "evidence": ev,
                              "reverse": False, "expected": v["expected"]})
                made += 1
                if made == 3:
                    break
            k += 1
    rng = J.rng_for("fab")
    base = rng.sample([r for r in valid if r["seed"] != 1000], 40)
    for r in base:
        ev, note, tag = J.build_evidence(r), r["report"]["note"].rstrip(), "%d:%d" % (r["seed"], r["step"])
        clause = J.fabrication(ev, rng)
        items.append({"id": "fab:" + tag, "set": "fab", "seed": r["seed"], "step": r["step"], "evidence": ev, "reverse": False,
                      "note": note.rstrip(".") + "; " + clause + ".", "expected": {"faithful": 0}})
        base_id = "real:nominal:" + tag
        items.append({"id": "rep:" + tag, "set": "rep", "seed": r["seed"], "step": r["step"], "evidence": ev, "reverse": False,
                      "note": note, "expected": None, "base": base_id})
        items.append({"id": "rev:" + tag, "set": "rev", "seed": r["seed"], "step": r["step"], "evidence": ev, "reverse": True,
                      "note": note, "expected": None, "base": base_id})
        items.append({"id": "pad:" + tag, "set": "pad", "seed": r["seed"], "step": r["step"], "evidence": ev, "reverse": False,
                      "note": note + J.PADDING % r["step"], "expected": None, "base": base_id})
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True, help="calibration-source run dir (condition 'nominal')")
    ap.add_argument("--extra", default="", help="more runs as cond=dir,cond=dir (real notes only)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--judges", default="gemma,sol")
    ap.add_argument("--cap-usd", type=float, default=25.0)
    ap.add_argument("--sets", default="real,kl,fab,rep,rev,pad")
    ap.add_argument("--limit", type=int, default=0, help="judge at most this many items per judge (smoke test)")
    args = ap.parse_args()
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    extra = [(c, load_rows(d)) for c, d in (p.split("=", 1) for p in args.extra.split(",") if p)]
    items = build_items(load_rows(args.runs), extra)
    for it in items:
        rf = it["evidence"]["report_fields"]
        it["known_labels"] = sorted(set(rf["map_labels"]) | {a.get("beacon") for a in rf.get("associations") or [] if a.get("beacon")}
                                    | {lc.get("beacon") for lc in rf.get("loop_closure") or [] if lc.get("beacon")})
        it["note_labels"] = sorted(set(re.findall(r"\bB\d+b?\b", it["note"])))
    (out / "items.jsonl").write_text("".join(json.dumps({k: v for k, v in it.items() if k != "evidence"}) + "\n"
                                             for it in items), encoding="utf-8")
    sets = set(args.sets.split(","))
    inv_bases = {it["base"] for it in items if it.get("base")}
    rank = {"kl": 0, "fab": 1, "rep": 3, "rev": 4, "pad": 5}
    # calibration items first, so the calibration is complete before the long tail of real notes
    todo_all = sorted((it for it in items if it["set"] in sets),
                      key=lambda it: 2 if it["id"] in inv_bases else rank.get(it["set"], 6))
    print("items:", {s: sum(1 for it in items if it["set"] == s) for s in ("real", "kl", "fab", "rep", "rev", "pad")}, flush=True)
    spent = {"usd": 0.0}
    for judge in args.judges.split(","):
        path = out / ("%s.jsonl" % judge)
        done = set()
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rec = json.loads(line)
                    done.add(rec["id"])
                    spent["usd"] += rec.get("cost_usd", 0.0) or 0.0
        todo = [it for it in todo_all if it["id"] not in done]
        if args.limit:
            todo = todo[: args.limit]
        if judge == "gemma":
            model, workers = "gemma4:26b-a4b-it-bf16", 4

            def call(prompt):
                r = J.ollama_judge(model, prompt)
                r["cost_usd"] = 0.0
                return r
        elif judge == "sol":
            from openai import OpenAI
            client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=600, max_retries=4)
            model, workers = "gpt-6.1-sol", 8

            def call(prompt):
                return J.openai_judge(client, model, prompt, effort="medium")
        else:
            sys.exit("unknown judge %s" % judge)
        print("%s (%s): %d to do, %d done, spent $%.2f" % (judge, model, len(todo), len(done), spent["usd"]), flush=True)

        def one(it):
            if spent["usd"] >= args.cap_usd:
                return None
            prompt = J.judge_prompt(it["evidence"], it["note"], reverse_anchors=it["reverse"])
            t0 = time.time()
            rec = {"id": it["id"], "set": it["set"], "judge": judge, "model": model}
            for attempt in range(3):
                try:
                    res = call(prompt)
                    rec.update(levels=res["levels"], reason=res["reason"], cost_usd=res.get("cost_usd", 0.0), error=None)
                    break
                except Exception as exc:  # recorded, retried twice, then kept as an error row
                    rec.update(levels=None, reason=None, cost_usd=0.0, error="%s: %s" % (type(exc).__name__, str(exc)[:200]))
                    time.sleep(5 * (attempt + 1))
            rec["seconds"] = round(time.time() - t0, 1)
            with LOCK:
                spent["usd"] += rec["cost_usd"]
                with open(path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec) + "\n")
            return rec

        n = 0
        with cf.ThreadPoolExecutor(max_workers=workers) as pool:
            for rec in pool.map(one, todo):
                n += 1
                if rec and (n % 25 == 0 or rec["error"]):
                    print(time.strftime("%H:%M:%S"), judge, n, "/", len(todo), rec["id"], rec["levels"], rec["seconds"], "s",
                          "$%.2f" % spent["usd"], rec["error"] or "", flush=True)
        print("%s finished, spent $%.2f" % (judge, spent["usd"]), flush=True)


if __name__ == "__main__":
    main()
