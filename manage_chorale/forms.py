from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Chorale, ChoraleEvent, Contribution, MemberContribution, CashFlow, Absence, Sanction
from manage_users.models import CustomUser

# Classe Tailwind partagée pour les inputs/selects des forms du tableau de bord.
# Mutualisée pour éviter le drift visuel et garder un seul endroit à modifier
# quand le design system évolue.
DASHBOARD_FIELD_CLASS = (
    "w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 rounded-xl border "
    "border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-primary/20 text-sm"
)

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
            location = location.strip()
            
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
    
    def clean_slogan(self):
        """Valide le slogan"""
        slogan = self.cleaned_data.get("slogan")
        
        if slogan:
            slogan = slogan.strip()
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

class ChoraleEventForm(forms.ModelForm):
    class Meta:
        model = ChoraleEvent
        fields = ["title", "description", "location", "date", "event_type", "expenses", "income", "report_file"]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-primary/20 text-sm",
                "placeholder": _("Titre de l'événement")
            }),
            "description": forms.Textarea(attrs={
                "class": "w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-primary/20 text-sm",
                "rows": 4,
                "placeholder": _("Description de l'événement")
            }),
            "location": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-primary/20 text-sm",
                "placeholder": _("Lieu de l'événement")
            }),
            "date": forms.DateTimeInput(attrs={
                "class": "w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-primary/20 text-sm",
                "type": "datetime-local"
            }),
            "event_type": forms.Select(attrs={
                "class": "w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-primary/20 text-sm",
            }),
            "expenses": forms.NumberInput(attrs={
                "class": "w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-primary/20 text-sm",
                "placeholder": "0.00",
                "step": "0.01",
                "min": "0",
            }),
            "income": forms.NumberInput(attrs={
                "class": "w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-primary/20 text-sm",
                "placeholder": "0.00",
                "step": "0.01",
                "min": "0",
            }),
            "report_file": forms.ClearableFileInput(attrs={
                "class": "w-full text-sm text-slate-500"
            }),
        }

    def clean_date(self):
        event_date = self.cleaned_data.get("date")
        if event_date and event_date < timezone.now():
            # En mode édition, on tolère la date actuelle de l'événement (déjà passée)
            # afin de pouvoir modifier d'autres champs (finances, rapport, etc.)
            # sans être forcé de reprogrammer l'événement.
            if self.instance.pk and event_date == self.instance.date:
                return event_date
            raise ValidationError(_("La date de l'événement ne peut pas être dans le passé."))
        return event_date

    def clean_report_file(self):
        report_file = self.cleaned_data.get("report_file")
        if report_file:
            if report_file.size > 10 * 1024 * 1024:
                raise ValidationError(_("Le fichier doit être inférieur à 10MB."))

            valid_extensions = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png']
            extension = report_file.name.split('.')[-1].lower()
            if extension not in valid_extensions:
                raise ValidationError(_("Format de fichier non autorisé. Formats acceptés : PDF, DOC, DOCX, JPG, PNG."))
        return report_file

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
        choices=CustomUser.CHORALE_ROLE_CHOICES,
        widget=forms.Select(attrs={
            "class": "w-full appearance-none px-4 py-3 bg-slate-50 dark:bg-slate-800 border-none rounded-xl focus:ring-2 focus:ring-primary/20 transition-all font-medium text-on-surface cursor-pointer",
        }),
    )

    def clean_email(self):
        """Valide l'email de contact"""
        email = self.cleaned_data.get("email")
        
        if email:
            email = email.strip()
            
            # Vérifier le format email (déjà fait par EmailField, mais on peut ajouter des règles)
            if len(email) > 254:
                raise ValidationError(_("L'adresse email est trop longue."))
        
        return email


class MemberRoleForm(forms.ModelForm):
    """Formulaire pour mettre à jour le rôle du membre dans la chorale"""

    class Meta:
        model = CustomUser
        fields = ['chorale_role']
        labels = {
            'chorale_role': _('Rôle dans la chorale'),
        }
        widgets = {
            'chorale_role': forms.Select(attrs={
                "class": "w-full appearance-none px-4 py-3 bg-slate-50 dark:bg-slate-800 border-none rounded-xl focus:ring-2 focus:ring-primary/20 transition-all font-medium text-on-surface cursor-pointer",
            }),
        }

    
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

# ── Trésorier ──────────────────────────────────────────────────────────────


class ContributionForm(forms.ModelForm):
    """CRUD d'un type de cotisation. `chorale` est injectée par la vue,
    jamais saisie par l'utilisateur (sécurité : un trésorier ne doit pas
    pouvoir forger un POST visant une autre chorale)."""

    class Meta:
        model = Contribution
        fields = ['title', 'amount', 'target_amount', 'description', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': DASHBOARD_FIELD_CLASS,
                'placeholder': _("Ex: Cotisation mensuelle Janvier 2026"),
            }),
            'amount': forms.NumberInput(attrs={
                'class': DASHBOARD_FIELD_CLASS,
                'placeholder': '5000',
                'step': '0.01', 'min': '0',
            }),
            'target_amount': forms.NumberInput(attrs={
                'class': DASHBOARD_FIELD_CLASS,
                'placeholder': _("Objectif total (optionnel)"),
                'step': '0.01', 'min': '0',
            }),
            'description': forms.Textarea(attrs={
                'class': DASHBOARD_FIELD_CLASS, 'rows': 3,
                'placeholder': _("À quoi sert cette cotisation ?"),
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-5 w-5 rounded text-primary focus:ring-primary/40',
            }),
        }

    def __init__(self, *args, chorale=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._chorale = chorale  # mémorisé pour `clean_title` (unicité)

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise ValidationError(_("Le montant doit être strictement positif."))
        return amount

    def clean_title(self):
        # On vérifie l'unicité côté form pour donner une erreur lisible
        # (la contrainte DB ferait planter par IntegrityError sinon).
        title = self.cleaned_data.get('title')
        if title and self._chorale:
            qs = Contribution.objects.filter(chorale=self._chorale, title__iexact=title)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(_("Un type de cotisation portant ce titre existe déjà."))
        return title


class MemberContributionForm(forms.ModelForm):
    """Enregistrer un paiement. Les choix de `contribution` et `member`
    sont restreints à la chorale courante — la liste déroulante ne doit pas
    laisser fuiter des objets d'autres chorales (sécurité par construction)."""

    class Meta:
        model = MemberContribution
        fields = ['contribution', 'member', 'amount', 'paid_at', 'note']
        widgets = {
            'contribution': forms.Select(attrs={'class': DASHBOARD_FIELD_CLASS}),
            'member': forms.Select(attrs={'class': DASHBOARD_FIELD_CLASS}),
            'amount': forms.NumberInput(attrs={
                'class': DASHBOARD_FIELD_CLASS, 'step': '0.01', 'min': '0',
            }),
            'paid_at': forms.DateInput(attrs={
                'class': DASHBOARD_FIELD_CLASS, 'type': 'date',
            }),
            'note': forms.TextInput(attrs={
                'class': DASHBOARD_FIELD_CLASS,
                'placeholder': _("Référence, mode de paiement... (optionnel)"),
            }),
        }

    def __init__(self, *args, chorale=None, **kwargs):
        super().__init__(*args, **kwargs)
        if chorale is not None:
            self.fields['contribution'].queryset = chorale.contributions.filter(is_active=True)
            self.fields['member'].queryset = chorale.members.all()

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise ValidationError(_("Le montant doit être strictement positif."))
        return amount


class CashFlowForm(forms.ModelForm):
    """CRUD entrée/sortie. Le `created_by` et `chorale` sont injectés en vue."""

    class Meta:
        model = CashFlow
        fields = ['title', 'type_cash_flow', 'amount', 'date', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': DASHBOARD_FIELD_CLASS,
                'placeholder': _("Ex: Don pour le concert, Achat partitions"),
            }),
            'type_cash_flow': forms.Select(attrs={'class': DASHBOARD_FIELD_CLASS}),
            'amount': forms.NumberInput(attrs={
                'class': DASHBOARD_FIELD_CLASS, 'step': '0.01', 'min': '0',
            }),
            'date': forms.DateInput(attrs={
                'class': DASHBOARD_FIELD_CLASS, 'type': 'date',
            }),
            'description': forms.Textarea(attrs={
                'class': DASHBOARD_FIELD_CLASS, 'rows': 3,
                'placeholder': _("Détails (optionnel)"),
            }),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise ValidationError(_("Le montant doit être strictement positif."))
        return amount


# ── Censeur ────────────────────────────────────────────────────────────


class BulkAbsenceForm(forms.Form):
    """Saisie en masse : 1 rencontre + N membres absents en un seul submit.
    Pattern Bulk + Idempotent upsert : le post est rejouable (delete + recreate
    dans une transaction côté vue) — pas de doublons possibles.
    """
    event = forms.ModelChoiceField(
        queryset=ChoraleEvent.objects.none(),  # rempli dans __init__
        label=_("Rencontre"),
        widget=forms.Select(attrs={'class': DASHBOARD_FIELD_CLASS}),
    )
    absent_members = forms.ModelMultipleChoiceField(
        queryset=None,  # rempli dans __init__
        required=False,  # vider la liste = 0 absent (efface tout)
        widget=forms.CheckboxSelectMultiple,
        label=_("Membres absents"),
    )
    reason = forms.CharField(
        required=False,
        label=_("Raison commune (optionnel)"),
        widget=forms.TextInput(attrs={
            'class': DASHBOARD_FIELD_CLASS,
            'placeholder': _("Ex: Maladie, voyage..."),
        }),
    )
    is_justified = forms.BooleanField(
        required=False, label=_("Absence(s) justifiée(s)"),
        widget=forms.CheckboxInput(attrs={'class': 'h-5 w-5 rounded text-primary'}),
    )

    def __init__(self, *args, chorale=None, **kwargs):
        super().__init__(*args, **kwargs)
        if chorale is not None:
            self.fields['event'].queryset = ChoraleEvent.objects.filter(
                chorale=chorale, event_type__in=Absence.TRACKED_EVENT_TYPES,
            ).order_by('-date')
            self.fields['absent_members'].queryset = chorale.members.all()


class AbsenceEditForm(forms.ModelForm):
    """Édition fine d'une absence existante (raison, caractère justifié)."""

    class Meta:
        model = Absence
        fields = ['reason', 'is_justified']
        widgets = {
            'reason': forms.TextInput(attrs={
                'class': DASHBOARD_FIELD_CLASS,
                'placeholder': _("Raison de l'absence"),
            }),
            'is_justified': forms.CheckboxInput(attrs={
                'class': 'h-5 w-5 rounded text-primary',
            }),
        }


class SanctionForm(forms.ModelForm):
    """CRUD d'une sanction.
    Validation croisée: amount obligatoire pour les amendes, interdit sinon.
    """

    class Meta:
        model = Sanction
        fields = ['member', 'sanction_type', 'reason', 'amount', 'time_limit',
                  'applied_at', 'is_paid']
        widgets = {
            'member': forms.Select(attrs={'class': DASHBOARD_FIELD_CLASS}),
            'sanction_type': forms.Select(attrs={'class': DASHBOARD_FIELD_CLASS,
                                                 'data-sanction-type-select': '1'}),
            'reason': forms.Textarea(attrs={
                'class': DASHBOARD_FIELD_CLASS, 'rows': 3,
                'placeholder': _("Pourquoi cette sanction ?"),
            }),
            'amount': forms.NumberInput(attrs={
                'class': DASHBOARD_FIELD_CLASS, 'step': '0.01', 'min': '0',
                'placeholder': _("Montant (amende uniquement)"),
            }),
            'time_limit': forms.DateInput(attrs={
                'class': DASHBOARD_FIELD_CLASS, 'type': 'date',
            }),
            'applied_at': forms.DateInput(attrs={
                'class': DASHBOARD_FIELD_CLASS, 'type': 'date',
            }),
            'is_paid': forms.CheckboxInput(attrs={
                'class': 'h-5 w-5 rounded text-primary',
            }),
        }

    def __init__(self, *args, chorale=None, **kwargs):
        super().__init__(*args, **kwargs)
        if chorale is not None:
            self.fields['member'].queryset = chorale.members.all()

    def clean(self):
        cleaned = super().clean()
        sanction_type = cleaned.get('sanction_type')
        amount = cleaned.get('amount')

        if sanction_type == Sanction.SANCTION_FINE:
            if amount is None or amount <= 0:
                self.add_error('amount', _("Une amende requiert un montant strictement positif."))
        else:
            # Pour warning/suspension, on force l'amount à None (cohérence DB).
            cleaned['amount'] = None
            # is_paid n'a de sens que pour les amendes
            cleaned['is_paid'] = False

        return cleaned
