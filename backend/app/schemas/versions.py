"""Response model for GET /forecast-versions."""

from datetime import UTC, datetime

from app.schemas.common import (
    ALGORITHM_VERSION,
    CONTRACT_VERSION,
    ApiModel,
    SourceOut,
    WarningOut,
    source_out,
    warning_out,
)
from app.services.replay_service import VersionsReport
from app.utils.dates import format_utc


class VersionsQueryOut(ApiModel):
    delivery_date: str
    business_timezone: str = "Europe/London"


class VersionsMetadataOut(ApiModel):
    contract_version: str
    algorithm_version: str
    request_id: str
    generated_at: str
    sources: list[SourceOut]


class ForecastVersionOut(ApiModel):
    publish_time: str
    values: list[int | None]


class ForecastVersionsResponse(ApiModel):
    query: VersionsQueryOut
    metadata: VersionsMetadataOut
    periods: list[str]
    versions: list[ForecastVersionOut]
    warnings: list[WarningOut]


def versions_response(report: VersionsReport, request_id: str) -> ForecastVersionsResponse:
    return ForecastVersionsResponse(
        query=VersionsQueryOut(delivery_date=report.delivery_date.isoformat()),
        metadata=VersionsMetadataOut(
            contract_version=CONTRACT_VERSION,
            algorithm_version=ALGORITHM_VERSION,
            request_id=request_id,
            generated_at=format_utc(datetime.now(UTC)),
            sources=[source_out(report.source)],
        ),
        periods=[format_utc(hour) for hour in report.hours],
        versions=[
            ForecastVersionOut(publish_time=format_utc(v.publish_time), values=v.values)
            for v in report.versions
        ],
        warnings=[warning_out(w) for w in report.warnings],
    )
