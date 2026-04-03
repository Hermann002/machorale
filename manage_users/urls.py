from django.urls import path
from .views import RegisterView, LoginView, LogoutView, VerifyEmailView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify_email"),
    # path("resend-otp/", ResendOtpView.as_view(), name="resend_otp")
]