"""A data source backed by recorded Elexon responses, for tests and offline development."""

import gzip
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.clients.base import SourceResult
from app.clients.parsing import parse_time


class RecordedSource:
    def __init__(self, directory: Path) -> None:
        manifest = json.loads((directory / "manifest.json").read_text())
        self._recorded_at = datetime.fromisoformat(manifest["recordedAt"])
        self._actuals = _load(directory / "fuelhh_wind.json.gz")
        self._forecasts = _load(directory / "windfor.json.gz")

    async def fetch_actuals(self, first: date, last: date) -> SourceResult:
        rows = [
            row
            for row in self._actuals
            if first.isoformat() <= str(row.get("settlementDate")) <= last.isoformat()
        ]
        return self._result(rows)

    async def fetch_forecasts(
        self, published_from: datetime, published_to: datetime
    ) -> SourceResult:
        rows = []
        for row in self._forecasts:
            published = parse_time(row.get("publishTime"))
            if published is not None and published_from <= published < published_to:
                rows.append(row)
        return self._result(rows)

    def _result(self, rows: list[dict[str, Any]]) -> SourceResult:
        return SourceResult(rows, self._recorded_at, "BYPASS")


def _load(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = json.loads(gzip.decompress(path.read_bytes()))
    return rows
