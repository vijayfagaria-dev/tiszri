"""Use cases: replay one delivery day, and summarise accuracy over a window of days."""

import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.analysis.cutoffs import cutoff_from_rule
from app.analysis.day_warnings import sort_warnings
from app.analysis.replay import analyze_day
from app.analysis.summary import summarize
from app.analysis.versions import forecast_versions
from app.clients.base import DataSource
from app.models.analysis import (
    AnalysisWarning,
    Cutoff,
    CutoffRule,
    DayAnalysis,
    ForecastVersion,
    Summary,
)
from app.services.loader import SourceInfo, load_data, load_forecasts


@dataclass
class DayReport:
    day: DayAnalysis
    sources: list[SourceInfo]
    warnings: list[AnalysisWarning]
    fetch_ms: float = 0.0
    analyze_ms: float = 0.0


@dataclass
class SummaryReport:
    summary: Summary
    rule: CutoffRule
    rule_source: str  # RULE or DEFAULT
    first: date
    last: date
    sources: list[SourceInfo]
    warnings: list[AnalysisWarning]
    fetch_ms: float = 0.0
    analyze_ms: float = 0.0


@dataclass
class VersionsReport:
    delivery_date: date
    hours: list[datetime]
    versions: list[ForecastVersion]
    source: SourceInfo
    warnings: list[AnalysisWarning]
    fetch_ms: float = 0.0
    analyze_ms: float = 0.0


class ReplayService:
    def __init__(self, source: DataSource, lookback_days: int) -> None:
        self._source = source
        self._lookback_days = lookback_days

    async def replay_day(self, delivery_date: date, cutoff: Cutoff) -> DayReport:
        started = time.perf_counter()
        data = await load_data(self._source, delivery_date, delivery_date, self._lookback_days)
        fetched = time.perf_counter()
        day = analyze_day(delivery_date, cutoff, data.forecasts_by_hour, data.actuals_by_start)
        warnings = sort_warnings(day.warnings + data.warnings)
        return DayReport(day, data.sources, warnings, _ms(started, fetched), _ms(fetched))

    async def summarize_window(
        self, first: date, last: date, rule: CutoffRule, rule_source: str
    ) -> SummaryReport:
        started = time.perf_counter()
        data = await load_data(self._source, first, last, self._lookback_days)
        fetched = time.perf_counter()
        days = []
        for offset in range((last - first).days + 1):
            delivery_date = first + timedelta(days=offset)
            cutoff = cutoff_from_rule(delivery_date, rule, rule_source)
            days.append(
                analyze_day(delivery_date, cutoff, data.forecasts_by_hour, data.actuals_by_start)
            )
        summary = summarize(days, rule, data.publish_times)
        warnings = sort_warnings(summary.warnings + data.warnings)
        return SummaryReport(
            summary,
            rule,
            rule_source,
            first,
            last,
            data.sources,
            warnings,
            _ms(started, fetched),
            _ms(fetched),
        )

    async def forecast_versions(self, delivery_date: date) -> VersionsReport:
        started = time.perf_counter()
        loaded = await load_forecasts(
            self._source, delivery_date, delivery_date, self._lookback_days
        )
        fetched = time.perf_counter()
        hours, versions = forecast_versions(delivery_date, loaded.by_hour)
        return VersionsReport(
            delivery_date,
            hours,
            versions,
            loaded.source,
            sort_warnings(loaded.warnings),
            _ms(started, fetched),
            _ms(fetched),
        )


def _ms(start: float, end: float | None = None) -> float:
    return ((end if end is not None else time.perf_counter()) - start) * 1000
