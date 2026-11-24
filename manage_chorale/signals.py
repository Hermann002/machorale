from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import (
    MemberContribution, CashFlow, Contribution,
    Membership, ChoraleEvent, Absence, Sanction
)

def get_chorale_id_from_instance(instance):
    if hasattr(instance, 'chorale_id'):
        return instance.chorale_id
    elif hasattr(instance, 'contribution') and instance.contribution:
        return instance.contribution.chorale_id
    elif hasattr(instance,'event') and instance.event;
        return instance.event.chorale_id
    return None
