from django.urls import path
from .views import DashboardView, CreateChoraleView

urlpatterns = [
    path("create-chorale/", CreateChoraleView.as_view(), name="create_chorale"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
]