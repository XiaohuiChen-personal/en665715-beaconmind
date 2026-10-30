#!/usr/bin/env python3
"""Hold a headless Isaac kit open and print ALIVE every 10 seconds.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: recorded the Qwen3.8 pin, deferred Bonsai, and started M1.T5.
Derived from: discussions/module2/sim/render_carter.py (headless SimulationApp pattern; reimplemented).
"""

import argparse
import time

parser = argparse.ArgumentParser(description="Measure how long a headless kit stays up.")
parser.add_argument("--seconds", type=float, default=900.0)
parser.add_argument("--ros-bridge", action="store_true")
args, _unknown = parser.parse_known_args()

T0 = time.time()

from isaacsim import SimulationApp

simulation_app = SimulationApp(
    {
        "headless": True,
        "hide_ui": True,
        "width": 640,
        "height": 480,
        "renderer": "RaytracedLighting",
        "anti_aliasing": 3,
        "active_gpu": 0,
        "physics_gpu": 0,
        "multi_gpu": False,
        "sync_loads": True,
        "disable_viewport_updates": False,
    }
)

if args.ros_bridge:
    from isaacsim.core.utils.extensions import enable_extension

    enable_extension("isaacsim.ros2.bridge")

print("READY {0:.1f}".format(time.time() - T0), flush=True)
next_alive = time.time() + 10.0
deadline = time.time() + args.seconds
while time.time() < deadline:
    simulation_app.update()
    now = time.time()
    if now >= next_alive:
        print("ALIVE {0:.1f}".format(now - T0), flush=True)
        next_alive += 10.0
print("DONE", flush=True)
simulation_app.close()
