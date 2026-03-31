from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from .models import Chorale
from manage_users.models import CustomUser

class CreateChoraleForm(forms.Form):
    """Collecte les données de base - PAS un ModelForm"""
    
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
            "placeholder": _("Ex: Paris, France")
        })
    )
    
    logo = forms.ImageField(
        required=False,
        label=_("Logo de la chorale"),
        widget=forms.ClearableFileInput(attrs={
            "class": "w-full px-4 py-3 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
        })
    )

    # ========== VALIDATIONS PERSONNALISÉES ==========
    
    def clean_name(self):
        """Vérifie que le nom n'est pas déjà utilisé"""
        name = self.cleaned_data.get("name")
        
        if not name:
            raise ValidationError(_("Le nom du groupe est requis."))
        
        # Vérifier si le nom existe déjà dans la base
        if Chorale.objects.filter(name__iexact=name).exists():
            raise ValidationError(_("Ce nom de chorale est déjà utilisé."))
        
        return name
    
    def clean_established_date(self):
        """Vérifie que la date n'est pas dans le futur"""
        established_date = self.cleaned_data.get("established_date")
        
        if established_date:
            from datetime import date
            if established_date > date.today():
                raise ValidationError(_("La date de création ne peut pas être dans le futur."))
        
        return established_date
    
    def clean_location(self):
        """Nettoie et valide le champ location"""
        location = self.cleaned_data.get("location")
        
        if location:
            # Supprimer les espaces en trop
            location = location.strip()
            
            # Vérification minimale : au moins 2 caractères
            if len(location) < 2:
                raise ValidationError(_("Le lieu doit contenir au moins 2 caractères."))
        
        return location
    
    def clean_logo(self):
        """Valide le fichier logo"""
        logo = self.cleaned_data.get("logo")
        
        if logo:
            # Vérifier la taille (max 5MB)
            if logo.size > 5 * 1024 * 1024:
                raise ValidationError(_("Le fichier ne doit pas dépasser 5MB."))
            
            # Vérifier le type de fichier
            valid_extensions = ['jpg', 'jpeg', 'png', 'gif']
            extension = logo.name.split('.')[-1].lower()
            
            if extension not in valid_extensions:
                raise ValidationError(_("Format de fichier non autorisé. Formats acceptés : JPG, PNG, GIF."))
        
        return logo


class ConfChoraleForm(forms.Form):
    """Collecte les paramètres de configuration - PAS un ModelForm"""
    
    slogan = forms.CharField(
        required=False,
        max_length=255,
        label=_("Slogan"),
        widget=forms.TextInput(attrs={
            "class": "form-input flex w-full rounded-lg text-[#0d121b] dark:text-white focus:outline-0 focus:ring-2 focus:ring-primary/20 border border-[#cfd7e7] dark:border-slate-700 bg-white dark:bg-slate-800 focus:border-primary h-14 placeholder:text-[#4c669a] dark:placeholder:text-slate-500 p-4 text-base font-normal leading-normal",
        })
    )

    contact_email = forms.EmailField(
        required=False,
        label=_("Email de contact"),
        widget=forms.EmailInput(attrs={
            "class": "form-input flex w-full rounded-lg text-[#0d121b] dark:text-white focus:outline-0 focus:ring-2 focus:ring-primary/20 border border-[#cfd7e7] dark:border-slate-700 bg-white dark:bg-slate-800 focus:border-primary h-14 placeholder:text-[#4c669a] dark:placeholder:text-slate-500 p-4 text-base font-normal leading-normal",
        })
    )

    contact_phone = forms.CharField(
        required=False,
        max_length=20,
        label=_("Téléphone de contact"),
        widget=forms.TextInput(attrs={
            "class": "form-input flex w-full rounded-lg text-[#0d121b] dark:text-white focus:outline-0 focus:ring-2 focus:ring-primary/20 border border-[#cfd7e7] dark:border-slate-700 bg-white dark:bg-slate-800 focus:border-primary h-14 placeholder:text-[#4c669a] dark:placeholder:text-slate-500 p-4 text-base font-normal leading-normal",
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
        }),
    )

    # ========== VALIDATIONS PERSONNALISÉES ==========
    
    def clean_slogan(self):
        """Valide le slogan"""
        slogan = self.cleaned_data.get("slogan")
        
        if slogan:
            # Supprimer les espaces en trop
            slogan = slogan.strip()
            
            # Limiter à 255 caractères (déjà fait par max_length, mais double vérification)
            if len(slogan) > 255:
                raise ValidationError(_("Le slogan ne doit pas dépasser 255 caractères."))
        
        return slogan
    
    def clean_contact_email(self):
        """Valide l'email de contact"""
        email = self.cleaned_data.get("contact_email")
        
        if email:
            email = email.strip()
            
            # Vérifier le format email (déjà fait par EmailField, mais on peut ajouter des règles)
            if len(email) > 254:
                raise ValidationError(_("L'adresse email est trop longue."))
        
        return email
    
    def clean_contact_phone(self):
        """Valide et nettoie le numéro de téléphone"""
        phone = self.cleaned_data.get("contact_phone")
        
        if phone:
            # Supprimer les espaces, parenthèses, tirets
            cleaned_phone = ''.join(c for c in phone if c.isdigit() or c == '+')
            
            # Vérifier la longueur minimale (au moins 7 chiffres)
            digits_only = ''.join(c for c in cleaned_phone if c.isdigit())
            
            if len(digits_only) < 7:
                raise ValidationError(_("Le numéro de téléphone doit contenir au moins 7 chiffres."))
            
            if len(digits_only) > 15:
                raise ValidationError(_("Le numéro de téléphone est trop long."))
            
            phone = cleaned_phone
        
        return phone
    
    def clean_meeting_frequency(self):
        """Valide la fréquence des réunions"""
        frequency = self.cleaned_data.get("meeting_frequency")
        
        # Si le champ est requis=False et non fourni, c'est OK
        if not frequency:
            return None
        
        # Vérifier que la valeur est dans les choix autorisés
        valid_choices = dict([
            ("weekly", _("Hebdomadaire")),
            ("biweekly", _("Bihebdomadaire")),
            ("monthly", _("Mensuelle")),
            ("yearly", _("Annuelle")),
        ])
        
        if frequency not in valid_choices:
            raise ValidationError(_("Fréquence de réunion invalide."))
        
        return frequency

class AddMemberForm(forms.Form):
    """Formulaire pour ajouter un membre à la chorale"""
    
    email = forms.EmailField(
        required=True,
        label=_("Email du membre"),
        widget=forms.EmailInput(attrs={
            "class": "w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 border-none rounded-xl focus:ring-2 focus:ring-primary/20 transition-all font-medium placeholder:text-slate-300",
            "placeholder": _("Entrez l'email du membre à ajouter")
        })
    )
    first_name = forms.CharField(
        required=True,
        max_length=150,
        label=_("Nom du membre"),
        widget=forms.TextInput(attrs={
            "class": "w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 border-none rounded-xl focus:ring-2 focus:ring-primary/20 transition-all font-medium placeholder:text-slate-300",
            "placeholder": _("Ex: Jean Dupont")
        })
    )
    last_name = forms.CharField(
        required=False,
        max_length=150,
        label=_("Prénom du membre"),
        widget=forms.TextInput(attrs={
            "class": "w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 border-none rounded-xl focus:ring-2 focus:ring-primary/20 transition-all font-medium placeholder:text-slate-300",
            "placeholder": _("Ex: Jean Dupont")
        })
    )
    contact_phone = forms.CharField(
        required=False,
        max_length=20,
        label=_("Numéro de téléphone"),
        widget=forms.TextInput(attrs={
            "class": "w-full pl-12 pr-4 py-3 bg-slate-50 dark:bg-slate-800 border-none rounded-xl focus:ring-2 focus:ring-primary/20 transition-all font-medium placeholder:text-slate-300",
            "placeholder": _("Ex: 01 23 45 67 89")
        })
    )
    
    role = forms.ChoiceField(
        required=True,
        label=_("Rôle dans la chorale"),
        choices=CustomUser.ROLE_CHOICES,
        widget=forms.Select(attrs={
            "class": "w-full appearance-none px-4 py-3 bg-slate-50 dark:bg-slate-800 border-none rounded-xl focus:ring-2 focus:ring-primary/20 transition-all font-medium text-on-surface cursor-pointer",
        }),
    )

    def clean_email(self):
        """Valide l'email de contact"""
        email = self.cleaned_data.get("semail")
        
        if email:
            email = email.strip()
            
            # Vérifier le format email (déjà fait par EmailField, mais on peut ajouter des règles)
            if len(email) > 254:
                raise ValidationError(_("L'adresse email est trop longue."))
        
        return email
    
    def clean_contact_phone(self):
        """Valide et nettoie le numéro de téléphone"""
        phone = self.cleaned_data.get("contact_phone")
        
        if phone:
            # Supprimer les espaces, parenthèses, tirets
            cleaned_phone = ''.join(c for c in phone if c.isdigit() or c == '+')
            
            # Vérifier la longueur minimale (au moins 7 chiffres)
            digits_only = ''.join(c for c in cleaned_phone if c.isdigit())
            
            if len(digits_only) < 7:
                raise ValidationError(_("Le numéro de téléphone doit contenir au moins 7 chiffres."))
            
            if len(digits_only) > 15:
                raise ValidationError(_("Le numéro de téléphone est trop long."))
            
            phone = cleaned_phone
        
        return phone