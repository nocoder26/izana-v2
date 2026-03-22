"""
Coach API routes — Partner & Gamification.

Partner endpoints are gated behind FEATURE_PARTNER_ENABLED.

- POST   /partner/invite       — Generate invite code
- POST   /partner/join         — Join with invite code
- GET    /partner/dashboard    — Partner view data
- GET    /partner/status       — Link status
- PUT    /partner/visibility   — Update what partner can see
- DELETE /partner/link         — Revoke partner link
- GET    /gamification/summary — Points, streak, level, badges
- GET    /gamification/badges  — All earned + available badges
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.auth import get_user_id
from app.core.database import get_supabase_admin as get_supabase_client
from app.core.feature_flags import require_feature

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class InviteOut(BaseModel):
    """Generated partner invite."""

    invite_code: str
    expires_at: str


class JoinRequest(BaseModel):
    """Partner join payload."""

    invite_code: str


class JoinResponse(BaseModel):
    """Partner join result."""

    success: bool
    message: str
    partner_pseudonym: Optional[str] = None


class PartnerDashboardOut(BaseModel):
    """Partner view data."""

    partner_pseudonym: str
    mood_today: Optional[str] = None
    current_phase: Optional[str] = None
    streak: int = 0
    visible_fields: list[str] = Field(default_factory=list)


class PartnerStatusOut(BaseModel):
    """Partner link status."""

    linked: bool
    partner_pseudonym: Optional[str] = None
    linked_at: Optional[str] = None


class VisibilityUpdate(BaseModel):
    """Payload for updating partner visibility settings."""

    visible_fields: list[str]


class VisibilityOut(BaseModel):
    """Updated visibility response."""

    visible_fields: list[str]


class GamificationSummary(BaseModel):
    """Gamification summary."""

    total_points: int
    current_streak: int
    level: int
    level_name: str
    badges_earned: int


class BadgeOut(BaseModel):
    """Single badge."""

    id: str
    name: str
    description: str
    icon: Optional[str] = None
    earned: bool
    earned_at: Optional[str] = None


class BadgesOut(BaseModel):
    """All badges with earn status."""

    badges: list[BadgeOut]


# ---------------------------------------------------------------------------
# Partner endpoints (feature-gated)
# ---------------------------------------------------------------------------


@router.post(
    "/partner/invite",
    response_model=InviteOut,
    dependencies=[require_feature("PARTNER")],
)
async def generate_invite(
    user_id: Annotated[str, Depends(get_user_id)],
) -> InviteOut:
    """Generate a partner invite code.

    Creates a URL-safe invite code valid for 7 days.
    """
    supabase = get_supabase_client()

    try:
        invite_code = secrets.token_urlsafe(16)
        expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

        supabase.table("partner_links").insert(
            {
                "id": str(uuid4()),
                "primary_user_id": user_id,
                "invite_code": invite_code,
                "invite_expires_at": expires_at,
                "is_active": True,
            }
        ).execute()

        return InviteOut(invite_code=invite_code, expires_at=expires_at)

    except Exception as exc:
        logger.error("Failed to generate invite: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate invite code.",
        )


@router.post(
    "/partner/join",
    response_model=JoinResponse,
    dependencies=[require_feature("PARTNER")],
)
async def join_partner(
    body: JoinRequest,
    user_id: Annotated[str, Depends(get_user_id)],
) -> JoinResponse:
    """Join with an invite code to link as a partner."""
    supabase = get_supabase_client()

    try:
        # Look up invite
        invite_resp = (
            supabase.table("partner_links")
            .select("*")
            .eq("invite_code", body.invite_code)
            .is_("partner_user_id", "null")
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if not invite_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid or expired invite code.",
            )

        invite = invite_resp.data

        # Check expiry
        if invite.get("invite_expires_at"):
            expires_at = datetime.fromisoformat(
                invite["invite_expires_at"].replace("Z", "+00:00")
            )
            if datetime.now(timezone.utc) > expires_at:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="This invite code has expired.",
                )

        # Cannot link to yourself
        if invite["primary_user_id"] == user_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You cannot link to yourself.",
            )

        # Update partner link to set the partner
        supabase.table("partner_links").update(
            {"partner_user_id": user_id}
        ).eq("id", invite["id"]).execute()

        # Get partner pseudonym
        profile_resp = (
            supabase.table("profiles")
            .select("pseudonym")
            .eq("id", invite["primary_user_id"])
            .limit(1)
            .execute()
        )
        pseudonym = profile_resp.data[0]["pseudonym"] if profile_resp.data else "Partner"

        return JoinResponse(
            success=True,
            message="Successfully linked as a partner!",
            partner_pseudonym=pseudonym,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to join partner: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to join with invite code.",
        )


@router.get(
    "/partner/dashboard",
    response_model=PartnerDashboardOut,
    dependencies=[require_feature("PARTNER")],
)
async def get_partner_dashboard(
    user_id: Annotated[str, Depends(get_user_id)],
) -> PartnerDashboardOut:
    """Get partner view data.

    Shows the linked user's data based on visibility settings.
    """
    supabase = get_supabase_client()

    try:
        # Find partner link where this user is the partner
        link_resp = (
            supabase.table("partner_links")
            .select("*")
            .eq("partner_user_id", user_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if not link_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No partner link found.",
            )

        link = link_resp.data
        linked_user_id = link["primary_user_id"]
        visibility = link.get("visibility_settings") or {}

        # Build visible_fields list from the JSONB settings
        visible_fields = [k for k, v in visibility.items() if v is True]

        # Get partner profile
        profile_resp = (
            supabase.table("profiles")
            .select("pseudonym")
            .eq("id", linked_user_id)
            .limit(1)
            .execute()
        )
        pseudonym = profile_resp.data[0]["pseudonym"] if profile_resp.data else "Partner"

        mood_today = None
        current_phase = None
        streak = 0

        if visibility.get("mood"):
            from datetime import date as date_type

            checkin_resp = (
                supabase.table("emotion_logs")
                .select("mood")
                .eq("user_id", linked_user_id)
                .eq("date", date_type.today().isoformat())
                .limit(1)
                .execute()
            )
            if checkin_resp.data:
                mood_today = checkin_resp.data[0]["mood"]

        if visibility.get("phase"):
            chapter_resp = (
                supabase.table("chapters")
                .select("phase")
                .eq("user_id", linked_user_id)
                .eq("status", "active")
                .limit(1)
                .execute()
            )
            if chapter_resp.data:
                current_phase = chapter_resp.data[0]["phase"]

        if visibility.get("streak") or visibility.get("plan_adherence"):
            gam_resp = (
                supabase.table("user_gamification")
                .select("current_streak")
                .eq("user_id", linked_user_id)
                .limit(1)
                .execute()
            )
            if gam_resp.data:
                streak = gam_resp.data[0]["current_streak"]

        return PartnerDashboardOut(
            partner_pseudonym=pseudonym,
            mood_today=mood_today,
            current_phase=current_phase,
            streak=streak,
            visible_fields=visible_fields,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get partner dashboard: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve partner dashboard.",
        )


@router.get(
    "/partner/status",
    response_model=PartnerStatusOut,
    dependencies=[require_feature("PARTNER")],
)
async def get_partner_status(
    user_id: Annotated[str, Depends(get_user_id)],
) -> PartnerStatusOut:
    """Get partner link status."""
    supabase = get_supabase_client()

    try:
        # Check if user has a partner link (as primary user)
        link_resp = (
            supabase.table("partner_links")
            .select("*")
            .eq("primary_user_id", user_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if link_resp.data and link_resp.data[0].get("partner_user_id"):
            profile_resp = (
                supabase.table("profiles")
                .select("pseudonym")
                .eq("id", link_resp.data[0]["partner_user_id"])
                .limit(1)
                .execute()
            )
            return PartnerStatusOut(
                linked=True,
                partner_pseudonym=profile_resp.data[0]["pseudonym"] if profile_resp.data else None,
                linked_at=link_resp.data[0].get("created_at"),
            )

        # Check as partner
        link_resp2 = (
            supabase.table("partner_links")
            .select("*")
            .eq("partner_user_id", user_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if link_resp2.data:
            profile_resp = (
                supabase.table("profiles")
                .select("pseudonym")
                .eq("id", link_resp2.data["primary_user_id"])
                .limit(1)
                .execute()
            )
            return PartnerStatusOut(
                linked=True,
                partner_pseudonym=profile_resp.data[0]["pseudonym"] if profile_resp.data else None,
                linked_at=link_resp2.data.get("created_at"),
            )

        return PartnerStatusOut(linked=False)

    except Exception as exc:
        logger.error("Failed to get partner status: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve partner status.",
        )


@router.put(
    "/partner/visibility",
    response_model=VisibilityOut,
    dependencies=[require_feature("PARTNER")],
)
async def update_visibility(
    body: VisibilityUpdate,
    user_id: Annotated[str, Depends(get_user_id)],
) -> VisibilityOut:
    """Update what the partner can see."""
    supabase = get_supabase_client()

    try:
        # Convert list of field names to JSONB visibility_settings
        visibility_settings = {field: True for field in body.visible_fields}

        resp = (
            supabase.table("partner_links")
            .update({"visibility_settings": visibility_settings})
            .eq("primary_user_id", user_id)
            .eq("is_active", True)
            .execute()
        )
        if not resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No partner link found.",
            )

        return VisibilityOut(visible_fields=body.visible_fields)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to update visibility: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update partner visibility.",
        )


@router.delete(
    "/partner/link",
    dependencies=[require_feature("PARTNER")],
)
async def revoke_partner_link(
    user_id: Annotated[str, Depends(get_user_id)],
) -> dict:
    """Revoke the partner link."""
    supabase = get_supabase_client()

    try:
        # Deactivate links where user is either party
        supabase.table("partner_links").update(
            {"is_active": False}
        ).eq("primary_user_id", user_id).execute()

        supabase.table("partner_links").update(
            {"is_active": False}
        ).eq("partner_user_id", user_id).execute()

        return {"success": True, "message": "Partner link revoked."}

    except Exception as exc:
        logger.error("Failed to revoke partner link: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke partner link.",
        )


# ---------------------------------------------------------------------------
# Gamification endpoints (no feature gate)
# ---------------------------------------------------------------------------


@router.get("/gamification/summary", response_model=GamificationSummary)
async def get_gamification_summary(
    user_id: Annotated[str, Depends(get_user_id)],
) -> GamificationSummary:
    """Get gamification summary: points, streak, level, badges earned."""
    supabase = get_supabase_client()

    try:
        gam_resp = (
            supabase.table("user_gamification")
            .select("total_points, current_streak, level, level_name")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        gam = gam_resp.data[0] if gam_resp.data else {
            "total_points": 0,
            "current_streak": 0,
            "level": 1,
            "level_name": "Beginner",
        }

        # Count earned badges
        badges_resp = (
            supabase.table("user_badges")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        badges_earned = badges_resp.count or 0

        return GamificationSummary(
            total_points=gam["total_points"],
            current_streak=gam["current_streak"],
            level=gam["level"],
            level_name=gam["level_name"],
            badges_earned=badges_earned,
        )

    except Exception as exc:
        logger.error("Failed to get gamification summary: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve gamification summary.",
        )


@router.get("/gamification/badges", response_model=BadgesOut)
async def get_badges(
    user_id: Annotated[str, Depends(get_user_id)],
) -> BadgesOut:
    """Get all earned and available badges."""
    supabase = get_supabase_client()

    try:
        # Get all badge definitions
        all_badges_resp = (
            supabase.table("badges")
            .select("*")
            .execute()
        )

        # Get user's earned badges
        earned_resp = (
            supabase.table("user_badges")
            .select("badge_id, earned_at")
            .eq("user_id", user_id)
            .execute()
        )
        earned_map = {
            e["badge_id"]: e["earned_at"] for e in (earned_resp.data or [])
        }

        badges = []
        for b in (all_badges_resp.data or []):
            badge_id = b["id"]
            badges.append(
                BadgeOut(
                    id=badge_id,
                    name=b["name"],
                    description=b.get("description", ""),
                    icon=b.get("icon"),
                    earned=badge_id in earned_map,
                    earned_at=earned_map.get(badge_id),
                )
            )

        return BadgesOut(badges=badges)

    except Exception as exc:
        logger.error("Failed to get badges: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve badges.",
        )
