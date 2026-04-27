import pytest
from django.urls import reverse
from django.contrib.auth import get_user
from model_bakery import baker
from manage_users.models import CustomUser
from django.core.cache import cache

@pytest.mark.django_db
def test_login_view_get(client):
    response = client.get(reverse("login"))
    assert response.status_code == 200
    assert "form"in response.context

@pytest.mark.django_db
def test_login_view_post_success(client):
    user = baker.make(CustomUser, username="testuser", is_verify=True)
    user.set_password("secret")
    user.save()

    chorale = baker.make("manage_chorale.Chorale", admin=user, slug="my-chorale")

    response = client.post(reverse("login"), {
        "username":"testuser",
        "password":"secret"
    })

    assert response.status_code == 302
    assert response.url == reverse("dashboard", kwargs={"slug":"my-chorale"})
    assert get_user(client).is_authenticated

@pytest.mark.django_db
def test_login_view_post_invalid_credential(client):
    user = baker.make(CustomUser, username="testuser", is_verify=True)
    user.set_password("secret")
    user.save()

    response = client.post(reverse("login"), {
        "username":"testuser",
        "password":"wrong"
    })

    assert response.status_code == 200
    assert "Invalid username or password." in response.content.decode()

@pytest.mark.django_db
def test_login_view_already_authenticated(client):
    """Test : utilisateur déjà connecté → redirection."""
    user = baker.make(CustomUser)
    client.force_login(user)
    
    response = client.get(reverse("login"))
    assert response.status_code == 302
    assert response.url == "/"

@pytest.mark.django_db
def test_rate_limiting(client):
    """Test blocage après trop de tentatives."""
    cache.clear()  # Nettoie le cache entre tests
    
    for _ in range(5):
        client.post(reverse("login"), {"username": "user", "password": "pass"})
    
    # 6e tentative → bloquée
    response = client.post(reverse("login"), {"username": "user", "password": "pass"})
    assert response.status_code == 403  # Too Many Requests