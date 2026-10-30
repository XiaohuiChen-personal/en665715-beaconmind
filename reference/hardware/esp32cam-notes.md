> Public copy for BeaconMind, 2026-10-29; the private course repo holds the unredacted original.

# ESP32-CAM camera unit — how it works and how to connect it

**Provenance.** Read from photos of my own parts (2026-09-19): the ESP32-CAM board
(`esp32cam-board.jpg`), the underside of its USB base board (`esp32cam-mb-underside.jpg`), the
camera (`esp32cam-ov3660.jpg`), and the antenna kit. Electrical facts from the AI-Thinker ESP32-CAM
schematic and spec (as reprinted by distributors), Espressif's ESP32 datasheet and `esp32-camera`
driver, and the seller's listing (Amazon B0FVXXDQRQ), checked 2026-09-19. Ribbon-seating steps from
the Hobby Components forum guide and SunFounder's ESP32 camera docs; antenna jumper from Random Nerd
Tutorials and the seller's own photo. Retrieved 2026-09-19.

---

## 1. What I have — four pieces

| Piece | What it is |
| --- | --- |
| **ESP32-CAM board** (black, `ESP32-CAM` printed on it) | A complete small computer: an **ESP32** microcontroller with WiFi (inside the metal can on the *other* side), extra RAM for image frames, a microSD slot, a white flash LED, a 3.3 V regulator, and the **camera ribbon socket**. 2 × 8 header pins are already soldered. |
| **OV3660 camera** on an orange flex ribbon (printed `TY-OV3660`) | The image sensor and lens — 3 megapixels. The red tab is the pull-tab of a **protective film over the lens**: peel it off before use. *(The course slide says OV2640; mine is the OV3660. Espressif's driver supports both and detects which one is fitted.)* |
| **ESP32-CAM-MB base board** (the one with the **double-sided foam tape** underneath) | A USB adapter the camera board plugs into. It carries the **USB-C socket**, a USB-to-serial chip, and two buttons (`RST`, `IO0`). Its jobs: **load firmware** and **supply 5 V from USB**. The four oval slots in my photo are the USB-C socket's mounting tabs; the tape is for sticking the unit to the robot. |
| **Stick antenna + thin black pigtail cable** | An optional external 2.4 GHz WiFi antenna. The pigtail's tiny gold end (IPEX / u.FL) snaps onto the board; the threaded gold end takes the stick. **It does nothing out of the box** — see §6. |

## 2. How it actually works

```
  lens + OV3660 sensor ──ribbon──► ESP32 (buffers each frame in its extra RAM,
                                          compresses to JPEG)
                                     │
                                     └── WiFi ──► router ──► Spark (ROS 2 image node → the agent/VLM)
```

- The sensor captures frames; the ESP32 pulls them in through the 24-contact ribbon, and **serves
  them over WiFi as a web (HTTP) stream**. The Spark fetches that stream and republishes it into
  ROS 2.
- It is a **second, independent computer** riding on the robot. It does not talk to the Pico at all.
  **No data wire goes to the breadboard.** In the instructor's drawing it receives only a red and a
  black wire: power and ground.
- Why a separate board: streaming video is far too heavy for the Pico, which must keep its timing
  for the motors and encoders.

---

## 3. The 16 header pins (as printed on my board, camera side up, SD slot at the top)

| Left column ↓ | | Right column ↓ | |
| --- | --- | --- | --- |
| **`5V`** | **power in** — the one supply pin to use | `3V3` | the ESP32's own 3.3 V rail. **Never feed 5 V here** (chip maximum 3.6 V). |
| **`GND`** | **ground** — use this one, next to `5V` | `IO16` | spare GPIO |
| `IO12` | microSD data | `IO0` | camera clock **and** boot-mode select. **Leave alone** — the base board's `IO0` button uses it to enter firmware-download mode. |
| `IO13` | microSD data | `GND` | ground |
| `IO15` | microSD command | `VCC` | an **output** tap (3.3 V or 5 V depending on a link fitted at the factory). Not an input. |
| `IO14` | microSD clock | `U0R` | serial receive — used by the base board for flashing |
| `IO2` | microSD data | `U0T` | serial transmit — used by the base board for flashing |
| `IO4` | microSD data **and** the flash LED | `GND/R` | ⚠ **Do not use as ground.** On boards sold with the base board this pin is reported to be the *reset* line; grounding it holds the camera in permanent reset. |

All I/O is **3.3 V logic and not 5 V tolerant**.

**For this robot only two pins matter: `5V` and the `GND` beside it.**

---

## 4. Connecting the camera ribbon (do this first, power off)

The socket is the cream-coloured bar with a **black hinged latch** along its SD-slot side. It is a
flip-lock, **bottom-contact** connector.

1. **Open the latch:** with a fingernail, gently lift the *outer* edge of the black bar upward. It
   pivots; it does not slide or come off. It is fragile — no tools, no force.
2. **Orient the camera:** **lens facing up, away from the board**; printed side of the ribbon up
   (so the gold contacts face **down**, toward the board).
3. **Insert** the ribbon end squarely and fully into the socket, from the SD-slot side. A very
   slight wiggle helps it seat. It must go in straight and all the way.
4. **Close the latch:** press the black bar back down until it clips.
5. **Fold the camera back** so the square camera body rests on top of the metal microSD slot, lens
   up. This is exactly how the seller's assembled photo shows it.

If the ribbon is crooked or not fully home, the usual symptom is a "camera init failed" error at
start-up — not damage. Re-seat it.

*I could not identify the black block at the end of the ribbon in my photo. If it is protective
material over the gold contacts, slide it off gently first.*

---

## 5. Powering it on the robot — two ways (never both at once)

Requirement: **4.75–5.25 V**. Average draw about 0.18 A (0.31 A with the flash LED), with short,
sharp bursts when WiFi transmits. An undervoltage does no damage — the ESP32 detects it and
**reboots** ("Brownout detector was triggered"), so a weak supply shows up as a reset loop.

| | **A. USB-C on the base board** | **B. `5V` + `GND` pins from the robot's 5 V rail** |
| --- | --- | --- |
| How | Leave the camera board plugged into the base board. Feed the USB-C socket from the computer (while developing) or a **USB power bank** on the robot. | Pull the camera board off the base board (with it attached, the `5V`/`GND` pins are buried in its sockets). Two **female** jumper wires onto `5V` and the `GND` beside it → the **left** `+` rail (the 5 V strip — see [`wiring-plan.md`](wiring-plan.md) §4) and any `−` rail. |
| Needs | Nothing from the breadboard. | The 5 V buck module, set and metered — **and a battery that can hold 5 V** (4 × NiMH cannot). |
| For | No breadboard wiring, no dependence on the AA pack, firmware loading always available, the foam tape mounts the whole stack. | Matches the instructor's drawing; one battery powers everything. |
| Against | A power bank is extra weight; a USB cable while tethered. | Polarity has **no protection** — reversed red/black can destroy the board. Loses the USB port unless the boards are re-stacked. |

**Working choice: A for first bring-up** (it is also the only way to load firmware), decide on B
later. It sidesteps the one unresolved power problem in the build. Slide 17 marks camera power "not
needed now" either way.

⚠ **Do not have the robot's 5 V on the `5V` pin while a USB cable is in the base board.** The base
board's schematic is unknown, so assume the two 5 V sources would be tied straight together.

*Unverified: whether the base board's USB-C socket has the resistors that C-to-C cables and some
power banks need before they deliver power. If a C-to-C cable gives nothing, use a USB-A-to-C cable.*

---

## 6. The external antenna

### Where the socket is

On the **underside** of the ESP32-CAM board — the face with the metal can marked `ESP-32S`. In the
assembled stack that face points **down, into the gap between the two boards**, so the socket
cannot be seen or reached until the camera board is lifted off the base board.

Landmarks, from the seller's own diagram of that face:
- At one end of that face is a gold **zig-zag trace** — the built-in antenna.
- The metal can has a small **notch cut out of one corner**, on the zig-zag end.
- **The socket sits in that notch**: a tiny square part, about 3 mm, with a **gold ring and a centre
  pin**. It is an IPEX / u.FL socket.
- Right beside it are **three minute pads in a `<` shape** carrying one speck-sized resistor — the
  antenna selector.

**Confirmed on my own board (photo, 2026-09-19):** the gold ring-and-pin socket sits in the can's
corner notch beside the zig-zag trace, next to the printed board revision `V1071` — the same
revision the seller's diagram shows. With the boards stacked, the base board's USB-C shell sits
almost directly above it, so the cable **cannot** be snapped on without separating the boards.

Seen from the *camera* side, that spot is **directly beneath the flash-LED corner** — the corner
with the white/yellow LED and the `GND/R` pin, at the `ESP32-CAM`-text end (the end that sits above
the USB-C socket).

### Attaching the cable

1. Power off. Hold the camera board **by its edges** (not the camera, ribbon or SD slot) and pull it
   **straight up** off the base board, rocking very slightly. Turn it over.
2. Put the pigtail's small gold ring squarely over the socket and **press straight down** with a
   fingernail until it clicks. Never slide it on sideways.
3. Once on, the cable swivels freely. To remove it, lever the plug **straight up** from its edge —
   never pull on the cable. These connectors survive only a few dozen matings: fit it once.
4. Re-stack the boards (USB-C under the `ESP32-CAM`-text end), routing the cable out through the
   side of the gap. Check it is not pinched between the boards or against the USB-C shell.
5. **Anchor the gold threaded end** to something solid on the chassis before screwing the stick on.
   Left hanging, the stick's weight works through the hair-thin cable and will tear the tiny socket
   off the board.

### ⚠ Snapping the cable on does not switch the antenna over

The selector resistor decides which antenna the radio uses, and **the factory position is ① = the
built-in antenna** (seller's note: "The default value is the onboard antenna at position ①… If you
need to use the external antenna at position ②, please do DIY welding by yourself"). Until that
0 Ω resistor is un-soldered from the leg toward the zig-zag and re-soldered on the other leg (②),
**the stick is connected to nothing** — harmless, but it does nothing.

That resistor is smaller than a grain of rice and sits against the radio shield: hard rework with a
real chance of ruining the board. The built-in antenna works unmodified, and the robot shares a room
with the router. **My recommendation stands: fit the cable if you like, but leave the resistor alone
unless the video link proves weak.** If the resistor *is* ever moved, never power the board without
the stick attached.

**My decision (2026-09-19): leave the resistor alone unless absolutely necessary — and leave the
antenna kit in the bag**, since the cable does nothing without the resistor change and the socket
survives only a few dozen matings.

"Necessary" = the stream stutters or drops with the robot near the router. Try these first, in
order: (1) rule out **power** — a sagging 5 V supply makes the camera reboot, which looks just like a
WiFi dropout; (2) keep metal, the battery holder and wire bundles away from the antenna end;
(3) lower the stream's resolution / frame rate; (4) confirm the router's 2.4 GHz band is on and not
congested; (5) have the firmware print the WiFi signal strength, so the decision rests on a number.

The built-in antenna is at the **`ESP32-CAM` text / flash-LED end** of the board.

---

## 7. Mounting — as installed (2026-09-19)

**Installed:** the stacked unit is foam-taped **flat** on the chassis plate at the **caster end**,
with the **USB-C socket facing outward** over the plate edge (easy cable access for loading firmware
and debugging). The SD-slot end of the board sits right against the **battery holder's end wall**.
This makes the **caster end the robot's front**. The stick antenna is attached and anchored to the
chassis (inert — the selector resistor has not been moved, by decision).

**⚠ Check once — caster screws.** The base board sits over the caster's four mounting screws. Those
screws are joined electrically (brass standoffs into the steel caster plate), and the base board's
underside has exposed solder points along both long edges (the foam tape covers only the middle).
With nothing powered, continuity-test a screw head against the USB-C shell and against the camera's
`5V` pin: **both must stay silent.** If either beeps, insulate the board edge from the screws.
**✔ Checked 2026-09-19: both silent — no contact.** (A snapshot: the robot vibrates when driving, so
a strip of electrical tape under any board edge that sits very close to a screw head is cheap
insurance. Re-check if the stack is ever pressed down or re-seated.)

**Forward view, without re-taping.** Lying flat, the lens looks at the ceiling (fine for bench
debugging). To look forward: stand the small camera module **upright against the battery holder's
end wall**, which is directly behind it — the lens then faces the USB-C end (the front). Gentle
curve in the ribbon, never a crease; a dab of double-sided tape holds it. An upside-down picture is
a firmware setting. *(My suggestion, not a datasheet fact.)*

**Known compromises of this position:** the built-in antenna (USB-C end) sits just above the metal
caster hardware — a suspect if the video link is ever weak; the lower part of a forward view will
include the board's own front edge and the USB plug; foam tape is one-shot, so this position is
effectively permanent.

- The lens film (red tab) must come off before first use.
- When re-stacking the two boards: USB-C under the **`ESP32-CAM` text / flash-LED end**. Rotated 180°
  it would put USB 5 V on the wrong pins.

## 8. Good to know for later

- **Loading firmware:** through the base board's USB-C. Holding `IO0` while pressing `RST` puts the
  ESP32 in download mode. **Verified for mine (2026-10-06): it does not enter download mode by
  itself** (esptool: "Wrong boot mode detected (0x12)"), so use the buttons every time, and press
  `RST` again after the write. The USB cable must be a **data** cable. The base board's USB serial
  is a FIREPHX `0843:5740` (cdc_acm), not a CH340.
- **⚠ This board boots only with a DOUT-mode bootloader at 0x1000** (since 2026-10-06,
  `course-project/evidence/M1/M1.T6/dout-write.txt`). With the DIO or QIO bootloader that a normal
  upload writes, it reboots in a loop (`serial-boot-dio-rst.txt`). So **never** use `arduino-cli
  upload`, PlatformIO Upload (the Module 8 guide's Step 9.3; its `board = esp32cam` writes the
  bootloader with `--flash-mode dio`), a build's `flash_args` or `merged.bin`. Flash only the app, at
  0x10000: `course-project/firmware/esp32cam/flash_app.sh SKETCH` on the Spark (it also checks the
  partition table). Recovery from a boot loop: write the bootloader again with
  `--flash-mode dout` in download mode, as in `dout-write.txt`. *(Added 2026-10-25, Claude Opus 5.5
  via Claude Code.)*
- **Camera firmware:** `bm_cam-0.2` since 2026-10-25 (`course-project/firmware/esp32cam/bm_cam_v02/`,
  one image for the Module 8 vision lab and the project; boots at VGA, `/control` switches size),
  IP 192.168.5.49 on the house Wi-Fi. `bm_cam-0.1` (UXGA) ran from 2026-10-06 and stays built as the
  fallback. The driver sometimes leaves several frames in one buffer; 0.2 serves only the first
  (`merged_buffers` in `/status`).
- **OV3660 quirk:** with firmware written only for the OV2640 the picture can come up vertically
  flipped and over-saturated. Espressif's own example corrects this specifically for the OV3660.
- **WiFi:** 2.4 GHz only.
