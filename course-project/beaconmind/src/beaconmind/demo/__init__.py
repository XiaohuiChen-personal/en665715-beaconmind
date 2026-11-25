"""The demo video (plan M6.T11-T16, re-scoped in plan/README.md section 3.6 work list 4.3-4.4).

The video is rendered from the experiment harness's logs (cut 4 of section 3.6: no ROSA runtime): the simulated
closed-loop episode of 2026-11-18 and, once they exist, the real car's episodes. Every number on screen is read from a
log or an evidence file by code.

    timeline.py   time-lapse pieces, frame times, fitting, the phone-clock sync, the sequence plan (standard library)
    episode.py    one closed-loop run folder as a timeline of steps (standard library)
    numbers.py    every number the video shows, with its source (standard library)
    draw.py, topdown.py, panels.py, cards.py   the Pillow renderers
    ffmpeg.py     the ffmpeg command lines and pipes (ffmpeg from PATH, $BM_FFMPEG or the imageio-ffmpeg wheel)
    sim_part.py, car_part.py, narration.py, video_cli.py   the parts, the narration script and the one command

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote the demo-video package.
"""
