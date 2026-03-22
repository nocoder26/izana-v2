"""
Stage 9 tests: Background jobs, gamification, chapters, and services.

Tests cover:
- Gamification point values match specification (Decision 15)
- Level thresholds are ascending and correctly mapped
- Streak increment logic
- Plan status returns correct state
- Chapter create/close lifecycle
- Disengagement sensing rules (1d, 2d, 3-5d, 5+ days)

All tests use mocks — no API calls or database connections (Decision 19).
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# ── Gamification Tests ────────────────────────────────────────────────────


class TestGamificationPointValues:
    """Verify point values match Decision 15 specification."""

    def test_point_values_match_spec(self):
        """All point values must match the Decision 15 specification."""
        from app.services.gamification_service import POINT_VALUES

        assert POINT_VALUES["meal_logged"] == 10
        assert POINT_VALUES["exercise_completed"] == 15
        assert POINT_VALUES["meditation_completed"] == 10
        assert POINT_VALUES["daily_checkin"] == 10
        assert POINT_VALUES["streak_bonus"] == 5
        assert POINT_VALUES["all_5_done"] == 10
        assert POINT_VALUES["bloodwork_upload"] == 25
        assert POINT_VALUES["partner_connected"] == 50

    def test_all_required_actions_present(self):
        """POINT_VALUES must contain all expected action keys."""
        from app.services.gamification_service import POINT_VALUES

        required_actions = {
            "meal_logged",
            "exercise_completed",
            "meditation_completed",
            "daily_checkin",
            "streak_bonus",
            "all_5_done",
            "bloodwork_upload",
            "partner_connected",
        }

        assert set(POINT_VALUES.keys()) == required_actions

    def test_all_point_values_are_positive(self):
        """Every point value must be a positive integer."""
        from app.services.gamification_service import POINT_VALUES

        for action, points in POINT_VALUES.items():
            assert isinstance(points, int), f"{action} value is not int"
            assert points > 0, f"{action} has non-positive value {points}"


class TestLevelThresholds:
    """Verify level thresholds are valid and ascending."""

    def test_thresholds_ascending(self):
        """Level thresholds must be sorted in ascending order by points."""
        from app.services.gamification_service import LEVEL_THRESHOLDS

        points = [t[0] for t in LEVEL_THRESHOLDS]
        assert points == sorted(points), "Thresholds are not ascending"

    def test_levels_are_sequential(self):
        """Level numbers must be sequential starting from 1."""
        from app.services.gamification_service import LEVEL_THRESHOLDS

        levels = [t[1] for t in LEVEL_THRESHOLDS]
        assert levels == list(range(1, len(LEVEL_THRESHOLDS) + 1))

    def test_all_levels_have_names(self):
        """Every level must have a non-empty name."""
        from app.services.gamification_service import LEVEL_THRESHOLDS

        for min_pts, level, name in LEVEL_THRESHOLDS:
            assert isinstance(name, str) and len(name) > 0, (
                f"Level {level} has empty or invalid name"
            )

    def test_first_threshold_starts_at_zero(self):
        """The lowest threshold must start at 0 points."""
        from app.services.gamification_service import LEVEL_THRESHOLDS

        assert LEVEL_THRESHOLDS[0][0] == 0

    def test_get_level_for_zero_points(self):
        """Zero points should return level 1 (Beginner)."""
        from app.services.gamification_service import get_level_for_points

        level, name = get_level_for_points(0)
        assert level == 1
        assert name == "Beginner"

    def test_get_level_for_exact_threshold(self):
        """Points exactly at a threshold should return that level."""
        from app.services.gamification_service import get_level_for_points

        level, name = get_level_for_points(100)
        assert level == 2
        assert name == "Committed"

    def test_get_level_for_between_thresholds(self):
        """Points between thresholds return the lower threshold's level."""
        from app.services.gamification_service import get_level_for_points

        level, name = get_level_for_points(250)
        assert level == 2
        assert name == "Committed"

    def test_get_level_for_max_points(self):
        """Very high points should return the highest level."""
        from app.services.gamification_service import get_level_for_points

        level, name = get_level_for_points(99999)
        assert level == 7
        assert name == "Luminous"

    def test_level_thresholds_match_spec(self):
        """Level thresholds must match the Decision 15 specification."""
        from app.services.gamification_service import LEVEL_THRESHOLDS

        expected = [
            (0, 1, "Beginner"),
            (100, 2, "Committed"),
            (300, 3, "Dedicated"),
            (600, 4, "Warrior"),
            (1000, 5, "Champion"),
            (2000, 6, "Radiant"),
            (4000, 7, "Luminous"),
        ]
        assert LEVEL_THRESHOLDS == expected


class TestStreakIncrement:
    """Test streak increment logic."""

    @pytest.mark.asyncio
    async def test_streak_increment_existing_user(self):
        """Incrementing streak for existing user increases current_streak."""
        from app.services.gamification_service import increment_streak

        mock_client = MagicMock()

        # First call: select current streak (returns existing record).
        select_mock = MagicMock()
        select_mock.execute.return_value = MagicMock(
            data={"current_streak": 3, "longest_streak": 5}
        )
        # Second call: update streak.
        update_mock = MagicMock()
        update_mock.execute.return_value = MagicMock(data=[])
        # Third call (award_points select): gamification record.
        award_select_mock = MagicMock()
        award_select_mock.execute.return_value = MagicMock(
            data={"total_points": 50, "level": 1}
        )
        # Fourth call (award_points update).
        award_update_mock = MagicMock()
        award_update_mock.execute.return_value = MagicMock(data=[])

        call_count = 0

        def table_side_effect(name):
            nonlocal call_count
            call_count += 1
            table_mock = MagicMock()

            if call_count == 1:
                # gamification select for streak
                table_mock.select.return_value = MagicMock()
                table_mock.select.return_value.eq.return_value = MagicMock()
                table_mock.select.return_value.eq.return_value.maybe_single.return_value = select_mock
            elif call_count == 2:
                # gamification update for streak
                table_mock.update.return_value = MagicMock()
                table_mock.update.return_value.eq.return_value = update_mock
            elif call_count == 3:
                # gamification select for award_points
                table_mock.select.return_value = MagicMock()
                table_mock.select.return_value.eq.return_value = MagicMock()
                table_mock.select.return_value.eq.return_value.maybe_single.return_value = award_select_mock
            elif call_count == 4:
                # gamification update for award_points
                table_mock.update.return_value = MagicMock()
                table_mock.update.return_value.eq.return_value = award_update_mock

            return table_mock

        mock_client.table.side_effect = table_side_effect

        with patch("app.services.gamification_service.get_supabase_client", return_value=mock_client):
            result = await increment_streak("test-user-id")

        assert result["current_streak"] == 4
        assert result["streak_bonus_awarded"] is True

    @pytest.mark.asyncio
    async def test_streak_increment_new_user(self):
        """Incrementing streak for a new user creates the record with streak=1."""
        from app.services.gamification_service import increment_streak

        mock_client = MagicMock()

        call_count = 0

        def table_side_effect(name):
            nonlocal call_count
            call_count += 1
            table_mock = MagicMock()

            if call_count == 1:
                # gamification select (no existing record)
                maybe_single = MagicMock()
                maybe_single.execute.return_value = MagicMock(data=None)
                table_mock.select.return_value = MagicMock()
                table_mock.select.return_value.eq.return_value = MagicMock()
                table_mock.select.return_value.eq.return_value.maybe_single.return_value = maybe_single
            elif call_count == 2:
                # gamification insert (new record)
                insert_mock = MagicMock()
                insert_mock.execute.return_value = MagicMock(data=[{"current_streak": 1}])
                table_mock.insert.return_value = insert_mock
            elif call_count == 3:
                # award_points select
                maybe_single = MagicMock()
                maybe_single.execute.return_value = MagicMock(
                    data={"total_points": 0, "level": 1}
                )
                table_mock.select.return_value = MagicMock()
                table_mock.select.return_value.eq.return_value = MagicMock()
                table_mock.select.return_value.eq.return_value.maybe_single.return_value = maybe_single
            elif call_count == 4:
                # award_points update
                update_mock = MagicMock()
                update_mock.execute.return_value = MagicMock(data=[])
                table_mock.update.return_value = MagicMock()
                table_mock.update.return_value.eq.return_value = update_mock

            return table_mock

        mock_client.table.side_effect = table_side_effect

        with patch("app.services.gamification_service.get_supabase_client", return_value=mock_client):
            result = await increment_streak("new-user-id")

        assert result["current_streak"] == 1
        assert result["streak_bonus_awarded"] is True


# ── Plan Service Tests ────────────────────────────────────────────────────


class TestPlanStatus:
    """Test plan status polling."""

    @pytest.mark.asyncio
    async def test_plan_status_returns_correct_state(self):
        """get_plan_status should return the most recent plan's status."""
        from app.services.plan_service import get_plan_status

        mock_client = MagicMock()
        plan_data = {
            "id": "plan-123",
            "status": "generating",
            "created_at": "2026-03-22T10:00:00+00:00",
            "updated_at": None,
        }

        limit_mock = MagicMock()
        limit_mock.execute.return_value = MagicMock(data=[plan_data])
        order_mock = MagicMock()
        order_mock.limit.return_value = limit_mock
        eq_mock = MagicMock()
        eq_mock.order.return_value = order_mock
        select_mock = MagicMock()
        select_mock.eq.return_value = eq_mock
        mock_client.table.return_value.select.return_value = select_mock

        with patch("app.services.plan_service.get_supabase_client", return_value=mock_client):
            result = await get_plan_status("test-user-id")

        assert result["plan_id"] == "plan-123"
        assert result["status"] == "generating"
        assert result["created_at"] == "2026-03-22T10:00:00+00:00"

    @pytest.mark.asyncio
    async def test_plan_status_no_plan(self):
        """get_plan_status returns {'status': 'none'} when no plan exists."""
        from app.services.plan_service import get_plan_status

        mock_client = MagicMock()

        limit_mock = MagicMock()
        limit_mock.execute.return_value = MagicMock(data=[])
        order_mock = MagicMock()
        order_mock.limit.return_value = limit_mock
        eq_mock = MagicMock()
        eq_mock.order.return_value = order_mock
        select_mock = MagicMock()
        select_mock.eq.return_value = eq_mock
        mock_client.table.return_value.select.return_value = select_mock

        with patch("app.services.plan_service.get_supabase_client", return_value=mock_client):
            result = await get_plan_status("test-user-id")

        assert result == {"status": "none"}


# ── Chapter Service Tests ─────────────────────────────────────────────────


class TestChapterLifecycle:
    """Test chapter create and close operations."""

    @pytest.mark.asyncio
    async def test_chapter_create_sets_active_status(self):
        """Creating a chapter should set status to 'active'."""
        from app.services.chapter_service import create_chapter

        mock_client = MagicMock()
        insert_mock = MagicMock()
        insert_mock.execute.return_value = MagicMock(data=[{
            "id": "chapter-123",
            "user_id": "test-user",
            "phase": "ovarian_stimulation",
            "journey_id": "journey-1",
            "cycle_id": "cycle-1",
            "status": "active",
            "started_at": "2026-03-22T10:00:00+00:00",
        }])
        mock_client.table.return_value.insert.return_value = insert_mock

        with patch("app.services.chapter_service.get_supabase_client", return_value=mock_client):
            result = await create_chapter(
                user_id="test-user",
                phase="ovarian_stimulation",
                journey_id="journey-1",
                cycle_id="cycle-1",
            )

        assert result["status"] == "active"
        assert result["phase"] == "ovarian_stimulation"

        # Verify the insert was called with active status.
        insert_call_args = mock_client.table.return_value.insert.call_args
        inserted_row = insert_call_args[0][0]
        assert inserted_row["status"] == "active"

    @pytest.mark.asyncio
    async def test_chapter_close_sets_completed_status(self):
        """Closing a chapter should set status to 'completed' and ended_at."""
        from app.services.chapter_service import close_chapter

        mock_client = MagicMock()
        update_result_mock = MagicMock()
        update_result_mock.execute.return_value = MagicMock(data=[{
            "id": "chapter-123",
            "status": "completed",
            "ended_at": "2026-03-22T18:00:00+00:00",
            "summary": "Phase completed successfully",
        }])
        eq_mock = MagicMock()
        eq_mock.execute.return_value = update_result_mock.execute.return_value
        update_mock = MagicMock()
        update_mock.eq.return_value = eq_mock
        mock_client.table.return_value.update.return_value = update_mock

        with patch("app.services.chapter_service.get_supabase_client", return_value=mock_client):
            result = await close_chapter(
                chapter_id="chapter-123",
                summary="Phase completed successfully",
            )

        assert result["status"] == "completed"
        assert result["ended_at"] is not None

        # Verify the update was called with completed status.
        update_call_args = mock_client.table.return_value.update.call_args
        update_data = update_call_args[0][0]
        assert update_data["status"] == "completed"
        assert "ended_at" in update_data

    @pytest.mark.asyncio
    async def test_chapter_close_with_empty_summary(self):
        """Closing a chapter without summary should not include summary field."""
        from app.services.chapter_service import close_chapter

        mock_client = MagicMock()
        update_result_mock = MagicMock()
        update_result_mock.execute.return_value = MagicMock(data=[{
            "id": "chapter-456",
            "status": "completed",
            "ended_at": "2026-03-22T18:00:00+00:00",
        }])
        eq_mock = MagicMock()
        eq_mock.execute.return_value = update_result_mock.execute.return_value
        update_mock = MagicMock()
        update_mock.eq.return_value = eq_mock
        mock_client.table.return_value.update.return_value = update_mock

        with patch("app.services.chapter_service.get_supabase_client", return_value=mock_client):
            result = await close_chapter(chapter_id="chapter-456")

        # Verify summary was not included in the update.
        update_call_args = mock_client.table.return_value.update.call_args
        update_data = update_call_args[0][0]
        assert "summary" not in update_data


# ── Disengagement Rules Tests ─────────────────────────────────────────────


class TestDisengagementRules:
    """Test disengagement classification logic.

    Rules (from spec):
    - 1 day:    no action
    - 2 days:   flag as "quiet", pause nudges
    - 3-5 days: pause all non-critical notifications
    - 5+ days:  complete silence, cancel all scheduled nudges
    """

    def test_one_day_inactive_no_action(self):
        """1 day of inactivity should trigger no action."""
        from app.workers.scheduled_tasks import classify_disengagement

        assert classify_disengagement(0) == "none"
        assert classify_disengagement(1) == "none"

    def test_two_days_inactive_flag_quiet(self):
        """2 days of inactivity should flag as 'quiet'."""
        from app.workers.scheduled_tasks import classify_disengagement

        assert classify_disengagement(2) == "flag_quiet"

    def test_three_to_five_days_pause_non_critical(self):
        """3-5 days of inactivity should pause non-critical notifications."""
        from app.workers.scheduled_tasks import classify_disengagement

        assert classify_disengagement(3) == "pause_non_critical"
        assert classify_disengagement(4) == "pause_non_critical"
        assert classify_disengagement(5) == "pause_non_critical"

    def test_five_plus_days_complete_silence(self):
        """5+ days of inactivity should trigger complete silence."""
        from app.workers.scheduled_tasks import classify_disengagement

        assert classify_disengagement(6) == "complete_silence"
        assert classify_disengagement(10) == "complete_silence"
        assert classify_disengagement(30) == "complete_silence"
        assert classify_disengagement(999) == "complete_silence"

    def test_disengagement_boundary_at_five_days(self):
        """Exactly 5 days should be 'pause_non_critical', not 'complete_silence'."""
        from app.workers.scheduled_tasks import classify_disengagement

        assert classify_disengagement(5) == "pause_non_critical"
        assert classify_disengagement(6) == "complete_silence"

    def test_disengagement_boundary_at_two_days(self):
        """Exactly 2 days should be 'flag_quiet', not 'none'."""
        from app.workers.scheduled_tasks import classify_disengagement

        assert classify_disengagement(1) == "none"
        assert classify_disengagement(2) == "flag_quiet"
        assert classify_disengagement(3) == "pause_non_critical"
