"""Tests of the demo video's renderers (Pillow), the ffmpeg command lines, the narration generator and the card file.

Pillow tests are skipped without Pillow; the one encode test is skipped without an ffmpeg (beaconmind.demo.ffmpeg
.find_ffmpeg). Tests that need the git-ignored simulated episode are skipped when its logs are absent.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote these tests.
"""
import json
import os

import pytest

import beaconmind
from beaconmind.demo import ffmpeg as F
from beaconmind.demo import narration as NR
from beaconmind.demo import numbers as N

PIL = pytest.importorskip("PIL")

from beaconmind.demo import cards as C  # noqa: E402
from beaconmind.demo import draw as D  # noqa: E402
from beaconmind.demo import panels as P  # noqa: E402
from beaconmind.demo.episode import Call  # noqa: E402
from beaconmind.demo.topdown import TopDown  # noqa: E402

ROOT = str(beaconmind.course_root())
SQUARE = {"walls_polygon": [[-1.0, -1.0], [1.25, -1.0], [1.25, 1.25], [-1.0, 1.25]]}


def test_topdown_is_a_rotation_never_a_mirror():
    td0 = TopDown(SQUARE, [], (400, 400), view_rot_deg=0.0)
    ox, oy = td0.px_out(0.0, 0.0)
    x1, y1 = td0.px_out(0.5, 0.0)
    xl, yl = td0.px_out(0.0, 0.5)
    assert x1 > ox and abs(y1 - oy) < 1e-6          # +x to the right
    assert yl < oy and abs(xl - ox) < 1e-6          # +y up (a left turn is counter-clockwise on screen)
    td = TopDown(SQUARE, [], (400, 400), view_rot_deg=180.0)
    ox, oy = td.px_out(0.0, 0.0)
    x1, _ = td.px_out(0.5, 0.0)
    _, yl = td.px_out(0.0, 0.5)
    assert x1 < ox and yl > oy                      # turned half a circle, still counter-clockwise
    # cross product of the screen images of +x and +y keeps its sign (no mirror)
    ax, ay = x1 - ox, 0.0
    bx, by = 0.0, yl - oy
    assert ax * (-by) - (-ay) * bx > 0


def test_topdown_draws_the_car_where_the_pose_is():
    td = TopDown(SQUARE, [{"tag": 0, "id": 5, "x_m": 1.25, "y_m": 0.0, "normal_deg": 180.0}], (400, 400),
                 view_rot_deg=0.0)
    img = td.render(truth={"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}, mapped={0}, show_fov=False)
    assert img.size == (400, 400)
    x, y = td.px_out(-0.08, 0.0)                     # inside the body, behind the white heading arrow
    assert all(abs(a - b) <= 12 for a, b in zip(img.getpixel((int(x), int(y))), D.CAR_BODY))   # scaled down: near
    tx, ty = td.px_out(1.25, 0.0)
    assert img.getpixel((int(tx), int(ty))) == D.MAPPED


def test_header_drops_chips_that_do_not_fit():
    img = P.header((1920, 84), ("SIMULATION", "a label"), [("real time", "07:00"), ("cost", "US$1.00")],
                   [("thinking \u00d722", False, D.WARN), ("driving \u00d72", True, D.OK)])
    assert img.size == (1920, 84)
    small = P.header((700, 84), ("SIMULATION", "a long label for a narrow bar"),
                     [("real time", "07:00"), ("model cost", "US$1.00"), ("tags mapped", "14 of 20")], "\u00d722")
    assert small.size == (700, 84)


def test_call_text_names_detections_by_tag_id():
    obs = {"detections": [{"det": 0, "id": 12}, {"det": 1, "id": 5}]}
    gate = Call("gate_detection", {"det": 1, "candidates": ["B5"]},
                {"candidates": [{"beacon": "B5", "in_gate": True, "point_distance_m": 0.02}]}, 0.0, True)
    assert P.call_text(gate, obs) == ("gate_detection", "ID 5 \u2248 B5 (0.02 m apart): match")
    err = Call("fix_pose", {}, {"status": "error", "error": "no matched confirmed beacons in this step. Nothing."},
               0.0, False)
    assert P.call_text(err, obs)[1] == "error: no matched confirmed beacons in this step"
    move = Call("move", {"action": "FORWARD_25"}, {"result": "refused", "reason": "not in forward_allowed"}, 0, True)
    assert P.call_text(move, obs)[1] == "FORWARD_25: refused (not in forward_allowed)"
    assert P.fmt_num(-0.004) == "0.00" and P.fmt_num(-1.5, 1) == "\u22121.5"


def test_cards_render_and_refuse_unfilled_fields():
    img = C.render_card({"style": "text", "title": "T", "lines": ["one", "!a warning"], "rows": [["a", "b"]]})
    assert img.size == (1920, 1080)
    assert len(set(img.resize((64, 36)).getdata())) > 1
    for bad in ({"title": "x {{sim.steps}}"}, {"title": "t", "lines": ["TBD"]}):
        with pytest.raises(C.UnfilledCard):
            C.render_card(bad)


def test_stripe_round_trip():
    from beaconmind.demo.car_part import draw_stripe, read_stripe, stripe_value
    img, dr = D.canvas((1280, 720), (0, 0, 0))
    v = stripe_value(1794988531.27, 1794988519)
    draw_stripe(dr, v, 1280, 90)
    small = img.resize((1130, 636))
    assert read_stripe(small, (0, 0, 1130, int(90 * 1130 / 1280))) == v == 1227


def test_ffmpeg_command_lines_are_argument_lists():
    enc = F.encode_cmd("ffmpeg", (1920, 1080), 25, "out.mp4")
    assert all(isinstance(a, str) for a in enc) and "1920x1080" in enc and "libx264" in enc and "yuv420p" in enc
    mux = F.mux_cmd("ffmpeg", "v.mp4", "n.m4a", "o.mp4")
    assert "copy" in mux and "apad" in mux and "-shortest" in mux
    dec = F.decode_cmd("ffmpeg", "clip.mov", 100.0, 13.0, 8.0, 25, (1130, 636), 41)
    assert dec[dec.index("-ss") + 1] == "100.000" and dec[dec.index("-t") + 1] == "13.000"
    assert "setpts=(PTS-STARTPTS)/8.0" in dec[dec.index("-vf") + 1] and dec[dec.index("-frames:v") + 1] == "41"
    assert F.concat_list_text(["/a/b.mp4", "/c/it's.mp4"]) == "file '/a/b.mp4'\nfile '/c/it'\\''s.mp4'\n"


@pytest.mark.skipif(F.find_ffmpeg() is None, reason="no ffmpeg on this machine")
def test_encode_and_probe_ten_frames(tmp_path):
    exe = F.find_ffmpeg()
    out = str(tmp_path / "t.mp4")
    with F.Encoder(exe, (320, 240), 25, out) as enc:
        img, _ = D.canvas((320, 240), (10, 20, 30))
        enc.write(img, 10)
    info = F.probe(exe, out)
    assert info["frames"] == 10 and info["width"] == 320 and info["height"] == 240
    assert abs(info["duration_s"] - 0.4) < 0.05


def test_narration_blocks_are_timed_and_budgeted():
    text = "intro\n@@ title\nHello there.\n@@ sim.detail\nOne {{a.n}} two three four five six.\n@@ car.part\nLater."
    blocks = NR.parse_template(text)
    assert blocks == [("title", "Hello there."), ("sim.detail", "One {{a.n}} two three four five six."),
                      ("car.part", "Later.")]
    n = N.Numbers()
    n.put("a.n", "7", "test")
    rows, missing = NR.build(blocks, {"title": 0.0, "sim.detail": 2.0}, 4.0, n, words_per_min=120)
    assert missing == ["car.part"]
    assert [(r["cue"], r["start_s"], r["end_s"], r["budget"], r["words"], r["over"]) for r in rows] == \
        [("title", 0.0, 2.0, 4, 2, False), ("sim.detail", 2.0, 4.0, 4, 7, True)]
    assert rows[1]["text"].startswith("One 7 two")
    md = NR.render_markdown(rows, missing, 4.0, "# H", "## F", 120)
    assert "`car.part`" in md and "| 0:00.0 | 0:02.0 | `title` | 2.0 | 2 / 4 |" in md


def _sim_numbers():
    sim = os.path.join(ROOT, "data", "closed-loop", "20261118-room-final", "claude-opus-5-5")
    if not os.path.isdir(sim):
        pytest.skip("the simulated episode's logs are git-ignored and not here")
    from beaconmind.demo.video_cli import Build
    return Build(root=ROOT, car_inputs={})


def test_every_card_and_narration_block_fills_from_the_logs():
    b = _sim_numbers()
    with open(os.path.join(ROOT, "presentation", "demo-cards.json")) as fh:
        specs = json.load(fh)
    from beaconmind.demo.sim_part import card_from_spec
    for name, spec in specs.items():
        if name.startswith("$"):
            continue
        card = card_from_spec(spec, b.nums, have_car=True)
        C._check(card)                                    # raises on any unfilled field
    with open(os.path.join(ROOT, "presentation", "demo-voiceover.template.md")) as fh:
        for _cue, text in NR.parse_template(fh.read()):
            assert "{{" not in b.nums.fill(text)
    # the numbers the result card shows are the report's (tools/report_assets.py)
    assert b.nums["cl.opus.tags-found"] == "14" and b.nums["sim.cost"] == b.nums["cl.opus.cost"]


def test_the_plan_fits_the_simulation_target():
    b = _sim_numbers()
    p = b.plan()
    sim = [s for s in p["sequence"] if s["id"] == "sim"][0]
    assert sim["dur_s"] <= b.cfg["sim"]["target_s_without_car"] + 1e-9           # no car part in this build
    lo, hi = b.length_bounds()
    assert (lo, hi) == (180.0, 300.0) and p["length_problem"] is None and lo <= p["total_s"] <= hi
    cues = p["cues"]
    assert cues["title"] == 0.0 and cues["sim.part"] == sim["start_s"]
    assert cues["sim.episode"] < cues["sim.detail"] < cues["sim.detail.end"] < cues["sim.result"]
    assert p["total_frames"] == sum(s["frames"] for s in p["sequence"])
