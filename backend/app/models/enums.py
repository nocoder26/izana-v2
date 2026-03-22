"""
Centralised enum definitions for the Izana backend.

All enums use string values so they serialise cleanly to JSON and can be
stored directly in Supabase text columns without extra conversion.
"""

from __future__ import annotations

from enum import Enum


# ---------------------------------------------------------------------------
# Treatment types
# ---------------------------------------------------------------------------

class TreatmentType(str, Enum):
    """Fertility treatment pathways supported by the platform."""

    IVF = "ivf"
    IUI = "iui"
    NATURAL = "natural"
    EGG_FREEZING = "egg_freezing"
    EXPLORING = "exploring"


# ---------------------------------------------------------------------------
# Phase enums — one per treatment type
# ---------------------------------------------------------------------------

class IVFPhase(str, Enum):
    """Twelve sequential phases of a standard IVF cycle."""

    INITIAL_CONSULTATION = "initial_consultation"
    DIAGNOSTIC_TESTING = "diagnostic_testing"
    OVARIAN_STIMULATION = "ovarian_stimulation"
    MONITORING = "monitoring"
    TRIGGER_SHOT = "trigger_shot"
    EGG_RETRIEVAL = "egg_retrieval"
    FERTILISATION = "fertilisation"
    EMBRYO_CULTURE = "embryo_culture"
    EMBRYO_TRANSFER = "embryo_transfer"
    LUTEAL_SUPPORT = "luteal_support"
    BETA_HCG_TEST = "beta_hcg_test"
    OUTCOME = "outcome"


class IUIPhase(str, Enum):
    """Eight sequential phases of an IUI cycle."""

    INITIAL_CONSULTATION = "initial_consultation"
    DIAGNOSTIC_TESTING = "diagnostic_testing"
    OVARIAN_STIMULATION = "ovarian_stimulation"
    MONITORING = "monitoring"
    TRIGGER_SHOT = "trigger_shot"
    INSEMINATION = "insemination"
    LUTEAL_SUPPORT = "luteal_support"
    OUTCOME = "outcome"


class NaturalPhase(str, Enum):
    """Phases for natural conception attempts."""

    PRECONCEPTION = "preconception"
    CYCLE_TRACKING = "cycle_tracking"
    FERTILE_WINDOW = "fertile_window"
    TWO_WEEK_WAIT = "two_week_wait"
    OUTCOME = "outcome"


class EggFreezingPhase(str, Enum):
    """Phases of an egg-freezing cycle."""

    INITIAL_CONSULTATION = "initial_consultation"
    DIAGNOSTIC_TESTING = "diagnostic_testing"
    OVARIAN_STIMULATION = "ovarian_stimulation"
    MONITORING = "monitoring"
    TRIGGER_SHOT = "trigger_shot"
    EGG_RETRIEVAL = "egg_retrieval"
    RECOVERY = "recovery"


class ExploringPhase(str, Enum):
    """Phases for users who are still exploring their options."""

    LEARNING = "learning"
    LIFESTYLE_OPTIMISATION = "lifestyle_optimisation"
    DIAGNOSTIC_TESTING = "diagnostic_testing"
    DECISION_MAKING = "decision_making"


# ---------------------------------------------------------------------------
# Plan lifecycle
# ---------------------------------------------------------------------------

class PlanStatus(str, Enum):
    """Status values for a nutrition / supplement plan."""

    GENERATING = "generating"
    PENDING_NUTRITIONIST = "pending_nutritionist"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    MODIFIED = "modified"
    REJECTED = "rejected"
    EXPIRED = "expired"


# ---------------------------------------------------------------------------
# Journey chapter
# ---------------------------------------------------------------------------

class ChapterStatus(str, Enum):
    """High-level status of a user's current journey chapter."""

    ACTIVE = "active"
    COMPLETED = "completed"
    GRIEF = "grief"
    POSITIVE = "positive"


# ---------------------------------------------------------------------------
# Nutritionist approval queue
# ---------------------------------------------------------------------------

class ApprovalPriority(str, Enum):
    """Priority tiers for the nutritionist approval queue."""

    NORMAL = "normal"
    URGENT_PHASE_CHANGE = "urgent_phase_change"
    POSITIVE_OUTCOME = "positive_outcome"


# ---------------------------------------------------------------------------
# Mood tracking
# ---------------------------------------------------------------------------

class Mood(str, Enum):
    """User-reported daily mood values."""

    GREAT = "great"
    GOOD = "good"
    OKAY = "okay"
    LOW = "low"
    STRUGGLING = "struggling"


# ---------------------------------------------------------------------------
# Content library
# ---------------------------------------------------------------------------

class ContentType(str, Enum):
    """Types of wellness content available in the content library."""

    EXERCISE_VIDEO = "exercise_video"
    MEDITATION_AUDIO = "meditation_audio"
    BREATHING_EXERCISE = "breathing_exercise"
    YOGA_VIDEO = "yoga_video"
    ARTICLE = "article"
    AUDIO_GUIDE = "audio_guide"


# ---------------------------------------------------------------------------
# User roles (internal platform)
# ---------------------------------------------------------------------------

class UserRole(str, Enum):
    """Roles for internal platform users (nutritionists, admins)."""

    NUTRITIONIST = "nutritionist"
    ADMIN = "admin"
