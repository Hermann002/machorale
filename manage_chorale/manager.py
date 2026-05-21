from django.db import models
from django.utils import timezone

class EventManager(models.Manager):
    def for_chorale(self, chorale, user):
        # Accès historique : réservé à l'admin de la chorale (Membership.is_admin)
        from .models import Membership
        if not Membership.objects.filter(chorale=chorale, user=user, is_admin=True).exists():
            return self.none()
        return self.filter(chorale=chorale)
    
    def for_user(self, user):
        return self.filter(user=user)
    
    def by_type(self, event_type):
        return self.filter(event_type=event_type)
    
    def since(self, hours=24):
        cutoff = timezone.now() - timezone.timedelta(hours=hours)
        return self.filter(timestamp__gte=cutoff)