"""Tests of the car part's input path (beaconmind.demo.car_part): the recorder's frame index, the join of the
backend's detections to its frames, and the phone-clip alignment through ffmpeg (skipped without an ffmpeg).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote these tests.
"""
import json

import pytest

pytest.importorskip("PIL")

from beaconmind.demo import car_part as CP  # noqa: E402
from beaconmind.demo import ffmpeg as F  # noqa: E402
from beaconmind.demo import timeline as TL  # noqa: E402


def _index(folder, rows):
    folder.mkdir(parents=True)
    (folder / "index.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))


def test_camera_index_prefers_the_backend_frames_and_skips_errors(tmp_path):
    _index(tmp_path / "frames", [{"n": 1, "file": "000001_2000000000.jpg", "t_resp_ns": 2_000_000_000}])
    assert [round(t, 3) for t, _ in CP.camera_index(str(tmp_path))] == [2.0]
    _index(tmp_path / "frames_backend", [
        {"n": 2, "file": "000002_3500000000.jpg", "t_resp_ns": 3_500_000_000},
        {"n": 1, "file": "000001_3000000000.jpg", "t_resp_ns": 3_000_000_000},
        {"n": 3, "error": "CameraError: timeout", "t_resp_ns": 4_000_000_000}])
    idx = CP.camera_index(str(tmp_path))
    assert [t for t, _ in idx] == [3.0, 3.5]
    assert idx[0][1].endswith("frames_backend/000001_3000000000.jpg")


def test_frame_detections_join_the_fused_detection_to_every_frame_it_used():
    backend = [{"type": "step", "step": 4,
                "sense": {"detections": [{"det": 0, "id": 12, "range_m": 1.85, "bearing_deg": 5.0}]},
                "frames": [{"file": "a.jpg"}, {"file": "b.jpg"}],
                "detections_internal": [{"det": 0, "id": 12, "base_xyz_m": [1.84, 0.16, 0.23]}]},
               {"type": "halt", "step": 5}]
    out = CP.frame_detections(backend)
    assert set(out) == {"a.jpg", "b.jpg"}
    step, dets = out["b.jpg"]
    assert step == 4 and dets[0]["range_m"] == 1.85 and dets[0]["base_xyz_m"] == [1.84, 0.16, 0.23]


def test_stripe_values_wrap_and_encode_centiseconds():
    assert CP.stripe_value(1000.25, 1000) == 25
    assert CP.stripe_value(1000.0 + (1 << 24) / 100.0, 1000) == 0


@pytest.mark.skipif(F.find_ffmpeg() is None, reason="no ffmpeg on this machine")
def test_phone_frames_show_the_instants_the_timeline_asks_for(tmp_path):
    exe = F.find_ffmpeg()
    base, epoch0 = 5000.0, 5003.0                       # the clip's frame k shows epoch 5003 + k / 30
    clip = CP.make_standin_phone(exe, str(tmp_path / "clip.mp4"), epoch0, 6.0, base, fps=30, size=(640, 360))
    car = CP.CarPart.__new__(CP.CarPart)               # only what phone_frames needs
    car.sync, car.phone, car.fps = TL.clock_sync([(1.0, epoch0 + 1.0)]), clip, 25
    box = (0, (CP.PHONE[3] - int(360 * CP.PHONE[2] / 640)) // 2, CP.PHONE[2], int(90 * CP.PHONE[2] / 640))
    for piece in (TL.Piece(5004.0, 5005.0, 1.0, "move"), TL.Piece(5004.0, 5008.0, 8.0, "think")):
        n = TL.n_frames(piece, 25)
        want = [w for _i, w, _j in TL.frame_times([piece], 25)]
        got = [CP.read_stripe(img, box, 0.85) / 100.0 + base for img in car.phone_frames(exe, piece, n)]
        assert len(got) == n
        # within half a frame of the 30 fps clip, plus the H.264 and resize margin of one frame
        assert max(abs(g - w) for g, w in zip(got, want)) <= 1.0 / 30 + 1e-6
