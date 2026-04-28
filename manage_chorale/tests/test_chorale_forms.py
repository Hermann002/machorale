import pytest
from model_bakery import baker
from manage_chorale.models import Chorale
from manage_users.models import CustomUser 
from manage_chorale.forms import CreateChoraleForm, ConfChoraleForm
from datetime import timezone, datetime, date
from django.core.files.uploadedfile import SimpleUploadedFile


@pytest.fixture
def user():
    user = baker.make(CustomUser, username="test_user", is_verify=True)
    user.set_password("secret")
    user.save()
    return user

@pytest.fixture
def chorale(user) -> Chorale:
    chorale = baker.make(Chorale, name="salut", slug="salut", description="test chorale", established_date=datetime(2020, 1, 1, tzinfo=timezone.utc), country="France", city="Paris", address="123 rue de Paris", contact_email="test@example.com", contact_phone="0123456789", type_c="chorale", admin=user)
    chorale.save()
    return chorale

@pytest.mark.django_db
def test_create_chorale_valid(user):
    form = CreateChoraleForm(data={
        "name":"salut2",
        "type_c":"chorale",
        "description":"description de la chorale",
        "established_date":datetime(2020, 1, 1, tzinfo=timezone.utc),
        "location":"Paris, France",
        })

    assert form.is_valid()
    assert form.cleaned_data["name"] == "salut2"
    assert form.cleaned_data["type_c"] == "chorale"
    assert form.cleaned_data["description"] == "description de la chorale"
    assert form.cleaned_data["established_date"] == date(2020, 1, 1)
    assert form.cleaned_data["location"] == "Paris, France"

@pytest.mark.django_db
def test_create_chorale_failed_name_exist(chorale):
    user = baker.make(CustomUser, username="test_user2", is_verify=True)
    user.set_password("secret")
    user.save()

    chorale = chorale
    form = CreateChoraleForm(data={
        "name":"salut",
        "type_c":"chorale",
        "description":"description de la chorale",
        "established_date":datetime(2020, 1, 1, tzinfo=timezone.utc),
        "location":"Paris, France",
        })

    assert not form.is_valid()
    assert "Ce nom de chorale est déjà utilisé." in str(form.errors)

@pytest.mark.django_db
def test_conf_chorale_valid(chorale):
    form = ConfChoraleForm(data={
        "contact_email": "test@example.com",
        "contact_phone": "01 23 45 67 89",
        "meeting_frequency": "weekly",
        "slogan": "Chantez avec nous !",
    })

    assert form.is_valid()
    assert form.cleaned_data["contact_email"] == "test@example.com"
    assert form.cleaned_data["contact_phone"] == "0123456789"
    assert form.cleaned_data["meeting_frequency"] == "weekly"
    assert form.cleaned_data["slogan"] == "Chantez avec nous !"

@pytest.mark.django_db
def test_conf_chorale_form_invalid_phone():
    form = ConfChoraleForm(data={"contact_phone": "12"})
    assert not form.is_valid()
    assert "au moins 7 chiffres" in str(form.errors["contact_phone"])
