"""
FIE Stage 5: Feedback Provider.

Provides actionable insights to swarms for enriched plan generation.
Reads from fie.insights where actionable=true and confidence='high'.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.core.database import get_supabase_client
from app.core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


class FIEFeedbackProvider:
    """Provides actionable insights to swarms for enriched plan generation."""

    def __init__(self):
        self.db = get_supabase_client()

    async def get_plan_context(
        self, treatment_type: str, phase: str
    ) -> str:
        """Return a text summary of relevant insights for plan generation.

        This context is appended to the Nutrition Swarm 2's system prompt.
        """
        if not settings.FEATURE_FIE_ENABLED:
            return ""

        try:
            result = self.db.schema("fie").table("insights") \
                .select("description") \
                .eq("actionable", True) \
                .eq("confidence", "high") \
                .eq("treatment_type", treatment_type) \
                .limit(5) \
                .execute()

            insights = result.data or []
            if not insights:
                return ""

            lines = ["Based on Izana's data from completed cycles:"]
            for insight in insights:
                lines.append(f"- {insight['description']}")

            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"FIE feedback provider error: {e}")
            return ""
