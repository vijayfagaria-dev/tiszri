"""Replay one delivery day as it was knowable at a decision time.

For each hour, the forecast used is the one with the latest publish time at or before the cutoff.
Records sharing that publish time count once if their values agree and make the hour ambiguous if
they don't. We never fall back to an older vintage: that would hide that newer information existed.

WINDFOR is hourly and FUELHH half-hourly. Each hourly forecast applies to both settlement periods
of its hour, the same way an hourly day-ahead product delivers constant MW across the hour.
"""

from collections import defaultdict
from datetime import date, datetime

from app.analysis.checks import check_day
from app.analysis.day_warnings import day_warnings
from app.analysis.metrics import compute_metrics
from app.models.analysis import Cutoff, DayAnalysis, ForecastChoice, Interval
from app.models.enums import Flag, Status
from app.models.source import Actual, Forecast
from app.utils.dates import HALF_HOUR, hour_start, settlement_starts

REASONS = {
    Status.AMBIGUOUS_FORECAST: "Conflicting forecasts were published at the same time.",
    Status.AMBIGUOUS_ACTUAL: "Conflicting actual values were reported for this period.",
    Status.INVALID_VALUE: "The forecast or actual value is not a usable number.",
    Status.FULLY_MISSING: "Neither a forecast nor an actual value is available.",
    Status.FORECAST_NOT_YET_PUBLISHED: "No forecast for this hour existed at the decision time.",
    Status.FORECAST_MISSING: "No forecast covering this hour was found in the source data.",
    Status.ACTUAL_MISSING: "No actual generation was reported for this settlement period.",
}


def index_forecasts(forecasts: list[Forecast]) -> dict[datetime, list[Forecast]]:
    by_hour: dict[datetime, list[Forecast]] = defaultdict(list)
    for forecast in forecasts:
        by_hour[forecast.start].append(forecast)
    return by_hour


def index_actuals(actuals: list[Actual]) -> dict[datetime, list[Actual]]:
    by_start: dict[datetime, list[Actual]] = defaultdict(list)
    for actual in actuals:
        by_start[actual.start].append(actual)
    return by_start


def choose_forecast(candidates: list[Forecast], cutoff: datetime) -> ForecastChoice:
    eligible = {f.publish_time for f in candidates if f.publish_time <= cutoff}
    later = {f.publish_time for f in candidates if f.publish_time > cutoff}
    choice = ForecastChoice(
        eligible=len(eligible), later=len(later), earliest_later=min(later, default=None)
    )
    if not eligible:
        return choice

    latest = [f for f in candidates if f.publish_time == max(eligible)]
    values = {f.generation for f in latest}
    if len(values) > 1:
        choice.ambiguous = True
        choice.conflicting = sorted(v for v in values if v is not None)
    else:
        choice.forecast = latest[0]
        choice.duplicated = len(latest) > 1
    return choice


def classify(choice: ForecastChoice, actuals: list[Actual]) -> Status:
    forecast = choice.forecast
    actual = actuals[0] if actuals else None
    if choice.ambiguous:
        return Status.AMBIGUOUS_FORECAST
    if len({a.generation for a in actuals}) > 1:
        return Status.AMBIGUOUS_ACTUAL
    if (forecast and forecast.generation is None) or (actual and actual.generation is None):
        return Status.INVALID_VALUE
    if forecast is None and actual is None:
        return Status.FULLY_MISSING
    if forecast is None:
        return Status.FORECAST_NOT_YET_PUBLISHED if choice.later else Status.FORECAST_MISSING
    if actual is None:
        return Status.ACTUAL_MISSING
    return Status.MATCHED


def analyze_day(
    delivery_date: date,
    cutoff: Cutoff,
    forecasts_by_hour: dict[datetime, list[Forecast]],
    actuals_by_start: dict[datetime, list[Actual]],
) -> DayAnalysis:
    starts = settlement_starts(delivery_date)
    hours = sorted({hour_start(start) for start in starts})
    choices = {hour: choose_forecast(forecasts_by_hour.get(hour, []), cutoff.utc) for hour in hours}

    intervals = []
    for number, start in enumerate(starts, start=1):
        choice = choices[hour_start(start)]
        actuals = actuals_by_start.get(start, [])
        intervals.append(_interval(number, start, choice, actuals, delivery_date))

    status_counts = dict.fromkeys(Status, 0)
    for interval in intervals:
        status_counts[interval.status] += 1

    covering = {f.publish_time for hour in hours for f in forecasts_by_hour.get(hour, [])}
    later = sorted(p for p in covering if p > cutoff.utc)
    errors = [i.error for i in intervals if i.error is not None]
    day = DayAnalysis(
        delivery_date=delivery_date,
        cutoff=cutoff,
        intervals=intervals,
        status_counts=status_counts,
        metrics=compute_metrics(errors),
        warnings=[],
        largest_over=_largest_error(intervals, sign=1),
        largest_under=_largest_error(intervals, sign=-1),
        versions_used=sorted({c.forecast.publish_time for c in choices.values() if c.forecast}),
        versions_covering=len(covering),
        versions_eligible=len(covering) - len(later),
        earliest_covering=min(covering, default=None),
        newer_after_cutoff=later[0] if later else None,
    )
    day.warnings = day_warnings(day)
    check_day(day)
    return day


def _interval(
    number: int, start: datetime, choice: ForecastChoice, actuals: list[Actual], delivery_date: date
) -> Interval:
    status = classify(choice, actuals)
    forecast = choice.forecast
    actual = actuals[0] if actuals and status != Status.AMBIGUOUS_ACTUAL else None

    error = None
    if status == Status.MATCHED and forecast and actual:
        error = (forecast.generation or 0) - (actual.generation or 0)  # both set when MATCHED

    flags = []
    if forecast and forecast.publish_time > start:
        flags.append(Flag.ISSUED_AFTER_DELIVERY_START)
    if choice.duplicated:
        flags.append(Flag.DUPLICATE_EQUIVALENT_FORECAST)
    if actual and len(actuals) > 1:
        flags.append(Flag.DUPLICATE_EQUIVALENT_ACTUAL)
    if actual and (
        (actual.settlement_date and actual.settlement_date != delivery_date)
        or (actual.settlement_period and actual.settlement_period != number)
    ):
        flags.append(Flag.ACTUAL_TIMESTAMP_INCONSISTENT)

    conflicting = []
    if status == Status.AMBIGUOUS_ACTUAL:
        conflicting = sorted({a.generation for a in actuals if a.generation is not None})

    return Interval(
        number=number,
        start=start,
        end=start + HALF_HOUR,
        status=status,
        reason=REASONS.get(status),
        choice=choice,
        actual=actual,
        actual_conflicting=conflicting,
        error=error,
        flags=flags,
    )


def _largest_error(intervals: list[Interval], sign: int) -> datetime | None:
    """Start of the largest error with the given sign; the earliest one wins a tie."""
    best = None
    best_size = 0
    for interval in intervals:
        size = (interval.error or 0) * sign
        if size > best_size:
            best, best_size = interval.start, size
    return best
