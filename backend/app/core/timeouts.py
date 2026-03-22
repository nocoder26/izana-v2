"""
Operation timeout configuration and helpers.

Centralises timeout values for every category of external or long-running
operation so they can be tuned in one place.  The ``with_timeout`` async
context manager wraps ``asyncio.timeout`` (Python 3.11+) and raises a
descriptive ``TimeoutError`` on expiry.

Usage::

    from app.core.timeouts import LLM_CALL_TIMEOUT, with_timeout

    async with with_timeout(LLM_CALL_TIMEOUT, "groq_chat_completion"):
        response = await groq_client.chat(...)
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

# ── Timeout constants (seconds) ──────────────────────────────────────────

LLM_CALL_TIMEOUT: float = 30.0
"""Maximum wait for a single LLM completion call (Groq / OpenAI)."""

EMBEDDING_TIMEOUT: float = 15.0
"""Maximum wait for an embedding generation request."""

DB_QUERY_TIMEOUT: float = 10.0
"""Maximum wait for a Supabase / Postgres query."""

FILE_UPLOAD_TIMEOUT: float = 60.0
"""Maximum wait for a file upload (bloodwork PDF, images)."""

SSE_STREAM_TIMEOUT: float = 120.0
"""Maximum idle time for a Server-Sent Events stream."""

REDIS_OPERATION_TIMEOUT: float = 5.0
"""Maximum wait for a single Redis command."""


# ── Async context manager ────────────────────────────────────────────────


@asynccontextmanager
async def with_timeout(
    seconds: float, operation_name: str
) -> AsyncIterator[None]:
    """Execute the enclosed block with an enforced timeout.

    On expiry a ``TimeoutError`` is raised whose message includes the
    *operation_name* and the configured *seconds* so that logs and error
    handlers immediately show which operation timed out and what the
    limit was.

    Args:
        seconds:        Maximum number of seconds to wait.
        operation_name: Human-readable name of the operation (used in the
                        error message).

    Yields:
        Control to the caller's ``async with`` block.

    Raises:
        TimeoutError: If the block does not complete within *seconds*.

    Example::

        async with with_timeout(10, "fetch_user_profile"):
            profile = await db.get_profile(user_id)
    """
    try:
        async with asyncio.timeout(seconds):
            yield
    except asyncio.TimeoutError:
        raise TimeoutError(
            f"Operation '{operation_name}' timed out after {seconds}s"
        ) from None
