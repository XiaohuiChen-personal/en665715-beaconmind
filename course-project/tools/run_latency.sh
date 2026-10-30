#!/usr/bin/env bash
# AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the sequential M1.T4 latency run (thinking on, then off).
# One smoke_test.py process at a time, so a request does not wait for a vLLM slot.
set -euo pipefail
STAMP="$1"; D=~/Projects/EN.665.715/course-project/data/latency; mkdir -p "$D"
cd ~/Projects/EN.665.715/assignments/assignment4/system-prompt/tools
bash ~/Projects/EN.665.715/course-project/tools/vllm_queue_probe.sh $D/$STAMP-probe.log & PROBE=$!
trap 'kill $PROBE 2>/dev/null || true' EXIT
python3 smoke_test.py ../evidence/print-output.txt $D/$STAMP-think.jsonl 5 1 2>&1 | tee $D/$STAMP-think.log
python3 smoke_test.py ../evidence/print-output.txt $D/$STAMP-nothink.jsonl 5 0 2>&1 | tee $D/$STAMP-nothink.log
echo "LATENCY RUN DONE $STAMP"
