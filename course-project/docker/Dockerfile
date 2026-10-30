# AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the BeaconMind Humble image.
# BeaconMind project graph: ROS 2 Humble (Ubuntu 22.04, Python 3.10). plan/README.md L5, C12.
FROM ros:humble-ros-base
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      ros-humble-apriltag-ros ros-humble-apriltag-msgs ros-humble-image-proc ros-humble-image-transport \
      ros-humble-compressed-image-transport ros-humble-cv-bridge ros-humble-camera-calibration-parsers \
      ros-humble-tf2-ros ros-humble-tf2-tools ros-humble-robot-state-publisher ros-humble-xacro \
      ros-humble-rmw-fastrtps-cpp python3-pip python3-opencv python3-numpy \
      python3-colcon-common-extensions tmux curl iproute2 \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --no-cache-dir --upgrade pip \
    && python3 -m pip install --no-cache-dir "pytest>=7.4" "jsonschema>=4.17" "openai>=2.0" "anthropic>=0.79"
RUN echo "source /opt/ros/humble/setup.bash" >> /etc/bash.bashrc
# Package console scripts (pyproject [project.scripts]) are not installed, because the package is on
# PYTHONPATH (step 5). Give each operator command a one-line wrapper instead (README C5 item 5, L3):
RUN printf '#!/bin/sh\nexec python3 -m beaconmind.validator clear-latch "$@"\n' > /usr/local/bin/bm-clear-latch \
    && chmod 755 /usr/local/bin/bm-clear-latch
WORKDIR /workspace/course-project
