"""Per-request concerns: request IDs, timing, security headers, rate limiting and access logs."""

import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from app.api.errors import ApiError, error_response

logger = logging.getLogger("app.access")

REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9-]{1,64}")
SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "frame-ancestors 'none'",
}


class RateLimiter:
    """A fixed one-minute window per client. Best effort: each server instance counts on its own."""

    def __init__(self, per_minute: int) -> None:
        self._per_minute = per_minute
        self._window = 0
        self._counts: dict[str, int] = {}

    def allow(self, client: str) -> bool:
        window = int(time.time() // 60)
        if window != self._window:
            self._window, self._counts = window, {}
        self._counts[client] = self._counts.get(client, 0) + 1
        return self._counts[client] <= self._per_minute


def add_middleware(app: FastAPI, rate_limit_per_minute: int) -> None:
    limiter = RateLimiter(rate_limit_per_minute)

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming = request.headers.get("X-Request-ID", "")
        request_id = incoming if REQUEST_ID_PATTERN.fullmatch(incoming) else uuid.uuid4().hex
        request.state.request_id = request_id
        started = time.perf_counter()

        client = request.headers.get("X-Real-IP") or (request.client.host if request.client else "")
        if request.url.path.startswith("/api/v1/health") or limiter.allow(client):
            response = await call_next(request)
        else:
            error = ApiError(
                429,
                "RATE_LIMITED",
                "Too many requests; try again shortly.",
                retryable=True,
                headers={"Retry-After": "60"},
            )
            response = error_response(request, error)

        total_ms = (time.perf_counter() - started) * 1000
        timings = getattr(request.state, "timings", {})
        response.headers["Server-Timing"] = ", ".join(
            [f"{name};dur={ms:.1f}" for name, ms in timings.items()] + [f"total;dur={total_ms:.1f}"]
        )
        response.headers["X-Request-ID"] = request_id
        response.headers.update(SECURITY_HEADERS)
        logger.info(
            "%s %s %s %.0fms id=%s",
            request.method,
            request.url.path,
            response.status_code,
            total_ms,
            request_id,
        )
        return response
