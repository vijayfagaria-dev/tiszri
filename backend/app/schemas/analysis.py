"""Response model for GET /wind-analysis."""

from datetime import UTC, datetime

from app.core.config import Settings
from app.models.analysis import Interval
from app.models.source import FORECAST_PERIOD
from app.schemas.common import (
    ALGORITHM_VERSION,
    CONTRACT_VERSION,
    POLICY_IDS,
    ApiModel,
    AppliedCutoffOut,
    CountsOut,
    MetricsOut,
    PolicyIdsOut,
    ResolutionOut,
    SourceOut,
    UnitSummaryOut,
    VersionCountsOut,
    WarningOut,
    counts_out,
    cutoff_out,
    error_direction,
    metrics_out,
    source_out,
    unit_summary,
    warning_out,
)
from app.services.replay_service import DayReport
from app.utils.dates import format_utc, minutes_between


class AnalysisQueryOut(ApiModel):
    delivery_date: str
    decision_cutoff: AppliedCutoffOut
    business_timezone: str = "Europe/London"


class AnalysisMetadataOut(ApiModel):
    contract_version: str
    algorithm_version: str
    request_id: str
    generated_at: str
    sources: list[SourceOut]
    unit: UnitSummaryOut
    resolution: ResolutionOut
    policy_ids: PolicyIdsOut
    counts: CountsOut
    coverage: float


class HighlightsOut(ApiModel):
    largest_over: str | None
    largest_under: str | None
    versions_used: list[str]
    earliest_covering_publish_time: str | None
    newer_version_after_cutoff: str | None


class IntervalForecastOut(ApiModel):
    generation: int | None
    publish_time: str
    period_start: str
    period_end: str
    lead_minutes: int
    age_at_cutoff_minutes: int


class IntervalSelectionOut(ApiModel):
    eligible_count: int
    later_count: int
    earliest_later_publish_time: str | None
    conflicting_values: list[int] | None


class IntervalActualOut(ApiModel):
    generation: int | None
    publish_time: str | None
    conflicting_values: list[int] | None


class IntervalErrorOut(ApiModel):
    signed: int
    absolute: int
    direction: str


class IntervalOut(ApiModel):
    settlement_period: int
    start_time: str
    end_time: str
    status: str
    exclusion_reason: str | None
    forecast: IntervalForecastOut | None
    selection: IntervalSelectionOut
    actual: IntervalActualOut | None
    error: IntervalErrorOut | None
    flags: list[str]


class DayAnalysisResponse(ApiModel):
    result_state: str
    query: AnalysisQueryOut
    metadata: AnalysisMetadataOut
    metrics: MetricsOut
    highlights: HighlightsOut
    intervals: list[IntervalOut]
    warnings: list[WarningOut]


def day_response(report: DayReport, settings: Settings, request_id: str) -> DayAnalysisResponse:
    day = report.day
    cutoff = day.cutoff.utc
    fuelhh, windfor = report.sources
    versions = VersionCountsOut(
        covering_day=day.versions_covering,
        eligible=day.versions_eligible,
        after_cutoff=day.versions_covering - day.versions_eligible,
    )
    return DayAnalysisResponse(
        result_state=day.result_state,
        query=AnalysisQueryOut(
            delivery_date=day.delivery_date.isoformat(), decision_cutoff=cutoff_out(day.cutoff)
        ),
        metadata=AnalysisMetadataOut(
            contract_version=CONTRACT_VERSION,
            algorithm_version=ALGORITHM_VERSION,
            request_id=request_id,
            generated_at=format_utc(datetime.now(UTC)),
            sources=[source_out(fuelhh), source_out(windfor, versions)],
            unit=unit_summary(settings),
            resolution=ResolutionOut(),
            policy_ids=PolicyIdsOut(**POLICY_IDS),
            counts=counts_out(day.status_counts),
            coverage=day.matched / day.expected,
        ),
        metrics=metrics_out(day.metrics, qualified=day.result_state != "COMPLETE"),
        highlights=HighlightsOut(
            largest_over=_utc_or_none(day.largest_over),
            largest_under=_utc_or_none(day.largest_under),
            versions_used=[format_utc(t) for t in day.versions_used],
            earliest_covering_publish_time=_utc_or_none(day.earliest_covering),
            newer_version_after_cutoff=_utc_or_none(day.newer_after_cutoff),
        ),
        intervals=[_interval_out(interval, cutoff) for interval in day.intervals],
        warnings=[warning_out(w) for w in report.warnings],
    )


def _interval_out(interval: Interval, cutoff: datetime) -> IntervalOut:
    choice = interval.choice
    return IntervalOut(
        settlement_period=interval.number,
        start_time=format_utc(interval.start),
        end_time=format_utc(interval.end),
        status=interval.status,
        exclusion_reason=interval.reason,
        forecast=_forecast_out(interval, cutoff),
        selection=IntervalSelectionOut(
            eligible_count=choice.eligible,
            later_count=choice.later,
            earliest_later_publish_time=_utc_or_none(choice.earliest_later),
            conflicting_values=choice.conflicting if choice.ambiguous else None,
        ),
        actual=_actual_out(interval),
        error=_error_out(interval.error),
        flags=[str(flag) for flag in interval.flags],
    )


def _forecast_out(interval: Interval, cutoff: datetime) -> IntervalForecastOut | None:
    forecast = interval.choice.forecast
    if forecast is None:
        return None
    return IntervalForecastOut(
        generation=forecast.generation,
        publish_time=format_utc(forecast.publish_time),
        period_start=format_utc(forecast.start),
        period_end=format_utc(forecast.start + FORECAST_PERIOD),
        lead_minutes=minutes_between(interval.start, forecast.publish_time),
        age_at_cutoff_minutes=minutes_between(cutoff, forecast.publish_time),
    )


def _actual_out(interval: Interval) -> IntervalActualOut | None:
    if interval.actual_conflicting:
        return IntervalActualOut(
            generation=None, publish_time=None, conflicting_values=interval.actual_conflicting
        )
    if interval.actual is None:
        return None
    return IntervalActualOut(
        generation=interval.actual.generation,
        publish_time=_utc_or_none(interval.actual.publish_time),
        conflicting_values=None,
    )


def _error_out(error: int | None) -> IntervalErrorOut | None:
    if error is None:
        return None
    return IntervalErrorOut(signed=error, absolute=abs(error), direction=error_direction(error))


def _utc_or_none(moment: datetime | None) -> str | None:
    return format_utc(moment) if moment else None
