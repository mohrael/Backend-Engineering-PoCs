from channels.generic.websocket import  AsyncWebsocketConsumer
import json
from datetime import datetime,timezone
from .services import get_messages,save_message
# from django.core.cache import cache
from django_redis import get_redis_connection
from asgiref.sync import sync_to_async
import time
import asyncio


CONNECT_SCRIPT = """
    local connections = tonumber(redis.call('INCR',KEYS[1]))
    redis.call('SADD',KEYS[2],ARGV[1])
    return connections
"""

DISCONNECT_SCRIPT = """
    local connections = tonumber(redis.call('GET',KEYS[1]) or 0)
    if connections >= 1 then
        connections = tonumber(redis.call('DECR',KEYS[1]))
        if connections <= 0 then
            redis.call('SREM',KEYS[2],ARGV[1])
            redis.call('DEL',KEYS[1])
        end
    end
    return connections
"""

RATE_LIMIT_SCRIPT = """
    local rate_limiter = tonumber(redis.call('INCR',KEYS[1]))
    if rate_limiter == 1 then
        redis.call('EXPIRE',KEYS[1],10)
    end
    return rate_limiter
"""


class ChatConsumer(AsyncWebsocketConsumer):
    HEARTBEAT_INTERVAL = 10
    CONNECTION_TTL = 60

    @property
    def redis_con(self):
        if not hasattr(self,"_redis_con"):
            self._redis_con = get_redis_connection("default")
        return self._redis_con

    async def connect(self):
        self.last_pong = time.time()
        
        self.has_more = True
        self.user_id = None
        self.group_name = None
        self.heartbeat_task = None
        self.first_msg = False

        user = self.scope['user']


        # 1. Authentication
        if not user.is_authenticated:
            await self.close()
            return

        # 2. get
        self.user_id = user.id
        self.connection_key = f"user:{self.user_id}:connections:{self.channel_name}"
        self.group_name = self.scope['url_route']["kwargs"]["gp_name"]
        self.rate_limiter = f"rate_limit:user:{self.user_id}:group:{self.group_name}"
    
        self.connect_script = self.redis_con.register_script(CONNECT_SCRIPT)
        self.disconnect_script = self.redis_con.register_script(DISCONNECT_SCRIPT)
        self.rate_limiter_script = self.redis_con.register_script(RATE_LIMIT_SCRIPT)
        # await sync_to_async(self.redis_con.set)(
        #     self.rate_limiter,
        #     5,
        #     ex= self.CONNECTION_TTL,
        # )
        await sync_to_async(self.redis_con.set)(
            f"user:{self.user_id}:username", 
            user.get_username(),
            ex=86400
        )

        await sync_to_async(self.redis_con.set)(
            self.connection_key,
            self.group_name,
            ex = self.CONNECTION_TTL + 5
        )
        # 3. Join channels group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # 4. Accept connection
        await self.accept()        

        # 5. Mark user as online
        connection_redis_key = f"user:{self.user_id}:connections"
        online_users_key = "online_users"
        connections = await self.run_connect_script(
            connection_redis_key,
            online_users_key,
            self.user_id
        )    

        await sync_to_async(self.redis_con.sadd)(f"user:{self.user_id}:groups", self.group_name)        
        
        # 6. Notify others if its the first connection
        if connections == 1 :
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type":"presence",
                    "event":"online",
                    "username":user.get_username(),
                    "sender_channel":self.channel_name
                }
            )
        
        # 7. Load message history
        historyMsgs = await get_messages(
            self.group_name,
            limit=5
        )
        
        self.next_before_id = historyMsgs["next_before_id"]
        self.has_more = historyMsgs.get("has_more",False)
        historyMsgs["type"] = "history"

        await self.send(
            text_data=json.dumps(historyMsgs)
        )

        # start heartbeat
        self.heartbeat_task = asyncio.create_task(self.send_heartbeat())


    async def receive(self, text_data=None, bytes_data=None):
        self.last_pong = time.time()
        await self.update_expire_connection_key()
        
        if text_data:
            try:
                data = json.loads(text_data)

                if data.get("type") == "pong":
                    return


                message_type = data.get("type")
                user = self.scope["user"]

                if message_type == "load_history":
                    if not self.has_more:
                        return
                    
                    historyMsgs = await get_messages(self.group_name,5,self.next_before_id)
                    self.next_before_id = historyMsgs["next_before_id"]
                    self.has_more = historyMsgs["has_more"]
                    historyMsgs["type"]="history"

                    await self.send(
                        text_data=json.dumps(historyMsgs)
                    )
                    return
                
                if "message" in data:
                    count_rate = await self.run_rate_limiter_script(self.rate_limiter)
                    if count_rate > 5:
                        await self.send(text_data=json.dumps({
                            "type": "error",
                            "message": "You are sending messages too quickly. Please wait 10 seconds."
                        }))
                        return

                    await save_message(user,self.group_name,data["message"])
                    await self.channel_layer.group_send(
                        self.group_name,
                        {
                            "type":"chat_message",
                            "sender":user.get_username(),
                            "message":data["message"],
                            "timestamp":datetime.now(timezone.utc).isoformat()
                        }
                    )

            except json.JSONDecodeError:
                pass


    async def chat_message(self,event):
        data = {
            "sender": event["sender"],
            "message": event["message"],
            "timestamp": event["timestamp"],
        }        

        await self.send(
            text_data=json.dumps(data)
        )


    async def presence(self,event):

        if event.get("sender_channel") == self.channel_name:
            return
        
        await self.send(text_data=json.dumps({
            "type":"presence",
            "username":event["username"],
            "event":event["event"]
        }))

  
    async def disconnect(self, code):
        # stop sending pings
        if self.heartbeat_task:
            self.heartbeat_task.cancel()

        if self.user_id is None:
            return

        await self.delete_connection_key()

        connection_redis_key = f"user:{self.user_id}:connections"
        online_users_key = "online_users"
        
        connections = await self.run_disconnect_script(
            connection_redis_key,
            online_users_key,
            self.user_id
        )

        if self.group_name:
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

        if connections == 0 :
            if self.group_name:
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type":"presence",
                        "event":"offline",
                        "username":self.scope['user'].get_username(),
                        "sender_channel":self.channel_name
                    }
                )
            await sync_to_async(self.redis_con.delete)(f"user:{self.user_id}:groups")

    async def send_heartbeat(self):
        try:
            while True:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                if time.time() - self.last_pong > self.CONNECTION_TTL:
                    await self.close(code=4000)
                    break
                try:
                    await self.send(text_data=json.dumps({"type":"ping"}))
                except Exception:
                    break
        except asyncio.CancelledError:
            pass


    @sync_to_async
    def run_connect_script(self, connection_key, online_users_key, user_id):
        return self.connect_script(
            keys=[connection_key, online_users_key],
            args=[user_id]
        )
    
    @sync_to_async
    def run_disconnect_script(self, connection_key, online_users_key, user_id):
        return self.disconnect_script(
            keys=[connection_key, online_users_key],
            args=[user_id]
        )
    
    @sync_to_async
    def run_rate_limiter_script(self,rate_limiter):
        return self.rate_limiter_script(
            keys=[rate_limiter],
        )
    
    
    @sync_to_async
    def update_expire_connection_key(self):
        return self.redis_con.expire(
            self.connection_key,
            self.CONNECTION_TTL+5
        )

    @sync_to_async
    def delete_connection_key(self):
        return self.redis_con.delete(self.connection_key)
    