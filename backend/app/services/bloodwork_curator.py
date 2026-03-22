"""
Swarm 6 \u2014 BloodworkCurator: Patient-friendly bloodwork formatting agent.

Converts clinical biomarker analysis (from Swarm 5) into warm,
patient-friendly language.  The output avoids jargon, uses second-person
voice ("your"), and ends with a recommendation to discuss results with
a doctor.  No specific dosage advice is given.

Swarm index: 6
Config key:  ``swarm_6_bloodwork_curator``
"""

from __future__ import annotations

import json
from typing import Any

from app.core.logging_config import get_logger
from app.core.model_config import SWARM_CONFIG
from app.services.swarm_base import SwarmBase

logger = get_logger(__name__)

_FALLBACK_MESSAGE = (
    "Your bloodwork results have been recorded. Please discuss the "
    "details with your doctor for a full interpretation."
)


class BloodworkCurator(SwarmBase):
    """Format clinical bloodwork analysis for patient consumption.

    Takes the structured JSON output from :class:`BloodworkAnalyser` and
    rewrites it as a conversational, empathetic explanation suitable for
    the Izana Chat UI.

    Attributes:
        swarm_id: ``"swarm_6_bloodwork_curator"``
    """

    swarm_id: str = "swarm_6_bloodwork_curator"

    # ── SwarmBase interface ──────────────────────────────────────────────

    def build_messages(
        self,
        analysis_json: list[dict[str, Any]] | str,
        user_context: str,
    ) -> list[dict[str, str]]:
        """Construct the prompt for patient-friendly formatting.

        Args:
            analysis_json: Structured analysis from Swarm 5, either as a
                           parsed list or a JSON string.
            user_context:  Additional context about the user (treatment
                           type, phase, etc.) to personalise the response.

        Returns:
            Messages list ready for the Groq chat completion API.
        """
        system_prompt = (
            "Convert this clinical analysis into warm, patient-friendly "
            "language. Use 'your' not 'the patient's'. Explain what each "
            "result means for fertility in simple terms. Do NOT give "
            "specific dosage advice. End with a recommendation to discuss "
            "with their doctor."
        )
        # Normalise analysis_json to a string for the user message.
        if not isinstance(analysis_json, str):
            analysis_str = json.dumps(analysis_json, default=str)
        else:
            analysis_str = analysis_json

        user_content = (
            f"Analysis:\n{analysis_str}\n\nUser context:\n{user_context}"
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    def validate_output(self, output: str) -> bool:
        """Verify the response is a non-empty string of sufficient length.

        The response must be at least 50 characters to be considered a
        meaningful patient-friendly explanation rather than a stub.

        Args:
            output: Raw LLM response string.

        Returns:
            ``True`` if the output is a non-empty string longer than 50
            characters; ``False`` otherwise.
        """
        return isinstance(output, str) and len(output.strip()) > 50

    def get_fallback_value(self) -> str:
        """Return a safe fallback message for the patient.

        Returns:
            A generic message acknowledging the bloodwork and advising
            the user to consult their doctor.
        """
        return _FALLBACK_MESSAGE

    # ── Public convenience method ────────────────────────────────────────

    async def format_for_patient(
        self,
        analysis_json: list[dict[str, Any]] | str,
        user_context: str,
        trace_id: str = "",
    ) -> str:
        """Format bloodwork analysis as a patient-friendly explanation.

        Args:
            analysis_json: Structured analysis output from Swarm 5.
            user_context:  Contextual information about the user.
            trace_id:      Correlation identifier for tracing.

        Returns:
            A warm, readable string explaining the bloodwork results,
            or the fallback message on failure.
        """
        result = await self.run(analysis_json, user_context, trace_id=trace_id)
        return str(result)
