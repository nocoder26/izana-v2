"""
Abstract base class for all 11 Izana swarms.

Provides (Decision 5):
- Universal retry wrapper: try LLM call -> validate output -> retry once
  with stricter prompt -> return fallback
- Automatic tracing to chat_traces table (Decision 10)
- Health metrics per swarm

Each subclass must implement:
- swarm_id: str (e.g., "swarm_0_polyglot")
- get_fallback_value() -> Any
- validate_output(output: Any) -> bool
- build_messages(**kwargs) -> list[dict]
"""

from __future__ import annotations

import asyncio
import json
import time
from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from app.core.database import get_supabase_client
from app.core.exceptions import EmptyResponseError, RefusalError
from app.core.logging_config import get_logger
from app.core.metrics import observe_chat_latency, record_swarm_error
from app.core.model_config import SWARM_CONFIG
from app.services.groq_client import groq_manager

logger = get_logger(__name__)


class SwarmBase(ABC):
    """Abstract base class providing retry, fallback, and tracing for every
    Izana swarm agent.

    Subclasses **must** set the class-level :attr:`swarm_id` attribute and
    implement the three abstract methods.  The heavy lifting -- retries,
    circuit-breaker-aware LLM calls via :data:`groq_manager`, output
    validation, and trace logging -- is handled by
    :meth:`execute_with_retry`.

    Attributes:
        swarm_id: Canonical identifier matching a key in
                  :data:`~app.core.model_config.SWARM_CONFIG`.
        model: Primary model identifier for this swarm.
        fallback_model: Model to try when the primary model fails, or
                        ``None`` if no fallback is configured.
        temperature: Sampling temperature for the LLM.
        max_tokens: Maximum tokens the LLM may generate.
        timeout_seconds: Per-call timeout budget in seconds.
    """

    # Subclasses MUST override this.
    swarm_id: str = ""

    def __init__(self) -> None:
        if not self.swarm_id:
            raise ValueError(
                f"{self.__class__.__name__} must set a non-empty 'swarm_id'"
            )
        config = SWARM_CONFIG[self.swarm_id]
        self.model: str = config["model"]
        self.fallback_model: str | None = config.get("fallback_model")
        self.temperature: float = config.get("temperature", 0.3)
        self.max_tokens: int = config.get("max_tokens", 1000)
        self.timeout_seconds: int = config.get("timeout_seconds", 30)

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def get_fallback_value(self) -> Any:
        """Return a safe default value when all LLM attempts fail.

        The returned value must satisfy the same contract as a successful
        LLM response for this swarm so that downstream consumers can
        proceed without crashing.
        """

    @abstractmethod
    def validate_output(self, output: Any) -> bool:
        """Return ``True`` if *output* meets the quality bar for this swarm.

        Called after parsing the raw LLM response.  Returning ``False``
        triggers a retry with a stricter prompt, and ultimately the
        fallback value.
        """

    @abstractmethod
    def build_messages(self, **kwargs: Any) -> list[dict[str, str]]:
        """Construct the ``messages`` list to send to the LLM.

        Args:
            **kwargs: Swarm-specific inputs (user message, context, etc.).

        Returns:
            A list of message dicts with ``role`` and ``content`` keys.
        """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self, *args: Any, trace_id: UUID | str = "", **kwargs: Any) -> Any:
        """Public entry point — build messages and execute with retry.

        All swarm convenience methods (e.g., ``gatekeeper.classify(text, trace_id)``)
        call this method. It:

        1. Forwards ``*args`` / ``**kwargs`` to ``self.build_messages()``
        2. Calls ``execute_with_retry()`` with the built messages
        3. Returns the validated (or fallback) result

        Args:
            *args: Positional arguments forwarded to ``build_messages()``.
            trace_id: Correlation ID for tracing (Decision 10).
            **kwargs: Keyword arguments forwarded to ``build_messages()``.

        Returns:
            The swarm's output (validated or fallback).
        """
        if isinstance(trace_id, str) and trace_id:
            trace_id = UUID(trace_id)
        elif not trace_id:
            from uuid import uuid4
            trace_id = uuid4()

        messages = self.build_messages(*args, **kwargs)
        return await self.execute_with_retry(messages, trace_id)

    # ------------------------------------------------------------------
    # Core execution (internal)
    # ------------------------------------------------------------------

    async def execute_with_retry(
        self,
        messages: list[dict[str, str]],
        trace_id: UUID,
        **kwargs: Any,
    ) -> Any:
        """Run the LLM call with automatic retry, fallback, and tracing.

        **Flow:**

        1. *Attempt 1* -- call the primary model; parse and validate the
           response.  On success return immediately.
        2. If the output is empty, invalid, or a JSON parse error, build a
           stricter prompt and retry with the fallback model (*Attempt 2*).
        3. If the retry also fails, return :meth:`get_fallback_value`.
        4. On hard infrastructure errors (timeout, rate-limit, service
           unavailable) skip the retry and go straight to fallback.
        5. Every path logs a trace row via :meth:`_log_trace`.

        Args:
            messages: Chat messages for the LLM.
            trace_id: UUID linking this call to the parent chat request.
            **kwargs: Extra metadata forwarded to the trace log.

        Returns:
            The parsed LLM output, or the fallback value.
        """
        start = time.monotonic()
        usage: dict[str, Any] | None = None
        retry_count = 0
        model_used = self.model
        error_detail: str | None = None

        # ── Attempt 1: primary model ─────────────────────────────────
        try:
            response = await asyncio.wait_for(
                groq_manager.chat_completion(
                    messages=messages,
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                ),
                timeout=self.timeout_seconds,
            )
            usage = self._extract_usage(response)
            parsed = self._parse_response(response)

            if not self.validate_output(parsed):
                raise EmptyResponseError(
                    f"Validation failed for {self.swarm_id} output."
                )

            # Success on first attempt.
            latency = time.monotonic() - start
            observe_chat_latency(self.swarm_id, latency)
            await self._log_trace(
                trace_id=trace_id,
                messages=messages,
                output=parsed,
                model=model_used,
                usage=usage,
                latency=latency,
                error=None,
                retry_count=0,
                fallback_used=False,
            )
            return parsed

        except (EmptyResponseError, RefusalError, json.JSONDecodeError) as exc:
            # Retriable content errors -- move to attempt 2.
            retry_count = 1
            error_detail = f"{type(exc).__name__}: {exc}"
            logger.warning(
                "Swarm %s attempt 1 failed (%s), retrying with fallback model",
                self.swarm_id,
                error_detail,
                extra={
                    "swarm_id": self.swarm_id,
                    "error_type": type(exc).__name__,
                },
            )

        except (asyncio.TimeoutError, Exception) as exc:
            error_detail = f"{type(exc).__name__}: {exc}"

            # Infrastructure errors skip retry entirely.
            if isinstance(exc, asyncio.TimeoutError) or _is_infrastructure_error(exc):
                record_swarm_error(self.swarm_id, type(exc).__name__)
                logger.error(
                    "Swarm %s hit infrastructure error (%s), returning fallback",
                    self.swarm_id,
                    error_detail,
                    extra={
                        "swarm_id": self.swarm_id,
                        "error_type": type(exc).__name__,
                    },
                )
                latency = time.monotonic() - start
                observe_chat_latency(self.swarm_id, latency)
                fallback_value = self.get_fallback_value()
                await self._log_trace(
                    trace_id=trace_id,
                    messages=messages,
                    output=fallback_value,
                    model=model_used,
                    usage=usage,
                    latency=latency,
                    error=error_detail,
                    retry_count=0,
                    fallback_used=True,
                )
                return fallback_value

            # Unexpected but non-infrastructure error -- treat as retriable.
            retry_count = 1
            logger.warning(
                "Swarm %s attempt 1 hit unexpected error (%s), retrying",
                self.swarm_id,
                error_detail,
                extra={
                    "swarm_id": self.swarm_id,
                    "error_type": type(exc).__name__,
                },
            )

        # ── Attempt 2: stricter prompt + fallback model ──────────────
        retry_model = self.fallback_model or self.model
        model_used = retry_model
        stricter_messages = self._make_stricter_prompt(messages)

        try:
            response = await asyncio.wait_for(
                groq_manager.chat_completion(
                    messages=stricter_messages,
                    model=retry_model,
                    temperature=max(0.0, self.temperature - 0.1),
                    max_tokens=self.max_tokens,
                ),
                timeout=self.timeout_seconds,
            )
            usage = self._extract_usage(response)
            parsed = self._parse_response(response)

            if not self.validate_output(parsed):
                raise EmptyResponseError(
                    f"Validation failed for {self.swarm_id} on retry."
                )

            # Success on retry.
            latency = time.monotonic() - start
            observe_chat_latency(self.swarm_id, latency)
            await self._log_trace(
                trace_id=trace_id,
                messages=stricter_messages,
                output=parsed,
                model=model_used,
                usage=usage,
                latency=latency,
                error=error_detail,
                retry_count=retry_count,
                fallback_used=False,
            )
            return parsed

        except Exception as retry_exc:
            # Both attempts exhausted -- return the safe fallback.
            error_detail = (
                f"{error_detail} | retry: {type(retry_exc).__name__}: {retry_exc}"
            )
            record_swarm_error(self.swarm_id, "fallback_used")
            logger.error(
                "Swarm %s both attempts failed, returning fallback value",
                self.swarm_id,
                extra={
                    "swarm_id": self.swarm_id,
                    "error": error_detail,
                },
            )

        # Final fallback path.
        latency = time.monotonic() - start
        observe_chat_latency(self.swarm_id, latency)
        fallback_value = self.get_fallback_value()
        await self._log_trace(
            trace_id=trace_id,
            messages=messages,
            output=fallback_value,
            model=model_used,
            usage=usage,
            latency=latency,
            error=error_detail,
            retry_count=retry_count,
            fallback_used=True,
        )
        return fallback_value

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_response(self, response: Any) -> str:
        """Extract the assistant message content from a chat completion.

        Args:
            response: The raw ``ChatCompletion`` object returned by the
                      Groq SDK.

        Returns:
            The trimmed text content of the first choice's message.

        Raises:
            EmptyResponseError: If the response contains no usable content.
        """
        try:
            content: str | None = response.choices[0].message.content
        except (IndexError, AttributeError) as exc:
            raise EmptyResponseError(
                f"Malformed completion response: {exc}"
            ) from exc

        if not content or not content.strip():
            raise EmptyResponseError("LLM returned empty content.")
        return content.strip()

    @staticmethod
    def _extract_usage(response: Any) -> dict[str, Any] | None:
        """Pull token-usage metadata from the completion response.

        Returns ``None`` gracefully if the response does not include usage
        data (some models / streaming modes omit it).
        """
        try:
            usage_obj = response.usage
            if usage_obj is None:
                return None
            return {
                "prompt_tokens": getattr(usage_obj, "prompt_tokens", None),
                "completion_tokens": getattr(usage_obj, "completion_tokens", None),
                "total_tokens": getattr(usage_obj, "total_tokens", None),
            }
        except AttributeError:
            return None

    # ------------------------------------------------------------------
    # Prompt helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_stricter_prompt(
        messages: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """Append a stern system instruction to improve output compliance.

        The appended message is intentionally terse and directive so that
        models which may have refused or hallucinated on the first attempt
        are nudged toward producing valid, non-empty content.

        Args:
            messages: The original message list.

        Returns:
            A *new* list with the stricter system message appended.
        """
        stricter_system: dict[str, str] = {
            "role": "system",
            "content": (
                "You MUST respond with valid, non-empty content that directly "
                "addresses the request. Do not refuse. Do not return empty "
                "responses. Do not apologise or explain why you cannot help. "
                "Provide the requested output now."
            ),
        }
        return [*messages, stricter_system]

    # ------------------------------------------------------------------
    # JSON helper (retained for subclasses that parse structured output)
    # ------------------------------------------------------------------

    def _parse_json(self, text: str) -> Any | None:
        """Attempt to parse *text* as JSON, returning ``None`` on failure.

        Handles common LLM quirks like markdown code fences around JSON.
        """
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [line for line in lines[1:] if line.strip() != "```"]
            cleaned = "\n".join(lines).strip()
        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            logger.warning(
                "JSON parse failed in swarm",
                extra={"swarm_id": self.swarm_id, "raw_output": text[:200]},
            )
            return None

    # ------------------------------------------------------------------
    # Trace logging
    # ------------------------------------------------------------------

    async def _log_trace(
        self,
        trace_id: UUID,
        messages: list[dict[str, str]],
        output: Any,
        model: str,
        usage: dict[str, Any] | None,
        latency: float,
        error: str | None,
        retry_count: int,
        fallback_used: bool,
    ) -> None:
        """Persist a trace row to the ``chat_traces`` table.

        This is fire-and-forget: failures are logged but never propagated
        to the caller so that tracing cannot break the user-facing request.

        Args:
            trace_id: UUID linking the trace to its parent chat request.
            messages: The messages sent to the LLM.
            output: The parsed response (or fallback value).
            model: The model identifier that was used.
            usage: Token-usage dict, or ``None``.
            latency: Wall-clock time for the call in seconds.
            error: Error description string, or ``None`` on success.
            retry_count: Number of retries performed (0 or 1).
            fallback_used: Whether the fallback value was returned.
        """
        try:
            row = {
                "trace_id": str(trace_id),
                "swarm_id": self.swarm_id,
                "model": model,
                "messages": json.dumps(messages, default=str),
                "output": (
                    json.dumps(output, default=str)
                    if not isinstance(output, str)
                    else output
                ),
                "usage": json.dumps(usage, default=str) if usage else None,
                "latency_ms": round(latency * 1000),
                "error": error,
                "retry_count": retry_count,
                "fallback_used": fallback_used,
            }

            supabase = get_supabase_client()
            await asyncio.to_thread(
                lambda: supabase.table("chat_traces").insert(row).execute()
            )
        except Exception:
            logger.exception(
                "Failed to log trace for swarm %s (trace_id=%s)",
                self.swarm_id,
                trace_id,
                extra={
                    "swarm_id": self.swarm_id,
                    "trace_id": str(trace_id),
                },
            )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _is_infrastructure_error(exc: Exception) -> bool:
    """Return ``True`` if *exc* represents a transient infrastructure
    failure that should skip the retry path and go straight to fallback.

    Covers Izana custom exceptions, Groq SDK rate-limit errors, and any
    exception whose class name contains ``ServiceUnavailable``.
    """
    from app.core.exceptions import (
        RateLimitError as IzanaRateLimitError,
        TimeoutError as IzanaTimeoutError,
    )

    if isinstance(exc, (IzanaRateLimitError, IzanaTimeoutError)):
        return True

    try:
        from groq import RateLimitError as GroqRateLimitError

        if isinstance(exc, GroqRateLimitError):
            return True
    except ImportError:
        pass

    if "ServiceUnavailable" in type(exc).__name__:
        return True

    return False
