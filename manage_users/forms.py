from django import forms
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, OtpCode
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

input_class = "form-input flex w-full min-w-0 flex-1 rounded-lg text-[#111318] dark:text-white dark:bg-slate-800 border border-[#dbdfe6] dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-[#e0ad53]/20 focus:border-[#e0ad53] h-14 placeholder:text-[#616f89] px-4 text-base font-normal leading-normal"
input_class_2 = "form-input w-full rounded-xl border-slate-200 dark:border-slate-700 dark:bg-slate-900 dark:text-white focus:border-primary focus:ring-1 focus:ring-primary h-14 px-4 text-base transition-all outline-none"
input_class_password = "form-input w-full rounded-xl border-slate-200 dark:border-slate-700 dark:bg-slate-900 dark:text-white focus:border-primary focus:ring-1 focus:ring-primary h-14 px-4 pr-12 text-base transition-all outline-none"

class UserRegisterForm(forms.ModelForm):
    confirm_password = forms.CharField(max_length=100, widget=forms.PasswordInput(attrs={"class": f"{input_class_password}", "placeholder": "••••••••"}), label=_("Confirm Password"))
    
    class Meta:
        model = CustomUser
        fields = ["username", "email", "password"]
        widgets = {
            "username": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none transition",
                "placeholder": "Ex: Tagne Théophile"
            }),
            "email": forms.EmailInput(attrs={
                "class": "w-full px-4 py-3 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none transition",
                "placeholder": "exemple@email.com"
            }),
            "password": forms.PasswordInput(attrs={
                "class": "w-full px-4 py-3 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none transition pr-12",
                "placeholder": "••••••••"
            }),
        }
        labels = {
            "username": _("Nom d'utilisateur"),
            "email": _("Email"),
            "password": _("Mot de passe"),
        }
    
    def clean_username(self):
        username = self.cleaned_data.get("username")
        if username and CustomUser.objects.filter(username=username.lower()).exists():
            raise forms.ValidationError(_("Ce nom d'utilisateur est déjà utilisé."))
        return username.lower()

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and CustomUser.objects.filter(email=email.lower()).exists():
            raise forms.ValidationError(_("Cet email est déjà utilisé."))
        return email.lower()
    
    def clean_password(self):
        password = self.cleaned_data.get("password")
        try:
            validate_password(password, self.instance)
        except ValidationError as e:
            raise forms.ValidationError(e.messages)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", _("Les mots de passe ne correspondent pas."))
        
        return cleaned_data

class UserLoginForm(forms.Form):
    username = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"class": f"{input_class}", "placeholder": "Username"}), label=_("Username"))
    password = forms.CharField(max_length=100, widget=forms.PasswordInput(attrs={"class": f"{input_class}", "placeholder": "Password"}), label=_("Password"))
    class Meta:
        Model = CustomUser
        fields = ["username", "password"]

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")

        user = authenticate(username=username, password=password)
        if not user:
            raise forms.ValidationError(_("Invalid username or password."))
        
        cleaned_data["user"] = user
        return cleaned_data
    
class VerifyEmailForm(forms.Form):
    input_class_ver = ""
    otp_code = forms.CharField(max_length=6, widget=forms.TextInput(attrs={"placeholder": "Enter OTP Code"}), label=_("OTP Code"))

    class Meta:
        model = OtpCode
        fields = ["otp_code"]

class ResetPasswordRequestForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": f"{input_class}", "placeholder": "Enter your email"}), label=_("Email"))

    class Meta:
        model = CustomUser
        fields = ["email"]
        widgets = {
            "email": forms.EmailInput(attrs={
                "class": "w-full px-4 py-3 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none transition",
                "placeholder": "exemple@email.com"
            }),
        }
        labels = {
            "email": _("Email"),
        }
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        if not CustomUser.objects.filter(email=email.lower()).exists():
            raise forms.ValidationError(_("No account found with this email."))
        return cleaned_data
    
class ProfileForm(forms.Form):
    """Édition par l'utilisateur de ses propres infos (CustomUser + Profile)."""

    FIELD_CLASS = (
        "w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 rounded-xl border "
        "border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-primary/20 text-sm"
    )

    first_name = forms.CharField(max_length=150, required=True, label=_("Prénom"),
        widget=forms.TextInput(attrs={'class': FIELD_CLASS}))
    last_name = forms.CharField(max_length=150, required=False, label=_("Nom"),
        widget=forms.TextInput(attrs={'class': FIELD_CLASS}))
    email = forms.EmailField(required=True, label=_("Email"),
        widget=forms.EmailInput(attrs={'class': FIELD_CLASS}))
    contact = forms.CharField(max_length=15, required=False, label=_("Téléphone"),
        widget=forms.TextInput(attrs={'class': FIELD_CLASS, 'placeholder': "+237 6XX XXX XXX"}))

    MARITAL_CHOICES = (
        ('single', _('Single')),
        ('married', _('Married')),
        ('divorced', _('Divorced')),
        ('widowed', _('Widowed')),
    )
    PROFESSION_CHOICES = (
        ('', '---'),
        ('student', _('Student')),
        ('computer_scientist', _('Computer scientist')),
        ('nurse', _('Nurse')),
        ('teacher', _('Teacher')),
        ('engineer', _('Engineer')),
        ('doctor', _('Doctor')),
        ('lawyer', _('Lawyer')),
        ('other', _('Other')),
    )

    marital_status = forms.ChoiceField(required=False, choices=MARITAL_CHOICES,
        label=_("Statut matrimonial"),
        widget=forms.Select(attrs={'class': FIELD_CLASS}))
    christened = forms.BooleanField(required=False, label=_("Baptisé(e)"),
        widget=forms.CheckboxInput(attrs={'class': 'h-5 w-5 rounded text-primary'}))
    confirmed = forms.BooleanField(required=False, label=_("Confirmé(e)"),
        widget=forms.CheckboxInput(attrs={'class': 'h-5 w-5 rounded text-primary'}))
    joined_date = forms.DateField(required=False, label=_("Date d'adhésion"),
        widget=forms.DateInput(attrs={'class': FIELD_CLASS, 'type': 'date'}))
    dob = forms.DateField(required=False, label=_("Date de naissance"),
        widget=forms.DateInput(attrs={'class': FIELD_CLASS, 'type': 'date'}))
    profession_c = forms.ChoiceField(required=False, choices=PROFESSION_CHOICES,
        label=_("Profession"),
        widget=forms.Select(attrs={'class': FIELD_CLASS}))
    profession_o = forms.CharField(max_length=100, required=False, label=_("Profession (autre)"),
        widget=forms.TextInput(attrs={'class': FIELD_CLASS}))
    neighborhood = forms.CharField(max_length=100, required=False, label=_("Quartier"),
        widget=forms.TextInput(attrs={'class': FIELD_CLASS}))
    department = forms.CharField(max_length=100, required=False, label=_("Département"),
        widget=forms.TextInput(attrs={'class': FIELD_CLASS}))

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        initial = kwargs.pop('initial', {}) or {}
        if user is not None:
            initial.setdefault('first_name', user.first_name)
            initial.setdefault('last_name', user.last_name)
            initial.setdefault('email', user.email)
            from .models import Profile
            profile = getattr(user, 'profile', None)
            if profile is not None:
                initial.setdefault('contact', profile._contact)
                initial.setdefault('marital_status', profile.marital_status)
                initial.setdefault('christened', profile.christened)
                initial.setdefault('confirmed', profile.confirmed)
                initial.setdefault('joined_date', profile.joined_date)
                initial.setdefault('dob', profile.dob)
                initial.setdefault('profession_c', profile.profession_c)
                initial.setdefault('profession_o', profile.profession_o)
                initial.setdefault('neighborhood', profile.neighborhood)
                initial.setdefault('department', profile.department)
        kwargs['initial'] = initial
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        qs = CustomUser.objects.filter(email=email)
        if self.user is not None:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise forms.ValidationError(_("Cet email est déjà utilisé."))
        return email

    def save(self):
        from .models import Profile
        user = self.user
        cd = self.cleaned_data
        user.first_name = cd['first_name']
        user.last_name = cd.get('last_name', '')
        user.email = cd['email']
        user.save()
        profile, _created = Profile.objects.get_or_create(user=user)
        profile._contact = cd.get('contact') or None
        profile.marital_status = cd.get('marital_status') or profile.marital_status
        profile.christened = cd.get('christened') or False
        profile.confirmed = cd.get('confirmed') or False
        profile.joined_date = cd.get('joined_date')
        profile.dob = cd.get('dob')
        profile.profession_c = cd.get('profession_c') or ''
        profile.profession_o = cd.get('profession_o') or ''
        profile.neighborhood = cd.get('neighborhood') or ''
        profile.department = cd.get('department') or ''
        profile.save()
        return user


class SetNewPasswordForm(forms.Form):
    new_password = forms.CharField(max_length=100, widget=forms.PasswordInput(attrs={"class": f"{input_class_password}", "placeholder": "••••••••"}), label=_("New Password"))
    confirm_password = forms.CharField(max_length=100, widget=forms.PasswordInput(attrs={"class": f"{input_class_password}", "placeholder": "••••••••"}), label=_("Confirm New Password"))

    def clean_new_password(self):
        new_password = self.cleaned_data.get("new_password")
        try:
            validate_password(new_password)
        except ValidationError as e:
            raise forms.ValidationError(e.messages)
        return new_password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password and new_password != confirm_password:
            self.add_error("confirm_password", _("The two password fields didn't match."))
        
        return cleaned_data