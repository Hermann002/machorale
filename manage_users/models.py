from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import re
from django.utils.translation import gettext as _


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

class Member(User):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        verbose_name = "Member"
        verbose_name_plural = "Members"

class SuperadminChorale(User):
    class Meta:
        verbose_name = "Superadmin Chorale"
        verbose_name_plural = "Superadmins Chorale"

# class AdminChorale(Member):
#     pass

class Secretary(models.Model):
    member= models.OneToOneField(Member, on_delete=models.CASCADE)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICE, default='general')

    class Meta:
        verbose_name = "Secretaire"
        verbose_name_plural = "Secretaires"

class Treasurer(models.Model):
    member= models.OneToOneField(Member, on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = "Tresorier"
        verbose_name_plural = "Tresoriers"

class Censor(models.Model):
    member= models.OneToOneField(Member, on_delete=models.CASCADE)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICE, default='general')

    class Meta:
        verbose_name = "Censeur"
        verbose_name_plural = "Censeurs"

class MemberContribution(models.Model):
    member= models.ForeignKey(Member, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_contributed = models.DateField(auto_now_add=True)
    contribution_ref = models.CharField(max_length=100, default='contibution mensuelle')

class Saction(models.Model):
    member= models.ForeignKey(Member, on_delete=models.CASCADE)
    reason = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_sanctioned = models.DateField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)
    time_limit = models.DateField()
