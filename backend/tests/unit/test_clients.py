import asyncio
from datetime import UTC, date, datetime

import httpx
import pytest
import respx

from app.clients.base import SourceResult
from app.clients.cache import CachedSource
from app.clients.elexon import ElexonClient
from app.clients.recorded import RecordedSource
from app.core.config import Settings
from app.core.errors import (
    UpstreamMalformedError,
    UpstreamRateLimitError,
    UpstreamRejectedError,
    UpstreamTimeoutError,
    UpstreamUnavailableError,
)
from tests.support import SOURCE_FIXTURES

BASE = "https://data.elexon.co.uk/bmrs/api/v1"
FUELHH = f"{BASE}/datasets/FUELHH/stream"
WINDFOR = f"{BASE}/datasets/WINDFOR/stream"
ROWS = [
    {"dataset": "FUELHH", "startTime": "2026-01-16T00:00:00Z", "fuelType": "WIND", "generation": 1}
]

pytestmark = pytest.mark.req("NFR-004", "API-005")


def client(**overrides: object) -> ElexonClient:
    settings = Settings(app_env="test", upstream_retry_backoff_s=0, **overrides)  # type: ignore[arg-type]
    return ElexonClient(settings)


async def fetch(elexon: ElexonClient) -> SourceResult:
    return await elexon.fetch_actuals(date(2026, 1, 16), date(2026, 1, 16))


@respx.mock
async def test_returns_rows_and_sends_the_expected_query() -> None:
    route = respx.get(FUELHH).respond(json=ROWS)
    elexon = client()
    result = await fetch(elexon)
    assert result.rows == ROWS
    assert result.cache == "MISS"
    assert route.calls.last.request.url.params["fuelType"] == "WIND"
    assert elexon.last_success_at is not None


@respx.mock
async def test_server_error_is_retried_once() -> None:
    route = respx.get(FUELHH).mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json=ROWS)]
    )
    assert (await fetch(client())).rows == ROWS
    assert route.call_count == 2


@respx.mock
async def test_persistent_server_error() -> None:
    route = respx.get(FUELHH).respond(500)
    elexon = client()
    with pytest.raises(UpstreamUnavailableError):
        await fetch(elexon)
    assert route.call_count == 2
    assert elexon.last_failure_at is not None


@respx.mock
async def test_rate_limit_keeps_retry_after() -> None:
    respx.get(FUELHH).respond(429, headers={"Retry-After": "30"})
    with pytest.raises(UpstreamRateLimitError) as raised:
        await fetch(client())
    assert raised.value.retry_after == 30


@respx.mock
async def test_timeout() -> None:
    respx.get(FUELHH).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(UpstreamTimeoutError):
        await fetch(client())


@respx.mock
@pytest.mark.parametrize(
    ("response", "error"),
    [
        (httpx.Response(400), UpstreamRejectedError),
        (httpx.Response(200, content=b"<html>"), UpstreamMalformedError),
        (httpx.Response(200, json={"data": []}), UpstreamMalformedError),
    ],
    ids=["client-error", "not-json", "not-a-list"],
)
async def test_non_retryable_failures_are_not_retried(
    response: httpx.Response, error: type
) -> None:
    route = respx.get(FUELHH).mock(return_value=response)
    with pytest.raises(error):
        await fetch(client())
    assert route.call_count == 1


@respx.mock
async def test_oversized_response_is_rejected() -> None:
    respx.get(FUELHH).respond(json=ROWS * 100)
    with pytest.raises(UpstreamMalformedError):
        await fetch(client(max_upstream_response_bytes=1000))


@respx.mock
async def test_forecast_window_is_half_open() -> None:
    rows = [
        {"publishTime": "2026-01-12T00:00:00Z"},
        {"publishTime": "2026-01-17T23:59:59Z"},
        {"publishTime": "2026-01-18T00:00:00Z"},  # equal to the end: excluded
        {"publishTime": None},  # kept for parsing to reject and count
    ]
    respx.get(WINDFOR).respond(json=rows)
    result = await client().fetch_forecasts(
        datetime(2026, 1, 12, tzinfo=UTC), datetime(2026, 1, 18, tzinfo=UTC)
    )
    assert [r["publishTime"] for r in result.rows] == [
        "2026-01-12T00:00:00Z",
        "2026-01-17T23:59:59Z",
        None,
    ]


class CountingSource:
    def __init__(self) -> None:
        self.calls = 0

    async def fetch_actuals(self, first: date, last: date) -> SourceResult:
        self.calls += 1
        await asyncio.sleep(0.01)
        return SourceResult([], datetime.now(UTC), "MISS")

    async def fetch_forecasts(
        self, published_from: datetime, published_to: datetime
    ) -> SourceResult:
        return await self.fetch_actuals(published_from.date(), published_to.date())


async def test_cache_serves_repeat_requests() -> None:
    upstream = CountingSource()
    cached = CachedSource(upstream, ttl_seconds=60)
    first = await cached.fetch_actuals(date(2026, 1, 16), date(2026, 1, 16))
    second = await cached.fetch_actuals(date(2026, 1, 16), date(2026, 1, 16))
    assert (first.cache, second.cache, upstream.calls) == ("MISS", "HIT", 1)


async def test_concurrent_requests_share_one_upstream_call() -> None:
    upstream = CountingSource()
    cached = CachedSource(upstream, ttl_seconds=60)
    await asyncio.gather(
        *(cached.fetch_actuals(date(2026, 1, 16), date(2026, 1, 16)) for _ in range(5))
    )
    assert upstream.calls == 1


async def test_cache_entries_expire() -> None:
    upstream = CountingSource()
    cached = CachedSource(upstream, ttl_seconds=0)
    await cached.fetch_actuals(date(2026, 1, 16), date(2026, 1, 16))
    await cached.fetch_actuals(date(2026, 1, 16), date(2026, 1, 16))
    assert upstream.calls == 2


async def test_recorded_source_filters_by_range() -> None:
    source = RecordedSource(SOURCE_FIXTURES)
    actuals = await source.fetch_actuals(date(2026, 1, 16), date(2026, 1, 16))
    forecasts = await source.fetch_forecasts(
        datetime(2026, 1, 15, tzinfo=UTC), datetime(2026, 1, 16, tzinfo=UTC)
    )
    assert len(actuals.rows) == 48
    assert len(forecasts.rows) == 8 * 73  # eight vintages of 73 hourly values
    assert actuals.cache == "BYPASS"


def test_production_refuses_recorded_data() -> None:
    with pytest.raises(ValueError, match="production"):
        Settings(app_env="production", source_mode="fixtures")


def test_only_the_elexon_host_is_allowed() -> None:
    with pytest.raises(ValueError, match="not allowed"):
        Settings(elexon_base_url="https://example.com/api")
