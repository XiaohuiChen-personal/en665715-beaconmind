# BeaconMind — final presentation: slide outline and speaker notes

Talk of about 15 minutes, 15 slides, for Tuesday 2026-12-01. This file is the content of the deck and its talk
track. The deck itself is built on the JHU template in the private course repository (the template may not be
redistributed), from this outline: one `## Slide N — <title>` per slide, a `Layout:` line naming the template
layout, the text blocks, and the speaker notes under `### Notes`.

Every number is written as a key of `course-project/slides/numbers.json`, which
`course-project/tools/report_assets.py --slides` writes from the same evidence files as the report
(`evidence/M4/M4.T16/`, `evidence/M4/M4.T1/`, `configs/camera.json`, `evidence/M3/M3.T10/layout/`); the source of
each key is in `course-project/report/generated/MANIFEST.txt`. Design values (the 3 cm threshold's role, the
60° design field of view, the 1.5 m spacing of duplicated IDs) are typed from `AGENT-DESIGN.md` and
`evidence/M4/M4.T1/prereg.md`.

**Placeholders.** Text in square brackets that starts with PENDING marks a result that is not measured yet. The
numbers are those of `course-project/report/PENDING.md`: 2 (bounded-move executor and STOP on the car), 4 (measured
tag positions, detector error), 5 (real-log replay and the sim-to-real gap), 6 (closed-loop episodes on the car
and the demo video), 7 (the real-car conclusion). Nothing on a pending
line is a result.

Block syntax: `> ` an introductory line; `**…**` a column header; `- ` a bullet (two spaces of indent per
level); `~ ` a small unbulleted line; a line starting with `Figure:` names the picture and `Alt:` its
description.

## Slide 1 — BeaconMind: Can a Large Language Model Own Landmark SLAM?
Layout: Title Slide
### Subtitle
Xiaohui Chen (individual project)
### Body
EN.665.715 · December 1, 2026
### Notes
(20 s) I am Xiaohui Chen, and this is my individual project, BeaconMind. The question is in the title: can a
large language model itself keep the pose and the map of a small robot, instead of handing that job to a
classical estimator?

## Slide 2 — The Question
Layout: One Column
### Body
> LLM agents plan for robots and call tools, but pose and map still come from classical estimators [1–3].
- Can the LLM itself keep the pose and the landmark map (SLAM)?
- A small differential-drive car; the only landmarks are AprilTags [4], and some tag IDs repeat
- Tools do the arithmetic; the LLM makes the estimator's decisions
  - trust this detection? which beacon is it? accept this pose fix?
- Is it better than dead reckoning? How far from a factor graph? Faithful to its procedure? Do models differ?
### Notes
(60 s) Agents such as SayCan, ReAct agents and ROSA plan and call tools, but they take the robot's pose and map
as given. Work on spatial reasoning explains why: language models make arithmetic and geometry mistakes. So I
give the arithmetic to tools and ask a narrower question. Can the model own the decisions of an estimator:
which detection to trust, which landmark it belongs to, and whether to accept a pose fix? The tag IDs repeat on
purpose, so the tag code does not settle the association. I ask four things: is the estimate better than dead
reckoning, how far is it from a factor graph, does the model follow its procedure, and do models differ.

## Slide 3 — The System: Who Decides What
Layout: Sidebar w/ Image
Figure: slides/figures/fig-system.png
Alt: Block diagram: the step message goes to the LLM agent, which calls nine deterministic tools, writes a JSON report and sends a move to the validator, which drives the car or simulator.
### Sidebar
- The LLM owns the pose belief and the map
- Nine tools compute every number
- A validator checks every move
- Stateless: its last report is its only memory
### Notes
(60 s) The model sits in the middle. It gets a text message, calls tools, and writes a report. It owns the pose
belief and the beacon map: no other component keeps them. Nine deterministic tools compute every number, for
example composing odometry, gating a detection against the map, or fixing the pose from matched beacons. Below
the model a validator checks every move before anything is executed. The agent is stateless: each step is one
call, and its own previous report is its only memory.

## Slide 4 — One Step of the Agent
Layout: Two Column
### Intro
> The car makes one bounded move and stops. Then the agent gets one message.
### Left
**The agent receives (text)**
- Odometry increment
- Tag detections: ID, range, bearing
- Safety flags
- Its own previous report
### Right
**The agent returns (JSON)**
- Pose, and how it got it
- Associations and loop closures
- The beacon map
- The next move
- A one-sentence note
### Notes
(60 s) One step. The car makes one of five bounded moves and stops. The agent then receives the odometry
increment, the tag detections with ID, range and bearing, safety flags, and its previous report. It follows a
procedure stated in its prompt: predict the pose, gate each detection against the map, correct the pose from
confirmed beacons, add or confirm beacons, and pick a move. It returns one JSON report. The same procedure
written as Python code is one of my baselines; I call it the coded procedure.

## Slide 5 — A Pre-Registered Study in Simulation
Layout: One Column
### Body
- Replay: every arm reads the same {{n.seeds}} held-out logs ({{n.steps}} steps), with a 2 % odometry over-read
- Baselines: B0 dead reckoning; B1 factor graph given the true association [5]; B2 the procedure as code
- LLM arms, one run per seed: Claude Opus 5.5, Qwen3.8-Flash-Next, Gemma 4 26B
- H1 per model: trajectory error (ATE [6]) below B0; practical only if the interval is below −{{sesoi.cm}} cm
- H2 (within twice B1) is tested only if every H1 is rejected [7, 8]
- Frozen by hash before any model saw a held-out seed; 22 declared deviations
### Notes
(90 s) The main study is a replay study in a kinematic simulator. Every arm reads the same thirty held-out
logs, so every arm sees identical observations. The odometry over-reads by two percent, because my pilot showed
that without drift nothing beats dead reckoning in a small arena. There are three baselines: dead reckoning, a
factor graph that is given the true association, and the coded procedure. There are three models, one run per
seed. The hypotheses, the tests and the analysis code were frozen by hash before any model saw a held-out seed.
H1 asks whether a model's trajectory error is below dead reckoning's, with exact signed-rank tests and Holm's
correction. I call a result practical only if the whole interval is below minus three centimeters. H2, within
twice the factor graph, is tested only if every H1 is rejected. This is a self-registration in my own
repository, and it lists twenty-two deviations from my first plan.

## Slide 6 — Result: Better Than Dead Reckoning, Not by Much
Layout: Sidebar w/ Image
Figure: slides/figures/fig-h1.png
Alt: Per-seed differences in trajectory error, model minus dead reckoning, for Opus 5.5, Qwen3.8 and Gemma 4, with the estimates, exact 95 percent intervals and the minus 3 cm threshold.
### Sidebar
- Opus 5.5: {{h1.opus.est}} cm
- Qwen3.8: {{h1.qwen.est}} cm
- Both rejected; neither practical
- Gemma 4: {{h1.gemma.est}} cm, worse
### Notes
(90 s) Each dot is one seed: the model's trajectory error minus dead reckoning's, so below zero is better. For
Opus the estimate is {{h1.opus.est}} centimeters, with an interval from {{h1.opus.lo}} to {{h1.opus.hi}}, and a
Holm-adjusted p of {{h1.opus.p-holm}}. For Qwen3.8 it is {{h1.qwen.est}}, interval {{h1.qwen.lo}} to
{{h1.qwen.hi}}. Both null hypotheses are rejected. But both intervals reach above the dashed line at minus three
centimeters, so neither result is supported in practice. My power analysis had predicted exactly that. Gemma 4
is on its own scale on the right: it is worse than dead reckoning on {{h1.gemma.worse}} of {{n.seeds}} seeds,
by a median of {{h1.gemma.est}} centimeters.

## Slide 7 — Result: The Models Reproduce the Coded Procedure
Layout: Sidebar w/ Image
Figure: slides/figures/fig-ate.png
Alt: Per-seed trajectory error of dead reckoning, the factor graph, the coded procedure, Opus 5.5, Qwen3.8 and Gemma 4 on a logarithmic axis, with medians.
### Sidebar
- Within 1 cm of B2 on {{fid.opus.within}} and {{fid.qwen.within}} of {{n.seeds}} seeds
- B2 alone: {{b2b0.est}} cm
- {{h2.opus.ratio}}× and {{h2.qwen.ratio}}× the factor graph
- H2 not tested
### Notes
(90 s) This is every arm's error per seed on a log axis. Look at the three middle strips: the coded procedure,
Opus and Qwen3.8 are almost the same. Opus is within one centimeter of the code on {{fid.opus.within}} of
{{n.seeds}} seeds, Qwen3.8 on {{fid.qwen.within}}. The code alone gains {{b2b0.est}} centimeters over dead
reckoning, so the models' gain is in effect the procedure's gain. Qwen3.8 did a little better on four seeds
where it departed from the code, but those are four single runs. The factor graph is far ahead: the models'
error is an estimated {{h2.opus.ratio}} and {{h2.qwen.ratio}} times its error. H2 was not tested, because the
gate needs every H1 rejected and Gemma's was not. That is the pre-registered rule, not a choice I made after
seeing the data. The two stronger models do differ statistically, but that result rests on a few seeds.

## Slide 8 — Why Gemma 4 Failed (Post Hoc)
Layout: Two Column
### Intro
> Checked in the run logs after the analysis. It is not a parsing artifact.
### Left
**What the logs show**
- No tool call on {{es.gemma.notool.share}} % of its steps
- Error grows {{es.gemma.notool.cm-per-step}} cm on each such step [9]
- {{es.gemma.jumps}} pose jumps with no fix
### Right
**Tool use, notes, cost**
- Tool-call F1: {{f1.opus}}, {{f1.qwen}}, {{f1.gemma}}
- Note rubric: {{rubric.opus}}, {{rubric.qwen}}, {{rubric.gemma}}
- Opus: US${{cost.seed.opus}} per episode
### Notes
(75 s) A result this far in the wrong direction could be a bug, so I checked the logs afterwards. This part is
exploratory. It is not a parsing problem: an independent decoder recovers the scored pose from every valid
report. Gemma 4 answered without calling any tool on {{es.gemma.notool.share}} percent of its steps. On those
steps it carries the pose forward by its own arithmetic, and its position error grows by
{{es.gemma.notool.cm-per-step}} centimeters per step. It also moved its pose by more than five centimeters
without a successful fix {{es.gemma.jumps}} times. On the right, in the order Opus, Qwen3.8, Gemma: tool-call F1
against the coded procedure, and the rubric score a judge model gave the agents' notes. One caveat: the prompt
was developed with another model and was not adapted to Gemma. Opus cost about {{cost.seed.opus}} dollars per
episode; the local models cost no API fee but were much slower.

## Slide 9 — The Real Room
Layout: Two Column_50/50
Figure: slides/figures/fig-room.png
Alt: Plan of the room arena with the twenty nominal AprilTag positions and their IDs on the walls, the desk, and the dashed driving area.
### Body
- A 3.8 × 5.1 m room; {{room.tags}} tags ({{room.tags.printed}} printed), three IDs twice
- Camera field of view {{cam.hfov}}°, not the design's 60°
- One heading sees a tag center from {{cov2.30.rule.one}} % of poses, a whole tag from {{cov2.30.camera.one}} % (study: {{cov.15.study.one}} %)
- {{cl.range-m}} m range limit, provisional
- Rehearse in simulation first; record every real run
- [PENDING 4: measured tag positions; detector error; confirmed range limit]
### Notes
(60 s) The real arena is a room, not a small square. The layout has {{room.tags}} tags on its walls, and three
IDs are used twice; {{room.tags.printed}} are printed and none is mounted yet. The camera is calibrated; its field of view is {{cam.hfov}} degrees,
not the sixty degrees the design and the simulator assumed. That matters. In the study arena as simulated, one
heading saw a tag from {{cov.15.study.one}} percent of poses. In the room, with the measured field of view and a
{{cl.range-m}} meter range limit, the same rule gives {{cov2.30.rule.one}} percent, and a camera model that
needs the whole tag in the picture gives {{cov2.30.camera.one}} percent, although a full turn finds two
different tags from {{cov2.30.camera.turn2}} percent of positions. The {{cl.range-m}} meter limit is the value
used in the rehearsals; it is provisional until a tag-accuracy pilot on real frames confirms it. Two rules govern the real car: every session is rehearsed in simulation first, and every
real run is recorded in full. [PENDING 4: say the measured tag positions, the detector's error and the confirmed range limit once
they exist.]

## Slide 10 — Demo: The Agent in Closed Loop
Layout: One Column
### Body
- One simulated episode per arm (n = 1) in the room simulator: {{cl.n-tags}} tags at nominal positions, {{cl.range-m}} m range
- Opus 5.5 and Fable 5.2 made the identical {{cl.opus.moves}} moves (coded procedure: {{cl.b2.moves}}); from each model's own state, every decision equals the procedure's
- All mapped {{cl.opus.tags-found}} of {{cl.n-tags}} tags; no move refused; no full pose fix
- Error {{cl.opus.ate}} cm for each arm; dead reckoning {{cl.opus.b0-ate}} cm: no drift and {{cl.opus.path-m}} m of travel, little to correct
- Prompt variant: range threshold 2.0 → {{cl.range-m}} m; cost US${{cl.opus.cost}} and US${{cl.fable.cost}}
- [PENDING 6, 2: demo video and episodes on the car; executor and STOP as tested on the car]
### Notes
(150 s, with the video) In the study the agent chose no move: it only estimated. In closed loop the arm chooses
each move and the validator checks it. I ran one exploration episode per arm in a simulator of the real room,
with the {{cl.n-tags}}-tag layout at its nominal positions: the coded procedure, Claude Opus 5.5 and Claude
Fable 5.2, which is not an arm of the study and ran at effort {{cl.fable.effort}}, below its default. The coded
procedure here is the frozen one plus one rule for a dead end, which did not fire in this episode. This is n equals one, so nothing here is a statistical result. The
two models made the identical {{cl.opus.moves}} moves, and at every step the frozen procedure, run on what the
model saw and on the model's own previous report, makes the model's decision. They left the procedure's path only after a pose
argument that differed from the procedure's changed one tool result: Opus's by a millimeter of rounding,
Fable's by two centimeters because it was not yet updated by that step's fix. So this shows agreement with the procedure, not a difference in driving. All three mapped
{{cl.opus.tags-found}} of {{cl.n-tags}} tags, and no move was refused. No arm got a full pose fix. The
episode's odometry had no two percent over-read and the car traveled about {{cl.opus.path-m}} meters, so there
was little to correct, and dead reckoning was at least as accurate: {{cl.opus.b0-ate}} centimeters against
{{cl.opus.ate}}. One deviation: the
prompt differs from the study prompt in one number, the range beyond which a detection is rejected, so these
numbers are not comparable with the replay results. The episodes cost {{cl.opus.cost}} and {{cl.fable.cost}}
dollars. [PENDING 6: play the demo recording and say what the episodes on the car showed. PENDING 2: say how
the car is stopped.] This is a demonstration, not a benchmark.

## Slide 11 — Real-Car Results
Layout: One Column
### Body
- Ground truth on the car: tape, and a full-turn resection against the surveyed tags (planned)
- Real logs test no hypothesis: this ground truth cannot resolve 3 cm
- [PENDING 5: number of recorded episodes; each arm's final-position error on the real logs; the same in the simulated rehearsal; the sim-to-real gap]
### Notes
(60 s) [PENDING 5: report the recorded real episodes, each arm's final-position error on the real logs, and how
that compares with the rehearsal of the same episode in simulation.] On the car the ground truth is a tape
measure and a resection against the surveyed tags, so the error is a final-pose error, not a trajectory error,
and it cannot resolve three centimeters. The real logs therefore describe the sim-to-real gap; they test no
hypothesis.

## Slide 12 — Limitations
Layout: One Column
### Body
- Simulation only so far: kinematic, placeholder noise, a 60° field of view
- Replay is open loop: the coded procedure drove every log, so the agent's moves were not evaluated
- The factor graph was given the true association
- One prompt, {{n.seeds}} seeds, one run each, one drift level
- Duplicated IDs were easy: copies at least 1.5 m apart
- Fidelity is measured against the agent's own specification
### Notes
(60 s) The limits. Everything measured so far is in a kinematic simulator with placeholder noise. Replay is
open loop: the coded procedure drove every log, so the agent's own moves were never evaluated and its errors
could not change what it saw next. The factor graph was given the true association, which flatters it. There
is one prompt, thirty seeds, one run per seed and one drift level. The duplicated IDs were easy to tell apart.
And fidelity is measured against the agent's own specification: where the model and the code disagree, the
study does not say which one is right.

## Slide 13 — Conclusions
Layout: One Column
### Body
- With geometry in tools and the procedure in the prompt, two models beat dead reckoning: supported statistically, not practically
- They did it by executing the procedure, which a short program also does at negligible cost
- The model that skipped its tools failed (post hoc)
- Not measured: what an LLM adds when the rules do not fit, such as close duplicates or operator requests
- [PENDING 7: what the real car showed]
### Notes
(60 s) To conclude. In this study two capable models kept a pose estimate that beats dead reckoning by
{{h1.opus.gain}} and {{h1.qwen.gain}} centimeters, which is statistically supported and not practically supported. They did it by
executing the prescribed procedure, and a short program does the same at negligible cost. The model that
skipped its tools failed. What the study did not measure is what a language model adds when the procedure's
rules do not fit: close duplicates, hidden IDs, operator requests. That is the next test. [PENDING 7: one
sentence on the real car and the closed loop.]

## Slide 14 — References
Layout: One Column
### Body
~ [1] M. Ahn et al., "Do as I can, not as I say: Grounding language in robotic affordances," arXiv:2204.01691, 2022.
~ [2] S. Yao et al., "ReAct: Synergizing reasoning and acting in language models," ICLR, 2023.
~ [3] R. Royce et al., "Enabling novel mission operations and interactions with ROSA," IEEE Aerospace Conf., 2025.
~ [4] E. Olson, "AprilTag: A robust and flexible visual fiducial system," IEEE ICRA, 2011.
~ [5] M. Kaess et al., "iSAM2: Incremental smoothing and mapping using the Bayes tree," Int. J. Robotics Research, 2012.
~ [6] J. Sturm et al., "A benchmark for the evaluation of RGB-D SLAM systems," IEEE/RSJ IROS, 2012.
~ [7] F. Wilcoxon, "Individual comparisons by ranking methods," Biometrics Bulletin, 1945.
~ [8] S. Holm, "A simple sequentially rejective multiple test procedure," Scandinavian J. Statistics, 1979.
~ [9] L. Gao et al., "PAL: Program-aided language models," ICML, 2023.
### Notes
(10 s) The references for the slides; the report has the full list of 41.

## Slide 15 — Generative-AI Disclosure
Layout: One Column
### Body
- Generative AI did most of the drafting, coding and running, under my direction
- Claude Opus 5.5: design documents, prompt, simulator, harness, baselines, analysis, the study runs
- Claude Fable 5.2: real-car software, rehearsals and closed-loop runs, the report rewrite, this deck; Fable 5.1: related works
- Grok 4.7 and GPT-5.6 Sol: early scaffolding and project research
- Under test: Opus 5.5, Qwen3.8, Gemma 4, and Fable 5.2 in the closed loop; judge: GPT-6.1 Sol
- I chose the question, models and scope, took every measurement, and am responsible for this work
### Notes
(20 s) Generative AI did most of the drafting, coding and running in this project, under my direction; the
slide names the models and what each did, and the report's disclosure has the detail. I chose the question, the
models and the scope, took every physical measurement, and I am responsible for all of it.

## Generative-AI disclosure

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: drafted this outline and its speaker notes from the
report (`course-project/report/Chen-Project-Report.tex`) and the evidence files, and built the deck from it.
Xiaohui Chen reviews the content, presents it, and is accountable for it.
