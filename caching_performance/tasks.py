from celery import shared_task
from django.core.cache import cache
from django_redis import get_redis_connection
from .models import ShortURL
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import F


TAKE_CLICKS_SCRIPT = """
    local synced = 0
    local clicks = tonumber(redis.call('GET',KEYS[1]) or 0)

    if clicks >= 50 then
        clicks = clicks - 50
        redis.call('SET',KEYS[1],clicks)
        synced = 50
    end
    return synced
"""

RESTORE_CLICKS_SCRIPT = """
    local clicks = tonumber(redis.call('GET',KEYS[1]) or 0)
    local amount = tonumber(ARGV[1])
    clicks = clicks + amount
    redis.call('SET',KEYS[1],clicks)
    return clicks
"""

REGISTER_CLICK_SCRIPT = """
    local clicks = redis.call('INCR',KEYS[1])
    redis.call('SADD',KEYS[2],ARGV[1])

    return clicks

"""

REMOVE_PENDING_SHORT_CODE_SCRIPT = """
    local rem = tonumber(redis.call('GET',KEYS[1]) or 0)

    if rem < 50 then
        redis.call('SREM',KEYS[2],ARGV[1])
    end

    return rem
    
"""




con = get_redis_connection("default")
register_click = con.register_script(REGISTER_CLICK_SCRIPT)



@shared_task(bind=True,max_retries=5,default_retry_delay=10)
def sync_clicks(self,short_code):
    

    take_script = con.register_script(TAKE_CLICKS_SCRIPT)
    restore_script = con.register_script(RESTORE_CLICKS_SCRIPT)
    remove_script = con.register_script(REMOVE_PENDING_SHORT_CODE_SCRIPT)

    redis_key = "clicks:"+short_code

    synced_clicks = take_script(keys=[redis_key])

    if synced_clicks == 0:
        return 0

    try:
        with transaction.atomic():
            ShortURL.objects.filter(short_code=short_code).update(clicks=F('clicks')+sync_clicks)
            # url = ShortURL.objects.select_for_update().get(short_code=short_code)

            # test_key = "test:fail_once:" + short_code

            # if con.setnx(test_key, 1):
            #     print("INTENTIONAL TEST FAILURE")
            #     raise Exception("TEST DATABASE FAILURE")


            # url.clicks += synced_clicks
            # url.save()

            remove_script(keys=[redis_key,+"pending_short_codes"],args=[short_code])

            # print("Synced clicks:", synced_clicks)
            # print("Postgres clicks:", url.clicks)

    except Exception as exc:

        restore_script(keys=[redis_key],args=[synced_clicks])
        
        raise self.retry(exc=exc, countdown = 2 ** self.request.retries)

    
    return synced_clicks

@shared_task
def dispatcher_task():
    pending_short_codes = con.smembers("pending_short_codes")
    for short_code in pending_short_codes:
        short_code = short_code.decode()
        clicks = con.get(f"clicks:{short_code}")
        if clicks and int(clicks) >= 50:
            print("DISPATCHING:", short_code)
            sync_clicks.delay(short_code)
            



    
