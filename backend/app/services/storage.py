"""
Supabase Storage file upload service.

Handles uploading bloodwork files (PDFs, images) to the ``bloodwork``
bucket in Supabase Storage and generating signed download URLs.

The bucket is created automatically on first use if it does not yet exist.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from app.core.database import get_supabase_client
from app.core.logging_config import get_logger

logger = get_logger(__name__)

_BUCKET_NAME = "bloodwork"
_SIGNED_URL_EXPIRY_SECONDS = 3600  # 1 hour


async def _ensure_bucket_exists() -> None:
    """Create the ``bloodwork`` storage bucket if it does not already exist.

    Uses the service-role client which has permission to create buckets.
    Failures are logged but not propagated -- the subsequent upload call
    will surface a clear error if the bucket is genuinely missing.
    """
    try:
        supabase = get_supabase_client()

        def _create() -> None:
            try:
                supabase.storage.create_bucket(
                    _BUCKET_NAME,
                    options={
                        "public": False,
                        "file_size_limit": 5 * 1024 * 1024,  # 5 MB
                    },
                )
            except Exception as exc:
                # "Bucket already exists" is expected on subsequent calls.
                if "already exists" in str(exc).lower() or "duplicate" in str(exc).lower():
                    logger.debug("Storage bucket '%s' already exists", _BUCKET_NAME)
                else:
                    raise

        await asyncio.to_thread(_create)
    except Exception:
        logger.warning(
            "Could not ensure storage bucket '%s' exists -- upload may still succeed "
            "if the bucket was created previously",
            _BUCKET_NAME,
        )


async def upload_file(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    user_id: str,
) -> str:
    """Upload a file to the ``bloodwork`` Supabase Storage bucket.

    The file is stored under a user-scoped path with a UUID prefix to
    prevent collisions::

        <user_id>/<uuid>_<filename>

    Args:
        file_bytes:   Raw file content.
        filename:     Original filename (used as a suffix in the stored path).
        content_type: MIME type (e.g. ``"application/pdf"``).
        user_id:      Authenticated Supabase user ID (used as a folder prefix).

    Returns:
        The storage path of the uploaded file (relative to the bucket root).

    Raises:
        RuntimeError: If the upload fails.
    """
    await _ensure_bucket_exists()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    unique_id = uuid4().hex[:8]
    safe_filename = filename.replace(" ", "_")
    file_path = f"{user_id}/{timestamp}_{unique_id}_{safe_filename}"

    supabase = get_supabase_client()

    def _upload() -> None:
        supabase.storage.from_(_BUCKET_NAME).upload(
            path=file_path,
            file=file_bytes,
            file_options={"content-type": content_type},
        )

    try:
        await asyncio.to_thread(_upload)
    except Exception as exc:
        logger.error(
            "Failed to upload file to storage",
            extra={
                "bucket": _BUCKET_NAME,
                "file_path": file_path,
                "user_id": user_id,
                "error": str(exc),
            },
        )
        raise RuntimeError(f"File upload failed: {exc}") from exc

    logger.info(
        "File uploaded to storage",
        extra={
            "bucket": _BUCKET_NAME,
            "file_path": file_path,
            "user_id": user_id,
        },
    )
    return file_path


async def get_file_url(file_path: str) -> str:
    """Generate a time-limited signed URL for a stored file.

    Args:
        file_path: The storage path returned by :func:`upload_file`.

    Returns:
        A signed URL valid for :data:`_SIGNED_URL_EXPIRY_SECONDS` seconds.

    Raises:
        RuntimeError: If URL generation fails.
    """
    supabase = get_supabase_client()

    def _sign() -> dict:
        return supabase.storage.from_(_BUCKET_NAME).create_signed_url(
            path=file_path,
            expires_in=_SIGNED_URL_EXPIRY_SECONDS,
        )

    try:
        result = await asyncio.to_thread(_sign)
    except Exception as exc:
        logger.error(
            "Failed to generate signed URL",
            extra={"file_path": file_path, "error": str(exc)},
        )
        raise RuntimeError(f"Could not generate signed URL: {exc}") from exc

    signed_url: str = result.get("signedURL", "") or result.get("signedUrl", "")
    if not signed_url:
        raise RuntimeError(f"Signed URL response did not contain a URL: {result}")

    return signed_url
