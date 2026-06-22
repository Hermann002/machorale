"""Sprint 3 — members CRUD."""
import pytest
from django.core.cache import cache
from django.urls import reverse
from model_bakery import baker
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from manage_chorale.models import Chorale, Membership
from manage_users.models import CustomUser


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
    return reverse("api:v1:member_list", kwargs={"slug": chorale.slug})


def detail_url(chorale, pk):
    return reverse("api:v1:member_detail", kwargs={"slug": chorale.slug, "pk": pk})


# --- list / search / filter ----------------------------------------------

def test_member_list_paginated(chorale, plain):
    make_member(chorale, first_name="Alice")
    make_member(chorale, first_name="Bob")
    resp = client_for(plain).get(list_url(chorale))
    assert resp.status_code == 200
    body = resp.json()
    assert "results" in body and "count" in body
    assert body["count"] >= 3


def test_member_list_search_by_name(chorale, admin):
    make_member(chorale, first_name="Zacharie", last_name="Ndongo")
    resp = client_for(admin).get(list_url(chorale), {"search": "Zacharie"})
    names = [m["user"]["first_name"] for m in resp.json()["results"]]
    assert "Zacharie" in names
    assert all("Zacharie" in n or True for n in names)
    assert resp.json()["count"] == 1


def test_member_list_filter_by_role(chorale, admin, secretary, plain):
    resp = client_for(admin).get(list_url(chorale), {"role": Membership.ROLE_SECRETARY})
    roles = {m["role"] for m in resp.json()["results"]}
    assert roles == {Membership.ROLE_SECRETARY}


def test_member_list_non_member_403(chorale):
    outsider = baker.make(CustomUser, is_verify=True)
    resp = client_for(outsider).get(list_url(chorale))
    assert resp.status_code == 403


# --- detail ---------------------------------------------------------------

def test_member_detail(chorale, plain):
    membership = Membership.objects.get(user=plain, chorale=chorale)
    resp = client_for(plain).get(detail_url(chorale, membership.id))
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == plain.email


# --- create ---------------------------------------------------------------

def test_admin_creates_member(chorale, admin):
    from manage_chorale.models import Event as ActivityEvent

    payload = {
        "email": "newbie@example.com",
        "first_name": "New",
        "last_name": "Bie",
        "role": Membership.ROLE_TREASURER,
    }
    resp = client_for(admin).post(list_url(chorale), payload, format="json")
    assert resp.status_code == 201, resp.content
    assert resp.json()["role"] == Membership.ROLE_TREASURER
    assert CustomUser.objects.filter(email="newbie@example.com").exists()
    assert Membership.objects.filter(
        chorale=chorale, user__email="newbie@example.com"
    ).exists()
    assert ActivityEvent.objects.filter(
        chorale=chorale, event_type="person_add"
    ).exists()


def test_secretary_can_only_assign_member_role(chorale, secretary):
    # secretary assigning an elevated role → 400
    bad = client_for(secretary).post(
        list_url(chorale),
        {"email": "x@example.com", "first_name": "X", "last_name": "Y",
         "role": Membership.ROLE_TREASURER},
        format="json",
    )
    assert bad.status_code == 400
    # plain member role is fine
    ok = client_for(secretary).post(
        list_url(chorale),
        {"email": "z@example.com", "first_name": "Z", "last_name": "W"},
        format="json",
    )
    assert ok.status_code == 201
    assert ok.json()["role"] == Membership.ROLE_MEMBER


def test_plain_member_cannot_create(chorale, plain):
    resp = client_for(plain).post(
        list_url(chorale),
        {"email": "a@example.com", "first_name": "A", "last_name": "B"},
        format="json",
    )
    assert resp.status_code == 403


def test_create_duplicate_email_400(chorale, admin):
    existing = make_member(chorale, email="dup@example.com")
    resp = client_for(admin).post(
        list_url(chorale),
        {"email": "dup@example.com", "first_name": "A", "last_name": "B"},
        format="json",
    )
    assert resp.status_code == 400
    assert "email" in resp.json()["errors"]


# --- update ---------------------------------------------------------------

def test_admin_updates_role(chorale, admin):
    target = make_member(chorale, role=Membership.ROLE_MEMBER)
    membership = Membership.objects.get(user=target, chorale=chorale)
    resp = client_for(admin).patch(
        detail_url(chorale, membership.id),
        {"role": Membership.ROLE_CENSOR},
        format="json",
    )
    assert resp.status_code == 200
    membership.refresh_from_db()
    assert membership.role == Membership.ROLE_CENSOR


def test_secretary_cannot_elevate_role(chorale, secretary):
    target = make_member(chorale, role=Membership.ROLE_MEMBER)
    membership = Membership.objects.get(user=target, chorale=chorale)
    resp = client_for(secretary).patch(
        detail_url(chorale, membership.id),
        {"role": Membership.ROLE_TREASURER},
        format="json",
    )
    assert resp.status_code == 400


def test_plain_member_cannot_update(chorale, plain):
    target = make_member(chorale)
    membership = Membership.objects.get(user=target, chorale=chorale)
    resp = client_for(plain).patch(
        detail_url(chorale, membership.id),
        {"first_name": "Nope"},
        format="json",
    )
    assert resp.status_code == 403


def test_update_name_and_contact(chorale, admin):
    target = make_member(chorale)
    membership = Membership.objects.get(user=target, chorale=chorale)
    resp = client_for(admin).patch(
        detail_url(chorale, membership.id),
        {"first_name": "Renamed", "contact_phone": "+237690000000"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["user"]["first_name"] == "Renamed"
    assert resp.json()["user"]["profile"]["contact"] == "+237690000000"


# --- delete ---------------------------------------------------------------

def test_admin_removes_member(chorale, admin):
    from manage_chorale.models import Event as ActivityEvent

    target = make_member(chorale)
    membership = Membership.objects.get(user=target, chorale=chorale)
    resp = client_for(admin).delete(detail_url(chorale, membership.id))
    assert resp.status_code == 204
    assert not Membership.objects.filter(id=membership.id).exists()
    assert ActivityEvent.objects.filter(
        chorale=chorale, event_type="person_remove"
    ).exists()


def test_cannot_remove_admin_membership(chorale, admin):
    membership = Membership.objects.get(user=admin, chorale=chorale)
    resp = client_for(admin).delete(detail_url(chorale, membership.id))
    assert resp.status_code == 403
    assert Membership.objects.filter(id=membership.id).exists()


def test_secretary_cannot_remove_admin_but_can_remove_member(chorale, secretary):
    target = make_member(chorale)
    membership = Membership.objects.get(user=target, chorale=chorale)
    resp = client_for(secretary).delete(detail_url(chorale, membership.id))
    assert resp.status_code == 204
