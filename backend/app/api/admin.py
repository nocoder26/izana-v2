"""
Admin Dashboard API routes (Admin Auth).

All endpoints require ``get_admin_key`` authentication.

- GET /admin/dashboard            — KPI overview
- GET /admin/analytics/gaps       — Knowledge gaps
- GET /admin/analytics/citations  — Citation stats
- GET /admin/analytics/sentiment  — Sentiment trends
- GET /admin/health               — Swarm health (all 11 swarms)
- GET /admin/prompts/{swarm_id}   — Get swarm prompt
- PUT /admin/prompts/{swarm_id}   — Update swarm prompt (versioned)
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Annotated, Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.auth import get_admin_key
from app.core.database import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class KPIDashboard(BaseModel):
    """Admin KPI overview."""

    total_users: int
    active_today: int
    plans_pending_review: int
    plans_approved_total: int
    average_accuracy: Optional[float] = None
    queue_depth: int


class KnowledgeGap(BaseModel):
    """Single knowledge gap entry."""

    id: str
    question: str
    frequency: int
    category: Optional[str] = None
    created_at: str


class GapsOut(BaseModel):
    """Knowledge gaps listing."""

    gaps: list[KnowledgeGap]
    total: int


class CitationStat(BaseModel):
    """Citation usage statistics."""

    source_title: str
    usage_count: int
    average_relevance: float


class CitationsOut(BaseModel):
    """Citation statistics."""

    citations: list[CitationStat]


class SentimentEntry(BaseModel):
    """Sentiment trend data point."""

    date: str
    average_sentiment: float
    message_count: int


class SentimentOut(BaseModel):
    """Sentiment trends."""

    trends: list[SentimentEntry]


class SwarmHealthItem(BaseModel):
    """Health status for a single swarm."""

    swarm_id: str
    name: str
    status: str  # healthy, degraded, down
    last_response_ms: Optional[int] = None
    error_rate: Optional[float] = None


class SwarmHealthOut(BaseModel):
    """Health status for all swarms."""

    swarms: list[SwarmHealthItem]


class PromptOut(BaseModel):
    """Swarm prompt data."""

    swarm_id: str
    prompt_text: str
    version: int
    updated_at: str


class PromptUpdateRequest(BaseModel):
    """Swarm prompt update payload."""

    prompt_text: str


class PromptUpdateResponse(BaseModel):
    """Prompt update confirmation."""

    success: bool
    swarm_id: str
    version: int
    message: str


# ---------------------------------------------------------------------------
# Swarm definitions
# ---------------------------------------------------------------------------

SWARM_NAMES: dict[str, str] = {
    "0": "Translator",
    "1": "Gatekeeper",
    "2": "Context Builder",
    "3": "Clinical Brain (RAG)",
    "4": "Response Curator",
    "5": "Compliance Checker",
    "6": "Sentiment Analyser",
    "7": "Gap Detector",
    "8": "Plan Generator",
    "9": "Evening Summary",
    "10": "Nudge Engine",
}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/admin/dashboard", response_model=KPIDashboard)
async def get_admin_dashboard(
    _admin_key: Annotated[str, Depends(get_admin_key)],
) -> KPIDashboard:
    """Get KPI overview: user count, active today, accuracy, queue depth."""
    supabase = get_supabase_client()

    try:
        # Total users
        users_resp = (
            supabase.table("profiles")
            .select("id", count="exact")
            .execute()
        )
        total_users = users_resp.count or 0

        # Active today (users who have chat logs today)
        today = date.today().isoformat()
        active_resp = (
            supabase.table("chat_logs")
            .select("user_id", count="exact")
            .gte("created_at", today)
            .execute()
        )
        active_today = active_resp.count or 0

        # Plans pending review
        pending_resp = (
            supabase.table("plans")
            .select("id", count="exact")
            .in_("status", ["pending_nutritionist", "in_review"])
            .execute()
        )
        plans_pending = pending_resp.count or 0

        # Total approved plans
        approved_resp = (
            supabase.table("plans")
            .select("id", count="exact")
            .in_("status", ["approved", "modified"])
            .execute()
        )
        plans_approved = approved_resp.count or 0

        return KPIDashboard(
            total_users=total_users,
            active_today=active_today,
            plans_pending_review=plans_pending,
            plans_approved_total=plans_approved,
            queue_depth=plans_pending,
        )

    except Exception as exc:
        logger.error("Failed to get admin dashboard: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard.",
        )


@router.get("/admin/analytics/gaps", response_model=GapsOut)
async def get_knowledge_gaps(
    _admin_key: Annotated[str, Depends(get_admin_key)],
) -> GapsOut:
    """Get knowledge gaps detected by the gap detector swarm."""
    supabase = get_supabase_client()

    try:
        resp = (
            supabase.table("knowledge_gaps")
            .select("*", count="exact")
            .order("frequency", desc=True)
            .limit(50)
            .execute()
        )
        total = resp.count or 0

        gaps = [
            KnowledgeGap(
                id=g["id"],
                question=g["question"],
                frequency=g.get("frequency", 1),
                category=g.get("category"),
                created_at=g["created_at"],
            )
            for g in (resp.data or [])
        ]

        return GapsOut(gaps=gaps, total=total)

    except Exception as exc:
        logger.error("Failed to get knowledge gaps: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve knowledge gaps.",
        )


@router.get("/admin/analytics/citations", response_model=CitationsOut)
async def get_citation_stats(
    _admin_key: Annotated[str, Depends(get_admin_key)],
) -> CitationsOut:
    """Get citation usage statistics from RAG sources."""
    supabase = get_supabase_client()

    try:
        resp = (
            supabase.table("citation_stats")
            .select("*")
            .order("usage_count", desc=True)
            .limit(50)
            .execute()
        )

        citations = [
            CitationStat(
                source_title=c["source_title"],
                usage_count=c["usage_count"],
                average_relevance=c.get("average_relevance", 0.0),
            )
            for c in (resp.data or [])
        ]

        return CitationsOut(citations=citations)

    except Exception as exc:
        logger.error("Failed to get citation stats: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve citation statistics.",
        )


@router.get("/admin/analytics/sentiment", response_model=SentimentOut)
async def get_sentiment_trends(
    _admin_key: Annotated[str, Depends(get_admin_key)],
) -> SentimentOut:
    """Get sentiment trends over time."""
    supabase = get_supabase_client()

    try:
        resp = (
            supabase.table("sentiment_daily")
            .select("*")
            .order("date", desc=True)
            .limit(30)
            .execute()
        )

        trends = [
            SentimentEntry(
                date=s["date"],
                average_sentiment=s.get("average_sentiment", 0.0),
                message_count=s.get("message_count", 0),
            )
            for s in (resp.data or [])
        ]

        return SentimentOut(trends=trends)

    except Exception as exc:
        logger.error("Failed to get sentiment trends: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sentiment trends.",
        )


@router.get("/admin/health", response_model=SwarmHealthOut)
async def get_swarm_health(
    _admin_key: Annotated[str, Depends(get_admin_key)],
) -> SwarmHealthOut:
    """Get health status for all 11 swarms."""
    supabase = get_supabase_client()

    try:
        # Try to read from a health status table
        resp = (
            supabase.table("swarm_health")
            .select("*")
            .execute()
        )

        health_map: dict[str, dict[str, Any]] = {}
        for h in (resp.data or []):
            health_map[h["swarm_id"]] = h

        swarms = []
        for swarm_id, name in SWARM_NAMES.items():
            if swarm_id in health_map:
                h = health_map[swarm_id]
                swarms.append(
                    SwarmHealthItem(
                        swarm_id=swarm_id,
                        name=name,
                        status=h.get("status", "unknown"),
                        last_response_ms=h.get("last_response_ms"),
                        error_rate=h.get("error_rate"),
                    )
                )
            else:
                swarms.append(
                    SwarmHealthItem(
                        swarm_id=swarm_id,
                        name=name,
                        status="unknown",
                    )
                )

        return SwarmHealthOut(swarms=swarms)

    except Exception as exc:
        logger.error("Failed to get swarm health: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve swarm health.",
        )


@router.get("/admin/prompts/{swarm_id}", response_model=PromptOut)
async def get_swarm_prompt(
    swarm_id: str,
    _admin_key: Annotated[str, Depends(get_admin_key)],
) -> PromptOut:
    """Get the current prompt for a specific swarm."""
    supabase = get_supabase_client()

    if swarm_id not in SWARM_NAMES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown swarm ID: {swarm_id}",
        )

    try:
        resp = (
            supabase.table("swarm_prompts")
            .select("*")
            .eq("swarm_id", swarm_id)
            .order("version", desc=True)
            .limit(1)
            .maybe_single()
            .execute()
        )
        if not resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No prompt found for swarm {swarm_id}.",
            )

        return PromptOut(
            swarm_id=resp.data["swarm_id"],
            prompt_text=resp.data["prompt_text"],
            version=resp.data["version"],
            updated_at=resp.data.get("updated_at", resp.data.get("created_at", "")),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get swarm prompt: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve swarm prompt.",
        )


@router.put("/admin/prompts/{swarm_id}", response_model=PromptUpdateResponse)
async def update_swarm_prompt(
    swarm_id: str,
    body: PromptUpdateRequest,
    _admin_key: Annotated[str, Depends(get_admin_key)],
) -> PromptUpdateResponse:
    """Update a swarm prompt (versioned).

    Creates a new version of the prompt rather than overwriting.
    """
    supabase = get_supabase_client()

    if swarm_id not in SWARM_NAMES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown swarm ID: {swarm_id}",
        )

    try:
        now = datetime.now(timezone.utc).isoformat()

        # Get current version
        current_resp = (
            supabase.table("swarm_prompts")
            .select("version")
            .eq("swarm_id", swarm_id)
            .order("version", desc=True)
            .limit(1)
            .maybe_single()
            .execute()
        )
        current_version = current_resp.data["version"] if current_resp.data else 0
        new_version = current_version + 1

        # Insert new version
        supabase.table("swarm_prompts").insert(
            {
                "id": str(uuid4()),
                "swarm_id": swarm_id,
                "prompt_text": body.prompt_text,
                "version": new_version,
                "created_at": now,
                "updated_at": now,
            }
        ).execute()

        return PromptUpdateResponse(
            success=True,
            swarm_id=swarm_id,
            version=new_version,
            message=f"Prompt updated to version {new_version}.",
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to update swarm prompt: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update swarm prompt.",
        )
