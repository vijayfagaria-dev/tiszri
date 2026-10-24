"""Failures raised below the API layer. The API maps each one to a stable error code."""


class InvariantError(Exception):
    """An analysis broke a guarantee of the API contract. Raised instead of returning bad data."""


class UpstreamError(Exception):
    retryable = False


class UpstreamTimeoutError(UpstreamError):
    retryable = True


class UpstreamUnavailableError(UpstreamError):
    retryable = True


class UpstreamRateLimitError(UpstreamError):
    retryable = True

    def __init__(self, message: str, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class UpstreamRejectedError(UpstreamError):
    """The source answered 4xx; repeating the same request will not help."""


class UpstreamMalformedError(UpstreamError):
    """The source answered with a payload we cannot use."""
