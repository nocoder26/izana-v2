"""
Cron-triggered background tasks for Izana Chat.

Each function in this module is an arq task that runs on a schedule.
They handle evening summaries, phase transitions, plan escalation,
nudge delivery, disengagement sensing, cache refresh, and data
lifecycle management.

These tasks are registered in ``app.workers.worker.WorkerSettings``
and triggered by the arq cron scheduler.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from app.core.database import get_supabase_admin as get_supabase_client
from app.core.logging_config import get_logger
from app.services.gamification_service import (
    POINT_VALUES,
    award_points,
    check_badges,
    increment_streak,
)

logger = get_logger(__name__)

# ── Phase transition thresholds ───────────────────────────────────────────

SOFT_CHECKIN_PCT = 0.8  # Prompt transition when 80% of avg phase days elapsed.


# ── Evening Summary ───────────────────────────────────────────────────────


async def evening_summary_task(ctx: dict, user_id: str) -> None:
    """Calculate and persist an evening summary card for a user.

    Summarises the day's completions (meals, exercise, meditation,
    check-ins), computes earned points, updates gamification state,
    and inserts a ``week_summary_card`` message into ``chat_logs``.

    Args:
        ctx:     arq worker context (contains ``redis`` key).
        user_id: Supabase auth user ID.
    """
    supabase = get_supabase_client()
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    today_iso = today_start.isoformat()

    try:
        # ── Count today's completions ────────────────────────────────
        meals_result = await asyncio.to_thread(
            lambda: supabase.table("meal_logs")
            .select("id")
            .eq("user_id", user_id)
            .gte("created_at", today_iso)
            .execute()
        )
        meals_count = len(meals_result.data) if meals_result.data else 0

        activities_result = await asyncio.to_thread(
            lambda: supabase.table("activity_logs")
            .select("id, activity_type")
            .eq("user_id", user_id)
            .gte("created_at", today_iso)
            .execute()
        )
        activities = activities_result.data or []
        exercise_count = sum(
            1 for a in activities if a.get("activity_type") == "exercise"
        )
        meditation_count = sum(
            1 for a in activities if a.get("activity_type") == "meditation"
        )

        checkin_result = await asyncio.to_thread(
            lambda: supabase.table("daily_checkins")
            .select("id")
            .eq("user_id", user_id)
            .gte("created_at", today_iso)
            .execute()
        )
        checkin_done = bool(checkin_result.data)

        # ── Mood from emotion logs ───────────────────────────────────
        mood_result = await asyncio.to_thread(
            lambda: supabase.table("emotion_logs")
            .select("mood")
            .eq("user_id", user_id)
            .gte("created_at", today_iso)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        mood = (
            mood_result.data[0]["mood"]
            if mood_result.data
            else None
        )

        # ── Calculate points earned today ────────────────────────────
        points_today = 0

        if meals_count > 0:
            meal_points = meals_count * POINT_VALUES["meal_logged"]
            await award_points(user_id, "meal_logged", meal_points)
            points_today += meal_points

        if exercise_count > 0:
            ex_points = exercise_count * POINT_VALUES["exercise_completed"]
            await award_points(user_id, "exercise_completed", ex_points)
            points_today += ex_points

        if meditation_count > 0:
            med_points = meditation_count * POINT_VALUES["meditation_completed"]
            await award_points(user_id, "meditation_completed", med_points)
            points_today += med_points

        if checkin_done:
            await award_points(
                user_id, "daily_checkin", POINT_VALUES["daily_checkin"]
            )
            points_today += POINT_VALUES["daily_checkin"]

        # Check if all 5 daily activities are done.
        all_5_done = (
            meals_count > 0
            and exercise_count > 0
            and meditation_count > 0
            and checkin_done
            and mood is not None
        )
        if all_5_done:
            await award_points(
                user_id, "all_5_done", POINT_VALUES["all_5_done"]
            )
            points_today += POINT_VALUES["all_5_done"]

        # Streak handling.
        if meals_count > 0 or exercise_count > 0 or meditation_count > 0:
            streak_result = await increment_streak(user_id)
            points_today += POINT_VALUES["streak_bonus"]
        else:
            streak_result = {"current_streak": 0}

        # Badge check.
        await check_badges(user_id)

        # ── Build summary card ───────────────────────────────────────
        summary_card = {
            "type": "evening_summary",
            "date": today_start.strftime("%Y-%m-%d"),
            "meals_logged": meals_count,
            "exercises_done": exercise_count,
            "meditation_done": meditation_count,
            "checkin_done": checkin_done,
            "mood": mood,
            "points_earned": points_today,
            "current_streak": streak_result.get("current_streak", 0),
            "all_5_done": all_5_done,
        }

        # ── Insert summary card into chat_logs ───────────────────────
        await asyncio.to_thread(
            lambda: supabase.table("chat_logs")
            .insert({
                "id": str(uuid4()),
                "user_id": user_id,
                "user_message": "",
                "assistant_message": json.dumps(summary_card),
                "message_type": "week_summary_card",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            .execute()
        )

        logger.info(
            "Evening summary generated",
            extra={
                "user_id": user_id,
                "points_today": points_today,
                "all_5_done": all_5_done,
            },
        )

    except Exception:
        logger.exception(
            "Evening summary task failed", extra={"user_id": user_id}
        )


# ── Phase Transition Check ───────────────────────────────────────────────


async def phase_transition_check_task(ctx: dict) -> None:
    """Check all active chapters for users who may need a phase transition.

    For each active chapter, compares ``days_in_phase`` against the
    average phase duration multiplied by ``SOFT_CHECKIN_PCT`` (0.8).
    When a user is due, a ``transition_card`` message is inserted into
    their ``chat_logs``.

    Args:
        ctx: arq worker context.
    """
    supabase = get_supabase_client()

    try:
        # Fetch all active chapters.
        result = await asyncio.to_thread(
            lambda: supabase.table("chapters")
            .select("id, user_id, phase, started_at")
            .eq("status", "active")
            .execute()
        )

        chapters = result.data or []

        if not chapters:
            logger.info("No active chapters to check for transitions")
            return

        # Fetch phase duration averages.
        durations_result = await asyncio.to_thread(
            lambda: supabase.table("phase_durations")
            .select("phase, avg_days")
            .execute()
        )

        duration_map: dict[str, float] = {}
        for row in (durations_result.data or []):
            duration_map[row["phase"]] = row["avg_days"]

        now = datetime.now(timezone.utc)
        transition_count = 0

        for chapter in chapters:
            phase = chapter["phase"]
            avg_days = duration_map.get(phase)

            if avg_days is None:
                continue

            started_at = datetime.fromisoformat(
                chapter["started_at"].replace("Z", "+00:00")
            )
            days_in_phase = (now - started_at).days

            threshold = avg_days * SOFT_CHECKIN_PCT

            if days_in_phase >= threshold:
                # Insert transition card.
                card_data = {
                    "type": "transition_card",
                    "phase": phase,
                    "days_in_phase": days_in_phase,
                    "avg_days": avg_days,
                    "suggested_action": "phase_transition",
                }

                await asyncio.to_thread(
                    lambda uid=chapter["user_id"], cd=card_data: (
                        supabase.table("chat_logs")
                        .insert({
                            "id": str(uuid4()),
                            "user_id": uid,
                            "user_message": "",
                            "assistant_message": json.dumps(cd),
                            "message_type": "transition_card",
                            "created_at": now.isoformat(),
                        })
                        .execute()
                    )
                )
                transition_count += 1

        logger.info(
            "Phase transition check complete",
            extra={
                "chapters_checked": len(chapters),
                "transitions_prompted": transition_count,
            },
        )

    except Exception:
        logger.exception("Phase transition check task failed")


# ── Plan Overdue Escalation ───────────────────────────────────────────────


async def plan_overdue_escalation_task(ctx: dict) -> None:
    """Escalate overdue plans in the approval queue.

    - Plans older than 4 hours: upgrade priority to ``urgent_phase_change``.
    - Plans older than 24 hours: log an admin alert.

    Args:
        ctx: arq worker context.
    """
    supabase = get_supabase_client()

    try:
        now = datetime.now(timezone.utc)
        four_hours_ago = (now - timedelta(hours=4)).isoformat()
        twenty_four_hours_ago = (now - timedelta(hours=24)).isoformat()

        # Fetch overdue entries (>4 hours).
        result = await asyncio.to_thread(
            lambda: supabase.table("approval_queue")
            .select("id, plan_id, user_id, priority, created_at")
            .in_("status", ["PENDING", "ASSIGNED"])
            .lt("created_at", four_hours_ago)
            .execute()
        )

        overdue_entries = result.data or []

        if not overdue_entries:
            logger.info("No overdue plans found")
            return

        escalated = 0
        admin_alerts = 0

        for entry in overdue_entries:
            entry_created = datetime.fromisoformat(
                entry["created_at"].replace("Z", "+00:00")
            )

            # Escalate priority if not already urgent.
            if entry["priority"] != "urgent_phase_change":
                await asyncio.to_thread(
                    lambda eid=entry["id"]: supabase.table("approval_queue")
                    .update({
                        "priority": "urgent_phase_change",
                        "updated_at": now.isoformat(),
                    })
                    .eq("id", eid)
                    .execute()
                )
                escalated += 1

            # Log admin alert for plans >24 hours old.
            if entry_created < datetime.fromisoformat(
                twenty_four_hours_ago.replace("Z", "+00:00")
                if "Z" in twenty_four_hours_ago
                else twenty_four_hours_ago
            ):
                logger.warning(
                    "ADMIN ALERT: Plan approval overdue >24 hours",
                    extra={
                        "approval_id": entry["id"],
                        "plan_id": entry["plan_id"],
                        "user_id": entry["user_id"],
                        "hours_overdue": (now - entry_created).total_seconds() / 3600,
                    },
                )
                admin_alerts += 1

        logger.info(
            "Plan overdue escalation complete",
            extra={
                "overdue_count": len(overdue_entries),
                "escalated": escalated,
                "admin_alerts": admin_alerts,
            },
        )

    except Exception:
        logger.exception("Plan overdue escalation task failed")


# ── Nudge Delivery ────────────────────────────────────────────────────────


async def nudge_delivery_task(ctx: dict) -> None:
    """Process pending nudges that are due for delivery.

    Fetches nudges from ``nudge_queue`` where ``status='pending'`` and
    ``scheduled_for <= now()``, then processes each based on its channel:
    - ``push``: placeholder for push notification service.
    - ``email``: placeholder for email delivery.
    - ``in_app``: placeholder for in-app banner.
    - ``chat_card``: inserts a message into ``chat_logs``.

    Args:
        ctx: arq worker context.
    """
    from app.services.nudge_service import get_pending_nudges

    supabase = get_supabase_client()

    try:
        nudges = await get_pending_nudges(limit=100)

        if not nudges:
            return

        sent = 0
        failed = 0

        for nudge in nudges:
            try:
                channel = nudge["channel"]
                user_id = nudge["user_id"]
                message_data = nudge.get("message_data", {})

                if channel == "chat_card":
                    # Insert message into chat_logs.
                    await asyncio.to_thread(
                        lambda uid=user_id, md=message_data: (
                            supabase.table("chat_logs")
                            .insert({
                                "id": str(uuid4()),
                                "user_id": uid,
                                "user_message": "",
                                "assistant_message": json.dumps(md),
                                "message_type": "nudge_card",
                                "created_at": datetime.now(timezone.utc).isoformat(),
                            })
                            .execute()
                        )
                    )
                elif channel == "push":
                    # Placeholder: integrate with push notification service.
                    logger.info(
                        "Push nudge delivery (placeholder)",
                        extra={"user_id": user_id, "nudge_id": nudge["id"]},
                    )
                elif channel == "email":
                    # Placeholder: integrate with email service.
                    logger.info(
                        "Email nudge delivery (placeholder)",
                        extra={"user_id": user_id, "nudge_id": nudge["id"]},
                    )
                elif channel == "in_app":
                    # Placeholder: integrate with in-app notification system.
                    logger.info(
                        "In-app nudge delivery (placeholder)",
                        extra={"user_id": user_id, "nudge_id": nudge["id"]},
                    )

                # Mark as sent.
                await asyncio.to_thread(
                    lambda nid=nudge["id"]: supabase.table("nudge_queue")
                    .update({
                        "status": "sent",
                        "sent_at": datetime.now(timezone.utc).isoformat(),
                    })
                    .eq("id", nid)
                    .execute()
                )
                sent += 1

            except Exception:
                logger.exception(
                    "Failed to deliver nudge",
                    extra={"nudge_id": nudge["id"]},
                )
                # Mark as failed.
                try:
                    await asyncio.to_thread(
                        lambda nid=nudge["id"]: supabase.table("nudge_queue")
                        .update({"status": "failed"})
                        .eq("id", nid)
                        .execute()
                    )
                except Exception:
                    logger.exception(
                        "Failed to mark nudge as failed",
                        extra={"nudge_id": nudge["id"]},
                    )
                failed += 1

        logger.info(
            "Nudge delivery complete",
            extra={"sent": sent, "failed": failed, "total": len(nudges)},
        )

    except Exception:
        logger.exception("Nudge delivery task failed")


# ── Disengagement Sensing ─────────────────────────────────────────────────

# Rules: days since last interaction -> action
DISENGAGEMENT_RULES: dict[str, dict[str, Any]] = {
    "1_day": {"min_days": 1, "max_days": 1, "action": "none"},
    "2_days": {"min_days": 2, "max_days": 2, "action": "flag_quiet"},
    "3_to_5_days": {"min_days": 3, "max_days": 5, "action": "pause_non_critical"},
    "5_plus_days": {"min_days": 5, "max_days": None, "action": "complete_silence"},
}


def classify_disengagement(days_inactive: int) -> str:
    """Classify a user's disengagement level based on days since last activity.

    Args:
        days_inactive: Number of days since the user's last ``chat_log`` entry.

    Returns:
        One of ``"none"``, ``"flag_quiet"``, ``"pause_non_critical"``, or
        ``"complete_silence"``.
    """
    if days_inactive <= 1:
        return "none"
    elif days_inactive == 2:
        return "flag_quiet"
    elif 3 <= days_inactive <= 5:
        return "pause_non_critical"
    else:  # 5+ days
        return "complete_silence"


async def disengagement_sensing_task(ctx: dict) -> None:
    """Scan active users and apply disengagement rules.

    For each user with an active chapter, counts the days since their
    last ``chat_log`` entry and applies the appropriate rule:
    - 1 day:   no action
    - 2 days:  flag as "quiet", pause nudges
    - 3-5 days: pause all non-critical notifications
    - 5+ days: complete silence — cancel all scheduled nudges

    Args:
        ctx: arq worker context.
    """
    from app.services.nudge_service import cancel_user_nudges

    supabase = get_supabase_client()

    try:
        # Fetch all active users (users with active chapters).
        result = await asyncio.to_thread(
            lambda: supabase.table("chapters")
            .select("user_id")
            .eq("status", "active")
            .execute()
        )

        active_users = {row["user_id"] for row in (result.data or [])}

        if not active_users:
            logger.info("No active users to check for disengagement")
            return

        now = datetime.now(timezone.utc)
        stats = {"none": 0, "flag_quiet": 0, "pause_non_critical": 0, "complete_silence": 0}

        for user_id in active_users:
            try:
                # Find last chat_log entry for this user.
                last_log = await asyncio.to_thread(
                    lambda uid=user_id: supabase.table("chat_logs")
                    .select("created_at")
                    .eq("user_id", uid)
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )

                if last_log.data:
                    last_activity = datetime.fromisoformat(
                        last_log.data[0]["created_at"].replace("Z", "+00:00")
                    )
                    days_inactive = (now - last_activity).days
                else:
                    # No chat logs at all — treat as highly disengaged.
                    days_inactive = 999

                action = classify_disengagement(days_inactive)
                stats[action] += 1

                if action == "flag_quiet":
                    # Pause nudges for quiet users.
                    await cancel_user_nudges(user_id)
                elif action == "pause_non_critical":
                    # Pause all non-critical notifications.
                    await cancel_user_nudges(user_id)
                elif action == "complete_silence":
                    # Complete silence — cancel everything.
                    await cancel_user_nudges(user_id)

            except Exception:
                logger.exception(
                    "Failed to check disengagement for user",
                    extra={"user_id": user_id},
                )

        logger.info(
            "Disengagement sensing complete",
            extra={
                "active_users": len(active_users),
                **stats,
            },
        )

    except Exception:
        logger.exception("Disengagement sensing task failed")


# ── Cache Refresh ─────────────────────────────────────────────────────────

# Landing page preview questions (English only for now).
PREVIEW_QUESTIONS: list[str] = [
    "What should I eat during IVF stimulation?",
    "How can I manage fertility treatment stress?",
    "What supplements help with egg quality?",
]


async def cache_refresh_task(ctx: dict) -> None:
    """Refresh the landing page preview cache.

    Runs the full swarm pipeline (gatekeeper -> RAG -> curator ->
    compliance) for each preview question and stores the results in
    Redis with a 24-hour TTL.

    Args:
        ctx: arq worker context.
    """
    redis = ctx["redis"]

    try:
        from app.services.clinical_brain import ClinicalBrain
        from app.services.compliance_checker import ComplianceChecker
        from app.services.gatekeeper import Gatekeeper
        from app.services.response_curator import ChatResponseCurator

        gk = Gatekeeper()
        brain = ClinicalBrain()
        curator = ChatResponseCurator()
        compliance = ComplianceChecker()

        results: list[dict[str, Any]] = []

        for question in PREVIEW_QUESTIONS:
            trace_id = str(uuid4())

            try:
                # Gatekeeper.
                classification = await gk.classify(question, trace_id=trace_id)
                if not classification.get("safe", True):
                    continue

                # RAG search.
                rag_result = await brain.search([question])

                rag_text = ""
                if rag_result.matches:
                    parts = []
                    for idx, match in enumerate(rag_result.matches, 1):
                        title = match.metadata.get("title", f"Source {idx}")
                        parts.append(
                            f"[Source {idx}] {title}: {match.content}"
                        )
                    rag_text = "\n\n".join(parts)

                # Curator.
                response = await curator.curate(
                    question=question,
                    context_summary="",
                    rag_sources=rag_text,
                    user_profile="{}",
                    trace_id=trace_id,
                )

                # Compliance.
                response = await compliance.check(response, trace_id=trace_id)

                results.append({
                    "question": question,
                    "answer": response,
                    "source_count": len(rag_result.matches),
                })

            except Exception:
                logger.exception(
                    "Failed to generate preview for question",
                    extra={"question": question},
                )

        # Store in Redis with 24-hour TTL.
        cache_key = "preview_cache:en"
        await redis.set(
            cache_key,
            json.dumps(results, default=str),
        )
        await redis.expire(cache_key, 86400)  # 24 hours

        logger.info(
            "Cache refresh complete",
            extra={"questions_processed": len(results)},
        )

    except Exception:
        logger.exception("Cache refresh task failed")


# ── Data Lifecycle ────────────────────────────────────────────────────────


async def data_lifecycle_task(ctx: dict) -> None:
    """Perform data lifecycle maintenance (Decision 20).

    - Delete ``chat_traces`` rows older than 90 days.
    - Move ``chat_logs`` from completed cycles (>90 days old) to
      ``chat_logs_archive``.
    - Log statistics for auditing.

    Args:
        ctx: arq worker context.
    """
    supabase = get_supabase_client()

    try:
        now = datetime.now(timezone.utc)
        cutoff = (now - timedelta(days=90)).isoformat()

        # ── Delete old chat_traces ───────────────────────────────────
        traces_result = await asyncio.to_thread(
            lambda: supabase.table("chat_traces")
            .select("id")
            .lt("created_at", cutoff)
            .execute()
        )
        traces_to_delete = len(traces_result.data) if traces_result.data else 0

        if traces_to_delete > 0:
            await asyncio.to_thread(
                lambda: supabase.table("chat_traces")
                .delete()
                .lt("created_at", cutoff)
                .execute()
            )

        # ── Archive old chat_logs from completed cycles ──────────────
        # Find completed chapters older than 90 days.
        old_chapters = await asyncio.to_thread(
            lambda: supabase.table("chapters")
            .select("id, user_id")
            .eq("status", "completed")
            .lt("ended_at", cutoff)
            .execute()
        )

        rows_archived = 0

        for chapter in (old_chapters.data or []):
            # Fetch logs for this chapter.
            logs = await asyncio.to_thread(
                lambda cid=chapter["id"]: supabase.table("chat_logs")
                .select("*")
                .eq("chapter_id", cid)
                .execute()
            )

            if not logs.data:
                continue

            # Insert into archive.
            await asyncio.to_thread(
                lambda rows=logs.data: supabase.table("chat_logs_archive")
                .insert(rows)
                .execute()
            )

            # Delete from chat_logs.
            for log in logs.data:
                await asyncio.to_thread(
                    lambda lid=log["id"]: supabase.table("chat_logs")
                    .delete()
                    .eq("id", lid)
                    .execute()
                )

            rows_archived += len(logs.data)

        logger.info(
            "Data lifecycle maintenance complete",
            extra={
                "traces_deleted": traces_to_delete,
                "rows_archived": rows_archived,
                "cutoff_date": cutoff,
            },
        )

    except Exception:
        logger.exception("Data lifecycle task failed")
