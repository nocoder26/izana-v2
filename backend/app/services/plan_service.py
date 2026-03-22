"""
Plan lifecycle management service for Izana Chat.

Handles creation, status polling, and cancellation of personalised nutrition
and supplement plans.  Plans flow through the approval queue (Decision 14)
before being presented to users.

Usage::

    from app.services.plan_service import (
        trigger_plan_generation,
        get_plan_status,
        cancel_pending_plans,
    )
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.database import get_supabase_admin as get_supabase_client
from app.core.logging_config import get_logger
from app.models.enums import ApprovalPriority, PlanStatus

logger = get_logger(__name__)


async def trigger_plan_generation(
    user_id: str,
    priority: str = "normal",
) -> dict[str, Any]:
    """Create a new personalised plan entry and queue it for approval.

    The plan is initially created with ``status='GENERATING'``.  A
    corresponding entry is inserted into the ``approval_queue`` so that
    a nutritionist can review and approve the generated plan.

    Args:
        user_id:  Supabase auth user ID.
        priority: One of ``'normal'``, ``'urgent_phase_change'``,
                  ``'positive_outcome'``.

    Returns:
        A dict with ``plan_id``, ``approval_id``, and ``status``.
    """
    supabase = get_supabase_client()
    plan_id = str(uuid4())
    approval_id = str(uuid4())

    try:
        # Cancel any existing pending plans first.
        await cancel_pending_plans(user_id)

        # Create the plan record.
        await asyncio.to_thread(
            lambda: supabase.table("personalized_plans")
            .insert({
                "id": plan_id,
                "user_id": user_id,
                "status": PlanStatus.GENERATING.value,
                "priority": priority,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            .execute()
        )

        # Create the approval queue entry.
        await asyncio.to_thread(
            lambda: supabase.table("approval_queue")
            .insert({
                "id": approval_id,
                "plan_id": plan_id,
                "user_id": user_id,
                "status": "PENDING",
                "priority": priority,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            .execute()
        )

        logger.info(
            "Plan generation triggered",
            extra={
                "user_id": user_id,
                "plan_id": plan_id,
                "approval_id": approval_id,
                "priority": priority,
            },
        )

        return {
            "plan_id": plan_id,
            "approval_id": approval_id,
            "status": PlanStatus.GENERATING.value,
        }

    except Exception:
        logger.exception(
            "Failed to trigger plan generation",
            extra={"user_id": user_id},
        )
        raise


async def get_plan_status(user_id: str) -> dict[str, Any]:
    """Return the current plan status for client-side polling.

    Fetches the most recent plan for the user.

    Args:
        user_id: Supabase auth user ID.

    Returns:
        A dict with ``plan_id``, ``status``, ``created_at``, and
        ``updated_at``.  Returns ``{"status": "none"}`` if no plan exists.
    """
    supabase = get_supabase_client()

    try:
        result = await asyncio.to_thread(
            lambda: supabase.table("personalized_plans")
            .select("id, status, created_at, updated_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if result.data:
            plan = result.data[0]
            return {
                "plan_id": plan["id"],
                "status": plan["status"],
                "created_at": plan["created_at"],
                "updated_at": plan.get("updated_at"),
            }

        return {"status": "none"}

    except Exception:
        logger.exception(
            "Failed to get plan status", extra={"user_id": user_id}
        )
        raise


async def cancel_pending_plans(user_id: str) -> int:
    """Cancel all pending or generating plans for a user.

    Used during phase transitions to avoid stale plans being approved
    after the user's context has changed.

    Args:
        user_id: Supabase auth user ID.

    Returns:
        The number of plans cancelled.
    """
    supabase = get_supabase_client()

    try:
        # Find pending plans.
        result = await asyncio.to_thread(
            lambda: supabase.table("personalized_plans")
            .select("id")
            .eq("user_id", user_id)
            .in_("status", [
                PlanStatus.GENERATING.value,
                PlanStatus.PENDING_NUTRITIONIST.value,
            ])
            .execute()
        )

        if not result.data:
            return 0

        plan_ids = [row["id"] for row in result.data]

        # Update plans to expired.
        await asyncio.to_thread(
            lambda: supabase.table("personalized_plans")
            .update({
                "status": PlanStatus.EXPIRED.value,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("user_id", user_id)
            .in_("status", [
                PlanStatus.GENERATING.value,
                PlanStatus.PENDING_NUTRITIONIST.value,
            ])
            .execute()
        )

        # Cancel corresponding approval queue entries.
        for plan_id in plan_ids:
            await asyncio.to_thread(
                lambda pid=plan_id: supabase.table("approval_queue")
                .update({
                    "status": "CANCELLED",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
                .eq("plan_id", pid)
                .in_("status", ["PENDING", "ASSIGNED"])
                .execute()
            )

        cancelled = len(plan_ids)
        logger.info(
            "Pending plans cancelled",
            extra={"user_id": user_id, "count": cancelled},
        )
        return cancelled

    except Exception:
        logger.exception(
            "Failed to cancel pending plans", extra={"user_id": user_id}
        )
        raise
