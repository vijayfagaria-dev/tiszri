"""Results produced by the analysis layer."""

from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any

from app.models.enums import Flag, Status, WarningCode
from app.models.source import Actual, Forecast


@dataclass
class CutoffRule:
    """A decision time relative to the delivery date, in UK local time."""

    day_offset: int
    local_time: time


@dataclass
class Cutoff:
    utc: datetime
    source: str  # EXPLICIT, RULE or DEFAULT
    position: str  # BEFORE_DELIVERY, INSIDE_DELIVERY or AFTER_DELIVERY
    rule: CutoffRule | None = None
    preset: str | None = None


@dataclass
class ForecastChoice:
    """Which forecast for one hour was knowable at the decision time."""

    forecast: Forecast | None = None
    eligible: int = 0  # vintages published at or before the cutoff
    later: int = 0  # vintages published after it
    earliest_later: datetime | None = None
    ambiguous: bool = False
    conflicting: list[int] = field(default_factory=list)
    duplicated: bool = False


@dataclass
class Interval:
    number: int  # GB settlement period, 1-based
    start: datetime
    end: datetime
    status: Status
    reason: str | None
    choice: ForecastChoice
    actual: Actual | None
    actual_conflicting: list[int]
    error: int | None  # forecast - actual, only when MATCHED
    flags: list[Flag]


@dataclass
class Metrics:
    n: int
    mae: float | None
    rmse: float | None
    bias: float | None
    over: int
    under: int
    exact: int


@dataclass
class AnalysisWarning:
    code: WarningCode
    severity: str  # INFO or WARNING
    scope: str  # ANALYSIS, INTERVAL or SOURCE
    message: str
    intervals: list[datetime] = field(default_factory=list)
    data: dict[str, Any] | None = None
    count: int | None = None  # defaults to the number of affected intervals

    @property
    def affected_count(self) -> int:
        return self.count if self.count is not None else len(self.intervals)


@dataclass
class DayAnalysis:
    delivery_date: date
    cutoff: Cutoff
    intervals: list[Interval]
    status_counts: dict[Status, int]
    metrics: Metrics
    warnings: list[AnalysisWarning]
    largest_over: datetime | None
    largest_under: datetime | None
    versions_used: list[datetime]
    versions_covering: int
    versions_eligible: int
    earliest_covering: datetime | None
    newer_after_cutoff: datetime | None

    @property
    def expected(self) -> int:
        return len(self.intervals)

    @property
    def matched(self) -> int:
        return self.status_counts[Status.MATCHED]

    @property
    def result_state(self) -> str:
        if self.matched == 0:
            return "EMPTY"
        return "COMPLETE" if self.matched == self.expected else "PARTIAL"


@dataclass
class FeaturedDay:
    kind: str  # WORST_DAY, BEST_DAY, BIAS_HIDES_ERROR or OFF_SCHEDULE_VINTAGE
    delivery_date: date
    rule: CutoffRule
    data: dict[str, Any]


@dataclass
class Summary:
    days: list[DayAnalysis]
    status_counts: dict[Status, int]
    metrics: Metrics
    on_the_hour: Metrics
    abs_percentiles: dict[str, int] | None  # p50, p90, p95 of |error|
    signed_percentiles: dict[str, int] | None  # p10, p90 of the signed error
    histogram: list[tuple[int, int]]  # (lower edge, count), 500 MW bins
    featured: list[FeaturedDay]
    warnings: list[AnalysisWarning]

    @property
    def matched(self) -> int:
        return self.status_counts[Status.MATCHED]

    @property
    def expected(self) -> int:
        return sum(self.status_counts.values())
