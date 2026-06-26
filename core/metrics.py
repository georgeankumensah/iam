from prometheus_client import Counter, Gauge, Histogram, generate_latest

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

pam_session_count = Gauge(
    "iam_pam_sessions_active",
    "Number of active PAM sessions",
)


def metrics_payload() -> bytes:
    return generate_latest()
