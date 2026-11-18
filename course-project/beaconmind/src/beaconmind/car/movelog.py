"""One JSONL file per move: every command sent, every telemetry sample received, the result (rule R2).

The files go into the recorder's active session (course-project/data/real/<session>/moves/; the session's name is
in data/real/.active, written by tools/record_session.sh) so that a move's log lies beside the rosbag, the frames
and the video of the same run. With no active session they go to data/moves/ (simulated cars, tests).

Line 1 is a header: the command, the configuration, the host's wall clock and monotonic clock at the same instant
(the samples carry monotonic times). Then the executor's records in order ("start", "cmd", "tel", "stop",
"result"), as executor.py writes them.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this move logger.
"""
import dataclasses
import json
import os
import time

SCHEMA = "bm.movelog/1"


def data_root():
    import beaconmind
    return os.path.join(str(beaconmind.course_root()), "data")


def active_session_dir(root=None):
    """The recorder's active session folder, or None when no session is recording."""
    root = root or data_root()
    marker = os.path.join(root, "real", ".active")
    try:
        with open(marker, encoding="utf-8") as handle:
            name = handle.read().strip()
    except OSError:
        return None
    if not name or "/" in name or name.startswith("."):
        return None
    path = os.path.join(root, "real", name)
    return path if os.path.isdir(path) else None


def moves_dir(root=None):
    """(directory for move logs, the active session's name or None)."""
    root = root or data_root()
    session = active_session_dir(root)
    if session is not None:
        return os.path.join(session, "moves"), os.path.basename(session)
    return os.path.join(root, "moves"), None


class MoveLog:
    """Open with begin(cmd, ...), pass write to the executor as its log, end with finish()."""

    def __init__(self, directory=None, root=None):
        if directory is None:
            directory, self.session = moves_dir(root)
        else:
            self.session = None
        self.directory = directory
        self.path = None
        self._fh = None
        self.error = None

    def begin(self, cmd, cfg=None, extra=None):
        try:
            os.makedirs(self.directory, exist_ok=True)
            stamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
            name = "move_%s_%s_%s.jsonl" % (stamp, cmd.get("cmd_seq", "x"), cmd.get("action", "x"))
            self.path = os.path.join(self.directory, name)
            n = 1
            while os.path.exists(self.path):
                n += 1
                self.path = os.path.join(self.directory, name[:-6] + "_%d.jsonl" % n)
            self._fh = open(self.path, "a", encoding="utf-8")
            header = {"ev": "header", "schema": SCHEMA, "cmd": cmd, "session": self.session,
                      "t_unix": time.time(), "t_monotonic": time.monotonic(),
                      "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            if cfg is not None:
                header["config"] = {k: v for k, v in dataclasses.asdict(cfg).items()}
            if extra:
                header.update(extra)
            self.write(header)
        except OSError as exc:      # a log that cannot be written must not move or stop the car by itself
            self.error = "%s: %s" % (type(exc).__name__, exc)
            self._fh = None
        return self.path

    def write(self, record):
        if self._fh is None:
            return
        try:
            self._fh.write(json.dumps(record, default=str) + "\n")
        except (OSError, ValueError) as exc:
            self.error = "%s: %s" % (type(exc).__name__, exc)

    def finish(self):
        if self._fh is not None:
            try:
                self._fh.flush()
                os.fsync(self._fh.fileno())
                self._fh.close()
            except OSError as exc:
                self.error = "%s: %s" % (type(exc).__name__, exc)
            self._fh = None
        return self.path
