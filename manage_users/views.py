from django.shortcuts import render
from .forms import UserRegisterForm, UserLoginForm
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView
from django.contrib.auth import login, logout
from django.contrib import messages


class RegisterView(TemplateView):
    template_name = "landing/pages/register.html"
    message = ""

    def get(self, request, *args, **kwargs):
        form = UserRegisterForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect("{% url 'login' %}")
        message = "Registration failed. Please correct the errors below."
        messages.error(request, message)
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
            user = form.cleaned_data.get("member")
            if user is not None:
                login(request, user)
                return HttpResponseRedirect("/a/dashboard")
            else:
                messages.error(request, "Invalid credentials. Please try again.")
        else:
            messages.error(request, "Invalid username or password.")
        return render(request, self.template_name, {"form": form})

class LogoutView(TemplateView):
    def get(self, request, *args, **kwargs):
        logout(request)
        return HttpResponseRedirect("/")