"""
Swarm 0 — Polyglot: Language translation agent.

Translates user input between languages so that downstream swarms always
operate on English text, and the final response can be translated back
to the user's preferred language.

Swarm index: 0
Config key:  ``swarm_0_polyglot``
"""

from __future__ import annotations

from typing import Any

from app.core.logging_config import get_logger
from app.core.model_config import SWARM_CONFIG
from app.services.swarm_base import SwarmBase

logger = get_logger(__name__)


class Translator(SwarmBase):
    """Translate text between a source and target language via LLM.

    The translation prompt instructs the model to return *only* the
    translated text with no preamble, explanation, or formatting so
    that the output can be used directly by other swarms or sent
    to the user.

    Attributes:
        swarm_id: ``"swarm_0_polyglot"``
    """

    swarm_id: str = "swarm_0_polyglot"

    def __init__(self) -> None:
        super().__init__()
        self._original_text: str = ""

    # ── SwarmBase interface ─────────────────────────────────────────────

    def build_messages(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> list[dict[str, str]]:
        """Build the prompt messages for a translation request.

        Args:
            text:        The text to translate.
            source_lang: ISO language name or code of the source language
                         (e.g. ``"Spanish"``, ``"fr"``).
            target_lang: ISO language name or code of the target language
                         (e.g. ``"English"``, ``"en"``).

        Returns:
            A messages list suitable for the Groq chat completion API.
        """
        self._original_text = text
        return [
            {
                "role": "system",
                "content": (
                    f"You are a translator. Translate the following text "
                    f"from {source_lang} to {target_lang}. "
                    f"Return ONLY the translated text, nothing else."
                ),
            },
            {
                "role": "user",
                "content": text,
            },
        ]

    def validate_output(self, output: str) -> bool:
        """Return ``True`` if the output is a non-empty string.

        Args:
            output: Raw LLM response content.

        Returns:
            ``True`` when *output* contains at least one non-whitespace
            character.
        """
        return bool(output and output.strip())

    def get_fallback_value(self) -> str:
        """Return the original input text untranslated.

        When the LLM fails, passing through the original text is safer
        than returning nothing — downstream swarms can still attempt to
        process it.
        """
        return self._original_text

    # ── Convenience method ──────────────────────────────────────────────

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        trace_id: str = "",
    ) -> str:
        """Translate *text* from *source_lang* to *target_lang*.

        This is the primary public API for the Polyglot swarm.  It
        delegates to :meth:`SwarmBase.run` and ensures the return type
        is always ``str``.

        Args:
            text:        The text to translate.
            source_lang: Source language name or code.
            target_lang: Target language name or code.
            trace_id:    Optional trace identifier for logging.

        Returns:
            The translated text, or the original text on failure.
        """
        result = await self.run(text, source_lang, target_lang, trace_id=trace_id)
        return str(result).strip()
