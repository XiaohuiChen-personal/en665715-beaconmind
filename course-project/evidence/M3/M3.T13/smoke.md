# STOP check on the car, 2026-11-25 (README "Procedure", steps 4 to 7)

Done inside the stand test, session `20261125-025313-stand-test` (car on its stand, wheels up, fresh 4 × AA, recorder
on; `../M3.T6/stand-test.md`). The STOP program ran in tmux `bm-stop`; the STOP key and the Ctrl+C were sent through
tmux by the lead agent (Claude), not typed by Xiaohui. Numbers recomputed from the session's move logs, its bag and
`data/LATCH.log` (readers in `../M3.T6/stand-test-runs/`).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: recomputed the numbers and wrote this record. The check was
run by Xiaohui Chen with the lead agent.

**Result: pass (steps 4, 6, 7; step 5 as far as the logs can show it).**

| Step | What | Result | Pass |
| --- | --- | --- | --- |
| 4 | SPACE during `FORWARD_25` (08:56:28 UTC) | latch written 08:56:30.333 by `bm_stop` (`operator STOP (key)`); zero commands at once; the car's duty 0 after **0.037 s**, wheels still after **0.129 s** (`estop_max_s` 0.2 s); the move ended `link_lost` / `estop` | yes |
| 5 | a move while latched | no move log between the latch (08:56:30) and its clearing (08:57:16): no move ran. The printed `refused, nothing was sent` was read in the terminal and is **not captured** | yes, as far as recorded |
| 6 | `clear-latch --operator xiaohui`, the move again | cleared 08:57:16.999 by `xiaohui` (`LATCH.log`); `FORWARD_10` at 08:57:20 ran `done` (0.0923 m) | yes |
| 7 | kill test | Ctrl+C mid-move: zeros at once, duty 0 after 0.034 s, wheels still after 0.144 s, executor latch set (cleared 08:57:51). Container killed mid-move, no zeros sent: wheels still 0.57 to 0.62 s after the kill, by the car's own 0.5 s command timeout | yes |

The 0.2 s figure (`estop_max_s`) is now measured on the real link: 0.129 s on the stand, 0.103 s on the floor
(`../M3.T6/floor-check.md`, F5). The STOP program's keyboard loop ran in a real tmux terminal on the Spark (the
README's open item about a terminal over ssh): the key reached it through tmux, not through Xiaohui's own keyboard.
