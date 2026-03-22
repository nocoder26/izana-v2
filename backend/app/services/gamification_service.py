"""
Gamification service for Izana Chat (Decision 15).

Manages points, levels, streaks, and badge eligibility. All point values
and level thresholds are defined as module-level constants so they remain
easy to audit and test.

Usage::

    from app.services.gamification_service import (
        award_points,
        increment_streak,
        check_badges,
        get_level_for_points,
    )

    await award_points(user_id, "meal_logged", POINT_VALUES["meal_logged"])
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from app.core.database import get_supabase_admin as get_supabase_client
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# ── Point values (Decision 15) ────────────────────────────────────────────

POINT_VALUES: dict[str, int] = {
    "meal_logged": 10,
    "exercise_completed": 15,
    "meditation_completed": 10,
    "daily_checkin": 10,
    "streak_bonus": 5,
    "all_5_done": 10,
    "bloodwork_upload": 25,
    "partner_connected": 50,
}

# ── Level thresholds (Decision 15) ────────────────────────────────────────
# Each entry is (min_points, level_number, level_name).
# The list MUST be sorted ascending by min_points.

LEVEL_THRESHOLDS: list[tuple[int, int, str]] = [
    (0, 1, "Beginner"),
    (100, 2, "Committed"),
    (300, 3, "Dedicated"),
    (600, 4, "Warrior"),
    (1000, 5, "Champion"),
    (2000, 6, "Radiant"),
    (4000, 7, "Luminous"),
]

# ── Badge criteria (Decision 15) ──────────────────────────────────────────
# Each badge maps to a check function that receives user stats and returns
# True if the badge should be awarded.

BADGE_CRITERIA: dict[str, dict[str, Any]] = {
    "first_meal": {
        "name": "First Meal Logged",
        "description": "Log your first meal",
        "check": lambda stats: stats.get("meals_logged", 0) >= 1,
    },
    "week_streak": {
        "name": "7-Day Streak",
        "description": "Maintain a 7-day activity streak",
        "check": lambda stats: stats.get("current_streak", 0) >= 7,
    },
    "month_streak": {
        "name": "30-Day Streak",
        "description": "Maintain a 30-day activity streak",
        "check": lambda stats: stats.get("current_streak", 0) >= 30,
    },
    "meditation_master": {
        "name": "Meditation Master",
        "description": "Complete 10 meditation sessions",
        "check": lambda stats: stats.get("meditations_completed", 0) >= 10,
    },
    "exercise_enthusiast": {
        "name": "Exercise Enthusiast",
        "description": "Complete 20 exercise sessions",
        "check": lambda stats: stats.get("exercises_completed", 0) >= 20,
    },
    "bloodwork_hero": {
        "name": "Bloodwork Hero",
        "description": "Upload your first bloodwork report",
        "check": lambda stats: stats.get("bloodwork_uploads", 0) >= 1,
    },
    "partner_duo": {
        "name": "Partner Duo",
        "description": "Connect with your partner",
        "check": lambda stats: stats.get("partner_connected", False),
    },
    "century_club": {
        "name": "Century Club",
        "description": "Earn 100 points",
        "check": lambda stats: stats.get("total_points", 0) >= 100,
    },
    "all_rounder": {
        "name": "All-Rounder",
        "description": "Complete all 5 daily activities in one day",
        "check": lambda stats: stats.get("all_5_done_count", 0) >= 1,
    },
}


# ── Public API ────────────────────────────────────────────────────────────


def get_level_for_points(points: int) -> tuple[int, str]:
    """Return the (level_number, level_name) for a given point total.

    Iterates the thresholds in descending order and returns the first
    match whose ``min_points`` the user has reached.

    Args:
        points: The user's total accumulated points.

    Returns:
        A tuple of ``(level_number, level_name)``.
    """
    for min_pts, level, name in reversed(LEVEL_THRESHOLDS):
        if points >= min_pts:
            return level, name
    # Fallback (should not happen since threshold 0 always matches).
    return 1, "Beginner"


async def award_points(user_id: str, action: str, points: int) -> dict[str, Any]:
    """Add points to a user's gamification record and check level thresholds.

    Creates the gamification row if it does not yet exist (upsert pattern).

    Args:
        user_id: Supabase auth user ID.
        action:  One of the keys in ``POINT_VALUES`` (for logging).
        points:  Number of points to award.

    Returns:
        A dict with ``total_points``, ``level``, ``level_name``, and
        ``leveled_up`` (bool indicating whether a level change occurred).
    """
    supabase = get_supabase_client()

    try:
        # Fetch current gamification record.
        result = await asyncio.to_thread(
            lambda: supabase.table("gamification")
            .select("total_points, level")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )

        if result.data:
            old_points = result.data["total_points"]
            old_level = result.data["level"]
            new_points = old_points + points
            new_level, new_level_name = get_level_for_points(new_points)

            await asyncio.to_thread(
                lambda: supabase.table("gamification")
                .update({
                    "total_points": new_points,
                    "level": new_level,
                    "level_name": new_level_name,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
                .eq("user_id", user_id)
                .execute()
            )

            leveled_up = new_level > old_level
        else:
            # First time — create record.
            new_points = points
            new_level, new_level_name = get_level_for_points(new_points)
            leveled_up = False

            await asyncio.to_thread(
                lambda: supabase.table("gamification")
                .insert({
                    "user_id": user_id,
                    "total_points": new_points,
                    "level": new_level,
                    "level_name": new_level_name,
                    "current_streak": 0,
                })
                .execute()
            )

        logger.info(
            "Points awarded",
            extra={
                "user_id": user_id,
                "action": action,
                "points": points,
                "total_points": new_points,
                "level": new_level,
                "leveled_up": leveled_up,
            },
        )

        return {
            "total_points": new_points,
            "level": new_level,
            "level_name": new_level_name,
            "leveled_up": leveled_up,
        }

    except Exception:
        logger.exception(
            "Failed to award points",
            extra={"user_id": user_id, "action": action, "points": points},
        )
        raise


async def increment_streak(user_id: str) -> dict[str, Any]:
    """Increment the user's daily activity streak by one.

    Also awards the streak bonus points and checks for streak-based badges.

    Args:
        user_id: Supabase auth user ID.

    Returns:
        A dict with ``current_streak`` and ``streak_bonus_awarded``.
    """
    supabase = get_supabase_client()

    try:
        result = await asyncio.to_thread(
            lambda: supabase.table("gamification")
            .select("current_streak, longest_streak")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )

        if result.data:
            current = result.data["current_streak"] + 1
            longest = max(result.data.get("longest_streak", 0), current)

            await asyncio.to_thread(
                lambda: supabase.table("gamification")
                .update({
                    "current_streak": current,
                    "longest_streak": longest,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
                .eq("user_id", user_id)
                .execute()
            )
        else:
            current = 1
            await asyncio.to_thread(
                lambda: supabase.table("gamification")
                .insert({
                    "user_id": user_id,
                    "total_points": 0,
                    "level": 1,
                    "level_name": "Beginner",
                    "current_streak": current,
                    "longest_streak": current,
                })
                .execute()
            )

        # Award streak bonus points.
        await award_points(user_id, "streak_bonus", POINT_VALUES["streak_bonus"])

        logger.info(
            "Streak incremented",
            extra={"user_id": user_id, "current_streak": current},
        )

        return {"current_streak": current, "streak_bonus_awarded": True}

    except Exception:
        logger.exception(
            "Failed to increment streak", extra={"user_id": user_id}
        )
        raise


async def reset_streak(user_id: str) -> None:
    """Reset the user's streak to zero.

    Used when a user resumes from grief mode or misses a day.

    Args:
        user_id: Supabase auth user ID.
    """
    supabase = get_supabase_client()

    try:
        await asyncio.to_thread(
            lambda: supabase.table("gamification")
            .update({
                "current_streak": 0,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("user_id", user_id)
            .execute()
        )
        logger.info("Streak reset", extra={"user_id": user_id})
    except Exception:
        logger.exception("Failed to reset streak", extra={"user_id": user_id})
        raise


async def check_badges(user_id: str) -> list[str]:
    """Check all badge criteria against the user's stats and award new badges.

    Badges that are already awarded are skipped.

    Args:
        user_id: Supabase auth user ID.

    Returns:
        A list of newly awarded badge IDs.
    """
    supabase = get_supabase_client()
    newly_awarded: list[str] = []

    try:
        # Fetch user stats from gamification table.
        stats_result = await asyncio.to_thread(
            lambda: supabase.table("gamification")
            .select("*")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )

        if not stats_result.data:
            return []

        stats = stats_result.data

        # Fetch already-awarded badges.
        badges_result = await asyncio.to_thread(
            lambda: supabase.table("user_badges")
            .select("badge_id")
            .eq("user_id", user_id)
            .execute()
        )

        existing_badges = {
            row["badge_id"] for row in (badges_result.data or [])
        }

        # Evaluate each badge criterion.
        for badge_id, badge_def in BADGE_CRITERIA.items():
            if badge_id in existing_badges:
                continue

            if badge_def["check"](stats):
                await asyncio.to_thread(
                    lambda bid=badge_id, bname=badge_def["name"]: (
                        supabase.table("user_badges")
                        .insert({
                            "user_id": user_id,
                            "badge_id": bid,
                            "badge_name": bname,
                            "awarded_at": datetime.now(timezone.utc).isoformat(),
                        })
                        .execute()
                    )
                )
                newly_awarded.append(badge_id)

        if newly_awarded:
            logger.info(
                "Badges awarded",
                extra={"user_id": user_id, "badges": newly_awarded},
            )

        return newly_awarded

    except Exception:
        logger.exception(
            "Failed to check badges", extra={"user_id": user_id}
        )
        raise
