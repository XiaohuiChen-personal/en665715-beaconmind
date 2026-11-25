#!/usr/bin/env bash
# The real-log replay chain for set real-2026-11-25 (M3.T19), as one script that can be re-run: after any interruption
# (the Spark lost power at 18:13:57 UTC on 2026-11-25) run it again and it continues where the run folders left off.
#   tmux new -d -s bm-rr-chain "bash course-project/data/real-replay/real-2026-11-25/replay_chain.sh ['resume reason']"
# Every part is a run folder and its seeds. A part whose seeds all have every step written is skipped; a part with a
# run.json is resumed with the reason (the pre-registered rule for an infrastructure failure: each resume records its
# reason in run.resume-*.json, and the runner refuses a resume under another configuration); a part without one starts.
# A part whose folder lock is held (a runner already writing it) is waited for, then checked again.
#   API:  Opus 5.5 on b2-real-06 (5001, 5002), cap US$14.50 for that folder (the set's US$70 less what the other two
#         Opus folders spent), in the background beside the GPU stages.
#   GPU:  one model server at a time. Qwen3.8 on b2-real-05 (4001-4003) and b2-real-06 (5001, 5002), side by side on
#         one server; then Gemma 4 (vLLM) on all seeds of the index, one worker per episode (or gemma-workers).
# Every stage is logged to chain.log; each runner to its own log.
# AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: written for the M3.T19 real-log replays.
set -u
cd "$HOME/Projects/en665715-beaconmind" || exit 1
R=course-project/data/real-replay/real-2026-11-25
T=course-project/tools
LOG=$R/chain.log
REASON=${1:-"replay_chain.sh re-run after an interruption (this boot began $(uptime -s))"}
ALL=$(python3 -c "import json,sys; print(','.join(str(e['seed']) for e in json.load(open(sys.argv[1]))['episodes']))" \
      "$R/obslogs/index.json")

say() { echo "$(date -u +%H:%M:%S) replay_chain: $*" >> "$LOG"; }
last_exit() { grep '^EXIT' "$1" 2>/dev/null | tail -1 | awk '{print $2}'; }

# missing <folder> <seeds>: the seeds of the list whose rows in the folder fall short of the log's steps
missing() {
  python3 - "$R/obslogs" "$1" "$2" <<'PY'
import json, os, sys
obs, folder, seeds = sys.argv[1], sys.argv[2], [int(s) for s in sys.argv[3].split(",")]
out = []
for s in seeds:
    n = len(json.load(open(os.path.join(obs, "seed_%d.json" % s)))["records"])
    p = os.path.join(folder, "seed_%d.jsonl" % s)
    rows = 0
    if os.path.exists(p):
        for line in open(p, encoding="utf-8", errors="replace"):
            try:
                json.loads(line)
                rows += 1
            except ValueError:
                pass
    if rows < n:
        out.append(str(s))
print(",".join(out))
PY
}

# part <arm> <folder> <seeds> <workers> <log> <cap>: run or resume one run folder until its seeds are complete
part() {
  local arm=$1 folder=$R/runs/$2 seeds=$3 workers=$4 log=$5 cap=$6 todo
  todo=$(missing "$folder" "$seeds")
  if [ -z "$todo" ]; then say "$2: complete"; return 0; fi
  if [ -f "$folder/.lock" ] && ! flock -n "$folder/.lock" true; then
    say "$2: a runner holds its lock; waiting for it"
    flock "$folder/.lock" true
    todo=$(missing "$folder" "$seeds")
    if [ -z "$todo" ]; then say "$2: complete"; return 0; fi
  fi
  local how=(--resume-reason "$REASON") what="resume"
  [ -f "$folder/run.json" ] || { how=(); what="first run"; }
  say "$2: seeds $todo to do ($what)"
  bash $T/real_replay.sh --provider "$arm" --obslogs $R/obslogs --out "$folder" --seeds "$seeds" --cap-usd "$cap" \
    --workers "$workers" "${how[@]}" >> "$log" 2>&1
  echo "EXIT $?" >> "$log"
  todo=$(missing "$folder" "$seeds")
  say "$2: exit $(last_exit "$log"); $(grep 'done: total spent' "$log" | tail -1); still to do: ${todo:-none}"
}

gpu_clear() {
  for _ in $(seq 1 12); do
    if ! docker ps --format '{{.Names}}' | grep -qxE 'bm-qwen38|bm-gemma4-vllm' \
       && [ -z "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null)" ]; then return 0; fi
    sleep 10
  done
  return 1
}

# After a crash: a file being appended when the power went can end in zeros or a torn line. For every run folder no
# runner holds: cut such a seed file back to its complete lines; cut such a spend ledger back the same way and append,
# labelled, what the written rows prove was spent beyond it plus US$0.10 for each step that was in flight (paid, not
# written), so the cap stays conservative. The original is kept as <file>.crash-<UTC time>.
repair() {
  python3 - "$R/runs" "$R/obslogs" <<'PY'
import fcntl, glob, json, os, shutil, sys, time
runs, obs = sys.argv[1], sys.argv[2]
stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

def complete_lines(b):
    keep = []
    for line in b.split(b"\0")[0].split(b"\n"):
        if not line.strip():
            continue
        try:
            json.loads(line)
        except ValueError:
            break
        keep.append(line)
    return keep

for d in sorted(glob.glob(os.path.join(runs, "*/"))):
    lock = os.path.join(d, ".lock")
    if os.path.exists(lock):
        fh = open(lock)
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            continue                                   # a runner is writing this folder: leave it alone
    torn_seeds = 0
    for p in sorted(glob.glob(os.path.join(d, "seed_*.jsonl"))):
        b = open(p, "rb").read()
        if b and (b"\0" in b or not b.endswith(b"\n")):
            keep = complete_lines(b)
            shutil.copy(p, p + ".crash-" + stamp)
            open(p, "wb").write(b"".join(l + b"\n" for l in keep))
            torn_seeds += 1
            print("repaired %s: kept %d complete rows" % (p, len(keep)))
    sp = os.path.join(d, "spend.jsonl")
    if os.path.exists(sp):
        b = open(sp, "rb").read()
        if b and (b"\0" in b or not b.endswith(b"\n")):
            keep = complete_lines(b)
            ledger = sum(json.loads(l)["usd"] for l in keep)
            rows = sum(json.loads(l).get("cost_usd") or 0.0 for p in glob.glob(os.path.join(d, "seed_*.jsonl"))
                       for l in open(p, "rb") if l.strip())
            seeds = [int(os.path.basename(p)[5:-6]) for p in glob.glob(os.path.join(d, "seed_*.jsonl"))]
            in_flight = sum(1 for s in seeds if sum(1 for l in open(os.path.join(d, "seed_%d.jsonl" % s), "rb") if l.strip())
                            < len(json.load(open(os.path.join(obs, "seed_%d.json" % s)))["records"]))
            shutil.copy(sp, sp + ".crash-" + stamp)
            t = round(time.time(), 3)
            extra = [{"t": t, "usd": round(max(0.0, rows - ledger), 6), "note": "crash repair %s: the written rows' "
                      "cost_usd %.4f minus the intact ledger %.4f" % (stamp, rows, ledger)},
                     {"t": t, "usd": round(0.10 * in_flight, 2), "note": "crash repair %s: US$0.10 for each of %d "
                      "steps in flight (paid calls, rows not written)" % (stamp, in_flight)}] if rows > 0 else []
            open(sp, "wb").write(b"".join(l + b"\n" for l in keep) + b"".join((json.dumps(e) + "\n").encode() for e in extra))
            print("repaired %s: ledger %.4f, rows %.4f, added %.4f" % (sp, ledger, rows, sum(e["usd"] for e in extra)))
PY
}

say "started (resume reason: $REASON)"
REPAIRED=$(repair 2>&1)
[ -n "$REPAIRED" ] && say "after a crash: $REPAIRED"

# API: Opus, beside the GPU stages
part claude-opus-5-5 "claude-opus-5-5+b2-real-06" 5001,5002 2 "$R/claude-opus-5-5+b2-real-06.log" 14.50 &
OPUS=$!

# GPU 1: Qwen3.8
Q5=$(missing "$R/runs/qwen38-flash-xhigh+b2-real-05" 4001,4002,4003)
Q6=$(missing "$R/runs/qwen38-flash-xhigh+b2-real-06" 5001,5002)
if [ -n "$Q5$Q6" ]; then
  if docker ps --format '{{.Names}}' | grep -qx bm-gemma4-vllm; then
    say "Qwen3.8 work remains: stopping the Gemma 4 server first: $(bash $T/serve_gemma4_vllm.sh stop 2>&1)"
  fi
  say "Qwen3.8 server: $(bash $T/serve_qwen38.sh start 2>&1 | tail -1)"
  if bash $T/serve_qwen38.sh wait >> "$LOG" 2>&1; then
    part qwen38-flash-xhigh "qwen38-flash-xhigh+b2-real-05" 4001,4002,4003 3 "$R/qwen38-flash-xhigh.log" 0 &
    A=$!
    part qwen38-flash-xhigh "qwen38-flash-xhigh+b2-real-06" 5001,5002 2 "$R/qwen38-flash-xhigh+b2-real-06.log" 0 &
    B=$!
    wait $A $B
  else
    say "the Qwen3.8 server did not become ready"
  fi
  say "stopping the Qwen3.8 server: $(bash $T/serve_qwen38.sh stop 2>&1)"
else
  say "Qwen3.8: complete"
fi

# GPU 2: Gemma 4 on every seed of the index
if [ -n "$(missing "$R/runs/gemma4-26b" "$ALL")" ]; then
  if docker ps --format '{{.Names}}' | grep -qx bm-qwen38; then
    say "stopping the Qwen3.8 server: $(bash $T/serve_qwen38.sh stop 2>&1)"
  fi
  if ! gpu_clear; then
    say "the GPU is not clear; Gemma not started:"
    docker ps --format '{{.Names}} {{.Image}}' >> "$LOG"
  else
    say "Gemma 4 server: $(bash $T/serve_gemma4_vllm.sh start 2>&1 | tail -1)"
    if bash $T/serve_gemma4_vllm.sh wait >> "$LOG" 2>&1; then
      W=$(tr -dc '0-9' < "$R/gemma-workers" 2>/dev/null)
      W=${W:-$(echo "$ALL" | tr ',' '\n' | wc -l)}
      part gemma4-26b gemma4-26b "$ALL" "$W" "$R/gemma4-26b.log" 0
    else
      say "the Gemma 4 server did not become ready"
    fi
    say "stopping the Gemma 4 server: $(bash $T/serve_gemma4_vllm.sh stop 2>&1)"
  fi
else
  say "Gemma 4: complete"
fi

wait $OPUS
say "end of this run; still to do: opus-b2-real-06 [$(missing "$R/runs/claude-opus-5-5+b2-real-06" 5001,5002)]" \
    "qwen-b2-real-05 [$(missing "$R/runs/qwen38-flash-xhigh+b2-real-05" 4001,4002,4003)]" \
    "qwen-b2-real-06 [$(missing "$R/runs/qwen38-flash-xhigh+b2-real-06" 5001,5002)]" \
    "gemma [$(missing "$R/runs/gemma4-26b" "$ALL")]"
