from django.db import models
from manage_users.models import CustomUser

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
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="Managed_group")
    members = models.ManyToManyField(CustomUser, related_name="chorales", blank=True)
    logo = models.ImageField(upload_to='chorale_logos/', blank=True, null=True)
    slogan = models.CharField(max_length=255, blank=True)
    meeting_frequency = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField(blank=True)


class Contribution(models.Model):
    title = models.CharField(max_length=100)
    chorale = models.ForeignKey(Chorale, on_delete=models.CASCADE)
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
    chorale = models.ForeignKey(Chorale, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(auto_now_add=True)
    description = models.TextField(blank=True)

class MeetingReport(models.Model):
    chorale = models.ForeignKey(Chorale, on_delete=models.CASCADE)
    date = models.DateField()
    agenda = models.TextField()
    minutes = models.TextField()
    attendees = models.TextField()
    report = models.FileField(upload_to='meeting_reports/', blank=True, null=True)

class Commission(models.Model):
    name = models.CharField(max_length=100)
    chorale = models.ForeignKey(Chorale, on_delete=models.CASCADE)
    lead = models.CharField(max_length=255, null=True, blank=True)