"""Client for the Elexon Insights API (FUELHH and WINDFOR stream endpoints)."""

import asyncio
import logging
import time
from datetime import UTC, date, datetime
from typing import Any

import httpx

from app.clients.base import SourceResult
from app.clients.parsing import parse_time
from app.core.config import Settings
from app.core.errors import (
    UpstreamError,
    UpstreamMalformedError,
    UpstreamRateLimitError,
    UpstreamRejectedError,
    UpstreamTimeoutError,
    UpstreamUnavailableError,
)
from app.utils.dates import format_utc

logger = logging.getLogger(__name__)


class ElexonClient:
    def __init__(self, settings: Settings, http: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self.last_success_at: datetime | None = None
        self.last_failure_at: datetime | None = None
        self._http = http or httpx.AsyncClient(
            base_url=settings.elexon_base_url,
            timeout=httpx.Timeout(
                settings.http_read_timeout_s, connect=settings.http_connect_timeout_s
            ),
            headers={"Accept": "application/json"},
        )

    async def fetch_actuals(self, first: date, last: date) -> SourceResult:
        params = {
            "settlementDateFrom": first.isoformat(),
            "settlementDateTo": last.isoformat(),
            "fuelType": "WIND",
        }
        rows = await self._get("/datasets/FUELHH/stream", params)
        return SourceResult(rows, datetime.now(UTC), "MISS")

    async def fetch_forecasts(
        self, published_from: datetime, published_to: datetime
    ) -> SourceResult:
        params = {
            "publishDateTimeFrom": format_utc(published_from),
            "publishDateTimeTo": format_utc(published_to),
        }
        rows = await self._get("/datasets/WINDFOR/stream", params)
        # Elexon does not document whether the end of the range is inclusive, so we apply our own
        # half-open window. Rows without a readable publish time are kept for parsing to reject.
        in_window = [row for row in rows if _published_within(row, published_from, published_to)]
        return SourceResult(in_window, datetime.now(UTC), "MISS")

    async def close(self) -> None:
        await self._http.aclose()

    async def _get(self, path: str, params: dict[str, str]) -> list[dict[str, Any]]:
        retries_left = self._settings.upstream_max_retries
        while True:
            try:
                rows = await self._get_once(path, params)
                self.last_success_at = datetime.now(UTC)
                return rows
            except UpstreamError as error:
                if not error.retryable or retries_left == 0:
                    self.last_failure_at = datetime.now(UTC)
                    raise
                retries_left -= 1
                logger.warning("Retrying %s after: %s", path, error)
                await asyncio.sleep(self._settings.upstream_retry_backoff_s)

    async def _get_once(self, path: str, params: dict[str, str]) -> list[dict[str, Any]]:
        started = time.perf_counter()
        try:
            response = await self._http.get(path, params=params)
        except httpx.TimeoutException as error:
            raise UpstreamTimeoutError(f"Elexon did not respond in time ({path})") from error
        except httpx.TransportError as error:
            raise UpstreamUnavailableError(f"Could not reach Elexon ({path})") from error

        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.info("Elexon GET %s -> %s in %.0f ms", path, response.status_code, elapsed_ms)

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise UpstreamRateLimitError(
                "Elexon is rate limiting requests",
                int(retry_after) if retry_after and retry_after.isdigit() else None,
            )
        if response.status_code >= 500:
            raise UpstreamUnavailableError(f"Elexon returned {response.status_code} ({path})")
        if response.status_code >= 400:
            raise UpstreamRejectedError(
                f"Elexon rejected the request with {response.status_code} ({path})"
            )
        if len(response.content) > self._settings.max_upstream_response_bytes:
            raise UpstreamMalformedError(f"Elexon response is larger than allowed ({path})")
        try:
            rows = response.json()
        except ValueError as error:
            raise UpstreamMalformedError(f"Elexon returned invalid JSON ({path})") from error
        if not isinstance(rows, list):
            raise UpstreamMalformedError(f"Elexon returned {type(rows).__name__}, expected a list")
        return rows


def _published_within(row: Any, start: datetime, end: datetime) -> bool:
    published = parse_time(row.get("publishTime")) if isinstance(row, dict) else None
    return published is None or start <= published < end
