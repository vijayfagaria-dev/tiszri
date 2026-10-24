from datetime import date

import pytest

from app.analysis.replay import (
    analyze_day,
    choose_forecast,
    classify,
    index_actuals,
    index_forecasts,
)
from app.models.analysis import ForecastChoice
from app.models.enums import Flag, Status, WarningCode
from tests.support import actual, explicit_cutoff, forecast, ts

HOUR = "2026-01-16T21:00:00Z"
CUTOFF = ts("2026-01-15T12:00:00Z")
DAY = date(2026, 1, 16)


class TestChooseForecast:
    pytestmark = pytest.mark.req("FR-009", "FR-010", "FR-011", "AC-003", "AC-004")

    def test_latest_publish_time_at_or_before_cutoff_wins(self) -> None:
        candidates = [
            forecast(HOUR, "2026-01-15T04:30:00Z", 900),
            forecast(HOUR, "2026-01-15T09:30:00Z", 1100),
            forecast(HOUR, "2026-01-15T07:30:00Z", 1000),
        ]
        choice = choose_forecast(candidates, CUTOFF)
        assert choice.forecast is not None
        assert choice.forecast.generation == 1100
        assert (choice.eligible, choice.later) == (3, 0)

    def test_publish_time_equal_to_cutoff_is_eligible(self) -> None:
        choice = choose_forecast([forecast(HOUR, "2026-01-15T12:00:00Z", 1234)], CUTOFF)
        assert choice.forecast is not None
        assert choice.forecast.generation == 1234

    def test_later_publications_are_ignored(self) -> None:
        candidates = [
            forecast(HOUR, "2026-01-15T09:30:00Z", 1000),
            forecast(HOUR, "2026-01-15T12:00:01Z", 9999),
        ]
        choice = choose_forecast(candidates, CUTOFF)
        assert choice.forecast is not None
        assert choice.forecast.generation == 1000
        assert (choice.eligible, choice.later) == (1, 1)
        assert choice.earliest_later == ts("2026-01-15T12:00:01Z")

    def test_nothing_published_yet(self) -> None:
        choice = choose_forecast([forecast(HOUR, "2026-01-15T15:30:00Z", 1000)], CUTOFF)
        assert choice.forecast is None
        assert choice.later == 1

    @pytest.mark.req("FR-014")
    def test_identical_duplicates_count_once(self) -> None:
        candidates = [forecast(HOUR, "2026-01-15T09:30:00Z", 1000)] * 2
        choice = choose_forecast(candidates, CUTOFF)
        assert choice.forecast is not None
        assert choice.duplicated
        assert choice.eligible == 1

    @pytest.mark.req("FR-014")
    def test_conflicting_duplicates_are_ambiguous_with_no_fallback(self) -> None:
        candidates = [
            forecast(HOUR, "2026-01-15T07:30:00Z", 500),
            forecast(HOUR, "2026-01-15T09:30:00Z", 1100),
            forecast(HOUR, "2026-01-15T09:30:00Z", 1000),
        ]
        choice = choose_forecast(candidates, CUTOFF)
        assert choice.ambiguous
        assert choice.forecast is None
        assert choice.conflicting == [1000, 1100]

    @pytest.mark.req("FR-023")
    def test_unusable_latest_value_is_not_replaced_by_an_older_one(self) -> None:
        candidates = [
            forecast(HOUR, "2026-01-15T07:30:00Z", 500),
            forecast(HOUR, "2026-01-15T09:30:00Z", None),
        ]
        choice = choose_forecast(candidates, CUTOFF)
        assert choice.forecast is not None
        assert choice.forecast.publish_time == ts("2026-01-15T09:30:00Z")
        assert choice.forecast.generation is None


GOOD = forecast(HOUR, "2026-01-15T09:30:00Z", 1000)
BAD = forecast(HOUR, "2026-01-15T09:30:00Z", None)
PRESENT = [actual("2026-01-16T21:30:00Z", 900)]


@pytest.mark.req("FR-023", "AC-010")
@pytest.mark.parametrize(
    ("choice", "actuals", "expected"),
    [
        (ForecastChoice(ambiguous=True), [], Status.AMBIGUOUS_FORECAST),
        (
            ForecastChoice(forecast=GOOD),
            [*PRESENT, actual("2026-01-16T21:30:00Z", 1)],
            Status.AMBIGUOUS_ACTUAL,
        ),
        (ForecastChoice(forecast=BAD), [], Status.INVALID_VALUE),
        (
            ForecastChoice(forecast=GOOD),
            [actual("2026-01-16T21:30:00Z", None)],
            Status.INVALID_VALUE,
        ),
        (ForecastChoice(), [], Status.FULLY_MISSING),
        (ForecastChoice(later=2), [], Status.FULLY_MISSING),
        (ForecastChoice(later=2), PRESENT, Status.FORECAST_NOT_YET_PUBLISHED),
        (ForecastChoice(), PRESENT, Status.FORECAST_MISSING),
        (ForecastChoice(forecast=GOOD), [], Status.ACTUAL_MISSING),
        (ForecastChoice(forecast=GOOD), PRESENT, Status.MATCHED),
    ],
)
def test_status_precedence(choice: ForecastChoice, actuals: list, expected: Status) -> None:
    assert classify(choice, actuals) == expected


def whole_day(
    forecast_mw: int = 1100, actual_mw: int = 1000, published: str = "2026-01-15T09:30:00Z"
):
    forecasts = [forecast(f"2026-01-16T{h:02d}:00:00Z", published, forecast_mw) for h in range(24)]
    actuals = [
        actual(f"2026-01-16T{h:02d}:{m:02d}:00Z", actual_mw) for h in range(24) for m in (0, 30)
    ]
    return forecasts, actuals


def replay(forecasts: list, actuals: list, cutoff: str = "2026-01-15T12:00:00Z", day: date = DAY):
    return analyze_day(
        day, explicit_cutoff(day, cutoff), index_forecasts(forecasts), index_actuals(actuals)
    )


@pytest.mark.req("FR-012", "AC-005")
def test_hourly_forecast_covers_both_half_hours() -> None:
    result = replay(*whole_day())
    assert result.result_state == "COMPLETE"
    assert len(result.intervals) == 48
    first, second = result.intervals[42], result.intervals[43]  # 21:00 and 21:30
    assert first.choice.forecast is second.choice.forecast
    assert all(i.error == 100 for i in result.intervals)
    assert result.metrics.bias == 100.0


@pytest.mark.req("FR-023", "FR-024", "FR-025")
def test_missing_hour_excludes_both_half_hours() -> None:
    forecasts, actuals = whole_day()
    result = replay([f for f in forecasts if f.start.hour != 5], actuals)
    assert [i.status for i in result.intervals[10:12]] == [Status.FORECAST_MISSING] * 2
    assert (result.matched, result.result_state, result.metrics.n) == (46, "PARTIAL", 46)
    partial = next(w for w in result.warnings if w.code == WarningCode.PARTIAL_COVERAGE)
    assert partial.affected_count == 2


@pytest.mark.req("FR-026")
def test_day_without_forecasts_has_no_metrics() -> None:
    _, actuals = whole_day()
    result = replay([], actuals)
    assert result.result_state == "EMPTY"
    assert result.metrics.mae is None
    assert [w.code for w in result.warnings] == [WarningCode.NO_MATCHED_INTERVALS]


def test_forecast_published_after_period_start_is_flagged() -> None:
    forecasts, actuals = whole_day(published="2026-01-16T10:30:00Z")
    result = replay(forecasts, actuals, cutoff="2026-01-16T12:00:00Z")
    flagged = [i.number for i in result.intervals if Flag.ISSUED_AFTER_DELIVERY_START in i.flags]
    assert flagged == list(range(1, 22))  # every half-hour starting before 10:30
    codes = {w.code for w in result.warnings}
    assert {
        WarningCode.CUTOFF_INSIDE_DELIVERY_DAY,
        WarningCode.ISSUED_AFTER_DELIVERY_START,
    } <= codes


def test_inconsistent_settlement_metadata_is_flagged_but_matched() -> None:
    forecasts, actuals = whole_day()
    actuals[0] = actual("2026-01-16T00:00:00Z", 1000, settlement_date=DAY, settlement_period=2)
    result = replay(forecasts, actuals)
    assert Flag.ACTUAL_TIMESTAMP_INCONSISTENT in result.intervals[0].flags
    assert result.intervals[0].status == Status.MATCHED


def test_largest_errors_prefer_the_earliest_on_ties() -> None:
    forecasts, actuals = whole_day()
    actuals[4] = actual("2026-01-16T02:00:00Z", 400)  # +700
    actuals[6] = actual("2026-01-16T03:00:00Z", 400)  # +700, later
    actuals[8] = actual("2026-01-16T04:00:00Z", 2000)  # -900
    result = replay(forecasts, actuals)
    assert result.largest_over == ts("2026-01-16T02:00:00Z")
    assert result.largest_under == ts("2026-01-16T04:00:00Z")


def test_clock_change_day_has_46_periods() -> None:
    spring = date(2026, 3, 29)
    forecasts = [
        forecast(f"2026-03-29T{h:02d}:00:00Z", "2026-03-28T09:30:00Z", 500) for h in range(23)
    ]
    actuals = [actual(f"2026-03-29T{h:02d}:{m:02d}:00Z", 400) for h in range(23) for m in (0, 30)]
    result = replay(forecasts, actuals, cutoff="2026-03-28T12:00:00Z", day=spring)
    assert len(result.intervals) == 46
    assert result.result_state == "COMPLETE"
