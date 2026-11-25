# M3.T19 / M4.T13 — replay of the real B2 logs through the three model arms: pipeline ready (2026-11-25)

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: wrote the converter, the runner, the analysis and their
tests, ran the dry rehearsal below and wrote this record. No model was called and nothing was spent; no GPU server was
started; nothing on the Spark was changed (the dry-run batch folders were copied to the Mac with `tar` over `ssh`).

Plan §3.6 work list 3.6 and report placeholder 5 (`report/PENDING.md`): per arm (B0, B2, Opus 5.5, Qwen3.8, Gemma 4)
the median final-position error on the real episodes driven by B2, with its uncertainty, the same on the simulated
rehearsal, and the difference.

## Input path

A batch episode folder is **not** a replay input as it is. The frozen replay loop (`harness/replay.py replay_seed`)
reads the study's observation logs, `{seed, world, records: [{step, truth, raw, report, calls}], noise, arena}`; the
batch writes, per episode `data/batches/<label>/episodes/<id>/`, the closed-loop harness's rows `seed_<n>.jsonl`, the
ground truth `truth.jsonl` and, in `manifest.json`, the episode's start pose and end circle. The converter
(`beaconmind/src/beaconmind/real_replay.py`, `tools/real_replay.py convert`) writes one log per episode that ended
normally (DONE or the step budget; halted, abandoned and superseded attempts are listed as excluded with the reason):

- `raw` from the rows (the sensing B2 got: detections, odometry, safety flags, last move);
- `truth` from `truth.jsonl` (`truth_map`: tag resection against the surveyed world, map frame of the episode's start,
  with `sigma_xy_m`, `sigma_theta_deg` and whether it is a fix at that step), checked equal to the rows' own truth;
  one extra trailing row after a last executed move (an episode that ran into the step budget) is accepted;
- `b2_estimate`, `report`, `calls`: the live driver's own, for the B2 reference row;
- `observation_real`: what the frozen `kinsim_lite.as_observation` cannot rebuild from `raw` (source "real", status
  and error, sensors, odometry quality, the validator's counters). A real step with `status: error` must reach the
  model as one (prompt rule 2 and row 0);
- `world`: the surveyed tags in the episode's map frame (`kinsim_room.room_scene` with the start pose);
- `real`: batch, episode, scenario, start pose, the end circle's position and sigma, the batch's own final error.

## Runner

`tools/replay_run.py` and `tools/replay_run.sh` are frozen by the pre-registration, so they are not edited. The new
`tools/real_replay.py run` imports the frozen runner and reuses its provider construction and checks, its
configuration tag, its resume rules, its spend cap and ledger, its workers and exit codes, and calls the frozen loop.
It adds the following:

- **`--dv`** (default `configs/dv-real.json`), through `beaconmind.dv_real.use_dv`, the batch's own scoped override.
  run.json records the file, its sha12 and the four fields that differ from the frozen file.
- **The real-room prompt** by default (`prompts/robot_system_prompt_v3.3-room.txt`). The run refuses to start when the
  prompt's range limit differs from the design values' `reject_range_above_m`: 3.0 m in both, checked.
- **The real observation's status fields** in every step message (`real_replay.real_observations`). For the duration of
  the run it wraps `kinsim_lite.as_observation`; no frozen file is edited.
- **Provider `procedure`**: the coded procedure as a free stand-in model, used for the rehearsal.

`tools/real_replay.sh` starts it in a one-off `beaconmind-ros` container, the same way `replay_run.sh` does: host
network for the local servers, the secrets env file for Opus, and the git commit recorded. The config tag differs from
the study's tags, because it covers the dv file, the overlay and the new code. `prereg_freeze.py --verify` stays OK.

## Dry rehearsal (simulated car, batch `b2-real-01-dry-r1-20261125`, the exact real arguments)

Converted 10 of 10 episodes, 732 steps (`dry-convert.txt`). The free `procedure` arm ran end to end through the
runner with `--dv configs/dv-real.json` and the room prompt (`dry-run-procedure.txt`, `dry-run-procedure-run.json`).

**Check:** at all 732 steps its estimate equals the live B2 driver's exactly, with 732 valid reports, 0 move calls and
US$0.00. That confirms the converter, the overlay, the design values and the prompt together: anything different
would have changed a pose. `--dv frozen` with the room prompt is refused (range limit 3.0 against 2.0 m).

Result table, exactly as the analysis writes it (`dry-rehearsal.md`, `dry-rehearsal.json`):

| Arm | n | median | IQR | min | max | median heading error (deg) | median truth sigma | vs end circle (median) | vs simulator truth (median) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 | 10 | 2.2 | 1.5 to 2.8 | 1.1 | 5.0 | 0.2 | 5.0 | 2.1 | 2.3 |
| B2 | 10 | 2.9 | 2.2 to 4.8 | 0.8 | 5.5 | 0.8 | 5.0 | 3.0 | 3.0 |
| procedure (stand-in) | 10 | 2.9 | 2.2 to 4.8 | 0.8 | 5.5 | 0.8 | 5.0 | 3.0 | 3.0 |

(cm.) B2's per-episode errors equal the batch's own `final pose error` column. In this dry run, the batch's resection
truth lies 0.3 cm (median) and at most 0.6 cm from the simulator's own pose at the last step.

**How to read it on the car.** The truth's own sigma is 5 cm (the batch's floor, `fix_floor_m`), as large as most of
the errors. Differences between arms smaller than about 5 cm are not resolved by this ground truth. The "vs end
circle" column uses the full circle after the episode (sigma about 2–3 cm) as a second truth for position.

## First real batch `b2-real-01`, episode 1 (2026-11-25)

The batch halted after episode 1 (`odometry_scale`: 0.72 m by odometry against 0.91 m by the tags over the episode).
The episode itself ran to its end: DONE after 83 steps, `result.complete` true, end circle OK. The check that halted
it runs after the episode, so the manifest has status "halted" and has no `end_pose_map` and no `final_pose_error`.
The converter now accepts such an episode: `real_replay.finished` requires the result complete and DONE or the step
budget, and status done or halted with an end circle. It takes the end pose from `end_fix.pose_now`, the pose the
batch tracks after the end circle (`car/batch.py` sets `end_pose_world` from that same pose). It records the episode
in `index.json` with "completed; batch halted after the end by odometry_scale". An episode halted before its end is
still excluded. Both cases are tests, built on the structure of the real folder: `real_car` true, `_tag` null, source
"real", one `slip_suspected` step, no `end_pose_map`. No frames are involved; the episode folder holds none.

`convert` (`real-b2-real-01-convert.txt`), `estimate` (`real-b2-real-01-estimate.txt`) and the free procedure arm
(`real-b2-real-01-check-procedure.md`):

| Arm | Final-position error (cm) | Heading error (deg) | Truth sigma (cm) | vs end circle (cm) |
| --- | --- | --- | --- | --- |
| B0 (dead reckoning) | 19.7 | 7.7 | 5.0 | 26.1 |
| B2 (live driver) | 3.1 | 3.7 | 5.0 | 3.4 |
| procedure (stand-in) | 3.1 | 3.7 | 5.0 | 3.4 |

The stand-in's estimate equals the live B2 at 83 of 83 steps, with 83 valid reports, 0 move calls and 0 errors. On
the carpet, dead reckoning drifted about 20 cm over the episode, and B2's fixes kept it to 3 cm. This is one episode.

**What the real folder's format held, against the dry runs:**
- `real_car` true, `source` "real" at all 83 steps.
- **No `status: error` step**: all 83 observations are `ok`, with sensors camera ok, imu ok, pico armed. The error path
  is still exercised only by the tests.
- Odometry quality: `slip_suspected` at step 24, the rest `ok`, and none at step 0 (null odometry, normal). The overlay
  carries `slip_suspected` into the replayed step message, checked.
- **`_tag` is null in all 105 detections.** The converter, the replay and the final-error analysis do not need it.
  The study's association precision and recall (`metrics/pilot.py LabelTracker`) and `tags_ever_detected` do, so they
  cannot be computed on real logs. Map scoring against the surveyed tags (C10.3) still can.
- truth.jsonl: 83 rows numbered 0 to 82, equal to the rows' truth. 60 are tag fixes and 23 are tracked since a fix;
  sigma 0.050–0.059 m; `sim_truth_world` null (handled; there is no simulator column).
- The manifest has no `end_pose_map`, `end_pose_world`, `agent_final_pose_map` or `final_pose_error`. They are handled
  as above; the final error comes from truth.jsonl anyway, the same method as the batch's.

## Commands for the real batch (Spark host, repository root `~/Projects/en665715-beaconmind`)

The order is Opus 5.5, then Qwen3.8, then Gemma 4, with one GPU server at a time. The Opus arm uses no GPU, so it may
run alongside a local arm. Start each run in tmux. **I have started none of these.**

```bash
cd ~/Projects/en665715-beaconmind && git pull --ff-only      # code of this commit (the clone is the batch agent's: coordinate)
L=b2-real-01; R=course-project/data/real-replay/$L

# 1. convert (host python3, standard library), estimate, free check (expect: the procedure row equals B2's)
python3 course-project/tools/real_replay.py convert  --batch course-project/data/batches/$L --out $R/obslogs
python3 course-project/tools/real_replay.py estimate --obslogs $R/obslogs
python3 course-project/tools/real_replay.py run --provider procedure --obslogs $R/obslogs --out $R/runs/procedure --cap-usd 0
python3 course-project/tools/real_replay.py analyze --obslogs $R/obslogs --run procedure=$R/runs/procedure --out $R/check-procedure

# 2. Opus 5.5 (Anthropic API; cap US$200 as approved)
tmux new -d -s bm-rr-opus "bash course-project/tools/real_replay.sh --provider claude-opus-5-5 --obslogs $R/obslogs \
  --out $R/runs/claude-opus-5-5 --cap-usd 200 --workers 8 2>&1 | tee $R/claude-opus-5-5.log"

# 3. Qwen3.8 (vLLM, 127.0.0.1:8000)
bash course-project/tools/serve_qwen38.sh start && bash course-project/tools/serve_qwen38.sh wait
tmux new -d -s bm-rr-qwen "bash course-project/tools/real_replay.sh --provider qwen38-flash-xhigh --obslogs $R/obslogs \
  --out $R/runs/qwen38-flash-xhigh --cap-usd 0 --workers 8 2>&1 | tee $R/qwen38-flash-xhigh.log"
# ... when it has finished:
bash course-project/tools/serve_qwen38.sh stop

# 4. Gemma 4: the study's arm is `gemma4-26b`, Google's bf16 checkpoint on vLLM (127.0.0.1:8001), not Ollama
bash course-project/tools/serve_gemma4_vllm.sh start && bash course-project/tools/serve_gemma4_vllm.sh wait
tmux new -d -s bm-rr-gemma "bash course-project/tools/real_replay.sh --provider gemma4-26b --obslogs $R/obslogs \
  --out $R/runs/gemma4-26b --cap-usd 0 --workers 10 2>&1 | tee $R/gemma4-26b.log"
bash course-project/tools/serve_gemma4_vllm.sh stop

# 5. the result (and the gap to the simulated rehearsal: convert and analyse the dry run the same way)
python3 course-project/tools/real_replay.py analyze --obslogs $R/obslogs --run "Opus 5.5=$R/runs/claude-opus-5-5" \
  --run "Qwen3.8=$R/runs/qwen38-flash-xhigh" --run "Gemma 4=$R/runs/gemma4-26b" --out $R/analysis \
  [--compare course-project/data/real-replay/<rehearsal>/analysis.json]
```

A run that stops (exit 1 failed seed, 2 cap, 130 Ctrl-C) resumes with the same command plus `--resume-reason "<why>"`.
A different configuration is refused. The `ollama` provider `gemma4-26b-ollama` also works with the runner, if the
lead prefers it, but it is not the study's arm.

## Estimates

The rates were measured in the study's held-out sweep, `data/main/runs/drift2/<arm>`, from run.json `started` to the
last `run.end` `ended`, over 1,976 steps and 30 seeds per arm:

| Arm | Workers | Latency per step | Wall per step at that parallelism | US$ per step |
| --- | --- | --- | --- | --- |
| Opus 5.5 | 8 | 19.3 s | 2.71 s | 0.0729 |
| Qwen3.8 xhigh | 8 | 236.2 s | 31.3 s | 0 |
| Gemma 4 (vLLM) | 16 | 1,240.4 s | 110.6 s | 0 |

`tools/real_replay.py estimate` gives the cost from the steps × US$ per step. It gives the time as a range: the total
steps at the study's throughput, and the longest episode replayed alone at the study's latency. With ten episodes and
eight or more workers, the longest episode can dominate.

For the dry rehearsal's 732 steps (longest episode 150), from `dry-estimate.txt`:
- Opus: about US$53, 0.6–0.8 h.
- Qwen3.8: 6.4–9.8 h.
- Gemma 4: 22.5–51.7 h (latency should be lower with 10 requests in flight than the study's 16).

For the real batch, rerun `estimate` on its converted logs.

## Tests

`beaconmind/tests/test_real_replay.py` has 8 tests, with no network:
- The converter keeps the truth, B2's estimate and the real observation, and puts the tags in the map frame.
- Truth rows must match the steps; one trailing row is allowed.
- The status of the real observation reaches the step message, and the wrapper is removed afterwards.
- The free arm reproduces B2 through the runner, records the dv file, and needs a resume reason to rerun.
- A prompt and design values that disagree are refused.
- A scripted Anthropic arm (the suite's fake client) runs through the real provider path, stops at its spend cap
  (exit 2), and then resumes to completion.
- The final errors and summary are checked against hand-computed values.
- The estimate arithmetic.

## Untested

- The container launcher `tools/real_replay.sh`. It is a copy of `replay_run.sh` with `--dv` added and `run`, and its
  shell syntax is checked. It was not started on the Spark, because no container was started there while the car was
  in use.
- The container's Python 3.10 itself. The syntax was checked with `ast` at 3.10, and the code ran under 3.12 and 3.13.
- Real provider calls: Opus through the real API, Qwen3.8 and Gemma 4 servers.
- A real `status: error` step: the first real episode had none.
- A batch halted inside an episode, on real data (only the test fixture).
