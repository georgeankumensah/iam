try:
    from prometheus_client import Counter, Gauge, Histogram, generate_latest
    _HAVE_PROMETHEUS = True
except ModuleNotFoundError:
    _HAVE_PROMETHEUS = False

    class _NoOpMetric:
        def labels(self, **kwargs):
            return self
        def inc(self, amount=1):
            pass
        def dec(self, amount=1):
            pass
        def set(self, value):
            pass
        def observe(self, amount):
            pass

    Counter = _NoOpMetric  # type: ignore
    Gauge = _NoOpMetric  # type: ignore
    Histogram = _NoOpMetric  # type: ignore

    def generate_latest() -> bytes:  # type: ignore
        return b""

if _HAVE_PROMETHEUS:
    request_count = Counter(
        "iam_http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status"],
    )

    request_latency_seconds = Histogram(
        "iam_http_request_duration_seconds",
        "HTTP request latency in seconds",
        ["method", "endpoint"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )

    zitadel_token_size_bytes = Gauge(
        "iam_zitadel_token_size_bytes",
        "Size of Zitadel-issued ID/access tokens in bytes",
        ["token_type"],
    )

    db_connection_count = Gauge(
        "iam_db_connections_active",
        "Active database connections",
    )

    celery_task_runtime_seconds = Histogram(
        "iam_celery_task_duration_seconds",
        "Celery task runtime in seconds",
        ["task_name"],
        buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0),
    )

    backchannel_logout_failures_total = Counter(
        "iam_backchannel_logout_failures_total",
        "Total backchannel logout failures",
    )

    pam_session_count = Gauge(
        "iam_pam_sessions_active",
        "Number of active PAM sessions",
    )
else:
    request_count = _NoOpMetric()
    request_latency_seconds = _NoOpMetric()
    zitadel_token_size_bytes = _NoOpMetric()
    db_connection_count = _NoOpMetric()
    celery_task_runtime_seconds = _NoOpMetric()
    backchannel_logout_failures_total = _NoOpMetric()
    pam_session_count = _NoOpMetric()


def metrics_payload() -> bytes:
    return generate_latest()
