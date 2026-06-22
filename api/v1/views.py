from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from manage_users.models import CustomUser, OtpCode
from manage_users.utils import send_code_to_user

from . import ratelimit
from .serializers import (
    OtpRequestSerializer,
    OtpVerifySerializer,
    UserSerializer,
)


@api_view(["GET"])
@permission_classes([AllowAny])
def ping(request):
    """Liveness probe. No auth. Proves the API pipe is wired."""
    return Response({"status": "ok"})


def _token_pair(user):
    """Issue an access/refresh pair for ``user`` (simplejwt)."""
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class OtpRequestView(APIView):
    """POST ``/auth/otp/request/`` — body ``{email}``.

    Triggers the existing OTP generation + email (Celery path). **Always**
    returns 200 with the same body whether or not the email maps to a user, so
    the endpoint can't be used to enumerate registered accounts.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        ratelimit.enforce(
            request, group="api_otp_request", key=ratelimit.email_key, rate="5/m"
        )
        serializer = OtpRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = CustomUser.objects.filter(email=email).first()
        if user is not None:
            otp_record, _created = OtpCode.objects.get_or_create(user=user)
            code = otp_record.generate_new_code()
            send_code_to_user(email=user.email, code=code)

        return Response(
            {"detail": _("If the email exists, a code has been sent.")},
            status=status.HTTP_200_OK,
        )


class OtpVerifyView(APIView):
    """POST ``/auth/otp/verify/`` — body ``{email, code}``.

    Verifies via the existing ``OtpCode.verify_code`` logic. On success marks
    the user verified (mirroring the web flow) and returns the token pair plus
    the serialized user.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        ratelimit.enforce(
            request, group="api_otp_verify", key=ratelimit.email_key, rate="5/m"
        )
        serializer = OtpVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]

        invalid = ValidationError({"code": [_("Invalid or expired code.")]})
        user = CustomUser.objects.filter(email=email).first()
        if user is None:
            raise invalid

        otp_record = (
            OtpCode.objects.filter(user=user).order_by("-created_at").first()
        )
        if otp_record is None or not otp_record.verify_code(code):
            raise invalid

        if not user.is_verify:
            user.is_verify = True
            user.save(update_fields=["is_verify"])

        tokens = _token_pair(user)
        return Response(
            {**tokens, "user": UserSerializer(user).data},
            status=status.HTTP_200_OK,
        )


class RefreshView(TokenRefreshView):
    """POST ``/auth/refresh/`` — body ``{refresh}`` → new ``{access}`` (and a
    rotated ``refresh`` since ``ROTATE_REFRESH_TOKENS`` is on). Public: the
    refresh token itself is the credential."""

    permission_classes = [AllowAny]


class MeView(APIView):
    """GET ``/auth/me/`` — the authenticated user's profile."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)
