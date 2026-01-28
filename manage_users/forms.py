from django import forms
from django.utils.translation import gettext as _
from .models import Member
from django.contrib.auth import authenticate

class UserRegisterForm(forms.ModelForm):
    confirm_password = forms.CharField(max_length=100, widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm Password"}), label=_("Confirm Password"))
    username = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Username"}), label=_("Username"))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "exemple@email.com"}), label=_("Email"))
    password = forms.CharField(max_length=100, widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"}), label=_("Password"))

    class Meta:
        model = Member
        fields = ["username", "email", "password", "confirm_password"]
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", _("Passwords do not match."))

        return cleaned_data

class UserLoginForm(forms.Form):
    username = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Username"}), label=_("Username"))
    password = forms.CharField(max_length=100, widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"}), label=_("Password"))
    class Meta:
        Model = Member
        fields = ["username", "password"]

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")

        member = authenticate(username=username, password=password)
        if not member:
            raise forms.ValidationError(_("Invalid username or password."))
        
        cleaned_data["member"] = member

        return cleaned_data