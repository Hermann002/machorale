from django.urls import path
from .views import DashboardView, CreateChoraleView, ContributionView, ListMembersView, MemberPopupView, close_popup, sidebar_toggle

urlpatterns = [
    path("create-chorale/", CreateChoraleView.as_view(), name="create_chorale"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("list-members/", ListMembersView.as_view(), name="members"),
    path("member-popup/", MemberPopupView.as_view(), name="member_popup"),
    path("contributions/", ContributionView.as_view(), name="contributions"),
    path("sidebar-toggle/", sidebar_toggle, name="sidebar_toggle"),
    path("close-popup/", close_popup, name="close_popup"),
]