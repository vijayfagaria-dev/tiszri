"""Response model for GET /accuracy-summary."""

from datetime import UTC, datetime
from typing import Any

from pydantic import Field

from app.analysis.cutoffs import preset_for
from app.analysis.summary import HISTOGRAM_BIN_MW
from app.core.config import Settings
from app.models.analysis import DayAnalysis, Metrics
from app.schemas.common import (
    ALGORITHM_VERSION,
    CONTRACT_VERSION,
    POLICY_IDS,
    ApiModel,
    AppliedCutoffOut,
    CountsOut,
    CutoffRuleOut,
    DirectionCountsOut,
    PolicyIdsOut,
    ResolutionOut,
    SourceOut,
    UnitSummaryOut,
    WarningOut,
    counts_out,
    cutoff_out,
    result_hash,
    rule_out,
    source_out,
    unit_summary,
    warning_out,
)
from app.services.replay_service import SummaryReport
from app.utils.dates import format_utc


class SummaryQueryOut(ApiModel):
    from_: str = Field(alias="from")
    to: str
    rule: CutoffRuleOut
    rule_source: str
    preset_id: str | None
    business_timezone: str = "Europe/London"


class SummaryMetadataOut(ApiModel):
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
    day_count: int
    result_hash: str = ""


class SummaryMetricsOut(ApiModel):
    n: int
    mae: float | None
    rmse: float | None
    bias: float | None
    direction_counts: DirectionCountsOut
    over_share: float | None
    under_share: float | None
    sign_convention: str = "FORECAST_MINUS_ACTUAL"
    qualified: bool
    unavailable_reason: str | None


class AbsErrorOut(ApiModel):
    p50: int
    p90: int
    p95: int


class SignedErrorOut(ApiModel):
    p10: int
    p90: int


class HistogramBinOut(ApiModel):
    lower_edge: int
    upper_edge: int
    count: int


class HistogramOut(ApiModel):
    bin_width: int
    bins: list[HistogramBinOut]


class DistributionOut(ApiModel):
    abs_error: AbsErrorOut | None
    signed_error: SignedErrorOut | None
    histogram: HistogramOut


class DaySummaryOut(ApiModel):
    delivery_date: str
    cutoff: AppliedCutoffOut
    result_state: str
    expected: int
    matched: int
    mae: float | None
    rmse: float | None
    bias: float | None
    direction_counts: DirectionCountsOut


class FeaturedDayOut(ApiModel):
    kind: str
    delivery_date: str
    suggested_rule: CutoffRuleOut
    data: dict[str, Any]


class SensitivityMetricsOut(ApiModel):
    n: int
    mae: float | None
    rmse: float | None
    bias: float | None


class SensitivityOut(ApiModel):
    on_the_hour_only: SensitivityMetricsOut


class AccuracySummaryResponse(ApiModel):
    result_state: str
    query: SummaryQueryOut
    metadata: SummaryMetadataOut
    metrics: SummaryMetricsOut
    distribution: DistributionOut
    days: list[DaySummaryOut]
    featured: list[FeaturedDayOut]
    sensitivity: SensitivityOut
    warnings: list[WarningOut]


def summary_response(
    report: SummaryReport, settings: Settings, request_id: str
) -> AccuracySummaryResponse:
    summary = report.summary
    m = summary.metrics
    if summary.matched == 0:
        result_state = "EMPTY"
    elif all(day.result_state == "COMPLETE" for day in summary.days):
        result_state = "COMPLETE"
    else:
        result_state = "PARTIAL"

    response = AccuracySummaryResponse(
        result_state=result_state,
        query=SummaryQueryOut(
            from_=report.first.isoformat(),
            to=report.last.isoformat(),
            rule=rule_out(report.rule),
            rule_source=report.rule_source,
            preset_id=preset_for(report.rule),
        ),
        metadata=SummaryMetadataOut(
            contract_version=CONTRACT_VERSION,
            algorithm_version=ALGORITHM_VERSION,
            request_id=request_id,
            generated_at=format_utc(datetime.now(UTC)),
            sources=[source_out(info) for info in report.sources],
            unit=unit_summary(settings),
            resolution=ResolutionOut(),
            policy_ids=PolicyIdsOut(**POLICY_IDS),
            counts=counts_out(summary.status_counts),
            coverage=summary.matched / summary.expected if summary.expected else 0.0,
            day_count=len(summary.days),
        ),
        metrics=SummaryMetricsOut(
            n=m.n,
            mae=m.mae,
            rmse=m.rmse,
            bias=m.bias,
            direction_counts=DirectionCountsOut(over=m.over, under=m.under, exact=m.exact),
            over_share=m.over / m.n if m.n else None,
            under_share=m.under / m.n if m.n else None,
            qualified=result_state != "COMPLETE",
            unavailable_reason="NO_MATCHED_INTERVALS" if m.n == 0 else None,
        ),
        distribution=DistributionOut(
            abs_error=AbsErrorOut(**summary.abs_percentiles) if summary.abs_percentiles else None,
            signed_error=SignedErrorOut(**summary.signed_percentiles)
            if summary.signed_percentiles
            else None,
            histogram=HistogramOut(
                bin_width=HISTOGRAM_BIN_MW,
                bins=[
                    HistogramBinOut(
                        lower_edge=lower, upper_edge=lower + HISTOGRAM_BIN_MW, count=count
                    )
                    for lower, count in summary.histogram
                ],
            ),
        ),
        days=[_day_summary(day) for day in summary.days],
        featured=[
            FeaturedDayOut(
                kind=f.kind,
                delivery_date=f.delivery_date.isoformat(),
                suggested_rule=rule_out(f.rule),
                data=f.data,
            )
            for f in summary.featured
        ],
        sensitivity=SensitivityOut(on_the_hour_only=_sensitivity(summary.on_the_hour)),
        warnings=[warning_out(w) for w in report.warnings],
    )
    response.metadata.result_hash = result_hash(response.model_dump(by_alias=True))
    return response


def _day_summary(day: DayAnalysis) -> DaySummaryOut:
    m = day.metrics
    return DaySummaryOut(
        delivery_date=day.delivery_date.isoformat(),
        cutoff=cutoff_out(day.cutoff),
        result_state=day.result_state,
        expected=day.expected,
        matched=day.matched,
        mae=m.mae,
        rmse=m.rmse,
        bias=m.bias,
        direction_counts=DirectionCountsOut(over=m.over, under=m.under, exact=m.exact),
    )


def _sensitivity(m: Metrics) -> SensitivityMetricsOut:
    return SensitivityMetricsOut(n=m.n, mae=m.mae, rmse=m.rmse, bias=m.bias)
