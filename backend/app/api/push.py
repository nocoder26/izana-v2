"""
Push Notifications API routes.

Gated behind FEATURE_PUSH_ENABLED.

- GET    /push/vapid-key   — Return public VAPID key
- POST   /push/subscribe   — Save push subscription
- DELETE /push/subscribe   — Remove push subscription
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import get_user_id
from app.core.config import settings
from app.core.database import get_supabase_client
from app.core.feature_flags import require_feature

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class VapidKeyOut(BaseModel):
    """Public VAPID key for Web Push."""

    public_key: str


class PushSubscription(BaseModel):
    """Web Push subscription object from the browser."""

    endpoint: str
    keys: dict[str, str]


class SubscribeResponse(BaseModel):
    """Push subscription confirmation."""

    success: bool
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/push/vapid-key",
    response_model=VapidKeyOut,
    dependencies=[require_feature("PUSH")],
)
async def get_vapid_key(
    user_id: Annotated[str, Depends(get_user_id)],
) -> VapidKeyOut:
    """Return the public VAPID key for Web Push subscription.

    The client uses this key when calling ``pushManager.subscribe()``.
    """
    # In production, this would come from an env var / settings.
    # Placeholder for now.
    vapid_public_key = getattr(settings, "VAPID_PUBLIC_KEY", "placeholder-vapid-public-key")

    return VapidKeyOut(public_key=vapid_public_key)


@router.post(
    "/push/subscribe",
    response_model=SubscribeResponse,
    dependencies=[require_feature("PUSH")],
)
async def save_push_subscription(
    body: PushSubscription,
    user_id: Annotated[str, Depends(get_user_id)],
) -> SubscribeResponse:
    """Save a push subscription for the authenticated user.

    Uses upsert keyed on (user_id, endpoint) to avoid duplicates.
    """
    supabase = get_supabase_client()

    try:
        now = datetime.now(timezone.utc).isoformat()

        supabase.table("push_subscriptions").upsert(
            {
                "user_id": user_id,
                "endpoint": body.endpoint,
                "keys": body.keys,
                "updated_at": now,
            },
            on_conflict="user_id,endpoint",
        ).execute()

        return SubscribeResponse(
            success=True,
            message="Push subscription saved.",
        )

    except Exception as exc:
        logger.error("Failed to save push subscription: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save push subscription.",
        )


@router.delete(
    "/push/subscribe",
    response_model=SubscribeResponse,
    dependencies=[require_feature("PUSH")],
)
async def remove_push_subscription(
    body: PushSubscription,
    user_id: Annotated[str, Depends(get_user_id)],
) -> SubscribeResponse:
    """Remove a push subscription for the authenticated user."""
    supabase = get_supabase_client()

    try:
        supabase.table("push_subscriptions").delete().eq(
            "user_id", user_id
        ).eq("endpoint", body.endpoint).execute()

        return SubscribeResponse(
            success=True,
            message="Push subscription removed.",
        )

    except Exception as exc:
        logger.error("Failed to remove push subscription: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove push subscription.",
        )
