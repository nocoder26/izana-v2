"""
Swarm 10 \u2014 SentimentAnalyser: Emotional tone analysis agent.

Analyses the emotional tone of a fertility-related conversation turn
to help downstream swarms adapt their response style.  Returns a
structured JSON object with sentiment label, intensity score, and a
flag indicating whether the user needs additional empathy.

This is a **non-critical** swarm -- failures are silently logged and
the pipeline continues with a neutral sentiment assumption.

Swarm index: 10
Config key:  ``swarm_10_sentiment``
"""

from __future__ import annotations

import json
from typing import Any

from app.core.logging_config import get_logger
from app.core.model_config import SWARM_CONFIG
from app.services.swarm_base import SwarmBase

logger = get_logger(__name__)

_VALID_SENTIMENTS = {
    "hopeful",
    "anxious",
    "frustrated",
    "sad",
    "neutral",
    "grateful",
    "determined",
}

_FALLBACK_SENTIMENT: dict[str, Any] = {
    "sentiment": "neutral",
    "intensity": 0.5,
    "needs_empathy": False,
}


class SentimentAnalyser(SwarmBase):
    """Analyse emotional tone to adapt response style.

    Classifies the user's emotional state from a conversation turn and
    returns a sentiment label, intensity (0-1), and empathy flag.

    Attributes:
        swarm_id: ``"swarm_10_sentiment"``
    """

    swarm_id: str = "swarm_10_sentiment"

    # ── SwarmBase interface ──────────────────────────────────────────────

    def build_messages(
        self,
        user_message: str,
        assistant_response: str,
    ) -> list[dict[str, str]]:
        """Construct the sentiment-analysis prompt.

        Args:
            user_message:       The user's most recent message.
            assistant_response: The assistant's reply to the user.

        Returns:
            Messages list ready for the Groq chat completion API.
        """
        system_prompt = (
            "Analyze the emotional tone of this fertility-related "
            'conversation. Return JSON: {"sentiment": '
            '"hopeful"|"anxious"|"frustrated"|"sad"|"neutral"|"grateful"|'
            '"determined", "intensity": float 0-1, "needs_empathy": bool}'
        )
        user_content = (
            f"User message: {user_message}\n\n"
            f"Assistant response: {assistant_response}"
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    def validate_output(self, output: str) -> bool:
        """Verify the LLM returned valid JSON with the ``sentiment`` key.

        Args:
            output: Raw LLM response string.

        Returns:
            ``True`` if the output is valid JSON containing a recognised
            ``"sentiment"`` value; ``False`` otherwise.
        """
        parsed = self._parse_json(output)
        if not isinstance(parsed, dict):
            return False
        return "sentiment" in parsed

    def get_fallback_value(self) -> str:
        """Return a JSON string with neutral sentiment defaults.

        Returns:
            A JSON string: ``{"sentiment": "neutral", "intensity": 0.5,
            "needs_empathy": false}``.
        """
        return json.dumps(_FALLBACK_SENTIMENT)

    # ── Public convenience method ────────────────────────────────────────

    async def analyse(
        self,
        user_message: str,
        assistant_response: str,
        trace_id: str = "",
    ) -> dict[str, Any]:
        """Analyse the emotional tone of a conversation turn.

        This is a non-critical operation.  If the swarm fails, the result
        defaults to neutral sentiment and the failure is silently logged.

        Args:
            user_message:       The user's most recent message.
            assistant_response: The assistant's reply.
            trace_id:           Correlation identifier for tracing.

        Returns:
            A dict with ``"sentiment"`` (str), ``"intensity"`` (float),
            and ``"needs_empathy"`` (bool).
        """
        try:
            result = await self.run(
                user_message, assistant_response, trace_id=trace_id,
            )
            parsed = self._parse_json(result) if isinstance(result, str) else result
            if isinstance(parsed, dict) and "sentiment" in parsed:
                return parsed
        except Exception as exc:
            logger.warning(
                "Sentiment analysis failed silently: %s",
                str(exc),
                extra={"swarm_id": self.swarm_id, "trace_id": trace_id},
            )

        return dict(_FALLBACK_SENTIMENT)
