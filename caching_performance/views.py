from django.shortcuts import render
from django.views import View
from .models import ShortURL
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.core.cache import cache
from .tasks import sync_clicks,register_click
from django_redis import get_redis_connection

# Create your views here.

con = get_redis_connection("default")
class ShortURLView(View):
    model = ShortURL
    
    def get(self,request,short_code):
        res = get_object_or_404(self.model,short_code=short_code)
        # res.clicks += 1
        # res.save()
        return redirect(res.original_url)

class ShortURLCachedView(View):
    model = ShortURL
    def get(self,request,short_code):
        shortCodeKey = "short_code:"+short_code
        shortCodeVal = cache.get(shortCodeKey)
        clicksKey = "clicks:"+short_code
        # clicksVal = cache.get(clicksKey)
        if shortCodeVal:
            cache.incr(clicksKey)
            return redirect(shortCodeVal)
        res = get_object_or_404(self.model,short_code=short_code) 
        cache.set(shortCodeKey,res.original_url)
        cache.set(clicksKey,res.clicks+1)
        return redirect(res.original_url)

class ShortURLCachedCeleryView(View):
    model = ShortURL
    def get(self,request,short_code):
        shortCodeKey = "short_code:"+short_code
        shortCodeVal = cache.get(shortCodeKey)
        clicksKey = "clicks:"+short_code
        # clicksVal = cache.get(clicksKey)
        # con.sadd("pending_short_codes",short_code)
        if shortCodeVal:
            register_click(
                keys=[clicksKey, "pending_short_codes"],
                args=[short_code],
            )
            # cache.incr(clicksKey)        
            # clicks = sync_clicks.delay(short_code)
            # print(clicks)
            return redirect(shortCodeVal)
        res = get_object_or_404(self.model,short_code=short_code) 
        cache.set(shortCodeKey,res.original_url)
        # cache.set(clicksKey,res.clicks+1)  
        register_click(
            keys=[clicksKey, "pending_short_codes"],
            args=[short_code],
        )
      

        return redirect(res.original_url)
