"""BeaconMind car description package. The URDF/xacro and launch files live in share/beaconmind_description.

AI-assisted: Claude Opus 5.5 (xhigh effort) via Claude Code, 2026-10-10: wrote the URDF/xacro, launch file and tests,
and gen_props.py.

gen_props.py (M2.T4 step 4) writes urdf/car_props.xacro from configs/car.json (M1.T9), plus configs/camera.json
(M1.T7) once it exists. It reads car.json through load_car_standin(), a stand-in for the M2.T3 view
beaconmind.config.load_car, which is not written yet. Geometry that car.json does not carry is hand-written in
urdf/car_geometry_extras.xacro.
"""
