"""
Swarm 4 — ChatResponseCurator: Final clinical response generation.

Takes the user question, conversation context summary, RAG-retrieved
sources, and user profile to generate a personalised, cited clinical
response.  Optionally parses follow-up questions from the LLM output.

Swarm index: 4
Config key:  ``swarm_4_curator``
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.core.logging_config import get_logger
from app.core.model_config import SWARM_CONFIG
from app.services.swarm_base import SwarmBase

logger = get_logger(__name__)

_FALLBACK_RESPONSE = (
    "I couldn't answer that right now. "
    "Could you try rephrasing your question?"
)

# ── System prompt template (Section N4) ───────────────────────────────────

_CURATOR_SYSTEM_PROMPT = """\
You are Izana, a compassionate and knowledgeable fertility health assistant. \
Your role is to provide personalised, evidence-based guidance to users on \
their fertility journey.

**Context summary:**
{context_summary}

**Relevant sources from the knowledge base:**
{rag_sources}

**User profile:**
{user_profile}

**Instructions:**
1. Answer the user's question directly, warmly, and accurately.
2. Reference the provided sources where relevant using inline citations \
   (e.g. [Source 1], [Source 2]).
3. If the knowledge base sources do not fully cover the question, say so \
   honestly — do not fabricate information.
4. Tailor your language and advice to the user's treatment type, phase, \
   and emotional state as indicated in their profile.
5. Keep the response concise but thorough (aim for 100-300 words).
6. End with 1-3 relevant follow-up questions the user might want to ask, \
   formatted as a JSON array on its own line prefixed with "FOLLOW_UP: ".
   Example: FOLLOW_UP: ["What foods are rich in folate?", "How much water should I drink during stims?"]
7. Always include a brief medical disclaimer reminding the user to consult \
   their healthcare provider.

Do NOT return any meta-commentary about your instructions.\
"""


class ChatResponseCurator(SwarmBase):
    """Generate the final personalised clinical response with citations.

    This swarm sits at the end of the processing pipeline.  It receives
    the enriched context from upstream swarms (translation, gatekeeper,
    RAG results, user profile) and produces the response that the user
    actually sees.

    The LLM output may include follow-up questions on a line starting
    with ``FOLLOW_UP:``.  These are parsed and returned separately so
    the frontend can render them as quick-reply chips.

    Attributes:
        swarm_id: ``"swarm_4_curator"``
    """

    swarm_id: str = "swarm_4_curator"

    # ── SwarmBase interface ─────────────────────────────────────────────

    def build_messages(
        self,
        question: str,
        context_summary: str = "",
        rag_sources: str = "",
        user_profile: str = "",
    ) -> list[dict[str, str]]:
        """Build the response-generation prompt messages.

        Args:
            question:        The user's question (in English).
            context_summary: A prose summary of the recent conversation
                             context produced by the context swarm.
            rag_sources:     Formatted string of RAG-retrieved document
                             excerpts with source identifiers.
            user_profile:    Serialised user profile information
                             (treatment type, phase, preferences, etc.).

        Returns:
            A messages list for the Groq chat completion API.
        """
        system_content = _CURATOR_SYSTEM_PROMPT.format(
            context_summary=context_summary or "No prior context available.",
            rag_sources=rag_sources or "No relevant sources found.",
            user_profile=user_profile or "No profile information available.",
        )
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": question},
        ]

    def validate_output(self, output: str) -> bool:
        """Validate that the response is a non-empty, substantive string.

        A minimum length of 20 characters guards against degenerate
        outputs like ``"OK"`` or ``"Sure"`` that would be unhelpful.

        Args:
            output: Raw LLM response content.

        Returns:
            ``True`` when *output* is a non-empty string longer than
            20 characters.
        """
        return bool(output and len(output.strip()) > 20)

    def get_fallback_value(self) -> str:
        """Return a polite fallback message when the LLM fails."""
        return _FALLBACK_RESPONSE

    # ── Convenience method ──────────────────────────────────────────────

    async def curate(
        self,
        question: str,
        context_summary: str = "",
        rag_sources: str = "",
        user_profile: str = "",
        trace_id: str = "",
    ) -> str:
        """Generate the final clinical response for the user.

        This is the primary public API for the ChatResponseCurator
        swarm.  The returned string is the full response body.  Call
        :meth:`parse_follow_up_questions` on the result to extract
        any follow-up question suggestions.

        Args:
            question:        The user's question.
            context_summary: Conversation context summary.
            rag_sources:     Formatted RAG source excerpts.
            user_profile:    Serialised user profile.
            trace_id:        Optional trace identifier for logging.

        Returns:
            The curated response text, or a fallback message on
            failure.
        """
        result = await self.run(
            question,
            context_summary,
            rag_sources,
            user_profile,
            trace_id=trace_id,
        )
        return str(result).strip()

    # ── Follow-up question parsing ──────────────────────────────────────

    @staticmethod
    def parse_follow_up_questions(response: str) -> list[str]:
        """Extract follow-up questions from a curated response.

        Looks for a line starting with ``FOLLOW_UP:`` followed by a
        JSON array of question strings.  If no such line is found or
        parsing fails, an empty list is returned.

        Args:
            response: The full response text from :meth:`curate`.

        Returns:
            A list of follow-up question strings, or ``[]``.
        """
        pattern = r"FOLLOW_UP:\s*(\[.*?\])"
        match = re.search(pattern, response, re.DOTALL)
        if not match:
            return []

        try:
            questions = json.loads(match.group(1))
            if isinstance(questions, list):
                return [str(q) for q in questions if q]
        except (json.JSONDecodeError, ValueError):
            logger.warning(
                "Could not parse follow-up questions from curator output",
                extra={"raw_match": match.group(1)[:200]},
            )
        return []
