#!/usr/bin/env python3
"""Compare two expanded URDF files: every element, attribute and number, plus the raw text diff.

Usage: python3 course-project/tools/urdf_compare.py BEFORE.urdf AFTER.urdf
Exit 0 when the two models are identical (same elements in the same order, same attributes, every number equal as
a float, every other token equal as text); exit 1 otherwise. XML comments are not part of the model, so they are
compared only in the text diff, which is printed in full so a reader can see that only comments changed.

Standard library only (runs on the Mac; no ROS needed). Written for M2.T4 to prove that generating car_props.xacro
from configs/car.json left the expanded URDF numerically unchanged.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-10-10: wrote this comparison.
"""

import collections
import difflib
import sys
import xml.etree.ElementTree as ET


def tokens(text):
    return (text or "").split()


def as_number(token):
    try:
        return float(token)
    except ValueError:
        return None


def compare(before_text, after_text):
    """(report lines, number of mismatches)."""
    a_root, b_root = ET.fromstring(before_text), ET.fromstring(after_text)
    a_elems, b_elems = list(a_root.iter()), list(b_root.iter())
    lines, bad = [], 0
    counts = collections.Counter()
    if len(a_elems) != len(b_elems):
        lines.append("MISMATCH element count: %d before, %d after" % (len(a_elems), len(b_elems)))
        bad += 1
    for i, (a, b) in enumerate(zip(a_elems, b_elems)):
        where = "element %d <%s name=%r>" % (i, a.tag, a.get("name"))
        if a.tag != b.tag:
            lines.append("MISMATCH %s: tag %r -> %r" % (where, a.tag, b.tag))
            bad += 1
            continue
        if set(a.attrib) != set(b.attrib):
            lines.append("MISMATCH %s: attributes %s -> %s" % (where, sorted(a.attrib), sorted(b.attrib)))
            bad += 1
        fields = [("@" + k, a.get(k), b.get(k)) for k in sorted(set(a.attrib) & set(b.attrib))]
        fields.append(("text", (a.text or "").strip(), (b.text or "").strip()))
        for field, va, vb in fields:
            ta, tb = tokens(va), tokens(vb)
            if len(ta) != len(tb):
                lines.append("MISMATCH %s %s: %r -> %r" % (where, field, va, vb))
                bad += 1
                continue
            for xa, xb in zip(ta, tb):
                na, nb = as_number(xa), as_number(xb)
                if na is not None and nb is not None:
                    counts["%s %s" % (a.tag, field)] += 1
                    if na != nb:
                        lines.append("MISMATCH %s %s: %s -> %s" % (where, field, xa, xb))
                        bad += 1
                elif xa != xb:
                    lines.append("MISMATCH %s %s: %r -> %r" % (where, field, xa, xb))
                    bad += 1
                else:
                    counts["(text tokens)"] += 1
    lines.append("elements compared: %d before / %d after" % (len(a_elems), len(b_elems)))
    lines.append("numbers compared as floats, by element and field:")
    for key in sorted(k for k in counts if k != "(text tokens)"):
        lines.append("    %-28s %4d" % (key, counts[key]))
    lines.append("numbers compared in total: %d; other tokens compared as text: %d"
                 % (sum(v for k, v in counts.items() if k != "(text tokens)"), counts["(text tokens)"]))
    lines.append("mismatches: %d" % bad)
    return lines, bad


def main(argv):
    if len(argv) != 3:
        sys.stderr.write("usage: urdf_compare.py BEFORE.urdf AFTER.urdf\n")
        return 2
    before = open(argv[1], encoding="utf-8").read()
    after = open(argv[2], encoding="utf-8").read()
    print("== text diff (unified; XML comments included) ==")
    diff = list(difflib.unified_diff(before.splitlines(True), after.splitlines(True), argv[1], argv[2]))
    sys.stdout.writelines(diff if diff else ["(no text difference)\n"])
    changed = [ln for ln in diff if ln[:1] in "+-" and not ln.startswith(("+++", "---"))]
    print("changed lines: %d" % len(changed))
    print("== model comparison (comments ignored) ==")
    lines, bad = compare(before, after)
    print("\n".join(lines))
    print("RESULT: %s" % ("IDENTICAL model: every element, attribute and number is equal" if not bad
                          else "DIFFERENT model"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
