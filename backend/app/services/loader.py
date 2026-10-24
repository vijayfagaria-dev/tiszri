"""Fetch and parse the source data needed for a range of delivery dates."""

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.analysis.replay import index_actuals, index_forecasts
from app.clients.base import DataSource
from app.clients.parsing import parse_actuals, parse_forecasts
from app.models.analysis import AnalysisWarning
from app.models.enums import WarningCode
from app.models.source import Actual, Forecast
from app.utils.dates import day_bounds, format_utc


@dataclass
class SourceInfo:
    """Where one dataset came from and how many of its rows were usable."""

    dataset: str
    role: str
    requested_from: str
    requested_to: str
    basis: str  # SETTLEMENT_DATE or PUBLISH_TIME
    rows_received: int
    rows_rejected: int
    rows_filtered: int
    fetched_at: datetime
    cache: str


@dataclass
class LoadedData:
    forecasts_by_hour: dict[datetime, list[Forecast]]
    actuals_by_start: dict[datetime, list[Actual]]
    publish_times: set[datetime]
    sources: list[SourceInfo]
    warnings: list[AnalysisWarning]


async def load_data(source: DataSource, first: date, last: date, lookback_days: int) -> LoadedData:
    """Actuals for first..last, plus every forecast vintage that could cover those days.

    Forecast vintages cover up to about three days ahead, so we read publications from
    `lookback_days` before the first day up to the end of the day after the last one. The
    latest permitted decision time is two days after delivery, and nothing published later
    can be used.
    """
    published_from = day_bounds(first - timedelta(days=lookback_days))[0]
    published_to = day_bounds(last + timedelta(days=1))[1]
    actual_result, forecast_result = await asyncio.gather(
        source.fetch_actuals(first, last),
        source.fetch_forecasts(published_from, published_to),
    )

    actuals, actuals_rejected, not_wind = parse_actuals(actual_result.rows)
    forecasts, forecasts_rejected, off_hour = parse_forecasts(forecast_result.rows)
    forecasts_by_hour = index_forecasts(forecasts)

    sources = [
        SourceInfo(
            dataset="FUELHH",
            role="ACTUAL",
            requested_from=first.isoformat(),
            requested_to=last.isoformat(),
            basis="SETTLEMENT_DATE",
            rows_received=len(actual_result.rows),
            rows_rejected=actuals_rejected,
            rows_filtered=not_wind,
            fetched_at=actual_result.fetched_at,
            cache=actual_result.cache,
        ),
        SourceInfo(
            dataset="WINDFOR",
            role="FORECAST",
            requested_from=format_utc(published_from),
            requested_to=format_utc(published_to),
            basis="PUBLISH_TIME",
            rows_received=len(forecast_result.rows),
            rows_rejected=forecasts_rejected + off_hour,
            rows_filtered=0,
            fetched_at=forecast_result.fetched_at,
            cache=forecast_result.cache,
        ),
    ]

    warnings = []
    for info in sources:
        if info.rows_received == 0:
            warnings.append(
                _source_warning(
                    WarningCode.NO_SOURCE_DATA,
                    f"{info.dataset} returned no rows for this range.",
                    {"dataset": info.dataset},
                )
            )
        if info.rows_rejected:
            warnings.append(
                _source_warning(
                    WarningCode.SOURCE_ROWS_REJECTED,
                    f"{info.rows_rejected} {info.dataset} rows could not be placed on the timeline "
                    "and were ignored.",
                    {"dataset": info.dataset, "count": info.rows_rejected},
                )
            )
    if off_hour:
        warnings.append(
            _source_warning(
                WarningCode.FORECAST_RESOLUTION_IRREGULAR,
                f"{off_hour} WINDFOR rows did not start on the hour and were ignored.",
                {"count": off_hour},
            )
        )

    # If a forecast covering the first day was published on the first day we read, an even
    # earlier publication might have covered it too.
    first_start, first_end = day_bounds(first)
    first_publish_day_end = day_bounds(first - timedelta(days=lookback_days))[1]
    covering_early = [
        f.publish_time
        for hour, hour_forecasts in forecasts_by_hour.items()
        if first_start <= hour < first_end
        for f in hour_forecasts
        if f.publish_time < first_publish_day_end
    ]
    if covering_early:
        warnings.append(
            _source_warning(
                WarningCode.RETRIEVAL_WINDOW_MAY_BE_INSUFFICIENT,
                "Forecasts for this day were found at the very start of the retrieval window; "
                "earlier vintages may exist.",
                {"earliestPublishTime": format_utc(min(covering_early))},
            )
        )

    return LoadedData(
        forecasts_by_hour=forecasts_by_hour,
        actuals_by_start=index_actuals(actuals),
        publish_times={f.publish_time for f in forecasts},
        sources=sources,
        warnings=warnings,
    )


def _source_warning(code: WarningCode, message: str, data: dict[str, object]) -> AnalysisWarning:
    return AnalysisWarning(
        code=code, severity="WARNING", scope="SOURCE", message=message, data=data
    )
