#!/usr/bin/env bash
# AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the 2-second vLLM running/waiting probe.
# Appends "<epoch> running=<n> waiting=<n>" from http://127.0.0.1:8000/metrics.
# The metric line starts with vllm:num_requests_running or vllm:num_requests_waiting;
# the count is that line's last whitespace-separated field, as an integer.
# A failed curl appends running=NA waiting=NA.
set -u
out="${1:?probe log path required}"
mkdir -p "$(dirname "$out")"
while true; do
  epoch=$(date +%s)
  if ! body=$(curl -sf --max-time 5 http://127.0.0.1:8000/metrics); then
    printf '%s running=NA waiting=NA\n' "$epoch" >> "$out"
  else
    running=$(printf '%s\n' "$body" | awk '/^vllm:num_requests_running/ {print $NF; exit}')
    waiting=$(printf '%s\n' "$body" | awk '/^vllm:num_requests_waiting/ {print $NF; exit}')
    ri=$(awk -v v="$running" 'BEGIN { if (v == "" || v == "NA") print ""; else printf "%d", int(v+0) }')
    wi=$(awk -v v="$waiting" 'BEGIN { if (v == "" || v == "NA") print ""; else printf "%d", int(v+0) }')
    if [ -z "$ri" ] || [ -z "$wi" ]; then
      printf '%s running=NA waiting=NA\n' "$epoch" >> "$out"
    else
      printf '%s running=%s waiting=%s\n' "$epoch" "$ri" "$wi" >> "$out"
    fi
  fi
  sleep 2
done
