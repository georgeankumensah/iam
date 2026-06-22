from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 1000

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ("success", True),
            ("message", None),
            ("data", data),
            ("meta", OrderedDict([
                ("page", self.page.number),
                ("page_size", self.get_page_size(self.request)),
                ("total_pages", self.page.paginator.num_pages),
                ("total_count", self.page.paginator.count),
            ])),
            ("errors", None),
        ]))
