"""
Prometheus business metrics for the Izana Chat backend.

All metrics are defined once at module level and exposed through thin
helper functions so that call-sites stay concise and import only what
they need.

Metric naming follows the Prometheus convention:
``<namespace>_<subsystem>_<unit>_<suffix>``

Usage::

    from app.core.metrics import record_chat_request

    record_chat_request(status="success")
"""

from prometheus_client import Counter, Gauge, Histogram

# ── Counters ──────────────────────────────────────────────────────────────

chat_requests_total = Counter(
    "izana_chat_requests_total",
    "Total number of chat requests processed.",
    labelnames=["status"],
)

plan_generation_total = Counter(
    "izana_plan_generation_total",
    "Total number of plans generated.",
    labelnames=["status"],
)

bloodwork_uploads_total = Counter(
    "izana_bloodwork_uploads_total",
    "Total number of bloodwork file uploads.",
)

swarm_errors_total = Counter(
    "izana_swarm_errors_total",
    "Total number of errors raised inside agent swarms.",
    labelnames=["swarm_id", "error_type"],
)

# ── Histograms ────────────────────────────────────────────────────────────

chat_latency_seconds = Histogram(
    "izana_chat_latency_seconds",
    "Latency of chat request handling in seconds.",
    labelnames=["swarm_id"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

plan_approval_latency_seconds = Histogram(
    "izana_plan_approval_latency_seconds",
    "Time between plan generation and user approval in seconds.",
    buckets=(1.0, 5.0, 15.0, 30.0, 60.0, 300.0, 900.0, 3600.0),
)

# ── Gauges ────────────────────────────────────────────────────────────────

active_users_gauge = Gauge(
    "izana_active_users",
    "Number of currently active (connected) users.",
)

queue_depth_gauge = Gauge(
    "izana_queue_depth",
    "Current depth of internal task queues.",
    labelnames=["queue_type"],
)


# ── Helper functions ─────────────────────────────────────────────────────


def record_chat_request(status: str) -> None:
    """Increment the chat-request counter.

    Args:
        status: Outcome label, e.g. ``"success"`` or ``"error"``.
    """
    chat_requests_total.labels(status=status).inc()


def observe_chat_latency(swarm_id: str, seconds: float) -> None:
    """Record a chat-request latency observation.

    Args:
        swarm_id: Identifier of the swarm that handled the request.
        seconds:  Duration in seconds.
    """
    chat_latency_seconds.labels(swarm_id=swarm_id).observe(seconds)


def record_plan_generation(status: str) -> None:
    """Increment the plan-generation counter.

    Args:
        status: Outcome label, e.g. ``"success"`` or ``"error"``.
    """
    plan_generation_total.labels(status=status).inc()


def observe_plan_approval_latency(seconds: float) -> None:
    """Record the time between plan creation and approval.

    Args:
        seconds: Duration in seconds.
    """
    plan_approval_latency_seconds.observe(seconds)


def record_bloodwork_upload() -> None:
    """Increment the bloodwork-upload counter."""
    bloodwork_uploads_total.inc()


def set_active_users(count: int) -> None:
    """Set the active-users gauge to an absolute value.

    Args:
        count: Current number of connected users.
    """
    active_users_gauge.set(count)


def increment_active_users() -> None:
    """Increment the active-users gauge by one."""
    active_users_gauge.inc()


def decrement_active_users() -> None:
    """Decrement the active-users gauge by one."""
    active_users_gauge.dec()


def record_swarm_error(swarm_id: str, error_type: str) -> None:
    """Increment the swarm-error counter.

    Args:
        swarm_id:   Identifier of the swarm that raised the error.
        error_type: Categorised error type, e.g. ``"timeout"``, ``"llm_error"``.
    """
    swarm_errors_total.labels(swarm_id=swarm_id, error_type=error_type).inc()


def set_queue_depth(queue_type: str, depth: int) -> None:
    """Set the queue-depth gauge for a specific queue.

    Args:
        queue_type: Name of the queue, e.g. ``"chat"``, ``"bloodwork"``.
        depth:      Current number of items in the queue.
    """
    queue_depth_gauge.labels(queue_type=queue_type).set(depth)
