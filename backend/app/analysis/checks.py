"""Guarantees every day analysis must meet. A failure raises instead of returning bad data."""

import math
from itertools import pairwise

from app.core.errors import InvariantError
from app.models.analysis import DayAnalysis
from app.models.enums import Status
from app.models.source import FORECAST_PERIOD


def check_day(day: DayAnalysis) -> None:
    intervals = day.intervals
    _require(sum(day.status_counts.values()) == len(intervals), "status counts do not add up")
    _require(day.metrics.n == day.matched, "metrics sample differs from the matched count")
    for previous, current in pairwise(intervals):
        _require(previous.end == current.start, "intervals are not contiguous")

    for interval in intervals:
        forecast = interval.choice.forecast
        if forecast is not None:
            _require(
                forecast.publish_time <= day.cutoff.utc,
                "used a forecast published after the cutoff",
            )
            _require(
                forecast.start <= interval.start < forecast.start + FORECAST_PERIOD,
                "forecast applied outside its own hour",
            )
        _require(
            (interval.error is not None) == (interval.status == Status.MATCHED),
            "error present for an unmatched period, or missing for a matched one",
        )

    m = day.metrics
    if m.n == 0:
        _require(m.mae is None and m.rmse is None and m.bias is None, "metrics must be empty")
    elif m.mae is None or m.rmse is None or m.bias is None:
        raise InvariantError("metrics missing although periods matched")
    else:
        _require(all(math.isfinite(v) for v in (m.mae, m.rmse, m.bias)), "non-finite metric")
        _require(m.rmse + 1e-9 >= m.mae >= abs(m.bias) - 1e-9, "expected rmse >= mae >= |bias|")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvariantError(message)
