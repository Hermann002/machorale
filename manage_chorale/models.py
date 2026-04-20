from django.db import models
from manage_users.models import CustomUser
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
from datetime import datetime, timedelta
from django.conf import settings
from django.utils.text import slugify



class Chorale(models.Model):
    name = models.CharField(max_length=100)
    established_date = models.DateField()
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    
    TYPE_CHOICES = (
        ('chorale', 'CHORALE'),
        ('mouvement', 'MOUVEMENT'),
        ('association', 'ASSOCIATION'),
    )

    type_c = models.CharField(max_length=20, choices=TYPE_CHOICES, default='chorale')
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="managed_group")
    members = models.ManyToManyField(CustomUser, related_name="chorales", blank=True)
    logo = models.ImageField(upload_to='chorale_logos/', blank=True, null=True)
    slogan = models.CharField(max_length=255, blank=True)
    meeting_frequency = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.name}{self.admin.username}"
    
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


class Contribution(models.Model):
    title = models.CharField(max_length=100)
    chorale = models.ForeignKey(Chorale, on_delete=models.CASCADE, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_contributed = models.DateField(auto_now_add=True)
    description = models.TextField(blank=True)
    target_amount = models.DecimalField(max_digits=10, decimal_places=2)

class CashFlow(models.Model):
    title = models.CharField(max_length=100)
    
    TYPE_CHOISE = (
        ('entrée', 'ENTREE'),
        ('sortie', 'SORTIE'),
    )

    type_cash_flow = models.CharField(max_length=20, choices=TYPE_CHOISE, default='entrée')
    chorale = models.ForeignKey(Chorale, on_delete=models.CASCADE, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(auto_now_add=True)
    description = models.TextField(blank=True)

class MeetingReport(models.Model):
    chorale = models.ForeignKey(Chorale, on_delete=models.CASCADE, db_index=True)
    date = models.DateField()
    agenda = models.TextField()
    minutes = models.TextField()
    attendees = models.TextField()
    report = models.FileField(upload_to='meeting_reports/', blank=True, null=True)

class Commission(models.Model):
    name = models.CharField(max_length=100)
    chorale = models.ForeignKey(Chorale, on_delete=models.CASCADE, db_index=True)
    lead = models.CharField(max_length=255, null=True, blank=True)

class Event(models.Model):
    from .manager import EventManager
    """
    Historique des événements
    """

    chorale = models.ForeignKey("Chorale", on_delete=models.CASCADE, related_name='events', help_text="Chorale Concernée par l'événement")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='events', help_text="Utilisateur ayant déclanché l'événement")
    timestamp = models.DateTimeField(default=timezone.now, db_index=True, help_text="Date et heure de l'événement")
    
    EVENT_TYPES = [
        ('payment', 'Paiement effectué'),
        ('warning', 'sanction appliquée'),
        ('person_add', 'membre ajouté'),
        ('person_remove', 'membre retiré'),
        ('upload_file', 'rapport'),
        ('other', 'autre'),
    ]


    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, help_text="Type d'événement")
    description = models.TextField(help_text="Description détaillée de l'événement")
    short_description = models.CharField(max_length=255, blank=True, help_text="Description courte pour les notifications")
    comment = models.TextField(blank=True, help_text="Commentaire additionnel (ex: raison d'une sanction, etc)")
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True, help_text="Type de l'objecct concerné (ex: Contribution, Sanction) ")
    object_id = models.PositiveBigIntegerField(null=True, blank=True, help_text="ID de l'objet concerné")
    content_object = GenericForeignKey('content_type', 'object_id')
    metadata = models.JSONField(default=dict, blank=True, help_text="Données contextuelles (ancienne valeur, nouvelle valeur, etc)")
    ip_address = models.GenericIPAddressField(null=True, blank=True, help_text="Adresse IP de l'utilisateur au moment de l'action")
    user_agent = models.TextField(blank=True, help_text="User agent du navigateur/appareil")
    is_important = models.BooleanField(default=False, help_text="Indique si l'événement est considéré comme important pour les notifications")

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
        user_agent = None

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