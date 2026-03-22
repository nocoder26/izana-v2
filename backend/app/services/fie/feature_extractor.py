"""
FIE Stage 1: Feature Extraction.

Reads production tables (READ-ONLY) and extracts anonymized features
per cycle for the Fertility Intelligence Engine.

RULES (from build guide):
- READ-ONLY on production tables
- Writes ONLY to fie.feature_store
- All user identifiers are hashed before storage
- Runs as a background job, never in request context
- Can be disabled via FEATURE_FIE_ENABLED=false
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from app.core.config import get_settings
from app.core.database import get_supabase_client
from app.core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


def anonymize_cycle(user_id: str, cycle_id: str) -> str:
    """One-way hash. Cannot be reversed to identify user."""
    salt = settings.FIE_ANONYMIZATION_SALT
    raw = f"{user_id}:{cycle_id}:{salt}"
    return hashlib.sha256(raw.encode()).hexdigest()


class FeatureExtractor:
    """Extract and anonymize features from production data."""

    def __init__(self):
        self.db = get_supabase_client()

    async def extract_all_cycles(self) -> int:
        """Extract features for all cycles. Returns count of cycles processed."""
        if not settings.FEATURE_FIE_ENABLED:
            logger.info("FIE is disabled, skipping extraction")
            return 0

        cycles = self.db.table("cycles").select("*").execute()
        processed = 0

        for cycle in cycles.data or []:
            try:
                features = await self.extract_cycle_features(
                    cycle["user_id"], cycle["id"]
                )
                if features:
                    # Upsert into fie.feature_store
                    self.db.schema("fie").table("feature_store").upsert(
                        features, on_conflict="anonymous_cycle_id"
                    ).execute()
                    processed += 1
            except Exception as e:
                logger.error(f"FIE extraction error for cycle {cycle['id']}: {e}")

        logger.info(f"FIE extracted features for {processed} cycles")
        return processed

    async def extract_cycle_features(self, user_id: str, cycle_id: str) -> dict | None:
        """Extract all features for a single cycle."""
        anon_id = anonymize_cycle(user_id, cycle_id)

        profile = self.db.table("profiles").select("*").eq("id", user_id).single().execute()
        if not profile.data:
            return None

        cycle = self.db.table("cycles").select("*").eq("id", cycle_id).single().execute()
        if not cycle.data:
            return None

        p = profile.data
        c = cycle.data

        # Category A: Demographics
        demographics = {
            "age_range": p.get("age_range"),
            "bmi": float(p["bmi"]) if p.get("bmi") else None,
            "health_conditions": p.get("health_conditions", []),
            "smoking": p.get("smoking_status"),
            "alcohol": p.get("alcohol_consumption"),
            "sleep_duration": p.get("sleep_duration"),
            "stress": p.get("stress_level"),
            "fitness": p.get("fitness_level"),
        }

        # Category B: Biomarkers
        biomarkers = p.get("core_fertility_json", {})

        # Category C: Behavioral (simplified — full version would aggregate per phase)
        meal_count = self.db.table("meal_logs").select("id", count="exact").eq("user_id", user_id).execute()
        activity_count = self.db.table("activity_logs").select("id", count="exact").eq("user_id", user_id).execute()
        checkin_count = self.db.table("emotion_logs").select("id", count="exact").eq("user_id", user_id).execute()

        behavioral = {
            "total_meals_logged": meal_count.count or 0,
            "total_activities_logged": activity_count.count or 0,
            "total_checkins": checkin_count.count or 0,
        }

        # Category D: Treatment
        chapters = self.db.table("chapters").select("*").eq("cycle_id", cycle_id).execute()
        treatment = {
            "treatment_type": c.get("treatment_type"),
            "cycle_number": c.get("cycle_number"),
            "chapter_count": len(chapters.data or []),
        }

        outcome = c.get("outcome")

        return {
            "anonymous_cycle_id": anon_id,
            "treatment_type": c.get("treatment_type"),
            "cycle_number": c.get("cycle_number"),
            "features_demographic": demographics,
            "features_biomarker": biomarkers,
            "features_behavioral": behavioral,
            "features_treatment": treatment,
            "outcome": outcome,
            "outcome_binary": 1 if outcome == "POSITIVE" else (0 if outcome else None),
            "cycle_completed": outcome is not None,
        }
