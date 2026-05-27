import os

# Doit être défini AVANT tout import Django (settings lus à l'import).
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ma_chorale.settings.dev')

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from notifications.routing import websocket_urlpatterns

# Application HTTP Django classique (pour les vues normales).
django_asgi_app = get_asgi_application()

# Aiguilleur : selon le type de connexion, on route différemment.
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns())
    ),
})