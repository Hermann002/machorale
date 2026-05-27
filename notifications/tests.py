"""
Tests du consumer WebSocket + helpers notify_user / notify_chorale.
notify_* écrivent en DB : tests marqués django_db(transaction=True)
pour fonctionner dans le contexte asyncio.
"""
import pytest
from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from model_bakery import baker

from ma_chorale.asgi import application
from notifications.services import notify_user, notify_chorale
from notifications.models import Notification


notify_chorale_async = sync_to_async(notify_chorale)
notify_user_async = sync_to_async(notify_user)


async def _open_ws(slug="test-slug"):
    communicator = WebsocketCommunicator(
        application, f"/ws/chorale/{slug}/notifications/"
    )
    connected, _ = await communicator.connect()
    assert connected, "Handshake WS refusé"
    return communicator


_slug_counter = 0


@sync_to_async
def _make_chorale_with_member():
    """Crée une chorale + un user membre avec slug court (limite Channels)."""
    global _slug_counter
    _slug_counter += 1
    user = baker.make('manage_users.CustomUser')
    chorale = baker.make('manage_chorale.Chorale', slug=f"c{_slug_counter}")
    baker.make('manage_chorale.Membership', user=user, chorale=chorale)
    return chorale, user


# ----- Tests -----

@pytest.mark.django_db(transaction=True)
async def test_welcome_message():
    comm = await _open_ws(slug="welcome-slug")
    msg = await comm.receive_json_from()
    assert msg["type"] == "welcome"
    assert "chorale_welcome-slug" in msg["groups"]
    await comm.disconnect()


@pytest.mark.django_db(transaction=True)
async def test_echo():
    comm = await _open_ws()
    await comm.receive_json_from()  # welcome
    await comm.send_json_to({"ping": 1})
    response = await comm.receive_json_from()
    assert response["type"] == "echo"
    await comm.disconnect()


# ----- Tests avec DB -----

@pytest.mark.django_db(transaction=True)
async def test_notify_chorale_reaches_subscriber():
    chorale, user = await _make_chorale_with_member()
    comm = await _open_ws(slug=chorale.slug)
    await comm.receive_json_from()  # welcome

    await notify_chorale_async(chorale, {"title": "Test", "body": "hello"})

    msg = await comm.receive_json_from()
    assert msg["type"] == "chorale_announcement"
    assert msg["message"]["title"] == "Test"
    assert msg["message"]["id"] is not None
    await comm.disconnect()


@pytest.mark.django_db(transaction=True)
async def test_notify_chorale_persists():
    chorale, user = await _make_chorale_with_member()
    await notify_chorale_async(chorale, {"title": "Persisté", "body": "ok"})

    count = await sync_to_async(
        Notification.objects.filter(user=user, chorale=chorale).count
    )()
    assert count == 1


@pytest.mark.django_db(transaction=True)
async def test_notify_user_persists_and_pushes():
    user = await sync_to_async(baker.make)('manage_users.CustomUser')
    comm = WebsocketCommunicator(
        application, f"/ws/chorale/whatever/notifications/"
    )
    connected, _ = await comm.connect()
    assert connected
    await comm.receive_json_from()  # welcome

    # Le consumer abonne 'user_anon' (pas de session). Pour tester le push perso,
    # on appelle notify_user avec l'id 'anon' — mais ça nécessite un user en DB.
    # On crée donc un Notification directement via notify_user(user) et on
    # vérifie juste la persistance ici (le push perso serait testé avec session).
    await notify_user_async(user, {"title": "Perso", "body": "pour toi"})

    count = await sync_to_async(
        Notification.objects.filter(user=user).count
    )()
    assert count == 1
    await comm.disconnect()


@pytest.mark.django_db(transaction=True)
async def test_notify_other_slug_not_received():
    chorale_a, _ = await _make_chorale_with_member()
    chorale_b, _ = await _make_chorale_with_member()

    comm = await _open_ws(slug=chorale_a.slug)
    await comm.receive_json_from()  # welcome

    await notify_chorale_async(chorale_b, {"title": "Pour B"})

    assert await comm.receive_nothing(timeout=0.5)


@pytest.mark.django_db(transaction=True)
async def test_disconnect_cleans_groups():
    chorale, _ = await _make_chorale_with_member()
    comm = await _open_ws(slug=chorale.slug)
    await comm.receive_json_from()
    await comm.disconnect()

    # Push après disconnect — ne doit pas planter.
    await notify_chorale_async(chorale, {"title": "Trop tard"})
