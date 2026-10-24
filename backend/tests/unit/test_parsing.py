import math
from datetime import UTC, date, datetime

import pytest

from app.clients.parsing import parse_actuals, parse_forecasts, parse_generation


def actual_row(**changes: object) -> dict[str, object]:
    row: dict[str, object] = {
        "dataset": "FUELHH",
        "publishTime": "2026-01-16T22:00:00Z",
        "startTime": "2026-01-16T21:30:00Z",
        "settlementDate": "2026-01-16",
        "settlementPeriod": 44,
        "fuelType": "WIND",
        "generation": 8244,
    }
    return row | changes


def forecast_row(**changes: object) -> dict[str, object]:
    row: dict[str, object] = {
        "dataset": "WINDFOR",
        "publishTime": "2026-01-15T09:30:00Z",
        "startTime": "2026-01-16T21:00:00Z",
        "generation": 10850,
    }
    return row | changes


@pytest.mark.req("FR-023")
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (8244, 8244),
        (8244.0, 8244),
        (None, None),
        (True, None),
        ("8244", None),
        (8244.5, None),
        (math.nan, None),
        (math.inf, None),
    ],
)
def test_parse_generation(value: object, expected: int | None) -> None:
    assert parse_generation(value) == expected


@pytest.mark.req("FR-002", "AC-006")
def test_only_wind_actuals_are_kept() -> None:
    actuals, rejected, not_wind = parse_actuals(
        [actual_row(), actual_row(fuelType="CCGT"), actual_row(fuelType="NUCLEAR")]
    )
    assert len(actuals) == 1
    assert (rejected, not_wind) == (0, 2)


@pytest.mark.req("FR-005")
def test_actual_fields() -> None:
    (actual,), _, _ = parse_actuals([actual_row()])
    assert actual.start == datetime(2026, 1, 16, 21, 30, tzinfo=UTC)
    assert actual.generation == 8244
    assert actual.settlement_date == date(2026, 1, 16)
    assert actual.settlement_period == 44


def test_offsets_are_normalised_to_utc() -> None:
    (actual,), _, _ = parse_actuals([actual_row(startTime="2026-07-01T10:30:00+01:00")])
    assert actual.start == datetime(2026, 7, 1, 9, 30, tzinfo=UTC)


@pytest.mark.parametrize(
    "row",
    [
        "not a row",
        actual_row(dataset="WINDFOR"),
        actual_row(startTime=None),
        actual_row(startTime="yesterday"),
        actual_row(startTime="2026-01-16T21:30:00"),  # no timezone
    ],
)
def test_unplaceable_actual_rows_are_rejected(row: object) -> None:
    actuals, rejected, _ = parse_actuals([row])  # type: ignore[list-item]
    assert (actuals, rejected) == ([], 1)


def test_unusable_actual_value_is_kept_as_none() -> None:
    (actual,), _, _ = parse_actuals([actual_row(generation=None)])
    assert actual.generation is None


def test_forecast_fields() -> None:
    (forecast,), rejected, off_hour = parse_forecasts([forecast_row()])
    assert forecast.start == datetime(2026, 1, 16, 21, 0, tzinfo=UTC)
    assert forecast.publish_time == datetime(2026, 1, 15, 9, 30, tzinfo=UTC)
    assert forecast.generation == 10850
    assert (rejected, off_hour) == (0, 0)


def test_forecast_not_on_the_hour_is_counted_separately() -> None:
    forecasts, rejected, off_hour = parse_forecasts(
        [forecast_row(startTime="2026-01-16T21:30:00Z")]
    )
    assert (forecasts, rejected, off_hour) == ([], 0, 1)


@pytest.mark.parametrize(
    "row",
    [forecast_row(dataset="FUELHH"), forecast_row(publishTime=None), forecast_row(startTime=12)],
)
def test_unplaceable_forecast_rows_are_rejected(row: dict[str, object]) -> None:
    forecasts, rejected, _ = parse_forecasts([row])
    assert (forecasts, rejected) == ([], 1)
