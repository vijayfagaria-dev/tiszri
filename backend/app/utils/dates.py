"""Time helpers. All comparisons happen on timezone-aware UTC instants.

A GB settlement day runs from local midnight to local midnight in Europe/London, so it has 48
half-hour periods, or 46/50 on clock-change days.
"""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")
HALF_HOUR = timedelta(minutes=30)


def london_time(day: date, at: time) -> datetime:
    """UTC instant of a UK wall-clock time.

    During the autumn change an hour repeats; the earlier occurrence wins. During the spring
    change an hour is skipped; a time inside it is moved forward by an hour.
    """
    return datetime.combine(day, at, tzinfo=LONDON).astimezone(UTC)


def day_bounds(day: date) -> tuple[datetime, datetime]:
    return london_time(day, time(0)), london_time(day + timedelta(days=1), time(0))


def settlement_starts(day: date) -> list[datetime]:
    start, end = day_bounds(day)
    starts = []
    while start < end:
        starts.append(start)
        start += HALF_HOUR
    return starts


def resolve_rule(delivery_date: date, day_offset: int, local_time: time) -> datetime:
    """UTC instant of `local_time` UK time, `day_offset` days from the delivery date."""
    return london_time(delivery_date + timedelta(days=day_offset), local_time)


def cutoff_position(cutoff: datetime, delivery_date: date) -> str:
    start, end = day_bounds(delivery_date)
    if cutoff <= start:
        return "BEFORE_DELIVERY"
    if cutoff >= end:
        return "AFTER_DELIVERY"
    return "INSIDE_DELIVERY"


def hour_start(moment: datetime) -> datetime:
    return moment.replace(minute=0, second=0, microsecond=0)


def minutes_between(later: datetime, earlier: datetime) -> int:
    return int((later - earlier).total_seconds()) // 60


def format_utc(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def format_london(moment: datetime) -> str:
    return moment.astimezone(LONDON).isoformat(timespec="seconds")


def describe_london(moment: datetime) -> str:
    """For messages, e.g. '12:25 GMT on 15 Jan'."""
    local = moment.astimezone(LONDON)
    return f"{local:%H:%M} {local.tzname()} on {local.day} {local:%b}"
