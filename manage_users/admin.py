from django.contrib import admin
from .models import CustomUser, OtpCode, Censor, Secretary, Treasurer

admin.site.register(CustomUser)
admin.site.register(OtpCode)
admin.site.register(Censor)
admin.site.register(Secretary)
admin.site.register(Treasurer)