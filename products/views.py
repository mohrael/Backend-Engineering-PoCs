from django.shortcuts import render
from django.http import HttpResponse,Http404
from .models import Product
from django.views import View
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction
from django.db.models import F

# Create your views here.
@method_decorator(csrf_exempt, name='dispatch')
class ProductView(View):
    model = Product
    def post(self,request,prod_id):
        max_retries = 3
        while max_retries > 0:
            prod = self.model.objects.get(id=prod_id)
            if(prod.stock==0):
                return HttpResponse("product sold out")
            result = self.model.objects.filter(id=prod_id,version=prod.version,stock__gt=0).update(stock=F('stock')-1,version=F('version')+1)
            if result:
                return HttpResponse("successful purchase.")
            max_retries -= 1
        return HttpResponse("System is experiencing high traffic, please try again.")