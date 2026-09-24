# from channels import AsgiHandler
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from .consumers import ChatConsumer



websocket_urlpatterns = [
    path("ws/chat/<str:gp_name>/",ChatConsumer.as_asgi())
]