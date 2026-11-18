"""Perception for the real car: AprilTag detection and tag geometry from one camera frame (plan task M1.T8).

``beaconmind.perception.tags`` needs OpenCV (``cv2`` with the ``aruco`` module) and numpy; ``beaconmind.perception.synth``
renders synthetic frames through the calibrated camera model for tests and simulation. Importing this package alone
imports neither, so the rest of ``beaconmind`` keeps working on a machine without OpenCV.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this package.
"""
