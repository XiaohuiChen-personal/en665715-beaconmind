#!/usr/bin/env python3
"""The demo video in one command: `python3 course-project/tools/demo_video.py all` (Mac or Spark host).

A thin launcher for beaconmind.demo.video_cli (see its docstring for the subcommands): it puts the package on the
path so no install is needed. Needs Pillow and an ffmpeg (PATH, $BM_FFMPEG, ~/.local/bin/ffmpeg or the
imageio-ffmpeg wheel); outputs go to course-project/data/video/ (git-ignored).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote this launcher.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "beaconmind", "src"))

from beaconmind.demo.video_cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
