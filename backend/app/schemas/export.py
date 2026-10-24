"""CSV export of a day replay: one row per settlement period, preceded by '#' context lines."""

import csv
import io

from app.schemas.common import CONTRACT_VERSION, error_direction
from app.services.replay_service import DayReport
from app.utils.dates import format_london, format_utc, minutes_between

COLUMNS = [
    "settlementPeriod",
    "startTime",
    "endTime",
    "status",
    "forecastMW",
    "forecastPublishTime",
    "forecastPeriodStart",
    "leadMinutes",
    "actualMW",
    "errorMW",
    "absErrorMW",
    "direction",
    "exclusionReason",
]


def day_csv(report: DayReport) -> str:
    day = report.day
    cutoff = day.cutoff.utc
    out = io.StringIO()
    for line in (
        f"deliveryDate={day.delivery_date.isoformat()}",
        f"decisionCutoffUtc={format_utc(cutoff)}",
        f"decisionCutoffLondon={format_london(cutoff)}",
        "source=Elexon FUELHH (fuelType WIND) and WINDFOR",
        "units=MW; error = forecast - actual (positive = forecast too high)",
        f"contractVersion={CONTRACT_VERSION}",
    ):
        out.write(f"# {line}\n")

    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(COLUMNS)
    for interval in day.intervals:
        forecast = interval.choice.forecast
        actual = interval.actual
        error = interval.error
        writer.writerow(
            [
                interval.number,
                format_utc(interval.start),
                format_utc(interval.end),
                interval.status,
                _blank(forecast.generation if forecast else None),
                format_utc(forecast.publish_time) if forecast else "",
                format_utc(forecast.start) if forecast else "",
                minutes_between(interval.start, forecast.publish_time) if forecast else "",
                _blank(actual.generation if actual else None),
                _blank(error),
                _blank(abs(error) if error is not None else None),
                error_direction(error) if error is not None else "",
                interval.reason or "",
            ]
        )
    return out.getvalue()


def _blank(value: int | None) -> int | str:
    return "" if value is None else value
