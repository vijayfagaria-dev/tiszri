"""Golden scenarios on recorded January 2026 data, cross-checked against an independent oracle."""

from datetime import date, time, timedelta
from functools import cache

import pytest

from app.analysis.replay import analyze_day, index_actuals, index_forecasts
from app.analysis.summary import summarize
from app.clients.parsing import parse_actuals, parse_forecasts
from app.models.analysis import CutoffRule, DayAnalysis, Summary
from app.models.enums import Flag, Status, WarningCode
from tests import oracle
from tests.support import recorded, rule_cutoff, ts

pytestmark = pytest.mark.req("AC-003", "AC-004", "AC-005", "AC-007", "AC-008", "AC-010")


@cache
def sources() -> tuple[dict, dict]:
    actuals, rejected_actuals, _ = parse_actuals(recorded("fuelhh_wind.json.gz"))
    forecasts, rejected_forecasts, off_hour = parse_forecasts(recorded("windfor.json.gz"))
    assert (rejected_actuals, rejected_forecasts, off_hour) == (0, 0, 0)
    return index_forecasts(forecasts), index_actuals(actuals)


def replay(delivery: date, day_offset: int, at: str) -> DayAnalysis:
    forecasts_by_hour, actuals_by_start = sources()
    return analyze_day(
        delivery, rule_cutoff(delivery, day_offset, at), forecasts_by_hour, actuals_by_start
    )


def summary(first: date, last: date, day_offset: int, at: str) -> Summary:
    days = [
        replay(first + timedelta(days=n), day_offset, at) for n in range((last - first).days + 1)
    ]
    forecasts_by_hour, _ = sources()
    publish_times = {f.publish_time for hour in forecasts_by_hour.values() for f in hour}
    return summarize(days, CutoffRule(day_offset, time.fromisoformat(at)), publish_times)


def test_late_forecast_falls_back_to_the_0930_vintage() -> None:
    day = replay(date(2026, 1, 16), -1, "12:00")
    assert day.result_state == "COMPLETE"
    assert (day.metrics.mae, day.metrics.rmse, day.metrics.bias) == pytest.approx(
        (882.583, 1099.327, 396.625), abs=5e-4
    )
    assert (day.metrics.over, day.metrics.under) == (27, 21)
    assert day.versions_used == [ts("2026-01-15T09:30:00Z")]
    assert day.newer_after_cutoff == ts("2026-01-15T12:25:00Z")
    assert day.earliest_covering == ts("2026-01-14T02:30:00Z")
    assert (day.versions_covering, day.versions_eligible) == (32, 12)

    sp44 = day.intervals[43]
    assert sp44.start == ts("2026-01-16T21:30:00Z")
    assert sp44.choice.forecast is not None
    assert sp44.actual is not None
    assert (sp44.choice.forecast.generation, sp44.actual.generation, sp44.error) == (
        10850,
        8244,
        2606,
    )
    assert (sp44.choice.eligible, sp44.choice.later) == (12, 20)


def test_default_decision_time_uses_the_0730_vintage() -> None:
    day = replay(date(2026, 1, 16), -1, "09:00")
    assert day.metrics.mae == pytest.approx(800.542, abs=5e-4)
    assert day.metrics.bias == pytest.approx(351.958, abs=5e-4)
    assert day.versions_used == [ts("2026-01-15T07:30:00Z")]


@pytest.mark.parametrize(
    ("delivery", "mae", "bias", "over", "under"),
    [
        (date(2026, 1, 28), 5374.792, 5374.792, 48, 0),
        (date(2026, 1, 19), 742.854, -730.062, 1, 47),
        (date(2026, 1, 5), 1335.3125, -55.854, 24, 24),
    ],
    ids=["worst-day", "best-day", "bias-hides-error"],
)
def test_reference_days(delivery: date, mae: float, bias: float, over: int, under: int) -> None:
    day = replay(delivery, -1, "09:00")
    assert (day.metrics.mae, day.metrics.bias) == pytest.approx((mae, bias), abs=5e-4)
    assert (day.metrics.over, day.metrics.under) == (over, under)


@pytest.mark.req("FR-025")
def test_two_days_ahead_leaves_the_evening_unforecast() -> None:
    day = replay(date(2026, 1, 15), -2, "09:00")
    assert (day.result_state, day.matched) == ("PARTIAL", 44)
    assert {i.status for i in day.intervals[44:]} == {Status.FORECAST_NOT_YET_PUBLISHED}
    sp45 = day.intervals[44]
    assert (sp45.choice.eligible, sp45.choice.later) == (0, 24)
    assert sp45.choice.earliest_later == ts("2026-01-14T02:30:00Z")
    assert WarningCode.PARTIAL_COVERAGE in {w.code for w in day.warnings}


@pytest.mark.req("FR-026")
def test_three_days_ahead_has_nothing_to_compare() -> None:
    day = replay(date(2026, 1, 15), -3, "09:00")
    assert day.result_state == "EMPTY"
    assert (day.metrics.mae, day.metrics.rmse, day.metrics.bias) == (None, None, None)
    assert day.earliest_covering == ts("2026-01-13T02:30:00Z")


def test_decision_after_delivery_is_marked_as_hindsight() -> None:
    day = replay(date(2026, 1, 16), 1, "00:00")
    assert day.cutoff.position == "AFTER_DELIVERY"
    assert {WarningCode.HINDSIGHT_CUTOFF, WarningCode.ISSUED_AFTER_DELIVERY_START} <= {
        w.code for w in day.warnings
    }
    late = [i for i in day.intervals if Flag.ISSUED_AFTER_DELIVERY_START in i.flags]
    assert late
    assert all(i.start < ts("2026-01-16T22:30:00Z") for i in late)


def test_january_decisions_at_0900() -> None:
    result = summary(date(2026, 1, 2), date(2026, 2, 1), -1, "09:00")
    m = result.metrics
    assert (result.matched, result.expected) == (1488, 1488)
    assert (m.mae, m.rmse, m.bias) == pytest.approx((2041.958, 2509.063, 1747.887), abs=5e-4)
    assert (m.over, m.under) == (1261, 227)
    assert result.abs_percentiles == {"p50": 1686, "p90": 4145, "p95": 5316}
    assert result.signed_percentiles == {"p10": -549, "p90": 4145}
    assert sum(count for _, count in result.histogram) == 1488

    featured = {f.kind: f for f in result.featured}
    assert featured["WORST_DAY"].delivery_date == date(2026, 1, 28)
    assert featured["BEST_DAY"].delivery_date == date(2026, 1, 19)
    assert featured["BIAS_HIDES_ERROR"].delivery_date == date(2026, 1, 5)
    late = featured["OFF_SCHEDULE_VINTAGE"]
    assert late.delivery_date == date(2026, 1, 16)
    assert late.rule == CutoffRule(-1, time(12, 0))
    assert late.data == {"publishTime": "2026-01-15T12:25:00Z", "missingSlot": "11:30"}

    assert result.on_the_hour.n == 744
    assert result.on_the_hour.mae == pytest.approx(2022.470, abs=5e-4)


def test_january_decisions_at_noon() -> None:
    result = summary(date(2026, 1, 2), date(2026, 2, 1), -1, "12:00")
    assert (result.metrics.mae, result.metrics.bias) == pytest.approx(
        (1903.809, 1687.223), abs=5e-4
    )
    assert result.abs_percentiles is not None
    assert result.abs_percentiles["p90"] == 3804


@pytest.mark.parametrize(("day_offset", "at"), [(-1, "09:00"), (-1, "12:00"), (-2, "09:00")])
def test_every_day_agrees_with_the_independent_oracle(day_offset: int, at: str) -> None:
    fuelhh, windfor = recorded("fuelhh_wind.json.gz"), recorded("windfor.json.gz")
    for n in range(32):
        delivery = date(2026, 1, 1) + timedelta(days=n)
        day = replay(delivery, day_offset, at)
        expected = oracle.errors_for_day(fuelhh, windfor, delivery, day.cutoff.utc)
        assert [i.error for i in day.intervals if i.error is not None] == expected, delivery
        if expected:
            assert (day.metrics.mae, day.metrics.rmse, day.metrics.bias) == pytest.approx(
                oracle.metrics(expected), abs=1e-9
            )
