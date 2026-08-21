"""API documentation endpoints (drf-spectacular Swagger UI + OpenAPI schema).

No ``django_db`` mark: none of these endpoints touch the database.
"""


def test_swagger_ui_is_served(client):
    response = client.get("/api/docs/")
    assert response.status_code == 200
    assert "text/html" in response["Content-Type"]
    assert b"swagger" in response.content.lower()


def test_docs_without_trailing_slash_redirects(client):
    response = client.get("/api/docs")
    assert response.status_code == 301
    assert response["Location"] == "/api/docs/"


def test_openapi_schema_is_served(client):
    response = client.get("/api/schema/")
    assert response.status_code == 200
    content = response.content.decode()
    assert "openapi:" in content
    assert "Ma Chorale API" in content
    # Every v1 endpoint must be documented.
    for path in (
        "/api/v1/ping/",
        "/api/v1/auth/otp/request/",
        "/api/v1/auth/otp/verify/",
        "/api/v1/auth/refresh/",
        "/api/v1/auth/me/",
        "/api/v1/chorales/",
        "/api/v1/chorales/{slug}/dashboard/",
        "/api/v1/chorales/{slug}/members/",
        "/api/v1/chorales/{slug}/members/{id}/",
        "/api/v1/chorales/{slug}/events/",
        "/api/v1/chorales/{slug}/events/{id}/",
        "/api/v1/chorales/{slug}/events/{id}/attendance/",
        "/api/v1/chorales/{slug}/members/{id}/absences/",
        "/api/v1/chorales/{slug}/contributions/",
        "/api/v1/chorales/{slug}/contributions/{id}/",
        "/api/v1/chorales/{slug}/contributions/{id}/payments/",
        "/api/v1/chorales/{slug}/cashflows/",
        "/api/v1/chorales/{slug}/cashflows/{id}/",
    ):
        assert path in content, f"{path} missing from schema"


def test_catch_all_still_returns_json_envelope(client):
    response = client.get("/api/nope/")
    assert response.status_code == 404
    assert response["Content-Type"].startswith("application/json")
    body = response.json()
    assert set(body) == {"detail", "errors"}
