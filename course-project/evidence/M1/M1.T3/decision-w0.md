# W0 decision — Humble `beaconmind-ros`

BeaconMind keeps a dedicated ROS 2 Humble container. Both proven live links are Humble: Isaac's bundled Fast DDS 2.6.10 reaches a Humble 2.6.x peer over UDP, and the Pico's `micro-ros-agent:humble` was seen from Humble. Host Jazzy received neither. This run stayed on Humble.

Evidence: `apt-policy.txt` (image `arm64 linux`; `ros-humble-apriltag-ros` candidate 3.4.0), `container-versions.txt` (Python 3.10.12, Fast DDS 2.6.12, openai 3.26.0, anthropic 1.11.0), `isaac-odom-in-container.txt` (`/chassis/odom` about 16.3 Hz), `one-graph.txt` (`/apriltag` and the Isaac odometry node in one graph), `apriltag-tf-frame.txt` (`tag36h11:3`).

The container does not `pip install -e`. It puts `beaconmind/src` on `PYTHONPATH` and runs as uid 1000, so a root-owned `egg-info` is not written into the bind mount. `pytest`, `jsonschema`, `openai`, and `anthropic` are installed in the image. `providers` is pinned to those container versions. `evo` was only a dry-run (it would install 1.37.1); it stays on the Spark host venv.

`/dev/shm` names containing `fastrtps_port` still numbered 72, all dated Oct 3–4. None were created during the Isaac launch (`shm_port_files_newer_than_stamp 0`). The Pico node is still M1.T13.

Generative-AI disclosure: Grok 4.7 via Cursor, 2026-10-06, wrote this note.
