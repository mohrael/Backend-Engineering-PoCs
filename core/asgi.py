"""
ASGI config for concurrency_poc project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from channels.auth import AuthMiddlewareStack
from django.urls import re_path,path
from realtime_chat.routing import websocket_urlpatterns
from realtime_chat.middleware import CustomMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http":django_asgi_app,
    "websocket": CustomMiddleware(
        AuthMiddlewareStack(
            URLRouter(
                websocket_urlpatterns
            )
        )
    )

})