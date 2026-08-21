"""Sprint 4 — events CRUD with date-range querying."""
from datetime import timedelta

import pytest
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from manage_chorale.models import Chorale, ChoraleEvent, Membership
from manage_chorale.models import Event as ActivityEvent
from manage_users.models import CustomUser

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def chorale(db):
    return baker.make(Chorale, name="Saint Cécile")


def make_member(chorale, role=Membership.ROLE_MEMBER, is_admin=False, **user_kw):
    user = baker.make(CustomUser, is_verify=True, **user_kw)
    baker.make(
        Membership, user=user, chorale=chorale, role=role, is_admin=is_admin
    )
    return user


def client_for(user):
    client = APIClient()
    token = RefreshToken.for_user(user).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def admin(chorale):
    return make_member(chorale, role=Membership.ROLE_ADMIN, is_admin=True)


@pytest.fixture
def secretary(chorale):
    return make_member(chorale, role=Membership.ROLE_SECRETARY)


@pytest.fixture
def plain(chorale):
    return make_member(chorale, role=Membership.ROLE_MEMBER)


def list_url(chorale):
    return reverse("api:v1:event_list", kwargs={"slug": chorale.slug})


def detail_url(chorale, pk):
    return reverse("api:v1:event_detail", kwargs={"slug": chorale.slug, "pk": pk})


def make_event(chorale, days_ahead=7, **kw):
    return baker.make(
        ChoraleEvent,
        chorale=chorale,
        date=timezone.now() + timedelta(days=days_ahead),
        **kw,
    )


def payload(days_ahead=7, **overrides):
    body = {
        "title": "Répétition générale",
        "description": "Avant le concert",
        "location": "Paroisse",
        "date": (timezone.now() + timedelta(days=days_ahead)).isoformat(),
        "event_type": "practice",
    }
    body.update(overrides)
    return body


# --- list / filters --------------------------------------------------------

def test_event_list_paginated_ordered(chorale, plain):
    make_event(chorale, days_ahead=10, title="B")
    make_event(chorale, days_ahead=2, title="A")
    resp = client_for(plain).get(list_url(chorale))
    assert resp.status_code == 200
    body = resp.json()
    assert "results" in body and body["count"] == 2
    assert [e["title"] for e in body["results"]] == ["A", "B"]


def test_event_list_excludes_other_chorales(chorale, plain):
    other = baker.make(Chorale, name="Autre")
    make_event(other)
    make_event(chorale)
    resp = client_for(plain).get(list_url(chorale))
    assert resp.json()["count"] == 1


def test_event_list_range_filter(chorale, plain):
    inside = make_event(chorale, days_ahead=5)
    make_event(chorale, days_ahead=40)
    start = timezone.now().date().isoformat()
    end = (timezone.now() + timedelta(days=10)).date().isoformat()
    resp = client_for(plain).get(list_url(chorale), {"start": start, "end": end})
    ids = [e["id"] for e in resp.json()["results"]]
    assert ids == [inside.id]


def test_event_list_end_is_inclusive(chorale, plain):
    event = make_event(chorale, days_ahead=3)
    end = event.date.date().isoformat()
    resp = client_for(plain).get(list_url(chorale), {"end": end})
    assert [e["id"] for e in resp.json()["results"]] == [event.id]


def test_event_list_month_filter(chorale, plain):
    event = make_event(chorale, days_ahead=45)
    month = event.date.strftime("%Y-%m")
    resp = client_for(plain).get(list_url(chorale), {"month": month})
    assert [e["id"] for e in resp.json()["results"]] == [event.id]


def test_event_list_type_filter(chorale, plain):
    make_event(chorale, event_type="practice")
    concert = make_event(chorale, event_type="concert")
    resp = client_for(plain).get(list_url(chorale), {"type": "concert"})
    assert [e["id"] for e in resp.json()["results"]] == [concert.id]


def test_event_list_bad_filters_400(chorale, plain):
    client = client_for(plain)
    assert client.get(list_url(chorale), {"start": "nope"}).status_code == 400
    assert client.get(list_url(chorale), {"month": "2026-13"}).status_code == 400
    assert client.get(list_url(chorale), {"type": "party"}).status_code == 400


def test_event_list_non_member_403(chorale):
    outsider = baker.make(CustomUser, is_verify=True)
    resp = client_for(outsider).get(list_url(chorale))
    assert resp.status_code == 403


# --- create ----------------------------------------------------------------

def test_secretary_creates_event(chorale, secretary):
    resp = client_for(secretary).post(
        list_url(chorale), payload(), format="json"
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Répétition générale"
    assert body["is_upcoming"] is True
    event = ChoraleEvent.objects.get(pk=body["id"])
    assert event.chorale == chorale
    assert event.created_by == secretary
    assert ActivityEvent.objects.filter(
        chorale=chorale, metadata__event_id=event.id
    ).exists()


def test_admin_creates_event(chorale, admin):
    resp = client_for(admin).post(list_url(chorale), payload(), format="json")
    assert resp.status_code == 201


def test_plain_member_cannot_create(chorale, plain):
    resp = client_for(plain).post(list_url(chorale), payload(), format="json")
    assert resp.status_code == 403
    assert ChoraleEvent.objects.count() == 0


def test_create_past_date_400(chorale, secretary):
    resp = client_for(secretary).post(
        list_url(chorale), payload(days_ahead=-2), format="json"
    )
    assert resp.status_code == 400
    assert "date" in resp.json()["errors"]


def test_create_negative_amount_400(chorale, secretary):
    resp = client_for(secretary).post(
        list_url(chorale), payload(expenses="-5.00"), format="json"
    )
    assert resp.status_code == 400
    assert "expenses" in resp.json()["errors"]


# --- detail / update / delete ----------------------------------------------

def test_event_detail(chorale, plain):
    event = make_event(chorale, title="Concert de Noël")
    resp = client_for(plain).get(detail_url(chorale, event.pk))
    assert resp.status_code == 200
    assert resp.json()["title"] == "Concert de Noël"


def test_event_detail_scoped_to_chorale_404(chorale, plain):
    other_event = make_event(baker.make(Chorale))
    resp = client_for(plain).get(detail_url(chorale, other_event.pk))
    assert resp.status_code == 404


def test_secretary_updates_event(chorale, secretary):
    event = make_event(chorale)
    resp = client_for(secretary).patch(
        detail_url(chorale, event.pk), {"title": "Nouveau titre"}, format="json"
    )
    assert resp.status_code == 200
    event.refresh_from_db()
    assert event.title == "Nouveau titre"


def test_update_keeps_past_date_allowed(chorale, secretary):
    """Filling in finances after the event: unchanged past date is tolerated."""
    event = make_event(chorale, days_ahead=-3)
    resp = client_for(secretary).patch(
        detail_url(chorale, event.pk),
        {"date": event.date.isoformat(), "expenses": "1500.00"},
        format="json",
    )
    assert resp.status_code == 200
    event.refresh_from_db()
    assert str(event.expenses) == "1500.00"


def test_update_to_new_past_date_400(chorale, secretary):
    event = make_event(chorale)
    past = (timezone.now() - timedelta(days=1)).isoformat()
    resp = client_for(secretary).patch(
        detail_url(chorale, event.pk), {"date": past}, format="json"
    )
    assert resp.status_code == 400


def test_plain_member_cannot_update(chorale, plain):
    event = make_event(chorale)
    resp = client_for(plain).patch(
        detail_url(chorale, event.pk), {"title": "X"}, format="json"
    )
    assert resp.status_code == 403


def test_secretary_deletes_event(chorale, secretary):
    event = make_event(chorale)
    resp = client_for(secretary).delete(detail_url(chorale, event.pk))
    assert resp.status_code == 204
    assert not ChoraleEvent.objects.filter(pk=event.pk).exists()


def test_plain_member_cannot_delete(chorale, plain):
    event = make_event(chorale)
    resp = client_for(plain).delete(detail_url(chorale, event.pk))
    assert resp.status_code == 403
    assert ChoraleEvent.objects.filter(pk=event.pk).exists()
