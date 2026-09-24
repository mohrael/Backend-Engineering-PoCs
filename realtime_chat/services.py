from channels.db import database_sync_to_async
from .models import Message

@database_sync_to_async
def save_message(user,room,content):
    return Message.objects.create(
        sender = user,
        room=room,
        content=content
    )

@database_sync_to_async
def get_messages(room,limit=20,before_id=None):
    query = Message.objects.filter(room=room)

    if before_id:
        query = query.filter(id__lt = before_id)

    messages = list(
        query
        .select_related("sender") \
        .values(
            "id",
            "sender__username",
            "content",
            "timestamp"
        ) \
        .order_by("-id")[:limit+1]
    )

    has_more = len(messages) > limit

    if has_more:    
        messages = messages[:limit]


    next_before_id = messages[-1]["id"] if has_more else None

    return {
        
        "messages": [
            {
                "id": message["id"],
                "sender": message["sender__username"],
                "message": message["content"],
                "timestamp": message["timestamp"].isoformat(),
            }
            for message in messages
        ],
        "next_before_id": next_before_id,
        "has_more": has_more,
    }

