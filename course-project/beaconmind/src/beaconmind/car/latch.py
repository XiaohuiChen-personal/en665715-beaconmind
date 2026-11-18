"""The STOP latch: a file that forbids every move while it exists (plan/README.md contract C5 item 5).

The file is course-project/data/LATCH (git-ignored, on the machine that drives the car). The out-of-band STOP
program writes it, the executor writes it after a lost link or a restart of the car (C5 item 2), and the executor
refuses to start, and ends a running move, while it exists. Only an operator removes it, by name, with
`car_move.py clear-latch --operator <name>` (clear() below). The latch is fail-safe: a file that cannot be read
or parsed still counts as set, and a failed write is reported, never swallowed.

Every set and clear is appended to data/LATCH.log, so a session's evidence shows who stopped and who cleared.

The plan expected this class in a `beaconmind.validator` module of task M2.T1, which the 2026-11-09 re-scope
never built; this is the one latch of the project, with the interface that task named (Latch(path), is_set(),
set(reason, by), read(), clear(operator)).

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this latch.
"""
import json
import os
import time


def default_latch_path():
    import beaconmind
    return os.path.join(str(beaconmind.course_root()), "data", "LATCH")


def _utc(t=None):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() if t is None else t))


class Latch:
    def __init__(self, path=None):
        self.path = os.fspath(path) if path is not None else default_latch_path()

    def is_set(self):
        """True unless the file is known to be absent. Any other answer of the file system (no permission, a stale
        mount, an I/O error) counts as set: when the latch cannot be read, nothing moves."""
        try:
            os.lstat(self.path)
            return True
        except FileNotFoundError:
            return False
        except OSError:
            return True

    def read(self):
        """The latch record, or None when the latch is clear. An unreadable file gives a record saying so."""
        if not self.is_set():
            return None
        try:
            with open(self.path, encoding="utf-8") as handle:
                record = json.load(handle)
            if not isinstance(record, dict):
                raise ValueError("not a JSON object")
            return record
        except (OSError, ValueError) as exc:
            return {"reason": "latch file unreadable (%s: %s)" % (type(exc).__name__, exc), "by": "unknown",
                    "time_utc": None}

    def _log(self, entry):
        try:
            with open(self.path + ".log", "a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry) + "\n")
        except OSError:
            pass    # the log is a convenience; the latch file itself is what stops the car

    def set(self, reason, by):
        """Set the latch. If it is already set the first record is kept (it names the first cause)."""
        record = {"reason": str(reason), "by": str(by), "time_utc": _utc(), "t_unix": round(time.time(), 3)}
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        self._log(dict(record, event="set", already_set=self.is_set()))
        if self.is_set():
            return self.read()
        tmp = "%s.tmp.%d" % (self.path, os.getpid())
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(record, handle)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, self.path)
        return record

    def clear(self, operator):
        """Remove the latch. `operator` is the name of the person who checked the car; an empty name is refused.
        Returns the record that was cleared, or None if the latch was not set."""
        name = str(operator or "").strip()
        if not name:
            raise ValueError("clearing the latch needs the operator's name")
        record = self.read()
        if record is None:
            return None
        os.remove(self.path)
        self._log({"event": "clear", "operator": name, "time_utc": _utc(), "t_unix": round(time.time(), 3),
                   "cleared": record})
        return record
