"""Tests of tools/report_assets.py: the report's numbers equal the evidence files they are generated from.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote these tests with the report generator.
"""
import importlib.util
import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("report_assets", ROOT / "tools" / "report_assets.py")
ra = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ra)


@pytest.fixture(scope="module")
def src():
    return ra.load()


@pytest.fixture(scope="module")
def numbers(src):
    return {k: v[0] for k, v in ra.build_numbers(src).items()}


def plain(value):
    return float(value.replace(ra.MINUS, "-").replace("+", "").replace(",", ""))


def test_formatting():
    assert ra.num(-0.0283 * 100, 2) == ra.MINUS + "2.83"
    assert ra.num(-0.0001, 2) == "0.00"
    assert ra.signed(0.567 * 100, 1) == "+56.7"
    assert ra.pval(0.002468690276145935) == "0.0025"
    assert ra.pval(7.245317101478577e-05) == "\\ensuremath{7.2\\times10^{-5}}"
    assert ra.pval(0.9999999990686774) == "\\ensuremath{\\approx}1.00"
    assert ra.half_up(36.15, 1) == "36.2"


def test_confirmatory_outcomes_match_the_frozen_summary(src, numbers):
    conf = src["summary"]["confirmatory"]
    for arm, key in (("claude-opus-5-5", "opus"), ("qwen38-flash-xhigh", "qwen"), ("gemma4-26b", "gemma")):
        c = conf["H1:" + arm]
        assert plain(numbers["h1.%s.est" % key]) == pytest.approx(c["estimate"] * 100, abs=0.051)
        assert numbers["h1.%s.reject" % key] == ("rejected" if c["reject_h0"] else "not rejected")
        assert numbers["h1.%s.practical" % key] == "no" and c["practical"] is False
        assert int(numbers["h1.%s.better" % key]) + int(numbers["h1.%s.worse" % key]) \
            + int(numbers["h1.%s.tied" % key]) == 30
        assert conf["H2:" + arm]["tested"] is False
    assert numbers["h1.opus.reject"] == numbers["h1.qwen.reject"] == "rejected"
    assert numbers["h1.gemma.reject"] == "not rejected" and numbers["h1.gemma.test"] == "sign"
    # the practical threshold: both upper ends are above -3 cm
    assert plain(numbers["h1.opus.hi"]) > -3 and plain(numbers["h1.qwen.hi"]) > -3


def test_totals_and_counts(src, numbers):
    assert numbers["n.seeds"] == "30" and numbers["n.steps"] == "1,976"
    assert numbers["spend.opus"] == "143.97"
    assert (numbers["fallbacks.opus"], numbers["fallbacks.qwen"], numbers["fallbacks.gemma"]) == ("1", "12", "78")
    assert numbers["repaired.qwen"] == "97"
    assert (numbers["fid.opus.within"], numbers["fid.qwen.within"], numbers["fid.gemma.within"]) == ("28", "26", "0")
    assert int(numbers["oq.tied"]) + int(numbers["oq.qwen-lower"]) + int(numbers["oq.opus-lower"]) == 30
    assert int(numbers["oq.tied"]) == 30 - src["summary"]["model_comparison"]["pairs"][
        "claude-opus-5-5-qwen38-flash-xhigh"]["n_used"]


def test_b2_minus_b0_agrees_with_the_frozen_statistics_code(src, numbers):
    np = pytest.importorskip("numpy")
    import sys
    sys.path.insert(0, str(ROOT / "beaconmind" / "src"))
    from beaconmind.metrics import stats
    per = src["summary"]["per_seed"]
    d = np.array([per[s]["B2"]["ate_m"] - per[s]["B0"]["ate_m"] for s in sorted(per, key=int)])
    hl = stats.hodges_lehmann(d)
    assert plain(numbers["b2b0.est"]) == pytest.approx(hl["estimate"] * 100, abs=0.006)
    assert plain(numbers["b2b0.lo"]) == pytest.approx(hl["ci"][0] * 100, abs=0.006)
    assert plain(numbers["b2b0.hi"]) == pytest.approx(hl["ci"][1] * 100, abs=0.006)


def test_every_key_used_in_the_report_exists(numbers):
    tex = (ROOT / "report" / "Chen-Project-Report.tex").read_text()
    tex = "\n".join(line for line in tex.splitlines() if not line.lstrip().startswith("%"))
    used = set(re.findall(r"\\bmnum\{([^}]+)\}", tex))
    assert used and not sorted(used - set(numbers))


def test_generated_files_are_up_to_date(src):
    files = ra.render(src)
    for name, text in files.items():
        assert (ROOT / "report" / "generated" / name).read_text() == text, name
    assert json.loads(files["numbers.json"])["status"] == "confirmatory"


def test_pending_list_is_parsed():
    assert len(ra.pending()) == len(re.findall(
        r"^\| \d+ \|", (ROOT / "report" / "PENDING.md").read_text(), re.M))
