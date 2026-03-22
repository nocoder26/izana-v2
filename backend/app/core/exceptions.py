"""
Custom exception hierarchy for the Izana Chat backend.

Every exception inherits from IzanaError and carries:
  - status_code  : the HTTP status code to return to the client
  - user_message : a human-friendly string safe to show in the UI
"""

from __future__ import annotations


class IzanaError(Exception):
    """Base exception for all Izana application errors."""

    status_code: int = 500
    user_message: str = "Something went wrong. Please try again."

    def __init__(self, detail: str | None = None, *, user_message: str | None = None):
        self.detail = detail or self.user_message
        if user_message is not None:
            self.user_message = user_message
        super().__init__(self.detail)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(status_code={self.status_code}, detail={self.detail!r})"


# ---------------------------------------------------------------------------
# Validation & Input
# ---------------------------------------------------------------------------

class ValidationError(IzanaError):
    """Raised when user input fails validation rules."""

    status_code = 422
    user_message = "The information you provided doesn't look right. Please check and try again."


class ContentNotFoundError(IzanaError):
    """Raised when requested content (articles, videos, etc.) cannot be located."""

    status_code = 404
    user_message = "We couldn't find that content. It may have been removed."


class BiomarkerNotFoundError(IzanaError):
    """Raised when a referenced biomarker does not exist in our registry."""

    status_code = 404
    user_message = "We don't recognise that biomarker. Please double-check the name."


class NotFoundError(IzanaError):
    """Generic resource-not-found error."""

    status_code = 404
    user_message = "The resource you're looking for doesn't exist."


# ---------------------------------------------------------------------------
# Authentication & Authorization
# ---------------------------------------------------------------------------

class AuthenticationError(IzanaError):
    """Raised when authentication credentials are missing or invalid."""

    status_code = 401
    user_message = "Please sign in to continue."


class AuthorizationError(IzanaError):
    """Raised when the authenticated user lacks the required permissions."""

    status_code = 403
    user_message = "You don't have permission to perform this action."


class AccountLockedError(IzanaError):
    """Raised when a user account has been locked (e.g. too many failed attempts)."""

    status_code = 403
    user_message = "Your account has been temporarily locked. Please try again later or contact support."


# ---------------------------------------------------------------------------
# Rate Limiting & Throttling
# ---------------------------------------------------------------------------

class RateLimitError(IzanaError):
    """Raised when the caller has exceeded the allowed request rate."""

    status_code = 429
    user_message = "You're sending messages too quickly. Please wait a moment and try again."


# ---------------------------------------------------------------------------
# External Service & Infrastructure
# ---------------------------------------------------------------------------

class ExternalServiceError(IzanaError):
    """Raised when an external service (Groq, Supabase, etc.) returns an error."""

    status_code = 502
    user_message = "One of our services is temporarily unavailable. Please try again shortly."


class TimeoutError(IzanaError):
    """Raised when an operation exceeds its allowed duration."""

    status_code = 504
    user_message = "The request took too long. Please try again."


class StorageError(IzanaError):
    """Raised when a file storage operation (upload, download, delete) fails."""

    status_code = 502
    user_message = "We had trouble saving your file. Please try again."


class PushError(IzanaError):
    """Raised when a push notification fails to deliver."""

    status_code = 502
    user_message = "We couldn't send you a notification. Please check your notification settings."


class EmailError(IzanaError):
    """Raised when an email delivery fails."""

    status_code = 502
    user_message = "We couldn't send the email. Please try again later."


# ---------------------------------------------------------------------------
# LLM Output Failures  (Decision 5)
# ---------------------------------------------------------------------------

class EmptyResponseError(IzanaError):
    """Raised when the LLM returns an empty or blank response."""

    status_code = 502
    user_message = "I wasn't able to generate a response. Please try again."


class RefusalError(IzanaError):
    """Raised when the LLM explicitly refuses to answer (safety filter, off-topic, etc.)."""

    status_code = 422
    user_message = "I'm not able to help with that request. Please ask something related to your fertility journey."


# ---------------------------------------------------------------------------
# Groq Key Rotation
# ---------------------------------------------------------------------------

class AllKeysExhaustedError(IzanaError):
    """Raised when every available Groq API key has been rate-limited or failed."""

    status_code = 503
    user_message = "Our AI service is experiencing heavy traffic. Please try again in a minute."


# ---------------------------------------------------------------------------
# Bloodwork / OCR
# ---------------------------------------------------------------------------

class AllOCRFailedError(IzanaError):
    """Raised when all OCR attempts for a bloodwork document have failed."""

    status_code = 422
    user_message = "We couldn't read your lab results. Please upload a clearer image or PDF."


class PDFReadError(IzanaError):
    """Raised when a PDF file cannot be parsed or is corrupted."""

    status_code = 422
    user_message = "We couldn't read this PDF. Please make sure the file isn't damaged and try again."


# ---------------------------------------------------------------------------
# Plan Lifecycle
# ---------------------------------------------------------------------------

class PlanNotReadyError(IzanaError):
    """Raised when a plan is accessed before it has been approved by a nutritionist."""

    status_code = 409
    user_message = "Your plan is still being reviewed. You'll be notified once it's ready."


class PlanExpiredError(IzanaError):
    """Raised when a user attempts to use a plan that is past its validity window."""

    status_code = 410
    user_message = "This plan has expired. A new one will be generated for your current phase."


# ---------------------------------------------------------------------------
# Recovery & Account
# ---------------------------------------------------------------------------

class RecoveryError(IzanaError):
    """Raised when an account recovery flow fails (bad token, expired link, etc.)."""

    status_code = 400
    user_message = "The recovery link is invalid or has expired. Please request a new one."


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

class ForeignKeyViolationError(IzanaError):
    """Raised when a database operation violates a foreign key constraint."""

    status_code = 409
    user_message = "This action conflicts with existing data. Please refresh and try again."


# ---------------------------------------------------------------------------
# Feature Flags
# ---------------------------------------------------------------------------

class FeatureDisabledError(IzanaError):
    """Raised when a user tries to access a feature that is currently turned off."""

    status_code = 403
    user_message = "This feature is not available right now. Please check back later."
