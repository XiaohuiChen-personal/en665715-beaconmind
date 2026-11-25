"""Read /pico/cmd_vel, /pico/wheel_ticks and /pico/drive/status from a rosbag2 sqlite3 file (stdlib only; CDR by hand).
usage: bagread.py BAG.db3 T0_UNIX T1_UNIX   -> one line per message in the window
AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this reader (read-only on the recorder's bag)."""
import sqlite3, struct, sys
db, t0, t1 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
con = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
topics = {i: n for i, n in con.execute("select id, name from topics")}
want = {i for i, n in topics.items() if n in ("/pico/cmd_vel", "/pico/wheel_ticks", "/pico/drive/status")}
for tid, ts, data in con.execute("select topic_id, timestamp, data from messages where timestamp between ? and ? order by timestamp",
                                 (int(t0 * 1e9), int(t1 * 1e9))):
    if tid not in want:
        continue
    name = topics[tid]
    if name == "/pico/cmd_vel":
        v = struct.unpack_from("<6d", data, 4)
        print("%.4f cmd v=%.3f w=%.3f" % (ts / 1e9, v[0], v[5]))
    elif name == "/pico/wheel_ticks":
        ndim = struct.unpack_from("<I", data, 4)[0]
        assert ndim == 0, ndim
        n = struct.unpack_from("<I", data, 12)[0]
        vals = struct.unpack_from("<%di" % n, data, 16)
        print("%.4f ticks %s" % (ts / 1e9, list(vals)))
    else:
        print("%.4f status %d" % (ts / 1e9, struct.unpack_from("<i", data, 4)[0]))
