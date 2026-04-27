import pytest
from django.contrib.auth import get_user_model
from model_bakery import baker
from manage_users.forms import UserLoginForm
from manage_users.models import CustomUser

@pytest.fixture
def user(db)-> CustomUser:
    user = baker.make(CustomUser, username="test_user")
    user.set_password("secret")
    user.is_verify = True
    user.save()
    return user


@pytest.mark.django_db
def test_valid_login_form(user:CustomUser):
    user.is_verify=True
    user.save()

    form = UserLoginForm(data={"username": "test_user", "password": "secret"})

    assert form.is_valid()
    assert form.cleaned_data["user"] == user


@pytest.mark.django_db
def test_invalid_login_form_wrong_password(user:CustomUser):
    form = UserLoginForm(data={"username": "test_user", "password": "wrong"})

    assert not form.is_valid()
    assert "Invalid username or password." in str(form.errors)