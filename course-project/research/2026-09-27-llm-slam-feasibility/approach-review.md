# Adversarial review of the approach documents — 2026-09-27

Scope: `course-project/APPROACH-LLM-SLAM.md`, the new sections of `course-project/CONTEXT.md`,
`assignments/assignment4/system-prompt/PLAN.md` §4, and this folder's README. Workflow
`review-llm-slam-approach` (run `wf_8d6747af-61c`, Claude Opus 5.5): three independent
reviewers, each with its own lens (source fidelity, repo/hardware fidelity, reasoning and D1).

**Result:** 36 raw findings. The duplicate pairs 1/23, 2/22, 5/34, 11/13, 15/36, 16/32 and 18/30
each count once, leaving **29 distinct findings**. The main session re-checked each one against
the evidence it cites, and **all 29 were confirmed; none was rejected**. All were fixed:

| Findings | Disposition |
| --- | --- |
| 1/23 "L2 most likely to work" | Removed. L2 is now justified as the project idea's level (LLM reasoning, code arithmetic), novel and unproven; L3 is named as closest to existing systems. The ROSA argument is demoted to secondary and made conditional on D10 |
| 2/22 Sandfuchs used as counter-evidence | Oracle-pose caveat added; the prior is described as "uninformed, not favourable" |
| 3 MMRV with 2–3 real models | RQ4 reworded to per-model sim-to-real gaps, with the whole roster run on real-log replay |
| 4 Navigation-model claims | Place recognition is now "unvalidated, off-label"; the move adapter is untested; the released explore script is random; sizes limited to the sourced ones |
| 5/34 ≥10 episodes | The 15-test premise is stated; called a lower bound; McNemar and tie caveats added; n comes from a power analysis |
| 6 TTFT vs decision latency | Reworded as a loose TTFT proxy; per-decision latency must be measured |
| 7 Camera error scaling | Restated as the verifier's rough inference: decimetre at 1–2 m, about 1 m at 3 m |
| 8 Responses API | Now stated for all GPT-6 models, with temperature allowed only at effort `none` |
| 9 "~100 demos" | Attributed to OpenVLA only |
| 10 Qwen speeds | Speeds attributed to Qwen3.6-FP8 only; Qwen3.5 cited from the local run; the stub caveat added |
| 11/13 Agent container state | Recorded as a dated 2026-09-27 `docker ps` observation; `pico-bringup.md` and AGENTS.md §7.4 updated |
| 12 Humble/Jazzy split | New workstream W0 (one ROS 2 graph) and risk 5; package checks qualified as host Jazzy only |
| 14 VSYS/USB current state | Last-known state and "not recorded, check" added |
| 15/36 Stale CONTEXT uncertainties | History heading; a note marks resolved and partly resolved items |
| 16/32 IMUPLUS and "true in both" | IMUPLUS is proposed, not fact; the camera is forward once stood up; 1a reads "consistent with the design of both", with capabilities labelled as design values |
| 17 "No camera firmware" | Reworded: no project firmware flashed; factory state unchecked |
| 18/30 Isaac Sim row | MDL availability in the Spark build and in 6.0 unverified; research recommended Gazebo; Isaac-only is the student's choice |
| 19 ROSA/vLLM gotcha | AGENTS.md §7.4 gotcha 5 and `llm_backends.py` cited in W5 |
| 20 Muse Glimmer "on the Spark" | Reworded: listed by vLLM recipes, not tested on spark-2a60 |
| 21 Verdict overclaimed | Now "yes, conditionally": the novel core is the contribution; "a one-day search found no report"; gating pilots listed |
| 24 L2 tool granularity | L2 tools limited to single-observation geometry; no batch or global optimisation (in APPROACH §3 and D1 1b) |
| 25 Replay vs closed loop | New D1 1d: the prompt targets closed loop; in replay a MODE line switches the relevant sections |
| 26 Work order | The W2 camera pilot moved to the first step; placeholder noise flagged for re-run |
| 27 Cost undercount | Cost is priced per call with a tool-turn multiplier; replay multiplier noted; an explicit budget decision requested |
| 28 Course fit | Marked blocking for the project (not the assignment); milestones and a cut line required |
| 29 Status wording | "Chosen, contingent on feasibility" used consistently; D1 approval separated from approval of the project redirection |
| 31 Hidden-ID vs id field | `id` nullable in D1 and D5; hidden-ID is a stretch |
| 33 Move-set justification | Justified on the car's terms; the Uni-NaVid match is a side benefit; NoMaD/GNM/ViNT flagged as out of distribution |
| 35 Data governance | Added to risks (item 9) and D10 |

Raw findings, with evidence, follow.

---

######## LENS source-fidelity — 11 findings

[1] (major) assignments/assignment4/system-prompt/PLAN.md
  QUOTE: 1. It is the project's headline design and the one most likely to work.
  PROBLEM: The research does not show that L2 is the most likely level to work. It points the other way. Every working system the research found runs a classical SLAM or MCL stack underneath and uses the LLM only on top, which is the L3 pattern. The topic-1 verifier says outright that the L2 pattern (the LLM running the estimator by calling tools) is "a new design, not an established pattern". APPROACH §3 itself calls L2 "Novel: no source shows an LLM owning data association through tool calls". So "most likely to work" is an unsupported inference, and it is being used as the first reason for the D1 decision.
  EVIDENCE: topic1-llm-as-slam-literature.md:72 CHALLENGES: "none of those systems has the LLM run the SLAM process by calling numeric tools. In each one a classical SLAM or MCL stack runs on its own underneath ... 'LLM orchestrates the estimator' is therefore a new design, not an established pattern." topic4-vla-nav-foundation-models.md:76: "The literature (VLM-GLoc, GemNav, ViNT) consistently uses VLMs, VLAs and navigation models around a classical pose estimator, not in place of one."
  FIX: Drop "the one most likely to work". Say instead that L2 is the headline design and is novel and unproven, and that L3 (the LLM on top of classical B1) is the level closest to existing working systems. Justify choosing L2 on scope or novelty grounds, not on likelihood of success.

[2] (major) course-project/APPROACH-LLM-SLAM.md
  QUOTE: But the verifier notes that reasoning models (GPT-5, GPT-OSS-120B) reached 100 % on sequential grid navigation where instruct models failed (Sandfuchs 2026, arXiv:2604.09604). Treat it as an open question, not an expected failure
  PROBLEM: The row presents Sandfuchs 2026 as counter-evidence to the prediction that an in-context pose estimator will drift. But the research records that Sandfuchs gave the agent its pose (oracle localization) and explicitly does not test SLAM. So the 100 % result says nothing about integrating odometry or estimating pose, which is exactly what L1 would do. The doc drops this caveat and uses the result to soften the central feasibility question. "Open question" is still the right conclusion, because no paper measures this. The right support for it is that absence, not Sandfuchs.
  EVIDENCE: topic1-llm-as-slam-literature.md:18 [confirmed]: "The agent's pose is given to it (oracle localization), so the benchmark explicitly does not test SLAM." topic1 SUMMARY: "the one text-only LLM exploration benchmark I found gives the model its position for free ('This is not SLAM: the uncertainty is in the map, not in pose')".
  FIX: Add "(with the pose given to the model, so not a test of estimation)" after the Sandfuchs citation. Rest "unknown" mainly on topic1 UNKNOWNS: no paper measures ATE for an in-context LLM estimator.

[3] (major) course-project/APPROACH-LLM-SLAM.md
  QUOTE: - **Sim to real:** MMRV + Pearson for sim-real agreement.
  PROBLEM: The doc adopts MMRV for sim-to-real agreement (RQ4: "do the model rankings from Isaac Sim hold on the real car?") without acknowledging the verifier's challenge. The verifier says MMRV needs several models evaluated in real episodes, and that with 2–3 real models it has very little resolving power. Two lines earlier, the same doc limits the real car to 2–3 pre-registered comparisons. As designed, RQ4 is nearly unanswerable, and the doc does not say so.
  EVIDENCE: topic5-benchmark-and-sim.md:82 CHALLENGES: "MMRV in particular needs several models evaluated in real episodes to be meaningful; with 2–3 real models it has very little resolving power." APPROACH-LLM-SLAM.md:181-182: "The real car therefore gets 2–3 pre-registered comparisons".
  FIX: Acknowledge the limit on MMRV. Either run more models on the real car (for example in replay with real logs) or reword RQ4 to cover per-model sim-to-real gaps rather than ranking agreement.

[4] (major) course-project/APPROACH-LLM-SLAM.md
  QUOTE: NoMaD/ViNT/GNM (19–31 M params, RGB only) explore and keep image-graph topological maps: valid for exploration and place recognition, **N/A** on pose and map metrics
  PROBLEM: "Valid for ... place recognition" adopts a researcher inference that the verifier challenged. Using the temporal-distance head as a loop-closure detector is off-label, and no source evaluates it with precision/recall. The verifier also challenged the plan to quantize their waypoints into stop-and-go FORWARD/TURN moves: it is an untested adapter and a distribution shift for these fixed-rate models. And the released NoMaD explore script only wanders at random, so whether it builds a graph online during exploration is listed as unknown. None of these points appears in §2, §7 or W6. Also, 19–31 M is sourced for NoMaD (19 M) and ViNT (31 M) only; the research gives no GNM parameter count.
  EVIDENCE: topic4-vla-nav-foundation-models.md:73: "Using the NoMaD/ViNT/GNM temporal-distance head as a loop-closure detector is off-label ... No source evaluates it as a place-recognition detector with precision/recall. Present it as an unvalidated baseline". Line 75: "Quantizing their waypoints into discrete FORWARD/TURN moves ... is an untested adapter, so 'fair comparison' is asserted, not shown." Line 32: "its exploration script only lets NoMaD wander at random". UNKNOWNS line 83: "Whether the released NoMaD code can build a topological graph online during frontier exploration".
  FIX: Change the wording to "candidate exploration baseline; place recognition only as an unvalidated, off-label baseline". Add the untested move-set adapter and the random-only released explore script to the risks (§11 item 7) and to W6. Give only the sourced sizes (NoMaD 19 M, ViNT 31 M).

[5] (minor) course-project/APPROACH-LLM-SLAM.md
  QUOTE: an exact paired test's smallest p is 2/2ⁿ, so a Holm-corrected pairwise comparison needs **≥ 10 paired episodes** even when one model wins every time.
  PROBLEM: The ≥ 10 figure comes from a specific premise that the doc dropped: 6 models compared pairwise, which is 15 tests, so Holm's first threshold is 0.05/15 ≈ 0.0033. It is not a general property of a Holm-corrected comparison. For the 2–3 real-car comparisons the doc then prescribes, the threshold is 0.05/3 ≈ 0.0167, and 2/2^7 = 0.0156 already clears it. So the stated rule does not follow for the real-car plan. The doc also leaves out the verifier's caveats: the ≥ 10 figure is a lower bound, not a sufficient number; McNemar's floor depends on the number of discordant pairs, not on n; and SciPy's default zero_method drops ties.
  EVIDENCE: topic5-benchmark-and-sim.md:71: "Comparing 6 models pairwise means 15 tests, so Holm's first threshold is 0.05/15 ≈ 0.0033, which needs at least 10 paired episodes". Line 83 CHALLENGES: "For McNemar, the floor depends on the number of DISCORDANT pairs, not on n ... The '≥10 paired episodes' rule is therefore a lower bound, not a sufficient number."
  FIX: State the premise ("with 15 pairwise tests among 6 models"). Note that ≥ 10 is a lower bound in the ideal all-wins case, that McNemar depends on discordant pairs, and that pilot variance plus a power analysis set the real n.

[6] (minor) course-project/APPROACH-LLM-SLAM.md
  QUOTE: Frontier latency ranges from about 1 s to minutes per decision (§9).
  PROBLEM: The numbers in §9 are Artificial Analysis time-to-first-token (TTFT) figures, not per-decision latency. TTFT excludes generating the output. At the doc's own assumption of 2k output tokens and about 80 tok/s, output adds roughly 25 s, so even Sol non-reasoning is not about 1 s per decision. The verifier also warned that AA's TTFT is measured on AA's own text prompts, not image+tool prompts, and is "only a loose proxy". In addition, AA's Opus 5.5 figures carry a 'Default Fallback' label. §9 presents the figures as "Measured time-to-first-token" without either caveat.
  EVIDENCE: topic3-models-availability.md:56 CHALLENGES: "AA's TTFT includes thinking time on AA's own text prompts, not image+tool prompts, so it is only a loose proxy." Line 59: "Artificial Analysis's own Opus 5.5 numbers carry a 'Default Fallback' label". Line 17: Opus 5.5 low 6.1 s TTFT and 79 tok/s.
  FIX: Say "time-to-first-token ranges from about 1 s to minutes", and add "a loose proxy; per-decision latency must be measured in the harness".

[7] (minor) course-project/APPROACH-LLM-SLAM.md
  QUOTE: A 1080p webcam scaled down to VGA suggests **decimetre-level** single-tag range error beyond about 1 m.
  PROBLEM: This is the verifier's own rough pixel-scaling inference, not a sourced figure. It is also understated. The verifier's scaling maps Hinderer's 3 m single-marker case (30–45 cm) to roughly 1 m at VGA, which is metre-level at 3 m, not decimetre-level. Hinderer's figures are planar localization RMSE from a camera on the ceiling looking down at the markers, not range error. (The verifier's own 1.33 m to 0.45 m figure is also arithmetically inconsistent with a 3x per-axis scaling, which would give 9–15 cm.)
  EVIDENCE: topic2-fiducial-slam-baseline.md:57 CHALLENGES: "Hinderer uses 1080p ArUco looking straight down from the ceiling ... A rough pixel-scaling INFERENCE ... the 3 m case (30–45 cm) to roughly 1 m, if the fields of view are similar."
  FIX: Say "a rough scaling (verifier inference) of a 1080p ceiling-camera study suggests decimetre-level planar error at about 1–2 m, rising toward about 1 m at 3 m", and keep "must be measured in a pilot".

[8] (minor) course-project/APPROACH-LLM-SLAM.md
  QUOTE: | Frontier | GPT-6 Astra (`gpt-6-astra`) | $10 / $50 | Released 2026-09-03. Lowest effort is `low`; no custom temperature; tools with reasoning need the Responses API;
  PROBLEM: The roster lists the Responses-API requirement only for Astra. The verifier flagged exactly this as incomplete: Sol and Luna also support function calling in Chat Completions only at reasoning_effort none. The Sol and Luna rows omit it, and so does the related sampling point: Sol and Luna accept temperature only at effort none.
  EVIDENCE: topic3-models-availability.md:58 CHALLENGES "HARNESS (incomplete): the Responses-API requirement is not Astra-only. Sol and Luna 'support function calling in Chat Completions only with `reasoning_effort: "none"`. Use Responses for reasoning with tools.'" Line 57: Sol and Luna at effort none accept temperature.
  FIX: Add "tools with reasoning need the Responses API; temperature allowed only at effort none" to the Sol and Luna rows, or state it once for all GPT-6 models.

[9] (minor) course-project/APPROACH-LLM-SLAM.md
  QUOTE: OpenVLA, π0/π0.5, SmolVLA, GR00T N1.7 and Octo have no mobile-base checkpoint and need about 100 teleop demos to adapt.
  PROBLEM: The "about 100 demos" figure is sourced only for OpenVLA, from its README. The doc applies it to all five models. The research gives no demo count for π0/π0.5, SmolVLA, GR00T or Octo.
  EVIDENCE: topic4-vla-nav-foundation-models.md:59 MISSED: "OpenVLA's README says 'OpenVLA typically requires fine-tuning on a small demonstration dataset (~100 demos) from your target domain robot'." No equivalent figure for the others appears in the file.
  FIX: Say "need teleop fine-tuning (about 100 demos for OpenVLA)".

[10] (minor) course-project/APPROACH-LLM-SLAM.md
  QUOTE: | Local (Spark) | Qwen3.6-35B-A3B / Qwen3.5-35B-A3B | free | MoE; vision; `qwen3_coder` parser; ~21–30 tok/s on Spark (community) |
  PROBLEM: The 21–30 tok/s community figure was measured only for Qwen3.6-35B-A3B-FP8 on vLLM. It is presented as applying to Qwen3.5-35B-A3B too. The verifier also notes that Qwen3.5-35B-A3B is not Spark-verified in the vLLM recipes, while Qwen3.6 and Qwen3.8 are.
  EVIDENCE: topic3-models-availability.md:34: "measured Qwen3.6-35B-A3B-FP8 on DGX Spark with vLLM at ~28–30 tok/s single-user steady state (21.0 tok/s at c=1)". Line 61: "Qwen3.5-35B-A3B is not Spark-verified in vLLM recipes; Qwen3.6-35B-A3B and Qwen3.8-27B are."
  FIX: Attribute the speed to Qwen3.6-35B-A3B-FP8 only. For Qwen3.5, cite the local AGENTS.md §7.4 run (it serves locally) rather than the community figure.

[11] (minor) course-project/CONTEXT.md
  QUOTE: ### Hardware state (copied from `reference/hardware/`, as of 2026-09-23) ... `pico-micro-ros-agent` (running: "Up 4 days" on 2026-09-27)
  PROBLEM: This is outside the research lens, but it is an internal inconsistency. The heading says the section is copied from reference/hardware as of 2026-09-23. But reference/hardware/pico-bringup.md records the agent container as stopped at the end of that session, and this line reports a 2026-09-27 observation that the cited source does not contain. It may be a genuine later check on the Spark; I cannot verify the Spark state from here.
  EVIDENCE: reference/hardware/pico-bringup.md:34: "the micro-ROS agent container was **stopped, not removed** (`pico-micro-ros-agent`)".
  FIX: Mark the container line as a separate observation dated 2026-09-27 (source: a docker ps on the Spark), or update pico-bringup.md so the cited source matches.

  checked_ok: Cost table in APPROACH §9 recomputed at 5k input + 2k output tokens per decision: Astra $0.05+$0.10=$0.15; Fable $0.15; ; Model IDs, prices and release dates match topic 3: gpt-6-astra $10/$50 (2026-09-03), gpt-6-sol $2/$10 (2026-09-22), gpt-; Opus 5.5 has thinking always on, rejects forced tool_choice and rejects non-default sampling (migration guide); Fable 5.; TTFT figures match topic 3: Sol non-reasoning 1.10 s, Luna low 2.16 s, Opus low 6.1 s, Fable low 6.5 s, Astra xhigh 98 s; The local decode arithmetic '20–100 s' is the corrected figure from the verifier (the researcher had written 40–100 s). ; arXiv IDs and attributions are correct: Syarubany 2601.00555 (ORB-SLAM3 pose, qualitative only, AprilTag anchors); Sandf; The TagSLAM quote 'guaranteed once a tag is successfully decoded' appears in the topic 2 summary; GTSAM Pose2/Point2/Bea; Isaac Sim: the AprilTag MDL material, the world→odom Raw Transform Tree and Replicator are confirmed in the 5.1 docs; th; Statistics citations are correctly attributed: Benavoli 2016 for Friedman then pairwise Wilcoxon + Holm; statsmodels def; The shared move set of FORWARD 0.25 m and TURN 30° matches Uni-NaVid's training actions, per the topic 4 verifier.; The research README verdict counts match the topic files exactly: 52/46/4/2, 37/33/4, 32/29/2/1, 36/32/4, 58/49/7/1/1.; The CONTEXT hardware rail voltages (5.03 / 3.3 / 6.67 V), GPIO map, 0x28 I2C address, STBY, VSYS interlock and UDP 8888 

######## LENS repo-hardware-fidelity — 9 findings

[12] (major) course-project/APPROACH-LLM-SLAM.md
  QUOTE: `ros-jazzy-apriltag-ros`, `ros-jazzy-apriltag` and `ros-jazzy-gtsam` are apt-installable on the Spark (checked).
  PROBLEM: The approach treats host-Jazzy package availability as showing the Spark can run the tag pipeline, and §5 draws one ROS graph (apriltag_ros + Pico odom + Isaac twin with "identical topics"). The repo records that the two live topic sources do not reach host Jazzy. The Pico's micro-ROS agent is the Humble image, and its node was seen only inside `rosa-ros2` (Humble). Isaac Sim odom does not arrive on host Jazzy even with UDP-only DDS. The Humble/Jazzy split is never mentioned. W1 says only "Resolve the ROS 2 bridge DDS path", which covers Isaac but not the Pico, and nobody checked whether AprilTag or GTSAM packages exist for the Humble container.
  EVIDENCE: reference/hardware/pico-bringup.md:51-52 (`microros/micro-ros-agent:humble`), :57 "Check the graph inside `rosa-ros2`, not on host Jazzy. Host Jazzy was not shown to see this node."; AGENTS.md §7.4 line ~911 "Host Jazzy 2.14.6 still does not receive Isaac odom even UDP-only (version drift), but the container is the target."; README local facts list only "apt candidates for host Jazzy"
  FIX: Add a risk and a W1/W2 step: pick one ROS distro for the project graph. Either move the Pico agent and Isaac bridge onto Jazzy and show that host Jazzy sees them, or check AprilTag/GTSAM availability for Humble in the container. Qualify the §2 row to say the packages were checked for host Jazzy only.

[13] (minor) course-project/CONTEXT.md
  QUOTE: `pico-micro-ros-agent` (running: "Up 4 days" on 2026-09-27)
  PROBLEM: This contradicts the hardware records. They say the agent container was stopped, not removed, at the end of the 2026-09-23 session. The section heading says it was "copied from `reference/hardware/`, as of 2026-09-23", but this line is a 2026-09-27 live observation that appears in no reference file and not in the research README's local-facts list. If it is true, pico-bringup.md and AGENTS.md §7.4 are stale and were not updated. It also implies the Pico/USB/VSYS state may differ from the record, but that state is not given (see next finding). I cannot confirm the observation without ssh.
  EVIDENCE: reference/hardware/pico-bringup.md:34 "the micro-ROS agent container was **stopped, not removed** (`pico-micro-ros-agent`)"; AGENTS.md §7.4 "It was stopped, not removed, on 2026-09-23."; CONTEXT.md:35 heading "(copied from `reference/hardware/`, as of 2026-09-23)"
  FIX: Record where the 09-27 container status came from (the command and host). Update pico-bringup.md and AGENTS.md §7.4 to match, or drop the claim. Fix the heading date so it does not call 09-27 facts copies of 09-23 files.

[14] (minor) course-project/CONTEXT.md
  QUOTE: The `VSYS` jumper is removed whenever USB is plugged in (no Schottky diode).
  PROBLEM: pico-bringup.md tells the first CONTEXT.md session to record the current state: whether the VSYS jumper is in, whether USB is plugged in, which UF2 is on the Pico, and which containers are running. The new section gives the UF2 and the containers but states only the rule, not whether the jumper is in or USB is plugged in now. The point of recording it is that the next session must not assume either.
  EVIDENCE: reference/hardware/pico-bringup.md:97 "copy the hardware state ... into `CONTEXT.md`, including whether the `VSYS` jumper is in, whether USB is plugged in, which UF2 is on the Pico, and which containers are running"; :34 "Do not assume the USB cable is still in the Spark."
  FIX: Add the last-known VSYS jumper and USB state with its date (2026-09-23: jumper out, USB state not recorded after the session), or mark them unknown.

[15] (minor) course-project/CONTEXT.md
  QUOTE: 5. Pico 2 W/RP2350 wireless micro-ROS transport is not yet proven in this environment.
  PROBLEM: The 2026-09-27 update adds a hardware section that contradicts older parts of the same canonical handoff file, which were left unchanged and are not marked as history. Only the 'Status of the 2026-09-14 design' heading is labelled history. 'Known hardware and integration uncertainties' still lists items that the reference files have since resolved: wireless micro-ROS transport (proven 2026-09-23), OV2640 vs OV3660 (OV3660 confirmed from a photo), and whether the regulators are what they claim (AMS1117 confirmed as the 3.3 V part, rails measured). The new section itself says the Pico runs micro-ROS over Wi-Fi and that the camera is an OV3660.
  EVIDENCE: CONTEXT.md:302-303, 308-311 vs CONTEXT.md:41, 46; reference/hardware/pico-bringup.md:10-21; esp32cam-notes.md:18 "mine is the OV3660"; car-build-notes.md:123 "AMS1117 measured 3.4 V ... confirms it is the 3.3 V part"
  FIX: Mark the 'Known hardware and integration uncertainties' and 'Immediate next steps' sections as 2026-09-14 history, or strike the resolved items and point to the reference files.

[16] (minor) assignments/assignment4/system-prompt/PLAN.md
  QUOTE: The twin has exactly the car's sensors (encoders, BNO055 in IMUPLUS, forward camera)
  PROBLEM: IMUPLUS (the BNO055 fusion mode without the magnetometer) is presented as a fact about the car's sensors. It is an undecided design choice. No hardware file or earlier decision picks a BNO055 fusion mode, no IMU firmware exists, and the older CONTEXT says to measure magnetic interference rather than assume anything. The same wording appears in APPROACH §5 ("BNO055 (IMUPLUS, no magnetometer)") and W3. The camera is not forward-facing today either: it looks at the ceiling.
  EVIDENCE: grep for IMUPLUS/NDOF finds it only in the new documents; CONTEXT.md:312-313 "Magnetic interference ... Measure this rather than assuming absolute heading is reliable."; esp32cam-notes.md:193 "Lying flat, the lens looks at the ceiling"
  FIX: Label IMUPLUS as a proposed design value (it belongs to D3/D10 or W3), and say the forward camera is planned, not current.

[17] (minor) course-project/CONTEXT.md
  QUOTE: No camera firmware yet.
  PROBLEM: No reference file supports this. esp32cam-notes.md never records whether the ESP32-CAM carries firmware. These boards often ship with a factory demo image. The repo only shows that nobody flashed it from the Spark (`esptool` and `arduino-cli` are absent). I suspect this is an inference; I cannot confirm or refute it from the files.
  EVIDENCE: reference/hardware/esp32cam-notes.md (no firmware-state statement; §5 and §8 only describe how to load firmware); AGENTS.md §7.4 "`picotool`, `esptool`, and `arduino-cli` are still absent"
  FIX: Reword to "No project camera firmware has been flashed (esptool/arduino-cli absent on the Spark); factory image state not checked", or check the board and record the result in esp32cam-notes.md.

[18] (minor) course-project/APPROACH-LLM-SLAM.md
  QUOTE: Isaac Sim ships an AprilTag MDL material and a ground-truth world→odom transform publisher; Replicator randomises scenes.
  PROBLEM: This row answers "Can Isaac Sim host it? Yes, with work" as though the AprilTag material is available on this Spark. The topic-5 research lists as an open unknown whether AprilTag.mdl and the tag36h11 mosaic ship with, or can be reached from, the source-built aarch64 install on the Spark (5.1.0-rc.19 built from `main`). The approach does not carry that caveat forward.
  EVIDENCE: research/.../topic5-benchmark-and-sim.md:108 "Not verified: whether the Isaac Sim 5.1 AprilTag.mdl material and tag36h11 mosaic ship with, or are reachable from, a source-built aarch64 install on the DGX Spark."; AGENTS.md §7.4 Isaac Sim row (source build, 5.1.0-rc.19)
  FIX: Add "(availability in the Spark's source build unverified)" to the row and a check step to W1.

[19] (minor) course-project/APPROACH-LLM-SLAM.md
  QUOTE: vLLM OpenAI-compatible with the right tool parser per model
  PROBLEM: W5 and risk 5 describe ROSA compatibility as unverified, but they leave out a problem already found and fixed on this Spark. Qwen chat templates reject ROSA's multiple system messages ("System message must be at the beginning."), and ROSA only works through the merging subclass in `discussions/module2/llm_backends.py`. There is also the one-`ROSA()`-per-process rule. Both bear directly on the "Decide ROSA's role" step and on every local-model arm.
  EVIDENCE: AGENTS.md §7.4 gotcha 5: "ROSA on vLLM-served Qwen needs one system message ... `discussions/module2/llm_backends.py` merges them ... construct **one** `ROSA()` per process."
  FIX: Cite AGENTS.md §7.4 gotcha 5 and llm_backends.py in W5 as known ROSA/vLLM integration requirements.

[20] (minor) course-project/APPROACH-LLM-SLAM.md
  QUOTE: Muse Glimmer is vLLM-verified on the Spark
  PROBLEM: In this repo "the Spark" means spark-2a60. The source (topic 3) says only that the vLLM recipes site marks Muse Glimmer verified on the dgx_spark_gb10 platform. The README's local check shows no Muse Glimmer weights in this Spark's Hugging Face cache, so it has not been verified here. Separately, the roster lists Qwen3.6-35B-A3B as a "Local (Spark)" model without the README's warning that the cached FP8 snapshot was an empty stub and must be re-checked.
  EVIDENCE: topic3-models-availability.md:34 and :73 ("vLLM recipes marks dgx_spark_gb10 'verified'"); README.md:40-42 (cache list, no Muse Glimmer; Qwen3.6 "earlier recorded as an empty stub; re-check before use"); pico-bringup.md:99
  FIX: Say "listed as verified on DGX Spark by vLLM recipes (not downloaded or tested on spark-2a60)" and add the Qwen3.6 stub caveat to the roster row.

  checked_ok: Rails in CONTEXT (left 5.03 V buck, middle 3.3 V from Pico pin 36, right 6.67 V 4xAA via rocker switch) match car-build-; GPIO map in CONTEXT (GP0/1 BNO055 I2C, GP2-8 TB6612FNG with STBY=GP5, GP16/17 right encoder, GP18/19 left encoder) match; Pico runs the instructor's LED-only pico2w_led micro-ROS image over Wi-Fi, agent on UDP 8888, with no motor/encoder/IMU ; VSYS/USB interlock, 'wheels up until a cutoff exists', and power-up order Pico first then battery switch (car-build-note; Camera is an OV3660 on its own USB-C, taped flat and looking at the ceiling, and must stand upright for a forward view (; Open firmware tests list (I2C 0x28, STBY high, encoder direction, motor direction) and watch items (battery-tray spring,; vllm-rosa serves Qwen3.5-35B-A3B with max-model-len 16384 (vllm-serve.sh NAME=vllm-rosa; the MAX_LEN=16384 run config in; ROSA 1.0.10, nine fixed system prompts, and the 'never perform calculations manually' math-tool rule inside prompts.py:6; RobotSystemPrompts has nine keyword arguments including environment_variables as a dict (HTML lines 954-965); the alphab; PLAN §3 range-sensor claim: syllabus line 13 mentions ToF sensors while the kit list (lines 128-156) has none; the Modul; SENTRY v1 patrol_tools.py claims a VL53L0X-class ToF (line 4), as PLAN §4 says; CONTEXT.md was last committed 2026-09-14 (git log 345b70d), as PLAN §3 says

######## LENS reasoning-and-d1 — 16 findings

[21] (major) course-project/APPROACH-LLM-SLAM.md
  QUOTE: **Technically feasible: yes.** The project is buildable with existing components, **novel**
(nothing in the literature reports an LLM doing landmark SLAM with trajectory error)
  PROBLEM: The verdict claims more than the research shows. (a) "Buildable with existing components": the research's own verifier says the core L2 design has no precedent. The component where the LLM orchestrates numeric tools and owns data association or loop closure does not exist, and no source shows an LLM calling a pose-graph solver as a tool. (b) The same document's §11 still lists as unresolved the items feasibility depends on: Isaac Sim 6.0 untested on aarch64 with 5.1 unsupported, harness compatibility with the 2026 APIs, aarch64 for the navigation models, and camera accuracy ("Borderline; it is the tightest limit"). (c) "Nothing in the literature" comes from a one-day agent web search that the researcher phrased as "I found no published work". One close candidate (an LLM-guided IMU-PDR paper doing "trajectory reconstruction") could not be opened and is marked unverifiable. The finding supports "plausibly feasible, subject to these conditions, and not found in a one-day search", not an unqualified "yes".
  EVIDENCE: topic1-llm-as-slam-literature.md:72 "'LLM orchestrates the estimator' is therefore a new design, not an established pattern"; topic1:98 "I found no source for an LLM agent calling a pose-graph or factor-graph solver ... as a tool"; topic1:1 "I found no published work, as of 2026-09-27"; topic1:50 [unverifiable] Sensors 26(18):5897 LLM-guided "trajectory reconstruction" (403); APPROACH §11 items 4, 5, 7; APPROACH:34 "Borderline; it is the tightest limit"
  FIX: Restate the verdict as conditional (for example "Plausibly feasible, conditional on W1/W2/W5 pilots"). List the open gating items next to it. Replace "nothing in the literature reports" with "a one-day search (2026-09-27) found no report" and note the unverified Sensors paper.

[22] (major) course-project/APPROACH-LLM-SLAM.md
  QUOTE: But the verifier notes that reasoning models (GPT-5, GPT-OSS-120B) reached 100 % on sequential grid navigation where instruct models failed (Sandfuchs 2026, arXiv:2604.09604). Treat it as an open question, not an expected failure
  PROBLEM: Sandfuchs 2026 is used as evidence against in-context pose drift, but the research records that the benchmark gives the agent its pose (oracle localization) and explicitly does not test SLAM. Scoring 100% on navigation with a known pose says nothing about whether an LLM can integrate odometry and keep a pose belief. The row presents the one piece of counter-evidence without this caveat, and the caveat undercuts it.
  EVIDENCE: topic1-llm-as-slam-literature.md:18 "The agent's pose is given to it (oracle localization), so the benchmark explicitly does not test SLAM"; topic1:1 "gives the model its position for free ('This is not SLAM: the uncertainty is in the map, not in pose')"
  FIX: Add the oracle-pose caveat. Say that no evidence directly tests in-context pose estimation by reasoning models, so the prior is uninformed, not favourable.

[23] (major) assignments/assignment4/system-prompt/PLAN.md
  QUOTE: 1. It is the project's headline design and the one most likely to work.
  2. It matches ROSA's own fixed prompt ("never perform calculations manually",
     `rosa/prompts.py:125`), whereas L1 contradicts it.
  PROBLEM: Both main reasons for choosing L2 are weak. Reason 1 is partly circular (L2 is the headline because D1 makes it so), and "most likely to work" goes against the approach's own ladder. L3 has classical GTSAM handling geometry underneath, and the approach itself flags L2 as novel and unprecedented. Reason 2 only matters if ROSA is the runtime harness. But D10 leaves the harness open ("ROSA or custom"). W5 plans a custom provider abstraction and records that rosa-ros2 lacks langchain-anthropic, so it may not be able to drive Opus/Fable. AGENTS.md says not to assume rosa-ros2 is the capstone runtime. The assignment itself only prints the prompts; no model runs under ROSA's fixed prompt. Outside ROSA, the nine fixed prompts, including the math rule, are absent, so "L1 contradicts ROSA" is not a reason to pick a level.
  EVIDENCE: PLAN.md:91 D10 "harness (ROSA or custom)"; APPROACH-LLM-SLAM.md:207 W5 "`rosa-ros2` pins LangChain 0.3.x, lacks `langchain-anthropic` ... **unverified**"; APPROACH:66 L2 "Novel: no source shows an LLM owning data association through tool calls"; APPROACH:67 L3 "Classical B1 runs underneath"; AGENTS.md:592-593 "Do not assume `rosa-ros2` is the capstone runtime unless `course-project/CONTEXT.md` says so"; PLAN.md:26 "printing all three"
  FIX: Drop "most likely to work", or justify it against L1 only (tool use fixes arithmetic: PAL/SpatialClaw) and not against L3. State that the ROSA argument holds only if D10 picks ROSA, or decide D10 before D1.

[24] (major) course-project/APPROACH-LLM-SLAM.md
  QUOTE: It calls **deterministic numeric tools** for geometry (integrate odometry, convert range/bearing into a map point, least-squares update, query the map)
  PROBLEM: The L2 definition is internally inconsistent with its claim that "the LLM owns the belief, the map". A "least-squares update" tool is a SLAM back-end: if the LLM can call it over accumulated observations, the tool computes the pose and map, and L2 collapses toward L3/B1. RQ1 ("how close does each model come to B1") would then measure the tool's design, not the LLM. The line between L2 and L3 depends entirely on tool granularity, which is deferred to D5 and never constrained. PLAN D1 1b repeats "The LLM owns the pose belief, the beacon map" while allowing "deterministic numeric tools for geometry".
  EVIDENCE: APPROACH:66 (L2 row) and APPROACH:67 (L3 row); APPROACH:73-74 RQ1; PLAN.md:98-101 D1 1b; PLAN.md:86 D5 "numeric tools" unspecified; topic1:98 no precedent for an LLM calling a factor-graph solver
  FIX: Define in D1 what the L2 tools may and may not do. For example, allow single-observation geometry (range/bearing to a map point, odometry composition) but no batch or global optimisation. Alternatively, make "least-squares update" an explicit sub-level so that RQ1 isolates the LLM's contribution.

[25] (major) assignments/assignment4/system-prompt/PLAN.md
  QUOTE: - **1a World:** one prompt that is true in **both** the Isaac Sim twin and the real car.
  PROBLEM: D1 defines validity across sim and real but ignores the benchmark's other axis, replay (open loop) versus closed loop. RQ1/RQ2 run on replay, where the logged observation sequence is fixed and the model's chosen moves are not executed. The L2 prompt D1 selects puts "exploration choice and termination" in scope and emits "belief report + ONE move" every step. In replay, the model's own move will often differ from the logged move, so the next observation contradicts its decision. A prompt that tells the model it chooses where to go is then false. D1 does not say how a single prompt stays true in replay.
  EVIDENCE: APPROACH:148-151 "Replay (open loop): record observation logs once ... feed the identical sequence to every model and level"; APPROACH:90 "belief report + ONE move"; PLAN.md:113-114 in-scope "exploration choice and termination"
  FIX: Add to D1 (or D10) which mode(s) the prompt targets. For replay, specify a variant in which the executed move is given as an input rather than chosen, and name the section that changes, as is already done for L1/L3.

[26] (major) course-project/APPROACH-LLM-SLAM.md
  QUOTE: Suggested order: W1 + W5 + W4 first. That gives a simulated L2 agent with 2–3 models against B1,
the minimum viable result. Then W2 + W3 + W8 for the real car.
  PROBLEM: The order conflicts with the sim design. The sim is supposed to use "detections degraded with the **measured** real noise", and W2 is where that noise is measured ("pilot: range and bearing error vs distance, which becomes the sim noise model"). Scheduling W2 after the sim-first minimum viable result means the first sim results either use an invented noise model or have to be re-run. It also means the sim-to-real risk (RQ4) is not tested until the end.
  EVIDENCE: APPROACH:118-119 "detections degraded with the **measured** real noise"; APPROACH:204 W2 "**pilot: range and bearing error vs distance**, which becomes the sim noise model"; APPROACH:212-213 order
  FIX: Move at least the W2 camera pilot (stand the camera up, flash firmware, calibrate, measure range/bearing error) before or alongside W1. Otherwise, state that early sim results use a placeholder noise model that will be re-run.

[27] (major) course-project/APPROACH-LLM-SLAM.md
  QUOTE: Assume 5k input + 2k output tokens per decision (the researcher's example; heavy reasoning
could exceed it). ... Replay mode costs about the same per
decision.
  PROBLEM: The cost model is likely too low for the design it prices. An L2 decision is not one model call. The agent calls observe, several numeric tools, belief/map read and write, and move, and each tool round trip re-sends the growing context and produces more output. The researcher's 5k+2k figure was a rough single-call example. Opus 5.5 has thinking always on. The total also covers only one closed-loop sweep, while replay multiplies the count by levels (L1/L2/L3/V) × conditions (unique/duplicated/hidden) × worlds (sim/real). The document calls cost "a first-class design constraint" but gives no budget and no per-level count. The same undercount affects latency: several tool turns × TTFT (~6 s for Opus low, ~98 s for Astra xhigh) per decision × 60 decisions.
  EVIDENCE: topic3-models-availability.md:44 "As a rough example, 200 steps × (5k in + 2k out)"; APPROACH:66 L2 lists four numeric tools; PLAN.md:86 D5 tools observe, move, belief/map read and write, numeric tools; APPROACH:131 "Thinking always on"; APPROACH:121-122 three conditions; APPROACH:196-197 TTFT figures
  FIX: Price per decision as (tool turns per decision) × (context per turn). Add replay sweep totals per level and condition. Set an explicit dollar budget before choosing the roster tiers.

[28] (major) course-project/APPROACH-LLM-SLAM.md
  QUOTE: 8. **Course fit.** The syllabus describes a *team* project with Customer/Seller roles, while
   `CONTEXT.md` records an individual project. Unresolved; it does not block the design.
  PROBLEM: "It does not block the design" is asserted without support, and the rest of the plan has no timeline. AGENTS.md records that the capstone is a team project with Customer/Seller roles, that 60% of its grade is preparation and participation, that the course's next-to-last week is devoted to it, and that the Course Project Description is authoritative (and not yet in the repo). A Customer/Seller structure could dictate scope, so the eight-workstream, many-model, sim-plus-real benchmark could be the wrong project for the grading scheme. The document gives no milestones against the semester, even though no motor, encoder, IMU or camera firmware exists yet and the twin is unbuilt.
  EVIDENCE: AGENTS.md:617-638 (team project, grading weights, "next-to-last week", "never default to a solo technical write-up", Course Project Description authoritative); CONTEXT.md:41-47 no motor/encoder/IMU or camera firmware; APPROACH §10 W1-W8 with no dates
  FIX: Mark course fit as a blocking open question until the Course Project Description or the instructor resolves team and role scope. Add a dated milestone plan working back from the project week, with an explicit cut line (for example, sim-only L2 plus B1 if the real car slips).

[29] (minor) assignments/assignment4/system-prompt/PLAN.md
  QUOTE: **Direction changed 2026-09-27.** The student proposed making the course project "LLM as
SLAM"
  PROBLEM: The status wording is inconsistent across the three documents. PLAN §4 says the direction "changed" (past tense). APPROACH says "proposed 2026-09-27, not yet approved". CONTEXT says "Status: proposed, awaiting approval", yet also lists "Decisions made 2026-09-27" (Isaac Sim, frontier models) under the unapproved direction. All three tie approval of the whole project redirection (roster, cost, benchmark, Isaac Sim) to approving D1 of a 10-point homework prompt, so signing off the prompt scope would silently approve the project change.
  EVIDENCE: PLAN.md:72; APPROACH-LLM-SLAM.md:3-4 "If Xiaohui approves the revised D1 (§12), this replaces the known-map ..."; CONTEXT.md:23-25 and 27-33
  FIX: Use "proposed" consistently. Separate the approval of the project direction from the approval of assignment D1, and state whether the instructor must also approve a change from the 2026-09-14 proposal (not verified here).

[30] (minor) course-project/APPROACH-LLM-SLAM.md
  QUOTE: | Can Isaac Sim host it? | **Yes, with work.** Isaac Sim ships an AprilTag MDL material and a ground-truth world→odom transform publisher; Replicator randomises scenes.
  PROBLEM: This row leaves out two things the research says. (a) The topic-5 researcher recommended Gazebo Harmonic as the main world generator and Isaac Sim 5.1 "only for a small photoreal subset". Choosing Isaac Sim for everything is the student's decision against that recommendation, and this is not disclosed as such. (b) Whether the AprilTag MDL and tag mosaic ship with, or can be reached from, the source-built aarch64 install is recorded as not verified, and the claims were checked against 5.1 docs only, not 6.0.
  EVIDENCE: topic5-benchmark-and-sim.md:69 "use Gazebo Harmonic ... as the main generator ... Use Isaac Sim 5.1 ... only for a small photoreal subset"; topic5:108 "Not verified: whether the Isaac Sim 5.1 AprilTag.mdl material ... ship with, or are reachable from, a source-built aarch64 install"
  FIX: Qualify the row: MDL availability on the Spark build and on 6.0 is unverified. Note that the research recommended Gazebo as the main tool and that Isaac Sim was chosen for career reasons.

[31] (minor) assignments/assignment4/system-prompt/PLAN.md
  QUOTE:   - detector output (id, range, bearing, quality) as observations;
  - the per-step belief report;
  - loop-closure decisions, including aliased-tag conditions;
  PROBLEM: The in-scope observation schema always includes an id, and D5's `observe` contract lists "detections: id, range, bearing, quality". But the aliasing conditions this item brings into scope include a hidden-ID condition, in which the detector reports only "a tag" plus geometry. As scoped, a prompt written to D1/D5 would be false in that condition.
  EVIDENCE: APPROACH:121-122 "hidden IDs (the detector reports 'a tag' plus geometry)"; APPROACH:53-54 "duplicated IDs, and a hidden-ID condition"; PLAN.md:86 D5
  FIX: Make id optional or nullable in the observation contract, and say explicitly in D1 whether hidden-ID is in v1 scope.

[32] (minor) assignments/assignment4/system-prompt/PLAN.md
  QUOTE: The twin has exactly the car's sensors (encoders, BNO055 in
  IMUPLUS, forward camera) and **no** range sensor.
  PROBLEM: The phrase "one prompt that is true in both" worlds describes neither world as it exists today. The twin has not been built (W1 gates all simulation). On the real car the camera looks at the ceiling, has no firmware and is uncalibrated, and there is no motor, encoder or IMU firmware, so the in-scope "shared bounded move set" and "detector output (id, range, bearing, quality)" are not yet capabilities of the car. PLAN §4 does frame decisions as design values, so this is acceptable only if the prompt labels them that way. D1 as worded says "true".
  EVIDENCE: CONTEXT.md:30-32 "No simulation runs until it exists"; CONTEXT.md:41-47 "no motor, encoder or IMU firmware yet", camera "looking at the ceiling ... No camera firmware yet"; reference/hardware/esp32cam-notes.md:193-196
  FIX: Reword 1a as "one prompt consistent with the design of both", and require the prompt's numbers and capabilities to be labelled as design limits (in line with PLAN §9 check 4).

[33] (minor) course-project/APPROACH-LLM-SLAM.md
  QUOTE: - **Shared move set:** FORWARD 0.25 m, TURN 30° left or right, DONE. These match Uni-NaVid's
  training actions (topic 4), so at least one navigation VLM runs in-distribution.
  PROBLEM: The move set is justified by a model the same document marks optional and not an exploration model. There is also no aarch64 evidence for it. The primary navigation arm (NoMaD/GNM/ViNT) is out of distribution under stop-and-go quantised moves whatever the step size. So the stated benefit does not reach any required arm of the benchmark.
  EVIDENCE: APPROACH:138 "Navigation model (optional) | Uni-NaVid 7B ... instruction-following VLN, not exploration"; topic4-vla-nav-foundation-models.md:57-58 and :80 "No direct evidence found that ... Uni-NaVid ... have run on aarch64"
  FIX: Justify the step sizes on the car's own terms (arena size, tag spacing, odometry error per step), and keep the Uni-NaVid match as a side benefit.

[34] (minor) course-project/APPROACH-LLM-SLAM.md
  QUOTE: an exact paired test's smallest p is 2/2ⁿ, so a Holm-corrected pairwise
  comparison needs **≥ 10 paired episodes** even when one model wins every time.
  PROBLEM: The figure of 10 was derived for 6 models (15 Holm tests). It is stated here as a general rule and then applied to the real car's 2–3 comparisons (7 would suffice there) and to the full sim roster (about 12 models, around 66 tests, where 10 is not enough). The verifier's correction is also missing: "≥10" is a lower bound, not a sufficient count, and for McNemar the floor depends on the number of discordant pairs.
  EVIDENCE: topic5-benchmark-and-sim.md:71 "Comparing 6 models pairwise means 15 tests"; topic5:83 "The '≥10 paired episodes' rule is therefore a lower bound, not a sufficient number"
  FIX: State the number of comparisons behind the figure and call it a lower bound. Size real-car n from the pilot variance, as topic5:72 recommends.

[35] (minor) course-project/APPROACH-LLM-SLAM.md
  QUOTE: | Frontier | Claude Fable 5.1 (`claude-fable-5-1`) | $10 / $50 | Released 2026-09-01. "Slower"; requires 30-day retention; no non-default sampling |
  PROBLEM: There is no data-governance decision anywhere in the approach, D1 or D10, even though frontier APIs will receive arena logs. The V ablation sends raw camera JPEGs, and the real arena location is not stated (possibly a home). Fable requires 30-day retention, and the Astra entry notes that monitoring can stop a conversation. Retention is listed only as a harness quirk. Minor because the text-model arms send detector output only.
  EVIDENCE: APPROACH:128, :132; APPROACH:69 V ablation "gets JPEG frames"; no data-handling item in APPROACH §11 or PLAN D10 (PLAN.md:91)
  FIX: Add a risk or decision: which arms may send images to which providers, the retention settings, and scrubbing the scene (no people or personal items in frame).

[36] (minor) course-project/CONTEXT.md
  QUOTE: 5. Pico 2 W/RP2350 wireless micro-ROS transport is not yet proven in this environment.
  PROBLEM: The new "Hardware state" section contradicts older sections that are not marked as history. It states that the Pico runs micro-ROS over Wi-Fi to the agent on UDP 8888, and that the camera is an OV3660. But "Known hardware and integration uncertainties" still calls wireless micro-ROS unproven and the sensor unconfirmed (OV2640 vs OV3660). These sections are top-level `##` headings, not under the "history" heading. Also, the Hardware state is labelled "as of 2026-09-23" but contains a 2026-09-27 observation.
  EVIDENCE: CONTEXT.md:41-42 and :46 vs :302-303 and :310-311; the history heading at :53 is a sibling `##`, not a parent; CONTEXT.md:35 vs :50
  FIX: Put the 2026-09-14 sections under one history parent heading, or mark the resolved uncertainties (items 1 and 5) as resolved with dates.

  checked_ok: Hardware state in CONTEXT.md (rails 5.03 V / 3.3 V / 6.67 V; GPIO GP0/1 I2C, GP2-8 TB6612FNG with STBY=GP5, GP16/17 righ; Camera 'taped flat, looking at the ceiling', caster end = front, must stand upright: matches reference/hardware/esp32cam; Ladder levels (L1 in-context, L2 tool-orchestrated, L3 on classical) and move set (FORWARD 0.25 m, TURN ±30°, DONE) agre; The L2 target and 'one prompt valid in sim and real' agree between APPROACH §12, CONTEXT:23 and PLAN D1; Per-decision cost arithmetic is internally correct given the stated prices and 5k/2k assumption (Astra/Fable $0.15, Opus; Syarubany 2026 characterisation (AprilTag anchors, ORB-SLAM3 pose, qualitative results only) matches topic1:44-45; Uni-NaVid 25 cm / 30° action space is supported by topic4:25 (verifier-quoted); Camera evidence (14 fps OV2640 at VGA, OV3660 ≲15 fps anecdotal, no OV3660 accuracy data, decimetre-level single-tag err; Isaac Sim 5.1 unsupported banner and 6.0 GA 2026-06-08 / v6.0.1 match topic5:38, 93; README verdict counts (52/37/32/36/58 claims; one refuted in topic5) match the table; the refuted CameraInfo claim is no; apt package versions and rosa-ros2 lacking langchain-anthropic in APPROACH:33/207 match README local facts (not independ
