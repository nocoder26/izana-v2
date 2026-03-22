"""
Structured JSON logging configuration.

Configures the Python standard-library ``logging`` module to emit
JSON-formatted log lines suitable for ingestion by log aggregation
platforms (Datadog, Loki, CloudWatch, etc.).

Each log record includes:
- ``timestamp``      – ISO-8601 UTC timestamp
- ``level``          – log level name
- ``message``        – the log message
- ``correlation_id`` – per-request UUID (from ``correlation.py``)
- ``module``         – Python module that emitted the log
- ``function``       – function name that emitted the log

Usage::

    from app.core.logging_config import get_logger

    logger = get_logger(__name__)
    logger.info("Processing request", extra={"user_id": user_id})
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict

from app.core.config import settings
from app.core.correlation import get_correlation_id


class _JSONFormatter(logging.Formatter):
    """Format every log record as a single JSON object on one line."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialise *record* to a JSON string.

        Extra keys passed via ``extra={...}`` are merged into the
        top-level JSON object so structured data is preserved.
        """
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "correlation_id": get_correlation_id(),
            "module": record.module,
            "function": record.funcName,
        }

        # Merge any extra keys the caller supplied.
        _RESERVED = {
            "name",
            "msg",
            "args",
            "created",
            "relativeCreated",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "pathname",
            "filename",
            "module",
            "levelno",
            "levelname",
            "thread",
            "threadName",
            "process",
            "processName",
            "msecs",
            "message",
            "taskName",
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                log_entry[key] = value

        # Include exception info if present.
        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def _configure_root_logger() -> None:
    """Set up the root logger with a JSON handler writing to *stderr*.

    Called once at module import time.  Subsequent calls are no-ops
    because the handler check prevents duplicate attachment.
    """
    root = logging.getLogger()

    # Guard against duplicate handlers when the module is re-imported.
    if any(isinstance(h, logging.StreamHandler) and isinstance(h.formatter, _JSONFormatter) for h in root.handlers):
        return

    level = logging.DEBUG if settings.DEBUG else logging.INFO
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)
    handler.setFormatter(_JSONFormatter())
    root.addHandler(handler)

    # Silence noisy third-party loggers.
    for noisy in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# Eagerly configure on first import.
_configure_root_logger()


def get_logger(name: str) -> logging.Logger:
    """Return a named logger that inherits the JSON root configuration.

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A ``logging.Logger`` configured to emit structured JSON.
    """
    return logging.getLogger(name)
