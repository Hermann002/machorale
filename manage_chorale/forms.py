from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Chorale

class CreateChoraleForm(forms.ModelForm):
    name = forms.CharField(
        max_length=150,
        label=_("Nom du groupe"),
        widget=forms.TextInput(attrs={
            "class": "form-input flex w-full rounded-lg text-[#0d121b] dark:text-white focus:outline-0 focus:ring-2 focus:ring-primary/20 border border-[#cfd7e7] dark:border-slate-700 bg-white dark:bg-slate-800 focus:border-primary h-14 placeholder:text-[#4c669a] dark:placeholder:text-slate-500 p-4 text-base font-normal leading-normal",
            "placeholder": _("Ex: Chorale Harmonie")
        })
    )

    type_c = forms.ChoiceField(
        choices=Chorale.TYPE_CHOICES,
        label=_("Type de groupe"),
        widget=forms.Select(attrs={
            "class": "form-select flex w-full rounded-lg text-[#0d121b] dark:text-white focus:outline-0 focus:ring-2 focus:ring-primary/20 border border-[#cfd7e7] dark:border-slate-700 bg-white dark:bg-slate-800 focus:border-primary h-14 p-4 text-base font-normal leading-normal",
            "placeholder": _("Sélectionner le type de groupe"),
        }),  
    )

    description = forms.CharField(
        required=False,
        label=_("Description"),
        widget=forms.Textarea(attrs={
            "class": "w-full px-4 py-3 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none transition",
            "placeholder": _("Une brève description de la chorale"),
            "rows": 4
        })
    )
    established_date = forms.DateField(
        required=False,
        label=_("Date de création"),
        widget=forms.DateInput(attrs={
            "class": "w-full px-4 py-3 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none transition",
            "type": "date"
        })
    )
    location = forms.CharField(
        required=False,
        max_length=255,
        label=_("Lieu"),
        widget=forms.TextInput(attrs={
            "class": "form-input flex w-full rounded-lg text-[#0d121b] dark:text-white focus:outline-0 focus:ring-2 focus:ring-primary/20 border border-[#cfd7e7] dark:border-slate-700 bg-white dark:bg-slate-800 focus:border-primary h-14 placeholder:text-[#4c669a] dark:placeholder:text-slate-500 pl-12 pr-4 text-base font-normal leading-normal",
            "placeholder": _("Ex: Paris, France ")
        })
    )
    logo = forms.ImageField(
        required=False,
        label=_("Logo de la chorale"),
        widget=forms.ClearableFileInput(attrs={
            "class": "w-full px-4 py-3 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
        })
    )

    class Meta:
        model = Chorale
        fields = ["name", "type_c", "description", "established_date", "location"]
    
    def clean_name(self):
        name = self.cleaned_data.get("name")
        if name and Chorale.objects.filter(name=name).exists():
            raise forms.ValidationError(_("Ce nom de chorale est déjà utilisé."))
        return name
    
    def clean_established_date(self):
        established_date = self.cleaned_data.get("established_date")
        if established_date and established_date > forms.fields.datetime.date.today():
            raise forms.ValidationError(_("La date de création ne peut pas être dans le futur."))
        return established_date
    
    def clean_location(self):
        location = self.cleaned_data.get("location")
        return location

class ConfChoraleForm(CreateChoraleForm):

    contact_email = forms.EmailField(
        required=False,
        label=_("Email de contact"),
        widget=forms.EmailInput(attrs={
            "class": "form-input flex w-full rounded-lg text-[#0d121b] dark:text-white focus:outline-0 focus:ring-2 focus:ring-primary/20 border border-[#cfd7e7] dark:border-slate-700 bg-white dark:bg-slate-800 focus:border-primary h-14 placeholder:text-[#4c669a] dark:placeholder:text-slate-500 pl-12 pr-4 text-base font-normal leading-normal",
            })
    )

    contact_phone = forms.CharField(
        required=False,
        max_length=20,
        label=_("Téléphone de contact"),
        widget=forms.TextInput(attrs={
            "class": "form-input flex w-full rounded-lg text-[#0d121b] dark:text-white focus:outline-0 focus:ring-2 focus:ring-primary/20 border border-[#cfd7e7] dark:border-slate-700 bg-white dark:bg-slate-800 focus:border-primary h-14 placeholder:text-[#4c669a] dark:placeholder:text-slate-500 pl-12 pr-4 text-base font-normal leading-normal",
            })
    )

    slogan = forms.CharField(
        required=False,
        max_length=255,
        label=_("Slogan"),
        widget=forms.TextInput(attrs={
            "class": "form-input flex w-full rounded-lg text-[#0d121b] dark:text-white focus:outline-0 focus:ring-2 focus:ring-primary/20 border border-[#cfd7e7] dark:border-slate-700 bg-white dark:bg-slate-800 focus:border-primary h-14 placeholder:text-[#4c669a] dark:placeholder:text-slate-500 pl-12 pr-4 text-base font-normal leading-normal",
            })
    )

    meeting_frequency = forms.ChoiceField(
        required=False,
        label=_("Fréquence des réunions"),
        choices=[
            ("weekly", _("Hebdomadaire")),
            ("biweekly", _("Bihebdomadaire")),
            ("monthly", _("Mensuelle")),
            ("yearly", _("Annuelle")),
        ],
        widget=forms.Select(attrs={
            "class": "form-select flex w-full rounded-lg text-[#0d121b] dark:text-white focus:outline-0 focus:ring-2 focus:ring-primary/20 border border-[#cfd7e7] dark:border-slate-700 bg-white dark:bg-slate-800 focus:border-primary h-14 p-4 text-base font-normal leading-normal",
            "placeholder": _("Sélectionner le type de groupe"),
        }),
    )

    class Meta:
        model = Chorale
        fields = ["contact_email", "contact_phone", "slogan", "meeting_frequency"]
