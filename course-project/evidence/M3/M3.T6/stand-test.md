# Stand test (wheels up), 2026-11-25 (README section 5.0 and 5.1; plan tasks M3.T6 and M3.T7)

Session `20261125-025313-stand-test` on the Spark (recorder on throughout, 02:53:14 to 03:02:14 CST; commit
`b57533b`); operator Xiaohui Chen; car on its stand, both drive wheels in the air; a fresh 4 × AA motor pack. The
STOP key (S6) and the deadman (S7) were sent through tmux by the lead agent (Claude), not typed by Xiaohui. Every
number below was recomputed on 2026-11-25 from the session's move logs (`moves/*.jsonl`), the recorder's bag
(`bag/bag_0.db3`: `/pico/cmd_vel`, `/pico/wheel_ticks`, `/pico/imu/std`) and `data/LATCH.log`, read-only; the readers
are in `stand-test-runs/` (`bagread.py`, `stopan.py`). No frame of the session is in the repository.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: recomputed the numbers from the logs and wrote this record.
The tests were run by Xiaohui Chen with the lead agent.

**Result: pass (S1 to S7). S8 (stall) was not run, by choice (README: only with Xiaohui's agreement).**

## Before the motor battery (5.0)

| Step | What | Result | Source |
| --- | --- | --- | --- |
| 1 | `car_net.sh status` | access point up, camera at 10.42.0.89, car at 10.42.0.138, camera relay up | `meta/checks.txt` (the recorder's start checks) |
| 2 | recorder | session `20261125-025313-stand-test`, camera polled (2,449 frames), car and camera pinged (0.04 % and 0 % loss, longest gaps 0.31 / 0.35 s) | the session README |
| 3 | STOP program | running in tmux `bm-stop` from 02:53:21 CST, before the first move (02:54:53 CST); it latched on the key in S6 | `tmux ls` on the Spark; `LATCH.log` |
| 4 | `car.sh state` | telemetry 0.007 s old, armed, IMU ready, clock ok, latch clear, STOP program alive; `/pico/cmd_vel` subscribers the car and the rosbag, the STOP program the only publisher | read in the terminal by the lead agent, **not captured** in the session (no `terminal/` log) |
| 5 | drive map | set to 0.25 / 0.33 at 08:54:02 UTC: the bag's one `/pico/imu/std` message reads `[0, 0, 0, 0.25, 0.33]`; the car reported it back (every move later ran: the executor refuses a move without it) | bag |
| 6 | refusal without `--i-am-at-the-car` | `refused`, nothing sent | terminal, **not captured** |

## Wheels up (5.1)

The executor ran with the nominal encoder scale (20,524 counts per metre both wheels; the floor check changed it
afterwards). Times are the move logs' own.

| # | Move (start, UTC) | Result | Pass criterion | Pass |
| --- | --- | --- | --- | --- |
| S1 | `FORWARD_10` (08:54:53) | `done`, `achieved_forward_m` 0.0906; left +1,172, right +2,548 counts | done; 0.09 to 0.12; both counts positive | yes |
| S2 | `FORWARD_25` × 3 (08:55:19, :25, :31) | `done` each; 0.2457, 0.2472, 0.2442 m; peak speed 0.124, 0.141, 0.125 m/s; round trip 0.008, 0.033, 0.009 s; no lost samples, stop confirmed | done; 0.23 to 0.27 each | yes |
| S3 | `BACKWARD_10` (08:55:46) | `done`, −0.0960 m; left −1,382, right −2,559 | done; both counts negative | yes |
| S4 | `TURN_LEFT_30` (08:55:54) | `timeout` after 5.33 s; left −5,170, right +10,359 (left wheel backward, right forward) | left backward, right forward, `timeout` | yes |
| S5 | `TURN_RIGHT_30` (08:56:02) | `timeout` after 5.38 s; left +5,233, right −10,135 | the mirror image, `timeout` | yes |
| S6 | STOP key during `FORWARD_25` (08:56:28) | see below | wheels stop at once; `link_lost` / `estop`; latch `by: bm_stop` | yes |
| S7 | deadman: Ctrl+C, then the container killed, each during `FORWARD_25` | see below | wheels stop within about half a second | yes |
| S8 | stall | not run | (optional) | — |

On the stand the left wheel counted about half the right in the straights (S1 0.46, S2 0.52, 0.21, 0.56 of the right
wheel's counts): free wheels, the heading hold steering against a gyro that sees no turn (the second S2 run's gyro
read −7.55°: the car moved on its stand). On the floor the two wheels differ by 4 to 7 % (floor-check.md), so this
is a stand effect, not a fault.

### S6: the STOP key (also M3.T13 steps 4 to 6, `../M3.T13/smoke.md`)

The STOP program wrote the latch at 08:56:30.333 UTC (`LATCH.log`: `operator STOP (key)`, `by: bm_stop`). From that
moment (bag): the first zero command on `/pico/cmd_vel` +0.000 s (the last non-zero one 0.013 s before); the car's
own duty (telemetry fields 12, 13) 0 at **+0.037 s**; the wheel counts last changed at **+0.129 s** (left 48, right
169 counts after the key, about 2 and 8 mm at the nominal scale). Design value `estop_max_s` 0.2 s: met. The move
ended `"result": "link_lost", "reason": "estop"`, 0.1965 m of 0.25.

### S7: the deadman

- **Ctrl+C during `FORWARD_25`** (08:57:35): the executor handled the interrupt at 08:57:36.845 UTC and sent zeros at
  once (the bag's first zero command +0.000 s, the last non-zero 0.024 s before); duty 0 at **+0.034 s**, wheels still
  at **+0.144 s**. The executor latched (`LATCH.log`, 08:57:37: `a move ended link_lost (interrupted)`, `by: executor`);
  cleared by Xiaohui at 08:57:51.
- **The move's container killed during `FORWARD_25`** (08:58:14; `docker kill`, so nothing sent zeros): the last
  command reached the bag at 08:58:15.841 UTC (v 0.077 m/s), none after it; the next would have followed within
  0.05 s. The car's duty read 0 at **+0.547 s** and the wheels last moved at **+0.622 s** after that last command,
  so 0.57 to 0.62 s after the kill: the firmware's own command timeout (0.5 s, README section 8 row 1) stopped the
  car, as designed. No latch was set (the process that would set it was gone); the move log ends mid-move (its last
  0.65 s were not flushed before the kill), so the bag is the record of this half.

## Not verified here

The motor-off state check (step 4) and the flag refusal (step 6) were read in the terminal and not captured in the
session; the latch-refusal of M3.T13 step 5 likewise (`../M3.T13/smoke.md`). The firmware's stall cut-off (README
section 8 row 4) was not exercised.
