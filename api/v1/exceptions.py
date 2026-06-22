"""Consistent error shape for the whole API.

Every handled error returns:

    {"detail": "<human message>", "errors": {<field>: [<msg>, ...], ...}}

`errors` is empty for non-validation errors (auth, permission, 404, throttle).
"""
from django.utils.translation import gettext_lazy as _
from rest_framework.views import exception_handler as drf_exception_handler


def api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        # Unhandled exception -> let Django produce the 500 (no leak in prod).
        return None

    data = response.data
    detail = None
    errors = {}

    if isinstance(data, dict):
        if list(data.keys()) == ["detail"]:
            detail = data["detail"]
        else:
            errors = data
            detail = _("Validation error.")
    elif isinstance(data, list):
        errors = {"non_field_errors": data}
        detail = _("Validation error.")
    else:
        detail = str(data)

    response.data = {
        "detail": str(detail) if detail is not None else _("Error."),
        "errors": errors,
    }
    return response
