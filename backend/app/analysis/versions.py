"""Every forecast version covering a delivery day, laid out hour by hour.

This feeds views that show how the forecast evolved. It does not choose a forecast: which
version was knowable at a decision time comes only from the day replay.
"""

from datetime import date, datetime

from app.models.analysis import ForecastVersion
from app.models.source import Forecast
from app.utils.dates import hour_start, settlement_starts


def forecast_versions(
    delivery_date: date, forecasts_by_hour: dict[datetime, list[Forecast]]
) -> tuple[list[datetime], list[ForecastVersion]]:
    """Returns the day's forecast hours and, oldest first, each version's value per hour."""
    hours = sorted({hour_start(start) for start in settlement_starts(delivery_date)})

    values_by_version: dict[datetime, dict[datetime, set[int | None]]] = {}
    for hour in hours:
        for forecast in forecasts_by_hour.get(hour, []):
            by_hour = values_by_version.setdefault(forecast.publish_time, {})
            by_hour.setdefault(hour, set()).add(forecast.generation)

    versions = []
    for publish_time in sorted(values_by_version):
        by_hour = values_by_version[publish_time]
        versions.append(
            ForecastVersion(publish_time, [_single_value(by_hour.get(h)) for h in hours])
        )
    return hours, versions


def _single_value(values: set[int | None] | None) -> int | None:
    """The value if there is exactly one; None if the hour is missing or its records disagree."""
    if values and len(values) == 1:
        return next(iter(values))
    return None
