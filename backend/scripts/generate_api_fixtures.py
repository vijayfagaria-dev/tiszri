"""Generate API response fixtures for the frontend's mock server, from the real backend.

Each scenario is run through the actual app on recorded Elexon data and written to
contracts/fixtures/api/, together with index.json (request -> file). A test regenerates them and
fails if the committed files no longer match what the backend returns.

Usage (from backend/): uv run python -m scripts.generate_api_fixtures
"""

import asyncio
import copy
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx

from app.clients.base import SourceResult
from app.clients.recorded import RecordedSource
from app.core.config import Settings
from app.core.errors import (
    UpstreamRateLimitError,
    UpstreamTimeoutError,
    UpstreamUnavailableError,
)
from app.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = REPO_ROOT / "contracts" / "fixtures" / "source"
OUTPUT_DIR = REPO_ROOT / "contracts" / "fixtures" / "api"
SETTINGS = Settings(app_env="test", source_mode="fixtures", cache_enabled=False)
RECORDED_AT = json.loads((SOURCE_DIR / "manifest.json").read_text())["recordedAt"]


@dataclass
class Scenario:
    name: str
    path: str
    params: dict[str, str] = field(default_factory=dict)
    description: str = ""
    source: str = "recorded"  # recorded, synthetic or a failure name


SCENARIOS = [
    Scenario("metadata", "/metadata", description="Static configuration"),
    Scenario(
        "analysis_2026-01-16_default",
        "/wind-analysis",
        {"deliveryDate": "2026-01-16"},
        "Default decision time (09:00 the day before): 07:30 forecast used",
    ),
    Scenario(
        "analysis_2026-01-16_noon-before",
        "/wind-analysis",
        {"deliveryDate": "2026-01-16", "cutoffDayOffset": "-1", "cutoffLocalTime": "12:00"},
        "Late 11:30 forecast (published 12:25): falls back to the 09:30 forecast",
    ),
    Scenario(
        "analysis_2026-01-28_default",
        "/wind-analysis",
        {"deliveryDate": "2026-01-28"},
        "Worst day: too high in all 48 periods",
    ),
    Scenario(
        "analysis_2026-01-19_default", "/wind-analysis", {"deliveryDate": "2026-01-19"}, "Best day"
    ),
    Scenario(
        "analysis_2026-01-05_default",
        "/wind-analysis",
        {"deliveryDate": "2026-01-05"},
        "Bias hides error: average error near zero, large misses both ways",
    ),
    Scenario(
        "analysis_2026-01-15_two-days-before",
        "/wind-analysis",
        {"deliveryDate": "2026-01-15", "cutoffDayOffset": "-2", "cutoffLocalTime": "09:00"},
        "PARTIAL: 22:00-23:30 not yet forecast",
    ),
    Scenario(
        "analysis_2026-01-15_three-days-before",
        "/wind-analysis",
        {"deliveryDate": "2026-01-15", "cutoffDayOffset": "-3", "cutoffLocalTime": "09:00"},
        "EMPTY: no forecast published yet",
    ),
    Scenario(
        "analysis_2026-01-16_after-delivery",
        "/wind-analysis",
        {"deliveryDate": "2026-01-16", "cutoffDayOffset": "1", "cutoffLocalTime": "00:00"},
        "Hindsight replay after delivery ended",
    ),
    Scenario(
        "analysis_2026-01-16_explicit-cutoff",
        "/wind-analysis",
        {"deliveryDate": "2026-01-16", "decisionCutoff": "2026-01-15T12:00:00Z"},
        "Exact decision time instead of a rule",
    ),
    Scenario(
        "analysis_synthetic_edge-cases",
        "/wind-analysis",
        {"deliveryDate": "2026-01-16"},
        "SYNTHETIC: every exclusion status, flag and data-quality warning",
        source="synthetic",
    ),
    Scenario(
        "versions_2026-01-16",
        "/forecast-versions",
        {"deliveryDate": "2026-01-16"},
        "Every forecast version covering 16 Jan, hour by hour",
    ),
    Scenario(
        "summary_default", "/accuracy-summary", description="Decisions made in January, 09:00"
    ),
    Scenario(
        "summary_noon-before",
        "/accuracy-summary",
        {"cutoffDayOffset": "-1", "cutoffLocalTime": "12:00"},
        "Decisions made in January, noon",
    ),
    Scenario("error_422_date-out-of-range", "/wind-analysis", {"deliveryDate": "2026-03-01"}),
    Scenario(
        "error_502_upstream-unavailable",
        "/wind-analysis",
        {"deliveryDate": "2026-01-16"},
        source="unavailable",
    ),
    Scenario(
        "error_503_upstream-rate-limited",
        "/wind-analysis",
        {"deliveryDate": "2026-01-16"},
        source="rate-limited",
    ),
    Scenario(
        "error_504_upstream-timeout",
        "/wind-analysis",
        {"deliveryDate": "2026-01-16"},
        source="timeout",
    ),
    Scenario(
        "error_500_internal", "/wind-analysis", {"deliveryDate": "2026-01-16"}, source="internal"
    ),
]

FAILURES: dict[str, Exception] = {
    "unavailable": UpstreamUnavailableError("down"),
    "rate-limited": UpstreamRateLimitError("busy", retry_after=60),
    "timeout": UpstreamTimeoutError("slow"),
    "internal": RuntimeError("boom"),
}


class FailingSource:
    def __init__(self, error: Exception) -> None:
        self._error = error

    async def fetch_actuals(self, first: date, last: date) -> SourceResult:
        raise self._error

    async def fetch_forecasts(
        self, published_from: datetime, published_to: datetime
    ) -> SourceResult:
        raise self._error


class SyntheticSource:
    """Recorded data for 16 Jan with targeted defects, one per edge case the UI must render."""

    def __init__(self, recorded: RecordedSource) -> None:
        self._recorded = recorded

    async def fetch_actuals(self, first: date, last: date) -> SourceResult:
        result = await self._recorded.fetch_actuals(first, last)
        rows = copy.deepcopy(result.rows)
        by_start = {row["startTime"]: row for row in rows}
        del by_start["2026-01-16T11:00:00Z"]  # ACTUAL_MISSING
        del by_start["2026-01-16T15:00:00Z"]  # with the 15:00 forecasts removed: FULLY_MISSING
        rows = list(by_start.values())
        rows.append({**by_start["2026-01-16T17:00:00Z"], "generation": 1})  # AMBIGUOUS_ACTUAL
        rows.append(dict(by_start["2026-01-16T18:00:00Z"]))  # identical duplicate
        by_start["2026-01-16T19:00:00Z"]["settlementPeriod"] = 1  # inconsistent metadata
        rows.append(
            {"dataset": "FUELHH", "fuelType": "WIND", "startTime": "not a time"}
        )  # rejected
        return SourceResult(rows, result.fetched_at, result.cache)

    async def fetch_forecasts(
        self, published_from: datetime, published_to: datetime
    ) -> SourceResult:
        result = await self._recorded.fetch_forecasts(published_from, published_to)
        latest = "2026-01-15T07:30:00Z"  # the vintage the default decision time selects
        rows = []
        for row in copy.deepcopy(result.rows):
            hour = row["startTime"]
            if hour in ("2026-01-16T07:00:00Z", "2026-01-16T15:00:00Z"):
                continue  # FORECAST_MISSING
            if hour == "2026-01-16T21:00:00Z" and row["publishTime"] <= "2026-01-15T09:00:00Z":
                continue  # only later vintages remain: FORECAST_NOT_YET_PUBLISHED
            if hour == "2026-01-16T09:00:00Z" and row["publishTime"] == latest:
                row["generation"] = None  # INVALID_VALUE
            rows.append(row)
            if hour == "2026-01-16T03:00:00Z" and row["publishTime"] == latest:
                rows.append(dict(row))  # identical duplicate
            if hour == "2026-01-16T05:00:00Z" and row["publishTime"] == latest:
                rows.append({**row, "generation": row["generation"] + 500})  # AMBIGUOUS_FORECAST
        rows.append(
            {
                "dataset": "WINDFOR",
                "publishTime": latest,
                "startTime": "2026-01-16T12:30:00Z",
                "generation": 1,
            }
        )  # off the hourly grid
        return SourceResult(rows, result.fetched_at, result.cache)


async def build_fixtures() -> dict[str, tuple[Scenario, int, Any]]:
    recorded = RecordedSource(SOURCE_DIR)
    built: dict[str, tuple[Scenario, int, Any]] = {}
    for scenario in SCENARIOS:
        if scenario.source == "recorded":
            source: Any = recorded
        elif scenario.source == "synthetic":
            source = SyntheticSource(recorded)
        else:
            source = FailingSource(FAILURES[scenario.source])
        app = create_app(SETTINGS, source=source)
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://fixtures") as client:
            response = await client.get(
                f"/api/v1{scenario.path}",
                params=scenario.params,
                headers={"X-Request-ID": f"fixture-{scenario.name.replace('_', '-')}"},
            )
        body = response.json()
        if isinstance(body.get("metadata"), dict) and "generatedAt" in body["metadata"]:
            body["metadata"]["generatedAt"] = RECORDED_AT  # keep regenerated files stable
        built[scenario.name] = (scenario, response.status_code, body)
    return built


def write(built: dict[str, tuple[Scenario, int, Any]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUTPUT_DIR.glob("*.json"):  # drop files of scenarios that no longer exist
        old.unlink()
    index = []
    for name, (scenario, status, body) in built.items():
        (OUTPUT_DIR / f"{name}.json").write_text(json.dumps(body, indent=2) + "\n")
        index.append(
            {
                "file": f"{name}.json",
                "status": status,
                "request": {"path": f"/api/v1{scenario.path}", "params": scenario.params},
                "source": scenario.source,
                "description": scenario.description,
            }
        )
    (OUTPUT_DIR / "index.json").write_text(json.dumps(index, indent=2) + "\n")


if __name__ == "__main__":
    fixtures = asyncio.run(build_fixtures())
    write(fixtures)
    for name, (_, status, _) in fixtures.items():
        print(f"{status}  {name}")
