"""
Groq API client with multi-key rotation and circuit breaking.

Manages multiple Groq API keys (from settings.GROQ_API_KEYS), rotates through
them round-robin, and applies per-key circuit breakers that open after 3
consecutive failures and reset after 60 seconds.

Uses asyncio.Semaphore to limit concurrent requests (settings.GROQ_MAX_CONCURRENT_REQUESTS).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from groq import APIError, Groq, RateLimitError

from app.core.config import settings
from app.core.exceptions import AllKeysExhaustedError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------


class CircuitBreaker:
    """Per-key circuit breaker that opens after consecutive failures.

    Once the breaker opens it stays open for ``reset_timeout`` seconds,
    during which the associated key is skipped.  After the timeout elapses
    the breaker moves to *half-open* (``is_open`` returns ``False``), and a
    single success will fully close it again.

    Attributes:
        failure_threshold: Number of consecutive failures before opening.
        reset_timeout: Seconds to wait before allowing another attempt.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        reset_timeout: float = 60.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._failure_count: int = 0
        self._last_failure_time: float | None = None

    # -- mutations ----------------------------------------------------------

    def record_failure(self) -> None:
        """Record a single failure and potentially open the breaker."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

    def record_success(self) -> None:
        """Reset the breaker on a successful call."""
        self._failure_count = 0
        self._last_failure_time = None

    # -- state queries ------------------------------------------------------

    @property
    def is_open(self) -> bool:
        """Return ``True`` if the breaker is open and the key should be skipped.

        The breaker is considered open when the failure count has reached the
        threshold **and** the reset timeout has *not* yet elapsed.  Once the
        timeout passes the breaker is half-open and ``is_open`` returns
        ``False`` to allow a probe request.
        """
        if self._failure_count < self.failure_threshold:
            return False
        # Breaker has tripped — check whether the cooldown has elapsed.
        if self._last_failure_time is None:
            return False
        elapsed = time.monotonic() - self._last_failure_time
        return elapsed < self.reset_timeout


# ---------------------------------------------------------------------------
# Groq Client Manager
# ---------------------------------------------------------------------------


class GroqClientManager:
    """Manages a pool of Groq API keys with round-robin rotation and
    per-key circuit breaking.

    The manager creates one :class:`groq.Groq` client per API key and
    rotates through them on successive calls.  Keys whose circuit breaker
    is open are skipped.  An :class:`asyncio.Semaphore` caps the number of
    concurrent in-flight requests to avoid overwhelming the upstream API.

    Args:
        keys: Explicit list of API keys.  When ``None`` (the default) the
              keys are read from ``settings.get_groq_keys()``.
        max_concurrent: Maximum number of concurrent requests.  When
                        ``None`` the value is taken from
                        ``settings.GROQ_MAX_CONCURRENT_REQUESTS``.
        failure_threshold: Consecutive failures before a key is
                           circuit-broken.
        reset_timeout: Seconds before a circuit-broken key is retried.
    """

    def __init__(
        self,
        keys: list[str] | None = None,
        max_concurrent: int | None = None,
        failure_threshold: int = 3,
        reset_timeout: float = 60.0,
    ) -> None:
        self._keys: list[str] = keys or settings.get_groq_keys()
        if not self._keys:
            raise ValueError("At least one Groq API key must be configured.")

        self._clients: dict[str, Groq] = {
            key: Groq(api_key=key) for key in self._keys
        }
        self._breakers: dict[str, CircuitBreaker] = {
            key: CircuitBreaker(
                failure_threshold=failure_threshold,
                reset_timeout=reset_timeout,
            )
            for key in self._keys
        }
        self._semaphore = asyncio.Semaphore(
            max_concurrent or settings.GROQ_MAX_CONCURRENT_REQUESTS
        )
        self._current_index: int = 0

    # -- key selection ------------------------------------------------------

    def _get_client(self) -> Groq:
        """Select the next healthy Groq client via round-robin.

        Skips keys whose circuit breaker is currently open.

        Returns:
            A :class:`groq.Groq` client instance bound to a healthy key.

        Raises:
            AllKeysExhaustedError: Every configured key is circuit-broken.
        """
        total_keys = len(self._keys)
        for _ in range(total_keys):
            key = self._keys[self._current_index % total_keys]
            self._current_index = (self._current_index + 1) % total_keys
            if not self._breakers[key].is_open:
                return self._clients[key]
        raise AllKeysExhaustedError(
            "All Groq API keys are circuit-broken. Please wait and retry."
        )

    def _current_key(self) -> str:
        """Return the key that will be used by the *next* ``_get_client`` call.

        Used internally for circuit-breaker bookkeeping.
        """
        # The index was already advanced by ``_get_client``, so look back one
        # position to find the key that was actually returned.
        idx = (self._current_index - 1) % len(self._keys)
        return self._keys[idx]

    # -- public API ---------------------------------------------------------

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> Any:
        """Execute a chat completion request with automatic key rotation.

        Acquires the concurrency semaphore, then tries up to 3 keys (or
        fewer if not enough are configured).  On ``RateLimitError`` or
        ``APIError`` the failure is recorded on the current key's circuit
        breaker and the next key is tried after an exponential back-off.

        Args:
            messages: The chat messages to send.
            model: The model identifier (e.g. ``"llama-3.3-70b-versatile"``).
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in the response.
            **kwargs: Forwarded to ``Groq.chat.completions.create``.

        Returns:
            The raw ``ChatCompletion`` response object from the Groq SDK.

        Raises:
            AllKeysExhaustedError: If all keys are broken and no attempt
                                   can be made.
            RateLimitError: If all retry attempts are exhausted.
            APIError: If a non-retryable API error is raised on the last
                      attempt.
        """
        max_attempts = min(3, len(self._keys))
        last_exception: Exception | None = None

        async with self._semaphore:
            for attempt in range(max_attempts):
                client = self._get_client()
                key = self._current_key()

                try:
                    response = await asyncio.to_thread(
                        client.chat.completions.create,
                        messages=messages,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs,
                    )
                    self._breakers[key].record_success()
                    return response

                except (RateLimitError, APIError) as exc:
                    last_exception = exc
                    self._breakers[key].record_failure()

                    masked_key = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"
                    logger.warning(
                        "Groq key rotated due to %s (key=%s, attempt=%d/%d)",
                        type(exc).__name__,
                        masked_key,
                        attempt + 1,
                        max_attempts,
                        extra={
                            "swarm_event": "key_rotation",
                            "error_type": type(exc).__name__,
                            "attempt": attempt + 1,
                        },
                    )

                    # Exponential back-off: 0.5s, 1s, 2s ...
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(0.5 * (2**attempt))

        # All attempts failed — re-raise the last exception so the caller
        # can decide how to handle it.
        if last_exception is not None:
            raise last_exception
        raise AllKeysExhaustedError("All Groq API key attempts failed.")


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

groq_manager = GroqClientManager()
