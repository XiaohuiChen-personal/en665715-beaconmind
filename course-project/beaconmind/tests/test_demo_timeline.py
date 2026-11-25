"""Tests of beaconmind.demo.timeline: frame counts and times, time-lapse fitting, the phone-clock sync, the sequence.

Hand-computed fixtures; standard library only (no Pillow, no ffmpeg).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote these tests.
"""
import pytest

from beaconmind.demo import timeline as TL


def test_frame_counts_round_half_up():
    # 12.5 frames rounds up to 13 (Python's round() would give 12); 2.5 to 3; never below 1
    assert TL.n_frames(TL.Piece(0.0, 1.0, 2.0), 25) == 13
    assert TL.n_frames(TL.Piece(0.0, 0.1, 1.0), 25) == 3
    assert TL.n_frames(TL.Piece(0.0, 0.0001, 100.0), 25) == 1


def test_frame_times_are_centred_and_increase():
    pieces = [TL.Piece(0.0, 10.0, 10.0), TL.Piece(10.0, 12.0, 1.0)]
    times = TL.frame_times(pieces, 25)
    assert [n for n in TL.frame_counts(pieces, 25)] == [25, 50]
    assert times[0][1] == pytest.approx(0.5 * 10.0 / 25)          # first frame: middle of its slice
    assert times[25][1] == pytest.approx(10.0 + 0.5 * 2.0 / 50)
    assert all(b[1] > a[1] for a, b in zip(times, times[1:]))
    assert [t[0] for t in times] == list(range(75))
    assert TL.output_duration(pieces, 25) == pytest.approx(3.0)


def test_hold_piece_shows_one_instant():
    h = TL.hold(7.0, 2.0)
    assert h.out_s == 2.0 and TL.piece_badge(h) == "paused"
    times = TL.frame_times([TL.Piece(0.0, 7.0, 7.0), h], 25)
    assert len(times) == 75
    assert {t for _, t, j in times if j == 1} == {7.0}
    with pytest.raises(ValueError):
        TL.Piece(1.0, 2.0, 1.0, hold_s=1.0)


def test_speed_badge():
    assert TL.speed_badge(1.0) == "real time"
    assert TL.speed_badge(1.4) == "real time"
    assert TL.speed_badge(8.0) == "×8"
    assert TL.speed_badge(16.4) == "×16"


def test_fit_sim_factor_is_the_smallest_whole_factor_that_fits():
    factor, pieces = TL.fit_sim_factor(1000.0, 50.0, 25)
    assert factor == 20 and TL.output_duration(pieces, 25) == pytest.approx(50.0)
    assert TL.output_duration(TL.sim_pieces(1000.0, 19), 25) > 50.0


def test_fit_sim_factor_with_a_slow_step_and_a_pause():
    # 1000 s of source; step [400, 420] at x2 (10 s) and a 5 s pause: 35 s left for 980 s -> x28
    factor, pieces = TL.fit_sim_factor(1000.0, 50.0, 25, detail=(400.0, 420.0), detail_speed=2.0, hold_s=5.0)
    assert factor == 28
    assert [p.label for p in pieces] == ["timelapse", "detail", "hold", "timelapse"]
    assert pieces[1].speed == 2.0 and pieces[2].hold_s == 5.0 and pieces[2].w0 == 420.0
    assert TL.output_duration(pieces, 25) <= 50.0
    assert TL.output_duration(TL.sim_pieces(1000.0, 27, (400.0, 420.0), 2.0, 5.0), 25) > 50.0
    with pytest.raises(ValueError):
        TL.fit_sim_factor(1000.0, 9.0, 25, detail=(400.0, 420.0), detail_speed=2.0)


def test_output_time_of_a_source_instant():
    pieces = [TL.Piece(0.0, 100.0, 10.0), TL.Piece(100.0, 110.0, 1.0)]
    assert TL.output_time_of(pieces, 25, 0.0) == 0.0
    assert TL.output_time_of(pieces, 25, 100.0) == pytest.approx(10.0 - 1 / 25.0)   # last frame of the first piece
    assert TL.output_time_of(pieces, 25, 105.0) == pytest.approx(15.0)
    assert TL.output_time_of(pieces, 25, 200.0) is None


def test_car_pieces_keep_motion_in_real_time():
    pieces = TL.car_pieces(0.0, 100.0, [(20.0, 22.0), (50.0, 53.0), (52.0, 54.0)], think_speed=10)
    assert [(p.w0, p.w1, p.label) for p in pieces] == [(0.0, 20.0, "think"), (20.0, 22.0, "move"),
                                                       (22.0, 50.0, "think"), (50.0, 54.0, "move"),
                                                       (54.0, 100.0, "think")]
    assert all(p.speed == 1.0 for p in pieces if p.label == "move")
    assert all(a.w1 == b.w0 for a, b in zip(pieces, pieces[1:]))


def test_fit_think_speed_fits_and_never_speeds_up_motion():
    wins = [(20.0, 22.0), (50.0, 54.0)]                      # 6 s of motion, 94 s of waiting
    speed, pieces, fits = TL.fit_think_speed(0.0, 100.0, wins, 16.0, 25)
    assert fits and TL.output_duration(pieces, 25) <= 16.0
    assert TL.output_duration(TL.car_pieces(0.0, 100.0, wins, speed - 1), 25) > 16.0
    speed, pieces, fits = TL.fit_think_speed(0.0, 100.0, wins, 5.0, 25)   # less than the motion itself
    assert not fits
    assert all(p.speed == 1.0 for p in pieces if p.label == "move")


def test_clock_sync_one_reading_gives_the_offset():
    s = TL.clock_sync([TL.parse_reading("1.0=1794988526.6")])
    assert s.rate == 1.0
    assert s.epoch(1.0) == pytest.approx(1794988526.6)
    assert s.phone(1794988530.6) == pytest.approx(5.0)


def test_clock_sync_two_readings_fit_offset_and_rate():
    # a phone whose clock runs 0.05 % fast: 200 s of clip are 199.9 s of epoch
    s = TL.clock_sync([(2.0, 1000.0), (202.0, 1199.9)])
    assert s.rate == pytest.approx(0.9995)
    assert s.epoch(102.0) == pytest.approx(1099.95)
    assert s.residuals() == pytest.approx([0.0, 0.0], abs=1e-9)
    with pytest.raises(ValueError):                           # a misread digit: 10 s off over 200 s
        TL.clock_sync([(2.0, 1000.0), (202.0, 1210.0)])
    with pytest.raises(ValueError):
        TL.parse_reading("12.4")


def test_clock_sync_close_readings_keep_rate_one():
    # 13 s apart, each read to 0.1 s: no rate is fitted, the offset is the mean of the two
    s = TL.clock_sync([(1.0, 1001.04), (14.0, 1013.96)])
    assert s.rate == 1.0 and s.offset == pytest.approx(1000.0)
    with pytest.raises(ValueError):
        TL.clock_sync([(1.0, 1001.0), (14.0, 1015.0)])


def test_latest_at():
    times = [10.0, 10.5, 11.0]
    assert TL.latest_at(times, 10.7) == 1
    assert TL.latest_at(times, 10.5) == 1
    assert TL.latest_at(times, 9.0) is None
    assert TL.latest_at(times, 99.0) == 2


def test_plan_sequence_and_budgets():
    items = [{"id": "title", "kind": "card", "seconds": 6}, {"id": "sim", "kind": "part"},
             {"id": "car", "kind": "part"}, {"id": "end", "kind": "card", "seconds": 4}]
    seq = TL.plan_sequence(items, {"sim": 100.0, "car": None})
    assert [(s["id"], s["start_s"], s["dur_s"]) for s in seq] == [("title", 0.0, 6.0), ("sim", 6.0, 100.0),
                                                                  ("end", 106.0, 4.0)]
    assert TL.card_seconds(items) == 10.0
    assert TL.word_budget(12.0) == 26 and TL.word_budget(6.0, 120) == 12


def test_mixed_pieces_keep_motion_slow_step_and_pauses():
    pieces = TL.mixed_pieces(0.0, 100.0, [(20.0, 22.0), (50.0, 54.0)], 10, 2.0, slow=(30.0, 50.0), slow_speed=2.0,
                             holds=[(50.0, 5.0), (100.0, 3.0)])
    assert [(p.w0, p.w1, p.speed, p.label, p.hold_s) for p in pieces] == [
        (0.0, 20.0, 10.0, "think", None), (20.0, 22.0, 2.0, "move", None), (22.0, 30.0, 10.0, "think", None),
        (30.0, 50.0, 2.0, "detail", None), (50.0, 50.0, 1.0, "hold", 5.0), (50.0, 54.0, 2.0, "move", None),
        (54.0, 100.0, 10.0, "think", None), (100.0, 100.0, 1.0, "hold", 3.0)]
    with pytest.raises(ValueError):
        TL.mixed_pieces(0.0, 10.0, [], 2, holds=[(11.0, 1.0)])


def test_fit_mixed_fits_the_thinking_around_the_fixed_pieces():
    # fixed: motion 6 s at x2 = 3 s, slow step 20 s at x2 = 10 s, pauses 8 s -> 21 s; 74 s of thinking
    # (0-20, 22-30, 54-100) in 9 s -> x9 (x8 gives 9.25 s)
    args = (0.0, 100.0, [(20.0, 22.0), (50.0, 54.0)])
    speed, pieces, fits = TL.fit_mixed(*args, 30.0, 25, 2.0, (30.0, 50.0), 2.0, [(50.0, 5.0), (100.0, 3.0)])
    assert fits and speed == 9 and TL.output_duration(pieces, 25) <= 30.0
    assert all(p.speed == 2.0 for p in pieces if p.label == "move")
    assert TL.output_duration(TL.mixed_pieces(*args, 8, 2.0, (30.0, 50.0), 2.0, [(50.0, 5.0), (100.0, 3.0)]), 25) > 30.0
    assert TL.fit_mixed(*args, 20.0, 25, 2.0, (30.0, 50.0), 2.0, [(50.0, 5.0), (100.0, 3.0)])[2] is False


def test_length_check_is_the_course_bound():
    assert TL.check_length(240.0, (180.0, 300.0)) is None
    assert TL.check_length(180.0, (180.0, 300.0)) is None and TL.check_length(300.0, (180.0, 300.0)) is None
    assert "shorter" in TL.check_length(161.8, (180.0, 300.0))
    assert "longer" in TL.check_length(300.2, (180.0, 300.0))


def test_every_move_gets_at_least_the_minimum_frames():
    wins = [(2.0, 2.2), (5.0, 6.0), (8.0, 8.667)]               # 0.2 s, 1.0 s and a 30 deg turn at 45 deg/s
    pieces = TL.mixed_pieces(0.0, 10.0, wins, 5, 2.0, min_move_frames=7, fps=25)
    frames = TL.move_frames(pieces, wins, 25)
    assert min(frames) >= 7 and frames == [7, 13, 8]
    slowed = [p for p in pieces if p.label == "move" and p.w0 == 2.0][0]
    assert slowed.speed < 1 and TL.speed_badge(slowed.speed) == "slowed \u00d70.7"
    assert all(p.speed == 2.0 for p in pieces if p.label == "move" and p.w0 != 2.0)    # long enough: untouched
