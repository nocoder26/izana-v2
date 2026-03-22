"""
Shared test fixtures for Izana backend tests.

Decision 8: Tests written alongside each stage.
Decision 19: Deterministic mock clients — no API calls in tests.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_supabase():
    """Mock Supabase client that returns predictable responses."""
    client = MagicMock()
    # Auth admin mock
    client.auth.admin.create_user = AsyncMock(return_value=MagicMock(
        user=MagicMock(id=str(uuid4()))
    ))
    # Table operations mock
    client.table = MagicMock(return_value=MagicMock(
        insert=MagicMock(return_value=MagicMock(
            execute=MagicMock(return_value=MagicMock(data=[{"id": str(uuid4())}]))
        )),
        select=MagicMock(return_value=MagicMock(
            eq=MagicMock(return_value=MagicMock(
                execute=MagicMock(return_value=MagicMock(data=[]))
            ))
        )),
    ))
    # RPC mock
    client.rpc = MagicMock(return_value=MagicMock(
        execute=MagicMock(return_value=MagicMock(data=[]))
    ))
    return client


@pytest.fixture
def mock_redis():
    """Mock Redis client for task queue tests."""
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    redis.xadd = AsyncMock()
    redis.xread = AsyncMock(return_value=[])
    redis.delete = AsyncMock()
    redis.expire = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    redis.incr = AsyncMock(return_value=1)
    return redis


@pytest.fixture
def test_user_id():
    """A consistent test user UUID."""
    return "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def test_jwt_token(test_user_id):
    """A valid JWT token for testing (Decision 1)."""
    import jwt
    from datetime import datetime, timedelta, timezone

    payload = {
        "sub": test_user_id,
        "aud": "authenticated",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
        "role": "authenticated",
    }
    return jwt.encode(payload, "test-jwt-secret", algorithm="HS256")


@pytest.fixture
def expired_jwt_token(test_user_id):
    """An expired JWT token for testing."""
    import jwt
    from datetime import datetime, timedelta, timezone

    payload = {
        "sub": test_user_id,
        "aud": "authenticated",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        "role": "authenticated",
    }
    return jwt.encode(payload, "test-jwt-secret", algorithm="HS256")


@pytest.fixture
def admin_api_key():
    """Test admin API key."""
    return "test-admin-api-key-64chars-padded-to-length-for-testing-purposes"
