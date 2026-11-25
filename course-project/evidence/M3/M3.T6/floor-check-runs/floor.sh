#!/bin/bash
# Floor check (work list 2.8), camera-measured against the wall tags. Stops at the first move that is not "done".
# Scratch runner, 2026-11-25. AI-assisted: Claude Opus 5.5 via Claude Code.
cd ~/Projects/en665715-beaconmind
S=~/bm-scratch; OUT=$S/floor-$(date +%H%M%S).log
mv1() {  # move name [args]; prints one line; returns 1 unless result is done
  local o; o=$(bash course-project/tools/car.sh move "$@" --i-am-at-the-car 2>&1)
  local line; line=$(printf "%s" "$o" | python3 -c "
import sys, json, re
t = sys.stdin.read(); i = t.find(\"{\")
try:
    d = json.loads(t[i:]); r = d.get(\"result\", {}); g = d.get(\"diag\", {})
    print(\"%s %s fwd=%+.4f dyaw=%+.2f L=%s R=%s dur=%.2f\" % (r.get(\"result\"), r.get(\"reason\"), r.get(\"achieved_forward_m\") or 0, r.get(\"gyro_dyaw_deg\") or 0, r.get(\"enc_left_ticks\"), r.get(\"enc_right_ticks\"), r.get(\"duration_s\") or 0))
except Exception as e:
    print(\"UNPARSED \" + t[-300:].replace(chr(10), \" \"))")
  echo "MOVE $* -> $line" | tee -a $OUT
  case "$line" in done*) return 0;; *) return 1;; esac
}
meas() { echo "MEAS $1 $(/usr/bin/python3 $S/tagmeas.py 10 1.5)" | tee -a $OUT; }
meas F0
for i in 1 2 3 4; do mv1 FORWARD_25 || exit 3; meas "F1.$i"; done
for i in 1 2 3; do
  mv1 FORWARD_10 || exit 3
  A=$(tail -1 $OUT | sed -E "s/.*fwd=([+-][0-9.]+).*/\1/" | tr -d +)
  mv1 BACKWARD_10 --prev-forward "$A" || exit 3; meas "F2.$i"
done
for i in 1 2 3; do mv1 TURN_LEFT_30 || exit 3; done; meas F3.left90
for i in 1 2 3; do mv1 TURN_RIGHT_30 || exit 3; done; meas F3.back
echo "FLOOR SEQUENCE DONE (F5 STOP next)" | tee -a $OUT
