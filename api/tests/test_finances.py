"""Sprint 6 — contributions catalogue, payments, cash flow."""
from datetime import date
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.urls import reverse
from model_bakery import baker
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from manage_chorale.models import (
    CashFlow,
    Chorale,
    Contribution,
    MemberContribution,
    Membership,
)
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
    membership = baker.make(
        Membership, user=user, chorale=chorale, role=role, is_admin=is_admin
    )
    return user, membership


def client_for(user):
    client = APIClient()
    token = RefreshToken.for_user(user).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def treasurer(chorale):
    return make_member(chorale, role=Membership.ROLE_TREASURER)[0]


@pytest.fixture
def plain(chorale):
    return make_member(chorale, role=Membership.ROLE_MEMBER)


def contributions_url(chorale):
    return reverse(
        "api:v1:contribution_list", kwargs={"slug": chorale.slug}
    )


def contribution_url(chorale, pk):
    return reverse(
        "api:v1:contribution_detail", kwargs={"slug": chorale.slug, "pk": pk}
    )


def payments_url(chorale, contribution):
    return reverse(
        "api:v1:payment_list",
        kwargs={"slug": chorale.slug, "pk": contribution.pk},
    )


def cashflows_url(chorale):
    return reverse("api:v1:cashflow_list", kwargs={"slug": chorale.slug})


@pytest.fixture
def contribution(chorale):
    return baker.make(
        Contribution,
        chorale=chorale,
        title="Cotisation Mensuelle",
        amount=Decimal("1000.00"),
    )


# --- contribution catalogue ---------------------------------------------------

def test_contribution_list_with_total_collected(chorale, plain, contribution):
    user = plain[0]
    baker.make(
        MemberContribution, contribution=contribution, member=user,
        amount=Decimal("600.50"),
    )
    baker.make(
        MemberContribution, contribution=contribution, member=user,
        amount=Decimal("400.00"),
    )
    resp = client_for(user).get(contributions_url(chorale))
    assert resp.status_code == 200
    row = resp.json()["results"][0]
    assert row["total_collected"] == "1000.50"  # Decimal string, no float


def test_contribution_list_is_active_filter(chorale, plain, contribution):
    baker.make(Contribution, chorale=chorale, title="Ancienne", is_active=False)
    resp = client_for(plain[0]).get(
        contributions_url(chorale), {"is_active": "true"}
    )
    titles = [c["title"] for c in resp.json()["results"]]
    assert titles == ["Cotisation Mensuelle"]


def test_treasurer_creates_contribution(chorale, treasurer):
    resp = client_for(treasurer).post(
        contributions_url(chorale),
        {"title": "Gala 2026", "amount": "2500.00",
         "target_amount": "500000.00", "description": "Concert de gala"},
        format="json",
    )
    assert resp.status_code == 201
    created = Contribution.objects.get(title="Gala 2026")
    assert created.chorale == chorale
    assert created.amount == Decimal("2500.00")


def test_duplicate_title_400(chorale, treasurer, contribution):
    resp = client_for(treasurer).post(
        contributions_url(chorale),
        {"title": "Cotisation Mensuelle", "amount": "500.00"},
        format="json",
    )
    assert resp.status_code == 400
    assert "title" in resp.json()["errors"]


def test_same_title_allowed_in_other_chorale(treasurer, chorale, contribution):
    """UniqueConstraint is per chorale — the serializer must scope its check."""
    other = baker.make(Chorale)
    baker.make(Contribution, chorale=other, title="Cotisation Mensuelle")
    resp = client_for(treasurer).patch(
        contribution_url(chorale, contribution.pk),
        {"description": "maj"},
        format="json",
    )
    assert resp.status_code == 200


def test_plain_member_cannot_create_contribution(chorale, plain):
    resp = client_for(plain[0]).post(
        contributions_url(chorale),
        {"title": "X", "amount": "100.00"},
        format="json",
    )
    assert resp.status_code == 403


def test_amount_must_be_positive(chorale, treasurer):
    resp = client_for(treasurer).post(
        contributions_url(chorale),
        {"title": "X", "amount": "0.00"},
        format="json",
    )
    assert resp.status_code == 400
    assert "amount" in resp.json()["errors"]


def test_treasurer_deletes_contribution(chorale, treasurer, contribution):
    resp = client_for(treasurer).delete(
        contribution_url(chorale, contribution.pk)
    )
    assert resp.status_code == 204
    assert not Contribution.objects.filter(pk=contribution.pk).exists()


def test_contribution_scoped_to_chorale_404(chorale, treasurer):
    foreign = baker.make(Contribution, chorale=baker.make(Chorale))
    resp = client_for(treasurer).get(contribution_url(chorale, foreign.pk))
    assert resp.status_code == 404


# --- payments -------------------------------------------------------------------

def test_treasurer_records_payment_default_amount(
    chorale, treasurer, plain, contribution
):
    user, membership = plain
    resp = client_for(treasurer).post(
        payments_url(chorale, contribution),
        {"member_id": membership.id},
        format="json",
    )
    assert resp.status_code == 201
    payment = MemberContribution.objects.get()
    assert payment.amount == contribution.amount  # service default
    assert payment.member == user
    assert payment.recorded_by == treasurer
    assert resp.json()["amount"] == "1000.00"


def test_payment_explicit_amount_and_note(chorale, treasurer, plain, contribution):
    resp = client_for(treasurer).post(
        payments_url(chorale, contribution),
        {"member_id": plain[1].id, "amount": "333.33",
         "paid_at": str(date(2026, 7, 1)), "note": "acompte"},
        format="json",
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["amount"] == "333.33"
    assert body["note"] == "acompte"
    assert body["paid_at"] == "2026-07-01"


def test_payment_unknown_member_400(chorale, treasurer, contribution):
    resp = client_for(treasurer).post(
        payments_url(chorale, contribution),
        {"member_id": 999999},
        format="json",
    )
    assert resp.status_code == 400
    assert MemberContribution.objects.count() == 0


def test_payment_member_of_other_chorale_400(chorale, treasurer, contribution):
    _, foreign = make_member(baker.make(Chorale))
    resp = client_for(treasurer).post(
        payments_url(chorale, contribution),
        {"member_id": foreign.id},
        format="json",
    )
    assert resp.status_code == 400


def test_plain_member_cannot_record_payment(chorale, plain, contribution):
    resp = client_for(plain[0]).post(
        payments_url(chorale, contribution),
        {"member_id": plain[1].id},
        format="json",
    )
    assert resp.status_code == 403


def test_payment_list_filter_by_member(chorale, treasurer, plain, contribution):
    user, membership = plain
    other_user, _ = make_member(chorale)
    baker.make(
        MemberContribution, contribution=contribution, member=user,
        amount=Decimal("100.00"),
    )
    baker.make(
        MemberContribution, contribution=contribution, member=other_user,
        amount=Decimal("200.00"),
    )
    resp = client_for(treasurer).get(
        payments_url(chorale, contribution), {"member": membership.id}
    )
    body = resp.json()
    assert body["count"] == 1
    assert body["results"][0]["member"]["id"] == user.id


def test_payment_list_readable_by_plain_member(chorale, plain, contribution):
    resp = client_for(plain[0]).get(payments_url(chorale, contribution))
    assert resp.status_code == 200


# --- cash flow --------------------------------------------------------------------

def test_cashflow_totals_math(chorale, plain):
    baker.make(
        CashFlow, chorale=chorale, type_cash_flow="entree",
        amount=Decimal("1000.10"), date=date(2026, 7, 1),
    )
    baker.make(
        CashFlow, chorale=chorale, type_cash_flow="entree",
        amount=Decimal("500.15"), date=date(2026, 7, 2),
    )
    baker.make(
        CashFlow, chorale=chorale, type_cash_flow="sortie",
        amount=Decimal("300.05"), date=date(2026, 7, 3),
    )
    resp = client_for(plain[0]).get(cashflows_url(chorale))
    totals = resp.json()["totals"]
    assert totals == {"in": "1500.25", "out": "300.05", "balance": "1200.20"}


def test_cashflow_totals_follow_filters(chorale, plain):
    baker.make(
        CashFlow, chorale=chorale, type_cash_flow="entree",
        amount=Decimal("100.00"), date=date(2026, 6, 1),
    )
    baker.make(
        CashFlow, chorale=chorale, type_cash_flow="sortie",
        amount=Decimal("40.00"), date=date(2026, 7, 5),
    )
    resp = client_for(plain[0]).get(
        cashflows_url(chorale), {"start": "2026-07-01"}
    )
    body = resp.json()
    assert body["count"] == 1
    assert body["totals"] == {"in": "0.00", "out": "40.00", "balance": "-40.00"}


def test_cashflow_type_filter_validation(chorale, plain):
    resp = client_for(plain[0]).get(cashflows_url(chorale), {"type": "nope"})
    assert resp.status_code == 400


def test_treasurer_creates_cashflow(chorale, treasurer):
    resp = client_for(treasurer).post(
        cashflows_url(chorale),
        {"title": "Location salle", "type_cash_flow": "sortie",
         "amount": "15000.00", "date": "2026-07-10"},
        format="json",
    )
    assert resp.status_code == 201
    flow = CashFlow.objects.get()
    assert flow.chorale == chorale
    assert flow.created_by == treasurer
    assert flow.amount == Decimal("15000.00")


def test_cashflow_amount_positive_required(chorale, treasurer):
    resp = client_for(treasurer).post(
        cashflows_url(chorale),
        {"title": "X", "type_cash_flow": "entree", "amount": "-5.00"},
        format="json",
    )
    assert resp.status_code == 400


def test_plain_member_cannot_create_cashflow(chorale, plain):
    resp = client_for(plain[0]).post(
        cashflows_url(chorale),
        {"title": "X", "type_cash_flow": "entree", "amount": "5.00"},
        format="json",
    )
    assert resp.status_code == 403


def test_treasurer_edits_cashflow(chorale, treasurer):
    flow = baker.make(
        CashFlow, chorale=chorale, type_cash_flow="entree",
        amount=Decimal("100.00"), date=date(2026, 7, 1),
    )
    url = reverse(
        "api:v1:cashflow_detail",
        kwargs={"slug": chorale.slug, "pk": flow.pk},
    )
    resp = client_for(treasurer).patch(
        url, {"amount": "150.00"}, format="json"
    )
    assert resp.status_code == 200
    flow.refresh_from_db()
    assert flow.amount == Decimal("150.00")


def test_cashflow_delete_not_allowed(chorale, treasurer):
    flow = baker.make(
        CashFlow, chorale=chorale, type_cash_flow="entree",
        amount=Decimal("100.00"), date=date(2026, 7, 1),
    )
    url = reverse(
        "api:v1:cashflow_detail",
        kwargs={"slug": chorale.slug, "pk": flow.pk},
    )
    resp = client_for(treasurer).delete(url)
    assert resp.status_code == 405
    assert CashFlow.objects.filter(pk=flow.pk).exists()
