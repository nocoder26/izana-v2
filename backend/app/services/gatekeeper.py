"""
Swarm 1 — Gatekeeper: Safety and intent classification agent.

Classifies incoming user messages to determine whether they are safe
(no harmful content) and whether they relate to fertility topics.
Downstream orchestration uses this classification to decide routing.

Swarm index: 1
Config key:  ``swarm_1_gatekeeper``
"""

from __future__ import annotations

import json
from typing import Any

from app.core.logging_config import get_logger
from app.core.model_config import SWARM_CONFIG
from app.services.swarm_base import SwarmBase

logger = get_logger(__name__)

# Default fail-open response — allows the message through when the
# LLM is unavailable so that users are not silently blocked.
_FALLBACK: dict[str, Any] = {
    "safe": True,
    "is_fertility_related": True,
    "category": "general",
}


class Gatekeeper(SwarmBase):
    """Classify a user message for safety and fertility relevance.

    The LLM returns a compact JSON object with three keys:

    - ``safe`` (bool): ``True`` if the message contains no harmful,
      abusive, or dangerous content.
    - ``is_fertility_related`` (bool): ``True`` if the message is
      related to fertility, reproductive health, nutrition, or
      wellness topics within the app's scope.
    - ``category`` (str): A short label for the topic, e.g.
      ``"nutrition"``, ``"medication"``, ``"emotional_support"``,
      ``"off_topic"``.

    Attributes:
        swarm_id: ``"swarm_1_gatekeeper"``
    """

    swarm_id: str = "swarm_1_gatekeeper"

    # ── SwarmBase interface ─────────────────────────────────────────────

    def build_messages(self, text: str) -> list[dict[str, str]]:
        """Build classification prompt messages.

        Args:
            text: The user message to classify.

        Returns:
            A messages list for the Groq chat completion API.
        """
        return [
            {
                "role": "system",
                "content": (
                    "You are a safety and intent classifier for a fertility "
                    "health application. Analyse the following user message "
                    "and return a JSON object with exactly these keys:\n\n"
                    '  "safe" (boolean) — true if the message is free of '
                    "harmful, abusive, or dangerous content.\n"
                    '  "is_fertility_related" (boolean) — true if the message '
                    "relates to fertility, reproductive health, pregnancy, "
                    "nutrition, supplements, hormones, bloodwork, emotional "
                    "wellbeing during fertility treatment, or general wellness "
                    "in the context of trying to conceive.\n"
                    '  "category" (string) — a short topic label such as '
                    '"nutrition", "medication", "emotional_support", '
                    '"bloodwork", "lifestyle", "general", or "off_topic".\n\n'
                    "Return ONLY the JSON object. No explanation, no markdown."
                ),
            },
            {
                "role": "user",
                "content": text,
            },
        ]

    def validate_output(self, output: str) -> bool:
        """Validate that the LLM returned well-formed classification JSON.

        Args:
            output: Raw LLM response content.

        Returns:
            ``True`` when *output* parses as JSON and contains the
            required ``"safe"`` and ``"is_fertility_related"`` keys.
        """
        parsed = self._parse_json(output)
        if not isinstance(parsed, dict):
            return False
        return "safe" in parsed and "is_fertility_related" in parsed

    def get_fallback_value(self) -> dict[str, Any]:
        """Return a fail-open classification.

        When the LLM is unavailable it is safer to let the message
        through (fail-open) than to silently block a legitimate user
        query.
        """
        return dict(_FALLBACK)

    # ── Convenience method ──────────────────────────────────────────────

    async def classify(self, text: str, trace_id: str = "") -> dict[str, Any]:
        """Classify *text* for safety and fertility relevance.

        This is the primary public API for the Gatekeeper swarm.

        Args:
            text:     The user message to classify.
            trace_id: Optional trace identifier for logging.

        Returns:
            A dict with ``"safe"``, ``"is_fertility_related"``, and
            ``"category"`` keys.  On LLM failure the fail-open fallback
            is returned.
        """
        result = await self.run(text, trace_id=trace_id)

        # If run() returned the fallback dict directly, use it.
        if isinstance(result, dict):
            return result

        # Otherwise parse the LLM string output.
        parsed = self._parse_json(str(result))
        if isinstance(parsed, dict) and "safe" in parsed:
            return parsed

        logger.warning(
            "Gatekeeper could not parse LLM output, using fallback",
            extra={"swarm_id": self.swarm_id, "trace_id": trace_id},
        )
        return dict(_FALLBACK)
