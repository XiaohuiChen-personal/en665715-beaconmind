# Which B2 the real batches drove, and the switch to the room's (2026-11-25)

The video agent found it: `tools/car_batch.py` built its driver with `build_driver(args.policy)`, without
`room=True`, so `--policy b2` gave `closed_loop.B2Driver()`, the frozen `kinsim_lite` procedure. The study's room B2
(M2.T7) is `kinsim_room.make_b2_policy()`: the same code plus the dead-end branch a room reaches. At "E5 leg with no
forward move and no E4" the frozen code stops, and the room's decides the step again with the heading blocked
(rule 7b). That is how `b2-real-06`'s episode 2 (S3) ended, at step 44 (`B2 stopped: E5 leg with no forward move
and no E4`). No manifest recorded which procedure ran. The config hash covered the driver's header, but the manifest
did not store it.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: checked the code and the logs, wrote `b2_policy_replay.py`
and this note, and made the change.

## What the real episodes ran

- **From the code:** every batch so far ran `car_batch.py` with `tool.build_driver(args.policy)` and no `room`
  argument. `closed_loop_run.build_driver` returns `cl.B2Driver()` then, with the policy `"kinsim_lite"`.
- **From the logs** (`b2_policy_replay.py`, `replay-output.txt`): every step of b2-real-01 to 06 is fed to both
  procedures, with the logged observation, the logged previous report, and the design values the batch ran with
  (`configs/dv-real.json` sha12 ea2cd23f9186, the same for all six).
  - The frozen one reproduces every logged decision: 888 of 888 steps (13 episodes, b2-real-06 ep02's dead-end
    step apart).
  - The room's decides exactly as the frozen one (decision, memory, pose, map) on every one of them.
  - The only step where they part is b2-real-06 episode 2 step 44. There the frozen one stopped, and the room's
    would have turned right (TURN_RIGHT_30), with the blocked heading 35.4°.
- **So the nine episodes that ran to DONE** (b2-real-01 ep01; 02 ep01, ep02; 03 ep01, ep02; 05 ep01–03; 06 ep01)
  are exactly what the room's procedure would have driven. They never reached the branch.
- b2-real-07 was not on the Mac when this was written. It ran the same `19f71e6` tool, so the frozen procedure.
- Without the design values the replay misses one step (b2-real-05 ep02 step 116, a beacon fix the real run took),
  so the batches' `--dv` has to be applied, as the script does.

## The change (in the commit after `ed5bf4d`)

- **`tools/car_batch.py`** builds `--policy b2` with `room=True`: `cl.B2Driver(kr.make_b2_policy(),
  "kinsim_room.make_b2_policy()")`, in real and dry batches. It logs `driver: B2 kinsim_room.make_b2_policy()
  (sources ...)`.
- **The manifest** has `driver`: arm, provider, policy, settings, and the sha12 of the procedure's sources
  (`envs/kinsim_lite.py`, `envs/kinsim_room.py`, `harness/closed_loop.py`, `geometry.py`, `dv.py`;
  `batch.driver_record`). A resumed batch appends to `drivers`.
- **Resume:** the config hash already covered the driver's header. A batch started on the frozen procedure is
  therefore not resumed on the room's: it is refused as a different configuration.
- **Test:** `test_a_batch_at_the_e5_dead_end_continues_with_the_room_b2` feeds the real step 44 to both drivers, from
  `beaconmind/tests/fixtures/b2_real_06_ep02_step44.json` under its design values. The frozen one stops with the
  logged error; the room's turns right with the heading blocked. A dry run of the tool then shows the room's
  procedure in the manifest with its sources' hashes.

## The ten-episode dry runs with the exact real arguments (`dry-runs-log.txt`)

`--slip-sigma 0.3`, plain and the simulated carpet at north 0.78, 0.67 and 0.60, run one at a time:

| Run | Room B2 (this commit) | Frozen B2 (`ed5bf4d`, the same code otherwise) |
| --- | --- | --- |
| plain | 10 of 10 by DONE, 1,508 moves | the same, move for move |
| north 0.78 | 10 of 10 by DONE, 1,588 moves, truth p95 / max 0.062 / 0.163 m | **episode 3 (S3) stopped at the dead end after 74 steps**; 1,553 moves, 0.057 / 0.256 m |
| north 0.67 | 10 of 10 by DONE, 1,691 moves | the same, move for move |
| north 0.60 | 10 of 10 by DONE, 1,814 moves | the same, move for move |

**The dead end was there in the earlier dry runs, and I missed it.** At north 0.78, on `19f71e6`
(`../truth-under-slip/final-dry-runs-log.txt`), `9dd80e9` and `ed5bf4d` (`../truth-under-slip/same-tag-dry-runs-log.txt`),
episode 3 ended "error (driver stopped: B2 stopped: E5 leg with no forward move and no E4)". The manifest counts such
an episode as done (it was measured at its end circle), and my summaries counted done episodes. So "10 of 10" there
meant nine by DONE and one stopped by the coded procedure. With the room's procedure all ten end by DONE.

Every run's manifest has `driver`: `kinsim_room.make_b2_policy()`, with kinsim_lite.py 4fe853bf47ac and
kinsim_room.py 33a3c5d49239.
