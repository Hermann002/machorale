"""Régressions du flux OTP (modèle + vues web).

Bugs couverts :
- ``generate_new_code`` ne remettait pas ``used=False`` → tout code régénéré
  sur une ligne déjà consommée était rejeté à la vérification.
- Le resend créait une nouvelle ligne ``OtpCode`` par clic → les
  ``get_or_create(user=...)`` en aval levaient ``MultipleObjectsReturned``.
- La vérification web cherchait ``get(otp_code=...)`` sans scoper par user →
  collision de codes à 5 chiffres possible entre deux utilisateurs.
"""
import pytest
from django.core.cache import cache
from django.urls import reverse
from model_bakery import baker

from manage_users.models import CustomUser, OtpCode

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_ratelimit_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user(db):
    return baker.make(CustomUser, is_verify=False)


# --- modèle -----------------------------------------------------------------

def test_generate_new_code_resets_used_flag(user):
    otp = OtpCode.objects.create(user=user)
    code = otp.generate_new_code()
    assert otp.verify_code(code) is True
    assert otp.used is True

    new_code = otp.generate_new_code()
    otp.refresh_from_db()
    assert otp.used is False
    assert otp.verify_code(new_code) is True


def test_latest_for_user_with_multiple_rows(user):
    """Lignes multiples héritées de l'ancien resend : on prend la plus récente,
    sans ``MultipleObjectsReturned``."""
    OtpCode.objects.create(user=user)
    newest = OtpCode.objects.create(user=user)
    assert OtpCode.latest_for_user(user) == newest


def test_latest_for_user_creates_when_missing(user):
    otp = OtpCode.latest_for_user(user)
    assert otp.pk is not None
    assert OtpCode.objects.filter(user=user).count() == 1


# --- resend web ---------------------------------------------------------------

def test_resend_reuses_row(client, user):
    otp = OtpCode.objects.create(user=user)
    otp.generate_new_code()
    otp.used = True  # ligne déjà consommée
    otp.save()

    resp = client.get(reverse("resend_otp", kwargs={"user_id": user.id}))
    assert resp.status_code == 302

    assert OtpCode.objects.filter(user=user).count() == 1  # pas de nouvelle ligne
    otp.refresh_from_db()
    assert otp.used is False  # le nouveau code est vérifiable


# --- vérification web ----------------------------------------------------------

def _verify(client, user, code):
    return client.post(
        reverse("verify_email", kwargs={"user_id": user.id}),
        {"otp_code": code},
    )


def test_verify_scoped_to_user_rejects_other_users_code(client, user):
    other = baker.make(CustomUser, is_verify=False)
    other_otp = OtpCode.objects.create(user=other)
    other_code = other_otp.generate_new_code()

    resp = _verify(client, user, other_code)
    assert resp.status_code == 200  # re-render avec erreur, pas de redirect
    user.refresh_from_db()
    assert user.is_verify is False


def test_verify_happy_path_after_resend(client, user):
    """Cycle complet : code initial consommé → resend → nouveau code accepté."""
    otp = OtpCode.objects.create(user=user)
    otp.generate_new_code()
    otp.used = True  # simule une ancienne vérification réussie
    otp.save()

    client.get(reverse("resend_otp", kwargs={"user_id": user.id}))
    otp.refresh_from_db()

    resp = _verify(client, user, otp.otp_code)
    assert resp.status_code == 302
    user.refresh_from_db()
    assert user.is_verify is True
