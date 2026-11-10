#!/usr/bin/env bash
# Copy one task's evidence folder from the Spark's clone back into the Mac's working copy (plan/README.md L6).
# Usage (Mac):  bash course-project/tools/pull_evidence.sh M<n> M<n>.T<k>
# AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the first evidence pull (private-repo layout).
# Claude Opus 5.5 via Claude Code, 2026-11-10: pointed it at the public repo and the Spark clone.
set -euo pipefail

if [ "$#" -ne 2 ] || [ -z "${1:-}" ] || [ -z "${2:-}" ]; then
  echo "usage: pull_evidence.sh M<n> M<n>.T<k>" >&2
  exit 2
fi
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
ssh -o ConnectTimeout=15 -o BatchMode=yes xiaohui_chen@spark-2a60 \
  "cd ~/Projects/en665715-beaconmind && tar czf - course-project/evidence/${1}/${2}" \
  | tar xzf - -C "$REPO"
echo "pulled course-project/evidence/${1}/${2}"
