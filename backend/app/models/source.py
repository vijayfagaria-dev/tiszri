"""Records parsed from the Elexon datasets."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

FORECAST_PERIOD = timedelta(hours=1)  # WINDFOR publishes hourly values


@dataclass
class Forecast:
    """One WINDFOR value: the forecast for the hour starting at `start`."""

    start: datetime
    publish_time: datetime
    generation: int | None  # None when the source value is unusable


@dataclass
class Actual:
    """One FUELHH wind value for the half-hour settlement period starting at `start`."""

    start: datetime
    generation: int | None
    publish_time: datetime | None = None
    settlement_date: date | None = None
    settlement_period: int | None = None
