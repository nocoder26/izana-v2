"""
FastAPI application entry point for the Izana Chat backend.

Creates and configures the ASGI application, wires up middleware,
mounts Prometheus instrumentation, and includes all API routers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.admin import router as admin_router
from app.api.auth_routes import router as auth_router
from app.api.bloodwork import router as bloodwork_router
from app.api.chapters import router as chapters_router
from app.api.chat import router as chat_router
from app.api.coach import router as coach_router
from app.api.companion import router as companion_router
from app.api.content import router as content_router
from app.api.jobs import router as jobs_router
from app.api.nutrition import router as nutrition_router
from app.api.nutritionist import router as nutritionist_router
from app.api.preview import router as preview_router
from app.api.privacy import router as privacy_router
from app.api.push import router as push_router
from app.api.reports import router as reports_router
from app.core.config import settings
from app.core.correlation import CorrelationMiddleware

# ── Application ───────────────────────────────────────────────────────────

app = FastAPI(
    title="Izana API",
    version="2.0",
    description="Backend API for the Izana personalised health platform.",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# ── Middleware (outermost first) ──────────────────────────────────────────

app.add_middleware(CorrelationMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Prometheus instrumentation ────────────────────────────────────────────

Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    excluded_handlers=["/health", "/metrics"],
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


# ── Health check ──────────────────────────────────────────────────────────


@app.get("/health", tags=["infra"])
async def health_check() -> dict:
    """Shallow liveness probe.

    Returns a simple JSON payload confirming the service is running and
    the current API version.  No downstream dependencies are checked
    (use a ``/ready`` endpoint for that).
    """
    return {"status": "healthy", "version": "2.0"}


# ── Routers ───────────────────────────────────────────────────────────────

# Core
app.include_router(auth_router, prefix="/api/v1", tags=["Auth"])
app.include_router(chat_router, prefix="/api/v1", tags=["Chat"])
app.include_router(preview_router, prefix="/api/v1", tags=["Preview"])

# Journey & Chapters (Stage 8)
app.include_router(chapters_router, prefix="/api/v1", tags=["Chapters"])

# Companion — Check-ins, Symptoms, Outcomes (Stage 8)
app.include_router(companion_router, prefix="/api/v1", tags=["Companion"])

# Nutrition — Plans, Meals, Activities (Stage 8)
app.include_router(nutrition_router, prefix="/api/v1", tags=["Nutrition"])

# Bloodwork (Stage 7)
app.include_router(bloodwork_router, prefix="/api/v1", tags=["Bloodwork"])

# Coach — Partner, Gamification (Stage 8)
app.include_router(coach_router, prefix="/api/v1", tags=["Coach"])

# Content Library (Stage 8)
app.include_router(content_router, prefix="/api/v1", tags=["Content"])

# Reports — Provider Portal (Stage 8)
app.include_router(reports_router, prefix="/api/v1", tags=["Reports"])

# Push Notifications (Stage 8)
app.include_router(push_router, prefix="/api/v1", tags=["Push"])

# Privacy — GDPR (Stage 8)
app.include_router(privacy_router, prefix="/api/v1", tags=["Privacy"])

# Nutritionist Portal (Stage 8)
app.include_router(nutritionist_router, prefix="/api/v1", tags=["Nutritionist"])

# Admin Dashboard (Stage 8)
app.include_router(admin_router, prefix="/api/v1", tags=["Admin"])

# Background Jobs (Stage 8)
app.include_router(jobs_router, prefix="/api/v1", tags=["Jobs"])
