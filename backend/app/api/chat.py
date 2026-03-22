"""
Chat API endpoints with SSE streaming and REST fallback.

Provides two endpoints:

- ``POST /chat/stream`` -- Enqueues the chat pipeline task, then streams
  events to the client via Server-Sent Events (SSE) from a Redis stream.
- ``POST /chat`` -- REST fallback that blocks until the full response is
  ready and returns it as JSON.

Architecture decisions:
- Decision 2:  Task queue architecture (arq + Redis).
- Decision 9:  Compliance runs before streaming -- the client only
               receives tokens that have passed the compliance check.
- Decision 12: Redis inline fallback -- when Redis is down, the pipeline
               runs synchronously in-process so the user is not blocked.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any, AsyncGenerator
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.auth import get_user_id
from app.core.logging_config import get_logger
from app.core.task_queue import enqueue_task, get_redis_pool
from app.core.validators import check_for_pii, is_greeting, sanitize_input

logger = get_logger(__name__)

router = APIRouter()

# ── Pydantic models ──────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    """Incoming chat message from the client.

    Attributes:
        content: The user's message text (1--2000 characters).
    """

    content: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    """Complete chat response for the REST fallback endpoint.

    Attributes:
        content:    The assistant's response text.
        sources:    List of RAG source metadata dicts.
        follow_ups: Suggested follow-up questions.
        message_id: Unique identifier for this message exchange.
    """

    content: str
    sources: list[dict] = []
    follow_ups: list[str] = []
    message_id: str


# ── Inline fallback pipeline ─────────────────────────────────────────────


async def run_pipeline_inline(
    user_id: str,
    content: str,
) -> AsyncGenerator[str, None]:
    """Run the chat pipeline synchronously when Redis is unavailable.

    Executes the same 12-step pipeline as ``chat_pipeline_task`` but
    yields SSE-formatted events directly instead of writing them to a
    Redis stream.  This is the Decision 12 inline fallback.

    Args:
        user_id: Authenticated Supabase user ID.
        content: Raw user message text.

    Yields:
        SSE-formatted event strings (``event: <type>\\ndata: <json>\\n\\n``).
    """
    # Lazy imports to avoid circular dependencies and to keep the
    # module importable even when swarm dependencies are not installed.
    from app.services.clinical_brain import ClinicalBrain, RAGResult
    from app.services.compliance_checker import ComplianceChecker
    from app.services.context_builder import ContextBuilder
    from app.services.gap_detector import GapDetector
    from app.services.gatekeeper import Gatekeeper
    from app.services.response_curator import ChatResponseCurator
    from app.services.sentiment_analyser import SentimentAnalyser
    from app.services.translator import Translator
    from app.workers.chat_tasks import (
        generate_greeting,
        get_user_language,
        get_user_profile_summary,
        save_chat_log,
    )

    trace_id = str(uuid4())

    translator_inst = Translator()
    gatekeeper_inst = Gatekeeper()
    clinical_brain_inst = ClinicalBrain()
    response_curator_inst = ChatResponseCurator()
    compliance_checker_inst = ComplianceChecker()
    context_builder_inst = ContextBuilder()
    gap_detector_inst = GapDetector()
    sentiment_analyser_inst = SentimentAnalyser()

    def _sse(event_type: str, data: dict[str, Any]) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    try:
        # Step 1: Sanitize
        content = sanitize_input(content)
        if not content:
            yield _sse("error", {"message": "Empty message"})
            return

        # Step 2: PII Detection
        pii_result = check_for_pii(content)
        if pii_result.has_pii:
            yield _sse(
                "stage",
                {"stage": "pii_warning", "pii_types": pii_result.pii_types},
            )

        # Step 3: Greeting Detection
        if is_greeting(content):
            greeting = await generate_greeting(user_id)
            for word in greeting.split():
                yield _sse("token", {"text": word + " "})
            yield _sse("done", {})
            try:
                await save_chat_log(user_id, content, greeting, trace_id)
            except Exception:
                pass
            return

        # Step 4: Translation
        yield _sse("stage", {"stage": "understanding"})
        user_language = await get_user_language(user_id)
        content_en = content

        if user_language and user_language != "en":
            try:
                content_en = await translator_inst.translate(
                    content, source_lang=user_language, target_lang="en",
                    trace_id=trace_id,
                )
            except Exception:
                content_en = content

        # Step 5: Gatekeeper
        try:
            classification = await gatekeeper_inst.classify(
                content_en, trace_id=trace_id
            )
        except Exception:
            classification = {
                "safe": True,
                "is_fertility_related": True,
                "category": "general",
            }

        if not classification.get("safe", True):
            yield _sse(
                "error",
                {
                    "message": (
                        "I'm not able to respond to that type of message. "
                        "Please rephrase your question about fertility "
                        "or wellness."
                    )
                },
            )
            return

        if not classification.get("is_fertility_related", True):
            yield _sse(
                "error",
                {
                    "message": (
                        "I'm specialised in fertility and wellness topics. "
                        "Could you ask me something related to your "
                        "fertility journey?"
                    )
                },
            )
            return

        # Step 6: Context Builder
        yield _sse("stage", {"stage": "searching"})
        user_profile = await get_user_profile_summary(user_id)
        user_context_data: dict[str, Any] = {
            "user_id": user_id,
            "profile": user_profile,
            "current_question": content_en,
        }

        try:
            context = await context_builder_inst.get_context(
                user_context_data, trace_id=trace_id
            )
        except Exception:
            context = {
                "phase": "unknown", "day": 0, "treatment": "unknown",
                "mood": None, "summary": "", "key_bloodwork": None,
            }

        # Step 7: RAG Search
        try:
            rag_result = await clinical_brain_inst.search([content_en])
        except Exception:
            rag_result = RAGResult(
                matches=[], degradation_level=4, message="Search failed"
            )

        for match in rag_result.matches:
            source_title = match.metadata.get("title", match.id)
            yield _sse(
                "source",
                {"title": source_title, "relevance": round(match.similarity, 2)},
            )

        yield _sse(
            "stage", {"stage": "found", "count": len(rag_result.matches)}
        )

        # Format RAG sources
        rag_sources_text = ""
        if rag_result.matches:
            source_parts: list[str] = []
            for idx, match in enumerate(rag_result.matches, 1):
                title = match.metadata.get("title", f"Source {idx}")
                source_parts.append(
                    f"[Source {idx}] {title} "
                    f"(relevance: {match.similarity:.2f}):\n{match.content}"
                )
            rag_sources_text = "\n\n".join(source_parts)

        # Step 8: Response Curator
        yield _sse("stage", {"stage": "crafting"})
        context_summary = (
            context.get("summary", "") if isinstance(context, dict) else str(context)
        )
        user_profile_str = json.dumps(user_profile, default=str)

        try:
            raw_response = await response_curator_inst.curate(
                question=content_en,
                context_summary=context_summary,
                rag_sources=rag_sources_text,
                user_profile=user_profile_str,
                trace_id=trace_id,
            )
        except Exception:
            raw_response = (
                "I'm sorry, I couldn't generate a response right now. "
                "Please try again in a moment."
            )

        follow_ups = ChatResponseCurator.parse_follow_up_questions(raw_response)
        response_text = re.sub(
            r"\n*FOLLOW_UP:\s*\[.*?\]\s*$", "", raw_response, flags=re.DOTALL
        ).strip()

        # Step 9: Compliance Check
        try:
            response_text = await compliance_checker_inst.check(
                response_text, trace_id=trace_id
            )
        except Exception:
            pass

        # Step 10: Translate Back
        if user_language and user_language != "en":
            try:
                response_text = await translator_inst.translate(
                    response_text, source_lang="en",
                    target_lang=user_language, trace_id=trace_id,
                )
            except Exception:
                pass

        # Step 11: Stream tokens
        words = response_text.split()
        for word in words:
            yield _sse("token", {"text": word + " "})

        if follow_ups:
            yield _sse("followups", {"questions": follow_ups})

        yield _sse("done", {})

        # Step 12: Background tasks (fire-and-forget)
        try:
            await save_chat_log(
                user_id=user_id,
                user_content=content,
                assistant_content=response_text,
                trace_id=trace_id,
            )
        except Exception:
            pass

        try:
            rag_summary = (
                f"Degradation level: {rag_result.degradation_level}. "
                f"{rag_result.message}. "
                f"Matches: {len(rag_result.matches)}"
            )
            await gap_detector_inst.detect(
                question=content_en, rag_summary=rag_summary,
                trace_id=trace_id,
            )
        except Exception:
            pass

        try:
            await sentiment_analyser_inst.analyse(
                user_message=content,
                assistant_response=response_text,
                trace_id=trace_id,
            )
        except Exception:
            pass

    except Exception as exc:
        logger.exception("Inline pipeline failed", extra={"user_id": user_id})
        yield _sse("error", {"message": "An unexpected error occurred. Please try again."})


# ── SSE streaming endpoint ───────────────────────────────────────────────


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    user_id: str = Depends(get_user_id),
) -> StreamingResponse:
    """Enqueue the chat pipeline task, then stream results via SSE.

    The endpoint first attempts to enqueue the work to an arq worker via
    Redis.  If Redis is unreachable (Decision 12 fallback), the pipeline
    runs inline in the current process.

    The response is a ``text/event-stream`` SSE stream containing events:

    - ``stage``     -- pipeline progress updates
    - ``source``    -- individual RAG source metadata
    - ``token``     -- a single word from the streamed response
    - ``followups`` -- suggested follow-up questions
    - ``done``      -- signals the end of the stream
    - ``error``     -- an error message (also terminates the stream)

    Args:
        request: Validated chat request body.
        user_id: Authenticated user ID (injected by ``get_user_id``).

    Returns:
        A ``StreamingResponse`` with ``media_type="text/event-stream"``.
    """
    task_id = str(uuid4())

    # Attempt to connect to Redis and enqueue the task.
    use_redis = True
    try:
        pool = await get_redis_pool()
        await pool.ping()
    except Exception:
        logger.warning(
            "Redis unavailable, falling back to inline pipeline",
            extra={"task_id": task_id, "user_id": user_id},
        )
        use_redis = False

    if use_redis:
        # Normal path: enqueue to arq worker.
        job = await enqueue_task(
            pool,
            "chat_pipeline_task",
            task_id,
            user_id,
            request.content,
        )
        if job is None:
            logger.warning(
                "Failed to enqueue task, falling back to inline",
                extra={"task_id": task_id},
            )
            use_redis = False

    if use_redis:
        # Stream from Redis.
        async def event_generator() -> AsyncGenerator[str, None]:
            """Read events from the Redis stream and yield SSE data."""
            try:
                redis = await get_redis_pool()
                last_id = "0"
                timeout_at = time.monotonic() + 120  # 2 min max

                while time.monotonic() < timeout_at:
                    try:
                        events = await redis.xread(
                            {f"chat:{task_id}": last_id},
                            count=10,
                            block=500,
                        )
                    except Exception:
                        logger.exception(
                            "Redis xread failed",
                            extra={"task_id": task_id},
                        )
                        yield f'event: error\ndata: {{"message": "Stream read error"}}\n\n'
                        return

                    for stream_name, messages in events:
                        for msg_id, fields in messages:
                            last_id = msg_id
                            event_type = (
                                fields[b"event"].decode()
                                if isinstance(fields[b"event"], bytes)
                                else fields["event"]
                            )
                            data = (
                                fields[b"data"].decode()
                                if isinstance(fields[b"data"], bytes)
                                else fields["data"]
                            )
                            yield f"event: {event_type}\ndata: {data}\n\n"

                            if event_type in ("done", "error"):
                                # Clean up the stream.
                                try:
                                    await redis.delete(f"chat:{task_id}")
                                except Exception:
                                    pass
                                return

                # Timeout reached.
                yield f'event: error\ndata: {{"message": "Request timed out"}}\n\n'
                try:
                    redis_conn = await get_redis_pool()
                    await redis_conn.delete(f"chat:{task_id}")
                except Exception:
                    pass

            except Exception:
                logger.exception(
                    "SSE event generator failed",
                    extra={"task_id": task_id},
                )
                yield f'event: error\ndata: {{"message": "Stream error"}}\n\n'

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Task-Id": task_id,
            },
        )

    # Fallback path: run pipeline inline (Decision 12).
    return StreamingResponse(
        run_pipeline_inline(user_id, request.content),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Task-Id": task_id,
        },
    )


# ── REST fallback endpoint ───────────────────────────────────────────────


@router.post("/chat")
async def chat_rest(
    request: ChatRequest,
    user_id: str = Depends(get_user_id),
) -> ChatResponse:
    """REST fallback -- blocks and returns the complete response as JSON.

    This endpoint runs the full pipeline inline (no task queue) and
    collects all emitted events into a single ``ChatResponse``.  Useful
    for clients that cannot consume SSE streams.

    Args:
        request: Validated chat request body.
        user_id: Authenticated user ID (injected by ``get_user_id``).

    Returns:
        A ``ChatResponse`` with the complete assistant reply, sources,
        follow-up questions, and a message ID.

    Raises:
        HTTPException 500: If the pipeline fails with an unrecoverable error.
    """
    message_id = str(uuid4())
    content_parts: list[str] = []
    sources: list[dict] = []
    follow_ups: list[str] = []
    has_error = False
    error_message = ""

    try:
        async for event_str in run_pipeline_inline(user_id, request.content):
            # Parse the SSE event string.
            event_type = ""
            data_str = ""
            for line in event_str.strip().split("\n"):
                if line.startswith("event: "):
                    event_type = line[7:]
                elif line.startswith("data: "):
                    data_str = line[6:]

            if not event_type or not data_str:
                continue

            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            if event_type == "token":
                content_parts.append(data.get("text", ""))
            elif event_type == "source":
                sources.append(data)
            elif event_type == "followups":
                follow_ups = data.get("questions", [])
            elif event_type == "error":
                has_error = True
                error_message = data.get("message", "Unknown error")
            elif event_type == "done":
                break

    except Exception:
        logger.exception(
            "REST chat endpoint failed",
            extra={"user_id": user_id, "message_id": message_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat request",
        )

    if has_error and not content_parts:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_message,
        )

    return ChatResponse(
        content="".join(content_parts).strip(),
        sources=sources,
        follow_ups=follow_ups,
        message_id=message_id,
    )
