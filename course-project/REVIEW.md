# Project Proposal Review

## 2026-10-01 revision (BeaconMind; instructor feedback)

Reviewed: 2026-10-01

Artifact: `course-project/Chen-Project-Proposal.pptx` (2 slides)

This revision answers the instructor's two comments on the 2026-09-14 submission and retargets
the deck from the known-route rover to BeaconMind (`APPROACH-LLM-SLAM.md`, `AGENT-DESIGN.md`
v3.3). Slide 1 remains the instructor quad chart. Slide 2 is a native "Two Content" backup
that holds the cited findings and the measurement protocol. The official prompt asked for one
slide; slide 1 is complete on its own.

### Instructor comments → what changed

1. **Motivation / prior work.** The problem statement now cites language-conditioned planning
   (SayCan, Salimpour 2025, Zero-Shot Planners), closed-loop verification (Inner Monologue,
   ReAct, LLM-Modulo), embodied-agent failure modes (Embodied Agent Interface, Lost in
   Aggregation, Li 2026 spatial world models, Lost in Space, SafeAgentBench), and the gap
   that pose/map come from classical SLAM or a pre-built map (SayPlan, Lee 2026 MCP,
   Syarubany 2026). Each claim was re-checked against the paper's arXiv HTML or abstract on
   2026-10-01. SayCan's 84% → 67% planning-success drop (No-VF ablation) is in the talk
   track, not on the slide.
2. **How metrics are applied.** Slide 1 states the application rule in one bullet (start-frame
   pose vs. Isaac / ceiling-camera truth → ATE; success judged at DONE from ground truth;
   unsafe/invalid = request suite + validator log + fault injection). Slide 2 writes the
   collection and interpretation protocol for pose, association, mission success, refusal,
   latency/cost, and statistics.

### Citation checks (2026-10-01)

Confirmed by fetching the record, not by memory:

- [1] Ahn et al. 2022, arXiv:2204.01691 — "lack real-world experience"; Table 2 84% vs 67%.
- [2] Salimpour et al. 2025, arXiv:2508.05294 — course required survey.
- [3] Huang et al. 2022a, arXiv:2201.07207 — naive plans often cannot map to admissible actions.
- [4] Huang et al. 2022b, arXiv:2207.05608 — closed-loop language feedback.
- [5] Yao et al. 2023, arXiv:2210.03629 — ReAct vs acting-only on ALFWorld.
- [6] Kambhampati et al. 2024, arXiv:2402.01817 — LLM-Modulo position.
- [7] Li et al. 2024, arXiv:2410.07166 — Embodied Agent Interface.
- [8] Jiang et al. 2026, arXiv:2606.22219 — collapse by 10×10; walker lift up to 92 points.
- [9] Li et al. 2026, arXiv:2604.10690 — no cumulative spatial knowledge.
- [10] Deng et al. 2026, arXiv:2601.22228v2 — best VLM 0.66 vs LoFTR 0.99.
- [11] Yin et al. 2024, arXiv:2412.13178v5 — most safety-aware agent rejects 10% of detailed
  hazardous tasks.
- [12] Rana et al. 2023, arXiv:2307.06135 — pre-built 3D scene graph.
- [13] Lee et al. 2026, arXiv:2609.27340 — MCP over existing ROS stack; Cartographer + Nav2
  on Isaac Sim Nova Carter (verified in the HTML, §experiments).
- [14] Syarubany et al. 2026, arXiv:2601.00555 — "ORB-SLAM3 provides global pose" (Introduction).
- [15] Sturm et al. 2012 IROS; Umeyama 1991; evo.
- [16] Anderson et al. 2018, arXiv:1807.06757.

### Mechanical validation

`course-project/validate_proposal.sh` against the instructor template:

```text
PASS: /Users/xiaohuichen/Projects/EN.665.715/course-project/Chen-Project-Proposal.pptx (25 warning(s))
```

All warnings are the documented geometry and custom-placement exceptions in
`validate_proposal.sh`. Canonical-JHU-template check still fails (instructor template
takes precedence); do not describe this deck as JHU-theme compliant.

### Render and fit

LibreOffice PDF + `check_render_fit.py`:

```text
PASS: every rendered word lies inside its text shape
```

Quick Look: one-slide copies (`qlmanage -t` of `slide1-only.pptx` and `slide2-only.pptx`)
showed the same complete text as the LibreOffice render; no clipping. PowerPoint
Accessibility Checker: **not run** — Microsoft PowerPoint is not installed on this Mac.
Deferred.

### Open issues

- The official prompt asked for one slide. Confirm with Xiaohui whether Canvas should get
  both slides or only the quad chart.
- New targets and measurement definitions listed in `proposal-talk-track.md` ("New in this
  revision") are not yet written into `AGENT-DESIGN.md`.
- PowerPoint Accessibility Checker remains deferred.

---

Reviewed: 2026-09-14

Artifact: `course-project/Chen-Project-Proposal.pptx` (historical one-slide rover proposal)

## Scope and authoritative template

The instructor requires the supplied single-slide `QuadChart-1.pptx`. The exact source was
copied to `course-project/QuadChart-Template.pptx`, and the generated proposal preserves its
four-quadrant structure and divider lines.

This assignment-specific template conflicts with the repository's general JHU-template rule:
its theme and native layout are not from
`reference/templates/JHU-Presentation-Template_Fa25.potx`. The instructor's explicit
template requirement takes precedence for this deliverable. Validation therefore uses the
instructor template as the artifact baseline, while the canonical-JHU failure is recorded
honestly below.

## Content review

An independent adversarial review checked requirement coverage, technical feasibility,
model claims, safety boundaries, evaluation, citations, disclosure, and visual readability.

### Confirmed findings and fixes

1. **ROSA tool names were absent.** Added `navigate_to_landmark`, `verify_arrival`,
   `inspect_station`, `return_home`, and `stop`.
2. **The evaluation did not explicitly test Questions 1 and 2.** Added one-shot versus
   replanning and encoder-only versus encoder+IMU versus encoder+IMU+AprilTag conditions.
3. **The on-slide safety boundary was ambiguous.** Changed the DGX block to show bounded
   ROSA tools and a ROS 2 validator, labeled the cart command as validated goals, and retained
   Pico PID/watchdog control.
4. **"Qwen3.5-35B-A3B (proven)" overstated the evidence.** Changed it to "smoke-tested";
   project-specific ROSA integration and mission reliability remain unverified.
5. **"Best model" lacked a decision rule.** The proposal now selects highest simulated
   mission success, breaking ties by valid-tool-call rate and then p95
   command-to-accepted-tool latency.
6. **Metrics lacked operational detail.** Added map-frame pose error, the latency start/end
   events, 30 held-out physical missions, and a 0.5-second command-loss stop target.
7. **Citations and disclosure were too small.** Increased the source line from 6.8 to 7.4 pt,
   increased disclosure from 6.9 to 7.5 pt, and added Anderson et al. (2018) for SPL.
8. **The first render's diagram arrows pointed backward.** Corrected the DrawingML endpoint
   from `headEnd` to `tailEnd` and re-rendered with both engines.
9. **The slide did not show the requested agent-prompt design or concrete ROS 2
   interfaces.** Added the prompt's mission role, landmark registry, bounded tool schema,
   and observe→verify→replan policy; added `/odom`, `/imu/data`,
   `/camera/image/compressed`, bounded `/cmd_vel`, and tool actions; and explained that
   vLLM's OpenAI-compatible API replaces the fixed Ollama path to support model comparison.

No review claim is treated as an experimental result. The models, Pico transport, camera,
odometry, mission success, and target thresholds remain proposed work and have not been
executed on the physical robot.

### Clean review round

After the fixes, a fresh independent pass rechecked the instructor requirements, the
vLLM/Ollama rationale, prompt design, ROS 2 interfaces, safety boundary, model wording,
evaluation conditions, citations, disclosure, and final render. It reported:

```text
Agent-prompt design, concrete ROS 2 interfaces, and the vLLM rationale are now explicit.
No confirmed critical or major findings.
```

## Placeholder geometry exceptions

The supplied slide deleted its own native placeholders even though its layout is named
`Title Slide`. A new slide from that same native layout was created so the artifact has a
real title and subtitle placeholder.

- Slide 1, title placeholder idx 0:
  - Native geometry: `(1524000,1122363,9144000,2387600)` EMU
    (`1.667, 1.227, 10.000, 2.611` inches).
  - Final geometry: `(320040,118872,5532120,329184)` EMU
    (`0.350, 0.130, 6.050, 0.360` inches).
  - Reason: place the project title in the upper-left quadrant without changing the
    instructor's four-quadrant structure.
- Slide 1, subtitle placeholder idx 1:
  - Native geometry: `(1524000,3602038,9144000,1655762)` EMU
    (`1.667, 3.939, 10.000, 1.811` inches).
  - Final geometry: `(320040,493776,5532120,822960)` EMU
    (`0.350, 0.540, 6.050, 0.900` inches).
  - Reason: use a native content placeholder for the problem statement inside the
    instructor-designated upper-left quadrant.

Fit check: both placeholders render completely with no visible clipping in LibreOffice and
Quick Look.

## Custom-placement exceptions

The slide-level graphics are required by the instructor template or by its requested
input/output schematic:

- Shapes 3 and 4: inherited vertical and horizontal quad-chart divider lines.
- Shapes 10–13: user-input box, mission-flow arrow, DGX Spark processing box, and
  validated-goal arrow.
- Shapes 15–19: robot-cart box, sensor-feedback box, two feedback arrows, and output box.

All unlabeled graphics have meaningful OOXML `descr` alternative text. The diagram remains
editable rather than being flattened into an image.

## Mechanical validation

### Package and content check

```text
PASS: final package, metadata, one-slide count, and 22 required content markers verified.
Artifact size: 37518 bytes; slide shapes: 19.
```

### Validation against the instructor-supplied template

Command: `course-project/validate_proposal.sh`. The script runs
`tools/validate_presentation.py` against the instructor template and supplies the documented
scoped geometry and custom-placement exceptions above.

```text
WARNING placeholder.geometry_exception: slide 1 placeholder idx=0 repositioned with documented dual-render reason.
WARNING placeholder.geometry_exception: slide 1 placeholder idx=1 repositioned with documented dual-render reason.
WARNING graphics.custom_placement_exception: slide 1 shapes 3, 4, 10–13, and 15–19 use documented instructor-template or schematic placements.
PASS: /Users/xiaohuichen/Projects/EN.665.715/course-project/Chen-Project-Proposal.pptx (13 warning(s))
```

### Canonical JHU-template check

The same current artifact was also checked against the repository's canonical JHU template:

```text
ERROR theme.identity: deck theme XML hashes do not match the canonical template
ERROR layout.signature: slide 1: layout 'Title Slide' placeholder signature does not match its canonical native layout
FAIL: /Users/xiaohuichen/Projects/EN.665.715/course-project/Chen-Project-Proposal.pptx (2 error(s), 13 warning(s))
```

This is an acknowledged open issue caused by the instructor's explicit requirement to use
the supplied quad-chart template. The artifact must not be described as canonical-JHU
template compliant.

## Render and accessibility review

- LibreOffice: all text and graphics visible; no clipping or overlap observed.
- macOS Quick Look: all text and graphics visible; no clipping or overlap observed.
- Cross-engine difference: minor font wrapping/spacing differences only; meaning and reading
  order remain intact.
- PowerPoint Accessibility Checker: **not run** because Microsoft PowerPoint is not installed
  on this Mac. This check remains deferred.

## Open implementation issues

1. Qwen3.8-27B-FP8 and Gemma 4-26B-A4B-it are only cached candidates; vLLM serving,
   structured tool calls, and ROSA compatibility have not been validated.
2. Qwen3.5-35B-A3B has only smoke-test evidence for vision and tool invocation, not
   project-level mission reliability.
3. The ESP32 camera identity, motor encoder counts, power modules, and Pico 2 W wireless
   transport remain unresolved as listed in `course-project/CONTEXT.md`.
4. The success and pose-error values are proposal targets, not measured outcomes.

## Generative-AI provenance

GPT-5.6 Sol in Cursor assisted with research, architecture, model-comparison framing,
slide drafting, build automation, and review remediation. Xiaohui Chen selected the project
direction and remains responsible for understanding, validating, and submitting the work.
