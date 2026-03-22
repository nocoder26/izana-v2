"""
Authentication dependencies for FastAPI.

Provides two dependency functions:
- ``get_user_id``  — verifies a Supabase JWT and returns the user ID.
- ``get_admin_key`` — validates a static admin API key from the request header.
"""

import jwt
from fastapi import HTTPException, Request, status

from app.core.config import settings


async def get_user_id(request: Request) -> str:
    """Extract and verify a Supabase JWT from the ``Authorization`` header.

    The token must:
    - be present as ``Bearer <token>``
    - be signed with **HS256** using ``SUPABASE_JWT_SECRET``
    - contain an ``"aud"`` claim equal to ``"authenticated"``
    - contain a ``"sub"`` claim (the Supabase user ID)

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
    except jwt.PyJWTError:
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
