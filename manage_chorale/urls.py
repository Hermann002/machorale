from django.urls import path
from .views import DashboardView, CreateChoraleView, ContributionView, ListMembersView, MemberPopupView, close_popup

urlpatterns = [
    path("create-chorale/", CreateChoraleView.as_view(), name="create_chorale"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("list-members/", ListMembersView.as_view(), name="members"),
    path("member-popup/", MemberPopupView.as_view(), name="member_popup"),
    path("contributions/", ContributionView.as_view(), name="contributions"),
    path("close-popup/", close_popup, name="close_popup"),
]