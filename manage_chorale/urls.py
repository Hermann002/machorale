from django.urls import path
from .views import DashboardView, CreateChoraleView, ContributionView, ListMembersView, MemberPopupView, close_popup, sidebar_toggle

urlpatterns = [
    path("create-chorale/", CreateChoraleView.as_view(), name="create_chorale"), #
    path("<slug:slug>/dashboard/", DashboardView.as_view(), name="dashboard"),
    path("<slug:slug>/list-members/", ListMembersView.as_view(), name="members"),
    path("<slug:slug>/member-popup/", MemberPopupView.as_view(), name="member_popup"),
    path("<slug:slug>/contributions/", ContributionView.as_view(), name="contributions"),
    path("<slug:slug>/sidebar-toggle/", sidebar_toggle, name="sidebar_toggle"),
    path("close-popup/", close_popup, name="close_popup"),
]