"""drf-spectacular postprocessing hooks.

The operational health endpoints (``/health/live``, ``/health/ready``,
``/health/metrics``) are intentionally plain Django views rather than DRF
views: ``/health/metrics`` must emit raw Prometheus text and the others must
stay public and bypass the unified-envelope renderer.  Because they are not
DRF views, drf-spectacular cannot auto-discover them, so we inject their
contract into the generated schema here.
"""

_HEALTH_PATHS = {
    "/health/live": {
        "get": {
            "operationId": "health_live",
            "description": "Liveness probe. Always returns 200 while the process is up.",
            "tags": ["health"],
            "security": [],
            "responses": {
                "200": {
                    "description": "Process is alive.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {"status": {"type": "string", "example": "alive"}},
                            }
                        }
                    },
                }
            },
        }
    },
    "/health/ready": {
        "get": {
            "operationId": "health_ready",
            "description": "Readiness probe. Returns 503 when the database is unreachable.",
            "tags": ["health"],
            "security": [],
            "responses": {
                "200": {"description": "Dependencies reachable; ready to serve traffic."},
                "503": {"description": "A required dependency is unavailable."},
            },
        }
    },
    "/health/metrics": {
        "get": {
            "operationId": "health_metrics",
            "description": "Prometheus exposition (text/plain; version=0.0.4).",
            "tags": ["health"],
            "security": [],
            "responses": {
                "200": {
                    "description": "Prometheus metrics.",
                    "content": {"text/plain": {"schema": {"type": "string"}}},
                }
            },
        }
    },
}


def add_health_endpoints(result, generator, request, public):  # noqa: ARG001
    """Inject the plain-Django health endpoints into the OpenAPI schema."""
    result.setdefault("paths", {}).update(_HEALTH_PATHS)
    return result
