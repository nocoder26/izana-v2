"""
OCR via Groq Vision with OpenAI Vision fallback.

Extracts text from bloodwork images (photos of lab reports) using
multimodal LLM vision capabilities.  The flow is:

1. Try Groq Vision (fast, cost-effective).
2. If Groq fails or is unavailable, fall back to OpenAI Vision.
3. If both fail, raise :class:`AllOCRFailedError`.

This module is designed to handle JPG, PNG, and HEIC image formats.
"""

from __future__ import annotations

import base64
from typing import Any

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Groq vision model -- meta-llama with vision support
_GROQ_VISION_MODEL = "llama-3.2-90b-vision-preview"

# OpenAI vision model
_OPENAI_VISION_MODEL = "gpt-4o-mini"

_OCR_SYSTEM_PROMPT = (
    "You are an expert OCR system specialised in medical lab reports. "
    "Extract ALL text from this image exactly as it appears, preserving "
    "the layout as much as possible. Include all biomarker names, values, "
    "units, and reference ranges. Do not interpret or summarise -- just "
    "reproduce the text verbatim."
)


class AllOCRFailedError(Exception):
    """Raised when all OCR providers (Groq Vision + OpenAI Vision) fail."""


def _encode_image_base64(file_bytes: bytes) -> str:
    """Encode raw image bytes to a base64 data URI string.

    Args:
        file_bytes: Raw image bytes.

    Returns:
        A base64-encoded string suitable for multimodal LLM APIs.
    """
    return base64.b64encode(file_bytes).decode("utf-8")


def _guess_media_type(filename: str) -> str:
    """Guess the MIME type from a filename extension.

    Args:
        filename: Original filename.

    Returns:
        A MIME type string (defaults to ``image/jpeg`` for unknown types).
    """
    lower = filename.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".heic"):
        return "image/heic"
    if lower.endswith(".webp"):
        return "image/webp"
    return "image/jpeg"


async def _try_groq_vision(
    file_bytes: bytes,
    filename: str,
) -> str | None:
    """Attempt OCR via Groq Vision API.

    Args:
        file_bytes: Raw image bytes.
        filename:   Original filename (for MIME type detection).

    Returns:
        Extracted text on success, or ``None`` if Groq is unavailable or
        the call fails.
    """
    if not settings.GROQ_API_KEY:
        logger.debug("Groq API key not configured, skipping Groq Vision")
        return None

    try:
        from groq import AsyncGroq

        client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        b64 = _encode_image_base64(file_bytes)
        media_type = _guess_media_type(filename)

        response = await client.chat.completions.create(
            model=_GROQ_VISION_MODEL,
            messages=[
                {"role": "system", "content": _OCR_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{b64}",
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Extract all text from this lab report image. "
                                "Include every biomarker, value, unit, and "
                                "reference range you can see."
                            ),
                        },
                    ],
                },
            ],
            temperature=0.1,
            max_tokens=4096,
        )

        content = response.choices[0].message.content
        if content and content.strip():
            logger.info(
                "Groq Vision OCR succeeded",
                extra={"text_length": len(content)},
            )
            return content.strip()

        logger.warning("Groq Vision returned empty content")
        return None

    except Exception as exc:
        logger.warning(
            "Groq Vision OCR failed: %s",
            exc,
            extra={"error_type": type(exc).__name__},
        )
        return None


async def _try_openai_vision(
    file_bytes: bytes,
    filename: str,
) -> str | None:
    """Attempt OCR via OpenAI Vision API.

    Args:
        file_bytes: Raw image bytes.
        filename:   Original filename (for MIME type detection).

    Returns:
        Extracted text on success, or ``None`` if OpenAI is unavailable
        or the call fails.
    """
    if not settings.OPENAI_API_KEY:
        logger.debug("OpenAI API key not configured, skipping OpenAI Vision")
        return None

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        b64 = _encode_image_base64(file_bytes)
        media_type = _guess_media_type(filename)

        response = await client.chat.completions.create(
            model=_OPENAI_VISION_MODEL,
            messages=[
                {"role": "system", "content": _OCR_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{b64}",
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Extract all text from this lab report image. "
                                "Include every biomarker, value, unit, and "
                                "reference range you can see."
                            ),
                        },
                    ],
                },
            ],
            temperature=0.1,
            max_tokens=4096,
        )

        content = response.choices[0].message.content
        if content and content.strip():
            logger.info(
                "OpenAI Vision OCR succeeded",
                extra={"text_length": len(content)},
            )
            return content.strip()

        logger.warning("OpenAI Vision returned empty content")
        return None

    except Exception as exc:
        logger.warning(
            "OpenAI Vision OCR failed: %s",
            exc,
            extra={"error_type": type(exc).__name__},
        )
        return None


async def extract_text_from_image_vision(
    file_bytes: bytes,
    filename: str,
) -> str:
    """Extract text from a lab-report image using vision LLM APIs.

    Tries Groq Vision first for speed, then falls back to OpenAI Vision.
    Raises :class:`AllOCRFailedError` if neither provider succeeds.

    Args:
        file_bytes: Raw image bytes (JPG, PNG, HEIC).
        filename:   Original filename (for MIME type detection).

    Returns:
        The extracted text from the image.

    Raises:
        AllOCRFailedError: If both Groq and OpenAI vision APIs fail.
    """
    # Attempt 1: Groq Vision
    text = await _try_groq_vision(file_bytes, filename)
    if text:
        return text

    # Attempt 2: OpenAI Vision fallback
    text = await _try_openai_vision(file_bytes, filename)
    if text:
        return text

    # Both providers failed
    logger.error(
        "All OCR providers failed for file '%s'",
        filename,
        extra={"filename": filename},
    )
    raise AllOCRFailedError(
        "Could not extract text from the uploaded image. Both Groq Vision "
        "and OpenAI Vision failed. Please try uploading a clearer photo "
        "or a PDF version of your lab report."
    )
