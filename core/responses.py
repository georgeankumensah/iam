"""Standard API response helpers.

The UnifiedEnvelopeRenderer passes through any dict that already has a "success"
key, so these helpers produce the canonical envelope without double-wrapping:
    { success, message, data, meta?, errors? }
"""

from __future__ import annotations

from rest_framework.response import Response

from core.pagination import StandardPagination


def success_response(data=None, message="", meta=None, status_code=200) -> Response:
    payload = {
        "success": True,
        "message": message,
        "data": data,
    }
    if meta is not None:
        payload["meta"] = meta
    return Response(payload, status=status_code)


def error_response(message="", errors=None, data=None, status_code=400) -> Response:
    payload = {
        "success": False,
        "message": message,
        "data": data,
    }
    if errors is not None:
        payload["errors"] = errors
    return Response(payload, status=status_code)


def paginated_response(request, queryset, serialize, message="") -> Response:
    """Paginate a queryset/list for a function-based view and return the envelope.

    `serialize` maps the page (list of items) to JSON-ready data.
    """
    paginator = StandardPagination()
    page = paginator.paginate_queryset(queryset, request)
    data = serialize(page if page is not None else list(queryset))
    if page is None:
        return success_response(data=data, message=message)
    return success_response(
        data=data,
        message=message,
        meta={
            "page": paginator.page.number,
            "page_size": paginator.get_page_size(request),
            "total_pages": paginator.page.paginator.num_pages,
            "total_count": paginator.page.paginator.count,
        },
    )
