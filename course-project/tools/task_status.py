#!/usr/bin/env python3
"""Print plan task statuses: python3 course-project/tools/task_status.py M2.T7 [M4.T3 ...]

One line per task: "<ID> <status>", where status is todo, in-progress, blocked, done,
dropped (cut line), NO-FILE (no plan/M<n>-*.md) or NOT-FOUND (no status-table row).
Exit code 0 if every task was found, 2 otherwise. Only a status-table row has a status
word in its third column; the task-list and entry-criteria tables never do.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote this status reader (plan/README.md L12).
"""
import pathlib
import re
import sys

PLAN = pathlib.Path(__file__).resolve().parents[1] / "plan"
STATUS = re.compile(r"^(todo|in-progress|blocked|done|dropped \(cut line\))$")

missing = False
for task in sys.argv[1:]:
    files = sorted(PLAN.glob(task.split(".")[0] + "-*.md"))
    found = "NO-FILE" if not files else "NOT-FOUND"
    for f in files:
        for line in f.read_text(encoding="utf-8").splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 3 and cells[0] == task and STATUS.match(cells[2]):
                found = cells[2]
                break
        if found not in ("NO-FILE", "NOT-FOUND"):
            break
    missing = missing or found in ("NO-FILE", "NOT-FOUND")
    print(task, found)
sys.exit(2 if missing else 0)
