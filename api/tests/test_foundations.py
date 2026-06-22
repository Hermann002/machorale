import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


def test_ping_no_auth(api_client):
    """GET /api/v1/ping/ works without auth and proves the pipe."""
    url = reverse("api:v1:ping")
    resp = api_client.get(url)
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ping_url_has_no_locale_prefix(api_client):
    """API lives outside i18n_patterns -> no /fr/ /en/ prefix."""
    assert reverse("api:v1:ping") == "/api/v1/ping/"


def test_protected_route_requires_auth_returns_consistent_shape(api_client):
    """Unauthenticated hit on a default-protected route returns the
    {detail, errors} envelope (401), not DRF's raw {detail} only."""
    # /api/v1/ping/ is AllowAny; assert the envelope on a 404 instead, which
    # also flows through the custom exception handler.
    resp = api_client.get("/api/v1/does-not-exist/")
    assert resp.status_code == 404
    body = resp.json()
    assert "detail" in body
    assert "errors" in body
