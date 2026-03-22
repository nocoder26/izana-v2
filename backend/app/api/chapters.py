"""
Chapter & Journey Management API routes.

Implements journey lifecycle and chapter tracking (Decision 13):
- GET  /chapters              — List all chapters for current cycle
- GET  /chapters/active       — Get active chapter (phase, day, streak)
- GET  /chapters/{id}/messages — Paginated messages
- POST /journey               — Create treatment journey
- GET  /journey               — Get active journey
- POST /journey/transition    — Record phase transition
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.auth import get_user_id
from app.core.database import get_supabase_client
from app.models.enums import (
    ChapterStatus,
    EggFreezingPhase,
    ExploringPhase,
    IUIPhase,
    IVFPhase,
    NaturalPhase,
    TreatmentType,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Phase ordering per treatment type
# ---------------------------------------------------------------------------

PHASE_ORDER: dict[str, list[str]] = {
    TreatmentType.IVF.value: [p.value for p in IVFPhase],
    TreatmentType.IUI.value: [p.value for p in IUIPhase],
    TreatmentType.NATURAL.value: [p.value for p in NaturalPhase],
    TreatmentType.EGG_FREEZING.value: [p.value for p in EggFreezingPhase],
    TreatmentType.EXPLORING.value: [p.value for p in ExploringPhase],
}

ALL_PHASES: set[str] = set()
for phases in PHASE_ORDER.values():
    ALL_PHASES.update(phases)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ChapterOut(BaseModel):
    """Serialised chapter record."""

    id: str
    journey_id: str
    phase: str
    status: str
    start_date: str
    end_date: Optional[str] = None


class ActiveChapterOut(BaseModel):
    """Active chapter with computed fields."""

    id: str
    journey_id: str
    phase: str
    status: str
    start_date: str
    day: int
    streak: int


class MessageOut(BaseModel):
    """Single chat message."""

    id: str
    role: str
    content: str
    created_at: str


class PaginatedMessages(BaseModel):
    """Paginated message list."""

    messages: list[MessageOut]
    page: int
    per_page: int
    total: int


class CreateJourneyRequest(BaseModel):
    """Payload for creating a new treatment journey."""

    treatment_type: str
    initial_phase: Optional[str] = None

    def validate_treatment(self) -> None:
        """Raise ValueError if treatment_type is invalid."""
        if self.treatment_type not in [t.value for t in TreatmentType]:
            raise ValueError(f"Invalid treatment type: {self.treatment_type}")


class JourneyOut(BaseModel):
    """Serialised journey record."""

    id: str
    user_id: str
    treatment_type: str
    cycle_number: int
    status: str
    created_at: str


class TransitionRequest(BaseModel):
    """Phase transition payload (Decision 13)."""

    target_phase: str
    confirm: bool = False


class TransitionResponse(BaseModel):
    """Phase transition result."""

    success: bool
    message: str
    new_chapter_id: Optional[str] = None
    requires_confirmation: bool = False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/chapters", response_model=list[ChapterOut])
async def list_chapters(
    user_id: Annotated[str, Depends(get_user_id)],
) -> list[ChapterOut]:
    """List all chapters for the current cycle.

    Returns chapters ordered by start_date descending.
    """
    supabase = get_supabase_client()

    try:
        # Get active journey first
        journey_resp = (
            supabase.table("journeys")
            .select("id")
            .eq("user_id", user_id)
            .eq("status", "active")
            .maybe_single()
            .execute()
        )
        if not journey_resp.data:
            return []

        journey_id = journey_resp.data["id"]

        chapters_resp = (
            supabase.table("chapters")
            .select("*")
            .eq("journey_id", journey_id)
            .order("start_date", desc=True)
            .execute()
        )
        return [ChapterOut(**c) for c in (chapters_resp.data or [])]

    except Exception as exc:
        logger.error("Failed to list chapters: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chapters.",
        )


@router.get("/chapters/active", response_model=ActiveChapterOut)
async def get_active_chapter(
    user_id: Annotated[str, Depends(get_user_id)],
) -> ActiveChapterOut:
    """Get the active chapter with phase, day count, and streak.

    Day is computed as the number of days since the chapter started.
    """
    supabase = get_supabase_client()

    try:
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

        chapter_resp = (
            supabase.table("chapters")
            .select("*")
            .eq("journey_id", journey_id)
            .eq("status", ChapterStatus.ACTIVE.value)
            .maybe_single()
            .execute()
        )
        if not chapter_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active chapter found.",
            )

        chapter = chapter_resp.data
        start = datetime.fromisoformat(chapter["start_date"].replace("Z", "+00:00"))
        day = (datetime.now(timezone.utc) - start).days + 1

        # Get streak from gamification
        gam_resp = (
            supabase.table("gamification")
            .select("current_streak")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        streak = gam_resp.data["current_streak"] if gam_resp.data else 0

        return ActiveChapterOut(
            id=chapter["id"],
            journey_id=chapter["journey_id"],
            phase=chapter["phase"],
            status=chapter["status"],
            start_date=chapter["start_date"],
            day=day,
            streak=streak,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get active chapter: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active chapter.",
        )


@router.get("/chapters/{chapter_id}/messages", response_model=PaginatedMessages)
async def get_chapter_messages(
    chapter_id: str,
    user_id: Annotated[str, Depends(get_user_id)],
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=100, ge=1, le=500),
) -> PaginatedMessages:
    """Get paginated messages for a specific chapter.

    Messages are ordered by created_at ascending (oldest first).
    """
    supabase = get_supabase_client()

    try:
        # Verify chapter belongs to user's journey
        chapter_resp = (
            supabase.table("chapters")
            .select("journey_id")
            .eq("id", chapter_id)
            .maybe_single()
            .execute()
        )
        if not chapter_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chapter not found.",
            )

        journey_resp = (
            supabase.table("journeys")
            .select("user_id")
            .eq("id", chapter_resp.data["journey_id"])
            .maybe_single()
            .execute()
        )
        if not journey_resp.data or journey_resp.data["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied.",
            )

        offset = (page - 1) * per_page

        # Get total count
        count_resp = (
            supabase.table("chat_logs")
            .select("id", count="exact")
            .eq("chapter_id", chapter_id)
            .execute()
        )
        total = count_resp.count or 0

        # Get paginated messages
        messages_resp = (
            supabase.table("chat_logs")
            .select("*")
            .eq("chapter_id", chapter_id)
            .order("created_at", desc=False)
            .range(offset, offset + per_page - 1)
            .execute()
        )

        messages = [
            MessageOut(
                id=m["id"],
                role=m.get("role", "user"),
                content=m.get("content", ""),
                created_at=m["created_at"],
            )
            for m in (messages_resp.data or [])
        ]

        return PaginatedMessages(
            messages=messages,
            page=page,
            per_page=per_page,
            total=total,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get chapter messages: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve messages.",
        )


@router.post(
    "/journey",
    response_model=JourneyOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_journey(
    body: CreateJourneyRequest,
    user_id: Annotated[str, Depends(get_user_id)],
) -> JourneyOut:
    """Create a new treatment journey.

    Creates the journey record and an initial chapter for the first phase
    of the selected treatment type.
    """
    supabase = get_supabase_client()

    try:
        body.validate_treatment()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    try:
        # Check for existing active journey
        existing = (
            supabase.table("journeys")
            .select("id")
            .eq("user_id", user_id)
            .eq("status", "active")
            .maybe_single()
            .execute()
        )
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An active journey already exists. Complete or close it first.",
            )

        # Determine initial phase
        phases = PHASE_ORDER.get(body.treatment_type, [])
        initial_phase = body.initial_phase or (phases[0] if phases else "unknown")

        journey_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Create journey
        supabase.table("journeys").insert(
            {
                "id": journey_id,
                "user_id": user_id,
                "treatment_type": body.treatment_type,
                "cycle_number": 1,
                "status": "active",
                "created_at": now,
            }
        ).execute()

        # Create initial chapter
        supabase.table("chapters").insert(
            {
                "id": str(uuid4()),
                "journey_id": journey_id,
                "phase": initial_phase,
                "status": ChapterStatus.ACTIVE.value,
                "start_date": now,
            }
        ).execute()

        return JourneyOut(
            id=journey_id,
            user_id=user_id,
            treatment_type=body.treatment_type,
            cycle_number=1,
            status="active",
            created_at=now,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to create journey: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create journey.",
        )


@router.get("/journey", response_model=JourneyOut)
async def get_active_journey(
    user_id: Annotated[str, Depends(get_user_id)],
) -> JourneyOut:
    """Get the user's active journey."""
    supabase = get_supabase_client()

    try:
        resp = (
            supabase.table("journeys")
            .select("*")
            .eq("user_id", user_id)
            .eq("status", "active")
            .maybe_single()
            .execute()
        )
        if not resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active journey found.",
            )

        return JourneyOut(**resp.data)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get journey: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve journey.",
        )


@router.post("/journey/transition", response_model=TransitionResponse)
async def transition_phase(
    body: TransitionRequest,
    user_id: Annotated[str, Depends(get_user_id)],
) -> TransitionResponse:
    """Record a phase transition (Decision 13).

    Accepts any valid phase for the treatment type. If the transition is
    non-sequential, returns a confirmation prompt. On confirm: closes
    the current chapter, creates a new chapter, and triggers plan
    generation placeholder.
    """
    supabase = get_supabase_client()

    try:
        # Get active journey
        journey_resp = (
            supabase.table("journeys")
            .select("*")
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

        journey = journey_resp.data
        treatment_type = journey["treatment_type"]

        # Validate target phase
        valid_phases = PHASE_ORDER.get(treatment_type, [])
        if body.target_phase not in valid_phases:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid phase '{body.target_phase}' for treatment type '{treatment_type}'.",
            )

        # Get current active chapter
        chapter_resp = (
            supabase.table("chapters")
            .select("*")
            .eq("journey_id", journey["id"])
            .eq("status", ChapterStatus.ACTIVE.value)
            .maybe_single()
            .execute()
        )
        if not chapter_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active chapter found.",
            )

        current_chapter = chapter_resp.data
        current_phase = current_chapter["phase"]

        # Check if transition is sequential
        current_idx = valid_phases.index(current_phase) if current_phase in valid_phases else -1
        target_idx = valid_phases.index(body.target_phase)
        is_sequential = target_idx == current_idx + 1

        if not is_sequential and not body.confirm:
            return TransitionResponse(
                success=False,
                message=(
                    f"Non-sequential transition from '{current_phase}' to "
                    f"'{body.target_phase}'. Set confirm=true to proceed."
                ),
                requires_confirmation=True,
            )

        now = datetime.now(timezone.utc).isoformat()

        # Close current chapter
        supabase.table("chapters").update(
            {
                "status": ChapterStatus.COMPLETED.value,
                "end_date": now,
            }
        ).eq("id", current_chapter["id"]).execute()

        # Create new chapter
        new_chapter_id = str(uuid4())
        supabase.table("chapters").insert(
            {
                "id": new_chapter_id,
                "journey_id": journey["id"],
                "phase": body.target_phase,
                "status": ChapterStatus.ACTIVE.value,
                "start_date": now,
            }
        ).execute()

        # TODO: Trigger plan generation placeholder
        logger.info(
            "Phase transition: %s -> %s (journey=%s, user=%s)",
            current_phase,
            body.target_phase,
            journey["id"],
            user_id,
        )

        return TransitionResponse(
            success=True,
            message=f"Transitioned from '{current_phase}' to '{body.target_phase}'.",
            new_chapter_id=new_chapter_id,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to transition phase: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record phase transition.",
        )
