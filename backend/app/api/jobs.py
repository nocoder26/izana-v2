"""
Background Job Triggers API routes (Admin Auth, for Render Cron).

All endpoints verify ``X-Admin-API-Key`` and enqueue tasks or run inline.

- POST /jobs/evening-summaries       — Trigger evening summary generation
- POST /jobs/phase-transition-checks — Check phase transitions
- POST /jobs/plan-overdue-escalation — Escalate overdue plans
- POST /jobs/nudge-delivery          — Process nudge queue
- POST /jobs/disengagement-sensing   — Detect silent users
- POST /jobs/landing-cache-refresh   — Refresh cached landing responses
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import get_admin_key

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class JobResponse(BaseModel):
    """Standard job trigger response."""

    success: bool
    job_name: str
    message: str
    triggered_at: str


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _job_response(job_name: str, message: str) -> JobResponse:
    """Create a standard job response."""
    return JobResponse(
        success=True,
        job_name=job_name,
        message=message,
        triggered_at=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/jobs/evening-summaries", response_model=JobResponse)
async def trigger_evening_summaries(
    _admin_key: Annotated[str, Depends(get_admin_key)],
) -> JobResponse:
    """Trigger evening summary generation for all active users.

    Typically called by Render Cron at the end of each day.
    """
    try:
        # TODO: Enqueue evening summary task for each active user
        # For now, log and return success
        logger.info("Evening summaries job triggered")

        return _job_response(
            "evening-summaries",
            "Evening summary generation triggered.",
        )

    except Exception as exc:
        logger.error("Failed to trigger evening summaries: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger evening summaries.",
        )


@router.post("/jobs/phase-transition-checks", response_model=JobResponse)
async def trigger_phase_transition_checks(
    _admin_key: Annotated[str, Depends(get_admin_key)],
) -> JobResponse:
    """Check for users who may need a phase transition.

    Detects users whose phase duration has exceeded expected ranges
    and flags them for review or nudging.
    """
    try:
        # TODO: Query active chapters and check durations against expected ranges
        logger.info("Phase transition checks job triggered")

        return _job_response(
            "phase-transition-checks",
            "Phase transition checks triggered.",
        )

    except Exception as exc:
        logger.error("Failed to trigger phase transition checks: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger phase transition checks.",
        )


@router.post("/jobs/plan-overdue-escalation", response_model=JobResponse)
async def trigger_plan_overdue_escalation(
    _admin_key: Annotated[str, Depends(get_admin_key)],
) -> JobResponse:
    """Escalate overdue plans in the nutritionist queue.

    Plans that have been pending review beyond the SLA are escalated
    (priority bumped, notifications sent).
    """
    try:
        # TODO: Query plans past their deadline and escalate priority
        logger.info("Plan overdue escalation job triggered")

        return _job_response(
            "plan-overdue-escalation",
            "Plan overdue escalation triggered.",
        )

    except Exception as exc:
        logger.error("Failed to trigger plan overdue escalation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger plan overdue escalation.",
        )


@router.post("/jobs/nudge-delivery", response_model=JobResponse)
async def trigger_nudge_delivery(
    _admin_key: Annotated[str, Depends(get_admin_key)],
) -> JobResponse:
    """Process the nudge queue and deliver pending nudges.

    Sends push notifications and in-app nudges based on user
    preferences and timing rules.
    """
    try:
        # TODO: Query nudge queue, filter by delivery time, send notifications
        logger.info("Nudge delivery job triggered")

        return _job_response(
            "nudge-delivery",
            "Nudge delivery triggered.",
        )

    except Exception as exc:
        logger.error("Failed to trigger nudge delivery: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger nudge delivery.",
        )


@router.post("/jobs/disengagement-sensing", response_model=JobResponse)
async def trigger_disengagement_sensing(
    _admin_key: Annotated[str, Depends(get_admin_key)],
) -> JobResponse:
    """Detect silent/disengaged users and queue re-engagement nudges.

    Identifies users who haven't interacted within a configurable
    window and prepares personalised re-engagement messages.
    """
    try:
        # TODO: Query users with no recent activity, queue re-engagement nudges
        logger.info("Disengagement sensing job triggered")

        return _job_response(
            "disengagement-sensing",
            "Disengagement sensing triggered.",
        )

    except Exception as exc:
        logger.error("Failed to trigger disengagement sensing: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger disengagement sensing.",
        )


@router.post("/jobs/landing-cache-refresh", response_model=JobResponse)
async def trigger_landing_cache_refresh(
    _admin_key: Annotated[str, Depends(get_admin_key)],
) -> JobResponse:
    """Refresh the cached landing page preview responses.

    Runs the swarm pipeline for the predefined landing page questions
    and updates the Redis cache (24-hour TTL).
    """
    try:
        # TODO: Run pipeline for each preview question, update Redis cache
        logger.info("Landing cache refresh job triggered")

        return _job_response(
            "landing-cache-refresh",
            "Landing cache refresh triggered.",
        )

    except Exception as exc:
        logger.error("Failed to trigger landing cache refresh: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger landing cache refresh.",
        )
