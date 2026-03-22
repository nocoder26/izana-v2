"""
Supabase client singletons.

Provides two accessor functions:
- ``get_supabase_client()`` — a cached Supabase client initialised with the
  **service_role_key** for general backend operations.
- ``get_supabase_admin()`` — a cached Supabase admin-auth client suitable for
  privileged operations such as user creation and management.
"""

from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


@lru_cache
def get_supabase_client() -> Client:
    """Return a cached Supabase client using the service-role key.

    The service-role key bypasses Row Level Security, so this client
    should only be used in trusted backend code — never exposed to the
    frontend.
    """
    return create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_SERVICE_ROLE_KEY,
    )


@lru_cache
def get_supabase_admin() -> Client:
    """Return a cached Supabase client for admin / user-management operations.

    Under the hood this is the same ``create_client`` call (service-role key
    grants admin privileges), but keeping a separate instance makes it easy
    to swap configuration or add middleware specifically for admin flows
    without affecting the general-purpose client.
    """
    client = create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_SERVICE_ROLE_KEY,
    )
    return client
