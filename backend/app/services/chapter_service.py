"""
Chapter lifecycle service for Izana Chat.

A "chapter" represents a contiguous period within a user's fertility
journey — typically one treatment cycle or phase.  Chapters track the
user's active state and support clean transitions between phases.

Usage::

    from app.services.chapter_service import (
        create_chapter,
        close_chapter,
        get_active_chapter,
        transition_phase,
    )
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.database import get_supabase_client
from app.core.logging_config import get_logger
from app.models.enums import ChapterStatus
from app.services.plan_service import trigger_plan_generation

logger = get_logger(__name__)


async def create_chapter(
    user_id: str,
    phase: str,
    journey_id: str,
    cycle_id: str,
) -> dict[str, Any]:
    """Create a new active chapter for a user.

    Args:
        user_id:    Supabase auth user ID.
        phase:      Treatment phase identifier (e.g. ``"ovarian_stimulation"``).
        journey_id: ID of the parent journey record.
        cycle_id:   ID of the treatment cycle.

    Returns:
        The newly created chapter row as a dict.
    """
    supabase = get_supabase_client()
    chapter_id = str(uuid4())

    try:
        row = {
            "id": chapter_id,
            "user_id": user_id,
            "phase": phase,
            "journey_id": journey_id,
            "cycle_id": cycle_id,
            "status": ChapterStatus.ACTIVE.value,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        result = await asyncio.to_thread(
            lambda: supabase.table("chapters")
            .insert(row)
            .execute()
        )

        chapter = result.data[0] if result.data else row

        logger.info(
            "Chapter created",
            extra={
                "user_id": user_id,
                "chapter_id": chapter_id,
                "phase": phase,
            },
        )

        return chapter

    except Exception:
        logger.exception(
            "Failed to create chapter",
            extra={"user_id": user_id, "phase": phase},
        )
        raise


async def close_chapter(
    chapter_id: str,
    summary: str = "",
) -> dict[str, Any]:
    """Close a chapter by setting its end time and status to completed.

    Args:
        chapter_id: The chapter to close.
        summary:    Optional free-text summary of the chapter.

    Returns:
        The updated chapter row as a dict.
    """
    supabase = get_supabase_client()

    try:
        update_data: dict[str, Any] = {
            "status": ChapterStatus.COMPLETED.value,
            "ended_at": datetime.now(timezone.utc).isoformat(),
        }
        if summary:
            update_data["summary"] = summary

        result = await asyncio.to_thread(
            lambda: supabase.table("chapters")
            .update(update_data)
            .eq("id", chapter_id)
            .execute()
        )

        chapter = result.data[0] if result.data else {"id": chapter_id, **update_data}

        logger.info(
            "Chapter closed",
            extra={"chapter_id": chapter_id, "status": "completed"},
        )

        return chapter

    except Exception:
        logger.exception(
            "Failed to close chapter", extra={"chapter_id": chapter_id}
        )
        raise


async def get_active_chapter(user_id: str) -> dict[str, Any] | None:
    """Return the user's currently active chapter, or None.

    Args:
        user_id: Supabase auth user ID.

    Returns:
        The active chapter row as a dict, or ``None`` if no chapter is
        active.
    """
    supabase = get_supabase_client()

    try:
        result = await asyncio.to_thread(
            lambda: supabase.table("chapters")
            .select("*")
            .eq("user_id", user_id)
            .eq("status", ChapterStatus.ACTIVE.value)
            .order("started_at", desc=True)
            .limit(1)
            .execute()
        )

        if result.data:
            return result.data[0]
        return None

    except Exception:
        logger.exception(
            "Failed to get active chapter", extra={"user_id": user_id}
        )
        raise


async def transition_phase(
    user_id: str,
    new_phase: str,
    skip_confirmation: bool = False,
) -> dict[str, Any]:
    """Transition a user to a new phase.

    Closes the current active chapter, creates a new one for the target
    phase, and triggers plan generation for the new context.

    Args:
        user_id:           Supabase auth user ID.
        new_phase:         The phase to transition into.
        skip_confirmation: If ``True``, bypass any confirmation prompt
                           (used by automated phase-transition checks).

    Returns:
        A dict with ``old_chapter``, ``new_chapter``, and ``plan`` keys.
    """
    try:
        # Close the current chapter (if any).
        current = await get_active_chapter(user_id)
        old_chapter: dict[str, Any] | None = None

        if current:
            old_chapter = await close_chapter(
                current["id"],
                summary=f"Transitioned to {new_phase}",
            )

        # Derive journey_id and cycle_id from the old chapter, or use
        # placeholders if this is the first chapter.
        journey_id = current["journey_id"] if current else str(uuid4())
        cycle_id = current["cycle_id"] if current else str(uuid4())

        # Create the new chapter.
        new_chapter = await create_chapter(
            user_id=user_id,
            phase=new_phase,
            journey_id=journey_id,
            cycle_id=cycle_id,
        )

        # Trigger plan generation for the new phase context.
        plan = await trigger_plan_generation(
            user_id=user_id,
            priority="urgent_phase_change",
        )

        logger.info(
            "Phase transition completed",
            extra={
                "user_id": user_id,
                "old_phase": current["phase"] if current else None,
                "new_phase": new_phase,
            },
        )

        return {
            "old_chapter": old_chapter,
            "new_chapter": new_chapter,
            "plan": plan,
        }

    except Exception:
        logger.exception(
            "Failed to transition phase",
            extra={"user_id": user_id, "new_phase": new_phase},
        )
        raise
