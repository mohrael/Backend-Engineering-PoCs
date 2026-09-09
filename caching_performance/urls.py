from django.urls import path
from .views import ShortURLView,ShortURLCachedView,ShortURLCachedCeleryView

urlpatterns = [
    path('go/<str:short_code>',ShortURLView.as_view()),
    path('go-cached/<str:short_code>',ShortURLCachedView.as_view()),
    path('go-celery/<str:short_code>',ShortURLCachedCeleryView.as_view()),

]