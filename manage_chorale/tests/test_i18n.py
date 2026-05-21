"""Smoke tests for i18n setup: default FR served at /, EN at /en/,
and set_language switching honors the requested language."""
import pytest


@pytest.mark.django_db
def test_root_redirects_to_french_by_default(client):
    response = client.get('/')
    assert response.status_code == 302
    assert response.url.startswith('/fr/')


@pytest.mark.django_db
def test_fr_prefix_serves_french(client):
    response = client.get('/fr/')
    assert response.status_code == 200
    assert response['Content-Language'] == 'fr'


@pytest.mark.django_db
def test_en_prefix_serves_english(client):
    response = client.get('/en/')
    assert response.status_code == 200
    assert response['Content-Language'] == 'en'


@pytest.mark.django_db
def test_set_language_switches_locale(client):
    response = client.post(
        '/i18n/setlang/',
        {'language': 'en', 'next': '/fr/u/login/'},
        HTTP_REFERER='/fr/u/login/',
    )
    assert response.status_code == 302
    assert response.url.startswith('/en/')
