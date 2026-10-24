"""End-to-end API behaviour on recorded data, with every response checked against the contract."""

import csv
from datetime import date, datetime

import httpx
import pytest

from app.clients.base import SourceResult
from app.core.config import Settings
from app.core.errors import (
    UpstreamError,
    UpstreamMalformedError,
    UpstreamRateLimitError,
    UpstreamRejectedError,
    UpstreamTimeoutError,
    UpstreamUnavailableError,
)
from app.main import create_app
from tests.support import contract_errors

pytestmark = pytest.mark.req("API-001", "API-003", "API-004", "API-007")


async def get(client: httpx.AsyncClient, path: str, **params: str) -> httpx.Response:
    return await client.get(f"/api/v1{path}", params=params)


@pytest.mark.req("FR-018", "FR-019", "AC-009")
async def test_metadata(client: httpx.AsyncClient) -> None:
    response = await get(client, "/metadata")
    body = response.json()
    assert response.status_code == 200
    assert contract_errors(body, "AppMetadata") == []
    assert body["supportedDeliveryWindow"] == {"from": "2026-01-01", "to": "2026-02-01"}
    assert body["cutoff"]["defaultRule"] == {"dayOffset": -1, "localTime": "09:00"}
    defaults = [p["id"] for p in body["cutoff"]["presets"] if p["isDefault"]]
    assert defaults == ["MORNING_BEFORE_0900"]


class TestWindAnalysis:
    @pytest.mark.req("FR-008", "AC-002")
    async def test_default_decision_time(self, client: httpx.AsyncClient) -> None:
        response = await get(client, "/wind-analysis", deliveryDate="2026-01-16")
        body = response.json()
        assert response.status_code == 200
        assert contract_errors(body, "DayAnalysis") == []
        cutoff = body["query"]["decisionCutoff"]
        assert cutoff["source"] == "DEFAULT"
        assert cutoff["utc"] == "2026-01-15T09:00:00Z"
        assert cutoff["presetId"] == "MORNING_BEFORE_0900"
        assert body["metrics"]["mae"] == pytest.approx(800.542, abs=5e-4)
        assert body["highlights"]["versionsUsed"] == ["2026-01-15T07:30:00Z"]

    @pytest.mark.req("FR-013", "FR-020", "FR-021", "AC-009", "AC-011")
    async def test_noon_preset_shows_the_late_forecast(self, client: httpx.AsyncClient) -> None:
        response = await get(
            client,
            "/wind-analysis",
            deliveryDate="2026-01-16",
            cutoffDayOffset="-1",
            cutoffLocalTime="12:00",
        )
        body = response.json()
        assert contract_errors(body, "DayAnalysis") == []
        assert body["resultState"] == "COMPLETE"
        assert body["query"]["decisionCutoff"]["presetId"] == "NOON_BEFORE_1200"
        assert body["metadata"]["counts"]["byStatus"]["MATCHED"] == 48
        assert body["metadata"]["sources"][1]["versions"] == {
            "coveringDay": 32,
            "eligible": 12,
            "afterCutoff": 20,
        }
        assert body["highlights"]["newerVersionAfterCutoff"] == "2026-01-15T12:25:00Z"

        sp44 = body["intervals"][43]
        assert sp44["settlementPeriod"] == 44
        assert sp44["forecast"] == {
            "generation": 10850,
            "publishTime": "2026-01-15T09:30:00Z",
            "periodStart": "2026-01-16T21:00:00Z",
            "periodEnd": "2026-01-16T22:00:00Z",
            "leadMinutes": 2160,
            "ageAtCutoffMinutes": 150,
        }
        assert sp44["error"] == {"signed": 2606, "absolute": 2606, "direction": "OVER"}
        assert sp44["selection"]["eligibleCount"] == 12

    @pytest.mark.req("NFR-003")
    async def test_metrics_can_be_recomputed_from_the_intervals(
        self, client: httpx.AsyncClient
    ) -> None:
        body = (await get(client, "/wind-analysis", deliveryDate="2026-01-28")).json()
        errors = [i["error"]["signed"] for i in body["intervals"] if i["error"]]
        assert len(errors) == body["metrics"]["n"]
        assert body["metrics"]["mae"] == pytest.approx(sum(abs(e) for e in errors) / len(errors))
        assert body["metrics"]["bias"] == pytest.approx(sum(errors) / len(errors))

    @pytest.mark.req("FR-008", "AC-002", "AC-013")
    async def test_explicit_cutoff_with_offset(self, client: httpx.AsyncClient) -> None:
        response = await get(
            client,
            "/wind-analysis",
            deliveryDate="2026-01-16",
            decisionCutoff="2026-01-15T12:00:00+00:00",
        )
        cutoff = response.json()["query"]["decisionCutoff"]
        assert (cutoff["source"], cutoff["utc"], cutoff["london"]) == (
            "EXPLICIT",
            "2026-01-15T12:00:00Z",
            "2026-01-15T12:00:00+00:00",
        )

    @pytest.mark.req("FR-024", "FR-025", "API-008")
    async def test_partial_day(self, client: httpx.AsyncClient) -> None:
        body = (
            await get(
                client,
                "/wind-analysis",
                deliveryDate="2026-01-15",
                cutoffDayOffset="-2",
                cutoffLocalTime="09:00",
            )
        ).json()
        assert contract_errors(body, "DayAnalysis") == []
        assert (body["resultState"], body["metrics"]["qualified"]) == ("PARTIAL", True)
        assert body["metadata"]["coverage"] == pytest.approx(44 / 48)
        sp45 = body["intervals"][44]
        assert sp45["status"] == "FORECAST_NOT_YET_PUBLISHED"
        assert sp45["forecast"] is None
        assert sp45["actual"]["generation"] == 7685
        assert sp45["selection"]["earliestLaterPublishTime"] == "2026-01-14T02:30:00Z"
        assert "PARTIAL_COVERAGE" in [w["code"] for w in body["warnings"]]

    @pytest.mark.req("FR-026")
    async def test_empty_day(self, client: httpx.AsyncClient) -> None:
        response = await get(
            client,
            "/wind-analysis",
            deliveryDate="2026-01-15",
            cutoffDayOffset="-3",
            cutoffLocalTime="09:00",
        )
        body = response.json()
        assert response.status_code == 200
        assert contract_errors(body, "DayAnalysis") == []
        assert body["resultState"] == "EMPTY"
        assert body["metrics"]["mae"] is None
        assert body["metrics"]["unavailableReason"] == "NO_MATCHED_INTERVALS"

    async def test_hindsight_replay(self, client: httpx.AsyncClient) -> None:
        body = (
            await get(
                client,
                "/wind-analysis",
                deliveryDate="2026-01-16",
                cutoffDayOffset="1",
                cutoffLocalTime="00:00",
            )
        ).json()
        assert body["query"]["decisionCutoff"]["position"] == "AFTER_DELIVERY"
        assert "HINDSIGHT_CUTOFF" in [w["code"] for w in body["warnings"]]

    @pytest.mark.req("NFR-006")
    async def test_headers(self, client: httpx.AsyncClient) -> None:
        response = await client.get(
            "/api/v1/wind-analysis",
            params={"deliveryDate": "2026-01-16"},
            headers={"X-Request-ID": "abc-123"},
        )
        assert response.headers["X-Request-ID"] == "abc-123"
        assert response.json()["metadata"]["requestId"] == "abc-123"
        assert "s-maxage=" in response.headers["Cache-Control"]
        timing = response.headers["Server-Timing"]
        assert all(part in timing for part in ("fetch;dur=", "analyze;dur=", "total;dur="))
        assert response.headers["X-Content-Type-Options"] == "nosniff"


async def test_accuracy_summary(client: httpx.AsyncClient) -> None:
    response = await get(client, "/accuracy-summary")
    body = response.json()
    assert response.status_code == 200
    assert contract_errors(body, "AccuracySummary") == []
    assert body["query"]["from"] == "2026-01-02"
    assert body["query"]["ruleSource"] == "DEFAULT"
    assert body["metadata"]["dayCount"] == 31
    assert body["metrics"]["mae"] == pytest.approx(2041.958, abs=5e-4)
    assert body["metrics"]["overShare"] == pytest.approx(1261 / 1488)
    assert body["distribution"]["absError"] == {"p50": 1686, "p90": 4145, "p95": 5316}
    assert sum(b["count"] for b in body["distribution"]["histogram"]["bins"]) == 1488
    assert [f["kind"] for f in body["featured"]] == [
        "WORST_DAY",
        "BEST_DAY",
        "BIAS_HIDES_ERROR",
        "OFF_SCHEDULE_VINTAGE",
    ]
    assert body["sensitivity"]["onTheHourOnly"]["n"] == 744


@pytest.mark.req("API-002", "FR-004", "AC-001", "NFR-016")
@pytest.mark.parametrize(
    ("path", "params", "code", "reason"),
    [
        ("/wind-analysis", {}, "INVALID_DELIVERY_DATE", "MISSING"),
        ("/wind-analysis", {"deliveryDate": "16/01/2026"}, "INVALID_DELIVERY_DATE", "UNPARSEABLE"),
        ("/wind-analysis", {"deliveryDate": "2026-02-02"}, "INVALID_DELIVERY_DATE", "OUT_OF_RANGE"),
        (
            "/wind-analysis",
            {"deliveryDate": "2026-01-16", "decisionCutoff": "2026-01-15T09:00:00"},
            "INVALID_CUTOFF",
            "TIMEZONE_REQUIRED",
        ),
        (
            "/wind-analysis",
            {"deliveryDate": "2026-01-16", "decisionCutoff": "2026-01-15T09:00:00.5Z"},
            "INVALID_CUTOFF",
            "FRACTIONAL_SECONDS",
        ),
        (
            "/wind-analysis",
            {"deliveryDate": "2026-01-16", "decisionCutoff": "2026-01-15T09:00:00 00:00"},
            "INVALID_CUTOFF",
            "UNPARSEABLE",
        ),
        (
            "/wind-analysis",
            {
                "deliveryDate": "2026-01-16",
                "decisionCutoff": "2026-01-15T09:00:00Z",
                "cutoffDayOffset": "-1",
                "cutoffLocalTime": "09:00",
            },
            "INVALID_PARAMETER",
            "MUTUALLY_EXCLUSIVE",
        ),
        (
            "/wind-analysis",
            {"deliveryDate": "2026-01-16", "cutoffDayOffset": "-1"},
            "INVALID_PARAMETER",
            "INCOMPLETE_PAIR",
        ),
        (
            "/wind-analysis",
            {"deliveryDate": "2026-01-16", "cutoffDayOffset": "-9", "cutoffLocalTime": "09:00"},
            "INVALID_CUTOFF_RULE",
            "DAY_OFFSET_OUT_OF_RANGE",
        ),
        (
            "/wind-analysis",
            {"deliveryDate": "2026-01-16", "cutoffDayOffset": "-1", "cutoffLocalTime": "9am"},
            "INVALID_CUTOFF_RULE",
            "TIME_UNPARSEABLE",
        ),
        (
            "/wind-analysis",
            {"deliveryDate": "2026-01-16", "cutoffDayOffset": "2", "cutoffLocalTime": "01:00"},
            "CUTOFF_OUT_OF_RANGE",
            "AFTER_RANGE",
        ),
        (
            "/wind-analysis",
            {"deliveryDate": "2026-01-16", "decisionCutoff": "2026-01-01T00:00:00Z"},
            "CUTOFF_OUT_OF_RANGE",
            "BEFORE_RANGE",
        ),
        (
            "/wind-analysis",
            {"deliveryDate": "2026-01-16", "colour": "blue"},
            "INVALID_PARAMETER",
            "UNKNOWN_PARAMETER",
        ),
        (
            "/wind-analysis",
            {"deliveryDate": "2026-01-16", "decisionCutoff": "x" * 65},
            "INVALID_PARAMETER",
            "TOO_LONG",
        ),
        ("/accuracy-summary", {"from": "2026-01-10"}, "INVALID_PARAMETER", "INCOMPLETE_PAIR"),
        (
            "/accuracy-summary",
            {"from": "2026-01-10", "to": "2026-01-05"},
            "INVALID_DATE_RANGE",
            "FROM_AFTER_TO",
        ),
        (
            "/accuracy-summary",
            {"from": "2025-12-31", "to": "2026-01-05"},
            "INVALID_DATE_RANGE",
            "OUT_OF_RANGE",
        ),
    ],
)
async def test_validation_errors(
    client: httpx.AsyncClient, path: str, params: dict[str, str], code: str, reason: str
) -> None:
    response = await client.get(f"/api/v1{path}", params=params)
    body = response.json()
    assert response.status_code == 422
    assert contract_errors(body, "ErrorEnvelope") == []
    assert body["error"]["code"] == code
    assert reason in [d["reason"] for d in body["error"]["details"]]
    assert body["error"]["retryable"] is False
    assert response.headers["Cache-Control"] == "no-store"


async def test_duplicate_parameter(client: httpx.AsyncClient) -> None:
    response = await client.get(
        "/api/v1/wind-analysis?deliveryDate=2026-01-16&deliveryDate=2026-01-17"
    )
    assert response.json()["error"]["details"][0]["reason"] == "DUPLICATE_PARAMETER"


async def test_unknown_route_and_method(client: httpx.AsyncClient) -> None:
    missing = await client.get("/api/v1/nope")
    assert (missing.status_code, missing.json()["error"]["code"]) == (404, "NOT_FOUND")
    wrong_method = await client.post("/api/v1/metadata")
    assert (wrong_method.status_code, wrong_method.json()["error"]["code"]) == (
        405,
        "METHOD_NOT_ALLOWED",
    )


class FailingSource:
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def fetch_actuals(self, first: date, last: date) -> SourceResult:
        raise self.error

    async def fetch_forecasts(
        self, published_from: datetime, published_to: datetime
    ) -> SourceResult:
        raise self.error


@pytest.mark.req("API-005", "API-006", "NFR-004")
@pytest.mark.parametrize(
    ("error", "status", "code", "retryable"),
    [
        (UpstreamTimeoutError("slow"), 504, "UPSTREAM_TIMEOUT", True),
        (UpstreamUnavailableError("down"), 502, "UPSTREAM_UNAVAILABLE", True),
        (UpstreamRateLimitError("busy", retry_after=30), 503, "UPSTREAM_RATE_LIMITED", True),
        (
            UpstreamRejectedError("400 at /datasets/WINDFOR"),
            502,
            "UPSTREAM_REJECTED_REQUEST",
            False,
        ),
        (UpstreamMalformedError("bad json"), 502, "UPSTREAM_MALFORMED_RESPONSE", False),
        (RuntimeError("boom"), 500, "INTERNAL_ERROR", False),
    ],
)
async def test_upstream_and_internal_failures(
    settings: Settings, error: Exception, status: int, code: str, retryable: bool
) -> None:
    app = create_app(settings, source=FailingSource(error))
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/wind-analysis", params={"deliveryDate": "2026-01-16"})
    body = response.json()
    assert response.status_code == status
    assert contract_errors(body, "ErrorEnvelope") == []
    assert (body["error"]["code"], body["error"]["retryable"]) == (code, retryable)
    assert "/datasets" not in body["error"]["message"]  # no upstream details leak to clients
    if isinstance(error, UpstreamRateLimitError):
        assert response.headers["Retry-After"] == "30"
    assert isinstance(error, UpstreamError) or code == "INTERNAL_ERROR"


async def test_health(client: httpx.AsyncClient) -> None:
    live = await client.get("/api/v1/health/live")
    ready = await client.get("/api/v1/health/ready")
    assert contract_errors(live.json(), "Liveness") == []
    assert contract_errors(ready.json(), "Readiness") == []
    assert ready.json()["checks"] == {"config": "OK", "upstream": "UNKNOWN"}


async def test_rate_limit(settings: Settings) -> None:
    app = create_app(settings.model_copy(update={"rate_limit_per_minute": 2}))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        statuses = [(await client.get("/api/v1/metadata")).status_code for _ in range(3)]
    assert statuses == [200, 200, 429]


async def test_forecast_versions(client: httpx.AsyncClient) -> None:
    response = await get(client, "/forecast-versions", deliveryDate="2026-01-16")
    body = response.json()
    assert response.status_code == 200
    assert contract_errors(body, "ForecastVersions") == []
    assert len(body["periods"]) == 24
    assert len(body["versions"]) == 32
    assert "s-maxage=" in response.headers["Cache-Control"]


@pytest.mark.req("FR-013")
async def test_versions_agree_with_the_replay(client: httpx.AsyncClient) -> None:
    """The forecast a replay selects must be the same value the versions view shows."""
    versions = (await get(client, "/forecast-versions", deliveryDate="2026-01-16")).json()
    replay = (
        await get(
            client,
            "/wind-analysis",
            deliveryDate="2026-01-16",
            cutoffDayOffset="-1",
            cutoffLocalTime="12:00",
        )
    ).json()
    by_publish = {v["publishTime"]: v["values"] for v in versions["versions"]}
    for interval in replay["intervals"]:
        forecast = interval["forecast"]
        hour = versions["periods"].index(forecast["periodStart"])
        assert by_publish[forecast["publishTime"]][hour] == forecast["generation"]


async def test_forecast_versions_rejects_a_cutoff(client: httpx.AsyncClient) -> None:
    response = await get(
        client,
        "/forecast-versions",
        deliveryDate="2026-01-16",
        decisionCutoff="2026-01-15T09:00:00Z",
    )
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["reason"] == "UNKNOWN_PARAMETER"


async def test_csv_export(client: httpx.AsyncClient) -> None:
    response = await get(
        client,
        "/wind-analysis/export",
        deliveryDate="2026-01-16",
        cutoffDayOffset="-1",
        cutoffLocalTime="12:00",
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/csv")
    assert response.headers["Content-Disposition"] == (
        'attachment; filename="wind-analysis-2026-01-16-cutoff-20260115T1200Z.csv"'
    )
    lines = response.text.splitlines()
    context = [line for line in lines if line.startswith("#")]
    assert "# decisionCutoffUtc=2026-01-15T12:00:00Z" in context
    rows = list(csv.DictReader(line for line in lines if not line.startswith("#")))
    assert len(rows) == 48
    sp44 = rows[43]
    assert (sp44["forecastMW"], sp44["actualMW"], sp44["errorMW"], sp44["direction"]) == (
        "10850",
        "8244",
        "2606",
        "OVER",
    )
    assert sp44["forecastPublishTime"] == "2026-01-15T09:30:00Z"


async def test_csv_export_leaves_missing_values_blank(client: httpx.AsyncClient) -> None:
    response = await get(
        client,
        "/wind-analysis/export",
        deliveryDate="2026-01-15",
        cutoffDayOffset="-2",
        cutoffLocalTime="09:00",
    )
    rows = list(
        csv.DictReader(line for line in response.text.splitlines() if not line.startswith("#"))
    )
    sp45 = rows[44]
    assert (sp45["status"], sp45["forecastMW"], sp45["errorMW"]) == (
        "FORECAST_NOT_YET_PUBLISHED",
        "",
        "",
    )
    assert sp45["actualMW"] == "7685"


async def test_csv_export_validates_like_the_replay(client: httpx.AsyncClient) -> None:
    response = await get(client, "/wind-analysis/export", deliveryDate="2026-03-01")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_DELIVERY_DATE"
