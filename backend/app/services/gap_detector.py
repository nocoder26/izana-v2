"""
Swarm 8 \u2014 GapDetector: Knowledge-base gap detection agent.

Determines whether the knowledge base adequately addressed a user's
question.  Returns a structured JSON assessment with gap type and
suggested topic for future content creation.

This is a **non-critical** swarm -- failures are silently logged and
the pipeline continues as if no gap was detected.

Swarm index: 8
Config key:  ``swarm_8_gap``
"""

from __future__ import annotations

import json
from typing import Any

from app.core.logging_config import get_logger
from app.core.model_config import SWARM_CONFIG
from app.services.swarm_base import SwarmBase

logger = get_logger(__name__)


class GapDetector(SwarmBase):
    """Detect gaps in knowledge-base coverage for a user question.

    The swarm analyses the RAG results summary to determine if the
    question was fully, partially, or not at all answered by the
    available sources.

    Attributes:
        swarm_id: ``"swarm_8_gap"``
    """

    swarm_id: str = "swarm_8_gap"

    # ── SwarmBase interface ──────────────────────────────────────────────

    def build_messages(
        self,
        question: str,
        rag_results_summary: str,
    ) -> list[dict[str, str]]:
        """Construct the gap-detection prompt.

        Args:
            question:            The user's original question.
            rag_results_summary: A textual summary of the RAG retrieval
                                 results (sources found, confidence
                                 scores, snippet previews).

        Returns:
            Messages list ready for the Groq chat completion API.
        """
        system_prompt = (
            "Determine if the knowledge base adequately addressed this "
            'question. Return JSON: {"has_gap": bool, "gap_type": '
            '"no_sources"|"low_confidence"|"partial_answer"|null, '
            '"suggested_topic": str|null}'
        )
        user_content = (
            f"Question: {question}\n\n"
            f"RAG results summary:\n{rag_results_summary}"
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    def validate_output(self, output: str) -> bool:
        """Verify the LLM returned valid JSON with the ``has_gap`` key.

        Args:
            output: Raw LLM response string.

        Returns:
            ``True`` if the output is valid JSON containing ``"has_gap"``;
            ``False`` otherwise.
        """
        parsed = self._parse_json(output)
        if not isinstance(parsed, dict):
            return False
        return "has_gap" in parsed

    def get_fallback_value(self) -> str:
        """Return a JSON string indicating no gap detected.

        On failure the detector assumes no gap exists so the pipeline
        is not disrupted.

        Returns:
            A JSON string: ``{"has_gap": false}``.
        """
        return json.dumps({"has_gap": False})

    # ── Public convenience method ────────────────────────────────────────

    async def detect(
        self,
        question: str,
        rag_summary: str,
        trace_id: str = "",
    ) -> dict[str, Any]:
        """Detect whether the knowledge base has a gap for a question.

        This is a non-critical operation.  If the swarm fails, the result
        indicates no gap and the failure is silently logged.

        Args:
            question:    The user's original question.
            rag_summary: Summary of RAG retrieval results.
            trace_id:    Correlation identifier for tracing.

        Returns:
            A dict with at least ``"has_gap"`` (bool), and optionally
            ``"gap_type"`` and ``"suggested_topic"``.
        """
        try:
            result = await self.run(question, rag_summary, trace_id=trace_id)
            parsed = self._parse_json(result) if isinstance(result, str) else result
            if isinstance(parsed, dict) and "has_gap" in parsed:
                return parsed
        except Exception as exc:
            logger.warning(
                "Gap detection failed silently: %s",
                str(exc),
                extra={"swarm_id": self.swarm_id, "trace_id": trace_id},
            )

        return {"has_gap": False}
