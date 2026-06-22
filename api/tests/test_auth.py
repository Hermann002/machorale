"""Sprint 1 — authentication (OTP-email flow → JWT)."""
import pytest
from django.core import mail
from django.core.cache import cache
from django.urls import reverse
from model_bakery import baker
from rest_framework.test import APIClient

from manage_users.models import CustomUser, OtpCode


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def clear_ratelimit_cache():
    """django-ratelimit counters live in the shared cache; reset between tests
    so limits don't bleed across cases (the test DB is reused)."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user(db):
    return baker.make(CustomUser, email="singer@example.com", is_verify=False)


# --- OTP request ----------------------------------------------------------

def test_otp_request_known_email_sends_code(api_client, user):
    url = reverse("api:v1:otp_request")
    resp = api_client.post(url, {"email": user.email}, format="json")
    assert resp.status_code == 200
    assert OtpCode.objects.filter(user=user).exists()
    assert len(mail.outbox) == 1
    assert user.email in mail.outbox[0].to


def test_otp_request_unknown_email_is_200_and_silent(api_client, db):
    """No enumeration: unknown email still 200, but no code/email created."""
    url = reverse("api:v1:otp_request")
    resp = api_client.post(url, {"email": "ghost@example.com"}, format="json")
    assert resp.status_code == 200
    assert OtpCode.objects.count() == 0
    assert len(mail.outbox) == 0


def test_otp_request_email_case_insensitive(api_client, user):
    url = reverse("api:v1:otp_request")
    resp = api_client.post(url, {"email": "SINGER@example.com"}, format="json")
    assert resp.status_code == 200
    assert OtpCode.objects.filter(user=user).exists()


def test_otp_request_invalid_email_400(api_client, db):
    url = reverse("api:v1:otp_request")
    resp = api_client.post(url, {"email": "not-an-email"}, format="json")
    assert resp.status_code == 400
    body = resp.json()
    assert "email" in body["errors"]


# --- OTP verify -----------------------------------------------------------

def test_otp_verify_valid_code_returns_tokens(api_client, user):
    otp = OtpCode.objects.create(user=user)
    code = otp.generate_new_code()

    url = reverse("api:v1:otp_verify")
    resp = api_client.post(
        url, {"email": user.email, "code": code}, format="json"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access" in body and "refresh" in body
    assert body["user"]["email"] == user.email
    user.refresh_from_db()
    assert user.is_verify is True


def test_otp_verify_wrong_code_400(api_client, user):
    otp = OtpCode.objects.create(user=user)
    otp.generate_new_code()

    url = reverse("api:v1:otp_verify")
    resp = api_client.post(
        url, {"email": user.email, "code": "00000"}, format="json"
    )
    assert resp.status_code == 400
    assert "code" in resp.json()["errors"]


def test_otp_verify_expired_code_400(api_client, user):
    from django.utils import timezone

    otp = OtpCode.objects.create(user=user)
    code = otp.generate_new_code()
    otp.expired_at = timezone.now() - timezone.timedelta(minutes=1)
    otp.save(update_fields=["expired_at"])

    url = reverse("api:v1:otp_verify")
    resp = api_client.post(
        url, {"email": user.email, "code": code}, format="json"
    )
    assert resp.status_code == 400


def test_otp_verify_unknown_email_400(api_client, db):
    url = reverse("api:v1:otp_verify")
    resp = api_client.post(
        url, {"email": "ghost@example.com", "code": "12345"}, format="json"
    )
    assert resp.status_code == 400


def test_otp_code_single_use(api_client, user):
    """A code already verified can't be replayed."""
    otp = OtpCode.objects.create(user=user)
    code = otp.generate_new_code()
    url = reverse("api:v1:otp_verify")

    first = api_client.post(url, {"email": user.email, "code": code}, format="json")
    assert first.status_code == 200
    second = api_client.post(url, {"email": user.email, "code": code}, format="json")
    assert second.status_code == 400


# --- refresh + me ---------------------------------------------------------

def _tokens_for(api_client, user):
    otp = OtpCode.objects.create(user=user)
    code = otp.generate_new_code()
    resp = api_client.post(
        reverse("api:v1:otp_verify"),
        {"email": user.email, "code": code},
        format="json",
    )
    return resp.json()


def test_refresh_returns_new_access(api_client, user):
    tokens = _tokens_for(api_client, user)
    resp = api_client.post(
        reverse("api:v1:token_refresh"),
        {"refresh": tokens["refresh"]},
        format="json",
    )
    assert resp.status_code == 200
    assert "access" in resp.json()


def test_me_requires_auth(api_client, db):
    resp = api_client.get(reverse("api:v1:me"))
    assert resp.status_code == 401
    body = resp.json()
    assert "detail" in body and "errors" in body


def test_me_returns_current_user(api_client, user):
    tokens = _tokens_for(api_client, user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    resp = api_client.get(reverse("api:v1:me"))
    assert resp.status_code == 200
    assert resp.json()["email"] == user.email


# --- rate limiting --------------------------------------------------------

def test_otp_request_rate_limited(api_client, user):
    """5/m per email → the 6th request in the window is throttled (429)."""
    url = reverse("api:v1:otp_request")
    for _ in range(5):
        ok = api_client.post(url, {"email": user.email}, format="json")
        assert ok.status_code == 200
    blocked = api_client.post(url, {"email": user.email}, format="json")
    assert blocked.status_code == 429
    assert "detail" in blocked.json()
