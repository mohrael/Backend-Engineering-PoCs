
from django_redis import get_redis_connection
from django.core.management.base import BaseCommand
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
class Command(BaseCommand):

    def handle(self, *args, **options):
        self.con = get_redis_connection()
        self.subscibe()

    def subscibe(self):
        pubsub = self.con.pubsub()
        pubsub.subscribe("__keyevent@1__:expired")

        print("waiting for expired connection messages..")

        for message in pubsub.listen():

            if message["type"] == "message":
                print("Received:",message["channel"], message['data'])

                key_name = message["data"].decode()

                if not key_name.startswith("user:") or ":connections:" not in key_name:
                    continue

                parts = key_name.split(":")
                self.user_id=parts[1]

                cursor = 0
                user_is_online = False

                while True:
                    new_cursor, keys = self.con.scan(cursor,match=f"user:{self.user_id}:connections:*")
                    cursor = new_cursor

                    if keys:
                        user_is_online = True
                        break

                    if cursor == 0:
                        break

                if not user_is_online:
                    self.con.srem("online_users",self.user_id)

                    self.con.delete(f"user:{self.user_id}:connections")

                    channel_layer = get_channel_layer()
                    groups = self.con.smembers(f"user:{self.user_id}:groups")
                    
                    username_bytes = self.con.get(f"user:{self.user_id}:username")
                    username = username_bytes.decode() if username_bytes else f"User {self.user_id}"
                    for gp in groups:
                        gp_name = gp.decode()

                        async_to_sync(channel_layer.group_send)(
                            gp_name,
                            {
                                "type":"presence",
                                "event":"offline",
                                "username":username,
                                "sender_channel": "system_worker"
                            }
                        )
                    self.con.delete(f"user:{self.user_id}:groups")
                        
                    

    # def publish(self):
    #     self.con.publish("my_channel","Hello from publicher")



