from __future__ import annotations

from typing import Any


class LeadpushError(Exception):
    """Base exception raised by the Leadpush SDK."""

    def __init__(self, message: str, *, status: int | None = None, response: Any = None) -> None:
        super().__init__(message)
        self.status = status
        self.response = response


class ApiError(LeadpushError):
    """Raised when the Leadpush API returns a non-success status."""

    def __init__(self, status: int, response: Any = None) -> None:
        super().__init__(
            f"Leadpush API request failed with status {status}.",
            status=status,
            response=response,
        )


class UnauthorizedError(ApiError):
    """Raised when an API request is unauthenticated."""

    def __init__(self, response: Any = None) -> None:
        super().__init__(401, response)
        self.args = ("Unauthorized. Check your Leadpush API key.",)


class ForbiddenError(ApiError):
    """Raised when the API rejects an authenticated request."""

    def __init__(self, response: Any = None) -> None:
        super().__init__(403, response)


class NotFoundError(ApiError):
    """Raised when an API resource cannot be found."""

    def __init__(self, response: Any = None) -> None:
        super().__init__(404, response)


class ValidationError(ApiError):
    """Raised when the API rejects request validation."""

    def __init__(self, response: Any = None) -> None:
        super().__init__(422, response)


class TimeoutError(LeadpushError):
    """Raised when a Leadpush API request times out."""

    def __init__(self, timeout: float | None) -> None:
        self.timeout = timeout
        label = "the configured timeout" if timeout is None else f"{timeout:g}s"
        super().__init__(f"Leadpush API request timed out after {label}.")


class UnsupportedEndpointError(LeadpushError):
    """Raised when a resource does not support an SDK operation."""


class DetachedModelError(LeadpushError):
    """Raised when an attached-model operation is used on a standalone model."""

    def __init__(self) -> None:
        super().__init__("This model is not attached to an API client.")
