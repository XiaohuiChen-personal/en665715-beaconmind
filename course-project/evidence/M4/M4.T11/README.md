# M4.T11 (early) — first-draft pilot, 2026-10-29

An early, reduced version of M4.T11 ("dev-seed pilot") run for the Class Project Report first draft.
It is not the full M4.T11: one LLM arm (Claude Opus 5.5), K = 1, five development seeds per condition,
the kinematic simulator only, no B1 (GTSAM) and no closed loop. Every number in the report's
Results section comes from the files below through `tools/pilot_analyze.py`.

## What was run

| Item | Value |
| --- | --- |
| Simulator | `beaconmind/src/beaconmind/envs/kinsim_lite.py` (port of the Module 4 `backstory_sim.py`; plan M2.T3 placeholder noise) |
| Seeds | development seeds 1000-1004 (plan C7 dev block) |
| Conditions | `nominal` (no systematic odometry error) and `drift2` (2 % systematic over-read of forward distance and turn angle) |
| Arms | B0 dead reckoning, B2 the D7 procedure as code (it drives the episode), L2 Claude Opus 5.5 in replay |
| Agent settings | `claude-opus-5-5`, adaptive thinking, effort medium, max_tokens 64000, prompt caching; prompt `prompts/robot_system_prompt_v3.3.txt` (SHA-256 prefix `d0b75b25a86e`); tools `harness/tools_d5.py` |
| Judges | `gpt-6.1-sol` (OpenAI Responses, effort medium, strict JSON schema) and `gemma4:26b-a4b-it-bf16` (Ollama 0.40.11, temperature 0, seed 101, think off) |
| Where | DGX Spark: agent and judges in one-off `beaconmind-ros:humble` containers; analysis in `~/.venvs/beaconmind` |

## Files

- `pilot_summary.json` — every metric per condition, seed and arm; H1 pilot statistics; L2-vs-B2 statistics;
  the power simulation; the judge calibration and the selected judge; per-seed rubric scores; the baseline sweep.
- `pilot_per_seed.csv` — the per-seed table behind Table `tab:pilot`.
- `trace_example.json` — the full transcript of one re-run step (Fig. `fig:trace`).
- `judge/` — evidence version 2 (the reported judge run): `items.jsonl.gz` (items without the evidence blocks),
  `sol.jsonl.gz`, `gemma.jsonl.gz` (levels and reasons). `judge-v1/` — the first judge run, whose evidence lacked
  the rules, the observation and map states; kept for the comparison in the report.
- `runs/<condition>/seed_<n>.jsonl.gz` — the raw run logs, one JSON line per step, and each run's `run.json`.
- `obslogs/<condition>/seed_<n>.json.gz` — the recorded episodes (world, truth, observations, B2 reports and calls).
- `CODE-REVIEW.md` — the adversarial review of the pilot code and what was changed.
- `../../M5/eval_refs.md` — verification notes for the evaluation and statistics references.

## Reproduce (on the Spark, from `course-project/`)

```bash
python3 tools/pilot_record.py --seeds 1000-1004 --out data/pilot-20261029/obslogs
python3 tools/pilot_record.py --seeds 1000-1006 --odo-bias 0.02 --out data/pilot-20261029/obslogs-drift02
bash tools/pilot_run.sh opus 1000-1004 110 40
bash tools/pilot_run.sh opus-drift02 1000-1004 80 35 obslogs-drift02
# judges, inside beaconmind-ros (see the docstring of tools/pilot_judge.py); evidence version 2
python3 tools/pilot_judge.py --runs data/pilot-20261029/opus --extra drift2=data/pilot-20261029/opus-drift02 \
    --out data/pilot-20261029/judge-v2 --judges sol --cap-usd 25
python3 tools/pilot_judge.py --runs data/pilot-20261029/opus --extra drift2=data/pilot-20261029/opus-drift02 \
    --out data/pilot-20261029/judge-v2 --judges gemma
~/.venvs/beaconmind/bin/python tools/pilot_analyze.py --data data/pilot-20261029 --evidence evidence/M4/M4.T11 --report report
```

## Known limits

- The pilot harness does not yet check reported states against tool results (M2.T14); the agent's report is
  scored as written, and only an unparseable report or one without a numeric pose and a well-formed map is replaced.
- Judge evidence version 2 still omits the beacons' `odo_last_seen_m`; the one remaining gate failure quotes it.
- The Gemma run on evidence version 2 was stopped after its calibration items and 158 real notes (all no-drift),
  so inter-judge agreement covers those notes only. The archived `judge/` files are the snapshot analysed.
- The trace in `trace_example.json` was re-run with `thinking.display = "summarized"`; the pilot runs left it unset,
  so their thinking blocks have empty text.
- One run of the no-drift smoke test was started twice by one SSH command; the smoke folder is not used, and the
  runner now takes an exclusive lock on its output folder.

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: wrote the pilot code, ran it and wrote this README.
