from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import AuditEvent
from .serializers import AuditEventSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search_audit(request):
    queryset = AuditEvent.objects.all()

    if request.query_params.get("actor_user_id"):
        queryset = queryset.filter(actor_user_id=request.query_params["actor_user_id"])
    if request.query_params.get("action"):
        queryset = queryset.filter(action__icontains=request.query_params["action"])
    if request.query_params.get("entity_type"):
        queryset = queryset.filter(entity_type=request.query_params["entity_type"])
    if request.query_params.get("channel"):
        queryset = queryset.filter(channel=request.query_params["channel"])
    if request.query_params.get("from"):
        queryset = queryset.filter(timestamp__gte=request.query_params["from"])
    if request.query_params.get("to"):
        queryset = queryset.filter(timestamp__lte=request.query_params["to"])

    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("page_size", 50))
    start = (page - 1) * page_size
    end = start + page_size

    total = queryset.count()
    results = queryset[start:end]

    serializer = AuditEventSerializer(results, many=True)
    return Response({
        "success": True,
        "data": serializer.data,
        "meta": {
            "page": page,
            "page_size": page_size,
            "total": total,
        },
    })
