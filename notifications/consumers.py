import json
from channels.generic.websocket import AsyncWebsocketConsumer

from .services import chorale_group, user_group


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Consumer minimal : accepte la connexion, renvoie en echo
    chaque message reçu. Sert de test de tunnel WS.
    """

    async def connect(self):
        user = self.scope.get('user')
        # Slug : 1) capture URL (re_path), 2) fallback session.
        slug = self.scope.get('url_route', {}).get('kwargs', {}).get('slug')
        if not slug:
            session = self.scope.get('session') or {}
            slug = session.get('active_chorale_slug')

        user_id = getattr(user, 'id', None) or 'anon'
        self.group_name = user_group(user_id)
        self.groups = [self.group_name]
        if slug:
            self.groups.append(chorale_group(slug))

        print(f"[WS] connect — user={user} groups={self.groups}")

        for group in self.groups:
            await self.channel_layer.group_add(group, self.channel_name)

        await self.accept()
        await self.send(text_data=json.dumps({
            "type": "welcome",
            "groups": self.groups,
        }))

    async def disconnect(self, close_code):
        print(f"[WS] disconnect — code={close_code}")
        if hasattr(self, "groups"):
            for group in self.groups:
                await self.channel_layer.group_discard(group, self.channel_name)
        


    async def receive(self, text_data=None, bytes_data=None):

        # Echo : renvoyer le même contenu enveloppé.
        await self.send(text_data=json.dumps({
            "type": "echo",
            "received": text_data,
        }))

    async def notify_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "notification",
            "message": event.get("payload", {}),
        }))
    
    async def chorale_announcement(self, event):
        await self.send(text_data=json.dumps({
            "type": "chorale_announcement",
            "message": event.get("payload", {}),
        }))