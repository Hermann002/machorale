from django.shortcuts import render
from .forms import UserRegisterForm, UserLoginForm
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.hashers import make_password
from .utils import send_code_to_user
from manage_users.models import OtpCode, CustomUser
from django.views.generic.edit import UpdateView

from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.core.cache import cache
from django_ratelimit.exceptions import Ratelimited

@method_decorator(ratelimit(key='ip', rate='5/h', method='POST', block=True), name='dispatch')
class RegisterView(TemplateView):
    template_name = "landing/pages/register.html"

    def get(self, request, *args, **kwargs):
        form = UserRegisterForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False) 
            user.set_password(form.cleaned_data["password"])
            user.save()
            otp_record, created = OtpCode.objects.get_or_create(user=user)
            code = otp_record.generate_new_code()
            try:
                print("Attempting to send OTP email to {}".format(user.email))
                send_code_to_user(email=user.email, code=code)
            except Exception as e:
                print(f"Error sending email: {e}")
                raise(e)
            messages.success(request, "Account created successfully! Please verify your email.")
            return HttpResponseRedirect(reverse("verify_email", kwargs={"user_id": user.id}))
        return render(request, self.template_name, {"form": form})

@method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True), name='dispatch')
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
            user = form.cleaned_data.get("user")
            if user is not None:
                login(request, user)
                try:
                    slug = user.managed_group.slug if hasattr(user, 'managed_group') else user.chorales.first().slug if user.chorales.exists() else None
                    cache.set("slug", slug)
                except Exception as e:
                    print(f"Error retrieving slug: {e}")
                if slug:
                    return HttpResponseRedirect(reverse("dashboard", kwargs={"slug": slug}))
                else:
                    return HttpResponseRedirect(reverse("create_chorale"))
            else:
                messages.error(request, "Invalid credentials. Please try again.")
        else:
            messages.error(request, "Invalid username or password.")
        return render(request, self.template_name, {"form": form})

@method_decorator(ratelimit(key='ip', rate='4/m', method='POST', block=True), name='dispatch')
class VerifyEmailView(TemplateView):
    template_name = "landing/pages/verify_email.html"

    def get(self, request, *args, **kwargs):
        try:
            user_id = kwargs.get("user_id")
            user = CustomUser.objects.get(id=user_id)
            return render(request, self.template_name, {"user_id": user.id})
        except CustomUser.DoesNotExist:
            messages.error(request, "User not found ! register first")
            return HttpResponseRedirect(reverse("register"))


    def post(self, request, user_id=None, *args, **kwargs):
        code = request.POST.get("otp_code")
        try:
            otp_record = OtpCode.objects.get(otp_code=code)
            user = otp_record.user
            if otp_record.otp_expired() or otp_record.used:
                messages.error(request, "OTP code has expired. Please request a new code.")
                return render(request, self.template_name)

            if not user.is_verify:
                user.is_verify = True
                user.save()
                otp_record.used = True
                otp_record.save()
                login(request, user)
                messages.success(request, "Email verified successfully!")
                return HttpResponseRedirect(reverse("create_chorale"))
            else:
                messages.info(request, "Email is already verified. Please log in.")
                return HttpResponseRedirect(reverse("login"))
        except OtpCode.DoesNotExist:
            print("No OTP record found for code:", code)
            messages.error(request, "No OTP record found. Please request a new code.")
            return render(request, self.template_name)
        except Ratelimited:
            messages.error(request, "You rate a limit, please wait 1 minute and retry !")

class LogoutView(TemplateView):
    def get(self, request, *args, **kwargs):
        logout(request)
        return HttpResponseRedirect("/")
    

def resend_otp_views(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
        user_email = user.email
        otp = OtpCode.objects.filter(user=user).last()
        if otp and not otp.otp_expired():
            otp.used = True
        otp_record = OtpCode.objects.create(user=user)
        code = otp_record.generate_new_code()
        send_code_to_user(email=user_email, code=code)
        messages.success(request, "OTP code resent successfully! Please check your email.")
    except CustomUser.DoesNotExist:
        messages.error(request, "User not found.")
    return HttpResponseRedirect(reverse("verify_email", kwargs={"user_id": user_id}))