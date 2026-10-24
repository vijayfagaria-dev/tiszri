"""Map every failure to the contract's error envelope, in one place."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.core.errors import (
    UpstreamError,
    UpstreamMalformedError,
    UpstreamRateLimitError,
    UpstreamRejectedError,
    UpstreamTimeoutError,
    UpstreamUnavailableError,
)
from app.schemas.errors import ErrorBodyOut, ErrorDetailOut, ErrorEnvelope

logger = logging.getLogger(__name__)

# Messages shown to clients never include upstream URLs or internal details.
UPSTREAM_ERRORS: dict[type[UpstreamError], tuple[int, str, str]] = {
    UpstreamTimeoutError: (
        504,
        "UPSTREAM_TIMEOUT",
        "The Elexon data service did not respond in time.",
    ),
    UpstreamUnavailableError: (
        502,
        "UPSTREAM_UNAVAILABLE",
        "The Elexon data service is unavailable.",
    ),
    UpstreamRateLimitError: (503, "UPSTREAM_RATE_LIMITED", "The Elexon data service is busy."),
    UpstreamRejectedError: (
        502,
        "UPSTREAM_REJECTED_REQUEST",
        "The Elexon data service rejected the request.",
    ),
    UpstreamMalformedError: (
        502,
        "UPSTREAM_MALFORMED_RESPONSE",
        "The Elexon data service returned unusable data.",
    ),
}


class ApiError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        details: list[ErrorDetailOut] | None = None,
        retryable: bool = False,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details or []
        self.retryable = retryable
        self.headers = headers or {}


def error_response(request: Request, error: ApiError) -> JSONResponse:
    body = ErrorEnvelope(
        error=ErrorBodyOut(
            code=error.code,
            message=error.message,
            details=error.details,
            request_id=getattr(request.state, "request_id", ""),
            retryable=error.retryable,
        )
    )
    headers = {"Cache-Control": "no-store", **error.headers}
    return JSONResponse(body.model_dump(by_alias=True), status_code=error.status, headers=headers)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, error: ApiError) -> JSONResponse:
        return error_response(request, error)

    @app.exception_handler(UpstreamError)
    async def handle_upstream_error(request: Request, error: UpstreamError) -> JSONResponse:
        status, code, message = UPSTREAM_ERRORS.get(
            type(error), (502, "UPSTREAM_UNAVAILABLE", "The Elexon data service is unavailable.")
        )
        logger.warning("Upstream failure (%s): %s", code, error)
        headers = {}
        if isinstance(error, UpstreamRateLimitError) and error.retry_after:
            headers["Retry-After"] = str(error.retry_after)
        return error_response(
            request, ApiError(status, code, message, retryable=error.retryable, headers=headers)
        )

    @app.exception_handler(HTTPException)
    async def handle_http_error(request: Request, error: HTTPException) -> JSONResponse:
        if error.status_code == 405:
            return error_response(
                request, ApiError(405, "METHOD_NOT_ALLOWED", "Method not allowed.")
            )
        return error_response(request, ApiError(404, "NOT_FOUND", "No such endpoint."))

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, error: Exception) -> JSONResponse:
        logger.exception("Unhandled error", exc_info=error)
        return error_response(
            request, ApiError(500, "INTERNAL_ERROR", "Something went wrong on our side.")
        )
