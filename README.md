# BeaconMind

Xiaohui Chen. BeaconMind is an individual class project for JHU EN.665.715 that asks whether a language-model agent can keep its own pose and AprilTag map on a small wheeled car: code does the geometry, and a validator gates each move. The geometry library, the 2026-10-10 car URDF, and flashed-but-uncalibrated ESP32-CAM firmware are in this repo; the Pico project firmware and the Isaac Sim twin are not built yet.

Wi-Fi secrets are not in this repo. `wifi_config.h` stays on the machine that flashes the boards.

## Tree

| Path | What it is |
| --- | --- |
| [`AGENTS.md`](AGENTS.md) | Rules for anyone, including an agent, working in this repo |
| [`course-project/CONTEXT.md`](course-project/CONTEXT.md) | Handoff. Read it before project work and update it at the end of a session |
| `course-project/beaconmind/` | Python package: geometry, car model, schemas, tests |
| `course-project/configs/` | Car and design-value files |
| `course-project/docker/` | `beaconmind-ros`, the project's ROS 2 Humble container |
| `course-project/firmware/esp32cam/` | Camera firmware, including `bm_cam-0.2` |
| `course-project/firmware/pico/` | Placeholders. The project Pico port is not written |
| `course-project/ros2_ws/` | URDF and bringup packages |
| `course-project/plan/` | Task plan |
| `course-project/report/` | IEEE-format report draft |
| `reference/hardware/` | Public, scrubbed copies of the pin and build notes |

The private course repository still holds assignments, module notes, the unredacted hardware notes, and the classmate's chassis CAD. This repository is the project.

## Disclosure

Grok 4.7 via Cursor (2026-10-29) drafted this README, `AGENTS.md`, and the public-repo migration notes in `docs/MIGRATION-PLAN.md`. Xiaohui Chen is accountable for what he submits.
