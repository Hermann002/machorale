from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    """Page-number pagination. Response shape:

    {"count": int, "next": url|null, "previous": url|null, "results": [...]}
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
