"""Every step of the real B2 episodes replayed through both coded procedures: the frozen kinsim_lite one that
tools/car_batch.py ran (closed_loop.B2Driver() without a policy) and the room's kinsim_room.make_b2_policy(). Each step
is given the logged observation and the logged previous report, so it compares the two decisions on the same
history. Per episode: steps compared, steps where the frozen one reproduces the logged decision, steps where the room
policy decides differently (decision, memory or pose), and the step where the frozen one stopped, if any.
Each batch is replayed under the design values it ran with (the manifest's dv record; --dv configs/dv-real.json for
every real batch), through beaconmind.dv_real.use_dv as tools/car_batch.py applies it.
usage (course-project/beaconmind, PYTHONPATH=src): python3 b2_policy_replay.py DV_FILE BATCH_DIR...

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this replay."""
import glob, json, os, sys
from beaconmind.harness import closed_loop as cl
from beaconmind.envs import kinsim_room as kr
from beaconmind import dv_real


def compare(path):
    rows = [json.loads(l) for l in open(path)]
    room = kr.make_b2_policy()
    n = same_logged = differ = 0
    stop = None
    for r in rows:
        obs, prev, logged = r.get("observation"), r.get("prev_report"), r.get("report")
        if obs is None or (r.get("agent_called") is False):
            continue
        try:
            fr, _, _ = cl.B2Driver._frozen(obs, prev)
        except NotImplementedError as exc:
            rr, _, _ = room(obs, prev)
            stop = {"step": r["step"], "frozen": str(exc), "room_decision": rr["decision"],
                    "room_blocked_heading_deg": rr["memory"].get("blocked_heading_deg")}
            continue
        except Exception as exc:     # noqa: BLE001
            stop = {"step": r["step"], "frozen_error": "%s: %s" % (type(exc).__name__, exc)}
            continue
        rr, _, _ = room(obs, prev)
        n += 1
        if logged and logged.get("decision") == fr["decision"]:
            same_logged += 1
        if (rr["decision"], rr["memory"], rr["pose"], rr["map"]) != (fr["decision"], fr["memory"], fr["pose"], fr["map"]):
            differ += 1
    return {"steps": n, "frozen_reproduces_logged": same_logged, "room_differs": differ, "frozen_stopped": stop}


dv_file = sys.argv[1]
for batch in sys.argv[2:]:
  with dv_real.use_dv(dv_real.resolve_arg(dv_file)):
    m = json.load(open(os.path.join(batch, "manifest.json")))
    for e in m["episodes"]:
        ep = e["id"] if "id" in e else e.get("index")
        for path in sorted(glob.glob(os.path.join(batch, "episodes", str(ep), "seed_*.jsonl"))):
            if path.endswith(".moves.jsonl"):
                continue
            out = compare(path)
            print("%-12s %-8s %-7s ended_by %-6s scenario %-3s | %s" % (os.path.basename(batch.rstrip("/")), ep, e["status"],
                  e.get("ended_by") or (e.get("result") or {}).get("ended_by"), (e.get("target_start") or {}).get("id"), json.dumps(out)))
