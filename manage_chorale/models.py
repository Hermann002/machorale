from django.db import models
from manage_users.models import CustomUser
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
from datetime import datetime, timedelta
from django.conf import settings
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _



class Chorale(models.Model):
    name = models.CharField(max_length=100)
    established_date = models.DateField()
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    
    TYPE_CHOICES = (
        ('chorale', _('Chorale')),
        ('mouvement', _('Movement')),
        ('association', _('Association')),
    )

    type_c = models.CharField(max_length=20, choices=TYPE_CHOICES, default='chorale')
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_chorales",
    )
    members = models.ManyToManyField(
        CustomUser,
        through="Membership",
        related_name="chorales",
        blank=True,
    )
    logo = models.ImageField(upload_to='chorale_logos/', blank=True, null=True)
    slogan = models.CharField(max_length=255, blank=True)
    meeting_frequency = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name
    
    def generate_unique_slug(self):
        base_slug = slugify(self.name)
        slug = base_slug
        num = 1
        while Chorale.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{num}"
            num += 1
        return slug
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_unique_slug()
        super().save(*args, **kwargs)


class Membership(models.Model):
    """Lien (user, chorale, rôle). Source de vérité pour l'appartenance et le rôle par chorale."""

    ROLE_MEMBER = 'member'
    ROLE_SECRETARY = 'secretary'
    ROLE_TREASURER = 'treasurer'
    ROLE_CENSOR = 'censor'
    ROLE_ADMIN = 'admin'

    ROLE_CHOICES = [
        (ROLE_MEMBER, _('Member')),
        (ROLE_SECRETARY, _('Secretary')),
        (ROLE_TREASURER, _('Treasurer')),
        (ROLE_CENSOR, _('Censor')),
        (ROLE_ADMIN, _('Admin')),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    chorale = models.ForeignKey(
        Chorale,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    is_admin = models.BooleanField(default=False)
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'chorale'], name='uniq_user_chorale'),
        ]
        indexes = [
            models.Index(fields=['chorale', 'is_admin']),
            models.Index(fields=['user', 'chorale']),
        ]

    def __str__(self):
        return f"{self.user} @ {self.chorale} ({self.get_role_display()})"


class Contribution(models.Model):
    """Type de cotisation géré par le trésorier (ex: « Cotisation Mensuelle 2026 »).
    Catalogue, pas une transaction : les paiements sont dans MemberContribution.
    """
    chorale = models.ForeignKey(Chorale, on_delete=models.CASCADE,
                                related_name='contributions', db_index=True)
    title = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2,
                                 help_text=_("Amount expected per member"))
    target_amount = models.DecimalField(max_digits=12, decimal_places=2,
                                        null=True, blank=True,
                                        help_text=_("Total chorale target (optional)"))
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            # Empêche deux types de cotisation portant le même titre dans une chorale
            models.UniqueConstraint(fields=['chorale', 'title'],
                                    name='uniq_contrib_per_chorale'),
        ]

    def __str__(self):
        return f"{self.title} ({self.chorale.name})"

    @property
    def total_collected(self):
        # Somme des paiements reçus pour ce type de cotisation
        return self.payments.aggregate(s=models.Sum('amount'))['s'] or 0


class MemberContribution(models.Model):
    """Paiement effectif d'un membre pour une Contribution.
    Une transaction immuable côté métier : on n'édite pas un paiement, on en crée un nouveau (ou on log un ajustement).
    """
    contribution = models.ForeignKey(Contribution, on_delete=models.CASCADE,
                                     related_name='payments')
    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='contribution_payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_at = models.DateField(default=timezone.now)
    note = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                    on_delete=models.SET_NULL, null=True,
                                    related_name='recorded_payments')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-paid_at', '-created_at']
        indexes = [
            models.Index(fields=['contribution', 'member']),
            models.Index(fields=['member', '-paid_at']),
        ]

    def __str__(self):
        return f"{self.member} → {self.contribution.title}: {self.amount}"


class CashFlow(models.Model):
    TYPE_ENTREE = 'entree'
    TYPE_SORTIE = 'sortie'
    TYPE_CHOICES = (
        (TYPE_ENTREE, _('Income')),
        (TYPE_SORTIE, _('Expense')),
    )

    chorale = models.ForeignKey(Chorale, on_delete=models.CASCADE,
                                related_name='cash_flows', db_index=True)
    title = models.CharField(max_length=100)
    type_cash_flow = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_ENTREE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    # date éditable (saisie par le trésorier) — auto_now_add forcerait la date du jour
    date = models.DateField(default=timezone.now)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.SET_NULL, null=True,
                                   related_name='cash_flows_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [models.Index(fields=['chorale', '-date'])]

    def __str__(self):
        return f"[{self.get_type_cash_flow_display()}] {self.title} — {self.amount}"

class MeetingReport(models.Model):
    chorale = models.ForeignKey(Chorale, on_delete=models.CASCADE, db_index=True)
    date = models.DateField()
    agenda = models.TextField()
    minutes = models.TextField()
    attendees = models.TextField()
    report = models.FileField(upload_to='meeting_reports/', blank=True, null=True)

class ChoraleEvent(models.Model):
    EVENT_TYPE_CHOICES = [
        ('practice', _('Practice')),
        ('meeting', _('Meeting')),
        ('concert', _('Concert')),
        ('assistance', _('Attendance')),
        ('other', _('Other')),
    ]

    chorale = models.ForeignKey(Chorale, on_delete=models.CASCADE, related_name='chorale_events')
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255)
    date = models.DateTimeField(db_index=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, default='practice')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_chorale_events')
    report_file = models.FileField(upload_to='event_reports/', blank=True, null=True)
    expenses = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("Expenses (XAF)"))
    income = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("Income (XAF)"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date']
        indexes = [
            models.Index(fields=['chorale', 'date']),
            models.Index(fields=['created_by', 'date']),
        ]

    def __str__(self):
        return f"{self.title} — {self.chorale.name} on {self.date:%Y-%m-%d %H:%M}"

    @property
    def is_upcoming(self):
        return self.date >= timezone.now()


# ── Censeur ─────────────────────────────────────────────────────────────
#
# Absence : on n'enregistre QUE les absents (sparse). Les présents = members - absents.
# Sanction : modèle polyvalent (warning / fine / suspension) — amount n'est rempli
# que pour les amendes (validation côté form).


class Absence(models.Model):
    """Fait métier : un membre était absent à une rencontre donnée.
    UniqueConstraint(event, member) empêche les doublons au niveau DB.
    """
    # Les rencontres pour lesquelles l'absentéisme est suivi (filtré côté form)
    TRACKED_EVENT_TYPES = ['practice', 'meeting']

    event = models.ForeignKey('ChoraleEvent', on_delete=models.CASCADE,
                              related_name='absences', db_index=True)
    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='absences')
    reason = models.CharField(max_length=255, blank=True)
    is_justified = models.BooleanField(default=False)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, related_name='recorded_absences')
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']
        constraints = [
            models.UniqueConstraint(fields=['event', 'member'],
                                    name='uniq_absence_per_event_member'),
        ]
        indexes = [models.Index(fields=['member', '-recorded_at'])]

    def __str__(self):
        return f"{self.member} absent à {self.event.title}"


class Sanction(models.Model):
    """Sanction polyvalente.
    - warning : avertissement moral (pas d'amount)
    - fine    : amende pécuniaire (amount requis côté form)
    - suspension : retrait temporaire (pas d'amount, time_limit utile)
    """
    SANCTION_WARNING = 'warning'
    SANCTION_FINE = 'fine'
    SANCTION_SUSPENSION = 'suspension'
    SANCTION_TYPE_CHOICES = (
        (SANCTION_WARNING, _('Warning')),
        (SANCTION_FINE, _('Fine')),
        (SANCTION_SUSPENSION, _('Suspension')),
    )

    chorale = models.ForeignKey(Chorale, on_delete=models.CASCADE,
                                related_name='sanctions', db_index=True)
    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='sanctions')
    sanction_type = models.CharField(max_length=20, choices=SANCTION_TYPE_CHOICES,
                                     default=SANCTION_WARNING)
    reason = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2,
                                 null=True, blank=True,
                                 help_text=_("Only for fines"))
    is_paid = models.BooleanField(default=False)
    time_limit = models.DateField(null=True, blank=True,
                                  help_text=_("Payment deadline (fine) or end date (suspension)"))
    applied_at = models.DateField(default=timezone.now)
    lifted_at = models.DateField(null=True, blank=True,
                                 help_text=_("Lift date — null = sanction active"))
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, related_name='recorded_sanctions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-applied_at', '-created_at']
        indexes = [
            models.Index(fields=['chorale', '-applied_at']),
            models.Index(fields=['member', '-applied_at']),
        ]

    def __str__(self):
        return f"[{self.get_sanction_type_display()}] {self.member} — {self.applied_at}"

    @property
    def is_active(self):
        # Une sanction est active tant qu'elle n'a pas été levée.
        # Pour les amendes, on tient compte aussi du paiement : payée = close.
        if self.lifted_at is not None:
            return False
        if self.sanction_type == self.SANCTION_FINE and self.is_paid:
            return False
        return True


class Commission(models.Model):
    name = models.CharField(max_length=100)
    chorale = models.ForeignKey(Chorale, on_delete=models.CASCADE, db_index=True)
    lead = models.CharField(max_length=255, null=True, blank=True)

class Event(models.Model):
    from .manager import EventManager
    """
    Historique des événements
    """

    chorale = models.ForeignKey("Chorale", on_delete=models.CASCADE, related_name='events', help_text=_("Chorale concerned by the event"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='events', help_text=_("User who triggered the event"))
    timestamp = models.DateTimeField(default=timezone.now, db_index=True, help_text=_("Date and time of the event"))

    EVENT_TYPES = [
        ('payment', _('Payment made')),
        ('warning', _('Sanction applied')),
        ('person_add', _('Member added')),
        ('person_remove', _('Member removed')),
        ('upload_file', _('Report')),
        ('other', _('Other')),
    ]
    IMPORTANT_EVENT_TYPES = ['payment', 'warning', 'person_add', 'person_remove', 'upload_file']

    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, help_text=_("Event type"))
    description = models.TextField(help_text=_("Detailed description of the event"))
    short_description = models.CharField(max_length=255, blank=True, help_text=_("Short description for notifications"))
    comment = models.TextField(blank=True, help_text=_("Additional comment (e.g., reason for a sanction)"))
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True, help_text=_("Type of the related object (e.g., Contribution, Sanction)"))
    object_id = models.PositiveBigIntegerField(null=True, blank=True, help_text=_("ID of the related object"))
    content_object = GenericForeignKey('content_type', 'object_id')
    metadata = models.JSONField(default=dict, blank=True, help_text=_("Contextual data (old value, new value, etc.)"))
    ip_address = models.GenericIPAddressField(null=True, blank=True, help_text=_("User's IP address at the time of the action"))
    user_agent = models.TextField(blank=True, help_text=_("User agent of the browser/device"))
    is_important = models.BooleanField(default=False, help_text=_("Indicates whether the event is considered important for notifications"))

    def save(self, *args, **kwargs):
        if self.event_type in self.IMPORTANT_EVENT_TYPES:
            self.is_important = True
        super().save(*args, **kwargs)

    objects = EventManager()

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['chorale', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['event_type']),
        ]

    def __str__(self):
        return f"[{self.chorale.name}] {self.get_event_type_display()} - {self.timestamp}"
    
    @classmethod
    def log(cls, chorale, user, event_type, description, obj=None, metadata=None, request=None):
        
        if metadata is None:
            metadata = {}
        
        ip_address = None
        user_agent = ''

        if request:
            ip_address = cls._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]

        return cls.objects.create(chorale=chorale, user=user, event_type=event_type, description=description, content_object=obj, metadata=metadata, ip_address=ip_address, user_agent=user_agent)
    
    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
    
    @staticmethod
    def format_date_diff(input_date):
        if isinstance(input_date, datetime):
            input_date = input_date.date()
        
        today = input_date.today()
        delta = today - input_date
        days = delta.days

        if days == 0:
            return "today"
        elif days == 1:
            return "yesterday"
        elif days > 1:
            return f"{days} days ago"
        else:
            return "in the future"