"""
Nutrition API routes — Plans, Meals, Activities.

Provides wellness profile management, meal/activity logging with
gamification, dashboard data, and plan status polling.

- GET  /nutrition/wellness-profile  — Get wellness profile
- POST /nutrition/wellness-profile  — Update wellness profile
- POST /nutrition/meals             — Log meal completion (+10 points)
- POST /nutrition/activities        — Log activity completion (+15 points)
- GET  /nutrition/dashboard         — Dashboard data
- GET  /nutrition/plan/current      — Get current approved plan
- GET  /plan-status                 — Check plan review status (polling)
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Annotated, Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.auth import get_user_id
from app.core.database import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class WellnessProfileOut(BaseModel):
    """User wellness profile data."""

    allergies: list[str] = Field(default_factory=list)
    dietary_preferences: list[str] = Field(default_factory=list)
    exercise_preferences: list[str] = Field(default_factory=list)
    supplements: list[str] = Field(default_factory=list)
    medical_conditions: list[str] = Field(default_factory=list)
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None


class WellnessProfileUpdate(BaseModel):
    """Payload for updating the wellness profile."""

    allergies: Optional[list[str]] = None
    dietary_preferences: Optional[list[str]] = None
    exercise_preferences: Optional[list[str]] = None
    supplements: Optional[list[str]] = None
    medical_conditions: Optional[list[str]] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None


class MealLogRequest(BaseModel):
    """Payload for logging a meal completion."""

    meal_type: str  # breakfast, lunch, dinner, snack
    description: Optional[str] = None
    plan_item_id: Optional[str] = None


class MealLogOut(BaseModel):
    """Recorded meal log."""

    id: str
    meal_type: str
    description: Optional[str] = None
    points_earned: int
    created_at: str


class ActivityLogRequest(BaseModel):
    """Payload for logging an activity completion."""

    activity_type: str
    duration_minutes: Optional[int] = None
    description: Optional[str] = None
    plan_item_id: Optional[str] = None


class ActivityLogOut(BaseModel):
    """Recorded activity log."""

    id: str
    activity_type: str
    duration_minutes: Optional[int] = None
    points_earned: int
    created_at: str


class DashboardOut(BaseModel):
    """Nutrition dashboard data."""

    meals_today: int
    activities_today: int
    total_points: int
    current_streak: int
    level: int
    level_name: str


class PlanOut(BaseModel):
    """Current nutrition/wellness plan."""

    id: str
    status: str
    plan_data: Any = None
    approved_at: Optional[str] = None
    created_at: str


class PlanStatusOut(BaseModel):
    """Plan review status for polling."""

    plan_id: Optional[str] = None
    status: str
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/nutrition/wellness-profile", response_model=WellnessProfileOut)
async def get_wellness_profile(
    user_id: Annotated[str, Depends(get_user_id)],
) -> WellnessProfileOut:
    """Get the user's wellness profile from the profiles table."""
    supabase = get_supabase_client()

    try:
        resp = (
            supabase.table("profiles")
            .select(
                "allergies, dietary_preferences, exercise_preferences, "
                "supplements, medical_conditions, height_cm, weight_kg"
            )
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        if not resp.data:
            return WellnessProfileOut()

        return WellnessProfileOut(
            allergies=resp.data.get("allergies") or [],
            dietary_preferences=resp.data.get("dietary_preferences") or [],
            exercise_preferences=resp.data.get("exercise_preferences") or [],
            supplements=resp.data.get("supplements") or [],
            medical_conditions=resp.data.get("medical_conditions") or [],
            height_cm=resp.data.get("height_cm"),
            weight_kg=resp.data.get("weight_kg"),
        )

    except Exception as exc:
        logger.error("Failed to get wellness profile: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve wellness profile.",
        )


@router.post("/nutrition/wellness-profile", response_model=WellnessProfileOut)
async def update_wellness_profile(
    body: WellnessProfileUpdate,
    user_id: Annotated[str, Depends(get_user_id)],
) -> WellnessProfileOut:
    """Update the user's wellness profile (allergies, exercise prefs, etc.)."""
    supabase = get_supabase_client()

    try:
        update_data: dict[str, Any] = {}
        if body.allergies is not None:
            update_data["allergies"] = body.allergies
        if body.dietary_preferences is not None:
            update_data["dietary_preferences"] = body.dietary_preferences
        if body.exercise_preferences is not None:
            update_data["exercise_preferences"] = body.exercise_preferences
        if body.supplements is not None:
            update_data["supplements"] = body.supplements
        if body.medical_conditions is not None:
            update_data["medical_conditions"] = body.medical_conditions
        if body.height_cm is not None:
            update_data["height_cm"] = body.height_cm
        if body.weight_kg is not None:
            update_data["weight_kg"] = body.weight_kg

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No fields provided to update.",
            )

        supabase.table("profiles").update(update_data).eq("id", user_id).execute()

        # Return updated profile
        return await get_wellness_profile(user_id)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to update wellness profile: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update wellness profile.",
        )


@router.post(
    "/nutrition/meals",
    response_model=MealLogOut,
    status_code=status.HTTP_201_CREATED,
)
async def log_meal(
    body: MealLogRequest,
    user_id: Annotated[str, Depends(get_user_id)],
) -> MealLogOut:
    """Log a meal completion (+10 gamification points)."""
    supabase = get_supabase_client()
    points = 10

    try:
        meal_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        supabase.table("meal_logs").insert(
            {
                "id": meal_id,
                "user_id": user_id,
                "meal_type": body.meal_type,
                "description": body.description,
                "plan_item_id": body.plan_item_id,
                "points_earned": points,
                "created_at": now,
            }
        ).execute()

        # Update gamification
        try:
            gam_resp = (
                supabase.table("gamification")
                .select("total_points")
                .eq("user_id", user_id)
                .maybe_single()
                .execute()
            )
            if gam_resp.data:
                supabase.table("gamification").update(
                    {"total_points": gam_resp.data["total_points"] + points}
                ).eq("user_id", user_id).execute()
        except Exception as gam_exc:
            logger.warning("Failed to update gamification for meal: %s", gam_exc)

        return MealLogOut(
            id=meal_id,
            meal_type=body.meal_type,
            description=body.description,
            points_earned=points,
            created_at=now,
        )

    except Exception as exc:
        logger.error("Failed to log meal: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to log meal.",
        )


@router.post(
    "/nutrition/activities",
    response_model=ActivityLogOut,
    status_code=status.HTTP_201_CREATED,
)
async def log_activity(
    body: ActivityLogRequest,
    user_id: Annotated[str, Depends(get_user_id)],
) -> ActivityLogOut:
    """Log an activity completion (+15 gamification points)."""
    supabase = get_supabase_client()
    points = 15

    try:
        activity_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        supabase.table("activity_logs").insert(
            {
                "id": activity_id,
                "user_id": user_id,
                "activity_type": body.activity_type,
                "duration_minutes": body.duration_minutes,
                "description": body.description,
                "plan_item_id": body.plan_item_id,
                "points_earned": points,
                "created_at": now,
            }
        ).execute()

        # Update gamification
        try:
            gam_resp = (
                supabase.table("gamification")
                .select("total_points")
                .eq("user_id", user_id)
                .maybe_single()
                .execute()
            )
            if gam_resp.data:
                supabase.table("gamification").update(
                    {"total_points": gam_resp.data["total_points"] + points}
                ).eq("user_id", user_id).execute()
        except Exception as gam_exc:
            logger.warning("Failed to update gamification for activity: %s", gam_exc)

        return ActivityLogOut(
            id=activity_id,
            activity_type=body.activity_type,
            duration_minutes=body.duration_minutes,
            points_earned=points,
            created_at=now,
        )

    except Exception as exc:
        logger.error("Failed to log activity: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to log activity.",
        )


@router.get("/nutrition/dashboard", response_model=DashboardOut)
async def get_dashboard(
    user_id: Annotated[str, Depends(get_user_id)],
) -> DashboardOut:
    """Get nutrition dashboard data.

    Returns today's meal/activity completions, streaks, points, and level.
    """
    supabase = get_supabase_client()
    today = date.today().isoformat()

    try:
        # Count today's meals
        meals_resp = (
            supabase.table("meal_logs")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .gte("created_at", today)
            .execute()
        )
        meals_today = meals_resp.count or 0

        # Count today's activities
        activities_resp = (
            supabase.table("activity_logs")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .gte("created_at", today)
            .execute()
        )
        activities_today = activities_resp.count or 0

        # Get gamification data
        gam_resp = (
            supabase.table("gamification")
            .select("total_points, current_streak, level, level_name")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        gam = gam_resp.data or {
            "total_points": 0,
            "current_streak": 0,
            "level": 1,
            "level_name": "Beginner",
        }

        return DashboardOut(
            meals_today=meals_today,
            activities_today=activities_today,
            total_points=gam["total_points"],
            current_streak=gam["current_streak"],
            level=gam["level"],
            level_name=gam["level_name"],
        )

    except Exception as exc:
        logger.error("Failed to get dashboard: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard data.",
        )


@router.get("/nutrition/plan/current", response_model=PlanOut)
async def get_current_plan(
    user_id: Annotated[str, Depends(get_user_id)],
) -> PlanOut:
    """Get the current approved nutrition/wellness plan."""
    supabase = get_supabase_client()

    try:
        resp = (
            supabase.table("plans")
            .select("*")
            .eq("user_id", user_id)
            .in_("status", ["approved", "modified"])
            .order("created_at", desc=True)
            .limit(1)
            .maybe_single()
            .execute()
        )
        if not resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No approved plan found.",
            )

        return PlanOut(
            id=resp.data["id"],
            status=resp.data["status"],
            plan_data=resp.data.get("plan_data"),
            approved_at=resp.data.get("approved_at"),
            created_at=resp.data["created_at"],
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get current plan: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve plan.",
        )


@router.get("/plan-status", response_model=PlanStatusOut)
async def get_plan_status(
    user_id: Annotated[str, Depends(get_user_id)],
) -> PlanStatusOut:
    """Check plan review status (for client-side polling).

    Returns the status of the most recent plan.
    """
    supabase = get_supabase_client()

    try:
        resp = (
            supabase.table("plans")
            .select("id, status")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .maybe_single()
            .execute()
        )
        if not resp.data:
            return PlanStatusOut(
                status="none",
                message="No plan has been generated yet.",
            )

        status_val = resp.data["status"]
        messages = {
            "generating": "Your plan is being generated...",
            "pending_nutritionist": "Your plan is waiting for nutritionist review.",
            "in_review": "A nutritionist is currently reviewing your plan.",
            "approved": "Your plan has been approved!",
            "modified": "Your plan has been reviewed and customised.",
            "rejected": "Your plan needs to be regenerated.",
            "expired": "Your plan has expired. A new one will be generated.",
        }

        return PlanStatusOut(
            plan_id=resp.data["id"],
            status=status_val,
            message=messages.get(status_val, f"Plan status: {status_val}"),
        )

    except Exception as exc:
        logger.error("Failed to get plan status: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve plan status.",
        )
