"""
arq task-queue helpers.

Wraps `arq <https://arq-docs.helpmanual.io/>`_ to provide:
- ``get_redis_settings()`` — parse ``REDIS_URL`` into arq ``RedisSettings``.
- ``get_redis_pool()``     — return (or create) a shared arq connection pool.
- ``enqueue_task()``       — enqueue a job with structured error handling.
"""

import logging
from typing import Any
from urllib.parse import urlparse

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings

from app.core.config import settings

logger = logging.getLogger(__name__)

_pool: ArqRedis | None = None


def get_redis_settings() -> RedisSettings:
    """Parse ``settings.REDIS_URL`` into an arq ``RedisSettings`` object.

    Supports standard Redis URLs of the form::

        redis://[:password@]host[:port][/db]
    """
    parsed = urlparse(settings.REDIS_URL)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        password=parsed.password,
        database=int(parsed.path.lstrip("/") or 0),
    )


async def get_redis_pool() -> ArqRedis:
    """Return a shared arq Redis connection pool.

    The pool is created lazily on the first call and reused for subsequent
    calls within the same process.
    """
    global _pool  # noqa: PLW0603
    if _pool is None:
        _pool = await create_pool(get_redis_settings())
        logger.info("arq Redis pool created")
    return _pool


async def enqueue_task(
    pool: ArqRedis,
    task_name: str,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Enqueue a background job via arq with error handling.

    Args:
        pool: An arq ``ArqRedis`` connection pool.
        task_name: The registered arq task/function name.
        *args: Positional arguments forwarded to the task.
        **kwargs: Keyword arguments forwarded to the task.

    Returns:
        The arq ``Job`` instance if enqueuing succeeds, or ``None`` on failure.
    """
    try:
        job = await pool.enqueue_job(task_name, *args, **kwargs)
        logger.info("Enqueued task %s (job_id=%s)", task_name, job.job_id if job else "duplicate")
        return job
    except Exception:
        logger.exception("Failed to enqueue task %s", task_name)
        return None
