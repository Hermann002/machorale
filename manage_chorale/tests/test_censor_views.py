"""Tests du rôle Censeur.

Couvre :
- access control (mêmes garanties que trésorier mais pour le rôle censor)
- bulk absence : idempotence, constraint d'unicité
- sanction : validation type/amount, audit log, levée
- dashboard stats : open_sanctions_count
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta

from django.urls import reverse
from django.utils import timezone
from django.db import IntegrityError
from model_bakery import baker

from manage_users.models import CustomUser
from manage_chorale.models import (
    Chorale, ChoraleEvent, Absence, Sanction, Event, Membership,
)
from manage_chorale.services import SanctionService


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
def censor(chorale):
    user = baker.make(CustomUser, is_verify=True)
    Membership.objects.create(user=user, chorale=chorale, role=Membership.ROLE_CENSOR)
    return user


@pytest.fixture
def plain_member(chorale):
    user = baker.make(CustomUser, is_verify=True)
    Membership.objects.create(user=user, chorale=chorale, role=Membership.ROLE_MEMBER)
    return user


@pytest.fixture
def practice(chorale):
    return baker.make(
        ChoraleEvent,
        chorale=chorale,
        title="Répétition test",
        event_type='practice',
        date=timezone.now() - timedelta(days=1),
    )


# ── Access control ──────────────────────────────────────────────────────


@pytest.mark.django_db
def test_plain_member_can_read_absences(client, chorale, plain_member):
    client.force_login(plain_member)
    response = client.get(reverse("absences", kwargs={"slug": chorale.slug}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_plain_member_cannot_create_absence(client, chorale, plain_member):
    client.force_login(plain_member)
    response = client.get(reverse("absence_bulk_create", kwargs={"slug": chorale.slug}))
    assert response.status_code == 302
    assert response.url == reverse("dashboard", kwargs={"slug": chorale.slug})


@pytest.mark.django_db
def test_censor_can_access_absences(client, chorale, censor):
    client.force_login(censor)
    response = client.get(reverse("absences", kwargs={"slug": chorale.slug}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_can_access_sanctions(client, chorale, admin_user):
    """L'admin de chorale bypasse RoleRequireMixin via la branche super_admin."""
    client.force_login(admin_user)
    response = client.get(reverse("sanctions", kwargs={"slug": chorale.slug}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_plain_member_can_read_sanctions(client, chorale, plain_member):
    client.force_login(plain_member)
    response = client.get(reverse("sanctions", kwargs={"slug": chorale.slug}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_plain_member_cannot_create_sanction(client, chorale, plain_member):
    client.force_login(plain_member)
    response = client.get(reverse("sanction_create", kwargs={"slug": chorale.slug}))
    assert response.status_code == 302


# ── Bulk absence ────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_bulk_absence_creates_records(client, chorale, censor, plain_member, practice):
    other = baker.make(CustomUser, is_verify=True)
    Membership.objects.create(user=other, chorale=chorale, role=Membership.ROLE_MEMBER)
    client.force_login(censor)
    response = client.post(
        reverse("absence_bulk_create", kwargs={"slug": chorale.slug}),
        {
            "event": practice.id,
            "absent_members": [plain_member.id, other.id],
            "reason": "Maladie",
            "is_justified": "on",
        },
    )
    assert response.status_code == 302
    assert Absence.objects.filter(event=practice).count() == 2
    a = Absence.objects.get(event=practice, member=plain_member)
    assert a.reason == "Maladie"
    assert a.is_justified is True
    assert a.recorded_by == censor


@pytest.mark.django_db
def test_bulk_absence_is_idempotent(client, chorale, censor, plain_member, practice):
    """Relancer la saisie écrase l'état précédent (delete + bulk_create)."""
    # Premier passage : 1 absent
    client.force_login(censor)
    client.post(
        reverse("absence_bulk_create", kwargs={"slug": chorale.slug}),
        {"event": practice.id, "absent_members": [plain_member.id], "reason": "test"},
    )
    assert Absence.objects.filter(event=practice).count() == 1

    # Second passage : 0 absent → tout doit être effacé
    client.post(
        reverse("absence_bulk_create", kwargs={"slug": chorale.slug}),
        {"event": practice.id, "absent_members": [], "reason": ""},
    )
    assert Absence.objects.filter(event=practice).count() == 0


@pytest.mark.django_db
def test_absence_unique_constraint_per_event_member(chorale, plain_member, practice):
    """La DB doit empêcher deux absences pour la même paire (event, member)."""
    Absence.objects.create(event=practice, member=plain_member)
    with pytest.raises(IntegrityError):
        Absence.objects.create(event=practice, member=plain_member)


# ── Sanction ────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_sanction_create_warning_no_amount_required(client, chorale, censor, plain_member):
    client.force_login(censor)
    response = client.post(
        reverse("sanction_create", kwargs={"slug": chorale.slug}),
        {
            "member": plain_member.id,
            "sanction_type": Sanction.SANCTION_WARNING,
            "reason": "Comportement inapproprié",
            "applied_at": date.today().isoformat(),
            "amount": "",
            "is_paid": "",
        },
    )
    assert response.status_code == 302
    s = Sanction.objects.get(member=plain_member)
    assert s.sanction_type == Sanction.SANCTION_WARNING
    assert s.amount is None


@pytest.mark.django_db
def test_sanction_create_fine_requires_amount(client, chorale, censor, plain_member):
    client.force_login(censor)
    response = client.post(
        reverse("sanction_create", kwargs={"slug": chorale.slug}),
        {
            "member": plain_member.id,
            "sanction_type": Sanction.SANCTION_FINE,
            "reason": "Retard de cotisation",
            "applied_at": date.today().isoformat(),
            "amount": "",  # vide → doit échouer
        },
    )
    # Le form rend la page avec une erreur, pas de redirect
    assert response.status_code == 200
    assert not Sanction.objects.filter(member=plain_member).exists()


@pytest.mark.django_db
def test_sanction_apply_creates_event_log_warning(chorale, censor, plain_member):
    initial = Event.objects.filter(chorale=chorale, event_type='warning').count()
    SanctionService.apply(
        chorale=chorale, member=plain_member,
        sanction_type=Sanction.SANCTION_WARNING,
        reason="Test", recorded_by=censor,
    )
    assert Event.objects.filter(chorale=chorale, event_type='warning').count() == initial + 1


@pytest.mark.django_db
def test_sanction_service_rejects_non_member(chorale, censor):
    from django.core.exceptions import ValidationError
    outsider = baker.make(CustomUser)  # not in chorale
    with pytest.raises(ValidationError):
        SanctionService.apply(
            chorale=chorale, member=outsider,
            sanction_type=Sanction.SANCTION_WARNING,
            reason="x", recorded_by=censor,
        )


@pytest.mark.django_db
def test_sanction_service_rejects_fine_without_amount(chorale, censor, plain_member):
    from django.core.exceptions import ValidationError
    with pytest.raises(ValidationError):
        SanctionService.apply(
            chorale=chorale, member=plain_member,
            sanction_type=Sanction.SANCTION_FINE,
            reason="x", recorded_by=censor, amount=None,
        )


@pytest.mark.django_db
def test_sanction_lift_sets_lifted_at(client, chorale, censor, plain_member):
    sanction = SanctionService.apply(
        chorale=chorale, member=plain_member,
        sanction_type=Sanction.SANCTION_WARNING,
        reason="test", recorded_by=censor,
    )
    assert sanction.lifted_at is None
    client.force_login(censor)
    response = client.post(reverse("sanction_lift", kwargs={
        "slug": chorale.slug, "sanction_id": sanction.id
    }))
    assert response.status_code == 302
    sanction.refresh_from_db()
    assert sanction.lifted_at == date.today()
    assert sanction.is_active is False


@pytest.mark.django_db
def test_sanction_active_property_for_paid_fine(chorale, censor, plain_member):
    """Une amende payée n'est plus active, même sans lifted_at."""
    s = SanctionService.apply(
        chorale=chorale, member=plain_member,
        sanction_type=Sanction.SANCTION_FINE,
        reason="x", recorded_by=censor, amount=Decimal("1000"),
    )
    assert s.is_active is True
    s.is_paid = True
    s.save()
    assert s.is_active is False


# ── Dashboard stats ─────────────────────────────────────────────────────


@pytest.mark.django_db
def test_dashboard_stats_includes_open_sanctions(chorale, censor, plain_member):
    from django.core.cache import cache
    from manage_chorale.services import get_dashboard_stats
    cache.clear()
    SanctionService.apply(
        chorale=chorale, member=plain_member,
        sanction_type=Sanction.SANCTION_WARNING,
        reason="x", recorded_by=censor,
    )
    stats = get_dashboard_stats(chorale.id)
    assert stats["open_sanctions_count"] == 1
    assert "unjustified_absences_this_month" in stats
