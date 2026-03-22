"""
Feature-flag dependency for FastAPI.

Provides ``require_feature(feature_name)`` which returns a FastAPI dependency
that raises **503 Service Unavailable** when the requested feature is disabled
in ``settings``.
"""

from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, status

from app.core.config import settings


def require_feature(feature_name: str) -> Callable[..., Any]:
    """Return a FastAPI dependency that gates access behind a feature flag.

    The *feature_name* is mapped to the settings attribute
    ``FEATURE_{feature_name}_ENABLED`` (case-insensitive lookup on the name
    portion).

    Usage::

        @router.get(
            "/bloodwork",
            dependencies=[Depends(require_feature("BLOODWORK"))],
        )
        async def get_bloodwork():
            ...

    Args:
        feature_name: The short feature name, e.g. ``"BLOODWORK"``,
            ``"PARTNER"``, ``"FIE"``, or ``"PUSH"``.

    Returns:
        A FastAPI-compatible dependency callable.

    Raises:
        HTTPException 503: when the feature flag is ``False``.
        HTTPException 500: when the feature flag attribute does not exist
            on settings (programming error).
    """
    attr_name = f"FEATURE_{feature_name.upper()}_ENABLED"

    def _check_feature() -> bool:
        """Verify the feature flag is enabled."""
        try:
            enabled = getattr(settings, attr_name)
        except AttributeError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unknown feature flag: {attr_name}",
            )

        if not enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="This feature is coming soon!",
            )

        return True

    return Depends(_check_feature)
