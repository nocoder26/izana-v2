"""
PDF and image text extraction utilities.

Provides helpers to extract raw text from uploaded bloodwork files:
- PDF extraction via ``pypdf``
- Image OCR placeholder (delegates to :mod:`app.services.vision_client`)

Encrypted or password-protected PDFs are handled gracefully -- the caller
receives a human-readable error message instead of an unhandled exception.
"""

from __future__ import annotations

import io

from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PdfReadError

from app.core.logging_config import get_logger

logger = get_logger(__name__)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from all pages of a PDF file.

    Args:
        file_bytes: Raw bytes of a PDF document.

    Returns:
        The concatenated text content of every page, separated by
        newlines.  If the PDF is encrypted or otherwise unreadable,
        a descriptive error string is returned instead.
    """
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
    except FileNotDecryptedError:
        logger.warning("Received encrypted/password-protected PDF")
        return (
            "ERROR: This PDF is password-protected. Please upload an "
            "unprotected version of your lab report."
        )
    except PdfReadError as exc:
        logger.warning("Could not read PDF: %s", exc)
        return (
            "ERROR: Could not read this PDF file. The file may be "
            "corrupted. Please try uploading again or use a different "
            "format (e.g. a photo of the report)."
        )
    except Exception as exc:
        logger.exception("Unexpected error reading PDF")
        return f"ERROR: Failed to process PDF: {exc}"

    pages_text: list[str] = []
    for page_num, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
            if text.strip():
                pages_text.append(text.strip())
        except Exception as exc:
            logger.warning(
                "Failed to extract text from page %d: %s",
                page_num,
                exc,
            )
            continue

    if not pages_text:
        logger.info(
            "PDF contained no extractable text -- likely a scanned image"
        )
        return ""

    combined = "\n\n".join(pages_text)
    logger.info(
        "Extracted text from PDF",
        extra={"page_count": len(reader.pages), "text_length": len(combined)},
    )
    return combined


def extract_text_from_image(file_bytes: bytes) -> str:
    """Placeholder for local OCR extraction from an image.

    Image-based OCR is handled by :func:`~app.services.vision_client.extract_text_from_image_vision`
    which uses Groq Vision / OpenAI Vision APIs.  This function exists as
    a structural placeholder and returns an empty string to signal that
    the caller should fall through to the vision-based pipeline.

    Args:
        file_bytes: Raw image bytes (JPG, PNG, HEIC).

    Returns:
        An empty string, indicating the caller should use the vision API.
    """
    logger.debug(
        "extract_text_from_image called -- delegating to vision client"
    )
    return ""
