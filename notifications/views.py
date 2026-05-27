from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from manage_chorale.models import Chorale

from .models import Notification
from .services import _serialize


def _chorale_for(request, slug):
    """Renvoie la Chorale si le user en est membre, sinon None."""
    chorale = Chorale.objects.filter(slug=slug).first()
    if not chorale or not chorale.members.filter(pk=request.user.pk).exists():
        return None
    return chorale


@login_required
@require_GET
def list_notifications(request, slug):
    chorale = _chorale_for(request, slug)
    if chorale is None:
        return JsonResponse({"error": "forbidden"}, status=403)

    qs = Notification.objects.filter(
        user=request.user, chorale=chorale
    ).order_by('-created_at')[:50]

    unread = Notification.objects.filter(
        user=request.user, chorale=chorale, read_at__isnull=True
    ).count()

    return JsonResponse({
        "unread": unread,
        "notifications": [_serialize(n) for n in qs],
    })


@login_required
@require_POST
def mark_all_read(request, slug):
    chorale = _chorale_for(request, slug)
    if chorale is None:
        return JsonResponse({"error": "forbidden"}, status=403)

    Notification.objects.filter(
        user=request.user, chorale=chorale, read_at__isnull=True
    ).update(read_at=timezone.now())

    return JsonResponse({"ok": True})
