from django.shortcuts import render
from .forms import UserRegisterForm, UserLoginForm
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView
from django.contrib.auth import login, logout
from django.contrib import messages


class RegisterView(TemplateView):
    template_name = "landing/pages/register.html"

    def get(self, request, *args, **kwargs):
        form = UserRegisterForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect("{% url 'login' %}")
        return render(request, self.template_name, {"form": form})

class LoginView(TemplateView):
    template_name = "landing/pages/login.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            message = "You're already logged in. Please log out first to switch accounts."
            messages.info(request, message)
            return HttpResponseRedirect("/")
        form = UserLoginForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = UserLoginForm(request.POST)
        message = ""
        if form.is_valid():
            login(request, form.cleaned_data["member"])
            # return HttpResponseRedirect("{% url 'dashboard' %}")
            return HttpResponseRedirect("/")
        message = "Login failed. Please correct the errors below."
        return render(request, self.template_name, {"form": form, "message": message})

class LogoutView(TemplateView):
    def get(self, request, *args, **kwargs):
        logout(request)
        return HttpResponseRedirect("/")