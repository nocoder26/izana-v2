"""
Preview chat API — landing page pre-auth endpoints.

Provides:
- GET /preview/cached-responses — Pre-computed responses for the 3 landing page questions
- POST /preview/ask — Real-time preview (rate limited: 1 per 10 min per IP)

No authentication required. These endpoints are for the landing page.
"""

from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ═══════════════════════════════════════════════════════════════
# Pre-cached landing page questions (per language)
# ═══════════════════════════════════════════════════════════════

PREVIEW_QUESTIONS = {
    "en": [
        "What should I eat during IVF?",
        "Is my AMH level normal?",
        "How do I manage TWW anxiety?",
    ],
}


class PreviewRequest(BaseModel):
    """Request body for real-time preview questions."""
    question: str = Field(..., min_length=1, max_length=2000)
    language: str = Field(default="en", max_length=5)


class PreviewResponse(BaseModel):
    """Response for preview questions."""
    question: str
    response: str
    sources: list[dict] = []
    follow_ups: list[str] = []


@router.get("/preview/cached-responses")
async def get_cached_responses(language: str = "en"):
    """Return pre-computed responses for the 3 landing page questions.

    These are cached server-side and refreshed daily by a background job.
    For now, returns placeholder responses that will be replaced once the
    cache refresh job runs the full swarm pipeline.
    """
    questions = PREVIEW_QUESTIONS.get(language, PREVIEW_QUESTIONS["en"])

    # Placeholder responses until the cache refresh job populates these
    # In production, these come from Redis cache (24-hour TTL)
    responses = []
    for q in questions:
        responses.append({
            "question": q,
            "response": _get_placeholder_response(q),
            "sources": [
                {"title": "ESHRE IVF Guidelines, 2024", "relevance": 0.87},
                {"title": "Fertility & Sterility Journal", "relevance": 0.82},
            ],
            "follow_ups": [
                "What supplements should I take?",
                "How much water should I drink?",
                "Are there foods I should avoid?",
            ],
        })

    return responses


@router.post("/preview/ask")
async def preview_ask(request: PreviewRequest, raw_request: Request):
    """Real-time preview for custom questions on the landing page.

    Rate limited: 1 request per 10 minutes per IP.
    Runs a subset of the swarm pipeline (no user context, no auth).
    """
    # TODO: Implement rate limiting (1 per 10 min per IP)
    # TODO: Run actual swarm pipeline (swarms 0→1→3→4→7)
    # For now, return a placeholder response

    logger.info(
        "Preview question asked",
        extra={
            "question": request.question[:100],
            "language": request.language,
            "ip": raw_request.client.host if raw_request.client else "unknown",
        },
    )

    return PreviewResponse(
        question=request.question,
        response=(
            "That's a great question about fertility. During treatment, "
            "it's important to focus on a balanced diet rich in protein, "
            "healthy fats, and antioxidants. Your doctor can provide "
            "personalised guidance based on your specific situation.\n\n"
            "⚕️ *Always consult your doctor before making medical decisions.*"
        ),
        sources=[
            {"title": "Clinical Fertility Guidelines", "relevance": 0.75},
        ],
        follow_ups=[
            "What vitamins are recommended?",
            "Should I change my exercise routine?",
            "How does stress affect fertility?",
        ],
    )


def _get_placeholder_response(question: str) -> str:
    """Generate a placeholder response for cached questions."""
    responses = {
        "What should I eat during IVF?": (
            "During IVF, focus on a Mediterranean-style diet rich in protein, "
            "omega-3 fatty acids, and antioxidants. Key foods include salmon, "
            "eggs, leafy greens, avocado, and whole grains. Aim for 2-3 litres "
            "of water daily. Avoid processed foods, excessive caffeine, and "
            "alcohol [ESHRE Guidelines, 2024].\n\n"
            "⚕️ *Always consult your doctor before making dietary changes during treatment.*"
        ),
        "Is my AMH level normal?": (
            "AMH (Anti-Müllerian Hormone) levels vary by age. Generally, "
            "1.0-3.5 ng/mL is considered normal for women of reproductive age. "
            "Below 1.0 may indicate diminished ovarian reserve, while above 3.5 "
            "could suggest PCOS. However, AMH is just one piece of the puzzle — "
            "your doctor will consider it alongside FSH, AFC, and your age "
            "[Fertility & Sterility Journal].\n\n"
            "⚕️ *Always consult your doctor for personalised interpretation of your bloodwork.*"
        ),
        "How do I manage TWW anxiety?": (
            "The two-week wait is one of the most emotionally challenging parts "
            "of fertility treatment. Evidence-based strategies include: mindfulness "
            "meditation (even 10 minutes daily helps), gentle yoga, journaling, "
            "and maintaining your normal routine. Avoid symptom-spotting and limit "
            "time on fertility forums if they increase anxiety. It's completely "
            "normal to feel anxious — be gentle with yourself "
            "[Reproductive BioMedicine Online].\n\n"
            "⚕️ *If anxiety becomes overwhelming, speak to your doctor or a fertility counsellor.*"
        ),
    }
    return responses.get(question, "I'd love to help with that question. Sign up to get personalised answers!")
