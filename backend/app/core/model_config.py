"""
LLM model registry for the Izana swarm architecture.

Each swarm agent has a dedicated configuration entry that specifies the model,
generation parameters, timeout budget, and (where applicable) a fallback model
to try when the primary model is rate-limited or unavailable.

Swarm index reference
---------------------
0  Polyglot         – Language detection & translation
1  Gatekeeper       – Intent classification / routing
2  Extractor        – Biomarker extraction from lab reports
3  Clinical Brain   – RAG retrieval over medical knowledge base
4  Curator          – Personalised response composition
5  Analyser         – Bloodwork & biomarker analysis
6  Bloodwork Curator – Bloodwork report formatting
7  Compliance       – Medical-disclaimer & safety guardrails
8  Gap              – Follow-up question detection
9  Context          – Conversation context summarisation
10 Sentiment        – Mood / emotional-tone detection
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Primary model identifiers
# ---------------------------------------------------------------------------

MODEL_LLAMA_70B = "llama-3.3-70b-versatile"
MODEL_LLAMA_70B_V1 = "llama-3.1-70b-versatile"
MODEL_LLAMA_8B = "llama-3.1-8b-instant"
MODEL_EMBEDDING = "text-embedding-3-small"

# ---------------------------------------------------------------------------
# Swarm configuration
# ---------------------------------------------------------------------------

SWARM_CONFIG: dict[str, dict[str, Any]] = {
    "swarm_0_polyglot": {
        "model": MODEL_LLAMA_70B,
        "temperature": 0.1,
        "max_tokens": 2000,
        "timeout_seconds": 15,
        "fallback_model": MODEL_LLAMA_8B,
    },
    "swarm_1_gatekeeper": {
        "model": MODEL_LLAMA_70B,
        "temperature": 0.0,
        "max_tokens": 200,
        "timeout_seconds": 10,
        "fallback_model": MODEL_LLAMA_8B,
    },
    "swarm_2_extractor": {
        "model": MODEL_LLAMA_70B,
        "temperature": 0.1,
        "max_tokens": 3000,
        "timeout_seconds": 25,
        "fallback_model": MODEL_LLAMA_8B,
    },
    "swarm_3_clinical_brain": {
        "embedding_model": MODEL_EMBEDDING,
        "embedding_dimensions": 384,
        "match_threshold": 0.5,
        "match_count": 10,
        "multi_query_count": 3,
    },
    "swarm_4_curator": {
        "model": MODEL_LLAMA_70B,
        "temperature": 0.4,
        "max_tokens": 1500,
        "timeout_seconds": 30,
        "fallback_model": MODEL_LLAMA_70B_V1,
    },
    "swarm_5_analyser": {
        "model": MODEL_LLAMA_70B,
        "temperature": 0.2,
        "max_tokens": 2000,
        "timeout_seconds": 20,
    },
    "swarm_6_bloodwork_curator": {
        "model": MODEL_LLAMA_70B,
        "temperature": 0.3,
        "max_tokens": 2000,
        "timeout_seconds": 20,
    },
    "swarm_7_compliance": {
        "model": MODEL_LLAMA_8B,
        "temperature": 0.0,
        "max_tokens": 500,
        "timeout_seconds": 10,
    },
    "swarm_8_gap": {
        "model": MODEL_LLAMA_8B,
        "temperature": 0.0,
        "max_tokens": 200,
        "timeout_seconds": 10,
    },
    "swarm_9_context": {
        "model": MODEL_LLAMA_8B,
        "temperature": 0.1,
        "max_tokens": 300,
        "timeout_seconds": 10,
    },
    "swarm_10_sentiment": {
        "model": MODEL_LLAMA_8B,
        "temperature": 0.0,
        "max_tokens": 100,
        "timeout_seconds": 8,
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_swarm_config(swarm_name: str) -> dict[str, Any]:
    """Return the configuration dict for a given swarm agent.

    Raises ``KeyError`` if *swarm_name* is not registered.
    """
    return SWARM_CONFIG[swarm_name]


def get_model(swarm_name: str) -> str:
    """Return the primary model identifier for a swarm agent."""
    cfg = get_swarm_config(swarm_name)
    return cfg.get("model") or cfg.get("embedding_model", "")


def get_fallback_model(swarm_name: str) -> str | None:
    """Return the fallback model for a swarm agent, or ``None`` if none is configured."""
    return get_swarm_config(swarm_name).get("fallback_model")


def get_timeout(swarm_name: str) -> int:
    """Return the timeout in seconds for a swarm agent, defaulting to 30s."""
    return get_swarm_config(swarm_name).get("timeout_seconds", 30)
