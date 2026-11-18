#!/usr/bin/env python3
"""A large clock for the phone video of a recorded session (rule R2; plan task M3.T27). Standard library only.

    python3 course-project/tools/session_clock.py [session id]

Film the terminal for two or three seconds at the start of every phone video (and again at the end if you can): the
video's own timeline is then tied to the host clock that stamps the bag, the frames and the logs. Run it on the Spark,
or on the Mac when both clocks are NTP-synchronised (the README of each session says whether the Spark's was). Ctrl-C
ends it.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-18: wrote this clock.
"""
import sys
import time

FONT = {  # 5 x 7 block digits
    "0": ["#####", "#   #", "#  ##", "# # #", "##  #", "#   #", "#####"],
    "1": ["  #  ", " ##  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "],
    "2": ["#####", "    #", "    #", "#####", "#    ", "#    ", "#####"],
    "3": ["#####", "    #", "    #", " ####", "    #", "    #", "#####"],
    "4": ["#   #", "#   #", "#   #", "#####", "    #", "    #", "    #"],
    "5": ["#####", "#    ", "#    ", "#####", "    #", "    #", "#####"],
    "6": ["#####", "#    ", "#    ", "#####", "#   #", "#   #", "#####"],
    "7": ["#####", "    #", "   # ", "  #  ", "  #  ", "  #  ", "  #  "],
    "8": ["#####", "#   #", "#   #", "#####", "#   #", "#   #", "#####"],
    "9": ["#####", "#   #", "#   #", "#####", "    #", "    #", "#####"],
    ":": ["     ", "  #  ", "  #  ", "     ", "  #  ", "  #  ", "     "],
    ".": ["     ", "     ", "     ", "     ", "     ", " ##  ", " ##  "],
}


def render(text):
    """Seven lines of block characters for a string of digits, ':' and '.'."""
    return ["  ".join(FONT[c][row].replace("#", "█") for c in text) for row in range(7)]


def frame(now, session):
    lt = time.localtime(now)
    stamp = time.strftime("%H:%M:%S", lt) + ".%d" % int((now % 1) * 10)
    head = "BeaconMind session %s" % session if session else "BeaconMind recording clock"
    lines = [head, time.strftime("%Y-%m-%d %Z (UTC%z)", lt) + "   epoch %.1f" % now, ""] + render(stamp)
    return "\n".join(lines)


def main(argv):
    session = argv[0] if argv else ""
    sys.stdout.write("\x1b[?25l")  # hide the cursor
    try:
        while True:
            now = time.time()
            sys.stdout.write("\x1b[H\x1b[2J" + frame(now, session) + "\n")
            sys.stdout.flush()
            time.sleep(0.1 - (time.time() % 0.1))
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\x1b[?25h\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
