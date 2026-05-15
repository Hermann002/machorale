from django.shortcuts import render
from .forms import UserRegisterForm, UserLoginForm, SetNewPasswordForm, ResetPasswordRequestForm
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.hashers import make_password
from .utils import send_code_to_user, send_password_reset_link
from manage_users.models import OtpCode, CustomUser
from django.views.generic.edit import UpdateView
from django.core.exceptions import ObjectDoesNotExist
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.urls import reverse_lazy
from django.core.cache import cache

from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited

@method_decorator(ratelimit(key='ip', rate='10/m', method='POST', block=True), name='dispatch') #TODO définir un template 
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
            cache.set(f"user_id", user.id)
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
                slug = None
                try:
                    slug = user.managed_group.slug
                except ObjectDoesNotExist:
                    first_chorale = user.chorales.only('slug').first()
                    if first_chorale:
                        slug = first_chorale.slug

                if slug:
                    cache.set("slug", slug)
                    cache.set("user_id", user.id)
                    return HttpResponseRedirect(reverse("dashboard", kwargs={"slug": slug}))
                return HttpResponseRedirect(reverse("create_chorale"))
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
        cache.clear()
        logout(request)
        return HttpResponseRedirect("/")
    

@ratelimit(key='ip', rate='3/m', method='GET', block=True)
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
    except Ratelimited:
        messages.error(request, "Rate limit exceeded, please wait before trying again.")
    return HttpResponseRedirect(reverse("verify_email", kwargs={"user_id": user_id}))

class ResetPasswordRequestView(TemplateView):
    template_name = "landing/pages/reset_password_request.html"
    form_class = ResetPasswordRequestForm

    @method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {"form": form})
    
    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("email")
            try:
                user = CustomUser.objects.get(email=email)
                uuidb64 = urlsafe_base64_encode(force_bytes(user.id))
                token_generator = PasswordResetTokenGenerator()
                token = token_generator.make_token(user)
                print(f"Attempting to send password reset email to {email} with uidb64: {uuidb64} and token: {token}")
                send_password_reset_link(email, uuidb64, token)
                messages.success(request, "Password reset link sent! Please check your email.")
                return HttpResponseRedirect(reverse("reset_password_request"))
            except CustomUser.DoesNotExist:
                messages.error(request, "No account found with that email address.")
            except Ratelimited:
                messages.error(request, "Rate limit exceeded, please wait before trying again.")
        else:
            messages.error(request, "Please enter a valid email address.")
        return render(request, self.template_name, {"form": form})
    
class ResetPasswordConfirmView(TemplateView):
    template_name = "landing/pages/reset_password_confirm.html"
    form_class = SetNewPasswordForm

    @method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        uidb64 = kwargs.get("uuidb64")
        token = kwargs.get("token")
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(id=uid)
            token_generator = PasswordResetTokenGenerator()
            if token_generator.check_token(user, token):
                form = self.form_class()
                return render(request, self.template_name, {"form": form, "uidb64": uidb64, "token": token})
            messages.error(request, "Invalid or expired password reset link.")
            return HttpResponseRedirect(reverse("reset_password_request"))
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            messages.error(request, "Invalid password reset link.")
            return HttpResponseRedirect(reverse("reset_password_request"))

    def post(self, request, *args, **kwargs):
        uidb64 = request.POST.get("uidb64") or kwargs.get("uuidb64")
        token = request.POST.get("token") or kwargs.get("token")
        form = self.form_class(request.POST)

        if not uidb64 or not token:
            messages.error(request, "Invalid password reset request.")
            return HttpResponseRedirect(reverse("reset_password_request"))

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(id=uid)
            token_generator = PasswordResetTokenGenerator()
            if not token_generator.check_token(user, token):
                messages.error(request, "Invalid or expired password reset link.")
                return HttpResponseRedirect(reverse("reset_password_request"))
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            messages.error(request, "Invalid password reset link.")
            return HttpResponseRedirect(reverse("reset_password_request"))
        except Ratelimited:
            messages.error(request, "Rate limit exceeded, please wait before trying again.")
            return render(request, self.template_name, {"form": form, "uidb64": uidb64, "token": token})

        if form.is_valid():
            user.password = make_password(form.cleaned_data.get("new_password"))
            user.save()
            messages.success(request, "Your password has been reset successfully! You can now log in.")
            return HttpResponseRedirect(reverse("login"))

        return render(request, self.template_name, {"form": form, "uidb64": uidb64, "token": token})