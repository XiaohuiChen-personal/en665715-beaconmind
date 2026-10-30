# Agent design — D1–D10 and the open project decisions (v3.3)

**Decided 2026-09-27 by Claude Opus 5.5 under Xiaohui's explicit delegation.** Before going to
sleep, Xiaohui asked Claude to "figure out D1–D10" and, for any open item, to "evaluate the pros
and cons for each option and select the one that is best suited for this project". Every
decision records the options, their pros and cons, the choice and why. Xiaohui can overturn any
of them. This is the Phase 0 spec required by `assignments/assignment4/system-prompt/PLAN.md` §4.

**History (all review logs are in [`research/2026-09-27-llm-slam-feasibility/`](research/2026-09-27-llm-slam-feasibility/README.md)):**
- **v1** was reviewed by five adversarial lenses; 73 findings (5 critical), all confirmed →
  `design-review-v1.md`.
- **v2** was reviewed by four lenses, including a hand-simulation and Monte-Carlo checks; 51
  findings (1 critical, 35 major), all confirmed → `design-review-v2.md`.
- **v3** applied both. A round-3 check (two lenses, including a literal Monte-Carlo simulation of
  the procedure) found no critical issues and 11 major edge cases, all confirmed →
  `design-review-v3.md`.
- **v3.1** fixes them.
- **v3.2** (2026-09-27) records the edits made while the Module 4 prompts were written:
  `safety.done_range_m` became an OBSERVATION field; the D7 decision table puts STOP/REPORT before
  contact recovery and the operator request (the AI reviser had copied the old order); rule 1 is
  "first match … skip 3-7"; E4 clears `target_heading_deg`; the D8 example note is first person
  and uses `[0,0]`; the D10 prompt budget moved from 3,000 to 3,500 tokens (target missed). See
  `assignments/assignment4/system-prompt/evidence/decision-log.md`.
- **v3.3** (this file, 2026-09-27, after the first smoke test) follows **Xiaohui's decisions** to add a
  duplicated-tag-id example, to raise the prompt budget rather than cut rules, and to increase the
  context window as needed. Claude Opus 5.5 decided and made the other changes below under that
  delegation (decision-log V1–V12).
  - The prompt gains a third few-shot example: a duplicated tag id during a scan (Example 3 in
    `tools/fewshot_scenario.py`). The refusal example becomes a JSON fragment.
  - The D10 prompt budget rises to **4,500** instead of cutting rules; the final measures 4,352
    tokens.
  - The project server runs `--max-model-len 131072`: first 32768, then 131072 on the model card's
    advice for thinking mode.
  - The E2 `scan_added` rule is fixed: a beacon found on a scan's last turn now counts.
  - The smoke test's scenarios come from a simulated history.
  - Benchmark sampling for self-hosted models follows the model card.
  - Example 1 / D8's `scans_without_new` is corrected to 1: its map shows that scan 2 found
    nothing new. The decision is unchanged.
  - Evidence: `assignments/assignment4/system-prompt/evidence/smoke-test.md` and
    `evidence/decision-log.md` (V1–V12).

**The v3 split.**
- **The prompt** states only rules the agent can act on.
- **Tools** compute every number and every gate flag. The LLM does no arithmetic beyond
  incrementing or decrementing small integer counters.
- **The validator and harness** enforce safety and bookkeeping and hand the agent flags
  (`forward_allowed`, `turn_allowed`, `scan_allowed`).
- **Hardware and firmware behaviour** are workstream requirements with acceptance tests (§W).

§P lists exactly what the prompt must say.

**Design values.** No wheel diameter, track width, chassis size, lens height, front overhang or
camera field of view is recorded in the repository (checked 2026-09-27). **Every numeric
threshold in this file is a design value (DV).** W2 replaces the detector-related ones and W3
the motion-related ones. The prompt presents DVs as limits, never as measured facts.
Reference implementation of every geometry tool:
`assignments/assignment4/system-prompt/tools/l2_geometry.py` (self-checks pass).

---

## D1 — Scope (amended from PLAN §4)

- **1a World:** one prompt consistent with the *design* of both the Isaac Sim twin and the real
  car. Results are labelled `sim` or `real`. No range sensor in either.
- **1b Level L2.** The LLM owns the pose belief, the beacon map and every SLAM decision. Tools
  are **single-timestep**: functions of one step's detections, the previous report and harness
  counters. Nothing optimises over observation history (that would be L3). *Amendment:* v1 said
  "single-observation"; multi-beacon resection from one step's detections is allowed.
- **1c Scope:**
  - **In:** an unknown tag layout in a clear, walled, convex arena; the D4 moves; detector output
    (`id` may be null); the D8 report; unique- and duplicated-ID conditions; the missions EXPLORE,
    GO_TO_BEACON, RETURN_TO_START, REPORT, STOP.
  - **Out:** obstacle sensing or avoidance; occupancy maps; free-form motion; pixels for text
    models; manipulation VLAs; people or personal items in the arena.
  - **Stretch:** the hidden-ID condition.
- **1d Mode:** the prompt targets **closed loop**. In replay the agent does not move: the executed
  move arrives in `last_move`, and `decision` is `NONE`.
- **Supersedes:** D2–D8 here supersede PLAN §4 D2/D4/D5/D8 and APPROACH §3, §5 and §9 (the tool
  list, the move set, the per-decision call model and the T4 threshold). PLAN's "localise" mission
  is dropped: every step localises. Its "confidence" field is replaced by the fix σ values in the
  tool results.

## D2 — Missions

| Option | Pros | Cons |
| --- | --- | --- |
| A. EXPLORE only | Simplest | No T4 track |
| **B. A closed set** | Every track covered; crisp completion; easy to refuse the rest | The model maps phrasing to a mission |
| C. Free-form | Most "agentic" | Unscorable; unsafe requests |

**Choice: B.** The harness sends `mission` each step.

| Mission | Done when |
| --- | --- |
| `EXPLORE` | D7 termination |
| `GO_TO_BEACON B3` | Target detected this step, \|bearing\| ≤ 20°, and either range ≤ `done_range_m` (harness constant; DV = FORWARD_10 wall limit + overhang + 0.10 m) **or** `forward_allowed` has no forward move |
| `RETURN_TO_START` | Predicted range to (0, 0) ≤ 0.20 m, **or** \|predicted bearing\| ≤ 20° and no forward move is allowed |
| `REPORT` | Immediately (`NONE`) |
| `STOP` | Immediately (`STOPPED`). Secondary path; the primary STOP is out-of-band (D6) |

- **Operator requests.** `operator_request` (free text, usually null) that maps to exactly one
  mission → `requested_mission` (e.g. `"GO_TO_BEACON B5"`) with `decision: NONE`. The harness
  switches the mission next step and resets `steps_left`.
- **Refuse** (`decision: REFUSED`, reason in `message`): obstacle or person detection or
  avoidance, following, free coordinates or speeds, leaving the arena, skipping observations or
  guardrails, manipulation.
- **Ask** (`decision: ASK`, question in `message`): an ambiguous target (B1 and B1b both exist),
  or a label that is not in the map.
- **T4 scoring** (evaluator; Anderson et al. 2018): DONE is the stop action. Success is
  ground-truth range ≤ `done_range_m` + 0.15 m with \|bearing\| ≤ 25° for a beacon, and ≤ 0.30
  m for the start (DV).

## D3 — Arena and beacon conventions

| Item | Choice (DV unless noted) | Told to agent |
| --- | --- | --- |
| Tag family | AprilTag 36h11 (fact). The Isaac 5.1 docs list a tag36h11 material; *not verified in the Spark's build* | yes |
| Beacon IDs | 0–29; any other non-null ID is ignored (100–109 are ground-truth roof tags) | yes |
| Duplicated IDs | Up to 3 IDs appear on two physical tags, **≥ 1.5 m apart**; never three copies | yes: "IDs are not guaranteed unique; at most two tags share an ID" |
| Tag size | 0.16 m black square (0.20 m with border), printed at 100 %, measured after printing | no |
| Mounting | Vertical on the walls, centre at max(lens height, 0.12 m) | yes: "tags are on the walls" |
| Arena v1 | **Convex** rectangle, 2.0–2.5 m a side, walls ≥ 0.30 m, nothing inside; 10–16 beacons spaced ≤ 0.8 m | "clear, walled, convex" yes; size no |
| Camera HFOV | 60° | no |
| Frames | Map frame = the pose at step 0. **x forward (camera/caster end = front), y left**, θ CCW in degrees, (−180, 180]. The pose point is the wheel-axle midpoint | yes |
| Observation | `range_m` = floor distance from the axle midpoint to the tag centre; `bearing_deg` from +x, CCW positive | yes |
| Labels | `B<id>` first; `B<id>b` for the second tag with that ID; `U<n>` for beacons first seen with id null, renamed `B<id>` when decoded | yes |

## D4 — Moves and limits

**Choice** (options as in v2: continuous motion or two moves were rejected): five bounded moves,
executed by the Pico's move executor.

| Action | Motion |
| --- | --- |
| `FORWARD_25` | 0.25 m forward (matches Uni-NaVid; the N-arm adapter uses only it and the turns) |
| `FORWARD_10` | 0.10 m forward |
| `BACKWARD_10` | Backward, the lesser of 0.10 m and the distance the previous forward move actually covered. Only directly after a forward move whose result was done, stalled or bumped |
| `TURN_LEFT_30` / `TURN_RIGHT_30` | ±30° in place |

- `DONE`, `NONE`, `STOPPED`, `ASK` and `REFUSED` are decisions, not moves.
- **Limits:** linear ≤ 0.15 m/s; turn rate set in W3; move timeout 5 s.
- **Step budgets:** EXPLORE 150, navigation 60. That is 2.5× the APPROACH §9 cost basis.
- **One move per observation.** A refused move does not use up the observation.

## D5 — Observation, tools, validator

**Step message** (harness → model):
- `mission`
- `operator_request`
- `OBSERVATION`
- `PREVIOUS_REPORT` (null at step 0)

**The harness is authoritative for state:**
- It checks every map entry and pose in a report against the step's tool results and
  PREVIOUS_REPORT, within rounding (0.005 m, 0.05°).
- A mismatch is logged as a `state_violation`, and the tool-derived value is used.

**OBSERVATION** (harness-built; bookkeeping precomputed):
```json
{"obs_id": "ep03-s014", "step": 14, "source": "sim", "mode": "closed_loop",
 "status": "ok", "error": null, "sensors": {"camera": "ok", "imu": "ok", "pico": "armed"},
 "odometry": {"forward_m": 0.25, "left_m": 0.0, "dtheta_deg": 0.4, "quality": "ok"},
 "last_move": {"action": "FORWARD_25", "result": "done"},
 "counters": {"steps_left": 136, "odometer_m": 0.5, "travel_since_fix_m": 0.5, "turns_since_fix": 12,
              "consecutive_contacts": 0, "consecutive_slips": 0, "consecutive_errors": 0, "latched": false},
 "safety": {"forward_allowed": ["FORWARD_25", "FORWARD_10"], "backward_allowed": true,
            "turn_allowed": true, "scan_allowed": true, "done_range_m": 0.55},
 "detections": [{"det": 0, "id": 1, "range_m": 1.02, "bearing_deg": 17.0, "quality": 0.86}]}
```

- **`status: error`** when:
  - a sensor is not ok: camera `stale`/`down`, IMU error, or Pico `disarmed` while the latch is
    clear;
  - the Pico rebooted: its boot id changed, and `odometry` is then null.

  An empty `detections` list means "no tags seen" **only** when status is ok.
- **`odometry`** is the motion since the previous observation, in the robot frame at that
  observation: chord at mid-heading, `forward_m` < 0 for backward. `dtheta_deg` is the BNO055
  gyro yaw (IMUPLUS, DV until W3) integrated during the move only.
- **`quality: slip_suspected`** when either:
  - encoder and IMU yaw disagree by > 10°;
  - a forward move changed the range to a tag within ±30° of ahead by less than
    max(0.08 m, 0.3 × move) of the expected amount, or a tag < 0.8 m ahead disappeared after a
    forward move.
- **`last_move.result`**, one enum everywhere: `done`, `stalled`, `bumped`, `timeout`,
  `link_lost`, `refused`, `not_called`.
- **`safety`** is computed by the validator with its own thresholds (W1–W3 measured):
  - wall distance = the minimum of the conservative tag-plane estimate (both pose-ambiguity
    solutions, ±20° normal uncertainty), range·cos(bearing) for tags within ±45°, the predicted
    ranges of mapped beacons within ±30° of +x, and a close tag that dropped out;
  - turns and scans are refused when anything, detected or mapped, lies within the sweep radius
    + margin.

  The agent plans with these flags, never with numbers.

**Tools.**
- All are single-timestep and return JSON with `status`. Errors return `{"status": "error",
  "error": "<reason>. Nothing changed."}`.
- `det` indexes **this** observation; beacon labels refer to PREVIOUS_REPORT's map. The harness
  resolves both.

| Tool | Returns |
| --- | --- |
| `compose_odometry(pose, forward_m, left_m, dtheta_deg)` | Pose: x' = x + f·cosθ − l·sinθ, y' = y + f·sinθ + l·cosθ, θ' = wrap(θ + dθ) |
| `gate_detection(pose, det, candidates)` | `new_point`; per candidate: predicted range/bearing, wrapped `d_range_m` and `d_bearing_deg`, `point_distance_m`, `in_gate`, `travel_since_seen_m`, `revisit`. The gate is 0.30 m / 15°, widened by 0.10 m and 5° per metre of `travel_since_fix_m` and by 1° per 30° turn since the last full fix (cap 0.60 m / 30°). `revisit` means a confirmed beacon with ≥ 1.5 m of travel since last seen |
| `fix_pose(prior, matches=[{det, beacon}])` | Refuses non-`confirmed` or `suspect` beacons. `full` (needs ≥ 2): x, y, θ, `residual_m`, `sigma_xy_m`, `sigma_theta_deg`, `well_conditioned` (σ ≤ 0.15 m / 8°), `within_prior_gate` (≤ 0.50 m / 20°), `relocalisation_ok` (≥ 3 beacons, residual ≤ 0.10, σ ≤ 0.25 m / 10°; used only when the prior gate fails). `position`: x, y at the prior's θ, `delta_m`, `within_prior_gate` (≤ 0.30 m), `heading_safe` (every \|d_bearing\| ≤ 3°) |
| `map_point(pose, det)` | x, y of a detection |
| `update_beacon(pose, det, beacon)` | Running-mean x, y, `n_obs`, `baseline_m` (distance from where it was first seen) |
| `predict_observation(pose, target)` | Range and bearing to a label, or to `{x_m, y_m}`, plus `near_blocked` (the target direction is within 30° of `blocked_heading_deg` from PREVIOUS_REPORT's memory) |
| `exploration_summary(pose)` | `nearest_scan_point_m` and `new_place` (no scan point within 0.5 m); 12 map-frame sectors of 30°, each with `blocked`, `max_leg_moves` (from mapped beacons as wall proxies: 1 if nothing is mapped that way, else clamp(⌊(wall_est − 0.60)/0.25⌋, 0, 3)), `score` (novelty + 0.5 × interior pull toward the beacon centroid) and `turns`. It reads `blocked_heading_deg` from PREVIOUS_REPORT's memory |
| `move(action)` | `result` (the enum above) and `reason` |
| `emergency_stop(reason)` | `{status: ok, latched: true}` |

**Validator** (below the LLM; each refusal is logged as a guardrail violation):
- `move` refuses:
  - anything outside D4;
  - a second executed move against one `obs_id`;
  - any move when `status` is error or the latch is set;
  - moves not in `safety`;
  - moves beyond `steps_left`.
- It auto-latches after 2 consecutive contacts (stalled or bumped), 2 consecutive slips, 2
  consecutive errors, `link_lost`, or a Pico reboot. Only the operator's latch-clear command
  re-arms the Pico.

## D6 — Safety

**Choice:** layered (options as in v2), with deterministic layers enforcing every safety rule
the prompt states.

1. **Out-of-band STOP:** a harness hotkey or `/estop`. It aborts any move, drops STBY, and sets a
   persistent on-disk latch. The Pico boots **disarmed** and moves only after an operator arm.
2. **Validator** (D5) and **Pico** (W3): speed caps, timeout, watchdog (`link_lost`), stall and
   bump detection, boot id.
3. **Agent guardrails** (the prompt):
   - use only the moves in `safety`;
   - no move on `status: error` or when latched;
   - stall/bump recovery (D7);
   - never claim to see obstacles or free space;
   - `emergency_stop` on any unresolved inconsistency;
   - obey STOP.
4. **Residual risk (the prompt states it):** walls are invisible between tags, and a contact is
   expected to be caught by stall or bump detection. *This is a W3 acceptance target, not yet a
   fact.*

Operator checklists, the wheels-down gate and the electrical requirements are in §W.

## D7 — Per-step procedure

**Step 0** (PREVIOUS_REPORT is null): pose (0, 0, 0); empty map; the odometry is ignored. The
memory starts as:
- `scan_points` [], `scan_index` 0, `scan_turns_left` 0, `scan_added` 0, `scans_without_new` 0;
- `legs_since_scan` 0, `leg_moves_left` 0, `target_heading_deg` null;
- `blocked_heading_deg` null, `recovery` none, `stuck` 0.

1. **Predict, then check.**
   - If `odometry` is non-null, first run Predict (step 2): a latched or error observation can
     carry a partial move.
   - Then, first match: latched → `STOPPED`; null odometry after step 0 → keep the pose,
     `emergency_stop`, `STOPPED`; `status: error` → `NONE`.
   - In those three cases skip steps 3–7 (memory unchanged).
2. **Predict:** `compose_odometry(previous pose, odometry)`. If `quality` is `slip_suspected`,
   use `forward_m = 0, left_m = 0`.
3. **Associate** each detection:
   - `rejected`: quality < 0.5, range > 2.0 m, or a non-null ID outside 0–29.
   - **Candidates:** the map entries with that ID; for a decoded ID with no in-gate entry, also
     the `U<n>` entries; for a null ID, every entry.
   - Call `gate_detection`. The harness passes `travel_since_fix_m` and `turns_since_fix`, both
     reset after any report whose `pose_source` is `beacon_fix` or `relocalised`, and the gate
     widens with both. Then classify:

     | Gate result | Association |
     | --- | --- |
     | exactly one candidate `in_gate` | `matched`. It clears that beacon's `suspect` flag and `conflicts`, and renames a `U<n>` to `B<id>` |
     | several `in_gate` | `ambiguous` |
     | none `in_gate`, and every `point_distance_m` > 1.0 or no candidates | `new` (label per D3; if B<id> and B<id>b already exist → `rejected`) |
     | none `in_gate`, but some candidate within 1.0 m | `rejected` (a conflict with the nearest candidate; counted in step 5) |
4. **Correct the pose.** With the matched, confirmed, non-suspect beacons, call `fix_pose`:

   | Condition (first match) | `pose_source` |
   | --- | --- |
   | `full.well_conditioned` and `full.within_prior_gate` | `beacon_fix` |
   | `full.relocalisation_ok` and **not** `full.within_prior_gate` | `relocalised` (the prior has failed) |
   | `position.within_prior_gate` and `position.heading_safe` | `position_fix` |
   | a fix was computed but none of the above held | `prior_kept` |
   | no matched confirmed beacon | `odometry` |

   **Drift recovery:** if ≥ 3 detections carry IDs whose single map entry is confirmed but not in
   gate, call `fix_pose` on those ID matches. If it gives `relocalisation_ok`, accept it
   (`relocalised`) and re-gate this step's detections from that pose.
5. **Update the map** (from the final pose):
   - `new` → `map_point` → `tentative`, with `first_seen_from` (the current position), and
     `first_seen_scan` = the `scan_index` in force **after** this step's decision (a scan started
     this step counts).
   - A matched **tentative** beacon → `update_beacon`. It becomes `confirmed` when `n_obs` ≥ 2
     and `baseline_m` ≥ 0.40.
   - **Confirmed beacons are frozen anchors.** They are never moved; only `odo_last_seen_m` is
     refreshed (for every matched beacon), after step 6.
   - **Conflicts:** only when `pose_source` is `beacon_fix`, `relocalised` or `position_fix`,
     each `rejected` conflict adds 1 to the nearest candidate's `conflicts`. At ≥ 2 it sets
     `suspect: true`, a flag beside `state`; suspect beacons are excluded from fixes until an
     in-gate match clears the flag.
   - **With `pose_source: prior_kept`, create or update nothing:** mark the detections
     `rejected` ("pose inconsistent").
6. **Loop closure:**
   - Every matched candidate with `revisit: true` goes into `loop_closure`.
   - It is **accepted** exactly when `pose_source` is `beacon_fix` or `relocalised` and that
     beacon was in the fix. Otherwise it is not accepted, with `pose_source` as the reason.
   - Closures correct only the current pose.
   - When unsure, do not close.
7. **Decide.** The first matching row wins, and each row names the step's decision. Two general
   rules apply to every mission:
   - **Refused turn:** a turn is needed but `turn_allowed` is false → `BACKWARD_10` if
     `backward_allowed`; otherwise end the leg or scan and decide `NONE` ("cannot turn"),
     `stuck` + 1; if `stuck` was already ≥ 1 → `ASK`. **Never drive forward to get around a
     refused turn.**
   - **Reset:** a forward move with result `done` sets `stuck` = 0, `recovery` = none and
     `blocked_heading_deg` = null. So does a mission switch, which also sets `leg_moves_left` =
     0; the map is kept.

   | # | Condition | Decision and memory writes |
   | --- | --- | --- |
   | 0 | Mission `STOP` or `REPORT` | `STOPPED` / `NONE`. Checked first, so STOP is never overridden by recovery |
   | 1 | **Contact:** `last_move.action` is a forward move and `last_move.result` is `stalled` or `bumped` | `BACKWARD_10` if `backward_allowed`, else `NONE`. Set `blocked_heading_deg` = θ, `recovery` = backed_off, `leg_moves_left` = 0, `target_heading_deg` = null. Any mission |
   | 1b | `operator_request` present | `NONE` with `requested_mission`, or `REFUSED`, or `ASK` (D2). The harness repeats the request until it is answered, so one deferred by row 1 is not lost |
   | 2 | Mission `EXPLORE` | The EXPLORE rows below |
   | 3 | Mission `GO_TO_BEACON` | Always call `predict_observation` for the target (it supplies `near_blocked`); use this step's detection of the target for range/bearing when present. DONE per D2. \|bearing\| > 20° → turn toward it (positive → left; refused-turn rule). \|bearing\| ≤ 20° → the largest allowed forward move (FORWARD_25 only when range ≥ 0.70 m); **if `near_blocked` is true → `ASK`** ("path blocked"). **3a (lost target, GO_TO only):** not detected, predicted \|bearing\| ≤ 20° and predicted range < 1.0 m → `ASK`; never turn in that case. **3b:** aligned (\|bearing\| ≤ 20°), not done, and no forward move allowed → `ASK` ("blocked") |
   | 4 | Mission `RETURN_TO_START` | Target = `predict_observation(pose, {0, 0})`. Row 3's turn, forward, `near_blocked` and 3b rules; **3a does not apply**. DONE per D2, with no detection required |

   **EXPLORE rows** (first match wins):

   | # | Condition | Decision and memory writes |
   | --- | --- | --- |
   | E1 | Termination: (`scans_without_new` ≥ 2 and no tentative beacon has `first_seen_scan` ≥ `scan_index` − 1), or `steps_left` = 0 | `DONE` |
   | E2 | Scan in progress (`scan_turns_left` > 0) | `TURN_LEFT_30` (`scan_turns_left` − 1). If the turn is not allowed: abandon the scan (`scan_turns_left` = 0) and continue with E3–E5 in this step. **Whenever `scan_turns_left` reaches 0 in a step** (last turn or abandoned): `scans_without_new` = 0 if `scan_added` > 0, else + 1. *(v3.3: one shared update, so an abandoned scan that found a beacon also resets the counter; review finding R-2)* |
   | E3 | Leg in progress (`leg_moves_left` > 0) | Face `target_heading_deg` (`exploration_summary` → that sector's `turns` ≠ 0 → one turn that way; refused-turn rule). Else the largest allowed forward move (`leg_moves_left` − 1). If no forward is allowed, end the leg (`leg_moves_left` = 0) and continue with E4 |
   | E4 | (`new_place` or `legs_since_scan` ≥ 2) and `scan_allowed` | Start a scan: append the position to `scan_points`, `scan_index` + 1, `scan_added` = this step's `new` associations, `scan_turns_left` = 12, `legs_since_scan` = 0, `target_heading_deg` = null, then apply E2 in this step |
   | E5 | Otherwise | Choose a leg: the unblocked sector with the highest `score` (ties: fewer turns, then left). Set `target_heading_deg`, `leg_moves_left` = its `max_leg_moves`, `legs_since_scan` + 1, then apply E3 in this step. **No unblocked sector → `DONE`** ("nowhere safe to explore") |

   While a scan was in progress before the decision, this step's `new` associations are added to
   `scan_added` **before** E2 reads it. A scan started this step gets them from E4 (above).
   *(v3.3, review findings E-5, R-1, E2-2 and H-3: the old wording, "whenever a scan is in progress
   after the decision", left a beacon found on a scan's last turn uncounted, so `scans_without_new` could
   rise after a scan that did find something.)*
8. **Report** (D8): the belief at this observation, before the move. `memory` is the state
   **after** this step's decision.

## D8 — Output format

**Choice:** one JSON object per step, nothing else. Prose and text-template formats were
rejected as unparseable.

The example below is **Example 1** from `tools/fewshot_scenario.py`. It is a constructed step
whose every number the script computes with the reference tools and asserts:

- **Previous belief:** (−0.30, 0.55, 26.0°); the odometry is FORWARD_25 with dθ −1.5°, so the
  prior is (−0.08, 0.66, 24.5°).
- **Detections:** tag 1 at 1.40 m / −24.1° and tag 5 at 0.78 m / 25.0°.
- **Gating:** both are in gate against the confirmed B1 (1.27, 0.63) and B5 (0.42, 1.22), and
  both are revisits (travel since seen 1.85 m and 2.10 m).
- **Fix:** `fix_pose` gives a full fix (−0.12, 0.65, 22.9°) with residual 0.016 m and σ 0.123 m /
  5.6°: well-conditioned, 0.042 m from the prior. So `beacon_fix`, and both loop closures are
  accepted.
- **Decision:** the leg had ended, and `nearest_scan_point_m` = 0.66 ≥ 0.5, so E4 starts a scan
  and takes its first turn.

(Ground truth (−0.15, 0.70, 20.0°): the fix error is 0.060 m versus 0.085 m for the prior.)

```json
{"step": 41, "mode": "closed_loop", "mission": "EXPLORE",
 "pose": {"x_m": -0.12, "y_m": 0.65, "theta_deg": 22.9}, "pose_source": "beacon_fix",
 "associations": [{"det": 0, "id": 1, "beacon": "B1", "result": "matched"},
                  {"det": 1, "id": 5, "beacon": "B5", "result": "matched"}],
 "loop_closure": [{"beacon": "B1", "accepted": true, "reason": "revisit in beacon_fix"},
                  {"beacon": "B5", "accepted": true, "reason": "revisit in beacon_fix"}],
 "map": [{"beacon": "B1", "id": 1, "x_m": 1.27, "y_m": 0.63, "n_obs": 3, "state": "confirmed",
          "first_seen_from": [0, 0], "first_seen_scan": 1, "odo_last_seen_m": 3.1, "conflicts": 0, "suspect": false},
         {"beacon": "B5", "id": 5, "x_m": 0.42, "y_m": 1.22, "n_obs": 2, "state": "confirmed",
          "first_seen_from": [0, 0], "first_seen_scan": 1, "odo_last_seen_m": 3.1, "conflicts": 0, "suspect": false}],
 "memory": {"scan_points": [[0, 0], [-0.6, 0.1], [-0.12, 0.65]], "scan_index": 3,
            "scan_turns_left": 11, "scan_added": 0, "scans_without_new": 1,
            "legs_since_scan": 0, "target_heading_deg": null, "leg_moves_left": 0,
            "blocked_heading_deg": null, "recovery": "none", "stuck": 0},
 "decision": "TURN_LEFT_30", "move_result": "done", "requested_mission": null, "message": null,
 "note": "I fixed my pose from B1+B5 (residual 0.02 m), closed both revisits and started scan 3 at a new place."}
```

*Numbering:* the prompt's Example 1 and Example 3 are the script's `example1()` and `example3()`.
The prompt's Example 2 is the refusal. The smoke test's held-out scenarios are built by
`tools/build_scenarios.py` from a simulated history. The former hand-made `s1_heldout()` was
removed on 2026-09-27, because its history could not happen under the rules.

**Example 1 is a constructed step.** Its numbers are tool-verified for the step itself, but its
pre-step memory is illustrative, not a history the rules reach:
- E5 at its scan-2 point would pick the 90° sector.
- In a 300-run sample of 4-tag worlds simulated with `tools/backstory_sim.py`, only 55 steps had
  a full fix and just 1 step had any loop closure. Searches over thousands more runs, with 3–7
  tags, found no step with two accepted loop closures. Revisits need 1.5 m of travel, and E1
  usually ends exploration first (about 51 steps on average).
- This is a finding for W3: loop closure may rarely trigger in a 2.25 m arena with these DVs.
- Example 3 is fully simulated.

**Example 3** (in the same script; **in the prompt since v3.3**) shows the duplicated-ID rule in
a different situation: step 28, during scan 2.
- **Its whole history is simulated**, not hand-picked. `tools/backstory_sim.py` applies the D7
  rules from step 0 to seeded noisy detections and odometry:
  - scan 1 at the start maps B6 (east wall) and B2 (west wall);
  - E5 picks two legs (90°, then 60°);
  - E4 starts scan 2 at (0.12, 0.47);
  - B6 is confirmed with `n_obs` 5 and B2 with `n_obs` 3 from their sightings;
  - `turns_since_fix` is 26, because no full fix is possible.
- At step 28 (after TURN_LEFT_30 done), B6 is matched without a revisit. That gives a
  heading-safe `position_fix`: (0.13, 0.46, 0.7°), with an error of 0.011 m against 0.026 m for
  the prior (the fix moves the pose 0.029 m).
- An id-2 tag has just come into view. It lies 2.23 m from B2 and out of its gate, so it becomes
  the tentative **B2b** at (1.24, 0.92), 0.02 m from the truth.
- E2 takes the next scan turn, and `scan_added` becomes 1.
- The simulation uses two DVs for the backstory only:
  - a reliable-detection limit (≤ 1.5 m and ≤ 60° off the tag's normal; W2 measures the real
    limits). In a 2.25 m arena every tag is inside the 2.0 m range cap from the start, so "not
    seen earlier" needs this model;
  - a validator limit: a forward move must leave ≥ 0.35 m to the wall.

Enums:
- `pose_source`: beacon_fix, relocalised, position_fix, prior_kept, odometry.
- Association `result`: matched, new, ambiguous, rejected.
- Map `state`: tentative, confirmed. `suspect` is a separate boolean flag.
- `decision`: FORWARD_25, FORWARD_10, BACKWARD_10, TURN_LEFT_30, TURN_RIGHT_30, DONE, NONE,
  STOPPED, ASK, REFUSED.
- `move_result`: the D5 enum.
- `loop_closure`: a list of `{beacon, accepted, reason}`.
- `message`: set only for ASK or REFUSED.
- `requested_mission`: set only when the operator's request maps to one mission.

## D9 — Operators and audience

**Choice:** the primary consumer is the evaluation harness (parser); the secondary is the
operator (Xiaohui, the experimenter), through `note` and `message`.

- **Tone:** terse, literal, numeric, first person as the robot, uncertainty stated plainly.
- Never report a success that no tool result shows.

## D10 — Runtime

| Item | Choice and reason |
| --- | --- |
| Prompt | One model-agnostic prompt, so model and prompt are not confounded |
| Conversation | Stateless per step (D5): identical across providers; bounded context; avoids the Opus 5.5 / Fable 5.1 thinking-edit rule |
| Harness | **Benchmark:** a custom harness exposing only the D5 tools (OpenAI Responses API, Anthropic Messages, vLLM OpenAI-compatible). **Course demo:** ROSA in `rosa-ros2`, subscribed to the project container's topics, with the same tools and `RobotSystemPrompts` and `accumulate_chat_history=False`. ROSA's blacklist only filters node/topic/param *names* inside its tools; it does not remove any tool, so the prompt tells the agent not to call them. ROSA always adds 30 calculation plus log/system tools and nine fixed prompts: **measured 5,195 Qwen tokens of built-in tool schemas (47 tools) and 819 tokens of fixed prompts**. So ROSA runs are **demo-only, not benchmark-comparable**. The robot prompt says its procedure replaces ROSA's discovery workflow and rosparam memory |
| Budget | Robot prompt ≤ **4,500** Qwen tokens (v3.3). *History:* 3,000 → 3,500 on 2026-09-27, when the complete v3.1 prompt measured 3,492 (3,499 after the final-prompt review fixes) and cutting further would have dropped verified rules; the 3,000 target was **missed**. → 4,500 later that day, after the first smoke test, when Xiaohui asked for a duplicated-ID example and for the budget to be raised rather than rules cut: the final prompt measures **4,352**. Step message ≤ 2,500. Project server `--max-model-len 131072` **in use since 2026-09-27**, first at 32,768, then raised because the Qwen3.5-35B-A3B model card advises "maintaining a context length of at least 128K tokens to preserve thinking capabilities" (GPU_UTIL 0.60: KV pool 129,952 tokens; `--max-num-seqs 4` caps concurrency at 4 requests). *Measured* first-turn input in the benchmark harness (prompt + step message + D5 tool schemas + template), round 2 of the smoke test: 5,216–5,316 tokens with the 3,499-token prompt and 6,069–6,169 with the 4,352-token prompt; at the full 2,500-token step budget ≈ 8k, leaving ≈ 123k at the 131,072 window (≈ 25k at 32,768) for tool turns and thinking output. The ROSA demo needs 819 (fixed prompts) + 5,195 (ROSA's 47 tools) + ≈ 915 (D5 tools) + 4,352 + 2,500 ≈ 13.8k before its tool turns. The 16,384 window of the first smoke test overflowed once (10,385 input + 6,000 reserved output) |
| Labels | `source` and `mode` in every observation |
| Sampling | Provider defaults; K ≥ 3 repeats. *v3.3:* for a self-hosted open model, "provider defaults" means the model card's recommended settings for the mode used (Qwen3.5-35B-A3B: thinking T 1.0, top_p 0.95, top_k 20, presence_penalty 1.5; instruct T 0.7, top_p 0.8, top_k 20, presence_penalty 1.5), and no output cap below the server window |
| Data governance | Text arms send detector output and odometry only. The image ablation sends only simulated frames to external APIs; real frames go only to local models. No keys, Wi-Fi details or personal data. Fable's 30-day retention is accepted for text-only traffic |

## §P — What the system prompt must state

In ROSA's alphabetical print order the procedure must sit in one field, and the few-shot must
come last (`nuance_and_assumptions`).

(The Module 4 final prompt, `assignments/assignment4/system-prompt/system_prompts.py`, implements this list; measured 4,352 tokens since v3.3, previously 3,499.)

1. **Persona:** the embodied L2 SLAM agent of the kit rover; its sensors; no range sensor.
2. **Instruction:** the missions and their done conditions; one decision per step.
3. **Context:** the step message and OBSERVATION fields; the tools (one line each); the fact that
   tools and the validator compute every number and flag ("never compute; read the flags").
4. **Data:** frames, units and labels; beacon IDs 0–29, not unique (at most two per ID); tags on
   walls; a convex, clear arena; all thresholds are design limits.
5. **Business logic:** the D7 procedure, compressed into the ordered checks and tables.
6. **Guardrails:** the D6 layer-3 rules; refuse and ask; the residual risk.
7. **Format:** the D8 JSON with its enums.
8. **Audience and tone:** D9.
9. **Few-shot:** the script-generated steps (Example 1: a two-beacon fix; Example 3 since v3.3: a duplicated tag id) and a refusal as a JSON fragment, placed last.

## §W — Workstream requirements this design places on W1–W3 (acceptance tests)

- **W1 (twin and car):** measure the wheel diameter, track width, axle-to-front overhang (camera,
  USB-C plug and cable bend included), sweep radius and lens height. The camera goes on a rigid
  bracket, and the power-bank cable uses a right-angle USB-C plug routed back along the chassis.
  The Isaac AprilTag material must render a tag36h11 that the detector decodes.
- **W2 (camera):** HFOV and VFOV; minimum and maximum reliable detection range; range and bearing
  error versus distance; tag-normal error against a known wall angle. Requirement: the minimum
  detection range plus the camera setback must be below the FORWARD_10 wall limit, otherwise
  raise the limits and `done_range_m`.
- **W3 (Pico) — electrical:**
  - **untethered mode:** the Pico runs from a USB power bank on micro-USB with the VSYS jumper
    **out**. That keeps the Toshiba order (Pico first, battery switch second) and the USB/VSYS
    interlock. A dual-port bank can also feed the camera.
  - **fallback:** the AMS1117 → VSYS path, with VM and VCC rising together, is allowed only with
    the pull-down below and wheels up at every switch-on.
  - **mandatory:** an external pull-down of ≤ 8.2 kΩ (e.g. 4.7 kΩ) from STBY/GP5 to GND before
    any wheels-down run (RP2350-E9). A resistor is outside the kit list; this is a scope decision
    in favour of safety. Firmware drives STBY/IN/PWM low at boot.
- **W3 — motion:** a stall profile (200 ms grace, then < 50 % of the profile over 200 ms); a bump
  threshold on the IMUPLUS linear acceleration (set from logged contacts); the
  heartbeat/watchdog period set from the measured p99 link latency with the camera streaming;
  `link_lost` and boot id reported. Acceptance: ≥ 10 drives into the real wall material at 0.15
  m/s, head-on and at 30°, all detected.
- **Wheels-down gate** (all logged on the bench, wheels up, before any wheels-down motion):
  - out-of-band STOP drops STBY within ≤ 0.2 s mid-move;
  - the watchdog trips when Wi-Fi or the harness is killed mid-move;
  - boot is disarmed with the pull-down fitted (Pico held in reset with VM live → wheels still);
  - stall trips when a wheel is held;
  - the boot id changes on reset.
- **Operator procedure:** measure the pack before each episode, motors idle, and replace the
  cells below 5.5 V (no ADC is wired).

## Other open project decisions

| Open item | Choice and reason |
| --- | --- |
| **W0 — ROS 2 distro** | **A dedicated Humble project container.** Both proven live links are Humble: the Isaac bridge UDP-only reaches `rosa-ros2` (FastDDS 2.6.12), and the Pico's `micro-ros-agent:humble` node was seen in Humble. Host Jazzy did not receive Isaac odometry and was *not shown* to see the Pico. `ros-humble-apriltag-ros` 3.4.0 is in the jammy arm64 index |
| **B1 (GTSAM)** | **Offline on the host**, in a Python 3.12 venv (gtsam 4.3.0 has cp311–cp314 aarch64 wheels only; Humble's Python 3.10 has none). B1 reads logged observations |
| **Isaac Sim version** | **Start on 5.1**: its Humble bridge and headless rendering are proven here (Nova Carter only). Evaluate 6.0 in parallel. For both, the AprilTag material check in W1 |
| **API budget** | Pilot first (≤ $100). The sweep budget stays open until the pilot measures tool turns and tokens per decision |
| **Course fit** | Xiaohui asks the instructor (team vs individual; accepting the change from the 2026-09-14 proposal). Blocking for the project scope, not for the Module 4 assignment |

## Generative-AI disclosure

Claude Opus 5.5 via Claude Code made and documented these decisions under Xiaohui Chen's explicit
delegation (2026-09-27). It revised them after three design-review rounds (124 findings in rounds 1–2 and 11 major edge
cases in round 3, all confirmed and addressed) and wrote a reference implementation to check the
geometry. For v3.3 it ran seven further review rounds (see the Module 4 decision log). Xiaohui
remains responsible for reviewing them and may overturn any of them.
