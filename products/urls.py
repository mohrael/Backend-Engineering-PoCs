from django.urls import path
from .views import ProductView

urlpatterns=[
    path("buy/<int:prod_id>",ProductView.as_view() )
]