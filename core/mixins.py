from core.responses import success_response


class SuccessResponseListMixin:
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated = self.paginator.get_paginated_response(serializer.data)
            return success_response(data={
                "count": paginated.data["count"],
                "next": paginated.data.get("next"),
                "previous": paginated.data.get("previous"),
                "results": paginated.data["results"],
            })
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data={"results": serializer.data})
