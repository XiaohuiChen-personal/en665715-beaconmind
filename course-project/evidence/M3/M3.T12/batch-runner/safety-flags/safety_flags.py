"""How often the guard's safety flags in the real episodes' observations left no forward move, or only FORWARD_10:
the batches that ran without the tracker's slip term (b2-real-01 to -03) against those with it (b2-real-05, -06).
The flags are what the agents saw (the obslogs of the real-log replay set real-2026-11-25). Answers the review's
question whether the slip term reached the agents' input systematically.
usage: python3 safety_flags.py OBSLOGS_DIR

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this count."""
import glob
import json
import os
import sys

GROUPS = (("without the slip term (b2-real-01 to -03)", ("1", "2", "3")),
          ("with the slip term (b2-real-05, -06)", ("4", "5")))
d = sys.argv[1]
idx = json.load(open(os.path.join(d, "index.json")))
flagged = {str(e["seed"]) for e in idx.get("episodes", []) if e.get("ended_by") not in (None, "DONE")}
print("episode            steps  both forward moves  only FORWARD_10  no forward move")
tot = {}
for f in sorted(glob.glob(os.path.join(d, "seed_*.json"))):
    seed = os.path.basename(f)[5:-5]
    recs = json.load(open(f))["records"]
    n = len(recs)
    fa = [tuple((r["raw"].get("safety") or {}).get("forward_allowed") or []) for r in recs]
    both = sum(1 for x in fa if len(x) == 2)
    only10 = sum(1 for x in fa if x == ("FORWARD_10",))
    none = sum(1 for x in fa if not x)
    print("seed %s%s  %5d  %5d (%4.1f %%)  %5d (%4.1f %%)  %5d (%4.1f %%)" % (
        seed, " (flagged)" if seed in flagged else "          ", n, both, 100.0 * both / n, only10,
        100.0 * only10 / n, none, 100.0 * none / n))
    if seed in flagged:
        continue
    for name, heads in GROUPS:
        if seed[0] in heads:
            t = tot.setdefault(name, [0, 0, 0, 0])
            t[0] += n; t[1] += both; t[2] += only10; t[3] += none
print()
print("Without the flagged episode:")
for name, _ in GROUPS:
    n, both, only10, none = tot[name]
    print("%s: %d steps; both %.1f %%, only FORWARD_10 %.1f %%, no forward move %.1f %%" % (
        name, n, 100.0 * both / n, 100.0 * only10 / n, 100.0 * none / n))
