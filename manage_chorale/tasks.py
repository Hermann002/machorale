from celery import shared_task
from .services import get_dashboard_stats

@shared_task(bind=True)
def calcul_stats_dashboard(self, chorale_id):
    try:
        return get_dashboard_stats(chorale_id)
    except Exception as e:
        self.retry(exc=e)
