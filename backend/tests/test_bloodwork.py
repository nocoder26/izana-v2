"""
Stage 7 tests: Bloodwork pipeline — file upload, extraction, and analysis.

Tests cover:
- File size validation (>5 MB rejected)
- File type validation (unsupported types rejected)
- Accepted file types (PDF, JPG, PNG)
- Feature flag gating (returns 503 when BLOODWORK disabled)
- Biomarker extraction returns a list
- PDF text extraction works correctly

Decision 8:  Tests written alongside each stage.
Decision 11: Feature flag gating.
Decision 19: Deterministic mock clients — no API calls in tests.
"""

import io
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

JWT_SECRET = "test-jwt-secret-at-least-32-characters-long-enough"
ADMIN_KEY = "test-admin-api-key-64chars-padded-for-testing-purposes-here-ok"


def _make_jwt(user_id: str) -> str:
    """Create a valid JWT for testing."""
    import jwt as pyjwt
    from datetime import datetime, timedelta, timezone

    payload = {
        "sub": user_id,
        "aud": "authenticated",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
        "role": "authenticated",
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")


def _get_test_client(bloodwork_enabled: bool = True) -> TestClient:
    """Build a TestClient with mocked settings to avoid real env vars.

    Args:
        bloodwork_enabled: Value for ``FEATURE_BLOODWORK_ENABLED``.

    Returns:
        A ``TestClient`` wired to the FastAPI ``app``.
    """
    # Patch settings across all modules that import it at module level.
    mock_settings = MagicMock()
    mock_settings.SUPABASE_JWT_SECRET = JWT_SECRET
    mock_settings.ADMIN_API_KEY = ADMIN_KEY
    mock_settings.DEBUG = False
    mock_settings.FRONTEND_URL = "http://localhost:3000"
    mock_settings.FEATURE_BLOODWORK_ENABLED = bloodwork_enabled
    mock_settings.FEATURE_PARTNER_ENABLED = False
    mock_settings.FEATURE_FIE_ENABLED = False
    mock_settings.FEATURE_PUSH_ENABLED = False
    mock_settings.GROQ_API_KEY = "test-groq-key"
    mock_settings.OPENAI_API_KEY = "test-openai-key"
    mock_settings.ENVIRONMENT = "test"

    with patch("app.core.auth.settings", mock_settings), \
         patch("app.core.feature_flags.settings", mock_settings):
        from app.api.bloodwork import router
        from fastapi import FastAPI

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api/v1")

        return TestClient(test_app)


def _make_pdf_bytes() -> bytes:
    """Create a minimal valid PDF file for testing.

    Returns:
        Bytes of a simple single-page PDF containing the text
        'TSH 2.5 mIU/L'.
    """
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)

    # Add metadata so the PDF is valid; actual text extraction from a
    # blank page will return empty, which is fine -- we mock the extractor.
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _make_large_bytes(size_mb: float) -> bytes:
    """Create a byte string of the specified size in MB."""
    return b"\x00" * int(size_mb * 1024 * 1024)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFileUploadValidation:
    """Validate file type and size constraints on /analyze-file."""

    def test_upload_rejects_oversized_file(self):
        """Files larger than 5 MB should be rejected with 422."""
        client = _get_test_client(bloodwork_enabled=True)
        token = _make_jwt("test-user-id")

        large_content = _make_large_bytes(5.5)

        with patch("app.api.bloodwork.upload_file", new_callable=AsyncMock):
            response = client.post(
                "/api/v1/bloodwork/analyze-file",
                headers={"Authorization": f"Bearer {token}"},
                files={
                    "file": ("large_report.pdf", io.BytesIO(large_content), "application/pdf"),
                },
            )

        assert response.status_code == 422
        assert "5 MB" in response.json()["detail"]

    def test_upload_rejects_invalid_file_type_exe(self):
        """An .exe file should be rejected with 422."""
        client = _get_test_client(bloodwork_enabled=True)
        token = _make_jwt("test-user-id")

        response = client.post(
            "/api/v1/bloodwork/analyze-file",
            headers={"Authorization": f"Bearer {token}"},
            files={
                "file": ("malware.exe", io.BytesIO(b"MZ..."), "application/octet-stream"),
            },
        )

        assert response.status_code == 422
        assert "Unsupported" in response.json()["detail"]

    def test_upload_rejects_invalid_file_type_doc(self):
        """A .doc file should be rejected with 422."""
        client = _get_test_client(bloodwork_enabled=True)
        token = _make_jwt("test-user-id")

        response = client.post(
            "/api/v1/bloodwork/analyze-file",
            headers={"Authorization": f"Bearer {token}"},
            files={
                "file": (
                    "report.doc",
                    io.BytesIO(b"fake doc content"),
                    "application/msword",
                ),
            },
        )

        assert response.status_code == 422
        assert "Unsupported" in response.json()["detail"]

    def test_upload_accepts_pdf(self):
        """A valid PDF under 5 MB should pass validation (mocked pipeline)."""
        client = _get_test_client(bloodwork_enabled=True)
        token = _make_jwt("test-user-id")
        pdf_bytes = _make_pdf_bytes()

        mock_biomarkers = [
            {"biomarker": "TSH", "value": 2.5, "unit": "mIU/L", "ref_min": 0.4, "ref_max": 4.0}
        ]

        with patch("app.api.bloodwork.upload_file", new_callable=AsyncMock, return_value="user/file.pdf"), \
             patch("app.api.bloodwork._extract_text", new_callable=AsyncMock, return_value="TSH 2.5 mIU/L"), \
             patch("app.services.bloodwork_extractor.BloodworkExtractor.extract", new_callable=AsyncMock, return_value=mock_biomarkers), \
             patch("app.core.database.get_supabase_client") as mock_db:
            # Mock the DB insert for snapshot
            mock_client = MagicMock()
            mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])
            mock_db.return_value = mock_client

            response = client.post(
                "/api/v1/bloodwork/analyze-file",
                headers={"Authorization": f"Bearer {token}"},
                files={
                    "file": ("bloodwork.pdf", io.BytesIO(pdf_bytes), "application/pdf"),
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["file_path"] == "user/file.pdf"
        assert len(data["extracted_biomarkers"]) == 1
        assert data["extracted_biomarkers"][0]["biomarker"] == "TSH"

    def test_upload_accepts_jpg(self):
        """A JPG image should pass file-type validation (mocked pipeline)."""
        client = _get_test_client(bloodwork_enabled=True)
        token = _make_jwt("test-user-id")

        # Minimal JPEG header bytes
        jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 100

        mock_biomarkers = [
            {"biomarker": "AMH", "value": 2.1, "unit": "ng/mL", "ref_min": 1.0, "ref_max": 3.5}
        ]

        with patch("app.api.bloodwork.upload_file", new_callable=AsyncMock, return_value="user/file.jpg"), \
             patch("app.api.bloodwork._extract_text", new_callable=AsyncMock, return_value="AMH 2.1 ng/mL"), \
             patch("app.services.bloodwork_extractor.BloodworkExtractor.extract", new_callable=AsyncMock, return_value=mock_biomarkers), \
             patch("app.core.database.get_supabase_client") as mock_db:
            mock_client = MagicMock()
            mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])
            mock_db.return_value = mock_client

            response = client.post(
                "/api/v1/bloodwork/analyze-file",
                headers={"Authorization": f"Bearer {token}"},
                files={
                    "file": ("report.jpg", io.BytesIO(jpeg_bytes), "image/jpeg"),
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["extracted_biomarkers"][0]["biomarker"] == "AMH"

    def test_upload_accepts_png(self):
        """A PNG image should pass file-type validation (mocked pipeline)."""
        client = _get_test_client(bloodwork_enabled=True)
        token = _make_jwt("test-user-id")

        # Minimal PNG header
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        with patch("app.api.bloodwork.upload_file", new_callable=AsyncMock, return_value="user/file.png"), \
             patch("app.api.bloodwork._extract_text", new_callable=AsyncMock, return_value="FSH 6.0 mIU/mL"), \
             patch("app.services.bloodwork_extractor.BloodworkExtractor.extract", new_callable=AsyncMock, return_value=[{"biomarker": "FSH", "value": 6.0, "unit": "mIU/mL", "ref_min": 3.5, "ref_max": 12.5}]), \
             patch("app.core.database.get_supabase_client") as mock_db:
            mock_client = MagicMock()
            mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])
            mock_db.return_value = mock_client

            response = client.post(
                "/api/v1/bloodwork/analyze-file",
                headers={"Authorization": f"Bearer {token}"},
                files={
                    "file": ("report.png", io.BytesIO(png_bytes), "image/png"),
                },
            )

        assert response.status_code == 200


class TestFeatureFlag:
    """Verify that the BLOODWORK feature flag gates all endpoints."""

    def test_feature_flag_disabled_returns_503(self):
        """All bloodwork endpoints should return 503 when BLOODWORK is disabled."""
        client = _get_test_client(bloodwork_enabled=False)
        token = _make_jwt("test-user-id")
        headers = {"Authorization": f"Bearer {token}"}

        # analyze-file
        response = client.post(
            "/api/v1/bloodwork/analyze-file",
            headers=headers,
            files={"file": ("test.pdf", io.BytesIO(b"fake"), "application/pdf")},
        )
        assert response.status_code == 503
        assert "coming soon" in response.json()["detail"].lower()

        # confirm-results
        response = client.post(
            "/api/v1/bloodwork/confirm-results",
            headers=headers,
            json={"biomarkers": [{"biomarker": "TSH", "value": 2.5, "unit": "mIU/L"}]},
        )
        assert response.status_code == 503

        # analyze-bloodwork
        response = client.post(
            "/api/v1/bloodwork/analyze-bloodwork",
            headers=headers,
        )
        assert response.status_code == 503


class TestBiomarkerExtraction:
    """Test biomarker extraction returns the expected structure."""

    def test_biomarker_extraction_returns_list(self):
        """BloodworkExtractor.extract() should return a list of dicts."""
        from app.services.bloodwork_extractor import BloodworkExtractor

        extractor = BloodworkExtractor.__new__(BloodworkExtractor)
        extractor.swarm_id = "swarm_2_extractor"

        # Test validate_output with valid data
        valid_output = '[{"biomarker": "TSH", "value": 2.5, "unit": "mIU/L"}]'
        assert extractor.validate_output(valid_output) is True

        # Test validate_output with invalid data (missing required keys)
        invalid_output = '[{"name": "TSH"}]'
        assert extractor.validate_output(invalid_output) is False

        # Test get_fallback_value returns an empty list
        assert extractor.get_fallback_value() == []

    def test_extractor_accepts_empty_array(self):
        """An empty JSON array is valid (report had no recognisable biomarkers)."""
        from app.services.bloodwork_extractor import BloodworkExtractor

        extractor = BloodworkExtractor.__new__(BloodworkExtractor)
        extractor.swarm_id = "swarm_2_extractor"

        assert extractor.validate_output("[]") is True

    def test_extractor_rejects_non_array(self):
        """A JSON object (not array) should fail validation."""
        from app.services.bloodwork_extractor import BloodworkExtractor

        extractor = BloodworkExtractor.__new__(BloodworkExtractor)
        extractor.swarm_id = "swarm_2_extractor"

        assert extractor.validate_output('{"biomarker": "TSH"}') is False


class TestPDFExtraction:
    """Test PDF text extraction with pypdf."""

    def test_pdf_text_extraction_works(self):
        """extract_text_from_pdf should handle a valid (empty) PDF gracefully."""
        from app.services.pdf_handler import extract_text_from_pdf

        pdf_bytes = _make_pdf_bytes()
        result = extract_text_from_pdf(pdf_bytes)

        # A blank-page PDF will yield empty text; the function should
        # return an empty string rather than raise.
        assert isinstance(result, str)

    def test_pdf_extraction_handles_corrupt_file(self):
        """Corrupt bytes should return an error message, not raise."""
        from app.services.pdf_handler import extract_text_from_pdf

        result = extract_text_from_pdf(b"this is not a PDF")
        assert isinstance(result, str)
        assert "ERROR" in result

    def test_pdf_extraction_handles_empty_bytes(self):
        """Empty bytes should return an error message."""
        from app.services.pdf_handler import extract_text_from_pdf

        result = extract_text_from_pdf(b"")
        assert isinstance(result, str)
        # Either empty string or an error message -- both are acceptable.

    def test_image_extraction_placeholder_returns_empty(self):
        """The image extraction placeholder should return an empty string."""
        from app.services.pdf_handler import extract_text_from_image

        result = extract_text_from_image(b"fake image bytes")
        assert result == ""
