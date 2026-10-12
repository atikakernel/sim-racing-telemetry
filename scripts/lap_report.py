#!/usr/bin/env python3
"""Print a lap-consistency report for a recorded session CSV.

Usage:
    python scripts/lap_report.py laps.csv [--column lap_time]

The CSV must contain a lap-time column (``lap_time``, ``LapTime`` or
``lap``; the first column is used as a fallback). Values may be raw
seconds (``92.4``) or ``M:SS.mmm`` strings.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analysis.lap_analysis import analyze_laps, format_report, parse_lap_time

CANDIDATE_COLUMNS = ("lap_time", "LapTime", "lap", "Lap", "time", "Time")


def read_lap_times(path: Path, column: str | None) -> list[float]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")
        chosen = column or next(
            (name for name in CANDIDATE_COLUMNS if name in reader.fieldnames),
            reader.fieldnames[0],
        )
        if chosen not in reader.fieldnames:
            raise ValueError(f"Column {chosen!r} not in CSV header {reader.fieldnames}")
        return [parse_lap_time(row[chosen]) for row in reader if row.get(chosen)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path, help="CSV file with one lap per row")
    parser.add_argument("--column", default=None, help="Lap-time column name")
    args = parser.parse_args(argv)

    try:
        lap_times = read_lap_times(args.csv_path, args.column)
        print(format_report(analyze_laps(lap_times)))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
