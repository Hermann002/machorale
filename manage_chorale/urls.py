from django.urls import path
from .views import DashboardView, CreateChoraleView, ContributionView, ListMembersView

urlpatterns = [
    path("create-chorale/", CreateChoraleView.as_view(), name="create_chorale"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("list-members/", ListMembersView.as_view(), name="members"),
    path("contributions/", ContributionView.as_view(), name="contributions"),
]