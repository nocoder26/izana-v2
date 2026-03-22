"""
Companion API routes — Check-ins, Symptoms, Outcomes.

Provides mood tracking, phase-specific symptom lists, phase content,
and cycle outcome recording.

- GET  /companion/context          — Journey context
- POST /companion/checkin          — Daily mood check-in
- GET  /companion/checkin/history  — Past check-ins (last 30 days)
- GET  /companion/symptoms/{phase} — Phase-specific symptoms
- GET  /companion/content/{phase}  — Phase tips/content
- POST /outcome/record             — Record cycle outcome
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.core.auth import get_user_id
from app.core.database import get_supabase_client
from app.models.enums import ChapterStatus, Mood

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class JourneyContextOut(BaseModel):
    """Current journey context for the companion."""

    phase: Optional[str] = None
    day: int = 0
    treatment_type: Optional[str] = None
    cycle_number: int = 0
    streak: int = 0


class CheckinRequest(BaseModel):
    """Daily mood check-in payload."""

    mood: str
    emotions: list[str] = Field(default_factory=list)

    @field_validator("mood")
    @classmethod
    def validate_mood(cls, v: str) -> str:
        """Ensure mood is one of the allowed values."""
        valid = {m.value for m in Mood}
        if v not in valid:
            raise ValueError(
                f"Mood must be one of: {', '.join(sorted(valid))}"
            )
        return v


class CheckinOut(BaseModel):
    """Mood check-in record."""

    id: str
    mood: str
    emotions: list[str]
    date: str
    created_at: str


class CheckinHistoryOut(BaseModel):
    """List of past check-ins."""

    checkins: list[CheckinOut]


class SymptomOut(BaseModel):
    """Phase-specific symptom."""

    id: str
    name: str
    description: str
    severity: Optional[str] = None


class ContentOut(BaseModel):
    """Phase-specific content / tip."""

    id: str
    title: str
    body: str
    content_type: Optional[str] = None


class OutcomeRequest(BaseModel):
    """Cycle outcome recording payload."""

    outcome: str  # "positive", "negative", "chemical", "uncertain"
    notes: Optional[str] = None

    @field_validator("outcome")
    @classmethod
    def validate_outcome(cls, v: str) -> str:
        valid = {"positive", "negative", "chemical", "uncertain"}
        if v not in valid:
            raise ValueError(f"Outcome must be one of: {', '.join(sorted(valid))}")
        return v


class OutcomeResponse(BaseModel):
    """Response after recording an outcome."""

    success: bool
    message: str
    grief_mode: bool = False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/companion/context", response_model=JourneyContextOut)
async def get_journey_context(
    user_id: Annotated[str, Depends(get_user_id)],
) -> JourneyContextOut:
    """Get the user's current journey context for the companion.

    Returns phase, day count, treatment type, cycle number, and streak.
    """
    supabase = get_supabase_client()

    try:
        journey_resp = (
            supabase.table("journeys")
            .select("*")
            .eq("user_id", user_id)
            .eq("status", "active")
            .maybe_single()
            .execute()
        )
        if not journey_resp.data:
            return JourneyContextOut()

        journey = journey_resp.data

        chapter_resp = (
            supabase.table("chapters")
            .select("*")
            .eq("journey_id", journey["id"])
            .eq("status", ChapterStatus.ACTIVE.value)
            .maybe_single()
            .execute()
        )

        phase = None
        day = 0
        if chapter_resp.data:
            phase = chapter_resp.data["phase"]
            start = datetime.fromisoformat(
                chapter_resp.data["start_date"].replace("Z", "+00:00")
            )
            day = (datetime.now(timezone.utc) - start).days + 1

        gam_resp = (
            supabase.table("gamification")
            .select("current_streak")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        streak = gam_resp.data["current_streak"] if gam_resp.data else 0

        return JourneyContextOut(
            phase=phase,
            day=day,
            treatment_type=journey["treatment_type"],
            cycle_number=journey.get("cycle_number", 1),
            streak=streak,
        )

    except Exception as exc:
        logger.error("Failed to get journey context: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve journey context.",
        )


@router.post(
    "/companion/checkin",
    response_model=CheckinOut,
    status_code=status.HTTP_201_CREATED,
)
async def daily_checkin(
    body: CheckinRequest,
    user_id: Annotated[str, Depends(get_user_id)],
) -> CheckinOut:
    """Record a daily mood check-in.

    Validates mood, enforces UNIQUE constraint on (user_id, date),
    and updates gamification (+10 points, increment streak).
    """
    supabase = get_supabase_client()
    today = date.today().isoformat()

    try:
        # Check for existing check-in today (UNIQUE constraint)
        existing = (
            supabase.table("checkins")
            .select("id")
            .eq("user_id", user_id)
            .eq("date", today)
            .maybe_single()
            .execute()
        )
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already checked in today.",
            )

        checkin_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        supabase.table("checkins").insert(
            {
                "id": checkin_id,
                "user_id": user_id,
                "mood": body.mood,
                "emotions": body.emotions,
                "date": today,
                "created_at": now,
            }
        ).execute()

        # Update gamification: +10 points, increment streak
        try:
            gam_resp = (
                supabase.table("gamification")
                .select("total_points, current_streak")
                .eq("user_id", user_id)
                .maybe_single()
                .execute()
            )
            if gam_resp.data:
                supabase.table("gamification").update(
                    {
                        "total_points": gam_resp.data["total_points"] + 10,
                        "current_streak": gam_resp.data["current_streak"] + 1,
                    }
                ).eq("user_id", user_id).execute()
        except Exception as gam_exc:
            logger.warning("Failed to update gamification: %s", gam_exc)

        return CheckinOut(
            id=checkin_id,
            mood=body.mood,
            emotions=body.emotions,
            date=today,
            created_at=now,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to record check-in: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record check-in.",
        )


@router.get("/companion/checkin/history", response_model=CheckinHistoryOut)
async def checkin_history(
    user_id: Annotated[str, Depends(get_user_id)],
) -> CheckinHistoryOut:
    """Get past check-ins for the last 30 days."""
    supabase = get_supabase_client()

    try:
        cutoff = (date.today() - timedelta(days=30)).isoformat()

        resp = (
            supabase.table("checkins")
            .select("*")
            .eq("user_id", user_id)
            .gte("date", cutoff)
            .order("date", desc=True)
            .execute()
        )

        checkins = [
            CheckinOut(
                id=c["id"],
                mood=c["mood"],
                emotions=c.get("emotions", []),
                date=c["date"],
                created_at=c["created_at"],
            )
            for c in (resp.data or [])
        ]

        return CheckinHistoryOut(checkins=checkins)

    except Exception as exc:
        logger.error("Failed to get checkin history: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve check-in history.",
        )


@router.get("/companion/symptoms/{phase}", response_model=list[SymptomOut])
async def get_phase_symptoms(
    phase: str,
    user_id: Annotated[str, Depends(get_user_id)],
) -> list[SymptomOut]:
    """Get phase-specific symptoms for the given phase.

    Returns a list of symptoms common to the specified treatment phase.
    """
    supabase = get_supabase_client()

    try:
        resp = (
            supabase.table("phase_symptoms")
            .select("*")
            .eq("phase", phase)
            .execute()
        )

        return [
            SymptomOut(
                id=s["id"],
                name=s["name"],
                description=s.get("description", ""),
                severity=s.get("severity"),
            )
            for s in (resp.data or [])
        ]

    except Exception as exc:
        logger.error("Failed to get phase symptoms: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve symptoms.",
        )


@router.get("/companion/content/{phase}", response_model=list[ContentOut])
async def get_phase_content(
    phase: str,
    user_id: Annotated[str, Depends(get_user_id)],
) -> list[ContentOut]:
    """Get phase-specific tips and content for the given phase."""
    supabase = get_supabase_client()

    try:
        resp = (
            supabase.table("phase_content")
            .select("*")
            .eq("phase", phase)
            .execute()
        )

        return [
            ContentOut(
                id=c["id"],
                title=c["title"],
                body=c.get("body", ""),
                content_type=c.get("content_type"),
            )
            for c in (resp.data or [])
        ]

    except Exception as exc:
        logger.error("Failed to get phase content: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve phase content.",
        )


@router.post("/outcome/record", response_model=OutcomeResponse)
async def record_outcome(
    body: OutcomeRequest,
    user_id: Annotated[str, Depends(get_user_id)],
) -> OutcomeResponse:
    """Record a cycle outcome.

    Triggers grief mode if the outcome is negative or chemical.
    """
    supabase = get_supabase_client()

    try:
        # Get active journey
        journey_resp = (
            supabase.table("journeys")
            .select("id")
            .eq("user_id", user_id)
            .eq("status", "active")
            .maybe_single()
            .execute()
        )
        if not journey_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active journey found.",
            )

        journey_id = journey_resp.data["id"]
        now = datetime.now(timezone.utc).isoformat()
        grief_mode = body.outcome in ("negative", "chemical")

        # Record outcome
        supabase.table("outcomes").insert(
            {
                "id": str(uuid4()),
                "journey_id": journey_id,
                "user_id": user_id,
                "outcome": body.outcome,
                "notes": body.notes,
                "created_at": now,
            }
        ).execute()

        # If negative outcome, update active chapter to grief status
        if grief_mode:
            chapter_resp = (
                supabase.table("chapters")
                .select("id")
                .eq("journey_id", journey_id)
                .eq("status", ChapterStatus.ACTIVE.value)
                .maybe_single()
                .execute()
            )
            if chapter_resp.data:
                supabase.table("chapters").update(
                    {"status": ChapterStatus.GRIEF.value}
                ).eq("id", chapter_resp.data["id"]).execute()

        # If positive outcome, update chapter status
        if body.outcome == "positive":
            chapter_resp = (
                supabase.table("chapters")
                .select("id")
                .eq("journey_id", journey_id)
                .eq("status", ChapterStatus.ACTIVE.value)
                .maybe_single()
                .execute()
            )
            if chapter_resp.data:
                supabase.table("chapters").update(
                    {"status": ChapterStatus.POSITIVE.value}
                ).eq("id", chapter_resp.data["id"]).execute()

        message = "Outcome recorded."
        if grief_mode:
            message = (
                "Outcome recorded. We're here for you during this difficult time. "
                "Your companion mode has been adjusted."
            )
        elif body.outcome == "positive":
            message = "Congratulations! Outcome recorded."

        return OutcomeResponse(
            success=True,
            message=message,
            grief_mode=grief_mode,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to record outcome: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record outcome.",
        )
