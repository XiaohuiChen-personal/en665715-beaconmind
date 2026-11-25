"""From a recorder bag: after a reference time, when did the car's own duty (wheel_ticks fields 12, 13) read 0, and
when did both wheel counts (fields 0, 1) last change? Also the last non-zero /pico/cmd_vel before the reference.
usage: stopan.py BAG.db3 REF_UNIX [label]
AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote this reader (read-only on the recorder's bag)."""
import sqlite3, struct, sys
db, ref = sys.argv[1], float(sys.argv[2])
label = sys.argv[3] if len(sys.argv) > 3 else ""
con = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
topics = {n: i for i, n in con.execute("select id, name from topics")}
def rows(name, t0, t1):
    return con.execute("select timestamp, data from messages where topic_id=? and timestamp between ? and ? order by timestamp",
                       (topics[name], int(t0 * 1e9), int(t1 * 1e9))).fetchall()
cmds = [(ts / 1e9, struct.unpack_from("<6d", d, 4)) for ts, d in rows("/pico/cmd_vel", ref - 3, ref + 2)]
last_nonzero = max((t for t, v in cmds if (v[0] or v[5]) and t <= ref + 0.001), default=None)
first_zero_cmd = min((t for t, v in cmds if not (v[0] or v[5]) and t >= ref - 0.001), default=None)
ticks = []
for ts, d in rows("/pico/wheel_ticks", ref - 0.5, ref + 2.0):
    n = struct.unpack_from("<I", d, 12)[0]
    v = struct.unpack_from("<%di" % n, d, 16)
    ticks.append((ts / 1e9, v[0], v[1], v[12], v[13]))
zero_duty = min((t for t, l, r, dl, dr in ticks if t >= ref and dl == 0 and dr == 0), default=None)
last_change = None
for a, b in zip(ticks, ticks[1:]):
    if (a[1], a[2]) != (b[1], b[2]) and b[0] >= ref:
        last_change = b[0]
after = [t for t in ticks if t[0] >= ref]
print("%s ref %.3f | last non-zero cmd %s | first zero cmd %s | duty 0 at %s | wheels last moved %s | counts moved after ref: L %d R %d"
      % (label, ref, "%+.3f" % (last_nonzero - ref) if last_nonzero else "-", "%+.3f" % (first_zero_cmd - ref) if first_zero_cmd else "none",
         "%+.3f" % (zero_duty - ref) if zero_duty else "-", "%+.3f" % (last_change - ref) if last_change else "-",
         after[-1][1] - after[0][1] if after else 0, after[-1][2] - after[0][2] if after else 0))
