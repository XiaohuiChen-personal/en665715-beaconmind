# Course project approach — LLM as SLAM with AprilTag beacons

**Project name: BeaconMind** (chosen 2026-09-28; see `CONTEXT.md`).

**Status (2026-09-27): direction chosen by Xiaohui, contingent on feasibility.** The research
supports it **with conditions** (§2). Three things are still open:

- the Module 4 D1 specifics (§12), awaiting the student's approval;
- whether the instructor must accept a change from the 2026-09-14 proposal (not checked);
- the team/role question (§11, item 10).

If adopted, this replaces the known-map "Landmark-Grounded Natural-Language Mission Rover" from
the 2026-09-14 proposal, which called itself "a starting point rather than a binding final
design".

Evidence for every sourced statement is in
[`research/2026-09-27-llm-slam-feasibility/`](research/2026-09-27-llm-slam-feasibility/README.md):
five topic files, each researched and then adversarially verified. The document itself was
reviewed the same day by three adversarial reviewers; all 29 distinct findings were confirmed and
fixed. Product facts (models, prices, latency, Isaac Sim versions) are as of 2026-09-27;
re-check them before committing money or time.

## 1. The idea

The kit car explores an **unknown arena** whose layout it has never seen. Printed AprilTags on
the walls act as beacons, as in landmark SLAM. A language model keeps the robot's **pose belief**
and the **beacon map** and makes the SLAM decisions: which observations to trust, which beacon an
observation belongs to, when a place is a revisit (loop closure), where to explore next and when
mapping is done. Deterministic code does the arithmetic. The same agent runs in **Isaac Sim**
(a digital twin of the car) and on the **real car**. The project **benchmarks many models** in
both worlds: frontier API models, open-weight models on the DGX Spark, and navigation foundation
models.

## 2. Feasibility verdict

**Technically feasible: yes, conditionally.** Every supporting component exists:

- tag detection;
- a classical GTSAM reference;
- Isaac Sim tag materials and ground truth;
- frontier and local models with vision and tool calling;
- navigation foundation models.

The core — an LLM that **owns the SLAM decisions** (level L2, §3) — has **no precedent**; it is
the project's contribution, not an off-the-shelf part. A one-day search (2026-09-27) found no
report of an LLM doing landmark SLAM with a measured trajectory error. One possibly related
paper, an LLM-guided pedestrian dead-reckoning study (Sensors 2026), could not be opened. The
outcome is **uncertain**, which is what makes it worth doing. Feasibility is gated by three pilots:

- camera accuracy (W2);
- Isaac Sim on aarch64 (W1);
- harness and API compatibility (W5).

| Question | Answer | Evidence |
| --- | --- | --- |
| Has anyone made an LLM/VLM the metric SLAM estimator? | **Not found.** Every system found gets geometry from a classical component (ORB-SLAM3, Cartographer, RTAB-Map, MCL, COLMAP). LLMs pick frontiers, add semantics, re-rank place-recognition candidates. The closest system (Syarubany 2026, arXiv:2601.00555) uses AprilTags as anchors with an LLM choosing moves, but ORB-SLAM3 supplies the pose and it reports only qualitative results | topic 1 |
| Will an LLM-maintained pose belief drift? | **Unknown: nobody has measured it.** Pre-reasoning-model evidence (Faith and Fate, seqBench, CogEval) and "Lost in Aggregation" (2026) predict compounding error. Reasoning models (GPT-5, GPT-OSS-120B) did reach 100 % on sequential grid navigation where instruct models failed (Sandfuchs 2026, arXiv:2604.09604), but **with the pose given to them**, so that is not a test of estimation. The prior is uninformed, not favourable | topic 1 (claims, challenges, unknowns) |
| What helps LLMs with spatial state? | Explicit Cartesian state (Martorell 2025, arXiv:2502.16690); an explicit cognitive map (VSI-Bench); structured memory (Thinking on Maps). Handing arithmetic to code: PAL, SpatialClaw, VADAR | topics 1, 5 |
| Can this hardware support a classical tag-SLAM reference? | **Yes, on paper.** GTSAM planar SLAM (Pose2 + one Point2 per tag ID + BearingRange factors) is the standard template. `ros-jazzy-apriltag-ros`, `ros-jazzy-apriltag` and `ros-jazzy-gtsam` are apt-installable **on host Jazzy** (checked; Humble in the container not checked). GTSAM 4.3.0 ships aarch64 wheels. See the ROS-distro risk in §11 | topic 2; local probe |
| Is the camera good enough? | **Borderline; it is the tightest limit.** ESP32-CAM (OV2640) over HTTP measured about 14 fps at 640×480; OV3660 users report ≲15 fps. There is no OV3660 accuracy data. Rough scaling of a 1080p ceiling-camera study down to VGA (the verifier's inference) suggests **decimetre-level** single-marker error at about 1–2 m, rising toward **about 1 m at 3 m**. Must be measured in a pilot | topic 2 + challenges |
| Do the named models exist? | **Yes.** `gpt-6-astra`, `gpt-6-sol` (plus `gpt-6-luna`), `claude-opus-5-5` and `claude-fable-5-1` all take images, call tools and have a 1M-token context | topic 3 |
| Can VLAs join the comparison? | **Manipulation VLAs no; navigation foundation models partly.** OpenVLA, π0/π0.5, SmolVLA, GR00T N1.7 and Octo have no mobile-base checkpoint and need teleop fine-tuning to adapt (about 100 demos for OpenVLA). None estimates pose. NoMaD (19 M) and ViNT (31 M), plus GNM, are RGB-only and keep image-graph topological maps: a **candidate exploration baseline**, and an **unvalidated, off-label** place-recognition baseline. **N/A** on pose and map metrics. The released NoMaD explore script only wanders at random | topic 4 + challenges |
| Can Isaac Sim host it? | **Probably, with work.** The Isaac Sim 5.1 docs list an AprilTag MDL material, a ground-truth world→odom transform publisher and Replicator randomisation. It is **not verified** that the material exists in the Spark's source build, or in 6.0. The Spark's 5.1 build is now an unsupported release; **Isaac Sim 6.0** went GA on 2026-06-08 (v6.0.1 exists). The research recommended Gazebo as the main world generator with Isaac for a photoreal subset. Isaac-only is the student's choice (NVIDIA stack) | topic 5 + challenges |

**The conditions attached to "feasible":**

1. **The map is a beacon map in a clear arena, not an occupancy map.** The car has no range
   sensor, so it cannot detect obstacles. "Unknown environment" means an unknown **tag layout**
   (and arena extent) inside a supervised, walled arena with nothing else in it. Obstacle
   avoidance is out of scope (topic 1: every LLM frontier-exploration system found used depth or
   lidar).
2. **Stop, observe, think, act.** Frontier time-to-first-token alone ranges from about 1 s to
   minutes (§9); a full decision takes longer. The robot halts and averages several frames, the
   model returns **one bounded move**, and the Pico executes it. The LLM never enters the motor
   loop.
3. **Text models get detector output, not pixels.** The best VLM scores 0.66 on relative camera
   pose versus 0.99 for LoFTR (Lost in Space, arXiv:2601.22228). Tag ID, range, bearing and
   quality come from the tag detector. Raw-image input is a separate ablation.
4. **Unique tag IDs make data association trivial** (TagSLAM: loop closure is "guaranteed once a
   tag is successfully decoded"). To give the LLM real SLAM work, the benchmark adds **aliased
   beacons**: duplicated IDs in v1, and a hidden-ID condition as a stretch.
5. **Frame the result honestly.** The research question is *which parts of landmark SLAM an LLM
   can own, and at what accuracy and cost*, not "the LLM replaces SLAM". A negative result is
   still a result, because nobody has measured this.

## 3. What "the LLM does SLAM" means: the responsibility ladder

| Level | Who does what | Role in the project |
| --- | --- | --- |
| **B0** | Dead reckoning from encoders + IMU yaw. No map | Floor baseline |
| **B1 (L0)** | Classical: GTSAM factor graph, iSAM2 online, tag IDs as landmark keys | Reference ceiling (topic 2) |
| **L1** | **LLM in-context estimator.** It reads odometry deltas and tag observations as text and writes the pose belief and beacon map itself, with no arithmetic tools. Cartesian JSON state; compact rolling state instead of the full history | The purest test. Needs a harness without ROSA's fixed rule "never perform calculations manually" (`rosa/prompts.py:125`) |
| **L2** | **LLM-orchestrated SLAM (primary design).** The LLM owns the belief, the map and every decision: which detections to trust, data association under aliasing, accepting or rejecting loop closures, where to explore, when to stop. Its numeric tools are limited to **single-observation geometry**: compose odometry, convert a range/bearing into a map point, predict a mapped tag's range/bearing, query the map. **No batch or global optimisation tool** — otherwise the tool would be doing the SLAM and L2 would collapse into L3 | Headline agent: the LLM does the SLAM *reasoning* while code does the arithmetic (PAL, SpatialClaw). **Novel and unproven**; no source shows an LLM owning data association through tool calls (topic 1 challenges) |
| **L3** | Classical B1 runs underneath. The LLM chooses exploration moves, vetoes doubtful loop closures under aliasing, and annotates the map | The level closest to existing working systems. Measures what the LLM adds when geometry is solved |
| **N** | Navigation foundation model (NoMaD / GNM / ViNT) chooses moves; B1 runs underneath only to read out the trajectory | Exploration comparison (and an off-label place-recognition baseline); N/A on pose and map error |
| **V** (ablation) | Like L2, but the model gets JPEG frames instead of detector output | Tests VLM perception |

## 4. Research questions (revised)

1. **Estimation:** at L1, L2 and L3, how close does each model come to B1, and does it beat B0?
   Measured by ATE, RPE and tag-map error on **identical replayed observations**.
2. **Association and loop closure:** with aliased beacons, how precise are LLM revisit and
   data-association decisions? Precision is weighted at least as heavily as recall, because L2
   has no robust optimiser to absorb a false loop closure.
3. **Exploration:** in closed loop, which models (LLMs and navigation models) find the most
   beacons per decision and per metre, and at what dollar and latency cost?
4. **Sim to real:** how large is each model's sim-to-real gap? Every model runs in **replay on
   real-car logs** (cheap), so the real-log comparison covers the whole roster. Closed-loop real
   runs cover 2–3 models only.

## 5. System architecture

```
ESP32-CAM ──JPEG/Wi-Fi──► bridge ─► rectify ─► tag detector ─┐
Encoders + BNO055 (fusion mode TBD; IMUPLUS proposed) ─► Pico ─► odom ─┤
                                                              ▼
              observation builder (stationary: N frames averaged per tag)
                                                              ▼
       agent harness ──► model (API or local vLLM) ──► belief report + ONE move
                                                              ▼
              validator (move set, limits, watchdog)  ─► Pico executes the bounded move
Isaac Sim twin replaces camera + Pico + car with identical topics; ground truth from world→odom
```

- **Shared move set (proposed, D4):** FORWARD 0.25 m, TURN 30° left or right, DONE. The sizes
  are chosen on the car's own terms: small enough to bound the odometry error per step and to
  keep tags in view between steps in a few-metre arena; D4 tunes them. As a side benefit they
  match Uni-NaVid's training actions (topic 4). The primary navigation models (NoMaD/GNM/ViNT)
  are **out of distribution** under stop-and-go moves whatever the step size; their adapter is
  untested.
- **Closed loop vs replay:** the prompt targets **closed loop**, where the model chooses the
  move. In replay the harness supplies the move that was executed and the model reports its
  belief only. A MODE line in each observation switches that part of the Business Logic and
  Format (D1, D10).
- **Per-step belief report:** every decision emits the model's pose estimate (x, y, θ in the
  start-pose frame) and its beacon map, so ATE and map error can be scored at every step (D8).
- **Stateless per-step calls (recommended):** each step sends the model its own last belief and
  map plus the new observation, in a fresh conversation. This is identical for every provider,
  bounds the context, and sidesteps the Opus 5.5 / Fable 5.1 rule that edits before a thinking
  block are rejected (topic 3) (D10).
- **One prompt for every model:** the `RobotSystemPrompts` text is model-agnostic. Only the
  CONTEXT/tool section changes between ladder levels L1, L2 and L3.

## 6. Arena and beacons

- **Real:** a clear, walled arena (size TBD in D3) with soft walls (cardboard), supervised, and
  motor-disable at hand. Tags are mounted vertically on the walls at camera height, sized ≥ 15–20
  cm (measured at the black/white border), and dense enough that 2–3 are usually in view.
  Tape-measured tag poses are the ground-truth map. No people, pets or personal items in frame
  (see the data-governance risk).
- **Tags on walls double as a wall-distance cue.** A tag straight ahead at range r means a wall
  about r away. This makes a guardrail ("no FORWARD when a tag dead ahead is closer than X")
  possible without a range sensor. My inference, to be tested (D6).
- **Sim:** Isaac Sim arenas generated from seeds (extent, tag poses, IDs, aliasing). The same car
  twin, a camera matched to the calibrated OV3660, and **no** range sensor, so the simulator
  never gives the agent more than the real car has. Detections are degraded with the real noise
  **measured in the W2 pilot**; until then a placeholder noise model is used and those results
  must be re-run.
- **Conditions:** unique IDs (easy association); duplicated IDs (ambiguous, v1); hidden IDs (the
  detector reports "a tag" plus geometry, `id` = null; stretch).

## 7. Model roster (verified 2026-09-27, topic 3)

All GPT-6 models need the **Responses API** to call tools while reasoning (Chat Completions
supports tools only at effort `none`). They accept `temperature` only at effort `none`.

| Tier | Model (API ID) | Price in/out per MTok | Notes that shape the harness |
| --- | --- | --- | --- |
| Frontier | GPT-6 Astra (`gpt-6-astra`) | $10 / $50 | Released 2026-09-03. Lowest effort is `low` (no `none`); misalignment monitoring can stop a conversation |
| Frontier | GPT-6 Sol (`gpt-6-sol`) | $2 / $10 | Released 2026-09-22. Effort `none`…`max`. The Sep 25 image-encoding fix invalidates vision results from before it |
| Frontier (cheap) | GPT-6 Luna (`gpt-6-luna`) | $0.10 / $0.50 | Low-cost OpenAI tier; same Sep 25 fix |
| Frontier | Claude Opus 5.5 (`claude-opus-5-5`) | $4 / $20 | Released 2026-09-22. Thinking always on; forced `tool_choice` rejected; no non-default sampling |
| Frontier | Claude Fable 5.1 (`claude-fable-5-1`) | $10 / $50 | Released 2026-09-01. "Slower"; requires 30-day data retention; no non-default sampling |
| Local (spark-2a60) | Qwen3.5-35B-A3B | free | Already serves here via vLLM (AGENTS.md §7.4); MoE; vision; `qwen3_coder` parser |
| Local (candidate) | Qwen3.6-35B-A3B | free | Community figure on DGX Spark: ~21–30 tok/s (FP8, vLLM). The cached FP8 snapshot was recorded as an empty stub; re-check |
| Local (candidate) | Qwen3.8-27B | free | Dense; `qwen3_xml` parser; ~24.5 tok/s vLLM (community) |
| Local (candidate) | Gemma-4-26B-A4B-it | free | Cached; `gemma4` parser; ~52 tok/s NVFP4 (community) |
| Local (candidates) | Meta Muse Glimmer 30B; NVIDIA Cosmos-Reason2; gpt-oss-120b (text-only) | free | vLLM recipes list Muse Glimmer as verified on DGX Spark (not downloaded or tested on spark-2a60). Cosmos-Reason2 is NVIDIA's robotics VLM (superseded by Cosmos 3). gpt-oss serves the detector-output arm |
| Navigation model | NoMaD (19 M), ViNT (31 M), GNM | free | RGB-only; trained with wide-angle cameras (mismatch risk); official stack is ROS 1; ROS 2 via a community port (aarch64 unverified) |
| Navigation model (optional) | Uni-NaVid 7B; NVIDIA X-Mobility | free | Uni-NaVid is instruction-following VLN, not exploration; aarch64 unproven. X-Mobility is Isaac-trained differential-drive but needs goal poses from a localizer; its demo targets Isaac Sim 4.2 / Humble (unverified here) |
| Excluded from the leaderboard | OpenVLA, π0/π0.5, SmolVLA, GR00T N1.7, Octo | — | Manipulation/humanoid checkpoints only; need teleop fine-tuning; no pose output. Optional stretch: fine-tune one as an end-to-end explorer, clearly labelled |

Local reasoning models run with thinking **off or low**: at 20–50 tok/s, a 1–2k-token trace
costs 20–100 s per step.

## 8. Benchmark design

**Two modes, because exploration confounds estimation:**

- **Replay (open loop):** record observation logs once, in sim and on the real car, and feed the
  identical sequence to every model and level. This isolates estimation (RQ1, RQ2), is cheap to
  repeat, and puts the whole roster on real data (RQ4).
- **Closed loop:** the model also chooses moves (RQ3). A model that explores badly sees fewer
  tags, so its ATE is not comparable with replay numbers.

**Tracks and metrics:**

| Track | Metric |
| --- | --- |
| T1 estimation (replay) | ATE-RMSE (evo, `--project_to_plane xy` + Umeyama, or a custom SE(2) fit), RPE per 1 m, tag-map RMSE after alignment **gated by tag-ID precision/recall** (Kümmerle 2009 prefers trajectory metrics for EKF-type methods) |
| T2 association / loop closure (replay, aliased) | Revisit precision and recall (precision weighted), data-association error rate |
| T3 exploration (closed loop) | Share of tags found vs decisions, metres and wall-clock; time to 90 % and 99 % of tags |
| T4 post-map navigation | "Go to tag k" / "return to start" using the agent's own map: success and SPL (Anderson et al. 2018: DONE action, threshold 2× body width) |
| All | Tokens, dollars per episode, seconds per decision, tool turns per decision, invalid tool calls, format violations, refusals |

**Baselines:** B0; B1; a random explorer; a frontier-on-beacon-graph heuristic; an oracle-pose
condition that isolates exploration from localisation.

**Ground truth:** exact in sim (world→odom transform tree). On the real car, tape-measured tag
poses plus an overhead camera tracking a roof tag from a reserved ID range. That camera's
accuracy must itself be measured; the "~1 cm" in the literature is a static-tag figure (topic
5 challenges).

**Statistics (topic 5):**

- **Design:** paired on identical seeds. K ≥ 3 repeats per seed, because temperature 0 is not
  deterministic and several frontier models reject sampling settings. Dev seeds (for prompt
  tuning) are kept separate from held-out test seeds.
- **Pre-registration:** one primary endpoint per mode.
- **Continuous metrics:** Friedman, then pairwise Wilcoxon with Holm (Benavoli 2016; request
  `holm` explicitly in statsmodels).
- **Binary outcomes:** exact McNemar, or Cochran's Q. Report paired, world-clustered bootstrap
  confidence intervals and IQM.
- **Episode counts:** an exact paired test's smallest p is 2/2ⁿ.
  - With 15 Holm-corrected pairwise tests (6 models), the first threshold is 0.05/15 ≈ 0.0033,
    so even a model that wins every episode needs **≥ 10 paired episodes**.
  - That is a **lower bound**, not a sufficient n. McNemar's floor depends on the number of
    discordant pairs, and SciPy's default drops ties.
  - Set n from pilot variance with a power analysis.
  - Closed-loop real runs get 2–3 pre-registered comparisons. At 3 tests, 7 all-win episodes
    clear the threshold, since 2/2⁷ ≈ 0.0156 < 0.0167.
- **Sim to real:** a per-model sim-to-real gap on real-log replay. MMRV/Pearson ranking
  agreement is meaningful only when enough models run on real data; with 2–3 it has little
  resolving power.
- **Logging:** exact model IDs, dates, prompt hash and tool-schema version on every call.

## 9. Cost and latency (estimate — assumptions stated)

**Per model call.** Assume 5k input + 2k output tokens per model call (the researcher's
single-call example). At the verified prices:

| Model | Cost per call |
| --- | --- |
| Astra | ≈ $0.15 |
| Fable 5.1 | ≈ $0.15 |
| Opus 5.5 | ≈ $0.06 |
| Sol | ≈ $0.03 |
| Luna | ≈ $0.0015 |

**Per decision.** An L2 decision is **several calls** (observe, numeric tools, map write, move),
each re-sending its context, so multiply by the tool turns per decision. That number is unknown
until the harness exists; 3–5 is plausible.

**Example sweep, at one call per decision (a floor).** 60 decisions × 30 held-out seeds × 3
repeats = 5,400 calls per model, which is roughly:

- **$810 each for Astra and Fable;**
- **$324 for Opus;**
- **$162 for Sol;**
- **$8 for Luna.**

Replay multiplies this again by levels × conditions × worlds.

**Cost is a first-class design constraint.** Run the full sweep on local models plus the
cheaper frontier tiers, and give Astra and Fable a smaller pre-registered subset. Caching the
system prompt cuts input cost, but output (reasoning) dominates. **Decision needed:** an
explicit dollar budget before the roster tiers are fixed.

**Latency.** Artificial Analysis time-to-first-token is a **loose proxy**: it is measured on
their own text prompts, not image + tool prompts, and some Opus figures carry a fallback label.

| Model and effort | Time to first token |
| --- | --- |
| Sol, non-reasoning | ~1.1 s |
| Luna, low | ~2.2 s |
| Opus 5.5, low | ~6 s |
| Fable 5.1, low | ~6.5 s |
| Astra, xhigh | ~98 s |

Per-decision latency must be measured in the harness. Compare models at matched effort tiers,
not at each one's default.

## 10. Workstreams (the major tasks)

| # | Workstream | Key steps |
| --- | --- | --- |
| W1 | **URDF + Isaac Sim twin** (own session; gates all simulation) | Measure the car: wheel diameter, track width, caster, mass, camera and IMU mounts (camera stood upright first). Write the URDF, import it, add a differential-drive controller, match the camera to the calibration, no range sensors. **Decide Isaac Sim 6.0 vs 5.1** on aarch64. Check that AprilTag.mdl and the tag36h11 mosaic exist in the chosen build. Ground-truth TF. Seeded arena generator (Replicator, or evaluate Arena-Rosnav's `arena-isaac`) |
| W0 | **One ROS 2 graph** (decide early) | Pick one distro for the whole project graph. Today the Pico's micro-ROS agent is the **Humble** image and its node was seen only inside `rosa-ros2`; Isaac odometry does not reach host Jazzy even UDP-only (AGENTS.md §7.4); `apriltag_ros` and GTSAM were checked for host Jazzy only. Either move the agent and the Isaac bridge onto Jazzy and prove host Jazzy sees them, or check the packages for Humble |
| W2 | Camera and tag pipeline | Stand the camera up. ESP32-CAM project firmware (JPEG). Timestamped bridge to `CompressedImage`. Checkerboard calibration. Tag detector. **Pilot: range and bearing error vs distance**, which becomes the sim noise model |
| W3 | Pico firmware | Motors (STBY high), encoders, BNO055 (measure motor magnetic interference, then choose the fusion mode; IMUPLUS proposed), bounded-move executor, watchdog. UMBmark odometry calibration |
| W4 | Classical baselines | B0; B1 in Python GTSAM (aarch64 wheel) |
| W5 | Agent harness | Provider abstraction: OpenAI Responses API; Anthropic Messages; vLLM OpenAI-compatible with the right tool parser per model. Stateless steps; validator; full logging. **Decide ROSA's role**: `rosa-ros2` pins LangChain 0.3.x, lacks `langchain-anthropic`, and its fixed prompts demand math tools. Under vLLM-served Qwen, ROSA also needs the one-system-message merge in `discussions/module2/llm_backends.py` and one `ROSA()` per process (AGENTS.md §7.4 gotcha 5). Whether ROSA can drive GPT-6 / Opus 5.5 with their 2026 API features is **unverified** |
| W6 | Navigation-model arm | NoMaD/GNM via the ROS 2 community port. Adapter to the shared move set (untested; a distribution shift for these fixed-rate models). Online graph building during exploration is unverified (the released explore script is random). aarch64 check |
| W7 | Benchmark and analysis | Seeds, replay logs, evo metrics, statistics, pre-registration |
| W8 | Real arena | Walls, printed and measured tags, overhead ground-truth camera |

**Suggested order:**

1. The **W2 camera pilot** (stand the camera up, flash it, calibrate, measure the range and
   bearing error) together with **W0** and **W1 + W5 + W4**. The sim noise model is then
   measured rather than invented, and together this gives a simulated L2 agent with 2–3 models
   against B1: the minimum viable result.
2. Then W3 + W8 for closed-loop real runs.
3. Then the full roster.

**Cut line if time runs short:** sim-only L2 + B1 with 2–3 models, plus real-log replay.

## 11. Risks and open questions

1. **API cost** (§9). Tier the roster, and set a budget.
2. **Camera accuracy and latency.** Decimetre error or worse beyond about 1–2 m is likely, and
   the camera shares Wi-Fi with the Pico's micro-ROS link. Mitigations: stop-and-look, tag size
   and density, the pilot.
3. **No range sensor.** Collisions are possible in the real arena. Mitigations: a clear walled
   arena, soft walls, supervision, the tag-range guardrail (D6).
4. **Isaac Sim on aarch64.** 5.1 is unsupported and 6.0 is untested here. The AprilTag material
   is unverified in the build. Bridge DDS quirks (AGENTS.md §7.4). Processes hang on shutdown and
   need a wrapper. No live viewport.
5. **The ROS 2 distro split** (W0): Humble agent, Jazzy host, Isaac bridge.
6. **Harness compatibility** with the 2026 frontier APIs (W5) is unverified.
7. **Real-world ground-truth accuracy** is unmeasured.
8. **Navigation models:**
   - camera mismatch (they expect a wide-angle lens);
   - ROS 1 upstream; aarch64 unproven;
   - an untested move adapter;
   - place recognition is off-label.
9. **Data governance.** Decide which arms may send what to which provider:
   - the V ablation sends raw JPEGs;
   - Fable 5.1 requires 30-day retention;
   - Astra runs misalignment monitoring.

   Keep people and personal items out of the arena's field of view. Text arms send detector
   output only.
10. **Course fit — RESOLVED 2026-10-05:** individual project, no Course Project Description
    exists, the instructor accepted the direction change, final deadline 2026-12-13; no dated
    plan is kept (see `CONTEXT.md` and `plan/`). Original text kept below.
    **Course fit — blocking for the project, not for the assignment.** The syllabus describes a
    *team* project with Customer/Seller roles, where 60 % of the grade is preparation and
    participation (AGENTS.md §5). `CONTEXT.md` records an individual project. The Course
    Project Description is authoritative but not in the repo. Confirm the team and role
    structure, and whether a change from the 2026-09-14 proposal needs the instructor's
    acceptance, before committing to this scope. Then add dated milestones working back from the
    project week (the course's next-to-last week), using the cut line above.
11. **Gazebo in the course.** The syllabus teaches Gazebo, so a later graded assignment may
    require it. That work stays separate; the project uses Isaac Sim (the student's choice,
    2026-09-27, for NVIDIA-stack career value).

## 12. What this changes now

- **Revised D1**, the decision for the Module 4 prompt assignment: the prompt describes the **L2
  agent**, consistent with the design of both Isaac Sim and the car, and targets closed loop.
  Details and alternatives are in `assignments/assignment4/system-prompt/PLAN.md` §4. **Pending
  Xiaohui's approval.** Approving D1 settles the assignment prompt only; it is not approval of
  the whole project redirection (§11 item 10).
- D2–D10 are redefined for this direction in the same PLAN section.
- `CONTEXT.md` points here; the 2026-09-14 known-map design is kept there as history.

## Generative-AI disclosure

Claude Opus 5.5 via Claude Code ran the research workflow (five web researchers and five
adversarial verifiers), checked local facts on the Spark, drafted this document, and revised it
after a three-lens adversarial review. The direction — LLM as SLAM with tag beacons, Isaac Sim,
the model roster, a sim and real benchmark — is Xiaohui Chen's. Cost figures are estimates from
verified list prices and stated assumptions.
