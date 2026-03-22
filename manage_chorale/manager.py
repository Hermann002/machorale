from django.db import models
from django.utils import timezone
from .models import Chorale

class EventManager(models.Manager):
    def for_chorale(self, chorale, user):
        if not Chorale.objects.filter(id=chorale.id, admin=user).exists():
            return self.none()
        return self.filter(chorale=chorale)
    
    def for_user(self, user):
        return self.filter(user=user)
    
    def by_type(self, event_type):
        return self.filter(event_type=event_type)
    
    def since(self, hours=24):
        cutoff = timezone.now() - timezone.timedelta(hours=hours)
        return self.filter(timestamp__gte=cutoff)