"""
Stage 3 tests: JWT verification and auth dependencies (Decision 1).

Tests cover:
- Valid JWT token acceptance
- Expired JWT token rejection
- Forged/invalid JWT token rejection
- Missing Authorization header rejection
- Admin API key verification
- Feature flag gating (Decision 11)
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
import jwt as pyjwt
from datetime import datetime, timedelta, timezone


JWT_SECRET = "test-jwt-secret-at-least-32-characters-long-enough"
ADMIN_KEY = "test-admin-api-key-64chars-padded-for-testing-purposes-here-ok"


@pytest.fixture(autouse=True)
def patch_settings():
    """Patch the settings singleton used by auth and feature_flags modules."""
    with patch("app.core.auth.settings") as auth_settings, \
         patch("app.core.feature_flags.settings", create=True) as ff_settings:
        # Auth settings
        auth_settings.SUPABASE_JWT_SECRET = JWT_SECRET
        auth_settings.ADMIN_API_KEY = ADMIN_KEY
        # Feature flag settings
        ff_settings.FEATURE_BLOODWORK_ENABLED = True
        ff_settings.FEATURE_PARTNER_ENABLED = True
        ff_settings.FEATURE_FIE_ENABLED = False
        ff_settings.FEATURE_PUSH_ENABLED = True
        yield auth_settings


def make_jwt(user_id: str, secret: str = JWT_SECRET,
             expired: bool = False, audience: str = "authenticated") -> str:
    """Helper to create JWT tokens for testing."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "aud": audience,
        "exp": now - timedelta(hours=1) if expired else now + timedelta(hours=1),
        "iat": now - timedelta(hours=2) if expired else now,
        "role": "authenticated",
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")


class TestJWTVerification:
    """Test server-side JWT verification (Decision 1)."""

    def test_valid_token_returns_user_id(self, patch_settings):
        """A valid Supabase JWT should return the user_id from the sub claim."""
        from app.core.auth import get_user_id
        import asyncio

        user_id = "550e8400-e29b-41d4-a716-446655440000"
        token = make_jwt(user_id)

        request = MagicMock()
        request.headers.get.return_value = f"Bearer {token}"

        result = asyncio.get_event_loop().run_until_complete(get_user_id(request))
        assert result == user_id

    def test_expired_token_raises_401(self, patch_settings):
        """An expired JWT should raise 401."""
        from app.core.auth import get_user_id
        import asyncio

        token = make_jwt("some-user", expired=True)
        request = MagicMock()
        request.headers.get.return_value = f"Bearer {token}"

        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(get_user_id(request))
        assert exc_info.value.status_code == 401

    def test_forged_token_raises_401(self, patch_settings):
        """A JWT signed with the wrong secret should raise 401."""
        from app.core.auth import get_user_id
        import asyncio

        token = make_jwt("some-user", secret="wrong-secret-that-doesnt-match")
        request = MagicMock()
        request.headers.get.return_value = f"Bearer {token}"

        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(get_user_id(request))
        assert exc_info.value.status_code == 401

    def test_missing_header_raises_401(self, patch_settings):
        """Missing Authorization header should raise 401."""
        from app.core.auth import get_user_id
        import asyncio

        request = MagicMock()
        request.headers.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(get_user_id(request))
        assert exc_info.value.status_code == 401

    def test_malformed_bearer_raises_401(self, patch_settings):
        """'Bearer' prefix without a token should raise 401."""
        from app.core.auth import get_user_id
        import asyncio

        request = MagicMock()
        request.headers.get.return_value = "Bearer "

        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(get_user_id(request))
        assert exc_info.value.status_code == 401


class TestAdminKeyVerification:
    """Test admin API key verification."""

    def test_valid_admin_key(self, patch_settings):
        """Valid X-Admin-API-Key should pass."""
        from app.core.auth import get_admin_key
        import asyncio

        request = MagicMock()
        request.headers.get.return_value = ADMIN_KEY

        result = asyncio.get_event_loop().run_until_complete(get_admin_key(request))
        assert result == ADMIN_KEY

    def test_invalid_admin_key_raises_403(self, patch_settings):
        """Invalid admin key should raise 403."""
        from app.core.auth import get_admin_key
        import asyncio

        request = MagicMock()
        request.headers.get.return_value = "wrong-key"

        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(get_admin_key(request))
        assert exc_info.value.status_code == 403


class TestFeatureFlags:
    """Test feature flag gating (Decision 11)."""

    def test_enabled_feature_passes(self, patch_settings):
        """Enabled feature should not raise."""
        from app.core.feature_flags import require_feature
        from fastapi import Depends

        # require_feature returns Depends(_check_feature)
        # We need the inner function — it's the .dependency attribute
        dep = require_feature("bloodwork")
        inner_fn = dep.dependency
        # FEATURE_BLOODWORK_ENABLED = True, should not raise
        result = inner_fn()
        assert result is True

    def test_disabled_feature_raises_503(self, patch_settings):
        """Disabled feature should raise 503 with human-friendly message."""
        from app.core.feature_flags import require_feature

        dep = require_feature("fie")
        inner_fn = dep.dependency
        # FEATURE_FIE_ENABLED = False
        with pytest.raises(HTTPException) as exc_info:
            inner_fn()
        assert exc_info.value.status_code == 503
        assert "coming soon" in exc_info.value.detail.lower()


class TestInputValidation:
    """Test input sanitization and PII detection."""

    def test_sanitize_strips_html(self):
        from app.core.validators import sanitize_input
        assert "<" not in sanitize_input("<b>hello</b>")

    def test_sanitize_enforces_2000_char_limit(self):
        from app.core.validators import sanitize_input
        long_input = "a" * 3000
        result = sanitize_input(long_input)
        assert len(result) <= 2000

    def test_pii_detects_email(self):
        from app.core.validators import check_for_pii
        result = check_for_pii("my email is test@example.com")
        assert result.has_pii is True
        assert "email" in result.pii_types

    def test_pii_detects_phone(self):
        from app.core.validators import check_for_pii
        result = check_for_pii("call me at 555-123-4567")
        assert result.has_pii is True

    def test_pii_clean_text_passes(self):
        from app.core.validators import check_for_pii
        result = check_for_pii("What should I eat during IVF stims?")
        assert result.has_pii is False

    def test_greeting_detection(self):
        from app.core.validators import is_greeting
        assert is_greeting("hello") is True
        assert is_greeting("hi") is True
        assert is_greeting("What is AMH?") is False
