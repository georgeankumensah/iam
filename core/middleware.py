import time
import uuid
from collections import defaultdict

from django.conf import settings
from django.http import JsonResponse


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.attempts: dict[str, list[float]] = defaultdict(list)

    def __call__(self, request):
        if self._is_rate_limited(request):
            return JsonResponse(
                {"success": False, "message": "Rate limit exceeded", "errors": {"code": "RATE_LIMIT_HIT"}},
                status=429,
            )
        response = self.get_response(request)
        return response

    def _is_rate_limited(self, request) -> bool:
        path = request.path_info
        if not any(p in path for p in getattr(settings, "RATE_LIMIT_PATHS", ["/login/", "/password-reset/"])):
            return False
        ip = request.META.get("REMOTE_ADDR", "unknown")
        now = time.time()
        window = getattr(settings, "RATE_LIMIT_WINDOW", 60)
        max_attempts = getattr(settings, "RATE_LIMIT_MAX_ATTEMPTS", 20)
        self.attempts[ip] = [t for t in self.attempts[ip] if now - t < window]
        if len(self.attempts[ip]) >= max_attempts:
            return True
        self.attempts[ip].append(now)
        return False


class CorrelationIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        correlation_id = request.META.get(
            "HTTP_X_CORRELATION_ID",
            request.META.get("HTTP_X_REQUEST_ID", str(uuid.uuid4())),
        )
        request.correlation_id = correlation_id
        response = self.get_response(request)
        response["X-Correlation-ID"] = correlation_id
        return response


class MetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        latency = time.monotonic() - start
        endpoint = request.resolver_match.view_name if request.resolver_match else request.path
        from .metrics import request_count, request_latency_seconds

        request_count.labels(method=request.method, endpoint=endpoint, status=response.status_code).inc()
        request_latency_seconds.labels(method=request.method, endpoint=endpoint).observe(latency)
        return response


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["X-XSS-Protection"] = "1; mode=block"
        response["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response["Cache-Control"] = "no-store"
        response["Pragma"] = "no-cache"
        return response
