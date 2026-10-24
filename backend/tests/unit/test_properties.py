"""Properties of forecast selection and metrics that must hold for any input."""

import random
from datetime import UTC, date, datetime, timedelta, timezone

from hypothesis import given
from hypothesis import strategies as st

from app.analysis.metrics import compute_metrics
from app.analysis.replay import analyze_day, choose_forecast, index_actuals, index_forecasts
from app.clients.parsing import parse_time
from app.models.source import Actual, Forecast
from tests.support import explicit_cutoff

BASE = datetime(2026, 1, 13, tzinfo=UTC)
HOUR = datetime(2026, 1, 16, 21, tzinfo=UTC)

minutes = st.integers(min_value=0, max_value=4 * 24 * 60)
instants = minutes.map(lambda m: BASE + timedelta(minutes=m))
generations = st.one_of(st.none(), st.integers(min_value=0, max_value=20_000))
vintages = st.lists(st.tuples(instants, generations), max_size=12).map(
    lambda items: [Forecast(HOUR, published, value) for published, value in items]
)


@given(vintages, instants)
def test_never_uses_a_forecast_published_after_the_cutoff(
    candidates: list[Forecast], cutoff: datetime
) -> None:
    choice = choose_forecast(candidates, cutoff)
    if choice.forecast:
        assert choice.forecast.publish_time <= cutoff


@given(vintages, instants)
def test_no_eligible_forecast_is_newer_than_the_chosen_one(
    candidates: list[Forecast], cutoff: datetime
) -> None:
    choice = choose_forecast(candidates, cutoff)
    eligible = [f.publish_time for f in candidates if f.publish_time <= cutoff]
    if choice.forecast:
        assert choice.forecast.publish_time == max(eligible)
    else:
        assert not eligible or choice.ambiguous


@given(vintages, instants, instants)
def test_a_later_cutoff_never_picks_an_older_forecast(
    candidates: list[Forecast], a: datetime, b: datetime
) -> None:
    earlier, later = sorted((a, b))
    first, second = choose_forecast(candidates, earlier), choose_forecast(candidates, later)
    if first.forecast and second.forecast:
        assert second.forecast.publish_time >= first.forecast.publish_time


@given(vintages, instants, st.randoms())
def test_input_order_does_not_change_the_choice(
    candidates: list[Forecast], cutoff: datetime, rng: random.Random
) -> None:
    shuffled = candidates.copy()
    rng.shuffle(shuffled)
    a, b = choose_forecast(candidates, cutoff), choose_forecast(shuffled, cutoff)
    assert (a.ambiguous, a.eligible, a.later, a.conflicting) == (
        b.ambiguous,
        b.eligible,
        b.later,
        b.conflicting,
    )
    assert (a.forecast is None) == (b.forecast is None)
    if a.forecast and b.forecast:
        assert (a.forecast.publish_time, a.forecast.generation) == (
            b.forecast.publish_time,
            b.forecast.generation,
        )


@given(st.lists(st.integers(min_value=-20_000, max_value=20_000), min_size=1))
def test_rmse_is_at_least_mae_which_is_at_least_absolute_bias(errors: list[int]) -> None:
    m = compute_metrics(errors)
    assert m.rmse is not None
    assert m.mae is not None
    assert m.bias is not None
    assert m.rmse + 1e-9 >= m.mae >= abs(m.bias) - 1e-9
    assert m.over + m.under + m.exact == m.n


@given(instants, st.integers(min_value=-12, max_value=14))
def test_the_same_instant_parses_identically_in_any_offset(instant: datetime, hours: int) -> None:
    written = instant.astimezone(timezone(timedelta(hours=hours))).isoformat()
    assert parse_time(written) == instant


day_hours = st.integers(min_value=0, max_value=23)
day_forecasts = st.lists(st.tuples(day_hours, instants, generations), max_size=60).map(
    lambda items: [Forecast(datetime(2026, 1, 16, h, tzinfo=UTC), p, g) for h, p, g in items]
)
day_actuals = st.lists(st.tuples(st.integers(0, 47), generations), max_size=60).map(
    lambda items: [
        Actual(datetime(2026, 1, 16, tzinfo=UTC) + timedelta(minutes=30 * n), g) for n, g in items
    ]
)


@given(day_forecasts, day_actuals, instants)
def test_any_day_satisfies_the_contract_guarantees(
    forecasts: list[Forecast], actuals: list[Actual], cutoff: datetime
) -> None:
    # analyze_day raises InvariantError if any guarantee is broken.
    day = analyze_day(
        date(2026, 1, 16),
        explicit_cutoff(date(2026, 1, 16), cutoff.isoformat()),
        index_forecasts(forecasts),
        index_actuals(actuals),
    )
    assert day.matched + sum(n for s, n in day.status_counts.items() if s != "MATCHED") == 48
    for interval in day.intervals:
        if interval.error is not None:
            assert interval.choice.forecast is not None
            assert interval.actual is not None
