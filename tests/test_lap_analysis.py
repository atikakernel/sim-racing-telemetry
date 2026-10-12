import pytest

from analysis.lap_analysis import analyze_laps, format_seconds, parse_lap_time


def test_parse_lap_time_accepts_seconds_and_clock_formats():
    assert parse_lap_time(92.4) == 92.4
    assert parse_lap_time("92.4") == 92.4
    assert parse_lap_time("1:32.456") == pytest.approx(92.456)
    assert parse_lap_time("1:02:03.5") == pytest.approx(3723.5)


def test_parse_lap_time_rejects_garbage():
    with pytest.raises(ValueError):
        parse_lap_time("not-a-time")
    with pytest.raises(ValueError):
        parse_lap_time(0)
    with pytest.raises(ValueError):
        parse_lap_time("")


def test_analyze_laps_reports_best_average_and_consistency():
    result = analyze_laps([90.0, 90.5, 91.0, 90.2])
    assert result.total_laps == 4
    assert result.valid_laps == 4
    assert result.best_lap_seconds == 90.0
    assert result.best_lap_number == 1
    assert result.average_lap_seconds == pytest.approx(90.425)
    assert 95 <= result.consistency_score <= 100


def test_analyze_laps_ignores_out_laps_beyond_factor():
    # 180s is a pit/out lap next to ~90s flyers: dropped at the 1.5x cutoff.
    result = analyze_laps([90.0, 90.4, 180.0])
    assert result.total_laps == 3
    assert result.valid_laps == 2
    assert result.worst_lap_seconds == 90.4


def test_analyze_laps_requires_at_least_one_lap():
    with pytest.raises(ValueError):
        analyze_laps([])


def test_format_seconds_renders_clock_format():
    assert format_seconds(45.5) == "45.500s"
    assert format_seconds(92.456) == "1:32.456"
