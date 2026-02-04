from django.shortcuts import render
from .forms import UserRegisterForm, UserLoginForm
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView
from django.contrib.auth import login, logout
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.hashers import make_password
from .utils import send_code_to_user
from manage_users.models import OtpCode


class RegisterView(TemplateView):
    template_name = "landing/pages/register.html"
    message = ""

    def get(self, request, *args, **kwargs):
        form = UserRegisterForm()
        return render(request, self.template_name, {"form": form})


    def post(self, request, *args, **kwargs):
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False) 
            user.set_password(form.cleaned_data["password"])
            user.save()
            otp_record, created = OtpCode.objects.get_or_create(super_admin_chorale=user)
            code = otp_record.generate_new_code()
            try:
                send_code_to_user(email=user.email, code=code)
            except Exception as e:
                print(f"Error sending email: {e}")
                raise(e)
            messages.success(request, "Account created successfully! Please verify your email.")
            return HttpResponseRedirect(reverse("verify_email"))
        # message = "Registration failed. Please correct the errors below."
        # messages.error(request, message)
        return render(request, self.template_name, {"form": form})

class LoginView(TemplateView):
    template_name = "landing/pages/login.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(
                request,
                "You're already logged in. Please log out first to switch accounts."
            )
            return HttpResponseRedirect("/")
        form = UserLoginForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = UserLoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data.get("super_admin_chorale")
            if user is not None:
                login(request, user)
                return HttpResponseRedirect(reverse("dashboard"))
            else:
                messages.error(request, "Invalid credentials. Please try again.")
        else:
            messages.error(request, "Invalid username or password.")
        return render(request, self.template_name, {"form": form})

class VerifyEmailView(TemplateView):
    template_name = "landing/pages/verify_email.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        code = request.POST.get("otp_code")
        try:
            otp_record = OtpCode.objects.get(otp_code=code)
            super_admin_chorale = otp_record.super_admin_chorale
            if otp_record.otp_expired():
                messages.error(request, "OTP code has expired. Please request a new code.")
                return render(request, self.template_name)

            if not super_admin_chorale.is_verify:
                super_admin_chorale.is_verify = True
                super_admin_chorale.save()
                otp_record.used = True
                otp_record.save()
                login(request, super_admin_chorale)
                messages.success(request, "Email verified successfully!")
                return HttpResponseRedirect(reverse("create_chorale"))
            else:
                messages.info(request, "Email is already verified. Please log in.")
                return HttpResponseRedirect(reverse("login"))
        except OtpCode.DoesNotExist:
            print("No OTP record found for code:", code)
            messages.error(request, "No OTP record found. Please request a new code.")
            return render(request, self.template_name)

class LogoutView(TemplateView):
    def get(self, request, *args, **kwargs):
        logout(request)
        return HttpResponseRedirect("/")