"""An independent, deliberately naive re-implementation used to cross-check golden values.

It works directly on raw Elexon rows and ISO strings and shares no code with `app`, so a bug in the
production pipeline cannot also hide here. It only supports winter days (UTC == UK local time).
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta


def _iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def errors_for_day(
    fuelhh: list[dict[str, object]],
    windfor: list[dict[str, object]],
    delivery_date: date,
    cutoff: datetime,
) -> list[int]:
    actual = {str(r["startTime"]): r["generation"] for r in fuelhh if r["fuelType"] == "WIND"}
    vintages: defaultdict[str, list[tuple[str, object]]] = defaultdict(list)
    for row in windfor:
        vintages[str(row["startTime"])].append((str(row["publishTime"]), row["generation"]))

    cutoff_iso = _iso(cutoff)
    day_start = datetime(delivery_date.year, delivery_date.month, delivery_date.day, tzinfo=UTC)
    errors: list[int] = []
    for half_hour in range(48):
        start = day_start + timedelta(minutes=30 * half_hour)
        hour = _iso(start.replace(minute=0))
        eligible = [v for v in vintages[hour] if v[0] <= cutoff_iso]  # ISO strings sort by time
        if eligible and _iso(start) in actual:
            forecast_mw = max(eligible)[1]
            errors.append(int(forecast_mw) - int(actual[_iso(start)]))  # type: ignore[call-overload]
    return errors


def metrics(errors: list[int]) -> tuple[float, float, float]:
    n = len(errors)
    return (
        sum(abs(e) for e in errors) / n,
        math.sqrt(sum(e * e for e in errors) / n),
        sum(errors) / n,
    )
