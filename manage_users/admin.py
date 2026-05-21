from django.contrib import admin
from .models import CustomUser, OtpCode

admin.site.register(CustomUser)
admin.site.register(OtpCode)
