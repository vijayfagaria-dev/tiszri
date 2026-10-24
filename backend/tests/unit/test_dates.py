from datetime import UTC, date, datetime, time

import pytest

from app.utils.dates import (
    cutoff_position,
    day_bounds,
    describe_london,
    format_london,
    format_utc,
    london_time,
    resolve_rule,
    settlement_starts,
)

pytestmark = pytest.mark.req("FR-005", "AC-013")


def utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=UTC)


def test_january_day_has_48_settlement_periods() -> None:
    starts = settlement_starts(date(2026, 1, 16))
    assert len(starts) == 48
    assert (starts[0], starts[-1]) == (utc(2026, 1, 16, 0, 0), utc(2026, 1, 16, 23, 30))


def test_spring_forward_day_has_46_periods() -> None:
    starts = settlement_starts(date(2026, 3, 29))
    assert len(starts) == 46
    assert starts[-1] == utc(2026, 3, 29, 22, 30)


def test_autumn_fallback_day_has_50_periods() -> None:
    starts = settlement_starts(date(2026, 10, 25))
    assert len(starts) == 50
    assert starts[0] == utc(2026, 10, 24, 23, 0)


def test_summer_day_starts_at_local_midnight() -> None:
    assert day_bounds(date(2026, 7, 1)) == (utc(2026, 6, 30, 23, 0), utc(2026, 7, 1, 23, 0))


def test_skipped_spring_hour_moves_forward() -> None:
    # 01:30 does not exist on 29 Mar 2026; it is read as 01:30 GMT, which is 02:30 BST.
    assert london_time(date(2026, 3, 29), time(1, 30)) == utc(2026, 3, 29, 1, 30)


def test_repeated_autumn_hour_takes_the_earlier_instant() -> None:
    assert london_time(date(2026, 10, 25), time(1, 30)) == utc(2026, 10, 25, 0, 30)


def test_rules_resolve_in_winter_and_summer() -> None:
    assert resolve_rule(date(2026, 1, 16), -1, time(9, 0)) == utc(2026, 1, 15, 9, 0)
    assert resolve_rule(date(2026, 7, 2), -1, time(9, 0)) == utc(2026, 7, 1, 8, 0)


@pytest.mark.parametrize(
    ("cutoff", "expected"),
    [
        (utc(2026, 1, 16, 0, 0), "BEFORE_DELIVERY"),
        (utc(2026, 1, 16, 0, 0, 1), "INSIDE_DELIVERY"),
        (utc(2026, 1, 17, 0, 0), "AFTER_DELIVERY"),
    ],
)
def test_cutoff_position(cutoff: datetime, expected: str) -> None:
    assert cutoff_position(cutoff, date(2026, 1, 16)) == expected


def test_formats() -> None:
    assert format_utc(utc(2026, 1, 15, 12, 0)) == "2026-01-15T12:00:00Z"
    assert format_london(utc(2026, 7, 1, 8, 0)) == "2026-07-01T09:00:00+01:00"
    assert describe_london(utc(2026, 1, 15, 12, 25)) == "12:25 GMT on 15 Jan"
