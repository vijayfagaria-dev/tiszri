"""Response models shared by several endpoints. Field names serialise to camelCase."""

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.core.config import Settings
from app.models.analysis import AnalysisWarning, Cutoff, CutoffRule, Metrics
from app.models.enums import Status
from app.services.loader import SourceInfo
from app.utils.dates import format_london, format_utc

CONTRACT_VERSION = "1.2.0"
ALGORITHM_VERSION = "replay/1.0.0"
POLICY_IDS = {
    "selection": "LATEST_ELIGIBLE_INCLUSIVE",
    "mapping": "HOURLY_FORECAST_APPLIED_TO_BOTH_SETTLEMENT_PERIODS",
    "duplicates": "EQUIVALENT_COLLAPSE_CONFLICT_EXCLUDE",
}


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CutoffRuleOut(ApiModel):
    day_offset: int
    local_time: str


class AppliedCutoffOut(ApiModel):
    utc: str
    london: str
    source: str
    rule: CutoffRuleOut | None
    preset_id: str | None
    position: str


class UnitInfoOut(ApiModel):
    unit: str
    meaning: str
    status: str
    evidence: str


class UnitSummaryOut(ApiModel):
    label: str
    actual: UnitInfoOut
    forecast: UnitInfoOut


class DirectionCountsOut(ApiModel):
    over: int
    under: int
    exact: int


class MetricsOut(ApiModel):
    n: int
    mae: float | None
    rmse: float | None
    bias: float | None
    direction_counts: DirectionCountsOut
    sign_convention: str = "FORECAST_MINUS_ACTUAL"
    qualified: bool
    unavailable_reason: str | None


class CountsOut(ApiModel):
    expected: int
    matched: int
    excluded: int
    by_status: dict[str, int]


class RequestedRangeOut(ApiModel):
    from_: str = Field(alias="from")
    to: str
    basis: str


class VersionCountsOut(ApiModel):
    covering_day: int
    eligible: int
    after_cutoff: int


class SourceOut(ApiModel):
    dataset: str
    role: str
    filter: dict[str, str] | None
    requested_range: RequestedRangeOut
    rows_received: int
    rows_rejected: int
    rows_filtered: int
    fetched_at: str
    cache: str
    versions: VersionCountsOut | None


class ResolutionOut(ApiModel):
    delivery_minutes: int = 30
    forecast_minutes: int = 60


class PolicyIdsOut(ApiModel):
    selection: str
    mapping: str
    duplicates: str


class WarningOut(ApiModel):
    code: str
    severity: str
    scope: str
    message: str
    affected_count: int
    affected_intervals: list[str]
    data: dict[str, Any] | None


# Fields that differ between otherwise identical responses; left out of the result hash.
VOLATILE_FIELDS = {"requestId", "generatedAt", "fetchedAt", "cache", "resultHash"}


def result_hash(body: dict[str, Any]) -> str:
    """Fingerprint of a response's content: the same inputs and data always give the same hash."""
    canonical = json.dumps(_without_volatile(body), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


def _without_volatile(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _without_volatile(v) for k, v in value.items() if k not in VOLATILE_FIELDS}
    if isinstance(value, list):
        return [_without_volatile(v) for v in value]
    return value


def error_direction(error: int) -> str:
    """OVER when the forecast was too high, UNDER when too low."""
    return "OVER" if error > 0 else "UNDER" if error < 0 else "EXACT"


def rule_out(rule: CutoffRule) -> CutoffRuleOut:
    return CutoffRuleOut(day_offset=rule.day_offset, local_time=rule.local_time.strftime("%H:%M"))


def cutoff_out(cutoff: Cutoff) -> AppliedCutoffOut:
    return AppliedCutoffOut(
        utc=format_utc(cutoff.utc),
        london=format_london(cutoff.utc),
        source=cutoff.source,
        rule=rule_out(cutoff.rule) if cutoff.rule else None,
        preset_id=cutoff.preset,
        position=cutoff.position,
    )


def metrics_out(metrics: Metrics, qualified: bool) -> MetricsOut:
    return MetricsOut(
        n=metrics.n,
        mae=metrics.mae,
        rmse=metrics.rmse,
        bias=metrics.bias,
        direction_counts=DirectionCountsOut(
            over=metrics.over, under=metrics.under, exact=metrics.exact
        ),
        qualified=qualified,
        unavailable_reason="NO_MATCHED_INTERVALS" if metrics.n == 0 else None,
    )


def counts_out(status_counts: dict[Status, int]) -> CountsOut:
    expected = sum(status_counts.values())
    matched = status_counts[Status.MATCHED]
    return CountsOut(
        expected=expected,
        matched=matched,
        excluded=expected - matched,
        by_status={status.value: count for status, count in status_counts.items()},
    )


def source_out(info: SourceInfo, versions: VersionCountsOut | None = None) -> SourceOut:
    return SourceOut(
        dataset=info.dataset,
        role=info.role,
        filter={"fuelType": "WIND"} if info.dataset == "FUELHH" else None,
        requested_range=RequestedRangeOut(
            from_=info.requested_from, to=info.requested_to, basis=info.basis
        ),
        rows_received=info.rows_received,
        rows_rejected=info.rows_rejected,
        rows_filtered=info.rows_filtered,
        fetched_at=format_utc(info.fetched_at),
        cache=info.cache,
        versions=versions,
    )


def warning_out(warning: AnalysisWarning) -> WarningOut:
    return WarningOut(
        code=warning.code,
        severity=warning.severity,
        scope=warning.scope,
        message=warning.message,
        affected_count=warning.affected_count,
        affected_intervals=[format_utc(start) for start in warning.intervals],
        data=warning.data,
    )


def unit_summary(settings: Settings) -> UnitSummaryOut:
    actual, forecast = units(settings)
    label = "MW" if actual.status == forecast.status == "VERIFIED" else "source units (unverified)"
    return UnitSummaryOut(label=label, actual=actual, forecast=forecast)


def units(settings: Settings) -> tuple[UnitInfoOut, UnitInfoOut]:
    actual = UnitInfoOut(
        unit="MW",
        meaning="Average over the 30-minute settlement period",
        status="VERIFIED",
        evidence="Elexon Insights FUELHH description",
    )
    forecast = UnitInfoOut(
        unit="MW",
        meaning="Hourly forecast value; averaging semantics undocumented",
        status=settings.windfor_unit_status,
        evidence="Product-owner approval; NETA IDD",
    )
    return actual, forecast
