"""Sprint 2 — chorale context & dashboard."""
import pytest
from django.core.cache import cache
from django.urls import reverse
from model_bakery import baker
from rest_framework.test import APIClient

from manage_chorale.models import Chorale, Membership
from manage_users.models import CustomUser


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user(db):
    return baker.make(CustomUser, is_verify=True)


@pytest.fixture
def other_user(db):
    return baker.make(CustomUser, is_verify=True)


@pytest.fixture
def chorale(db):
    return baker.make(Chorale, name="Saint Cécile")


@pytest.fixture
def auth_client(user):
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    token = RefreshToken.for_user(user).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def _membership(user, chorale, role=Membership.ROLE_MEMBER, is_admin=False):
    return baker.make(
        Membership, user=user, chorale=chorale, role=role, is_admin=is_admin
    )


# --- chorale list ---------------------------------------------------------

def test_chorale_list_returns_only_my_chorales_with_role(auth_client, user, chorale):
    _membership(user, chorale, role=Membership.ROLE_TREASURER)
    other = baker.make(Chorale, name="Autre")  # user is NOT a member

    resp = auth_client.get(reverse("api:v1:chorale_list"))
    assert resp.status_code == 200
    data = resp.json()
    slugs = [c["slug"] for c in data]
    assert chorale.slug in slugs
    assert other.slug not in slugs
    row = next(c for c in data if c["slug"] == chorale.slug)
    assert row["role"] == Membership.ROLE_TREASURER
    assert row["is_admin"] is False


def test_chorale_list_requires_auth():
    resp = APIClient().get(reverse("api:v1:chorale_list"))
    assert resp.status_code == 401


def test_chorale_list_admin_flag(auth_client, user, chorale):
    _membership(user, chorale, role=Membership.ROLE_ADMIN, is_admin=True)
    resp = auth_client.get(reverse("api:v1:chorale_list"))
    row = next(c for c in resp.json() if c["slug"] == chorale.slug)
    assert row["is_admin"] is True


# --- dashboard ------------------------------------------------------------

def test_dashboard_member_gets_stats(auth_client, user, chorale):
    _membership(user, chorale)
    url = reverse("api:v1:dashboard", kwargs={"slug": chorale.slug})
    resp = auth_client.get(url)
    assert resp.status_code == 200
    body = resp.json()
    # Shape contract — every documented key present.
    for key in (
        "total_members",
        "upcoming_event_count",
        "cash_balance",
        "cash_in_total",
        "cash_out_total",
        "contributions_collected_this_month",
        "active_contribution_count",
        "open_sanctions_count",
        "unjustified_absences_this_month",
    ):
        assert key in body
    # Money rendered as a string (Decimal), never a float.
    assert isinstance(body["cash_balance"], str)


def test_dashboard_non_member_403(auth_client, chorale):
    url = reverse("api:v1:dashboard", kwargs={"slug": chorale.slug})
    resp = auth_client.get(url)
    assert resp.status_code == 403


def test_dashboard_unknown_slug_404(auth_client):
    url = reverse("api:v1:dashboard", kwargs={"slug": "ghost-chorale"})
    resp = auth_client.get(url)
    assert resp.status_code == 404


def test_dashboard_requires_auth(chorale):
    url = reverse("api:v1:dashboard", kwargs={"slug": chorale.slug})
    resp = APIClient().get(url)
    assert resp.status_code == 401
