"""Load BeaconMind design values from configs/dv.json.

load_dv returns the numeric value of each key. dv_get raises KeyError naming
any key that is absent. dv_sha12 is the first 12 hex characters of the
SHA-256 of the file's canonical JSON.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote load_dv, dv_get and dv_sha12.
"""

import hashlib
import json
import os
from pathlib import Path

import beaconmind

_CACHE = {}


def _resolve(path):
    if path is None:
        return beaconmind.course_root() / "configs" / "dv.json"
    return Path(os.fspath(path)).expanduser().resolve()


def load_dv(path: "str | os.PathLike | None" = None) -> dict:
    """Return {key: value} from configs/dv.json (default: course_root()/configs/dv.json).

    Raises KeyError naming the key if a caller later asks for a missing one (use dv_get).
    The parsed file is cached by absolute path. Each call returns a shallow copy so a
    caller can override one value without changing the cache.
    """
    resolved = _resolve(path)
    cache_key = str(resolved)
    if cache_key not in _CACHE:
        with open(resolved, encoding="utf-8") as handle:
            document = json.load(handle)
        values = {}
        for name, entry in document["values"].items():
            values[name] = entry["value"]
        _CACHE[cache_key] = values
    return dict(_CACHE[cache_key])


def dv_get(dv: dict, key: str) -> float:
    if key not in dv:
        raise KeyError(key)
    return float(dv[key])


def dv_sha12(path=None) -> str:
    """First 12 hex chars of SHA-256 of the canonical JSON (sort_keys=True, separators=(',', ':'))."""
    resolved = _resolve(path)
    with open(resolved, encoding="utf-8") as handle:
        document = json.load(handle)
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return digest[:12]
