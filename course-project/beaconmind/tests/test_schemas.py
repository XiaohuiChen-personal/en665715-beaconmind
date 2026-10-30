"""JSON Schema contract tests for C0–C11.

The verbatim fixtures (move, move_result, observation, step, report_example1) copy
the contract examples and so have no comment line of their own. This module's
disclosure covers those copies.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the schema validation tests.
"""
import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from beaconmind import course_root
from beaconmind.schemas import SCHEMA_NAMES, load_schema, validate

FIX = Path(__file__).parent / "fixtures" / "contracts"


def _load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def test_every_schema_is_valid_2020_12():
    assert len(SCHEMA_NAMES) == 14
    for name in SCHEMA_NAMES:
        schema = load_schema(name)
        Draft202012Validator.check_schema(schema)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"] == (
            "https://schemas.beaconmind.invalid/bm.%s-1.schema.json" % name
        )
        assert schema["title"] == "bm.%s/1" % name


def test_c2_examples_validate():
    assert validate("move", _load("move.json")) == []
    assert validate("move_result", _load("move_result.json")) == []


def test_c3_observation_validates():
    assert validate("observation", _load("observation.json")) == []


def test_step_validates():
    assert validate("step", _load("step.json")) == []


def test_d8_example1_validates():
    assert validate("report", _load("report_example1.json")) == []


def test_c7_world_validates():
    world = _load("world.json")
    assert len(world["tags"]) == 10
    assert world["tags"][0]["uid"] == "T00"
    assert validate("world", world) == []


def test_dv_json_validates():
    path = course_root() / "configs" / "dv.json"
    assert validate("dv", json.loads(path.read_text(encoding="utf-8"))) == []


def test_providers_json_validates():
    config = json.loads((course_root() / "configs" / "providers.json").read_text(encoding="utf-8"))
    assert validate("providers", config) == []
    assert validate("providers", _load("providers.json")) == []


def test_bad_move_result_enum_fails():
    document = _load("move_result.json")
    document["result"] = "ok"
    assert len(validate("move_result", document)) >= 1


def test_observation_missing_field_fails():
    document = _load("observation.json")
    del document["counters"]
    assert len(validate("observation", document)) >= 1


def test_report_bad_label_fails():
    document = _load("report_example1.json")
    document["map"][0]["beacon"] = "B1c"
    assert len(validate("report", document)) >= 1


def test_run_header_rejects_api_key_field():
    header = {
        "schema": "bm.run/1",
        "arm": "L2",
        "model_key": "qwen35-a3b-think",
        "provider": {
            "provider": "vllm",
            "model": "Qwen/Qwen3.5-35B-A3B",
            "api_key_env": None,
            "price_usd_per_mtok": {"input": 0, "cached_input": 0, "output": 0},
            "price_checked": None,
            "options": {},
        },
        "prompt_sha12": "0123456789ab",
        "tool_schema_sha12": "0123456789ab",
        "dv_sha12": "0123456789ab",
        "harness_hashes": {"geometry.py": "0123456789abcdef"},
        "seeds": [1000],
        "K": 3,
        "budget_usd": 0,
        "start_time": "2026-10-06T00:00:00Z",
        "end_time": "2026-10-06T00:01:00Z",
        "host": "spark-2a60",
    }
    assert validate("run", header) == []
    header["api_key"] = "sk-test"
    assert len(validate("run", header)) >= 1


def test_cli_reports_ok(tmp_path):
    fixture = FIX / "move.json"
    proc = subprocess.run(
        [sys.executable, "-m", "beaconmind.schemas", "move", str(fixture)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "OK" in proc.stdout
