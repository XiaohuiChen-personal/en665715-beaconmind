"""JSON Schema loaders for BeaconMind contracts C0–C11 and the M1 config files.

validate() checks one document and returns error strings. It does not fetch
schemas over the network: every $ref is resolved from the local schema files.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote load_schema and validate.
"""

import json
from pathlib import Path

SCHEMA_NAMES = (
    "dv",
    "move",
    "move_result",
    "observation",
    "step",
    "report",
    "world",
    "obslog",
    "runlog",
    "run",
    "providers",
    "car",
    "camera",
    "detector_noise",
)

_DIR = Path(__file__).resolve().parent


def load_schema(name: str, major: int = 1) -> dict:
    """Read bm.<name>-<major>.schema.json from this package."""
    if name not in SCHEMA_NAMES:
        raise KeyError(name)
    path = _DIR / ("bm.%s-%s.schema.json" % (name, major))
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _registry(major):
    from referencing import Registry, Resource

    pairs = []
    for name in SCHEMA_NAMES:
        schema = load_schema(name, major)
        pairs.append((schema["$id"], Resource.from_contents(schema)))
    return Registry().with_resources(pairs)


def validate(name: str, obj, major: int = 1) -> list:
    """Return a list of error strings ('' path: message); [] if valid. Imports jsonschema lazily and
    raises ImportError('pip install jsonschema (extra dev)') if it is missing. Resolves the
    observation $ref inside bm.step-1 through a local registry built from SCHEMA_NAMES, keyed
    by each schema's absolute $id (no network retrieval)."""
    try:
        import jsonschema
    except ImportError:
        raise ImportError("pip install jsonschema (extra dev)")
    try:
        from referencing import Registry, Resource  # noqa: F401
    except ImportError:
        raise ImportError("pip install jsonschema (extra dev)")
    schema = load_schema(name, major)
    validator = jsonschema.Draft202012Validator(schema, registry=_registry(major))
    errors = []
    for err in validator.iter_errors(obj):
        path = err.json_path or ""
        errors.append("%s: %s" % (path, err.message))
    return errors
