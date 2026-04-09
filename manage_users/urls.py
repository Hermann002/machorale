from django.urls import path
from .views import RegisterView, LoginView, LogoutView, VerifyEmailView, resend_otp_views

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("verify-email/<int:user_id>/", VerifyEmailView.as_view(), name="verify_email"),
    path("resend-otp/<int:user_id>/", resend_otp_views, name="resend_otp"),
]