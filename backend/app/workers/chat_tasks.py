"""
Chat pipeline task for the arq worker.

Implements the full 12-step chat pipeline (Decision 9 -- compliance BEFORE
streaming) that runs inside the arq worker process.  Each step emits events
to a Redis stream keyed by ``chat:{task_id}`` so the SSE endpoint can relay
them to the client in real time.

Pipeline steps:
 1. Input Sanitization
 2. PII Detection
 3. Greeting Detection
 4. Translation (if non-English user)
 5. Gatekeeper classification
 6. Context Builder
 7. RAG Search (ClinicalBrain)
 8. Response Curator
 9. Compliance Check (runs on FULL response before streaming)
10. Translate Back (if non-English user)
11. Stream approved tokens
12. Background tasks (save chat log, gap detection, sentiment analysis)
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.database import get_supabase_client
from app.core.logging_config import get_logger
from app.core.validators import check_for_pii, is_greeting, sanitize_input
from app.services.clinical_brain import ClinicalBrain
from app.services.compliance_checker import ComplianceChecker
from app.services.context_builder import ContextBuilder
from app.services.gap_detector import GapDetector
from app.services.gatekeeper import Gatekeeper
from app.services.response_curator import ChatResponseCurator
from app.services.sentiment_analyser import SentimentAnalyser
from app.services.translator import Translator

logger = get_logger(__name__)

# ── Swarm instances (module-level singletons) ────────────────────────────

translator = Translator()
gatekeeper = Gatekeeper()
clinical_brain = ClinicalBrain()
response_curator = ChatResponseCurator()
compliance_checker = ComplianceChecker()
context_builder = ContextBuilder()
gap_detector = GapDetector()
sentiment_analyser = SentimentAnalyser()

# ── Time-based greeting templates ────────────────────────────────────────

_GREETING_TEMPLATES = {
    "morning": "Good morning! I hope you're having a great start to your day.",
    "afternoon": "Good afternoon! How can I help you today?",
    "evening": "Good evening! I'm here whenever you need me.",
    "night": "Hello! I'm here if you need anything.",
}


# ── Helper functions ─────────────────────────────────────────────────────


async def _emit(
    redis: Any,
    task_id: str,
    event_type: str,
    data: dict[str, Any],
) -> None:
    """Write a single event to the Redis stream for this task.

    Args:
        redis:      The arq Redis connection from the worker context.
        task_id:    Unique identifier for this chat request.
        event_type: One of ``stage``, ``token``, ``source``, ``followups``,
                    ``done``, ``error``.
        data:       JSON-serialisable event payload.
    """
    stream_key = f"chat:{task_id}"
    await redis.xadd(stream_key, {"event": event_type, "data": json.dumps(data)})


async def get_user_language(user_id: str) -> str:
    """Fetch the user's preferred language from the ``profiles`` table.

    Args:
        user_id: Supabase auth user ID.

    Returns:
        An ISO language code (e.g. ``"en"``, ``"es"``).  Defaults to
        ``"en"`` if the profile is missing or the field is not set.
    """
    try:
        supabase = get_supabase_client()
        result = await asyncio.to_thread(
            lambda: supabase.table("profiles")
            .select("language")
            .eq("id", user_id)
            .single()
            .execute()
        )
        if result.data and result.data.get("language"):
            return result.data["language"]
    except Exception:
        logger.warning(
            "Could not fetch user language, defaulting to 'en'",
            extra={"user_id": user_id},
        )
    return "en"


async def get_user_profile_summary(user_id: str) -> dict[str, Any]:
    """Fetch a summary of the user's profile for context personalisation.

    Queries the ``profiles`` table for treatment type, allergies, current
    phase, and other relevant fields.

    Args:
        user_id: Supabase auth user ID.

    Returns:
        A dict with profile fields, or an empty dict on failure.
    """
    try:
        supabase = get_supabase_client()
        result = await asyncio.to_thread(
            lambda: supabase.table("profiles")
            .select(
                "treatment_type, allergies, current_phase, "
                "cycle_day, language, partner_status, age"
            )
            .eq("id", user_id)
            .single()
            .execute()
        )
        if result.data:
            return result.data
    except Exception:
        logger.warning(
            "Could not fetch user profile summary",
            extra={"user_id": user_id},
        )
    return {}


async def generate_greeting(user_id: str) -> str:
    """Generate a time-based greeting with user phase context.

    Combines a time-of-day greeting with the user's current treatment
    phase if available, creating a personalised welcome message.

    Args:
        user_id: Supabase auth user ID.

    Returns:
        A greeting string.
    """
    now = datetime.now(timezone.utc)
    hour = now.hour

    if 5 <= hour < 12:
        period = "morning"
    elif 12 <= hour < 17:
        period = "afternoon"
    elif 17 <= hour < 21:
        period = "evening"
    else:
        period = "night"

    base_greeting = _GREETING_TEMPLATES[period]

    try:
        profile = await get_user_profile_summary(user_id)
        phase = profile.get("current_phase")
        if phase:
            base_greeting += (
                f" I see you're currently in the {phase} phase "
                f"-- feel free to ask me anything about it."
            )
    except Exception:
        pass

    return base_greeting


async def save_chat_log(
    user_id: str,
    user_content: str,
    assistant_content: str,
    trace_id: str,
    chapter_id: str | None = None,
) -> None:
    """Persist a conversation turn to the ``chat_logs`` table.

    This is fire-and-forget: errors are logged but never propagated.

    Args:
        user_id:           Supabase auth user ID.
        user_content:      The user's original message.
        assistant_content: The assistant's response.
        trace_id:          Correlation ID linking to ``chat_traces``.
        chapter_id:        Optional conversation chapter / session ID.
    """
    try:
        supabase = get_supabase_client()
        row = {
            "user_id": user_id,
            "user_message": user_content,
            "assistant_message": assistant_content,
            "trace_id": trace_id,
        }
        if chapter_id:
            row["chapter_id"] = chapter_id

        await asyncio.to_thread(
            lambda: supabase.table("chat_logs").insert(row).execute()
        )
    except Exception:
        logger.exception(
            "Failed to save chat log",
            extra={"user_id": user_id, "trace_id": trace_id},
        )


# ── Main pipeline task ───────────────────────────────────────────────────


async def chat_pipeline_task(
    ctx: dict,
    task_id: str,
    user_id: str,
    content: str,
) -> None:
    """The full 12-step chat pipeline.

    Runs inside the arq worker process.  Writes events to the Redis
    stream ``chat:{task_id}`` so the API SSE endpoint can relay them to
    the client.

    Args:
        ctx:     arq worker context (contains ``redis`` key).
        task_id: Unique identifier for this chat request.
        user_id: Authenticated Supabase user ID.
        content: Raw user message text.
    """
    redis = ctx["redis"]
    trace_id = str(uuid4())
    stream_key = f"chat:{task_id}"

    # Set stream TTL so abandoned streams are cleaned up.
    await redis.expire(stream_key, 300)

    try:
        # ── Step 1: Input Sanitization ───────────────────────────────
        content = sanitize_input(content)

        if not content:
            await _emit(redis, task_id, "error", {"message": "Empty message"})
            return

        # ── Step 2: PII Detection ────────────────────────────────────
        pii_result = check_for_pii(content)
        if pii_result.has_pii:
            await _emit(
                redis,
                task_id,
                "stage",
                {
                    "stage": "pii_warning",
                    "pii_types": pii_result.pii_types,
                },
            )
            logger.warning(
                "PII detected in user input",
                extra={
                    "user_id": user_id,
                    "pii_types": pii_result.pii_types,
                    "trace_id": trace_id,
                },
            )

        # ── Step 3: Greeting Detection ───────────────────────────────
        if is_greeting(content):
            greeting = await generate_greeting(user_id)
            # Stream greeting as tokens.
            for word in greeting.split():
                await _emit(redis, task_id, "token", {"text": word + " "})
            await _emit(redis, task_id, "done", {})

            # Fire-and-forget: save greeting to chat log.
            try:
                await save_chat_log(user_id, content, greeting, trace_id)
            except Exception:
                logger.exception("Failed to save greeting chat log")
            return

        # ── Step 4: Translation (user language -> English) ───────────
        await _emit(redis, task_id, "stage", {"stage": "understanding"})

        user_language = await get_user_language(user_id)
        content_en = content

        if user_language and user_language != "en":
            try:
                content_en = await translator.translate(
                    content,
                    source_lang=user_language,
                    target_lang="en",
                    trace_id=trace_id,
                )
            except Exception:
                logger.exception(
                    "Translation to English failed, using original",
                    extra={"trace_id": trace_id},
                )
                content_en = content

        # ── Step 5: Gatekeeper ───────────────────────────────────────
        try:
            classification = await gatekeeper.classify(
                content_en, trace_id=trace_id
            )
        except Exception:
            logger.exception(
                "Gatekeeper classification failed, allowing message",
                extra={"trace_id": trace_id},
            )
            classification = {
                "safe": True,
                "is_fertility_related": True,
                "category": "general",
            }

        if not classification.get("safe", True):
            await _emit(
                redis,
                task_id,
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
            await _emit(
                redis,
                task_id,
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

        # ── Step 6: Context Builder ──────────────────────────────────
        await _emit(redis, task_id, "stage", {"stage": "searching"})

        user_profile = await get_user_profile_summary(user_id)
        user_context_data: dict[str, Any] = {
            "user_id": user_id,
            "profile": user_profile,
            "current_question": content_en,
        }

        try:
            context = await context_builder.get_context(
                user_context_data, trace_id=trace_id
            )
        except Exception:
            logger.exception(
                "Context builder failed, using empty context",
                extra={"trace_id": trace_id},
            )
            context = {
                "phase": "unknown",
                "day": 0,
                "treatment": "unknown",
                "mood": None,
                "summary": "",
                "key_bloodwork": None,
            }

        # ── Step 7: RAG Search (ClinicalBrain) ───────────────────────
        try:
            rag_result = await clinical_brain.search([content_en])
        except Exception:
            logger.exception(
                "ClinicalBrain search failed",
                extra={"trace_id": trace_id},
            )
            from app.services.clinical_brain import RAGResult

            rag_result = RAGResult(
                matches=[], degradation_level=4, message="Search failed"
            )

        # Emit source events for each RAG match.
        for match in rag_result.matches:
            source_title = match.metadata.get("title", match.id)
            await _emit(
                redis,
                task_id,
                "source",
                {"title": source_title, "relevance": round(match.similarity, 2)},
            )

        await _emit(
            redis,
            task_id,
            "stage",
            {"stage": "found", "count": len(rag_result.matches)},
        )

        # Format RAG sources for the curator prompt.
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

        # ── Step 8: Response Curator ─────────────────────────────────
        await _emit(redis, task_id, "stage", {"stage": "crafting"})

        context_summary = context.get("summary", "") if isinstance(context, dict) else str(context)
        user_profile_str = json.dumps(user_profile, default=str)

        try:
            raw_response = await response_curator.curate(
                question=content_en,
                context_summary=context_summary,
                rag_sources=rag_sources_text,
                user_profile=user_profile_str,
                trace_id=trace_id,
            )
        except Exception:
            logger.exception(
                "Response curator failed",
                extra={"trace_id": trace_id},
            )
            raw_response = (
                "I'm sorry, I couldn't generate a response right now. "
                "Please try again in a moment."
            )

        # Extract follow-up questions before compliance check.
        follow_ups = ChatResponseCurator.parse_follow_up_questions(raw_response)

        # Strip the FOLLOW_UP line from the response body.
        response_text = re.sub(
            r"\n*FOLLOW_UP:\s*\[.*?\]\s*$", "", raw_response, flags=re.DOTALL
        ).strip()

        # ── Step 9: Compliance Check (before streaming) ──────────────
        try:
            response_text = await compliance_checker.check(
                response_text, trace_id=trace_id
            )
        except Exception:
            logger.exception(
                "Compliance check failed, using unchecked response",
                extra={"trace_id": trace_id},
            )
            # Pass through original response (fail-open).

        # ── Step 10: Translate Back ──────────────────────────────────
        if user_language and user_language != "en":
            try:
                response_text = await translator.translate(
                    response_text,
                    source_lang="en",
                    target_lang=user_language,
                    trace_id=trace_id,
                )
            except Exception:
                logger.exception(
                    "Translation back to user language failed",
                    extra={"trace_id": trace_id},
                )
                # Fall through with English response.

        # ── Step 11: Stream approved tokens ──────────────────────────
        words = response_text.split()
        for word in words:
            await _emit(redis, task_id, "token", {"text": word + " "})

        # Emit follow-up questions if any.
        if follow_ups:
            await _emit(
                redis, task_id, "followups", {"questions": follow_ups}
            )

        await _emit(redis, task_id, "done", {})

        # ── Step 12: Background tasks ────────────────────────────────
        # Save chat log (fire-and-forget).
        try:
            await save_chat_log(
                user_id=user_id,
                user_content=content,
                assistant_content=response_text,
                trace_id=trace_id,
            )
        except Exception:
            logger.exception(
                "Failed to save chat log",
                extra={"trace_id": trace_id},
            )

        # Gap detection (non-critical).
        try:
            rag_summary = (
                f"Degradation level: {rag_result.degradation_level}. "
                f"{rag_result.message}. "
                f"Matches: {len(rag_result.matches)}"
            )
            gap_result = await gap_detector.detect(
                question=content_en,
                rag_summary=rag_summary,
                trace_id=trace_id,
            )
            if gap_result.get("has_gap"):
                logger.info(
                    "Knowledge gap detected",
                    extra={
                        "trace_id": trace_id,
                        "gap_type": gap_result.get("gap_type"),
                        "suggested_topic": gap_result.get("suggested_topic"),
                    },
                )
        except Exception:
            logger.warning(
                "Gap detection failed (non-critical)",
                extra={"trace_id": trace_id},
            )

        # Sentiment analysis (non-critical).
        try:
            await sentiment_analyser.analyse(
                user_message=content,
                assistant_response=response_text,
                trace_id=trace_id,
            )
        except Exception:
            logger.warning(
                "Sentiment analysis failed (non-critical)",
                extra={"trace_id": trace_id},
            )

    except Exception as exc:
        logger.exception(
            "Chat pipeline failed with unhandled error",
            extra={"task_id": task_id, "user_id": user_id, "trace_id": trace_id},
        )
        try:
            await _emit(
                redis,
                task_id,
                "error",
                {"message": "An unexpected error occurred. Please try again."},
            )
        except Exception:
            logger.exception("Failed to emit error event to Redis stream")
