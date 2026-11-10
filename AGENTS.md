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

**Xiaohui presents on Tuesday 2026-12-01 (Group 1), and all four project deliverables are
due then, 10 points each:** the slides, a demo **recording** (a video, not a live demo),
the report, and this repository's link (EN.665.715 lecture of 2026-10-27; confirmed by
Xiaohui on 2026-11-09). The target is to finish by **2026-11-25**. The plan was re-scoped
for this on 2026-11-09: `course-project/plan/README.md` §3.6 is the authority for what
remains, and it overrides older scope text in the plan.

Two standing rules (Xiaohui, 2026-11-09; plan §3.6):

- **R1 — always sim-to-real.** The real car is in scope. Every real-car session is first
  rehearsed in simulation (the kinematic simulator, with the same arena layout, start,
  agent, prompt and tools) and compared with that rehearsal.
- **R2 — record every real run.** One evidence folder per session holds the phone video,
  a rosbag of the car's topics, the camera frames, the agent's traces and tool calls, a
  terminal capture, the tape readings and a README. Never drive the car without the
  recorder (`M3.T27`).

The LLM arms are Claude Opus 5.5, Qwen3.8-Flash-Next (vLLM) and Gemma 4 26B-A4B (Ollama),
set in `course-project/configs/providers.json` (Xiaohui, 2026-11-09).

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
 The footprint now includes the cables, by Xiaohui's decision of 2026-10-29
 (keep them as they are): front overhang 0.178 m (camera cable tip), rear
 overhang 0.148 m (Pico cable), sweep radius about 0.178 m. If the cables are
 rerouted later, re-measure both points and rebuild `car.json` and the URDF.

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

Since 2026-11-10 the Spark has a **git clone of this repository at
`~/Projects/en665715-beaconmind`**, and that clone is the project's working tree there
(git-ignored `course-project/data/` lives in it; the older tar copy under the private
course repo's clone is stale). Move code by commit, push and `git pull --ff-only` on the
Spark; for uncommitted work, `course-project/tools/sync_to_spark.sh` copies the working
copy over with `tar` through `ssh`. Never use `rsync` to the Spark (its Tailscale SSH check
corrupts rsync's stream). `course-project/tools/pull_evidence.sh` copies a task's evidence
back. The host venv `~/.venvs/beaconmind` (Python 3.12, gtsam 4.3.0) imports `beaconmind`
from that clone.

Model servers on the Spark: `course-project/tools/serve_qwen38.sh start|wait|stop` runs
Qwen3.8-Flash-Next on vLLM at `127.0.0.1:8000` (container `bm-qwen38`, about 97 GB of the
121 GB); Gemma 4 runs in the host's Ollama at `127.0.0.1:11434` (about 52 GB). The two do
not fit at the same time: stop one before loading the other. Replay runs go through
`course-project/tools/replay_run.sh` (a one-off `beaconmind-ros` container).

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
