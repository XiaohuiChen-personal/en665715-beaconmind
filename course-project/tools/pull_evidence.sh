#!/usr/bin/env bash
# AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the Spark-to-Mac evidence pull (plan/README.md L6).
set -euo pipefail

if [ "$#" -ne 2 ] || [ -z "${1:-}" ] || [ -z "${2:-}" ]; then
  echo "usage: pull_evidence.sh M<n> M<n>.T<k>" >&2
  exit 2
fi

ssh -o ConnectTimeout=15 -o BatchMode=yes xiaohui_chen@spark-2a60 \
  "cd ~/Projects/EN.665.715 && tar czf - course-project/evidence/${1}/${2}" \
  | tar xzf - -C /Users/xiaohuichen/Projects/EN.665.715
