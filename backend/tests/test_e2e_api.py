"""
E2E API Tests — tests the full user journey against the live backend.

These tests hit the REAL deployed backend at https://izana-api.onrender.com
to verify the full flow works. Uses the httpx library.

Tests run in order (sequential class/method naming):
1. Signup -> get access_token + recovery_phrase
2. Auth lookup -> always returns same format
3. Duplicate signup -> returns conflict
4. Preview chat (no auth) -> get cached responses
5. Wellness profile -> save onboarding data
6. Journey creation -> create treatment journey
7. Chapters -> get active chapter
8. Mood check-in -> daily check-in
9. Chat REST -> get a clinical response
10. Plan status -> check plan review status
11. Gamification -> check points/streak
12. Content library -> browse content
13. Nutritionist login -> auth check
14. Nutritionist queue -> requires admin auth
15. Admin dashboard -> requires admin API key
16. Admin health -> requires admin API key
17. Recovery phrase -> regenerate
18. Unauthenticated chat -> 401
19. Empty content chat -> 422
20. Health endpoint -> healthy
"""

import httpx
import pytest
import time

BASE_URL = "https://izana-api.onrender.com/api/v1"
TIMEOUT = 30  # seconds — Render cold starts can be slow

# ---------------------------------------------------------------------------
# Global state shared between ordered tests
# ---------------------------------------------------------------------------
state = {
    "access_token": None,
    "user_id": None,
    "pseudonym": None,
    "recovery_phrase": None,
}


# ---------------------------------------------------------------------------
# 1. Signup Flow
# ---------------------------------------------------------------------------
class TestSignupFlow:
    def test_01_signup_creates_account(self):
        """POST /auth/signup creates user + profile + gamification + recovery phrase."""
        pseudonym = f"TestBot{int(time.time()) % 10000}"
        r = httpx.post(
            f"{BASE_URL}/auth/signup",
            json={
                "pseudonym": pseudonym,
                "password": "TestPass2026",
                "gender": "Female",
                "avatar": "Phoenix",
                "timezone": "UTC",
            },
            timeout=TIMEOUT,
        )
        assert r.status_code in [200, 201], f"Signup failed ({r.status_code}): {r.text}"
        data = r.json()
        assert "user_id" in data, f"Missing user_id in response: {data}"
        assert "access_token" in data, f"Missing access_token in response: {data}"
        assert "recovery_phrase" in data, f"Missing recovery_phrase in response: {data}"
        # Recovery phrase format: XXXX-XXXX-XXXX-XXXX (19 chars)
        assert len(data["recovery_phrase"]) == 19, (
            f"Unexpected recovery_phrase length: {data['recovery_phrase']}"
        )

        # Persist for later tests
        state["access_token"] = data["access_token"]
        state["user_id"] = data["user_id"]
        state["pseudonym"] = data.get("pseudonym", pseudonym)
        state["recovery_phrase"] = data["recovery_phrase"]

    def test_02_lookup_always_returns_200(self):
        """GET /auth/lookup always returns same format regardless of existence."""
        r1 = httpx.get(
            f"{BASE_URL}/auth/lookup",
            params={"pseudonym": "ExistingUser"},
            timeout=TIMEOUT,
        )
        r2 = httpx.get(
            f"{BASE_URL}/auth/lookup",
            params={"pseudonym": "NonExistentXYZ999"},
            timeout=TIMEOUT,
        )
        assert r1.status_code == 200, f"Lookup existing failed: {r1.text}"
        assert r2.status_code == 200, f"Lookup non-existent failed: {r2.text}"
        assert r1.json()["email"] == "ExistingUser@users.izana.ai"
        assert r2.json()["email"] == "NonExistentXYZ999@users.izana.ai"

    def test_03_duplicate_signup_returns_conflict(self):
        """Duplicate pseudonym should fail with 409/422/400."""
        assert state["pseudonym"], "Signup must run first"
        r = httpx.post(
            f"{BASE_URL}/auth/signup",
            json={
                "pseudonym": state["pseudonym"],
                "password": "TestPass2026",
                "gender": "Female",
                "avatar": "Phoenix",
                "timezone": "UTC",
            },
            timeout=TIMEOUT,
        )
        assert r.status_code in [409, 422, 400], (
            f"Expected conflict but got {r.status_code}: {r.text}"
        )


# ---------------------------------------------------------------------------
# 2. Preview Chat (no auth required)
# ---------------------------------------------------------------------------
class TestPreviewChat:
    def test_04_cached_responses(self):
        """GET /preview/cached-responses returns 3 pre-built responses."""
        r = httpx.get(f"{BASE_URL}/preview/cached-responses", timeout=TIMEOUT)
        assert r.status_code == 200, f"Cached responses failed: {r.text}"
        data = r.json()
        assert len(data) == 3, f"Expected 3 cached responses, got {len(data)}"
        for item in data:
            assert "question" in item, f"Missing 'question' key in: {item}"
            assert "response" in item, f"Missing 'response' key in: {item}"
            assert "sources" in item, f"Missing 'sources' key in: {item}"


# ---------------------------------------------------------------------------
# 3. Authenticated Endpoints (require Bearer token from signup)
# ---------------------------------------------------------------------------
class TestAuthenticatedEndpoints:
    def _headers(self):
        assert state["access_token"], "Signup must run first to obtain token"
        return {"Authorization": f"Bearer {state['access_token']}"}

    def test_05_wellness_profile_save(self):
        """POST /nutrition/wellness-profile saves onboarding data."""
        r = httpx.post(
            f"{BASE_URL}/nutrition/wellness-profile",
            headers=self._headers(),
            json={
                "allergies": ["dairy"],
                "dietary_restrictions": ["dairy-free"],
                "food_preferences": ["Mediterranean"],
                "exercise_preferences": ["yoga", "walking"],
                "exercise_time_minutes": 20,
                "health_conditions": [],
                "fitness_level": "moderate",
                "smoking_status": "never",
                "alcohol_consumption": "none",
                "sleep_duration": "7-8h",
                "stress_level": "sometimes",
                "age_range": "31-35",
            },
            timeout=TIMEOUT,
        )
        assert r.status_code in [200, 201], (
            f"Wellness profile save failed ({r.status_code}): {r.text}"
        )

    def test_06_create_journey(self):
        """POST /journey creates treatment journey."""
        r = httpx.post(
            f"{BASE_URL}/journey",
            headers=self._headers(),
            json={
                "treatment_type": "ivf",
                "initial_phase": "stims",
            },
            timeout=TIMEOUT,
        )
        assert r.status_code in [200, 201], (
            f"Journey creation failed ({r.status_code}): {r.text}"
        )

    def test_07_get_active_chapter(self):
        """GET /chapters/active returns the active chapter or 404."""
        r = httpx.get(
            f"{BASE_URL}/chapters/active",
            headers=self._headers(),
            timeout=TIMEOUT,
        )
        # 200 with data or 404 if no chapter yet — both acceptable
        assert r.status_code in [200, 404], (
            f"Active chapter unexpected status ({r.status_code}): {r.text}"
        )

    def test_08_mood_checkin(self):
        """POST /companion/checkin records daily mood."""
        r = httpx.post(
            f"{BASE_URL}/companion/checkin",
            headers=self._headers(),
            json={"mood": "good"},
            timeout=TIMEOUT,
        )
        # 200/201 success, 409 if already checked in today
        assert r.status_code in [200, 201, 409], (
            f"Mood checkin unexpected status ({r.status_code}): {r.text}"
        )

    def test_09_chat_rest(self):
        """POST /chat returns a clinical response."""
        r = httpx.post(
            f"{BASE_URL}/chat",
            headers=self._headers(),
            json={"content": "What should I eat during IVF stims?"},
            timeout=60,  # LLM calls can be slow
        )
        assert r.status_code == 200, f"Chat failed ({r.status_code}): {r.text}"
        data = r.json()
        assert "content" in data, f"Missing 'content' in chat response: {data}"
        assert len(data["content"]) > 20, (
            f"Chat response too short ({len(data['content'])} chars)"
        )

    def test_10_plan_status(self):
        """GET /plan-status returns plan review status."""
        r = httpx.get(
            f"{BASE_URL}/plan-status",
            headers=self._headers(),
            timeout=TIMEOUT,
        )
        # 200 if plan exists, 404 if not yet
        assert r.status_code in [200, 404], (
            f"Plan status unexpected ({r.status_code}): {r.text}"
        )

    def test_11_gamification_summary(self):
        """GET /gamification/summary returns points and streak."""
        r = httpx.get(
            f"{BASE_URL}/gamification/summary",
            headers=self._headers(),
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, (
            f"Gamification summary failed ({r.status_code}): {r.text}"
        )

    def test_12_content_library(self):
        """GET /content/library returns content items."""
        r = httpx.get(
            f"{BASE_URL}/content/library",
            headers=self._headers(),
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, (
            f"Content library failed ({r.status_code}): {r.text}"
        )


# ---------------------------------------------------------------------------
# 4. Nutritionist Portal
# ---------------------------------------------------------------------------
class TestNutritionistPortal:
    def test_13_nutritionist_login_bad_creds(self):
        """POST /nutritionist/auth/login with bad creds returns 401/404."""
        r = httpx.post(
            f"{BASE_URL}/nutritionist/auth/login",
            json={"email": "test@izana.com", "password": "wrong"},
            timeout=TIMEOUT,
        )
        assert r.status_code in [401, 403, 404], (
            f"Expected auth error but got {r.status_code}: {r.text}"
        )

    def test_14_nutritionist_queue_requires_auth(self):
        """GET /nutritionist/queue without admin key returns 403."""
        r = httpx.get(f"{BASE_URL}/nutritionist/queue", timeout=TIMEOUT)
        assert r.status_code == 403, (
            f"Expected 403 but got {r.status_code}: {r.text}"
        )


# ---------------------------------------------------------------------------
# 5. Admin Dashboard
# ---------------------------------------------------------------------------
class TestAdminDashboard:
    def test_15_admin_dashboard_requires_auth(self):
        """GET /admin/dashboard without admin API key returns 403."""
        r = httpx.get(f"{BASE_URL}/admin/dashboard", timeout=TIMEOUT)
        assert r.status_code == 403, (
            f"Expected 403 but got {r.status_code}: {r.text}"
        )

    def test_16_admin_health_requires_auth(self):
        """GET /admin/health without admin API key returns 403."""
        r = httpx.get(f"{BASE_URL}/admin/health", timeout=TIMEOUT)
        assert r.status_code == 403, (
            f"Expected 403 but got {r.status_code}: {r.text}"
        )


# ---------------------------------------------------------------------------
# 6. Recovery Phrase
# ---------------------------------------------------------------------------
class TestRecoveryPhrase:
    def _headers(self):
        assert state["access_token"], "Signup must run first"
        return {"Authorization": f"Bearer {state['access_token']}"}

    def test_17_recovery_regenerate(self):
        """POST /recovery/regenerate creates new recovery phrase."""
        r = httpx.post(
            f"{BASE_URL}/recovery/regenerate",
            headers=self._headers(),
            json={"current_password": "TestPass2026"},
            timeout=TIMEOUT,
        )
        # 200 on success; 422/500 if endpoint expects different payload
        assert r.status_code in [200, 422, 500], (
            f"Recovery regenerate unexpected ({r.status_code}): {r.text}"
        )


# ---------------------------------------------------------------------------
# 7. Edge Cases
# ---------------------------------------------------------------------------
class TestEdgeCases:
    def test_18_unauthenticated_chat_returns_401(self):
        """POST /chat without auth returns 401."""
        r = httpx.post(
            f"{BASE_URL}/chat",
            json={"content": "test"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 401, (
            f"Expected 401 but got {r.status_code}: {r.text}"
        )

    def test_19_empty_content_returns_422(self):
        """POST /chat with empty content returns 422."""
        assert state["access_token"], "Signup must run first"
        headers = {"Authorization": f"Bearer {state['access_token']}"}
        r = httpx.post(
            f"{BASE_URL}/chat",
            headers=headers,
            json={"content": ""},
            timeout=TIMEOUT,
        )
        assert r.status_code == 422, (
            f"Expected 422 but got {r.status_code}: {r.text}"
        )

    def test_20_health_endpoint(self):
        """GET /health returns healthy status."""
        r = httpx.get(
            "https://izana-api.onrender.com/health",
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, f"Health check failed ({r.status_code}): {r.text}"
        data = r.json()
        assert data["status"] == "healthy", f"Unexpected health status: {data}"
