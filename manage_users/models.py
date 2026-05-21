from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
import re
from django.utils.translation import gettext_lazy as _
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
        
class Profile(models.Model):
    user = models.OneToOneField('CustomUser', on_delete=models.CASCADE)
    _contact = models.CharField(max_length=15, blank=True, null=True, validators=[validate_international_phone])

    MARITAL_STATUS_CHOICE = (
        ('single', _('Single')),
        ('married', _('Married')),
        ('divorced', _('Divorced')),
        ('widowed', _('Widowed')),
    )
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICE, default='single')
    christened = models.BooleanField(default=False)
    confirmed = models.BooleanField(default=False)
    joined_date = models.DateField(blank=True, null=True)
    dob = models.DateField(blank=True, null=True)

    PROFESSION_CHOICES = (
        ('student', _('Student')),
        ('computer_scientist', _('Computer scientist')),
        ('nurse', _('Nurse')),
        ('teacher', _('Teacher')),
        ('engineer', _('Engineer')),
        ('doctor', _('Doctor')),
        ('lawyer', _('Lawyer')),
        ('other', _('Other')),
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
        (ROLE_MEMBER, _('Member')),
        (ROLE_SUPERADMIN_CHORALE, _('Super Chorale Admin')),
    ]

    CHORALE_ROLE_MEMBER = 'member'
    CHORALE_ROLE_SECRETARY = 'secretary'
    CHORALE_ROLE_TREASURER = 'treasurer'
    CHORALE_ROLE_CENSOR = 'censor'

    CHORALE_ROLE_CHOICES = [
        (CHORALE_ROLE_MEMBER, _('Member')),
        (CHORALE_ROLE_SECRETARY, _('Secretary')),
        (CHORALE_ROLE_TREASURER, _('Treasurer')),
        (CHORALE_ROLE_CENSOR, _('Censor')),
    ]
    
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    chorale_role = models.CharField(max_length=20, choices=CHORALE_ROLE_CHOICES, default=CHORALE_ROLE_MEMBER)
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
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
        ]

class OtpCode(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField(blank=True, null=True)
    used = models.BooleanField(default=False)

    def generate_new_code(self):
        new_code = ""
        for _i in range(5):
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

