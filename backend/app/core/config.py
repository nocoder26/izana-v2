"""
Central application configuration using pydantic-settings.

All environment variables are loaded here and accessed via the singleton
``settings`` instance.  Sensitive values (API keys, secrets) have no defaults
and *must* be provided through the environment or a ``.env`` file.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, validated configuration for the Izana Chat backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Supabase (Decision 1) ─────────────────────────────────────────
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str

    # ── Groq LLM ──────────────────────────────────────────────────────
    GROQ_API_KEY: str
    GROQ_API_KEYS: str = ""  # Comma-separated, parsed by get_groq_keys()
    GROQ_MAX_CONCURRENT_REQUESTS: int = 10

    # ── OpenAI ────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""

    # ── Auth / Admin ──────────────────────────────────────────────────
    ADMIN_API_KEY: str
    NUTRITIONIST_JWT_SECRET: str

    # ── Redis / Task Queue (Decision 2) ───────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"

    # ── Frontend ──────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"

    # ── Email (SendGrid + SMTP) ───────────────────────────────────────
    SENDGRID_API_KEY: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = ""

    # ── Cloudflare Stream ─────────────────────────────────────────────
    CLOUDFLARE_ACCOUNT_ID: str = ""
    CLOUDFLARE_STREAM_TOKEN: str = ""

    # ── Feature Flags (Decision 11) ───────────────────────────────────
    FEATURE_BLOODWORK_ENABLED: bool = False
    FEATURE_PARTNER_ENABLED: bool = False
    FEATURE_FIE_ENABLED: bool = False
    FEATURE_PUSH_ENABLED: bool = False

    # ── FIE (Federated Insights Engine) ───────────────────────────────
    FIE_ANONYMIZATION_SALT: str = ""
    FIE_MIN_CYCLES_FOR_INSIGHTS: int = 3

    # ── Misc ──────────────────────────────────────────────────────────
    NEXT_PUBLIC_ADMIN_EMAIL: str = ""
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # ── Validators ────────────────────────────────────────────────────

    def get_groq_keys(self) -> list[str]:
        """Parse comma-separated GROQ_API_KEYS into a list."""
        if self.GROQ_API_KEYS:
            return [k.strip() for k in self.GROQ_API_KEYS.split(",") if k.strip()]
        return [self.GROQ_API_KEY]


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` singleton.

    Using ``lru_cache`` ensures the ``.env`` file is read only once and
    the same ``Settings`` object is reused for the lifetime of the process.
    """
    return Settings()  # type: ignore[call-arg]


settings: Settings = get_settings()
