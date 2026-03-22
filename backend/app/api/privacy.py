"""
GDPR Privacy API routes.

Provides account deletion and data export endpoints.

- DELETE /delete-account — Mark account for deletion (30-day grace)
- GET    /data-export    — Generate JSON export of all user data
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.auth import get_user_id
from app.core.database import get_supabase_admin as get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class DeleteAccountResponse(BaseModel):
    """Account deletion response."""

    success: bool
    message: str
    deletion_date: str


class DataExportOut(BaseModel):
    """Data export response wrapper."""

    user_id: str
    exported_at: str
    data: dict[str, Any]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.delete("/delete-account", response_model=DeleteAccountResponse)
async def delete_account(
    user_id: Annotated[str, Depends(get_user_id)],
) -> DeleteAccountResponse:
    """Mark account for deletion with a 30-day grace period.

    The account will be permanently deleted after 30 days. The user
    can log in during the grace period to cancel the deletion.
    """
    supabase = get_supabase_client()

    try:
        deletion_date = (
            datetime.now(timezone.utc) + timedelta(days=30)
        ).isoformat()
        now = datetime.now(timezone.utc).isoformat()

        # Mark profile for deletion
        supabase.table("profiles").update(
            {
                "deletion_requested_at": now,
                "deletion_scheduled_for": deletion_date,
            }
        ).eq("id", user_id).execute()

        # Log the request
        try:
            supabase.table("phi_audit_log").insert(
                {
                    "id": str(uuid4()),
                    "action": "account_deletion_requested",
                    "user_id": user_id,
                    "created_at": now,
                }
            ).execute()
        except Exception as log_exc:
            logger.warning("Failed to log deletion request: %s", log_exc)

        return DeleteAccountResponse(
            success=True,
            message=(
                "Your account has been scheduled for deletion. "
                "You have 30 days to log in and cancel this request."
            ),
            deletion_date=deletion_date,
        )

    except Exception as exc:
        logger.error("Failed to request account deletion: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process deletion request.",
        )


@router.get("/data-export", response_model=DataExportOut)
async def export_user_data(
    user_id: Annotated[str, Depends(get_user_id)],
) -> DataExportOut:
    """Generate a JSON export of all user data (GDPR data portability).

    Collects profile, journey, chapters, check-ins, meal/activity logs,
    gamification, and chat history into a single JSON response.
    """
    supabase = get_supabase_client()

    try:
        now = datetime.now(timezone.utc).isoformat()
        data: dict[str, Any] = {}

        # Profile
        profile_resp = (
            supabase.table("profiles")
            .select("*")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        data["profile"] = profile_resp.data

        # Journeys
        journeys_resp = (
            supabase.table("journeys")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        data["journeys"] = journeys_resp.data or []

        # Chapters (via journeys)
        journey_ids = [j["id"] for j in data["journeys"]]
        if journey_ids:
            chapters_resp = (
                supabase.table("chapters")
                .select("*")
                .in_("journey_id", journey_ids)
                .execute()
            )
            data["chapters"] = chapters_resp.data or []
        else:
            data["chapters"] = []

        # Check-ins
        checkins_resp = (
            supabase.table("checkins")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        data["checkins"] = checkins_resp.data or []

        # Meal logs
        meals_resp = (
            supabase.table("meal_logs")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        data["meal_logs"] = meals_resp.data or []

        # Activity logs
        activities_resp = (
            supabase.table("activity_logs")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        data["activity_logs"] = activities_resp.data or []

        # Gamification
        gam_resp = (
            supabase.table("gamification")
            .select("*")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        data["gamification"] = gam_resp.data

        # Chat logs
        chat_resp = (
            supabase.table("chat_logs")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .execute()
        )
        data["chat_logs"] = chat_resp.data or []

        # Outcomes
        outcomes_resp = (
            supabase.table("outcomes")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        data["outcomes"] = outcomes_resp.data or []

        # Plans
        plans_resp = (
            supabase.table("plans")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        data["plans"] = plans_resp.data or []

        # Log the export
        try:
            supabase.table("phi_audit_log").insert(
                {
                    "id": str(uuid4()),
                    "action": "data_export",
                    "user_id": user_id,
                    "created_at": now,
                }
            ).execute()
        except Exception as log_exc:
            logger.warning("Failed to log data export: %s", log_exc)

        return DataExportOut(
            user_id=user_id,
            exported_at=now,
            data=data,
        )

    except Exception as exc:
        logger.error("Failed to export user data: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate data export.",
        )
