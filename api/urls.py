from django.urls import include, path, re_path

from . import views

app_name = "api"

urlpatterns = [
    path("v1/", include("api.v1.urls")),
    # Catch-all: any unmatched /api/ path returns the JSON error envelope,
    # never Django's HTML 404. Must stay last.
    re_path(r"^.*$", views.api_not_found, name="not_found"),
]
