"""The real-run design values, configs/dv-real.json, and the --dv switch of the run tools.

Xiaohui Chen approved on 2026-11-24 "a separate design-values file" for the real runs (CONTEXT.md, that day). It is
the frozen configs/dv.json with exactly four fields changed:

    sigma_range_a_m, sigma_range_b_per_m, sigma_bearing_deg   the agent's detector noise model (geometry._sigma),
                                                               from the tag pilot's configs/detector_noise.json
    reject_range_above_m                                       the range limit Xiaohui sets after the pilot

build_real_dv() makes that document and refuses anything else; tools/real_dv.py writes it. use_dv() is how
tools/closed_loop_run.py, tools/car_batch.py and tools/room_rehearsal.py run with it: the frozen modules (geometry.py,
dv.py, kinsim_lite.py, ...) read their values through beaconmind.dv.load_dv(), which caches the parsed default file;
inside the block the cached values of the default file are the chosen file's, and on exit (also after an exception)
the cache holds exactly what it held before. No frozen file is edited. The same technique as
envs/kinsim_room.dv_override (the room rehearsal's), with a whole file instead of a few values.

What maps the pilot's model onto the agent's: the detector does not correct the pilot's biases, so they count as
error. Range: sigma_range = (|range bias a| + range sigma a) + (|range bias b| + range sigma b) r. Bearing: the agent's
model has one bearing sigma for every range, so it is the pilot's at the range limit (the largest range the agent
uses), |bearing bias| + bearing sigma a + bearing sigma b x limit. Rounded up to 4 decimals; never under 0.005 m
(range a) or 0.1 deg (bearing), so no detection is ever weighted as exact.

What does not follow the sigmas (decided 2026-11-24): well_cond_sigma_xy_m / _theta_deg and reloc_sigma_xy_m /
_theta_deg. They are acceptance thresholds on a fix's computed uncertainty ("a fix this certain may be trusted"), a
requirement on the result, not a model of the camera. The rehearsal (evidence/M3/M3.T12/rehearsal-b2.md) showed what
goes wrong today: with the frozen sigmas almost no two-tag fix passes its own test. Measured sigmas make the
computed uncertainty honest; scaling the thresholds with them would cancel exactly that. The gates
(gate_range_m, gate_bearing_deg, ...) are association windows that also cover pose drift and stay as well.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote this module.
"""
import contextlib
import hashlib
import json
import math
import os
import pathlib
import re

import beaconmind
from beaconmind import dv as dvm

CHANGEABLE = ("sigma_range_a_m", "sigma_range_b_per_m", "sigma_bearing_deg", "reject_range_above_m")
NOISE_FIELDS = CHANGEABLE[:3]


def frozen_path():
    return pathlib.Path(dvm._resolve(None))


def sha12(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()[:12]


def _rel(path):
    path = pathlib.Path(path).resolve()
    try:
        return str(path.relative_to(beaconmind.course_root().resolve()))
    except ValueError:
        return str(path)


def _ceil(value, places=4):
    scale = 10 ** places
    return math.ceil(value * scale - 1e-9) / scale


def noise_to_dv(model, reject_range_m):
    """{sigma_range_a_m, sigma_range_b_per_m, sigma_bearing_deg} from a bm.detector_noise/1 model (module text).
    ValueError when the model is not usable."""
    if not isinstance(model, dict) or model.get("schema") != "bm.detector_noise/1":
        raise ValueError("not a bm.detector_noise/1 document")
    try:
        rb, rs, bs = model["range_bias_m"], model["range_sigma_m"], model["bearing_sigma_deg"]
        nums = [float(rb["a"]), float(rb["b"]), float(rs["a"]), float(rs["b"]), float(model["bearing_bias_deg"]),
                float(bs["a"]), float(bs["b"]), float(reject_range_m)]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("the detector-noise model lacks a number: %s" % exc)
    if not all(math.isfinite(v) for v in nums) or min(nums[2], nums[3], nums[5], nums[6]) < 0 or nums[7] <= 0:
        raise ValueError("the detector-noise model has a sigma that is negative or not a number")
    rba, rbb, rsa, rsb, bb, bsa, bsb, limit = nums
    return {"sigma_range_a_m": max(_ceil(abs(rba) + rsa), 0.005),
            "sigma_range_b_per_m": _ceil(abs(rbb) + rsb),
            "sigma_bearing_deg": max(_ceil(abs(bb) + bsa + bsb * limit), 0.1)}


def build_real_dv(frozen_doc, frozen_sha12, model, noise_rel, noise_sha256, reject_range_m, today,
                  evidence=None, beyond_pilot=False):
    """The configs/dv-real.json document. Refuses (ValueError) a range limit beyond the range the pilot found
    reliable unless beyond_pilot (Xiaohui's explicit decision), and any difference from the frozen file outside the
    four fields."""
    if frozen_doc.get("schema") != "bm.dv/1":
        raise ValueError("the frozen file is not bm.dv/1")
    limit = float(reject_range_m)
    if not 0.5 <= limit <= 5.0:
        raise ValueError("--reject-range %.2f m is not a range limit (0.5 to 5.0 m)" % limit)
    pilot_max = model.get("max_range_m")
    if pilot_max is not None and limit > float(pilot_max) + 1e-9 and not beyond_pilot:
        raise ValueError("--reject-range %.2f m is beyond the %.2f m the tag pilot found reliable; the plan says 2.5 m "
                         "then, or Xiaohui decides otherwise (--beyond-pilot-range)" % (limit, float(pilot_max)))
    new = noise_to_dv(model, limit)
    source = model.get("source") or {}
    pilot = "tag pilot %s (%s, %s frames, %s placements)" % (source.get("log"), source.get("date"),
                                                           source.get("n_frames"), source.get("n_placements"))
    noise_sha12 = noise_sha256[:12]
    where = "%s sha12 %s (sha256 %s)%s" % (noise_rel, noise_sha12, noise_sha256, "; %s" % evidence if evidence else "")
    values = json.loads(json.dumps(frozen_doc["values"]))
    rb, rs, bs = model["range_bias_m"], model["range_sigma_m"], model["bearing_sigma_deg"]
    texts = {
        "sigma_range_a_m": "%s: |range bias a| %.4f + range sigma a %.4f m" % (pilot, abs(rb["a"]), rs["a"]),
        "sigma_range_b_per_m": "%s: |range bias b| %.4f + range sigma b %.4f m/m" % (pilot, abs(rb["b"]), rs["b"]),
        "sigma_bearing_deg": "%s: |bearing bias| %.3f + bearing sigma %.3f + %.4f x %.2f m (the range limit) deg"
                             % (pilot, abs(model["bearing_bias_deg"]), bs["a"], bs["b"], limit),
    }
    for key in NOISE_FIELDS:
        values[key] = dict(values[key], value=new[key], status="measured", source=texts[key] + " (dv_real.py)",
                           evidence=where, updated=today)
    values["reject_range_above_m"] = dict(
        values["reject_range_above_m"], value=limit, status="DV",
        source="Xiaohui Chen's range limit after the tag pilot (plan 3.6: 3.0 m, or 2.5 m if the pilot does not confirm "
               "it); the pilot's reliable range %s m%s" % (pilot_max, "; set beyond it by decision" if beyond_pilot else ""),
        evidence=where, updated=today)
    changed = [k for k in values if values[k] != frozen_doc["values"][k]]
    diffs = ["%s %s -> %s" % (k, frozen_doc["values"][k]["value"], values[k]["value"]) for k in CHANGEABLE
             if values[k]["value"] != frozen_doc["values"][k]["value"]]
    doc = {"$comment": ("Real-run design values (Xiaohui Chen, 2026-11-24: a separate design-values file). Written by "
                        "tools/real_dv.py on %s from configs/dv.json (frozen, sha12 %s) and %s (sha12 %s). Only these "
                        "fields differ from the frozen file: %s; values changed: %s. Every other entry is the frozen "
                        "file's, entry for entry. AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote "
                        "the tool that writes this file; the numbers are the pilot's and Xiaohui's."
                        % (today, frozen_sha12, noise_rel, noise_sha12, ", ".join(changed) or "none",
                           "; ".join(diffs) or "none")),
           "schema": "bm.dv/1", "values": values}
    extra = differs_outside(frozen_doc, doc)
    if extra:
        raise ValueError("would differ from the frozen file outside the four fields: %s" % extra)
    return doc


def sha256(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def noise_source(path):
    """The sha256 of the detector-noise file a dv file's three sigmas were made from (tools/real_dv.py writes it
    into their `evidence`), or None when they do not name one and the same one (the frozen file names none)."""
    try:
        with open(path, encoding="utf-8") as handle:
            values = json.load(handle)["values"]
        found = {re.search(r"sha256 ([0-9a-f]{64})", str(values[k].get("evidence")) or "") for k in NOISE_FIELDS}
    except (OSError, ValueError, KeyError, TypeError):
        return None
    shas = {m.group(1) if m else None for m in found}
    return shas.pop() if len(shas) == 1 else None


def differs_outside(frozen_doc, doc):
    """Keys whose entries differ from the frozen file's (or are missing or added) other than the four fields."""
    a, b = frozen_doc.get("values") or {}, doc.get("values") or {}
    keys = set(a) | set(b)
    return sorted(k for k in keys if k not in CHANGEABLE and a.get(k) != b.get(k))


def record(path=None):
    """What a run records about the design values it used: file, sha12 of its bytes, the canonical sha12 of
    beaconmind.dv, whether it is the frozen file, and which of the four fields differ."""
    p = frozen_path() if path is None else pathlib.Path(path).resolve()
    frozen = p == frozen_path().resolve()
    out = {"file": _rel(p), "sha12": sha12(p), "canonical_sha12": dvm.dv_sha12(p), "frozen": frozen}
    if not frozen:
        a = dvm.load_dv(frozen_path())
        b = dvm.load_dv(p)
        out["differs_from_frozen"] = {k: [a[k], b[k]] for k in CHANGEABLE if a.get(k) != b.get(k)}
    return out


def check_file(path):
    """Refusals (a list of sentences) for a --dv file: a bm.dv/1 document with the frozen file's keys that differs
    from it only in the four fields."""
    try:
        with open(path, encoding="utf-8") as handle:
            doc = json.load(handle)
    except (OSError, ValueError) as exc:
        return ["the design-values file %s cannot be read: %s" % (path, exc)]
    with open(frozen_path(), encoding="utf-8") as handle:
        frozen_doc = json.load(handle)
    if not isinstance(doc, dict) or doc.get("schema") != "bm.dv/1" or not isinstance(doc.get("values"), dict):
        return ["%s is not a bm.dv/1 document" % path]
    extra = differs_outside(frozen_doc, doc)
    if extra:
        return ["%s differs from the frozen configs/dv.json outside %s: %s" % (path, ", ".join(CHANGEABLE), extra)]
    bad = [k for k in CHANGEABLE if not isinstance((doc["values"].get(k) or {}).get("value"), (int, float))
           or not math.isfinite(doc["values"][k]["value"]) or doc["values"][k]["value"] <= 0]
    if bad:
        return ["%s: these values are not positive numbers: %s" % (path, bad)]
    return []


@contextlib.contextmanager
def use_dv(path=None):
    """Run the block with the design values of `path` (None or the frozen file: nothing changes). Yields record().
    Refuses (ValueError) a file check_file() refuses. Not thread-safe; nothing outside the block sees the values."""
    if path is None or pathlib.Path(path).resolve() == frozen_path().resolve():
        yield record(None)
        return
    problems = check_file(path)
    if problems:
        raise ValueError("; ".join(problems))
    rec = record(path)
    key = str(frozen_path())
    had = key in dvm._CACHE
    saved = dvm._CACHE.get(key)
    values = dvm.load_dv(path)                  # (cached under its own path)
    dvm._CACHE[key] = dict(values)
    try:
        yield rec
    finally:
        if had:
            dvm._CACHE[key] = saved
        else:
            dvm._CACHE.pop(key, None)


def resolve_arg(value):
    """--dv as given: None (default: frozen) or a path; 'frozen' is accepted as the frozen file."""
    if value in (None, "", "frozen"):
        return None
    return os.fspath(value)
