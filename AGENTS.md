# AGENTS.md — BeaconMind

**This file is the single source of truth for every AI agent working in this repository**
(Claude Code, Cursor, Codex, or anything else). `CLAUDE.md` and `.cursor/rules/` are thin
pointers to this file — do not duplicate guidance into them, because copies drift.

Read this file **in full** before changing the project. Re-read it if it changes mid-task.

Student: **Xiaohui Chen**. This repository is **public**.

---

## 1. What this repository is

BeaconMind is Xiaohui Chen's **individual** class project for JHU EN.665.715
(*Embodied Agentic AI for Robotic Control*). This public GitHub repository is the
project tree an instructor opens for review.

The course's final project deadline is **2026-12-13**. That date is a course fact.
It is not the due date of the class-project code-repository link.

BeaconMind asks whether a language-model agent can keep its own pose and AprilTag
map on a small differential-drive car. Code does the geometry. A validator gates
each move. Do not describe work as finished when `course-project/CONTEXT.md` says
it is not.

**Read `course-project/CONTEXT.md` before project work, and update it at the end of
every project session.** It is the handoff. A later session does not remember this
one. When an older entry disagrees with a later dated entry, the later entry wins.
As of the **2026-10-29** handoff, which later work must not silently overwrite:

- The Pico image the docs name is Assignment 8 **Build K2**. The chip was **not**
  re-read that day. Confirm the chip before any port or flash. The project firmware
  under `course-project/firmware/pico/` is still only placeholders.
- Camera firmware **`bm_cam-0.2`** is flashed and **not** calibrated. There is no
  `configs/camera.json`. **M1.T7 is not done.**
- The URDF describes the **M1.T16** car since the late 2026-10-29 M2.T4 update:
 total mass 0.660 kg, centre of mass 0.0105 m ahead of the axle (middle value,
 ±0.0018 m), power-bank box as geometry only (readings in
 `course-project/evidence/M1/M1.T16/`, run and review in
 `course-project/evidence/M2/M2.T4/2026-10-29-m1t16/`). It was 0.506 kg before.
 M2.T4 stays blocked on `camera.json` (M1.T7) and the `load_car` view (M2.T3).
 Do not change the sweep radius, the front overhang or the rear overhang until
 the cable stick-out in the M1.T16 folder is settled.

The Isaac Sim twin and the Pico project firmware are not built.

## 2. Where the private course repo fits

Assignments, module discussions, and knowledge-point notes stay in the private
course repository. This repository is the project. Do not vendor `assignments/`,
`discussions/`, or `knowledge-points/` into this tree. Do not copy the JHU
presentation template, the instructor QuadChart template, or a classmate's chassis
CAD into this tree. Derived car sizes already live in `course-project/configs/car.json`.

`l2_geometry.py` is an assignment solution. It is not published here. Geometry
tests that need it skip. Do not add that file back.

## 3. Layout

```
en665715-beaconmind/
├── AGENTS.md
├── CLAUDE.md
├── README.md
├── .gitignore
├── .cursor/rules/00-agents-md.mdc
├── docs/MIGRATION-PLAN.md
├── reference/hardware/          # scrubbed public copies of the pin and build notes
└── course-project/              # working project tree; paths stay course-project/...
    ├── CONTEXT.md               # read first, update at the end of a session
    ├── beaconmind/              # Python package: geometry, car model, schemas, tests
    ├── configs/                 # car.json and other design-value files
    ├── docker/                  # beaconmind-ros (ROS 2 Humble)
    ├── evidence/
    ├── firmware/esp32cam/       # project camera firmware, including bm_cam-0.2
    ├── firmware/pico/           # placeholders only; the port is not written
    ├── plan/
    ├── report/                  # IEEEtran report; cited PDFs in sources/ are gitignored
    ├── research/
    ├── ros2_ws/src/             # beaconmind_description, beaconmind_bringup
    ├── sim/isaac/
    └── tools/
```

## 4. Hardware

Never invent a pin number, a voltage, a logic level, a current, or a wiring
connection. Verify each one against `reference/hardware/` or the part's datasheet,
and cite it. If you cannot verify it, say so.

**USB and `VSYS` must not be live together.** There is no Schottky in the kit.
Remove the green AMS1117 `OUT` → Pico pin 39 jumper before a micro-USB cable is
connected to the host. The battery switch being off does not prevent the back-feed.

The notes in `reference/hardware/` are public copies dated 2026-10-29. The private
course repo holds the unredacted originals. Do not put a room-by-room home-mesh
map back into this repo.

## 5. Secrets

Never commit, and never print into evidence, logs, or commit messages:

- `wifi_config.h`
- a Wi-Fi SSID or password
- a full BSSID or a home-mesh MAC
- an API key
- a Tailscale address or a tailnet DNS name
- a home-mesh map that names rooms

The camera and Pico `wifi_config.h` files stay only on the machine that flashes.
They are gitignored (`**/wifi_config.h`). The tracked `wifi_config.h.example`
files keep placeholders.

Home LAN `192.168.*` addresses may stay when they are operational notes (the
camera IP, the agent IP). Last-three-byte node labels already used by the
firmware design may stay. Do not expand them to full MACs.

## 6. Runtime

Project containers, Isaac Sim, vLLM, and Pico or ESP32-CAM flashing run on the
DGX Spark host named `spark-2a60`. Do not write a Tailscale IP or a tailnet DNS
name into this file or into a new public note.

Copy files to that host with `tar` over `ssh`, not `rsync`.

The project container is **`beaconmind-ros`** (ROS 2 Humble, Ubuntu 22.04),
defined in `course-project/docker/`. Compose project name `beaconmind`, container
name `beaconmind-ros`. Host ROS on the Spark is for Spark-native work this
project actually runs there, not a second copy of the assignment stack.

The assignment container `rosa-ros2` is a course container **outside this repo**.
It is not this repo's runtime. Do not `docker compose down` it from here.

## 7. Pico firmware (not written yet)

When the BeaconMind Pico port is written, base it on Assignment 8 **Build K2**
behaviour: the Wi-Fi supervisor, the session supervisor, roam, safety, the
deadman, and the stall cutoff. Build with `WIFI_SESSION_TOLERANCE=1` and
`WIFI_ROAM_MODE=1`. Do not start from instructor firmware that connects to Wi-Fi
once and cannot rejoin.

The K2 sources stay in the private course repo. This public repo must not vendor
`assignments/assignment7` or `assignments/assignment8`.

Never commit `wifi_config.h`. The ESP32-CAM firmware already in
`course-project/firmware/esp32cam` is project code and stays. Flash the app at
`0x10000` only; this board boots with the DOUT-mode bootloader at `0x1000`.

## 8. Disclosure

Submitted course work needs a short generative-AI disclosure naming the model
and what it helped with. Xiaohui Chen is accountable for what he submits.

## 9. Third-party code

Do not paste upstream or tutorial implementations. Where an approach is derived
from an upstream source, name that source in a comment.

Instructor lab code may be reused with a comment naming the instructor file.
Every part that an agent changed keeps the disclosure in §8.

## 10. Working conventions

- Prefer a checked fact over a plausible guess. Do not invent citations, API
  signatures, pin numbers, voltages, or benchmark numbers.
- If a claim in an older note conflicts with the 2026-10-29 entry in
  `course-project/CONTEXT.md`, that entry wins until a later dated entry
  replaces it.
- Keep this file current when a project convention changes. `CLAUDE.md` and
  `.cursor/rules/` stay pointers.
