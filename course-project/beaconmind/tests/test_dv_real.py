"""configs/dv-real.json and the --dv switch (beaconmind/dv_real.py, tools/real_dv.py; Xiaohui Chen approved a separate
design-values file for real runs on 2026-11-24). Everything here uses a fixture detector-noise file: the real
configs/dv-real.json is written only after the tag pilot, and configs/dv.json and the pre-registered files stay as they
are (checked at the end of every test that runs a tool).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote these tests.
"""
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys

import pytest

import beaconmind
from beaconmind import dv as dvm
from beaconmind import dv_real
from beaconmind import geometry as g
from beaconmind.envs import kinsim_room as kr

ROOT = beaconmind.course_root()
FROZEN = ROOT / "configs" / "dv.json"
FROZEN_BYTES = FROZEN.read_bytes()
REAL = ROOT / "configs" / "dv-real.json"
WORLD20 = ROOT / "configs" / "arenas" / "real-room-plus8-160mm-nominal.json"
FROZEN_VALUES = {k: v["value"] for k, v in json.loads(FROZEN_BYTES)["values"].items()}


def noise_model(**over):
    """A bm.detector_noise/1 document as tools/tag_pilot.py analyze writes it (invented numbers: a fixture)."""
    model = {"schema": "bm.detector_noise/1", "range_bias_m": {"a": 0.004, "b": -0.006},
             "range_sigma_m": {"a": 0.01, "b": 0.012}, "bearing_bias_deg": 0.2, "bearing_sigma_deg": {"a": 0.3, "b": 0.1},
             "min_range_m": 0.75, "max_range_m": 3.2, "max_incidence_deg": 60.0,
             "p_detect": [{"range_m": 1.0, "incidence_deg": 0.0, "p": 1.0}], "obs_frames": 5, "obs_min_frames": 3,
             "tag_black_size_m": 0.16,
             "source": {"log": "fixture frames.csv", "date": "2026-11-25", "n_frames": 900, "n_placements": 30}}
    model.update(over)
    return model


def tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / ("%s.py" % name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def real_dv(tmp_path):
    """A dv-real file written by tools/real_dv.py from the fixture noise file, in tmp_path."""
    noise = tmp_path / "detector_noise.json"
    noise.write_text(json.dumps(noise_model()))
    out = tmp_path / "dv-real.json"
    assert tool("real_dv").main(["--noise", str(noise), "--reject-range", "3.0", "--out", str(out),
                                 "--date", "2026-11-25"]) == 0
    yield out, noise
    assert FROZEN.read_bytes() == FROZEN_BYTES and not REAL.exists()


def test_the_pilots_model_maps_onto_the_agents_noise_fields():
    """Range: |bias| + sigma for each term (the detector does not correct the bias). Bearing: one value for every
    range, the pilot's at the range limit plus |bias|. Rounded up; never zero."""
    v = dv_real.noise_to_dv(noise_model(), 3.0)
    assert v == {"sigma_range_a_m": 0.014, "sigma_range_b_per_m": 0.018, "sigma_bearing_deg": 0.8}
    assert dv_real.noise_to_dv(noise_model(), 2.5)["sigma_bearing_deg"] == 0.75
    tiny = dv_real.noise_to_dv(noise_model(range_bias_m={"a": 0, "b": 0}, range_sigma_m={"a": 0.0, "b": 0.00001},
                                           bearing_bias_deg=0.0, bearing_sigma_deg={"a": 0.0, "b": 0.0}), 3.0)
    assert tiny == {"sigma_range_a_m": 0.005, "sigma_range_b_per_m": 0.0001, "sigma_bearing_deg": 0.1}
    assert dv_real.noise_to_dv(noise_model(range_sigma_m={"a": 0.01234, "b": 0.012}), 3.0)["sigma_range_a_m"] == 0.0164
    for bad in (noise_model(schema="bm.detector_noise/2"), noise_model(range_sigma_m={"a": -0.01, "b": 0.0}),
                noise_model(bearing_sigma_deg={"a": float("nan"), "b": 0.0}), {"schema": "bm.detector_noise/1"}):
        with pytest.raises(ValueError):
            dv_real.noise_to_dv(bad, 3.0)


def test_the_real_file_differs_from_the_frozen_one_in_exactly_four_fields(real_dv):
    out, noise = real_dv
    doc = json.loads(out.read_text())
    frozen = json.loads(FROZEN_BYTES)
    assert set(doc["values"]) == set(frozen["values"])
    changed = sorted(k for k in doc["values"] if doc["values"][k] != frozen["values"][k])
    assert changed == sorted(dv_real.CHANGEABLE)
    for k in ("well_cond_sigma_xy_m", "well_cond_sigma_theta_deg", "reloc_sigma_xy_m", "reloc_sigma_theta_deg",
              "gate_range_m", "gate_bearing_deg"):
        assert doc["values"][k] == frozen["values"][k]                  # thresholds stay frozen (module text)
    noise_sha = hashlib.sha256(noise.read_bytes()).hexdigest()[:12]
    for k in dv_real.NOISE_FIELDS:
        e = doc["values"][k]
        assert e["status"] == "measured" and e["updated"] == "2026-11-25" and "sha12 %s" % noise_sha in e["evidence"]
        assert "sha256 %s" % hashlib.sha256(noise.read_bytes()).hexdigest() in e["evidence"]
        assert "fixture frames.csv" in e["source"] and e["unit"] == frozen["values"][k]["unit"]
    r = doc["values"]["reject_range_above_m"]
    assert r["value"] == 3.0 and r["status"] == "DV" and "Xiaohui" in r["source"] and r["updated"] == "2026-11-25"
    comment = doc["$comment"]
    assert hashlib.sha256(FROZEN_BYTES).hexdigest()[:12] in comment and noise_sha in comment
    assert all(k in comment for k in dv_real.CHANGEABLE) and "AI-assisted" in comment
    from beaconmind.schemas import validate
    assert validate("dv", doc) == []
    assert dv_real.check_file(out) == []
    assert dv_real.noise_source(out) == hashlib.sha256(noise.read_bytes()).hexdigest()
    assert dv_real.noise_source(FROZEN) is None


def test_the_tool_refuses_what_it_must(tmp_path, real_dv, monkeypatch):
    out, noise = real_dv
    real = tool("real_dv")
    base = ["--noise", str(noise), "--reject-range", "3.0"]
    assert real.main(base + ["--out", str(out)]) == 2                    # exists: not without --force
    assert real.main(base + ["--out", str(out), "--force"]) == 0
    assert real.main(base + ["--out", str(FROZEN)]) == 2                 # the frozen file is never written
    assert real.main(["--noise", str(noise), "--reject-range", "3.5", "--out", str(tmp_path / "a.json")]) == 2
    assert real.main(["--noise", str(noise), "--reject-range", "3.5", "--out", str(tmp_path / "a.json"),
                      "--beyond-pilot-range"]) == 0                     # beyond the pilot's 3.2 m: only by decision
    assert "set beyond it by decision" in json.loads((tmp_path / "a.json").read_text())["values"]["reject_range_above_m"]["source"]
    assert real.main(["--noise", str(noise), "--reject-range", "0.2", "--out", str(tmp_path / "b.json")]) == 2
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps(noise_model(range_sigma_m={"a": 0.01})))
    assert real.main(["--noise", str(broken), "--reject-range", "3.0", "--out", str(tmp_path / "c.json")]) == 2
    frozen = json.loads(FROZEN_BYTES)
    # build_real_dv's own last check: a field it changes that is not on the allowed list (simulated by taking the
    # range limit off the list) refuses the whole document
    monkeypatch.setattr(dv_real, "CHANGEABLE", dv_real.NOISE_FIELDS)
    with pytest.raises(ValueError, match="outside the four fields: \\['reject_range_above_m'\\]"):
        dv_real.build_real_dv(frozen, "x", noise_model(), "n", "y", 3.0, "2026-11-25")
    monkeypatch.undo()
    assert not (tmp_path / "b.json").exists() and not (tmp_path / "c.json").exists()
    assert dv_real.differs_outside(frozen, frozen) == []


def test_a_dv_file_that_differs_anywhere_else_is_refused(tmp_path, real_dv):
    out, _ = real_dv
    doc = json.loads(out.read_text())
    doc["values"]["well_cond_sigma_xy_m"]["value"] = 0.5                 # a threshold changed by hand
    edited = tmp_path / "edited.json"
    edited.write_text(json.dumps(doc))
    assert "well_cond_sigma_xy_m" in dv_real.check_file(edited)[0]
    with pytest.raises(ValueError):
        with dv_real.use_dv(edited):
            pass
    doc = json.loads(out.read_text())
    doc["values"]["sigma_bearing_deg"]["value"] = 0.0
    edited.write_text(json.dumps(doc))
    assert "not positive" in dv_real.check_file(edited)[0]
    assert "cannot be read" in dv_real.check_file(tmp_path / "none.json")[0]


def two_tag_fix_sigma():
    """fix_pose's full fix of two tags 1.5 m ahead (the agent's geometry, reading the cached default values)."""
    prior = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
    matches = [{"det": {"range_m": 1.5, "bearing_deg": 15.0}, "point": {"x_m": 1.5 * math.cos(math.radians(15)),
                                                                        "y_m": 1.5 * math.sin(math.radians(15))}},
               {"det": {"range_m": 1.5, "bearing_deg": -15.0}, "point": {"x_m": 1.5 * math.cos(math.radians(15)),
                                                                         "y_m": -1.5 * math.sin(math.radians(15))}}]
    return g.fix_pose(prior, matches)


def test_the_override_is_scoped_and_code_without_it_sees_the_frozen_values(real_dv):
    """Inside use_dv every load_dv() of the default file (geometry, the harness, the car code) returns the file's
    values, and the agent's fix is judged by them; outside it, before and after, also after an exception and inside
    the room rehearsal's own override, the frozen values, in this same test session."""
    out, _ = real_dv
    before_fix = two_tag_fix_sigma()
    assert dvm.load_dv() == FROZEN_VALUES
    with dv_real.use_dv(out) as rec:
        assert rec["file"].endswith("dv-real.json") and not rec["frozen"] and rec["sha12"] == dv_real.sha12(out)
        assert rec["differs_from_frozen"]["sigma_bearing_deg"] == [2.0, 0.8]
        inside = dvm.load_dv()
        assert inside["sigma_bearing_deg"] == 0.8 and inside["reject_range_above_m"] == 3.0
        assert inside["well_cond_sigma_xy_m"] == FROZEN_VALUES["well_cond_sigma_xy_m"]
        assert dvm.load_dv(FROZEN) == inside        # (one cache entry: the default file named by path reads the same)
        inside_fix = two_tag_fix_sigma()
    assert dvm.load_dv() == FROZEN_VALUES
    assert json.dumps(two_tag_fix_sigma(), sort_keys=True) == json.dumps(before_fix, sort_keys=True)
    assert json.dumps(inside_fix, sort_keys=True) != json.dumps(before_fix, sort_keys=True)   # the agent saw them
    with pytest.raises(RuntimeError):
        with dv_real.use_dv(out):
            raise RuntimeError("an episode failed")
    assert dvm.load_dv() == FROZEN_VALUES
    with kr.dv_override(sigma_bearing_deg=1.5):
        with dv_real.use_dv(out):
            assert dvm.load_dv()["sigma_bearing_deg"] == 0.8
        assert dvm.load_dv()["sigma_bearing_deg"] == 1.5
    assert dvm.load_dv() == FROZEN_VALUES
    dvm._CACHE.pop(str(dv_real.frozen_path()), None)                    # nothing cached yet: still restored
    with dv_real.use_dv(out):
        assert dvm.load_dv()["sigma_bearing_deg"] == 0.8
    assert dvm.load_dv() == FROZEN_VALUES
    with dv_real.use_dv(None) as rec:                                    # no --dv: nothing changes
        assert rec["frozen"] and rec["file"] == "configs/dv.json" and dvm.load_dv() == FROZEN_VALUES


def test_closed_loop_run_records_the_file_and_keeps_the_frozen_configuration(tmp_path, real_dv):
    out, _ = real_dv
    base = [sys.executable, str(ROOT / "tools" / "closed_loop_run.py"), "--driver", "b2", "--env", "room", "--world",
            str(WORLD20), "--start", "2.5,1.5,90", "--max-range", "3.0", "--seeds", "1", "--max-steps", "2", "--cap-usd", "0"]
    env = dict(os.environ, PYTHONPATH=str(ROOT / "beaconmind" / "src"))
    runs = {}
    for name, extra in (("real", ["--dv", str(out)]), ("frozen", []), ("named", ["--dv", str(FROZEN)])):
        p = subprocess.run(base + ["--out", str(tmp_path / name)] + extra, env=env, capture_output=True, text=True,
                           timeout=300)
        assert p.returncode == 0, p.stdout[-800:] + p.stderr[-800:]
        runs[name] = json.loads((tmp_path / name / "run.json").read_text())
    assert runs["real"]["dv_file"]["sha12"] == dv_real.sha12(out) and runs["real"]["dv_file"]["frozen"] is False
    assert runs["real"]["dv_file"]["differs_from_frozen"]["reject_range_above_m"] == [2.0, 3.0]
    assert runs["frozen"]["dv_file"] == {"file": "configs/dv.json", "sha12": dv_real.sha12(FROZEN),
                                         "canonical_sha12": dvm.dv_sha12(), "frozen": True}
    assert "dv_file" in runs["real"] and runs["real"]["config"] != runs["frozen"]["config"]
    assert runs["named"]["config"] == runs["frozen"]["config"]          # naming the frozen file changes nothing
    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    p = subprocess.run(base + ["--out", str(tmp_path / "bad"), "--dv", str(bad)], env=env, capture_output=True,
                       text=True, timeout=120)
    assert p.returncode != 0 and "not a bm.dv/1 document" in p.stderr and not (tmp_path / "bad").exists()


def test_car_batch_takes_dv_and_a_real_batch_must_name_it(tmp_path, real_dv, capsys):
    out, noise = real_dv
    batch = tool("car_batch")
    run = ["run", "--world", str(WORLD20), "--start", "S1:2.5,1.5,90", "--initial-pose", "2.4,1.6,70", "--max-steps", "3",
           "--max-range", "3.0"]
    # a real batch without --dv: refused (with the marker's refusal, nothing sent, before any ROS import)
    assert batch.main(run + ["--label", "t", "--marker", str(tmp_path / "none.json"), "--latch", str(tmp_path / "L")]) == 2
    err = capsys.readouterr().err
    assert "a real batch needs --dv" in err and "no pass marker" in err
    # a dry run with --dv: the file and its sha12 in the manifest, and in the summary; another configuration
    assert batch.main(run + ["--dry-run", "--out", str(tmp_path / "a"), "--dv", str(out), "--detector-noise", str(noise)]) == 0
    m = json.loads((tmp_path / "a" / "manifest.json").read_text())
    assert dv_real.sha12(out) in m["params"]["dv_file"] and "differs from the frozen file" in m["params"]["dv_file"]
    assert "design values: " in (tmp_path / "a" / "summary.txt").read_text()
    assert dvm.load_dv() == FROZEN_VALUES                               # restored after the batch, same session
    assert batch.main(run + ["--dry-run", "--out", str(tmp_path / "b")]) == 0
    m2 = json.loads((tmp_path / "b" / "manifest.json").read_text())
    assert m2["params"]["dv_file"].startswith("configs/dv.json sha12 %s (frozen)" % dv_real.sha12(FROZEN))
    assert m2["config"] != m["config"]
    # the range limit of the file and --max-range must agree; the sigmas must come from --detector-noise
    assert batch.main(run[:-1] + ["2.5", "--dry-run", "--out", str(tmp_path / "c"), "--dv", str(out)]) == 2
    assert "range limit 3.00 m, --max-range is 2.50 m" in capsys.readouterr().err
    other = tmp_path / "other_noise.json"
    other.write_text(json.dumps(noise_model(bearing_bias_deg=0.1)))
    assert batch.main(run + ["--dry-run", "--out", str(tmp_path / "d"), "--dv", str(out), "--detector-noise", str(other)]) == 2
    assert "was not made from --detector-noise" in capsys.readouterr().err
    assert not (tmp_path / "c").exists() and not (tmp_path / "d").exists()


def test_room_rehearsal_one_takes_a_file(tmp_path, real_dv):
    out, _ = real_dv
    rehearsal = tool("room_rehearsal")
    assert rehearsal.dv_tag("frozen") == "" and rehearsal.dv_tag("measured") == "-dv-measured"
    assert rehearsal.dv_tag(str(out)) == "-dv-dv-real"
    p = subprocess.run([sys.executable, str(ROOT / "tools" / "room_rehearsal.py"), "one", "--option", "A", "--scenario",
                        "S1", "--range", "3.0", "--dv", str(out)], capture_output=True, text=True, timeout=300,
                       env=dict(os.environ, PYTHONPATH=str(ROOT / "beaconmind" / "src")))
    assert p.returncode == 0, p.stderr[-800:]
    metrics = json.loads(p.stdout[p.stdout.index("{"):])
    assert metrics["dv"]["sha12"] == dv_real.sha12(out) and metrics["dv"]["frozen"] is False
    with rehearsal.dv_scope(str(out)):
        assert dvm.load_dv()["sigma_range_b_per_m"] == 0.018
    with rehearsal.dv_scope("measured"):
        assert dvm.load_dv()["sigma_bearing_deg"] == kr.MEASURED_SIGMA_DV["sigma_bearing_deg"]
    assert dvm.load_dv() == FROZEN_VALUES


def test_a_real_batch_takes_both_sigmas_from_one_detector_noise_file(tmp_path, real_dv, capsys):
    """The lead's rule (2026-11-25): the agent's sigmas (--dv) and the batch's fix sigma (--detector-noise) come from
    the same configs/detector_noise.json, and real batches run with it. The manifest says whether they agree, with the
    sha256; a real batch is refused when they would not (these refusals are listed with the pass marker's, before
    anything is sent)."""
    out, noise = real_dv
    batch = tool("car_batch")
    run = ["run", "--world", str(WORLD20), "--start", "S1:2.5,1.5,90", "--initial-pose", "2.4,1.6,70", "--max-steps", "3",
           "--max-range", "3.0"]
    real = run + ["--label", "t", "--marker", str(tmp_path / "none.json"), "--latch", str(tmp_path / "L")]
    full = hashlib.sha256(noise.read_bytes()).hexdigest()
    assert batch.main(real + ["--dv", str(out), "--detector-noise", str(noise)]) == 2
    err = capsys.readouterr().err
    assert "no pass marker" in err and "--dv" not in err and "--detector-noise" not in err      # only the marker stops it
    for extra, why in ((["--dv", str(FROZEN), "--detector-noise", str(noise)], "not the frozen configs/dv.json"),
                       (["--dv", str(out)], "a real batch needs --detector-noise"),
                       (["--detector-noise", str(noise)], "a real batch needs --dv")):
        assert batch.main(real + extra) == 2
        err = capsys.readouterr().err
        assert why in err and "no pass marker" in err, (extra, err)
    other = tmp_path / "other_noise.json"
    other.write_text(json.dumps(noise_model(bearing_bias_deg=0.1)))
    assert batch.main(real + ["--dv", str(out), "--detector-noise", str(other)]) == 2
    assert "was not made from --detector-noise" in capsys.readouterr().err
    # the dry run records the agreement with the sha256, and says so in the summary
    assert batch.main(run + ["--dry-run", "--out", str(tmp_path / "a"), "--dv", str(out), "--detector-noise", str(noise)]) == 0
    m = json.loads((tmp_path / "a" / "manifest.json").read_text())
    assert m["params"]["sigma_sources"].startswith("agree:") and full in m["params"]["sigma_sources"]
    assert "sigma sources: agree" in (tmp_path / "a" / "summary.txt").read_text()
    assert batch.main(run + ["--dry-run", "--out", str(tmp_path / "b"), "--detector-noise", str(noise)]) == 0
    assert json.loads((tmp_path / "b" / "manifest.json").read_text())["params"]["sigma_sources"].startswith(
        "not the same file: the agent's sigmas are the frozen study's")
    assert dvm.load_dv() == FROZEN_VALUES and FROZEN.read_bytes() == FROZEN_BYTES
