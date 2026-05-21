"""Tests du rôle Trésorier.

Conventions :
- pytest-django + model_bakery
- Une fixture par concept (admin, treasurer, plain_member)
- Chaque test décrit UN comportement métier (pas de méga-test)
"""

import pytest
from decimal import Decimal
from django.urls import reverse
from model_bakery import baker

from manage_users.models import CustomUser
from manage_chorale.models import Chorale, Contribution, MemberContribution, CashFlow, Event, Membership
from manage_chorale.services import ContributionService


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def admin_user(db):
    return baker.make(CustomUser, is_verify=True)


@pytest.fixture
def chorale(admin_user):
    c = baker.make(Chorale, created_by=admin_user)
    Membership.objects.create(user=admin_user, chorale=c, role=Membership.ROLE_ADMIN, is_admin=True)
    return c


@pytest.fixture
def treasurer(chorale):
    user = baker.make(CustomUser, is_verify=True)
    Membership.objects.create(user=user, chorale=chorale, role=Membership.ROLE_TREASURER)
    return user


@pytest.fixture
def plain_member(chorale):
    user = baker.make(CustomUser, is_verify=True)
    Membership.objects.create(user=user, chorale=chorale, role=Membership.ROLE_MEMBER)
    return user


@pytest.fixture
def contribution(chorale):
    return baker.make(Contribution, chorale=chorale, amount=Decimal("5000"), title="Cotisation Janvier")


# ── Access control ──────────────────────────────────────────────────────


@pytest.mark.django_db
def test_plain_member_can_read_contribution_list(client, chorale, plain_member):
    client.force_login(plain_member)
    response = client.get(reverse("contributions", kwargs={"slug": chorale.slug}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_plain_member_cannot_create_contribution(client, chorale, plain_member):
    client.force_login(plain_member)
    response = client.get(reverse("contribution_create", kwargs={"slug": chorale.slug}))
    assert response.status_code == 302
    assert response.url == reverse("dashboard", kwargs={"slug": chorale.slug})


@pytest.mark.django_db
def test_treasurer_can_access_contribution_list(client, chorale, treasurer):
    client.force_login(treasurer)
    response = client.get(reverse("contributions", kwargs={"slug": chorale.slug}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_can_access_contribution_list(client, chorale, admin_user):
    client.force_login(admin_user)
    response = client.get(reverse("contributions", kwargs={"slug": chorale.slug}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_plain_member_can_read_cashflow(client, chorale, plain_member):
    client.force_login(plain_member)
    response = client.get(reverse("cashflow", kwargs={"slug": chorale.slug}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_plain_member_can_read_payments(client, chorale, plain_member):
    client.force_login(plain_member)
    response = client.get(reverse("payments", kwargs={"slug": chorale.slug}))
    assert response.status_code == 200


# ── CRUD Contribution ───────────────────────────────────────────────────


@pytest.mark.django_db
def test_treasurer_can_create_contribution(client, chorale, treasurer):
    client.force_login(treasurer)
    response = client.post(
        reverse("contribution_create", kwargs={"slug": chorale.slug}),
        {"title": "Fête de fin d'année", "amount": "10000", "target_amount": "", "description": "", "is_active": "on"},
    )
    assert response.status_code == 302
    assert Contribution.objects.filter(chorale=chorale, title="Fête de fin d'année").exists()


@pytest.mark.django_db
def test_contribution_form_rejects_duplicate_title(client, chorale, treasurer, contribution):
    client.force_login(treasurer)
    response = client.post(
        reverse("contribution_create", kwargs={"slug": chorale.slug}),
        {"title": contribution.title, "amount": "1000", "target_amount": "", "description": "", "is_active": "on"},
    )
    # Renvoyé sur le form avec erreur, pas de création
    assert response.status_code == 200
    assert Contribution.objects.filter(chorale=chorale, title=contribution.title).count() == 1


@pytest.mark.django_db
def test_contribution_form_rejects_zero_amount(client, chorale, treasurer):
    client.force_login(treasurer)
    response = client.post(
        reverse("contribution_create", kwargs={"slug": chorale.slug}),
        {"title": "Test", "amount": "0", "target_amount": "", "description": "", "is_active": "on"},
    )
    assert response.status_code == 200
    assert not Contribution.objects.filter(title="Test").exists()


@pytest.mark.django_db
def test_treasurer_can_delete_contribution(client, chorale, treasurer, contribution):
    client.force_login(treasurer)
    response = client.post(
        reverse("contribution_delete", kwargs={"slug": chorale.slug, "contribution_id": contribution.id})
    )
    assert response.status_code == 302
    assert not Contribution.objects.filter(id=contribution.id).exists()


@pytest.mark.django_db
def test_contribution_delete_get_is_idempotent(client, chorale, treasurer, contribution):
    """Un GET ne doit JAMAIS supprimer (anti-CSRF / pré-fetch crawler)."""
    client.force_login(treasurer)
    response = client.get(
        reverse("contribution_delete", kwargs={"slug": chorale.slug, "contribution_id": contribution.id})
    )
    assert response.status_code == 302
    assert Contribution.objects.filter(id=contribution.id).exists()


# ── Paiement (MemberContribution) ───────────────────────────────────────


@pytest.mark.django_db
def test_record_payment_creates_event_log(chorale, treasurer, plain_member, contribution):
    initial_events = Event.objects.filter(chorale=chorale, event_type="payment").count()
    ContributionService.record_payment(
        contribution=contribution,
        member=plain_member,
        amount=Decimal("5000"),
        recorded_by=treasurer,
    )
    assert MemberContribution.objects.filter(contribution=contribution, member=plain_member).count() == 1
    assert Event.objects.filter(chorale=chorale, event_type="payment").count() == initial_events + 1


@pytest.mark.django_db
def test_record_payment_rejects_non_member(chorale, treasurer, contribution):
    """Un user qui n'est pas dans chorale.members ne peut pas recevoir un paiement enregistré."""
    from django.core.exceptions import ValidationError
    outsider = baker.make(CustomUser)  # NOT in chorale.members
    with pytest.raises(ValidationError):
        ContributionService.record_payment(
            contribution=contribution,
            member=outsider,
            amount=Decimal("5000"),
            recorded_by=treasurer,
        )
    assert not MemberContribution.objects.filter(member=outsider).exists()


@pytest.mark.django_db
def test_record_payment_rejects_zero_amount(chorale, treasurer, plain_member, contribution):
    from django.core.exceptions import ValidationError
    with pytest.raises(ValidationError):
        ContributionService.record_payment(
            contribution=contribution,
            member=plain_member,
            amount=Decimal("0"),
            recorded_by=treasurer,
        )


@pytest.mark.django_db
def test_treasurer_can_create_payment_via_view(client, chorale, treasurer, plain_member, contribution):
    client.force_login(treasurer)
    response = client.post(
        reverse("payment_create", kwargs={"slug": chorale.slug}),
        {
            "contribution": contribution.id,
            "member": plain_member.id,
            "amount": "5000",
            "paid_at": "2026-05-15",
            "note": "Espèces",
        },
    )
    assert response.status_code == 302
    payment = MemberContribution.objects.get(contribution=contribution, member=plain_member)
    assert payment.amount == Decimal("5000")
    assert payment.recorded_by == treasurer


# ── CashFlow ────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_treasurer_can_create_cashflow(client, chorale, treasurer):
    client.force_login(treasurer)
    response = client.post(
        reverse("cashflow_create", kwargs={"slug": chorale.slug}),
        {
            "title": "Don anonyme",
            "type_cash_flow": CashFlow.TYPE_ENTREE,
            "amount": "20000",
            "date": "2026-05-10",
            "description": "",
        },
    )
    assert response.status_code == 302
    flow = CashFlow.objects.get(chorale=chorale, title="Don anonyme")
    assert flow.created_by == treasurer


@pytest.mark.django_db
def test_dashboard_stats_includes_cash_balance(chorale, treasurer):
    """Le dashboard doit refléter le solde de caisse une fois des mouvements créés."""
    from django.core.cache import cache
    from manage_chorale.services import get_dashboard_stats
    cache.clear()  # éviter qu'un test précédent ait caché un état vide
    baker.make(CashFlow, chorale=chorale, type_cash_flow=CashFlow.TYPE_ENTREE, amount=Decimal("50000"))
    baker.make(CashFlow, chorale=chorale, type_cash_flow=CashFlow.TYPE_SORTIE, amount=Decimal("15000"))
    stats = get_dashboard_stats(chorale.id)
    assert stats["cash_in_total"] == Decimal("50000")
    assert stats["cash_out_total"] == Decimal("15000")
    assert stats["cash_balance"] == Decimal("35000")
