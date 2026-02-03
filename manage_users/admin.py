from django.contrib import admin
from .models import Member, SuperadminChorale, OtpCode, Censor, Secretary, Treasurer

admin.site.register(Member)
admin.site.register(SuperadminChorale)
admin.site.register(OtpCode)
admin.site.register(Censor)
admin.site.register(Secretary)
admin.site.register(Treasurer)