# manage_users/tests/test_integration.py
import pytest
from django.test import Client, override_settings
from django.urls import reverse
from django.core import mail
from model_bakery import baker
from manage_users.models import CustomUser, OtpCode
from manage_chorale.models import Chorale, Membership
from datetime import date

@pytest.mark.django_db
def test_user_registration_to_chorale_creation_flow():
    """
    Test d'intégration complet :
    1. Inscription
    2. Vérification OTP
    3. Création de chorale
    """
    client = Client()
    
    # Étape 1 : Inscription
    response = client.post(reverse('register'), {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'SecurePassword123',
        'confirm_password': 'SecurePassword123'
    })
    user = CustomUser.objects.get(email='test@example.com')
    # Vérifie la redirection vers verify_email
    assert response.status_code == 302
    assert reverse('verify_email', kwargs={"user_id": user.id}) in response.url
    assert not user.is_verify
    
    # Vérifie qu’un OTP a été généré
    otp = OtpCode.objects.get(user=user)
    assert otp.otp_code is not None
    assert len(otp.otp_code) == 5
    
    # assert len(mail.outbox) == 1
    # assert 'code' in mail.outbox[0].body.lower()
    
    # Étape 2 : Vérification OTP
    response = client.post(reverse('verify_email', kwargs={"user_id": user.id}), {
        'otp_code': otp.otp_code
    })
    
    # Vérifie la connexion + redirection vers create_chorale
    assert response.status_code == 302
    assert reverse('create_chorale') in response.url
    
    # Vérifie que l'utilisateur est maintenant vérifié
    user.refresh_from_db()
    assert user.is_verify
    
    response = client.get(reverse("create_chorale"))
    assert response.status_code == 200

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
    
    management_form = response.context['wizard']['management_form']
    step2_data = {
        "conf-contact_email": "contact@ma-chorale.org",
        "conf-contact_phone": "+33612345678",
        "conf-meeting_frequency": "weekly",
        "conf-slogan": "Chantez avec nous !",
        management_form.add_prefix('current_step'): 'conf',
    }
    response = client.post(reverse("create_chorale"), step2_data)
    
    # Vérifie la redirection vers le dashboard
    assert response.status_code == 302
    assert 'dashboard' in response.url
    
    user.refresh_from_db()
    # Vérifie que la chorale a été créée
    chorale = Chorale.objects.get(name='Ma Chorale')
    membership = Membership.objects.get(user=user, chorale=chorale)
    assert membership.is_admin is True
    assert membership.role == Membership.ROLE_ADMIN
    assert user in chorale.members.all()