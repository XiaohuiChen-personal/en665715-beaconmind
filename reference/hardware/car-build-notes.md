> Public copy for BeaconMind, 2026-10-29; the private course repo holds the unredacted original.

# Robot car — build state and physical facts

Observed from my own photos. Update as the build progresses. Companion to
[`pico2w-pin-map.md`](pico2w-pin-map.md).

## State on 2026-09-19 (photo `IMG_7220`)

**Mechanical — done**
- Single clear chassis plate, caster at the rear, 4 × AA battery holder (empty) in the middle.
- **The blue Hall-encoder motors fit the chassis kit's clear T-brackets and long screws, and the
  kit's yellow-hub wheels fit the motors' metal flat shaft.** (This was the one mechanical
  compatibility question the Amazon listings could not answer.)
- Red rocker switch mounted through the plate, wired in series with the battery holder's **red (+)**
  lead — as slide 15 recommends. The switched red lead is not yet connected to the breadboard.
- Battery holder's **black (−)** lead is pushed into the **`−` column of the right-hand rail strip**,
  near row 29. Correct polarity.

**Breadboard**
- **Two 400-point boards snapped side by side** with one rail strip removed, stuck to the front of
  the plate above the motors. Strip order left → right:
  `[+ −] [a–e] [f–j] [+ −] [a–e] [f–j] [+ −]`, rows numbered 1–30 on each board.
- So there are **3 rail strips = 3 separate `+` rails and 3 separate `−` rails.** Snapping boards
  together is mechanical only; the rails are **not** joined to each other. Common ground needs a
  jumper between the `−` rails. `+` rails that carry different voltages must never be bridged.
- Rail print order is `+` then `−` on **every** strip (not mirrored): on the far-left strip the
  `−` column is next to column `a`; on the far-right strip the `+` column is next to column `j`.
- Row 30 end is directly above the motors (magnets); row 1 end is at the front arc.

**Motor cables**
- Each motor's 6-wire rainbow cable ends in **six separate female Dupont sockets**. They cannot go
  into breadboard holes directly; use male-to-male jumper wires as adapters (or plug onto male
  header pins).
- **Wire colours are not yet mapped to functions.** Map them by reading the plug at the motor, whose
  pin order is `(−)(5V)(B)(A)(GND)(+)` — outer two = motor power, inner four = encoder. Do not
  guess from colour.

## Still to do before wiring
- Solder headers: TB6612FNG (2 × 8), BNO055 (6-pin row at minimum), 5 V buck module (4-pin).
- Test-fit the TB6612FNG's two header strips in the breadboard **before** soldering — its row
  spacing is not published.
- Set and meter the 5 V buck module before any load is connected to it — see [`buck5v-pin-map.md`](buck5v-pin-map.md) §3 (needs ≳ 5.6 V in for the trimmer method; my delivered boards carry a `4R7` inductor, unlike the listing photos).
- ~~Photograph the TB6612FNG underside labels~~ — done, see [`tb6612fng-pin-map.md`](tb6612fng-pin-map.md) (row spacing ≈ 0.6 in).
- ~~Photograph the plug at one motor~~ — done: black · red · blue · green · yellow · red; see [`motor-encoder-cable-map.md`](motor-encoder-cable-map.md). **Next: its §5 bench check on both cables, then tape-flag the two motor reds.**

## Update 2026-09-19 (photo `IMG_7239`) — camera installed; front defined

- **ESP32-CAM unit taped flat at the caster end, USB-C facing outward.** See
  [`esp32cam-notes.md`](esp32cam-notes.md) §7 for the screw-short check and the forward-view plan.
- **The caster end is now the FRONT of the robot** (the camera defines it). Consequences to carry
  into the wiring diagram and firmware: **left/right are mirrored** relative to viewing the robot
  from the breadboard end — "motor L" is the wheel on the robot's left when facing the caster end.
  Forward direction and L/R assignment are both set in software; no rewiring is ever needed for them.
- Stick antenna mounted upright near the battery holder / breadboard corner, anchored to the chassis.
  Electrically inert (selector resistor untouched).
- Motor cable ends re-checked: **female** Dupont sockets.

## Update 2026-09-19 — first live wiring on the breadboard

- **Pico 2 W seated** with its USB-end pins in breadboard row 1. Power-side **row 3 (`GND`) → `−` rail**,
  **row 5 (`3V3`) → `+` rail**, that rail labelled 3V3. Measured **3.32 V** on USB power.
- **One motor's encoder is wired and working**: inner red → 3V3 rail, yellow → `−` rail; signals swing
  0 ↔ 3.32 V, encoder LED lit. Its black and flagged-red motor wires are still unconnected.
- This completes wiring-plan stages 2–3 (in part) and 4b for one motor. Second motor's cable: checks pending.

## Update 2026-09-20 — wiring complete, every stage measured

Built step by step against [`../../assignments/assignment3/Chen-Assign3.fzz`](../../assignments/assignment3/Chen-Assign3.fzz).
Every stage was verified with the multimeter before the next one was added.

**As built** — view: row 1 at the top, column `a` on the left, three rail strips each printed `+` then `−`.

| Item | Seated at | Notes |
| --- | --- | --- |
| Pico 2 W | left board, **cols b + g**, rows 1–20 | USB end at row 1. Blocked holes c–f; usable `a`, `h`, `i`, `j` |
| TB6612FNG | left board, **cols c + g**, rows 22–29 | `VM` at row 29 col g, `PWMA` row 29 col c |
| BNO055 | right board, **cols b + g**, rows 1–6 | 6-pin row in col g, **`RST` at row 1 → `Vin` at row 6** |
| AMS1117-3.3 | right board, **col e**, rows 11–13 | `VIN` 11, `OUT` 12, `GND` 13 |
| 5 V buck | right board, **col e**, rows 27–30 | `EN` 27 (unconnected), `IN+` 28, `GND` 29, `VO+` 30 |

**Rail allocation as built** (matches [`wiring-plan.md`](wiring-plan.md) §4):

| Strip | `+` measured | Source |
| --- | --- | --- |
| Left | **5.03 V** | buck module, set by trimmer with `VO+` unloaded, re-checked on the rail |
| Middle | **3.3 V** | Pico pin 36 → BNO055 `Vin`, TB6612FNG `VCC`, both encoder supplies |
| Right | **6.67 V** | 4×AA alkaline (1.67 V/cell) through the rocker switch |

All three `−` rails jumpered together (left↔middle, middle↔right). No two `+` rails ever joined —
re-verified at every power-up by reading the two idle rails as 0 V.

**GPIO as built:** `GP0` SDA, `GP1` SCL → BNO055 · `GP2` PWMA, `GP3` AIN2, `GP4` AIN1, `GP5` STBY,
`GP6` BIN1, `GP7` BIN2, `GP8` PWMB → TB6612FNG · `GP16`/`GP17` right encoder A/B · `GP18`/`GP19` left
encoder A/B. Motor `+` → `AO1`/`BO1`, motor `−` → `AO2`/`BO2` on both channels.

### Battery tray fault found and fixed (2026-09-20)

**Symptom:** 0 V at the tray leads while every cell measured 1.67 V and the switch had continuity.

**Diagnosis** — the decisive test was a voltage sweep with the cells *in*, black probe parked on the
red lead, red probe touching all eight contacts. The readings grouped into nodes and mapped the tray:

```
black lead ─ T3 ┊ cell3 ┊ B3═B2 ┊ cell2 ┊ T2═T1 ┊ cell1 ┊ B1═B4 ┊ cell4 ┊ T4 ─ red lead
```

i.e. leads at **compartment 3 top** and **compartment 4 top**, with a link strip running the length of
the tray joining compartments 1 and 4 at the bottom. A floating contact reads ~0 V against the
reference, which is how the break was located: `T3` read 0 where it should have read 6.69 V.

**Root cause:** the black wire is soldered as a blob *inside* the `T3` spring. The blob takes up length
in the compartment, so cell 3 could not reach the flat plate at the far end (`B3`). The open joint was
**cell 3's `+` nub against `B3`**, not anything at the spring end.

**Fix:** the spring was bent outward with pliers so it presses the cell harder onto `B3`. Pack now reads
**6.67 V**, steady through a shake test (press each cell, wiggle, tilt, tap, flex the leads).

◻ **Watch this joint.** Nothing was re-soldered, and a spring that has been annealed by soldering can
relax. If the robot ever browns out or the motors cut mid-run, suspect this before firmware. The
durable fix is to reduce the solder blob so the cell seats fully.

### Untethered power — works, but the wire comes out for USB work

AMS1117 measured **3.4 V** unloaded (confirms it is the 3.3 V part — the chip's voltage code was
unreadable). With `OUT` → Pico `VSYS` (pin 39, row 2) and **USB unplugged**, the Pico runs from the
battery: middle rail 3.3 V, encoder LEDs lit, IMU and driver logic powered.

⚠ **`VSYS` and USB must never be live together** — no Schottky diode in the kit. The dangerous case is
the quiet one: **USB in with the battery switch OFF**. USB then puts ~4.7 V on `VSYS`, above the
AMS1117's own input at 0 V, so current flows backwards through the regulator onto the VBAT rail and
into `VM`, the buck input and the battery. **The `OUT` wire is removed during USB development.**

### Notes for the firmware bring-up

- **The Pico 2 W's LED is not a power indicator.** It hangs off the CYW43 wireless chip, not a normal
  GPIO, and lights only when firmware brings that chip up. It stayed dark on battery power while
  everything measured correct.
- **`STBY` must be driven HIGH** or the motors never move, however good the wiring is.
- Still unverifiable with a meter, and therefore the first firmware tests: I2C scan answering at
  `0x28`; encoder quadrature *direction* (only the swing 0 ↔ 3.3 V has been confirmed); motor
  direction per channel.

## Update 2026-09-23 — Pico 2 W flashed with the micro-ROS LED image

The board is no longer a blank Pico. It runs `pico2w_led` (RP2350 / Cortex-M33): Wi-Fi to the LAN, one `/pico2w_led` node, LED topics only. The onboard CYW43 LED beside the micro-USB plug was lit and photographed. Procedure, agent container, and reflash steps: [`pico-bringup.md`](pico-bringup.md).

For that USB session the green AMS1117 `OUT` → `VSYS` jumper was removed. The battery switch stayed off. This image does not drive the motors, encoders, or IMU. Those tests below are still open.

## Update 2026-10-01 — three wires moved for Module 5; IMU and tilt firmware running

**Wiring change.** The instructor's Module 5 firmware drives the right-motor channel from `GP10`
(`BIN1`), `GP11` (`BIN2`) and `GP12` (`PWMB`). The car had them on `GP6`/`GP7`/`GP8` (my Assignment 3
choice), so I moved the three jumpers at the Pico end: left board, column `a`, rows 9/10/11 → rows
14/15/16. The driver ends did not move. Everything else matched the guide already. **GPIO now:**
`GP0` SDA, `GP1` SCL · `GP2` PWMA, `GP3` AIN2, `GP4` AIN1, `GP5` STBY, `GP10` BIN1, `GP11` BIN2,
`GP12` PWMB · `GP16`/`GP17` right encoder A/B · `GP18`/`GP19` left encoder A/B (encoders stay wired;
the Module 5 firmware does not use those pins).

**I2C check.** On my BNO055, breadboard row 2 is `SCL` and row 3 is `SDA` — the reverse of the part
in the Fritzing drawing. Continuity test with the power off: Pico pin 1 (`GP0`) ↔ `SDA` and pin 2
(`GP1`) ↔ `SCL` beep, the cross pairs do not. Confirmed again by the firmware: the BNO055 is found
at boot and `/pico/imu/pitch` publishes.

**Power for this session.** The green AMS1117 `OUT` → `VSYS` jumper is **out** (the whole wire was
removed), USB from the Spark powers the Pico, and the battery feeds only `VM` and the two
regulators' inputs through the rocker switch.

**Firmware.** The Module 5 tilt image is on the Pico — see [`pico-bringup.md`](pico-bringup.md).

**After the session (2026-10-01, evening): the `VSYS` jumper is back IN** and the USB cable is
unplugged, so the Pico is again powered from the battery switch through the AMS1117. ⚠ **Pull the
jumper before the next USB connection** (flashing, serial console). With the tilt firmware on the
board and the jumper in, switching the battery on boots the Pico and powers the motor driver at the
same moment: it stays idle until a request arms it, but keep the wheels off the table.

### Dead right wheel found and fixed (2026-10-01): the driver board was not fully seated

**Symptom.** On the first motor run only the left wheel (channel A) turned, while the firmware
reported the normal status sequence. The firmware is open loop, so the statuses say nothing about
whether a wheel moves.

**Diagnosis**, with a diagnostic firmware (`assignments/assignment5/diagnostics/pintest/`) and the
multimeter; readings are in `assignments/assignment5/evidence/diagnostics/`:

1. Control signals reach the driver: with a distinct PWM duty on each pin, the driver's pin tops read
   0.83 / 1.66 / 2.49 V on `PWMA`/`AIN2`/`AIN1` and the same on `BIN1`/`BIN2`/`PWMB`. So the three
   wires moved to `GP10`/`GP11`/`GP12` are right.
2. Pulsing each motor alone: motor A about 4500 encoder edges per 1.5 s in both directions, motor B
   zero in both.
3. The right wheel turns freely by hand and its encoder counts, and a voltage appears across
   `BO1`–`BO2` when it is turned (the motor and its wires reach the driver pins).
4. With motor B driven, `BO1` (row 23) read 5.73 V; **the wheel started the moment the probe pressed
   on the `BO2` pin (row 24)**.

**Cause.** The driver board was not pushed fully into the breadboard, so its row-24 pin (`BO2`) was
not gripped by the breadboard contact and only touched under pressure. **Fix:** press the board down
firmly and evenly. After that, motor B gave about 4700–4900 edges per pulse in both directions, three
times each, with nobody touching it. No soldering was needed.

◻ **Watch this contact.** If a wheel goes dead again, press the driver board down first. The motor
cables tug on that corner of the board.

**Wheel direction under the Module 5 firmware (my observation of the four runs on 2026-10-01):** both
wheels turned in every run, both the same way as each other, and the backward requests reversed
them. So the firmware's reversal of channel A suits my mirror-mounted motors and neither motor's
wires need swapping. **Still not recorded:** whether the firmware's "forward" moves the car toward
the caster end (my front) or away from it.

**Two readings to remember.** A DMM on its lowest ohms range reads these motors at about 65 Ω at
rest (both of them), far above what the stall current implies; and the battery pack now reads about
5.7 to 5.9 V at the driver (it was 6.67 V on 2026-09-20).

## Update 2026-10-19 — driver board replaced, three jumpers replaced, the green wire on `VSYS`

The diagnosis behind these changes is in
[`assignments/assignment7/evidence/precheck-notes.md`](../../assignments/assignment7/evidence/precheck-notes.md)
(section "2026-10-18 evening → 2026-10-19 early"). Changes made by me, Xiaohui, on 2026-10-18/19:

| What | Before | Now |
| --- | --- | --- |
| **TB6612FNG driver** | the original board, re-soldered 2026-10-17 (BO1, then VM, VCC and STBY) | **the spare board** (HW-166), headers soldered 2026-10-19, same seat: columns c + g, rows 22–29, `VM` at row 29 column g. The old board is set aside: no solder bridges found, capacitors intact, two over-soldered joints (probably `BO2` and `VCC`) |
| **Green AMS1117 `OUT` jumper** | plugged into the **middle `+` rail** (3.3 V, joined to Pico pin 36 by the orange wire). This had been my usual wiring, unlike the design below, so the AMS1117 fed the Pico's 3.3 V side directly | a new jumper in **left board row 2, column j = Pico `VSYS` (pin 39)**, as designed in [`wiring-plan.md`](wiring-plan.md) decision 4. The Pico's own regulator now makes its 3.3 V, and it works down to 1.8 V at `VSYS` |
| **Driver ground** (row 27, column h → middle `−` rail) | insulation melted by the soldering iron | new jumper |
| **Right encoder supply** (inner red → middle `+` rail) | insulation melted by the soldering iron | new jumper |
| **Right motor `+` / `−`** | (unplugged during the board swap) | red `+` → `AO1` row 26 column i; black `−` → `AO2` row 25 column i |
| **5 V buck `VO+`** (right board 30-d) | (unplugged during the board swap) | back on the left strip's `+` rail (camera supply only) |

⚠ **The interlock is unchanged: pull the green wire before plugging in USB**, wherever it sits, and put it back only
after the USB cable is out.

**Battery tray, measured again.** With one free-spinning motor the tray lost **≈ 0.87 V** between the cells' own
terminals and its leads (cells 4 × 1.43 V = 5.72 V, leads 4.85 V). By contact: the red lead's contact on its cell
0.38–0.50 V, the long link strip 0.11–0.43 V, two others up to 0.16–0.18 V, the best 0.02–0.08 V. This is the tray
whose spring was bent on 2026-09-20 (above). **Still to do:** clean the springs and plates, re-tension them, and put a
rubber band over the cell ends, or replace the tray; it also has to carry the rechargeable cells.

**Right motor: replace.** It sometimes will not start at all: with the old driver board it buzzed without turning
until nudged (my observation); with the new one, logged on USB power, it moved 6 counts in 8 s at duty 0.96 and 0 in
3 of 4 start pulses, then started 3 of 3 times about 2.4 minutes later. Its current appears to rise when it slows
(inferred from the cell voltage, not measured). Until a new motor
arrives, firmware Build F gives a stalled wheel up to three reverse-and-forward jogs per start (`drive_control.c`).

## Update 2026-10-20 — right motor replaced; the original power wiring back for a test

Changes made by me, Xiaohui, before the 2026-10-20 bench session. The aim is to test the new motor on the power wiring
the car used before the 2026-10-17 re-soldering. Cells: Energizer Ultimate Lithium AA (L91).

| What | Before (2026-10-19) | Now |
| --- | --- | --- |
| **Right TT motor** | the original, which often would not start (above) | **replaced** with a motor of the same type (blue 1:90 TT with the Hall encoder); the old cable's plug moved onto it, so the breadboard ends are unchanged |
| **Green AMS1117 `OUT` jumper** | left board row 2, column j (`VSYS`, pin 39) | **back on the middle `+` rail** (3.3 V, joined to Pico pin 36 by the orange wire): the original setup, in which the AMS1117 feeds the Pico's 3.3 V side directly |
| **Camera supply** | the camera on its own USB-C | the red jumper from the 5 V buck's `VO+` (right board 30-d) back on the left strip's `+` rail, and the **ESP32-CAM's 5V pin on that rail** (its USB-C unplugged: never both). The camera is now a load on the battery (about 0.18 A at 5 V, never measured on this car) |

What this wiring means for testing (from the 2026-10-17/18 diagnosis in `precheck-notes.md`):
- The black box's `VSYS` reading no longer measures the Pico's supply (it read ≈ 0.07 V with this wiring, runs
  `d13`–`d15`), so a supply dip shows only as a reset or a silent Pico. A meter on the battery side is the only way to
  watch the voltage.
- The AMS1117 needs about 4.6 V in. With this wiring the Pico crashed at motor starts on battery (`d13`, `d18`); the
  diagnosis blamed the battery path (tray contacts, switch) and the sticking motor's current. This test shows how much
  of that the new motor fixes.
- ⚠ **The interlock still applies: pull the green wire before plugging in USB**, and put it back only after the USB
  cable is out. With the wire on the 3.3 V rail, USB would tie the Pico's own 3.3 V regulator to the AMS1117 output.

**Result (bench session, `assignments/assignment7/evidence/new-motor-bench-2026-10-20.md`):** the new motor starts
every time, but on battery this wiring still HardFaulted the Pico twice on the floor (mid-spin, and at the start of
a straight). It runs about 2.4× faster than the left motor at the same duty.

### Decision 2026-10-20: a USB power bank for the Pico and the camera

I will power the Pico and the camera from a two-port USB power bank on the car; the AA pack then runs only the motors
(camera option A in [`esp32cam-notes.md`](esp32cam-notes.md) §5; the alternative noted under "Cleaner alternative"
below). Planned wiring: the green AMS1117 `OUT` jumper out entirely; the camera back on its base board on USB-C, its
`5V`/`GND` pin jumpers removed; the buck's `VO+` jumper (30-d) out.

| Power bank | |
| --- | --- |
| Shape | black rectangular block |
| Size (my measurement) | **70 × 70 × 25 mm** |
| Ports | two USB outputs (types and faces not recorded yet) |
| Not recorded yet | mass, capacity and output rating, where it sits on the car |

## TODO — open items as of 2026-09-23

Nothing here blocks Module 3; the wiring diagram is submitted and the car is fully wired and
measured. Ordered roughly by when each will matter.

### 1. Firmware bring-up — the tests a multimeter cannot do

The LED micro-ROS image is already on the Pico (2026-09-23). See [`pico-bringup.md`](pico-bringup.md). It does not cover the tests in this list.

- **I2C scan** must answer at `0x28`. This is the first proof that `GP0`/`GP1` reach the right
  BNO055 holes, which matters because my board is the Adafruit 2472 and its `SDA`/`SCL` are swapped
  relative to the part in the drawing — it is wired by label, not by the picture.
- **`STBY` must be driven HIGH** or the motors never move however good the wiring is. This is the
  classic "nothing happens" cause with the TB6612FNG; check it before suspecting anything else.
- **Encoder direction.** Only the *swing* (0 ↔ 3.3 V on both channels, both motors) has been
  confirmed. Quadrature phase — which of `A`/`B` leads — cannot be seen on a meter and may be
  reversed on either motor. Harmless; fix the sign in software.
- **Motor direction per channel.** Same: if a wheel runs backwards, invert it in firmware. The
  motors are mirror-mounted, so one side's direction and count sign are inverted anyway.
- **Power-up order every time:** Pico first (USB *or* the `VSYS` jumper), battery switch second.
  Power-down: switch first. This is Toshiba's requirement — logic supply before motor supply.

### 2. Camera power — deferred on purpose (2026-09-20)

Running on its own USB-C for now. Option B (the robot's 5 V rail, which is wired and sitting at
5.03 V unloaded) is deferred for two reasons, neither of them about mounting — the camera's pins are
reachable from the top of the stack, so it does **not** have to come apart:

- **It would be a second "never both at once" rule.** The camera's `5V` pin is the same net as the
  base board's USB-C 5 V, so feeding the rail into it with USB plugged in puts two supplies in
  parallel and back-feeds the port. That interlock plus the `VSYS` one is two invisible hazards on
  one robot.
- **Brownout risk.** Each motor can pull ≈ 0.8 A at stall from the same pack the buck runs from. The
  symptom would be "video drops when the robot moves", which reads like a WiFi or firmware bug.

**Cleaner alternative:** a small USB **power bank** on the chassis. Untethered operation with no
shared-battery sag and no second interlock.

**When option B is wired:** `5V` and the `GND` **immediately beside it** — *not* `GND/R` at the far
end of the opposite edge, which is reported to be the reset line on boards sold with a base board.
Continuity-check the top terminal against the camera's own `5V` hole first, and test with the
**motors actually running**, not stationary.

### 3. Watch items

- ◻ **The battery tray spring** was bent, not re-soldered (see the 2026-09-20 fault write-up above).
  An annealed spring relaxes. **First suspect on any brownout or mid-run motor cut** — before
  firmware. Durable fix: reduce the solder blob so the cell seats fully on the far plate.
- ◻ **Pack voltage as the cells age.** At ≈ 5.5 V the buck loses headroom and the 5 V rail droops
  before anything else shows it.
- ◻ **WiFi range.** The stick antenna is mounted but **electrically inert** — the selector resistor
  was deliberately left alone. If the video link is weak, check power/brownout, antenna-end
  clearance, stream resolution, the 2.4 GHz band and RSSI *before* reconsidering that rework.
- ◻ **Module 3 dates** are still `_dates not recorded_` in the AGENTS.md module map — confirm from
  Canvas.

### Decision 2026-10-21: replace the left motor

The bench session of 2026-10-21 (`assignments/assignment7/evidence/new-motor-bench-2026-10-20.md`, from "Motor balance
history" on) found the **original left TT motor** weak: with the car lifted it ran 592-2,451 counts/s from duty 0.56 to
0.96, against 3,707-6,059 for the new right motor, and it stuck once at a start. With both wheels running, the right one
fell to a third of its own speed, so a per-wheel calibration cannot fit (likely the shared supply sagging under the left
motor's current; the tray's 0.87 V loss from 2026-10-19 is still open). I will replace the left motor with the same type
(blue 1:90 TT with the Hall encoder), moving the old cable's plug onto it as for the right; then the floor and lifted
calibrations (`m23_cal`, `m23_lifted`) are rerun before any per-wheel maps or PID. Still to do as well: the battery
tray's springs and plates, or a new tray.
State left on the car: Pico and camera on the power bank (camera unplugged during the Wi-Fi tests), AA pack (fresh L91
cells, 2026-10-21) for the motors only, green wire out, firmware Build G.1 Flash B.
