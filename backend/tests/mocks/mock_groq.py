"""
Deterministic mock Groq client (Decision 19).

Returns fixture responses per swarm — no API calls, fast, deterministic.
Used by all swarm tests. Covers success, empty response, and timeout scenarios.
"""

from unittest.mock import MagicMock, AsyncMock
from dataclasses import dataclass
from typing import Optional


@dataclass
class MockUsage:
    prompt_tokens: int = 50
    completion_tokens: int = 100
    total_tokens: int = 150


@dataclass
class MockChoice:
    message: MagicMock
    finish_reason: str = "stop"


@dataclass
class MockCompletion:
    choices: list
    usage: MockUsage = None

    def __post_init__(self):
        if self.usage is None:
            self.usage = MockUsage()


# ═══════════════════════════════════════════════════
# Per-swarm fixture responses
# ═══════════════════════════════════════════════════

FIXTURE_RESPONSES = {
    "swarm_0_polyglot": "This is the translated text.",
    "swarm_1_gatekeeper": '{"safe": true, "is_fertility_related": true, "category": "nutrition"}',
    "swarm_4_curator": (
        "During IVF stims, focus on protein-rich foods and omega-3 fatty acids. "
        "Studies show that a Mediterranean diet may support follicle development "
        "[ESHRE Guidelines, 2024]. Stay hydrated with 2-3 litres of water daily.\n\n"
        "⚕️ *Always consult your doctor before making dietary changes during treatment.*"
    ),
    "swarm_5_analyser": '{"biomarkers": [{"name": "AMH", "value": 2.1, "status": "normal", "interpretation": "Within expected range for your age group."}]}',
    "swarm_6_bloodwork_curator": "Your AMH level of 2.1 ng/mL is within the normal range. This is a positive indicator for your ovarian reserve.",
    "swarm_7_compliance": None,  # Returns input with disclaimer appended
    "swarm_8_gap": '{"has_gap": false}',
    "swarm_9_context": '{"phase": "STIMS", "day": 8, "treatment": "IVF", "mood": "good", "summary": "User is on day 8 of IVF stims."}',
    "swarm_10_sentiment": '{"sentiment": "hopeful", "intensity": 0.7}',
}


def create_mock_completion(content: str) -> MockCompletion:
    """Create a mock Groq completion response."""
    message = MagicMock()
    message.content = content
    choice = MockChoice(message=message)
    return MockCompletion(choices=[choice])


def create_mock_groq_client(swarm_id: Optional[str] = None):
    """
    Create a mock Groq client.

    If swarm_id is provided, returns the fixture response for that swarm.
    Otherwise, returns a generic response.
    """
    client = MagicMock()

    def mock_create(**kwargs):
        messages = kwargs.get("messages", [])
        # Determine response based on swarm_id or default
        if swarm_id and swarm_id in FIXTURE_RESPONSES:
            content = FIXTURE_RESPONSES[swarm_id]
            if content is None:
                # Compliance checker: return last user message with disclaimer
                last_msg = messages[-1]["content"] if messages else ""
                content = last_msg + "\n\n⚕️ *Always consult your doctor before making medical decisions.*"
        else:
            content = "This is a mock response."
        return create_mock_completion(content)

    client.chat.completions.create = mock_create
    return client


def create_mock_groq_empty():
    """Mock that returns empty responses (for retry/fallback testing)."""
    client = MagicMock()
    message = MagicMock()
    message.content = ""
    choice = MockChoice(message=message)
    client.chat.completions.create = MagicMock(
        return_value=MockCompletion(choices=[choice])
    )
    return client


def create_mock_groq_timeout():
    """Mock that raises timeout (for fallback testing)."""
    client = MagicMock()
    client.chat.completions.create = MagicMock(
        side_effect=TimeoutError("Groq API timeout after 30s")
    )
    return client


def create_mock_groq_rate_limited():
    """Mock that raises rate limit error."""
    client = MagicMock()
    client.chat.completions.create = MagicMock(
        side_effect=Exception("Rate limit exceeded")
    )
    return client
