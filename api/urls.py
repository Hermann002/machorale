from django.urls import include, path, re_path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from . import views

app_name = "api"

urlpatterns = [
    path("v1/", include("api.v1.urls")),
    # OpenAPI schema + Swagger UI.
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(url_name="api:schema"),
        name="docs",
    ),
    # The catch-all below resolves /api/docs (no slash) before APPEND_SLASH
    # can kick in, so redirect it explicitly.
    path("docs", RedirectView.as_view(pattern_name="api:docs", permanent=True)),
    # Catch-all: any unmatched /api/ path returns the JSON error envelope,
    # never Django's HTML 404. Must stay last.
    re_path(r"^.*$", views.api_not_found, name="not_found"),
]
