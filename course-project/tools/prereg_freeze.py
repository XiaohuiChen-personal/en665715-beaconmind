#!/usr/bin/env python3
"""Freeze the main study's pre-registration: hash every file the runs and the analysis depend on, record the model
servers and package versions, and precompute each arm's configuration tag.

Usage (Spark host, from the repository root, on a clean checkout of the commit that holds the final prereg.md):
  python3 course-project/tools/prereg_freeze.py --out course-project/evidence/M4/M4.T1/prereg.json
  python3 course-project/tools/prereg_freeze.py --verify --out course-project/evidence/M4/M4.T1/prereg.json
The freeze refuses a tree whose frozen files are modified or untracked. `--verify` re-hashes exactly the files and
logs listed in prereg.json (not the current list), compares the environment it can see, and exits 1 on any change.
Every run's config tag (tools/replay_run.py `config_invariant`) must equal the tag frozen here; study_analyze.py
checks that, and that each run was launched from a clean tree.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote this freeze tool and revised it after the analysis
review of the same day.
"""
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]          # repository root
CP = "course-project/"
sys.path.insert(0, str(ROOT / CP / "tools"))
sys.path.insert(0, str(ROOT / CP / "beaconmind" / "src"))
FROZEN = [
    "evidence/M4/M4.T1/prereg.md", "tools/prereg_freeze.py", "tools/prereg_power.py", "evidence/M4/M4.T1/power.txt",
    "prompts/robot_system_prompt_v3.3.txt", "configs/dv.json", "configs/providers.json",
    "beaconmind/src/beaconmind/__init__.py", "beaconmind/src/beaconmind/geometry.py", "beaconmind/src/beaconmind/dv.py",
    "beaconmind/src/beaconmind/envs/kinsim_lite.py",
    "beaconmind/src/beaconmind/harness/tools_d5.py", "beaconmind/src/beaconmind/harness/replay.py",
    "beaconmind/src/beaconmind/harness/providers/anthropic_messages.py",
    "beaconmind/src/beaconmind/harness/providers/openai_chat.py",
    "beaconmind/src/beaconmind/harness/anthropic_replay.py",
    "beaconmind/src/beaconmind/baselines/b1_gtsam.py", "beaconmind/src/beaconmind/metrics/pilot.py",
    "beaconmind/src/beaconmind/metrics/stats.py", "beaconmind/src/beaconmind/metrics/judge.py",
    "tools/pilot_record.py", "tools/replay_run.py", "tools/replay_run.sh", "tools/b1_run.py", "tools/study_analyze.py",
    "tools/study_judge.py", "tools/pilot_judge.py", "tools/serve_qwen38.sh", "tools/serve_gemma4_vllm.sh",
]
DESIGN = {
    "study": "main-2026-11", "condition": "drift2 (2 % systematic odometry over-read, duplicated IDs)",
    "obslogs_dir": "course-project/data/main/obslogs/test/drift2", "seeds": "2000-2029",
    "replacement_rule": "a seed whose B2 episode fails is replaced by the next unused seed from 2030 upward (none failed)",
    "arms": {"B0": "dead reckoning, rounded at every step", "B1": "GTSAM iSAM2 online estimate, odometry-scale "
             "calibration, oracle association", "B2": "coded procedure (drives the log)",
             "L2": ["claude-opus-5-5", "qwen38-flash-xhigh", "gemma4-26b"]},
    "repeats": 1, "max_steps": 150, "workers": {"claude-opus-5-5": 8, "qwen38-flash-xhigh": 8, "gemma4-26b": 16},
    "order_seed": 20261110, "opus_cap_usd": 250, "judge_cap_usd": 25,
    "primary_endpoint": "unaligned ATE-RMSE over all steps of the episode, per seed, at report precision",
    "family_1": "H1[arm]: ATE(arm)-ATE(B0)<0, the three LLM arms, Holm at 0.05; a test not run counts as p=1",
    "family_2": "H2[arm]: log(ATE(arm)/ATE(B1))-log 2<0, Holm at 0.05, tested only if every H1 is rejected",
    "test": "exact one-sided Wilcoxon signed-rank (zeros dropped, ties exact); exact sign test if |G1|>1",
    "estimand": "Hodges-Lehmann estimate with its exact 95 % interval (median and order-statistic interval under the "
                "sign test)",
    "practical_h1": "H1 rejected and the interval's upper end below -0.03 m",
    "secondary": "H4: Friedman over the three LLM arms (Kendall's W); pairwise two-sided exact signed-rank with Holm, "
                 "interpreted only if Friedman p<0.05",
    "missing": "a seed stopped by an infrastructure failure is rerun once (resume); steps still missing are scored as "
               "invalid-report fallbacks and counted; sensitivity: H1 without unfinished seeds",
    "judge": "gpt-6.1-sol, evidence v2, 10 random valid-report steps per seed and arm (seed 777), descriptive",
}


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def seed_list(text):
    out = []
    for part in text.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b) + 1)) if b else [int(a)]
    return out


def run(*a):
    try:
        return subprocess.check_output(list(a), text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def environment():
    """What the Spark host can tell about the servers, images and packages the runs and the analysis use."""
    home = pathlib.Path.home()
    tpl = home / ".cache/huggingface/qwen38-flash-dgx/chat-templates/" \
        "models--nvidia--Qwen3.8-Flash-Next-NVFP4--fc694b54fb0174e0913e6adf86691ef85a4ead47-fp8hybrid.jinja"
    venv = home / ".venvs/beaconmind/bin/python"
    pkgs = run(str(venv), "-c", "import importlib.metadata as m, json; print(json.dumps({p: m.version(p) for p in "
               "('numpy','scipy','matplotlib','gtsam')}))")
    cont = run("docker", "run", "--rm", "beaconmind-ros:humble", "python3", "-c",
               "import anthropic, openai, json; print(json.dumps({'anthropic': anthropic.__version__, "
               "'openai': openai.__version__}))")
    return {"qwen38_chat_template_sha256": sha(tpl) if tpl.exists() else None,
            "qwen38_image_id": run("docker", "image", "inspect", "qwen38-flash-dgx:v0.30", "--format", "{{.Id}}"),
            "beaconmind_ros_image_id": run("docker", "image", "inspect", "beaconmind-ros:humble", "--format", "{{.Id}}"),
            "gemma4_snapshot": run("ls", str(home / ".cache/huggingface/hub/models--google--gemma-4-26B-A4B-it/snapshots")),
            "gemma4_weights_index_sha256": sha(next((home / ".cache/huggingface/hub/models--google--gemma-4-26B-A4B-it/snapshots")
                                                  .glob("*/model.safetensors.index.json"))) if (home / ".cache/huggingface/hub/"
                                                  "models--google--gemma-4-26B-A4B-it/snapshots").exists() else None,
            "ollama_version": run("/usr/local/bin/ollama", "--version"),
            "host_venv_packages": json.loads(pkgs) if pkgs else None,
            "container_packages": json.loads(cont) if cont else None}


def git(*args):
    return run("git", "-C", str(ROOT), *args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--allow-dirty", action="store_true", help="dry run only: the output is marked not valid")
    args = ap.parse_args()
    out = pathlib.Path(args.out)
    if args.verify:
        ref = json.loads(out.read_text())
        bad = [f for f, h in ref["files"].items() if not (ROOT / CP / f).exists() or sha(ROOT / CP / f) != h]
        bad += ["obslog seed %s" % s for s, h in ref["obslogs"].items()
                if sha(ROOT / ref["obslogs_dir"] / ("seed_%s.json" % s)) != h]
        env = environment()
        envbad = [k for k, v in ref.get("environment", {}).items() if v is not None and env.get(k) not in (None, v)]
        print("frozen at %s; now at %s" % (ref["git_commit"], git("rev-parse", "HEAD")))
        print("files and logs: " + ("OK, all %d files and %d logs match" % (len(ref["files"]), len(ref["obslogs"]))
                                    if not bad else "CHANGED: " + ", ".join(bad)))
        print("environment: " + ("OK" if not envbad else "CHANGED: " + ", ".join(envbad)))
        sys.exit(1 if bad or envbad else 0)
    from replay_run import config_invariant  # noqa: E402
    seeds = seed_list(DESIGN["seeds"])
    dirty = git("status", "--porcelain", "--untracked-files=all", "--", *[CP + f for f in FROZEN])
    if dirty and not args.allow_dirty:
        sys.exit("refusing to freeze: frozen files are modified or untracked:\n" + dirty)
    files = {f: sha(ROOT / CP / f) for f in FROZEN}
    logs = {str(s): sha(ROOT / DESIGN["obslogs_dir"] / ("seed_%d.json" % s)) for s in seeds}
    tags = {}
    for arm in DESIGN["arms"]["L2"]:
        _, tags[arm] = config_invariant(arm, ROOT / CP / "configs/providers.json",
                                        ROOT / CP / "prompts/robot_system_prompt_v3.3.txt",
                                        DESIGN["repeats"] - 1, DESIGN["max_steps"])
    doc = {"valid": not dirty, "git_commit": git("rev-parse", "HEAD"), "git_commit_short": git("rev-parse", "--short=12", "HEAD"),
           "design": DESIGN, "seeds": seeds, "obslogs_dir": DESIGN["obslogs_dir"], "config_tags": tags,
           "files": files, "obslogs": logs, "environment": environment()}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1) + "\n")
    print("wrote %s: %d files, %d logs, commit %s, valid=%s, tags %s" % (out, len(files), len(logs),
                                                                        doc["git_commit_short"], doc["valid"], tags))


if __name__ == "__main__":
    main()
