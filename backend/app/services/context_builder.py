"""
Swarm 9 \u2014 ContextBuilder: Conversation context summarisation agent.

Summarises the user's current conversational and clinical context into
a compact JSON object (under 300 tokens) that downstream swarms can use
to personalise responses.  Includes treatment phase, day count, mood,
recent topics, and key bloodwork values when available.

The ``user_context_data`` input should be fetched from the database
before calling this swarm.

Swarm index: 9
Config key:  ``swarm_9_context``
"""

from __future__ import annotations

import json
from typing import Any

from app.core.logging_config import get_logger
from app.core.model_config import SWARM_CONFIG
from app.services.swarm_base import SwarmBase

logger = get_logger(__name__)

_FALLBACK_CONTEXT: dict[str, Any] = {
    "phase": "unknown",
    "day": 0,
    "treatment": "unknown",
    "mood": None,
    "summary": "",
    "key_bloodwork": None,
}


class ContextBuilder(SwarmBase):
    """Summarise user context for downstream response personalisation.

    Produces a compact JSON summary of the user's current state:
    treatment type, phase, day count, recent mood, last message topics,
    and key bloodwork values.

    Attributes:
        swarm_id: ``"swarm_9_context"``
    """

    swarm_id: str = "swarm_9_context"

    # ── SwarmBase interface ──────────────────────────────────────────────

    def build_messages(
        self,
        user_id_context: dict[str, Any] | str,
    ) -> list[dict[str, str]]:
        """Construct the context-summarisation prompt.

        Args:
            user_id_context: A dict (or JSON string) of raw user context
                             data fetched from the database, including
                             conversation history, treatment info, and
                             bloodwork records.

        Returns:
            Messages list ready for the Groq chat completion API.
        """
        system_prompt = (
            "Summarize the user's current context in under 300 tokens. "
            "Include: treatment type, phase, day count, recent mood, "
            "last 3 message topics, key bloodwork values if available. "
            'Return JSON: {"phase": str, "day": int, "treatment": str, '
            '"mood": str|null, "summary": str, "key_bloodwork": dict|null}'
        )
        if isinstance(user_id_context, dict):
            user_content = json.dumps(user_id_context, default=str)
        else:
            user_content = str(user_id_context)

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    def validate_output(self, output: str) -> bool:
        """Verify the LLM returned valid JSON with the ``summary`` key.

        Args:
            output: Raw LLM response string.

        Returns:
            ``True`` if the output is valid JSON containing ``"summary"``;
            ``False`` otherwise.
        """
        parsed = self._parse_json(output)
        if not isinstance(parsed, dict):
            return False
        return "summary" in parsed

    def get_fallback_value(self) -> str:
        """Return a JSON string with empty/unknown context fields.

        Returns:
            A JSON string representing the default empty context.
        """
        return json.dumps(_FALLBACK_CONTEXT)

    # ── Public convenience method ────────────────────────────────────────

    async def get_context(
        self,
        user_context_data: dict[str, Any] | str,
        trace_id: str = "",
    ) -> dict[str, Any]:
        """Build a summarised context dict for the current user.

        Args:
            user_context_data: Raw context data fetched from the database.
            trace_id:          Correlation identifier for tracing.

        Returns:
            A dict with keys ``phase``, ``day``, ``treatment``, ``mood``,
            ``summary``, and ``key_bloodwork``.  Returns the fallback
            context on any failure.
        """
        result = await self.run(user_context_data, trace_id=trace_id)

        parsed = self._parse_json(result) if isinstance(result, str) else result
        if isinstance(parsed, dict) and "summary" in parsed:
            return parsed

        return dict(_FALLBACK_CONTEXT)
