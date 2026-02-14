from django.urls import path
from .views import DashboardView, CreateChoraleView, ConfChoraleView

urlpatterns = [
    path("create-chorale/", CreateChoraleView.as_view(), name="create_chorale"),
    path("conf-chorale/", ConfChoraleView.as_view, name="conf-chorale"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
]