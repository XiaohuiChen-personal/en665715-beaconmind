# LLM-as-SLAM feasibility research — 2026-09-27

Evidence behind [`../../APPROACH-LLM-SLAM.md`](../../APPROACH-LLM-SLAM.md). The approach
document cites this folder; read it here rather than re-running the search.

## Method

A Claude Code workflow (`llm-slam-feasibility`, run `wf_2372cb88-a5a`, Claude Opus 5.5) ran five
web researchers, one per topic. Each researcher was followed by an **adversarial verifier** that
re-opened every cited source and tried to refute each claim. Researchers had to quote a fetched
page for every claim and label their own inferences as such. Ten agents in total, no errors.

| File | Topic | Claims | Verifier verdicts |
| --- | --- | --- | --- |
| `topic1-llm-as-slam-literature.md` | Can an LLM/VLM itself do localization and mapping? | 52 | 46 confirmed, 4 overstated, 2 unverifiable |
| `topic2-fiducial-slam-baseline.md` | Classical AprilTag SLAM baseline; can this hardware support it? | 37 | 33 confirmed, 4 overstated |
| `topic3-models-availability.md` | Do the named frontier models exist? Which open models fit the Spark? | 32 | 29 confirmed, 2 overstated, 1 outdated |
| `topic4-vla-nav-foundation-models.md` | VLA and navigation foundation models as comparison subjects | 36 | 32 confirmed, 4 overstated |
| `topic5-benchmark-and-sim.md` | Benchmark metrics, simulation tooling, statistics | 58 | 49 confirmed, 7 overstated, 1 unverifiable, 1 refuted |

Each topic file lists every claim tagged with its verdict (a non-confirmed claim carries the
verifier's note), then the researcher's labelled **inferences**, the verifier's **challenges**
to those inferences, facts the researcher **missed**, and the open **unknowns**. `results.json`
is the raw workflow output.

**How to use it:** treat `confirmed` claims as sourced facts, as of 2026-09-27. Treat
`overstated` claims in their corrected form (the verifier's note). Treat inferences as design
suggestions only, and read the challenges before relying on one. Product facts (model
names, prices, latency, Isaac Sim versions) change monthly, so re-check them before spending
money or time on them.

## Local facts checked on `spark-2a60` the same day (read-only)

- apt candidates for host Jazzy, none installed yet: `ros-jazzy-apriltag-ros` 3.4.0-1,
  `ros-jazzy-apriltag` 3.4.5-1, `ros-jazzy-gtsam` 4.2.0-4.
- Host Python: `gtsam` and every AprilTag binding are missing. OpenCV 4.13.0 is installed with
  `cv2.aruco`, which also detects AprilTag 36h11.
- Gazebo Sim 8.11.0 is present (not the chosen simulator); Isaac Sim 5.1.0-rc.19 is built from
  source (AGENTS.md §7.4).
- Hugging Face cache: Qwen3.5-35B-A3B, Qwen3.6-35B-A3B-FP8 (earlier recorded as an empty stub;
  re-check before use), Qwen3.8-27B-FP8, Gemma-4-26B-A4B-it, Qwen3-Coder-Next(-FP8/NVFP4).
  No VLA or navigation-model weights.
- Ollama: `mistral`, `llama3.2`, `qwen3-coder-next:q8_0`. Memory: 121 GB total, ~118 GB available.
- `rosa-ros2` (jpl-rosa 1.0.10) has langchain 0.3.30, langchain-openai 0.3.35 and openai 2.54.0,
  and no `langchain-anthropic`. `rosa/prompts.py:125` tells the model: "You must use your math
  tools to perform calculations, especially for angles, distances, coordinates … never perform
  calculations manually in your reasoning". `rosa/tools/calculation.py` ships `atan2`,
  `distance_between_points`, `calculate_line_angle_and_distance` and more.
