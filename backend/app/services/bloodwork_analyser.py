"""
Swarm 5 \u2014 BloodworkAnalyser: Biomarker interpretation agent.

Interprets biomarker values against clinical reference ranges and returns
structured JSON indicating whether each value is normal, high, or low,
along with an interpretation and fertility relevance note.

This swarm is typically called after OCR extraction of a lab report.
The output feeds into Swarm 6 (Bloodwork Curator) for patient-friendly
formatting.

Swarm index: 5
Config key:  ``swarm_5_analyser``
"""

from __future__ import annotations

import json
from typing import Any

from app.core.logging_config import get_logger
from app.core.model_config import SWARM_CONFIG
from app.services.swarm_base import SwarmBase

logger = get_logger(__name__)

_REQUIRED_KEYS = {"biomarker", "value", "status", "interpretation", "fertility_relevance"}


class BloodworkAnalyser(SwarmBase):
    """Interpret biomarker results against fertility reference ranges.

    Each biomarker is classified as ``"normal"``, ``"high"``, or ``"low"``
    with a clinical interpretation and fertility-relevance explanation.

    Attributes:
        swarm_id: ``"swarm_5_analyser"``
    """

    swarm_id: str = "swarm_5_analyser"

    # ── SwarmBase interface ──────────────────────────────────────────────

    def build_messages(
        self,
        biomarkers: list[dict[str, Any]],
        gender: str,
        age_range: str,
    ) -> list[dict[str, str]]:
        """Construct the prompt for biomarker interpretation.

        Args:
            biomarkers: List of dicts, each containing at minimum
                        ``{"name": str, "value": float, "unit": str}``.
            gender:     Patient gender (e.g. ``"female"``, ``"male"``).
            age_range:  Age bracket string (e.g. ``"25-34"``).

        Returns:
            Messages list ready for the Groq chat completion API.
        """
        system_prompt = (
            f"You are a clinical lab analyst. Interpret these biomarker results "
            f"for a {gender} patient aged {age_range}. For each biomarker, "
            f"indicate if the value is normal/high/low relative to fertility "
            f"reference ranges, and explain the clinical significance. "
            f'Return JSON: [{{"biomarker": str, "value": float, '
            f'"status": "normal"|"high"|"low", "interpretation": str, '
            f'"fertility_relevance": str}}]'
        )
        user_content = json.dumps(biomarkers, default=str)
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    def validate_output(self, output: str) -> bool:
        """Verify the LLM returned a JSON list with required keys.

        Args:
            output: Raw LLM response string.

        Returns:
            ``True`` if the output is a valid JSON list where every item
            contains the required keys; ``False`` otherwise.
        """
        parsed = self._parse_json(output)
        if not isinstance(parsed, list):
            return False
        if len(parsed) == 0:
            return False
        for item in parsed:
            if not isinstance(item, dict):
                return False
            if not _REQUIRED_KEYS.issubset(item.keys()):
                return False
        return True

    def get_fallback_value(self) -> str:
        """Return a safe fallback message advising medical review.

        Returns:
            A string recommending the user consult their doctor.
        """
        return (
            "Your biomarker values have been recorded but could not be "
            "fully interpreted at this time. Please share these results "
            "with your doctor for a complete clinical review."
        )

    # ── Public convenience method ────────────────────────────────────────

    async def analyse(
        self,
        biomarkers: list[dict[str, Any]],
        gender: str,
        age_range: str,
        trace_id: str = "",
    ) -> list[dict[str, Any]]:
        """Analyse biomarker values and return structured interpretations.

        Args:
            biomarkers: List of biomarker dicts from the OCR/extraction step.
            gender:     Patient gender.
            age_range:  Patient age bracket.
            trace_id:   Correlation identifier for tracing.

        Returns:
            A list of dicts with keys ``biomarker``, ``value``, ``status``,
            ``interpretation``, and ``fertility_relevance``.  On failure,
            returns the fallback string wrapped in a single-item list with
            ``interpretation`` set to the fallback message.
        """
        result = await self.run(biomarkers, gender, age_range, trace_id=trace_id)

        # run() returns the raw string on success, fallback string on failure.
        if isinstance(result, str):
            parsed = self._parse_json(result)
            if isinstance(parsed, list):
                return parsed
            # If parsing fails here, return a structured fallback.
            return [{"biomarker": "unknown", "value": 0, "status": "unknown",
                     "interpretation": result, "fertility_relevance": ""}]

        return result
