"""Checks against the live Elexon API that the assumptions this service relies on still hold.

Skipped unless RUN_LIVE_TESTS=1. Run daily by .github/workflows/contract-live.yml, so a change in
Elexon's data format, resolution or history is noticed before it reaches users.
"""

import os
from collections import Counter
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime

import pytest

from app.clients.elexon import ElexonClient
from app.clients.parsing import parse_actuals, parse_forecasts
from app.core.config import Settings
from tests.support import recorded

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_TESTS") != "1", reason="set RUN_LIVE_TESTS=1 to call the live Elexon API"
)


@pytest.fixture
async def elexon() -> AsyncIterator[ElexonClient]:
    client = ElexonClient(Settings(app_env="test"))
    yield client
    await client.close()


async def test_fuelhh_still_has_every_settlement_period(elexon: ElexonClient) -> None:
    result = await elexon.fetch_actuals(date(2026, 1, 16), date(2026, 1, 16))
    actuals, rejected, not_wind = parse_actuals(result.rows)
    assert (rejected, not_wind) == (0, 0)
    assert sorted(a.settlement_period or 0 for a in actuals) == list(range(1, 49))
    assert all(a.generation is not None for a in actuals)


async def test_windfor_is_still_hourly_with_eight_versions_a_day(elexon: ElexonClient) -> None:
    result = await elexon.fetch_forecasts(
        datetime(2026, 1, 14, tzinfo=UTC), datetime(2026, 1, 15, tzinfo=UTC)
    )
    forecasts, rejected, off_hour = parse_forecasts(result.rows)
    assert (rejected, off_hour) == (0, 0)
    rows_per_version = Counter(f.publish_time for f in forecasts)
    assert len(rows_per_version) == 8
    assert set(rows_per_version.values()) == {73}


async def test_history_still_matches_the_recording(elexon: ElexonClient) -> None:
    """If Elexon revises January 2026, re-record the fixtures (`make record`) and recheck tests."""
    live = await elexon.fetch_actuals(date(2026, 1, 16), date(2026, 1, 16))
    saved = [r for r in recorded("fuelhh_wind.json.gz") if r["settlementDate"] == "2026-01-16"]

    def by_start(rows: list[dict[str, object]]) -> list[dict[str, object]]:
        return sorted(rows, key=lambda row: str(row["startTime"]))

    assert by_start(live.rows) == by_start(saved)
