"""Error envelope returned by every non-2xx response."""

from app.schemas.common import ApiModel


class ErrorDetailOut(ApiModel):
    field: str | None
    reason: str
    message: str


class ErrorBodyOut(ApiModel):
    code: str
    message: str
    details: list[ErrorDetailOut]
    request_id: str
    retryable: bool


class ErrorEnvelope(ApiModel):
    error: ErrorBodyOut
