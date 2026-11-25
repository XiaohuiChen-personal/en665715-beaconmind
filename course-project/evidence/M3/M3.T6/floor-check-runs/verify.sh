#!/bin/bash
# Floor check: verify the new encoder scales (two FORWARD_25, tag fixes before and after). Scratch, 2026-11-25.
# AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25 (the lead agent): wrote this scratch runner; copied here unchanged but for this line.
cd ~/Projects/en665715-beaconmind; S=~/bm-scratch; OUT=$S/verify-$(date +%H%M%S).log
meas() { echo "MEAS $1 $(/usr/bin/python3 $S/tagmeas.py 10 1.5)" | tee -a $OUT; }
meas V0
for i in 1 2; do
  o=$(bash course-project/tools/car.sh move FORWARD_25 --i-am-at-the-car 2>&1)
  echo "MOVE FORWARD_25 -> $(printf "%s" "$o" | python3 -c "
import sys, json; t = sys.stdin.read(); d = json.loads(t[t.find(\"{\"):]); r = d[\"result\"]
print(r[\"result\"], \"fwd=%+.4f dyaw=%+.2f L=%s R=%s scale=%s\" % (r[\"achieved_forward_m\"], r[\"gyro_dyaw_deg\"], r[\"enc_left_ticks\"], r[\"enc_right_ticks\"], d.get(\"diag\", {}).get(\"scale_source\", \"?\")))")" | tee -a $OUT
  meas "V$i"
done
