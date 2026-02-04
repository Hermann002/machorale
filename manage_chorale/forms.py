from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Chorale

class CreateChoraleForm(forms.Form):
    name = forms.CharField(
        max_length=150,
        label=_("Nom de la chorale"),
        widget=forms.TextInput(attrs={
            "class": "w-full px-4 py-3 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none transition",
            "placeholder": _("Ex: Chorale Harmonie")
        })
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
            "class": "w-full px-4 py-3 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none transition",
            "placeholder": _("Ex: Paris, France ")
        })
    )

    class Meta:
        model = Chorale
        fields = ["name", "description", "established_date", "location"]
    
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
