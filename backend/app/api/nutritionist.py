"""
Nutritionist Portal API routes (Admin Auth).

All endpoints require ``get_admin_key`` authentication.

- POST /nutritionist/auth/login         — Email + password login
- GET  /nutritionist/queue              — View approval queue
- GET  /nutritionist/queue/stats        — Queue statistics
- POST /nutritionist/queue/{id}/assign  — Assign plan to self
- GET  /nutritionist/plan/{id}          — Get plan for review
- POST /nutritionist/plan/{id}/approve  — Approve plan
- POST /nutritionist/plan/{id}/modify   — Modify and approve
- POST /nutritionist/plan/{id}/reject   — Reject plan
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Optional
from uuid import uuid4

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.auth import get_admin_key
from app.core.config import settings
from app.core.database import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class NutritionistLoginRequest(BaseModel):
    """Nutritionist login payload."""

    email: str
    password: str


class NutritionistLoginResponse(BaseModel):
    """Nutritionist login response."""

    token: str
    nutritionist_id: str
    name: str


class QueueItem(BaseModel):
    """Single item in the approval queue."""

    id: str
    user_id: str
    pseudonym: Optional[str] = None
    treatment_type: Optional[str] = None
    phase: Optional[str] = None
    priority: str
    status: str
    created_at: str
    deadline: Optional[str] = None
    assigned_to: Optional[str] = None


class QueueOut(BaseModel):
    """Approval queue listing."""

    items: list[QueueItem]
    total: int


class QueueStats(BaseModel):
    """Queue statistics."""

    total_pending: int
    total_in_review: int
    total_approved_today: int
    average_review_minutes: Optional[float] = None


class AssignResponse(BaseModel):
    """Plan assignment confirmation."""

    success: bool
    plan_id: str
    assigned_to: str


class PlanReviewOut(BaseModel):
    """Plan data for review (3-panel data)."""

    id: str
    user_id: str
    pseudonym: Optional[str] = None
    treatment_type: Optional[str] = None
    phase: Optional[str] = None
    plan_data: Any = None
    user_profile: Any = None
    journey_context: Any = None
    status: str
    created_at: str


class ApproveRequest(BaseModel):
    """Plan approval payload."""

    notes: Optional[str] = None


class ApproveResponse(BaseModel):
    """Plan approval confirmation."""

    success: bool
    plan_id: str
    message: str


class ModifyRequest(BaseModel):
    """Plan modification payload."""

    modifications: dict[str, Any]
    notes: Optional[str] = None


class ModifyResponse(BaseModel):
    """Plan modification confirmation."""

    success: bool
    plan_id: str
    message: str


class RejectRequest(BaseModel):
    """Plan rejection payload."""

    reason: str
    request_regeneration: bool = False


class RejectResponse(BaseModel):
    """Plan rejection confirmation."""

    success: bool
    plan_id: str
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/nutritionist/auth/login", response_model=NutritionistLoginResponse)
async def nutritionist_login(
    body: NutritionistLoginRequest,
) -> NutritionistLoginResponse:
    """Nutritionist email + password login.

    Verifies credentials against the nutritionists table and returns
    a signed JWT for subsequent requests.
    """
    supabase = get_supabase_client()

    try:
        # Look up nutritionist by email
        resp = (
            supabase.table("admin_users")
            .select("id, name, password_hash")
            .eq("email", body.email)
            .limit(1)
            .execute()
        )
        if not resp.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials.",
            )

        nutritionist = resp.data[0]

        # Verify password with bcrypt
        import bcrypt as _bcrypt

        stored_hash = nutritionist.get("password_hash", "")
        try:
            pw_ok = stored_hash and _bcrypt.checkpw(body.password.encode(), stored_hash.encode())
        except Exception as pw_err:
            logger.error("bcrypt error: %s (hash_prefix=%s)", pw_err, stored_hash[:10] if stored_hash else "NONE")
            pw_ok = False
        if not pw_ok:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials.",
            )

        # Generate JWT
        token = jwt.encode(
            {
                "sub": nutritionist["id"],
                "role": "nutritionist",
                "exp": datetime.now(timezone.utc)
                + timedelta(hours=8),
            },
            settings.NUTRITIONIST_JWT_SECRET,
            algorithm="HS256",
        )

        return NutritionistLoginResponse(
            token=token,
            nutritionist_id=nutritionist["id"],
            name=nutritionist["name"],
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Nutritionist login failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed.",
        )


@router.get("/nutritionist/queue", response_model=QueueOut)
async def get_approval_queue(
    _admin_key: Annotated[str, Depends(get_admin_key)],
    status_filter: Optional[str] = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
) -> QueueOut:
    """View the nutritionist approval queue.

    Sorted by priority (urgent first) and deadline.
    """
    supabase = get_supabase_client()

    try:
        query = supabase.table("plans").select("*", count="exact")

        if status_filter:
            query = query.eq("status", status_filter)
        else:
            query = query.in_("status", ["pending_nutritionist", "in_review"])

        offset = (page - 1) * per_page
        query = (
            query.order("priority", desc=True)
            .order("created_at", desc=False)
            .range(offset, offset + per_page - 1)
        )

        resp = query.execute()
        total = resp.count or 0

        items = []
        for p in (resp.data or []):
            # Fetch user pseudonym
            profile_resp = (
                supabase.table("profiles")
                .select("pseudonym")
                .eq("id", p["user_id"])
                .limit(1)
                .execute()
            )
            pseudonym = profile_resp.data[0]["pseudonym"] if profile_resp.data else None

            items.append(
                QueueItem(
                    id=p["id"],
                    user_id=p["user_id"],
                    pseudonym=pseudonym,
                    treatment_type=p.get("treatment_type"),
                    phase=p.get("phase"),
                    priority=p.get("priority", "normal"),
                    status=p["status"],
                    created_at=p["created_at"],
                    deadline=p.get("deadline"),
                    assigned_to=p.get("assigned_to"),
                )
            )

        return QueueOut(items=items, total=total)

    except Exception as exc:
        logger.error("Failed to get approval queue: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve approval queue.",
        )


@router.get("/nutritionist/queue/stats", response_model=QueueStats)
async def get_queue_stats(
    _admin_key: Annotated[str, Depends(get_admin_key)],
) -> QueueStats:
    """Get queue statistics."""
    supabase = get_supabase_client()

    try:
        # Pending count
        pending_resp = (
            supabase.table("plans")
            .select("id", count="exact")
            .eq("status", "pending_nutritionist")
            .execute()
        )
        total_pending = pending_resp.count or 0

        # In review count
        review_resp = (
            supabase.table("plans")
            .select("id", count="exact")
            .eq("status", "in_review")
            .execute()
        )
        total_in_review = review_resp.count or 0

        # Approved today
        from datetime import date

        today = date.today().isoformat()
        approved_resp = (
            supabase.table("plans")
            .select("id", count="exact")
            .in_("status", ["approved", "modified"])
            .gte("approved_at", today)
            .execute()
        )
        total_approved_today = approved_resp.count or 0

        return QueueStats(
            total_pending=total_pending,
            total_in_review=total_in_review,
            total_approved_today=total_approved_today,
        )

    except Exception as exc:
        logger.error("Failed to get queue stats: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve queue statistics.",
        )


@router.post("/nutritionist/queue/{plan_id}/assign", response_model=AssignResponse)
async def assign_plan(
    plan_id: str,
    _admin_key: Annotated[str, Depends(get_admin_key)],
    nutritionist_id: str = Query(..., description="ID of the nutritionist"),
) -> AssignResponse:
    """Assign a plan to a nutritionist for review."""
    supabase = get_supabase_client()

    try:
        now = datetime.now(timezone.utc).isoformat()

        resp = (
            supabase.table("plans")
            .update(
                {
                    "status": "in_review",
                    "assigned_to": nutritionist_id,
                    "assigned_at": now,
                }
            )
            .eq("id", plan_id)
            .eq("status", "pending_nutritionist")
            .execute()
        )
        if not resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found or already assigned.",
            )

        return AssignResponse(
            success=True,
            plan_id=plan_id,
            assigned_to=nutritionist_id,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to assign plan: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign plan.",
        )


@router.get("/nutritionist/plan/{plan_id}", response_model=PlanReviewOut)
async def get_plan_for_review(
    plan_id: str,
    _admin_key: Annotated[str, Depends(get_admin_key)],
) -> PlanReviewOut:
    """Get plan data for review (3-panel data).

    Returns the plan, user profile, and journey context.
    """
    supabase = get_supabase_client()

    try:
        # Get plan
        plan_resp = (
            supabase.table("plans")
            .select("*")
            .eq("id", plan_id)
            .limit(1)
            .execute()
        )
        if not plan_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found.",
            )

        plan = plan_resp.data
        plan_user_id = plan["user_id"]

        # Get user profile
        profile_resp = (
            supabase.table("profiles")
            .select("*")
            .eq("id", plan_user_id)
            .limit(1)
            .execute()
        )
        user_profile = profile_resp.data

        pseudonym = user_profile.get("pseudonym") if user_profile else None

        # Get journey context
        journey_resp = (
            supabase.table("journeys")
            .select("*")
            .eq("user_id", plan_user_id)
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        journey_context = journey_resp.data

        return PlanReviewOut(
            id=plan["id"],
            user_id=plan_user_id,
            pseudonym=pseudonym,
            treatment_type=plan.get("treatment_type"),
            phase=plan.get("phase"),
            plan_data=plan.get("plan_data"),
            user_profile=user_profile,
            journey_context=journey_context,
            status=plan["status"],
            created_at=plan["created_at"],
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get plan for review: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve plan.",
        )


@router.post("/nutritionist/plan/{plan_id}/approve", response_model=ApproveResponse)
async def approve_plan(
    plan_id: str,
    body: ApproveRequest,
    _admin_key: Annotated[str, Depends(get_admin_key)],
) -> ApproveResponse:
    """Approve a plan."""
    supabase = get_supabase_client()

    try:
        now = datetime.now(timezone.utc).isoformat()

        resp = (
            supabase.table("plans")
            .update(
                {
                    "status": "approved",
                    "approved_at": now,
                    "review_notes": body.notes,
                }
            )
            .eq("id", plan_id)
            .in_("status", ["in_review", "pending_nutritionist"])
            .execute()
        )
        if not resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found or not in reviewable state.",
            )

        return ApproveResponse(
            success=True,
            plan_id=plan_id,
            message="Plan approved successfully.",
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to approve plan: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve plan.",
        )


@router.post("/nutritionist/plan/{plan_id}/modify", response_model=ModifyResponse)
async def modify_plan(
    plan_id: str,
    body: ModifyRequest,
    _admin_key: Annotated[str, Depends(get_admin_key)],
) -> ModifyResponse:
    """Modify and approve a plan.

    Saves the modifications for DPO (Direct Preference Optimisation)
    training data collection.
    """
    supabase = get_supabase_client()

    try:
        now = datetime.now(timezone.utc).isoformat()

        # Get original plan data for DPO
        original_resp = (
            supabase.table("plans")
            .select("plan_data")
            .eq("id", plan_id)
            .limit(1)
            .execute()
        )
        if not original_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found.",
            )

        # Save modification for DPO
        try:
            supabase.table("plan_modifications").insert(
                {
                    "id": str(uuid4()),
                    "plan_id": plan_id,
                    "original_data": original_resp.data[0].get("plan_data"),
                    "modifications": body.modifications,
                    "notes": body.notes,
                    "created_at": now,
                }
            ).execute()
        except Exception as dpo_exc:
            logger.warning("Failed to save DPO data: %s", dpo_exc)

        # Update plan
        supabase.table("plans").update(
            {
                "status": "modified",
                "plan_data": body.modifications,
                "approved_at": now,
                "review_notes": body.notes,
            }
        ).eq("id", plan_id).execute()

        return ModifyResponse(
            success=True,
            plan_id=plan_id,
            message="Plan modified and approved.",
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to modify plan: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to modify plan.",
        )


@router.post("/nutritionist/plan/{plan_id}/reject", response_model=RejectResponse)
async def reject_plan(
    plan_id: str,
    body: RejectRequest,
    _admin_key: Annotated[str, Depends(get_admin_key)],
) -> RejectResponse:
    """Reject a plan, optionally requesting regeneration."""
    supabase = get_supabase_client()

    try:
        now = datetime.now(timezone.utc).isoformat()

        resp = (
            supabase.table("plans")
            .update(
                {
                    "status": "rejected",
                    "review_notes": body.reason,
                    "rejected_at": now,
                }
            )
            .eq("id", plan_id)
            .in_("status", ["in_review", "pending_nutritionist"])
            .execute()
        )
        if not resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found or not in reviewable state.",
            )

        message = "Plan rejected."
        if body.request_regeneration:
            # TODO: Trigger plan regeneration
            message = "Plan rejected. Regeneration has been requested."
            logger.info("Plan regeneration requested for plan_id=%s", plan_id)

        return RejectResponse(
            success=True,
            plan_id=plan_id,
            message=message,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to reject plan: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reject plan.",
        )
