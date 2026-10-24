from datetime import date

from app.analysis.replay import index_forecasts
from app.analysis.versions import forecast_versions
from tests.support import forecast, ts


def test_versions_are_laid_out_by_hour_oldest_first() -> None:
    forecasts = [
        forecast("2026-01-16T00:00:00Z", "2026-01-15T09:30:00Z", 100),
        forecast("2026-01-16T23:00:00Z", "2026-01-15T09:30:00Z", 123),
        forecast("2026-01-16T00:00:00Z", "2026-01-14T09:30:00Z", 90),  # older, covers 00:00 only
    ]
    hours, versions = forecast_versions(date(2026, 1, 16), index_forecasts(forecasts))

    assert len(hours) == 24
    assert hours[0] == ts("2026-01-16T00:00:00Z")
    assert [v.publish_time for v in versions] == [
        ts("2026-01-14T09:30:00Z"),
        ts("2026-01-15T09:30:00Z"),
    ]
    older, newer = versions
    assert older.values[0] == 90
    assert older.values[1:] == [None] * 23
    assert (newer.values[0], newer.values[23]) == (100, 123)


def test_unusable_or_conflicting_values_are_null() -> None:
    forecasts = [
        forecast("2026-01-16T01:00:00Z", "2026-01-15T09:30:00Z", None),
        forecast("2026-01-16T02:00:00Z", "2026-01-15T09:30:00Z", 10),
        forecast("2026-01-16T02:00:00Z", "2026-01-15T09:30:00Z", 20),
        forecast("2026-01-16T03:00:00Z", "2026-01-15T09:30:00Z", 30),
        forecast("2026-01-16T03:00:00Z", "2026-01-15T09:30:00Z", 30),  # identical duplicate
    ]
    _, (version,) = forecast_versions(date(2026, 1, 16), index_forecasts(forecasts))
    assert version.values[1:4] == [None, None, 30]


def test_clock_change_day_has_23_hours() -> None:
    hours, versions = forecast_versions(date(2026, 3, 29), {})
    assert (len(hours), versions) == (23, [])
