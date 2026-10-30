#!/usr/bin/env python3
"""Compare two expanded URDF files element by element, keyed by NAME (link, visual/collision name, joint).

Usage: python3 course-project/tools/urdf_named_diff.py BEFORE.urdf AFTER.urdf
urdf_compare.py compares elements by position, which misaligns once boxes are added or removed; this prints, for
every named visual, collision, inertial and joint, the before and after origin and geometry (or mass and inertia) when
they differ, and how many are identical. Standard library only.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-10-16: wrote this comparison for the plate-CAD URDF update.
"""
import sys, xml.etree.ElementTree as ET
def index(path):
    r = ET.parse(path).getroot(); out = {}
    for lk in r.findall("link"):
        n = lk.get("name")
        for el in list(lk):
            key = (n, el.tag, el.get("name") or "")
            o = el.find("origin"); g = el.find("geometry")
            geo = None if g is None or not len(g) else (g[0].tag, dict(g[0].attrib))
            val = (None if o is None else (o.get("xyz"), o.get("rpy")), geo)
            if el.tag == "inertial":
                m = el.find("mass"); i = el.find("inertia")
                val = (None if o is None else (o.get("xyz"), o.get("rpy")), m.get("value"), dict(i.attrib))
            out[key] = val
    for j in r.findall("joint"):
        o = j.find("origin"); out[("joint", j.get("name"), "")] = (o.get("xyz"), o.get("rpy"), j.find("parent").get("link"), j.find("child").get("link"))
    return out
a, b = index(sys.argv[1]), index(sys.argv[2])
same = [k for k in a if k in b and a[k] == b[k]]
print("identical elements: %d of %d before / %d after" % (len(same), len(a), len(b)))
for k in sorted(set(a) | set(b), key=str):
    if a.get(k) != b.get(k):
        print("%-60s\n    before %s\n    after  %s" % (k, a.get(k), b.get(k)))
