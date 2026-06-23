from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny


@api_view(["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
@permission_classes([AllowAny])
def api_not_found(request):
    """Catch-all for unmatched /api/ URLs.

    Raising DRF's NotFound routes the response through api_exception_handler so
    the client always gets the JSON {detail, errors} envelope instead of
    Django's HTML 404 page.
    """
    raise NotFound()
