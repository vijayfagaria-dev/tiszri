"""The interface every data source implements. Services depend on this, not on a concrete client."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol


@dataclass
class SourceResult:
    rows: list[dict[str, Any]]
    fetched_at: datetime
    cache: str  # HIT, MISS or BYPASS


class DataSource(Protocol):
    async def fetch_actuals(self, first: date, last: date) -> SourceResult:
        """FUELHH wind rows for settlement dates first..last (inclusive)."""
        ...

    async def fetch_forecasts(
        self, published_from: datetime, published_to: datetime
    ) -> SourceResult:
        """WINDFOR rows (every vintage) published in [published_from, published_to)."""
        ...
