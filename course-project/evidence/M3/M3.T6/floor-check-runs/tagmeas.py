"""Median range/bearing per tag from the newest frames of the active recorder session (floor check, 2026-11-25).
Usage: tagmeas.py [n_frames=12] [wait_s=3]. Waits wait_s so the frames are taken after the car settled.
Scratch helper; AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25."""
import glob, json, os, statistics, sys, time
repo = os.path.expanduser("~/Projects/en665715-beaconmind/course-project")
sys.path.insert(0, os.path.join(repo, "beaconmind", "src"))
import cv2
from beaconmind.perception import tags as T
from beaconmind import camera_model as cm
n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
time.sleep(float(sys.argv[2]) if len(sys.argv) > 2 else 3.0)
t0 = time.time()
active = open(os.path.join(repo, "data/real/.active")).read().strip()
sess = active if os.path.isabs(active) else os.path.join(repo, "data/real", os.path.basename(active))
cam = cm.load_camera()
# newest n frames written after t0 (wait for them)
while True:
    files = sorted(glob.glob(os.path.join(sess, "frames", "0*.jpg")))
    fresh = [f for f in files if os.path.getmtime(f) >= t0]
    if len(fresh) >= n: break
    time.sleep(0.2)
per = {}
for f in fresh[:n]:
    for d in T.detect_tags(cv2.imread(f), cam, tag_size_m=0.1599):
        per.setdefault(d["id"], []).append((d["range_m"], d["bearing_deg"]))
out = {str(k): {"n": len(v), "range_m": round(statistics.median(r for r, _ in v), 4),
                "bearing_deg": round(statistics.median(b for _, b in v), 2)} for k, v in sorted(per.items())}
print(json.dumps({"t_unix": round(t0, 2), "frames": n, "tags": out}))
