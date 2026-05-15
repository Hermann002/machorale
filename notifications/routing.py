def websocket_urlpatterns():
    from django.urls import re_path
    from notifications import consumers

    return [
        re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
    ]