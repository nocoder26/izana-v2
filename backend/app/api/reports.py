"""
Provider Portal API routes — Shareable reports.

Enables users to generate share tokens for provider access, and
providers to view/download reports via token-based (no auth) endpoints.

- POST /reports/share            — Generate share token
- GET  /reports/portal/{token}   — View shared report (NO auth)
- GET  /reports/download/{token} — Download PDF placeholder
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.auth import get_user_id
from app.core.database import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ShareRequest(BaseModel):
    """Payload for generating a share token."""

    includes: list[str] = Field(
        default_factory=lambda: ["journey", "mood", "plan"],
        description="Data sections to include in the report.",
    )
    expiry_days: int = Field(default=7, ge=1, le=90)


class ShareOut(BaseModel):
    """Generated share token response."""

    share_token: str
    share_url: str
    expires_at: str
    includes: list[str]


class PortalReportOut(BaseModel):
    """Shared report data for provider viewing."""

    pseudonym: str
    generated_at: str
    includes: list[str]
    journey: Optional[dict[str, Any]] = None
    mood_history: Optional[list[dict[str, Any]]] = None
    plan: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/reports/share",
    response_model=ShareOut,
    status_code=status.HTTP_201_CREATED,
)
async def generate_share_token(
    body: ShareRequest,
    user_id: Annotated[str, Depends(get_user_id)],
) -> ShareOut:
    """Generate a share token for provider access.

    Creates a UUID token with configurable data includes and expiry
    (default 7 days).
    """
    supabase = get_supabase_client()

    try:
        share_token = str(uuid4())
        expires_at = (
            datetime.now(timezone.utc) + timedelta(days=body.expiry_days)
        ).isoformat()
        now = datetime.now(timezone.utc).isoformat()

        supabase.table("share_tokens").insert(
            {
                "id": str(uuid4()),
                "user_id": user_id,
                "token": share_token,
                "includes": body.includes,
                "expires_at": expires_at,
                "created_at": now,
            }
        ).execute()

        return ShareOut(
            share_token=share_token,
            share_url=f"/reports/portal/{share_token}",
            expires_at=expires_at,
            includes=body.includes,
        )

    except Exception as exc:
        logger.error("Failed to generate share token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate share token.",
        )


@router.get("/reports/portal/{token}", response_model=PortalReportOut)
async def view_shared_report(
    token: str,
) -> PortalReportOut:
    """View a shared report via token (NO auth required).

    Token-based access for providers. Logs access to phi_audit_log.
    """
    supabase = get_supabase_client()

    try:
        # Look up token
        token_resp = (
            supabase.table("share_tokens")
            .select("*")
            .eq("token", token)
            .maybe_single()
            .execute()
        )
        if not token_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid or expired share token.",
            )

        token_data = token_resp.data

        # Check expiry
        expires_at = datetime.fromisoformat(
            token_data["expires_at"].replace("Z", "+00:00")
        )
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="This share link has expired.",
            )

        user_id = token_data["user_id"]
        includes = token_data.get("includes", [])

        # Log PHI access
        try:
            supabase.table("phi_audit_log").insert(
                {
                    "id": str(uuid4()),
                    "action": "report_viewed",
                    "user_id": user_id,
                    "share_token": token,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ).execute()
        except Exception as log_exc:
            logger.warning("Failed to log PHI access: %s", log_exc)

        # Get user pseudonym
        profile_resp = (
            supabase.table("profiles")
            .select("pseudonym")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        pseudonym = profile_resp.data["pseudonym"] if profile_resp.data else "User"

        # Build report based on includes
        journey_data = None
        mood_history = None
        plan_data = None

        if "journey" in includes:
            journey_resp = (
                supabase.table("journeys")
                .select("treatment_type, cycle_number, status, created_at")
                .eq("user_id", user_id)
                .eq("status", "active")
                .maybe_single()
                .execute()
            )
            if journey_resp.data:
                journey_data = journey_resp.data

        if "mood" in includes:
            from datetime import date

            cutoff = (date.today() - timedelta(days=30)).isoformat()
            mood_resp = (
                supabase.table("checkins")
                .select("mood, date, emotions")
                .eq("user_id", user_id)
                .gte("date", cutoff)
                .order("date", desc=True)
                .execute()
            )
            mood_history = mood_resp.data or []

        if "plan" in includes:
            plan_resp = (
                supabase.table("plans")
                .select("status, plan_data, approved_at, created_at")
                .eq("user_id", user_id)
                .in_("status", ["approved", "modified"])
                .order("created_at", desc=True)
                .limit(1)
                .maybe_single()
                .execute()
            )
            if plan_resp.data:
                plan_data = plan_resp.data

        return PortalReportOut(
            pseudonym=pseudonym,
            generated_at=datetime.now(timezone.utc).isoformat(),
            includes=includes,
            journey=journey_data,
            mood_history=mood_history,
            plan=plan_data,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to view shared report: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve report.",
        )


@router.get("/reports/download/{token}")
async def download_report_pdf(
    token: str,
) -> JSONResponse:
    """Download a shared report as PDF (placeholder).

    PDF generation via reportlab will be implemented later.
    Currently returns a JSON stub indicating the feature is coming.
    """
    supabase = get_supabase_client()

    try:
        # Verify token
        token_resp = (
            supabase.table("share_tokens")
            .select("expires_at, user_id")
            .eq("token", token)
            .maybe_single()
            .execute()
        )
        if not token_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid or expired share token.",
            )

        expires_at = datetime.fromisoformat(
            token_resp.data["expires_at"].replace("Z", "+00:00")
        )
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="This share link has expired.",
            )

        # Log PHI access for download
        try:
            supabase.table("phi_audit_log").insert(
                {
                    "id": str(uuid4()),
                    "action": "report_downloaded",
                    "user_id": token_resp.data["user_id"],
                    "share_token": token,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ).execute()
        except Exception as log_exc:
            logger.warning("Failed to log PHI download: %s", log_exc)

        # TODO: Generate PDF using reportlab
        return JSONResponse(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            content={
                "message": "PDF download is coming soon. Use the portal view for now.",
                "portal_url": f"/reports/portal/{token}",
            },
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to download report: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF.",
        )
