from django.urls import path

from . import attendance, chorales, events, finances, members, views

app_name = "v1"

urlpatterns = [
    path("ping/", views.ping, name="ping"),
    # Sprint 1 — authentication (OTP-email flow → JWT)
    path("auth/otp/request/", views.OtpRequestView.as_view(), name="otp_request"),
    path("auth/otp/verify/", views.OtpVerifyView.as_view(), name="otp_verify"),
    path("auth/refresh/", views.RefreshView.as_view(), name="token_refresh"),
    path("auth/me/", views.MeView.as_view(), name="me"),
    # Sprint 2 — chorale context & dashboard
    path("chorales/", chorales.ChoraleListView.as_view(), name="chorale_list"),
    path(
        "chorales/<slug:slug>/dashboard/",
        chorales.DashboardView.as_view(),
        name="dashboard",
    ),
    # Sprint 3 — members CRUD
    path(
        "chorales/<slug:slug>/members/",
        members.MemberListCreateView.as_view(),
        name="member_list",
    ),
    path(
        "chorales/<slug:slug>/members/<int:pk>/",
        members.MemberDetailView.as_view(),
        name="member_detail",
    ),
    # Sprint 4 — events CRUD
    path(
        "chorales/<slug:slug>/events/",
        events.EventListCreateView.as_view(),
        name="event_list",
    ),
    path(
        "chorales/<slug:slug>/events/<int:pk>/",
        events.EventDetailView.as_view(),
        name="event_detail",
    ),
    # Sprint 5 — attendance
    path(
        "chorales/<slug:slug>/events/<int:pk>/attendance/",
        attendance.EventAttendanceView.as_view(),
        name="event_attendance",
    ),
    path(
        "chorales/<slug:slug>/members/<int:pk>/absences/",
        attendance.MemberAbsenceListView.as_view(),
        name="member_absences",
    ),
    # Sprint 6 — contributions & finances
    path(
        "chorales/<slug:slug>/contributions/",
        finances.ContributionListCreateView.as_view(),
        name="contribution_list",
    ),
    path(
        "chorales/<slug:slug>/contributions/<int:pk>/",
        finances.ContributionDetailView.as_view(),
        name="contribution_detail",
    ),
    path(
        "chorales/<slug:slug>/contributions/<int:pk>/payments/",
        finances.PaymentListCreateView.as_view(),
        name="payment_list",
    ),
    path(
        "chorales/<slug:slug>/cashflows/",
        finances.CashFlowListCreateView.as_view(),
        name="cashflow_list",
    ),
    path(
        "chorales/<slug:slug>/cashflows/<int:pk>/",
        finances.CashFlowDetailView.as_view(),
        name="cashflow_detail",
    ),
]
