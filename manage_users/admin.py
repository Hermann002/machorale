from django.contrib import admin
from .models import Member, Profile, Secretary, Treasurer, Censor
# Register your models here.

admin.site.register(Member)
admin.site.register(Profile)
admin.site.register(Secretary)
admin.site.register(Treasurer)
admin.site.register(Censor)
