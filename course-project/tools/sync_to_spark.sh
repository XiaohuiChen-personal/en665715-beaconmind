#!/usr/bin/env bash
# Copy the Mac's working copy of the public BeaconMind repo onto the Spark's clone (plan/README.md L6).
#
# Since 2026-11-10 the Spark has a git clone of the public repo at ~/Projects/en665715-beaconmind, and that clone
# is the project's working tree there (it used to be a tar copy inside the private course repo's clone). The
# normal path is commit + push on the Mac and `git pull --ff-only` on the Spark; this script is for uncommitted
# work: it copies tracked and untracked-but-not-ignored files (so never data/, secrets or build output) on top
# of the Spark clone. Run pull_evidence.sh first if the Spark wrote evidence you have not pulled.
#
# Usage (Mac):  bash course-project/tools/sync_to_spark.sh [--dry-run]
#
# AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the first sync (private-repo layout).
# Claude Opus 5.5 via Claude Code, 2026-11-10: rewrote it for the public repo and the Spark clone.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO"
FILES="$(git ls-files -co --exclude-standard -- course-project)"
if [ "${1:-}" = "--dry-run" ]; then echo "$FILES" | head -50; echo "($(echo "$FILES" | wc -l) files)"; exit 0; fi
echo "$FILES" | COPYFILE_DISABLE=1 tar czf - --no-xattrs -T - 2>/dev/null \
  | ssh -o ConnectTimeout=15 -o BatchMode=yes xiaohui_chen@spark-2a60 \
      'cd ~/Projects/en665715-beaconmind && tar xzf - --warning=no-unknown-keyword'
echo "synced $(echo "$FILES" | wc -l | tr -d ' ') files of course-project/ to spark-2a60:~/Projects/en665715-beaconmind"
