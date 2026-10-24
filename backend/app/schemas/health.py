"""Response models for the health endpoints."""

from app.schemas.common import ApiModel


class LivenessResponse(ApiModel):
    status: str = "OK"


class ReadinessChecksOut(ApiModel):
    config: str
    upstream: str  # OK, UNKNOWN or DEGRADED


class ReadinessResponse(ApiModel):
    status: str
    checks: ReadinessChecksOut
    last_upstream_success_at: str | None
