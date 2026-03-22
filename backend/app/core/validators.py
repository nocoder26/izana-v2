"""
Input sanitization, PII detection, and greeting classification utilities.

These run early in the request pipeline — before any message reaches the
swarm agents — to enforce Decision 16 (2 000-char input cap) and to prevent
accidental PII from being persisted or forwarded to third-party LLMs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import bleach

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_INPUT_LENGTH = 2000  # Decision 16

# Greetings list — lowercase, no punctuation
_GREETINGS: set[str] = {
    "hello",
    "hi",
    "hey",
    "hiya",
    "howdy",
    "yo",
    "hola",
    "bonjour",
    "namaste",
    "good morning",
    "good afternoon",
    "good evening",
    "good day",
    "morning",
    "evening",
    "afternoon",
    "gm",
    "whats up",
    "what's up",
    "sup",
    "heya",
    "greetings",
    "salutations",
}

# ---------------------------------------------------------------------------
# PII regex patterns
# ---------------------------------------------------------------------------

_PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "phone_number": re.compile(
        r"""
        (?<!\d)                      # no leading digit
        (?:
            \+?\d{1,3}[\s.-]?        # optional country code
        )?
        \(?\d{2,4}\)?[\s.-]?         # area code
        \d{3,4}[\s.-]?               # first group
        \d{3,4}                      # second group
        (?!\d)                       # no trailing digit
        """,
        re.VERBOSE,
    ),
    "ssn": re.compile(
        r"\b\d{3}-\d{2}-\d{4}\b"
    ),
    "email": re.compile(
        r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
    ),
    "credit_card": re.compile(
        r"""
        \b
        (?:
            4\d{3}|                  # Visa
            5[1-5]\d{2}|             # Mastercard
            3[47]\d{2}|              # Amex
            6(?:011|5\d{2})          # Discover
        )
        [\s.-]?
        \d{4}[\s.-]?
        \d{4}[\s.-]?
        \d{3,4}
        \b
        """,
        re.VERBOSE,
    ),
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PiiResult:
    """Result of a PII scan on user input.

    Attributes:
        has_pii:   True if any PII pattern was detected.
        pii_types: List of PII category names that matched (e.g. ``["email", "phone_number"]``).
    """

    has_pii: bool
    pii_types: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def sanitize_input(text: str) -> str:
    """Sanitize raw user input before any downstream processing.

    Steps performed:
    1. Strip leading / trailing whitespace.
    2. Remove all HTML tags via *bleach* (Decision 16 — no markup in chat).
    3. Truncate to ``MAX_INPUT_LENGTH`` characters.

    Args:
        text: The raw input string.

    Returns:
        The cleaned, length-limited string.
    """
    text = text.strip()
    text = bleach.clean(text, tags=[], strip=True)
    text = text[:MAX_INPUT_LENGTH]
    return text


def check_for_pii(text: str) -> PiiResult:
    """Scan *text* for common PII patterns.

    Detected categories:
    - ``phone_number``
    - ``ssn``
    - ``email``
    - ``credit_card``

    Args:
        text: The string to scan (ideally already sanitized).

    Returns:
        A ``PiiResult`` indicating whether PII was found and which types.
    """
    detected: list[str] = []
    for pii_type, pattern in _PII_PATTERNS.items():
        if pattern.search(text):
            detected.append(pii_type)
    return PiiResult(has_pii=bool(detected), pii_types=detected)


def is_greeting(text: str) -> bool:
    """Determine whether *text* is a simple greeting with no substantive question.

    Comparison is case-insensitive and ignores trailing punctuation / emoji so
    that ``"Hello!"`` and ``"Hey 👋"`` both return ``True``.

    Args:
        text: The user message (ideally already sanitized).

    Returns:
        ``True`` if the message is a standalone greeting.
    """
    # Normalise: lowercase, strip punctuation and common emoji
    cleaned = re.sub(r"[^\w\s']", "", text.lower()).strip()
    return cleaned in _GREETINGS
