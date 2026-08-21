"""Sprint 5 — attendance (bulk absence write + member history)."""
from datetime import timedelta

import pytest
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from manage_chorale.models import Absence, Chorale, ChoraleEvent, Membership
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
def censor(chorale):
    return make_member(chorale, role=Membership.ROLE_CENSOR)[0]


@pytest.fixture
def plain(chorale):
    return make_member(chorale, role=Membership.ROLE_MEMBER)


@pytest.fixture
def practice(chorale):
    return baker.make(
        ChoraleEvent,
        chorale=chorale,
        event_type="practice",
        date=timezone.now() + timedelta(days=1),
    )


def attendance_url(chorale, event):
    return reverse(
        "api:v1:event_attendance",
        kwargs={"slug": chorale.slug, "pk": event.pk},
    )


def absences_url(chorale, membership):
    return reverse(
        "api:v1:member_absences",
        kwargs={"slug": chorale.slug, "pk": membership.pk},
    )


# --- attendance sheet (GET) --------------------------------------------------

def test_sheet_full_roster_all_present(chorale, censor, plain, practice):
    resp = client_for(censor).get(attendance_url(chorale, practice))
    assert resp.status_code == 200
    sheet = resp.json()
    assert len(sheet) == 2  # censor + plain
    assert all(entry["present"] for entry in sheet)
    assert all(entry["absence"] is None for entry in sheet)


def test_sheet_marks_absentees(chorale, censor, plain, practice):
    user, membership = plain
    baker.make(
        Absence, event=practice, member=user, reason="Maladie", is_justified=True
    )
    resp = client_for(censor).get(attendance_url(chorale, practice))
    entry = next(
        e for e in resp.json() if e["membership_id"] == membership.id
    )
    assert entry["present"] is False
    assert entry["absence"]["reason"] == "Maladie"
    assert entry["absence"]["is_justified"] is True


def test_sheet_readable_by_plain_member(chorale, plain, practice):
    resp = client_for(plain[0]).get(attendance_url(chorale, practice))
    assert resp.status_code == 200


def test_sheet_untracked_event_type_400(chorale, censor):
    concert = baker.make(
        ChoraleEvent, chorale=chorale, event_type="concert",
        date=timezone.now(),
    )
    resp = client_for(censor).get(attendance_url(chorale, concert))
    assert resp.status_code == 400
    assert "event" in resp.json()["errors"]


def test_sheet_event_scoped_to_chorale_404(chorale, censor):
    foreign = baker.make(
        ChoraleEvent, chorale=baker.make(Chorale), event_type="practice",
        date=timezone.now(),
    )
    resp = client_for(censor).get(attendance_url(chorale, foreign))
    assert resp.status_code == 404


# --- bulk write (PUT) --------------------------------------------------------

def test_censor_bulk_sets_absentees(chorale, censor, plain, practice):
    user, membership = plain
    resp = client_for(censor).put(
        attendance_url(chorale, practice),
        {"absences": [
            {"member_id": membership.id, "reason": "Voyage",
             "is_justified": False},
        ]},
        format="json",
    )
    assert resp.status_code == 200
    absence = Absence.objects.get(event=practice, member=user)
    assert absence.reason == "Voyage"
    assert absence.recorded_by == censor
    entry = next(
        e for e in resp.json() if e["membership_id"] == membership.id
    )
    assert entry["present"] is False


def test_bulk_write_is_idempotent_replace(chorale, censor, plain, practice):
    user, membership = plain
    other_user, other_membership = make_member(chorale)
    baker.make(Absence, event=practice, member=other_user)

    resp = client_for(censor).put(
        attendance_url(chorale, practice),
        {"absences": [{"member_id": membership.id}]},
        format="json",
    )
    assert resp.status_code == 200
    # Previous state wiped: only the new absentee remains.
    assert list(
        Absence.objects.filter(event=practice).values_list("member", flat=True)
    ) == [user.id]


def test_bulk_write_empty_list_clears_all(chorale, censor, plain, practice):
    baker.make(Absence, event=practice, member=plain[0])
    resp = client_for(censor).put(
        attendance_url(chorale, practice), {"absences": []}, format="json"
    )
    assert resp.status_code == 200
    assert Absence.objects.filter(event=practice).count() == 0


def test_bulk_write_unknown_member_400(chorale, censor, practice):
    resp = client_for(censor).put(
        attendance_url(chorale, practice),
        {"absences": [{"member_id": 999999}]},
        format="json",
    )
    assert resp.status_code == 400
    assert Absence.objects.count() == 0


def test_bulk_write_member_of_other_chorale_400(chorale, censor, practice):
    _, foreign_membership = make_member(baker.make(Chorale))
    resp = client_for(censor).put(
        attendance_url(chorale, practice),
        {"absences": [{"member_id": foreign_membership.id}]},
        format="json",
    )
    assert resp.status_code == 400


def test_bulk_write_duplicate_member_400(chorale, censor, plain, practice):
    membership = plain[1]
    resp = client_for(censor).put(
        attendance_url(chorale, practice),
        {"absences": [
            {"member_id": membership.id},
            {"member_id": membership.id},
        ]},
        format="json",
    )
    assert resp.status_code == 400


def test_plain_member_cannot_write(chorale, plain, practice):
    user, membership = plain
    resp = client_for(user).put(
        attendance_url(chorale, practice),
        {"absences": [{"member_id": membership.id}]},
        format="json",
    )
    assert resp.status_code == 403


def test_admin_can_write(chorale, plain, practice):
    admin, _ = make_member(chorale, role=Membership.ROLE_ADMIN, is_admin=True)
    resp = client_for(admin).put(
        attendance_url(chorale, practice),
        {"absences": [{"member_id": plain[1].id}]},
        format="json",
    )
    assert resp.status_code == 200


# --- member absence history --------------------------------------------------

def test_member_absence_history_and_stats(chorale, censor, plain):
    user, membership = plain
    for i, justified in enumerate((True, False, False)):
        event = baker.make(
            ChoraleEvent, chorale=chorale, event_type="practice",
            date=timezone.now() - timedelta(days=i),
        )
        baker.make(
            Absence, event=event, member=user, is_justified=justified
        )
    resp = client_for(censor).get(absences_url(chorale, membership))
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 3
    assert body["stats"] == {"total": 3, "justified": 1, "unjustified": 2}
    # Newest event first.
    dates = [a["event"]["date"] for a in body["results"]]
    assert dates == sorted(dates, reverse=True)


def test_member_absence_history_scoped_to_chorale(chorale, censor, plain):
    """Absences from another chorale's events never leak into the history."""
    user, membership = plain
    foreign_event = baker.make(
        ChoraleEvent, chorale=baker.make(Chorale), event_type="practice",
        date=timezone.now(),
    )
    baker.make(Absence, event=foreign_event, member=user)
    resp = client_for(censor).get(absences_url(chorale, membership))
    assert resp.json()["count"] == 0


def test_member_absences_unknown_membership_404(chorale, censor):
    resp = client_for(censor).get(
        reverse(
            "api:v1:member_absences",
            kwargs={"slug": chorale.slug, "pk": 999999},
        )
    )
    assert resp.status_code == 404


def test_member_absences_non_member_403(chorale, plain):
    outsider = baker.make(CustomUser, is_verify=True)
    resp = client_for(outsider).get(absences_url(chorale, plain[1]))
    assert resp.status_code == 403
