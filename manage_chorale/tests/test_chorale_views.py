import pytest
from django.urls import reverse
from django.contrib.messages import get_messages
from model_bakery import baker
from manage_users.models import CustomUser
from manage_chorale.models import Chorale
from datetime import date

@pytest.fixture
def verified_user():
    user = baker.make(CustomUser, is_verify=True, role="member")
    return user

@pytest.mark.django_db
def test_create_chorale_view_redirects_if_not_verified(client):
    user = baker.make(CustomUser, is_verify=False)
    client.force_login(user)
    response = client.get(reverse("create_chorale"))
    assert response.status_code == 302
    messages = list(get_messages(response.wsgi_request))
    assert "You need to verify your email" in str(messages[0])

@pytest.mark.django_db
def test_create_chorale_view_redirects_if_already_admin(client, verified_user):
    chorale = baker.make("manage_chorale.Chorale", admin=verified_user)
    client.force_login(verified_user)
    response = client.get(reverse("create_chorale"))
    assert response.status_code == 302
    assert response.url == reverse("dashboard", kwargs={"slug": chorale.slug})

@pytest.mark.django_db
def test_create_chorale_view_get_step1(client, verified_user):
    client.force_login(verified_user)
    response = client.get(reverse("create_chorale"))
    assert response.status_code == 200
    assert "Nom du groupe" in response.content.decode()

@pytest.mark.django_db
def test_create_chorale_view_post_success(client, verified_user):
    client.force_login(verified_user)
    
    # 1. GET initial
    response = client.get(reverse("create_chorale"))
    assert response.status_code == 200
    
    # 2. ÉTAPE 1 : 'create'
    management_form = response.context['wizard']['management_form']
    step1_data = {
        "create-name": "Ma Chorale",
        "create-type_c": "chorale",
        "create-location": "Lyon, France",
        "create-established_date": date(2020, 1, 1),
        management_form.add_prefix('current_step'): 'create',
    }
    response = client.post(reverse("create_chorale"), step1_data)
    assert response.status_code == 200  # Doit afficher l'étape 'conf'
    
    # 3. ÉTAPE 2 : 'conf'
    management_form = response.context['wizard']['management_form']
    step2_data = {
        "conf-contact_email": "contact@ma-chorale.org",
        "conf-contact_phone": "+33612345678",
        "conf-meeting_frequency": "weekly",
        "conf-slogan": "Chantez avec nous !",
        management_form.add_prefix('current_step'): 'conf',
    }
    response = client.post(reverse("create_chorale"), step2_data)
    
    chorale = Chorale.objects.get(name="Ma Chorale")
    assert response.status_code == 302
    assert Chorale.objects.filter(name="Ma Chorale").exists()
    assert chorale.city == "Lyon"
    assert chorale.country == "France"

# @pytest.mark.django_db
# def test_create_event_view_forbidden_for_non_secretary_or_admin(client, verified_user):
#     chorale = baker.make(Chorale, admin=baker.make(CustomUser, role=CustomUser.ROLE_SUPERADMIN_CHORALE))
#     chorale.members.add(verified_user)
#     client.force_login(verified_user)
#     response = client.get(reverse('event_create', kwargs={'slug': chorale.slug}))
#     assert response.status_code == 302
#     assert response.url == reverse('dashboard', kwargs={'slug': chorale.slug})

# @pytest.mark.django_db
# def test_create_event_view_allows_secretary(client):
#     admin = baker.make(CustomUser, role=CustomUser.ROLE_SUPERADMIN_CHORALE)
#     chorale = baker.make(Chorale, admin=admin)
#     secretary = baker.make(CustomUser, role='member', chorale_role=CustomUser.CHORALE_ROLE_SECRETARY)
#     chorale.members.add(secretary)
#     client.force_login(secretary)

#     response = client.get(reverse('event_create', kwargs={'slug': chorale.slug}))
#     assert response.status_code == 200
#     assert 'Créer un événement' in response.content.decode()

#     event_data = {
#         'title': 'Pratique du week-end',
#         'description': 'Répétition générale avant le concert.',
#         'location': 'Salle des fêtes',
#         'date': '2030-01-05T18:00',
#         'event_type': 'practice',
#     }
#     response = client.post(reverse('event_create', kwargs={'slug': chorale.slug}), event_data)
#     assert response.status_code == 302
#     assert response.url == reverse('events', kwargs={'slug': chorale.slug})

# @pytest.mark.django_db
# def test_event_detail_page_shows_event_information(client):
#     admin = baker.make(CustomUser, role=CustomUser.ROLE_SUPERADMIN_CHORALE)
#     chorale = baker.make(Chorale, admin=admin)
#     event = baker.make('manage_chorale.ChoraleEvent', chorale=chorale, title='Concert de Noël', location='Église centrale', date='2030-12-20 20:00:00')
#     client.force_login(admin)

#     response = client.get(reverse('event_detail', kwargs={'slug': chorale.slug, 'event_id': event.id}))
#     assert response.status_code == 200
#     assert 'Concert de Noël' in response.content.decode()

# @pytest.mark.django_db
# def test_customuser_has_default_chorale_role():
#     user = baker.make(CustomUser, username='roler_test')
#     assert user.chorale_role == CustomUser.CHORALE_ROLE_MEMBER

# @pytest.mark.django_db
# def test_update_member_role_view_updates_role(client, verified_user):
#     chorale = baker.make(Chorale, admin=verified_user)
#     member = baker.make(CustomUser, username='member1', email='member1@example.com', chorale_role=CustomUser.CHORALE_ROLE_MEMBER)
#     chorale.members.add(member)
#     client.force_login(verified_user)

#     response = client.post(
#         reverse('member_role_edit', kwargs={'slug': chorale.slug, 'user_id': member.id}),
#         {'chorale_role': CustomUser.CHORALE_ROLE_TREASURER},
#     )

#     member.refresh_from_db()
#     assert member.chorale_role == CustomUser.CHORALE_ROLE_TREASURER
#     assert response.status_code == 302
#     assert response.url == reverse('members', kwargs={'slug': chorale.slug})
 