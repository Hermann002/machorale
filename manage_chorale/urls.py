from django.urls import path
from .views import DashboardView, CreateChoraleView, ContributionView, ListMembersView, MemberPopupView, UpdateMemberRoleView, close_popup, sidebar_toggle, EventListView, CreateEventView, EventDetailView, EventTableView, EventUpdateView

urlpatterns = [
    path("create-chorale/", CreateChoraleView.as_view(), name="create_chorale"),
    path("<slug:slug>/dashboard/", DashboardView.as_view(), name="dashboard"),
    path("<slug:slug>/list-members/", ListMembersView.as_view(), name="members"),
    path("<slug:slug>/member/<int:user_id>/role/", UpdateMemberRoleView.as_view(), name="member_role_edit"),
    path("<slug:slug>/member-popup/", MemberPopupView.as_view(), name="member_popup"),
    path("<slug:slug>/events/", EventListView.as_view(), name="events"),
    path("<slug:slug>/events/create/", CreateEventView.as_view(), name="event_create"),
    path("<slug:slug>/events/<int:event_id>/", EventDetailView.as_view(), name="event_detail"),
    path("<slug:slug>/events/list/", EventTableView.as_view(), name="events_list"),
    path("<slug:slug>/events/<int:event_id>/edit/", EventUpdateView.as_view(), name="event_edit"),
    path("<slug:slug>/contributions/", ContributionView.as_view(), name="contributions"),
    path("<slug:slug>/sidebar-toggle/", sidebar_toggle, name="sidebar_toggle"),
    path("close-popup/", close_popup, name="close_popup"),
]