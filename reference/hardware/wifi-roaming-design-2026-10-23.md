> Public copy for BeaconMind, 2026-10-29; the private course repo holds the unredacted original.

# Build J: a robust, roaming Wi-Fi link for the Pico 2 W car (firmware design)

Date: 2026-10-23. Status: **design only** (saved to the repo 2026-10-24). Nothing has been built or flashed, and no repository file, network setting or router setting was changed. This document replaces the 2026-10-20 "keep the car pinned" recommendation (`reports/Seamless WiFi mesh roaming for Pico.md`). That recommendation fails at the car's floor spot.

**Privacy.** No SSID, password or full MAC address appears here. A node is named by the last 3 bytes of its 2.4 GHz BSSID (for example ..bd2b48). The firmware must keep printing BSSIDs the same way.

**How to read the labels.**
- **(V)**: verified, either in the source read for this design (cyw43-driver v1.1.1 at commit 055d642, pico-sdk 2.3.1, lwIP 2.2.1, all taken from the Spark's `pico-microros-builder` image) or in the measurements.
- **(I)**: inference.
- **(L)**: likely. These claims come from the Broadcom wl 7.10 FullMAC source, a sibling of the chip's 7.95.49 firmware but not that binary. They stay "likely" until a Build J stage measures them.

**Terms used below.**
- **Node:** one eero.
- **Roam:** the radio leaves one node and associates with another node of the same network. The IP address stays the same.
- **Chip:** the CYW43439 Wi-Fi chip, running its own firmware 7.95.49, which includes its own roam engine.
- **Host:** our C code on the RP2350, together with the cyw43 driver.
- **ioctl:** one command from the host to the chip. It can block the main loop for up to about 2 s.
- **Session:** the micro-ROS session with the agent on the Spark. Rebuilding it takes seconds and disarms the car.
- **Beacon:** the "I am here" frame each node sends about 10 times a second.
- **BTM (802.11v):** a request from a node asking a client to move.

---

## 1. Bottom line

> **Public copy, 2026-10-29.** The room-by-room mesh map and each node's LAN address are omitted. The private course repo holds them. Firmware-relevant result of the 2026-10-24 check: one node that an earlier draft said should get an Ethernet cable was already wired, so that router change is withdrawn. Its 1 Mb/s bursts still coincided with a stall and are not treated as backhaul data. Two nodes with a wireless backhaul (`..b955c8` and `..b75a08`) start at −6 dB in `WIFI_NODE_PRIORS`; wired-backhaul nodes start at 0 dB. The per-node service record then adjusts those priors.

1. Most of the car's long outages at the floor spot are made by the firmware's own supervisors, not by the radio. In the synchronized capture, about 1.4 s of real silence became 9.4 s of silence plus a disarm, because the 4 s session rule tore the session down (V). Build I's 23-34 s silence matches the forced-rejoin path in size (I).
2. The first fix is therefore **session tolerance (Build J1), with the pin kept**. The firmware counts any datagram from the agent as proof of life and rebuilds the session only after 20 s of silence, an IP change, or a proven agent restart. It keeps the session across Wi-Fi rejoins. It still disarms after 3 s of silence, so the safety rule keeps its meaning.
3. Roaming alone cannot fix the floor spot. All six nodes share channel 6, the car's RSSI did not move during the worst stall, and the stall coincided with the eero mesh's own 1 Mb/s traffic between nodes (V for the measurement, I for the cause). Range still matters, though: at that spot the pinned ..bd2b48 swings between -58 and -77 dBm, while ..b75a08 was heard at -56 dBm.
4. Roaming is added in two layers.
   - **Chip safety net (J2):** the chip's roam engine is switched on with emergency-only settings: trigger -78 dBm, delta 10 dB. It then recovers from beacon loss, deauthentication and very weak signal by itself, even while driving.
   - **Host-chosen nodes (J2 and J3):** the host picks the node at every join, using a per-node preference and a record of how well each node has served the car. From J3 it also moves the car proactively, **only while parked**, with Apple-style hysteresis (-70 dBm and 8-12 dB) and strict limits against flapping.
5. Everything ships as one-change-at-a-time builds, each A/B-tested at the floor spot with numeric pass criteria:
   - J0: observe only.
   - J1: session tolerance.
   - J2: chip safety net plus host-chosen joins.
   - J3: parked host roaming. It starts with break-before-make; in-place REASSOC comes only after a 20-of-20 bench gate.
   - J4 (optional): BTM.
   `WIFI_ROAM_MODE 0` rolls back to Build I at any time.
6. Motor safety does not change. The 500 ms command timeout and the 600 ms deadman interrupt stay exactly as they are, and no radio ioctl runs while driving. Blocking leave and join calls now also wait until the wheels have stopped.
7. On the router side, wireless backhaul adds 1 Mb/s mesh airtime on the shared 2.4 GHz channel. The household map of which node to cable is not in this public copy. A 2026-10-24 check withdrew one "add Ethernet" item because that node was already wired.

---

## 2. What the measurements show

| What | Measured | Where |
|---|---|---|
| Mesh layout | 6 eero nodes. Every 2.4 GHz radio is on **channel 6** (20 MHz); 5 GHz is on ch 108 and 6 GHz on ch 133, which the Pico cannot use. Room placement and per-node LAN addresses are omitted from this public copy. | survey:7-12 |
| Roaming standards offered | 802.11k and 802.11v advertised. 802.11r not offered (PSK only, no Mobility Domain). | survey:15-16 |
| Channel 6 load | Nodes report 45-56 % utilisation with 6-18 stations each. About 839 frames/s from 77 transmitters. | survey:19-28 |
| Airtime at the Spark (120 s) | About 41 % of airtime was decoded frames. 27.6 % was eero's own node-to-node mesh data at 1-2 Mb/s, about 87 % of it retries. | eero research, `assignments/assignment7/tools/wifi_survey/analysis_air/airstats.py` |
| Car RSSI at the floor spot (pinned ..bd2b48) | -58 to -77 dBm over the day (2-min medians -61 to -66). Once ..b75a08 was heard at -56 dBm. Near the Spark: -42 dBm, clean. | survey:36-38 |
| Link quality at the floor spot | Ping median 4-7 ms, but p90 485-1845 ms and p99 2.5-11 s. Up to 45 % lost in the worst 30 s. | survey:45-46 |
| Build G.1 vs Build I at the spot (2 min each) | G.1: 46 sync misses/min, 3 gaps > 1 s (max 3.55 s), 0 rebuilds. I: 32/min, 7 gaps > 1 s (max 3.46 s), then about 23-34 s silent and 2 rebuilds. | bench log :764-769 |
| Session churn | 12 sessions in 17 min, all with the Wi-Fi link up. | survey:44 |
| eero behaviour | No deauth, disassoc, BTM or reassociation involving the Pico in 210 s, and none sent to any station in another 120 s. The PM bit was never set in 2,127 Pico frames. | survey:49-51; eero research |
| Retries | Pico uplink 31-32 %; the node's downlink to the Pico 18-21 %. | survey:52-53 |
| Node against node (10-21, same area) | Pinned ..b955c8 (-57 dBm): 1.47 % lost, gaps > 0.3/0.5/1 s of 23/10/0. Pinned ..bd2b48 (-59 dBm): 0.26 % lost, 6/5/2, max 1.57 s. | bench log :229-233, :265-271 |

**What this means:**
- The stalls are **delivery delays on a shared channel**. They are not disconnections: the Pico stays associated and nobody kicks it.
- **Which node serves the car matters for both range and load.** The strongest node is not always the best. On 10-21, ..b955c8 lost about 5 times more than ..bd2b48, although ..bd2b48 had the two longest gaps.

---

## 3. Why the car fails today (the failure chain)

All times below are seconds after the start of the synchronized air capture. The Pico was on ..bd2b48 at -60..-62 dBm the whole time. Source: the analysis step, scripts in `assignments/assignment7/tools/wifi_survey/analysis_timeline/`. This is one 120 s capture with two episodes.

1. **A mesh episode starts (V).** Only at 0-15 s and 60-80 s did the serving node's backhaul interface exchange 4-address frames with the gateway's. These are the only bins with bad ping times (p50 51-1692 ms against 3-19 ms) and tick gaps over 0.6 s.
   - In those bins the node's own 1 Mb/s airtime was 16.5 % inside the downlink gaps, against 7.0 % overall. Other nodes' 1 Mb/s airtime was 23.1 % against 20.7 %, so it was not raised.
   - Whether this traffic *causes* the stall or only *marks* a mesh-wide event is open (I).
2. **Frames queue at both ends; air retries add little (V).**
   - During the episode the node held the Pico's frames before its first transmission for a median of 292 ms (max 2.3 s).
   - The Pico answered frames it had already acknowledged after a median of 264 ms (max 2.6 s).
   - Air retries added only 24 ms at p90.
   - One reason the Pico is slow to answer: when a send waits for bus credits, the cyw43 driver drops the received data packets it reads in the meantime (cyw43_ll.c:651-696, the drop at :679-682) (V).
3. **The supervisor starves itself of proof of life (V).**
   - The agent answered all 131 time syncs within 2 ms on the wire.
   - The send hold blocks syncs (pico_odometry.c:588), so only 2 syncs reached the wire between 68.06 and 72.25 s.
4. **The session is declared lost (V).** At about 72.57 s the 4 s rule fired (`SESSION_LOST_MS 4000`, pico_odometry.c:118; test at :606-607). Up to then the Pico's uplink had never been silent at the wire for more than 1.36 s, and ping replies never paused for more than 2.07 s.
5. **Teardown makes it worse (V).**
   - `entities_destroy` sends DELETE (pico_odometry.c:394-412), so the agent drops the client.
   - Each reconnection ping allows only 100 ms (:634), and pings failed until 74.96 s.
   - The first re-creation stalled and failed after 4.6 s. Each entity has a 1 s creation timeout, and session creation makes up to 10 attempts of 1 s each (libmicroros config).
   - The second re-creation took 0.77 s. Telemetry came back at 81.92 s, **disarmed** (:648-651).
6. **Result:** about 1.4 s of real stall became **9.4 s of silence plus a manual re-arm**.
7. **Build I's 23-34 s outage is the next rung of the same ladder (I, by size).**
   - A forced Wi-Fi rejoin after 15 s with no agent (`REJOIN_AFTER_MS`, :122, :624-630).
   - Then leave, a directed all-channel scan of about 0.7 s, and a rescan (wifi_link.c:228-232).
   - Then pin misses with back-off of 0.5, 1 and 2 s (:292-293), and after 3 misses a fallback join of about 5.8 s (:244-247).
   - Then another rebuild, because the join count changed (pico_odometry.c:606).
8. **Why the pinned node is weak at that spot (V plus I).** The pinned node (`..bd2b48`) is strong when the car is beside the development machine and weak at the floor spot, so at the floor spot the car is at the edge of its range (-61 dBm even on 10-21; bench log :773-775). Its radio also sends long 1 Mb/s mesh bursts toward the gateway (I: possibly measurement traffic). Which room that gateway is in is not in this public copy.

Motor safety held throughout: the wheels stop through the 500 ms timeout and the 600 ms deadman whatever the network does (drive_control.c:41, :114-129) (V).

---

## 4. The solution

### 4.0 Design at a glance

**Starting point.** This design starts from the "chip-roam" design, which scored best on feasibility and safety (7/10) and tied for the best average. It applies every must-fix from both judges. Grafted from the other two designs:
- From "robust-hybrid":
  - the radio token and its guard counter;
  - the command quarantine;
  - the beacon meter;
  - the strict agent-lost rule;
  - a low chip trigger;
  - parked host REASSOC.
- From "host-roam":
  - the watchdog choice while the link is busy;
  - settle-before-join;
  - the per-node service record;
  - break-before-make roams;
  - desk unit tests.

| Layer | Who | Does | When |
|---|---|---|---|
| Motors | drive_control.c (unchanged) | 500 ms command timeout, 600 ms deadman interrupt | always |
| Emergency roaming | chip firmware (roam_off 0, from J2) | roams on beacon loss, deauth, RSSI < -78 dBm | any time, including while driving |
| Node choice and proactive roaming | host (`wifi_roam.c`) | picks the node at every join (J2); moves the car to a better node (J3) | parked only |
| Link recovery | host (`wifi_link.c`) | grace, revival, leave and rejoin with back-off | wheels stopped |
| Session | host (`pico_odometry.c`) | keeps the micro-ROS session through stalls and rejoins; disarms after 3 s of silence | always |
| Visibility | host (`wifi_events.c`) | event tap that costs no ioctls, plus telemetry layout 6 | always |

### 4.1 Rules for every stage

1. **Motors.** `drive_control.c` is not touched:
   - `DRIVE_TIMEOUT_MS 500` (:41), enforced at :422-428;
   - the overdue-timeout stop (:382-386);
   - the 600 ms deadman in a 10 ms timer interrupt at priority 0x80 (:108-129, :371).

   The stale-command guard (`CMD_MAX_AGE_MS 300`, pico_odometry.c:130, :258-275) is unchanged.
2. **No radio ioctl while driving,** as today (wifi_link.c:432-434, pico_odometry.c:748-750). A new guard counter, `ioctl_while_run_watchdog`, must read 0 in every test.
3. **At most one blocking radio operation per main-loop pass** (the radio token, J1). The one exception is `cyw43_wifi_join`, about 11 ioctls inside one driver call (cyw43_ll.c:2051-2177). It runs only with the link down, the wheels stopped and the 16 s watchdog armed.
4. **Blocking leave and join wait until the wheels have stopped** (J1). Today `go_backoff` calls `cyw43_wifi_leave` at once (wifi_link.c:278-284).
5. **Watchdog:** 16 s whenever the link is not UP or a roam step is running, 8 s while parked, 2 s while driving. The values in safety.h:43-49 are unchanged.
6. **Code conventions** (AGENTS.md §5):
   - every changed block carries `ADDED for Build J (2026-10-xx; AI-assisted: Claude Opus 5.5 via Claude Code)`;
   - upstream approaches are re-implemented, not pasted, and named in comments.
7. **Rollback:**
   - `WIFI_ROAM_MODE 0` gives Build I behaviour (pinned, roam_off 1);
   - every UF2 is kept in `~/fw_builds_m7/` and recorded in the bench log with its hash;
   - Build I is `buildI_b809f95f`.

---

### 4.2 Build J0: observe only (behaviour stays Build I)

> **As built, 2026-10-24 (after an adversarial code review: 30 of 31 findings confirmed and fixed).** Differences from
> the plan in 4.2-4.3 and 4.9:
> - **Agent-lost check corrected.** The premise "the agent answers pings even for a client it no longer knows" is
>   right on the wire but wrong for rmw: with a session open, `rmw_uros_ping_agent` returns OK only for an in-session
>   pong (Micro-XRCE-DDS-Client session.c, PONG_IN_SESSION_STATUS), and an agent that lost the session answers INFO with
>   implementation status 0, which rmw reports as a failed ping. So: ping OK = the session is alive; an INFO with
>   status 0 (read in `picow_udp_receive`) = the agent lost the session, and two such pongs at least 2 s apart within
>   10 s rebuild it; no reply = a link problem, no sample. INFO replies with status 0 never count as proof of life, and
>   the probe sends no time sync of its own.
> - **Disarm latch.** A gap of 3 s or more is also detected when its datagram arrives (a latch in the transport,
>   checked in the supervisor and at the top of `cmd_vel_callback`), so a gap that ends inside a blocking call still
>   disarms.
> - **Quarantine** starts at the first command processed after a gap of 1.5 s or more and stays open while held
>   datagrams wait in the receive queue.
> - **Send hold:** a fast send ends it; driving caps it at 1 s. QUIET starts at 1.5 s, not 1 s.
> - **Layout 6 is the as-built 69-field J0/J1 map** (`pico_odometry.c` TK_*, decoded by `tools/diag_run.py` and
>   `tools/wifi_survey/capture/link_listen.py`), not the 77-field plan in 4.9. The `counters` beacon meter, the TX retry
>   rate and the probe table are deferred (the counter offsets are unverified); the guard counter is field 68
>   (`TK_RADIO_GUARD`). J2 will extend the layout as 7.
> - **J0 vs Build I:** J0 adds only observation (event tap, read-backs at boot, counters, the radio guard, a validated
>   event-mask write enabling the chip's ROAM event); its join path, session rules and watchdog use are Build I's.

**Why.** Before changing behaviour, J0 measures what the chip actually does. It answers four questions:
- Which roam knobs does the 7.95.49 ROM have?
- Do the floor-spot stalls come with link-downs, beacon loss or kicks?
- How often does the driver hit its 1 s credit timeout?
- What are the beacon rate and the TX retry rate?

J0 also gives the J1 tests their telemetry.

| File | Change | API and driver source (v1.1.1 unless marked) |
|---|---|---|
| `cyw43_hook.h` (new) | `#pragma once`, then inside `#ifndef __ASSEMBLER__` one prototype: `int car_cyw43_printf(const char *fmt, ...) __attribute__((format(printf, 1, 2)));` | The builder compiles with arm-none-eabi-gcc 10.3.1. An implicit declaration is a warning there and would break the 0-warnings gate (judge, verified). |
| `CMakeLists.txt` | Add `wifi_events.c wifi_radio.c` to `add_executable` (:29-40). Then `target_compile_definitions(pico_odometry PRIVATE $<$<COMPILE_LANGUAGE:C>:CYW43_PRINTF=car_cyw43_printf>)` and `target_compile_options(pico_odometry PRIVATE "$<$<COMPILE_LANGUAGE:C>:SHELL:-include ${CMAKE_CURRENT_LIST_DIR}/cyw43_hook.h>")`. | `CYW43_PRINTF` is defined only `#ifndef` (cyw43_config.h:153-156). The SDK's fallback does nothing once it is defined (pico-sdk cyw43_configport.h:205-212). The driver .c files are INTERFACE sources compiled in our target (pico-sdk pico_cyw43_driver/CMakeLists.txt:27-33). The C-only generator expression matters: this target also compiles 13 `.S` files and 1 `.cpp`, and an unguarded `-include` breaks the `.S` files (judge, reproduced). |
| `wifi_events.c/.h` (new) | **Event tap.** `car_cyw43_printf` compares `fmt` (with `strcmp`) against the driver's three event-dump formats `"[% 8d] ASYNC(%04x,"`, `"%s"` or `"%u"`, and `",%u,%u,%u)\n"`, and reads the arguments with `va_arg`. It does no formatting and no USB output. Event names map back to numbers through a re-implemented copy of the 13-entry name table. **ESCAN_RESULT (69) is only counted, never queued**, so a scan cannot overwrite AUTH, LINK and PSK_SUP (judge must-fix). Other events go into a 32-entry ring of `{ms, type, flags, status, reason}`; an overrun drops the newest entry and is counted. The warnings `"[CYW43] STALL(%u;%u-%u): timeout\n"`, `"[CYW43] do_ioctl(%u, %u, %u): timeout\n"` and `"[CYW43] send_ethernet failed: %d\n"` are counted, then forwarded with `vprintf` as today; every other print is forwarded too. `#if CYW43_VERSION != 0x010100` stops the build with `#error`. API: `wifi_events_drain(cb)`, `wifi_events_counts(&c)`. | Dump: cyw43_ctrl.c:315-331 (formats at :316, :322/:324, :326). It is called **before** the handler (:336-338). Name table :298-313. Warnings at cyw43_ll.c:691, :1183 and cyw43_lwip.c:97; prefix at cyw43_config.h:175-177. Version: cyw43.h:66-76. One producer at a time (the driver lock); the main loop drains the ring under `cyw43_arch_lwip_begin/end` (pico-sdk cyw43_arch.h:277, :300). Prototype: `assignments/assignment7/tools/wifi_survey/event_tap_prototype/hook.c` (16 of 16 events decoded). |
| `wifi_link.c`, `wifi_link_init` | After `cyw43_arch_enable_sta_mode` (pico_odometry.c:486), set `cyw43_state.trace_flags \|= CYW43_TRACE_ASYNC_EV`. Read back `bsscfg:event_msgs`, set bit 19 (ROAM), write it back, read it again. The driver's other cleared bits (20, 40, 44, 54, 71) stay cleared. Register `netif_set_link_callback(&cyw43_state.netif[CYW43_ITF_STA], …)`; the callback timestamps link down and up and touches RAM only. | `trace_flags`: cyw43.h:84, :111. Event-mask layout (18-byte name, u32 bsscfg 0, 19-byte mask, 41 bytes in all) and the driver's own clears: cyw43_ll.c:1893-1904. The handler ignores type 19 (cyw43_ctrl.c:333-438). The callback must be registered after `netif_add`, because `netif_add` clears it (lwIP netif.c:354; called at cyw43_lwip.c:203-205); `netif_set_link_callback` is at netif.c:1094-1101; `LWIP_NETIF_LINK_CALLBACK 1` is at lwipopts.h:38. |
| `wifi_radio.c/.h` (new) | **Length-checked sentinel helpers** replace `iovar_get_i32`/`iovar_set_u32`. Their 24-byte buffers (wifi_link.c:89-110) overflow for `roam_rssi_cancel_hysteresis` (28 + 4 bytes) and `bsscfg:event_msgs` (41 bytes) (judge must-fix). New: `radio_iovar(set, name, param, plen, out, olen)` with a static 64-byte buffer (900 bytes for `counters`). It refuses any request that does not fit, pre-fills with 0xA5, and treats a reply that leaves the buffer unchanged as "failed". It keeps an iovar-presence bitmask. **Probe table** (read-only in J0, one item per parked poll): see 4.9. **Beacon meter:** the `counters` iovar every 3 s while parked, accepted only if version == 10 and length ≥ 472. Deltas: `rxbeaconmbss`@344, `txframe`@4, `txretrans`@12, `txfail`@432, `txnoack`@456, `rxcrsglitch`@280, `rxbadplcp`@276. | `cyw43_ioctl` takes the driver lock (cyw43_ctrl.c:444-456). Encoding `cmd = WLC<<1 \| set` (cyw43_ll.c:1187-1190). The firmware status is ignored (:866-868), hence the sentinels. Maximum payload 2020 bytes (:762-764). GET_VAR 0x20c / SET_VAR 0x20f (cyw43_ll.h). The `counters` offsets were computed from WHD's `wl_cnt_ver_ten_t` (I; checked against version and length at run time). |
| `wifi_link.c`, `poll_one` (:445-504) | 9-slot cycle at the same 333 ms: RSSI, BSSID, counters, RSSI, BSSID, probe item, RSSI, BSSID, channel. Still one ioctl per poll, parked only (gate :432-443), and the slow-query pause stays (:501-503). **BSSID sentinel:** the buffer is pre-filled with 0xA5 instead of 0 (:459). A reply counts as *not associated* if the call returned 0 and the buffer is unchanged or all zero. A non-zero return (timeout) counts as *unknown*: it neither counts nor resets the zombie counter. Today line 474 resets the counter on a timeout. `ZERO_BSSID_LIMIT 3` is unchanged. | `cyw43_wifi_get_bssid` returns the ioctl result (cyw43_ctrl.c:679-684 → cyw43_ll.c:2189-2192). A NOTASSOCIATED reply leaves the buffer as it was (research; L). |
| `picow_udp_transport.c/.h` | In `picow_udp_receive` (:8-37): stamp `volatile last_rx_ms` and `rx_count` **before** the queue-full test (:23-25), count drops, and track the longest completed silence. In write: count `udp_send` failures. Getters: `picow_udp_last_rx_ms()`, `_rx_count()`, `_rx_drops()`, `_tx_errors()`, `_silence_max_take()`. | The pcb is connected to the agent (:64-69), so lwIP delivers only datagrams from the agent's address and port (I, from lwIP's connected-pcb filtering). |
| `pico_odometry.c` | Layout 6 (4.9): extend the enum after `TK_CUTOFFS` (:93), set `TK_LAYOUT_VERSION 6` (:96), fill the fields in `fill_diag_fields`. The 1 Hz log (:752-799) prints the drained events, e.g. `ev LINK down rsn 1`, with BSSIDs as their low 3 bytes. Behaviour is otherwise unchanged. | Indices 0-48 stay unchanged; `odometry_node.py` reads only `data[0..1]`. |
| `safety.h` (:27-38) | Add `PH_RADIO_CFG = 24`. A hang shows as boot report 1424. | Report format 1000 + 100 × kind + phase (safety.h:53). |
| `tools/diag_run.py`, `link_listen.py`, `link_gate.py`, `tick_times.py` | Decode layout ≥ 5 and print the per-run Wi-Fi summary: events, kicks, link-downs, credit and ioctl timeouts, beacon rate, retry rate, and the probe table. | — |

---

### 4.3 Build J1: session tolerance, still pinned (WIFI_ROAM_MODE 0, roam_off 1)

**Why.** This stage alone removes the 1.4 s → 9.4 s amplification and the 23-34 s rung. Every reviewer called it the decisive robustness gain. It keeps the pin, so its effect is measured on its own.

**Session supervisor.** `session_supervise()` replaces pico_odometry.c:579-664.

Silence `s` is measured from the latest of three things:
- any agent datagram (`picow_udp_last_rx_ms()`);
- a late TIMESTAMP reply (as today, :582-587);
- cmd_vel DATA (:256, :602-605).

| State | Entered when | What happens |
|---|---|---|
| ACTIVE | s < 1 s | Syncs every 1 s with the 50 ms window, as today (:116, :419). |
| QUIET | 1 s ≤ s < 3 s | Sync retries back off 250 → 500 → 1000 ms (today a fixed 250, :117, :600). A sync held by the send hold waits at most 1 s (`SYNC_HOLD_MAX_MS`; today it can wait without limit, :588). While parked, a lighter load: wheel_ticks every 500 ms instead of 100 (:716-720), heading skipped (:723-743), radio polling cut to one ioctl per 1.5 s alternating BSSID and counters, and none at all if a credit timeout was counted in the last 1 s. |
| SILENT | s ≥ 3 s | **Disarm:** `drive_control_stop()`, `drive_armed = false`, `need_arm_marker = true`, `TK_FLAGS` bit 13 set, disarms counted. The session is kept. |
| SUSPENDED | the link is not UP | Session objects are kept. No syncs and no publishes (they would fail with ERR_RTE); `spin_some` still runs. |
| LOST → rebuild | s ≥ 20 s (`SESSION_LOST_MS` 4000 → **20000**, :118), **or** the netif IP differs from the session's IP, **or** the agent-lost check fires | Destroy, ping, create, as today (:612-663). The first command after a rebuild still needs the arm marker (:648-651). |

The terms `!link_up` and `wifi_link_joins() != session_joins` are removed from the loss test (:606). A rejoin that keeps the IP keeps the session. The fixed client key (:302-310) and the fixed UDP port 8889 (picow_udp_transport.h:12) keep the agent's mapping (I).

**Agent-lost check** (strict form; must-fixes from both judges). It runs only when all of these hold:
- at least 3 unanswered syncs in a row;
- at least 6 s since the last answered sync;
- `rmw_uros_epoch_synchronized()` is false, so no late reply arrived;
- the link is up;
- the car is not DRIVING;
- the previous check was at least 2 s ago.

One positive sample is `rmw_uros_ping_agent(200, 1)` answered, then `rmw_uros_sync_session(200)` unanswered. **Two positive samples at least 2 s apart, within 10 s,** trigger a rebuild. Why this works: the agent answers pings even for a client it no longer knows, but drops its TIMESTAMP requests (Micro-XRCE-DDS-Agent Processor.cpp:136-181; pico_odometry.c:114-115).

*Design detail:* liveness stamping is paused while the probe's own ping is in flight (a flag read by `picow_udp_receive`). Otherwise the ping reply would itself count as proof of life.

**Command quarantine** (graft). When a datagram ends a silence of at least 1.5 s, `quarantine_until = now + 250 ms`. While it is active, `cmd_vel_callback` (:253-290) drops non-zero *unstamped* commands and counts them. Zero commands always stop the car, and stamped commands keep their age guard. This covers the gap the 3 s disarm leaves: unstamped commands skip the age check today (:276-278).

**Send hold.** It becomes adaptive: 500 ms, doubling on each consecutive stall up to 4 s while parked or 1 s while driving, and reset after 5 s without a stall (:164-178).

**Wi-Fi link supervisor (`wifi_link.c`).**
- **Signature change:** `wifi_link_update(now_ms, motors_idle)`, called with `last_status != DRIVE_STATUS_DRIVING` (pico_odometry.c:572). `lose_link` (:296-307) now only enters `LINK_LOST_PENDING`. The leave and the netif-down of `go_backoff` (:278-294) run on the first call with the wheels stopped; after a real loss the 500 ms timeout has already stopped them.
- **Watchdog fix** (judge must-fix 1). A new `wifi_link_busy()` returns true while the state is not UP, in grace, lost-pending, or in a roam step. The loop's choice (:557-563) becomes `want = busy ? WATCHDOG_CONNECT_MS : parked ? WATCHDOG_PARKED_MS : WATCHDOG_RUN_MS`, re-armed when it changes. `start_join` (:224-274) arms `WATCHDOG_CONNECT_MS` itself. Why: once the session survives a link loss, today's loop would re-arm 8 s or 2 s over the 16 s that `go_backoff` arms (:280), just before an 11-ioctl join.
- **One-ioctl settings applier** (in `wifi_radio.c`). `on_link_up` (:309-328) no longer makes about 12 blocking calls in one pass. It queues these items, run one per pass with the token:
  1. `GET_PM` 0xaa, then `SET_PM` 0xad with 0 only if the reading was not 0;
  2. set interference mode (0x1a9), then read it (0x1a6);
  3. read back roam_off and the roam trigger.

  The full `cyw43_wifi_pm(CYW43_NONE_PM)` (7 ioctls, cyw43_ctrl.c:494) stays at boot only. The driver applies its default PM2 only when the first interface comes up (cyw43_ctrl.c:553-562) (V). The comment at wifi_link.c:318-319 should be corrected to say so.
- **Radio token** (graft). `wifi_radio_pass_begin()` runs at the top of each pass; `wifi_radio_token_take()` grants one radio operation (an ioctl, a leave/join, a scan start, the agent-lost ping) only when all of these hold:
  - the car is parked with the 8 s watchdog, or the 16 s watchdog is armed;
  - no send in this pass took 200 ms or more;
  - no slow-query pause is active.

  Any attempt under the 2 s watchdog increments `ioctl_while_run_watchdog`.
- **Forced rejoin from the session layer** (:621-630). It needs **radio evidence** that the association is dead, plus at least 30 s without any agent datagram (`REJOIN_AFTER_MS` 15000 → 30000). The evidence is one of:
  - 3 not-associated BSSID reads in a row;
  - a beacon delta of 0 over at least 4 s;
  - 3 ioctl timeouts in a row.

  `REJOIN_EVERY_MS 60000` is unchanged. A stopped agent or Spark therefore never causes a rejoin, and in mode 0 such a rejoin is not counted as a pin miss (:301-303).
- **Watchdog during a rebuild:** `entities_create` (:313-390) calls `safety_watchdog_feed()` between its steps. A slow but successful creation (up to 10 × 1 s for the session plus 13 × 1 s for entities) can no longer reach 16 s. There is no feed inside the transport, so real hangs elsewhere still reboot the board.
- **Receive queue:** `PICOW_UDP_RECEIVE_QUEUE_DEPTH` goes from 4 to 8 (picow_udp_transport.h:10; about 4 KB more RAM) **only if J0 counted drops**.

**Tools.** `diag_run.py` and `imu_bench.py` treat flags bit 13 like a disarm and halt, as they already do on a new session or a disarm (bench log :178-180). They must send the arm marker again afterwards.

---

### 4.4 Build J2: chip safety net plus host-chosen joins (WIFI_ROAM_MODE 1, WIFI_PIN_BSSID 0)

> **As built, 2026-10-24 (`buildJ2_b4298742`, after an adversarial review, 16 of 17 findings confirmed and fixed, and
> four fix-verification passes, 11, 4, 4 and 2 more fixed; not flashed yet).** Differences from the text below:
> - **Deferred to J3 or later:** REVIVE (`PH_LINK_REVIVE`) and the channel-6 measurement scan (`PH_CH6_SCAN`). The
>   probe items fullroamperiod, roam_nfscan, bcn_timeout and the TX-failure thresholds are not read. T6 shows whether
>   REVIVE is needed. J2 keeps the existing pin macro: `WIFI_PIN_BSSID 1` with roam mode 1 is allowed, and the pin is
>   simply not applied (`PIN_ACTIVE`), so `WIFI_PIN_NODE` becomes the +3 dB preference (`WIFI_PREFER_DB`).
> - **Settings order:** trigger, delta and period first. Then **roam_off 0 only if the trigger reads back -78**;
>   otherwise roam_off stays 1, as in J1, and wheel_ticks field 69 bit 3 (engine on) reads 0; a failed trigger read
>   leaves roam_off as it was. The parked check rotates six slots, one per poll: two trigger-then-roam_off slots (the
>   trigger read, and if needed rewritten, then roam_off judged from it; the second retries the first, J2-RG3-2),
>   delta, period, PM and interference. A slow or failed call ends its slot, marks the rotation incomplete and pauses
>   the check for 5 s (a flag plus a start time, wrap-safe; J2-RG-1, J2-RG3-4). An incomplete rotation keeps the
>   previous "as asked" verdict unless a read-back is known to differ, which clears it (J2-RG3-3). It runs after every chip roam and
>   about every 72 s, rewrites a drifted item (the trigger and roam_off up to twice per rotation), reads it back at
>   once and counts it, and counts failed calls like the normal poll. A complete rotation judges "as asked" (bit 2)
>   from its fresh read-backs (reviews J2-DRV-5, J2-R2, REG-1, REG-4).
> - **Grace:** 5 s, held up to **12 s** (not 15 s), so grace plus a host scan and join stays under J1's 20 s session
>   limit. It is held open only by a roam in progress or just done: ROAM_PREP, ROAM_START, ROAM status 0, or an AUTH
>   or PSK_SUP result (not the host join's own, which link-up clears). A failed ROAM does not hold it (J2-R1). **The
>   grace also ends as soon as the session has under 7 s left before J1's 20 s rebuild** (the host path's back-off,
>   scan and join), because a beacon loss reports LINK down about 8 s after the last beacon (FIXCHECK-J2-R1).
>   Only a grace that began with that much time left is cut; one that began with less keeps its base 5 s for the chip
>   and is never extended (J2-RG-3). **A BADAUTH while up gets the same grace (J2-DRV-1):**
>   v1.1.1 sets BADAUTH on any failed AUTH or 4-way handshake, including a chip roam attempt's, and only a later
>   AUTH 0 clears it.
> - **No chip-quiet wait before host joins (J2-DRV-2):** every way into BACKOFF passes the host's leave, so the chip
>   is no longer associated. The 10 s window now only holds the grace open.
> - **Zombie count:** reset by a *successful* ROAM, an AUTH 0 or a LINK up. A failed ROAM does not reset it (J2-DRV-3).
> - **Which node a loss blocks:** the node the car is known to be on. That is the host join's choice until a BSSID
>   read confirms it, and nobody after a chip roam until a read names the new node (J2-DRV-4, J2-ROAM-3, J2-R4); a
>   roam handled during a BSSID read makes that read the new baseline, counted once (REG-3).
> - **Join floor (J2-ROAM-6, FIXCHECK-J2-R3, REG-2, J2-RG-2), in `wifi_roam_choose`:** nodes below -78 dBm are left
>   out while an unblocked node at or above -78 is heard; when none is, the strongest unblocked node replaces the
>   score's pick if it is more than 10 dB stronger (where the chip's own roam would take it), and while the chip's
>   engine is on that may be a node blocked only for a lost link (the chip ignores host blocks), never one blocked for
>   a failed join (each reason has its own expiry, J2-RG3-1). Otherwise blocked nodes are chosen only when every heard
>   node is blocked.
> - **Service record (J2-ROAM-1/2, J2-R3):** a parked session hears from the agent only once per 1 s time sync. So a
>   stall is the silence **beyond the 1 s sync period**: an episode is ≥ 2 s of silence, and it charges its peak
>   minus 1.5 s, capped at 3 s per episode, to the node it began on. An episode is not charged when the link was
>   lost (that is the block's job), when the agent proved it had restarted, or across a session rebuild.
>   The first version counted the raw silence. Replayed on the 20-min J1 soak, it would have charged the healthy
>   pinned node 4.1 stall-s/min (the 12 dB cap); the fixed rule charges 0.
> - **Telemetry:** layout 7 as planned. Field 69 bit 3 = the chip's roam engine on (roam_off read 0). The 1 Hz
>   console line and `link_listen` name the build J2.

**Why.** The car needs to recover from a dead or very weak node even while driving, without leaving channel 6 for long at the spot that needs fixing. A trigger of -70 dBm with a 5 s period would keep the chip in roam-scan mode at a spot that reads -58..-77 dBm (judge must-fix). -78 dBm keeps the engine quiet except in real emergencies. The chip picks nodes by RSSI only, so the **host** picks the node at every join. An unpinned SSID join previously chose the busier ..b955c8 (bench log :187-205, confounded with the power source).

`wifi_link.h` gets `#error` if `WIFI_ROAM_MODE >= 1` is combined with `WIFI_PIN_BSSID 1`.

**Chip roam settings.** They are written at boot after PM and interference, re-checked after every join and roam (one item per pass), and re-read slowly about every 72 s while parked. A value that drifted is rewritten once and counted (wl 7.10 can change roam profiles at run time, `wlc_roam_prof_update`, wlc_assoc.c:8243; L).

| Knob | Value | Raw call | Default and source |
|---|---|---|---|
| roam_off | 0 | iovar, u32 | Build I writes 1 (wifi_link.c:118-120). WHD writes 0 at every join (whd_wifi_api.c:1785-1786). |
| Roam trigger | **-78 dBm** (A/B arms -75, -80) | set 0x6f, get 0x6c, 4-byte int32 | Firmware -75 (PR #151; the car read -75, bench log :187-188). |
| Roam delta | 10 dB | 0x73 / 0x70 | Firmware 20 (PR #151). |
| Roam scan period | 10 s | 0x77 / 0x74 | Firmware 10. |
| fullroamperiod | 300 s, only if a sentinel GET answers | iovar | wl 7.10 default 70 (wlc.h:335) (L) |
| roam_nfscan | 1, only if a GET answers | iovar | wl 7.10 does 3 full scans when a roam starts (`ROAM_FULLSCAN_NTIMES`, wlc.h:340) (L) |
| bcn_timeout | read only | iovar | expected 8 s (wlc.h:332) (L); A/B arm 6, never below 4 |
| txfail_roamthresh, txmin_roamthresh, roam_rssi_cancel_hysteresis | read only | iovar | A roam can also start on TX failure or minimum rate, not only on RSSI (wlc_assoc.c:8218, :8966) (L); judge must-fix |

v1.1.1 does not name the roam ioctl numbers. They come from cyw43-driver v2.0.0 (cyw43_ll.h:34-45) and WHD (WLC 54-59).

**What the chip will then do (L, wl 7.10).**
- It starts roam scans when the link's RSSI average drops below -78. The first scan is full; after that, partial scans of the roam-channel cache run every 10 s. Here the cache should hold channel 6 only (I).
- It stops roaming at the trigger plus 5 dB of hysteresis (wlc_assoc.c:8264-8299; wlc.h:341).
- A swing of more than 7 dB forces full scans (wlc_assoc.c:8235-8262; wlc.h:342).
- A candidate must be more than 10 dB better.
- On beacon loss it roams early and reports LINK down at bcn_timeout. On deauth or disassociation it also roams.
- A successful roam re-sends AUTH, LINK and PSK_SUP keyed. The driver completes its join state, and `netif_set_link_up` does nothing because the link is already up (cyw43_ctrl.c:383-438; lwIP netif.c:1024) (V). So there is **no DHCP and no socket change, and the session is untouched.**

**Joins** (`start_join`, :224-274; the pin logic at :229-247 is used only in mode 0):
1. The existing directed all-channel scan (`scan_for_best_node`, :191-219). The link is down at this point, so leaving the channel costs nothing.
2. Each heard node of our SSID is scored: `scan RSSI + prior(node) − service penalty(node) − (blocked ? ∞ : 0)`. The car joins the best one **by BSSID and channel**, as today (:255-257).
   - `WIFI_NODE_PRIORS` lives in the uncommitted `wifi_config.h` as `{low24, dB}` pairs. A suggested start is ..b955c8 at -6 dB (from 10-21), to be revised with J0/J1 data.
   - `WIFI_PREFER_NODE` (+3 dB) replaces the pin.
3. If the scan heard none of our nodes: a **hinted SSID join**, `cyw43_wifi_join(…, bssid = ff:ff:ff:ff:ff:ff, home channel)`. It sends the `join` iovar with one chanspec, `0x1000 | ch` (cyw43_ll.c:2143-2169). That the chip treats a broadcast BSSID as "any node of this SSID" is an inference; Linux brcmfmac uses the same form.
4. If that fails: `cyw43_arch_wifi_connect_async`, an all-channel `WLC_SET_SSID` (pico-sdk cyw43_arch.c:96-98; cyw43_ll.c:2173). Steps 3 and 4 alternate.

**Link states in mode 1.**
- **GRACE.** The status reads JOIN or NOIP while the link is UP. Mode 1 waits `ROAM_GRACE_MS 5000` (mode 0 keeps `LINK_GRACE_MS 3000`, :35, :396-408) to give the chip time to reassociate.
- **REVIVE** (`WIFI_LINK_REVIVE 1`). Problem: in v1.1.1, if beacons come back without a reassociation, the netif never comes back. LINK down leaves the join state alone, and a later LINK up without AUTH and KEYED never completes it (cyw43_ctrl.c:402-415, :434-438) (V). The fix: when the tap sees LINK up (flags bit 0) with no AUTH since the last LINK down, the host waits 300 ms. Then, in the next pass with the token (16 s watchdog, phase `PH_LINK_REVIVE`), it reads the BSSID once with a sentinel. If it equals the BSSID from before the drop, it calls `netif_set_link_up` under `cyw43_arch_lwip_begin/end`. lwIP then runs the DHCP reboot and sends a gratuitous ARP (netif.c:1018-1035). Inference: the keys are still valid on this path; test T6 checks it.
- **Zombie check.** `ZERO_BSSID_LIMIT 6` in mode 1, because a chip roam leaves the BSSID unset while it runs. Any ROAM, AUTH or LINK-up event resets the count.
- **lose_link** records the cause from the tap (beacon loss = reason 1, deauth, disassoc) and blocks the lost node for 60 s for the next host join.
- **Driver DISASSOC.** It zeroes the driver's state (cyw43_ctrl.c:353-355), so recovery is the host rejoin path.

**Roam handling and the gratuitous ARP.**
- A drained ROAM (status 0) event, or a BSSID(125) event *after the first link-up and with a changed BSSID* (judge minor fix), counts as a chip roam. The host then:
  - restarts the node dwell timer;
  - queues the post-roam checks (GET_PM, interference, roam_off);
  - prints a console line: `Wi-Fi: chip roam ..AAAAAA -> ..BBBBBB, reason R, RSSI x -> y`;
  - queues a gratuitous ARP. The new `wifi_link_service(now, sends_allowed)` sends the ARP (`etharp_gratuitous` under the lwIP lock) on the next pass whose sends are not held, and counts it with `note_send`.
- The 1 Hz BSSID poll stays as a fallback for node changes the tap did not explain. It also sends a gratuitous ARP (:477-484).

**Which engine wins** (judge must-fix). The chip may roam at any time. The host starts no scan, join or roam step within 10 s of chip roam activity in the tap: ROAM_PREP (32), ROAM_START (37) and ROAM (19) of any status. Events 32 and 37 are not masked (cyw43_ll.c:1896-1901) (V); their meanings are taken from the Broadcom numbering (L).

**Per-node service record** (`wifi_roam.c`, new; graft from host-roam). While parked on node n, the host adds up `stall_s`: the silence beyond 0.5 s in each episode of 1 s or more. Each minute it updates an average of stall-seconds per minute.
- The service penalty is min(12 dB, 3 dB × stall-s/min). It is halved until the node has 2 min of service.
- The table lives in RAM, is reset at boot and is seeded from `WIFI_NODE_PRIORS`, so a reboot does not forget the busy relay (judge must-fix).

**Measurement-only channel-6 scan** (graft). Its only purpose in J2 is to fill the node table for telemetry; it makes no decisions. At most once per 60 s, parked, with the token, ACTIVE only, until test T7 passes (judge must-fix).
- **Buffer, 82 bytes:** `"escan\0"` followed by a `cyw43_wifi_scan_options_t`, 76 bytes with `channel_num` at offset 68 and `channel_list` at 72 (cyw43_ll.h:248-263). Fields:
  - version 1, action 1, sync_id n;
  - our SSID, bssid ff×6, bss_type 2;
  - scan_type 1 (passive), passive_time 220 ms (over two 102.4 ms beacon intervals);
  - nprobes, active_time and home_time -1;
  - channel_num 1, `channel_list[0] = 0x1000 | home channel` (0x1006).
- **Starting it:** under `cyw43_arch_lwip_begin/end`, set `cyw43_state.wifi_scan_env`, `wifi_scan_cb` and `wifi_scan_state = 1` (public fields, cyw43.h:114-117), exactly as `cyw43_wifi_scan` does (cyw43_ctrl.c:587-611). Then call `cyw43_ioctl(&cyw43_state, CYW43_IOCTL_SET_VAR, 82, buf, CYW43_ITF_STA)`. The driver's own scan sends the same iovar (cyw43_ll.c:2046), but overwrites the channel list and dwell times (:2032-2049).
- **Results:** status-8 events go to the callback; status 0 sets the state to 2 (cyw43_ctrl.c:340-352). Completion is read with `cyw43_wifi_scan_active()` (cyw43.h:327-329), which makes no radio call.
- **Timeout 820 ms:** reset `wifi_scan_state = 0` under the lock, send an escan abort (action 3; WHD whd_wifi_api.c, L) in a later pass, and count a failure.
- **Callback:** SSID match and home channel only; it keeps the maximum RSSI per BSSID in an 8-entry inbox, with no lwIP and no printf.
- **Never** during a join, `scan_for_best_node` or a REASSOC.
- **Expected cost (L, wl 7.10 wlc_scan.c:1882-1941):** a scan whose only channel is the home channel skips the PM=1 announcement, the TX suspend and the retune. T7 must confirm this.

`safety.h` adds `PH_LINK_REVIVE = 25` and `PH_CH6_SCAN = 27`.

---

### 4.5 Build J3: parked host roaming "whenever it helps" (WIFI_ROAM_MODE 2)

**Why.** The chip safety net only acts in emergencies. To move the car from ..bd2b48 at -66 dBm to ..b75a08 at -56 dBm, the host must decide. It does so only while parked, so a roam can never interrupt a drive.

**Scans** (parked, with the token, session ACTIVE, no chip roam activity in the last 10 s, no credit timeout in the last 1 s):
- every 60 s when the current node's RSSI average is at least -65 and its service penalty is 0;
- every 15 s when the average is below -65 or the penalty is above 0;
- on arrival: when the car is parked again after at least 2 s of driving, or when the RSSI average has dropped 6 dB or more since the last scan;
- decisions use a pair of scans 2 s apart, merged per BSSID;
- if 2 passive scans in a row hear at most 1 node, the next one is active (40 ms, 2 probes);
- **none while driving**;
- the scan before a host join becomes the channel-6 scan. The all-channel scan is used only if the channel-6 scan hears none of our nodes.

**Node table** (8 entries; the full BSSID is kept in RAM only, and only its low 24 bits are exported). Per node: scan RSSI average (α 0.25), seen in how many of the last 3 scans, last seen, prior, service penalty, block level and expiry, time left. **The current node is measured in the same scans** as the candidates (Zephyr does the same; if the current node is missing, `WLC_GET_RSSI` is used).

**Score:** `S(n) = RSSI_avg(n) + prior(n) − Psvc(n) − Pret(n)`. Pret is 5 dB for 20 min after leaving a node.

**Gates** (all must hold):
- parked for at least 3 s;
- session ACTIVE, with an agent datagram less than 1 s ago;
- at least 60 s on the current node;
- at least 120 s since the last host attempt;
- the candidate was heard in at least 2 of the last 3 scans, the newest no more than 10 s old;
- the candidate is not blocked and was not left within the last 5 min;
- no chip roam activity in the last 10 s;
- at least 10 s since the session was (re)created;
- **rate limit:** while the car is stationary (the current node's RSSI within ±6 dB of its value at the last roam), at most **2 host roams per 30 min**; otherwise at most 6 per hour.

**Rules** (the first match wins):
- **R1, weak signal:** the current average has been below -70 dBm for at least 20 s, S_alt ≥ S_cur + 8 dB, **and the raw RSSI is at least 5 dB better.** These numbers follow Apple's rule of -70 dBm and 8 dB.
- **R2, big win:** S_alt ≥ S_cur + 12 dB at any level, and the raw RSSI is at least 5 dB better. Apple uses 12 dB when idle.
- **R3, node-specific service problem:** the current node's service penalty is at least 6 dB (2 or more stall-seconds per minute over at least 3 min parked). The candidate must have *its own* better record (a measured penalty at least 6 dB lower from at least 2 min of service, or a configured prior), and an RSSI of at least -70 dBm and no more than 3 dB below the current node. At most one R3 roam per 30 min.
  - Why this rule needs evidence about one node: mesh-wide episodes hit every node, so a stall alone is no reason to move (judge must-fix).
- **Dead link** (zombie check, a beacon delta of 0 over at least 4 s, or LINK down without recovery). This is recovery, not a policy roam. The host joins the best fresh, unblocked node by method B at once, ignoring dwell and rate limits but not blocks.

**Execution, method B: break-before-make (the default).**
1. Enter `LINK_ROAMING`. The quarantine is active, sends are held for 300 ms, the watchdog is 16 s and the phase is `PH_ROAM = 26`.
2. **LEAVE:** `cyw43_wifi_leave` (cyw43_ctrl.c:666-669) plus `netif_set_link_down`, as at wifi_link.c:287-289. This is not counted as a loss.
3. **SETTLE:** wait at least 150 ms and at most 1 s, until `cyw43_wifi_link_status` reads DOWN (cyw43_ctrl.c:613-630). A late DISASSOC would otherwise wipe the new join (cyw43_ctrl.c:353-355). Then one GET_BSSID probe must answer within 20 ms, which shows the bus is healthy.
4. **JOIN:** `cyw43_wifi_join(ssid, key, CYW43_AUTH_WPA2_AES_PSK, target, home channel)`, which sends a `join` with one chanspec (cyw43_ctrl.c:635-664; cyw43_ll.c:2143-2169).
5. **JOIN_WAIT:** 6 s, with the JOINING rules (wifi_link.c:352-389). On UP, lwIP keeps the IP, runs the DHCP reboot and sends its own gratuitous ARP (netif.c:1018-1035; the checks are off at lwipopts.h:54-55). **The session is kept** (J1).
6. **On failure:** block the target, rejoin the previous node by BSSID, and then fall back to the normal back-off path.

**Execution, method A: in-place REASSOC (Build J3b, only after T8a passes 20 of 20).**
- The call is `cyw43_ioctl(&cyw43_state, 0x6b, 16, p, CYW43_ITF_STA)` with `p = {bssid[6], u16 bssid_cnt 0, i32 chanspec_num 1, u16 0x1006, u16 pad}`. This is WLC_REASSOC 53 with `wl_reassoc_params_t`, as in the WHD headers.
- In wl 7.10 this is a directed reassociation: it has no roam_off check, allows roaming to the same node, and is queued if the chip is busy (wlc.c:14543-14594; wlc_assoc.c:1329-1384) (L).
- The host confirms by reading the BSSID every 250 ms for up to 3 s. Then it sends a gratuitous ARP, because the netif sees nothing (netif.c:1024), and runs the post-roam checks.
- If the timeout passes with the link still up, the car stays where it is and the target is blocked. If the link goes down, the host switches to method B toward the same target.

**After a roam.**
- **Probation, 120 s:** roll back once if the new node's sync-miss rate is at least 1.3 times the old node's over its last 5 min, or if a silence longer than 4 s occurs. The new node then gets 6 dB of penalty and a 600 s block.
- **Blocks:** a failed roam blocks the target for 300 s, tripled on each repeat up to 1800 s. Block levels decay after 30 min without a failure. **The last usable node is never blocked.** The levels follow the escalation idea in wpa_supplicant (10 s up to 1800 s) and ESP-IDF (300 s after 3 failures).
- **Uncommanded node changes:** chip roams, and the driver's own rejoins by SSID after PRUNE, ICV or PSK timeouts (cyw43_ctrl.c:240-254, :366-372, :416-432). The host adopts the new node, sends a gratuitous ARP and starts probation without a roll-back, with the reason recorded as UNCOMMANDED.

---

### 4.6 Build J4 (optional, low priority): BTM acceptance

The firmware is built with `wnm` and `bsstrans` (firmware strings) (V). The SSID advertises BSS Transition (survey:15). eero sent no BTM to anyone in 330 s of captures (V).

J4 would set `wnm |= 0x1` and `wnm_bsstrans_resp = 2` (ROAM_IF_PREF: move only when the request names a candidate) (wl wlc_wnm.c:479, :1302-1320; L). Keep it only if the A/B shows no harm.

Risks:
- eero might steer the car to a busy relay.
- A "disassociation imminent" request makes the firmware disassociate itself, which drops the driver's state and leads to the slower host rejoin (cyw43_ctrl.c:353-355).

---

### 4.7 Roaming policy summary

| Question | Answer |
|---|---|
| When to scan | Never while driving. Parked: every 60 s on a good node, every 15 s on a marginal or penalised node, on arrival, and never within 10 s of chip roam activity. In J2 the channel-6 scan is limited to once per 60 s until T7 passes. |
| When to roam (host, J3) | Parked only. R1 (below -70 dBm for 20 s, 8 dB score and 5 dB RSSI better), R2 (12 dB score and 5 dB RSSI better), or R3 (node-specific service evidence). |
| When to roam (chip, J2+) | Any time, in emergencies: RSSI below -78 dBm, beacon loss, deauth or disassociation, TX-failure or minimum-rate triggers (read back). Delta 10 dB. |
| Hysteresis | Host: 8 or 12 dB margins plus at least 5 dB raw RSSI; current node measured in the same scans; 5 dB return penalty for 20 min. Chip: 10 dB delta, and roaming ends at trigger + 5 dB. |
| Dwell and rate | At least 60 s on a node, at least 120 s between attempts, at most 2 per 30 min while stationary (6 per hour while moving), no return within 5 min, 120 s probation with one roll-back. |
| Blacklisting | 300 s → 900 s → 1800 s; lost node 60 s; probation failure 600 s; never all nodes. |
| Driving vs parked | Driving: only the chip safety net plus the timers; no host ioctl. Parked: the host scans and decides, one ioctl per pass. |
| BTM | Not advertised (wnm 0) through J3; opt-in in J4. |

### 4.8 Recovery ladder and outage budget

**The ladder, from mildest to most drastic:**
1. Wheels stop at 0.5 s (timeout) or 0.6 s (deadman).
2. QUIET at 1 s: syncs back off and the load drops.
3. SILENT at 3 s: the car disarms.
4. GRACE at 5 s (mode 1+): the chip has time to reassociate.
5. REVIVE once beacons return.
6. LOST-PENDING until the wheels have stopped, then leave and rejoin with back-off (0.5-8 s with jitter, unchanged).
7. Session rebuild only at 20 s, on an IP change, or when the agent is proven to have restarted.
8. Reboot after 90 s without a link (unchanged, wifi_link.h:37).

| Event | Expected outage (estimates, I) | Session | Arming |
|---|---|---|---|
| Delivery stall under 3 s | the stall itself | kept | armed; quarantine 250 ms if the stall was 1.5 s or more |
| Stall of 3-20 s | the stall itself | kept | disarmed; needs the marker |
| Chip RSSI or deauth roam | about 0.1-1 s (scan plus about 50-150 ms reassociation; AUTH to keyed took 46-48 ms on 7.95.49, issue #161) | kept | armed unless 3 s or more |
| Chip beacon-loss roam | about 4-6 s (half of bcn_timeout plus the scan) | kept | disarmed |
| Host method B roam (parked) | about 1-3 s link down | kept | disarmed if 3 s or more (parked anyway) |
| Host method A roam (J3b) | about 50-300 ms | kept | armed |
| Node unplugged, host path | 16 s or less | kept if the IP is unchanged and the outage is under 20 s | disarmed |
| Agent restarted | rebuilt about 8-10 s after the agent answers | rebuilt | disarmed |

### 4.9 Telemetry: `/pico/wheel_ticks` layout 6 (defined in J0, filled as the stages arrive)

> **Superseded for J0/J1:** the firmware sends the as-built 69-field layout 6 described in the note at the start of
> 4.2; this 77-field plan becomes layout 7 for J2.

`TK_LAYOUT_VERSION 6`, `TK_FIELDS 77`. Indices 0-48 are unchanged. Fields not yet used read `INT32_MIN`. The message grows by 112 bytes: about +5.6 kB/s at 50 Hz while driving and +1.1 kB/s at 10 Hz parked.

| # | Field | Content |
|---|---|---|
| 49 | TK_WIFI_STATE | bits 0-3 link state (0 backoff, 1 joining, 2 up, 3 grace, 4 lost-pending, 5 roaming); 4-7 session (0 active, 1 quiet, 2 silent, 3 suspended, 4 down); 8-9 roam mode; 10 tap alive; 11 event-19 unmask read back; 12 quarantine; 13 reduced load; 14 BTM advertised; 15 channel-6 scan verified |
| 50 | TK_AGENT_RX_AGE_MS | ms since any agent datagram |
| 51 | TK_RX_SILENCE_MAX_MS | longest completed silence since the previous message |
| 52 | TK_RX_DGRAMS | datagrams since boot |
| 53 | TK_UDP_DROPS | queue-full drops (0-15) \| udp_send errors (16-31) |
| 54 | TK_SEND_STALLS | sends of 200 ms or more (today console only, pico_odometry.c:785-795) |
| 55 | TK_DRV_TIMEOUTS | credit timeouts (0-9) \| ioctl timeouts (10-19) \| send_ethernet failures (20-29) |
| 56 | TK_EV_TOTAL | events parsed |
| 57 | TK_EV_OVERRUNS | ring overruns (0-15) \| ESCAN results mod 65536 (16-31) |
| 58 | TK_ROAMS | chip (0-9) \| host method B (10-19) \| host method A (20-29) |
| 59 | TK_ROAM_TRIES | ROAM(19) events of any status (0-15) \| host roam failures (16-31) |
| 60 | TK_ROAM_LAST | reason (0-7) \| status (8-15) \| age in s, capped at 32767 (16-30) |
| 61 | TK_LINK_DOWNS | LINK-down events (0-15) \| last reason (16-23) |
| 62 | TK_KICKS | DEAUTH_IND \| DISASSOC_IND << 10 \| DISASSOC << 20 |
| 63 | TK_KICK_LAST | 802.11 reason (0-15) \| event type (16-23) |
| 64 | TK_RECOVERIES | revivals \| gratuitous ARPs << 10 \| link-loss episodes the session survived << 20 |
| 65 | TK_DISARMS | silence disarms (0-15) \| quarantine drops (16-31) |
| 66 | TK_REBUILDS | by the agent-lost check (0-15) \| by 20 s of silence (16-31) |
| 67 | TK_BCN_RATE_X10 | own-node beacons per second × 10 (about 98 when healthy; -1 if unsupported) |
| 68 | TK_TX_RETRY_PM | Δtxretrans / Δtxframe × 1000 |
| 69 | TK_NODE_DWELL_S | seconds on the current BSSID |
| 70 | TK_NODE_SVC_X10 | current node's stall-seconds per minute × 10 |
| 71 | TK_ALT_BSSID_LOW | best alternative node (low 24 bits) |
| 72 | TK_ALT_SCAN_RSSI | its RSSI |
| 73 | TK_CUR_SCAN_RSSI | the current node in the same scans |
| 74 | TK_SCANS | completed (0-15) \| nodes heard in the last pair (16-23) \| failures (24-31) |
| 75-76 | TK_PROBE_ID / TK_PROBE_VAL | rotating probe table, one id per message |

`TK_FLAGS` bit 13 (new) means "disarmed by 3 s or more of agent silence". Bit 8 still means the arm marker is needed. Meanings sharpened:
- `TK_WIFI_JOINS` (33) counts host joins only.
- `TK_BSSID_CHANGES` (36) counts node changes found by polling.
- `TK_ROAM_OFF` and `TK_ROAM_TRIGGER` (45-46) are refreshed by every check, not only at start-up.

**Probe table ids.** `INT32_MIN` = absent or failed; `INT32_MIN + 1` = not read yet.
- **1-15, roam and radio settings:** 1 roam_off, 2 trigger, 3 delta, 4 scan period, 5 bcn_timeout, 6 fullroamperiod, 7 roam_nfscan, 8 roam_rssi_cancel_hysteresis, 9 txfail_roamthresh, 10 txmin_roamthresh, 11 wnm, 12 wnm_bsstrans_resp, 13 PM, 14 interference mode, 15 the event-mask byte for events 16-23 (bit 3 = event 19).
- **16-20, scan and counters read-backs:** 16 `counters` version << 16 \| length; scan times 17 (0x170), 18 (0x178), 19 (0x202) and 20 nprobes (0x17c).
- **21-26, bookkeeping:** 21 iovar-presence bitmask, 22 drift rewrites, 23 `ioctl_while_run_watchdog` (must be 0), 24 settings-queue backlog, 25 home channel, 26 last scan duration in ms.
- **32-63, node table** (8 × 4): low 24 bits; scan RSSI \| seen-of-3 << 8; prior + penalty in dB \| blocked << 8 \| failures << 16; service × 10.
- **64-79, the last 4 roam records** (4 × 4): rule \| outcome, from (low 24), to (low 24), duration in ms or a negative reason.

**Console.**
- At boot, one probe line, for example: `Wi-Fi radio (Build J2): PM 0; interference 3; ev19 on; roam_off 0; trigger -78 (asked -78); delta 10; period 10 s; bcn_timeout 8 s; fullroamperiod 300|absent; roam_nfscan 1|absent; wnm 0x0; tap v1.1.0 ok`.
- Each second, the drained events.
- One line per roam, block, revival and disarm.
- BSSIDs only ever appear as `..xxxxxx`.

**New boot-report phases:** 24 `PH_RADIO_CFG`, 25 `PH_LINK_REVIVE`, 26 `PH_ROAM`, 27 `PH_CH6_SCAN` (so 1424-1427 = a hang inside them).

### 4.10 Constants

| Constant | J0 | J1 | J2 | J3 | Was |
|---|---|---|---|---|---|
| WIFI_ROAM_MODE | 0 | 0 | 1 | 2 | — |
| roam_off / trigger / delta / period | 1 / read / – / – | same | 0 / -78 / 10 / 10 s | same | 1 / -75 read |
| SESSION_LOST_MS | 4000 | 20000 | 20000 | 20000 | 4000 |
| DISARM_SILENCE_MS / quarantine | – | 3000 / 250 ms after a silence of 1.5 s or more | same | same | rebuild at 4 s |
| Agent-lost check | – | ≥ 3 misses, ≥ 6 s, 2 samples ≥ 2 s apart | same | same | — |
| Sync retry / maximum hold | 250 / ∞ | 250 → 500 → 1000 / 1000 ms | same | same | 250 / ∞ |
| REJOIN_AFTER_MS | 15000 | 30000 + radio evidence | same | same | 15000 |
| Grace | 3000 | 3000 | 5000 | 5000 | 3000 |
| ZERO_BSSID_LIMIT | 3 | 3 | 6 (reset by events) | 6 | 3 |
| Scan cadence | – | – | ≤ 1/60 s, measurement only | 60 s / 15 s / on arrival | — |
| Host roam dwell / interval / maximum | – | – | – | 60 s / 120 s / 2 per 30 min | — |
| Unchanged | JOIN_TIMEOUT_MS 15000, JOIN_SETTLE_MS 500, BADAUTH_GRACE_MS 3000, back-off 0.5-8 s, RADIO_POLL_MS 333, SLOW_QUERY_US 100000 / SLOW_PAUSE_MS 5000, WIFI_REBOOT_AFTER_MS 90000, watchdogs 2/8/16 s, SEND_STALL_US 200000, SYNC_PERIOD_MS 1000, 50 ms sync window, CMD_MAX_AGE_MS 300, DRIVE_TIMEOUT_MS 500, deadman 600 ms | | | | |

---

## 5. Test plan with pass criteria

> **As built for J0/J1 (2026-10-24):** read "guard id 23" as wheel_ticks field 68 (`TK_RADIO_GUARD`, radio calls
> started while the drive status was DRIVING; must stay 0), "TK_RECOVERIES / session kept" as field 65
> (`TK_SESSION_KEPT`), and "probe table complete" as the boot console line plus fields 66-67 (roam delta and period,
> PM). The beacon rate and TX retry rate are deferred with the `counters` meter, so T1/T4 criteria that need them wait
> for a later build; LINK-down reasons (field 58) and kicks (59-60) cover the J0 question about beacon loss.

**Conditions for every run:**
- The car is on its tape mark with the same heading, the Pico on the power bank, and the battery switch off unless the test drives.
- Runs are listen-only unless stated. **The wheels are never turned by hand;** wheel checks are powered stand runs.
- A 5 Hz ping from the Spark runs alongside.
- Node and RSSI are taken from telemetry.
- Comparisons alternate A-B-A-B in the same sitting (3 pairs of 5 min within about 40 min), because RSSI at "the same spot" varied by 10-20 dB on 10-23.
- Air checks use the existing channel-6 monitor scripts. They need root on the Spark, as the 10-23 captures did, and report counts only, never MACs.
- Each stage is reviewed adversarially before it is flashed, is flashed near the Spark only with your go-ahead, and gets its own bench-log section (UF2 name and hash, probe table, result tables).

| Test | Stages | Pass criteria |
|---|---|---|
| **T0 desk** | all | 0 warnings in every mode (0-2). The version guard and the static asserts (76-byte options struct, 16-byte reassoc parameters) compile. The `hook.c` harness decodes 200 random events plus the 3 warnings exactly, counts ESCAN results without queuing them and counts overruns. The length-checked helper refuses oversize names. J3 adds the decision unit test on synthetic sequences: no roam for 9 dB when healthy; R1 at -71 and 8+5 dB; no R3 without node-specific evidence; dwell, interval and the 2-per-30-min limit respected; blocks escalate; never all nodes blocked; no A-B-A within 5 min. |
| **T1 stand boot** (Spark USB, about -42 dBm) | all | The probe table is complete. Every SET that answered reads back its value; a mismatch drops that knob. The tap shows the boot join as AUTH status 0 → LINK flags 1 → PSK_SUP status 6 within 3 s. `TK_EV_TOTAL` > 0 and overruns 0. Guard id 23 = 0. `TK_RADIO_MAX_US` p99 ≤ 10 ms. 10 min parked: 0 rebuilds, 0 host joins, 0 reboots. J2 adds: event-19 bit set; `TK_ROAM_TRIES` 0 above the trigger. |
| **T2 session tolerance** (stand) | J1+ | (a) `docker pause` the agent for 10 s: `TK_SESSIONS` unchanged, bit 13 set at about 3 s, telemetry back within 1 s of the unpause, the marker re-arms. (b) `docker restart` the agent: rebuilt within 10 s of the agent answering, no Pico reboot, no Wi-Fi join, disarmed until the marker. (c) Agent stopped for 2 min: no Wi-Fi rejoin (`TK_WIFI_JOINS` unchanged; beacon rate about 90 or more), no reboot, rebuilt within 5 s of the agent's return. (d) **A real link outage of 15 s or more** (a metal tin over the car, or carried out of range; judge must-fix): session kept (IP unchanged), `TK_RECOVERIES` session-kept +1, disarmed, re-arm works. (e) `imu_bench.py` and `diag_run.py` halt on bit 13. |
| **T3 lifted motor stop** (wheels free, powered) | J1, J2, J3 | (a) Stop the agent while driving both wheels at duty 0.71: the duty fields reach 0 within 0.6 s of the last command's arrival and the encoders are flat within 1.0 s. (b) 20 Hz unstamped publisher, agent paused for 2.5 s: the duty stays 0 for at least 250 ms after the unpause, quarantine drops rise, and motion resumes only from commands sent after the unpause. (c) The same with a 5 s pause: disarmed, no motion until the marker. |
| **T4 floor-spot idle, A-B-A-B** | J0 (baseline), J1 vs J0, J2 vs J1, J3 vs J2 | **J0:** behaviour like Build I, 0 reboots, the probe table filled, and the run records whether the stalls come with LINK downs, kicks or beacon-rate dips. **J1:** 0 rebuilds, 0 forced rejoins, 0 reboots in every run; **no amplification** (maximum telemetry gap no more than the longest ping-reply pause + 1.0 s); maximum gap ≤ 4 s or ≤ 50 % of J0's in the same pair. **J2:** 0 rebuilds and reboots; 0 host joins unless a LINK down or kick is logged; gaps > 1 s ≤ J1's in the same pair + 1; loss ≤ 1 %; roams ≤ 2 per 30 min with no return within 5 min; Pico PM=1 Null frames ≤ 1 per minute while RSSI ≥ -73 and counted separately below -73. **J3:** in at least 2 of 3 runs, gaps > 1 s ≤ 3, maximum ≤ 2.5 s, loss ≤ 0.5 %, sync misses ≤ 15 per minute (today 32-46), median RSSI ≥ -62 dBm; no gap > 5 s without a logged cause; ≤ 1 host roam per run after the first 120 s; 30 s `link_gate` passes 4 of 5 times (0 of 2 on 10-23, bench log :747-752). **A J3 failure caused by mesh-wide stalls (ping pauses equal on every node) counts as a FAIL with a diagnosis, not a waiver** (judge must-fix). The next step is then section 6. |
| **T5 walk between nodes** (car carried level, motor switch off, 3 loops) | J2, J3 | Route: stand (..bd2b48), floor spot, near ..b75a08, near ..b955c8, back; **3 min at each stop.** **J2:** 0 rebuilds and reboots; every chip roam gap ≤ 1 s; gratuitous ARPs = roams; no A-B-A within 5 min. **J3:** in every loop **at least 1 roam away from ..bd2b48 at the far stops and at least 1 back at the stand** (no escape clause); within 120 s of each arrival the car is on the best-scoring node or within 3 dB of it; method B outage ≤ 3 s (method A ≤ 1 s); ≤ 1 roam per stop; 0 rebuilds and reboots; loss over the whole walk ≤ 2 %. |
| **T6 tin test, beacon loss** (cover 6 s, 3 times) | J2 | Each LINK down (reason 1) recovers within 2 s of uncovering, by revival or a chip roam, with no host join, or there is no LINK down at all. |
| **T7 scan cost and chip scans while driving** | J2 gate | (a) Stand and floor spot, 2-min A/B arms of a channel-6 scan every 5 s against no scans: 0 Pico PM=1 frames in the scan arms (baseline 0 of 2,127); ping p90 within +10 ms and p99 within +20 ms; ≥ 95 % of scans complete within 820 ms; the serving node listed in ≥ 90 % of scans; ≥ 3 nodes per merged pair. If it fails: try active 40 ms scans, then disable the scans. (b) **m22 floor patterns with a capture:** count PM=1 frames while driving with roam_off 0; A/B triggers -78 against -75 and -80 (judge must-fix). (c) Information only: write roam_off 1 then 0 while associated on the stand and watch for LINK events. |
| **T8 roam primitives** (stand where ..bd2b48 and ..b75a08 are both at -70 dBm or better) | J3, J3b | (a) **Method A gate:** 20 REASSOCs; ≥ 19 of 20 confirmed within 1 s; Pico receive silence median ≤ 300 ms and maximum ≤ 1 s; 0 netif link-downs; no DISASSOC; the trace shows AUTH → LINK → PSK_SUP 6; a gratuitous ARP seen on the wire; `TK_SESSIONS` +0. (b) 20 method-B roams: 20 of 20 end UP on the target; link-down median ≤ 2.5 s and maximum ≤ 6 s; IP unchanged; `TK_SESSIONS` +0; loop maximum ≤ 16 s. |
| **T9 forced node loss** (the satellite the car is on; **never the gateway, and never the node the development machine is wired through**; you unplug it with the household's consent and restore it after 3 min; twice) | J2, J3 | Telemetry back within 8 s through a chip roam, or within 15 s through the host path; 0 reboots; session kept; disarmed and re-armable; the lost node blocked; after the plug-in, 10 min with ≤ 1 roam and no ping-pong. Lifted variant while driving at 0.71: the T3 criteria hold. |
| **T10 floor driving** (m22 floor, spin and turn patterns, stamped commands) | J1, J2, J3 | Every segment completes, or stops within 0.5 s on a gap; no motion after a silence of 3 s or more until the marker; 0 stale-command motions; 0 reboots; `TK_RADIO_MAX_US` = 0 in every 50 Hz message; guard 0; `TK_SCANS` unchanged during commanded segments. |
| **T11 soak** (60 min parked at the floor spot plus a capture) | J3 | 0 reboots, 0 rebuilds, ≤ 2 roams per 30 min, every gap > 3 s explained by a logged cause, settings drift logged and rewritten, roam_off reads 0. |
| **T12 rollback** | every stage | `WIFI_ROAM_MODE 0` behaves like Build I (pinned, roam_off reads 1), with the layout-6 fields filled. |
| **T13 BTM** | J4 | The Pico's association request (one join captured) has Extended Capabilities bit 19 set (clear in J3). T4 and T5 repeated: no worse than J3; no "disassociation imminent" outage over 8 s. If eero sends no BTM in 30 min, J4 has shown nothing; keep it off. |

**Hold-back rule.** If J2 is worse than J1 at the floor spot while T6 and T9 pass, try one tuning arm at a time, each with its own A/B: trigger -80; fullroamperiod 70 against 300; bcn_timeout 6; delta 12.

---

## 6. Router-side options (map omitted)

The household checklist — which node is in which room, what to unplug, and the eero-app clicks — is not in this public copy. The private course repo holds it.

What the firmware design uses from that checklist:

- Every 2.4 GHz radio is on one channel, so a stall on that channel hits every node.
- Mesh traffic at 1–2 Mb/s, much of it retries, uses a large share of that channel.
- A node with a wireless backhaul is a worse default than a wired one. That is why host node choice and the −6 dB prior exist.
- Wiring a wireless-backhaul node can be tested later. A 2026-10-24 check withdrew one "add Ethernet" item because that node was already wired. This copy does not say which node, or which room.

None of these router settings was changed when the design was written.

## 7. Risks and open questions

**Risks:**
1. **The 7.95.49 firmware is not wl 7.10.** Trigger semantics, the scan schedule, the beacon-loss timer, the event order, REASSOC, home-channel scans and the presence of each iovar all come from a sibling source (L). J0, T7 and T8 exist to check them, and any knob whose iovar is absent is skipped.
2. **The host cannot hold off chip roam scans while driving.** The -78 trigger makes them rare, and T7b measures them. Whether roam_off can be toggled while associated is unknown (T7c).
3. **The event tap depends on the exact v1.1.1 format strings.** A driver upgrade stops the build (`#error`). A format change within the same version would show as `TK_EV_TOTAL` = 0 in T1; the 1 Hz BSSID poll stays as the fallback.
4. **Any firmware DISASSOC drops the driver's state** (cyw43_ctrl.c:353-355). This covers DEAUTH_IND with reason 2 (:396-401) and BTM "disassociation imminent". Recovery then takes the slower host rejoin path (up to about 16 s).
5. **A PRUNE with reason 8 makes the driver rejoin by SSID with WPA1** (cyw43_ctrl.c:366-372). That join fails and the host restores WPA2. This is the same risk as today; it is logged in `TK_KICK_LAST`.
6. **A join is one driver call of about 11 ioctls.** Under extreme credit starvation it could exceed 16 s and reboot the board (boot report phase 3). It runs only with the link down and the wheels stopped, and J3 requires a probe answered within 20 ms first.
7. **REVIVE calls `netif_set_link_up` outside the driver's state machine.** It requires the same BSSID as before the drop, the tin test checks it, and `WIFI_LINK_REVIVE 0` turns it off.
8. **Keeping the session across rejoins assumes the agent keeps this client's mapping.** Backstops: the agent-lost check, the 20 s rule and the IP-change rule. The topics' best-effort traffic should carry on (I).
9. **The 3 s disarm ends test runs** that a 3-4 s gap would not end today. Today those runs were rebuilt and disarmed at 4 s anyway; the tools must send the marker again.
10. **The raw escan relies on public but internal driver fields** (cyw43.h:114-117) and on the options layout. Mitigations: timeout, reset, abort, and no overlap with joins.
11. **Roaming cannot escape mesh-wide channel-6 episodes.** Node differences of 4-6 dB sit within the CYW43439's ±5 dB RSSI accuracy (datasheet Table 25). R3 and probation limit useless moves.
12. **Telemetry gets bigger** (+112 bytes per message) on a link with about 32 % uplink retries.
13. **The node-unplug tests disturb the household,** and eero re-optimises after resets.
14. **Scope:** three new modules and a rewritten supervisor. Hence one capability per stage, a review per stage and rollback UF2s.
15. **Privacy:** the 10-23 captures (full MACs and SSIDs of every household device) were deleted from the Spark and the Mac after the analysis (2026-10-24); new tests make new captures and report counts only.

**Open questions, and the stage that answers each:**
- Which roam iovars exist in the 7.95.49 ROM: fullroamperiod, roam_nfscan, txfail and txmin thresholds, wnm? (J0)
- Do the floor-spot stalls come with LINK downs, beacon loss or kicks, and how often do credit timeouts happen? (J0)
- Does a home-channel-only escan stay on channel? (T7)
- Does WLC_REASSOC work on 7.95.49, and which events does it produce? (T8)
- How does the link behave on ..b75a08 at the floor spot? It was never measured after Build I's fallback. (J3, T4/T5)
- Is the stall/mesh-burst association repeatable, and does Ethernet backhaul remove it? (30-60 min captures; section 6 item 2)
- Which nodes still have a wireless backhaul? The 2026-10-24 check is in the private course repo; this public copy does not map nodes to rooms.
- Does eero ever send BTM or deauth to a client? (a capture of 30 min or more)
- The Pico's PMK may be recomputed on every join (the passphrase is sent with flag 1, cyw43_ll.c:2092-2101). If so, method B costs more; the T8b event timeline measures it.

**Deliberately outside this design** (a separate A/B plan later, because each would confound the roaming verdict even though each may help the floor stalls):
- interference mode NONE, and the NVRAM `glitch_based_crsmin=0` setting (pico-sdk #2835);
- refusing downlink A-MPDU (`ampdu_rx_tid`) and turning off `ampdu_rts`;
- retry limits;
- country code US instead of WORLDWIDE (pico-sdk cyw43_arch.h:151-153);
- `btc_mode`.

---

## 8. Sources

**Repository and workflow evidence:**
- firmware: `assignments/assignment7/module-7-kinematics-control/firmware/pico_odometry/` (`wifi_link.c`, `pico_odometry.c`, `drive_control.c`, `safety.h`, `picow_udp_transport.c/.h`, `lwipopts.h`, `CMakeLists.txt`; line numbers as cited);
- bench log: `assignments/assignment7/evidence/new-motor-bench-2026-10-20.md`;
- survey: `assignments/assignment7/evidence/wifi-survey-2026-10-23.md`;
- capture analysis: `assignments/assignment7/tools/wifi_survey/analysis_timeline/` and `assignments/assignment7/tools/wifi_survey/analysis_air/`;
- driver source copy: `cyw43-driver v1.1.1 (commit 055d642) in the Spark's `pico-microros-builder` image, /opt/pico-sdk/lib/cyw43-driver/`;
- event-tap prototype: `assignments/assignment7/tools/wifi_survey/event_tap_prototype/hook.c`;
- earlier research: `reports/Seamless WiFi mesh roaming for Pico.md`.

**Driver, SDK and stack:**
- cyw43-driver v1.1.1: https://github.com/georgerobotics/cyw43-driver/blob/055d64274b014dd7b1c2fc94d26e8a18face7124/src/
- cyw43-driver v2.0.0 roam ioctls: https://github.com/georgerobotics/cyw43-driver/blob/bed438f119cfba03f75957fceb6a5623ef95e6d9/src/cyw43_ll.h#L34-L45
- Roam defaults on a Pico W (PR #151): https://github.com/georgerobotics/cyw43-driver/pull/151
- Join timing on 7.95.49 (issue #161): https://github.com/georgerobotics/cyw43-driver/issues/161
- PR #163: https://github.com/georgerobotics/cyw43-driver/pull/163
- pico-sdk 2.3.1: https://github.com/raspberrypi/pico-sdk/blob/2.3.1/src/rp2_common/
- pico-sdk issue #2835: https://github.com/raspberrypi/pico-sdk/issues/2835
- lwIP 2.2.1: https://github.com/lwip-tcpip/lwip/blob/77dcd25a72509eb83f72b033d219b1d40cd8eb95/src/core/
- Broadcom wl 7.10 (third-party copy): https://github.com/afeng11/43602/blob/ccf6c7adde7f218242dcb312d6a0f09247e2a221/43602/src/wl/sys/
- Infineon WHD headers: https://github.com/Infineon/wifi-host-driver/blob/55639e22c6bd614984b5c7007add8ba240017a30/WiFi_Host_Driver/src/include/whd_wlioctl.h
- WHD roam_off 0 at join: https://github.com/Infineon/wifi-host-driver/blob/bd99da7b005c97500d7c697f544b36fabdaa3f5e/WHD/COMPONENT_WIFI6/src/whd_wifi_api.c#L1785-L1786
- brcmfmac hinted join: https://github.com/torvalds/linux/blob/v6.17/drivers/net/wireless/broadcom/brcm80211/brcmfmac/cfg80211.c#L2546-L2555
- Micro-XRCE-DDS Agent: https://github.com/eProsima/Micro-XRCE-DDS-Agent/blob/73622810d984349b80bbac0ef55fc0b694d62222/src/cpp/processor/Processor.cpp#L136-L181
- Micro-XRCE-DDS Client: https://github.com/eProsima/Micro-XRCE-DDS-Client/blob/83f129a80770a09aac9e823896ecbf6a0eddf0fc/src/c/core/session/session.c#L1257-L1272
- rmw_microxrcedds time sync: https://github.com/micro-ROS/rmw_microxrcedds/blob/b5ad1740ecfc611496a6ba2f12c7540b85cbec8f/rmw_microxrcedds_c/src/rmw_microros/time_sync.c#L23-L35

**Roaming practice:**
- Apple: https://support.apple.com/en-gb/guide/deployment/dep98f116c0f
- Android: https://source.android.com/docs/core/connect/wifi-network-selection
- ESP-IDF: https://github.com/espressif/esp-idf/blob/383dda6c182e3dabf6355160166fe007df775629/components/esp_wifi/wifi_apps/roaming_app/src/Kconfig.roaming
- wpa_supplicant: https://github.com/zephyrproject-rtos/hostap/blob/33921a8a77c56bddfe196a11935009cededc3bb3/wpa_supplicant/bssid_ignore.c#L68-L107
- Zephyr: https://github.com/zephyrproject-rtos/zephyr/blob/2a9e8ac155a3f2fd85d4559753be86a47b44ccf0/modules/hostap/src/supp_api.c#L2279-L2310

**Hardware:**
- CYW43439 datasheet: https://www.farnell.com/datasheets/3758304.pdf
- Pico 2 W datasheet: https://pip-assets.raspberrypi.com/categories/1088-raspberry-pi-pico-2-w/documents/RP-008304-DS-2-pico-2-w-datasheet.pdf

**eero:**
- release notes (archive): https://web.archive.org/web/20211202134922/https://support.eero.com/hc/en-us/articles/209636523-eero-Software-Release-Notes
- https://eero.com/support/articles/what-advanced-features-does-eero-support
- https://eero.com/blog/articles/truemesh-trueroam-truechannel
- https://eero.com/support/articles/what-is-eero-truemesh
- https://eero.com/support/articles/how-does-eero-optimize-my-network
- https://eero.com/support/articles/why-doesnt-my-device-connect-to-the-closest-eero
- https://eero.com/blog/articles/ethernet-backhaul-mesh-wifi
- https://eero.com/support/articles/what-is-eero-connection-strength
- https://eero.com/support/articles/what-is-compatibility-mode
- https://eero.com/support/articles/what-is-coverage-scan
- https://eero.com/support/articles/how-do-i-share-my-eero-network-with-guests
- https://eero.com/support/articles/what-is-mobile-roaming
- https://eero.com/support/articles/what-is-smart-queue-management-sqm
- https://eero.com/support/articles/can-i-set-my-eeros-to-use-the-2-4-5-or-6-ghz-frequency
- https://eero.com/support/articles/how-do-i-get-started-with-eero-business
- https://community.eero.com/t/806rsm/channel-selection

**Steering by other mesh vendors:**
- Airties: https://patents.google.com/patent/US10362526B2/en
- Netgear: https://patents.google.com/patent/US9967884B2/en

**Root access:** none was needed to write this design. All sources were read without root, from the Spark's builder image and local copies. The monitor-mode captures in tests T4, T7 and T8 need root on the Spark, as the 10-23 captures did.

AI-assisted: Claude Opus 5.5 via Claude Code (research, design and review workflow, 2026-10-23).
