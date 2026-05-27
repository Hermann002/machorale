from django.urls import path
from .views import (
    DashboardView, CreateChoraleView, ListMembersView, MemberPopupView,
    UpdateMemberRoleView, EditMemberProfileView, ChoraleSelectView,
    close_popup, sidebar_toggle, ActivityListView,
    EventListView, CreateEventView, EventDetailView, EventUpdateView,
    # Trésorier
    ContributionListView, ContributionCreateView, ContributionUpdateView, ContributionDeleteView,
    MemberContributionListView, MemberContributionCreateView,
    CashFlowListView, CashFlowCreateView, CashFlowUpdateView,
    # Censeur
    AbsenceListView, AbsenceBulkCreateView, AbsenceUpdateView, AbsenceDeleteView,
    SanctionListView, SanctionCreateView, SanctionUpdateView,
    SanctionLiftView, SanctionDeleteView,
)

urlpatterns = [
    # Patterns sans <slug:slug> en premier (sinon collision).
    path("create-chorale/", CreateChoraleView.as_view(), name="create_chorale"),
    path("select-chorale/", ChoraleSelectView.as_view(), name="select_chorale"),
    path("<slug:slug>/dashboard/", DashboardView.as_view(), name="dashboard"),
    path("<slug:slug>/list-members/", ListMembersView.as_view(), name="members"),
    path("<slug:slug>/member/<int:user_id>/role/", UpdateMemberRoleView.as_view(), name="member_role_edit"),
    path("<slug:slug>/member/<int:user_id>/edit/", EditMemberProfileView.as_view(), name="member_edit"),
    path("<slug:slug>/member-popup/", MemberPopupView.as_view(), name="member_popup"),
    path("<slug:slug>/events/", EventListView.as_view(), name="events"),
    path("<slug:slug>/events/create/", CreateEventView.as_view(), name="event_create"),
    path("<slug:slug>/events/<int:event_id>/", EventDetailView.as_view(), name="event_detail"),
    path("<slug:slug>/events/<int:event_id>/edit/", EventUpdateView.as_view(), name="event_edit"),

    path("<slug:slug>/activities/", ActivityListView.as_view(), name="activities"),

    # ── Trésorier ─────────────────────────────────────────────────────────
    # CRUD types de cotisation
    path("<slug:slug>/treasurer/contributions/",
         ContributionListView.as_view(), name="contributions"),
    path("<slug:slug>/treasurer/contributions/create/",
         ContributionCreateView.as_view(), name="contribution_create"),
    path("<slug:slug>/treasurer/contributions/<int:contribution_id>/edit/",
         ContributionUpdateView.as_view(), name="contribution_edit"),
    path("<slug:slug>/treasurer/contributions/<int:contribution_id>/delete/",
         ContributionDeleteView.as_view(), name="contribution_delete"),

    # Enregistrement / liste des paiements membres
    path("<slug:slug>/treasurer/payments/",
         MemberContributionListView.as_view(), name="payments"),
    path("<slug:slug>/treasurer/payments/create/",
         MemberContributionCreateView.as_view(), name="payment_create"),

    # Entrées / sorties (cash flow)
    path("<slug:slug>/treasurer/cashflow/",
         CashFlowListView.as_view(), name="cashflow"),
    path("<slug:slug>/treasurer/cashflow/create/",
         CashFlowCreateView.as_view(), name="cashflow_create"),
    path("<slug:slug>/treasurer/cashflow/<int:cashflow_id>/edit/",
         CashFlowUpdateView.as_view(), name="cashflow_edit"),

    # ── Censeur ──────────────────────────────────────────────────────────
    # Absences (sparse, idempotent bulk record)
    path("<slug:slug>/censor/absences/",
         AbsenceListView.as_view(), name="absences"),
    path("<slug:slug>/censor/absences/record/",
         AbsenceBulkCreateView.as_view(), name="absence_bulk_create"),
    path("<slug:slug>/censor/absences/<int:absence_id>/edit/",
         AbsenceUpdateView.as_view(), name="absence_edit"),
    path("<slug:slug>/censor/absences/<int:absence_id>/delete/",
         AbsenceDeleteView.as_view(), name="absence_delete"),

    # Sanctions (warning / fine / suspension)
    path("<slug:slug>/censor/sanctions/",
         SanctionListView.as_view(), name="sanctions"),
    path("<slug:slug>/censor/sanctions/create/",
         SanctionCreateView.as_view(), name="sanction_create"),
    path("<slug:slug>/censor/sanctions/<int:sanction_id>/edit/",
         SanctionUpdateView.as_view(), name="sanction_edit"),
    path("<slug:slug>/censor/sanctions/<int:sanction_id>/lift/",
         SanctionLiftView.as_view(), name="sanction_lift"),
    path("<slug:slug>/censor/sanctions/<int:sanction_id>/delete/",
         SanctionDeleteView.as_view(), name="sanction_delete"),

    path("<slug:slug>/sidebar-toggle/", sidebar_toggle, name="sidebar_toggle"),
    path("close-popup/", close_popup, name="close_popup"),
]
