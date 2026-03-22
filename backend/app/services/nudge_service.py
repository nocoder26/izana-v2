"""
Nudge scheduling and management service for Izana Chat.

Nudges are scheduled messages delivered through various channels (push
notifications, email, in-app banners, or chat cards).  They are stored
in the ``nudge_queue`` table and processed by the background worker.

Usage::

    from app.services.nudge_service import (
        schedule_nudge,
        cancel_user_nudges,
        get_pending_nudges,
    )
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.database import get_supabase_client
from app.core.logging_config import get_logger

logger = get_logger(__name__)


async def schedule_nudge(
    user_id: str,
    nudge_type: str,
    channel: str,
    scheduled_for: datetime,
    message_data: dict[str, Any],
) -> dict[str, Any]:
    """Schedule a nudge for future delivery.

    Args:
        user_id:       Supabase auth user ID.
        nudge_type:    Category of the nudge (e.g. ``"meal_reminder"``,
                       ``"exercise_prompt"``, ``"checkin"``).
        channel:       Delivery channel — ``"push"``, ``"email"``,
                       ``"in_app"``, or ``"chat_card"``.
        scheduled_for: UTC datetime when the nudge should be delivered.
        message_data:  JSON-serialisable payload containing the nudge
                       content (title, body, action URL, etc.).

    Returns:
        The inserted nudge row as a dict.
    """
    supabase = get_supabase_client()
    nudge_id = str(uuid4())

    try:
        row = {
            "id": nudge_id,
            "user_id": user_id,
            "nudge_type": nudge_type,
            "channel": channel,
            "status": "pending",
            "scheduled_for": scheduled_for.isoformat(),
            "message_data": message_data,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        result = await asyncio.to_thread(
            lambda: supabase.table("nudge_queue")
            .insert(row)
            .execute()
        )

        nudge = result.data[0] if result.data else row

        logger.info(
            "Nudge scheduled",
            extra={
                "user_id": user_id,
                "nudge_id": nudge_id,
                "nudge_type": nudge_type,
                "channel": channel,
                "scheduled_for": scheduled_for.isoformat(),
            },
        )

        return nudge

    except Exception:
        logger.exception(
            "Failed to schedule nudge",
            extra={"user_id": user_id, "nudge_type": nudge_type},
        )
        raise


async def cancel_user_nudges(user_id: str) -> int:
    """Cancel all pending nudges for a user.

    Used when disengagement sensing detects the user has been quiet,
    preventing unwanted notifications from being delivered.

    Args:
        user_id: Supabase auth user ID.

    Returns:
        The number of nudges cancelled.
    """
    supabase = get_supabase_client()

    try:
        # Count pending nudges first.
        count_result = await asyncio.to_thread(
            lambda: supabase.table("nudge_queue")
            .select("id")
            .eq("user_id", user_id)
            .eq("status", "pending")
            .execute()
        )

        count = len(count_result.data) if count_result.data else 0

        if count == 0:
            return 0

        # Cancel them.
        await asyncio.to_thread(
            lambda: supabase.table("nudge_queue")
            .update({
                "status": "cancelled",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("user_id", user_id)
            .eq("status", "pending")
            .execute()
        )

        logger.info(
            "User nudges cancelled",
            extra={"user_id": user_id, "count": count},
        )

        return count

    except Exception:
        logger.exception(
            "Failed to cancel user nudges", extra={"user_id": user_id}
        )
        raise


async def get_pending_nudges(limit: int = 100) -> list[dict[str, Any]]:
    """Fetch nudges that are due for delivery.

    Queries the ``nudge_queue`` for rows with ``status='pending'`` and
    ``scheduled_for <= now()``.

    Args:
        limit: Maximum number of nudges to return.

    Returns:
        A list of nudge rows as dicts.
    """
    supabase = get_supabase_client()

    try:
        now = datetime.now(timezone.utc).isoformat()

        result = await asyncio.to_thread(
            lambda: supabase.table("nudge_queue")
            .select("*")
            .eq("status", "pending")
            .lte("scheduled_for", now)
            .order("scheduled_for")
            .limit(limit)
            .execute()
        )

        return result.data or []

    except Exception:
        logger.exception("Failed to fetch pending nudges")
        raise
