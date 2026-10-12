"""Lap-time analysis for recorded sim racing sessions.

Pure-stdlib helpers that turn a list of lap times into a stint summary:
best/average lap, dispersion, and a 0-100 consistency score. Used by the
``scripts/lap_report.py`` CLI and importable from the Streamlit apps.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, median, pstdev


@dataclass(frozen=True)
class LapAnalysis:
    """Summary statistics for one stint or session."""

    total_laps: int
    valid_laps: int
    best_lap_seconds: float
    worst_lap_seconds: float
    average_lap_seconds: float
    median_lap_seconds: float
    std_dev_seconds: float
    consistency_score: float  # 0 (erratic) .. 100 (metronomic)
    best_lap_number: int  # 1-based position in the original list


def parse_lap_time(value: str | float | int) -> float:
    """Parse a lap time into seconds.

    Accepts raw seconds (``92.4``), ``M:SS.mmm`` (``1:32.456``), and
    ``H:MM:SS.mmm`` strings. Raises ``ValueError`` on anything else.
    """
    if isinstance(value, (int, float)):
        seconds = float(value)
    else:
        text = str(value).strip()
        if not text:
            raise ValueError("Empty lap time")
        parts = text.split(":")
        try:
            numbers = [float(part) for part in parts]
        except ValueError as exc:
            raise ValueError(f"Unparseable lap time: {value!r}") from exc
        if len(numbers) == 1:
            seconds = numbers[0]
        elif len(numbers) == 2:
            seconds = numbers[0] * 60 + numbers[1]
        elif len(numbers) == 3:
            seconds = numbers[0] * 3600 + numbers[1] * 60 + numbers[2]
        else:
            raise ValueError(f"Unparseable lap time: {value!r}")
    if seconds <= 0:
        raise ValueError(f"Lap time must be positive, got {value!r}")
    return seconds


def _valid_laps(lap_times: list[float], max_factor: float) -> list[tuple[int, float]]:
    """Drop out/in laps: anything slower than ``best * max_factor``."""
    if not lap_times:
        return []
    best = min(lap_times)
    cutoff = best * max_factor
    return [(index, lap) for index, lap in enumerate(lap_times) if lap <= cutoff]


def analyze_laps(lap_times: list[float], *, max_factor: float = 1.5) -> LapAnalysis:
    """Summarize lap times, ignoring laps slower than ``best * max_factor``.

    The consistency score is ``100 - 10 * CV%`` clamped to [0, 100], where
    CV is the coefficient of variation (std / average * 100). A perfectly
    repeatable stint scores near 100; a CV of 10% or more scores 0.
    """
    laps = [parse_lap_time(lap) for lap in lap_times]  # validates positivity
    if not laps:
        raise ValueError("At least one lap time is required")

    valid = _valid_laps(laps, max_factor)
    values = [lap for _, lap in valid]
    average = mean(values)
    std_dev = pstdev(values) if len(values) > 1 else 0.0
    cv_percent = (std_dev / average * 100) if average else 0.0
    consistency = max(0.0, min(100.0, 100.0 - cv_percent * 10))

    best_index, best_value = min(valid, key=lambda item: item[1])
    return LapAnalysis(
        total_laps=len(laps),
        valid_laps=len(values),
        best_lap_seconds=round(best_value, 3),
        worst_lap_seconds=round(max(values), 3),
        average_lap_seconds=round(average, 3),
        median_lap_seconds=round(median(values), 3),
        std_dev_seconds=round(std_dev, 3),
        consistency_score=round(consistency, 1),
        best_lap_number=best_index + 1,
    )


def format_seconds(seconds: float) -> str:
    """Render seconds as ``M:SS.mmm`` (or ``SS.mmm`` under a minute)."""
    if seconds < 60:
        return f"{seconds:.3f}s"
    minutes, remainder = divmod(seconds, 60)
    return f"{int(minutes)}:{remainder:06.3f}"


def format_report(analysis: LapAnalysis) -> str:
    """Human-readable stint report, as printed by the CLI."""
    lines = [
        "Lap analysis",
        "------------",
        f"Laps: {analysis.valid_laps} valid / {analysis.total_laps} total",
        f"Best lap: {format_seconds(analysis.best_lap_seconds)} (lap {analysis.best_lap_number})",
        f"Worst lap: {format_seconds(analysis.worst_lap_seconds)}",
        f"Average: {format_seconds(analysis.average_lap_seconds)}",
        f"Median: {format_seconds(analysis.median_lap_seconds)}",
        f"Std dev: {analysis.std_dev_seconds:.3f}s",
        f"Consistency: {analysis.consistency_score:.1f}/100",
    ]
    return "\n".join(lines)
