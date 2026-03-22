"""
Swarm 2 — BloodworkExtractor: Biomarker extraction from OCR text.

Takes raw OCR output from a scanned or photographed lab report and
extracts structured biomarker data (name, value, unit, reference range).

Swarm index: 2
Config key:  ``swarm_2_extractor``
"""

from __future__ import annotations

import json
from typing import Any

from app.core.logging_config import get_logger
from app.core.model_config import SWARM_CONFIG
from app.services.swarm_base import SwarmBase

logger = get_logger(__name__)

# Required keys every biomarker dict must contain.
_REQUIRED_KEYS = {"biomarker", "value", "unit"}


class BloodworkExtractor(SwarmBase):
    """Extract structured biomarker data from lab-report OCR text.

    The LLM is prompted to return a JSON array of biomarker objects,
    each containing:

    - ``biomarker`` (str): Name of the biomarker (e.g. ``"AMH"``,
      ``"TSH"``, ``"Vitamin D"``).
    - ``value`` (float): The numeric measurement value.
    - ``unit`` (str): The unit of measurement (e.g. ``"ng/mL"``,
      ``"mIU/L"``).
    - ``ref_min`` (float | null): Lower bound of the reference range,
      or ``null`` if not provided on the report.
    - ``ref_max`` (float | null): Upper bound of the reference range,
      or ``null`` if not provided on the report.

    Attributes:
        swarm_id: ``"swarm_2_extractor"``
    """

    swarm_id: str = "swarm_2_extractor"

    # ── SwarmBase interface ─────────────────────────────────────────────

    def build_messages(
        self,
        ocr_text: str,
        gender: str = "female",
    ) -> list[dict[str, str]]:
        """Build extraction prompt messages.

        Args:
            ocr_text: Raw OCR text from the lab report image or PDF.
            gender:   Patient gender, used to contextualise reference
                      ranges (default ``"female"``).

        Returns:
            A messages list for the Groq chat completion API.
        """
        return [
            {
                "role": "system",
                "content": (
                    "Extract all biomarker values from this lab report text. "
                    f"The patient is {gender}. "
                    "Return a JSON array where each element is an object with "
                    "these keys:\n\n"
                    '  "biomarker" (string) — the biomarker name.\n'
                    '  "value" (number) — the numeric result.\n'
                    '  "unit" (string) — the unit of measurement.\n'
                    '  "ref_min" (number or null) — lower reference range '
                    "bound, or null if not listed.\n"
                    '  "ref_max" (number or null) — upper reference range '
                    "bound, or null if not listed.\n\n"
                    "Return ONLY the JSON array. No explanation, no markdown."
                ),
            },
            {
                "role": "user",
                "content": ocr_text,
            },
        ]

    def validate_output(self, output: str) -> bool:
        """Validate that the output is a JSON array of biomarker dicts.

        Args:
            output: Raw LLM response content.

        Returns:
            ``True`` when *output* parses as a JSON list and every
            element contains the required keys ``biomarker``, ``value``,
            and ``unit``.
        """
        parsed = self._parse_json(output)
        if not isinstance(parsed, list):
            return False
        if len(parsed) == 0:
            # An empty array is technically valid JSON but likely means
            # the LLM couldn't extract anything — still accept it since
            # the report may genuinely have no recognisable biomarkers.
            return True
        return all(
            isinstance(item, dict) and _REQUIRED_KEYS.issubset(item.keys())
            for item in parsed
        )

    def get_fallback_value(self) -> list[dict[str, Any]]:
        """Return an empty list when extraction fails.

        An empty list signals to the caller that no biomarkers could be
        extracted, which is safe — the user can be prompted to re-upload
        a clearer image.
        """
        return []

    # ── Convenience method ──────────────────────────────────────────────

    async def extract(
        self,
        ocr_text: str,
        gender: str = "female",
        trace_id: str = "",
    ) -> list[dict[str, Any]]:
        """Extract biomarker values from OCR text.

        This is the primary public API for the BloodworkExtractor swarm.

        Args:
            ocr_text: Raw OCR text from a lab report.
            gender:   Patient gender for reference-range context.
            trace_id: Optional trace identifier for logging.

        Returns:
            A list of biomarker dicts, or an empty list on failure.
        """
        result = await self.run(ocr_text, gender, trace_id=trace_id)

        # If run() returned the fallback list directly, use it.
        if isinstance(result, list):
            return result

        # Otherwise parse the LLM string output.
        parsed = self._parse_json(str(result))
        if isinstance(parsed, list):
            return parsed

        logger.warning(
            "BloodworkExtractor could not parse LLM output, using fallback",
            extra={"swarm_id": self.swarm_id, "trace_id": trace_id},
        )
        return []
