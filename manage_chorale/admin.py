from django.contrib import admin
from .models import Chorale, Contribution, CashFlow, MeetingReport, Commission, Event

admin.site.register(Chorale)
admin.site.register(Contribution)
admin.site.register(Event)
