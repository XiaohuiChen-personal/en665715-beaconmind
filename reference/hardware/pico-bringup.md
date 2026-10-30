> Public copy for BeaconMind, 2026-10-29; the private course repo holds the unredacted original.

# Pico 2 W — flashed image and how to connect it again

Read this before any session that plugs in the Pico, reflashes it, or drives the
physical car from an assignment or the course project. Wiring facts stay in
[`car-build-notes.md`](car-build-notes.md) and [`wiring-plan.md`](wiring-plan.md).
Do not print or commit `wifi_config.h`.

## What is on the board now (2026-10-11) — the Module 6 sim-to-real drive firmware

Replaced the tilt image on 2026-10-11 for the Module 6 discussion. Node `/pico2w_drive`; it subscribes
`/pico/cmd_vel` (`geometry_msgs/Twist`, best effort) and publishes `/pico/imu/heading`, `/pico/imu/pitch` and
`/pico/drive/status` (0 stopped, 1 driving, 2 stopped by the 0.5 s command timeout). Same Wi-Fi agent address and
UDP 8888, but its micro-ROS Agent now runs as the `micro-ros-agent` container inside the Module 6 Gazebo compose
project, not as `pico-micro-ros-agent`. Source: `assignments/assignment6/module-6-gazebo-sim/sim-to-real/pico2w_led/`
(compile: `discussions/module6/tools/build-firmware.sh`; flash: `UF2=<path> …/assignment5/module-5-imu-tilt-control/spark-flash.sh`).
`drive_control.c` differs from the instructor's in two ways: the wheel remap `tb6612_set(-right_duty, -left_duty)`,
because on this car channel A drives the **right** wheel and the instructor's "forward" went drive-wheels-first, and the
calibrated constants. Flashed UF2s are kept on the Spark in `discussions/module6/firmware/`: `-remap-uncalibrated`,
`-calibrated1`, `-calibrated2` (current). The BNO055 heading does not reset on a Pico-only reboot if the IMU stays
powered.

## Before that (2026-10-01) — the Module 5 tilt firmware

The Module 4 LED image described in the next section was **replaced on 2026-10-01** by the
instructor's Module 5 firmware (same project name, `pico2w_led`, same node name `/pico2w_led`).

| Fact | Value |
| --- | --- |
| Source | `assignments/assignment5/module-5-imu-tilt-control/pico2w_led/` — the instructor's files, unmodified (identical to repo `drelishiahjmiller/en665715-embodied-ai` at `8a62bad`, folder `module-5-imu-tilt-control/`) |
| Build | `assignments/assignment5/module-5-imu-tilt-control/spark-build.sh` on the Spark: `libmicroros.a` rebuilt with `RMW_UXRCE_MAX_PUBLISHERS=3`, then the firmware, both in the existing `pico-microros-builder` image |
| UF2 | On the Spark: `.../module-5-imu-tilt-control/pico2w_led/build/pico2w_led.uf2`, 808448 bytes, sha256 `9e1725d4933ee58e54884dfddd894be58326456c039a9a0b22a05de86bf59314` (gitignored, root-owned) |
| Flash | `assignments/assignment5/module-5-imu-tilt-control/spark-flash.sh` — the 1200-baud touch, a check that the drive is `usb RPI RP2350`, then the privileged-container copy described under "Reflash" below. Takes about 10 s and needs no hands on the board. It finds the serial port by USB identity (`/dev/serial/by-id/usb-Raspberry_Pi_Pico_*`), because the board comes back as `/dev/ttyACM1` when a program still holds `ttyACM0` |
| What the image does | Wi-Fi + micro-ROS as before, plus: BNO055 on I2C0 (`GP0` SDA, `GP1` SCL) publishing `/pico/imu/pitch` (`std_msgs/Float32`, 10 Hz); TB6612FNG on `GP2` PWMA, `GP4` AIN1, `GP3` AIN2, `GP5` STBY, `GP12` PWMB, `GP10` BIN1, `GP11` BIN2; arm requests on `/pico/tilt/request` (`Int32`, `1` / `-1`), state on `/pico/tilt/status` (`Int32`, 1–8). The LED topics still work |
| Motor behaviour | Idle until armed. Once armed, a pitch change of 2° held for 100 ms runs **both wheels at 100 % PWM for 10 s**, then stops. An armed request never times out: it waits for a tilt until the board is reset |
| First boot evidence | 2026-10-01: `Connected. IP address: 192.168.4.95`, `Neutral pitch`, `micro-ROS Agent connected.`, `micro-ROS node ready.`, `BNO055 pitch:` lines; one `/pico2w_led` node in `rosa-ros2`. **This closes the open I2C test** in `car-build-notes.md` (the BNO055 answers at `0x28` with chip ID `0xA0`, so `GP0`/`GP1` reach `SDA`/`SCL`) |
| Diagnostic image | `assignments/assignment5/diagnostics/pintest/` — a small pico-sdk program (no Wi-Fi) that holds test levels on the driver pins, pulses each motor alone and counts encoder edges over USB serial. Flash it with `UF2=<repo>/assignments/assignment5/diagnostics/pintest/build/pintest.uf2 spark-flash.sh`; re-flash the tilt firmware afterwards (stage `boot` of `assignments/assignment5/build/capture_session.py` does that). It was on the board from about 15:25 to 17:03 on 2026-10-01; **the tilt firmware is the image on the board now** |
| Agent | Run fresh for each session on the host network: `docker run --rm -it --name pico-micro-ros-agent --network host microros/micro-ros-agent:humble udp4 --port 8888 -v6`. The firmware has no reconnect logic, so after the Agent restarts the Pico must be rebooted (re-flash, or unplug and replug) |

The address facts below still hold (agent address `192.168.5.1:8888` compiled in; Pico address by
DHCP, `192.168.4.95` on 2026-10-01).

## What was on the board before (2026-09-23) — the Module 4 LED image

The Pico 2 W **is flashed**. It ran this image on the DGX Spark the same night:
the instructor `pico2w_led` firmware, built for **Pico 2 W / RP2350 / Cortex-M33**
and copied to the board as `pico2w_led.uf2` (794624 bytes).

| Fact | Value |
| --- | --- |
| Source | `assignments/assignment4/module4-pico2w/pico2w_led/` |
| UF2 used | On the Spark: `.../pico2w_led/build/pico2w_led.uf2`. Confirm the file is still there before a reflash. The directory is gitignored. |
| Builder image | `pico-microros-builder` on `spark-2a60`. SDK commit `079c6f39023649b154152db30f1d781e884879bc`, micro-ROS setup commit `99757720fdf33031a41288d8b69c7c0356f2db64`. |
| Running USB id | `2e8a:0009`, "Raspberry Pi Pico", `/dev/ttyACM0` |
| BOOTSEL USB id | `2e8a:000f`, "Raspberry Pi RP2350 Boot", volume label `RP2350` |
| What the image does | Joins the 2.4 GHz LAN, pings the micro-ROS agent, creates node `/pico2w_led`, and serves `/pico/led/set` and `/pico/led/state` (`std_msgs/Bool`). |
| What it does not do | No motors, encoders, IMU, or camera. Those bring-up tests in `car-build-notes.md` are still open. |
| Onboard LED | The CYW43 lamp beside the micro-USB plug. It is not a power light. A photo of it lit stays in the private course repo and is not in this public copy. |
| Report | `assignments/assignment4/Chen_Xiaohui_Module4_microROS_LED.pdf` (built and reviewed; not a statement that Canvas has it). |

Observed on that run, and **not stable across DHCP renewals**:

- Pico address `192.168.4.81`
- Agent address compiled into the firmware: Spark Ethernet `192.168.5.1`, UDP **8888**
- The firmware joined the 2.4 GHz network named in `wifi_config.h`. That name is not recorded in this public copy. The password stays only in `wifi_config.h`.

If the Spark's Ethernet address is no longer `192.168.5.1`, this image will not find the agent until `wifi_config.h` is updated and the UF2 is rebuilt and reflashed.

Left at the end of that session: the micro-ROS agent container was **stopped, not removed** (`pico-micro-ros-agent`). **2026-09-27:** `docker ps` on spark-2a60 showed it **"Up 4 days"**, so it was started again after this record. Check before assuming either state; `llama3.2` was unloaded; `rosa-ros2` was left running. The AMS1117 `OUT` → Pico `VSYS` jumper was **unplugged** before USB. Do not assume the USB cable is still in the Spark.

## Connect again (no reflash)

1. **Pull the `VSYS` jumper first.** It is the **green** wire from AMS1117 `OUT` (right board, column `e`, row 12) to Pico pin 39 (row 2 on the power side). The battery switch being off is not enough: USB back-feeds that rail. Other green wires are encoder or motor-driver signals — leave them. Leave AMS1117 `VIN` and `GND`. Leave the orange wire on Pico pin 36 (`3V3` out).
2. Plug the Pico's **micro-USB** cable into the **Spark**, not the Mac. USB is power, flash, and serial. ROS traffic is Wi-Fi.
3. Keep the battery switch off while USB is in. Do not put the `VSYS` jumper back until USB is unplugged.
4. Start the agent on the host network so the Pico's UDP and the Humble graph in `rosa-ros2` are the same network. `ROS_DOMAIN_ID` stays `0`, matching `rosa-ros2`. If the stopped container is still present:

   ```bash
   docker start pico-micro-ros-agent
   ```

   If it is gone:

   ```bash
   docker run -d --name pico-micro-ros-agent --network host \
     -e ROS_DOMAIN_ID=0 \
     microros/micro-ros-agent:humble \
     udp4 --port 8888 -v6
   ```

5. The flashed image starts by itself when the board powers up. Serial is `/dev/ttyACM0` at 115200 (`pyserial` is installed; the account is in `dialout`). A healthy boot prints Wi-Fi connected, `micro-ROS Agent connected.`, and `micro-ROS node ready.`
6. Check the graph **inside `rosa-ros2`**, not on host Jazzy. Host Jazzy was not shown to see this node.

   ```bash
   cd ~/Projects/EN.665.715/assignments/assignment2/ollama
   docker compose exec -T ros2 bash -lc \
     'source /opt/ros/humble/setup.bash && ros2 node list && ros2 topic list'
   ```

   Expect one `/pico2w_led`. Two or three means the agent kept a dead session. Remove the agent container, start a new one, then power-cycle the Pico and wait until the count is exactly one.

Do not `docker compose down` `rosa-ros2`. Do not open `/dev/ttyACM0` at 1200 baud unless the next section is what you mean to do: that reset enters the bootloader and the application stops.

## Reflash

`picotool`, `esptool`, and `arduino-cli` are still not installed. `udisksctl` over SSH fails (no polkit tty), and this user is not in the `disk` group. The method that worked:

1. `VSYS` jumper out, USB in the Spark, agent stopped or freshly created.
2. `python3 -c 'import serial; serial.Serial("/dev/ttyACM0", 1200).close()'`
3. Wait until `lsblk` shows label `RP2350`. The disk name was `/dev/sda1` once. **Check the label. Do not mount any other disk.**
4. Copy the UF2 from a privileged container that can see `/dev`:

   ```bash
   docker run --rm --privileged -v /dev:/dev \
     -v /home/xiaohui_chen/Projects/EN.665.715/assignments/assignment4/module4-pico2w/pico2w_led/build:/uf2:ro \
     pico-microros-builder \
     bash -lc 'mkdir -p /mnt/pico && mount /dev/sda1 /mnt/pico && cp /uf2/pico2w_led.uf2 /mnt/pico/ && sync'
   ```

   Replace `/dev/sda1` with the device whose label is `RP2350`. The board reboots into the application on its own. Rebuild the UF2 in `pico-microros-builder` when the source or `wifi_config.h` changes. Do not use an RP2040 `libmicroros.a`.

## Later assignments that use this car

- The graded ROS 2 / ROSA stack stays `rosa-ros2` (Humble) plus host Ollama. Assignment models stay `llama3.2` and `mistral` unless that assignment's prompt says otherwise.
- A new behavior needs a new firmware image. This UF2 only answers the LED topics.
- Stop the course-project vLLM container before loading a large Ollama model, and the other way around. `docker stop` / `docker start vllm-rosa` keeps the container. Do not delete it, and do not compose-down `rosa-ros2`.
- Evidence rules do not change: real command output, no Wi-Fi password, no `wifi_config.h` in a PDF or a commit.
- Motor or sensor work still has to pass the open tests in `car-build-notes.md`: I2C answer at `0x28`, `STBY` driven high, encoder direction, motor direction. Raise the wheels, and do not turn the battery switch on until the Pico is already up. Power-down is the switch first.

## Course project, when it is assigned

Do not create `course-project/` until the Course Project Description is in hand. Its first file is still `CONTEXT.md`. On that first session, copy the hardware state from this file and from `car-build-notes.md` into `CONTEXT.md`, including whether the `VSYS` jumper is in, whether USB is plugged in, which UF2 is on the Pico, and which containers are running. Update `CONTEXT.md` at the end of every later session.

The capstone LLM is not this assignment's `llama3.2`. The intended serving path is vLLM on the Spark, model Qwen 3.5 35B-A3B (the complete Hugging Face snapshot) unless a later decision replaces it. Qwen 3.6 35B-A3B-FP8 was an empty stub on 2026-09-13; check the cache before treating it as available. Do not point assignment scripts at that server.

The capstone does not inherit `rosa-ros2` unless `CONTEXT.md` says so. It does inherit the car: same Spark USB host, same `VSYS`/USB interlock, same "wheels up until a cutoff exists" rule. Name the individual role on every project artifact. Sixty percent of that grade is preparation and participation, not a solo write-up.
