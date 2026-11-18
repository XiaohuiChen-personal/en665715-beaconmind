"""Host-side control of the real car (plan/README.md section 3.6, work list 2.6, 2.7 and 2.9).

The car keeps the firmware it has (Assignment 8 Build K2, access-point variant): it drives open loop from a stream
of velocity commands on /pico/cmd_vel and stops by itself when the stream ends. This package turns the five bounded
moves of contract C2 into such a stream, closed on the car's own wheel counts and IMU heading, and reports each move
in the bm.move_result/1 format. Nothing here imports ROS at import time:

    config      constants, each with the file it was read from, and the configuration loaded from configs/
    telemetry   the car's /pico/wheel_ticks array (layout 9) as a Telemetry sample
    odometry    wheel counts and IMU heading to motion in the robot frame (contract C1)
    moves       the C2 move table, the bm.move/1 command and its limits
    latch       the STOP latch file (contract C5 item 5)
    executor    the bounded-move state machine
    simcar      a deterministic simulated car with the firmware's behaviour, for tests
    link        the executor coupled to a car: the simulated one here, the real one in ros_io
    ros_io      the rclpy node, the out-of-band STOP program and a simulated-car node (rclpy imported lazily)
    camera      frames from the camera and the C3 detection pipeline
    backend     the real-car environment with the simulator's per-step data
    movelog     one JSONL file per move in the recorder's session

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this package (host-side executor, STOP latch,
simulated car, real-car backend).
"""
