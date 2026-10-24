"""Turn raw Elexon rows into Forecast and Actual records.

Rows that cannot be placed on the timeline are counted and skipped. Rows that can be placed but
carry an unusable value are kept with `generation=None`, so they show up as INVALID_VALUE.
"""

from datetime import UTC, date, datetime
from typing import Any

from app.models.source import Actual, Forecast


def parse_time(value: Any) -> datetime | None:
    """A timezone-aware ISO 8601 timestamp as UTC; None if missing, malformed or naive."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def parse_generation(value: Any) -> int | None:
    # JSON true/false arrive as bool, which Python treats as int, so exclude them first.
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():  # also rejects NaN and infinity
        return int(value)
    return None


def parse_actuals(rows: list[dict[str, Any]]) -> tuple[list[Actual], int, int]:
    """Returns (wind actuals, rejected row count, non-wind row count)."""
    actuals = []
    rejected = 0
    not_wind = 0
    for row in rows:
        if not isinstance(row, dict) or row.get("dataset", "FUELHH") != "FUELHH":
            rejected += 1
            continue
        if row.get("fuelType") != "WIND":
            not_wind += 1
            continue
        start = parse_time(row.get("startTime"))
        if start is None:
            rejected += 1
            continue
        actuals.append(
            Actual(
                start=start,
                generation=parse_generation(row.get("generation")),
                publish_time=parse_time(row.get("publishTime")),
                settlement_date=_parse_date(row.get("settlementDate")),
                settlement_period=_parse_int(row.get("settlementPeriod")),
            )
        )
    return actuals, rejected, not_wind


def parse_forecasts(rows: list[dict[str, Any]]) -> tuple[list[Forecast], int, int]:
    """Returns (hourly forecasts, rejected row count, rows not starting on the hour)."""
    forecasts = []
    rejected = 0
    off_hour = 0
    for row in rows:
        if not isinstance(row, dict) or row.get("dataset", "WINDFOR") != "WINDFOR":
            rejected += 1
            continue
        start = parse_time(row.get("startTime"))
        published = parse_time(row.get("publishTime"))
        if start is None or published is None:
            rejected += 1
            continue
        if start.minute or start.second:
            off_hour += 1
            continue
        forecasts.append(Forecast(start, published, parse_generation(row.get("generation"))))
    return forecasts, rejected, off_hour


def _parse_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def _parse_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
