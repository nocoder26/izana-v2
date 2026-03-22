"""
Content Library API routes.

Provides browsing, streaming, progress tracking, and rating for
wellness content (videos, audio, articles).

- GET  /content/library          — Browse content (filter by phase, type)
- GET  /content/{id}/stream-url  — Get signed Cloudflare Stream URL (placeholder)
- POST /content/{id}/progress    — Update watch/listen progress
- POST /content/{id}/rating      — Rate content (1-5 stars)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from app.core.auth import get_user_id
from app.core.database import get_supabase_admin as get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ContentItem(BaseModel):
    """Single content library item."""

    id: str
    title: str
    description: Optional[str] = None
    content_type: str
    treatment_phases: list[str] = Field(default_factory=list)
    treatment_types: list[str] = Field(default_factory=list)
    duration_seconds: Optional[int] = None
    thumbnail_url: Optional[str] = None
    intensity: Optional[str] = None
    sort_order: int = 0


class ContentLibraryOut(BaseModel):
    """Content library listing."""

    items: list[ContentItem]
    total: int


class StreamUrlOut(BaseModel):
    """Signed streaming URL response."""

    stream_url: str
    expires_at: str


class ProgressRequest(BaseModel):
    """Progress update payload (debounced from client)."""

    position_seconds: int = Field(..., ge=0)
    completed: bool = False


class ProgressOut(BaseModel):
    """Progress update response."""

    content_id: str
    position_seconds: int
    completed: bool


class RatingRequest(BaseModel):
    """Content rating payload."""

    rating: int
    feedback: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: int) -> int:
        """Ensure rating is between 1 and 5."""
        if v < 1 or v > 5:
            raise ValueError("Rating must be between 1 and 5.")
        return v


class RatingOut(BaseModel):
    """Rating confirmation."""

    content_id: str
    rating: int
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/content/library", response_model=ContentLibraryOut)
async def browse_content(
    user_id: Annotated[str, Depends(get_user_id)],
    phase: Optional[str] = Query(default=None, description="Filter by treatment phase"),
    content_type: Optional[str] = Query(default=None, description="Filter by content type"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
) -> ContentLibraryOut:
    """Browse the content library with optional filters.

    Supports filtering by phase and content type, with pagination.
    Returns empty list if no content exists (not 500).
    """
    supabase = get_supabase_client()

    try:
        query = (
            supabase.table("wellness_content")
            .select("*", count="exact")
            .eq("is_active", True)
        )

        if phase:
            query = query.contains("treatment_phases", [phase])
        if content_type:
            query = query.eq("content_type", content_type)

        offset = (page - 1) * per_page
        query = query.order("sort_order", desc=False).range(offset, offset + per_page - 1)

        resp = query.execute()
        total = resp.count or 0

        items = [
            ContentItem(
                id=c["id"],
                title=c["title"],
                description=c.get("description"),
                content_type=c["content_type"],
                treatment_phases=c.get("treatment_phases") or [],
                treatment_types=c.get("treatment_types") or [],
                duration_seconds=c.get("duration_seconds"),
                thumbnail_url=c.get("thumbnail_url"),
                intensity=c.get("intensity"),
                sort_order=c.get("sort_order", 0),
            )
            for c in (resp.data or [])
        ]

        return ContentLibraryOut(items=items, total=total)

    except Exception as exc:
        logger.error("Failed to browse content: %s", exc)
        # Return empty list rather than 500 if the table is empty or query fails gracefully
        return ContentLibraryOut(items=[], total=0)


@router.get("/content/{content_id}/stream-url", response_model=StreamUrlOut)
async def get_stream_url(
    content_id: str,
    user_id: Annotated[str, Depends(get_user_id)],
) -> StreamUrlOut:
    """Get a signed Cloudflare Stream URL for video/audio content.

    This is a placeholder implementation. In production, this will
    generate a signed URL via the Cloudflare Stream API.
    """
    supabase = get_supabase_client()

    try:
        # Verify content exists
        resp = (
            supabase.table("wellness_content")
            .select("id, title, content_type, cloudflare_stream_id")
            .eq("id", content_id)
            .maybe_single()
            .execute()
        )
        if not resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Content not found.",
            )

        # Placeholder: In production, generate a signed Cloudflare Stream URL
        expires_at = (
            datetime.now(timezone.utc) + timedelta(hours=2)
        ).isoformat()

        stream_id = resp.data.get("cloudflare_stream_id") or content_id

        return StreamUrlOut(
            stream_url=f"https://stream.cloudflare.com/placeholder/{stream_id}",
            expires_at=expires_at,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get stream URL: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate stream URL.",
        )


@router.post("/content/{content_id}/progress", response_model=ProgressOut)
async def update_progress(
    content_id: str,
    body: ProgressRequest,
    user_id: Annotated[str, Depends(get_user_id)],
) -> ProgressOut:
    """Update watch/listen progress for content.

    The client debounces position updates to avoid excessive writes.
    Uses upsert to maintain a single progress record per user/content.
    """
    supabase = get_supabase_client()

    try:
        now = datetime.now(timezone.utc).isoformat()

        upsert_data: dict[str, Any] = {
            "user_id": user_id,
            "content_id": content_id,
            "position_seconds": body.position_seconds,
            "completed": body.completed,
            "updated_at": now,
        }
        if body.completed:
            upsert_data["completed_at"] = now

        supabase.table("content_progress").upsert(
            upsert_data,
            on_conflict="user_id,content_id",
        ).execute()

        return ProgressOut(
            content_id=content_id,
            position_seconds=body.position_seconds,
            completed=body.completed,
        )

    except Exception as exc:
        logger.error("Failed to update progress: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update content progress.",
        )


@router.post("/content/{content_id}/rating", response_model=RatingOut)
async def rate_content(
    content_id: str,
    body: RatingRequest,
    user_id: Annotated[str, Depends(get_user_id)],
) -> RatingOut:
    """Rate content (1-5 with optional feedback).

    Uses upsert so a user can update their rating.
    """
    supabase = get_supabase_client()

    try:
        # Verify content exists
        content_resp = (
            supabase.table("wellness_content")
            .select("id")
            .eq("id", content_id)
            .maybe_single()
            .execute()
        )
        if not content_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Content not found.",
            )

        now = datetime.now(timezone.utc).isoformat()

        supabase.table("content_ratings").upsert(
            {
                "user_id": user_id,
                "content_id": content_id,
                "rating": body.rating,
                "feedback": body.feedback,
                "created_at": now,
            },
            on_conflict="user_id,content_id",
        ).execute()

        return RatingOut(
            content_id=content_id,
            rating=body.rating,
            message="Thank you for your feedback!",
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to rate content: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit rating.",
        )
