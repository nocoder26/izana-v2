"""
arq worker entry point for Izana Chat background tasks.

Start the worker with::

    arq app.workers.worker.WorkerSettings

This process picks up jobs enqueued by the FastAPI application (e.g. the
chat pipeline) and executes them with a shared Redis connection that is
also used for streaming events back to the SSE endpoint.

Scheduled (cron) tasks run on fixed intervals:
- Evening summary:           daily at 20:00 UTC
- Phase transition check:    every 6 hours
- Plan overdue escalation:   every hour
- Nudge delivery:            every 5 minutes
- Disengagement sensing:     daily at 06:00 UTC
- Cache refresh:             daily at 03:00 UTC
- Data lifecycle:            daily at 02:00 UTC
"""

from arq.cron import cron

from app.core.task_queue import get_redis_settings
from app.workers.chat_tasks import chat_pipeline_task
from app.workers.scheduled_tasks import (
    cache_refresh_task,
    data_lifecycle_task,
    disengagement_sensing_task,
    evening_summary_task,
    nudge_delivery_task,
    phase_transition_check_task,
    plan_overdue_escalation_task,
)


class WorkerSettings:
    """arq worker configuration.

    Attributes:
        functions:      List of task functions the worker can execute.
        cron_jobs:      Scheduled cron tasks with their intervals.
        redis_settings: Parsed Redis connection settings from ``REDIS_URL``.
        max_jobs:       Maximum number of concurrent jobs per worker process.
        job_timeout:    Per-job timeout in seconds (2 minutes for chat).
    """

    functions = [
        chat_pipeline_task,
        evening_summary_task,
        phase_transition_check_task,
        plan_overdue_escalation_task,
        nudge_delivery_task,
        disengagement_sensing_task,
        cache_refresh_task,
        data_lifecycle_task,
    ]

    cron_jobs = [
        cron(phase_transition_check_task, hour={0, 6, 12, 18}, minute=0),
        cron(plan_overdue_escalation_task, minute=0),  # Every hour
        cron(nudge_delivery_task, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
        cron(disengagement_sensing_task, hour=6, minute=0),
        cron(cache_refresh_task, hour=3, minute=0),
        cron(data_lifecycle_task, hour=2, minute=0),
    ]

    redis_settings = get_redis_settings()
    max_jobs = 10
    job_timeout = 120  # 2 minutes max per chat pipeline execution
