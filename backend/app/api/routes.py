"""HTTP endpoints. Handlers only parse input, call the service and shape the response."""

from fastapi import APIRouter, Request, Response

from app.api.deps import ReplayServiceDep, SettingsDep
from app.api.params import parse_analysis_query, parse_summary_query, parse_versions_query
from app.clients.elexon import ElexonClient
from app.core.config import Settings
from app.schemas.analysis import DayAnalysisResponse, day_response
from app.schemas.export import day_csv
from app.schemas.health import LivenessResponse, ReadinessChecksOut, ReadinessResponse
from app.schemas.metadata import MetadataResponse, metadata_response
from app.schemas.summary import AccuracySummaryResponse, summary_response
from app.schemas.versions import ForecastVersionsResponse, versions_response
from app.utils.dates import format_utc

router = APIRouter(prefix="/api/v1")


@router.get("/wind-analysis", response_model=DayAnalysisResponse)
async def wind_analysis(
    request: Request,
    response: Response,
    settings: SettingsDep,
    service: ReplayServiceDep,
) -> DayAnalysisResponse:
    delivery_date, cutoff = parse_analysis_query(request.query_params, settings)
    report = await service.replay_day(delivery_date, cutoff)
    request.state.timings = {"fetch": report.fetch_ms, "analyze": report.analyze_ms}
    response.headers["Cache-Control"] = _cacheable(settings)
    return day_response(report, settings, request.state.request_id)


@router.get("/wind-analysis/export")
async def wind_analysis_export(
    request: Request, settings: SettingsDep, service: ReplayServiceDep
) -> Response:
    delivery_date, cutoff = parse_analysis_query(request.query_params, settings)
    report = await service.replay_day(delivery_date, cutoff)
    request.state.timings = {"fetch": report.fetch_ms, "analyze": report.analyze_ms}
    filename = f"wind-analysis-{delivery_date.isoformat()}-cutoff-{cutoff.utc:%Y%m%dT%H%MZ}.csv"
    return Response(
        day_csv(report),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": _cacheable(settings),
        },
    )


@router.get("/forecast-versions", response_model=ForecastVersionsResponse)
async def forecast_versions(
    request: Request, response: Response, settings: SettingsDep, service: ReplayServiceDep
) -> ForecastVersionsResponse:
    delivery_date = parse_versions_query(request.query_params, settings)
    report = await service.forecast_versions(delivery_date)
    request.state.timings = {"fetch": report.fetch_ms, "analyze": report.analyze_ms}
    response.headers["Cache-Control"] = _cacheable(settings)
    return versions_response(report, request.state.request_id)


@router.get("/accuracy-summary", response_model=AccuracySummaryResponse)
async def accuracy_summary(
    request: Request,
    response: Response,
    settings: SettingsDep,
    service: ReplayServiceDep,
) -> AccuracySummaryResponse:
    query = parse_summary_query(request.query_params, settings)
    report = await service.summarize_window(query.first, query.last, query.rule, query.rule_source)
    request.state.timings = {"fetch": report.fetch_ms, "analyze": report.analyze_ms}
    response.headers["Cache-Control"] = _cacheable(settings)
    return summary_response(report, settings, request.state.request_id)


@router.get("/metadata", response_model=MetadataResponse)
async def metadata(response: Response, settings: SettingsDep) -> MetadataResponse:
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=3600"
    return metadata_response(settings)


@router.get("/health/live", response_model=LivenessResponse)
async def liveness(response: Response) -> LivenessResponse:
    response.headers["Cache-Control"] = "no-store"
    return LivenessResponse()


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness(request: Request, response: Response) -> ReadinessResponse:
    response.headers["Cache-Control"] = "no-store"
    client: ElexonClient | None = request.app.state.elexon_client
    last_success = client.last_success_at if client else None
    last_failure = client.last_failure_at if client else None
    if last_success is None and last_failure is None:
        upstream = "UNKNOWN"
    elif last_failure is None or (last_success is not None and last_success > last_failure):
        upstream = "OK"
    else:
        upstream = "DEGRADED"
    return ReadinessResponse(
        status="READY",
        checks=ReadinessChecksOut(config="OK", upstream=upstream),
        last_upstream_success_at=format_utc(last_success) if last_success else None,
    )


def _cacheable(settings: Settings) -> str:
    """Historical analyses can be cached; the URL holds every input, so it is the cache key."""
    return (
        f"public, max-age={settings.browser_max_age_s}, s-maxage={settings.cdn_max_age_s}, "
        f"stale-while-revalidate={settings.cdn_stale_while_revalidate_s}"
    )
