from django import forms
from django.utils.translation import gettext as _
from .models import Member
from django.contrib.auth import authenticate

input_class = "form-input flex w-full min-w-0 flex-1 rounded-lg text-[#111318] dark:text-white dark:bg-slate-800 border border-[#dbdfe6] dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-[#e0ad53]/20 focus:border-[#e0ad53] h-14 placeholder:text-[#616f89] px-4 text-base font-normal leading-normal"
input_class_2 = "form-input w-full rounded-xl border-slate-200 dark:border-slate-700 dark:bg-slate-900 dark:text-white focus:border-primary focus:ring-1 focus:ring-primary h-14 px-4 text-base transition-all outline-none"
input_class_password = "form-input w-full rounded-xl border-slate-200 dark:border-slate-700 dark:bg-slate-900 dark:text-white focus:border-primary focus:ring-1 focus:ring-primary h-14 px-4 pr-12 text-base transition-all outline-none"

class UserRegisterForm(forms.ModelForm):
    confirm_password = forms.CharField(max_length=100, widget=forms.PasswordInput(attrs={"class": f"{input_class_password}", "placeholder": "••••••••"}), label=_("Confirm Password"))
    username = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"class": f"{input_class_2}", "placeholder": "Ex: Tagne Théophile"}), label=_("Username"))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": f"{input_class_2}", "placeholder": "exemple@email.com"}), label=_("Email"))
    password = forms.CharField(max_length=100, widget=forms.PasswordInput(attrs={"class": f"{input_class_password}", "placeholder": "••••••••"}), label=_("Password"))

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
    username = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"class": f"{input_class}", "placeholder": "Username"}), label=_("Username"))
    password = forms.CharField(max_length=100, widget=forms.PasswordInput(attrs={"class": f"{input_class}", "placeholder": "Password"}), label=_("Password"))
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