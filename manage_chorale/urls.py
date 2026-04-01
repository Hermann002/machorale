from django.urls import path
from .views import DashboardView, CreateChoraleView, ContributionView, ListMembersView, MemberPopupView, close_popup, sidebar_toggle

urlpatterns = [
    path("<slug:chorale_name>/create-chorale/", CreateChoraleView.as_view(), name="create_chorale"),
    path("<slug:chorale_name>/dashboard/", DashboardView.as_view(), name="dashboard"),
    path("<slug:chorale_name>/list-members/", ListMembersView.as_view(), name="members"),
    path("<slug:chorale_name>/member-popup/", MemberPopupView.as_view(), name="member_popup"),
    path("<slug:chorale_name>/contributions/", ContributionView.as_view(), name="contributions"),
    path("sidebar-toggle/", sidebar_toggle, name="sidebar_toggle"),
    path("close-popup/", close_popup, name="close_popup"),
]