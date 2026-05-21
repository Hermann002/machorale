"""Tests de l'écran de sélection de chorale et du helper de redirection
``resolve_post_login_redirect``.

Couvre :
- 0 membership  → wizard de création
- 1 membership  → dashboard direct + session set
- N memberships → stickiness session > écran de sélection
- POST select_chorale : valide l'appartenance, set la session, redirige
- POST select_chorale : slug d'une autre chorale rejeté
"""

import pytest
from django.urls import reverse
from model_bakery import baker

from manage_users.models import CustomUser
from manage_users.utils import resolve_post_login_redirect
from manage_chorale.models import Chorale, Membership


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def user(db):
    return baker.make(CustomUser, username="alice", email="alice@example.com", is_verify=True)


@pytest.fixture
def chorale_a(user):
    c = baker.make(Chorale, created_by=user)
    Membership.objects.create(user=user, chorale=c, role=Membership.ROLE_ADMIN, is_admin=True)
    return c


@pytest.fixture
def chorale_b(user):
    c = baker.make(Chorale, created_by=user)
    Membership.objects.create(user=user, chorale=c, role=Membership.ROLE_MEMBER, is_admin=False)
    return c


# ── Helper resolve_post_login_redirect ──────────────────────────────────


@pytest.mark.django_db
def test_resolve_redirect_zero_memberships(user):
    session = {}
    url = resolve_post_login_redirect(user, session)
    assert url == reverse('create_chorale')
    assert 'active_chorale_slug' not in session


@pytest.mark.django_db
def test_resolve_redirect_one_membership_sets_session(user, chorale_a):
    session = {}
    url = resolve_post_login_redirect(user, session)
    assert url == reverse('dashboard', kwargs={'slug': chorale_a.slug})
    assert session['active_chorale_slug'] == chorale_a.slug


@pytest.mark.django_db
def test_resolve_redirect_many_no_sticky_goes_to_select(user, chorale_a, chorale_b):
    session = {}
    url = resolve_post_login_redirect(user, session)
    assert url == reverse('select_chorale')


@pytest.mark.django_db
def test_resolve_redirect_many_with_valid_sticky_goes_to_that_chorale(user, chorale_a, chorale_b):
    session = {'active_chorale_slug': chorale_b.slug}
    url = resolve_post_login_redirect(user, session)
    assert url == reverse('dashboard', kwargs={'slug': chorale_b.slug})


@pytest.mark.django_db
def test_resolve_redirect_many_with_stale_sticky_goes_to_select(user, chorale_a, chorale_b):
    session = {'active_chorale_slug': 'no-such-chorale'}
    url = resolve_post_login_redirect(user, session)
    assert url == reverse('select_chorale')


# ── ChoraleSelectView ───────────────────────────────────────────────────


@pytest.mark.django_db
def test_select_view_redirects_if_no_membership(client, user):
    client.force_login(user)
    response = client.get(reverse('select_chorale'))
    assert response.status_code == 302
    assert response.url == reverse('create_chorale')


@pytest.mark.django_db
def test_select_view_redirects_if_single_membership(client, user, chorale_a):
    client.force_login(user)
    response = client.get(reverse('select_chorale'))
    assert response.status_code == 302
    assert response.url == reverse('dashboard', kwargs={'slug': chorale_a.slug})
    # Session sticky doit être posée
    assert client.session.get('active_chorale_slug') == chorale_a.slug


@pytest.mark.django_db
def test_select_view_lists_chorales_for_multi(client, user, chorale_a, chorale_b):
    client.force_login(user)
    response = client.get(reverse('select_chorale'))
    assert response.status_code == 200
    content = response.content.decode()
    assert chorale_a.name in content
    assert chorale_b.name in content


@pytest.mark.django_db
def test_select_view_post_sets_session_and_redirects(client, user, chorale_a, chorale_b):
    client.force_login(user)
    response = client.post(reverse('select_chorale'), {'slug': chorale_b.slug})
    assert response.status_code == 302
    assert response.url == reverse('dashboard', kwargs={'slug': chorale_b.slug})
    assert client.session.get('active_chorale_slug') == chorale_b.slug


@pytest.mark.django_db
def test_select_view_post_rejects_foreign_chorale(client, user, chorale_a):
    other_user = baker.make(CustomUser, is_verify=True)
    foreign = baker.make(Chorale, created_by=other_user)
    Membership.objects.create(user=other_user, chorale=foreign, role=Membership.ROLE_ADMIN, is_admin=True)

    client.force_login(user)
    response = client.post(reverse('select_chorale'), {'slug': foreign.slug})
    assert response.status_code == 302
    assert response.url == reverse('select_chorale')
    assert client.session.get('active_chorale_slug') != foreign.slug


@pytest.mark.django_db
def test_select_view_post_without_slug_redirects_back(client, user, chorale_a, chorale_b):
    client.force_login(user)
    response = client.post(reverse('select_chorale'), {})
    assert response.status_code == 302
    assert response.url == reverse('select_chorale')


# ── LoginView intégré ────────────────────────────────────────────────────


@pytest.mark.django_db
def test_login_view_redirects_to_select_for_multi_membership(client, user, chorale_a, chorale_b):
    user.set_password("Secret123!")
    user.save()
    response = client.post(reverse('login'), {
        'username': user.username,
        'password': 'Secret123!',
    })
    assert response.status_code == 302
    assert response.url == reverse('select_chorale')


@pytest.mark.django_db
def test_login_view_uses_sticky_session_for_multi_membership(client, user, chorale_a, chorale_b):
    user.set_password("Secret123!")
    user.save()
    session = client.session
    session['active_chorale_slug'] = chorale_a.slug
    session.save()
    response = client.post(reverse('login'), {
        'username': user.username,
        'password': 'Secret123!',
    })
    assert response.status_code == 302
    assert response.url == reverse('dashboard', kwargs={'slug': chorale_a.slug})


# ── Mixin cross-chorale denial ──────────────────────────────────────────


@pytest.mark.django_db
def test_user_denied_on_foreign_chorale_dashboard(client, user, chorale_a):
    other_user = baker.make(CustomUser, is_verify=True)
    foreign = baker.make(Chorale, created_by=other_user)
    Membership.objects.create(user=other_user, chorale=foreign, role=Membership.ROLE_ADMIN, is_admin=True)

    client.force_login(user)
    response = client.get(reverse('dashboard', kwargs={'slug': foreign.slug}))
    assert response.status_code == 302
    assert response.url == reverse('select_chorale')


@pytest.mark.django_db
def test_mixin_sets_active_session_on_dashboard_visit(client, user, chorale_a, chorale_b):
    client.force_login(user)
    client.get(reverse('dashboard', kwargs={'slug': chorale_b.slug}))
    assert client.session.get('active_chorale_slug') == chorale_b.slug
