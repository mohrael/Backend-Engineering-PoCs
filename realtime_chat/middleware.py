from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.tokens import AccessToken
from jwt.exceptions import InvalidTokenError
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async

User = get_user_model()

@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except:
        return None

    
class CustomMiddleware(BaseMiddleware):

    async def __call__(self, scope,receive,send):
        query_string = scope.get('query_string').decode()
        token = None

        if "token=" in query_string:
            token = query_string.split("=")[1]

        if token:
            try:
                validated_token = AccessToken(token)
                user = await get_user(validated_token["user_id"])

                if user:
                    scope["user"] = user
    

            except (InvalidTokenError):
                print("Invalid JWT token")

        return await super().__call__(scope,receive,send)