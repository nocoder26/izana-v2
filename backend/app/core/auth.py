"""
Authentication dependencies for FastAPI.

Provides two dependency functions:
- ``get_user_id``  — verifies a Supabase JWT and returns the user ID.
- ``get_admin_key`` — validates a static admin API key from the request header.
"""

import jwt
import httpx
from functools import lru_cache
from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _get_jwks_client() -> jwt.PyJWKClient:
    """Create a cached JWKS client for Supabase ES256 token verification."""
    jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    return jwt.PyJWKClient(jwks_url, cache_keys=True)


async def get_user_id(request: Request) -> str:
    """Extract and verify a Supabase JWT from the ``Authorization`` header.

    Supports both:
    - **ES256** (ECDSA) — newer Supabase projects, verified via JWKS endpoint
    - **HS256** (HMAC) — legacy Supabase projects, verified via JWT_SECRET

    Returns:
        The ``sub`` claim (user ID) as a string.

    Raises:
        HTTPException 401: for missing, malformed, expired, or invalid tokens.
    """
    auth_header: str | None = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.removeprefix("Bearer ").strip()

    try:
        # Detect algorithm from token header
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")

        if alg == "ES256":
            # New Supabase: verify with JWKS public key
            jwks_client = _get_jwks_client()
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                audience="authenticated",
            )
        else:
            # Legacy Supabase: verify with shared secret
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidAudienceError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token audience",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing 'sub' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


async def get_admin_key(request: Request) -> str:
    """Verify the ``X-Admin-API-Key`` header matches the configured admin key.

    Returns:
        The validated API key string.

    Raises:
        HTTPException 403: if the header is missing or does not match.
    """
    api_key: str | None = request.headers.get("X-Admin-API-Key")

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-Admin-API-Key header",
        )

    if api_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin API key",
        )

    return api_key
