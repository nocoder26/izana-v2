"""
Request correlation ID management.

Generates a unique UUID4 correlation ID for each incoming request, stores it
in a ``contextvars.ContextVar`` so it is accessible from any layer of the
application (services, repositories, background tasks), and returns it in
the ``X-Correlation-ID`` response header for client-side tracing.
"""

import uuid
from contextvars import ContextVar
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# ── ContextVar ────────────────────────────────────────────────────────────
_correlation_id_var: ContextVar[Optional[str]] = ContextVar(
    "correlation_id", default=None
)

CORRELATION_HEADER = "X-Correlation-ID"


def get_correlation_id() -> Optional[str]:
    """Return the correlation ID for the current execution context.

    Returns:
        The UUID4 string if a request is in progress, otherwise ``None``.
    """
    return _correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """Explicitly set the correlation ID for the current execution context.

    This is useful for background workers or tasks that receive a
    correlation ID from an upstream caller (e.g. a queue message).

    Args:
        correlation_id: The correlation ID string to store.
    """
    _correlation_id_var.set(correlation_id)


# ── Middleware ────────────────────────────────────────────────────────────


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that attaches a correlation ID to every request.

    If the incoming request already carries an ``X-Correlation-ID`` header
    (e.g. from an API gateway), it is reused.  Otherwise a fresh UUID4 is
    generated.  The ID is stored in a ``ContextVar`` and echoed back in the
    response headers.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request, injecting a correlation ID."""
        # Honour an existing header (gateway / upstream service) or generate.
        correlation_id: str = request.headers.get(
            CORRELATION_HEADER, str(uuid.uuid4())
        )
        _correlation_id_var.set(correlation_id)

        response: Response = await call_next(request)
        response.headers[CORRELATION_HEADER] = correlation_id
        return response
