"""Response shapes that exist only for OpenAPI documentation (drf-spectacular).

Nothing here is used to serialize actual responses — views build those by hand.
These serializers mirror the wire format so the generated schema matches reality.
"""
from rest_framework import serializers

from .serializers import UserSerializer


class PingResponseSerializer(serializers.Serializer):
    """``{"status": "ok"}`` returned by the liveness probe."""

    status = serializers.CharField()


class DetailResponseSerializer(serializers.Serializer):
    """Plain ``{"detail": "..."}`` acknowledgement."""

    detail = serializers.CharField()


class ErrorResponseSerializer(serializers.Serializer):
    """The API-wide error envelope produced by ``api_exception_handler``:
    ``{"detail": "...", "errors": {field: [messages]}}`` (``errors`` empty for
    non-validation errors)."""

    detail = serializers.CharField()
    errors = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField())
    )


class TokenPairResponseSerializer(serializers.Serializer):
    """Successful ``auth/otp/verify`` response: JWT pair + the user."""

    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()
