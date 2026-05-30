"""
API sync pour persister + pousser des notifications WebSocket.

Pattern : DB d'abord (source de vérité), WS ensuite (push temps réel).
Si Channels indisponible, la notif reste en base et sera vue au prochain reload.
"""
import hashlib

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Notification


# Channels limite les noms de group à 100 chars ASCII alphanum/_/-/.
# Au-delà, on hash le suffixe pour rester valide tout en restant déterministe.
_GROUP_MAX_LEN = 100


def _safe_group(prefix: str, suffix: str) -> str:
    """Construit un nom de group < 100 chars. Hash si suffixe trop long."""
    candidate = f"{prefix}_{suffix}"
    if len(candidate) <= _GROUP_MAX_LEN:
        return candidate
    digest = hashlib.sha1(str(suffix).encode()).hexdigest()[:32]
    return f"{prefix}_{digest}"


def chorale_group(slug: str) -> str:
    return _safe_group("chorale", slug)


def user_group(user_id) -> str:
    return _safe_group("user", str(user_id))


def _serialize(notif: Notification) -> dict:
    """Format unique pour API REST et message WS — JS dédup par id."""
    return {
        "id": notif.id,
        "kind": notif.kind,
        "title": notif.title,
        "body": notif.body,
        "payload": notif.payload,
        "created_at": notif.created_at.isoformat(),
        "read_at": notif.read_at.isoformat() if notif.read_at else None,
    }


def _push(group: str, type_name: str, data: dict) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    async_to_sync(layer.group_send)(
        group,
        {"type": type_name, "payload": data},
    )


def notify_user(user, payload: dict, *, chorale=None, kind: str = "generic") -> Notification:
    """
    Persiste 1 Notification pour `user` + push WS sur son groupe perso.
    `user` peut être un objet User ou un id (int).
    """
    user_id = getattr(user, 'id', user)

    notif = Notification.objects.create(
        user_id=user_id,
        chorale=chorale,
        kind=kind,
        title=payload.get("title", "Notification"),
        body=payload.get("body", ""),
        payload=payload,
    )
    _push(user_group(user_id), "notify.message", _serialize(notif))
    return notif


def notify_chorale(chorale, payload: dict, *, kind: str = "generic"):
    """
    Persiste 1 Notification par membre de la chorale + push WS sur le groupe.
    `chorale` peut être un objet Chorale ou un slug (str).
    """
    # Import local pour éviter cycle (manage_chorale n'importe pas notifications).
    from manage_chorale.models import Chorale

    if isinstance(chorale, str):
        chorale = Chorale.objects.get(slug=chorale)

    members = list(chorale.members.all())
    notifs = [
        Notification(
            user=member,
            chorale=chorale,
            kind=kind,
            title=payload.get("title", "Notification"),
            body=payload.get("body", ""),
            payload=payload,
        )
        for member in members
    ]
    Notification.objects.bulk_create(notifs)

    # bulk_create avec PostgreSQL renseigne les id (>= Django 4).
    if notifs:
        _push(
            chorale_group(chorale.slug),
            "chorale.announcement",
            _serialize(notifs[0]),
        )
    return notifs
