from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
import re
from django.utils.translation import gettext as _
from django.utils import timezone

import random
import re


def validate_international_phone(value):
    if value:
        # Regex pour format international : + suivi de chiffres (espaces optionnels)
        if not re.match(r'^\+\d{1,3}[ \d]+$', value):
            raise ValidationError(
                _('Le numéro doit être au format international, ex: +237 77 123 45 67')
            )
        
LEVEL_CHOICE = (
    ('general', 'GENERAL'),
    ('deputy', 'DEPUTY')
)


class Profile(models.Model):
    user = models.OneToOneField('CustomUser', on_delete=models.CASCADE)
    _contact = models.CharField(max_length=15, blank=True, null=True, validators=[validate_international_phone])

    MARITAL_STATUS_CHOICE = (
        ('single', 'SINGLE'),
        ('married', 'MARRIED'),
        ('divorced', 'DIVORCED'),
        ('widowed', 'WIDOWED'),
    )
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICE, default='single')
    christened = models.BooleanField(default=False)
    confirmed = models.BooleanField(default=False)
    joined_date = models.DateField(blank=True, null=True)
    dob = models.DateField(blank=True, null=True)

    PROFESSION_CHOICES = (
        ('student', 'STUDENT'),
        ('computer_scientist', 'COMPUTER_SCIENTIST'),
        ('nurse', 'NURSE'),
        ('teacher', 'TEACHER'),
        ('engineer', 'ENGINEER'),
        ('doctor', 'DOCTOR'),
        ('lawyer', 'LAWYER'),
        ('other', 'OTHER'),
    )
    profession_c = models.CharField(max_length=100, choices=PROFESSION_CHOICES, blank=True)
    profession_o = models.CharField(max_length=100, blank=True)
    neighborhood = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)

    @property
    def profession(self):
        if self.profession_c == 'other':
            return self.profession_o
        return dict(self.PROFESSION_CHOICES).get(self.profession_c, '')

class CustomUser(AbstractUser):
    ROLE_MEMBER = 'member'
    ROLE_SUPERADMIN_CHORALE = 'super_admin_chorale'
    
    ROLE_CHOICES = [
        (ROLE_MEMBER, 'Membre'),
        (ROLE_SUPERADMIN_CHORALE, 'Super admin Chorale'),
    ]
    
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    is_verify = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def save(self, *args, **kwargs):
        if self.username:
            self.username = self.username.lower()
        if self.email:
            self.email = self.email.lower()
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['date_joined']

class OtpCode(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField(blank=True, null=True)
    used = models.BooleanField(default=False)

    def generate_new_code(self):
        new_code = ""
        for _ in range(5):
            new_code += str(random.randint(1, 9))
        self.otp_code = new_code
        self.created_at = timezone.now()
        self.expired_at = timezone.now() + timezone.timedelta(minutes=10)
        self.save()
        return self.otp_code
    
    def verify_code(self, code):
        if self.used:
            return False
        if timezone.now() > self.expired_at:
            return False
        
        is_valid = self.otp_code == code
        if is_valid:
            self.used = True
            self.save()
        return is_valid

    def otp_expired(self):
        return timezone.now() - self.created_at > timezone.timedelta(minutes=10)

    def regenerate_code(self):
        if self.used or self.otp_expired():
            self.generate_new_code()

    def __str__(self) -> str:
        return f"{self.user.first_name}-passcode"

# class AdminChorale(Member):
#     pass

class Secretary(models.Model):
    user= models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICE, default='general')

    class Meta:
        verbose_name = "Secretaire"
        verbose_name_plural = "Secretaires"

class Treasurer(models.Model):
    user= models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = "Tresorier"
        verbose_name_plural = "Tresoriers"

class Censor(models.Model):
    user= models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICE, default='general')

    class Meta:
        verbose_name = "Censeur"
        verbose_name_plural = "Censeurs"

class MemberContribution(models.Model):
    user= models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_contributed = models.DateField(auto_now_add=True)
    contribution_ref = models.CharField(max_length=100, default='contibution mensuelle')

class Sanction(models.Model):
    user= models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_sanctioned = models.DateField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)
    time_limit = models.DateField()
    sanction_ref = models.CharField(max_length=100, default='sanction pour retard de paiement')
