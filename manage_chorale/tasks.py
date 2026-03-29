from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from manage_chorale.models import Chorale, Event
from manage_users.models import CustomUser, Profile
from django.db.models import Count, Avg, Sum

@shared_task(bind=True)
def calcul_stats_dashboard(self, chorale_id):
    try:
        chorale = Chorale.objects.get(id=chorale_id)
        total_members = chorale.members.count()
        # last_meeting_date = chorale.events.filter(type="meeting").order_by('-date').first().date
        # current_balance = chorale.contributions.aggregate(total=Sum('amount'))['total'] or 0
        # pending_sanctions = chorale.sanctions.filter(is_resolved=False).count()

        return {
            "total_members": total_members,
            # "last_meeting_date": last_meeting_date,
            # "current_balance": current_balance,
            # "pending_sanctions": pending_sanctions,
        }
    except Chorale.DoesNotExist:
        return {"error": "Chorale not found"}
    except Exception as e:
        self.retry(exc=e)