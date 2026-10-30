> Public copy for BeaconMind, 2026-10-29; the private course repo holds the unredacted original.

# Wiring plan — running picture of the robot's connections

**Purpose.** A plain-language net list that grows as each board is examined, so that drawing the
Fritzing diagram (Module 3, LO 3.1) becomes a matter of transcription. **Start here** before any
wiring work; the per-board pin maps sit beside this file.

**Status: DRAFT — GPIO numbers are not final.** The instructor's `.fzz` file (to be provided) and
the course firmware decide them. Everything marked ✔ is settled by a datasheet or by my own
board; everything marked ◻ is waiting on something named in the last column.

| Board | Pin map | Examined from my own hardware? |
| --- | --- | --- |
| Raspberry Pi Pico 2 W | [`pico2w-pin-map.md`](pico2w-pin-map.md) | ✔ 2026-09-19 |
| Adafruit BNO055 IMU | [`bno055-pin-map.md`](bno055-pin-map.md) | ✔ 2026-09-19 |
| TB6612FNG motor driver (`HW-166`) | [`tb6612fng-pin-map.md`](tb6612fng-pin-map.md) | ✔ 2026-09-19 |
| Hall-encoder motors + 6-wire cables | [`motor-encoder-cable-map.md`](motor-encoder-cable-map.md) | ✔ 2026-09-19 (colour map **confirmed by meter and by a powered 3.3 V test on one cable** — signals 0 ↔ 3.32 V, LED lit; second cable pending) |
| 5 V buck module (DKARDU) | [`buck5v-pin-map.md`](buck5v-pin-map.md) | ✔ 2026-09-19 |
| AMS1117-3.3 module | [`ams1117-pin-map.md`](ams1117-pin-map.md) | ✔ 2026-09-19 (chip's voltage code illegible → bench-test `OUT`) |
| ESP32-CAM + MB base + OV3660 + antenna | [`esp32cam-notes.md`](esp32cam-notes.md) | ✔ 2026-09-19 |
| Car build state | [`car-build-notes.md`](car-build-notes.md) | ✔ 2026-09-20 wiring; Pico flashed 2026-09-23 — [`pico-bringup.md`](pico-bringup.md) |
| Fritzing (the diagram tool) | [`fritzing-setup.md`](fritzing-setup.md) | ✔ 2026-09-19 — 1.0.2 installed, verified genuine, runs and renders |

---

## 1. The picture so far

```
                        ┌─────────── switch ───────────┐
   4×AA battery  (+) ───┘                              ├──► TB6612FNG  VM   (motor power, raw battery)
                                                       └──► 5 V buck  IN+ ──► VO+ ──► ESP32-CAM 5V
                 (−) ───────────────► COMMON GROUND  (every board's GND joins here)

   Pico 2 W  pin 36  3V3(OUT) ──┬──► BNO055     Vin
   (its own 3.3 V regulator)    ├──► TB6612FNG  VCC   (logic supply)
                                ├──► Encoder L  "5V" pin   (fed 3.3 V on purpose)
                                └──► Encoder R  "5V" pin   (fed 3.3 V on purpose)

   Pico GPIO ──── I2C  SDA, SCL ───────────────► BNO055
   Pico GPIO ◄─── A, B ──────────────────────── Encoder L
   Pico GPIO ◄─── A, B ──────────────────────── Encoder R
   Pico GPIO ──── PWMA AIN1 AIN2 PWMB BIN1 BIN2 STBY ──► TB6612FNG ── AO1/AO2 ──► Motor L
                                                                  └── BO1/BO2 ──► Motor R
   ESP32-CAM: power and ground only. Images travel over WiFi, not over a wire.
```

---

## 2. Power nets

| Net | Source | Loads | Status |
| --- | --- | --- | --- |
| **GND** (common) | battery `−` | Pico GND, BNO055 GND, TB6612FNG GND, both encoder GND, 5 V buck GND, ESP32-CAM GND, (AMS1117 GND) | ✔ Required by every datasheet. The breadboard's three `−` rails must be jumpered together. |
| **VBAT** (switched) | battery `+` through the rocker switch | TB6612FNG `VM`; 5 V buck `IN+` | ✔ Motors run from the raw battery, never through a regulator (matches the instructor's drawing). 4×AA is inside the driver's range. |
| **5V** | buck module `VO+` | ESP32-CAM `5V` pin | ✔ wiring · ◻ whether it can *hold* 5 V depends on the battery choice (§6). Slide 17: camera "not needed now". |
| **3V3** | **Pico pin 36** | BNO055 `Vin`, TB6612FNG `VCC`, encoder L + R supply | ✔ ≈ 40 mA total against a 300 mA guideline. Feeding these from 3.3 V is what keeps every signal into the Pico at 3.3 V. |

**Never:** raw battery on any Pico pin · 5 V on Pico pin 36 · anything on Pico pin 37 (`3V3_EN`) ·
two supplies tied to one net · `+` rails of different voltages bridged together.

---

## 3. Signal connections

GPIO column: **✔ settled 2026-09-20** in §4 and in `assignments/assignment3/Chen-Assign3.fzz`. The
"Drawing suggests" column below is kept only as history — it is what the instructor's raster image
*appears* to use, read by counting pads — medium confidence, recorded only as a starting hypothesis.

### BNO055 IMU — 4 wires ✔ (board examined)

| BNO055 hole | Goes to | GPIO | Drawing suggests |
| --- | --- | --- | --- |
| `Vin` | Pico pin 36 (3V3 OUT) | — | — |
| `GND` | common ground | — | — |
| `SDA` | a Pico I2C **SDA** pin | ◻ | GP0 (pin 1) |
| `SCL` | the matching I2C **SCL** pin | ◻ | GP1 (pin 2) |
| `3vo`, `RST`, `PS0`, `PS1`, `INT`, `ADR` | **unconnected** | — | — |

⚠ Wire by label: the drawing's BNO055 part is a different board revision with SDA/SCL swapped.

### TB6612FNG motor driver — 7 signal wires + power ✔ (board examined)

On the breadboard the board sits **chip up with its labels hidden**. Front view, capacitor at the
top: **left column** `VM VCC GND AO1 AO2 BO2 BO1 GND`, **right column**
`PWMA AIN2 AIN1 STBY BIN1 BIN2 PWMB GND`. Rows are ≈ 0.6 inch apart (straddles the centre gap).

| Driver pin | Goes to | GPIO | Constraint |
| --- | --- | --- | --- |
| `VM` | VBAT | — | next to `VCC` on the board — do not swap |
| `VCC` | Pico pin 36 (3.3 V) | — | must be 3.3 V so the Pico's 3.3 V highs count as HIGH |
| `GND` | common ground | — | |
| `PWMA`, `PWMB` | Pico PWM outputs | ◻ | **different PWM channels** (GPn and GP(n+16) are the same channel). Drawing suggests GP2 and GP12. |
| `AIN1`, `AIN2`, `BIN1`, `BIN2` | Pico digital outputs | ◻ | any GPIO |
| `STBY` | Pico digital output | ◻ | must be driven HIGH in firmware or the motors never move. Drawing suggests GP5. |
| `AO1`/`AO2`, `BO1`/`BO2` | motor L / motor R power wires (the **outer two** of each 6-wire cable) | — | swapping the pair reverses that motor |

### Hall-encoder motors — 6 wires each ✔ (cables examined; bench check passed on one cable 2026-09-19)

Ribbon order across the plug, both cables: **black · red · blue · green · yellow · red.** All loose
ends are **female** → one male-to-male jumper each. **Run the bench check in
[`motor-encoder-cable-map.md`](motor-encoder-cable-map.md) §5 before wiring any of this.**

| Wire | Function | Goes to | GPIO | Notes |
| --- | --- | --- | --- | --- |
| **black** (ribbon edge) | motor `−` | TB6612FNG `AO2` / `BO2` | — | battery voltage — **never to a Pico pin** |
| **red next to yellow** (other ribbon edge) | motor `+` | TB6612FNG `AO1` / `BO1` | — | battery voltage — **tape-flag this connector**; same colour as the supply wire |
| **red next to black** | encoder supply (`5V` label) | **3V3 rail** (Pico pin 36) | — | 3.3 V on purpose: the signal HIGH level equals this voltage |
| **yellow** | encoder `GND` | `−` rail | — | |
| **green** | encoder `A` | Pico interrupt input | ◻ | GP0–GP22 only. Drawing suggests GP18–GP21 for the four lines. |
| **blue** | encoder `B` | Pico interrupt input | ◻ | same |

High confidence: the two edge wires are the motor pair. Medium: inner red = supply / yellow = ground
(settled by bench-check step 4). `A`/`B` order and motor polarity are harmless if wrong — fix in
software. The motors are mirror-mounted, so one side's direction and count sign get inverted in
software.

### 5 V buck module — 3 wires ✔ (board examined)

Installed component-side up, labels hidden. Front view with the **holes at the top**, left → right:
`VO+  GND  IN+  EN` — **`EN` is the hole next to the blank strip.**

| Module hole | Goes to | Constraint |
| --- | --- | --- |
| `IN+` | VBAT (right `+` rail) | 4.5–24 V. No reverse-polarity protection. |
| `GND` | common ground | the module's only ground |
| `VO+` | 5V net (left `+` rail) | **Ships adjustable, not at 5 V.** Set and meter it with nothing connected first. |
| `EN` | **unconnected** | on by default; never to the battery rail |

### AMS1117-3.3 regulator module — optional ✔ (board examined)

Stands upright across three rows; label side facing, pins down, left → right: `VIN  OUT  GND`
(**middle pin = `OUT`**, not ground).

| Module pin | Goes to | Status |
| --- | --- | --- |
| `VIN` | VBAT (right `+` rail) | ✔ |
| `GND` | common ground | ✔ |
| `OUT` | **First build: not used** (Pico on USB). Later, to run untethered: **Pico `VSYS`, pin 39** — and never while USB is also plugged in. **Never to Pico pin 36.** | ◻ open decision 4 |

### ESP32-CAM — 0 or 2 wires ✔ (parts examined)

An independent WiFi computer: **no data wire to the breadboard, ever.** Two ways to power it — never
both at once:

| Option | Wiring | Status |
| --- | --- | --- |
| **A. USB-C on its base board** (computer or USB power bank) | **none** — nothing touches the breadboard | **working choice for first bring-up**; also the only way to load firmware |
| **B. from the robot's 5 V rail** (instructor's drawing) | camera board lifted off the base; female jumpers: `5V` ← left `+` rail, the `GND` *beside* `5V` ← `−` rail | ◻ needs the buck module set to 5.0 V **and** a battery that can hold 5 V |

Do not use the pin labelled `GND/R` as ground — on boards sold with the base board it is reported to
be the reset line. No reverse-polarity protection on the `5V` pin.

---

## 4. Rail allocation and wiring order

### Rail allocation (decided 2026-09-20 with the Assignment 3 Fritzing diagram)

My breadboard has three rail strips (view: row 1 at the top, column `a` on the left; every strip is
printed `+` then `−`). Each `+` rail has **one** job — label it with tape:

| Rail strip | `+` rail carries | `−` rail |
| --- | --- | --- |
| Left | **5V** (from the 5 V module — camera only) | GND |
| Middle | **3V3** (from Pico pin 36) | GND |
| Right | **VBAT** (switched battery +) — the battery's black lead is already in this strip's `−` rail | GND |

All three `−` rails are jumpered together (left↔middle, middle↔right). **No two `+` rails are ever joined.**

**Changed from the first proposal (left = 3V3, middle = 5V).** With the Pico's USB end at row 1, its
`3V3` (pin 36, row 5) and `GND` (pin 38, row 3) pins sit on the side facing the **middle** strip, and
every 3.3 V load (BNO055, TB6612FNG `VCC`, both encoder supplies) reaches the middle strip without a
jumper having to cross the Pico or the seven driver control wires. 3V3 and VBAT are still on different
strips with a whole board between them, so the one catastrophic mistake — battery voltage on the
3.3 V net — stays physically hard to make. The tables and wiring
order in this file have been updated to match.

**Pin assignments — current, since 2026-10-01:**
`GP0` SDA, `GP1` SCL → BNO055 · `GP2` PWMA, `GP3` AIN2, `GP4` AIN1, `GP5` STBY, **`GP10` BIN1, `GP11` BIN2,
`GP12` PWMB** → TB6612FNG · `GP16`/`GP17` right encoder A/B · `GP18`/`GP19` left encoder A/B ·
driver channel **A = left wheel** (`AO1` → motor `+`, `AO2` → motor `−`), channel **B = right wheel**
(`BO1` → motor `+`, `BO2` → motor `−`). Motor polarity and A/B order are harmless if reversed — fixed in firmware.

> **As built (observed 2026-10-11, Module 6 discussion):** on the car, channel **A drives the RIGHT wheel** (camera
> end = front), and both channels roll toward the drive-wheel end on the instructor's "forward". The Module 6 drive
> firmware fixes it with `tb6612_set(-right_duty, -left_duty)`; verified with the IMU heading. The encoder pin sides
> above are unverified for the same reason. Evidence and open items:
> [`course-project/research/2026-10-11-sim-to-real-drive-lessons.md`](../../course-project/research/2026-10-11-sim-to-real-drive-lessons.md) F1.

> **Changed 2026-10-01 for Module 5.** The diagram submitted for Assignment 3
> (`assignments/assignment3/Chen-Assign3.fzz`) put the right-motor channel on `GP6` BIN1, `GP7` BIN2,
> `GP8` PWMB. The instructor's Module 5 firmware (`tb6612.c`) drives `GP10`, `GP11`, `GP12` instead, so
> those three wires were moved at the Pico end: left board column `a`, rows 9/10/11 → rows 14/15/16
> (Pico pins 14/15/16). `GP6`–`GP8` are now free. **The submitted diagram is therefore out of date
> for these three wires**; everything else in it still matches the car. `GP12` is PWM slice 6A and
> `GP2` is slice 1A, so the two PWM lines are still on different channels.
> (An earlier version of this paragraph also said `AO2` → left motor `+`; that was a leftover from the
> first draft. The as-built record in `car-build-notes.md`, the diagram and stage 6 below all have
> `AO1` → motor `+`.)

### Wiring order — for the boards examined so far (Pico 2 W, BNO055, TB6612FNG)

Principle: **ground first, lowest energy next, battery last — and test after every stage**, so a
fault is always in the few wires just added. (Same idea as committing small changes with a test
after each.) Batteries out and USB unplugged whenever wires are being moved.

| Stage | Do | Then check (multimeter) |
| ---: | --- | --- |
| **0** | **Solder headers.** Practise on a spare TB6612FNG, then the real one, then the BNO055 last. Inspect every joint; continuity-check that no neighbouring TB6612FNG pads are bridged. | No beep between adjacent pads, above all `VM`–`VCC`. |
| **1** | **Place the boards, no wires.** Pico with its USB socket at a board edge; BNO055 at the row-1 end (away from the motors); TB6612FNG at the row-30 end (next to the motors). | Each board straddles the centre gap; nothing shares a 5-hole group by accident. |
| **2** | **Ground network.** Jumper the three `−` rails together. Then one wire each: Pico `GND` → `−`, BNO055 `GND` → `−`, TB6612FNG `GND` → `−`. | Continuity beep from the battery's black lead to each board's GND pin. |
| **3** | **3.3 V logic power.** Pico **pin 36** → middle `+` rail. From that rail: BNO055 `Vin`, TB6612FNG `VCC`. *Count from the USB end: 40, 39, 38, 37, **36**.* | Plug in USB only (no batteries). Expect ≈ 3.3 V from the 3V3 rail to GND, at BNO055 `Vin`, and at TB6612FNG `VCC`. Unplug. |
| **4** | **I2C.** BNO055 `SDA` and `SCL` → the Pico's I2C pins. Wire by the printed labels. | With firmware: an I2C scan answers at `0x28`. |
| **4b** | **Encoders.** *After the bench check has passed for both cables.* Per motor, through male-to-male jumpers: inner red → 3V3 rail, yellow → `−` rail, green and blue → two Pico GPIO inputs. Black and the flagged red stay **taped and unconnected** for now. | USB only: turn each wheel a little and stop, several times — each signal reads near 0 V or near 3.3 V, and both states appear. |
| **5** | **Driver control lines.** Seven wires, Pico GPIO → `PWMA AIN1 AIN2 PWMB BIN1 BIN2 STBY`. | Visual check against the front-view pin map. No power needed. |
| **6** | **Motor outputs.** Per motor, via male-to-male jumpers: flagged red (motor `+`) → `AO1` (left wheel) or `BO1` (right wheel), black (motor `−`) → `AO2` or `BO2` — same convention on both channels, as drawn in `Chen-Assign3.fzz`. Motor L / R are named with the **caster end as the front**. | **Neither black nor a flagged red lands on a Pico pin or the 3V3 rail.** No power needed. |
| **7** | **Battery to the motors.** Switched battery `+` → right `+` rail (VBAT) → TB6612FNG `VM`. | **Before** the wire reaches `VM`: batteries in, switch on, VBAT rail reads **positive** ≈ 4.8–6 V against GND. Switch off, then connect `VM`. |

| **8** | **5 V module — the very end, and optional for now** (slide 17: camera power "not needed now"). First, *on the bench with nothing on `VO+`*: power `IN+`/`GND` and set the output with the trimmer (my chosen method). Then `IN+` → VBAT rail, `GND` → `−`, `VO+` → left `+` rail. | `VO+` reads **5.0 V** (4.75–5.25 V) against GND with no load, *then* again with the robot's real battery pack fitted. |
| **9** | **ESP32-CAM — only if powering it from the robot (option B).** Seat the camera ribbon first, power off. Camera board off its base; `5V` pin ← left `+` rail, the `GND` pin beside it ← `−`. **No USB cable in the base board at the same time.** With option A (USB-C) this stage is skipped entirely. | Polarity checked with the meter *before* the jumpers go on. Camera boots without resetting when WiFi starts. |

| *opt.* | **AMS1117 module — only when going untethered.** Bench-test it first (`OUT` = 3.20–3.40 V with nothing connected). Then `VIN` → VBAT rail, `GND` → `−`, `OUT` → Pico pin 39 (`VSYS`). | **USB unplugged** before the `OUT` jumper goes in. Pico boots from the battery switch alone. |


**Power-up sequence, every time:** Pico first (USB), battery switch second. **Power-down:** battery
switch first. This is Toshiba's required order (logic supply before motor supply).

---

## 5. Pico pin budget

26 GPIO available; this design uses **13** (2 I2C + 4 encoder + 7 driver), plus pin 36 (3.3 V out)
and ground pins. Plenty spare for later sensors (the syllabus mentions a ToF sensor).

---

## 6. Open decisions

All the decisions that blocked wiring are now closed. What remains is listed as **TODO** at the end
of [`car-build-notes.md`](car-build-notes.md).

1. ~~**GPIO assignments**~~ **Decided 2026-09-20** — see §4. The instructor's starter `.fzz` carries
   no wiring, so I chose them; they are recorded in `Chen-Assign3.fzz` and checked by
   `build/netcheck.py`.
2. ~~**How the Pico is powered on the moving robot.**~~ **Decided 2026-09-20: both, one at a time.**
   USB while developing; `AMS1117 OUT` → `VSYS` (pin 39) for untethered runs, measured working on
   2026-09-20 (Pico boots on battery alone, 3.3 V rail up, encoder LEDs lit). ⚠ **Never both** —
   there is no Schottky in the kit, and the dangerous case is USB in with the battery switch OFF,
   which back-feeds ≈ 4.7 V through the regulator onto the VBAT rail. **The `OUT` jumper comes out
   for USB work.**
3. ~~**Battery chemistry.**~~ **Settled in practice 2026-09-20: 4 × alkaline, measured 6.67 V**
   (1.67 V/cell). That is comfortably above what the buck needs to hold 5 V, so the camera rail is
   viable; the NiMH objection would return with a 4.8 V pack. Watch it as the cells age — once the
   pack falls to ≈ 5.5 V the buck loses headroom and the 5 V rail droops first.
4. ~~**What is the AMS1117-3.3 module for?**~~ **Answered: untethered running only.** Measured
   3.4 V unloaded on 2026-09-20, which also confirms it is the 3.3 V part (the chip's voltage code
   was unreadable). `OUT` → Pico `VSYS` pin 39. **Never `OUT` → pin 36.** See decision 2 for the
   interlock.
5. ~~**5 V module setting.**~~ **Decided 2026-09-19: trimmer + multimeter** (no trace-cutting; a
   mis-set screw is reversible, a slipped knife is not). **Set to 5.03 V on 2026-09-20** with
   `VO+` unloaded, then re-checked on the rail. Re-measure whenever the board is handled or the
   battery type changes.
6. ~~**How the camera is powered.**~~ **Decided 2026-09-20: option A (its own USB-C, or a power
   bank on the chassis) for now**, with option B (the robot's 5 V rail) deferred. Conditions and
   reasoning are in the TODO in [`car-build-notes.md`](car-build-notes.md).
