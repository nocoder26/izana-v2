"""
Bloodwork API endpoints — file upload, confirmation, and analysis.

Provides three endpoints gated behind the ``FEATURE_BLOODWORK_ENABLED``
feature flag (Decision 11):

- ``POST /bloodwork/analyze-file``    — Upload and extract biomarkers
- ``POST /bloodwork/confirm-results`` — Confirm/edit extracted values
- ``POST /bloodwork/analyze-bloodwork`` — Run full analysis pipeline

Architecture notes:
- Swarm 2 (BloodworkExtractor) parses OCR text into structured biomarkers.
- Swarm 5 (BloodworkAnalyser) interprets values against reference ranges.
- Swarm 6 (BloodworkCurator) rewrites analysis in patient-friendly language.
- Swarm 7 (ComplianceChecker) ensures medical compliance before delivery.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel, Field

from app.core.auth import get_user_id
from app.core.database import get_supabase_admin as get_supabase_client
from app.core.feature_flags import require_feature
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# ── Router (gated behind BLOODWORK feature flag) ─────────────────────────

router = APIRouter(
    prefix="/bloodwork",
    dependencies=[require_feature("BLOODWORK")],
)

# ── Constants ────────────────────────────────────────────────────────────

_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
_ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/heic",
    "image/heif",
}
_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".heic", ".heif"}

# ── Pydantic Models ──────────────────────────────────────────────────────


class FileUploadResponse(BaseModel):
    """Response from the ``/analyze-file`` endpoint.

    Attributes:
        file_path:            Storage path of the uploaded file.
        extracted_biomarkers: List of biomarker dicts extracted from the file.
        message:              Human-readable status message.
    """

    file_path: str
    extracted_biomarkers: list[dict[str, Any]]
    message: str


class ConfirmResultsRequest(BaseModel):
    """Request body for the ``/confirm-results`` endpoint.

    Attributes:
        biomarkers: List of confirmed/edited biomarker dicts, each
                    containing ``biomarker``, ``value``, ``unit``,
                    ``ref_min``, and ``ref_max``.
    """

    biomarkers: list[dict[str, Any]] = Field(
        ...,
        min_length=1,
        description=(
            "List of biomarker objects, each with keys: "
            "biomarker, value, unit, ref_min, ref_max"
        ),
    )


class ConfirmResultsResponse(BaseModel):
    """Response from the ``/confirm-results`` endpoint.

    Attributes:
        message: Confirmation status message.
        biomarker_count: Number of confirmed biomarkers saved.
    """

    message: str
    biomarker_count: int


class AnalysisResponse(BaseModel):
    """Response from the ``/analyze-bloodwork`` endpoint.

    Attributes:
        analysis_text:    Patient-friendly analysis text.
        biomarker_summary: Structured summary of each biomarker's status.
        message_id:       Unique identifier for this analysis exchange.
    """

    analysis_text: str
    biomarker_summary: list[dict[str, Any]]
    message_id: str


# ── Helpers ──────────────────────────────────────────────────────────────


def _validate_file_extension(filename: str) -> None:
    """Raise 422 if the file extension is not in the allowed set.

    Args:
        filename: The original filename from the upload.

    Raises:
        HTTPException 422: If the file type is not supported.
    """
    import os

    _, ext = os.path.splitext(filename.lower())
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Unsupported file type '{ext}'. "
                f"Accepted formats: PDF, JPG, PNG, HEIC."
            ),
        )


def _validate_content_type(content_type: str | None) -> None:
    """Raise 422 if the MIME content type is not allowed.

    Args:
        content_type: The MIME type reported by the upload.

    Raises:
        HTTPException 422: If the content type is not supported.
    """
    if not content_type or content_type.lower() not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Unsupported content type '{content_type}'. "
                f"Accepted types: PDF, JPG, PNG, HEIC."
            ),
        )


async def _extract_text(
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> str:
    """Extract text from a file using the appropriate method.

    PDFs are processed with ``pypdf`` first; if no text is found (scanned
    PDF), the vision API is used as a fallback.  Image files go directly
    to the vision API.

    Args:
        file_bytes:   Raw file bytes.
        filename:     Original filename.
        content_type: MIME type of the file.

    Returns:
        Extracted text from the file.

    Raises:
        HTTPException 422: If text extraction fails completely.
    """
    from app.services.pdf_handler import extract_text_from_pdf
    from app.services.vision_client import (
        AllOCRFailedError,
        extract_text_from_image_vision,
    )

    if content_type == "application/pdf":
        text = extract_text_from_pdf(file_bytes)
        if text.startswith("ERROR:"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=text,
            )
        # If pypdf returned no text (scanned PDF), try vision OCR.
        if not text.strip():
            logger.info("PDF had no extractable text, trying vision OCR")
            try:
                text = await extract_text_from_image_vision(file_bytes, filename)
            except AllOCRFailedError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=str(exc),
                )
        return text

    # Image file -- use vision API directly.
    try:
        return await extract_text_from_image_vision(file_bytes, filename)
    except AllOCRFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )


# ── Endpoints ────────────────────────────────────────────────────────────


@router.post(
    "/analyze-file",
    response_model=FileUploadResponse,
    summary="Upload a bloodwork file and extract biomarkers",
)
async def analyze_file(
    file: UploadFile = File(..., description="PDF, JPG, PNG, or HEIC lab report (max 5 MB)"),
    user_id: str = Depends(get_user_id),
) -> FileUploadResponse:
    """Upload a bloodwork file, extract text, and return structured biomarker values.

    The endpoint:
    1. Validates file type and size.
    2. Uploads the file to Supabase Storage.
    3. Extracts text (pypdf for PDFs, Vision API for images).
    4. Runs Swarm 2 (BloodworkExtractor) to parse biomarker values.
    5. Saves extracted data to the ``bloodwork_snapshots`` table.
    6. Returns extracted biomarkers for user confirmation.

    Args:
        file:    Uploaded file (multipart form data).
        user_id: Authenticated user ID (injected by ``get_user_id``).

    Returns:
        A :class:`FileUploadResponse` containing the storage path and
        extracted biomarker data.
    """
    from app.services.bloodwork_extractor import BloodworkExtractor
    from app.services.storage import upload_file

    # ── Validate file ─────────────────────────────────────────────────
    filename = file.filename or "upload"
    _validate_file_extension(filename)
    _validate_content_type(file.content_type)

    file_bytes = await file.read()
    if len(file_bytes) > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"File size ({len(file_bytes) / (1024 * 1024):.1f} MB) "
                f"exceeds the 5 MB limit."
            ),
        )

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty.",
        )

    content_type = file.content_type or "application/octet-stream"

    # ── Upload to storage ─────────────────────────────────────────────
    try:
        file_path = await upload_file(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
            user_id=user_id,
        )
    except RuntimeError as exc:
        logger.error(
            "Storage upload failed",
            extra={"user_id": user_id, "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store the uploaded file. Please try again.",
        )

    # ── Extract text ──────────────────────────────────────────────────
    text = await _extract_text(file_bytes, filename, content_type)

    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "No text could be extracted from the uploaded file. "
                "Please upload a clearer image or a text-based PDF."
            ),
        )

    # ── Run Swarm 2: Biomarker Extraction ─────────────────────────────
    trace_id = str(uuid4())
    extractor = BloodworkExtractor()

    try:
        biomarkers = await extractor.extract(
            ocr_text=text,
            gender="female",
            trace_id=trace_id,
        )
    except Exception as exc:
        logger.exception(
            "Biomarker extraction failed",
            extra={"user_id": user_id, "trace_id": trace_id},
        )
        biomarkers = []

    # ── Save snapshot to database ─────────────────────────────────────
    snapshot_id = str(uuid4())
    try:
        supabase = get_supabase_client()
        await asyncio.to_thread(
            lambda: supabase.table("bloodwork_snapshots")
            .insert(
                {
                    "id": snapshot_id,
                    "user_id": user_id,
                    "file_path": file_path,
                    "raw_text": text[:10000],  # Truncate for safety
                    "extracted_biomarkers": json.dumps(biomarkers, default=str),
                    "status": "pending_confirmation",
                }
            )
            .execute()
        )
    except Exception:
        logger.exception(
            "Failed to save bloodwork snapshot",
            extra={"user_id": user_id, "snapshot_id": snapshot_id},
        )
        # Non-fatal -- the user still gets their extracted biomarkers.

    return FileUploadResponse(
        file_path=file_path,
        extracted_biomarkers=biomarkers,
        message=(
            f"Successfully extracted {len(biomarkers)} biomarker(s). "
            f"Please review and confirm the values."
            if biomarkers
            else "No biomarkers could be automatically extracted. "
            "Please enter your values manually."
        ),
    )


@router.post(
    "/confirm-results",
    response_model=ConfirmResultsResponse,
    summary="Confirm or edit extracted biomarker values",
)
async def confirm_results(
    request: ConfirmResultsRequest,
    user_id: str = Depends(get_user_id),
) -> ConfirmResultsResponse:
    """Accept confirmed or manually-edited biomarker values from the user.

    Updates the most recent ``bloodwork_snapshots`` entry for this user
    with the confirmed values, and writes the biomarkers to
    ``profiles.core_fertility_json``.

    Args:
        request: Confirmed biomarker data.
        user_id: Authenticated user ID (injected by ``get_user_id``).

    Returns:
        A :class:`ConfirmResultsResponse` acknowledging the save.
    """
    supabase = get_supabase_client()
    biomarkers_json = json.dumps(request.biomarkers, default=str)

    # ── Update latest snapshot status ─────────────────────────────────
    try:
        await asyncio.to_thread(
            lambda: supabase.table("bloodwork_snapshots")
            .update(
                {
                    "confirmed_biomarkers": biomarkers_json,
                    "status": "confirmed",
                }
            )
            .eq("user_id", user_id)
            .eq("status", "pending_confirmation")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception(
            "Failed to update bloodwork snapshot",
            extra={"user_id": user_id},
        )

    # ── Update profile with confirmed fertility data ──────────────────
    try:
        await asyncio.to_thread(
            lambda: supabase.table("profiles")
            .update({"core_fertility_json": biomarkers_json})
            .eq("user_id", user_id)
            .execute()
        )
    except Exception:
        logger.exception(
            "Failed to update core_fertility_json in profile",
            extra={"user_id": user_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save confirmed biomarker values.",
        )

    logger.info(
        "Bloodwork results confirmed",
        extra={
            "user_id": user_id,
            "biomarker_count": len(request.biomarkers),
        },
    )

    return ConfirmResultsResponse(
        message="Biomarker values confirmed and saved.",
        biomarker_count=len(request.biomarkers),
    )


@router.post(
    "/analyze-bloodwork",
    response_model=AnalysisResponse,
    summary="Run full bloodwork analysis pipeline",
)
async def analyze_bloodwork(
    user_id: str = Depends(get_user_id),
) -> AnalysisResponse:
    """Run the full bloodwork analysis pipeline on confirmed biomarker values.

    Pipeline steps:
    1. Fetch confirmed biomarkers from ``profiles.core_fertility_json``.
    2. Swarm 5 (BloodworkAnalyser) — interpret values against reference ranges.
    3. Swarm 6 (BloodworkCurator) — rewrite as patient-friendly text.
    4. Swarm 7 (ComplianceChecker) — ensure medical compliance.
    5. Save the final analysis to ``profiles.bloodwork_analysis_json``.

    Args:
        user_id: Authenticated user ID (injected by ``get_user_id``).

    Returns:
        An :class:`AnalysisResponse` with the patient-friendly analysis.
    """
    from app.services.bloodwork_analyser import BloodworkAnalyser
    from app.services.bloodwork_curator import BloodworkCurator
    from app.services.compliance_checker import ComplianceChecker

    supabase = get_supabase_client()
    trace_id = str(uuid4())
    message_id = str(uuid4())

    # ── Fetch confirmed biomarkers from profile ───────────────────────
    try:
        result = await asyncio.to_thread(
            lambda: supabase.table("profiles")
            .select("core_fertility_json")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception(
            "Failed to fetch profile for analysis",
            extra={"user_id": user_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve your biomarker data.",
        )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No profile found. Please complete your profile first.",
        )

    core_fertility_raw = result.data[0].get("core_fertility_json")
    if not core_fertility_raw:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No confirmed biomarker data found. "
                "Please upload and confirm your bloodwork first."
            ),
        )

    # Parse biomarkers (handle both string and dict/list).
    if isinstance(core_fertility_raw, str):
        try:
            biomarkers: list[dict[str, Any]] = json.loads(core_fertility_raw)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Stored biomarker data is malformed.",
            )
    else:
        biomarkers = core_fertility_raw

    if not biomarkers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No biomarkers available for analysis.",
        )

    # ── Swarm 5: Analyse biomarkers ───────────────────────────────────
    analyser = BloodworkAnalyser()
    try:
        analysis_results = await analyser.analyse(
            biomarkers=biomarkers,
            gender="female",
            age_range="25-40",
            trace_id=trace_id,
        )
    except Exception as exc:
        logger.exception(
            "Swarm 5 (Analyser) failed",
            extra={"user_id": user_id, "trace_id": trace_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Biomarker analysis failed. Please try again.",
        )

    # ── Swarm 6: Format for patient ───────────────────────────────────
    curator = BloodworkCurator()
    user_context = f"User ID: {user_id}. Reviewing bloodwork results."

    try:
        patient_text = await curator.format_for_patient(
            analysis_json=analysis_results,
            user_context=user_context,
            trace_id=trace_id,
        )
    except Exception as exc:
        logger.exception(
            "Swarm 6 (Curator) failed",
            extra={"user_id": user_id, "trace_id": trace_id},
        )
        patient_text = (
            "Your bloodwork results have been recorded. Please discuss "
            "the details with your doctor for a full interpretation."
        )

    # ── Swarm 7: Compliance check ─────────────────────────────────────
    compliance = ComplianceChecker()
    try:
        final_text = await compliance.check(
            response_text=patient_text,
            trace_id=trace_id,
        )
    except Exception:
        logger.warning(
            "Swarm 7 (Compliance) failed, using unchecked text",
            extra={"user_id": user_id, "trace_id": trace_id},
        )
        final_text = patient_text

    # ── Save analysis to profile ──────────────────────────────────────
    analysis_payload = {
        "analysis_text": final_text,
        "biomarker_summary": analysis_results,
        "message_id": message_id,
        "trace_id": trace_id,
    }

    try:
        await asyncio.to_thread(
            lambda: supabase.table("profiles")
            .update(
                {
                    "bloodwork_analysis_json": json.dumps(
                        analysis_payload, default=str
                    )
                }
            )
            .eq("user_id", user_id)
            .execute()
        )
    except Exception:
        logger.exception(
            "Failed to save bloodwork analysis to profile",
            extra={"user_id": user_id, "message_id": message_id},
        )
        # Non-fatal -- user still receives their analysis.

    logger.info(
        "Bloodwork analysis complete",
        extra={
            "user_id": user_id,
            "message_id": message_id,
            "biomarker_count": len(analysis_results),
        },
    )

    return AnalysisResponse(
        analysis_text=final_text,
        biomarker_summary=analysis_results,
        message_id=message_id,
    )
