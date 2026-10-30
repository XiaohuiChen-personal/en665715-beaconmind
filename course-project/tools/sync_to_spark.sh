#!/usr/bin/env bash
# AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the Mac-to-Spark course-project sync (plan/README.md L6).
set -euo pipefail

echo "remember: pull Spark-side evidence first (pull_evidence.sh), or it is kept but never updated"

cd /Users/xiaohuichen/Projects/EN.665.715

# Optional arguments are extra repo-relative paths added to the archive.
tar_paths=(course-project)
if [ "$#" -gt 0 ]; then
  tar_paths+=("$@")
fi

COPYFILE_DISABLE=1 tar czf - \
  --exclude __pycache__ --exclude .venv --exclude 'course-project/data' --exclude 'report/sources' \
  --exclude '*.egg-info' --exclude .pytest_cache \
  "${tar_paths[@]}" | ssh -o ConnectTimeout=15 -o BatchMode=yes xiaohui_chen@spark-2a60 \
  'cd ~/Projects/EN.665.715 && tar xzf -'

echo "synced course-project to spark-2a60"
