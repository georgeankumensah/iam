from django.db import connection
from django.http import HttpResponse, JsonResponse


def liveness(request):  # noqa: ARG001
    return JsonResponse({"status": "alive"})


def readiness(request):  # noqa: ARG001
    try:
        connection.ensure_connection()
        return JsonResponse({"status": "ready", "database": "connected"})
    except Exception as e:
        return JsonResponse({"status": "not_ready", "error": str(e)}, status=503)


def metrics_view(request):  # noqa: ARG001
    from .metrics import metrics_payload

    return HttpResponse(metrics_payload(), content_type="text/plain; version=0.0.4")
