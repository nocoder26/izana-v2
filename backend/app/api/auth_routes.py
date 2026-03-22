"""
Authentication and account-recovery API routes.

Implements four endpoints aligned with key architectural decisions:
- **Decision 6**:  GET  /auth/lookup           — constant response regardless of existence
- **Decision 7**:  POST /auth/signup           — atomic server-side transaction
- **Decision 14**: POST /recovery/regenerate   — regenerate recovery phrase (authed)
-                  POST /recovery/attempt      — password reset via recovery phrase
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import string
import time
from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, field_validator

from app.core.auth import get_user_id
from app.core.database import get_supabase_admin, get_supabase_client
from app.core.validators import sanitize_input

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# In-memory rate limiting (simple counters per IP)
# ---------------------------------------------------------------------------
# In production these should be replaced by Redis-backed middleware.

_lookup_rate: dict[str, list[float]] = defaultdict(list)
_recovery_rate: dict[str, list[float]] = defaultdict(list)

_LOOKUP_LIMIT = 10       # max requests
_LOOKUP_WINDOW = 60      # per 60 seconds
_RECOVERY_LIMIT = 3      # max attempts
_RECOVERY_WINDOW = 3600  # per hour


def _check_rate_limit(
    store: dict[str, list[float]],
    ip: str,
    limit: int,
    window: int,
) -> None:
    """Raise 429 if *ip* has exceeded *limit* requests within *window* seconds."""
    now = time.time()
    timestamps = store[ip]
    # Prune expired entries
    store[ip] = [t for t in timestamps if now - t < window]
    if len(store[ip]) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )
    store[ip].append(now)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RECOVERY_CHARSET = string.ascii_uppercase + string.digits  # A-Z 0-9


def _generate_recovery_phrase() -> str:
    """Generate a recovery phrase in the format XXXX-XXXX-XXXX-XXXX.

    Each group is 4 uppercase alphanumeric characters drawn from a
    cryptographically secure random source.
    """
    groups = []
    for _ in range(4):
        group = "".join(
            _RECOVERY_CHARSET[b % len(_RECOVERY_CHARSET)]
            for b in os.urandom(4)
        )
        groups.append(group)
    return "-".join(groups)


def _hash_phrase(phrase: str, salt: bytes | None = None) -> tuple[str, str]:
    """Hash a recovery phrase with SHA-256 and a random salt.

    Returns:
        A tuple of ``(hex_hash, hex_salt)``.
    """
    if salt is None:
        salt = os.urandom(32)
    digest = hashlib.sha256(salt + phrase.encode()).hexdigest()
    return digest, salt.hex()


# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    """Payload for creating a new Izana account."""

    pseudonym: str
    password: str
    gender: str
    avatar: str
    timezone: str

    @field_validator("pseudonym")
    @classmethod
    def validate_pseudonym(cls, v: str) -> str:
        v = v.strip()
        if not re.fullmatch(r"[A-Za-z0-9]{3,30}", v):
            raise ValueError(
                "Pseudonym must be 3-30 alphanumeric characters."
            )
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        if v not in ("Male", "Female"):
            raise ValueError("Gender must be 'Male' or 'Female'.")
        return v

    @field_validator("avatar")
    @classmethod
    def validate_avatar(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Avatar must be a non-empty string.")
        return v.strip()

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Timezone must be a non-empty string.")
        return v.strip()


class SignupResponse(BaseModel):
    """Successful signup payload returned to the client."""

    user_id: str
    access_token: str
    recovery_phrase: str
    pseudonym: str


class LookupResponse(BaseModel):
    """Constant-shape response for pseudonym lookups (Decision 6)."""

    email: str


class RegenerateRequest(BaseModel):
    """Payload for regenerating a recovery phrase."""

    current_password: str


class RegenerateResponse(BaseModel):
    """New recovery phrase returned after regeneration."""

    recovery_phrase: str


class RecoveryAttemptRequest(BaseModel):
    """Payload for resetting a password via recovery phrase."""

    pseudonym: str
    recovery_phrase: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


class RecoveryAttemptResponse(BaseModel):
    """Response after a successful password reset."""

    success: bool
    message: str


# ---------------------------------------------------------------------------
# 1. GET /auth/lookup — Decision 6
# ---------------------------------------------------------------------------

@router.get("/auth/lookup", response_model=LookupResponse)
async def auth_lookup(
    request: Request,
    pseudonym: Annotated[str, Query(min_length=1, max_length=60)],
) -> LookupResponse:
    """Look up the email address for a given pseudonym.

    **Decision 6**: This endpoint always returns the same shape
    (``200 OK``) regardless of whether the pseudonym actually exists.
    This prevents enumeration attacks — an attacker cannot distinguish
    existing accounts from non-existing ones.

    Rate limited to 10 requests per minute per IP address.
    """
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(_lookup_rate, client_ip, _LOOKUP_LIMIT, _LOOKUP_WINDOW)

    pseudonym = sanitize_input(pseudonym)
    return LookupResponse(email=f"{pseudonym}@users.izana.ai")


# ---------------------------------------------------------------------------
# 2. POST /auth/signup — Decision 7 (server-side transaction)
# ---------------------------------------------------------------------------

@router.post(
    "/auth/signup",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def auth_signup(body: SignupRequest) -> SignupResponse:
    """Create a new Izana account as an atomic server-side transaction.

    **Decision 7**: All four resources — Supabase auth user, profile row,
    gamification row, and recovery phrase — are created together. If any
    step fails, the auth user is deleted (rollback) and a clear error is
    returned.

    Returns the ``access_token`` (from an immediate sign-in), the
    one-time ``recovery_phrase``, and the ``user_id`` / ``pseudonym``.
    """
    supabase = get_supabase_client()
    admin = get_supabase_admin()

    email = f"{body.pseudonym}@users.izana.ai"
    created_user_id: str | None = None

    try:
        # Step 1: Create auth user via admin API
        try:
            auth_response = admin.auth.admin.create_user(
                {
                    "email": email,
                    "password": body.password,
                    "email_confirm": True,
                }
            )
            created_user_id = auth_response.user.id
        except Exception as exc:
            error_msg = str(exc).lower()
            if "already" in error_msg or "duplicate" in error_msg or "exists" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This pseudonym is already taken. Please choose another.",
                )
            raise

        # Step 2: Insert profile row
        supabase.table("profiles").insert(
            {
                "id": created_user_id,
                "pseudonym": body.pseudonym,
                "gender": body.gender,
                "avatar": body.avatar,
                "timezone": body.timezone,
            }
        ).execute()

        # Step 3: Insert gamification row
        supabase.table("user_gamification").insert(
            {
                "user_id": created_user_id,
                "total_points": 0,
                "current_streak": 0,
                "level": 1,
                "level_name": "Beginner",
            }
        ).execute()

        # Step 4: Generate recovery phrase
        recovery_phrase = _generate_recovery_phrase()

        # Step 5: Hash and store recovery phrase
        phrase_hash, salt_hex = _hash_phrase(recovery_phrase)
        supabase.table("recovery_phrases").insert(
            {
                "user_id": created_user_id,
                "phrase_hash": phrase_hash,
                "salt": salt_hex,
            }
        ).execute()

        # Step 6 (success path): Sign in to obtain access token
        sign_in_response = supabase.auth.sign_in_with_password(
            {"email": email, "password": body.password}
        )
        access_token = sign_in_response.session.access_token

        return SignupResponse(
            user_id=created_user_id,
            access_token=access_token,
            recovery_phrase=recovery_phrase,
            pseudonym=body.pseudonym,
        )

    except HTTPException:
        # Re-raise HTTP exceptions (e.g. 409) without rollback clobbering them
        raise

    except Exception as exc:
        # Step 6 (failure path): Rollback — delete auth user
        logger.error("Signup transaction failed, rolling back: %s", exc)
        if created_user_id:
            try:
                admin.auth.admin.delete_user(created_user_id)
            except Exception as rollback_exc:
                logger.error("Rollback failed: %s", rollback_exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account creation failed. Please try again.",
        )


# ---------------------------------------------------------------------------
# 3. POST /recovery/regenerate — Decision 14
# ---------------------------------------------------------------------------

@router.post("/recovery/regenerate", response_model=RegenerateResponse)
async def recovery_regenerate(
    body: RegenerateRequest,
    user_id: Annotated[str, Depends(get_user_id)],
) -> RegenerateResponse:
    """Regenerate the caller's recovery phrase.

    **Decision 14**: Requires the current password for verification.
    The old phrase hash is replaced (upserted) with the new one.
    """
    supabase = get_supabase_client()

    # 1. Look up pseudonym from profile
    profile_resp = (
        supabase.table("profiles")
        .select("pseudonym")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    if not profile_resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found.",
        )

    pseudonym = profile_resp.data["pseudonym"]
    email = f"{pseudonym}@users.izana.ai"

    # 2. Verify current password
    try:
        supabase.auth.sign_in_with_password(
            {"email": email, "password": body.current_password}
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect.",
        )

    # 3. Generate new phrase, hash, and upsert
    new_phrase = _generate_recovery_phrase()
    phrase_hash, salt_hex = _hash_phrase(new_phrase)

    supabase.table("recovery_phrases").upsert(
        {
            "user_id": user_id,
            "phrase_hash": phrase_hash,
            "salt": salt_hex,
        },
        on_conflict="user_id",
    ).execute()

    return RegenerateResponse(recovery_phrase=new_phrase)


# ---------------------------------------------------------------------------
# 4. POST /recovery/attempt
# ---------------------------------------------------------------------------

@router.post("/recovery/attempt", response_model=RecoveryAttemptResponse)
async def recovery_attempt(
    request: Request,
    body: RecoveryAttemptRequest,
) -> RecoveryAttemptResponse:
    """Reset a user's password using their recovery phrase.

    This endpoint is unauthenticated because the user is locked out of
    their account. Rate limited to 3 attempts per hour per IP.
    """
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(_recovery_rate, client_ip, _RECOVERY_LIMIT, _RECOVERY_WINDOW)

    supabase = get_supabase_client()
    admin = get_supabase_admin()

    # 1. Look up user by pseudonym
    profile_resp = (
        supabase.table("profiles")
        .select("id")
        .eq("pseudonym", body.pseudonym)
        .maybe_single()
        .execute()
    )
    if not profile_resp.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid recovery phrase.",
        )

    target_user_id = profile_resp.data["id"]

    # 2. Get stored hash + salt
    recovery_resp = (
        supabase.table("recovery_phrases")
        .select("phrase_hash, salt")
        .eq("user_id", target_user_id)
        .maybe_single()
        .execute()
    )
    if not recovery_resp.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid recovery phrase.",
        )

    stored_hash = recovery_resp.data["phrase_hash"]
    stored_salt = bytes.fromhex(recovery_resp.data["salt"])

    # 3. Hash submitted phrase with stored salt and compare
    submitted_hash, _ = _hash_phrase(body.recovery_phrase, salt=stored_salt)

    if submitted_hash != stored_hash:
        # Log failed attempt
        try:
            supabase.table("recovery_attempts").insert(
                {
                    "user_id": target_user_id,
                    "ip_address": client_ip,
                    "success": False,
                }
            ).execute()
        except Exception as log_exc:
            logger.warning("Failed to log recovery attempt: %s", log_exc)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid recovery phrase.",
        )

    # 4. Phrase matched — update password via admin API
    try:
        admin.auth.admin.update_user_by_id(
            target_user_id,
            {"password": body.new_password},
        )
    except Exception as exc:
        logger.error("Failed to update password for user %s: %s", target_user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed. Please try again.",
        )

    # Log successful attempt
    try:
        supabase.table("recovery_attempts").insert(
            {
                "user_id": target_user_id,
                "ip_address": client_ip,
                "success": True,
            }
        ).execute()
    except Exception as log_exc:
        logger.warning("Failed to log recovery attempt: %s", log_exc)

    return RecoveryAttemptResponse(
        success=True,
        message="Password reset. Please log in.",
    )
