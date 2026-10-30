#!/usr/bin/env bash
set -euo pipefail

# Generative-AI disclosure: GPT-5.6 Sol in Cursor wrote the first version of these
# instructor-template-specific validation exceptions; Claude Opus 5.5 in Cursor updated
# them for the October 2026 two-slide revision.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SCHEMATIC="is part of the instructor-requested input/output system schematic on the quad chart (user-approved 2026-10-01 with the two-slide layout)."

args=(
  --allow-placeholder-geometry
  "1:0:Instructor quad-chart has no usable title placeholder instance; the native title is repositioned into the upper-left quadrant, verified complete by check_render_fit.py on the LibreOffice render and by Quick Look."
  --allow-placeholder-geometry
  "1:1:Instructor quad-chart has no usable content placeholder instance; the native subtitle is repositioned as the problem-statement area, verified complete by check_render_fit.py on the LibreOffice render and by Quick Look."
  --allow-placeholder-geometry
  "2:0:Two Content title moved from (0.917,0.399,11.500,1.450) to (0.917,0.300,11.500,0.620) in, same left and width, so the cited evidence and measurement protocol fit at >= 8 pt; no native layout of the instructor template has a taller content area; verified by check_render_fit.py and Quick Look."
  --allow-placeholder-geometry
  "2:1:Two Content left column top raised from 1.997 to 1.020 in (height 4.759 to 5.735 in); left 0.917, width 5.667 and bottom 6.755 in unchanged, so the 16 cited references fit at 8.25 pt; verified by check_render_fit.py and Quick Look."
  --allow-placeholder-geometry
  "2:2:Two Content right column top raised from 1.997 to 1.020 in (height 4.759 to 5.735 in); left 6.750, width 5.667 and bottom 6.755 in unchanged, so the measurement protocol fits at 8 pt; verified by check_render_fit.py and Quick Look."
  --allow-custom-placement
  "1:3:Vertical divider is inherited unchanged from the instructor-required quad-chart template."
  --allow-custom-placement
  "1:4:Horizontal divider is inherited unchanged from the instructor-required quad-chart template."
)

declare -a parts=(
  "10:Mission box"
  "11:Mission-to-agent arrow"
  "12:LLM agent box"
  "13:Agent-to-validator arrow"
  "14:Validator box"
  "15:Validator-to-car arrow"
  "16:Car box (Pico 2 W and ESP32-CAM)"
  "17:Observation-builder box"
  "18:Observation-to-agent arrow"
  "19:Deterministic-tools box"
  "20:Tool-call arrow"
  "21:Tool-result arrow"
  "22:Isaac Sim twin box"
  "23:Twin-to-perception arrow"
  "24:Perception box"
  "25:Perception-to-observation arrow"
  "26:Car-to-perception arrow"
  "27:Evaluator-log box"
)
for part in "${parts[@]}"; do
  args+=(--allow-custom-placement "1:${part%%:*}:${part#*:} ${SCHEMATIC}")
done

python3 "$ROOT/tools/validate_presentation.py" \
  "$ROOT/course-project/Chen-Project-Proposal.pptx" \
  --expected-slides 2 \
  --talk-track "$ROOT/course-project/proposal-talk-track.md" \
  --template "$ROOT/course-project/QuadChart-Template.pptx" \
  "${args[@]}"
