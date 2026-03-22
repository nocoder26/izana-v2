"""
FIE Stage 3: Insight Discovery.

Discovers correlations between behavior, biomarkers, and outcomes
from completed cycles. Writes to fie.insights table.

Runs weekly. Requires minimum 50 completed cycles for statistical significance.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.core.database import get_supabase_client
from app.core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


class InsightEngine:
    """Discover correlations between behavior, biomarkers, and outcomes."""

    def __init__(self):
        self.db = get_supabase_client()
        self.min_cycles = settings.FIE_MIN_CYCLES_FOR_INSIGHTS

    async def run_weekly_analysis(self) -> int:
        """Run all insight analyses. Returns count of insights generated."""
        if not settings.FEATURE_FIE_ENABLED:
            logger.info("FIE is disabled, skipping insight analysis")
            return 0

        # Get completed cycles from feature store
        result = self.db.schema("fie").table("feature_store") \
            .select("*") \
            .eq("cycle_completed", True) \
            .execute()

        completed_cycles = result.data or []

        if len(completed_cycles) < self.min_cycles:
            logger.info(
                f"Insufficient data for insights ({len(completed_cycles)} < {self.min_cycles})"
            )
            return 0

        insights_count = 0

        # Placeholder insight analyses — will be expanded with real statistical methods
        # when sufficient data is available

        try:
            # Adherence → Outcome correlations
            insight = {
                "insight_type": "adherence_outcome_correlation",
                "treatment_type": "IVF",
                "description": f"Analysis pending — {len(completed_cycles)} cycles available",
                "sample_size": len(completed_cycles),
                "confidence": "low",
                "actionable": False,
                "insight_data": {"cycles_analyzed": len(completed_cycles)},
            }
            self.db.schema("fie").table("insights").insert(insight).execute()
            insights_count += 1
        except Exception as e:
            logger.error(f"FIE insight generation error: {e}")

        logger.info(f"FIE generated {insights_count} insights from {len(completed_cycles)} cycles")
        return insights_count
