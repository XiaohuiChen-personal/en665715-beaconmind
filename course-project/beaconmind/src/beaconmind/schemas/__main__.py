"""Validate a JSON or JSONL file: python -m beaconmind.schemas <name> <file>.

A .jsonl file is checked line by line (observation logs and run logs). Prints
OK <file> (<n> objects) or one line per error, and exits 1 when any object fails.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the schema CLI.
"""

import json
import sys
from pathlib import Path

from beaconmind.schemas import validate


def main(argv):
    if len(argv) != 3:
        sys.stderr.write("usage: python -m beaconmind.schemas <name> <file>\n")
        return 2
    name = argv[1]
    path = Path(argv[2])
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        documents = []
        for line_no, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            documents.append((line_no, json.loads(line)))
    else:
        documents = [(None, json.loads(text))]
    failed = False
    for line_no, document in documents:
        for error in validate(name, document):
            failed = True
            if line_no is None:
                print(error)
            else:
                print("line %d: %s" % (line_no, error))
    if failed:
        return 1
    print("OK %s (%d objects)" % (argv[2], len(documents)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
