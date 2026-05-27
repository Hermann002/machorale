from django.urls import path
from .views import RegisterView, LoginView, LogoutView, VerifyEmailView, resend_otp_views, ResetPasswordRequestView, ResetPasswordConfirmView, ProfileView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("verify-email/<int:user_id>/", VerifyEmailView.as_view(), name="verify_email"),
    path("resend-otp/<int:user_id>/", resend_otp_views, name="resend_otp"),
    path("reset-password-request/", ResetPasswordRequestView.as_view(), name="reset_password_request"),
    path("reset-password-confirm/<uuidb64>/<token>/", ResetPasswordConfirmView.as_view(), name="reset_password_confirm"),
    path("profile/", ProfileView.as_view(), name="profile"),
]