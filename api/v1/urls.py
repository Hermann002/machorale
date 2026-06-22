from django.urls import path

from . import chorales, members, views

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
]
